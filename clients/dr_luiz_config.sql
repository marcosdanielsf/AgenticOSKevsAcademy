-- ============================================================================
-- GROWTH OS - CONFIGURAÇÃO DO PRIMEIRO CLIENTE: DR. LUIZ
-- ============================================================================
--
-- Cliente: Clínica Dr. Luiz (Medicina/Clínica Médica)
-- Location ID GHL: dr_luiz_location_001 (placeholder - substituir pelo real)
-- Data: 2026-01-04
--
-- IMPORTANTE: Executar APÓS a migração 007_growth_os_tables.sql
-- ============================================================================

-- 1. ESTRATÉGIA DE SEGMENTO PARA SAÚDE/MEDICINA (criar primeiro para FK)
-- ----------------------------------------------------------------------------
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
    'medicina-integrativa-particular',
    'Medicina Integrativa - Particular',

    -- Dores típicas do segmento
    ARRAY[
        'Médicos que não escutam',
        'Consultas de 5 minutos',
        'Tratamentos que só mascaram sintomas',
        'Falta de acompanhamento',
        'Dificuldade de agendar',
        'Longas esperas'
    ],

    -- Objeções típicas
    ARRAY[
        'Consulta particular é muito cara',
        'Meu convênio já paga médico',
        'Não sei se preciso de medicina integrativa',
        'Já fui em vários médicos e nenhum resolveu'
    ],

    -- Buyer persona típica
    '{
        "age_range": "35-60",
        "income_level": "classe A/B",
        "decision_style": "pesquisador",
        "primary_motivation": "saúde de qualidade",
        "communication_preference": "whatsapp"
    }'::jsonb,

    -- Ajustes de tom
    '{
        "formality_level": "semi-formal",
        "empathy_level": "alto",
        "technical_level": "baixo",
        "urgency_level": "moderado"
    }'::jsonb,

    -- Vocabulário preferido
    ARRAY['acolhimento', 'cuidado', 'atenção', 'escuta', 'tempo', 'qualidade de vida'],

    -- Palavras proibidas (ética médica)
    ARRAY[
        'cura garantida',
        'resultado garantido',
        'melhor médico',
        'único tratamento',
        'grátis',
        'promoção',
        'desconto'
    ],

    -- Perguntas BANT específicas
    '{
        "budget": "Você já fez consultas particulares antes ou usa convênio?",
        "authority": "A consulta seria pra você mesmo ou pra outra pessoa?",
        "need": "O que te motivou a buscar um médico diferente agora?",
        "timeline": "Você quer marcar consulta pra essa semana ou pode ser mais pra frente?"
    }'::jsonb,

    -- Estratégia de preço
    'Justificar valor com tempo de consulta (60 min vs 10 min convênio) e atenção personalizada. Nunca oferecer desconto.',

    -- Âncoras de valor
    ARRAY[
        'Consultas de 1 hora - tempo de verdade pra te ouvir',
        'Tratamento da causa, não só dos sintomas',
        'Acompanhamento contínuo pelo WhatsApp',
        'Visão integrativa: corpo e mente juntos'
    ],

    -- Melhores horários
    '{
        "weekdays": ["08:00-10:00", "12:00-14:00", "18:00-20:00"],
        "saturday": ["09:00-12:00"],
        "sunday": []
    }'::jsonb,

    -- Intervalos de follow-up
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
    updated_at = NOW();


-- 2. CONFIGURAÇÃO DO CLIENTE DR. LUIZ
-- ----------------------------------------------------------------------------
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
    canais_ativos,
    horario_inicio,
    horario_fim,
    timezone,
    perguntas_qualificacao,
    calendario_url,
    tempo_consulta_minutos,
    max_followups,
    intervalo_followup_horas,
    telefone_humano,
    email_humano,
    gatilhos_escalacao,
    segment_id,
    meta_leads_mes,
    meta_agendamentos_mes,
    meta_vendas_mes
) VALUES (
    -- Identificador (SUBSTITUIR pelo location_id real do GHL)
    'dr_luiz_location_001',
    'Clínica Dr. Luiz',

    -- Contexto do Negócio (6 variáveis essenciais)
    'Clínica Dr. Luiz - Medicina Integrativa',
    'Clínica Médica / Medicina Integrativa',
    'Consultas médicas personalizadas com abordagem integrativa que trata a causa, não só os sintomas',
    'Frustração com médicos que não escutam, tratamentos que só mascaram sintomas, falta de atenção no atendimento',
    'Homens e mulheres 35-60 anos, classe A/B, que valorizam saúde e querem um médico que realmente escute',

    -- Diferenciais
    ARRAY[
        'Consultas de 1 hora (não apressado)',
        'Abordagem integrativa (corpo + mente)',
        'Atendimento humanizado e personalizado',
        'Acompanhamento contínuo via WhatsApp',
        'Foco na causa, não só nos sintomas'
    ],

    -- Pricing
    'a partir de R$ 500',
    false,  -- Não mostrar preço antes de qualificar
    800.00, -- Ticket médio

    -- Personalidade do Agente
    'consultivo',
    'Julia',
    1,

    -- Canais ativos
    ARRAY['instagram', 'whatsapp'],

    -- Horários de atendimento
    '08:00',
    '18:00',
    'America/Sao_Paulo',

    -- Qualificação BANT customizada
    '{
        "budget": "Você já fez consultas particulares antes ou usa convênio?",
        "authority": "A consulta seria pra você mesmo ou pra outra pessoa?",
        "need": "O que te motivou a buscar um médico diferente agora?",
        "timeline": "Você quer marcar consulta pra essa semana ou pode ser mais pra frente?"
    }'::jsonb,

    -- Agendamento
    'https://calendly.com/drluiz/consulta',  -- SUBSTITUIR PELO REAL
    60,  -- Consulta de 1 hora

    -- Follow-up
    3,
    24,

    -- Escalação para humano
    '+55 11 99999-9999',  -- SUBSTITUIR PELO REAL
    'contato@drluiz.com.br',  -- SUBSTITUIR PELO REAL
    ARRAY['reclamação', 'urgência médica', 'emergência', 'insatisfação'],

    -- Referência ao segmento
    (SELECT id FROM growth_segment_strategies WHERE segment_code = 'medicina-integrativa-particular'),

    -- Metas mensais
    100,  -- meta_leads_mes
    30,   -- meta_agendamentos_mes
    20    -- meta_vendas_mes
) ON CONFLICT (location_id) DO UPDATE SET
    client_name = EXCLUDED.client_name,
    nome_empresa = EXCLUDED.nome_empresa,
    updated_at = NOW();


-- ============================================================================
-- PIPELINES GHL - CONFIGURAÇÃO MANUAL
-- ============================================================================
--
-- PIPELINE COMERCIAL (Renomear estágios do Funil "3- Recruiting"):
--   1. Novo Lead (10%)
--   2. Contactado (20%)
--   3. Qualificado (40%)
--   4. Agendado (60%)
--   5. Compareceu (75%)
--   6. Proposta (85%)
--   7. Fechado Ganho (100%)
--   8. Fechado Perdido (0%)
--
-- PIPELINE TRATAMENTO (Criar nova pipeline com 7 estágios):
--   1. Onboarding
--   2. Mês 1-2
--   3. Mês 3-4
--   4. Mês 5-6
--   5. Renovação
--   6. Concluído
--   7. Cancelado
--
-- ============================================================================


-- 3. TEMPLATE DE AGENTE CUSTOMIZADO PARA DR. LUIZ
-- ----------------------------------------------------------------------------
-- Nota: Este é um template específico para o Dr. Luiz baseado no SSIG-004 base
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
    'SSIG-DRLUIZ-001',                          -- agent_code
    'Julia - Assistente Dr. Luiz (Instagram)',  -- agent_name
    'inbound',                                  -- agent_category
    'operacional',                              -- agent_level
    'instagram',                                -- channel
    'inbound',                                  -- process_type

    -- system_prompt_template
    '### IDENTIDADE ###
Você é a Julia, assistente de atendimento da Clínica Dr. Luiz.
Seu tom é acolhedor e consultivo. Use português brasileiro natural.
Máximo 1 emoji por mensagem.

### SOBRE A CLÍNICA ###
- **Clínica**: {{NOME_EMPRESA}}
- **Especialidade**: Medicina Integrativa
- **Oferta**: {{OFERTA_PRINCIPAL}}
- **Diferencial**: Consultas de 1 hora, foco na causa

### DOR DO PACIENTE ###
A principal frustração: {{DOR_PRINCIPAL}}
Valide esse sentimento. Mostre que o Dr. Luiz é diferente.

### ESTILO DE COMUNICAÇÃO ###
1. **ACOLHIMENTO**: Primeiro valide o sentimento
2. **BREVIDADE**: Máximo 3 linhas por mensagem
3. **EMPATIA**: "Entendo como isso é frustrante"
4. **CURIOSIDADE**: Termine com pergunta aberta
5. **ÉTICA**: NUNCA prometa cura ou resultados

### O QUE NUNCA FAZER ###
- Prometer cura ou resultados específicos
- Dar diagnóstico ou sugestão de tratamento
- Falar mal de outros médicos
- Ser insistente ou agressivo
- Usar linguagem promocional

### QUALIFICAÇÃO ###
{{PERGUNTAS_QUALIFICACAO_JSON}}

### AGENDAMENTO ###
Quando qualificado, oferecer:
"O próximo passo seria uma consulta inicial com o Dr. Luiz.
São {{TEMPO_CONSULTA}} minutos pra ele entender seu caso com calma.
Prefere marcar pra essa semana ou semana que vem?"',

    -- available_modes
    ARRAY['first_contact', 'qualifier', 'scheduler', 'followuper'],

    -- few_shot_examples
    '[
        {
            "context": "Lead curtiu post sobre medicina integrativa",
            "lead_message": "Oi, gostei do post",
            "agent_response": "Oi! Que bom que gostou! Você tá buscando um médico que realmente escute ou só curtiu o conteúdo mesmo?",
            "why_works": "Pergunta aberta que qualifica interesse"
        },
        {
            "context": "Lead pergunta sobre preço",
            "lead_message": "Quanto custa a consulta?",
            "agent_response": "A consulta inicial é de R$500. Diferente de consultas de 10 minutos, aqui são 60 minutos pra o Dr. Luiz entender seu caso com calma. Você tá buscando um atendimento assim?",
            "why_works": "Justifica o valor com diferencial, requalifica"
        },
        {
            "context": "Lead com objeção de já ter ido em vários médicos",
            "lead_message": "Já fui em vários médicos e ninguém resolve meu problema",
            "agent_response": "Entendo essa frustração. É muito comum quando os médicos só olham exames e não escutam a história completa. Posso te perguntar: o que te levou a buscar um médico diferente agora?",
            "why_works": "Valida frustração, mostra diferencial implícito, pergunta sobre motivação"
        }
    ]'::jsonb,

    -- Handoff triggers
    '{
        "to_scheduler": ["quer agendar", "qual horário", "pode ser essa semana"],
        "to_objection_handler": ["caro", "não sei se preciso", "preciso pensar"],
        "to_human": ["urgência", "dor forte", "emergência", "reclamação"]
    }'::jsonb,

    -- expected_metrics
    '{
        "response_time_target_min": 30,
        "qualification_rate_target": 0.40,
        "schedule_rate_target": 0.30,
        "lead_score_avg_target": 70
    }'::jsonb,

    -- is_active
    true
)
ON CONFLICT (agent_code) DO UPDATE SET
    system_prompt_template = EXCLUDED.system_prompt_template,
    few_shot_examples = EXCLUDED.few_shot_examples,
    updated_at = NOW();


-- 4. ATIVAR AGENTE PARA O DR. LUIZ (instância compilada)
-- ----------------------------------------------------------------------------
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
    gat.id,
    gcc.id,
    'dr_luiz_location_001',
    'Julia - Social Seller Instagram (Dr. Luiz)',
    -- Prompt compilado com variáveis substituídas
    REPLACE(
        REPLACE(
            REPLACE(
                REPLACE(gat.system_prompt_template, '{{NOME_EMPRESA}}', gcc.nome_empresa),
                '{{OFERTA_PRINCIPAL}}', gcc.oferta_principal
            ),
            '{{DOR_PRINCIPAL}}', gcc.dor_principal
        ),
        '{{TEMPO_CONSULTA}}', gcc.tempo_consulta_minutos::TEXT
    ),
    -- Variáveis do cliente para referência
    jsonb_build_object(
        'nome_empresa', gcc.nome_empresa,
        'tipo_negocio', gcc.tipo_negocio,
        'oferta_principal', gcc.oferta_principal,
        'dor_principal', gcc.dor_principal,
        'publico_alvo', gcc.publico_alvo,
        'diferenciais', gcc.diferenciais,
        'nome_agente', gcc.nome_agente,
        'tempo_consulta', gcc.tempo_consulta_minutos
    ),
    'active'
FROM growth_agent_templates gat
CROSS JOIN growth_client_configs gcc
WHERE gat.agent_code = 'SSIG-DRLUIZ-001'
  AND gcc.location_id = 'dr_luiz_location_001'
ON CONFLICT (template_id, location_id) DO UPDATE SET
    compiled_prompt = EXCLUDED.compiled_prompt,
    client_variables = EXCLUDED.client_variables,
    updated_at = NOW();


-- 5. CRIAR PERSONAS DE TESTE PARA DR. LUIZ
-- ----------------------------------------------------------------------------
INSERT INTO growth_test_personas (
    persona_code,
    persona_name,
    persona_description,
    profile,
    behavior_traits,
    likely_objections,
    buying_signals,
    difficulty_level,
    simulation_prompt,
    success_criteria,
    is_active
) VALUES
(
    'DRLUIZ-PERS-001',
    'Maria - Paciente Frustrada',
    'Empresária de 45 anos frustrada com médicos que não escutam. Hot buyer com alta urgência.',
    -- profile
    '{
        "age": 45,
        "gender": "female",
        "occupation": "Empresária",
        "pain_level": 9,
        "budget_available": true,
        "is_decision_maker": true,
        "timeline_urgency": 8,
        "backstory": "Já foi em 5 médicos diferentes nos últimos 2 anos. Todos passam remédio mas ninguém escuta. Está cansada e quer um médico diferente."
    }'::jsonb,
    -- behavior_traits
    '{
        "response_style": "medium",
        "patience_level": 6,
        "skepticism_level": 4,
        "decisiveness": 8
    }'::jsonb,
    -- likely_objections
    ARRAY['Já fui em vários médicos', 'Ninguém resolve meu problema'],
    -- buying_signals
    ARRAY['Ele realmente escuta?', 'Quanto tempo dura a consulta?', 'Posso marcar pra essa semana?'],
    -- difficulty_level
    'easy',
    -- simulation_prompt
    'Você é Maria, 45 anos, empresária. Está MUITO frustrada porque já foi em 5 médicos nos últimos 2 anos e nenhum resolveu seus problemas de saúde. Todos passam remédio rápido e não escutam. Você quer um médico diferente que realmente preste atenção. Quando convencida de que o Dr. Luiz é diferente, você quer agendar logo. Responda de forma natural, com respostas médias (2-3 frases).',
    -- success_criteria
    '{
        "must_reach_stage": "scheduled",
        "min_score": 80,
        "max_messages": 10,
        "expected_handoff": "scheduler"
    }'::jsonb,
    true
),
(
    'DRLUIZ-PERS-002',
    'João - Cético do Preço',
    'Gerente de 52 anos com plano de saúde que questiona por que pagar consulta particular.',
    -- profile
    '{
        "age": 52,
        "gender": "male",
        "occupation": "Gerente",
        "pain_level": 6,
        "budget_available": true,
        "is_decision_maker": true,
        "timeline_urgency": 4,
        "backstory": "Tem plano de saúde bom e acha que não precisa pagar consulta particular. Mas está curioso sobre a abordagem diferente."
    }'::jsonb,
    -- behavior_traits
    '{
        "response_style": "short",
        "patience_level": 4,
        "skepticism_level": 8,
        "decisiveness": 5
    }'::jsonb,
    -- likely_objections
    ARRAY['Por que pagar se tenho convênio?', '500 reais é muito caro', 'Qual a diferença real?'],
    -- buying_signals
    ARRAY['Se fosse um valor menor...', 'Qual a diferença pro convênio?', 'Quanto tempo dura?'],
    -- difficulty_level
    'medium',
    -- simulation_prompt
    'Você é João, 52 anos, gerente. Tem um bom plano de saúde e acha estranho pagar R$500 numa consulta particular. Mas está curioso porque ouviu falar que medicina integrativa é diferente. Faça perguntas sobre preço e questione o valor. Só se convença se o agente justificar bem o diferencial. Respostas curtas (1-2 frases).',
    -- success_criteria
    '{
        "must_reach_stage": "qualified",
        "min_score": 65,
        "max_messages": 12,
        "expected_handoff": "objection_handler"
    }'::jsonb,
    true
),
(
    'DRLUIZ-PERS-003',
    'Ana - Pesquisadora',
    'Advogada de 38 anos interessada em medicina preventiva. Pesquisa muito antes de decidir.',
    -- profile
    '{
        "age": 38,
        "gender": "female",
        "occupation": "Advogada",
        "pain_level": 4,
        "budget_available": true,
        "is_decision_maker": true,
        "timeline_urgency": 2,
        "backstory": "Está interessada em medicina preventiva. Não tem problema urgente, só quer se cuidar melhor. Pesquisa bastante antes de decidir."
    }'::jsonb,
    -- behavior_traits
    '{
        "response_style": "verbose",
        "patience_level": 9,
        "skepticism_level": 6,
        "decisiveness": 3
    }'::jsonb,
    -- likely_objections
    ARRAY['Preciso pesquisar mais', 'Vou pensar', 'Quais as credenciais do médico?'],
    -- buying_signals
    ARRAY['Vocês trabalham com prevenção?', 'Qual a formação do Dr. Luiz?', 'Como funciona o acompanhamento?'],
    -- difficulty_level
    'hard',
    -- simulation_prompt
    'Você é Ana, 38 anos, advogada. Está interessada em medicina preventiva e qualidade de vida. Não tem urgência, só quer se cuidar melhor a longo prazo. Você pesquisa MUITO antes de decidir qualquer coisa. Faça perguntas detalhadas sobre a formação do médico, a metodologia, como funciona o acompanhamento. Diga que vai pensar e pesquisar mais. Respostas longas (3-4 frases).',
    -- success_criteria
    '{
        "must_reach_stage": "lead",
        "min_score": 55,
        "max_messages": 15,
        "expected_handoff": "nurture"
    }'::jsonb,
    true
)
ON CONFLICT (persona_code) DO UPDATE SET
    persona_description = EXCLUDED.persona_description,
    profile = EXCLUDED.profile,
    behavior_traits = EXCLUDED.behavior_traits,
    simulation_prompt = EXCLUDED.simulation_prompt;


-- 6. VERIFICAÇÃO FINAL
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    v_client_count INTEGER;
    v_agent_count INTEGER;
    v_persona_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_client_count
    FROM growth_client_configs
    WHERE location_id = 'dr_luiz_location_001';

    SELECT COUNT(*) INTO v_agent_count
    FROM growth_agent_templates
    WHERE agent_code LIKE 'SSIG-DRLUIZ%';

    SELECT COUNT(*) INTO v_persona_count
    FROM growth_test_personas
    WHERE persona_code LIKE 'DRLUIZ%';

    RAISE NOTICE '=== CONFIGURAÇÃO DR. LUIZ ===';
    RAISE NOTICE 'Clientes configurados: %', v_client_count;
    RAISE NOTICE 'Templates de agente: %', v_agent_count;
    RAISE NOTICE 'Personas de teste: %', v_persona_count;
    RAISE NOTICE '=============================';
END $$;
