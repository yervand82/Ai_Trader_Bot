# --- backtest.py (Fixed Module) ---
import ccxt
import pandas as pd
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import warnings

warnings.filterwarnings("ignore")

# Функция RSI (без зависимостей)
def RSI(array, n):
    series = pd.Series(array)
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/n, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/n, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

class RsiStrat(Strategy):
    upper_bound = 70
    lower_bound = 30
    
    def init(self):
        self.rsi = self.I(RSI, self.data.Close, 14)

    def next(self):
        if crossover(self.lower_bound, self.rsi):
            self.buy(size=0.99)
        elif crossover(self.rsi, self.upper_bound):
            self.position.close()

def run_backtest_engine(symbol, timeframe='15m', limit=1000):
    """Функция для вызова из Telegram"""
    try:
        exchange = ccxt.binance()
        if '/' not in symbol: symbol = f"{symbol[:-4]}/{symbol[-4:]}"
        
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not ohlcv: return "❌ Нет данных с биржи."

        df = pd.DataFrame(ohlcv, columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Time'] = pd.to_datetime(df['Time'], unit='ms')
        df.set_index('Time', inplace=True)

        bt = Backtest(df, RsiStrat, cash=10000, commission=.001)
        stats = bt.run()

        return (
            f"📊 **Результат Бэктеста**\n"
            f"Пара: `{symbol}` ({timeframe})\n"
            f"--------------------------\n"
            f"💰 Доход: `{stats['Return [%]']:.2f}%`\n"
            f"🎯 Винрейт: `{stats['Win Rate [%]']:.2f}%`\n"
            f"🔢 Сделок: `{stats['# Trades']}`\n"
            f"📉 Просадка: `{stats['Max. Drawdown [%]']:.2f}%`"
        )
    except Exception as e:
        return f"❌ Ошибка бэктеста: {e}"
