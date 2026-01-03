import requests
import json

SESSION_ID = "258328766:EKJ8m0QEivWYrN:26:AYhUMNhVmKHrhGMaUHaGq8g0VeaX8khoySa6eU2mfw"

headers = {
    'User-Agent': 'Instagram 275.0.0.27.98 Android',
    'Cookie': f'sessionid={SESSION_ID}',
    'X-IG-App-ID': '936619743392459'
}

# 1. Buscar perfil
print("🔍 Buscando @theodorelewisusa...")
r = requests.get(
    "https://i.instagram.com/api/v1/users/web_profile_info/?username=theodorelewisusa",
    headers=headers
)

user = r.json()['data']['user']
bio = user['biography']
name = user['full_name']
user_id = user['id']

print(f"✅ {name}")
print(f"📝 Bio: {bio}")

# 2. Mensagem personalizada
msg = f"""Oi {name}! 👋

To na call com você e a Flavia AGORA e nem mexi as mãos pra escrever isso!

Vi no seu perfil que você trabalha com a Flavia na Beauty School - transformando o mercado de estética nos EUA! 🇺🇸

Isso é IA analisando sua bio em tempo real e mandando msg personalizada.

Imagina isso abordando leads da escola automaticamente...

🚀 Marcos Daniel (via IA)"""

print(f"\n📤 Enviando DM...")

# 3. Enviar
dm = requests.post(
    "https://i.instagram.com/api/v1/direct_v2/threads/broadcast/text/",
    headers=headers,
    data={
        'recipient_users': json.dumps([user_id]),
        'action': 'send_item', 
        'text': msg
    }
)

if dm.status_code == 200:
    print("✅ DM ENVIADA! Theo vai ver agora! 🎉")
else:
    print(f"❌ Erro: {dm.status_code}")
    print(dm.text[:300])
