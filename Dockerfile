# Parole Patente B: flip-card app with persistent progress sync.
FROM python:3.12-alpine

WORKDIR /app

COPY docker/server.py /app/server.py
COPY app/index.html /app/index.html

ENV PORT=80 \
    DATA_DIR=/data \
    PYTHONUNBUFFERED=1

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:80/health || exit 1

CMD ["python3", "/app/server.py"]
