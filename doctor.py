import sqlite3
import os

DB_FILE = "trades.db"

print(f"🏥 Диагностика базы {DB_FILE}...")

if not os.path.exists(DB_FILE):
    print("❌ Файл базы данных не найден!")
    exit()

conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# 1. Проверка колонок
print("🔍 Проверяю структуру...")
try:
    c.execute("SELECT sl_percent FROM trades LIMIT 1")
except sqlite3.OperationalError:
    print("⚠️ Колонка sl_percent отсутствует. Добавляю...")
    try:
        c.execute("ALTER TABLE trades ADD COLUMN sl_percent REAL DEFAULT 0.02")
        conn.commit()
        print("✅ Колонка добавлена успешно.")
    except Exception as e:
        print(f"❌ Не удалось добавить колонку: {e}")

try:
    c.execute("SELECT exit_time FROM trades LIMIT 1")
except sqlite3.OperationalError:
    print("⚠️ Колонка exit_time отсутствует. Добавляю...")
    try:
        c.execute("ALTER TABLE trades ADD COLUMN exit_time TEXT")
        conn.commit()
        print("✅ Колонка добавлена успешно.")
    except Exception as e:
        print(f"❌ Не удалось добавить: {e}")

# 2. Проверка открытых сделок
print("\n🔍 Поиск открытых сделок...")
c.execute("SELECT id, ticker, amount, price, sl_percent FROM trades WHERE status='OPEN'")
rows = c.fetchall()

if rows:
    print(f"✅ Найдено {len(rows)} активных сделок:")
    for r in rows:
        print(f"   🔹 ID {r[0]} | {r[1]} | Вход: {r[3]} | SL: {r[4]}")
else:
    print("💤 Активных сделок в базе НЕТ (0).")
    print("   (Если в Telegram они есть - значит рассинхрон. Удалите их в TG командой 'PANIC SELL' или вручную)")

conn.close()
