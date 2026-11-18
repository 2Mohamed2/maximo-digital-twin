"""A stand-in for E-2501: the crude / kerosene exchanger with its transmitters and the kerosene colour analyser, with
injectable faults.

The real exchanger sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests, the figures and the live pages. Pure Python (math, random) so it also runs in the browser.

Physics of the stand-in (same 1-2 shell-and-tube relations as the twin, plus what the twin does not know):
  U = 1 / (1/hio(Wc_tubes) + 1/ho(Wk) + R_wall + Rf_tube + Rf_shell); duty from effectiveness-NTU.
  Tube fouling: deposit of thickness Rf x k_dep (k_dep = 0.35 W/m K, assumption) narrows the tube, and the rough deposit
  adds friction: dP ratio = (ID / (ID - 2 thickness))^5 x (1 + 250 Rf).
  Pass partition leak: a fraction b of the crude short-cuts the passes and mixes at the outlet.
  Tube leak: crude (higher pressure) leaks into the shell and leaves with the kerosene, colder and dark.
"""
import math
import random

try:
    from twin_calc import _k, u_clean, duty
except ImportError:  # pragma: no cover
    raise


class Exchanger:
    RF_T0, RF_S0 = 0.00006, 0.00003      # residual fouling a few weeks after cleaning (assumption)
    K_DEP = 0.35                         # deposit thermal conductivity, W/m K (assumption)

    def __init__(self, twin, seed=1):
        self.tw = twin
        self.k = _k(twin)
        d = twin["design"]
        self.p, self.g, self.hy = d["process"], d["geometry"], d["hydraulics"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.load, self.kload, self.dtc, self.dtk = 1.0, 1.0, 0.0, 0.0

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    def vary(self):
        """A random but plausible operating point (throughput 92-105 %, inlet temperatures +-3 K)."""
        self.load = self.rnd.uniform(0.92, 1.05)
        self.kload = self.load * self.rnd.uniform(0.97, 1.03)
        self.dtc, self.dtk = self.rnd.uniform(-3, 3), self.rnd.uniform(-3, 3)

    # true state ---------------------------------------------------------------------------------------------------
    def true(self):
        f, k, p = self.faults, self.k, self.p
        turn = 1 - 0.45 * f["low_throughput"]
        wc = p["crude_flow_t_h"] * self.load * turn
        wk = p["kero_flow_t_h"] * self.kload * (1 - 0.4 * f["low_throughput"])
        tci, tki = p["crude_in_c"] + self.dtc, p["kero_in_c"] + self.dtk
        rft = self.RF_T0 + 0.00114 * f["tube_fouling"]
        rfs = self.RF_S0 + 0.00077 * f["shell_fouling"]
        b = 0.30 * f["partition_leak"]
        leak = 0.06 * f["tube_leak"]
        wct = wc * (1 - b)
        u = 1 / (1 / u_clean(k, wct, wk) + rft + rfs)
        q = duty(k, u, wct, wk, tki, tci)
        cc, ch = wc / 3.6 * k["cpc"], wk / 3.6 * k["cpk"]
        tco = tci + q / cc                                   # bypassed crude mixes back at the outlet
        tk_mid = tki - q / ch
        cl = leak * cc
        tko = (ch * tk_mid + cl * tco) / (ch + cl)           # leaked crude leaves with the kerosene
        idm = self.g["tube_id_mm"]
        th = rft * self.K_DEP * 1000                         # deposit thickness, mm
        dpt = k["dpt0"] * (wct / k["wc0"]) ** k["ed"] * (idm / (idm - 2 * th)) ** 5 * (1 + 250 * rft)
        dps = k["dps0"] * (wk / k["wk0"]) ** k["ed"] * (1 + 600 * (rfs - self.RF_S0))
        return {"wc": wc, "wk": wk, "tci": tci, "tco": tco, "tki": tki, "tko": tko, "q": q, "u": u, "rf": rft + rfs,
                "dpt": dpt, "dps": dps, "leak": leak, "bypass": b}

    # one published message ------------------------------------------------------------------------------------------
    def reading(self, s):
        f, k, hy = self.faults, self.k, self.hy
        return {
            "crude_flow_t_h": round(s["wc"] * (1 + self.n(0.003)), 3),
            "crude_in_c": round(s["tci"] + self.n(0.08), 2),
            "crude_out_c": round(s["tco"] + 6.0 * f["ti_drift"] + self.n(0.08), 2),
            "dp_tube_bar": round(s["dpt"] * (1 + self.n(0.01)), 4),
            "crude_pressure_barg": round(hy["crude_pressure_barg"] + self.n(0.05), 2),
            "kero_flow_t_h": round(s["wk"] * (1 + self.n(0.003)), 3),
            "kero_in_c": round(s["tki"] + self.n(0.08), 2),
            "kero_out_c": round(s["tko"] + self.n(0.08), 2),
            "dp_shell_bar": round(s["dps"] * (1 + self.n(0.01)), 4),
            "kero_pressure_barg": round(hy["kero_pressure_barg"] + self.n(0.05), 2),
            "kero_saybolt": round(max(-16.0, k["sayn"] - 333 * s["leak"] + self.n(0.3)), 1),
        }

    def measure(self):
        self.vary()
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

    The plant clock runs `demo.time_scale` times faster than real time. Over a plant day the crude throughput swings
    +-4 % and the tank and column temperatures drift a little, so the twin's expected values move with the operating point.
    """

    def __init__(self, twin, seed=2501):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.x = Exchanger(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        """Back to a just-cleaned exchanger at once (all faults to zero)."""
        for f in self.faults.values():
            f.sev = f.target = 0.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.x.faults[k] = f.sev
        self.t += dt * self.scale
        ph = 2 * math.pi * (self.t % 86400) / 86400
        self.x.load = 1.0 + 0.04 * math.sin(ph)
        self.x.kload = self.x.load * (1 + 0.01 * math.sin(2 * ph))
        self.x.dtc = 2.0 * math.sin(ph - 0.8)
        self.x.dtk = 1.5 * math.cos(ph)
        return self.x.true()

    def measure(self, true):
        return self.x.reading(true)
