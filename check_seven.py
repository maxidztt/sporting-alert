import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOKEN = os.getenv("TELEGRAM_TOKEN") or "8843148366:AAGcapDQk_NcjVmVkR-pahZeObjSrq_SNcA"
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or "7727821551"

PRECIO_MAXIMO = 45000

try:
    with open("config_alertas.json", "r", encoding="utf-8") as f:
        CONFIG = json.load(f)

    ENVIAR_ALERTAS = CONFIG.get("seven", True)

except Exception:
    ENVIAR_ALERTAS = True

BASE_API_URL = (
    "https://www.sevensport.com.ar/"
    "api/catalog_system/pub/products/search/"
    "calzado/zapatillas"
)

PAGINAS_A_REVISAR = 5
PRODUCTOS_POR_PAGINA = 24

HISTORIAL_PATH = Path("sent_offers_seven.json")

PALABRAS_EXCLUIDAS = (
    "ojota", "ojotas",
    "chinela", "chinelas",
    "sandalia", "sandalias",
    "niño", "niños",
    "niña", "niñas",
    "bebe", "bebes",
    "bebé", "bebés",
    "infantil",
    "juvenil", "Juvenil",
)

def cargar_historial(path: Path = HISTORIAL_PATH) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    sent = data.get("sent", {})

    if isinstance(sent, list):
        return {key: {"key": key} for key in sent}

    if not isinstance(sent, dict):
        return {}

    return sent

def guardar_historial(historial: dict[str, dict[str, Any]], path: Path = HISTORIAL_PATH) -> None:
    data = {"sent": dict(sorted(historial.items()))}
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

def clave_oferta(nombre: str, precio: int) -> str:
    return f"{nombre.strip().lower()}|{precio}"

def enviar_telegram(mensaje: str) -> None:
    import requests

    if not ENVIAR_ALERTAS:
        print("Alertas desactivadas.")
        return

    response = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": mensaje},
        timeout=20,
    )

    response.raise_for_status()

def obtener_productos(numero_pagina: int) -> list[dict[str, Any]]:
    import requests

    desde = (numero_pagina - 1) * PRODUCTOS_POR_PAGINA
    hasta = desde + PRODUCTOS_POR_PAGINA - 1

    response = requests.get(
        BASE_API_URL,
        params={
            "map": "c,c",
            "O": "OrderByPriceASC",
            "_from": desde,
            "_to": hasta,
        },
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )

    if response.status_code == 403:
        print("Seven devolvió 403.")
        return []

    response.raise_for_status()
    return response.json()

def extraer_precio_producto(producto: dict[str, Any]) -> int | None:
    precios = []

    for item in producto.get("items", []):
        for seller in item.get("sellers", []):
            oferta = seller.get("commertialOffer", {})
            precio = oferta.get("Price")
            stock = oferta.get("AvailableQuantity", 0)

            if precio and stock:
                precios.append(float(precio))

    if not precios:
        return None

    return int(min(precios))

def producto_permitido(nombre: str) -> bool:
    nombre = nombre.lower()
    return not any(p in nombre for p in PALABRAS_EXCLUIDAS)

def formatear_oferta(nombre: str, precio: int, link: str) -> str:
    return "\n".join([
        "🔥 OFERTA 🟦SEVEN SPORT🟦",
        "",
        f"Producto: {nombre}",
        f"Precio: ${precio:,}".replace(",", "."),
        "",
        link,
    ])

def main() -> None:
    historial = cargar_historial()
    nuevas_ofertas = []
    vistos = set()

    for pagina in range(1, PAGINAS_A_REVISAR + 1):
        print(f"Revisando página {pagina}")

        productos = obtener_productos(pagina)

        if not productos:
            break

        for producto in productos:
            nombre = producto.get("productName", "").strip()
            link = producto.get("link", "")
            precio = extraer_precio_producto(producto)

            if not nombre or precio is None:
                continue

            if not producto_permitido(nombre):
                continue

            if precio > PRECIO_MAXIMO:
                continue

            key = clave_oferta(nombre, precio)

            if key in vistos:
                continue

            vistos.add(key)

            if key in historial:
                continue

            nuevas_ofertas.append({
                "key": key,
                "nombre": nombre,
                "precio": precio,
                "link": link,
            })

    if not nuevas_ofertas:
        print("No hay ofertas nuevas.")
        return

    ofertas_a_enviar = nuevas_ofertas[:10]

    mensaje = "\n\n--------------\n\n".join(
        formatear_oferta(x["nombre"], x["precio"], x["link"])
        for x in ofertas_a_enviar
    )

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

    print(f"Enviadas {len(ofertas_a_enviar)} ofertas.")

if __name__ == "__main__":
    main()
