"""The on-load tap-changer and HV bushing twin's expectations (PT-7501, 60 MVA 132/33 kV grid transformer).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Voltage regulation (tap n, neutral n0, step s, taps on the HV winding, a higher tap removes HV turns):
      V2 (pu) = V1 (pu) / (1 - (n - n0) s) - dV,     dV = I (pu) x (r cos phi + x sin phi)
  r = load losses / rated power, x = sqrt(uk^2 - r^2), both rounded to 6 decimals. The twin predicts the LV voltage from the REPORTED tap and compares it
  with the measured LV voltage (a tap transmitter fault shows as a residual of whole steps), and it computes the tap the
  regulator SHOULD be on to hold the desired value:  n_expected = n0 + (1 - V1 / (Vset + dV)) / s.
  The regulator bandwidth must be greater than 0.6 x step (MR TAPCON instructions), or the tap-changer hunts.
Motor-drive signature (last tap change): mean motor current against the commissioning value corrected for the cabinet
  temperature, I_exp = I0 x (1 + k x (20 - T_cab)); duration against the commissioning value.
Duty: contact wear = sum over operations of (I_switched / I_rated)^2 / interrupter life (operations at rated current);
  maintenance due = max(operations since maintenance / 300,000, years since maintenance / interval): whichever comes first.
OLTC oil: compartment temperature minus top-oil temperature (normally negative); acetylene and ethylene in the OLTC oil in
  excess of the main tank (a vacuum OLTC gasses like the main tank).
Bushings (from the test-tap monitor): C1 change = C1 / C1 nameplate - 1 per bushing (worst of three);
  tan delta ratio = tan delta / tan delta nameplate (worst of three) and the largest tan delta.
"""
import math

PH = ("l1", "l2", "l3")


def _k(twin):
    d = twin["design"]
    tr, tp, ol, rg, mo, th, bs = d["transformer"], d["tapping"], d["oltc"], d["regulator"], d["motor"], d["thermal"], d["bushings"]
    r = round(tr["load_loss_kw"] / (tr["rated_mva"] * 1000), 6)
    x = round(math.sqrt((tr["uk_pct"] / 100) ** 2 - r ** 2), 6)
    return dict(hv=tr["hv_kv"], lv=tr["lv_kv"], ilv=tr["lv_rated_a"], r=r, x=x, n0=tp["neutral"], s=tp["step_pct"] / 100,
                bmin=rg["band_min_factor"] * tp["step_pct"], ir=ol["rated_through_current_a"], mops=ol["maint_ops"], myr=ol["maint_years"],
                life=ol["interrupter_life_ops"], opd=ol["ops_per_day_expected"], t0=mo["op_time_s"], i0=mo["current_a"], kt=mo["current_temp_coeff"],
                tref=mo["ref_temp_c"], c1=bs["c1_pf"], tand=bs["tand_pct"])


def _parts(twin):
    k = _k(twin)
    V1 = f"(df['HV_VOLTAGE_KV'] / {k['hv']})"
    DV = (f"(df['LV_CURRENT_A'] / {k['ilv']} * ({k['r']} * df['POWER_FACTOR'] + {k['x']} * np.sqrt(1 - df['POWER_FACTOR'] ** 2)))")
    VS = f"(df['AVR_SETPOINT_KV'] / {k['lv']})"
    V2E = f"({V1} / (1 - (df['TAP_POSITION'] - {k['n0']}) * {k['s']}) - {DV})"
    TE = f"({k['n0']} + (1 - {V1} / ({VS} + {DV})) / {k['s']})"
    RES = f"((df['LV_VOLTAGE_KV'] / {k['lv']} - {V2E}) * 100)"
    IE = f"({k['i0']} * (1 + {k['kt']} * ({k['tref']} - df['CABINET_TEMP_C'])))"
    C1 = [f"(df['BSH_C1_{p.upper()}_PF'] / {c} - 1) * 100" for p, c in zip(PH, k["c1"])]
    C1M = f"np.maximum(np.maximum({C1[0]}, {C1[1]}), {C1[2]})"
    TR = [f"df['BSH_TAND_{p.upper()}_PCT'] / {t}" for p, t in zip(PH, k["tand"])]
    TRM = f"np.maximum(np.maximum({TR[0]}, {TR[1]}), {TR[2]})"
    TM = "np.maximum(np.maximum(df['BSH_TAND_L1_PCT'], df['BSH_TAND_L2_PCT']), df['BSH_TAND_L3_PCT'])"
    WEAR = f"(df['WEAR_SUM_PU'] / {k['life']} * 100)"
    DUE = f"(np.maximum(df['OPS_SINCE_MAINT'] / {k['mops']}, df['YEARS_SINCE_MAINT'] / {k['myr']}) * 100)"
    REM = f"np.minimum(({k['mops']} - df['OPS_SINCE_MAINT']) / np.maximum(df['OPS_365D'], 1), {k['myr']} - df['YEARS_SINCE_MAINT'])"
    return dict(k=k, V1=V1, DV=DV, V2E=V2E, TE=TE, RES=RES, IE=IE, C1M=C1M, TRM=TRM, TM=TM, WEAR=WEAR, DUE=DUE, REM=REM)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("LOAD_DROP_PCT", f"{p['DV']} * 100"),
        ("LV_VOLTAGE_EXPECTED_KV", f"{p['V2E']} * {k['lv']}"),
        ("LV_VOLTAGE_RESIDUAL_PCT", p["RES"]),
        ("TAP_EXPECTED", p["TE"]),
        ("TAP_DEVIATION", f"df['TAP_POSITION'] - {p['TE']}"),
        ("VOLTAGE_DEVIATION_PCT", "(df['LV_VOLTAGE_KV'] / df['AVR_SETPOINT_KV'] - 1) * 100"),
        ("BAND_MARGIN_PCT", f"df['AVR_BAND_PCT'] - {k['bmin']:.6g}"),
        ("OPS_RATIO", f"df['OPS_24H'] / {k['opd']}"),
        ("MOTOR_CURRENT_EXPECTED_A", p["IE"]),
        ("MOTOR_CURRENT_RATIO", f"df['MOTOR_CURRENT_A'] / {p['IE']}"),
        ("OP_TIME_RATIO", f"df['OP_TIME_S'] / {k['t0']}"),
        ("CONTACT_WEAR_PCT", p["WEAR"]),
        ("MAINT_DUE_PCT", p["DUE"]),
        ("MAINT_REMAINING_YEARS", p["REM"]),
        ("OLTC_TEMP_DIFF_K", "df['OLTC_OIL_TEMP_C'] - df['TOP_OIL_TEMP_C']"),
        ("OLTC_C2H2_EXCESS_PPM", "df['OLTC_C2H2_PPM'] - df['MAIN_C2H2_PPM']"),
        ("OLTC_C2H4_EXCESS_PPM", "df['OLTC_C2H4_PPM'] - df['MAIN_C2H4_PPM']"),
        ("BSH_C1_CHANGE_MAX_PCT", p["C1M"]),
        ("BSH_TAND_RATIO_MAX", p["TRM"]),
        ("BSH_TAND_MAX_PCT", p["TM"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    v1 = r["hv_voltage_kv"] / k["hv"]
    pf = r["power_factor"]
    dv = r["lv_current_a"] / k["ilv"] * (k["r"] * pf + k["x"] * math.sqrt(1 - pf ** 2))
    vs = r["avr_setpoint_kv"] / k["lv"]
    v2e = v1 / (1 - (r["tap_position"] - k["n0"]) * k["s"]) - dv
    te = k["n0"] + (1 - v1 / (vs + dv)) / k["s"]
    ie = k["i0"] * (1 + k["kt"] * (k["tref"] - r["cabinet_temp_c"]))
    c1 = max((r[f"bsh_c1_{p}_pf"] / c - 1) * 100 for p, c in zip(PH, k["c1"]))
    trm = max(r[f"bsh_tand_{p}_pct"] / t for p, t in zip(PH, k["tand"]))
    return {
        "load_drop_pct": dv * 100, "lv_voltage_expected_kv": v2e * k["lv"],
        "lv_voltage_residual_pct": (r["lv_voltage_kv"] / k["lv"] - v2e) * 100,
        "tap_expected": te, "tap_deviation": r["tap_position"] - te,
        "voltage_deviation_pct": (r["lv_voltage_kv"] / r["avr_setpoint_kv"] - 1) * 100,
        "band_margin_pct": r["avr_band_pct"] - k["bmin"], "ops_ratio": r["ops_24h"] / k["opd"],
        "motor_current_expected_a": ie, "motor_current_ratio": r["motor_current_a"] / ie, "op_time_ratio": r["op_time_s"] / k["t0"],
        "contact_wear_pct": r["wear_sum_pu"] / k["life"] * 100,
        "maint_due_pct": max(r["ops_since_maint"] / k["mops"], r["years_since_maint"] / k["myr"]) * 100,
        "maint_remaining_years": min((k["mops"] - r["ops_since_maint"]) / max(r["ops_365d"], 1), k["myr"] - r["years_since_maint"]),
        "oltc_temp_diff_k": r["oltc_oil_temp_c"] - r["top_oil_temp_c"],
        "oltc_c2h2_excess_ppm": r["oltc_c2h2_ppm"] - r["main_c2h2_ppm"], "oltc_c2h4_excess_ppm": r["oltc_c2h4_ppm"] - r["main_c2h4_ppm"],
        "bsh_c1_change_max_pct": c1, "bsh_tand_ratio_max": trm,
        "bsh_tand_max_pct": max(r["bsh_tand_l1_pct"], r["bsh_tand_l2_pct"], r["bsh_tand_l3_pct"]),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    tm = L["tap_mismatch_steps"] * k["s"] * 100
    return [
        ("BSH_C1_CRITICAL", f"{p['C1M']} >= {L['c1_limit_pct']}", "Critical", "bushing_layer_short"),
        ("BSH_C1_HIGH", f"({p['C1M']} >= {L['c1_alert_pct']}) & ({p['C1M']} < {L['c1_limit_pct']})", "High", "bushing_layer_short"),
        ("BSH_TAND_LIMIT", f"{p['TM']} >= {L['tand_limit_pct']}", "High", "bushing_moisture"),
        ("OLTC_DGA_ARCING", f"(df['OLTC_C2H2_PPM'] - df['MAIN_C2H2_PPM']) > {L['oltc_c2h2_excess_ppm']}", "High", "vacuum_loss"),
        ("OLTC_TEMP_DIFF", f"(df['OLTC_OIL_TEMP_C'] - df['TOP_OIL_TEMP_C']) > {L['temp_diff_alert_k']}", "High", "compartment_heating"),
        ("BSH_TAND_RISE", f"{p['TRM']} >= {L['tand_ratio_alert']}", "Medium", "bushing_moisture"),
        ("OLTC_DGA_HEATING", f"(df['OLTC_C2H4_PPM'] - df['MAIN_C2H4_PPM']) > {L['oltc_c2h4_excess_ppm']}", "Medium", "compartment_heating"),
        ("OLTC_MOTOR_CURRENT_HIGH", f"df['MOTOR_CURRENT_A'] / {p['IE']} > {L['motor_current_ratio_alert']}", "Medium", "drive_stiff"),
        ("OLTC_OP_SLOW", f"df['OP_TIME_S'] / {k['t0']} > {L['op_time_ratio_alert']}", "Medium", "drive_stiff"),
        ("OLTC_TAP_MISMATCH", f"np.abs({p['RES']}) > {tm:.6g}", "Medium", "tap_sensor_fault"),
        ("OLTC_HUNTING", f"df['OPS_24H'] / {k['opd']} > {L['ops_ratio_alert']}", "Medium", "band_too_narrow"),
        ("OLTC_CONTACT_WEAR", f"{p['WEAR']} > {L['wear_alert_pct']}", "Medium", "contact_wear"),
        ("OLTC_MAINT_DUE", f"{p['DUE']} >= 100", "Medium", None),
        ("OLTC_BAND_NARROW", f"df['AVR_BAND_PCT'] < {k['bmin']:.6g}", "Low", "band_too_narrow"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    tm = L["tap_mismatch_steps"] * k["s"] * 100
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    c1, trm, tmax = t["bsh_c1_change_max_pct"], t["bsh_tand_ratio_max"], t["bsh_tand_max_pct"]
    add(c1 >= L["c1_limit_pct"], "BSH_C1_CRITICAL", "Critical", f"Bushing C1 up {c1:.1f} % on its nameplate: several layers shorted, take the transformer out", "bushing", "bushing_layer_short")
    add(L["c1_alert_pct"] <= c1 < L["c1_limit_pct"], "BSH_C1_HIGH", "High", f"Bushing C1 up {c1:.1f} % on its nameplate: partial breakdown between layers", "bushing", "bushing_layer_short")
    add(tmax >= L["tand_limit_pct"], "BSH_TAND_LIMIT", "High", f"Bushing tan delta {tmax:.2f} %, at or above {L['tand_limit_pct']} %", "bushing", "bushing_moisture")
    add(t["oltc_c2h2_excess_ppm"] > L["oltc_c2h2_excess_ppm"], "OLTC_DGA_ARCING", "High",
        f"Acetylene in the OLTC oil {t['oltc_c2h2_excess_ppm']:.0f} ppm above the main tank: arcing outside the vacuum", "oltc", "vacuum_loss")
    add(t["oltc_temp_diff_k"] > L["temp_diff_alert_k"], "OLTC_TEMP_DIFF", "High",
        f"OLTC oil {t['oltc_temp_diff_k']:+.1f} K against the top oil: the compartment makes heat", "oltc", "compartment_heating")
    add(trm >= L["tand_ratio_alert"], "BSH_TAND_RISE", "Medium", f"Bushing tan delta {trm:.1f} x its nameplate value", "bushing", "bushing_moisture")
    add(t["oltc_c2h4_excess_ppm"] > L["oltc_c2h4_excess_ppm"], "OLTC_DGA_HEATING", "Medium",
        f"Ethylene in the OLTC oil {t['oltc_c2h4_excess_ppm']:.0f} ppm above the main tank: overheated contact", "oltc", "compartment_heating")
    add(t["motor_current_ratio"] > L["motor_current_ratio_alert"], "OLTC_MOTOR_CURRENT_HIGH", "Medium",
        f"Motor current {r['motor_current_a']:.2f} A, {t['motor_current_ratio']:.2f} x expected at {r['cabinet_temp_c']:.0f} °C", "drive", "drive_stiff")
    add(t["op_time_ratio"] > L["op_time_ratio_alert"], "OLTC_OP_SLOW", "Medium", f"Tap change took {r['op_time_s']:.1f} s, {t['op_time_ratio']:.2f} x commissioning", "drive", "drive_stiff")
    add(abs(t["lv_voltage_residual_pct"]) > tm, "OLTC_TAP_MISMATCH", "Medium",
        f"LV voltage {t['lv_voltage_residual_pct']:+.2f} % from what tap {r['tap_position']:.0f} must give: tap reading wrong", "drive", "tap_sensor_fault")
    add(t["ops_ratio"] > L["ops_ratio_alert"], "OLTC_HUNTING", "Medium", f"{r['ops_24h']:.0f} tap changes in 24 h, {t['ops_ratio']:.1f} x normal", "regulator", "band_too_narrow")
    add(t["contact_wear_pct"] > L["wear_alert_pct"], "OLTC_CONTACT_WEAR", "Medium", f"Interrupter contact wear {t['contact_wear_pct']:.0f} % of life", "oltc", "contact_wear")
    add(t["maint_due_pct"] >= 100, "OLTC_MAINT_DUE", "Medium", f"OLTC maintenance due ({t['maint_due_pct']:.0f} % of the interval)", "oltc")
    add(r["avr_band_pct"] < k["bmin"], "OLTC_BAND_NARROW", "Low", f"Bandwidth ±{r['avr_band_pct']:.2f} % is below 0.6 step (±{k['bmin']:.2f} %)", "regulator", "band_too_narrow")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
