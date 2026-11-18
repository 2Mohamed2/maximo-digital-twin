"""Checks for the TM-5401 traction motor twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings from every phase of the run, healthy and faulted; every alert rule equals the Python conditions.
2. faults: each failure mode, injected at full severity, raises exactly its own conditions on the climb; a healthy motor
   raises none in any phase.
3. plant: the live Plant (used by the twin pages) shows each fault's rules within 240 one-second steps, and none when healthy.
4. writes ../blog/_twin/example_traction-twin.json (one healthy reading on the climb and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import PHASES, Motor, Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]


def readings():
    m, rows = Motor(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            m.clear()
            if fm:
                m.set_fault(fm, sev)
            for ph in PHASES:
                rows += [m.measure(ph[0]) for _ in range(4)]
    p = Plant(TW, seed=5)
    for i in range(600):                       # plant readings through several runs with ramping faults
        if i == 150:
            p.set_fault("inverter_cooling", 1.0, 60)
        if i == 350:
            p.clear_faults(30)
            p.set_fault("low_adhesion", 1.0, 60)
        rows.append(p.measure(p.step(1.0)))
    off = Motor(TW, seed=9)                    # a wrong wheel-diameter parameter: TM_CREEP_OFFSET only (no failure mode)
    for ph in PHASES:
        r = off.measure(ph[0])
        r["creep_coast_pct"] = 2.4
        rows.append(r)
    return rows


def parity(rows):
    df = pd.DataFrame([{k.upper(): x for k, x in r.items()} for r in rows])
    bad = 0
    for name, expr in tc.monitor_expressions(TW):
        got = np.asarray(eval(expr, {"df": df, "np": np}), dtype=float)
        want = np.array([tc.evaluate(TW, r)[name.lower()] for r in rows], dtype=float)
        nb = int((~np.isclose(got, want, rtol=1e-9, atol=1e-9)).sum())
        bad += nb
        if nb:
            print(f"MISMATCH {name}: {nb}")
    for name, expr, sev, fm in tc.alert_rules(TW):
        got = np.asarray(eval(expr, {"df": df, "np": np}), dtype=bool)
        want = np.array([any(c["name"] == name for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]) for r in rows])
        nb = int((got != want).sum())
        bad += nb
        if nb:
            print(f"MISMATCH rule {name}: {nb}")
    print(f"parity: {len(rows)} readings, {len(tc.monitor_expressions(TW))} expressions, {len(tc.alert_rules(TW))} rules, {bad} mismatches")
    return bad


EXPECT = {fm: set(TW["failure_modes"][fm]["rules"]) for fm in FMS}


def faults():
    bad = 0
    m = Motor(TW, seed=3)
    for fm in [None] + FMS:
        m.clear()
        if fm:
            m.set_fault(fm, 1.0)
        seen = set()
        phases = [p[0] for p in PHASES] if fm is None else ["climbing"]
        for ph in phases:
            for _ in range(20):                # every reading must give exactly the expected set
                r = m.measure(ph)
                got = {x["name"] for x in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
                if got != EXPECT.get(fm, set()):
                    seen = got | {"@" + ph}
                    break
        ok = not seen
        bad += not ok
        print(f"  {fm or 'healthy':24s} {'ok ' if ok else 'BAD'} {sorted(EXPECT.get(fm, set())) if ok else sorted(seen)}")
    return bad


def plant():
    bad = 0
    for fm in [None] + FMS:
        p = Plant(TW, seed=11)
        for _ in range(300):
            p.step(2.0)
        if fm:
            p.set_fault(fm, 1.0, TW["failure_modes"][fm]["default_ramp_min"] * 60)
        seen, first = set(), {}
        for i in range(240):
            m = p.measure(p.step(1.0))
            for x in tc.conditions(TW, m, tc.evaluate(TW, m))[0]:
                seen.add(x["name"])
                first.setdefault(x["name"], i + 1)
        want = EXPECT.get(fm, set())
        ok = want <= seen and not (seen - want)
        bad += not ok
        print(f"  plant {fm or 'healthy':24s} {'ok ' if ok else 'BAD'} " + ", ".join(f"{k} @{v}s" for k, v in sorted(first.items(), key=lambda x: x[1])))
    return bad


def example():
    m = Motor(TW, seed=11)
    r = m.measure("climbing")
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_traction-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()}}, indent=1), encoding="utf-8")
    print("example:", out)


if __name__ == "__main__":
    b = parity(readings())
    print("faults:")
    b += faults()
    print("plant:")
    b += plant()
    example()
    sys.exit(1 if b else 0)
