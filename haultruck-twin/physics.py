"""A stand-in for HT-4001: a Cat 793F hauling ore up a ramp, with its engine, tyres, payload monitor and oil samples,
and injectable faults.

The real truck sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests, the figures and the live pages.

How the stand-in works: the engine delivers the power the road asks for (rimpull x speed on the grade, with the true
rolling resistance a little different from the twin's assumed value), up to its rated power. On the ramp the truck is
power-limited, so its speed is whatever the available power allows. Faults change the physics only: a plugged air filter
costs boost, power and fuel and heats the exhaust; a bad injector heats one bank; dust wears the rings; a slow leak lets one
tyre lose pressure and run hot. Pure Python (math, random): it also runs in the browser under Pyodide.
"""
import math
import random

P_ATM = 101.325
G = 9.81

# one haul cycle: (name, share of the cycle, grade %, loaded, speed limit key)
PHASES = [("loading", 20, 0.0, None, 0.0), ("loaded haul", 15, 0.0, True, "loaded"), ("loaded ramp", 40, 10.0, True, "ramp"),
          ("dumping", 10, 0.0, None, 0.0), ("empty return downhill", 25, -10.0, False, "down"), ("empty haul", 10, 0.0, False, "empty")]


class Truck:
    def __init__(self, twin, seed=1):
        self.tw = twin
        d = twin["design"]
        self.d = d
        self.e, self.f, self.dt, self.tr, self.hr = d["engine"], d["fuel"], d["drivetrain"], d["truck"], d["haul_road"]
        self.ty, self.em, self.oil = d["tyres"], d["engine_model"], d["oil"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.ambient = 32.0
        self.ambient_max = 36.0
        self.fuel_total = 2390000.0
        self.hours = 15800.0
        self.oil_hours = 240.0

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    def c(self, s, lim=3.0):
        """Gaussian noise clamped at lim standard deviations (keeps healthy readings inside the alarm bands)."""
        return max(-lim * s, min(lim * s, self.rnd.gauss(0, s)))

    # true state ---------------------------------------------------------------------------------------------------------
    def payload_loaded(self):
        tgt = self.tr["target_payload_t"]
        return tgt * (0.97 + 0.18 * self.faults["payload_overload"] + self.c(0.012))

    def p_max(self):
        return self.e["rated_gross_kw"] * 0.985 * (1 - 0.10 * self.faults["air_intake_restriction"])

    def speed_for(self, gvw_t, grade, limit_kmh, rr_true):
        """Steady speed: the speed limit, or the power-limited speed on a climb."""
        res = (grade + rr_true) / 100
        if res <= 0:
            return limit_kmh
        v_pow = (self.p_max() - self.dt["accessory_kw"]) * self.dt["efficiency"] / (gvw_t * G * res) * 3.6
        return min(limit_kmh, v_pow)

    def power(self, gvw_t, v_kmh, grade, rr_true):
        if v_kmh < 1:
            return self.e["idle_kw"]
        wheel = max(gvw_t * G * v_kmh / 3.6 * (grade + rr_true) / 100, 0.0)
        return min(wheel / self.dt["efficiency"] + self.dt["accessory_kw"], self.p_max())

    def limits(self):
        h = self.hr
        return {"loaded": h["speed_limit_loaded_kmh"], "ramp": h["speed_limit_loaded_kmh"], "down": h["downhill_limit_kmh"], "empty": h["speed_limit_empty_kmh"]}

    def steady(self, phase="loaded ramp"):
        """True steady state for one phase of the cycle (the stand-in used by the tests)."""
        name, _, grade, loaded, lim = next(p for p in PHASES if p[0] == phase)
        payload = self.payload_loaded() if loaded else 0.0
        rr = self.hr["rolling_resistance_pct"] + self.c(0.12)
        gvw = self.tr["empty_kg"] / 1000 + payload
        v = self.speed_for(gvw, grade, self.limits()[lim], rr) if lim else 0.0
        p = self.power(gvw, v, grade, rr)
        ld = p / self.e["rated_gross_kw"]
        cool = max(self.em["coolant_regulated_c"], self.ambient + self.em["coolant_rise_full_k"] * ld)
        cool += (12 + 6 * ld) * self.faults["cooling_degraded"]
        tk = self.tkph_ratio_true(payload)
        return {"phase": name, "payload": payload, "grade": grade, "speed": v, "power": p, "load": ld, "coolant": cool,
                "tyre_temp": [self.tyre_temp_true(i, tk) for i in range(1, 7)]}

    def shift(self):
        f = self.faults
        tgt = self.tr["target_payload_t"]
        return {"mean": tgt * (0.975 + 0.15 * f["payload_overload"] + self.c(0.004)),
                "over110": max(0.0, 1.5 + 60 * f["payload_overload"] + self.c(1.0)),
                "cycle_km": 14.0 + 6.0 * f["tkph_exceeded"] + self.c(0.1), "cycle_min": 45.0 + 7.0 * f["tkph_exceeded"] + self.c(0.3),
                "amb_max": self.ambient_max + 6.0 * f["tkph_exceeded"]}

    def tkph_ratio_true(self, payload=None):
        """Rough site TKPH / rating, used only to warm the tyres in the stand-in."""
        f = self.faults
        return 0.86 + 0.34 * f["tkph_exceeded"] + 0.04 * f["payload_overload"]

    def tyre_temp_true(self, i, tk):
        t = self.ambient + 22 * tk + 8
        if i == 3:
            t += 40 * self.faults["tyre_underinflation"]
        return t

    # one published message ------------------------------------------------------------------------------------------------
    def reading(self, s, sh=None):
        f, k = self.faults, self
        sh = sh or self.shift()
        ld, p = s["load"], s["power"]
        v = s["speed"]
        gear = 0 if v < 0.5 else next(i + 1 for i, g in enumerate(self.dt["gear_top_kmh"]) if v <= g * 0.98 or i == 5)
        rpm = self.e["idle_rpm"] if gear == 0 else 1300 + 450 * min(1.0, v / (self.dt["gear_top_kmh"][gear - 1] * 0.98))
        fuel = (self.f["zero_load_lph"] + p * self.f["bsfc_marginal_g_kwh"] / (1000 * self.f["density_kg_l"])) * (1 + 0.20 * f["air_intake_restriction"])
        em = self.em
        boost = (em["boost_zero_kpa"] + (em["boost_full_kpa"] - em["boost_zero_kpa"]) * ld) * (1 - 0.30 * f["air_intake_restriction"])
        exh = em["exhaust_zero_c"] + (em["exhaust_full_c"] - em["exhaust_zero_c"]) * ld + 160 * ld * f["air_intake_restriction"]
        right_extra = 110 * ld * f["injector_fault"]
        fe_rate = 12 + 43 * f["dust_ingestion"] + self.c(1.5)
        iso_add = round(5 * f["hydraulic_contamination"])
        r = {
            "payload_t": round(s["payload"] + (self.n(0.3) if s["payload"] > 0 else 0.0), 1),
            "shift_payload_mean_t": round(sh["mean"], 1), "shift_over110_pct": round(sh["over110"], 1), "shift_loads": 18,
            "speed_kmh": round(max(0.0, v * (1 + self.c(0.004))), 2), "grade_pct": round(s["grade"] + self.c(0.05), 2), "gear": gear,
            "cycle_km": round(sh["cycle_km"], 2), "cycle_min": round(sh["cycle_min"], 1),
            "engine_rpm": round(rpm + self.c(5)), "fuel_lph": round(fuel * (1 + self.c(0.01)), 1), "boost_kpa": round(boost * (1 + self.c(0.015)), 1),
            "exh_left_c": round(exh + self.c(4), 1), "exh_right_c": round(exh + right_extra + self.c(4), 1),
            "coolant_c": round(s["coolant"] + self.c(0.4), 1), "oil_temp_c": round(s["coolant"] + 8 + 6 * ld + self.c(0.5), 1),
            "oil_kpa": round(180 + 0.13 * rpm + self.c(5), 0),
            "crankcase_kpa": round(em["crankcase_zero_kpa"] + (em["crankcase_full_kpa"] - em["crankcase_zero_kpa"]) * ld + 1.4 * f["dust_ingestion"] + self.c(0.05), 3),
            "fuel_total_l": round(self.fuel_total), "engine_hours": round(self.hours, 1),
            "ambient_c": round(self.ambient + self.c(0.2), 1), "ambient_max_c": round(sh["amb_max"], 1),
        }
        for i in range(1, 7):
            cold = self.ty["cold_set_kpa"] * (1 - (0.25 * f["tyre_underinflation"] if i == 3 else 0.0)) * (1 + self.c(0.004))
            tt = s["tyre_temp"][i - 1] + self.c(1.0)
            hot = (cold + P_ATM) * (tt + 273.15) / (self.ambient + 273.15) - P_ATM
            r[f"tyre{i}_kpa"] = round(hot, 1)
            r[f"tyre{i}_c"] = round(tt, 1)
        r.update({"oil_fe_ppm": round(fe_rate * self.oil_hours / 250, 1), "oil_si_ppm": round(6 + 30 * f["dust_ingestion"] + self.c(1.0), 1),
                  "oil_soot_pct": round(0.4 + 1.2 * f["air_intake_restriction"] + self.c(0.05), 2), "oil_hours": self.oil_hours,
                  "hyd_iso4": 16 + self.rnd.randint(0, 1) + iso_add, "hyd_iso6": 14 + self.rnd.randint(0, 1) + iso_add,
                  "hyd_iso14": 11 + self.rnd.randint(0, 1) + iso_add})
        return r

    def measure(self, phase="loaded ramp"):
        return self.reading(self.steady(phase))


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

    The truck runs its haul cycle again and again: loading at the shovel, loaded haul, loaded ramp (power-limited), dumping
    at the crusher, empty return down the ramp, empty haul. One cycle takes `demo.cycle_s` real seconds. Coolant and tyre
    temperatures follow their steady values with a lag; everything else follows at once.
    """
    TAU_COOLANT = 30.0
    TAU_TYRE = 60.0

    def __init__(self, twin, seed=4001):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.cycle = float(demo.get("cycle_s", 120))
        self.tr = Truck(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 9 * 3600.0
        self.running, self.trip = True, 0
        self.pos = 0.0
        self.speed = 0.0
        self.payload_now = 0.0
        self.load_target = self.tr.payload_loaded()
        self.rr = twin["design"]["haul_road"]["rolling_resistance_pct"]
        self.coolant = twin["design"]["engine_model"]["coolant_regulated_c"]
        self.tyre = [self.tr.ambient + 22 * 0.86 + 8] * 6
        self.state = None

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.pos, self.speed, self.payload_now = 0.0, 0.0, 0.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def phase(self):
        x, acc = self.pos / self.cycle * 120.0, 0.0
        for p in PHASES:
            if x < acc + p[1]:
                return p, (x - acc) / p[1]
            acc += p[1]
        return PHASES[-1], 1.0

    def step(self, dt=1.0):
        tr = self.tr
        for k, f in self.faults.items():
            f.step(dt)
            tr.faults[k] = f.sev
        self.t += dt * self.scale
        hour = (self.t / 3600.0) % 24
        tr.ambient = 30 + 6 * math.sin(2 * math.pi * (hour - 9) / 24)
        tr.ambient_max = 36.0
        self.pos = (self.pos + dt) % self.cycle
        (name, _, grade, loaded, lim), frac = self.phase()
        if name == "loading":
            if frac < 0.05:
                self.load_target = tr.payload_loaded()
            self.payload_now = 0.0 if frac < 0.5 else self.load_target * min(1.0, (frac - 0.5) / 0.4)
        elif name == "dumping":
            self.payload_now = self.load_target if frac < 0.5 else 0.0
        elif loaded:
            self.payload_now = self.load_target
        else:
            self.payload_now = 0.0
        gvw = tr.tr["empty_kg"] / 1000 + self.payload_now
        target_v = tr.speed_for(gvw, grade, tr.limits()[lim], self.rr) if lim else 0.0
        a = 1 - math.exp(-dt / 3.0) if dt > 0 else 0.0
        self.speed += (target_v - self.speed) * a
        if self.speed < 0.3 and target_v == 0:
            self.speed = 0.0
        p = tr.power(gvw, self.speed, grade, self.rr)
        ld = p / tr.e["rated_gross_kw"]
        em = tr.em
        cool_ss = max(em["coolant_regulated_c"], tr.ambient + em["coolant_rise_full_k"] * ld) + (12 + 6 * ld) * tr.faults["cooling_degraded"]
        if dt > 0:
            self.coolant += (cool_ss - self.coolant) * (1 - math.exp(-dt / self.TAU_COOLANT))
            tk = tr.tkph_ratio_true()
            for i in range(6):
                self.tyre[i] += (tr.tyre_temp_true(i + 1, tk) - self.tyre[i]) * (1 - math.exp(-dt / self.TAU_TYRE))
            fuel = (tr.f["zero_load_lph"] + p * tr.f["bsfc_marginal_g_kwh"] / (1000 * tr.f["density_kg_l"]))
            tr.fuel_total += fuel * dt * self.scale / 3600
            tr.hours += dt * self.scale / 3600
        self.state = {"phase": name, "payload": self.payload_now, "grade": grade, "speed": self.speed, "power": p, "load": ld,
                      "coolant": self.coolant, "tyre_temp": list(self.tyre), "cycle_pos": self.pos / self.cycle}
        return dict(self.state)

    def measure(self, true):
        return self.tr.reading(true)
