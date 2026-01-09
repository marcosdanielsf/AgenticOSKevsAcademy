"""
Skill: sync_lead
================
Sincroniza leads entre AgenticOS, AI Factory e GHL.

Uso:
    from skills.sync_lead import sync_lead

    result = await sync_lead(
        lead_id="uuid-123",
        source="agenticos",
        target="ghl"
    )
"""

import os
from typing import Dict, Literal
from datetime import datetime

from . import skill, auto_register, logger

# Importar cliente Supabase existente
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from supabase_integration import SupabaseClient
    supabase = SupabaseClient()
except Exception as e:
    logger.warning(f"SupabaseClient nao disponivel: {e}")
    supabase = None


@skill(name="sync_lead", description="Sincroniza lead entre sistemas")
# @auto_register (agora feito pelo @skill)
async def sync_lead(
    lead_id: str,
    source: Literal["agenticos", "ai_factory"],
    target: Literal["agenticos", "ai_factory", "ghl"]
) -> Dict:
    """
    Sincroniza dados de um lead entre sistemas.

    Args:
        lead_id: ID do lead no sistema de origem
        source: Sistema de origem ("agenticos" ou "ai_factory")
        target: Sistema de destino ("agenticos", "ai_factory" ou "ghl")

    Returns:
        Dict com:
        - synced: bool
        - source: str
        - target: str
        - synced_fields: List[str]
        - sync_log_id: str
    """

    if not supabase:
        return {"synced": False, "error": "SupabaseClient nao inicializado"}

    sync_data = {}
    lead = None

    # 1. Buscar dados do lead no source
    if source == "agenticos":
        # Buscar em growth_leads
        lead_result = supabase._request('GET', 'growth_leads', params={
            'id': f'eq.{lead_id}',
            'limit': 1
        })

        if not lead_result or isinstance(lead_result, dict) and "error" in lead_result:
            # Tentar em crm_leads
            lead_result = supabase._request('GET', 'crm_leads', params={
                'id': f'eq.{lead_id}',
                'limit': 1
            })

        if not lead_result or (isinstance(lead_result, list) and len(lead_result) == 0):
            return {"synced": False, "error": "Lead nao encontrado no AgenticOS"}

        lead = lead_result[0] if isinstance(lead_result, list) else lead_result

        # Buscar dados enriquecidos
        enriched_result = supabase._request('GET', 'enriched_lead_data', params={
            'lead_id': f'eq.{lead_id}'
        })
        enriched = enriched_result[0] if isinstance(enriched_result, list) and enriched_result else {}

    elif source == "ai_factory":
        # Buscar de agent_conversations
        lead_result = supabase._request('GET', 'agent_conversations', params={
            'id': f'eq.{lead_id}',
            'limit': 1
        })

        if not lead_result or (isinstance(lead_result, list) and len(lead_result) == 0):
            return {"synced": False, "error": "Lead nao encontrado no AI Factory"}

        lead = lead_result[0] if isinstance(lead_result, list) else lead_result
        enriched = {}

    # 2. Preparar dados para sync
    source_data = lead.get("source_data", {}) if isinstance(lead.get("source_data"), dict) else {}

    sync_data = {
        "agenticos_id": lead_id,
        "name": lead.get("name") or lead.get("contact_name"),
        "phone": lead.get("phone") or lead.get("contact_phone"),
        "email": lead.get("email") or lead.get("contact_email"),
        "instagram_username": lead.get("instagram_username") or lead.get("ig_handle"),
        "cargo": enriched.get("cargo") or source_data.get("cargo") or lead.get("title"),
        "empresa": enriched.get("empresa") or source_data.get("empresa") or lead.get("company"),
        "setor": enriched.get("setor") or source_data.get("setor"),
        "porte": enriched.get("porte") or source_data.get("porte"),
        "icp_score": lead.get("icp_score"),
        "lead_temperature": lead.get("lead_temperature"),
        "synced_at": datetime.utcnow().isoformat()
    }

    # Remover valores None
    sync_data = {k: v for k, v in sync_data.items() if v is not None}

    # 3. Sincronizar para target
    if target == "ai_factory":
        # Sincroniza para growth_leads
        result = supabase._request('POST', 'growth_leads', data={
            **sync_data,
            "source_channel": f"sync_from_{source}",
            "location_id": lead.get("location_id") or "DEFAULT_LOCATION",
            "updated_at": datetime.utcnow().isoformat()
        })

    elif target == "ghl":
        # Para GHL, precisamos do skill update_ghl_contact
        from .update_ghl_contact import update_ghl_contact_internal

        ghl_data = {
            "lead_cargo": sync_data.get("cargo"),
            "lead_empresa": sync_data.get("empresa"),
            "lead_setor": sync_data.get("setor"),
            "lead_porte": sync_data.get("porte"),
            "icp_score": str(sync_data.get("icp_score", 0)),
            "lead_temperature": sync_data.get("lead_temperature"),
            "agenticos_id": lead_id,
            "enriched_at": datetime.utcnow().isoformat()
        }

        # Buscar ghl_contact_id e location_id do lead
        ghl_contact_id = lead.get("ghl_contact_id")
        location_id = lead.get("location_id") or lead.get("ghl_location_id")

        if not ghl_contact_id or not location_id:
            return {
                "synced": False,
                "error": "Lead nao tem ghl_contact_id ou location_id",
                "lead_data": sync_data
            }

        result = await update_ghl_contact_internal(
            contact_id=ghl_contact_id,
            location_id=location_id,
            custom_fields=ghl_data
        )

    elif target == "agenticos":
        # Atualizar no AgenticOS (growth_leads)
        result = supabase._request('PATCH', 'growth_leads',
            params={'id': f'eq.{lead_id}'},
            data={
                **sync_data,
                "updated_at": datetime.utcnow().isoformat()
            }
        )

    # 4. Registrar sync log
    sync_log = {
        "source_system": source,
        "target_system": target,
        "entity_type": "lead",
        "entity_id": lead_id,
        "sync_status": "success" if not (isinstance(result, dict) and "error" in result) else "failed",
        "sync_data": sync_data,
        "error_message": result.get("error") if isinstance(result, dict) and "error" in result else None,
        "created_at": datetime.utcnow().isoformat()
    }

    log_result = supabase._request('POST', 'integration_sync_log', data=sync_log)

    return {
        "synced": sync_log["sync_status"] == "success",
        "source": source,
        "target": target,
        "synced_fields": list(sync_data.keys()),
        "sync_log_id": log_result[0]["id"] if isinstance(log_result, list) and log_result else None
    }


async def sync_batch_leads(
    lead_ids: list,
    source: Literal["agenticos", "ai_factory"],
    target: Literal["agenticos", "ai_factory", "ghl"]
) -> Dict:
    """
    Sincroniza multiplos leads em batch.

    Args:
        lead_ids: Lista de IDs dos leads
        source: Sistema de origem
        target: Sistema de destino

    Returns:
        Dict com estatisticas do batch
    """
    results = {
        "total": len(lead_ids),
        "success": 0,
        "failed": 0,
        "errors": []
    }

    for lead_id in lead_ids:
        result = await sync_lead(lead_id, source, target)
        if result.get("data", {}).get("synced"):
            results["success"] += 1
        else:
            results["failed"] += 1
            results["errors"].append({
                "lead_id": lead_id,
                "error": result.get("data", {}).get("error") or result.get("error")
            })

    return results
