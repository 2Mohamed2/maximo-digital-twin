"""A stand-in for ST-4701: the steam main, the TD52M trap, its Rosemount 708 acoustic transmitter and the survey records
of the 800-trap population, with injectable faults.

The real gateway sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings, trap
cycles and fault fingerprints for the tests and the figures.
"""
import math
import random

_N = [0.0, 0.11670521452767e4, -0.72421316703206e6, -0.17073846940092e2, 0.12020824702470e5, -0.32325550322333e7,
      0.14915108613530e2, -0.48232657361591e4, 0.40511340542057e6, -0.23855557567849, 0.65017534844798e3]


def tsat_c(p_barg, atm=1.01325):
    b = ((p_barg + atm) / 10) ** 0.25
    e = b * b + _N[3] * b + _N[6]
    f = _N[1] * b * b + _N[4] * b + _N[7]
    g = _N[2] * b * b + _N[5] * b + _N[8]
    d = 2 * g / (-f - math.sqrt(f * f - 4 * e * g))
    return (_N[10] + d - math.sqrt((_N[10] + d) ** 2 - 4 * (_N[9] + _N[10] * d))) / 2 - 273.15


class Trap:
    def __init__(self, twin, seed=1):
        self.t = twin
        d = twin["design"]
        self.st, self.ac, self.th, self.cy, self.po = d["steam"], d["acoustic"], d["thermal"], d["cycling"], d["population"]
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
    def cycle_rate(self):
        """Cycles per minute: a worn disc cycles fast; a trap blowing open or held open by a heavy load stops cycling."""
        f = self.faults
        c = self.cy["design_cycles_per_min"] * (1 + 3.2 * f["disc_wear"])
        c *= (1 - f["failed_open"]) * (1 - 0.9 * f["condensate_overload"]) * (1 - f["blocked_cold"]) * (1 - f["sensor_fault"])
        return max(0.0, c)

    def leak_fraction(self):
        f = self.faults
        return min(1.0, 0.85 * f["failed_open"] + 0.30 * f["disc_wear"])

    # one published message ------------------------------------------------------------------------------------------
    def measure(self):
        f = self.faults
        p = self.st["line_pressure_barg"] + self.n(0.08)
        ts = tsat_c(p)
        amb = 28.0 + self.n(0.5)
        outlet = 0.4 + 8.2 * f["backpressure_high"] + abs(self.n(0.03))
        dp = p - outlet
        ae = self.ac["a0_counts"] + self.ac["a1_counts_per_bar"] * dp
        ao = self.ac["open0_counts"] + self.ac["open1_counts_per_bar"] * dp
        lf = self.leak_fraction()
        level = ae + lf * (ao - ae) + 0.25 * ae * f["condensate_overload"] + self.n(2.0)
        level = level * (1 - 0.75 * f["blocked_cold"]) * (1 - 0.7 * f["sensor_fault"])
        # inlet temperature: saturation minus the clamp offset; condensate standing in the drip leg cools it
        sub = self.th["surface_offset_c"] + self.n(1.2) - 2.0 * f["failed_open"]
        sub += 20.0 * f["condensate_overload"] + 18.0 * f["backpressure_high"] + 60.0 * f["blocked_cold"]
        tin = ts - sub
        tin = tin + (amb + 4.0 - tin) * f["sensor_fault"]
        days = 60.0 + 640.0 * f["survey_lapsed"] + abs(self.n(5))
        tot = self.po["traps_total"]
        new_open = tot * self.po["design_fail_open_rate_pct_y"] / 100 * (1 + 1.1 * f["population_ageing"]) + self.n(1.5)
        r_cold = tot * self.po["design_fail_cold_rate_pct_y"] / 100
        return {
            "acoustic_level": round(min(255.0, max(0.0, level)), 1), "inlet_temp_c": round(tin, 2),
            "cycle_rate_per_min": round(max(0.0, self.cycle_rate() + self.n(0.15)), 2), "outlet_pressure_barg": round(outlet, 3),
            "line_pressure_barg": round(p, 3), "line_temp_c": round(ts + 1.0 + self.n(0.4), 2), "ambient_temp_c": round(amb, 2),
            "pop_traps_total": tot, "pop_failed_open": int(round(new_open * days / 365 + self.n(1))),
            "pop_failed_cold": int(round(r_cold * days / 365 + abs(self.n(0.7)))),
            "pop_new_failed_open_365d": int(round(new_open)), "survey_days_since": round(days, 1),
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

    The steam main runs at its design pressure. The trap's disc lifts for a short discharge and snaps shut, at the cycling
    rate of the trap model (faster with a worn disc); a failed-open trap blows continuously and a blocked trap stays shut.
    The clock of the day is not used, so the warm-up of the in-browser shim does not matter.
    """
    OPEN_S = 2.0

    def __init__(self, twin, seed=4701):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.v = Trap(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.phase = 0.0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.phase = 0.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.v.faults[k] = f.sev
        self.t += dt * self.scale
        rate = self.v.cycle_rate()
        period = 60.0 / rate if rate > 0.05 else 1e9
        self.phase = (self.phase + dt) % period if period < 1e8 else 0.0
        blowing = self.v.faults["failed_open"] > 0.5
        disc_open = blowing or (period < 1e8 and self.phase < min(self.OPEN_S, period / 2))
        return {"disc_open": disc_open, "blowing": blowing, "cycle_period_s": period if period < 1e8 else None}

    def measure(self, true):
        r = self.v.measure()
        return r
