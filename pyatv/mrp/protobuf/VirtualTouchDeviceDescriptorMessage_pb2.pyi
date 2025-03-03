# @generated by generate_proto_mypy_stubs.py.  Do not edit!
import sys
from google.protobuf.descriptor import (
    Descriptor as google___protobuf___descriptor___Descriptor,
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


class VirtualTouchDeviceDescriptor(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    absolute = ... # type: bool
    integratedDisplay = ... # type: bool
    screenSizeWidth = ... # type: float
    screenSizeHeight = ... # type: float

    def __init__(self,
        *,
        absolute : typing___Optional[bool] = None,
        integratedDisplay : typing___Optional[bool] = None,
        screenSizeWidth : typing___Optional[float] = None,
        screenSizeHeight : typing___Optional[float] = None,
        ) -> None: ...
    @classmethod
    def FromString(cls, s: bytes) -> VirtualTouchDeviceDescriptor: ...
    def MergeFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def CopyFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    if sys.version_info >= (3,):
        def HasField(self, field_name: typing_extensions___Literal[u"absolute",u"integratedDisplay",u"screenSizeHeight",u"screenSizeWidth"]) -> bool: ...
        def ClearField(self, field_name: typing_extensions___Literal[u"absolute",u"integratedDisplay",u"screenSizeHeight",u"screenSizeWidth"]) -> None: ...
    else:
        def HasField(self, field_name: typing_extensions___Literal[u"absolute",b"absolute",u"integratedDisplay",b"integratedDisplay",u"screenSizeHeight",b"screenSizeHeight",u"screenSizeWidth",b"screenSizeWidth"]) -> bool: ...
        def ClearField(self, field_name: typing_extensions___Literal[u"absolute",b"absolute",u"integratedDisplay",b"integratedDisplay",u"screenSizeHeight",b"screenSizeHeight",u"screenSizeWidth",b"screenSizeWidth"]) -> None: ...
