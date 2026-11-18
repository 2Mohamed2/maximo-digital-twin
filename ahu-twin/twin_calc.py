"""The air handling unit twin's expectations (AHU-6401, Swegon GOLD RX 20, rotary heat recovery, DCV on CO2).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Fans (EN 16798-3 definition of the specific fan power):
    SFP = (P_supply + P_extract) / q_supply                                        [kW/(m3/s)]
  Each fan works against its filter plus the rest of the system (wheel, casing, coils, ducts). On a fixed duct system the
  rest rises with flow squared; a clean filter rises with flow^n (n = 1.5):
    dp_rest = k x q^2,  k = (dp_design - dp_filter_clean) / q_design^2
    dp_filter_clean(q) = dp_clean_design x (q / q_design)^n
    P = q x (dp_rest + dp_filter) / eta_fan / 1000                                 [kW]
  SFP expected = both fans with clean filters at today's flows. The supply fan's expected power uses the filter pressure
  drop it actually sees, so a dirty filter does not look like a bad fan:
    fan efficiency ratio = P_supply expected (measured filter dp) / P_supply measured
  Filter ratio = filter dp / clean filter dp at today's flow: 2 = plan a change, 3 = change now, < 0.5 = torn or bypassed.
  Extra fan energy of a loaded filter: q x (dp - dp_clean) / eta x hours x price.
Rotary heat exchanger (supply-side temperature ratio, the dry ratio EN 308 tests):
    eta = (t_after_wheel - t_outdoor) / (t_extract - t_outdoor)
    expected = min(cap, eta_design - k_eta x (q_s / q_design - 1)) x min(1, q_e / q_s)
  Compared only when the rotor is commanded to full speed and extract and outdoor differ by at least 8 K.
    recovered heat = rho cp q_s (t_after_wheel - t_outdoor);  heat lost to a slipping wheel = rho cp q_s (expected - eta) (t_e - t_o)
Coils (the air must agree with the water):
    air side = rho cp q_s (t_supply - t_after_wheel) - P_supply   (the supply fan motor heats the air)
    water side = heating meter - cooling meter
    coil balance = (air side - water side) / (rho cp q_s)                            [K]
  A residual in kelvin is a temperature sensor drifting. Heat with the heating valve closed is a passing valve; heating
  and cooling at the same time is wasted energy.
Ventilation (steady-state CO2 balance, G = CO2 generated per person):
    people implied by CO2 = q_s x (CO2 - CO2_outdoor) x 1e-6 / G;   outdoor air per person = q_s x 1000 / people counted   [l/s]
"""

SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}
SFP_BANDS = [300, 500, 750, 1250, 2000, 3000, 4500]     # W/(m3/s): SFP 0 below 300 ... SFP 7 above 4500


def _k(twin):
    d = twin["design"]
    a, f, fl, hr, c, v, e = d["airflow"], d["fans"], d["filters"], d["heat_recovery"], d["coils"], d["ventilation"], d["economics"]
    qd, n = a["design_m3s"], fl["flow_exponent"]
    return dict(qd=qd, rc=a["rho_kg_m3"] * a["cp_kj_kgk"], eta=f["eta_total"], n=n,
                ks=(f["dp_supply_pa"] - fl["supply_clean_pa"]) / qd ** 2, ke=(f["dp_extract_pa"] - fl["extract_clean_pa"]) / qd ** 2,
                fs=fl["supply_clean_pa"] / qd ** n, fe=fl["extract_clean_pa"] / qd ** n, sfp_d=f["sfp_design_kw_m3s"],
                etad=hr["eta_design"], keta=hr["eta_per_flow"], cap=hr["eta_cap"], sp=c["supply_setpoint_c"],
                hcap=c["heating_kw"], ccap=c["cooling_kw"], g=v["co2_per_person_ls"] / 1000, co2o=v["co2_outdoor_ppm"],
                co2sp=v["co2_setpoint_ppm"], qmin=a["min_m3s"], qmax=a["max_m3s"], lsd=v["design_ls_person"],
                pe=e["electricity_eur_kwh"], ph=e["heat_eur_kwh"], hy=e["hours_per_year"])


def fan_kw(k, q, dp_filter, rest_k):
    """Electric power (kW) of one fan moving q m3/s through its filter (dp_filter Pa) and the rest of the system."""
    return q * (rest_k * q ** 2 + dp_filter) / k["eta"] / 1000


def eta_expected(k, qs, qe):
    return min(k["cap"], k["etad"] - k["keta"] * (qs / k["qd"] - 1)) * min(1.0, qe / qs)


def filter_economics(twin):
    """When to change the supply filter, in money (at design flow, operating hours spread evenly over the year).

    The pressure drop rises by `a` Pa per month. One extra Pa costs c = q / eta x hours per month x price per month.
    Changing every T months costs on average  Cf / T + c x a x T / 2  per month (filter set + extra fan energy), which is
    lowest at T* = sqrt(2 Cf / (c a)). The pressure-drop limit (filter_dirty_ratio x clean) is reached after
    T_limit = (ratio - 1) x clean / a months. Change at the earlier of the two.
    """
    k = _k(twin)
    e, fl, L = twin["design"]["economics"], twin["design"]["filters"], twin["twin_model"]["limits"]
    c = k["qd"] / k["eta"] / 1000 * e["hours_per_year"] / 12 * e["electricity_eur_kwh"]      # EUR per Pa per month
    a, cf = e["loading_pa_per_month"], e["filter_set_eur"]
    t_opt = (2 * cf / (c * a)) ** 0.5
    t_lim = (L["filter_dirty_ratio"] - 1) * fl["supply_clean_pa"] / a
    t_lim3 = (L["filter_limit_ratio"] - 1) * fl["supply_clean_pa"] / a
    cost = lambda t: cf / t + c * a * t / 2
    return dict(c=c, a=a, cf=cf, t_opt=t_opt, t_lim=t_lim, t_lim3=t_lim3, cost=cost)


def sfp_category(w):
    return sum(1 for b in SFP_BANDS if w >= b)


def _parts(twin):
    k = _k(twin)
    QS, QE = "df['SUPPLY_FLOW_M3S']", "df['EXTRACT_FLOW_M3S']"
    n, eta = k["n"], k["eta"]
    SFP = f"((df['SUPPLY_FAN_KW'] + df['EXTRACT_FAN_KW']) / {QS})"
    SFPX = (f"(({QS} * ({k['ks']} * {QS} ** 2 + {k['fs']} * {QS} ** {n}) + {QE} * ({k['ke']} * {QE} ** 2 + {k['fe']} * {QE} ** {n}))"
            f" / {eta} / 1000 / {QS})")
    SFPW = f"(df['SUPPLY_FAN_KW'] / {QS} * 1000)"
    CAT = "0"
    for i, b in enumerate(SFP_BANDS):          # the outermost np.where tests the highest band
        CAT = f"np.where({SFPW} >= {b}, {i + 1}, {CAT})"
    FCL = f"({k['fs']} * {QS} ** {n})"
    FR = f"(df['SUPPLY_FILTER_PA'] / {FCL})"
    FRE = f"(df['EXTRACT_FILTER_PA'] / ({k['fe']} * {QE} ** {n}))"
    FCOST = f"({QS} * (df['SUPPLY_FILTER_PA'] - {FCL}) / {eta} / 1000 * {k['hy'] * k['pe']})"
    FX = f"({QS} * ({k['ks']} * {QS} ** 2 + df['SUPPLY_FILTER_PA']) / {eta} / 1000)"
    FER = f"({FX} / df['SUPPLY_FAN_KW'])"
    DT = "(df['T_EXTRACT_C'] - df['T_OUTDOOR_C'])"
    HR = f"((df['T_AFTER_HR_C'] - df['T_OUTDOOR_C']) / {DT})"
    HRX = f"(np.minimum({k['cap']}, {k['etad']} - {k['keta']} * ({QS} / {k['qd']} - 1)) * np.minimum(1, {QE} / {QS}))"
    HRD = f"({HR} - {HRX})"
    REC = f"({k['rc']} * {QS} * (df['T_AFTER_HR_C'] - df['T_OUTDOOR_C']))"
    LOST = f"(np.where(df['WHEEL_SPEED_PCT'] >= {twin['twin_model']['limits']['hr_min_wheel_pct']}, np.maximum(0, {HRX} - {HR}), 0) * {k['rc']} * {QS} * {DT})"
    AIR = f"({k['rc']} * {QS} * (df['T_SUPPLY_C'] - df['T_AFTER_HR_C']) - df['SUPPLY_FAN_KW'])"
    CB = f"(({AIR} - (df['HEATING_KW'] - df['COOLING_KW'])) / ({k['rc']} * {QS}))"
    FB = f"({QE} / {QS})"
    OCC = f"({QS} * (df['CO2_PPM'] - {k['co2o']}) * 1e-06 / {k['g']})"
    VPP = f"({QS} * 1000 / np.maximum(df['OCCUPANCY'], 1))"
    return dict(k=k, SFP=SFP, SFPX=SFPX, SFPW=SFPW, CAT=CAT, FR=FR, FRE=FRE, FCOST=FCOST, FX=FX, FER=FER, DT=DT, HR=HR, HRX=HRX,
                HRD=HRD, REC=REC, LOST=LOST, AIR=AIR, CB=CB, FB=FB, OCC=OCC, VPP=VPP)


def monitor_expressions(twin):
    p = _parts(twin)
    return [
        ("SFP_KW_M3S", p["SFP"]),
        ("SFP_EXPECTED_KW_M3S", p["SFPX"]),
        ("SFP_RATIO", f"{p['SFP']} / {p['SFPX']}"),
        ("SFP_SUPPLY_W_M3S", p["SFPW"]),
        ("SFP_SUPPLY_CATEGORY", p["CAT"]),
        ("FILTER_SUP_RATIO", p["FR"]),
        ("FILTER_EXT_RATIO", p["FRE"]),
        ("FILTER_EXTRA_COST_EUR_Y", p["FCOST"]),
        ("FAN_SUP_EXPECTED_KW", p["FX"]),
        ("FAN_SUP_EFF_RATIO", p["FER"]),
        ("HR_EFF", p["HR"]),
        ("HR_EFF_EXPECTED", p["HRX"]),
        ("HR_EFF_DEV", p["HRD"]),
        ("HR_RECOVERED_KW", p["REC"]),
        ("HR_LOST_KW", p["LOST"]),
        ("COIL_AIR_KW", p["AIR"]),
        ("COIL_BALANCE_K", p["CB"]),
        ("FLOW_BALANCE", p["FB"]),
        ("OCC_FROM_CO2", p["OCC"]),
        ("VENT_PER_PERSON_LS", p["VPP"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    L = twin["twin_model"]["limits"]
    qs, qe, n = r["supply_flow_m3s"], r["extract_flow_m3s"], k["n"]
    sfp = (r["supply_fan_kw"] + r["extract_fan_kw"]) / qs
    sfpx = (qs * (k["ks"] * qs ** 2 + k["fs"] * qs ** n) + qe * (k["ke"] * qe ** 2 + k["fe"] * qe ** n)) / k["eta"] / 1000 / qs
    sfpw = r["supply_fan_kw"] / qs * 1000
    fcl = k["fs"] * qs ** n
    fx = fan_kw(k, qs, r["supply_filter_pa"], k["ks"])
    dt = r["t_extract_c"] - r["t_outdoor_c"]
    hr = (r["t_after_hr_c"] - r["t_outdoor_c"]) / dt
    hrx = eta_expected(k, qs, qe)
    air = k["rc"] * qs * (r["t_supply_c"] - r["t_after_hr_c"]) - r["supply_fan_kw"]
    return {
        "sfp_kw_m3s": sfp, "sfp_expected_kw_m3s": sfpx, "sfp_ratio": sfp / sfpx, "sfp_supply_w_m3s": sfpw,
        "sfp_supply_category": sfp_category(sfpw),
        "filter_sup_ratio": r["supply_filter_pa"] / fcl, "filter_ext_ratio": r["extract_filter_pa"] / (k["fe"] * qe ** n),
        "filter_extra_cost_eur_y": qs * (r["supply_filter_pa"] - fcl) / k["eta"] / 1000 * k["hy"] * k["pe"],
        "fan_sup_expected_kw": fx, "fan_sup_eff_ratio": fx / r["supply_fan_kw"],
        "hr_eff": hr, "hr_eff_expected": hrx, "hr_eff_dev": hr - hrx,
        "hr_recovered_kw": k["rc"] * qs * (r["t_after_hr_c"] - r["t_outdoor_c"]),
        "hr_lost_kw": (max(0.0, hrx - hr) if r["wheel_speed_pct"] >= L["hr_min_wheel_pct"] else 0.0) * k["rc"] * qs * dt,
        "coil_air_kw": air, "coil_balance_k": (air - (r["heating_kw"] - r["cooling_kw"])) / (k["rc"] * qs),
        "flow_balance": qe / qs, "occ_from_co2": qs * (r["co2_ppm"] - k["co2o"]) * 1e-06 / k["g"],
        "vent_per_person_ls": qs * 1000 / max(r["occupancy"], 1),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    FR = p["FR"]
    return [
        ("AHU_FILTER_SUP_LIMIT", f"{FR} > {L['filter_limit_ratio']}", "High", "filter_loading"),
        ("AHU_FILTER_SUP_LOW", f"{FR} < {L['filter_low_ratio']}", "High", "filter_bypass"),
        ("AHU_UNDERVENTILATION", f"(df['OCCUPANCY'] >= {L['vent_min_persons']}) & ({p['VPP']} < {L['vent_alert_ls']})", "High", "co2_sensor_drift"),
        ("AHU_FILTER_SUP_DIRTY", f"({FR} > {L['filter_dirty_ratio']}) & ({FR} <= {L['filter_limit_ratio']})", "Medium", "filter_loading"),
        ("AHU_SFP_HIGH", f"{p['SFP']} / {p['SFPX']} > {L['sfp_ratio_alert']}", "Medium", "filter_loading"),
        ("AHU_FAN_EFF_LOW", f"{p['FER']} < {L['fan_eff_ratio_alert']}", "Medium", "fan_degradation"),
        ("AHU_HR_EFF_LOW", f"(df['WHEEL_SPEED_PCT'] >= {L['hr_min_wheel_pct']}) & ({p['DT']} >= {L['hr_min_dt_k']}) & ({p['HRD']} < {L['hr_dev_alert']})",
         "Medium", "wheel_slip"),
        ("AHU_HEAT_VALVE_PASSING", f"(df['HEATING_KW'] > {L['coil_on_kw']}) & (df['HEATING_VALVE_PCT'] < {L['valve_closed_pct']})", "Medium", "heating_valve_passing"),
        ("AHU_SIMULT_HEAT_COOL", f"(df['HEATING_KW'] > {L['coil_on_kw']}) & (df['COOLING_KW'] > {L['coil_on_kw']})", "Medium", "heating_valve_passing"),
        ("AHU_COIL_BALANCE", f"np.abs({p['CB']}) > {L['coil_balance_alert_k']}", "Medium", "supply_temp_drift"),
        ("AHU_CO2_OCC_MISMATCH", f"np.abs({p['OCC']} - df['OCCUPANCY']) > np.maximum({L['occ_mismatch_min']}, {L['occ_mismatch_frac']} * df['OCCUPANCY'])",
         "Medium", "co2_sensor_drift"),
        ("AHU_FLOW_IMBALANCE", f"np.abs({p['FB']} - 1) > {L['flow_balance_alert']}", "Medium", "extract_blockage"),
        ("AHU_FILTER_EXT_DIRTY", f"{p['FRE']} > {L['extract_filter_ratio']}", "Medium", None),
    ]


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    fr, vpp = t["filter_sup_ratio"], t["vent_per_person_ls"]
    clean = k["fs"] * r["supply_flow_m3s"] ** k["n"]
    add(fr > L["filter_limit_ratio"], "AHU_FILTER_SUP_LIMIT", "High",
        f"Supply filter {r['supply_filter_pa']:.0f} Pa, {fr:.1f} x clean ({clean:.0f} Pa) at this flow: change it now", "filters", "filter_loading")
    add(fr < L["filter_low_ratio"], "AHU_FILTER_SUP_LOW", "High",
        f"Supply filter only {r['supply_filter_pa']:.0f} Pa, {fr:.2f} x clean: torn or bypassed, unfiltered air", "filters", "filter_bypass")
    add(r["occupancy"] >= L["vent_min_persons"] and vpp < L["vent_alert_ls"], "AHU_UNDERVENTILATION", "High",
        f"{vpp:.1f} l/s of outdoor air per person for {r['occupancy']:.0f} people (design {k['lsd']:.0f})", "sensors", "co2_sensor_drift")
    add(L["filter_dirty_ratio"] < fr <= L["filter_limit_ratio"], "AHU_FILTER_SUP_DIRTY", "Medium",
        f"Supply filter {fr:.1f} x clean at this flow: plan a change ({t['filter_extra_cost_eur_y']:.0f} EUR a year of fan energy)", "filters", "filter_loading")
    add(t["sfp_ratio"] > L["sfp_ratio_alert"], "AHU_SFP_HIGH", "Medium",
        f"SFP {t['sfp_kw_m3s']:.2f} kW/(m3/s), {t['sfp_ratio']:.2f} x expected with clean filters at this flow", "fans", "filter_loading")
    add(t["fan_sup_eff_ratio"] < L["fan_eff_ratio_alert"], "AHU_FAN_EFF_LOW", "Medium",
        f"Supply fan draws {r['supply_fan_kw']:.2f} kW against {t['fan_sup_expected_kw']:.2f} kW expected", "fans", "fan_degradation")
    add(r["wheel_speed_pct"] >= L["hr_min_wheel_pct"] and r["t_extract_c"] - r["t_outdoor_c"] >= L["hr_min_dt_k"] and t["hr_eff_dev"] < L["hr_dev_alert"],
        "AHU_HR_EFF_LOW", "Medium",
        f"Wheel recovers {t['hr_eff'] * 100:.0f} % against {t['hr_eff_expected'] * 100:.0f} % expected at full speed: {t['hr_lost_kw']:.1f} kW of heat lost", "heat recovery", "wheel_slip")
    add(r["heating_kw"] > L["coil_on_kw"] and r["heating_valve_pct"] < L["valve_closed_pct"], "AHU_HEAT_VALVE_PASSING", "Medium",
        f"Heat meter {r['heating_kw']:.1f} kW with the heating valve at {r['heating_valve_pct']:.0f} %", "coils", "heating_valve_passing")
    add(r["heating_kw"] > L["coil_on_kw"] and r["cooling_kw"] > L["coil_on_kw"], "AHU_SIMULT_HEAT_COOL", "Medium",
        f"Heating {r['heating_kw']:.1f} kW and cooling {r['cooling_kw']:.1f} kW at the same time", "coils", "heating_valve_passing")
    add(abs(t["coil_balance_k"]) > L["coil_balance_alert_k"], "AHU_COIL_BALANCE", "Medium",
        f"Air temperatures and heat meters disagree by {t['coil_balance_k']:+.1f} K: check the supply air sensor", "sensors", "supply_temp_drift")
    add(abs(t["occ_from_co2"] - r["occupancy"]) > max(L["occ_mismatch_min"], L["occ_mismatch_frac"] * r["occupancy"]), "AHU_CO2_OCC_MISMATCH", "Medium",
        f"CO2 {r['co2_ppm']:.0f} ppm implies {t['occ_from_co2']:.0f} people, the counter says {r['occupancy']:.0f}: check the CO2 sensor", "sensors", "co2_sensor_drift")
    add(abs(t["flow_balance"] - 1) > L["flow_balance_alert"], "AHU_FLOW_IMBALANCE", "Medium",
        f"Extract {r['extract_flow_m3s']:.2f} m3/s against supply {r['supply_flow_m3s']:.2f} m3/s ({(t['flow_balance'] - 1) * 100:+.0f} %)", "ducts", "extract_blockage")
    add(t["filter_ext_ratio"] > L["extract_filter_ratio"], "AHU_FILTER_EXT_DIRTY", "Medium",
        f"Extract filter {r['extract_filter_pa']:.0f} Pa, {t['filter_ext_ratio']:.1f} x clean at this flow", "filters")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
