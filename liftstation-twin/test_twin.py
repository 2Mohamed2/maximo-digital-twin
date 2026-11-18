"""Checks for the LS-5201 twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings over the dry-weather day, healthy and faulted; every alert rule equals the Python conditions.
2. faults: each failure mode, injected at full severity, raises exactly its own conditions at 50 random moments of the day;
   a healthy station raises none.
3. plant: the live Plant (as the twin pages run it: inflow, level control, alternation, cycle log), each fault set at full
   severity with its default ramp: its rules appear within 240 simulated steps of 1 s.
4. writes ../blog/_twin/example_liftstation-twin.json (one healthy reading during a run, and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Station, Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]


def readings():
    x, rows = Station(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            x.clear()
            if fm:
                x.set_fault(fm, sev)
            rows += [x.measure() for _ in range(30)]
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
    x = Station(TW, seed=3)
    for fm in [None] + FMS:
        want = EXPECT.get(fm, set())
        for _ in range(50):
            x.clear()
            if fm:
                x.set_fault(fm, 1.0)
            r = x.measure()
            got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            if got != want:
                break
        ok = got == want
        bad += not ok
        print(f"  {fm or 'healthy':22s} {'ok ' if ok else 'BAD'} {sorted(got)}" + ("" if ok else f"  want {sorted(want)}"))
    return bad


def plant():
    bad = 0
    # healthy: a whole simulated day raises nothing
    P = Plant(TW, seed=11)
    seen = set()
    for _ in range(300):
        P.step(2.0)
    for _ in range(1440):
        r = P.measure(P.step(1.0))
        seen |= {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
    print(f"  {'healthy (1 day)':22s} {'ok ' if not seen else 'BAD'} {sorted(seen)}")
    bad += bool(seen)
    for fm in FMS:
        P = Plant(TW, seed=11)
        for _ in range(300):
            P.step(2.0)
        P.set_fault(fm, 1.0, TW["failure_modes"][fm]["default_ramp_min"] * 60)
        first = None
        for i in range(240):
            r = P.measure(P.step(1.0))
            got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            if first is None and EXPECT[fm] <= got:
                first = i + 1
        ok = first is not None
        bad += not ok
        print(f"  {fm:22s} {'ok ' if ok else 'BAD'} all rules by step {first}")
    return bad


def example():
    """A healthy moment mid-morning: the duty pump running, the level falling through the middle of the band."""
    P = Plant(TW, seed=21)
    P.t = 6 * 3600.0
    for _ in range(3600):
        P.step(2.0)
    for _ in range(2000):
        tr = P.step(0.1)
        if tr["n"] == 1 and abs(tr["level_meas"] - 1.30) < 0.03 and tr["qin"] > 30:
            break
    r = P.measure(tr)
    t = tc.evaluate(TW, r)
    assert not tc.conditions(TW, r, t)[0], tc.conditions(TW, r, t)[0]
    out = HERE.parent / "blog" / "_twin" / "example_liftstation-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: float(f"{v:.7g}") if isinstance(v, float) else v for k, v in t.items()}}, indent=1), encoding="utf-8")
    print("example:", out, f"(plant time {P.t % 86400 / 3600:.2f} h, inflow {tr['qin']:.1f} l/s)")


if __name__ == "__main__":
    b = parity(readings())
    print("faults:")
    b += faults()
    print("plant (240 steps):")
    b += plant()
    example()
    sys.exit(1 if b else 0)
