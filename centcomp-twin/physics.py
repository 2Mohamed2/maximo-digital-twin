"""A stand-in for K-2301: the compressor, its process, the anti-surge loop, the dry gas seals and the bearings, with injectable faults.

The real machine sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests, the figures and the live twin pages.

How the stand-in works: the process sets the suction pressure and temperature, the discharge header pressure and the gas
flow it wants. The speed controller of the VSD finds the speed at which the compressor makes the head the process needs
(bisection on the map with the fan laws). The anti-surge controller keeps the compressor flow at or right of the control
line by opening the recycle valve. Pure Python + math/random only (it also runs in the browser under Pyodide).
"""
import math
import random

import twin_calc as tc


class Compressor:
    def __init__(self, twin, seed=1):
        self.tw = twin
        d = twin["design"]
        self.k = tc._k(twin)
        self.pr, self.se, self.br = d["process"], d["seals"], d["bearings"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.windup = 0.0          # anti-surge controller output wound up above the demand (set by Plant)
        self.t = 0.0               # plant time, s (slow process swing)

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state -------------------------------------------------------------------------------------------------------
    def head_req(self, t1, pr, eta):
        k = self.k
        m = k["km"] / eta
        return k["zr"] * t1 * (pr ** m - 1) / m / 1000

    def solve(self, qc, t1, pr, foul):
        """Speed ratio s at which the compressor makes the head the process needs at compressor flow qc."""
        k = self.k
        eta_f, head_f = 1 - 0.0875 * foul, 1 - 0.08 * foul
        lo, hi = 0.5, 1.2
        for _ in range(48):
            s = (lo + hi) / 2
            x = qc / (k["q0"] * s)
            eta = tc.eta_map(k, x) * eta_f
            made = s * s * k["h0"] * tc.head_map(k, x) * head_f
            if made < self.head_req(t1, pr, eta):
                lo = s
            else:
                hi = s
        s = (lo + hi) / 2
        x = qc / (k["q0"] * s)
        eta = tc.eta_map(k, x) * eta_f
        return s, eta, self.head_req(t1, pr, eta)

    def true_state(self):
        k, f = self.k, self.faults
        swing = math.sin(2 * math.pi * self.t / 3600.0)
        p1 = self.pr["suction_bara"] * (1 + 0.004 * swing)
        t1 = self.pr["suction_temp_c"] + 1.0 * swing + 273.15
        p2 = self.pr["discharge_bara"] * (1 + 0.01 * swing)
        q_proc = self.pr["flow_normal_m3h"] * (1 + 0.02 * swing) * (1 - 0.55 * f["surge_approach"]) * (1 - 0.27 * f["asv_stuck"])
        pr = p2 / p1
        foul = f["impeller_fouling"]
        h = self.head_req(t1, pr, k["e0"] * (1 - 0.0875 * foul))
        for _ in range(3):
            q_scl = tc.q_surge(k, h) / (1 - k["scl"] / 100)
            demand = max(0.0, (q_scl - q_proc) / k["asv"] * 100)
            stuck = f["asv_stuck"] > 0.3
            valve = 0.0 if stuck else min(100.0, demand)
            qc = q_proc + valve / 100 * k["asv"]
            s, eta, h = self.solve(qc, t1, pr, foul)
        out = min(100.0, demand + (self.windup if stuck else 0.0))
        m = k["km"] / eta
        t2 = t1 * pr ** m
        rho = p1 * 1e5 / (k["zr"] * t1)
        mf = qc / 3600 * rho
        gas_kw = mf * k["zrc"] * (t2 - t1) / 1000
        return dict(p1=p1, t1=t1, p2=p2, t2=t2, qc=qc, q_proc=q_proc, rho=rho, speed=s * k["n0"], eta=eta, head=h,
                    gas_kw=gas_kw, valve=valve, out=out, demand=demand)

    # one published message ----------------------------------------------------------------------------------------------
    def measure(self, s=None):
        s = s or self.true_state()
        k, f, se, br = self.k, self.faults, self.se, self.br
        dp_pa = s["rho"] * (s["qc"] / 3600 / k["C"]) ** 2
        oil = br["oil_supply_temp_c"] + self.n(0.2)
        return {
            "suction_pressure_bara": round(s["p1"] + self.n(0.005), 4),
            "suction_temp_c": round(s["t1"] - 273.15 + self.n(0.15), 3),
            "discharge_pressure_bara": round(s["p2"] + self.n(0.015), 4),
            "discharge_temp_c": round(s["t2"] - 273.15 + 10.0 * f["discharge_tt_drift"] + self.n(0.15), 3),
            "flow_dp_mbar": round(dp_pa / 100 * (1 + self.n(0.006)), 3),
            "speed_rpm": round(s["speed"] + self.n(3), 1),
            "driver_power_kw": round(s["gas_kw"] / k["eff"] * (1 + self.n(0.006)), 1),
            "asc_output_pct": round(max(0.0, s["out"] + self.n(0.2)), 2),
            "recycle_valve_pct": round(max(0.0, s["valve"] + self.n(0.2)), 2),
            "seal_gas_dp_bar": round(se["seal_gas_dp_normal_bar"] * (1 - 0.8 * f["seal_gas_supply"]) + self.n(0.02), 3),
            "vent_flow_de_nm3h": round(se["vent_flow_normal_nm3h"] + 9.0 * f["seal_primary_wear"] + abs(self.n(0.1)), 3),
            "vent_flow_ne_nm3h": round(se["vent_flow_normal_nm3h"] * 0.9 + abs(self.n(0.1)), 3),
            "brg_temp_de_c": round(br["journal_temp_normal_c"] + (oil - br["oil_supply_temp_c"]) + self.n(0.4), 2),
            "brg_temp_ne_c": round(br["journal_temp_normal_c"] - 3 + (oil - br["oil_supply_temp_c"]) + self.n(0.4), 2),
            "thrust_temp_c": round(br["thrust_temp_normal_c"] + 38 * f["thrust_overload"] + self.n(0.4), 2),
            "axial_pos_mm": round(0.42 * f["thrust_overload"] + self.n(0.01), 3),
            "vib_de_um": round(br["vib_normal_um"] + 50 * f["rotor_unbalance"] + abs(self.n(0.6)), 2),
            "vib_ne_um": round(br["vib_normal_um"] * 0.8 + 20 * f["rotor_unbalance"] + abs(self.n(0.6)), 2),
            "oil_supply_temp_c": round(oil, 2),
            "oil_supply_bar": round(br["oil_supply_bar"] + self.n(0.02), 3),
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

    The compressor runs continuously. The anti-surge controller output winds up (integral action) while the recycle valve
    does not follow it, as a real PI controller does when its valve is stuck.
    """

    def __init__(self, twin, seed=2301):
        self.twin = twin
        self.scale = float(twin["design"].get("demo", {}).get("time_scale", 1))
        self.c = Compressor(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.c.windup = 0.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.c.faults[k] = f.sev
        self.t += dt * self.scale
        self.c.t = self.t
        s = self.c.true_state()
        if s["valve"] < s["demand"] - 0.5:
            self.c.windup = min(100.0, self.c.windup + 1.5 * dt)
        else:
            self.c.windup = max(0.0, self.c.windup - 5.0 * dt)
        return self.c.true_state()

    def measure(self, true):
        return self.c.measure(true)
