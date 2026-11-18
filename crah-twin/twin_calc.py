"""The chilled-water computer room air handler twin's expectations (CR-6301, Vertiv Liebert PCW PH081DC).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Every expression works on one reading (Monitor keeps no state for the twin).

Air side and water side of the coil (sensible heat, dry coil):
    rho_air  = 353.05 / (T_supply + 273.15)                 kg/m3 (fans after the coil, so supply-air density)
    m_air    = rho_air x airflow / 3600                      kg/s
    Q_air    = m_air x 1.006 x (T_return - T_supply)         kW
    Q_water  = 1000 x flow / 3600 x 4.19 x (T_chwr - T_chws) kW
    coil balance = Q_air / Q_water   (1.0 on a dry coil; a sensor or a meter is wrong when it drifts away)
Coil conductance (fouling):
    LMTD = (dT1 - dT2) / ln(dT1 / dT2), dT1 = T_return - T_chwr, dT2 = T_supply - T_chws   (counterflow form)
    UA_measured = Q_water / LMTD
    UA_expected = UA_rated x (airflow / 20000)^0.6 x (flow / F_rated)^0.25
  UA_rated comes from the maker's rating point (83.3 kW, 29.5 C return, 20,000 m3/h, 10/16.5 C water), computed in _k.
Fans (affinity laws + measured filter pressure):
    P_expected = P_rated x (V / V_rated)^3 + V/3600 x (dp_filter - dp_filter_clean(V)) / eta / 1000
    dp_filter_clean(V) = 60 Pa x (V / V_rated)^1.6,  eta = V_rated/3600 x dp_total_rated / P_rated
    specific fan power SFP = P / (V / 3600)  (W per m3/s)
Air management (mixing at the return):
    T_return = BF x T_supply + (1 - BF) x T_hot_aisle   ->  bypass fraction BF = (T_hot - T_return) / (T_hot - T_supply)
    recirculation = T_rack_inlet - T_supply
Humidity (Magnus): gamma = ln(RH/100) + a T / (b + T),  dew point = b gamma / (a - gamma). Sensible cooling keeps the
moisture, so the dew point at the return and at the rack inlet must agree.
"""
import math


def _k(twin):
    d = twin["design"]
    rt, co, fa, va, si, en, ai = d["rating"], d["coil"], d["fan"], d["valve"], d["site"], d["envelope"], d["air"]
    cp, rc, cw, rw = ai["cp_kj_kgk"], ai["rho_const"], ai["water_cp_kj_kgk"], ai["water_rho"]
    v, q, tr = rt["airflow_m3h"], rt["q_sensible_kw"], rt["return_air_c"]
    ts = tr - 12.0
    for _ in range(60):                                   # rated supply air temperature (density at supply)
        ts = tr - q / (rc / (ts + 273.15) * v / 3600 * cp)
    fw = q / (rw / 3600 * cw * (rt["chw_return_c"] - rt["chw_supply_c"]))
    d1, d2 = tr - rt["chw_return_c"], ts - rt["chw_supply_c"]
    lmtd = (d1 - d2) / math.log(d1 / d2)
    eta = v / 3600 * fa["dp_total_rated_pa"] / (fa["power_rated_kw"] * 1000)
    return dict(cp=cp, rc=rc, cw=cw, rw=rw, v=v, q=q, ts_rated=ts, fw=fw, lmtd=lmtd, ua=q / lmtd,
                ea=co["air_exp"], ew=co["water_exp"], p=fa["power_rated_kw"], dpt=fa["dp_total_rated_pa"],
                dpf=fa["filter_dp_clean_pa"], ef=fa["filter_exp"], eta=eta, fmax=va["flow_max_m3h"],
                sp=si["supply_setpoint_c"], hi=en["recommended_high_c"], a1=en["allowable_a1_high_c"],
                dph=en["dewpoint_high_c"], a=ai["magnus_a"], b=ai["magnus_b"])


def _g(x):
    """Format a constant for an expression."""
    return f"{x:.10g}"


def _parts(twin):
    k = _k(twin)
    g = _g
    RHO = f"({g(k['rc'])} / (df['SUPPLY_AIR_C'] + 273.15))"
    M = f"({RHO} * df['AIRFLOW_M3H'] / 3600)"
    QA = f"({M} * {g(k['cp'])} * (df['RETURN_AIR_C'] - df['SUPPLY_AIR_C']))"
    QW = f"({g(k['rw'] / 3600 * k['cw'])} * df['CHW_FLOW_M3H'] * (df['CHW_RETURN_C'] - df['CHW_SUPPLY_C']))"
    D1 = "(df['RETURN_AIR_C'] - df['CHW_RETURN_C'])"
    D2 = "(df['SUPPLY_AIR_C'] - df['CHW_SUPPLY_C'])"
    LM = f"np.where(np.abs({D1} - {D2}) < 1e-6, {D1}, ({D1} - {D2}) / np.log({D1} / {D2}))"
    UAM = f"({QW} / {LM})"
    UAE = f"({g(k['ua'])} * (df['AIRFLOW_M3H'] / {g(k['v'])}) ** {g(k['ea'])} * (df['CHW_FLOW_M3H'] / {g(k['fw'])}) ** {g(k['ew'])})"
    DPF = f"({g(k['dpf'])} * (df['AIRFLOW_M3H'] / {g(k['v'])}) ** {g(k['ef'])})"
    PE = (f"({g(k['p'])} * (df['AIRFLOW_M3H'] / {g(k['v'])}) ** 3 + df['AIRFLOW_M3H'] / 3600 * (df['FILTER_DP_PA'] - {DPF})"
          f" / {g(k['eta'] * 1000)})")
    SFP = "(df['FAN_POWER_KW'] * 1000 / (df['AIRFLOW_M3H'] / 3600))"
    BF = "((df['RACK_OUTLET_C'] - df['RETURN_AIR_C']) / (df['RACK_OUTLET_C'] - df['SUPPLY_AIR_C']))"

    def dp(t, rh):
        gm = f"(np.log({rh} / 100) + {g(k['a'])} * {t} / ({g(k['b'])} + {t}))"
        return f"({g(k['b'])} * {gm} / ({g(k['a'])} - {gm}))"
    DPR = dp("df['RETURN_AIR_C']", "df['RETURN_RH_PCT']")
    DPI = dp("df['RACK_INLET_C']", "df['RACK_INLET_RH_PCT']")
    return dict(k=k, M=M, QA=QA, QW=QW, LM=LM, UAM=UAM, UAE=UAE, DPF=DPF, PE=PE, SFP=SFP, BF=BF, DPR=DPR, DPI=DPI)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("AIR_MASS_FLOW_KGS", p["M"]),
        ("Q_AIR_KW", p["QA"]),
        ("Q_WATER_KW", p["QW"]),
        ("COIL_BALANCE", f"{p['QA']} / {p['QW']}"),
        ("LOAD_PCT", f"{p['QA']} / {_g(k['q'])} * 100"),
        ("CHW_DT_K", "df['CHW_RETURN_C'] - df['CHW_SUPPLY_C']"),
        ("LMTD_K", p["LM"]),
        ("UA_MEASURED_KW_K", p["UAM"]),
        ("UA_EXPECTED_KW_K", p["UAE"]),
        ("UA_RATIO", f"{p['UAM']} / {p['UAE']}"),
        ("FILTER_DP_EXPECTED_PA", p["DPF"]),
        ("FILTER_LOAD_RATIO", f"df['FILTER_DP_PA'] / {p['DPF']}"),
        ("FAN_POWER_EXPECTED_KW", p["PE"]),
        ("FAN_POWER_RATIO", f"df['FAN_POWER_KW'] / {p['PE']}"),
        ("SFP_W_M3S", p["SFP"]),
        ("BYPASS_FRACTION", p["BF"]),
        ("RECIRC_K", "df['RACK_INLET_C'] - df['SUPPLY_AIR_C']"),
        ("INLET_MARGIN_K", f"{_g(k['hi'])} - df['RACK_INLET_C']"),
        ("DEWPOINT_RETURN_C", p["DPR"]),
        ("DEWPOINT_INLET_C", p["DPI"]),
    ]


def dewpoint(k, t, rh):
    gm = math.log(rh / 100) + k["a"] * t / (k["b"] + t)
    return k["b"] * gm / (k["a"] - gm)


def rh_from_dp(k, t, dp):
    """Relative humidity (%) of air at t (C) with dew point dp (C), Magnus."""
    return 100 * math.exp(k["a"] * dp / (k["b"] + dp) - k["a"] * t / (k["b"] + t))


def evaluate(twin, r):
    k = _k(twin)
    v = r["airflow_m3h"]
    m = k["rc"] / (r["supply_air_c"] + 273.15) * v / 3600
    qa = m * k["cp"] * (r["return_air_c"] - r["supply_air_c"])
    qw = k["rw"] / 3600 * k["cw"] * r["chw_flow_m3h"] * (r["chw_return_c"] - r["chw_supply_c"])
    d1, d2 = r["return_air_c"] - r["chw_return_c"], r["supply_air_c"] - r["chw_supply_c"]
    lm = d1 if abs(d1 - d2) < 1e-6 else (d1 - d2) / math.log(d1 / d2)
    uae = k["ua"] * (v / k["v"]) ** k["ea"] * (r["chw_flow_m3h"] / k["fw"]) ** k["ew"]
    dpf = k["dpf"] * (v / k["v"]) ** k["ef"]
    pe = k["p"] * (v / k["v"]) ** 3 + v / 3600 * (r["filter_dp_pa"] - dpf) / (k["eta"] * 1000)
    return {
        "air_mass_flow_kgs": m, "q_air_kw": qa, "q_water_kw": qw, "coil_balance": qa / qw, "load_pct": qa / k["q"] * 100,
        "chw_dt_k": r["chw_return_c"] - r["chw_supply_c"], "lmtd_k": lm, "ua_measured_kw_k": qw / lm,
        "ua_expected_kw_k": uae, "ua_ratio": qw / lm / uae, "filter_dp_expected_pa": dpf,
        "filter_load_ratio": r["filter_dp_pa"] / dpf, "fan_power_expected_kw": pe, "fan_power_ratio": r["fan_power_kw"] / pe,
        "sfp_w_m3s": r["fan_power_kw"] * 1000 / (v / 3600),
        "bypass_fraction": (r["rack_outlet_c"] - r["return_air_c"]) / (r["rack_outlet_c"] - r["supply_air_c"]),
        "recirc_k": r["rack_inlet_c"] - r["supply_air_c"], "inlet_margin_k": k["hi"] - r["rack_inlet_c"],
        "dewpoint_return_c": dewpoint(k, r["return_air_c"], r["return_rh_pct"]),
        "dewpoint_inlet_c": dewpoint(k, r["rack_inlet_c"], r["rack_inlet_rh_pct"]),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    CB = f"({p['QA']} / {p['QW']})"
    UR = f"({p['UAM']} / {p['UAE']})"
    return [
        ("CRAH_INLET_ALLOWABLE", f"df['RACK_INLET_C'] > {_g(k['a1'])}", "Critical", None),
        ("CRAH_INLET_HIGH", f"(df['RACK_INLET_C'] > {_g(k['hi'])}) & (df['RACK_INLET_C'] <= {_g(k['a1'])})", "High", "recirculation"),
        ("CRAH_VALVE_SATURATED", f"(df['VALVE_POS_PCT'] >= {L['valve_saturated_pct']}) & (df['SUPPLY_AIR_C'] - df['SUPPLY_SETPOINT_C'] > {L['supply_over_sp_k']})",
         "High", "coil_fouling"),
        ("CRAH_DEWPOINT_HIGH", f"{p['DPI']} > {_g(k['dph'])}", "High", "humidity_sensor_drift"),
        ("CRAH_UA_LOW", f"{UR} < {L['ua_ratio_alert']}", "Medium", "coil_fouling"),
        ("CRAH_CHW_DT_LOW", f"((df['CHW_RETURN_C'] - df['CHW_SUPPLY_C']) < {L['chw_dt_low_k']}) & (df['VALVE_POS_PCT'] > 50)", "Medium", "coil_fouling"),
        ("CRAH_COIL_BALANCE", f"np.abs({CB} - 1) > {L['coil_balance_tol']}", "Medium", "supply_sensor_drift"),
        ("CRAH_FILTER_DIRTY", f"df['FILTER_DP_PA'] / {p['DPF']} > {L['filter_ratio_alert']}", "Medium", "filter_loading"),
        ("CRAH_FAN_POWER_HIGH", f"df['FAN_POWER_KW'] / {p['PE']} > {L['fan_power_ratio_alert']}", "Medium", "fan_degradation"),
        ("CRAH_BYPASS_HIGH", f"{p['BF']} > {L['bypass_alert']}", "Medium", "bypass_air"),
        ("CRAH_RECIRC_HIGH", f"(df['RACK_INLET_C'] - df['SUPPLY_AIR_C']) > {L['recirc_alert_k']}", "Medium", "recirculation"),
        ("CRAH_VALVE_HUNTING", f"df['VALVE_REVERSALS_H'] > {L['valve_reversals_alert_h']}", "Medium", "valve_hunting"),
        ("CRAH_RH_SENSOR_MISMATCH", f"np.abs({p['DPR']} - {p['DPI']}) > {L['dp_mismatch_k']}", "Medium", "humidity_sensor_drift"),
        ("CRAH_SFP_HIGH", f"{p['SFP']} > {L['sfp_alert_w_m3s']}", "Low", "bypass_air"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    ti = r["rack_inlet_c"]
    add(ti > k["a1"], "CRAH_INLET_ALLOWABLE", "Critical", f"Server inlet {ti:.1f} °C, above the {k['a1']:.0f} °C allowable limit of class A1", "airflow")
    add(k["hi"] < ti <= k["a1"], "CRAH_INLET_HIGH", "High", f"Server inlet {ti:.1f} °C, above the recommended {k['hi']:.0f} °C", "airflow", "recirculation")
    add(r["valve_pos_pct"] >= L["valve_saturated_pct"] and r["supply_air_c"] - r["supply_setpoint_c"] > L["supply_over_sp_k"],
        "CRAH_VALVE_SATURATED", "High", f"Valve {r['valve_pos_pct']:.0f} % open and supply air {r['supply_air_c'] - r['supply_setpoint_c']:+.1f} K over the setpoint: no cooling left",
        "coil", "coil_fouling")
    add(t["dewpoint_inlet_c"] > k["dph"], "CRAH_DEWPOINT_HIGH", "High", f"Dew point at the server inlet {t['dewpoint_inlet_c']:.1f} °C, above {k['dph']:.0f} °C",
        "humidity", "humidity_sensor_drift")
    add(t["ua_ratio"] < L["ua_ratio_alert"], "CRAH_UA_LOW", "Medium", f"Coil UA {t['ua_measured_kw_k']:.2f} kW/K, {t['ua_ratio']:.2f} × expected", "coil", "coil_fouling")
    add(t["chw_dt_k"] < L["chw_dt_low_k"] and r["valve_pos_pct"] > 50, "CRAH_CHW_DT_LOW", "Medium",
        f"Chilled water ΔT {t['chw_dt_k']:.1f} K with the valve {r['valve_pos_pct']:.0f} % open", "coil", "coil_fouling")
    add(abs(t["coil_balance"] - 1) > L["coil_balance_tol"], "CRAH_COIL_BALANCE", "Medium",
        f"Air side {t['q_air_kw']:.1f} kW against water side {t['q_water_kw']:.1f} kW ({t['coil_balance']:.2f})", "sensor", "supply_sensor_drift")
    add(t["filter_load_ratio"] > L["filter_ratio_alert"], "CRAH_FILTER_DIRTY", "Medium",
        f"Filter drop {r['filter_dp_pa']:.0f} Pa, {t['filter_load_ratio']:.2f} × clean at this airflow", "filter", "filter_loading")
    add(t["fan_power_ratio"] > L["fan_power_ratio_alert"], "CRAH_FAN_POWER_HIGH", "Medium",
        f"Fans draw {r['fan_power_kw']:.2f} kW, {t['fan_power_ratio']:.2f} × the fan law", "fan", "fan_degradation")
    add(t["bypass_fraction"] > L["bypass_alert"], "CRAH_BYPASS_HIGH", "Medium",
        f"{t['bypass_fraction'] * 100:.0f} % of the supply air returns without passing a server", "airflow", "bypass_air")
    add(t["recirc_k"] > L["recirc_alert_k"], "CRAH_RECIRC_HIGH", "Medium",
        f"Server inlet {t['recirc_k']:.1f} K warmer than the supply air", "airflow", "recirculation")
    add(r["valve_reversals_h"] > L["valve_reversals_alert_h"], "CRAH_VALVE_HUNTING", "Medium",
        f"Valve reversed {r['valve_reversals_h']:.0f} times in the last hour", "valve", "valve_hunting")
    add(abs(t["dewpoint_return_c"] - t["dewpoint_inlet_c"]) > L["dp_mismatch_k"], "CRAH_RH_SENSOR_MISMATCH", "Medium",
        f"Dew point {t['dewpoint_return_c']:.1f} °C at the return against {t['dewpoint_inlet_c']:.1f} °C at the rack inlet", "humidity", "humidity_sensor_drift")
    add(t["sfp_w_m3s"] > L["sfp_alert_w_m3s"], "CRAH_SFP_HIGH", "Low", f"Specific fan power {t['sfp_w_m3s']:.0f} W per m³/s", "fan", "bypass_air")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
