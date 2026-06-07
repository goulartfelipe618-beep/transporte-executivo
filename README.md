# Motor de Reservas Nexus Transfer

Motor de reservas independente da plataforma Transporte Executivo.

**URL de produção:** https://engine.transporteexecutivo.com

**Link de parceiro:** `https://engine.transporteexecutivo.com/{partner_id}/{partner_token}`

Exemplo: https://engine.transporteexecutivo.com/net-000001/a8x72mkq9

---

## Arquitetura

Este projeto é o **terceiro sistema** do ecossistema:

| Sistema | Responsabilidade |
|---------|------------------|
| Sistema Master (backoffice) | Fonte oficial de dados operacionais |
| Website institucional (Django) | SEO, captação, conteúdo público |
| **Motor de Reservas (este projeto)** | Reservas via rede de parceiros |

### Regras de integração

- **Não** acessa `app_state.json`, Portal Empresa ou Portal Motorista
- Comunicação com o Master **somente via HTTP API**
- Website **não** acessa o banco deste motor diretamente

### Cliente Master (desacoplado)

```
GET  /api/v1/public/stats
GET  /api/v1/public/coverage
GET  /api/v1/public/locations
GET  /api/v1/public/vehicles
POST /api/v1/webhooks/inbound/reservation.request
```

Implementação: `app/clients/master_api.py`

---

## Stack

- Python 3.12+
- FastAPI + Jinja2 (frontend mobile-first)
- SQLAlchemy 2 (async) + PostgreSQL / Supabase
- JWT + Refresh Token, CSRF, Rate Limit, bcrypt
- Redis (cache opcional)
- Docker + Alembic

---

## Estrutura

```
app/
  api/          # REST API (v1, partner, admin)
  web/          # Rotas HTML (booking, parceiro)
  models/       # SQLAlchemy (UUID em todas entidades)
  services/     # Regras de negócio
  clients/      # Master API HTTP
  security/     # JWT, CSRF, bcrypt, sanitização
  templates/    # Jinja2
  static/       # CSS/JS premium
alembic/        # Migrations
supabase/       # RLS policies
scripts/        # seed, deploy
tests/          # pytest
```

---

## Início rápido

### 1. Variáveis de ambiente

```bash
cp .env.example .env
# Edite DATABASE_URL, SECRET_KEY, JWT_SECRET_KEY, CSRF_SECRET_KEY
```

### 2. Docker Compose

```bash
docker compose up -d db redis
# Ajuste DATABASE_URL no .env:
# postgresql+asyncpg://nexus:nexus_dev_password@localhost:5432/motor_reservas

alembic upgrade head
python scripts/seed_data.py
uvicorn app.main:app --reload
```

### 3. Windows (script)

```powershell
.\scripts\run_dev.ps1
```

### 4. Deploy

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

---

## Fluxo de reserva

1. **Buscar** — origem, destino, data, horário, passageiros, bagagens
2. **Veículos** — cards com foto, categoria, benefícios, valor
3. **Seleção** — confirma veículo
4. **Passageiro** — nome, telefone, e-mail, CPF, observações
5. **Pagamento** — Mercado Pago / Stripe / PIX (estrutura preparada)
6. **Confirmação** — código, QR Code, PDF, e-mail

Comissão calculada automaticamente: `valor × percentual / 100`

---

## Painéis

| URL | Função |
|-----|--------|
| `/partner` | Login, reservas, comissões, extrato |
| `/admin` | Parceiros, reservas, financeiro, logs |

API:

- `POST /api/partner/auth/login`
- `GET  /api/partner/dashboard`
- `POST /api/admin/auth/login`
- `GET  /api/admin/partners`

---

## Credenciais de desenvolvimento (seed)

| Tipo | E-mail | Senha |
|------|--------|-------|
| Admin | admin@nexus.local | Admin@123 |
| Parceiro | parceiro@demo.local | Parceiro@123 |

Link parceiro demo: http://localhost:8000/net-000001/a8x72mkq9

---

## Banco de dados

Tabelas principais:

- `partners`, `partner_sessions`, `partner_commissions`, `partner_payments`
- `booking_reservations`, `booking_passengers`, `booking_payments`, `booking_logs`
- `admin_users`, `partner_users`, `refresh_tokens`
- `access_logs`, `audit_logs`

RLS Supabase: `supabase/migrations/001_rls_policies.sql`

---

## Testes

```bash
pip install -r requirements.txt
pytest -v
```

---

## Segurança

- JWT access + refresh tokens
- CSRF em formulários
- Rate limiting (SlowAPI)
- bcrypt para senhas
- Headers de segurança (HSTS em produção)
- Proteção brute-force no login
- Sanitização de entradas (bleach)
- Auditoria (`audit_logs`, `access_logs`)

---

## Licença

Proprietário — Transporte Executivo / Nexus Transfer.
