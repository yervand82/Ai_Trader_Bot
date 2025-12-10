# --- control_bot.py (v35.0 - FULL FIXED CODE) ---
import logging
import requests
import json
import os
import ccxt
import sqlite3
import asyncio
import pandas as pd
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

# Импорт модулей
try: from backtest import run_backtest_engine
except ImportError: run_backtest_engine = None
try: from optimizer import run_optimization
except ImportError: run_optimization = None

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
YOUR_TELEGRAM_ID = int(os.getenv('YOUR_TELEGRAM_ID'))
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
WEBHOOK_URL = "http://localhost:5000/tv_alert"
DB_FILE = "trades.db"
TRAILING_PERCENT = 0.02 

try:
    exchange = ccxt.binance({'apiKey': API_KEY, 'secret': API_SECRET, 'options': {'defaultType': 'spot'}})
    exchange.set_sandbox_mode(True) # REAL MODE
except: exchange = None

logging.basicConfig(filename='control_bot.log', level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

MENU_KEYBOARD = [
    ["🌐 Создать Грид", "🗑 Удалить Грид"], 
    ["💰 Баланс", "📦 Портфолио"], 
    ["📚 История", "👀 Сканер"], 
    ["🔗 Инфо", "ℹ️ Помощь"], 
    ["🔥 PANIC SELL"]
]
MENU_MARKUP = ReplyKeyboardMarkup(MENU_KEYBOARD, resize_keyboard=True)

# --- ХЕЛПЕРЫ ---
def get_ngrok_url():
    try: return requests.get("http://localhost:4040/api/tunnels", timeout=2).json()['tunnels'][0]['public_url']
    except: return None

def security_check(func):
    async def wrapper(u, c, *a, **k):
        if u.effective_user.id != YOUR_TELEGRAM_ID: return
        return await func(u, c, *a, **k)
    return wrapper

def db_execute(q, args=()):
    try:
        conn = sqlite3.connect(DB_FILE); c = conn.cursor(); c.execute(q, args); conn.commit(); conn.close(); return True
    except: return False

def db_get_pairs():
    try: conn = sqlite3.connect(DB_FILE); c = conn.cursor(); c.execute("SELECT ticker FROM watchlist"); rows = c.fetchall(); conn.close(); return [r[0] for r in rows]
    except: return []

def db_add_pair(ticker):
    conn = sqlite3.connect(DB_FILE); c = conn.cursor(); c.execute('CREATE TABLE IF NOT EXISTS watchlist (ticker TEXT PRIMARY KEY)')
    try: c.execute('INSERT INTO watchlist (ticker) VALUES (?)', (ticker.upper(),)); conn.commit(); conn.close(); return True
    except: conn.close(); return False

def db_del_pair(ticker):
    conn = sqlite3.connect(DB_FILE); c = conn.cursor(); c.execute('DELETE FROM watchlist WHERE ticker = ?', (ticker.upper(),)); conn.commit(); conn.close()

def calculate_rsi_simple(ohlcv, period=14):
    try:
        if not ohlcv or len(ohlcv) < period: return 0
        df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'close', 'v'])
        delta = df['close'].diff(); gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean(); loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
        rs = gain / loss; return (100 - (100 / (1 + rs))).iloc[-1]
    except: return 0

# --- КОМАНДЫ ---
@security_check
async def start_command(u, c): await u.message.reply_text("🤖 **Пульт v35.0**", reply_markup=MENU_MARKUP, parse_mode='Markdown')

@security_check
async def help_command(u, c):
    msg = (
        "📚 **СПРАВКА:**\n"
        "🟢 `/buy BTCUSDT 0.01 1% 3%`\n"
        "⚙️ `/setsl BTCUSDT 5` (Стоп 5%)\n"
        "⚙️ `/settp BTCUSDT 1% 5%` (Тейки)\n"
        "🛡 `/budget 500`\n"
        "🧬 `/opt SOL/USDT`\n"
        "👀 `/add ETH/USDT`"
    )
    await u.message.reply_text(msg, parse_mode='Markdown', reply_markup=MENU_MARKUP)

@security_check
async def info_command(u, c):
    url = get_ngrok_url()
    await u.message.reply_text(f"🌐 `{url}/tv_alert`" if url else "⚠️ Ngrok выкл.", parse_mode='Markdown', reply_markup=MENU_MARKUP)

@security_check
async def balance_command(u, c):
    try: 
        bal = exchange.fetch_balance(); nz = {k: v for k, v in bal['total'].items() if v > 0.0001}
        msg = "💰 <b>Баланс:</b>\n<pre>" + "\n".join([f"{k:<6}: {v}" for k,v in sorted(nz.items())[:20]]) + "</pre>"
        await u.message.reply_text(msg, parse_mode='HTML', reply_markup=MENU_MARKUP)
    except: await u.message.reply_text("Err", reply_markup=MENU_MARKUP)

@security_check
async def portfolio_command(u, c):
    try:
        conn = sqlite3.connect(DB_FILE); cur = conn.cursor()
        cur.execute("SELECT ticker, amount, price, highest_price, sl_percent, tp_config FROM trades WHERE status='OPEN'")
        rows = cur.fetchall(); conn.close()
        if not rows: return await u.message.reply_text("📦 Пусто.", reply_markup=MENU_MARKUP)
        msg = "📦 <b>Позиции:</b>\n\n"
        for r in rows:
            sl_pct = r[4] if r[4] else 0.02
            stop = r[3] * (1 - sl_pct)
            tp_info = "Нет"
            if r[5]:
                try: tps = json.loads(r[5]); pend = [f"{s['pct_name']}%" for s in tps if not s['done']]; tp_info = ", ".join(pend) if pend else 'Все!'
                except: pass
            msg += f"🔹 <b>{r[0]}</b> ({r[1]:.4f})\n   📥 ${r[2]:.4f}\n   🛡 Стоп ({sl_pct*100:.1f}%): ${stop:.4f}\n   🎯 {tp_info}\n\n"
        await u.message.reply_text(msg, parse_mode='HTML', reply_markup=MENU_MARKUP)
    except Exception as e: await u.message.reply_text(f"❌ {e}")

@security_check
async def history_command(u, c):
    try:
        conn = sqlite3.connect(DB_FILE); cur = conn.cursor()
        cur.execute("SELECT ticker, amount, price, sell_price, net_pnl, source, commission, timestamp, exit_time FROM trades WHERE status='CLOSED' ORDER BY id DESC LIMIT 10")
        rows = cur.fetchall(); cur.execute("SELECT SUM(net_pnl) FROM trades WHERE status='CLOSED'"); total = cur.fetchone()[0] or 0.0; conn.close()
        if not rows: return await u.message.reply_text("📚 Пусто.", reply_markup=MENU_MARKUP)
        msg = f"📚 <b>История (Net: ${total:.2f}):</b>\n━━━━━━━━━━\n"
        for r in rows:
            pnl = r[4] or 0.0; icon = "🟢" if pnl > 0 else "🔴"
            src = r[5] if r[5] else "?"
            comm = r[6] if r[6] else 0.0
            t_in = r[7][5:-3] if r[7] else "?"; t_out = r[8][5:-3] if r[8] else "?"
            if "Manual" in src: src="👤"
            elif "TV" in src: src="📺" 
            elif "Grid" in src: src="🕸"
            else: src="👀"
            msg += f"{src} <b>{r[0]}</b> | {t_in}->{t_out}\n   {icon} <b>Net: ${pnl:+.2f}</b> (Fee: -${comm:.2f})\n------------------\n"
        await u.message.reply_text(msg, parse_mode='HTML', reply_markup=MENU_MARKUP)
    except Exception as e: await u.message.reply_text(f"❌ {e}")

@security_check
async def list_scanner_command(update, context):
    pairs = db_get_pairs(); 
    if not pairs: return await update.message.reply_text("👀 Пусто.", reply_markup=MENU_MARKUP)
    msg = await update.message.reply_text("🔄 Сканирую...", parse_mode='Markdown'); res = "👀 **Сканер:**\n<pre>"
    for p in pairs:
        try: rsi = calculate_rsi_simple(exchange.fetch_ohlcv(p, '5m', limit=30)); icon = "🔥" if 0 < rsi < 30 else ""; res += f"{p:<9} | {rsi:.1f} {icon}\n"
        except: res += f"{p:<9} | Err\n"
    res += "</pre>"; await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=res, parse_mode='HTML')

# --- СПЕЦ КОМАНДЫ ---
@security_check
async def panic_command(u, c): await u.message.reply_text("🚨 **ПАНИКА...**"); requests.post(WEBHOOK_URL, json={"signal": "panic", "ticker": "ALL", "amount": 0}, timeout=5)
@security_check
async def optimize_command(u,c):
    if not run_optimization: return await u.message.reply_text("❌ Нет optimizer.py")
    p = u.message.text.replace('\u200b','').split()
    if len(p)<2: return await u.message.reply_text("❌ `/opt BTC/USDT`", parse_mode='Markdown')
    await u.message.reply_text(f"🧬 Анализ...", parse_mode='Markdown')
    report, cmd = await asyncio.to_thread(run_optimization, p[1].upper())
    await u.message.reply_text(report, parse_mode='Markdown')
    if cmd: await u.message.reply_text(f"👇 Нажми:\n`{cmd}`", parse_mode='Markdown')
@security_check
async def test_command(u, c):
    if not run_backtest_engine: return await u.message.reply_text("❌ Нет backtest.py")
    p = u.message.text.replace('\u200b', '').split(); await u.message.reply_text(f"⏳ Тест...", parse_mode='Markdown'); await u.message.reply_text(run_backtest_engine(p[1].upper(), p[2] if len(p)>2 else '15m'), parse_mode='Markdown')

# --- НАСТРОЙКИ (SL/TP/BUDGET) ---
@security_check
async def setsl_command(u, c):
    p = u.message.text.replace('\u200b','').split()
    if len(p)<3: return await u.message.reply_text("❌ `/setsl BTCUSDT 5`")
    try: sl=float(p[2].replace('%',''))/100; db_execute("UPDATE trades SET sl_percent=? WHERE ticker=? AND status='OPEN'", (sl, p[1].upper())); await u.message.reply_text("✅ OK")
    except: await u.message.reply_text("❌ Err")
@security_check
async def settp_command(u, c):
    p = u.message.text.replace('\u200b','').split()
    if len(p)<3: return await u.message.reply_text("❌ `/settp BTCUSDT 1% 5%`")
    try:
        conn=sqlite3.connect(DB_FILE); cur=conn.cursor(); cur.execute("SELECT price, amount FROM trades WHERE status='OPEN' AND ticker=?",(p[1].upper(),)); row=cur.fetchone(); conn.close()
        if not row: return await u.message.reply_text("❌ Нет сделки")
        pcts = [float(x.replace('%','')) for x in p[2:]]
        steps = [{"price": row[0]*(1+pc/100), "amount": row[1]/len(pcts), "pct_name": pc, "done": False} for pc in pcts]
        db_execute("UPDATE trades SET tp_config=? WHERE ticker=? AND status='OPEN'", (json.dumps(steps), p[1].upper())); await u.message.reply_text("✅ OK")
    except Exception as e: await u.message.reply_text(f"❌ {e}")
@security_check
async def budget_command(u, c):
    p=u.message.text.replace('\u200b','').split(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor(); cur.execute('CREATE TABLE IF NOT EXISTS bot_settings (key TEXT PRIMARY KEY, value TEXT)')
    if len(p)<2: cur.execute("SELECT value FROM bot_settings WHERE key='max_budget'"); r=cur.fetchone(); msg=f"💰 Лимит: ${r[0]}" if r else "💰 Безлимит"
    elif p[1]=='off': cur.execute("DELETE FROM bot_settings WHERE key='max_budget'"); msg="✅ Удален"
    else: cur.execute("REPLACE INTO bot_settings VALUES (?, ?)", ('max_budget', p[1])); msg=f"✅ Лимит ${p[1]}"
    conn.commit(); conn.close(); await u.message.reply_text(msg, parse_mode='Markdown')
@security_check
async def range_command(u, c):
    p=u.message.text.replace('\u200b','').split(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor(); cur.execute('CREATE TABLE IF NOT EXISTS trade_limits (ticker TEXT PRIMARY KEY, min_price REAL, max_price REAL)')
    if len(p)<3: msg="❌ `/range BTC 90000 100000`"
    elif p[2]=='off': cur.execute("DELETE FROM trade_limits WHERE ticker=?",(p[1].upper(),)); msg="✅ Выкл"
    else: cur.execute("REPLACE INTO trade_limits VALUES (?, ?, ?)", (p[1].upper(), float(p[2]), float(p[3]))); msg="✅ Задан"
    conn.commit(); conn.close(); await u.message.reply_text(msg, parse_mode='Markdown')
@security_check
async def add_pair_command(u,c): p=u.message.text.replace('\u200b','').split(); (db_add_pair(p[1].upper()) if len(p)>1 else None); await u.message.reply_text("✅ OK", reply_markup=MENU_MARKUP)
@security_check
async def del_pair_command(u,c): p=u.message.text.replace('\u200b','').split(); (db_del_pair(p[1].upper()) if len(p)>1 else None); await u.message.reply_text("🗑 OK", reply_markup=MENU_MARKUP)

# --- ОБРАБОТЧИК СООБЩЕНИЙ ---
@security_check
async def handle_message(update, context):
    if not update.message: return
    text = update.message.text.replace('\u200b', '').strip()

    # Кнопки
    if text == "💰 Баланс": await balance_command(update, context)
    elif text == "📦 Портфолио": await portfolio_command(update, context)
    elif text == "📚 История": await history_command(update, context)
    elif text == "🔗 Инфо": await info_command(update, context)
    elif text == "🔥 PANIC SELL": await panic_command(update, context)
    elif text == "👀 Сканер": await list_scanner_command(update, context)
    elif text == "ℹ️ Помощь": await help_command(update, context)
    elif text in ["🌐 Создать Грид", "🗑 Удалить Грид"]: await update.message.reply_text("Грид отключен.", reply_markup=MENU_MARKUP)

    # Команды
    elif text.startswith('/start'): await start_command(update, context)
    elif text.startswith('/opt'): await optimize_command(update, context)
    elif text.startswith('/test'): await test_command(update, context)
    elif text.startswith('/budget'): await budget_command(update, context)
    elif text.startswith('/range'): await range_command(update, context)
    elif text.startswith('/add'): await add_pair_command(update, context)
    elif text.startswith('/del'): await del_pair_command(update, context)
    elif text.startswith('/list'): await list_scanner_command(update, context)
    elif text.startswith('/setsl'): await setsl_command(update, context) # <-- ВЕРНУЛИ
    elif text.startswith('/settp'): await settp_command(update, context) # <-- ВЕРНУЛИ

    # Торговля
    elif text.startswith('/buy') or text.startswith('/sell'):
        parts = text.split()
        if len(parts) < 3: return await update.message.reply_text("❌ Формат.")
        signal = parts[0][1:]; ticker = parts[1].upper(); amount = parts[2]
        
        tp_parts = []
        sl_val = None
        for p in parts[3:]:
            if p.lower().startswith('sl='): sl_val = p.split('=')[1]
            else: tp_parts.append(p)
        tp_str = " ".join(tp_parts) if tp_parts else None

        try: requests.post(WEBHOOK_URL, json={"signal": signal, "ticker": ticker, "amount": amount, "tp": tp_str, "sl": sl_val, "source": "👤 Manual"}, timeout=2); await update.message.reply_text("📡 OK")
        except: await update.message.reply_text("Err App")
    
    else: await update.message.reply_text("Меню.", reply_markup=MENU_MARKUP)

if __name__ == "__main__":
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.run_polling()
