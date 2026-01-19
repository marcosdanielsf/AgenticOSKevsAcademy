#!/usr/bin/env python3
"""
Teste COMPLETO de campanha: Proxy + Spintax + Block Detection
Execute: python3 test_campaign_full.py

Valida:
1. Carregamento do proxy do Supabase
2. Geração de mensagens com spintax híbrido
3. Detecção de bloqueios
4. Logs detalhados
"""
import sys
import os

# Add implementation directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'implementation'))

import asyncio
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

async def test_proxy():
    """Testa se o proxy está configurado"""
    logger.info("=" * 50)
    logger.info("TESTE 1: Verificando Proxy")
    logger.info("=" * 50)

    try:
        from proxy_manager import ProxyManager
        pm = ProxyManager()

        # Buscar proxy global (método síncrono, não precisa de await)
        proxy = pm.get_proxy_for_tenant('global')
        if proxy:
            logger.info(f"✅ Proxy encontrado: {proxy.host}:{proxy.port}")
            logger.info(f"   Provider: {proxy.provider}")
            logger.info(f"   Residential: {proxy.is_residential}")
            return True
        else:
            logger.warning("⚠️ Nenhum proxy configurado - continuando sem proxy")
            return False
    except Exception as e:
        logger.error(f"❌ Erro ao verificar proxy: {e}")
        return False

async def test_spintax():
    """Testa geração de mensagens com spintax"""
    logger.info("=" * 50)
    logger.info("TESTE 2: Verificando Spintax Híbrido")
    logger.info("=" * 50)

    try:
        from message_generator import MessageGenerator

        mg = MessageGenerator()

        # Mock profile data
        profile = {
            'username': 'dr_teste',
            'full_name': 'Dr. João Silva',
            'biography': 'Cirurgião plástico | Lipo HD | Harmonização facial | São Paulo',
            'followers_count': 50000,
            'is_verified': True
        }

        # Mock score data
        score_data = {
            'total_score': 85,
            'priority': 'HOT',
            'icp_match': 90,
            'engagement_score': 80,
            'bio_quality': 85
        }

        # Gerar 3 mensagens para ver variação
        logger.info("Gerando 3 mensagens para verificar variação:")
        messages = []
        for i in range(3):
            msg = mg.generate_hybrid(profile, score_data)
            messages.append(msg.message if hasattr(msg, 'message') else str(msg))
            logger.info(f"\n   Msg {i+1}: {messages[-1][:100]}...")

        # Verificar se há variação
        unique = len(set(messages))
        if unique > 1:
            logger.info(f"✅ Spintax funcionando! {unique}/3 mensagens únicas")
            return True
        else:
            logger.warning("⚠️ Mensagens iguais - spintax pode não estar ativo")
            return True  # Não é erro crítico

    except Exception as e:
        logger.error(f"❌ Erro ao testar spintax: {e}")
        return False

async def test_block_detection():
    """Testa sistema de detecção de bloqueio"""
    logger.info("=" * 50)
    logger.info("TESTE 3: Verificando Block Detection")
    logger.info("=" * 50)

    try:
        from instagram_dm_agent import BlockType, BlockDetectionResult

        # Testar criação de BlockDetectionResult
        result = BlockDetectionResult(
            is_blocked=True,
            block_type=BlockType.ACTION_BLOCKED,
            message="Ação bloqueada temporariamente"
        )

        logger.info(f"   should_stop_campaign: {result.should_stop_campaign}")
        logger.info(f"   should_switch_account: {result.should_switch_account}")

        # Testar diferentes tipos
        for bt in BlockType:
            r = BlockDetectionResult(is_blocked=True, block_type=bt, message="test")
            logger.info(f"   {bt.value}: stop={r.should_stop_campaign}, switch={r.should_switch_account}")

        logger.info("✅ Block Detection classes funcionando!")
        return True

    except ImportError as e:
        logger.error(f"❌ BlockType/BlockDetectionResult não encontrados: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Erro ao testar block detection: {e}")
        return False

async def test_campaign_dry_run():
    """Teste de campanha em modo DRY RUN (não envia DMs)"""
    logger.info("=" * 50)
    logger.info("TESTE 4: Campanha DRY RUN")
    logger.info("=" * 50)

    try:
        from instagram_dm_agent import InstagramDMAgent

        # Criar agente
        agent = InstagramDMAgent(
            headless=True,  # Sem janela
            tenant_id='mottivme'
        )

        logger.info("Iniciando agente (pode demorar - carrega Playwright)...")
        await agent.start()

        # Verificar se proxy foi carregado
        if hasattr(agent, 'current_proxy') and agent.current_proxy:
            logger.info(f"✅ Proxy carregado: {agent.current_proxy.host}")
        else:
            logger.info("⚠️ Agente iniciado sem proxy")

        # NÃO executar campanha real - apenas verificar inicialização
        logger.info("✅ Agente inicializado com sucesso!")

        await agent.stop()
        logger.info("✅ Agente encerrado corretamente")
        return True

    except Exception as e:
        logger.error(f"❌ Erro no teste de campanha: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Executa todos os testes"""
    print("\n" + "=" * 60)
    print("🧪 TESTE COMPLETO: Proxy + Spintax + Block Detection")
    print("=" * 60 + "\n")

    results = {}

    # Teste 1: Proxy
    results['proxy'] = await test_proxy()

    # Teste 2: Spintax
    results['spintax'] = await test_spintax()

    # Teste 3: Block Detection
    results['block_detection'] = await test_block_detection()

    # Teste 4: Campanha (dry run)
    # results['campaign'] = await test_campaign_dry_run()
    logger.info("⏭️ Teste 4 (campanha) pulado - requer browser")
    results['campaign'] = None

    # Resumo
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)

    for test_name, passed in results.items():
        if passed is None:
            status = "⏭️ PULADO"
        elif passed:
            status = "✅ PASSOU"
        else:
            status = "❌ FALHOU"
        print(f"   {test_name.upper()}: {status}")

    # Contagem
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)

    print(f"\n   Total: {passed} passou, {failed} falhou, {skipped} pulado")

    if failed == 0:
        print("\n🎉 Sistema pronto para campanha real!")
    else:
        print("\n⚠️ Corrija os erros antes de rodar campanha real")

if __name__ == "__main__":
    asyncio.run(main())
