"""Checks for the ST-3201 twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings, healthy and faulted; every alert rule equals the Python conditions.
2. faults: each failure mode, injected at full severity, raises exactly its own conditions; a healthy turbine raises none.
3. plant: in the live stand-in (Plant), each failure mode ramped in at its default ramp raises its rules within 240 steps of 1 s.
4. writes ../blog/_twin/example_steamturb-twin.json (one healthy reading and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]
EXPECT = {fm: set(TW["failure_modes"][fm]["rules"]) for fm in FMS}


def settled(fm, sev, seed, steps=150):
    p = Plant(TW, seed=seed)
    if fm:
        p.set_fault(fm, sev, 1)
    for _ in range(steps):
        tr = p.step(1.0)
    return p, tr


def readings():
    rows = []
    for i, fm in enumerate([None] + FMS):
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            p, tr = settled(fm, sev, seed=100 + i, steps=60)
            for _ in range(25):
                tr = p.step(7.0)
                rows.append(p.measure(tr))
    return rows


def parity(rows):
    df = pd.DataFrame([{k.upper(): x for k, x in r.items()} for r in rows])
    bad = 0
    for name, expr in tc.monitor_expressions(TW):
        got = np.asarray(eval(expr, {"df": df, "np": np}), dtype=float)
        want = np.array([tc.evaluate(TW, r)[name.lower()] for r in rows], dtype=float)
        n = int((~np.isclose(got, want, rtol=1e-9, atol=1e-12)).sum())
        bad += n
        if n:
            print(f"MISMATCH {name}: {n}")
    for name, expr, sev, fm in tc.alert_rules(TW):
        got = np.asarray(eval(expr, {"df": df, "np": np}), dtype=bool)
        want = np.array([any(c["name"] == name for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]) for r in rows])
        n = int((got != want).sum())
        bad += n
        if n:
            print(f"MISMATCH rule {name}: {n}")
    print(f"parity: {len(rows)} readings, {len(tc.monitor_expressions(TW))} expressions, {len(tc.alert_rules(TW))} rules, {bad} mismatches")
    return bad


def faults():
    bad = 0
    for fm in [None] + FMS:
        p, tr = settled(fm, 1.0, seed=3)
        seen = set()
        for _ in range(20):           # every reading at full severity must show exactly the fingerprint
            tr = p.step(1.0)
            r = p.measure(tr)
            got = frozenset(c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0])
            seen.add(got)
        want = EXPECT.get(fm, set())
        ok = seen == {frozenset(want)}
        bad += not ok
        print(f"  {fm or 'healthy':24s} {'ok ' if ok else 'BAD'} {sorted(set().union(*seen))}")
    return bad


def plant_run():
    bad = 0
    for fm in FMS:
        p = Plant(TW, seed=17)
        for _ in range(300):
            p.step(1.0)
        p.set_fault(fm, 1.0, TW["failure_modes"][fm]["default_ramp_min"] * 60)
        first = {}
        for i in range(240):
            tr = p.step(1.0)
            r = p.measure(tr)
            for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]:
                first.setdefault(c["name"], i + 1)
        missing = EXPECT[fm] - set(first)
        bad += bool(missing)
        print(f"  {fm:24s} {'ok ' if not missing else 'MISSING ' + str(sorted(missing))} first step: "
              + ", ".join(f"{n} {s}" for n, s in sorted(first.items(), key=lambda x: x[1])))
    return bad


def example():
    p, tr = settled(None, 0.0, seed=11, steps=900)
    r = p.measure(tr)
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_steamturb-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()}}, indent=1), encoding="utf-8")
    print("example:", out)


if __name__ == "__main__":
    b = parity(readings())
    print("faults:")
    b += faults()
    print("plant run (240 steps of 1 s):")
    b += plant_run()
    example()
    sys.exit(1 if b else 0)
