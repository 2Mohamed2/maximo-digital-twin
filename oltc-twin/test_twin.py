"""Checks for the PT-7501 OLTC and bushing twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings, healthy and faulted; every alert rule equals the Python conditions.
2. faults: each failure mode, injected at full severity, raises exactly its own conditions; a healthy unit raises none.
3. plant: in the live Plant, each failure mode's rules appear within 240 steps of 1 s after it is injected.
4. writes ../blog/_twin/example_oltc-twin.json (one healthy reading and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Transformer, Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]


def readings():
    u, rows = Transformer(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            u.clear()
            if fm:
                u.set_fault(fm, sev)
            rows += [u.measure() for _ in range(40)]
    return rows


def parity(rows):
    df = pd.DataFrame([{k.upper(): x for k, x in r.items()} for r in rows])
    bad = 0
    for name, expr in tc.monitor_expressions(TW):
        got = np.broadcast_to(np.asarray(eval(expr, {"df": df, "np": np}), dtype=float), (len(rows),))
        want = np.array([tc.evaluate(TW, r)[name.lower()] for r in rows], dtype=float)
        bad += int((~np.isclose(got, want, rtol=1e-9, atol=1e-12)).sum())
    for name, expr, sev, fm in tc.alert_rules(TW):
        got = np.broadcast_to(np.asarray(eval(expr, {"df": df, "np": np}), dtype=bool), (len(rows),))
        want = np.array([any(c["name"] == name for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]) for r in rows])
        bad += int((got != want).sum())
    print(f"parity: {len(rows)} readings, {len(tc.monitor_expressions(TW))} expressions, {len(tc.alert_rules(TW))} rules, {bad} mismatches")
    return bad


EXPECT = {fm: set(TW["failure_modes"][fm]["rules"]) for fm in FMS}


def faults():
    bad = 0
    u = Transformer(TW, seed=3)
    for fm in [None] + FMS:
        for rep in range(20):
            u.clear()
            if fm:
                u.set_fault(fm, 1.0)
            r = u.measure()
            got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            want = EXPECT.get(fm, set())
            if got != want:
                break
        ok = got == want
        bad += not ok
        print(f"  {fm or 'healthy':22s} {'ok ' if ok else 'BAD'} {sorted(got)}")
    return bad


def plant():
    bad = 0
    for fm in FMS:
        P = Plant(TW, seed=11)
        for _ in range(600):
            P.step(2.0)
        want = EXPECT[fm]
        P.set_fault(fm, 1.0, TW["failure_modes"][fm]["default_ramp_min"] * 60)
        seen, first = set(), None
        for i in range(240):
            r = P.measure(P.step(1.0))
            got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            seen |= got
            if first is None and want <= seen:
                first = i + 1
        extra = seen - want
        ok = first is not None and not extra
        bad += not ok
        print(f"  {fm:22s} {'ok ' if ok else 'BAD'} all rules by step {first}; extra {sorted(extra)}")
    P = Plant(TW, seed=12)
    noisy = set()
    for _ in range(1800):
        r = P.measure(P.step(1.0))
        noisy |= {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
    print(f"  healthy plant, 1800 steps: {sorted(noisy) or 'no conditions'}")
    return bad + bool(noisy)


def example():
    u = Transformer(TW, seed=11)
    st = u.operating_point()
    st.update(v1=0.992, ipu=0.62, pf=0.95, amb=31.0, cab=39.0)
    vs = u.rg["setpoint_kv"] / u.tr["lv_kv"]
    st["tap"] = round(u.tp["neutral"] + (1 - st["v1"] / (vs + u.drop(st["ipu"], st["pf"]))) / u.s)
    st["motor_i"], st["op_t"] = u.last_op(st["cab"])
    r = u.reading(st)
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_oltc-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()}}, indent=1), encoding="utf-8")
    print("example:", out, "conditions:", [c["name"] for c in tc.conditions(TW, r, t)[0]])


if __name__ == "__main__":
    b = parity(readings())
    print("faults:")
    b += faults()
    print("plant (each fault injected at full severity, 240 steps of 1 s):")
    b += plant()
    example()
    sys.exit(1 if b else 0)
