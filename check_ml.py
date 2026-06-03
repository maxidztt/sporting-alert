import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

PRECIO_MAXIMO = 60000

HISTORIAL_PATH = Path("sent_offers_ml.json")

BUSQUEDAS = [
    "https://listado.mercadolibre.com.ar/zapatillas-adidas-hombre",
    "https://listado.mercadolibre.com.ar/zapatillas-adidas-mujer",
    "https://listado.mercadolibre.com.ar/zapatillas-nike-hombre",
    "https://listado.mercadolibre.com.ar/zapatillas-nike-mujer",
    "https://listado.mercadolibre.com.ar/zapatillas-puma-hombre",
    "https://listado.mercadolibre.com.ar/zapatillas-puma-mujer",
]

EXCLUIR = [
    "niño",
    "niños",
    "niña",
    "niñas",
    "bebé",
    "bebes",
    "bebé",
    "ojota",
    "ojotas",
    "chinela",
    "chinelas",
    "sandalia",
    "sandalias",
    "usado",
]


def cargar_historial():
    if not HISTORIAL_PATH.exists():
        return {}

    data = json.loads(HISTORIAL_PATH.read_text(encoding="utf-8"))
    return data.get("sent", {})


def guardar_historial(historial):
    HISTORIAL_PATH.write_text(
        json.dumps({"sent": historial}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def enviar_telegram(mensaje):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": mensaje,
        },
        timeout=20,
    )


def limpiar_precio(texto):
    numeros = re.sub(r"[^\d]", "", texto)

    if numeros.isdigit():
        return int(numeros)

    return None


historial = cargar_historial()
nuevas_ofertas = []

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled"
        ]
    )

    page = browser.new_page(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
    )

    for url in BUSQUEDAS:

        print("Revisando:", url)

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=120000
        )

        page.wait_for_timeout(8000)

        print("TITULO:", page.title())

        html = page.content()

        print("HTML:")
        print(html[:1000])

        cards = page.locator(".poly-card").all()

        print("Productos:", len(cards))

        for card in cards:

            try:

                titulo = card.locator(
                    ".poly-component__title"
                ).first

                nombre = titulo.inner_text().strip()

                nombre_lower = nombre.lower()

                if any(x in nombre_lower for x in EXCLUIR):
                    continue

                href = titulo.get_attribute("href")

                precios = card.locator(
                    ".andes-money-amount__fraction"
                ).all()

                if not precios:
                    continue

                precio_texto = precios[0].inner_text()

                precio = limpiar_precio(precio_texto)

                print(nombre)
                print("PRECIO:", precio)

                if precio is None:
                    continue

                if precio > PRECIO_MAXIMO:
                    continue

                print("ACEPTADA:", nombre, precio)

                envio_gratis = (
                    "Envío gratis" in card.inner_text()
                )

                key = f"{href}|{precio}"

                if key in historial:
                    continue

                nuevas_ofertas.append(
                    {
                        "key": key,
                        "nombre": nombre,
                        "precio": precio,
                        "link": href,
                        "envio": envio_gratis,
                    }
                )

            except Exception as e:
                print("ERROR:", e)

    browser.close()

if nuevas_ofertas:

    mensajes = []

    sent_at = datetime.now(timezone.utc).isoformat()

    for oferta in nuevas_ofertas[:10]:

        mensajes.append(
            f"🔥 MERCADO LIBRE\n\n"
            f"👟 {oferta['nombre']}\n"
            f"💲 ${oferta['precio']}\n"
            f"🚚 Envío gratis: {'Sí' if oferta['envio'] else 'No'}\n\n"
            f"{oferta['link']}"
        )

        historial[oferta["key"]] = {
            "name": oferta["nombre"],
            "price": oferta["precio"],
            "link": oferta["link"],
            "sent_at": sent_at,
        }

    guardar_historial(historial)

    enviar_telegram(
        "\n\n-----------------\n\n".join(mensajes)
    )

else:
    print("No se encontraron ofertas nuevas.")
