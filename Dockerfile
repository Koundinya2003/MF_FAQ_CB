FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code only (.dockerignore excludes frontend + venv)
COPY server.py topic_detection.py ./
COPY "Topic Detection Data.json" ./

# Railway injects PORT; default 8000 for local docker run
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --timeout 120 --workers 1 server:app"]
