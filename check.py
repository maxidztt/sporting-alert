import asyncio
import re
import requests
from playwright.async_api import async_playwright

TOKEN = "8843148366:AAGcapDQk_NcjVmVkR-pahZeObjSrq_SNcA"
CHAT_ID = "7727821551"
URL = "https://www.sporting.com.ar/sporting/calzado"
PRECIO_LIMITE = 10000

def enviar_mensaje(texto: str):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": texto},
        timeout=20
    )

def extraer_precio(texto: str):
    m = re.search(r"\$\s*([0-9\.]+)", texto)
    if not m:
        return None
    return int(m.group(1).replace(".", ""))

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1600, "height": 2200})
        await page.goto(URL, wait_until="networkidle", timeout=60000)

        cards = await page.locator("div.vtex-product-summary-2-x-container").count()

        if cards == 0:
            await browser.close()
            enviar_mensaje("No encontré productos en Sporting. El selector no coincidió con la página.")
            return

        encontrados = []

        for i in range(cards):
            card = page.locator("div.vtex-product-summary-2-x-container").nth(i)
            texto = (await card.inner_text()).strip()
            precio = extraer_precio(texto)

            if precio is not None and precio <= PRECIO_LIMITE:
                enlace = await card.locator("a").first.get_attribute("href")
                if enlace and enlace.startswith("/"):
                    enlace = "https://www.sporting.com.ar" + enlace
                encontrados.append(f"🔥 {texto}\nPrecio: ${precio}\n{enlace or URL}")

        await browser.close()

        if encontrados:
            enviar_mensaje("\n\n".join(encontrados[:3]))
        else:
            enviar_mensaje("No encontré zapatillas por debajo del precio límite.")

asyncio.run(main())
