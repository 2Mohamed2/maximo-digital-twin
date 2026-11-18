"""The district heating substation twin's expectations (DH-7101: Danfoss Termix VVX-I, Kamstrup MULTICAL 403).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

k = rho * cp / 3600 = 1.15 kWh/(m3 K) for water (the heat coefficient).

Heating circuit and weather curve:
    curve      = clip(tr + (Ts,d - tr) * (tr - t_out) / (tr - t_out,d), Ts,min, Ts,max)     (the twin's heat curve)
    Q_sh       = k * V_sec * (T_flow - T_ret,sec)                                              (heat into the building)
    return ref = tr + (curve - tr) * (Tr,d - tr) / (Ts,d - tr) + (Tpr,d - Tr,d)
  The return reference is the primary return a clean, balanced substation gives at this outdoor temperature: the design
  secondary return scaled along the curve, plus the design approach of the exchanger.
    return excess = T2 (meter) - return ref                cooling = T1 - T2
    cost of the excess = max(excess, 0) * annual MWh * EUR per MWh and K

Heating exchanger (counterflow):
    LMTD = (dT1 - dT2) / ln(dT1 / dT2),  dT1 = Tp,in - T_flow,  dT2 = Tp,out,sh - T_ret,sec
    UA measured = Q_sh / LMTD
    primary flow of the heating exchanger = V_sec * (T_flow - T_ret,sec) / (Tp,in - Tp,out,sh)   (heat balance)
    UA expected = UA_d / (s * (Vp,d / Vp)^n + (1 - s) * (Vs,d / Vs)^n)       (film resistances scale with flow^-n)
    UA ratio = UA measured / UA expected: below 1 = fouling (an extra resistance in series)

Valve: live authority = dp of the fully open valve at design flow / dp measured across valve and exchanger.
Heat meter (EN 1434-1, class 2): the meter's power is checked against k * meter flow * (controller supply - controller
return); the error must stay inside MPE = Ef + Et + Ec with
    Ef = min(2 + 0.02 qp / q, 5),  Et = 0.5 + 3 dTmin / dT,  Ec = 0.5 + dTmin / dT        (in %)
"""
import math


def _k(twin):
    d = twin["design"]
    h, w, c, v, m, e = d["heating"], d["dhw"], d["curve"], d["valve"], d["meter"], d["economics"]
    return dict(k=m["k_kwh_m3k"], tr=c["room_c"], tod=c["outdoor_design_c"], smax=c["supply_max_c"], smin=c["supply_min_c"],
                tsd=h["secondary_supply_c"], trd=h["secondary_return_c"], tprd=h["primary_return_c"], q=h["q_kw"],
                ua=h["ua_kw_k"], mpd=h["primary_flow_m3h"], msd=h["secondary_flow_m3h"], n=h["ua_flow_exponent"], s=h["film_split"],
                dpv=v["dpv100_kpa"], qp=m["qp_m3h"], dtm=m["dtheta_min_k"], dhw_min=w["min_supply_c"], circ_min=w["min_circulation_c"],
                tap=w["tap_threshold_lpm"], mwh=e["annual_heat_mwh"], eur=e["operator_cost_eur_per_mwh_k"])


def curve(k, t_out):
    x = k["tr"] + (k["tsd"] - k["tr"]) * (k["tr"] - t_out) / (k["tr"] - k["tod"])
    return min(max(x, k["smin"]), k["smax"])


def _parts(twin):
    k = _k(twin)
    K = k["k"]
    CURVE = f"np.clip({k['tr']} + {(k['tsd'] - k['tr']) / (k['tr'] - k['tod']):.6g} * ({k['tr']} - df['OUTDOOR_C']), {k['smin']}, {k['smax']})"
    DTS = "(df['SH_FLOW_C'] - df['SH_RETURN_C'])"
    QSH = f"({K} * df['SH_PUMP_FLOW_M3H'] * {DTS})"
    D1 = "np.maximum(df['P_SUPPLY_C'] - df['SH_FLOW_C'], 0.1)"
    D2 = "np.maximum(df['SH_P_RETURN_C'] - df['SH_RETURN_C'], 0.1)"
    LMTD = f"np.where(np.abs({D1} - {D2}) < 1e-6, {D1}, ({D1} - {D2}) / np.log({D1} / {D2}))"
    MP = f"(df['SH_PUMP_FLOW_M3H'] * {DTS} / np.maximum(df['P_SUPPLY_C'] - df['SH_P_RETURN_C'], 0.5))"
    UAE = (f"({k['ua']} / ({k['s']} * ({k['mpd']} / np.maximum({MP}, 0.01)) ** {k['n']}"
           f" + {1 - k['s']:.6g} * ({k['msd']} / np.maximum(df['SH_PUMP_FLOW_M3H'], 0.01)) ** {k['n']}))")
    UAM = f"({QSH} / {LMTD})"
    REF = f"({k['tr']} + ({CURVE} - {k['tr']}) * {(k['trd'] - k['tr']) / (k['tsd'] - k['tr']):.6g} + {k['tprd'] - k['trd']})"
    EXC = f"(df['HM_T_RETURN_C'] - {REF})"
    DTC = "np.maximum(df['P_SUPPLY_C'] - df['P_RETURN_C'], 0.1)"
    MERR = f"((df['HM_POWER_KW'] / ({K} * np.maximum(df['HM_FLOW_M3H'], 0.001) * {DTC}) - 1) * 100)"
    MPE = (f"(np.minimum(2 + {0.02 * k['qp']:.6g} / np.maximum(df['HM_FLOW_M3H'], 0.001), 5) + 0.5 + {3 * k['dtm']:.6g} / {DTC}"
           f" + 0.5 + {k['dtm']:.6g} / {DTC})")
    return dict(k=k, CURVE=CURVE, QSH=QSH, LMTD=LMTD, MP=MP, UAE=UAE, UAM=UAM, REF=REF, EXC=EXC, MERR=MERR, MPE=MPE)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("SH_POWER_KW", p["QSH"]),
        ("HEAT_CURVE_C", p["CURVE"]),
        ("CURVE_OFFSET_K", f"df['SH_FLOW_SET_C'] - {p['CURVE']}"),
        ("SUPPLY_SHORTFALL_K", "df['SH_FLOW_SET_C'] - df['SH_FLOW_C']"),
        ("SEC_FLOW_RATIO", f"df['SH_PUMP_FLOW_M3H'] / {k['msd']}"),
        ("SH_APPROACH_K", "df['SH_P_RETURN_C'] - df['SH_RETURN_C']"),
        ("LMTD_K", p["LMTD"]),
        ("UA_MEASURED_KW_K", p["UAM"]),
        ("PRIMARY_FLOW_SH_M3H", p["MP"]),
        ("UA_EXPECTED_KW_K", p["UAE"]),
        ("UA_RATIO", f"{p['UAM']} / {p['UAE']}"),
        ("RETURN_REF_C", p["REF"]),
        ("RETURN_EXCESS_K", p["EXC"]),
        ("COOLING_K", "df['HM_T_SUPPLY_C'] - df['HM_T_RETURN_C']"),
        ("RETURN_COST_EUR_Y", f"np.maximum({p['EXC']}, 0) * {k['mwh'] * k['eur']:.6g}"),
        ("BYPASS_MIX_K", "df['HM_T_RETURN_C'] - df['SH_P_RETURN_C']"),
        ("METER_ERROR_PCT", p["MERR"]),
        ("METER_MPE_PCT", p["MPE"]),
        ("VALVE_AUTHORITY", f"{k['dpv']} / np.maximum(df['DP_SECTION_KPA'], 1)"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    K = k["k"]
    cv = curve(k, r["outdoor_c"])
    dts = r["sh_flow_c"] - r["sh_return_c"]
    qsh = K * r["sh_pump_flow_m3h"] * dts
    d1 = max(r["p_supply_c"] - r["sh_flow_c"], 0.1)
    d2 = max(r["sh_p_return_c"] - r["sh_return_c"], 0.1)
    lmtd = d1 if abs(d1 - d2) < 1e-6 else (d1 - d2) / math.log(d1 / d2)
    mp = r["sh_pump_flow_m3h"] * dts / max(r["p_supply_c"] - r["sh_p_return_c"], 0.5)
    uae = k["ua"] / (k["s"] * (k["mpd"] / max(mp, 0.01)) ** k["n"] + (1 - k["s"]) * (k["msd"] / max(r["sh_pump_flow_m3h"], 0.01)) ** k["n"])
    uam = qsh / lmtd
    ref = k["tr"] + (cv - k["tr"]) * (k["trd"] - k["tr"]) / (k["tsd"] - k["tr"]) + (k["tprd"] - k["trd"])
    exc = r["hm_t_return_c"] - ref
    dtc = max(r["p_supply_c"] - r["p_return_c"], 0.1)
    q = max(r["hm_flow_m3h"], 0.001)
    merr = (r["hm_power_kw"] / (K * q * dtc) - 1) * 100
    mpe = min(2 + 0.02 * k["qp"] / q, 5) + 0.5 + 3 * k["dtm"] / dtc + 0.5 + k["dtm"] / dtc
    return {
        "sh_power_kw": qsh, "heat_curve_c": cv, "curve_offset_k": r["sh_flow_set_c"] - cv,
        "supply_shortfall_k": r["sh_flow_set_c"] - r["sh_flow_c"], "sec_flow_ratio": r["sh_pump_flow_m3h"] / k["msd"],
        "sh_approach_k": r["sh_p_return_c"] - r["sh_return_c"], "lmtd_k": lmtd, "ua_measured_kw_k": uam,
        "primary_flow_sh_m3h": mp, "ua_expected_kw_k": uae, "ua_ratio": uam / uae, "return_ref_c": ref, "return_excess_k": exc,
        "cooling_k": r["hm_t_supply_c"] - r["hm_t_return_c"], "return_cost_eur_y": max(exc, 0) * k["mwh"] * k["eur"],
        "bypass_mix_k": r["hm_t_return_c"] - r["sh_p_return_c"], "meter_error_pct": merr, "meter_mpe_pct": mpe,
        "valve_authority": k["dpv"] / max(r["dp_section_kpa"], 1),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    MERR, MPE = p["MERR"], p["MPE"]
    return [
        ("DH_DHW_CIRC_LOW", f"df['DHW_CIRC_RETURN_C'] < {k['circ_min']}", "High", "dhw_circulation_fault"),
        ("DH_DHW_TEMP_LOW", f"df['DHW_C'] < {k['dhw_min']}", "High", "dhw_setpoint_low"),
        ("DH_METER_ERROR", f"np.abs({MERR}) > {MPE}", "High", "meter_sensor_fault"),
        ("DH_PRIMARY_BYPASS", f"(df['DHW_FLOW_LPM'] < {k['tap']}) & ((df['HM_T_RETURN_C'] - df['SH_P_RETURN_C']) > {L['bypass_mix_alert_k']})", "High", "primary_bypass"),
        ("DH_SUPPLY_LOW", f"(df['SH_FLOW_SET_C'] - df['SH_FLOW_C']) > {L['supply_shortfall_alert_k']}", "High", None),
        ("DH_RETURN_HIGH", f"{p['EXC']} > {L['return_excess_alert_k']}", "Medium", "secondary_overflow"),
        ("DH_UA_LOW", f"({p['QSH']} > {L['ua_min_load'] * k['q']:.6g}) & (({p['UAM']} / {p['UAE']}) < {L['ua_ratio_alert']})", "Medium", "hex_fouling"),
        ("DH_SEC_FLOW_HIGH", f"(df['SH_PUMP_FLOW_M3H'] / {k['msd']}) > {L['sec_flow_ratio_alert']}", "Medium", "secondary_overflow"),
        ("DH_CURVE_HIGH", f"(df['SH_FLOW_SET_C'] - {p['CURVE']}) > {L['curve_offset_alert_k']}", "Medium", "curve_too_high"),
        ("DH_METER_TEMP_MISMATCH", f"(np.abs(df['HM_T_SUPPLY_C'] - df['P_SUPPLY_C']) > {L['meter_temp_dev_alert_k']})"
                                   f" | (np.abs(df['HM_T_RETURN_C'] - df['P_RETURN_C']) > {L['meter_temp_dev_alert_k']})", "Medium", "meter_sensor_fault"),
        ("DH_AUTHORITY_LOW", f"({k['dpv']} / np.maximum(df['DP_SECTION_KPA'], 1)) < {L['authority_alert']}", "Medium", "dp_controller_fault"),
        ("DH_VALVE_HUNTING", f"(df['VALVE_REVERSALS_H'] > {L['hunting_reversals_alert_h']}) & (df['SH_FLOW_RMS_K'] > {L['hunting_rms_alert_k']})", "Medium", "dp_controller_fault"),
        ("DH_METER_INFO", "df['HM_INFO_CODE'] > 0.5", "Low", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    add(r["dhw_circ_return_c"] < k["circ_min"], "DH_DHW_CIRC_LOW", "High",
        f"DHW circulation returns at {r['dhw_circ_return_c']:.1f} °C, below {k['circ_min']:.0f} °C: legionella risk in the loop", "DHW circulation", "dhw_circulation_fault")
    add(r["dhw_c"] < k["dhw_min"], "DH_DHW_TEMP_LOW", "High",
        f"Hot water leaves the heater at {r['dhw_c']:.1f} °C, below {k['dhw_min']:.0f} °C", "DHW controller", "dhw_setpoint_low")
    add(abs(t["meter_error_pct"]) > t["meter_mpe_pct"], "DH_METER_ERROR", "High",
        f"Heat meter reads {t['meter_error_pct']:+.1f} % against the controller sensors, outside the class 2 MPE of {t['meter_mpe_pct']:.1f} %", "heat meter", "meter_sensor_fault")
    add(r["dhw_flow_lpm"] < k["tap"] and t["bypass_mix_k"] > L["bypass_mix_alert_k"], "DH_PRIMARY_BYPASS", "High",
        f"Common return {t['bypass_mix_k']:.1f} K above the heating exchanger return with no tapping: hot water bypasses", "primary pipework", "primary_bypass")
    add(t["supply_shortfall_k"] > L["supply_shortfall_alert_k"], "DH_SUPPLY_LOW", "High",
        f"Heating flow {t['supply_shortfall_k']:.1f} K below its setpoint: the substation cannot deliver", "heating exchanger")
    add(t["return_excess_k"] > L["return_excess_alert_k"], "DH_RETURN_HIGH", "Medium",
        f"Primary return {r['hm_t_return_c']:.1f} °C, {t['return_excess_k']:.1f} K above the reference {t['return_ref_c']:.1f} °C", "substation", "secondary_overflow")
    add(t["sh_power_kw"] > L["ua_min_load"] * k["q"] and t["ua_ratio"] < L["ua_ratio_alert"], "DH_UA_LOW", "Medium",
        f"Heating exchanger UA {t['ua_measured_kw_k']:.2f} kW/K, {t['ua_ratio']:.2f} × expected", "heating exchanger", "hex_fouling")
    add(t["sec_flow_ratio"] > L["sec_flow_ratio_alert"], "DH_SEC_FLOW_HIGH", "Medium",
        f"Heating circuit flow {r['sh_pump_flow_m3h']:.2f} m³/h, {t['sec_flow_ratio']:.2f} × design", "heating circuit", "secondary_overflow")
    add(t["curve_offset_k"] > L["curve_offset_alert_k"], "DH_CURVE_HIGH", "Medium",
        f"Flow setpoint {r['sh_flow_set_c']:.1f} °C, {t['curve_offset_k']:.1f} K above the heat curve", "controller", "curve_too_high")
    add(abs(r["hm_t_supply_c"] - r["p_supply_c"]) > L["meter_temp_dev_alert_k"] or abs(r["hm_t_return_c"] - r["p_return_c"]) > L["meter_temp_dev_alert_k"],
        "DH_METER_TEMP_MISMATCH", "Medium",
        f"Meter T1/T2 {r['hm_t_supply_c']:.1f}/{r['hm_t_return_c']:.1f} °C against controller {r['p_supply_c']:.1f}/{r['p_return_c']:.1f} °C", "heat meter", "meter_sensor_fault")
    add(t["valve_authority"] < L["authority_alert"], "DH_AUTHORITY_LOW", "Medium",
        f"Valve authority {t['valve_authority']:.2f} at {r['dp_section_kpa']:.0f} kPa across valve and exchanger", "control valve", "dp_controller_fault")
    add(r["valve_reversals_h"] > L["hunting_reversals_alert_h"] and r["sh_flow_rms_k"] > L["hunting_rms_alert_k"], "DH_VALVE_HUNTING", "Medium",
        f"Valve reverses {r['valve_reversals_h']:.0f} times an hour, flow temperature swings {r['sh_flow_rms_k']:.1f} K RMS", "control valve", "dp_controller_fault")
    add(r["hm_info_code"] > 0.5, "DH_METER_INFO", "Low", f"Heat meter info code {r['hm_info_code']:.0f}", "heat meter")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
