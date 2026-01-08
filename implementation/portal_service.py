#!/usr/bin/env python3
"""
Portal CRM Service
==================
Lógica de negócio para o Portal CRM Multi-Tenant MOTTIVME Sales.

Este módulo implementa:
- Sincronização de leads GHL → Supabase
- Sincronização de conversas e mensagens
- Cálculo de métricas diárias
- APIs para dashboard, leads e conversas

Integração:
- Usa tabelas do Growth OS (growth_*)
- Usa tabelas do Portal (portal_*)
- Supabase Auth para autenticação
- RLS para isolamento multi-tenant
"""

import os
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Setup logging
logger = logging.getLogger(__name__)

# Supabase config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


class FunnelStage(str, Enum):
    """Etapas do funil de vendas (Growth OS)"""
    PROSPECTED = "prospected"
    LEAD = "lead"
    QUALIFIED = "qualified"
    SCHEDULED = "scheduled"
    SHOWED = "showed"
    NO_SHOW = "no_show"
    PROPOSAL = "proposal"
    WON = "won"
    LOST = "lost"


class SourceType(str, Enum):
    """Tipos de fonte de lead"""
    OUTBOUND = "outbound"
    INBOUND = "inbound"


# Mapeamento de source_channel para source_type
OUTBOUND_CHANNELS = ["instagram_dm", "linkedin", "cold_email", "cold_call"]
INBOUND_CHANNELS = ["ads", "inbound_call", "referral", "whatsapp", "reactivation", "facebook_ads", "instagram_ads", "google_ads", "organic"]


def get_source_type(source_channel: str) -> str:
    """Determina se o canal é outbound ou inbound"""
    if source_channel in OUTBOUND_CHANNELS:
        return SourceType.OUTBOUND.value
    return SourceType.INBOUND.value


@dataclass
class LeadSyncData:
    """Dados para sincronizar um lead do GHL"""
    ghl_contact_id: str
    location_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    instagram_username: Optional[str] = None
    source_channel: Optional[str] = None
    source_campaign: Optional[str] = None
    funnel_stage: str = FunnelStage.LEAD.value
    lead_temperature: str = "cold"
    lead_score: int = 0
    tags: List[str] = None
    custom_fields: Dict = None


@dataclass
class MessageSyncData:
    """Dados para sincronizar uma mensagem do GHL"""
    ghl_conversation_id: str
    ghl_message_id: str
    location_id: str
    ghl_contact_id: str
    content: str
    direction: str  # inbound, outbound
    channel: str  # instagram, whatsapp, sms, email
    sent_at: datetime
    sender_name: Optional[str] = None
    is_from_ai: bool = False
    content_type: str = "text"
    media_url: Optional[str] = None


class PortalService:
    """
    Serviço principal do Portal CRM.
    Gerencia sincronização, métricas e consultas.
    """

    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        self.supabase_url = supabase_url or SUPABASE_URL
        self.supabase_key = supabase_key or SUPABASE_KEY

        if not self.supabase_url or not self.supabase_key:
            logger.warning("Supabase credentials not configured")

    def _get_supabase_client(self):
        """Obtém cliente Supabase"""
        try:
            from supabase import create_client
            return create_client(self.supabase_url, self.supabase_key)
        except Exception as e:
            logger.error(f"Failed to create Supabase client: {e}")
            raise

    # =========================================================================
    # SYNC: Lead do GHL → Supabase (growth_leads)
    # =========================================================================

    def sync_lead(self, data: LeadSyncData) -> Dict[str, Any]:
        """
        Sincroniza um lead do GHL para o Supabase (growth_leads).
        Cria ou atualiza baseado no ghl_contact_id.

        Args:
            data: Dados do lead para sincronizar

        Returns:
            Dict com resultado da operação
        """
        try:
            supabase = self._get_supabase_client()

            # Verificar se já existe
            existing = supabase.table("growth_leads").select("id, funnel_stage").eq(
                "location_id", data.location_id
            ).eq(
                "ghl_contact_id", data.ghl_contact_id
            ).execute()

            lead_data = {
                "location_id": data.location_id,
                "ghl_contact_id": data.ghl_contact_id,
                "name": data.name,
                "email": data.email,
                "phone": data.phone,
                "instagram_username": data.instagram_username,
                "source_channel": data.source_channel,
                "source_campaign": data.source_campaign,
                "funnel_stage": data.funnel_stage,
                "lead_temperature": data.lead_temperature,
                "lead_score": data.lead_score,
                "tags": data.tags or [],
                "custom_fields": data.custom_fields or {},
                "updated_at": datetime.now().isoformat()
            }

            if existing.data:
                # Update existente
                lead_id = existing.data[0]["id"]
                old_stage = existing.data[0]["funnel_stage"]

                # Registrar mudança de stage se houver
                if old_stage != data.funnel_stage:
                    lead_data["previous_stage"] = old_stage
                    lead_data["stage_changed_at"] = datetime.now().isoformat()

                    # Registrar timestamps específicos por stage
                    stage_timestamps = {
                        FunnelStage.QUALIFIED.value: "qualified_at",
                        FunnelStage.SCHEDULED.value: "meeting_scheduled_at",
                        FunnelStage.SHOWED.value: "showed_at",
                        FunnelStage.WON.value: "converted_at",
                        FunnelStage.LOST.value: "lost_at"
                    }
                    if data.funnel_stage in stage_timestamps:
                        lead_data[stage_timestamps[data.funnel_stage]] = datetime.now().isoformat()

                result = supabase.table("growth_leads").update(lead_data).eq("id", lead_id).execute()
                action = "updated"
            else:
                # Insert novo
                lead_data["created_at"] = datetime.now().isoformat()
                lead_data["first_contact_at"] = datetime.now().isoformat() if data.funnel_stage == FunnelStage.LEAD.value else None
                result = supabase.table("growth_leads").insert(lead_data).execute()
                action = "created"
                lead_id = result.data[0]["id"] if result.data else None

            logger.info(f"Lead {action}: {data.ghl_contact_id} -> {lead_id}")

            return {
                "success": True,
                "action": action,
                "lead_id": lead_id,
                "ghl_contact_id": data.ghl_contact_id
            }

        except Exception as e:
            logger.error(f"Error syncing lead: {e}")
            return {
                "success": False,
                "error": str(e),
                "ghl_contact_id": data.ghl_contact_id
            }

    # =========================================================================
    # SYNC: Mensagem do GHL → Supabase (portal_conversations + portal_messages)
    # =========================================================================

    def sync_message(self, data: MessageSyncData) -> Dict[str, Any]:
        """
        Sincroniza uma mensagem do GHL para o Supabase.
        Cria/atualiza conversa e adiciona mensagem.

        Args:
            data: Dados da mensagem para sincronizar

        Returns:
            Dict com resultado da operação
        """
        try:
            supabase = self._get_supabase_client()

            # 1. Buscar ou criar conversa
            conversation = supabase.table("portal_conversations").select("id").eq(
                "location_id", data.location_id
            ).eq(
                "ghl_conversation_id", data.ghl_conversation_id
            ).execute()

            if conversation.data:
                conversation_id = conversation.data[0]["id"]
            else:
                # Buscar lead_id se existir
                lead = supabase.table("growth_leads").select("id").eq(
                    "location_id", data.location_id
                ).eq(
                    "ghl_contact_id", data.ghl_contact_id
                ).execute()

                lead_id = lead.data[0]["id"] if lead.data else None

                # Criar conversa
                conv_result = supabase.table("portal_conversations").insert({
                    "location_id": data.location_id,
                    "ghl_conversation_id": data.ghl_conversation_id,
                    "ghl_contact_id": data.ghl_contact_id,
                    "lead_id": lead_id,
                    "channel": data.channel,
                    "status": "open",
                    "created_at": datetime.now().isoformat()
                }).execute()

                conversation_id = conv_result.data[0]["id"]
                logger.info(f"Created conversation: {conversation_id}")

            # 2. Verificar se mensagem já existe
            existing_msg = supabase.table("portal_messages").select("id").eq(
                "ghl_message_id", data.ghl_message_id
            ).execute()

            if existing_msg.data:
                return {
                    "success": True,
                    "action": "skipped",
                    "reason": "message_already_exists",
                    "message_id": existing_msg.data[0]["id"]
                }

            # 3. Inserir mensagem
            msg_data = {
                "conversation_id": conversation_id,
                "location_id": data.location_id,
                "ghl_message_id": data.ghl_message_id,
                "content": data.content,
                "content_type": data.content_type,
                "direction": data.direction,
                "sender_type": "ai" if data.is_from_ai else ("lead" if data.direction == "inbound" else "human"),
                "sender_name": data.sender_name,
                "is_from_ai": data.is_from_ai,
                "media_url": data.media_url,
                "sent_at": data.sent_at.isoformat() if isinstance(data.sent_at, datetime) else data.sent_at,
                "created_at": datetime.now().isoformat()
            }

            result = supabase.table("portal_messages").insert(msg_data).execute()
            message_id = result.data[0]["id"] if result.data else None

            logger.info(f"Message synced: {data.ghl_message_id} -> {message_id}")

            return {
                "success": True,
                "action": "created",
                "conversation_id": conversation_id,
                "message_id": message_id
            }

        except Exception as e:
            logger.error(f"Error syncing message: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # =========================================================================
    # MÉTRICAS: Calcular métricas diárias
    # =========================================================================

    def calculate_daily_metrics(
        self,
        location_id: str,
        target_date: date = None
    ) -> Dict[str, Any]:
        """
        Calcula métricas diárias para um location_id.
        Popula portal_metrics_daily e growth_funnel_daily.

        Args:
            location_id: ID do tenant
            target_date: Data alvo (default: hoje)

        Returns:
            Dict com as métricas calculadas
        """
        try:
            supabase = self._get_supabase_client()
            target_date = target_date or date.today()
            date_str = target_date.isoformat()

            # Buscar todos os leads do location até a data
            leads = supabase.table("growth_leads").select(
                "id, funnel_stage, source_channel, lead_temperature, conversion_value, created_at"
            ).eq("location_id", location_id).execute()

            if not leads.data:
                return {
                    "success": True,
                    "location_id": location_id,
                    "date": date_str,
                    "message": "No leads found"
                }

            # Calcular métricas
            metrics = {
                "prospected_outbound": 0,
                "leads_outbound": 0,
                "leads_inbound": 0,
                "leads_instagram_dm": 0,
                "leads_linkedin": 0,
                "leads_cold_email": 0,
                "leads_cold_call": 0,
                "leads_facebook_ads": 0,
                "leads_instagram_ads": 0,
                "leads_whatsapp": 0,
                "leads_referral": 0,
                "leads_organic": 0,
                "revenue": 0
            }

            funnel_counts = {stage.value: 0 for stage in FunnelStage}

            for lead in leads.data:
                stage = lead.get("funnel_stage")
                source = lead.get("source_channel", "")
                value = lead.get("conversion_value") or 0

                # Contar por stage
                if stage in funnel_counts:
                    funnel_counts[stage] += 1

                # Contar por source type
                if source in OUTBOUND_CHANNELS:
                    if stage == FunnelStage.PROSPECTED.value:
                        metrics["prospected_outbound"] += 1
                    else:
                        metrics["leads_outbound"] += 1
                else:
                    metrics["leads_inbound"] += 1

                # Contar por canal específico
                channel_mapping = {
                    "instagram_dm": "leads_instagram_dm",
                    "linkedin": "leads_linkedin",
                    "cold_email": "leads_cold_email",
                    "cold_call": "leads_cold_call",
                    "facebook_ads": "leads_facebook_ads",
                    "instagram_ads": "leads_instagram_ads",
                    "ads": "leads_facebook_ads",  # fallback
                    "whatsapp": "leads_whatsapp",
                    "referral": "leads_referral",
                    "organic": "leads_organic"
                }
                if source in channel_mapping:
                    metrics[channel_mapping[source]] += 1

                # Receita dos won
                if stage == FunnelStage.WON.value:
                    metrics["revenue"] += value

            # Upsert portal_metrics_daily
            portal_metrics = {
                "date": date_str,
                "location_id": location_id,
                "prospected_outbound": metrics["prospected_outbound"],
                "leads_outbound": metrics["leads_outbound"],
                "leads_inbound": metrics["leads_inbound"],
                "leads_instagram_dm": metrics["leads_instagram_dm"],
                "leads_linkedin": metrics["leads_linkedin"],
                "leads_cold_email": metrics["leads_cold_email"],
                "leads_cold_call": metrics["leads_cold_call"],
                "leads_facebook_ads": metrics["leads_facebook_ads"],
                "leads_instagram_ads": metrics["leads_instagram_ads"],
                "leads_whatsapp": metrics["leads_whatsapp"],
                "leads_referral": metrics["leads_referral"],
                "leads_organic": metrics["leads_organic"],
                "revenue": metrics["revenue"],
                "updated_at": datetime.now().isoformat()
            }

            # Upsert (insert or update on conflict)
            supabase.table("portal_metrics_daily").upsert(
                portal_metrics,
                on_conflict="date,location_id"
            ).execute()

            # Calcular taxas de conversão
            total_prospected = funnel_counts[FunnelStage.PROSPECTED.value]
            total_leads = funnel_counts[FunnelStage.LEAD.value]
            total_qualified = funnel_counts[FunnelStage.QUALIFIED.value]
            total_scheduled = funnel_counts[FunnelStage.SCHEDULED.value]
            total_showed = funnel_counts[FunnelStage.SHOWED.value]
            total_won = funnel_counts[FunnelStage.WON.value]

            rates = {
                "lead_rate": round((total_leads / total_prospected * 100) if total_prospected > 0 else 0, 2),
                "qualification_rate": round((total_qualified / total_leads * 100) if total_leads > 0 else 0, 2),
                "scheduling_rate": round((total_scheduled / total_qualified * 100) if total_qualified > 0 else 0, 2),
                "show_rate": round((total_showed / total_scheduled * 100) if total_scheduled > 0 else 0, 2),
                "closing_rate": round((total_won / total_showed * 100) if total_showed > 0 else 0, 2),
                "total_conversion_rate": round((total_won / total_prospected * 100) if total_prospected > 0 else 0, 2)
            }

            logger.info(f"Calculated metrics for {location_id} on {date_str}")

            return {
                "success": True,
                "location_id": location_id,
                "date": date_str,
                "funnel": funnel_counts,
                "breakdown": {
                    "outbound": {
                        "prospected": metrics["prospected_outbound"],
                        "leads": metrics["leads_outbound"]
                    },
                    "inbound": {
                        "leads": metrics["leads_inbound"]
                    }
                },
                "channels": {
                    "instagram_dm": metrics["leads_instagram_dm"],
                    "linkedin": metrics["leads_linkedin"],
                    "cold_email": metrics["leads_cold_email"],
                    "facebook_ads": metrics["leads_facebook_ads"],
                    "whatsapp": metrics["leads_whatsapp"]
                },
                "rates": rates,
                "revenue": metrics["revenue"]
            }

        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # =========================================================================
    # API: Dashboard Summary
    # =========================================================================

    def get_dashboard_summary(
        self,
        location_id: str,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Obtém resumo do dashboard para um tenant.

        Args:
            location_id: ID do tenant
            period_days: Período em dias (7, 30, 90)

        Returns:
            Dict com KPIs, funil, breakdown e métricas
        """
        try:
            supabase = self._get_supabase_client()
            start_date = (date.today() - timedelta(days=period_days)).isoformat()

            # Chamar função do Supabase
            result = supabase.rpc(
                "portal_get_dashboard_summary",
                {
                    "p_location_id": location_id,
                    "p_start_date": start_date,
                    "p_end_date": date.today().isoformat()
                }
            ).execute()

            if result.data:
                return {
                    "success": True,
                    "data": result.data,
                    "period": {
                        "days": period_days,
                        "start": start_date,
                        "end": date.today().isoformat()
                    }
                }

            # Fallback: calcular manualmente
            return self._calculate_dashboard_manually(location_id, start_date)

        except Exception as e:
            logger.error(f"Error getting dashboard summary: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _calculate_dashboard_manually(self, location_id: str, start_date: str) -> Dict[str, Any]:
        """Calcula dashboard manualmente se função RPC não existir"""
        try:
            supabase = self._get_supabase_client()

            # Buscar leads
            leads = supabase.table("growth_leads").select(
                "id, funnel_stage, source_channel, conversion_value, lead_temperature"
            ).eq(
                "location_id", location_id
            ).gte(
                "created_at", start_date
            ).execute()

            if not leads.data:
                return {
                    "success": True,
                    "data": {
                        "kpis": {"prospected": 0, "leads": 0, "qualified": 0, "scheduled": 0, "showed": 0, "won": 0, "lost": 0},
                        "breakdown": {"outbound": 0, "inbound": 0},
                        "revenue": {"total": 0, "avg_ticket": 0}
                    }
                }

            # Calcular KPIs
            kpis = {stage.value: 0 for stage in FunnelStage}
            outbound = 0
            inbound = 0
            total_revenue = 0

            for lead in leads.data:
                stage = lead.get("funnel_stage")
                source = lead.get("source_channel", "")

                if stage in kpis:
                    kpis[stage] += 1

                if source in OUTBOUND_CHANNELS:
                    outbound += 1
                else:
                    inbound += 1

                if stage == FunnelStage.WON.value:
                    total_revenue += lead.get("conversion_value") or 0

            won_count = kpis.get(FunnelStage.WON.value, 0)

            return {
                "success": True,
                "data": {
                    "kpis": kpis,
                    "breakdown": {
                        "outbound": outbound,
                        "inbound": inbound
                    },
                    "revenue": {
                        "total": total_revenue,
                        "avg_ticket": round(total_revenue / won_count, 2) if won_count > 0 else 0
                    }
                }
            }

        except Exception as e:
            logger.error(f"Error in manual dashboard calculation: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # API: Lista de Leads
    # =========================================================================

    def get_leads(
        self,
        location_id: str,
        page: int = 1,
        limit: int = 20,
        stage: str = None,
        source_type: str = None,
        search: str = None
    ) -> Dict[str, Any]:
        """
        Lista leads paginados com filtros.

        Args:
            location_id: ID do tenant
            page: Página atual
            limit: Itens por página
            stage: Filtrar por etapa do funil
            source_type: 'outbound' ou 'inbound'
            search: Busca por nome/email

        Returns:
            Dict com leads e paginação
        """
        try:
            supabase = self._get_supabase_client()

            # Tentar usar função RPC
            result = supabase.rpc(
                "portal_get_leads",
                {
                    "p_location_id": location_id,
                    "p_page": page,
                    "p_limit": limit,
                    "p_stage": stage,
                    "p_source_type": source_type,
                    "p_search": search
                }
            ).execute()

            if result.data:
                return {"success": True, "data": result.data}

            # Fallback manual
            return self._get_leads_manually(location_id, page, limit, stage, source_type, search)

        except Exception as e:
            logger.error(f"Error getting leads: {e}")
            return {"success": False, "error": str(e)}

    def _get_leads_manually(
        self,
        location_id: str,
        page: int,
        limit: int,
        stage: str,
        source_type: str,
        search: str
    ) -> Dict[str, Any]:
        """Lista leads manualmente se função RPC não existir"""
        try:
            supabase = self._get_supabase_client()
            offset = (page - 1) * limit

            # Query base
            query = supabase.table("growth_leads").select(
                "id, name, email, phone, instagram_username, source_channel, funnel_stage, lead_temperature, lead_score, bant_total_score, last_contact_at, created_at",
                count="exact"
            ).eq("location_id", location_id)

            # Filtros
            if stage:
                query = query.eq("funnel_stage", stage)

            if search:
                query = query.or_(f"name.ilike.%{search}%,email.ilike.%{search}%")

            # Paginação
            query = query.order("created_at", desc=True).range(offset, offset + limit - 1)

            result = query.execute()

            # Filtrar por source_type em memória (sem OR complexo no Supabase)
            leads = result.data or []
            if source_type:
                if source_type == "outbound":
                    leads = [l for l in leads if l.get("source_channel") in OUTBOUND_CHANNELS]
                else:
                    leads = [l for l in leads if l.get("source_channel") not in OUTBOUND_CHANNELS]

            # Adicionar source_type a cada lead
            for lead in leads:
                lead["source_type"] = get_source_type(lead.get("source_channel", ""))

            total = result.count if hasattr(result, 'count') else len(leads)

            return {
                "success": True,
                "data": {
                    "leads": leads,
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": total,
                        "pages": (total + limit - 1) // limit
                    }
                }
            }

        except Exception as e:
            logger.error(f"Error in manual leads query: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # API: Detalhe do Lead
    # =========================================================================

    def get_lead_detail(self, location_id: str, lead_id: str) -> Dict[str, Any]:
        """
        Obtém detalhes completos de um lead.

        Args:
            location_id: ID do tenant (para validação RLS)
            lead_id: ID do lead

        Returns:
            Dict com dados completos do lead
        """
        try:
            supabase = self._get_supabase_client()

            # Buscar lead
            lead = supabase.table("growth_leads").select("*").eq(
                "id", lead_id
            ).eq(
                "location_id", location_id
            ).execute()

            if not lead.data:
                return {"success": False, "error": "Lead not found"}

            lead_data = lead.data[0]
            lead_data["source_type"] = get_source_type(lead_data.get("source_channel", ""))

            # Buscar conversas do lead
            conversations = supabase.table("portal_conversations").select(
                "id, channel, status, last_message, last_message_at, total_messages"
            ).eq(
                "lead_id", lead_id
            ).order(
                "last_message_at", desc=True
            ).limit(5).execute()

            # Buscar atividades recentes
            activities = supabase.table("growth_activities").select(
                "id, activity_type, channel, direction, content, result, performed_at"
            ).eq(
                "lead_id", lead_id
            ).order(
                "performed_at", desc=True
            ).limit(10).execute()

            return {
                "success": True,
                "data": {
                    "lead": lead_data,
                    "conversations": conversations.data or [],
                    "activities": activities.data or []
                }
            }

        except Exception as e:
            logger.error(f"Error getting lead detail: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # API: Lista de Conversas
    # =========================================================================

    def get_conversations(
        self,
        location_id: str,
        page: int = 1,
        limit: int = 20,
        channel: str = None,
        status: str = None
    ) -> Dict[str, Any]:
        """
        Lista conversas do tenant.

        Args:
            location_id: ID do tenant
            page: Página atual
            limit: Itens por página
            channel: Filtrar por canal
            status: Filtrar por status (open, closed)

        Returns:
            Dict com conversas e paginação
        """
        try:
            supabase = self._get_supabase_client()
            offset = (page - 1) * limit

            # Query com join para dados do lead
            query = supabase.table("portal_conversations").select(
                "*, growth_leads(id, name, instagram_username, phone, funnel_stage, lead_temperature)",
                count="exact"
            ).eq("location_id", location_id)

            if channel:
                query = query.eq("channel", channel)

            if status:
                query = query.eq("status", status)

            query = query.order("last_message_at", desc=True).range(offset, offset + limit - 1)

            result = query.execute()
            total = result.count if hasattr(result, 'count') else len(result.data or [])

            return {
                "success": True,
                "data": {
                    "conversations": result.data or [],
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": total,
                        "pages": (total + limit - 1) // limit
                    }
                }
            }

        except Exception as e:
            logger.error(f"Error getting conversations: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # API: Mensagens de uma Conversa
    # =========================================================================

    def get_conversation_messages(
        self,
        location_id: str,
        conversation_id: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Obtém mensagens de uma conversa.

        Args:
            location_id: ID do tenant
            conversation_id: ID da conversa
            limit: Máximo de mensagens

        Returns:
            Dict com mensagens ordenadas
        """
        try:
            supabase = self._get_supabase_client()

            # Validar que conversa pertence ao tenant
            conv = supabase.table("portal_conversations").select("id").eq(
                "id", conversation_id
            ).eq(
                "location_id", location_id
            ).execute()

            if not conv.data:
                return {"success": False, "error": "Conversation not found"}

            # Buscar mensagens
            messages = supabase.table("portal_messages").select(
                "id, content, content_type, direction, sender_type, sender_name, is_from_ai, media_url, sent_at"
            ).eq(
                "conversation_id", conversation_id
            ).order(
                "sent_at", desc=False
            ).limit(limit).execute()

            # Marcar como lidas
            supabase.table("portal_conversations").update({
                "unread_count": 0
            }).eq("id", conversation_id).execute()

            return {
                "success": True,
                "data": {
                    "messages": messages.data or [],
                    "conversation_id": conversation_id
                }
            }

        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # TENANT: Obter ou criar tenant
    # =========================================================================

    def ensure_tenant_exists(self, location_id: str, client_name: str = None) -> Dict[str, Any]:
        """
        Garante que o tenant existe no growth_client_configs.
        Cria se não existir.

        Args:
            location_id: ID do GHL
            client_name: Nome do cliente (opcional)

        Returns:
            Dict com dados do tenant
        """
        try:
            supabase = self._get_supabase_client()

            # Verificar se existe
            existing = supabase.table("growth_client_configs").select("*").eq(
                "location_id", location_id
            ).execute()

            if existing.data:
                return {
                    "success": True,
                    "action": "found",
                    "tenant": existing.data[0]
                }

            # Criar novo tenant
            tenant_data = {
                "location_id": location_id,
                "client_name": client_name or f"Cliente {location_id[:8]}",
                "nome_empresa": client_name or "Empresa",
                "tipo_negocio": "Geral",
                "oferta_principal": "Serviço principal",
                "dor_principal": "Problema do cliente",
                "publico_alvo": "Público-alvo",
                "diferenciais": ["Diferencial 1"],
                "status": "active",
                "created_at": datetime.now().isoformat()
            }

            result = supabase.table("growth_client_configs").insert(tenant_data).execute()

            logger.info(f"Created tenant: {location_id}")

            return {
                "success": True,
                "action": "created",
                "tenant": result.data[0] if result.data else tenant_data
            }

        except Exception as e:
            logger.error(f"Error ensuring tenant: {e}")
            return {"success": False, "error": str(e)}


# Instância singleton para uso em outros módulos
portal_service = PortalService()
