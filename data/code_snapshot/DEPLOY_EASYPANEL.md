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

## Apos deploy

```bash
curl https://api.transporteexecutivo.com/api/v1/public/statistics
curl https://sistema.transporteexecutivo.com/api/health
curl https://driver.transporteexecutivo.com/
curl https://business.transporteexecutivo.com/
```

Log esperado: `[Nexus] Sistema web: https://sistema.transporteexecutivo.com`
