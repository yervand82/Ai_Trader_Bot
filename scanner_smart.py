# --- scanner_smart.py (Аналитик) ---
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
WEBHOOK_URL = "http://localhost:5000/tv_alert" # Куда кричать "ПОКУПАЙ!"
COOLDOWN = 300          # 5 минут не трогать пару после сигнала
PAIRS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'DOGE/USDT', 'XRP/USDT'] # Список наблюдения

load_dotenv() # Загрузка ключей из .env (если нужны для публичных данных, обычно не нужны)
exchange = ccxt.binance() # Для сканирования ключи не обязательны

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
        # Проверка кулдауна (чтобы не спамить сигналами по одной монете)
        if symbol in last_alert_time:
            if time.time() - last_alert_time[symbol] < COOLDOWN:
                continue

        df = get_data(symbol)
        if df is None: continue

        # --- ТЕХНИЧЕСКИЙ АНАЛИЗ ---
        # Считаем RSI
        rsi_indicator = RSIIndicator(close=df['close'], window=14)
        current_rsi = rsi_indicator.rsi().iloc[-1]

        # Логика стратегии (RSI < 30 - Перепроданность -> ПОКУПКА)
        if current_rsi < 30:
            print(f">>> СИГНАЛ: {symbol} RSI={round(current_rsi, 2)}")
            
            # Формируем сообщение для Исполнителя
            signal_data = {
                "ticker": symbol,        # BTC/USDT
                "action": "buy",         # Покупка
                "price": df['close'].iloc[-1],
                "amount_usd": AMOUNT_TO_BUY
            }
            
            # Отправка сигнала Исполнителю
            try:
                requests.post(WEBHOOK_URL, json=signal_data)
                print(f"Сигнал отправлен исполнителю!")
                last_alert_time[symbol] = time.time()
            except Exception as e:
                print(f"Не удалось связаться с Исполнителем (он запущен?): {e}")
        
        else:
            print(f"{symbol}: RSI {round(current_rsi, 2)} (Ждем...)")
            
        time.sleep(1) # Пауза между монетами, чтобы не забанил Binance

if __name__ == "__main__":
    print("СКАНЕР ЗАПУЩЕН...")
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
