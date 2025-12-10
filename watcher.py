# --- watcher.py (v4.0 - Trailing + Ladder TP) ---
import time
import sqlite3
import ccxt
import os
import requests
import urllib.parse
import json
from dotenv import load_dotenv

TRAILING_PERCENT = 0.02
CHECK_INTERVAL = 30 
DB_FILE = "trades.db"

load_dotenv()
API_KEY = os.getenv('EXCHANGE_API_KEY')
API_SECRET = os.getenv('EXCHANGE_API_SECRET')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
YOUR_TELEGRAM_ID = os.getenv('YOUR_TELEGRAM_ID')

exchange = ccxt.binance({'apiKey': API_KEY, 'secret': API_SECRET, 'options': {'defaultType': 'spot'}})
exchange.set_sandbox_mode(True)

def send_tg(text):
    if not TELEGRAM_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={YOUR_TELEGRAM_ID}&text={urllib.parse.quote_plus(text)}&parse_mode=Markdown"
    try: requests.get(url, timeout=5)
    except: pass

def close_part(trade_id, ticker, amount, current_price, is_full_close=False, reason=""):
    """Универсальная функция закрытия"""
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10); c = conn.cursor()
        
        # Получаем актуальные данные (amount мог измениться!)
        c.execute("SELECT amount, price FROM trades WHERE id=?", (trade_id,))
        row = c.fetchone()
        if not row: return
        
        current_db_amount, buy_price = row
        
        # Если пытаемся продать больше, чем есть - продаем всё что есть
        sell_amount = min(amount, current_db_amount)
        pnl = (current_price - buy_price) * sell_amount
        
        if is_full_close or (current_db_amount - sell_amount < 0.000001):
            # Полное закрытие
            c.execute("UPDATE trades SET status='CLOSED', sell_price=?, pnl_usd=? WHERE id=?", (current_price, pnl, trade_id))
        else:
            # Частичное
            new_amount = current_db_amount - sell_amount
            c.execute("UPDATE trades SET amount=? WHERE id=?", (new_amount, trade_id))
            # Запись в историю
            c.execute('''INSERT INTO trades (ticker, side, amount, price, highest_price, status, sell_price, pnl_usd) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (ticker, 'buy', sell_amount, buy_price, 0, 'CLOSED', current_price, pnl))

        conn.commit(); conn.close()
        
        # exchange.create_market_sell_order(ticker_fmt, sell_amount) # REAL
        
        icon = "🟢" if pnl > 0 else "🔴"
        msg = f"{reason}\nПродано: {sell_amount}\nЦена: {current_price}\n{icon} PnL: ${pnl:.2f}"
        print(msg)
        send_tg(msg)

    except Exception as e: print(f"Ошибка Close: {e}")

def check():
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10); c = conn.cursor()
        c.execute("SELECT id, ticker, amount, price, highest_price, tp_config FROM trades WHERE status='OPEN'")
        trades = c.fetchall(); conn.close()
        
        if not trades: return

        print(f"--- Проверка {len(trades)} позиций ---")
        
        for t in trades:
            tid, ticker, amount, buy_price, high_price, tp_json = t
            sym = ticker if '/' in ticker else f"{ticker[:-4]}/{ticker[-4:]}"
            
            try:
                curr_price = exchange.fetch_ticker(sym)['last']
                
                # 1. ЛОГИКА ТРЕЙЛИНГА
                if curr_price > high_price:
                    conn = sqlite3.connect(DB_FILE, timeout=10); c = conn.cursor()
                    c.execute("UPDATE trades SET highest_price = ? WHERE id = ?", (curr_price, tid))
                    conn.commit(); conn.close()
                    high_price = curr_price

                stop_price = high_price * (1 - TRAILING_PERCENT)
                print(f"{ticker}: Тек {curr_price} | Стоп {stop_price:.2f}")

                if curr_price < stop_price:
                    close_part(tid, ticker, amount, curr_price, is_full_close=True, reason=f"🛡 **STOP-LOSS**: {ticker}")
                    continue # Сделка закрыта, идем к следующей

                # 2. ЛОГИКА ЛЕСТНИЦЫ (TAKE PROFIT)
                if tp_json:
                    tps = json.loads(tp_json)
                    updated = False
                    
                    for step in tps:
                        # Если шаг еще не выполнен И цена выше цели
                        if not step['done'] and curr_price >= step['price']:
                            # ПРОДАЕМ ЧАСТЬ!
                            part_amount = step['amount']
                            pct_name = step.get('pct_name', '?')
                            
                            close_part(tid, ticker, part_amount, curr_price, is_full_close=False, reason=f"🪜 **LADDER TP (+{pct_name}%)**: {ticker}")
                            
                            step['done'] = True
                            updated = True
                    
                    # Если что-то сработало, обновляем конфиг в БД (чтобы не продать это снова)
                    if updated:
                         conn = sqlite3.connect(DB_FILE, timeout=10); c = conn.cursor()
                         c.execute("UPDATE trades SET tp_config = ? WHERE id = ?", (json.dumps(tps), tid))
                         conn.commit(); conn.close()

            except Exception as e: print(f"Ошибка тикера {ticker}: {e}")

    except Exception as e: print(f"Ошибка Watcher: {e}")

if __name__ == "__main__":
    print(f"Watcher (Ladder + Trailing) запущен.")
    while True:
        check()
        time.sleep(CHECK_INTERVAL)
