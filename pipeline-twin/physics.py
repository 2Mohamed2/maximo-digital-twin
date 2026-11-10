"""Physics model of PIPE-1501 (14 km DN 1200 ductile iron transmission main, pump station -> hilltop reservoir R-15):
the stand-in for the real pipeline.

Per step (dt real seconds; the plant clock runs `time_scale` times faster, see the twin file design.demo):
  schedule   3 pumps at night (cheap power, fill the reservoir), 2 by day, 1 in the evening peak; the variable-speed
             drive hunts +-2 % around its set point
  pumps      each pump H = H_shut - c Q^2 (duty 2100 m3/h); the pump station flow is where the pump curve meets the
             system curve (reservoir level + friction + local losses + leak), found by bisection
  friction   Darcy-Weisbach with Swamee-Jain, true roughness k = design k + tuberculation; water viscosity from T
  stations   head at every transmitter is integrated back from the reservoir: friction with the flow each reach carries
             (Q_in upstream of the leak, Q_out downstream), plus local losses at HP-1 (air pocket) and LV-2 (valve)
  reservoir  level follows inflow minus town demand (2 x 15,000 m3)
  meters     FM-A and FM-B +-0.2 % fixed bias plus noise; transmitters 0.003 bar noise (1-minute averages)
  transients the high-rate loggers report the envelope of a full pump trip at the current flow: Joukowsky rho a v,
             cut to 22 % by the surge vessel; without it the high point drops to vapour pressure (column separation)
             and the rejoining columns add half a Joukowsky on top at the pump station
  faults     leak (orifice at ch 8.2 km, 500 m3/h at 6.5 bar at full severity); tuberculation (k +2 mm);
             air_pocket (4 m extra loss at HP-1); valve_throttled (LV-2 to 35 % open, 6 m at 1 m/s);
             meter_drift (FM-B reads 12 % low: lost zero / fouled electrodes); surge_protection (surge vessel lost); transmitter_fault (PT-2 -0.25 bar)
"""
import math
import random

import twin_calc as tc

G = tc.G
P_VAPOUR_BAR = -0.97          # gauge vapour pressure of water at ~20 C


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
    def __init__(self, twin, seed=1501):
        self.twin, self.rng = twin, random.Random(seed)
        self.d = twin["design"]
        self.k = tc._k(twin)
        rt = self.d["route"]
        self.feat = rt["features"]
        self.res = self.feat["reservoir"]
        self.q_duty = rt["pumps"]["q_each_m3h"]
        self.n_pumps = rt["pumps"]["count"]
        self.h_shut, self.h_duty = 175.0, 139.0
        self.c_pump = (self.h_shut - self.h_duty) / self.q_duty ** 2
        self.vessel = self.d["transients"]["surge_vessel_factor"]
        self.scale = float(self.d.get("demo", {}).get("time_scale", 1))
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0                    # plant clock, seconds of day (runs time_scale x real time)
        self.running, self.trip = True, 0
        self.level = 5.5
        self.temp = 18.0
        self.area = 2 * 15000.0 / 8.0
        self.q_leak = 0.0
        self.vfd = 1.0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        pass

    def fault_state(self):
        return {k: round(v.sev, 3) for k, v in self.faults.items()}

    def pumps(self):
        h = (self.t / 3600.0) % 24
        return 3 if (h < 6 or h >= 22) else (1 if 17 <= h < 21 else 2)

    def demand(self):
        h = (self.t / 3600.0) % 24
        base = 4300 * (1 + 0.22 * math.sin((h - 9) / 24 * 2 * math.pi) + 0.12 * math.sin((h - 6) / 12 * 2 * math.pi))
        return base + (self.level - 5.5) * 400

    def _slope(self, q, k_m):
        q = max(q, 1.0) / 3600
        v = q / self.k["A"]
        re = v * self.k["D"] / tc.nu(self.temp)
        f = 0.25 / math.log10(k_m / (3.7 * self.k["D"]) + 5.74 / re ** 0.9) ** 2
        return f / self.k["D"] * v * v / (2 * G)

    def _profile(self, q_in, q_leak):
        """head (m) at the five stations and at HP-1, LV-2, the leak, for a pump station flow and a leak flow."""
        f, k = self.faults, self.k
        L, xl = k["L"], self.feat["leak_site"]["ch"]
        x_hp, x_lv = self.feat["high_point"]["ch"], self.feat["line_valve"]["ch"]
        kt = k["k"] + 2.0e-3 * f["tuberculation"].sev
        q_out = max(q_in - q_leak, 0.0)
        s_in, s_out = self._slope(q_in, kt), self._slope(q_out, kt)
        v_in, v_out = q_in / 3600 / k["A"], q_out / 3600 / k["A"]
        h_res = self.res["floor_z"] + self.level
        h_end = h_res + v_out ** 2 / (2 * G)              # exit loss into the reservoir
        air = 4.0 * f["air_pocket"].sev if q_in > 50 else 0.0
        valve = 6.0 * f["valve_throttled"].sev * (v_out / 1.0) ** 2

        def head(x):
            fr = s_out * (L - x) if x >= xl else s_out * (L - xl) + s_in * (xl - x)
            return h_end + fr + (valve if x < x_lv else 0.0) + (air if x < x_hp else 0.0)
        return [head(x) for x in k["x"]], head(xl), head(x_hp), q_out, v_in

    def _solve(self, n):
        """pump station flow where n pumps (with the drive trim) meet the system curve."""
        lo, hi = 0.0, n * self.q_duty * 1.6
        for _ in range(48):
            q = (lo + hi) / 2
            H = self._profile(q, self.q_leak)[0]
            if self.vfd ** 2 * self.h_shut - self.c_pump * (q / n) ** 2 > H[0]:
                lo = q
            else:
                hi = q
        return (lo + hi) / 2

    def step(self, dt=1.0):
        f, k = self.faults, self.k
        for x in f.values():
            x.step(dt)
        pdt = dt * self.scale
        self.t += pdt
        h = (self.t / 3600.0) % 24
        self.temp = 18.0 + 1.5 * math.sin((h - 15) / 24 * 2 * math.pi) + 0.2 * math.sin(self.t / 40000)
        self.vfd = 1.0 + 0.02 * math.sin(self.t / 1700) + 0.006 * math.sin(self.t / 310)
        n = self.pumps()
        for _ in range(3):                                   # leak flow depends on the pressure at the leak
            q_in = self._solve(n)
            H, h_leak, h_hp, q_out, v_in = self._profile(q_in, self.q_leak)
            p_leak = max(h_leak - self.feat["leak_site"]["z"], 0.0)
            self.q_leak = 500.0 * f["leak"].sev * math.sqrt(p_leak / 66.5)
        H, h_leak, h_hp, q_out, v_in = self._profile(q_in, self.q_leak)
        self.level = max(3.0, min(8.0, self.level + (q_out - self.demand()) * pdt / 3600 / self.area))
        bpm = k["bpm"]
        p = [(Hh - z) * bpm for Hh, z in zip(H, k["z"])]
        p_hp = (h_hp - self.feat["high_point"]["z"]) * bpm
        J = k["rho"] * k["a"] * v_in / 1e5
        fac = self.vessel + (1 - self.vessel) * f["surge_protection"].sev
        pmin = max(P_VAPOUR_BAR, p_hp - fac * J)
        pmax = p[0] + fac * J + (0.5 * J if p_hp - fac * J < P_VAPOUR_BAR else 0.0)
        return {"flow_in_m3h": q_in * 1.002, "flow_out_m3h": q_out * 0.998 * (1 - 0.12 * f["meter_drift"].sev),
                "water_temp_c": self.temp,
                "pressure_ps_bar": p[0], "pressure_pt1_bar": p[1],
                "pressure_pt2_bar": p[2] - 0.25 * f["transmitter_fault"].sev,
                "pressure_pt3_bar": p[3], "pressure_res_bar": p[4],
                "reservoir_level_m": self.level, "pumps_running": n,
                "surge_pmax_bar": pmax, "surge_pmin_hp_bar": pmin,
                "line_valve_pos_pct": 100.0 - 65.0 * f["valve_throttled"].sev,
                "_q_leak_m3h": self.q_leak, "_p_hp_bar": p_hp}

    def measure(self, true):
        out = {}
        for p in self.twin["telemetry"]["points"]:
            k = p["metric"]
            v = true[k]
            if p["noise"]:
                v = v + self.rng.gauss(0, p["noise"])
            lo, hi = p["range"]
            v = max(lo, min(hi, v))
            out[k] = int(round(v)) if k == "pumps_running" else round(v, 4)
        return out
