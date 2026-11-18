"""Checks for the BL-4501 steam boiler twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings, healthy and faulted, at loads from 50 to 100 %; every alert rule equals the Python conditions.
2. faults: each failure mode, injected at full severity, raises exactly its own conditions at several loads; a healthy
   boiler raises none.
3. plant: in the live Plant, each fault (ramped in over 120 s) raises its rules within 240 simulated steps.
4. writes ../blog/_twin/example_boiler-twin.json (one healthy reading and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Boiler, Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]
LOADS = (0.5, 0.6, 0.75, 0.9, 1.0)


def readings():
    b, rows = Boiler(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            b.clear()
            if fm:
                b.set_fault(fm, sev)
            for i in range(30):
                rows.append(b.measure(b.true_state(0.5 + 0.5 * (i % 11) / 10, 15 + i)))
    p = Plant(TW, seed=5)
    for i in range(400):
        rows.append(p.measure(p.step(1.0)))
    return rows


def parity(rows):
    df = pd.DataFrame([{k.upper(): x for k, x in r.items()} for r in rows])
    bad = 0
    for name, expr in tc.monitor_expressions(TW):
        got = np.asarray(eval(expr, {"df": df, "np": np}), dtype=float)
        want = np.array([tc.evaluate(TW, r)[name.lower()] for r in rows], dtype=float)
        n = int((~np.isclose(got, want, rtol=1e-9, atol=1e-9)).sum())
        if n:
            print(f"MISMATCH {name}: {n}")
        bad += n
    for name, expr, sev, fm in tc.alert_rules(TW):
        got = np.asarray(eval(expr, {"df": df, "np": np}), dtype=bool)
        want = np.array([any(c["name"] == name for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]) for r in rows])
        n = int((got != want).sum())
        if n:
            print(f"MISMATCH rule {name}: {n}")
        bad += n
    print(f"parity: {len(rows)} readings, {len(tc.monitor_expressions(TW))} expressions, {len(tc.alert_rules(TW))} rules, {bad} mismatches")
    return bad


EXPECT = {
    "fireside_fouling": {"BLR_FIRESIDE_FOULING"},
    "waterside_scale": {"BLR_HARDNESS", "BLR_WATERSIDE_SCALE"},
    "economiser_fouling": {"BLR_ECO_EFFECTIVENESS_LOW", "BLR_STACK_HIGH", "BLR_EFF_LOW"},
    "excess_air_high": {"BLR_EXCESS_AIR_HIGH", "BLR_EFF_LOW"},
    "tds_control_fault": {"BLR_TDS_HIGH"},
    "blowdown_valve_passing": {"BLR_BLOWDOWN_HIGH"},
    "feed_pump_wear": {"BLR_FEED_MARGIN_LOW", "BLR_LEVEL_DEVIATION"},
    "safety_tests_overdue": {"BLR_LWCO_TEST_OVERDUE", "BLR_SV_TEST_OVERDUE"},
}


def faults():
    bad = 0
    b = Boiler(TW, seed=3)
    print("faults (full severity, 20 readings at each of 5 loads):")
    for fm in [None] + FMS:
        b.clear()
        if fm:
            b.set_fault(fm, 1.0)
        want = EXPECT.get(fm, set())
        seen, ok = set(), True
        for load in LOADS:
            for _ in range(20):
                r = b.measure(b.true_state(load, 25))
                got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
                seen |= got
                ok &= got == want
        bad += not ok
        print(f"  {fm or 'healthy':24s} {'ok ' if ok else 'BAD'} {sorted(seen)}")
    return bad


def plant():
    bad = 0
    print("plant (fault ramped in over 120 s, 1 s steps):")
    for fm in FMS:
        p = Plant(TW, seed=11)
        for _ in range(60):
            p.step(1.0)
        p.set_fault(fm, 1.0, 120)
        first = {}
        for i in range(240):
            r = p.measure(p.step(1.0))
            for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]:
                first.setdefault(c["name"], i + 1)
        missing = EXPECT[fm] - set(first)
        extra = set(first) - EXPECT[fm]
        bad += bool(missing) + bool(extra)
        print(f"  {fm:24s} {'ok ' if not missing and not extra else 'MISSING ' + str(sorted(missing)) + ' EXTRA ' + str(sorted(extra))} "
              + ", ".join(f"{n} @{s}" for n, s in sorted(first.items(), key=lambda x: x[1])))
    p = Plant(TW, seed=12)
    seen = set()
    for _ in range(3600):
        r = p.measure(p.step(2.0))
        seen |= {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
    bad += bool(seen)
    print(f"  healthy warm-up, 3600 x 2 s: {'ok ' if not seen else 'BAD'} {sorted(seen)}")
    return bad


def example():
    b = Boiler(TW, seed=11)
    r = b.measure(b.true_state(0.85, 24.0))
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_boiler-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()}}, indent=1), encoding="utf-8")
    cs, health = tc.conditions(TW, r, t)
    print("example:", out, "conditions", [c["name"] for c in cs], "health", health)


if __name__ == "__main__":
    b = parity(readings())
    b += faults()
    b += plant()
    example()
    sys.exit(1 if b else 0)
