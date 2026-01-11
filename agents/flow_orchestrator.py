"""
GROWTH OS - FLOW ORCHESTRATOR
Sistema de orquestração que gerencia transições entre agentes.

Responsabilidades:
    - Detectar gatilhos de handoff
    - Rotear leads para o agente correto
    - Manter contexto entre transições
    - Logar todas as transições
    - Alertar managers sobre eventos importantes
"""

import os
import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Callable, Any
from datetime import datetime
from enum import Enum
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flow_orchestrator")


# =============================================================================
# ENUMS E CONSTANTES
# =============================================================================

class AgentCode(Enum):
    """Códigos dos 19 agentes do Growth OS"""
    # Operacionais
    PROSPECTOR = "PROS-001"
    DATABASE_REACTIVATOR = "REAC-002"
    REFERRAL_GENERATOR = "REFR-003"
    SOCIAL_SELLER_IG = "SSIG-004"
    SOCIAL_SELLER_LI = "SSLI-005"
    SDR_INBOUND = "SDRI-006"
    SDR_OUTBOUND = "SDRO-007"
    COLD_CALLER = "CCAL-008"
    INBOUND_CALLER = "ICAL-009"
    COLD_EMAILER = "CEMA-010"
    OBJECTION_HANDLER = "OBJH-011"
    SCHEDULER = "SCHD-012"
    CONCIERGE = "CONC-013"
    CLOSER = "CLOS-014"

    # Gestão
    OUTBOUND_MANAGER = "OMGR-015"
    INBOUND_MANAGER = "IMGR-016"
    CLOSING_MANAGER = "CMGR-017"
    SALES_OPS = "SOPS-018"
    SALES_DIRECTOR = "SDIR-019"


class FunnelStage(Enum):
    """Estágios do funil de vendas"""
    PROSPECTED = "prospected"
    LEAD = "lead"
    QUALIFIED = "qualified"
    SCHEDULED = "scheduled"
    SHOWED = "showed"
    NO_SHOW = "no_show"
    PROPOSAL = "proposal"
    WON = "won"
    LOST = "lost"


class HandoffTrigger(Enum):
    """Gatilhos que causam handoff entre agentes"""
    # Sinais positivos
    SHOWED_INTEREST = "showed_interest"
    ASKED_PRICE = "asked_price"
    WANTS_TO_SCHEDULE = "wants_to_schedule"
    READY_TO_CLOSE = "ready_to_close"
    GAVE_REFERRAL = "gave_referral"

    # Sinais negativos
    HAS_OBJECTION = "has_objection"
    WENT_COLD = "went_cold"
    NO_SHOW = "no_show"
    LOST_DEAL = "lost_deal"

    # Sinais de processo
    BANT_COMPLETE = "bant_complete"
    MEETING_CONFIRMED = "meeting_confirmed"
    MEETING_HAPPENED = "meeting_happened"
    PROPOSAL_SENT = "proposal_sent"

    # Escalações
    VIP_LEAD = "vip_lead"
    COMPLEX_OBJECTION = "complex_objection"
    MANAGER_NEEDED = "manager_needed"


@dataclass
class HandoffContext:
    """Contexto passado durante um handoff"""
    lead_id: str
    lead_name: str
    lead_company: Optional[str]
    lead_channel: str  # instagram, linkedin, whatsapp, email, phone

    # Qualificação BANT
    bant_budget: Optional[int] = None  # 0-25
    bant_authority: Optional[int] = None
    bant_need: Optional[int] = None
    bant_timeline: Optional[int] = None

    # Contexto da conversa
    conversation_summary: str = ""
    last_message: str = ""
    lead_temperature: str = "warm"  # cold, warm, hot

    # Metadados
    previous_agents: List[str] = field(default_factory=list)
    handoff_reason: str = ""
    priority: str = "medium"  # low, medium, high, critical
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "lead_id": self.lead_id,
            "lead_name": self.lead_name,
            "lead_company": self.lead_company,
            "lead_channel": self.lead_channel,
            "bant": {
                "budget": self.bant_budget,
                "authority": self.bant_authority,
                "need": self.bant_need,
                "timeline": self.bant_timeline,
                "total": sum(filter(None, [
                    self.bant_budget,
                    self.bant_authority,
                    self.bant_need,
                    self.bant_timeline
                ]))
            },
            "conversation_summary": self.conversation_summary,
            "last_message": self.last_message,
            "lead_temperature": self.lead_temperature,
            "previous_agents": self.previous_agents,
            "handoff_reason": self.handoff_reason,
            "priority": self.priority,
            "notes": self.notes
        }


@dataclass
class HandoffRule:
    """Regra de handoff entre agentes"""
    from_agent: AgentCode
    to_agent: AgentCode
    trigger: HandoffTrigger
    conditions: List[Callable[[HandoffContext], bool]] = field(default_factory=list)
    priority: int = 5  # 1-10, maior = mais prioritário
    description: str = ""

    def matches(self, context: HandoffContext) -> bool:
        """Verifica se a regra deve ser aplicada"""
        if not self.conditions:
            return True
        return all(condition(context) for condition in self.conditions)


@dataclass
class HandoffEvent:
    """Evento de handoff registrado"""
    event_id: str
    timestamp: datetime
    from_agent: str
    to_agent: str
    trigger: str
    context: HandoffContext
    success: bool
    error_message: Optional[str] = None


# =============================================================================
# REGRAS DE HANDOFF
# =============================================================================

# Funções auxiliares para condições
def is_hot_lead(ctx: HandoffContext) -> bool:
    return ctx.lead_temperature == "hot"

def is_decision_maker(ctx: HandoffContext) -> bool:
    return ctx.bant_authority and ctx.bant_authority >= 20

def bant_complete(ctx: HandoffContext) -> bool:
    return all([ctx.bant_budget, ctx.bant_authority, ctx.bant_need, ctx.bant_timeline])

def high_priority(ctx: HandoffContext) -> bool:
    return ctx.priority in ["high", "critical"]

def is_vip(ctx: HandoffContext) -> bool:
    return ctx.priority == "critical"


# Definição das regras de handoff
HANDOFF_RULES: List[HandoffRule] = [

    # ===== PROSPECTOR (PROS-001) =====
    HandoffRule(
        from_agent=AgentCode.PROSPECTOR,
        to_agent=AgentCode.SOCIAL_SELLER_IG,
        trigger=HandoffTrigger.SHOWED_INTEREST,
        conditions=[lambda ctx: ctx.lead_channel == "instagram"],
        priority=7,
        description="Lead do IG demonstrou interesse → Social Seller IG"
    ),
    HandoffRule(
        from_agent=AgentCode.PROSPECTOR,
        to_agent=AgentCode.SOCIAL_SELLER_LI,
        trigger=HandoffTrigger.SHOWED_INTEREST,
        conditions=[lambda ctx: ctx.lead_channel == "linkedin"],
        priority=7,
        description="Lead do LI demonstrou interesse → Social Seller LI"
    ),
    HandoffRule(
        from_agent=AgentCode.PROSPECTOR,
        to_agent=AgentCode.SDR_OUTBOUND,
        trigger=HandoffTrigger.ASKED_PRICE,
        priority=8,
        description="Lead pediu preço → SDR Outbound para qualificar"
    ),

    # ===== SOCIAL SELLER IG (SSIG-004) =====
    HandoffRule(
        from_agent=AgentCode.SOCIAL_SELLER_IG,
        to_agent=AgentCode.SDR_INBOUND,
        trigger=HandoffTrigger.BANT_COMPLETE,
        priority=8,
        description="BANT completo via IG → SDR Inbound"
    ),
    HandoffRule(
        from_agent=AgentCode.SOCIAL_SELLER_IG,
        to_agent=AgentCode.SCHEDULER,
        trigger=HandoffTrigger.WANTS_TO_SCHEDULE,
        priority=9,
        description="Lead quer agendar → Scheduler"
    ),
    HandoffRule(
        from_agent=AgentCode.SOCIAL_SELLER_IG,
        to_agent=AgentCode.OBJECTION_HANDLER,
        trigger=HandoffTrigger.HAS_OBJECTION,
        priority=7,
        description="Lead tem objeção → Objection Handler"
    ),

    # ===== SDR INBOUND (SDRI-006) =====
    HandoffRule(
        from_agent=AgentCode.SDR_INBOUND,
        to_agent=AgentCode.SCHEDULER,
        trigger=HandoffTrigger.BANT_COMPLETE,
        conditions=[bant_complete],
        priority=8,
        description="Lead qualificado → Scheduler"
    ),
    HandoffRule(
        from_agent=AgentCode.SDR_INBOUND,
        to_agent=AgentCode.CLOSER,
        trigger=HandoffTrigger.READY_TO_CLOSE,
        conditions=[is_hot_lead, is_decision_maker],
        priority=10,
        description="Lead hot e decisor → Closer direto"
    ),
    HandoffRule(
        from_agent=AgentCode.SDR_INBOUND,
        to_agent=AgentCode.OBJECTION_HANDLER,
        trigger=HandoffTrigger.HAS_OBJECTION,
        priority=7,
        description="Lead com objeção → Objection Handler"
    ),

    # ===== SDR OUTBOUND (SDRO-007) =====
    HandoffRule(
        from_agent=AgentCode.SDR_OUTBOUND,
        to_agent=AgentCode.COLD_CALLER,
        trigger=HandoffTrigger.SHOWED_INTEREST,
        conditions=[lambda ctx: "ligar" in ctx.last_message.lower() or "call" in ctx.last_message.lower()],
        priority=8,
        description="Lead quer ligação → Cold Caller"
    ),
    HandoffRule(
        from_agent=AgentCode.SDR_OUTBOUND,
        to_agent=AgentCode.SCHEDULER,
        trigger=HandoffTrigger.WANTS_TO_SCHEDULE,
        priority=9,
        description="Lead quer agendar → Scheduler"
    ),

    # ===== COLD CALLER (CCAL-008) =====
    HandoffRule(
        from_agent=AgentCode.COLD_CALLER,
        to_agent=AgentCode.SCHEDULER,
        trigger=HandoffTrigger.WANTS_TO_SCHEDULE,
        priority=9,
        description="Lead quer agendar pós-call → Scheduler"
    ),
    HandoffRule(
        from_agent=AgentCode.COLD_CALLER,
        to_agent=AgentCode.CLOSER,
        trigger=HandoffTrigger.READY_TO_CLOSE,
        conditions=[is_hot_lead],
        priority=10,
        description="Lead pronto para fechar → Closer"
    ),

    # ===== SCHEDULER (SCHD-012) =====
    HandoffRule(
        from_agent=AgentCode.SCHEDULER,
        to_agent=AgentCode.CONCIERGE,
        trigger=HandoffTrigger.MEETING_CONFIRMED,
        priority=7,
        description="Reunião confirmada → Concierge prepara"
    ),
    HandoffRule(
        from_agent=AgentCode.SCHEDULER,
        to_agent=AgentCode.DATABASE_REACTIVATOR,
        trigger=HandoffTrigger.NO_SHOW,
        priority=6,
        description="No-show → Reativador"
    ),

    # ===== CONCIERGE (CONC-013) =====
    HandoffRule(
        from_agent=AgentCode.CONCIERGE,
        to_agent=AgentCode.CLOSER,
        trigger=HandoffTrigger.MEETING_HAPPENED,
        priority=10,
        description="Reunião aconteceu → Closer assume"
    ),

    # ===== CLOSER (CLOS-014) =====
    HandoffRule(
        from_agent=AgentCode.CLOSER,
        to_agent=AgentCode.OBJECTION_HANDLER,
        trigger=HandoffTrigger.COMPLEX_OBJECTION,
        priority=8,
        description="Objeção complexa → Objection Handler ajuda"
    ),
    HandoffRule(
        from_agent=AgentCode.CLOSER,
        to_agent=AgentCode.REFERRAL_GENERATOR,
        trigger=HandoffTrigger.GAVE_REFERRAL,
        conditions=[lambda ctx: ctx.lead_temperature == "hot"],
        priority=7,
        description="Fechou e pode indicar → Referral Generator"
    ),
    HandoffRule(
        from_agent=AgentCode.CLOSER,
        to_agent=AgentCode.CLOSING_MANAGER,
        trigger=HandoffTrigger.MANAGER_NEEDED,
        conditions=[is_vip],
        priority=10,
        description="Deal VIP precisa de manager → Closing Manager"
    ),

    # ===== OBJECTION HANDLER (OBJH-011) =====
    HandoffRule(
        from_agent=AgentCode.OBJECTION_HANDLER,
        to_agent=AgentCode.CLOSER,
        trigger=HandoffTrigger.READY_TO_CLOSE,
        priority=9,
        description="Objeção superada → Volta pro Closer"
    ),
    HandoffRule(
        from_agent=AgentCode.OBJECTION_HANDLER,
        to_agent=AgentCode.SCHEDULER,
        trigger=HandoffTrigger.WANTS_TO_SCHEDULE,
        priority=8,
        description="Superou objeção e quer agendar → Scheduler"
    ),

    # ===== DATABASE REACTIVATOR (REAC-002) =====
    HandoffRule(
        from_agent=AgentCode.DATABASE_REACTIVATOR,
        to_agent=AgentCode.SDR_INBOUND,
        trigger=HandoffTrigger.SHOWED_INTEREST,
        priority=8,
        description="Lead reativado → SDR Inbound qualifica"
    ),
    HandoffRule(
        from_agent=AgentCode.DATABASE_REACTIVATOR,
        to_agent=AgentCode.OBJECTION_HANDLER,
        trigger=HandoffTrigger.HAS_OBJECTION,
        priority=7,
        description="Lead reativado com objeção → Objection Handler"
    ),

    # ===== ESCALAÇÕES PARA MANAGERS =====
    HandoffRule(
        from_agent=AgentCode.PROSPECTOR,
        to_agent=AgentCode.OUTBOUND_MANAGER,
        trigger=HandoffTrigger.VIP_LEAD,
        conditions=[is_vip],
        priority=10,
        description="Lead VIP identificado → Outbound Manager"
    ),
    HandoffRule(
        from_agent=AgentCode.SDR_INBOUND,
        to_agent=AgentCode.INBOUND_MANAGER,
        trigger=HandoffTrigger.MANAGER_NEEDED,
        priority=9,
        description="SDR precisa de suporte → Inbound Manager"
    ),
    HandoffRule(
        from_agent=AgentCode.CLOSER,
        to_agent=AgentCode.SALES_DIRECTOR,
        trigger=HandoffTrigger.VIP_LEAD,
        conditions=[is_vip, lambda ctx: ctx.bant_budget and ctx.bant_budget >= 20],
        priority=10,
        description="Deal VIP alto valor → Sales Director"
    ),
]


# =============================================================================
# ORQUESTRADOR PRINCIPAL
# =============================================================================

class FlowOrchestrator:
    """Orquestrador de fluxos entre agentes"""

    def __init__(
        self,
        rules: List[HandoffRule] = None,
        on_handoff: Callable[[HandoffEvent], None] = None,
        on_error: Callable[[Exception, HandoffContext], None] = None
    ):
        self.rules = rules or HANDOFF_RULES
        self.on_handoff = on_handoff
        self.on_error = on_error
        self.event_log: List[HandoffEvent] = []

    def find_next_agent(
        self,
        current_agent: AgentCode,
        trigger: HandoffTrigger,
        context: HandoffContext
    ) -> Optional[AgentCode]:
        """
        Encontra o próximo agente baseado no gatilho e contexto.

        Args:
            current_agent: Agente atual
            trigger: Gatilho que causou o handoff
            context: Contexto do lead

        Returns:
            Código do próximo agente ou None se não houver match
        """
        matching_rules = []

        for rule in self.rules:
            if rule.from_agent == current_agent and rule.trigger == trigger:
                if rule.matches(context):
                    matching_rules.append(rule)

        if not matching_rules:
            logger.warning(
                f"Nenhuma regra encontrada para handoff: "
                f"{current_agent.value} + {trigger.value}"
            )
            return None

        # Ordena por prioridade (maior primeiro)
        matching_rules.sort(key=lambda r: r.priority, reverse=True)
        selected_rule = matching_rules[0]

        logger.info(
            f"Handoff selecionado: {selected_rule.from_agent.value} → "
            f"{selected_rule.to_agent.value} ({selected_rule.description})"
        )

        return selected_rule.to_agent

    def execute_handoff(
        self,
        current_agent: AgentCode,
        trigger: HandoffTrigger,
        context: HandoffContext,
        agent_registry: Dict[str, Any] = None
    ) -> HandoffEvent:
        """
        Executa um handoff completo entre agentes.

        Args:
            current_agent: Agente atual
            trigger: Gatilho do handoff
            context: Contexto do lead
            agent_registry: Registro de agentes (para invocar)

        Returns:
            Evento de handoff com resultado
        """
        event_id = f"hoff_{datetime.now().strftime('%Y%m%d%H%M%S')}_{context.lead_id[:8]}"

        try:
            # Encontra próximo agente
            next_agent = self.find_next_agent(current_agent, trigger, context)

            if not next_agent:
                raise ValueError(f"Nenhum agente encontrado para handoff")

            # Atualiza contexto
            context.previous_agents.append(current_agent.value)
            context.handoff_reason = trigger.value

            # Cria evento
            event = HandoffEvent(
                event_id=event_id,
                timestamp=datetime.now(),
                from_agent=current_agent.value,
                to_agent=next_agent.value,
                trigger=trigger.value,
                context=context,
                success=True
            )

            # Invoca callback se existir
            if self.on_handoff:
                self.on_handoff(event)

            # Registra evento
            self.event_log.append(event)

            # Se tiver registry, pode invocar o próximo agente
            if agent_registry and next_agent.value in agent_registry:
                agent = agent_registry[next_agent.value]
                # agent.receive_handoff(context)

            logger.info(f"Handoff executado com sucesso: {event_id}")
            return event

        except Exception as e:
            logger.error(f"Erro no handoff: {str(e)}")

            event = HandoffEvent(
                event_id=event_id,
                timestamp=datetime.now(),
                from_agent=current_agent.value,
                to_agent="ERROR",
                trigger=trigger.value,
                context=context,
                success=False,
                error_message=str(e)
            )

            if self.on_error:
                self.on_error(e, context)

            self.event_log.append(event)
            return event

    def get_possible_handoffs(
        self,
        current_agent: AgentCode
    ) -> List[Dict]:
        """
        Lista todos os handoffs possíveis a partir de um agente.

        Args:
            current_agent: Agente atual

        Returns:
            Lista de handoffs possíveis com triggers
        """
        possible = []
        for rule in self.rules:
            if rule.from_agent == current_agent:
                possible.append({
                    "to_agent": rule.to_agent.value,
                    "trigger": rule.trigger.value,
                    "description": rule.description,
                    "priority": rule.priority
                })
        return sorted(possible, key=lambda x: x["priority"], reverse=True)

    def analyze_lead_journey(
        self,
        lead_id: str
    ) -> List[HandoffEvent]:
        """
        Analisa a jornada de um lead através dos agentes.

        Args:
            lead_id: ID do lead

        Returns:
            Lista de eventos de handoff do lead
        """
        return [
            event for event in self.event_log
            if event.context.lead_id == lead_id
        ]

    def get_bottleneck_analysis(self) -> Dict:
        """
        Analisa gargalos no fluxo de handoffs.

        Returns:
            Análise de gargalos por agente
        """
        agent_stats = {}

        for event in self.event_log:
            from_agent = event.from_agent

            if from_agent not in agent_stats:
                agent_stats[from_agent] = {
                    "total_handoffs": 0,
                    "successful": 0,
                    "failed": 0,
                    "to_agents": {}
                }

            agent_stats[from_agent]["total_handoffs"] += 1

            if event.success:
                agent_stats[from_agent]["successful"] += 1
                to_agent = event.to_agent
                agent_stats[from_agent]["to_agents"][to_agent] = \
                    agent_stats[from_agent]["to_agents"].get(to_agent, 0) + 1
            else:
                agent_stats[from_agent]["failed"] += 1

        return agent_stats

    def export_to_json(self, filepath: str):
        """Exporta log de eventos para JSON"""
        data = [
            {
                "event_id": e.event_id,
                "timestamp": e.timestamp.isoformat(),
                "from_agent": e.from_agent,
                "to_agent": e.to_agent,
                "trigger": e.trigger,
                "context": e.context.to_dict(),
                "success": e.success,
                "error": e.error_message
            }
            for e in self.event_log
        ]

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Log exportado para {filepath}")


# =============================================================================
# DETECTOR DE TRIGGERS
# =============================================================================

class TriggerDetector:
    """
    Detecta gatilhos de handoff baseado na mensagem e contexto.

    Usa pattern matching e pode ser estendido com ML/LLM.
    """

    # Padrões de texto para cada trigger
    PATTERNS = {
        HandoffTrigger.SHOWED_INTEREST: [
            r"quero saber mais",
            r"me interessei",
            r"gostei",
            r"interessante",
            r"como funciona",
            r"me conta mais"
        ],
        HandoffTrigger.ASKED_PRICE: [
            r"quanto custa",
            r"qual o valor",
            r"preço",
            r"investimento",
            r"quanto é"
        ],
        HandoffTrigger.WANTS_TO_SCHEDULE: [
            r"vamos marcar",
            r"pode agendar",
            r"quando posso",
            r"tenho disponibilidade",
            r"prefiro horário"
        ],
        HandoffTrigger.HAS_OBJECTION: [
            r"tá caro",
            r"não tenho orçamento",
            r"preciso pensar",
            r"não é o momento",
            r"já uso",
            r"concorrente"
        ],
        HandoffTrigger.WENT_COLD: [
            r"depois te respondo",
            r"não sei",
            r"deixa pra lá"
        ],
        HandoffTrigger.READY_TO_CLOSE: [
            r"vamos fechar",
            r"como faço pra contratar",
            r"quero começar",
            r"aceito",
            r"fechado"
        ]
    }

    @classmethod
    def detect(cls, message: str, context: HandoffContext) -> Optional[HandoffTrigger]:
        """
        Detecta trigger baseado na mensagem.

        Args:
            message: Última mensagem do lead
            context: Contexto atual

        Returns:
            Trigger detectado ou None
        """
        import re

        message_lower = message.lower()

        # Verifica cada padrão
        for trigger, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    logger.info(f"Trigger detectado: {trigger.value} (padrão: {pattern})")
                    return trigger

        return None

    @classmethod
    def detect_with_llm(
        cls,
        message: str,
        context: HandoffContext,
        llm_callable: Callable[[str], str]
    ) -> Optional[HandoffTrigger]:
        """
        Detecta trigger usando LLM para casos ambíguos.

        Args:
            message: Mensagem do lead
            context: Contexto
            llm_callable: Função que chama LLM

        Returns:
            Trigger detectado
        """
        prompt = f"""Analise a mensagem do lead e determine qual trigger de handoff deve ser acionado.

Mensagem do lead: "{message}"

Contexto:
- Lead: {context.lead_name} ({context.lead_company})
- Temperatura: {context.lead_temperature}
- Último agente: {context.previous_agents[-1] if context.previous_agents else 'Nenhum'}

Triggers possíveis:
- SHOWED_INTEREST: Lead demonstrou interesse genuíno
- ASKED_PRICE: Lead perguntou sobre preço/valores
- WANTS_TO_SCHEDULE: Lead quer agendar reunião/call
- HAS_OBJECTION: Lead tem objeção específica
- WENT_COLD: Lead esfriou/perdeu interesse
- READY_TO_CLOSE: Lead está pronto para fechar
- VIP_LEAD: Lead é de empresa grande/importante
- None: Nenhum trigger claro

Responda APENAS com o nome do trigger ou "None".
"""
        response = llm_callable(prompt).strip().upper()

        # Tenta converter para enum
        try:
            return HandoffTrigger[response]
        except KeyError:
            return None


# =============================================================================
# INTEGRAÇÃO COM N8N / SUPABASE
# =============================================================================

class GrowthOSIntegration:
    """
    Integração com infraestrutura existente (n8n, Supabase, GHL).
    """

    def __init__(
        self,
        supabase_url: str = None,
        supabase_key: str = None,
        n8n_webhook_url: str = None
    ):
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.n8n_webhook_url = n8n_webhook_url or os.getenv("N8N_HANDOFF_WEBHOOK")

    def log_handoff_to_supabase(self, event: HandoffEvent):
        """
        Registra handoff na tabela growth_activities.

        Em produção, usar supabase-py:
        ```python
        from supabase import create_client

        supabase = create_client(self.supabase_url, self.supabase_key)
        supabase.table("growth_activities").insert({
            "lead_id": event.context.lead_id,
            "activity_type": "agent_handoff",
            "agent_code": event.to_agent,
            "details": event.context.to_dict(),
            "created_at": event.timestamp.isoformat()
        }).execute()
        ```
        """
        logger.info(f"[Supabase] Logging handoff: {event.event_id}")

    def notify_manager_via_n8n(self, event: HandoffEvent):
        """
        Notifica manager via webhook n8n.

        Em produção:
        ```python
        import requests

        requests.post(self.n8n_webhook_url, json={
            "event_type": "handoff",
            "event_id": event.event_id,
            "from_agent": event.from_agent,
            "to_agent": event.to_agent,
            "lead_id": event.context.lead_id,
            "priority": event.context.priority
        })
        ```
        """
        logger.info(f"[n8n] Notificando sobre handoff: {event.event_id}")

    def update_lead_stage_in_ghl(
        self,
        lead_id: str,
        new_stage: FunnelStage,
        agent_code: str
    ):
        """
        Atualiza estágio do lead no GoHighLevel.

        Precisa de integração com GHL API.
        """
        logger.info(f"[GHL] Atualizando lead {lead_id} para estágio {new_stage.value}")


# =============================================================================
# CLI / MAIN
# =============================================================================

def main():
    """Ponto de entrada CLI para teste"""
    import argparse

    parser = argparse.ArgumentParser(description="Growth OS Flow Orchestrator")
    parser.add_argument(
        "--agent",
        type=str,
        help="Código do agente atual"
    )
    parser.add_argument(
        "--list-rules",
        action="store_true",
        help="Lista todas as regras de handoff"
    )
    parser.add_argument(
        "--show-possible",
        action="store_true",
        help="Mostra handoffs possíveis a partir de um agente"
    )

    args = parser.parse_args()

    orchestrator = FlowOrchestrator()

    if args.list_rules:
        print("\n=== REGRAS DE HANDOFF ===\n")
        for rule in HANDOFF_RULES:
            print(f"{rule.from_agent.value} → {rule.to_agent.value}")
            print(f"  Trigger: {rule.trigger.value}")
            print(f"  Prioridade: {rule.priority}")
            print(f"  Descrição: {rule.description}")
            print()
        return

    if args.show_possible and args.agent:
        try:
            agent_code = AgentCode(args.agent)
            possible = orchestrator.get_possible_handoffs(agent_code)

            print(f"\n=== HANDOFFS POSSÍVEIS A PARTIR DE {args.agent} ===\n")
            for h in possible:
                print(f"→ {h['to_agent']}")
                print(f"  Trigger: {h['trigger']}")
                print(f"  {h['description']}")
                print()
        except ValueError:
            print(f"Agente '{args.agent}' não encontrado.")
            print("Agentes válidos:")
            for a in AgentCode:
                print(f"  - {a.value}")
        return

    # Demo de handoff
    print("\n=== DEMO: HANDOFF ===\n")

    # Cria contexto de exemplo
    context = HandoffContext(
        lead_id="lead_12345",
        lead_name="Paula Mendes",
        lead_company="Clínica Bella Vita",
        lead_channel="instagram",
        bant_budget=20,
        bant_authority=25,
        bant_need=20,
        bant_timeline=15,
        conversation_summary="Lead interessada em marketing para clínica de estética",
        last_message="Quero saber mais sobre como vocês podem ajudar",
        lead_temperature="warm"
    )

    # Executa handoff
    event = orchestrator.execute_handoff(
        current_agent=AgentCode.SOCIAL_SELLER_IG,
        trigger=HandoffTrigger.BANT_COMPLETE,
        context=context
    )

    print(f"Resultado: {'SUCESSO' if event.success else 'ERRO'}")
    print(f"De: {event.from_agent}")
    print(f"Para: {event.to_agent}")
    print(f"Trigger: {event.trigger}")


if __name__ == "__main__":
    main()
