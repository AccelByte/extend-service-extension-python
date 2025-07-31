from google.protobuf import descriptor_pb2 as _descriptor_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from typing import ClassVar as _ClassVar

ACTION_FIELD_NUMBER: _ClassVar[int]
CREATE: Action
DELETE: Action
DESCRIPTOR: _descriptor.FileDescriptor
READ: Action
RESOURCE_FIELD_NUMBER: _ClassVar[int]
UPDATE: Action
action: _descriptor.FieldDescriptor
resource: _descriptor.FieldDescriptor
unknown: Action

class Action(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
