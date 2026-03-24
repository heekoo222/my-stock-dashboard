import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 및 프리미엄 스타일
st.set_page_config(page_title="EXECUTIVE MARKET INTELLIGENCE", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #fcfcfc; font-family: 'Inter', sans-serif; }
    .verdict-box { padding: 30px; border-radius: 20px; margin-bottom: 30px; border: 1px solid #eee; }
    .positive-v { background: linear-gradient(135deg, #fff5f5 0%, #ffffff 100%); border-left: 10px solid #ff6b6b; color: #e03131; }
    .neutral-v { background: linear-gradient(135deg, #fff9db 0%, #ffffff 100%); border-left: 10px solid #fab005; color: #f08c00; }
    .negative-v { background: linear-gradient(135deg, #e7f5ff 0%, #ffffff 100%); border-left: 10px solid #228be6; color: #1971c2; }
    .v-content { font-size: 32px; font-weight: 800; letter-spacing: -1px; }
    .indicator-desc { background-color: #f8f9fa; padding: 15px; border-radius: 12px; border: 1px solid #eef0f2; margin-top: 10px; font-size: 14px; color: #444; }
    .macro-appendix { background-color: #f1f3f5; padding: 40px; border-radius: 20px; margin-top: 50px; border: 1px solid #dee2e6; }
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
    macros = {"Rate": "^TNX", "Oil": "CL=F", "Dollar": "DX-Y.NYB", "VIX": "^VIX"}
    results = {}
    for name, t in macros.items():
        d = yf.download(t, start="2022-01-01")
        if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
        results[name] = d['Close'].resample('ME').mean()
    return results

# --- 데이터 준비 ---
st.sidebar.markdown("## 🏛️ MARKET INTELLIGENCE")
indices = {"NASDAQ": "^IXIC", "NASDAQ 100": "^NDX", "S&P 500": "^GSPC", "KOSPI": "^KS11", "KOSDAQ": "^KQ11"}
choice = st.sidebar.radio("Index Selection", list(indices.keys()))
data = load_index_data(indices[choice])
macro_history = load_macro_history()

last = data.iloc[-1]
curr, ma60, ma120, rsi = float(last['Close']), float(last['MA60']), float(last['MA120']), float(last['RSI'])
disp_120 = (curr / ma120) * 100

# --- 상단: AI Verdict (보스 보고용 결론) ---
st.title(f"Market Analysis: {choice}")

score = 0
if ma60 > ma120: score += 2
if rsi < 40: score += 2
elif rsi > 65: score -= 2
if score >= 2: verdict, v_class = "긍정 (Buy / Overweight)", "positive-v"
elif score <= -1: verdict, v_class = "부정 (Caution / Underweight)", "negative-v"
else: verdict, v_class = "중립 (Neutral / Watch)", "neutral-v"

st.markdown(f'<div class="verdict-box {v_class}"><div style="font-size:12px; font-weight:700; opacity:0.7;">EXECUTIVE VERDICT</div><div class="v-content">{verdict}</div></div>', unsafe_allow_html=True)

# --- 중단: 지표 심층 설명 및 현재 의미 (초보자 가이드) ---
st.subheader("📚 Indicator Dictionary & Real-time Diagnosis")
col_idx1, col_idx2, col_idx3 = st.columns(3)

with col_idx1:
    st.markdown("#### 1. 지수 추세 (Moving Average)")
    trend_val = "상승 정배열" if ma60 > ma120 else "하락 역배열"
    st.success(f"현재 상태: **{trend_val}**")
    st.markdown(f"""
    <div class="indicator-desc">
    <b>💡 설명:</b> 단기 평균(60일)이 장기 평균(120일)보다 위에 있으면 '정배열'이라 하며, 시장이 힘차게 올라가는 중임을 뜻합니다.<br>
    <b>🎯 현재 의미:</b> {choice} 지수는 현재 {trend_val} 상태로, {'추세가 살아있어 공격적인 투자가 가능합니다.' if ma60 > ma120 else '추세가 꺾여 방어적인 자세가 필요합니다.'}
    </div>
    """, unsafe_allow_html=True)

with col_idx2:
    st.markdown("#### 2. 이격률 (Disparity Ratio)")
    st.warning(f"현재 수치: **{disp_120:.1f}%**")
    st.markdown(f"""
    <div class="indicator-desc">
    <b>💡 설명:</b> 주가가 평균선(120일선)에서 얼마나 떨어져 있는지를 나타내는 '평균 회귀' 지표입니다.<br>
    <b>🎯 현재 의미:</b> 현재 수치는 {disp_120:.1f}%입니다. {'수치가 110%를 넘어가면 과열로 보고 곧 하락할 것을 경고하며, 90% 아래면 바닥으로 보고 반등을 기대합니다.' if abs(disp_120-100) > 5 else '현재 평균선 근처에서 안정적으로 흐르고 있습니다.'}
    </div>
    """, unsafe_allow_html=True)

with col_idx3:
    st.markdown("#### 3. RSI (상대강도지수)")
    st.info(f"현재 수치: **{rsi:.1f}**")
    st.markdown(f"""
    <div class="indicator-desc">
    <b>💡 설명:</b> 시장 참여자들의 심리적 과열 상태를 0~100으로 나타냅니다. 70 이상은 탐욕, 30 이하는 공포를 뜻합니다.<br>
    <b>🎯 현재 의미:</b> {rsi:.1f}점입니다. {'시장이 너무 흥분한 상태이니 추격 매수를 조심하세요.' if rsi > 70 else ('시장이 겁에 질린 상태이니 역발상 매수 기회입니다.' if rsi < 30 else '투자 심리가 매우 균형 잡힌 중립 상태입니다.')}
    </div>
    """, unsafe_allow_html=True)

# --- 차트 영역 ---
st.markdown("---")
st.subheader("📊 Performance Chart")
tabs = st.tabs(["1년", "3년", "전체"])
def render_chart(df_sub):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_sub.index, open=df_sub['Open'], high=df_sub['High'], low=df_sub['Low'], close=df_sub['Close'], name="Price", opacity=0.4))
    for d, c in {60:'#2f9e44', 120:'#1971c2', 240:'#495057'}.items():
        fig.add_trace(go.Scatter(x=df_sub.index, y=df_sub[f'MA{d}'], name=f'{d}MA', line=dict(color=c, width=2)))
    fig.update_layout(height=450, template="plotly_white", xaxis_rangeslider_visible=False, dragmode='pan', margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

with tabs[0]: render_chart(data.iloc[-250:])
with tabs[1]: render_chart(data.iloc[-750:])
with tabs[2]: render_chart(data)

# --- [PART 2] APPENDIX: Macro Economic Trends (하단 부록) ---
st.markdown('<div class="macro-appendix">', unsafe_allow_html=True)
st.markdown('<div style="font-size:24px; font-weight:700; color:#495057; margin-bottom:20px;">📎 Appendix: Global Macro Trends</div>', unsafe_allow_html=True)
a_c1, a_c2 = st.columns(2)
a_c3, a_c4 = st.columns(2)

def draw_macro(series, title, color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series.index, y=series.values, mode='lines+markers', line=dict(color=color, width=3)))
    fig.update_layout(height=250, title=title, template="plotly_white", margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

with a_c1: draw_macro(macro_history['Rate'], "US 10Y Yield (금리)", "#e03131")
with a_c2: draw_macro(macro_history['Oil'], "WTI Crude Oil (유가)", "#495057")
with a_c3: draw_macro(macro_history['Dollar'], "Dollar Index (달러)", "#1971c2")
with a_c4: draw_macro(macro_history['VIX'], "VIX Index (공포지수)", "#f08c00")
st.markdown('</div>', unsafe_allow_html=True)
