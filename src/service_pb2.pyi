from google.api import annotations_pb2 as _annotations_pb2
from protoc_gen_openapiv2.options import annotations_pb2 as _annotations_pb2_1
import permission_pb2 as _permission_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CreateOrUpdateGuildProgressRequest(_message.Message):
    __slots__ = ("namespace", "guild_progress")
    NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    GUILD_PROGRESS_FIELD_NUMBER: _ClassVar[int]
    namespace: str
    guild_progress: GuildProgress
    def __init__(self, namespace: _Optional[str] = ..., guild_progress: _Optional[_Union[GuildProgress, _Mapping]] = ...) -> None: ...

class CreateOrUpdateGuildProgressResponse(_message.Message):
    __slots__ = ("guild_progress",)
    GUILD_PROGRESS_FIELD_NUMBER: _ClassVar[int]
    guild_progress: GuildProgress
    def __init__(self, guild_progress: _Optional[_Union[GuildProgress, _Mapping]] = ...) -> None: ...

class GetGuildProgressRequest(_message.Message):
    __slots__ = ("namespace", "guild_id")
    NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    GUILD_ID_FIELD_NUMBER: _ClassVar[int]
    namespace: str
    guild_id: str
    def __init__(self, namespace: _Optional[str] = ..., guild_id: _Optional[str] = ...) -> None: ...

class GetGuildProgressResponse(_message.Message):
    __slots__ = ("guild_progress",)
    GUILD_PROGRESS_FIELD_NUMBER: _ClassVar[int]
    guild_progress: GuildProgress
    def __init__(self, guild_progress: _Optional[_Union[GuildProgress, _Mapping]] = ...) -> None: ...

class GuildProgress(_message.Message):
    __slots__ = ("guild_id", "namespace", "objectives")
    class ObjectivesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...
    GUILD_ID_FIELD_NUMBER: _ClassVar[int]
    NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    OBJECTIVES_FIELD_NUMBER: _ClassVar[int]
    guild_id: str
    namespace: str
    objectives: _containers.ScalarMap[str, int]
    def __init__(self, guild_id: _Optional[str] = ..., namespace: _Optional[str] = ..., objectives: _Optional[_Mapping[str, int]] = ...) -> None: ...
