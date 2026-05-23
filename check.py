import requests
from bs4 import BeautifulSoup

URL = "https://www.sporting.com.ar/sporting/calzado"
headers = {"User-Agent": "Mozilla/5.0"}

r = requests.get(URL, headers=headers, timeout=20)
print("STATUS:", r.status_code)
print("URL final:", r.url)
print("Tamaño HTML:", len(r.text))

soup = BeautifulSoup(r.text, "html.parser")
productos = soup.find_all("div", class_="vtex-product-summary-2-x-container")
print("Productos encontrados:", len(productos))
