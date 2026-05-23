
import asyncio
import re
import requests
from playwright.async_api import async_playwright

TOKEN = "8843148366:AAGcapDQk_NcjVmVkR-pahZeObjSrq_SNcA"
CHAT_ID = "7727821551"

URL = "https://www.sporting.com.ar/sporting/calzado"

PRECIO_LIMITE = 100000


def enviar_mensaje(texto):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": texto
        }
    )


def limpiar_precio(precio_texto):
    numeros = re.sub(r"[^\d]", "", precio_texto)

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

        await page.wait_for_timeout(10000)

        # Scroll para cargar más productos
        for _ in range(4):
            await page.mouse.wheel(0, 3000)
            await page.wait_for_timeout(3000)

        productos = await page.locator("article").all()

        print(f"Productos encontrados: {len(productos)}")

        encontrados = []

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

                precio = None

                for linea in lineas:

                    if "$" in linea:

                        posible = limpiar_precio(linea)

                        if posible:
                            precio = posible
                            break

                if not precio:
                    continue

                if precio <= PRECIO_LIMITE:

                    link = None

                    try:
                        link = await producto.locator("a").first.get_attribute("href")
                    except:
                        pass

                    if link and link.startswith("/"):
                        link = "https://www.sporting.com.ar" + link

                    mensaje = (
                        f"🔥 OFERTA\n\n"
                        f"👟 {nombre}\n"
                        f"💲 ${precio}\n\n"
                        f"{link if link else URL}"
                    )

                    encontrados.append(mensaje)

            except Exception as e:
                print(e)

        await browser.close()

        if encontrados:

            texto_final = "\n\n-------------------\n\n".join(encontrados[:5])

            enviar_mensaje(texto_final)

        else:

            enviar_mensaje("❌ No encontré ofertas.")


asyncio.run(main())
