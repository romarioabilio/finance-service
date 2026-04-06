from __future__ import annotations

import streamlit as st


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
        html, body, [class*="css"]  { font-family: 'Manrope', sans-serif; }
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(37, 99, 235, 0.09), transparent 28%),
                radial-gradient(circle at bottom right, rgba(15, 118, 110, 0.08), transparent 22%),
                linear-gradient(180deg, #F8FAFC 0%, #F1F5F9 100%);
        }
        .block-container { max-width: 1220px; padding-top: 1.1rem; padding-bottom: 3rem; }
        [data-testid="stSidebar"] {
            background: rgba(255,255,255,0.92);
            border-right: 1px solid #E2E8F0;
        }
        .hero {
            background: linear-gradient(135deg, #0F172A 0%, #1D4ED8 60%, #0F766E 100%);
            border-radius: 30px;
            padding: 1.8rem;
            color: white;
            box-shadow: 0 26px 60px rgba(15, 23, 42, 0.16);
            margin-bottom: 1rem;
        }
        .hero-kicker {
            text-transform: uppercase; letter-spacing: .14em; font-size: .78rem;
            color: rgba(255,255,255,.72); margin-bottom: .45rem;
        }
        .hero-title {
            font-size: 2.25rem; line-height: 1.03; font-weight: 800; margin-bottom: .6rem;
        }
        .hero-copy { max-width: 760px; color: rgba(255,255,255,.88); font-size: 1rem; margin: 0; }
        .section-shell {
            background: rgba(255,255,255,.88);
            border: 1px solid #E2E8F0;
            border-radius: 24px;
            padding: 1rem 1rem .25rem;
            margin-bottom: 1rem;
            box-shadow: 0 12px 32px rgba(15, 23, 42, 0.04);
        }
        .section-title { font-size: 1.06rem; font-weight: 800; color: #0F172A; margin-bottom: .2rem; }
        .section-copy { color: #64748B; font-size: .95rem; margin-bottom: .75rem; }
        .stat-card {
            background: rgba(255,255,255,.94); border: 1px solid #E2E8F0; border-radius: 22px;
            padding: 1rem; min-height: 132px; box-shadow: 0 12px 24px rgba(15, 23, 42, 0.04);
        }
        .stat-label {
            color: #64748B; font-size: .8rem; text-transform: uppercase; letter-spacing: .08em; margin-bottom: .55rem;
        }
        .stat-value { color: #0F172A; font-size: 1.72rem; font-weight: 800; line-height: 1.05; margin-bottom: .28rem; }
        .stat-foot { color: #475569; font-size: .9rem; }
        .feature-grid {
            display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 1rem; margin-bottom: 1rem;
        }
        .feature-card {
            background: white; border: 1px solid #E2E8F0; border-radius: 22px; padding: 1rem;
            box-shadow: 0 12px 24px rgba(15, 23, 42, 0.04);
        }
        .feature-badge {
            display:inline-flex; width: 30px; height: 30px; align-items:center; justify-content:center;
            border-radius:999px; background:#DBEAFE; color:#1D4ED8; font-weight:800; margin-bottom:.8rem;
        }
        .feature-title { font-weight: 700; color: #0F172A; margin-bottom: .35rem; }
        .feature-copy { color: #64748B; font-size: .94rem; margin: 0; }
        .stButton > button {
            min-height: 2.9rem; border-radius: 999px; border: 1px solid #CBD5E1; background: white; font-weight: 700;
        }
        .stButton > button:hover { border-color: #2563EB; color: #2563EB; }
        .stTabs [data-baseweb="tab"] {
            border-radius: 999px; padding-left: 1rem; padding-right: 1rem; background: #E2E8F0;
        }
        .stTabs [aria-selected="true"] { background: #0F172A !important; color: white !important; }
        div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, .stDateInput > div > div, .stNumberInput > div > div {
            background: rgba(255,255,255,.92); border-radius: 16px;
        }
        div[data-testid="stDataFrame"] { border-radius: 18px; overflow: hidden; border: 1px solid #E2E8F0; }
        .stAlert { border-radius: 18px; }
        @media (max-width: 900px) {
            .feature-grid { grid-template-columns: 1fr; }
            .hero-title { font-size: 1.8rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
