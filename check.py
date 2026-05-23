import asyncio
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

TOKEN = "8843148366:AAGcapDQk_NcjVmVkR-pahZeObjSrq_SNcA"
CHAT_ID = "7727821551"

URL = "https://www.sporting.com.ar/sporting/calzado"

PRECIO_LIMITE = 1000000


async def enviar_mensaje(texto):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    requests.get(url, params={
        "chat_id": CHAT_ID,
        "text": texto
    })


async def main():

    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=True)

        page = await browser.new_page()

        print("Abriendo Sporting...")

        await page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=120000
        )

        # Esperar a que carguen los productos
        await page.wait_for_timeout(10000)

        html = await page.content()

        soup = BeautifulSoup(html, "html.parser")

        productos = soup.find_all(
            "div",
            class_="vtex-product-summary-2-x-container"
        )

        print(f"Productos encontrados: {len(productos)}")

        if len(productos) == 0:
            await enviar_mensaje("❌ No se encontraron productos")
            return

        encontrados = 0

        for p in productos:

            texto = p.get_text(" ", strip=True)

            precios = []

            for s in texto.split():

                numero = s.replace(".", "").replace("$", "")

                if numero.isdigit():
                    precios.append(int(numero))

            if precios:

                precio = min(precios)

                if precio <= PRECIO_LIMITE:

                    mensaje = (
                        f"🔥 Oferta encontrada\n\n"
                        f"{texto}\n\n"
                        f"💲 Precio: ${precio}"
                    )

                    await enviar_mensaje(mensaje)

                    encontrados += 1

        if encontrados == 0:
            await enviar_mensaje("⚠️ No hay ofertas por debajo del límite")

        await browser.close()


asyncio.run(main())
