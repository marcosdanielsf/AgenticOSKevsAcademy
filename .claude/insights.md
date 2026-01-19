# AgenticOS - Insights e Decisoes

> **Atualizado em:** 2026-01-19
> **Status:** SISTEMA COMPLETO - Segurança 8/10
> Conhecimento acumulado durante o desenvolvimento

---

## Sessão 2026-01-19 - SISTEMA DE SEGURANÇA COMPLETO

### Arquitetura de Segurança em Camadas (8/10)

| Camada | Componente | Arquivo | Função |
|--------|------------|---------|--------|
| 1. Rede | Proxy Decodo | `proxy_manager.py` | IP residencial brasileiro |
| 2. Browser | Playwright Stealth | `instagram_dm_agent.py` | Oculta automação |
| 3. Comportamento | Warm-up Protocol | `warmup_manager.py` | Limites graduais |
| 4. Detecção | Block Detection | `instagram_dm_agent.py` | 8 tipos de bloqueio |

### Insight: Proxy Trial vs Pago

**Problema:** HTTP 407 (Authentication Required) com trial Decodo
**Causa:** Trial tem limite de requisições/conexões
**Solução:** Plano pago $6/mês (2GB) - funciona imediatamente

### Insight: Seletores Instagram Mudam Frequentemente

**Problema:** `input[placeholder="Search..."]` não encontrado
**Causa:** Instagram mudou placeholder de "Search..." para "Search"
**Solução:** Usar múltiplos fallbacks:
```python
selectors = [
    'div[role="dialog"] input[name="queryBox"]',
    'div[role="dialog"] input[placeholder="Search..."]',
    'div[role="dialog"] input[placeholder="Search"]',
]
```

### Insight: Modal vs Background

**Problema:** Código digitava no campo errado (atrás do modal)
**Causa:** Seletor pegava campo do background, não do dialog
**Solução:** Sempre prefixar com `div[role="dialog"]`

### Configuração Final do Proxy (Supabase)

```sql
INSERT INTO instagram_proxies (
    tenant_id, name, host, port, username, password,
    proxy_type, provider, country, is_residential
) VALUES (
    'global', 'Decodo BR', 'gate.decodo.com', 10001,
    'spmqvj96vr', '<password>', 'http', 'smartproxy', 'BR', true
);
```

### Configuração Playwright Stealth

```python
# requirements.txt
playwright-stealth>=1.0.6

# instagram_dm_agent.py
try:
    from playwright_stealth import stealth_async
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False

# Após criar página:
if STEALTH_AVAILABLE:
    await stealth_async(self.page)
    logger.info("🥷 Stealth mode ENABLED")
```

### Commits Importantes (2026-01-19)

| Commit | Descrição |
|--------|-----------|
| `a76945f` | feat: playwright-stealth anti-detection |
| `8f5593c` | feat: warm-up protocol manager |
| `6f762b6` | feat: proxy rotation infrastructure |
| `076b09e` | feat: block detection system |

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
