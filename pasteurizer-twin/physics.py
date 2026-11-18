"""A stand-in for PS-6801: the HTST pasteurizer (regenerator, heating section with hot water unit, holding tube, flow
diversion valve, cooler, booster pump and CIP counters), with injectable faults.

The real PLC sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests, the figures and the live pages. Pure Python (math, random) so it also runs in the browser.

Physics of the stand-in (the twin's relations plus what the twin does not know):
  Fouling is carried as x = U_clean x Rf (U = U_clean / (1 + x)). During a run it grows with the hours since the last
  CIP (heating section faster than the regenerator: the hottest plates foul first); faults add to it.
  Pressure drop ratio = 1 + 1.1 x (heater) or 1 + 1.8 x (regenerator raw side, narrower gaps). The extra raw-side
  pressure drop raises the raw pressure at the regenerator inlet, so regenerator fouling eats the pressure differential.
  The temperature controller holds the milk leaving the heating section at the set point; the hot water inlet
  temperature follows from effectiveness-NTU of the counterflow heating section at the hot water flow.
  The PMO interlock: when the differential falls below 6.9 kPa, the FDD goes to divert.
"""
import math
import random

from twin_calc import _k, regen_eps


def eps_cf(ntu, cr):
    """Effectiveness of a counterflow exchanger."""
    if abs(1 - cr) < 1e-9:
        return ntu / (1 + ntu)
    e = math.exp(-ntu * (1 - cr))
    return (1 - e) / (1 - cr * e)


class Pasteurizer:
    XH_RATE, XR_RATE = 0.0136, 0.0053      # fouling growth per production hour (assumption)

    def __init__(self, twin, seed=1):
        self.tw = twin
        self.k = _k(twin)
        d = twin["design"]
        self.p, self.ht, self.he, self.pr, self.cip = d["process"], d["holding_tube"], d["heater"], d["pressures"], d["cip"]
        self.cw = self.he["hot_water_flow_m3_h"] * 1000 / 3600 * self.he["hot_water_density_kg_l"] * self.he["hot_water_cp_kj_kgk"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.qbase, self.tin, self.run_h, self.phase, self.start_q, self.dsp = self.p["run_flow_l_h"], self.p["raw_in_c"], 6.0, 0.0, self.p["run_flow_l_h"], 0.0

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    def vary(self):
        """A random but plausible operating point (flow 9,300-9,600 l/h, raw milk 3-6 °C, anywhere in the run)."""
        self.qbase = self.rnd.uniform(9300, 9600)
        self.tin = self.rnd.uniform(3.0, 6.0)
        self.run_h = self.rnd.uniform(0.5, 9.5)
        self.phase = self.rnd.uniform(0, 2 * math.pi)
        self.start_q = self.rnd.uniform(9400, 9600)

    # true state ---------------------------------------------------------------------------------------------------
    def true(self):
        f, k = self.faults, self.k
        q = self.qbase * (1 + 0.12 * f["flow_timing_drift"])
        c = k["kc"] * q
        hrs = self.run_h + self.cip["run_length_h"] * f["cip_skipped"]
        xh = self.XH_RATE * hrs + 0.2 * f["cip_incomplete"] + 1.0 * f["heater_fouling"]
        xr = self.XR_RATE * hrs + 1.0 * f["regen_fouling"]
        hu = f["heating_unstable"]
        heat_out = self.p["pasteurization_setpoint_c"] + self.dsp - 1.3 * hu + 0.3 * hu * math.sin(self.phase)
        hold = heat_out - self.ht["heat_loss_k"]
        eps = regen_eps(k, q, xr)
        rro = self.tin + eps * (hold - self.tin)
        rpo = hold - (rro - self.tin)
        duty = c * (heat_out - rro)
        cmin, cmax = min(c, self.cw), max(c, self.cw)
        uh = k["uh"] * (q / k["q0"]) ** k["eh"] / (1 + xh)
        eh = eps_cf(uh * k["ah"] / (cmin * 1000), cmin / cmax)
        hw_in = rro + duty / (cmin * eh)
        hw_out = hw_in - duty / self.cw
        fq = (q / k["q0"]) ** 1.8
        dph = k["dph0"] * fq * (1 + 1.1 * xh)
        dpr = k["dpr0"] * fq * (1 + 1.8 * xr)
        p_raw = self.pr["p_raw_regen_in_bar"] + (dpr - k["dpr0"] * fq)
        p_past = self.pr["p_past_regen_out_bar"] - 0.97 * f["pressure_diff_loss"]
        fwd = 1 if p_past - p_raw >= k["dpmin"] else 0
        diverts = max(round(8 * hu), 0 if fwd else 6)
        start_dp = k["dph0"] * (self.start_q / k["q0"]) ** 1.8 * (1 + 1.1 * 0.2 * f["cip_incomplete"])
        steam = duty * 3600 / (k["hfg"] * k["eff"])
        return {"q": q, "tin": self.tin, "rro": rro, "heat_out": heat_out, "hold": hold, "rpo": rpo, "hw_in": hw_in, "hw_out": hw_out,
                "p_raw": p_raw, "p_past": p_past, "dph": dph, "dpr": dpr, "fwd": fwd, "diverts": diverts, "hrs": hrs,
                "start_dp": start_dp, "lye": 75.0 - 10.0 * f["cip_incomplete"], "steam": steam, "xh": xh, "xr": xr, "eps": eps, "duty": duty}

    # one published message ------------------------------------------------------------------------------------------
    def reading(self, s):
        f = self.faults
        return {
            "flow_l_h": round(s["q"] * (1 + self.n(0.002)), 1),
            "raw_in_c": round(s["tin"] + self.n(0.03), 2),
            "regen_raw_out_c": round(s["rro"] + self.n(0.03), 2),
            "heat_out_c": round(s["heat_out"] + self.n(0.03), 2),
            "hold_out_c": round(s["hold"] + 1.2 * f["stlr_drift"] + self.n(0.03), 2),
            "hold_ref_c": round(s["hold"] + self.n(0.03), 2),
            "regen_past_out_c": round(s["rpo"] + self.n(0.03), 2),
            "product_out_c": round(self.p["outlet_c"] + self.n(0.05), 2),
            "hw_in_c": round(s["hw_in"] + self.n(0.03), 2),
            "hw_out_c": round(s["hw_out"] + self.n(0.03), 2),
            "p_raw_regen_in_bar": round(s["p_raw"] + self.n(0.005), 3),
            "p_past_regen_out_bar": round(s["p_past"] + self.n(0.005), 3),
            "dp_heater_bar": round(s["dph"] * (1 + self.n(0.01)), 4),
            "dp_regen_bar": round(s["dpr"] * (1 + self.n(0.01)), 4),
            "fdd_forward": s["fwd"],
            "fdd_diverts_1h": s["diverts"],
            "hours_since_cip": round(s["hrs"], 2),
            "run_start_dp_heater_bar": round(s["start_dp"] * (1 + self.n(0.01)), 4),
            "run_start_flow_l_h": round(self.start_q, 1),
            "cip_lye_return_c": round(s["lye"] + self.n(0.3), 1),
            "steam_kg_h": round(s["steam"] * (1 + self.n(0.01)), 1),
        }

    def measure(self):
        self.vary()
        return self.reading(self.true())


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

    The plant clock runs `demo.time_scale` times faster than real time. A production run lasts the validated run length
    (10 plant hours = 10 real minutes at 60x); fouling grows during the run, then a CIP resets it and the next run starts
    with the pressure drop the CIP left behind. Flow and raw milk temperature drift a little; the plant does not depend on
    the time of day.
    """

    def __init__(self, twin, seed=6801):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.x = Pasteurizer(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.runlen = twin["design"]["cip"]["run_length_h"]
        self.t = 0.0
        self.running, self.trip = True, 0
        self.real = 0.0
        self.x.run_h = 3.0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        """All faults to zero at once and a fresh CIP: a clean pasteurizer at the start of a run."""
        for f in self.faults.values():
            f.sev = f.target = 0.0
        self.x.run_h = 0.0
        self.x.start_q = self.x.qbase

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.x.faults[k] = f.sev
        self.t += dt * self.scale
        self.real += dt
        self.x.run_h += dt * self.scale / 3600
        if self.x.run_h >= self.runlen:              # end of the validated run: CIP, then a new run
            self.x.run_h = 0.0
            self.x.start_q = self.x.qbase
        ph = 2 * math.pi * (self.t % 14400) / 14400
        self.x.qbase = 9480 + 70 * math.sin(ph)
        self.x.tin = 4.3 + 0.8 * math.sin(ph / 3 + 1.0)
        self.x.dsp = 0.05 * math.sin(2 * math.pi * self.real / 23)
        self.x.phase = 2 * math.pi * self.real / 40
        return self.x.true()

    def measure(self, true):
        return self.x.reading(true)
