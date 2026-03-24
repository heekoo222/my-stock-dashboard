import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 및 프리미엄 매크로 디자인
st.set_page_config(page_title="GLOBAL MACRO & MARKET MONITOR", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #f8f9fa; font-family: 'Inter', sans-serif; }
    .macro-card { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #eee; box-shadow: 0 4px 6px rgba(0,0,0,0.02); height: 100%; }
    .macro-label { font-size: 12px; font-weight: 700; color: #888; text-transform: uppercase; letter-spacing: 1px; }
    .macro-val { font-size: 24px; font-weight: 800; color: #111; margin: 5px 0; }
    .macro-status { font-size: 13px; font-weight: 600; padding: 4px 8px; border-radius: 6px; display: inline-block; }
    .status-bad { background-color: #fff5f5; color: #e03131; } /* 주가에 부정적 */
    .status-good { background-color: #ebfbee; color: #2f9e44; } /* 주가에 긍정적 */
    .verdict-box { padding: 30px; border-radius: 20px; margin-bottom: 30px; border: 1px solid #e9ecef; }
    .positive-v { background: linear-gradient(135deg, #fff5f5 0%, #ffffff 100%); border-left: 10px solid #ff6b6b; color: #e03131; }
    .neutral-v { background: linear-gradient(135deg, #fff9db 0%, #ffffff 100%); border-left: 10px solid #fab005; color: #f08c00; }
    .negative-v { background: linear-gradient(135deg, #e7f5ff 0%, #ffffff 100%); border-left: 10px solid #228be6; color: #1971c2; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 엔진 (지수 + 매크로)
@st.cache_data(ttl=3600)
def load_all_market_data(ticker):
    # 지수 데이터
    df = yf.download(ticker, start="2000-01-01")
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    for m in [5, 20, 60, 120, 240]:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    df['G'] = (df['MA60'].shift(1) < df['MA120'].shift(1)) & (df['MA60'] > df['MA120'])
    df['D'] = (df['MA60'].shift(1) > df['MA120'].shift(1)) & (df['MA60'] < df['MA120'])
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    return df.dropna(subset=['MA240'])

@st.cache_data(ttl=3600)
def get_macro_data():
    # 금리(^TNX), 유가(CL=F), 달러(DX-Y.NYB), VIX(^VIX)
    macros = {"Rate": "^TNX", "Oil": "CL=F", "Dollar": "DX-Y.NYB", "VIX": "^VIX"}
    results = {}
    for name, t in macros.items():
        d = yf.download(t, period="5d")
        if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
        curr = d['Close'].iloc[-1]
        prev = d['Close'].iloc[-2]
        change = ((curr - prev) / prev) * 100
        results[name] = {"val": curr, "change": change}
    return results

# --- 데이터 로드 ---
macro_dict = get_macro_data()
st.sidebar.markdown("### 🏛️ MONITORING ASSETS")
indices = {"NASDAQ": "^IXIC", "NASDAQ 100": "^NDX", "S&P 500": "^GSPC", "KOSPI": "^KS11", "KOSDAQ": "^KQ11"}
choice = st.sidebar.radio("Select Benchmark", list(indices.keys()))
data = load_all_market_data(indices[choice])

# 실시간 분석
last = data.iloc[-1]
curr, ma60, ma120, rsi = float(last['Close']), float(last['MA60']), float(last['MA120']), float(last['RSI'])

# --- 1단계: Global Macro Pulse (가장 상단) ---
st.title("🌐 Global Macro & Market Intelligence")
m_c1, m_c2, m_c3, m_c4 = st.columns(4)

with m_c1:
    rate = macro_dict['Rate']
    status = "BAD (Tech Risk)" if rate['change'] > 0 else "GOOD"
    st.markdown(f'''<div class="macro-card"><div class="macro-label">US 10Y Yield (금리)</div><div class="macro-val">{rate['val']:.2f}%</div>
                <div class="macro-status {'status-bad' if status[0]=='B' else 'status-good'}">{status}</div>
                <div style="font-size:11px; color:#888; margin-top:5px;">금리 상승은 기술주 가치 하락의 원인이 됩니다.</div></div>''', unsafe_allow_html=True)
with m_c2:
    oil = macro_dict['Oil']
    status = "BAD (Inflation)" if oil['val'] > 85 else "STABLE"
    st.markdown(f'''<div class="macro-card"><div class="macro-label">WTI Oil (유가)</div><div class="macro-val">${oil['val']:.2f}</div>
                <div class="macro-status {'status-bad' if status[0]=='B' else 'status-good'}">{status}</div>
                <div style="font-size:11px; color:#888; margin-top:5px;">고유가는 물가 상승과 소비 위축을 초래합니다.</div></div>''', unsafe_allow_html=True)
with m_c3:
    dollar = macro_dict['Dollar']
    status = "BAD (FX Risk)" if dollar['change'] > 0.5 else "STABLE"
    st.markdown(f'''<div class="macro-card"><div class="macro-label">Dollar Index (달러)</div><div class="macro-val">{dollar['val']:.2f}</div>
                <div class="macro-status {'status-bad' if status[0]=='B' else 'status-good'}">{status}</div>
                <div style="font-size:11px; color:#888; margin-top:5px;">강달러는 신흥국 주식 시장의 자금 유출을 부릅니다.</div></div>''', unsafe_allow_html=True)
with m_c4:
    vix = macro_dict['VIX']
    status = "RISK (Fear)" if vix['val'] > 25 else "NORMAL"
    st.markdown(f'''<div class="macro-card"><div class="macro-label">VIX Index (공포)</div><div class="macro-val">{vix['val']:.2f}</div>
                <div class="macro-status {'status-bad' if status[0]=='R' else 'status-good'}">{status}</div>
                <div style="font-size:11px; color:#888; margin-top:5px;">지수가 높을수록 시장의 불안감이 크다는 뜻입니다.</div></div>''', unsafe_allow_html=True)

# --- 2단계: 매크로 결합형 투자 의견 ---
score = 0
if ma60 > ma120: score += 2
if rsi < 40: score += 2
elif rsi > 60: score -= 2
if macro_dict['Rate']['change'] > 1.5: score -= 1 # 금리 급등 시 패널티

if score >= 2: verdict, v_class = "적극적 투자 권장 (매크로 우호)", "positive-v"
elif score <= -1: verdict, v_class = "보수적 관망 (리스크 관리)", "negative-v"
else: verdict, v_class = "중립적 접근 (포트폴리오 유지)", "neutral-v"

st.markdown(f'<div class="verdict-box {v_class}"><div class="v-title">Executive Verdict</div><div class="v-content">{verdict}</div></div>', unsafe_allow_html=True)

# --- 3단계: 지수 상세 분석 (이전 핵심 로직 유지) ---
st.subheader(f"📊 {choice} Technical Analysis")
t1, t2, t3 = st.columns(3)
with t1: st.info(f"**이평선 배열:** {'상승 정배열' if ma60 > ma120 else '하락 역배열'}")
with t2: st.info(f"**이격률(120일):** {(curr/ma120*100):.1f}% (평균 회귀 확인)")
with t3: st.info(f"**RSI 지표:** {rsi:.1f} ({'과열' if rsi > 70 else ('바닥' if rsi < 30 else '안정')})")

tabs = st.tabs(["1년 흐름", "3년 흐름", "전체 및 10년 예측"])
def render_chart(df_plot):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name="Price", opacity=0.4))
    for d, c in {60:'#2f9e44', 120:'#1971c2', 240:'#495057'}.items():
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot[f'MA{d}'], name=f'{d}MA', line=dict(color=c, width=2)))
    fig.update_layout(height=500, template="plotly_white", xaxis_rangeslider_visible=False, dragmode='pan', margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

with tabs[0]: render_chart(data.iloc[-250:])
with tabs[1]: render_chart(data.iloc[-750:])
with tabs[2]: render_chart(data)

# --- 4단계: 초보자를 위한 매크로 가이드북 (최하단) ---
st.markdown("---")
st.subheader("💡 초보 투자자를 위한 매크로-주식 연결고리")
g1, g2, g3, g4 = st.columns(4)
with g1:
    st.markdown("### 🏦 금리와 주가\n금리는 '돈의 값어치'입니다. 금리가 오르면 기업이 돈 빌리는 비용이 비싸져 이익이 줄고, 주가는 하락 압력을 받습니다.")
with g2:
    st.markdown("### 🛢️ 유가와 물가\n유가는 '물가의 기초'입니다. 유가가 너무 오르면 물가(인플레이션)가 올라 연준이 금리를 더 올릴 가능성이 높아집니다.")
with g3:
    st.markdown("### 💵 달러와 환율\n달러가 강해지면 외국인 투자자들이 한국 주식을 팔고 달러로 바꿔 나가려 하기 때문에 한국 증시엔 악재입니다.")
with g4:
    st.markdown("### 📉 VIX와 심리\n'공포 지수'라고 불립니다. 시장이 불안할 때 치솟으며, 가끔 VIX가 너무 높을 때가 역발상 매수 기회가 되기도 합니다.")
