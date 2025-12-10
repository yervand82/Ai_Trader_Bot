import os
import requests
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

print("--- ДИАГНОСТИКА УВЕДОМЛЕНИЙ ---")

# 1. Проверка Telegram
tg_token = os.getenv("TG_TOKEN")
tg_chat = os.getenv("TG_PRIVATE_ID") # Проверяем приватный канал

print(f"\n1. TELEGRAM:")
if not tg_token:
    print("❌ ОШИБКА: TG_TOKEN не найден в .env")
else:
    print(f"✅ Токен загружен: {tg_token[:5]}...*****")

if not tg_chat:
    print("❌ ОШИБКА: TG_PRIVATE_ID не найден в .env")
else:
    print(f"✅ Chat ID загружен: {tg_chat}")

if tg_token and tg_chat:
    print("Попытка отправки в Telegram...")
    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    try:
        resp = requests.post(url, json={'chat_id': tg_chat, 'text': "🛠 TEST MESSAGE"})
        print(f"Ответ сервера Telegram: {resp.status_code}")
        print(f"Тело ответа: {resp.text}")
    except Exception as e:
        print(f"Ошибка соединения: {e}")

# 2. Проверка Discord
discord_url = os.getenv("DISCORD_WEBHOOK_URL")
print(f"\n2. DISCORD:")
if not discord_url:
    print("❌ ОШИБКА: DISCORD_WEBHOOK_URL не найден в .env")
else:
    print(f"✅ Webhook загружен: {discord_url[:10]}...")
    print("Попытка отправки в Discord...")
    try:
        resp = requests.post(discord_url, json={'content': "🛠 TEST MESSAGE"})
        print(f"Ответ сервера Discord: {resp.status_code}")
        print(f"Тело ответа: {resp.text}")
    except Exception as e:
        print(f"Ошибка соединения: {e}")
