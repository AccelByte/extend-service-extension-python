from google.protobuf import descriptor_pb2 as _descriptor_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from typing import ClassVar as _ClassVar

DESCRIPTOR: _descriptor.FileDescriptor

class Action(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    unknown: _ClassVar[Action]
    CREATE: _ClassVar[Action]
    READ: _ClassVar[Action]
    UPDATE: _ClassVar[Action]
    DELETE: _ClassVar[Action]
unknown: Action
CREATE: Action
READ: Action
UPDATE: Action
DELETE: Action
RESOURCE_FIELD_NUMBER: _ClassVar[int]
resource: _descriptor.FieldDescriptor
ACTION_FIELD_NUMBER: _ClassVar[int]
action: _descriptor.FieldDescriptor
