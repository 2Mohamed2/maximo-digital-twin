"""Checks for the PSV-2601 twin.

  python test_twin.py
1. sizing: the API 520 Part I vapour equation of twin_calc reproduces a published example, and the API 526 J orifice
   with Kd 0.975 gives close to the certified air capacity in the Crosby J-Series data sheet.
2. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings, healthy and faulted; every alert rule equals the Python conditions.
3. faults: each failure mode, injected at full severity, raises exactly its own conditions; a healthy valve raises none.
4. plant: the live stand-in (Plant) shows each fault's rules within 240 one-second steps.
5. writes ../blog/_twin/example_psv-twin.json (one healthy reading and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Valve, Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]


def sizing():
    bad = 0
    # Example from the open-source fluids library (API520_A_g docstring): 24270 kg/h, 348 K, Z 0.90, M 51, k 1.11, P1 670 kPa
    a = tc.api520_area_mm2(24270, 348, 0.90, 51, 1.11, 670)
    ok = abs(a - 3699.046) < 0.5
    bad += not ok
    print(f"sizing: API 520 example area {a:.1f} mm2 (published 3699.0) {'ok' if ok else 'BAD'}")
    # Crosby J-Series: J orifice, air, 600 psig set, 10 % overpressure, 60 F: certified 15544 SCFM
    p1 = (600 * 1.1 + 14.696) * 6.894757
    w = 830 * tc.api520_c(1.4) * 0.975 * p1 / ((288.71 * 1.0 / 28.96) ** 0.5)
    scfm = w / 1.2232 / 60 * 35.3147
    ok = abs(scfm / 15544 - 1) < 0.02
    bad += not ok
    print(f"sizing: J orifice air at 600 psig {scfm:.0f} SCFM (Crosby certified 15544) {'ok' if ok else 'BAD'}")
    return bad


def readings():
    v, rows = Valve(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            v.clear()
            if fm:
                v.set_fault(fm, sev)
            rows += [v.measure() for _ in range(40)]
    p = Plant(TW, seed=5)
    p.set_fault("seat_passing", 0.6, 30)
    for _ in range(200):
        rows.append(p.measure(p.step(1.0)))
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
    "seat_passing": {"PSV_PASSING"},
    "operating_near_set": {"PSV_NEAR_SET"},
    "set_pressure_drift": {"PSV_POP_DRIFT", "PSV_SEAT_TIGHTNESS", "PSV_RBI_INTERVAL_SHORT"},
    "valve_sticking": {"PSV_LATE_OPENING", "PSV_ACCUMULATION"},
    "inlet_restriction": {"PSV_INLET_LOSS", "PSV_CHATTER"},
    "high_backpressure": {"PSV_BACKPRESSURE_HIGH"},
    "relief_load_increase": {"PSV_CAPACITY_SHORT"},
    "test_overdue": {"PSV_TEST_OVERDUE"},
}


def faults():
    bad = 0
    v = Valve(TW, seed=3)
    for fm in [None] + FMS:
        for trial in range(20):
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
        print(f"  {fm or 'healthy':22s} {'ok ' if ok else 'BAD'} {sorted(got)}")
    return bad


def plant():
    bad = 0
    for fm in FMS:
        p = Plant(TW, seed=11)
        p.set_fault(fm, 1.0, TW["failure_modes"][fm]["default_ramp_min"] * 60)
        seen, first = set(), {}
        for i in range(240):
            r = p.measure(p.step(1.0))
            for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]:
                seen.add(c["name"])
                first.setdefault(c["name"], i + 1)
        ok = EXPECT[fm] <= seen
        bad += not ok
        print(f"  {fm:22s} {'ok ' if ok else 'BAD'} " + ", ".join(f"{n} @{first[n]}s" for n in sorted(EXPECT[fm]) if n in first))
    return bad


def example():
    v = Valve(TW, seed=11)
    r = v.measure()
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_psv-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()}}, indent=1), encoding="utf-8")
    print("example:", out, "conditions:", [c["name"] for c in tc.conditions(TW, r, t)[0]])


if __name__ == "__main__":
    b = sizing()
    b += parity(readings())
    print("faults:")
    b += faults()
    print("plant (rules seen within 240 s):")
    b += plant()
    example()
    sys.exit(1 if b else 0)
