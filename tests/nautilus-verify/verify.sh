#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VERIFIED="$(cat "$SCRIPT_DIR/VERSION")"
INSTALLED=$("$REPO_ROOT/.venv/bin/python" -c "import nautilus_trader; print(nautilus_trader.__version__)")

echo "Verified: $VERIFIED | Installed: $INSTALLED"

if [[ "$VERIFIED" != "$INSTALLED" ]]; then
  echo "VERSION CHANGED — full verification required"
fi

RUST_OK=true
PYTHON_OK=true

echo ""
echo "=== Rust compile tests ==="
if (cd "$SCRIPT_DIR" && cargo test 2>&1); then
  echo "Rust: PASS"
else
  echo "Rust: FAIL"
  RUST_OK=false
fi

echo ""
echo "=== Python tests ==="
if (cd "$SCRIPT_DIR" && "$REPO_ROOT/.venv/bin/python" -m pytest python/ -v 2>&1); then
  echo "Python: PASS"
else
  echo "Python: FAIL"
  PYTHON_OK=false
fi

echo ""
if $RUST_OK && $PYTHON_OK; then
  if [[ "$VERIFIED" != "$INSTALLED" ]]; then
    echo "$INSTALLED" > "$SCRIPT_DIR/VERSION"
    echo "All tests pass. Updated VERSION: $VERIFIED -> $INSTALLED"
  else
    echo "All tests pass. VERSION unchanged ($VERIFIED)."
  fi
else
  echo "FAILURES DETECTED — hallucination rows may be stale for v$INSTALLED"
  exit 1
fi
