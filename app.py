import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 및 프리미엄 스타일
st.set_page_config(page_title="EXECUTIVE MARKET REPORT", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #fcfcfc; font-family: 'Inter', sans-serif; }
    .verdict-box { padding: 30px; border-radius: 20px; margin-bottom: 30px; border: 1px solid #eee; }
    .positive-v { background: linear-gradient(135deg, #fff5f5 0%, #ffffff 100%); border-left: 10px solid #ff6b6b; color: #e03131; }
    .neutral-v { background: linear-gradient(135deg, #fff9db 0%, #ffffff 100%); border-left: 10px solid #fab005; color: #f08c00; }
    .negative-v { background: linear-gradient(135deg, #e7f5ff 0%, #ffffff 100%); border-left: 10px solid #228be6; color: #1971c2; }
    .v-content { font-size: 32px; font-weight: 800; letter-spacing: -1px; }
    .macro-appendix { background-color: #f8f9fa; padding: 40px; border-radius: 20px; margin-top: 50px; border: 1px solid #e9ecef; }
    .appendix-title { color: #495057; font-weight: 700; font-size: 24px; margin-bottom: 20px; }
    .info-card { background-color: #fff; padding: 20px; border-radius: 12px; border: 1px solid #eee; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 엔진
@st.cache_data(ttl=3600)
def load_index_data(ticker):
    df = yf.download(ticker, start="2010-01-01")
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    for m in [5, 20, 60, 120, 240]:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    df['G'] = (df['MA60'].shift(1) < df['MA120'].shift(1)) & (df['MA60'] > df['MA120'])
    df['D'] = (df['MA60'].shift(1) > df['MA120'].shift(1)) & (df['MA60'] < df['MA120'])
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    return df.dropna(subset=['MA240'])

@st.cache_data(ttl=3600)
def load_macro_history():
    # 금리(^TNX), 유가(CL=F), 달러(DX-Y.NYB), VIX(^VIX)
    macros = {"Rate": "^TNX", "Oil": "CL=F", "Dollar": "DX-Y.NYB", "VIX": "^VIX"}
    results = {}
    for name, t in macros.items():
        d = yf.download(t, start="2022-01-01")
        if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
        # 월별 평균으로 리샘플링하여 추세 가독성 향상
        results[name] = d['Close'].resample('ME').mean()
    return results

# --- 데이터 준비 ---
st.sidebar.markdown("## 🏛️ MONITORING")
indices = {"NASDAQ": "^IXIC", "NASDAQ 100": "^NDX", "S&P 500": "^GSPC", "KOSPI": "^KS11", "KOSDAQ": "^KQ11"}
choice = st.sidebar.radio("Index", list(indices.keys()))
data = load_index_data(indices[choice])
macro_history = load_macro_history()

# 실시간 분석 값
last = data.iloc[-1]
curr, ma60, ma120, rsi = float(last['Close']), float(last['MA60']), float(last['MA120']), float(last['RSI'])

# --- [PART 1] 지수 분석 및 Investment Verdict (상단) ---
st.title(f"Market Intelligence: {choice}")

# AI Verdict 계산
score = 0
if ma60 > ma120: score += 2
if rsi < 40: score += 2
elif rsi > 60: score -= 2
if score >= 2: verdict, v_class = "긍정 (Buy / Overweight)", "positive-v"
elif score <= -1: verdict, v_class = "부정 (Caution / Underweight)", "negative-v"
else: verdict, v_class = "중립 (Neutral / Watch)", "neutral-v"

st.markdown(f'<div class="verdict-box {v_class}"><div style="font-size:12px; font-weight:700; opacity:0.7;">EXECUTIVE VERDICT</div><div class="v-content">{verdict}</div></div>', unsafe_allow_html=True)

# 주요 기술적 Insight 3종
i1, i2, i3 = st.columns(3)
with i1: st.info(f"**추세:** {'상승 정배열(60>120)' if ma60 > ma120 else '하락 역배열(60<120)'}")
with i2: st.info(f"**이격률:** {(curr/ma120*100):.1f}% (120일선 기준)")
with i3: st.info(f"**RSI:** {rsi:.1f} ({'과열' if rsi > 70 else ('바닥' if rsi < 30 else '안정')})")

# 성과 분석 탭
st.markdown("---")
tabs = st.tabs(["3개월", "6개월", "1년", "3년", "전체"])
def render_index_chart(df_sub, p_name):
    s_p, e_p = float(df_sub['Close'].iloc[0]), float(df_sub['Close'].iloc[-1])
    ret = ((e_p - s_p) / s_p) * 100
    days = (df_sub.index[-1] - df_sub.index[0]).days
    cagr = (((e_p / s_p) ** (365 / (days if days > 0 else 1))) - 1) * 100
    st.markdown(f"**{p_name} 성과:** 수익률 {ret:.2f}% | 연평균 성장률(CAGR) {cagr:.2f}%")
    
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_sub.index, open=df_sub['Open'], high=df_sub['High'], low=df_sub['Low'], close=df_sub['Close'], name="Price", opacity=0.4))
    for d, c in {60:'#2f9e44', 120:'#1971c2', 240:'#495057'}.items():
        fig.add_trace(go.Scatter(x=df_sub.index, y=df_sub[f'MA{d}'], name=f'{d}MA', line=dict(color=c, width=2)))
    fig.update_layout(height=450, template="plotly_white", xaxis_rangeslider_visible=False, dragmode='pan', margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

with tabs[0]: render_index_chart(data.iloc[-60:], "3개월")
with tabs[1]: render_index_chart(data.iloc[-125:], "6개월")
with tabs[2]: render_index_chart(data.iloc[-250:], "1년")
with tabs[3]: render_index_chart(data.iloc[-750:], "3년")
with tabs[4]: render_index_chart(data, "전체")

# --- [PART 2] APPENDIX: Macro Economic Trends (하단) ---
st.markdown('<div class="macro-appendix">', unsafe_allow_html=True)
st.markdown('<div class="appendix-title">📎 Appendix: Macro Economic Trends (Monthly)</div>', unsafe_allow_html=True)

a_col1, a_col2 = st.columns(2)
a_col3, a_col4 = st.columns(2)

def draw_macro_line(series, title, color, unit):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series.index, y=series.values, mode='lines+markers', line=dict(color=color, width=3), name=title))
    fig.update_layout(height=250, title=f"{title} ({unit})", template="plotly_white", margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

with a_col1:
    draw_macro_line(macro_history['Rate'], "US 10Y Yield (금리)", "#e03131", "%")
    st.caption("💡 **Insight:** 금리 상승은 기업의 조달 비용을 높여 특히 기술주(나스닥)에 하락 압력을 줍니다.")
with a_col2:
    draw_macro_line(macro_history['Oil'], "WTI Crude Oil (유가)", "#495057", "$")
    st.caption("💡 **Insight:** 유가 급등은 인플레이션을 유발하여 연준의 금리 인상을 정당화시키는 요인이 됩니다.")
with a_col3:
    draw_macro_line(macro_history['Dollar'], "Dollar Index (달러)", "#1971c2", "pt")
    st.caption("💡 **Insight:** 달러 강세는 신흥국(코스피) 시장에서 외국인 자금이 빠져나가는 원인이 됩니다.")
with a_col4:
    draw_macro_line(macro_history['VIX'], "VIX Index (공포지수)", "#f08c00", "pt")
    st.caption("💡 **Insight:** VIX가 낮게 유지되다 급등할 때는 시장의 패닉 셀링이 시작될 수 있음을 경고합니다.")

st.markdown('</div>', unsafe_allow_html=True)

# --- [PART 3] Investment Guide (최하단) ---
st.markdown("---")
st.subheader("📖 AI 투자 가이드북 (핵심 요약)")
g1, g2, g3 = st.columns(3)
with g1:
    st.markdown("#### 1. 금리-주가 역의 상관관계")
    st.write("금리가 월별 차트에서 계단식으로 상승한다면, 지수 차트가 좋아도 비중을 줄여야 합니다. 돈의 가치가 비싸지면 주식의 매력이 떨어지기 때문입니다.")
with g2:
    st.markdown("#### 2. 에너지 수렴과 변동성")
    st.write("상단 차트에서 60일선과 120일선이 만날 때 하단 VIX 지수가 최저점이라면, 곧 위든 아래든 거대한 폭발이 일어날 징조입니다.")
with g3:
    st.markdown("#### 3. 달러-코스피 연결고리")
    st.write("국내 지수를 볼 때는 달러 인덱스 추이를 반드시 보세요. 달러가 월별 고점을 경신하면 코스피는 전고점을 뚫기 매우 어렵습니다.")
