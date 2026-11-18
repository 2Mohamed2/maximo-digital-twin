"""A stand-in for BESS-3501: the LFP battery container (cells, BMS), its HVAC, its PCS and its gas detection, with injectable faults.

The real BMS, PCS and HVAC send the same points (see telemetry.points in the twin file). Nothing here is used by Monitor:
the expected values are computed in Monitor from the twin file only. This model only produces believable readings and
fault fingerprints for the tests, the figures and the live pages.
"""
import math
import random


def ocv(soc):
    """Open-circuit voltage of an LFP cell (V) against state of charge (0..1): a flat plateau with two knees."""
    v = 3.18 + 0.16 * soc
    if soc < 0.10:
        v -= 2.0 * (0.10 - soc)
    if soc > 0.95:
        v += 3.0 * (soc - 0.95)
    return v


class Bess:
    def __init__(self, twin, seed=1):
        self.t = twin
        d = twin["design"]
        self.c, self.e, self.h, self.a, self.cell = d["container"], d["electrical"], d["hvac"], d["ageing"], d["cell"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.days, self.efc, self.tlife = 1460.0, 1300.0, 27.0

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state ---------------------------------------------------------------------------------------------------
    def pcs_loss(self, p_ac):
        e = self.e
        kl = (e["pcs_loss_rated_kw"] - e["pcs_noload_kw"]) / e["pcs_rated_kw"] ** 2
        return (e["pcs_noload_kw"] + kl * p_ac ** 2) * (1 + 1.6 * self.faults["pcs_degradation"])

    def soh_model(self):
        a = self.a
        ft = 2.0 ** ((self.tlife - a["t_ref_c"]) / a["t_double_k"])
        return 100 - ft * (a["k_cal_pct_sqrt_year"] * math.sqrt(self.days / 365) + a["k_cyc_pct_per_efc"] * self.efc)

    def true_state(self, p_frac=0.9, soc=0.55, amb=32.0, running=True):
        """One operating point: p_frac x rated AC power (+ discharge, - charge) at state of charge soc (0..1)."""
        f = self.f = self.faults
        p_ac = self.e["pcs_rated_kw"] * p_frac if running else 0.0
        loss = self.pcs_loss(p_ac)
        p_dc = p_ac + loss
        ns = self.c["cells_series"]
        rcell = self.e["r_string_ohm"] / ns
        v0 = ocv(soc) * ns
        i = p_dc * 1000 / v0
        istr = i / self.c["strings"]
        v = v0 - istr * self.e["r_string_ohm"]
        # heat and HVAC
        h = self.h
        bh = self.c["strings"] * istr ** 2 * self.e["r_string_ohm"] / 1000
        sup = h["supply_setpoint_c"] + 6.0 * f["hvac_degraded"]
        load = bh + h["aux_internal_kw"]
        air = h["airflow_m3h"] * max(0.3, min(1.0, (load + 1.0) / 17.0))
        dT = load / (h["rho_cp_kj_m3k"] / 3600 * air)
        ret = sup + dT
        env = h["ua_kw_per_k"] * (amb - ret)
        dT = (load + env) / (h["rho_cp_kj_m3k"] / 3600 * air)
        ret = sup + dT
        cool = h["rho_cp_kj_m3k"] / 3600 * air * dT
        cope = h["cop_35c"] * (1 - h["cop_slope_per_k"] * (amb - 35))
        hpow = cool / (cope * (1 - 0.45 * f["hvac_degraded"]))
        tavg = ret - 1.0 + 4.0 * (istr / 138.0) ** 2
        return dict(p_ac=p_ac, p_dc=p_dc, i=i, istr=istr, v=v, soc=soc, rcell=rcell, sup=sup, ret=ret, air=air, hpow=hpow,
                    amb=amb, tavg=tavg, running=running, dr=1.2e-3 * f["weak_module"])

    # one published message ------------------------------------------------------------------------------------------
    def measure(self, s=None):
        s = s or self.true_state()
        f, n = self.faults, self.n
        ns = self.c["cells_series"]
        istr, vavg = s["istr"], s["v"] / ns
        rest = 8.0 + 52.0 * f["cell_imbalance"] + n(0.5)
        norm = 0.06e-3 * abs(istr)
        vmax = vavg + rest / 2000 + norm / 2 + (s["dr"] * abs(istr) if istr < 0 else 0.0)
        vmin = vavg - rest / 2000 - norm / 2 - (s["dr"] * abs(istr) if istr > 0 else 0.0)
        tp = f["thermal_runaway_precursor"]
        tavg = s["tavg"]
        tmax = tavg + 1.5 + 7.0 * f["weak_module"] + 15.0 * tp + s.get("self_heat", 0.0)
        tmin = tavg - 1.5
        k = self.e
        rte_loss = 1 + 1.6 * f["pcs_degradation"]
        kl = (k["pcs_loss_rated_kw"] - k["pcs_noload_kw"]) / k["pcs_rated_kw"] ** 2
        pr = k["pcs_rated_kw"]
        eta_pcs = 1 - rte_loss * (k["pcs_noload_kw"] + kl * pr ** 2) / pr
        vn = ns * self.cell["nominal_v"]
        x = pr * 1000 / (vn * self.c["strings"]) * k["r_string_ohm"] / vn
        rte = eta_pcs ** 2 * (1 - x) / (1 + x)
        dis = 1150.0 + n(8)
        soh = self.soh_model() - 6.5 * f["capacity_fade_fast"] + n(0.25)
        return {
            "soc_pct": round(s["soc"] * 100 + n(0.3), 2), "soh_bms_pct": round(soh, 2),
            "dc_voltage_v": round(s["v"] + n(0.5), 1), "dc_current_a": round(s["i"] + n(0.5), 1),
            "cell_v_max_v": round(vmax + n(0.0005), 4), "cell_v_min_v": round(vmin + n(0.0005), 4),
            "cell_v_spread_rest_mv": round(rest, 1),
            "cell_t_max_c": round(tmax + n(0.2), 2), "cell_t_min_c": round(tmin + n(0.2), 2), "cell_t_avg_c": round(tavg + n(0.1), 2),
            "cell_t_max_rate_c_min": round(0.08 * (istr / 138.0) ** 2 + 2.0 * tp + n(0.04), 3),
            "hvac_supply_air_c": round(s["sup"] + n(0.15), 2), "hvac_return_air_c": round(s["ret"] + n(0.15), 2),
            "hvac_airflow_m3h": round(s["air"] + n(20), 0), "hvac_power_kw": round(s["hpow"] * (1 + n(0.01)), 3),
            "ambient_c": round(s["amb"] + n(0.2), 2),
            "ac_power_kw": round(s["p_ac"] + n(0.15), 2), "pcs_dc_power_kw": round(s["p_dc"] + n(0.15), 2),
            "pcs_running": 1 if s["running"] else 0,
            "offgas_ppm": round(abs(n(0.4)) + 60.0 * tp, 2), "gas_lel_pct": round(abs(n(0.2)) + 4.0 * tp, 2),
            "insulation_kohm": round(2000.0 * 0.02 ** f["insulation_fault"] * (1 + n(0.03)), 1),
            "energy_charged_24h_kwh": round(dis / rte, 1), "energy_discharged_24h_kwh": round(dis, 1),
            "aux_energy_24h_kwh": round(24 * (self.h["aux_internal_kw"] + 6.0 * (1 + 0.8 * f["hvac_degraded"])) + n(3), 1),
            "efc_count": round(self.efc, 2), "days_in_service": round(self.days, 3), "life_cell_temp_avg_c": round(self.tlife + n(0.02), 3),
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

    The container cycles: discharge at 90 % of the PCS rating down to 10 % SOC, rest, charge back to 95 %, rest. The battery
    clock runs demo.time_scale times faster, so one discharge takes about four minutes of real time. The outdoor temperature
    follows the visitor's time of day (P.t, real seconds). When the off-gas or the temperature-rise detection fires, the BMS
    opens the contactors and the PCS stops (trip = 1) until reset().
    """

    def __init__(self, twin, seed=3501):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.rest_s = float(demo.get("rest_s", 60))
        self.b = Bess(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.soc, self.mode, self.rest = 0.85, 1, 0.0   # mode +1 discharge, -1 charge, 0 rest
        self.next_mode = -1
        self.tavg, self.self_heat = None, 0.0   # cell thermal mass (first-order lag) and heat from a self-heating cell

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.running, self.trip = True, 0
        self.mode, self.rest = 1, 0.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.b.faults[k] = f.sev
        self.t += dt
        if self.b.faults["thermal_runaway_precursor"] > 0.5 and not self.trip:
            self.trip, self.running = 1, False
        p_frac = 0.0
        if self.running:
            if self.mode == 0:
                self.rest += dt
                if self.rest >= self.rest_s:
                    self.mode, self.rest = self.next_mode, 0.0
            else:
                p_frac = 0.9 * self.mode
                e_kwh = self.b.c["nameplate_kwh"] * self.b.soh_model() / 100
                dsoc = p_frac * self.b.e["pcs_rated_kw"] * dt * self.scale / 3600 / e_kwh
                self.soc -= dsoc
                self.b.efc += abs(dsoc) / 2
                if self.mode == 1 and self.soc <= 0.10:
                    self.soc, self.mode, self.next_mode = 0.10, 0, -1
                elif self.mode == -1 and self.soc >= 0.95:
                    self.soc, self.mode, self.next_mode = 0.95, 0, 1
        self.b.days += dt * self.scale / 86400
        amb = 32.0 + 6.0 * math.sin(2 * math.pi * ((self.t % 86400) / 86400 - 0.375))
        s = self.b.true_state(p_frac if self.running else 0.0, self.soc, amb, self.running)
        tau = 120.0
        self.tavg = s["tavg"] if self.tavg is None else self.tavg + (s["tavg"] - self.tavg) * min(1.0, dt / tau)
        tp = self.b.faults["thermal_runaway_precursor"]
        self.self_heat = self.self_heat + 2.0 * tp * dt / 60 if tp > 0.01 else max(0.0, self.self_heat - 0.5 * dt / 60)
        s["tavg"], s["self_heat"] = self.tavg, self.self_heat
        return s

    def measure(self, true):
        return self.b.measure(true)
