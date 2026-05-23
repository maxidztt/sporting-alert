
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
    matches = re.findall(r"\$\s*([0-9\.\,]+)", texto)
    if not matches:
        return None

    precios = []
    for m in matches:
        limpio = m.replace(".", "").replace(",", "")
        if limpio.isdigit():
            precios.append(int(limpio))

    return min(precios) if precios else None


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1600, "height": 2200})

        await page.goto(URL, wait_until="domcontentloaded", timeout=120000)
        await page.wait_for_timeout(10000)

        cards = page.locator("div.vtex-product-summary-2-x-container")
        total = await cards.count()

        print("Productos encontrados:", total, flush=True)

        if total == 0:
            enviar_mensaje("No se encontraron productos en Sporting.")
            await browser.close()
            return

        encontrados = []

        for i in range(total):
            card = cards.nth(i)
            try:
                texto = (await card.inner_text()).strip()
            except:
                continue

            precio = extraer_precio(texto)

            if precio is not None and precio <= PRECIO_LIMITE:
                link = None
                try:
                    link = await card.locator("a").first.get_attribute("href")
                except:
                    pass

                if link and link.startswith("/"):
                    link = "https://www.sporting.com.ar" + link

                encontrados.append(
                    f"🔥 Oferta encontrada\n\n{texto}\n\nPrecio: ${precio}\n{link or URL}"
                )

        await browser.close()

        if encontrados:
            enviar_mensaje("\n\n".join(encontrados[:3]))
        else:
            enviar_mensaje("No encontré zapatillas por debajo del precio límite.")


asyncio.run(main())
