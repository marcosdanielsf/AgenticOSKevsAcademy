# Prompt para Design do Portal CRM MOTTIVME Sales

## Use este prompt no Gemini/Claude Artifacts para gerar o visual

---

```
Crie um design de interface (UI mockup) para um Portal CRM moderno e minimalista chamado "MOTTIVME Sales".

O portal deve ter as seguintes características:

## ESTILO VISUAL
- Design moderno, clean e profissional
- Cores principais: Azul escuro (#1a1a2e), Roxo (#6c5ce7), Verde para sucesso (#00b894)
- Fundo escuro (dark mode) com cards em tons de cinza escuro
- Tipografia: Inter ou similar, sans-serif
- Bordas arredondadas, sombras sutis
- Ícones minimalistas (estilo Lucide/Heroicons)

## TELAS NECESSÁRIAS

### 1. TELA DE LOGIN
- Logo MOTTIVME centralizado
- Campo de email
- Campo de senha
- Botão "Entrar" em roxo
- Link "Esqueci minha senha"
- Background com gradiente sutil

### 2. DASHBOARD PRINCIPAL
Layout com sidebar à esquerda e conteúdo principal à direita.

**Sidebar (fixa, 250px):**
- Logo MOTTIVME no topo
- Menu com ícones:
  - 📊 Dashboard (ativo)
  - 👥 Leads
  - 💬 Conversas
  - 📈 Métricas
  - ⚙️ Configurações
- Nome do cliente logado no rodapé
- Botão de logout

**Área Principal:**

**Header:**
- Título "Dashboard"
- Seletor de período (Hoje / 7 dias / 30 dias / Personalizado)
- Nome da empresa do cliente

**KPIs em Cards (4 cards em linha):**
- Total de Leads (número grande + variação %)
- Leads Qualificados (número + %)
- Agendamentos (número + %)
- Vendas Fechadas (número + valor R$)

**Funil de Vendas (gráfico horizontal):**
```
Leads     ████████████████████████████████████  42
Qualific. ██████████████████████████            28 (67%)
Agendados ████████████████                      15 (54%)
Realizad. █████████████                         12 (80%)
Vendas    ██████                                 5 (42%)
```
Mostrar barras coloridas com degradê, números à direita e taxa de conversão entre etapas.

**Gráfico de Pizza - Leads por Canal:**
- Facebook: 42 (60%) - Azul
- Instagram: 15 (21%) - Rosa
- WhatsApp: 8 (11%) - Verde
- Orgânico: 5 (7%) - Cinza

**Gráfico de Linha - Leads por Dia (últimos 7 dias):**
- Eixo X: Dias da semana
- Eixo Y: Quantidade de leads
- Linha suave com área preenchida

### 3. TELA DE LEADS
**Header:**
- Título "Leads"
- Campo de busca
- Filtros: Canal | Status | Período
- Botão "Exportar CSV"

**Tabela de Leads:**
| Nome | Canal | Status | Classificação | Data | Ações |
|------|-------|--------|---------------|------|-------|
| Maria Silva | Facebook | 🟢 Qualificado | 🔥 HOT | 08/01 | 👁️ 💬 |
| João Santos | Instagram | 🟡 Novo | 🌡️ WARM | 08/01 | 👁️ 💬 |
| Ana Costa | WhatsApp | 🔵 Agendado | 🔥 HOT | 07/01 | 👁️ 💬 |

- Paginação no rodapé
- Status com badges coloridos
- Classificação com emoji de temperatura
- Ações: Ver detalhes, Abrir conversa

### 4. DETALHE DO LEAD (Modal ou página)
**Cabeçalho:**
- Avatar/Inicial do nome
- Nome completo
- Canal de origem (ícone + texto)
- Status atual (badge colorido)

**Informações em 2 colunas:**

**Coluna 1 - Dados:**
- Email
- Telefone
- Instagram
- Empresa (se tiver)

**Coluna 2 - Métricas:**
- Classificação IA: 🔥 HOT (Score: 85)
- Primeiro contato: 05/01/2026
- Última interação: 08/01/2026
- Total de mensagens: 12

**Timeline de Etapas:**
```
✅ Novo Lead - 05/01 10:30
✅ Qualificado - 06/01 14:20
✅ Agendado - 07/01 09:15
⏳ Aguardando consulta - 10/01 15:00
○ Proposta
○ Fechamento
```

**Histórico de Conversas (preview das últimas 3 mensagens):**
- Mostrar bolhas de chat estilo WhatsApp
- Mensagens do lead à esquerda (cinza)
- Mensagens da IA/equipe à direita (roxo)

### 5. TELA DE CONVERSAS
**Layout estilo WhatsApp/Intercom:**

**Lista de Conversas (sidebar esquerda, 350px):**
- Campo de busca
- Filtro por canal (Todos / Instagram / WhatsApp)
- Lista de conversas:
  - Avatar + Nome
  - Preview da última mensagem (truncado)
  - Horário
  - Badge de não lidas
  - Ícone do canal

**Área de Chat (direita):**
- Header: Nome + Canal + Status do lead
- Área de mensagens (bolhas)
- Input de mensagem (desabilitado, só visualização)
- Indicador "Respondido pela IA" quando aplicável

### 6. TELA DE MÉTRICAS/TRÁFEGO (para clientes de tráfego)
**KPIs de Tráfego:**
- Investimento Total: R$ 5.000
- CPL (Custo por Lead): R$ 119
- CPA (Custo por Aquisição): R$ 625
- ROI: 1.100%
- ROAS: 12x

**Gráfico Comparativo:**
- Investimento vs Retorno (barras lado a lado por semana)

**Tabela de Campanhas:**
| Campanha | Gasto | Leads | CPL | Vendas | ROI |
|----------|-------|-------|-----|--------|-----|
| Facebook - Menopausa | R$ 2.500 | 25 | R$ 100 | 3 | 800% |
| Instagram - Stories | R$ 1.500 | 12 | R$ 125 | 2 | 600% |

## COMPONENTES REUTILIZÁVEIS
- Card com sombra e borda arredondada
- Badge de status (cores: verde, amarelo, azul, vermelho, cinza)
- Botão primário (roxo) e secundário (outline)
- Input com label flutuante
- Tabela com hover e zebra stripes
- Gráficos com tooltips ao hover
- Avatar com iniciais quando sem foto
- Skeleton loading para carregamento

## RESPONSIVIDADE
- Desktop: Layout completo com sidebar
- Tablet: Sidebar colapsável
- Mobile: Bottom navigation, cards empilhados

## ESTADOS
- Loading: Skeleton placeholders
- Empty: Ilustração + texto "Nenhum lead ainda"
- Error: Toast vermelho no canto superior direito

---

Gere mockups visuais de alta fidelidade para cada tela, priorizando o Dashboard e a Lista de Leads.
```

---

## Alternativa: Prompt mais curto para Artifacts

```
Crie um mockup de dashboard para CRM de vendas dark mode.

Elementos:
1. Sidebar com menu (Dashboard, Leads, Conversas, Métricas)
2. 4 KPI cards (Total Leads, Qualificados, Agendados, Vendas)
3. Funil de vendas horizontal com barras e taxas de conversão
4. Gráfico pizza de leads por canal (Facebook, Instagram, WhatsApp)
5. Tabela de leads recentes com status coloridos

Cores: Azul escuro #1a1a2e, Roxo #6c5ce7, Verde #00b894
Estilo: Moderno, clean, profissional, bordas arredondadas
```

---

## Para testar no Claude Artifacts

Copie o prompt acima e peça para criar um React component com Tailwind CSS que renderiza o dashboard. Isso te dará uma visualização interativa do design.
