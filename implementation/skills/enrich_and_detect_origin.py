"""
Skill Orquestrador: enrich_and_detect_origin
=============================================
Orquestra múltiplas skills para:
1. Buscar contato no GHL e extrair username do Instagram
2. Fazer scrape do perfil do Instagram (bio, seguidores, etc.)
3. Analisar a mensagem para detectar origem (outbound vs inbound)

Retorna tudo consolidado para o agente de qualificação.

Uso:
    from skills.enrich_and_detect_origin import enrich_and_detect_origin

    result = await enrich_and_detect_origin(
        contact_id="abc123",
        location_id="loc_xyz",
        api_key="pit-xxx",
        message="Oi!! Muito obrigada pelo elogio..."
    )

    # result.data = {
    #     "origin": "outbound",
    #     "profile_context": {
    #         "bio": "Médica | Dermatologia",
    #         "followers": 15000,
    #         "specialty": "dermatologista"
    #     },
    #     "agent_context": {
    #         "tom_agente": "direto, dar continuidade",
    #         "context_type": "prospecting_response"
    #     }
    # }
"""

import asyncio
from typing import Dict, Any, Optional

from . import skill, logger, SkillRegistry


@skill(
    name="enrich_and_detect_origin",
    description="Orquestra: GHL contact + Instagram scrape + Message analysis"
)
async def enrich_and_detect_origin(
    contact_id: str,
    api_key: str,
    message: str,
    location_id: Optional[str] = None,
    session_id: Optional[str] = None,  # Para scrape do Instagram
    skip_scrape: bool = False,  # Pular scrape se já tiver dados
    skip_analysis: bool = False  # Pular análise se já souber origem
) -> Dict[str, Any]:
    """
    Orquestra as skills para enriquecer lead e detectar origem.

    Fluxo:
    1. get_ghl_contact → extrai username do Instagram
    2. scrape_instagram_profile → bio, seguidores, etc. (paralelo com 3)
    3. analyze_message_intent → detecta outbound vs inbound (paralelo com 2)
    4. Combina resultados

    Args:
        contact_id: ID do contato no GHL
        api_key: GHL API key
        message: Mensagem do lead (para análise de intent)
        location_id: ID da location (opcional)
        session_id: Session ID do Instagram (opcional)
        skip_scrape: Se True, pula scrape do Instagram
        skip_analysis: Se True, pula análise de mensagem

    Returns:
        Dict consolidado com origin + profile_context + agent_context
    """
    # Validar inputs
    if not contact_id:
        return {
            "error": "contact_id é obrigatório",
            "origin": "unknown",
            "success": False
        }

    if not api_key:
        return {
            "error": "api_key é obrigatório",
            "origin": "unknown",
            "success": False
        }

    # Imports das skills (lazy para evitar circular)
    from .get_ghl_contact import get_ghl_contact
    from .scrape_instagram_profile import scrape_instagram_profile
    from .analyze_message_intent import analyze_message_intent

    result = {
        "contact_id": contact_id,
        "origin": "unknown",
        "origin_confidence": 0.0,
        "instagram_username": None,
        "profile_context": {},
        "origin_context": {},
        "agent_context": {},
        "skills_executed": [],
        "errors": []
    }

    # =====================================================
    # STEP 1: Buscar contato no GHL
    # =====================================================
    logger.info(f"[ORCHESTRATOR] Step 1: Buscando contato {contact_id} no GHL")

    ghl_result = await get_ghl_contact(
        contact_id=contact_id,
        api_key=api_key,
        location_id=location_id
    )

    result["skills_executed"].append("get_ghl_contact")

    # Extrair dados do resultado (skill wrapper)
    ghl_data = ghl_result.get("data", ghl_result) if ghl_result.get("success") else ghl_result

    if ghl_data.get("error"):
        result["errors"].append(f"GHL: {ghl_data['error']}")
        logger.warning(f"[ORCHESTRATOR] Erro no GHL: {ghl_data['error']}")
    else:
        result["instagram_username"] = ghl_data.get("instagram_username")
        result["profile_photo"] = ghl_data.get("profile_photo")
        result["ghl_tags"] = ghl_data.get("tags", [])
        result["ghl_source"] = ghl_data.get("source")

        # Verificar se já tem tags de prospecção
        tags = ghl_data.get("tags", [])
        tags_lower = [t.lower() for t in tags]

        if "prospectado" in tags_lower or "outbound-instagram" in tags_lower or "bdr-abordou" in tags_lower:
            result["has_outbound_tags"] = True
            logger.info("[ORCHESTRATOR] Lead já tem tags de prospecção (outbound)")
        else:
            result["has_outbound_tags"] = False

    instagram_username = result.get("instagram_username")

    # =====================================================
    # STEP 2 & 3: Executar em paralelo
    # =====================================================
    tasks = []

    # Task 2: Scrape do Instagram (se tiver username e não pular)
    if instagram_username and not skip_scrape:
        logger.info(f"[ORCHESTRATOR] Step 2: Scraping @{instagram_username}")
        tasks.append(("scrape", scrape_instagram_profile(
            username=instagram_username,
            session_id=session_id
        )))
    else:
        if not instagram_username:
            result["errors"].append("Sem username do Instagram para scrape")
        tasks.append(("scrape", asyncio.coroutine(lambda: {"skipped": True})()))

    # Task 3: Análise de mensagem (se tiver mensagem e não pular)
    if message and not skip_analysis:
        logger.info(f"[ORCHESTRATOR] Step 3: Analisando mensagem")
        tasks.append(("analysis", analyze_message_intent(
            message=message,
            use_ai=True
        )))
    else:
        if not message:
            result["errors"].append("Sem mensagem para análise de intent")
        tasks.append(("analysis", asyncio.coroutine(lambda: {"skipped": True})()))

    # Executar tasks em paralelo
    if tasks:
        task_results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)

        for (task_name, _), task_result in zip(tasks, task_results):
            if isinstance(task_result, Exception):
                result["errors"].append(f"{task_name}: {str(task_result)}")
                continue

            # Extrair data do wrapper
            data = task_result.get("data", task_result) if isinstance(task_result, dict) else task_result

            if task_name == "scrape" and not data.get("skipped"):
                result["skills_executed"].append("scrape_instagram_profile")

                if data.get("error"):
                    result["errors"].append(f"Scrape: {data['error']}")
                else:
                    result["profile_context"] = {
                        "bio": data.get("bio"),
                        "followers": data.get("followers_count"),
                        "following": data.get("following_count"),
                        "is_verified": data.get("is_verified"),
                        "is_business": data.get("is_business"),
                        "category": data.get("category"),
                        "specialty": data.get("specialty"),
                        "audience_size": data.get("audience_size"),
                        "profile_summary": data.get("profile_summary"),
                        "external_url": data.get("external_url")
                    }

            elif task_name == "analysis" and not data.get("skipped"):
                result["skills_executed"].append("analyze_message_intent")

                if data.get("error"):
                    result["errors"].append(f"Analysis: {data['error']}")
                else:
                    result["origin"] = data.get("origin", "unknown")
                    result["origin_confidence"] = data.get("confidence", 0.0)
                    result["origin_context"] = {
                        "origin": data.get("origin"),
                        "confidence": data.get("confidence"),
                        "reasoning": data.get("reasoning"),
                        "detected_context": data.get("detected_context"),
                        "is_response": data.get("is_response"),
                        "analysis_method": data.get("analysis_method")
                    }

    # =====================================================
    # STEP 4: Consolidar e gerar contexto para agente
    # =====================================================
    logger.info("[ORCHESTRATOR] Step 4: Consolidando resultados")

    # Se análise não foi conclusiva mas tem tags de outbound, usar tags
    if result["origin"] == "unknown" and result.get("has_outbound_tags"):
        result["origin"] = "outbound"
        result["origin_confidence"] = 0.8
        result["origin_context"]["fallback_reason"] = "Detectado por tags do GHL"

    # Gerar contexto para o agente de qualificação
    origin = result["origin"]
    specialty = result["profile_context"].get("specialty")

    if origin == "outbound":
        result["agent_context"] = {
            "should_activate": True,
            "context_type": "prospecting_response",
            "tom_agente": "direto, dar continuidade à conversa",
            "source_channel": "instagram_dm",
            "recommendation": "Lead respondendo prospecção - ativar qualificação imediata",
            "avoid": "Não se apresentar novamente, não fazer introduções genéricas",
            "personalization_hint": f"Usar especialidade ({specialty})" if specialty else "Personalizar com base na bio"
        }
    elif origin == "inbound":
        result["agent_context"] = {
            "should_activate": True,
            "context_type": "inbound_organic",
            "tom_agente": "receptivo, acolhedor, qualificar com perguntas",
            "source_channel": "instagram_dm",
            "recommendation": "Novo lead orgânico - iniciar qualificação com tom receptivo",
            "avoid": "Ser muito direto ou assumir contexto",
            "personalization_hint": f"Mencionar especialidade ({specialty})" if specialty else "Perguntar sobre área de atuação"
        }
    else:
        result["agent_context"] = {
            "should_activate": True,
            "context_type": "unknown_origin",
            "tom_agente": "neutro, buscar entender contexto",
            "source_channel": "instagram_dm",
            "recommendation": "Origem incerta - fazer perguntas para entender contexto",
            "avoid": "Assumir que sabe o contexto",
            "personalization_hint": "Usar bio se disponível" if result["profile_context"].get("bio") else "Fazer perguntas abertas"
        }

    # Adicionar label legível
    origin_labels = {
        "outbound": "BDR/Empresa iniciou (prospecção)",
        "inbound": "Lead iniciou (orgânico/novo seguidor)",
        "unknown": "Origem não identificada"
    }
    result["origin_label"] = origin_labels.get(origin, "Desconhecido")

    # Success se conseguiu determinar origem OU conseguiu dados do perfil
    result["success"] = (
        result["origin"] != "unknown" or
        bool(result["profile_context"].get("bio"))
    )

    logger.info(f"[ORCHESTRATOR] Concluído: origin={origin}, confidence={result['origin_confidence']:.2f}, skills={result['skills_executed']}")

    return result
