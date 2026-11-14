#!/usr/bin/env bash
set -euo pipefail
app_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -x "$app_dir/.venv/bin/python" ]]; then
    exec "$app_dir/.venv/bin/python" "$app_dir/main.py" "$@"
fi
exec python3 "$app_dir/main.py" "$@"
