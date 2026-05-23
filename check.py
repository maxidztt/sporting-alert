import asyncio
import re
import requests
from playwright.async_api import async_playwright

TOKEN = "8843148366:AAGcapDQk_NcjVmVkR-pahZeObjSrq_SNcA"
CHAT_ID = "7727821551"

URL = "https://www.sporting.com.ar/sporting/calzado"

PRECIO_MAXIMO = 35000


def enviar_telegram(mensaje):

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": mensaje
        }
    )


def limpiar_precio(texto):

    numeros = re.sub(r"[^\d]", "", texto)

    if numeros.isdigit():
        return int(numeros)

    return None


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

        await page.wait_for_timeout(12000)

        # scroll para cargar productos
        for _ in range(5):

            await page.mouse.wheel(0, 4000)

            await page.wait_for_timeout(3000)

        productos = await page.locator("article").all()

        print(f"Productos encontrados: {len(productos)}")

        mensajes = []

        for producto in productos:

            try:

                # link REAL
                link = None

                anchors = producto.locator("a")

                total_links = await anchors.count()

                for i in range(total_links):

                    href = await anchors.nth(i).get_attribute("href")

                    if href and "/p" in href:

                        if href.startswith("/"):
                            link = "https://www.sporting.com.ar" + href
                        else:
                            link = href

                        break

                texto = await producto.inner_text()

                lineas = [
                    l.strip()
                    for l in texto.split("\n")
                    if l.strip()
                ]

                if len(lineas) < 2:
                    continue

                nombre = lineas[0]

                # buscar TODOS los precios
                precios = []

                for linea in lineas:

                    if "$" in linea:

                        precio = limpiar_precio(linea)

                        if precio:
                            precios.append(precio)

                if not precios:
                    continue

                # el precio más chico suele ser el FINAL
                precio_final = min(precios)

                if precio_final <= PRECIO_MAXIMO:

                    mensaje = (
                        f"🔥 OFERTA\n\n"
                        f"👟 {nombre}\n"
                        f"💲 ${precio_final}\n\n"
                        f"{link if link else URL}"
                    )

                    mensajes.append(mensaje)

            except Exception as e:
                print(e)

        await browser.close()

        if mensajes:

            texto_final = "\n\n──────────────\n\n".join(mensajes[:5])

            enviar_telegram(texto_final)




asyncio.run(main())
