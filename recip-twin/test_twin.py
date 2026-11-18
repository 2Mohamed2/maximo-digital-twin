"""Checks for the K-2201 twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings, healthy and faulted; every alert rule equals the Python conditions.
2. faults: each failure mode, injected at full severity, raises exactly its own conditions; a healthy compressor raises none.
3. plant: the live Plant (used by the twin pages) shows each fault's rules within 240 one-second steps, and none when healthy.
4. writes ../blog/_twin/example_recip-twin.json (one healthy reading and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Compressor, Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]


def readings():
    c, rows = Compressor(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            c.clear()
            if fm:
                c.set_fault(fm, sev)
            rows += [c.measure() for _ in range(30)]
    p = Plant(TW, seed=5)
    for i in range(400):                       # plant readings with slow process wander and ramping faults
        if i == 100:
            p.set_fault("discharge_pressure_high", 1.0, 60)
        if i == 250:
            p.clear_faults(30)
            p.set_fault("suction_valve_leak", 1.0, 60)
        rows.append(p.measure(p.step(30.0)))
    return rows


def parity(rows):
    df = pd.DataFrame([{k.upper(): x for k, x in r.items()} for r in rows])
    bad = 0
    for name, expr in tc.monitor_expressions(TW):
        got = np.asarray(eval(expr, {"df": df, "np": np}), dtype=float)
        want = np.array([tc.evaluate(TW, r)[name.lower()] for r in rows], dtype=float)
        nb = int((~np.isclose(got, want, rtol=1e-9, atol=1e-9)).sum())
        bad += nb
        if nb:
            print(f"MISMATCH {name}: {nb}")
    for name, expr, sev, fm in tc.alert_rules(TW):
        got = np.asarray(eval(expr, {"df": df, "np": np}), dtype=bool)
        want = np.array([any(c["name"] == name for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]) for r in rows])
        nb = int((got != want).sum())
        bad += nb
        if nb:
            print(f"MISMATCH rule {name}: {nb}")
    print(f"parity: {len(rows)} readings, {len(tc.monitor_expressions(TW))} expressions, {len(tc.alert_rules(TW))} rules, {bad} mismatches")
    return bad


EXPECT = {fm: set(TW["failure_modes"][fm]["rules"]) for fm in FMS}


def faults():
    bad = 0
    c = Compressor(TW, seed=3)
    for fm in [None] + FMS:
        c.clear()
        if fm:
            c.set_fault(fm, 1.0)
        seen = set()
        for _ in range(20):                    # every one of 20 readings must give exactly the expected set
            r = c.measure()
            got = {x["name"] for x in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            want = EXPECT.get(fm, set())
            if got != want:
                seen = got
                break
        ok = not seen
        bad += not ok
        print(f"  {fm or 'healthy':24s} {'ok ' if ok else 'BAD'} {sorted(EXPECT.get(fm, set())) if ok else sorted(seen)}")
    return bad


def plant():
    bad = 0
    for fm in [None] + FMS:
        p = Plant(TW, seed=11)
        for _ in range(30):
            p.step(1.0)
        if fm:
            p.set_fault(fm, 1.0, TW["failure_modes"][fm]["default_ramp_min"] * 60)
        seen, first = set(), {}
        for i in range(240):
            m = p.measure(p.step(1.0))
            for x in tc.conditions(TW, m, tc.evaluate(TW, m))[0]:
                seen.add(x["name"])
                first.setdefault(x["name"], i + 1)
        want = EXPECT.get(fm, set())
        ok = want <= seen and not (seen - want - {"RECIP_ROD_LOAD_LIMIT"} if fm == "discharge_pressure_high" else seen - want)
        bad += not ok
        print(f"  plant {fm or 'healthy':24s} {'ok ' if ok else 'BAD'} " + ", ".join(f"{k} @{v}s" for k, v in sorted(first.items(), key=lambda x: x[1])))
    return bad


def example():
    c = Compressor(TW, seed=11)
    r = c.measure()
    t = tc.evaluate(TW, r)
    rev = {}
    for i in (1, 2):
        cur = tc.pin_load_curve(TW, i, r[f"ps{i}_barg"], r[f"pd{i}_barg"])
        deg, pct = tc.reversal(cur)
        rev[f"s{i}"] = {"deg": deg, "pct": round(pct, 3), "max_comp_kn": round(max(x[3] for x in cur), 3), "max_tens_kn": round(-min(x[3] for x in cur), 3)}
    out = HERE.parent / "blog" / "_twin" / "example_recip-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()}, "reversal": rev}, indent=1), encoding="utf-8")
    print("example:", out, rev)


if __name__ == "__main__":
    b = parity(readings())
    print("faults:")
    b += faults()
    print("plant:")
    b += plant()
    example()
    sys.exit(1 if b else 0)
