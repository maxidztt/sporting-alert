
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


def extraer_precios(texto: str):
    encontrados = re.findall(r"\$\s*([0-9][0-9\.\,]*)", texto)
    precios = []
    for p in encontrados:
        limpio = p.replace(".", "").replace(",", "")
        if limpio.isdigit():
            precios.append(int(limpio))
    return precios


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1600, "height": 2200})

        await page.goto(URL, wait_until="domcontentloaded", timeout=120000)
        await page.wait_for_timeout(12000)

        # bajar un poco para que carguen productos dinámicos
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, 1200)")
            await page.wait_for_timeout(4000)

        texto_total = await page.locator("body").inner_text()
        lineas = [l.strip() for l in texto_total.splitlines() if l.strip()]

        resultados = []
        vistos = set()

        for i, linea in enumerate(lineas):
            precios = extraer_precios(linea)
            if not precios:
                continue

            precio = min(precios)

            if precio <= PRECIO_LIMITE:
                contexto_inicio = max(0, i - 1)
                contexto_fin = min(len(lineas), i + 2)
                contexto = " | ".join(lineas[contexto_inicio:contexto_fin])

                if contexto not in vistos:
                    vistos.add(contexto)
                    resultados.append(
                        f"🔥 Oferta encontrada\n\n{contexto}\n\nPrecio: ${precio}"
                    )

        await browser.close()

        if resultados:
            enviar_mensaje("\n\n".join(resultados[:5]))
        else:
            enviar_mensaje("No encontré productos por debajo del precio límite.")

asyncio.run(main())
