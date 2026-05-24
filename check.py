import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TOKEN = os.getenv("TELEGRAM_TOKEN") or "8843148366:AAGcapDQk_NcjVmVkR-pahZeObjSrq_SNcA"
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or "7727821551"

BASE_API_URL = os.getenv(
    "SPORTING_API_URL",
    "https://www.sporting.com.ar/api/catalog_system/pub/products/search/sporting/calzado",
)

PRECIO_MAXIMO = int(os.getenv("PRECIO_MAXIMO", "41000"))
PAGINAS_A_REVISAR = int(os.getenv("PAGINAS_A_REVISAR", "5"))
PRODUCTOS_POR_PAGINA = int(os.getenv("PRODUCTOS_POR_PAGINA", "24"))
HISTORIAL_ALERTAS_PATH = Path(os.getenv("HISTORIAL_ALERTAS_PATH", "sent_offers.json"))
PALABRAS_EXCLUIDAS = (
    "ojota",
    "ojotas",
    "chinela",
    "chinelas",
    "sandalia",
    "sandalias",
    "niño",
    "niños",
    "niña",
    "niñas",
    "bebe",
    "bebes",
    "bebé",
    "bebés",
)


def cargar_historial(path: Path = HISTORIAL_ALERTAS_PATH) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}

    data = json.loads(path.read_text(encoding="utf-8"))
    sent = data.get("sent", {})

    if isinstance(sent, list):
        return {key: {"key": key} for key in sent}

    if not isinstance(sent, dict):
        return {}

    return sent


def guardar_historial(historial: dict[str, dict[str, Any]], path: Path = HISTORIAL_ALERTAS_PATH) -> None:
    data = {"sent": dict(sorted(historial.items()))}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clave_oferta(precio: int, link: str) -> str:
    return f"{link}|{precio}"


def enviar_telegram(mensaje: str) -> None:
    import requests

    if not TOKEN or not CHAT_ID:
        raise RuntimeError("Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID en las variables de entorno.")

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

    if not response.ok:
        print("Sporting respondio con error:", response.status_code, response.text[:500])

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


def formatear_oferta(nombre: str, precio: int, link: str) -> str:
    return "\n".join(
        [
            "OFERTA SPORTING",
            "",
            f"Producto: {nombre}",
            f"Precio: ${precio}",
            "",
            link,
        ]
    )


def producto_permitido(nombre: str) -> bool:
    nombre_normalizado = nombre.lower()

    return not any(palabra in nombre_normalizado for palabra in PALABRAS_EXCLUIDAS)


def main() -> None:
    historial = cargar_historial()
    nuevas_ofertas = []
    vistos = set()

    for numero_pagina in range(1, PAGINAS_A_REVISAR + 1):
        print(f"Revisando pagina {numero_pagina}")
        productos = obtener_productos(numero_pagina)
        print(f"Productos encontrados: {len(productos)}")

        if not productos:
            break

        for producto in productos:
            nombre = producto.get("productName", "").strip()
            link = producto.get("link", "https://www.sporting.com.ar/sporting/calzado")
            precio = extraer_precio_producto(producto)

            if not nombre or precio is None:
                continue

            if not producto_permitido(nombre):
                print(f"Producto ignorado por filtro: {nombre}")
                continue

            print(nombre, precio)

            if precio <= PRECIO_MAXIMO:
                key = clave_oferta(precio, link)
                if key in vistos:
                    continue

                vistos.add(key)

                if key in historial:
                    print(f"Oferta ya enviada: {nombre} ${precio}")
                    continue

                nuevas_ofertas.append(
                    {
                        "key": key,
                        "nombre": nombre,
                        "precio": precio,
                        "link": link,
                    }
                )

    if not nuevas_ofertas:
        print(f"No hay ofertas nuevas por debajo de ${PRECIO_MAXIMO}.")
        return

    ofertas_a_enviar = nuevas_ofertas[:10]
    mensaje_final = "\n\n--------------\n\n".join(
        formatear_oferta(oferta["nombre"], oferta["precio"], oferta["link"]) for oferta in ofertas_a_enviar
    )
    enviar_telegram(mensaje_final)

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
