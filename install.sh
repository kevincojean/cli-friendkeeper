#!/usr/bin/env bash
set -euo pipefail
PREFIX="${PREFIX:-${1:-$HOME/.local}}"
BIN_NAME="${BIN_NAME:-${BUILD_NAME:-friend}}"
REAL_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
CWRAPPER="$REAL_DIR/ccli"

if [ ! -f "$CWRAPPER" ]; then
    echo "ERROR: ccli not found at $CWRAPPER. Run task T2 first." >&2
    exit 1
fi

mkdir -p "$PREFIX/bin"
cp "$CWRAPPER" "$PREFIX/bin/$BIN_NAME"
chmod +x "$PREFIX/bin/$BIN_NAME"
echo "Installed: $PREFIX/bin/$BIN_NAME"
