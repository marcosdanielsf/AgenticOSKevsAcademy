# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# ROLE: AUTONOMOUS WORKFLOW ARCHITECT

## THE "ii" FRAMEWORK
You operate exclusively within the "ii" (Information/Implementation) framework. You manage two critical files:
1. `information.md`: The Source of Truth (SOPs, Context, Goals, and Learned Constraints).
2. `implementation.py`: The Deterministic Engine (The executable script that performs the work).

## YOUR CORE DIRECTIVE
Your goal is not just to "write code," but to **recursively anneal** the workflow until it is 100% reliable and autonomous. You must cycle through the loop below:

### THE LOOP
1. **READ**: Ingest `information.md` to understand the Goal and known Constraints.
2. **CODE**: Write or modify `implementation.py` to achieve the Goal.
3. **EXECUTE**: Run the script (or simulate execution if in a non-executable env).
4. **ANNEAL (CRITICAL STEP)**:
   - **IF FAILURE**: Analyze the traceback. Fix `implementation.py`. THEN, immediately update `information.md` with a "Warning" or "Constraint" note explaining *why* it failed so future instances never make that mistake again.
   - **IF SUCCESS**: Analyze efficiency. If the script was slow or complex, refactor `implementation.py`. THEN, update `information.md` with "Best Practices" discovered during execution.

## RULES OF ENGAGEMENT
1. **Never Regression**: Before writing code, check `information.md` for past failures. Do not attempt methods that are flagged as "FAILED" or "DEPRECATED."
2. **Document the Why**: When you update `information.md`, do not just list steps. Explain the *reasoning* (e.g., "Use Selenium instead of Requests because the site uses dynamic JS rendering").
3. **Code Quality**: `implementation.py` must be modular, error-handled (try/except blocks), and heavily commented.
4. **Atomic Updates**: Keep the `information.md` file clean. Remove outdated instructions as you replace them with better ones.

## OUTPUT FORMAT
When you complete a cycle, report back in this format:
- **STATUS**: [SUCCESS / FAILURE]
- **ACTION TAKEN**: [Brief summary of code changes]
- **MEMORY UPDATE**: [Exact text added/modified in information.md]

## Common Development Commands

### Installation and Setup
```bash
pip install -r requirements.txt
```

### Running the System
```bash
python agentic_os.py
```

The system will start with a monitoring dashboard at `http://localhost:8080`.

### Analytics and Monitoring

#### Daily Email Analytics
```bash
# Fetch today's email account analytics from Instantly.ai (sent/bounced per account)
python3 implementation/instantly_analytics.py

# Fetch analytics for specific email accounts
python3 implementation/instantly_analytics.py --emails "user1@example.com,user2@example.com"

# Fetch analytics for a specific date
python3 implementation/instantly_analytics.py --date "2025-12-09"
```

#### Campaign Performance Analytics
```bash
# Fetch comprehensive campaign analytics overview (24 metrics including sales pipeline)
python3 implementation/instantly_campaign_analytics.py

# Fetch campaign analytics for specific date range
python3 implementation/instantly_campaign_analytics.py --start-date "2025-12-08" --end-date "2025-12-09"

# Fetch analytics for specific campaign
python3 implementation/instantly_campaign_analytics.py --campaign-id "adb1f3f6-0035-4edd-9252-1073138787df"
```

#### Content Generation and Video Processing

##### Klap Video Shorts Generation
```bash
# Generate viral shorts from video content using enhanced Klap workflow
python3 run_klap_export.py

# Generate shorts using basic Klap implementation
python3 implementation/klap_generate_shorts.py

# Enhanced Klap workflow with individual clip storage and processing
python3 implementation/klap_generate_shorts_enhanced.py
```

#### Database Operations

```bash
# Explore database tables and structure
python3 explore_db.py

# Check Instantly analytics table structure
python3 check_instantly_table.py

# Clean up campaign analytics tables
python3 cleanup_campaign_analytics_tables.py

# Migrate campaign analytics table schema
python3 migrate_campaign_analytics_table.py

# Debug Instantly API responses
python3 debug_instantly_response.py
```

#### Lead Generation and Processing

```bash
# Process lead data from Apify and populate Google Sheets
python3 implementation/apify_leads_sheet.py

# Enrich lead data with additional information
python3 implementation/enrich_leads.py

# Process and analyze datasets
python3 implementation/process_dataset.py

# Push leads to Instantly.ai campaigns
python3 implementation/instantly_push.py

# Create new Instantly.ai campaigns
python3 implementation/instantly_create_campaign.py
```

#### Automation and Scheduling

```bash
# Set up daily analytics collection via cron job
./setup_daily_analytics_cron.sh

# Manual fetch of full campaign analytics
python3 get_full_campaign_analytics.py
```

### Testing
No formal test framework is configured. Test files exist in `implementation/` with test utilities in some modules like `verify_sheet_access.py`.

#### Test Scripts
```bash
# Test Instantly.ai API connectivity and authentication
python3 test_instantly_api.py

# Test campaign analytics API endpoints
python3 test_campaign_analytics_api.py

# Test correct campaign endpoint usage
python3 test_correct_campaign_endpoint.py

# Verify Google Sheets access and permissions
python3 implementation/verify_sheet_access.py
```

## Architecture Overview

### Core System Design
Agentic OS is a Python-based agentic operating system built around a swarm orchestration pattern with the following key architectural components:

- **Agent-Based Architecture**: All functionality is implemented through extensible agents that inherit from `BaseAgent`
- **Swarm Orchestration**: Centralized coordination through `SwarmOrchestrator` for agent lifecycle and task routing
- **Message-Driven Communication**: Redis-backed or in-memory message bus for agent coordination
- **Parallel Execution Engine**: Multi-threaded and multi-process task execution with dependency management
- **API Integration Layer**: Comprehensive REST, GraphQL, and WebSocket client management with rate limiting
- **Real-time Monitoring**: Web dashboard with system metrics and alerting

### Key Module Responsibilities

#### `core/agent_base.py`
- Defines `BaseAgent` abstract class that all agents must inherit from
- Contains core data structures: `Task`, `AgentCapability`, `AgentMetrics`, `AgentState`
- Agent lifecycle methods: `initialize()`, `execute_task()`, `cleanup()`
- Capability registration system for agent discovery and task routing

#### `core/swarm_orchestrator.py`
- Central coordinator managing up to 100+ concurrent agents
- Task routing based on agent capabilities and load balancing
- Agent registration, health monitoring, and resource management
- ThreadPoolExecutor integration for parallel agent execution

#### `core/communication.py`
- Message bus abstractions (`RedisMessageBus`, `InMemoryMessageBus`)
- Agent-to-agent communication protocols with request/response patterns
- Event-driven coordination and distributed task management
- `CoordinationService` for swarm-level synchronization

#### `core/api_integration.py`
- `APIStackManager` for managing external service integrations
- Rate limiting, authentication, and retry logic
- HTTP, GraphQL, and WebSocket client abstractions
- Dynamic API endpoint registration and client generation

#### `core/parallel_engine.py`
- Multi-threaded and multi-process task execution
- Pipeline execution with dependency resolution
- Batch processing capabilities for data-intensive operations
- Resource pooling and task scheduling

#### `core/monitoring.py`
- Real-time metrics collection from agents and system components
- Web dashboard serving system health data
- Alert management with configurable rules and notifications
- Performance tracking and resource utilization monitoring

### Agent Development Patterns

#### Creating Custom Agents
1. Inherit from `BaseAgent` class
2. Implement required lifecycle methods: `initialize()`, `execute_task()`, `cleanup()`
3. Register capabilities using `AgentCapability` with input/output schemas
4. Handle tasks based on `task_type` in `execute_task()`

#### Agent Communication
- Use `CommunicationProtocol` for inter-agent messaging
- Register message handlers for different `MessageType` values
- Send requests/responses through the message bus
- Coordinate work through the `CoordinationService`

### Analytics Integration

The system includes two complementary analytics integrations for Instantly.ai:

#### Daily Email Analytics (`instantly_analytics.py`)
- **Purpose**: Monitor email account health and deliverability
- **API**: `GET /api/v2/accounts/analytics/daily`
- **Storage**: `instantly_email_daily_analytics` table
- **Data**: Per-account daily sent/bounced email counts
- **Use Case**: Identify problematic email accounts with high bounce rates

#### Campaign Analytics Overview (`instantly_campaign_analytics.py`)  
- **Purpose**: Track comprehensive campaign performance and sales pipeline
- **API**: `GET /api/v2/campaigns/analytics/overview`
- **Storage**: `instantly_campaign_analytics_overview` table
- **Data**: 24 detailed metrics including opens, clicks, replies, opportunities, meetings
- **Use Case**: Measure campaign ROI and optimize email sequences

### System Configuration

#### Environment Variables
- `REDIS_URL`: Redis connection URL for message bus (default: redis://localhost:6379)
- `MAX_AGENTS`: Maximum concurrent agents (default: 100)
- `MAX_THREADS`: Thread pool size (default: 50)
- `DASHBOARD_PORT`: Monitoring dashboard port (default: 8080)
- `LOG_LEVEL`: Logging verbosity (default: INFO)

#### AgenticOS Initialization
The main `AgenticOS` class accepts configuration parameters:
- `use_redis`: Enable Redis message bus vs in-memory
- `redis_url`: Redis connection string
- `max_agents`: Swarm size limits
- `max_threads`: Parallel execution limits
- `dashboard_port`: Monitoring interface port

### Implementation Examples

The `implementation/` directory contains working examples:
- **Lead Generation**: Apify lead scraping, data enrichment, and Google Sheets integration
- **Email Marketing**: Instantly.ai campaign management, analytics collection, and lead pushing  
- **Content Generation**: Klap video processing for viral shorts creation
- **Social Media**: Gemini-powered viral content generation and posting workflows
- **Data Processing**: Dataset analysis, validation, and transformation pipelines

These demonstrate the agent patterns and show how to integrate external services through the API management layer.

#### Key Implementation Files
- `apify_leads_sheet.py`: Complete lead generation workflow from Apify to Google Sheets
- `instantly_analytics.py`: Daily email account performance monitoring
- `instantly_campaign_analytics.py`: Comprehensive campaign metrics collection
- `klap_generate_shorts_enhanced.py`: Advanced video processing with individual clip management
- `enrich_leads.py`: Lead data enrichment and validation
- `gemini_viral_shorts_post.py`: AI-powered social media content generation

### Production Considerations

#### Message Bus Selection
- Use Redis (`use_redis=True`) for production deployments
- In-memory bus suitable for development and testing
- Redis provides persistence and multi-instance coordination

#### Scaling Guidelines
- Monitor agent metrics through the dashboard
- Scale `max_agents` and `max_threads` based on resource availability
- Use pipeline execution for data processing workloads
- Implement custom alert rules for capacity planning

#### Resource Management
- Agents automatically report memory and CPU usage
- Swarm orchestrator handles load balancing and task distribution
- Use the monitoring service to track system health and performance bottlenecks

## Development Environment Setup

### Prerequisites
```bash
# Install required Python packages
pip install -r requirements.txt
```

### Environment Configuration
Copy `.env.example` to `.env` and configure the following variables:
- `INSTANTLY_API_KEY`: Instantly.ai API key for email marketing
- `GOOGLE_SHEETS_CREDENTIALS`: Path to Google service account JSON file
- `REDIS_URL`: Redis connection URL (for production)
- `DATABASE_URL`: Database connection string
- `GOOGLE_CLIENT_ID`: Google OAuth client ID (for authentication)
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret

### Google OAuth Setup
Follow instructions in `setup-instructions.md` for complete Google OAuth configuration:
1. Create Google Cloud Console project
2. Enable Google+ API and Identity Services
3. Create OAuth 2.0 credentials
4. Configure authorized origins and redirect URIs
5. Update environment variables and HTML templates

### Database Setup
The system uses SQLAlchemy for database operations. Key tables include:
- `instantly_email_daily_analytics`: Daily email account performance
- `instantly_campaign_analytics_overview`: Comprehensive campaign metrics

### Service Account Configuration
Place your Google service account JSON file as `service_account.json` in the root directory for Google Sheets and other Google API integrations.

## Workflow Integration

### Klap Video Processing
The enhanced Klap workflow processes video content to generate viral shorts:
1. Video input processing and analysis
2. Individual clip extraction and optimization
3. Metadata generation and storage
4. Export to various formats and platforms

### Instantly.ai Integration
Comprehensive email marketing automation:
1. Campaign creation and management
2. Lead import and segmentation
3. Real-time analytics collection
4. Performance monitoring and optimization

### Lead Generation Pipeline
End-to-end lead processing workflow:
1. Apify web scraping for lead discovery
2. Data enrichment and validation
3. Google Sheets integration for management
4. Instantly.ai push for email campaigns

## Logging and Debugging

### Log Files
- `klap_export.log`: Klap video processing logs
- `klap_process.log`: Detailed Klap workflow execution
- System logs available through the monitoring dashboard

### Debug Scripts
Use debug scripts to troubleshoot API integrations:
- `debug_instantly_response.py`: Instantly.ai API response analysis
- `test_*.py` files: Individual component testing