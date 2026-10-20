"""
scheduler.py  -  The CPU scheduling algorithms (the "brain" of the project).

No Streamlit code lives here. Every algorithm takes a table of processes and returns the
execution timeline ("slices") plus the standard performance metrics.

Terms used throughout (all times in ms / s - the unit does not matter):
    Arrival    - time the process enters the system
    Burst      - total CPU time the process needs
    Completion - time the process finishes
    Turnaround = Completion - Arrival
    Waiting    = Turnaround - Burst
    Response   = (time it first gets the CPU) - Arrival
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import pandas as pd

# The six algorithms offered by the reference site, in the same order.
ALGOS = [
    "FCFS",
    "Priority Preemptive",
    "Priority Non-Preemptive",
    "Round Robin",
    "Shortest Job First Preemptive",
    "Shortest Job First Non-Preemptive",
]

# Sample data from Practical Activity 1 (municipal control centre, SDG 6 / 11 / 12).
# "Priority" is only used by the two priority algorithms (1 = highest priority).
ACTIVITY_DATA = pd.DataFrame(
    {
        "Process": ["P1", "P2", "P3", "P4"],
        "Task": ["Water-quality monitoring", "Waste-collection scheduling",
                 "Traffic-pollution analysis", "Public energy-use monitoring"],
        "Arrival": [0, 1, 2, 3],
        "Burst": [5, 3, 4, 2],
        "Priority": [2, 3, 1, 4],
    }
)


# ───────────────────────────── result container ─────────────────────────────
@dataclass
class Result:
    """Everything one simulation run produces."""
    algo: str
    quantum: int | None   # only meaningful for Round Robin
    slices: list          # [{"pid": "P1", "start": 0, "end": 2}, ...]  (the Gantt chart data)
    table: pd.DataFrame   # one row per process with all metrics
    avg_tat: float        # average turnaround time
    avg_wt: float         # average waiting time
    avg_rt: float         # average response time
    switches: int         # total number of context switches
    end: int              # time at which the last process finishes


def finalize(df: pd.DataFrame, slices: list, algo: str, quantum=None) -> Result:
    """Turn a list of slices into the per-process metrics table and the averages."""
    first_start, completion = {}, {}
    for s in slices:
        if s["pid"] == "Idle":
            continue
        first_start.setdefault(s["pid"], s["start"])   # first time the process got the CPU
        completion[s["pid"]] = s["end"]                # last slice end = completion time

    rows = []
    for r in df.itertuples():
        ct = completion[r.Process]
        tat = ct - r.Arrival
        rows.append({
            "Process": r.Process, "Task": r.Task, "Arrival": r.Arrival, "Burst": r.Burst,
            "Priority": r.Priority, "Completion": ct, "Turnaround": tat,
            "Waiting": tat - r.Burst, "Response": first_start[r.Process] - r.Arrival,
        })
    table = pd.DataFrame(rows)
    table = table.sort_values("Process", key=lambda c: c.str.extract(r"(\d+)")[0].astype(int)).reset_index(drop=True)

    # A context switch = the CPU is handed from one process to a DIFFERENT process.
    # The very first dispatch and a process that simply keeps running are not counted.
    real = [s for s in slices if s["pid"] != "Idle"]
    switches = sum(1 for a, b in zip(real, real[1:]) if a["pid"] != b["pid"])

    return Result(algo, quantum, slices, table, table.Turnaround.mean(), table.Waiting.mean(),
                  table.Response.mean(), switches, slices[-1]["end"])


# ───────────────────────────── non-preemptive family ─────────────────────────────
def _non_preemptive(df, key):
    """
    Once a process gets the CPU it runs to completion.
    `key` ranks the ready processes; the smallest key is chosen next.
        FCFS            -> arrival time
        SJF             -> burst time
        Priority        -> priority number
    """
    procs = df.to_dict("records")
    done, slices, t = set(), [], 0
    while len(done) < len(procs):
        ready = [p for p in procs if p["Process"] not in done and p["Arrival"] <= t]
        if not ready:                                    # CPU idle until the next arrival
            nxt = min(p["Arrival"] for p in procs if p["Process"] not in done)
            slices.append({"pid": "Idle", "start": t, "end": nxt})
            t = nxt
            continue
        p = min(ready, key=key)
        slices.append({"pid": p["Process"], "start": t, "end": t + p["Burst"]})
        t += p["Burst"]
        done.add(p["Process"])
    return slices


# ───────────────────────────── preemptive family ─────────────────────────────
def _preemptive(df, key):
    """
    The scheduler re-decides EVERY millisecond, so a newly arrived, better process can
    pre-empt the running one.
        SJF preemptive (SRTF) -> key = remaining burst time
        Priority preemptive   -> key = priority number
    Consecutive milliseconds of the same process are merged into one slice.
    """
    procs = df.to_dict("records")
    remaining = {p["Process"]: p["Burst"] for p in procs}
    slices, t, last = [], 0, None
    while any(v > 0 for v in remaining.values()):
        ready = [p for p in procs if remaining[p["Process"]] > 0 and p["Arrival"] <= t]
        if not ready:
            nxt = min(p["Arrival"] for p in procs if remaining[p["Process"]] > 0)
            slices.append({"pid": "Idle", "start": t, "end": nxt})
            t, last = nxt, None
            continue
        # tie-break: keep the current process (avoids a pointless switch), then earlier arrival
        p = min(ready, key=lambda x: (key(x, remaining), 0 if x["Process"] == last else 1, x["Arrival"]))
        pid = p["Process"]
        if slices and slices[-1]["pid"] == pid and slices[-1]["end"] == t:
            slices[-1]["end"] += 1                       # extend the current slice
        else:
            slices.append({"pid": pid, "start": t, "end": t + 1})
        remaining[pid] -= 1
        t += 1
        last = pid
    return slices


# ───────────────────────────── Round Robin ─────────────────────────────
def _round_robin(df, quantum):
    """
    Each process may run for at most `quantum` ms, then it goes to the back of the queue.
    Context-switching overhead is ignored (0 ms) as the activity states.

    Tie rule (standard textbook convention): if a process arrives at the same instant another
    one is pre-empted, the NEW arrival is queued first, the pre-empted process second.
    """
    procs = df.sort_values(["Arrival", "Process"], kind="stable").to_dict("records")
    n = len(procs)
    remaining = {p["Process"]: p["Burst"] for p in procs}
    queue, slices = deque(), []
    idx, t, finished = 0, 0, 0            # idx = next process (by arrival) not yet queued

    def admit(upto):
        """Move every process that has arrived by time `upto` into the ready queue."""
        nonlocal idx
        while idx < n and procs[idx]["Arrival"] <= upto:
            queue.append(procs[idx]["Process"])
            idx += 1

    admit(t)
    while finished < n:
        if not queue:                                     # nothing ready -> CPU idle
            nxt = procs[idx]["Arrival"]
            slices.append({"pid": "Idle", "start": t, "end": nxt})
            t = nxt
            admit(t)
            continue
        pid = queue.popleft()                             # front of the queue gets the CPU
        run = min(quantum, remaining[pid])                # full quantum, or less if it finishes
        slices.append({"pid": pid, "start": t, "end": t + run})
        t += run
        remaining[pid] -= run
        admit(t)                                          # 1) new arrivals join first ...
        if remaining[pid] > 0:
            queue.append(pid)                             # 2) ... then the pre-empted process
        else:
            finished += 1
    return slices


# ───────────────────────────── public entry point ─────────────────────────────
def run_algo(df: pd.DataFrame, algo: str, quantum: int = 2) -> Result:
    """Run any of the six algorithms on the process table and return a Result."""
    df = df.sort_values(["Arrival", "Process"], kind="stable").reset_index(drop=True)
    if algo == "FCFS":
        slices = _non_preemptive(df, lambda p: (p["Arrival"], p["Process"]))
    elif algo == "Shortest Job First Non-Preemptive":
        slices = _non_preemptive(df, lambda p: (p["Burst"], p["Arrival"], p["Process"]))
    elif algo == "Priority Non-Preemptive":
        slices = _non_preemptive(df, lambda p: (p["Priority"], p["Arrival"], p["Process"]))
    elif algo == "Shortest Job First Preemptive":
        slices = _preemptive(df, lambda p, rem: rem[p["Process"]])
    elif algo == "Priority Preemptive":
        slices = _preemptive(df, lambda p, rem: p["Priority"])
    else:
        slices = _round_robin(df, quantum)
    return finalize(df, slices, algo, quantum if algo == "Round Robin" else None)
