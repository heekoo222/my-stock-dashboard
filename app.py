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
    for m in [5, 20, 60, 120, 240, 480]:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
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

# --- 사이드바 ---
st.sidebar.title("🧭 지수 선택")
indices = {"NASDAQ": "^IXIC", "S&P 500": "^GSPC", "KOSPI": "^KS11", "KOSDAQ": "^KQ11"}
choice = st.sidebar.radio("모니터링할 지수", list(indices.keys()))
t_code = indices[choice]

data = load_data(t_code)
pred = get_pred(data)
last = data.iloc[-1]
curr = float(last['Close'])

# --- 상단 타이틀 ---
st.title(f"📊 주요 지수 Monitoring ({choice})")

# --- [인사이트 추가] 핵심 수익률 및 지표 통계 ---
st.subheader("📝 주요 수익률 및 핵심 지표")
col_ret1, col_ret2, col_ret3, col_ret4 = st.columns(4)

def calc_ret(days):
    if len(data) < days: return 0
    past_price = data['Close'].iloc[-days]
    return ((curr - past_price) / past_price) * 100

with col_ret1: st.metric("3개월 수익률", f"{calc_ret(60):.2f}%")
with col_ret2: st.metric("6개월 수익률", f"{calc_ret(120):.2f}%")
with col_ret3: st.metric("1년 수익률", f"{calc_ret(240):.2f}%")
with col_ret4: st.metric("3년 수익률", f"{calc_ret(720):.2f}%")

# 야후 파이낸스 스타일 핵심 지표
st.markdown("---")
m1, m2, m3 = st.columns(3)
high_52 = data['High'].iloc[-250:].max()
low_52 = data['Low'].iloc[-250:].min()

with m1:
    st.write("🚩 **52주 최고/최저**")
    st.write(f"최고: {high_52:,.2f} / 최저: {low_52:,.2f}")
    st.caption("설명: 지난 1년 동안 지수가 가장 높았던 지점과 낮았던 지점입니다.")
    st.info("Insight: 현재가가 최고점에 가깝다면 과열, 최저점에 가깝다면 바닥권 매수를 검토할 시점입니다.")

with m2:
    volatility = data['Close'].iloc[-20:].std()
    st.write("📉 **20일 변동성**")
    st.write(f"수치: {volatility:.2f}")
    st.caption("설명: 최근 20일 동안 주가가 얼마나 위아래로 크게 움직였는지를 나타냅니다.")
    st.info("Insight: 변동성이 갑자기 커지면 시장에 큰 뉴스가 있거나 추세가 바뀔 전조일 수 있습니다.")

with m3:
    ma_dist = ((curr - last['MA240']) / last['MA240']) * 100
    st.write("🏠 **경기선(240일) 이격**")
    st.write(f"이격도: {ma_dist:.2f}%")
    st.caption("설명: 1년 평균 가격(집)에서 현재 가격이 얼마나 멀리 나와 있는지를 봅니다.")
    st.info("Insight: 집(평균선)에서 너무 멀리 나가면 결국 다시 돌아오려는 성질이 강해집니다.")

# --- 차트 영역 ---
st.markdown("---")
tabs = st.tabs(["전체 & 10년 예측", "3년", "1년", "6개월", "3개월"])

def make_chart(df_in, show_p=False):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_in.index, open=df_in['Open'], high=df_in['High'], low=df_in['Low'], close=df_in['Close'], name="Price", opacity=0.5))
    clrs = {5:'red', 20:'orange', 240:'purple', 480:'black'}
    for d, c in clrs.items():
        fig.add_trace(go.Scatter(x=df_in.index, y=df_in[f'MA{d}'], name=f'{d}일선', line=dict(color=c, width=1.3)))
    if show_p:
        fig.add_trace(go.Scatter(x=pred.index, y=pred.values, name="10년 예측", line=dict(color='gray', dash='dash')))
    
    # 골든/데드크로스 마커
    gs = df_in[df_in['G']]
    ds = df_in[df_in['D']]
    fig.add_trace(go.Scatter(x=gs.index, y=gs['MA5'], mode='markers', marker=dict(symbol='triangle-up', size=10, color='red'), name='Buy'))
    fig.add_trace(go.Scatter(x=ds.index, y=ds['MA5'], mode='markers', marker=dict(symbol='triangle-down', size=10, color='blue'), name='Sell'))
    
    # [차트 컨트롤 개선] 이동은 클릭 후 드래그, 확대는 스크롤
    fig.update_layout(
        height=600, 
        template="plotly_white", 
        xaxis_rangeslider_visible=False,
        dragmode='pan', # 기본 모드를 '이동'으로 설정
        margin=dict(l=10, r=10, t=10, b=10)
    )
    
    # 스크롤 줌 활성화 설정
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

with tabs[0]: make_chart(data, True)
with tabs[1]: make_chart(data.iloc[-750:])
with tabs[2]: make_chart(data.iloc[-250:])
with tabs[3]: make_chart(data.iloc[-125:])
with tabs[4]: make_chart(data.iloc[-60:])
