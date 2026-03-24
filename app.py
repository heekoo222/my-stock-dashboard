import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="주요 지수 Monitoring", layout="wide")

# 2. 데이터 불러오기 함수
@st.cache_data
def load_data(ticker):
    df = yf.download(ticker, start="2000-01-01")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 이평선 계산
    for m in [5, 20, 60, 120, 240, 480]:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    
    # 신호 생성
    df['G'] = (df['MA5'].shift(1) < df['MA20'].shift(1)) & (df['MA5'] > df['MA20'])
    df['D'] = (df['MA5'].shift(1) > df['MA20'].shift(1)) & (df['MA5'] < df['MA20'])
    return df.dropna(subset=['MA480'])

# 3. 10년 추세 예측
def get_pred(df):
    last_d = df.index[-1]
    last_v = float(df['MA240'].iloc[-1])
    recent = df['MA240'].iloc[-500:]
    slope = (recent.iloc[-1] - recent.iloc[0]) / len(recent)
    f_dates = [last_d + timedelta(days=i) for i in range(1, 3650)]
    f_prices = [last_v + (slope * i) for i in range(1, 3650)]
    return pd.Series(index=f_dates, data=f_prices)

# --- 사이드바 설정 ---
st.sidebar.title("🧭 지수 선택")
indices = {
    "NASDAQ": "^IXIC",
    "S&P 500": "^GSPC",
    "KOSPI": "^KS11",
    "KOSDAQ": "^KQ11"
}
choice = st.sidebar.radio("모니터링할 지수", list(indices.keys()))
t_code = indices[choice]

data = load_data(t_code)
pred = get_pred(data)
last = data.iloc[-1]
curr = float(last['Close'])
ma20 = float(last['MA20'])
disp = (curr / ma20) * 100

# --- 상단 리포트 ---
st.title(f"📊 주요 지수 Monitoring ({choice})")

c1, c2, c3, c4 = st.columns(4)
is_up = (last['MA5'] > last['MA20'] > last['MA60'] > last['MA120'])
is_down = (last['MA5'] < last['MA20'] < last['MA60'] < last['MA120'])
gap = max(last['MA5'], last['MA20'], last['MA60']) / min(last['MA5'], last['MA20'], last['MA60'])

with c1: st.metric("현재가", f"{curr:,.2f}")
with c2: st.metric("추세", "🚀 상승장" if is_up else ("📉 하락장" if is_down else "🔄 조정중"))
with c3: st.metric("에너지", "🧨 수렴(응축)" if gap < 1.04 else "🌊 발산(확산)")
with c4: st.metric("이격도", f"{disp:.1f}%")

st.markdown("---")

# 자산제곱 인사이트 박스
if last['G'] and disp > 105:
    st.error("🚨 **역발상 신호:** 골든크로스지만 과열입니다! 고점 매수를 주의하세요.")
elif last['D'] and disp < 95:
    st.success("💎 **역발상 신호:** 데드크로스지만 공포 구간입니다! 저가 매수를 검토하세요.")
else:
    st.info("💡 현재는 안정적인 흐름을 유지하고 있습니다.")

# --- 차트 탭 ---
tabs = st.tabs(["전체 & 10년 예측", "3년", "1년", "6개월", "3개월"])

def make_chart(df_in, show_p=False):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_in.index, open=df_in['Open'], high=df_in['High'], low=df_in['Low'], close=df_in['Close'], name="Price", opacity=0.5))
    clrs = {5:'red', 20:'orange', 240:'purple', 480:'black'}
    for d, c in clrs.items():
        fig.add_trace(go.Scatter(x=df_in.index, y=df_in[f'MA{d}'], name=f'{d}일선', line=dict(color=c, width=1.3)))
    if show_p:
        fig.add_trace(go.Scatter(x=pred.index, y=pred.values, name="10년 예측", line=dict(color='gray', dash='dash')))
    
    gs = df_in[df_in['G']]
    ds = df_in[df_in['D']]
    fig.add_trace(go.Scatter(x=gs.index, y=gs['MA5'], mode='markers', marker=dict(symbol='triangle-up', size=10, color='red'), name='Buy'))
    fig.add_trace(go.Scatter(x=ds.index, y=ds['MA5'], mode='markers', marker=dict(symbol='triangle-down', size=10, color='blue'), name='Sell'))
    
    fig.update_layout(height=600, template="plotly_white", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

with tabs[0]: make_chart(data, True)
with tabs[1]: make_chart(data.iloc[-750:])
with tabs[2]: make_chart(data.iloc[-250:])
with tabs[3]: make_chart(data.iloc[-125:])
with tabs[4]: make_chart(data.iloc[-60:])
