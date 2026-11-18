"""Checks for the MBR-5301 twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings, healthy and faulted; every alert rule equals the Python conditions.
2. faults: each failure mode, injected at full severity, raises exactly its own conditions; a healthy train raises none.
3. live plant: each failure mode, ramped in on the Plant used by the twin pages, raises its rules within 240 steps.
4. writes ../blog/_twin/example_mbr-twin.json (one healthy reading and the twin's numbers) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Membrane, Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]


def readings():
    e, rows = Membrane(TW, seed=7), []
    for fm in [None] + FMS:
        for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
            e.clear()
            if fm:
                e.set_fault(fm, sev)
            s = e.state()
            rows += [e.reading(s) for _ in range(40)]
    return rows


def parity(rows):
    df = pd.DataFrame([{k.upper(): x for k, x in r.items()} for r in rows])
    bad = 0
    for name, expr in tc.monitor_expressions(TW):
        got = np.asarray(eval(expr, {"df": df, "np": np}), dtype=float)
        want = np.array([tc.evaluate(TW, r)[name.lower()] for r in rows], dtype=float)
        bad += int((~np.isclose(got, want, rtol=1e-9, atol=1e-12)).sum())
    for name, expr, sev, fm in tc.alert_rules(TW):
        got = np.asarray(eval(expr, {"df": df, "np": np}), dtype=bool)
        want = np.array([any(c["name"] == name for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]) for r in rows])
        bad += int((got != want).sum())
    print(f"parity: {len(rows)} readings, {len(tc.monitor_expressions(TW))} expressions, {len(tc.alert_rules(TW))} rules, {bad} mismatches")
    return bad


EXPECT = {
    "irreversible_fouling": {"MBR_PERM_LOW", "MBR_MC_INEFFECTIVE", "MBR_IRREVERSIBLE_HIGH"},
    "poor_filterability": {"MBR_FOULING_FAST", "MBR_FILTERABILITY_POOR", "MBR_CLEAN_DUE_SOON"},
    "air_scour_low": {"MBR_SCOUR_LOW", "MBR_FOULING_FAST", "MBR_CLEAN_DUE_SOON"},
    "fibre_breakage": {"MBR_INTEGRITY_BREACH"},
    "sludging": {"MBR_MLSS_HIGH", "MBR_PERM_VERY_LOW", "MBR_TMP_HIGH", "MBR_FOULING_FAST"},
    "peak_flux": {"MBR_FLUX_HIGH"},
    "mc_skipped": {"MBR_MC_OVERDUE"},
}


def faults():
    bad = 0
    e = Membrane(TW, seed=3)
    for fm in [None] + FMS:
        e.clear()
        if fm:
            e.set_fault(fm, 1.0)
        for _ in range(20):                       # several noisy readings at the same state: the fingerprint must be stable
            r = e.measure()
            got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            if got != EXPECT.get(fm, set()):
                break
        ok = got == EXPECT.get(fm, set())
        bad += not ok
        print(f"  {fm or 'healthy':22s} {'ok ' if ok else 'BAD'} {sorted(got)}")
    return bad


def plant_run():
    bad = 0
    for fm in FMS:
        p = Plant(TW)
        for _ in range(100):                      # warm up healthy, as the pages do
            p.step(2.0)
        p.set_fault(fm, 1.0, TW["failure_modes"][fm]["default_ramp_min"] * 60)
        first = {}
        for i in range(1, 241):
            r = p.measure(p.step(1.0))
            for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]:
                first.setdefault(c["name"], i)
        miss = EXPECT[fm] - set(first)
        bad += bool(miss)
        print(f"  {fm:22s} {'ok ' if not miss else 'BAD'} " + ", ".join(f"{n}@{s}" for n, s in sorted(first.items(), key=lambda x: x[1]))
              + (f"  missing {sorted(miss)}" if miss else ""))
    p = Plant(TW)
    healthy = set()
    for _ in range(600):
        r = p.measure(p.step(1.0))
        healthy |= {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
    bad += bool(healthy)
    print(f"  healthy plant, 600 steps: {sorted(healthy) or 'no conditions'}")
    return bad


def example():
    e = Membrane(TW, seed=11)
    r = e.measure()
    t = tc.evaluate(TW, r)
    out = HERE.parent / "blog" / "_twin" / "example_mbr-twin.json"
    out.write_text(json.dumps({"reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()}}, indent=1), encoding="utf-8")
    print("example:", out)


if __name__ == "__main__":
    b = parity(readings())
    print("faults (full severity):")
    b += faults()
    print("plant run (step at which each rule first appears, 1 step = 1 s):")
    b += plant_run()
    example()
    sys.exit(1 if b else 0)
