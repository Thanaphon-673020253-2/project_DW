import os
import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="IndoHotel Executive Analytics",
    page_icon="🏨",
    layout="wide"
)

st.markdown(
    """
    <style>
        /* Main container spacing */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            padding-left: 2.5rem;
            padding-right: 2.5rem;
        }

        /* Adaptive Metric Card for Light & Dark Mode */
        div[data-testid="stMetric"] {
            background-color: rgba(128, 128, 128, 0.05);
            border: 1px solid rgba(128, 128, 128, 0.15);
            padding: 18px 22px;
            border-radius: 14px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
            transition: all 0.3s ease;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            border-color: rgba(59, 130, 246, 0.4);
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.08);
        }

        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background-color: rgba(128, 128, 128, 0.08);
            padding: 8px;
            border-radius: 12px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: 600;
        }

        /* Divider */
        hr {
            margin-top: 2.5rem;
            margin-bottom: 2.5rem;
            border: none;
            height: 1px;
            background: linear-gradient(90deg, rgba(128,128,128,0) 0%, rgba(128,128,128,0.3) 50%, rgba(128,128,128,0) 100%);
        }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================
# HELPER FUNCTIONS
# =========================================================

def clean_chart(fig):
    """
    ปรับรูปแบบกราฟให้โปร่งใส เพื่อให้กลมกลืนไปกับทั้ง Theme ขาวและดำอัตโนมัติ
    """
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)", title=""),
        margin=dict(t=40, b=20, l=20, r=20),
        font=dict(family="Inter, sans-serif", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None)
    )
    return fig


def sql_escape(value):
    return str(value).replace("'", "''")


def safe_number(value, default=0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default

# =========================================================
# DATABASE CONNECTION
# =========================================================

@st.cache_resource
def get_connection():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(base_dir, "indohotel", "dev.duckdb"),
        os.path.join(base_dir, "dev.duckdb")
    ]
    db_path = next((path for path in possible_paths if os.path.exists(path)), None)

    if db_path is None:
        st.error("❌ ไม่พบไฟล์ฐานข้อมูล dev.duckdb\n\nกรุณาตรวจสอบว่าไฟล์อยู่ที่: `indohotel/dev.duckdb`")
        st.stop()

    try:
        conn = duckdb.connect(db_path, read_only=True)
        conn.execute("SET search_path = 'main';")
        return conn
    except Exception as e:
        st.error(f"❌ ไม่สามารถเชื่อมต่อ DuckDB ได้\n\n{e}")
        st.stop()


conn = get_connection()

# =========================================================
# SIDEBAR FILTERS
# =========================================================

with st.sidebar:
    st.markdown("### 🎛️ ตัวกรองข้อมูล")
    st.markdown("---")

    years_df = conn.execute("SELECT DISTINCT year FROM main.dim_date WHERE year BETWEEN 2023 AND 2026 ORDER BY year DESC").df()
    year_options = ["ทั้งหมด"] + ([str(int(y)) for y in years_df["year"]] if not years_df.empty else [])
    selected_year = st.selectbox("📅 เลือกปี", year_options)

    properties_df = conn.execute("SELECT DISTINCT property_name FROM main.dim_property WHERE property_name IS NOT NULL ORDER BY property_name").df()
    property_options = ["ทั้งหมด"] + (properties_df["property_name"].dropna().astype(str).tolist() if not properties_df.empty else [])
    selected_property = st.selectbox("🏨 เลือกสาขา", property_options)

    seasons_df = conn.execute("SELECT DISTINCT season FROM main.dim_date WHERE season IS NOT NULL ORDER BY season").df()
    season_options = ["ทั้งหมด"] + (seasons_df["season"].dropna().astype(str).tolist() if not seasons_df.empty else [])
    selected_season = st.selectbox("🌤️ เลือกฤดูกาล", season_options)