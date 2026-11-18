"""A stand-in for PSV-2601: the protected drum, the relief valve, its acoustic transmitter and its bench-test record, with
injectable faults.

The real gateway sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings, lift
events and fault fingerprints for the tests and the figures.
"""
import math
import random


class Valve:
    def __init__(self, twin, seed=1):
        self.t = twin
        d = twin["design"]
        self.v, self.rl, self.ac, self.rb = d["vessel"], d["relief"], d["acoustic"], d["rbi"]
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
    def operating_barg(self):
        return self.v["operating_barg"] + 2.5 * self.faults["operating_near_set"]

    def open_ratio(self):
        """Opening pressure / set: a clean valve pops at set; deposits and corrosion hold the disc down."""
        return 1.004 + 0.12 * self.faults["valve_sticking"]

    def peak_ratio(self):
        """Peak drum pressure / MAWP during a lift: overpressure needed for full lift, plus the late opening."""
        return 1.045 + 0.10 * self.faults["valve_sticking"]

    # one published message ------------------------------------------------------------------------------------------
    def measure(self):
        f = self.faults
        s, mawp = self.v["set_barg"], self.v["mawp_barg"]
        p = self.operating_barg() + self.n(0.06)
        op = p / s * 100
        amb = 30.0 + self.n(0.3)
        simmer = max(0.0, op - 92.0) * 4.0
        lift_vessel = s * 1.07 + self.n(0.03)
        return {
            "vessel_pressure_barg": round(p, 3), "vessel_temp_c": round(self.v["temp_c"] + self.n(0.4), 2),
            "vapour_feed_kgh": round(self.rl["design_feed_kgh"] * (1 + 0.35 * f["relief_load_increase"]) + self.n(80), 1),
            "acoustic_level": round(min(255.0, self.ac["background_counts"] + self.n(2.5) + 45 * f["seat_passing"] + simmer), 1),
            "outlet_temp_c": round(amb + self.n(0.8) - 9.0 * f["seat_passing"], 2), "ambient_temp_c": round(amb, 2),
            "header_pressure_barg": round(0.15 + 0.3 * f["high_backpressure"] + abs(self.n(0.02)), 3),
            "lift_active": 0,
            "lift_open_barg": round(s * self.open_ratio() + self.n(0.03), 3),
            "lift_peak_barg": round(mawp * self.peak_ratio() + self.n(0.03), 3),
            "lift_vessel_barg": round(lift_vessel, 3),
            "lift_inlet_barg": round(lift_vessel - s * (0.016 + 0.042 * f["inlet_restriction"]) + self.n(0.012), 3),
            "lift_outlet_barg": round(s * (0.05 + 0.11 * f["high_backpressure"]) + self.n(0.02), 3),
            "lift_duration_s": round(max(2.0, 95 - 90 * f["inlet_restriction"] + self.n(3 * (1 - f["inlet_restriction"]) + 0.6)), 1),
            "lift_count_30d": int(round(9 * f["inlet_restriction"])), "lift_count_365d": 2 + int(round(30 * f["inlet_restriction"])),
            "test_asfound_barg": round(s * (1.006 + 0.064 * f["set_pressure_drift"]) + self.n(0.02), 3),
            "test_prev_asleft_barg": round(s + self.n(0.01), 3), "test_interval_h": 34800.0,
            "test_seat_bpm": round(4 + 41 * f["set_pressure_drift"] + abs(self.n(1.0)), 1),
            "test_hours_since": round(17500 + 22000 * f["test_overdue"] + abs(self.n(100)), 1),
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

    The drum runs at its operating pressure. Every `demo.lift_every_s` real seconds a short process upset pushes the drum to
    set: the valve lifts for `demo.lift_s` seconds (acoustic level high, drum pressure up to its peak and back), and at the
    end the lift values (opening, peak, inlet and outlet pressure, duration) are stored, as the acoustic event log does.
    """
    LIFT_COUNTS = 205.0

    def __init__(self, twin, seed=2601):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.every = float(demo.get("lift_every_s", 75))
        self.lift_s = float(demo.get("lift_s", 8))
        self.v = Valve(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.timer, self.lift = 0.0, None
        self.last = self.v.measure()

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.timer, self.lift = 0.0, None

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.v.faults[k] = f.sev
        self.t += dt * self.scale
        p = self.v.operating_barg()
        if self.lift is None:
            self.timer += dt
            if self.timer >= self.every:
                self.timer, self.lift = 0.0, 0.0
        else:
            self.lift += dt
            if self.lift >= self.lift_s:
                self.lift, self.last = None, self.v.measure()
        if self.lift is not None:
            peak = self.twin["design"]["vessel"]["mawp_barg"] * self.v.peak_ratio()
            p = p + (peak - p) * math.sin(math.pi * min(1.0, self.lift / self.lift_s))
        return {"pressure": p, "lifting": self.lift is not None}

    def measure(self, true):
        r = self.v.measure()
        for k in ("lift_open_barg", "lift_peak_barg", "lift_vessel_barg", "lift_inlet_barg", "lift_outlet_barg", "lift_duration_s"):
            r[k] = self.last[k]
        r["vessel_pressure_barg"] = round(true["pressure"] + self.v.n(0.04), 3)
        if true["lifting"]:
            r["lift_active"] = 1
            r["acoustic_level"] = round(min(255.0, self.LIFT_COUNTS + self.v.n(6)), 1)
        return r
