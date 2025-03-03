# @generated by generate_proto_mypy_stubs.py.  Do not edit!
import sys
from google.protobuf.descriptor import (
    Descriptor as google___protobuf___descriptor___Descriptor,
    FieldDescriptor as google___protobuf___descriptor___FieldDescriptor,
)

from google.protobuf.message import (
    Message as google___protobuf___message___Message,
)

from typing import (
    Optional as typing___Optional,
)

from typing_extensions import (
    Literal as typing_extensions___Literal,
)


class RegisterHIDDeviceResultMessage(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    errorCode = ... # type: int
    deviceIdentifier = ... # type: int

    def __init__(self,
        *,
        errorCode : typing___Optional[int] = None,
        deviceIdentifier : typing___Optional[int] = None,
        ) -> None: ...
    @classmethod
    def FromString(cls, s: bytes) -> RegisterHIDDeviceResultMessage: ...
    def MergeFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def CopyFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    if sys.version_info >= (3,):
        def HasField(self, field_name: typing_extensions___Literal[u"deviceIdentifier",u"errorCode"]) -> bool: ...
        def ClearField(self, field_name: typing_extensions___Literal[u"deviceIdentifier",u"errorCode"]) -> None: ...
    else:
        def HasField(self, field_name: typing_extensions___Literal[u"deviceIdentifier",b"deviceIdentifier",u"errorCode",b"errorCode"]) -> bool: ...
        def ClearField(self, field_name: typing_extensions___Literal[u"deviceIdentifier",b"deviceIdentifier",u"errorCode",b"errorCode"]) -> None: ...

registerHIDDeviceResultMessage = ... # type: google___protobuf___descriptor___FieldDescriptor
