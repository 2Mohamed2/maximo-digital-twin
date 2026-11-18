"""Checks for the TK-2701 twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings, healthy and faulted, from the stand-in tank and from the live Plant; every alert rule equals the Python conditions.
2. faults: each failure mode, injected at full severity, raises exactly its own conditions; a healthy tank raises none.
3. plant: in the live Plant, each failure mode's rules appear within 240 steps; a healthy Plant raises none over two cycles.
4. writes ../blog/_twin/example_tank-twin.json (one healthy reading and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Plant, Tank

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]


def readings():
    v, rows = Tank(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            v.clear()
            if fm:
                v.set_fault(fm, sev)
            rows += [v.measure() for _ in range(25)]
    p = Plant(TW, seed=9)
    for fm in [None] + FMS:
        p.clear_faults(1)
        if fm:
            p.set_fault(fm, 1.0, 30)
        for i in range(240):
            tr = p.step(1.0)
            if i % 4 == 0:
                rows.append(p.measure(tr))
    return rows


def parity(rows):
    df = pd.DataFrame([{k.upper(): x for k, x in r.items()} for r in rows])
    bad = 0
    for name, expr in tc.monitor_expressions(TW):
        got = np.asarray(eval(expr, {"df": df, "np": np}), dtype=float)
        want = np.array([tc.evaluate(TW, r)[name.lower()] for r in rows], dtype=float)
        n = int((~np.isclose(got, want, rtol=1e-9, atol=1e-9)).sum())
        if n:
            print(f"  MISMATCH {name}: {n}")
        bad += n
    for name, expr, sev, fm in tc.alert_rules(TW):
        got = np.asarray(eval(expr, {"df": df, "np": np}), dtype=bool)
        want = np.array([any(c["name"] == name for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]) for r in rows])
        n = int((got != want).sum())
        if n:
            print(f"  MISMATCH rule {name}: {n}")
        bad += n
    print(f"parity: {len(rows)} readings, {len(tc.monitor_expressions(TW))} expressions, {len(tc.alert_rules(TW))} rules, {bad} mismatches")
    return bad


EXPECT = {
    "overfill": {"TANK_LEVEL_HH"},
    "gauge_drift": {"TANK_GAUGE_MISMATCH"},
    "bottom_leak": {"TANK_STATIC_LOSS"},
    "meter_error": {"TANK_METER_IMBALANCE"},
    "roof_tilt": {"TANK_ROOF_TILT"},
    "roof_drain_blocked": {"TANK_ROOF_LOW"},
    "rim_seal_damage": {"TANK_RIM_GAS"},
    "bottom_corrosion": {"TANK_BOTTOM_RATE", "TANK_BOTTOM_MRT"},
}


def faults():
    bad = 0
    v = Tank(TW, seed=3)
    for fm in [None] + FMS:
        for rep in range(20):
            v.clear()
            if fm:
                v.set_fault(fm, 1.0)
            r = v.measure()
            got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            want = EXPECT.get(fm, set())
            if got != want:
                break
        ok = got == want
        bad += not ok
        print(f"  {fm or 'healthy':20s} {'ok ' if ok else 'BAD'} {sorted(got)}")
    return bad


def plant():
    bad = 0
    p = Plant(TW, seed=5)
    hits = {}
    for i in range(500):
        tr = p.step(1.0)
        for c in tc.conditions(TW, p.measure(tr), tc.evaluate(TW, p.measure(tr)))[0]:
            hits[c["name"]] = hits.get(c["name"], 0) + 1
    print(f"plant healthy: 500 steps (about {500 * p.scale / 3600:.0f} plant hours), conditions: {hits or 'none'}")
    bad += bool(hits)
    for fm in FMS:
        p = Plant(TW, seed=11)
        for _ in range(100):
            p.step(1.0)
        p.set_fault(fm, 1.0, 30)
        want, seen, first = EXPECT[fm], set(), None
        for i in range(240):
            r = p.measure(p.step(1.0))
            names = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            seen |= names & want
            if first is None and seen == want:
                first = i + 1
        ok = seen == want
        bad += not ok
        print(f"  plant {fm:20s} {'ok ' if ok else 'BAD'} all of {sorted(want)} within {first} steps" if ok else f"  plant {fm:20s} BAD saw {sorted(seen)}")
    return bad


def example():
    v = Tank(TW, seed=11)
    r = v.measure()
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_tank-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()}}, indent=1), encoding="utf-8")
    print("example:", out)


if __name__ == "__main__":
    b = parity(readings())
    print("faults:")
    b += faults()
    b += plant()
    example()
    sys.exit(1 if b else 0)
