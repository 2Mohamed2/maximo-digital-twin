"""Physics model of RO-1201, a seawater reverse osmosis train: the stand-in for the real plant.

Train: cartridge filters -> high-pressure (HP) pump in parallel with 3 isobaric energy recovery devices (PX) and a
booster pump -> 40 pressure vessels x 7 spiral-wound elements (DuPont FilmTec SW30HRLE-440i) -> permeate + concentrate;
the concentrate pressurises fresh seawater in the PX and leaves to the outfall.

Membrane (solution-diffusion, per element, solved element by element along each vessel):
  water flux   Jw = A * TCF(T) * NDP            NDP = Pf - dP/2 - Pp - (pi(Cavg) - pi(Cp))       L/(m2 h)
  salt flux    Js = B * TCF(T) * (Cavg - Cp)    Cp = Js / Jw                                     mg/(m2 h)
  osmotic      pi = 0.79 bar per 1000 mg/L      (NaCl-equivalent simplification; no concentration polarisation)
  TCF          exp(2640 * (1/298.15 - 1/(273.15 + T)))   (FilmTec form of the temperature correction factor)
  element dP   k_dp * Qavg^1.5                   (Qavg = mean of element feed and concentrate flow, m3/h)
  A and B are fitted to the data-sheet test point (32,000 mg/L NaCl, 55.2 bar, 25 C, 8 % recovery: 31 m3/d, 99.80 %).
  Each element is solved by bisection on its permeate flow, so the tail elements stay physical when their NDP nears zero.

Plant per step (1 s): seawater temperature and salinity drift through the day; the controls hold the permeate flow
(HP pump speed -> membrane feed pressure, solved by bisection) and the recovery (booster -> PX flow). Faults change
element A, B and k_dp (biofouling at the lead, scaling at the tail, oxidation everywhere), add an interconnector
leak in bank 3, wear the HP pump, increase PX leakage and mixing, clog the cartridge filters, or warm the intake.
"""
import math
import random

AREA = 41.0            # m2 per element (data sheet)
KOS = 0.00079          # bar per mg/L (0.79 bar per 1000 mg/L)


def tcf(t):
    return math.exp(2640.0 * (1.0 / 298.15 - 1.0 / (273.15 + t)))


def element(qf, cf, pf, pp, t, a, b, kdp, area=AREA):
    """One spiral-wound element. qf m3/h, cf mg/L, pf/pp bar(g), t C, a L/(m2 h bar), b L/(m2 h).
    Solved by bisection on the permeate flow (the water balance is monotonic), with Cp = B f Cavg / (Jw + B f),
    which follows from Js = B f (Cavg - Cp) and Cp = Js / Jw and never exceeds Cavg.
    Returns (qp m3/h, cp mg/L, qc m3/h, cc mg/L, dp bar)."""
    f = tcf(t)
    lo, hi, cp = 0.0, 0.6 * qf, cf * 0.004
    for _ in range(18):
        qp = 0.5 * (lo + hi)
        qc = qf - qp
        jq = qp * 1000.0 / area                       # the flux this trial permeate flow means
        for _ in range(2):
            cc = (qf * cf - qp * cp) / qc
            cavg = 0.5 * (cf + cc)
            cp = b * f * cavg / (jq + b * f)
        dp = kdp * (0.5 * (qf + qc)) ** 1.5
        jw = max(a * f * (pf - dp / 2 - pp - KOS * (cavg - cp)), 0.0)
        if jw > jq:
            lo = qp
        else:
            hi = qp
    qp = 0.5 * (lo + hi)
    qc = qf - qp
    cp = b * f * cavg / (qp * 1000.0 / area + b * f)
    cc = (qf * cf - qp * cp) / qc
    return qp, cp, qc, cc, kdp * (0.5 * (qf + qc)) ** 1.5


def fit_ab(test):
    """Fit A and B to the data-sheet test point."""
    qp_t = test["permeate_m3d"] / 24.0
    qf = qp_t / test["recovery"]
    cp_t = test["nacl_mgl"] * (1 - test["rejection"])
    a, b = 1.0, 0.05
    for _ in range(60):
        qp, cp, *_ = element(qf, test["nacl_mgl"], test["pressure_bar"], 0.0, test["temp_c"], a, b, test["kdp"])
        a *= qp_t / qp
        b *= cp_t / cp
    return a, b


def vessel(q, c, p, pp, t, mem, mult):
    """7 elements in series. mult = [(a_mult, b_mult, dp_mult)] per element."""
    qp_tot, salt, dp_tot = 0.0, 0.0, 0.0
    for am, bm, dm in mult:
        qp, cp, q, c, dp = element(q, c, p, pp, t, mem["a"] * am, mem["b"] * bm, mem["kdp"] * dm)
        qp_tot += qp
        salt += qp * cp
        dp_tot += dp
        p -= dp
    return qp_tot, salt / qp_tot, q, c, dp_tot


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


BANK_B = [0.97, 1.02, 1.0, 1.01]     # small natural spread of salt passage between the 4 banks of 10 vessels


def train(d, mem, qm, cm, pm, t, f):
    """Whole train at membrane feed flow qm, salinity cm, pressure pm. f = fault severities.
    Returns dict with permeate, concentrate and bank results."""
    n_v, n_e = d["train"]["vessels"], d["train"]["elements_per_vessel"]
    pp = d["train"]["permeate_pressure_bar"]
    mult = []
    for i in range(n_e):
        am, bm, dm = 1.0, 1.0, 1.0
        if i < 2:                                            # biofouling grows at the lead end
            dm *= 1 + 2.2 * f["biofouling"]
            am *= 1 - 0.22 * f["biofouling"]
        if i >= n_e - 3:                                     # scale precipitates at the tail (highest concentration)
            am *= 1 - 0.7 * f["scaling"]
            bm *= 1 + 0.4 * f["scaling"]
        am *= 1 + 0.25 * f["oxidation"]                      # oxidised polyamide: more water, much more salt
        bm *= 1 + 3.0 * f["oxidation"]
        mult.append((am, bm, dm))
    qv = qm / n_v
    qp_v, cp_v, qc_v, cc_v, dp_v = vessel(qv, cm, pm, pp, t, mem, mult)
    per_bank = n_v // 4
    banks, qp_tot, salt = [], 0.0, 0.0
    leak = d["train"]["oring_leak_frac"] * f["oring_leak"]
    for k in range(4):
        bq, bs = qp_v * per_bank, qp_v * per_bank * cp_v * BANK_B[k]
        if k == 2 and leak > 0:                              # interconnector O-ring leak in bank 3: feed into permeate
            lq = leak * qv * per_bank
            bq += lq
            bs += lq * cm
        banks.append(bs / bq)
        qp_tot += bq
        salt += bs
    qc = qm - qp_tot
    cc = (qm * cm - salt) / qc
    return {"qp": qp_tot, "cp": salt / qp_tot, "qc": qc, "cc": cc, "dp": dp_v, "banks": banks}


class Plant:
    def __init__(self, twin, seed=1201):
        self.twin, self.rng = twin, random.Random(seed)
        self.d = twin["design"]
        self.mem = self.d["membrane"]
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.pm = 60.0
        self.cc_prev = self.d["seawater"]["tds_mgl"] * 1.75
        self.sal_bias = 0.0
        self.q_bias = 0.0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.trip, self.running = 0, True

    def fault_state(self):
        return {k: round(v.sev, 3) for k, v in self.faults.items()}

    def seawater(self):
        sw = self.d["seawater"]
        h = (self.t / 3600.0) % 24
        temp = sw["temp_c"] + sw["temp_swing_c"] * math.sin(2 * math.pi * (h - 9) / 24) + 7.0 * self.faults["feed_temperature"].sev
        self.sal_bias = 0.999 * self.sal_bias + self.rng.gauss(0, 4)
        tds = sw["tds_mgl"] + sw["tds_swing_mgl"] * math.sin(2 * math.pi * (h - 3) / 24) + self.sal_bias
        return temp, tds

    def step(self, dt=1.0):
        f = {k: v.sev for k, v in self.faults.items()}
        for x in self.faults.values():
            x.step(dt)
        self.t += dt
        d, tr, hp, px, cf = self.d, self.d["train"], self.d["hp_pump"], self.d["erd"], self.d["cartridge"]
        temp, cf_tds = self.seawater()
        self.q_bias = 0.995 * self.q_bias + self.rng.gauss(0, 0.05)
        qp_set = tr["permeate_setpoint_m3h"] + self.q_bias
        qm = qp_set / tr["recovery"]
        qc_set = qm - qp_set
        # PX: lubrication (leakage) and volumetric mixing
        lk = qc_set * (px["lubrication_frac"] + 0.05 * f["erd_leakage"])
        mix = px["mixing_frac"] + 0.06 * f["erd_leakage"]
        q_hpout = qc_set - lk
        q_lpin, q_lpout = q_hpout, qc_set
        q_hp = qm - q_hpout
        # cartridge filters and suction
        q_feed = q_hp + q_lpin
        cf_dp = cf["dp_clean_bar"] * (q_feed / cf["design_flow_m3h"]) ** 2 * (1 + 3.6 * f["cartridge_clogging"])
        p_sup = cf["supply_pressure_bar"]
        p_suc = p_sup - cf_dp
        p_lpin = p_suc - 0.2
        p_lpout = px["lp_out_pressure_bar"]
        # membrane feed salinity: PX output carries some brine (mixing); use last step's concentrate
        cm = (q_hp * cf_tds + q_hpout * (cf_tds + mix * (self.cc_prev - cf_tds))) / qm
        # HP pump speed control: find the membrane feed pressure that makes the permeate setpoint
        lo, hi = 30.0, tr["max_pressure_bar"]
        res = None
        for _ in range(26):
            mid = 0.5 * (lo + hi)
            res = train(d, self.mem, qm, cm, mid, temp, f)
            if res["qp"] < qp_set:
                lo = mid
            else:
                hi = mid
        pm = 0.5 * (lo + hi)
        res = train(d, self.mem, qm, cm, pm, temp, f)
        self.pm = pm
        self.cc_prev = res["cc"]
        p_conc = pm - res["dp"]
        p_hpout = p_conc - px["hp_dp_bar"] * (1 + 1.2 * f["erd_leakage"])
        p_hpd = pm + 0.3
        # pumps
        eta_hp = hp["eta_bep"] * (1 - 0.8 * (q_hp / hp["q_bep_m3h"] - 1) ** 2) * (1 - 0.16 * f["hp_pump_wear"])
        hp_kw = q_hp * (p_hpd - p_suc) / 36.0 / eta_hp / hp["eta_motor"]
        bst = d["booster"]
        bst_kw = q_hpout * max(pm - p_hpout, 0.1) / 36.0 / bst["eta"] / bst["eta_motor"]
        speed = 100 * math.sqrt(max(p_hpd - p_suc, 1) / hp["head_rated_bar"])
        orp = d["seawater"]["orp_mv"] + 420 * min(1.0, 4 * f["oxidation"])    # chlorine shows on ORP before the damage
        return {"feed_flow_m3h": q_feed, "feed_tds_mgl": cf_tds, "feed_temp_c": temp, "feed_ph": 7.95 + 0.03 * math.sin(self.t / 4000),
                "feed_orp_mv": orp, "cf_inlet_pressure_bar": p_sup, "cf_dp_bar": cf_dp,
                "hp_suction_pressure_bar": p_suc, "hp_discharge_pressure_bar": p_hpd, "hp_flow_m3h": q_hp, "hp_power_kw": hp_kw,
                "hp_speed_pct": speed, "px_hp_out_pressure_bar": p_hpout, "px_lp_in_pressure_bar": p_lpin, "px_lp_out_pressure_bar": p_lpout,
                "px_hp_out_flow_m3h": q_hpout, "px_lp_in_flow_m3h": q_lpin, "px_lp_out_flow_m3h": q_lpout, "booster_power_kw": bst_kw,
                "membrane_feed_pressure_bar": pm, "membrane_feed_tds_mgl": cm, "vessel_dp_bar": res["dp"], "concentrate_pressure_bar": p_conc,
                "concentrate_flow_m3h": res["qc"], "concentrate_tds_mgl": res["cc"], "permeate_pressure_bar": tr["permeate_pressure_bar"],
                "permeate_flow_m3h": res["qp"], "permeate_tds_mgl": res["cp"],
                "bank1_permeate_tds_mgl": res["banks"][0], "bank2_permeate_tds_mgl": res["banks"][1],
                "bank3_permeate_tds_mgl": res["banks"][2], "bank4_permeate_tds_mgl": res["banks"][3]}

    def measure(self, true):
        out = {}
        for p in self.twin["telemetry"]["points"]:
            k = p["metric"]
            v = true[k]
            if p["noise"]:
                v = v + self.rng.gauss(0, p["noise"])
            lo, hi = p["range"]
            v = max(lo, min(hi, v))
            out[k] = round(v, 4 if abs(v) < 10 else 2)
        return out
