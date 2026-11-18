"""The standby diesel generator set twin's expectations (DG-6201, Cummins C2000 D5, 1650 kW standby, QSK60-G3).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Load:  load fraction lf = P / 1650 kW (the standby nameplate; NFPA 110's 30 % test load is a fraction of it).
Fuel:  the data sheet's four standby points (122 / 208 / 300 / 406 L/h at 1/4 ... full load) give, fitted once in
       build_twin.py,
           fuel_expected(P) = a + b P + c P^2        (L/h, P in kW)
       fuel ratio = measured / expected (judged only on load, above 20 % load);
       specific fuel consumption SFC = fuel x density x 1000 / P   (g/kWh).
Exhaust: the data sheet gives 440 C at the standby rating. The twin's line through it (assumption):
           exhaust_expected = t0 + k x lf + 1.0 x (T_ambient - 25)
       residual = mean of the two banks - expected; spread = hottest - coldest cylinder port.
Coolant: while the radiator has spare capacity the thermostat holds the coolant; above that the coolant settles at
           coolant_expected = max(T_thermostat, T_ambient + dT_full x (q0 + (1 - q0) x lf))
       with q0 the share of the full-load heat rejected at no load. Residual = coolant - expected, on load only.
Start and transfer (NFPA 110 Type 10, power back within 10 s):
           ATS time = outage-to-load time - start-to-ready time;  Type 10 margin = 10 s - outage-to-load time.
Transient (ISO 8528-5 G3, diesel): frequency dip <= 7 % and recovery <= 3 s at the site's load step.
Fuel autonomy:  fuel = bulk % x V_bulk + day % x V_day;  run time = fuel / fuel_expected(P)  at the standby rating
       (NFPA 110 Class: hours at rated load without refuelling) and at the data centre's design load.
Wet stacking: index = hours below 30 % load since the last load-bank test / alert hours.
Every expression works on one reading; counters that need history (light-load hours, fuel test age, last start) are kept
at the source: the controller, the ATS and the maintenance records.
"""
import math


def _k(twin):
    d = twin["design"]
    rt, f, ex, co, st, tr, tk, du = (d["rating"], d["fuel"], d["exhaust"], d["coolant"], d["start"], d["transient"],
                                      d["tanks"], d["duty"])
    return dict(kw=rt["standby_kw"], fa=f["fuel_a_lph"], fb=f["fuel_b_lph_per_kw"], fc=f["fuel_c_lph_per_kw2"], rho=f["density_kg_l"],
                e0=ex["t0_c"], e1=ex["t_per_load_c"], ek=ex["t_per_ambient"], eref=ex["ambient_ref_c"],
                tth=co["thermostat_c"], dtf=co["rise_full_k"], q0=co["heat_frac_no_load"],
                type_s=st["type_s"], start_s=st["start_budget_s"], crank_v=st["crank_min_v_alert"],
                fdip=tr["freq_dip_pct"], frec=tr["freq_recovery_s"], vday=tk["day_l"], vbulk=tk["bulk_l"],
                req_h=tk["required_runtime_h"], pdes=tk["design_load_kw"], min_lf=du["min_test_load_pct"] / 100,
                fti=du["fuel_test_interval_d"])


def fuel_expected(k, p):
    """Expected fuel rate (L/h) at p kW, from the data sheet points."""
    return k["fa"] + k["fb"] * p + k["fc"] * p * p


def exhaust_expected(k, lf, amb):
    return k["e0"] + k["e1"] * lf + k["ek"] * (amb - k["eref"])


def coolant_expected(k, lf, amb):
    return max(k["tth"], amb + k["dtf"] * (k["q0"] + (1 - k["q0"]) * lf))


def _parts(twin):
    k = _k(twin)
    P = "df['OUTPUT_KW']"
    LF = f"({P} / {k['kw']})"
    ON = "(df['RUN_MODE'] > 2.5)"
    FE = f"({k['fa']} + {k['fb']} * {P} + {k['fc']} * {P} ** 2)"
    FR = f"(df['FUEL_RATE_LPH'] / {FE})"
    EM = "((df['EXHAUST_TEMP_A_C'] + df['EXHAUST_TEMP_B_C']) / 2)"
    EE = f"({k['e0']} + {k['e1']} * {LF} + {k['ek']} * (df['AMBIENT_C'] - {k['eref']}))"
    SP = "(df['EXHAUST_CYL_MAX_C'] - df['EXHAUST_CYL_MIN_C'])"
    CE = f"np.maximum({k['tth']}, df['AMBIENT_C'] + {k['dtf']} * ({k['q0']} + {1 - k['q0']:.6g} * {LF}))"
    ATS = "(df['LAST_OUTAGE_TO_LOAD_S'] - df['LAST_START_READY_S'])"
    VOL = f"(df['BULK_TANK_PCT'] * {k['vbulk'] / 100:.6g} + df['DAY_TANK_PCT'] * {k['vday'] / 100:.6g})"
    RTF = f"({VOL} / {fuel_expected(k, k['kw']):.9g})"
    return dict(k=k, P=P, LF=LF, ON=ON, FE=FE, FR=FR, EM=EM, EE=EE, SP=SP, CE=CE, ATS=ATS, VOL=VOL, RTF=RTF)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    L = twin["twin_model"]["limits"]
    return [
        ("LOAD_PCT", f"{p['LF']} * 100"),
        ("KVA", f"np.sqrt({p['P']} ** 2 + df['OUTPUT_KVAR'] ** 2)"),
        ("FUEL_EXPECTED_LPH", p["FE"]),
        ("FUEL_RATIO", p["FR"]),
        ("SFC_G_KWH", f"df['FUEL_RATE_LPH'] * {k['rho'] * 1000:.6g} / np.maximum({p['P']}, 1)"),
        ("EXH_MEAN_C", p["EM"]),
        ("EXH_EXPECTED_C", p["EE"]),
        ("EXH_RESIDUAL_K", f"{p['EM']} - {p['EE']}"),
        ("EXH_BANK_DIFF_K", "df['EXHAUST_TEMP_A_C'] - df['EXHAUST_TEMP_B_C']"),
        ("EXH_CYL_SPREAD_K", p["SP"]),
        ("COOLANT_EXPECTED_C", p["CE"]),
        ("COOLANT_RESIDUAL_K", f"df['COOLANT_TEMP_C'] - {p['CE']}"),
        ("ATS_TIME_S", p["ATS"]),
        ("TYPE10_MARGIN_S", f"{k['type_s']} - df['LAST_OUTAGE_TO_LOAD_S']"),
        ("FUEL_VOLUME_L", p["VOL"]),
        ("RUNTIME_FULL_LOAD_H", p["RTF"]),
        ("RUNTIME_DESIGN_LOAD_H", f"{p['VOL']} / {fuel_expected(k, k['pdes']):.9g}"),
        ("WET_STACK_INDEX", f"df['LIGHT_LOAD_H'] / {L['light_load_alert_h']}"),
        ("FUEL_TEST_DUE_D", f"{k['fti']} - df['FUEL_TEST_AGE_D']"),
        ("TRANSIENT_FREQ_MARGIN_PCT", f"{k['fdip']} - df['LAST_STEP_FREQ_DIP_PCT']"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    L = twin["twin_model"]["limits"]
    p = r["output_kw"]
    lf = p / k["kw"]
    fe = fuel_expected(k, p)
    em = (r["exhaust_temp_a_c"] + r["exhaust_temp_b_c"]) / 2
    ee = exhaust_expected(k, lf, r["ambient_c"])
    ce = coolant_expected(k, lf, r["ambient_c"])
    vol = r["bulk_tank_pct"] * k["vbulk"] / 100 + r["day_tank_pct"] * k["vday"] / 100
    return {
        "load_pct": lf * 100, "kva": math.sqrt(p ** 2 + r["output_kvar"] ** 2),
        "fuel_expected_lph": fe, "fuel_ratio": r["fuel_rate_lph"] / fe,
        "sfc_g_kwh": r["fuel_rate_lph"] * k["rho"] * 1000 / max(p, 1),
        "exh_mean_c": em, "exh_expected_c": ee, "exh_residual_k": em - ee,
        "exh_bank_diff_k": r["exhaust_temp_a_c"] - r["exhaust_temp_b_c"],
        "exh_cyl_spread_k": r["exhaust_cyl_max_c"] - r["exhaust_cyl_min_c"],
        "coolant_expected_c": ce, "coolant_residual_k": r["coolant_temp_c"] - ce,
        "ats_time_s": r["last_outage_to_load_s"] - r["last_start_ready_s"],
        "type10_margin_s": k["type_s"] - r["last_outage_to_load_s"],
        "fuel_volume_l": vol, "runtime_full_load_h": vol / fuel_expected(k, k["kw"]),
        "runtime_design_load_h": vol / fuel_expected(k, k["pdes"]),
        "wet_stack_index": r["light_load_h"] / L["light_load_alert_h"],
        "fuel_test_due_d": k["fti"] - r["fuel_test_age_d"],
        "transient_freq_margin_pct": k["fdip"] - r["last_step_freq_dip_pct"],
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    ON, LF = p["ON"], p["LF"]
    return [
        ("GEN_TYPE10_FAIL", f"df['LAST_OUTAGE_TO_LOAD_S'] > {k['type_s']}", "Critical", "starting_battery_weak"),
        ("GEN_START_SLOW", f"df['LAST_START_READY_S'] > {k['start_s']}", "High", "starting_battery_weak"),
        ("GEN_RUNTIME_SHORT", f"{p['RTF']} < {k['req_h']}", "High", None),
        ("GEN_COOLANT_HOT", f"{ON} & ((df['COOLANT_TEMP_C'] - {p['CE']}) > {L['coolant_residual_alert_k']})", "High", "radiator_fouling"),
        ("GEN_CRANK_DIP", f"df['LAST_CRANK_MIN_V'] < {k['crank_v']}", "Medium", "starting_battery_weak"),
        ("GEN_ATS_SLOW", f"{p['ATS']} > {L['ats_time_alert_s']}", "Medium", "ats_slow"),
        ("GEN_JW_HEATER_LOW", f"df['LAST_PRESTART_COOLANT_C'] < {L['prestart_coolant_alert_c']}", "Medium", "jacket_heater_failure"),
        ("GEN_EXH_TEMP_HIGH", f"{ON} & ({LF} >= {k['min_lf']}) & (({p['EM']} - {p['EE']}) > {L['exh_residual_alert_k']})", "Medium", "air_restriction"),
        ("GEN_EXH_SPREAD_HIGH", f"{ON} & ({LF} >= {k['min_lf']}) & ({p['SP']} > {L['exh_spread_alert_k']})", "Medium", "injector_fault"),
        ("GEN_FUEL_RATE_HIGH", f"{ON} & ({LF} >= 0.2) & ({p['FR']} > {L['fuel_ratio_alert']})", "Medium", "air_restriction"),
        ("GEN_TRANSIENT_G3", f"(df['LAST_STEP_FREQ_DIP_PCT'] > {k['fdip']}) | (df['LAST_STEP_FREQ_RECOVERY_S'] > {k['frec']})", "Medium", "air_restriction"),
        ("GEN_TEST_LOAD_LOW", f"(np.abs(df['RUN_MODE'] - 3) < 0.5) & ({LF} < {k['min_lf']}) & ({p['EM']} < {L['min_test_exhaust_c']})", "Medium", "light_load_testing"),
        ("GEN_WET_STACK_RISK", f"df['LIGHT_LOAD_H'] > {L['light_load_alert_h']}", "Medium", "light_load_testing"),
        ("GEN_FUEL_WATER", f"df['FUEL_WATER_PPM'] > {L['fuel_water_alert_ppm']}", "Medium", "fuel_water"),
        ("GEN_DAYTANK_LOW", f"df['DAY_TANK_PCT'] < {L['day_tank_alert_pct']}", "Medium", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    on = r["run_mode"] > 2.5
    lf = t["load_pct"] / 100
    add(r["last_outage_to_load_s"] > k["type_s"], "GEN_TYPE10_FAIL", "Critical",
        f"Load back on the set {r['last_outage_to_load_s']:.1f} s after the outage: more than the {k['type_s']:.0f} s of Type 10", "ats", "starting_battery_weak")
    add(r["last_start_ready_s"] > k["start_s"], "GEN_START_SLOW", "High",
        f"Ready to load {r['last_start_ready_s']:.1f} s after the start signal (budget {k['start_s']} s)", "engine", "starting_battery_weak")
    add(t["runtime_full_load_h"] < k["req_h"], "GEN_RUNTIME_SHORT", "High",
        f"Fuel for {t['runtime_full_load_h']:.0f} h at the standby rating, below the {k['req_h']:.0f} h required", "fuel")
    add(on and t["coolant_residual_k"] > L["coolant_residual_alert_k"], "GEN_COOLANT_HOT", "High",
        f"Coolant {r['coolant_temp_c']:.1f} °C, {t['coolant_residual_k']:.1f} K above what {t['load_pct']:.0f} % load and {r['ambient_c']:.0f} °C ambient explain",
        "cooling", "radiator_fouling")
    add(r["last_crank_min_v"] < k["crank_v"], "GEN_CRANK_DIP", "Medium",
        f"Battery fell to {r['last_crank_min_v']:.1f} V while cranking (alert below {k['crank_v']:.0f} V)", "battery", "starting_battery_weak")
    add(t["ats_time_s"] > L["ats_time_alert_s"], "GEN_ATS_SLOW", "Medium",
        f"Transfer switch took {t['ats_time_s']:.1f} s beyond the set being ready", "ats", "ats_slow")
    add(r["last_prestart_coolant_c"] < L["prestart_coolant_alert_c"], "GEN_JW_HEATER_LOW", "Medium",
        f"Engine at {r['last_prestart_coolant_c']:.1f} °C when it was started: jacket water heater not holding", "cooling", "jacket_heater_failure")
    add(on and lf >= k["min_lf"] and t["exh_residual_k"] > L["exh_residual_alert_k"], "GEN_EXH_TEMP_HIGH", "Medium",
        f"Exhaust {t['exh_mean_c']:.0f} °C, {t['exh_residual_k']:.0f} K above the curve at {t['load_pct']:.0f} % load", "engine", "air_restriction")
    add(on and lf >= k["min_lf"] and t["exh_cyl_spread_k"] > L["exh_spread_alert_k"], "GEN_EXH_SPREAD_HIGH", "Medium",
        f"Cylinder exhaust spread {t['exh_cyl_spread_k']:.0f} K ({r['exhaust_cyl_min_c']:.0f} to {r['exhaust_cyl_max_c']:.0f} °C)", "engine", "injector_fault")
    add(on and lf >= 0.2 and t["fuel_ratio"] > L["fuel_ratio_alert"], "GEN_FUEL_RATE_HIGH", "Medium",
        f"Fuel {r['fuel_rate_lph']:.0f} L/h, {t['fuel_ratio']:.2f} x the data sheet at {r['output_kw']:.0f} kW", "engine", "air_restriction")
    add(r["last_step_freq_dip_pct"] > k["fdip"] or r["last_step_freq_recovery_s"] > k["frec"], "GEN_TRANSIENT_G3", "Medium",
        f"Last {r['last_step_pct']:.0f} % load step: frequency dip {r['last_step_freq_dip_pct']:.1f} %, recovery {r['last_step_freq_recovery_s']:.1f} s (G3: {k['fdip']} %, {k['frec']} s)",
        "engine", "air_restriction")
    add(abs(r["run_mode"] - 3) < 0.5 and lf < k["min_lf"] and t["exh_mean_c"] < L["min_test_exhaust_c"], "GEN_TEST_LOAD_LOW", "Medium",
        f"Monthly test at {t['load_pct']:.0f} % load with exhaust at {t['exh_mean_c']:.0f} °C: neither 30 % load nor the minimum exhaust temperature",
        "testing", "light_load_testing")
    add(r["light_load_h"] > L["light_load_alert_h"], "GEN_WET_STACK_RISK", "Medium",
        f"{r['light_load_h']:.1f} h below 30 % load since the last load-bank test: wet stacking risk", "testing", "light_load_testing")
    add(r["fuel_water_ppm"] > L["fuel_water_alert_ppm"], "GEN_FUEL_WATER", "Medium", f"Water in fuel {r['fuel_water_ppm']:.0f} ppm", "fuel", "fuel_water")
    add(r["day_tank_pct"] < L["day_tank_alert_pct"], "GEN_DAYTANK_LOW", "Medium", f"Day tank at {r['day_tank_pct']:.0f} %", "fuel")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
