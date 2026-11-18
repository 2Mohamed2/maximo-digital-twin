"""Checks for the AD-4901 twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings, healthy and faulted; every alert rule equals the Python conditions.
2. faults: each failure mode, injected at full severity, raises exactly its own conditions; a healthy digester raises none.
3. plant: in the live Plant, each fault (ramped in over 120 s) raises its rules within 240 simulated steps.
4. writes ../blog/_twin/example_digester-twin.json (one healthy reading and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Digester, Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]


def readings():
    d, rows = Digester(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            d.clear()
            if fm:
                d.set_fault(fm, sev)
            rows += [d.measure() for _ in range(30)]
    p = Plant(TW, seed=5)
    p.set_fault("souring", 0.7, 200)
    p.set_fault("mixing_failure", 0.8, 300)
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
    "souring": {"DIG_FOSTAC_HIGH", "DIG_PH_LOW", "DIG_CH4_LOW", "DIG_GAS_YIELD_LOW"},
    "hx_fouling": {"DIG_HX_FOULED", "DIG_TEMP_LOW"},
    "mixing_failure": {"DIG_MIXING_LOW", "DIG_STRATIFIED"},
    "grit_accumulation": {"DIG_ACTIVE_VOLUME_LOW", "DIG_SRT_LOW"},
    "foaming": {"DIG_FOAM_HIGH"},
    "h2s_high": {"DIG_H2S_HIGH"},
    "chp_degradation": {"DIG_CHP_EFF_LOW"},
}


def faults():
    bad = 0
    d = Digester(TW, seed=3)
    print("faults (full severity, 50 readings each):")
    for fm in [None] + FMS:
        d.clear()
        if fm:
            d.set_fault(fm, 1.0)
        want = EXPECT.get(fm, set())
        seen, ok = set(), True
        for _ in range(50):
            r = d.measure()
            got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            seen |= got
            ok &= got == want
        bad += not ok
        print(f"  {fm or 'healthy':20s} {'ok ' if ok else 'BAD'} {sorted(seen)}")
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
        bad += bool(missing)
        print(f"  {fm:20s} {'ok ' if not missing else 'MISSING ' + str(sorted(missing))} "
              + ", ".join(f"{n} @{s}" for n, s in sorted(first.items(), key=lambda x: x[1])))
    return bad


def example():
    d = Digester(TW, seed=11)
    r = d.measure()
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_digester-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()}}, indent=1), encoding="utf-8")
    cs, health = tc.conditions(TW, r, t)
    print("example:", out, "conditions", [c["name"] for c in cs], "health", health)


if __name__ == "__main__":
    b = parity(readings())
    b += faults()
    b += plant()
    example()
    sys.exit(1 if b else 0)
