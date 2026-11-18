"""Checks for the PS-6801 twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings, healthy and faulted; every alert rule equals the Python conditions.
2. faults: each failure mode, injected at full severity, raises exactly its own conditions; a healthy pasteurizer raises none.
3. plant: the live Plant (as the twin pages run it), each fault set at full severity with its default ramp: its rules
   appear within 240 simulated steps of 1 s.
4. writes ../blog/_twin/example_pasteurizer-twin.json (one healthy reading and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Pasteurizer, Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]


def readings():
    x, rows = Pasteurizer(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            x.clear()
            if fm:
                x.set_fault(fm, sev)
            rows += [x.measure() for _ in range(40)]
    return rows


def parity(rows):
    df = pd.DataFrame([{k.upper(): x for k, x in r.items()} for r in rows])
    bad = 0
    for name, expr in tc.monitor_expressions(TW):
        got = np.asarray(eval(expr, {"df": df, "np": np}), dtype=float)
        want = np.array([tc.evaluate(TW, r)[name.lower()] for r in rows], dtype=float)
        bad += int((~np.isclose(got, want, rtol=1e-9, atol=1e-12)).sum())
    for name, expr, sev, fm in tc.alert_rules(TW):
        got = np.asarray(eval(expr, {"df": df, "np": np}), dtype=bool)
        want = np.array([any(c["name"] == name for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]) for r in rows])
        bad += int((got != want).sum())
    print(f"parity: {len(rows)} readings, {len(tc.monitor_expressions(TW))} expressions, {len(tc.alert_rules(TW))} rules, {bad} mismatches")
    return bad


EXPECT = {fm: set(TW["failure_modes"][fm]["rules"]) for fm in FMS}


def faults():
    bad = 0
    x = Pasteurizer(TW, seed=3)
    for fm in [None] + FMS:
        want = EXPECT.get(fm, set())
        for _ in range(50):                   # 50 random operating points per mode, all must give exactly the set
            x.clear()
            if fm:
                x.set_fault(fm, 1.0)
            r = x.measure()
            got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            if got != want:
                break
        ok = got == want
        bad += not ok
        print(f"  {fm or 'healthy':20s} {'ok ' if ok else 'BAD'} {sorted(got)}" + ("" if ok else f"  want {sorted(want)}"))
    return bad


def plant():
    bad = 0
    for fm in FMS:
        P = Plant(TW, seed=11)
        for _ in range(300):
            P.step(2.0)
        P.set_fault(fm, 1.0, TW["failure_modes"][fm]["default_ramp_min"] * 60)
        seen, first = set(), None
        for i in range(240):
            true = P.step(1.0)
            r = P.measure(true)
            got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            seen |= got
            if first is None and EXPECT[fm] <= got:
                first = i + 1
        ok = first is not None
        bad += not ok
        print(f"  {fm:20s} {'ok ' if ok else 'BAD'} all rules by step {first}")
    return bad


def example():
    x = Pasteurizer(TW, seed=11)
    x.qbase, x.tin, x.run_h, x.phase, x.start_q, x.dsp = 9500.0, 4.0, 6.0, 0.0, 9500.0, 0.0
    r = x.reading(x.true())
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_pasteurizer-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: float(f"{v:.7g}") if isinstance(v, float) else v for k, v in t.items()}}, indent=1), encoding="utf-8")
    print("example:", out)


if __name__ == "__main__":
    b = parity(readings())
    print("faults:")
    b += faults()
    print("plant (240 steps):")
    b += plant()
    example()
    sys.exit(1 if b else 0)
