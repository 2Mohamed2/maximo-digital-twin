"""A stand-in for DG-6201: the QSK60 engine, the PI734F alternator, the radiator and jacket water heater, the starting
batteries, the fuel tanks and the automatic transfer switch, with injectable faults.

The real generator set controller, ATS controller and tank gauges send the same points (see telemetry.points in the
twin file). Nothing here is used by Monitor: the expected values are computed in Monitor from the twin file only. This
model only produces believable readings, start records and fault fingerprints for the tests, the figures and the pages.
"""
import math
import random


class Genset:
    def __init__(self, twin, seed=1):
        self.tw = twin
        d = twin["design"]
        self.rt, self.fu, self.ex, self.co, self.st, self.tk = d["rating"], d["fuel"], d["exhaust"], d["coolant"], d["start"], d["tanks"]
        self.test_kw = d["demo"]["test_load_kw"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.run_hours = 412.0
        self.last = None

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state ---------------------------------------------------------------------------------------------------
    def fuel_true(self, p):
        f = self.fu
        return (f["fuel_a_lph"] + f["fuel_b_lph_per_kw"] * p + f["fuel_c_lph_per_kw2"] * p * p) * (1 + 0.15 * self.faults["air_restriction"])

    def coolant_steady(self, lf, amb, on=True):
        """Coolant the engine settles at: thermostat or radiator-limited on load; heater set point in standby."""
        c, f = self.co, self.faults
        if not on:
            return c["heater_setpoint_c"] - (c["heater_setpoint_c"] - amb) * f["jacket_heater_failure"]
        rise = c["rise_full_k"] * (c["heat_frac_no_load"] + (1 - c["heat_frac_no_load"]) * lf) * (1 + 1.3 * f["radiator_fouling"])
        return min(103.0, max(c["thermostat_c"], amb + rise))

    def start_record(self, amb=24.0):
        """The values the controller and the ATS hold after a start: cranking dip, time to ready, outage to load, pre-start
        coolant, and the transient at the first load step."""
        f, n = self.faults, self.n
        bat, ats, air = f["starting_battery_weak"], f["ats_slow"], f["air_restriction"]
        ready = 7.0 + 6.0 * bat + n(0.25)
        step = self.st["step_pct"] * (1 - 0.6 * f["light_load_testing"])
        return {
            "last_crank_min_v": round(19.6 - 5.0 * bat + n(0.25), 2),
            "last_start_ready_s": round(ready, 2),
            "last_outage_to_load_s": round(ready + 1.1 + 3.0 * ats + n(0.06), 2),
            "last_prestart_coolant_c": round(self.coolant_steady(0, amb, on=False) + n(0.6), 1),
            "last_step_pct": round(step, 1),
            "last_step_freq_dip_pct": round((4.5 + 4.5 * air) * step / self.st["step_pct"] + n(0.2), 2),
            "last_step_freq_recovery_s": round(2.0 + 2.0 * air + n(0.1), 2),
            "last_step_volt_dip_pct": round(11.0 * step / self.st["step_pct"] + n(0.4), 2),
        }

    def true_state(self, load_kw=None, amb=24.0, mode=3, coolant=None):
        """One operating point. mode 0 standby, 1 starting, 2 cool-down, 3 test on load, 4 emergency on load.
        On a test, load_kw (default: the demo test load) is cut by the light-load fault."""
        f = self.faults
        if mode == 3:
            load_kw = (self.test_kw if load_kw is None else load_kw) * (1 - 0.78 * f["light_load_testing"])
        p = load_kw if mode >= 3 else 0.0
        lf = p / self.rt["standby_kw"]
        running = mode >= 1
        ex = self.ex
        if running:
            exh = ex["t0_c"] + ex["t_per_load_c"] * lf + ex["t_per_ambient"] * (amb - ex["ambient_ref_c"]) + 90.0 * f["air_restriction"]
            if mode == 1:
                exh = amb + 60.0
        else:
            exh = amb + 3.0
        cs = self.coolant_steady(lf, amb, on=mode >= 2)
        return dict(mode=mode, p=p, lf=lf, amb=amb, exh=exh, running=running,
                    coolant=cs if coolant is None else coolant, fuel=self.fuel_true(p) if running else 0.0)

    # one published message ------------------------------------------------------------------------------------------
    def measure(self, s=None, start=None):
        s = s or self.true_state()
        start = start or self.last or self.start_record(s["amb"])
        f, n = self.faults, self.n
        run = s["running"]
        inj = 75.0 * f["injector_fault"] if run and s["mode"] >= 3 else 0.0
        spread = (26.0 + abs(n(3.0))) if run and s["mode"] >= 2 else abs(n(1.0))
        cmax = s["exh"] + 0.5 * spread + 25.0 * (run and s["mode"] >= 2)
        cmin = cmax - spread - inj
        ea = s["exh"] + 3.0 - inj / 16 + n(3.0)
        eb = s["exh"] - 3.0 + n(3.0)
        r = {
            "run_mode": s["mode"], "engine_speed_rpm": round(1500 + n(2.0), 0) if run else 0,
            "fuel_rate_lph": round(s["fuel"] * (1 + n(0.012)), 1) if run else 0.0,
            "coolant_temp_c": round(s["coolant"] + n(0.3), 1),
            "oil_pressure_kpa": round(380 + 40 * s["lf"] + n(4.0), 0) if run else 0.0,
            "exhaust_temp_a_c": round(ea, 1), "exhaust_temp_b_c": round(eb, 1),
            "exhaust_cyl_max_c": round(cmax, 1), "exhaust_cyl_min_c": round(cmin, 1),
            "output_kw": round(max(0.0, s["p"] + n(2.0)), 1) if s["p"] > 0 else 0.0,
            "output_kvar": round(0.33 * s["p"] + n(2.0), 1) if s["p"] > 0 else 0.0,
            "voltage_v": round(400.0 + n(0.8), 1) if run and s["mode"] != 1 else 0.0,
            "frequency_hz": round(50.0 + n(0.02), 3) if run and s["mode"] != 1 else 0.0,
            "ambient_c": round(s["amb"] + n(0.1), 2),
            "ats_transfers_30d": 1,
            "battery_v": round((28.0 if run else 27.2 - 0.6 * f["starting_battery_weak"]) + n(0.05), 2),
            "day_tank_pct": round(92.0 + n(0.5), 1), "bulk_tank_pct": round(88.0 + n(0.2), 1),
            "fuel_water_ppm": round(70.0 + 420.0 * f["fuel_water"] + n(6.0), 0),
            "fuel_test_age_d": 196.0,
            "light_load_h": round(1.5 + 20.0 * f["light_load_testing"] + abs(n(0.2)), 2),
            "run_hours": round(self.run_hours, 2),
        }
        r.update(start)
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

    A standby set spends almost all its life waiting. To show something, the demo compresses the monthly test into a
    cycle of about two minutes: standby (jacket water heater holding the engine warm), an ATS test transfer that
    starts the set (cranking, run-up to rated voltage and frequency), load on for `cycle_load_s`, cool-down without
    load, stop. The start record (cranking dip, time to ready, outage to load, load-step transient) is taken at each
    start and held until the next one, as the controller and the ATS do. P.t is the visitor's local time in seconds;
    during the warm-up (dt >= 2 s) the clock is ignored so the radiator air starts at a normal value.
    """

    def __init__(self, twin, seed=6201):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.t_sb = float(demo.get("cycle_standby_s", 15))
        self.t_load = float(demo.get("cycle_load_s", 90))
        self.t_cd = float(demo.get("cycle_cooldown_s", 15))
        self.g = Genset(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = False, 0
        self.phase, self.timer = 0, 0.0          # phase = mode: 0 standby, 1 starting, 3 on load, 2 cool-down
        self.amb = 24.0
        self.coolant = self.g.coolant_steady(0, self.amb, on=False)
        self.g.last = self.g.start_record(self.amb)
        self.ready_at = self.g.last["last_start_ready_s"]

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.phase, self.timer, self.trip = 0, 0.0, 0
        self.running = False

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.g.faults[k] = f.sev
        self.t += dt * self.scale
        day = 0.0 if dt >= 2.0 else math.sin(2 * math.pi * ((self.t % 86400) / 86400 - 0.375))
        self.amb = 24.0 + 4.0 * day
        self.timer += dt
        if self.phase == 0 and self.timer >= self.t_sb:
            self.phase, self.timer = 1, 0.0
            self.g.last = self.g.start_record(self.amb)          # the ATS test transfer starts the set
            self.ready_at = self.g.last["last_start_ready_s"]
        elif self.phase == 1 and self.timer >= self.ready_at:
            self.phase, self.timer = 3, 0.0
        elif self.phase == 3 and self.timer >= self.t_load:
            self.phase, self.timer = 2, 0.0
        elif self.phase == 2 and self.timer >= self.t_cd:
            self.phase, self.timer = 0, 0.0
        self.running = self.phase != 0
        if self.running:
            self.g.run_hours += dt * self.scale / 3600
        s = self.g.true_state(None, self.amb, self.phase)
        tau = 15.0 if self.phase >= 2 else 8.0
        self.coolant += (s["coolant"] - self.coolant) * min(1.0, dt / tau)
        s["coolant"] = self.coolant
        if self.phase == 1:
            s["speed_frac"] = min(1.0, self.timer / max(self.ready_at, 1.0))
        return s

    def measure(self, true):
        r = self.g.measure(true, self.g.last)
        if true["mode"] == 1:
            r["engine_speed_rpm"] = round(1500 * true.get("speed_frac", 1.0), 0)
        return r
