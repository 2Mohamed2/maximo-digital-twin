"""A stand-in for K-2201: the two-stage reciprocating compressor, its valves, packing, lubricator and running gear,
with injectable faults.

The real unit sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and
fault fingerprints for the tests, the figures and the live pages.

How the stand-in works: the two stages must pass the same mass flow, so the interstage pressure settles where the
stage 1 capacity equals the stage 2 capacity (each from its volumetric efficiency, minus any leak through a valve or the
rings). A leak heats the gas: a leaking valve heats its own cover most, worn rings heat the whole cylinder a little.
"""
import math
import random

ATM = 1.01325
IN = 0.0254
COOLER_DP = 0.5            # bar across the interstage cooler and separator (assumption)


class Compressor:
    def __init__(self, twin, seed=1):
        self.t = twin
        d = twin["design"]
        self.d = d
        self.s = d["stages"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        fr = d["frame"]
        self.stroke = fr["stroke_in"] * IN
        arod = math.pi / 4 * (fr["rod_diameter_in"] * IN) ** 2
        self.disp = [(2 * math.pi / 4 * (s["bore_in"] * IN) ** 2 - arod) * self.stroke for s in self.s]
        self.k = d["gas"]["k"]

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state -------------------------------------------------------------------------------------------------------
    def _ve(self, i, ps, pd):
        r = (pd + ATM) / (ps + ATM)
        return 1 - r / 100 - self.s[i]["clearance"] * (r ** (1 / self.k) - 1)

    def _q(self, i, ps, pd, ts, leak, rpm):
        return (self._ve(i, ps, pd) - leak) * self.disp[i] * rpm * 60 * (ps + ATM) / ATM * 273.15 / (ts + 273.15)

    def _td(self, i, ps, pd, ts):
        s = self.s[i]
        psi, pdi = (ps + ATM) * (1 - s["loss_suction"]), (pd + ATM) * (1 + s["loss_discharge"])
        re = (pdi / psi) ** ((self.k - 1) / self.k)
        f = 0.02 + 0.002 * s["bore_in"]
        return (ts + 273.15) * (1 - f) / (1 - f * re) * re - 273.15

    def state(self, ps1, ts1, ts2, pd2, rpm):
        f = self.faults
        leak1 = 0.10 * f["discharge_valve_leak"]
        leak2 = 0.08 * f["suction_valve_leak"] + 0.06 * f["ring_wear"]
        lo, hi = ps1 + 5, pd2 - 5
        for _ in range(60):                                     # interstage pressure: stage 1 flow = stage 2 flow
            mid = (lo + hi) / 2
            q1 = self._q(0, ps1, mid, ts1, leak1, rpm)
            q2 = self._q(1, mid - COOLER_DP, pd2, ts2, leak2, rpm)
            lo, hi = (mid, hi) if q1 > q2 else (lo, mid)
        pd1 = (lo + hi) / 2
        ps2 = pd1 - COOLER_DP
        q = self._q(0, ps1, pd1, ts1, leak1, rpm)
        res1 = 16.0 * f["discharge_valve_leak"]
        res2 = 14.0 * f["suction_valve_leak"] + 12.0 * f["ring_wear"]
        return dict(ps1=ps1, pd1=pd1, ps2=ps2, pd2=pd2, ts1=ts1, ts2=ts2, q=q, rpm=rpm,
                    tde1=self._td(0, ps1, pd1, ts1), tde2=self._td(1, ps2, pd2, ts2), res1=res1, res2=res2)

    # one published message --------------------------------------------------------------------------------------------
    def measure(self):
        f, d = self.faults, self.d
        st = self.state(self.s[0]["ps_barg"] + self.n(0.08), self.s[0]["ts_c"] + self.n(0.3), self.s[1]["ts_c"] + self.n(0.3),
                        self.s[1]["pd_barg"] + 18.0 * f["discharge_pressure_high"] + self.n(0.2), d["operation"]["rpm"])
        return self.reading(st)

    def reading(self, st):
        f, d, n = self.faults, self.d, self.n
        rise, off = d["valves"]["suction_cover_rise_k"], d["valves"]["discharge_cover_offset_k"]
        td1, td2 = st["tde1"] + st["res1"], st["tde2"] + st["res2"]
        dvl, svl, rw = f["discharge_valve_leak"], f["suction_valve_leak"], f["ring_wear"]
        r = {
            "ps1_barg": round(st["ps1"], 3), "ts1_c": round(st["ts1"], 2), "pd1_barg": round(st["pd1"] + n(0.05), 3),
            "td1_c": round(td1 + n(0.4), 2), "ps2_barg": round(st["ps2"] + n(0.05), 3), "ts2_c": round(st["ts2"], 2),
            "pd2_barg": round(st["pd2"], 3), "td2_c": round(td2 + n(0.4), 2),
            "flow_nm3h": round(st["q"] * (1 + n(0.004)), 1), "speed_rpm": round(st["rpm"] + n(0.3), 1),
            # valve covers: a leaking valve heats its own cover most
            "tv1_he_s_c": round(st["ts1"] + rise + n(0.6), 2),
            "tv1_he_d_c": round(st["tde1"] + 2 * st["res1"] + off + 15 * dvl + n(0.6), 2),
            "tv1_ce_s_c": round(st["ts1"] + rise + n(0.6), 2),
            "tv1_ce_d_c": round(st["tde1"] + off + n(0.6), 2),
            "tv2_he_s_c": round(st["ts2"] + rise + 5 * rw + n(0.6), 2),
            "tv2_he_d_c": round(st["tde2"] + st["res2"] + off + n(0.6), 2),
            "tv2_ce_s_c": round(st["ts2"] + rise + 35 * svl + 5 * rw + n(0.6), 2),
            "tv2_ce_d_c": round(st["tde2"] + st["res2"] + off + n(0.6), 2),
            "packing_vent1_nm3h": round(max(0.0, d["packing"]["vent_normal_nm3h"] + n(0.03)), 3),
            "packing_vent2_nm3h": round(max(0.0, d["packing"]["vent_normal_nm3h"] + 3.0 * f["packing_leak"] + n(0.03)), 3),
            "lube_cycle_s": round(d["lube"]["design_cycle_s"] / (1 - 0.6 * f["lube_starvation"]) + n(0.2), 2),
            "rod_drop1_mm": round(d["rod_drop"]["normal_mm"] + 1.2 * f["rider_band_wear"] + n(0.01), 3),
            "rod_drop2_mm": round(d["rod_drop"]["normal_mm"] + 0.05 + n(0.01), 3),
            "xhead_acc1_g": round(d["crosshead"]["baseline_g"][0] * (1 + n(0.04)), 3),
            "xhead_acc2_g": round(d["crosshead"]["baseline_g"][1] * (1 + 2.0 * f["crosshead_wear"] + n(0.04)), 3),
        }
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

    The compressor runs at its operating point. Suction pressure and temperatures wander slowly (a refinery header is
    never quite steady); the crank angle is kept for the 3D animation.
    """

    def __init__(self, twin, seed=2201):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.c = Compressor(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.crank = 0.0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.crank = 0.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.c.faults[k] = f.sev
        self.t += dt * self.scale
        d = self.twin["design"]
        rpm = d["operation"]["rpm"]
        self.crank = (self.crank + rpm / 60 * 360 * dt) % 360
        h = self.t / 3600.0
        ps1 = d["stages"][0]["ps_barg"] + 0.4 * math.sin(2 * math.pi * h / 7.0)
        ts1 = d["stages"][0]["ts_c"] + 1.5 * math.sin(2 * math.pi * h / 24.0)
        ts2 = d["stages"][1]["ts_c"] + 1.0 * math.sin(2 * math.pi * h / 24.0 + 0.6)
        pd2 = d["stages"][1]["pd_barg"] + 0.6 * math.sin(2 * math.pi * h / 5.0) + 18.0 * self.faults["discharge_pressure_high"].sev
        st = self.c.state(ps1, ts1, ts2, pd2, rpm)
        st.update(crank=self.crank, running=self.running)
        return st

    def measure(self, true):
        c, n = self.c, self.c.n
        st = dict(true)
        st["ps1"] = true["ps1"] + n(0.03)
        st["ts1"] = true["ts1"] + n(0.2)
        st["ts2"] = true["ts2"] + n(0.2)
        st["pd2"] = true["pd2"] + n(0.1)
        return c.reading(st)
