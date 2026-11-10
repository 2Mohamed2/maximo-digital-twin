"""Physics model of OHL-901 (132 kV span, ACSR Drake 795 kcmil 26/7) and its weather: the stand-in for the real line.

Per step (dt real seconds; the plant clock runs `time_scale` times faster, see the twin file design.demo):
  weather   ambient day/night swing; solar irradiance follows the sun (0 at night, ~950 W/m2 at noon, passing clouds);
            wind speed rises in the afternoon with slow gusts (Ornstein-Uhlenbeck, ~20 min correlation); wind direction
            drifts; relative humidity is high at dawn, low in the afternoon
  load      transmission day profile: morning ramp, afternoon cooling peak, evening peak (~800 A)
  thermal   IEEE 738 transient heat balance m Cp dTc/dt = I^2 R(Tc) + qs - qc - qr (exact film properties; sub-steps)
  sag       true sag from the conductor temperature (change of state, the fitted cubic) + permanent creep (fault)
  sensors   line monitor (current, conductor temperature, LiDAR ground clearance), joint monitor, LiDAR vegetation
            distance, weather station (10-minute mean wind, 5-minute irradiance), insulator leakage current, aeolian
            vibration recorder
  faults    joint_hotspot heats the mid-span joint ~ I^2; conductor_creep adds permanent sag; vegetation_encroachment
            grows the trees under the span; insulator_pollution raises leakage when humid; overload_beyond_dlr pushes the
            current above today's dynamic rating; damper_loss multiplies the aeolian amplitude; sensor_fault makes the
            conductor probe read low
"""
import math
import random

import twin_calc as tc


class Fault:
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


class OU:
    """Ornstein-Uhlenbeck noise with correlation time tau (plant seconds)."""

    def __init__(self, rng, sigma, tau):
        self.rng, self.sigma, self.tau, self.x = rng, sigma, tau, 0.0

    def step(self, dt):
        a = math.exp(-dt / self.tau)
        self.x = a * self.x + self.sigma * math.sqrt(1 - a * a) * self.rng.gauss(0, 1)
        return self.x


class Plant:
    def __init__(self, twin, seed=901):
        self.twin, self.rng = twin, random.Random(seed)
        self.d = twin["design"]
        self.k = tc._k(twin)
        self.scale = float(self.d.get("demo", {}).get("time_scale", 1))
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 12 * 3600.0
        self.running, self.trip = True, 0
        self.n_wind, self.n_dir = OU(self.rng, 0.55, 1200), OU(self.rng, 25.0, 3600)
        self.n_amb, self.n_cloud, self.n_load = OU(self.rng, 0.8, 5400), OU(self.rng, 0.25, 1500), OU(self.rng, 25.0, 1800)
        self.w = self.weather()
        self.avg = {"v": self.w["v"], "g": self.w["g"], "sx": math.sin(math.radians(self.w["wd"])), "cx": math.cos(math.radians(self.w["wd"]))}
        self.I = self.demand()
        self.tc = tc.steady_tc(self.k, self.I, self.w["ta"], self.w["v"], self.w["phi"], self.w["g"])
        self.tj = self.tc + 0.5

    # ---------------------------------------------------------------- helpers
    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.trip, self.running = 0, True

    def fault_state(self):
        return {k: round(v.sev, 3) for k, v in self.faults.items()}

    def weather(self):
        h = (self.t / 3600.0) % 24
        ta = 25.0 + 8.0 * math.sin((h - 9.0) / 24 * 2 * math.pi) + self.n_amb.x
        sun = max(0.0, math.sin(math.pi * (h - 6.0) / 13.0)) if 6.0 < h < 19.0 else 0.0
        g = 950.0 * sun * max(0.25, min(1.0, 1.0 - max(0.0, self.n_cloud.x)))
        v = max(0.25, 1.3 + 1.7 * math.exp(-((h - 15.0) / 4.0) ** 2) + self.n_wind.x)
        wd = (225.0 + 35.0 * math.sin(h / 24 * 2 * math.pi) + self.n_dir.x) % 360
        rh = max(10.0, min(98.0, 52.0 - 30.0 * math.sin((h - 9.0) / 24 * 2 * math.pi) - 1.5 * self.n_amb.x))
        return {"ta": ta, "g": g, "v": v, "wd": wd, "rh": rh, "phi": tc.wind_phi(wd, self.k["az"])}

    def demand(self):
        h = (self.t / 3600.0) % 24
        gs = lambda c, w: math.exp(-((h - c) / w) ** 2)
        return max(60.0, 400.0 + 170 * gs(9.0, 2.0) + 250 * gs(15.0, 2.6) + 330 * gs(20.5, 2.2) + self.n_load.x)

    # ---------------------------------------------------------------- step
    def step(self, dt=1.0):
        f, k = self.faults, self.k
        for x in f.values():
            x.step(dt)
        pdt = dt * self.scale
        self.t += pdt
        for n in (self.n_wind, self.n_dir, self.n_amb, self.n_cloud, self.n_load):
            n.step(pdt)
        w = self.w = self.weather()
        I = self.demand()
        ov = f["overload_beyond_dlr"].sev
        if ov > 0:
            dlr = tc.ampacity(k, k["tmax"], w["ta"], w["v"], w["phi"], w["g"])
            I += ov * max(0.0, 1.25 * dlr - I)
        self.I = I
        # IEEE 738 transient, sub-steps of <= 10 plant seconds
        n = max(1, int(math.ceil(pdt / 10.0)))
        h = pdt / n
        for _ in range(n):
            q = I * I * tc.r_ac(k, self.tc) + tc.qs(k, w["g"]) - tc.qc(k, self.tc, w["ta"], w["v"], w["phi"]) - tc.qr(k, self.tc, w["ta"])
            self.tc += q / k["mcp"] * h
        # mid-span joint: a healthy compression joint runs ~0.5 K above the conductor; a failing one heats with I^2
        dj = 0.5 + 0.3 * (I / 600.0) ** 2 + 48.0 * f["joint_hotspot"].sev * (I / 600.0) ** 2
        self.tj += (self.tc + dj - self.tj) * min(1.0, pdt / 240.0)
        # sag and clearances
        sag = tc.poly(k["sag"], self.tc) + 1.6 * f["conductor_creep"].sev
        clearance = k["h_att"] - sag
        tree = 4.6 + 4.4 * f["vegetation_encroachment"].sev
        veg = clearance - tree
        # insulator leakage current: grows steeply with humidity on a polluted string
        hum = w["rh"] / 100.0
        leak = 0.35 + 1.4 * hum ** 4 + f["insulator_pollution"].sev * 34.0 * hum ** 3
        # aeolian vibration: steady winds of ~1-7 m/s, damped by the Stockbridge dampers
        aeol = math.exp(-((w["v"] - 3.0) / 1.8) ** 2)
        vib = (12.0 + 55.0 * aeol) * (1.0 + 4.2 * f["damper_loss"].sev)
        sensor = self.tc - 26.0 * f["sensor_fault"].sev
        # the weather station reports 10-minute means (WMO practice) of wind speed and direction, 5-minute irradiance
        a10, a5 = min(1.0, pdt / 600.0), min(1.0, pdt / 300.0)
        av = self.avg
        av["v"] += (w["v"] - av["v"]) * a10
        av["sx"] += (math.sin(math.radians(w["wd"])) - av["sx"]) * a10
        av["cx"] += (math.cos(math.radians(w["wd"])) - av["cx"]) * a10
        av["g"] += (w["g"] - av["g"]) * a5
        u = self.d["line"]["voltage_kv"] * (1.0 - 0.015 * I / 1000.0)
        return {"line_current_a": I, "line_voltage_kv": u, "active_power_mw": math.sqrt(3) * u * I * 0.95 / 1000.0,
                "conductor_temp_c": sensor, "joint_temp_c": self.tj, "clearance_m": clearance, "vegetation_distance_m": veg,
                "ambient_temp_c": w["ta"], "wind_speed_ms": av["v"], "wind_dir_deg": math.degrees(math.atan2(av["sx"], av["cx"])) % 360,
                "solar_wm2": av["g"],
                "humidity_pct": w["rh"], "leakage_current_ma": leak, "vibration_um": vib,
                "_true_tc": self.tc}

    def measure(self, true):
        out = {}
        for p in self.twin["telemetry"]["points"]:
            key = p["metric"]
            v = true[key]
            if p["noise"]:
                v = v + self.rng.gauss(0, p["noise"])
            if key == "wind_dir_deg":
                v %= 360
            lo, hi = p["range"]
            v = max(lo, min(hi, v))
            out[key] = round(v, 4 if abs(v) < 10 else 2)
        return out
