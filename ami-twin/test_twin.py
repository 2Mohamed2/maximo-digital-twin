"""Checks for the AMI-7301 twin.

  python test_twin.py
1. parity: every Monitor expression (evaluated with pandas, as the Monitor pipeline does) equals evaluate() on simulated
   readings over whole days, healthy and faulted at several severities; every alert rule equals the Python conditions.
2. faults: each failure mode, injected at full severity at 19:30 (evening peak), raises exactly its expected rules; a healthy
   feeder raises none, at 19:30 and over a whole day.
3. live plant: each failure mode set on the Plant (the stand-in used by the live pages) shows its rules within 240 steps.
4. writes ../blog/_twin/example_ami-twin.json (one healthy 19:30 reading, the twin's numbers and the meter table) for the post.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import twin_calc as tc
from physics import Feeder, Plant

HERE = Path(__file__).parent
TW = json.load(open(next((HERE / "twin").glob("*.twin.json")), encoding="utf-8"))
FMS = [k for k in TW["failure_modes"] if not k.startswith("$")]
HOUR = 19.5


def readings():
    rows = []
    p = Plant(TW, seed=7)
    for fm in [None] + FMS:
        p.clear_faults(1)
        for _ in range(5):
            p.step(1.0)
        if fm:
            p.set_fault(fm, 1.0, 300)
        for i in range(960):                       # one plant day (960 s x 90 = 24 h)
            tr = p.step(1.0)
            if i % 8 == 0:
                rows.append(p.measure(tr))
    f = Feeder(TW, seed=5)
    for fm in [None] + FMS:
        for sev in (0.25, 0.5, 0.75, 1.0):
            f.clear()
            if fm:
                f.set_fault(fm, sev)
            for h in (2.0, 7.5, 12.0, 17.0, 19.5, 22.0):
                rows.append(f.measure(h))
    return rows


def parity(rows):
    df = pd.DataFrame([{k.upper(): x for k, x in r.items()} for r in rows])
    bad = 0
    for name, expr in tc.monitor_expressions(TW):
        got = np.asarray(eval(expr, {"df": df, "np": np}), dtype=float)
        want = np.array([tc.evaluate(TW, r)[name.lower()] for r in rows], dtype=float)
        n = int((~np.isclose(got, want, rtol=1e-9, atol=1e-9)).sum())
        bad += n
        if n:
            print(f"MISMATCH {name}: {n}")
    fired = {}
    for name, expr, sev, fm in tc.alert_rules(TW):
        got = np.asarray(eval(expr, {"df": df, "np": np}), dtype=bool)
        want = np.array([any(c["name"] == name for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]) for r in rows])
        n = int((got != want).sum())
        bad += n
        fired[name] = int(got.sum())
        if n:
            print(f"MISMATCH rule {name}: {n}")
    print(f"parity: {len(rows)} readings x {len(tc.monitor_expressions(TW))} expressions + {len(tc.alert_rules(TW))} rules, {bad} mismatches")
    print("  rule fired on", ", ".join(f"{k} {v}" for k, v in fired.items()))
    return bad


EXPECT = {
    "bypass_theft": {"AMI_LOSS_UNEXPLAINED", "AMI_TAMPER"},
    "ct_polarity": {"AMI_LOSS_NEGATIVE", "AMI_REVERSE_ENERGY"},
    "phase_mismapping": {"AMI_PHASE_MAPPING"},
    "loose_neutral": {"AMI_NEUTRAL_SHIFT", "AMI_VOLTAGE_OUT"},
    "tap_setting": {"AMI_BUS_VOLTAGE"},
    "concentrator_comms": {"AMI_READS_LOW"},
    "clock_drift": {"AMI_CLOCK_DRIFT"},
    "relay_stuck": {"AMI_RELAY_MISMATCH"},
}


def faults():
    bad = 0
    print(f"faults (full severity, {HOUR:.1f} h, 20 readings each):")
    for fm in [None] + FMS:
        f = Feeder(TW, seed=3)
        if fm:
            f.set_fault(fm, 1.0)
        want = EXPECT.get(fm, set())
        seen, ok = set(), True
        for _ in range(20):
            r = f.measure(HOUR)
            got = {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
            ok &= got == want
            seen |= got
        bad += not ok
        print(f"  {fm or 'healthy':20s} {'ok ' if ok else 'BAD'} {sorted(seen)}")
    f, day = Feeder(TW, seed=4), set()
    for i in range(0, 24 * 4):
        r = f.measure(i / 4)
        day |= {c["name"] for c in tc.conditions(TW, r, tc.evaluate(TW, r))[0]}
    print(f"  healthy, whole day   {'ok ' if not day else 'BAD'} {sorted(day)}")
    bad += bool(day)
    return bad


def plant_run():
    bad = 0
    print("live plant (fault ramps in over 120 s, 1 s steps, starts 19:00):")
    for fm in FMS:
        p = Plant(TW, seed=11)
        for _ in range(10):
            p.step(1.0)
        p.set_fault(fm, 1.0, 120)
        seen, first = set(), None
        for i in range(240):
            tr = p.step(1.0)
            m = p.measure(tr)
            names = {c["name"] for c in tc.conditions(TW, m, tc.evaluate(TW, m))[0]}
            if EXPECT[fm] <= names and first is None:
                first = i + 1
            seen |= names
        ok = first is not None
        bad += not ok
        print(f"  {fm:20s} {'ok ' if ok else 'BAD'} all rules after {first} steps (plant {p.hour():.1f} h)  seen {sorted(seen)}")
    return bad


def example():
    f = Feeder(TW, seed=11)
    st = f.state(HOUR)
    r = f.measure(HOUR, st)
    t = tc.evaluate(TW, r)
    # the same feeder with a bypass at the meter in cabinet D: the meter table used for the inspection ranking (section 9)
    g = Feeder(TW, seed=11)
    g.set_fault("bypass_theft", 1.0)
    sg = g.state(HOUR)
    rg = g.measure(HOUR, sg)
    meters = [{"id": f"M{c + 1:02d}", "node": m["node"], "v": [round(x, 2) for x in m["v"]], "i": [round(x, 2) for x in m["i_service"]],
               "pt": [round(x, 1) for x in m["p_terminal"]], "kw": round(m["p_metered"] / 1000, 3)} for c, m in enumerate(sg["meters"])]
    out = HERE.parent / "blog" / "_twin" / "example_ami-twin.json"
    out.write_text(json.dumps({"hour": HOUR, "reading": r, "twin": {k: round(x, 6) if isinstance(x, float) else x for k, x in t.items()},
                               "true": {"load_kw": round(st["load_w"] / 1000, 3), "loss_kw": round(st["loss_w"] / 1000, 3)},
                               "theft": {"reading": rg, "twin": {k: round(x, 6) for k, x in tc.evaluate(TW, rg).items()},
                                         "theft_kw": round(sg["theft_w"] / 1000, 3), "meters": meters},
                               "healthy_meters": [{"id": f"M{c + 1:02d}", "node": m["node"], "v": [round(x, 2) for x in m["v"]],
                                                   "i": [round(x, 2) for x in m["i_service"]], "pt": [round(x, 1) for x in m["p_terminal"]],
                                                   "kw": round(m["p_metered"] / 1000, 3)} for c, m in enumerate(st["meters"])]}, indent=1), encoding="utf-8")
    print("example:", out)


if __name__ == "__main__":
    b = parity(readings())
    b += faults()
    b += plant_run()
    example()
    sys.exit(1 if b else 0)
