import calendar
import os
import subprocess
from functools import reduce

import duckdb
import numpy as np
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
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            padding-left: 2.5rem;
            padding-right: 2.5rem;
        }
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

MONTH_LOOKUP = {calendar.month_abbr[i].lower(): i for i in range(1, 13)}
MONTH_LABELS = [calendar.month_abbr[i] for i in range(1, 13)]


def month_no(name):
    """แปลงชื่อเดือน (January / Jan) เป็นเลขเดือน 1-12"""
    return MONTH_LOOKUP.get(str(name).strip()[:3].lower(), 0)


def clean_chart(fig):
    """ทำให้กราฟโปร่งใส กลมกลืนกับทั้ง Light / Dark theme"""
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


def question_header(no, text):
    st.markdown(f"#### Q{no}. {text}")


# =========================================================
# DATABASE AUTO-BUILD & CONNECTION (STREAMLIT CLOUD SUPPORT)
# =========================================================

@st.cache_resource
def get_connection():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    path_in_sub = os.path.join(base_dir, "indohotel", "dev.duckdb")
    path_in_root = os.path.join(base_dir, "dev.duckdb")

    db_path = None
    if os.path.exists(path_in_sub):
        db_path = path_in_sub
    elif os.path.exists(path_in_root):
        db_path = path_in_root

    if db_path is None:
        with st.spinner("⏳ กำลังเตรียมฐานข้อมูลคลังข้อมูล (รัน dbt pipeline ครั้งแรก)..."):
            try:
                dbt_cwd = os.path.join(base_dir, "indohotel") if os.path.exists(os.path.join(base_dir, "indohotel", "dbt_project.yml")) else base_dir
                result = subprocess.run(["dbt", "run"], capture_output=True, text=True, cwd=dbt_cwd)
                if result.returncode != 0:
                    st.error(f"❌ เกิดข้อผิดพลาดในการรัน dbt:\n\n{result.stderr}")
                    st.stop()
            except Exception as e:
                st.error(f"❌ ไม่สามารถรันคำสั่ง dbt ได้:\n\n{e}")
                st.stop()

            if os.path.exists(path_in_sub):
                db_path = path_in_sub
            elif os.path.exists(path_in_root):
                db_path = path_in_root
            else:
                os.makedirs(os.path.join(base_dir, "indohotel"), exist_ok=True)
                db_path = path_in_sub

    try:
        conn = duckdb.connect(db_path, read_only=True)
        conn.execute("SET search_path = 'main';")
        return conn
    except Exception as e:
        st.error(f"❌ ไม่สามารถเชื่อมต่อ DuckDB ได้ที่ path: {db_path}\n\n{e}")
        st.stop()


conn = get_connection()


def q(sql):
    return conn.execute(sql).df()


# occupancy_rate อาจเก็บเป็น 0-1 หรือ 0-100 -> ตรวจอัตโนมัติ
_occ_max = safe_number(q("SELECT MAX(occupancy_rate) AS m FROM main.fact_daily_occupancy").loc[0, "m"], 1)
OCC_SCALE = 100 if _occ_max <= 1.5 else 1

# =========================================================
# SIDEBAR FILTERS (เลือกได้หลายปี / หลายสาขา เพื่อเปรียบเทียบ)
# =========================================================

with st.sidebar:
    st.markdown("### 🎛️ ตัวกรองข้อมูล")
    st.markdown("---")

    years_df = q("SELECT DISTINCT year FROM main.dim_date WHERE year BETWEEN 2023 AND 2026 ORDER BY year")
    all_years = [int(y) for y in years_df["year"]]
    selected_years = st.multiselect("📅 ปี (เลือกหลายปีเพื่อเปรียบเทียบ)", all_years, default=all_years)

    props_df = q("SELECT DISTINCT property_name FROM main.dim_property WHERE property_name IS NOT NULL ORDER BY property_name")
    all_props = props_df["property_name"].astype(str).tolist()
    selected_props = st.multiselect("🏨 สาขา", all_props, default=all_props)

    seasons_df = q("SELECT DISTINCT season FROM main.dim_date WHERE season IS NOT NULL ORDER BY season")
    all_seasons = seasons_df["season"].astype(str).tolist()
    selected_seasons = st.multiselect("🌤️ ฤดูกาล", all_seasons, default=all_seasons)

    st.markdown("---")
    exclude_cancel = st.checkbox(
        "ไม่นับการจองที่ถูกยกเลิก (รายได้ / คืนพัก / จำนวนจอง)",
        value=False,
        help="ถ้าเปิด: ตัวเลขรายได้และจำนวนคืนจะไม่รวมการจองที่ is_canceled = true "
             "(Q12 อัตราการยกเลิกจะนับทุกการจองเสมอ)"
    )
    st.caption("💱 สกุลเงินในข้อมูลเป็นรูเปียห์ (Rp)")

# =========================================================
# GLOBAL SQL FILTER
# =========================================================

years_used = selected_years or all_years or [2023, 2024, 2025, 2026]
where_clauses = [f"d.year IN ({', '.join(str(y) for y in years_used)})"]

if selected_props and len(selected_props) < len(all_props):
    plist = ", ".join(f"'{sql_escape(p)}'" for p in selected_props)
    where_clauses.append(f"p.property_name IN ({plist})")

if selected_seasons and len(selected_seasons) < len(all_seasons):
    slist = ", ".join(f"'{sql_escape(s)}'" for s in selected_seasons)
    where_clauses.append(f"d.season IN ({slist})")

where_stmt = "WHERE " + " AND ".join(where_clauses)

# ตัวกรองสำหรับ fact_hotel_bookings (ตัดการจองที่ยกเลิกออกได้)
KEEP_EXPR = "CAST(b.is_canceled AS INTEGER) = 0" if exclude_cancel else "TRUE"
where_book = where_stmt + (f" AND {KEEP_EXPR}" if exclude_cancel else "")

# =========================================================
# MAIN HEADER
# =========================================================

st.title("🏨 INDONESIAN HOTEL GROUP OPERATIONS")
st.caption("ระบบวิเคราะห์ข้อมูลเชิงยุทธศาสตร์ ครอบคลุมการดำเนินงานรอบด้านระดับองค์กร")
st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 รายได้และผลประกอบการ (Q1-Q5)",
    "👥 ลูกค้าและพฤติกรรม (Q6-Q9)",
    "🛏️ ห้องพักและการจอง (Q10-Q12)",
    "📅 กิจกรรมและสถานที่ (Q13-Q15)",
    "🔄 เปรียบเทียบ ปี / สาขา"
])

# =========================================================
# TAB 1: REVENUE & PERFORMANCE (Q1 - Q5)
# =========================================================

with tab1:
    # ---------------- Q1 ----------------
    question_header(1, "โรงแรมทั้งหมดทำรายได้รวมเท่าไร และขายห้องพักได้กี่คืน")

    q1_df = q(
        f"""
        SELECT p.property_name,
               COALESCE(SUM(b.total_revenue), 0) AS revenue,
               COALESCE(SUM(b.nights), 0) AS nights
        FROM main.fact_hotel_bookings b
        JOIN main.dim_date d ON b.date_key = d.date_key
        JOIN main.dim_property p ON b.property_key = p.property_key
        {where_book}
        GROUP BY 1 ORDER BY revenue DESC
        """
    )

    if not q1_df.empty:
        c1, c2 = st.columns(2, gap="medium")
        c1.metric("ยอดขายรวม (Total Revenue)", f"Rp {q1_df['revenue'].sum() / 1e9:,.2f}B")
        c2.metric("จำนวนคืนที่ขายได้ (Nights)", f"{q1_df['nights'].sum():,.0f} คืน")

        q1_df["revenue_b"] = q1_df["revenue"] / 1e9
        tot_q1 = q1_df["revenue"].sum()
        q1_df["share"] = q1_df["revenue"] / tot_q1 * 100 if tot_q1 else 0
        q1_df["label"] = q1_df.apply(
            lambda r: f"Rp {r['revenue_b']:,.2f}B ({r['share']:.1f}%) · {r['nights']:,.0f} คืน", axis=1)
        fig_q1 = px.bar(q1_df.sort_values("revenue_b"), x="revenue_b", y="property_name", orientation="h",
                        text="label", color_discrete_sequence=["#2563eb"])
        fig_q1.update_traces(textposition="outside", cliponaxis=False)
        fig_q1.update_xaxes(range=[0, q1_df["revenue_b"].max() * 1.45])
        st.markdown("**รายได้และจำนวนคืนพักรายสาขา (เรียงจากมากไปน้อย, แสดงสัดส่วนของรายได้รวม)**")
        st.plotly_chart(clean_chart(fig_q1), use_container_width=True)
    else:
        st.info("ไม่พบข้อมูลรายได้")

    st.markdown("---")

    # ---------------- Q2 ----------------
    question_header(2, "รายได้พุ่งสูงในเดือนไหน และตกต่ำในเดือนไหน (Peak & Low Season)")

    q2_df = q(
        f"""
        SELECT d.year AS year, d.month_name AS month_name,
               COALESCE(SUM(b.total_revenue), 0) / 1e9 AS revenue_b
        FROM main.fact_hotel_bookings b
        JOIN main.dim_date d ON b.date_key = d.date_key
        JOIN main.dim_property p ON b.property_key = p.property_key
        {where_book}
        GROUP BY 1, 2
        """
    )

    if not q2_df.empty:
        q2_df["month_no"] = q2_df["month_name"].map(month_no)
        q2_df = q2_df[q2_df["month_no"] > 0].sort_values(["year", "month_no"])
        q2_df["month"] = q2_df["month_no"].map(lambda m: calendar.month_abbr[m])
        q2_df["year"] = q2_df["year"].astype(int).astype(str)

        avg_by_month = q2_df.groupby("month_no")["revenue_b"].mean()
        if not avg_by_month.empty:
            peak_m, low_m = int(avg_by_month.idxmax()), int(avg_by_month.idxmin())
            m1, m2 = st.columns(2, gap="medium")
            m1.metric("🔺 เดือน Peak (รายได้เฉลี่ยสูงสุด)", calendar.month_name[peak_m],
                      f"Rp {avg_by_month[peak_m]:,.2f}B / เดือน")
            m2.metric("🔻 เดือน Low (รายได้เฉลี่ยต่ำสุด)", calendar.month_name[low_m],
                      f"Rp {avg_by_month[low_m]:,.2f}B / เดือน", delta_color="inverse")

        fig_q2 = px.line(q2_df, x="month", y="revenue_b", color="year", markers=True,
                         category_orders={"month": MONTH_LABELS})
        fig_q2.update_traces(line_width=3, marker_size=7)
        fig_q2.update_yaxes(title="รายได้ (Rp พันล้าน)")
        st.plotly_chart(clean_chart(fig_q2), use_container_width=True)

        st.markdown("**🗓️ Heatmap รายได้ ปี × เดือน (สีเข้ม = รายได้สูง)**")
        heat = q2_df.pivot_table(index="year", columns="month_no", values="revenue_b", aggfunc="sum") \
                    .reindex(columns=range(1, 13))
        heat_text = np.where(np.isnan(heat.values), "", np.round(heat.values, 2).astype(str))
        fig_heat = px.imshow(heat.values, x=MONTH_LABELS, y=heat.index.tolist(), aspect="auto",
                             color_continuous_scale="YlOrRd")
        fig_heat.update_traces(text=heat_text, texttemplate="%{text}")
        fig_heat.update_layout(coloraxis_showscale=False)
        st.plotly_chart(clean_chart(fig_heat), use_container_width=True)

        months_per_year = q2_df.groupby("year")["month_no"].nunique()
        partial = [f"{y} ({n} เดือน)" for y, n in months_per_year.items() if n < 12]
        if partial:
            st.caption("⚠️ ปีที่มีข้อมูลไม่ครบ 12 เดือน: " + ", ".join(partial) +
                       " — ควรระวังเมื่อเทียบภาพรวมรายปี")
    else:
        st.info("ไม่พบข้อมูลแนวโน้มรายได้")

    st.markdown("---")

    # ---------------- Q3 ----------------
    question_header(3, "รายได้เฉลี่ยต่อวัน วันธรรมดา (Weekday) เทียบกับวันหยุดสุดสัปดาห์ (Weekend) ในแต่ละปี → เดือน")

    q3_df = q(
        f"""
        SELECT CASE WHEN d.is_weekend THEN 'Weekend' ELSE 'Weekday' END AS day_type,
               d.year AS year,
               d.month_name AS month_name,
               COALESCE(SUM(b.total_revenue), 0) AS revenue,
               COUNT(DISTINCT d.date_key) AS days
        FROM main.fact_hotel_bookings b
        JOIN main.dim_date d ON b.date_key = d.date_key
        JOIN main.dim_property p ON b.property_key = p.property_key
        {where_book}
        GROUP BY 1, 2, 3
        """
    )

    if not q3_df.empty:
        q3_df["month_no"] = q3_df["month_name"].map(month_no)
        q3_df = q3_df[q3_df["month_no"] > 0].copy()
        q3_df["year"] = q3_df["year"].astype(int).astype(str)
        q3_df["month"] = q3_df["month_no"].map(lambda m: calendar.month_abbr[m])
        q3_day_colors = {"Weekday": "#3b82f6", "Weekend": "#f59e0b"}

        # ---- ภาพรวมทุกปีที่เลือก ----
        overall = q3_df.groupby("day_type", as_index=False)[["revenue", "days"]].sum()
        overall["avg_per_day"] = overall["revenue"] / overall["days"].replace(0, np.nan)
        avg_map = overall.set_index("day_type")["avg_per_day"].to_dict()

        m1, m2, m3 = st.columns(3, gap="medium")
        m1.metric("Weekday — รายได้เฉลี่ย/วัน", f"Rp {safe_number(avg_map.get('Weekday')) / 1e6:,.1f}M")
        m2.metric("Weekend — รายได้เฉลี่ย/วัน", f"Rp {safe_number(avg_map.get('Weekend')) / 1e6:,.1f}M")
        wd, we = safe_number(avg_map.get("Weekday")), safe_number(avg_map.get("Weekend"))
        if wd:
            m3.metric("Weekend เทียบ Weekday", f"{(we - wd) / wd * 100:+.1f}%")

        # ---- รายปี ----
        by_year = q3_df.groupby(["year", "day_type"], as_index=False)[["revenue", "days"]].sum()
        by_year["avg_m"] = by_year["revenue"] / by_year["days"].replace(0, np.nan) / 1e6
        st.markdown("**📅 รายได้เฉลี่ยต่อวัน แยกรายปี (Rp ล้าน / วัน)**")
        fig_q3y = px.bar(by_year.sort_values("year"), x="year", y="avg_m", color="day_type", barmode="group",
                         text="avg_m", color_discrete_map=q3_day_colors)
        fig_q3y.update_traces(texttemplate="%{y:,.1f}M", textposition="outside")
        fig_q3y.update_xaxes(type="category")
        st.plotly_chart(clean_chart(fig_q3y), use_container_width=True)

        # ---- รายปี → รายเดือน ----
        by_month = q3_df.copy()
        by_month["avg_m"] = by_month["revenue"] / by_month["days"].replace(0, np.nan) / 1e6
        by_month = by_month.sort_values(["year", "month_no"])
        n_years = by_month["year"].nunique()

        with st.expander("ดูตัวเลขเป็นตาราง (ปี × เดือน)"):
            tbl = by_month.pivot_table(index=["year", "month_no", "month"], columns="day_type",
                                       values="avg_m", aggfunc="sum").reset_index()
            for c in ("Weekday", "Weekend"):
                if c not in tbl.columns:
                    tbl[c] = np.nan
            tbl["Weekend เทียบ Weekday (%)"] = (tbl["Weekend"] - tbl["Weekday"]) / tbl["Weekday"].replace(0, np.nan) * 100
            tbl = tbl.drop(columns="month_no").rename(columns={
                "year": "ปี", "month": "เดือน",
                "Weekday": "Weekday (Rp M/วัน)", "Weekend": "Weekend (Rp M/วัน)"})
            st.dataframe(tbl.style.format({"Weekday (Rp M/วัน)": "{:,.2f}", "Weekend (Rp M/วัน)": "{:,.2f}",
                                           "Weekend เทียบ Weekday (%)": "{:+.1f}%"}, na_rep="-"),
                         hide_index=True, use_container_width=True)

        st.caption("💡 รายได้เฉลี่ยต่อวัน = รายได้รวมของประเภทวัน ÷ จำนวนวันที่มีการจองของประเภทนั้น "
                   "จึงเทียบ Weekday (5 วัน/สัปดาห์) กับ Weekend (2 วัน/สัปดาห์) ได้อย่างยุติธรรม")
    else:
        st.info("ไม่พบข้อมูลรายได้วันธรรมดา/วันหยุด")

    st.markdown("---")

    # ---------------- Q4 ----------------
    question_header(4, "บริการเสริมแต่ละอย่างทำรายได้กี่บาท และมีผู้ใช้บริการกี่คน")

    q4_df = q(
    f"""
    SELECT 'Food & Beverage' AS service_type, CAST(d.year AS VARCHAR) AS year,
           COALESCE(SUM(f.sales_amount), 0) AS revenue,
           COUNT(DISTINCT f.guest_key) AS guest_count
    FROM main.fact_fnb_operations f JOIN main.dim_date d ON f.date_key = d.date_key JOIN main.dim_property p ON f.property_key = p.property_key {where_stmt}
    GROUP BY 1, 2
    UNION ALL
    SELECT 'Spa & Wellness', CAST(d.year AS VARCHAR),
           COALESCE(SUM(a.spa_revenue), 0),
           COUNT(DISTINCT CASE WHEN a.spa_revenue > 0 THEN a.guest_key END)
    FROM main.fact_ancillary_services a JOIN main.dim_date d ON a.date_key = d.date_key JOIN main.dim_property p ON a.property_key = p.property_key {where_stmt}
    GROUP BY 1, 2
    UNION ALL
    SELECT 'Event & Venue', CAST(d.year AS VARCHAR),
           COALESCE(SUM(a.event_revenue), 0),
           COUNT(CASE WHEN a.event_revenue > 0 THEN 1 END)
    FROM main.fact_ancillary_services a JOIN main.dim_date d ON a.date_key = d.date_key JOIN main.dim_property p ON a.property_key = p.property_key {where_stmt}
    GROUP BY 1, 2
    """
    )

    if not q4_df.empty:
        totals = q4_df.groupby("service_type", as_index=False)[["revenue", "guest_count"]].sum() \
                    .sort_values("revenue", ascending=False).reset_index(drop=True)
        mcols = st.columns(3, gap="medium")
        for idx, row in totals.iterrows():
            if idx >= 3:
                break
            unit = "งานอีเวนต์" if row["service_type"] == "Event & Venue" else "ผู้ใช้บริการ (ไม่ซ้ำคน)"
            mcols[idx].metric(f"{row['service_type']} (รวมทุกปีที่เลือก)", f"Rp {safe_number(row['revenue']) / 1e9:,.2f}B",
                            f"{int(safe_number(row['guest_count'])):,} {unit}")

        q4_df["revenue_b"] = pd.to_numeric(q4_df["revenue"], errors="coerce").fillna(0) / 1e9
        fig_q4 = px.bar(q4_df.sort_values("year"), x="service_type", y="revenue_b", color="year", barmode="group",
                        text="revenue_b", color_discrete_sequence=px.colors.sequential.Blues[3:])
        fig_q4.update_traces(texttemplate="Rp %{y:.2f}B", textposition="outside")
        fig_q4.update_layout(title="รายได้บริการเสริม แยกรายปี")
        st.plotly_chart(clean_chart(fig_q4), use_container_width=True)
        st.caption("Event & Venue ไม่มีข้อมูลรายคน จึงนับเป็น 'จำนวนงานที่จัด'")
    else:
        st.info("ไม่พบข้อมูลบริการเสริม")

    st.markdown("---")

    # ---------------- Q5 ----------------
    question_header(5, "ห้องพักของแต่ละสาขาถูกจองกี่ % เมื่อเทียบกับจำนวนห้องทั้งหมด (Occupancy)")

    q5_df = q(
        f"""
        SELECT CAST(d.year AS VARCHAR) AS year, p.property_name, AVG(f.occupancy_rate) AS avg_occ
        FROM main.fact_daily_occupancy f
        JOIN main.dim_property p ON f.property_key = p.property_key
        JOIN main.dim_date d ON f.date_key = d.date_key
        {where_stmt}
        GROUP BY 1, 2 ORDER BY 1, 2
        """
    )

    if not q5_df.empty:
        q5_df["avg_occ"] = pd.to_numeric(q5_df["avg_occ"], errors="coerce").fillna(0) * OCC_SCALE
        fig_q5 = px.bar(q5_df, x="property_name", y="avg_occ", color="year", barmode="group",
                        text="avg_occ", range_y=[0, 110], color_discrete_sequence=px.colors.sequential.Blues[3:])
        fig_q5.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        st.plotly_chart(clean_chart(fig_q5), use_container_width=True)
    else:
        st.info("ไม่พบข้อมูล Occupancy Rate")    
# =========================================================
# TAB 2: CUSTOMER ANALYSIS (Q6 - Q9)
# =========================================================

with tab2:
    # ---------------- Q6 ----------------
    question_header(6, "สมาชิกแต่ละระดับกลับมาพักซ้ำกี่ครั้ง")

    q6_df = q(
        f"""
        WITH gb AS (
            SELECT CASE WHEN g.loyalty_tier IS NULL OR LOWER(TRIM(g.loyalty_tier)) = 'none'
                        THEN 'Non-Member' ELSE g.loyalty_tier END AS loyalty_tier,
                   d.year AS stay_year,
                   b.guest_key,
                   COUNT(b.booking_id) AS n
            FROM main.fact_hotel_bookings b
            LEFT JOIN main.dim_guest g ON b.guest_key = g.guest_key
            JOIN main.dim_property p ON b.property_key = p.property_key
            JOIN main.dim_date d ON b.date_key = d.date_key
            {where_book} AND b.guest_key IS NOT NULL
            GROUP BY 1, 2, 3
        )
        SELECT loyalty_tier,
               stay_year,
               COUNT(*) AS guests,
               SUM(n) AS bookings,
               SUM(CASE WHEN n > 1 THEN n - 1 ELSE 0 END) AS repeat_stays,
               SUM(CASE WHEN n > 1 THEN 1 ELSE 0 END) AS repeat_guests,
               SUM(CASE WHEN n > 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS repeat_guest_pct,
               AVG(n) AS avg_stays
        FROM gb GROUP BY 1, 2 ORDER BY stay_year, repeat_stays DESC
        """
    )

    if not q6_df.empty:
        q6_df["stay_year"] = q6_df["stay_year"].astype(int).astype(str)

        col_c, col_d = st.columns([1, 1], gap="large")
        with col_c:
            fig_q6 = px.bar(
                q6_df, x="loyalty_tier", y="repeat_stays", color="stay_year",
                barmode="group", text="repeat_stays",
                color_discrete_sequence=px.colors.sequential.Purples_r
            )
            fig_q6.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
            fig_q6.update_layout(
                title="จำนวนการมาพักซ้ำ (ครั้ง) แยกตามระดับสมาชิก และปี",
                xaxis_title="ระดับสมาชิก",
                yaxis_title="จำนวนการพักซ้ำ (ครั้ง)",
                legend_title="ปี"
            )
            st.plotly_chart(clean_chart(fig_q6), use_container_width=True)

        with col_d:
            pivot = q6_df.pivot_table(
                index="loyalty_tier", columns="stay_year",
                values="repeat_stays", aggfunc="sum", fill_value=0
            )
            pivot.columns = [f"พักซ้ำปี {c} (ครั้ง)" for c in pivot.columns]
            pivot = pivot.reset_index().rename(columns={"loyalty_tier": "ระดับสมาชิก"})

            fmt = {c: "{:,.0f}" for c in pivot.columns if c != "ระดับสมาชิก"}
            st.dataframe(
                pivot.style.format(fmt),
                use_container_width=True, hide_index=True
            )
        st.caption("จำนวนการพักซ้ำ = จำนวนการจองส่วนที่เกินครั้งแรกของลูกค้าแต่ละคน ในแต่ละปี (นับภายในช่วงที่กรอง)")
    else:
        st.info("ไม่พบข้อมูล Loyalty Tier")

        st.markdown("---")
    # ---------------- Q7 ----------------
    question_header(7, "ลูกค้า 5 สัญชาติแรกที่พักมากที่สุด มียอดจองกี่รายการ")

    nat_filter = "AND g.nationality IS NOT NULL AND TRIM(g.nationality) <> '' AND LOWER(TRIM(g.nationality)) <> 'others'"
    q7_df = q(
        f"""
        SELECT g.nationality, COUNT(b.booking_id) AS bookings
        FROM main.fact_hotel_bookings b
        JOIN main.dim_guest g ON b.guest_key = g.guest_key
        JOIN main.dim_property p ON b.property_key = p.property_key
        JOIN main.dim_date d ON b.date_key = d.date_key
        {where_book} {nat_filter}
        GROUP BY g.nationality ORDER BY bookings DESC LIMIT 5
        """
    )

    if not q7_df.empty:
        col_a, col_b = st.columns(2, gap="large")
        with col_a:
            fig_q7 = px.bar(q7_df, x="bookings", y="nationality", orientation="h", text="bookings",
                            color="bookings", color_continuous_scale="Tealgrn")
            fig_q7.update_traces(texttemplate="%{text:,.0f} รายการ", textposition="outside")
            fig_q7.update_layout(yaxis=dict(autorange="reversed"), coloraxis_showscale=False,
                                 title="Top 5 สัญชาติ (รวมทุกปีที่เลือก)")
            st.plotly_chart(clean_chart(fig_q7), use_container_width=True)

        with col_b:
            nat_list = ", ".join(f"'{sql_escape(n)}'" for n in q7_df["nationality"])
            q7y_df = q(
                f"""
                SELECT CAST(d.year AS VARCHAR) AS year, g.nationality, COUNT(b.booking_id) AS bookings
                FROM main.fact_hotel_bookings b
                JOIN main.dim_guest g ON b.guest_key = g.guest_key
                JOIN main.dim_property p ON b.property_key = p.property_key
                JOIN main.dim_date d ON b.date_key = d.date_key
                {where_book} AND g.nationality IN ({nat_list})
                GROUP BY 1, 2 ORDER BY 1
                """
            )
            fig_q7y = px.bar(q7y_df, x="nationality", y="bookings", color="year", barmode="group",
                             category_orders={"nationality": q7_df["nationality"].tolist()},
                             color_discrete_sequence=px.colors.sequential.Tealgrn[2:])
            fig_q7y.update_layout(title="เปรียบเทียบรายปี")
            st.plotly_chart(clean_chart(fig_q7y), use_container_width=True)
        st.caption("ไม่รวมสัญชาติที่ระบุเป็น 'Others'")
    else:
        st.info("ไม่พบข้อมูลสัญชาติลูกค้า")

    st.markdown("---")

    # ---------------- Q8 ----------------
    question_header(8, "ลูกค้าในประเทศและต่างชาติ ใช้บริการอาหารและสปากี่ครั้ง")

    guest_case = ("CASE WHEN g.is_domestic IS NULL THEN 'ไม่ระบุ' "
                  "WHEN g.is_domestic = TRUE THEN 'ในประเทศ (Domestic)' ELSE 'ต่างชาติ (International)' END")
    q8_df = q(
        f"""
        WITH raw_data AS (
            SELECT 'Food' AS service_type, {guest_case} AS guest_type, COUNT(*) AS service_count
            FROM main.fact_fnb_operations f
            JOIN main.dim_guest g ON f.guest_key = g.guest_key
            JOIN main.dim_date d ON f.date_key = d.date_key
            JOIN main.dim_property p ON f.property_key = p.property_key
            {where_stmt} AND f.sales_amount > 0 GROUP BY 1, 2
            UNION ALL
            SELECT 'Spa', {guest_case}, COUNT(*)
            FROM main.fact_ancillary_services a
            JOIN main.dim_guest g ON a.guest_key = g.guest_key
            JOIN main.dim_date d ON a.date_key = d.date_key
            JOIN main.dim_property p ON a.property_key = p.property_key
            {where_stmt} AND a.spa_revenue > 0 GROUP BY 1, 2
        )
        SELECT service_type, guest_type, service_count,
               service_count * 100.0 / SUM(service_count) OVER (PARTITION BY service_type) AS percentage
        FROM raw_data
        """
    )

    if not q8_df.empty:
        fig_q8 = px.bar(q8_df, x="service_type", y="service_count", color="guest_type", barmode="group",
                        text="service_count", color_discrete_sequence=["#38bdf8", "#fb7185", "#a3a3a3"],
                        custom_data=["percentage"])
        fig_q8.update_traces(texttemplate="%{text:,.0f} (%{customdata[0]:.1f}%)", textposition="outside")
        st.plotly_chart(clean_chart(fig_q8), use_container_width=True)
    else:
        st.info("ไม่พบข้อมูลการใช้บริการ Spa และ Food")

    st.markdown("---")

    # ---------------- Q9 ----------------
    question_header(9, "ในแต่ละสาขา ลูกค้าเข้าพักเฉลี่ยกี่คืนต่อการจอง 1 ครั้ง")

    q9_df = q(
        f"""
        SELECT CAST(d.year AS VARCHAR) AS year, p.property_name, AVG(b.nights) AS avg_nights
        FROM main.fact_hotel_bookings b
        JOIN main.dim_property p ON b.property_key = p.property_key
        JOIN main.dim_date d ON b.date_key = d.date_key
        {where_book}
        GROUP BY 1, 2 ORDER BY 1, 2
        """
    )

    if not q9_df.empty:
        fig_q9 = px.bar(q9_df, x="property_name", y="avg_nights", color="year", barmode="group",
                        text="avg_nights", color_discrete_sequence=px.colors.sequential.Oranges[3:])
        fig_q9.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig_q9.update_yaxes(title="คืน / การจอง")
        st.plotly_chart(clean_chart(fig_q9), use_container_width=True)
    else:
        st.info("ไม่พบข้อมูลระยะเวลาเข้าพักเฉลี่ย")

# =========================================================
# TAB 3: ROOM & BOOKING PATTERNS (Q10 - Q12)
# =========================================================

with tab3:
    # ---------------- Q10 ----------------
    question_header(10, "ลูกค้าจองห้องพักล่วงหน้าเฉลี่ยกี่วัน")

    q10_df = q(
        f"""
        SELECT CAST(d.year AS VARCHAR) AS year, p.property_name,
               SUM(b.lead_time_days) AS lead_sum, COUNT(b.lead_time_days) AS lead_cnt
        FROM main.fact_hotel_bookings b
        JOIN main.dim_property p ON b.property_key = p.property_key
        JOIN main.dim_date d ON b.date_key = d.date_key
        {where_book}
        GROUP BY 1, 2 ORDER BY 1, 2
        """
    )

    if not q10_df.empty:
        overall_lead = q10_df["lead_sum"].sum() / max(q10_df["lead_cnt"].sum(), 1)
        st.metric("ระยะเวลาจองล่วงหน้าเฉลี่ย (Lead Time)", f"{overall_lead:,.1f} วัน")

        q10_df["avg_lead"] = q10_df["lead_sum"] / q10_df["lead_cnt"].replace(0, np.nan)
        fig_q10 = px.bar(q10_df, x="property_name", y="avg_lead", color="year", barmode="group",
                         text="avg_lead", color_discrete_sequence=px.colors.sequential.Purp[2:])
        fig_q10.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig_q10.update_yaxes(title="วัน")
        st.plotly_chart(clean_chart(fig_q10), use_container_width=True)
    else:
        st.info("ไม่พบข้อมูล Lead Time")

    st.markdown("---")

    # ---------------- Q11 ----------------
    question_header(11, "ห้องพักแต่ละแบบทำรายได้กี่บาท")

    q11_df = q(
    f"""
    SELECT COALESCE(r.room_type, b.room_type, 'Unknown') AS room_type,
           CAST(d.year AS VARCHAR) AS year,
           COUNT(b.booking_id) AS bookings,
           COALESCE(SUM(b.total_revenue), 0) / 1e9 AS revenue_b
    FROM main.fact_hotel_bookings b
    LEFT JOIN main.dim_room r ON b.room_key = r.room_key
    JOIN main.dim_property p ON b.property_key = p.property_key
    JOIN main.dim_date d ON b.date_key = d.date_key
    {where_book}
    GROUP BY 1, 2 ORDER BY 2, revenue_b DESC
    """
    )

    if not q11_df.empty and q11_df["revenue_b"].notna().any():
        fig_q11 = px.bar(q11_df.sort_values("year"), x="room_type", y="revenue_b", color="year", barmode="group",
                        text="bookings", color_discrete_sequence=px.colors.sequential.Greens[3:])
        fig_q11.update_traces(texttemplate="%{text:,} จอง", textposition="outside")
        fig_q11.update_yaxes(title="รายได้ (Rp พันล้าน)")
        st.plotly_chart(clean_chart(fig_q11), use_container_width=True)
    else:
        st.warning("⚠️ ไม่พบข้อมูลประเภทห้องพักตามเงื่อนไขที่เลือก")

    st.markdown("---")

    # ---------------- Q12 ----------------
    question_header(12, "ห้องพักแต่ละแบบถูกยกเลิกกี่ % เมื่อเทียบกับยอดจองทั้งหมด")

    # ใช้ where_stmt (นับทุกการจอง) เพราะต้องมีตัวหารเป็นยอดจองทั้งหมด
    q12_df = q(
    f"""
    SELECT COALESCE(r.room_type, b.room_type, 'Unknown') AS room_type,
           CAST(d.year AS VARCHAR) AS year,
           COUNT(*) AS total_bookings,
           SUM(CAST(b.is_canceled AS INTEGER)) AS canceled,
           AVG(CAST(b.is_canceled AS INTEGER)) * 100 AS cancel_rate
    FROM main.fact_hotel_bookings b
    LEFT JOIN main.dim_room r ON b.room_key = r.room_key
    JOIN main.dim_property p ON b.property_key = p.property_key
    JOIN main.dim_date d ON b.date_key = d.date_key
    {where_stmt}
    GROUP BY 1, 2 ORDER BY 2, cancel_rate DESC
    """
    )

    if not q12_df.empty and q12_df["cancel_rate"].notna().any():
        fig_q12 = px.bar(q12_df.sort_values("year"), x="room_type", y="cancel_rate", color="year", barmode="group",
                        text="cancel_rate", color_discrete_sequence=px.colors.sequential.Reds[3:],
                        custom_data=["canceled", "total_bookings"])
        fig_q12.update_traces(
            texttemplate="%{text:.1f}%", textposition="outside",
            hovertemplate="%{x}<br>ยกเลิก %{customdata[0]:,} / %{customdata[1]:,} การจอง<extra></extra>"
        )
        st.plotly_chart(clean_chart(fig_q12), use_container_width=True)
    else:
        st.warning("⚠️ ไม่พบข้อมูลอัตราการยกเลิกตามเงื่อนไขที่เลือก")

# =========================================================
# TAB 4: EVENTS & VENUE (Q13 - Q15)
# =========================================================

with tab4:
    # ---------------- Q13 ----------------
    question_header(13, "สถานที่ที่ใช้จัดกิจกรรมแต่ละแบบถูกใช้งานกี่ครั้ง")

    q13_df = q(
        f"""
        SELECT COALESCE(v.venue_type, 'Unknown') AS venue_type,
               COALESCE(e.event_type_name, 'Unknown') AS event_type,
               COUNT(*) AS usage_count
        FROM main.fact_ancillary_services a
        LEFT JOIN main.dim_venue v ON a.venue_key = v.venue_key
        LEFT JOIN main.dim_event_type e ON a.event_type_key = e.event_type_key
        JOIN main.dim_property p ON a.property_key = p.property_key
        JOIN main.dim_date d ON a.date_key = d.date_key
        {where_stmt} AND a.event_revenue > 0
        GROUP BY 1, 2
        """
    )

    if not q13_df.empty:
        order = q13_df.groupby("venue_type")["usage_count"].sum().sort_values(ascending=False)
        totals = order.reset_index().rename(columns={"usage_count": "total"})
        fig_q13 = px.bar(q13_df, x="venue_type", y="usage_count", color="event_type", barmode="stack",
                         category_orders={"venue_type": order.index.tolist()},
                         color_discrete_sequence=px.colors.qualitative.Set2)
        for _, r in totals.iterrows():
            fig_q13.add_annotation(x=r["venue_type"], y=r["total"], text=f"{int(r['total']):,} ครั้ง",
                                   showarrow=False, yshift=12)
        st.plotly_chart(clean_chart(fig_q13), use_container_width=True)
        st.caption("แท่งซ้อนแสดงว่าแต่ละสถานที่ถูกใช้จัดกิจกรรมประเภทใดบ้าง (นับเฉพาะรายการที่มีรายได้จากอีเวนต์)")
    else:
        st.info("ไม่พบข้อมูลการใช้สถานที่")

    st.markdown("---")

    # ---------------- Q14 + Q15 ----------------
    q_event = q(
    f"""
    SELECT COALESCE(e.event_type_name, 'Unknown') AS event_type,
           CAST(d.year AS VARCHAR) AS year,
           COUNT(*) AS total_bookings,
           COALESCE(SUM(a.event_revenue), 0) / 1e9 AS rev_billions
    FROM main.fact_ancillary_services a
    LEFT JOIN main.dim_event_type e ON a.event_type_key = e.event_type_key
    JOIN main.dim_date d ON a.date_key = d.date_key
    JOIN main.dim_property p ON a.property_key = p.property_key
    {where_stmt} AND a.event_revenue > 0
    GROUP BY 1, 2
    """
    )

    if not q_event.empty:
        col_m, col_n = st.columns(2, gap="large")
        order14 = q_event.groupby("event_type")["total_bookings"].sum().sort_values(ascending=False).index.tolist()
        order15 = q_event.groupby("event_type")["rev_billions"].sum().sort_values(ascending=False).index.tolist()

        with col_m:
            question_header(14, "กิจกรรมแต่ละประเภทถูกจัดทั้งหมดกี่ครั้ง")
            fig14 = px.bar(q_event.sort_values("year"), x="event_type", y="total_bookings", color="year",
                        barmode="group", text="total_bookings", category_orders={"event_type": order14},
                        color_discrete_sequence=px.colors.sequential.Blues[3:])
            fig14.update_traces(texttemplate="%{text:,}", textposition="outside")
            st.plotly_chart(clean_chart(fig14), use_container_width=True)

        with col_n:
            question_header(15, "กิจกรรมประเภทใดทำรายได้มากที่สุด")
            totals15 = q_event.groupby("event_type", as_index=False)["rev_billions"].sum() \
                            .sort_values("rev_billions", ascending=False)
            top = totals15.iloc[0]
            st.metric("🏆 รายได้สูงสุด (รวมทุกปีที่เลือก)", str(top["event_type"]), f"Rp {top['rev_billions']:,.2f}B")
            fig15 = px.bar(q_event.sort_values("year"), x="event_type", y="rev_billions", color="year",
                        barmode="group", text="rev_billions", category_orders={"event_type": order15},
                        color_discrete_sequence=px.colors.sequential.YlGnBu[3:])
            fig15.update_traces(texttemplate="%{y:.2f}B", textposition="outside")
            st.plotly_chart(clean_chart(fig15), use_container_width=True)
    else:
        st.info("ไม่พบข้อมูลประเภทกิจกรรมจัดงานตามเงื่อนไข")

# =========================================================
# TAB 5: COMPARISON (เลือกเทียบ ปี-ปี หรือ สาขา-สาขา)
# =========================================================

SUM_COLS = ["revenue", "nights", "bookings", "lead_sum", "lead_cnt", "all_bookings",
            "canceled", "occ_sum", "occ_cnt", "fnb_rev", "spa_rev", "event_rev"]

# label -> (คอลัมน์, ชนิดการแสดงผล, ทิศทางที่ "ดี": up / down / neutral)
METRICS = {
    "รายได้ห้องพักรวม": ("revenue", "money", "up"),
    "จำนวนคืนที่ขายได้": ("nights", "int", "up"),
    "จำนวนการจอง": ("bookings", "int", "up"),
    "รายได้เฉลี่ยต่อคืน (ADR)": ("adr", "rp", "up"),
    "อัตราการเข้าพัก (Occupancy %)": ("occupancy", "pct", "up"),
    "อัตราการยกเลิก (%)": ("cancel_rate", "pct", "down"),
    "จำนวนคืนเฉลี่ยต่อการจอง": ("avg_nights", "dec", "neutral"),
    "Lead Time เฉลี่ย (วัน)": ("avg_lead", "dec", "neutral"),
    "รายได้บริการเสริมรวม (F&B + Spa + Event)": ("ancillary", "money", "up"),
    "รายได้ Food & Beverage": ("fnb_rev", "money", "up"),
    "รายได้ Spa": ("spa_rev", "money", "up"),
    "รายได้ Event": ("event_rev", "money", "up"),
}
KPI_KEYS = ["รายได้ห้องพักรวม", "จำนวนคืนที่ขายได้", "รายได้เฉลี่ยต่อคืน (ADR)",
            "อัตราการเข้าพัก (Occupancy %)", "อัตราการยกเลิก (%)",
            "รายได้บริการเสริมรวม (F&B + Spa + Event)"]

COLOR_A, COLOR_B = "#94a3b8", "#2563eb"
STATUS_COLORS = {"ดีขึ้น": "#16a34a", "แย่ลง": "#dc2626", "เท่าเดิม": "#9ca3af",
                 "เพิ่มขึ้น": "#2563eb", "ลดลง": "#f97316"}


def fmt(v, kind):
    if pd.isna(v):
        return "-"
    if kind == "money":
        return f"Rp {v / 1e9:,.2f}B"
    if kind == "rp":
        return f"Rp {v:,.0f}"
    if kind == "int":
        return f"{v:,.0f}"
    if kind == "pct":
        return f"{v:.1f}%"
    return f"{v:,.2f}"


def change(v_a, v_b, kind):
    """% เปลี่ยนแปลง (สำหรับอัตราส่วน % ใช้ส่วนต่างเป็นจุด pp)"""
    if pd.isna(v_a) or pd.isna(v_b):
        return np.nan
    if kind == "pct":
        return v_b - v_a
    return (v_b - v_a) / v_a * 100 if v_a else np.nan


def fmt_change(c, kind):
    if pd.isna(c):
        return "-"
    return f"{c:+.1f} pp" if kind == "pct" else f"{c:+.1f}%"


def status(chg, direction):
    if pd.isna(chg) or chg == 0:
        return "เท่าเดิม"
    if direction == "neutral":
        return "เพิ่มขึ้น" if chg > 0 else "ลดลง"
    return "ดีขึ้น" if (chg > 0) == (direction == "up") else "แย่ลง"


def aggregate(frame, by):
    g = frame.groupby(by, as_index=False)[SUM_COLS].sum()
    g["adr"] = g["revenue"] / g["nights"].replace(0, np.nan)
    g["avg_nights"] = g["nights"] / g["bookings"].replace(0, np.nan)
    g["avg_lead"] = g["lead_sum"] / g["lead_cnt"].replace(0, np.nan)
    g["cancel_rate"] = g["canceled"] / g["all_bookings"].replace(0, np.nan) * 100
    g["occupancy"] = g["occ_sum"] / g["occ_cnt"].replace(0, np.nan) * OCC_SCALE
    g["ancillary"] = g["fnb_rev"] + g["spa_rev"] + g["event_rev"]
    return g


@st.cache_data(show_spinner=False)
def load_monthly(cmp_where, keep_expr):
    """ข้อมูลระดับ ปี-เดือน-สาขา ของทุกตัวชี้วัด (ใช้ทุกปี/ทุกสาขา แล้วค่อยกรองใน pandas)"""
    key_cols = ["year", "month_name", "property"]

    hotel_m = q(
        f"""
        SELECT d.year AS year, d.month_name AS month_name, p.property_name AS property,
               COALESCE(SUM(b.total_revenue) FILTER (WHERE {keep_expr}), 0) AS revenue,
               COALESCE(SUM(b.nights) FILTER (WHERE {keep_expr}), 0) AS nights,
               COUNT(b.booking_id) FILTER (WHERE {keep_expr}) AS bookings,
               COALESCE(SUM(b.lead_time_days) FILTER (WHERE {keep_expr}), 0) AS lead_sum,
               COUNT(b.lead_time_days) FILTER (WHERE {keep_expr}) AS lead_cnt,
               COUNT(*) AS all_bookings,
               COALESCE(SUM(CAST(b.is_canceled AS INTEGER)), 0) AS canceled
        FROM main.fact_hotel_bookings b
        JOIN main.dim_date d ON b.date_key = d.date_key
        JOIN main.dim_property p ON b.property_key = p.property_key
        {cmp_where}
        GROUP BY 1, 2, 3
        """
    )
    occ_m = q(
        f"""
        SELECT d.year AS year, d.month_name AS month_name, p.property_name AS property,
               SUM(f.occupancy_rate) AS occ_sum, COUNT(f.occupancy_rate) AS occ_cnt
        FROM main.fact_daily_occupancy f
        JOIN main.dim_date d ON f.date_key = d.date_key
        JOIN main.dim_property p ON f.property_key = p.property_key
        {cmp_where}
        GROUP BY 1, 2, 3
        """
    )
    fnb_m = q(
        f"""
        SELECT d.year AS year, d.month_name AS month_name, p.property_name AS property,
               COALESCE(SUM(f.sales_amount), 0) AS fnb_rev
        FROM main.fact_fnb_operations f
        JOIN main.dim_date d ON f.date_key = d.date_key
        JOIN main.dim_property p ON f.property_key = p.property_key
        {cmp_where}
        GROUP BY 1, 2, 3
        """
    )
    anc_m = q(
        f"""
        SELECT d.year AS year, d.month_name AS month_name, p.property_name AS property,
               COALESCE(SUM(a.spa_revenue), 0) AS spa_rev,
               COALESCE(SUM(a.event_revenue), 0) AS event_rev
        FROM main.fact_ancillary_services a
        JOIN main.dim_date d ON a.date_key = d.date_key
        JOIN main.dim_property p ON a.property_key = p.property_key
        {cmp_where}
        GROUP BY 1, 2, 3
        """
    )
    if hotel_m.empty:
        return hotel_m

    df = reduce(lambda l, r: l.merge(r, on=key_cols, how="outer"), [hotel_m, occ_m, fnb_m, anc_m])
    num_cols = [c for c in df.columns if c not in key_cols]
    df[num_cols] = df[num_cols].fillna(0)
    df["month_no"] = df["month_name"].map(month_no)
    df["year"] = df["year"].astype(int)
    return df


with tab5:
    st.markdown("### 🔄 เปรียบเทียบผลประกอบการ")
    st.caption(
        "เลือกได้เองว่าจะเทียบ 'ปีกับปี' หรือ 'สาขากับสาขา' — หน้านี้ใช้ข้อมูลทุกปี/ทุกสาขา "
        "(ไม่ผูกกับตัวกรองปี/สาขาด้านซ้าย) แต่ยังใช้ตัวกรองฤดูกาลและตัวเลือก 'ไม่นับการจองที่ยกเลิก'"
    )

    cmp_clauses = ["d.year BETWEEN 2023 AND 2026"]
    if selected_seasons and len(selected_seasons) < len(all_seasons):
        cmp_clauses.append("d.season IN (" + ", ".join(f"'{sql_escape(s)}'" for s in selected_seasons) + ")")
    cmp_where = "WHERE " + " AND ".join(cmp_clauses)

    df_all = load_monthly(cmp_where, KEEP_EXPR)

    if df_all.empty:
        st.info("ไม่พบข้อมูลตามเงื่อนไขที่เลือก")
    else:
        years_avail = sorted(int(y) for y in df_all["year"].unique())
        props_avail = sorted(df_all["property"].unique())

        mode = st.radio("รูปแบบการเปรียบเทียบ", ["📅 เทียบปีกับปี", "🏨 เทียบสาขากับสาขา"], horizontal=True)

        # ---------- เลือกสิ่งที่จะเทียบ ----------
        if mode.startswith("📅"):
            c1, c2, c3 = st.columns(3, gap="medium")
            with c1:
                year_a = st.selectbox("ปีฐาน (A)", years_avail, index=max(len(years_avail) - 2, 0))
            with c2:
                year_b = st.selectbox("ปีที่ต้องการเทียบ (B)", years_avail, index=len(years_avail) - 1)
            with c3:
                scope_props = st.multiselect("สาขาที่รวมในการเทียบ", props_avail, default=props_avail)

            scope = df_all[df_all["property"].isin(scope_props or props_avail)]
            df_a = scope[scope["year"] == year_a]
            df_b = scope[scope["year"] == year_b]

            lfl = st.checkbox("เทียบเฉพาะเดือนที่ทั้งสองปีมีข้อมูล (Like-for-like)", value=True,
                              help="ป้องกันการเทียบปีที่ยังไม่จบปีกับปีเต็ม")
            if lfl:
                common = (set(df_a["month_no"]) & set(df_b["month_no"])) - {0}
                df_a = df_a[df_a["month_no"].isin(common)]
                df_b = df_b[df_b["month_no"].isin(common)]
                if common:
                    st.caption("📆 เดือนที่ใช้เปรียบเทียบ: " + ", ".join(calendar.month_abbr[m] for m in sorted(common)))

            label_a, label_b = str(year_a), str(year_b)
            dim, dim_label = "property", "สาขา"
        else:
            c1, c2, c3 = st.columns(3, gap="medium")
            with c1:
                prop_a = st.selectbox("สาขา A", props_avail, index=0)
            with c2:
                prop_b = st.selectbox("สาขา B", props_avail, index=1 if len(props_avail) > 1 else 0)
            with c3:
                scope_years = st.multiselect("ปีที่รวมในการเทียบ", years_avail, default=years_avail)

            scope = df_all[df_all["year"].isin(scope_years or years_avail)]
            df_a = scope[scope["property"] == prop_a]
            df_b = scope[scope["property"] == prop_b]
            label_a, label_b = prop_a, prop_b
            dim, dim_label = "year", "ปี"

        name_a, name_b = f"A: {label_a}", f"B: {label_b}"
        color_map = {name_a: COLOR_A, name_b: COLOR_B}

        if df_a.empty or df_b.empty:
            st.warning("ไม่พบข้อมูลของตัวเลือกที่ต้องการเทียบ")
        else:
            if label_a == label_b:
                st.warning("A และ B เป็นค่าเดียวกัน — ผลเปรียบเทียบจะไม่มีความเปลี่ยนแปลง")

            tot_a = aggregate(df_a.assign(_k=1), ["_k"]).iloc[0]
            tot_b = aggregate(df_b.assign(_k=1), ["_k"]).iloc[0]

            # ---------- 1) Scorecards ----------
            st.markdown(f"#### 📌 ภาพรวม: {name_b} เทียบกับ {name_a}")
            card_cols = st.columns(3, gap="medium")
            for i, key in enumerate(KPI_KEYS):
                col_name, kind, direction = METRICS[key]
                va, vb = tot_a[col_name], tot_b[col_name]
                chg = change(va, vb, kind)
                delta_color = {"up": "normal", "down": "inverse", "neutral": "off"}[direction]
                with card_cols[i % 3]:
                    st.metric(
                        key, fmt(vb, kind),
                        None if pd.isna(chg) else f"{fmt_change(chg, kind)} (A: {fmt(va, kind)})",
                        delta_color=delta_color
                    )

            st.markdown("---")

            # ---------- 2) เลือกตัวชี้วัดเชิงลึก ----------
            metric_label = st.selectbox("📐 เลือกตัวชี้วัดเพื่อดูรายละเอียด", list(METRICS.keys()), key="cmp_metric")
            col_name, kind, direction = METRICS[metric_label]

            ba = aggregate(df_a, [dim])[[dim, col_name]].rename(columns={col_name: "va"})
            bb = aggregate(df_b, [dim])[[dim, col_name]].rename(columns={col_name: "vb"})
            br = ba.merge(bb, on=dim, how="outer")
            br = br.sort_values("vb", ascending=False) if dim == "property" else br.sort_values(dim)
            br["dim_s"] = br[dim].astype(str)
            br["chg"] = [change(a, b, kind) for a, b in zip(br["va"], br["vb"])]
            br["status"] = br["chg"].map(lambda c: status(c, direction))
            br["chg_txt"] = br["chg"].map(lambda c: fmt_change(c, kind))
            order = br["dim_s"].tolist()

            # ---------- 3) กราฟเทียบค่า + กราฟส่วนต่าง ----------
            col_l, col_r = st.columns([3, 2], gap="large")

            with col_l:
                st.markdown(f"**{metric_label} — แยกตาม{dim_label}**")
                long = pd.concat([
                    br[["dim_s", "va"]].rename(columns={"va": "value"}).assign(series=name_a),
                    br[["dim_s", "vb"]].rename(columns={"vb": "value"}).assign(series=name_b),
                ])
                long["plot_val"] = long["value"] / 1e9 if kind == "money" else long["value"]
                long["label"] = long["value"].map(lambda v: fmt(v, kind))
                fig_l = px.bar(long, x="dim_s", y="plot_val", color="series", barmode="group", text="label",
                               color_discrete_map=color_map, category_orders={"dim_s": order})
                fig_l.update_traces(textposition="outside", cliponaxis=False)
                fig_l.update_xaxes(type="category")
                fig_l.update_yaxes(title="Rp พันล้าน" if kind == "money" else "")
                st.plotly_chart(clean_chart(fig_l), use_container_width=True)

            with col_r:
                st.markdown(f"**ส่วนต่าง B เทียบ A ({'จุด %' if kind == 'pct' else '%'})**")
                var_df = br.dropna(subset=["chg"])
                if not var_df.empty:
                    fig_r = px.bar(var_df, x="chg", y="dim_s", orientation="h", color="status", text="chg_txt",
                                   color_discrete_map=STATUS_COLORS, category_orders={"dim_s": order})
                    fig_r.update_traces(textposition="outside", cliponaxis=False)
                    fig_r.add_vline(x=0, line_color="gray", line_width=1)
                    fig_r.update_yaxes(type="category", autorange="reversed")
                    st.plotly_chart(clean_chart(fig_r), use_container_width=True)
                else:
                    st.info("ไม่มีข้อมูลเพียงพอสำหรับคำนวณส่วนต่าง")

            # ---------- 4) แนวโน้มรายเดือน A vs B ----------
            st.markdown(f"**แนวโน้มรายเดือน: {metric_label}**")
            trend = pd.concat([
                aggregate(df_a, ["month_no"]).assign(series=name_a),
                aggregate(df_b, ["month_no"]).assign(series=name_b),
            ])
            trend = trend[trend["month_no"] > 0].sort_values("month_no")
            trend["month"] = trend["month_no"].map(lambda m: calendar.month_abbr[m])
            trend["plot_val"] = trend[col_name] / 1e9 if kind == "money" else trend[col_name]
            fig_t = px.line(trend, x="month", y="plot_val", color="series", markers=True,
                            color_discrete_map=color_map, category_orders={"month": MONTH_LABELS})
            fig_t.update_traces(line_width=3, marker_size=7)
            fig_t.update_yaxes(title="Rp พันล้าน" if kind == "money" else "")
            st.plotly_chart(clean_chart(fig_t), use_container_width=True)

            # ---------- 5) ตารางรายละเอียด + สรุปอัตโนมัติ ----------
            total_row = {dim_label: "รวม", name_a: fmt(tot_a[col_name], kind), name_b: fmt(tot_b[col_name], kind),
                         "เปลี่ยนแปลง": fmt_change(change(tot_a[col_name], tot_b[col_name], kind), kind),
                         "สถานะ": status(change(tot_a[col_name], tot_b[col_name], kind), direction)}
            body = pd.DataFrame({
                dim_label: br["dim_s"],
                name_a: br["va"].map(lambda v: fmt(v, kind)),
                name_b: br["vb"].map(lambda v: fmt(v, kind)),
                "เปลี่ยนแปลง": br["chg_txt"],
                "สถานะ": br["status"],
            })
            st.dataframe(pd.concat([pd.DataFrame([total_row]), body], ignore_index=True),
                         hide_index=True, use_container_width=True)

            valid = br.dropna(subset=["chg"])
            if not valid.empty:
                hi, lo = valid.loc[valid["chg"].idxmax()], valid.loc[valid["chg"].idxmin()]
                tot_chg = change(tot_a[col_name], tot_b[col_name], kind)
                msg = (f"**สรุป {metric_label}**: ภาพรวม {name_b} เทียบ {name_a} = {fmt_change(tot_chg, kind)} · "
                       f"เพิ่มขึ้นมากที่สุด: **{hi['dim_s']}** ({hi['chg_txt']}) · "
                       f"เพิ่มขึ้นน้อยที่สุด/ลดลงมากที่สุด: **{lo['dim_s']}** ({lo['chg_txt']})")
                if direction == "down":
                    msg += " (ตัวชี้วัดนี้ ค่าน้อยกว่า = ดีกว่า)"
                st.info(msg)

        # ---------- 6) Heatmap ภาพรวมทุกปี × ทุกสาขา ----------
        with st.expander("🗺️ ภาพรวมทุกปี × ทุกสาขา (Heatmap) ตามตัวชี้วัดที่เลือก"):
            m_label = st.session_state.get("cmp_metric", list(METRICS.keys())[0])
            h_col, h_kind, h_dir = METRICS[m_label]
            hm = aggregate(df_all, ["year", "property"]).pivot(index="property", columns="year", values=h_col)
            z = hm / 1e9 if h_kind == "money" else hm
            text = hm.apply(lambda s: s.map(lambda v: fmt(v, h_kind)))
            fig_h = px.imshow(z.values, x=[str(c) for c in z.columns], y=z.index.tolist(), aspect="auto",
                              color_continuous_scale="RdYlGn_r" if h_dir == "down" else "Blues")
            fig_h.update_traces(text=text.values, texttemplate="%{text}")
            fig_h.update_layout(coloraxis_showscale=False, title=m_label)
            st.plotly_chart(clean_chart(fig_h), use_container_width=True)
            if h_kind in ("money", "int"):
                st.caption("⚠️ ปีที่ข้อมูลไม่ครบ 12 เดือนจะมีค่ารวมต่ำกว่าความเป็นจริง")

# =========================================================
# FOOTER
# =========================================================

st.markdown("---")
st.caption("Indonesia Hotel Executive Analytics | Supported by AJ.Prem")