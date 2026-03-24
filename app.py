import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 및 프리미엄 디자인 UI
st.set_page_config(page_title="STRATEGIC MARKET INTELLIGENCE", layout="wide")

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
    .card-caption { font-size: 13px; color: #868e96; margin-top: 8px; line-height: 1.4; }
    .indicator-desc { background-color: #f8f9fa; padding: 15px; border-radius: 12px; border: 1px solid #eef0f2; margin-top: 10px; font-size: 14px; color: #444; }
    .macro-section { background-color: #f1f3f5; padding: 30px; border-radius: 20px; margin-top: 40px; border: 1px solid #dee2e6; }
    .news-box { background-color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #333; font-size: 13px; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 엔진
@st.cache_data(ttl=3600)
def load_all_data(ticker):
    # 지수 데이터 (최대 20년 이상)
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
    # 매크로: 미국 10년(^TNX), 한국 10년(KR10YT=RR), 유가(CL=F), 달러(DX-Y.NYB), VIX(^VIX)
    macros = {"US_Rate": "^TNX", "KR_Rate": "KR10YT=RR", "Oil": "CL=F", "Dollar": "DX-Y.NYB", "VIX": "^VIX"}
    results = {}
    for name, t in macros.items():
        d = yf.download(t, start="2022-01-01")
        if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
        results[name] = d['Close'].resample('ME').mean()
    return results

# --- 데이터 준비 ---
st.sidebar.markdown("### 🏛️ ASSET SELECTION")
indices = {"NASDAQ": "^IXIC", "NASDAQ 100": "^NDX", "S&P 500": "^GSPC", "KOSPI": "^KS11", "KOSDAQ": "^KQ11"}
choice = st.sidebar.radio("Primary Index", list(indices.keys()))
data = load_all_data(indices[choice])
macros = load_macro_trends()

last = data.iloc[-1]
curr, ma60, ma120, rsi = float(last['Close']), float(last['MA60']), float(last['MA120']), float(last['RSI'])
disp_120 = (curr / ma120) * 100

# --- [신규] 버핏 지수 계산 (Market Cap to GDP) ---
# 최신 명목 GDP 추정치 (US: 약 27조$, KR: 약 2300조원) 및 지수 시총 비중 활용 단순 모델
def get_buffett_status(idx_choice, current_price):
    if "NASDAQ" in idx_choice or "S&P" in idx_choice:
        ratio = (current_price / 15000) * 100 # 단순화된 모델
        status = "Overvalued" if ratio > 120 else ("Undervalued" if ratio < 80 else "Fair Value")
    else: # 한국
        ratio = (current_price / 2500) * 80
        status = "Overvalued" if ratio > 90 else ("Undervalued" if ratio < 60 else "Fair Value")
    return ratio, status

buff_val, buff_status = get_buffett_status(choice, curr)

# --- 상단: Executive Verdict ---
st.title(f"{choice} Intelligence Report")

score = 0
if ma60 > ma120: score += 2
if rsi < 40: score += 2
elif rsi > 65: score -= 2
if buff_status == "Undervalued": score += 1

if score >= 2: verdict, v_class = "긍정 (적극 투자 권장)", "positive-v"
elif score <= -1: verdict, v_class = "부정 (현금 비중 확대)", "negative-v"
else: verdict, v_class = "중립 (신중한 분할 대응)", "neutral-v"

st.markdown(f'''<div class="verdict-box {v_class}"><div style="font-size:12px; font-weight:700; opacity:0.7;">EXECUTIVE VERDICT</div><div class="v-content">{verdict}</div></div>''', unsafe_allow_html=True)

# --- 중단: 60/120 진단 & 버핏 지수 & 기술지표 설명 ---
st.subheader("🔍 Strategic Diagnostic & Valuation")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="info-card"><div class="card-title">Buffett Indicator</div><div class="card-val">{buff_val:.1f}%</div><div class="card-caption">상태: <b>{buff_status}</b><br>GDP 대비 시총 비중을 통한 저평가/고평가 판단 지표입니다.</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="info-card"><div class="card-title">Trend (60/120)</div><div class="card-val">{"Bullish" if ma60 > ma120 else "Bearish"}</div><div class="card-caption">배열: <b>{"정배열" if ma60 > ma120 else "역배열"}</b><br>60일 수급선과 120일 경기선의 정배열 여부를 체크합니다.</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="info-card"><div class="card-title">Mean Reversion</div><div class="card-val">{disp_120:.1f}%</div><div class="card-caption">해석: <b>{"과열 주의" if disp_120 > 110 else "안정적"}</b><br>120일 평균 가격에서 현재 주가가 얼마나 벌어져 있는지 측정합니다.</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="info-card"><div class="card-title">Sentiment (RSI)</div><div class="card-val">{rsi:.1f}</div><div class="card-caption">심리: <b>{"탐욕" if rsi > 70 else ("공포" if rsi < 30 else "중립")}</b><br>시장 참여자들의 단기 심리 과열도를 0~100으로 나타냅니다.</div></div>', unsafe_allow_html=True)

# --- 차트 영역 (8단계 탭 유지 및 확장) ---
st.markdown("---")
st.subheader("📅 Interactive Performance Analysis")
tabs = st.tabs(["7일", "1개월", "3개월", "6개월", "1년", "3년", "5년", "10년"])
days_map = {"7일":7, "1개월":20, "3개월":60, "6개월":125, "1년":250, "3년":750, "5년":1250, "10년":2500}

def render_chart(df_sub, period_name):
    # 수익률 계산
    s_p, e_p = float(df_sub['Close'].iloc[0]), float(df_sub['Close'].iloc[-1])
    ret = ((e_p - s_p) / s_p) * 100
    st.markdown(f"**{period_name} 성과:** 실질 수익률 {ret:.2f}%")
    
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_sub.index, open=df_sub['Open'], high=df_sub['High'], low=df_sub['Low'], close=df_sub['Close'], name="Price", opacity=0.4))
    for d, c in {60:'#5c7cfa', 120:'#228be6', 240:'#adb5bd'}.items():
        if f'MA{d}' in df_sub.columns:
            fig.add_trace(go.Scatter(x=df_sub.index, y=df_sub[f'MA{d}'], name=f'{d}MA', line=dict(color=c, width=2 if d != 240 else 1.2)))
    fig.update_layout(height=500, template="plotly_white", xaxis_rangeslider_visible=False, dragmode='pan', margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

for i, (name, days) in enumerate(days_map.items()):
    with tabs[i]: render_chart(data.iloc[-days:], name)

# --- 하단: Macro Economic Trends (부록 및 인사이트) ---
st.markdown('<div class="macro-section">', unsafe_allow_html=True)
st.markdown('### 📎 Appendix: Macro Pulse & Global News Insight', unsafe_allow_html=True)

m_c1, m_c2 = st.columns(2)
m_c3, m_c4 = st.columns(2)

def draw_macro(series, title, color, insight, news):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series.index, y=series.values, mode='lines+markers', line=dict(color=color, width=3)))
    fig.update_layout(height=250, title=title, template="plotly_white", margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.info(f"**💡 Insight:** {insight}")
    st.markdown(f'<div class="news-box"><b>📰 주요 요인 및 뉴스:</b><br>{news}</div>', unsafe_allow_html=True)

with m_c1:
    draw_macro(macros['US_Rate'], "US/KR 10Y Yield (금리 추이)", "#e03131", 
               "금리 상승 시 기술주 밸류에이션 부담 가중. 미/한 금리차 확대 시 환율 변동 주의.", 
               "- 연준 FOMC 금리 동결/인상 가능성 논의<br>- 인플레이션 지표(CPI, PCE) 발표에 따른 국채 매도세")
with m_c2:
    draw_macro(macros['Oil'], "WTI Crude Oil (유가)", "#495057", 
               "유가 85불 상회 시 인플레이션 재점화 및 소비 위축 리스크.", 
               "- 중동 지정학적 리스크 심화<br>- OPEC+ 감산 연장 여부 및 글로벌 경기 둔화 우려")
with m_c3:
    draw_macro(macros['Dollar'], "Dollar Index (달러 인덱스)", "#1971c2", 
               "강달러 지속 시 외국인 자금 유출로 국내 증시 하방 압력.", 
               "- 글로벌 안전자산 선호 심리 강화<br>- 타 통화(엔, 유로) 대비 달러 가치 상대적 강세")
with m_c4:
    draw_macro(macros['VIX'], "VIX Index (공포지수)", "#f08c00", 
               "25 상회 시 시장 패닉 셀링 구간. 역사적 저점에서는 변동성 폭발 주의.", 
               "- 시장 변동성 확대 및 파생상품 청산 물량 발생<br>- 불확실성 증대로 인한 헤지 펀드들의 매수세")

st.markdown('</div>', unsafe_allow_html=True)

# --- 최하단: 투자 가이드북 (기존 내용 유지) ---
st.markdown("---")
st.subheader("📖 AI 투자 가이드북 (Executive Reference)")
g1, g2, g3 = st.columns(3)
with g1:
    st.markdown("#### 1. 버핏 지수와 밸류에이션\n버핏 지수가 120%를 넘으면 역사적으로 시장이 '매우 비싼' 구간입니다. 수익률이 좋아도 현금 비중을 조금씩 늘리는 지혜가 필요합니다.")
with g2:
    st.markdown("#### 2. 금리와 기술주의 상관관계\n금리 차트가 우상향할 때 나스닥은 가장 취약합니다. 하단의 금리 추이가 꺾이는지 확인하는 것이 매수 타이밍의 핵심입니다.")
with g3:
    st.markdown("#### 3. 평균 회귀와 이격률\n주가는 결국 120일선으로 돌아옵니다. 이격률이 115%를 넘으면 욕심을 버리고, 85%를 밑돌면 용기를 내어 분할 매수하세요.")
