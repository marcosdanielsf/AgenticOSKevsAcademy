# Instagram Followers Downloader

## 📋 Descrição

Script Python para baixar todos os seguidores de um perfil do Instagram e exportar em múltiplos formatos (CSV, JSON, TXT).

## ✨ Características

- ✅ Baixa lista completa de seguidores
- ✅ Exporta em múltiplos formatos (CSV, JSON, TXT)
- ✅ Coleta dados detalhados de cada seguidor:
  - Username
  - Nome completo
  - Biografia
  - Verificado/Privado
  - Contagem de seguidores/seguindo/posts
  - URL do perfil
  - Link externo
  - Tipo de conta (pessoal/business)
- ✅ Sistema de sessão (não precisa fazer login toda vez)
- ✅ Rate limiting automático (evita bloqueio)
- ✅ Logging detalhado

## 🚀 Instalação

### 1. Instalar dependências

```bash
cd implementation
pip install -r instagram_requirements.txt
```

### 2. Configurar credenciais

Você precisará de:
- Seu username do Instagram
- Sua senha do Instagram

**⚠️ IMPORTANTE**:
- Recomendo criar uma conta secundária do Instagram para testes
- Desabilite autenticação de 2 fatores temporariamente
- O Instagram pode bloquear temporariamente se detectar muitas requisições

## 📖 Como Usar

### Modo Interativo (Recomendado)

```bash
python3 instagram_followers_downloader.py
```

O script irá solicitar:
1. Seu username do Instagram
2. Sua senha
3. Username do perfil alvo (deixe vazio para usar seu próprio perfil)
4. Formato de exportação

### Exemplo de Uso

```
INSTAGRAM FOLLOWERS DOWNLOADER
============================================================

Seu username do Instagram: seu_usuario
Sua senha: ********

Username do perfil (deixe vazio para usar o seu próprio): perfil_alvo

Formatos de exportação:
1 - CSV (completo)
2 - JSON (completo)
3 - TXT (apenas usernames)
4 - Todos os formatos
Escolha (1-4): 4

============================================================
✅ Login realizado e sessão salva
============================================================
Buscando perfil de perfil_alvo...
Total de seguidores: 5432
Baixando lista de seguidores... (isso pode demorar)
Progresso: 50/5432 seguidores baixados
Progresso: 100/5432 seguidores baixados
...
✅ Total de 5432 seguidores baixados
============================================================
✅ CSV exportado: instagram_followers_20251231_143022.csv
✅ JSON exportado: instagram_followers_20251231_143022.json
✅ Lista de usernames exportada: instagram_followers_usernames_20251231_143022.txt
============================================================
✅ PROCESSO CONCLUÍDO!
Total de seguidores baixados: 5432
============================================================
```

## 📊 Formatos de Exportação

### CSV (Completo)
Arquivo CSV com todas as informações de cada seguidor:
```csv
username,full_name,user_id,is_verified,is_private,followers_count,...
joao123,João Silva,123456789,False,False,500,350,42,...
maria_santos,Maria Santos,987654321,False,True,1200,890,156,...
```

### JSON (Completo)
Arquivo JSON estruturado:
```json
[
  {
    "username": "joao123",
    "full_name": "João Silva",
    "user_id": 123456789,
    "is_verified": false,
    "is_private": false,
    "followers_count": 500,
    "following_count": 350,
    "posts_count": 42,
    "biography": "Desenvolvedor Python",
    "external_url": "https://github.com/joao",
    "profile_pic_url": "https://...",
    "is_business_account": false,
    "collected_at": "2025-12-31T14:30:22"
  }
]
```

### TXT (Lista Simples)
Arquivo de texto com apenas os usernames:
```
joao123
maria_santos
pedro_oliveira
```

## 🔧 Uso Programático

Você também pode usar a classe diretamente em seus scripts:

```python
from instagram_followers_downloader import InstagramFollowersDownloader

# Inicializar
downloader = InstagramFollowersDownloader(
    username="seu_usuario",
    password="sua_senha"
)

# Login
if downloader.login():
    # Baixar seguidores
    followers = downloader.get_followers()  # Seus próprios seguidores
    # ou
    followers = downloader.get_followers("perfil_alvo")  # Seguidores de outro perfil

    # Exportar
    downloader.export_to_csv(followers)
    downloader.export_to_json(followers)
    downloader.export_simple_list(followers)
```

## 🔐 Sessões

O script salva sua sessão do Instagram em um arquivo `session-{username}`. Isso permite:
- Não precisar fazer login toda vez
- Evitar bloqueios por múltiplos logins
- Retomar download se interrompido

**Para limpar sessão:**
```bash
rm session-*
```

## ⚠️ Limitações e Avisos

### Rate Limiting
- O Instagram limita o número de requisições por período
- O script inclui pausas automáticas (10s a cada 100 seguidores)
- Para perfis com muitos seguidores (>10k), o processo pode demorar horas

### Bloqueios Temporários
Se você receber erro de rate limit:
1. Pare o script
2. Aguarde 24-48 horas
3. Tente novamente com pausas maiores

### Privacidade
- Você só pode ver seguidores de:
  - Seu próprio perfil
  - Perfis públicos
  - Perfis privados que você segue

### Termos de Serviço
- Este script é para uso educacional
- Respeite a privacidade dos usuários
- Use com responsabilidade

## 📝 Logs

Todos os eventos são registrados em `instagram_followers.log`:
```
2025-12-31 14:30:22 - INFO - Fazendo login como seu_usuario...
2025-12-31 14:30:25 - INFO - ✅ Login realizado e sessão salva
2025-12-31 14:30:30 - INFO - Buscando perfil de perfil_alvo...
2025-12-31 14:30:32 - INFO - Total de seguidores: 5432
```

## 🐛 Troubleshooting

### "Bad credentials"
- Verifique username e senha
- Tente fazer login manual no Instagram primeiro

### "Two factor auth required"
- Desabilite 2FA temporariamente nas configurações do Instagram
- Ou use código de backup manualmente

### "Login required / Session expired"
- Delete o arquivo de sessão: `rm session-*`
- Faça login novamente

### "Challenge required"
- O Instagram detectou atividade suspeita
- Aguarde 24-48 horas
- Verifique seu email/notificações do Instagram

### Rate Limit
- Aguarde antes de tentar novamente
- Use pausas maiores entre requisições
- Divida em múltiplas sessões

## 🔄 Integração com Google Sheets

Para enviar direto para Google Sheets, você pode adicionar:

```python
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def export_to_sheets(followers, sheet_name):
    # Autenticar
    scope = ['https://spreadsheets.google.com/feeds']
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        'service_account.json', scope
    )
    client = gspread.authorize(creds)

    # Abrir planilha
    sheet = client.open(sheet_name).sheet1

    # Limpar e adicionar header
    sheet.clear()
    if followers:
        headers = list(followers[0].keys())
        sheet.append_row(headers)

        # Adicionar dados
        for follower in followers:
            sheet.append_row(list(follower.values()))
```

## 📚 Referências

- [Instaloader Documentation](https://instaloader.github.io/)
- [Instagram API Limits](https://developers.facebook.com/docs/instagram-api/overview)

## 📄 Licença

MIT License - Use livremente, mas com responsabilidade.
