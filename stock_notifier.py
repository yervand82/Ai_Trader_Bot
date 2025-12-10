# --- stock_notifier.py (Сигналы Акций) ---
from flask import Flask, request
import requests
import os

app = Flask(__name__)

# --- ВАШИ ДАННЫЕ (Вставьте сюда то же самое, что было в .env) ---
TELEGRAM_TOKEN = "8364912791:AAEsDnAL-IyN6RWcfNedEXY5-99I_68JbGs"
YOUR_CHAT_ID = "2010843048"
# ------------------------------------------------------------------

def send_tg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": YOUR_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Ошибка отправки в TG: {e}")

@app.route('/stock_alert', methods=['POST'])
def webhook():
    try:
        # TradingView присылает простой текст
        data = request.get_data(as_text=True)
        
        print(f"🔔 Сигнал: {data}")
        
        # Формируем красивое сообщение
        msg = f"📢 **СИГНАЛ С БИРЖИ**\n\n{data}"
        send_tg(msg)
        
        return "OK", 200
    except Exception as e:
        print(f"Ошибка: {e}")
        return "Error", 500

if __name__ == '__main__':
    print("🚀 Stock Notifier слушает порт 8000...")
    # Запускаем на порту 8000, чтобы не путать с крипто-ботом (5000)
    app.run(host='0.0.0.0', port=8000)
