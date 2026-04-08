#!/usr/bin/env bash
# Build logo.icns from logo.png (macOS only). Uses sips + iconutil.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
SRC="${ROOT}/logo.png"
OUT="${ROOT}/logo.icns"
SET="${ROOT}/logo.iconset"

if [[ ! -f "$SRC" ]]; then
  echo "ERROR: logo.png not found at ${SRC}" >&2
  exit 1
fi

if ! command -v sips &>/dev/null || ! command -v iconutil &>/dev/null; then
  echo "ERROR: sips/iconutil not found (run on macOS)." >&2
  exit 1
fi

rm -rf "$SET"
mkdir -p "$SET"

# Sizes required for a valid .icns (see iconutil(1))
sips -z 16 16     "$SRC" --out "$SET/icon_16x16.png"
sips -z 32 32     "$SRC" --out "$SET/icon_16x16@2x.png"
sips -z 32 32     "$SRC" --out "$SET/icon_32x32.png"
sips -z 64 64     "$SRC" --out "$SET/icon_32x32@2x.png"
sips -z 128 128   "$SRC" --out "$SET/icon_128x128.png"
sips -z 256 256   "$SRC" --out "$SET/icon_128x128@2x.png"
sips -z 256 256   "$SRC" --out "$SET/icon_256x256.png"
sips -z 512 512   "$SRC" --out "$SET/icon_256x256@2x.png"
sips -z 512 512   "$SRC" --out "$SET/icon_512x512.png"
sips -z 1024 1024 "$SRC" --out "$SET/icon_512x512@2x.png"

iconutil -c icns "$SET" -o "$OUT"
rm -rf "$SET"
echo "Wrote $OUT"
