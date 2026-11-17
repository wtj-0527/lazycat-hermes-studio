#!/bin/sh
# Keep the conventional Docker endpoint without binding a single socket inode.
set -eu
CLIENT_SOCKET="${DOCKER_CLIENT_SOCKET:-/run/docker.sock}"
RELAY_SOCKET="${DOCKER_RELAY_LISTEN:-/run/hermes-docker/docker.sock}"
if [ -L "$CLIENT_SOCKET" ]; then
  if [ "$(readlink "$CLIENT_SOCKET")" = "$RELAY_SOCKET" ]; then
    exit 0
  fi
elif [ -S "$CLIENT_SOCKET" ]; then
  # Existing administrator overrides can retain the old single-socket bind
  # while replacing the packaged override entirely. Keep that working endpoint.
  echo "[setup] Using existing administrator Docker socket; relay migration is optional for this upgrade." >&2
  exit 0
elif [ ! -e "$CLIENT_SOCKET" ] && [ ! -S "$CLIENT_SOCKET" ]; then
  mkdir -p "$(dirname "$CLIENT_SOCKET")"
  ln -s "$RELAY_SOCKET" "$CLIENT_SOCKET"
  exit 0
fi
echo "[setup] Docker endpoint already exists; leaving it intact. Merge the current packaged compose override and recreate the service to enable the socket relay." >&2
exit 1
