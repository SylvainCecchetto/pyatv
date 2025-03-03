#!/usr/bin/env python3
#
# This is a hack to sort-of intercept traffic between an Apple TV and the iOS
# app. It will establish a connection to the ATV-of-interest (using code from
# pyatv to do so), publish a fake device called "ATVProxy" that can be paired
# with the app and forward messages between the two devices. Two sets of
# encryption keys are used: one set between ATV and this proxy and a second set
# between this proxy and the app. So all messages are "re-encrypted".
#
# What you need is:
#
# * Credentials to device of interest (atvremote -a --id <device> pair)
# * Unique identifer of device, look for UniqueIdentifier in a zeroconf browser
# * IP-address and port to the Apple TV of interest
# * IP-address of an interface that is on the same network as the Apple TV
#
# Then you just call this script like:
#
#   python ./scripts/proxy.py `cat credentials` 10.0.0.20 10.0.10.30 49152 \
#      aaaaaaaa-bbbb-ccccccccc-dddddddddddd
#
# Argument order: <credentials> <local ip> <atv ip> <atv port> <identifier>
#
# The script should connect to the Apple TV immediately and you should be able
# to connect to ATVProxy from your phone (the file "credentials" contains the
# credentials you got during pairing). Use pin 1111 when pairing. You will have
# to re-pair everytime you connect and you have to restart this script if you
# disconnect, e.g. close the app.
#
# Please note that this script is perhaps not a 100% accurate MITM of all
# traffic. It takes shortcuts, doesn't imitate everything correctly and also
# has a connection established before the app (this should maybe be reversed
# here?), so some traffic might be missed. Also note that printed protobuf
# messages are based on the definitions in pyatv. If new fields have been added
# by Apple, they will not be seen in the logs.
#
# Some suggestions for improvements:
#
# * Support re-connection better without having to restart script
# * Use pyatv to discover device (based on device id) to not have to enter all
#   details on command line
# * Use argparse for arguments
# * Base proxy device name on real device (e.g. Bedroom -> Bedroom Proxy)
# * Re-work logging to make it more clear what is what
# * General clean-ups
#
# Help to improve the proxy is greatly appreciated! I will only make
# improvements in case I personally see any benefits of doing so.
"""Simple MRP proxy server to intercept traffic."""

import sys
import socket
import hashlib
import asyncio
import logging
import binascii

from aiozeroconf import Zeroconf, ServiceInfo

import curve25519
from srptools import (SRPContext, SRPServerSession, constants)
from ed25519.keys import SigningKey

from pyatv.conf import MrpService
from pyatv.mrp.srp import SRPAuthHandler, hkdf_expand
from pyatv.mrp.connection import MrpConnection
from pyatv.mrp.protocol import MrpProtocol
from pyatv.mrp import (chacha20, messages, protobuf, variant, tlv8)
from pyatv.log import log_binary

_LOGGER = logging.getLogger(__name__)


# TODO: Refactor and clean up: this is very messy
class ProxyMrpAppleTV(asyncio.Protocol):  # pylint: disable=too-many-instance-attributes  # noqa
    """Implementation of a fake MRP Apple TV."""

    def __init__(self, loop, credentials, atv_device_id):
        """Initialize a new instance of ProxyMrpAppleTV."""
        self.loop = loop
        self.credentials = credentials
        self.atv_device_id = atv_device_id
        self.server = None
        self.buffer = b''
        self.has_paired = False
        self.transport = None
        self.chacha = None
        self.connection = None
        self.input_key = None
        self.output_key = None
        self.mapping = {
            protobuf.DEVICE_INFO_MESSAGE: self.handle_device_info,
            protobuf.CRYPTO_PAIRING_MESSAGE: self.handle_crypto_pairing,
            }

        self._shared = None
        self._session_key = None
        self._signing_key = SigningKey(32 * b'\x01')
        self._auth_private = self._signing_key.to_seed()
        self._auth_public = self._signing_key.get_verifying_key().to_bytes()
        self._verify_private = curve25519.Private(secret=32 * b'\x01')
        self._verify_public = self._verify_private.get_public()

        self.context = SRPContext(
            'Pair-Setup', str(1111),
            prime=constants.PRIME_3072,
            generator=constants.PRIME_3072_GEN,
            hash_func=hashlib.sha512,
            bits_salt=128)
        self.username, self.verifier, self.salt = \
            self.context.get_user_data_triplet()

        context_server = SRPContext(
            'Pair-Setup',
            prime=constants.PRIME_3072,
            generator=constants.PRIME_3072_GEN,
            hash_func=hashlib.sha512,
            bits_salt=128)

        self._session = SRPServerSession(
            context_server,
            self.verifier,
            binascii.hexlify(self._auth_private).decode())

    def start(self, address, port):
        """Start the proxy instance."""
        # Establish connection to ATV
        self.connection = MrpConnection(address, port, self.loop)
        protocol = MrpProtocol(
            self.loop, self.connection, SRPAuthHandler(),
            MrpService(None, port, credentials=self.credentials))
        self.loop.run_until_complete(
            protocol.start(skip_initial_messages=True))
        self.connection.listener = self

        # Setup server used to publish a fake MRP server
        coro = self.loop.create_server(lambda: self, '0.0.0.0')
        self.server = self.loop.run_until_complete(coro)
        _LOGGER.info('Started MRP server at port %d', self.port)

    @property
    def port(self):
        """Port used by MRP proxy server."""
        return self.server.sockets[0].getsockname()[1]

    def connection_made(self, transport):
        """Client did connect to proxy."""
        self.transport = transport

    def _send(self, message):
        data = message.SerializeToString()
        _LOGGER.info('<<(DECRYPTED): %s', message)
        if self.chacha:
            data = self.chacha.encrypt(data)
            log_binary(_LOGGER, '<<(ENCRYPTED)', Message=message)

        length = variant.write_variant(len(data))
        self.transport.write(length + data)

    def _send_raw(self, raw):
        parsed = protobuf.ProtocolMessage()
        parsed.ParseFromString(raw)

        log_binary(_LOGGER, 'ATV->APP', Raw=raw)
        _LOGGER.info('ATV->APP Parsed: %s', parsed)
        if self.chacha:
            raw = self.chacha.encrypt(raw)
            log_binary(_LOGGER, 'ATV->APP', Encrypted=raw)

        length = variant.write_variant(len(raw))
        try:
            self.transport.write(length + raw)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception('Failed to send to app')

    def message_received(self, _, raw):
        """Message received from ATV."""
        self._send_raw(raw)

    def data_received(self, data):
        """Message received from iOS app/client."""
        self.buffer += data

        while self.buffer:
            length, raw = variant.read_variant(self.buffer)
            if len(raw) < length:
                break

            data = raw[:length]
            self.buffer = raw[length:]
            if self.chacha:
                log_binary(_LOGGER, 'ENC Phone->ATV', Encrypted=data)
                data = self.chacha.decrypt(data)

            parsed = protobuf.ProtocolMessage()
            parsed.ParseFromString(data)
            _LOGGER.info('(DEC Phone->ATV): %s', parsed)

            try:
                def unhandled_message(_, raw):
                    self.connection.send_raw(raw)

                self.mapping.get(parsed.type, unhandled_message)(parsed, data)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception('Error while dispatching message')

    def handle_device_info(self, message, _):
        """Handle received device information message."""
        _LOGGER.debug('Received device info message')

        # TODO: Consolidate this better with message.device_information(...)
        resp = messages.create(protobuf.DEVICE_INFO_MESSAGE)
        resp.identifier = message.identifier
        resp.inner().uniqueIdentifier = self.atv_device_id.decode()
        resp.inner().name = 'ATVProxy'
        resp.inner().systemBuildVersion = '15K600'
        resp.inner().applicationBundleIdentifier = 'com.apple.mediaremoted'
        resp.inner().protocolVersion = 1
        resp.inner().lastSupportedMessageType = 58
        resp.inner().supportsSystemPairing = True
        resp.inner().allowsPairing = True
        resp.inner().systemMediaApplication = "com.apple.TVMusic"
        resp.inner().supportsACL = True
        resp.inner().supportsSharedQueue = True
        resp.inner().supportsExtendedMotion = True
        resp.inner().sharedQueueVersion = 2
        self._send(resp)

    def handle_crypto_pairing(self, message, _):
        """Handle incoming crypto pairing message."""
        _LOGGER.debug('Received crypto pairing message')
        pairing_data = tlv8.read_tlv(message.inner().pairingData)
        seqno = pairing_data[tlv8.TLV_SEQ_NO][0]
        getattr(self, "_seqno_" + str(seqno))(pairing_data)

    def _seqno_1(self, pairing_data):
        if self.has_paired:
            server_pub_key = self._verify_public.serialize()
            client_pub_key = pairing_data[tlv8.TLV_PUBLIC_KEY]

            self._shared = self._verify_private.get_shared_key(
                curve25519.Public(client_pub_key), hashfunc=lambda x: x)

            session_key = hkdf_expand('Pair-Verify-Encrypt-Salt',
                                      'Pair-Verify-Encrypt-Info',
                                      self._shared)

            info = server_pub_key + self.atv_device_id + client_pub_key
            signature = SigningKey(self._signing_key.to_seed()).sign(info)

            tlv = tlv8.write_tlv({
                tlv8.TLV_IDENTIFIER: self.atv_device_id,
                tlv8.TLV_SIGNATURE: signature
            })

            chacha = chacha20.Chacha20Cipher(session_key, session_key)
            encrypted = chacha.encrypt(tlv, nounce='PV-Msg02'.encode())

            msg = messages.crypto_pairing({
                tlv8.TLV_SEQ_NO: b'\x02',
                tlv8.TLV_PUBLIC_KEY: server_pub_key,
                tlv8.TLV_ENCRYPTED_DATA: encrypted
            })

            self.output_key = hkdf_expand('MediaRemote-Salt',
                                          'MediaRemote-Write-Encryption-Key',
                                          self._shared)

            self.input_key = hkdf_expand('MediaRemote-Salt',
                                         'MediaRemote-Read-Encryption-Key',
                                         self._shared)

            log_binary(_LOGGER,
                       'Keys',
                       Output=self.output_key,
                       Input=self.input_key)

        else:
            msg = messages.crypto_pairing({
                tlv8.TLV_SALT: binascii.unhexlify(self.salt),
                tlv8.TLV_PUBLIC_KEY: binascii.unhexlify(self._session.public),
                tlv8.TLV_SEQ_NO: b'\x02'
            })

        self._send(msg)

    def _seqno_3(self, pairing_data):
        if self.has_paired:
            self._send(messages.crypto_pairing({tlv8.TLV_SEQ_NO: b'\x04'}))
            self.chacha = chacha20.Chacha20Cipher(
                self.input_key, self.output_key)
        else:
            pubkey = binascii.hexlify(
                pairing_data[tlv8.TLV_PUBLIC_KEY]).decode()
            self._session.process(pubkey, self.salt)

            proof = binascii.unhexlify(self._session.key_proof_hash)
            assert self._session.verify_proof(
                binascii.hexlify(pairing_data[tlv8.TLV_PROOF]))

            msg = messages.crypto_pairing({
                tlv8.TLV_PROOF: proof,
                tlv8.TLV_SEQ_NO: b'\x04'
            })
            self._send(msg)

    def _seqno_5(self, _):
        self._session_key = hkdf_expand(
            'Pair-Setup-Encrypt-Salt',
            'Pair-Setup-Encrypt-Info',
            binascii.unhexlify(self._session.key))

        chacha = chacha20.Chacha20Cipher(self._session_key, self._session_key)

        acc_device_x = hkdf_expand(
            'Pair-Setup-Accessory-Sign-Salt',
            'Pair-Setup-Accessory-Sign-Info',
            binascii.unhexlify(self._session.key))

        device_info = acc_device_x + self.atv_device_id + self._auth_public
        signature = self._signing_key.sign(device_info)

        tlv = tlv8.write_tlv({tlv8.TLV_IDENTIFIER: self.atv_device_id,
                              tlv8.TLV_PUBLIC_KEY: self._auth_public,
                              tlv8.TLV_SIGNATURE: signature})

        chacha = chacha20.Chacha20Cipher(self._session_key, self._session_key)
        encrypted = chacha.encrypt(tlv, nounce='PS-Msg06'.encode())

        msg = messages.crypto_pairing({
            tlv8.TLV_SEQ_NO: b'\x06',
            tlv8.TLV_ENCRYPTED_DATA: encrypted,
        })
        self.has_paired = True

        self._send(msg)


async def publish_zeroconf(zconf, ip_address, port):
    """Publish zeroconf service for ATV proxy instance."""
    props = {
        b'ModelName': False,
        b'AllowPairing': b'YES',
        b'BluetoothAddress': False,
        b'Name': b'ATVProxy',
        b'UniqueIdentifier': '4d797fd3-3538-427e-a47b-a32fc6cf3a69'.encode(),
        b'SystemBuildVersion': b'15K600',
        }

    service = ServiceInfo(
        '_mediaremotetv._tcp.local.',
        'ATVProxy._mediaremotetv._tcp.local.',
        address=socket.inet_aton(ip_address),
        port=port,
        weight=0,
        priority=0,
        properties=props)
    await zconf.register_service(service)
    _LOGGER.debug('Published zeroconf service: %s', service)


def main(loop):
    """Script starts here."""
    # To get logging from pyatv
    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) != 6:
        print("Usage: {0} <credentials> <local ip> "
              "<atv ip> <atv port> <unique identifier>".format(
                  sys.argv[0]))
        sys.exit(1)

    credentials = sys.argv[1]
    local_ip_addr = sys.argv[2]
    atv_ip_addr = sys.argv[3]
    atv_port = int(sys.argv[4])
    unique_identifier = sys.argv[5].encode()
    zconf = Zeroconf(loop)
    proxy = ProxyMrpAppleTV(loop, credentials, unique_identifier)

    proxy.start(atv_ip_addr, atv_port)
    loop.run_until_complete(
        publish_zeroconf(zconf, local_ip_addr, proxy.port))
    loop.run_forever()


if __name__ == '__main__':
    main(asyncio.get_event_loop())
