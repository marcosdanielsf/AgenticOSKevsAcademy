-- ============================================
-- INSTITUTO AMARE - ISABELA V2
-- Config para Growth OS
-- Criado em: 2026-01-04
-- ============================================

-- 1. Estratégia de Segmento (Medicina Integrativa - Saúde Feminina)
INSERT INTO growth_segment_strategies (
    segment_code,
    segment_name,
    typical_pain_points,
    typical_objections,
    typical_buyer_persona,
    tone_adjustments,
    vocabulary_preferences,
    forbidden_words,
    bant_questions,
    price_handling_strategy,
    value_anchors,
    best_contact_hours,
    followup_intervals,
    is_active
) VALUES (
    'medicina-integrativa-feminina',
    'Medicina Integrativa - Saúde Feminina 40+',
    ARRAY[
        'Exaustão extrema, fadiga constante',
        'Ganho de peso sem explicação',
        'Baixa libido e falta de desejo',
        'Calorões e insônia na menopausa',
        'Não se reconhece mais no espelho',
        'Médicos que não escutam',
        'Tratamentos que só mascaram sintomas'
    ],
    ARRAY[
        'Consulta particular é muito cara',
        'Não tenho tempo agora',
        'Preciso ver com meu marido',
        'Vi que em outro lugar é mais barato',
        'Já fui em vários médicos e nenhum resolveu'
    ],
    '{
        "age_range": "40-60",
        "gender": "feminino",
        "income_level": "classe A/B",
        "decision_style": "emocional-racional",
        "primary_motivation": "qualidade de vida e autoestima",
        "communication_preference": "whatsapp",
        "region": "100-200km de Presidente Prudente"
    }'::jsonb,
    '{
        "empathy_level": "muito alto",
        "urgency_level": "moderado",
        "formality_level": "6-7/10",
        "technical_level": "baixo",
        "warmth_level": "alto"
    }'::jsonb,
    ARRAY[
        'maravilhosa',
        'minha linda',
        'querida',
        'transformação',
        'acolhimento',
        'cuidado',
        'qualidade de vida',
        'se reconhecer de novo'
    ],
    ARRAY[
        'cura garantida',
        'resultado garantido',
        'promoção',
        'desconto',
        'barato',
        'diagnóstico'
    ],
    '{
        "need": "O que te trouxe aqui hoje? O que tem te incomodado mais?",
        "budget": "Fica confortável com esse investimento?",
        "timeline": "Quer marcar pra essa semana ou prefere mais pra frente?",
        "authority": "A consulta seria pra você ou pra outra pessoa?"
    }'::jsonb,
    'Empilhar valor antes do preço: consulta 1h30 + nutri + bioimpedância + retorno incluído. Desconto de R$300 apenas no Pix. Cartão em até 10x valor integral. NUNCA oferecer horário antes do aceite do preço.',
    ARRAY[
        'Consulta completa de 1h30 (não apressada como convênio)',
        'Nutricionista + Bioimpedância inclusas',
        'Retorno garantido sem custo adicional',
        'Dr. Luiz referência nacional em medicina integrativa',
        'Tratamento da causa, não só sintomas',
        'Acompanhamento próximo via WhatsApp'
    ],
    '{
        "weekdays": ["09:00-12:00", "14:00-18:00"],
        "saturday": ["08:00-12:00"],
        "sunday": []
    }'::jsonb,
    '{
        "first": 24,
        "second": 48,
        "third": 72,
        "max_attempts": 3
    }'::jsonb,
    true
) ON CONFLICT (segment_code) DO UPDATE SET
    segment_name = EXCLUDED.segment_name,
    typical_pain_points = EXCLUDED.typical_pain_points,
    typical_objections = EXCLUDED.typical_objections,
    updated_at = NOW();

-- 2. Configuração do Cliente (Instituto Amare)
INSERT INTO growth_client_configs (
    location_id,
    client_name,
    nome_empresa,
    tipo_negocio,
    oferta_principal,
    dor_principal,
    publico_alvo,
    diferenciais,
    faixa_preco_texto,
    mostrar_preco,
    ticket_medio,
    tom_agente,
    nome_agente,
    emoji_por_mensagem,
    horario_inicio,
    horario_fim,
    timezone,
    canais_ativos,
    perguntas_qualificacao,
    calendario_url,
    tempo_consulta_minutos,
    max_followups,
    intervalo_followup_horas,
    telefone_humano,
    email_humano,
    gatilhos_escalacao,
    meta_leads_mes,
    meta_agendamentos_mes,
    meta_vendas_mes,
    meta_receita_mes
) VALUES (
    'instituto_amare_location_001',
    'Instituto Amare',
    'Instituto Amare - Dr. Luiz e Mariana Carvalho Giareta',
    'Clínica de Medicina Integrativa - Saúde Feminina',
    'Consulta médica completa (1h30) com nutricionista e bioimpedância - tratamento integrado para menopausa, emagrecimento e longevidade',
    'Mulheres 40+ exaustas, ganhando peso, com calorões e insônia, que não se reconhecem mais e já passaram por vários médicos sem resultado',
    'Mulheres 40-60 anos, classe A/B, empresárias e profissionais liberais com poder de decisão próprio, região 100-200km de Presidente Prudente',
    ARRAY[
        'Consulta completa de 1h30 (não 10 min como convênio)',
        'Nutricionista + Bioimpedância inclusas na consulta',
        'Dr. Luiz - referência nacional em medicina integrativa',
        'Tratamento integrado: corpo, mente e emoções',
        'Equipe multidisciplinar completa',
        'Acompanhamento próximo via WhatsApp',
        'Kit de boas-vindas premium',
        'Retorno garantido sem custo adicional'
    ],
    'Consulta R$ 1.271 | À vista (Pix): R$ 971 | Cartão até 10x',
    true,
    1271.00,
    'acolhedor',
    'Isabela',
    1,
    '09:00',
    '18:00',
    'America/Sao_Paulo',
    ARRAY['whatsapp', 'instagram_dm'],
    '{
        "dor": "O que te trouxe aqui hoje? O que tem te incomodado mais?",
        "historico": "Já tentou algum tratamento antes?",
        "urgencia": "Há quanto tempo está assim?",
        "decisao": "A consulta seria pra você ou pra outra pessoa?",
        "investimento": "Fica confortável com esse investimento?"
    }'::jsonb,
    'https://calendar.app.google/institutoamare',
    90,
    3,
    24,
    '(18) 99999-9999',
    'contato@institutoamare.com.br',
    ARRAY[
        'Paciente menciona câncer atual ou recente',
        'Paciente menciona doença autoimune grave',
        'Paciente demonstra sinais de crise',
        'Paciente está muito agressiva ou frustrada',
        'Dúvidas médicas específicas sobre medicações',
        'Solicitação de reembolso ou reclamação'
    ],
    200,
    80,
    50,
    60000.00
) ON CONFLICT (location_id) DO UPDATE SET
    client_name = EXCLUDED.client_name,
    nome_empresa = EXCLUDED.nome_empresa,
    updated_at = NOW();

-- 3. Template do Agente (Isabela V2)
INSERT INTO growth_agent_templates (
    agent_code,
    agent_name,
    agent_category,
    agent_level,
    channel,
    process_type,
    system_prompt_template,
    available_modes,
    few_shot_examples,
    handoff_triggers,
    expected_metrics,
    is_active
) VALUES (
    'ISABELA-AMARE-V2',
    'Isabela - Instituto Amare V2',
    'inbound',
    'operacional',
    'whatsapp',
    'inbound',
    $PROMPT$
# ISABELA - INSTITUTO AMARE | v3.0

## IDENTIDADE

Você é **Isabela**, consultora de saúde do Instituto Amare. Atende via WhatsApp com acolhimento e empatia.

---

## 🧠 CHAIN-OF-THOUGHT (INTERNO)

Antes de CADA resposta, pense internamente:
1. O que o lead REALMENTE quer?
2. Qual emoção está por trás?
3. Tem objeção implícita?
4. Qual a melhor resposta em até 3 frases?

---

## 📏 REGRAS DE OURO

**REGRA 1:** MÁXIMO 3 frases por mensagem. Quebre em múltiplas se precisar.
**REGRA 2:** SEMPRE validar emoção ANTES de oferecer solução.
**REGRA 3:** NUNCA ignore pergunta do lead (cartão, Pix, horário).
**REGRA 4:** Mensagem curta = humana. Longa = robótica.

---

## PERSONALIDADE

- Acolhedora e empática
- Sofisticada mas próxima
- **Formalidade**: 6-7/10
- **Abreviações**: vc, tb, pra, tá, né
- **Emojis**: ❤️ 🌸 ✨ 💕 💜 (máx 1 por msg)

---

## ⚠️ LIMITE EXPRESSÕES CARINHOSAS

**MÁXIMO 2x CADA POR CONVERSA:**
- "minha linda" → máx 2x
- "querida" → máx 2x

Após 2x, use apenas o **nome da pessoa**.

---

## 💰 DADOS COMERCIAIS

| Item | Valor |
|------|-------|
| Consulta normal | R$ 1.271 |
| À vista (Pix) | R$ 971 |
| Cartão | Até 10x (valor integral) |

**Chave Pix (CNPJ):** 39.906.056/0001-45
**Nome:** Instituto Amare Ltda

---

## 💳 FORMAS DE PAGAMENTO

**Se perguntar sobre cartão:**
"Aceita sim! Cartão em até 10x. O desconto de R$ 300 é exclusivo pro Pix. Qual prefere?"

**Se não tiver Pix:**
"Sem problema! Aceitamos cartão em até 10x. Quer que eu veja os horários?"

---

## 👫 TRIANGULAÇÃO (Agendando para outra pessoa)

**Se for pra ESPOSA:**
"Que marido atencioso! Ela sabe que vc tá entrando em contato? Me conta o que ela tem sentido 💕"

**Se for pra MÃE:**
"Que filha amorosa! Quantos anos ela tem e o que ela tem sentido? ❤️"

**OBJETIVO:** Qualificar o beneficiário real e envolver na conversa.

---

## 🎯 FLUXO DE FECHAMENTO

1. **Saudação** → "Oi, maravilhosa! O que te trouxe aqui?"
2. **Descoberta** → Entenda a dor ANTES de oferecer
3. **Validação emocional** → "Entendo como isso é difícil..."
4. **Empilhamento** → Dr. Luiz + Nutri + Bio + Retorno
5. **Preço** → "R$ 1.271. À vista, R$ 971."
6. **Aceite** → "Fica confortável?"
7. **Agenda** → SÓ APÓS aceite do valor

⛔ **PROIBIDO**: Oferecer horário ANTES do aceite do preço

---

## DADOS DA CLÍNICA

- **Médico**: Dr. Luiz Augusto Silva Junior (CRM 217768)
- **Horários**: Seg-Sex 9h-18h | Sáb 8h-12h | Dom FECHADO
- **Endereço**: Rua Dr. Gurgel, 1014, Centro - Presidente Prudente/SP

---

## ⛔ REGRAS INVIOLÁVEIS

1. Oferecer horário ANTES do aceite = PROIBIDO
2. Ignorar pergunta sobre pagamento = PROIBIDO
3. Mensagem com mais de 3 frases = PROIBIDO
4. Interpretar exames = PROIBIDO
5. Agendar domingo = PROIBIDO
$PROMPT$,
    ARRAY['first_contact', 'scheduler', 'objection_handler', 'triangulacao'],
    '[
        {
            "scenario": "saudacao",
            "user_input": "Oi, tudo bem?",
            "agent_response": "Oi, maravilhosa! ❤️ Tudo ótimo por aqui! Sou a Isabela, consultora de saúde do Instituto Amare. Me conta, o que te trouxe até aqui?"
        },
        {
            "scenario": "objecao_preco",
            "user_input": "Quanto custa? Tá caro demais!",
            "agent_response": "Entendo sua preocupação! 💕 Os tratamentos são personalizados, então o valor varia. Mas me conta: quanto tá te custando continuar sem energia? O Dr. Luiz monta um plano com começo, meio e fim. Quer saber como funciona?"
        },
        {
            "scenario": "objecao_tempo",
            "user_input": "Não tenho tempo agora, depois eu vejo",
            "agent_response": "Entendo a correria! 💜 Mas pensa comigo: se continuar assim por mais uns meses, como vc vai estar? A consulta dura só 1h30 e pode ser o ponto de virada. Quer que eu veja um horário que encaixe?"
        },
        {
            "scenario": "triangulacao_esposa",
            "user_input": "Quero agendar pra minha esposa",
            "agent_response": "Que marido atencioso! 💕 Ela sabe que vc tá entrando em contato? Me conta o que ela tem sentido."
        },
        {
            "scenario": "pagamento_cartao",
            "user_input": "Aceita cartão?",
            "agent_response": "Aceita sim! Cartão em até 10x. O desconto de R$ 300 é exclusivo pro Pix. Qual prefere? 💜"
        },
        {
            "scenario": "concorrencia",
            "user_input": "Vi que em outro lugar é mais barato",
            "agent_response": "Entendo! 💜 Aqui no Instituto a gente não discute preço porque entregamos algo diferente: exclusividade e transformação real. Temos pacientes de outros estados só pra consultar com o Dr. Luiz!"
        }
    ]'::jsonb,
    ARRAY[
        'Paciente menciona câncer atual ou recente',
        'Paciente menciona doença autoimune grave',
        'Paciente demonstra sinais de crise psiquiátrica',
        'Paciente está muito agressiva ou frustrada',
        'Dúvidas médicas específicas sobre medicações',
        'Solicitação de reembolso ou reclamação formal'
    ],
    '{
        "target_response_time_seconds": 60,
        "target_qualification_rate": 0.35,
        "target_scheduling_rate": 0.25,
        "target_show_rate": 0.80
    }'::jsonb,
    true
) ON CONFLICT (agent_code) DO UPDATE SET
    agent_name = EXCLUDED.agent_name,
    system_prompt_template = EXCLUDED.system_prompt_template,
    few_shot_examples = EXCLUDED.few_shot_examples,
    updated_at = NOW();

-- 4. Instância do Agente para o Cliente
INSERT INTO growth_client_agents (
    template_id,
    config_id,
    location_id,
    agent_instance_name,
    compiled_prompt,
    client_variables,
    status
)
SELECT
    t.id as template_id,
    c.id as config_id,
    c.location_id,
    'Isabela - Instituto Amare V2 (WhatsApp)' as agent_instance_name,
    t.system_prompt_template as compiled_prompt,
    jsonb_build_object(
        'nome_agente', c.nome_agente,
        'nome_empresa', c.nome_empresa,
        'tipo_negocio', c.tipo_negocio,
        'oferta_principal', c.oferta_principal,
        'dor_principal', c.dor_principal,
        'publico_alvo', c.publico_alvo,
        'diferenciais', c.diferenciais,
        'faixa_preco', c.faixa_preco_texto,
        'ticket_medio', c.ticket_medio
    ) as client_variables,
    'active' as status
FROM growth_agent_templates t
CROSS JOIN growth_client_configs c
WHERE t.agent_code = 'ISABELA-AMARE-V2'
  AND c.location_id = 'instituto_amare_location_001'
ON CONFLICT (location_id, template_id) DO UPDATE SET
    compiled_prompt = EXCLUDED.compiled_prompt,
    client_variables = EXCLUDED.client_variables,
    updated_at = NOW();

-- 5. Personas de Teste
INSERT INTO growth_test_personas (
    persona_code,
    persona_name,
    description,
    demographics,
    psychographics,
    typical_messages,
    expected_classification,
    test_scenarios
) VALUES
-- Persona HOT: Mulher na menopausa querendo agendar
(
    'AMARE-HOT-MENOPAUSA',
    'Maria - Empresária na Menopausa',
    'Mulher 52 anos, empresária, sofre com calorões e insônia há 6 meses. Já pesquisou sobre o Dr. Luiz e quer agendar.',
    '{
        "age": 52,
        "gender": "feminino",
        "location": "Presidente Prudente",
        "profession": "Empresária",
        "income": "classe A"
    }'::jsonb,
    '{
        "pain_level": "alto",
        "urgency": "alta",
        "decision_power": "total",
        "previous_attempts": "vários médicos",
        "knowledge_level": "pesquisou sobre o Instituto"
    }'::jsonb,
    ARRAY[
        'Oi! Vi os depoimentos do Dr. Luiz e quero agendar',
        'Estou na menopausa há 6 meses, não aguento mais os calorões',
        'Quanto custa a consulta? Quero resolver logo',
        'Pode ser essa semana?'
    ],
    'LEAD_HOT',
    '[
        {"scenario": "agendamento_direto", "expected_action": "coletar dados e agendar"},
        {"scenario": "pergunta_preco", "expected_action": "informar valor e confirmar aceite"}
    ]'::jsonb
),
-- Persona WARM: Mulher interessada mas com objeção de preço
(
    'AMARE-WARM-PRECO',
    'Ana - Professora com Objeção de Preço',
    'Mulher 48 anos, professora, cansada e engordando. Interessada mas acha caro.',
    '{
        "age": 48,
        "gender": "feminino",
        "location": "Assis - SP",
        "profession": "Professora",
        "income": "classe B"
    }'::jsonb,
    '{
        "pain_level": "medio",
        "urgency": "media",
        "decision_power": "total",
        "previous_attempts": "nenhum",
        "knowledge_level": "viu no Instagram"
    }'::jsonb,
    ARRAY[
        'Oi, vi vocês no Instagram',
        'Quanto custa a consulta?',
        'Acho meio caro né...',
        'Aceita parcelamento?'
    ],
    'LEAD_WARM',
    '[
        {"scenario": "objecao_preco", "expected_action": "empilhar valor antes de falar preço"},
        {"scenario": "parcelamento", "expected_action": "oferecer cartão 10x"}
    ]'::jsonb
),
-- Persona TRIANGULAÇÃO: Marido agendando pra esposa
(
    'AMARE-TRIANGULACAO',
    'João - Marido Agendando pra Esposa',
    'Homem 55 anos agendando consulta para a esposa que está na menopausa.',
    '{
        "age": 55,
        "gender": "masculino",
        "location": "Marília - SP",
        "profession": "Empresário",
        "income": "classe A"
    }'::jsonb,
    '{
        "pain_level": "da esposa",
        "urgency": "media",
        "decision_power": "financeiro sim, saúde da esposa",
        "previous_attempts": "esposa já foi em outros",
        "knowledge_level": "indicação de amigo"
    }'::jsonb,
    ARRAY[
        'Oi, quero agendar pra minha esposa',
        'Ela tá muito mal, calorões toda hora',
        'Um amigo indicou o Dr. Luiz',
        'Quanto custa?'
    ],
    'LEAD_WARM',
    '[
        {"scenario": "triangulacao", "expected_action": "qualificar a esposa, envolver na conversa"},
        {"scenario": "agendamento_terceiro", "expected_action": "confirmar se esposa sabe e quer"}
    ]'::jsonb
)
ON CONFLICT (persona_code) DO UPDATE SET
    persona_name = EXCLUDED.persona_name,
    description = EXCLUDED.description,
    typical_messages = EXCLUDED.typical_messages;

-- 6. Verificação
SELECT 'Instituto Amare - Isabela V2 configurada com sucesso!' as status;

SELECT
    'Segment Strategy' as item,
    segment_code,
    segment_name
FROM growth_segment_strategies
WHERE segment_code = 'medicina-integrativa-feminina'

UNION ALL

SELECT
    'Client Config' as item,
    location_id,
    client_name
FROM growth_client_configs
WHERE location_id = 'instituto_amare_location_001'

UNION ALL

SELECT
    'Agent Template' as item,
    agent_code,
    agent_name
FROM growth_agent_templates
WHERE agent_code = 'ISABELA-AMARE-V2';
