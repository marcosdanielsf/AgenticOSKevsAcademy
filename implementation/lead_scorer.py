"""
Lead Scorer - Sistema de Pontuacao Semantica
=============================================
Calcula score de 0-100 para leads baseado em dados do perfil.
Determina prioridade e tipo de abordagem.

Suporta configuracao por tenant via tabela tenant_icp_config no Supabase.
"""

import os
import re
import httpx
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum
from functools import lru_cache


class LeadPriority(Enum):
    """Prioridade do lead baseada no score"""
    HOT = "hot"           # Score >= hot_threshold: DM imediato
    WARM = "warm"         # Score >= warm_threshold: DM em 24h
    COLD = "cold"         # Score >= cold_threshold: DM em 48h
    NURTURING = "nurturing"  # Score < cold_threshold: Nao enviar DM


@dataclass
class LeadScore:
    """Resultado da pontuacao de um lead"""
    username: str
    total_score: int
    priority: LeadPriority

    # Breakdown do score
    bio_score: int = 0
    engagement_score: int = 0
    profile_score: int = 0
    recency_score: int = 0

    # Dados extraidos
    detected_profession: Optional[str] = None
    detected_interests: List[str] = None
    detected_location: Optional[str] = None
    is_decision_maker: bool = False

    # Recomendacoes
    recommended_template: str = "standard"
    personalization_hooks: List[str] = None
    approach_notes: Optional[str] = None

    def __post_init__(self):
        if self.detected_interests is None:
            self.detected_interests = []
        if self.personalization_hooks is None:
            self.personalization_hooks = []


@dataclass
class TenantICPConfig:
    """Configuracao de ICP por tenant"""
    tenant_id: str
    tenant_name: str = "Default"

    # Keywords
    decision_maker_keywords: List[str] = None
    interest_keywords: Dict[str, List[str]] = None
    high_value_locations: List[str] = None

    # Faixas de seguidores
    min_followers: int = 200
    max_followers: int = 100000
    ideal_min_followers: int = 500
    ideal_max_followers: int = 50000

    # Engajamento
    min_engagement_rate: float = 1.0
    ideal_engagement_rate: float = 2.0

    # Thresholds
    hot_threshold: int = 70
    warm_threshold: int = 50
    cold_threshold: int = 40

    # Pesos
    weight_bio: int = 30
    weight_engagement: int = 30
    weight_profile: int = 25
    weight_recency: int = 15

    # Configuracoes
    skip_private_profiles: bool = True
    require_bio: bool = False
    require_business_account: bool = False

    def __post_init__(self):
        if self.decision_maker_keywords is None:
            self.decision_maker_keywords = DEFAULT_DECISION_MAKER_KEYWORDS
        if self.interest_keywords is None:
            self.interest_keywords = DEFAULT_INTEREST_KEYWORDS
        if self.high_value_locations is None:
            self.high_value_locations = DEFAULT_HIGH_VALUE_LOCATIONS


# Valores default (usados quando nao ha config no Supabase)
DEFAULT_DECISION_MAKER_KEYWORDS = [
    'ceo', 'fundador', 'founder', 'dono', 'proprietario', 'diretor',
    'empresario', 'empreendedor', 'socio', 'gestor', 'gerente',
    'executivo', 'c-level', 'head', 'lider', 'coordenador',
    'medico', 'medica', 'dr.', 'dra.', 'advogado', 'advogada',
    'dentista', 'arquiteto', 'engenheiro', 'psicologo', 'nutricionista',
    'fisioterapeuta', 'coach', 'consultor', 'consultora',
    'entrepreneur', 'business owner', 'manager', 'director'
]

DEFAULT_INTEREST_KEYWORDS = {
    'marketing': ['marketing', 'growth', 'vendas', 'sales', 'leads', 'trafego'],
    'tecnologia': ['tech', 'startup', 'saas', 'software', 'automacao', 'ia', 'ai'],
    'negocios': ['business', 'negocio', 'empresa', 'empreend', 'lucro', 'faturamento'],
    'estetica': ['estetica', 'beleza', 'clinica', 'procedimento', 'harmonizacao'],
    'saude': ['saude', 'bem-estar', 'fitness', 'nutricao', 'medicina'],
    'financas': ['investimento', 'financas', 'renda', 'dinheiro', 'patrimonio'],
    'educacao': ['curso', 'mentoria', 'treinamento', 'ensino', 'educacao']
}

DEFAULT_HIGH_VALUE_LOCATIONS = [
    'sp', 'sao paulo', 'sampa',
    'rj', 'rio de janeiro', 'rio',
    'bh', 'belo horizonte',
    'brasilia', 'df',
    'curitiba', 'porto alegre', 'florianopolis', 'salvador',
    'recife', 'fortaleza', 'campinas'
]


# Cache de configs por tenant (evita queries repetidas)
_config_cache: Dict[str, TenantICPConfig] = {}


def _fetch_tenant_config(tenant_id: str) -> Optional[Dict]:
    """Busca configuracao do tenant no Supabase."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        return None

    try:
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json"
        }

        # Buscar config do tenant especifico
        url = f"{supabase_url}/rest/v1/tenant_icp_config?tenant_id=eq.{tenant_id}&select=*"

        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0]

            # Se nao encontrou, buscar DEFAULT
            if tenant_id != "DEFAULT":
                url_default = f"{supabase_url}/rest/v1/tenant_icp_config?tenant_id=eq.DEFAULT&select=*"
                response = client.get(url_default, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        return data[0]

    except Exception as e:
        print(f"[LeadScorer] Erro ao buscar config do tenant {tenant_id}: {e}")

    return None


def get_tenant_config(tenant_id: str = "DEFAULT") -> TenantICPConfig:
    """
    Retorna configuracao de ICP para um tenant.
    Usa cache para evitar queries repetidas.
    """
    # Verificar cache
    if tenant_id in _config_cache:
        return _config_cache[tenant_id]

    # Buscar do Supabase
    config_data = _fetch_tenant_config(tenant_id)

    if config_data:
        config = TenantICPConfig(
            tenant_id=config_data.get('tenant_id', tenant_id),
            tenant_name=config_data.get('tenant_name', 'Unknown'),
            decision_maker_keywords=config_data.get('decision_maker_keywords') or DEFAULT_DECISION_MAKER_KEYWORDS,
            interest_keywords=config_data.get('interest_keywords') or DEFAULT_INTEREST_KEYWORDS,
            high_value_locations=config_data.get('high_value_locations') or DEFAULT_HIGH_VALUE_LOCATIONS,
            min_followers=config_data.get('min_followers', 200),
            max_followers=config_data.get('max_followers', 100000),
            ideal_min_followers=config_data.get('ideal_min_followers', 500),
            ideal_max_followers=config_data.get('ideal_max_followers', 50000),
            min_engagement_rate=float(config_data.get('min_engagement_rate', 1.0)),
            ideal_engagement_rate=float(config_data.get('ideal_engagement_rate', 2.0)),
            hot_threshold=config_data.get('hot_threshold', 70),
            warm_threshold=config_data.get('warm_threshold', 50),
            cold_threshold=config_data.get('cold_threshold', 40),
            weight_bio=config_data.get('weight_bio', 30),
            weight_engagement=config_data.get('weight_engagement', 30),
            weight_profile=config_data.get('weight_profile', 25),
            weight_recency=config_data.get('weight_recency', 15),
            skip_private_profiles=config_data.get('skip_private_profiles', True),
            require_bio=config_data.get('require_bio', False),
            require_business_account=config_data.get('require_business_account', False)
        )
    else:
        # Usar defaults hardcoded
        config = TenantICPConfig(tenant_id=tenant_id)

    # Salvar no cache
    _config_cache[tenant_id] = config

    return config


def clear_config_cache(tenant_id: str = None):
    """Limpa cache de configuracao (util apos atualizar config)."""
    global _config_cache
    if tenant_id:
        _config_cache.pop(tenant_id, None)
    else:
        _config_cache = {}


class LeadScorer:
    """
    Calcula score semantico de leads baseado em dados do perfil.
    Score maximo: 100 pontos.

    Suporta configuracao por tenant via Supabase.
    """

    def __init__(self, tenant_id: str = "DEFAULT"):
        """
        Inicializa scorer com configuracao do tenant.

        Args:
            tenant_id: ID do tenant para carregar config customizada
        """
        self.tenant_id = tenant_id
        self.config = get_tenant_config(tenant_id)

        # Atalhos para config
        self.DECISION_MAKER_KEYWORDS = self.config.decision_maker_keywords
        self.INTEREST_KEYWORDS = self.config.interest_keywords
        self.HIGH_VALUE_LOCATIONS = self.config.high_value_locations

    def calculate_score(self, profile: Dict[str, Any]) -> LeadScore:
        """
        Calcula score completo de um lead.

        Args:
            profile: Dados do perfil (InstagramProfile.to_dict())

        Returns:
            LeadScore com pontuacao e recomendacoes
        """
        username = profile.get('username', '')
        bio = (profile.get('bio') or '').lower()
        full_name = (profile.get('full_name') or '').lower()

        score = LeadScore(username=username, total_score=0, priority=LeadPriority.NURTURING)

        # 1. SCORE DA BIO E DEMOGRAFIA
        score.bio_score = self._calculate_bio_score(bio, full_name, profile)

        # 2. SCORE DE ENGAJAMENTO
        score.engagement_score = self._calculate_engagement_score(profile)

        # 3. SCORE DO PERFIL
        score.profile_score = self._calculate_profile_score(profile)

        # 4. SCORE DE RECENCIA
        score.recency_score = self._calculate_recency_score(profile)

        # Calcular total (usar pesos da config)
        score.total_score = (
            score.bio_score +
            score.engagement_score +
            score.profile_score +
            score.recency_score
        )

        # Determinar prioridade (usar thresholds da config)
        score.priority = self._determine_priority(score.total_score)

        # Extrair dados para personalizacao
        score.detected_profession = self._detect_profession(bio, full_name)
        score.detected_interests = self._detect_interests(bio)
        score.detected_location = self._detect_location(bio)
        score.is_decision_maker = self._is_decision_maker(bio, full_name)

        # Gerar recomendacoes
        score.recommended_template = self._recommend_template(score)
        score.personalization_hooks = self._generate_hooks(profile, score)
        score.approach_notes = self._generate_approach_notes(score)

        return score

    def _calculate_bio_score(self, bio: str, full_name: str, profile: Dict) -> int:
        """Calcula score baseado na bio e dados demograficos"""
        max_points = self.config.weight_bio
        points = 0

        # Titulo profissional (Dr., Dra., etc.) - 5 pts
        if re.search(r'\b(dr\.|dra\.|dr |dra )\b', full_name + ' ' + bio):
            points += 5

        # E decisor/profissional de alto valor - 10 pts
        if self._is_decision_maker(bio, full_name):
            points += 10

        # Menciona negocio/empresa - 5 pts
        if re.search(r'(empresa|negocio|business|founder|ceo|startup|clinica|consultorio)', bio):
            points += 5

        # Localizacao de alto valor - 5 pts
        if self._detect_location(bio):
            points += 5

        # Tem interesses relevantes - 5 pts
        if self._detect_interests(bio):
            points += 5

        return min(points, max_points)

    def _calculate_engagement_score(self, profile: Dict) -> int:
        """Calcula score de engajamento"""
        max_points = self.config.weight_engagement
        points = 0

        followers = profile.get('followers_count', 0)
        following = profile.get('following_count', 1)
        engagement_rate = profile.get('engagement_rate', 0)

        # Proporcao seguidores/seguindo saudavel (0.5 - 3.0) - 10 pts
        if following > 0:
            ratio = followers / following
            if 0.5 <= ratio <= 3.0:
                points += 10
            elif 0.3 <= ratio <= 5.0:
                points += 5

        # Quantidade de seguidores ideal - 10 pts
        if self.config.ideal_min_followers <= followers <= self.config.ideal_max_followers:
            points += 10
        elif self.config.min_followers <= followers <= self.config.max_followers:
            points += 5

        # Taxa de engajamento - 10 pts
        if engagement_rate >= self.config.ideal_engagement_rate * 2.5:  # 5%+ se ideal=2%
            points += 10
        elif engagement_rate >= self.config.ideal_engagement_rate:
            points += 7
        elif engagement_rate >= self.config.min_engagement_rate:
            points += 3

        return min(points, max_points)

    def _calculate_profile_score(self, profile: Dict) -> int:
        """Calcula score do perfil"""
        max_points = self.config.weight_profile
        points = 0

        # Nao e privado - 10 pts
        if not profile.get('is_private', True):
            points += 10
        elif self.config.skip_private_profiles:
            return 0  # Zero pontos se config exige perfil publico

        # Tem bio preenchida - 5 pts
        bio = profile.get('bio', '')
        if bio and len(bio) > 10:
            points += 5
        elif self.config.require_bio:
            return 0  # Zero pontos se config exige bio

        # Perfil ativo (muitos posts) - 5 pts
        posts = profile.get('posts_count', 0)
        if posts >= 50:
            points += 5
        elif posts >= 20:
            points += 3

        # E conta business - 5 pts
        if profile.get('is_business', False):
            points += 5
        elif profile.get('category'):
            points += 3
        elif self.config.require_business_account:
            return 0  # Zero pontos se config exige business

        return min(points, max_points)

    def _calculate_recency_score(self, profile: Dict) -> int:
        """Calcula score de recencia/atividade"""
        max_points = self.config.weight_recency
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

        return min(points, max_points)

    def _determine_priority(self, score: int) -> LeadPriority:
        """Determina prioridade baseada no score e thresholds do tenant"""
        if score >= self.config.hot_threshold:
            return LeadPriority.HOT
        elif score >= self.config.warm_threshold:
            return LeadPriority.WARM
        elif score >= self.config.cold_threshold:
            return LeadPriority.COLD
        else:
            return LeadPriority.NURTURING

    def _is_decision_maker(self, bio: str, full_name: str) -> bool:
        """Verifica se e um decisor/profissional de alto valor"""
        combined = (bio + ' ' + full_name).lower()
        for keyword in self.DECISION_MAKER_KEYWORDS:
            if keyword in combined:
                return True
        return False

    def _detect_profession(self, bio: str, full_name: str) -> Optional[str]:
        """Detecta profissao do perfil"""
        combined = (bio + ' ' + full_name).lower()

        professions = {
            'medico': ['medico', 'medica', 'dr.', 'dra.', 'medicina'],
            'dentista': ['dentista', 'odonto', 'cirurgiao dentista'],
            'advogado': ['advogado', 'advogada', 'juridico', 'direito'],
            'empresario': ['empresario', 'empresaria', 'empreendedor', 'founder', 'ceo'],
            'coach': ['coach', 'mentora', 'mentor'],
            'consultor': ['consultor', 'consultora', 'consultoria'],
            'nutricionista': ['nutricionista', 'nutri', 'nutricao'],
            'psicologo': ['psicologo', 'psicologa', 'psico', 'terapeuta'],
            'arquiteto': ['arquiteto', 'arquiteta', 'arquitetura'],
            'designer': ['designer', 'design', 'ux', 'ui'],
            'desenvolvedor': ['developer', 'desenvolvedor', 'programador', 'tech'],
            'marketing': ['marketing', 'growth', 'social media', 'trafego']
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
        """Detecta localizacao do perfil"""
        if not bio:
            return None
        bio_lower = bio.lower()

        for location in self.HIGH_VALUE_LOCATIONS:
            if location in bio_lower:
                # Retornar formatado
                location_map = {
                    'sp': 'Sao Paulo', 'sao paulo': 'Sao Paulo',
                    'rj': 'Rio de Janeiro', 'rio de janeiro': 'Rio de Janeiro',
                    'bh': 'Belo Horizonte', 'belo horizonte': 'Belo Horizonte',
                    'df': 'Brasilia', 'brasilia': 'Brasilia',
                    'curitiba': 'Curitiba', 'porto alegre': 'Porto Alegre',
                    'florianopolis': 'Florianopolis', 'salvador': 'Salvador',
                    'recife': 'Recife', 'fortaleza': 'Fortaleza', 'campinas': 'Campinas'
                }
                return location_map.get(location, location.title())

        return None

    def _recommend_template(self, score: LeadScore) -> str:
        """Recomenda template de mensagem"""
        if score.total_score >= self.config.hot_threshold:
            return "ultra_personalized"
        elif score.total_score >= self.config.warm_threshold:
            return "personalized"
        else:
            return "standard"

    def _generate_hooks(self, profile: Dict, score: LeadScore) -> List[str]:
        """Gera ganchos de personalizacao para a mensagem"""
        hooks = []

        if score.detected_profession:
            hooks.append(f"profissao: {score.detected_profession}")

        if score.detected_location:
            hooks.append(f"localizacao: {score.detected_location}")

        if score.detected_interests:
            hooks.append(f"interesses: {', '.join(score.detected_interests)}")

        bio = profile.get('bio', '')
        if bio and len(bio) > 20:
            first_part = bio.split('|')[0].strip() if '|' in bio else bio[:50]
            hooks.append(f"bio: {first_part}")

        followers = profile.get('followers_count', 0)
        if followers >= 10000:
            hooks.append(f"influencer: {followers} seguidores")
        elif followers >= 1000:
            hooks.append(f"audiencia: {followers} seguidores")

        return hooks

    def _generate_approach_notes(self, score: LeadScore) -> str:
        """Gera notas de abordagem"""
        notes = []

        if score.is_decision_maker:
            notes.append("DECISOR - Abordagem direta sobre ROI")

        if score.priority == LeadPriority.HOT:
            notes.append("HOT LEAD - Prioridade maxima")
        elif score.priority == LeadPriority.WARM:
            notes.append("WARM LEAD - Personalizar bem")

        if score.detected_profession:
            notes.append(f"Mencionar que trabalha com {score.detected_profession}s")

        if score.detected_location:
            notes.append(f"Possivel referencia local: {score.detected_location}")

        return " | ".join(notes) if notes else "Abordagem padrao"


# Funcao helper para uso direto (backward compatible)
def score_lead(profile: Dict[str, Any], tenant_id: str = "DEFAULT") -> LeadScore:
    """Funcao helper para calcular score de um lead"""
    scorer = LeadScorer(tenant_id=tenant_id)
    return scorer.calculate_score(profile)
