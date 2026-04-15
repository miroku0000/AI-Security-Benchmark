# -*- coding: utf-8 -*-
# Generated manually for gateway.v1 — regenerate with grpc_tools.protoc if needed.
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

_sym_db = _symbol_database.Default()

DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b"\n\rgateway.proto\x12\ngateway.v1\"0\n\x0e\x46orwardRequest\x12\x0c\n\x04path\x18\x01 \x01(\t\x12\x0c\n\x04\x62ody\x18\x02 \x01(\x0c\"3\n\x0f\x46orwardResponse\x12\x0c\n\x04\x62ody\x18\x01 \x01(\x0c\x12\x12\n\x06status\x18\x02 \x01(\x05\x42\x02\x18\x01\x32U\n\x0e\x46orwardService\x12\x43\n\x07\x46orward\x12\x1a.gateway.v1.ForwardRequest\x1a\x1b.gateway.v1.ForwardResponse\"\x00\x62\x06proto3"
)

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, "gateway_pb2", _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
    DESCRIPTOR._options = None
    _globals["FORWARDREQUEST"]._serialized_start = 29
    _globals["FORWARDREQUEST"]._serialized_end = 77
    _globals["FORWARDRESPONSE"]._serialized_start = 79
    _globals["FORWARDRESPONSE"]._serialized_end = 130
    _globals["FORWARDSERVICE"]._serialized_start = 132
    _globals["FORWARDSERVICE"]._serialized_end = 217
