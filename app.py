import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 및 프리미엄 스타일 시트
st.set_page_config(page_title="EXECUTIVE MARKET INTELLIGENCE 2026", layout="wide")

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
    .situation-box { background-color: rgba(255,255,255,0.07); padding: 15px; border-radius: 10px; border-left: 4px solid #fab005; font-size: 13px; margin-top: 10px; line-height: 1.6; color: #ced4da; }
    .buffett-appendix { background-color: rgba(255,255,255,0.1); padding: 25px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 30px;}
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 엔진 (지수 및 매크로 통합 로드)
@st.cache_data(ttl=3600)
def load_all_market_intelligence(ticker):
    # 지수 데이터
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
    
    # 매크로/부록 데이터 (금리, 유가, 달러, VIX, 버핏지수용 S&P/KOSPI)
    macros = {"US_Rate": "^TNX", "KR_Rate": "KR10YT=RR", "Oil": "CL=F", "Dollar": "DX-Y.NYB", "VIX": "^VIX", "SP500": "^GSPC", "KOSPI": "^KS11"}
    macro_res = {}
    for k, t in macros.items():
        d = yf.download(t, start="2022-01-01")
        if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
        macro_res[k] = d['Close']
        
    return df.dropna(subset=['MA240']), macro_res

# --- 데이터 준비 ---
indices = {"NASDAQ Composite": "^IXIC", "NASDAQ 100": "^NDX", "S&P 500": "^GSPC", "KOSPI": "^KS11", "KOSDAQ": "^KQ11"}
choice = st.sidebar.radio("Select Asset", list(indices.keys()))
data, appendix_data = load_all_market_intelligence(indices[choice])

last = data.iloc[-1]
curr, ma60, ma120, rsi = float(last['Close']), float(last['MA60']), float(last['MA120']), float(last['RSI'])
disp_120 = (curr / ma120) * 100

# 3. 버핏 지수 전용 계산 (US & KR 비교용)
def calc_global_buffett(sp_val, ks_val):
    # US GDP 2026: 28.5T, Multiplier 9.5 / KR GDP: 2450T, Multiplier 0.83
    us_ratio = (sp_val * 9.5 / 1000 / 28.5) * 100
    kr_ratio = (ks_val * 0.83 / 2450) * 100
    us_stat = "Overvalued" if us_ratio > 170 else ("Undervalued" if us_ratio < 110 else "Fair Value")
    kr_stat = "Overvalued" if kr_ratio > 110 else ("Undervalued" if kr_ratio < 75 else "Fair Value")
    return (us_ratio, us_stat), (kr_ratio, kr_stat)

(us_buff, us_stat), (kr_buff, kr_stat) = calc_global_buffett(appendix_data['SP500'].iloc[-1], appendix_data['KOSPI'].iloc[-1])

# 4. 상단: Executive Verdict
score = 0
if ma60 > ma120: score += 2
if rsi < 40: score += 2
elif rsi > 65: score -= 2
# 현재 선택한 지수의 국가별 버핏지수 상태 반영
current_buff_stat = us_stat if any(x in choice for x in ["NASDAQ", "S&P"]) else kr_stat
if current_buff_stat == "Undervalued": score += 1

if score >= 2: verdict, v_class = "긍정 (적극 투자 권장)", "positive-v"
elif score <= -1: verdict, v_class = "부정 (보수적 대응 권장)", "negative-v"
else: verdict, v_class = "중립 (시장 관망 필요)", "neutral-v"

st.title(f"Market Intelligence: {choice}")
st.markdown(f'''<div class="verdict-box {v_class}"><div style="font-size:12px; font-weight:700; opacity:0.7;">EXECUTIVE VERDICT</div><div class="v-content">{verdict}</div></div>''', unsafe_allow_html=True)

# 5. 중단: 지수 핵심 진단 카드 (3종)
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="info-card"><div class="card-title">Trend (60/120)</div><div class="card-val">{"Bullish" if ma60 > ma120 else "Bearish"}</div><div class="card-caption">배열: <b>{"정배열" if ma60 > ma120 else "역배열"}</b></div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="info-card"><div class="card-title">Mean Reversion</div><div class="card-val">{disp_120:.1f}%</div><div class="card-caption">진단: <b>{"고평가 주의" if disp_120 > 110 else "안정적"}</b></div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="info-card"><div class="card-title">Sentiment (RSI)</div><div class="card-val">{rsi:.1f}</div><div class="card-caption">심리: <b>{"탐욕" if rsi > 70 else ("공포" if rsi < 30 else "중립")}</b></div></div>', unsafe_allow_html=True)

# 6. 차트 영역: 8단계 탭 및 고대비 이평선 색상
st.markdown("---")
st.subheader("📅 Interactive Performance Report")
tabs = st.tabs(["7일", "1개월", "3개월", "6개월", "1년", "3년", "5년", "10년"])
days_map = {"7일":7, "1개월":22, "3개월":66, "6개월":132, "1년":252, "3년":756, "5년":1260, "10년":2520}

def render_analysis_chart(df_sub, p_name):
    # 수익률 및 CAGR
    start_p, end_p = float(df_sub['Close'].iloc[0]), float(df_sub['Close'].iloc[-1])
    ret = ((end_p - start_p) / start_p) * 100
    days = (df_sub.index[-1] - df_sub.index[0]).days
    cagr = (((end_p / start_p) ** (365 / days)) - 1) * 100 if days > 0 else 0
    
    col_m1, col_m2 = st.columns(2)
    col_m1.metric(f"{p_name} 실질 수익률", f"{ret:.2f}%")
    col_m2.metric(f"{p_name} 연평균 수익률(CAGR)", f"{cagr:.2f}%")
    
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_sub.index, open=df_sub['Open'], high=df_sub['High'], low=df_sub['Low'], close=df_sub['Close'], name="주가", opacity=0.4))
    
    # [수정] 이평선 색상 최적화 (가독성 증대)
    ma_styles = {
        5: {'color': '#FF0000', 'name': '5일(단기)'}, 
        20: {'color': '#FFD700', 'name': '20일(심리)'}, 
        60: {'color': '#008000', 'name': '60일(수급)'}, 
        120: {'color': '#0000FF', 'name': '120일(경기)'}, 
        240: {'color': '#800080', 'name': '240일(대세)'}, 
        480: {'color': '#4B4B4B', 'name': '480일(장기)'}
    }
    
    for d, style in ma_styles.items():
        if f'MA{d}' in df_sub.columns:
            fig.add_trace(go.Scatter(x=df_sub.index, y=df_sub[f'MA{d}'], name=style['name'], line=dict(color=style['color'], width=1.8 if d != 480 else 1.2)))
    
    gs, ds = df_sub[df_sub['G']], df_sub[df_sub['D']]
    fig.add_trace(go.Scatter(x=gs.index, y=gs['MA60'], mode='markers', marker=dict(symbol='triangle-up', size=12, color='#FF0000'), name='Golden'))
    fig.add_trace(go.Scatter(x=ds.index, y=ds['MA60'], mode='markers', marker=dict(symbol='triangle-down', size=12, color='#0000FF'), name='Death'))

    fig.update_layout(height=500, template="plotly_white", xaxis_rangeslider_visible=False, dragmode='pan', margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

for i, (name, d) in enumerate(days_map.items()):
    with tabs[i]: render_analysis_chart(data.iloc[-d:], name)

# 7. 하단 부록: Buffett Index & Macro Pulse
st.markdown('<div class="macro-section"><h2>📎 Appendix: Global Macro & Valuation Analysis</h2>', unsafe_allow_html=True)

# [수정] 버핏 지수 부록 통합 (미국 vs 한국)
st.markdown('<div class="buffett-appendix">', unsafe_allow_html=True)
st.markdown("### 🏛️ Global Buffett Indicators (Market Cap to GDP)")
b_col1, b_col2 = st.columns(2)
with b_col1:
    st.markdown(f"**United States**")
    st.markdown(f"Value: <span style='font-size:28px; font-weight:bold;'>{us_buff:.1f}%</span> (Status: **{us_stat}**)", unsafe_allow_html=True)
    st.caption("Benchmark: S&P 500 Est. Cap / US GDP 28.5T")
with b_col2:
    st.markdown(f"**South Korea**")
    st.markdown(f"Value: <span style='font-size:28px; font-weight:bold;'>{kr_buff:.1f}%</span> (Status: **{kr_stat}**)", unsafe_allow_html=True)
    st.caption("Benchmark: KOSPI Est. Cap / KR GDP 2450T")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
# 매크로 차트 및 시나리오 진단
m1, m2 = st.columns(2)
m3, m4 = st.columns(2)

def get_macro_situation(name, series):
    curr_v, prev_v = series.iloc[-1], series.iloc[-22]
    diff = curr_v - prev_v
    if name == "US_Rate": return f"미 10년물 금리 {curr_v:.2f}% ({diff:+.2f}%). 금리 급등 시 기술주 할인율 적용으로 하락 압력 가중."
    elif name == "Oil": return f"WTI 유가 ${curr_v:.2f}. 85불 상회 시 인플레이션 우려로 긴축 기조 장기화 가능성."
    elif name == "Dollar": return f"달러 인덱스 {curr_v:.2f}. 강달러 지속 시 외국인 자금 유출로 KOSPI 하방 압력."
    else: return f"VIX 지수 {curr_v:.2f}. 20 이하 안정적이나, 저점에서 반등 시 시장 패닉 셀링 주의."

def render_macro_appendix(series, title, color, m_name):
    fig = go.Figure(go.Scatter(x=series.index[-250:], y=series.values[-250:], mode='lines', line=dict(color=color, width=2.5)))
    fig.update_layout(height=220, title=title, template="plotly_dark", margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f'<div class="situation-box"><b>🕵️ Situation Analysis:</b><br>{get_macro_situation(m_name, series)}</div>', unsafe_allow_html=True)

with m1: render_macro_appendix(appendix_data['US_Rate'], "US 10Y Yield", "#ff6b6b", "US_Rate")
with m2: render_macro_appendix(appendix_data['Oil'], "WTI Crude Oil", "#adb5bd", "Oil")
with m3: render_macro_appendix(appendix_data['Dollar'], "Dollar Index", "#4dadf7", "Dollar")
with m4: render_macro_appendix(appendix_data['VIX'], "VIX (Fear Index)", "#fab005", "VIX")
st.markdown('</div>', unsafe_allow_html=True)

# 8. 투자 가이드북
st.markdown("---")
st.subheader("📖 Strategic Investment Guidelines")
g1, g2, g3 = st.columns(3)
with g1: st.info("**1. Mean Reversion:** 이격률 110% 이상 시 하락 조정 경계, 90% 이하 시 바닥권 매수 검토.")
with g2: st.info("**2. Macro Correlation:** 금리와 달러가 동시에 오를 때는 지수 차트가 좋아도 조심해야 합니다.")
with g3: st.info("**3. Buffett Index:** 부록의 국가별 버핏 지수가 150%를 넘으면 역사적으로 '비싼' 시장입니다.")
