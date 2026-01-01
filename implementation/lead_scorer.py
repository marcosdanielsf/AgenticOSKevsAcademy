"""
Lead Scorer - Sistema de Pontuação Semântica
=============================================
Calcula score de 0-100 para leads baseado em dados do perfil.
Determina prioridade e tipo de abordagem.
"""

import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


class LeadPriority(Enum):
    """Prioridade do lead baseada no score"""
    HOT = "hot"           # Score >= 70: DM imediato
    WARM = "warm"         # Score 50-69: DM em 24h
    COLD = "cold"         # Score 40-49: DM em 48h
    NURTURING = "nurturing"  # Score < 40: Não enviar DM


@dataclass
class LeadScore:
    """Resultado da pontuação de um lead"""
    username: str
    total_score: int
    priority: LeadPriority

    # Breakdown do score
    bio_score: int = 0
    engagement_score: int = 0
    profile_score: int = 0
    recency_score: int = 0

    # Dados extraídos
    detected_profession: Optional[str] = None
    detected_interests: List[str] = None
    detected_location: Optional[str] = None
    is_decision_maker: bool = False

    # Recomendações
    recommended_template: str = "standard"
    personalization_hooks: List[str] = None
    approach_notes: Optional[str] = None

    def __post_init__(self):
        if self.detected_interests is None:
            self.detected_interests = []
        if self.personalization_hooks is None:
            self.personalization_hooks = []


class LeadScorer:
    """
    Calcula score semântico de leads baseado em dados do perfil.
    Score máximo: 100 pontos.
    """

    # Profissões de decisores (alto valor)
    DECISION_MAKER_KEYWORDS = [
        # Português
        'ceo', 'fundador', 'founder', 'dono', 'proprietário', 'diretor',
        'empresário', 'empreendedor', 'sócio', 'gestor', 'gerente',
        'executivo', 'c-level', 'head', 'líder', 'coordenador',
        # Profissionais liberais
        'médico', 'médica', 'dr.', 'dra.', 'advogado', 'advogada',
        'dentista', 'arquiteto', 'engenheiro', 'psicólogo', 'nutricionista',
        'fisioterapeuta', 'coach', 'consultor', 'consultora',
        # Inglês
        'entrepreneur', 'business owner', 'manager', 'director'
    ]

    # Interesses relevantes
    INTEREST_KEYWORDS = {
        'marketing': ['marketing', 'growth', 'vendas', 'sales', 'leads', 'tráfego'],
        'tecnologia': ['tech', 'startup', 'saas', 'software', 'automação', 'ia', 'ai'],
        'negocios': ['business', 'negócio', 'empresa', 'empreend', 'lucro', 'faturamento'],
        'estetica': ['estética', 'beleza', 'clínica', 'procedimento', 'harmonização'],
        'saude': ['saúde', 'bem-estar', 'fitness', 'nutrição', 'medicina'],
        'financas': ['investimento', 'finanças', 'renda', 'dinheiro', 'patrimônio'],
        'educacao': ['curso', 'mentoria', 'treinamento', 'ensino', 'educação']
    }

    # Localizações de alto valor (Brasil)
    HIGH_VALUE_LOCATIONS = [
        'sp', 'são paulo', 'sao paulo', 'sampa',
        'rj', 'rio de janeiro', 'rio',
        'bh', 'belo horizonte',
        'brasília', 'brasilia', 'df',
        'curitiba', 'porto alegre', 'florianópolis', 'salvador',
        'recife', 'fortaleza', 'campinas'
    ]

    def calculate_score(self, profile: Dict[str, Any]) -> LeadScore:
        """
        Calcula score completo de um lead.

        Args:
            profile: Dados do perfil (InstagramProfile.to_dict())

        Returns:
            LeadScore com pontuação e recomendações
        """
        username = profile.get('username', '')
        bio = (profile.get('bio') or '').lower()
        full_name = (profile.get('full_name') or '').lower()

        score = LeadScore(username=username, total_score=0, priority=LeadPriority.NURTURING)

        # 1. SCORE DA BIO E DEMOGRAFIA (30 pontos)
        score.bio_score = self._calculate_bio_score(bio, full_name, profile)

        # 2. SCORE DE ENGAJAMENTO (30 pontos)
        score.engagement_score = self._calculate_engagement_score(profile)

        # 3. SCORE DO PERFIL (25 pontos)
        score.profile_score = self._calculate_profile_score(profile)

        # 4. SCORE DE RECÊNCIA (15 pontos)
        score.recency_score = self._calculate_recency_score(profile)

        # Calcular total
        score.total_score = (
            score.bio_score +
            score.engagement_score +
            score.profile_score +
            score.recency_score
        )

        # Determinar prioridade
        score.priority = self._determine_priority(score.total_score)

        # Extrair dados para personalização
        score.detected_profession = self._detect_profession(bio, full_name)
        score.detected_interests = self._detect_interests(bio)
        score.detected_location = self._detect_location(bio)
        score.is_decision_maker = self._is_decision_maker(bio, full_name)

        # Gerar recomendações
        score.recommended_template = self._recommend_template(score)
        score.personalization_hooks = self._generate_hooks(profile, score)
        score.approach_notes = self._generate_approach_notes(score)

        return score

    def _calculate_bio_score(self, bio: str, full_name: str, profile: Dict) -> int:
        """Calcula score baseado na bio e dados demográficos (máx 30 pts)"""
        points = 0

        # Título profissional (Dr., Dra., etc.) - 5 pts
        if re.search(r'\b(dr\.|dra\.|dr |dra )\b', full_name + ' ' + bio):
            points += 5

        # É decisor/profissional de alto valor - 10 pts
        if self._is_decision_maker(bio, full_name):
            points += 10

        # Menciona negócio/empresa - 5 pts
        if re.search(r'(empresa|negócio|business|founder|ceo|startup|clínica|consultório)', bio):
            points += 5

        # Localização de alto valor - 5 pts
        if self._detect_location(bio):
            points += 5

        # Tem interesses relevantes - 5 pts
        if self._detect_interests(bio):
            points += 5

        return min(points, 30)  # Máximo 30

    def _calculate_engagement_score(self, profile: Dict) -> int:
        """Calcula score de engajamento (máx 30 pts)"""
        points = 0

        followers = profile.get('followers_count', 0)
        following = profile.get('following_count', 1)
        posts = profile.get('posts_count', 0)
        engagement_rate = profile.get('engagement_rate', 0)

        # Proporção seguidores/seguindo saudável (0.5 - 3.0) - 10 pts
        if following > 0:
            ratio = followers / following
            if 0.5 <= ratio <= 3.0:
                points += 10
            elif 0.3 <= ratio <= 5.0:
                points += 5

        # Quantidade de seguidores ideal (500 - 50k) - 10 pts
        if 500 <= followers <= 50000:
            points += 10
        elif 200 <= followers <= 100000:
            points += 5

        # Taxa de engajamento boa (>2%) - 10 pts
        if engagement_rate >= 5:
            points += 10
        elif engagement_rate >= 2:
            points += 7
        elif engagement_rate >= 1:
            points += 3

        return min(points, 30)  # Máximo 30

    def _calculate_profile_score(self, profile: Dict) -> int:
        """Calcula score do perfil (máx 25 pts)"""
        points = 0

        # Não é privado - 10 pts
        if not profile.get('is_private', True):
            points += 10

        # Tem bio preenchida - 5 pts
        bio = profile.get('bio', '')
        if bio and len(bio) > 10:
            points += 5

        # Perfil ativo (muitos posts) - 5 pts
        posts = profile.get('posts_count', 0)
        if posts >= 50:
            points += 5
        elif posts >= 20:
            points += 3

        # É conta business - 5 pts
        if profile.get('is_business', False):
            points += 5
        elif profile.get('category'):
            points += 3

        return min(points, 25)  # Máximo 25

    def _calculate_recency_score(self, profile: Dict) -> int:
        """Calcula score de recência/atividade (máx 15 pts)"""
        points = 0

        # Tem posts recentes - 10 pts
        recent_posts = profile.get('recent_posts', [])
        if recent_posts and len(recent_posts) >= 3:
            points += 10
        elif recent_posts:
            points += 5

        # Perfil parece ativo - 5 pts
        posting_frequency = profile.get('posting_frequency') or ''
        if 'muito ativo' in posting_frequency or 'ativo' in posting_frequency:
            points += 5

        return min(points, 15)  # Máximo 15

    def _determine_priority(self, score: int) -> LeadPriority:
        """Determina prioridade baseada no score"""
        if score >= 70:
            return LeadPriority.HOT
        elif score >= 50:
            return LeadPriority.WARM
        elif score >= 40:
            return LeadPriority.COLD
        else:
            return LeadPriority.NURTURING

    def _is_decision_maker(self, bio: str, full_name: str) -> bool:
        """Verifica se é um decisor/profissional de alto valor"""
        combined = (bio + ' ' + full_name).lower()
        for keyword in self.DECISION_MAKER_KEYWORDS:
            if keyword in combined:
                return True
        return False

    def _detect_profession(self, bio: str, full_name: str) -> Optional[str]:
        """Detecta profissão do perfil"""
        combined = (bio + ' ' + full_name).lower()

        professions = {
            'médico': ['médico', 'médica', 'dr.', 'dra.', 'medicina'],
            'dentista': ['dentista', 'odonto', 'cirurgião dentista'],
            'advogado': ['advogado', 'advogada', 'jurídico', 'direito'],
            'empresário': ['empresário', 'empresária', 'empreendedor', 'founder', 'ceo'],
            'coach': ['coach', 'mentora', 'mentor'],
            'consultor': ['consultor', 'consultora', 'consultoria'],
            'nutricionista': ['nutricionista', 'nutri', 'nutrição'],
            'psicólogo': ['psicólogo', 'psicóloga', 'psico', 'terapeuta'],
            'arquiteto': ['arquiteto', 'arquiteta', 'arquitetura'],
            'designer': ['designer', 'design', 'ux', 'ui'],
            'desenvolvedor': ['developer', 'desenvolvedor', 'programador', 'tech'],
            'marketing': ['marketing', 'growth', 'social media', 'tráfego']
        }

        for profession, keywords in professions.items():
            for keyword in keywords:
                if keyword in combined:
                    return profession

        return None

    def _detect_interests(self, bio: str) -> List[str]:
        """Detecta interesses do perfil"""
        if not bio:
            return []
        interests = []
        bio_lower = bio.lower()

        for interest, keywords in self.INTEREST_KEYWORDS.items():
            for keyword in keywords:
                if keyword in bio_lower:
                    interests.append(interest)
                    break

        return list(set(interests))

    def _detect_location(self, bio: str) -> Optional[str]:
        """Detecta localização do perfil"""
        if not bio:
            return None
        bio_lower = bio.lower()

        for location in self.HIGH_VALUE_LOCATIONS:
            if location in bio_lower:
                # Retornar formatado
                location_map = {
                    'sp': 'São Paulo', 'são paulo': 'São Paulo', 'sao paulo': 'São Paulo',
                    'rj': 'Rio de Janeiro', 'rio de janeiro': 'Rio de Janeiro',
                    'bh': 'Belo Horizonte', 'belo horizonte': 'Belo Horizonte',
                    'df': 'Brasília', 'brasília': 'Brasília',
                    'curitiba': 'Curitiba', 'porto alegre': 'Porto Alegre',
                    'florianópolis': 'Florianópolis', 'salvador': 'Salvador',
                    'recife': 'Recife', 'fortaleza': 'Fortaleza', 'campinas': 'Campinas'
                }
                return location_map.get(location, location.title())

        return None

    def _recommend_template(self, score: LeadScore) -> str:
        """Recomenda template de mensagem"""
        if score.total_score >= 70:
            return "ultra_personalized"
        elif score.total_score >= 50:
            return "personalized"
        else:
            return "standard"

    def _generate_hooks(self, profile: Dict, score: LeadScore) -> List[str]:
        """Gera ganchos de personalização para a mensagem"""
        hooks = []

        # Hook de profissão
        if score.detected_profession:
            hooks.append(f"profissão: {score.detected_profession}")

        # Hook de localização
        if score.detected_location:
            hooks.append(f"localização: {score.detected_location}")

        # Hook de interesses
        if score.detected_interests:
            hooks.append(f"interesses: {', '.join(score.detected_interests)}")

        # Hook de bio
        bio = profile.get('bio', '')
        if bio and len(bio) > 20:
            # Extrair primeira frase relevante
            first_part = bio.split('|')[0].strip() if '|' in bio else bio[:50]
            hooks.append(f"bio: {first_part}")

        # Hook de seguidores
        followers = profile.get('followers_count', 0)
        if followers >= 10000:
            hooks.append(f"influencer: {followers} seguidores")
        elif followers >= 1000:
            hooks.append(f"audiência: {followers} seguidores")

        return hooks

    def _generate_approach_notes(self, score: LeadScore) -> str:
        """Gera notas de abordagem"""
        notes = []

        if score.is_decision_maker:
            notes.append("DECISOR - Abordagem direta sobre ROI")

        if score.priority == LeadPriority.HOT:
            notes.append("HOT LEAD - Prioridade máxima")
        elif score.priority == LeadPriority.WARM:
            notes.append("WARM LEAD - Personalizar bem")

        if score.detected_profession:
            notes.append(f"Mencionar que trabalha com {score.detected_profession}s")

        if score.detected_location:
            notes.append(f"Possível referência local: {score.detected_location}")

        return " | ".join(notes) if notes else "Abordagem padrão"


# Função helper para uso direto
def score_lead(profile: Dict[str, Any]) -> LeadScore:
    """Função helper para calcular score de um lead"""
    scorer = LeadScorer()
    return scorer.calculate_score(profile)
