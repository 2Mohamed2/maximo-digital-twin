"""A stand-in for CL-5101: clearwell, hypochlorite dosing loop, storage tank and chlorine analysers, with injectable faults.

The real works sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the expected
values are computed in Monitor from the twin file only. This model only produces believable readings and fault fingerprints
for the tests, the figures and the live pages. Pure Python (math, random) so it also runs in the browser.

Physics of the stand-in (steady state at each reading):
  Hypochlorite strength decays first order at the tank temperature (the twin's own relation).
  The PLC paces the pump on the filtered water flow: pump setpoint = Q_in x dose_sp / S_config, and trims dose_sp so that
  outlet analyser A reads the target (limited to dose_sp_max). The real dose is dose_sp x S_true / S_config x pump ratio.
  Inlet residual = dose - immediate demand; outlet = inlet x exp(-k_b x TDT) (first-order decay over the mean residence time).
  Faults: cold water + peak outflow + low level; pump gas lock (ratio down to 0.25); old and hot hypochlorite; demand x 4.5;
  analyser A reads +0.4 mg/L; decay 0.05 -> 0.18 per hour; pH +1.4.
"""
import math
import random

from twin_calc import _k, strength


class Clearwell:
    def __init__(self, twin, seed=1):
        self.tw = twin
        self.k = _k(twin)
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.nominal()

    def nominal(self):
        k = self.k
        self.q_in, self.q_out, self.level = k["qd"], k["qd"], k["lnorm"]
        self.temp, self.ph = 12.0, 7.3
        self.age, self.t_tank, self.s_del, self.tank_pct = 12.0, 22.0, k["s0"], 70.0

    def vary(self):
        """A random but plausible state over the year (used by the parity test)."""
        r = self.rnd
        self.q_in = r.uniform(600, 1400)
        self.q_out = self.q_in * r.uniform(0.8, 1.2)
        self.level = r.uniform(2.0, 4.9)
        self.temp, self.ph = r.uniform(0.5, 28.0), r.uniform(6.5, 8.8)
        self.age, self.t_tank, self.s_del = r.uniform(0, 40), r.uniform(10, 35), r.uniform(118, 132)
        self.tank_pct = r.uniform(5, 95)

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state ---------------------------------------------------------------------------------------------------
    def true(self):
        f, k = self.faults, self.k
        c = f["cold_peak_drawdown"]
        temp = self.temp + (0.5 - self.temp) * c
        q_out = self.q_out * (1 + 0.5 * c)
        level = self.level + (2.2 - self.level) * c
        ph = self.ph + 1.4 * f["ph_high"]
        h = f["hypo_strength_loss"]
        age, t_tank = self.age + (45.0 - self.age) * h, self.t_tank + (35.0 - self.t_tank) * h
        s = strength(k, self.s_del, t_tank, age)
        demand = k["dem0"] * (1 + 3.5 * f["demand_rise"])
        kb = k["kb0"] + 0.13 * f["clearwell_decay"]
        ratio = 1 - 0.75 * f["dose_pump_gas_lock"]
        drift = 0.4 * f["analyser_drift"]
        tdt_h = k["area"] * level / q_out
        fdec = math.exp(kb * tdt_h)
        out_need = max(0.05, k["target"] - drift)
        dose_sp = (demand + out_need * fdec) * k["scfg"] / (s * ratio)
        dose_sp = max(0.3, min(k["spmax"], dose_sp))
        dose = dose_sp * s / k["scfg"] * ratio
        cl_in = max(0.02, dose - demand)
        cl_out = cl_in / fdec
        pump_sp = self.q_in * dose_sp / k["scfg"]
        return {"q_in": self.q_in, "q_out": q_out, "level": level, "temp": temp, "ph": ph, "age": age, "t_tank": t_tank,
                "s": s, "dose_sp": dose_sp, "pump_sp": pump_sp, "pump_flow": pump_sp * ratio, "cl_in": cl_in, "cl_out": cl_out,
                "drift": drift, "gas": f["dose_pump_gas_lock"], "tank_pct": self.tank_pct}

    # one published message ------------------------------------------------------------------------------------------
    def reading(self, s):
        return {
            "flow_in_m3h": round(s["q_in"] * (1 + self.n(0.003)), 1),
            "flow_out_m3h": round(s["q_out"] * (1 + self.n(0.003)), 1),
            "level_m": round(s["level"] + self.n(0.004), 3),
            "temp_c": round(s["temp"] + self.n(0.03), 2),
            "ph": round(s["ph"] + self.n(0.01), 2),
            "cl_in_mgl": round(max(0.02, s["cl_in"] + self.n(0.01)), 3),
            "cl_out_a_mgl": round(max(0.02, s["cl_out"] + s["drift"] + self.n(0.01)), 3),
            "cl_out_b_mgl": round(max(0.02, s["cl_out"] + self.n(0.01)), 3),
            "dose_sp_mgl": round(s["dose_sp"], 3),
            "pump_sp_lh": round(s["pump_sp"], 2),
            "pump_flow_lh": round(s["pump_flow"] * (1 + self.n(0.005)), 2),
            "pump_pressure_bar": round(3.0 - 0.6 * s["gas"] + self.n(0.03), 2),
            "pump_alarm": 1 if s["gas"] > 0.3 else 0,
            "hypo_level_pct": round(s["tank_pct"], 1),
            "hypo_temp_c": round(s["t_tank"] + self.n(0.05), 2),
            "hypo_age_d": round(s["age"], 2),
            "hypo_delivered_gl": round(self.s_del, 1),
        }

    def measure(self, vary=False):
        if vary:
            self.vary()
        else:
            self.nominal()
        return self.reading(self.true())


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

    The plant clock runs `demo.time_scale` times faster than real time. The filtered water flow is steady at the design
    flow; the outflow to the high-lift pumps follows the day's demand (+-15 %), so the clearwell level swings about
    0.7 m around its normal level: highest at dawn, lowest in the evening. The hypochlorite is delivered every 14 days.
    """
    DELIVERY_D = 14.0

    def __init__(self, twin, seed=5101):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.x = Clearwell(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        """Back to a healthy clearwell at once (all faults to zero)."""
        for f in self.faults.values():
            f.sev = f.target = 0.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.x.faults[k] = f.sev
        self.t += dt * self.scale
        x, k = self.x, self.x.k
        w = 2 * math.pi / 86400.0
        ph = w * self.t - 2 * math.pi * 0.3
        amp = 0.15 * k["qd"]
        x.q_in = k["qd"]
        x.q_out = k["qd"] + amp * math.sin(ph)
        x.level = k["lnorm"] + amp / (w * 3600) / k["area"] * math.cos(ph)
        day = (self.t / 86400.0) % 1.0
        x.temp = 12.0 + 0.4 * math.sin(2 * math.pi * (day - 0.4))
        x.ph = 7.3
        x.age = 8.0 + (self.t / 86400.0) % self.DELIVERY_D
        x.tank_pct = 88.0 - 5.0 * (x.age - 8.0)
        x.t_tank = 22.0 + 2.0 * math.sin(2 * math.pi * (day - 0.35))
        return x.true()

    def measure(self, true):
        return self.x.reading(true)
