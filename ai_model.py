# --- ai_model.py (v3.0 - NEURAL NETWORK EDITION) ---
import ccxt
import pandas as pd
import numpy as np
from sklearn.neural_network import MLPClassifier # <--- НЕЙРОСЕТЬ
from sklearn.preprocessing import StandardScaler # <--- МАСШТАБИРОВАНИЕ
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score
import warnings
import pickle 
import os

warnings.filterwarnings("ignore")

# Настройки
SYMBOL = 'BTC/USDT'
TIMEFRAME = '15m'
LIMIT = 2000 

class TradingAI:
    def __init__(self):
        # --- КОНФИГУРАЦИЯ НЕЙРОСЕТИ ---
        # hidden_layer_sizes=(128, 64): Два скрытых слоя нейронов
        # activation='relu': Стандартная функция активации
        # max_iter=1000: Даем ей время подумать
        self.model = MLPClassifier(
            hidden_layer_sizes=(128, 64), 
            activation='relu', 
            solver='adam', 
            max_iter=1000, 
            random_state=42,
            early_stopping=True # Остановиться, если обучение не улучшается
        )
        self.scaler = StandardScaler() # "Нормализатор" данных
        
        self.exchange = ccxt.binance()
        self.model_file = "brain.pkl" # Новый файл для нейромозга
        self.is_trained = False

    def add_indicators(self, df):
        # Те же индикаторы, что и раньше
        df['close_pct'] = df['close'].pct_change()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # EMA Distance
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['dist_ema'] = (df['close'] - df['ema50']) / df['ema50'] * 100
        
        # Volatility
        df['vol_change'] = df['volume'].pct_change()
        
        return df.dropna()

    def fetch_data(self, symbol, limit=1000):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            return df
        except: return pd.DataFrame()

    def prepare_data(self, df, is_training=False):
        df = self.add_indicators(df)
        
        # Цель: Рост > 0.25%
        if is_training:
            future_high = df['high'].shift(-2).rolling(2).max() 
            df['target'] = (future_high > df['close'] * 1.0025).astype(int)
            df = df.dropna()
        
        return df

    def train(self, symbol=SYMBOL):
        print(f"🧠 НЕЙРОСЕТЬ: Обучаюсь на {symbol} (это может занять время)...")
        df = self.fetch_data(symbol, LIMIT)
        if df.empty: print("❌ Ошибка данных"); return 0
        
        df = self.prepare_data(df, is_training=True)
        
        # Проверяем баланс классов (сколько было роста, сколько падения)
        positives = df['target'].sum()
        total = len(df)
        print(f"📊 Данные: {total} свечей. Сигналов роста: {positives} ({positives/total:.1%})")
        
        feature_cols = ['rsi', 'dist_ema', 'vol_change', 'close_pct']
        X = df[feature_cols]
        y = df['target']
        
        # МАСШТАБИРУЕМ ДАННЫЕ (Нейросеть не любит большие числа)
        X_scaled = self.scaler.fit_transform(X)
        
        split = int(len(df) * 0.8)
        X_train, X_test = X_scaled[:split], X_scaled[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]
        
        # Учимся
        self.model.fit(X_train, y_train)
        
        # Проверяем
        preds = self.model.predict(X_test)
        precision = precision_score(y_test, preds, zero_division=0)
        
        print(f"🎓 Обучение завершено!")
        print(f"   Точность (Precision): {precision*100:.1f}%")
        
        # Сохраняем И модель, И скейлер (важно!)
        with open(self.model_file, "wb") as f:
            pickle.dump((self.model, self.scaler), f)
        self.is_trained = True
        return precision

    def predict_live(self, symbol):
        if not os.path.exists(self.model_file): return 0.0
        
        # Загружаем
        if not self.is_trained:
            with open(self.model_file, "rb") as f:
                self.model, self.scaler = pickle.load(f)
            self.is_trained = True
            
        df = self.fetch_data(symbol, limit=100)
        if len(df) < 50: return 0.0
        
        df = self.prepare_data(df, is_training=False)
        
        # Берем последние данные
        feature_cols = ['rsi', 'dist_ema', 'vol_change', 'close_pct']
        last_row = df.iloc[[-1]][feature_cols]
        
        # !!! ВАЖНО: Масштабируем так же, как при обучении !!!
        last_row_scaled = self.scaler.transform(last_row)
        
        # Спрашиваем нейросеть
        probability = self.model.predict_proba(last_row_scaled)[0][1]
        
        return probability

if __name__ == "__main__":
    ai = TradingAI()
    ai.train('BTC/USDT')
    
    coin = 'SOL/USDT'
    print(f"\n🧪 Нейро-тест на {coin}:")
    prob = ai.predict_live(coin)
    print(f"Вероятность роста: {prob*100:.1f}%")
