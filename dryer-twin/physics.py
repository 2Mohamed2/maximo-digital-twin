"""A stand-in for PM-4301: the sheet, the four steam groups, the syphons, the vent, the hood and the instruments, with injectable faults.

The real machine sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and
fault fingerprints for the tests and the figures. Pure Python (math, random): it also runs in the browser (Pyodide).
"""
import math
import random

import twin_calc as tc

G = (1, 2, 3, 4)


def p_for_tsat(k, t_c):
    """Gauge pressure (bar g) whose saturation temperature is t_c (inverse of the steam table)."""
    return tc.interp(t_c, k["tt"], k["tp"]) - tc.P0


class Dryer:
    def __init__(self, twin, seed=1):
        self.twin = twin
        self.k = tc._k(twin)
        d = twin["design"]
        self.m, self.s, self.h = d["machine"], d["steam"], d["hood"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        k = self.k
        # the hood fans are set for the design evaporation and the design exhaust humidity
        self.exh_d = k["evap_d"] / 3600 / ((k["hum_d"] - k["hum_s"]) / 1000)

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state ------------------------------------------------------------------------------------------------------
    def true_state(self, speed_factor=1.0):
        k, f, m, s = self.k, self.faults, self.m, self.s
        speed = m["speed_mpm"] * speed_factor
        prod, fib, evap = tc.evaporation(speed, m["width_m"], m["basis_weight_gsm"], m["reel_moisture_pct"], m["press_dryness_pct"])
        p = {g: s["p_barg"][g - 1] for g in G}
        dt = {g: s["dt_surface_c"][g - 1] for g in G}
        dp = {g: s["dp_kpa"] for g in G}
        # filled fabric: to hold the reel moisture the control raises groups 3 and 4 so their surfaces run 25 K hotter
        for g in (3, 4):
            p[g] = p_for_tsat(k, tc.tsat(k, p[g]) + 25.0 * f["fabric_filling"])
        dp[3] -= 21.0 * f["low_dp"]
        dt[3] += 16.0 * f["low_dp"]
        dt[4] += 6.0 * f["syphon_wear"]
        ts = {g: tc.tsat(k, p[g]) - dt[g] for g in G}
        spread = {g: s["spread_design_k"] + (3.0 * f["low_dp"] if g == 3 else 0.0) for g in G}
        # one flooded cylinder in group 3 (of 20): 45 K colder than its neighbours
        drop = 45.0 * f["flooded_cylinder"]
        ts[3] -= drop / k["groups"][2]
        tsmin = {g: ts[g] - spread[g] for g in G}
        tsmin[3] = min(tsmin[3], ts[3] + drop / k["groups"][2] - drop)
        # steam: useful steam follows the evaporation and the latent heat at the main group pressure
        useful = evap * k["q"] / tc.hfg(k, p[3])
        vent_frac = (s["vent_design_pct"] + 1.0 * f["syphon_wear"] + 14.0 * f["vent_valve_passing"]) / 100
        total = useful / (1 - vent_frac)
        heat = {g: k["ag"][g - 1] * (ts[g] - k["tsh"]) for g in G}
        cond = {g: useful * heat[g] / sum(heat.values()) for g in G}
        bt = {g: k["bt_d"] * math.sqrt(max(dp[g], 0) / k["dp_ref"]) for g in (3, 4)}
        bt[3] *= 1 - f["low_dp"]                          # condensate seals the syphon shoes: no steam blows through
        bt[4] *= 1 + 2.5 * f["syphon_wear"]               # eroded elbows and shoes let steam bypass
        exh = self.exh_d * (1 + 0.5 * f["hood_exhaust_high"] - 0.3 * f["hood_exhaust_low"])
        sup = self.exh_d * k["ratio_d"]
        return {
            "speed": speed, "prod": prod, "evap": evap, "p": p, "dp": dp, "ts": ts, "tsmin": tsmin, "total": total,
            "vent": total * vent_frac, "cond_main": cond[3] + cond[4], "bt_main": cond[3] * bt[3] / 100 + cond[4] * bt[4] / 100,
            "exh": exh, "sup": sup, "hum": k["hum_s"] + evap / 3600 / exh * 1000,
            "pocket": self.h["pocket_humidity_gkg"] + 100.0 * f["fabric_filling"],
        }

    # one published message ---------------------------------------------------------------------------------------------
    def measure(self, s=None):
        s = s or self.true_state()
        f, m = self.faults, self.m
        r = {
            "speed_mpm": round(s["speed"] + self.n(0.3), 1),
            "basis_weight_gsm": round(m["basis_weight_gsm"] + self.n(0.3), 2),
            "reel_moisture_pct": round(m["reel_moisture_pct"] + self.n(0.08), 2),
            "press_dryness_pct": round(m["press_dryness_pct"] + self.n(0.1), 2),
            "steam_total_kgh": round(s["total"] * (1 - 0.15 * f["steam_meter_drift"]) * (1 + self.n(0.003)), 0),
            "vent_kgh": round(max(0.0, s["vent"] * (1 + self.n(0.03))), 0),
            "cond_main_kgh": round(s["cond_main"] * (1 + self.n(0.006)), 0),
            "bt_main_kgh": round(s["bt_main"] * (1 + self.n(0.01)), 0),
        }
        for g in G:
            ts = s["ts"][g] + self.n(0.3)
            r[f"p{g}_barg"] = round(s["p"][g] + self.n(0.01), 3)
            r[f"dp{g}_kpa"] = round(s["dp"][g] + self.n(0.3), 2)
            r[f"ts{g}_c"] = round(ts, 2)
            r[f"tsmin{g}_c"] = round(min(ts - 0.5, s["tsmin"][g] + (ts - s["ts"][g]) + self.n(0.4)), 2)
        r.update({
            "hood_humidity_gkg": round(s["hum"] + self.n(1.0), 1),
            "hood_exh_temp_c": round(82.0 + 0.04 * (s["hum"] - 160) + self.n(0.3), 1),
            "hood_exhaust_kgs": round(s["exh"] * (1 + self.n(0.005)), 2),
            "hood_supply_kgs": round(s["sup"] * (1 + self.n(0.005)), 2),
            "pv_air_temp_c": round(self.h["pv_air_c"] + self.n(0.4), 1),
            "pocket_humidity_gkg": round(s["pocket"] + self.n(2.0), 1),
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

    The machine runs the design grade with a slow 2 % speed swing (demo.speed_swing over demo.speed_period_s real seconds);
    the moisture control holds the reel moisture, so the evaporation and the steam follow the speed. The dryer section
    does not depend on the time of day.
    """

    def __init__(self, twin, seed=4301):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.swing = float(demo.get("speed_swing", 0.02))
        self.period = float(demo.get("speed_period_s", 600))
        self.d = Dryer(twin, seed)
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
            self.d.faults[k] = f.sev
        self.t += dt * self.scale
        self.clock += dt
        return self.d.true_state(1 + self.swing * math.sin(2 * math.pi * self.clock / self.period))

    def measure(self, true):
        return self.d.measure(true)
