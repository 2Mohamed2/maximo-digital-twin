"""Checks for the ST-4701 steam trap twin.

  python test_twin.py
1. reference: the IAPWS-IF97 saturation temperature reproduces the release's own test values (Table 36), and the Napier
   orifice equation with Cd 0.72 reproduces the US DOE Steam Tip Sheet #1 steam-loss table within 3 %.
2. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings, healthy and faulted; every alert rule equals the Python conditions.
3. faults: each failure mode, injected at full severity, raises exactly its own conditions; a healthy trap raises none.
4. plant: the live stand-in (Plant) shows each fault's rules within 240 one-second steps.
5. writes ../blog/_twin/example_steamtrap-twin.json (one healthy reading and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Trap, Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]

# US DOE Steam Tip Sheet #1 (Jan 2012), leaking trap discharge rate, lb/h: (orifice in, psig) -> lb/h
DOE = {(1 / 8, 15): 13.7, (1 / 8, 100): 52.8, (1 / 8, 150): 75.8, (1 / 8, 300): 145, (1 / 16, 150): 18.9,
       (3 / 16, 150): 170, (1 / 4, 150): 303, (3 / 8, 150): 682, (3 / 8, 300): 1303}


def reference():
    bad = 0
    for p, want in ((0.1, 372.755919), (1.0, 453.035632), (10.0, 584.149488)):
        got = tc.tsat_k(p)
        ok = abs(got - want) < 1e-5
        bad += not ok
        print(f"reference: IF97 Ts({p} MPa) = {got:.6f} K (release {want}) {'ok' if ok else 'BAD'}")
    worst = 0.0
    for (d_in, psig), lbh in DOE.items():
        kgh = tc.napier_kgh(d_in * 25.4, (psig + 14.696) / 14.503773773, 0.72)
        worst = max(worst, abs(kgh / tc.LB_KG / lbh - 1))
    ok = worst < 0.03
    bad += not ok
    print(f"reference: Napier x Cd 0.72 vs DOE table, {len(DOE)} points, worst deviation {worst * 100:.1f} % {'ok' if ok else 'BAD'}")
    return bad


def readings():
    v, rows = Trap(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            v.clear()
            if fm:
                v.set_fault(fm, sev)
            rows += [v.measure() for _ in range(30)]
    p = Plant(TW, seed=5)
    p.set_fault("disc_wear", 0.7, 30)
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
    v = Trap(TW, seed=3)
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
    return bad


def example():
    v = Trap(TW, seed=11)
    r = v.measure()
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_steamtrap-twin.json"
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
