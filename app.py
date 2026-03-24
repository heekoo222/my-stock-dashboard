import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 및 프리미엄 디자인 UI
st.set_page_config(page_title="EXECUTIVE MARKET MONITOR", layout="wide")

# 디자이너급 UI/UX 스타일 정의
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #fcfcfc; font-family: 'Inter', sans-serif; }
    [data-testid="stHeader"] { background-color: rgba(252, 252, 252, 0); }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #eee; }
    
    /* Executive Verdict Card */
    .verdict-box { padding: 30px; border-radius: 20px; margin-bottom: 30px; border: 1px solid #efefef;}
    .positive-v { background: linear-gradient(135deg, #fff5f5 0%, #ffffff 100%); border-left: 10px solid #ff6b6b; color: #e03131; }
    .neutral-v { background: linear-gradient(135deg, #fff9db 0%, #ffffff 100%); border-left: 10px solid #fab005; color: #f08c00; }
    .negative-v { background: linear-gradient(135deg, #e7f5ff 0%, #ffffff 100%); border-left: 10px solid #228be6; color: #1971c2; }
    .v-title { font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 8px; opacity: 0.7;}
    .v-content { font-size: 34px; font-weight: 800; letter-spacing: -1.2px; line-height: 1.1; }
    
    /* Indicator Card */
    .info-card { background-color: #ffffff; padding: 22px; border-radius: 15px; border: 1px solid #f1f3f5; box-shadow: 0 4px 12px rgba(0,0,0,0.03); height: 100%; }
    .card-title { font-size: 12px; font-weight: 700; color: #adb5bd; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }
    .card-val { font-size: 26px; font-weight: 700; color: #212529; letter-spacing: -0.5px; }
    .card-caption { font-size: 13px; color: #868e96; margin-top: 8px; line-height: 1.4; }
    
    /* Tabs Customizing */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f1f3f5; border-radius: 8px; padding: 8px 20px; color: #495057; font-size: 14px; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background-color: #228be6 !important; color: white !important; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 인프라 구축 (에러 수정: G/D 신호 계산 포함)
@st.cache_data(ttl=3600)
def load_full_data(ticker):
    df = yf.download(ticker, start="2000-01-01")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 이동평균선
    for m in [5, 20, 60, 120, 240]:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    
    # [에러 해결 부위] 신호 데이터 생성
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
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    return df.dropna(subset=['MA240'])

# --- 사이드바 및 데이터 세팅 ---
st.sidebar.markdown("### 🏛️ MARKET SELECTION")
indices = {
    "NASDAQ (Composite)": "^IXIC", "NASDAQ 100 (Tech)": "^NDX", 
    "S&P 500 (US Large)": "^GSPC", "KOSPI (Korea)": "^KS11", "KOSDAQ (Korea)": "^KQ11"
}
choice = st.sidebar.radio("Select Benchmark", list(indices.keys()))
data = load_full_data(indices[choice])

# 실시간 분석 데이터 추출
last = data.iloc[-1]
curr, ma60, ma120 = float(last['Close']), float(last['MA60']), float(last['MA120'])
rsi, macd, signal = float(last['RSI']), float(last['MACD']), float(last['Signal_Line'])
disp_120 = (curr / ma120) * 100

# AI 스코어링 결론 도출
score = 0
if ma60 > ma120: score += 2
else: score -= 2
if rsi < 38: score += 2
elif rsi > 62: score -= 2
if macd > signal: score += 1
else: score -= 1

if score >= 2: verdict, v_class = "긍정 (적극적 투자 권장)", "positive-v"
elif score <= -2: verdict, v_class = "부정 (보수적 대응 권장)", "negative-v"
else: verdict, v_class = "중립 (시장 관망 필요)", "neutral-v"

# --- 메인 대시보드 뷰 ---
st.title(f"{choice} Executive Intelligence")

# 1. 최상단 Executive Verdict
st.markdown(f'''
    <div class="verdict-box {v_class}">
        <div class="v-title">Investment Verdict for Today</div>
        <div class="v-content">{verdict}</div>
    </div>
''', unsafe_allow_html=True)

# 2. 핵심 요약 카드 4종
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="info-card"><div class="card-title">Trend Status</div><div class="card-val">{"Bullish" if ma60 > ma120 else "Bearish"}</div><div class="card-caption">60/120 이평선 정배열 여부</div></div>', unsafe_allow_html=True)
with c2:
    energy_gap = abs(ma60 - ma120) / ma120 * 100
    st.markdown(f'<div class="info-card"><div class="card-title">Market Energy</div><div class="card-val">{"Converged" if energy_gap < 2.5 else "Diverged"}</div><div class="card-caption">이평선 수렴을 통한 변동성 진단</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="info-card"><div class="card-title">Sentiment (RSI)</div><div class="card-val">{rsi:.1f}</div><div class="card-caption">시장 과열 및 바닥권 진단</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="info-card"><div class="card-title">Mean Reversion</div><div class="card-val">{disp_120:.1f}%</div><div class="card-caption">120일 평균선 대비 이격률</div></div>', unsafe_allow_html=True)

# 3. 성과 분석 및 차트
st.markdown("---")
st.subheader("📊 Performance Analysis & Interactive Chart")
tabs = st.tabs(["3개월", "6개월", "1년", "3년", "전체"])

def render_analysis(df_sub, p_name):
    # 성과 지표 산출
    s_p, e_p = float(df_sub['Close'].iloc[0]), float(df_sub['Close'].iloc[-1])
    ret = ((e_p - s_p) / s_p) * 100
    days = (df_sub.index[-1] - df_sub.index[0]).days
    cagr = (((e_p / s_p) ** (365 / days)) - 1) * 100 if days > 0 else 0
    
    m_col1, m_col2 = st.columns(2)
    m_col1.metric(f"{p_name} 실질 수익률", f"{ret:.2f}%")
    m_col2.metric(f"{p_name} 연평균 성장률(CAGR)", f"{cagr:.2f}%")

    # 전문가용 클린 차트
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_sub.index, open=df_sub['Open'], high=df_sub['High'], 
                                 low=df_sub['Low'], close=df_sub['Close'], name="Price", opacity=0.4))
    
    for d, c in {60:'#5c7cfa', 120:'#228be6', 240:'#868e96'}.items():
        if f'MA{d}' in df_sub.columns:
            fig.add_trace(go.Scatter(x=df_sub.index, y=df_sub[f'MA{d}'], name=f'{d}MA', line=dict(color=c, width=2 if d != 240 else 1.2)))
    
    # 골든/데드 마커 표시
    cross_data = data.loc[df_sub.index[0]:df_sub.index[-1]]
    gs, ds = cross_data[cross_data['G']], cross_data[cross_data['D']]
    fig.add_trace(go.Scatter(x=gs.index, y=gs['MA60'], mode='markers', marker=dict(symbol='triangle-up', size=12, color='#fa5252'), name='Golden'))
    fig.add_trace(go.Scatter(x=ds.index, y=ds['MA60'], mode='markers', marker=dict(symbol='triangle-down', size=12, color='#1c7ed6'), name='Death'))
    
    fig.update_layout(height=550, template="plotly_white", xaxis_rangeslider_visible=False, dragmode='pan', margin=dict(l=0, r=0, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

with tabs[0]: render_analysis(data.iloc[-60:], "3개월")
with tabs[1]: render_analysis(data.iloc[-125:], "6개월")
with tabs[2]: render_analysis(data.iloc[-250:], "1년")
with tabs[3]: render_analysis(data.iloc[-750:], "3년")
with tabs[4]: render_analysis(data, "전체")

# 4. 하단 가이드라인 (Footnotes)
st.markdown("""
    <div style="background-color: #1a1b1e; padding: 30px; border-radius: 15px; color: #ced4da; margin-top: 40px;">
        <h4 style="color: white; margin-bottom: 20px;">💡 Investment Reference Guidelines</h4>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px;">
            <div><b style="color: #fab005;">Mean Reversion</b><br><span style="font-size: 13px; opacity: 0.8;">주가는 120일선 이격률 115% 이상 시 하락 가능성, 85% 이하 시 반등 가능성이 높습니다.</span></div>
            <div><b style="color: white;">Trend Analysis</b><br><span style="font-size: 13px; opacity: 0.8;">60일선이 120일선 위에 있는 정배열 상태에서만 매수 우위 전략을 유지합니다.</span></div>
            <div><b style="color: #fab005;">Energy Convergence</b><br><span style="font-size: 13px; opacity: 0.8;">이평선 수렴 이후에는 거대 변동성이 발생합니다. RSI 지표와 함께 방향성을 예측합니다.</span></div>
            <div><b style="color: white;">Reverse Cross</b><br><span style="font-size: 13px; opacity: 0.8;">골든크로스 시점에 이격률이 높다면 오히려 단기 고점으로 판단하는 역발상이 필요합니다.</span></div>
        </div>
    </div>
""", unsafe_allow_html=True)
