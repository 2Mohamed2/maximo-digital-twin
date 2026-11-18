"""A stand-in for LS-5201: inflow, wet well, two Flygt NP 3153 pumps (duty/standby), check valves, rising main, the
station PLC and its cycle log, with injectable faults.

The real station sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests, the figures and the live pages. Pure Python (math, random) so it also runs in the browser.

Physics of the stand-in (the twin's relations, plus what the twin does not know):
  Pump curve H = H0 - (H0 - Hd) (q / (Q0 f))^2: a flow factor f < 1 means less flow at the same head (ragging f = 1 - 0.30 s,
  wear f = 1 - 0.25 s). Input power = the clean pump's power at that head x g (ragging g = 1 + 0.35 s: the rags add drag;
  wear g = 1 - 0.12 s). Both pumps see the same sewage, so ragging and wear act on both.
  System: H = (z_out - level) + k0 x kf x (n q)^2 with n pumps in parallel; a blocked or air-locked main has kf = 1 + 2 s.
  Wet well: A d(level)/dt = inflow + backflow - pumped flow. A passing check valve lets the main drain back for the first
  minute after each stop (14 s l/s). A slamming check valve closes against 0.03 + 0.35 s m/s of reverse flow.
  The level transmitter reads 0.85 s m low when fouled; the PLC runs the pumps on that reading, the float on the true level.
"""
import math
import random

from twin_calc import _k, power_exp


class Station:
    """Stateless stand-in: every measure() is an independent, plausible moment of the station's day."""
    OFFSET_M = 0.85
    BACKFLOW_LS = 14.0

    def __init__(self, twin, seed=1):
        self.tw = twin
        self.k = _k(twin)
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # pump and system ------------------------------------------------------------------------------------------------
    def factors(self):
        f = self.faults
        return (1 - 0.30 * f["impeller_ragging"] - 0.25 * f["impeller_wear"],
                (1 + 0.35 * f["impeller_ragging"]) * (1 - 0.12 * f["impeller_wear"]),
                1 + 2.0 * f["main_restriction"])

    def op(self, level, n):
        """Flow per pump (l/s), head (m) and input power per pump (kW) with n pumps running at this true level."""
        if n == 0:
            return 0.0, 0.0, 0.0
        k = self.k
        fl, g, kf = self.factors()
        st = k["zo"] - level
        q = math.sqrt(max(k["h0"] - st, 0.5) / (k["a"] / (k["qd"] * fl) ** 2 + k["k0"] * kf * n * n))
        h = st + k["k0"] * kf * (n * q) ** 2
        return q, h, power_exp(k, h) * g

    def offset(self):
        return self.OFFSET_M * self.faults["level_sensor_fault"]

    def v_rev(self):
        return 0.03 + 0.35 * self.faults["check_valve_slam"]

    def cycle(self, qc, pump=1):
        """The PLC's log of one pump cycle at inflow qc: rates before, during and after the run, mid-run values."""
        k, a60 = self.k, self.k["a60"]
        lt = k["lref"] + self.n(0.02)
        q, h, pw = self.op(lt, 1)
        qb = self.BACKFLOW_LS * self.faults["check_valve_passing"]
        return {
            "cyc_pump": pump,
            "cyc_fill_mm_min": round(qc / a60 * (1 + self.n(0.01)), 2),
            "cyc_draw_mm_min": round((q - qc) / a60 * (1 + self.n(0.01)), 2),
            "cyc_level_m": round(lt - self.offset() + self.n(0.003), 3),
            "cyc_discharge_bar": round((h - k["zg"] + lt) / k["pcoef"] + self.n(0.002), 4),
            "cyc_power_kw": round(pw * (1 + self.n(0.005)), 2),
            "cyc_after_stop_mm_min": round((qc + qb) / a60 * (1 + self.n(0.01)), 2),
            "cyc_stop_peak_bar": round(k["static_bar"] + k["jk"] * max(0.0, self.v_rev() + self.n(0.005)), 4),
        }

    def starts_per_h(self, qin, q1):
        """Station starts per hour (both pumps) at inflow qin with one pump of flow q1: 3600 / (fill time + run time)."""
        v = self.k["area"] * (self.k["start"] - self.k["stop"]) * 1000
        if qin <= 0 or q1 <= qin:
            return 1.0
        return 3600 / (v / qin + v / (q1 - qin))

    # one published message ------------------------------------------------------------------------------------------
    def measure(self):
        k, f, a60 = self.k, self.faults, self.k["a60"]
        dry = self.rnd.uniform(k["dry"] - k["amp"], k["dry"] + k["amp"])
        s = f["storm_inflow"]
        qin = (1 - s) * dry + s * k["storm"]
        off = self.offset()
        if s > 0 and qin > 0.9 * k["qd"]:
            n = 2
            lt = min(k["spill"], k["start2"] + 0.05 + s * self.rnd.uniform(0.3, 0.95))
            lm = lt - off
        else:
            n = 1 if self.rnd.random() < 0.5 else 0
            lm = self.rnd.uniform(1.6, k["start"]) if f["level_sensor_fault"] > 0.5 else self.rnd.uniform(k["stop"], k["start"])
            lt = lm + off
        q, h, pw = self.op(lt, n)
        lead = 1 if self.rnd.random() < 0.5 else 2
        on = {1: n >= 1 and (lead == 1 or n == 2), 2: n >= 1 and (lead == 2 or n == 2)}
        q1 = self.op(k["lref"], 1)[0]
        st = self.starts_per_h(dry, q1) / 2
        duty = min(1.0, dry / q1)
        r = {
            "level_m": round(lm + self.n(0.003), 3),
            "level_rate_mm_min": round((qin - n * q) / a60 + self.n(2.0), 2),
            "float_high": 1 if lt >= k["high"] else 0,
        }
        for p in (1, 2):
            r[f"p{p}_running"] = 1 if on[p] else 0
            r[f"p{p}_power_kw"] = round(pw * (1 + self.n(0.005)), 2) if on[p] else 0.0
            r[f"p{p}_starts_1h"] = max(0, round(st + self.n(0.6)))
            r[f"p{p}_run_h_7d"] = round(168 * duty / 2 + self.n(1.0), 1)
            r[f"p{p}_leak"] = 1 if (p == 2 and f["seal_leak"] > 0.5) else 0
        r["discharge_bar"] = round(((h - k["zg"] + lt) / k["pcoef"] if n else k["static_bar"]) + self.n(0.002), 4)
        r["main_flow_ls"] = round(n * q * (1 + self.n(0.005)), 2)
        r.update(self.cycle(dry, self.rnd.choice((1, 2))))
        return r


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

    The plant clock runs `demo.time_scale` times faster than real time and is integrated in steps of 5 s of plant time.
    Dry-weather inflow follows the day (low at night, peak mid-morning). The PLC starts the duty pump at the start level,
    the standby pump too at the assist level, stops both at the stop level, alternates the duty pump at every start and
    logs each single-pump cycle (the drawdown test) one minute after the stop.
    """
    SUB = 5.0

    def __init__(self, twin, seed=5201):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.x = Station(twin, seed)
        self.k = self.x.k
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.reset_state()

    def reset_state(self):
        self.level = self.k["lref"]
        self.on, self.duty = [], 1
        self.cyc, self.since_stop = None, 1e9
        self.starts = {1: [], 2: []}
        self.h7 = {1: 42.0, 2: 42.0}
        self.last = self.x.cycle(self.k["dry"], 2)

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        """Back to a healthy station at once (all faults to zero, level at the design level)."""
        for f in self.faults.values():
            f.sev = f.target = 0.0
            self.x.faults = {k: 0.0 for k in self.x.faults}
        self.reset_state()

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def inflow(self):
        k = self.k
        tod = (self.t % 86400) / 86400
        dry = k["dry"] + k["amp"] * math.sin(2 * math.pi * (tod - 1 / 6))      # peak at 10:00, low at 22:00
        s = self.x.faults["storm_inflow"]
        return (1 - s) * dry + s * k["storm"]

    def _sub(self, h):
        k, x = self.k, self.x
        qin = self.inflow()
        qb = x.BACKFLOW_LS * x.faults["check_valve_passing"] if (not self.on and self.since_stop < 60) else 0.0
        n = len(self.on)
        q, hd, pw = x.op(self.level, n)
        self.level = min(k["spill"], max(0.1, self.level + (qin + qb - n * q) * h / 1000 / k["area"]))
        self.t += h
        self.since_stop += h
        for p in (1, 2):
            if p in self.on:
                self.h7[p] += h / 3600
            self.h7[p] -= self.h7[p] * h / (7 * 86400)
            self.starts[p] = [s for s in self.starts[p] if self.t - s < 3600]
        lm = self.level - x.offset()
        a60 = k["a60"]
        if not self.on and lm >= k["start"]:
            self.on = [self.duty]
            self.starts[self.duty].append(self.t)
            self.cyc = {"cyc_pump": self.duty, "fill": (qin + qb) / a60, "mid": None}
            self.duty = 2 if self.duty == 1 else 1
        elif len(self.on) == 1 and lm >= k["start2"]:
            other = 2 if self.on[0] == 1 else 1
            self.on.append(other)
            self.starts[other].append(self.t)
            if self.cyc:
                self.cyc["mid"] = None
                self.cyc["assist"] = True
        elif self.on and lm <= k["stop"]:
            self.on = []
            self.since_stop = 0.0
            if self.cyc and self.cyc["mid"] and not self.cyc.get("assist"):
                self.cyc["peak"] = k["static_bar"] + k["jk"] * x.v_rev()
                self.cyc["stopped"] = True
            else:
                self.cyc = None
        if len(self.on) == 1 and self.cyc and self.cyc["mid"] is None and not self.cyc.get("assist") and lm <= k["lref"]:
            self.cyc["mid"] = {"draw": (q - qin) / a60, "lm": lm, "p": (hd - k["zg"] + self.level) / k["pcoef"], "pw": pw}
        if self.cyc and self.cyc.get("stopped") and self.since_stop >= 60:
            c, m, nn = self.cyc, self.cyc["mid"], x.n
            self.last = {
                "cyc_pump": c["cyc_pump"],
                "cyc_fill_mm_min": round(c["fill"] * (1 + nn(0.01)), 2),
                "cyc_draw_mm_min": round(m["draw"] * (1 + nn(0.01)), 2),
                "cyc_level_m": round(m["lm"] + nn(0.003), 3),
                "cyc_discharge_bar": round(m["p"] + nn(0.002), 4),
                "cyc_power_kw": round(m["pw"] * (1 + nn(0.005)), 2),
                "cyc_after_stop_mm_min": round((qin + x.BACKFLOW_LS * x.faults["check_valve_passing"]) / a60 * (1 + nn(0.01)), 2),
                "cyc_stop_peak_bar": round(c["peak"] + k["jk"] * nn(0.005), 4),
            }
            self.cyc = None
        return qin, qb, n, q, hd, pw

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.x.faults[k] = f.sev
        total = dt * self.scale
        m = max(1, int(math.ceil(total / self.SUB)))
        for _ in range(m):
            qin, qb, n, q, hd, pw = self._sub(total / m)
        n = len(self.on)
        q, hd, pw = self.x.op(self.level, n)
        return {"level": self.level, "level_meas": self.level - self.x.offset(), "qin": qin, "qb": qb, "n": n, "q": q, "h": hd,
                "pw": pw, "on": list(self.on)}

    def measure(self, true):
        k, x = self.k, self.x
        n, a60 = true["n"], k["a60"]
        net = true["qin"] + true["qb"] - n * true["q"]
        if true["level"] >= k["spill"] - 1e-6 and net > 0:
            net = 0.0                      # spilling over the weir: the level stands still, the overflow is not measured
        r = {
            "level_m": round(true["level_meas"] + x.n(0.003), 3),
            "level_rate_mm_min": round(net / a60 + x.n(2.0), 2),
            "float_high": 1 if true["level"] >= k["high"] else 0,
        }
        for p in (1, 2):
            on = p in true["on"]
            r[f"p{p}_running"] = 1 if on else 0
            r[f"p{p}_power_kw"] = round(true["pw"] * (1 + x.n(0.005)), 2) if on else 0.0
            r[f"p{p}_starts_1h"] = len(self.starts[p])
            r[f"p{p}_run_h_7d"] = round(self.h7[p], 1)
            r[f"p{p}_leak"] = 1 if (p == 2 and x.faults["seal_leak"] > 0.5) else 0
        r["discharge_bar"] = round(((true["h"] - k["zg"] + true["level"]) / k["pcoef"] if n else k["static_bar"]) + x.n(0.002), 4)
        r["main_flow_ls"] = round(n * true["q"] * (1 + x.n(0.005)), 2)
        r.update(self.last)
        return r
