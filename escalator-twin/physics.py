"""A stand-in for ES-5601: drive, step band, handrails, step chain, gearbox, brake and safety circuit, with injectable faults.

The real escalator controller sends the same points (see telemetry.points in the twin file). Nothing here is used by
Monitor: the expected values are computed in Monitor from the twin file only. This model only produces believable readings
and fault fingerprints for the tests, the figures and the live pages. Pure Python (math, random).

The "true" escalator follows the same equations as the twin, with the faults acting on the physical causes:
  brake_weak        brake force down 12 %, delay up 0.10 s (worn lining, larger air gap)
  brake_harsh       brake force up 60 %, delay down 0.15 s (brake set too hard)
  handrail_slip     the left handrail drive slips: from +1 % down to -13 % against the steps
  chain_wear        step chain elongation grows 1.05 % beyond its wear line (lubrication failure)
  step_band_drag    step band friction (no-load power) up 50 %, step sag trips
  gearbox_wear      gear oil 16 K hotter than the power explains, vibration x 3.5
  comb_damage       comb plate impact switch trips
  standby_disabled  the escalator no longer drops to stand-by speed
"""
import math
import random

G = 9.81


class Escalator:
    def __init__(self, twin, seed=1):
        self.tw = twin
        d = twin["design"]
        self.d = d
        ge, sp, dr, pa, br = d["geometry"], d["speed"], d["drive"], d["passengers"], d["brake"]
        self.H, self.sin = ge["rise_m"], math.sin(math.radians(ge["inclination_deg"]))
        self.vr, self.vsb = sp["rated_ms"], sp["standby_ms"]
        self.pnl = dr["noload_a_kw_per_m"] * self.H + dr["noload_b_kw"]
        self.eta, self.share, self.m = dr["eta_load"], dr["friction_share"], pa["mass_kg"]
        self.meq, self.td = br["m_eq_kg"], br["delay_s"]
        riser = ge["step_depth_m"] * math.tan(math.radians(ge["inclination_deg"]))
        self.mfull = br["brake_load_kg_per_step"] * self.H / riser
        self.ff = self.share * self.pnl * 1000 / self.vr
        # brake force set at commissioning so that a fully loaded down stop takes 0.70 m (inside 0.20 .. 1.00 m)
        a = self.vr ** 2 / 2 / (0.70 - self.vr * self.td)
        self.fb = a * (self.meq + self.mfull) + self.mfull * G * self.sin - self.ff
        self.hr, self.ch, self.gb, self.us = d["handrail"], d["chain"], d["gearbox"], d["usage"]
        self.demo = d["demo"]
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
    def power(self, v, ppm, direction):
        """True motor input power (kW) at step speed v with ppm passengers per minute."""
        drag = 1 + 0.5 * self.faults["step_band_drag"]
        x = ppm / 60 * self.m * G * self.H / 1000
        load = x / self.eta if direction > 0 else -x * self.eta
        return self.pnl * drag * v / self.vr + load

    def stop(self, v, load_kg, direction):
        """One stop: the brake values the controller records."""
        f = self.faults
        fb = self.fb * (1 - 0.12 * f["brake_weak"]) * (1 + 0.6 * f["brake_harsh"])
        td = self.td + 0.10 * f["brake_weak"] - 0.15 * f["brake_harsh"]
        ff = self.ff * (1 + 0.5 * f["step_band_drag"])
        a = max(0.05, (fb + ff + direction * load_kg * G * self.sin) / (self.meq + load_kg))
        return {"last_stop_distance_m": round(v * td + v * v / (2 * a) + self.n(0.003), 3),
                "last_stop_decel_ms2": round(a * (1 + self.n(0.004)), 4), "last_stop_delay_s": round(td + self.n(0.004), 3),
                "last_stop_speed_ms": round(v, 3), "last_stop_load_kg": round(max(0.0, load_kg + self.n(25)), 0),
                "last_stop_dir": direction}

    # one published message ------------------------------------------------------------------------------------------
    def reading(self, v, ppm, direction, p_avg, stop, amb, run_h, standby_share):
        f, n = self.faults, self.n
        p = self.power(v, ppm, direction)
        hl_pct = self.hr["nominal_pct"] - 14.0 * f["handrail_slip"]
        e = self.ch["elong0_pct"] + self.ch["wear_pct_per_1000h"] * run_h / 1000 + 1.05 * f["chain_wear"]
        oil = amb + self.gb["oil_rise0_k"] + self.gb["oil_k_per_kw"] * max(p_avg, 0) + 16.0 * f["gearbox_wear"]
        vm = v * (1 + n(0.001))
        r = {
            "motor_power_kw": round(p + n(0.01 * self.pnl + 0.008 * abs(p - self.pnl)), 3),
            "motor_power_avg_kw": round(p_avg, 3), "step_speed_ms": round(vm, 4),
            "run_mode": 2 if v > (self.vr + self.vsb) / 2 else 1, "direction": direction,
            "passengers_per_min": round(max(0.0, ppm * (1 + n(0.015))), 1),
            "handrail_left_ms": round(v * (1 + hl_pct / 100 + n(0.0012)), 4),
            "handrail_right_ms": round(v * (1 + self.hr["nominal_pct"] / 100 + n(0.0012)), 4),
            "chain_elongation_pct": round(e + n(0.01), 3), "gear_oil_temp_c": round(oil + n(0.5), 2),
            "gearbox_vib_mms": round(self.gb["vib_baseline_mms"] * (1 + 2.5 * f["gearbox_wear"]) * (1 + n(0.05)), 3),
            "ambient_temp_c": round(amb, 1),
            "trips_comb_24h": int(round(7 * f["comb_damage"])) + (1 if self.rnd.random() < 0.15 else 0),
            "trips_handrail_inlet_24h": 1 if self.rnd.random() < 0.1 else 0,
            "trips_step_sag_24h": int(round(4 * f["step_band_drag"])),
            "trips_estop_24h": self.rnd.choice((0, 0, 1, 1, 2)),
            "run_hours": round(run_h, 1), "standby_share_24h": round(max(0.0, standby_share - 0.28 * f["standby_disabled"] + n(0.01)), 3),
        }
        r.update(stop)
        return r

    def measure(self, ppm=None, direction=1, standby=None):
        """A random steady reading (tests): passenger flow, stand-by or rated speed, a random last stop."""
        rnd = self.rnd
        ppm = rnd.uniform(0, 95) if ppm is None else ppm
        standby = (ppm < 1 and self.faults["standby_disabled"] < 0.5) if standby is None else standby
        v = self.vsb if standby else self.vr
        p_avg = self.power(self.vr, rnd.uniform(15, 60), direction)
        stop = self.stop(rnd.choice((self.vr, self.vr, self.vsb)), rnd.uniform(0, 3000), rnd.choice((1, 1, -1)))
        return self.reading(v, ppm, direction, p_avg, stop, self.demo["ambient_c"] + self.n(1.5),
                            self.us["run_hours_now"] + rnd.uniform(0, 500), 0.30)


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

    A train arrives every demo.train_every_s seconds; its passengers ride up in a burst that decays with demo.train_tau_s.
    When nobody has entered for demo.standby_after_s seconds the escalator drops to stand-by speed. Every demo.stop_every_s
    seconds the controller records a stop (brake values). The readings do not depend on the time of day.
    """
    TAU_AVG = 60.0

    def __init__(self, twin, seed=5601):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.es = Escalator(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.reset()

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        es = self.es
        self.clock, self.idle, self.stop_timer = 30.0, 0.0, 0.0
        self.v = es.vr
        self.p_avg = es.power(es.vr, 30.0, 1)
        self.run_h = es.us["run_hours_now"]
        self.last_stop = es.stop(es.vr, 1200.0, 1)

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        es, dm = self.es, self.es.demo
        for k, f in self.faults.items():
            f.step(dt)
            es.faults[k] = f.sev
        self.t += dt * self.scale
        self.run_h += dt * self.scale / 3600
        self.clock = (self.clock + dt) % dm["train_every_s"]
        ppm = dm["train_peak_ppm"] * math.exp(-self.clock / dm["train_tau_s"]) if self.clock > 2 else 0.0
        ppm = ppm if ppm >= 1.0 else 0.0
        self.idle = 0.0 if ppm > 0 else self.idle + dt
        standby = self.idle >= dm["standby_after_s"] and es.faults["standby_disabled"] < 0.5
        self.v = es.vsb if standby else es.vr
        p = es.power(self.v, ppm, 1)
        self.p_avg += min(1.0, dt / self.TAU_AVG) * (p - self.p_avg)
        self.stop_timer += dt
        if self.stop_timer >= dm["stop_every_s"]:
            self.stop_timer = 0.0
            self.last_stop = es.stop(self.v, es.rnd.uniform(0, 2500) if ppm > 0 else es.rnd.uniform(0, 300), 1)
        return {"v": self.v, "ppm": ppm, "p_avg": self.p_avg, "standby": standby, "amb": dm["ambient_c"],
                "run_h": self.run_h, "standby_share": 0.30, "stop": dict(self.last_stop)}

    def measure(self, true):
        return self.es.reading(true["v"], true["ppm"], 1, true["p_avg"], true["stop"], true["amb"], true["run_h"], true["standby_share"])
