#!/usr/bin/env bash
# Start FundBot backend locally (port 8000).
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

# Load .env if present (OPENAI_API_KEY, ALLOWED_ORIGINS, etc.)
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export PORT="${PORT:-8000}"
echo "FundBot API → http://localhost:${PORT}/health"
exec .venv/bin/python server.py
