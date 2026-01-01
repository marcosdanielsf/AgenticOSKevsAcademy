"""
Message Generator - Gerador de Mensagens Personalizadas
========================================================
Gera mensagens de DM altamente personalizadas baseadas no perfil e score do lead.
"""

import random
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class GeneratedMessage:
    """Mensagem gerada com metadados"""
    message: str
    template_used: str
    personalization_level: str  # ultra, high, medium, low
    hooks_used: List[str]
    confidence: float  # 0-1


class MessageGenerator:
    """
    Gera mensagens personalizadas para DMs do Instagram.
    Usa dados do perfil e score para personalização.
    """

    # Templates por nível de personalização
    ULTRA_PERSONALIZED_TEMPLATES = [
        """Oi {first_name}! 👋

Vi que você é {profession} em {location}. Muito legal o trabalho que você faz!

{bio_hook}

Tenho ajudado outros {profession}s a automatizar a prospecção de clientes no Instagram. Resultados têm sido bem interessantes.

Posso te mostrar como funciona?""",

        """E aí {first_name}!

Curti muito seu perfil. {bio_hook}

Trabalho com automação de prospecção no Instagram e vi que você provavelmente recebe muitas mensagens genéricas aqui...

A diferença é que eu realmente olhei seu perfil antes de escrever 😅

Posso te fazer uma pergunta rápida sobre {interest}?""",

        """{first_name}, tudo bem?

Notei que você trabalha com {profession} - área que admiro muito.

{bio_hook}

Desenvolvi uma solução que ajuda profissionais como você a encontrar clientes ideais de forma automatizada.

Vale uma conversa de 5 min?"""
    ]

    PERSONALIZED_TEMPLATES = [
        """Oi {first_name}! 👋

{bio_hook}

Trabalho com automação de prospecção e acho que posso te ajudar a encontrar mais clientes no Instagram.

Interesse em saber mais?""",

        """E aí {first_name}!

Vi seu perfil e achei interessante seu trabalho com {interest}.

Tenho uma solução de automação que pode te economizar horas por dia na prospecção.

Quer que eu te explique em 2 minutos?""",

        """{first_name}, tudo bem?

Passei pelo seu perfil e vi que você é {profession}.

Ajudo profissionais como você a automatizar a captação de clientes no Instagram.

Posso te mostrar como funciona?"""
    ]

    STANDARD_TEMPLATES = [
        """Oi {first_name}! 👋

Tudo bem? Vi seu perfil e achei interessante.

Trabalho com automação de prospecção no Instagram - ajudando profissionais a encontrar clientes de forma mais eficiente.

Quer saber mais?""",

        """E aí {first_name}!

Prazer! Passei pelo seu perfil e resolvi mandar uma mensagem.

Desenvolvo soluções de automação para Instagram. Posso te mostrar como funciona?""",

        """{first_name}, tudo certo?

Sou especialista em automação de prospecção no Instagram.

Se você busca mais clientes, posso te ajudar. Interesse em uma conversa rápida?"""
    ]

    # Hooks baseados em profissão
    PROFESSION_HOOKS = {
        'médico': [
            "Sei que a rotina de consultório é corrida, mas tenho algo que pode te interessar.",
            "Muitos médicos têm usado automação para captar mais pacientes particulares.",
        ],
        'dentista': [
            "Tenho trabalhado com vários dentistas que querem mais pacientes de estética.",
            "A captação de pacientes mudou muito - automação tá fazendo diferença.",
        ],
        'advogado': [
            "Advogados que prospectam bem no Instagram têm se destacado muito.",
            "Captação de clientes para advocacia tá cada vez mais digital.",
        ],
        'empresário': [
            "Empresários que automatizam a prospecção conseguem escalar muito mais rápido.",
            "Automação de vendas é o que mais cresce entre empresários que conheço.",
        ],
        'coach': [
            "Coaches que automatizam a captação conseguem focar mais na entrega.",
            "A prospecção manual rouba muito tempo que poderia ir para os alunos.",
        ],
        'consultor': [
            "Consultores de sucesso estão todos automatizando a captação.",
            "Prospectar manualmente é coisa do passado para consultores.",
        ],
        'nutricionista': [
            "Nutricionistas que automatizam a captação triplicam os atendimentos.",
            "Muitos nutris estão crescendo rápido com automação de Instagram.",
        ],
        'psicólogo': [
            "Psicólogos que usam automação conseguem ajudar mais pessoas.",
            "A demanda por saúde mental tá alta - automação ajuda a alcançar quem precisa.",
        ],
        'marketing': [
            "Quem é de marketing sabe que automação é o futuro.",
            "Profissionais de marketing adoram quando mostro as métricas da automação.",
        ],
        'desenvolvedor': [
            "Devs geralmente adoram ver a arquitetura da automação que criei.",
            "Acho que você vai curtir o lado técnico da solução.",
        ]
    }

    # Hooks baseados em interesses
    INTEREST_HOOKS = {
        'marketing': "Vi que você curte marketing/growth - isso vai te interessar.",
        'tecnologia': "Como você é de tech, vai entender rápido o poder da automação.",
        'negocios': "Para quem foca em negócios, isso pode ser um game changer.",
        'estetica': "O mercado de estética é perfeito para prospecção automatizada.",
        'saude': "Profissionais de saúde estão cada vez mais usando automação.",
        'financas': "O ROI dessa automação é muito claro - você vai gostar dos números.",
        'educacao': "Quem trabalha com educação pode escalar muito com automação."
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
        """Gera um hook personalizado baseado na bio"""
        hooks = []

        # Hook de profissão
        if profession and profession in self.PROFESSION_HOOKS:
            hooks.extend(self.PROFESSION_HOOKS[profession])

        # Hook de interesse
        for interest in interests:
            if interest in self.INTEREST_HOOKS:
                hooks.append(self.INTEREST_HOOKS[interest])

        # Hook genérico da bio
        if bio and len(bio) > 20:
            # Extrair algo interessante da bio
            if '|' in bio:
                parts = bio.split('|')
                if len(parts) > 1:
                    hooks.append(f"Vi que você trabalha com {parts[0].strip()}.")

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


# Função helper
def generate_message(profile: Dict, score_data: Dict) -> GeneratedMessage:
    """Helper para gerar mensagem"""
    generator = MessageGenerator()
    return generator.generate(profile, score_data)
