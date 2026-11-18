"""A stand-in for WTG-3001: rotor, drivetrain, cooling, CMS and oil particle counter, with injectable faults.

The real turbine sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable 10-minute SCADA and
CMS readings and fault fingerprints for the tests, the figures and the live pages. Pure Python (math, random).
"""
import math
import random


def interp(x, xp, fp):
    if x < xp[0] or x > xp[-1]:
        return 0.0
    for i in range(len(xp) - 1):
        if x <= xp[i + 1]:
            return fp[i] + (x - xp[i]) * (fp[i + 1] - fp[i]) / (xp[i + 1] - xp[i])
    return fp[-1]


class Turbine:
    def __init__(self, twin, seed=1):
        self.tw = twin
        d = twin["design"]
        self.ro, self.pc, self.dt, self.th, self.vb, self.site = (d["rotor"], d["power_curve"], d["drivetrain"], d["thermal"],
                                                                  d["vibration"], d["site"])
        self.R0 = d["density"]["R0"]
        dt = self.dt
        self.ratio = (1 + dt["z_ring"] / dt["z_sun"]) * dt["z_wheel2"] / dt["z_pinion2"] * dt["z_wheel3"] / dt["z_pinion3"]
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
    def true_state(self, wind, amb, pressure):
        f, th, vb = self.faults, self.th, self.vb
        rho = pressure * 100 / (self.R0 * (amb + 273.15))
        vn = wind * (rho / self.pc["rho_ref"]) ** (1 / 3)
        yaw = 25.0 * f["yaw_misalignment"]
        veff = vn * math.cos(math.radians(yaw)) * (1 - 0.25 * f["rotor_performance_loss"]) ** (1 / 3)
        p = interp(veff, self.pc["wind_ms"], self.pc["power_kw"]) if wind <= self.ro["cut_out_ms"] else 0.0
        ld = p / self.ro["rated_kw"]
        rpm = self.dt["tsr_opt"] * veff / (self.ro["diameter_m"] / 2) * 60 / (2 * math.pi)
        rpm = max(self.ro["rotor_rpm_min"], min(self.ro["rotor_rpm_nominal"], rpm))
        oil = amb + th["oil_a0"] + th["oil_a1"] * ld + f["oil_cooler_fouling"] * (10 + 25 * ld)
        bump = 1 + 3.5 * max(0.0, (f["hss_bearing_damage"] - 0.55) / 0.45) ** 1.5
        dirt = 1 + 5 * f["oil_contamination"] + 0.5 * f["hss_bearing_damage"] + 0.5 * f["planet_gear_pitting"]
        return {
            "wind": wind, "amb": amb, "pressure": pressure, "yaw": yaw, "power": p, "load": ld, "rotor_rpm": rpm,
            "gen_rpm": rpm * self.ratio, "pitch": max(0.0, (veff - self.ro["rated_ms"]) * 1.8),
            "oil": oil, "hss": oil + th["hss_b0"] + th["hss_b1"] * ld + 12 * f["hss_bearing_damage"],
            "mb": amb + th["mb_m0"] + th["mb_m1"] * ld + 11 * f["main_bearing_wear"],
            "gen_wind": amb + 40 + 50 * ld, "gen_brg": amb + 25 + 15 * ld, "nacelle": amb + 8 + 6 * ld,
            "planet": (vb["planet0"] + vb["planet1"] * ld) * (1 + 2.5 * f["planet_gear_pitting"]),
            "hssmesh": (vb["hssmesh0"] + vb["hssmesh1"] * ld) * (1 + 0.3 * f["hss_bearing_damage"]),
            "hssenv": (vb["hssenv0"] + vb["hssenv1"] * ld) * bump,
            "mbenv": (vb["mbenv0"] + vb["mbenv1"] * ld) * (1 + 3 * f["main_bearing_wear"]),
            "gbxrms": (vb["gbxrms0"] + vb["gbxrms1"] * ld) * (1 + 3.5 * f["planet_gear_pitting"] + 0.15 * f["hss_bearing_damage"]),
            "pc4": 1000 * dirt, "pc6": 120 * dirt, "pc14": 15 * dirt,
            "fe": 3 + 40 * f["hss_bearing_damage"] ** 1.5 + 30 * f["planet_gear_pitting"] ** 1.5,
        }

    # one published message ------------------------------------------------------------------------------------------
    def reading(self, s):
        n = self.n
        return {
            "wind_speed_ms": round(s["wind"] * (1 + n(0.006)), 3), "yaw_error_deg": round(s["yaw"] + n(2.0), 2),
            "ambient_temp_c": round(s["amb"] + n(0.1), 2), "ambient_pressure_hpa": round(s["pressure"] + n(0.3), 1),
            "active_power_kw": round(s["power"] * (1 + n(0.01)), 1), "turbine_state": 1 if s["power"] > 0 else 0,
            "rotor_rpm": round(s["rotor_rpm"] * (1 + n(0.002)), 3), "gen_rpm": round(s["gen_rpm"] * (1 + n(0.002)), 1),
            "pitch_deg": round(s["pitch"] + abs(n(0.1)), 2),
            "gbx_oil_temp_c": round(s["oil"] + n(0.8), 2), "gbx_hss_brg_temp_c": round(s["hss"] + n(0.8), 2),
            "main_brg_temp_c": round(s["mb"] + n(0.7), 2), "gen_winding_temp_c": round(s["gen_wind"] + n(1.0), 2),
            "gen_brg_temp_c": round(s["gen_brg"] + n(0.7), 2), "nacelle_temp_c": round(s["nacelle"] + n(0.5), 2),
            "vib_planet_mesh": round(s["planet"] * (1 + n(0.05)), 4), "vib_hss_mesh": round(s["hssmesh"] * (1 + n(0.05)), 4),
            "vib_hss_brg_env": round(s["hssenv"] * (1 + n(0.06)), 4), "vib_mb_env": round(s["mbenv"] * (1 + n(0.06)), 4),
            "vib_gbx_rms_mms": round(s["gbxrms"] * (1 + n(0.04)), 3),
            "pc_4um_per_ml": round(s["pc4"] * (1 + n(0.08)), 1), "pc_6um_per_ml": round(s["pc6"] * (1 + n(0.08)), 1),
            "pc_14um_per_ml": round(s["pc14"] * (1 + n(0.08)), 2), "fe_particles_24h": max(0, round(s["fe"] + n(1.0))),
        }

    def measure(self, wind=None, amb=None):
        wind = self.rnd.uniform(4.5, 14.0) if wind is None else wind
        amb = self.site["ambient_c"] + self.n(3.0) if amb is None else amb
        return self.reading(self.true_state(wind, amb, self.site["pressure_hpa"] + self.n(5.0)))


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

    One real second is `demo.time_scale` plant seconds. The wind follows a mean-reverting random walk around
    `demo.wind_mean_ms`; temperatures follow their steady state with a short lag. Each measure() is one 10-minute message.
    """
    TAU_S = 3.0

    def __init__(self, twin, seed=3001):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.vmean = float(demo.get("wind_mean_ms", 9.5))
        self.amb = float(demo.get("ambient_c", 20.0))
        self.wt = Turbine(twin, seed)
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
        self.wind = self.vmean
        self.temps = None

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.wt.faults[k] = f.sev
        self.t += dt * self.scale
        r = self.wt.rnd
        self.wind += 0.05 * (self.vmean - self.wind) * dt + r.gauss(0, 0.25) * math.sqrt(dt)
        self.wind = max(3.0, min(20.0, self.wind))
        amb = self.amb + 1.5 * math.sin(2 * math.pi * self.t / 86400)
        s = self.wt.true_state(self.wind, amb, self.wt.site["pressure_hpa"])
        keys = ("oil", "hss", "mb", "gen_wind", "gen_brg", "nacelle")
        if self.temps is None:
            self.temps = {k: s[k] for k in keys}
        a = min(1.0, dt / self.TAU_S)
        for k in keys:
            self.temps[k] += a * (s[k] - self.temps[k])
            s[k] = self.temps[k]
        self.running = s["power"] > 0
        return s

    def measure(self, true):
        return self.wt.reading(true)
