# Deploy EasyPanel — 5 dominios

## Servico 1: Sistema Master (`sistema_do_projeto`)

Compose: `docker-compose.sistema.yml` · Portas: **8770, 8772, 8765, 8766**

| Dominio | Porta |
|---------|-------|
| `api.transporteexecutivo.com` | 8770 |
| `sistema.transporteexecutivo.com` | 8772 |
| `driver.transporteexecutivo.com` | 8765 |
| `business.transporteexecutivo.com` | 8766 |

Env obrigatorio: `NEXUS_DEPLOY_TARGET=sistema`

Ver `.env.sistema.example` para URLs publicas.

## Servico 2: Motor (`transporteexecutivo_com`)

Dockerfile padrao · Porta **8000** · Dominio `engine.transporteexecutivo.com`

## Rebuild obrigatorio (nao basta reiniciar)

Se o log mostrar `admin_login` + `libtk8.6.so`, a imagem esta **antiga**.

1. EasyPanel → servico `sistema_do_projeto` → **Implantar** (rebuild completo)
2. Confirmar: repositorio GitHub, branch **`main`**, Dockerfile **`Dockerfile.sistema`**
3. Comando/Argumentos customizados: **vazio**
4. `NEXUS_DEPLOY_TARGET=sistema`

## Validar na VPS

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"

# Troque pelo container mais novo
docker exec NOME_CONTAINER head -12 /app/app/sistema_web.py
docker exec NOME_CONTAINER test -f /app/app/admin_auth.py && echo admin_auth OK
docker logs NOME_CONTAINER --tail 15
```

Linha 10 de `sistema_web.py` deve ser: `from .admin_auth import authenticate_admin`

## Apos deploy

```bash
curl https://api.transporteexecutivo.com/api/v1/public/statistics
curl https://sistema.transporteexecutivo.com/api/health
curl https://driver.transporteexecutivo.com/
curl https://business.transporteexecutivo.com/
```

Log esperado:

```
[Nexus] Bundle sistema validado — build 2026.08.11
[Nexus] Sistema web: https://sistema.transporteexecutivo.com
```
