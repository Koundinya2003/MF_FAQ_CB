#!/usr/bin/env bash
# Start FundBot locally — API and frontend from a single process on :8000.
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  echo "Creating virtualenv…"
  python3 -m venv .venv
  .venv/bin/pip install --quiet --upgrade pip
  .venv/bin/pip install --quiet -r requirements-dev.txt
fi

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export PORT="${PORT:-8000}"

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  echo "note: OPENROUTER_API_KEY is not set — answers will be the retrieved text,"
  echo "      unrephrased. Retrieval and citations work exactly the same."
fi

echo "FundBot  → http://localhost:${PORT}"
echo "Health   → http://localhost:${PORT}/api/health"
exec .venv/bin/python -m fundbot.app
