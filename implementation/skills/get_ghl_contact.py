"""
Skill: get_ghl_contact
======================
Busca contato completo no GHL e extrai informações importantes,
especialmente o username do Instagram.

Uso:
    from skills.get_ghl_contact import get_ghl_contact

    result = await get_ghl_contact(
        contact_id="abc123",
        location_id="loc_xyz",
        api_key="pit-xxx"
    )

    # result.data = {
    #     "contact_id": "abc123",
    #     "instagram_username": "dra.marilia.santos",
    #     "profile_photo": "https://...",
    #     "full_name": "Dra Marilia Santos",
    #     "tags": ["tag1", "tag2"],
    #     "source": "instagram",
    #     "ig_sid": "1386946543118614"
    # }
"""

import os
import httpx
from typing import Dict, Any, Optional

from . import skill, logger

# GHL API Config
GHL_API_URL = "https://services.leadconnectorhq.com"


def _get_ghl_headers(api_key: str) -> Dict[str, str]:
    """Headers para API GHL v2."""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Version": "2021-07-28"
    }


def _extract_instagram_username(contact: Dict) -> Optional[str]:
    """
    Extrai o username do Instagram do contato.

    O GHL guarda o username em diferentes lugares dependendo da origem:
    - firstName (quando vem do Instagram DM)
    - fullNameLowerCase
    - customFields com chave específica
    - attributionSource.mediumId
    """
    if not contact:
        return None

    # 1. Verificar se veio do Instagram
    attribution = contact.get("attributionSource") or {}
    medium = (attribution.get("medium") or "").lower()

    if medium == "instagram":
        # firstName geralmente é o username quando vem do Instagram
        first_name = contact.get("firstName") or ""
        full_name_lower = contact.get("fullNameLowerCase") or ""

        # Se firstName parece um username (sem espaços, lowercase)
        if first_name and " " not in first_name and first_name == first_name.lower():
            return first_name

        # Fallback para fullNameLowerCase
        if full_name_lower and " " not in full_name_lower:
            return full_name_lower

    # 2. Verificar campo customizado 'instagram'
    custom_fields = contact.get("customFields") or []
    for field in custom_fields:
        if isinstance(field, dict):
            field_id = (field.get("id") or "").lower()
            field_key = (field.get("key") or "").lower()
            if "instagram" in field_id or "instagram" in field_key:
                value = field.get("value")
                if value:
                    # Remover @ se tiver
                    return value.lstrip("@")

    # 3. Última tentativa: firstName mesmo sem ser lowercase
    first_name = contact.get("firstName")
    if first_name and " " not in first_name:
        return first_name.lower().replace(" ", "")

    return None


@skill(
    name="get_ghl_contact",
    description="Busca contato no GHL e extrai username do Instagram"
)
async def get_ghl_contact(
    contact_id: str,
    api_key: str,
    location_id: Optional[str] = None  # Não usado, mas mantido para compatibilidade
) -> Dict[str, Any]:
    """
    Busca contato completo no GHL.

    Args:
        contact_id: ID do contato no GHL
        api_key: GHL API key (Private Integration Token)
        location_id: ID da location (opcional)

    Returns:
        Dict com dados do contato e username do Instagram extraído
    """
    if not contact_id:
        return {
            "error": "contact_id é obrigatório",
            "contact_id": None
        }

    if not api_key:
        return {
            "error": "api_key é obrigatório",
            "contact_id": contact_id
        }

    headers = _get_ghl_headers(api_key)
    url = f"{GHL_API_URL}/contacts/{contact_id}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers)

            if response.status_code == 404:
                return {
                    "error": "Contato não encontrado",
                    "contact_id": contact_id,
                    "status_code": 404
                }

            if response.status_code == 401:
                return {
                    "error": "API key inválida ou sem permissão",
                    "contact_id": contact_id,
                    "status_code": 401
                }

            if response.status_code != 200:
                return {
                    "error": f"Erro na API GHL: {response.status_code}",
                    "contact_id": contact_id,
                    "status_code": response.status_code,
                    "response_text": response.text[:500]
                }

            data = response.json()
            contact = data.get("contact") or {}

            # Extrair informações
            attribution = contact.get("attributionSource") or {}
            last_attribution = contact.get("lastAttributionSource") or {}

            # Extrair username do Instagram
            instagram_username = _extract_instagram_username(contact)

            result = {
                "contact_id": contact_id,
                "instagram_username": instagram_username,
                "profile_photo": contact.get("profilePhoto"),
                "full_name": contact.get("firstName"),
                "email": contact.get("email"),
                "phone": contact.get("phone"),
                "tags": contact.get("tags") or [],
                "source": attribution.get("medium") or last_attribution.get("medium"),
                "ig_sid": attribution.get("igSid") or last_attribution.get("igSid"),
                "country": contact.get("country"),
                "date_added": contact.get("dateAdded"),
                "custom_fields": contact.get("customFields") or [],
                "raw_attribution": attribution
            }

            # Log para debug
            if instagram_username:
                logger.info(f"Username Instagram extraído: @{instagram_username}")
            else:
                logger.warning(f"Não foi possível extrair username do Instagram para contact {contact_id}")

            return result

        except httpx.TimeoutException:
            return {
                "error": "Timeout ao buscar contato no GHL",
                "contact_id": contact_id
            }
        except Exception as e:
            logger.error(f"Erro ao buscar contato: {e}", exc_info=True)
            return {
                "error": f"Erro: {str(e)}",
                "contact_id": contact_id
            }
