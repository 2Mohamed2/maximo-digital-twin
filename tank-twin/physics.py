"""A stand-in for TK-2701: the tank, its product, floating roof, gauges, meters and inspection records, with injectable faults.

The real device sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings, tank
tickets and fault fingerprints for the tests and the figures.

The true state is the net standard volume in the tank (m3 at 15 degC) and the product temperature. Levels are derived
from them with the same tank and product data the twin uses, then the gauges add their own noise and faults.
"""
import math
import random


class Tank:
    def __init__(self, twin, seed=1):
        self.t = twin
        d = twin["design"]
        self.g, self.p, self.r, self.o, self.op = d["geometry"], d["product"], d["roof"], d["overfill"], d["operation"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.rho = self.p["density15_nominal"]
        self.water_mm = 120.0
        self.fl = self.r["leg_height_m"] * 1000 + self.r["mass_kg"] / (self.rho * self.r["roof_area_m2"]) * 1000

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # tank and product ---------------------------------------------------------------------------------------------------
    def vcf(self, t):
        al = self.p["k0"] / self.rho ** 2 + self.p["k1"] / self.rho
        dt = t - 15.0
        return math.exp(-al * dt * (1 + 0.8 * al * dt))

    def ctsh(self, t):
        a, d = self.g["shell_alpha_per_c"], t - self.g["strapping_base_temp_c"]
        return 1 + 2 * a * d + a * a * d * d

    def level_for(self, gsv, t):
        """True level (mm) that holds `gsv` m3 at 15 degC at temperature t (inverse of the twin's GSV)."""
        A, f = self.g["area_m2"], self.ctsh(t) * self.vcf(t)
        lv = (gsv + self.r["mass_kg"] / self.rho) / f * 1000 / A + self.water_mm
        if lv < self.fl:
            lv = gsv / f * 1000 / A + self.water_mm
        return lv

    def gsv_for(self, level, t):
        A, v = self.g["area_m2"], self.vcf(t)
        fra = self.r["mass_kg"] / (self.rho * v) if level >= self.fl else 0.0
        return (A * (level - self.water_mm) / 1000 * self.ctsh(t) - fra) * v

    # gauges, roof and records ----------------------------------------------------------------------------------------------
    def drift_mm(self):
        return -60.0 * self.faults["gauge_drift"]

    def gauge(self, level):
        return round(level + self.drift_mm() + self.n(0.3), 1)

    def temp(self, t):
        return round(t + self.n(0.02), 3)

    def roof(self, level, t):
        f = self.faults
        rim = self.r["rim_height_m"] * 1000
        if level < self.fl:
            base = [self.r["leg_height_m"] * 1000 + rim] * 3
        else:
            water_on_deck = 60000.0 * f["roof_drain_blocked"]
            draft = (self.r["mass_kg"] + water_on_deck) / (self.rho * self.vcf(t) * self.r["roof_area_m2"]) * 1000
            base = [level - draft + rim] * 3
        tilt = 150.0 * f["roof_tilt"]
        return [round(base[0] + tilt + self.n(3), 1), round(base[1] - tilt + self.n(3), 1), round(base[2] + self.n(3), 1)]

    def inspection(self):
        s = self.faults["bottom_corrosion"]
        return {"shell_t_mm": 18.2, "shell_t_prev_mm": 18.6, "shell_years_between": 10.0, "years_since_ut": 3.0,
                "bottom_t_mm": round(6.9 - 2.7 * s, 2), "bottom_t_prev_mm": round(7.3 - 0.3 * s, 2), "bottom_years_between": 8.0,
                "years_since_internal": 2.0}

    def reading(self, level, t, inflow, outflow, mv, st, ambient=31.0, hh=None):
        """One message: the live gauge values plus the last movement ticket `mv` and the last quiet-period ticket `st`."""
        hh_m = self.o["hh_m"] * 1000
        r = {"level_mm": self.gauge(level), "level2_mm": round(level + self.n(0.3), 1),
             "hh_switch": (1 if level >= hh_m else 0) if hh is None else hh,
             "water_level_mm": round(self.water_mm + self.n(0.2), 1), "product_temp_c": self.temp(t), "ambient_temp_c": round(ambient + self.n(0.2), 1),
             "density15_kgm3": self.rho, "inflow_m3h": round(inflow, 1), "outflow_m3h": round(outflow, 1)}
        r.update(mv)
        r.update(st)
        h = self.roof(level, t)
        r.update({"roof_h1_mm": h[0], "roof_h2_mm": h[1], "roof_h3_mm": h[2],
                  "rim_gas_lel_pct": round(max(0.0, 2.0 + 25.0 * self.faults["rim_seal_damage"] + self.n(0.4)), 1)})
        r.update(self.inspection())
        return r

    def ticket_mv(self, l0, t0, l1, t1, metered, hours):
        return {"mv_open_level_mm": self.gauge(l0), "mv_open_temp_c": self.temp(t0), "mv_close_level_mm": self.gauge(l1),
                "mv_close_temp_c": self.temp(t1), "mv_meter_m3": round(metered, 1), "mv_hours": round(hours, 2)}

    def ticket_st(self, l0, t0, l1, t1, hours):
        return {"st_open_level_mm": self.gauge(l0), "st_open_temp_c": self.temp(t0), "st_close_level_mm": self.gauge(l1),
                "st_close_temp_c": self.temp(t1), "st_hours": round(hours, 2)}

    def leak_m3h(self):
        return 1.5 * self.faults["bottom_leak"]

    def meter_gain(self):
        return 1 + 0.01 * self.faults["meter_error"]

    # one published message for the tests: the tank half-way through a receipt ---------------------------------------------------
    def measure(self):
        f = self.faults
        hh_m, mw_m = self.o["hh_m"] * 1000, self.o["mw_m"] * 1000
        rec = self.op["receipt_m3h"]
        # last movement: a delivery of 7 h at the delivery rate, from 13.8 m
        hours = 7.0
        g0 = self.gsv_for(13800.0, 33.4)
        moved = self.op["delivery_m3h"] * hours
        g1 = g0 - moved - self.leak_m3h() * hours
        mv = self.ticket_mv(self.level_for(g0, 33.4), 33.4, self.level_for(g1, 33.1), 33.1, -moved * self.meter_gain(), hours)
        # last quiet period: 8 h with the valves shut after that delivery
        g2 = g1 - self.leak_m3h() * 8.0
        st = self.ticket_st(self.level_for(g1, 33.1), 33.1, self.level_for(g2, 32.9), 32.9, 8.0)
        # now: a receipt from the pipeline is filling the tank (product warmer than the tank)
        if f["overfill"] > 0.5:   # receipt not stopped at MW: the independent HH alarm tripped the inlet valve 50 mm above HH
            level, inflow = hh_m + 50.0 * f["overfill"], 0.0
        else:
            level, inflow = 9500.0 + (mw_m - 9500.0) * f["overfill"] * 2, rec
        return self.reading(level, 35.0, inflow, 0.0, mv, st)


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

    The tank cycles: receive at the receipt rate up to MW, settle, deliver down to the low working level, settle.
    The end of each movement writes a movement ticket (opening and closing gauge, metered volume); the end of each
    settling period writes a quiet-period ticket. With 'overfill' active the receipt is not stopped at MW: it goes on
    until the independent high-high alarm closes the inlet valve (AOPS), `trip` = 1.
    """

    def __init__(self, twin, seed=2701):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.k = Tank(twin, seed)
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
        k = self.k
        self.temp = 34.0
        self.gsv = k.gsv_for(9000.0, self.temp)
        self.phase, self.ph_h = "receive", 0.0
        self.open = (self.level(), self.temp, self.gsv)
        self.metered = 0.0
        self.trip = 0
        l0 = self.level()
        self.mv = k.ticket_mv(l0, self.temp, l0, self.temp, 0.0, 0.0)
        self.st = k.ticket_st(l0, self.temp, l0, self.temp, 8.0)
        self.flow = (0.0, 0.0)

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def level(self):
        return self.k.level_for(self.gsv, self.temp)

    def ambient(self):
        return 30.0 + 6.0 * math.sin(2 * math.pi * ((self.t / 3600) % 24 - 9) / 24)

    def _close(self, kind):
        k, (l0, t0, g0), l1 = self.k, self.open, self.level()
        if kind == "move":
            self.mv = k.ticket_mv(l0, t0, l1, self.temp, self.metered, self.ph_h)
        else:
            self.st = k.ticket_st(l0, t0, l1, self.temp, self.ph_h)
        self.open, self.metered, self.ph_h = (l1, self.temp, self.gsv), 0.0, 0.0

    def step(self, dt=1.0):
        k, op, o = self.k, self.k.op, self.k.o
        for name, f in self.faults.items():
            f.step(dt)
            k.faults[name] = f.sev
        h = dt * self.scale / 3600.0
        self.t += dt * self.scale
        hh_m, mw_m = o["hh_m"] * 1000, o["mw_m"] * 1000
        inflow = outflow = 0.0
        if h > 0:
            self.ph_h += h
            if self.phase == "receive":
                stop = mw_m + (hh_m + 60.0 - mw_m) * k.faults["overfill"]
                if self.level() >= hh_m:          # independent HH alarm: AOPS closes the inlet
                    self.trip = 1
                if self.level() < stop - 0.5 and not self.trip:
                    inflow = op["receipt_m3h"]
                    v = min(inflow * h, max(k.gsv_for(stop, self.temp) - self.gsv, 0.0))   # the valve closes at the stop level
                    self.temp += (self.p_in() - self.temp) * v / max(self.gsv + v, 1.0)
                    self.gsv += v
                    self.metered += v * k.meter_gain()
                else:
                    self._close("move")
                    self.phase = "settle_full"
            elif self.phase == "deliver":
                if self.level() > o["low_working_m"] * 1000 + 0.5:
                    outflow = op["delivery_m3h"]
                    v = min(outflow * h, max(self.gsv - k.gsv_for(o["low_working_m"] * 1000, self.temp), 0.0))
                    self.gsv -= v
                    self.metered -= v * k.meter_gain()
                else:
                    self._close("move")
                    self.phase = "settle_empty"
            elif self.ph_h >= op["settle_h"]:
                self._close("static")
                self.phase = "deliver" if self.phase == "settle_full" else "receive"
                self.trip = 0
            self.gsv -= k.leak_m3h() * h
            self.temp += (self.ambient() - self.temp) * h / 300.0
        else:
            inflow, outflow = self.flow
        self.flow = (inflow, outflow)
        return {"level": self.level(), "temp": self.temp, "inflow": inflow, "outflow": outflow, "phase": self.phase,
                "gsv": self.gsv, "trip": self.trip, "ambient": self.ambient()}

    def p_in(self):
        return self.k.p["temp_receipt_c"]

    def measure(self, true):
        r = self.k.reading(true["level"], true["temp"], true["inflow"], true["outflow"], self.mv, self.st, true["ambient"])
        return r
