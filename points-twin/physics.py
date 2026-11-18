"""A stand-in for PM-5501: the point machine, its turnout, the point heating and the condition monitoring unit, with
injectable faults.

The real CMU sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the expected
values are computed in Monitor from the twin file only. This model only produces believable throws, power curves and
fault fingerprints for the tests, the figures and the live pages.
Pure Python (math, random): it also runs in the browser under Pyodide.
"""
import math
import random

SQ3 = 1.7320508075688772
PF = 0.361          # power factor while driving: 500 W at 400 V and the rated 2 A of the data sheet


class Machine:
    def __init__(self, twin, seed=1):
        self.tw = twin
        d = twin["design"]
        self.m, self.c, self.md, self.ct, self.h = d["machine"], d["curve"], d["model"], d["control"], d["heating"]
        self.v = self.m["stroke_mm"] / 1000.0 / self.m["throw_time_s"]
        self.cf = self.md["efficiency"] / self.v
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.air = 14.0
        self.direction = 1
        self.throws_total, self.throws_oh = 412360, 381240

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # weather and heating ----------------------------------------------------------------------------------------------
    def weather(self):
        s = self.faults["ice_heater"]
        air = self.air * (1 - s) - 4.0 * s
        rail = air + (4.0 if air > 5 else -1.0) * (1 - s) - 1.0 * s
        on = 1 if rail < self.h["switch_on_c"] else 0
        cur = on * self.h["rated_current_a"] * (1 - s)
        return air, rail, on, cur

    def f_exp(self, rail):
        md = self.md
        return md["force_ref_n"] + md["k_cold_n_per_k"] * max(0.0, md["t_low_c"] - rail) + md["k_hot_n_per_k"] * max(0.0, rail - md["t_high_c"])

    def power(self, force):
        return self.md["no_load_w"] + force / self.cf

    # one throw, summarised as the CMU sends it ------------------------------------------------------------------------
    def throw(self):
        f = self.faults
        air, rail, on, hcur = self.weather()
        fx = self.f_exp(rail) * (1 + self.n(0.02))
        fu = fx * (1 + 0.3 * f["unlock_tight"])
        fd = fx * (1 + 0.9 * f["lubrication_loss"])
        fl = fx * (1 + 1.0 * f["ice_heater"] + 0.6 * min(1.0, 2 * f["obstruction"]))
        u = self.m["supply_v"] * (1 - 0.15 * f["supply_low"]) + self.n(2.0)
        tu = self.c["unlock_s"] + self.n(0.02)
        td = self.c["drive_s"] * (1 + 0.04 * f["lubrication_loss"]) * (1 + 0.05 * f["supply_low"]) + self.n(0.03)
        tl = self.c["lock_s"] + self.n(0.02)
        blocked = f["obstruction"] > 0.5
        if blocked:
            fl = self.m["throwing_force_n"] * (1 + self.n(0.005))
            tl = self.ct["time_limit_s"] - tu - td
        peak = self.c["unlock_peak_w"] * (1 + 1.8 * f["unlock_tight"]) * (1 + self.n(0.03))
        pd, pl, pu = self.power(fd), self.power(fl), self.power(fu)
        energy = pu * tu + pd * td + pl * tl + self.md["start_energy_j"] * peak / self.c["unlock_peak_w"]
        trailed = f["trailed"] > 0.5
        self.direction = 1 - self.direction
        self.throws_total += 1
        self.throws_oh += 1
        return {
            "throw_direction": self.direction, "throw_time_s": round(tu + td + tl, 3),
            "unlock_time_s": round(tu, 3), "drive_time_s": round(td, 3), "lock_time_s": round(tl, 3),
            "unlock_peak_w": round(peak, 1), "drive_power_mean_w": round(pd + self.n(2.0), 1),
            "drive_power_peak_w": round(self.power(fd * (1.12 + 0.1 * f["lubrication_loss"])) + self.n(2.0), 1),
            "lock_power_mean_w": round(pl + self.n(2.0), 1), "energy_kj": round(energy / 1000 * (1 + self.n(0.01)), 4),
            "motor_voltage_v": round(u, 1), "drive_current_a": round(pd / (SQ3 * u * PF) * (1 + self.n(0.01)), 3),
            "start_current_a": round(self.m["starting_current_a"] * u / self.m["supply_v"] * (1 + self.n(0.02)), 2),
            "detection_ok": 0 if (blocked or trailed) else 1,
            "detection_delay_s": round(self.ct["detection_delay_s"] + 0.9 * f["detector_adjust"] + abs(self.n(0.03)), 3),
            "detection_losses_24h": int(round(6 * f["detector_adjust"])),
            "trailed": 1 if trailed else 0,
            "air_temp_c": round(air + self.n(0.2), 2), "rail_temp_c": round(rail + self.n(0.2), 2),
            "heater_on": on, "heater_current_a": round(max(0.0, hcur + (self.n(0.2) if on else 0.0)), 2),
            "throws_total": self.throws_total, "throws_since_overhaul": self.throws_oh,
        }

    def measure(self):
        """A reading as the test and the figures use it: the summary of a fresh throw."""
        return self.throw()


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

    The points lie in one end position. Every `demo.throw_every_s` seconds the interlocking calls them to the other
    position: the motor runs through unlock, drive and lock, and the CMU stores the summary of that throw. Weather and
    heating are read live between throws. The time of day does not matter to this asset, so `t` is only a counter.
    """

    def __init__(self, twin, seed=5501):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.every = float(demo.get("throw_every_s", 20))
        self.mc = Machine(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.timer, self.run, self.pos = 0.0, None, 0.0
        self.last = self.mc.throw()
        self.pos = float(self.last["throw_direction"])

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.timer, self.run = 0.0, None

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.mc.faults[k] = f.sev
        self.t += dt * self.scale
        if self.run is None:
            self.timer += dt
            if self.timer >= self.every:
                self.timer = 0.0
                self.run = {"t": 0.0, "r": self.mc.throw(), "from": self.pos}
        else:
            self.run["t"] += dt
            if self.run["t"] >= self.run["r"]["throw_time_s"]:
                self.last = self.run["r"]
                self.pos = float(self.last["throw_direction"]) if self.last["detection_ok"] else (
                    self.run["from"] + (self.last["throw_direction"] - self.run["from"]) * 0.97)
                self.run = None
        phase, power, pos = "lying", 0.0, self.pos
        if self.run is not None:
            r, tt = self.run["r"], self.run["t"]
            if tt < r["unlock_time_s"]:
                phase, power = "unlock", r["unlock_peak_w"] if tt < 0.25 else r["drive_power_mean_w"]
                done = tt / self.mc.m["throw_time_s"]
            elif tt < r["unlock_time_s"] + r["drive_time_s"]:
                phase, power = "drive", r["drive_power_mean_w"]
                done = (r["unlock_time_s"] + (tt - r["unlock_time_s"]) / r["drive_time_s"] * self.mc.c["drive_s"]) / self.mc.m["throw_time_s"]
            else:
                phase, power = "lock", r["lock_power_mean_w"]
                done = min(1.0 if r["detection_ok"] else 0.97, (self.mc.c["unlock_s"] + self.mc.c["drive_s"] + (tt - r["unlock_time_s"] - r["drive_time_s"])) / self.mc.m["throw_time_s"])
            pos = self.run["from"] + (r["throw_direction"] - self.run["from"]) * done
        return {"position": pos, "moving": self.run is not None, "phase": phase, "power_w": power}

    def measure(self, true):
        air, rail, on, cur = self.mc.weather()
        r = dict(self.last)
        r["air_temp_c"] = round(air + self.mc.n(0.2), 2)
        r["rail_temp_c"] = round(rail + self.mc.n(0.2), 2)
        r["heater_on"] = on
        r["heater_current_a"] = round(max(0.0, cur + (self.mc.n(0.2) if on else 0.0)), 2)
        if self.faults["trailed"].sev > 0.5:
            r["trailed"], r["detection_ok"] = 1, 0
        if self.faults["detector_adjust"].sev > 0.01:
            r["detection_losses_24h"] = int(round(6 * self.faults["detector_adjust"].sev))
        return r
