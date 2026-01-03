"""
Skill: update_ghl_contact
=========================
Atualiza custom fields de um contato no GoHighLevel.

Uso:
    from skills.update_ghl_contact import update_ghl_contact

    result = await update_ghl_contact(
        contact_id="abc123",
        location_id="loc_xyz",
        custom_fields={"lead_cargo": "CEO", "icp_score": "85"}
    )
"""

import os
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime

from . import skill, auto_register, logger

# GHL API Config
GHL_API_URL = "https://services.leadconnectorhq.com"
GHL_API_KEY = os.getenv("GHL_API_KEY") or os.getenv("GHL_ACCESS_TOKEN")


async def _get_ghl_headers(location_id: str = None) -> Dict[str, str]:
    """Retorna headers para API do GHL."""
    return {
        "Authorization": f"Bearer {GHL_API_KEY}",
        "Content-Type": "application/json",
        "Version": "2021-07-28"
    }


async def _get_custom_field_map(location_id: str) -> Dict[str, str]:
    """
    Busca mapeamento de field_key para field_id no GHL.

    Returns:
        Dict com field_key -> field_id
    """
    headers = await _get_ghl_headers(location_id)

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{GHL_API_URL}/locations/{location_id}/customFields",
                headers=headers
            )

            if response.status_code != 200:
                logger.error(f"Erro ao buscar custom fields: {response.status_code} - {response.text}")
                return {}

            data = response.json()
            custom_fields = data.get("customFields", [])

            return {f.get("fieldKey"): f.get("id") for f in custom_fields if f.get("fieldKey")}

        except Exception as e:
            logger.error(f"Excecao ao buscar custom fields: {e}")
            return {}


async def update_ghl_contact_internal(
    contact_id: str,
    location_id: str,
    custom_fields: Dict[str, Any]
) -> Dict:
    """
    Funcao interna para atualizar contato (sem decorator de skill).
    Usada por outros skills como sync_lead.
    """

    if not GHL_API_KEY:
        return {"updated": False, "error": "GHL_API_KEY nao configurada"}

    headers = await _get_ghl_headers(location_id)

    # 1. Buscar mapeamento de custom fields
    field_map = await _get_custom_field_map(location_id)

    if not field_map:
        logger.warning("Nenhum custom field encontrado, tentando criar...")
        # Poderia chamar ensure_custom_fields_exist aqui

    # 2. Preparar payload
    custom_fields_payload = []
    fields_not_found = []

    for field_key, value in custom_fields.items():
        if field_key in field_map:
            custom_fields_payload.append({
                "id": field_map[field_key],
                "field_value": str(value) if value is not None else ""
            })
        else:
            fields_not_found.append(field_key)
            logger.warning(f"Custom field '{field_key}' nao existe no GHL location {location_id}")

    if not custom_fields_payload:
        return {
            "updated": False,
            "error": "Nenhum custom field valido para atualizar",
            "fields_not_found": fields_not_found
        }

    # 3. Atualizar contato
    update_payload = {
        "customFields": custom_fields_payload
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.put(
                f"{GHL_API_URL}/contacts/{contact_id}",
                headers=headers,
                json=update_payload
            )

            if response.status_code not in [200, 201]:
                return {
                    "updated": False,
                    "error": f"Erro ao atualizar contato: {response.status_code} - {response.text}",
                    "fields_not_found": fields_not_found
                }

            return {
                "updated": True,
                "contact_id": contact_id,
                "updated_fields": list(custom_fields.keys()),
                "fields_not_found": fields_not_found
            }

        except Exception as e:
            return {
                "updated": False,
                "error": f"Excecao ao atualizar contato: {str(e)}"
            }


@skill(name="update_ghl_contact", description="Atualiza custom fields de contato no GHL")
# @auto_register (agora feito pelo @skill)
async def update_ghl_contact(
    contact_id: str,
    location_id: str,
    custom_fields: Dict[str, Any]
) -> Dict:
    """
    Atualiza custom fields de um contato no GoHighLevel.

    Args:
        contact_id: ID do contato no GHL
        location_id: ID da location no GHL
        custom_fields: Dict com field_key -> value

    Custom Fields Esperados:
        - lead_cargo: Cargo do lead
        - lead_empresa: Empresa do lead
        - lead_setor: Setor/Industria
        - lead_porte: Porte da empresa
        - lead_followers: Seguidores IG
        - lead_engagement: Taxa de engajamento
        - icp_score: Score ICP (0-100)
        - icp_tier: Tier (HOT/WARM/COLD)
        - lead_source: Fonte do lead
        - agenticos_id: ID no AgenticOS
        - enriched_at: Data de enriquecimento

    Returns:
        Dict com:
        - updated: bool
        - contact_id: str
        - updated_fields: List[str]
        - fields_not_found: List[str]
    """
    return await update_ghl_contact_internal(contact_id, location_id, custom_fields)


@skill(name="ensure_ghl_custom_fields", description="Garante que custom fields existem no GHL")
# @auto_register (agora feito pelo @skill)
async def ensure_custom_fields_exist(location_id: str) -> Dict:
    """
    Verifica e cria custom fields necessarios no GHL.

    Args:
        location_id: ID da location no GHL

    Returns:
        Dict com:
        - existing: List[str] - campos que ja existiam
        - created: List[str] - campos criados
        - failed: List[str] - campos que falharam ao criar
    """

    required_fields = [
        {"name": "Lead Cargo", "fieldKey": "lead_cargo", "dataType": "TEXT"},
        {"name": "Lead Empresa", "fieldKey": "lead_empresa", "dataType": "TEXT"},
        {"name": "Lead Setor", "fieldKey": "lead_setor", "dataType": "TEXT"},
        {"name": "Lead Porte", "fieldKey": "lead_porte", "dataType": "TEXT"},
        {"name": "Lead Followers", "fieldKey": "lead_followers", "dataType": "NUMERICAL"},
        {"name": "Lead Engagement", "fieldKey": "lead_engagement", "dataType": "NUMERICAL"},
        {"name": "ICP Score", "fieldKey": "icp_score", "dataType": "NUMERICAL"},
        {"name": "ICP Tier", "fieldKey": "icp_tier", "dataType": "TEXT"},
        {"name": "Lead Source", "fieldKey": "lead_source", "dataType": "TEXT"},
        {"name": "AgenticOS ID", "fieldKey": "agenticos_id", "dataType": "TEXT"},
        {"name": "Enriched At", "fieldKey": "enriched_at", "dataType": "TEXT"},
    ]

    if not GHL_API_KEY:
        return {"error": "GHL_API_KEY nao configurada"}

    headers = await _get_ghl_headers(location_id)

    # Buscar campos existentes
    existing_map = await _get_custom_field_map(location_id)
    existing_keys = set(existing_map.keys())

    result = {
        "existing": [],
        "created": [],
        "failed": []
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        for field in required_fields:
            if field["fieldKey"] in existing_keys:
                result["existing"].append(field["fieldKey"])
                continue

            # Criar campo
            try:
                response = await client.post(
                    f"{GHL_API_URL}/locations/{location_id}/customFields",
                    headers=headers,
                    json={
                        "name": field["name"],
                        "fieldKey": field["fieldKey"],
                        "dataType": field["dataType"],
                        "model": "contact"
                    }
                )

                if response.status_code in [200, 201]:
                    result["created"].append(field["fieldKey"])
                    logger.info(f"Custom field criado: {field['fieldKey']}")
                else:
                    result["failed"].append(field["fieldKey"])
                    logger.error(f"Falha ao criar {field['fieldKey']}: {response.text}")

            except Exception as e:
                result["failed"].append(field["fieldKey"])
                logger.error(f"Excecao ao criar {field['fieldKey']}: {e}")

    return result


async def batch_update_ghl_contacts(
    contacts: List[Dict[str, Any]],
    location_id: str
) -> Dict:
    """
    Atualiza multiplos contatos em batch.

    Args:
        contacts: Lista de dicts com contact_id e custom_fields
        location_id: ID da location

    Returns:
        Dict com estatisticas
    """
    results = {
        "total": len(contacts),
        "success": 0,
        "failed": 0,
        "errors": []
    }

    for contact in contacts:
        result = await update_ghl_contact_internal(
            contact_id=contact["contact_id"],
            location_id=location_id,
            custom_fields=contact["custom_fields"]
        )

        if result.get("updated"):
            results["success"] += 1
        else:
            results["failed"] += 1
            results["errors"].append({
                "contact_id": contact["contact_id"],
                "error": result.get("error")
            })

    return results
