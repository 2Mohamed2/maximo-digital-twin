"""The chlorine contact tank twin's expectations (CL-5101, clearwell with sodium hypochlorite dosing).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Contact time (US EPA 815-R-20-003, chapter 4), at the level and flow of this reading:
    V = length x width x level         TDT = V / Q_out          T10 = BF x TDT
CT achieved (Eq. 4-1), with C the lower of the two outlet analysers (conservative):
    CT = C x T10   (mg.min/L)
CT required for 3-log Giardia by free chlorine (Appendix H, Smith et al. 1995 regression of the 1991 tables):
    T < 12.5 C:  CT99.9 = 0.353 x 3 x (12.006 + exp(2.46 - 0.073 T + 0.125 C + 0.389 pH))
    T >= 12.5 C: CT99.9 = 0.361 x 3 x (-2.261 + exp(2.69 - 0.065 T + 0.111 C + 0.361 pH))
    log Giardia achieved = 3 x CT / CT99.9 (Eq. 5-1);  CT ratio = log achieved / log required (>= 1 complies)
Viruses: log = 4 x CT / CT99.99, CT99.99 from Table B-2 (free chlorine, pH 6-9) interpolated on temperature.
Chemistry:
    HOCl fraction = 1 / (1 + 10^(pH - pKa)), pKa = 3000/T_K - 10.0686 + 0.0253 T_K (Morris 1966)
    hypochlorite strength now = S_delivered x exp(-k(T_tank) x age), k(T) = ln2/180 d x (180/48)^((T-25)/10)
    dose applied = pump flow (L/h) x strength (g/L) / water flow (m3/h)   -> g/m3 = mg/L
    immediate demand = dose applied - inlet residual;  decay = ln(inlet / outlet) / TDT (per hour, first order)
Dosing pump health: measured flow / flow-paced setpoint; trim = dose setpoint / design dose.
"""
import math


def _k(twin):
    d = twin["design"]
    cw, fl, ds, ct, ch, do, hy = d["clearwell"], d["flow"], d["disinfection"], d["ct"], d["chemistry"], d["dosing"], d["hypochlorite"]
    return dict(area=cw["length_m"] * cw["width_m"], bf=cw["baffling_factor"], lmin=cw["level_min_op_m"], lnorm=cw["level_normal_m"],
                lmax=cw["level_max_m"], qd=fl["design_m3h"], qp=fl["peak_m3h"],
                ig=ds["giardia_log_required"], iv=ds["virus_log_required"], target=ds["residual_target_mgl"],
                entry=ds["entry_min_mgl"], mrdl=ds["mrdl_mgl"], lt=ct["giardia_lt"], ge=ct["giardia_ge"], tsplit=ct["t_split_c"],
                vt=ct["virus_t_c"], vct=ct["virus_ct99_99"], pa=ch["pka_a"], pb=ch["pka_b"], pc=ch["pka_c"],
                dem0=ch["demand_immediate_mgl"], kb0=ch["decay_per_h"], dose0=do["dose_design_mgl"], spmax=do["dose_sp_max_mgl"],
                scfg=do["strength_config_gl"], pmax=do["pump_max_lh"], s0=hy["delivered_gl"],
                k25=math.log(2) / hy["half_life_25c_d"], fq=hy["half_life_25c_d"] / hy["half_life_35c_d"],
                tank_l=hy["tank_m3"] * 1000.0)


def ct99(k, temp, c, ph, logs=3.0):
    """CT (mg.min/L) for `logs` log Giardia inactivation by free chlorine (EPA Appendix H regression)."""
    g = k["lt"] if temp < k["tsplit"] else k["ge"]
    return g["a"] * logs * (g["b"] + math.exp(g["c0"] + g["ct"] * temp + g["cc"] * c + g["cph"] * ph))


def ct_virus(k, temp):
    """CT99.99 for viruses by free chlorine (Table B-2), linear in temperature, clamped like np.interp."""
    xs, ys = k["vt"], k["vct"]
    if temp <= xs[0]:
        return float(ys[0])
    if temp >= xs[-1]:
        return float(ys[-1])
    for i in range(len(xs) - 1):
        if xs[i] <= temp <= xs[i + 1]:
            return ys[i] + (ys[i + 1] - ys[i]) * (temp - xs[i]) / (xs[i + 1] - xs[i])


def pka(k, temp):
    tk = temp + 273.15
    return k["pa"] / tk + k["pb"] + k["pc"] * tk


def strength(k, s_del, t_tank, age):
    return s_del * math.exp(-k["k25"] * math.exp(math.log(k["fq"]) * (t_tank - 25.0) / 10.0) * age)


def _parts(twin):
    k = _k(twin)
    CMIN = "np.minimum(df['CL_OUT_A_MGL'], df['CL_OUT_B_MGL'])"
    V = f"({k['area']} * df['LEVEL_M'])"
    TDT = f"({V} / df['FLOW_OUT_M3H'] * 60)"
    T10 = f"({k['bf']} * {TDT})"
    CT = f"({CMIN} * {T10})"
    lt, ge = k["lt"], k["ge"]
    lo = f"{lt['a'] * 3:.6g} * ({lt['b']} + np.exp({lt['c0']} + {lt['ct']} * df['TEMP_C'] + {lt['cc']} * {CMIN} + {lt['cph']} * df['PH']))"
    hi = f"{ge['a'] * 3:.6g} * ({ge['b']} + np.exp({ge['c0']} + {ge['ct']} * df['TEMP_C'] + {ge['cc']} * {CMIN} + {ge['cph']} * df['PH']))"
    CT99 = f"np.where(df['TEMP_C'] < {k['tsplit']}, {lo}, {hi})"
    GLOG = f"(3 * {CT} / {CT99})"
    RATIO = f"({GLOG} / {k['ig']})"
    VCT = f"np.interp(df['TEMP_C'], {list(k['vt'])}, {list(k['vct'])})"
    TK = "(df['TEMP_C'] + 273.15)"
    PKA = f"({k['pa']} / {TK} + {k['pb']} + {k['pc']} * {TK})"
    S = (f"(df['HYPO_DELIVERED_GL'] * np.exp(-{k['k25']:.10g} * np.exp({math.log(k['fq']):.10g} * (df['HYPO_TEMP_C'] - 25.0) / 10.0)"
         f" * df['HYPO_AGE_D']))")
    DOSE = f"(df['PUMP_FLOW_LH'] * {S} / df['FLOW_IN_M3H'])"
    DEC = f"(np.log(np.maximum(df['CL_IN_MGL'], 0.01) / np.maximum({CMIN}, 0.01)) / ({TDT} / 60))"
    return dict(k=k, CMIN=CMIN, V=V, TDT=TDT, T10=T10, CT=CT, CT99=CT99, GLOG=GLOG, RATIO=RATIO, VCT=VCT, PKA=PKA, S=S, DOSE=DOSE, DEC=DEC)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("VOLUME_M3", p["V"]),
        ("TDT_MIN", p["TDT"]),
        ("T10_MIN", p["T10"]),
        ("CL_OUT_MIN_MGL", p["CMIN"]),
        ("CT_ACHIEVED", p["CT"]),
        ("CT99_9_GIARDIA", p["CT99"]),
        ("CT_REQUIRED", f"{p['CT99']} * {k['ig'] / 3:.10g}"),
        ("GIARDIA_LOG", p["GLOG"]),
        ("CT_RATIO", p["RATIO"]),
        ("VIRUS_LOG", f"4 * {p['CT']} / {p['VCT']}"),
        ("HOCL_FRACTION", f"1 / (1 + 10 ** (df['PH'] - {p['PKA']}))"),
        ("HYPO_STRENGTH_GL", p["S"]),
        ("DOSE_APPLIED_MGL", p["DOSE"]),
        ("CL_DEMAND_MGL", f"{p['DOSE']} - df['CL_IN_MGL']"),
        ("CL_DECAY_PER_H", p["DEC"]),
        ("PUMP_FLOW_RATIO", "df['PUMP_FLOW_LH'] / df['PUMP_SP_LH']"),
        ("TRIM_RATIO", f"df['DOSE_SP_MGL'] / {k['dose0']}"),
        ("ANALYSER_DIFF_MGL", "np.abs(df['CL_OUT_A_MGL'] - df['CL_OUT_B_MGL'])"),
        ("HYPO_DAYS_LEFT", f"df['HYPO_LEVEL_PCT'] / 100 * {k['tank_l']} / np.maximum(df['PUMP_FLOW_LH'] * 24, 0.1)"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    cmin = min(r["cl_out_a_mgl"], r["cl_out_b_mgl"])
    v = k["area"] * r["level_m"]
    tdt = v / r["flow_out_m3h"] * 60
    t10 = k["bf"] * tdt
    ct = cmin * t10
    c99 = ct99(k, r["temp_c"], cmin, r["ph"])
    glog = 3 * ct / c99
    s = strength(k, r["hypo_delivered_gl"], r["hypo_temp_c"], r["hypo_age_d"])
    dose = r["pump_flow_lh"] * s / r["flow_in_m3h"]
    return {
        "volume_m3": v, "tdt_min": tdt, "t10_min": t10, "cl_out_min_mgl": cmin, "ct_achieved": ct,
        "ct99_9_giardia": c99, "ct_required": c99 * (k["ig"] / 3), "giardia_log": glog, "ct_ratio": glog / k["ig"],
        "virus_log": 4 * ct / ct_virus(k, r["temp_c"]),
        "hocl_fraction": 1 / (1 + 10 ** (r["ph"] - pka(k, r["temp_c"]))),
        "hypo_strength_gl": s, "dose_applied_mgl": dose, "cl_demand_mgl": dose - r["cl_in_mgl"],
        "cl_decay_per_h": math.log(max(r["cl_in_mgl"], 0.01) / max(cmin, 0.01)) / (tdt / 60),
        "pump_flow_ratio": r["pump_flow_lh"] / r["pump_sp_lh"], "trim_ratio": r["dose_sp_mgl"] / k["dose0"],
        "analyser_diff_mgl": abs(r["cl_out_a_mgl"] - r["cl_out_b_mgl"]),
        "hypo_days_left": r["hypo_level_pct"] / 100 * k["tank_l"] / max(r["pump_flow_lh"] * 24, 0.1),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    R, C = p["RATIO"], p["CMIN"]
    return [
        ("CL_CT_FAIL", f"{R} < {L['ct_ratio_limit']}", "Critical", "cold_peak_drawdown"),
        ("CL_ENTRY_LOW", f"{C} < {k['entry']}", "Critical", "dose_pump_gas_lock"),
        ("CL_OUTLET_LOW", f"({C} >= {k['entry']}) & ({C} < {L['residual_low_mgl']})", "High", "analyser_drift"),
        ("CL_OUTLET_HIGH", f"np.maximum(df['CL_OUT_A_MGL'], df['CL_OUT_B_MGL']) > {k['mrdl']}", "High", None),
        ("DOSE_PUMP_DEVIATION", f"np.abs(df['PUMP_FLOW_LH'] / df['PUMP_SP_LH'] - 1) > {L['pump_dev_frac']}", "High", "dose_pump_gas_lock"),
        ("CL_CT_MARGIN_LOW", f"({R} >= {L['ct_ratio_limit']}) & ({R} < {L['ct_ratio_alert']})", "Medium", "cold_peak_drawdown"),
        ("CL_LEVEL_LOW", f"df['LEVEL_M'] < {L['level_low_m']}", "Medium", "cold_peak_drawdown"),
        ("CL_ANALYSER_MISMATCH", f"np.abs(df['CL_OUT_A_MGL'] - df['CL_OUT_B_MGL']) > {L['analyser_diff_mgl']}", "Medium", "analyser_drift"),
        ("HYPO_STRENGTH_LOW", f"{p['S']} < {L['hypo_strength_low_gl']}", "Medium", "hypo_strength_loss"),
        ("CL_DEMAND_HIGH", f"({p['DOSE']} - df['CL_IN_MGL']) > {L['demand_high_mgl']}", "Medium", "demand_rise"),
        ("CL_DECAY_HIGH", f"{p['DEC']} > {L['decay_high_per_h']}", "Medium", "clearwell_decay"),
        ("CL_TRIM_HIGH", f"df['DOSE_SP_MGL'] / {k['dose0']} > {L['trim_ratio_alert']}", "Medium", "hypo_strength_loss"),
        ("CL_PH_HIGH", f"df['PH'] > {L['ph_max']}", "Medium", "ph_high"),
        ("HYPO_STOCK_LOW", f"df['HYPO_LEVEL_PCT'] / 100 * {k['tank_l']} / np.maximum(df['PUMP_FLOW_LH'] * 24, 0.1) < {L['hypo_days_left_min']}", "Low", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    R, C = t["ct_ratio"], t["cl_out_min_mgl"]
    add(R < L["ct_ratio_limit"], "CL_CT_FAIL", "Critical",
        f"CT {t['ct_achieved']:.1f} mg·min/L, only {R:.2f} x the {t['ct_required']:.1f} required for {k['ig']}-log Giardia", "clearwell", "cold_peak_drawdown")
    add(C < k["entry"], "CL_ENTRY_LOW", "Critical", f"Residual to supply {C:.2f} mg/L, below {k['entry']} mg/L (40 CFR 141.72)", "outlet", "dose_pump_gas_lock")
    add(k["entry"] <= C < L["residual_low_mgl"], "CL_OUTLET_LOW", "High", f"Outlet residual {C:.2f} mg/L, target {k['target']:.1f}", "outlet", "analyser_drift")
    add(max(r["cl_out_a_mgl"], r["cl_out_b_mgl"]) > k["mrdl"], "CL_OUTLET_HIGH", "High",
        f"Outlet residual {max(r['cl_out_a_mgl'], r['cl_out_b_mgl']):.2f} mg/L above the MRDL {k['mrdl']}", "outlet")
    add(abs(t["pump_flow_ratio"] - 1) > L["pump_dev_frac"], "DOSE_PUMP_DEVIATION", "High",
        f"Pump delivers {r['pump_flow_lh']:.1f} L/h for a setpoint of {r['pump_sp_lh']:.1f} ({t['pump_flow_ratio'] * 100:.0f} %)", "dosing pump", "dose_pump_gas_lock")
    add(L["ct_ratio_limit"] <= R < L["ct_ratio_alert"], "CL_CT_MARGIN_LOW", "Medium", f"CT only {R:.2f} x required", "clearwell", "cold_peak_drawdown")
    add(r["level_m"] < L["level_low_m"], "CL_LEVEL_LOW", "Medium", f"Level {r['level_m']:.2f} m, below the {L['level_low_m']} m used in the CT design", "clearwell", "cold_peak_drawdown")
    add(t["analyser_diff_mgl"] > L["analyser_diff_mgl"], "CL_ANALYSER_MISMATCH", "Medium",
        f"Analysers disagree: A {r['cl_out_a_mgl']:.2f}, B {r['cl_out_b_mgl']:.2f} mg/L", "analyser", "analyser_drift")
    add(t["hypo_strength_gl"] < L["hypo_strength_low_gl"], "HYPO_STRENGTH_LOW", "Medium",
        f"Hypochlorite about {t['hypo_strength_gl']:.0f} g/L ({r['hypo_age_d']:.0f} d at {r['hypo_temp_c']:.0f} °C)", "hypochlorite tank", "hypo_strength_loss")
    add(t["cl_demand_mgl"] > L["demand_high_mgl"], "CL_DEMAND_HIGH", "Medium", f"Immediate chlorine demand {t['cl_demand_mgl']:.2f} mg/L", "water quality", "demand_rise")
    add(t["cl_decay_per_h"] > L["decay_high_per_h"], "CL_DECAY_HIGH", "Medium", f"Decay in the clearwell {t['cl_decay_per_h']:.3f} per hour", "clearwell", "clearwell_decay")
    add(t["trim_ratio"] > L["trim_ratio_alert"], "CL_TRIM_HIGH", "Medium",
        f"Dose setpoint {r['dose_sp_mgl']:.2f} mg/L, {t['trim_ratio']:.2f} x design", "dosing loop", "hypo_strength_loss")
    add(r["ph"] > L["ph_max"], "CL_PH_HIGH", "Medium", f"pH {r['ph']:.2f}: only {t['hocl_fraction'] * 100:.0f} % of the chlorine is HOCl", "water quality", "ph_high")
    add(t["hypo_days_left"] < L["hypo_days_left_min"], "HYPO_STOCK_LOW", "Low", f"Hypochlorite for {t['hypo_days_left']:.1f} days", "hypochlorite tank")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
