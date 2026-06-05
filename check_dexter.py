import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

TOKEN = os.getenv("TELEGRAM_TOKEN") or "8843148366:AAGcapDQk_NcjVmVkR-pahZeObjSrq_SNcA"
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or "7727821551"

PRECIO_MAXIMO = 45000

HISTORIAL_PATH = Path("sent_offers_dexter.json")

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
    "infantil",
)

PAGINAS = 5
PRODUCTOS_POR_PAGINA = 36


def cargar_historial():
    if not HISTORIAL_PATH.exists():
        return {}

    data = json.loads(
        HISTORIAL_PATH.read_text(encoding="utf-8")
    )

    return data.get("sent", {})


def guardar_historial(historial):
    HISTORIAL_PATH.write_text(
        json.dumps(
            {"sent": historial},
            ensure_ascii=False,
            indent=2,
        ),
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


def producto_permitido(nombre):
    nombre = nombre.lower()

    return not any(
        palabra in nombre
        for palabra in PALABRAS_EXCLUIDAS
    )


def obtener_html(start):
    url = (
        "https://www.dexter.com.ar/"
        "on/demandware.store/"
        "Sites-Dexter-Site/default/"
        "Search-UpdateGrid"
    )

    r = requests.get(
        url,
        params={
            "cgid": "zapatillas",
            "srule": "lowest-price",
            "start": start,
            "sz": PRODUCTOS_POR_PAGINA,
        },
        headers={
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        },
        timeout=30,
    )

    print(
        f"Página start={start} ->",
        r.status_code
    )

    r.raise_for_status()

    return r.text


historial = cargar_historial()

nuevas_ofertas = []

vistos = set()

for pagina in range(PAGINAS):

    start = pagina * PRODUCTOS_POR_PAGINA

    html = obtener_html(start)

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    productos = soup.select(".product")

    print(
        f"Productos encontrados: {len(productos)}"
    )

    for producto in productos:

        try:

            nombre_tag = producto.select_one(
                ".pdp-link a"
            )

            precio_tag = producto.select_one(
                ".sales .value"
            )

            if not nombre_tag or not precio_tag:
                continue

            nombre = (
                nombre_tag.get_text(strip=True)
            )

            if not producto_permitido(nombre):
                continue

            precio = int(
                float(
                    precio_tag.get(
                        "content"
                    )
                )
            )

            if precio > PRECIO_MAXIMO:
                continue

            href = nombre_tag.get(
                "href"
            )

            if href.startswith("/"):
                link = (
                    "https://www.dexter.com.ar"
                    + href
                )
            else:
                link = href

            key = f"{link}|{precio}"

            if key in vistos:
                continue

            vistos.add(key)

            if key in historial:
                continue

            nuevas_ofertas.append(
                {
                    "key": key,
                    "nombre": nombre,
                    "precio": precio,
                    "link": link,
                }
            )

            print(
                "Oferta:",
                nombre,
                precio
            )

        except Exception as e:
            print("ERROR:", e)

if nuevas_ofertas:

    sent_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    mensajes = []

    for oferta in nuevas_ofertas[:10]:

        mensajes.append(
            f"🔥 DEXTER\n\n"
            f"👟 {oferta['nombre']}\n"
            f"💲 ${oferta['precio']}\n\n"
            f"{oferta['link']}"
        )

        historial[
            oferta["key"]
        ] = {
            "name": oferta["nombre"],
            "price": oferta["precio"],
            "link": oferta["link"],
            "sent_at": sent_at,
        }

    guardar_historial(
        historial
    )

    enviar_telegram(
        "\n\n-----------------\n\n".join(
            mensajes
        )
    )

    print(
        f"Enviadas {len(mensajes)} ofertas"
    )

else:

    print(
        "No se encontraron ofertas nuevas."
    )
