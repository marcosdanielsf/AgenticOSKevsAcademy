#!/usr/bin/env python3
"""
Orchestrator Agent (Maestro)
============================
Central coordinator for all Socialfy sub-agents.

Responsibilities:
- Route tasks to appropriate agents
- Manage agent lifecycle
- Coordinate multi-step workflows
- Monitor system health
- Handle failover and recovery

Architecture (6 Squads, 23 Agents):
├── OUTBOUND SQUAD (Active Lead Hunt) - 5 agents
│   ├── Lead Discovery Agent
│   ├── Profile Analyzer Agent
│   ├── Lead Qualifier Agent
│   ├── Message Composer Agent
│   └── Outreach Executor Agent
│
├── INBOUND SQUAD (Lead Comes to Us) - 3 agents
│   ├── Inbox Monitor Agent
│   ├── Lead Classifier Agent
│   └── Auto Responder Agent
│
├── INFRASTRUCTURE SQUAD (Support) - 3 agents
│   ├── Account Manager Agent
│   ├── Analytics Agent
│   └── Error Handler Agent
│
├── SECURITY SQUAD (Protection) - 4 agents
│   ├── Rate Limit Guard Agent
│   ├── Session Security Agent
│   ├── Anti-Detection Agent
│   └── Compliance Agent
│
├── PERFORMANCE SQUAD (Optimization) - 4 agents
│   ├── Cache Manager Agent
│   ├── Batch Processor Agent
│   ├── Queue Manager Agent
│   └── Load Balancer Agent
│
└── QUALITY SQUAD (Quality Assurance) - 4 agents
    ├── Data Validator Agent
    ├── Message Quality Agent
    ├── Deduplication Agent
    └── Audit Logger Agent
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from .base_agent import BaseAgent, Task, TaskStatus, TaskPriority, AgentCapability, AgentState


@dataclass
class WorkflowStep:
    """Represents a step in a workflow"""
    agent_name: str
    task_type: str
    payload_transform: Optional[Callable] = None
    condition: Optional[Callable] = None
    on_success: Optional[str] = None  # Next step name
    on_failure: Optional[str] = None  # Fallback step name


@dataclass
class Workflow:
    """Represents a multi-step workflow"""
    name: str
    steps: List[WorkflowStep] = field(default_factory=list)
    current_step: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"


class OrchestratorAgent(BaseAgent):
    """
    Central orchestrator that coordinates all Socialfy agents.
    Routes tasks, manages workflows, and ensures system reliability.
    """

    # Squad definitions (6 squads, 23 agents)
    SQUAD_OUTBOUND = "outbound"
    SQUAD_INBOUND = "inbound"
    SQUAD_INFRASTRUCTURE = "infrastructure"
    SQUAD_SECURITY = "security"
    SQUAD_PERFORMANCE = "performance"
    SQUAD_QUALITY = "quality"

    def __init__(self, config: Dict = None):
        super().__init__(
            name="Orchestrator",
            description="Central coordinator for all Socialfy agents",
            max_concurrent_tasks=10
        )

        self.config = config or {}

        # Agent registry by squad (6 squads)
        self.squads: Dict[str, Dict[str, BaseAgent]] = {
            self.SQUAD_OUTBOUND: {},
            self.SQUAD_INBOUND: {},
            self.SQUAD_INFRASTRUCTURE: {},
            self.SQUAD_SECURITY: {},
            self.SQUAD_PERFORMANCE: {},
            self.SQUAD_QUALITY: {}
        }

        # Task routing table
        self._task_routes: Dict[str, str] = {}

        # Active workflows
        self._workflows: Dict[str, Workflow] = {}

        # System metrics
        self._system_metrics = {
            "total_tasks_routed": 0,
            "active_agents": 0,
            "workflows_completed": 0,
            "workflows_failed": 0
        }

        # Register capabilities
        self.register_capability(AgentCapability(
            name="orchestration",
            description="Task routing and workflow coordination",
            task_types=[
                "route_task",
                "execute_workflow",
                "system_health",
                "agent_status"
            ]
        ))

    async def _on_initialize(self):
        """Initialize orchestrator and all agents"""
        self.logger.info("Initializing Orchestrator and all squads...")

        # Initialize all registered agents
        for squad_name, agents in self.squads.items():
            for agent_name, agent in agents.items():
                try:
                    await agent.initialize()
                    self.logger.info(f"  [{squad_name}] {agent_name}: ready")
                except Exception as e:
                    self.logger.error(f"  [{squad_name}] {agent_name}: failed - {e}")

        self._update_agent_count()
        self.logger.info(f"Orchestrator ready with {self._system_metrics['active_agents']} agents")

    async def _on_cleanup(self):
        """Cleanup all agents"""
        for squad_name, agents in self.squads.items():
            for agent in agents.values():
                await agent.cleanup()

    # =========================================
    # AGENT REGISTRATION
    # =========================================

    def register_agent(self, agent: BaseAgent, squad: str):
        """Register an agent to a squad"""
        if squad not in self.squads:
            self.logger.warning(f"Unknown squad: {squad}")
            return

        self.squads[squad][agent.name] = agent
        self._sub_agents[agent.name] = agent

        # Register task routes for this agent
        for cap in agent.capabilities:
            for task_type in cap.task_types:
                self._task_routes[task_type] = agent.name

        self.logger.info(f"Registered {agent.name} to {squad} squad")
        self._update_agent_count()

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get agent by name"""
        return self._sub_agents.get(name)

    def get_squad_agents(self, squad: str) -> Dict[str, BaseAgent]:
        """Get all agents in a squad"""
        return self.squads.get(squad, {})

    def _update_agent_count(self):
        """Update active agent count"""
        count = sum(len(agents) for agents in self.squads.values())
        self._system_metrics["active_agents"] = count

    # =========================================
    # TASK EXECUTION & ROUTING
    # =========================================

    async def execute_task(self, task: Task) -> Any:
        """Execute or route a task"""
        task_type = task.task_type

        # Handle orchestrator-specific tasks
        if task_type == "route_task":
            return await self._route_task(task)
        elif task_type == "execute_workflow":
            return await self._execute_workflow(task)
        elif task_type == "system_health":
            return self._get_system_health()
        elif task_type == "agent_status":
            return self._get_agent_status(task.payload.get("agent_name"))

        # Route to appropriate agent
        agent_name = self._task_routes.get(task_type)
        if agent_name:
            return await self._delegate_to_agent(agent_name, task)

        raise ValueError(f"No handler for task type: {task_type}")

    async def _route_task(self, task: Task) -> Dict:
        """Route a task to the appropriate agent"""
        inner_task_type = task.payload.get("task_type")
        inner_payload = task.payload.get("payload", {})

        agent_name = self._task_routes.get(inner_task_type)
        if not agent_name:
            return {"success": False, "error": f"No agent for: {inner_task_type}"}

        inner_task = Task(
            task_type=inner_task_type,
            payload=inner_payload,
            priority=TaskPriority(task.payload.get("priority", 3))
        )

        result = await self._delegate_to_agent(agent_name, inner_task)
        self._system_metrics["total_tasks_routed"] += 1

        return {"success": True, "agent": agent_name, "result": result}

    async def _delegate_to_agent(self, agent_name: str, task: Task) -> Any:
        """Delegate task to a specific agent"""
        agent = self._sub_agents.get(agent_name)
        if not agent:
            raise ValueError(f"Agent not found: {agent_name}")

        # Start agent if not running
        if agent.state != AgentState.RUNNING:
            await agent.start()

        # Submit and wait for result
        await agent.submit_task(task)

        # Wait for task completion (with timeout)
        timeout = task.timeout_seconds
        start_time = asyncio.get_event_loop().time()

        while task.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.RETRYING]:
            await asyncio.sleep(0.1)
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(f"Task {task.id} timed out")

        if task.status == TaskStatus.FAILED:
            raise Exception(task.error or "Task failed")

        return task.result

    # =========================================
    # WORKFLOW EXECUTION
    # =========================================

    async def _execute_workflow(self, task: Task) -> Dict:
        """Execute a multi-step workflow"""
        workflow_name = task.payload.get("workflow_name")
        workflow_context = task.payload.get("context", {})

        workflow = self._create_workflow(workflow_name, workflow_context)
        if not workflow:
            return {"success": False, "error": f"Unknown workflow: {workflow_name}"}

        self._workflows[workflow.name] = workflow
        workflow.status = "running"

        try:
            while workflow.current_step < len(workflow.steps):
                step = workflow.steps[workflow.current_step]

                # Check condition
                if step.condition and not step.condition(workflow.context):
                    workflow.current_step += 1
                    continue

                # Prepare payload
                payload = workflow.context.copy()
                if step.payload_transform:
                    payload = step.payload_transform(payload)

                # Execute step
                step_task = Task(
                    task_type=step.task_type,
                    payload=payload
                )

                try:
                    result = await self._delegate_to_agent(step.agent_name, step_task)
                    workflow.context["last_result"] = result
                    workflow.context[f"step_{workflow.current_step}_result"] = result
                    workflow.current_step += 1

                except Exception as e:
                    self.logger.error(f"Workflow step failed: {e}")
                    if step.on_failure:
                        # Jump to failure handler
                        for i, s in enumerate(workflow.steps):
                            if s.agent_name == step.on_failure:
                                workflow.current_step = i
                                break
                    else:
                        raise

            workflow.status = "completed"
            self._system_metrics["workflows_completed"] += 1

            return {
                "success": True,
                "workflow": workflow_name,
                "result": workflow.context
            }

        except Exception as e:
            workflow.status = "failed"
            self._system_metrics["workflows_failed"] += 1
            return {"success": False, "error": str(e)}

    def _create_workflow(self, name: str, context: Dict) -> Optional[Workflow]:
        """Create a workflow by name"""

        # Pre-defined workflows
        workflows = {
            "outbound_lead_pipeline": self._workflow_outbound_lead,
            "inbound_message_handler": self._workflow_inbound_message,
            "full_enrichment": self._workflow_full_enrichment
        }

        creator = workflows.get(name)
        if creator:
            return creator(context)
        return None

    def _workflow_outbound_lead(self, context: Dict) -> Workflow:
        """OUTBOUND: Complete lead pipeline workflow"""
        return Workflow(
            name="outbound_lead_pipeline",
            steps=[
                WorkflowStep(
                    agent_name="ProfileAnalyzer",
                    task_type="scrape_profile",
                    payload_transform=lambda c: {"username": c.get("username")}
                ),
                WorkflowStep(
                    agent_name="LeadQualifier",
                    task_type="qualify_lead",
                    payload_transform=lambda c: {
                        "username": c.get("username"),
                        "profile": c.get("last_result")
                    }
                ),
                WorkflowStep(
                    agent_name="MessageComposer",
                    task_type="compose_message",
                    condition=lambda c: c.get("last_result", {}).get("score", 0) >= 50,
                    payload_transform=lambda c: {
                        "username": c.get("username"),
                        "profile": c.get("step_0_result"),
                        "qualification": c.get("last_result")
                    }
                ),
                WorkflowStep(
                    agent_name="OutreachExecutor",
                    task_type="send_dm",
                    condition=lambda c: c.get("last_result", {}).get("message"),
                    payload_transform=lambda c: {
                        "username": c.get("username"),
                        "message": c.get("last_result", {}).get("message")
                    }
                )
            ],
            context=context
        )

    def _workflow_inbound_message(self, context: Dict) -> Workflow:
        """INBOUND: Handle incoming message workflow"""
        return Workflow(
            name="inbound_message_handler",
            steps=[
                WorkflowStep(
                    agent_name="LeadClassifier",
                    task_type="classify_lead",
                    payload_transform=lambda c: {
                        "username": c.get("username"),
                        "message": c.get("message"),
                        "tenant_id": c.get("tenant_id")
                    }
                ),
                WorkflowStep(
                    agent_name="ProfileAnalyzer",
                    task_type="scrape_profile",
                    condition=lambda c: c.get("last_result", {}).get("needs_profile"),
                    payload_transform=lambda c: {"username": c.get("username")}
                ),
                WorkflowStep(
                    agent_name="AutoResponder",
                    task_type="generate_response",
                    condition=lambda c: c.get("step_0_result", {}).get("classification") != "SPAM",
                    payload_transform=lambda c: {
                        "username": c.get("username"),
                        "original_message": c.get("message"),
                        "classification": c.get("step_0_result"),
                        "profile": c.get("step_1_result")
                    }
                )
            ],
            context=context
        )

    def _workflow_full_enrichment(self, context: Dict) -> Workflow:
        """Enrich a lead with all available data"""
        return Workflow(
            name="full_enrichment",
            steps=[
                WorkflowStep(
                    agent_name="ProfileAnalyzer",
                    task_type="scrape_profile",
                    payload_transform=lambda c: {"username": c.get("username")}
                ),
                WorkflowStep(
                    agent_name="LeadQualifier",
                    task_type="qualify_lead"
                ),
                WorkflowStep(
                    agent_name="Analytics",
                    task_type="save_enriched_lead"
                )
            ],
            context=context
        )

    # =========================================
    # SYSTEM HEALTH & STATUS
    # =========================================

    def _get_system_health(self) -> Dict:
        """Get overall system health"""
        agents_health = {}
        total_tasks = 0
        total_errors = 0

        for squad_name, agents in self.squads.items():
            for agent_name, agent in agents.items():
                status = agent.get_status()
                agents_health[agent_name] = {
                    "squad": squad_name,
                    "state": status["state"],
                    "tasks_completed": status["metrics"]["tasks_completed"],
                    "tasks_failed": status["metrics"]["tasks_failed"],
                    "success_rate": status["metrics"]["success_rate"]
                }
                total_tasks += status["metrics"]["tasks_completed"]
                total_errors += status["metrics"]["tasks_failed"]

        return {
            "status": "healthy" if total_errors == 0 else "degraded",
            "timestamp": datetime.now().isoformat(),
            "system_metrics": self._system_metrics,
            "total_tasks_processed": total_tasks,
            "total_errors": total_errors,
            "overall_success_rate": total_tasks / max(1, total_tasks + total_errors),
            "agents": agents_health,
            "active_workflows": len([w for w in self._workflows.values() if w.status == "running"])
        }

    def _get_agent_status(self, agent_name: str) -> Dict:
        """Get status of a specific agent"""
        agent = self._sub_agents.get(agent_name)
        if agent:
            return agent.get_status()
        return {"error": f"Agent not found: {agent_name}"}

    # =========================================
    # CONVENIENCE METHODS
    # =========================================

    async def process_outbound_lead(self, username: str, tenant_id: str = None) -> Dict:
        """Process a single outbound lead through the full pipeline"""
        task = Task(
            task_type="execute_workflow",
            payload={
                "workflow_name": "outbound_lead_pipeline",
                "context": {
                    "username": username,
                    "tenant_id": tenant_id
                }
            }
        )
        return await self.execute_task(task)

    async def process_inbound_message(
        self,
        username: str,
        message: str,
        tenant_id: str
    ) -> Dict:
        """Process an inbound message through classification and response"""
        task = Task(
            task_type="execute_workflow",
            payload={
                "workflow_name": "inbound_message_handler",
                "context": {
                    "username": username,
                    "message": message,
                    "tenant_id": tenant_id
                }
            }
        )
        return await self.execute_task(task)

    async def enrich_lead(self, username: str) -> Dict:
        """Fully enrich a lead"""
        task = Task(
            task_type="execute_workflow",
            payload={
                "workflow_name": "full_enrichment",
                "context": {"username": username}
            }
        )
        return await self.execute_task(task)

    # =========================================
    # BATCH OPERATIONS
    # =========================================

    async def process_leads_batch(
        self,
        usernames: List[str],
        workflow: str = "outbound_lead_pipeline",
        concurrency: int = 3
    ) -> List[Dict]:
        """Process multiple leads concurrently"""
        semaphore = asyncio.Semaphore(concurrency)
        results = []

        async def process_one(username: str):
            async with semaphore:
                task = Task(
                    task_type="execute_workflow",
                    payload={
                        "workflow_name": workflow,
                        "context": {"username": username}
                    }
                )
                return await self.execute_task(task)

        tasks = [process_one(u) for u in usernames]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [
            {"username": u, "result": r if not isinstance(r, Exception) else {"error": str(r)}}
            for u, r in zip(usernames, results)
        ]
