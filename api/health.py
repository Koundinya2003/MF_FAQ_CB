"""Vercel function for GET /api/health."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fundbot.wsgi import app  # noqa: E402,F401
