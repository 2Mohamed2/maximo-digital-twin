"""Checks for the DH-7101 district heating substation twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings, healthy and faulted, at outdoor temperatures from -4 to +6 °C, with and without hot water tapping; every
   alert rule equals the Python conditions.
2. faults: each failure mode, injected at full severity, raises exactly its own conditions at several outdoor
   temperatures (no tapping); a healthy substation raises none, also while hot water is tapped.
3. plant: in the live Plant, each fault (ramped in over 120 s) raises its rules within 240 simulated steps, and no rule
   outside its own list; a healthy warm-up of 3600 x 2 s raises nothing.
4. writes ../blog/_twin/example_dhsub-twin.json (one healthy reading and the twin's numbers) for the post.
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Substation, Plant

warnings.filterwarnings("ignore", category=RuntimeWarning)
HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]
OUTDOOR = (-4.0, -2.0, 0.0, 2.0, 4.0)


def readings():
    s, rows = Substation(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            s.clear()
            if fm:
                s.set_fault(fm, sev)
            for i in range(24):
                rows.append(s.measure(s.true_state(-4 + 10 * (i % 11) / 10, (0, 0, 6, 11)[i % 4])))
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


def faults():
    bad = 0
    s = Substation(TW, seed=3)
    print("faults (full severity, 20 readings at each of 5 outdoor temperatures, no tapping):")
    for fm in [None] + FMS:
        s.clear()
        if fm:
            s.set_fault(fm, 1.0)
        want = EXPECT.get(fm, set())
        seen, ok = set(), True
        for t_out in OUTDOOR:
            for taps in ((0.0,) if fm else (0.0, 6.0, 12.0)):
                for _ in range(20):
                    r = s.measure(s.true_state(t_out, taps))
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
    s = Substation(TW, seed=11)
    r = s.measure(s.true_state(0.0, 0.0))
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_dhsub-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()}}, indent=1), encoding="utf-8")
    cs, health = tc.conditions(TW, r, t)
    print("example:", out, "conditions", [c["name"] for c in cs], "health", health)


if __name__ == "__main__":
    b = parity(readings())
    b += faults()
    b += plant()
    example()
    print("TOTAL BAD", b)
    sys.exit(1 if b else 0)
