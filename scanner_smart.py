# --- scanner_smart.py (FULL VERSION: BUY & SELL) ---
import ccxt
import pandas as pd
import time
import requests
import json
import os
from ta.momentum import RSIIndicator
from dotenv import load_dotenv

# --- НАСТРОЙКИ ---
TIMEFRAME = '15m'       
AMOUNT_TO_BUY = 15      # $15
WEBHOOK_URL = "http://localhost:5000/tv_alert" 
COOLDOWN = 300          # 5 минут кулдаун
PAIRS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'DOGE/USDT', 'XRP/USDT'] 

load_dotenv() 
exchange = ccxt.binance() 

last_alert_time = {}

def get_data(symbol):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except Exception as e:
        print(f"Ошибка получения данных {symbol}: {e}")
        return None

def analyze():
    print(f"--- Сканирование {len(PAIRS)} монет [{TIMEFRAME}] ---")
    
    for symbol in PAIRS:
        # Проверка кулдауна
        if symbol in last_alert_time:
            if time.time() - last_alert_time[symbol] < COOLDOWN:
                continue

        df = get_data(symbol)
        if df is None: continue

        # --- ТЕХНИЧЕСКИЙ АНАЛИЗ ---
        try:
            rsi_indicator = RSIIndicator(close=df['close'], window=14)
            current_rsi = rsi_indicator.rsi().iloc[-1]
            current_price = df['close'].iloc[-1]

            # 1. ЛОГИКА ПОКУПКИ (RSI < 30)
            if current_rsi < 30:
                print(f">>> 🟢 СИГНАЛ BUY: {symbol} RSI={round(current_rsi, 2)}")
                signal_data = {
                    "ticker": symbol,
                    "action": "buy",
                    "price": current_price,
                    "amount_usd": AMOUNT_TO_BUY
                }
                requests.post(WEBHOOK_URL, json=signal_data)
                last_alert_time[symbol] = time.time()

            # 2. ЛОГИКА ПРОДАЖИ (RSI > 70)
            elif current_rsi > 70:
                print(f">>> 🔴 СИГНАЛ SELL: {symbol} RSI={round(current_rsi, 2)}")
                signal_data = {
                    "ticker": symbol,
                    "action": "sell",
                    "price": current_price,
                    "amount_usd": 0 
                }
                requests.post(WEBHOOK_URL, json=signal_data)
                last_alert_time[symbol] = time.time()
            
            # 3. ЖДЕМ
            else:
                print(f"{symbol}: RSI {round(current_rsi, 2)} (Ждем...)")

        except Exception as e:
            print(f"Ошибка анализа {symbol}: {e}")
            
        time.sleep(1) # Пауза между запросами к бирже

if __name__ == "__main__":
    print("СКАНЕР (BUY/SELL) ЗАПУЩЕН...")
    while True:
        try:
            analyze()
            print("Пауза 60 сек...")
            time.sleep(60) 
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Критическая ошибка сканера: {e}")
            time.sleep(10)
