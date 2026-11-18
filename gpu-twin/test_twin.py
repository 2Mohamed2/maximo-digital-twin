"""Checks for the GPU-5901 twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings, healthy and faulted, loaded, lightly loaded and with the stand empty; every alert rule equals the Python conditions.
2. faults: each failure mode, injected at full severity, raises exactly its own conditions; a healthy unit raises none.
3. plant: each failure mode, ramped in on the live stand-in (turnarounds running), shows its rules within 240 steps of 1 s.
4. writes ../blog/_twin/example_gpu-twin.json (one healthy reading and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import GPU, Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]


def readings():
    g, rows = GPU(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            g.clear()
            if fm:
                g.set_fault(fm, sev)
            for i in range(36):
                kva = (10, 20, 35, 55, 70, 90, 118)[i % 7]
                rows.append(g.measure(g.state(kva, 0.8 + 0.2 * (i % 5) / 4, connected=(i % 9 != 0))))
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


EXPECT = {fm: set(TW["failure_modes"][fm]["rules"]) for fm in FMS}
EXPECT["output_filter_aging"] = {"GPU_THD_LIMIT"}          # at full severity the THD is past 5 %: the limit rule replaces the 2 % one


def faults():
    bad = 0
    g = GPU(TW, seed=3)
    print("faults (full severity, 50 readings each at the nominal aircraft load):")
    for fm in [None] + FMS:
        g.clear()
        if fm:
            g.set_fault(fm, 1.0)
        want = EXPECT.get(fm, set())
        seen, ok = set(), True
        for _ in range(50):
            r = g.measure()
            got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            seen |= got
            ok &= got == want
        bad += not ok
        print(f"  {fm or 'healthy':28s} {'ok ' if ok else 'BAD'} {sorted(seen)}")
    return bad


def plant():
    bad = 0
    print("plant (fault ramped in over 60 s, 1 s steps, turnarounds running):")
    p = Plant(TW, seed=11)
    seen0 = set()
    for _ in range(600):
        r = p.measure(p.step(1.0))
        seen0 |= {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
    print(f"  {'healthy (600 s)':28s} {'ok ' if not seen0 else 'BAD'} {sorted(seen0)}")
    bad += bool(seen0)
    for fm in FMS:
        p = Plant(TW, seed=11)
        for _ in range(60):
            p.step(1.0)
        p.set_fault(fm, 1.0, 60)
        first = {}
        for i in range(240):
            r = p.measure(p.step(1.0))
            for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]:
                first.setdefault(c["name"], i + 1)
        missing = EXPECT[fm] - set(first)
        bad += bool(missing)
        print(f"  {fm:28s} {'ok ' if not missing else 'MISSING ' + str(sorted(missing))} "
              + ", ".join(f"{n} @{s}" for n, s in sorted(first.items(), key=lambda x: x[1])))
    return bad


def example():
    g = GPU(TW, seed=11)
    r = g.measure()
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_gpu-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()}}, indent=1), encoding="utf-8")
    cs, health = tc.conditions(TW, r, t)
    print("example:", out, "conditions", [c["name"] for c in cs], "health", health)


if __name__ == "__main__":
    b = parity(readings())
    b += faults()
    b += plant()
    example()
    sys.exit(1 if b else 0)
