#!/usr/bin/env python3
"""
Gera diagrama visual do fluxo SDR Julia Amare + AgenticOS
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# Configuração do tamanho da figura
fig, ax = plt.subplots(1, 1, figsize=(24, 32))
ax.set_xlim(0, 24)
ax.set_ylim(0, 32)
ax.axis('off')
ax.set_aspect('equal')

# Cores do sistema
COLORS = {
    'ghl': '#4A90D9',        # Azul - GHL
    'n8n': '#9B59B6',        # Roxo - n8n
    'railway': '#E74C3C',    # Vermelho - Railway/AgenticOS
    'supabase': '#3ECF8E',   # Verde - Supabase
    'instagram': '#E1306C',  # Rosa - Instagram
    'whatsapp': '#25D366',   # Verde WhatsApp
    'header': '#2C3E50',     # Header
    'text': '#FFFFFF',
    'arrow': '#7F8C8D',
    'tag_green': '#27AE60',
    'tag_red': '#E74C3C',
    'tag_blue': '#3498DB',
}

def draw_box(ax, x, y, width, height, color, label, sublabel=None, radius=0.3):
    """Desenha uma caixa com label"""
    box = FancyBboxPatch(
        (x, y), width, height,
        boxstyle=f"round,pad=0.02,rounding_size={radius}",
        facecolor=color,
        edgecolor='white',
        linewidth=2,
        alpha=0.9
    )
    ax.add_patch(box)

    # Label principal
    ax.text(x + width/2, y + height/2 + (0.15 if sublabel else 0), label,
            ha='center', va='center', fontsize=10, fontweight='bold',
            color='white', wrap=True)

    # Sublabel
    if sublabel:
        ax.text(x + width/2, y + height/2 - 0.25, sublabel,
                ha='center', va='center', fontsize=7,
                color='white', alpha=0.9, wrap=True)

def draw_arrow(ax, start, end, color=COLORS['arrow'], style='->'):
    """Desenha seta entre pontos"""
    ax.annotate('', xy=end, xytext=start,
                arrowprops=dict(arrowstyle=style, color=color, lw=2))

def draw_section_header(ax, y, text, color):
    """Desenha header de seção"""
    box = FancyBboxPatch(
        (0.5, y), 23, 1.2,
        boxstyle="round,pad=0.02,rounding_size=0.2",
        facecolor=color,
        edgecolor='white',
        linewidth=3,
        alpha=0.95
    )
    ax.add_patch(box)
    ax.text(12, y + 0.6, text, ha='center', va='center',
            fontsize=14, fontweight='bold', color='white')

# === TÍTULO ===
ax.text(12, 31, 'FLUXO COMPLETO - SDR Julia Amare + AgenticOS',
        ha='center', va='center', fontsize=18, fontweight='bold', color=COLORS['header'])
ax.text(12, 30.4, 'MOTTIVME Sales - Arquitetura de Integracao',
        ha='center', va='center', fontsize=12, color='#7F8C8D')

# === SEÇÃO 1: ENTRADA DE LEADS ===
draw_section_header(ax, 28.5, 'ENTRADA DE LEADS', COLORS['header'])

# Canais de entrada
draw_box(ax, 2, 26.5, 3.5, 1.5, COLORS['instagram'], 'Instagram DM', 'messageType=15')
draw_box(ax, 6.5, 26.5, 3.5, 1.5, COLORS['whatsapp'], 'WhatsApp', 'messageType=2')
draw_box(ax, 11, 26.5, 3.5, 1.5, COLORS['ghl'], 'SMS', 'messageType=2')
draw_box(ax, 15.5, 26.5, 3.5, 1.5, '#F39C12', 'Trafego Pago', 'utm_source')

# GHL
draw_box(ax, 8, 24.5, 8, 1.5, COLORS['ghl'], 'GHL (GoHighLevel)', 'Recebe webhook -> Envia para n8n')

# Setas para GHL
draw_arrow(ax, (3.75, 26.5), (10, 26), COLORS['arrow'])
draw_arrow(ax, (8.25, 26.5), (11, 26), COLORS['arrow'])
draw_arrow(ax, (12.75, 26.5), (13, 26), COLORS['arrow'])
draw_arrow(ax, (17.25, 26.5), (14, 26), COLORS['arrow'])
draw_arrow(ax, (12, 24.5), (12, 23.5), COLORS['arrow'])

# === SEÇÃO 2: N8N WORKFLOW ===
draw_section_header(ax, 22, 'N8N - WORKFLOW SDR JULIA AMARE', COLORS['n8n'])

# Node Info
draw_box(ax, 8, 19.5, 8, 2, COLORS['n8n'], 'NODE: Info', 'Extrai: mensagem, source, lead_id, tags, etc.')
draw_arrow(ax, (12, 22), (12, 21.5), COLORS['arrow'])

# 3 Caminhos paralelos
draw_box(ax, 1.5, 16.5, 6, 2.5, '#3498DB', 'CAMINHO 1\nANALISE DE CONTEXTO', 'Verifica tags e historico')
draw_box(ax, 9, 16.5, 6, 2.5, '#27AE60', 'CAMINHO 2\nCLASSIFICACAO IA', 'Gemini classifica lead')
draw_box(ax, 16.5, 16.5, 6, 2.5, '#F1C40F', 'CAMINHO 3\nVERIFICACAO TRAFEGO', 'Detecta utm_source')

# Setas dos 3 caminhos
draw_arrow(ax, (10, 19.5), (4.5, 19), COLORS['arrow'])
draw_arrow(ax, (12, 19.5), (12, 19), COLORS['arrow'])
draw_arrow(ax, (14, 19.5), (19.5, 19), COLORS['arrow'])

# === SEÇÃO 3: RAILWAY APIs ===
draw_section_header(ax, 14.5, 'RAILWAY - AgenticOS APIs', COLORS['railway'])

# APIs
draw_box(ax, 1, 11, 7, 3, COLORS['railway'], '/api/analyze-conversation\n-context',
         'Verifica tags de bloqueio\nRetorna: should_activate_ia')
draw_box(ax, 8.5, 11, 7, 3, COLORS['railway'], '/webhook/classify-lead',
         'Gemini 1.5 Flash\nRetorna: LEAD_HOT/WARM/COLD')
draw_box(ax, 16, 11, 7, 3, COLORS['railway'], '/api/match-lead-context',
         'Busca em socialfy_leads\nRetorna: matched true/false')

# Setas para APIs
draw_arrow(ax, (4.5, 16.5), (4.5, 14), COLORS['railway'])
draw_arrow(ax, (12, 16.5), (12, 14), COLORS['railway'])
draw_arrow(ax, (19.5, 16.5), (19.5, 14), COLORS['railway'])

# Auto Enrich (condicional)
draw_box(ax, 16, 8, 7, 2, COLORS['railway'], '/api/auto-enrich-lead',
         'Scrape Instagram + Salva')
draw_arrow(ax, (19.5, 11), (19.5, 10), COLORS['railway'])
ax.text(20.5, 10.5, 'se matched=false', fontsize=7, color='#E74C3C', style='italic')

# === SEÇÃO 4: SUPABASE ===
draw_section_header(ax, 6, 'SUPABASE - BANCO DE DADOS', COLORS['supabase'])

# Tabelas
draw_box(ax, 1.5, 3.5, 5, 2, COLORS['supabase'], 'socialfy_leads',
         'instagram_handle, phone\noutreach_sent_at <- NOVO!')
draw_box(ax, 7, 3.5, 5, 2, COLORS['supabase'], 'agentic_instagram\n_leads',
         'username, bio\nfollowers, scraped_at')
draw_box(ax, 12.5, 3.5, 5, 2, COLORS['supabase'], 'enriched_lead\n_data',
         'ig_handle, bio\nengagement_rate')
draw_box(ax, 18, 3.5, 5, 2, COLORS['supabase'], 'dm_sent',
         'username, message\nsent_at, status')

# Setas para Supabase
draw_arrow(ax, (4.5, 11), (4, 6), COLORS['supabase'])
draw_arrow(ax, (12, 11), (9.5, 6), COLORS['supabase'])
draw_arrow(ax, (19.5, 8), (15, 6), COLORS['supabase'])

# === LEGENDA DE TAGS ===
ax.text(1, 1.5, 'TAGS DO SISTEMA:', fontsize=10, fontweight='bold', color=COLORS['header'])

# Tags
tag_y = 0.8
draw_box(ax, 1, tag_y, 4.5, 0.6, COLORS['tag_blue'], 'lead-prospectado-ia', None, 0.1)
draw_box(ax, 6, tag_y, 4.5, 0.6, COLORS['tag_green'], 'lead-classificado-ia', None, 0.1)
draw_box(ax, 11, tag_y, 3, 0.6, COLORS['tag_red'], 'perdido', None, 0.1)
draw_box(ax, 14.5, tag_y, 3, 0.6, '#9B59B6', 'ativar_ia', None, 0.1)

ax.text(1, 0.3, 'matched=true', fontsize=7, color='#7F8C8D')
ax.text(6, 0.3, 'LEAD_*', fontsize=7, color='#7F8C8D')
ax.text(11, 0.3, 'SPAM/PESSOAL', fontsize=7, color='#7F8C8D')
ax.text(14.5, 0.3, 'flag de controle', fontsize=7, color='#7F8C8D')

# Bug fix note
ax.text(18.5, 1.2, 'BUG FIX 08/01/2026:', fontsize=8, fontweight='bold', color=COLORS['tag_red'])
ax.text(18.5, 0.7, 'Removido ativar_ia de', fontsize=7, color='#7F8C8D')
ax.text(18.5, 0.3, 'prospecting_tags', fontsize=7, color='#7F8C8D')

# Salvar
plt.tight_layout()
plt.savefig('/Users/marcosdaniels/Projects/mottivme/AgenticOSKevsAcademy/docs/FLUXO_SDR_VISUAL.png',
            dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
plt.savefig('/Users/marcosdaniels/Projects/mottivme/AgenticOSKevsAcademy/docs/FLUXO_SDR_VISUAL.pdf',
            bbox_inches='tight', facecolor='white', edgecolor='none')

print("Diagrama gerado com sucesso!")
print("   PNG: docs/FLUXO_SDR_VISUAL.png")
print("   PDF: docs/FLUXO_SDR_VISUAL.pdf")
