FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV SERVICE_TARGET=app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY adk_app ./adk_app
COPY workspace_service ./workspace_service

RUN printf '%s\n' \
  '#!/usr/bin/env sh' \
  'if [ "$SERVICE_TARGET" = "workspace_service" ]; then' \
  '  exec uvicorn workspace_service.main:app --host 0.0.0.0 --port 8080' \
  'else' \
  '  exec uvicorn app.main:app --host 0.0.0.0 --port 8080' \
  'fi' > /app/run-service.sh \
  && chmod +x /app/run-service.sh

CMD ["/app/run-service.sh"]
