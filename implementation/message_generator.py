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
    # Foco no bio_hook específico, sem usar {profession} genérico
    ULTRA_PERSONALIZED_TEMPLATES = [
        """{first_name}, passei pelo seu perfil.

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
    # Foco no bio_hook específico, evitar {profession} genérico
    PERSONALIZED_TEMPLATES = [
        """{first_name}, vi seu perfil.

{bio_hook}

Posso te fazer uma pergunta rápida?""",

        """Oi {first_name}

{bio_hook}

Faz sentido trocar uma ideia sobre isso?""",

        """{first_name}, curti o que você faz.

{bio_hook}

Posso te mandar um áudio de 1 min?""",

        """{first_name}

{bio_hook}

Teria interesse em saber como outros profissionais da área estão resolvendo isso?"""
    ]

    # Templates padrão (score < 50) - curtos e curiosos
    # Evitar {profession} genérico, usar bio_hook quando disponível
    STANDARD_TEMPLATES = [
        """{first_name}, tudo bem?

{bio_hook}

Posso te fazer uma pergunta?""",

        """Oi {first_name}

Passei pelo seu perfil.

Faz sentido trocar uma ideia rápida?""",

        """{first_name}

Curti seu trabalho.

Posso te contar algo que talvez te interesse?""",

        """{first_name}, beleza?

{bio_hook}

Como tá a demanda de clientes hoje?"""
    ]

    # ===========================================
    # HOOKS ESTILO CHARLIE MORGAN
    # Curtos, específicos, geram curiosidade
    # ===========================================

    # Hooks baseados em profissão - estilo Charlie Morgan (curtos, curiosos, específicos)
    PROFESSION_HOOKS = {
        'médico': [
            "Sei como é corrida a rotina de consultório.",
            "Notei que você atende na área de saúde.",
            "Trabalho com vários médicos que estão escalando a agenda.",
        ],
        'dentista': [
            "Curti os resultados que você posta.",
            "Sei como funciona o mercado de odontologia premium.",
            "Trabalho com vários dentistas que estão lotando a agenda.",
        ],
        'advogado': [
            "Interessante seu posicionamento aqui.",
            "Sei como funciona a captação no jurídico.",
            "Trabalho com vários advogados que estão gerando demanda previsível.",
        ],
        'empresário': [
            "Curti a proposta do seu negócio.",
            "Notei que você empreende na área.",
            "Trabalho com vários empresários que estão escalando.",
        ],
        'coach': [
            "Curti sua abordagem.",
            "Sei como funciona o mercado de coaching.",
            "Trabalho com vários coaches que estão lotando turmas.",
        ],
        'consultor': [
            "Interessante seu nicho de atuação.",
            "Sei como funciona a geração de demanda em consultoria.",
            "Trabalho com vários consultores que estão escalando.",
        ],
        'nutricionista': [
            "Curti seu conteúdo sobre alimentação.",
            "Sei como funciona o mercado de nutrição.",
            "Trabalho com vários nutris que estão lotando a agenda.",
        ],
        'psicólogo': [
            "Curti seu conteúdo sobre saúde mental.",
            "Sei como funciona a captação em psicologia.",
            "Trabalho com vários psicólogos que estão gerando demanda.",
        ],
        'marketing': [
            "Curti suas estratégias.",
            "Interessante sua abordagem de growth.",
            "Vi que você manja de aquisição.",
        ],
        'estetica': [
            "Curti os antes e depois.",
            "Sei como funciona o mercado de estética.",
            "Trabalho com várias clínicas que estão lotando.",
        ],
        'fisioterapeuta': [
            "Curti sua abordagem.",
            "Sei como funciona o mercado de fisio.",
            "Trabalho com vários fisios que estão gerando demanda.",
        ],
        'personal': [
            "Curti sua metodologia.",
            "Sei como funciona a captação de alunos.",
            "Trabalho com vários personais que estão lotando a agenda.",
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
            'bio_hook': self._generate_bio_hook(bio, profession, interests, profile)
        }

        # Gerar mensagem
        try:
            message = template.format(**variables)
        except KeyError:
            # Fallback se alguma variável faltar
            message = f"""{first_name}, tudo bem?

Passei pelo seu perfil.

Posso te fazer uma pergunta?"""
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
        interests: List[str],
        profile: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Gera hook CURIOSO baseado na bio - estilo Charlie Morgan.

        PRIORIDADES DE PERSONALIZAÇÃO:
        1. Escala de negócio (múltiplas clínicas/empresas)
        2. Operação internacional
        3. Especialidades específicas extraídas da bio
        4. Dados de autoridade (verificado, followers)
        5. Profissão genérica (fallback)
        """
        hooks = []
        bio_lower = bio.lower() if bio else ''

        # Extrair dados do profile se disponível
        is_verified = profile.get('is_verified', False) if profile else False
        followers = profile.get('follower_count', 0) if profile else 0
        username = profile.get('username', '') if profile else ''

        # ===========================================
        # PRIORIDADE 1: ESCALA DE NEGÓCIO
        # Múltiplas clínicas/empresas = hook premium
        # ===========================================

        # Detectar @mentions (indica múltiplos negócios)
        mentions = re.findall(r'@[\w\.]+', bio) if bio else []
        if len(mentions) >= 2:
            hooks.append(f"Vi que você comanda mais de um negócio.")
            hooks.append(f"Notei que você tem múltiplas operações.")
            hooks.append(f"Curti que você diversificou os negócios.")

        # Detectar múltiplas clínicas/unidades
        multi_unit_patterns = [
            (r'fundador[a]?\s+(?:da|de|do)?\s*[@\w\s,]+,\s*[@\w\s,]+',
             "Vi que você é fundador de mais de uma clínica."),
            (r'\d+\s*(?:clínicas?|unidades?|filiais?)',
             "Notei a expansão com múltiplas unidades."),
            (r'(?:rede|grupo)\s+(?:de\s+)?(?:clínicas?|consultórios?)',
             "Vi que você construiu uma rede."),
        ]

        for pattern, hook in multi_unit_patterns:
            if re.search(pattern, bio_lower):
                hooks.append(hook)
                break

        # ===========================================
        # PRIORIDADE 2: OPERAÇÃO INTERNACIONAL
        # Atuação em múltiplos países = hook premium
        # ===========================================

        international_markers = {
            'usa': ['usa', 'eua', 'estados unidos', 'miami', 'orlando', 'new york', 'los angeles'],
            'mexico': ['méxico', 'mexico', 'cancun', 'ciudad de méxico'],
            'dominican': ['república dominicana', 'dominican republic', 'santo domingo', 'punta cana'],
            'europe': ['portugal', 'espanha', 'españa', 'italia', 'london', 'paris'],
            'latam': ['argentina', 'chile', 'colombia', 'peru'],
        }

        countries_found = []
        for region, markers in international_markers.items():
            for marker in markers:
                if marker in bio_lower:
                    countries_found.append(region)
                    break

        if len(countries_found) >= 2:
            hooks.append("Vi que você atende internacionalmente.")
            hooks.append("Notei sua operação em múltiplos países.")
            hooks.append("Curti a expansão internacional.")
        elif len(countries_found) == 1 and 'brasil' not in bio_lower:
            hooks.append("Vi que você atende fora do Brasil também.")

        # ===========================================
        # PRIORIDADE 3: ESPECIALIDADES ESPECÍFICAS
        # Procedimentos/técnicas específicas
        # ===========================================

        if not hooks and bio:
            # Especialidades cirúrgicas específicas
            surgical_specialties = {
                'cirurgião plástico': 'Vi seu trabalho com cirurgia plástica.',
                'cirurgia plástica': 'Vi seu trabalho com cirurgia plástica.',
                'plástica': 'Vi seu trabalho com cirurgia plástica.',
                'lipoaspiração': 'Vi seus resultados com lipo.',
                'lipo': 'Vi seus resultados com lipo.',
                'abdominoplastia': 'Notei seu trabalho com abdominoplastia.',
                'rinoplastia': 'Vi que você faz rinoplastia.',
                'mamoplastia': 'Notei seu trabalho com mamas.',
                'mamas': 'Notei seu trabalho com mamas.',
                'prótese': 'Vi seus resultados com prótese.',
                'silicone': 'Vi seus resultados com prótese.',
                'lifting': 'Notei seu trabalho com lifting.',
                'blefaroplastia': 'Vi que você faz blefaroplastia.',
                'bichectomia': 'Notei seu trabalho com bichectomia.',
                'otoplastia': 'Vi que você faz otoplastia.',
            }

            # Especialidades estéticas não-cirúrgicas
            aesthetic_specialties = {
                'harmonização': 'Curti seu trabalho com harmonização.',
                'bioestimulador': 'Vi seu trabalho com bioestimuladores.',
                'fios': 'Notei seu trabalho com fios.',
                'skinbooster': 'Vi seus resultados com skinbooster.',
                'preenchimento': 'Curti seu trabalho com preenchimento.',
                'botox': 'Vi seus resultados com toxina.',
                'toxina': 'Vi seus resultados com toxina.',
                'peeling': 'Notei seu trabalho com peelings.',
                'laser': 'Vi seu trabalho com laser.',
            }

            # Especialidades médicas gerais
            medical_specialties = {
                'longevidade': 'Vi seu foco em longevidade.',
                'emagrecimento': 'Notei seu trabalho com emagrecimento.',
                'metabólica': 'Vi seu foco em saúde metabólica.',
                'integrativa': 'Notei seu foco em medicina integrativa.',
                'funcional': 'Vi seu trabalho com medicina funcional.',
                'nutrologia': 'Notei seu trabalho com nutrologia.',
                'endocrinologia': 'Vi que você é endócrino.',
                'dermatologia': 'Notei sua especialidade em dermato.',
                'cardiologia': 'Vi que você é cardiologista.',
                'ortopedia': 'Notei que você é ortopedista.',
            }

            # Especialidades business/coaching
            business_specialties = {
                'mentoria': 'Vi que você faz mentoria.',
                'coaching': 'Notei seu trabalho com coaching.',
                'consultoria': 'Vi que você faz consultoria.',
                'infoproduto': 'Notei seu infoproduto.',
                'curso': 'Vi que você tem curso.',
                'método': 'Notei seu método.',
                'treinamento': 'Vi seu trabalho com treinamentos.',
            }

            all_specialties = {
                **surgical_specialties,
                **aesthetic_specialties,
                **medical_specialties,
                **business_specialties
            }

            for keyword, hook in all_specialties.items():
                if keyword in bio_lower:
                    hooks.append(hook)
                    break

        # ===========================================
        # PRIORIDADE 4: AUTORIDADE/SOCIAL PROOF
        # Verificado, muitos followers
        # ===========================================

        if not hooks:
            if is_verified:
                hooks.append("Vi que você é verificado no Instagram.")
                hooks.append("Notei o selo de verificado.")
            elif followers >= 50000:
                hooks.append("Vi que você tem uma audiência grande.")
                hooks.append("Notei sua comunidade engajada.")
            elif followers >= 10000:
                hooks.append("Vi que você construiu uma boa audiência.")

        # ===========================================
        # PRIORIDADE 5: EXTRAÇÃO GENÉRICA DA BIO
        # Primeira parte relevante da bio (evitar termos genéricos)
        # ===========================================

        # Termos muito genéricos que não geram personalização
        generic_terms = [
            'médico', 'medico', 'dentista', 'advogado', 'coach',
            'empresário', 'empresario', 'consultor', 'especialista',
            'profissional', 'empreendedor', 'dono', 'fundador',
            'ceo', 'diretor', 'gerente', 'sócio', 'socio'
        ]

        if not hooks and bio:
            # Tentar extrair o "título" da bio (antes dos separadores)
            for separator in ['|', '📍', '•', '🔹', '✨', '👇', '⬇', '\n']:
                if separator in bio:
                    first_part = bio.split(separator)[0].strip()
                    # Limpar emojis do início
                    first_part = re.sub(r'^[\U0001F300-\U0001F9FF\s]+', '', first_part)
                    first_part_lower = first_part.lower()

                    # Verificar se NÃO é termo genérico
                    is_generic = any(term in first_part_lower for term in generic_terms)

                    if 5 < len(first_part) < 40 and not is_generic:
                        # Não usar se for só emoji
                        if not re.match(r'^[\U0001F300-\U0001F9FF\s]+$', first_part):
                            hooks.append(f"Vi que você trabalha com {first_part_lower}.")
                        break

        # ===========================================
        # PRIORIDADE 6: PROFISSÃO GENÉRICA (FALLBACK)
        # ===========================================

        if not hooks and profession and profession in self.PROFESSION_HOOKS:
            hooks.extend(self.PROFESSION_HOOKS[profession])

        # ===========================================
        # PRIORIDADE 7: INTERESSE (ÚLTIMO FALLBACK)
        # ===========================================

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

        # 2. CONTEÚDO (IA - personalizado pela bio + dados do profile)
        bio_hook = self._generate_bio_hook(bio, profession, interests, profile)

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
