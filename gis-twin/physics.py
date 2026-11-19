"""A stand-in for GIS-7401: one 145 kV gas-insulated bay (four SF6 compartments, breaker, switches, VT, CT), with injectable faults.

The real bay sends the same points (see telemetry.points in the twin file): gas density transmitters, the UHF partial
discharge monitor, the bay controller's breaker and switch monitoring, the protection relay's CT and VT values. Nothing
here is used by Monitor: the expected values are computed in Monitor from the twin file only. This model only produces
believable readings and fault fingerprints for the tests, the figures and the live pages. Pure Python (math, random).
"""
import math
import random

COMPS = ("cb", "bb", "ld", "vt")
T20 = 293.15


class SF6:
    """The twin file's SF6 equation of state, solved the other way round (density -> pressure at a temperature)."""
    def __init__(self, twin):
        s = twin["design"]["sf6"]
        self.R, self.a, self.q = s["r_j_kgk"], s["eos_a"], s["eos_q"]

    def z(self, p, T):
        a = self.a
        return 1 + p * (a[0] + a[1] / T + a[2] / T ** 2) + a[3] * p ** 2 / T

    def rho_from_p20(self, p20):
        q1, q2 = self.q
        d = p20 * 1e6 / (self.R * T20)
        for _ in range(30):
            f = d * self.R * T20 * (1 + q1 * d + q2 * d * d) / 1e6 - p20
            df = self.R * T20 * (1 + 2 * q1 * d + 3 * q2 * d * d) / 1e6
            d -= f / df
        return d

    def p_from_rho(self, rho, T):
        p = rho * self.R * T / 1e6
        for _ in range(40):
            p = rho * self.R * T * self.z(p, T) / 1e6
        return p


class Bay:
    def __init__(self, twin, seed=1):
        self.tw = twin
        d = twin["design"]
        self.cmp, self.b, self.sw, self.ld, self.ins = d["compartments"], d["breaker"], d["switches"], d["load"], d["instr"]
        self.ir = d["rating"]["ir_a"]
        self.sf6 = SF6(twin)
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.ops = 412

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state ----------------------------------------------------------------------------------------------------------
    def true_state(self, hour):
        L = self.ld
        prof = 0.5 - 0.5 * math.cos(2 * math.pi * (hour - 4) / 24)
        load = L["min_a"] + (L["peak_a"] - L["min_a"]) * prof
        amb = L["hall_c"] + L["hall_swing_c"] * math.sin(2 * math.pi * (hour - 9) / 24)
        return {"hour": hour, "load_a": load, "amb_c": amb}

    # one operation of the breaker and of the two switches (what the bay controller records) --------------------------------
    def operate(self):
        f, b, sw = self.faults, self.b, self.sw
        self.ops += 1
        return {
            "cb_open_ms": round(b["open_ms"] * (1 + 0.30 * f["cb_slow_mechanism"]) + self.n(0.25), 2),
            "cb_close_ms": round(b["close_ms"] * (1 + 0.20 * f["cb_slow_mechanism"]) + self.n(0.4), 2),
            "cb_armature_ms": round(b["armature_ms"] * (1 + 0.45 * f["cb_slow_mechanism"]) + self.n(0.08), 2),
            "cb_trip_coil_a": round(b["coil_v"] / b["coil_r_ohm"] * (1 + self.n(0.01)), 3),
            "cb_charge_s": round(b["charge_s"] + self.n(0.2), 2),
            "ds1_motor_a": round(sw["ds1_motor_a"] * (1 + 0.5 * f["ds_motor_wear"]) + self.n(0.03), 3),
            "ds1_time_s": round(sw["ds1_time_s"] * (1 + 0.4 * f["ds_motor_wear"]) + self.n(0.03), 2),
            "es2_motor_a": round(sw["es2_motor_a"] + self.n(0.03), 3),
            "es2_time_s": round(sw["es2_time_s"] + self.n(0.03), 2),
        }

    # one published message --------------------------------------------------------------------------------------------------
    def measure(self, true, ops=None):
        f = self.faults
        ops = ops or self.operate()
        load, amb = true["load_a"], true["amb_c"]
        r = {}
        base_p20 = {"cb": -0.002, "bb": -0.003, "ld": -0.002, "vt": -0.001}
        h2o = {"cb": 80.0, "bb": 60.0, "ld": 70.0, "vt": 90.0}
        for c in COMPS:
            cc = self.cmp[c]
            p20 = cc["fill_mpa"] + base_p20[c]
            slope = -0.3 + self.n(0.15)
            if c == "cb":
                p20 -= 0.035 * f["cb_compartment_leak"]
                slope -= 110 * f["cb_compartment_leak"]
            T = amb + cc["heat_k"] * (load / self.ir) ** 2 + self.n(0.1)
            p = self.sf6.p_from_rho(self.sf6.rho_from_p20(p20), T + 273.15)
            if c == "bb":                                         # the transmitter drifts, the gas does not
                p += 0.030 * f["density_sensor_drift"] * (T + 273.15) / T20
                slope += 35 * f["density_sensor_drift"]
            p += self.n(0.0004)
            w = h2o[c] + 0.6 * (amb - 24) + self.n(2) + (450 * f["moisture_ingress"] if c == "ld" else 0)
            dbm = -72 + self.n(1.2) + (38 * f["internal_pd"] if c == "bb" else 0)
            pps = abs(self.n(1.5)) + (250 * f["internal_pd"] if c == "bb" else 0)
            r.update({f"gas_{c}_p_mpa": round(p, 5), f"gas_{c}_t_c": round(T, 2), f"gas_{c}_slope_kpa_yr": round(slope, 2),
                      f"gas_{c}_h2o_ppmv": round(w, 1), f"pd_{c}_dbm": round(dbm, 1), f"pd_{c}_pps": round(pps, 1)})
        vbus = 132.0 * (1.01 + 0.01 * math.sin(2 * math.pi * true["hour"] / 24)) + self.n(0.05)
        i = load + self.n(1.0)
        r.update(ops)
        r.update({
            "cb_so2_ppmv": round(0.4 + 9.0 * f["cb_contact_wear"] + abs(self.n(0.05)), 2),
            "cb_wear_ka2s": round(140 + 300 * f["cb_contact_wear"], 1), "cb_ops": self.ops,
            "vt_bus_kv": round(vbus, 3), "vt_bay_kv": round(vbus * (1 + 0.02 * f["vt_drift"] + self.n(0.0008)), 3),
            "ct_meas_a": round(i, 1), "ct_prot_a": round(i * (1 + self.n(0.002)), 1), "amb_t_c": round(amb + self.n(0.1), 2),
        })
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

    The bay carries the feeder load of a daily profile (plant clock x time_scale). Every `demo.op_every_s` real seconds
    the breaker opens and recloses and the switches run, so the bay controller's last-operation values refresh. Steps of
    2 s or more (the browser warm-up) skip the operations.
    """
    def __init__(self, twin, seed=7401):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.every = float(demo.get("op_every_s", 30))
        self.bay = Bay(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 9 * 3600.0
        self.running, self.trip = True, 0
        self.timer, self.op_age = 0.0, 99.0
        self.last = self.bay.operate()

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.timer = 0.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.bay.faults[k] = f.sev
        self.t += dt * self.scale
        if 0 < dt < 2.0:
            self.timer += dt
            self.op_age += dt
            if self.timer >= self.every:
                self.timer, self.op_age = 0.0, 0.0
                self.last = self.bay.operate()
        true = self.bay.true_state((self.t / 3600.0) % 24)
        true["op_age_s"] = self.op_age
        return true

    def measure(self, true):
        return self.bay.measure(true, dict(self.last))
