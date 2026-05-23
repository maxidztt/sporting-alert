import os
from typing import Any


TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

BASE_API_URL = os.getenv(
    "SPORTING_API_URL",
    "https://www.sporting.com.ar/api/catalog_system/pub/products/search/sporting/calzado",
)

PRECIO_MAXIMO = int(os.getenv("PRECIO_MAXIMO", "39000"))
PAGINAS_A_REVISAR = int(os.getenv("PAGINAS_A_REVISAR", "5"))
PRODUCTOS_POR_PAGINA = int(os.getenv("PRODUCTOS_POR_PAGINA", "24"))


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


def main() -> None:
    encontrados = []
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

            print(nombre, precio)

            if precio <= PRECIO_MAXIMO:
                key = f"{nombre}|{precio}|{link}"
                if key in vistos:
                    continue

                vistos.add(key)
                encontrados.append(formatear_oferta(nombre, precio, link))

    if not encontrados:
        print(f"No hay productos por debajo de ${PRECIO_MAXIMO}.")
        return

    mensaje_final = "\n\n--------------\n\n".join(encontrados[:10])
    enviar_telegram(mensaje_final)
    print(f"Mensaje enviado con {min(len(encontrados), 10)} ofertas.")


if __name__ == "__main__":
    main()
