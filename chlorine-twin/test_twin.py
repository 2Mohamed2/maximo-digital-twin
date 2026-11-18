"""Checks for the CL-5101 twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings over the whole year (0.5 to 28 C, pH 6.5 to 8.8, any level and flow), healthy and faulted; every alert rule
   equals the Python conditions.
2. faults: each failure mode, injected at full severity at the nominal state (12 C, pH 7.3, design flow, 4.0 m), raises
   exactly its expected conditions in 50 noisy readings; a healthy clearwell raises none.
3. plant: the live Plant (as the twin pages run it), each fault set at full severity with its default ramp: its rules appear
   within 240 simulated steps of 1 s; a healthy Plant raises nothing over a whole plant day.
4. writes ../blog/_twin/example_chlorine-twin.json (one healthy reading and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Clearwell, Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]


def readings():
    x, rows = Clearwell(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            x.clear()
            if fm:
                x.set_fault(fm, sev)
            rows += [x.measure(vary=True) for _ in range(20)] + [x.measure() for _ in range(10)]
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


# At full severity, at the nominal state. The twin file lists every rule that can see a mode (a superset).
EXPECT = {
    "cold_peak_drawdown": {"CL_CT_FAIL", "CL_LEVEL_LOW"},
    "dose_pump_gas_lock": {"DOSE_PUMP_DEVIATION", "CL_TRIM_HIGH", "CL_OUTLET_LOW", "CL_CT_MARGIN_LOW"},
    "hypo_strength_loss": {"HYPO_STRENGTH_LOW", "CL_TRIM_HIGH"},
    "demand_rise": {"CL_DEMAND_HIGH", "CL_TRIM_HIGH"},
    "analyser_drift": {"CL_ANALYSER_MISMATCH", "CL_OUTLET_LOW"},
    "clearwell_decay": {"CL_DECAY_HIGH"},
    "ph_high": {"CL_PH_HIGH"},
}


def faults():
    bad = 0
    x = Clearwell(TW, seed=3)
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
    P = Plant(TW, seed=11)
    seen = set()
    for _ in range(1440):                      # one plant day at time_scale 60
        true = P.step(1.0)
        r = P.measure(true)
        seen |= {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
    print(f"  {'healthy day':22s} {'ok ' if not seen else 'BAD'} {sorted(seen)}")
    bad += bool(seen)
    for fm in FMS:
        P = Plant(TW, seed=11)
        for _ in range(3600):
            P.step(2.0)
        P.set_fault(fm, 1.0, TW["failure_modes"][fm]["default_ramp_min"] * 60)
        first = None
        for i in range(240):
            true = P.step(1.0)
            r = P.measure(true)
            got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            if first is None and EXPECT[fm] <= got:
                first = i + 1
        ok = first is not None
        bad += not ok
        print(f"  {fm:22s} {'ok ' if ok else 'BAD'} all rules by step {first}")
    return bad


def example():
    x = Clearwell(TW, seed=11)
    r = x.measure()
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_chlorine-twin.json"
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
