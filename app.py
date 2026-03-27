import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 및 프리미엄 스타일 (Executive & Beginner Friendly)
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
    .macro-section {{ background-color: #1a1c1e; padding: 40px; border-radius: 25px; margin-top: 50px; color: white; }}
    .situation-box {{ background-color: rgba(255,255,255,0.07); padding: 15px; border-radius: 10px; border-left: 4px solid #fab005; font-size: 13px; margin-top: 10px; line-height: 1.6; color: #ced4da; }}
    .buffett-card {{ background-color: rgba(255,255,255,0.1); padding: 20px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); text-align: center; }}
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 수집 엔진
@st.cache_data(ttl=3600)
def load_all_market_intelligence(ticker):
    df = yf.download(ticker, start="2000-01-01", auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    for m in [5, 20, 60, 120, 240]:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    df['G'] = (df['MA60'].shift(1) < df['MA120'].shift(1)) & (df['MA60'] > df['MA120'])
    df['D'] = (df['MA60'].shift(1) > df['MA120'].shift(1)) & (df['MA60'] < df['MA120'])
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    # 매크로 데이터 로드 (시작 시점 2010년으로 조정)
    macros = {"US_Rate": "^TNX", "Oil": "CL=F", "Dollar": "DX-Y.NYB", "VIX": "^VIX", "SP500": "^GSPC", "KOSPI": "^KS11"}
    macro_res = {}
    for k, t in macros.items():
        d = yf.download(t, start="2010-01-01", auto_adjust=True)
        if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
        macro_res[k] = d['Close']
    return df.dropna(subset=['MA240']), macro_res

indices = {"NASDAQ Composite": "^IXIC", "NASDAQ 100": "^NDX", "S&P 500": "^GSPC", "KOSPI": "^KS11", "KOSDAQ": "^KQ11"}
choice = st.sidebar.radio("📋 분석 대상 선택", list(indices.keys()))
data, appendix_data = load_all_market_intelligence(indices[choice])

last = data.iloc[-1]
curr, ma60, ma120, rsi = float(last['Close']), float(last['MA60']), float(last['MA120']), float(last['RSI'])

# 3. 버핏 지수 정밀 계산 (2026 데이터 보정)
def calc_buffett(sp_val, ks_val):
    # US GDP 2026: 29.5T / KR GDP: 2550T (추정치 업데이트)
    # S&P500 지수 대비 시총 배수 9.2 / KOSPI 지수 대비 시총 배수 0.78 (보수적 조정)
    us_ratio = (sp_val * 9.2 / 1000 / 29.5) * 100
    kr_ratio = (ks_val * 0.78 / 2550) * 100
    us_stat = "고평가" if us_ratio > 160 else ("저평가" if us_ratio < 110 else "적정")
    kr_stat = "고평가" if kr_ratio > 100 else ("저평가" if kr_ratio < 75 else "적정")
    return (us_ratio, us_stat), (kr_ratio, kr_stat)

(us_buff, us_stat), (kr_buff, kr_stat) = calc_buffett(appendix_data['SP500'].iloc[-1], appendix_data['KOSPI'].iloc[-1])

# 4. 상단 AI 투자 의견
score = 0
if ma60 > ma120: score += 2
if rsi < 40: score += 2
elif rsi > 65: score -= 2
curr_stat = us_stat if "NASDAQ" in choice or "S&P" in choice else kr_stat
if "저평가" in curr_stat: score += 1

if score >= 2: verdict, v_class = "긍정 (Buy / 적극 투자)", "positive-v"
elif score <= -1: verdict, v_class = "부정 (Caution / 비중 축소)", "negative-v"
else: verdict, v_class = "중립 (Neutral / 관망)", "neutral-v"

st.title(f"📊 {choice} 전략 보고서")
st.markdown(f'''<div class="verdict-box {v_class}"><div class="date-badge">기준 날짜: {today_str}</div><div style="font-size:12px; font-weight:700; opacity:0.7;">AI EXECUTIVE VERDICT (최종 의견)</div><div class="v-content">{verdict}</div></div>''', unsafe_allow_html=True)

# 5. 핵심 지표 진단 카드
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="info-card"><div class="card-title">Trend (60/120)</div><div class="card-val">{"상승 추세" if ma60 > ma120 else "하락 추세"}</div><div class="card-caption">중기 수급선(60)이 장기 경기선(120) 위에 있는지 확인합니다.</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="info-card"><div class="card-title">이격도 (Mean Reversion)</div><div class="card-val">{(curr/ma120*100):.1f}%</div><div class="card-caption">평균 가격에서 얼마나 멀어졌는지 봅니다. 110% 이상은 고점 경고입니다.</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="info-card"><div class="card-title">심리 지수 (RSI)</div><div class="card-val">{rsi:.1f}</div><div class="card-caption">70 이상이면 다들 너무 흥분(탐욕), 30 이하면 다들 패닉(공포) 상태입니다.</div></div>', unsafe_allow_html=True)

# 6. 메인 차트 영역
st.markdown("---")
tabs = st.tabs(["6개월", "1년", "5년", "10년", "전체"])
d_map = {"6개월":132, "1년":252, "5년":1260, "10년":2520}

def render_main_chart(df_sub):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_sub.index, open=df_sub['Open'], high=df_sub['High'], low=df_sub['Low'], close=df_sub['Close'], name="주가", opacity=0.4))
    cols = {60:'#008000', 120:'#0000FF', 240:'#800080'}
    for d, c in cols.items():
        if f'MA{d}' in df_sub.columns:
            fig.add_trace(go.Scatter(x=df_sub.index, y=df_sub[f'MA{d}'], name=f'{d}일선', line=dict(color=c, width=1.5)))
    fig.update_layout(height=500, template="plotly_white", xaxis_rangeslider_visible=False, dragmode='pan', hovermode='x unified', margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[df_sub.index.min(), df_sub.index.max()]))
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

for i, name in enumerate(["6개월", "1년", "5년", "10년", "전체"]):
    with tabs[i]:
        d_count = d_map.get(name, len(data))
        render_main_chart(data.iloc[-d_count:])

# 7. 하단 부록: 글로벌 매크로 및 밸류에이션 (표 수정 및 설명 추가)
st.markdown('<div class="macro-section"><h2>📎 부록: 글로벌 매크로 및 밸류에이션 리포트</h2>', unsafe_allow_html=True)

# 버핏 지수 섹션 (디자인 수정)
st.markdown("### 🏛️ 버핏 지수 (GDP 대비 시가총액 비율)")
b1, b2 = st.columns(2)
with b1: st.markdown(f'<div class="buffett-card"><b>미국(US)</b><br><span style="font-size:24px;">{us_buff:.1f}%</span><br>상태: <b>{us_stat}</b></div>', unsafe_allow_html=True)
with b2: st.markdown(f'<div class="buffett-card"><b>한국(KR)</b><br><span style="font-size:24px;">{kr_buff:.1f}%</span><br>상태: <b>{kr_stat}</b></div>', unsafe_allow_html=True)
st.caption("※ 버핏 지수 가이드: 100%를 적정으로 보며, 미국은 역사적으로 150% 이상, 한국은 100% 이상일 때 시장이 매우 비싸다고 판단합니다.")

st.markdown("---")
m_tabs = st.tabs(["1년 추이", "5년 추이", "10년 추이"])
m_days = {"1년 추이": 252, "5년 추이": 1260, "10년 추이": 2520}

for i, t_name in enumerate(["1년 추이", "5년 추이", "10년 추이"]):
    with m_tabs[i]:
        d = m_days[t_name]
        col1, col2 = st.columns(2); col3, col4 = st.columns(2)
        
        # 각 지표별 렌더링 및 초보자용 상황 진단
        def draw_m(series, title, color, name):
            fig = go.Figure(go.Scatter(x=series.index[-d:], y=series.values[-d:], line=dict(color=color, width=2)))
            fig.update_layout(height=200, title=title, template="plotly_dark", margin=dict(l=10, r=10, t=40, b=10), hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            # 상황 진단 로직
            curr_v, prev_v = series.iloc[-1], series.iloc[-22]
            diff = curr_v - prev_v
            if name == "Rate": msg = f"현재 {curr_v:.2f}% ({diff:+.2f}%). 금리가 오르면 기업의 이자 부담이 커져 주가엔 부정적입니다."
            elif name == "Oil": msg = f"현재 ${curr_v:.2f}. 유가가 오르면 물가가 상승해 금리를 내리기 어려워집니다."
            elif name == "Dollar": msg = f"현재 {curr_v:.2f}. 달러가 강해지면 외국인이 한국 주식을 팔고 떠날 확률이 높습니다."
            else: msg = f"현재 {curr_v:.2f}. 지수가 20을 넘으면 시장이 매우 불안하다는 신호입니다."
            st.markdown(f'<div class="situation-box"><b>💡 초보자 가이드:</b> {msg}</div>', unsafe_allow_html=True)

        with col1: draw_m(appendix_data['US_Rate'], "미 국채 10년 금리", "#ff6b6b", "Rate")
        with col2: draw_m(appendix_data['Oil'], "WTI 유가", "#adb5bd", "Oil")
        with col3: draw_m(appendix_data['Dollar'], "달러 인덱스", "#4dadf7", "Dollar")
        with col4: draw_m(appendix_data['VIX'], "VIX 공포지수", "#fab005", "VIX")

st.markdown('</div>', unsafe_allow_html=True)

# 8. 초보자 마스터 가이드 (클릭 시 펼쳐짐)
with st.expander("🎓 **초보자도 1분 만에 이해하는 지표 읽는 법 (마스터 가이드)**"):
    st.write("""
    1. **금리(Rate):** '돈의 값어치'입니다. 금리가 오르면 돈 빌리기가 힘들어져 주식 시장에 들어오는 돈이 줄어듭니다. (주가에 하락 요인)
    2. **유가(Oil):** '물가의 기초'입니다. 유가가 너무 오르면 물가가 오르고, 물가를 잡으려고 금리를 또 올리게 되는 악순환이 생깁니다.
    3. **달러(Dollar):** '안전자산의 상징'입니다. 달러가 비싸지면 전 세계 돈이 미국으로 쏠리면서 한국 같은 신흥국 주식 시장은 힘이 빠집니다.
    4. **VIX(공포지수):** '시장의 비명 소리'입니다. 지수가 갑자기 솟구치면 누군가 큰 손해를 보고 투매하고 있다는 뜻입니다.
    5. **버핏 지수:** 한 나라의 경제 크기(GDP)에 비해 주식 시장이 얼마나 무거운지 봅니다. 몸집보다 가방이 너무 무거우면 언젠가 주저앉겠죠?
    """)
