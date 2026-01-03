# MANUAL INTERNO - SISTEMA DE PROSPECCAO E CLASSIFICACAO DE LEADS

**Versao:** 2.0
**Ultima Atualizacao:** 03/01/2026
**Departamento:** Vendas / Operacoes
**Confidencial:** Uso interno MOTTIVME

---

## SUMARIO

1. [Visao Geral do Sistema](#1-visao-geral-do-sistema)
2. [Como Verificar se Esta Funcionando](#2-como-verificar-se-esta-funcionando)
3. [Troubleshooting - Erros Comuns](#3-troubleshooting---erros-comuns)
4. [Como Validar Acertos](#4-como-validar-acertos)
5. [Comandos Uteis](#5-comandos-uteis)
6. [Contatos para Suporte](#6-contatos-para-suporte)

---

## 1. VISAO GERAL DO SISTEMA

### O que e o Sistema de Prospeccao Automatica

O sistema de prospeccao automatica da MOTTIVME e uma solucao integrada que:

1. **Identifica** potenciais clientes no Instagram automaticamente
2. **Envia** mensagens personalizadas via DM
3. **Classifica** as respostas usando Inteligencia Artificial
4. **Ativa** agentes de IA para continuar a conversa no CRM

### Componentes Principais

| Componente | O que faz | Onde acessar |
|------------|-----------|--------------|
| **AgenticOS** | Coleta dados de perfis e armazena leads | Railway (backend) |
| **n8n** | Orquestra o fluxo e classifica leads | https://cliente-a1.mentorfy.io |
| **GoHighLevel (GHL)** | CRM onde os leads sao gerenciados | https://app.socialfy.me |

### Fluxo Resumido (5 Etapas)

```
   ETAPA 1              ETAPA 2              ETAPA 3
  +---------+         +---------+         +---------+
  | SCRAPE  |   -->   | SALVAR  |   -->   | ENVIAR  |
  | PERFIL  |         | NO DB   |         |   DM    |
  +---------+         +---------+         +---------+
       |                   |                   |
       v                   v                   v
   AgenticOS          AgenticOS           Instagram
   coleta dados       registra lead       mensagem enviada


                    LEAD RESPONDE
                         |
                         v

   ETAPA 4              ETAPA 5              RESULTADO
  +---------+         +---------+         +-----------+
  | n8n     |   -->   |   GHL   |   -->   | IA ATIVA  |
  | CLASSIF.|         |  TAGS   |         | CONVERSA  |
  +---------+         +---------+         +-----------+
       |                   |                    |
       v                   v                    v
   IA analisa         Tag aplicada         Agente IA
   a mensagem         automaticamente      assume atendimento
```

### Tags do Sistema

| Tag | Significado | Acao Automatica |
|-----|-------------|-----------------|
| `lead-prospectado-ia` | Lead veio da nossa prospeccao | ativar_ia = sim |
| `lead-classificado-ia` | Lead classificado pela IA | ativar_ia = sim |
| `perdido` | Lead e SPAM ou conta pessoal | ativar_ia = nao |
| `ia-ativada` | IA ja esta respondendo | Evita duplicacao |

### Campos Importantes no GHL

| Campo | Valores Possiveis | Significado |
|-------|-------------------|-------------|
| `ativar_ia` | sim / nao | Se a IA deve responder |
| `agente_ia` | SDR Prospeccao / SDR Inbound | Qual perfil de IA usar |
| `origem_lead` | prospeccao_instagram / trafego | De onde veio o lead |
| `classificacao_ia` | LEAD_QUENTE / LEAD_MORNO / LEAD_FRIO | Temperatura do lead |

---

## 2. COMO VERIFICAR SE ESTA FUNCIONANDO

### 2.1 Verificar no n8n

**Acesso:** https://cliente-a1.mentorfy.io

**Workflow Principal:** "GHL - Mottivme - EUA Versionado"
**ID do Workflow:** `R2fVs2qpct1Qr2Y1`

#### Passo a Passo para Ver Execucoes:

1. Faca login no n8n
2. Va em **"Executions"** no menu lateral
3. Filtre pelo workflow **"GHL - Mottivme - EUA Versionado"**
4. Verifique as ultimas execucoes

#### Entendendo os Status:

| Status | Cor | Significado | Acao Necessaria |
|--------|-----|-------------|-----------------|
| **Success** | Verde | Funcionou corretamente | Nenhuma |
| **Error** | Vermelho | Algo falhou | Ver detalhes do erro |
| **Running** | Azul | Em execucao | Aguardar |
| **Waiting** | Amarelo | Aguardando input | Normal em alguns casos |

#### O que Verificar em Cada Execucao:

1. **Webhook disparou?** - Primeiro node deve ter dados do GHL
2. **IF "Veio de Trafego" passou?** - Se sim, lead NAO e de prospeccao
3. **Match retornou true?** - Se false, lead nao estava no AgenticOS
4. **Tag foi aplicada?** - Ultimo node deve mostrar sucesso

### 2.2 Verificar no GoHighLevel

**Acesso:** https://app.socialfy.me

**Location ID:** `sNwLyynZWP6jEtBy1ubf`

#### URLs Importantes:

| Funcao | URL |
|--------|-----|
| Dashboard | https://app.socialfy.me/v2/location/sNwLyynZWP6jEtBy1ubf/dashboard |
| Contatos | https://app.socialfy.me/v2/location/sNwLyynZWP6jEtBy1ubf/contacts/smart_list/All |
| Conversas | https://app.socialfy.me/v2/location/sNwLyynZWP6jEtBy1ubf/conversations |
| Automacoes | https://app.socialfy.me/v2/location/sNwLyynZWP6jEtBy1ubf/automation |

#### Verificar Tags em um Contato:

1. Acesse **Contatos**
2. Busque pelo nome ou Instagram do lead
3. Clique no contato
4. Veja a secao **"Tags"** no perfil
5. Tags esperadas: `lead-prospectado-ia`, `lead-classificado-ia`, ou `perdido`

#### Verificar Campos Customizados:

1. No perfil do contato, role ate **"Custom Fields"**
2. Verifique:
   - `ativar_ia` deve estar = "sim" (se lead qualificado)
   - `agente_ia` deve ter um valor (SDR Prospeccao ou SDR Inbound)
   - `data_ativacao_ia` deve ter data/hora

### 2.3 Verificar no AgenticOS

**Base URL:** `https://agenticoskevsacademy-production.up.railway.app`

#### Verificar se Lead Existe:

```bash
curl -s -X GET "https://agenticoskevsacademy-production.up.railway.app/api/leads?username=NOME_DO_PERFIL&tenant_id=mottivme" \
  -H "Content-Type: application/json"
```

**Resposta Esperada se Lead Existe:**
```json
{
  "success": true,
  "matched": true,
  "lead": {
    "id": "uuid-do-lead",
    "username": "nome_do_perfil",
    "source": "prospeccao_instagram"
  }
}
```

**Resposta se Lead NAO Existe:**
```json
{
  "success": true,
  "matched": false
}
```

---

## 3. TROUBLESHOOTING - ERROS COMUNS

### 3.1 TAG NAO FOI ADICIONADA NO GHL

#### Possiveis Causas:

**Causa 1: IF "Ja Ativou IA?" bloqueou**
- O lead ja tinha a tag `ia-ativada`
- Sistema evita aplicar tags duplicadas
- **Verificacao:** Olhe se o lead ja tem a tag no GHL
- **Acao:** Isso e comportamento normal, nao e erro

**Causa 2: IF "Veio de Trafego?" bloqueou**
- O lead tem UTM source preenchido
- Sistema identifica como lead de trafego pago, nao prospeccao
- **Verificacao:** No n8n, veja se `utm_source` tem valor
- **Acao:** Isso e comportamento normal para leads de anuncios

**Causa 3: Workflow parou com erro**
- Algum node falhou durante a execucao
- **Verificacao:** No n8n, veja a execucao com status "Error"
- **Acao:** Clique na execucao e veja qual node falhou

**Causa 4: API Key do GHL expirada**
- Credenciais do GHL no n8n estao invalidas
- **Verificacao:** Erro menciona "401 Unauthorized"
- **Acao:** Contatar suporte tecnico para renovar credenciais

### 3.2 MATCH RETORNOU FALSE QUANDO DEVERIA SER TRUE

**O que significa:** O sistema nao encontrou o lead no AgenticOS, mesmo que ele tenha sido prospectado.

#### Possiveis Causas:

**Causa 1: Lead nao tem telefone/email/ig_handle registrado**
- O match busca por multiplos identificadores
- Se nenhum bate, retorna false
- **Verificacao:** Veja os dados do lead no AgenticOS
- **Acao:** Garantir que o lead foi salvo corretamente na Etapa 2

**Causa 2: Username diferente**
- @ foi incluido no username
- Maiusculas/minusculas diferentes
- **Verificacao:** Compare o username no GHL vs AgenticOS
- **Acao:** Padronizar sempre sem @ e em minusculas

**Causa 3: Tenant ID incorreto**
- Lead foi salvo em outro tenant
- **Verificacao:** Verificar tenant_id na busca
- **Acao:** Sempre usar `tenant_id=mottivme`

#### Identificadores Usados para Match (ordem de prioridade):

1. `ghl_contact_id` - Match direto se ja sincronizado
2. `phone` - Telefone normalizado (+55...)
3. `email` - Email em minusculas
4. `ig_handle` - Username do Instagram

### 3.3 WORKFLOW NAO EXECUTOU

**Sintoma:** Mensagem chegou no GHL mas nao aparece execucao no n8n

#### Verificacoes:

1. **Workflow esta ativo?**
   - No n8n, verifique se o toggle do workflow esta verde
   - Se estiver cinza, clique para ativar

2. **Webhook esta configurado no GHL?**
   - Va em GHL > Automation > Webhooks
   - Verifique se existe webhook apontando para n8n
   - URL deve ser: `https://cliente-a1.mentorfy.io/webhook/...`

3. **Teste manual do webhook:**
   ```bash
   curl -X POST "https://cliente-a1.mentorfy.io/webhook/R2fVs2qpct1Qr2Y1" \
     -H "Content-Type: application/json" \
     -d '{"test": true}'
   ```
   - Deve retornar resposta sem erro

### 3.4 IA CLASSIFICOU INCORRETAMENTE

**Sintoma:** Lead bom marcado como SPAM, ou SPAM marcado como LEAD_QUENTE

#### Acoes:

1. **Revise a mensagem do lead**
   - Abra a execucao no n8n
   - Veja o node de classificacao
   - Analise se a classificacao faz sentido

2. **Se foi erro claro:**
   - Corrija manualmente no GHL
   - Remova tag incorreta
   - Adicione tag correta
   - Atualize campo `ativar_ia` se necessario

3. **Se acontece frequentemente:**
   - Reportar ao suporte tecnico
   - Prompt de classificacao pode precisar de ajuste

### 3.5 AGENTE IA NAO ESTA RESPONDENDO

**Sintoma:** Tag aplicada, ativar_ia = sim, mas IA nao responde

#### Verificacoes:

1. **Campo `ativar_ia` esta correto?**
   - Deve estar exatamente = "sim" (minusculo)

2. **Campo `agente_ia` esta preenchido?**
   - Deve ter "SDR Prospeccao" ou "SDR Inbound"

3. **Tag `ia-ativada` esta presente?**
   - Esta tag confirma que automacao GHL rodou

4. **Automacao GHL esta ativa?**
   - Va em Automations no GHL
   - Verifique se as automacoes de IA estao ativas

---

## 4. COMO VALIDAR ACERTOS

### 4.1 Checklist de Validacao - Lead de Prospeccao

Use este checklist para validar se um lead de prospeccao foi processado corretamente:

```
CHECKLIST DE VALIDACAO - PROSPECCAO
===================================

LEAD: ______________________________
DATA: ______________________________

ETAPA 1 - LEAD RESPONDEU
[ ] Lead enviou mensagem no Instagram
[ ] Mensagem aparece no GHL (Conversas)

ETAPA 2 - N8N PROCESSOU
[ ] Execucao aparece no n8n
[ ] Status da execucao: SUCCESS
[ ] IF "Veio de Trafego" = FALSE (nao bloqueou)

ETAPA 3 - MATCH NO AGENTICOS
[ ] Match retornou TRUE
[ ] Dados do lead foram recuperados

ETAPA 4 - TAG APLICADA
[ ] Tag "lead-prospectado-ia" presente no GHL
    OU
[ ] Tag "lead-classificado-ia" presente no GHL

ETAPA 5 - CAMPOS ATUALIZADOS
[ ] ativar_ia = "sim"
[ ] agente_ia = preenchido
[ ] data_ativacao_ia = preenchido

ETAPA 6 - IA ATIVA
[ ] Tag "ia-ativada" presente
[ ] Agente IA comecou a responder

RESULTADO: [ ] OK  [ ] FALHA

Se FALHA, descreva:
_______________________________________
_______________________________________
```

### 4.2 Checklist de Validacao - Lead de Trafego (nao prospectado)

```
CHECKLIST DE VALIDACAO - TRAFEGO
================================

LEAD: ______________________________
DATA: ______________________________

[ ] Lead tem utm_source preenchido
[ ] Lead tem utm_medium preenchido
[ ] IF "Veio de Trafego" = TRUE (bloqueou corretamente)
[ ] Lead NAO recebeu tag de prospeccao
[ ] Lead segue fluxo normal de trafego

RESULTADO: [ ] OK  [ ] FALHA
```

### 4.3 Indicadores de Sucesso Diario

| Metrica | Meta | Como Verificar |
|---------|------|----------------|
| Taxa de Match | > 90% | Leads matchados / Leads que responderam |
| Execucoes com Sucesso | > 95% | No n8n, filtrar por Success |
| Tags Aplicadas | 100% dos processados | Verificar contatos no GHL |
| IA Ativada | 100% dos qualificados | Verificar campo ativar_ia |

### 4.4 Relatorio Diario Simplificado

Execute ao final de cada dia:

```
RELATORIO DIARIO - PROSPECCAO
Data: ____/____/______

1. VOLUME
   - Mensagens recebidas: ____
   - Processadas com sucesso: ____
   - Erros: ____

2. CLASSIFICACAO
   - LEAD_QUENTE: ____
   - LEAD_MORNO: ____
   - LEAD_FRIO: ____
   - SPAM/PESSOAL: ____

3. PROBLEMAS IDENTIFICADOS
   _______________________________
   _______________________________

4. ACOES PENDENTES
   _______________________________
   _______________________________

Responsavel: ____________________
```

---

## 5. COMANDOS UTEIS

### 5.1 Verificar Execucoes do Workflow via API

```bash
# Ver ultimas 5 execucoes
curl -s "https://cliente-a1.mentorfy.io/api/v1/executions?workflowId=R2fVs2qpct1Qr2Y1&limit=5" \
  -H "X-N8N-API-KEY: [SUA_API_KEY]"
```

### 5.2 Verificar Lead no AgenticOS

```bash
# Buscar por username
curl -s -X GET "https://agenticoskevsacademy-production.up.railway.app/api/leads?username=PERFIL_INSTAGRAM&tenant_id=mottivme" \
  -H "Content-Type: application/json"
```

### 5.3 Testar Match de Lead

```bash
# Simular chegada de mensagem
curl -s -X POST "https://agenticoskevsacademy-production.up.railway.app/webhook/inbound-dm" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "PERFIL_INSTAGRAM",
    "message": "",
    "tenant_id": "mottivme"
  }'
```

### 5.4 Testar Webhook do n8n

```bash
# Enviar payload de teste
curl -X POST "https://cliente-a1.mentorfy.io/webhook/R2fVs2qpct1Qr2Y1" \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "teste123",
    "instagram_username": "perfil_teste",
    "message": "Mensagem de teste",
    "channel": "instagram",
    "utm_source": null
  }'
```

### 5.5 Verificar Status do Workflow

```bash
# Ver detalhes do workflow
curl -s "https://cliente-a1.mentorfy.io/api/v1/workflows/R2fVs2qpct1Qr2Y1" \
  -H "X-N8N-API-KEY: [SUA_API_KEY]"
```

---

## 6. CONTATOS PARA SUPORTE

### Matriz de Escalacao

| Problema | Nivel 1 | Nivel 2 | Nivel 3 |
|----------|---------|---------|---------|
| Duvidas de uso | Este manual | Supervisor | - |
| Erro no n8n | Verificar execucao | Suporte Tecnico | Marcos |
| Erro no GHL | Verificar contato | Suporte Tecnico | Marcos |
| Erro no AgenticOS | Verificar API | Suporte Tecnico | Marcos |
| IA classificando errado | Coletar exemplos | Suporte Tecnico | Marcos |
| Sistema fora do ar | Verificar status | Suporte Tecnico | Marcos |

### Canais de Suporte

| Sistema | Responsavel | Contato |
|---------|-------------|---------|
| **n8n** | Equipe MOTTIVME | suporte@mottivme.com |
| **GoHighLevel** | Equipe MOTTIVME | suporte@mottivme.com |
| **AgenticOS** | Equipe MOTTIVME | suporte@mottivme.com |
| **Geral / Urgente** | Marcos Daniels | [Slack/WhatsApp interno] |

### Informacoes para Reportar Problema

Ao reportar um problema, sempre inclua:

1. **Data e hora** do problema
2. **Nome/username** do lead afetado
3. **Screenshot** da tela com erro (se aplicavel)
4. **ID da execucao** no n8n (se aplicavel)
5. **Descricao** do comportamento esperado vs. ocorrido

---

## ANEXO A - GLOSSARIO

| Termo | Significado |
|-------|-------------|
| **AgenticOS** | Sistema backend que armazena e processa leads |
| **GHL** | GoHighLevel - CRM principal |
| **Match** | Processo de encontrar lead no banco de dados |
| **n8n** | Ferramenta de automacao (orquestrador) |
| **Scrape** | Coleta automatica de dados publicos |
| **Tag** | Etiqueta para categorizar contatos no CRM |
| **Tenant** | Identificador da conta (mottivme) |
| **UTM** | Parametros de rastreamento de origem |
| **Webhook** | Gatilho automatico entre sistemas |
| **Workflow** | Fluxo automatizado no n8n |

---

## ANEXO B - DIAGRAMA VISUAL DO FLUXO

```
+------------------+     +------------------+     +------------------+
|   INSTAGRAM      |     |     AGENTICOS    |     |    PLAYWRIGHT    |
|                  |     |                  |     |                  |
|  Perfil alvo     |---->|  Scrape dados    |---->|  Envia DM        |
|  identificado    |     |  Salva lead      |     |  personalizada   |
+------------------+     +------------------+     +------------------+
                                                          |
                                                          v
                                                  [LEAD RESPONDE]
                                                          |
                                                          v
+------------------+     +------------------+     +------------------+
|       GHL        |     |       N8N        |     |       GHL        |
|                  |     |                  |     |                  |
|  Recebe msg      |---->|  Webhook         |---->|  Tag aplicada    |
|  via Instagram   |     |  Classifica      |     |  ativar_ia=sim   |
+------------------+     +------------------+     +------------------+
                                                          |
                                                          v
                                                +------------------+
                                                |    AGENTE IA     |
                                                |                  |
                                                |  Assume conversa |
                                                |  Qualifica lead  |
                                                +------------------+
```

---

## ANEXO C - FLUXO DE DECISAO DO WORKFLOW

```
                        [WEBHOOK GHL]
                              |
                              v
                    /------------------\
                   | Lead tem UTM?      |
                    \------------------/
                      |            |
                     SIM          NAO
                      |            |
                      v            v
                   [SKIP]    [MATCH AGENTICOS]
               Lead de              |
               trafego              v
                            /------------------\
                           | matched = true?    |
                            \------------------/
                              |            |
                             SIM          NAO
                              |            |
                              v            v
                       [TAG:          [CLASSIFICAR
                       lead-            COM IA]
                       prospectado        |
                       -ia]               v
                              |    /------------------\
                              |   | Resultado IA?      |
                              |    \------------------/
                              |      |    |    |    |
                              |    QUENTE MORNO FRIO SPAM
                              |      |    |    |    |
                              |      v    v    v    v
                              |   [TAG:        [TAG:
                              |   lead-        perdido]
                              |   classificado
                              |   -ia]
                              |      |
                              +------+
                                     |
                                     v
                            /------------------\
                           | Ja ativou IA?      |
                            \------------------/
                              |            |
                             SIM          NAO
                              |            |
                              v            v
                           [SKIP]    [UPDATE GHL]
                         Ja             ativar_ia=sim
                         processado     agente_ia=XXX
```

---

## ANEXO D - CHECKLIST OPERACIONAL

### Diario

- [ ] Verificar se workflow n8n esta ativo
- [ ] Checar fila de mensagens nao processadas
- [ ] Revisar leads classificados como SPAM (falsos positivos)
- [ ] Monitorar rate limits do Instagram

### Semanal

- [ ] Analisar metricas de conversao
- [ ] Ajustar mensagens de prospeccao se necessario
- [ ] Revisar precisao da classificacao IA
- [ ] Atualizar lista de perfis alvo

### Mensal

- [ ] Gerar relatorio completo de performance
- [ ] Revisar e otimizar prompt de classificacao
- [ ] Atualizar automacoes GHL se necessario
- [ ] Backup de dados AgenticOS

---

## ANEXO E - METRICAS DE SUCESSO

### KPIs Principais

| Metrica | Meta | Calculo |
|---------|------|---------|
| Taxa de Resposta | > 15% | Respostas / DMs enviadas |
| Taxa de Match | > 90% | Leads matchados / Leads que responderam |
| Precisao IA | > 85% | Classificacoes corretas / Total classificado |
| Conversao para Oportunidade | > 5% | Oportunidades / Leads classificados |

---

*Manual criado para uso interno MOTTIVME*
*Versao 2.0 - Janeiro 2026*
*Duvidas: suporte@mottivme.com*
*NAO COMPARTILHAR EXTERNAMENTE*
