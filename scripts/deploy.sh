#!/usr/bin/env bash
set -euo pipefail

echo "==> Motor de Reservas Nexus Transfer - Deploy"

if [ ! -f .env ]; then
  echo "ERRO: Arquivo .env não encontrado. Copie .env.example para .env"
  exit 1
fi

echo "==> Building Docker image..."
docker compose build api

echo "==> Running migrations..."
docker compose run --rm migrate

echo "==> Starting services..."
docker compose up -d api redis db

echo "==> Health check..."
sleep 5
curl -sf http://localhost:8000/health || { echo "Health check failed"; exit 1; }

echo "==> Deploy concluído: https://engine.transporteexecutivo.com"
