#!/bin/bash
# Wrapper script for docker commands to handle permission issues in dev containers

# Check if docker socket exists
if [ ! -S /var/run/docker.sock ]; then
    echo "Error: Docker socket not found at /var/run/docker.sock" >&2
    exit 1
fi

# Try to use docker directly first (if user is in docker group)
if docker info >/dev/null 2>&1; then
    exec docker "$@"
fi

# If that fails, try with sudo (passwordless sudo is configured in dev container)
if sudo -n docker info >/dev/null 2>&1; then
    exec sudo docker "$@"
fi

# If both fail, try docker directly anyway (will show the actual error)
exec docker "$@"

