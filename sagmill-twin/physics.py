"""A stand-in for ML-3901: the SAG mill, its charge, liners, trunnion bearings and ring gear drive, with injectable faults.

The real mill sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the expected
values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests, the figures and the live pages.

True state -> readings:
  liner thickness from the tonnage (faster with 'liner_wear_fast'); diameter inside the liners from it;
  power from the same Austin model at the TRUE filling, ball charge and diameter, times an overload factor
  1 - 2.5 x (J - 0.34) above J = 0.34 (the charge stops lifting); bearing pressures from the true rotating mass;
  feed rate = motor power / (Wa x efficiency loss), i.e. the control system feeds the mill to its power.
Pure Python (math, random), no numpy.
"""
import math
import random

import twin_calc as tc


class Mill:
    def __init__(self, twin, seed=1):
        self.t = twin
        self.k = tc._k(twin)
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.kt = 3000.0            # tonnes since reline (kt): half way through the planned life
        self.scan_kt = 2900.0       # the last laser scan
        self.mia = self.k["mia"]
        self.j_base = self.k["j"]
        k = self.k
        d_nom = k["D"] - 2 * (k["tn"] - k["rate"] * self.kt) / 1000
        self.rpm = k["phi"] * k["cc"] / math.sqrt(d_nom)

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state --------------------------------------------------------------------------------------------------
    def wear_factor(self):
        return 1 + 0.8 * self.faults["liner_wear_fast"]

    def thickness(self, kt):
        return self.k["tn"] - self.k["rate"] * kt * self.wear_factor()

    def true_state(self, j=None):
        k, f = self.k, self.faults
        jb = k["jb"] + 0.10 * f["ball_overcharge"]
        J = (self.j_base if j is None else j) + 0.12 * f["charge_overload"] + 0.04 * f["ball_overcharge"]
        t = self.thickness(self.kt)
        D = k["D"] - 2 * t / 1000
        sg = k["sg"]
        phi = self.rpm * math.sqrt(D) / k["cc"]
        over = 1 - 2.5 * max(0.0, J - 0.34)
        p_motor = tc.austin_shell(k, D, J, jb, sg, phi) / k["eta"] * over
        v = math.pi / 4 * D ** 2 * k["L"]
        e = k["eps"]
        m_charge = v * ((1 - e) * (jb * k["rb"] + (J - jb) * sg) + e * J * tc.pulp_density(k, sg))
        m_total = k["me"] + k["mln"] * t / k["tn"] + m_charge
        w = tc.wa(k, self.mia, k["f80"])
        tph = p_motor / (k["share"] * w * (1 + 0.35 * f["lifter_profile_loss"]))
        return {"J": J, "jb": jb, "t_mm": t, "D": D, "phi": phi, "power": p_motor, "m_total": m_total, "m_charge": m_charge,
                "tph": tph, "wa": w, "mia": self.mia}

    # one published message ------------------------------------------------------------------------------------------
    def reading(self, s):
        k, f = self.k, self.faults
        p_bar = s["m_total"] / k["ct"]
        fe = p_bar / 2 * 1.0 + self.n(0.15)
        de = p_bar / 2 * (1 - 0.3 * f["pocket_leak"]) + self.n(0.15)
        oil = k["oil"] + self.n(0.2)
        scan = k["tn"] - k["rate"] * self.scan_kt * self.wear_factor() + self.n(0.5)
        return {
            "motor_power_kw": round(s["power"] * (1 + self.n(0.006)), 1),
            "mill_speed_rpm": round(self.rpm + self.n(0.005), 3),
            "pinion_vib_mm_s": round(2.0 + 6.5 * f["gear_misalignment"] + abs(self.n(0.12)), 2),
            "motor_vib_mm_s": round(1.5 + abs(self.n(0.08)), 2),
            "gear_dt_k": round(3.0 + 11.0 * f["gear_misalignment"] + self.n(0.3), 2),
            "brg_fe_pressure_bar": round(fe, 2), "brg_de_pressure_bar": round(de, 2),
            "brg_fe_temp_c": round(oil + 5.0 + 25.0 * f["bearing_lube"] + self.n(0.3), 2),
            "brg_de_temp_c": round(oil + 5.0 + self.n(0.3), 2),
            "lube_oil_temp_c": round(oil, 2),
            "feed_tph": round(s["tph"] * (1 + self.n(0.006)), 1),
            "feed_f80_mm": round(k["f80"] + self.n(1.0), 1),
            "ore_mia": round(s["mia"], 2), "ore_sg": round(k["sg"] + self.n(0.005), 3),
            "ball_charge_pct": round(s["jb"] * 100 + self.n(0.1), 2),
            "liner_kt": round(self.kt, 2), "liner_scan_mm": round(scan, 1), "liner_scan_kt": self.scan_kt,
        }

    def measure(self):
        return self.reading(self.true_state())


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

    One real second is `demo.time_scale` plant seconds. The ore hardness Mia wanders around its design value (blend
    changes); the filling follows its target with a 20 s lag; the tonnage counter grows with the feed. The clock of day
    plays no part, so the page opens in a sensible state at any hour.
    """
    TAU_S = 20.0

    def __init__(self, twin, seed=3901):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.m = Mill(twin, seed)
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
        self.J = self.m.k["j"]
        self.m.mia = self.m.k["mia"]
        self.temp_add = 0.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.m.faults[k] = f.sev
        self.t += dt * self.scale
        r, k = self.m.rnd, self.m.k
        self.m.mia += 0.01 * (k["mia"] - self.m.mia) * dt + r.gauss(0, 0.04) * math.sqrt(dt)
        self.m.mia = max(14.0, min(22.0, self.m.mia))
        a = min(1.0, dt / self.TAU_S)
        self.J += a * (k["j"] - self.J)
        s = self.m.true_state(self.J)
        self.m.kt += s["tph"] * dt * self.scale / 3600 / 1000
        return s

    def measure(self, true):
        return self.m.reading(true)
