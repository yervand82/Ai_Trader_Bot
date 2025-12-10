# --- shadow_scanner.py (Теневой режим Golden Scalper) ---
import ccxt
import pandas as pd
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from ta.trend import EMAIndicator
import time
import os

# Настройки как в TV
TIMEFRAME = '5m'
RSI_PERIOD = 7
RSI_BUY = 30
BB_PERIOD = 20
BB_STD = 2.0
EMA_PERIOD = 100

# Пары для слежки
PAIRS = ['SOL/USDT', 'ETH/USDT', 'BNB/USDT', 'SUI/USDT']

exchange = ccxt.binance()

def check_market():
    print(f"--- 🕵️ Теневой анализ ({len(PAIRS)} пар) ---")
    
    for symbol in PAIRS:
        try:
            # Качаем данные
            ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=200)
            if not ohlcv: continue
            
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            
            # 1. RSI (7)
            rsi = RSIIndicator(close=df['c'], window=RSI_PERIOD).rsi().iloc[-1]
            
            # 2. Bollinger Bands (20, 2)
            bb = BollingerBands(close=df['c'], window=BB_PERIOD, window_dev=BB_STD)
            lower_bb = bb.bollinger_lband().iloc[-1]
            
            # 3. EMA (100) - Тренд
            ema = EMAIndicator(close=df['c'], window=EMA_PERIOD).ema_indicator().iloc[-1]
            
            current_price = df['c'].iloc[-1]
            
            # --- ЛОГИКА "GOLDEN SCALPER" ---
            # Условие: Тренд ВВЕРХ (Цена > EMA) И Пробой Боллинджера вниз И RSI перепродан
            is_uptrend = current_price > ema
            is_dip = current_price < lower_bb
            is_oversold = rsi < RSI_BUY
            
            # Лог для проверки
            # print(f"{symbol}: Price {current_price} | EMA {ema:.2f} | BB_Low {lower_bb:.2f} | RSI {rsi:.1f}")

            if is_uptrend and is_dip and is_oversold:
                print(f"✅ [SHADOW] Я БЫ КУПИЛ {symbol} ПРЯМО СЕЙЧАС!")
                print(f"   Причина: Trend UP, Price < BB, RSI {rsi:.1f} < {RSI_BUY}")
                # В будущем здесь будет: requests.post(...)

        except Exception as e:
            print(f"Err {symbol}: {e}")

if __name__ == "__main__":
    print("🕵️ Теневой сканер запущен. Я только наблюдаю.")
    while True:
        check_market()
        time.sleep(60) # Проверяем каждую минуту (как закрытие свечи)
