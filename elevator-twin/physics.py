"""A stand-in for EL-5701: car, counterweight, machine, brake, doors, drive and energy meter, with injectable faults.

The real elevator controller sends the same points (see telemetry.points in the twin file). Nothing here is used by
Monitor: the expected values are computed in Monitor from the twin file only. This model only produces believable
readings and fault fingerprints for the tests, the figures and the live pages. Pure Python (math, random).

The "true" elevator follows the same hoisting equation as the twin, with the faults acting on the physical causes:
  door_obstruction         doors close up to 60 % slower and the operator draws up to 80 % more current
  light_curtain_fault      reopenings go from 5 % to 35 % of the closings
  door_lock_fault          up to 12 closings a day without the lock contact made
  counterweight_imbalance  the car got heavier (or filler weights were lost): balance ratio down by up to 12 points
  guide_friction_high      running friction up to 2.5 x, horizontal vibration up
  brake_wear               the brake holds up to 55 % less torque in its automatic test
  levelling_drift          stopping error up to 18 mm, re-levelling after up to 20 % of the stops
  regen_lost               the drive burns the regenerated energy: running energy per trip up 60 %
Traffic follows an office day on the plant clock (morning, lunch and evening peaks, quiet nights).
"""
import math
import random


def office_starts_per_h(hour):
    """Motor starts per hour of an office lift through the day (assumption: a typical weekday shape)."""
    day = 1 / (1 + math.exp(-(hour - 7.3) * 4)) * 1 / (1 + math.exp((hour - 18.8) * 4))
    peaks = (85 * math.exp(-((hour - 8.6) / 0.7) ** 2) + 50 * math.exp(-((hour - 12.6) / 0.6) ** 2)
             + 65 * math.exp(-((hour - 17.4) / 0.7) ** 2))
    return 4 + 45 * day + peaks


TRIPS_DAY = sum(office_starts_per_h(h / 10) for h in range(240)) / 10


class Elevator:
    def __init__(self, twin, seed=1):
        self.tw = twin
        d = twin["design"]
        self.d = d
        h, dr, e = d["hoist"], d["doors"], d["energy"]
        self.Q, self.kb, self.ff, self.g = d["car"]["rated_load_kg"], h["balance_ratio"], h["friction_kn"], h["g"]
        self.r, self.i = h["sheave_d_m"] / 2, h["roping"]
        self.open0, self.close0, self.amp0 = dr["open_time_s"], dr["close_time_s"], dr["close_current_a"]
        self.e0, self.em, self.psb = e["e_start_wh"], e["e_metre_wh"], e["standby_w"]
        self.brl = d["brake"]["test_required_load_ratio"]
        self.demo = d["demo"]
        self.rope_trips = float(self.demo["rope_trips_now"])
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
    def kb_true(self):
        return self.kb - 0.12 * self.faults["counterweight_imbalance"]

    def ff_true(self):
        return self.ff * (1 + 1.5 * self.faults["guide_friction_high"])

    def torque(self, load, d):
        """True constant-speed motor torque (N m) for a load (kg) and direction (+1 up, -1 down), with drive noise."""
        f = (load - self.kb_true() * self.Q) * self.g + d * self.ff_true() * 1000
        return f * self.r / self.i * (1 + self.n(0.004)) + self.n(1.5)

    def brake_ratio(self):
        return 1.9 * (1 - 0.55 * self.faults["brake_wear"])

    def energy_per_trip(self, s):
        f = self.faults
        fr = self.ff_true() / self.ff
        return ((self.e0 + self.em * s * (1 + 0.12 * (fr - 1))) * (1 + 0.8 * abs(self.kb_true() - self.kb))
                * (1 + 0.6 * f["regen_lost"]))

    # one published message ------------------------------------------------------------------------------------------
    def reading(self, hour, up_load, down_load, live=None):
        f, n = self.faults, self.n
        live = live or {"floor": 0, "speed": 0.0, "load": 0.0, "door": 100.0}
        floor_starts = self.demo.get("min_starts_per_h", 0)
        starts = max(0, round(max(office_starts_per_h(hour), floor_starts) * (1 + n(0.05))))

        def per_hour(rate):
            mean = starts * rate
            return max(0, round(mean + n(0.5 * math.sqrt(mean + 0.25))))
        trips = round(TRIPS_DAY * (1 + n(0.02)))
        s_avg = 13.0 * (1 + n(0.02))
        e24 = trips * self.energy_per_trip(s_avg) / 1000 * (1 + n(0.008)) + (self.psb + n(3)) * 24 / 1000
        req = (self.brl - self.kb) * self.Q * self.g * self.r / self.i
        return {
            "car_floor": live["floor"], "car_speed_ms": round(live["speed"], 3), "car_load_kg": round(live["load"]),
            "door_position_pct": round(live["door"], 1),
            "up_torque_nm": round(self.torque(up_load, 1), 1), "up_load_kg": round(up_load + n(5)),
            "down_torque_nm": round(self.torque(down_load, -1), 1), "down_load_kg": round(down_load + n(5)),
            "door_open_time_s": round(self.open0 * (1 + 0.15 * f["door_obstruction"]) + n(0.04), 2),
            "door_close_time_s": round(self.close0 * (1 + 0.6 * f["door_obstruction"]) + n(0.05), 2),
            "door_close_current_a": round(self.amp0 * (1 + 0.8 * f["door_obstruction"]) + n(0.03), 2),
            "door_reopens_1h": per_hour(0.05 + 0.30 * f["light_curtain_fault"]),
            "door_lock_fails_24h": max(0, round(0.3 + 12 * f["door_lock_fault"] + n(0.6))),
            "level_error_max_mm": round(abs(4.0 + 14.0 * f["levelling_drift"] + n(0.8)), 1),
            "relevels_1h": per_hour(0.01 + 0.19 * f["levelling_drift"]),
            "vib_lateral_mg": round(9.0 + 18.0 * f["guide_friction_high"] + n(1.0), 1),
            "vib_vertical_mg": round(12.0 + 3.0 * f["guide_friction_high"] + n(1.0), 1),
            "jerk_max_ms3": round(1.0 + n(0.03), 2),
            "brake_test_torque_nm": round(req * self.brake_ratio() * (1 + n(0.01)), 1),
            "brake_test_hours_since": round((hour - 3.0) % 24, 2),
            "energy_kwh_24h": round(e24, 2), "standby_power_w": round(self.psb + n(3), 1),
            "trips_24h": trips, "distance_m_24h": round(trips * s_avg), "starts_1h": starts,
            "trips_since_rope_change": round(self.rope_trips), "in_service": 1,
        }

    def measure(self, hour=None, up_load=None, down_load=None):
        hour = self.rnd.uniform(7, 19) if hour is None else hour
        up_load = self.rnd.uniform(0, 800) if up_load is None else up_load
        down_load = self.rnd.uniform(0, 600) if down_load is None else down_load
        return self.reading(hour, up_load, down_load)


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

    The car serves random calls: doors open (dwell), doors close, run with a trapezoid speed profile, stop, doors open.
    Each trip takes a new load and its constant-speed torque becomes the "last up" or "last down" reading. The counters
    (starts per hour, trips per day) follow the office profile on the plant clock, with demo.min_starts_per_h as a floor
    so the per-hour rates work at night too.
    """
    DWELL = 4.0

    def __init__(self, twin, seed=5701):
        self.twin = twin
        d = twin["design"]
        demo = d.get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.el = Elevator(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.stops, self.fh = d["shaft"]["stops"], d["shaft"]["floor_height_m"]
        self.vmax, self.acc = d["car"]["speed_ms"], d["ride"]["accel_ms2"]
        self.t = 0.0
        self.running, self.trip = True, 0
        self.reset()

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.pos, self.v, self.target = 0.0, 0.0, 0
        self.phase, self.timer, self.door = "dwell", 0.0, 100.0
        self.load = 0.0
        self.up_load, self.down_load = 320.0, 160.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def _new_call(self):
        r = self.el.rnd
        here = round(self.pos / self.fh)
        nxt = here
        while nxt == here:
            nxt = r.randrange(self.stops)
        self.target = nxt
        self.load = r.uniform(0, 800) if nxt > here else r.uniform(0, 600)
        if nxt > here:
            self.up_load = self.load
        else:
            self.down_load = self.load
        self.el.rope_trips += 1

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.el.faults[k] = f.sev
        self.t += dt * self.scale
        close_t = self.el.close0 * (1 + 0.6 * self.el.faults["door_obstruction"])
        left = dt
        while left > 1e-9:
            h = min(left, 0.25)
            left -= h
            if self.phase == "dwell":
                self.timer += h
                if self.timer >= self.DWELL:
                    self._new_call()
                    self.phase, self.timer = "closing", 0.0
            elif self.phase == "closing":
                self.door = max(0.0, self.door - 100 * h / close_t)
                if self.door <= 0:
                    self.phase = "run"
            elif self.phase == "run":
                goal = self.target * self.fh
                dist = goal - self.pos
                sgn = 1 if dist > 0 else -1
                vstop = math.sqrt(2 * self.acc * abs(dist))
                speed = min(abs(self.v) + self.acc * h, self.vmax, vstop)
                self.v = sgn * speed
                step = self.v * h
                if abs(step) >= abs(dist) or abs(dist) < 0.005:
                    self.pos, self.v, self.phase = goal, 0.0, "opening"
                else:
                    self.pos += step
            elif self.phase == "opening":
                self.door = min(100.0, self.door + 100 * h / self.el.open0)
                if self.door >= 100:
                    self.phase, self.timer = "dwell", 0.0
        hour = (self.t / 3600) % 24
        return {"hour": hour, "floor": round(self.pos / self.fh, 2), "speed": self.v, "load": self.load, "door": self.door,
                "pos_m": self.pos, "phase": self.phase}

    def measure(self, true):
        return self.el.reading(true["hour"], self.up_load, self.down_load, true)
