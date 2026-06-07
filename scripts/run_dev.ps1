# Desenvolvimento local (Windows)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    (Get-Content .env) -replace 'postgresql\+asyncpg://.*', 'postgresql+asyncpg://nexus:nexus_dev_password@localhost:5432/motor_reservas' | Set-Content .env
}

Write-Host "Iniciando stack Docker..."
docker compose up -d db redis
Start-Sleep -Seconds 8

Write-Host "Migracoes..."
$env:DATABASE_URL = "postgresql+asyncpg://nexus:nexus_dev_password@localhost:5432/motor_reservas"
alembic upgrade head

Write-Host "Seed..."
python scripts/seed_data.py

Write-Host "API em http://localhost:8000"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
