# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: permission.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from google.protobuf import descriptor_pb2 as google_dot_protobuf_dot_descriptor__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x10permission.proto\x12\npermission\x1a google/protobuf/descriptor.proto*C\n\x06\x41\x63tion\x12\x0b\n\x07unknown\x10\x00\x12\n\n\x06\x43REATE\x10\x01\x12\x08\n\x04READ\x10\x02\x12\n\n\x06UPDATE\x10\x04\x12\n\n\x06\x44\x45LETE\x10\x08:2\n\x08resource\x12\x1e.google.protobuf.MethodOptions\x18\xd1\x86\x03 \x01(\t:D\n\x06\x61\x63tion\x12\x1e.google.protobuf.MethodOptions\x18\xd2\x86\x03 \x01(\x0e\x32\x12.permission.ActionBt\n%net.accelbyte.extend.serviceextensionP\x01Z%accelbyte.net/extend/serviceextension\xaa\x02!AccelByte.Extend.ServiceExtensionb\x06proto3')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'permission_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:
  google_dot_protobuf_dot_descriptor__pb2.MethodOptions.RegisterExtension(resource)
  google_dot_protobuf_dot_descriptor__pb2.MethodOptions.RegisterExtension(action)

  DESCRIPTOR._options = None
  DESCRIPTOR._serialized_options = b'\n%net.accelbyte.extend.serviceextensionP\001Z%accelbyte.net/extend/serviceextension\252\002!AccelByte.Extend.ServiceExtension'
  _ACTION._serialized_start=66
  _ACTION._serialized_end=133
# @@protoc_insertion_point(module_scope)
