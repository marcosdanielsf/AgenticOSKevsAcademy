"""
Socialfy Agent Framework
========================
Multi-agent system for Instagram lead generation and outreach.

Architecture:
- Orchestrator: Central coordinator
- Squads: Outbound, Inbound, Infrastructure
- 30+ specialized sub-agents
"""

from .base_agent import BaseAgent, AgentState, AgentMetrics, AgentCapability, Task
from .orchestrator import OrchestratorAgent

__all__ = [
    'BaseAgent',
    'AgentState',
    'AgentMetrics',
    'AgentCapability',
    'Task',
    'OrchestratorAgent'
]
