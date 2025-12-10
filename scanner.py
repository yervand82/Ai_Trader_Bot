# --- scanner.py (AI Auto-Pilot) ---
import time
import requests
import json
import sqlite3
import os
from dotenv import load_dotenv
try: from ai_model import TradingAI
except ImportError: print("❌ Нет ai_model.py"); exit()

# --- НАСТРОЙКИ ---
PAIRS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'DOGE/USDT', 'XRP/USDT', 'SUI/USDT']
CONFIDENCE_THRESHOLD = 0.65  # Входим только если ИИ уверен на 65%
AMOUNT_TO_BUY = "15"         # Размер сделки ($15)
WEBHOOK_URL = "http://localhost:5000/tv_alert"
COOLDOWN = 3600              # 1 час пауза на монету

load_dotenv()
print("🧠 Загружаю Нейросеть...")
ai = TradingAI()
if not os.path.exists("brain.pkl"):
    print("⚠️ Обучаю с нуля...")
    ai.train('BTC/USDT')
else:
    try: ai.predict_live('BTC/USDT')
    except: ai.train('BTC/USDT')

last_trade_time = {}

def scan_ai():
    print(f"--- 🧠 AI Сканирование ({len(PAIRS)} пар) ---")
    for symbol in PAIRS:
        try:
            # Спрашиваем ИИ
            probability = ai.predict_live(symbol)
            
            # Визуал в консоль
            col = "\033[92m" if probability > 0.5 else "\033[90m"
            print(f"{col}{symbol}: {probability*100:.1f}%\033[0m")

            if probability >= CONFIDENCE_THRESHOLD:
                if time.time() - last_trade_time.get(symbol, 0) < COOLDOWN: continue

                print(f"💎 **СИГНАЛ!** {symbol} ({probability*100:.0f}%)")
                
                # Умная лесенка от уверенности
                tp_str = "1% 2.5% 5%" if probability < 0.75 else "1.5% 3% 7%"
                
                payload = {
                    "signal": "buy",
                    "ticker": symbol.replace('/', ''),
                    "amount": AMOUNT_TO_BUY,
                    "tp": tp_str,
                    "source": f"🧠 AI Neuro ({probability*100:.0f}%)"
                }
                
                try:
                    requests.post(WEBHOOK_URL, json=payload, timeout=2)
                    last_trade_time[symbol] = time.time()
                except: pass
        except: pass

if __name__ == "__main__":
    print(f"🤖 AI-Трейдер запущен. Порог: {CONFIDENCE_THRESHOLD*100}%")
    while True:
        scan_ai()
        time.sleep(60)
