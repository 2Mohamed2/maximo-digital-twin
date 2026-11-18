"""A stand-in for GEN-3401: terminals, excitation, stator RTDs, air coolers, PD monitor, flux probe and bearings,
with injectable faults.

The real generator sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests, the figures and the live pages. Pure Python (math, random).
"""
import math
import random

SQ3 = math.sqrt(3)


class Generator:
    def __init__(self, twin, seed=1):
        self.tw = twin
        d = twin["design"]
        self.ra, self.el, self.th, self.pd, self.br, self.co = (d["rating"], d["electrical"], d["thermal"], d["pd"], d["bearings"], d["cooling"])
        self.xd = self.el["xd_pu"]
        pf = self.ra["pf"]
        self.e_rated = math.sqrt((1 + math.sqrt(1 - pf ** 2) * self.xd) ** 2 + (pf * self.xd) ** 2)
        self.i_rated = self.ra["s_mva"] * 1e6 / (SQ3 * self.ra["v_kv"] * 1e3)
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
    def true_state(self, p, q, v=1.0, water=None, oil=None):
        """p, q in pu of the rated MVA (the dispatch and AVR set points), v in pu."""
        f, th, el, xd = self.faults, self.th, self.el, self.xd
        water = self.co["water_in_c"] if water is None else water
        oil = self.co["oil_in_c"] if oil is None else oil
        ifr = el["if_rated_a"]
        # excitation faults change the reactive power the machine actually delivers
        q = q - (q + 0.42) * f["under_excitation"]
        ey = p * xd / v
        e = math.sqrt((v + q * xd / v) ** 2 + ey ** 2)
        if_healthy = ifr * e / self.e_rated
        if f["over_excitation"] > 0:
            if_t = if_healthy + (1.25 * ifr - if_healthy) * f["over_excitation"]
            e = if_t / ifr * self.e_rated
            q = (math.sqrt(max(e ** 2 - ey ** 2, 1e-9)) - v) * v / xd
            if_healthy = if_t
        frac = 0.0625 * f["rotor_shorted_turns"]              # 6 of 96 turns per pole at full severity
        if_a = if_healthy / (1 - frac)
        i_pu = math.sqrt(p ** 2 + q ** 2) / v
        heat = i_pu ** 2
        cold = water + th["approach0_k"] + th["approach1_k"] * heat + 14.0 * f["cooler_fouling"]
        rise = th["stator_core_k"] * v ** 2 + th["stator_cu_k"] * heat
        rotor = cold + th["rotor_rise_k"] * (if_a / ifr) ** 2
        r_f = el["rf20_ohm"] * (el["k_cu"] + rotor) / (el["k_cu"] + 20) * (1 - frac)
        bl = f["stator_vent_blockage"]
        sp = f["stator_insulation_pd"]
        bw = f["bearing_wear"]
        lp = p * self.ra["s_mva"] / self.ra["p_mw"]
        return {
            "p": p, "q": q, "v": v, "i_pu": i_pu, "if": if_a, "vf": if_a * r_f, "rotor": rotor, "water": water, "oil": oil,
            "cold": cold, "hot": cold + th["air_rise0_k"] + th["air_rise1_k"] * heat,
            "rtd_max": cold + rise + 15.0 * bl, "rtd_mean": cold + th["rtd_mean_ratio"] * rise + 2.5 * bl,
            "qm": self.pd["qm_normal_mv"] * (1 + 5.0 * sp), "qm6": self.pd["qm_normal_mv"] / 1.1 * (1 + 1.5 * sp),
            "turns": round(6 * f["rotor_shorted_turns"]),
            "brg_de": oil + self.br["metal_over_oil_k"] + self.br["load_k"] * lp + 12.0 * bw,
            "brg_nde": oil + self.br["metal_over_oil_k"] - 2.0 + self.br["load_k"] * lp,
            "vib_de": self.br["vib_normal_um"] * (1 + 2.2 * bw), "vib_nde": self.br["vib_normal_um"] * 0.9 * (1 + 0.2 * bw),
        }

    # one published message ------------------------------------------------------------------------------------------
    def reading(self, s):
        n, ra = self.n, self.ra
        qm = s["qm"] * (1 + n(0.05))
        return {
            "active_power_mw": round(s["p"] * ra["s_mva"] * (1 + n(0.002)), 2),
            "reactive_power_mvar": round(s["q"] * ra["s_mva"] + n(0.5), 2),
            "terminal_voltage_kv": round(s["v"] * ra["v_kv"] * (1 + n(0.001)), 3),
            "stator_current_a": round(s["i_pu"] * self.i_rated * (1 + n(0.002)), 1),
            "frequency_hz": round(ra["f_hz"] + n(0.01), 3),
            "field_voltage_v": round(s["vf"] * (1 + n(0.002)), 1), "field_current_a": round(s["if"] * (1 + n(0.002)), 1),
            "stator_rtd_max_c": round(s["rtd_max"] + n(0.6), 2), "stator_rtd_mean_c": round(s["rtd_mean"] + n(0.3), 2),
            "cold_air_c": round(s["cold"] + n(0.3), 2), "hot_air_c": round(s["hot"] + n(0.4), 2), "cooler_water_in_c": round(s["water"] + n(0.2), 2),
            "pd_qm_mv": round(qm, 1), "pd_qm_6mo_mv": round(s["qm6"] * (1 + n(0.05)), 1), "pd_nqn": round(qm * 0.55 * (1 + n(0.08)), 1),
            "shorted_turns": int(s["turns"]), "oil_in_c": round(s["oil"] + n(0.2), 2),
            "brg_de_temp_c": round(s["brg_de"] + n(0.5), 2), "brg_nde_temp_c": round(s["brg_nde"] + n(0.5), 2),
            "vib_de_um": round(s["vib_de"] * (1 + n(0.04)), 1), "vib_nde_um": round(s["vib_nde"] * (1 + n(0.04)), 1),
        }

    def measure(self, p=None, q=None):
        p = self.rnd.uniform(0.55, 0.80) if p is None else p
        q = self.rnd.uniform(0.25, 0.45) if q is None else q
        return self.reading(self.true_state(p, q, 1.0 + self.n(0.005), self.co["water_in_c"] + self.n(1.0), self.co["oil_in_c"] + self.n(1.0)))


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

    One real second is `demo.time_scale` plant seconds. The dispatch (P) and the AVR reactive set point (Q) follow slow
    mean-reverting random walks; temperatures follow their steady state with a short lag. No time-of-day dependence.
    """
    TAU_S = 3.0
    KEYS = ("cold", "hot", "rtd_max", "rtd_mean", "rotor", "brg_de", "brg_nde")

    def __init__(self, twin, seed=3401):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.pm = float(demo.get("p_mean_pu", 0.7))
        self.qm = float(demo.get("q_mean_pu", 0.33))
        self.g = Generator(twin, seed)
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
        self.p, self.q = self.pm, self.qm
        self.temps = None

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.g.faults[k] = f.sev
        self.t += dt * self.scale
        r = self.g.rnd
        self.p += 0.02 * (self.pm - self.p) * dt + r.gauss(0, 0.006) * math.sqrt(dt)
        self.q += 0.05 * (self.qm - self.q) * dt + r.gauss(0, 0.006) * math.sqrt(dt)
        self.p = max(0.55, min(0.80, self.p))
        self.q = max(0.25, min(0.45, self.q))
        co = self.g.co
        s = self.g.true_state(self.p, self.q, 1.0, co["water_in_c"] + 0.5 * math.sin(self.t / 7200.0), co["oil_in_c"])
        if self.temps is None:
            self.temps = {k: s[k] for k in self.KEYS}
        a = min(1.0, dt / self.TAU_S)
        for k in self.KEYS:
            self.temps[k] += a * (s[k] - self.temps[k])
            s[k] = self.temps[k]
        el = self.g.el
        # field voltage follows the lagged rotor temperature (resistance)
        frac = 0.0625 * self.g.faults["rotor_shorted_turns"]
        s["vf"] = s["if"] * el["rf20_ohm"] * (el["k_cu"] + s["rotor"]) / (el["k_cu"] + 20) * (1 - frac)
        self.running = True
        return s

    def measure(self, true):
        return self.g.reading(true)
