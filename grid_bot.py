# --- grid_bot.py (v5.0 - Full DB Integration) ---
import ccxt
import time
import os
import sqlite3
import requests
import urllib.parse
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
YOUR_TELEGRAM_ID = os.getenv('YOUR_TELEGRAM_ID')
DB_FILE = "trades.db"
FEE_RATE = 0.001 # 0.1% комиссия биржи

exchange = ccxt.binance({
    'apiKey': os.getenv('EXCHANGE_API_KEY'),
    'secret': os.getenv('EXCHANGE_API_SECRET'),
    'options': {'defaultType': 'spot'}
})
# !!! ЗАКОММЕНТИРУЙТЕ СТРОКУ НИЖЕ, ЕСЛИ ТОРГУЕТЕ НА РЕАЛЬНЫЕ ДЕНЬГИ !!!
exchange.set_sandbox_mode(True) 

current_grid_config = None 

def send_tg(text):
    if not TELEGRAM_TOKEN: return
    try: requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={YOUR_TELEGRAM_ID}&text={urllib.parse.quote_plus(text)}&parse_mode=Markdown", timeout=5)
    except: pass

def log_grid_profit(ticker, price, amount, gross_pnl):
    """Записывает прибыль от сетки в историю сделок"""
    try:
        # Считаем комиссию за круг (покупка + продажа)
        # Комиссия = (Сумма * 0.001) * 2
        volume_usd = price * amount
        total_comm = volume_usd * FEE_RATE * 2
        
        net_pnl = gross_pnl - total_comm

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        # Записываем как закрытую сделку
        c.execute('''
            INSERT INTO trades 
            (ticker, side, amount, price, highest_price, status, sell_price, pnl_usd, source, commission, net_pnl) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (ticker, 'buy', amount, price, 0, 'CLOSED', price, gross_pnl, '🕸 Grid', total_comm, net_pnl))
        
        conn.commit()
        conn.close()
        return net_pnl
    except Exception as e:
        print(f"Ошибка записи в БД: {e}")
        return gross_pnl

def get_grid_from_db():
    try:
        conn = sqlite3.connect(DB_FILE); c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='active_grids'")
        if not c.fetchone(): return None
        c.execute("SELECT * FROM active_grids LIMIT 1")
        row = c.fetchone()
        conn.close()
        if row: return {'ticker': row[0], 'lower': row[1], 'upper': row[2], 'count': row[3], 'amount': row[4]}
        return None
    except: return None

def calculate_levels(conf):
    step = (conf['upper'] - conf['lower']) / conf['count']
    return [conf['lower'] + (i * step) for i in range(conf['count'] + 1)]

def setup_grid(conf):
    print(f"--- ⚙️ Настройка сетки для {conf['ticker']} ---")
    send_tg(f"⚙️ **Начинаю расстановку сетки** для `{conf['ticker']}`...")
    
    try: exchange.cancel_all_orders(conf['ticker'])
    except: pass
    
    try: current_price = exchange.fetch_ticker(conf['ticker'])['last']
    except Exception as e: send_tg(f"❌ Ошибка цены: {e}"); return

    levels = calculate_levels(conf)
    placed = 0
    errors = []

    for price in levels:
        if abs(price - current_price) / current_price < 0.005: continue
        try:
            if price < current_price:
                exchange.create_limit_buy_order(conf['ticker'], conf['amount'], price)
            else:
                exchange.create_limit_sell_order(conf['ticker'], conf['amount'], price)
            placed += 1
            time.sleep(0.2)
        except Exception as e:
            if "Insufficient balance" in str(e) and "Баланс" not in str(errors): errors.append("Не хватает баланса (BNB/USDT)")
            elif "MIN_NOTIONAL" in str(e) and "MIN" not in str(errors): errors.append("Сумма < $10")
            
    if placed > 0: send_tg(f"✅ **Грид Активен!**\nОрдеров: {placed}/{len(levels)}")
    else: send_tg(f"❌ **Грид ПРОВАЛЕН!**\n{errors}")

def loop():
    global current_grid_config
    while True:
        db_conf = get_grid_from_db()
        
        # Остановка
        if not db_conf and current_grid_config:
            print("🛑 Грид удален.")
            try: exchange.cancel_all_orders(current_grid_config['ticker'])
            except: pass
            current_grid_config = None
            send_tg("🛑 Грид остановлен.")
            time.sleep(5); continue

        if not db_conf: time.sleep(5); continue
            
        # Запуск
        if db_conf != current_grid_config:
            current_grid_config = db_conf
            setup_grid(db_conf)
            
        # Мониторинг исполнения
        if current_grid_config:
            try:
                sym = current_grid_config['ticker']
                levels = calculate_levels(current_grid_config)
                open_orders = exchange.fetch_open_orders(sym)
                open_prices = [o['price'] for o in open_orders]
                current_price = exchange.fetch_ticker(sym)['last']
                
                for level in levels:
                    # Проверяем, исчез ли ордер (исполнился)
                    exists = False
                    for op in open_prices:
                        if abs(op - level) / level < 0.001: exists = True; break
                    
                    if not exists:
                        # Уровень сработал!
                        amount = current_grid_config['amount']
                        
                        if abs(current_price - level) / level > 0.005:
                            if current_price > level:
                                # Цена ушла ВВЕРХ -> Сработал BUY (внизу) -> Ставим SELL (чтобы закрыть)
                                # НЕТ, в классическом гриде: 
                                # Если цена ВЫШЕ уровня, значит мы его ПРОБИЛИ снизу вверх. Значит сработал SELL.
                                # Нам нужно поставить BUY обратно.
                                print(f"♻️ Восстанавливаю BUY на {level:.2f}")
                                exchange.create_limit_buy_order(sym, amount, level)
                                
                                # Это значит мы продали дороже, чем купили шаг назад. Фиксируем прибыль!
                                step_profit = ((current_grid_config['upper'] - current_grid_config['lower']) / current_grid_config['count']) * amount
                                net_profit = log_grid_profit(sym, level, amount, step_profit)
                                
                                send_tg(f"💰 **GRID PROFIT:** +${net_profit:.2f}\nУровень {level} перезаряжен.")
                                
                            else:
                                # Цена ушла ВНИЗ -> Сработал BUY. Ставим SELL обратно.
                                print(f"♻️ Восстанавливаю SELL на {level:.2f}")
                                exchange.create_limit_sell_order(sym, amount, level)
                                # Тут прибыли нет, мы просто набрали позицию
                                
            except Exception as e: print(f"Loop err: {e}")

        time.sleep(10)

if __name__ == "__main__":
    loop()
