import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright


TOKEN = os.getenv("TELEGRAM_TOKEN") or "8843148366:AAGcapDQk_NcjVmVkR-pahZeObjSrq_SNcA"
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or "7727821551"

PRECIO_MAXIMO = int(os.getenv("PRECIO_MAXIMO_ML", "82000"))
HISTORIAL_PATH = Path("sent_offers_ml.json")

BUSQUEDAS = [
    "https://listado.mercadolibre.com.ar/zapatillas-adidas-hombre",
    "https://listado.mercadolibre.com.ar/zapatillas-adidas-mujer",
    "https://listado.mercadolibre.com.ar/zapatillas-nike-hombre",
    "https://listado.mercadolibre.com.ar/zapatillas-nike-mujer",
    "https://listado.mercadolibre.com.ar/zapatillas-puma-hombre",
    "https://listado.mercadolibre.com.ar/zapatillas-puma-mujer",
]

PRODUCTOS_DIRECTOS = [
    {
        "url": "https://articulo.mercadolibre.com.ar/MLA-1469429645-zapatillas-adidas-formula1-mercedes-amg-unisex-jr1062-_JM",
        "nombre": "Zapatillas adidas Formula1 Mercedes - AMG Unisex JR1062",
        "precio": 59999,
    },
]

EXCLUIR = (
    "niño",
    "niños",
    "niña",
    "niñas",
    "bebé",
    "bebés",
    "bebe",
    "bebes",
    "ojota",
    "ojotas",
    "chinela",
    "chinelas",
    "sandalia",
    "sandalias",
    "usado",
)


def cargar_historial():
    if not HISTORIAL_PATH.exists():
        return {}

    data = json.loads(HISTORIAL_PATH.read_text(encoding="utf-8"))
    sent = data.get("sent", {})
    return sent if isinstance(sent, dict) else {}


def guardar_historial(historial):
    HISTORIAL_PATH.write_text(
        json.dumps({"sent": dict(sorted(historial.items()))}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def enviar_telegram(mensaje):
    if not TOKEN or not CHAT_ID:
        raise RuntimeError("Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID.")

    response = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": mensaje},
        timeout=20,
    )

    if not response.ok:
        print("Telegram respondio con error:", response.status_code, response.text)

    response.raise_for_status()

    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram no acepto el mensaje: {data}")


def limpiar_precio(texto):
    numeros = re.sub(r"[^\d]", "", texto or "")
    return int(numeros) if numeros.isdigit() else None


def producto_permitido(nombre):
    nombre_lower = nombre.lower()
    return not any(x in nombre_lower for x in EXCLUIR)


def normalizar_link(link):
    return (link or "").split("#", 1)[0].split("?", 1)[0]


def clave_oferta(link, precio):
    return f"{normalizar_link(link)}|{precio}"


def extraer_precio_producto(page):
    selectores = [
        'meta[itemprop="price"]',
        'meta[property="product:price:amount"]',
    ]

    for selector in selectores:
        locator = page.locator(selector).first
        if locator.count():
            precio = limpiar_precio(locator.get_attribute("content"))
            if precio:
                return precio

    textos = page.locator(".andes-money-amount__fraction").all_inner_texts()
    precios = [limpiar_precio(texto) for texto in textos]
    precios = [precio for precio in precios if precio]
    return min(precios) if precios else None


def revisar_producto_directo(page, producto_directo):
    url = producto_directo["url"]
    print("Revisando producto directo:", url)

    nombre = producto_directo["nombre"]
    precio = producto_directo["precio"]
    link = normalizar_link(url)
    envio_gratis = False

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(5000)

        if page.locator("h1").count():
            nombre = page.locator("h1").first.inner_text().strip()

        precio_extraido = extraer_precio_producto(page)
        if precio_extraido:
            precio = precio_extraido

        link = normalizar_link(page.url)
        envio_gratis = "Envío gratis" in page.locator("body").inner_text()
    except Exception as e:
        print("No se pudo leer el producto directo desde la pagina, se usa el precio configurado:", e)

    print("Producto directo:", nombre)
    print("PRECIO:", precio)

    return {
        "nombre": nombre,
        "precio": precio,
        "link": link,
        "envio": envio_gratis,
    }


def revisar_busqueda(page, url):
    print("Revisando busqueda:", url)

    page.goto(url, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(8000)

    print("TITULO:", page.title())

    cards = page.locator(".poly-card, li.ui-search-layout__item").all()
    print("Productos:", len(cards))

    ofertas = []

    for card in cards:
        try:
            titulo = card.locator(".poly-component__title, h2 a, a.poly-component__title").first
            if not titulo.count():
                continue

            nombre = titulo.inner_text().strip()
            href = titulo.get_attribute("href")
            precios = card.locator(".andes-money-amount__fraction").all_inner_texts()

            if not nombre or not href or not precios:
                continue

            precio = limpiar_precio(precios[0])

            print(nombre)
            print("PRECIO:", precio)

            if precio is None:
                continue

            ofertas.append(
                {
                    "nombre": nombre,
                    "precio": precio,
                    "link": normalizar_link(href),
                    "envio": "Envío gratis" in card.inner_text(),
                }
            )
        except Exception as e:
            print("ERROR tarjeta:", e)

    return ofertas


def formatear_oferta(oferta):
    return (
        "MERCADO LIBRE\n\n"
        f"Producto: {oferta['nombre']}\n"
        f"Precio: ${oferta['precio']}\n"
        f"Envio gratis: {'Si' if oferta['envio'] else 'No'}\n\n"
        f"{oferta['link']}"
    )


def main():
    historial = cargar_historial()
    nuevas_ofertas = []
    vistos = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/137.0.0.0 Safari/537.36"
            )
        )

        ofertas = []

        for producto_directo in PRODUCTOS_DIRECTOS:
            try:
                oferta = revisar_producto_directo(page, producto_directo)
                if oferta:
                    ofertas.append(oferta)
            except Exception as e:
                print("ERROR producto directo:", e)

        for url in BUSQUEDAS:
            ofertas.extend(revisar_busqueda(page, url))

        browser.close()

    for oferta in ofertas:
        nombre = oferta["nombre"]
        precio = oferta["precio"]

        if not producto_permitido(nombre):
            print(f"Producto ignorado por filtro: {nombre}")
            continue

        if precio > PRECIO_MAXIMO:
            continue

        key = clave_oferta(oferta["link"], precio)

        if key in vistos:
            continue

        vistos.add(key)

        if key in historial:
            print(f"Oferta ya enviada: {nombre} ${precio}")
            continue

        print("ACEPTADA:", nombre, precio)

        oferta["key"] = key
        nuevas_ofertas.append(oferta)

    if not nuevas_ofertas:
        print("No se encontraron ofertas nuevas.")
        return

    ofertas_a_enviar = nuevas_ofertas[:10]
    mensaje = "\n\n-----------------\n\n".join(formatear_oferta(oferta) for oferta in ofertas_a_enviar)

    enviar_telegram(mensaje)

    sent_at = datetime.now(timezone.utc).isoformat()

    for oferta in ofertas_a_enviar:
        historial[oferta["key"]] = {
            "name": oferta["nombre"],
            "price": oferta["precio"],
            "link": oferta["link"],
            "sent_at": sent_at,
        }

    guardar_historial(historial)

    print(f"Mensaje enviado con {len(ofertas_a_enviar)} ofertas nuevas.")


if __name__ == "__main__":
    main()
