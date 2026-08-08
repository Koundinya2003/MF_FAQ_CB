"""Vercel function for POST /api/search — retrieval-only debug view.

Returns 404 unless FUNDBOT_DEBUG is set, so it is inert in a normal deployment.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fundbot.wsgi import app  # noqa: E402,F401
