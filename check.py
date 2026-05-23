import requests
from bs4 import BeautifulSoup

TOKEN = "8843148366:AAHVJxCJ_IrtcGsct14yBlZDIUALj2AjUZ8"
CHAT_ID = "7727821551"

URL = "https://www.sporting.com.ar/sporting/calzado"

PRECIO_LIMITE = 10000

headers = {
    "User-Agent": "Mozilla/5.0"
}

r = requests.get(URL, headers=headers)
soup = BeautifulSoup(r.text, "html.parser")

productos = soup.find_all("div", class_="vtex-product-summary-2-x-container")

for p in productos:
    texto = p.get_text(" ", strip=True)

    precios = [int(s.replace(".", "")) for s in texto.split() if s.replace(".", "").isdigit()]

    if precios:
        precio = min(precios)

        if precio <= PRECIO_LIMITE:

            mensaje = f"🔥 Oferta encontrada\n\n{texto}\n\nPrecio: ${precio}"

            requests.get(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                params={
                    "chat_id": CHAT_ID,
                    "text": mensaje
                }
            )
