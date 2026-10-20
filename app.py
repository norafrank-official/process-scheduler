"""
Round Robin CPU Scheduling Lab  -  Smart Municipal Control Centre (SDG 6 · 11 · 12)
Run locally :  streamlit run app.py
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ───────────────────────────── page config ─────────────────────────────
st.set_page_config(
    page_title="RR Scheduler Lab · Municipal Control Centre",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

PALETTE = ["#22d3ee", "#a78bfa", "#fbbf24", "#34d399", "#f472b6", "#fb923c", "#60a5fa", "#f87171"]
SDG_TAG = {
    "Water-quality monitoring": ("SDG 6", "#26bde2"),
    "Waste-collection scheduling": ("SDG 12", "#bf8b2e"),
    "Traffic-pollution analysis": ("SDG 11", "#fd9d24"),
    "Public energy-use monitoring": ("SDG 11", "#fd9d24"),
}

DEFAULT_DATA = pd.DataFrame(
    {
        "Process": ["P1", "P2", "P3", "P4"],
        "Task": [
            "Water-quality monitoring",
            "Waste-collection scheduling",
            "Traffic-pollution analysis",
            "Public energy-use monitoring",
        ],
        "Arrival": [0, 1, 2, 3],
        "Burst": [5, 3, 4, 2],
    }
)

# ───────────────────────────── styling ─────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"], .stApp { font-family: 'Space Grotesk', sans-serif; }
.stApp {
  background:
    radial-gradient(900px 500px at 8% -10%, rgba(34,211,238,.13), transparent 60%),
    radial-gradient(800px 500px at 100% 0%, rgba(167,139,250,.14), transparent 60%),
    #070b14;
  color: #e6edf7;
}
header[data-testid="stHeader"] { background: transparent; }
section[data-testid="stSidebar"] {
  background: #0a1020; border-right: 1px solid rgba(148,163,184,.12);
}
.block-container { padding-top: 1.6rem; max-width: 1280px; }

.hero {
  position: relative; overflow: hidden;
  padding: 30px 34px; border-radius: 22px; margin-bottom: 18px;
  background: linear-gradient(135deg, rgba(34,211,238,.10), rgba(167,139,250,.10));
  border: 1px solid rgba(148,163,184,.18);
}
.hero:after {
  content:""; position:absolute; right:-60px; top:-60px; width:260px; height:260px; border-radius:50%;
  background: conic-gradient(from 0deg, #22d3ee, #a78bfa, #f472b6, #fbbf24, #22d3ee);
  filter: blur(70px); opacity:.28;
}
.hero .eyebrow { font-family:'JetBrains Mono',monospace; font-size:12px; letter-spacing:.18em;
  color:#22d3ee; text-transform:uppercase; }
.hero h1 { font-size: 2.3rem; font-weight:700; margin:6px 0 6px;
  background: linear-gradient(90deg,#fff,#a5f3fc 55%,#c4b5fd); -webkit-background-clip:text; color:transparent; }
.hero p { color:#9fb0c8; margin:0; max-width: 780px; line-height:1.55; }
.chip { display:inline-block; padding:3px 11px; border-radius:999px; font-size:12px; font-weight:600;
  margin-right:6px; margin-top:12px; color:#06101c; }

.kpi { padding:16px 18px; border-radius:16px; background:rgba(15,23,42,.7);
  border:1px solid rgba(148,163,184,.16); height:100%; }
.kpi .l { font-size:11.5px; color:#8ea0ba; text-transform:uppercase; letter-spacing:.12em; }
.kpi .v { font-family:'JetBrains Mono',monospace; font-size:1.9rem; font-weight:600; margin-top:4px; }
.kpi .s { font-size:12px; color:#6f819b; margin-top:2px; }
.kpi.accent { border-color: rgba(34,211,238,.45); box-shadow: 0 0 0 1px rgba(34,211,238,.15) inset; }

.sect { font-size:1.15rem; font-weight:600; margin:26px 0 10px; display:flex; align-items:center; gap:10px; }
.sect:before { content:""; width:4px; height:20px; border-radius:2px;
  background:linear-gradient(#22d3ee,#a78bfa); }

.verdict { padding:22px 26px; border-radius:18px;
  background:linear-gradient(135deg, rgba(52,211,153,.12), rgba(34,211,238,.08));
  border:1px solid rgba(52,211,153,.4); }
.verdict h3 { margin:0 0 6px; font-size:1.3rem; color:#6ee7b7; }
.verdict p { margin:4px 0; color:#cbd5e1; line-height:1.6; }

.qbox { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
.qitem { padding:6px 14px; border-radius:10px; font-family:'JetBrains Mono',monospace; font-weight:600;
  color:#06101c; font-size:14px; }
.qarrow { color:#52637d; }
.running { border:1px dashed #22d3ee; background:rgba(34,211,238,.08); color:#a5f3fc;
  padding:6px 14px; border-radius:10px; font-family:'JetBrains Mono',monospace; font-weight:600; }

div[data-testid="stTabs"] button { font-weight:600; }
div[data-testid="stDataFrame"] { border-radius:12px; overflow:hidden; }
</style>
""",
    unsafe_allow_html=True,
)

# ───────────────────────────── scheduler core ─────────────────────────────


@dataclass
class Result:
    quantum: int
    slices: list  # dicts: pid, start, end
    table: pd.DataFrame
    avg_tat: float
    avg_wt: float
    avg_rt: float
    avg_ct: float
    switches: int
    makespan: int
    cpu_util: float
    throughput: float


def round_robin(df: pd.DataFrame, quantum: int) -> Result:
    """Round Robin, context-switch overhead ignored.

    Tie rule: a process arriving at the same instant a running process is pre-empted
    enters the ready queue BEFORE the pre-empted process (standard textbook convention).
    Context switch = CPU hand-over from one process to a *different* process.
    """
    procs = df.sort_values(["Arrival", "Process"], kind="stable").to_dict("records")
    n = len(procs)
    remaining = {p["Process"]: int(p["Burst"]) for p in procs}
    arrival = {p["Process"]: int(p["Arrival"]) for p in procs}
    burst = dict(remaining)
    first_start: dict = {}
    completion: dict = {}
    slices: list = []

    queue: deque = deque()
    idx = 0
    t = 0

    def admit(upto: int):
        nonlocal idx
        while idx < n and int(procs[idx]["Arrival"]) <= upto:
            queue.append(procs[idx]["Process"])
            idx += 1

    admit(t)
    while len(completion) < n:
        if not queue:  # CPU idle until next arrival
            nxt = int(procs[idx]["Arrival"])
            slices.append({"pid": "Idle", "start": t, "end": nxt})
            t = nxt
            admit(t)
            continue
        pid = queue.popleft()
        first_start.setdefault(pid, t)
        run = min(quantum, remaining[pid])
        slices.append({"pid": pid, "start": t, "end": t + run})
        t += run
        remaining[pid] -= run
        admit(t)  # new arrivals first …
        if remaining[pid] > 0:
            queue.append(pid)  # … then the pre-empted process
        else:
            completion[pid] = t

    rows = []
    for p in procs:
        pid = p["Process"]
        ct = completion[pid]
        tat = ct - arrival[pid]
        wt = tat - burst[pid]
        rt = first_start[pid] - arrival[pid]
        rows.append(
            {
                "Process": pid,
                "Task": p["Task"],
                "Arrival": arrival[pid],
                "Burst": burst[pid],
                "Completion": ct,
                "Turnaround": tat,
                "Waiting": wt,
                "Response": rt,
            }
        )
    table = pd.DataFrame(rows).sort_values("Process").reset_index(drop=True)

    real = [s for s in slices if s["pid"] != "Idle"]
    switches = sum(1 for a, b in zip(real, real[1:]) if a["pid"] != b["pid"])
    makespan = max(completion.values()) - min(arrival.values())
    busy = sum(s["end"] - s["start"] for s in real)
    return Result(
        quantum=quantum,
        slices=slices,
        table=table,
        avg_tat=table["Turnaround"].mean(),
        avg_wt=table["Waiting"].mean(),
        avg_rt=table["Response"].mean(),
        avg_ct=table["Completion"].mean(),
        switches=switches,
        makespan=makespan,
        cpu_util=100 * busy / max(1, max(completion.values())),
        throughput=n / max(1, max(completion.values())),
    )


# ───────────────────────────── visual helpers ─────────────────────────────


def color_map(pids):
    return {p: PALETTE[i % len(PALETTE)] for i, p in enumerate(sorted(pids))}


def gantt(res: Result, cmap: dict, upto: float | None = None, height: int = 330) -> go.Figure:
    fig = go.Figure()
    shown = set()
    for s in res.slices:
        if s["pid"] == "Idle":
            continue
        end = s["end"] if upto is None else min(s["end"], upto)
        if end <= s["start"]:
            continue
        fig.add_trace(
            go.Bar(
                x=[end - s["start"]],
                base=[s["start"]],
                y=["CPU"],
                orientation="h",
                name=s["pid"],
                legendgroup=s["pid"],
                showlegend=s["pid"] not in shown,
                marker=dict(color=cmap[s["pid"]], line=dict(color="#070b14", width=2.5)),
                text=f"<b>{s['pid']}</b>",
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color="#06101c", size=15, family="JetBrains Mono"),
                hovertemplate=f"<b>{s['pid']}</b><br>{s['start']} → {s['end']} ms<extra></extra>",
            )
        )
        shown.add(s["pid"])
    ticks = sorted({s["start"] for s in res.slices} | {res.slices[-1]["end"]})
    fig.update_layout(
        barmode="overlay",
        height=height,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", family="Space Grotesk"),
        xaxis=dict(
            title="Time (ms)",
            tickmode="array",
            tickvals=ticks,
            range=[0, res.slices[-1]["end"] + 0.3],
            gridcolor="rgba(148,163,184,.12)",
            zeroline=False,
        ),
        yaxis=dict(showticklabels=False, fixedrange=True),
        legend=dict(orientation="h", y=1.18, x=0),
        bargap=0.25,
    )
    if upto is not None:
        fig.add_vline(x=upto, line=dict(color="#f472b6", width=2, dash="dot"))
    return fig


def kpi(label, value, sub="", accent=False):
    cls = "kpi accent" if accent else "kpi"
    return f'<div class="{cls}"><div class="l">{label}</div><div class="v">{value}</div><div class="s">{sub}</div></div>'


def _shade(rgb):
    """Return a column styler that shades cells by value (no matplotlib needed)."""

    def f(col):
        hi = max(col.max(), 1)
        return [f"background-color: rgba({rgb},{0.10 + 0.50 * v / hi:.2f}); color: #f1f5f9" for v in col]

    return f


def style_table(df: pd.DataFrame):
    cols = ["Completion", "Turnaround", "Waiting", "Response"]
    return (
        df.style.apply(_shade("34,211,238"), subset=["Waiting"])
        .apply(_shade("167,139,250"), subset=["Turnaround"])
        .format({c: "{:d}" for c in cols})
    )


def validate(df: pd.DataFrame) -> str | None:
    if df.empty:
        return "Add at least one process."
    if df[["Process", "Arrival", "Burst"]].isnull().any().any():
        return "Process, Arrival and Burst cannot be empty."
    if df["Process"].duplicated().any():
        return "Process IDs must be unique."
    if (df["Burst"] <= 0).any():
        return "Burst time must be at least 1 ms."
    if (df["Arrival"] < 0).any():
        return "Arrival time cannot be negative."
    return None


# ───────────────────────────── sidebar ─────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Simulation controls")
    q1 = st.number_input("Time quantum A (ms)", 1, 20, 2, help="Task baseline: 2 ms")
    q2 = st.number_input("Time quantum B (ms)", 1, 20, 3, help="Task comparison: 3 ms")
    st.caption("Context-switch overhead is **ignored** (0 ms), as specified.")
    st.markdown("---")
    st.markdown("### 🎯 Decision weights")
    st.caption("How much should each factor matter when picking the best quantum?")
    w_wait = st.slider("Waiting time", 0, 10, 5)
    w_fair = st.slider("Fair CPU access (response time)", 0, 10, 4)
    w_cs = st.slider("Context switches", 0, 10, 3)
    st.markdown("---")
    if st.button("↺ Reset workload to assignment data", width="stretch"):
        st.session_state.pop("workload", None)
        st.rerun()
    st.caption("Built with Python · Streamlit · Plotly")

# ───────────────────────────── hero ─────────────────────────────
st.markdown(
    """
<div class="hero">
  <div class="eyebrow">Practical Activity 1 · Operating Systems</div>
  <h1>Round Robin Scheduling Lab</h1>
  <p>A smart municipal control centre runs water, waste, traffic and energy services on one processor.
  Simulate Round Robin scheduling without context-switch overhead, view the Gantt chart, per-process metrics,
  and compare time quanta to find the fairest, most efficient setting.</p>
  <span class="chip" style="background:#26bde2">SDG 6 · Clean Water &amp; Sanitation</span>
  <span class="chip" style="background:#fd9d24">SDG 11 · Sustainable Cities</span>
  <span class="chip" style="background:#bf8b2e">SDG 12 · Responsible Consumption</span>
</div>
""",
    unsafe_allow_html=True,
)

# ───────────────────────────── workload editor ─────────────────────────────
st.markdown('<div class="sect">Workload · process table</div>', unsafe_allow_html=True)
if "workload" not in st.session_state:
    st.session_state["workload"] = DEFAULT_DATA.copy()

edited = st.data_editor(
    st.session_state["workload"],
    num_rows="dynamic",
    width="stretch",
    hide_index=True,
    column_config={
        "Process": st.column_config.TextColumn("Process", required=True),
        "Task": st.column_config.TextColumn("Sustainability-related task"),
        "Arrival": st.column_config.NumberColumn("Arrival time (ms)", min_value=0, step=1, format="%d", required=True),
        "Burst": st.column_config.NumberColumn("Burst time (ms)", min_value=1, step=1, format="%d", required=True),
    },
    key="editor",
)
edited = edited.copy()
edited["Task"] = edited["Task"].fillna("Custom task")

err = validate(edited)
if err:
    st.error(err)
    st.stop()
edited["Arrival"] = edited["Arrival"].astype(int)
edited["Burst"] = edited["Burst"].astype(int)

# ───────────────────────────── run simulations ─────────────────────────────
A = round_robin(edited, int(q1))
B = round_robin(edited, int(q2))
cmap = color_map(edited["Process"].tolist())

tab_run, tab_cmp, tab_dec, tab_theory = st.tabs(
    [f"▶ Simulation (Q = {q1} ms)", "⚖ Comparison", "🏁 Best quantum", "📘 How it works"]
)


def render_run(res: Result, key: str):
    # KPIs
    c = st.columns(5)
    c[0].markdown(kpi("Avg turnaround", f"{res.avg_tat:.2f}", "ms", True), unsafe_allow_html=True)
    c[1].markdown(kpi("Avg waiting", f"{res.avg_wt:.2f}", "ms", True), unsafe_allow_html=True)
    c[2].markdown(kpi("Avg response", f"{res.avg_rt:.2f}", "ms"), unsafe_allow_html=True)
    c[3].markdown(kpi("Context switches", res.switches, "CPU hand-overs", True), unsafe_allow_html=True)
    c[4].markdown(kpi("Total time", f"{res.slices[-1]['end']}", f"ms · util {res.cpu_util:.0f}%"), unsafe_allow_html=True)

    st.markdown('<div class="sect">Gantt chart · execution sequence</div>', unsafe_allow_html=True)
    st.plotly_chart(gantt(res, cmap), width="stretch", key=f"g_{key}")

    seq = " → ".join(f"{s['pid']}({s['start']}-{s['end']})" for s in res.slices if s["pid"] != "Idle")
    st.code(seq, language=None)

    st.markdown('<div class="sect">Per-process results</div>', unsafe_allow_html=True)
    st.dataframe(style_table(res.table), width="stretch", hide_index=True)
    st.download_button(
        "⬇ Download results (CSV)",
        res.table.to_csv(index=False).encode(),
        file_name=f"round_robin_q{res.quantum}.csv",
        mime="text/csv",
        key=f"dl_{key}",
    )

    # replay
    st.markdown('<div class="sect">Time-travel replay · ready queue</div>', unsafe_allow_html=True)
    end_t = res.slices[-1]["end"]
    t = st.slider("Scrub through time (ms)", 0.0, float(end_t), float(end_t), 1.0, key=f"t_{key}")
    st.plotly_chart(gantt(res, cmap, upto=t, height=250), width="stretch", key=f"gr_{key}")

    running, rem, last_time = None, {}, {}
    for _, r in edited.iterrows():
        rem[r["Process"]] = int(r["Burst"])
        last_time[r["Process"]] = (int(r["Arrival"]), 0)
    for s in res.slices:
        if s["pid"] == "Idle" or s["start"] >= t:
            continue
        done = min(s["end"], t) - s["start"]
        rem[s["pid"]] -= done
        if s["end"] <= t:
            last_time[s["pid"]] = (s["end"], 1)
        if s["start"] <= t < s["end"]:
            running = s["pid"]
    ready = [
        p
        for p in rem
        if rem[p] > 0 and p != running and int(edited.loc[edited["Process"] == p, "Arrival"].iloc[0]) <= t
    ]
    ready.sort(key=lambda p: last_time[p])
    done_list = [p for p in rem if rem[p] <= 0]

    cc = st.columns([1, 3, 1.4])
    cc[0].markdown("**CPU now**")
    cc[0].markdown(
        f'<div class="running">{running or "idle / finished"}</div>', unsafe_allow_html=True
    )
    cc[1].markdown("**Ready queue** (front → back)")
    cc[1].markdown(
        '<div class="qbox">'
        + (
            '<span class="qarrow">→</span>'.join(
                f'<span class="qitem" style="background:{cmap[p]}">{p} · {rem[p]}ms left</span>' for p in ready
            )
            or '<span style="color:#64748b">empty</span>'
        )
        + "</div>",
        unsafe_allow_html=True,
    )
    cc[2].markdown("**Completed**")
    cc[2].markdown(", ".join(done_list) if done_list else "—")


with tab_run:
    render_run(A, "A")

# ───────────────────────────── comparison ─────────────────────────────
with tab_cmp:
    st.markdown(f'<div class="sect">Gantt · Q = {q1} ms vs Q = {q2} ms</div>', unsafe_allow_html=True)
    for i, res in enumerate((A, B)):
        st.markdown(f"**Time quantum = {res.quantum} ms**")
        st.plotly_chart(gantt(res, cmap, height=210), width="stretch", key=f"cg_{i}")

    st.markdown('<div class="sect">Tool-generated comparison table</div>', unsafe_allow_html=True)

    def delta(a, b, lower_better=True):
        d = b - a
        if abs(d) < 1e-9:
            return "—"
        better = (d < 0) == lower_better
        return f"{'▲' if d > 0 else '▼'} {abs(d):.2f} {'✅' if better else '⚠️'}"

    comp = pd.DataFrame(
        {
            "Metric": [
                "Average turnaround time (ms)",
                "Average waiting time (ms)",
                "Average response time (ms)",
                "Average completion time (ms)",
                "Total context switches",
                "Total schedule length (ms)",
                "CPU utilisation (%)",
            ],
            f"Q = {A.quantum} ms": [A.avg_tat, A.avg_wt, A.avg_rt, A.avg_ct, A.switches, A.slices[-1]["end"], A.cpu_util],
            f"Q = {B.quantum} ms": [B.avg_tat, B.avg_wt, B.avg_rt, B.avg_ct, B.switches, B.slices[-1]["end"], B.cpu_util],
        }
    )
    comp["Change (B vs A)"] = [
        delta(A.avg_tat, B.avg_tat),
        delta(A.avg_wt, B.avg_wt),
        delta(A.avg_rt, B.avg_rt),
        delta(A.avg_ct, B.avg_ct),
        delta(A.switches, B.switches),
        delta(A.slices[-1]["end"], B.slices[-1]["end"]),
        delta(A.cpu_util, B.cpu_util, lower_better=False),
    ]
    st.dataframe(
        comp.style.format({f"Q = {A.quantum} ms": "{:.2f}", f"Q = {B.quantum} ms": "{:.2f}"}),
        width="stretch",
        hide_index=True,
    )
    st.download_button(
        "⬇ Download comparison (CSV)", comp.to_csv(index=False).encode(), "rr_comparison.csv", "text/csv"
    )

    # bar charts
    st.markdown('<div class="sect">Visual comparison</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    metrics = ["Avg turnaround", "Avg waiting", "Avg response"]
    fig = go.Figure()
    for res, col in ((A, "#22d3ee"), (B, "#a78bfa")):
        fig.add_bar(
            name=f"Q = {res.quantum} ms",
            x=metrics,
            y=[res.avg_tat, res.avg_wt, res.avg_rt],
            marker_color=col,
            text=[f"{v:.2f}" for v in (res.avg_tat, res.avg_wt, res.avg_rt)],
            textposition="outside",
        )
    fig.update_layout(
        barmode="group",
        height=340,
        title="Average times (ms) · lower is better",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", family="Space Grotesk"),
        yaxis=dict(gridcolor="rgba(148,163,184,.12)"),
        margin=dict(t=50, b=10),
    )
    c1.plotly_chart(fig, width="stretch")

    pr = go.Figure()
    for res, col in ((A, "#22d3ee"), (B, "#a78bfa")):
        pr.add_bar(name=f"Q = {res.quantum} ms", x=res.table["Process"], y=res.table["Waiting"], marker_color=col)
    pr.update_layout(
        barmode="group",
        height=340,
        title="Waiting time per process (ms)",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", family="Space Grotesk"),
        yaxis=dict(gridcolor="rgba(148,163,184,.12)"),
        margin=dict(t=50, b=10),
    )
    c2.plotly_chart(pr, width="stretch")

    st.markdown("**Per-process detail**")
    d1, d2 = st.columns(2)
    d1.caption(f"Q = {A.quantum} ms")
    d1.dataframe(style_table(A.table), width="stretch", hide_index=True)
    d2.caption(f"Q = {B.quantum} ms")
    d2.dataframe(style_table(B.table), width="stretch", hide_index=True)

# ───────────────────────────── decision ─────────────────────────────
with tab_dec:
    st.markdown('<div class="sect">Which quantum balances fairness, waiting time and switching?</div>', unsafe_allow_html=True)

    def norm(a, b):
        lo, hi = min(a, b), max(a, b)
        return (0.5, 0.5) if hi == lo else ((hi - a) / (hi - lo), (hi - b) / (hi - lo))  # 1 = best

    wa, wb = norm(A.avg_wt, B.avg_wt)
    ra, rb = norm(A.avg_rt, B.avg_rt)
    ca, cb = norm(A.switches, B.switches)
    tw = max(1, w_wait + w_fair + w_cs)
    score_a = 100 * (w_wait * wa + w_fair * ra + w_cs * ca) / tw
    score_b = 100 * (w_wait * wb + w_fair * rb + w_cs * cb) / tw

    best, other = (A, B) if score_a >= score_b else (B, A)
    tie = abs(score_a - score_b) < 1e-9

    if tie:
        head = "Both quanta score equally under your weights"
    else:
        head = f"Recommended time quantum: {best.quantum} ms"
    reasons = []
    for label, a, b, unit in (
        ("average waiting time", best.avg_wt, other.avg_wt, "ms"),
        ("average response time (fair CPU access)", best.avg_rt, other.avg_rt, "ms"),
        ("context switches", best.switches, other.switches, ""),
    ):
        if abs(a - b) < 1e-9:
            reasons.append(f"{label.capitalize()} is the same for both ({a:.2f}{unit}).")
        elif a < b:
            reasons.append(f"Q = {best.quantum} ms gives the lower {label}: **{a:.2f}{unit}** vs {b:.2f}{unit}.")
        else:
            reasons.append(f"Q = {best.quantum} ms has a higher {label} (**{a:.2f}{unit}** vs {b:.2f}{unit}), a trade-off accepted for the other gains.")

    st.markdown(
        f'<div class="verdict"><h3>🏆 {head}</h3>'
        + "".join(f"<p>• {r}</p>" for r in reasons)
        + "<p style='margin-top:10px'>For a municipal control centre, short response times keep urgent monitoring "
        "(e.g. water quality alerts) responsive, while fewer context switches reduce scheduling churn. "
        "Adjust the weights in the sidebar to see how priorities change the verdict.</p></div>",
        unsafe_allow_html=True,
    )

    st.write("")
    g1, g2 = st.columns([1.1, 1])
    radar = go.Figure()
    cats = ["Waiting", "Fair access (response)", "Few switches", "Waiting"]
    for res, (w_, r_, c_), col in ((A, (wa, ra, ca), "#22d3ee"), (B, (wb, rb, cb), "#a78bfa")):
        radar.add_trace(
            go.Scatterpolar(
                r=[w_, r_, c_, w_],
                theta=cats,
                fill="toself",
                name=f"Q = {res.quantum} ms",
                line=dict(color=col, width=3),
                opacity=0.75,
            )
        )
    radar.update_layout(
        height=380,
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(range=[0, 1], showticklabels=False, gridcolor="rgba(148,163,184,.2)"),
            angularaxis=dict(gridcolor="rgba(148,163,184,.2)"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", family="Space Grotesk"),
        title="Balance profile (outer = better)",
        margin=dict(t=60, b=20),
    )
    g1.plotly_chart(radar, width="stretch")

    with g2:
        st.markdown("**Weighted balance score** (0–100)")
        st.markdown(kpi(f"Q = {A.quantum} ms", f"{score_a:.0f}", "higher is better", score_a >= score_b), unsafe_allow_html=True)
        st.write("")
        st.markdown(kpi(f"Q = {B.quantum} ms", f"{score_b:.0f}", "higher is better", score_b > score_a), unsafe_allow_html=True)
        st.caption("Each metric is min-max normalised between the two runs, then combined using the sidebar weights.")

    st.markdown('<div class="sect">Sweep every quantum (1 → max burst)</div>', unsafe_allow_html=True)
    sweep = [round_robin(edited, q) for q in range(1, int(edited["Burst"].max()) + 1)]
    sw = pd.DataFrame(
        {
            "Quantum": [r.quantum for r in sweep],
            "Avg waiting": [r.avg_wt for r in sweep],
            "Avg response": [r.avg_rt for r in sweep],
            "Context switches": [r.switches for r in sweep],
        }
    )
    sf = go.Figure()
    sf.add_scatter(x=sw["Quantum"], y=sw["Avg waiting"], name="Avg waiting", mode="lines+markers", line=dict(color="#22d3ee", width=3))
    sf.add_scatter(x=sw["Quantum"], y=sw["Avg response"], name="Avg response", mode="lines+markers", line=dict(color="#fbbf24", width=3))
    sf.add_scatter(x=sw["Quantum"], y=sw["Context switches"], name="Context switches", mode="lines+markers", line=dict(color="#f472b6", width=3), yaxis="y2")
    sf.update_layout(
        height=360,
        xaxis=dict(title="Time quantum (ms)", dtick=1, gridcolor="rgba(148,163,184,.12)"),
        yaxis=dict(title="ms", gridcolor="rgba(148,163,184,.12)"),
        yaxis2=dict(title="switches", overlaying="y", side="right", showgrid=False),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", family="Space Grotesk"),
        legend=dict(orientation="h", y=1.15),
        margin=dict(t=30, b=10),
    )
    st.plotly_chart(sf, width="stretch")
    st.caption("Small quanta → fast response but many switches. Large quanta → few switches but Round Robin drifts toward FCFS.")

# ───────────────────────────── theory ─────────────────────────────
with tab_theory:
    st.markdown('<div class="sect">Algorithm & formulas</div>', unsafe_allow_html=True)
    st.markdown(
        """
**Round Robin** gives every ready process the CPU for at most one *time quantum*, then pre-empts it and moves it to the back of the ready queue.

| Metric | Formula |
|---|---|
| Completion time (CT) | Clock time when the process finishes |
| Turnaround time (TAT) | `CT − Arrival` |
| Waiting time (WT) | `TAT − Burst` |
| Response time (RT) | `First CPU start − Arrival` |
| Context switch | CPU hand-over between two *different* processes |

**Conventions used in this simulator**
1. Context-switch overhead is **0 ms** (ignored, as the activity states).
2. If a process arrives at the same moment another is pre-empted, the **new arrival is queued first**.
3. The first dispatch at t = 0 and a process continuing on its own are **not** counted as switches.
4. If the CPU has nothing to run, an *idle* gap is shown until the next arrival.
"""
    )
    st.markdown('<div class="sect">Task → SDG mapping</div>', unsafe_allow_html=True)
    st.dataframe(
        pd.DataFrame(
            [{"Process": r.Process, "Task": r.Task, "SDG": SDG_TAG.get(r.Task, ("—", ""))[0]} for r in DEFAULT_DATA.itertuples()]
        ),
        hide_index=True,
        width="stretch",
    )
