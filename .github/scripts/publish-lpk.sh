#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${GITHUB_SHA:?GITHUB_SHA is required}"
: "${LPK:?LPK is required}"
: "${CHECKSUM:?CHECKSUM is required}"
: "${TAG:?TAG is required}"
: "${VERSION:?VERSION is required}"

[[ -f "$LPK" && -f "$CHECKSUM" ]] || { echo '::error::LPK/checksum missing'; exit 1; }
NOTES="$(mktemp)"
cat > "$NOTES" <<NOTES
Automated Hermes Studio LPK build from \`${GITHUB_SHA}\`.

- Version: \`${VERSION}\`
- SHA-256: \`$(awk '{print $1}' "$CHECKSUM")\`

See [CHANGELOG.md](https://github.com/${GITHUB_REPOSITORY}/blob/${GITHUB_SHA}/CHANGELOG.md) for packaged changes.
NOTES

if gh release view "$TAG" >/dev/null 2>&1; then
  gh release edit "$TAG" --target "$GITHUB_SHA" --title "$TAG" --notes-file "$NOTES"
else
  gh release create "$TAG" --target "$GITHUB_SHA" --title "$TAG" --notes-file "$NOTES"
fi
gh release upload "$TAG" "$LPK" "$CHECKSUM" --clobber

VERIFY="$(mktemp -d)"
trap 'rm -rf "$VERIFY" "$NOTES"' EXIT
gh release download "$TAG" --pattern "$(basename "$LPK")" --dir "$VERIFY" --clobber
LOCAL_SHA="$(awk '{print $1}' "$CHECKSUM")"
REMOTE_SHA="$(sha256sum "$VERIFY/$(basename "$LPK")" | awk '{print $1}')"
[[ "$LOCAL_SHA" == "$REMOTE_SHA" ]] || { echo "::error::Release asset checksum mismatch"; exit 1; }
echo "Published and verified $TAG ($REMOTE_SHA)"
