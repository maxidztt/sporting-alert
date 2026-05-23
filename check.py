import requests

TOKEN = "8843148366:AAGcapDQk_NcjVmVkR-pahZeObjSrq_SNcA"
CHAT_ID = "7727821551"

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

response = requests.post(url, data={
    "chat_id": CHAT_ID,
    "text": "🔥 TEST DEFINITIVO"
})

print(response.status_code)
print(response.text)
