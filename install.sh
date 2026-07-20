#!/usr/bin/env bash
set -euo pipefail
PREFIX="${PREFIX:-${1:-$HOME/.local}}"
BIN_NAME="${BIN_NAME:-${BUILD_NAME:-friend}}"
REPO_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"

if [ ! -f "$REPO_DIR/ccli" ]; then
    echo "ERROR: ccli not found in $REPO_DIR. Are you running install.sh from the repo root?" >&2
    exit 1
fi

mkdir -p "$PREFIX/bin"

cat > "$PREFIX/bin/$BIN_NAME" << EOF
#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="$REPO_DIR"
PYTHONPATH="\$REPO_DIR/src/python/main"
export PYTHONPATH
exec uv run --project "\$REPO_DIR" python -m cli_friendkeeper.ccli.ccli "\$@"
EOF

chmod +x "$PREFIX/bin/$BIN_NAME"
echo "Installed: $PREFIX/bin/$BIN_NAME"
