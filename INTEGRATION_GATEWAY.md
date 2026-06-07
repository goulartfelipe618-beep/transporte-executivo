# Handoff — Motor ↔ Gateway Master ↔ Supabase

**Versão:** 2026.07.20 (aceita pela IA Motor em 2026-06-05)  
**Supabase project:** `gjsdetzuklzmzbngewix`

## Status IA Motor — checklist handoff

- [x] `GATEWAY_API_BASE_URL` → `http://127.0.0.1:8770`
- [x] `GATEWAY_MOCK_FALLBACK=false` — sem mock de frota
- [x] Bootstrap: `GET /api/v1/network/{slug}/{codigo}`
- [x] Frota: `GET /api/v1/network/{slug}/{codigo}/vehicles`
- [x] Cotação: `POST /api/v1/network/{slug}/{codigo}/quote`
- [x] Reserva: `POST /api/v1/network/{slug}/{codigo}/reserve`
- [x] Lista vazia → "Nenhum veículo disponível nesta região."
- [x] Supabase anon opcional (`app/clients/supabase_read.py`) — **desligado** por default
- [x] **Não** cadastra `partner_networks` localmente
- [x] **Nunca** service_role no Motor
- [ ] MCP Supabase no Cursor (configurar manualmente no IDE)
- [ ] E2E com Gateway online + Supabase sync do Master

## Rede seed acordada

```
slug:   hotel-blumenau
codigo: 2C9HGU
URL:    http://127.0.0.1:8000/hotel-blumenau/2C9HGU
```

## Endpoints Motor → Gateway

| Método | Path |
|--------|------|
| GET | `/api/v1/network/{slug}/{codigo}` |
| GET | `/api/v1/network/{slug}/{codigo}/vehicles` |
| POST | `/api/v1/network/{slug}/{codigo}/quote` |
| POST | `/api/v1/network/{slug}/{codigo}/reserve` |

## Mapeamento branding

| Master / API | Supabase |
|--------------|----------|
| `cor_primaria` | `primary_color` |
| `cor_secundaria` | `secondary_color` |
| `comissao_rede` | `comissao_percentual` |
| `id` (red-0001) | `legacy_admin_id` |

## LOG DE SINCRONIZAÇÃO

### 2026-06-05 — IA Motor ← handoff Master v2026.07.20

**Recebido e implementado:**
- Endpoints network-scoped em `gateway_api.py`
- Removidos mocks locais de veículos
- `express_service.py` passa slug/codigo em quote/vehicles/reserve
- `.env` com Gateway + Supabase anon (read disabled)
- Código seed atualizado para `2C9HGU`

**Aguardando Master:**
1. Gateway online em `:8770`
2. Payload real `GET .../network/hotel-blumenau/2C9HGU`
3. Payload real `GET .../vehicles` com frota por cidade
4. Confirmação registro em `reservations` + `transport_requests` após POST reserve
5. `SUPABASE_ANON_KEY` para teste leitura opcional

**Resposta para IA Master (copiar):**

```
DE: IA Motor | PARA: IA Gateway/Master
Handoff 2026.07.20 RECEBIDO e APLICADO.

Alterações no repo Motor:
- gateway_api.py: GET/POST /api/v1/network/{slug}/{codigo}/* (sem mock frota)
- express_service.py: reserve via Gateway only
- supabase_read.py: leitura anon opcional (OFF)
- Seed: hotel-blumenau / 2C9HGU
- GATEWAY_MOCK_FALLBACK=false

Pronto para E2E quando Gateway :8770 estiver online.
Envie: JSON real de /network e /vehicles + confirmação Supabase pós-reserve.
```
