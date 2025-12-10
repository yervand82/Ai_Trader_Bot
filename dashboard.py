# --- dashboard.py (v2.0 - PRO TERMINAL) ---
import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ccxt
import os
import time
from dotenv import load_dotenv

st.set_page_config(page_title="AI Trade Terminal", layout="wide", page_icon="🚀")

# --- ЗАГРУЗКА ДАННЫХ ---
load_dotenv()
DB_FILE = "trades.db"
exchange = ccxt.binance({'options': {'defaultType': 'spot'}})
exchange.set_sandbox_mode(True) # TESTNET

def get_db_data():
    try:
        conn = sqlite3.connect(DB_FILE)
        open_trades = pd.read_sql("SELECT * FROM trades WHERE status='OPEN'", conn)
        history = pd.read_sql("SELECT * FROM trades WHERE status='CLOSED' ORDER BY id DESC", conn)
        conn.close()
        return open_trades, history
    except: return pd.DataFrame(), pd.DataFrame()

def get_market_data(symbol, timeframe='1h', limit=100):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        return df
    except: return pd.DataFrame()

# --- SIDEBAR (НАСТРОЙКИ) ---
st.sidebar.title("🎛 Управление")
selected_pair = st.sidebar.text_input("Тикер для Графика", "BNB/USDT").upper()
refresh_rate = st.sidebar.slider("Автообновление (сек)", 5, 60, 30)

# --- ГЛАВНАЯ ПАНЕЛЬ ---
st.title("🚀 AI Trading Terminal")

col1, col2, col3, col4 = st.columns(4)
open_df, hist_df = get_db_data()

total_pnl = hist_df['pnl_usd'].sum() if not hist_df.empty else 0
open_count = len(open_df)
last_trade = hist_df.iloc[0]['timestamp'] if not hist_df.empty else "Нет"

col1.metric("💰 Реализованный PnL", f"${total_pnl:.2f}")
col2.metric("📦 Открытые Позиции", f"{open_count}")
col3.metric("🕓 Последняя сделка", f"{str(last_trade)[5:16]}")

# --- ГРАФИК (CANDLESTICK) ---
st.subheader(f"📈 График {selected_pair}")

df_ohlc = get_market_data(selected_pair)
if not df_ohlc.empty:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])

    # 1. Свечи
    fig.add_trace(go.Candlestick(
        x=df_ohlc['time'],
        open=df_ohlc['open'], high=df_ohlc['high'],
        low=df_ohlc['low'], close=df_ohlc['close'],
        name='Price'
    ), row=1, col=1)

    # 2. Накладываем сделки из БД на график
    # Фильтруем сделки только по выбранной паре
    pair_clean = selected_pair.replace('/', '')
    
    # Покупки
    buys = open_df[open_df['ticker'] == pair_clean]
    if not buys.empty:
        # (Упрощение: берем время текущее, так как точное время входа может быть далеко)
        # В идеале нужно хранить timestamp входа в формате unix
        fig.add_trace(go.Scatter(
            x=[df_ohlc['time'].iloc[-1]], 
            y=buys['price'],
            mode='markers',
            marker=dict(symbol='triangle-up', size=15, color='green'),
            name='Open Buy'
        ), row=1, col=1)

    # 3. Рисуем Сетку (если это BNB)
    if "BNB" in selected_pair:
        # Хардкод из grid_bot.py для визуализации (можно вынести в конфиг)
        levels = [600, 610, 620, 630, 640, 650] 
        for l in levels:
            fig.add_hline(y=l, line_width=1, line_dash="dash", line_color="yellow", opacity=0.5)

    # 4. Объем
    fig.add_trace(go.Bar(x=df_ohlc['time'], y=df_ohlc['volume'], name='Volume'), row=2, col=1)

    fig.update_layout(height=600, xaxis_rangeslider_visible=False, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Не удалось загрузить данные графика. Проверьте тикер.")

# --- ТАБЛИЦЫ ---
tab1, tab2, tab3 = st.tabs(["Активные Сделки", "История", "Системные Логи"])

with tab1:
    st.dataframe(open_df, use_container_width=True)

with tab2:
    st.dataframe(hist_df, use_container_width=True)

with tab3:
    st.write("📜 **Последние записи из alerts.log:**")
    try:
        with open("alerts.log", "r") as f:
            lines = f.readlines()[-20:] # Последние 20 строк
            for line in lines:
                st.text(line.strip())
    except:
        st.warning("Лог файл пуст или не найден.")

# Автообновление страницы
time.sleep(refresh_rate)
st.rerun()
