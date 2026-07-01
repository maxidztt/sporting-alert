import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone

import requests

TOKEN = os.getenv("TELEGRAM_TOKEN") or "8843148366:AAGcapDQk_NcjVmVkR-pahZeObjSrq_SNcA" 
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or "7727821551"

BASE_URL = "https://www.vaypol.com.ar"

PAGINAS_A_REVISAR = 5

HISTORIAL_PATH = Path("sent_offers_vaypol.json")

PALABRAS_EXCLUIDAS = (
    "ojota", "ojotas",
    "chinela", "chinelas",
    "sandalia", "sandalias",
    "niño", "niños",
    "niña", "niñas",
    "bebe", "bebes",
    "bebé", "bebés",
    "infantil",
    "juvenil",
    "silbato",
    "venda",
    "medias",
    "gorro",
    "bocha",
    "soga",
    "tarjeta"
)


def cargar_config():
    with open(
        "config_alertas.json",
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def cargar_historial():
    if not HISTORIAL_PATH.exists():
        return {}

    with open(
        HISTORIAL_PATH,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def guardar_historial(historial):
    with open(
        HISTORIAL_PATH,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            historial,
            f,
            ensure_ascii=False,
            indent=2
        )


def enviar_telegram(texto):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": texto
        },
        timeout=20
    )


def obtener_build():
    r = requests.get(
        BASE_URL + "/productos/o/ofertas/p/1",
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=30
    )

    r.raise_for_status()

    html = r.text

    m = re.search(
        r'/_next/data/([^/]+)/',
        html
    )

    if not m:
        raise Exception("No pude obtener el Build ID")

    return m.group(1)


def obtener_productos(build, pagina):
    url = (
        f"{BASE_URL}"
        f"/_next/data/{build}"
        f"/productos/o/menor_precio/p/{pagina}.json"
    )

    r = requests.get(
        url,
        params={
            "slugs": [
                "o",
                "menor_precio",
                "p",
                str(pagina)
            ]
        },
        headers={
            "User-Agent": "Mozilla/5.0",
            "x-nextjs-data": "1"
        },
        timeout=30
    )

    r.raise_for_status()

    data = r.json()

    return data["pageProps"]["initialReduxState"]["products"]["items"]


def producto_permitido(nombre):
    nombre = nombre.lower()

    return not any(
        palabra in nombre
        for palabra in PALABRAS_EXCLUIDAS
    )


def limpiar_precio(texto):
    if texto is None:
        return None

    texto = (
        texto
        .replace(".", "")
        .replace(",", ".")
    )

    return int(float(texto))


def clave(nombre, precio):
    return (
        nombre.lower().strip()
        + "|"
        + str(precio)
    )


def revisar_ofertas():
    config = cargar_config()

    if not config.get("vaypol", True):
        print("Alertas de Vaypol desactivadas.")
        return []

    precio_maximo = config.get(
        "precio_vaypol",
        40000
    )

    historial = cargar_historial()

    build = obtener_build()

    print(f"Build ID: {build}")

    nuevas = []
    vistos = set()

    for pagina in range(
        1,
        PAGINAS_A_REVISAR + 1
    ):
        print(f"Página {pagina}")

        try:
            productos = obtener_productos(
                build,
                pagina
            )

        except Exception as e:
            print(e)
            continue

        if not productos:
            break

        for producto in productos:
            try:
                nombre = producto["name"].strip()

                if not producto_permitido(nombre):
                    continue

                precios = producto.get(
                    "all_prices",
                    {}
                )

                precio = (
                    precios.get("discount")
                    or precios.get("sale_price")
                    or precios.get("original")
                )

                if not precio:
                    continue

                precio = limpiar_precio(precio)

                if precio > precio_maximo:
                    continue

                link = (
                    BASE_URL
                    + producto["url"]
                )

                k = clave(
                    nombre,
                    precio
                )

                if k in vistos:
                    continue

                vistos.add(k)

                if k in historial:
                    continue

                historial[k] = {
                    "nombre": nombre,
                    "precio": precio,
                    "link": link,
                    "fecha": datetime.now(
                        timezone.utc
                    ).isoformat()
                }

                nuevas.append({
                    "nombre": nombre,
                    "precio": precio,
                    "link": link
                })

            except Exception:
                continue

    guardar_historial(historial)

    return nuevas


def main():
    try:
        ofertas = revisar_ofertas()

    except Exception as e:
        print(e)
        return

    if not ofertas:
        print("No hay ofertas nuevas.")
        return

    mensajes = []

    for oferta in ofertas[:10]:
        mensajes.append(
            "\n".join([
                "🔥 OFERTA ⬜VAYPOL⬜",
                "",
                f"Producto: {oferta['nombre']}",
                f"Precio: ${oferta['precio']:,}".replace(",", "."),
                "",
                oferta["link"]
            ])
        )

    mensaje = "\n\n--------------\n\n".join(
        mensajes
    )

    enviar_telegram(mensaje)

    print(
        f"Enviadas {len(ofertas[:10])} ofertas."
    )


if __name__ == "__main__":
    main()
