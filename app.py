import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 및 프리미엄 스타일 시트 (Executive UI)
st.set_page_config(page_title="STRATEGIC MARKET INTELLIGENCE 2026", layout="wide")

st.markdown("""
    <style>
    /* 전체 배경 및 폰트 */
    [data-testid="stAppViewContainer"] { background-color: #fcfcfc; font-family: 'Inter', sans-serif; }
    
    /* 최종 결론 (Verdict) 디자인 */
    .verdict-box { padding: 30px; border-radius: 20px; margin-bottom: 30px; border: 1px solid #efefef;}
    .positive-v { background: linear-gradient(135deg, #fff5f5 0%, #ffffff 100%); border-left: 10px solid #ff6b6b; color: #e03131; }
    .neutral-v { background: linear-gradient(135deg, #fff9db 0%, #ffffff 100%); border-left: 10px solid #fab005; color: #f08c00; }
    .negative-v { background: linear-gradient(135deg, #e7f5ff 0%, #ffffff 100%); border-left: 10px solid #228be6; color: #1971c2; }
    .v-content { font-size: 34px; font-weight: 800; letter-spacing: -1.2px; line-height: 1.1; }
    
    /* 정보 카드 UI */
    .info-card { background-color: #ffffff; padding: 22px; border-radius: 15px; border: 1px solid #f1f3f5; box-shadow: 0 4px 12px rgba(0,0,0,0.03); height: 100%; }
    .card-title { font-size: 12px; font-weight: 700; color: #adb5bd; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }
    .card-val { font-size: 26px; font-weight: 700; color: #212529; letter-spacing: -0.5px; }
    .card-caption { font-size: 13px; color: #868e96; margin-top: 8px; line-height: 1.4; }
    
    /* 지표 설명 박스 */
    .indicator-desc { background-color: #f8f9fa; padding: 15px; border-radius: 12px; border: 1px solid #eef0f2; margin-top: 10px; font-size: 14px; color: #444; line-height: 1.6;}
    
    /* 하단 매크로 섹션 */
    .macro-section { background-color: #1a1c1e; padding: 40px; border-radius: 25px; margin-top: 50px; color: white; }
    .situation-box { background-color: rgba(255,255,255,0.07); padding: 15px; border-radius: 10px; border-left: 4px solid #fab005; font-size: 13px; margin-top: 10px; line-height: 1.6; color: #ced4da; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 수집 및 계산 엔진
@st.cache_data(ttl=3600)
def load_market_intelligence(ticker):
    df = yf.download(ticker, start="2000-01-01")
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # 이동평균선 (전체 라인업)
    for m in [5, 20, 60, 120, 240, 480]:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    
    # 기술적 신호 (60 vs 120 기준)
    df['G'] = (df['MA60'].shift(1) < df['MA120'].shift(1)) & (df['MA60'] > df['MA120'])
    df['D'] = (df['MA60'].shift(1) > df['MA120'].shift(1)) & (df['MA60'] < df['MA120'])
    
    # RSI & MACD
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    return df.dropna(subset=['MA240'])

@st.cache_data(ttl=3600)
def load_macro_data():
    # 미국채 10년, 한국채 10년, 유가, 달러인덱스, VIX
    macros = {"US_Rate": "^TNX", "KR_Rate": "KR10YT=RR", "Oil": "CL=F", "Dollar": "DX-Y.NYB", "VIX": "^VIX"}
    res = {}
    for k, t in macros.items():
        d = yf.download(t, start="2022-01-01")
        if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
        res[k] = d['Close']
    return res

# --- 데이터 로드 및 초기화 ---
indices = {"NASDAQ Composite": "^IXIC", "NASDAQ 100": "^NDX", "S&P 500": "^GSPC", "KOSPI": "^KS11", "KOSDAQ": "^KQ11"}
choice = st.sidebar.radio("Select Asset", list(indices.keys()))
data = load_market_intelligence(indices[choice])
macros = load_macro_data()

last = data.iloc[-1]
curr, ma60, ma120, rsi = float(last['Close']), float(last['MA60']), float(last['MA120']), float(last['RSI'])
disp_120 = (curr / ma120) * 100

# 3. 버핏 지수 정밀 계산 로직 (2026 GDP 반영)
def get_buffett_score(idx_name, price):
    if any(x in idx_name for x in ["NASDAQ", "S&P"]):
        est_cap = price * 9.5 / 1000 # US 시총 추정 (Trillion $)
        gdp = 28.5 # 2026 US GDP 추정
        ratio = (est_cap / gdp) * 100
        status = "Overvalued" if ratio > 170 else ("Undervalued" if ratio < 100 else "Fair Value")
    else:
        est_cap = price * 0.83 # KR 시총 추정 (Trillion KRW)
        gdp = 2450 # 2026 KR GDP 추정
        ratio = (est_cap / gdp) * 100
        status = "Overvalued" if ratio > 110 else ("Undervalued" if ratio < 70 else "Fair Value")
    return ratio, status

buff_val, buff_status = get_buffett_score(choice, curr)

# 4. 상단 섹션: AI Investment Verdict
score = 0
if ma60 > ma120: score += 2
if rsi < 40: score += 2
elif rsi > 65: score -= 2
if buff_status == "Undervalued": score += 1

if score >= 2: verdict, v_class = "긍정 (적극 투자 권장)", "positive-v"
elif score <= -1: verdict, v_class = "부정 (현금 비중 확대)", "negative-v"
else: verdict, v_class = "중립 (신중한 분할 대응)", "neutral-v"

st.title(f"Strategic Intelligence: {choice}")
st.markdown(f'''<div class="verdict-box {v_class}"><div style="font-size:12px; font-weight:700; opacity:0.7;">EXECUTIVE VERDICT</div><div class="v-content">{verdict}</div></div>''', unsafe_allow_html=True)

# 5. 중단 섹션: 지표 카드 및 사전식 설명
st.subheader("🔍 핵심 지표 진단 (Strategic Diagnosis)")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="info-card"><div class="card-title">Buffett Indicator</div><div class="card-val">{buff_val:.1f}%</div><div class="card-caption">상태: <b>{buff_status}</b><br>GDP 대비 전체 시총 비중을 통한 시장 거품 측정</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="info-card"><div class="card-title">Trend Strategy</div><div class="card-val">{"Bullish" if ma60 > ma120 else "Bearish"}</div><div class="card-caption">배열: <b>{"정배열" if ma60 > ma120 else "역배열"}</b><br>60일 수급선과 120일 경기선의 정렬 상태</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="info-card"><div class="card-title">Mean Reversion</div><div class="card-val">{disp_120:.1f}%</div><div class="card-caption">진단: <b>{"고평가 주의" if disp_120 > 110 else "안정적"}</b><br>120일 평균선 대비 현재 주가 위치</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="info-card"><div class="card-title">Sentiment (RSI)</div><div class="card-val">{rsi:.1f}</div><div class="card-caption">심리: <b>{"탐욕" if rsi > 70 else ("공포" if rsi < 30 else "중립")}</b><br>시장 참여자들의 단기 심리 과열도</div></div>', unsafe_allow_html=True)

# 지표 설명 섹션 (초보자용)
with st.expander("📚 지표 설명 및 현재 수치 해석 가이드"):
    st.markdown(f"""
    <div class="indicator-desc">
    <b>1. 버핏 지수 ({buff_val:.1f}%):</b> GDP 대비 시가총액 비율입니다. 현재 {buff_status} 상태이며, 이는 역사적 평균 대비 {'비싼' if 'Over' in buff_status else '저렴한'} 가격임을 뜻합니다.<br>
    <b>2. 이평선 배열:</b> 60일선이 120일선 위에 있는 {'정배열은 상승 추세의 지속' if ma60 > ma120 else '역배열은 하락 추세의 심화'}를 의미합니다.<br>
    <b>3. 이격률 ({disp_120:.1f}%):</b> 주가가 120일 평균선에서 {abs(disp_120-100):.1f}% 벌어져 있습니다. 수치가 100에서 멀어질수록 평균으로 회귀하려는 성질이 강해집니다.<br>
    <b>4. RSI ({rsi:.1f}):</b> 70 이상은 과매수(매도 검토), 30 이하는 과매도(매수 검토)입니다. 현재는 {rsi:.1f}로 {'심리가 안정적입니다.' if 30 < rsi < 70 else '극단적 심리 구간입니다.'}
    </div>
    """, unsafe_allow_html=True)

# 6. 차트 영역: 8단계 기간 탭 및 수익률(CAGR) 자동화
st.markdown("---")
st.subheader("📅 Interactive Performance Report")
tabs = st.tabs(["7일", "1개월", "3개월", "6개월", "1년", "3년", "5년", "10년"])
days_map = {"7일":7, "1개월":22, "3개월":66, "6개월":132, "1년":252, "3년":756, "5년":1260, "10년":2520}

def render_performance_chart(df_sub, p_name):
    # 수익률 및 CAGR 계산
    start_p, end_p = float(df_sub['Close'].iloc[0]), float(df_sub['Close'].iloc[-1])
    ret = ((end_p - start_p) / start_p) * 100
    days = (df_sub.index[-1] - df_sub.index[0]).days
    cagr = (((end_p / start_p) ** (365 / days)) - 1) * 100 if days > 0 else 0
    
    col_m1, col_m2 = st.columns(2)
    col_m1.metric(f"{p_name} 실질 수익률", f"{ret:.2f}%")
    col_m2.metric(f"{p_name} 연평균 수익률(CAGR)", f"{cagr:.2f}%")
    
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_sub.index, open=df_sub['Open'], high=df_sub['High'], low=df_sub['Low'], close=df_sub['Close'], name="Price", opacity=0.4))
    for d, c in {60:'#5c7cfa', 120:'#228be6', 240:'#adb5bd'}.items():
        if f'MA{d}' in df_sub.columns:
            fig.add_trace(go.Scatter(x=df_sub.index, y=df_sub[f'MA{d}'], name=f'{d}MA', line=dict(color=c, width=2)))
    
    # 골든/데드크로스 마커
    gs, ds = df_sub[df_sub['G']], df_sub[df_sub['D']]
    fig.add_trace(go.Scatter(x=gs.index, y=gs['MA60'], mode='markers', marker=dict(symbol='triangle-up', size=12, color='#e03131'), name='Golden'))
    fig.add_trace(go.Scatter(x=ds.index, y=ds['MA60'], mode='markers', marker=dict(symbol='triangle-down', size=12, color='#1971c2'), name='Death'))

    fig.update_layout(height=480, template="plotly_white", xaxis_rangeslider_visible=False, dragmode='pan', margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

for i, (name, d) in enumerate(days_map.items()):
    with tabs[i]: render_performance_chart(data.iloc[-d:], name)

# 7. 하단 부록: Global Macro Pulse & Dynamic Analysis
st.markdown('<div class="macro-section"><h2>📎 Appendix: Global Macro Situation Report</h2>', unsafe_allow_html=True)
m1, m2 = st.columns(2)
m3, m4 = st.columns(2)

def get_macro_logic(name, series):
    curr_v = series.iloc[-1]
    prev_v = series.iloc[-22] # 한달 전
    diff = curr_v - prev_v
    if name == "US_Rate":
        msg = f"미 10년물 국채 금리가 {curr_v:.2f}%로 {'상승' if diff > 0 else '하락'}세입니다. 금리 상승 시 나스닥 등 성장주 밸류에이션 하락 압력이 커집니다."
    elif name == "Oil":
        msg = f"WTI 유가가 ${curr_v:.2f}를 기록 중입니다. 85불 상회 시 인플레이션 우려가 다시 주가 발목을 잡을 수 있습니다."
    elif name == "Dollar":
        msg = f"달러 인덱스 {curr_v:.2f} 수준입니다. 강달러 지속 시 신흥국(KOSPI) 시장에서의 외국인 자금 유출 위험이 커집니다."
    else:
        msg = f"VIX 공포 지수 {curr_v:.2f}입니다. 20 이하는 평온한 상태이나, 역사적 저점에서 급등 시 패닉 셀링을 주의해야 합니다."
    return msg

def draw_macro_appendix(series, title, color, m_name):
    fig = go.Figure(go.Scatter(x=series.index[-250:], y=series.values[-250:], mode='lines', line=dict(color=color, width=2.5)))
    fig.update_layout(height=220, title=title, template="plotly_dark", margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f'<div class="situation-box"><b>🕵️ 분석 및 리스크 요인:</b><br>{get_macro_logic(m_name, series)}</div>', unsafe_allow_html=True)

with m1: draw_macro_appendix(macros['US_Rate'], "US 10Y Yield", "#ff6b6b", "US_Rate")
with m2: draw_macro_appendix(macros['Oil'], "WTI Crude Oil", "#adb5bd", "Oil")
with m3: draw_macro_appendix(macros['Dollar'], "Dollar Index", "#4dadf7", "Dollar")
with m4: draw_macro_appendix(macros['VIX'], "VIX (Fear Index)", "#fab005", "VIX")
st.markdown('</div>', unsafe_allow_html=True)

# 8. 투자 가이드북 (Executive Reference)
st.markdown("---")
st.subheader("📖 자산제곱 AI 투자 가이드북")
g_col1, g_col2, g_col3 = st.columns(3)
with g_col1:
    st.info("**1. 평균 회귀 원칙:** 이격률이 110%를 넘으면 욕심을 줄이고, 90% 아래면 공포를 이겨내고 매수를 검토하세요.")
with g_col2:
    st.info("**2. 매크로-주가 연결:** 하단 Appendix의 금리와 달러가 동시에 오를 때는 지수 차트가 좋아도 조심해야 합니다.")
with g_col3:
    st.info("**3. 버핏 지수 활용:** 지수 포인트보다 중요한 것은 밸류에이션입니다. 버핏 지수가 150%를 상회하면 장기적 하락에 대비하세요.")
