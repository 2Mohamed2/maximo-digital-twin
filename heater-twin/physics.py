"""A stand-in for H-2401: the coil, the firebox, the burners, the stack and the instruments, with injectable faults.

The real heater sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and
fault fingerprints for the tests and the figures. Pure Python (math, random): it also runs in the browser (Pyodide).
"""
import math
import random

import twin_calc as tc

PASSES = "abcd"
OFFSET = {"a": 4.0, "b": -3.0, "c": 6.0, "d": -2.0}     # small built-in differences between the passes' hottest skin points


class Heater:
    def __init__(self, twin, seed=1):
        self.twin = twin
        self.k = tc._k(twin)
        d = twin["design"]
        self.c, self.dr = d["combustion"], d["draft"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state ------------------------------------------------------------------------------------------------------
    def true_state(self, load=1.0, ambient=None):
        k, f = self.k, self.faults
        amb = self.c["ambient_design_c"] if ambient is None else ambient
        imb = f["pass_imbalance"]
        flows = {p: k["fpass"] * load * ((1 - 0.3 * imb) if p == "c" else (1 + 0.1 * imb)) for p in PASSES}
        tin, cot = k["tin"], k["cot"]
        qa = sum(flows.values()) / 3.6 * k["cp"] * (cot - tin) / 1000
        o2 = self.c["o2_design_pct"] + 5.0 * f["excess_air_high"] - 2.2 * f["air_starvation"] - 0.8 * f["draft_loss"]
        stack = k["st_d"] + k["st_k"] * (qa / k["duty"] - 1) + 70.0 * f["convection_fouling"] + (amb - self.c["ambient_design_c"]) * 0.3
        lhv = self.c["lhv_mj_kg"]
        eff = 100 - tc.stack_loss(k, o2, stack, amb, lhv) - k["rad"]
        qf = qa / eff * 100
        fuel = qf / lhv * 3600
        flux = k["q0"] * qa / k["duty"]
        clean = cot + flux * 1000 * k["rc"]
        tmt = {p: clean + OFFSET[p] for p in PASSES}
        tmt["b"] += 200.0 * f["coking"]
        tmt["c"] += 40.0 * imb
        tmt["a"] += 70.0 * f["flame_impingement"]
        dp = {p: k["dp"] * (flows[p] / k["fpass"]) ** k["nexp"] for p in PASSES}
        dp["b"] *= 1 + 0.6 * f["coking"] ** 0.4
        return {
            "flows": flows, "tin": tin, "cot": cot, "qa": qa, "qf": qf, "eff": eff, "o2": o2, "stack": stack, "amb": amb, "lhv": lhv,
            "fuel": fuel, "tmt": tmt, "dp": dp, "clean": clean,
            "co": 15 + 1500 * f["air_starvation"] ** 2 + 30 * f["flame_impingement"],
            "draft": self.dr["arch_design_mmh2o"] + 4.0 * f["draft_loss"],
            "bridgewall": 820 + 120 * (qf / k["fired_d"] - 1) + 40 * f["air_starvation"],
            "p_burner": (k["pb"] + 1.01325) * fuel / k["fuel_d"] * (1 + 0.35 * f["flame_impingement"]) - 1.01325,
            "p_in": self.twin["design"]["process"]["inlet_pressure_barg"] * (0.97 + 0.03 * load ** 2),
        }

    # one published message ---------------------------------------------------------------------------------------------
    def measure(self, s=None):
        s = s or self.true_state()
        f = self.faults
        r = {}
        for p in PASSES:
            r[f"flow_{p}_th"] = round(s["flows"][p] * (1 + self.n(0.004)), 2)
        for p in PASSES:
            r[f"dp_{p}_bar"] = round(s["dp"][p] + self.n(0.04), 3)
        for p in PASSES:
            r[f"tmt_{p}_c"] = round(s["tmt"][p] + self.n(1.5), 1)
        r.update({
            "inlet_temp_c": round(s["tin"] + self.n(0.3), 2), "cot_c": round(s["cot"] + self.n(0.3), 2),
            "inlet_pressure_barg": round(s["p_in"] + self.n(0.05), 2),
            "fuel_flow_kgh": round(s["fuel"] * (1 - 0.08 * f["fuel_meter_drift"]) * (1 + self.n(0.004)), 1),
            "fuel_lhv_mjkg": round(s["lhv"] + self.n(0.05), 3), "fuel_pressure_barg": round(s["p_burner"] + self.n(0.01), 3),
            "o2_pct": round(max(0.2, s["o2"] + self.n(0.08)), 2), "co_ppm": round(max(0.0, s["co"] + self.n(5)), 0),
            "arch_draft_mmh2o": round(s["draft"] + self.n(0.15), 2), "bridgewall_temp_c": round(s["bridgewall"] + self.n(3), 1),
            "stack_temp_c": round(s["stack"] + self.n(1.5), 1), "ambient_temp_c": round(s["amb"] + self.n(0.3), 1),
        })
        return r


class Fault:
    """A failure mode whose severity ramps towards a target (0..1)."""
    def __init__(self):
        self.sev, self.target, self.rate = 0.0, 0.0, 0.0

    def set(self, target, ramp_s):
        self.target = max(0.0, min(1.0, target))
        self.rate = abs(self.target - self.sev) / max(ramp_s, 1.0)

    def step(self, dt):
        if self.sev < self.target:
            self.sev = min(self.target, self.sev + self.rate * dt)
        elif self.sev > self.target:
            self.sev = max(self.target, self.sev - self.rate * dt)


class Plant:
    """The live stand-in used by the twin pages (same interface as the other twins' Plant).

    The heater runs at design charge with a slow 3 % swing (demo.load_swing over demo.load_period_s real seconds) and a
    small daily ambient swing; the COT controller holds 360 °C, so the fuel follows the load and the efficiency.
    """

    def __init__(self, twin, seed=2401):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.swing = float(demo.get("load_swing", 0.03))
        self.period = float(demo.get("load_period_s", 600))
        self.h = Heater(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.clock = 0.0
        self.running, self.trip = True, 0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.clock = 0.0
        self.running, self.trip = True, 0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.h.faults[k] = f.sev
        self.t += dt * self.scale
        self.clock += dt
        load = 1 + self.swing * math.sin(2 * math.pi * self.clock / self.period)
        amb = self.h.c["ambient_design_c"] + 4 * math.sin(2 * math.pi * self.t / 86400)
        return self.h.true_state(load, amb)

    def measure(self, true):
        return self.h.measure(true)
