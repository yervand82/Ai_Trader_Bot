# --- trade_server.py (FIXED DISCORD) ---
from flask import Flask, request
import ccxt
import os
import requests
from dotenv import load_dotenv

# Загрузка
load_dotenv()
API_KEY = os.getenv("API_KEY")
SECRET = os.getenv("API_SECRET")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_PRIVATE_ID = os.getenv("TG_PRIVATE_ID")
TG_PUBLIC_ID = os.getenv("TG_PUBLIC_ID")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")

app = Flask(__name__)

exchange = ccxt.binance({
    'apiKey': API_KEY, 'secret': SECRET,
    'enableRateLimit': True, 'options': {'defaultType': 'spot'} 
})
exchange.set_sandbox_mode(True) # TESTNET

# --- УВЕДОМЛЕНИЯ ---
def notify(symbol, action, price, amount, is_test=True):
    mode = "[TEST MODE]" if is_test else "🚀 LIVE"
    emoji = "🟢" if action == "buy" else "🔴"
    
    # Текст для Телеграм (с HTML)
    msg_tg = (
        f"{emoji} <b>{mode} {action.upper()} SIGNAL</b>\n\n"
        f"💎 <b>Coin:</b> #{symbol.replace('/', '')}\n"
        f"💰 <b>Price:</b> ${price}\n"
        f"📊 <b>Size:</b> {amount}"
    )

    # Текст для Дискорда (Без HTML, так как Дискорд его не понимает)
    msg_discord = (
        f"**{emoji} {mode} {action.upper()} SIGNAL**\n"
        f"💎 **Coin:** {symbol}\n"
        f"💰 **Price:** ${price}\n"
        f"📊 **Size:** {amount}"
    )
    
    # 1. Отправляем в Телеграм
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        requests.post(url, json={'chat_id': TG_PUBLIC_ID, 'text': msg_tg, 'parse_mode': 'HTML'})
        requests.post(url, json={'chat_id': TG_PRIVATE_ID, 'text': msg_tg, 'parse_mode': 'HTML'})
    except Exception as e:
        print(f"Ошибка TG: {e}")

    # 2. Отправляем в Discord (ВОТ ЭТОГО БЛОКА НЕ ХВАТАЛО)
    if DISCORD_WEBHOOK:
        try:
            requests.post(DISCORD_WEBHOOK, json={'content': msg_discord})
        except Exception as e:
            print(f"Ошибка Discord: {e}")

# --- ЛОГИКА ---
@app.route('/tv_alert', methods=['POST'])
def webhook():
    data = request.json
    symbol = data.get('ticker')
    side = data.get('action') # 'buy' или 'sell'
    amount_usd = float(data.get('amount_usd', 15))
    
    print(f"\n--- СИГНАЛ: {side.upper()} {symbol} ---")
    
    if side == 'buy':
        return execute_buy(symbol, amount_usd)
    elif side == 'sell':
        return execute_sell(symbol)
    
    return {"status": "ignored"}, 200

def execute_buy(symbol, amount_usd):
    try:
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        amount_coin = exchange.amount_to_precision(symbol, amount_usd / price)
        
        print(f"Покупаем {amount_coin} {symbol}...")
        
        # --- TESTNET ---
        notify(symbol, "buy", price, f"${amount_usd}", is_test=True)
        return {"status": "success", "message": "Test Buy"}, 200
        
        # --- REAL ORDER ---
        # exchange.create_market_buy_order(symbol, amount_coin)
        # notify(symbol, "buy", price, f"${amount_usd}", is_test=False)

    except Exception as e:
        print(f"Ошибка покупки: {e}")
        return {"error": str(e)}, 500

def execute_sell(symbol):
    try:
        base_currency = symbol.split('/')[0]
        balance = exchange.fetch_balance()
        free_amount = balance[base_currency]['free']
        
        if free_amount == 0:
            print(f"Нечего продавать: баланс {base_currency} пуст.")
            return {"status": "skipped", "message": "Zero balance"}, 200

        print(f"Продаем всё: {free_amount} {symbol}...")
        
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']

        # --- TESTNET ---
        notify(symbol, "sell", price, f"{free_amount} coins", is_test=True)
        return {"status": "success", "message": "Test Sell"}, 200

        # --- REAL ORDER ---
        # exchange.create_market_sell_order(symbol, free_amount)
        # notify(symbol, "sell", price, f"{free_amount} coins", is_test=False)

    except Exception as e:
        print(f"Ошибка продажи: {e}")
        return {"error": str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
