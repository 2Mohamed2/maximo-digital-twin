"""The SF6 circuit breaker twin's expectations (Siemens Energy 3AP1 FG 145 kV, IEC 62271-100).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (twin viewer, tests)

SF6 density:
  The gas pressure rises and falls with the gas temperature at constant density. Density monitors therefore report the
  pressure "compensated to 20 C". The twin compensates the raw pressure and gas temperature itself, along the
  ideal-gas isochore p20 = p x 293.15 / (T + 273.15), and compares the result with the filling (0.70 MPa abs), alarm
  (0.62, assumed) and lockout (0.60 = minimum functional pressure) densities. The difference between the monitor's own
  output and the twin's compensation is the monitor drift check.
Operating mechanism:
  expected opening / closing time = rated time (23 / 54 ms) + sensitivity x (110 V - control voltage);
  expected trip coil peak current = control voltage / coil resistance; spring charging time against 12 s.
Contact wear:
  the breaker monitor accumulates sum(I^1.8) per pole over every opening; wear % = sum / (20 x 40 kA^1.8) x 100.
Pole temperature:
  terminal temperature rise expected = 35 K x (I / 3150 A)^2; a lasting excess means a higher contact resistance.
"""
import math


def _k(twin):
    d = twin["design"]
    g, m, w, th = d["sf6"], d["mechanism"], d["wear"], d["thermal"]
    return dict(fill=g["fill_mpa_abs_20c"], alarm=g["alarm_mpa_abs_20c"], lock=g["lockout_mpa_abs_20c"], early=g["early_warning_mpa_abs_20c"],
                rs=g["r_specific_j_kgk"], to=m["open_time_ms"], tc=m["close_time_ms"], uc=m["coil_voltage_v"], so=m["open_ms_per_v"],
                sc=m["close_ms_per_v"], rtc=m["trip_coil_r_ohm"], tch=m["charge_time_s"], allow=w["allowance_ka_y"],
                rise=th["pole_rise_at_ir_k"], ir=d["rating"]["ir_a"])


def p20(k, p_mpa, t_c):
    return p_mpa * 293.15 / (t_c + 273.15)


def _parts(twin):
    k = _k(twin)
    P20 = "(df['SF6_PRESSURE_MPA'] * 293.15 / (df['SF6_GAS_TEMP_C'] + 273.15))"
    OTE = f"({k['to']} + {k['so']} * ({k['uc']} - df['CONTROL_VOLTAGE_V']))"
    CTE = f"({k['tc']} + {k['sc']} * ({k['uc']} - df['CONTROL_VOLTAGE_V']))"
    TCE = f"(df['CONTROL_VOLTAGE_V'] / {k['rtc']})"
    W = {i: f"(df['WEAR_SUM_L{i}'] / {k['allow']} * 100)" for i in (1, 2, 3)}
    WMAX = f"np.maximum(np.maximum({W[1]}, {W[2]}), {W[3]})"
    RISEE = {i: f"({k['rise']} * (df['LOAD_CURRENT_L{i}_A'] / {k['ir']}) ** 2)" for i in (1, 2, 3)}
    RES = {i: f"((df['POLE_TEMP_L{i}_C'] - df['AMBIENT_TEMP_C']) - {RISEE[i]})" for i in (1, 2, 3)}
    RESMAX = f"np.maximum(np.maximum({RES[1]}, {RES[2]}), {RES[3]})"
    IMAX = "np.maximum(np.maximum(df['LOAD_CURRENT_L1_A'], df['LOAD_CURRENT_L2_A']), df['LOAD_CURRENT_L3_A'])"
    return dict(k=k, P20=P20, OTE=OTE, CTE=CTE, TCE=TCE, W=W, WMAX=WMAX, RISEE=RISEE, RES=RES, RESMAX=RESMAX, IMAX=IMAX)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("SF6_P20_CALC_MPA", p["P20"]),
        ("SF6_DENSITY_KG_M3", f"{p['P20']} * 1e6 / ({k['rs']} * 293.15)"),
        ("SF6_MARGIN_ALARM_MPA", f"{p['P20']} - {k['alarm']}"),
        ("SF6_MARGIN_LOCKOUT_MPA", f"{p['P20']} - {k['lock']}"),
        ("DENSITY_MONITOR_DEV_MPA", f"df['SF6_DENSITY_P20_MPA'] - {p['P20']}"),
        ("OPEN_TIME_EXPECTED_MS", p["OTE"]),
        ("OPEN_TIME_DEV_MS", f"df['LAST_OPEN_TIME_MS'] - {p['OTE']}"),
        ("CLOSE_TIME_EXPECTED_MS", p["CTE"]),
        ("CLOSE_TIME_DEV_MS", f"df['LAST_CLOSE_TIME_MS'] - {p['CTE']}"),
        ("TRIP_COIL_EXPECTED_A", p["TCE"]),
        ("TRIP_COIL_RATIO", f"df['TRIP_COIL_PEAK_A'] / {p['TCE']}"),
        ("CHARGE_TIME_EXPECTED_S", f"df['CONTROL_VOLTAGE_V'] * 0 + {k['tch']}"),
        ("CHARGE_TIME_RATIO", f"df['SPRING_CHARGE_TIME_S'] / {k['tch']}"),
        ("WEAR_L1_PCT", p["W"][1]),
        ("WEAR_L2_PCT", p["W"][2]),
        ("WEAR_L3_PCT", p["W"][3]),
        ("WEAR_MAX_PCT", p["WMAX"]),
        ("POLE_RISE_L2_K", "df['POLE_TEMP_L2_C'] - df['AMBIENT_TEMP_C']"),
        ("POLE_RISE_EXPECTED_K", p["RISEE"][2]),
        ("POLE_RESIDUAL_MAX_K", p["RESMAX"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    pc = p20(k, r["sf6_pressure_mpa"], r["sf6_gas_temp_c"])
    uc = r["control_voltage_v"]
    ote = k["to"] + k["so"] * (k["uc"] - uc)
    cte = k["tc"] + k["sc"] * (k["uc"] - uc)
    tce = uc / k["rtc"]
    w = {i: r[f"wear_sum_l{i}"] / k["allow"] * 100 for i in (1, 2, 3)}
    risee = {i: k["rise"] * (r[f"load_current_l{i}_a"] / k["ir"]) ** 2 for i in (1, 2, 3)}
    res = {i: (r[f"pole_temp_l{i}_c"] - r["ambient_temp_c"]) - risee[i] for i in (1, 2, 3)}
    return {
        "sf6_p20_calc_mpa": pc, "sf6_density_kg_m3": pc * 1e6 / (k["rs"] * 293.15),
        "sf6_margin_alarm_mpa": pc - k["alarm"], "sf6_margin_lockout_mpa": pc - k["lock"],
        "density_monitor_dev_mpa": r["sf6_density_p20_mpa"] - pc,
        "open_time_expected_ms": ote, "open_time_dev_ms": r["last_open_time_ms"] - ote,
        "close_time_expected_ms": cte, "close_time_dev_ms": r["last_close_time_ms"] - cte,
        "trip_coil_expected_a": tce, "trip_coil_ratio": r["trip_coil_peak_a"] / tce,
        "charge_time_expected_s": uc * 0 + k["tch"], "charge_time_ratio": r["spring_charge_time_s"] / k["tch"],
        "wear_l1_pct": w[1], "wear_l2_pct": w[2], "wear_l3_pct": w[3], "wear_max_pct": max(max(w[1], w[2]), w[3]),
        "pole_rise_l2_k": r["pole_temp_l2_c"] - r["ambient_temp_c"], "pole_rise_expected_k": risee[2],
        "pole_residual_max_k": max(max(res[1], res[2]), res[3]),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    P20 = p["P20"]
    return [
        ("CB_SF6_LOCKOUT", f"{P20} < {k['lock']}", "Critical", "sf6_leak"),
        ("CB_SF6_ALARM", f"({P20} < {k['alarm']}) & ({P20} >= {k['lock']})", "High", "sf6_leak"),
        ("CB_SF6_LOW", f"({P20} < {k['early']}) & ({P20} >= {k['alarm']})", "Low", "sf6_leak"),
        ("CB_DENSITY_MONITOR", f"np.abs(df['SF6_DENSITY_P20_MPA'] - {P20}) > {L['density_monitor_dev_alert_mpa']}", "Medium", "density_monitor_drift"),
        ("CB_OPEN_SLOW", f"(df['LAST_OPEN_TIME_MS'] - {p['OTE']}) > {L['open_time_dev_alert_ms']}", "Medium", "mechanism_lubrication"),
        ("CB_CLOSE_SLOW", f"(df['LAST_CLOSE_TIME_MS'] - {p['CTE']}) > {L['close_time_dev_alert_ms']}", "Medium", "mechanism_lubrication"),
        ("CB_TRIP_COIL", f"(df['TRIP_COIL_PEAK_A'] / {p['TCE']}) < {L['trip_coil_ratio_alert']}", "High", "trip_coil"),
        ("CB_SPRING_CHARGE", f"(df['SPRING_CHARGE_TIME_S'] / {k['tch']}) > {L['charge_time_ratio_alert']}", "Medium", "spring_motor"),
        ("CB_CONTACT_WEAR", f"({p['WMAX']} > {L['wear_alert_pct']}) & ({p['WMAX']} < {L['wear_limit_pct']})", "Medium", "contact_wear"),
        ("CB_CONTACT_WEAR_LIMIT", f"{p['WMAX']} >= {L['wear_limit_pct']}", "High", "contact_wear"),
        ("CB_POLE_HOT", f"({p['RESMAX']} > {L['pole_residual_alert_k']}) & ({p['IMAX']} > {L['pole_check_min_a']})", "Medium", "contact_wear"),
        ("CB_HEATER", f"(df['HEATER_CURRENT_A'] < {L['heater_min_a']}) | (df['CABINET_HUMIDITY_PCT'] > {L['humidity_alert_pct']})", "Medium", "heater_fault"),
        ("CB_INSPECTION_DUE", f"df['OPERATION_COUNT'] >= {L['inspection_cycles']}", "Low", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    pc = t["sf6_p20_calc_mpa"]
    imax = max(max(r["load_current_l1_a"], r["load_current_l2_a"]), r["load_current_l3_a"])
    add(pc < k["lock"], "CB_SF6_LOCKOUT", "Critical", f"SF6 {pc:.3f} MPa at 20 °C, below the lockout density {k['lock']}: breaker blocked", "gas", "sf6_leak")
    add(k["lock"] <= pc < k["alarm"], "CB_SF6_ALARM", "High", f"SF6 {pc:.3f} MPa at 20 °C, below the alarm density {k['alarm']}: refill", "gas", "sf6_leak")
    add(k["alarm"] <= pc < k["early"], "CB_SF6_LOW", "Low", f"SF6 {pc:.3f} MPa at 20 °C, {t['sf6_margin_alarm_mpa'] * 1000:.0f} kPa above alarm", "gas", "sf6_leak")
    add(abs(t["density_monitor_dev_mpa"]) > L["density_monitor_dev_alert_mpa"], "CB_DENSITY_MONITOR", "Medium",
        f"Density monitor reads {t['density_monitor_dev_mpa'] * 1000:+.0f} kPa vs. the twin's compensation", "gas", "density_monitor_drift")
    add(t["open_time_dev_ms"] > L["open_time_dev_alert_ms"], "CB_OPEN_SLOW", "Medium",
        f"Opening {r['last_open_time_ms']:.1f} ms, {t['open_time_dev_ms']:+.1f} ms vs. expected", "mechanism", "mechanism_lubrication")
    add(t["close_time_dev_ms"] > L["close_time_dev_alert_ms"], "CB_CLOSE_SLOW", "Medium",
        f"Closing {r['last_close_time_ms']:.1f} ms, {t['close_time_dev_ms']:+.1f} ms vs. expected", "mechanism", "mechanism_lubrication")
    add(t["trip_coil_ratio"] < L["trip_coil_ratio_alert"], "CB_TRIP_COIL", "High",
        f"Trip coil peak {r['trip_coil_peak_a']:.2f} A, {t['trip_coil_ratio'] * 100:.0f} % of expected", "coils", "trip_coil")
    add(t["charge_time_ratio"] > L["charge_time_ratio_alert"], "CB_SPRING_CHARGE", "Medium",
        f"Spring charged in {r['spring_charge_time_s']:.1f} s (expected {k['tch']:.0f} s), motor {r['spring_motor_current_a']:.1f} A", "mechanism", "spring_motor")
    add(L["wear_alert_pct"] < t["wear_max_pct"] < L["wear_limit_pct"], "CB_CONTACT_WEAR", "Medium",
        f"Contact wear {t['wear_max_pct']:.0f} % of the allowance (worst pole)", "interrupter", "contact_wear")
    add(t["wear_max_pct"] >= L["wear_limit_pct"], "CB_CONTACT_WEAR_LIMIT", "High",
        f"Contact wear {t['wear_max_pct']:.0f} %: interrupter overhaul due", "interrupter", "contact_wear")
    add(t["pole_residual_max_k"] > L["pole_residual_alert_k"] and imax > L["pole_check_min_a"], "CB_POLE_HOT", "Medium",
        f"Pole terminal {t['pole_residual_max_k']:.1f} K hotter than (I/Ir)² explains", "interrupter", "contact_wear")
    add(r["heater_current_a"] < L["heater_min_a"] or r["cabinet_humidity_pct"] > L["humidity_alert_pct"], "CB_HEATER", "Medium",
        f"Heater {r['heater_current_a']:.2f} A, cabinet humidity {r['cabinet_humidity_pct']:.0f} %", "cabinet", "heater_fault")
    add(r["operation_count"] >= L["inspection_cycles"], "CB_INSPECTION_DUE", "Low",
        f"{r['operation_count']:.0f} operating cycles: first inspection due at {L['inspection_cycles']}", "mechanism")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
