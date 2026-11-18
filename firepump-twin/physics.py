"""A stand-in for FP-6501: the fire pump, its motor and controller, the jockey pump, the system pressure and the test records,
with injectable faults.

The real controller and test rig send the same points (see telemetry.points in the twin file). Nothing here is used by
Monitor: the expected values are computed in Monitor from the twin file only. This model only produces believable readings
and fault fingerprints for the tests, the figures and the live twin pages. Pure Python (math, random) so it also runs in the
browser under Pyodide.
"""
import math
import random


def _h(c, q_gpm):
    q = q_gpm / 1000.0
    return c[0] + c[1] * q + c[2] * q * q + c[3] * q * q * q


class FirePump:
    def __init__(self, twin, seed=1):
        self.t = twin
        d = twin["design"]
        self.p, self.s, self.m, self.sup = d["pump"], d["settings"], d["motor"], d["supply"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true pump ---------------------------------------------------------------------------------------------------------
    def head_true(self, q_gpm, speed):
        """Net pressure the pump really gives at flow q and speed (affinity laws around the worn curve)."""
        n0, p0, q0 = self.p["rated_speed_rpm"], self.p["rated_net_psi"], self.p["rated_flow_gpm"]
        w = self.faults["impeller_wear"]
        qc = q_gpm * n0 / speed
        h = _h(self.p["head_poly_kgpm"], qc) * (1 - 0.07 * w) - 0.03 * w * p0 * (qc / q0) ** 2
        return h * (speed / n0) ** 2

    def current(self, q_gpm, speed, volts):
        n0, m = self.p["rated_speed_rpm"], self.m
        bhp = _h(self.p["bhp_poly_kgpm"], q_gpm * n0 / speed) * (speed / n0) ** 3
        return bhp * 745.7 / (math.sqrt(3) * volts * m["efficiency"] * m["power_factor"])

    def static_suction(self):
        return self.s["nominal_static_suction_psi"] - 14.0 * self.faults["weak_supply"]

    def start_psi(self):
        return self.s["fire_pump_start_psi"] - 12.0 * self.faults["pressure_sensing_drift"]

    def jockey_ok(self):
        return self.faults["jockey_failed"] <= 0.3

    # one published message (pump at standby) ----------------------------------------------------------------------------
    def measure(self):
        f, s = self.faults, self.s
        suction = self.static_suction() + self.n(0.3)
        if self.jockey_ok():
            system = self.rnd.uniform(s["jockey_start_psi"] + 0.5, s["jockey_stop_psi"])
        else:
            system = s["jockey_start_psi"] - 1.0 - 3.0 * f["jockey_failed"] + self.n(0.3)
        rpm_c = 1792 + self.n(1.5)
        rq, rr = 1000 + self.n(8), 1781 + self.n(2)
        pq, pr = 1500 + self.n(10), 1772 + self.n(2)
        return {
            "suction_psi": round(suction, 2), "discharge_psi": round(system, 2), "flow_gpm": 0.0, "speed_rpm": 0.0, "pump_running": 0,
            "motor_current_a": 0.0, "supply_voltage_v": round(self.m["voltage_v"] + self.n(2), 1),
            "last_start_psi": round(self.start_psi() + self.n(0.6), 1),
            "time_to_run_s": round(s["time_to_run_s"] + 10.0 * f["starter_fault"] + self.n(0.15), 2),
            "auto_starts_30d": (1 + round(2 * f["jockey_failed"])) if not self.jockey_ok() else 0,
            "jockey_starts_24h": 0 if not self.jockey_ok() else max(1, round(4 + 60 * f["system_leak"] + self.n(1))),
            "jockey_run_min_24h": 0.0 if not self.jockey_ok() else round(max(0.5, 6 + 200 * f["system_leak"] + self.n(0.5)), 1),
            "churn_net_psi": round(self.head_true(0, rpm_c) * (1 + self.n(0.003)), 2), "churn_rpm": round(rpm_c, 1),
            "churn_packing_c": round(38 + 60 * f["packing_overtight"] + self.n(1), 1),
            "ft_rated_gpm": round(rq, 1), "ft_rated_net_psi": round(self.head_true(rq, rr) * (1 + self.n(0.004)), 2), "ft_rated_rpm": round(rr, 1),
            "ft_peak_gpm": round(pq, 1), "ft_peak_net_psi": round(self.head_true(pq, pr) * (1 + self.n(0.004)), 2), "ft_peak_rpm": round(pr, 1),
            "ft_peak_suction_psi": round(self.sup["residual_at_peak_psi"] - 22.0 * f["weak_supply"] + self.n(0.5), 2),
            "room_temp_c": round(18 + self.n(0.5), 1),
            "days_since_churn": round(self.rnd.uniform(0.2, 6.5) + 40 * f["tests_skipped"], 1),
            "days_since_flow_test": round(200 + self.rnd.uniform(0, 20) + 300 * f["tests_skipped"], 0),
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

    At standby the system pressure leaks down slowly; the jockey pump starts at its start pressure and stops at its stop
    pressure. Every `demo.churn_every_s` real seconds the controller runs a no-flow (churn) test for `demo.churn_run_s`
    seconds: start signal, time to run, the motor at speed, no flow. At the end of the test the churn pressure, speed and
    packing temperature are stored. If the jockey pump has failed, the pressure falls to the fire pump start pressure and the
    controller starts the fire pump on its own (an unplanned start), which then runs its minimum run time.
    """
    def __init__(self, twin, seed=6501):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.every = float(demo.get("churn_every_s", 45))
        self.run_s = float(demo.get("churn_run_s", 20))
        self.fp = FirePump(twin, seed)
        s = twin["design"]["settings"]
        self.jstart, self.jstop = s["jockey_start_psi"], s["jockey_stop_psi"]
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = False, 0
        self.reset()
        self.last = self.fp.measure()

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.timer, self.test, self.auto = 0.0, None, None
        self.p_sys, self.jockey, self.speed, self.running = 158.0, False, 0.0, False

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.fp.faults[k] = f.sev
        self.t += dt * self.scale
        fp = self.fp
        suction = fp.static_suction()
        ttr = self.twin["design"]["settings"]["time_to_run_s"] + 10.0 * fp.faults["starter_fault"]
        # scheduled churn test
        if self.test is None and self.auto is None:
            self.timer += dt
            if self.timer >= self.every:
                self.timer = 0.0
                if fp.faults["tests_skipped"] < 0.3:
                    self.test = 0.0
        phase = self.test if self.test is not None else self.auto
        if phase is not None:
            phase += dt
            on = phase >= ttr
            target = 1792.0 if on else 0.0
            self.speed += (target - self.speed) * min(1.0, dt * 1.5)
            if self.test is not None:
                self.test = phase
                if phase >= ttr + self.run_s:
                    m = fp.measure()
                    for key in ("churn_net_psi", "churn_rpm", "churn_packing_c"):
                        self.last[key] = m[key]
                    self.test, self.speed = None, 0.0
            else:
                self.auto = phase
                if phase >= ttr + self.run_s:
                    self.auto, self.speed = None, 0.0
            self.running = phase >= ttr and (self.test is not None or self.auto is not None)
            self.jockey = False
            if self.running:
                self.p_sys = suction + fp.head_true(0, max(self.speed, 300))
        else:
            self.running = False
            leak = 0.35 + 0.6 * fp.faults["system_leak"]
            self.p_sys -= leak * dt
            if fp.jockey_ok():
                if self.p_sys < self.jstart:
                    self.jockey = True
                if self.jockey:
                    self.p_sys += 2.0 * dt
                    if self.p_sys >= self.jstop:
                        self.jockey = False
            else:
                self.jockey = False
            if self.p_sys <= fp.start_psi():
                self.auto = 0.0
            self.p_sys = max(self.p_sys, suction)
        return {"running": self.running, "speed": self.speed if self.running else 0.0, "system_psi": self.p_sys, "suction_psi": suction,
                "jockey": self.jockey, "testing": self.test is not None, "auto": self.auto is not None}

    def measure(self, true):
        r = self.fp.measure()
        for key in ("churn_net_psi", "churn_rpm", "churn_packing_c"):
            r[key] = self.last[key]
        r["suction_psi"] = round(true["suction_psi"] + self.fp.n(0.2), 2)
        r["discharge_psi"] = round(true["system_psi"] + self.fp.n(0.2), 2)
        r["pump_running"] = 1 if true["running"] else 0
        if true["running"]:
            sp = true["speed"] + self.fp.n(1.0)
            r["speed_rpm"] = round(sp, 1)
            r["motor_current_a"] = round(self.fp.current(0.0, max(sp, 300), r["supply_voltage_v"]) + self.fp.n(0.5), 1)
        return r
