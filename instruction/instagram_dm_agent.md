# Instagram DM Agent - Information (Framework ii)

## GOAL
Enviar 200 mensagens diretas personalizadas por dia para leads qualificados no Instagram, de forma autônoma e respeitando os limites da plataforma.

## CONTEXT
Este agente opera como parte do AgenticOS para automatizar outreach no Instagram.
- **Conta:** @marcosdanielsf
- **Database:** Supabase
- **Limite diário:** 200 DMs
- **Limite por hora:** 10 DMs
- **Delay entre DMs:** 30-60 segundos (aleatório)

## WORKFLOW

```
1. INICIALIZAÇÃO
   ├── Carregar sessão salva (sessions/instagram_session.json)
   ├── Se não existir → Fazer login
   ├── Se 2FA necessário → Aguardar intervenção manual
   └── Salvar sessão após login

2. VERIFICAR LIMITES
   ├── Consultar DMs enviados hoje (Supabase)
   ├── Consultar DMs enviados última hora
   └── Se limite atingido → PARAR

3. CARREGAR LEADS
   ├── Buscar leads não contactados (Supabase)
   ├── Filtrar leads já contactados
   └── Limitar ao número disponível

4. LOOP DE ENVIO
   ├── Para cada lead:
   │   ├── Verificar limites novamente
   │   ├── Abrir Instagram Direct
   │   ├── Buscar usuário
   │   ├── Enviar mensagem personalizada
   │   ├── Registrar resultado no Supabase
   │   └── Aguardar delay aleatório (30-60s)
   └── Continuar até limite ou fim dos leads

5. FINALIZAÇÃO
   ├── Salvar sessão
   ├── Atualizar estatísticas diárias
   └── Gerar relatório
```

## CONSTRAINTS (Learned)

### Instagram Limits
- ❌ NUNCA enviar mais de 10 DMs por hora
- ❌ NUNCA enviar mais de 200 DMs por dia
- ❌ NUNCA enviar DM para contas privadas (não aceita sem follow)
- ✅ SEMPRE aguardar 30-60 segundos entre DMs
- ✅ SEMPRE salvar sessão após login bem-sucedido
- ✅ SEMPRE verificar limites ANTES de cada DM

### Technical Constraints
- Se login falhar com 2FA → aguardar intervenção manual (max 2 min)
- Se usuário não encontrado → marcar como failed e continuar
- Se rate limited → PARAR imediatamente
- Se erro de rede → retry até 3x com backoff

### Anti-Detection
- Usar delays aleatórios (não fixos)
- Não enviar mensagens idênticas (personalizar)
- Simular comportamento humano (pausas, variação)

## MESSAGE TEMPLATES

### Template 1: Curiosidade
```
Hey {first_name}! 👋

Noticed you're into {interest}. Really cool stuff!

We built an AI system that automates Instagram outreach - sends 200+ personalized DMs daily on autopilot.

Would love to show you how it works. Interested?
```

### Template 2: Problema/Solução
```
{first_name}, quick question...

Do you spend hours manually DMing prospects on Instagram?

We automated this entire process. Now we send personalized messages while focusing on what matters.

Want me to show you how?
```

### Template 3: Direto
```
Hey {first_name}! 👋

Saw your profile and thought you'd appreciate this...

We're helping businesses automate their Instagram outreach with AI. Personalized DMs at scale, without the manual work.

30 sec to check it out?
```

## DATABASE TABLES (Supabase)

### instagram_leads
| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | BIGSERIAL | ID único |
| username | VARCHAR(255) | Username Instagram |
| full_name | VARCHAR(255) | Nome completo |
| bio | TEXT | Bio do perfil |
| source | VARCHAR(100) | Origem do lead |
| created_at | TIMESTAMP | Data de criação |

### instagram_dm_sent
| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | BIGSERIAL | ID único |
| lead_id | BIGINT | FK para instagram_leads |
| username | VARCHAR(255) | Username |
| message_sent | TEXT | Mensagem enviada |
| status | VARCHAR(50) | sent/failed |
| sent_at | TIMESTAMP | Data/hora do envio |
| account_used | VARCHAR(255) | Conta que enviou |

### instagram_dm_agent_runs
| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | BIGSERIAL | ID único |
| started_at | TIMESTAMP | Início da execução |
| ended_at | TIMESTAMP | Fim da execução |
| dms_sent | INTEGER | Total enviados |
| dms_failed | INTEGER | Total falhados |
| status | VARCHAR(50) | running/completed/error |

## ERROR HANDLING

### Se erro de login:
1. Tirar screenshot
2. Verificar se é 2FA
3. Se 2FA → aguardar manual
4. Se outro erro → abortar e logar

### Se erro ao enviar DM:
1. Tirar screenshot
2. Logar erro no Supabase
3. Incrementar contador de falhas
4. Continuar para próximo lead

### Se rate limit detectado:
1. PARAR imediatamente
2. Logar no Supabase
3. Atualizar status do run
4. Salvar sessão

## METRICS TO TRACK
- DMs enviados hoje
- DMs enviados esta hora
- Taxa de sucesso (%)
- Tempo médio por DM
- Erros por tipo

## COMANDOS

```bash
# Login e salvar sessão (primeira vez)
python implementation/instagram_dm_agent.py --login-only

# Executar campanha (com janela do browser)
python implementation/instagram_dm_agent.py

# Executar em modo headless
python implementation/instagram_dm_agent.py --headless

# Limitar quantidade de DMs
python implementation/instagram_dm_agent.py --limit 50

# Usar template específico
python implementation/instagram_dm_agent.py --template 2
```

## SCHEDULE RECOMENDADO
- **Manhã (9h):** 50 DMs
- **Tarde (14h):** 75 DMs
- **Noite (20h):** 75 DMs
- **Total:** 200 DMs/dia

## CHANGELOG
- v1.0: Implementação inicial com Playwright + Supabase
