import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TG_TOKEN")
PUBLIC_ID = os.getenv("TG_PUBLIC_ID")

print(f"Токен: {TOKEN[:5]}...")
print(f"Публичный канал: {PUBLIC_ID}")

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
data = {
    'chat_id': PUBLIC_ID, 
    'text': "🚀 Тест прав администратора"
}

print("Отправка...")
resp = requests.post(url, json=data)
print(f"Ответ сервера: {resp.text}")
