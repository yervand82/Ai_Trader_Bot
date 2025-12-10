# --- trade_server.py (Исполнитель v2.0 с уведомлениями) ---
from flask import Flask, request
import ccxt
import os
import requests
from dotenv import load_dotenv

# 1. Загрузка настроек
load_dotenv()
API_KEY = os.getenv("API_KEY")      # Ваши названия переменных
SECRET = os.getenv("API_SECRET")

# Настройки уведомлений
TG_TOKEN = os.getenv("TG_TOKEN")
TG_PRIVATE_ID = os.getenv("TG_PRIVATE_ID")
TG_PUBLIC_ID = os.getenv("TG_PUBLIC_ID")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")

# Настройка биржи
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': SECRET,
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'} 
})

app = Flask(__name__)

# --- ФУНКЦИИ УВЕДОМЛЕНИЙ ---
def send_telegram(message, chat_id):
    if not TG_TOKEN or not chat_id: return
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        requests.post(url, json={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'})
    except Exception as e:
        print(f"Ошибка отправки в TG: {e}")

def send_discord(message):
    if not DISCORD_WEBHOOK: return
    try:
        requests.post(DISCORD_WEBHOOK, json={'content': message})
    except Exception as e:
        print(f"Ошибка отправки в Discord: {e}")

def notify_all(symbol, price, amount_usd, is_test=True):
    # Красивое сообщение со смайликами
    mode = "[TEST MODE]" if is_test else "🚀 LIVE TRADE"
    msg = (
        f"<b>{mode} BUY SIGNAL</b>\n\n"
        f"💎 <b>Coin:</b> #{symbol.replace('/', '')}\n"
        f"💰 <b>Price:</b> ${price}\n"
        f"💵 <b>Amount:</b> ${amount_usd}\n"
        f"Strategy: RSI < 30 (Oversold)"
    )
    
    # Discord (без HTML тегов, можно упростить)
    discord_msg = f"**{mode} BUY SIGNAL**\nCoin: {symbol}\nPrice: ${price}\nAmount: ${amount_usd}"

    # 1. В публичный канал (Хвастаемся сделкой)
    send_telegram(msg, TG_PUBLIC_ID)
    
    # 2. В приватный канал (Дублируем для контроля)
    send_telegram(msg, TG_PRIVATE_ID)
    
    # 3. В Дискорд
    send_discord(discord_msg)

def notify_error(error_text):
    # Ошибки шлем ТОЛЬКО админу в приват
    msg = f"⚠️ <b>BOT ERROR</b>\n\n<code>{error_text}</code>"
    send_telegram(msg, TG_PRIVATE_ID)

# --- ОСНОВНОЙ СЕРВЕР ---
@app.route('/tv_alert', methods=['POST'])
def webhook():
    data = request.json
    print(f"--- СИГНАЛ: {data} ---")
    
    symbol = data.get('ticker')
    side = data.get('action')
    amount_usd = float(data.get('amount_usd', 15))
    
    if side == 'buy':
        return execute_buy(symbol, amount_usd)
    
    return {"status": "ignored"}, 200

def execute_buy(symbol, amount_usd):
    try:
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        amount_coin = amount_usd / price
        amount_coin = exchange.amount_to_precision(symbol, amount_coin)
        
        print(f"Покупка {amount_coin} {symbol}...")
        
        # --- ! РЕАЛЬНАЯ ТОРГОВЛЯ (Раскомментировать для боя) ! ---
        # order = exchange.create_market_buy_order(symbol, amount_coin)
        # notify_all(symbol, price, amount_usd, is_test=False) # Отправляем уведомление
        # return {"status": "success", "order": order['id']}, 200
        
        # --- ТЕСТОВЫЙ РЕЖИМ ---
        print("Тест успех.")
        notify_all(symbol, price, amount_usd, is_test=True) # Отправляем уведомление
        return {"status": "success", "message": "Test Buy"}, 200
        
    except Exception as e:
        err_msg = str(e)
        print(f"ОШИБКА: {err_msg}")
        notify_error(err_msg) # Сообщаем об ошибке в TG
        return {"status": "error", "message": err_msg}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
