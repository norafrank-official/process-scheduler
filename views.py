"""
views.py  -  The two analysis tabs that match the questions in Practical Activity 1.

    results_tab()  - Gantt chart + completion / turnaround / waiting / response time of every
                     process + average turnaround, average waiting, total context switches.
    quantum_tab()  - Run Round Robin with two time quanta (2 ms and 3 ms), show a tool-generated
                     comparison, and pick the quantum with the better balance.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from scheduler import run_algo
from theme import PALETTE, kpi, sect


# ───────────────────────────── Gantt chart ─────────────────────────────
def color_map(pids):
    """Give every process its own colour."""
    return {p: PALETTE[i % len(PALETTE)] for i, p in enumerate(sorted(pids))}


def gantt(res, cmap, height=200):
    """Horizontal timeline: one coloured bar per slice (idle gaps are shown dark)."""
    fig = go.Figure()
    seen = set()
    for s in res.slices:
        idle = s["pid"] == "Idle"
        fig.add_trace(go.Bar(
            x=[s["end"] - s["start"]], base=[s["start"]], y=["CPU"], orientation="h", name=s["pid"],
            showlegend=(s["pid"] not in seen and not idle), legendgroup=s["pid"],
            marker=dict(color="#1e293b" if idle else cmap[s["pid"]], line=dict(color="#0f172a", width=2.5)),
            text=f"<b>{'idle' if idle else s['pid']}</b>", textposition="inside", insidetextanchor="middle",
            textfont=dict(color="#0b1220", size=14),
            hovertemplate=f"<b>{s['pid']}</b><br>{s['start']} → {s['end']} ms<extra></extra>"))
        seen.add(s["pid"])
    ticks = sorted({s["start"] for s in res.slices} | {res.end})      # show every slice boundary
    fig.update_layout(
        barmode="overlay", bargap=0.25, height=height, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1"),
        xaxis=dict(title="Time (ms)", tickmode="array", tickvals=ticks, range=[0, res.end + 0.3],
                   gridcolor="rgba(148,163,184,.15)", zeroline=False),
        yaxis=dict(showticklabels=False, fixedrange=True), legend=dict(orientation="h", y=1.2, x=0))
    return fig


def metrics_table(res, show_priority=False):
    """Per-process results: completion, turnaround, waiting and response time."""
    cols = ["Process", "Task", "Arrival", "Burst"] + (["Priority"] if show_priority else []) + \
           ["Completion", "Turnaround", "Waiting", "Response"]
    return res.table[cols]


# ───────────────────────────── Tab: results ─────────────────────────────
def results_tab(res, cmap, show_priority):
    c = st.columns(3)
    c[0].markdown(kpi("Average turnaround time", f"{res.avg_tat:.2f}", "ms"), unsafe_allow_html=True)
    c[1].markdown(kpi("Average waiting time", f"{res.avg_wt:.2f}", "ms"), unsafe_allow_html=True)
    c[2].markdown(kpi("Total context switches", res.switches), unsafe_allow_html=True)

    sect("Gantt chart · execution sequence")
    st.plotly_chart(gantt(res, cmap), width="stretch", key="res_gantt")
    st.code(" → ".join(f"{s['pid']}({s['start']}-{s['end']})" for s in res.slices if s["pid"] != "Idle"), language=None)

    sect("Completion, turnaround, waiting and response time of every process")
    st.dataframe(metrics_table(res, show_priority), width="stretch", hide_index=True)


# ───────────────────────────── Tab: quantum comparison ─────────────────────────────
def quantum_tab(df, cmap):
    c1, c2 = st.columns(2)
    qa = int(c1.number_input("First time quantum (ms)", 1, 20, 2, key="qa"))
    qb = int(c2.number_input("Second time quantum (ms)", 1, 20, 3, key="qb"))
    A, B = run_algo(df, "Round Robin", qa), run_algo(df, "Round Robin", qb)

    sect("Gantt charts")
    for i, r in enumerate((A, B)):
        st.markdown(f"**Time quantum = {r.quantum} ms**")
        st.plotly_chart(gantt(r, cmap, height=180), width="stretch", key=f"q_gantt{i}")

    # ---- tool-generated comparison table -------------------------------------------------
    sect("Tool-generated comparison")
    metrics = [("Average turnaround time (ms)", A.avg_tat, B.avg_tat),
               ("Average waiting time (ms)", A.avg_wt, B.avg_wt),
               ("Average response time (ms)", A.avg_rt, B.avg_rt),
               ("Total context switches", A.switches, B.switches)]

    def better(a, b):
        return "Same" if abs(a - b) < 1e-9 else (f"Q = {qa}" if a < b else f"Q = {qb}")   # lower is better

    comp = pd.DataFrame([{"Metric": m, f"Q = {qa} ms": a, f"Q = {qb} ms": b, "Better (lower)": better(a, b)}
                         for m, a, b in metrics])
    st.dataframe(comp.style.format({f"Q = {qa} ms": "{:.2f}", f"Q = {qb} ms": "{:.2f}"}),
                 width="stretch", hide_index=True)

    fig = go.Figure()
    labels = ["Avg turnaround", "Avg waiting", "Avg response"]
    for r, color in ((A, "#38bdf8"), (B, "#a78bfa")):
        vals = [r.avg_tat, r.avg_wt, r.avg_rt]
        fig.add_bar(name=f"Q = {r.quantum} ms", x=labels, y=vals, marker_color=color,
                    text=[f"{v:.2f}" for v in vals], textposition="outside")
    fig.update_layout(barmode="group", height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#cbd5e1"), margin=dict(t=30, b=10), yaxis=dict(gridcolor="rgba(148,163,184,.15)"),
                      title="Average times (ms) · lower is better")
    st.plotly_chart(fig, width="stretch", key="q_bar")

    st.markdown("**Per-process results**")
    d1, d2 = st.columns(2)
    for col, r in ((d1, A), (d2, B)):
        col.caption(f"Q = {r.quantum} ms")
        col.dataframe(r.table[["Process", "Completion", "Turnaround", "Waiting", "Response"]],
                      width="stretch", hide_index=True)

    # ---- choose the better quantum ---------------------------------------------------------
    sect("Selecting the better time quantum")
    # Three criteria from the question; for each, the smaller value wins.
    criteria = [("waiting time", A.avg_wt, B.avg_wt),
                ("fair CPU access (average response time)", A.avg_rt, B.avg_rt),
                ("context switching", A.switches, B.switches)]
    wins_a = sum(1 for _, a, b in criteria if a < b)
    wins_b = sum(1 for _, a, b in criteria if b < a)
    if wins_a == wins_b:                                  # tie -> prefer the lower waiting time
        best, other = (A, B) if A.avg_wt <= B.avg_wt else (B, A)
    else:
        best, other = (A, B) if wins_a > wins_b else (B, A)

    lines = []
    for name, a, b in criteria:
        va, vb = (a, b) if best is A else (b, a)          # va = best quantum's value, vb = other's
        if abs(va - vb) < 1e-9:
            lines.append(f"Both quanta are equal for {name}.")
        elif va < vb:
            lines.append(f"Q = {best.quantum} ms is better for {name}: <b>{va:.2f}</b> vs {vb:.2f}.")
        else:
            lines.append(f"Q = {other.quantum} ms is better for {name}: <b>{vb:.2f}</b> vs {va:.2f} "
                         f"(the trade-off of choosing Q = {best.quantum} ms).")
    st.markdown(f'<div class="verdict"><h3>Recommended time quantum: {best.quantum} ms</h3>'
                + "".join(f"<p>• {l}</p>" for l in lines)
                + "<p style='margin-top:10px'>A very small quantum gives quick responses but many context switches; "
                  "a large quantum reduces switching but makes Round Robin behave like FCFS. "
                  "The recommended value is the one that wins the most of the three criteria.</p></div>",
                unsafe_allow_html=True)
