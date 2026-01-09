"""
Skill: get_lead_by_channel
==========================
Busca lead no AgenticOS pelo identificador do canal.
Usado pelo AI Factory para buscar contexto antes de responder.

Uso:
    from skills.get_lead_by_channel import get_lead_by_channel

    result = await get_lead_by_channel(
        channel="instagram",
        identifier="@joaosilva"
    )
"""

import os
import re
from typing import Dict, Optional
from datetime import datetime

from . import skill, auto_register, logger

# Importar cliente Supabase
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from supabase_integration import SupabaseClient
    supabase = SupabaseClient()
except Exception as e:
    logger.warning(f"SupabaseClient nao disponivel: {e}")
    supabase = None


def normalize_phone(phone: str) -> str:
    """Normaliza numero de telefone para formato padrao."""
    # Remove tudo que nao eh digito
    digits = re.sub(r'\D', '', phone)

    # Adiciona codigo do pais se nao tiver
    if len(digits) == 11:  # DDD + numero
        digits = f"55{digits}"
    elif len(digits) == 10:  # Fixo sem DDD? improvavel
        digits = f"5511{digits}"

    return f"+{digits}"


def normalize_instagram(handle: str) -> str:
    """Normaliza handle do Instagram - sem @ para growth_leads."""
    # Remove @ se tiver
    handle = handle.lstrip("@")
    # Remove URL se for
    if "instagram.com" in handle:
        handle = handle.split("/")[-1].split("?")[0]
    return handle.lower()  # growth_leads usa username sem @


def consolidate_enrichment(enriched_list: list) -> Dict:
    """Consolida dados de multiplas fontes de enriquecimento."""
    if not enriched_list:
        return {}

    consolidated = {}

    # Prioridade: linkedin > cnpj > instagram
    priority_order = ["linkedin", "cnpj", "instagram"]

    for source in priority_order:
        source_data = next((e for e in enriched_list if e.get("source") == source), None)
        if source_data:
            if "cargo" not in consolidated and source_data.get("cargo"):
                consolidated["cargo"] = source_data["cargo"]
            if "empresa" not in consolidated and source_data.get("empresa"):
                consolidated["empresa"] = source_data["empresa"]
            if "setor" not in consolidated and source_data.get("setor"):
                consolidated["setor"] = source_data["setor"]
            if "porte" not in consolidated and source_data.get("porte"):
                consolidated["porte"] = source_data["porte"]

            # Dados especificos do Instagram
            if source == "instagram":
                consolidated["ig_followers"] = source_data.get("ig_followers")
                consolidated["ig_engagement"] = source_data.get("ig_engagement_rate")
                consolidated["ig_bio"] = source_data.get("ig_bio")
                consolidated["ig_is_business"] = source_data.get("ig_is_business")

            # Dados especificos do LinkedIn
            if source == "linkedin":
                consolidated["li_headline"] = source_data.get("li_headline")
                consolidated["li_connections"] = source_data.get("li_connections")

            # Dados especificos do CNPJ
            if source == "cnpj":
                consolidated["cnpj"] = source_data.get("cnpj")
                consolidated["razao_social"] = source_data.get("razao_social")
                consolidated["cnae"] = source_data.get("cnae_principal")

    return consolidated


@skill(name="get_lead_by_channel", description="Busca lead pelo identificador do canal")
# @auto_register (agora feito pelo @skill)
async def get_lead_by_channel(
    channel: str,
    identifier: str
) -> Dict:
    """
    Busca lead no AgenticOS pelo identificador do canal.

    Args:
        channel: Canal de origem ("instagram", "whatsapp", "email", "facebook")
        identifier: Identificador no canal (@handle, +5511999999999, email@domain.com)

    Returns:
        Dict com:
        - found: bool
        - lead_id: str
        - lead_data: Dict com dados do lead e enriquecimento
        - was_prospected: bool (se foi prospectado pelo outbound)
        - prospected_at: str (data da prospeccao)
    """

    if not supabase:
        return {"found": False, "error": "SupabaseClient nao inicializado"}

    # Mapear canal para campo de busca
    field_map = {
        "instagram": "instagram_username",
        "whatsapp": "phone",
        "email": "email",
        "facebook": "facebook_id",
        "sms": "phone"
    }

    field = field_map.get(channel.lower())
    if not field:
        return {
            "found": False,
            "error": f"Canal desconhecido: {channel}",
            "supported_channels": list(field_map.keys())
        }

    # Normalizar identifier
    if channel.lower() == "instagram":
        identifier = normalize_instagram(identifier)
    elif channel.lower() in ["whatsapp", "sms"]:
        identifier = normalize_phone(identifier)
    elif channel.lower() == "email":
        identifier = identifier.lower().strip()

    # Buscar lead
    # Tentar primeiro em growth_leads
    lead_result = supabase._request('GET', 'growth_leads', params={
        field: f'eq.{identifier}',
        'limit': 1
    })

    if not lead_result or (isinstance(lead_result, list) and len(lead_result) == 0):
        # Tentar em crm_leads
        lead_result = supabase._request('GET', 'crm_leads', params={
            field: f'eq.{identifier}',
            'limit': 1
        })

    if not lead_result or (isinstance(lead_result, list) and len(lead_result) == 0):
        return {
            "found": False,
            "lead_data": None,
            "channel": channel,
            "identifier": identifier
        }

    lead = lead_result[0] if isinstance(lead_result, list) else lead_result

    # Buscar dados enriquecidos
    enriched_result = supabase._request('GET', 'enriched_lead_data', params={
        'lead_id': f'eq.{lead.get("id")}'
    })

    enriched_list = enriched_result if isinstance(enriched_result, list) else []
    enrichment = consolidate_enrichment(enriched_list)

    # Determinar se foi prospectado
    source_channel = lead.get("source_channel", "")
    funnel_stage = lead.get("funnel_stage", "")
    was_prospected = any([
        source_channel.startswith("outbound") if source_channel else False,
        source_channel.startswith("instagram_scrape") if source_channel else False,
        source_channel.startswith("linkedin_scrape") if source_channel else False,
        lead.get("outreach_sent_at") is not None,
        funnel_stage == "prospected"
    ])

    # Montar resposta
    lead_data = {
        "id": lead.get("id"),
        "name": lead.get("name"),
        "email": lead.get("email"),
        "phone": lead.get("phone"),
        "instagram_username": lead.get("instagram_username"),

        # Dados de qualificacao
        "icp_score": lead.get("icp_score"),
        "lead_temperature": lead.get("lead_temperature"),
        "funnel_stage": lead.get("funnel_stage"),

        # Dados enriquecidos consolidados
        "cargo": enrichment.get("cargo") or lead.get("title"),
        "empresa": enrichment.get("empresa") or lead.get("company"),
        "setor": enrichment.get("setor"),
        "porte": enrichment.get("porte"),
        "ig_followers": enrichment.get("ig_followers"),
        "ig_engagement": enrichment.get("ig_engagement"),

        # Metadata
        "source_channel": lead.get("source_channel"),
        "ghl_contact_id": lead.get("ghl_contact_id"),
        "location_id": lead.get("location_id"),
        "created_at": lead.get("created_at"),
        "updated_at": lead.get("updated_at")
    }

    # Remover valores None para resposta mais limpa
    lead_data = {k: v for k, v in lead_data.items() if v is not None}

    return {
        "found": True,
        "lead_id": lead.get("id"),
        "lead_data": lead_data,
        "enrichment": enrichment,
        "was_prospected": was_prospected,
        "prospected_at": lead.get("outreach_sent_at"),
        "last_outreach_message": lead.get("last_outreach_message")
    }


@skill(name="get_lead_context_for_ai", description="Busca contexto formatado para AI Agent")
# @auto_register (agora feito pelo @skill)
async def get_lead_context_for_ai(
    channel: str,
    identifier: str
) -> Dict:
    """
    Busca contexto do lead formatado para uso no AI Agent.
    Retorna string formatada para adicionar ao prompt.

    Args:
        channel: Canal de origem
        identifier: Identificador no canal

    Returns:
        Dict com:
        - found: bool
        - context_string: str (texto para adicionar ao prompt)
        - lead_data: Dict (dados brutos)
    """

    result = await get_lead_by_channel(channel, identifier)

    if not result.get("data", {}).get("found"):
        return {
            "found": False,
            "context_string": "",
            "lead_data": None
        }

    data = result.get("data", {})
    lead = data.get("lead_data", {})

    # Montar contexto formatado para o AI
    context_parts = ["CONTEXTO DO LEAD:"]

    if lead.get("name"):
        context_parts.append(f"- Nome: {lead['name']}")

    if lead.get("cargo"):
        context_parts.append(f"- Cargo: {lead['cargo']}")

    if lead.get("empresa"):
        context_parts.append(f"- Empresa: {lead['empresa']}")

    if lead.get("setor"):
        context_parts.append(f"- Setor: {lead['setor']}")

    if lead.get("porte"):
        context_parts.append(f"- Porte: {lead['porte']}")

    if lead.get("icp_score"):
        temp = lead.get("lead_temperature", "")
        context_parts.append(f"- ICP Score: {lead['icp_score']}/100 ({temp})")

    if lead.get("ig_followers"):
        context_parts.append(f"- Seguidores IG: {lead['ig_followers']}")

    if data.get("was_prospected"):
        context_parts.append(f"- Foi prospectado: Sim (em {data.get('prospected_at', 'data desconhecida')})")

    context_string = "\n".join(context_parts)

    return {
        "found": True,
        "context_string": context_string,
        "lead_data": lead,
        "was_prospected": data.get("was_prospected", False)
    }
