#!/usr/bin/env bash
set -euo pipefail

ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
cd "$ROOT"

command -v lzc-cli >/dev/null 2>&1 || { echo '::error::lzc-cli is required'; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo '::error::python3 is required'; exit 1; }

VERSION="$(python3 - <<'PY'
from pathlib import Path
import re
text = Path('package.yml').read_text(encoding='utf-8')
match = re.search(r'^version:\s*([^\s#]+)', text, re.MULTILINE)
if not match:
    raise SystemExit('package.yml missing version')
print(match.group(1))
PY
)"
PACKAGE_ID="$(python3 - <<'PY'
from pathlib import Path
import re
text = Path('package.yml').read_text(encoding='utf-8')
match = re.search(r'^package:\s*([^\s#]+)', text, re.MULTILINE)
if not match:
    raise SystemExit('package.yml missing package id')
print(match.group(1))
PY
)"

[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]] || {
  echo "::error::package.yml version is not accepted: $VERSION"
  exit 1
}

# Build only from immutable, explicit image references. Mutable latest tags make
# an LPK impossible to reproduce and may change after release verification.
mapfile -t APP_IMAGES < <(python3 - <<'PY'
from pathlib import Path
import re
for line in Path('lzc-manifest.yml').read_text(encoding='utf-8').splitlines():
    match = re.match(r'^\s+image:\s*([^\s#]+)', line)
    if match:
        print(match.group(1))
PY
)
mapfile -t APP_IMAGES < <(printf '%s\n' "${APP_IMAGES[@]}" | LC_ALL=C sort -u)
if ((${#APP_IMAGES[@]} == 0)); then
  echo '::error::No service images found in lzc-manifest.yml'
  exit 1
fi
for image in "${APP_IMAGES[@]}"; do
  case "$image" in
    *:latest|*:main|*':<none>') echo "::error::Mutable image tag is not allowed: $image"; exit 1 ;;
  esac
  echo "Checking image: $image"
  docker buildx imagetools inspect "$image" >/dev/null
 done

mkdir -p content lpk
find lpk -maxdepth 1 -type f -name '*.lpk' -delete

lzc-cli project lint .
lzc-cli project release .

mapfile -t PACKAGES < <(find lpk -maxdepth 1 -type f -name '*.lpk' -print | LC_ALL=C sort)
if ((${#PACKAGES[@]} != 1)); then
  echo "::error::Expected exactly one LPK, found ${#PACKAGES[@]}"
  exit 1
fi
LPK="${PACKAGES[0]}"
EXPECTED="lpk/${PACKAGE_ID}-v${VERSION}.lpk"
if [[ "$LPK" != "$EXPECTED" ]]; then
  echo "::error::Unexpected LPK name: $LPK (expected $EXPECTED)"
  exit 1
fi

for entry in manifest.yml package.yml compose.override.yml content.tar icon.png; do
  tar -tf "$LPK" | grep -qx "$entry" || { echo "::error::$entry missing from LPK"; exit 1; }
done

python3 - "$LPK" "$PACKAGE_ID" "$VERSION" <<'PY'
import io, re, sys, tarfile
lpk, expected_id, expected_version = sys.argv[1:]
with tarfile.open(lpk, 'r:*') as archive:
    package = archive.extractfile('package.yml').read().decode('utf-8')
    manifest = archive.extractfile('manifest.yml').read().decode('utf-8')
package_id = re.search(r'^package:\s*([^\s#]+)', package, re.MULTILINE)
version = re.search(r'^version:\s*([^\s#]+)', package, re.MULTILINE)
if not package_id or package_id.group(1) != expected_id:
    raise SystemExit('Packaged package id does not match source package.yml')
if not version or version.group(1) != expected_version:
    raise SystemExit('Packaged version does not match source package.yml')
source_images = sorted(re.findall(r'^\s+image:\s*([^\s#]+)', open('lzc-manifest.yml', encoding='utf-8').read(), re.MULTILINE))
packed_images = sorted(re.findall(r'^\s+image:\s*([^\s#]+)', manifest, re.MULTILINE))
if source_images != packed_images:
    raise SystemExit('Packaged image list does not match source manifest')
print(f'Verified package metadata and {len(packed_images)} image references')
PY

lzc-cli lpk info "$LPK"
if ! lzc-cli lpk lint "$LPK"; then
  echo "::warning::LPK has App Store policy warnings; the verified side-load package is still produced"
fi
SHA256="$(sha256sum "$LPK" | awk '{print $1}')"
SIZE="$(stat -c '%s' "$LPK")"
printf '%s  %s\n' "$SHA256" "$(basename "$LPK")" > "${LPK}.sha256"

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  {
    echo "package=$LPK"
    echo "checksum=${LPK}.sha256"
    echo "package_name=$(basename "$LPK")"
    echo "version=$VERSION"
    echo "tag=v$VERSION"
    echo "sha256=$SHA256"
    echo "size=$SIZE"
  } >> "$GITHUB_OUTPUT"
fi
printf 'LPK=%s\nVERSION=%s\nSHA256=%s\nSIZE=%s\n' "$LPK" "$VERSION" "$SHA256" "$SIZE"
