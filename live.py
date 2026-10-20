"""
live.py  -  The live dashboard that updates every second.

How it works
------------
1. Python runs the chosen algorithm once (scheduler.run_algo) and converts the result into a
   second-by-second list called `run`:   run[0] = process running during second 0-1,
   run[1] = process running during second 1-2, ... (None = CPU idle).
2. That list, plus the process table, is sent to the browser as JSON.
3. A small JavaScript program (below) moves a timer `t` forward by 1 every second and redraws
   the screen from `run` - so remaining time, waiting time, completion time and the Gantt strip all
   change at the exact moment they happen.
"""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from scheduler import Result
from theme import PALETTE

# Everything between r""" and """ is a normal web page (HTML + CSS + JavaScript).
TEMPLATE = r"""<!doctype html><html><head><meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');
:root{--card:#162038;--line:#25324f;--txt:#e2e8f0;--mut:#94a3b8;--run:#facc15;--ready:#60a5fa;--done:#22c55e}
*{box-sizing:border-box}
body{margin:0;padding:2px;font-family:'Inter',system-ui,sans-serif;color:var(--txt);background:transparent}
.grid{display:grid;grid-template-columns:minmax(280px,.8fr) 1.8fr;gap:16px;align-items:start}
.col{display:flex;flex-direction:column;gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px 24px}
.row{display:flex;align-items:baseline;gap:12px;margin:10px 0;flex-wrap:wrap}
.k{font-weight:600;color:#cbd5e1;font-size:15px}
.big{font-size:24px;font-weight:700}
.cpu{font-family:'JetBrains Mono',monospace;font-size:30px;font-weight:700;color:#22e55e}
.cpu.idle{color:#94a3b8}.cpu.done{color:#38bdf8}
.timer{font-family:'JetBrains Mono',monospace;font-size:32px;font-weight:700}
.avg b{font-family:'JetBrains Mono',monospace;font-size:22px;margin-left:6px}
table{width:100%;border-collapse:collapse}
th{font-size:14px;color:#fff;font-weight:700;padding:6px 8px 14px;text-align:center}
td{padding:10px 8px;text-align:center;font-size:15px;border-top:1px solid rgba(255,255,255,.06)}
td.pid{font-weight:700}
.num{font-family:'JetBrains Mono',monospace}
.bar{position:relative;height:28px;border-radius:8px;background:#26334f;overflow:hidden;min-width:150px}
.fill{position:absolute;left:0;top:0;bottom:0;width:0;border-radius:8px;background:var(--ready);transition:width .35s ease,background .25s}
.fill.run{background:var(--run)}.fill.done{background:var(--done)}.fill.wait{background:rgba(96,165,250,.55)}
.state{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#0b1220;letter-spacing:.04em}
.state.dim{color:#9fb0c8}
tr.runrow{background:rgba(250,204,21,.07)}
.controls{display:flex;gap:12px;margin-top:16px}
button{font-family:inherit;font-size:14px;font-weight:600;color:#fff;background:#243352;border:1px solid #334566;border-radius:10px;padding:9px 18px;cursor:pointer}
button:hover{border-color:#38bdf8;color:#bae6fd}
.sec{font-weight:700;font-size:15px;margin:0 0 12px;color:#cbd5e1}
.gantt{display:flex;overflow-x:auto}
.cell{flex:1 0 26px;min-width:26px;height:42px;display:flex;align-items:center;justify-content:center;font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:700;color:#0b1220;background:#1d2a45;border-top:1px solid #2a3a5c;border-bottom:1px solid #2a3a5c}
.cell.cut{border-left:2px solid #0f172a}
.cell.now{outline:2px solid #fff;outline-offset:-2px}
.ticks{display:flex}
.tick{flex:1 0 26px;min-width:26px;font-size:10.5px;color:var(--mut);padding-top:4px;font-family:'JetBrains Mono',monospace}
@media(max-width:820px){.grid{grid-template-columns:1fr}}
</style></head><body>

<!-- ============ screen layout ============ -->
<div class="grid">
  <div class="col">
    <div class="card">
      <div class="row"><span class="k">Algorithm:</span><span class="big" id="algo"></span></div>
      <div class="row"><span class="k">CPU:</span><span class="cpu" id="cpu">—</span></div>
      <div class="row"><span class="k">Timer:</span><span class="timer" id="timer">0 s</span></div>
    </div>
    <div class="card avg">
      <div class="row"><span class="k">Average Waiting Time:</span><b id="awt">—</b></div>
      <div class="row"><span class="k">Average Turn-around Time:</span><b id="atat">—</b></div>
      <div class="row"><span class="k">Context Switches:</span><b id="cs">0</b></div>
    </div>
  </div>
  <div class="card">
    <table><thead><tr id="head"></tr></thead><tbody id="body"></tbody></table>
    <div class="controls">
      <button id="bReset">⏮ Restart</button>
      <button id="bPlay">⏸ Pause</button>
    </div>
  </div>
</div>
<div class="card" style="margin-top:16px">
  <div class="sec">Gantt chart (one block per second)</div>
  <div class="gantt" id="gantt"></div><div class="ticks" id="ticks"></div>
</div>

<script>
/* ============ 1. data sent from Python ============ */
const D = __DATA__;                       // {algo, procs, run, cuts, ...}
const P = D.procs, run = D.run, N = run.length;      // N = total seconds of the schedule
const $ = id => document.getElementById(id);
const col = {}; P.forEach((p,i) => col[p.pid] = D.palette[i % D.palette.length]);

/* completion time of each process = (index of the last second it ran) + 1 */
const ct = {}; run.forEach((pid,i) => { if (pid) ct[pid] = i + 1; });
const cuts = new Set(D.cuts);             // seconds where a new slice starts (drawn as a thin divider)

let t = 0, playing = false, timer = null; // t = the simulated clock, in seconds

/* ============ 2. build the table and the Gantt strip once ============ */
$('algo').textContent = D.algo + (D.rr ? ' (Q = ' + D.quantum + ' s)' : '');
const heads = ['PID','AT','BT'].concat(D.showPri ? ['Priority'] : []).concat(['Status Bar','Remaining BT','WT','CT']);
$('head').innerHTML = heads.map(h => '<th>' + h + '</th>').join('');
$('body').innerHTML = P.map((p,i) =>
  '<tr id="r'+i+'"><td class="pid" style="color:'+col[p.pid]+'">'+p.pid+'</td>'+
  '<td class="num">'+p.at+' s</td><td class="num">'+p.bt+' s</td>'+
  (D.showPri ? '<td class="num">'+p.pr+'</td>' : '')+
  '<td><div class="bar"><div class="fill" id="f'+i+'"></div><div class="state dim" id="s'+i+'"></div></div></td>'+
  '<td class="num" id="rem'+i+'"></td><td class="num" id="wt'+i+'"></td><td class="num" id="ct'+i+'"></td></tr>').join('');

let g = '', tk = '';
const step = N <= 30 ? 1 : (N <= 80 ? 5 : 10);
for (let i = 0; i < N; i++) {
  g  += '<div class="cell' + (cuts.has(i) ? ' cut' : '') + '" id="c' + i + '"></div>';
  tk += '<div class="tick">' + (i % step === 0 ? i : '') + '</div>';
}
$('gantt').innerHTML = g; $('ticks').innerHTML = tk;

/* ============ 3. redraw everything for the current time t ============ */
const executed = (pid, tt) => { let c = 0; for (let i = 0; i < tt; i++) if (run[i] === pid) c++; return c; };
const fmt = x => Number.isInteger(x) ? String(x) : x.toFixed(2);

function render() {
  const justRan = t > 0 ? run[t-1] : null;           // process that used the CPU during the last second

  /* CPU label and timer */
  const cpu = $('cpu');
  if (t === 0)        { cpu.textContent = '—';    cpu.className = 'cpu idle'; }
  else if (t >= N)    { cpu.textContent = 'DONE'; cpu.className = 'cpu done'; }
  else if (justRan)   { cpu.textContent = justRan; cpu.className = 'cpu'; }
  else                { cpu.textContent = 'IDLE'; cpu.className = 'cpu idle'; }
  $('timer').textContent = t + ' s';

  /* one table row per process */
  let sumW = 0, sumT = 0, finished = 0;
  P.forEach((p, i) => {
    const ex = executed(p.pid, t);                    // CPU time received so far
    const rem = p.bt - ex;                            // remaining burst time
    const done = ex >= p.bt, arrived = t >= p.at;
    const running = !done && justRan === p.pid;

    const fill = $('f'+i), state = $('s'+i);
    fill.style.width = (ex / p.bt * 100) + '%';       // status bar = ex / burst
    fill.className = 'fill' + (done ? ' done' : running ? ' run' : (arrived && ex > 0 ? ' wait' : ''));
    if (!arrived)      { state.textContent = 'NOT ARRIVED'; state.className = 'state dim'; }
    else if (done)     { state.textContent = 'DONE';        state.className = 'state'; }
    else if (running)  { state.textContent = 'RUNNING';     state.className = 'state'; }
    else               { state.textContent = 'READY';       state.className = 'state dim'; }
    $('r'+i).className = running ? 'runrow' : '';

    $('rem'+i).textContent = rem + ' s';
    /* waiting time so far = time since arrival minus time spent running; frozen once finished */
    let wt = '-', ctText = '-';
    if (arrived) wt = done ? (ct[p.pid] - p.at - p.bt) : ((t - p.at) - ex);
    if (done) { ctText = ct[p.pid] + ' s'; sumW += wt; sumT += ct[p.pid] - p.at; finished++; }
    $('wt'+i).textContent = wt === '-' ? '-' : wt + ' s';
    $('ct'+i).textContent = ctText;
  });

  /* averages (over processes that have finished) and context switches so far */
  $('awt').textContent  = finished ? fmt(sumW / finished) + ' s' : '—';
  $('atat').textContent = finished ? fmt(sumT / finished) + ' s' : '—';
  let cs = 0, prev = null;
  for (let i = 0; i < t; i++) if (run[i]) { if (prev && prev !== run[i]) cs++; prev = run[i]; }
  $('cs').textContent = cs;

  /* Gantt strip: colour the seconds that have already happened */
  for (let i = 0; i < N; i++) {
    const c = $('c'+i);
    if (i < t) {
      c.style.background = run[i] ? col[run[i]] : '#1e293b';
      c.textContent = (i === 0 || cuts.has(i) || run[i] !== run[i-1]) ? (run[i] || '') : '';
    } else { c.style.background = ''; c.textContent = ''; }
    c.classList.toggle('now', i === t - 1);
  }
}

/* ============ 4. the clock: +1 second every 1000 ms ============ */
function setPlay(on) {
  playing = on; clearInterval(timer);
  if (on) {
    if (t >= N) t = 0;
    timer = setInterval(() => { if (t < N) { t++; render(); } if (t >= N) setPlay(false); }, 1000);
  }
  $('bPlay').textContent = playing ? '⏸ Pause' : '▶ Play';
  render();
}
$('bPlay').onclick  = () => setPlay(!playing);
$('bReset').onclick = () => { t = 0; setPlay(true); };
render(); setTimeout(() => setPlay(true), 400);       // start automatically
</script></body></html>"""


def live_dashboard(df: pd.DataFrame, res: Result, algo: str, quantum: int, show_priority: bool):
    """Prepare the data and embed the dashboard in the Streamlit page."""
    # slices -> one entry per second
    run, cuts = [], []
    for s in res.slices:
        cuts.append(s["start"])
        run += [None if s["pid"] == "Idle" else s["pid"]] * (s["end"] - s["start"])

    # process list in natural order P1, P2, ... P10
    ordered = df.sort_values("Process", key=lambda c: c.str.extract(r"(\d+)")[0].astype(int))
    procs = [{"pid": r.Process, "at": int(r.Arrival), "bt": int(r.Burst), "pr": int(r.Priority)}
             for r in ordered.itertuples()]

    data = {"algo": algo, "rr": algo == "Round Robin", "quantum": quantum, "procs": procs,
            "run": run, "cuts": cuts, "palette": PALETTE, "showPri": show_priority}
    html = TEMPLATE.replace("__DATA__", json.dumps(data))
    height = 120 + 58 * len(procs) + 330
    if hasattr(st, "iframe"):                 # newer Streamlit versions
        st.iframe(html, height=height)
    else:                                     # older versions
        components.html(html, height=height, scrolling=True)
