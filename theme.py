"""
theme.py  -  Look and feel of the whole app.

Streamlit lets us inject our own CSS with st.markdown(..., unsafe_allow_html=True).
Here we keep one clean dark-slate theme (no decorative background) and one extra
rule-set that turns the first two pages (start page, input page) into a centred card.
"""
import streamlit as st

# Colours used by the Gantt chart and the live dashboard (one colour per process).
PALETTE = ["#38bdf8", "#a78bfa", "#fbbf24", "#34d399", "#f472b6",
           "#fb923c", "#60a5fa", "#f87171", "#2dd4bf", "#c084fc"]

BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');
html, body, [class*="css"], .stApp { font-family: 'Inter', sans-serif; }
.stApp { background: #0f172a; color: #e2e8f0; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2rem; max-width: 1250px; }
.kpi { padding: 16px 20px; border-radius: 14px; background: #162038; border: 1px solid #25324f; }
.kpi .l { font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: .1em; }
.kpi .v { font-family: 'JetBrains Mono', monospace; font-size: 1.9rem; font-weight: 700; margin-top: 4px; color: #f8fafc; }
.sect { font-size: 1.1rem; font-weight: 600; margin: 26px 0 10px; padding-left: 10px; border-left: 4px solid #38bdf8; }
.verdict { padding: 20px 24px; border-radius: 14px; background: rgba(52,211,153,.10); border: 1px solid rgba(52,211,153,.45); }
.verdict h3 { margin: 0 0 8px; color: #6ee7b7; font-size: 1.25rem; }
.verdict p { margin: 4px 0; color: #cbd5e1; line-height: 1.6; }
div[data-testid="stTabs"] button { font-weight: 600; }
div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
</style>
"""

# Only used on the start page and the input page: turns the page into a centred card.
CARD_CSS = """
<style>
.block-container { max-width: 540px !important; margin-top: 8vh; padding: 2.2rem 2.5rem !important;
  background: #162038; border: 1px solid #25324f; border-radius: 18px; box-shadow: 0 20px 50px rgba(0,0,0,.35); }
.block-container .stButton > button { width: 100%; height: 46px; border-radius: 10px; font-weight: 600;
  background: #243352; color: #fff; border: 1px solid #334566; }
.block-container .stButton > button:hover { border-color: #38bdf8; color: #bae6fd; }
.block-container .stButton > button[kind="primary"] { background: #0284c7; border: none; }
.brand { font-size: 2rem; font-weight: 700; color: #fff; letter-spacing: -.02em; margin-bottom: 4px; }
.brand small { display: block; font-size: .9rem; font-weight: 500; color: #94a3b8; letter-spacing: 0; margin-top: 2px; }
label p { font-weight: 600 !important; color: #e2e8f0 !important; }
</style>
"""


def inject_css(card: bool = False):
    """Apply the theme. card=True gives the centred card look."""
    st.markdown(BASE_CSS, unsafe_allow_html=True)
    if card:
        st.markdown(CARD_CSS, unsafe_allow_html=True)


def sect(text: str):
    """Section heading with a blue accent bar."""
    st.markdown(f'<div class="sect">{text}</div>', unsafe_allow_html=True)


def kpi(label: str, value, unit: str = "") -> str:
    """HTML for one summary tile (e.g. 'Average waiting time  7.00 ms')."""
    return f'<div class="kpi"><div class="l">{label}</div><div class="v">{value} <span style="font-size:1rem;color:#94a3b8">{unit}</span></div></div>'
