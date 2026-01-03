# GROWTH OS - ARQUITETURA UNIVERSAL WHITE-LABEL

## Visao Geral

Sistema universal de automacao de vendas replicavel para qualquer cliente/nicho.
Baseado em metodologias: Charlie Morgan, JP Middleton, Thiago Reis.

---

## INFRAESTRUTURA EXISTENTE

### Stack Atual
| Componente | Tecnologia | URL/Config |
|------------|------------|------------|
| Backend API | Railway FastAPI | https://agenticoskevsacademy-production.up.railway.app |
| Banco de Dados | Supabase PostgreSQL | bfumywvwubvernvhjehk.supabase.co |
| Orquestracao | n8n | cliente-a1.mentorfy.io |
| CRM | GoHighLevel | Multiplas locations |
| IA Classificacao | Gemini 1.5 Flash | /webhook/classify-lead |
| RAG/Memoria | OpenAI + pgvector | /webhook/rag-* |

### Tabelas Supabase Existentes
- `agent_versions` - Agentes de IA por location
- `crm_leads` - Leads prospectados
- `rag_knowledge` - Base de conhecimento RAG

### Workflow n8n Principal
- ID: `R2fVs2qpct1Qr2Y1`
- Nome: GHL - Mottivme - EUA Versionado
- Funcao: Classificacao de leads + resposta IA

---

## ARQUITETURA GROWTH OS

### FASE 1: Configuracao do Cliente

#### Nova Tabela: `client_configs`

```sql
CREATE TABLE client_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identificadores
    location_id TEXT NOT NULL UNIQUE,  -- GHL Location ID
    client_name TEXT NOT NULL,

    -- VARIAVEIS DE CONTEXTO (6 Essenciais)
    nome_empresa TEXT NOT NULL,
    tipo_negocio TEXT NOT NULL,           -- Ex: "Clinica de Estetica"
    oferta_principal TEXT NOT NULL,       -- Ex: "Harmonizacao facial com resultado natural"
    dor_principal TEXT NOT NULL,          -- Ex: "Baixa autoestima, inseguranca com aparencia"
    publico_alvo TEXT NOT NULL,           -- Ex: "Mulheres 30-55, classe A/B"
    diferenciais TEXT[] NOT NULL,         -- Array de diferenciais

    -- CONFIGURACAO DE PRECOS (Charlie Morgan - Vagueness)
    faixa_preco_texto TEXT,               -- Ex: "a partir de R$ 2.000"
    mostrar_preco BOOLEAN DEFAULT false,

    -- PERSONALIDADE DO AGENTE
    tom_agente TEXT DEFAULT 'consultivo', -- consultivo, amigavel, formal
    nome_agente TEXT DEFAULT 'Assistente',
    emoji_por_mensagem INTEGER DEFAULT 1,

    -- CANAIS ATIVOS
    canais_ativos TEXT[] DEFAULT '{"instagram","whatsapp"}',

    -- HORARIOS DE OPERACAO
    horario_inicio TIME DEFAULT '08:00',
    horario_fim TIME DEFAULT '20:00',
    timezone TEXT DEFAULT 'America/Sao_Paulo',

    -- QUALIFICACAO BANT
    perguntas_qualificacao JSONB DEFAULT '{
        "budget": "Voce ja tem um investimento em mente para isso?",
        "authority": "Voce e quem decide sobre isso ou precisa consultar alguem?",
        "need": "O que te motivou a buscar essa solucao agora?",
        "timeline": "Para quando voce gostaria de resolver isso?"
    }',

    -- AGENDAMENTO
    calendario_url TEXT,                  -- Link do Calendly/GHL Calendar
    tempo_consulta_minutos INTEGER DEFAULT 30,

    -- FOLLOW-UP CONFIG
    max_followups INTEGER DEFAULT 3,
    intervalo_followup_horas INTEGER DEFAULT 24,

    -- ESCALACAO
    telefone_humano TEXT,
    email_humano TEXT,
    gatilhos_escalacao TEXT[] DEFAULT '{"proposta formal","concorrente","reclamacao"}',

    -- METADATA
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index para busca rapida
CREATE INDEX idx_client_configs_location ON client_configs(location_id);
CREATE INDEX idx_client_configs_status ON client_configs(status);
```

---

### FASE 2: Template Universal de Prompt

#### Estrutura do System Prompt Dinamico

```
### 1. IDENTIDADE ###
Voce e {{NOME_AGENTE}}, assistente de atendimento da {{NOME_EMPRESA}}.
Seu tom e {{TOM_AGENTE}}. Use portugues brasileiro natural.
Maximo {{EMOJI_POR_MENSAGEM}} emoji por mensagem.

### 2. SOBRE O NEGOCIO ###
- **Empresa**: {{NOME_EMPRESA}}
- **Segmento**: {{TIPO_NEGOCIO}}
- **Oferta Principal**: {{OFERTA_PRINCIPAL}}
- **Publico-Alvo**: {{PUBLICO_ALVO}}
- **Diferenciais**: {{DIFERENCIAIS_LISTA}}

### 3. DOR DO CLIENTE ###
A principal dor que resolvemos: {{DOR_PRINCIPAL}}
Use empatia ao abordar essa dor. Mostre que entende o problema.

### 4. MODOS DE OPERACAO ###
Este agente opera nos seguintes modos:
- first_contact: Gerar interesse inicial
- qualifier: Qualificar com perguntas BANT
- scheduler: Agendar consulta/demonstracao
- followuper: Reengajar leads frios

### 5. ESTILO CHARLIE MORGAN ###

**Principios de Comunicacao:**
1. VAGUENESS - Seja vago sobre precos ate qualificar
2. BREVIDADE - Mensagens curtas (max 3 linhas)
3. REVERSE DISQUALIFICATION - "Nao sei se e pra voce, mas..."
4. OPCOES BINARIAS - "Prefere A ou B?"
5. CURIOSIDADE - Termine com pergunta

**O que NUNCA fazer:**
- Revelar precos antes de qualificar
- Enviar mensagens longas
- Ser agressivo ou insistente
- Prometer resultados especificos

### 6. QUALIFICACAO BANT ###
{{PERGUNTAS_QUALIFICACAO_JSON}}

### 7. ESCALACAO HUMANA ###
Escalar para humano quando:
{{GATILHOS_ESCALACAO_LISTA}}

Contato humano: {{TELEFONE_HUMANO}} / {{EMAIL_HUMANO}}

### 8. FEW-SHOT EXAMPLES ###

**Primeiro Contato:**
Lead: "Oi"
Voce: "Oi! Tudo bem? Vi seu interesse em {{OFERTA_PRINCIPAL}}. Posso te fazer uma pergunta rapida?"

**Qualificacao de Preco:**
Lead: "Quanto custa?"
Voce: "Depende muito do que voce precisa! Antes de falar valores, me conta: {{PERGUNTA_NEED}}"

**Objecao de Preco:**
Lead: "Ta caro"
Voce: "Entendo! Muitos clientes achavam isso no inicio tambem. O que te fez buscar {{TIPO_NEGOCIO}} agora? Talvez eu consiga te mostrar uma opcao que faca sentido."

**Agendamento:**
Lead: "Quero saber mais"
Voce: "Otimo! A melhor forma e uma conversa rapida de {{TEMPO_CONSULTA}} minutos. Prefere manha ou tarde?"
```

---

### FASE 3: Reativacao (9-Word Message)

#### Dean Jackson Adaptado para WhatsApp/Instagram

**Template Reativacao:**
```
Oi {{PRIMEIRO_NOME}}, ainda ta pensando em {{OFERTA_RESUMIDA}}?
```

**Variacoes:**
1. `Oi {{NOME}}, ainda tem interesse em {{OFERTA}}?`
2. `{{NOME}}, voce desistiu de {{OFERTA}}?`
3. `Oi! Lembrei de voce. Ainda precisa de ajuda com {{DOR}}?`

#### Workflow n8n Reativacao

```
[Trigger: Cron Diario 9h]
    ↓
[Query Supabase: leads status=cold, last_contact > 7 dias]
    ↓
[Para cada lead:]
    ↓
[Buscar client_config por location_id]
    ↓
[Montar mensagem 9-word com variaveis]
    ↓
[Enviar via GHL/WhatsApp]
    ↓
[Atualizar status: reactivation_sent]
```

---

### FASE 4: Show Rate Protocol (27h Rule)

#### Sequencia de Confirmacao

| Momento | Canal | Mensagem |
|---------|-------|----------|
| Imediato | WhatsApp | "Agendamento confirmado para {{DATA}} as {{HORA}}! Vou te mandar um lembrete antes." |
| -24h | Email | "Amanha e o dia! Sua consulta com {{NOME_EMPRESA}} esta confirmada para {{HORA}}. Preparei algumas perguntas pra gente aproveitar ao maximo." |
| -3h | WhatsApp | "Oi! Daqui a 3 horas e nosso horario. Ta tudo certo pra voce?" |
| -30min | WhatsApp | "Ja ja a gente se fala! O link da reuniao: {{LINK}}" |

#### Workflow n8n Show Rate

```
[Trigger: Webhook GHL - Appointment Created]
    ↓
[Salvar appointment em Supabase]
    ↓
[Agendar 4 mensagens no n8n Schedule]
    ↓
[Cada mensagem verifica se appointment ainda existe]
    ↓
[Se cancelado, para sequencia]
```

---

### FASE 5: Trojan Horse Prospecting

#### Script Universal de Abordagem

```
Oi {{NOME}}! Vi que voce {{GATILHO_CONEXAO}}.

Trabalho com {{TIPO_NEGOCIO}} e estou fazendo uma pesquisa rapida
com pessoas do seu perfil.

Posso te fazer UMA pergunta? Leva 30 segundos.

[Se responder SIM]

Legal! {{PERGUNTA_QUALIFICADORA}}

[Se resposta indica dor]

Interessante! Isso e mais comum do que imagina.
A maioria dos meus clientes tinha exatamente esse problema.
Quer que eu te mande um material rapido sobre isso?
```

#### Variaveis Trojan Horse
- `{{GATILHO_CONEXAO}}`: "trabalha com estetica", "tem clinica", "postou sobre X"
- `{{PERGUNTA_QUALIFICADORA}}`: Baseada na dor principal do client_config

---

### FASE 6: KPI Dashboard

#### Metricas por Location

```sql
-- View para dashboard
CREATE VIEW v_growth_os_metrics AS
SELECT
    cc.location_id,
    cc.client_name,

    -- Prospeccao
    COUNT(DISTINCT l.id) FILTER (WHERE l.created_at > NOW() - INTERVAL '7 days') as leads_7d,
    COUNT(DISTINCT l.id) FILTER (WHERE l.status = 'hot') as leads_hot,
    COUNT(DISTINCT l.id) FILTER (WHERE l.status = 'warm') as leads_warm,

    -- Conversao
    ROUND(
        COUNT(DISTINCT l.id) FILTER (WHERE l.status = 'hot')::NUMERIC /
        NULLIF(COUNT(DISTINCT l.id), 0) * 100, 2
    ) as taxa_hot_pct,

    -- Agendamentos (se tiver tabela)
    -- COUNT appointments...

    -- Reativacao
    COUNT(DISTINCT l.id) FILTER (
        WHERE l.reactivation_sent = true
        AND l.last_response_at > l.reactivation_sent_at
    ) as reativacoes_respondidas

FROM client_configs cc
LEFT JOIN crm_leads l ON l.location_id = cc.location_id
GROUP BY cc.location_id, cc.client_name;
```

---

## IMPLEMENTACAO POR ETAPAS

### Etapa 1: Infraestrutura (1-2 dias)
- [ ] Criar tabela `client_configs` no Supabase
- [ ] Criar endpoint `/api/client-config` para CRUD
- [ ] Criar primeira config para MOTTIVME como teste

### Etapa 2: Agente Dinamico (2-3 dias)
- [ ] Modificar busca de agente para puxar `client_configs`
- [ ] Criar funcao de template rendering no n8n/Railway
- [ ] Testar com location MOTTIVME

### Etapa 3: Reativacao (1 dia)
- [ ] Criar workflow n8n de reativacao
- [ ] Template 9-word message
- [ ] Cron job diario

### Etapa 4: Show Rate (1-2 dias)
- [ ] Webhook de appointment
- [ ] Sequencia de 4 mensagens
- [ ] Verificacao de cancelamento

### Etapa 5: Dashboard (2 dias)
- [ ] View SQL de metricas
- [ ] Endpoint `/api/metrics/{location_id}`
- [ ] (Opcional) UI simples

---

## CHECKLIST ONBOARDING NOVO CLIENTE

### Informacoes Necessarias
1. [ ] Nome da Empresa
2. [ ] Tipo de Negocio/Segmento
3. [ ] Oferta Principal (1 frase)
4. [ ] Dor Principal do Cliente (1 frase)
5. [ ] Publico-Alvo (perfil demografico)
6. [ ] 3-5 Diferenciais

### Configuracoes Tecnicas
7. [ ] Location ID do GHL
8. [ ] Calendario de agendamento (link)
9. [ ] Telefone/Email para escalacao
10. [ ] Horario de funcionamento

### Ativacao
11. [ ] Criar registro em `client_configs`
12. [ ] Criar agente em `agent_versions`
13. [ ] Testar fluxo completo
14. [ ] Ativar automacoes

---

## PROXIMOS PASSOS IMEDIATOS

1. **Aprovar este plano** - Ajustar se necessario
2. **Criar tabela client_configs** - SQL pronto acima
3. **Migrar MOTTIVME** - Primeiro cliente do Growth OS
4. **Documentar processo** - Para replicar com outros clientes

---

*Documento criado em: 2026-01-03*
*Versao: 1.0*
*Autor: Claude Code + Marcos Daniels*
