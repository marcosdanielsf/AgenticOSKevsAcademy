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


def _make_error_response(
    error: str,
    contact_id: str = "",
    conversation_id: Optional[str] = None,
    available_types: Optional[List[str]] = None,
    channel_filter: Optional[str] = None,
    debug_hint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Cria resposta de erro padronizada com TODOS os campos esperados.
    Garante que nenhum campo fique faltando.
    """
    return {
        "origin": "unknown",
        "origin_label": f"Erro: {error}",
        "first_message_direction": None,
        "first_message_date": None,
        "first_message_preview": None,
        "conversation_id": conversation_id,
        "conversation_type": None,
        "total_messages": None,
        "tags_added": [],
        "contact_id": contact_id,
        "agent_context": None,
        "error": error,
        "available_conversation_types": available_types or [],
        "channel_filter_used": channel_filter,
        "debug_hint": debug_hint
    }


def _get_ghl_headers(api_key: Optional[str] = None) -> Dict[str, str]:
    """Headers para API GHL v2."""
    key = api_key or GHL_API_KEY
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Version": "2021-07-28"
    }


async def _search_conversation(contact_id: str, location_id: str, api_key: Optional[str] = None, channel_filter: Optional[str] = None) -> Dict:
    """
    Busca a conversa de um contato no GHL.

    API: GET /conversations/search?contactId={contact_id}&locationId={location_id}

    Args:
        channel_filter: Filtrar por canal específico ("instagram", "whatsapp", "sms", etc.)

    Returns:
        Dict com:
        - conversation: dados da conversa encontrada (ou None)
        - all_types: lista de tipos de conversa disponíveis (para debug)
        - error: mensagem de erro se houver
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
                return {"conversation": None, "all_types": [], "error": f"API error: {response.status_code}"}

            # Parse JSON com tratamento de erro
            try:
                data = response.json()
            except ValueError as je:
                logger.error(f"JSON inválido na resposta GHL: {je}")
                return {"conversation": None, "all_types": [], "error": f"JSON inválido: {str(je)}"}

            # Validar que data é dict
            if not isinstance(data, dict):
                logger.error(f"Resposta GHL não é dict: {type(data)}")
                return {"conversation": None, "all_types": [], "error": f"Resposta inválida (tipo: {type(data).__name__})"}

            conversations = data.get("conversations", [])

            # Garantir que conversations é lista
            if not isinstance(conversations, list):
                logger.error(f"conversations não é lista: {type(conversations)}")
                return {"conversation": None, "all_types": [], "error": f"Formato inválido de conversations"}

            # Extrair tipos com validação
            all_types = []
            for c in conversations:
                if isinstance(c, dict):
                    all_types.append(c.get("type", "unknown") or "unknown")

            if not conversations:
                logger.info(f"Nenhuma conversa encontrada para contact {contact_id}")
                return {"conversation": None, "all_types": [], "error": "Nenhuma conversa no GHL"}

            # Se channel_filter especificado, busca a conversa do canal correto
            if channel_filter:
                channel_lower = channel_filter.lower()
                for conv in conversations:
                    if not isinstance(conv, dict):
                        continue
                    conv_type = (conv.get("type") or "").lower()
                    # Verifica se o tipo da conversa contém o filtro
                    # Ex: "TYPE_INSTAGRAM" contém "instagram"
                    if channel_lower in conv_type:
                        logger.info(f"Conversa do canal {channel_filter} encontrada: {conv.get('id')}")
                        return {"conversation": conv, "all_types": all_types, "error": None}

                # Nenhuma conversa do canal encontrada
                logger.info(f"Nenhuma conversa do canal {channel_filter} para contact {contact_id}. Tipos disponíveis: {all_types}")
                return {"conversation": None, "all_types": all_types, "error": f"Canal {channel_filter} não encontrado"}

            # Retorna a primeira conversa que seja um dict válido
            for conv in conversations:
                if isinstance(conv, dict):
                    return {"conversation": conv, "all_types": all_types, "error": None}

            return {"conversation": None, "all_types": all_types, "error": "Nenhuma conversa válida encontrada"}

        except httpx.TimeoutException:
            logger.error(f"Timeout ao buscar conversa para contact {contact_id}")
            return {"conversation": None, "all_types": [], "error": "Timeout na API GHL"}
        except Exception as e:
            logger.error(f"Exceção ao buscar conversa: {e}", exc_info=True)
            return {"conversation": None, "all_types": [], "error": f"Erro: {str(e)}"}


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

            try:
                data = response.json()
            except ValueError as je:
                logger.error(f"JSON inválido ao buscar mensagens: {je}")
                return []

            if not isinstance(data, dict):
                logger.error(f"Resposta de mensagens não é dict: {type(data)}")
                return []

            messages = data.get("messages", [])

            if not isinstance(messages, list):
                logger.error(f"messages não é lista: {type(messages)}")
                return []

            return messages

        except httpx.TimeoutException:
            logger.error(f"Timeout ao buscar mensagens da conversa {conversation_id}")
            return []
        except Exception as e:
            logger.error(f"Exceção ao buscar mensagens: {e}", exc_info=True)
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
            logger.error(f"Exceção ao adicionar tags: {e}", exc_info=True)
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
    # Validar inputs
    if not contact_id or not isinstance(contact_id, str):
        return _make_error_response(
            error="contact_id inválido ou ausente",
            debug_hint="contact_id deve ser uma string não vazia"
        )

    if not location_id or not isinstance(location_id, str):
        return _make_error_response(
            error="location_id inválido ou ausente",
            contact_id=contact_id,
            debug_hint="location_id deve ser uma string não vazia"
        )

    # Usa api_key do parâmetro ou do ambiente
    effective_api_key = api_key or GHL_API_KEY

    if not effective_api_key:
        return _make_error_response(
            error="GHL_API_KEY não configurada",
            contact_id=contact_id,
            debug_hint="Passe api_key no body ou configure GHL_API_KEY no ambiente"
        )

    # 1. Buscar conversa do contato (já filtrando pelo canal se especificado)
    search_result = await _search_conversation(contact_id, location_id, effective_api_key, channel_filter)

    # Validar que search_result é dict
    if not isinstance(search_result, dict):
        return _make_error_response(
            error=f"Erro interno: search_result não é dict (tipo: {type(search_result).__name__})",
            contact_id=contact_id,
            channel_filter=channel_filter
        )

    conversation = search_result.get("conversation")
    all_types = search_result.get("all_types", [])

    # Garantir que all_types é lista
    if not isinstance(all_types, list):
        all_types = []

    if not conversation:
        return _make_error_response(
            error=search_result.get("error") or "Nenhuma conversa encontrada",
            contact_id=contact_id,
            available_types=all_types,
            channel_filter=channel_filter,
            debug_hint="Verifique se o contato tem conversa do canal especificado no GHL"
        )

    # Validar que conversation é dict
    if not isinstance(conversation, dict):
        return _make_error_response(
            error=f"Conversa em formato inválido (tipo: {type(conversation).__name__})",
            contact_id=contact_id,
            available_types=all_types,
            channel_filter=channel_filter
        )

    conversation_id = conversation.get("id")
    conversation_type = (conversation.get("type") or "").lower()

    if not conversation_id:
        return _make_error_response(
            error="Conversa sem ID",
            contact_id=contact_id,
            available_types=all_types,
            channel_filter=channel_filter
        )

    # 2. Buscar mensagens da conversa
    messages = await _get_conversation_messages(conversation_id, limit=100, api_key=effective_api_key)

    if not messages:
        return _make_error_response(
            error="Conversa sem mensagens",
            contact_id=contact_id,
            conversation_id=conversation_id,
            available_types=all_types,
            channel_filter=channel_filter
        )

    # 2.5. Filtrar apenas mensagens que são dicts válidos
    valid_messages = [m for m in messages if isinstance(m, dict)]

    if not valid_messages:
        sample = str(messages[:2])[:200] if messages else "[]"
        logger.error(f"Mensagens em formato inválido para conversa {conversation_id}: {sample}")
        return _make_error_response(
            error=f"Formato de mensagens inválido (tipo: {type(messages[0]).__name__ if messages else 'none'})",
            contact_id=contact_id,
            conversation_id=conversation_id,
            debug_hint=f"Sample: {sample}"
        )

    # 3. Ordenar por data (mais antiga primeiro)
    # Usar função segura para ordenação
    def safe_get_date(m: Dict) -> str:
        if not isinstance(m, dict):
            return ""
        return (m.get("dateAdded") or m.get("createdAt") or "")

    messages_sorted = sorted(valid_messages, key=safe_get_date)

    # Double-check: garantir que temos mensagens após ordenação
    if not messages_sorted:
        return _make_error_response(
            error="Nenhuma mensagem válida após ordenação",
            contact_id=contact_id,
            conversation_id=conversation_id
        )

    # 4. Pegar a PRIMEIRA mensagem
    first_message = messages_sorted[0]

    # Extrair campos com tratamento seguro de None
    # CRÍTICO: usar (value or "") para evitar .lower() ou [:] em None
    raw_direction = first_message.get("direction")
    first_direction = (raw_direction or "").lower() if isinstance(raw_direction, str) else ""

    first_date = first_message.get("dateAdded") or first_message.get("createdAt")

    raw_body = first_message.get("body")
    first_body = ((raw_body or "")[:100]) if isinstance(raw_body, str) else ""

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
        origin_label = f"Direção não identificada: '{first_direction}'"
        tags_to_add = []

    # 6. Auto-tagging se habilitado
    tags_added = []
    if auto_tag and tags_to_add:
        success = await _add_tags_to_contact(contact_id, tags_to_add, effective_api_key)
        if success:
            tags_added = tags_to_add

    # 7. Montar resposta completa
    result = {
        "origin": origin,
        "origin_label": origin_label,
        "first_message_direction": first_direction,
        "first_message_date": first_date,
        "first_message_preview": first_body,
        "conversation_id": conversation_id,
        "conversation_type": conversation_type,
        "total_messages": len(valid_messages),
        "tags_added": tags_added,
        "contact_id": contact_id,
        "error": None,
        "available_conversation_types": all_types,
        "channel_filter_used": channel_filter,
        "debug_hint": None
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
        ),
        "tom_agente": "direto, dar continuidade" if origin == "outbound" else "receptivo, qualificar",
        "origem_conversa": origin
    }

    logger.info(f"Origem detectada para {contact_id}: {origin} ({origin_label})")

    return result
