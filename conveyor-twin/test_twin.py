"""Checks for the CV-3801 overland belt conveyor twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings, healthy and faulted; every alert rule equals the Python conditions.
2. faults: each failure mode, injected at full severity, raises exactly its expected conditions at 20 tonnages; a healthy
   conveyor raises none.
3. plant: the live Plant (used by the twin pages) shows every rule listed for each fault within 240 one-second steps.
4. writes ../blog/_twin/example_conveyor-twin.json (one healthy reading and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Conveyor, Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]


def readings():
    v, rows = Conveyor(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            v.clear()
            if fm:
                v.set_fault(fm, sev)
            rows += [v.measure() for _ in range(40)]
    p = Plant(TW, seed=5)
    for fm in [None] + FMS:
        p.clear_faults(1)
        if fm:
            p.set_fault(fm, 1.0, 60)
        for i in range(300):
            s = p.step(1.0)
            if i % 3 == 0:
                rows.append(p.measure(s))
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


# At full severity the tiered rules (HOT / GROWTH / MISTRACKING) have handed over to their higher tier.
EXPECT = {
    "high_resistance": {"CV_POWER_HIGH"},
    "idler_bearing_failure": {"CV_IDLER_CRITICAL"},
    "lagging_wear": {"CV_SLIP"},
    "takeup_jammed": {"CV_TAKEUP_TENSION_LOW", "CV_SLIP_MARGIN_LOW", "CV_SLIP"},
    "belt_stretch": {"CV_TAKEUP_TRAVEL_END", "CV_BELT_STRETCH"},
    "splice_failure": {"CV_SPLICE_CRITICAL"},
    "mistracking": {"CV_MISTRACKING_SEVERE"},
    "load_share_imbalance": {"CV_LOAD_SHARE", "CV_MOTOR_OVERLOAD"},
}


def faults():
    bad = 0
    v = Conveyor(TW, seed=3)
    dm = TW["design"]["demo"]
    for fm in [None] + FMS:
        want, nbad = EXPECT.get(fm, set()), 0
        for trial in range(20):
            v.clear()
            if fm:
                v.set_fault(fm, 1.0)
            tph = dm["tph_min"] + (dm["tph_max"] - dm["tph_min"]) * trial / 19
            r = v.measure(tph=tph)
            got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            if got != want:
                nbad += 1
                print(f"  {fm or 'healthy':22s} BAD {sorted(got)} at {tph:.0f} t/h")
        bad += nbad
        print(f"  {fm or 'healthy':22s} {'ok ' if not nbad else 'BAD'} {sorted(want)}")
    return bad


def plant():
    bad = 0
    for fm in FMS:
        p = Plant(TW, seed=11)
        for _ in range(120):
            p.step(1.0)
        p.set_fault(fm, 1.0, TW["failure_modes"][fm]["default_ramp_min"] * 60)
        first = {}
        for i in range(240):
            m = p.measure(p.step(1.0))
            for c in tc.conditions(TW, m, tc.evaluate(TW, m))[0]:
                first.setdefault(c["name"], i + 1)
        want = set(TW["failure_modes"][fm]["rules"])
        ok = want <= set(first)
        bad += not ok
        order = ", ".join(f"{n} {first[n]} s" for n in sorted(want & set(first), key=first.get))
        extra = sorted(set(first) - want)
        print(f"  {fm:22s} {'OK     ' if ok else 'MISSING'} {order}  missing: {sorted(want - set(first))}  other: {extra}")
    p = Plant(TW, seed=13)
    seen = set()
    for _ in range(1200):
        m = p.measure(p.step(1.0))
        seen |= {c["name"] for c in tc.conditions(TW, m, tc.evaluate(TW, m))[0]}
    print(f"  healthy plant, 1200 s: {'OK' if not seen else 'BAD'} {sorted(seen)}")
    return bad + bool(seen)


def example():
    v = Conveyor(TW, seed=11)
    r = v.measure(tph=2250.0, amb=TW["design"]["demo"]["ambient_c"])
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_conveyor-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()},
                               "conditions": tc.conditions(TW, r, t)[0]}, indent=1), encoding="utf-8")
    print("example:", out)


if __name__ == "__main__":
    b = parity(readings())
    print("faults (full severity, 20 tonnages each):")
    b += faults()
    print("plant (first second each rule appears after the fault starts):")
    b += plant()
    example()
    sys.exit(1 if b else 0)
