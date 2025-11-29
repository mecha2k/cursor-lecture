#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit 완전 가이드
===================

이 파일은 Streamlit을 사용한 웹 애플리케이션 개발에 대한
기초부터 중급 사용법까지 상세히 설명하고 예제를 제공합니다.

Streamlit이란?
- Python으로 데이터 앱을 빠르게 만들 수 있는 오픈소스 프레임워크
- 코드만으로 인터랙티브한 웹 앱 생성
- 데이터 과학자와 개발자를 위한 최적화된 도구
- 자동 리로딩으로 빠른 개발 사이클

주요 특징:
- 간단한 Python 코드로 웹 앱 제작
- 자동 리로딩 (코드 변경 시 자동 새로고침)
- 다양한 위젯과 차트 지원
- 캐싱을 통한 성능 최적화
- 세션 상태 관리

실행 방법:
    streamlit run 09_streamlit_guide.py

또는:
    python -m streamlit run 09_streamlit_guide.py
"""

import streamlit as st
from typing import Any
import pandas as pd
import numpy as np
from datetime import datetime, date, time
import json
import time as time_module
from io import StringIO, BytesIO

# Plotly는 선택적 의존성
try:
    import plotly.express as px  # type: ignore[import-untyped]
    import plotly.graph_objects as go  # type: ignore[import-untyped]

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    px = None  # type: ignore[assignment]
    go = None  # type: ignore[assignment]

# Matplotlib은 선택적 의존성
try:
    import matplotlib.pyplot as plt  # type: ignore[import-untyped]

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None  # type: ignore[assignment]


# ============================================================================
# 페이지 설정
# ============================================================================

st.set_page_config(
    page_title="Streamlit 완전 가이드",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================================
# 1. Streamlit 소개 및 기본 개념
# ============================================================================


def show_introduction():
    """Streamlit 소개 및 기본 개념"""
    st.title("📚 Streamlit 완전 가이드")
    st.markdown("---")

    st.header("1. Streamlit이란?")
    st.write(
        """
        Streamlit은 Python으로 데이터 앱을 빠르게 만들 수 있는 오픈소스 프레임워크입니다.
        복잡한 웹 개발 지식 없이도 Python 코드만으로 인터랙티브한 웹 애플리케이션을 만들 수 있습니다.
        """
    )

    st.subheader("주요 특징")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            - ✅ **간단한 문법**: Python만 알면 됩니다
            - ✅ **자동 리로딩**: 코드 변경 시 자동 새로고침
            - ✅ **풍부한 위젯**: 버튼, 입력, 차트 등 다양한 컴포넌트
            - ✅ **캐싱 지원**: 성능 최적화 내장
            """
        )

    with col2:
        st.markdown(
            """
            - ✅ **세션 상태**: 사용자 상태 관리
            - ✅ **레이아웃**: 컬럼, 탭, 사이드바 등
            - ✅ **데이터 시각화**: 차트, 지도, 테이블
            - ✅ **파일 처리**: 업로드/다운로드 지원
            """
        )

    st.subheader("설치 방법")
    st.code(
        """
# Streamlit 설치
pip install streamlit

# 실행
streamlit run your_app.py

# 또는 특정 포트로 실행
streamlit run your_app.py --server.port 8501
        """,
        language="bash",
    )

    st.subheader("기본 실행 구조")
    st.code(
        """
import streamlit as st

# 제목
st.title("나의 첫 Streamlit 앱")

# 텍스트 표시
st.write("안녕하세요, Streamlit!")

# 입력 위젯
name = st.text_input("이름을 입력하세요")
if name:
    st.write(f"안녕하세요, {name}님!")
        """,
        language="python",
    )

    st.info(
        """
        💡 **핵심 개념**: Streamlit은 스크립트를 위에서 아래로 실행합니다.
        사용자가 위젯과 상호작용하면 스크립트가 처음부터 다시 실행됩니다.
        """
    )


# ============================================================================
# 2. 텍스트 표시 위젯
# ============================================================================


def show_text_widgets():
    """텍스트 표시 위젯 예제"""
    st.title("📝 텍스트 표시 위젯")

    st.header("2.1 제목 계층 구조")
    st.write("제목, 헤더, 서브헤더를 사용하여 계층적 구조를 만들 수 있습니다.")

    st.code(
        """
st.title("제목 (Title)")      # 가장 큰 제목
st.header("헤더 (Header)")     # 큰 제목
st.subheader("서브헤더")       # 중간 제목
        """,
        language="python",
    )

    st.title("이것은 st.title()입니다")
    st.header("이것은 st.header()입니다")
    st.subheader("이것은 st.subheader()입니다")

    st.markdown("---")

    st.header("2.2 텍스트 표시")
    st.write("`st.write()`는 가장 유연한 텍스트 표시 함수입니다.")

    st.code(
        """
st.write("일반 텍스트")
st.write(123)  # 숫자
st.write([1, 2, 3])  # 리스트
st.write({"key": "value"})  # 딕셔너리
        """,
        language="python",
    )

    col1, col2 = st.columns(2)

    with col1:
        st.write("일반 텍스트")
        st.write(123)
        st.write([1, 2, 3])
        st.write({"key": "value"})

    with col2:
        st.text("st.text() - 고정폭 텍스트")
        st.caption("st.caption() - 작은 설명 텍스트")

    st.markdown("---")

    st.header("2.3 Markdown 지원")
    st.write("`st.markdown()`을 사용하여 Markdown 문법을 사용할 수 있습니다.")

    st.code(
        """
st.markdown("# 제목")
st.markdown("**굵은 글씨**")
st.markdown("*기울임*")
st.markdown("- 리스트 항목")
        """,
        language="python",
    )

    st.markdown(
        """
        # Markdown 제목
        **굵은 글씨**와 *기울임*을 사용할 수 있습니다.
        
        - 리스트 항목 1
        - 리스트 항목 2
        - 리스트 항목 3
        
        [링크](https://streamlit.io)
        """
    )

    st.markdown("---")

    st.header("2.4 코드 표시")
    st.write("`st.code()`를 사용하여 코드 블록을 표시할 수 있습니다.")

    st.code(
        """
def hello():
    print("Hello, Streamlit!")
        """,
        language="python",
    )

    st.markdown("---")

    st.header("2.5 수식 표시 (LaTeX)")
    st.write("`st.latex()`를 사용하여 수학 수식을 표시할 수 있습니다.")

    st.code(
        """
st.latex(r"E = mc^2")
st.latex(r"\\sum_{i=1}^{n} x_i")
        """,
        language="python",
    )

    st.latex(r"E = mc^2")
    st.latex(r"\sum_{i=1}^{n} x_i = \frac{n(n+1)}{2}")

    st.markdown("---")

    st.header("2.6 상태 메시지")
    st.write("성공, 에러, 경고, 정보 메시지를 표시할 수 있습니다.")

    st.code(
        """
st.success("성공 메시지")
st.error("에러 메시지")
st.warning("경고 메시지")
st.info("정보 메시지")
        """,
        language="python",
    )

    st.success("✅ 작업이 성공적으로 완료되었습니다!")
    st.error("❌ 오류가 발생했습니다.")
    st.warning("⚠️ 주의가 필요합니다.")
    st.info("ℹ️ 이것은 정보 메시지입니다.")


# ============================================================================
# 3. 입력 위젯
# ============================================================================


def show_input_widgets():
    """입력 위젯 예제"""
    st.title("⌨️ 입력 위젯")

    st.header("3.1 텍스트 입력")
    st.write("사용자로부터 텍스트를 입력받을 수 있습니다.")

    st.code(
        """
name = st.text_input("이름", placeholder="이름을 입력하세요")
password = st.text_input("비밀번호", type="password")
bio = st.text_area("자기소개", height=100)
        """,
        language="python",
    )

    name = st.text_input("이름", placeholder="이름을 입력하세요")
    password = st.text_input("비밀번호", type="password")
    bio = st.text_area("자기소개", height=100, placeholder="자기소개를 작성하세요")

    if name:
        st.write(f"안녕하세요, {name}님!")

    st.markdown("---")

    st.header("3.2 숫자 입력")
    st.write("숫자 입력 위젯을 사용할 수 있습니다.")

    st.code(
        """
age = st.number_input("나이", min_value=0, max_value=120, value=25)
price = st.slider("가격", min_value=0, max_value=1000, value=500, step=10)
        """,
        language="python",
    )

    col1, col2 = st.columns(2)

    with col1:
        age = st.number_input("나이", min_value=0, max_value=120, value=25)
        st.write(f"선택한 나이: {age}세")

    with col2:
        price = st.slider("가격", min_value=0, max_value=1000, value=500, step=10)
        st.write(f"선택한 가격: {price}원")

    st.markdown("---")

    st.header("3.3 선택 위젯")
    st.write("다양한 선택 위젯을 사용할 수 있습니다.")

    st.code(
        """
option = st.selectbox("옵션 선택", ["옵션 1", "옵션 2", "옵션 3"])
options = st.multiselect("다중 선택", ["A", "B", "C", "D"])
choice = st.radio("라디오 버튼", ["선택 1", "선택 2", "선택 3"])
checked = st.checkbox("동의합니다")
        """,
        language="python",
    )

    col1, col2 = st.columns(2)

    with col1:
        option = st.selectbox("옵션 선택", ["옵션 1", "옵션 2", "옵션 3"])
        st.write(f"선택한 옵션: {option}")

        choice = st.radio("라디오 버튼", ["선택 1", "선택 2", "선택 3"])
        st.write(f"선택한 값: {choice}")

    with col2:
        options = st.multiselect("다중 선택", ["A", "B", "C", "D"])
        st.write(f"선택한 항목: {options}")

        checked = st.checkbox("이용약관에 동의합니다")
        if checked:
            st.success("동의 완료!")

    st.markdown("---")

    st.header("3.4 날짜 및 시간 입력")
    st.write("날짜와 시간을 입력받을 수 있습니다.")

    st.code(
        """
birth_date = st.date_input("생년월일")
appointment = st.time_input("약속 시간")
        """,
        language="python",
    )

    col1, col2 = st.columns(2)

    with col1:
        birth_date = st.date_input("생년월일", value=date(2000, 1, 1))
        st.write(f"선택한 날짜: {birth_date}")

    with col2:
        appointment = st.time_input("약속 시간", value=time(12, 0))
        st.write(f"선택한 시간: {appointment}")

    st.markdown("---")

    st.header("3.5 색상 선택")
    st.write("색상을 선택할 수 있습니다.")

    st.code(
        """
color = st.color_picker("색상 선택", "#00f900")
        """,
        language="python",
    )

    color = st.color_picker("색상 선택", "#00f900")
    st.write(f"선택한 색상: {color}")
    st.markdown(
        f'<div style="width: 100px; height: 100px; background-color: {color}; border-radius: 5px;"></div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    st.header("3.6 버튼")
    st.write("버튼을 사용하여 액션을 트리거할 수 있습니다.")

    st.code(
        """
if st.button("클릭하세요"):
    st.write("버튼이 클릭되었습니다!")
        """,
        language="python",
    )

    if st.button("클릭하세요", type="primary"):
        st.balloons()
        st.success("버튼이 클릭되었습니다! 🎉")


# ============================================================================
# 4. 레이아웃 관리
# ============================================================================


def show_layout():
    """레이아웃 관리 예제"""
    st.title("📐 레이아웃 관리")

    st.header("4.1 컬럼 레이아웃")
    st.write("`st.columns()`를 사용하여 여러 컬럼으로 나눌 수 있습니다.")

    st.code(
        """
col1, col2, col3 = st.columns(3)
with col1:
    st.write("첫 번째 컬럼")
with col2:
    st.write("두 번째 컬럼")
with col3:
    st.write("세 번째 컬럼")
        """,
        language="python",
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.header("컬럼 1")
        st.write("이것은 첫 번째 컬럼입니다.")
        st.button("버튼 1", key="btn1")

    with col2:
        st.header("컬럼 2")
        st.write("이것은 두 번째 컬럼입니다.")
        st.button("버튼 2", key="btn2")

    with col3:
        st.header("컬럼 3")
        st.write("이것은 세 번째 컬럼입니다.")
        st.button("버튼 3", key="btn3")

    st.markdown("---")

    st.header("4.2 사이드바")
    st.write("`st.sidebar`를 사용하여 사이드바에 위젯을 배치할 수 있습니다.")

    st.code(
        """
st.sidebar.title("사이드바")
st.sidebar.selectbox("옵션", ["옵션 1", "옵션 2"])
        """,
        language="python",
    )

    st.info("왼쪽 사이드바를 확인해보세요! 메뉴가 표시됩니다.")

    st.markdown("---")

    st.header("4.3 탭")
    st.write("`st.tabs()`를 사용하여 탭 인터페이스를 만들 수 있습니다.")

    st.code(
        """
tab1, tab2, tab3 = st.tabs(["탭 1", "탭 2", "탭 3"])
with tab1:
    st.write("탭 1 내용")
with tab2:
    st.write("탭 2 내용")
with tab3:
    st.write("탭 3 내용")
        """,
        language="python",
    )

    tab1, tab2, tab3 = st.tabs(["📊 데이터", "📈 차트", "⚙️ 설정"])

    with tab1:
        st.subheader("데이터 탭")
        df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        st.dataframe(df)

    with tab2:
        st.subheader("차트 탭")
        chart_data = pd.DataFrame(np.random.randn(20, 3), columns=["A", "B", "C"])
        st.line_chart(chart_data)

    with tab3:
        st.subheader("설정 탭")
        st.checkbox("옵션 1")
        st.checkbox("옵션 2")
        st.slider("값 조정", 0, 100, 50)

    st.markdown("---")

    st.header("4.4 컨테이너")
    st.write("`st.container()`를 사용하여 위젯을 그룹화할 수 있습니다.")

    st.code(
        """
with st.container():
    st.write("컨테이너 내부")
    st.button("버튼")
        """,
        language="python",
    )

    with st.container():
        st.subheader("컨테이너 예제")
        st.write("이 내용은 컨테이너 안에 있습니다.")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("메트릭 1", "100", "10")
        with col2:
            st.metric("메트릭 2", "200", "-5")

    st.markdown("---")

    st.header("4.5 접을 수 있는 섹션")
    st.write("`st.expander()`를 사용하여 접을 수 있는 섹션을 만들 수 있습니다.")

    st.code(
        """
with st.expander("자세히 보기"):
    st.write("접혀있는 내용")
        """,
        language="python",
    )

    with st.expander("📖 자세한 설명 보기"):
        st.write(
            """
            이것은 접을 수 있는 섹션입니다.
            많은 내용을 포함하되 공간을 절약할 수 있습니다.
            
            - 항목 1
            - 항목 2
            - 항목 3
            """
        )

    st.markdown("---")

    st.header("4.6 동적 콘텐츠 업데이트")
    st.write("`st.empty()`를 사용하여 동적으로 콘텐츠를 업데이트할 수 있습니다.")

    st.code(
        """
placeholder = st.empty()
placeholder.write("초기 내용")
placeholder.write("업데이트된 내용")
        """,
        language="python",
    )

    if st.button("콘텐츠 업데이트"):
        placeholder = st.empty()
        with placeholder.container():
            st.success("콘텐츠가 업데이트되었습니다!")
            time_module.sleep(2)
        placeholder.empty()


# ============================================================================
# 5. 데이터 표시
# ============================================================================


def show_data_display():
    """데이터 표시 예제"""
    st.title("📊 데이터 표시")

    st.header("5.1 데이터프레임")
    st.write("`st.dataframe()`을 사용하여 대화형 데이터프레임을 표시할 수 있습니다.")

    st.code(
        """
df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
st.dataframe(df)
        """,
        language="python",
    )

    # 샘플 데이터 생성
    df = pd.DataFrame(
        {
            "이름": ["홍길동", "김철수", "이영희", "박민수"],
            "나이": [25, 30, 28, 35],
            "도시": ["서울", "부산", "대구", "인천"],
            "점수": [85, 92, 78, 95],
        }
    )

    st.dataframe(df, use_container_width=True)

    st.markdown("---")

    st.header("5.2 정적 테이블")
    st.write("`st.table()`을 사용하여 정적 테이블을 표시할 수 있습니다.")

    st.code(
        """
st.table(df)
        """,
        language="python",
    )

    st.table(df.head(3))

    st.markdown("---")

    st.header("5.3 JSON 표시")
    st.write("`st.json()`을 사용하여 JSON 데이터를 표시할 수 있습니다.")

    st.code(
        """
data = {"name": "홍길동", "age": 25}
st.json(data)
        """,
        language="python",
    )

    json_data = {
        "사용자": {
            "이름": "홍길동",
            "나이": 25,
            "취미": ["독서", "영화감상", "여행"],
        },
        "설정": {"테마": "다크", "언어": "한국어"},
    }
    st.json(json_data)

    st.markdown("---")

    st.header("5.4 메트릭 카드")
    st.write("`st.metric()`을 사용하여 메트릭을 표시할 수 있습니다.")

    st.code(
        """
st.metric("매출", "1000만원", "10%")
        """,
        language="python",
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("총 사용자", "1,234", "12%")

    with col2:
        st.metric("활성 사용자", "856", "5%")

    with col3:
        st.metric("매출", "₩1,234,567", "-3%")

    with col4:
        st.metric("전환율", "3.2%", "0.5%")

    st.markdown("---")

    st.header("5.5 데이터 필터링 예제")
    st.write("입력 위젯과 데이터프레임을 결합한 실전 예제입니다.")

    # 필터 옵션
    cities = ["전체"] + list(df["도시"].unique())
    selected_city = st.selectbox("도시 선택", cities)

    # 필터링
    filtered_df = df if selected_city == "전체" else df[df["도시"] == selected_city]

    st.dataframe(filtered_df, use_container_width=True)

    # 통계
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("총 인원", len(filtered_df))
    with col2:
        st.metric("평균 나이", f"{filtered_df['나이'].mean():.1f}세")
    with col3:
        st.metric("평균 점수", f"{filtered_df['점수'].mean():.1f}점")


# ============================================================================
# 6. 데이터 시각화
# ============================================================================


def show_visualization():
    """데이터 시각화 예제"""
    st.title("📈 데이터 시각화")

    st.header("6.1 기본 차트")
    st.write("Streamlit은 기본적으로 간단한 차트를 지원합니다.")

    # 샘플 데이터 생성
    chart_data = pd.DataFrame(
        np.random.randn(20, 3),
        columns=["제품 A", "제품 B", "제품 C"],
    )

    st.subheader("라인 차트")
    st.code(
        """
st.line_chart(chart_data)
        """,
        language="python",
    )
    st.line_chart(chart_data)

    st.subheader("바 차트")
    st.code(
        """
st.bar_chart(chart_data)
        """,
        language="python",
    )
    st.bar_chart(chart_data)

    st.subheader("영역 차트")
    st.code(
        """
st.area_chart(chart_data)
        """,
        language="python",
    )
    st.area_chart(chart_data)

    st.markdown("---")

    st.header("6.2 지도 시각화")
    st.write("`st.map()`을 사용하여 지도에 데이터를 표시할 수 있습니다.")

    st.code(
        """
map_data = pd.DataFrame({
    "lat": [37.5665, 35.1796, 35.8714],
    "lon": [126.9780, 129.0756, 128.6014],
    "name": ["서울", "부산", "대구"]
})
st.map(map_data)
        """,
        language="python",
    )

    map_data = pd.DataFrame(
        {
            "lat": [37.5665, 35.1796, 35.8714, 37.4563, 36.3504],
            "lon": [126.9780, 129.0756, 128.6014, 126.7052, 127.3845],
            "name": ["서울", "부산", "대구", "인천", "광주"],
        }
    )
    st.map(map_data)

    st.markdown("---")

    if PLOTLY_AVAILABLE:
        st.header("6.3 Plotly 통합")
        st.write("Plotly를 사용하여 더 고급 차트를 만들 수 있습니다.")

        st.code(
            """
import plotly.express as px
fig = px.scatter(df, x="나이", y="점수", color="도시")
st.plotly_chart(fig)
            """,
            language="python",
        )

        # 샘플 데이터
        df_viz = pd.DataFrame(
            {
                "나이": np.random.randint(20, 50, 50),
                "점수": np.random.randint(60, 100, 50),
                "도시": np.random.choice(["서울", "부산", "대구"], 50),
            }
        )

        # 산점도
        fig_scatter = px.scatter(
            df_viz, x="나이", y="점수", color="도시", size="점수", hover_data=["도시"]
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

        # 바 차트
        city_scores = df_viz.groupby("도시")["점수"].mean().reset_index()
        fig_bar = px.bar(city_scores, x="도시", y="점수", title="도시별 평균 점수")
        st.plotly_chart(fig_bar, use_container_width=True)

    else:
        st.warning("Plotly가 설치되지 않았습니다. `pip install plotly`로 설치하세요.")

    st.markdown("---")

    if MATPLOTLIB_AVAILABLE:
        st.header("6.4 Matplotlib 통합")
        st.write("Matplotlib 차트도 표시할 수 있습니다.")

        st.code(
            """
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.plot([1, 2, 3, 4], [1, 4, 2, 3])
st.pyplot(fig)
            """,
            language="python",
        )

        fig, ax = plt.subplots(figsize=(10, 6))
        x = np.linspace(0, 10, 100)
        ax.plot(x, np.sin(x), label="sin(x)")
        ax.plot(x, np.cos(x), label="cos(x)")
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_title("삼각함수 그래프")
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)

    else:
        st.warning(
            "Matplotlib이 설치되지 않았습니다. `pip install matplotlib`로 설치하세요."
        )


# ============================================================================
# 7. 파일 처리
# ============================================================================


def show_file_handling():
    """파일 처리 예제"""
    st.title("📁 파일 처리")

    st.header("7.1 파일 업로드")
    st.write("`st.file_uploader()`를 사용하여 파일을 업로드할 수 있습니다.")

    st.code(
        """
uploaded_file = st.file_uploader("파일 선택", type=["csv", "txt"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.dataframe(df)
        """,
        language="python",
    )

    uploaded_file = st.file_uploader(
        "파일을 선택하세요",
        type=["csv", "txt", "json", "png", "jpg"],
    )

    if uploaded_file is not None:
        file_type = uploaded_file.name.split(".")[-1].lower()

        if file_type == "csv":
            df = pd.read_csv(uploaded_file)
            st.success(f"CSV 파일이 업로드되었습니다! ({len(df)}행)")
            st.dataframe(df, use_container_width=True)

        elif file_type == "json":
            json_data = json.load(uploaded_file)
            st.success("JSON 파일이 업로드되었습니다!")
            st.json(json_data)

        elif file_type in ["png", "jpg", "jpeg"]:
            st.success("이미지 파일이 업로드되었습니다!")
            st.image(uploaded_file, caption=uploaded_file.name)

        else:
            content = uploaded_file.read()
            st.text_area("파일 내용", content.decode("utf-8"), height=200)

    st.markdown("---")

    st.header("7.2 파일 다운로드")
    st.write("`st.download_button()`을 사용하여 파일을 다운로드할 수 있습니다.")

    st.code(
        """
csv = df.to_csv(index=False)
st.download_button("CSV 다운로드", csv, "data.csv", "text/csv")
        """,
        language="python",
    )

    # 샘플 데이터 생성
    sample_df = pd.DataFrame(
        {
            "이름": ["홍길동", "김철수", "이영희"],
            "나이": [25, 30, 28],
            "점수": [85, 92, 78],
        }
    )

    st.dataframe(sample_df)

    col1, col2 = st.columns(2)

    with col1:
        # CSV 다운로드
        csv = sample_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "CSV 다운로드",
            csv,
            "sample_data.csv",
            "text/csv",
            key="download-csv",
        )

    with col2:
        # JSON 다운로드
        json_str = sample_df.to_json(orient="records", force_ascii=False, indent=2)
        st.download_button(
            "JSON 다운로드",
            json_str.encode("utf-8"),
            "sample_data.json",
            "application/json",
            key="download-json",
        )

    st.markdown("---")

    st.header("7.3 실전 예제: CSV 분석기")
    st.write("업로드한 CSV 파일을 분석하는 예제입니다.")

    csv_file = st.file_uploader("CSV 파일 업로드", type=["csv"], key="csv_analyzer")

    if csv_file is not None:
        try:
            df = pd.read_csv(csv_file)

            st.subheader("데이터 미리보기")
            st.dataframe(df.head(10), use_container_width=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("행 수", len(df))
            with col2:
                st.metric("열 수", len(df.columns))
            with col3:
                st.metric("결측값", df.isnull().sum().sum())

            st.subheader("데이터 타입")
            st.dataframe(df.dtypes.to_frame("타입"), use_container_width=True)

            st.subheader("기본 통계")
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                st.dataframe(df[numeric_cols].describe(), use_container_width=True)

        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")


# ============================================================================
# 8. 캐싱 및 성능 최적화
# ============================================================================


def show_caching():
    """캐싱 및 성능 최적화 예제"""
    st.title("⚡ 캐싱 및 성능 최적화")

    st.header("8.1 데이터 캐싱")
    st.write("`@st.cache_data`를 사용하여 데이터 로딩 결과를 캐싱할 수 있습니다.")

    st.code(
        """
@st.cache_data
def load_data():
    # 무거운 데이터 로딩 작업
    time.sleep(2)
    return pd.DataFrame({"A": [1, 2, 3]})

df = load_data()  # 첫 실행만 느림, 이후는 캐시 사용
        """,
        language="python",
    )

    @st.cache_data
    def expensive_data_loading():
        """비용이 큰 데이터 로딩 함수"""
        st.write("데이터를 로딩하는 중... (이 메시지는 캐시된 경우 표시되지 않음)")
        time_module.sleep(2)  # 시뮬레이션: 실제로는 DB 쿼리 등
        return pd.DataFrame(
            {
                "ID": range(1000),
                "값": np.random.randn(1000),
            }
        )

    if st.button("데이터 로드 (캐싱 사용)"):
        start_time = time_module.time()
        df = expensive_data_loading()
        elapsed = time_module.time() - start_time
        st.success(f"데이터 로드 완료! (소요 시간: {elapsed:.2f}초)")
        st.dataframe(df.head(10))

    st.info("💡 **팁**: 같은 데이터를 다시 로드하면 캐시에서 가져오므로 매우 빠릅니다!")

    st.markdown("---")

    st.header("8.2 리소스 캐싱")
    st.write(
        "`@st.cache_resource`를 사용하여 모델, 연결 등의 리소스를 캐싱할 수 있습니다."
    )

    st.code(
        """
@st.cache_resource
def load_model():
    # 모델 로딩 (한 번만 실행)
    return YourModel()

model = load_model()
        """,
        language="python",
    )

    @st.cache_resource
    def create_expensive_resource():
        """비용이 큰 리소스 생성 함수"""
        st.write("리소스를 생성하는 중... (이 메시지는 캐시된 경우 표시되지 않음)")
        time_module.sleep(1)
        return {"model": "trained_model", "config": {"epochs": 100}}

    if st.button("리소스 생성 (캐싱 사용)"):
        resource = create_expensive_resource()
        st.json(resource)

    st.markdown("---")

    st.header("8.3 캐시 무효화")
    st.write("캐시를 수동으로 무효화할 수 있습니다.")

    st.code(
        """
# 특정 함수의 캐시 무효화
load_data.clear()

# 모든 캐시 무효화
st.cache_data.clear()
st.cache_resource.clear()
        """,
        language="python",
    )

    if st.button("캐시 무효화"):
        expensive_data_loading.clear()
        create_expensive_resource.clear()
        st.success("캐시가 무효화되었습니다!")

    st.markdown("---")

    st.header("8.4 성능 비교 예제")
    st.write("캐싱 사용 전후의 성능을 비교해보세요.")

    def slow_function(n: int) -> int:
        """느린 함수 (시뮬레이션)"""
        time_module.sleep(0.5)
        return sum(range(n))

    @st.cache_data
    def cached_slow_function(n: int) -> int:
        """캐싱된 느린 함수"""
        time_module.sleep(0.5)
        return sum(range(n))

    n = st.number_input("계산할 숫자", min_value=1, max_value=1000, value=100)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("캐싱 없이 실행"):
            start = time_module.time()
            result = slow_function(int(n))
            elapsed = time_module.time() - start
            st.metric("결과", result)
            st.metric("소요 시간", f"{elapsed:.2f}초")

    with col2:
        if st.button("캐싱 사용"):
            start = time_module.time()
            result = cached_slow_function(int(n))
            elapsed = time_module.time() - start
            st.metric("결과", result)
            st.metric("소요 시간", f"{elapsed:.2f}초")
            if elapsed < 0.1:
                st.success("캐시에서 가져왔습니다! ⚡")


# ============================================================================
# 9. 세션 상태 관리
# ============================================================================


def show_session_state():
    """세션 상태 관리 예제"""
    st.title("💾 세션 상태 관리")

    st.header("9.1 기본 사용법")
    st.write("`st.session_state`를 사용하여 앱 실행 중 상태를 유지할 수 있습니다.")

    st.code(
        """
# 초기화
if "counter" not in st.session_state:
    st.session_state.counter = 0

# 사용
st.session_state.counter += 1
        """,
        language="python",
    )

    # 세션 상태 초기화
    if "counter" not in st.session_state:
        st.session_state.counter = 0

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("증가"):
            st.session_state.counter += 1

    with col2:
        if st.button("감소"):
            st.session_state.counter -= 1

    with col3:
        if st.button("초기화"):
            st.session_state.counter = 0

    st.metric("카운터", st.session_state.counter)

    st.markdown("---")

    st.header("9.2 입력 위젯과 세션 상태")
    st.write("입력 위젯의 값을 세션 상태에 저장할 수 있습니다.")

    st.code(
        """
name = st.text_input("이름", key="name_input")
if st.session_state.name_input:
    st.write(f"안녕하세요, {st.session_state.name_input}님!")
        """,
        language="python",
    )

    name = st.text_input("이름을 입력하세요", key="user_name")
    if st.session_state.user_name:
        st.success(f"안녕하세요, {st.session_state.user_name}님!")

    st.markdown("---")

    st.header("9.3 쇼핑 카트 예제")
    st.write("세션 상태를 사용한 실전 예제입니다.")

    # 쇼핑 카트 초기화
    if "cart" not in st.session_state:
        st.session_state.cart = []

    # 상품 목록
    products = {
        "사과": 1000,
        "바나나": 1500,
        "오렌지": 2000,
        "포도": 3000,
    }

    st.subheader("상품 목록")
    for product, price in products.items():
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.write(f"**{product}**")
        with col2:
            st.write(f"₩{price:,}")
        with col3:
            if st.button(f"추가", key=f"add_{product}"):
                st.session_state.cart.append({"name": product, "price": price})
                st.success(f"{product}이(가) 카트에 추가되었습니다!")

    st.markdown("---")

    st.subheader("장바구니")
    if st.session_state.cart:
        total = 0
        for i, item in enumerate(st.session_state.cart):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(item["name"])
            with col2:
                st.write(f"₩{item['price']:,}")
            with col3:
                if st.button("삭제", key=f"remove_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()
            total += item["price"]

        st.markdown("---")
        st.metric("총액", f"₩{total:,}")

        if st.button("카트 비우기"):
            st.session_state.cart = []
            st.rerun()
    else:
        st.info("장바구니가 비어있습니다.")

    st.markdown("---")

    st.header("9.4 상태 초기화 및 관리")
    st.write("세션 상태를 초기화하고 관리하는 방법입니다.")

    st.code(
        """
# 모든 세션 상태 확인
st.write(st.session_state)

# 특정 키 삭제
del st.session_state['key']

# 모든 상태 초기화
for key in list(st.session_state.keys()):
    del st.session_state[key]
        """,
        language="python",
    )

    with st.expander("현재 세션 상태 보기"):
        st.json(dict(st.session_state))


# ============================================================================
# 10. 실전 예제
# ============================================================================


def show_practical_examples():
    """실전 예제"""
    st.title("🚀 실전 예제")

    st.header("10.1 간단한 계산기")
    st.write("Streamlit으로 만든 간단한 계산기입니다.")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        num1 = st.number_input("첫 번째 숫자", value=0.0, key="calc_num1")

    with col2:
        operation = st.selectbox(
            "연산",
            ["+", "-", "*", "/"],
            key="calc_op",
        )

    with col3:
        num2 = st.number_input("두 번째 숫자", value=0.0, key="calc_num2")

    with col4:
        st.write("")  # 공간 맞추기
        st.write("")  # 공간 맞추기
        if st.button("계산", key="calc_btn"):
            try:
                if operation == "+":
                    result = num1 + num2
                elif operation == "-":
                    result = num1 - num2
                elif operation == "*":
                    result = num1 * num2
                elif operation == "/":
                    if num2 == 0:
                        st.error("0으로 나눌 수 없습니다!")
                        result = None
                    else:
                        result = num1 / num2

                if result is not None:
                    st.session_state.calc_result = result
            except Exception as e:
                st.error(f"계산 오류: {e}")

    if "calc_result" in st.session_state:
        st.success(f"결과: **{st.session_state.calc_result}**")

    st.markdown("---")

    st.header("10.2 데이터 분석 대시보드")
    st.write("샘플 데이터를 분석하는 대시보드입니다.")

    # 샘플 데이터 생성
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    dashboard_data = pd.DataFrame(
        {
            "날짜": dates,
            "매출": np.random.randn(100).cumsum() + 1000,
            "방문자": np.random.randint(50, 200, 100),
            "전환율": np.random.uniform(0.01, 0.05, 100),
        }
    )

    # 필터
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "시작 날짜", value=dashboard_data["날짜"].min().date()
        )
    with col2:
        end_date = st.date_input("종료 날짜", value=dashboard_data["날짜"].max().date())

    # 데이터 필터링
    filtered_data = dashboard_data[
        (dashboard_data["날짜"].dt.date >= start_date)
        & (dashboard_data["날짜"].dt.date <= end_date)
    ]

    # 메트릭
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 매출", f"₩{filtered_data['매출'].sum():,.0f}")
    with col2:
        st.metric("평균 방문자", f"{filtered_data['방문자'].mean():.0f}명")
    with col3:
        st.metric("평균 전환율", f"{filtered_data['전환율'].mean()*100:.2f}%")
    with col4:
        st.metric("기간", f"{len(filtered_data)}일")

    # 차트
    tab1, tab2, tab3 = st.tabs(["매출 추이", "방문자 추이", "전환율 추이"])

    with tab1:
        st.line_chart(filtered_data.set_index("날짜")["매출"])

    with tab2:
        st.bar_chart(filtered_data.set_index("날짜")["방문자"])

    with tab3:
        st.area_chart(filtered_data.set_index("날짜")["전환율"])

    st.markdown("---")

    st.header("10.3 인터랙티브 차트 예제")
    st.write("사용자 입력에 따라 변하는 차트입니다.")

    chart_type = st.selectbox("차트 타입", ["라인", "바", "영역"])

    num_points = st.slider("데이터 포인트 수", 10, 100, 50)
    noise_level = st.slider("노이즈 레벨", 0.0, 2.0, 0.5)

    # 데이터 생성
    x = np.linspace(0, 10, num_points)
    y = np.sin(x) + np.random.normal(0, noise_level, num_points)

    chart_df = pd.DataFrame({"X": x, "Y": y})

    if chart_type == "라인":
        st.line_chart(chart_df.set_index("X"))
    elif chart_type == "바":
        st.bar_chart(chart_df.set_index("X"))
    elif chart_type == "영역":
        st.area_chart(chart_df.set_index("X"))

    if PLOTLY_AVAILABLE:
        st.subheader("Plotly 인터랙티브 차트")
        fig = px.line(chart_df, x="X", y="Y", title="인터랙티브 라인 차트")
        st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# 메인 함수
# ============================================================================


def main():
    """메인 함수 - 메뉴 선택으로 예제 실행"""
    # 사이드바 메뉴
    st.sidebar.title("📚 Streamlit 가이드")
    st.sidebar.markdown("---")

    menu_options = [
        "소개",
        "텍스트 표시__",
        "입력 위젯",
        "레이아웃",
        "데이터 표시",
        "데이터 시각화",
        "파일 처리",
        "캐싱",
        "세션 상태",
        "실전 예제",
    ]

    selected_menu = st.sidebar.selectbox("예제 선택", menu_options)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 실행 방법")
    st.sidebar.code(
        """
streamlit run 
09_streamlit_guide.py
        """,
        language="bash",
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 필요한 패키지")
    st.sidebar.code(
        """
pip install streamlit
pip install pandas numpy
pip install plotly  # 선택적
pip install matplotlib  # 선택적
        """,
        language="bash",
    )

    # 선택된 메뉴에 따라 해당 예제 실행
    if selected_menu == "소개":
        show_introduction()
    elif selected_menu == "텍스트 표시1":
        show_text_widgets()
    elif selected_menu == "입력 위젯":
        show_input_widgets()
    elif selected_menu == "레이아웃":
        show_layout()
    elif selected_menu == "데이터 표시":
        show_data_display()
    elif selected_menu == "데이터 시각화":
        show_visualization()
    elif selected_menu == "파일 처리":
        show_file_handling()
    elif selected_menu == "캐싱":
        show_caching()
    elif selected_menu == "세션 상태":
        show_session_state()
    elif selected_menu == "실전 예제":
        show_practical_examples()


# Streamlit은 파일을 직접 실행하므로 main() 함수를 호출합니다
# 이 파일은 streamlit run 명령으로 실행해야 합니다:
#   streamlit run 09_streamlit_guide.py
main()
