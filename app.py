import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 및 CSS (오타 수정 완료: unsafe_allow_html)
st.set_page_config(page_title="주요 지수 Monitoring", layout="wide")
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
    .insight-box { background-color: #f0f2f6; padding: 20px; border-radius: 15px; border-left: 5px solid #ff4b4b; margin-bottom: 20px;}
    .guide-card { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e6ed; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); height: 100%;}
    .guide-title { font-weight: bold; color: #1c83e1; font-size: 16px; margin-bottom: 10px;}
    .guide-text { font-size: 14px; color: #5e6d82; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 불러오기 함수
@st.cache_data
def load_data(ticker):
    df = yf.download(ticker, start="2000-01-01")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    for m in [5, 20, 60, 120, 240]:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    # 60일 vs 120일 크로스 신호
    df['G'] = (df['MA60'].shift(1) < df['MA120'].shift(1)) & (df['MA60'] > df['MA120'])
    df['D'] = (df['MA60'].shift(1) > df['MA120'].shift(1)) & (df['MA60'] < df['MA120'])
    return df.dropna(subset=['MA240'])

# --- 사이드바 ---
st.sidebar.title("⚙️ Dashboard 설정")
indices = {
    "NASDAQ": "^IXIC", 
    "NASDAQ 100": "^NDX", 
    "S&P 500": "^GSPC", 
    "KOSPI": "^KS11", 
    "KOSDAQ": "^KQ11"
}
choice = st.sidebar.radio("모니터링할 지수", list(indices.keys()))
t_code = indices[choice]

st.sidebar.markdown("---")
ma_options = {5: "5일선", 20: "20일선", 60: "60일선", 120: "120일선", 240: "240일선"}
selected_ma_day = st.sidebar.selectbox("분석 기준 이평선 선택", list(ma_options.keys()), index=4)

data = load_data(t_code)
last = data.iloc[-1]
curr = float(last['Close'])

# --- 최상단: AI 투자 Insight ---
st.title(f"📊 주요 지수 Monitoring ({choice})")

st.markdown('<div class="insight-box">', unsafe_allow_html=True)
st.subheader("💡 실시간 종합 투자 Insight")

is_bull = (last['MA5'] > last['MA20'] > last['MA60'] > last['MA120'] > last['MA240'])
is_bear = (last['MA5'] < last['MA20'] < last['MA60'] < last['MA120'] < last['MA240'])
gap_val = max(last['MA5'], last['MA20'], last['MA60']) / min(last['MA5'], last['MA20'], last['MA60'])

t_msg = "🚀 **정배열(상승)** 상태입니다. 눌림목 매수 전략이 유리합니다." if is_bull else \
        ("📉 **역배열(하락)** 상태입니다. 보수적 관망이 필요합니다." if is_bear else "🔄 **혼조세**입니다. 방향성 확인이 필요합니다.")
e_msg = "🧨 **에너지 수렴** 중입니다. 조만간 큰 변동성이 예상됩니다." if gap_val < 1.04 else "🌊 **추세 확산** 중입니다. 현재 방향이 강화되고 있습니다."

st.markdown(f"- **추세:** {t_msg}")
st.markdown(f"- **에너지:** {e_msg}")
st.markdown(f"**결론:** 현재 {choice} 지수는 {t_msg.split(' 상태')[0]} 흐름 속에서 {e_msg.split(' 중')[0]} 상황입니다. 가이드 원칙에 따라 신중히 대응하세요.")
st.markdown('</div>', unsafe_allow_html=True)

# --- 중단: 수익률 및 동적 지표 함수 ---
def show_metrics(df_subset, period_name):
    st.subheader(f"📝 {period_name} 기준 지표 분석")
    s_p = float(df_subset['Close'].iloc[0])
    e_p = float(df_subset['Close'].iloc[-1])
    ret = ((e_p - s_p) / s_p) * 100
    days = (df_subset.index[-1] - df_subset.index[0]).days
    cagr = (((e_p / s_p) ** (365 / days)) - 1) * 100 if days > 0 else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric(f"{period_name} 수익률", f"{ret:.2f}%")
    c2.metric("연평균 수익률(CAGR)", f"{cagr:.2f}%")
    
    ma_val = float(last[f'MA{selected_ma_day}'])
    disp = (curr / ma_val) * 100
    th = 15 if selected_ma_day >= 120 else 5
    avg_msg = "🔴 하락 예상 (평균회귀)" if disp > (100+th) else ("🟢 상승 예상 (평균회귀)" if disp < (100-th) else "⚪ 안정 유지")
    c3.metric(f"{selected_ma_day}일 이격률", f"{disp:.1f}%", avg_msg)

# --- 차트 영역 ---
tabs = st.tabs(["3개월", "6개월", "1년", "3년", "전체"])

def make_chart(df_in, p_name):
    show_metrics(df_in, p_name)
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_in.index, open=df_in['Open'], high=df_in['High'], low=df_in['Low'], close=df_in['Close'], name="Price", opacity=0.5))
    clrs = {5:'red', 20:'orange', 60:'green', 120:'blue', 240:'black'}
    for d, c in clrs.items():
        w = 2.5 if d == selected_ma_day else 1.2
        fig.add_trace(go.Scatter(x=df_in.index, y=df_in[f'MA{d}'], name=f'{d}일선', line=dict(color=c, width=w)))
    
    # 크로스 마커
    gs, ds = df_in[df_in['G']], df_in[df_in['D']]
    fig.add_trace(go.Scatter(x=gs.index, y=gs['MA60'], mode='markers', marker=dict(symbol='triangle-up', size=12, color='red'), name='Golden(60/120)'))
    fig.add_trace(go.Scatter(x=ds.index, y=ds['MA60'], mode='markers', marker=dict(symbol='triangle-down', size=12, color='blue'), name='Death(60/120)'))
    
    fig.update_layout(height=550, template="plotly_white", xaxis_rangeslider_visible=False, dragmode='pan', margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

with tabs[0]: make_chart(data.iloc[-60:], "3개월")
with tabs[1]: make_chart(data.iloc[-120:], "6개월")
with tabs[2]: make_chart(data.iloc[-250:], "1년")
with tabs[3]: make_chart(data.iloc[-750:], "3년")
with tabs[4]: make_chart(data, "전체")

# --- 최하단: 투자 가이드북 ---
st.markdown("---")
st.subheader("📖 자산제곱 AI 투자 가이드북")
g1, g2, g3, g4 = st.columns(4)
with g1:
    st.markdown('<div class="guide-card"><div class="guide-title">1. 평균 회귀</div><div class="guide-text">주가는 이평선에서 멀어지면 결국 돌아옵니다. 이격률이 과하게 높으면 하락을, 낮으면 상승을 준비하세요.</div></div>', unsafe_allow_html=True)
with g2:
    st.markdown('<div class="guide-card"><div class="guide-title">2. 정배열/역배열</div><div class="guide-text">정배열은 상승 추세로 눌림목 매수, 역배열은 하락 추세로 주가 상승 시 매도/관망 타이밍입니다.</div></div>', unsafe_allow_html=True)
with g3:
    st.markdown('<div class="guide-card"><div class="guide-title">3. 에너지 수렴</div><div class="guide-text">이평선들이 한곳에 모이면 에너지가 응축된 것입니다. 곧 강력한 변동성이 터질 징조입니다.</div></div>', unsafe_allow_html=True)
with g4:
    st.markdown('<div class="guide-card"><div class="guide-title">4. 역발상 크로스</div><div class="guide-text">골든/데드크로스는 추세 변화 신호지만, 이미 가격에 선반영된 경우가 많아 반대로 대응하는 역발상이 필요할 수 있습니다.</div></div>', unsafe_allow_html=True)
