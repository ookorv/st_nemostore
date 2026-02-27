import streamlit as st
import pandas as pd
import sqlite3
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import koreanize_matplotlib

# 페이지 설정
st.set_page_config(
    page_title="네모스토어 매물 분석 대시보드",
    page_icon="🏠",
    layout="wide"
)

# 네모스토어 스타일 커스텀 CSS (Premium Look)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@100;400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Pretendard', sans-serif;
        background-color: #fcfcfc;
    }
    
    .main {
        background-color: #f7f9fb;
    }
    
    /* 카드 스타일 */
    .nemo-card {
        background-color: white;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.03);
        margin-bottom: 24px;
        border: 1px solid #f0f2f5;
    }
    
    /* 포인트 컬러 및 폰트 설정 */
    .nemo-title {
        color: #111;
        font-weight: 700;
        font-size: 1.25rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .nemo-primary-text {
        color: #0084ff;
        font-weight: 700;
    }
    
    /* 메트릭 스타일 커스텀 */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #0084ff;
    }

    /* 탭 스타일 조정 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
        border-bottom: 1px solid #eee;
    }

    .stTabs [data-baseweb="tab"] {
        height: 60px;
        background-color: transparent;
        font-weight: 600;
        font-size: 1.1rem;
        color: #666;
    }

    .stTabs [aria-selected="true"] {
        color: #0084ff !important;
        border-bottom: 3px solid #0084ff !important;
    }
    
    /* 상세 정보 테이블 스타일 */
    .info-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
    }
    .info-table th {
        text-align: left;
        color: #888;
        font-weight: 400;
        padding: 8px 0;
        width: 120px;
        font-size: 0.9rem;
    }
    .info-table td {
        text-align: left;
        color: #333;
        font-weight: 600;
        padding: 8px 0;
        font-size: 0.95rem;
    }
    </style>
    """, unsafe_allow_html=True)

# 프로젝트 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "nemostore.db")

@st.cache_data
def load_and_preprocess_data():
    """데이터 로드 및 심층 분석을 위한 전처리"""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM stores", conn)
    conn.close()
    
    if df.empty: return df

    # 면적 기초 정합성 확인 및 계산
    df['size'] = pd.to_numeric(df['size'], errors='coerce').fillna(0)
    
    # 평당 임대료 (면적 대비 월세) 계산 - 단위: 만원/평
    # 1평 = 3.305785㎡ 기준
    df['size_pyeong'] = (df['size'] / 3.305785).round(2)
    df['rent_per_pyeong'] = df.apply(
        lambda row: (row['monthlyRent'] / row['size_pyeong']) if row['size_pyeong'] > 0 else 0, axis=1
    )
    
    # 층 구분 로직
    def categorize_floor(floor):
        if floor is None: return "미지정"
        try:
            f = int(floor)
            if f < 0: return "지하"
            if f == 1: return "1층"
            if f > 1: return f"{f}층"
            return "기타"
        except: return "미지정"
    
    df['floor_cat'] = df['floor'].apply(categorize_floor)
    
    # 총 소요 비용 (보증금 + 권리금)
    df['total_initial_cost'] = df['deposit'] + df['premium']
    
    return df

def main():
    # 헤더 섹션
    st.markdown('<h1 style="color: #111; font-weight: 800; margin-bottom: 0px;">🏠 NemoStore <span style="color: #0084ff;">Market Analytics</span></h1>', unsafe_allow_html=True)
    st.markdown('<p style="color: #888; font-size: 1.1rem; margin-bottom: 30px;">네모스토어 실시간 상가 시장 데이터 분석 및 의사결정 지원 대시보드</p>', unsafe_allow_html=True)

    df = load_and_preprocess_data()
    
    if df.empty:
        st.error("⚠️ 데이터를 불러올 수 없습니다. 데이터 수집 상태를 확인해주세요.")
        return

    # 사이드바: 브랜드 로고 및 검색 필터
    with st.sidebar:
        st.markdown('<div style="text-align: center; padding: 20px 0;"><img src="https://www.nemoapp.kr/_next/image?url=%2Fimage%2Fcommon%2Flogo_nemo.svg&w=128&q=75" width="100"></div>', unsafe_allow_html=True)
        st.markdown("---")
        st.subheader("🔍 필터링 설정")
        
        # 업종 필터
        categories = sorted(df['businessLargeCodeName'].unique().tolist())
        selected_cats = st.multiselect("업종 카테고리", categories, default=categories)
        
        # 가격 필터 (슬라이더 최적화)
        max_rent = int(df['monthlyRent'].max()) if not df.empty else 1000
        rent_range = st.slider("월세 범위 (만원)", 0, max_rent, (0, max_rent), step=50)
        
        max_dep = int(df['deposit'].max()) if not df.empty else 10000
        dep_range = st.slider("보증금 범위 (만원)", 0, max_dep, (0, max_dep), step=1000)
        
        # 데이터 필터링 적용
        filtered_df = df[
            (df['businessLargeCodeName'].isin(selected_cats)) &
            (df['monthlyRent'].between(rent_range[0], rent_range[1])) &
            (df['deposit'].between(dep_range[0], dep_range[1]))
        ]

    # 메인 컨텐트 - 위젯 탭 방식
    tab1, tab2, tab3 = st.tabs(["📊 시장 대시보드", "📉 단가 심층 분석", "📋 매물 리스트"])

    # ---------------------------------------------------------
    # [탭 1] 시장 대시보드
    # ---------------------------------------------------------
    with tab1:
        # 요약 지표
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("분석 매물", f"{len(filtered_df):,}개")
        m2.metric("평균 보증금", f"{filtered_df['deposit'].mean():.0f}만")
        m3.metric("평균 월세", f"{filtered_df['monthlyRent'].mean():.0f}만")
        m4.metric("평균 평당 월세", f"{filtered_df['rent_per_pyeong'].mean():.1f}만")

        st.markdown("### 🏢 시장 현황 리포트")
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown('<div class="nemo-card"><h3 class="nemo-title">📍 업종별 매물 비중</h3>', unsafe_allow_html=True)
            cat_counts = filtered_df['businessLargeCodeName'].value_counts()
            if not cat_counts.empty:
                fig, ax = plt.subplots(figsize=(8, 8))
                ax.pie(cat_counts, labels=cat_counts.index, autopct='%1.1f%%', startangle=140, 
                       colors=['#0084ff', '#33a0ff', '#66bdff', '#99d9ff', '#ccefff'],
                       wedgeprops={'edgecolor': 'white', 'linewidth': 2})
                st.pyplot(fig)
            else:
                st.info("선택된 업종 데이터가 없습니다.")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with c2:
            st.markdown('<div class="nemo-card"><h3 class="nemo-title">📶 층별 매물 분포</h3>', unsafe_allow_html=True)
            floor_counts = filtered_df['floor_cat'].value_counts().reindex(["지하", "1층", "2층", "3층", "기타"], fill_value=0)
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.bar(floor_counts.index, floor_counts.values, color='#0084ff', alpha=0.8)
            ax.set_ylabel("매물 수")
            # 값 표시
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1, f'{int(height)}', ha='center', va='bottom')
            st.pyplot(fig)
            st.markdown('</div>', unsafe_allow_html=True)

    # ---------------------------------------------------------
    # [탭 2] 단가 심층 분석
    # ---------------------------------------------------------
    with tab2:
        st.markdown("### 💸 임대 효율 및 가격 분석")
        
        col_a, col_b = st.columns([1.5, 1])
        
        with col_a:
            st.markdown('<div class="nemo-card"><h3 class="nemo-title">📉 면적 대비 임대료 상관계수</h3>', unsafe_allow_html=True)
            fig, ax = plt.subplots(figsize=(12, 7))
            for cat in selected_cats:
                sub = filtered_df[filtered_df['businessLargeCodeName'] == cat]
                if not sub.empty:
                    ax.scatter(sub['size_pyeong'], sub['monthlyRent'], label=cat, alpha=0.7, s=100)
            ax.set_xlabel("전용면적 (평)")
            ax.set_ylabel("월 임대료 (만원)")
            ax.legend(frameon=False)
            ax.grid(True, linestyle='--', alpha=0.1)
            st.pyplot(fig)
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col_b:
            st.markdown('<div class="nemo-card"><h3 class="nemo-title">💰 업종별 평당 평균 월세</h3>', unsafe_allow_html=True)
            avg_rent_cat = filtered_df.groupby('businessLargeCodeName')['rent_per_pyeong'].mean().sort_values()
            if not avg_rent_cat.empty:
                fig, ax = plt.subplots(figsize=(8, 10))
                avg_rent_cat.plot(kind='barh', ax=ax, color='#0084ff', alpha=0.9)
                ax.set_xlabel("단위: 만원/평")
                st.pyplot(fig)
            else:
                st.info("데이터가 없습니다.")
            st.markdown('</div>', unsafe_allow_html=True)

    # ---------------------------------------------------------
    # [탭 3] 매물 리스트 & 상세 정보
    # ---------------------------------------------------------
    with tab3:
        st.markdown(f"### 🔍 검색 결과 (**{len(filtered_df)}**개 매물)")
        
        # 데이터프레임 시각화 개선
        display_df = filtered_df.copy().sort_values('monthlyRent')
        st.dataframe(
            display_df[['title', 'businessLargeCodeName', 'deposit', 'monthlyRent', 'premium', 'size_pyeong', 'floor_cat', 'nearSubwayStation']],
            column_config={
                "title": "매물 정보",
                "businessLargeCodeName": "업종",
                "deposit": st.column_config.NumberColumn("보증금(만)", format="%d"),
                "monthlyRent": st.column_config.NumberColumn("월세(만)", format="%d"),
                "premium": st.column_config.NumberColumn("권리금(만)", format="%d"),
                "size_pyeong": "면적(평)",
                "floor_cat": "층",
                "nearSubwayStation": "인근역/위치"
            },
            use_container_width=True,
            hide_index=True
        )

        # 개별 매물 상세 카드 (HTML 매핑 가이드 반영)
        st.markdown("---")
        st.markdown("### 🔍 매물 상세 분석")
        
        if not display_df.empty:
            selected_title = st.selectbox("상세 정보를 확인하려는 매물을 선택하세요", options=display_df['title'].tolist())
            
            if selected_title:
                item = df[df['title'] == selected_title].iloc[0]
                
                detail_col1, detail_col2 = st.columns([1, 1.2])
                
                with detail_col1:
                    st.markdown(f"""
                    <div class="nemo-card">
                        <div class="nemo-title">📌 기본 임대 정보</div>
                        <table class="info-table">
                            <tr><th>월세</th><td><span class="nemo-primary-text">{item['monthlyRent']:,}만원</span> (부가세별도)</td></tr>
                            <tr><th>보증금</th><td>{item['deposit']:,}만원</td></tr>
                            <tr><th>권리금</th><td>{item['premium']:,}만원</td></tr>
                            <tr><th>관리비</th><td>{item['maintenanceFee']:,}만원</td></tr>
                            <tr><th>평당 월세</th><td>{item['rent_per_pyeong']:.1f}만원</td></tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with detail_col2:
                    st.markdown(f"""
                    <div class="nemo-card">
                        <div class="nemo-title">🏢 건축물 및 입지 정보</div>
                        <table class="info-table">
                            <tr><th>업종 구분</th><td>{item['businessLargeCodeName']} ({item['businessMiddleCodeName']})</td></tr>
                            <tr><th>층 정보</th><td>{item['floor_cat']} (지상 1층 기준)</td></tr>
                            <tr><th>면적</th><td>전용 {item['size']}㎡ (약 {item['size_pyeong']}평)</td></tr>
                            <tr><th>인근 역</th><td>{item['nearSubwayStation']}</td></tr>
                            <tr><th>최초 수집일</th><td>{item['createdDateUtc'][:10] if item['createdDateUtc'] else '-'}</td></tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)
                
                # 하단 부가 정보 (가이드 참고)
                with st.expander("✨ 예비 사장님을 위한 매물 특성 (HTML 데이터 매핑 연동)"):
                    st.write(f"본 매물은 **{item['businessLargeCodeName']}** 업종에 최적화된 공간으로, **{item['nearSubwayStation']}** 역세권에 위치하여 안정적인 소비 수요를 보장합니다.")
                    st.info(f"💡 팁: 현재 평당 임대료 {item['rent_per_pyeong']:.1f}만원은 필터링된 평균 대비 {'저렴한' if item['rent_per_pyeong'] < filtered_df['rent_per_pyeong'].mean() else '다소 높은'} 수준입니다.")
        else:
            st.info("검색 결과가 없어 상세 정보를 표시할 수 없습니다.")

if __name__ == "__main__":
    main()
