import ccxt
import pandas as pd
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings("ignore")

def RSI(array, n):
    series = pd.Series(array)
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/n, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/n, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

class RsiOptimized(Strategy):
    rsi_buy = 30; sl_percent = 0.02; tp_percent = 0.03 
    def init(self): self.rsi = self.I(RSI, self.data.Close, 14)
    def next(self):
        if not self.position and self.rsi < self.rsi_buy:
            self.buy(sl=self.data.Close[-1]*(1-self.sl_percent), tp=self.data.Close[-1]*(1+self.tp_percent))

def run_optimization(symbol):
    try:
        exchange = ccxt.binance()
        if '/' not in symbol: symbol = f"{symbol[:-4]}/{symbol[-4:]}"
        ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=500)
        if not ohlcv: return "❌ Нет данных", None
        df = pd.DataFrame(ohlcv, columns=['Time','Open','High','Low','Close','Volume'])
        df['Time'] = pd.to_datetime(df['Time'], unit='ms'); df.set_index('Time', inplace=True)
        
        bt = Backtest(df, RsiOptimized, cash=10000, commission=.001)
        stats = bt.optimize(rsi_buy=range(20,45,5), sl_percent=[0.02,0.03,0.04], tp_percent=[0.02,0.04,0.06], maximize='Return [%]')
        best = stats['_strategy']
        
        cmd = f"/buy {symbol.replace('/','')} 10% {best.tp_percent*50:.1f}% {best.tp_percent*100:.1f}% sl={best.sl_percent*100:.1f}%"
        return f"💎 RSI<{best.rsi_buy} TP:{best.tp_percent*100}%", cmd
    except Exception as e: return f"Err: {e}", None

def get_best_params(symbol, timeframe='1h'):
    # Упрощенная версия для сканера
    return 30, 0.03 
