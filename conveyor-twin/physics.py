"""A stand-in for CV-3801: route, belt, drive, take-up, idlers and belt scanner, with injectable faults.

The real conveyor sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests, the figures and the live pages. Pure Python (math, random).

The "true" conveyor follows the same ISO 5048 equation as the twin, with the faults acting on the physical causes:
  high_resistance        artificial friction coefficient f up by 30 %
  idler_bearing_failure  one idler heats up (and adds a little drag)
  lagging_wear           pulley-belt friction mu down by 45 %: the belt slips once T1/T2 > e^(mu phi)
  takeup_jammed          the carriage sticks: slack-side tension drops, the carriage no longer follows the belt stretch
  belt_stretch           permanent elongation grows from 0.03 % to 0.13 %
  splice_failure         one splice grows in length (cords pulling out of the rubber)
  mistracking            the belt runs off centre at the tail (and adds a little drag)
  load_share_imbalance   motor 1 takes 75 % of the load
"""
import math
import random


class Conveyor:
    def __init__(self, twin, seed=1):
        self.tw = twin
        d = twin["design"]
        self.d = d
        r, b, i, rs, dr, tu = d["route"], d["belt"], d["idlers"], d["resistance"], d["drive"], d["takeup"]
        self.L, self.H, self.qB, self.qRO, self.qRU = r["length_m"], r["lift_m"], b["q_b_kg_m"], i["q_ro_kg_m"], i["q_ru_kg_m"]
        self.f, self.g, self.C = rs["f"], rs["g"], (r["length_m"] + rs["L0_m"]) / r["length_m"]
        self.eta, self.mu, self.phi, self.v0 = dr["eta"], dr["mu"], math.radians(dr["wrap_deg"]), dr["speed_ms"]
        self.K, self.mcw, self.x0, self.travel = b["stiffness_n"], tu["counterweight_t"], tu["x0_m"], tu["travel_m"]
        self.demo = d["demo"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state ---------------------------------------------------------------------------------------------------
    def true_state(self, tph, amb):
        f = self.faults
        v = self.v0
        qg = tph / (3.6 * v)
        ftrue = self.f * (1 + 0.30 * f["high_resistance"] + 0.04 * f["idler_bearing_failure"] + 0.04 * f["mistracking"])
        fu = self.C * ftrue * self.L * self.g * (self.qRO + self.qRU + 2 * self.qB + qg) + qg * self.H * self.g   # N
        p = fu * v / self.eta / 1000                                                                              # kW
        share = 0.5 + 0.25 * f["load_share_imbalance"]
        t2 = self.mcw * self.g / 2 * (1 - 0.55 * f["takeup_jammed"])                                              # kN
        mu = self.mu * (1 - 0.45 * f["lagging_wear"])
        ratio = (t2 + fu / 1000) / t2
        excess = 8.0 * max(0.0, ratio / math.exp(mu * self.phi) - 1)                                              # %
        creep = fu / self.K * 100
        el = fu * self.L / (4 * self.K)
        perm = self.L * (0.0003 + 0.0010 * f["belt_stretch"])
        x = self.x0 + perm + el * (1 - f["takeup_jammed"])
        dt = 6.0 + 69.0 * f["idler_bearing_failure"]
        return {"tph": tph, "amb": amb, "v": v, "fu": fu, "power": p, "share": share, "t2": t2, "slip": creep + excess,
                "x": min(x, self.travel), "idler_dt": dt, "track_head": 8.0 + 20 * f["mistracking"],
                "track_tail": 15.0 + 115.0 * f["mistracking"], "splice": 2.0 + 24.0 * f["splice_failure"],
                "worst": 7 if f["splice_failure"] > 0.1 else 12}

    # one published message ------------------------------------------------------------------------------------------
    def reading(self, s):
        n = self.n
        v = s["v"] * (1 + n(0.0004))
        vd = v / (1 - s["slip"] / 100) * (1 + n(0.0002))
        dt = s["idler_dt"] + n(1.5)
        return {
            "tonnage_tph": round(s["tph"] * (1 + n(0.004)), 1), "belt_speed_ms": round(v, 4), "drive_pulley_speed_ms": round(vd, 4),
            "motor1_power_kw": round(s["power"] * s["share"] * (1 + n(0.008)), 1),
            "motor2_power_kw": round(s["power"] * (1 - s["share"]) * (1 + n(0.008)), 1),
            "takeup_force_kn": round(2 * s["t2"] * (1 + n(0.005)), 2), "takeup_position_m": round(s["x"] + n(0.005), 3),
            "tracking_head_mm": round(s["track_head"] + n(3.0), 1), "tracking_tail_mm": round(s["track_tail"] + n(3.0), 1),
            "idler_max_temp_c": round(s["amb"] + dt, 1), "idler_hot_count": 1 if dt > 20 else 0,
            "ambient_temp_c": round(s["amb"], 1), "splice_max_growth_mm": round(s["splice"] + n(0.3), 1),
            "splice_worst_id": s["worst"], "cord_damage_count": 3, "top_cover_min_mm": round(7.2 + n(0.05), 2), "running": 1,
        }

    def measure(self, tph=None, amb=None):
        dm = self.demo
        tph = self.rnd.uniform(dm["tph_min"], dm["tph_max"]) if tph is None else tph
        amb = dm["ambient_c"] + self.n(2.0) if amb is None else amb
        return self.reading(self.true_state(tph, amb))


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

    The crusher feed wanders between demo.tph_min and demo.tph_max (mean-reverting random walk). The take-up carriage and
    the idler temperature follow their steady state with a lag. The readings do not depend on the time of day.
    """
    TAU_X, TAU_T = 15.0, 10.0

    def __init__(self, twin, seed=3801):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.cv = Conveyor(twin, seed)
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
        self.tph = self.cv.demo["tph_mean"]
        self.lag = None

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.cv.faults[k] = f.sev
        self.t += dt * self.scale
        dm, r = self.cv.demo, self.cv.rnd
        self.tph += 0.05 * (dm["tph_mean"] - self.tph) * dt + r.gauss(0, 25.0) * math.sqrt(dt)
        self.tph = max(dm["tph_min"], min(dm["tph_max"], self.tph))
        s = self.cv.true_state(self.tph, dm["ambient_c"])
        if self.lag is None:
            self.lag = {"x": s["x"], "idler_dt": s["idler_dt"]}
        for key, tau in (("x", self.TAU_X), ("idler_dt", self.TAU_T)):
            self.lag[key] += min(1.0, dt / tau) * (s[key] - self.lag[key])
            s[key] = self.lag[key]
        return s

    def measure(self, true):
        return self.cv.reading(true)
