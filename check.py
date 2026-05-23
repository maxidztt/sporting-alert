import requests
from bs4 import BeautifulSoup

# =========================
# CONFIG
# =========================

TOKEN = "8843148366:AAGcapDQk_NcjVmVkR-pahZeObjSrq_SNcA"
CHAT_ID = "7727821551"

URL = "https://www.sporting.com.ar/sporting/calzado"

# precio máximo para alertar
PRECIO_MAXIMO = 90000

# =========================
# TELEGRAM
# =========================

def enviar_telegram(mensaje):

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": mensaje
    }

    requests.post(url, data=data)

# =========================
# SCRAPING
# =========================

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

response = requests.get(URL, headers=headers)

soup = BeautifulSoup(response.text, "html.parser")

# tarjetas de productos
productos = soup.select("a.vtex-product-summary-2-x-clearLink")

mensajes = []

for producto in productos[:20]:

    try:

        # =========================
        # NOMBRE
        # =========================

        nombre_tag = producto.select_one(
            ".vtex-product-summary-2-x-productBrand"
        )

        # =========================
        # PRECIO FINAL
        # =========================

        precio_tag = producto.select_one(
            ".selling-price-value"
        )

        # =========================
        # LINK
        # =========================

        href = producto.get("href")

        if not nombre_tag or not precio_tag or not href:
            continue

        nombre = nombre_tag.text.strip()

        precio = (
            precio_tag.text
            .replace("$", "")
            .replace(".", "")
            .replace(",", "")
            .strip()
        )

        precio_num = int(precio)

        # =========================
        # FILTRAR OFERTAS
        # =========================

        if precio_num <= PRECIO_MAXIMO:

            if href.startswith("/"):
                link = "https://www.sporting.com.ar" + href
            else:
                link = href

            mensaje = (
                f"🔥 OFERTA\n\n"
                f"👟 {nombre}\n"
                f"💲 ${precio_num}\n\n"
                f"{link}"
            )

            mensajes.append(mensaje)

    except Exception as e:
        print("ERROR:", e)

# =========================
# ENVIAR MENSAJES
# =========================

if mensajes:

    texto = "\n\n────────────\n\n".join(mensajes[:5])

    enviar_telegram(texto)

else:

    enviar_telegram("❌ No se encontraron ofertas.")
