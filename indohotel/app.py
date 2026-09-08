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