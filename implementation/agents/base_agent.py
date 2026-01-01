#!/usr/bin/env python3
"""
Base Agent Framework
====================
Foundation for all Socialfy agents.

Features:
- Async execution
- State management
- Metrics collection
- Error handling with retry
- Inter-agent communication
"""

import asyncio
import logging
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from uuid import uuid4
import time


class AgentState(Enum):
    """Agent lifecycle states"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class Task:
    """Represents a task to be executed by an agent"""
    id: str = field(default_factory=lambda: str(uuid4()))
    task_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "task_type": self.task_type,
            "payload": self.payload,
            "priority": self.priority.name,
            "status": self.status.name,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "retry_count": self.retry_count
        }


@dataclass
class AgentCapability:
    """Defines what an agent can do"""
    name: str
    description: str
    task_types: List[str] = field(default_factory=list)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    requires_browser: bool = False
    requires_api_key: Optional[str] = None
    rate_limit_per_minute: int = 60


@dataclass
class AgentMetrics:
    """Agent performance metrics"""
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_execution_time_ms: float = 0
    avg_execution_time_ms: float = 0
    last_error: Optional[str] = None
    last_success_at: Optional[str] = None
    uptime_seconds: float = 0
    start_time: Optional[str] = None

    def record_success(self, execution_time_ms: float):
        self.tasks_completed += 1
        self.total_execution_time_ms += execution_time_ms
        self.avg_execution_time_ms = self.total_execution_time_ms / self.tasks_completed
        self.last_success_at = datetime.now().isoformat()

    def record_failure(self, error: str):
        self.tasks_failed += 1
        self.last_error = error

    def to_dict(self) -> Dict:
        return {
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "success_rate": self.tasks_completed / max(1, self.tasks_completed + self.tasks_failed),
            "avg_execution_time_ms": round(self.avg_execution_time_ms, 2),
            "last_error": self.last_error,
            "last_success_at": self.last_success_at,
            "uptime_seconds": round(self.uptime_seconds, 2)
        }


class BaseAgent(ABC):
    """
    Base class for all Socialfy agents.

    Provides:
    - Lifecycle management (initialize, run, cleanup)
    - Task queue with priority
    - Metrics collection
    - Error handling with exponential backoff retry
    - Sub-agent coordination
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        max_concurrent_tasks: int = 1,
        logger: Optional[logging.Logger] = None
    ):
        self.id = str(uuid4())
        self.name = name
        self.description = description
        self.max_concurrent_tasks = max_concurrent_tasks

        # State
        self.state = AgentState.IDLE
        self.metrics = AgentMetrics()
        self.capabilities: List[AgentCapability] = []

        # Task management
        self._task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._active_tasks: Dict[str, Task] = {}
        self._task_history: List[Task] = []

        # Sub-agents
        self._sub_agents: Dict[str, 'BaseAgent'] = {}

        # Callbacks
        self._on_task_complete: Optional[Callable] = None
        self._on_error: Optional[Callable] = None

        # Logging
        self.logger = logger or logging.getLogger(f"Agent.{name}")

        # Control
        self._running = False
        self._shutdown_event = asyncio.Event()

    # =========================================
    # LIFECYCLE METHODS
    # =========================================

    async def initialize(self) -> bool:
        """Initialize the agent. Override in subclass."""
        self.state = AgentState.INITIALIZING
        self.metrics.start_time = datetime.now().isoformat()

        try:
            await self._on_initialize()
            self.state = AgentState.READY
            self.logger.info(f"Agent {self.name} initialized")
            return True
        except Exception as e:
            self.state = AgentState.ERROR
            self.logger.error(f"Failed to initialize: {e}")
            return False

    @abstractmethod
    async def _on_initialize(self):
        """Override: Custom initialization logic"""
        pass

    async def start(self):
        """Start the agent's task processing loop"""
        if self.state != AgentState.READY:
            await self.initialize()

        self._running = True
        self.state = AgentState.RUNNING
        self.logger.info(f"Agent {self.name} started")

        # Start task processor
        asyncio.create_task(self._process_tasks())

    async def stop(self):
        """Stop the agent gracefully"""
        self._running = False
        self._shutdown_event.set()
        self.state = AgentState.STOPPED
        self.logger.info(f"Agent {self.name} stopped")

        # Stop sub-agents
        for sub_agent in self._sub_agents.values():
            await sub_agent.stop()

    async def cleanup(self):
        """Cleanup resources. Override in subclass."""
        await self._on_cleanup()
        self.logger.info(f"Agent {self.name} cleaned up")

    async def _on_cleanup(self):
        """Override: Custom cleanup logic"""
        pass

    # =========================================
    # TASK EXECUTION
    # =========================================

    async def submit_task(self, task: Task) -> str:
        """Submit a task for execution"""
        await self._task_queue.put((task.priority.value, task.created_at, task))
        self.logger.debug(f"Task {task.id} submitted: {task.task_type}")
        return task.id

    async def _process_tasks(self):
        """Main task processing loop"""
        while self._running:
            try:
                # Wait for a task
                try:
                    priority, created_at, task = await asyncio.wait_for(
                        self._task_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Execute task
                await self._execute_task(task)

            except Exception as e:
                self.logger.error(f"Error in task loop: {e}")
                await asyncio.sleep(1)

    async def _execute_task(self, task: Task):
        """Execute a single task with error handling and retry"""
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now().isoformat()
        self._active_tasks[task.id] = task

        start_time = time.time()

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                self.execute_task(task),
                timeout=task.timeout_seconds
            )

            # Success
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.now().isoformat()

            execution_time = (time.time() - start_time) * 1000
            self.metrics.record_success(execution_time)

            self.logger.info(f"Task {task.id} completed in {execution_time:.0f}ms")

            if self._on_task_complete:
                await self._on_task_complete(task)

        except asyncio.TimeoutError:
            task.error = "Task timeout"
            await self._handle_task_failure(task)

        except Exception as e:
            task.error = str(e)
            self.logger.error(f"Task {task.id} failed: {e}\n{traceback.format_exc()}")
            await self._handle_task_failure(task)

        finally:
            self._active_tasks.pop(task.id, None)
            self._task_history.append(task)

    async def _handle_task_failure(self, task: Task):
        """Handle task failure with retry logic"""
        self.metrics.record_failure(task.error)

        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = TaskStatus.RETRYING

            # Exponential backoff
            delay = 2 ** task.retry_count
            self.logger.warning(f"Retrying task {task.id} in {delay}s (attempt {task.retry_count}/{task.max_retries})")

            await asyncio.sleep(delay)
            await self.submit_task(task)
        else:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now().isoformat()

            if self._on_error:
                await self._on_error(task)

    @abstractmethod
    async def execute_task(self, task: Task) -> Any:
        """
        Execute a task. Must be implemented by subclass.

        Args:
            task: Task to execute

        Returns:
            Task result

        Raises:
            Exception if task fails
        """
        pass

    # =========================================
    # SUB-AGENT MANAGEMENT
    # =========================================

    def register_sub_agent(self, agent: 'BaseAgent'):
        """Register a sub-agent"""
        self._sub_agents[agent.name] = agent
        self.logger.info(f"Registered sub-agent: {agent.name}")

    def get_sub_agent(self, name: str) -> Optional['BaseAgent']:
        """Get a sub-agent by name"""
        return self._sub_agents.get(name)

    async def delegate_task(self, agent_name: str, task: Task) -> Optional[str]:
        """Delegate a task to a sub-agent"""
        agent = self._sub_agents.get(agent_name)
        if agent:
            return await agent.submit_task(task)
        else:
            self.logger.warning(f"Sub-agent not found: {agent_name}")
            return None

    # =========================================
    # CAPABILITIES
    # =========================================

    def register_capability(self, capability: AgentCapability):
        """Register an agent capability"""
        self.capabilities.append(capability)

    def can_handle(self, task_type: str) -> bool:
        """Check if agent can handle a task type"""
        for cap in self.capabilities:
            if task_type in cap.task_types:
                return True
        return False

    # =========================================
    # STATUS & METRICS
    # =========================================

    def get_status(self) -> Dict:
        """Get agent status"""
        # Update uptime
        if self.metrics.start_time:
            start = datetime.fromisoformat(self.metrics.start_time)
            self.metrics.uptime_seconds = (datetime.now() - start).total_seconds()

        return {
            "id": self.id,
            "name": self.name,
            "state": self.state.value,
            "active_tasks": len(self._active_tasks),
            "queue_size": self._task_queue.qsize(),
            "sub_agents": list(self._sub_agents.keys()),
            "capabilities": [cap.name for cap in self.capabilities],
            "metrics": self.metrics.to_dict()
        }

    def get_metrics(self) -> AgentMetrics:
        """Get agent metrics"""
        return self.metrics

    # =========================================
    # CALLBACKS
    # =========================================

    def on_task_complete(self, callback: Callable):
        """Set callback for task completion"""
        self._on_task_complete = callback

    def on_error(self, callback: Callable):
        """Set callback for errors"""
        self._on_error = callback


class SimpleAgent(BaseAgent):
    """
    Simple agent that executes tasks via a handler function.
    Useful for quick agent creation without subclassing.
    """

    def __init__(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        task_types: List[str] = None
    ):
        super().__init__(name, description)
        self.handler = handler

        if task_types:
            self.register_capability(AgentCapability(
                name=f"{name}_capability",
                description=description,
                task_types=task_types
            ))

    async def _on_initialize(self):
        pass

    async def execute_task(self, task: Task) -> Any:
        if asyncio.iscoroutinefunction(self.handler):
            return await self.handler(task)
        else:
            return self.handler(task)


# Utility functions

def create_agent(
    name: str,
    handler: Callable,
    description: str = "",
    task_types: List[str] = None
) -> SimpleAgent:
    """Factory function to create a simple agent"""
    return SimpleAgent(name, handler, description, task_types)
