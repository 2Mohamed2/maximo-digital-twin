"""Checks for the DG-6201 twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings, healthy and faulted, in standby, starting, on load and cooling down; every alert rule equals the Python conditions.
2. faults: each failure mode, injected at full severity, raises exactly its own conditions on a monthly test reading;
   a healthy set raises none.
3. plant: in the live Plant, each fault (ramped in over 120 s) raises its rules within 240 simulated steps; a healthy
   plant raises none over 3000 steps (about 25 test cycles).
4. writes ../blog/_twin/example_genset-twin.json (one healthy monthly-test reading and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Genset, Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]
POINTS = [(990.0, 24.0, 3), (1200.0, 30.0, 4), (1650.0, 38.0, 4), (450.0, 18.0, 3), (None, 24.0, 0), (None, 26.0, 2), (None, 22.0, 1)]


def readings():
    g, rows = Genset(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            g.clear()
            if fm:
                g.set_fault(fm, sev)
            for i in range(28):
                p, amb, mode = POINTS[i % len(POINTS)]
                rows.append(g.measure(g.true_state(p, amb, mode), g.start_record(amb)))
    p = Plant(TW, seed=5)
    for i in range(600):
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
    g = Genset(TW, seed=3)
    print("faults (full severity, monthly test at 990 kW, 25 C, 40 readings):")
    for fm in [None] + FMS:
        g.clear()
        if fm:
            g.set_fault(fm, 1.0)
        want = EXPECT.get(fm, set())
        seen, ok = set(), True
        for i in range(40):
            r = g.measure(g.true_state(990.0 + (i % 5 - 2) * 5, 25.0, 3), g.start_record(25.0))
            got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            seen |= got
            ok &= got == want
        bad += not ok
        print(f"  {fm or 'healthy':24s} {'ok ' if ok else 'BAD'} {sorted(seen)}")
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
    print(f"  healthy, 3000 steps     {'ok ' if not seen else 'BAD'} {sorted(seen)}")
    bad += bool(seen)
    for fm in FMS:
        worst = 0
        for start_offset in (0, 37, 81):                # fault set at different points of the test cycle
            p = Plant(TW, seed=11)
            for _ in range(3600):
                p.step(2.0)
            for _ in range(60 + start_offset):
                p.step(1.0)
            p.set_fault(fm, 1.0, 120)
            first = {}
            for i in range(240):
                r = p.measure(p.step(1.0))
                for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]:
                    first.setdefault(c["name"], i + 1)
            missing = EXPECT[fm] - set(first)
            extra = set(first) - EXPECT[fm]
            worst = max(worst, max((first.get(x, 999) for x in EXPECT[fm]), default=0))
            if missing or extra:
                bad += 1
                print(f"  {fm:24s} offset {start_offset}: MISSING {sorted(missing)} EXTRA {sorted(extra)}")
        print(f"  {fm:24s} ok, every rule within {worst} steps (3 cycle offsets)" if worst <= 240 else f"  {fm:24s} BAD")
    return bad


def example():
    g = Genset(TW, seed=11)
    r = g.measure(g.true_state(990.0, 25.0, 3), g.start_record(25.0))
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_genset-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()}}, indent=1), encoding="utf-8")
    cs, health = tc.conditions(TW, r, t)
    print("example:", out, "conditions", [c["name"] for c in cs], "health", health)


if __name__ == "__main__":
    b = parity(readings())
    b += faults()
    b += plant()
    example()
    sys.exit(1 if b else 0)
