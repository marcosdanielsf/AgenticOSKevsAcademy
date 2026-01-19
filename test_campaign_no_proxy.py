#!/usr/bin/env python3
"""
Teste de campanha SEM PROXY (para validar seletores)
Execute: python3 test_campaign_no_proxy.py
"""
import sys
import os

# Add implementation directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'implementation'))

import asyncio
from instagram_dm_agent import InstagramDMAgent

async def test():
    agent = InstagramDMAgent(headless=False, tenant_id='mottivme')

    # DESATIVAR PROXY para este teste
    agent.proxy_manager = None
    agent.current_proxy = None

    await agent.start()
    await agent.run_campaign(limit=2, min_score=0)
    await agent.stop()

if __name__ == "__main__":
    asyncio.run(test())
