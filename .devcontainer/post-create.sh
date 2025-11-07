#!/bin/bash
set -e

echo "🚀 Setting up development environment..."

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
