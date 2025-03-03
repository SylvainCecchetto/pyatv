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


class SendHIDEventMessage(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    hidEventData = ... # type: bytes

    def __init__(self,
        *,
        hidEventData : typing___Optional[bytes] = None,
        ) -> None: ...
    @classmethod
    def FromString(cls, s: bytes) -> SendHIDEventMessage: ...
    def MergeFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def CopyFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    if sys.version_info >= (3,):
        def HasField(self, field_name: typing_extensions___Literal[u"hidEventData"]) -> bool: ...
        def ClearField(self, field_name: typing_extensions___Literal[u"hidEventData"]) -> None: ...
    else:
        def HasField(self, field_name: typing_extensions___Literal[u"hidEventData",b"hidEventData"]) -> bool: ...
        def ClearField(self, field_name: typing_extensions___Literal[u"hidEventData",b"hidEventData"]) -> None: ...

sendHIDEventMessage = ... # type: google___protobuf___descriptor___FieldDescriptor
