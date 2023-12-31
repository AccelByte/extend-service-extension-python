FROM rvolosatovs/protoc:4.1.0 as proto-builder
WORKDIR /.build
COPY proto proto

# protoc-apidocs
RUN mkdir -p /.output/apidocs && \
    protoc \
        --proto_path=proto/app \
        --openapiv2_out /.output/apidocs \
        --openapiv2_opt logtostderr=true \
        --openapiv2_opt use_go_templates=true \
        guildService.proto

# protoc-gateway
RUN mkdir -p /.output/gateway/pkg/pb && \
    protoc \
        --proto_path=proto/app \
        --go_out=/.output/gateway/pkg/pb \
        --go_opt=paths=source_relative \
        --go-grpc_out=require_unimplemented_servers=false:/.output/gateway/pkg/pb \
        --go-grpc_opt=paths=source_relative \
        --grpc-gateway_out=logtostderr=true:/.output/gateway/pkg/pb \
        --grpc-gateway_opt paths=source_relative \
        permission.proto \
        guildService.proto

# protoc-app
RUN mkdir -p /.output/src && \
    protoc \
        --proto_path=google/api=proto/google/api \
        --proto_path=protoc-gen-openapiv2/options=proto/protoc-gen-openapiv2/options \
        --python_out=/.output/src \
        --pyi_out=/.output/src \
        --grpc-python_out=/.output/src \
        google/api/annotations.proto \
        google/api/http.proto \
        protoc-gen-openapiv2/options/annotations.proto \
        protoc-gen-openapiv2/options/openapiv2.proto
RUN mkdir -p /.output/src/app/proto && \
    protoc \
        --proto_path=proto/app \
        --python_out=/.output/src/app/proto \
        --pyi_out=/.output/src/app/proto \
        --grpc-python_out=/.output/src/app/proto \
        permission.proto \
        guildService.proto
RUN sed -i 's/import permission_pb2 as permission__pb2/from . import permission_pb2 as permission__pb2/' \
        /.output/src/app/proto/guildService_pb2.py
RUN sed -i 's/import permission_pb2 as _permission_pb2/from . import permission_pb2 as _permission_pb2/' \
        /.output/src/app/proto/guildService_pb2.pyi
RUN sed -i 's/import guildService_pb2 as guildService__pb2/from . import guildService_pb2 as guildService__pb2/' \
        /.output/src/app/proto/guildService_pb2_grpc.py


FROM golang:1.20-bullseye as gateway-builder
WORKDIR /build
COPY gateway .
COPY proto/app/guildService.proto .
COPY --from=proto-builder /.output/gateway/pkg/pb pkg/pb
RUN sed -i "s/var BasePath = \".*\"/var BasePath = \"\\$(sed -n 's/^.*base_path:\s*"\(\S*\)";.*$/\1/p' guildService.proto)\"/" \
  pkg/common/config.go
RUN sed -i -r "s/pb.Register.*Handler/pb.Register$(sed -n 's/^.*service\s*\(\S*\)\s{.*$/\1/p' guildService.proto)Handler/" \
  pkg/common/gateway.go
RUN go mod tidy
RUN go mod verify
RUN CGO_ENABLED=0 go build -o /.output/gateway extend-grpc-gateway


FROM python:3.9-slim-bullseye
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN apt-get update && \
    apt-get install -y supervisor procps --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*
COPY supervisord.conf /etc/supervisor/supervisord.conf
WORKDIR /build
COPY pyproject.toml pyproject.toml
COPY src src
COPY --from=proto-builder /.output/src src
RUN python -m pip install .
WORKDIR /app
COPY gateway/third_party third_party
COPY --from=proto-builder /.output/apidocs apidocs
COPY --from=gateway-builder /.output/gateway gateway
EXPOSE 6565
EXPOSE 8000
EXPOSE 8080
ENTRYPOINT ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
