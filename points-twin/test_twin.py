"""Checks for the PM-5501 point machine twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   throws, healthy and faulted, warm and frosty; every alert rule equals the Python conditions.
2. faults: each failure mode, injected at full severity, raises exactly its own conditions; a healthy machine raises none.
3. plant: the live Plant, with each fault ramped in at its default rate, shows that fault's rules within 240 steps.
4. writes ../blog/_twin/example_points-twin.json (one healthy throw and the twin's numbers) for the post.
"""
import json
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Machine, Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]


def readings():
    m, rows, rnd = Machine(TW, seed=7), [], random.Random(3)
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            m.clear()
            if fm:
                m.set_fault(fm, sev)
            for _ in range(40):
                m.air = rnd.uniform(-12, 38)
                rows.append(m.measure())
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


EXPECT = {
    "lubrication_loss": {"PTS_FORCE_HIGH", "PTS_ENERGY_HIGH"},
    "obstruction": {"PTS_DETECTION_LOST", "PTS_CLUTCH_LIMIT", "PTS_THROW_SLOW", "PTS_ENERGY_HIGH"},
    "ice_heater": {"PTS_HEATER_FAIL", "PTS_LOCK_FORCE_HIGH"},
    "unlock_tight": {"PTS_UNLOCK_PEAK_HIGH"},
    "detector_adjust": {"PTS_DETECTION_FLICKER"},
    "supply_low": {"PTS_SUPPLY_LOW"},
    "trailed": {"PTS_TRAILED", "PTS_DETECTION_LOST"},
}


def faults():
    bad = 0
    m = Machine(TW, seed=3)
    for fm in [None] + FMS:
        m.clear()
        if fm:
            m.set_fault(fm, 1.0)
        for _ in range(20):
            r = m.measure()
            got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            if got != EXPECT.get(fm, set()):
                break
        want = EXPECT.get(fm, set())
        ok = got == want
        bad += not ok
        print(f"  {fm or 'healthy':18s} {'ok ' if ok else 'BAD'} {sorted(got)}" + ("" if ok else f" want {sorted(want)}"))
    return bad


def plant():
    bad = 0
    for fm in FMS:
        P = Plant(TW, seed=11)
        for _ in range(200):
            P.step(2.0)
        P.set_fault(fm, 1.0, TW["failure_modes"][fm]["default_ramp_min"] * 60)
        want, seen, at = EXPECT[fm], set(), None
        for i in range(240):
            tr = P.step(1.0)
            r = P.measure(tr)
            seen |= {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            if want <= seen and at is None:
                at = i + 1
        ok = at is not None
        bad += not ok
        print(f"  plant {fm:18s} {'ok ' if ok else 'BAD'} all rules by step {at}  seen {sorted(seen)}")
    P = Plant(TW, seed=11)
    for _ in range(3600):
        P.step(2.0)
    quiet = set()
    for _ in range(240):
        tr = P.step(1.0)
        r = P.measure(tr)
        quiet |= {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
    bad += bool(quiet)
    print(f"  plant healthy            {'ok ' if not quiet else 'BAD'} {sorted(quiet)}")
    return bad


def example():
    m = Machine(TW, seed=11)
    m.air = 14.0
    m.measure()
    r = m.measure()
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_points-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()}}, indent=1), encoding="utf-8")
    print("example:", out)


if __name__ == "__main__":
    b = parity(readings())
    print("faults:")
    b += faults()
    print("plant:")
    b += plant()
    example()
    sys.exit(1 if b else 0)
