"""Physics model of GT-501 (Siemens Energy SGT-400, 13 MW power generation): the stand-in for the real gas turbine.

Two-shaft Brayton cycle with constant specific heats (thermodynamic stand-in, not Siemens' model):
  inlet      ambient T0, p0; inlet filter loss dp_f ~ (air flow)^2 -> compressor inlet T1 = T0, P1 = p0 - dp_f
  compressor corrected flow Wc = Wc0 * n^a (n = gas generator corrected speed); isentropic efficiency eta_c
  combustor  6 can-annular DLE cans, pressure loss 4 %, fuel natural gas LHV 50 MJ/kg (assumption), burner eff. 99.5 %
             fuel from the energy balance  (m_a + m_f) cp_g (T4 - Tref) = m_a cp_a (T2 - Tref) + m_f LHV eta_b
  CT         2-stage compressor turbine drives the compressor (mechanical eff. 99 %); its nozzle is choked:
             m_g sqrt(T4) / P2 = K1 sets the pressure ratio
  PT         2-stage free power turbine at 9,500 rpm (generator synchronous), nozzle choked: m_g sqrt(T45) / P45 = K2;
             expands to the exhaust pressure p0 + dp_exh; shaft power x L (gearbox + generator) = electrical output
  matching   for a given turbine inlet temperature T4 the gas generator speed n is solved (bisection) so that both
             nozzles pass the same gas: the classic two-shaft working line
  control    governor: PI on T4 to meet the power demand, limited by the firing temperature limit T4_max (the ISO
             value) and the gas generator speed limit. Hot days hit the T4 limit at lower power: the derate falls out.

Calibration (build_twin.py, `calibrate()`): ISO 15 C, 101.325 kPa, no inlet/exhaust losses, natural gas, base load.
  Siemens Energy SGT-400 13 MW data sheet: 12.9 MWe, 35.0 % (heat rate 10,294 kJ/kWh), PR 17.1, exhaust 40.0 kg/s, 555 C.
  Fixed (assumed): eta_c 0.86, cp_a 1005 J/kgK, gamma_a 1.4, gamma_g 1.333, combustor dp 4 %, eta_b 0.995, gearbox x
  generator efficiency L 0.96. Fitted: the effective gas cp_g (so that the exhaust and the output close the energy
  balance at 555 C), the turbine isentropic efficiency eta_t (CT and PT, so that the PT exit is 555 C), T4, K1, K2, Wc0.
  These are calibrated stand-in values, not Siemens data.

Faults (twin file failure_modes): compressor_fouling (corrected flow -5 %, eta_c -2.5 pts at full severity, after
Meher-Homji et al. 2013), hot_section (eta_t of the CT -3 pts), burner_fault (one can runs hot: two exhaust thermocouples
read high), thermocouple_fault (exhaust TC 5 reads low: the sensor, not the engine), inlet_filter (filter dp x6),
bearing_wear (PT bearing shaft vibration and drain temperature), lube_cooler (lube oil header temperature).
"""
import math
import random

TREF = 288.15
P_ISO = 101.325
N_TC = 6                        # exhaust thermocouples: count assumed (Siemens' count not published)
TC_PATTERN = [6.0, -4.0, 9.0, -7.0, 3.0, -5.0]   # normal circumferential exhaust profile at full load, K (assumed)


def calibrate(iso):
    """Fit the stand-in cycle to the data-sheet ISO point. Returns the cycle constants."""
    c = dict(eta_c=0.86, cp_a=1005.0, ka=0.4 / 1.4, kg=0.333 / 1.333, dp_comb=0.04, eta_b=0.995, L=0.96,
             eta_m=0.99, lhv=iso["lhv_mj_kg"] * 1e6, wc_exp=2.0)
    P = iso["power_mw"] * 1e6
    mf = iso["power_mw"] * 1000 * iso["heat_rate_kj_kwh"] / 3600.0 / (c["lhv"] / 1000)
    mg = iso["exhaust_flow_kg_s"]
    ma = mg - mf
    T1, PR, T5 = TREF, iso["pressure_ratio"], iso["exhaust_temp_c"] + 273.15
    T2 = T1 * (1 + (PR ** c["ka"] - 1) / c["eta_c"])
    wcomp = ma * c["cp_a"] * (T2 - T1) / c["eta_m"]
    wpt = P / c["L"]

    def from_cp(cpg):
        T4 = TREF + (ma * c["cp_a"] * (T2 - TREF) + mf * c["lhv"] * c["eta_b"]) / (mg * cpg)
        T45 = T4 - wcomp / (mg * cpg)
        T5c = T45 - wpt / (mg * cpg)
        return T4, T45, T5c

    lo, hi = 900.0, 1600.0                 # effective cp_g so that the PT exit is 555 C
    for _ in range(80):
        cpg = (lo + hi) / 2
        if from_cp(cpg)[2] > T5:
            lo = cpg
        else:
            hi = cpg
    T4, T45, _ = from_cp(cpg)
    P3 = PR * (1 - c["dp_comb"])           # relative to P_ISO
    Pexh = 1.0

    def t5_for(eta):                         # same eta for CT and PT
        prct = (1 - (T4 - T45) / (eta * T4)) ** (-1 / c["kg"])
        p45 = P3 / prct
        return T45 * (1 - eta * (1 - (p45 / Pexh) ** (-c["kg"]))), prct, p45

    lo, hi = 0.70, 0.99
    for _ in range(80):
        eta = (lo + hi) / 2
        if t5_for(eta)[0] > T5:
            lo = eta
        else:
            hi = eta
    _, prct, p45 = t5_for(eta)
    c.update(cp_g=round(cpg, 2), eta_t=round(eta, 5), T4_iso=round(T4, 2), wc0=round(ma, 4),
             K1=mg * math.sqrt(T4) / PR, K2=mg * math.sqrt(T45) / p45,
             iso_check=dict(T2_c=round(T2 - 273.15, 1), T4_c=round(T4 - 273.15, 1), T45_c=round(T45 - 273.15, 1),
                            pr_ct=round(prct, 3), pr_pt=round(p45 / Pexh, 3), fuel_kg_s=round(mf, 4), air_kg_s=round(ma, 3)))
    c["K1"], c["K2"] = round(c["K1"], 6), round(c["K2"], 6)
    return c


class Cycle:
    """Steady two-shaft cycle for given ambient, losses, T4 and degradation."""

    def __init__(self, c):
        self.c = c

    def at_n(self, n, T1, P1, T4, deg):
        c = self.c
        th, de = T1 / TREF, P1 / P_ISO
        ma = c["wc0"] * n ** c["wc_exp"] * (1 - 0.05 * deg.get("foul", 0)) * de / math.sqrt(th)
        eta_c = c["eta_c"] - 0.025 * deg.get("foul", 0)
        eta_t = c["eta_t"] - 0.03 * deg.get("hot", 0)
        mf = 0.018 * ma
        for _ in range(4):
            mg = ma + mf
            PR = mg * math.sqrt(T4) / (c["K1"] * de)
            T2 = T1 * (1 + (max(PR, 1.0001) ** c["ka"] - 1) / eta_c)
            mf = ma * (c["cp_g"] * (T4 - TREF) - c["cp_a"] * (T2 - TREF)) / (c["lhv"] * c["eta_b"] - c["cp_g"] * (T4 - TREF))
        mg = ma + mf
        wcomp = ma * c["cp_a"] * (T2 - T1) / c["eta_m"]
        T45 = T4 - wcomp / (mg * c["cp_g"])
        x = 1 - (T4 - T45) / (eta_t * T4)
        if x <= 0.05 or mf <= 0:
            return None
        prct = x ** (-1 / c["kg"])
        P3 = PR * de * (1 - c["dp_comb"])
        p45 = P3 / prct
        return dict(n=n, ma=ma, mf=mf, mg=mg, PR=PR, T2=T2, T4=T4, T45=T45, p45=p45, P3=P3,
                    resid=mg * math.sqrt(T45) / p45 - c["K2"], eta_c=eta_c)

    def solve(self, T1, P1, Pexh, T4, deg, n0=None):
        lo, hi = 0.45, 1.25
        for _ in range(48):
            n = (lo + hi) / 2
            s = self.at_n(n, T1, P1, T4, deg)
            if s is None or s["resid"] > 0:   # more gas than the PT nozzle passes -> lower speed
                hi = n
            else:
                lo = n
        s = self.at_n((lo + hi) / 2, T1, P1, T4, deg)
        if s is None:
            return None
        c = self.c
        prpt = s["p45"] / (Pexh / P_ISO)
        T5 = s["T45"] * (1 - c["eta_t"] * (1 - max(prpt, 1.0001) ** (-c["kg"])))
        s["T5"] = T5
        s["power_w"] = max(0.0, s["mg"] * c["cp_g"] * (s["T45"] - T5) * c["L"])
        return s


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
    def __init__(self, twin, seed=501):
        self.twin, self.rng = twin, random.Random(seed)
        self.d = twin["design"]
        self.cyc = Cycle(self.d["cycle"])
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.T4 = self.d["cycle"]["T4_iso"] - 120
        self.integ = 0.0
        self.s = None
        self.ngg = 0.95
        self.counters = {"hours": 31250.0, "starts": 412, "washes": 86}
        self.load_bias = 0.0
        self.T = {"oil": 52.0, "brg_gg": 88.0, "brg_pt": 86.0, "brg_gen": 72.0}
        self.ramp_limit = 1.0                  # 0..1 available after a restart
        self.dp_f = self.d["inlet"]["filter_dp_clean_pa"]

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        if self.faults["compressor_fouling"].sev > 0.1:
            self.counters["washes"] += 1          # an off-line wash restores the compressor
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        if self.trip:
            self.trip, self.running = 0, True
            self.counters["starts"] += 1
            self.ramp_limit = 0.0

    def fault_state(self):
        return {k: round(v.sev, 3) for k, v in self.faults.items()}

    def ambient(self):
        h = (self.t / 3600.0) % 24
        a = self.d["site"]
        T0 = a["t_mean_c"] + a["t_swing_c"] * math.sin(2 * math.pi * (h - 9.0) / 24)
        return T0, a["p0_kpa"]

    def demand(self):
        h = (self.t / 3600.0) % 24
        s = self.d["site"]
        self.load_bias = 0.995 * self.load_bias + self.rng.gauss(0, 0.004)
        return max(3.0, s["demand_base_mw"] + s["demand_peak_mw"] * math.exp(-((h - 15.0) / 5.0) ** 2) + self.load_bias)

    def deg(self):
        f = self.faults
        return {"foul": f["compressor_fouling"].sev, "hot": f["hot_section"].sev}

    def steady(self, T0c, p0, T4, deg, dp_f):
        """Steady state at T4 with the filter loss iterated on the air flow."""
        T1 = T0c + 273.15
        Pexh = p0 + self.d["exhaust"]["dp_kpa"]
        s = None
        for _ in range(3):
            s = self.cyc.solve(T1, p0 - dp_f / 1000, Pexh, T4, deg)
            if s is None:
                return None
            dp_f = self.d["inlet"]["filter_dp_clean_pa"] * (s["ma"] / self.d["cycle"]["wc0"]) ** 2 * (1 + 5.0 * self.faults["inlet_filter"].sev)
        s["dp_f"], s["P1"], s["T1"] = dp_f, p0 - dp_f / 1000, T1
        return s

    def step(self, dt=1.0):
        f, d = self.faults, self.d
        for x in f.values():
            x.step(dt)
        self.t += dt
        T0, p0 = self.ambient()
        dem = self.demand()
        c = d["cycle"]
        lim = d["limits_control"]
        if self.running:
            self.counters["hours"] += dt / 3600
            self.ramp_limit = min(1.0, self.ramp_limit + dt / 600)        # 10 min to full load after a start
            target = min(dem, d["rating"]["power_mw"] * 1.1 * self.ramp_limit + 0.5)
            p_now = self.s["power_w"] / 1e6 if self.s else 0.0
            err = target - p_now
            self.integ = max(-400, min(400, self.integ + 6.0 * err * dt))
            T4 = c["T4_iso"] - 250 + self.integ + 25 * err
            T4 = max(c["T4_iso"] - 520, min(c["T4_iso"], T4))
            s = self.steady(T0, p0, T4, self.deg(), self.dp_f)
            if s and s["n"] > lim["ngg_max"]:            # speed limit on cold days
                lo, hi = c["T4_iso"] - 520, T4
                for _ in range(30):
                    mid = (lo + hi) / 2
                    sm = self.steady(T0, p0, mid, self.deg(), self.dp_f)
                    if sm is None or sm["n"] > lim["ngg_max"]:
                        hi = mid
                    else:
                        lo = mid
                T4 = lo
                s = self.steady(T0, p0, T4, self.deg(), self.dp_f)
            if s:
                self.s, self.T4, self.dp_f = s, T4, s["dp_f"]
            self.ngg += ((self.s["n"] if self.s else 0) - self.ngg) * min(1.0, dt / 4)
        else:
            self.ngg += (0.0 - self.ngg) * min(1.0, dt / 40)
        return self.read(T0, p0, dt)

    def read(self, T0, p0, dt=1.0):
        f, s, d = self.faults, self.s, self.d
        run = self.running and s is not None
        load = (s["power_w"] / 1e6 / d["rating"]["power_mw"]) if run else 0.0
        T1c = T0
        if run:
            cdp = s["PR"] * s["P1"] / 100.0                       # bar(a)
            cdt = s["T2"] - 273.15
            t5 = s["T5"] - 273.15
            fuel = s["mf"]
            power = s["power_w"] / 1e6
            P1 = s["P1"]
            dpf = s["dp_f"]
        else:
            cdp, cdt, t5, fuel, power, P1, dpf = p0 / 100, T0 + 2, T0 + 40, 0.0, 0.0, p0, 0.0
        # exhaust thermocouples: circumferential profile + burner (hot can) + a failed TC
        tcs = []
        for i in range(N_TC):
            v = t5 + TC_PATTERN[i] * max(load, 0.2)
            if run:
                v += f["burner_fault"].sev * (40.0 if i == 2 else 20.0 if i == 3 else -15.0)   # same total fuel: the other cans run leaner
            v -= f["thermocouple_fault"].sev * (110.0 if i == 4 else 0.0)
            tcs.append(v)
        # lube oil and bearings (first-order lags)
        oil_t = 50.0 + 0.12 * (T0 - 30) + 3.0 * load + 24.0 * f["lube_cooler"].sev
        dt_lag = min(1.0, dt / 300)
        self.T["oil"] += (oil_t - self.T["oil"]) * dt_lag
        self.T["brg_gg"] += ((self.T["oil"] + 30 + 6 * load) - self.T["brg_gg"]) * dt_lag
        self.T["brg_pt"] += ((self.T["oil"] + 26 + 5 * load + 22 * f["bearing_wear"].sev) - self.T["brg_pt"]) * dt_lag
        self.T["brg_gen"] += ((self.T["oil"] + 18 + 3 * load) - self.T["brg_gen"]) * dt_lag
        gg_vib = (1.6 + 1.4 * load + 0.4 * f["compressor_fouling"].sev) if run else 0.2
        pt_prox = (24.0 + 6.0 * load + 78.0 * f["bearing_wear"].sev ** 1.4) if (run or self.ngg > 0.2) else 4.0
        gen_vib = (1.1 + 0.6 * load) if run else 0.1
        # protections (typical): lube oil 80 C, PT shaft vibration 125 um
        if run and not self.trip:
            if self.T["oil"] > 80:
                self.trip = 2
            elif pt_prox > 125:
                self.trip = 3
            if self.trip:
                self.running = False
                self.s = None
        ngg_pct = self.ngg * 100 if self.running else self.ngg * 100
        out = {"ambient_temp_c": T0, "ambient_pressure_kpa": p0, "inlet_temp_c": T1c, "inlet_pressure_kpa": P1,
               "inlet_filter_dp_pa": dpf, "ngg_pct": ngg_pct,
               "npt_rpm": d["rating"]["pt_speed_rpm"] * (1.0 if run else 0.0),
               "cdp_bar": cdp, "cdt_c": cdt,
               "fuel_flow_kg_s": fuel, "fuel_gas_pressure_bar": 24.6 if run else 25.4, "fuel_gas_temp_c": 32.0 + 0.2 * (T0 - 30),
               "power_mw": power, "gg_vib_mm_s": gg_vib, "pt_prox_um": pt_prox, "gen_vib_mm_s": gen_vib,
               "lube_oil_pressure_bar": (2.4 if run else 0.3) - 0.1 * f["bearing_wear"].sev, "lube_oil_temp_c": self.T["oil"],
               "brg_gg_temp_c": self.T["brg_gg"], "brg_pt_temp_c": self.T["brg_pt"], "brg_gen_temp_c": self.T["brg_gen"],
               "running_hours": self.counters["hours"], "starts": self.counters["starts"], "washes": self.counters["washes"],
               "fault_code": self.trip}
        for i, v in enumerate(tcs):
            out[f"egt_tc{i + 1}_c"] = v
        return out

    def measure(self, true):
        out = {}
        for p in self.twin["telemetry"]["points"]:
            k = p["metric"]
            v = true[k]
            if p["noise"]:
                v = v + self.rng.gauss(0, p["noise"])
            lo, hi = p["range"]
            v = max(lo, min(hi, v))
            out[k] = int(v) if k in ("fault_code", "starts", "washes") else round(v, 4 if abs(v) < 10 else 2)
        return out
