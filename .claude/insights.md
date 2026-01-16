# AgenticOS - Insights e Decisões

> **Atualizado em:** 2026-01-16
> **Arquivo de conhecimento acumulado - NÃO DELETAR**

---

## Decisões de Arquitetura

### 1. Scoring Multi-Tenant via Supabase (2026-01-16)

**Contexto:** Precisávamos de ICP scoring personalizado por cliente.

**Opções consideradas:**
- A) Tabela Supabase `tenant_icp_config` ✅ ESCOLHIDA
- B) Arquivo JSON por tenant
- C) Configuração via n8n

**Decisão:** Opção A - Supabase centralizado com cache em memória.

**Razão:**
- Facilita CRUD via Supabase Dashboard
- Cache evita queries repetidas
- Fallback automático para DEFAULT se tenant não existe

**Implementação:**
```python
_config_cache: Dict[str, TenantICPConfig] = {}

def get_tenant_config(tenant_id: str) -> TenantICPConfig:
    if tenant_id in _config_cache:
        return _config_cache[tenant_id]
    config = _fetch_tenant_config(tenant_id)
    if not config:
        config = _fetch_tenant_config("DEFAULT")
    _config_cache[tenant_id] = config
    return config
```

---

### 2. Sistema de Scoring - 4 Categorias (2026-01-16)

**Pesos definidos:**
| Categoria | Peso | O que avalia |
|-----------|------|--------------|
| Bio | 30 pts | Keywords de decisor, profissão, interesses |
| Engagement | 30 pts | Ratio followers/following, conta verificada |
| Profile | 25 pts | Business account, público, localização |
| Recency | 15 pts | Atividade recente (posts, stories) |

**Thresholds:**
| Prioridade | Score | Ação |
|------------|-------|------|
| HOT | >= 70 | Prospectar imediatamente |
| WARM | 50-69 | Prospectar |
| COLD | 40-49 | Nutrir |
| NURTURING | < 40 | Baixa prioridade |

---

### 3. Sync com GHL via Custom Fields (2026-01-16)

**Custom Fields criados no GHL:**
- `outreach_sent_at` - Timestamp do último outreach
- `last_outreach_message` - Última mensagem enviada
- `source_channel` - Canal de origem (instagram_dm, etc)
- `icp_score` - Score calculado
- `lead_priority` - HOT/WARM/COLD

**Tags automáticas:**
- `prospectado` - Lead já abordado
- `outbound-instagram` - Origem Instagram

---

## Padrões de Código Descobertos

### 1. Terminal quebrando comandos Python

**Problema:** Comandos multi-linha no terminal eram quebrados em linhas separadas, causando SyntaxError.

**Solução:** Criar arquivos .py em `/tmp/claude/` e executar separadamente.

```bash
# Em vez de:
python3 -c "import x; ..."

# Usar:
# 1. Criar arquivo /tmp/claude/script.py
# 2. Executar: python3 /tmp/claude/script.py
```

---

### 2. Railway não suporta módulos built-in no requirements.txt

**Problema:** Build falhava com módulos como `concurrent.futures`, `asyncio`.

**Solução:** NÃO incluir no requirements.txt:
- `concurrent.futures` (built-in Python 3.2+)
- `asyncio` (built-in Python 3.4+)
- `asyncio-compat`

---

### 3. Playwright não funciona no Railway

**Problema:** Railway não tem browser instalado.

**Solução:**
- Usar Instagram API (Bruno Fraga) para scraping no servidor
- Playwright apenas LOCAL para demos

---

## Métricas e Resultados

### Teste de Scoring Multi-Tenant (2026-01-16)

**Perfil de teste:**
```json
{
  "username": "pedro.dev",
  "bio": "CTO | Startup SaaS B2B em SP | Software Developer",
  "followers_count": 3000
}
```

**Resultados:**
| Tenant | Score | Prioridade | Decisor | Interesses |
|--------|-------|------------|---------|------------|
| DEFAULT | 45 | COLD | ❌ | tecnologia |
| startup_abc | 55 | WARM | ✅ | tecnologia, negocios |

**Conclusão:** Multi-tenant funciona. "CTO" está nas keywords do startup_abc mas não no DEFAULT.

---

## Erros Resolvidos

### 1. Git push rejected (2026-01-16)

**Erro:** `rejected - fetch first`

**Solução:**
```bash
git pull origin main --rebase && git push origin main
```

---

### 2. npm ENOTEMPTY (2026-01-16)

**Erro:** `ENOTEMPTY: directory not empty` no node_modules

**Solução:**
```bash
rm -rf node_modules package-lock.json && npm install
```

---

## Conhecimentos para RAG

> Estes insights devem ser salvos no Segundo Cérebro (RAG) para referência futura.

**A salvar:**
1. Arquitetura de scoring multi-tenant
2. Padrão de cache de configuração
3. Integração GHL com custom fields
4. Workaround para terminal multi-linha
