import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="주요 지수 Monitoring", layout="wide")
st.markdown("""
    <style>
    .verdict-box { padding: 25px; border-radius: 15px; text-align: center; margin-bottom: 25px; color: white; font-weight: bold; font-size: 32px; }
    .positive { background-color: #ff4b4b; } /* 상승/긍정: 빨강 */
    .neutral { background-color: #ffa500; } /* 중립: 주황 */
    .negative { background-color: #1c83e1; } /* 하락/부정: 파랑 */
    .insight-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #333; height: 100%; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 수집 및 지표 계산 함수
@st.cache_data
def load_full_data(ticker):
    df = yf.download(ticker, start="2000-01-01")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 이평선
    for m in [5, 20, 60, 120, 240]:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    
    # RSI (상대강도지수) 계산
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD 계산
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    return df.dropna(subset=['MA240'])

# --- 사이드바 ---
st.sidebar.title("🧭 모니터링 설정")
indices = {"NASDAQ": "^IXIC", "NASDAQ 100": "^NDX", "S&P 500": "^GSPC", "KOSPI": "^KS11", "KOSDAQ": "^KQ11"}
choice = st.sidebar.radio("지수 선택", list(indices.keys()))
data = load_full_data(indices[choice])

# --- 데이터 분석 로직 ---
last = data.iloc[-1]
curr = float(last['Close'])
ma60, ma120 = float(last['MA60']), float(last['MA120'])
rsi = float(last['RSI'])
macd = float(last['MACD'])
signal = float(last['Signal_Line'])

# [요청 1] 60일/120일 기준 정배열/역배열
is_60_120_bull = ma60 > ma120
arrangement = "정배열(상승)" if is_60_120_bull else "역배열(하락)"

# [요청 2] 에너지 수렴/발산
energy_gap = abs(ma60 - ma120) / ma120 * 100
energy_status = "수렴(에너지 응축)" if energy_gap < 3 else "발산(추세 진행)"

# [요청 3] 이격률
disp_60 = (curr / ma60) * 100
disp_120 = (curr / ma120) * 100

# [추가] 투자 의사결정 스코어링 로직
score = 0
if is_60_120_bull: score += 2  # 추세가 살아있음
else: score -= 2
if rsi < 30: score += 2        # 과매도 (기회)
elif rsi > 70: score -= 2      # 과열 (위험)
if macd > signal: score += 1   # 추세 관성 상승
else: score -= 1
if disp_120 < 95: score += 1   # 역사적 저평가

# 최종 결과값 도출
if score >= 2:
    verdict, v_class = "긍정 (BUY / HOLD)", "positive"
elif score <= -2:
    verdict, v_class = "부정 (SELL / WAIT)", "negative"
else:
    verdict, v_class = "중립 (NEUTRAL)", "neutral"

# --- 메인 화면: 최상단 최종 결과 ---
st.title(f"📊 {choice} Monitoring & Decision")
st.markdown(f'<div class="verdict-box {v_class}">오늘의 투자 의견: {verdict}</div>', unsafe_allow_html=True)

# --- 중단: 60/120 집중 인사이트 ---
st.subheader("🔍 60일 & 120일 이평선 핵심 진단")
c1, c2, c3 = st.columns(3)
with c1:
    st.write("📊 **배열 상태**")
    st.write(f"현재: **{arrangement}**")
    st.caption("60일선이 120일선 위에 있으면 정배열(상승)입니다.")
with c2:
    st.write("🧨 **에너지 상태**")
    st.write(f"현재: **{energy_status}**")
    st.caption("두 선의 간격이 좁을수록 큰 변동성이 임박했음을 뜻합니다.")
with c3:
    st.write("🏠 **이격률 (120일선 기준)**")
    st.write(f"수치: **{disp_120:.1f}%**")
    st.caption("100%보다 너무 높으면 고점, 너무 낮으면 저점입니다.")

# --- 중단: 보조 지표 및 인사이트 ---
st.markdown("---")
st.subheader("💡 투자 의사결정을 위한 추가 지표")
i1, i2, i3 = st.columns(3)
with i1:
    st.markdown(f'<div class="insight-card"><b>🔥 RSI (심리 과열도)</b><br><br>현재 수치: {rsi:.1f}<br><br>'
                f'{"⚠️ 과열 구간입니다. 매수 자제." if rsi > 70 else ("💎 바닥 구간입니다. 매수 검토." if rsi < 30 else "✅ 심리가 안정적입니다.")}'
                f'</div>', unsafe_allow_html=True)
with i2:
    st.markdown(f'<div class="insight-card"><b>📈 MACD (추세 에너지)</b><br><br>방향: {"상승 관성" if macd > signal else "하락 관성"}<br><br>'
                f'MACD가 시그널 선 위에 있으면 상승하려는 힘이 더 강함을 의미합니다.</div>', unsafe_allow_html=True)
with i3:
    # 52주 최고/최저 대비 위치
    high_52 = data['High'].iloc[-250:].max()
    pos_52 = (curr / high_52) * 100
    st.markdown(f'<div class="insight-card"><b>🏆 52주 최고점 대비 위치</b><br><br>현재 위치: {pos_52:.1f}%<br><br>'
                f'고점 대비 {100-pos_52:.1f}% 하락한 상태입니다. 역사적 고점 대비 부담을 체크하세요.</div>', unsafe_allow_html=True)

# --- 차트 영역 ---
st.markdown("---")
tab1, tab2 = st.tabs(["주가 차트 분석", "장기 추세 & 예측"])

def draw_main_chart(df_plot):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name="Price", opacity=0.4))
    # 60일, 120일 강조
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MA60'], name='60일선', line=dict(color='green', width=2)))
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MA120'], name='120일선', line=dict(color='blue', width=2)))
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MA240'], name='240일선(경기)', line=dict(color='black', width=1, dash='dot')))
    
    fig.update_layout(height=600, template="plotly_white", xaxis_rangeslider_visible=False, dragmode='pan')
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

with tab1:
    period = st.radio("기간 선택", ["3개월", "6개월", "1년", "3년"], horizontal=True)
    days = {"3개월":60, "6개월":125, "1년":250, "3년":750}
    draw_main_chart(data.iloc[-days[period]:])

with tab2:
    # 10년 예측선 포함
    last_d, last_v = data.index[-1], float(last['MA240'])
    slope = (data['MA240'].iloc[-1] - data['MA240'].iloc[-500]) / 500
    f_dates = [last_d + timedelta(days=i) for i in range(1, 3650)]
    f_prices = [last_v + (slope * i) for i in range(1, 3650)]
    
    fig_long = go.Figure()
    fig_long.add_trace(go.Scatter(x=data.index, y=data['Close'], name="과거 지수", line=dict(color='lightgray')))
    fig_long.add_trace(go.Scatter(x=f_dates, y=f_prices, name="향후 10년 추세 예측", line=dict(color='red', dash='dash')))
    fig_long.update_layout(height=500, template="plotly_white")
    st.plotly_chart(fig_long, use_container_width=True)

# --- 최하단: 투자 가이드북 ---
st.markdown("---")
st.subheader("📖 자산제곱 AI 투자 가이드북")
g1, g2, g3 = st.columns(3)
with g1:
    st.info("**1. 60/120 골든크로스의 역발상:** 60일선이 120일선을 뚫는 골든크로스는 강력한 매수 신호지만, 이미 선반영된 경우 단기 고점일 수 있으니 이격률을 반드시 체크하세요.")
with g2:
    st.info("**2. 에너지 수렴의 폭발력:** 60일선과 120일선이 만나는 수렴 구간 이후에는 위든 아래든 거대한 파동이 옵니다. 이때 RSI가 낮다면 상방 폭발 가능성이 큽니다.")
with g3:
    st.info("**3. 120일선 이격률의 의미:** 120일선(반기 평균)에서 주가가 15% 이상 멀어지면, 시장은 '과하다'고 판단하고 다시 평균으로 돌아오려는 회귀 본능이 작동합니다.")
