#!/bin/sh
set -eu
LEASE_SCRIPT="${LEASE_SCRIPT:-/lzcapp/pkg/content/lazycat-ticket-lease.mjs}"
SOCKET_PATH="${SOCKET_PATH:?SOCKET_PATH is required}"
mkdir -p "$(dirname "$SOCKET_PATH")"
exec /usr/local/bin/node "$LEASE_SCRIPT"
