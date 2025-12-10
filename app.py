from flask import Flask, request
import logging, json, os, ccxt, sqlite3, time, threading
from dotenv import load_dotenv
import requests 
try: from notifier import send_public_message
except: send_public_message = lambda *a: None

load_dotenv()
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
YOUR_TELEGRAM_ID = os.getenv('YOUR_TELEGRAM_ID')
DB_FILE = "trades.db"
FEE_RATE = 0.001 
TRAILING_PERCENT = 0.02 

exchange = ccxt.binance({'apiKey': API_KEY, 'secret': API_SECRET, 'options': {'defaultType': 'spot'}})
# exchange.set_sandbox_mode(True) # <--- РАСКОММЕНТИРУЙТЕ ДЛЯ ТЕСТНЕТА!

app = Flask(__name__)
logging.basicConfig(filename='alerts.log', level=logging.INFO)

def init_db():
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS trades (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, ticker TEXT, side TEXT, amount REAL, price REAL, highest_price REAL, status TEXT, sell_price REAL, pnl_usd REAL, tp_config TEXT, source TEXT, commission REAL, net_pnl REAL, exit_time TEXT, sl_percent REAL DEFAULT 0.02)''')
    c.execute('''CREATE TABLE IF NOT EXISTS active_grids (ticker TEXT PRIMARY KEY, lower_price REAL, upper_price REAL, grid_count INTEGER, amount_per_grid REAL, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS trade_limits (ticker TEXT PRIMARY KEY, min_price REAL, max_price REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS bot_settings (key TEXT PRIMARY KEY, value TEXT)''')
    conn.commit(); conn.close()

def send_telegram_message(text):
    if not TELEGRAM_TOKEN: return
    try: requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={YOUR_TELEGRAM_ID}&text={text}", timeout=5)
    except: pass

def get_allowed_budget(cost):
    try:
        conn = sqlite3.connect(DB_FILE); c = conn.cursor()
        c.execute("SELECT value FROM bot_settings WHERE key='max_budget'"); row = c.fetchone()
        if not row: conn.close(); return cost, ""
        max_b = float(row[0])
        c.execute("SELECT SUM(amount * price) FROM trades WHERE status='OPEN'"); trade_exposure = c.fetchone()[0] or 0.0
        conn.close()
        rem = max_b - trade_exposure
        if rem < 5: return 0, f"⛔️ Бюджет исчерпан! Лимит: ${max_b}"
        if cost > rem: return rem, f"⚠️ Урезано до ${rem:.2f}"
        return cost, ""
    except: return cost, ""

def add_buy_trade(ticker, amount, price, tp_str, source, sl):
    try:
        conn = sqlite3.connect(DB_FILE); c = conn.cursor()
        tp_json = None
        if tp_str:
            pcts = [float(x.replace('%','')) for x in tp_str.split()]
            steps = [{"price": price*(1+p/100), "amount": amount/len(pcts), "pct_name": p, "done": False} for p in pcts]
            tp_json = json.dumps(steps)
        comm = (amount * price) * FEE_RATE
        c.execute("INSERT INTO trades (ticker, side, amount, price, highest_price, status, tp_config, source, commission, sl_percent) VALUES (?,?,?,?,?,?,?,?,?,?)", 
                  (ticker, 'buy', amount, price, price, 'OPEN', tp_json, source, comm, sl))
        conn.commit(); conn.close()
    except: pass

def place_order(signal, ticker, amount_input, tp_str=None, source='Manual', sl_input=None):
    if signal == 'panic': return
    try:
        t_clean = ticker.replace('/', '')
        # АВТО-ИСПРАВЛЕНИЕ USD -> USDT
        if t_clean.endswith("USD") and not t_clean.endswith("USDT"): t_clean += "T"; ticker += "T"
            
        price = exchange.fetch_ticker(t_clean)['last']
        
        if signal == 'buy':
            # Расчет суммы
            if "%" in str(amount_input):
                 bal = exchange.fetch_balance()['free'].get('USDT', 0)
                 if bal < 10: return send_telegram_message("⛔️ Нет USDT")
                 usd_amount = bal * (float(str(amount_input).replace('%',''))/100)
            else: usd_amount = float(amount_input) * price # Если введено кол-во монет? Нет, считаем что ввод в монетах.
            # Упростим: ввод всегда в монетах, переводим в баксы для бюджета
            
            # Если ввод был в монетах (например 10 XRP), то usd_amount = 10 * цена
            # Если ввод был 10% -> мы уже получили usd_amount
            
            # Для простоты считаем что amount_input - это КОЛИЧЕСТВО МОНЕТ (если число)
            if not "%" in str(amount_input):
                 usd_amount = float(amount_input) * price
            
            allow_usd, warn = get_allowed_budget(usd_amount)
            if allow_usd < 5: return send_telegram_message(warn)
            if warn: send_telegram_message(warn)
            
            final_coins = allow_usd / price
            
            # ОРДЕР
            try: exchange.create_market_buy_order(t_clean, final_coins)
            except Exception as e: return send_telegram_message(f"❌ Биржа: {e}")
            
            # SL
            sl = float(str(sl_input).replace('%',''))/100 if sl_input else TRAILING_PERCENT
            
            add_buy_trade(ticker, final_coins, price, tp_str, source, sl)
            
            msg = f"✅ [{source}] BUY: {final_coins:.4f} {ticker} @ {price}"
            send_telegram_message(msg)
            
            # ПУБЛИКАЦИЯ
            pub = f"🤖 **ВХОД В СДЕЛКУ**\n#{ticker}\n💵 Вход: `${price}`\n📊 Сигнал: {source}\n🎯 Тейки: {tp_str if tp_str else 'Авто'}"
            send_public_message(pub, "BUY")

        elif signal == 'sell':
            # Продажа через Watcher, тут заглушка
            pass

    except Exception as e: app.logger.error(f"Err: {e}")

@app.route('/tv_alert', methods=['POST'])
def receive_webhook():
    try:
        data = json.loads(request.data.decode('utf-8'))
        place_order(data.get('signal'), data.get('ticker'), data.get('amount'), data.get('tp'), source=data.get('source', '📺 TV'), sl_input=data.get('sl'))
        return "OK", 200
    except: return "Error", 500

def keep_alive():
    while True: time.sleep(60)

if __name__ == '__main__':
    init_db()
    threading.Thread(target=keep_alive, daemon=True).start()
    app.run(host='127.0.0.1', port=5000)
