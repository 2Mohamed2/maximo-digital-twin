"""Checks for the ESDV-2101 twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings, healthy and faulted; every alert rule equals the Python conditions.
2. faults: each failure mode, injected at full severity, raises its own conditions; a healthy valve raises none.
3. writes example_esdv-twin.json (one healthy reading and the twin numbers), used by the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Valve

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]


def readings():
    v, rows = Valve(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            v.clear()
            if fm:
                v.set_fault(fm, sev)
            rows += [v.measure() for _ in range(40)]
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


EXPECT = {
    "stem_seat_sticking": {"ESD_FRICTION_HIGH", "ESD_TORQUE_MARGIN_LIMIT", "ESD_PST_FAILED"},
    "spring_relaxation": {"ESD_SPRING_WEAK", "ESD_TORQUE_MARGIN_LOW"},
    "sov_exhaust_restriction": {"ESD_STROKE_TOO_SLOW"},
    "air_supply_low": {"ESD_AIR_MARGIN"},
    "position_feedback": {"ESD_POSITION_MISMATCH"},
    "pst_not_run": {"ESD_PST_OVERDUE", "ESD_SIL_DRIFT"},
    "bypass_left_on": {"ESD_BYPASS_LONG", "ESD_SIL_DRIFT"},
}


def faults():
    bad = 0
    v = Valve(TW, seed=3)
    for fm in [None] + FMS:
        v.clear()
        if fm:
            v.set_fault(fm, 1.0)
        r = v.measure()
        got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
        want = EXPECT.get(fm, set())
        ok = got == want
        bad += not ok
        print(f"  {fm or 'healthy':26s} {'ok ' if ok else 'BAD'} {sorted(got)}")
    return bad


def example():
    v = Valve(TW, seed=11)
    r = v.measure()
    t = tc.evaluate(TW, r)
    out = HERE / "example_esdv-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()}}, indent=1), encoding="utf-8")
    print("example:", out)


if __name__ == "__main__":
    b = parity(readings())
    print("faults:")
    b += faults()
    example()
    sys.exit(1 if b else 0)
