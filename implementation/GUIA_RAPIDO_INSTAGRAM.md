# 🚀 Guia Rápido - Instagram Followers Downloader

## ⚡ Instalação Rápida

### 1. Instalar Biblioteca
```bash
cd implementation
pip install instaloader
```

### 2. Executar Script
```bash
python3 instagram_followers_downloader.py
```

## 📝 Como Usar

### Modo Interativo

Quando executar, você será perguntado:

1. **Seu username do Instagram**: `seu_usuario`
2. **Sua senha**: `********`
3. **Perfil alvo**: (deixe vazio para usar seu perfil)
4. **Formato**: Escolha 1, 2, 3 ou 4

### Exemplo de Execução

```
INSTAGRAM FOLLOWERS DOWNLOADER
============================================================

Seu username do Instagram: mottivme
Sua senha: ********

Username do perfil (deixe vazio para usar o seu próprio):

Formatos de exportação:
1 - CSV (completo)
2 - JSON (completo)
3 - TXT (apenas usernames)
4 - Todos os formatos
Escolha (1-4): 4
```

## 📊 Resultados

Você receberá 3 arquivos (se escolher opção 4):

### 1. CSV Completo
```csv
username,full_name,followers_count,posts_count,...
joao123,João Silva,500,42,...
```

### 2. JSON Detalhado
```json
{
  "username": "joao123",
  "full_name": "João Silva",
  "followers_count": 500
}
```

### 3. Lista Simples
```
joao123
maria_santos
pedro_oliveira
```

## 🔐 Credenciais Seguras (Opcional)

Crie arquivo `.env`:
```bash
INSTAGRAM_USERNAME=seu_usuario
INSTAGRAM_PASSWORD=sua_senha
```

Use no script:
```python
from dotenv import load_dotenv
import os

load_dotenv()
username = os.getenv('INSTAGRAM_USERNAME')
password = os.getenv('INSTAGRAM_PASSWORD')
```

## ⚡ Exportar Direto para Google Sheets

```bash
python3 instagram_to_sheets.py
```

Você precisará de:
- ✅ Arquivo `service_account.json` (credenciais Google)
- ✅ Credenciais do Instagram

## ⚠️ Avisos Importantes

### Rate Limiting
- Instagram limita requisições
- Para muitos seguidores (>10k), pode demorar horas
- Script pausa automaticamente a cada 100 seguidores

### Bloqueios
Se receber erro "rate limit":
1. Aguarde 24-48 horas
2. Tente novamente

### Segurança
- Use conta secundária para testes
- Nunca compartilhe suas credenciais
- Desabilite 2FA temporariamente

## 🐛 Problemas Comuns

### "Bad credentials"
✅ Verifique username e senha

### "Two factor auth required"
✅ Desabilite 2FA nas configurações do Instagram

### "Challenge required"
✅ Instagram detectou atividade suspeita
✅ Aguarde 24-48 horas

## 📚 Exemplo de Código

```python
from instagram_followers_downloader import InstagramFollowersDownloader

# Criar downloader
downloader = InstagramFollowersDownloader('seu_usuario', 'sua_senha')

# Login
downloader.login()

# Baixar seguidores
followers = downloader.get_followers()  # Seu perfil
# ou
followers = downloader.get_followers('perfil_alvo')  # Outro perfil

# Exportar
downloader.export_to_csv(followers)
downloader.export_to_json(followers)
```

## 🎯 Casos de Uso

### 1. Análise de Audiência
Entenda quem são seus seguidores:
- Contas verificadas
- Contas privadas vs públicas
- Engajamento médio

### 2. Backup de Seguidores
Tenha uma cópia dos seus seguidores

### 3. Análise Competitiva
Compare seguidores de competidores

### 4. Lead Generation
Identifique potenciais clientes

## 🔗 Integração com Google Sheets

```python
# Após baixar seguidores
from instagram_to_sheets import InstagramToSheets

sheets = InstagramToSheets()
sheets.authenticate()
sheets.export_followers(followers, "Meus Seguidores Instagram")
```

## 💡 Dicas

1. **Primeira execução**: Teste com perfil pequeno (<1k seguidores)
2. **Sessões**: O script salva sua sessão automaticamente
3. **Logs**: Verifique `instagram_followers.log` para debug
4. **Pausas**: Quanto mais seguidores, mais tempo demora

## 📞 Suporte

Veja documentação completa em `README_INSTAGRAM.md`

---

**Desenvolvido para MOTTIVME** 🚀
