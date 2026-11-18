"""A stand-in for BP-5001: the sludge feed, the polymer dosing, the belt filter press, its belts and wash system, with
injectable faults.

The real device sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests, the figures and the live pages.

True state: the polymer that really reaches the sludge (active dose) sets the cake dry solids through the dose-response
curve of twin_calc; capture sets the solids that leave with the filtrate; the filtrate flow closes the water balance
    Qe = Qf + Qpolymer + Qwash - cake / rho
A weak make-down lowers the active dose while the dosing pump (and so the measured dose) stays the same: that is the gap
the twin sees.
"""
import math
import random

import twin_calc as tc


class BeltPress:
    def __init__(self, twin, seed=1):
        self.twin = twin
        d = twin["design"]
        self.k = tc._k(twin)
        self.d = d
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.hours = d["belts"]["hours_start"]
        self.feed_ds = d["sludge"]["feed_ds_pct"]

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state -------------------------------------------------------------------------------------------------------
    def state(self):
        k, f, d = self.k, self.faults, self.d
        qf = d["operation"]["feed_flow_m3h"] * (1 + 1.18 * f["feed_overload"])
        sf = self.feed_ds
        ds = qf * sf * 10
        dose_set = d["polymer"]["dose_design_kg_t"] * (1 + 0.8 * f["polymer_overdose"])
        poly_kgh = dose_set * ds / 1000                                       # flow-paced dosing on dry solids
        qp_lph = poly_kgh / (k["conc"] / 100)
        dose_active = dose_set * (1 - 0.6 * f["polymer_weak"])
        t_up = k["tset"] - 2.2 * f["tension_low"]
        t_lo = k["tset"]
        sr = ds / k["scap"]
        cake = tc.cake_expected(k, dose_active, min(t_up, t_lo), sr) - 4.5 * f["wash_nozzle_blinding"]
        cap = (d["capture"]["capture_design_pct"] - 11.5 * f["polymer_weak"] - 10.0 * f["belt_wear"]
               - 3.5 * f["feed_overload"] - 2.0 * f["wash_nozzle_blinding"])
        pw = k["pw0"] - 3.5 * f["wash_pressure_low"]
        qw = k["qw0"] * math.sqrt(pw / k["pw0"]) * (1 - 0.45 * f["wash_nozzle_blinding"])
        cake_tph = ds * cap / 100 / (cake / 100) / 1000
        qe = qf + qp_lph / 1000 + qw - cake_tph / k["rho"]
        tss = ds * (1 - cap / 100) / qe * 1000
        speed = d["belts"]["speed_mpm"] * (1 + 0.15 * f["feed_overload"])
        return {
            "qf": qf, "sf": sf, "ds": ds, "qp": qp_lph, "dose_active": dose_active, "cake": cake, "cap": cap, "qe": qe, "tss": tss,
            "pw": pw, "qw": qw, "t_up": t_up, "t_lo": t_lo, "trk_up": 3.0 + 42.0 * f["belt_mistracking"], "trk_lo": -2.0,
            "speed": speed, "kw": 2.1 * (speed / d["belts"]["speed_mpm"]) * (0.7 + 0.3 * min(t_up, t_lo) / k["tset"]),
            "hours": self.hours + 2500.0 * f["belt_wear"], "cake_tph": cake_tph,
        }

    # one published message ----------------------------------------------------------------------------------------------
    def reading(self, s):
        n = self.n
        return {
            "running": 1, "feed_flow_m3h": round(s["qf"] * (1 + n(0.004)), 2), "feed_ds_pct": round(s["sf"] + n(0.02), 3),
            "polymer_solution_lph": round(s["qp"] * (1 + n(0.004)), 1), "cake_ds_pct": round(s["cake"] + n(0.25), 2),
            "filtrate_flow_m3h": round(s["qe"] * (1 + n(0.005)), 2), "filtrate_tss_mgl": round(max(0.0, s["tss"] * (1 + n(0.02))), 0),
            "wash_pressure_bar": round(s["pw"] + n(0.05), 2), "wash_flow_m3h": round(s["qw"] * (1 + n(0.006)), 2),
            "tension_upper_bar": round(s["t_up"] + n(0.03), 2), "tension_lower_bar": round(s["t_lo"] + n(0.03), 2),
            "tracking_upper_mm": round(s["trk_up"] + n(1.0), 1), "tracking_lower_mm": round(s["trk_lo"] + n(1.0), 1),
            "belt_speed_mpm": round(s["speed"] + n(0.02), 2), "drive_kw": round(s["kw"] + n(0.03), 2),
            "belt_hours": round(s["hours"], 1),
        }

    def measure(self):
        return self.reading(self.state())


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

    The press runs continuously on flow-paced polymer dosing. The feed solids drift slowly (+/- 0.25 % DS over about
    half an hour of real time) as the storage tank is drawn down and refilled, so the dose and the cake move a little.
    reset() stands for a belt change: the belt wear is gone and the belt hours restart from zero.
    """

    def __init__(self, twin, seed=5001):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.p = BeltPress(twin, seed)
        self.base_ds = self.p.feed_ds
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
        """Belt change: new belts, hours from zero."""
        w = self.faults["belt_wear"]
        w.sev = w.target = 0.0
        self.p.hours = 0.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.p.faults[k] = f.sev
        self.t += dt * self.scale
        self.clock += dt
        self.p.hours += dt * self.scale / 3600
        self.p.feed_ds = self.base_ds + 0.25 * math.sin(2 * math.pi * self.clock / 1800.0)
        return self.p.state()

    def measure(self, true):
        return self.p.reading(true)
