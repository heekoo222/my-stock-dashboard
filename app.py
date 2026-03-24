import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 및 프리미엄 스타일 시트 (Executive UI/UX)
st.set_page_config(page_title="STRATEGIC MARKET INTELLIGENCE 2026", layout="wide")

today_str = datetime.now().strftime("%Y-%m-%d")

st.markdown(f"""
    <style>
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

    /* 하단 섹션 */
    .macro-section {{ background-color: #1a1c1e; padding: 40px; border-radius: 25px; margin-top: 50px; color: white; }}
    .situation-box {{ background-color: rgba(255,255,255,0.07); padding: 15px; border-radius: 10px; border-left: 4px solid #fab005; font-size: 13px; margin-top: 10px; line-height: 1.6; color: #ced4da; }}
    .buffett-appendix {{ background-color: rgba(255,255,255,0.1); padding: 25px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 30px;}}
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 엔진
@st.cache_data(ttl=3600)
def load_market_intelligence(ticker):
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
    
    macros = {"US_Rate": "^TNX", "KR_Rate": "KR10YT=RR", "Oil": "CL=F", "Dollar": "DX-Y.NYB", "VIX": "^VIX", "SP500": "^GSPC", "KOSPI": "^KS11"}
    macro_res = {}
    for k, t in macros.items():
        d = yf.download(t, start="2022-01-01")
        if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
        macro_res[k] = d['Close']
    return df.dropna(subset=['MA240']), macro_res

# --- 데이터 준비 ---
indices = {"NASDAQ Composite": "^IXIC", "NASDAQ 100": "^NDX", "S&P 500": "^GSPC", "KOSPI": "^KS11", "KOSDAQ": "^KQ11"}
choice = st.sidebar.radio("📋 분석 대상 선택", list(indices.keys()))
data, appendix_data = load_market_intelligence(indices[choice])

last = data.iloc[-1]
curr, ma60, ma120, rsi = float(last['Close']), float(last['MA60']), float(last['MA120']), float(last['RSI'])
disp_120 = (curr / ma120) * 100

# 3. 버핏 지수 전용 계산
def calc_global_buffett(sp_val, ks_val):
    us_ratio = (sp_val * 9.5 / 1000 / 28.5) * 100
    kr_ratio = (ks_val * 0.83 / 2450) * 100
    us_stat = "고평가(주의)" if us_ratio > 170 else ("저평가(기회)" if us_ratio < 110 else "적정 가치")
    kr_stat = "고평가(주의)" if kr_ratio > 110 else ("저평가(기회)" if kr_ratio < 75 else "적정 가치")
    return (us_ratio, us_stat), (kr_ratio, kr_stat)

(us_buff, us_stat), (kr_buff, kr_stat) = calc_global_buffett(appendix_data['SP500'].iloc[-1], appendix_data['KOSPI'].iloc[-1])

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

# 5. 중단: 지표 카드
c1, c2, c3 = st.columns(3)
with c1:
    trend_status = "상승 정배열" if ma60 > ma120 else "하락 역배열"
    st.markdown(f'''<div class="info-card"><div class="card-title">Trend - 이평선 추이</div><div class="card-val">{trend_status}</div>
    <div class="card-analysis"><b>해석:</b> 현재 지수는 중기 상승 엔진인 60일선이 120일선 {"위에" if ma60 > ma120 else "아래에"} 있는 {trend_status} 구간입니다.</div></div>''', unsafe_allow_html=True)
with c2:
    st.markdown(f'''<div class="info-card"><div class="card-title">Mean Reversion - 이격도</div><div class="card-val">{disp_120:.1f}%</div>
    <div class="card-analysis"><b>해석:</b> 평균 회귀 지표입니다. {"110%를 초과하여 단기 과열 양상입니다." if disp_120 > 110 else ("90% 미만으로 바닥권 반등 신호입니다." if disp_120 < 90 else "현재 지수는 평균선 근처에서 안정적입니다.")}</div></div>''', unsafe_allow_html=True)
with c3:
    st.markdown(f'''<div class="info-card"><div class="card-title">Sentiment - 심리 지수(RSI)</div><div class="card-val">{rsi:.1f}</div>
    <div class="card-analysis"><b>해석:</b> 현재 심리 점수는 {rsi:.1f}점입니다. {"탐욕 구간으로 분할 매도를 고려하세요." if rsi > 70 else ("공포 구간으로 저점 매수 기회입니다." if rsi < 30 else "시장 심리가 균형을 이루고 있습니다.")}</div></div>''', unsafe_allow_html=True)

# 6. 차트 영역 (UX 최적화: 공백 제거 및 통합 툴팁)
st.markdown("---")
st.subheader("📅 기간별 성과 분석 (Interactive Performance Report)")
tabs = st.tabs(["7일", "1개월", "3개월", "6개월", "1년", "3년", "5년", "10년"])
days_map = {"7일":7, "1개월":22, "3개월":66, "6개월":132, "1년":252, "3년":756, "5년":1260, "10년":2520}

def render_analysis_chart(df_sub, p_name):
    # 수익률 및 CAGR 계산
    start_p, end_p = float(df_sub['Close'].iloc[0]), float(df_sub['Close'].iloc[-1])
    ret = ((end_p - start_p) / start_p) * 100
    days = (df_sub.index[-1] - df_sub.index[0]).days
    cagr = (((end_p / start_p) ** (365 / (days if days > 0 else 1))) - 1) * 100
    
    col_m1, col_m2 = st.columns(2)
    col_m1.metric(f"{p_name} 실질 수익률", f"{ret:.2f}%")
    col_m2.metric(f"{p_name} 연평균 수익률 (CAGR)", f"{cagr:.2f}%")
    
    fig = go.Figure()
    # 캔들스틱
    fig.add_trace(go.Candlestick(x=df_sub.index, open=df_sub['Open'], high=df_sub['High'], 
                                 low=df_sub['Low'], close=df_sub['Close'], name="주가", opacity=0.4))
    
    # 이평선 색상 및 스타일
    ma_styles = {5: '#FF0000', 20: '#FFD700', 60: '#008000', 120: '#0000FF', 240: '#800080', 480: '#4B4B4B'}
    for d, color in ma_styles.items():
        if f'MA{d}' in df_sub.columns:
            fig.add_trace(go.Scatter(x=df_sub.index, y=df_sub[f'MA{d}'], name=f'{d}일선', line=dict(color=color, width=1.8)))
    
    # 골든/데드크로스
    gs, ds = df_sub[df_sub['G']], df_sub[df_sub['D']]
    fig.add_trace(go.Scatter(x=gs.index, y=gs['MA60'], mode='markers', marker=dict(symbol='triangle-up', size=12, color='#FF0000'), name='Golden Cross'))
    fig.add_trace(go.Scatter(x=ds.index, y=ds['MA60'], mode='markers', marker=dict(symbol='triangle-down', size=12, color='#0000FF'), name='Dead Cross'))

    # [UX 업그레이드] 레이아웃 설정
    fig.update_layout(
        height=550, 
        template="plotly_white", 
        xaxis_rangeslider_visible=False, 
        dragmode='pan', 
        hovermode='x unified', # 마우스 올리면 날짜/수치 한방에 표시
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(
            range=[df_sub.index.min(), df_sub.index.max()], # [요청] 데이터 없는 영역은 안 보이게 고정
            showspikes=True, spikemode='across', spikesnap='cursor', spikedash='dot'
        ),
        yaxis=dict(fixedrange=False), # Y축은 가격에 따라 움직임 가능
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

for i, (name, d) in enumerate(days_map.items()):
    with tabs[i]: render_analysis_chart(data.iloc[-d:], name)

# 7. 하단 부록: Global Macro & Buffett Index
st.markdown('<div class="macro-section"><h2>📎 부록: 글로벌 매크로 및 밸류에이션 분석 (Appendix)</h2>', unsafe_allow_html=True)

st.markdown('<div class="buffett-appendix">', unsafe_allow_html=True)
st.markdown("### 🏛️ Buffett Index - 국가별 버핏 지수 (시총/GDP)")
b_col1, b_col2 = st.columns(2)
with b_col1:
    st.markdown(f"**미국 (US Market)**: <span style='font-size:28px;'>{us_buff:.1f}%</span> (상태: **{us_stat}**)", unsafe_allow_html=True)
    st.caption("설명: GDP 대비 주식 가치. 170% 이상 시 역사적 고평가를 경고합니다.")
with b_col2:
    st.markdown(f"**한국 (KR Market)**: <span style='font-size:28px;'>{kr_buff:.1f}%</span> (상태: **{kr_stat}**)", unsafe_allow_html=True)
    st.caption("설명: 한국 시장은 보통 75~100% 사이를 유지합니다.")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
m1, m2 = st.columns(2); m3, m4 = st.columns(2)

def get_macro_situation(name, series):
    curr_v, prev_v = series.iloc[-1], series.iloc[-22]
    diff = curr_v - prev_v
    if name == "US_Rate": return f"미 10년물 금리 {curr_v:.2f}% ({diff:+.2f}%). 금리 급등 시 기술주 매력도가 떨어집니다."
    elif name == "Oil": return f"WTI 유가 ${curr_v:.2f}. 고유가는 인플레이션을 자극하여 금리 인하를 지연시킵니다."
    elif name == "Dollar": return f"달러 인덱스 {curr_v:.2f}. 달러 강세 시 외국인 수급이 불리해집니다."
    else: return f"VIX(공포지수) {curr_v:.2f}. 시장의 패닉 상태를 측정하며, 20 이하가 안정적입니다."

def render_macro_appendix(series, title, color, m_name):
    fig = go.Figure(go.Scatter(x=series.index[-250:], y=series.values[-250:], mode='lines', line=dict(color=color, width=2.5)))
    fig.update_layout(height=220, title=title, template="plotly_dark", margin=dict(l=10, r=10, t=40, b=10),
                      xaxis=dict(showspikes=True, spikemode='across'), hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown(f'<div class="situation-box"><b>🕵️ 상황 진단:</b> {get_macro_situation(m_name, series)}</div>', unsafe_allow_html=True)

with m1: render_macro_appendix(appendix_data['US_Rate'], "US 10Y Yield (미 국채 금리)", "#ff6b6b", "US_Rate")
with m2: render_macro_appendix(appendix_data['Oil'], "WTI Crude Oil (유가)", "#adb5bd", "Oil")
with m3: render_macro_appendix(appendix_data['Dollar'], "Dollar Index (달러 지수)", "#4dadf7", "Dollar")
with m4: render_macro_appendix(appendix_data['VIX'], "VIX (공포 지수)", "#fab005", "VIX")
st.markdown('</div>', unsafe_allow_html=True)

# 8. 초보자 통합 마스터 가이드
st.markdown("---")
with st.expander("🐣 **초보자 통합 가이드: 지표 독법 마스터하기 (클릭)**"):
    st.markdown("""
    ### 1. 지수 추세 (Trend)
    - **정배열:** 단기선이 장기선보다 위. "달리는 말"입니다. 떨어질 때 매수하세요.
    - **역배열:** 장기선이 단기선보다 위. "내려가는 길"입니다. 보수적으로 보세요.
    

    ### 2. 이격도 (Mean Reversion)
    - 주가는 평균선(120일선) 근처로 돌아오려는 본능이 있습니다. 110% 이상이면 너무 흥분한 것이고, 90% 이하면 너무 겁먹은 것입니다.
    

    ### 3. 심리 지수 (RSI)
    - **70 이상:** 탐욕 구간. 다들 파티 중이니 나갈 준비를 하세요.
    - **30 이하:** 공포 구간. 다들 도망쳤으니 보물을 주울 시간입니다.
    

    ### 4. 버핏 지수 (Buffett Index)
    - 국가 경제(GDP) 대비 주식 시장이 얼마나 무거운지를 봅니다. 역사적 버블 여부를 가리는 '거인의 지표'입니다.
    
    """)
