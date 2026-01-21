"""
Skill: analyze_message_intent
=============================
Analisa semanticamente uma mensagem para detectar se é uma RESPOSTA
a algo que a empresa enviou (outbound) ou uma INICIATIVA do lead (inbound).

Usa Gemini para análise inteligente quando disponível,
com fallback para heurísticas baseadas em padrões.

Uso:
    from skills.analyze_message_intent import analyze_message_intent

    result = await analyze_message_intent(
        message="Oi!! Muito obrigada pelo elogio e pelas palavras tão gentis."
    )

    # result.data = {
    #     "origin": "outbound",
    #     "confidence": 0.95,
    #     "reasoning": "Mensagem agradece elogio recebido anteriormente",
    #     "is_response": True,
    #     "detected_context": "agradecimento_elogio"
    # }
"""

import os
import re
from typing import Dict, Any, Optional, List, Tuple

from . import skill, logger

# Tentar importar Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = bool(os.getenv("GEMINI_API_KEY"))
    if GEMINI_AVAILABLE:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None


# =====================================================
# HEURÍSTICAS (Fallback quando Gemini não disponível)
# =====================================================

# Padrões que indicam RESPOSTA (outbound - empresa iniciou)
RESPONSE_PATTERNS = [
    # Agradecimentos a algo recebido
    (r"obrigad[ao].*pelo", "agradecimento_algo_recebido", 0.9),
    (r"obrigad[ao].*pelas", "agradecimento_algo_recebido", 0.9),
    (r"obrigad[ao].*elogio", "agradecimento_elogio", 0.95),
    (r"obrigad[ao].*mensagem", "agradecimento_mensagem", 0.85),
    (r"obrigad[ao].*contato", "agradecimento_contato", 0.85),
    (r"obrigad[ao].*interesse", "agradecimento_interesse", 0.8),

    # Referências a algo anterior
    (r"vi (sua|seu|a) (mensagem|dm|direct)", "referencia_mensagem_anterior", 0.9),
    (r"recebi (sua|seu|a)", "referencia_algo_recebido", 0.85),
    (r"sobre (o que|aquilo que) (você|vc|voce) (disse|falou|mandou)", "referencia_conteudo_anterior", 0.9),
    (r"em resposta", "resposta_explicita", 0.95),
    (r"respondendo", "resposta_explicita", 0.9),

    # Reações a elogios/comentários
    (r"fico feliz", "reacao_positiva", 0.7),
    (r"que bom", "reacao_positiva", 0.6),
    (r"muito gentil", "reacao_elogio", 0.8),
    (r"palavras.*gentis", "reacao_elogio", 0.85),
    (r"que fofo", "reacao_elogio", 0.75),

    # Continuação de conversa
    (r"como (você|vc|voce) (disse|falou|mencionou)", "continuacao_conversa", 0.85),
    (r"sobre isso", "continuacao_conversa", 0.6),
]

# Padrões que indicam INICIATIVA (inbound - lead iniciou)
INITIATIVE_PATTERNS = [
    # Perguntas iniciais
    (r"^oi[,!]?\s*(tudo bem|td bem|como vai)?", "saudacao_inicial", 0.6),
    (r"^olá[,!]?\s*(tudo bem|td bem)?", "saudacao_inicial", 0.6),
    (r"^bom dia[,!]?", "saudacao_inicial", 0.5),
    (r"^boa tarde[,!]?", "saudacao_inicial", 0.5),
    (r"^boa noite[,!]?", "saudacao_inicial", 0.5),

    # Interesse/curiosidade espontânea
    (r"quero (saber|conhecer|entender)", "interesse_espontaneo", 0.8),
    (r"gostaria de (saber|conhecer)", "interesse_espontaneo", 0.8),
    (r"pode me (explicar|falar|contar)", "pedido_informacao", 0.75),
    (r"como funciona", "pedido_informacao", 0.7),
    (r"qual (o |é o )?(valor|preço|preco|custo)", "pergunta_preco", 0.85),
    (r"quanto custa", "pergunta_preco", 0.85),

    # Vi seu perfil/trabalho
    (r"vi (seu|o seu) (perfil|trabalho|post|stories)", "descoberta_organica", 0.7),
    (r"te encontrei", "descoberta_organica", 0.65),
    (r"achei (seu|o seu|você)", "descoberta_organica", 0.6),

    # Pedidos diretos
    (r"preciso de (ajuda|um|uma)", "pedido_ajuda", 0.7),
    (r"estou (procurando|buscando)", "busca_ativa", 0.75),
    (r"vocês (fazem|trabalham|atendem)", "pergunta_servico", 0.7),
]


def _analyze_with_heuristics(message: str) -> Tuple[str, float, str, str]:
    """
    Analisa mensagem usando heurísticas (regex patterns).

    Returns:
        Tuple[origin, confidence, reasoning, detected_context]
    """
    message_lower = message.lower().strip()

    # Verificar padrões de RESPOSTA
    for pattern, context, confidence in RESPONSE_PATTERNS:
        if re.search(pattern, message_lower):
            return (
                "outbound",
                confidence,
                f"Padrão detectado: {context}",
                context
            )

    # Verificar padrões de INICIATIVA
    for pattern, context, confidence in INITIATIVE_PATTERNS:
        if re.search(pattern, message_lower):
            return (
                "inbound",
                confidence,
                f"Padrão detectado: {context}",
                context
            )

    # Default: inconclusivo
    return (
        "unknown",
        0.3,
        "Nenhum padrão claro detectado",
        "indefinido"
    )


async def _analyze_with_gemini(message: str) -> Tuple[str, float, str, str]:
    """
    Analisa mensagem usando Gemini para análise semântica profunda.

    Returns:
        Tuple[origin, confidence, reasoning, detected_context]
    """
    if not GEMINI_AVAILABLE or not genai:
        return _analyze_with_heuristics(message)

    prompt = f"""Analise esta mensagem de DM do Instagram e determine se é:

1. RESPOSTA (outbound): O lead está respondendo a algo que a empresa/vendedor enviou primeiro
   - Exemplos: agradecimentos por elogios, respostas a perguntas, continuação de conversa iniciada pela empresa

2. INICIATIVA (inbound): O lead está iniciando contato de forma espontânea
   - Exemplos: primeiro contato, perguntas sobre preço/serviço, descobriu o perfil sozinho

MENSAGEM DO LEAD:
"{message}"

Responda APENAS no formato JSON:
{{
    "origin": "outbound" ou "inbound" ou "unknown",
    "confidence": 0.0 a 1.0,
    "reasoning": "explicação curta",
    "detected_context": "tipo_de_mensagem"
}}"""

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)

        # Extrair JSON da resposta
        text = response.text.strip()

        # Tentar extrair JSON
        import json

        # Remover markdown se tiver
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        result = json.loads(text)

        return (
            result.get("origin", "unknown"),
            float(result.get("confidence", 0.5)),
            result.get("reasoning", "Análise via Gemini"),
            result.get("detected_context", "gemini_analysis")
        )

    except Exception as e:
        logger.warning(f"Erro no Gemini, usando heurísticas: {e}")
        return _analyze_with_heuristics(message)


@skill(
    name="analyze_message_intent",
    description="Analisa se mensagem é resposta (outbound) ou iniciativa (inbound)"
)
async def analyze_message_intent(
    message: str,
    use_ai: bool = True
) -> Dict[str, Any]:
    """
    Analisa a intenção/contexto de uma mensagem.

    Args:
        message: Texto da mensagem do lead
        use_ai: Se True, usa Gemini para análise (default: True)

    Returns:
        Dict com origin (outbound/inbound), confidence, reasoning
    """
    if not message:
        return {
            "error": "message é obrigatório",
            "origin": "unknown",
            "confidence": 0.0
        }

    message = message.strip()

    # Mensagem muito curta: difícil analisar
    if len(message) < 3:
        return {
            "origin": "unknown",
            "confidence": 0.1,
            "reasoning": "Mensagem muito curta para análise",
            "is_response": None,
            "detected_context": "mensagem_curta",
            "message_length": len(message)
        }

    # Analisar
    if use_ai and GEMINI_AVAILABLE:
        origin, confidence, reasoning, context = await _analyze_with_gemini(message)
        analysis_method = "gemini"
    else:
        origin, confidence, reasoning, context = _analyze_with_heuristics(message)
        analysis_method = "heuristics"

    # Determinar tom recomendado para o agente
    if origin == "outbound":
        recommended_tone = "direto, dar continuidade à conversa iniciada"
        agent_hint = "Lead está respondendo prospecção - não precisa se apresentar novamente"
    elif origin == "inbound":
        recommended_tone = "receptivo, qualificar com perguntas abertas"
        agent_hint = "Lead iniciou contato - fazer qualificação inicial"
    else:
        recommended_tone = "neutro, buscar entender contexto"
        agent_hint = "Origem incerta - fazer perguntas para entender contexto"

    result = {
        "origin": origin,
        "confidence": confidence,
        "reasoning": reasoning,
        "is_response": origin == "outbound",
        "detected_context": context,
        "analysis_method": analysis_method,
        "message_preview": message[:100] + "..." if len(message) > 100 else message,
        "recommended_tone": recommended_tone,
        "agent_hint": agent_hint
    }

    logger.info(f"Análise de intent: origin={origin}, confidence={confidence:.2f}, method={analysis_method}")

    return result
