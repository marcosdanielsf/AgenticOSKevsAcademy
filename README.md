# Agentic OS

A powerful Python-based agentic operating system designed to evolve into an employee swarm with full API stack access and parallel agent execution capabilities.

## Features

### Core Components
- **Agent Base Classes**: Extensible agent framework with capability registration
- **Swarm Orchestration**: Manage and coordinate multiple agents with load balancing
- **API Integration**: Comprehensive API stack with REST, GraphQL, and WebSocket support
- **Parallel Execution**: Multi-threaded and multi-process task execution engine
- **Communication Protocols**: Message passing with Redis or in-memory buses
- **Real-time Monitoring**: Web dashboard with metrics and alerting

### Key Capabilities
- **Scalable Agent Management**: Support for 100+ concurrent agents
- **Intelligent Task Routing**: Automatic agent selection based on capabilities
- **Rate Limiting**: Built-in API rate limiting and throttling
- **Real-time Metrics**: System performance monitoring and agent health tracking
- **Flexible Communication**: Redis-backed or in-memory message passing
- **Web Dashboard**: Real-time monitoring interface with charts and alerts

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Basic Usage

```python
import asyncio
from agentic_os import AgenticOS
from core.agent_base import BaseAgent, Task, AgentCapability

# Create the OS
os = AgenticOS(use_redis=False, dashboard_port=8080)

# Start the system
await os.start()

# Create a custom agent
class MyAgent(BaseAgent):
    async def initialize(self):
        self.register_capability(AgentCapability(
            name="data_processing",
            description="Process and analyze data",
            input_schema={"data": "list"},
            output_schema={"result": "dict"}
        ))
    
    async def execute_task(self, task: Task):
        return {"result": "Task completed"}
    
    async def cleanup(self):
        pass

# Register and use the agent
agent = MyAgent()
await os.register_agent(agent)

# Submit tasks
task_id = await os.submit_task({
    "data": [1, 2, 3, 4, 5]
}, "data_processing")

# Monitor at http://localhost:8080
```

### Running the Demo

```bash
python agentic_os.py
```

Visit `http://localhost:8080` for the monitoring dashboard.

## Architecture

### Core Modules

#### `core/agent_base.py`
- Base agent classes and interfaces
- Task definitions and agent capabilities
- Agent lifecycle management

#### `core/swarm_orchestrator.py`
- Agent registration and management
- Task routing and load balancing
- Swarm-level coordination

#### `core/api_integration.py`
- HTTP, GraphQL, and WebSocket API clients
- Rate limiting and authentication
- API registry and management

#### `core/parallel_engine.py`
- Multi-threaded and multi-process execution
- Task dependency management
- Pipeline execution support

#### `core/communication.py`
- Message bus implementations (Redis/in-memory)
- Agent-to-agent communication
- Event-driven coordination

#### `core/monitoring.py`
- Real-time metrics collection
- Web dashboard with charts
- Alerting and health monitoring

## Agent Development

### Creating Custom Agents

```python
class DataAnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="DataAnalyzer")
        
        # Register what this agent can do
        self.register_capability(AgentCapability(
            name="statistical_analysis",
            description="Perform statistical analysis on datasets",
            input_schema={"data": "list", "analysis_type": "string"},
            output_schema={"statistics": "dict", "visualizations": "list"}
        ))
    
    async def initialize(self):
        # Setup agent resources
        self.analysis_tools = load_analysis_tools()
    
    async def execute_task(self, task: Task) -> Dict[str, Any]:
        if task.task_type == "statistical_analysis":
            data = task.payload["data"]
            analysis_type = task.payload.get("analysis_type", "basic")
            
            # Perform analysis
            results = await self.analyze_data(data, analysis_type)
            
            return {
                "statistics": results.stats,
                "visualizations": results.charts
            }
    
    async def cleanup(self):
        # Clean up resources
        await self.analysis_tools.cleanup()
```

### Agent Capabilities

Agents declare their capabilities using the `AgentCapability` class:

```python
capability = AgentCapability(
    name="web_scraping",
    description="Extract data from web pages",
    input_schema={
        "url": {"type": "string", "required": True},
        "selectors": {"type": "list", "required": False}
    },
    output_schema={
        "data": {"type": "dict"},
        "metadata": {"type": "dict"}
    }
)
```

## API Integration

### Adding API Clients

```python
# Add a custom API
await os.add_api_integration(
    name="my_service",
    base_url="https://api.myservice.com",
    api_key="your-api-key",
    endpoints=[
        {
            "name": "get_users",
            "url": "/users",
            "method": "GET",
            "rate_limit": 100
        },
        {
            "name": "create_user",
            "url": "/users",
            "method": "POST",
            "rate_limit": 50
        }
    ]
)

# Agents can then use the API
class APIAgent(BaseAgent):
    async def execute_task(self, task: Task):
        client = self.api_clients["my_service"]
        response = await client.call_endpoint("get_users")
        return {"users": response.data}
```

## Parallel Execution

### Batch Processing

```python
# Execute multiple tasks in parallel
tasks = [
    {"func": process_data_chunk, "args": (chunk,)}
    for chunk in data_chunks
]

results = await os.execute_parallel_tasks(tasks, mode="thread")
```

### Pipeline Execution

```python
# Create a processing pipeline
pipeline = [
    {"func": extract_data, "args": (source,)},
    {"func": transform_data, "dependencies": ["extract_data"]},
    {"func": load_data, "dependencies": ["transform_data"]}
]

pipeline_ids = await os.parallel_engine.pipeline_execution(pipeline)
```

## Communication

### Agent-to-Agent Messaging

```python
class CoordinatorAgent(BaseAgent):
    async def initialize(self):
        self.comm = CommunicationProtocol(self.id, message_bus)
        
        # Handle task requests
        self.comm.register_handler(
            MessageType.TASK_REQUEST,
            self.handle_task_request
        )
    
    async def handle_task_request(self, message: Message):
        # Process request and send response
        await self.comm.send_response(message, {
            "status": "accepted",
            "estimated_time": 30
        })
    
    async def request_work_from_peer(self, peer_id: str):
        response = await self.comm.send_request(
            peer_id,
            MessageType.TASK_REQUEST,
            {"task_type": "data_analysis", "priority": 1}
        )
        return response.payload
```

## Monitoring and Alerts

### Custom Alert Rules

```python
class CustomAlertRule(AlertRule):
    def __init__(self, threshold: int = 100):
        super().__init__(
            name="Task Queue Overload",
            severity="warning",
            message=f"Task queue size exceeded {threshold}"
        )
        self.threshold = threshold
    
    async def evaluate(self, system_metrics, agent_metrics):
        for agent_id, metrics in agent_metrics.items():
            if metrics.queue_size > self.threshold:
                return True
        return False

# Add to monitoring service
os.monitoring_service.alert_manager.add_alert_rule(CustomAlertRule(50))
```

### Dashboard Access

The monitoring dashboard provides:
- Real-time system metrics (CPU, memory, disk)
- Agent status and performance
- Task completion rates and failure tracking
- Active alerts and system health

Access at `http://localhost:8080` when running.

## Configuration

### Environment Variables

```bash
REDIS_URL=redis://localhost:6379
MAX_AGENTS=100
MAX_THREADS=50
DASHBOARD_PORT=8080
LOG_LEVEL=INFO
```

### System Limits

```python
os = AgenticOS(
    use_redis=True,
    redis_url="redis://localhost:6379",
    max_agents=200,
    max_threads=100,
    dashboard_port=9000
)
```

## Production Deployment

### Docker Setup

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "agentic_os.py"]
```

### Redis Configuration

For production, use Redis for message passing:

```python
os = AgenticOS(
    use_redis=True,
    redis_url="redis://redis:6379",
    max_agents=500,
    max_threads=200
)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License - see LICENSE file for details.# Force rebuild sáb  3 jan 2026 01:22:38 -03
# Rebuild sáb  3 jan 2026 09:26:40 -03
