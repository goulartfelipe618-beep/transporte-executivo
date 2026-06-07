@echo off
cd /d "%~dp0"
set NEXUS_BIND_HOST=0.0.0.0
set INTEGRACAO_GATEWAY_HOST=0.0.0.0
echo Nexus Transfer - Servidor Producao (headless)
python scripts\run_production_server.py
pause
