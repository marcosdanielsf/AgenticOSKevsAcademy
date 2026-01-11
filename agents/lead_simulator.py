"""
GROWTH OS - LEAD SIMULATOR
Sistema de teste onde Claude simula ser um lead para testar agentes de vendas.

Uso:
    python lead_simulator.py --persona hot_buyer --agent SSIG-004

Funcionalidades:
    - Múltiplas personas de leads (hot, warm, cold, objector, etc)
    - Histórico de conversa
    - Avaliação automática do agente
    - Métricas de qualidade
"""

import os
import json
import random
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class PersonaType(Enum):
    """Tipos de persona de lead simulado"""
    HOT_BUYER = "hot_buyer"           # Quer comprar agora
    WARM_CURIOUS = "warm_curious"      # Interessado mas explorando
    COLD_SKEPTIC = "cold_skeptic"      # Desconfiado, precisa convencer
    PRICE_OBJECTOR = "price_objector"  # Objeção de preço
    TIME_OBJECTOR = "time_objector"    # "Não é o momento"
    BUSY_EXECUTIVE = "busy_executive"  # Pouco tempo, precisa ser direto
    RESEARCHER = "researcher"          # Só pesquisando, sem urgência
    COMPETITOR_USER = "competitor_user" # Já usa concorrente
    GHOSTING = "ghosting"              # Responde pouco, some
    VIP_ENTERPRISE = "vip_enterprise"  # Grande empresa, deal complexo


@dataclass
class LeadPersona:
    """Persona de um lead simulado"""
    type: PersonaType
    name: str
    company: str
    role: str
    industry: str
    pain_level: int  # 1-10
    budget_available: bool
    is_decision_maker: bool
    timeline_urgency: int  # 1-10

    # Comportamentos
    response_style: str  # "short", "medium", "verbose"
    objections: List[str] = field(default_factory=list)
    hidden_concerns: List[str] = field(default_factory=list)
    trigger_words: List[str] = field(default_factory=list)  # Palavras que fazem ele engajar mais

    # Estado
    engagement_level: int = 5  # 1-10, muda durante conversa
    trust_level: int = 5  # 1-10
    ready_to_buy: bool = False

    def to_system_prompt(self) -> str:
        """Gera system prompt para Claude simular esta persona"""
        return f"""### VOCÊ É UM LEAD SIMULADO ###

Você está simulando um potencial cliente para testar um agente de vendas.
Responda como se fosse uma pessoa REAL interessada (ou não) em comprar.

### SUA IDENTIDADE ###
- Nome: {self.name}
- Empresa: {self.company}
- Cargo: {self.role}
- Segmento: {self.industry}

### SEU PERFIL ###
- Nível de dor: {self.pain_level}/10
- Tem budget: {"Sim" if self.budget_available else "Não ou não sabe"}
- É decisor: {"Sim" if self.is_decision_maker else "Precisa consultar outros"}
- Urgência: {self.timeline_urgency}/10

### SEU COMPORTAMENTO ###
- Estilo de resposta: {self.response_style}
- Suas objeções típicas: {', '.join(self.objections) if self.objections else 'Nenhuma específica'}
- Preocupações escondidas: {', '.join(self.hidden_concerns) if self.hidden_concerns else 'Nenhuma'}
- Palavras que te fazem engajar: {', '.join(self.trigger_words) if self.trigger_words else 'Nenhuma específica'}

### REGRAS DE SIMULAÇÃO ###
1. Responda de forma REALISTA, como uma pessoa de verdade responderia
2. NÃO seja perfeito - pessoas reais têm dúvidas, resistências, distrações
3. Se o agente fizer algo bom, engaje mais (aumente engagement_level mentalmente)
4. Se o agente for muito agressivo ou genérico, esfrie
5. Use linguagem natural do seu perfil (executivo fala diferente de empreendedor)
6. Você pode ghost (parar de responder) se o agente for muito ruim
7. Sua objeção principal vai aparecer em algum momento

### O QUE VOCÊ QUER ###
{"Você quer resolver sua dor e está disposto a comprar se fizer sentido" if self.pain_level >= 7 else "Você está explorando opções, sem pressa de decidir" if self.pain_level >= 4 else "Você está só curioso, não tem intenção real de comprar agora"}

### FORMATO DE RESPOSTA ###
Responda APENAS como o lead responderia.
Seja breve se seu estilo é "short", moderado se "medium", detalhado se "verbose".
Não inclua metadados ou explicações - apenas a resposta do lead.
"""


# =============================================================================
# BIBLIOTECA DE PERSONAS PRÉ-DEFINIDAS
# =============================================================================

PERSONA_LIBRARY: Dict[PersonaType, LeadPersona] = {

    PersonaType.HOT_BUYER: LeadPersona(
        type=PersonaType.HOT_BUYER,
        name="Paula Mendes",
        company="Clínica Bella Vita",
        role="Proprietária",
        industry="Estética",
        pain_level=9,
        budget_available=True,
        is_decision_maker=True,
        timeline_urgency=9,
        response_style="medium",
        objections=["Preciso entender melhor como funciona"],
        hidden_concerns=["Já fui enganada por marketing antes"],
        trigger_words=["resultado", "garantia", "outros clientes", "caso de sucesso"]
    ),

    PersonaType.WARM_CURIOUS: LeadPersona(
        type=PersonaType.WARM_CURIOUS,
        name="Roberto Silva",
        company="Consultório Dr. Roberto",
        role="Médico e Proprietário",
        industry="Medicina",
        pain_level=6,
        budget_available=True,
        is_decision_maker=True,
        timeline_urgency=4,
        response_style="short",
        objections=["Preciso pensar melhor", "Vou analisar"],
        hidden_concerns=["Não sei se marketing funciona pra médico"],
        trigger_words=["ética médica", "pacientes", "resultado mensurável"]
    ),

    PersonaType.COLD_SKEPTIC: LeadPersona(
        type=PersonaType.COLD_SKEPTIC,
        name="Fernanda Costa",
        company="FC Pilates",
        role="Fundadora",
        industry="Fitness",
        pain_level=5,
        budget_available=False,
        is_decision_maker=True,
        timeline_urgency=2,
        response_style="short",
        objections=["Já tentei isso e não funcionou", "Marketing não funciona pra mim"],
        hidden_concerns=["Tenho medo de gastar e não ter retorno"],
        trigger_words=["sem risco", "comprovado", "piloto", "teste"]
    ),

    PersonaType.PRICE_OBJECTOR: LeadPersona(
        type=PersonaType.PRICE_OBJECTOR,
        name="Carlos Eduardo",
        company="Clínica Derma+",
        role="Diretor Comercial",
        industry="Dermatologia",
        pain_level=7,
        budget_available=True,  # Tem, mas vai usar como objeção
        is_decision_maker=False,  # Precisa aprovar com sócio
        timeline_urgency=6,
        response_style="medium",
        objections=["Tá muito caro", "Vi opções mais baratas", "Não tenho esse orçamento"],
        hidden_concerns=["O sócio é conservador com gastos"],
        trigger_words=["ROI", "retorno", "pagamento", "parcela", "investimento vs custo"]
    ),

    PersonaType.TIME_OBJECTOR: LeadPersona(
        type=PersonaType.TIME_OBJECTOR,
        name="Ana Beatriz",
        company="AB Odonto",
        role="Dentista e Proprietária",
        industry="Odontologia",
        pain_level=8,
        budget_available=True,
        is_decision_maker=True,
        timeline_urgency=3,
        response_style="short",
        objections=["Não é o momento", "Vamos começar ano que vem", "Estou focada em outra coisa"],
        hidden_concerns=["Tenho medo de não conseguir acompanhar"],
        trigger_words=["simples", "não toma tempo", "a gente cuida de tudo"]
    ),

    PersonaType.BUSY_EXECUTIVE: LeadPersona(
        type=PersonaType.BUSY_EXECUTIVE,
        name="Marcos Andrade",
        company="Rede Saúde Plus",
        role="CEO",
        industry="Healthcare",
        pain_level=7,
        budget_available=True,
        is_decision_maker=True,
        timeline_urgency=8,
        response_style="short",
        objections=["Não tenho tempo pra isso", "Me manda um resumo"],
        hidden_concerns=["Não quero microgerenciar mais um fornecedor"],
        trigger_words=["rápido", "objetivo", "resultados", "delegável"]
    ),

    PersonaType.RESEARCHER: LeadPersona(
        type=PersonaType.RESEARCHER,
        name="Juliana Ferreira",
        company="Espaço Bem-Estar",
        role="Gerente",
        industry="Wellness",
        pain_level=4,
        budget_available=False,
        is_decision_maker=False,
        timeline_urgency=1,
        response_style="verbose",
        objections=["Só estou pesquisando", "Preciso comparar com outras opções"],
        hidden_concerns=["Minha chefe que decide, só estou levantando opções"],
        trigger_words=["material", "case study", "comparativo"]
    ),

    PersonaType.COMPETITOR_USER: LeadPersona(
        type=PersonaType.COMPETITOR_USER,
        name="Ricardo Gomes",
        company="RG Fisioterapia",
        role="Proprietário",
        industry="Fisioterapia",
        pain_level=5,
        budget_available=True,
        is_decision_maker=True,
        timeline_urgency=3,
        response_style="medium",
        objections=["Já uso [concorrente]", "O que vocês fazem de diferente?"],
        hidden_concerns=["Estou insatisfeito mas dá trabalho trocar"],
        trigger_words=["diferente", "melhor", "migração", "suporte"]
    ),

    PersonaType.GHOSTING: LeadPersona(
        type=PersonaType.GHOSTING,
        name="Patricia Lima",
        company="Clínica Harmonia",
        role="Administradora",
        industry="Psicologia",
        pain_level=6,
        budget_available=True,
        is_decision_maker=False,
        timeline_urgency=4,
        response_style="short",
        objections=[],  # Não objeta, só some
        hidden_concerns=["Não sou a decisora, estou só sondando"],
        trigger_words=[]
    ),

    PersonaType.VIP_ENTERPRISE: LeadPersona(
        type=PersonaType.VIP_ENTERPRISE,
        name="Dr. Henrique Matos",
        company="Rede Hospital Central",
        role="Diretor de Marketing",
        industry="Hospitais",
        pain_level=8,
        budget_available=True,
        is_decision_maker=False,  # Precisa de board approval
        timeline_urgency=5,
        response_style="medium",
        objections=["Precisa passar pelo jurídico", "Temos um processo de aprovação"],
        hidden_concerns=["Se der errado, meu emprego tá em risco"],
        trigger_words=["enterprise", "compliance", "segurança", "caso similar", "referência"]
    ),
}


@dataclass
class ConversationTurn:
    """Um turno de conversa"""
    role: str  # "agent" ou "lead"
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)


@dataclass
class SimulationSession:
    """Sessão completa de simulação"""
    session_id: str
    agent_code: str
    persona: LeadPersona
    conversation: List[ConversationTurn] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    outcome: Optional[str] = None  # "scheduled", "qualified", "lost", "ghosted"

    # Métricas de avaliação
    agent_score: Optional[int] = None  # 1-100
    evaluation_notes: List[str] = field(default_factory=list)

    def add_turn(self, role: str, message: str, metadata: Dict = None):
        """Adiciona um turno à conversa"""
        self.conversation.append(ConversationTurn(
            role=role,
            message=message,
            metadata=metadata or {}
        ))

    def get_conversation_history(self) -> str:
        """Retorna histórico formatado"""
        lines = []
        for turn in self.conversation:
            prefix = "AGENTE:" if turn.role == "agent" else "LEAD:"
            lines.append(f"{prefix} {turn.message}")
        return "\n\n".join(lines)

    def to_evaluation_prompt(self) -> str:
        """Gera prompt para Claude avaliar a performance do agente"""
        return f"""### AVALIE A PERFORMANCE DO AGENTE ###

Você é um especialista em vendas avaliando a performance de um agente de IA.

### CONTEXTO ###
- Agente testado: {self.agent_code}
- Tipo de lead simulado: {self.persona.type.value}
- Perfil do lead: {self.persona.name}, {self.persona.role} na {self.persona.company}
- Dor do lead: {self.persona.pain_level}/10
- Urgência: {self.persona.timeline_urgency}/10

### CONVERSA COMPLETA ###
{self.get_conversation_history()}

### CRITÉRIOS DE AVALIAÇÃO ###

1. **Rapport e Conexão (0-20 pontos)**
   - O agente criou conexão genuína?
   - Usou nome e contexto do lead?
   - Tom adequado?

2. **Descoberta e Qualificação (0-25 pontos)**
   - Fez perguntas abertas?
   - Descobriu a dor real?
   - Qualificou BANT?

3. **Tratamento de Objeções (0-20 pontos)**
   - Identificou objeções?
   - Tratou de forma adequada?
   - Não foi agressivo?

4. **Avanço do Funil (0-20 pontos)**
   - Conseguiu avançar a conversa?
   - Propôs próximo passo?
   - Fechou com call-to-action?

5. **Comunicação (0-15 pontos)**
   - Mensagens curtas e claras?
   - Sem erros ou confusão?
   - Estilo Charlie Morgan aplicado?

### FORMATO DE RESPOSTA ###

Retorne um JSON com:
{{
    "score": <número 0-100>,
    "breakdown": {{
        "rapport": <0-20>,
        "discovery": <0-25>,
        "objections": <0-20>,
        "advancement": <0-20>,
        "communication": <0-15>
    }},
    "strengths": ["<ponto forte 1>", "<ponto forte 2>"],
    "weaknesses": ["<ponto fraco 1>", "<ponto fraco 2>"],
    "suggestions": ["<sugestão 1>", "<sugestão 2>"],
    "outcome_prediction": "<scheduled|qualified|nurture|lost>",
    "summary": "<resumo em 2-3 frases>"
}}
"""

    def to_dict(self) -> Dict:
        """Converte para dicionário (para salvar em JSON/Supabase)"""
        return {
            "session_id": self.session_id,
            "agent_code": self.agent_code,
            "persona_type": self.persona.type.value,
            "persona_name": self.persona.name,
            "conversation": [
                {
                    "role": t.role,
                    "message": t.message,
                    "timestamp": t.timestamp.isoformat()
                }
                for t in self.conversation
            ],
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "outcome": self.outcome,
            "agent_score": self.agent_score,
            "evaluation_notes": self.evaluation_notes
        }


class LeadSimulator:
    """Orquestrador de simulações de lead"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.sessions: List[SimulationSession] = []

    def create_session(
        self,
        agent_code: str,
        persona_type: PersonaType
    ) -> SimulationSession:
        """Cria uma nova sessão de simulação"""
        persona = PERSONA_LIBRARY.get(persona_type)
        if not persona:
            raise ValueError(f"Persona type {persona_type} not found")

        session = SimulationSession(
            session_id=f"sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}",
            agent_code=agent_code,
            persona=persona
        )
        self.sessions.append(session)
        return session

    def get_lead_response(
        self,
        session: SimulationSession,
        agent_message: str
    ) -> str:
        """
        Gera resposta do lead simulado usando Claude.

        Em produção, isso chamaria a API do Claude.
        Aqui está a estrutura para integração.
        """
        # Adiciona mensagem do agente ao histórico
        session.add_turn("agent", agent_message)

        # Monta o prompt para o lead simulado
        system_prompt = session.persona.to_system_prompt()
        conversation_history = session.get_conversation_history()

        # Aqui entraria a chamada real para Claude API
        # Por enquanto, retorna placeholder
        lead_response = self._call_claude_api(
            system_prompt=system_prompt,
            user_message=f"""Histórico da conversa:
{conversation_history}

Responda à última mensagem do agente como o lead {session.persona.name}."""
        )

        # Adiciona resposta ao histórico
        session.add_turn("lead", lead_response)

        return lead_response

    def _call_claude_api(
        self,
        system_prompt: str,
        user_message: str
    ) -> str:
        """
        Placeholder para chamada real à API do Claude.

        Para integrar com Anthropic SDK:
        ```python
        from anthropic import Anthropic

        client = Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        return response.content[0].text
        ```
        """
        # Placeholder - em produção, usar SDK
        return "[Resposta simulada - integrar com Anthropic SDK]"

    def evaluate_session(self, session: SimulationSession) -> Dict:
        """
        Avalia a performance do agente na sessão.

        Usa Claude para analisar a conversa e dar score.
        """
        evaluation_prompt = session.to_evaluation_prompt()

        # Chamada para Claude avaliar
        evaluation_json = self._call_claude_api(
            system_prompt="Você é um especialista em vendas B2B.",
            user_message=evaluation_prompt
        )

        # Parse do resultado
        try:
            evaluation = json.loads(evaluation_json)
            session.agent_score = evaluation.get("score")
            session.evaluation_notes = evaluation.get("suggestions", [])
            session.outcome = evaluation.get("outcome_prediction")
            return evaluation
        except json.JSONDecodeError:
            return {"error": "Failed to parse evaluation", "raw": evaluation_json}

    def run_full_simulation(
        self,
        agent_code: str,
        persona_type: PersonaType,
        agent_callable,  # Função que recebe mensagem e retorna resposta do agente
        max_turns: int = 10,
        initial_message: Optional[str] = None
    ) -> SimulationSession:
        """
        Executa uma simulação completa.

        Args:
            agent_code: Código do agente sendo testado
            persona_type: Tipo de persona do lead
            agent_callable: Função que representa o agente (msg -> resposta)
            max_turns: Máximo de turnos antes de encerrar
            initial_message: Mensagem inicial (se None, lead inicia)

        Returns:
            Sessão completa com avaliação
        """
        session = self.create_session(agent_code, persona_type)

        # Se agente inicia
        if initial_message:
            lead_response = self.get_lead_response(session, initial_message)
        else:
            # Lead inicia (ex: respondeu a um post)
            initial_lead_msg = self._generate_initial_lead_message(session.persona)
            session.add_turn("lead", initial_lead_msg)

        # Loop de conversa
        for turn in range(max_turns):
            # Agente responde
            last_lead_msg = session.conversation[-1].message
            agent_response = agent_callable(
                message=last_lead_msg,
                history=session.get_conversation_history()
            )

            # Lead responde
            lead_response = self.get_lead_response(session, agent_response)

            # Verifica se deve encerrar
            if self._should_end_conversation(session, lead_response):
                break

        # Finaliza e avalia
        session.ended_at = datetime.now()
        self.evaluate_session(session)

        return session

    def _generate_initial_lead_message(self, persona: LeadPersona) -> str:
        """Gera mensagem inicial baseada na persona"""
        starters = {
            PersonaType.HOT_BUYER: [
                "Oi, vi vocês no Instagram. Quanto custa?",
                "Olá! Quero saber mais sobre o serviço de vocês",
                "Oi, uma amiga indicou vocês. Como funciona?"
            ],
            PersonaType.WARM_CURIOUS: [
                "Oi",
                "Olá, tudo bem?",
                "Vi o post de vocês, interessante"
            ],
            PersonaType.COLD_SKEPTIC: [
                "Oi",
                "?"
            ],
            PersonaType.PRICE_OBJECTOR: [
                "Quanto custa?",
                "Qual o valor?",
                "Me passa o preço"
            ],
            PersonaType.BUSY_EXECUTIVE: [
                "Oi, me manda informações rápido",
                "Objetivo: o que vocês fazem?"
            ],
            PersonaType.GHOSTING: [
                "Oi"
            ]
        }

        options = starters.get(persona.type, ["Olá"])
        return random.choice(options)

    def _should_end_conversation(
        self,
        session: SimulationSession,
        last_lead_response: str
    ) -> bool:
        """Verifica se a conversa deve encerrar"""
        # Encerra se lead agendou
        if any(word in last_lead_response.lower() for word in
               ["combinado", "fechado", "vamos marcar", "pode ser"]):
            session.outcome = "scheduled"
            return True

        # Encerra se lead desistiu claramente
        if any(word in last_lead_response.lower() for word in
               ["não quero", "não tenho interesse", "para de me mandar"]):
            session.outcome = "lost"
            return True

        # Encerra se lead ghostou (resposta muito curta após muitos turnos)
        if len(session.conversation) > 6 and len(last_lead_response) < 5:
            session.outcome = "ghosted"
            return True

        return False

    def generate_test_report(self, sessions: List[SimulationSession]) -> str:
        """Gera relatório de testes"""
        report = []
        report.append("=" * 60)
        report.append("GROWTH OS - RELATÓRIO DE TESTES DE AGENTES")
        report.append("=" * 60)
        report.append(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append(f"Total de sessões: {len(sessions)}")
        report.append("")

        # Agrupa por agente
        agents = {}
        for s in sessions:
            if s.agent_code not in agents:
                agents[s.agent_code] = []
            agents[s.agent_code].append(s)

        for agent_code, agent_sessions in agents.items():
            report.append(f"\n### AGENTE: {agent_code} ###")
            report.append(f"Sessões testadas: {len(agent_sessions)}")

            scores = [s.agent_score for s in agent_sessions if s.agent_score]
            if scores:
                avg_score = sum(scores) / len(scores)
                report.append(f"Score médio: {avg_score:.1f}/100")

            outcomes = {}
            for s in agent_sessions:
                outcome = s.outcome or "incomplete"
                outcomes[outcome] = outcomes.get(outcome, 0) + 1

            report.append("Outcomes:")
            for outcome, count in outcomes.items():
                pct = count / len(agent_sessions) * 100
                report.append(f"  - {outcome}: {count} ({pct:.1f}%)")

        report.append("\n" + "=" * 60)
        return "\n".join(report)


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    """Ponto de entrada CLI"""
    import argparse

    parser = argparse.ArgumentParser(description="Growth OS Lead Simulator")
    parser.add_argument(
        "--persona",
        type=str,
        choices=[p.value for p in PersonaType],
        default="warm_curious",
        help="Tipo de persona do lead"
    )
    parser.add_argument(
        "--agent",
        type=str,
        default="SSIG-004",
        help="Código do agente a testar"
    )
    parser.add_argument(
        "--list-personas",
        action="store_true",
        help="Lista todas as personas disponíveis"
    )

    args = parser.parse_args()

    if args.list_personas:
        print("\n=== PERSONAS DISPONÍVEIS ===\n")
        for ptype, persona in PERSONA_LIBRARY.items():
            print(f"{ptype.value}:")
            print(f"  Nome: {persona.name}")
            print(f"  Empresa: {persona.company}")
            print(f"  Dor: {persona.pain_level}/10")
            print(f"  Urgência: {persona.timeline_urgency}/10")
            print(f"  Objeções: {', '.join(persona.objections) if persona.objections else 'Nenhuma'}")
            print()
        return

    # Criar simulador
    simulator = LeadSimulator()

    # Criar sessão
    persona_type = PersonaType(args.persona)
    session = simulator.create_session(args.agent, persona_type)

    print(f"\n=== SIMULAÇÃO INICIADA ===")
    print(f"Agente: {args.agent}")
    print(f"Persona: {session.persona.name} ({persona_type.value})")
    print(f"Empresa: {session.persona.company}")
    print()
    print("System prompt do lead:")
    print("-" * 40)
    print(session.persona.to_system_prompt())
    print("-" * 40)
    print()
    print("Para executar simulação completa, integre com a API do Claude.")
    print("Veja o método run_full_simulation() para exemplo de uso.")


if __name__ == "__main__":
    main()
