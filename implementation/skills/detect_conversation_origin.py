"""
Skill: detect_conversation_origin
=================================
Detecta se uma conversa no GHL foi iniciada pela empresa (outbound/BDR)
ou pelo lead (inbound/novo seguidor).

PALIATIVO para uso enquanto AgenticOS não está 100% integrado.

Uso:
    from skills.detect_conversation_origin import detect_conversation_origin

    result = await detect_conversation_origin(
        contact_id="abc123",
        location_id="loc_xyz",
        auto_tag=True  # Adiciona tags automaticamente
    )

    # result.data = {
    #     "origin": "outbound" | "inbound",
    #     "first_message_direction": "outbound" | "inbound",
    #     "first_message_date": "2026-01-19T10:00:00Z",
    #     "first_message_preview": "Oi, vi que você...",
    #     "conversation_id": "conv_xyz",
    #     "tags_added": ["outbound-instagram", "bdr-abordou"]
    # }
"""

import os
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime

from . import skill, logger

# GHL API Config
GHL_API_URL = "https://services.leadconnectorhq.com"
GHL_API_KEY = os.getenv("GHL_API_KEY") or os.getenv("GHL_ACCESS_TOKEN")


def _get_ghl_headers(api_key: Optional[str] = None) -> Dict[str, str]:
    """Headers para API GHL v2."""
    key = api_key or GHL_API_KEY
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Version": "2021-07-28"
    }


async def _search_conversation(contact_id: str, location_id: str, api_key: Optional[str] = None, channel_filter: Optional[str] = None) -> Optional[Dict]:
    """
    Busca a conversa de um contato no GHL.

    API: GET /conversations/search?contactId={contact_id}&locationId={location_id}

    Args:
        channel_filter: Filtrar por canal específico ("instagram", "whatsapp", "sms", etc.)
    """
    headers = _get_ghl_headers(api_key)

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{GHL_API_URL}/conversations/search",
                headers=headers,
                params={
                    "contactId": contact_id,
                    "locationId": location_id
                }
            )

            if response.status_code != 200:
                logger.error(f"Erro ao buscar conversa: {response.status_code} - {response.text}")
                return None

            data = response.json()
            conversations = data.get("conversations", [])

            if not conversations:
                logger.info(f"Nenhuma conversa encontrada para contact {contact_id}")
                return None

            # Se channel_filter especificado, busca a conversa do canal correto
            if channel_filter:
                channel_lower = channel_filter.lower()
                for conv in conversations:
                    conv_type = conv.get("type", "").lower()
                    # Verifica se o tipo da conversa contém o filtro
                    # Ex: "TYPE_INSTAGRAM" contém "instagram"
                    if channel_lower in conv_type:
                        logger.info(f"Conversa do canal {channel_filter} encontrada: {conv.get('id')}")
                        return conv

                # Nenhuma conversa do canal encontrada
                logger.info(f"Nenhuma conversa do canal {channel_filter} para contact {contact_id}. Tipos disponíveis: {[c.get('type') for c in conversations]}")
                return None

            # Retorna a primeira (mais recente por padrão)
            return conversations[0]

        except Exception as e:
            logger.error(f"Exceção ao buscar conversa: {e}")
            return None


async def _get_conversation_messages(conversation_id: str, limit: int = 50, api_key: Optional[str] = None) -> List[Dict]:
    """
    Busca mensagens de uma conversa.

    API: GET /conversations/{conversationId}/messages
    """
    headers = _get_ghl_headers(api_key)

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{GHL_API_URL}/conversations/{conversation_id}/messages",
                headers=headers,
                params={"limit": limit}
            )

            if response.status_code != 200:
                logger.error(f"Erro ao buscar mensagens: {response.status_code} - {response.text}")
                return []

            data = response.json()
            return data.get("messages", [])

        except Exception as e:
            logger.error(f"Exceção ao buscar mensagens: {e}")
            return []


async def _add_tags_to_contact(contact_id: str, tags: List[str], api_key: Optional[str] = None) -> bool:
    """
    Adiciona tags a um contato no GHL.

    API: POST /contacts/{contactId}/tags
    """
    headers = _get_ghl_headers(api_key)

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{GHL_API_URL}/contacts/{contact_id}/tags",
                headers=headers,
                json={"tags": tags}
            )

            if response.status_code in [200, 201]:
                logger.info(f"Tags {tags} adicionadas ao contato {contact_id}")
                return True
            else:
                logger.error(f"Erro ao adicionar tags: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Exceção ao adicionar tags: {e}")
            return False


@skill(
    name="detect_conversation_origin",
    description="Detecta se conversa foi iniciada por outbound (BDR) ou inbound (lead)"
)
async def detect_conversation_origin(
    contact_id: str,
    location_id: str,
    auto_tag: bool = True,
    channel_filter: Optional[str] = None,  # "instagram", "whatsapp", etc.
    api_key: Optional[str] = None  # GHL API key (usa env var se não fornecida)
) -> Dict[str, Any]:
    """
    Detecta a origem de uma conversa analisando quem enviou a primeira mensagem.

    Args:
        contact_id: ID do contato no GHL
        location_id: ID da location no GHL
        auto_tag: Se True, adiciona tags automaticamente ao contato
        channel_filter: Filtrar por canal específico (opcional)
        api_key: GHL API key (opcional, usa GHL_API_KEY do ambiente se não fornecida)

    Returns:
        Dict com origin ("outbound" ou "inbound"), detalhes da primeira mensagem,
        e tags adicionadas (se auto_tag=True)
    """
    # Usa api_key do parâmetro ou do ambiente
    effective_api_key = api_key or GHL_API_KEY

    if not effective_api_key:
        return {
            "origin": "unknown",
            "error": "GHL_API_KEY não configurada"
        }

    # 1. Buscar conversa do contato (já filtrando pelo canal se especificado)
    conversation = await _search_conversation(contact_id, location_id, effective_api_key, channel_filter)

    if not conversation:
        return {
            "origin": "unknown",
            "error": "Nenhuma conversa encontrada",
            "contact_id": contact_id
        }

    conversation_id = conversation.get("id")
    conversation_type = conversation.get("type", "").lower()  # sms, email, instagram, etc.

    # 2. Buscar mensagens da conversa
    messages = await _get_conversation_messages(conversation_id, limit=100, api_key=effective_api_key)

    if not messages:
        return {
            "origin": "unknown",
            "error": "Conversa sem mensagens",
            "conversation_id": conversation_id
        }

    # 3. Ordenar por data (mais antiga primeiro)
    # GHL retorna em ordem decrescente (mais recente primeiro), então invertemos
    messages_sorted = sorted(
        messages,
        key=lambda m: m.get("dateAdded", m.get("createdAt", ""))
    )

    # 4. Pegar a PRIMEIRA mensagem
    first_message = messages_sorted[0]

    # direction: "inbound" = lead enviou, "outbound" = empresa enviou
    first_direction = first_message.get("direction", "").lower()
    first_date = first_message.get("dateAdded") or first_message.get("createdAt")
    first_body = first_message.get("body", "")[:100]  # Preview de 100 chars

    # 5. Determinar origem
    if first_direction == "outbound":
        origin = "outbound"
        origin_label = "BDR/Empresa iniciou (prospecção)"
        tags_to_add = ["outbound-instagram", "bdr-abordou", "prospectado"]
    elif first_direction == "inbound":
        origin = "inbound"
        origin_label = "Lead iniciou (novo seguidor/orgânico)"
        tags_to_add = ["novo-seguidor", "inbound-organico", "lead-iniciou"]
    else:
        origin = "unknown"
        origin_label = f"Direção não identificada: {first_direction}"
        tags_to_add = []

    # 6. Auto-tagging se habilitado
    tags_added = []
    if auto_tag and tags_to_add:
        success = await _add_tags_to_contact(contact_id, tags_to_add, effective_api_key)
        if success:
            tags_added = tags_to_add

    # 7. Montar resposta
    result = {
        "origin": origin,
        "origin_label": origin_label,
        "first_message_direction": first_direction,
        "first_message_date": first_date,
        "first_message_preview": first_body,
        "conversation_id": conversation_id,
        "conversation_type": conversation_type,
        "total_messages": len(messages),
        "tags_added": tags_added,
        "contact_id": contact_id
    }

    # 8. Incluir contexto para o agente social_seller
    result["agent_context"] = {
        "should_activate": True,
        "context_type": "prospecting_response" if origin == "outbound" else "inbound_organic",
        "source_channel": f"{conversation_type}_dm" if conversation_type else "instagram_dm",
        "recommendation": (
            "Lead respondendo prospecção - ativar qualificação imediata"
            if origin == "outbound"
            else "Novo lead orgânico - iniciar qualificação com tom receptivo"
        )
    }

    logger.info(f"Origem detectada para {contact_id}: {origin} ({origin_label})")

    return result
