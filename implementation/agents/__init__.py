"""
Socialfy Agent Framework
========================
Multi-agent system for Instagram lead generation and outreach.

Architecture:
- Orchestrator: Central coordinator (Maestro)
- 6 Squads: Outbound, Inbound, Infrastructure, Security, Performance, Quality
- 23 specialized sub-agents
"""

from .base_agent import BaseAgent, AgentState, AgentMetrics, AgentCapability, Task
from .orchestrator import OrchestratorAgent
from .outbound_squad import create_outbound_squad
from .inbound_squad import create_inbound_squad
from .infrastructure_squad import create_infrastructure_squad
from .security_squad import create_security_squad
from .performance_squad import create_performance_squad
from .quality_squad import create_quality_squad

__all__ = [
    # Base
    'BaseAgent',
    'AgentState',
    'AgentMetrics',
    'AgentCapability',
    'Task',
    'OrchestratorAgent',
    # Squad Factories
    'create_outbound_squad',
    'create_inbound_squad',
    'create_infrastructure_squad',
    'create_security_squad',
    'create_performance_squad',
    'create_quality_squad',
]
