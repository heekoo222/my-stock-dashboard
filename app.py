import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 및 사용자 정의 CSS
st.set_page_config(page_title="주요 지수 Monitoring", layout="wide")
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
    .insight-box { background-color: #f0f2f6; padding: 20px; border-radius: 15px; border-left: 5px solid #ff4b4b; margin-bottom: 20px;}
    .guide-card { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e6ed; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); height: 100%;}
    .guide-title { font-weight: bold; color: #1c83e1; font-size: 16px; margin-bottom: 10px;}
    .guide-text { font-size: 14px; color: #5e6d82; }
    </style>
    """, unsafe_allow_value=True)

# 2. 데이터 불러오기 함수
@st.cache_data
def load_data(ticker):
    df = yf.download(ticker, start="2000-01-01")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 이평선 계산 (5, 20, 60, 120, 240일)
    for m in [5, 20, 60, 120, 240]:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    
    # 크로스 신호 생성 (사용자 가이드 기반: 60일 vs 120일)
    df['G'] = (df['MA60'].shift(1) < df['MA120'].shift(1)) & (df['MA60'] > df['MA120'])
    df['D'] = (df['MA60'].shift(1) > df['MA120'].shift(1)) & (df['MA60'] < df['MA120'])
    return df.dropna(subset=['MA240'])

# --- 사이드바 ---
st.sidebar.title("⚙️ Dashboard 설정")

# [메뉴 추가] 지수 선택 (나스닥 100 추가)
indices = {
    "NASDAQ": "^IXIC", 
    "NASDAQ 100": "^NDX", # 추가됨
    "S&P 500": "^GSPC", 
    "KOSPI": "^KS11", 
    "KOSDAQ": "^KQ11"
}
choice = st.sidebar.radio("모니터링할 지수", list(indices.keys()))
t_code = indices[choice]

st.sidebar.markdown("---")

# [기능 추가] 분석 기준 이평선 선택 (기본 240일)
ma_options = {5: "5일선 (초단기)", 20: "20일선 (단기/심리)", 60: "60일선 (중기/수급)", 120: "120일선 (장기)", 240: "240일선 (초장기/경기)"}
selected_ma_day = st.sidebar.selectbox("분석 기준 이평선 선택", list(ma_options.keys()), index=4) # index 4는 240일

# 데이터 준비
data = load_data(t_code)
last = data.iloc[-1]
curr = float(last['Close'])

# --- 최상단: AI 투자 Insight (가이드 기반 분석) ---
st.title(f"📊 주요 지수 Monitoring ({choice})")

st.markdown(f'<div class="insight-box">', unsafe_allow_value=True)
st.subheader("💡 실시간 종합 투자 Insight (AI 분석)")

# 가이드 기반 분석 로직
# 2) 정배열/역배열
is_bull = (last['MA5'] > last['MA20'] > last['MA60'] > last['MA120'] > last['MA240'])
is_bear = (last['MA5'] < last['MA20'] < last['MA60'] < last['MA120'] < last['MA240'])
trend_desc = "🚀 현재 전형적인 **정배열(상승 추세)** 상태입니다. 눌림목 매수 타이밍을 노리세요." if is_bull else \
             ("📉 현재 전형적인 **역배열(하락 추세)** 상태입니다. 보수적 접근 또는 관망이 필요합니다." if is_bear else \
              "🔄 이평선들이 뒤섞여 있는 **혼조세**입니다. 확실한 방향성이 나올 때까지 대기하세요.")

# 3) 수렴/확산
gap_3 = max(last['MA5'], last['MA20'], last['MA60']) / min(last['MA5'], last['MA20'], last['MA60'])
energy_desc = "🧨 단/중기 이평선들이 모이며 **에너지가 수렴** 중입니다. 조만간 큰 변동성에 대비하세요." if gap_3 < 1.04 else \
              "🌊 이평선들이 벌어지며 **추세가 확산** 중입니다. 기존 추세가 강화되고 있습니다."

# 4) 골든/데드 크로스 (최근 5일 내 발생 여부)
recent_cross = data.iloc[-5:]
has_golden = recent_cross['G'].any()
has_death = recent_cross['D'].any()
cross_desc = "🔔 최근 60일선이 120일선을 뚫는 **골든크로스**가 발생했습니다! (선반영 주의, 역발상 매도 고려 가능)" if has_golden else \
             ("🔕 최근 60일선이 120일선 밑으로 가는 **데드크로스**가 발생했습니다! (선반영 주의, 역발상 매수 고려 가능)" if has_death else \
              "📊 최근 특이한 크로스 신호는 없습니다.")

st.markdown(f"- **추세:** {trend_desc}")
st.markdown(f"- **에너지:** {energy_desc}")
st.markdown(f"- **신호:** {cross_desc}")
st.markdown(f"**결론:** {choice} 지수는 {trend_desc.split(' 상태입니다.')[0]}이며, {energy_desc.split(' 중입니다.')[0]} 상황입니다. {cross_desc.split('! ')[0]} 상황을 종합적으로 고려하여 신중히 투자하시기 바랍니다.")
st.markdown('</div>', unsafe_allow_value=True)

# --- 중단: 수익률 및 선택 이평선 지표 ---
st.subheader(f"📝 {ma_options[selected_ma_day]} 기준 핵심 지표 및 수익률")

# 기간 및 연평균 수익률 계산 함수 (차트 탭에서 사용)
def display_returns(df_subset, period_text):
    if len(df_subset) < 2: return
    start_p = float(df_subset['Close'].iloc[0])
    end_p = float(df_subset['Close'].iloc[-1])
    # 기간 수익률
    total_ret = ((end_p - start_p) / start_p) * 100
    # 연평균 수익률(CAGR) 계산
    days = (df_subset.index[-1] - df_subset.index[0]).days
    if days > 0:
        cagr = (((end_p / start_p) ** (365 / days)) - 1) * 100
    else:
        cagr = 0
    
    # 지표 표시
    c_ret1, c_ret2 = st.columns(2)
    with c_ret1: st.metric(f"{period_text} 기간 수익률", f"{total_ret:.2f}%")
    with c_ret2: st.metric(f"{period_text} 연평균 수익률 (CAGR)", f"{cagr:.2f}%")

# 선택 이평선 기반 지표 (실시간)
m_disp, m_vol, m_pred = st.columns(3)
selected_ma_val = float(last[f'MA{selected_ma_day}'])

with m_disp:
    # 1) 이격률 계산 및 평균 회귀 예측
    disp = (curr / selected_ma_val) * 100
    st.write(f"🏠 **{selected_ma_day}일선 이격률**")
    st.write(f"현재 이격도: {disp:.1f}%")
    st.caption(f"설명: 현재가가 {selected_ma_day}일 평균 가격에서 얼마나 멀리 있는지 봅니다.")
    
    # 이격률에 따른 예측 (가이드 1 기반)
    # 임계값은 이평선 기간에 따라 다르게 설정하는 것이 좋음 (장기선일수록 임계값을 크게)
    threshold = 15 if selected_ma_day >= 120 else (8 if selected_ma_day >= 60 else 4)
    if disp > (100 + threshold):
        st.error(f"Insight: 경기선에서 너무 멀어졌습니다(+{threshold}% 초과). **평균 회귀에 따른 하락 예상**. 분할 매도를 고려하세요.")
    elif disp < (100 - threshold):
        st.success(f"Insight: 경기선에서 너무 밀려났습니다(-{threshold}% 미만). **평균 회귀에 따른 상승 예상**. 분할 매수를 검토하세요.")
    else:
        st.info("Insight: 경기선 근처에서 안정적인 흐름입니다. 추세 유지를 관망하세요.")

with m_vol:
    # 최근 해당 기간 동안의 변동성 (표준편차)
    volatility = data['Close'].iloc[-selected_ma_day:].std()
    st.write(f"📉 **최근 {selected_ma_day}일 변동성**")
    st.write(f"변동성 수치: {volatility:.2f}")
    st.caption(f"설명: 최근 {selected_ma_day}일 동안 주가가 얼마나 위아래로 크게 움직였는지를 나타냅니다.")
    
with m_pred:
    st.write("📊 **분석 기준**")
    st.write(f"기준선: {ma_options[selected_ma_day]}")
    st.caption("설명: 왼쪽의 이격률과 변동성은 이 기준선을 기초로 계산되었습니다.")

# --- 차트 영역 (기간 수익률 연동) ---
st.markdown("---")
tabs = st.tabs(["3개월", "6개월", "1년", "3년", "전체"])

# 차트 그리기 및 수익률 표시 함수
def make_chart_and_returns(df_in, period_desc, show_p=False):
    # 수익률 표시
    display_returns(df_in, period_desc)
    st.markdown("---")
    
    # 차트
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_in.index, open=df_in['Open'], high=df_in['High'], low=df_in['Low'], close=df_in['Close'], name="Price", opacity=0.5))
    
    # 이평선 범례 및 가시성 설정 (사이드바에서 선택한 것과 기본 240일선은 더 굵게)
    clrs = {5:'red', 20:'orange', 60:'green', 120:'blue', 240:'black'}
    for d, c in clrs.items():
        width = 2 if (d == selected_ma_day or d == 240) else 1.2
        fig.add_trace(go.Scatter(x=df_in.index, y=df_in[f'MA{d}'], name=f'{d}일선', line=dict(color=c, width=width)))
    
    # 골든/데드크로스 마커 (60일 vs 120일)
    gs = df_in[df_in['G']]
    ds = df_in[df_in['D']]
    fig.add_trace(go.Scatter(x=gs.index, y=gs['MA60'], mode='markers', marker=dict(symbol='triangle-up', size=10, color='red'), name='Golden Cross (60vs120)'))
    fig.add_trace(go.Scatter(x=ds.index, y=ds['MA60'], mode='markers', marker=dict(symbol='triangle-down', size=10, color='blue'), name='Dead Cross (60vs120)'))
    
    # [차트 컨트롤] 이동은 클릭 후 드래그, 확대는 스크롤
    fig.update_layout(height=600, template="plotly_white", xaxis_rangeslider_visible=False, dragmode='pan', margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

# 각 탭에 차트 및 동적 수익률 배치
with tabs[0]: make_chart_and_returns(data.iloc[-60:], "3개월")
with tabs[1]: make_chart_and_returns(data.iloc[-125:], "6개월")
with tabs[2]: make_chart_and_returns(data.iloc[-250:], "1년")
with tabs[3]: make_chart_and_returns(data.iloc[-750:], "3년")
with tabs[4]: make_chart_and_returns(data, "전체") # 10년 예측은 사용자 가이드에 없어 제거함 (요청시 추가 가능)

# --- 최하단: 투자 가이드 가시성 정리 ---
st.markdown("---")
st.subheader("📖 자산제곱 AI 투자 가이드북")

g_col1, g_col2, g_col3, g_col4 = st.columns(4)

with g_col1:
    st.markdown(f'<div class="guide-card"><div class="guide-title">1. 평균 회귀 원칙</div><div class="guide-text">'
                f'주가는 경기선(이평선)에서 너무 멀어지면 결국 자석처럼 다시 돌아오려는 성질이 있습니다. 이격률이 지나치게 높거나 낮으면 반대 방향으로 추세가 꺾일 징조입니다.'
                f'</div></div>', unsafe_allow_value=True)

with g_col2:
    st.markdown(f'<div class="guide-card"><div class="guide-title">2. 추세 판독기 (배열 상태)</div><div class="guide-text">'
                f'<b>정배열:</b> 단기선이 위에 있고 장기선이 아래에 있는 상승 추세. 주가가 눌릴 때가 매수 기회입니다.<br>'
                f'<b>역배열:</b> 장기선이 위에 있고 단기선이 아래에 있는 하락 추세. 주가가 눌리면 매도 또는 관망해야 합니다.'
                f'</div></div>', unsafe_allow_value=True)

with g_col3:
    st.markdown(f'<div class="guide-card"><div class="guide-title">3. 에너지 수렴 (에너지 응축)</div><div class="guide-text">'
                f'이평선들이 한곳으로 모이면 시장의 에너지가 응축된 상태입니다. 조만간 위든 아래든 강력한 방향성과 함께 **변동성이 매우 커질 징조**입니다.'
                f'</div></div>', unsafe_allow_value=True)

with g_col4:
    st.markdown(f'<div class="guide-card"><div class="guide-title">4. 크로스 신호 (골든 vs 데드)</div><div class="guide-text">'
                f'낮은 이평선(60일)이 높은 이평선(120일)을 뚫고 나오면 골든크로스(매수), 밑으로 가면 데드크로스(매도)입니다. 단, 주가는 이미 선반영되어 있어 **역발상 타이밍**으로 활용해야 할 수도 있습니다.'
                f'</div></div>', unsafe_allow_value=True)
