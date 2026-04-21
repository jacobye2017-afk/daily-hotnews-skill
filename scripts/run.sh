#!/usr/bin/env bash
# daily-hotnews skill entry point
# Usage: bash run.sh "<用户消息>"

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PY="$SKILL_DIR/venv/bin/python"

# Validate venv
if [ ! -x "$VENV_PY" ]; then
    echo "❌ Python venv not found. Run: cd $SKILL_DIR && python3 -m venv venv && venv/bin/pip install -r requirements.txt"
    exit 1
fi

MESSAGE="${1:-}"

# Dispatch by keyword
cd "$SCRIPT_DIR"
exec "$VENV_PY" main.py "$MESSAGE"
