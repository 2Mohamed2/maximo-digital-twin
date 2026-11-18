"""A stand-in for WFI-6701: hot WFI tank, loop pump, steam heater, points of use and coolers, analysers and the LIMS results,
with injectable faults.

The real loop sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the expected
values are computed in Monitor from the twin file only. This model only produces believable readings and fault fingerprints
for the tests, the figures and the live pages. Pure Python (math, random) so it also runs in the browser.

Physics of the stand-in (steady state at each reading):
  The drive raises the supply flow a little when outlets open: Q_s = (Q0 + 0.5 x draw) x pump factor; Q_r = Q_s - draw.
  The heater holds the supply at its setpoint; the loop loses about 12 kW, so T_return = T_supply - loss / (rho cp Q_r).
  Pump: dp = (dp0 (n/n0)^2 - k Q^2) x wear factor; shaft power = Q dp / 36 / efficiency.
  Raw conductivity of hot WFI = C25 x (1 + 0.022 (T - 25)) (assumed ionic temperature coefficient); TOC in ppb.
  Faults: heater output down (supply to 66 C); draw forced to 9 m3/h; impeller wear (dp x 0.8, flow x 0.85, efficiency x 0.75);
  seal leak (quench +35 K); cooler pressure reversal and telltale wet; still upset (C25 0.35 -> 1.5, TOC 45 -> 300 ppb);
  biofilm at a cooled point of use (branch to 45 C, sub-loop cold 30 h, 25 CFU/100 mL, 0.3 EU/mL); vent heater off.
"""
import math
import random

from twin_calc import _k, rho


class Loop:
    def __init__(self, twin, seed=1):
        self.tw = twin
        self.k = _k(twin)
        d = twin["design"]
        self.flow_per_draw = d["loop"]["flow_per_draw"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.nominal()

    def nominal(self):
        self.draw, self.cooling, self.cold_h, self.cycles, self.level = 0.0, False, 0.3, 16, 62.0

    def vary(self):
        """A random but plausible state over a production day (used by the parity test)."""
        r = self.rnd
        self.draw = r.choice([0.0, 0.0, r.uniform(0.5, 3.5)])
        self.cooling = r.random() < 0.3
        self.cold_h, self.cycles, self.level = r.uniform(0, 1.5), r.randint(0, 40), r.uniform(30, 90)

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
        draw = self.draw + (9.0 - self.draw) * f["over_draw"]
        wear = f["pump_wear"]
        qs = (k["q0"] + self.flow_per_draw * draw) * (1 - 0.15 * wear)
        qr = max(0.3, qs - draw)
        ts = k["tset"] - 16.0 * f["heating_loss"]
        tank = ts + 0.3
        loss_kw = 12.0 * (ts - 20) / (k["tset"] - 20)
        tr = ts - loss_kw / (rho(ts) * k["cp"] * qr / 3600)
        n = k["n0"]
        dp = (k["dp0"] * (n / k["n0"]) ** 2 - k["kq"] * qs * qs) * (1 - 0.2 * wear)
        eff = k["eff"] * (1 - 0.25 * wear)
        power = qs * dp / 36 / eff
        quench = k["qin"] + 0.1 * (ts - k["qin"]) + 35.0 * f["seal_wear"]
        c25 = 0.35 + 1.15 * f["generator_upset"]
        toc = 45.0 + 255.0 * f["generator_upset"]
        b = f["biofilm_deadleg"]
        tmin = min(ts, tr, tank)
        deadleg = tmin - 3.0 - 33.0 * b
        cw = 1.5 + 2.5 * f["cooler_leak"]
        vent = 90.0 - 35.0 * f["vent_heater_fail"]
        pou = 25.0 if (self.cooling or b > 0.5) else ts - 6.0
        return {"qs": qs, "qr": qr, "ts": ts, "tr": tr, "tank": tank, "dp": dp, "power": power, "n": n, "quench": quench,
                "c25": c25, "toc": toc, "deadleg": deadleg, "cw": cw, "telltale": 1 if f["cooler_leak"] > 0.5 else 0,
                "vent": vent, "pou": pou, "cold_h": self.cold_h + 30.0 * b, "micro": 25.0 * b, "eu": 0.01 + 0.29 * b,
                "level": self.level, "cycles": self.cycles}

    # one published message ------------------------------------------------------------------------------------------
    def reading(self, s):
        ts, tr = s["ts"] + self.n(0.08), s["tr"] + self.n(0.08)
        sp = 2.0 + s["dp"] - 0.8 + self.n(0.01)
        return {
            "supply_flow_m3h": round(s["qs"] * (1 + self.n(0.004)), 3),
            "return_flow_m3h": round(s["qr"] * (1 + self.n(0.004)), 3),
            "supply_temp_c": round(ts, 2), "return_temp_c": round(tr, 2),
            "supply_pressure_bar": round(sp, 3),
            "return_pressure_bar": round(1.2 + self.n(0.01), 3),
            "tank_temp_c": round(s["tank"] + self.n(0.08), 2),
            "tank_level_pct": round(s["level"], 1),
            "vent_filter_temp_c": round(s["vent"] + self.n(0.2), 2),
            "cond_us_cm": round(max(0.05, s["c25"] * (1 + 0.022 * (tr - 25)) + self.n(0.01)), 3),
            "toc_ppb": round(max(0.03, s["toc"] * (1 + self.n(0.03))), 1),
            "pump_speed_rpm": round(s["n"] + self.n(2), 0),
            "pump_dp_bar": round(s["dp"] + self.n(0.01), 3),
            "pump_power_kw": round(s["power"] * (1 + self.n(0.01)), 3),
            "seal_quench_temp_c": round(s["quench"] + self.n(0.2), 2),
            "pou_temp_c": round(s["pou"] + self.n(0.2), 2),
            "cooler_cycles_24h": s["cycles"],
            "subloop_cold_h": round(s["cold_h"], 2),
            "cooler_wfi_bar": round(sp - 0.6 + self.n(0.01), 3),
            "cooler_cw_bar": round(s["cw"] + self.n(0.01), 3),
            "cooler_telltale": s["telltale"],
            "deadleg_temp_c": round(s["deadleg"] + self.n(0.15), 2),
            "micro_cfu_100ml": float(round(s["micro"])),
            "endotoxin_eu_ml": round(s["eu"], 3),
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

    The plant clock runs `demo.time_scale` times faster than real time. Between 06:00 and 22:00 production draws WFI: every
    30 plant minutes one or two outlets open for 10 minutes (2.5 m3/h), and every other draw is a cooled draw from a point-of-use
    cooler, after which the sub-loop is hot-flushed. At night the loop only circulates. The tank level falls during the day and
    the still refills it.
    """

    def __init__(self, twin, seed=6701):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.x = Loop(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        """Back to a healthy loop at once (all faults to zero)."""
        for f in self.faults.values():
            f.sev = f.target = 0.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.x.faults[k] = f.sev
        self.t += dt * self.scale
        x = self.x
        h = (self.t / 3600.0) % 24.0
        m = (self.t / 60.0) % 30.0
        day = 6.0 <= h < 22.0
        slot = int(self.t // 1800)
        x.draw = 2.5 if day and m < 10.0 else 0.0
        x.cooling = x.draw > 0 and slot % 2 == 0
        x.cold_h = (m / 60.0) if x.cooling else 0.0
        x.cycles = 16                                   # 32 draws a day, every other one cooled
        x.level = 75.0 - 25.0 * ((h - 6.0) / 16.0) if day else 50.0 + 25.0 * ((h - 22.0) % 24.0) / 8.0
        return x.true()

    def measure(self, true):
        return self.x.reading(true)
