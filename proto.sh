#!/bin/bash

set -eou pipefail

shopt -s globstar

clean_generated_files() {
  find "$1" -type f \( \
    -name '*_pb2.py' -o \
    -name '*_pb2.pyi' -o \
    -name '*_pb2_grpc.py' -o \
    -name '*_grpc.py' -o \
    -name '*.pyc' \
  \) -delete

  find "$1" -type d -name '__pycache__' -exec rm -rf {} +
}

PROTO_DIR="${1:-proto}"
OUT_DIR="${2:-src}"
GATEWAY_DIR="${3:-gateway/pkg/pb}"
APIDOCS_DIR="${4:-gateway/apidocs}"

# Ensure output directory exists.
mkdir -p "${OUT_DIR}"

# Clean previously generated files.
clean_generated_files "${OUT_DIR}"

# Generate protobuf files.
protoc-wrapper \
  -I"${PROTO_DIR}" \
  --python_out="${OUT_DIR}" \
  --pyi_out="${OUT_DIR}" \
  --grpc-python_out="${OUT_DIR}" \
  "${PROTO_DIR}"/**/*.proto

# Clean previously generated files.
rm -rf "${GATEWAY_DIR}"/* && \
  mkdir -p "${GATEWAY_DIR}"

# Generate gateway code.
protoc-wrapper \
  -I"${PROTO_DIR}" \
  --go_out="${GATEWAY_DIR}" \
  --go_opt=paths=source_relative \
  --go-grpc_out=require_unimplemented_servers=false:"${GATEWAY_DIR}" \
  --go-grpc_opt=paths=source_relative \
  --grpc-gateway_out=logtostderr=true:"${GATEWAY_DIR}" \
  --grpc-gateway_opt paths=source_relative \
  "${PROTO_DIR}"/*.proto

# Clean previously generated files.
rm -rf "${APIDOCS_DIR}"/* && \
  mkdir -p "${APIDOCS_DIR}"

# Generate swagger.json file.
protoc-wrapper \
  -I"${PROTO_DIR}" \
  --openapiv2_out "${APIDOCS_DIR}" \
  --openapiv2_opt logtostderr=true \
  --openapiv2_opt use_go_templates=true \
  "${PROTO_DIR}"/*.proto

# Remove google directory since the protobuf package already includes it.
rm -rf src/google
