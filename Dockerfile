FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HEALTHCHECK_HOST=engine.transporteexecutivo.com

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt \
    && mv /usr/local/bin/uvicorn /usr/local/bin/_uvicorn_motor

COPY scripts/uvicorn_wrapper.sh /usr/local/bin/uvicorn
RUN chmod +x /usr/local/bin/uvicorn

COPY . .

RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000 8770

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request;t=os.environ.get('NEXUS_DEPLOY_TARGET','').lower();d=os.environ.get('PRIMARY_DOMAIN','')+os.environ.get('EASYPANEL_DOMAIN','');\
s=t=='sistema' or 'api.transporteexecutivo.com' in d;\
urllib.request.urlopen('http://127.0.0.1:8770/api/v1/public/statistics') if s else \
urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/health',headers={'Host':os.environ.get('HEALTHCHECK_HOST','engine.transporteexecutivo.com')}))" || exit 1

ENTRYPOINT ["python", "scripts/docker_entrypoint.py"]
