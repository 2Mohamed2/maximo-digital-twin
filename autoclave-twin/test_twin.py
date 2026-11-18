"""Checks for the ST-6601 steam sterilizer twin.

  python test_twin.py
1. reference: IAPWS-IF97 Ts(p) and ps(T) reproduce the release's own check values (Tables 35 and 36), and Ts(3 bar abs)
   matches the steam table value 133.52 C.
2. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings, healthy and faulted; every alert rule equals the Python conditions.
3. faults: each failure mode, injected at full severity, raises exactly its own conditions; a healthy sterilizer raises none.
4. plant: the live stand-in (Plant) shows each fault's rules within 240 one-second steps.
5. writes ../blog/_twin/example_autoclave-twin.json (one healthy reading and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Sterilizer, Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]


def reference():
    bad = 0
    for p, want in ((0.1, 372.755919), (1.0, 453.035632), (10.0, 584.149488)):
        got = tc.tsat_k(p)
        ok = abs(got - want) < 1e-5
        bad += not ok
        print(f"reference: IF97 Ts({p} MPa) = {got:.6f} K (release {want}) {'ok' if ok else 'BAD'}")
    for t, want in ((300.0, 0.353658941e-2), (500.0, 0.263889776e1), (600.0, 0.123443146e2)):
        got = tc.psat_mpa(t)
        ok = abs(got / want - 1) < 1e-8
        bad += not ok
        print(f"reference: IF97 ps({t:.0f} K) = {got:.9e} MPa (release {want:.9e}) {'ok' if ok else 'BAD'}")
    got = tc.tsat_c(3.0)
    ok = abs(got - 133.52) < 0.01
    bad += not ok
    print(f"reference: Ts(3 bar abs) = {got:.3f} C (steam table 133.52) {'ok' if ok else 'BAD'}")
    return bad


def readings():
    v, rows = Sterilizer(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            v.clear()
            if fm:
                v.set_fault(fm, sev)
            rows += [v.measure() for _ in range(30)]
    p = Plant(TW, seed=5)
    p.set_fault("door_seal_wear", 0.7, 30)
    for _ in range(200):
        rows.append(p.measure(p.step(1.0)))
    return rows


def parity(rows):
    df = pd.DataFrame([{k.upper(): x for k, x in r.items()} for r in rows])
    bad = 0
    for name, expr in tc.monitor_expressions(TW):
        got = np.asarray(eval(expr, {"df": df, "np": np}), dtype=float)
        want = np.array([tc.evaluate(TW, r)[name.lower()] for r in rows], dtype=float)
        bad += int((~np.isclose(got, want, rtol=1e-9, atol=1e-9)).sum())
    for name, expr, sev, fm in tc.alert_rules(TW):
        got = np.asarray(eval(expr, {"df": df, "np": np}), dtype=bool)
        want = np.array([any(c["name"] == name for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]) for r in rows])
        bad += int((got != want).sum())
    print(f"parity: {len(rows)} readings, {len(tc.monitor_expressions(TW))} expressions, {len(tc.alert_rules(TW))} rules, {bad} mismatches")
    return bad


EXPECT = {fm: set(TW["failure_modes"][fm]["rules"]) for fm in FMS}


def faults():
    bad = 0
    v = Sterilizer(TW, seed=3)
    for fm in [None] + FMS:
        for trial in range(25):
            v.clear()
            if fm:
                v.set_fault(fm, 1.0)
            r = v.measure()
            got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            want = EXPECT.get(fm, set())
            if got != want:
                break
        ok = got == want
        bad += not ok
        print(f"  {fm or 'healthy':20s} {'ok ' if ok else 'BAD'} {sorted(got)}")
    return bad


def plant():
    bad = 0
    for fm in FMS:
        p = Plant(TW, seed=11)
        p.set_fault(fm, 1.0, TW["failure_modes"][fm]["default_ramp_min"] * 60)
        seen, first = set(), {}
        for i in range(240):
            r = p.measure(p.step(1.0))
            for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]:
                seen.add(c["name"])
                first.setdefault(c["name"], i + 1)
        ok = EXPECT[fm] <= seen
        bad += not ok
        print(f"  {fm:20s} {'ok ' if ok else 'BAD'} " + ", ".join(f"{n} @{first[n]}s" for n in sorted(EXPECT[fm]) if n in first))
    # healthy plant, including the browser warm-up (3600 steps of 2 s) and step(0)
    p = Plant(TW, seed=12)
    for _ in range(3600):
        p.step(2.0)
    noisy = set()
    for _ in range(600):
        r = p.measure(p.step(1.0))
        noisy |= {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
    p.measure(p.step(0.0))
    ok = not noisy
    bad += not ok
    print(f"  {'healthy plant':20s} {'ok ' if ok else 'BAD'} {sorted(noisy)}")
    return bad


def example():
    v = Sterilizer(TW, seed=11)
    r = v.measure()
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_autoclave-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()}}, indent=1), encoding="utf-8")
    print("example:", out, "conditions:", [c["name"] for c in tc.conditions(TW, r, t)[0]])


if __name__ == "__main__":
    b = reference()
    b += parity(readings())
    print("faults:")
    b += faults()
    print("plant (rules seen within 240 s):")
    b += plant()
    example()
    sys.exit(1 if b else 0)
