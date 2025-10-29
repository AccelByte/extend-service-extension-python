# Development container for AccelByte Extend Service Extension
FROM ubuntu:22.04

# Avoid warnings by switching to noninteractive
ENV DEBIAN_FRONTEND=noninteractive

# Configure apt and install packages
RUN apt-get update \
    #
    # Install essential development tools
    && apt-get -y install \
    git \
    build-essential \
    sudo \
    wget \
    unzip \
    #
    # Install Protocol Buffers compiler
    && PROTOC_VERSION=21.9 \
    && wget -O protoc.zip https://github.com/protocolbuffers/protobuf/releases/download/v${PROTOC_VERSION}/protoc-${PROTOC_VERSION}-linux-x86_64.zip \
    && unzip protoc.zip -d /usr/local \
    && rm protoc.zip \
    && chmod +x /usr/local/bin/protoc \
    #
    # Install Python 3.10 and pip
    && apt-get -y install \
    python3.10 \
    python3.10-dev \
    python3.10-venv \
    python3-pip \
    #
    # Install Go 1.24
    && wget -O go.tar.gz https://go.dev/dl/go1.24.9.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go.tar.gz \
    && rm go.tar.gz \
    #
    # Clean up
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Set up Go environment
ENV GOROOT=/usr/local/go
ENV GOPATH=/go
ENV PATH=$GOPATH/bin:$GOROOT/bin:$PATH

# Create a non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Create workspace and GOPATH directories
RUN mkdir -p /workspace && chown $USERNAME:$USERNAME /workspace \
    && mkdir -p /go && chown $USERNAME:$USERNAME /go

# Switch to non-root user
USER $USERNAME

# Set up Python symlinks for the user
RUN sudo ln -sf /usr/bin/python3.10 /usr/local/bin/python3 \
    && sudo ln -sf /usr/bin/python3.10 /usr/local/bin/python

# Install Go Language Server (required by Go extension)
RUN go install -v golang.org/x/tools/gopls@latest

# Install Go Debugger
RUN go install -v github.com/go-delve/delve/cmd/dlv@latest

# Install protoc Go tools and plugins
RUN go install -v google.golang.org/protobuf/cmd/protoc-gen-go@latest \
    && go install -v google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest \
    && go install -v github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-grpc-gateway@latest \
    && go install -v github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-openapiv2@latest

# Switch back to dialog for any ad-hoc use of apt-get
ENV DEBIAN_FRONTEND=dialog

WORKDIR /workspace
