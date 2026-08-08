# Container image for running FundBot anywhere that is not Vercel
# (Fly.io, Render, Hugging Face Spaces, a VPS, or just `docker run` locally).
# The Vercel deployment does not use this file — it builds api/*.py directly.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Dependencies first so the layer caches across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt "gunicorn>=22,<24"

COPY fundbot/ ./fundbot/
COPY data/ ./data/
COPY public/ ./public/

# Run unprivileged.
RUN useradd --create-home --uid 10001 fundbot && chown -R fundbot:fundbot /app
USER fundbot

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,os,sys; \
sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/health', timeout=4).status == 200 else 1)"

# Two workers is plenty: the index is a few thousand terms held in memory per
# process, and requests are dominated by waiting on the LLM, not by CPU.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 2 --timeout 60 fundbot.wsgi:app"]
