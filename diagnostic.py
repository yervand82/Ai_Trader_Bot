import ccxt
import os
from dotenv import load_dotenv

# 1. Загружаем настройки
load_dotenv()
api_key = os.getenv('API_KEY')
api_secret = os.getenv('API_SECRET')

print(f"🔑 API Key: {'ЕСТЬ' if api_key else 'НЕТ (Проверьте .env!)'}")
print(f"🔑 Secret:  {'ЕСТЬ' if api_secret else 'НЕТ (Проверьте .env!)'}")

# 2. Пробуем подключиться
try:
    print("\n⏳ Подключаюсь к Binance (Real)...")
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'options': {'defaultType': 'spot'}
    })
    # exchange.set_sandbox_mode(True) # Если нужен тестнет - раскомментируйте

    # 3. Запрашиваем баланс
    balance = exchange.fetch_balance()
    print("✅ УСПЕХ! Связь есть.")
    print(f"💰 USDT Доступно: {balance['free'].get('USDT', 0)}")

except Exception as e:
    print("\n❌ ОШИБКА:")
    print(e)
