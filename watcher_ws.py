# --- watcher_ws.py (v16.0 - SYNTAX FIXED) ---
import asyncio
import websockets
import json
import sqlite3
import ccxt
import os
import math
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# ИМПОРТ РЕКЛАМЫ
try: 
    from notifier import send_public_message
except: 
    send_public_message = lambda *a: None

DB_FILE = "trades.db"
FEE_RATE = 0.001
WS_URL = "wss://stream.binance.com:9443/ws/!miniTicker@arr"
TRAILING_PERCENT = 0.02

load_dotenv()
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
YOUR_TELEGRAM_ID = os.getenv('YOUR_TELEGRAM_ID')

exchange = ccxt.binance({'apiKey': API_KEY, 'secret': API_SECRET, 'options': {'defaultType': 'spot'}})
# exchange.set_sandbox_mode(True) # ТЕСТНЕТ (Раскомментировать если нужно)

trades_cache = {}

def get_market_precision(symbol):
    try: 
        return exchange.load_markets()[symbol]['precision']['amount']
    except: 
        return 4

def amount_to_precision(symbol, amount):
    p = 4
    try:
        p = get_market_precision(symbol)
    except: pass
    f = 10**p
    return math.floor(amount * f) / f

def send_tg(text):
    if not TELEGRAM_TOKEN: return
    try: 
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={YOUR_TELEGRAM_ID}&text={text}", timeout=2)
    except: pass

def update_cache():
    global trades_cache
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, ticker, amount, entry_price, tp_config, sl_percent FROM trades WHERE status='OPEN'")
        rows = c.fetchall()
        conn.close()
        
        new_cache = {}
        for r in rows:
            sym = r[1].replace('/','').upper()
            new_cache[sym] = {
                'id': r[0], 
                'ticker': r[1], 
                'amt': r[2], 
                'entry': r[3], 
                'tp': r[4], 
                'sl': r[5] if r[5] else TRAILING_PERCENT, 
                'high': r[3]
            }
        trades_cache = new_cache
        if rows: 
            print(f"👀 Слежу: {list(new_cache.keys())}")
    except: pass

def close_trade_db(trade, price, raw_amount, reason):
    try:
        sym = trade['ticker'].replace('/','')
        amount = amount_to_precision(sym, raw_amount)
        
        if amount * price < 5.1: 
            return # Пыль

        try: 
            exchange.create_market_sell_order(sym, amount)
        except Exception as e: 
            print(f"Sell Err: {e}")
            if "Insufficient" in str(e): 
                conn=sqlite3.connect(DB_FILE)
                c=conn.cursor()
                c.execute("UPDATE trades SET status='CLOSED', note='NoBal' WHERE id=?", (trade['id'],))
                conn.commit()
                conn.close()
            return

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        buy_comm = trade['amt'] * 0.001 # Примерная комиссия входа
        sell_comm = (amount * price) * FEE_RATE
        # tot_comm = (buy_comm * (amount / trade['amt']) if trade['amt']>0 else 0) + sell_comm
        tot_comm = sell_comm * 2 # Упрощено
        
        gross = (price - trade['entry']) * amount
        net = gross - tot_comm

        if trade['amt'] - amount < 0.0001:
            c.execute("UPDATE trades SET status='CLOSED', sell_price=?, pnl_usd=?, commission=commission+?, net_pnl=?, exit_time=datetime('now') WHERE id=?", (price, gross, sell_comm, net, trade['id']))
        else:
            c.execute("UPDATE trades SET amount=? WHERE id=?", (trade['amt'] - amount, trade['id']))
            c.execute("INSERT INTO trades (ticker, side, amount, price, status, sell_price, pnl_usd, source, commission, net_pnl, exit_time) VALUES (?, 'buy', ?, ?, 'CLOSED', ?, ?, ?, ?, ?, datetime('now'))", (trade['ticker'], amount, trade['entry'], price, gross, "Auto", tot_comm, net))

        conn.commit()
        conn.close()
        
        # Личное
        icon = "🟢" if net > 0 else "🔴"
        send_tg(f"{reason}\n📉 ${price}\n{icon} Net: ${net:.2f}")
        
        # Публичное
        msg_type = "PROFIT" if net > 0 else "LOSS"
        pub_msg = f"{icon} **СДЕЛКА ЗАКРЫТА**\n🔹 #{trade['ticker']}\n💰 PnL: **${net:.2f}**\n📉 Выход: ${price}\n📝 {reason.split(':')[0].replace('*','')}"
        send_public_message(pub_msg, msg_type)

    except Exception as e: 
        print(f"Close Err: {e}")

async def process(data):
    sym = data['s'].upper()
    price = float(data['c'])
    
    if sym in trades_cache:
        t = trades_cache[sym]
        
        # Обновляем хай
        if price > t['high']: 
            t['high'] = price
        
        # Стоп
        stop_price = t['high'] * (1 - t['sl'])
        if price < stop_price:
            close_trade_db(t, price, t['amt'], f"🛡 **STOP ({t['sl']*100:.1f}%)**: {t['ticker']}")
            del trades_cache[sym]
            return

        # Тейк
        if t['tp']:
            try:
                tps = json.loads(t['tp'])
                updated = False
                for step in tps:
                    if not step['done'] and price >= step['price']:
                        # Продаем часть (33%)
                        part = t['amt'] * 0.33
                        close_trade_db(t, price, part, f"🎯 **TP (+{step['pct_name']}%)**: {t['ticker']}")
                        
                        step['done'] = True
                        updated = True
                        t['amt'] -= part # Обновляем локально
                
                if updated:
                    conn=sqlite3.connect(DB_FILE)
                    c=conn.cursor()
                    c.execute("UPDATE trades SET tp_config=? WHERE id=?", (json.dumps(tps), t['id']))
                    conn.commit()
                    conn.close()
                    t['tp'] = json.dumps(tps)
            except: pass

async def listen():
    print("🚀 Watcher v16.0 (SYNTAX FIXED) Started...")
    
    # ИСПРАВЛЕНО: Многострочный try/except
    try:
        await asyncio.to_thread(exchange.load_markets)
    except:
        pass
        
    async with websockets.connect(WS_URL) as websocket:
        last = 0
        while True:
            if time.time() - last > 5: 
                update_cache()
                last = time.time()
            
            msg = await websocket.recv()
            data = json.loads(msg)
            
            if isinstance(data, list):
                for i in data: await process(i)
            else: 
                await process(data)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try: 
        loop.run_until_complete(listen())
    except KeyboardInterrupt:
        print("\n🛑 Stopped.")
    except Exception as e:
        print(f"Error: {e}")
