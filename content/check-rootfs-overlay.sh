#!/bin/sh
# Disposable mount probe; never touch rootfs base/upper/work or host config.
set -eu
PROBE=$(mktemp -d /lzcapp/cache/.overlay-preflight.XXXXXX) || exit 1
MOUNTED=0
cleanup() {
  if [ "$MOUNTED" = 1 ]; then
    if ! umount "$PROBE/merged"; then
      echo "[setup] ERROR: cannot unmount overlay probe; left at $PROBE" >&2
      return 1
    fi
    MOUNTED=0
  fi
  rm -rf "$PROBE"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
mkdir "$PROBE/lower" "$PROBE/upper" "$PROBE/work" "$PROBE/merged"
if ! mount -t overlay overlay \
  -o "lowerdir=$PROBE/lower,upperdir=$PROBE/upper,workdir=$PROBE/work" "$PROBE/merged"; then
  echo "[setup] ERROR: overlay mount preflight failed; persistent tools would be hidden." >&2
  echo "[setup] Check effective hermes-webui SYS_ADMIN and host administrator compose override; preserve packaged override requirements. See content/ROOTFS-REPAIR.md." >&2
  exit 1
fi
MOUNTED=1
if ! umount "$PROBE/merged"; then
  echo "[setup] ERROR: overlay preflight unmount failed; refusing startup" >&2
  exit 1
fi
MOUNTED=0
