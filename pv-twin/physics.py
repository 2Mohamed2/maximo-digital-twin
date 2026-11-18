"""A stand-in for PV-3101: weather, 24 strings, the string inverter and the weather station, with injectable faults.

The real block sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings over a
day and the fingerprints of the failure modes, for the tests, the figures and the live pages.

Weather: a clear-sky bell for the plane-of-array irradiance (sunrise 06:00, sunset 18:00), ambient 18 to 36 C.
Module temperature: Sandia module model T_m = G x exp(a + b x wind) + T_amb, open rack glass/glass a = -3.47, b = -0.0594
(King et al. 2004). Inverter: PVWatts v5 part-load efficiency, clipping at its own limit (derating curve, setpoint).
Pure Python (math, random) so it also runs in the browser.
"""
import math
import random

SAPM_A, SAPM_B = -3.47, -0.0594
OPEN_STRING, BYPASS_STRING = 7, 15            # which string the string faults hit


def _interp(x, xs, ys):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            return ys[i - 1] + (ys[i] - ys[i - 1]) * (x - xs[i - 1]) / (xs[i] - xs[i - 1])
    return ys[-1]


class Block:
    """The physical block: true state at an hour of the day, and one published reading."""

    def __init__(self, twin, seed=1):
        d = twin["design"]
        self.m, self.a, self.inv, self.ec = d["module"], d["array"], d["inverter"], d["efficiency_curve"]
        self.dr, self.ins, self.w = d["derating"], d["insulation"], d["weather"]
        self.age = d["plant"]["years_in_service"]
        self.ns = self.a["strings"]
        self.rnd = random.Random(seed)
        mm = [1 + self.rnd.gauss(0, 0.012) for _ in range(self.ns)]
        s = sum(mm) / self.ns
        self.mm = [x / s for x in mm]                  # fixed module / string mismatch, mean 1
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.setpoint = 100.0

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        """Gaussian measurement noise."""
        return self.rnd.gauss(0, s)

    # weather -------------------------------------------------------------------------------------------------------
    @staticmethod
    def weather(h):
        g = 1040.0 * max(0.0, math.sin(math.pi * (h - 6) / 12)) ** 1.2 if 6 < h < 18 else 0.0
        ta = 27 + 9 * math.sin(math.pi * (h - 9) / 12)
        ws = 2.5 + 0.9 * math.sin(math.pi * (h - 8) / 12)
        return g, ta, max(0.5, ws)

    def eta(self, p_dc):
        pdc0 = self.inv["p_ac_max_kw"] / self.ec["eta_nom"]
        z = max(p_dc, 1) / pdc0
        e = self.ec["eta_nom"] / self.ec["eta_ref"] * (-0.0162 * z - 0.0059 / z + 0.9858)
        return max(e, 0) * (1 - 0.03 * self.faults["inverter_efficiency"])

    # true state ----------------------------------------------------------------------------------------------------
    def state(self, h):
        f, m, a = self.faults, self.m, self.a
        g, ta, ws = self.weather(h)
        tm = g * math.exp(SAPM_A + SAPM_B * ws) + ta
        tc = tm + g / 1000 * self.w["cell_delta_t_c"]
        sr = 0.99 - 0.13 * f["soiling"]
        warranty = 1 - m["degradation_first_year_pct"] / 100 * min(self.age, 1) - m["degradation_annual_pct"] / 100 * max(self.age - 1, 0)
        p_str = (a["modules_per_string"] * m["pmax_w"] / 1000 * g / 1000 * (1 + m["gamma_pmax_pct_per_c"] / 100 * (tc - 25))
                 * (1 + a["rear_irradiance_ratio"] * m["bifaciality"]) * (1 - a["dc_loss_frac"]) * warranty * 0.995)
        fac = []
        for i in range(self.ns):
            x = self.mm[i] * sr * (1 - 0.12 * f["module_degradation"])
            if i + 1 == OPEN_STRING:
                x *= max(0.0, 1 - 1.25 * f["string_open"])
            if i + 1 == BYPASS_STRING:
                x *= 1 - 0.30 * f["string_bypass"]
            fac.append(x)
        p_avail = p_str * sum(fac)
        dew = 0.6 if h < 8.5 else 1.0
        riso = math.exp(math.log(self.ins["riso_typical_kohm"] * dew) * (1 - f["ground_fault"]) + math.log(20.0) * f["ground_fault"])
        running = riso >= self.ins["riso_limit_kohm"] and g > 15
        p_max = min(_interp(ta + 25 * f["inverter_cooling"], self.dr["temp_c"], self.dr["p_kw"]), self.inv["p_ac_max_kw"] * self.setpoint / 100)
        vmp = a["modules_per_string"] * m["vmp_v"] * (1 + m["beta_voc_pct_per_c"] / 100 * (tc - 25))
        voc = a["modules_per_string"] * m["voc_v"] * (1 + m["beta_voc_pct_per_c"] / 100 * (tc - 25))
        if running:
            p_dc = p_avail
            if self.eta(p_dc) * p_dc > p_max:            # clipping: the inverter moves off the MPP until AC = its limit
                for _ in range(6):
                    p_dc = p_max / max(self.eta(p_dc), 0.5)
            p_ac = self.eta(p_dc) * p_dc
            scale = p_dc / p_avail if p_avail > 0 else 0.0
            v = vmp * (1 + 0.04 * (1 - scale))
            cur = [p_str * x * scale * 1000 / v for x in fac]
        else:
            p_dc = p_ac = 0.0
            v = voc if g > 15 else 0.0
            cur = [0.0] * self.ns
        t_inv = ta + self.dr["heat_rise_full_load_k"] * p_ac / self.inv["p_ac_max_kw"] + 25 * f["inverter_cooling"] + (0 if running else 1.5)
        return {"g": g, "ta": ta, "ws": ws, "tm": tm, "tc": tc, "sr": sr, "p_avail": p_avail, "p_dc": p_dc, "p_ac": p_ac, "v": v,
                "cur": cur, "riso": riso, "running": running, "p_max": p_max, "t_inv": t_inv, "clipping": running and p_dc < p_avail - 0.5}

    # one published message -----------------------------------------------------------------------------------------
    def read(self, s):
        nz = self.n
        g_clean = s["g"] * (1 - 0.15 * self.faults["irradiance_sensor"])
        r = {
            "poa_wm2": round(max(0.0, g_clean + nz(0.003 * g_clean + 0.3)), 1),
            "poa_soiled_wm2": round(max(0.0, s["g"] * s["sr"] + nz(0.003 * s["g"] + 0.3)), 1),
            "module_temp_c": round(s["tm"] + nz(0.3), 2), "ambient_temp_c": round(s["ta"] + nz(0.2), 2), "wind_ms": round(max(0.0, s["ws"] + nz(0.3)), 2),
            "p_dc_kw": round(max(0.0, s["p_dc"] * (1 + nz(0.0015))), 2), "v_dc_v": round(s["v"] + (nz(2.0) if s["v"] else 0), 1),
            "p_ac_kw": round(max(0.0, s["p_ac"] * (1 + nz(0.001))), 2) if s["running"] else 0.0,
            "inv_running": 1 if s["running"] else 0, "inv_temp_c": round(s["t_inv"] + nz(0.4), 2), "p_max_kw": round(s["p_max"], 1),
            "riso_kohm": round(s["riso"] * (1 + nz(0.02)), 1), "setpoint_pct": self.setpoint, "years_in_service": self.age,
        }
        if s["running"] and r["p_ac_kw"] > s["p_max"]:
            r["p_ac_kw"] = round(s["p_max"], 2)                # the inverter never exceeds its own limit
        for i, c in enumerate(s["cur"]):
            r[f"i_s{i + 1:02d}_a"] = round(max(0.0, c * (1 + nz(0.004)) + (nz(0.02) if c else 0)), 3)
        return r

    def measure(self, h=10.0):
        return self.read(self.state(h))


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

    `t` is the plant clock in seconds of the day. By day it runs `demo.time_scale` times faster than real time; by night
    `night_speedup` times faster again, so the demo spends little time in the dark.
    """

    def __init__(self, twin, seed=3101):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.night = float(demo.get("night_speedup", 1))
        self.start = float(demo.get("start_hour", 10.0)) * 3600
        self.b = Block(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = self.start
        self.running, self.trip = True, 0
        self.last = None

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.t = self.start

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def hour(self):
        return (self.t / 3600.0) % 24

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.b.faults[k] = f.sev
        g = self.b.weather(self.hour())[0]
        if dt < 2.0:  # the in-browser shim warms up with 2 s steps: they must not move the clock away from the visitor's time
            self.t += dt * self.scale * (1 if g > 0 else self.night)
        s = self.b.state(self.hour())
        self.running = s["running"]
        self.trip = 1 if s["riso"] < self.b.ins["riso_limit_kohm"] else 0
        s["hour"] = self.hour()
        s["string_fault"] = {"open": OPEN_STRING, "bypass": BYPASS_STRING}
        self.last = s
        return s

    def measure(self, true):
        return self.b.read(true)
