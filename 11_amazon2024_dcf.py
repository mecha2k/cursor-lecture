from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
import streamlit as st

# ============================================================
# 1) DCF 입력 파라미터 데이터 클래스
# ============================================================


@dataclass
class DCFInputs:
    # 기본 재무
    base_revenue: float  # 기준 연도 매출 (Most recent 12M)
    base_ebit_margin: float  # 기준/다음 해 EBIT 마진
    effective_tax_rate: float  # 현재 유효 세율
    marginal_tax_rate: float  # 장기 한계 세율

    # 성장/마진 가정
    g_year1: float  # 다음 해 매출 성장률
    g_years2_5: float  # 2~5년 복리 성장률
    target_ebit_margin: float  # 장기 목표 EBIT 마진
    margin_convergence_year: int  # 마진이 목표치에 수렴하는 연도(예: 5년)

    # 재투자 (Sales to capital ratio)
    sales_to_capital_yrs1_5: float  # 1~5년 Sales/Capital
    sales_to_capital_yrs6_10: float  # 6~10년 Sales/Capital

    # 할인율
    initial_wacc: float  # 초기 WACC
    terminal_wacc: float  # 터미널(안정기) WACC

    # 터미널 성장/ROIC
    terminal_growth: float  # 안정기 성장률 (보통 장기 무위험+인플레 수준)
    terminal_roic: float  # 안정기 ROIC (Return on invested capital)

    # 자본 구조 (Equity bridge)
    debt: float  # 시가 기준 부채
    cash: float  # 현금 및 현금성 자산
    non_operating_assets: float  # 비영업자산 (예: 지분법 투자 등)
    options_value: float  # 스톡옵션 가치
    shares_outstanding: float  # 발행 주식 수

    # 진단용 Invested capital
    base_invested_capital: float  # 현재 투자자본(자기자본+이자부채-현금 등)

    # 파산 확률 관련 (보통 0으로 두면 됨)
    prob_failure: float = 0.0  # 파산 확률 (0~1)
    recovery_rate: float = 0.5  # 파산 시 회수율 (0~1)


# ============================================================
# 2) 경로 생성 함수들
# ============================================================


def build_growth_path(inputs: DCFInputs, horizon_years: int = 10) -> np.ndarray:
    """
    매출 성장률 경로
      - 1년차: g_year1
      - 2~5년차: g_years2_5
      - 6~10년차: 5년 성장률 → terminal_growth 로 선형 수렴
      - 11년차(터미널): terminal_growth
    """
    g = np.zeros(horizon_years + 2)  # index 0..11

    # 1~5년
    for t in range(1, min(5, horizon_years) + 1):
        g[t] = inputs.g_year1 if t == 1 else inputs.g_years2_5

    # 6~10년: 선형 수렴
    if horizon_years >= 6:
        step = (inputs.g_years2_5 - inputs.terminal_growth) / (10 - 5)
        for t in range(6, horizon_years + 1):
            g[t] = inputs.g_years2_5 - step * (t - 5)

    # 터미널 연도
    g[horizon_years + 1] = inputs.terminal_growth
    return g


def build_margin_path_excel_style(
    inputs: DCFInputs, horizon_years: int = 10
) -> np.ndarray:
    """
    마진(EBIT Margin) 수렴 경로
      - 0년(Base): base_margin
      - 1년차: base_margin
      - 2~N년차: base + (target - base) * (t / N)
      - N년 이후: target
    """
    m = np.zeros(horizon_years + 2)
    base = inputs.base_ebit_margin
    target = inputs.target_ebit_margin
    N = inputs.margin_convergence_year

    m[0] = base
    for t in range(1, horizon_years + 1):
        if t == 1:
            m[t] = base
        elif t <= N:
            m[t] = base + (target - base) * (t / N)
        else:
            m[t] = target

    m[horizon_years + 1] = target
    return m


def build_tax_path(inputs: DCFInputs, horizon_years: int = 10) -> np.ndarray:
    """
    세율 경로
      - 0~5년차: Effective tax
      - 6~10년차: Marginal tax 로 선형 수렴
      - 터미널: Marginal tax
    """
    tr = np.zeros(horizon_years + 2)
    eff = inputs.effective_tax_rate
    mar = inputs.marginal_tax_rate

    for t in range(0, 6):
        tr[t] = eff
    for t in range(6, horizon_years + 1):
        frac = (t - 5) / 5
        tr[t] = eff + (mar - eff) * frac
    tr[horizon_years + 1] = mar
    return tr


def build_wacc_path(inputs: DCFInputs, horizon_years: int = 10) -> np.ndarray:
    """
    WACC 경로
      - 1~5년차: initial_wacc
      - 6~10년차: terminal_wacc 로 선형 수렴
      - 터미널: terminal_wacc
    """
    w = np.zeros(horizon_years + 2)
    init = inputs.initial_wacc
    term = inputs.terminal_wacc

    for t in range(1, 5 + 1):
        w[t] = init

    step = (init - term) / 5
    for t in range(6, horizon_years + 1):
        w[t] = init - step * (t - 5)

    w[horizon_years + 1] = term
    return w


# ============================================================
# 3) 메인 DCF 실행 함수
# ============================================================


def run_dcf(inputs: DCFInputs, horizon_years: int = 10):
    """
    10년 DCF + 터미널 밸류 계산
    """
    # 1) 경로 생성
    g = build_growth_path(inputs, horizon_years)
    m = build_margin_path_excel_style(inputs, horizon_years)
    tr = build_tax_path(inputs, horizon_years)
    wac = build_wacc_path(inputs, horizon_years)

    years = list(range(0, horizon_years + 2))  # 0..11

    # 2) 매출 경로
    rev = np.zeros(horizon_years + 2)
    rev[0] = inputs.base_revenue
    for t in range(1, horizon_years + 1):
        rev[t] = rev[t - 1] * (1 + g[t])
    # 터미널 (11년차)
    rev[horizon_years + 1] = rev[horizon_years] * (1 + g[horizon_years + 1])

    # 3) EBIT & 세후 EBIT
    ebit = rev * m
    ebit_1_t = ebit * (1 - tr)

    # 4) Sales to capital ratio 경로
    stc = np.zeros(horizon_years + 2)
    for t in range(1, min(5, horizon_years) + 1):
        stc[t] = inputs.sales_to_capital_yrs1_5
    for t in range(6, horizon_years + 1):
        stc[t] = inputs.sales_to_capital_yrs6_10
    stc[horizon_years + 1] = inputs.sales_to_capital_yrs6_10

    # 5) 재투자
    reinv = np.zeros(horizon_years + 2)
    # 1~9년: 다음 해 매출 증가분 기반
    for t in range(1, horizon_years):
        reinv[t] = (rev[t + 1] - rev[t]) / stc[t]
    # 10년차: 10→11년(터미널) 매출 증가분
    reinv[horizon_years] = (rev[horizon_years + 1] - rev[horizon_years]) / stc[
        horizon_years
    ]
    # 터미널: g/ROIC * EBIT(1-t)
    reinv[horizon_years + 1] = (
        inputs.terminal_growth / inputs.terminal_roic
    ) * ebit_1_t[horizon_years + 1]

    # 6) FCFF
    fcff = np.zeros(horizon_years + 2)
    for t in range(1, horizon_years + 1):
        fcff[t] = ebit_1_t[t] - reinv[t]
    # 터미널 연도 FCFF (TV용)
    fcff_terminal = ebit_1_t[horizon_years + 1] - reinv[horizon_years + 1]

    # 7) 할인계수 & PV(FCFF)
    cum_df = np.zeros(horizon_years + 2)
    pv_fcff = np.zeros(horizon_years + 2)
    cum_df[0] = 1.0
    for t in range(1, horizon_years + 1):
        cum_df[t] = cum_df[t - 1] / (1 + wac[t])
        pv_fcff[t] = fcff[t] * cum_df[t]

    # 8) 터미널 밸류 & PV
    tv = fcff_terminal / (inputs.terminal_wacc - inputs.terminal_growth)
    df_terminal = cum_df[horizon_years]
    pv_terminal = tv * df_terminal

    # 9) 1~10년 PV 합, 총합
    pv_cf_1_10 = pv_fcff[1 : horizon_years + 1].sum()
    sum_pv = pv_cf_1_10 + pv_terminal

    # 10) 파산 가능성 반영 (필요 시)
    if inputs.prob_failure > 0:
        proceeds_if_fail = sum_pv * inputs.recovery_rate
        value_operating_assets = (
            sum_pv * (1 - inputs.prob_failure) + proceeds_if_fail * inputs.prob_failure
        )
    else:
        value_operating_assets = sum_pv

    # 11) Equity bridge
    value_equity = (
        value_operating_assets - inputs.debt + inputs.cash + inputs.non_operating_assets
    )
    value_equity_common = value_equity - inputs.options_value
    value_per_share = value_equity_common / inputs.shares_outstanding

    # 12) Invested capital & ROIC 진단
    invested = np.zeros(horizon_years + 1)
    invested[0] = inputs.base_invested_capital
    for t in range(1, horizon_years + 1):
        invested[t] = invested[t - 1] + reinv[t]
    roic = ebit_1_t[: horizon_years + 1] / invested

    df = pd.DataFrame(
        {
            "year": years,
            "growth": g,
            "revenue": rev,
            "ebit_margin": m,
            "ebit": ebit,
            "tax_rate": tr,
            "ebit_1_t": ebit_1_t,
            "sales_to_capital": stc,
            "reinvestment": reinv,
            "fcff": fcff,
            "wacc": wac,
            "cum_discount_factor": cum_df,
            "pv_fcff": pv_fcff,
        }
    )

    diag = pd.DataFrame(
        {
            "year": list(range(0, horizon_years + 1)),
            "invested_capital": invested,
            "roic": roic,
        }
    )

    summary = {
        "pv_cf_1_10": pv_cf_1_10,
        "terminal_value": tv,
        "pv_terminal_value": pv_terminal,
        "sum_pv": sum_pv,
        "value_operating_assets": value_operating_assets,
        "value_equity": value_equity,
        "value_equity_common": value_equity_common,
        "value_per_share": value_per_share,
    }

    return df, diag, summary


# ============================================================
# 4) Streamlit UI
# ============================================================


def main():
    st.set_page_config(page_title="DCF Valuation Dashboard", layout="wide")
    st.title("📊 DCF Valuation 대시보드 (Damodaran 스타일)")

    st.sidebar.header("기본 회사 정보 / 규모")
    company_name = st.sidebar.text_input("회사명", "Amazon (예시)")

    # --- 규모 관련 (단위: million USD 기준 예시) ---
    base_revenue = st.sidebar.number_input(
        "기준 매출 (Base Revenue)",
        min_value=0.0,
        value=574_785.0,
        step=10_000.0,
        help="최근 12개월 매출 (예: million 단위)",
    )
    base_ebit_margin = st.sidebar.slider(
        "기준 EBIT 마진",
        min_value=0.0,
        max_value=0.3,
        value=0.113,
        step=0.005,
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("세율")
    effective_tax = st.sidebar.slider(
        "유효 세율 (Effective Tax Rate)",
        min_value=0.0,
        max_value=0.5,
        value=0.19,
        step=0.01,
    )
    marginal_tax = st.sidebar.slider(
        "한계 세율 (Marginal Tax Rate)",
        min_value=0.0,
        max_value=0.5,
        value=0.25,
        step=0.01,
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("성장률 가정")
    g_y1 = st.sidebar.slider(
        "1년차 매출 성장률 g1", min_value=0.0, max_value=0.4, value=0.12, step=0.01
    )
    g_y2_5 = st.sidebar.slider(
        "2~5년차 매출 성장률 g2-5", min_value=0.0, max_value=0.4, value=0.12, step=0.01
    )
    terminal_growth = st.sidebar.slider(
        "터미널 성장률 g(안정기)",
        min_value=0.0,
        max_value=0.06,
        value=0.0408,
        step=0.001,
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("마진 / 재투자 가정")
    target_margin = st.sidebar.slider(
        "장기 목표 EBIT 마진", min_value=0.0, max_value=0.3, value=0.14, step=0.005
    )
    margin_convergence_year = st.sidebar.slider(
        "마진 수렴 기간 (년)", min_value=3, max_value=10, value=5, step=1
    )
    stc_1_5 = st.sidebar.slider(
        "Sales to Capital (1~5년)", min_value=0.5, max_value=5.0, value=2.0, step=0.1
    )
    stc_6_10 = st.sidebar.slider(
        "Sales to Capital (6~10년)", min_value=0.5, max_value=5.0, value=2.0, step=0.1
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("WACC / ROIC")
    initial_wacc = st.sidebar.slider(
        "초기 WACC", min_value=0.02, max_value=0.20, value=0.086, step=0.002
    )
    terminal_wacc = st.sidebar.slider(
        "터미널 WACC", min_value=0.02, max_value=0.20, value=0.08, step=0.002
    )
    terminal_roic = st.sidebar.slider(
        "터미널 ROIC", min_value=0.05, max_value=0.30, value=0.16, step=0.01
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("자본 구조 / 기타")
    shares_outstanding = st.sidebar.number_input(
        "발행 주식 수", min_value=1.0, value=10_492.0, step=100.0
    )
    debt = st.sidebar.number_input(
        "부채 (시가)", min_value=0.0, value=164_036.0, step=10_000.0
    )
    cash = st.sidebar.number_input(
        "현금 및 현금성 자산", min_value=0.0, value=86_780.0, step=10_000.0
    )
    non_op_assets = st.sidebar.number_input(
        "비영업자산", min_value=0.0, value=0.0, step=1_000.0
    )
    options_value = st.sidebar.number_input(
        "스톡옵션 가치", min_value=0.0, value=10_000.0, step=1_000.0
    )
    base_invested_capital = st.sidebar.number_input(
        "기초 투자자본 (Invested Capital)",
        min_value=0.0,
        value=257_360.0,
        step=10_000.0,
    )

    # --------------------------------------------------------
    # DCF 실행
    # --------------------------------------------------------
    inputs = DCFInputs(
        base_revenue=base_revenue,
        base_ebit_margin=base_ebit_margin,
        effective_tax_rate=effective_tax,
        marginal_tax_rate=marginal_tax,
        g_year1=g_y1,
        g_years2_5=g_y2_5,
        target_ebit_margin=target_margin,
        margin_convergence_year=margin_convergence_year,
        sales_to_capital_yrs1_5=stc_1_5,
        sales_to_capital_yrs6_10=stc_6_10,
        initial_wacc=initial_wacc,
        terminal_wacc=terminal_wacc,
        terminal_growth=terminal_growth,
        terminal_roic=terminal_roic,
        debt=debt,
        cash=cash,
        non_operating_assets=non_op_assets,
        options_value=options_value,
        shares_outstanding=shares_outstanding,
        base_invested_capital=base_invested_capital,
        prob_failure=0.0,
        recovery_rate=0.5,
    )

    df, diag, summary = run_dcf(inputs)

    # --------------------------------------------------------
    # 화면 표시
    # --------------------------------------------------------
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"{company_name} DCF 결과 요약")
        st.markdown("**Enterprise Value → Equity Value → 주당 가치**")

        st.metric(
            "운영자산 가치 (Enterprise Value)",
            f"{summary['value_operating_assets']:,.0f}",
        )
        st.metric(
            "지분가치 (Equity Value, options 차감 전)",
            f"{summary['value_equity']:,.0f}",
        )
        st.metric(
            "지분가치 (일반주, options 차감 후)",
            f"{summary['value_equity_common']:,.0f}",
        )
        st.metric("주당 가치 (Value per share)", f"{summary['value_per_share']:,.2f}")

        st.markdown("---")
        st.markdown("### 1~10년 FCFF 및 현재가치")
        chart_df = df.set_index("year").loc[1:10, ["fcff", "pv_fcff"]]
        st.line_chart(chart_df)

    with col2:
        st.markdown("### 10년 PV & 터미널 밸류 분해")
        st.write(
            pd.DataFrame(
                {
                    "항목": [
                        "PV(1~10년 FCFF)",
                        "PV(Terminal Value)",
                        "합계 (Enterprise Value 기준)",
                    ],
                    "값": [
                        summary["pv_cf_1_10"],
                        summary["pv_terminal_value"],
                        summary["sum_pv"],
                    ],
                }
            )
        )

        st.markdown("---")
        st.markdown("### Invested Capital & ROIC")
        st.dataframe(
            diag.style.format({"invested_capital": "{:,.0f}", "roic": "{:.3f}"})
        )

    st.markdown("---")
    st.markdown("### 세부 테이블 (Valuation Output 스타일)")
    st.dataframe(
        df.style.format(
            {
                "revenue": "{:,.0f}",
                "ebit_margin": "{:.3f}",
                "ebit": "{:,.0f}",
                "tax_rate": "{:.3f}",
                "ebit_1_t": "{:,.0f}",
                "reinvestment": "{:,.0f}",
                "fcff": "{:,.0f}",
                "wacc": "{:.3f}",
                "cum_discount_factor": "{:.4f}",
                "pv_fcff": "{:,.0f}",
            }
        )
    )

    # --------------------------------------------------------
    # 성장률 × 마진 2D 감도분석
    # --------------------------------------------------------
    st.markdown("---")
    st.header("📈 성장률 × 마진 2D 감도분석 (Value per share)")

    # 감도 범위/격자 설정
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        g_min = st.number_input("성장률(2~5년) 최소값", 0.00, 0.40, 0.08, 0.01)
    with col_s2:
        g_max = st.number_input("성장률(2~5년) 최대값", 0.00, 0.40, 0.16, 0.01)
    with col_s3:
        n_g = st.slider("성장률 그리드 개수", 3, 11, 5, 1)

    col_s4, col_s5, col_s6 = st.columns(3)
    with col_s4:
        m_min = st.number_input("목표 마진 최소값", 0.00, 0.30, 0.10, 0.005)
    with col_s5:
        m_max = st.number_input("목표 마진 최대값", 0.00, 0.30, 0.18, 0.005)
    with col_s6:
        n_m = st.slider("마진 그리드 개수", 3, 11, 5, 1)

    # 그리드 생성
    g_list = np.linspace(g_min, g_max, n_g)
    m_list = np.linspace(m_min, m_max, n_m)

    sens_matrix = np.zeros((n_g, n_m))

    # 현재 inputs를 그대로 쓰되, g_years2_5 / target_ebit_margin만 바꿔가며 계산
    for i, g_sens in enumerate(g_list):
        for j, m_sens in enumerate(m_list):
            tmp_inputs = DCFInputs(
                base_revenue=inputs.base_revenue,
                base_ebit_margin=inputs.base_ebit_margin,
                effective_tax_rate=inputs.effective_tax_rate,
                marginal_tax_rate=inputs.marginal_tax_rate,
                g_year1=inputs.g_year1,
                g_years2_5=g_sens,  # ← 감도
                target_ebit_margin=m_sens,  # ← 감도
                margin_convergence_year=inputs.margin_convergence_year,
                sales_to_capital_yrs1_5=inputs.sales_to_capital_yrs1_5,
                sales_to_capital_yrs6_10=inputs.sales_to_capital_yrs6_10,
                initial_wacc=inputs.initial_wacc,
                terminal_wacc=inputs.terminal_wacc,
                terminal_growth=inputs.terminal_growth,
                terminal_roic=inputs.terminal_roic,
                debt=inputs.debt,
                cash=inputs.cash,
                non_operating_assets=inputs.non_operating_assets,
                options_value=inputs.options_value,
                shares_outstanding=inputs.shares_outstanding,
                base_invested_capital=inputs.base_invested_capital,
                prob_failure=inputs.prob_failure,
                recovery_rate=inputs.recovery_rate,
            )
            _, _, s = run_dcf(tmp_inputs)
            sens_matrix[i, j] = s["value_per_share"]

    # 감도 테이블 DataFrame (행: 성장률, 열: 마진)
    sens_df = pd.DataFrame(
        sens_matrix,
        index=[f"{g*100:.1f}%" for g in g_list],
        columns=[f"{m*100:.1f}%" for m in m_list],
    )

    st.subheader("감도 테이블 (단위: 주당 가치)")
    st.dataframe(sens_df.style.format("{:,.2f}"))

    # --------------------------------------------------------
    # 히트맵 (Altair)
    # --------------------------------------------------------
    import altair as alt

    # 1) Long 형태로 변환
    heat_df = sens_df.copy()
    heat_df["Growth"] = heat_df.index  # 인덱스 → 컬럼으로
    heat_df = heat_df.melt(
        id_vars="Growth", var_name="Margin", value_name="ValuePerShare"
    )

    # 2) 타입을 확실히 숫자로 맞추기
    heat_df["Growth_num"] = heat_df["Growth"].str.rstrip("%").astype(float)
    heat_df["Margin_num"] = heat_df["Margin"].str.rstrip("%").astype(float)
    heat_df["ValuePerShare"] = heat_df["ValuePerShare"].astype(float)

    # 3) 색상 스케일 domain을 명시적으로 지정 (min~max)
    vmin = float(heat_df["ValuePerShare"].min())
    vmax = float(heat_df["ValuePerShare"].max())

    st.subheader("감도 히트맵 (성장률 × 마진 vs 주당 가치)")

    heat_chart = (
        alt.Chart(heat_df)
        .mark_rect()
        .encode(
            x=alt.X("Margin_num:Q", title="목표 EBIT 마진 (%)"),
            y=alt.Y("Growth_num:Q", title="2~5년 매출 성장률 (%)"),
            color=alt.Color(
                "ValuePerShare:Q",
                title="Value per share",
                scale=alt.Scale(
                    domain=[vmin, vmax],
                    scheme="redyellowgreen",  # 원하면 다른 스킴으로 변경 가능
                ),
            ),
            tooltip=[
                alt.Tooltip("Growth", title="성장률(2~5년)"),
                alt.Tooltip("Margin", title="목표 마진"),
                alt.Tooltip("ValuePerShare", title="Value/share", format=".2f"),
            ],
        )
        .properties(width=500, height=400)
    )

    st.altair_chart(heat_chart, width="stretch")

    # 디버깅 정보 (선택적)
    with st.expander("🔍 디버깅 정보", expanded=False):
        st.write("ValuePerShare min/max:", vmin, vmax)
        # st.dataframe()을 사용하여 Arrow 호환성 문제 해결
        st.dataframe(sens_df.head())
        st.dataframe(heat_df.head())
        st.write("**DataFrame 타입 정보:**")
        st.code(str(heat_df.dtypes))


if __name__ == "__main__":
    main()
