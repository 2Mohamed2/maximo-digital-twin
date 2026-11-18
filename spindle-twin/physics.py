"""A stand-in for MC-4801: motor spindle, drive, tool, cut, cooling, lubrication, clamping and crash sensor, with injectable faults.

The real machine sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable CNC and sensor
readings and fault fingerprints for the tests, the figures and the live pages. Pure Python (math, random).
"""
import math
import random


def op_speeds(op):
    """Spindle speed (rpm) and feed rate (mm/min) of one operation of the part program."""
    n = op["vc_m_min"] * 1000 / (math.pi * op["dc_mm"])
    return n, op["fz_mm"] * n * op["z"]


def kienzle_kw(twin, op, n, vf):
    """True cutting power of the healthy tool (same physics the twin expects; the stand-in has no other source of truth)."""
    m = twin["design"]["material"]
    ae, dc = op["ae_mm"], op["dc_mm"]
    phi = math.acos(max(-1.0, min(1.0, 1 - 2 * ae / dc)))
    hm = 2 * (vf / (n * op["z"])) * ae / (dc * phi)
    kc = m["kc1_n_mm2"] * hm ** (-m["mc"]) * (1 - op["rake_deg"] / 100)
    return ae * op["ap_mm"] * vf * kc / 60e6


class Spindle:
    def __init__(self, twin, seed=1):
        self.tw = twin
        d = twin["design"]
        self.sp, self.dr, self.th, self.vb, self.co, self.cl = d["spindle"], d["drive"], d["thermal"], d["vibration"], d["cooling"], d["clamping"]
        self.ops = d["program"]["operations"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.shocks = 2

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    def idle_kw(self, n):
        dr = self.dr
        return dr["idle_p0_kw"] + dr["idle_p1_kw_per_krpm"] * n / 1000 + dr["idle_p2_kw_per_krpm2"] * (n / 1000) ** 2

    # true state ---------------------------------------------------------------------------------------------------
    def power_kw(self, op, n, in_cut):
        if n <= 0:
            return 0.0
        _, vf = op_speeds(op)
        pc = kienzle_kw(self.tw, op, n, vf) * (1 + 0.6 * self.faults["tool_wear"]) if in_cut else 0.0
        return pc / self.dr["eta"] + self.idle_kw(n)

    def thermal(self, navg, pavg, cin):
        f, th = self.faults, self.th
        bd, lu, co = f["bearing_damage"], f["lubrication_starvation"], f["cooling_failure"]
        x = navg / 1000
        return {"front": cin + th["front_f0"] + th["front_f1"] * x + 9 * bd + 11 * lu + 3 * co,
                "rear": cin + th["rear_r0"] + th["rear_r1"] * x + 10 * lu + 3 * co,
                "motor": cin + th["motor_m0"] + th["motor_m1"] * pavg + 20 * co,
                "growth": th["growth_g0_um"] + th["growth_g1_um"] * x + 3 * bd + 3 * lu + 16 * co}

    # one published message ------------------------------------------------------------------------------------------
    def reading(self, op, n, in_cut, navg, pavg, clamp_kn):
        f, vb, co = self.faults, self.vb, self.co
        nn = self.n
        p = self.power_kw(op, n, in_cut)
        cin = co["inlet_c"] + nn(0.2)
        T = self.thermal(navg, pavg, cin)
        flow = co["flow_nominal_lpm"] - 6 * f["cooling_failure"] + nn(0.1)
        heat = 0.5 * self.idle_kw(navg) + 0.08 * pavg
        _, vf = op_speeds(op)
        env = (vb["env0_g"] + vb["env1_g"] * n / self.sp["n_max_rpm"]) * (1 + 4 * f["bearing_damage"] + 0.5 * f["lubrication_starvation"])
        v1x = (vb["v1x0_mms"] + vb["v1x1_mms"] * (n / 10000) ** 2) * (1 + 3 * f["tool_imbalance"] + 2.5 * f["spindle_crash"])
        return {
            "speed_rpm": round(n * (1 + nn(0.0005)), 1) if n > 0 else 0.0, "speed_avg_rpm": round(navg, 1),
            "power_kw": round(p * (1 + nn(0.015)), 3) if n > 0 else 0.0, "power_avg_kw": round(pavg, 3),
            "running": 1 if n > 0 else 0,
            "tool_number": op["tool"], "tool_diameter_mm": op["dc_mm"], "tool_teeth": op["z"], "tool_rake_deg": op["rake_deg"],
            "tool_mass_kg": op["mass_kg"], "in_cut": 1 if (in_cut and n > 0) else 0,
            "ap_mm": op["ap_mm"], "ae_mm": op["ae_mm"], "feed_mm_min": round(vf, 1) if n > 0 else 0.0,
            "front_brg_temp_c": round(T["front"] + nn(0.4), 2), "rear_brg_temp_c": round(T["rear"] + nn(0.4), 2),
            "motor_temp_c": round(T["motor"] + nn(0.6), 2), "coolant_in_c": round(cin, 2),
            "coolant_out_c": round(cin + heat / (max(flow, 0.5) / 60 * 4.18), 2), "coolant_flow_lpm": round(flow, 2),
            "oilair_pressure_bar": round(co["oilair_nominal_bar"] - 2 * f["lubrication_starvation"] + nn(0.05), 3),
            "z_growth_um": round(T["growth"] + nn(1.0), 2),
            "vib_1x_mms": round(v1x * (1 + nn(0.05)), 4) if n > 0 else 0.0,
            "vib_env_g": round(env * (1 + nn(0.06)), 4) if n > 0 else 0.0,
            "clamp_force_kn": round(clamp_kn, 2),
            "shock_max_g_24h": round(1.2 + abs(nn(0.3)) + 30 * f["spindle_crash"], 2),
            "shock_count_total": self.shocks + (1 if f["spindle_crash"] > 0.28 else 0),
        }

    def clamp_kn(self):
        return self.cl["nominal_kn"] * (1 - 0.4 * self.faults["clamping_force_loss"]) + self.n(0.15)

    def measure(self, op=None):
        """One steady-state reading in the middle of a cut (mean speed and power = the current ones)."""
        op = op or self.rnd.choice(self.ops[:3])
        n, _ = op_speeds(op)
        p = self.power_kw(op, n, True)
        return self.reading(op, n, True, n, p, self.clamp_kn())


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

    One real second is `demo.time_scale` machine seconds. The machine runs the part program of the twin file in a loop:
    each operation cuts for `demo.op_s` machine seconds (approach and retract in air at both ends), then a tool change of
    `demo.change_s` seconds with the spindle stopped; the clamping force is measured at each tool change. The edge keeps
    exponential means of speed and power with the time constant `demo.mean_tau_s`.
    """

    def __init__(self, twin, seed=4801):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.op_s, self.ch_s, self.tau = float(demo.get("op_s", 90)), float(demo.get("change_s", 10)), float(demo.get("mean_tau_s", 300))
        self.sp = Spindle(twin, seed)
        self.ops = self.sp.ops
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
        self.clock, self.navg, self.pavg = 0.0, None, None
        self.clamp = self.sp.clamp_kn()
        self.crashed = False

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.sp.faults[k] = f.sev
        if self.sp.faults["spindle_crash"] > 0.28 and not self.crashed:
            self.crashed = True
            self.sp.shocks += 1
        elif self.sp.faults["spindle_crash"] < 0.05:
            self.crashed = False
        h = dt * self.scale
        self.t += h
        cyc = self.op_s + self.ch_s
        before = int(self.clock // cyc)
        self.clock = (self.clock + h) % (cyc * len(self.ops))
        i, tin = int(self.clock // cyc), self.clock % cyc
        if i != before:
            self.clamp = self.sp.clamp_kn()                     # new tool clamped: the force is measured
        op = self.ops[i]
        n, _ = op_speeds(op)
        if tin >= self.op_s:                                     # tool change: spindle stopped, next tool shown
            op, n, cut = self.ops[(i + 1) % len(self.ops)], 0.0, False
        else:
            cut = 6.0 <= tin <= self.op_s - 6.0
        p = self.sp.power_kw(op, n, cut)
        if self.navg is None:
            self.navg, self.pavg = n, p
        a = 1 - math.exp(-h / self.tau)
        self.navg += a * (n - self.navg)
        self.pavg += a * (p - self.pavg)
        self.running = n > 0
        return {"op": op, "op_name": op["op"], "n": n, "in_cut": cut, "power": p, "navg": self.navg, "pavg": self.pavg,
                "phase": "tool change" if n == 0 else ("cutting" if cut else "air")}

    def measure(self, true):
        return self.sp.reading(true["op"], true["n"], true["in_cut"], true["navg"], true["pavg"], self.clamp)
