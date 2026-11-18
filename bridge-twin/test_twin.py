"""Checks for the BR-6001 twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings over whole bridge days, healthy and faulted at several severities; every alert rule equals the Python conditions.
2. faults: each failure mode, injected at full severity at 10:00, raises exactly its expected rules; a healthy bridge raises none,
   also over a whole day.
3. live plant: each failure mode set on the Plant (the stand-in used by the live pages) shows its rules within 240 steps.
4. writes ../blog/_twin/example_bridge-twin.json (one healthy 10:00 reading and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Bridge, Plant

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
            p.set_fault(fm, 1.0, 300)
        for i in range(1500):                      # about one bridge day
            tr = p.step(1.0)
            if i % 10 == 0:
                rows.append(p.measure(tr))
    b = Bridge(TW, seed=5)
    for fm in [None] + FMS:
        for sev in (0.25, 0.5, 0.75, 1.0):
            b.clear()
            if fm:
                b.set_fault(fm, sev)
            for h in range(0, 24, 3):
                rows.append(b.measure(h + 0.5))
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
    "bearing_seized": {"BR_BEARING_SEIZED", "BR_PIER_TILT", "BR_BEARING_FRICTION_HIGH"},
    "ptfe_wear": {"BR_SLIDING_GAP_LOW", "BR_BEARING_FRICTION_HIGH"},
    "sliding_path_fast": {"BR_WEAR_RATE_HIGH", "BR_WEAR_LIFE_LOW"},
    "joint_blocked": {"BR_JOINT_BLOCKED", "BR_DECK_RESTRAINT"},
    "joint_control_failure": {"BR_JOINT_GAP_UNEVEN", "BR_JOINT_GAP_LIMIT", "BR_JOINT_IMPACT"},
    "girder_stiffness_loss": {"BR_STRAIN_RATIO_HIGH"},
    "overweight_traffic": {"BR_OVERWEIGHT_TRAFFIC"},
    "displacement_sensor": {"BR_SENSOR_MISMATCH"},
}


def faults():
    bad = 0
    print("faults (full severity, 10:00, 20 readings each):")
    for fm in [None] + FMS:
        b = Bridge(TW, seed=3)
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
        print(f"  {fm or 'healthy':22s} {'ok ' if ok else 'BAD'} {sorted(seen)}")
    b, day = Bridge(TW, seed=4), set()
    for i in range(24 * 12):
        r = b.measure(i / 12)
        day |= {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
    print(f"  healthy, whole day     {'ok ' if not day else 'BAD'} {sorted(day)}")
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
        print(f"  {fm:22s} {'ok ' if ok else 'BAD'} all rules after {first} steps (plant {p.hour():.1f} h)  seen {sorted(seen)}")
    return bad


def example():
    b = Bridge(TW, seed=11)
    r = b.measure(10.0)
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_bridge-twin.json"
    out.write_text(json.dumps({"hour": 10.0, "reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()}}, indent=1), encoding="utf-8")
    print("example:", out)


if __name__ == "__main__":
    b = parity(readings())
    b += faults()
    b += plant_run()
    example()
    sys.exit(1 if b else 0)
