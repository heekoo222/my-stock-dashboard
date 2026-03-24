import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 및 프리미엄 스타일 시트 (Executive UI/UX 유지)
st.set_page_config(page_title="GLOBAL STRATEGIC INTELLIGENCE 2026", layout="wide")

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

# 2. 데이터 엔진 (장기 데이터 로드 설정)
@st.cache_data(ttl=3600)
def load_all_market_intelligence(ticker):
    # 지수 데이터 (최소 20년 이상 로드)
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
    
    # [수정] 매크로 부록 데이터 (10년 탭 지원을 위해 start 날짜 변경)
    macros = {"US_Rate": "^TNX", "KR_Rate": "KR10YT=RR", "Oil": "CL=F", "Dollar": "DX-Y.NYB", "VIX": "^VIX", "SP500": "^GSPC", "KOSPI": "^KS11"}
    macro_res = {}
    for k, t in macros.items():
        d = yf.download(t, start="2010-01-01") # [수정] 2010년부터 로드
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

# 3. 버핏 지수 전용 계산
def calc_global_buffett(sp_val, ks_val):
    # US GDP 2026: 28.5T, Multiplier 9.5 / KR GDP: 2450T, Multiplier 0.83
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

# 5. 중단: 지표 카드 (그대로 유지)
c1, c2, c3 = st.columns(3)
with c1:
    trend_status = "상승 정배열" if ma60 > ma120 else "하락 역배열"
    st.markdown(f'''<div class="info-card"><div class="card-title">Trend - 이평선 추이</div><div class="card-val">{trend_status}</div>
    <div class="card-analysis"><b>해석:</b> 현재 지수는 중기 수급선(60일)이 경기선(120일) {"위에" if ma60 > ma120 else "아래에"} 있는 {trend_status} 상태입니다.</div></div>''', unsafe_allow_html=True)
with c2:
    st.markdown(f'''<div class="info-card"><div class="card-title">Mean Reversion - 이격도</div><div class="card-val">{disp_120:.1f}%</div>
    <div class="card-analysis"><b>해석:</b> 평균 회귀 지표입니다. {"110% 초과로 고평가 상태입니다." if disp_120 > 110 else ("90% 미만으로 바닥권 매수 신호입니다." if disp_120 < 90 else "현재 지수는 평균선 근처에서 안정적입니다.")}</div></div>''', unsafe_allow_html=True)
with c3:
    st.markdown(f'''<div class="info-card"><div class="card-title">Sentiment - 심리 지수(RSI)</div><div class="card-val">{rsi:.1f}</div>
    <div class="card-analysis"><b>해석:</b> 심리 점수는 {rsi:.1f}점입니다. {"탐욕 구간으로 과열을 주의하세요." if rsi > 70 else ("공포 구간으로 저점 매수 기회입니다." if rsi < 30 else "시장 심리가 균형 상태입니다.")}</div></div>''', unsafe_allow_html=True)

# 6. 차트 영역: [수정] 5단계 탭 라인업 (6개월~전체) 및 UX 최적화
st.markdown("---")
st.subheader("📅 Interactive Performance Report")
# [수정] 탭 구성을 5개로 정예화
tabs = st.tabs(["6개월", "1년", "5년", "10년", "전체"])
# 거래일 기준 approximate mapping
days_map = {"6개월":132, "1년":252, "5년":1260, "10년":2520}

def render_analysis_chart(df_sub, p_name):
    # 성과 지표 계산
    start_p, end_p = float(df_sub['Close'].iloc[0]), float(df_sub['Close'].iloc[-1])
    ret = ((end_p - start_p) / start_p) * 100
    days = (df_sub.index[-1] - df_sub.index[0]).days
    cagr = (((end_p / start_p) ** (365 / (days if days > 0 else 1))) - 1) * 100
    
    col_m1, col_m2 = st.columns(2)
    col_m1.metric(f"{p_name} 실질 수익률", f"{ret:.2f}%")
    col_m2.metric(f"{p_name} 연평균 수익률 (CAGR)", f"{cagr:.2f}%")
    
    fig = go.Figure()
    # 캔들스틱 (가시성 확보)
    fig.add_trace(go.Candlestick(x=df_sub.index, open=df_sub['Open'], high=df_sub['High'], 
                                 low=df_sub['Low'], close=df_sub['Close'], name="주가", opacity=0.4))
    
    # 이평선 색상 (고대비 유지)
    ma_styles = {5: '#FF0000', 20: '#FFD700', 60: '#008000', 120: '#0000FF', 240: '#800080', 480: '#4B4B4B'}
    for d, color in ma_styles.items():
        if f'MA{d}' in df_sub.columns:
            # 장기 차트에서는 선 굵기를 살짝 얇게 조정
            width = 1.6 if d < 240 else 1.0
            fig.add_trace(go.Scatter(x=df_sub.index, y=df_sub[f'MA{d}'], name=f'{d}일선', line=dict(color=color, width=width)))
    
    # 골든/데드크로스
    gs, ds = df_sub[df_sub['G']], df_sub[df_sub['D']]
    fig.add_trace(go.Scatter(x=gs.index, y=gs['MA60'], mode='markers', marker=dict(symbol='triangle-up', size=12, color='#FF0000'), name='Golden Cross'))
    fig.add_trace(go.Scatter(x=ds.index, y=ds['MA60'], mode='markers', marker=dict(symbol='triangle-down', size=12, color='#0000FF'), name='Dead Cross'))

    # 레이아웃 설정 (Unified Hover 및 공백 제거 UX 유지)
    fig.update_layout(
        height=550, 
        template="plotly_white", 
        xaxis_rangeslider_visible=False, 
        dragmode='pan', 
        hovermode='x unified', # unified hover 유지
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(
            range=[df_sub.index.min(), df_sub.index.max()], # [UX 유지] 공백 제거
            showspikes=True, spikemode='across', spikesnap='cursor', spikedash='dot'
        ),
        yaxis=dict(fixedrange=False), 
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

# [수정] 5단계 탭 렌더링 로직
for i, name in enumerate(["6개월", "1년", "5년", "10년", "전체"]):
    with tabs[i]:
        if name == "전체":
            render_analysis_chart(data, name)
        else:
            days = days_map[name]
            render_analysis_chart(data.iloc[-days:], name)

# --- 하단 부록 섹션 (버핏 지수 + 매크로) ---
st.markdown('<div class="macro-section"><h2>📎 부록: 글로벌 매크로 및 밸류에이션 분석 (Appendix)</h2>', unsafe_allow_html=True)

st.markdown('<div class="buffett-appendix">', unsafe_allow_html=True)
st.markdown("### 🏛️ Buffett Index - 국가별 버핏 지수 (시총/GDP)")
b_col1, b_col2 = st.columns(2)
with b_col1:
    st.markdown(f"**미국 (US Market)**: <span style='font-size:28px;'>{us_buff:.1f}%</span> (상태: **{us_stat}**)", unsafe_allow_html=True)
    st.caption("설명: GDP 대비 주식 비중. 170% 이상 시 고평가를 경고합니다.")
with b_col2:
    st.markdown(f"**한국 (KR Market)**: <span style='font-size:28px;'>{kr_buff:.1f}%</span> (상태: **{kr_stat}**)", unsafe_allow_html=True)
    st.caption("설명: 한국 시장은 보통 75~100% 사이에서 움직입니다.")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
# [수정] 매크로 부록에도 기간 탭 추가 (1y, 5y, 10y)
st.markdown("### 🌐 Macro Trend Indicators")
macro_tabs = st.tabs(["1년 추이", "5년 추이", "10년 추이"])
macro_days_map = {"1년 추이": 252, "5년 추이": 1260, "10년 추이": 2520}

# 매크로 상황 진단 함수 (데이터 기반 시나리오 엔진 유지)
def get_macro_situation(name, series):
    curr_v, prev_v = series.iloc[-1], series.iloc[-22] # 한달 전과 비교
    diff = curr_v - prev_v
    if name == "US_Rate": return f"미 10년물 금리 {curr_v:.2f}% ({diff:+.2f}%). 금리 상승 시 기술주 할인율 부담이 가중됩니다."
    elif name == "Oil": return f"WTI 유가 ${curr_v:.2f}. 고유가는 물가 상승을 자극하여 긴축 기조를 장기화시킵니다."
    elif name == "Dollar": return f"달러 인덱스 {curr_v:.2f}. 강달러 지속 시 외국인 자금 유출로 국내 증시에 하방 압력을 줍니다."
    else: return f"VIX(공포지수) {curr_v:.2f}. 시장 패닉 측도이며, 20 이하 안정, 25 상회 시 공포 확산을 의미합니다."

# 매크로 차트 렌더링 함수 (다크 모드 유지 및 툴팁 최적화)
def render_macro_chart(series, title, color, m_name):
    # unified hover 및 공백 제거 적용
    fig = go.Figure(go.Scatter(x=series.index, y=series.values, mode='lines', line=dict(color=color, width=2.5)))
    fig.update_layout(height=220, title=title, template="plotly_dark", margin=dict(l=10, r=10, t=40, b=10),
                      xaxis=dict(
                          range=[series.index.min(), series.index.max()], # 공백 제거
                          showspikes=True, spikemode='across'
                      ), 
                      hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    # 상황 진단 텍스트는 최신 데이터 기준 하나만 출력

# [수정] 매크로 탭 렌더링 루프
for i, tab_name in enumerate(["1년 추이", "5년 추이", "10년 추이"]):
    with macro_tabs[i]:
        days = macro_days_map[tab_name]
        m1, m2 = st.columns(2); m3, m4 = st.columns(2)
        
        # 각 탭 안에 그리드 배치
        with m1: 
            render_macro_chart(appendix_data['US_Rate'].iloc[-days:], "US 10Y Yield (미 국채 금리)", "#ff6b6b", "US_Rate")
            st.markdown(f'<div class="situation-box"><b>🕵️ 상황 진단:</b> {get_macro_situation("US_Rate", appendix_data["US_Rate"])}</div>', unsafe_allow_html=True)
        with m2: 
            render_macro_chart(appendix_data['Oil'].iloc[-days:], "WTI Crude Oil (유가)", "#adb5bd", "Oil")
            st.markdown(f'<div class="situation-box"><b>🕵️ 상황 진단:</b> {get_macro_situation("Oil", appendix_data["Oil"])}</div>', unsafe_allow_html=True)
        with m3: 
            render_macro_chart(appendix_data['Dollar'].iloc[-days:], "Dollar Index (달러 지수)", "#4dadf7", "Dollar")
            st.markdown(f'<div class="situation-box"><b>🕵️ 상황 진단:</b> {get_macro_situation("Dollar", appendix_data["Dollar"])}</div>', unsafe_allow_html=True)
        with m4: 
            render_macro_chart(appendix_data['VIX'].iloc[-days:], "VIX (공포 지수)", "#fab005", "VIX")
            st.markdown(f'<div class="situation-box"><b>🕵️ 상황 진단:</b> {get_macro_situation("VIX", appendix_data["VIX"])}</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# 8. 초보자 통합 마스터 가이드 (유지)
st.markdown("---")
with st.expander("🐣 **초보자 통합 가이드: 대시보드 지표 마스터하기 (클릭)**"):
    st.markdown("""
    ### 1. 지수 추세 (Trend)
    - **정배열:** 단기선이 장기선보다 위. 상승세가 강력합니다. 눌림목 매수 기회입니다.
    - **역배열:** 장기선이 단기선보다 위. 하락세가 강력합니다. 반등 시 매도 기회입니다.
    

    ### 2. 이격도 (Mean Reversion)
    - 주가는 평균선(120일선)으로 돌아오려는 본능이 있습니다. 110%를 넘으면 너무 흥분한 것이고, 90% 이하면 너무 겁먹은 것입니다.
    

    ### 3. 심리 지수 (RSI)
    - **70 이상:** 탐욕 구간. 다들 환호할 때입니다. 과열을 주의하세요.
    - **30 이하:** 공포 구간. 다들 도망쳤을 때입니다. 저점 매수 기회일 수 있습니다.
    

    ### 4. 버핏 지수 (Buffett Index)
    - 국가 경제(GDP) 대비 주식 시장이 얼마나 무거운지를 봅니다. 거시적 버블 여부를 가리는 '거인의 지표'입니다.
    
    """)
