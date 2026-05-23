import asyncio
import re
import requests
from playwright.async_api import async_playwright

TOKEN = "8843148366:AAGcapDQk_NcjVmVkR-pahZeObjSrq_SNcA"
CHAT_ID = "7727821551"

BASE_URL = "https://www.sporting.com.ar/ofertas?initialMap=category-1,ofertas&initialQuery=sporting/ofertas&map=category-1,category-2,genero,genero,ofertas&order=OrderByPriceASC&query=/sporting/calzado/hombre/mujer/ofertas&searchState"

# ALERTAS SOLO POR DEBAJO DE ESTE PRECIO
PRECIO_MAXIMO = 39000


# =========================
# TELEGRAM
# =========================

def enviar_telegram(mensaje):

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": mensaje
        }
    )


# =========================
# LIMPIAR PRECIO
# =========================

def limpiar_precio(texto):

    numeros = re.sub(r"[^\d]", "", texto)

    if numeros.isdigit():
        return int(numeros)

    return None


# =========================
# MAIN
# =========================

async def main():

    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=True)

        page = await browser.new_page()

        mensajes = []

        # RECORRER PÁGINAS
        for numero_pagina in range(1, 6):

            url = BASE_URL + f"&page={numero_pagina}"

            print(f"\nAbriendo: {url}")

            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=120000
            )

            await page.wait_for_timeout(6000)

            productos = await page.locator("article").all()

            print(f"Productos encontrados: {len(productos)}")

            for producto in productos:

                try:

                    texto = await producto.inner_text()

                    lineas = [
                        l.strip()
                        for l in texto.split("\n")
                        if l.strip()
                    ]

                    if len(lineas) < 2:
                        continue

                    nombre = lineas[0]

                    precios = []

                    for linea in lineas:

                        if "$" in linea:

                            precio = limpiar_precio(linea)

                            if precio:
                                precios.append(precio)

                    if not precios:
                        continue

                    # TOMA EL PRECIO MÁS BAJO
                    precio_final = min(precios)

                    print(nombre, precio_final)

                    # SOLO OFERTAS MENORES AL LÍMITE
                    if precio_final <= PRECIO_MAXIMO:

                        # BUSCAR LINK DEL PRODUCTO
                        link = await producto.locator("a").first.get_attribute("href")

                        if link:

                            if not link.startswith("http"):
                                link = "https://www.sporting.com.ar" + link

                        else:
                            link = "https://www.sporting.com.ar"

                        mensaje = (
                            f"🔥 OFERTA SPORTING\n\n"
                            f"👟 {nombre}\n"
                            f"💲 ${precio_final}\n\n"
                            f"{link}"
                        )

                        # EVITAR REPETIDOS
                        if mensaje not in mensajes:
                            mensajes.append(mensaje)

                except Exception as e:
                    print("ERROR:", e)

        await browser.close()

        # SOLO ENVÍA SI HAY OFERTAS
        if mensajes:

            texto_final = "\n\n──────────────\n\n".join(mensajes[:10])

            enviar_telegram(texto_final)

        else:
            print("No se encontraron ofertas.")


asyncio.run(main())
