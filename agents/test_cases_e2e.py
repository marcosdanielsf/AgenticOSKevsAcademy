"""
GROWTH OS - TEST CASES E2E
Casos de teste end-to-end para cada um dos 14 agentes operacionais.

Cada agente tem:
- Cenários positivos (happy path)
- Cenários de objeção
- Edge cases
- Métricas esperadas

Uso:
    python test_cases_e2e.py --agent SSIG-004 --run
    python test_cases_e2e.py --all --report
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

from lead_simulator import (
    PersonaType,
    LeadPersona,
    PERSONA_LIBRARY,
    LeadSimulator,
    SimulationSession
)
from flow_orchestrator import (
    AgentCode,
    HandoffTrigger,
    FunnelStage
)


# =============================================================================
# ESTRUTURAS DE TESTE
# =============================================================================

class TestOutcome(Enum):
    """Resultados possíveis de um teste"""
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


@dataclass
class TestScenario:
    """Um cenário de teste específico"""
    scenario_id: str
    name: str
    description: str
    agent_code: AgentCode
    persona_type: PersonaType

    # Conversa esperada
    initial_message: str  # Primeira mensagem (do lead ou do agente)
    agent_starts: bool = False  # Se True, agente inicia a conversa
    expected_flow: List[Dict] = field(default_factory=list)  # Fluxo esperado

    # Critérios de sucesso
    expected_handoff: Optional[HandoffTrigger] = None
    expected_stage: Optional[FunnelStage] = None
    min_score: int = 70  # Score mínimo para passar
    max_turns: int = 8  # Máximo de turnos

    # Tags
    tags: List[str] = field(default_factory=list)  # ["happy_path", "objection", "edge_case"]
    priority: str = "medium"  # low, medium, high, critical


@dataclass
class TestResult:
    """Resultado de execução de um teste"""
    scenario: TestScenario
    outcome: TestOutcome
    actual_score: Optional[int] = None
    actual_handoff: Optional[str] = None
    actual_turns: int = 0
    session: Optional[SimulationSession] = None
    error_message: Optional[str] = None
    execution_time_ms: int = 0
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "scenario_id": self.scenario.scenario_id,
            "scenario_name": self.scenario.name,
            "agent": self.scenario.agent_code.value,
            "outcome": self.outcome.value,
            "score": self.actual_score,
            "expected_min_score": self.scenario.min_score,
            "handoff": self.actual_handoff,
            "expected_handoff": self.scenario.expected_handoff.value if self.scenario.expected_handoff else None,
            "turns": self.actual_turns,
            "max_turns": self.scenario.max_turns,
            "execution_time_ms": self.execution_time_ms,
            "error": self.error_message,
            "notes": self.notes
        }


# =============================================================================
# BIBLIOTECA DE TEST CASES
# =============================================================================

TEST_CASES: Dict[AgentCode, List[TestScenario]] = {

    # =========================================================================
    # AGENTE 01: PROSPECTOR (PROS-001)
    # =========================================================================
    AgentCode.PROSPECTOR: [
        TestScenario(
            scenario_id="PROS-001-HP-001",
            name="Prospect responde positivamente à abordagem",
            description="Lead responde com interesse à primeira mensagem",
            agent_code=AgentCode.PROSPECTOR,
            persona_type=PersonaType.WARM_CURIOUS,
            initial_message="Oi {{NOME}}! Vi que você trabalha com estética. Posso te fazer uma pergunta rápida?",
            agent_starts=True,
            expected_flow=[
                {"lead": "Pode sim, fala"},
                {"agent": "Qual seu maior desafio com captação de clientes hoje?"},
                {"lead": "Ah, a agenda fica vazia em alguns dias da semana"},
                {"agent": "Isso é bem comum! Você já tentou algo pra resolver?"}
            ],
            expected_handoff=HandoffTrigger.SHOWED_INTEREST,
            expected_stage=FunnelStage.LEAD,
            min_score=75,
            tags=["happy_path", "prospection"],
            priority="high"
        ),
        TestScenario(
            scenario_id="PROS-001-OBJ-001",
            name="Prospect ignora primeira mensagem",
            description="Lead não responde à abordagem inicial",
            agent_code=AgentCode.PROSPECTOR,
            persona_type=PersonaType.GHOSTING,
            initial_message="Oi! Vi que você tem clínica de estética. Posso fazer uma pergunta rápida?",
            agent_starts=True,
            expected_flow=[
                {"lead": "[SEM RESPOSTA - 48h]"},
                {"agent": "Oi! Mandei mensagem ontem mas acho que se perdeu. Só queria saber se você trabalha com estética mesmo."},
                {"lead": "[SEM RESPOSTA - 48h]"}
            ],
            expected_handoff=HandoffTrigger.WENT_COLD,
            min_score=60,
            tags=["objection", "ghosting"],
            priority="medium"
        ),
        TestScenario(
            scenario_id="PROS-001-EDGE-001",
            name="Prospect é agressivo na resposta",
            description="Lead responde de forma hostil",
            agent_code=AgentCode.PROSPECTOR,
            persona_type=PersonaType.COLD_SKEPTIC,
            initial_message="Oi! Vi seu perfil e achei interessante. Posso te fazer uma pergunta?",
            agent_starts=True,
            expected_flow=[
                {"lead": "Mais um vendendo curso? Para de me mandar spam!"},
                {"agent": "Desculpa pelo incômodo! Não é curso não. Mas entendo. Se quiser conversar algum dia, tô por aqui."}
            ],
            min_score=65,
            tags=["edge_case", "hostile"],
            priority="medium"
        )
    ],

    # =========================================================================
    # AGENTE 04: SOCIAL SELLER INSTAGRAM (SSIG-004)
    # =========================================================================
    AgentCode.SOCIAL_SELLER_IG: [
        TestScenario(
            scenario_id="SSIG-004-HP-001",
            name="Lead engaja após curtir post",
            description="Pessoa curtiu post e agente inicia DM",
            agent_code=AgentCode.SOCIAL_SELLER_IG,
            persona_type=PersonaType.WARM_CURIOUS,
            initial_message="Oi! Vi que curtiu o post sobre agenda lotada. Você trabalha com estética também?",
            agent_starts=True,
            expected_flow=[
                {"lead": "Oi! Sim, tenho uma clínica de estética"},
                {"agent": "Que legal! Como tá a demanda aí esse mês?"},
                {"lead": "Tá meio fraca, alguns dias fico com a agenda vazia"},
                {"agent": "Isso é frustrante mesmo. Você já tentou alguma estratégia pra resolver?"},
                {"lead": "Já fiz uns anúncios mas não deu muito certo"},
                {"agent": "Entendo. E você cuida disso sozinha ou tem uma equipe?"}
            ],
            expected_handoff=HandoffTrigger.BANT_COMPLETE,
            expected_stage=FunnelStage.QUALIFIED,
            min_score=80,
            tags=["happy_path", "qualification"],
            priority="critical"
        ),
        TestScenario(
            scenario_id="SSIG-004-HP-002",
            name="Lead pede preço diretamente",
            description="Lead já quer saber valor antes de qualificar",
            agent_code=AgentCode.SOCIAL_SELLER_IG,
            persona_type=PersonaType.PRICE_OBJECTOR,
            initial_message="Oi! Vi o post de vocês. Quanto custa?",
            agent_starts=False,
            expected_flow=[
                {"agent": "Oi! Que bom que se interessou! O valor varia bastante dependendo do que você precisa. Me conta: você tem clínica de estética?"},
                {"lead": "Tenho sim, de dermatologia"},
                {"agent": "Legal! E qual seu maior desafio hoje? Captar pacientes ou reter os que já tem?"},
                {"lead": "Captar. A agenda tá vazia demais"}
            ],
            min_score=75,
            tags=["happy_path", "price_question"],
            priority="high"
        ),
        TestScenario(
            scenario_id="SSIG-004-OBJ-001",
            name="Lead tem objeção de já usar concorrente",
            description="Lead menciona que já usa outra solução",
            agent_code=AgentCode.SOCIAL_SELLER_IG,
            persona_type=PersonaType.COMPETITOR_USER,
            initial_message="Já uso outra empresa de marketing",
            agent_starts=False,
            expected_flow=[
                {"agent": "Entendi! E como tá sendo a experiência? Tá tendo os resultados que esperava?"},
                {"lead": "Mais ou menos. Os leads que chegam não são muito qualificados"},
                {"agent": "Isso é bem frustrante mesmo. O que seria o ideal pra você?"},
                {"lead": "Receber leads que realmente querem fazer procedimento"}
            ],
            expected_handoff=HandoffTrigger.HAS_OBJECTION,
            min_score=70,
            tags=["objection", "competitor"],
            priority="high"
        ),
        TestScenario(
            scenario_id="SSIG-004-EDGE-001",
            name="Lead é funcionário, não decisor",
            description="Pessoa que engajou não é quem decide",
            agent_code=AgentCode.SOCIAL_SELLER_IG,
            persona_type=PersonaType.RESEARCHER,
            initial_message="Oi! Vi o post. Achei interessante",
            agent_starts=False,
            expected_flow=[
                {"agent": "Oi! Que bom! Você trabalha com clínica de estética?"},
                {"lead": "Trabalho sim, sou recepcionista"},
                {"agent": "Legal! E quem cuida da parte de marketing e captação aí?"},
                {"lead": "É a dona da clínica, a Dra. Paula"},
                {"agent": "Entendi! Você acha que ela teria interesse em conversar sobre isso?"}
            ],
            min_score=70,
            tags=["edge_case", "non_decision_maker"],
            priority="medium"
        )
    ],

    # =========================================================================
    # AGENTE 06: SDR INBOUND (SDRI-006)
    # =========================================================================
    AgentCode.SDR_INBOUND: [
        TestScenario(
            scenario_id="SDRI-006-HP-001",
            name="Lead inbound qualificado rapidamente",
            description="Lead que veio por formulário é qualificado com BANT completo",
            agent_code=AgentCode.SDR_INBOUND,
            persona_type=PersonaType.HOT_BUYER,
            initial_message="Quero saber mais sobre o serviço de vocês",
            agent_starts=False,
            expected_flow=[
                {"agent": "Oi Paula! Que bom que entrou em contato. Vi que você tem interesse em lotar a agenda da clínica. O que te fez buscar isso agora?"},
                {"lead": "Minha clínica tá com a agenda muito vazia, preciso de mais pacientes"},
                {"agent": "Entendo, isso é bem frustrante. E pra quando você quer resolver isso?"},
                {"lead": "O mais rápido possível, quero começar esse mês ainda"},
                {"agent": "Perfeito! E você é quem decide sobre investimentos de marketing ou precisa consultar alguém?"},
                {"lead": "Sou eu que decido, é minha clínica"},
                {"agent": "Ótimo! Sobre investimento, você já tem um valor em mente pra isso?"},
                {"lead": "Pensei em uns 3 a 5 mil por mês"}
            ],
            expected_handoff=HandoffTrigger.BANT_COMPLETE,
            expected_stage=FunnelStage.QUALIFIED,
            min_score=85,
            tags=["happy_path", "fast_qualification"],
            priority="critical"
        ),
        TestScenario(
            scenario_id="SDRI-006-OBJ-001",
            name="Lead quer preço antes de qualificar",
            description="Lead insiste em saber preço antes de responder perguntas",
            agent_code=AgentCode.SDR_INBOUND,
            persona_type=PersonaType.PRICE_OBJECTOR,
            initial_message="Quanto custa? Só me passa o preço",
            agent_starts=False,
            expected_flow=[
                {"agent": "Claro! O valor varia bastante dependendo do que você precisa. Pra te dar um número mais preciso: você tem clínica de estética?"},
                {"lead": "Tenho. Mas só me fala o preço que eu vejo se faz sentido"},
                {"agent": "Entendo a pressa! Nossos planos vão de R$2k a R$10k dependendo do tamanho da operação. Qual seria mais ou menos seu faturamento mensal?"},
                {"lead": "Faturo uns 30 mil por mês"}
            ],
            min_score=70,
            tags=["objection", "price_pressure"],
            priority="high"
        ),
        TestScenario(
            scenario_id="SDRI-006-EDGE-001",
            name="Lead hot demais - quer fechar na hora",
            description="Lead já chega querendo contratar sem passar por qualificação",
            agent_code=AgentCode.SDR_INBOUND,
            persona_type=PersonaType.HOT_BUYER,
            initial_message="Quero contratar vocês. Como faço?",
            agent_starts=False,
            expected_flow=[
                {"agent": "Que maravilha! Adoro esse entusiasmo. Só pra eu te encaminhar pro caminho certo: qual o tamanho da sua clínica?"},
                {"lead": "Tenho 3 unidades, preciso de ajuda em todas"},
                {"agent": "Perfeito! Para operações maiores assim, o ideal é conversar com nosso especialista. Ele vai entender melhor o cenário e fazer uma proposta personalizada. Consegue amanhã às 10h ou às 15h?"}
            ],
            expected_handoff=HandoffTrigger.READY_TO_CLOSE,
            min_score=85,
            tags=["edge_case", "vip", "fast_track"],
            priority="critical"
        )
    ],

    # =========================================================================
    # AGENTE 11: OBJECTION HANDLER (OBJH-011)
    # =========================================================================
    AgentCode.OBJECTION_HANDLER: [
        TestScenario(
            scenario_id="OBJH-011-HP-001",
            name="Supera objeção de preço com ROI",
            description="Lead diz que tá caro, agente mostra retorno",
            agent_code=AgentCode.OBJECTION_HANDLER,
            persona_type=PersonaType.PRICE_OBJECTOR,
            initial_message="Tá muito caro pra mim",
            agent_starts=False,
            expected_flow=[
                {"agent": "Entendo! Muita gente sente isso no começo. Posso te fazer uma pergunta? Quanto você perde por mês quando a agenda fica vazia?"},
                {"lead": "Ah, uns 10, 15 mil fácil"},
                {"agent": "Então são R$15k perdidos todo mês. Nosso investimento é de R$3k. Se a gente conseguir recuperar só 20% desse potencial, você já tem retorno. Faz sentido pensar assim?"},
                {"lead": "É, vendo assim faz sentido..."},
                {"agent": "Exato! E a maioria dos nossos clientes vê resultado já no primeiro mês. Quer que eu te mostre alguns casos?"}
            ],
            expected_handoff=HandoffTrigger.READY_TO_CLOSE,
            min_score=80,
            tags=["happy_path", "price_objection"],
            priority="critical"
        ),
        TestScenario(
            scenario_id="OBJH-011-HP-002",
            name="Supera 'preciso pensar'",
            description="Lead diz que precisa pensar, agente descobre objeção real",
            agent_code=AgentCode.OBJECTION_HANDLER,
            persona_type=PersonaType.TIME_OBJECTOR,
            initial_message="Gostei, mas preciso pensar",
            agent_starts=False,
            expected_flow=[
                {"agent": "Claro, sem pressão! Só pra eu entender melhor: o que exatamente você quer pensar? É sobre o investimento, o timing, ou algo que eu não expliquei direito?"},
                {"lead": "É mais o timing mesmo, to focada em outra coisa agora"},
                {"agent": "Entendo! O que tá ocupando sua atenção? Porque às vezes a gente consegue encaixar de uma forma que não atrapalha o resto"},
                {"lead": "To inaugurando uma segunda unidade"},
                {"agent": "Uau, parabéns! E justamente, lotar a agenda da nova unidade não seria uma prioridade?"}
            ],
            min_score=75,
            tags=["happy_path", "think_about_it"],
            priority="high"
        ),
        TestScenario(
            scenario_id="OBJH-011-OBJ-001",
            name="Objeção não superada - lead não é fit",
            description="Lead realmente não tem budget e não é fit",
            agent_code=AgentCode.OBJECTION_HANDLER,
            persona_type=PersonaType.COLD_SKEPTIC,
            initial_message="Não tenho dinheiro pra isso, minha clínica tá quase fechando",
            agent_starts=False,
            expected_flow=[
                {"agent": "Entendo, momento difícil. Posso te perguntar: o que tá causando isso?"},
                {"lead": "Os custos fixos tão muito altos e os pacientes não aparecem"},
                {"agent": "Situação complicada. Olha, sendo honesto: nosso serviço funciona melhor pra quem já tem uma base mínima. Talvez não seja o momento ideal pra vocês investirem."},
                {"lead": "É, acho que você tem razão"},
                {"agent": "Mas posso te mandar um material gratuito com dicas pra melhorar isso por conta própria. Interesse?"}
            ],
            expected_stage=FunnelStage.LOST,
            min_score=70,
            tags=["objection", "disqualification", "honest"],
            priority="medium"
        )
    ],

    # =========================================================================
    # AGENTE 12: SCHEDULER (SCHD-012)
    # =========================================================================
    AgentCode.SCHEDULER: [
        TestScenario(
            scenario_id="SCHD-012-HP-001",
            name="Agendamento com opções binárias",
            description="Lead é agendado com técnica de opções binárias",
            agent_code=AgentCode.SCHEDULER,
            persona_type=PersonaType.HOT_BUYER,
            initial_message="Quero agendar a conversa",
            agent_starts=False,
            expected_flow=[
                {"agent": "Perfeito! Vamos marcar então. Consegue amanhã às 10h ou quinta às 15h?"},
                {"lead": "Quinta às 15h tá ótimo"},
                {"agent": "Fechado! Quinta, dia 16, às 15h. Vai ser uma call de 30 minutos pelo Google Meet. Qual email você usa pro convite?"},
                {"lead": "paula@clinicabella.com"},
                {"agent": "Pronto! Convite enviado. Vou te mandar um lembrete antes. Qualquer imprevisto, me avisa por aqui. Até quinta!"}
            ],
            expected_handoff=HandoffTrigger.MEETING_CONFIRMED,
            expected_stage=FunnelStage.SCHEDULED,
            min_score=90,
            tags=["happy_path", "scheduling"],
            priority="critical"
        ),
        TestScenario(
            scenario_id="SCHD-012-OBJ-001",
            name="Lead quer reagendar várias vezes",
            description="Lead pede pra remarcar mais de uma vez",
            agent_code=AgentCode.SCHEDULER,
            persona_type=PersonaType.BUSY_EXECUTIVE,
            initial_message="Preciso remarcar nossa conversa",
            agent_starts=False,
            expected_flow=[
                {"agent": "Sem problema! Quando fica melhor pra você?"},
                {"lead": "Semana que vem talvez"},
                {"agent": "Ok! Segunda às 10h ou terça às 15h, qual prefere?"},
                {"lead": "Terça tá bom"},
                {"agent": "Perfeito, confirmado pra terça às 15h!"},
                {"lead": "[2 DIAS DEPOIS] Vou ter que remarcar de novo..."},
                {"agent": "Entendo! Sua agenda parece bem corrida. Olha, sem pressão - quando você tiver um momento mais tranquilo, me avisa que a gente marca. Que tal me chamar quando estiver pronta?"}
            ],
            min_score=70,
            tags=["objection", "reschedule"],
            priority="medium"
        )
    ],

    # =========================================================================
    # AGENTE 14: CLOSER (CLOS-014)
    # =========================================================================
    AgentCode.CLOSER: [
        TestScenario(
            scenario_id="CLOS-014-HP-001",
            name="Fechamento após call bem conduzida",
            description="Lead fecha após conversa de descoberta e proposta",
            agent_code=AgentCode.CLOSER,
            persona_type=PersonaType.HOT_BUYER,
            initial_message="[CALL INICIADA] Oi Paula, prazer te conhecer!",
            agent_starts=True,
            expected_flow=[
                {"lead": "Oi! Prazer também!"},
                {"agent": "Antes da gente começar: o objetivo de hoje é entender seu cenário e ver se faz sentido trabalharmos juntos. Se fizer, te mostro como. Se não, tudo bem também. Funciona?"},
                {"lead": "Funciona!"},
                {"agent": "Ótimo! Me conta: qual o maior desafio da clínica hoje?"},
                {"lead": "A agenda fica muito vazia, especialmente segunda e terça"},
                {"agent": "E quanto você perde de faturamento nesses dias vazios?"},
                {"lead": "Uns 3 mil por semana, fácil"},
                {"agent": "Então são R$12k por mês de potencial perdido. Se eu te mostrar como recuperar pelo menos metade disso, faz sentido pra você?"},
                {"lead": "Com certeza!"},
                {"agent": "[APRESENTA SOLUÇÃO]... O investimento é de R$3k por mês. Baseado no que você me contou, você recuperaria isso em 1 semana. Faz sentido começarmos?"},
                {"lead": "Faz sentido sim, vamos fechar"}
            ],
            expected_stage=FunnelStage.WON,
            min_score=90,
            tags=["happy_path", "closing"],
            priority="critical"
        ),
        TestScenario(
            scenario_id="CLOS-014-OBJ-001",
            name="Fechamento com objeção de preço no final",
            description="Lead engaja na call mas hesita no preço",
            agent_code=AgentCode.CLOSER,
            persona_type=PersonaType.PRICE_OBJECTOR,
            initial_message="[CALL] O investimento é R$5k por mês",
            agent_starts=True,
            expected_flow=[
                {"lead": "Hmm, tá meio pesado... Não sei se consigo agora"},
                {"agent": "Entendo. Me ajuda a entender: o valor que você perde por mês com agenda vazia é quanto mesmo?"},
                {"lead": "Uns 15 mil talvez"},
                {"agent": "Então o investimento é 5k pra potencialmente recuperar 15k. Mesmo que a gente consiga só 50%, você já tem 7.5k a mais. O que te impede de começar?"},
                {"lead": "É que o fluxo de caixa esse mês tá apertado"},
                {"agent": "Faz sentido. E se a gente começar no mês que vem? Você teria esse respiro e não perde a oportunidade. Funciona?"},
                {"lead": "Isso funciona sim!"}
            ],
            expected_stage=FunnelStage.WON,
            min_score=85,
            tags=["objection", "price", "closing"],
            priority="critical"
        )
    ],

    # =========================================================================
    # AGENTE 02: DATABASE REACTIVATOR (REAC-002)
    # =========================================================================
    AgentCode.DATABASE_REACTIVATOR: [
        TestScenario(
            scenario_id="REAC-002-HP-001",
            name="Lead reativado com 9-word message",
            description="Lead frio responde à mensagem de reativação",
            agent_code=AgentCode.DATABASE_REACTIVATOR,
            persona_type=PersonaType.WARM_CURIOUS,
            initial_message="Oi Maria, ainda tá pensando em lotar a agenda?",
            agent_starts=True,
            expected_flow=[
                {"lead": "Oi! Sim, ainda preciso resolver isso"},
                {"agent": "Que bom! O que mudou desde a última vez que conversamos?"},
                {"lead": "Contratei uma pessoa nova e preciso de mais pacientes pra pagar ela"},
                {"agent": "Entendi! Então agora é mais urgente. Quer que a gente retome de onde paramos?"}
            ],
            expected_handoff=HandoffTrigger.SHOWED_INTEREST,
            min_score=80,
            tags=["happy_path", "reactivation"],
            priority="high"
        ),
        TestScenario(
            scenario_id="REAC-002-OBJ-001",
            name="Lead pede para parar de mandar mensagem",
            description="Lead responde negativamente à reativação",
            agent_code=AgentCode.DATABASE_REACTIVATOR,
            persona_type=PersonaType.COLD_SKEPTIC,
            initial_message="João, você desistiu de resolver o problema da agenda?",
            agent_starts=True,
            expected_flow=[
                {"lead": "Para de me mandar mensagem! Não quero nada"},
                {"agent": "Desculpa pelo incômodo! Vou te remover da lista agora. Se mudar de ideia no futuro, estamos por aqui. Abraço!"}
            ],
            expected_stage=FunnelStage.LOST,
            min_score=70,
            tags=["objection", "dnd"],
            priority="medium"
        )
    ]
}


# =============================================================================
# TEST RUNNER
# =============================================================================

class TestRunner:
    """Executa e gerencia testes E2E"""

    def __init__(self, simulator: LeadSimulator = None):
        self.simulator = simulator or LeadSimulator()
        self.results: List[TestResult] = []

    def run_scenario(
        self,
        scenario: TestScenario,
        agent_callable=None
    ) -> TestResult:
        """
        Executa um cenário de teste.

        Args:
            scenario: Cenário a testar
            agent_callable: Função que simula o agente

        Returns:
            Resultado do teste
        """
        start_time = datetime.now()

        try:
            # Cria sessão de simulação
            session = self.simulator.create_session(
                agent_code=scenario.agent_code.value,
                persona_type=scenario.persona_type
            )

            # Simula conversa (em produção, integraria com agentes reais)
            for turn, expected_turn in enumerate(scenario.expected_flow):
                if "lead" in expected_turn:
                    session.add_turn("lead", expected_turn["lead"])
                elif "agent" in expected_turn:
                    session.add_turn("agent", expected_turn["agent"])

                if turn >= scenario.max_turns:
                    break

            # Avalia sessão
            evaluation = self.simulator.evaluate_session(session)

            # Determina resultado
            actual_score = evaluation.get("score", 0) if isinstance(evaluation, dict) else 50
            passed = actual_score >= scenario.min_score

            result = TestResult(
                scenario=scenario,
                outcome=TestOutcome.PASS if passed else TestOutcome.FAIL,
                actual_score=actual_score,
                actual_handoff=evaluation.get("outcome_prediction") if isinstance(evaluation, dict) else None,
                actual_turns=len(scenario.expected_flow),
                session=session,
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )

        except Exception as e:
            result = TestResult(
                scenario=scenario,
                outcome=TestOutcome.ERROR,
                error_message=str(e),
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )

        self.results.append(result)
        return result

    def run_agent_tests(self, agent_code: AgentCode) -> List[TestResult]:
        """Executa todos os testes de um agente"""
        scenarios = TEST_CASES.get(agent_code, [])
        results = []

        for scenario in scenarios:
            result = self.run_scenario(scenario)
            results.append(result)
            print(f"  [{result.outcome.value.upper()}] {scenario.name}")

        return results

    def run_all_tests(self) -> Dict[str, List[TestResult]]:
        """Executa todos os testes de todos os agentes"""
        all_results = {}

        for agent_code, scenarios in TEST_CASES.items():
            print(f"\n=== TESTANDO {agent_code.value} ===")
            results = self.run_agent_tests(agent_code)
            all_results[agent_code.value] = results

        return all_results

    def generate_report(self) -> str:
        """Gera relatório de testes"""
        lines = []
        lines.append("=" * 60)
        lines.append("GROWTH OS - RELATÓRIO DE TESTES E2E")
        lines.append("=" * 60)
        lines.append(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"Total de testes: {len(self.results)}")
        lines.append("")

        # Estatísticas gerais
        passed = sum(1 for r in self.results if r.outcome == TestOutcome.PASS)
        failed = sum(1 for r in self.results if r.outcome == TestOutcome.FAIL)
        errors = sum(1 for r in self.results if r.outcome == TestOutcome.ERROR)

        lines.append(f"✅ Passou: {passed}")
        lines.append(f"❌ Falhou: {failed}")
        lines.append(f"⚠️ Erros: {errors}")
        lines.append(f"Taxa de sucesso: {passed / len(self.results) * 100:.1f}%" if self.results else "N/A")
        lines.append("")

        # Por agente
        agents = {}
        for r in self.results:
            agent = r.scenario.agent_code.value
            if agent not in agents:
                agents[agent] = {"pass": 0, "fail": 0, "error": 0}
            agents[agent][r.outcome.value] += 1

        lines.append("### POR AGENTE ###")
        for agent, stats in agents.items():
            total = stats["pass"] + stats["fail"] + stats["error"]
            pct = stats["pass"] / total * 100 if total else 0
            status = "✅" if pct >= 80 else "⚠️" if pct >= 50 else "❌"
            lines.append(f"{status} {agent}: {stats['pass']}/{total} ({pct:.0f}%)")

        lines.append("")
        lines.append("### TESTES FALHADOS ###")
        for r in self.results:
            if r.outcome in [TestOutcome.FAIL, TestOutcome.ERROR]:
                lines.append(f"- [{r.scenario.agent_code.value}] {r.scenario.name}")
                if r.error_message:
                    lines.append(f"  Erro: {r.error_message}")
                else:
                    lines.append(f"  Score: {r.actual_score} (mínimo: {r.scenario.min_score})")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    def export_results_json(self, filepath: str):
        """Exporta resultados para JSON"""
        data = [r.to_dict() for r in self.results]
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# =============================================================================
# CLI
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Growth OS E2E Test Runner")
    parser.add_argument(
        "--agent",
        type=str,
        help="Código do agente a testar (ex: SSIG-004)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Executa todos os testes"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Lista todos os cenários disponíveis"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Gera relatório após execução"
    )
    parser.add_argument(
        "--export",
        type=str,
        help="Exporta resultados para JSON"
    )

    args = parser.parse_args()

    if args.list:
        print("\n=== CENÁRIOS DE TESTE DISPONÍVEIS ===\n")
        for agent_code, scenarios in TEST_CASES.items():
            print(f"{agent_code.value}:")
            for s in scenarios:
                tags = " ".join(f"[{t}]" for t in s.tags)
                print(f"  - {s.scenario_id}: {s.name} {tags}")
            print()
        return

    runner = TestRunner()

    if args.all:
        runner.run_all_tests()
    elif args.agent:
        try:
            agent_code = AgentCode(args.agent)
            print(f"\n=== TESTANDO {agent_code.value} ===")
            runner.run_agent_tests(agent_code)
        except ValueError:
            print(f"Agente '{args.agent}' não encontrado.")
            print("Agentes disponíveis:")
            for a in AgentCode:
                print(f"  - {a.value}")
            return
    else:
        print("Use --all para rodar todos os testes ou --agent CÓDIGO para testar um agente específico")
        print("Use --list para ver cenários disponíveis")
        return

    if args.report:
        print("\n" + runner.generate_report())

    if args.export:
        runner.export_results_json(args.export)
        print(f"\nResultados exportados para {args.export}")


if __name__ == "__main__":
    main()
