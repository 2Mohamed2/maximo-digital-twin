"""A stand-in for ESP-2801: the well, the pump on its VSD, the motor and the downhole gauge, with injectable faults.

The real device sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests, the figures and the live pages.

Operating point: the flow Q where the pump's pressure rise equals what the well asks for,
    N x k x H(Q, f) x 0.433 SG = Pd(Q) - PIP(Q)
    Pd(Q)  = wellhead pressure + 0.433 SG x (pump depth + tubing friction(Q))      (Hazen-Williams friction)
    PIP(Q) = reservoir pressure - Q / PI - 0.433 SG x (perforations - pump depth)  (straight-line inflow)
k is 1 for a healthy pump; wear, scale, free gas and a broken shaft lower it. Solved by bisection every step.
"""
import math
import random

import twin_calc as tc


class ESP:
    def __init__(self, twin, seed=1):
        self.twin = twin
        d = twin["design"]
        self.k = tc._k(twin)
        self.w, self.fl, self.m, self.op = d["well"], d["fluid"], d["motor"], d["operation"]
        self.L = twin["twin_model"]["limits"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.freq = self.op["freq_hz"]
        self.run_days = self.op["run_days_at_start"]

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state -------------------------------------------------------------------------------------------------------
    def friction_ft(self, q):
        w = self.w
        gpm = max(q, 0.0) * 0.02917
        return w["pump_depth_ft"] * 0.2083 * (100 / w["hazen_c"]) ** 1.852 * gpm ** 1.852 / w["tubing_id_in"] ** 4.8655 / 100

    def state(self):
        k, w, fl, m, f = self.k, self.w, self.fl, self.m, self.faults
        fr = self.freq / 60
        wc = fl["water_cut_pct"]
        sg = wc / 100 * fl["sg_water"] + (1 - wc / 100) * fl["sg_oil"]
        grad = tc.GRAD * sg
        pi = w["pi_bpd_psi"] * (1 - 0.88 * f["inflow_decline"])
        gor = fl["rsb_scf_stb"] + 3000 * f["gas_interference"]
        lock = max(0.0, (f["gas_interference"] - 0.75) / 0.25)
        kmech = (1 - 0.30 * f["stage_wear"]) * (1 - 0.14 * f["scale_deposits"]) * (1 - 0.98 * f["broken_shaft"])
        tin = w["bht_f"]
        pd_of = lambda q: w["whp_psi"] + grad * (w["pump_depth_ft"] + self.friction_ft(q))
        pip_of = lambda q: max(20.0, w["reservoir_psi"] - q / pi - grad * (w["perf_depth_ft"] - w["pump_depth_ft"]))
        gvf, q = 0.0, 0.0
        for _ in range(6):                                   # free gas depends on PIP, PIP on the flow: fixed point
            kgas = 1 / (1 + (max(0.0, gvf - 10) / 12) ** 2) * (1 - 0.9 * lock)
            kk = kmech * kgas
            g = lambda qq: kk * tc.pump_head(k, qq, self.freq) * grad - (pd_of(qq) - pip_of(qq))
            lo, hi = 0.0, 3100 * fr
            if g(lo) <= 0:
                q = 0.0
            else:
                for _ in range(50):
                    mid = (lo + hi) / 2
                    lo, hi = (mid, hi) if g(mid) > 0 else (lo, mid)
                q = (lo + hi) / 2
            gvf_new = tc.gvf_pct(k, pip_of(q), gor, wc, tin)
            gvf = 0.5 * gvf + 0.5 * gvf_new
        pip, pd = pip_of(q), pd_of(q)
        q60 = q / fr
        bhp = k["N"] * tc.stage_bhp(k, q60) * fr ** 3 * sg * (1 - gvf / 100) * (1 + 0.25 * f["scale_deposits"]) * (1 - 0.8 * lock)
        bhp = (1 - f["broken_shaft"]) * bhp + f["broken_shaft"] * 0.12 * k["hp"] * fr
        kw = bhp * tc.KW / (k["eff"] * k["ceff"])
        load = kw * (k["eff"] * k["ceff"] / tc.KW) / (k["hp"] * fr) * 100
        v = q * tc.BBL_FT3 / 86400 / k["area"]
        rise = tc.motor_rise(k, load, v) * (1 + 3.0 * f["motor_cooling"])
        tm = tin + rise
        leak = self.L["leak_base_ua"] * 2 ** ((tm - self.L["leak_ref_f"]) / 18) * (1 + 30 * f["motor_insulation"])
        return {
            "q": q, "pip": pip, "pd": pd, "sg": sg, "gor": gor, "wc": wc, "gvf": gvf, "kw": kw, "load": load, "tin": tin, "tm": tm,
            "leak": leak, "vib": 0.3 + 1.3 * f["stage_wear"] + 0.15 * lock,
            "cv": 1.0 + 0.8 * max(0.0, gvf - 10) + 14 * lock,
            "starts": self.op["starts_30d_normal"] + round(10 * max(0.0, (f["gas_interference"] - 0.6) / 0.4)),
            "amps": m["rated_a"] * (0.3 + 0.7 * load / 100), "freq": self.freq,
        }

    # one published message ----------------------------------------------------------------------------------------------
    def reading(self, s):
        n = self.n
        return {
            "running": 1, "vsd_freq_hz": round(s["freq"] + n(0.02), 2), "vsd_kw": round(max(0.5, s["kw"] * (1 + n(0.006))), 2),
            "motor_current_a": round(s["amps"] * (1 + n(0.006)), 2), "current_cv_pct": round(max(0.2, s["cv"] + n(0.15)), 2),
            "pip_psi": round(s["pip"] + n(2.0), 1), "pd_psi": round(s["pd"] + n(2.0), 1),
            "intake_temp_f": round(s["tin"] + n(0.3), 1), "motor_temp_f": round(s["tm"] + n(0.5), 1),
            "vibration_g": round(max(0.02, s["vib"] + n(0.03)), 3), "leakage_ua": round(max(0.05, s["leak"] * (1 + n(0.03))), 2),
            "whp_psi": round(self.w["whp_psi"] + n(1.5), 1), "casing_psi": round(self.w["casing_psi"] + n(1.0), 1),
            "flow_bpd": round(max(0.0, s["q"] * (1 + n(0.008))), 1), "water_cut_pct": round(s["wc"], 1), "gor_scf_stb": round(s["gor"]),
            "run_days": round(self.run_days, 2), "starts_30d": s["starts"],
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

    The ESP runs at its frequency set point. Every step solves the operating point with the faults as they ramp; the run
    days follow the demo clock.
    """

    def __init__(self, twin, seed=2801):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.e = ESP(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.base_days = self.e.run_days

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.e.freq = self.twin["design"]["operation"]["freq_hz"]

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.e.faults[k] = f.sev
        self.t += dt * self.scale
        self.e.run_days = self.base_days + self.t / 86400
        return self.e.state()

    def measure(self, true):
        return self.e.reading(true)
