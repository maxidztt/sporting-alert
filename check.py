import requests

TOKEN = "8843148366:AAGcapDQk_NcjVmVkR-pahZeObjSrq_SNcA"
CHAT_ID = "7727821551"

mensaje = "🔥 TEST OK - el bot funciona"

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

r = requests.get(url, params={
    "chat_id": CHAT_ID,
    "text": mensaje
})

print(r.text)
