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


def limpiar_numero(texto: str) -> int | None:
    numeros = re.sub(r"[^\d]", "", texto)
    if numeros.isdigit():
        return int(numeros)
    return None


def extraer_precio_real(texto: str) -> int | None:
    lineas = [l.strip() for l in texto.split("\n") if l.strip()]

    # 1) Primero buscar una línea con porcentaje de descuento
    #    porque ahí suele estar el precio real con descuento.
    for linea in lineas:
        linea_minuscula = linea.lower()

        if "cuotas" in linea_minuscula:
            continue

        if "%" in linea and "$" in linea:
            precios = re.findall(r"\$\s*([0-9][0-9\.\,]*)", linea)
            if precios:
                candidatos = []
                for p in precios:
                    limpio = p.replace(".", "").replace(",", "")
                    if limpio.isdigit():
                        candidatos.append(int(limpio))
                if candidatos:
                    return min(candidatos)

    # 2) Si no hubo línea con %, buscar una línea de precio normal
    #    pero ignorando cuotas.
    for linea in lineas:
        linea_minuscula = linea.lower()

        if "cuotas" in linea_minuscula:
            continue

        if "$" in linea:
            precios = re.findall(r"\$\s*([0-9][0-9\.\,]*)", linea)
            if precios:
                limpio = precios[0].replace(".", "").replace(",", "")
                if limpio.isdigit():
                    return int(limpio)

    return None


async def obtener_tarjetas(page):
    selectores = [
        "article",
        'a.vtex-product-summary-2-x-clearLink',
        ".vtex-product-summary-2-x-container",
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

        return "https://www.sporting.com.ar/ofertas"
    except Exception:
        return "https://www.sporting.com.ar/ofertas"


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

            # scroll suave para que cargue el contenido dinámico
            for _ in range(3):
                await page.mouse.wheel(0, 3000)
                await page.wait_for_timeout(2000)

            tarjetas = await obtener_tarjetas(page)
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
                    precio_real = extraer_precio_real(texto)

                    if precio_real is None:
                        continue

                    print(nombre, precio_real)

                    if precio_real <= PRECIO_MAXIMO:
                        link = await obtener_link_producto(card)

                        key = f"{nombre}|{precio_real}|{link}"
                        if key in vistos:
                            continue
                        vistos.add(key)

                        encontrados.append(
                            f"🔥 OFERTA SPORTING\n\n"
                            f"👟 {nombre}\n"
                            f"💲 ${precio_real}\n\n"
                            f"{link}"
                        )

                except Exception as e:
                    print("ERROR tarjeta:", e)

        await browser.close()

        if encontrados:
            mensaje_final = "\n\n──────────────\n\n".join(encontrados[:10])
            enviar_telegram(mensaje_final)


asyncio.run(main())
