"""Implementation of external API for AirPlay."""

import logging
import binascii

from pyatv import const, net
from pyatv.interface import AirPlay

from pyatv.airplay.player import AirPlayPlayer
from pyatv.airplay.srp import SRPAuthHandler
from pyatv.airplay.auth import AuthenticationVerifier

_LOGGER = logging.getLogger(__name__)


class AirPlayAPI(AirPlay):  # pylint: disable=too-few-public-methods
    """Implementation of API for AirPlay support."""

    def __init__(self, config, loop):
        """Initialize a new AirPlayInternal instance."""
        self.config = config
        self.loop = loop
        self.service = self.config.get_service(const.PROTOCOL_AIRPLAY)
        self.identifier = None

    def _get_credentials(self):
        if self.service.credentials is None:
            _LOGGER.debug('No AirPlay credentials loaded')
            return None

        split = self.service.credentials.split(':')
        _LOGGER.debug(
            'Loaded AirPlay credentials: %s',
            self.service.credentials)

        return split[1]

    async def _player(self, session):
        player = AirPlayPlayer(
            self.loop, session, self.config.address, self.service.port)
        http = net.HttpSession(
            session, 'http://{0}:{1}/'.format(
                self.config.address, self.service.port))

        # If credentials have been loaded, do device verification first
        credentials = self._get_credentials()
        if credentials:
            srp = SRPAuthHandler()
            srp.initialize(binascii.unhexlify(credentials))
            verifier = AuthenticationVerifier(http, srp)
            await verifier.verify_authed()

        return player

    async def play_url(self, url, **kwargs):
        """Play media from an URL on the device.

        Note: This method will not yield until the media has finished playing.
        The Apple TV requires the request to stay open during the entire
        play duration.
        """
        # This creates a new ClientSession every time something is played.
        # It is not recommended by aiohttp, but it is the only way not having
        # a dangling connection laying around. So it will have to do for now.
        session = await net.create_session(self.loop)
        try:
            player = await self._player(session)
            position = int(kwargs.get('position', 0))
            return await player.play_url(url, position)
        finally:
            await session.close()
