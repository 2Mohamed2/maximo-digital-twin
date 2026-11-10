"""Physics model of TR-601 (SGB-SMIT DOTML 1000 kVA hermetic, ONAN) in a district substation: the stand-in for the real transformer.

Per step (dt real seconds; the plant clock runs `time_scale` times faster, see the twin file design.demo):
  load      district substation day profile: night trough, morning bump, evening peak; every third day a warm-evening
            peak runs to ~1.15 pu; power factor ~0.92; slight phase imbalance and neutral current
  ambient   day/night swing around a temperate mean
  thermal   IEC 60076-7 difference equations (top oil, hot-spot rise as the difference of two exponentials),
            losses P0 + Pk K^2; the monitoring IED's thermal image filters the ultimate top-oil rise f(K) and the
            ambient through the same k11 tau_o lag and reports K_eq and the mean ambient
  tank      hermetic: gauge pressure follows the oil temperature, oil level gauge follows thermal expansion
  DGA       background gases of a healthy unit; faults add their own gas signature (Duval PD, T1-T3, D1/D2). The
            online monitor updates once a (real) minute; gas changes are compressed to 1-3 min for the demo and relax
            back to the pre-fault levels after Clear all
  faults    cooling_degraded raises dTheta_or; overload_ageing adds load; oil_leak lowers level and pressure; arcing
            trips the protection relay at full severity (the transformer is de-energised until the operator reset)
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


BACKGROUND = {"h2": 18.0, "o2": 1500.0, "co": 240.0, "co2": 2100.0, "ch4": 9.0, "c2h2": 0.3, "c2h4": 4.0, "c2h6": 7.0}


class Plant:
    def __init__(self, twin, seed=601):
        self.twin, self.rng = twin, random.Random(seed)
        self.d = twin["design"]
        self.k = tc._k(twin)
        th = self.d["thermal"]
        self.th = th
        self.scale = float(self.d.get("demo", {}).get("time_scale", 1))
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0                    # plant clock, seconds of day (runs time_scale x real time)
        self.running, self.trip = True, 0
        self.load_bias = 0.0
        self.gas = dict(BACKGROUND)
        self.water = 8.0
        self.gas_clock = 0.0
        self.K = 0.5
        self.theta_a = 14.0
        self.f_filt = self._f(self.K)
        self.amb_filt = self.theta_a
        self.theta_o = tc.top_oil_steady(self.k, self.theta_a, self.K)
        self.dh1 = th["k21"] * th["H"] * th["g_r_k"] * self.K ** th["y"]
        self.dh2 = (th["k21"] - 1) * th["H"] * th["g_r_k"] * self.K ** th["y"]
        self.relay = 0

    # ---------------------------------------------------------------- helpers
    def _f(self, K):
        return ((1 + self.k["R"] * K ** 2) / (1 + self.k["R"])) ** self.th["x"]

    def _k_from_f(self, f):
        return math.sqrt(max(0.0, (f ** (1 / self.th["x"]) * (1 + self.k["R"]) - 1) / self.k["R"]))

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        if self.faults["arcing"].sev < 0.9:
            self.trip, self.running, self.relay = 0, True, 0

    def fault_state(self):
        return {k: round(v.sev, 3) for k, v in self.faults.items()}

    def demand(self):
        h = (self.t / 3600.0) % 24
        day = int(self.t // 86400)
        g = lambda c, w: math.exp(-((h - c) / w) ** 2)
        hot = 0.2 if day % 3 == 2 else 0.0
        frac = 0.30 + 0.22 * g(8.5, 1.8) + (0.58 + hot) * g(19.8, 2.4) + 0.08 * g(13.0, 3.0)
        self.load_bias = 0.998 * self.load_bias + self.rng.gauss(0, 0.002)
        return max(0.08, frac + self.load_bias)

    # ---------------------------------------------------------------- step
    def step(self, dt=1.0):
        f, d, th = self.faults, self.d, self.th
        for x in f.values():
            x.step(dt)
        pdt = dt * self.scale                       # plant seconds
        self.t += pdt
        h = (self.t / 3600.0) % 24
        self.theta_a = 14.0 + 6.0 * math.sin((h - 9.0) / 24 * 2 * math.pi) + 0.3 * math.sin(self.t / 9000)
        K = self.demand()
        K += f["overload_ageing"].sev * (1.35 - K)              # sustained overload: load held at 1.35 pu
        if self.trip:
            K = 0.0
        self.K = K
        # IEC 60076-7 difference equations (minutes -> seconds)
        to, tw = th["tau_o_min"] * 60, th["tau_w_min"] * 60
        cool = 1 + 0.9 * f["cooling_degraded"].sev           # blocked fins: a larger top-oil rise for the same losses
        target_o = self.theta_a + (0.0 if self.trip else th["dtheta_or_k"] * self._f(K) * cool)
        a_o = 1 - math.exp(-pdt / (th["k11"] * to))
        self.theta_o += (target_o - self.theta_o) * a_o
        hg = th["H"] * th["g_r_k"] * K ** th["y"]
        self.dh1 += (th["k21"] * hg - self.dh1) * (1 - math.exp(-pdt / (th["k22"] * tw)))
        self.dh2 += ((th["k21"] - 1) * hg - self.dh2) * (1 - math.exp(-pdt / (to / th["k22"])))
        theta_h = self.theta_o + self.dh1 - self.dh2
        # monitoring IED thermal image (same lag as the oil): equivalent load and mean ambient
        self.f_filt += ((self._f(K) if not self.trip else 0.0) - self.f_filt) * a_o
        self.amb_filt += (self.theta_a - self.amb_filt) * a_o
        k_eq = self._k_from_f(self.f_filt) if self.f_filt > (1 / (1 + self.k["R"])) ** th["x"] else 0.0
        # tank (hermetic)
        leak = f["oil_leak"].sev
        hm = d["hermetic"]
        pressure = hm["pressure_at_20c_bar"] + hm["pressure_per_k_bar"] * (self.theta_o - 20) - 0.22 * leak
        level = 98.0 + 0.06 * (self.theta_o - 50) - 24.0 * leak
        # protection relay (DGPT2-style): temperature stages + gas
        arc = f["arcing"].sev
        if arc >= 0.95 or self.theta_o > 110:
            self.trip, self.running = 1, False
        self.relay = 2 if self.trip else (1 if (self.theta_o > 95 or arc > 0.6) else 0)
        # DGA: targets per fault signature, first-order approach (~1 real min); relaxes to background when cleared
        th_f, pd, mo = f["thermal_fault_core"].sev, f["partial_discharge"].sev, f["moisture_ingress"].sev
        ov = f["overload_ageing"].sev
        tgt = dict(BACKGROUND)
        tgt["ch4"] += 180 * th_f + 420 * pd + 70 * arc
        tgt["c2h4"] += 420 * th_f ** 2 + 110 * arc
        tgt["c2h6"] += 70 * th_f
        tgt["h2"] += 60 * th_f + 1300 * pd + 520 * arc
        tgt["c2h2"] += 3 * th_f ** 2 + 160 * arc
        tgt["co"] += 820 * ov + 40 * th_f
        tgt["co2"] += 1300 * ov
        tgt["o2"] += 6500 * mo
        tau = 60.0 if any(x.target > 0 or x.sev > 0 for x in f.values()) else 15.0    # Clear all: demo oil back to background fast
        for g in self.gas:
            self.gas[g] += (tgt[g] - self.gas[g]) * min(1.0, dt / tau)
        water_eq = 6.0 * math.exp(0.025 * (self.theta_o - 40)) * (1 + 4.5 * mo)
        self.water += (water_eq - self.water) * min(1.0, dt / 60.0)
        # load quantities
        s_kva = K * d["rating"]["s_kva"]
        u = d["rating"]["u_lv_v"] * (1 - 0.018 * K) if not self.trip else 0.0
        i = s_kva * 1000 / (math.sqrt(3) * max(u, 1.0)) if not self.trip else 0.0
        pf = 0.92 + 0.02 * math.sin(self.t / 7000)
        gv = self.gas
        return {"load_current_l1_a": i * 1.03, "load_current_l2_a": i * 0.98, "load_current_l3_a": i * 0.99, "neutral_current_a": 0.045 * i,
                "lv_voltage_v": u, "load_kva": s_kva, "power_factor": pf if not self.trip else 0.0, "load_eq_pu": k_eq,
                "ambient_temp_c": self.theta_a, "ambient_avg_c": self.amb_filt, "top_oil_temp_c": self.theta_o,
                "wti_temp_c": theta_h + 0.4, "tank_pressure_bar": pressure, "oil_level_pct": level, "tap_position": 3,
                "relay_status": self.relay,
                "dga_h2_ppm": gv["h2"], "dga_o2_ppm": gv["o2"], "dga_co_ppm": gv["co"], "dga_co2_ppm": gv["co2"],
                "dga_ch4_ppm": gv["ch4"], "dga_c2h2_ppm": gv["c2h2"], "dga_c2h4_ppm": gv["c2h4"], "dga_c2h6_ppm": gv["c2h6"],
                "moisture_ppm": self.water}

    def measure(self, true):
        out = {}
        for p in self.twin["telemetry"]["points"]:
            k = p["metric"]
            v = true[k]
            if p["noise"]:
                v = v + self.rng.gauss(0, p["noise"])
            lo, hi = p["range"]
            v = max(lo, min(hi, v))
            out[k] = int(v) if k in ("relay_status", "tap_position") else round(v, 4 if abs(v) < 10 else 2)
        return out
