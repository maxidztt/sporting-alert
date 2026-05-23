
import requests
import sys

TOKEN = "8843148366:AAGcapDQk_NcjVmVkR-pahZeObjSrq_SNcA"
CHAT_ID = "7727821551"

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

response = requests.post(
    url,
    json={
        "chat_id": CHAT_ID,
        "text": "🔥 FUNCIONA EL BOT"
    },
    timeout=20
)

print("STATUS:", response.status_code, flush=True)
print("RESPUESTA:", response.text, flush=True)

sys.stdout.flush()
