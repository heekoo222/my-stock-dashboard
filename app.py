import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 및 프리미엄 스타일 (Executive UI/UX)
st.set_page_config(page_title="GLOBAL STRATEGIC DASHBOARD 2026", layout="wide")

today_str = datetime.now().strftime("%Y-%m-%d")

st.markdown(f"""
    <style>
    [data-testid="stAppViewContainer"] {{ background-color: #fcfcfc; font-family: 'Inter', sans-serif; }}
    .date-badge {{ position: absolute; top: -50px; right: 10px; background-color: #f1f3f5; padding: 5px 15px; border-radius: 20px; font-size: 14px; font-weight: 600; color: #495057; border: 1px solid #dee2e6; }}
    .verdict-box {{ padding: 30px; border-radius: 20px; margin-bottom: 30px; border: 1px solid #efefef; position: relative; }}
    .positive-v {{ background: linear-gradient(135deg, #fff5f5 0%, #ffffff 100%); border-left: 10px solid #ff6b6b; color: #e03131; }}
    .neutral-v {{ background: linear-gradient(135deg, #fff9db 0%, #ffffff 100%); border-left: 10px solid #fab005; color: #f08c00; }}
    .negative-v {{ background: linear-gradient(135deg, #e7f5ff 0%, #ffffff 100%); border-left: 10px solid #228be6; color: #1971c2; }}
    .v-content {{ font-size: 34px; font-weight: 800; letter-spacing: -1.2px; line-height: 1.1; }}
    .info-card {{ background-color: #ffffff; padding: 22px; border-radius: 15px; border: 1px solid #f1f3f5; box-shadow: 0 4px 12px rgba(0,0,0,0.03); height: 100%; }}
    .card-title {{ font-size: 13px; font-weight: 700; color: #adb5bd; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }}
    .card-val {{ font-size: 26px; font-weight: 700; color: #212529; letter-spacing: -0.5px; }}
    .macro-section {{ background-color: #1a1c1e; padding: 40px; border-radius: 25px; margin-top: 50px; color: white; }}
    .situation-box {{ background-color: rgba(255,255,255,0.07); padding: 15px; border-radius: 10px; border-left: 4px solid #fab005; font-size: 13px; margin-top: 10px; line-height: 1.6; color: #ced4da; }}
    .buffett-appendix {{ background-color: rgba(255,255,255,0.1); padding: 25px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 30px;}}
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 엔진 (안정성 강화)
@st.cache_data(ttl=3600)
def load_data(ticker, start_date="2000-01-01"):
    try:
        df = yf.download(ticker, start=start_date, auto_adjust=True)
        if df.empty: return pd.DataFrame()
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
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_macro_trends():
    macros = {"US_Rate": "^TNX", "KR_Rate": "KR10YT=RR", "Oil": "CL=F", "Dollar": "DX-Y.NYB", "VIX": "^VIX", "SP500": "^GSPC", "KOSPI": "^KS11"}
    macro_res = {}
    for k, t in macros.items():
        try:
            d = yf.download(t, start="2010-01-01", auto_adjust=True)
            if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
            macro_res[k] = d['Close']
        except:
            macro_res[k] = pd.Series()
    return macro_res

# --- 데이터 로드 ---
indices = {"NASDAQ Composite": "^IXIC", "NASDAQ 100": "^NDX", "S&P 500": "^GSPC", "KOSPI": "^KS11", "KOSDAQ": "^KQ11"}
choice = st.sidebar.radio("📋 분석 대상 선택", list(indices.keys()))
data = load_data(indices[choice])
appendix_data = load_macro_trends()

# [오류 방지 로직] 데이터가 비어있는 경우 처리
if data.empty:
    st.error(f"⚠️ {choice} 데이터를 불러올 수 없습니다. 지수 코드를 확인하거나 잠시 후 다시 시도해주세요.")
    st.stop()

# 정상 데이터인 경우 분석 시작
last = data.iloc[-1]
curr, ma60, ma120, rsi = float(last['Close']), float(last['MA60']), float(last['MA120']), float(last['RSI'])
disp_120 = (curr / ma120) * 100

# 3. 버핏 지수 계산
def calc_global_buffett(sp_val, ks_val):
    if sp_val == 0 or ks_val == 0: return (0, "N/A"), (0, "N/A")
    us_ratio = (sp_val * 9.5 / 1000 / 28.5) * 100
    kr_ratio = (ks_val * 0.83 / 2450) * 100
    us_stat = "고평가" if us_ratio > 170 else ("저평가" if us_ratio < 110 else "적정")
    kr_stat = "고평가" if kr_ratio > 110 else ("저평가" if kr_ratio < 75 else "적정")
    return (us_ratio, us_stat), (kr_ratio, kr_stat)

sp_last = appendix_data['SP500'].iloc[-1] if not appendix_data['SP500'].empty else 0
ks_last = appendix_data['KOSPI'].iloc[-1] if not appendix_data['KOSPI'].empty else 0
(us_buff, us_stat), (kr_buff, kr_stat) = calc_global_buffett(sp_last, ks_last)

# 4. 상단: AI Investment Verdict
score = 0
if ma60 > ma120: score += 2
if rsi < 40: score += 2
elif rsi > 65: score -= 2
current_buff_stat = us_stat if any(x in choice for x in ["NASDAQ", "S&P"]) else kr_stat
if "저평가" in current_buff_stat: score += 1

if score >= 2: verdict, v_class = "긍정 (Buy / 적극 투자 권장)", "positive-v"
elif score <= -1: verdict, v_class = "부정 (Caution / 현금 비중 확대)", "negative-v"
else: verdict, v_class = "중립 (Neutral / 신중한 관망)", "neutral-v"

st.title(f"📊 {choice} 전략 보고서")
st.markdown(f'''<div class="verdict-box {v_class}"><div class="date-badge">기준 날짜: {today_str}</div><div style="font-size:12px; font-weight:700; opacity:0.7;">AI EXECUTIVE VERDICT (최종 투자 의견)</div><div class="v-content">{verdict}</div></div>''', unsafe_allow_html=True)

# 5. 지수 핵심 진단 카드
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="info-card"><div class="card-title">Trend (60/120)</div><div class="card-val">{"상승" if ma60 > ma120 else "하락"}</div><div class="card-caption">배열: <b>{"정배열" if ma60 > ma120 else "역배열"}</b></div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="info-card"><div class="card-title">이격도 (120MA)</div><div class="card-val">{disp_120:.1f}%</div><div class="card-caption">진단: <b>{"고평가 주의" if disp_120 > 110 else "안정적"}</b></div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="info-card"><div class="card-title">심리 지수 (RSI)</div><div class="card-val">{rsi:.1f}</div><div class="card-caption">심리: <b>{"탐욕" if rsi > 70 else ("공포" if rsi < 30 else "중립")}</b></div></div>', unsafe_allow_html=True)

# 6. 차트 영역 (5단계 탭)
st.markdown("---")
st.subheader("📅 Interactive Performance Report")
tabs = st.tabs(["6개월", "1년", "5년", "10년", "전체"])
days_map = {"6개월":132, "1년":252, "5년":1260, "10년":2520}

def render_chart(df_sub, p_name):
    start_p, end_p = float(df_sub['Close'].iloc[0]), float(df_sub['Close'].iloc[-1])
    ret = ((end_p - start_p) / start_p) * 100
    days = (df_sub.index[-1] - df_sub.index[0]).days
    cagr = (((end_p / start_p) ** (365 / (days if days > 0 else 1))) - 1) * 100
    
    col1, col2 = st.columns(2)
    col1.metric(f"{p_name} 수익률", f"{ret:.2f}%")
    col2.metric(f"{p_name} CAGR", f"{cagr:.2f}%")
    
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_sub.index, open=df_sub['Open'], high=df_sub['High'], low=df_sub['Low'], close=df_sub['Close'], name="주가", opacity=0.4))
    ma_styles = {5: '#FF0000', 20: '#FFD700', 60: '#008000', 120: '#0000FF', 240: '#800080', 480: '#4B4B4B'}
    for d, color in ma_styles.items():
        if f'MA{d}' in df_sub.columns:
            fig.add_trace(go.Scatter(x=df_sub.index, y=df_sub[f'MA{d}'], name=f'{d}일선', line=dict(color=color, width=1.5)))
    
    fig.update_layout(height=500, template="plotly_white", xaxis_rangeslider_visible=False, dragmode='pan', hovermode='x unified', margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[df_sub.index.min(), df_sub.index.max()]))
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

for i, name in enumerate(["6개월", "1년", "5년", "10년", "전체"]):
    with tabs[i]:
        d_count = days_map.get(name, len(data))
        render_chart(data.iloc[-d_count:], name)

# 7. 하단 부록: Macro & Buffett
st.markdown('<div class="macro-section"><h2>📎 부록: 글로벌 매크로 및 밸류에이션</h2>', unsafe_allow_html=True)
st.markdown('<div class="buffett-appendix">### 🏛️ Buffett Index (시총/GDP)  \n' + f'**미국:** {us_buff:.1f}% ({us_stat}) | **한국:** {kr_buff:.1f}% ({kr_stat})</div>', unsafe_allow_html=True)

macro_tabs = st.tabs(["1년", "5년", "10년"])
m_days = {"1년": 252, "5년": 1260, "10년": 2520}

def get_logic(name, series):
    if series.empty: return "데이터 없음"
    curr_v, prev_v = series.iloc[-1], series.iloc[-22]
    diff = curr_v - prev_v
    if name == "US_Rate": return f"금리 {curr_v:.2f}% ({diff:+.2f}%). 금리 상승 시 기술주 하락 압력."
    elif name == "Oil": return f"유가 ${curr_v:.2f}. 고유가는 인플레이션 자극 요인."
    elif name == "Dollar": return f"달러 {curr_v:.2f}. 강달러 시 외국인 자금 유출 위험."
    else: return f"VIX {curr_v:.2f}. 20 이상 시 시장 공포 확산."

for i, t_name in enumerate(["1년", "5년", "10년"]):
    with macro_tabs[i]:
        d = m_days[t_name]
        m1, m2 = st.columns(2); m3, m4 = st.columns(2)
        with m1: 
            fig = go.Figure(go.Scatter(x=appendix_data['US_Rate'].index[-d:], y=appendix_data['US_Rate'].values[-d:], line=dict(color='#ff6b6b')))
            fig.update_layout(height=200, title="미 국채 10년 금리", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            st.caption(get_logic("US_Rate", appendix_data['US_Rate']))
        with m2: 
            fig = go.Figure(go.Scatter(x=appendix_data['Oil'].index[-d:], y=appendix_data['Oil'].values[-d:], line=dict(color='#adb5bd')))
            fig.update_layout(height=200, title="WTI 유가", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            st.caption(get_logic("Oil", appendix_data['Oil']))
        with m3:
            fig = go.Figure(go.Scatter(x=appendix_data['Dollar'].index[-d:], y=appendix_data['Dollar'].values[-d:], line=dict(color='#4dadf7')))
            fig.update_layout(height=200, title="달러 인덱스", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            st.caption(get_logic("Dollar", appendix_data['Dollar']))
        with m4:
            fig = go.Figure(go.Scatter(x=appendix_data['VIX'].index[-d:], y=appendix_data['VIX'].values[-d:], line=dict(color='#fab005')))
            fig.update_layout(height=200, title="VIX 공포지수", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            st.caption(get_logic("VIX", appendix_data['VIX']))
st.markdown('</div>', unsafe_allow_html=True)
