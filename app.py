"""
app.py  -  Entry point.  Run with:   streamlit run app.py

The app has three pages. Streamlit re-runs this file on every click, so we remember which page
we are on (and the user's data) in st.session_state.

    "home"   -> choose algorithm and process count, then Enter Input / Visualise Random
    "input"  -> type the arrival / burst (/ priority) times
    "viz"    -> live simulation + results (+ time-quantum comparison for Round Robin)
"""
import random

import pandas as pd
import streamlit as st

st.set_page_config(page_title="CPU Scheduling Visualiser", page_icon="🧠", layout="wide",
                   initial_sidebar_state="collapsed")

import scheduler                                   # noqa: E402  (the algorithms)
from live import live_dashboard                    # noqa: E402  (live per-second dashboard)
from theme import inject_css                       # noqa: E402  (look and feel)
from views import color_map, quantum_tab, results_tab  # noqa: E402  (analysis tabs)

PRIORITY_ALGOS = ("Priority Preemptive", "Priority Non-Preemptive")

# ---- session state: values that must survive between clicks ----
S = st.session_state
S.setdefault("page", "home")
S.setdefault("algo", scheduler.ALGOS[0])
S.setdefault("n", 4)            # process count
S.setdefault("quantum", 2)      # Round Robin time quantum


def goto(page: str):
    """Switch page and redraw."""
    S["page"] = page
    st.rerun()


# ───────────────────────────── data helpers ─────────────────────────────
def random_df(n: int) -> pd.DataFrame:
    """'Visualise Random': random arrival (0-8), burst (1-7) and unique priorities."""
    return pd.DataFrame({
        "Process": [f"P{i + 1}" for i in range(n)],
        "Task": ["Random task"] * n,
        "Arrival": [random.randint(0, 8) for _ in range(n)],
        "Burst": [random.randint(1, 7) for _ in range(n)],
        "Priority": random.sample(range(1, n + 1), n),
    })


def starter_df(n: int) -> pd.DataFrame:
    """Pre-filled table for 'Enter Input' (first 4 rows = the activity data, extra rows simple defaults)."""
    rows = []
    for i in range(n):
        if i < len(scheduler.ACTIVITY_DATA):
            r = scheduler.ACTIVITY_DATA.iloc[i].to_dict()
        else:
            r = {"Task": "Custom task", "Arrival": i, "Burst": 3, "Priority": i + 1}
        r["Process"] = f"P{i + 1}"
        rows.append(r)
    return pd.DataFrame(rows)[["Process", "Task", "Arrival", "Burst", "Priority"]]


# ───────────────────────────── page 1: start ─────────────────────────────
def home():
    inject_css(card=True)
    st.markdown('<div class="brand">CPU Scheduling Visualiser<small>Watch each algorithm run, second by second</small></div>',
                unsafe_allow_html=True)
    S["algo"] = st.selectbox("Algorithm:", scheduler.ALGOS, index=scheduler.ALGOS.index(S["algo"]))
    S["n"] = int(st.number_input("Process Count:", 1, 10, S["n"]))
    if S["algo"] == "Round Robin":
        S["quantum"] = int(st.number_input("Time Quantum (ms):", 1, 20, S["quantum"]))
    st.write("")
    if st.button("Enter Input"):
        S["df"] = starter_df(S["n"])
        goto("input")
    if st.button("Visualise Random"):
        S["df"] = random_df(S["n"])
        goto("viz")
    st.markdown("---")
    if st.button("Load Practical Activity 1 data (Round Robin, Q = 2)"):
        S.update(algo="Round Robin", n=4, quantum=2, df=starter_df(4))
        goto("viz")


# ───────────────────────────── page 2: enter input ─────────────────────────────
def input_page():
    inject_css(card=True)
    st.markdown(f'<div class="brand">Enter Input<small>{S["algo"]} · {S["n"]} processes</small></div>', unsafe_allow_html=True)
    show_pri = S["algo"] in PRIORITY_ALGOS
    cols = ["Process", "Arrival", "Burst"] + (["Priority"] if show_pri else [])
    edited = st.data_editor(
        S["df"][cols], hide_index=True, num_rows="fixed", width="stretch", key="inp",
        column_config={
            "Process": st.column_config.TextColumn("PID", disabled=True),
            "Arrival": st.column_config.NumberColumn("Arrival Time", min_value=0, step=1, format="%d"),
            "Burst": st.column_config.NumberColumn("Burst Time", min_value=1, step=1, format="%d"),
            "Priority": st.column_config.NumberColumn("Priority (1 = highest)", min_value=1, step=1, format="%d"),
        })
    if S["algo"] == "Round Robin":
        S["quantum"] = int(st.number_input("Time Quantum (ms):", 1, 20, S["quantum"]))
    c1, c2 = st.columns(2)
    if c1.button("← Back"):
        goto("home")
    if c2.button("Visualise", type="primary"):
        out = S["df"].copy()
        for c in cols:
            out[c] = edited[c]
        if out[cols[1:]].isnull().any().any():                 # a cell was left empty
            st.error("Please fill every cell.")
        else:
            for c in ("Arrival", "Burst", "Priority"):
                out[c] = out[c].astype(int)
            S["df"] = out
            goto("viz")


# ───────────────────────────── page 3: visualiser ─────────────────────────────
def viz():
    inject_css()
    algo, df, q = S["algo"], S["df"], S["quantum"]
    show_pri = algo in PRIORITY_ALGOS

    top = st.columns([5, 1.4])
    top[0].markdown(f"### CPU Scheduling · <span style='color:#38bdf8'>{algo}</span>", unsafe_allow_html=True)
    if top[1].button("↺ Reset and Restart", width="stretch"):
        goto("home")

    res = scheduler.run_algo(df, algo, q)          # run the chosen algorithm once
    cmap = color_map(df.Process.tolist())

    names = ["Live simulation", "Results and Gantt chart"] + (["Time quantum comparison"] if algo == "Round Robin" else [])
    tabs = st.tabs(names)
    with tabs[0]:
        live_dashboard(df, res, algo, q, show_pri)
    with tabs[1]:
        results_tab(res, cmap, show_pri)
    if algo == "Round Robin":
        with tabs[2]:
            quantum_tab(df, cmap)


# ───────────────────────────── router ─────────────────────────────
{"home": home, "input": input_page, "viz": viz}[S["page"]]()
