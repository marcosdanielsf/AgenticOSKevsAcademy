#!/usr/bin/env python3
"""
Socialfy - Lead Generation & DM Automation System
==================================================
Complete multi-agent system for Instagram lead generation.

Architecture:
- Orchestrator Agent (Maestro)
- Outbound Squad (5 agents)
- Inbound Squad (3 agents)
- Infrastructure Squad (3 agents)
- API Server (FastAPI)

Usage:
    # Start full system (API + Agents)
    python socialfy_main.py

    # Start only API server
    python socialfy_main.py --api-only

    # Start only agents (CLI mode)
    python socialfy_main.py --cli

    # Process specific lead
    python socialfy_main.py --process-lead @username

    # Start inbox monitoring
    python socialfy_main.py --monitor-inbox
"""

import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

# ============================================
# LOGGING SETUP
# ============================================

BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "socialfy.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Socialfy")


# ============================================
# SYSTEM BANNER
# ============================================

BANNER = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   ███████╗ ██████╗  ██████╗██╗ █████╗ ██╗     ███████╗██╗   ██╗   ║
║   ██╔════╝██╔═══██╗██╔════╝██║██╔══██╗██║     ██╔════╝╚██╗ ██╔╝   ║
║   ███████╗██║   ██║██║     ██║███████║██║     █████╗   ╚████╔╝    ║
║   ╚════██║██║   ██║██║     ██║██╔══██║██║     ██╔══╝    ╚██╔╝     ║
║   ███████║╚██████╔╝╚██████╗██║██║  ██║███████╗██║        ██║      ║
║   ╚══════╝ ╚═════╝  ╚═════╝╚═╝╚═╝  ╚═╝╚══════╝╚═╝        ╚═╝      ║
║                                                                   ║
║   Lead Generation & DM Automation System                          ║
║   Version 1.0.0 | Multi-Agent Architecture                        ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"""


# ============================================
# SQUAD FACTORY
# ============================================

def create_all_squads(config: Dict = None) -> Dict:
    """Create all agent squads (6 squads, 23 agents)"""
    from agents.outbound_squad import create_outbound_squad
    from agents.inbound_squad import create_inbound_squad
    from agents.infrastructure_squad import create_infrastructure_squad
    from agents.security_squad import create_security_squad
    from agents.performance_squad import create_performance_squad
    from agents.quality_squad import create_quality_squad

    config = config or {}

    return {
        "outbound": create_outbound_squad(config.get("outbound")),
        "inbound": create_inbound_squad(config.get("inbound")),
        "infrastructure": create_infrastructure_squad(config.get("infrastructure")),
        "security": create_security_squad(config.get("security")),
        "performance": create_performance_squad(config.get("performance")),
        "quality": create_quality_squad(config.get("quality")),
    }


async def initialize_orchestrator(config: Dict = None) -> 'OrchestratorAgent':
    """Initialize the orchestrator with all 6 squads (23 agents)"""
    from agents.orchestrator import OrchestratorAgent

    logger.info("Initializing Orchestrator with 6 squads...")

    orchestrator = OrchestratorAgent(config)

    # Create and register all squads
    squads = create_all_squads(config)

    total_agents = 0
    for squad_name, agents in squads.items():
        for agent_name, agent in agents.items():
            orchestrator.register_agent(agent, squad_name)
            total_agents += 1

    # Initialize
    await orchestrator.initialize()

    logger.info(f"Orchestrator ready with {total_agents} agents across {len(squads)} squads")

    return orchestrator


# ============================================
# CLI COMMANDS
# ============================================

async def process_lead(username: str, orchestrator: 'OrchestratorAgent'):
    """Process a single lead through the pipeline"""
    logger.info(f"Processing lead: @{username}")

    result = await orchestrator.process_outbound_lead(username)

    if result.get("success"):
        logger.info(f"Lead processed successfully!")
        logger.info(f"  Score: {result.get('result', {}).get('step_1_result', {}).get('score', 'N/A')}")
        logger.info(f"  Classification: {result.get('result', {}).get('step_1_result', {}).get('classification', 'N/A')}")
    else:
        logger.error(f"Lead processing failed: {result.get('error')}")

    return result


async def batch_process_leads(usernames: List[str], orchestrator: 'OrchestratorAgent'):
    """Process multiple leads"""
    logger.info(f"Processing {len(usernames)} leads...")

    results = await orchestrator.process_leads_batch(usernames)

    successful = len([r for r in results if r.get("result", {}).get("success")])
    logger.info(f"Completed: {successful}/{len(usernames)} successful")

    return results


async def start_inbox_monitoring(orchestrator: 'OrchestratorAgent'):
    """Start inbox monitoring"""
    logger.info("Starting inbox monitoring...")

    inbox_agent = orchestrator.get_agent("InboxMonitor")
    if inbox_agent:
        from agents.base_agent import Task

        task = Task(
            task_type="start_monitoring",
            payload={"accounts": ["default"]}
        )
        await inbox_agent.start()
        result = await inbox_agent.execute_task(task)
        logger.info(f"Monitoring started: {result}")
    else:
        logger.error("InboxMonitor agent not found")


async def get_system_status(orchestrator: 'OrchestratorAgent'):
    """Get system status"""
    from agents.base_agent import Task

    task = Task(task_type="system_health", payload={})
    health = await orchestrator.execute_task(task)

    print("\n" + "="*60)
    print("SYSTEM STATUS")
    print("="*60)
    print(f"Status: {health.get('status', 'unknown')}")
    print(f"Active Agents: {health.get('system_metrics', {}).get('active_agents', 0)}")
    print(f"Total Tasks: {health.get('total_tasks_processed', 0)}")
    print(f"Success Rate: {health.get('overall_success_rate', 0):.1%}")
    print()

    print("Agents:")
    for name, info in health.get("agents", {}).items():
        state_icon = "✅" if info.get("state") == "ready" else "⚠️"
        print(f"  {state_icon} {name} [{info.get('squad')}]: {info.get('tasks_completed', 0)} tasks")

    print("="*60 + "\n")

    return health


# ============================================
# API SERVER
# ============================================

async def start_api_server(host: str = "0.0.0.0", port: int = 8000):
    """Start the FastAPI server"""
    import uvicorn
    from api_server import app

    logger.info(f"Starting API server on {host}:{port}")
    logger.info(f"API docs: http://{host}:{port}/docs")

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()


# ============================================
# MAIN
# ============================================

async def main():
    parser = argparse.ArgumentParser(
        description='Socialfy - Lead Generation & DM Automation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python socialfy_main.py                    # Start full system
  python socialfy_main.py --api-only         # Start only API server
  python socialfy_main.py --status           # Show system status
  python socialfy_main.py --process @user    # Process single lead
  python socialfy_main.py --monitor-inbox    # Start inbox monitoring
        """
    )

    parser.add_argument('--api-only', action='store_true',
                       help='Start only the API server')
    parser.add_argument('--cli', action='store_true',
                       help='Start in CLI mode (no API server)')
    parser.add_argument('--process', type=str, metavar='USERNAME',
                       help='Process a single lead (e.g., @username)')
    parser.add_argument('--batch', type=str, metavar='FILE',
                       help='Process leads from file (one username per line)')
    parser.add_argument('--monitor-inbox', action='store_true',
                       help='Start inbox monitoring')
    parser.add_argument('--status', action='store_true',
                       help='Show system status')
    parser.add_argument('--host', default='0.0.0.0',
                       help='API server host (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8000,
                       help='API server port (default: 8000)')

    args = parser.parse_args()

    # Show banner
    print(BANNER)

    # API-only mode
    if args.api_only:
        await start_api_server(args.host, args.port)
        return

    # Initialize orchestrator for CLI modes
    orchestrator = await initialize_orchestrator()

    # Show status
    if args.status:
        await get_system_status(orchestrator)
        return

    # Process single lead
    if args.process:
        username = args.process.lstrip('@')
        await process_lead(username, orchestrator)
        return

    # Process batch
    if args.batch:
        with open(args.batch) as f:
            usernames = [line.strip().lstrip('@') for line in f if line.strip()]
        await batch_process_leads(usernames, orchestrator)
        return

    # Monitor inbox
    if args.monitor_inbox:
        await start_inbox_monitoring(orchestrator)
        # Keep running
        try:
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            logger.info("Stopping...")
        return

    # CLI mode
    if args.cli:
        await interactive_cli(orchestrator)
        return

    # Default: Start full system (API + monitoring)
    logger.info("Starting full system...")

    # Start inbox monitoring in background
    monitoring_task = asyncio.create_task(start_inbox_monitoring(orchestrator))

    # Start API server (blocks)
    try:
        await start_api_server(args.host, args.port)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        monitoring_task.cancel()
        await orchestrator.cleanup()


async def interactive_cli(orchestrator: 'OrchestratorAgent'):
    """Interactive CLI mode"""
    print("\nSocialfy CLI")
    print("Commands: process <username>, status, batch <file>, inbox, quit\n")

    while True:
        try:
            command = input("socialfy> ").strip()

            if not command:
                continue

            parts = command.split()
            cmd = parts[0].lower()

            if cmd == "quit" or cmd == "exit":
                break

            elif cmd == "status":
                await get_system_status(orchestrator)

            elif cmd == "process" and len(parts) > 1:
                username = parts[1].lstrip('@')
                await process_lead(username, orchestrator)

            elif cmd == "batch" and len(parts) > 1:
                with open(parts[1]) as f:
                    usernames = [line.strip().lstrip('@') for line in f if line.strip()]
                await batch_process_leads(usernames, orchestrator)

            elif cmd == "inbox":
                await start_inbox_monitoring(orchestrator)

            else:
                print(f"Unknown command: {command}")
                print("Commands: process <username>, status, batch <file>, inbox, quit")

        except KeyboardInterrupt:
            print("\nUse 'quit' to exit")
        except EOFError:
            break
        except Exception as e:
            print(f"Error: {e}")

    logger.info("CLI mode ended")
    await orchestrator.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
