"""Checks for the CR-6301 twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings, healthy and faulted; every alert rule equals the Python conditions.
2. faults: each failure mode, injected at full severity, raises exactly its own conditions; a healthy unit raises none.
3. plant: in the live Plant, each fault (ramped in over 120 s) raises its rules within 240 simulated steps.
4. writes ../blog/_twin/example_crah-twin.json (one healthy reading and the twin's numbers) for the post.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Crah, Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]
LOADS = [60.0, 57.0, 63.0, 45.0, 70.0]


def readings():
    u, rows = Crah(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            u.clear()
            if fm:
                u.set_fault(fm, sev)
            for i in range(30):
                rows.append(u.measure(u.true_state(LOADS[i % len(LOADS)])))
    p = Plant(TW, seed=5)
    for i in range(500):
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


EXPECT = {fm: set(TW["failure_modes"][fm]["rules"]) for fm in FMS}


def faults():
    bad = 0
    u = Crah(TW, seed=3)
    print("faults (full severity, IT load 57 to 63 kW, 40 readings):")
    for fm in [None] + FMS:
        u.clear()
        if fm:
            u.set_fault(fm, 1.0)
        want = EXPECT.get(fm, set())
        seen, ok = set(), True
        for i in range(40):
            r = u.measure(u.true_state(60.0 + 1.5 * (i % 5 - 2)))
            got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            seen |= got
            ok &= got == want
        bad += not ok
        print(f"  {fm or 'healthy':22s} {'ok ' if ok else 'BAD'} {sorted(seen)}")
    return bad


def plant():
    bad = 0
    print("plant (fault ramped in over 120 s, 1 s steps):")
    p = Plant(TW, seed=11)
    for _ in range(3600):
        p.step(2.0)
    seen = set()
    for _ in range(3000):
        r = p.measure(p.step(1.0))
        seen |= {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
    print(f"  healthy, 3000 steps   {'ok ' if not seen else 'BAD'} {sorted(seen)}")
    bad += bool(seen)
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
        print(f"  {fm:22s} {'ok ' if not missing and not extra else 'MISSING ' + str(sorted(missing)) + ' EXTRA ' + str(sorted(extra))} "
              + ", ".join(f"{n} @{s}" for n, s in sorted(first.items(), key=lambda x: x[1])))
    return bad


def example():
    u = Crah(TW, seed=11)
    r = u.measure(u.true_state(60.0, math.pi / 2))
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_crah-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()}}, indent=1), encoding="utf-8")
    cs, health = tc.conditions(TW, r, t)
    print("example:", out, "conditions", [c["name"] for c in cs], "health", health)


if __name__ == "__main__":
    b = parity(readings())
    b += faults()
    b += plant()
    example()
    sys.exit(1 if b else 0)
