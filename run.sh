#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
# Explicit HBASE_HOST always wins. Otherwise use a native Docker bridge address.
if [[ -z "${HBASE_HOST:-}" ]]; then
  container_ip="$(docker inspect -f '{{range.NetworkSettings.Networks}}{{println .IPAddress}}{{end}}' cloudera 2>/dev/null | head -n 1 || true)"
  export HBASE_HOST="${container_ip:-127.0.0.1}"
fi
export HBASE_PORT="${HBASE_PORT:-9090}"
exec .venv/bin/streamlit run app.py "$@"
