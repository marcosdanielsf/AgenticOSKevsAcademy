"""
Message Generator - Gerador de Mensagens Personalizadas
========================================================
Gera mensagens de DM altamente personalizadas baseadas no perfil e score do lead.

Inclui suporte a SPINTAX para variação automática de mensagens:
- Sintaxe: {opção1|opção2|opção3}
- Evita detecção de spam pelo Instagram
- Cada mensagem é única
"""

import random
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


# ===========================================
# SPINTAX ENGINE
# ===========================================

def expand_spintax(text: str) -> str:
    """
    Expande spintax recursivamente.

    Sintaxe: {opção1|opção2|opção3}

    Exemplo:
        Input: "{Oi|Olá}, {tudo bem|como vai}?"
        Output: "Olá, como vai?" (aleatorizado)

    Suporta aninhamento:
        Input: "{Oi|{E aí|Fala}}, beleza?"
        Output: "E aí, beleza?" (aleatorizado)
    """
    if not text:
        return text

    pattern = r'\{([^{}]+)\}'

    def replace_match(match):
        options = match.group(1).split('|')
        return random.choice(options).strip()

    # Loop para resolver spintax aninhado
    max_iterations = 10
    iteration = 0
    while re.search(pattern, text) and iteration < max_iterations:
        text = re.sub(pattern, replace_match, text)
        iteration += 1

    return text


@dataclass
class GeneratedMessage:
    """Mensagem gerada com metadados"""
    message: str
    template_used: str
    personalization_level: str  # ultra, high, medium, low
    hooks_used: List[str]
    confidence: float  # 0-1
    spintax_used: bool = False


# ===========================================
# SPINTAX HÍBRIDO - Só elementos fixos
# Saudações e fechamentos variam, conteúdo é IA
# ===========================================

# Saudações com spintax (elemento fixo)
SPINTAX_GREETINGS = [
    "{Oi|Olá|E aí} {first_name}",
    "{first_name}, {tudo bem|beleza|tudo certo}?",
    "{Fala|E aí|Opa} {first_name}",
    "{first_name}",  # Direto ao ponto
]

# Fechamentos com spintax (elemento fixo)
SPINTAX_CLOSINGS = [
    "{Posso te fazer uma pergunta|Teria 2 min pra trocar uma ideia}?",
    "{Faz sentido|Faria sentido} a gente conversar?",
    "{Me conta|Conta pra mim}: como {tá|está} a captação de clientes {hoje|atualmente}?",
    "{Posso te explicar melhor|Te explico melhor} por aqui?",
    "{Queria te perguntar uma coisa|Tenho uma pergunta rápida}.",
    "{Posso te mandar um áudio|Te mando um áudio} de 1 min?",
]

# Fechamentos por nível de score
SPINTAX_CLOSINGS_BY_LEVEL = {
    "ultra": [
        "{Posso te fazer uma pergunta|Queria te perguntar uma coisa}?",
        "{Me conta|Conta pra mim}: como {tá|está} a captação {hoje|atualmente}?",
        "{Acho que faz sentido|Talvez faça sentido} a gente conversar.",
    ],
    "high": [
        "{Posso te fazer uma pergunta rápida|Teria 2 min}?",
        "{Faz sentido|Faria sentido} trocar uma ideia?",
        "{Posso te mandar um áudio|Te mando um áudio} de 1 min?",
    ],
    "medium": [
        "{Posso te fazer uma pergunta|Queria te perguntar}?",
        "{Faz sentido|Faria sentido} trocar uma ideia rápida?",
        "{Posso te contar algo|Te conto algo} que {pode te interessar|talvez te interesse}?",
    ]
}


class MessageGenerator:
    """
    Gera mensagens personalizadas para DMs do Instagram.

    Modo HÍBRIDO:
    - Saudação: Spintax (variação sintática)
    - Conteúdo: IA (personalização semântica baseada na bio)
    - Fechamento: Spintax (variação sintática)
    """

    # ===========================================
    # TEMPLATES ESTILO CHARLIE MORGAN
    # Curto, vago, curioso - baseado na bio
    # ===========================================

    # Templates ULTRA personalizados (score >= 70 + profissão)
    ULTRA_PERSONALIZED_TEMPLATES = [
        """{first_name}, vi que você trabalha com {profession}.

{bio_hook}

Posso te fazer uma pergunta?""",

        """{first_name}, curti seu perfil.

{bio_hook}

Teria 2 min pra trocar uma ideia?""",

        """Oi {first_name}

{bio_hook}

Acho que faz sentido a gente conversar. Posso te explicar o porquê?""",

        """{first_name}, passei pelo seu perfil.

{bio_hook}

Me conta uma coisa: como tá a captação de clientes hoje?"""
    ]

    # Templates personalizados (score >= 50)
    PERSONALIZED_TEMPLATES = [
        """{first_name}, vi seu perfil.

{bio_hook}

Posso te fazer uma pergunta rápida?""",

        """Oi {first_name}

{bio_hook}

Faz sentido trocar uma ideia sobre isso?""",

        """{first_name}, curti o que você faz.

{bio_hook}

Posso te mandar um áudio de 1 min explicando algo?""",

        """{first_name}

{bio_hook}

Teria interesse em saber como alguns {profession}s estão resolvendo isso?"""
    ]

    # Templates padrão (score < 50) - ainda curtos e curiosos
    STANDARD_TEMPLATES = [
        """{first_name}, tudo bem?

Vi seu perfil e achei interessante.

Posso te fazer uma pergunta?""",

        """Oi {first_name}

Passei pelo seu perfil.

Faz sentido trocar uma ideia rápida?""",

        """{first_name}

Curti seu trabalho.

Posso te contar algo que talvez te interesse?""",

        """{first_name}, beleza?

Vi que você é {profession}.

Me conta: como tá a demanda de clientes hoje?"""
    ]

    # ===========================================
    # HOOKS ESTILO CHARLIE MORGAN
    # Curtos, específicos, geram curiosidade
    # ===========================================

    # Hooks baseados em profissão (curtos e curiosos)
    PROFESSION_HOOKS = {
        'médico': [
            "Notei que você atende particular.",
            "Vi que você é da área de saúde.",
            "Sei como é corrida a rotina de consultório.",
        ],
        'dentista': [
            "Vi que você trabalha com estética dental.",
            "Notei seu trabalho com harmonização.",
            "Curti os resultados que você posta.",
        ],
        'advogado': [
            "Vi que você atua na área jurídica.",
            "Notei sua especialidade.",
            "Interessante seu posicionamento aqui.",
        ],
        'empresário': [
            "Vi que você empreende.",
            "Notei seu negócio.",
            "Curti a proposta da sua empresa.",
        ],
        'coach': [
            "Vi seu trabalho com desenvolvimento pessoal.",
            "Notei sua metodologia.",
            "Curti sua abordagem.",
        ],
        'consultor': [
            "Vi que você faz consultoria.",
            "Notei sua área de atuação.",
            "Interessante seu nicho.",
        ],
        'nutricionista': [
            "Vi seu trabalho com nutrição.",
            "Notei sua especialidade.",
            "Curti seu conteúdo sobre alimentação.",
        ],
        'psicólogo': [
            "Vi seu trabalho com saúde mental.",
            "Notei sua abordagem terapêutica.",
            "Curti seu conteúdo.",
        ],
        'marketing': [
            "Vi que você é da área de marketing.",
            "Notei seu trabalho com growth.",
            "Curti suas estratégias.",
        ],
        'estetica': [
            "Vi seu trabalho com estética.",
            "Notei seus resultados.",
            "Curti os antes e depois.",
        ],
        'fisioterapeuta': [
            "Vi seu trabalho com fisioterapia.",
            "Notei sua especialidade.",
            "Curti sua abordagem.",
        ],
        'personal': [
            "Vi seu trabalho como personal.",
            "Notei seus resultados com alunos.",
            "Curti sua metodologia.",
        ]
    }

    # Hooks baseados em interesses (curtos)
    INTEREST_HOOKS = {
        'marketing': "Notei que você manja de marketing.",
        'tecnologia': "Vi que você curte tecnologia.",
        'negocios': "Notei seu foco em negócios.",
        'estetica': "Vi que você é da área de estética.",
        'saude': "Notei que você é da área de saúde.",
        'financas': "Vi que você trabalha com finanças.",
        'educacao': "Notei seu trabalho com educação.",
        'fitness': "Vi seu trabalho com fitness.",
        'beleza': "Notei seu trabalho com beleza.",
        'longevidade': "Vi seu foco em longevidade.",
        'bem-estar': "Notei seu trabalho com bem-estar.",
    }

    def generate(
        self,
        profile: Dict[str, Any],
        score_data: Dict[str, Any]
    ) -> GeneratedMessage:
        """
        Gera mensagem personalizada para um lead.

        Args:
            profile: Dados do perfil do Instagram
            score_data: Dados do score (LeadScore.to_dict() ou similar)

        Returns:
            GeneratedMessage com a mensagem e metadados
        """
        # Extrair dados
        full_name = profile.get('full_name', profile.get('username', ''))
        first_name = self._extract_first_name(full_name)
        bio = profile.get('bio', '')

        profession = score_data.get('detected_profession')
        interests = score_data.get('detected_interests', [])
        location = score_data.get('detected_location')
        total_score = score_data.get('total_score', 0)
        priority = score_data.get('priority', 'nurturing')

        # Determinar nível de personalização
        if total_score >= 70 and profession:
            level = 'ultra'
            templates = self.ULTRA_PERSONALIZED_TEMPLATES
        elif total_score >= 50:
            level = 'high'
            templates = self.PERSONALIZED_TEMPLATES
        else:
            level = 'medium'
            templates = self.STANDARD_TEMPLATES

        # Escolher template
        template = random.choice(templates)

        # Preparar variáveis
        variables = {
            'first_name': first_name,
            'profession': profession or 'profissional',
            'location': location or '',
            'interest': interests[0] if interests else 'seu trabalho',
            'bio_hook': self._generate_bio_hook(bio, profession, interests)
        }

        # Gerar mensagem
        try:
            message = template.format(**variables)
        except KeyError:
            # Fallback se alguma variável faltar
            message = self.STANDARD_TEMPLATES[0].format(
                first_name=first_name,
                bio_hook='',
                profession='profissional',
                interest='seu trabalho',
                location=''
            )
            level = 'low'

        # Limpar mensagem
        message = self._clean_message(message)

        # Coletar hooks usados
        hooks_used = []
        if profession:
            hooks_used.append(f"profession:{profession}")
        if location:
            hooks_used.append(f"location:{location}")
        if interests:
            hooks_used.append(f"interests:{','.join(interests)}")

        return GeneratedMessage(
            message=message,
            template_used=template[:50] + '...',
            personalization_level=level,
            hooks_used=hooks_used,
            confidence=self._calculate_confidence(total_score, level)
        )

    def _extract_first_name(self, full_name: str) -> str:
        """Extrai primeiro nome"""
        if not full_name:
            return "Oi"

        # Remover títulos
        name = full_name.replace('Dr. ', '').replace('Dra. ', '')
        name = name.replace('Dr ', '').replace('Dra ', '')

        # Pegar primeiro nome
        parts = name.strip().split()
        if parts:
            return parts[0].title()

        return "Oi"

    def _generate_bio_hook(
        self,
        bio: str,
        profession: Optional[str],
        interests: List[str]
    ) -> str:
        """
        Gera hook CURIOSO baseado na bio - estilo Charlie Morgan.
        Prioriza informações específicas da bio sobre hooks genéricos.
        """
        hooks = []

        # PRIORIDADE 1: Extrair algo específico da bio
        if bio and len(bio) > 10:
            bio_lower = bio.lower()

            # Detectar especialidades específicas
            specialties = {
                'longevidade': 'Vi seu foco em longevidade.',
                'emagrecimento': 'Notei seu trabalho com emagrecimento.',
                'harmonização': 'Curti seu trabalho com harmonização.',
                'estética': 'Vi seus resultados com estética.',
                'botox': 'Notei seu trabalho com procedimentos.',
                'implante': 'Vi que você trabalha com implantes.',
                'ortodontia': 'Notei seu trabalho com ortodontia.',
                'personal': 'Vi seu trabalho como personal.',
                'crossfit': 'Notei que você é de crossfit.',
                'pilates': 'Vi seu trabalho com pilates.',
                'yoga': 'Notei seu trabalho com yoga.',
                'coaching': 'Vi que você faz coaching.',
                'mentoria': 'Notei que você faz mentoria.',
                'consultoria': 'Vi que você faz consultoria.',
                'dermatologia': 'Notei sua especialidade em dermato.',
                'cardiologia': 'Vi que você é cardiologista.',
                'ortopedia': 'Notei que você é ortopedista.',
                'ginecologia': 'Vi sua especialidade.',
                'pediatria': 'Notei que você atende crianças.',
                'psiquiatria': 'Vi seu trabalho com psiquiatria.',
                'nutrologia': 'Notei seu trabalho com nutrologia.',
                'endocrino': 'Vi que você é endócrino.',
                'integrativa': 'Notei seu foco em medicina integrativa.',
                'funcional': 'Vi seu trabalho com medicina funcional.',
                'clínica': 'Notei sua clínica.',
                'consultório': 'Vi que você tem consultório próprio.',
            }

            for keyword, hook in specialties.items():
                if keyword in bio_lower:
                    hooks.append(hook)
                    break

            # Extrair primeira parte da bio (antes de | ou 📍 ou •)
            if not hooks:
                for separator in ['|', '📍', '•', '🔹', '✨', '\n']:
                    if separator in bio:
                        first_part = bio.split(separator)[0].strip()
                        if 10 < len(first_part) < 50:
                            hooks.append(f"Vi que você trabalha com {first_part.lower()}.")
                            break

        # PRIORIDADE 2: Hook de profissão (se não achou nada específico)
        if not hooks and profession and profession in self.PROFESSION_HOOKS:
            hooks.extend(self.PROFESSION_HOOKS[profession])

        # PRIORIDADE 3: Hook de interesse
        if not hooks:
            for interest in interests:
                if interest in self.INTEREST_HOOKS:
                    hooks.append(self.INTEREST_HOOKS[interest])

        if hooks:
            return random.choice(hooks)

        return ""

    def _clean_message(self, message: str) -> str:
        """Limpa e formata a mensagem"""
        # Remover linhas vazias extras
        lines = message.split('\n')
        cleaned_lines = []
        prev_empty = False

        for line in lines:
            is_empty = not line.strip()
            if is_empty and prev_empty:
                continue
            cleaned_lines.append(line)
            prev_empty = is_empty

        message = '\n'.join(cleaned_lines)

        # Remover espaços extras
        message = message.strip()

        return message

    def _calculate_confidence(self, score: int, level: str) -> float:
        """Calcula confiança na personalização"""
        base = {
            'ultra': 0.9,
            'high': 0.7,
            'medium': 0.5,
            'low': 0.3
        }.get(level, 0.3)

        # Ajustar pelo score
        score_factor = min(score / 100, 1.0)

        return round((base + score_factor) / 2, 2)

    def generate_hybrid(
        self,
        profile: Dict[str, Any],
        score_data: Dict[str, Any],
        use_spintax: bool = True
    ) -> GeneratedMessage:
        """
        Gera mensagem com SPINTAX HÍBRIDO.

        Estrutura:
        - Saudação: Spintax (variação sintática anti-spam)
        - Conteúdo: IA (personalização semântica baseada na bio)
        - Fechamento: Spintax (variação sintática anti-spam)

        Args:
            profile: Dados do perfil do Instagram
            score_data: Dados do score
            use_spintax: Se True, expande spintax. Se False, retorna com sintaxe raw.

        Returns:
            GeneratedMessage com spintax expandido
        """
        # Extrair dados
        full_name = profile.get('full_name', profile.get('username', ''))
        first_name = self._extract_first_name(full_name)
        bio = profile.get('bio', '')

        profession = score_data.get('detected_profession')
        interests = score_data.get('detected_interests', [])
        total_score = score_data.get('total_score', 0)

        # Determinar nível
        if total_score >= 70:
            level = 'ultra'
        elif total_score >= 50:
            level = 'high'
        else:
            level = 'medium'

        # 1. SAUDAÇÃO (Spintax)
        greeting_template = random.choice(SPINTAX_GREETINGS)
        greeting = greeting_template.replace('{first_name}', first_name)

        # 2. CONTEÚDO (IA - personalizado pela bio)
        bio_hook = self._generate_bio_hook(bio, profession, interests)

        # 3. FECHAMENTO (Spintax por nível)
        closings = SPINTAX_CLOSINGS_BY_LEVEL.get(level, SPINTAX_CLOSINGS_BY_LEVEL['medium'])
        closing = random.choice(closings)

        # Montar mensagem
        if bio_hook:
            message = f"{greeting}\n\n{bio_hook}\n\n{closing}"
        else:
            message = f"{greeting}\n\n{closing}"

        # Expandir spintax se habilitado
        if use_spintax:
            message = expand_spintax(message)

        # Limpar
        message = self._clean_message(message)

        # Hooks usados
        hooks_used = ['spintax:hybrid']
        if profession:
            hooks_used.append(f"profession:{profession}")
        if interests:
            hooks_used.append(f"interests:{','.join(interests)}")

        return GeneratedMessage(
            message=message,
            template_used=f"hybrid:{level}",
            personalization_level=level,
            hooks_used=hooks_used,
            confidence=self._calculate_confidence(total_score, level),
            spintax_used=use_spintax
        )


# Funções helper
def generate_message(profile: Dict, score_data: Dict, hybrid: bool = False) -> GeneratedMessage:
    """
    Helper para gerar mensagem.

    Args:
        profile: Dados do perfil Instagram
        score_data: Dados do score
        hybrid: Se True, usa spintax híbrido (saudação/fechamento variados)

    Returns:
        GeneratedMessage
    """
    generator = MessageGenerator()
    if hybrid:
        return generator.generate_hybrid(profile, score_data)
    return generator.generate(profile, score_data)


def generate_message_hybrid(profile: Dict, score_data: Dict) -> GeneratedMessage:
    """Helper direto para modo híbrido (spintax + IA)"""
    generator = MessageGenerator()
    return generator.generate_hybrid(profile, score_data)
