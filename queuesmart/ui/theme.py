"""Identité visuelle commune aux deux interfaces Streamlit.

CSS limité à l'habillage, sans modification des calculs métier.
"""
import streamlit as st


def apply_theme() -> None:
    st.markdown("""<style>
    :root { --sq-navy:#14233b; --sq-blue:#2862a4; --sq-gold:#d6a858; }
    [data-testid="stSidebar"] { border-right: 1px solid #2f4867; }
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] { font-weight: 600; }
    [data-testid="stHorizontalBlock"] { align-items: stretch; }
    div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; }
    [data-testid="stSegmentedControl"] { margin: 10px 0 22px; }
    [data-testid="stDownloadButton"] button { border-radius: 11px; }
    .stApp { background:linear-gradient(160deg,#f5f8fc 0%,#eef3f9 100%); color:#15263d; }
    [data-testid="stSidebar"] { background:#14233b; }
    [data-testid="stSidebar"] * { color:#f5f8ff; }
    [data-testid="stSidebar"] input { color:#14233b !important; }
    .block-container { padding-top:1.7rem; padding-bottom:3rem; max-width:1480px; }
    h1,h2,h3 { color:#14233b !important; letter-spacing:-.025em; }
    h1 { font-size:2.1rem !important; }
    [data-testid="stMetric"] { background:white; border:1px solid #dce5ef;
       border-radius:15px; padding:17px 18px; box-shadow:0 4px 18px #14233b0a; }
    [data-testid="stMetricLabel"] { color:#586a80; }
    [data-testid="stMetricValue"] { color:#14233b; }
    [data-testid="stTabs"] [data-baseweb="tab-list"] { gap:.4rem; }
    [data-testid="stTabs"] button[role="tab"] { border-radius:10px 10px 0 0; padding:10px 16px; }
    [data-testid="stTabs"] button[aria-selected="true"] { color:#2862a4; border-bottom-color:#d6a858; }
    [data-testid="stDataFrame"] { border:1px solid #dce5ef; border-radius:12px; overflow:hidden; }
    div.stButton > button[kind="primary"],div.stDownloadButton > button[kind="primary"] {
       background:#2862a4; border-color:#2862a4; color:white; border-radius:10px; }
    div[data-testid="stAlert"] { border-radius:12px; }
    .sq-hero { padding:23px 28px; background:linear-gradient(115deg,#14233b,#24456b);
       border-radius:18px; margin-bottom:22px; box-shadow:0 8px 28px #14233b22; }
    .sq-hero h1 { color:white !important; margin:0; font-size:2.05rem !important; }
    .sq-hero p { color:#dce8f7; margin:9px 0 0; font-size:.97rem; }
    .sq-eyebrow { color:#e2b96e; font-size:.73rem; letter-spacing:.14em; font-weight:700; }
    .sq-section { color:#536b87; font-weight:650; text-transform:uppercase;
      letter-spacing:.08em; font-size:.77rem; margin-top:15px; }
    @media(max-width:700px) { .block-container{padding:1rem .7rem;} .sq-hero{padding:18px;} }
    </style>""", unsafe_allow_html=True)


def hero(title: str, subtitle: str, eyebrow: str = "SIMULATEUR DE FILES D'ATTENTE") -> None:
    from html import escape
    st.markdown(
        f'<div class="sq-hero"><div class="sq-eyebrow">{escape(eyebrow)}</div>'
        f'<h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )
