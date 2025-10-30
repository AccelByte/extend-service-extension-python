#!/bin/bash
set -e

echo "🚀 Setting up development environment..."

# Fix Docker socket permissions if mounted
if [ -S /var/run/docker.sock ]; then
    echo "🔧 Configuring Docker socket access..."
    DOCKER_GID=$(stat -c '%g' /var/run/docker.sock 2>/dev/null || echo "")
    if [ -n "$DOCKER_GID" ] && [ "$DOCKER_GID" != "65534" ]; then
        # Get current docker group GID if it exists
        EXISTING_DOCKER_GID=$(getent group docker | cut -d: -f3 2>/dev/null || echo "")
        
        if [ -z "$EXISTING_DOCKER_GID" ]; then
            # Create docker group with correct GID
            sudo groupadd -g "$DOCKER_GID" docker 2>/dev/null || true
        elif [ "$EXISTING_DOCKER_GID" != "$DOCKER_GID" ]; then
            # Update docker group GID to match socket
            sudo groupmod -g "$DOCKER_GID" docker 2>/dev/null || true
        fi
        
        # Ensure current user is in docker group
        if ! groups "$USER" | grep -q docker; then
            sudo usermod -aG docker "$USER" 2>/dev/null || true
        fi
        
        echo "✅ Docker group configured (GID: $DOCKER_GID)"
        echo "⚠️  Note: Docker group membership requires container restart to take effect"
        echo "   The docker-wrapper.sh script will handle permissions until then"
    fi
fi

# Ensure docker wrapper is executable
if [ -f .devcontainer/docker-wrapper.sh ]; then
    chmod +x .devcontainer/docker-wrapper.sh
    echo "✅ Docker wrapper script is executable"
fi

# Create Python virtual environment if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt

# Install Go dependencies
echo "📦 Installing Go dependencies..."
cd gateway
go mod download
cd ..

# Make scripts executable
echo "🔧 Setting up scripts..."
chmod +x proto.sh
chmod +x wrapper.sh
chmod +x .devcontainer/proto.sh

# Generate protobuf files
echo "✏️ Generating protocol buffer files..."
if command -v protoc &> /dev/null; then
    .devcontainer/proto.sh || echo "⚠️  Protocol buffer generation skipped"
else
    echo "⚠️  protoc not found"
fi

# Configure git for safe directory
if [ -d ".git" ]; then
    echo "🔧 Setting up git..."
    git config --global --add safe.directory /workspace
fi

echo "✅ Development environment setup complete!"
echo ""
echo "🎯 Quick start commands:"
echo "  • Activate Python venv: source venv/bin/activate"
echo "  • Run Python service: python -m app"
echo "  • Build Go gateway: cd gateway && go build"
echo "  • Generate protobuf: ./proto.sh"
echo ""
echo "🛟 Ports:"
echo "  • gRPC Server: 6565"
echo "  • gRPC Gateway: 8000"
echo "  • Prometheus Metrics: 8080"
