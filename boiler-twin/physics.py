"""A stand-in for BL-4501: the shell boiler, economiser, burner, TDS blowdown, feed pump and safety test log, with injectable faults.

The real boiler sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests, the figures and the live pages. Pure Python (math, random).
"""
import math
import random

import twin_calc as tc


class Boiler:
    def __init__(self, twin, seed=1):
        self.twin = twin
        self.k = tc._k(twin)
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.lwco_h, self.sv_h = 9.0, 70.0          # test clocks (h since the last test), advanced by the Plant
        self.burner_kw = self.true_state(1.0)["fuel"] * 1.1   # burner sized 10 % above the full-load firing (assumption)

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    def true_state(self, load=1.0, t_air=25.0):
        k, f = self.k, self.faults
        steam = k["rated"] * load
        p = k["p_op"] + 0.05 * (1 - load)
        ts = tc.tsat(k, p)
        o2 = k["o2d"] + 5.0 * f["excess_air_high"]
        t_exit = ts + k["app"] * load ** k["appn"] + 45 * f["fireside_fouling"] + 35 * f["waterside_scale"] + 6 * f["excess_air_high"]
        eps = k["eps_d"] - 0.25 * f["economiser_fouling"]
        tfw = k["tfw"]
        stack = t_exit - eps * (t_exit - tfw)
        dp = k["dp_d"] * load ** k["dpn"] * (1 + 0.6 * f["fireside_fouling"]) * (1 + 0.15 * f["excess_air_high"])
        # water chemistry: TDS control holds the setpoint; a stuck valve lets it climb; a passing valve dumps water
        cf = k["cf_d"]
        cb = k["cset"] + 2500 * f["tds_control_fault"]
        bd = steam * cf / (cb - cf) + 0.15 * steam * f["blowdown_valve_passing"]
        cb = cf * (steam + bd) / bd
        feed = steam + bd
        valve = min(100.0, 100 * steam * cf / (cb - cf) / (0.25 * k["rated"])) * (1 - f["blowdown_valve_passing"])
        # efficiency (true) and gas
        hg, hb, hfw = tc.h_steam(k, p), tc.h_boil(k, p), tc.h_liq(k, tfw)
        qout = (steam * (hg - hfw) + bd * (hb - hfw)) / 3600
        eta = 100 - tc.siegert(k, stack, o2, t_air) - tc.rad_loss(k, load)
        fuel = qout / eta * 100
        q_eco = fuel * (tc.siegert(k, t_exit, o2, t_air) - tc.siegert(k, stack, o2, t_air)) / 100
        t_eco_out = tc.t_liq(k, hfw + q_eco * 3600 / feed)
        # feed pump and level
        pump = (k["p0"] - k["kp"] * (feed / 1000) ** 2) * (1 - 0.3 * f["feed_pump_wear"])
        short = max(0.0, 1.5 - (pump - p))
        level = -60 * short
        return dict(load=load, steam=steam, p=p, tsat=ts, o2=o2, t_exit=t_exit, stack=stack, dp=dp, cb=cb, cf=cf, bd=bd,
                    feed=feed * (1 - 0.01 * short), valve=valve, fuel=fuel, eta=eta, gas=fuel * 3.6 / k["lhv"], t_eco_out=t_eco_out,
                    tfw=tfw, pump=pump, level=level, t_air=t_air, co=12 + 4 * f["excess_air_high"],
                    hard=0.002 + 0.06 * f["waterside_scale"], q_eco=q_eco, eps=eps)

    def measure(self, true=None):
        s = true or self.true_state()
        n, f, k = self.n, self.faults, self.k
        return {
            "steam_flow_kgh": round(s["steam"] * (1 + n(0.003)), 1),
            "steam_pressure_barg": round(s["p"] + n(0.02), 3),
            "drum_level_mm": round(s["level"] + n(3), 1),
            "feed_flow_kgh": round(s["feed"] * (1 + n(0.003)), 1),
            "feed_temp_c": round(s["tfw"] + n(0.2), 2),
            "eco_water_out_c": round(s["t_eco_out"] + n(0.3), 2),
            "feed_pump_p_barg": round(s["pump"] + n(0.05), 3),
            "feed_cond_uscm": round(s["cf"] * (1 + n(0.01)), 1),
            "feed_hardness_mmol": round(max(0.0, s["hard"] + n(0.0005)), 4),
            "gas_flow_nm3h": round(s["gas"] * (1 + n(0.003)), 2),
            "burner_load_pct": round(100 * s["fuel"] / self.burner_kw + n(0.3), 1),
            "air_temp_c": round(s["t_air"] + n(0.2), 2),
            "flue_exit_c": round(s["t_exit"] + n(0.6), 2),
            "stack_c": round(s["stack"] + n(0.4), 2),
            "o2_pct": round(s["o2"] + n(0.05), 3),
            "co_ppm": round(max(0.0, s["co"] + n(2)), 1),
            "flue_dp_mbar": round(s["dp"] * (1 + n(0.015)), 3),
            "boiler_cond_uscm": round(s["cb"] * (1 + n(0.01)), 0),
            "blowdown_valve_pct": round(s["valve"] + n(0.5), 1),
            "lwco_test_hours_since": round(self.lwco_h + 60 * f["safety_tests_overdue"], 1),
            "sv_test_hours_since": round(self.sv_h + 250 * f["safety_tests_overdue"], 1),
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

    The steam demand swings between demo.load_min and demo.load_max over demo.load_period_s real seconds; the pressure
    controller fires the burner to match, the TDS control holds the boiler water, the level control the water level. The
    low-water limiter test resets every 24 h and the safety valve lift every 168 h of plant time, unless the tests are skipped.
    The load follows the demo clock, not the time of day, so the page looks the same whenever it is opened.
    """

    def __init__(self, twin, seed=4501):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.lo, self.hi = float(demo.get("load_min", 0.6)), float(demo.get("load_max", 1.0))
        self.period = float(demo.get("load_period_s", 900))
        self.b = Boiler(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.clock = 0.0
        self.running, self.trip = True, 0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.clock = 0.0
        self.running, self.trip = True, 0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.b.faults[k] = f.sev
        self.t += dt * self.scale
        self.clock += dt
        k = self.b.k
        hours = dt * self.scale / 3600
        self.b.lwco_h += hours
        self.b.sv_h += hours
        if self.b.lwco_h >= k["lwco"] * 0.95:
            self.b.lwco_h = 0.0
        if self.b.sv_h >= k["sv"] * 0.95:
            self.b.sv_h = 0.0
        mid, amp = (self.lo + self.hi) / 2, (self.hi - self.lo) / 2
        load = mid + amp * math.sin(2 * math.pi * self.clock / self.period)
        t_air = 25 + 3 * math.sin(2 * math.pi * self.clock / (self.period * 3))
        return self.b.true_state(load, t_air)

    def measure(self, true):
        return self.b.measure(true)
