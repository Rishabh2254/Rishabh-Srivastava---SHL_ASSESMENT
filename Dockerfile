FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python scripts/bootstrap_catalog.py || true
RUN python scripts/build_index.py || true

EXPOSE 8000

# Render injects PORT at runtime; bind to 0.0.0.0 on that port.
CMD ["/bin/sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
