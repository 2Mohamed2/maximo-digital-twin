"""A stand-in for HYD-3601: waterway, Francis turbine, governor, bearings and draft tube, with injectable faults.

The real unit sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the expected
values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests, the figures and the live pages. Pure Python (math, random).
"""
import math
import random


class Unit:
    def __init__(self, twin, seed=1):
        self.tw = twin
        d = twin["design"]
        self.hc, self.u, self.lv, self.ww, self.fl, self.cv, self.dt, self.br, self.gv = (
            d["hill_chart"], d["unit"], d["levels"], d["waterway"], d["flow"], d["cavitation"], d["draft_tube"], d["bearings"], d["governor"])
        self.demo = d.get("demo", {})
        self.g, self.rho = self.u["g"], self.u["rho"]
        a = math.pi * self.ww["diameter_m"] ** 2 / 4
        self.kl = (self.ww["friction_f"] * self.ww["length_m"] / self.ww["diameter_m"] + self.ww["k_minor"]) / (2 * self.g * a ** 2)
        self.ain = math.pi * self.ww["spiral_inlet_d_m"] ** 2 / 4
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    def hill(self, ned, qed):
        hc = self.hc
        dn = ned / hc["ned_bep"] - 1
        dq = qed / hc["qed_bep"] - 1 - hc["tilt"] * dn
        return hc["eta_model_max"] + hc["step_up"] - hc["a_part"] * min(dq, 0) ** 2 - hc["a_over"] * max(dq, 0) ** 2 - hc["b_speed"] * dn ** 2

    # true state ---------------------------------------------------------------------------------------------------
    def true_state(self, load_mw, cw=12.0, water_c=10.0, amb_kpa=98.9):
        f, g, rho, u = self.faults, self.g, self.rho, self.u
        D, n = u["runner_d_m"], u["speed_rpm"]
        hw = self.lv["headwater_m"]
        tw = self.lv["tailwater_m"] - 6.0 * f["low_tailwater"]
        kl = self.kl * (1 + 1.4 * f["intake_head_loss"])
        adt = self.ww["draft_outlet_m2"]
        leak = 1 + 0.08 * f["guide_vane_leakage"]
        P = max(load_mw, 1.0) * 1e6
        Q = 25.0
        for _ in range(60):
            H = hw - kl * Q * Q - tw - (Q / adt) ** 2 / (2 * g)
            sq = math.sqrt(g * H)
            ned, qed = n / 60 * D / sq, Q / (D * D * sq)
            eta = self.hill(ned, qed) - 0.04 * f["runner_wear"] - 0.003 * f["guide_vane_leakage"]
            Q = 0.5 * Q + 0.5 * P / (eta * u["eta_gen"] * rho * g * H)
        q = qed / self.hc["qed_bep"]
        gate = u["gate_bep_pct"] * q / leak
        hsp = hw - kl * Q * Q
        p_bar = (hsp - self.lv["z_spiral_m"] - (Q / self.ain) ** 2 / (2 * g)) * rho * g / 1e5
        dt = self.dt
        puls = dt["base_pct"] + dt["rope_pct"] * math.exp(-((q - dt["rope_q"]) / dt["rope_width"]) ** 2)
        br = self.br
        ld = load_mw / u["rated_mw"]
        oil = cw + br["oil_a0"] + br["oil_a1"] * ld + 15 * f["bearing_cooling_loss"]
        return {
            "load": load_mw, "ld": ld, "Q": Q, "H": H, "q": q, "eta": eta, "hw": hw, "tw": tw, "p_bar": p_bar, "wk_dp": (Q / self.fl["wk_k"]) ** 2,
            "speed": n, "gate": gate, "gate_sp": gate + 4.0 * f["governor_servo_fault"],
            "oil_bar": self.gv["oil_nominal_bar"] - 9.0 * f["governor_servo_fault"], "puls": puls, "water_c": water_c, "amb_kpa": amb_kpa,
            "cw": cw, "cw_flow": 100 - 55 * f["bearing_cooling_loss"], "tgb_oil": oil,
            "tgb_pad": oil + br["pad_b0"] + br["pad_b1"] * ld + 9 * f["guide_bearing_wear"],
            "thrust": cw + br["thrust_c0"] + br["thrust_c1"] * ld + 28 * f["bearing_cooling_loss"],
            "ggb": cw + br["ggb_d0"] + br["ggb_d1"] * ld + 12 * f["bearing_cooling_loss"],
            "runout": (br["runout0_um"] + br["runout_per_pct"] * puls) * (1 + 2.0 * f["guide_bearing_wear"]),
            "hcv": 0.8 + 0.25 * puls,
        }

    # one published message ------------------------------------------------------------------------------------------
    def reading(self, s):
        n = self.n
        return {
            "headwater_level_m": round(s["hw"] + n(0.02), 3), "tailwater_level_m": round(s["tw"] + n(0.02), 3),
            "spiral_pressure_bar": round(s["p_bar"] + n(0.006), 4), "wk_dp_kpa": round(s["wk_dp"] * (1 + n(0.003)), 3),
            "speed_rpm": round(s["speed"] * (1 + n(0.0002)), 3), "active_power_mw": round(s["load"] * (1 + n(0.002)), 3),
            "unit_state": 1, "gate_setpoint_pct": round(s["gate_sp"] + n(0.08), 2), "gate_position_pct": round(s["gate"] + n(0.08), 2),
            "gov_oil_pressure_bar": round(s["oil_bar"] + n(0.2), 2), "dt_pulsation_pct": round(s["puls"] * (1 + n(0.05)), 3),
            "water_temp_c": round(s["water_c"] + n(0.05), 2), "ambient_pressure_kpa": round(s["amb_kpa"] + n(0.05), 2),
            "tgb_oil_temp_c": round(s["tgb_oil"] + n(0.4), 2), "tgb_pad_temp_c": round(s["tgb_pad"] + n(0.4), 2),
            "thrust_pad_temp_c": round(s["thrust"] + n(0.4), 2), "ggb_pad_temp_c": round(s["ggb"] + n(0.4), 2),
            "cooling_water_flow_pct": round(s["cw_flow"] + n(1.0), 1), "cooling_water_temp_c": round(s["cw"] + n(0.1), 2),
            "shaft_runout_um": round(s["runout"] * (1 + n(0.04)), 1), "headcover_vib_mms": round(s["hcv"] * (1 + n(0.05)), 3),
        }

    def measure(self, load=None, cw=None):
        dm = self.demo
        load = self.rnd.uniform(dm.get("load_min_mw", 45), dm.get("load_max_mw", 60)) if load is None else load
        load = load * (1 - self.faults["rough_zone_operation"]) + dm.get("rough_zone_mw", 30) * self.faults["rough_zone_operation"]
        cw = dm.get("cooling_water_c", 12) + self.n(2.0) if cw is None else cw
        return self.reading(self.true_state(load, cw, dm.get("water_c", 10) + self.n(1.0), self.cv["ambient_kpa"] + self.n(0.5)))


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

    One real second is `demo.time_scale` plant seconds. Dispatch moves the load setpoint as a slow mean-reverting random
    walk between load_min_mw and load_max_mw (no time-of-day dependence); the rough zone failure mode pulls it to
    rough_zone_mw. Bearing temperatures follow their steady state with a short lag. Each measure() is one record.
    """
    TAU_S = 3.0

    def __init__(self, twin, seed=3601):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.lmean, self.lmin, self.lmax = float(demo.get("load_mean_mw", 52)), float(demo.get("load_min_mw", 45)), float(demo.get("load_max_mw", 60))
        self.rz = float(demo.get("rough_zone_mw", 30))
        self.cw0, self.wc = float(demo.get("cooling_water_c", 12)), float(demo.get("water_c", 10))
        self.un = Unit(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.reset()

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.load = self.lmean
        self.temps = None

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.un.faults[k] = f.sev
        self.t += dt * self.scale
        r = self.un.rnd
        self.load += 0.03 * (self.lmean - self.load) * dt + r.gauss(0, 0.4) * math.sqrt(dt)
        self.load = max(self.lmin, min(self.lmax, self.load))
        frz = self.faults["rough_zone_operation"].sev
        target = self.load * (1 - frz) + self.rz * frz
        s = self.un.true_state(target, self.cw0, self.wc, self.un.cv["ambient_kpa"])
        keys = ("tgb_oil", "tgb_pad", "thrust", "ggb")
        if self.temps is None:
            self.temps = {k: s[k] for k in keys}
        a = min(1.0, dt / self.TAU_S)
        for k in keys:
            self.temps[k] += a * (s[k] - self.temps[k])
            s[k] = self.temps[k]
        self.running = True
        return s

    def measure(self, true):
        return self.un.reading(true)
