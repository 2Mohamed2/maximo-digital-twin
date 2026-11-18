"""Checks for the PV-3101 twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings over whole days (night, morning, clipping at noon), healthy and faulted at several severities; every alert rule
   equals the Python conditions.
2. faults: each failure mode, injected at full severity at 10:00, raises exactly its expected rules; a healthy block raises none.
3. live plant: each failure mode set on the Plant (the stand-in used by the live pages) shows its rules within 240 steps.
4. writes ../blog/_twin/example_pv-twin.json (one healthy 10:00 reading and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Block, Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]


def readings():
    rows = []
    p = Plant(TW, seed=7)
    for fm in [None] + FMS:
        p.clear_faults(1)
        for _ in range(5):
            p.step(1.0)
        if fm:
            p.set_fault(fm, 1.0, 600)
        for i in range(1600):                      # about one plant day
            tr = p.step(1.0)
            if i % 5 == 0:
                rows.append(p.measure(tr))
    b = Block(TW, seed=5)
    for fm in [None] + FMS:
        for sev in (0.25, 0.5, 0.75, 1.0):
            b.clear()
            if fm:
                b.set_fault(fm, sev)
            for h in (6.5, 8.0, 10.0, 12.0, 13.0, 15.5, 17.5, 22.0):
                rows.append(b.measure(h))
    return rows


def parity(rows):
    df = pd.DataFrame([{k.upper(): x for k, x in r.items()} for r in rows])
    bad = 0
    for name, expr in tc.monitor_expressions(TW):
        got = np.asarray(eval(expr, {"df": df, "np": np}), dtype=float)
        want = np.array([tc.evaluate(TW, r)[name.lower()] for r in rows], dtype=float)
        n = int((~np.isclose(got, want, rtol=1e-9, atol=1e-9)).sum())
        bad += n
        if n:
            print(f"MISMATCH {name}: {n}")
    fired = {}
    for name, expr, sev, fm in tc.alert_rules(TW):
        got = np.asarray(eval(expr, {"df": df, "np": np}), dtype=bool)
        want = np.array([any(c["name"] == name for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]) for r in rows])
        n = int((got != want).sum())
        bad += n
        fired[name] = int(got.sum())
        if n:
            print(f"MISMATCH rule {name}: {n}")
    print(f"parity: {len(rows)} readings x {len(tc.monitor_expressions(TW))} expressions + {len(tc.alert_rules(TW))} rules, {bad} mismatches")
    print("  rule fired on", ", ".join(f"{k} {v}" for k, v in fired.items()))
    return bad


EXPECT = {
    "soiling": {"PV_CLEANING_DUE"},
    "string_open": {"PV_STRING_OPEN"},
    "string_bypass": {"PV_STRING_LOW"},
    "module_degradation": {"PV_DC_UNDERPERFORM"},
    "ground_fault": {"PV_RISO_TRIP", "PV_INVERTER_DOWN"},
    "inverter_cooling": {"PV_INV_HOT", "PV_DERATE_EARLY"},
    "inverter_efficiency": {"PV_INV_EFF_LOW"},
    "irradiance_sensor": {"PV_IRRADIANCE_SENSOR"},
}


def faults():
    bad = 0
    print("faults (full severity, 10:00, 20 readings each):")
    for fm in [None] + FMS:
        b = Block(TW, seed=3)
        if fm:
            b.set_fault(fm, 1.0)
        want = EXPECT.get(fm, set())
        seen, ok = set(), True
        for _ in range(20):
            r = b.measure(10.0)
            got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            ok &= got == want
            seen |= got
        bad += not ok
        print(f"  {fm or 'healthy':20s} {'ok ' if ok else 'BAD'} {sorted(seen)}")
    # a healthy block over a whole day raises nothing
    b, day = Block(TW, seed=4), set()
    for i in range(0, 24 * 12):
        r = b.measure(i / 12)
        day |= {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
    print(f"  healthy, whole day    {'ok ' if not day else 'BAD'} {sorted(day)}")
    bad += bool(day)
    return bad


def plant_run():
    bad = 0
    print("live plant (fault ramps in over 120 s, 1 s steps, starts 10:00):")
    for fm in FMS:
        p = Plant(TW, seed=11)
        for _ in range(10):
            p.step(1.0)
        p.set_fault(fm, 1.0, 120)
        seen, first = set(), None
        for i in range(240):
            tr = p.step(1.0)
            m = p.measure(tr)
            names = {c["name"] for c in tc.conditions(TW, m, tc.evaluate(TW, m))[0]}
            if EXPECT[fm] <= names and first is None:
                first = i + 1
            seen |= names
        ok = first is not None
        bad += not ok
        print(f"  {fm:20s} {'ok ' if ok else 'BAD'} all rules after {first} steps (plant {p.hour():.1f} h)  seen {sorted(seen)}")
    return bad


def example():
    b = Block(TW, seed=11)
    r = b.measure(10.0)
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_pv-twin.json"
    out.write_text(json.dumps({"hour": 10.0, "reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()}}, indent=1), encoding="utf-8")
    print("example:", out)


if __name__ == "__main__":
    b = parity(readings())
    b += faults()
    b += plant_run()
    example()
    sys.exit(1 if b else 0)
