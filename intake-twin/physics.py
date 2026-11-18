"""A stand-in for INT-3701: tide, intake culvert, band screen with spray wash, circulating water pump and condenser, with
injectable faults.

The real intake sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the expected
values are computed in Monitor from the twin file only. This model only produces believable readings and fault fingerprints
for the tests, the figures and the live pages. Pure Python (math, random) so it also runs in the browser.

Physics of the stand-in (the twin's relations, plus what the twin does not know):
  Sea level follows one semi-diurnal tide. The culvert loses cl0 x (Q/Q0)^2 (x 36 with culvert fouling at full severity).
  Screen: dh = dh_clean / (1 - b)^2 with b the blinded open-area fraction (debris surge, biofouling); a damaged seal lets
  water bypass the mesh, so dh falls to 8 % of clean and debris reaches the condenser tube sheet.
  Pump operating point: pump curve wear x (H0 - a x^2) meets the system curve (Z_out - DN) + k_sys x^2, where Z_out - DN is
  the static lift to the seal pit (assumption: 8 m at the design pump bay level) and k_sys grows when the condenser plugs.
  Vortex: the vibration rises when the submergence margin drops below 1.1.
  Wash: wash pump curve p = p_shut - kw Qw^2 meets the nozzles Qw = C sqrt(p).
"""
import math
import random

from twin_calc import _k, s_req


class Intake:
    STATIC_M = 8.0          # static lift at the design pump bay level (assumption)

    def __init__(self, twin, seed=1):
        self.tw = twin
        self.k = _k(twin)
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.sea = self.k["sea0"]
        self.cw_in = 27.0
        k = self.k
        self.dn0 = k["sea0"] - k["cl0"] - k["dh0"]                    # design pump bay level
        self.zout = self.dn0 + self.STATIC_M
        self.ksys = k["hd"] - self.STATIC_M
        self.c0 = k["qw0"] / math.sqrt(k["pw0"])                      # nozzle coefficient
        self.kw = (k["wsh"] - k["pw0"]) / k["qw0"] ** 2               # wash pump curve

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    def vary(self, tide=1.0):
        """A random but plausible state: tide anywhere within +-tide x amplitude, seawater 24 to 30 C."""
        self.sea = self.k["sea0"] + self.rnd.uniform(-tide, tide) * self.k["amp"]
        self.cw_in = self.rnd.uniform(24.0, 30.0)

    # true state ---------------------------------------------------------------------------------------------------
    def true(self):
        f, k = self.faults, self.k
        b = min(0.9, 0.02 + 0.78 * f["debris_surge"] + 0.50 * f["mesh_biofouling"])
        byp = 1 - 0.92 * f["seal_carryover"]
        cul = k["cl0"] * (1 + 35 * f["culvert_fouling"])
        wear = 1 - 0.15 * f["cw_pump_wear"]
        ksys = self.ksys * (1 + 0.3 * f["seal_carryover"])
        a = k["h00"] - k["hd"]
        x = 1.0
        for _ in range(30):
            q = x * k["qd"]
            up = self.sea - cul * (q / k["q0"]) ** 2
            dhc = k["dh0"] * (q / k["q0"]) ** 2 * (k["h0"] / up) ** 2
            dh = dhc / (1 - b) ** 2 * byp
            dn = up - dh
            lift = self.zout - dn
            x_new = math.sqrt(max(0.05, (wear * k["h00"] - lift) / (wear * a + ksys)))
            x = 0.5 * x + 0.5 * x_new
        q = x * k["qd"]
        up = self.sea - cul * (q / k["q0"]) ** 2
        dhc = k["dh0"] * (q / k["q0"]) ** 2 * (k["h0"] / up) ** 2
        dh = dhc / (1 - b) ** 2 * byp
        dn = up - dh
        h = wear * (k["h00"] - a * x * x)
        eta = k["eta0"] * (2 * x - x * x) * (1 - 0.15 * f["cw_pump_wear"])
        power = k["rho"] * k["g"] * q * h / eta / 1000
        margin = (dn - k["cb"]) / s_req(k, q)
        speed = k["vhi"] if dh > k["hs"] else k["vlo"]
        c = self.c0 * (1 - 0.45 * f["spray_nozzle_blockage"])
        shut = k["wsh"] * (1 - 0.45 * f["wash_pump_wear"])
        pw = shut / (1 + self.kw * c * c)
        return {"sea": self.sea, "up": up, "dn": dn, "dh": dh, "q": q, "h": h, "power": power, "margin": margin, "speed": speed,
                "torque": k["t0"] + k["kt"] * dh + 35 * f["drive_chain_wear"], "pw": pw, "qw": c * math.sqrt(pw),
                "hs_h": 1.5 + 17 * f["mesh_biofouling"] + 5 * f["debris_surge"],
                "vib": 2.2 + 40 * max(0.0, 1.1 - margin) + 1.0 * f["cw_pump_wear"],
                "cdp": k["cdp0"] * (q / k["q0"]) ** 2 * (1 + 0.8 * f["seal_carryover"]), "cw_in": self.cw_in, "blind": b}

    # one published message ------------------------------------------------------------------------------------------
    def reading(self, s):
        k = self.k
        return {
            "sea_level_m": round(s["sea"] + self.n(0.002), 4),
            "level_up_m": round(s["up"] + self.n(0.002), 4),
            "level_down_m": round(s["dn"] + self.n(0.002), 4),
            "screen_speed_m_min": round(s["speed"] * (1 + self.n(0.01)), 3),
            "screen_torque_pct": round(s["torque"] + self.n(1.0), 2),
            "high_speed_h_24h": round(min(24.0, max(0.0, s["hs_h"] + self.n(0.4))), 2),
            "wash_pressure_bar": round(s["pw"] + self.n(0.02), 3),
            "wash_flow_m3h": round(s["qw"] * (1 + self.n(0.01)), 2),
            "cw_flow_m3s": round(s["q"] * (1 + self.n(0.004)), 4),
            "pump_discharge_bar": round((s["h"] - k["zg"] + s["dn"]) / k["pcoef"] + self.n(0.002), 4),
            "pump_power_kw": round(s["power"] * (1 + self.n(0.004)), 1),
            "pump_vib_mm_s": round(max(0.3, s["vib"] + self.n(0.15)), 2),
            "pump_running": 1,
            "cw_in_c": round(s["cw_in"] + self.n(0.05), 2),
            "cond_dp_bar": round(s["cdp"] * (1 + self.n(0.01)), 4),
        }

    def measure(self, tide=1.0):
        self.vary(tide)
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

    The plant clock runs `demo.time_scale` times faster than real time. The sea follows a 12.42 h tide; the seawater
    temperature swings 1.6 K over the day. Levels, flow and the expected screen differential move with the tide.
    """

    def __init__(self, twin, seed=3701):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.x = Intake(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        """Back to a clean intake at once (all faults to zero)."""
        for f in self.faults.values():
            f.sev = f.target = 0.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.x.faults[k] = f.sev
        self.t += dt * self.scale
        k = self.x.k
        self.x.sea = k["sea0"] + k["amp"] * math.sin(2 * math.pi * self.t / (k["period"] * 3600))
        self.x.cw_in = 27.0 + 0.8 * math.sin(2 * math.pi * ((self.t % 86400) / 86400 - 0.375))
        return self.x.true()

    def measure(self, true):
        return self.x.reading(true)
