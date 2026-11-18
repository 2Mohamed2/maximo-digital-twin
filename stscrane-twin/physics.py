"""A stand-in for QC-5801: a Liebherr ship-to-shore container crane discharging a ship, with its hoist, brakes, ropes,
spreader, trolley wheels, anemometer and the crane management system's counters, and injectable faults.

The real crane sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests, the figures and the live pages.

How the stand-in works: every move picks a container from the twin file's container mix. The hoist runs on the maker's
speed-load curve (constant power between the rated-load and the empty-spreader speed), the trolley at its rated speed;
the rest of the 120 s cycle is landing, locking and waiting for the truck. Faults change the physics only: a dragging
brake costs hoist power and slows the brake release; worn pads thin the pad; worn ropes shrink; twistlock faults add
retries and slow the crane; wheel misalignment wears the trolley wheels; snags put load-cell peaks above the safe working
load; rising wind is wind. Pure Python (math, random): it also runs in the browser under Pyodide.
"""
import math
import random

G = 9.81
AGE_Y = 8.4          # years in service at the start of the demo (stand-in only)


class Crane:
    def __init__(self, twin, seed=1):
        self.tw = twin
        d = twin["design"]
        self.d = d
        self.ra, self.h, self.tr, self.ga = d["rated"], d["hoist"], d["trolley"], d["gantry"]
        self.ro, self.br, self.op, self.cl = d["rope"], d["brake"], d["operation"], d["classification"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.swl, self.pa = self.ra["swl_twin_t"], self.ra["attachment_t"]
        self.prated = (self.swl + self.pa) * G * self.h["speed_rated_mpm"] / 60
        mpy, hpy = self.op["moves_per_year"], self.op["hoist_hours_per_year"]
        self.km = self.km_mix()
        self.struct_per_move = sum(s * (p / self.swl) ** 3 for _, s, p in self.op["mix"])
        # lifetime counters (the crane management system keeps them; the stand-in starts them at AGE_Y years)
        self.moves = round(AGE_Y * mpy)
        self.struct = self.moves * self.struct_per_move
        self.hours = AGE_Y * hpy
        self.equiv = self.hours * self.km
        self.rope_moves = 62000
        self.trolley_km = 6000.0

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

    # the maker's curve ---------------------------------------------------------------------------------------------------
    def speed(self, payload):
        return min(self.h["speed_empty_mpm"], self.prated * 60 / ((payload + self.pa) * G))

    def km_mix(self):
        """Spectrum factor of the hoist mechanism for the container mix (ISO 12482 Annex B weighting, same hoist height both ways)."""
        ref = self.swl + self.pa
        num = den = 0.0
        for _, s, p in self.op["mix"]:
            tl, tr = 1 / self.speed(p), 1 / self.speed(0.0)
            num += s * (tl * ((p + self.pa) / ref) ** 3 + tr * (self.pa / ref) ** 3)
            den += s * (tl + tr)
        return num / den

    def pick(self):
        r, acc = self.rnd.random(), 0.0
        for name, s, p in self.op["mix"]:
            acc += s
            if r <= acc:
                return name, max(1.5, p * (1 + self.c(0.12)))
        name, _, p = self.op["mix"][-1]
        return name, p

    def last_lift(self, payload):
        f = self.faults
        v = self.speed(payload) * (1 + self.c(0.004))
        p = (payload + self.pa) * G * v / 60 / self.h["efficiency"] * (1 + 0.25 * f["brake_drag"]) * (1 + self.c(0.012))
        return {"load": payload, "speed": v, "power": p}

    # one published message -----------------------------------------------------------------------------------------------
    def reading(self, s, lift=None):
        f = self.faults
        ro, tr = self.ro, self.tr
        lift = lift or self.last_lift(s.get("payload", 22.0) or 22.0)
        mpy, hpy = self.op["moves_per_year"], self.op["hoist_hours_per_year"]
        m30 = mpy * 30 / 365 * (1 + self.c(0.02))
        h30 = hpy * 30 / 365 * (1 + self.c(0.02))
        worn = self.trolley_km * tr["wear_mm_per_1000km"] / 1000 * (1 + 2.0 * f["trolley_wheel_wear"])
        cyc24 = 2 * 600 * (1 - 0.2 * f["twistlock_faults"]) + self.c(15)
        return {
            "crane_active": 1, "trolley_pos_m": round(s["x"], 2), "hoist_height_m": round(s["z"], 2),
            "load_now_t": round(s["load"], 1), "hoist_speed_mpm": round(s["v"], 1), "hoist_power_kw": round(s["p"], 0),
            "moves_per_hour": round(self.op["moves_per_hour"] * (1 - 0.27 * f["twistlock_faults"]) + self.c(0.8), 1),
            "last_load_t": round(lift["load"], 1), "last_lift_speed_mpm": round(lift["speed"], 1), "last_lift_power_kw": round(lift["power"], 0),
            "brake_release_ms": round(self.br["release_ms"] + self.c(8) + 300 * f["brake_drag"]),
            "brake_pad_mm": round(6.0 - 4.8 * f["brake_pad_wear"] + self.c(0.05), 2),
            "rope_moves_since_change": round(self.rope_moves + 78000 * f["rope_wear"]),
            "rope_dia_mm": round(ro["ref_mm"] - ro["nominal_mm"] * (0.016 + 0.066 * f["rope_wear"]) + self.c(0.02), 2),
            "twl_cycles_24h": round(cyc24), "twl_faults_24h": max(0, round(2 + self.c(1) + 20 * f["twistlock_faults"])),
            "snag_events_24h": round(3 * f["snag_overload"]),
            "peak_load_24h_t": round(max(44 + self.c(1.0), 1.35 * self.swl * f["snag_overload"]), 1),
            "trolley_km_since_change": round(self.trolley_km, 1), "trolley_wheel_mm": round(tr["wheel_new_mm"] - worn + self.c(0.05), 2),
            "wind_ms": round(max(0.0, 7.0 + self.c(1.0) + 16.0 * f["wind_operation"]), 1),
            "moves_total": self.moves, "moves_30d": round(m30),
            "struct_equiv": round(self.struct, 1), "struct_equiv_30d": round(m30 * self.struct_per_move * (1 + self.c(0.03)), 1),
            "hoist_hours": round(self.hours, 1), "hoist_hours_30d": round(h30, 1),
            "hoist_equiv_h": round(self.equiv, 2), "hoist_equiv_30d_h": round(h30 * self.km * (1 + self.c(0.03)), 2),
        }

    def measure(self):
        """A snapshot while hoisting a laden 40 ft box at steady speed (the stand-in used by the tests)."""
        p = 22.0 * (1 + self.c(0.1))
        lift = self.last_lift(p)
        st = {"x": 20.0, "z": 18.0, "load": p, "v": lift["speed"], "p": lift["power"], "payload": p}
        return self.reading(st, lift)


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


SAFE_Z, TRUCK_X, TRUCK_Z = 30.0, -12.0, 1.5


class Plant:
    """The live stand-in used by the twin pages (same interface as the other twins' Plant).

    The crane discharges a ship: trolley out to a row on the ship, lower the empty spreader into the cell, lock, hoist the
    box, trolley in over the truck lane, lower, unlock, hoist the empty spreader, and again. One move takes `demo.cycle_s`
    real seconds; twistlock faults add retries and lengthen it. The hoist follows the maker's speed-load curve.
    """
    LOCK_S = 4.0

    def __init__(self, twin, seed=5801):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.cycle = float(demo.get("cycle_s", 120))
        self.cr = Crane(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.lift = self.cr.last_lift(22.0)
        self.reset()

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.x, self.z, self.v, self.load = TRUCK_X, SAFE_Z, 0.0, 0.0
        self.new_move()

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def new_move(self):
        cr = self.cr
        self.box, self.payload = cr.pick()
        self.cell_x = 8.0 + cr.rnd.random() * 40.0
        self.cell_z = 2.0 + cr.rnd.random() * 18.0
        sev = self.faults["twistlock_faults"].sev
        retry = 1 + 1.2 * sev                      # lock / unlock retries
        tro = 60 / cr.tr["speed_mpm"]
        legs = [("trolley out", abs(self.cell_x - TRUCK_X) * tro + 3), ("lower empty", (SAFE_Z - self.cell_z) * 60 / cr.speed(0) + 3),
                ("lock", self.LOCK_S * retry), ("hoist loaded", (SAFE_Z - self.cell_z) * 60 / cr.speed(self.payload) + 3),
                ("trolley in", abs(self.cell_x - TRUCK_X) * tro + 3), ("lower loaded", (SAFE_Z - TRUCK_Z) * 60 / cr.speed(self.payload) + 3),
                ("unlock", self.LOCK_S * retry), ("hoist empty", (SAFE_Z - TRUCK_Z) * 60 / cr.speed(0) + 3)]
        busy = sum(x[1] for x in legs)
        target = self.cycle * (1 + 0.37 * sev)
        legs.append(("wait for the truck", max(2.0, target - busy)))
        self.legs, self.leg, self.leg_t = legs, 0, 0.0

    def step(self, dt=1.0):
        cr = self.cr
        for k, f in self.faults.items():
            f.step(dt)
            cr.faults[k] = f.sev
        self.t += dt * self.scale
        remaining = dt
        hoist_run, equiv = 0.0, 0.0
        ref = cr.swl + cr.pa
        while remaining > 1e-9:
            name, dur = self.legs[self.leg]
            use = min(remaining, dur - self.leg_t)
            frac0 = self.leg_t / dur
            self.leg_t += use
            frac = min(1.0, self.leg_t / dur)
            self.load = self.payload if name in ("hoist loaded", "trolley in", "lower loaded") else 0.0
            v = 0.0
            if name.startswith("trolley"):
                a, b = (TRUCK_X, self.cell_x) if name == "trolley out" else (self.cell_x, TRUCK_X)
                self.x = a + (b - a) * frac
                cr.trolley_km += abs(b - a) * (frac - frac0) / 1000 * self.scale
            elif name in ("lower empty", "hoist loaded", "lower loaded", "hoist empty"):
                top, bot = SAFE_Z, (self.cell_z if name in ("lower empty", "hoist loaded") else TRUCK_Z)
                up = name.startswith("hoist")
                self.z = (bot + (top - bot) * frac) if up else (top - (top - bot) * frac)
                v = (cr.speed(self.load) if up else -cr.speed(self.load)) * (1 if 0.05 < frac < 0.95 else 0.5)
                hoist_run += use
                equiv += use * ((self.load + cr.pa) / ref) ** 3
            self.v = v
            remaining -= use
            if self.leg_t >= dur - 1e-9:
                if name == "hoist loaded":
                    self.lift = cr.last_lift(self.payload)
                if name == "unlock":
                    cr.moves += 1
                    cr.rope_moves += 1
                    cr.struct += (self.payload / cr.swl) ** 3
                self.leg += 1
                self.leg_t = 0.0
                if self.leg >= len(self.legs):
                    self.new_move()
        cr.hours += hoist_run * self.scale / 3600
        cr.equiv += equiv * self.scale / 3600
        m = (self.load + cr.pa) * G * abs(self.v) / 60
        drag = 1 + 0.25 * cr.faults["brake_drag"]
        p = m / cr.h["efficiency"] * drag if self.v > 0 else (-m * cr.h["efficiency"] if self.v < 0 else 0.0)
        return {"x": self.x, "z": self.z, "v": self.v, "p": p, "load": self.load, "phase": self.legs[self.leg][0],
                "box": self.box, "payload": self.payload}

    def measure(self, true):
        return self.cr.reading(true, self.lift)
