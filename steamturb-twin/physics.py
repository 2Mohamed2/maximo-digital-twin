"""A stand-in for ST-3201: the turbine, its governor and extraction valves, the condenser and the bearings, with injectable faults.

The real machine sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests, the figures and the live twin pages.

How the stand-in works: the plant asks for a load (main steam flow) and a process steam flow (extraction); both swing
slowly. The HP section expands the main steam to the extraction pressure with its efficiency; the steam that is not
extracted goes through the LP section to the condenser. The condenser pressure follows the cooling water outlet
temperature plus the terminal temperature difference. Output = (HP work + LP work) x mechanical/generator efficiency.
Pure Python + math/random only (it also runs in the browser under Pyodide).
"""
import math
import random

import twin_calc as tc

C2K = 273.15


class Turbine:
    def __init__(self, twin, seed=1):
        self.tw = twin
        self.k = tc._k(twin)
        self.mech = twin["design"]["mechanical"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0           # plant time, s (slow swings)

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state -------------------------------------------------------------------------------------------------------
    def operating_point(self):
        k = self.k
        w = 2 * math.pi * self.t
        m = k["m0"] * (0.93 + 0.04 * math.sin(w / 3600.0))
        e = k["e0"] * (1 + 0.12 * math.sin(w / 2700.0 + 1.0))
        p1 = k["p0"] * (1 + 0.004 * math.sin(w / 900.0))
        t1 = k["t0"] + 2.0 * math.sin(w / 1300.0 + 0.5)
        cw_in = k["cw_in"] + 1.5 * math.sin(w / 5400.0)
        return m, e, p1, t1, None, cw_in

    def true_state(self, m=None, e=None, p1=None, t1=None, pc_fixed=None):
        k, f = self.k, self.faults
        if m is None:
            m, e, p1, t1, pc_fixed, cw_in = self.operating_point()
        else:
            cw_in = k["cw_in"]
        tk1 = t1 + C2K
        pe = k["pe0"]
        lp = max(m - e, 5.0)
        # HP section
        eta = (tc.eta_expected(k, m) - 5.5 * f["hp_deposits"] - 9.0 * f["solid_particle_erosion"]) / 100
        h1 = tc.h_pt(k, p1, tk1)
        he = h1 - eta * tc.dh_isen(k, p1, tk1, pe)
        tke = tc.t_from_h(k, pe, he)
        area = (1 - 0.09 * f["hp_deposits"]) * (1 + 0.05 * f["solid_particle_erosion"])
        pw = k["pw0"] * (m / k["m0"]) * math.sqrt(tk1 / (k["t0"] + C2K)) / area
        # condenser
        rise = k["cw_rise"] * lp / (k["m0"] - k["e0"])
        cw_out = cw_in + rise
        ttd = k["ttd0"] + 8.0 * f["condenser_fouling"]
        pc = pc_fixed if pc_fixed is not None else tc.psat_mbar(k, cw_out + ttd)
        # LP section (extraction -> condenser, k for wet expansion)
        eta_lp = (k["eta_lp"] - 6.0 * f["lp_blade_damage"] - 3.0 * f["hp_deposits"]) / 100
        dh_lp = eta_lp * tc.dh_isen(k, pe, tke, pc / 1000, k["k_lp"])
        kw = (m * (h1 - he) + lp * dh_lp) / 3.6          # t/h x kJ/kg / 3.6 = kW
        mw = kw / 1000 * k["emg"]
        lift = k["lift0"] * (m / k["m0"]) * (k["p0"] / p1) * math.sqrt(tk1 / (k["t0"] + C2K)) / (1 - 0.15 * f["governor_valve"])
        return dict(m=m, e=e, lp=lp, p1=p1, t1=t1, pe=pe, te=tke - C2K, pw=pw, cw_in=cw_in, cw_out=cw_out, pc=pc, mw=mw,
                    lift=min(100.0, lift), eta=eta, h1=h1, he=he)

    # one published message ----------------------------------------------------------------------------------------------
    def measure(self, s=None):
        s = s or self.true_state()
        f, me = self.faults, self.mech
        return {
            "main_flow_th": round(s["m"] * (1 + self.n(0.001)), 3),
            "main_press_bara": round(s["p1"] + self.n(0.05), 3),
            "main_temp_c": round(s["t1"] + self.n(0.2), 2),
            "wheel_press_bara": round(s["pw"] * (1 + self.n(0.002)), 3),
            "ext_press_bara": round(s["pe"] + self.n(0.01), 3),
            "ext_temp_c": round(s["te"] + self.n(0.2), 2),
            "ext_flow_th": round(s["e"] * (1 + self.n(0.002)), 3),
            "cond_press_mbar": round(s["pc"] * (1 + self.n(0.003)), 2),
            "cw_in_c": round(s["cw_in"] + self.n(0.05), 2),
            "cw_out_c": round(s["cw_out"] + self.n(0.05), 2),
            "power_mw": round(s["mw"] * (1 + self.n(0.001)), 3),
            "gv_lift_pct": round(s["lift"] + self.n(0.1), 2),
            "ev_lift_pct": round(min(100.0, 25 + 55 * s["lp"] / (self.k["m0"] - self.k["e0"])) + self.n(0.1), 2),
            "speed_rpm": round(self.k["n0"] + self.n(0.8), 1),
            "vib_brg1_mms": round(me["vib_normal_mms"] + 7.0 * f["rotor_unbalance"] + abs(self.n(0.08)), 3),
            "vib_brg2_mms": round(me["vib_normal_mms"] * 0.8 + 3.0 * f["rotor_unbalance"] + abs(self.n(0.08)), 3),
            "thrust_pos_mm": round(me["thrust_pos_normal_mm"] + 0.32 * f["thrust_bearing_wear"] + self.n(0.005), 4),
            "thrust_pad_c": round(me["thrust_pad_normal_c"] + 33.0 * f["thrust_bearing_wear"] + self.n(0.3), 2),
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

    The turbine runs continuously at 3000 rpm; the load and the process steam demand swing slowly with the plant clock.
    """

    def __init__(self, twin, seed=3201):
        self.twin = twin
        self.scale = float(twin["design"].get("demo", {}).get("time_scale", 1))
        self.c = Turbine(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.trip = 0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.c.faults[k] = f.sev
        self.t += dt * self.scale
        self.c.t = self.t
        return self.c.true_state()

    def measure(self, true):
        return self.c.measure(true)
