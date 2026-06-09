import json
import os
from pathlib import Path
from datetime import datetime, timezone

import requests

TOKEN = os.getenv("TELEGRAM_TOKEN") or "<TOKEN_LOCAL>"
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or "<CHAT_ID_LOCAL>"

VENDOR_ID = "183015"

HISTORIAL_ALERTAS_PATH = Path(
    os.getenv("HISTORIAL_ALERTAS_PATH", "sent_offers_pedidosya.json")
)

PALABRAS_CLAVE = [
    "figurita",
    "figuritas",
    "panini",
    "fifa",
    "world cup",
    "2026",
    "sticker",
    "stickers",
]

try:
    with open("config_alertas.json", "r", encoding="utf-8") as f:
        CONFIG = json.load(f)

    ENVIAR_ALERTAS = CONFIG.get("pedidosya", True)

except Exception:
    ENVIAR_ALERTAS = True


def cargar_historial():
    if not HISTORIAL_ALERTAS_PATH.exists():
        return {}

    try:
        with open(HISTORIAL_ALERTAS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data.get("sent", {})

    except Exception:
        return {}


def guardar_historial(historial):
    with open(HISTORIAL_ALERTAS_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {"sent": historial},
            f,
            ensure_ascii=False,
            indent=2
        )


def enviar_telegram(mensaje):
    if not ENVIAR_ALERTAS:
        print("Alertas PedidosYa desactivadas.")
        return

    response = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": mensaje
        },
        timeout=20
    )

    response.raise_for_status()


def obtener_categorias():
    url = f"https://www.pedidosya.com.ar/groceries/web/v1/vendors/{VENDOR_ID}/categories"

    response = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def obtener_productos_categoria(category_id, page=1):
    url = (
        f"https://www.pedidosya.com.ar/groceries/web/v1/vendors/"
        f"{VENDOR_ID}/products"
    )

    response = requests.get(
        url,
        params={
            "categoryId": category_id,
            "limit": 100,
            "page": page
        },
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def contiene_palabra_clave(nombre):
    nombre = nombre.lower()

    return any(
        palabra in nombre
        for palabra in PALABRAS_CLAVE
    )


def formatear_mensaje(producto):
    nombre = producto.get("name", "Sin nombre")

    precio = (
        producto.get("pricing", {})
        .get("price", 0)
    )

    stock = producto.get("stock", 0)

    return (
        "🔥 PEDIDOSYA MARKET\n\n"
        f"Producto: {nombre}\n"
        f"Precio: ${precio}\n"
        f"Stock: {stock}"
    )


def main():
    historial = cargar_historial()

    categorias = obtener_categorias()

    nuevas = []

    for categoria in categorias:

        category_id = categoria.get("id")

        if not category_id:
            continue

        try:
            productos = obtener_productos_categoria(category_id)

        except Exception as e:
            print("Error categoría:", e)
            continue

        items = productos.get("items", [])

        for producto in items:

            nombre = producto.get("name", "")

            if not contiene_palabra_clave(nombre):
                continue

            stock = producto.get("stock", 0)

            if stock <= 0:
                continue

            product_id = producto.get("id")

            key = str(product_id)

            if key in historial:
                continue

            nuevas.append(producto)

    if not nuevas:
        print("No se encontraron figuritas.")
        return

    for producto in nuevas:

        enviar_telegram(
            formatear_mensaje(producto)
        )

        historial[str(producto["id"])] = {
            "name": producto["name"],
            "sent_at": datetime.now(
                timezone.utc
            ).isoformat()
        }

    guardar_historial(historial)

    print(
        f"Enviadas {len(nuevas)} alertas."
    )


if __name__ == "__main__":
    main()
