#!/usr/bin/env python3
"""
Teste de campanha com block detection
Execute: python3 test_campaign.py
"""
import sys
import os

# Add implementation directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'implementation'))

import asyncio
from instagram_dm_agent import InstagramDMAgent

async def test():
    agent = InstagramDMAgent(headless=False, tenant_id='mottivme')
    await agent.start()
    await agent.run_campaign(limit=3, min_score=0)
    await agent.stop()

if __name__ == "__main__":
    asyncio.run(test())
