import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf

# -------------------------------
# 기본 설정
# -------------------------------
st.set_page_config(page_title="Tesla DCF Dashboard", page_icon="🚗", layout="wide")

st.title("🚗 Tesla DCF Valuation Dashboard")
st.markdown("테슬라(TSLA) 부문별 가정 기반 DCF(할인현금흐름) 밸류에이션 대시보드")


# -------------------------------
# 유틸 함수
# -------------------------------
@st.cache_data
def load_tesla_financials():
    tsla = yf.Ticker("TSLA")
    income = tsla.financials.T  # 연간 손익계산서
    balance = tsla.balance_sheet.T
    cashflow = tsla.cashflow.T
    info = tsla.info
    return income, balance, cashflow, info


def prepare_base_revenue(income):
    # 가장 최근 연도의 매출을 기준으로 사용
    latest_year = income.index[0]
    total_revenue = float(income.loc[latest_year, "Total Revenue"])
    return latest_year.year, total_revenue


def run_dcf(
    base_revenue_auto,
    base_revenue_energy,
    base_revenue_service,
    years,
    g_auto,
    g_energy,
    g_service,
    ebit_margin_auto,
    ebit_margin_energy,
    ebit_margin_service,
    tax_rate,
    capex_ratio,
    wc_ratio,
    wacc,
    terminal_g,
):
    n = len(years)
    df = pd.DataFrame(index=years)

    # 매출 예측
    df["rev_auto"] = base_revenue_auto * (1 + g_auto) ** np.arange(n)
    df["rev_energy"] = base_revenue_energy * (1 + g_energy) ** np.arange(n)
    df["rev_service"] = base_revenue_service * (1 + g_service) ** np.arange(n)
    df["revenue"] = df["rev_auto"] + df["rev_energy"] + df["rev_service"]

    # EBIT
    df["ebit"] = (
        df["rev_auto"] * ebit_margin_auto
        + df["rev_energy"] * ebit_margin_energy
        + df["rev_service"] * ebit_margin_service
    )

    # NOPAT
    df["nopat"] = df["ebit"] * (1 - tax_rate)

    # CAPEX & WC
    df["capex"] = df["revenue"] * capex_ratio
    df["wc_increase"] = df["revenue"].diff().fillna(0) * wc_ratio

    # FCFF
    df["fcff"] = df["nopat"] - df["capex"] - df["wc_increase"]

    # 할인계수
    df["t"] = np.arange(1, n + 1)
    df["discount_factor"] = 1 / (1 + wacc) ** df["t"]
    df["discounted_fcff"] = df["fcff"] * df["discount_factor"]

    # Terminal Value
    terminal_fcff = df["fcff"].iloc[-1] * (1 + terminal_g)
    terminal_value = terminal_fcff / (wacc - terminal_g)
    discounted_terminal = terminal_value * df["discount_factor"].iloc[-1]

    enterprise_value = df["discounted_fcff"].sum() + discounted_terminal

    return df, enterprise_value, terminal_value, discounted_terminal


# -------------------------------
# 사이드바 입력 영역
# -------------------------------
st.sidebar.header("입력 가정 설정")

with st.sidebar.expander("1️⃣ 데이터 소스 및 기간", expanded=True):
    use_yf = st.checkbox("yfinance에서 최신 TSLA 재무데이터 사용", value=True)
    forecast_years = st.slider("예측 기간 (년)", min_value=5, max_value=15, value=10)
    start_year = st.number_input(
        "DCF 시작 연도", min_value=2024, max_value=2100, value=2025
    )

with st.sidebar.expander("2️⃣ 부문별 기준 매출 (Base Year)", expanded=True):
    if use_yf:
        try:
            income, balance, cashflow, info = load_tesla_financials()
            base_year, total_rev = prepare_base_revenue(income)
            st.caption(
                f"yfinance 기준 최근 연도: {base_year}년, 매출: {total_rev/1e9:,.1f} Bn USD"
            )

            base_auto = st.number_input(
                "자동차 매출 (Bn USD)", value=float(total_rev * 0.85 / 1e9)
            )
            base_energy = st.number_input(
                "에너지 매출 (Bn USD)", value=float(total_rev * 0.10 / 1e9)
            )
            base_service = st.number_input(
                "서비스 매출 (Bn USD)", value=float(total_rev * 0.05 / 1e9)
            )
        except Exception as e:
            st.warning(f"yfinance 로딩 실패: {e}")
            base_auto = st.number_input("자동차 매출 (Bn USD)", value=220.0)
            base_energy = st.number_input("에너지 매출 (Bn USD)", value=30.0)
            base_service = st.number_input("서비스 매출 (Bn USD)", value=20.0)
    else:
        base_auto = st.number_input("자동차 매출 (Bn USD)", value=220.0)
        base_energy = st.number_input("에너지 매출 (Bn USD)", value=30.0)
        base_service = st.number_input("서비스 매출 (Bn USD)", value=20.0)

with st.sidebar.expander("3️⃣ 성장률 가정 (연평균)", expanded=True):
    g_auto = st.slider("자동차 매출 성장률", -0.05, 0.20, 0.05)
    g_energy = st.slider("에너지 매출 성장률", 0.00, 0.40, 0.20)
    g_service = st.slider("서비스 매출 성장률", 0.00, 0.30, 0.10)

with st.sidebar.expander("4️⃣ 마진 및 투자 가정", expanded=False):
    ebit_margin_auto = st.slider("자동차 EBIT 마진", 0.00, 0.20, 0.07)
    ebit_margin_energy = st.slider("에너지 EBIT 마진", 0.00, 0.25, 0.12)
    ebit_margin_service = st.slider("서비스 EBIT 마진", 0.00, 0.25, 0.10)

    tax_rate = st.slider("법인세율", 0.10, 0.30, 0.20)
    capex_ratio = st.slider("CAPEX / 매출", 0.01, 0.15, 0.05)
    wc_ratio = st.slider("운전자본 증가 / 매출증가", 0.00, 0.20, 0.01)

with st.sidebar.expander("5️⃣ 할인율 및 말기가치", expanded=False):
    calc_auto_wacc = st.checkbox("베타 기반 WACC 자동 계산 (yfinance)", value=False)

    if calc_auto_wacc and use_yf:
        try:
            beta = info.get("beta", 2.0)
            rf = 0.045  # 미국 10년물 수동 가정 (원하면 UI로 뺄 수 있음)
            mrp = 0.055
            cost_equity = rf + beta * mrp
            wacc = st.number_input(
                "WACC",
                value=float(cost_equity),
                min_value=0.01,
                max_value=0.20,
                step=0.005,
            )
            st.caption(
                f"(자동 계산 참고) Beta={beta:.2f}, Cost of Equity≈{cost_equity:.2%}"
            )
        except Exception as e:
            st.warning(f"WACC 자동 계산 실패: {e}")
            wacc = st.number_input(
                "WACC", value=0.09, min_value=0.01, max_value=0.20, step=0.005
            )
    else:
        wacc = st.number_input(
            "WACC", value=0.09, min_value=0.01, max_value=0.20, step=0.005
        )

    terminal_g = st.slider("말기가치 영구 성장률 (g)", 0.00, 0.05, 0.025)

# -------------------------------
# 메인 컨텐츠
# -------------------------------
col_top_left, col_top_right = st.columns([2, 1])

with col_top_left:
    st.subheader("📈 DCF 결과 개요")

    years = np.arange(start_year, start_year + forecast_years)
    df, ev, tv, disc_tv = run_dcf(
        base_auto * 1e9,
        base_energy * 1e9,
        base_service * 1e9,
        years,
        g_auto,
        g_energy,
        g_service,
        ebit_margin_auto,
        ebit_margin_energy,
        ebit_margin_service,
        tax_rate,
        capex_ratio,
        wc_ratio,
        wacc,
        terminal_g,
    )

    st.metric("Enterprise Value (EV)", f"${ev/1e9:,.1f} Bn")
    st.caption(
        f"할인된 Terminal Value: ${disc_tv/1e9:,.1f} Bn (비중 {disc_tv/ev:,.1%})"
    )

    st.markdown("### FCFF 추이")
    st.line_chart(df[["fcff", "discounted_fcff"]])

with col_top_right:
    st.subheader("💡 가정 요약")
    st.write(f"- 예측 기간: **{start_year}–{start_year + forecast_years - 1}**")
    st.write(f"- WACC: **{wacc:.2%}**")
    st.write(f"- Terminal g: **{terminal_g:.2%}**")
    st.write(f"- 자동차 성장률: **{g_auto:.2%}**")
    st.write(f"- 에너지 성장률: **{g_energy:.2%}**")
    st.write(f"- 서비스 성장률: **{g_service:.2%}**")

    st.write("---")
    st.markdown("#### 부문별 기준 매출 (Base Year)")
    st.write(f"- Auto: **${base_auto:,.1f} Bn**")
    st.write(f"- Energy: **${base_energy:,.1f} Bn**")
    st.write(f"- Service: **${base_service:,.1f} Bn**")

st.markdown("---")

st.subheader("📊 상세 테이블")
st.dataframe(
    df[
        [
            "rev_auto",
            "rev_energy",
            "rev_service",
            "revenue",
            "ebit",
            "nopat",
            "capex",
            "wc_increase",
            "fcff",
            "discounted_fcff",
        ]
    ].style.format("{:,.0f}")
)

# -------------------------------
# 선택: 현재 TSLA 시가총액과 비교
# -------------------------------
with st.expander("📌 현재 TSLA 시가총액과 비교 (yfinance)", expanded=False):
    try:
        tsla = yf.Ticker("TSLA")
        live_price = tsla.history(period="1d")["Close"].iloc[-1]
        shares_out = tsla.info.get("sharesOutstanding", None)

        if shares_out:
            equity_value_per_share = ev / shares_out
            mkt_cap = live_price * shares_out

            col1, col2 = st.columns(2)
            with col1:
                st.metric("현재 TSLA 주가", f"${live_price:,.2f}")
                st.metric("현재 시가총액", f"${mkt_cap/1e9:,.1f} Bn")
            with col2:
                st.metric("DCF 내재가치(주당)", f"${equity_value_per_share:,.2f}")
                premium = equity_value_per_share / live_price - 1
                st.metric("DCF 대비 Upside(Downside)", f"{premium:.1%}")
        else:
            st.write("sharesOutstanding 정보를 가져오지 못했습니다.")
    except Exception as e:
        st.warning(f"TSLA 시가총액 로딩 실패: {e}")
