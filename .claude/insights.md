# AgenticOS - Insights e Decisoes

> **Atualizado em:** 2026-01-16
> Conhecimento acumulado durante o desenvolvimento

---

## Arquitetura

### API Server (api_server.py)
- **Linhas:** ~4.700
- **Endpoints:** 57 rotas
- **Framework:** FastAPI + Uvicorn
- **Deploy:** Railway via Nixpacks

### Problemas Criticos de Escalabilidade

#### 1. Campanhas em Memoria RAM
```python
# Linha 4516-4517
running_campaigns: Dict[str, Dict[str, Any]] = {}
```
**Problema:** Perde tudo em crash/restart. Impossivel escalar horizontalmente.
**Solucao:** Migrar para Redis HSET

#### 2. Rate Limiter Falho
```python
# Linha 91-170
class RateLimiter:
    self.requests: Dict[str, List[float]] = defaultdict(list)
```
**Problema:** Memory leak, sem persistencia, bypass facil.
**Solucao:** Redis INCR com TTL

#### 3. N+1 Queries Supabase
```python
# Linha 344-554
# Cada save_lead faz 2 requests (check + insert/update)
```
**Solucao:** Usar UPSERT ou bulk operations

#### 4. BackgroundTasks Sem Retry
**Problema:** 12 endpoints usam BackgroundTasks sem persistencia.
**Solucao:** Celery + Redis

#### 5. Auth Superficial
```python
# Linha 779-783
# Apenas verifica API_SECRET_KEY header
# Sem JWT, sem scopes, sem RBAC
```

---

## Decisoes Tecnicas

### Multi-Tenant Scoring
- Cada tenant tem seu proprio ICP config na tabela `tenant_icp_config`
- Score calculado com pesos diferentes por tenant
- Prioridades: HOT (>=70), WARM (50-69), COLD (40-49), NURTURING (<40)

### Sincronizacao com GHL
- Metodo `sync_to_ghl()` no instagram_dm_agent.py
- Tags adicionadas: `prospectado`, `outbound-instagram`
- Custom fields: `outreach_sent_at`, `last_outreach_message`, `source_channel`

### Endpoints de Campanha
- `POST /api/campaign/start` - Inicia campanha em background
- `GET /api/campaign/{id}` - Status da campanha
- `GET /api/campaigns` - Lista campanhas (filtro por status)
- `POST /api/campaign/{id}/stop` - Para campanha

---

## Padroes de Codigo

### Async/Await
- 87% dos endpoints sao async
- Usar `async def` para I/O bound operations
- BackgroundTasks para operacoes longas

### Error Handling
```python
try:
    # operacao
except Exception as e:
    logger.error(f"Error: {e}")
    return {"success": False, "error": str(e)}
```

### Logging
```python
import logging
logger = logging.getLogger(__name__)
logger.info("message", extra={"campaign_id": id})
```

---

## Roadmap de Escalabilidade

### Prioridade 1 (Semana 1-2)
1. Redis para campanhas e rate limiting
2. Connection pooling (httpx)
3. Retry logic (tenacity)

### Prioridade 2 (Semana 3-4)
1. Celery job queue
2. Checkpoint system
3. JWT auth

### Prioridade 3 (Semana 5-6)
1. Structured logging
2. Prometheus metrics
3. Sentry integration

---

## Variaveis de Ambiente

```
SUPABASE_URL=https://bfumywvwubvernvhjehk.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<secret>
GEMINI_API_KEY=<secret>
OPENAI_API_KEY=<secret>
GHL_API_KEY=<secret>
GHL_LOCATION_ID=<secret>
INSTAGRAM_SESSION_ID=<secret>
```

**ATENCAO:** `.env` estava commitado no git. Rotacionar todas as keys!

---

## Links Uteis

- Railway Dashboard: https://railway.app
- Supabase: https://supabase.com/dashboard/project/bfumywvwubvernvhjehk
- API Docs: https://agenticoskevsacademy-production.up.railway.app/docs
