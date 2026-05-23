
import asyncio
import re
import requests
from urllib.parse import urljoin
from playwright.async_api import async_playwright

TOKEN = "8843148366:AAGcapDQk_NcjVmVkR-pahZeObjSrq_SNcA"
CHAT_ID = "7727821551"

BASE_URL = "https://www.sporting.com.ar/ofertas?initialMap=category-1,ofertas&initialQuery=sporting/ofertas&map=category-1,category-2,genero,genero,ofertas&order=OrderByPriceASC&query=/sporting/calzado/hombre/mujer/ofertas&searchState"

PRECIO_MAXIMO = 39000
PAGINAS_A_REVISAR = 5


def enviar_telegram(mensaje: str) -> None:
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": mensaje},
            timeout=20,
        )
    except Exception as e:
        print("Error enviando Telegram:", e)


def extraer_precios(texto: str) -> list[int]:
    precios = []
    for match in re.findall(r"\$\s*([0-9][0-9\.\,]*)", texto):
        limpio = match.replace(".", "").replace(",", "")
        if limpio.isdigit():
            precios.append(int(limpio))
    return precios


async def buscar_tarjetas(page):
    selectores = [
        'a.vtex-product-summary-2-x-clearLink',
        '.vtex-product-summary-2-x-container',
        'article',
        '[data-testid="product-card"]',
    ]

    for selector in selectores:
        loc = page.locator(selector)
        try:
            cantidad = await loc.count()
        except Exception:
            cantidad = 0

        if cantidad > 0:
            print(f"Selector usado: {selector} ({cantidad})")
            return loc

    return None


async def obtener_link_producto(card):
    try:
        anchors = card.locator("a")
        total = await anchors.count()

        for i in range(total):
            href = await anchors.nth(i).get_attribute("href")
            if not href:
                continue

            link = urljoin("https://www.sporting.com.ar", href)

            if "sporting.com.ar" in link:
                return link

        return None
    except Exception:
        return None


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1600, "height": 2200})

        encontrados = []
        vistos = set()

        for numero_pagina in range(1, PAGINAS_A_REVISAR + 1):
            url = f"{BASE_URL}&page={numero_pagina}"
            print(f"Abriendo: {url}")

            await page.goto(url, wait_until="domcontentloaded", timeout=120000)
            await page.wait_for_timeout(10000)

            for _ in range(4):
                await page.mouse.wheel(0, 3500)
                await page.wait_for_timeout(2000)

            tarjetas = await buscar_tarjetas(page)
            if tarjetas is None:
                print("No se encontraron tarjetas en esta página.")
                continue

            total = await tarjetas.count()
            print(f"Tarjetas encontradas: {total}")

            for i in range(total):
                try:
                    card = tarjetas.nth(i)
                    texto = (await card.inner_text()).strip()

                    if not texto:
                        continue

                    lineas = [l.strip() for l in texto.split("\n") if l.strip()]
                    if len(lineas) < 2:
                        continue

                    nombre = lineas[0]
                    precios = extraer_precios(texto)

                    if not precios:
                        continue

                    precio_final = min(precios)
                    print(nombre, precio_final)

                    if precio_final <= PRECIO_MAXIMO:
                        link = await obtener_link_producto(card)
                        if not link:
                            link = "https://www.sporting.com.ar/ofertas"

                        key = f"{nombre}|{precio_final}|{link}"
                        if key in vistos:
                            continue

                        vistos.add(key)
                        encontrados.append(
                            f"🔥 OFERTA SPORTING\n\n"
                            f"👟 {nombre}\n"
                            f"💲 ${precio_final}\n\n"
                            f"{link}"
                        )

                except Exception as e:
                    print("ERROR tarjeta:", e)

        await browser.close()

        if encontrados:
            mensaje_final = "\n\n──────────────\n\n".join(encontrados[:10])
            enviar_telegram(mensaje_final)


asyncio.run(main())
