"""Checks for the QC-5801 twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings, healthy and faulted, and on readings from the live Plant through whole moves; every alert rule equals the
   Python conditions.
2. faults: each failure mode, injected at full severity, raises exactly its own conditions; a healthy crane raises none.
3. plant: the live Plant (used by the twin pages) shows each fault's rules within 240 one-second steps, and none when healthy.
4. writes ../blog/_twin/example_stscrane-twin.json (one healthy reading and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Crane, Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]

# rules at full severity (the twin file lists these first, then the ones that show on the way there)
FULL = {
    "brake_drag": {"STS_HOIST_POWER_HIGH", "STS_BRAKE_SLOW"},
    "brake_pad_wear": {"STS_BRAKE_PAD_LOW"},
    "rope_wear": {"STS_ROPE_DISCARD", "STS_ROPE_LIFE"},
    "twistlock_faults": {"STS_TWISTLOCK_FAULTS", "STS_MOVES_LOW"},
    "trolley_wheel_wear": {"STS_TROLLEY_WEAR_RATE", "STS_TROLLEY_WHEEL_MIN"},
    "snag_overload": {"STS_SNAG", "STS_OVERLOAD"},
    "wind_operation": {"STS_WIND_LIMIT"},
}
ANY = {fm: set(TW["failure_modes"][fm]["rules"]) for fm in FMS}


def readings():
    c, rows = Crane(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            c.clear()
            if fm:
                c.set_fault(fm, sev)
            rows += [c.measure() for _ in range(40)]
    p = Plant(TW, seed=5)
    for i in range(800):                       # plant readings through many moves with ramping faults
        if i == 200:
            p.set_fault("brake_drag", 1.0, 60)
        if i == 450:
            p.clear_faults(30)
            p.set_fault("twistlock_faults", 1.0, 60)
        rows.append(p.measure(p.step(1.0)))
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


def faults():
    bad = 0
    c = Crane(TW, seed=3)
    for fm in [None] + FMS:
        c.clear()
        if fm:
            c.set_fault(fm, 1.0)
        seen = set()
        for _ in range(50):                    # every reading must give exactly the expected set
            r = c.measure()
            got = {x["name"] for x in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            if got != FULL.get(fm, set()):
                seen = got | {"!"}
                break
        ok = not seen
        bad += not ok
        print(f"  {fm or 'healthy':20s} {'ok ' if ok else 'BAD'} {sorted(FULL.get(fm, set())) if ok else sorted(seen)}")
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
        ok = FULL.get(fm, set()) <= seen and not (seen - ANY.get(fm, set()))
        bad += not ok
        print(f"  plant {fm or 'healthy':20s} {'ok ' if ok else 'BAD'} " + ", ".join(f"{k} @{v}s" for k, v in sorted(first.items(), key=lambda x: x[1])))
    return bad


def example():
    c = Crane(TW, seed=11)
    r = c.measure()
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_stscrane-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()},
                               "stand_in": {"km_mix": c.km, "struct_per_move": c.struct_per_move}}, indent=1), encoding="utf-8")
    print("example:", out)


if __name__ == "__main__":
    b = parity(readings())
    print("faults:")
    b += faults()
    print("plant:")
    b += plant()
    example()
    sys.exit(1 if b else 0)
