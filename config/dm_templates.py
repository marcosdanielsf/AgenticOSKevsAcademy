#!/usr/bin/env python3
"""
DM Templates - Mensagens de Abordagem para Instagram
=====================================================
Templates personalizáveis para diferentes fases do Social Selling
"""

# ============================================
# FASE 1: FIRST CONTACT (Primeiro Contato)
# ============================================
FIRST_CONTACT_TEMPLATES = [
    {
        "id": "fc_01",
        "name": "Interesse Genuíno",
        "message": """Oi {first_name}! 👋

Vi seu perfil e achei muito interessante o trabalho que você faz com {specialty}.

Tenho acompanhado seu conteúdo sobre {topic} e queria te dar os parabéns pela qualidade.

Posso te fazer uma pergunta rápida sobre {specialty}?""",
        "variables": ["first_name", "specialty", "topic"],
        "best_for": ["médicos", "terapeutas", "coaches"]
    },
    {
        "id": "fc_02",
        "name": "Conexão Profissional",
        "message": """Olá {first_name}!

Trabalho com profissionais da área de {specialty} e seu perfil chamou minha atenção.

Adorei ver como você aborda {topic} de forma tão clara e acessível.

Podemos trocar uma ideia?""",
        "variables": ["first_name", "specialty", "topic"],
        "best_for": ["consultores", "profissionais liberais"]
    },
    {
        "id": "fc_03",
        "name": "Casual e Direto",
        "message": """E aí {first_name}! Tudo bem?

Curti muito seu conteúdo sobre {topic}. Você tem uma abordagem diferenciada que chama atenção.

Queria bater um papo contigo quando tiver um tempinho. O que acha?""",
        "variables": ["first_name", "topic"],
        "best_for": ["empreendedores", "criadores de conteúdo"]
    }
]

# ============================================
# FASE 2: WARMING UP (Aquecimento)
# ============================================
WARMING_UP_TEMPLATES = [
    {
        "id": "wu_01",
        "name": "Follow-up Engajamento",
        "message": """Oi {first_name}!

Vi que você curtiu/comentou no meu último post. Obrigado pelo engajamento!

Estava pensando em você quando criei aquele conteúdo sobre {topic}.

Como está sendo sua experiência com {pain_point}?""",
        "variables": ["first_name", "topic", "pain_point"],
        "timing": "2-3 dias após primeiro contato"
    },
    {
        "id": "wu_02",
        "name": "Valor Agregado",
        "message": """Oi {first_name}!

Lembrei de você quando li esse artigo sobre {topic}: [link]

Achei que poderia ser útil pra você considerando o trabalho que faz.

O que você achou?""",
        "variables": ["first_name", "topic"],
        "timing": "4-5 dias após primeiro contato"
    }
]

# ============================================
# FASE 3: QUALIFICATION (Qualificação)
# ============================================
QUALIFICATION_TEMPLATES = [
    {
        "id": "qa_01",
        "name": "Descoberta de Necessidade",
        "message": """Oi {first_name}!

Tenho conversado com vários profissionais de {specialty} e notei que muitos enfrentam {pain_point}.

Isso também é uma realidade pra você? Como você tem lidado com isso?""",
        "variables": ["first_name", "specialty", "pain_point"],
        "goal": "Identificar necessidade"
    },
    {
        "id": "qa_02",
        "name": "Sondagem de Interesse",
        "message": """Oi {first_name}!

Vi que você tem {followers_count} seguidores - parabéns pelo crescimento!

Já pensou em como transformar essa audiência em {desired_outcome}?

Tenho ajudado profissionais como você com isso.""",
        "variables": ["first_name", "followers_count", "desired_outcome"],
        "goal": "Qualificar interesse"
    }
]

# ============================================
# FASE 4: PRESENTATION (Apresentação)
# ============================================
PRESENTATION_TEMPLATES = [
    {
        "id": "pr_01",
        "name": "Convite para Conversa",
        "message": """Oi {first_name}!

Baseado no que conversamos, acho que tenho algo que pode te ajudar com {pain_point}.

Desenvolvi uma solução específica para {specialty} que tem gerado resultados interessantes.

Que tal uma call rápida de 15 min essa semana pra eu te mostrar?""",
        "variables": ["first_name", "pain_point", "specialty"],
        "call_to_action": "Agendar call"
    },
    {
        "id": "pr_02",
        "name": "Prova Social",
        "message": """Oi {first_name}!

Lembra que comentei sobre {solution}?

Acabei de ajudar outro {specialty} a alcançar {result}.

Posso te mostrar como funcionou pra ele e como pode funcionar pra você também?""",
        "variables": ["first_name", "solution", "specialty", "result"],
        "call_to_action": "Apresentar case"
    }
]

# ============================================
# FASE 5: CLOSING (Fechamento)
# ============================================
CLOSING_TEMPLATES = [
    {
        "id": "cl_01",
        "name": "Fechamento Suave",
        "message": """Oi {first_name}!

Depois da nossa conversa, montei uma proposta personalizada pra você.

Considerando sua situação com {pain_point}, acredito que essa solução vai te ajudar a {desired_outcome}.

Posso te enviar os detalhes?""",
        "variables": ["first_name", "pain_point", "desired_outcome"],
        "goal": "Enviar proposta"
    },
    {
        "id": "cl_02",
        "name": "Urgência Natural",
        "message": """Oi {first_name}!

Estou abrindo {limited_spots} vagas pro próximo grupo e lembrei de você.

Considerando o que conversamos sobre {pain_point}, acho que seria perfeito pra você.

Quer garantir uma vaga?""",
        "variables": ["first_name", "limited_spots", "pain_point"],
        "goal": "Criar urgência"
    }
]


# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def get_template(phase: str, template_id: str = None) -> dict:
    """Retorna um template específico ou aleatório da fase"""
    import random

    phases = {
        "first_contact": FIRST_CONTACT_TEMPLATES,
        "warming_up": WARMING_UP_TEMPLATES,
        "qualification": QUALIFICATION_TEMPLATES,
        "presentation": PRESENTATION_TEMPLATES,
        "closing": CLOSING_TEMPLATES
    }

    templates = phases.get(phase, FIRST_CONTACT_TEMPLATES)

    if template_id:
        for t in templates:
            if t["id"] == template_id:
                return t

    return random.choice(templates)


def render_message(template: dict, variables: dict) -> str:
    """Renderiza o template com as variáveis fornecidas"""
    message = template["message"]

    for key, value in variables.items():
        message = message.replace(f"{{{key}}}", str(value))

    return message.strip()


def extract_first_name(full_name: str) -> str:
    """Extrai o primeiro nome de um nome completo"""
    if not full_name:
        return ""

    # Remove títulos comuns
    name = full_name.replace("Dr. ", "").replace("Dra. ", "")
    name = name.replace("Dr ", "").replace("Dra ", "")

    return name.split()[0] if name else ""


# ============================================
# EXEMPLO DE USO
# ============================================
if __name__ == "__main__":
    # Exemplo de lead
    lead = {
        "full_name": "Dr. João Silva",
        "bio": "Cardiologista | Consultório em SP",
        "followers_count": 5420
    }

    # Pegar template de primeiro contato
    template = get_template("first_contact", "fc_01")

    # Variáveis para renderização
    variables = {
        "first_name": extract_first_name(lead["full_name"]),
        "specialty": "cardiologia",
        "topic": "saúde do coração"
    }

    # Renderizar mensagem
    message = render_message(template, variables)

    print("=" * 50)
    print("EXEMPLO DE MENSAGEM RENDERIZADA")
    print("=" * 50)
    print(message)
    print("=" * 50)
