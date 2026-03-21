#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DOCS_DIR="$SCRIPT_DIR/../references/docs"

if [ -d "$DOCS_DIR" ]; then
  echo "Docs already present at $DOCS_DIR"
  exit 0
fi

echo "Fetching NautilusTrader docs..."

TEMP=$(mktemp -d)
trap 'rm -rf "$TEMP"' EXIT

git clone --filter=blob:none --sparse --depth 1 \
  https://github.com/nautechsystems/nautilus_trader.git "$TEMP"
git -C "$TEMP" sparse-checkout set docs/

rm -rf "$TEMP/docs/api_reference"
mv "$TEMP/docs" "$DOCS_DIR"

echo "Done. Docs installed to $DOCS_DIR"
