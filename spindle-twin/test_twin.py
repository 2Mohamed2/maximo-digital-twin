"""Checks for the MC-4801 machining centre main spindle twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings, healthy and faulted, steady cuts and the live part program (air moves and tool changes included); every alert
   rule equals the Python conditions.
2. faults: each failure mode, injected at full severity, raises exactly its expected conditions in each of the three
   roughing operations (20 readings per operation); a healthy spindle raises none.
3. plant: the live Plant (used by the twin pages) shows every expected rule of each fault within 240 one-second steps,
   and a healthy Plant raises nothing over 600 steps (all four operations, air moves and tool changes).
4. writes ../blog/_twin/example_spindle-twin.json (one healthy reading in the roughing cut and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Plant, Spindle

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]
OPS = TW["design"]["program"]["operations"]


def readings():
    v, rows = Spindle(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            v.clear()
            if fm:
                v.set_fault(fm, sev)
            rows += [v.measure(OPS[i % len(OPS)]) for i in range(40)]
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


# At full severity the clamping loss is past the warning band, so only the LOW rule is expected.
EXPECT = {fm: set(TW["failure_modes"][fm]["rules"]) for fm in FMS}
EXPECT["clamping_force_loss"] = {"SP_CLAMP_FORCE_LOW"}


def faults():
    bad = 0
    v = Spindle(TW, seed=3)
    for fm in [None] + FMS:
        want, nbad = EXPECT.get(fm, set()), 0
        for op in OPS[:3]:
            for _ in range(20):
                v.clear()
                if fm:
                    v.set_fault(fm, 1.0)
                r = v.measure(op)
                got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
                if got != want:
                    nbad += 1
                    print(f"  {fm or 'healthy':24s} BAD {sorted(got)} in {op['op']}")
        bad += nbad
        print(f"  {fm or 'healthy':24s} {'ok ' if not nbad else 'BAD'} {sorted(want)}")
    return bad


def plant():
    bad = 0
    p = Plant(TW, seed=13)
    seen = set()
    for _ in range(600):
        m = p.measure(p.step(1.0))
        seen |= {c["name"] for c in tc.conditions(TW, m, tc.evaluate(TW, m))[0]}
    print(f"  {'healthy (600 s)':24s} {'OK     ' if not seen else 'FALSE  '} {sorted(seen)}")
    bad += bool(seen)
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
        want = EXPECT[fm]
        ok = want <= set(first)
        bad += not ok
        order = ", ".join(f"{n} {first[n]} s" for n in sorted(set(first), key=first.get))
        print(f"  {fm:24s} {'OK     ' if ok else 'MISSING'} {order}  missing: {sorted(want - set(first))}")
    return bad


def example():
    v = Spindle(TW, seed=11)
    r = v.measure(OPS[0])
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_spindle-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()},
                               "conditions": tc.conditions(TW, r, t)[0]}, indent=1), encoding="utf-8")
    print("example:", out)


if __name__ == "__main__":
    b = parity(readings())
    print("faults (full severity, 3 roughing operations x 20 readings):")
    b += faults()
    print("plant (first second each rule appears after the fault starts):")
    b += plant()
    example()
    sys.exit(1 if b else 0)
