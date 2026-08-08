"""Vercel function for POST /api/ask."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fundbot.wsgi import app  # noqa: E402,F401
