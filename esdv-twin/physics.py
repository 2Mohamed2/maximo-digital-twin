"""A stand-in for ESDV-2101: the valve, actuator, solenoid, digital valve controller and SIS bypass, with injectable faults.

The real device sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings, PST traces
and fault fingerprints for the tests and the figures.
"""
import math
import random


class Valve:
    def __init__(self, twin, seed=1):
        self.t = twin
        d = twin["design"]
        self.g, self.st, self.ln = d["signature"], d["stroke"], d["line"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.demands = 2

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state ---------------------------------------------------------------------------------------------------
    def spring_true(self):
        return self.g["spring_open_bar"] * (1 - 0.35 * self.faults["spring_relaxation"])

    def friction_true(self, line_bar):
        return (self.g["friction0_bar"] + self.g["friction_per_bar"] * line_bar) * (1 + 1.6 * self.faults["stem_seat_sticking"])

    def close_time(self, line_bar):
        fr = self.friction_true(line_bar) / (self.g["friction0_bar"] + self.g["friction_per_bar"] * line_bar)
        return (self.st["close_baseline_s"] * (1 + 1.1 * self.faults["sov_exhaust_restriction"]) * (1 + 0.15 * (fr - 1))
                * math.sqrt(self.g["spring_open_bar"] / self.spring_true()))

    # one published message ------------------------------------------------------------------------------------------
    def measure(self):
        f = self.faults
        lp = self.ln["pressure_nominal_bar"] + self.n(0.8)
        plp = self.ln["pressure_nominal_bar"] + self.n(0.8)
        s, fr = self.spring_true(), self.friction_true(plp)
        fe = self.g["friction0_bar"] + self.g["friction_per_bar"] * plp
        pst_ok = fr / fe <= 2.3
        supply = self.st["supply_nominal_bar"] - 2.3 * f["air_supply_low"] + self.n(0.03)
        zsc = 1 if f["position_feedback"] > 0.5 else 0
        return {
            "travel_pct": round(100 + self.n(0.15), 2), "limit_open": 1, "limit_closed": zsc,
            "actuator_pressure_bar": round(min(supply, 5.2) + self.n(0.02), 3), "supply_pressure_bar": round(supply, 3),
            "line_pressure_bar": round(lp, 2), "line_temp_c": round(self.ln["temp_nominal_c"] + self.n(0.5), 2),
            "sov_energized": 1, "pst_result": 1 if pst_ok else 0,
            "pst_travel_reached_pct": round(self.st["pst_target_travel_pct"] + self.n(0.3) if pst_ok else 97.5 + self.n(0.5), 2),
            "pst_p_close_start_bar": round(s - fr + self.n(0.015), 3), "pst_p_open_end_bar": round(s + fr + self.n(0.015), 3),
            "pst_line_pressure_bar": round(plp, 2),
            "pst_hours_since": round(300 + 2900 * f["pst_not_run"] + abs(self.n(40)), 1),
            "pst_interval_achieved_h": round(745 + 8015 * f["pst_not_run"] + self.n(5), 1),
            "proof_hours_since": 21000.0 + round(abs(self.n(200))), "overhaul_hours_since": 56040.0 + round(abs(self.n(200))),
            "last_close_time_s": round(self.close_time(plp) + self.n(0.08), 2),
            "bypass_active": 1 if f["bypass_left_on"] > 0.05 else 0,
            "bypass_active_h": round(2 + 70 * f["bypass_left_on"], 1) if f["bypass_left_on"] > 0.05 else 0.0,
            "bypass_hours_365d": round(6 + 60 * f["bypass_left_on"], 1),
            "demand_count": self.demands,
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

    The valve stands open. Every `demo.pst_every_s` real seconds the digital valve controller runs a partial stroke test:
    the travel goes 100 -> 85 -> 100 % over 8 s, and at the end the signature pressures, the result and the closing time are
    stored. With 'pst_not_run' active the tests are skipped, so the stored signature goes stale.
    """
    PST_S = 8.0

    def __init__(self, twin, seed=2101):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.every = float(demo.get("pst_every_s", 45))
        self.target = twin["design"]["stroke"]["pst_target_travel_pct"]
        self.v = Valve(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.timer, self.pst = 0.0, None
        self.last = self.v.measure()

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.timer, self.pst = 0.0, None

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.v.faults[k] = f.sev
        self.t += dt * self.scale
        travel = 100.0
        if self.pst is None:
            self.timer += dt
            if self.timer >= self.every:
                self.timer = 0.0
                if self.faults["pst_not_run"].sev < 0.3:
                    self.pst = 0.0
        else:
            self.pst += dt
            if self.pst >= self.PST_S:
                self.pst, self.last = None, self.v.measure()
        if self.pst is not None:
            m = self.v.measure()
            depth = (100 - self.target) if m["pst_result"] else 2.5
            travel = 100 - depth * math.sin(math.pi * min(1.0, self.pst / self.PST_S))
        return {"travel": travel, "pst_active": self.pst is not None}

    def measure(self, true):
        r = self.v.measure()
        for k in ("pst_result", "pst_travel_reached_pct", "pst_p_close_start_bar", "pst_p_open_end_bar",
                  "pst_line_pressure_bar", "last_close_time_s"):
            r[k] = self.last[k]
        r["travel_pct"] = round(true["travel"] + self.v.n(0.1), 2)
        r["limit_open"] = 1 if true["travel"] >= 97 else 0
        return r
