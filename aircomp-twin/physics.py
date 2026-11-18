"""A stand-in for AC-4601: the screw compressor package, its controller, the dryer, the receiver and the plant demand, with injectable faults.

The real compressor and meters send the same points (see telemetry.points in the twin file). Nothing here is used by
Monitor: the expected values are computed in Monitor from the twin file only. This model only produces believable readings
and fault fingerprints for the tests, the figures and the live twin pages.

How the stand-in works: the plant asks for a free-air demand that swings slowly around its normal value (plus the leaks).
The fixed-speed compressor loads (inlet valve open, full free air delivery) until the pressure reaches the unload set
point, then unloads and blows down its sump until the pressure falls to the load set point. The load share is demand / FAD,
the cycle rate follows from the storage volume and the pressure band, and the power from the CAGI line at the actual
pressure plus the blow-down time after every unload. Pure Python + math/random only (it also runs in the browser under Pyodide).
"""
import math
import random

import twin_calc as tc


class Compressor:
    def __init__(self, twin, seed=1):
        self.tw = twin
        d = twin["design"]
        self.k = tc._k(twin)
        self.d = d
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0               # plant time, s (slow swing of demand and weather)
        self.phase = 0.0           # position in the load/unload cycle, 0..1

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state -------------------------------------------------------------------------------------------------------
    def true_state(self):
        k, f, d = self.k, self.faults, self.d
        sw = math.sin(2 * math.pi * self.t / 3600.0)
        sw2 = math.sin(2 * math.pi * self.t / 5400.0 + 1.0)
        pin = 1.0 + 0.004 * sw2
        tin = 28.0 + 3.0 * sw
        rh = 60.0 - 6.0 * sw
        shift = 0.8 * f["pressure_setpoint_high"]
        pd = (k["pl"] + k["pu_set"]) / 2 + shift
        sep = d["oil"]["separator_dp_new_bar"] + 1.2 * f["separator_clogged"]
        fad = tc.fad_exp(k, pd) * (1 - 0.25 * f["element_wear"])
        leak_frac = d["leak"]["test_load_normal_pct"] / 100 + 0.20 * f["leaks_growing"]
        demand = d["system"]["demand_normal_m3min"] * 0.94 * (1 + 0.04 * sw) + (leak_frac - d["leak"]["test_load_normal_pct"] / 100) * tc.fad_exp(k, pd)
        lf = min(0.98, demand / fad)
        vol = k["vol"] * (1 - 5 / 6 * f["receiver_isolated"])
        cyc = 60 * pin * fad * lf * (1 - lf) / (vol * k["band"])
        # loaded power: CAGI line at the element pressure (outlet + extra separator drop), same FAD as a healthy element
        pl = tc.p_load(k, pd + sep - d["oil"]["separator_dp_new_bar"], pin, tc.fad_exp(k, pd))
        power = tc.p_avg(k, lf, pl, cyc)
        o = d["oil"]
        app = o["cooler_approach_k"] * (1 + 1.5 * f["oil_cooler_fouled"]) * (0.6 + 0.4 * lf)
        if f["thermostat_stuck_open"] > 0.5:
            tel = tin + app
        else:
            tel = max(o["element_out_normal_c"] - 14 * f["thermostat_stuck_open"], tin + app)
        pdp = d["dryer"]["pdp_normal_c"] + 12.0 * f["dryer_fault"]
        header = pd - d["system"]["system_dp_normal_bar"]
        i_load = (pl - d["cagi"]["fan_hp"] * 0.7457 / d["cagi"]["fan_eff"]) * 1000 / (math.sqrt(3) * d["motor"]["voltage_v"] * d["motor"]["power_factor"])
        loaded = self.phase < lf
        p_inst = k["pl"] + shift + k["band"] * (self.phase / lf if loaded else 1 - (self.phase - lf) / max(1e-6, 1 - lf))
        return dict(pin=pin, tin=tin, rh=rh, pd=pd, p_inst=p_inst, sep=sep, fad=fad, demand=demand, lf=lf, vol=vol, cyc=cyc, pl=pl,
                    power=power, tel=tel, pdp=pdp, header=header, i_load=i_load, loaded=loaded, leak_frac=leak_frac)

    # one published message ----------------------------------------------------------------------------------------------
    def measure(self, s=None):
        s = s or self.true_state()
        q_n = s["demand"] * s["pin"] / 1.01325 * 273.15 / (s["tin"] + 273.15)
        return {
            "discharge_pressure_barg": round(s["pd"] + self.n(0.01), 3),
            "header_pressure_barg": round(s["header"] + self.n(0.01), 3),
            "inlet_pressure_bara": round(s["pin"] + self.n(0.0005), 4),
            "inlet_temp_c": round(s["tin"] + self.n(0.15), 2),
            "inlet_rh_pct": round(s["rh"] + self.n(0.5), 1),
            "flow_nm3min": round(q_n * (1 + self.n(0.006)), 3),
            "package_power_kw": round(s["power"] * (1 + self.n(0.006)), 2),
            "motor_current_a": round(s["i_load"] * (1 + self.n(0.004)), 1),
            "load_pct": round(s["lf"] * 100 + self.n(0.3), 2),
            "load_cycles_per_h": round(s["cyc"] * (1 + self.n(0.02)), 2),
            "loaded": 1 if s["loaded"] else 0,
            "element_outlet_temp_c": round(s["tel"] + self.n(0.3), 2),
            "separator_dp_bar": round(s["sep"] + self.n(0.01), 3),
            "dryer_pdp_c": round(s["pdp"] + self.n(0.25), 2),
            "leak_test_load_pct": round(s["leak_frac"] * 100 + self.n(0.4), 2),
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

    The compressor runs continuously in load/unload. The cycle phase advances at the cycle rate of the moment, so the
    'loaded' flag and the instantaneous pressure saw-tooth move in the 3D view; the published values are window means.
    """

    def __init__(self, twin, seed=4601):
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
        self.c.phase = 0.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.c.faults[k] = f.sev
        self.t += dt * self.scale
        self.c.t = self.t
        s = self.c.true_state()
        self.c.phase = (self.c.phase + s["cyc"] / 3600 * dt * self.scale) % 1.0
        return self.c.true_state()

    def measure(self, true):
        return self.c.measure(true)
