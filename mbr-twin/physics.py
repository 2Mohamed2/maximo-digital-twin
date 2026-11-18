"""A stand-in for MBR-5301: the membrane train, its permeate pump, air scour and cleaning records, with injectable faults.

The real PLC sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the expected
values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests, the figures and the live pages.

True state: the permeability at 20 °C right after the last maintenance clean (MC) falls linearly with the time since that
clean at a fouling rate r (fraction per day). Weak air scour and poor sludge filterability raise r. A maintenance clean
brings the permeability back to a level a little below the last recovery clean (RC); irreversible fouling lowers both.
Sludging blocks part of the fibres, so the permeability seen on the nominal area drops at once. The TMP follows from
    TMP = J x TCF(T) / K20 x 100     (kPa; J the flux, TCF the viscosity ratio to 20 °C)
"""
import math
import random

import twin_calc as tc


class Membrane:
    def __init__(self, twin, seed=1):
        self.twin = twin
        self.k = tc._k(twin)
        d = twin["design"]
        self.d = d
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.h_mc = 84.0                 # mid-way through the weekly cycle
        self.h_rc = 2000.0
        self.temp = d["operation"]["temp_nominal_c"]
        self.mc_temp = d["operation"]["temp_nominal_c"] + 0.4
        self.inflow = 1.0                # forward flow relative to design

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state ---------------------------------------------------------------------------------------------------------
    def rate(self):
        f = self.faults
        return (self.d["permeability"]["fouling_rate_design_pct_d"] / 100 + 0.065 * f["poor_filterability"] + 0.05 * f["air_scour_low"])

    def k_rc(self):
        return self.d["permeability"]["k_rc_last_lmhbar"] * (1 - 0.4 * self.faults["irreversible_fouling"])

    def k_after_mc(self):
        return self.k_rc() * (0.95 - 0.25 * self.faults["irreversible_fouling"])

    def state(self):
        k, f, d = self.k, self.faults, self.d
        h_mc = self.h_mc + (250.0 * f["mc_skipped"] if not hasattr(self, "_live") else 0.0)
        cass = k["ncass"] - (1 if f["peak_flux"] >= 0.5 else 0)
        q = d["operation"]["flow_design_m3h"] * self.inflow * (1 + 0.25 * f["peak_flux"])
        j = q * 1000 / (k["am"] * cass)
        r = self.rate()
        kmc = self.k_after_mc()
        k20 = kmc * max(0.3, 1 - r * h_mc / 24) * (1 - 0.7 * f["sludging"])
        tmp = j * tc.tcf(k, self.temp) / k20 * 100
        mc_j = d["operation"]["flux_design_lmh"]
        mc_after = mc_j * tc.tcf(k, self.mc_temp) / kmc * 100
        week = self.k["mci"] / 24
        rec = (1 / max(0.3, 1 - d["permeability"]["fouling_rate_design_pct_d"] / 100 * week) - 1) * (1 - 0.85 * f["irreversible_fouling"])
        air = d["aeration"]["air_design_nm3h"] * cass / k["ncass"] * (1 - 0.5 * f["air_scour_low"])
        return {
            "q": q, "cass": cass, "j": j, "k20": k20, "tmp": tmp, "temp": self.temp, "h_mc": h_mc, "h_rc": self.h_rc,
            "mc_j": mc_j, "mc_temp": self.mc_temp, "mc_after": mc_after, "mc_before": mc_after * (1 + rec), "k_rc": self.k_rc(),
            "air": air, "blower_kw": d["aeration"]["blower_kw_design"] * air / d["aeration"]["air_design_nm3h"],
            "pump_kw": 3.0 + q * (tmp + 35.0) / 3600 / 0.6,
            "mlss": d["process"]["mlss_nominal_mgl"] + 5000.0 * f["sludging"],
            "ttf": d["process"]["ttf_nominal_s"] + 170.0 * f["poor_filterability"],
            "turb": d["process"]["turbidity_nominal_ntu"] + 0.75 * f["fibre_breakage"],
        }

    # one published message ----------------------------------------------------------------------------------------------
    def reading(self, s):
        n = self.n
        return {
            "running": 1, "cassettes_in_service": s["cass"], "permeate_flow_m3h": round(s["q"] * (1 + n(0.002)), 2),
            "tmp_kpa": round(s["tmp"] * (1 + n(0.004)), 2), "permeate_turbidity_ntu": round(max(0.01, s["turb"] + n(0.008)), 3),
            "permeate_pump_kw": round(s["pump_kw"] + n(0.05), 2), "ml_temp_c": round(s["temp"] + n(0.05), 2),
            "mlss_mgl": round(s["mlss"] + n(120), 0), "sludge_ttf_s": round(s["ttf"] + n(2), 0),
            "air_scour_nm3h": round(s["air"] * (1 + n(0.005)), 0), "scour_blower_kw": round(s["blower_kw"] + n(0.3), 1),
            "mc_flux_lmh": round(s["mc_j"], 2), "mc_temp_c": round(s["mc_temp"], 2),
            "mc_tmp_before_kpa": round(s["mc_before"], 2), "mc_tmp_after_kpa": round(s["mc_after"], 2),
            "hours_since_mc": round(s["h_mc"], 1), "rc_perm20_lmhbar": round(s["k_rc"], 1), "hours_since_rc": round(s["h_rc"], 0),
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

    The train produces continuously at the design flow (a gentle diurnal swing of +/- 8 % on the plant clock is left out
    on purpose: the twin compares at any flux). The plant clock runs `demo.time_scale` times faster than real time: the
    hours since the last maintenance clean grow, the permeability falls, and every `cleaning.mc_interval_h` plant hours the
    PLC runs a maintenance clean (skipped while 'mc_skipped' is active). A recovery clean runs every
    `cleaning.rc_interval_h`. The mixed liquor temperature drifts +/- 1 °C over about half an hour of real time.
    reset() stands for a recovery clean on demand.
    """

    def __init__(self, twin, seed=5301):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.m = Membrane(twin, seed)
        self.m._live = True
        self.m.h_mc = 30.0
        self.base_t = twin["design"]["operation"]["temp_nominal_c"]
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.clock = 0.0
        self.running, self.trip = True, 0
        self.mci = twin["design"]["cleaning"]["mc_interval_h"]
        self.rci = twin["design"]["cleaning"]["rc_interval_h"]

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        """Recovery clean on demand: the cleaning clock restarts from zero."""
        self.m.h_rc = 0.0
        self.m.h_mc = 0.0
        self.m.mc_temp = self.m.temp

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.m.faults[k] = f.sev
        hours = dt * self.scale / 3600
        self.t += dt * self.scale
        self.clock += dt
        self.m.temp = self.base_t + 1.0 * math.sin(2 * math.pi * self.clock / 1800.0)
        self.m.h_mc += hours
        self.m.h_rc += hours
        if self.m.h_rc >= self.rci:
            self.reset()
        elif self.m.h_mc >= self.mci and self.faults["mc_skipped"].sev < 0.3:
            self.m.h_mc = 0.0
            self.m.mc_temp = self.m.temp
        return self.m.state()

    def measure(self, true):
        return self.m.reading(true)
