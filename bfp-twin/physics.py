"""A stand-in for BFP-3301: deaerator, suction line, the barrel pump on its VSD, the minimum-flow valve, the balance drum
leak-off and the bearings, with injectable faults.

The real device sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests, the figures and the live pages.

Operating point: the feedwater control (drum level) asks for a feed flow Qf to the boiler. The pump must give the head
the boiler path needs, Hreq = Hstatic + k Qf^2, while passing Q = Qf + recirculation + balance leak-off. The VSD finds the
speed ratio r where the pump curve meets it:  kh x (H0 r^2 + h2 Q^2) = Hreq.
The discharge temperature follows from the true efficiency with the same ISO 5198 energy balance the twin inverts:
    cp (T2 - T1) = (p2 - p1) / rho / eta - a (p2 - p1)
so, in this stand-in, the thermodynamic efficiency and the flow from shaft power agree exactly with the truth when no
fault is active (a real pump adds the kinetic, elevation and heat-loss terms this simple balance leaves out).
"""
import math
import random

import twin_calc as tc


class BFP:
    def __init__(self, twin, seed=1):
        self.twin = twin
        d = twin["design"]
        self.k = tc._k(twin)
        self.p, self.b, self.dr, self.s, self.sy, self.br = d["pump"], d["balance"], d["drive"], d["suction"], d["system"], d["bearings"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.ksys = (self.sy["h_at_rated_m"] - self.sy["h_static_m"]) / self.sy["q_rated_m3h"] ** 2
        self.t_suction = tc.tsat(self.k, self.s["da_pressure_bar"] + tc.ATM) - 0.1     # stored water, just below saturation

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state ---------------------------------------------------------------------------------------------------
    def state(self):
        k, f, p = self.k, self.faults, self.p
        qf = self.sy["load_flow_m3h"] - f["minflow_valve_stuck"] * (self.sy["load_flow_m3h"] - 100.0)
        hreq = self.sy["h_static_m"] + self.ksys * qf * qf
        kh = 1 - 0.08 * f["impeller_wear"]
        t1 = self.t_suction
        ros = tc.rho(k, t1)
        p_da = self.s["da_pressure_bar"] - 1.1 * f["npsh_loss"]
        level = self.s["level_normal_m"] - 1.2 * f["npsh_loss"]
        r, recirc_ctl, leak, q, ratio = 0.95, 0.0, self.b["leakoff_m3h"], qf, 2.0
        drift = 1 + 0.15 * f["flow_meter_drift"]
        for _ in range(8):
            qmin = k["qmf"] * k["qb"] * r
            q_meter = (qf + leak) * drift
            if f["minflow_valve_stuck"] > 0.0:
                recirc_ctl = 0.0
            elif q_meter < 1.1 * qmin:
                recirc_ctl = 1.25 * qmin - (qf + leak)
            else:
                recirc_ctl = 0.0
            recirc = recirc_ctl + 70.0 * f["recirc_valve_passing"]
            q = qf + leak + recirc
            kcav = 1 - 0.5 * max(0.0, 1.0 - ratio)
            r = math.sqrt(max((hreq / (kh * kcav) - k["h2"] * q * q) / k["h0"], 0.05))
            dp = ros * tc.G * hreq / 1e5
            leak = self.b["leakoff_m3h"] * math.sqrt(dp / self.b["dp_ref_bar"]) * (1 + 1.6 * f["balance_drum_wear"])
            strainer = 0.04 * (q / k["qb"]) ** 2 + 0.9 * f["strainer_clogging"]
            ps = (p_da + ros * tc.G * (k["z"] + level) / 1e5 - k["kf"] * q * q * ros * tc.G / 1e5 - strainer)
            npsha = (ps + tc.ATM - tc.pvap(k, t1)) * 1e5 / (ros * tc.G)
            x = q / (r * k["qb"])
            ratio = npsha / tc.npsh3(k, x, r)
        pd = ps + dp
        eta = max(0.05, tc.eff_curve(k, x)) * (1 - 0.14 * f["impeller_wear"]) * (1 - 0.02 * f["balance_drum_wear"])
        t2 = t1 + 3.0
        for _ in range(6):                                    # energy balance at the mean temperature
            tm = (t1 + t2) / 2
            em = dp * 1e5 / tc.rho(k, tm) / eta
            t2 = t1 + (em - tc.a_iso(k, tm) * dp * 1e5) / tc.cp(k, tm)
        shaft_kw = q / 3600 * dp * 1e5 / eta / 1000
        pos = min(100.0, recirc_ctl / (0.6 * k["qb"]) * 100) if recirc_ctl > 0 else 0.0
        oil = self.br["oil_c"]
        vib = (self.br["vib_base_mm_s"] + 2.0 * max(0.0, 0.5 - x) + 12.0 * max(0.0, 1.3 - ratio) + 6.0 * f["bearing_degradation"])
        return {
            "qf": qf, "q": q, "q_meter": q * drift, "r": r, "rpm": r * k["n0"], "ps": ps, "pd": pd, "dp": dp, "t1": t1, "t2": t2,
            "eta": eta, "kw": shaft_kw / k["ed"], "leak": leak, "recirc": recirc, "pos": pos, "strainer": strainer,
            "p_da": p_da, "level": level, "npsha": npsha, "ratio": ratio, "x": x, "hreq": hreq,
            "thrust": oil + k["thr"] * r * r + 18.0 * f["balance_drum_wear"],
            "de": oil + k["jr"] * r * r + 16.0 * f["bearing_degradation"], "nde": oil + (k["jr"] - 2.0) * r * r,
            "oil": oil, "vib": vib, "mw": self.sy["unit_mw"] * qf / self.sy["q_rated_m3h"],
        }

    # one published message ----------------------------------------------------------------------------------------------
    def reading(self, s):
        n = self.n
        t1 = s["t1"] + n(0.02)
        return {
            "running": 1, "speed_rpm": round(s["rpm"] + n(2.0), 1), "motor_kw": round(s["kw"] * (1 + n(0.003)), 1),
            "suction_flow_m3h": round(s["q_meter"] * (1 + n(0.004)), 1),
            "suction_pressure_bar": round(s["ps"] + n(0.01), 3), "discharge_pressure_bar": round(s["pd"] + n(0.05), 2),
            "suction_temp_c": round(t1, 3), "discharge_temp_c": round(t1 + (s["t2"] - s["t1"]) + n(0.005), 3),
            "leakoff_flow_m3h": round(s["leak"] * (1 + n(0.01)), 2), "recirc_valve_pct": round(s["pos"], 1),
            "recirc_flow_m3h": round(max(0.0, s["recirc"] + n(0.3)), 1), "strainer_dp_bar": round(max(0.0, s["strainer"] + n(0.005)), 3),
            "da_pressure_bar": round(s["p_da"] + n(0.005), 3), "da_level_m": round(s["level"] + n(0.01), 3),
            "bearing_de_c": round(s["de"] + n(0.15), 2), "bearing_nde_c": round(s["nde"] + n(0.15), 2),
            "thrust_bearing_c": round(s["thrust"] + n(0.15), 2), "lube_oil_c": round(s["oil"] + n(0.1), 2),
            "vibration_mm_s": round(max(0.2, s["vib"] + n(0.08)), 2), "unit_load_mw": round(s["mw"] + n(0.5), 1),
        }

    def measure(self):
        return self.reading(self.state())


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

    The unit runs at a steady load; the VSD finds the speed every step while the faults ramp. Nothing depends on the
    time of day, so the in-browser warm-up and clock do not matter.
    """

    def __init__(self, twin, seed=3301):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.e = BFP(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        for f in self.faults.values():
            f.sev, f.target, f.rate = 0.0, 0.0, 0.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.e.faults[k] = f.sev
        self.t += dt * self.scale
        return self.e.state()

    def measure(self, true):
        return self.e.reading(true)
