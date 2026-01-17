# Clone System SOP - Prospecção Escalável Instagram

> **Versão:** 1.0
> **Data:** 2026-01-17
> **Baseado em:** Kevin Badi Stack, Bruno Fraga, Kevs Academy
> **Status:** SPEC - Pronto para implementação

---

## Sumário Executivo

Este documento consolida as melhores práticas para escalar prospecção via Instagram DM sem bloqueios, baseado em análises de:

1. **Stack Kevin Badi** - Claude Code + Playwright MCP + Skills
2. **Playwright MCP Options** - Stealth Browser MCP recomendado
3. **Clone System Kevs** - Warm-up 21 dias + rotação + delays
4. **Instagram Private API** - Extração de dados ocultos (FBID, geolocation)

---

## 1. Arquitetura Recomendada

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CLONE SYSTEM v2.0                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐        │
│  │  WARM-UP        │    │  PROSPECTOR     │    │  ANALYZER       │        │
│  │  MODULE         │    │  MODULE         │    │  MODULE         │        │
│  │                 │    │                 │    │                 │        │
│  │  • 21-day       │ ─> │  • Round-robin  │ ─> │  • Private API  │        │
│  │    protocol     │    │    rotation     │    │    extraction   │        │
│  │  • Trust score  │    │  • Spintax DMs  │    │  • FBID lookup  │        │
│  │  • Engagement   │    │  • Delay jitter │    │  • Geolocation  │        │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘        │
│           │                      │                      │                  │
│           │                      │                      │                  │
│           ▼                      ▼                      ▼                  │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    INFRASTRUCTURE LAYER                              │  │
│  │  • Stealth Browser MCP (anti-detect)                                │  │
│  │  • Residential/4G Proxies (rotation)                                │  │
│  │  • Session Management (Supabase)                                    │  │
│  │  • Rate Limiter (Redis)                                             │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Stack Tecnológico

### 2.1 Claude Code + MCP (Kevin Badi Style)

| Componente | Função | Implementação |
|------------|--------|---------------|
| **Claude Code** | Orquestrador principal | CLI com skills |
| **Playwright MCP** | Browser automation | Accessibility tree, não screenshots |
| **Skills** | Funções reutilizáveis | `.claude/skills/*.md` |
| **Memory** | Persistência | `.claude/context.md`, `.claude/todos.md` |

### 2.2 Opções de Playwright MCP

| Opção | Prós | Contras | Recomendação |
|-------|------|---------|--------------|
| **Microsoft Playwright MCP** | Oficial, estável | Sem stealth | Desenvolvimento |
| **ExecuteAutomation MCP** | Funcionalidades extras | Menos testado | Opcional |
| **Browser MCP** | Local, leve | Sem anti-detect | Testes |
| **Stealth Browser MCP** | 98.7% anti-detect | Mais complexo | **PRODUÇÃO** |

**Recomendação:** Usar **Stealth Browser MCP** para produção (98.7% success rate em sites protegidos).

### 2.3 Infraestrutura de Proxies

| Tipo | Uso | Custo | Provider |
|------|-----|-------|----------|
| **Residential** | DMs em escala | Alto | BrightData, Oxylabs |
| **4G/Mobile** | Warm-up, contas novas | Médio | Proxidize, 911 |
| **Datacenter** | Scraping leve | Baixo | IPRoyal |

**Regra:** 1 proxy residencial por conta. NUNCA compartilhar IPs entre contas.

---

## 3. Protocolo de Warm-up (21 Dias)

### Fase 1: Ativação (Dias 1-7)

| Dia | Ação | Limite |
|-----|------|--------|
| 1 | Criar conta, foto, bio | 0 DMs |
| 2-3 | Seguir 10-20 perfis relevantes | 0 DMs |
| 4-5 | Curtir posts, ver stories | 0 DMs |
| 6-7 | Comentários em 3-5 posts | 0 DMs |

### Fase 2: Aquecimento (Dias 8-14)

| Dia | Ação | Limite DMs |
|-----|------|------------|
| 8 | Primeira DM (amigo/conhecido) | 1 |
| 9-10 | DMs para contas que seguem você | 3-5 |
| 11-12 | DMs para contas que interagiram | 5-10 |
| 13-14 | DMs mistas | 10-15 |

### Fase 3: Escala Gradual (Dias 15-21)

| Dia | Limite DMs | Delay Mínimo |
|-----|------------|--------------|
| 15 | 20 | 5 min |
| 16 | 25 | 4 min |
| 17 | 30 | 4 min |
| 18 | 35 | 3 min |
| 19 | 40 | 3 min |
| 20 | 45 | 3 min |
| 21 | 50 | 3 min |

### Fase 4: Manutenção (Dia 22+)

- **Limite diário:** 50-70 DMs por conta
- **Delay:** 3-7 minutos entre DMs
- **Rotação:** Round-robin entre contas
- **Descanso:** Pausa de 8h à noite

---

## 4. Sistema de Spintax

### 4.1 Sintaxe

```
{Oi|Olá|E aí}, {vi|percebi|notei} que você {trabalha com|atua em} {especialidade}.
{Tenho uma pergunta rápida|Posso te fazer uma pergunta}?
```

**Output possível:**
- "Oi, vi que você trabalha com marketing. Tenho uma pergunta rápida?"
- "Olá, percebi que você atua em vendas. Posso te fazer uma pergunta?"

### 4.2 Templates Spintax (Charlie Morgan Style)

```python
SPINTAX_TEMPLATES = {
    "opener_vague": "{Oi|Olá|E aí}, {vi|percebi|notei} seu perfil...",
    "curiosity_hook": "{Você já pensou em|Já considerou|Estaria aberto a} {escalar|crescer|expandir}?",
    "reverse_disqualify": "{Provavelmente não é pra você|Pode não fazer sentido}, mas {queria perguntar|tenho uma dúvida}...",
    "close_soft": "{Me conta mais|Posso te explicar|Quer saber como funciona}?"
}
```

### 4.3 Implementação Python

```python
import re
import random

def expand_spintax(text: str) -> str:
    """Expande spintax: {op1|op2|op3} -> escolhe aleatório"""
    pattern = r'\{([^{}]+)\}'

    def replace_match(match):
        options = match.group(1).split('|')
        return random.choice(options)

    while re.search(pattern, text):
        text = re.sub(pattern, replace_match, text)

    return text
```

---

## 5. Instagram Private API

### 5.1 Endpoints Úteis

| Endpoint | Função | Dados Retornados |
|----------|--------|------------------|
| `i.instagram.com/api/v1/users/web_profile_info/` | Perfil completo | Bio, followers, FBID |
| `i.instagram.com/api/v1/users/{pk}/info/` | Info por PK | Dados detalhados |
| `i.instagram.com/api/v1/friendships/{pk}/followers/` | Followers | Lista paginada |

### 5.2 Headers Obrigatórios

```python
INSTAGRAM_HEADERS = {
    'User-Agent': 'Instagram 275.0.0.27.98 Android',
    'Cookie': f'sessionid={SESSION_ID}',
    'X-IG-App-ID': '936619743392459',
    'X-IG-Device-ID': 'unique-device-id',
    'X-Requested-With': 'XMLHttpRequest',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9'
}
```

### 5.3 Dados Ocultos Extraíveis

| Campo | Descrição | Uso |
|-------|-----------|-----|
| `fbid` | Facebook ID interno | Identificação única |
| `pk` | Primary Key Instagram | API calls |
| `city_id`, `city_name` | Geolocalização | Segmentação |
| `business_category_name` | Categoria comercial | ICP scoring |
| `connected_fb_page` | Página FB vinculada | Cross-platform |
| `account_type` | 1=personal, 2=business, 3=creator | Qualificação |

### 5.4 Exemplo de Extração

```python
import requests

def get_hidden_profile_data(username: str, session_id: str) -> dict:
    """Extrai dados ocultos do perfil via Private API"""
    headers = {
        'User-Agent': 'Instagram 275.0.0.27.98 Android',
        'Cookie': f'sessionid={session_id}',
        'X-IG-App-ID': '936619743392459'
    }

    url = f'https://i.instagram.com/api/v1/users/web_profile_info/?username={username}'
    response = requests.get(url, headers=headers)
    data = response.json()

    user = data.get('data', {}).get('user', {})

    return {
        'fbid': user.get('fbid'),
        'pk': user.get('pk'),
        'is_business': user.get('is_business_account'),
        'business_category': user.get('business_category_name'),
        'city_name': user.get('city_name'),
        'follower_count': user.get('edge_followed_by', {}).get('count'),
        'following_count': user.get('edge_follow', {}).get('count'),
        'post_count': user.get('edge_owner_to_timeline_media', {}).get('count')
    }
```

---

## 6. Limites de Segurança

### 6.1 Por Conta

| Métrica | Limite Seguro | Limite Máximo | Risco |
|---------|---------------|---------------|-------|
| DMs/dia | 50 | 70 | Ban temporário |
| DMs/hora | 10 | 15 | Rate limit |
| Follows/dia | 100 | 200 | Action block |
| Likes/hora | 60 | 100 | Shadowban |

### 6.2 Por Sessão de Trabalho

```python
SESSION_LIMITS = {
    "max_dms_per_session": 30,        # Parar e descansar depois
    "min_delay_minutes": 3,            # Delay mínimo entre DMs
    "max_delay_minutes": 7,            # Delay máximo entre DMs
    "session_duration_hours": 4,       # Duração máxima de sessão
    "rest_between_sessions_hours": 2   # Descanso entre sessões
}
```

### 6.3 Detecção de Bloqueio

```python
BLOCK_INDICATORS = [
    "action_blocked",
    "challenge_required",
    "checkpoint_required",
    "feedback_required",
    "rate_limit_exceeded"
]

def check_for_block(response: dict) -> bool:
    """Verifica se resposta indica bloqueio"""
    status = response.get('status', '')
    message = response.get('message', '')

    for indicator in BLOCK_INDICATORS:
        if indicator in status.lower() or indicator in message.lower():
            return True
    return False
```

---

## 7. Roadmap de Implementação

### Fase 1: Quick Wins (Já Implementado) ✅

- [x] Round-robin rotation (`RoundRobinAccountRotator`)
- [x] Delay em minutos (`run_campaign_kevs`)
- [x] Múltiplos perfis de origem (`target_type: profiles`)
- [x] Jitter humano (±15%)

### Fase 2: Próximas Implementações

| Prioridade | Feature | Arquivo | Esforço |
|------------|---------|---------|---------|
| P0 | Spintax engine | `message_generator.py` | 2h |
| P0 | Block detection | `instagram_dm_agent.py` | 2h |
| P1 | Warm-up protocol | `warm_up_manager.py` | 4h |
| P1 | Private API extraction | `instagram_api.py` | 3h |
| P2 | Stealth Browser MCP | `browser_manager.py` | 8h |
| P2 | Proxy rotation | `proxy_manager.py` | 4h |

### Fase 3: Infraestrutura Avançada

- [ ] Redis para rate limiting distribuído
- [ ] Celery para job queue
- [ ] Sentry para monitoramento de erros
- [ ] Prometheus + Grafana para métricas

---

## 8. Checklist de Deploy

### Antes de Escalar

- [ ] Warm-up de 21 dias completado em todas as contas
- [ ] Proxies residenciais configurados (1 por conta)
- [ ] Session IDs atualizados no Supabase
- [ ] Spintax templates validados
- [ ] Limites de segurança configurados
- [ ] Monitoramento de bloqueios ativo
- [ ] Backup de sessões funcionando

### Configuração de Campanha

```json
{
  "tenant_id": "mottivme",
  "target_type": "profiles",
  "target_value": "perfil1,perfil2,perfil3",
  "limit": 150,
  "kevs_mode": true,
  "delay_min": 3,
  "delay_max": 7,
  "min_score": 50,
  "use_spintax": true,
  "warm_up_complete": true
}
```

---

## Referências

- [Kevin Badi - Agentic Workflows](https://kevinbadi.com)
- [Bruno Fraga - OSINT Instagram](https://brunofraga.com)
- [Kevs Academy - Clone System](https://kevsacademy.com)
- [Stealth Browser MCP](https://github.com/nicholasyoder/stealth-browser-mcp)

---

*Documento gerado automaticamente por Claude Code*
*Última atualização: 2026-01-17*
