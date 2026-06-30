import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

TOKEN = os.getenv("TELEGRAM_TOKEN") or "TU_TOKEN"
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or "TU_CHAT_ID"

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
    "tarjeta",
)

def obtener_build_id():

    response = requests.get(
        f"{BASE_URL}/productos/o/menor_precio/p/1",
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=30
    )

    response.raise_for_status()

    html = response.text

    match = re.search(
        r'/_next/data/([^/]+)/productos/',
        html
    )

    if not match:
        raise Exception(
            "No se pudo obtener el Build ID de Vaypol."
        )

    return match.group(1)


def obtener_productos(
    build_id,
    pagina
):

    url = (
        f"{BASE_URL}"
        f"/_next/data/{build_id}"
        f"/productos/o/menor_precio/p/{pagina}.json"
    )

    response = requests.get(
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

    response.raise_for_status()

    return response.json()

if __name__ == "__main__":

    build = obtener_build_id()

    print("BUILD:", build)

    data = obtener_productos(
        build,
        1
    )

    print(json.dumps(data, indent=2)[:5000])
