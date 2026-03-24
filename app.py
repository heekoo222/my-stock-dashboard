import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 및 프리미엄 디자인
st.set_page_config(page_title="GLOBAL STRATEGIC DASHBOARD 2026", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #fcfcfc; font-family: 'Inter', sans-serif; }
    .verdict-box { padding: 30px; border-radius: 20px; margin-bottom: 30px; border: 1px solid #efefef;}
    .positive-v { background: linear-gradient(135deg, #fff5f5 0%, #ffffff 100%); border-left: 10px solid #ff6b6b; color: #e03131; }
    .neutral-v { background: linear-gradient(135deg, #fff9db 0%, #ffffff 100%); border-left: 10px solid #fab005; color: #f08c00; }
    .negative-v { background: linear-gradient(135deg, #e7f5ff 0%, #ffffff 100%); border-left: 10px solid #228be6; color: #1971c2; }
    .v-content { font-size: 34px; font-weight: 800; letter-spacing: -1.2px; line-height: 1.1; }
    .info-card { background-color: #ffffff; padding: 22px; border-radius: 15px; border: 1px solid #f1f3f5; box-shadow: 0 4px 12px rgba(0,0,0,0.03); height: 100%; }
    .card-title { font-size: 12px; font-weight: 700; color: #adb5bd; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }
    .card-val { font-size: 26px; font-weight: 700; color: #212529; letter-spacing: -0.5px; }
    .macro-section { background-color: #1a1c1e; padding: 40px; border-radius: 25px; margin-top: 50px; color: white; }
    .situation-box { background-color: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; border-left: 4px solid #fab005; font-size: 13px; margin-top: 10px; line-height: 1.6; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 엔진
@st.cache_data(ttl=3600)
def load_all_market_data(ticker):
    df = yf.download(ticker, start="2000-01-01")
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    for m in [5, 20, 60, 120, 240, 480]:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    df['G'] = (df['MA60'].shift(1) < df['MA120'].shift(1)) & (df['MA60'] > df['MA120'])
    df['D'] = (df['MA60'].shift(1) > df['MA120'].shift(1)) & (df['MA60'] < df['MA120'])
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    return df.dropna(subset=['MA240'])

@st.cache_data(ttl=3600)
def load_macro_trends():
    macros = {"US_Rate": "^TNX", "KR_Rate": "KR10YT=RR", "Oil": "CL=F", "Dollar": "DX-Y.NYB", "VIX": "^VIX"}
    results = {}
    for name, t in macros.items():
        d = yf.download(t, start="2022-01-01")
        if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
        results[name] = d['Close']
    return results

# --- 데이터 로드 ---
indices = {"NASDAQ": "^IXIC", "NASDAQ 100": "^NDX", "S&P 500": "^GSPC", "KOSPI": "^KS11", "KOSDAQ": "^KQ11"}
choice = st.sidebar.radio("Primary Index", list(indices.keys()))
data = load_all_market_data(indices[choice])
macros_data = load_macro_trends()

# 실시간 분석
last = data.iloc[-1]
curr, ma60, ma120, rsi = float(last['Close']), float(last['MA60']), float(last['MA120']), float(last['RSI'])
disp_120 = (curr / ma120) * 100

# 버핏 지수 정밀 계산 (2026 추정 GDP 기반)
def get_accurate_buffett(idx_choice, price):
    if any(x in idx_choice for x in ["NASDAQ", "S&P"]):
        est_market_cap = price * 9.5 / 1000 
        gdp, ratio_ref = 28.5, 170
        ratio = (est_market_cap / gdp) * 100
    else:
        est_market_cap = price * 0.83 
        gdp, ratio_ref = 2450, 110
        ratio = (est_market_cap / gdp) * 100
    status = "Overvalued" if ratio > ratio_ref else ("Undervalued" if ratio < ratio_ref * 0.7 else "Fair Value")
    return ratio, status

buff_val, buff_status = get_accurate_buffett(choice, curr)

# --- 상단: Executive Verdict ---
score = 0
if ma60 > ma120: score += 2
if rsi < 40: score += 2
elif rsi > 65: score -= 2
if buff_status == "Undervalued": score += 1

if score >= 2: verdict, v_class = "긍정 (적극 투자 권장)", "positive-v"
elif score <= -1: verdict, v_class = "부정 (보수적 대응 권장)", "negative-v"
else: verdict, v_class = "중립 (시장 관망 필요)", "neutral-v"

st.title(f"{choice} Strategic Monitoring")
st.markdown(f'''<div class="verdict-box {v_class}"><div style="font-size:12px; font-weight:700; opacity:0.7;">EXECUTIVE VERDICT</div><div class="v-content">{verdict}</div></div>''', unsafe_allow_html=True)

# --- 중단: 주요 지표 카드 ---
c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(f'<div class="info-card"><div class="card-title">Buffett Indicator</div><div class="card-val">{buff_val:.1f}%</div><div class="card-caption">상태: <b>{buff_status}</b><br>GDP 대비 밸류에이션 부담 측정</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="info-card"><div class="card-title">60/120 Trend</div><div class="card-val">{"Upward" if ma60 > ma120 else "Downward"}</div><div class="card-caption">배열: <b>{"정배열" if ma60 > ma120 else "역배열"}</b></div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="info-card"><div class="card-title">Disparity (120MA)</div><div class="card-val">{disp_120:.1f}%</div><div class="card-caption">평균 회귀 가능성 진단</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="info-card"><div class="card-title">RSI (Sentiment)</div><div class="card-val">{rsi:.1f}</div><div class="card-caption">시장 심리 과열도 측정</div></div>', unsafe_allow_html=True)

# --- 차트 영역 (8단계 탭) ---
st.markdown("---")
tabs = st.tabs(["7일", "1개월", "3개월", "6개월", "1년", "3년", "5년", "10년"])
days_map = {"7일":7, "1개월":22, "3개월":66, "6개월":132, "1년":252, "3년":756, "5년":1260, "10년":2520}

def render_chart(df_sub, p_name):
    ret = ((df_sub['Close'].iloc[-1] - df_sub['Close'].iloc[0]) / df_sub['Close'].iloc[0]) * 100
    st.markdown(f"**{p_name} 실질 수익률:** {ret:.2f}%")
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_sub.index, open=df_sub['Open'], high=df_sub['High'], low=df_sub['Low'], close=df_sub['Close'], name="Price", opacity=0.4))
    for d, c in {60:'#5c7cfa', 120:'#228be6', 240:'#adb5bd'}.items():
        if f'MA{d}' in df_sub.columns: fig.add_trace(go.Scatter(x=df_sub.index, y=df_sub[f'MA{d}'], name=f'{d}MA', line=dict(color=c, width=2)))
    fig.update_layout(height=480, template="plotly_white", xaxis_rangeslider_visible=False, dragmode='pan', margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

for i, (name, d) in enumerate(days_map.items()):
    with tabs[i]: render_chart(data.iloc[-d:], name)

# --- 하단: 매크로 Appendix & 다이내믹 시나리오 엔진 ---
st.markdown('<div class="macro-section"><h2>📎 Appendix: Global Macro Situation Report</h2>', unsafe_allow_html=True)
m1, m2 = st.columns(2)
m3, m4 = st.columns(2)

def get_macro_situation(name, series):
    curr_v = series.iloc[-1]
    prev_v = series.iloc[-22] # 약 한달 전 데이터와 비교
    diff = curr_v - prev_v
    
    if name == "US_Rate":
        status = "금리 급등 중" if diff > 0.3 else ("금리 하락 중" if diff < -0.3 else "금리 횡보 중")
        impact = "기술주 멀티플 하락 압력 가중" if diff > 0.3 else "성장주 투자 심리 개선"
        news = f"현재 미 10년물 금리가 {curr_v:.2f}%로 한 달 전 대비 {diff:+.2f}% 변화했습니다. {status} 상황으로 인해 {impact} 중입니다."
    elif name == "Oil":
        status = "에너지 가격 상승" if diff > 5 else ("에너지 가격 안정" if diff < -5 else "유가 보합세")
        impact = "인플레이션 재점화 우려" if curr_v > 85 else "물가 안정 및 비용 절감"
        news = f"WTI 유가가 배럴당 ${curr_v:.2f}를 기록하며 {status}을 보이고 있습니다. 이는 {impact} 요인으로 작용합니다."
    elif name == "Dollar":
        status = "킹달러 현상" if diff > 2 else ("달러 약세" if diff < -2 else "환율 안정")
        impact = "외국인 자금 이탈 경계" if diff > 2 else "신흥국 증시 자금 유입 기대"
        news = f"달러 인덱스가 {curr_v:.2f}로 {status}을 나타내고 있습니다. {impact}가 필요한 시점입니다."
    else: # VIX
        status = "시장 공포 확산" if curr_v > 25 else "시장 안도 랠리"
        impact = "변동성 매도 물량 주의" if curr_v > 25 else "변동성 폭발 전야 경계"
        news = f"VIX 지수가 {curr_v:.2f}로 {status} 국면입니다. {impact} 단계입니다."
    return news

def draw_macro_appendix(series, title, color, name):
    fig = go.Figure(go.Scatter(x=series.index[-250:], y=series.values[-250:], mode='lines', line=dict(color=color, width=2)))
    fig.update_layout(height=220, title=title, template="plotly_dark", margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)
    situation = get_macro_situation(name, series)
    st.markdown(f'<div class="situation-box"><b>🕵️ 실시간 상황 진단:</b><br>{situation}</div>', unsafe_allow_html=True)

with m1: draw_macro_appendix(macros_data['US_Rate'], "US 10Y Yield", "#ff6b6b", "US_Rate")
with m2: draw_macro_appendix(macros_data['Oil'], "WTI Crude Oil", "#adb5bd", "Oil")
with m3: draw_macro_appendix(macros_data['Dollar'], "Dollar Index", "#4dadf7", "Dollar")
with m4: draw_macro_appendix(macros_data['VIX'], "VIX (Fear Index)", "#fab005", "VIX")
st.markdown('</div>', unsafe_allow_html=True)
