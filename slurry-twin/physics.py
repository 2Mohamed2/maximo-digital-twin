"""A stand-in for SP-4101: the tailings sump, the slurry pump on its VSD, the discharge line, the gland water and the
bearings, with injectable faults.

The real device sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests, the figures and the live pages.

Operating point: the VSD holds the sump level, so over a few minutes the pump delivers what flows into the sump (the flow
set point). The speed is the one at which the pump's slurry head at that flow equals what the system asks for:
    wear x HR x s^2 (a + b Q/s + c Q^2/s^2) = static + K Q^2 + suction loss / (g SG)        s = n / n_ref
which is a quadratic in s. Wear lowers the pump's head, so the VSD speeds up to keep the flow: the speed hides the wear,
the head ratio at the live speed does not.
"""
import math
import random

import twin_calc as tc


class SlurryPump:
    def __init__(self, twin, seed=1):
        self.twin = twin
        d = twin["design"]
        self.k = tc._k(twin)
        self.p, self.s, self.ln, self.gl, self.op = d["pump"], d["slurry"], d["line"], d["gland"], d["operation"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.hours = self.op["hours_since_adjust_start"]
        self.flow = self.op["flow_setpoint_m3h"]
        self.ambient = 30.0

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state -------------------------------------------------------------------------------------------------------
    def flow_target(self):
        return self.op["flow_setpoint_m3h"] * (1 - 0.40 * self.faults["line_sanding"])

    def state(self, q=None):
        k, f, ln = self.k, self.faults, self.ln
        q = self.flow_target() if q is None else q
        sg_design = 1 + (self.s["cw_design_pct"] / 100 / k["ss"]) / (self.s["cw_design_pct"] / 100 / k["ss"] + (1 - self.s["cw_design_pct"] / 100)) * (k["ss"] - 1)
        sg = sg_design + (1.65 - sg_design) * f["density_high"]
        d50 = self.s["d50_um"]
        hr = tc.warman_hr(k, tc.cw_of_sg(k, sg), d50)
        wear = 1 - 0.20 * f["impeller_wear"]
        kf = ln["friction_k"] * (1 + 0.40 * f["line_sanding"])
        loss_kpa = 3.0 + 85.0 * f["suction_blockage"]
        h_need = ln["static_head_m"] + kf * q * q + loss_kpa / (tc.G * sg)      # slurry head the pump must give
        # wear*hr*(a s^2 + b q s + c q^2) = h_need  ->  A s^2 + B s + C = 0
        A, B, C = wear * hr * k["a"], wear * hr * k["b"] * q, wear * hr * k["c"] * q * q - h_need
        s = (-B + math.sqrt(max(B * B - 4 * A * C, 0.0))) / (2 * A)
        n = s * k["n0"]
        eff = hr * tc.water_eff(k, q, n) * (1 - 0.15 * f["impeller_wear"])
        kw = sg * tc.G * q / 3600 * h_need / max(eff, 0.05) / k["ed"]
        ps = sg * tc.G * ln["sump_level_m"] - loss_kpa
        pd = ps + sg * tc.G * h_need
        gland_p = self.gl["supply_kpa"] - 220 * f["gland_water_loss"] - 30 * f["packing_wear"]
        gland_q = self.gl["flow_nominal_lpm"] * (1 - 0.8 * f["gland_water_loss"]) + 35 * f["packing_wear"]
        return {
            "q": q, "n": n, "sg": sg, "d50": d50, "hr": hr, "kw": kw, "ps": ps, "pd": pd, "eff": eff, "h": h_need,
            "gland_p": gland_p, "gland_q": gland_q,
            "t_de": self.ambient + 22 + 40 * f["bearing_failure"], "t_nde": self.ambient + 18,
            "vib": 2.4 + 7.0 * f["bearing_failure"] + 2.0 * f["suction_blockage"],
        }

    # one published message ----------------------------------------------------------------------------------------------
    def reading(self, s):
        n = self.n
        return {
            "running": 1, "speed_rpm": round(s["n"] + n(1.0), 1), "motor_kw": round(s["kw"] * (1 + n(0.006)), 2),
            "flow_m3h": round(s["q"] * (1 + n(0.004)), 1), "density_sg": round(s["sg"] + n(0.003), 3),
            "suction_kpa": round(s["ps"] + n(1.0), 1), "discharge_kpa": round(s["pd"] + n(1.5), 1),
            "d50_um": round(s["d50"] + n(3.0), 1),
            "gland_flow_lpm": round(max(0.0, s["gland_q"] + n(0.3)), 2), "gland_kpa": round(s["gland_p"] + n(2.0), 1),
            "bearing_de_c": round(s["t_de"] + n(0.4), 1), "bearing_nde_c": round(s["t_nde"] + n(0.4), 1),
            "vibration_mms": round(max(0.2, s["vib"] + n(0.15)), 2), "ambient_c": round(self.ambient + n(0.2), 1),
            "hours_since_adjust": round(self.hours, 1),
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

    The VSD holds the sump level, so the flow follows the sump inflow with a lag of about 20 s; the speed is solved for
    that flow every step. reset() stands for an impeller / throatbush adjustment: the wear is taken up and the hours since
    the adjustment restart from zero.
    """
    TAU = 20.0

    def __init__(self, twin, seed=4101):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.p = SlurryPump(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.q = self.p.flow_target()

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        """Impeller adjustment: the gap is closed again."""
        w = self.faults["impeller_wear"]
        w.sev = w.target = 0.0
        self.p.hours = 0.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.p.faults[k] = f.sev
        self.t += dt * self.scale
        self.p.hours += dt * self.scale / 3600
        tgt = self.p.flow_target()
        self.q += (tgt - self.q) * min(1.0, dt / self.TAU)
        return self.p.state(self.q)

    def measure(self, true):
        return self.p.reading(true)
