import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 및 디자이너급 CSS 주입
st.set_page_config(page_title="GLOBAL MARKETS MONITOR", layout="wide")

# 디자이너가 만진 듯한 UI/UX 스타일 정의 (Bloomberg/Toss Security 감성)
st.markdown("""
    <style>
    /* 전체 배경색 및 폰트 설정 */
    [data-testid="stAppViewContainer"] { background-color: #fcfcfc; font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
    [data-testid="stHeader"] { background-color: rgba(252, 252, 252, 0); }
    [data-testid="stSidebar"] { background-color: #f1f3f5; border-right: 1px solid #e9ecef; }
    
    /* 타이틀 및 서브타이틀 스타일 */
    h1 { color: #111111; font-weight: 800; letter-spacing: -1px; margin-bottom: 0px; }
    h3 { color: #333333; font-weight: 700; margin-top: 25px; margin-bottom: 15px; }
    
    /* 최종 결론 (Verdict) Card 스타일 - 있어보이는 핵심 */
    .verdict-box { padding: 30px; border-radius: 20px; text-align: left; margin-bottom: 30px; border: 1px solid #e9ecef;}
    .positive-v { background: linear-gradient(135deg, #fcedeb 0%, #fff6f5 100%); border-left: 10px solid #ff6b6b; color: #e03131; } /* 상승/긍정 */
    .neutral-v { background: linear-gradient(135deg, #fff9db 0%, #fffef5 100%); border-left: 10px solid #fab005; color: #f08c00; } /* 중립 */
    .negative-v { background: linear-gradient(135deg, #e7f5ff 0%, #f3faff 100%); border-left: 10px solid #228be6; color: #1971c2; } /* 하락/부정 */
    .v-title { font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; opacity: 0.8;}
    .v-content { font-size: 36px; font-weight: 800; letter-spacing: -1.5px; line-height: 1.1; }
    
    /* 일반 정보 Card 스타일 */
    .info-card { background-color: #ffffff; padding: 25px; border-radius: 15px; border: 1px solid #e9ecef; box-shadow: 0 4px 6px rgba(0,0,0,0.02); height: 100%; }
    .card-title { font-size: 14px; font-weight: 600; color: #868e96; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
    .card-val { font-size: 28px; font-weight: 700; color: #111111; letter-spacing: -1px; }
    .card-caption { font-size: 13px; color: #868e96; margin-top: 10px; line-height: 1.4; }
    
    /* 메트릭 스타일 재정의 (초보자용 지표) */
    [data-testid="stMetricValue"] { font-size: 32px !important; font-weight: 700 !important; color: #111111 !important; letter-spacing: -1.5px !important; }
    [data-testid="stMetricLabel"] { font-size: 14px !important; color: #868e96 !important; font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 1px !important; }
    [data-testid="stMetricDelta"] { font-size: 15px !important; }

    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f1f3f5; border-radius: 10px; padding: 8px 16px; color: #495057; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background-color: #228be6 !important; color: white !important; font-weight: 600; }
    
    /* 가이드북 하단 바 스타일 */
    .guide-box { background-color: #111111; padding: 25px; border-radius: 15px; color: #f8f9fa; margin-top: 40px;}
    .guide-box h4 { color: #f8f9fa !important; font-weight: 700; }
    .guide-box .info-col { border-left: 1px solid #333; padding-left: 20px;}
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 수집 및 지표 계산 함수 ( Bloomberg 급 데이터 인프라)
@st.cache_data(ttl=3600) # 1시간 캐시
def load_full_data(ticker):
    df = yf.download(ticker, start="2000-01-01")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 주요 이평선
    for m in [5, 20, 60, 120, 240]:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    
    # RSI (심리 과열도)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD (추세 에너지)
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    return df.dropna(subset=['MA240'])

# --- 사이드바: 설정 영역 ---
st.sidebar.markdown("# ⚙️ Dashboard <br>Intelligence Config", unsafe_allow_html=True)
indices = {
    "NASDAQ (종합 기술)": "^IXIC", 
    "NASDAQ 100 (핵심 기술)": "^NDX", 
    "S&P 500 (시장 전체)": "^GSPC", 
    "KOSPI (한국 코스피)": "^KS11", 
    "KOSDAQ (한국 코스닥)": "^KQ11"
}
choice = st.sidebar.radio("모니터링 대상 지수", list(indices.keys()))
data = load_full_data(indices[choice])

# --- 데이터 분석 및 스코어링 로직 ---
last = data.iloc[-1]
curr = float(last['Close'])
ma60, ma120 = float(last['MA60']), float(last['MA120'])
rsi, macd, signal = float(last['RSI']), float(last['MACD']), float(last['Signal_Line'])

# 분석 지표들
is_60_120_bull = ma60 > ma120
energy_gap = abs(ma60 - ma120) / ma120 * 100
disp_120 = (curr / ma120) * 100

# 최종 의사결정 점수 (Score) - 보스용 고급 알고리즘
score = 0
if is_60_120_bull: score += 2 # 추세 상승
else: score -= 2
if rsi < 38: score += 2 # 저평가 기회
elif rsi > 62: score -= 2 # 과평가 위험
if macd > signal: score += 1 # 상승 모멘텀
else: score -= 1
if disp_120 < 97: score += 1 # 평균 회귀 매수

# 스코어에 따른 최종 결론 및 색상 클래스
if score >= 2: verdict, v_class = "긍정 (적극적 투자 권장)", "positive-v"
elif score <= -2: verdict, v_class = "부정 (보수적 대응/현금화)", "negative-v"
else: verdict, v_class = "중립 (신중한 관망)", "neutral-v"

# --- 메인 화면: 보스용 최상단 Executive Summary ---
st.title(f"{choice} Intelligence Report")
# Bloomberg 급 최종 결론 카드
st.markdown(f'''
    <div class="verdict-box {v_class}">
        <div class="v-title">오늘의 시장 투자 의견</div>
        <div class="v-content">{verdict}</div>
    </div>
''', unsafe_allow_html=True)

# --- 중단: 60/120 핵심 진단 & 보조 지표 (Card UI) ---
st.subheader("🔍 Key Strategic Indicators (60/120 MA focus)")
d_c1, d_c2, d_c3, d_c4 = st.columns(4)

with d_c1:
    st.markdown(f'''
        <div class="info-card">
            <div class="card-title">중장기 추세 상태</div>
            <div class="card-val">{'상승 흐름' if is_60_120_bull else '하락 흐름'}</div>
            <div class="card-caption">60일선(수급)이 120일선(경기) 위에 위치합니다.</div>
        </div>
    ''', unsafe_allow_html=True)
with d_c2:
    st.markdown(f'''
        <div class="info-card">
            <div class="card-title">시장 에너지</div>
            <div class="card-val">{'응축 (폭발전야)' if energy_gap < 2.5 else '진행 (추세지속)'}</div>
            <div class="card-caption">두 선의 간격이 좁을수록 큰 변동성이 곧 발생합니다.</div>
        </div>
    ''', unsafe_allow_html=True)
with d_c3:
    st.markdown(f'''
        <div class="info-card">
            <div class="card-title">심리 과열도 (RSI)</div>
            <div class="card-val">{rsi:.1f}</div>
            <div class="card-caption">{'조정 주의 (과열)' if rsi > 70 else ('매수 기회 (바닥)' if rsi < 30 else '정상 범위')} 구간입니다.</div>
        </div>
    ''', unsafe_allow_html=True)
with d_c4:
    st.markdown(f'''
        <div class="info-card">
            <div class="card-title">평균 회귀 이격률</div>
            <div class="card-val">{disp_120:.1f}%</div>
            <div class="card-caption">120일 평균 가격(집) 대비 현재 위치입니다.</div>
        </div>
    ''', unsafe_allow_html=True)

# --- 차트 및 성과 영역: 보스가 가장 오래 볼 영역 (UX 고도화) ---
st.markdown("---")
st.subheader("📅 Historical Performance & Chart Analysis")
tabs = st.tabs(["3개월", "6개월", "1년", "3년", "전체"])

# 성과 지표 및 차트 그리기 함수 (전문가용 클린 차트)
def display_analysis_tab(df_subset, period_name, show_predictions=False):
    # 수익률 및 성과 지표 계산
    s_p = float(df_subset['Close'].iloc[0])
    e_p = float(df_subset['Close'].iloc[-1])
    ret = ((e_p - s_p) / s_p) * 100
    days = (df_subset.index[-1] - df_subset.index[0]).days
    cagr = (((e_p / s_p) ** (365 / days)) - 1) * 100 if days > 0 else 0
    
    # [가장 중요한 성과 지표] 차트 바로 위에 크게 배치
    r1, r2 = st.columns(2)
    # tosssec 스타일 클린 메트릭
    r1.metric(f"{period_name} 기간 실질 수익률", f"{ret:.2f}%")
    r2.metric(f"{period_name} 연평균 성장률(CAGR)", f"{cagr:.2f}%")

    # 전문가용 클린 차트 디자인 (Plotly Dark Style을 White에 이식)
    fig = go.Figure()
    # 캔들
    fig.add_trace(go.Candlestick(x=df_subset.index, open=df_subset['Open'], high=df_subset['High'], 
                                 low=df_subset['Low'], close=df_subset['Close'], name="주가", opacity=0.4))
    # 이평선 색상 간결화 및 60/120 강조
    ma_colors = {60:'#5c7cfa', 120:'#228be6', 240:'#adb5bd'} # 블루 팔레트 & 블랙/그레이
    for d, c in ma_colors.items():
        if f'MA{d}' in df_subset.columns:
            fig.add_trace(go.Scatter(x=df_subset.index, y=df_subset[f'MA{d}'], name=f'{d}일선', line=dict(color=c, width=2 if d != 240 else 1.2)))
    
    # 골든/데드 크로스 (사용자 가이드 기반: 60vs120)
    # 기존 코드에서 df['G']가 전체 데이터 기준이라, subset에서 G/D 컬럼을 가져와야 함. 
    # load_full_data에서 전체 데이터 df를 반환하므로 tabs의 slicing을 이용.
    df_for_cross = data.loc[df_subset.index[0]:df_subset.index[-1]]
    gs = df_for_cross[df_for_cross['G']]
    ds = df_for_cross[df_for_cross['D']]
    
    # 코랄 레드/스틸 블루 마커
    fig.add_trace(go.Scatter(x=gs.index, y=gs['MA60'], mode='markers', marker=dict(symbol='triangle-up', size=12, color='#e03131'), name='Golden(60/120)'))
    fig.add_trace(go.Scatter(x=ds.index, y=ds['MA60'], mode='markers', marker=dict(symbol='triangle-down', size=12, color='#1971c2'), name='Death(60/120)'))
    
    # 디자이너급 차트 레이아웃
    fig.update_layout(
        height=550, 
        template="plotly_white", # 배경색 대시보드와 통일
        xaxis_rangeslider_visible=False, 
        dragmode='pan', 
        hovermode='x unified', # 전문가용 툴팁
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    # 스크롤 줌 config 최적화
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

with tabs[0]: display_analysis_tab(data.iloc[-60:], "3개월")
with tabs[1]: display_analysis_tab(data.iloc[-125:], "6개월")
with tabs[2]: display_analysis_tab(data.iloc[-250:], "1년")
with tabs[3]: display_analysis_tab(data.iloc[-750:], "3년")
with tabs[4]: display_analysis_tab(data, "전체")

# --- 최하단: 투자 가이드북 (Executive Footnotes 스타일) ---
# 기존의 밝은 가이드 박스를 블랙 배경으로 바꾸어 화면 마지막의 무게감을 줌
st.markdown("""
    <div class="guide-box">
        <h4>📖 Executive Intelligence Reference</h4>
        <div style="margin-top:20px;">
            <div style="display:flex; justify-content: space-between;">
                <div class="info-col">
                    <div style="font-weight:600; color:# fab005;">1. 평균 회귀 원칙</div>
                    <div style="font-size:13px; opacity:0.7;">주가는 120일선에서 너무 멀어지면 결국 자석처럼 다시 돌아옵니다. 이격률이 115% 이상이면 하락을, 85% 이하면 상승을 준비하세요.</div>
                </div>
                <div class="info-col">
                    <div style="font-weight:600; color:# ffffff;">2. 추세 판독기</div>
                    <div style="font-size:13px; opacity:0.7;">60일선이 120일선 위에 있는 정배열 상태에서 주가가 이평선 근처까지 눌릴 때가 가장 안전한 매수 타이밍입니다.</div>
                </div>
                <div class="info-col">
                    <div style="font-weight:600; color:# fab005;">3. 에너지 수렴</div>
                    <div style="font-size:13px; opacity:0.7;">60/120일선이 만나는 수렴 구간 이후에는 거대한 추세 변화가 옵니다. 이때 RSI가 낮다면 상방 돌파 가능성이 큽니다.</div>
                </div>
                <div class="info-col">
                    <div style="font-weight:600; color:# ffffff;">4. 역발상 크로스</div>
                    <div style="font-size:13px; opacity:0.7;">골든크로스가 발생했을 때 이미 주가가 너무 올랐다면(이격률 높음), 오히려 단기 고점일 확률이 높으니 주의하세요.</div>
                </div>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)
