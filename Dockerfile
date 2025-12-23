# Copyright (c) 2025 AccelByte Inc. All Rights Reserved.
# This is licensed software from AccelByte Inc, for limitations
# and restrictions contact your company contract manager.

# ----------------------------------------
# Stage 1: Protoc Code Generation
# ----------------------------------------
FROM --platform=$BUILDPLATFORM ubuntu:22.04 AS proto-builder

# Avoid warnings by switching to noninteractive
ENV DEBIAN_FRONTEND=noninteractive

ARG PROTOC_VERSION=21.9
ARG PYTHON_VERSION=3.10
ARG GO_VERSION=1.24.10

# Configure apt and install packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    #
    # Install essential development tools
    build-essential \
    ca-certificates \
    git \
    unzip \
    wget \
    #
    # Install Python and pip
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-dev \
    python${PYTHON_VERSION}-venv \
    python3-pip \
    #
    # Detect architecture for downloads
    && ARCH_SUFFIX=$(case "$(uname -m)" in \
        x86_64) echo "x86_64" ;; \
        aarch64) echo "aarch_64" ;; \
        *) echo "x86_64" ;; \
       esac) \
    && GOARCH_SUFFIX=$(case "$(uname -m)" in \
        x86_64) echo "amd64" ;; \
        aarch64) echo "arm64" ;; \
        *) echo "amd64" ;; \
       esac) \
    #
    # Install Protocol Buffers compiler
    && wget -O protoc.zip https://github.com/protocolbuffers/protobuf/releases/download/v${PROTOC_VERSION}/protoc-${PROTOC_VERSION}-linux-${ARCH_SUFFIX}.zip \
    && unzip protoc.zip -d /usr/local \
    && rm protoc.zip \
    && chmod +x /usr/local/bin/protoc \
    #
    # Install Go
    && wget -O go.tar.gz https://go.dev/dl/go${GO_VERSION}.linux-${GOARCH_SUFFIX}.tar.gz \
    && tar -C /usr/local -xzf go.tar.gz \
    && rm go.tar.gz \
    #
    # Clean up
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Set up Python symlinks
RUN ln -sf /usr/bin/python${PYTHON_VERSION} /usr/local/bin/python3 \
    && ln -sf /usr/bin/python${PYTHON_VERSION} /usr/local/bin/python \
    && ln -sf /usr/bin/pip3 /usr/local/bin/pip

# Install Python tools required for proto generation.
RUN pip install --no-cache-dir grpcio-tools==1.76.0 mypy-protobuf==4.0.0

# Set up Go environment
ENV GOROOT=/usr/local/go
ENV GOPATH=/go
ENV PATH=$GOPATH/bin:$GOROOT/bin:$PATH

# Install protoc Go tools and plugins
RUN go install -v google.golang.org/protobuf/cmd/protoc-gen-go@latest \
    && go install -v google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest \
    && go install -v github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-grpc-gateway@latest \
    && go install -v github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-openapiv2@latest

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
# Stage 3: gRPC Server Builder
# ----------------------------------------
FROM ubuntu:22.04 AS grpc-server-builder

ARG TARGETOS
ARG TARGETARCH

# Keeps Python from generating .pyc files in the container.
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging.
ENV PYTHONUNBUFFERED=1

# Install Python.
RUN apt update && \
    apt install -y --no-install-recommends \
        python3-venv && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

RUN useradd user

# Set working directory.
WORKDIR /build

# Create and activate virtual environment.
RUN python3 -m venv venv
ENV PATH="/build/venv/bin:$PATH"

# Install Python dependencies.
COPY requirements.txt .
RUN python3 -m pip install \
    --no-cache-dir \
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

# Fix up python3 symlink for use in chiseled Ubuntu.
RUN ln -sf /usr/bin/python3 /build/venv/bin/python3 



# ----------------------------------------
# Stage 4: Runtime Container
# ----------------------------------------
FROM ubuntu/python:3.10-22.04_stable

# Keeps Python from generating .pyc files in the container.
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging.
ENV PYTHONUNBUFFERED=1

# Set working directory.
WORKDIR /app

# Copy build from stage 2.
COPY --from=grpc-server-builder /usr/bin/bash /usr/bin/bash
COPY --from=grpc-server-builder /usr/bin/kill /usr/bin/kill
COPY --from=grpc-server-builder /usr/bin/sleep /usr/bin/sleep
COPY --from=grpc-server-builder /etc/passwd /etc/passwd
COPY --from=grpc-server-builder /etc/group /etc/group
COPY --from=grpc-server-builder /build/ .

USER user

# Activate virtual environment.
ENV PATH="/app/venv/bin:$PATH"

# Plugin Arch gRPC Server Port.
EXPOSE 6565

# gRPC Gateway Port.
EXPOSE 8000

# Prometheus /metrics Web Server Port.
EXPOSE 8080

# Entrypoint.
ENTRYPOINT ["bash", "/app/wrapper.sh"]
