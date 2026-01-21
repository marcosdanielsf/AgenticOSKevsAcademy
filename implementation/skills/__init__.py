"""
SKILLS MODULE - FASE 0 Integration
==================================
Skills reutilizaveis para integracao AgenticOS <-> AI Factory <-> GHL

Skills disponiveis:
- sync_lead: Sincroniza lead entre sistemas
- enrich_lead: Enriquece lead com dados externos
- update_ghl_contact: Atualiza custom fields no GHL
- get_agent_config: Busca config do agente AI Factory
- send_qa_data: Envia dados para QA-Analyst
- get_lead_by_channel: Busca lead por canal/identifier
"""

from typing import Dict, List, Any, Literal, Optional, Callable
from functools import wraps
import asyncio
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("skills")


# =====================================================
# SKILL REGISTRY - Definir ANTES do decorator skill()
# =====================================================

class SkillRegistry:
    """
    Registro central de skills disponíveis.
    Permite descoberta e execução dinâmica.
    """

    _skills: Dict[str, Callable] = {}

    @classmethod
    def register(cls, func: Callable) -> None:
        """Registra um skill no registry."""
        if hasattr(func, '_skill_name'):
            cls._skills[func._skill_name] = func
            logger.info(f"[REGISTRY] Skill registrado: {func._skill_name}")

    @classmethod
    def get(cls, name: str) -> Optional[Callable]:
        """Retorna um skill pelo nome."""
        return cls._skills.get(name)

    @classmethod
    def list_all(cls) -> List[Dict[str, str]]:
        """Lista todos os skills registrados."""
        return [
            {
                "name": func._skill_name,
                "description": func._skill_description
            }
            for func in cls._skills.values()
        ]

    @classmethod
    async def execute(cls, name: str, **kwargs) -> Dict[str, Any]:
        """Executa um skill pelo nome."""
        skill_func = cls.get(name)
        if not skill_func:
            return {
                "success": False,
                "error": f"Skill '{name}' nao encontrado",
                "available_skills": [s["name"] for s in cls.list_all()]
            }
        return await skill_func(**kwargs)


# =====================================================
# SKILL DECORATOR
# =====================================================

def skill(name: str, description: str, auto_register: bool = True):
    """
    Decorator para registrar e executar skills.

    Adiciona:
    - Logging automatico de inicio/fim
    - Tratamento de erros padronizado
    - Metadata do skill
    - Auto-registro no SkillRegistry (por padrao)

    Uso:
        @skill(name="sync_lead", description="Sincroniza lead entre sistemas")
        async def sync_lead(lead_id: str, source: str, target: str) -> Dict:
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Dict[str, Any]:
            start_time = datetime.utcnow()
            logger.info(f"[SKILL] Iniciando: {name}")

            try:
                result = await func(*args, **kwargs)

                elapsed = (datetime.utcnow() - start_time).total_seconds()
                logger.info(f"[SKILL] Concluido: {name} ({elapsed:.2f}s)")

                return {
                    "success": True,
                    "skill": name,
                    "data": result,
                    "elapsed_seconds": elapsed
                }

            except Exception as e:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                logger.error(f"[SKILL] Erro em {name}: {str(e)} ({elapsed:.2f}s)")

                return {
                    "success": False,
                    "skill": name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "elapsed_seconds": elapsed
                }

        # Adicionar metadata ao wrapper
        wrapper._skill_name = name
        wrapper._skill_description = description
        wrapper._is_skill = True

        # Auto-registrar no SkillRegistry
        if auto_register:
            SkillRegistry.register(wrapper)

        return wrapper
    return decorator


# Auto-registrar decorator legado (para compatibilidade)
def auto_register(func: Callable) -> Callable:
    """Decorator que registra skill automaticamente (legado)."""
    SkillRegistry.register(func)
    return func


# =====================================================
# IMPORTAR SKILLS PARA AUTO-REGISTRO
# =====================================================

try:
    from . import sync_lead
    from . import update_ghl_contact
    from . import get_lead_by_channel
    from . import detect_conversation_origin
    # Novas skills v2 (2026-01-21)
    from . import get_ghl_contact
    from . import scrape_instagram_profile
    from . import analyze_message_intent
    from . import enrich_and_detect_origin  # Orquestrador
    logger.info(f"[REGISTRY] {len(SkillRegistry._skills)} skills carregados")
except ImportError as e:
    logger.warning(f"[REGISTRY] Erro ao carregar skills: {e}")


# =====================================================
# EXPORTAR
# =====================================================

__all__ = [
    "skill",
    "auto_register",
    "SkillRegistry",
    "logger",
    "sync_lead",
    "update_ghl_contact",
    "get_lead_by_channel"
]
