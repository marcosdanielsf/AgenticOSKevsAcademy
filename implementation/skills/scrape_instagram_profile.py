"""
Skill: scrape_instagram_profile
===============================
Faz scrape do perfil do Instagram usando a API interna (método Bruno Fraga).

Retorna dados ricos do perfil:
- Bio completa
- Número de seguidores
- Categoria/profissão
- Se é verificado
- Se é conta business
- Links externos

Uso:
    from skills.scrape_instagram_profile import scrape_instagram_profile

    result = await scrape_instagram_profile(
        username="dra.marilia.santos",
        session_id="opcional"  # usa env var se não passar
    )

    # result.data = {
    #     "username": "dra.marilia.santos",
    #     "bio": "Médica | Dermatologia",
    #     "followers_count": 15000,
    #     "specialty": "dermatologista",
    #     "is_verified": False,
    #     "is_business": True,
    #     "category": "Medical & Health"
    # }
"""

import os
import re
import asyncio
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

from . import skill, logger

# Palavras-chave para detectar especialidades da bio
SPECIALTY_KEYWORDS = {
    "dermatologista": ["dermatologia", "dermatologista", "dermato", "skin", "pele"],
    "nutricionista": ["nutrição", "nutricionista", "nutri", "dieta", "emagrecimento"],
    "psicóloga": ["psicologia", "psicóloga", "psicólogo", "terapia", "saúde mental"],
    "dentista": ["odontologia", "dentista", "odonto", "dentes", "sorriso"],
    "personal": ["personal", "trainer", "fitness", "musculação", "treino"],
    "coach": ["coach", "coaching", "mentoria", "desenvolvimento pessoal"],
    "advogado": ["advogado", "advocacia", "direito", "jurídico", "oab"],
    "médico": ["médico", "medicina", "dr.", "dra.", "clínica"],
    "fisioterapeuta": ["fisioterapia", "fisioterapeuta", "reabilitação"],
    "esteticista": ["estética", "esteticista", "beleza", "skincare"],
    "arquiteto": ["arquitetura", "arquiteto", "design de interiores"],
    "contador": ["contabilidade", "contador", "financeiro", "impostos"],
    "empresário": ["empreendedor", "empresário", "ceo", "founder", "negócios"],
}


def _detect_specialty(bio: str) -> Optional[str]:
    """Detecta especialidade baseado na bio."""
    if not bio:
        return None

    bio_lower = bio.lower()

    for specialty, keywords in SPECIALTY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in bio_lower:
                return specialty

    return None


def _run_sync_scraper(username: str, session_id: Optional[str] = None) -> Dict:
    """
    Executa o scraper de forma síncrona.
    Wrapper para usar com ThreadPoolExecutor.
    """
    try:
        # Import aqui para evitar circular imports
        import sys
        from pathlib import Path

        # Adicionar path do implementation
        impl_path = Path(__file__).parent.parent
        if str(impl_path) not in sys.path:
            sys.path.insert(0, str(impl_path))

        from instagram_api_scraper import InstagramAPIScraper

        scraper = InstagramAPIScraper(session_id=session_id)
        profile = scraper.get_profile(username)

        if not profile:
            return {"error": f"Perfil @{username} não encontrado"}

        return profile

    except ImportError as e:
        return {"error": f"InstagramAPIScraper não disponível: {str(e)}"}
    except Exception as e:
        return {"error": f"Erro no scraper: {str(e)}"}


@skill(
    name="scrape_instagram_profile",
    description="Faz scrape do perfil do Instagram e retorna bio, seguidores, etc."
)
async def scrape_instagram_profile(
    username: str,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Faz scrape do perfil do Instagram.

    Args:
        username: Username do Instagram (sem @)
        session_id: Session ID do Instagram (opcional, usa env var se não passar)

    Returns:
        Dict com dados do perfil
    """
    if not username:
        return {
            "error": "username é obrigatório",
            "username": None
        }

    # Limpar username (remover @ se tiver)
    username = username.lstrip("@").strip().lower()

    logger.info(f"Iniciando scrape do perfil @{username}")

    # Executar scraper em thread separada para não bloquear
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        profile_data = await loop.run_in_executor(
            executor,
            _run_sync_scraper,
            username,
            session_id
        )

    # Verificar erro
    if isinstance(profile_data, dict) and "error" in profile_data:
        logger.error(f"Erro ao fazer scrape de @{username}: {profile_data['error']}")
        return {
            "username": username,
            "error": profile_data["error"],
            "profile_found": False
        }

    # Extrair dados relevantes
    bio = profile_data.get("biography") or profile_data.get("bio") or ""
    followers = profile_data.get("follower_count") or profile_data.get("followers_count") or 0
    following = profile_data.get("following_count") or 0
    full_name = profile_data.get("full_name") or ""
    is_verified = profile_data.get("is_verified") or False
    is_business = profile_data.get("is_business_account") or profile_data.get("is_business") or False
    is_private = profile_data.get("is_private") or False
    category = profile_data.get("category_name") or profile_data.get("category") or ""
    external_url = profile_data.get("external_url") or ""
    profile_pic = profile_data.get("profile_pic_url_hd") or profile_data.get("profile_pic_url") or ""
    user_id = profile_data.get("pk") or profile_data.get("id") or ""

    # Detectar especialidade da bio
    specialty = _detect_specialty(bio)

    # Classificar tamanho da audiência
    if followers >= 100000:
        audience_size = "grande"
    elif followers >= 10000:
        audience_size = "média"
    elif followers >= 1000:
        audience_size = "pequena"
    else:
        audience_size = "micro"

    result = {
        "username": username,
        "profile_found": True,
        "user_id": str(user_id) if user_id else None,
        "full_name": full_name,
        "bio": bio,
        "followers_count": followers,
        "following_count": following,
        "is_verified": is_verified,
        "is_business": is_business,
        "is_private": is_private,
        "category": category,
        "external_url": external_url,
        "profile_pic_url": profile_pic,
        "specialty": specialty,
        "audience_size": audience_size,
        # Dados para IA de qualificação
        "profile_summary": f"{full_name} (@{username}) - {bio[:100]}..." if len(bio) > 100 else f"{full_name} (@{username}) - {bio}",
        "qualification_hints": {
            "has_business_account": is_business,
            "has_large_audience": followers >= 10000,
            "detected_specialty": specialty,
            "is_public": not is_private
        }
    }

    logger.info(f"Scrape completo: @{username} - {followers} seguidores, especialidade: {specialty}")

    return result
