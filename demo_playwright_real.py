import asyncio
from playwright.async_api import async_playwright

async def demo_abordagem():
    print("🚀 SOCIALFY AI - Demo Ao Vivo")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900}
        )
        
        await context.add_cookies([{
            'name': 'sessionid',
            'value': '258328766:EKJ8m0QEivWYrN:26:AYhUMNhVmKHrhGMaUHaGq8g0VeaX8khoySa6eU2mfw',
            'domain': '.instagram.com',
            'path': '/'
        }])
        
        page = await context.new_page()
        
        # 1. Vai pro perfil
        print("\n🔍 Acessando @theodorelewisusa...")
        await page.goto('https://www.instagram.com/theodorelewisusa/')
        await asyncio.sleep(4)
        
        # 2. Clica em Message/Enviar mensagem
        print("📤 Clicando em Mensagem...")
        try:
            # Tenta clicar no botão de mensagem
            btn = await page.locator('div[role="button"]:has-text("Message")').first
            await btn.click()
        except:
            try:
                btn = await page.locator('div[role="button"]:has-text("Enviar")').first
                await btn.click()
            except:
                # Clica pelo xpath
                await page.click('//div[contains(text(), "Message") or contains(text(), "Enviar")]')
        
        await asyncio.sleep(3)
        
        # 3. Digita a mensagem
        print("💬 Digitando mensagem personalizada...")
        
        msg = """Oi Theodore! 👋

To na call com você e a Flavia AGORA!

Vi que é CEO @clinicabrasilcare e Host @recordoficial 🎬

Isso é IA prospectando ao vivo!

🚀 Marcos"""

        # Encontra qualquer input de texto na página
        await page.keyboard.type(msg, delay=25)
        
        await asyncio.sleep(2)
        
        # 4. Envia (Enter ou botão)
        print("✅ Enviando...")
        await page.keyboard.press('Enter')
        
        await asyncio.sleep(3)
        print("\n🎉 FEITO!")
        
        print("\n⏳ Aberto por 60s - mostra na call!")
        await asyncio.sleep(60)
        await browser.close()

asyncio.run(demo_abordagem())
