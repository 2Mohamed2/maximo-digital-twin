"""The HTST milk pasteurizer twin's expectations (PS-6801, plate heat exchanger with regeneration, holding tube, FDD).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Milk heat capacity flow: C = Q / 3600 x rho x cp (kW/K, Q in l/h).
Holding (Tetra Pak Dairy Processing Handbook): V = Q x HT / (3600 x eta), so the time of the fastest particle is
    HT = 3600 x eta x V / Q            (eta = holding tube efficiency, 0.85 in turbulent flow)
    legal: HT >= 15 s and the temperature at the end of the tube >= 72 °C (PMO 72 °C / 161 °F, EU 853/2004 72 °C)
    the lower of the recorder-controller (STLR) and the indicating thermometer is used; the STLR must not read higher.
Regeneration (handbook): R = (t_r - t_i) / (t_p - t_i) x 100, with t_p the milk entering the regenerator hot side
(the end of the holding tube). Both streams are the same milk, so the section is a balanced counterflow exchanger:
    eps = NTU / (1 + NTU), NTU = U A / C, approach = t_p - t_r = (1 - eps) (t_p - t_i)
    expected: U_clean x (Q/Q0)^0.6, so NTU_clean = U_clean(Q) A / C(Q); U ratio = NTU_actual / NTU_clean
    with NTU_actual = eps / (1 - eps) from the three temperatures.
Heating section (hot water, counterflow): Q_h = C (t_heat_out - t_r); LMTD from hot water in/out and milk in/out;
    U_actual = Q_h / (A LMTD); U_clean x (Q/Q0)^0.35. Fouling (denatured whey protein on the hot plates) lowers U and,
    because the controller holds the milk outlet at the set point, raises the hot water temperature: the approach grows.
Pressure drop ratio: dP / (dP_clean x (Q/Q0)^1.8). CIP effectiveness: the same ratio taken at the start of the run.
Leak protection (PMO): pasteurized pressure - raw pressure in the regenerator >= 6.9 kPa (0.069 bar).
Energy: steam = Q_h / (h_fg x eta_hw); per m3 = steam / (Q/1000); energy per litre = (Q_h + Q_cool) x 3600 / Q.
"""
import math


def _k(twin):
    d = twin["design"]
    p, lg, ht, rg, he, pr, en, cp = (d["process"], d["legal"], d["holding_tube"], d["regenerator"], d["heater"], d["pressures"],
                                     d["energy"], d["cip"])
    k = dict(q0=p["rated_flow_l_h"], kc=p["milk_density_kg_l"] * p["milk_cp_kj_kgk"] / 3600, tmin=lg["min_temp_c"],
             hmin=lg["min_hold_s"], dpmin=lg["pressure_diff_min_bar"], ht=3600 * ht["efficiency"] * ht["volume_l"],
             ur=rg["u_clean_w_m2k"], ar=rg["area_m2"], er=rg["flow_exp"], dpr0=rg["dp_clean_bar"],
             uh=he["u_clean_w_m2k"], ah=he["area_m2"], eh=he["flow_exp"], dph0=he["dp_clean_bar"],
             pmargin=pr["margin_alert_bar"], hfg=en["h_fg_kj_kg"], eff=en["hot_water_unit_eff"], ealert=en["energy_alert_ratio"],
             runlen=cp["run_length_h"], recov=cp["recovery_alert_ratio"])
    # design steam per m3 at the rated flow, clean regenerator, set point and design inlet temperature
    c0 = k["kc"] * k["q0"]
    ntu = k["ur"] * k["ar"] / (c0 * 1000)
    eps = ntu / (1 + ntu)
    t_hold = p["pasteurization_setpoint_c"] - ht["heat_loss_k"]
    duty = c0 * (p["pasteurization_setpoint_c"] - (p["raw_in_c"] + eps * (t_hold - p["raw_in_c"])))
    k["steam_m3_design"] = round(duty * 3600 / (k["hfg"] * k["eff"]) / (k["q0"] / 1000), 4)
    return k


# ---- plain-Python building blocks (also used by physics.py and the figures) ----------------------------------------------
def regen_eps(k, q, x=0.0):
    """Regeneration effectiveness at flow q (l/h) with fouling x = U_clean x Rf (0 = clean)."""
    ntu = k["ur"] * (q / k["q0"]) ** k["er"] / (1 + x) * k["ar"] / (k["kc"] * q * 1000)
    return ntu / (1 + ntu)


def hold_time(k, q):
    return k["ht"] / q


def lmtd(d1, d2):
    d1, d2 = max(d1, 0.05), max(d2, 0.05)
    return d1 if abs(d1 - d2) < 1e-9 else (d1 - d2) / math.log(d1 / d2)


# ---- Monitor expressions ----------------------------------------------------------------------------------------------
def _parts(twin):
    k = _k(twin)
    FL = "df['FLOW_L_H']"
    RAW, RRO, HO, HR = "df['RAW_IN_C']", "df['REGEN_RAW_OUT_C']", "df['HEAT_OUT_C']", "df['HOLD_REF_C']"
    C = f"({k['kc']:.9g} * {FL})"
    HOLD = f"({k['ht']:.9g} / {FL})"
    TMIN = f"np.minimum(df['HOLD_OUT_C'], {HR})"
    EPS = f"(({RRO} - {RAW}) / ({HR} - {RAW}))"
    NTUC = f"({k['ur']} * ({FL} / {k['q0']}) ** {k['er']} * {k['ar']} / ({C} * 1000))"
    NTUA = f"(np.minimum({EPS}, 0.999) / (1 - np.minimum({EPS}, 0.999)))"
    DUTY = f"({C} * ({HO} - {RRO}))"
    D1 = f"np.maximum(df['HW_IN_C'] - {HO}, 0.05)"
    D2 = f"np.maximum(df['HW_OUT_C'] - {RRO}, 0.05)"
    LM = f"np.where(np.abs({D1} - {D2}) < 1e-9, {D1}, ({D1} - {D2}) / np.log({D1} / {D2}))"
    UHR = f"(({DUTY} * 1000 / ({k['ah']} * {LM})) / ({k['uh']} * ({FL} / {k['q0']}) ** {k['eh']}))"
    DPH = f"(df['DP_HEATER_BAR'] / ({k['dph0']} * ({FL} / {k['q0']}) ** 1.8))"
    DPR = f"(df['DP_REGEN_BAR'] / ({k['dpr0']} * ({FL} / {k['q0']}) ** 1.8))"
    PD = "(df['P_PAST_REGEN_OUT_BAR'] - df['P_RAW_REGEN_IN_BAR'])"
    REC = f"(df['RUN_START_DP_HEATER_BAR'] / ({k['dph0']} * (df['RUN_START_FLOW_L_H'] / {k['q0']}) ** 1.8))"
    STEAM = f"({DUTY} * 3600 / ({k['hfg']} * {k['eff']}))"
    SPM = f"(df['STEAM_KG_H'] / ({FL} / 1000))"
    COOL = f"({C} * (df['REGEN_PAST_OUT_C'] - df['PRODUCT_OUT_C']))"
    return dict(k=k, FL=FL, C=C, HOLD=HOLD, TMIN=TMIN, EPS=EPS, NTUC=NTUC, NTUA=NTUA, DUTY=DUTY, LM=LM, UHR=UHR, DPH=DPH, DPR=DPR,
                PD=PD, REC=REC, STEAM=STEAM, SPM=SPM, COOL=COOL, RRO=RRO, HR=HR, HO=HO)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("HOLD_TIME_S", p["HOLD"]),
        ("HOLD_TIME_MARGIN_S", f"{p['HOLD']} - {k['hmin']}"),
        ("HOLD_TEMP_MARGIN_K", f"{p['TMIN']} - {k['tmin']}"),
        ("HOLD_TUBE_LOSS_K", f"{p['HO']} - {p['HR']}"),
        ("STLR_OFFSET_K", f"df['HOLD_OUT_C'] - {p['HR']}"),
        ("REGEN_EFF_PCT", f"{p['EPS']} * 100"),
        ("REGEN_EFF_EXPECTED_PCT", f"{p['NTUC']} / (1 + {p['NTUC']}) * 100"),
        ("REGEN_APPROACH_K", f"{p['HR']} - {p['RRO']}"),
        ("U_REGEN_RATIO", f"{p['NTUA']} / {p['NTUC']}"),
        ("HEATER_DUTY_KW", p["DUTY"]),
        ("HEATER_APPROACH_K", f"df['HW_IN_C'] - {p['HO']}"),
        ("U_HEATER_RATIO", p["UHR"]),
        ("DP_HEATER_RATIO", p["DPH"]),
        ("DP_REGEN_RATIO", p["DPR"]),
        ("PRESSURE_DIFF_BAR", p["PD"]),
        ("CIP_DP_RECOVERY", p["REC"]),
        ("STEAM_EXPECTED_KG_H", p["STEAM"]),
        ("STEAM_PER_M3_KG", p["SPM"]),
        ("ENERGY_KJ_PER_L", f"({p['DUTY']} + {p['COOL']}) * 3600 / {p['FL']}"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    q = r["flow_l_h"]
    c = k["kc"] * q
    hold = k["ht"] / q
    eps = (r["regen_raw_out_c"] - r["raw_in_c"]) / (r["hold_ref_c"] - r["raw_in_c"])
    ntuc = k["ur"] * (q / k["q0"]) ** k["er"] * k["ar"] / (c * 1000)
    e = min(eps, 0.999)
    ntua = e / (1 - e)
    duty = c * (r["heat_out_c"] - r["regen_raw_out_c"])
    lm = lmtd(r["hw_in_c"] - r["heat_out_c"], r["hw_out_c"] - r["regen_raw_out_c"])
    uhr = (duty * 1000 / (k["ah"] * lm)) / (k["uh"] * (q / k["q0"]) ** k["eh"])
    cool = c * (r["regen_past_out_c"] - r["product_out_c"])
    return {
        "hold_time_s": hold, "hold_time_margin_s": hold - k["hmin"],
        "hold_temp_margin_k": min(r["hold_out_c"], r["hold_ref_c"]) - k["tmin"],
        "hold_tube_loss_k": r["heat_out_c"] - r["hold_ref_c"], "stlr_offset_k": r["hold_out_c"] - r["hold_ref_c"],
        "regen_eff_pct": eps * 100, "regen_eff_expected_pct": ntuc / (1 + ntuc) * 100,
        "regen_approach_k": r["hold_ref_c"] - r["regen_raw_out_c"], "u_regen_ratio": ntua / ntuc,
        "heater_duty_kw": duty, "heater_approach_k": r["hw_in_c"] - r["heat_out_c"], "u_heater_ratio": uhr,
        "dp_heater_ratio": r["dp_heater_bar"] / (k["dph0"] * (q / k["q0"]) ** 1.8),
        "dp_regen_ratio": r["dp_regen_bar"] / (k["dpr0"] * (q / k["q0"]) ** 1.8),
        "pressure_diff_bar": r["p_past_regen_out_bar"] - r["p_raw_regen_in_bar"],
        "cip_dp_recovery": r["run_start_dp_heater_bar"] / (k["dph0"] * (r["run_start_flow_l_h"] / k["q0"]) ** 1.8),
        "steam_expected_kg_h": duty * 3600 / (k["hfg"] * k["eff"]),
        "steam_per_m3_kg": r["steam_kg_h"] / (q / 1000),
        "energy_kj_per_l": (duty + cool) * 3600 / q,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    FWD = "(df['FDD_FORWARD'] > 0.5)"
    MARG = f"({p['TMIN']} - {k['tmin']})"
    return [
        ("PAST_UNDERTEMP_FORWARD", f"({p['TMIN']} < {k['tmin']}) & {FWD}", "Critical", None),
        ("PAST_HOLD_TIME_SHORT", f"({p['HOLD']} < {k['hmin']}) & {FWD}", "Critical", "flow_timing_drift"),
        ("PAST_PRESSURE_DIFF_LOW", f"{p['PD']} < {k['dpmin']}", "Critical", "pressure_diff_loss"),
        ("PAST_DIVERT_FREQUENT", f"df['FDD_DIVERTS_1H'] >= {L['diverts_alert_1h']}", "High", "heating_unstable"),
        ("PAST_STLR_MISMATCH", f"(df['HOLD_OUT_C'] - {p['HR']}) > {L['stlr_offset_alert_k']}", "High", "stlr_drift"),
        ("PAST_RUN_OVERDUE", f"df['HOURS_SINCE_CIP'] > {k['runlen']}", "High", "cip_skipped"),
        ("PAST_HOLD_MARGIN_LOW", f"({p['HOLD']} >= {k['hmin']}) & ({p['HOLD']} < {k['hmin'] + L['hold_margin_alert_s']})", "Medium", "flow_timing_drift"),
        ("PAST_TEMP_MARGIN_LOW", f"({MARG} >= 0) & ({MARG} < {L['temp_margin_alert_k']})", "Medium", "heating_unstable"),
        ("PAST_PRESSURE_MARGIN_LOW", f"({p['PD']} >= {k['dpmin']}) & ({p['PD']} < {k['pmargin']})", "Medium", "pressure_diff_loss"),
        ("PAST_HEATER_FOULING", f"{p['UHR']} < {L['u_heater_ratio_alert']}", "Medium", "heater_fouling"),
        ("PAST_HEATER_DP_HIGH", f"{p['DPH']} > {L['dp_ratio_alert']}", "Medium", "heater_fouling"),
        ("PAST_REGEN_EFF_LOW", f"({p['EPS']} * 100) < ({p['NTUC']} / (1 + {p['NTUC']}) * 100 - {L['regen_eff_drop_alert_pct']})", "Medium", "regen_fouling"),
        ("PAST_REGEN_DP_HIGH", f"{p['DPR']} > {L['dp_ratio_alert']}", "Medium", "regen_fouling"),
        ("PAST_CIP_INEFFECTIVE", f"{p['REC']} > {k['recov']}", "Medium", "cip_incomplete"),
        ("PAST_ENERGY_HIGH", f"{p['SPM']} > {k['ealert'] * k['steam_m3_design']!r}", "Low", "regen_fouling"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    fwd = r["fdd_forward"] > 0.5
    hold, marg, pd = t["hold_time_s"], t["hold_temp_margin_k"], t["pressure_diff_bar"]
    tmin = min(r["hold_out_c"], r["hold_ref_c"])
    add(tmin < k["tmin"] and fwd, "PAST_UNDERTEMP_FORWARD", "Critical",
        f"Holding tube outlet {tmin:.2f} °C, below {k['tmin']:.0f} °C, with the FDD in forward flow: under-pasteurized milk forward", "holding tube")
    add(hold < k["hmin"] and fwd, "PAST_HOLD_TIME_SHORT", "Critical",
        f"Fastest particle held {hold:.2f} s at {r['flow_l_h']:.0f} l/h, below the {k['hmin']:.0f} s minimum", "timing", "flow_timing_drift")
    add(pd < k["dpmin"], "PAST_PRESSURE_DIFF_LOW", "Critical",
        f"Pasteurized side only {pd * 100:.1f} kPa above the raw side (minimum 6.9 kPa): a plate leak would carry raw milk into pasteurized milk",
        "regenerator", "pressure_diff_loss")
    add(r["fdd_diverts_1h"] >= L["diverts_alert_1h"], "PAST_DIVERT_FREQUENT", "High",
        f"{r['fdd_diverts_1h']:.0f} diverts in the last hour", "fdd", "heating_unstable")
    add(t["stlr_offset_k"] > L["stlr_offset_alert_k"], "PAST_STLR_MISMATCH", "High",
        f"Recorder-controller reads {t['stlr_offset_k']:.2f} K above the indicating thermometer: it must not read higher", "holding tube", "stlr_drift")
    add(r["hours_since_cip"] > k["runlen"], "PAST_RUN_OVERDUE", "High",
        f"{r['hours_since_cip']:.1f} h since the last CIP, beyond the validated {k['runlen']:.0f} h run", "cip", "cip_skipped")
    add(k["hmin"] <= hold < k["hmin"] + L["hold_margin_alert_s"], "PAST_HOLD_MARGIN_LOW", "Medium",
        f"Fastest particle held {hold:.2f} s: less than {L['hold_margin_alert_s']} s above the minimum", "timing", "flow_timing_drift")
    add(0 <= marg < L["temp_margin_alert_k"], "PAST_TEMP_MARGIN_LOW", "Medium",
        f"Holding tube outlet only {marg:.2f} K above {k['tmin']:.0f} °C", "hot water unit", "heating_unstable")
    add(k["dpmin"] <= pd < k["pmargin"], "PAST_PRESSURE_MARGIN_LOW", "Medium",
        f"Regenerator pressure differential {pd:.2f} bar, below the {k['pmargin']} bar early-warning margin", "regenerator", "pressure_diff_loss")
    add(t["u_heater_ratio"] < L["u_heater_ratio_alert"], "PAST_HEATER_FOULING", "Medium",
        f"Heating section U at {t['u_heater_ratio'] * 100:.0f} % of clean; hot water {t['heater_approach_k']:.1f} K above the milk", "heater", "heater_fouling")
    add(t["dp_heater_ratio"] > L["dp_ratio_alert"], "PAST_HEATER_DP_HIGH", "Medium",
        f"Heating section pressure drop {t['dp_heater_ratio']:.2f} × clean at this flow", "heater", "heater_fouling")
    add(t["regen_eff_pct"] < t["regen_eff_expected_pct"] - L["regen_eff_drop_alert_pct"], "PAST_REGEN_EFF_LOW", "Medium",
        f"Regeneration {t['regen_eff_pct']:.1f} % against {t['regen_eff_expected_pct']:.1f} % expected clean", "regenerator", "regen_fouling")
    add(t["dp_regen_ratio"] > L["dp_ratio_alert"], "PAST_REGEN_DP_HIGH", "Medium",
        f"Regenerator raw-side pressure drop {t['dp_regen_ratio']:.2f} × clean at this flow", "regenerator", "regen_fouling")
    add(t["cip_dp_recovery"] > k["recov"], "PAST_CIP_INEFFECTIVE", "Medium",
        f"Run started at {t['cip_dp_recovery']:.2f} × the clean pressure drop (lye return {r['cip_lye_return_c']:.0f} °C): the CIP left deposit",
        "cip", "cip_incomplete")
    add(t["steam_per_m3_kg"] > k["ealert"] * k["steam_m3_design"], "PAST_ENERGY_HIGH", "Low",
        f"Steam {t['steam_per_m3_kg']:.1f} kg per m³ of milk against {k['steam_m3_design']:.1f} by design", "energy", "regen_fouling")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
