#!/usr/bin/env bash
# Build a single-file macOS GUI executable (logo bundled; put serviceAccountKey.json next to the binary).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script must run on macOS." >&2
  exit 1
fi

if [[ ! -f "logo.png" ]]; then
  echo "ERROR: logo.png must exist in the project root." >&2
  exit 1
fi

if bash scripts/make_logo_icns.sh; then
  :
else
  echo "WARN: logo.icns not created; PyInstaller will use default icon." >&2
fi

python3 -m PyInstaller --noconfirm --clean dawa_whatsapp.spec

echo ""
echo "Built: dist/DawaWhatsApp"
echo "Copy serviceAccountKey.json next to that binary if you use Firebase."
echo "Gatekeeper: you may need to allow the app in System Settings > Privacy & Security."
