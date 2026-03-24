import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 및 프리미엄 스타일 시트 (Executive & Human-Centric UI)
st.set_page_config(page_title="GLOBAL STRATEGIC DASHBOARD 2026", layout="wide")

# 오늘 날짜 가져오기
today_str = datetime.now().strftime("%Y-%m-%d")

st.markdown(f"""
    <style>
    /* 전체 배경 및 폰트 */
    [data-testid="stAppViewContainer"] {{ background-color: #fcfcfc; font-family: 'Inter', -apple-system, sans-serif; }}
    
    /* 우측 상단 날짜 배지 */
    .date-badge {{
        position: absolute; top: -50px; right: 10px;
        background-color: #f1f3f5; padding: 5px 15px; border-radius: 20px;
        font-size: 14px; font-weight: 600; color: #495057; border: 1px solid #dee2e6;
    }}

    /* 최종 투자 의견 (Verdict) 디자인 */
    .verdict-box {{ padding: 30px; border-radius: 20px; margin-bottom: 30px; border: 1px solid #efefef; position: relative; }}
    .positive-v {{ background: linear-gradient(135deg, #fff5f5 0%, #ffffff 100%); border-left: 10px solid #ff6b6b; color: #e03131; }}
    .neutral-v {{ background: linear-gradient(135deg, #fff9db 0%, #ffffff 100%); border-left: 10px solid #fab005; color: #f08c00; }}
    .negative-v {{ background: linear-gradient(135deg, #e7f5ff 0%, #ffffff 100%); border-left: 10px solid #228be6; color: #1971c2; }}
    .v-content {{ font-size: 34px; font-weight: 800; letter-spacing: -1.2px; line-height: 1.1; }}
    
    /* 정보 카드 UI */
    .info-card {{ background-color: #ffffff; padding: 22px; border-radius: 15px; border: 1px solid #f1f3f5; box-shadow: 0 4px 12px rgba(0,0,0,0.03); height: 100%; }}
    .card-title {{ font-size: 13px; font-weight: 700; color: #adb5bd; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }}
    .card-val {{ font-size: 26px; font-weight: 700; color: #212529; letter-spacing: -0.5px; }}
    .card-analysis {{ font-size: 13px; color: #495057; margin-top: 10px; line-height: 1.5; padding: 10px; background: #f8f9fa; border-radius: 8px; }}

    /* 부록 및 가이드 섹션 */
    .macro-section {{ background-color: #1a1c1e; padding: 40px; border-radius: 25px; margin-top: 50px; color: white; }}
    .situation-box {{ background-color: rgba(255,255,255,0.07); padding: 15px; border-radius: 10px; border-left: 4px solid #fab005; font-size: 13px; margin-top: 10px; line-height: 1.6; color: #ced4da; }}
    .buffett-appendix {{ background-color: rgba(255,255,255,0.1); padding: 25px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 30px;}}
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 사이언스 엔진
@st.cache_data(ttl=3600)
def load_all_market_intelligence(ticker):
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
    
    # 매크로/부록 데이터
    macros = {"US_Rate": "^TNX", "KR_Rate": "KR10YT=RR", "Oil": "CL=F", "Dollar": "DX-Y.NYB", "VIX": "^VIX", "SP500": "^GSPC", "KOSPI": "^KS11"}
    macro_res = {}
    for k, t in macros.items():
        d = yf.download(t, start="2022-01-01")
        if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
        macro_res[k] = d['Close']
    return df.dropna(subset=['MA240']), macro_res

# --- 데이터 로드 ---
indices = {"NASDAQ Composite": "^IXIC", "NASDAQ 100": "^NDX", "S&P 500": "^GSPC", "KOSPI": "^KS11", "KOSDAQ": "^KQ11"}
choice = st.sidebar.radio("📋 분석 대상 선택", list(indices.keys()))
data, appendix_data = load_all_market_intelligence(indices[choice])

last = data.iloc[-1]
curr, ma60, ma120, rsi = float(last['Close']), float(last['MA60']), float(last['MA120']), float(last['RSI'])
disp_120 = (curr / ma120) * 100

# 3. 버핏 지수 전용 계산 (US & KR)
def calc_global_buffett(sp_val, ks_val):
    us_ratio = (sp_val * 9.5 / 1000 / 28.5) * 100
    kr_ratio = (ks_val * 0.83 / 2450) * 100
    us_stat = "고평가(주의)" if us_ratio > 170 else ("저평가(기회)" if us_ratio < 110 else "적정 가치")
    kr_stat = "고평가(주의)" if kr_ratio > 110 else ("저평가(기회)" if kr_ratio < 75 else "적정 가치")
    return (us_ratio, us_stat), (kr_ratio, kr_stat)

(us_buff, us_stat), (kr_buff, kr_stat) = calc_global_buffett(appendix_data['SP500'].iloc[-1], appendix_data['KOSPI'].iloc[-1])

# 4. 상단 섹션: AI Investment Verdict & Date Badge
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
st.markdown(f'''
    <div class="verdict-box {v_class}">
        <div class="date-badge">기준 날짜: {today_str}</div>
        <div style="font-size:12px; font-weight:700; opacity:0.7;">AI EXECUTIVE VERDICT (최종 투자 의견)</div>
        <div class="v-content">{verdict}</div>
    </div>
''', unsafe_allow_html=True)

# 5. 중단 섹션: 지표 카드 (한글 병기 및 수치 해석)
st.subheader("🔍 핵심 지표 진단 (Strategic Diagnosis)")
c1, c2, c3 = st.columns(3)
with c1:
    trend_status = "상승 정배열" if ma60 > ma120 else "하락 역배열"
    st.markdown(f'''<div class="info-card"><div class="card-title">Trend - 이평선 추이</div><div class="card-val">{trend_status}</div>
    <div class="card-analysis"><b>해석:</b> 현재 60일선이 120일선 {"위에" if ma60 > ma120 else "아래에"} 있는 {trend_status} 상태입니다. 시장의 기초 체력이 {"상승세를 지지하고" if ma60 > ma120 else "약화되어 주의가 필요한"} 구간입니다.</div></div>''', unsafe_allow_html=True)
with c2:
    st.markdown(f'''<div class="info-card"><div class="card-title">Mean Reversion - 이격도</div><div class="card-val">{disp_120:.1f}%</div>
    <div class="card-analysis"><b>해석:</b> 120일 평균선 대비 위치입니다. {"110% 이상으로 고평가되어 조정이 우려됩니다." if disp_120 > 110 else ("90% 이하로 저평가되어 반등이 기대됩니다." if disp_120 < 90 else "평균선 근처에서 안정적인 흐름입니다.")}</div></div>''', unsafe_allow_html=True)
with c3:
    st.markdown(f'''<div class="info-card"><div class="card-title">Sentiment - 심리 지수(RSI)</div><div class="card-val">{rsi:.1f}</div>
    <div class="card-analysis"><b>해석:</b> 투자자 심리입니다. 현재 {rsi:.1f}로 {"과매수(탐욕) 상태로 조정 주의가 필요합니다." if rsi > 70 else ("과매도(공포) 상태로 매수 기회를 검토하세요." if rsi < 30 else "매수/매도가 균형을 이룬 중립 상태입니다.")}</div></div>''', unsafe_allow_html=True)

# 6. 차트 영역: 8단계 기간 탭 및 수익률(CAGR)
st.markdown("---")
st.subheader("📅 기간별 성과 분석 (Performance Report)")
tabs = st.tabs(["7일", "1개월", "3개월", "6개월", "1년", "3년", "5년", "10년"])
days_map = {"7일":7, "1개월":22, "3개월":66, "6개월":132, "1년":252, "3년":756, "5년":1260, "10년":2520}

def render_analysis_chart(df_sub, p_name):
    start_p, end_p = float(df_sub['Close'].iloc[0]), float(df_sub['Close'].iloc[-1])
    ret = ((end_p - start_p) / start_p) * 100
    days = (df_sub.index[-1] - df_sub.index[0]).days
    cagr = (((end_p / start_p) ** (365 / (days if days > 0 else 1))) - 1) * 100
    
    col_m1, col_m2 = st.columns(2)
    col_m1.metric(f"{p_name} 실질 수익률", f"{ret:.2f}%")
    col_m2.metric(f"{p_name} 연평균 수익률 (CAGR)", f"{cagr:.2f}%")
    
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_sub.index, open=df_sub['Open'], high=df_sub['High'], low=df_sub['Low'], close=df_sub['Close'], name="주가", opacity=0.4))
    ma_styles = {5: '#FF0000', 20: '#FFD700', 60: '#008000', 120: '#0000FF', 240: '#800080', 480: '#4B4B4B'}
    for d, color in ma_styles.items():
        if f'MA{d}' in df_sub.columns:
            fig.add_trace(go.Scatter(x=df_sub.index, y=df_sub[f'MA{d}'], name=f'{d}일선', line=dict(color=color, width=1.8 if d != 480 else 1.2)))
    
    gs, ds = df_sub[df_sub['G']], df_sub[df_sub['D']]
    fig.add_trace(go.Scatter(x=gs.index, y=gs['MA60'], mode='markers', marker=dict(symbol='triangle-up', size=12, color='#FF0000'), name='Golden Cross'))
    fig.add_trace(go.Scatter(x=ds.index, y=ds['MA60'], mode='markers', marker=dict(symbol='triangle-down', size=12, color='#0000FF'), name='Dead Cross'))

    fig.update_layout(height=500, template="plotly_white", xaxis_rangeslider_visible=False, dragmode='pan', margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

for i, (name, d) in enumerate(days_map.items()):
    with tabs[i]: render_performance_chart = render_analysis_chart(data.iloc[-d:], name)

# 7. 하단 부록: Global Macro & Buffett Index
st.markdown('<div class="macro-section"><h2>📎 부록: 글로벌 매크로 및 밸류에이션 분석 (Appendix)</h2>', unsafe_allow_html=True)

st.markdown('<div class="buffett-appendix">', unsafe_allow_html=True)
st.markdown("### 🏛️ Buffett Index - 국가별 버핏 지수 (시총/GDP)")
b_col1, b_col2 = st.columns(2)
with b_col1:
    st.markdown(f"**미국 (US Market)**: <span style='font-size:28px;'>{us_buff:.1f}%</span> (상태: **{us_stat}**)", unsafe_allow_html=True)
    st.caption("설명: GDP 대비 주식 비중. 170% 이상 시 역사적 고평가(버블)를 경고합니다.")
with b_col2:
    st.markdown(f"**한국 (KR Market)**: <span style='font-size:28px;'>{kr_buff:.1f}%</span> (상태: **{kr_stat}**)", unsafe_allow_html=True)
    st.caption("설명: 한국 시장은 보통 75~100% 사이에서 박스권을 형성합니다.")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
m1, m2 = st.columns(2); m3, m4 = st.columns(2)

def get_macro_situation(name, series):
    curr_v, prev_v = series.iloc[-1], series.iloc[-22]
    diff = curr_v - prev_v
    if name == "US_Rate": return f"미 10년물 금리 {curr_v:.2f}% ({diff:+.2f}%). 금리 상승 시 기업 할인율이 높아져 주가에 하방 압력을 줍니다."
    elif name == "Oil": return f"WTI 유가 ${curr_v:.2f}. 고유가는 물가 상승을 자극하여 금리 인하 시점을 늦추는 요인이 됩니다."
    elif name == "Dollar": return f"달러 인덱스 {curr_v:.2f}. 달러 강세 시 외국인 자금 이탈로 국내 증시의 탄력이 줄어듭니다."
    else: return f"VIX(공포지수) {curr_v:.2f}. 20 이하 안정적이나, 최근 {diff:+.2f}포인트 변화하며 시장 심리를 반영 중입니다."

def render_macro_appendix(series, title, color, m_name):
    fig = go.Figure(go.Scatter(x=series.index[-250:], y=series.values[-250:], mode='lines', line=dict(color=color, width=2.5)))
    fig.update_layout(height=220, title=title, template="plotly_dark", margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f'<div class="situation-box"><b>🕵️ 현재 상황 진단:</b><br>{get_macro_situation(m_name, series)}</div>', unsafe_allow_html=True)

with m1: render_macro_appendix(appendix_data['US_Rate'], "US 10Y Yield (미 국채 금리)", "#ff6b6b", "US_Rate")
with m2: render_macro_appendix(appendix_data['Oil'], "WTI Crude Oil (서부 텍사스산 원유)", "#adb5bd", "Oil")
with m3: render_macro_appendix(appendix_data['Dollar'], "Dollar Index (달러 인덱스)", "#4dadf7", "Dollar")
with m4: render_macro_appendix(appendix_data['VIX'], "VIX (공포 지수)", "#fab005", "VIX")
st.markdown('</div>', unsafe_allow_html=True)

# 8. 초보자를 위한 통합 마스터 가이드
st.markdown("---")
with st.expander("🐣 **초보자 통합 가이드: 대시보드 지표 마스터하기 (클릭)**"):
    st.markdown("""
    ### 1. 지수 추세 (Trend) - '달리는 말인가?'
    - **정배열:** 단기선이 장기선보다 위. 추세가 살아있어 '떨어지면 매수'가 유리합니다.
    - **역배열:** 단기선이 장기선보다 아래. 추세가 꺾여 '오르면 매도'가 유리합니다.
    

    ### 2. 이격도 (Mean Reversion) - '집에서 얼마나 멀어졌나?'
    - 주가는 결국 120일선(평균선)으로 돌아오려는 성질이 있습니다. 110%를 넘으면 너무 비싼 고점, 90% 아래면 너무 싼 바닥일 확률이 높습니다.
    

    ### 3. 심리 지수 (RSI) - '과열인가 공포인가?'
    - **70 이상:** 다들 환호할 때(탐욕). 이때는 조심해야 합니다.
    - **30 이하:** 다들 도망갈 때(공포). 이때가 좋은 매수 기회일 수 있습니다.
    

    ### 4. 버핏 지수 (Buffett Index) - '시장 전체가 싼가 비싼가?'
    - 시가총액을 GDP와 비교합니다. 주식 가격뿐만 아니라 경제 전체 크기 대비 거품이 끼었는지 판단하는 장기 지표입니다.
    
    """)
