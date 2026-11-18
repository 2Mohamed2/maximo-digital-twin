"""A stand-in for AHU-6401: fans, filters, rotary heat exchanger, coils, the IQlogic sequence and the office floor, with
injectable faults.

The real unit sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and
fault fingerprints for the tests and the figures. Pure Python (math, random): it also runs in the browser (Pyodide).

The unit is solved in steady state on every step (air moves through an AHU in seconds):
  1. occupancy from the time of day; DCV sets the supply flow so that the CO2 the sensor reads equals its setpoint;
  2. fan powers from the flows, filter pressure drops and the rest of the system (fan affinity laws);
  3. the IQlogic temperature sequence: heating coil, then rotor speed, then cooling coil, to hold the supply setpoint.
"""
import math
import random

import twin_calc as tc


def occupancy_fraction(hour):
    """Office floor, working day: arrive 7-9, lunch dip 12-13, leave 17-19, cleaners at night."""
    h = hour % 24
    if h < 7 or h >= 19:
        return 0.03
    if h < 9:
        return 0.03 + 0.97 * (h - 7) / 2
    if 12 <= h < 13:
        return 0.65
    if h < 17:
        return 1.0
    return 1.0 - 0.97 * (h - 17) / 2


class Unit:
    def __init__(self, twin, seed=1):
        self.twin = twin
        self.k = tc._k(twin)
        d = twin["design"]
        self.v, self.w, self.fl = d["ventilation"], d["weather"], d["filters"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    def outdoor(self, hour):
        return self.w["outdoor_mean_c"] + self.w["outdoor_swing_c"] * math.cos(2 * math.pi * (hour - 15) / 24)

    # true state ------------------------------------------------------------------------------------------------------
    def true_state(self, hour=10.5, t_out=None):
        k, f, v = self.k, self.faults, self.v
        t_out = self.outdoor(hour) if t_out is None else t_out
        people = v["persons_peak"] * occupancy_fraction(hour)
        co2_drift = -350.0 * f["co2_sensor_drift"]
        # DCV: the controller holds the CO2 it reads at the setpoint
        qs = k["g"] * people * 1e6 / (k["co2sp"] - k["co2o"] - co2_drift)
        qs = max(k["qmin"], min(k["qmax"], qs))
        co2 = k["co2o"] + k["g"] * people / qs * 1e6
        qe = qs * (1 - 0.3 * f["extract_blockage"])
        # filters and fans
        dpf_s = k["fs"] * qs ** k["n"] * (1 + 3.3 * f["filter_loading"]) * (1 - 0.7 * f["filter_bypass"])
        dpf_e = k["fe"] * qe ** k["n"]
        p_s = tc.fan_kw(k, qs, dpf_s, k["ks"]) / (1 - 0.3 * f["fan_degradation"])
        p_e = tc.fan_kw(k, qe, dpf_e, k["ke"] * (1 + 5.0 * f["extract_blockage"]))
        # temperatures and the IQlogic sequence
        t_eta = v["extract_base_c"] + v["extract_rise_c"] * people / v["persons_design"]
        eta_full = tc.eta_expected(k, qs, qe) * (1 - 0.55 * f["wheel_slip"])
        cq = k["rc"] * qs                                  # kW per K of supply air
        dt_fan = p_s / cq
        leak = 30.0 * f["heating_valve_passing"]          # kW through the closed heating valve
        target = k["sp"] - 4.0 * f["supply_temp_drift"]   # the sensor reads high, the controller holds the reading
        base = t_out + dt_fan + leak / cq
        need = cq * (target - (base + eta_full * (t_eta - t_out)))
        wheel, heat_valve, cool = 1.0, 0.0, 0.0
        if need >= 0:
            heat_valve = need
        else:
            span = eta_full * (t_eta - t_out)
            wheel = (target - base) / span if span > 0.5 else -1.0
            if wheel < 0:
                wheel = 0.0
                cool = cq * (base - target)
        t_hr = t_out + eta_full * wheel * (t_eta - t_out)
        t_sup = t_hr + dt_fan + (heat_valve + leak - cool) / cq
        return {"hour": hour, "people": people, "qs": qs, "qe": qe, "co2": co2, "co2_read": co2 + co2_drift, "dpf_s": dpf_s, "dpf_e": dpf_e,
                "p_s": p_s, "p_e": p_e, "t_out": t_out, "t_eta": t_eta, "t_hr": t_hr, "t_sup": t_sup,
                "t_sup_read": t_sup + 4.0 * f["supply_temp_drift"], "t_eha": t_eta - qs / qe * (t_hr - t_out),
                "wheel": wheel, "heat_valve_kw": heat_valve, "heat_kw": heat_valve + leak, "cool_kw": cool, "eta_full": eta_full}

    # one published message ---------------------------------------------------------------------------------------------
    def measure(self, s=None):
        s = s or self.true_state()
        k = self.k
        return {
            "supply_flow_m3s": round(s["qs"] * (1 + self.n(0.005)), 4),
            "extract_flow_m3s": round(s["qe"] * (1 + self.n(0.005)), 4),
            "supply_fan_kw": round(s["p_s"] * (1 + self.n(0.008)), 4),
            "extract_fan_kw": round(s["p_e"] * (1 + self.n(0.008)), 4),
            "supply_filter_pa": round(max(1.0, s["dpf_s"] + self.n(1.0)), 1),
            "extract_filter_pa": round(max(1.0, s["dpf_e"] + self.n(1.0)), 1),
            "t_outdoor_c": round(s["t_out"] + self.n(0.08), 2),
            "t_extract_c": round(s["t_eta"] + self.n(0.08), 2),
            "t_after_hr_c": round(s["t_hr"] + self.n(0.08), 2),
            "t_supply_c": round(s["t_sup_read"] + self.n(0.08), 2),
            "t_exhaust_c": round(s["t_eha"] + self.n(0.1), 2),
            "wheel_speed_pct": round(100 * s["wheel"], 1),
            "heating_valve_pct": round(min(100.0, 100 * s["heat_valve_kw"] / k["hcap"]), 1),
            "cooling_valve_pct": round(min(100.0, 100 * s["cool_kw"] / k["ccap"]), 1),
            "heating_kw": round(max(0.0, s["heat_kw"] * (1 + self.n(0.01)) + self.n(0.03)), 2),
            "cooling_kw": round(max(0.0, s["cool_kw"] * (1 + self.n(0.01)) + self.n(0.03)), 2),
            "co2_ppm": round(s["co2_read"] + self.n(10), 0),
            "occupancy": max(0, round(s["people"] + self.n(1.0))),
        }


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

    The plant clock `t` is seconds of the day (the page sets it to the visitor's local time): office hours fill the floor
    and the DCV raises the airflow; at night the unit runs at its minimum flow. The weather is a winter day.
    """

    def __init__(self, twin, seed=6401):
        self.twin = twin
        self.scale = float(twin["design"].get("demo", {}).get("time_scale", 1))
        self.u = Unit(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 10.5 * 3600
        self.running, self.trip = True, 0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.running, self.trip = True, 0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.u.faults[k] = f.sev
        self.t = (self.t + dt * self.scale) % 86400
        return self.u.true_state(self.t / 3600)

    def measure(self, true):
        return self.u.measure(true)
