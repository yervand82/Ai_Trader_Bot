# --- scanner_ml.py (AI Powered Trader) ---
import time
import requests
import json
import os
import sqlite3
from dotenv import load_dotenv
from ai_model import TradingAI  # Импортируем наш обученный мозг

# --- НАСТРОЙКИ ---
CONFIDENCE_THRESHOLD = 0.60  # Покупать только если уверенность >= 60%
AMOUNT_TO_BUY = "15"         # Сумма покупки
WEBHOOK_URL = "http://localhost:5000/tv_alert"
DB_FILE = "trades.db"
COOLDOWN = 3600              # 1 час пауза на монету

load_dotenv()

# Инициализация ИИ
ai = TradingAI()
print("🧠 Загружаю мозг...")
if not os.path.exists("brain.pkl"):
    print("⚠️ Мозг не найден! Обучаю с нуля...")
    ai.train('BTC/USDT')
else:
    # Просто делаем фиктивный прогноз, чтобы загрузить файл
    ai.predict_live('BTC/USDT') 
    print("✅ Мозг загружен из файла.")

last_trade_time = {}

def get_pairs_from_db():
    try:
        conn = sqlite3.connect(DB_FILE); cursor = conn.cursor()
        cursor.execute("SELECT ticker FROM watchlist")
        return [r[0] for r in cursor.fetchall()]
    except: return []

def scan_ai():
    pairs = get_pairs_from_db()
    if not pairs:
        print("⚠️ Список пуст! Добавьте монеты через Telegram: /add ETH/USDT")
        return

    print(f"--- 🧠 AI Анализ ({len(pairs)} пар) ---")
    
    for symbol in pairs:
        try:
            # Спрашиваем ИИ
            probability = ai.predict_live(symbol)
            
            # Красивый вывод
            icon = "🟢" if probability >= CONFIDENCE_THRESHOLD else "⚪️"
            print(f"{icon} {symbol}: Вероятность {probability*100:.1f}%")

            # ЛОГИКА ВХОДА
            if probability >= CONFIDENCE_THRESHOLD:
                
                # Проверка кулдауна
                if time.time() - last_trade_time.get(symbol, 0) < COOLDOWN:
                    print(f"   ⏳ Кулдаун (недавно торговали)")
                    continue

                print(f"💎 **СИГНАЛ ПОДТВЕРЖДЕН!** Покупаю {symbol}")
                
                # Формируем умную лесенку
                # Если уверенность высокая (70%), ставим тейки повыше
                if probability > 0.7:
                    tp_str = "1.5% 3% 6%"
                else:
                    tp_str = "1% 2% 4%"
                
                payload = {
                    "signal": "buy",
                    "ticker": symbol.replace('/', ''),
                    "amount": AMOUNT_TO_BUY,
                    "tp": tp_str,
                    "source": f"🧠 AI Bot ({probability*100:.0f}%)"
                }
                
                try:
                    requests.post(WEBHOOK_URL, json=payload, timeout=2)
                    print(f"🚀 Ордер отправлен")
                    last_trade_time[symbol] = time.time()
                except Exception as e:
                    print(f"❌ Ошибка отправки: {e}")
                    
        except Exception as e:
            print(f"Ошибка анализа {symbol}: {e}")
            time.sleep(1)

if __name__ == "__main__":
    print(f"🤖 AI-Трейдер запущен. Ищем вероятность > {CONFIDENCE_THRESHOLD*100}%")
    while True:
        scan_ai()
        print("💤 Сплю 60 секунд...")
        time.sleep(60)
