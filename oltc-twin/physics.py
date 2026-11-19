"""A stand-in for PT-7501: grid, voltage regulator, on-load tap-changer, motor drive, OLTC oil and HV bushings, with faults.

The real device sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests, the figures and the live pages.
"""
import math
import random


class Transformer:
    def __init__(self, twin, seed=1):
        self.tw = twin
        d = twin["design"]
        self.tr, self.tp, self.ol, self.rg, self.mo = d["transformer"], d["tapping"], d["oltc"], d["regulator"], d["motor"]
        self.th, self.dg, self.bs = d["thermal"], d["dga"], d["bushings"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.r = self.tr["load_loss_kw"] / (self.tr["rated_mva"] * 1000)
        self.x = math.sqrt((self.tr["uk_pct"] / 100) ** 2 - self.r ** 2)
        self.s = self.tp["step_pct"] / 100

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # physics ---------------------------------------------------------------------------------------------------------
    def drop(self, ipu, pf):
        return ipu * (self.r * pf + self.x * math.sqrt(1 - pf * pf))

    def v2(self, v1, tap, ipu, pf):
        return v1 / (1 - (tap - self.tp["neutral"]) * self.s) - self.drop(ipu, pf)

    def band(self):
        return self.rg["band_pct"] - 0.5 * self.faults["band_too_narrow"]

    def last_op(self, cab):
        """Mean motor current and duration of a tap change made now."""
        st = self.faults["drive_stiff"]
        i = self.mo["current_a"] * (1 + self.mo["current_temp_coeff"] * (self.mo["ref_temp_c"] - cab)) * (1 + 0.6 * st)
        return i + self.n(0.02), self.mo["op_time_s"] * (1 + 0.45 * st) + self.n(0.04)

    def operating_point(self):
        """A random steady operating point with the regulator settled (used by the tests)."""
        v1 = 1.0 + self.n(0.015)
        ipu = min(1.0, max(0.15, 0.55 + self.n(0.15)))
        pf = min(0.99, max(0.85, 0.94 + self.n(0.02)))
        amb = 28 + self.n(6)
        vs = self.rg["setpoint_kv"] / self.tr["lv_kv"]
        tap = round(self.tp["neutral"] + (1 - v1 / (vs + self.drop(ipu, pf))) / self.s)
        tap = max(1, min(self.tp["positions"], tap))
        cab = amb + 8
        mi, mt = self.last_op(cab)
        return {"v1": v1, "ipu": ipu, "pf": pf, "tap": tap, "amb": amb, "cab": cab, "motor_i": mi, "op_t": mt}

    def reading(self, st):
        f, tr, bs = self.faults, self.tr, self.bs
        v2 = self.v2(st["v1"], st["tap"], st["ipu"], st["pf"])
        top = st["amb"] + 12 + 33 * st["ipu"] ** 2 + self.n(0.2)
        main_c2h2, main_c2h4 = self.dg["main_c2h2_ppm"] + abs(self.n(0.1)), self.dg["main_c2h4_ppm"] + self.n(0.3)
        hunt = f["band_too_narrow"]
        c1 = [c * (1 + self.n(0.0015)) for c in bs["c1_pf"]]
        c1[1] *= 1 + 0.065 * f["bushing_layer_short"]
        td = [t + self.n(0.008) for t in bs["tand_pct"]]
        td[2] += 0.65 * f["bushing_moisture"]
        return {
            "hv_voltage_kv": round(st["v1"] * tr["hv_kv"] + self.n(0.05), 3),
            "lv_voltage_kv": round(v2 * tr["lv_kv"] + self.n(0.02), 3),
            "lv_current_a": round(st["ipu"] * tr["lv_rated_a"] + self.n(1.0), 1),
            "power_factor": round(min(0.999, st["pf"] + self.n(0.002)), 4),
            "tap_position": int(st["tap"] + round(2 * f["tap_sensor_fault"])),
            "avr_setpoint_kv": self.rg["setpoint_kv"], "avr_band_pct": round(self.band(), 2),
            "motor_current_a": round(st["motor_i"], 3), "op_time_s": round(st["op_t"], 2), "cabinet_temp_c": round(st["cab"] + self.n(0.2), 1),
            "ops_total": int(161000 + 4000 * hunt), "ops_since_maint": int(70400 + 4000 * hunt),
            "ops_24h": max(0, int(round(self.ol["ops_per_day_expected"] * (1 + 4 * hunt) + self.n(3)))),
            "ops_365d": int(11000 + 25000 * hunt + self.n(150)), "years_since_maint": 6.4,
            "wear_sum_pu": round(6200 + 0.85 * self.ol["interrupter_life_ops"] * f["contact_wear"] + abs(self.n(20)), 1),
            "top_oil_temp_c": round(top, 2),
            "oltc_oil_temp_c": round(top + self.th["oltc_minus_top_oil_k"] + 10 * f["compartment_heating"] + self.n(0.3), 2),
            "ambient_temp_c": round(st["amb"] + self.n(0.1), 2),
            "main_c2h2_ppm": round(main_c2h2, 2), "main_c2h4_ppm": round(main_c2h4, 2),
            "oltc_c2h2_ppm": round(main_c2h2 + 0.8 + 140 * f["vacuum_loss"] + abs(self.n(0.2)), 2),
            "oltc_c2h4_ppm": round(main_c2h4 + 4 + 25 * f["vacuum_loss"] + 160 * f["compartment_heating"] + self.n(0.5), 2),
            "bsh_c1_l1_pf": round(c1[0], 2), "bsh_c1_l2_pf": round(c1[1], 2), "bsh_c1_l3_pf": round(c1[2], 2),
            "bsh_tand_l1_pct": round(td[0], 4), "bsh_tand_l2_pct": round(td[1], 4), "bsh_tand_l3_pct": round(td[2], 4),
        }

    def measure(self):
        return self.reading(self.operating_point())


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

    The load follows a daily profile on the plant clock (seconds of the day). For the demo the 132 kV grid voltage swings
    +/-3 % over 6 minutes, so the regulator leaves its band about once a minute: after the delay T1 it starts a tap change,
    the motor drive runs for the operation time and the tap moves one step. The duration and mean motor current of the
    last tap change are kept until the next one, as the motor-drive monitoring does.
    """

    def __init__(self, twin, seed=7501):
        self.twin = twin
        d = twin["design"]
        demo = d.get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.swing = float(demo.get("voltage_swing_pct", 3.0)) / 100
        self.period = float(demo.get("voltage_period_s", 360.0))
        self.u = Transformer(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 12 * 3600.0
        self.running, self.trip = True, 0
        self.reset()

    def reset(self):
        u = self.u
        self.clock, self.walk, self.timer, self.op = 0.0, 0.0, 0.0, None
        st = u.operating_point()
        st.update(v1=1.0, ipu=0.6, pf=0.95, amb=30.0, cab=38.0)
        vs = u.rg["setpoint_kv"] / u.tr["lv_kv"]
        st["tap"] = round(u.tp["neutral"] + (1 - 1.0 / (vs + u.drop(0.6, 0.95))) / u.s)
        st["motor_i"], st["op_t"] = u.last_op(st["cab"])
        self.st = st

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        u, st = self.u, self.st
        for k, f in self.faults.items():
            f.step(dt)
            u.faults[k] = f.sev
        self.t += dt * self.scale
        self.clock += dt
        h = (self.t / 3600.0) % 24
        self.walk = max(-0.05, min(0.05, self.walk + u.n(0.002) * math.sqrt(max(dt, 0.0))))
        st["ipu"] = max(0.2, min(1.0, 0.55 + 0.22 * math.sin(2 * math.pi * (h - 13) / 24) + self.walk))
        st["amb"] = 30 + 7 * math.sin(2 * math.pi * (h - 9) / 24)
        st["cab"] = st["amb"] + 8
        st["v1"] = 1.0 + self.swing * math.sin(2 * math.pi * self.clock / self.period)
        # regulator and tap change
        if self.op is not None:
            self.op["left"] -= dt
            if self.op["left"] <= 0:
                st["tap"] = max(1, min(u.tp["positions"], st["tap"] + self.op["dir"]))
                st["motor_i"], st["op_t"] = self.op["i"], self.op["t"]
                self.op, self.timer = None, 0.0
        v2 = u.v2(st["v1"], st["tap"], st["ipu"], st["pf"])
        dev = (v2 * u.tr["lv_kv"] / u.rg["setpoint_kv"] - 1) * 100
        if self.op is None:
            if abs(dev) > u.band():
                self.timer += dt
                if self.timer >= u.rg["t1_s"]:
                    i, t = u.last_op(st["cab"])
                    self.op = {"dir": 1 if dev < 0 else -1, "left": t, "i": i, "t": t}
            else:
                self.timer = 0.0
        return {"v1": st["v1"], "v2": v2, "tap": st["tap"], "dev_pct": dev, "op_active": self.op is not None,
                "op_dir": self.op["dir"] if self.op else 0, "timer": self.timer}

    def measure(self, true):
        return self.u.reading(self.st)
