"""Physics model of UGC-801 (3.6 km, 132 kV, Prysmian 1x1200 mm2 Al XLPE in trefoil, cross-bonded): the stand-in for the
real circuit and its monitoring (CTs, RTTR unit, DTS interrogator, link-box sensors, PD HFCTs, IR camera).

Per step (dt real seconds; the plant clock runs `time_scale` times faster, see the twin file design.demo):
  load      urban 132 kV feeder: night trough, midday and evening peaks (~700 A), slight phase imbalance
  ambient   soil at cable depth ~25 C with a slow drift; air at the sealing ends swings day/night
  thermal   12 route segments of 300 m, each with its own external thermal resistance T4 (direct buried, or the road
            crossing in ducts at 1.8 m); IEC 60287 losses with R(theta_c); two time constants (IEC 60853 idea):
            screen rise over soil lags with tau_soil (10 h), conductor rise over screen with tau_cable (30 min)
  RTTR      equivalent current = sqrt of I^2 filtered with tau_soil (what the RTTR unit reports)
  DTS       fibre in the screen of the middle phase: max temperature per segment (joints run ~1 K warmer)
  faults    soil_drying raises the crossing soil resistivity 1.2 -> 2.6 K.m/W; cross_bonding_fault turns major section 1
            into a solidly bonded one (lambda1 0.02 -> 0.54, circulating sheath current); overload lifts the load to
            ~980 A; joint_pd / jacket_damage / termination_overheating act on their sensors; dts_fibre_break cuts the
            fibre at km 1.3 (the interrogator sees nothing beyond: segments report 0)
"""
import math
import random

import twin_calc as tc


class Fault:
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
    def __init__(self, twin, seed=801):
        self.twin, self.rng = twin, random.Random(seed)
        self.d = twin["design"]
        self.k = tc._k(twin)
        th = self.d["thermal"]
        self.th = th
        self.scale = float(self.d.get("demo", {}).get("time_scale", 1))
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.load_bias = 0.0
        ci = self.d["circuit"]
        self.n = ci["segments"]
        self.xseg = ci["crossing_segment"] - 1
        rr = random.Random(seed + 1)
        self.t4 = [th["T4_normal"] * (1 + rr.uniform(-0.04, 0.04)) for _ in range(self.n)]
        self.t4[self.xseg] = th["T4_crossing"]
        self.joint_seg = [int(km / ci["segment_km"] - 1e-6) for km in ci["joints"].values()]
        self.ta = th["soil_ambient_c"]
        self.I = 450.0
        self.i2f = self.I ** 2
        self.ds = [0.0] * self.n                 # screen rise over soil, per segment
        self.dc = [0.0] * self.n                 # conductor rise over screen
        self.term = 30.0
        self.pd_state = 0.0
        self._settle()

    def _settle(self):
        for s in range(self.n):
            ts, tcn = self._ultimate(s, self.I, self.th["lambda1_cross_bonded"], self.t4[s])
            self.ds[s], self.dc[s] = ts, tcn

    def _ultimate(self, s, I, lam, t4):
        """Steady screen rise over soil and conductor rise over screen (IEC 60287), R at the resulting temperature."""
        k = self.k
        theta_c = self.ta + 40
        for _ in range(3):
            wc = I * I * tc.r_ac(k, theta_c)
            ds = (wc * (1 + lam) + k["WD"]) * (k["T3"] + t4)
            dc = wc * k["T1"] + k["WD"] * k["T1"] / 2
            theta_c = self.ta + ds + dc
        return ds, dc

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.trip, self.running = 0, True

    def fault_state(self):
        return {k: round(v.sev, 3) for k, v in self.faults.items()}

    def demand(self):
        h = (self.t / 3600.0) % 24
        g = lambda c, w: math.exp(-((h - c) / w) ** 2)
        frac = 0.42 + 0.30 * g(13.5, 3.2) + 0.40 * g(20.5, 2.3)
        self.load_bias = 0.998 * self.load_bias + self.rng.gauss(0, 0.002)
        return max(0.1, frac + self.load_bias) * 820.0

    def step(self, dt=1.0):
        f, th, k = self.faults, self.th, self.k
        for x in f.values():
            x.step(dt)
        pdt = dt * self.scale
        self.t += pdt
        h = (self.t / 3600.0) % 24
        self.ta = th["soil_ambient_c"] + 0.6 * math.sin(self.t / 86400 / 9 * 2 * math.pi)
        air = 27.0 + 7.0 * math.sin((h - 9.0) / 24 * 2 * math.pi)
        I = self.demand()
        I += f["overload"].sev * (985.0 - I)
        self.I = I
        a_soil = 1 - math.exp(-pdt / (th["tau_soil_min"] * 60))
        a_cab = 1 - math.exp(-pdt / (th["tau_cable_min"] * 60))
        self.i2f += (I * I - self.i2f) * a_soil
        lam_xb, lam_solid = th["lambda1_cross_bonded"], th["lambda1_solid"]
        bond = f["cross_bonding_fault"].sev
        dry = f["soil_drying"].sev
        tparts = th["T4_crossing_parts"]
        for s in range(self.n):
            t4 = self.t4[s]
            if s == self.xseg:
                rho = th["rho_soil"] + 1.4 * dry
                t4 = tparts["cable_to_duct"] + tparts["duct_wall"] + tparts["external"] * rho / th["rho_soil"]
            lam = lam_xb + (lam_solid - lam_xb) * bond if s < self.n // 2 else lam_xb
            ds_u, dc_u = self._ultimate(s, I, lam, t4)
            self.ds[s] += (ds_u - self.ds[s]) * a_soil
            self.dc[s] += (dc_u - self.dc[s]) * a_cab
        screen = [self.ta + self.ds[s] + (0.9 if s in self.joint_seg else 0.0) for s in range(self.n)]
        # DTS: fibre break at km 1.3 blinds everything beyond
        cut = f["dts_fibre_break"].sev > 0.5
        fibre_km = 1.3 if cut else self.d["circuit"]["length_km"] + 0.02
        seg_km = self.d["circuit"]["segment_km"]
        dts = [v if (not cut or (s + 1) * seg_km <= 1.3) else 0.0 for s, v in enumerate(screen)]
        imax = max(range(self.n), key=lambda s: dts[s])
        # sheath / bonding
        sheath = I * (k["sh"] + 0.37 * bond) * (1 + 0.04 * math.sin(self.t / 3000))
        vstand = 0.032 * I * (1 - 0.95 * bond)
        leak = 0.08 + 3.6 * f["jacket_damage"].sev ** 1.2
        # partial discharge (pC): background noise; joint PD grows and flickers
        jp = f["joint_pd"].sev
        self.pd_state += ((25 + 900 * jp ** 1.5) * (1 if jp > 0.02 else 0) - self.pd_state) * min(1.0, dt / 20)
        pdj = 3.0 + self.pd_state * (0.8 + 0.4 * self.rng.random())
        pdt_ = 4.0
        # sealing end A connector (IR): air + k I^2, a bad contact multiplies the rise
        tu = air + k["kterm"] * (I / 1000) ** 2 * (1 + 7.0 * f["termination_overheating"].sev)
        self.term += (tu - self.term) * min(1.0, dt / 30)
        phase = (1.01, 1.0, 0.99)
        out = {"current_l1_a": I * phase[0], "current_l2_a": I * phase[1], "current_l3_a": I * phase[2],
               "load_eq_a": math.sqrt(self.i2f), "voltage_kv": 132.0 * (1 + 0.01 * math.sin(self.t / 5000)),
               "soil_ambient_c": self.ta, "air_temp_c": air,
               "dts_max_c": dts[imax], "dts_max_km": (imax + 0.5) * seg_km, "dts_fibre_km": fibre_km,
               "sheath_current_a": sheath, "sheath_voltage_v": vstand, "sheath_leakage_ma": leak,
               "pd_joint_pc": pdj, "pd_term_pc": pdt_, "term_a_temp_c": self.term}
        for s in range(self.n):
            out[f"dts_seg{s + 1:02d}_c"] = dts[s]
        self.conductor_true = [screen[s] + self.dc[s] for s in range(self.n)]
        return out

    def measure(self, true):
        out = {}
        for p in self.twin["telemetry"]["points"]:
            k = p["metric"]
            v = true[k]
            if p["noise"] and not (k.startswith("dts_seg") and v == 0.0):
                v = v + self.rng.gauss(0, p["noise"])
            lo, hi = p["range"]
            v = max(lo, min(hi, v))
            out[k] = round(v, 4 if abs(v) < 10 else 2)
        return out
