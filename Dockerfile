# Copyright (c) 2025 AccelByte Inc. All Rights Reserved.
# This is licensed software from AccelByte Inc, for limitations
# and restrictions contact your company contract manager.

# ----------------------------------------
# Stage 1: Protoc Code Generation
# ----------------------------------------
FROM --platform=$BUILDPLATFORM rvolosatovs/protoc:4.1.0 AS proto-builder

# Set working directory.
WORKDIR /build

# Copy proto sources and generator script.
COPY proto.sh .
COPY proto/ proto/

# Make script executable and run it.
RUN chmod +x proto.sh && \
    ./proto.sh



# ----------------------------------------
# Stage 2: gRPC Gateway Builder
# ----------------------------------------
FROM --platform=$BUILDPLATFORM golang:1.24 AS grpc-gateway-builder

ARG TARGETOS
ARG TARGETARCH
ARG GOOS=$TARGETOS
ARG GOARCH=$TARGETARCH
ARG CGO_ENABLED=0

# Set working directory.
WORKDIR /build

# Copy gateway go module files.
COPY gateway/go.mod gateway/go.sum ./

# Download dependencies.
RUN go mod download

# Copy application code.
COPY gateway/ .

# Copy generated protobuf files from stage 1.
RUN rm -rf pkg/pb
COPY --from=proto-builder /build/gateway/pkg/pb ./pkg/pb

# Build application code.
RUN go build -v -o /output/$TARGETOS/$TARGETARCH/grpc_gateway .



# ----------------------------------------
# Stage 3: Runtime Container
# ----------------------------------------
FROM ubuntu:22.04

ARG TARGETOS
ARG TARGETARCH

# Install Python and Upgrade Pip
RUN apt update && \
    apt install -y --no-install-recommends \
        python3-pip python-is-python3 && \
    python -m pip install --no-cache-dir --upgrade pip && \
    apt upgrade -y && \
    apt dist-upgrade -y && \
    apt purge -y && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

# Keeps Python from generating .pyc files in the container.
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging.
ENV PYTHONUNBUFFERED=1

# Set working directory.
WORKDIR /app

# Install Python dependencies.
COPY requirements.txt .
RUN python -m pip install \
    --no-cache-dir \
    --force-reinstall \
    --requirement requirements.txt

# Copy apidocs code from stage 1.
COPY --from=proto-builder /build/gateway/apidocs ./apidocs

# Copy gateway code from stage 2.
COPY --from=grpc-gateway-builder /output/$TARGETOS/$TARGETARCH/grpc_gateway ./

# Copy other gateway code.
COPY gateway/third_party third_party/

# Copy application code.
COPY src/ .

# Copy generated protobuf files from stage 1.
COPY --from=proto-builder /build/src/ .

# Copy entrypoint script.
COPY wrapper.sh .
RUN chmod +x wrapper.sh

# Plugin Arch gRPC Server Port.
EXPOSE 6565

# gRPC Gateway Port.
EXPOSE 8000

# Prometheus /metrics Web Server Port.
EXPOSE 8080

# Entrypoint.
CMD ["sh", "/app/wrapper.sh"]
