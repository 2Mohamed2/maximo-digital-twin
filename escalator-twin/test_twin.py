"""Checks for the ES-5601 metro escalator twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings, healthy and faulted, up and down, rated and stand-by speed; every alert rule equals the Python conditions.
2. faults: each failure mode, injected at full severity, raises exactly its expected conditions at 20 passenger flows; a
   healthy escalator raises none.
3. plant: the live Plant (used by the twin pages) shows every rule listed for each fault within 240 one-second steps,
   and a healthy plant raises nothing in 1200 s.
4. writes ../blog/_twin/example_escalator-twin.json (one healthy reading and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Escalator, Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]


def readings():
    v, rows = Escalator(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            v.clear()
            if fm:
                v.set_fault(fm, sev)
            rows += [v.measure(direction=1 if i % 4 else -1) for i in range(40)]
            rows += [v.measure(ppm=0.0) for _ in range(5)]
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


# At full severity the tiered rules (MARGIN_LOW, OUT_OF_TOL, ELONG_ALERT) have handed over to their higher tier.
EXPECT = {
    "brake_weak": {"ESC_STOP_TOO_LONG"},
    "brake_harsh": {"ESC_STOP_HARSH"},
    "handrail_slip": {"ESC_HANDRAIL_SLIP"},
    "chain_wear": {"ESC_CHAIN_WEAR_FAST", "ESC_CHAIN_ELONG_LIMIT"},
    "step_band_drag": {"ESC_DRAG_HIGH", "ESC_STEP_SAG_TRIPS"},
    "gearbox_wear": {"ESC_GEAR_OIL_HOT", "ESC_GEAR_VIB_HIGH"},
    "comb_damage": {"ESC_COMB_TRIPS"},
    "standby_disabled": {"ESC_STANDBY_UNUSED"},
}


def faults():
    bad = 0
    v = Escalator(TW, seed=3)
    for fm in [None] + FMS:
        want, nbad = EXPECT.get(fm, set()), 0
        for trial in range(20):
            v.clear()
            if fm:
                v.set_fault(fm, 1.0)
            ppm = 95 * trial / 19
            r = v.measure(ppm=ppm, direction=1 if trial % 3 else -1)
            got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            if got != want:
                nbad += 1
                print(f"  {fm or 'healthy':18s} BAD {sorted(got)} at {ppm:.0f} passengers/min")
        bad += nbad
        print(f"  {fm or 'healthy':18s} {'ok ' if not nbad else 'BAD'} {sorted(want)}")
    return bad


def plant():
    bad = 0
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
        want = set(TW["failure_modes"][fm]["rules"])
        ok = want <= set(first)
        bad += not ok
        order = ", ".join(f"{n} {first[n]} s" for n in sorted(want & set(first), key=first.get))
        extra = sorted(set(first) - want)
        print(f"  {fm:18s} {'OK     ' if ok else 'MISSING'} {order}  missing: {sorted(want - set(first))}  other: {extra}")
    p = Plant(TW, seed=13)
    seen = set()
    for _ in range(1200):
        m = p.measure(p.step(1.0))
        seen |= {c["name"] for c in tc.conditions(TW, m, tc.evaluate(TW, m))[0]}
    print(f"  healthy plant, 1200 s: {'OK' if not seen else 'BAD'} {sorted(seen)}")
    return bad + bool(seen)


def example():
    v = Escalator(TW, seed=11)
    v.rnd.seed(11)
    r = v.reading(v.vr, 48.0, 1, v.power(v.vr, 36.0, 1), v.stop(v.vr, 1800.0, 1), TW["design"]["demo"]["ambient_c"],
                  TW["design"]["usage"]["run_hours_now"], 0.30)
    r["trips_comb_24h"], r["trips_handrail_inlet_24h"], r["trips_estop_24h"] = 0, 0, 1
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_escalator-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()},
                               "conditions": tc.conditions(TW, r, t)[0]}, indent=1), encoding="utf-8")
    print("example:", out)


if __name__ == "__main__":
    b = parity(readings())
    print("faults (full severity, 20 passenger flows each):")
    b += faults()
    print("plant (first second each rule appears after the fault starts):")
    b += plant()
    example()
    sys.exit(1 if b else 0)
