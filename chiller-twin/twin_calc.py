"""The chiller twin's expectations from BITZER data (EN 12900 polynomial + clean heat exchangers).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (twin viewer, tests)
The clean-exchanger approach uses the effectiveness at design water flow (k = (1/eps - 1)/C), so Monitor needs no exp().
"""
import math

TON_KW = 3.517


def _k(twin):
    d = twin["design"]
    c = d["compressor"]
    cp = d["water_cp_kW_per_m3h_K"]
    ev, cd = d["evaporator"], d["condenser"]
    Ce, Cc = cp * ev["chw_flow_m3h"], cp * cd["cw_flow_m3h"]
    eps_e, eps_c = 1 - math.exp(-ev["UA_kW_K"] / Ce), 1 - math.exp(-cd["UA_kW_K"] / Cc)
    return dict(Q=c["en12900"]["Q_kW"], P=c["en12900"]["P_kW"], a=c["part_load_power"]["a"], cp=cp,
                ke=(1 / eps_e - 1) / Ce, kc=(1 / eps_c - 1) / Cc)


def _p(c, to, tc):
    return (f"({c[0]!r} + ({c[1]!r})*{to} + ({c[2]!r})*{tc} + ({c[3]!r})*{to}**2 + ({c[4]!r})*{to}*{tc} + ({c[5]!r})*{tc}**2"
            f" + ({c[6]!r})*{to}**3 + ({c[7]!r})*{to}**2*{tc} + ({c[8]!r})*{to}*{tc}**2 + ({c[9]!r})*{tc}**3)")


def poly10(c, to, tc):
    return (c[0] + c[1] * to + c[2] * tc + c[3] * to * to + c[4] * to * tc + c[5] * tc * tc
            + c[6] * to ** 3 + c[7] * to * to * tc + c[8] * to * tc * tc + c[9] * tc ** 3)


def _parts(twin):
    k = _k(twin)
    TO, TC, SL = "df['EVAP_SAT_TEMP_C']", "df['COND_SAT_TEMP_C']", "(df['SLIDE_PCT'] / 100)"
    QM = f"({k['cp']} * df['CHW_FLOW_M3H'] * (df['CHW_IN_TEMP_C'] - df['CHW_OUT_TEMP_C']))"
    QE = f"({SL} * {_p(k['Q'], TO, TC)})"
    PE = f"({_p(k['P'], TO, TC)} * ({k['a']} + {1 - k['a']} * {SL}))"
    CA = "(df['COND_SAT_TEMP_C'] - df['CW_OUT_TEMP_C'])"
    CAE = f"({k['kc']} * ({QM} + df['POWER_KW']))"
    EA = "(df['CHW_OUT_TEMP_C'] - df['EVAP_SAT_TEMP_C'])"
    EAE = f"({k['ke']} * {QM})"
    return QM, QE, PE, CA, CAE, EA, EAE


def monitor_expressions(twin):
    QM, QE, PE, CA, CAE, EA, EAE = _parts(twin)
    return [
        ("Q_EXPECTED_KW", QE),
        ("CAPACITY_DEVIATION_PCT", f"({QM} - {QE}) / {QE}.clip(lower=1) * 100"),
        ("P_EXPECTED_KW", PE),
        ("POWER_DEVIATION_PCT", f"(df['POWER_KW'] - {PE}) / {PE}.clip(lower=1) * 100"),
        ("COP", f"{QM} / df['POWER_KW'].clip(lower=0.5)"),
        ("COP_EXPECTED", f"{QE} / {PE}.clip(lower=0.5)"),
        ("KW_PER_TON", f"df['POWER_KW'] / ({QM} / {TON_KW}).clip(lower=0.5)"),
        ("COND_APPROACH_K", CA),
        ("COND_APPROACH_EXPECTED_K", CAE),
        ("COND_FOULING_K", f"{CA} - {CAE}"),
        ("EVAP_APPROACH_K", EA),
        ("EVAP_APPROACH_EXPECTED_K", EAE),
        ("EVAP_FOULING_K", f"{EA} - {EAE}"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    to, tc, sl = r["evap_sat_temp_c"], r["cond_sat_temp_c"], r["slide_pct"] / 100
    qm = k["cp"] * r["chw_flow_m3h"] * (r["chw_in_temp_c"] - r["chw_out_temp_c"])
    qe = sl * poly10(k["Q"], to, tc)
    pe = poly10(k["P"], to, tc) * (k["a"] + (1 - k["a"]) * sl)
    ca, ea = tc - r["cw_out_temp_c"], r["chw_out_temp_c"] - to
    cae, eae = k["kc"] * (qm + r["power_kw"]), k["ke"] * qm
    return {
        "q_expected_kw": qe, "capacity_deviation_pct": (qm - qe) / max(qe, 1) * 100,
        "p_expected_kw": pe, "power_deviation_pct": (r["power_kw"] - pe) / max(pe, 1) * 100,
        "cop": qm / max(r["power_kw"], 0.5), "cop_expected": qe / max(pe, 0.5),
        "kw_per_ton": r["power_kw"] / max(qm / TON_KW, 0.5),
        "cond_approach_k": ca, "cond_approach_expected_k": cae, "cond_fouling_k": ca - cae,
        "evap_approach_k": ea, "evap_approach_expected_k": eae, "evap_fouling_k": ea - eae,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    QM, QE, PE, CA, CAE, EA, EAE = _parts(twin)
    run = "(df['RUNNING'] > 0)"
    return [
        ("CHILLER_COND_FOULING", f"{run} & (({CA} - {CAE}) > {L['cond_fouling_alert_k']}) & (df['SUBCOOLING_K'] <= {L['subcooling_high_k']})", "Medium", "cond_fouling"),
        ("CHILLER_EVAP_FOULING", f"{run} & (({EA} - {EAE}) > {L['evap_fouling_alert_k']}) & (df['SUPERHEAT_K'] <= {L['superheat_high_k']})", "Medium", "evap_fouling"),
        ("CHILLER_LOW_CHARGE", f"{run} & (df['SUPERHEAT_K'] > {L['superheat_high_k']}) & (df['SUBCOOLING_K'] < {L['subcooling_low_k'] + 1.5})", "High", "low_charge"),
        ("CHILLER_NONCONDENSABLES", f"{run} & (df['SUBCOOLING_K'] > {L['subcooling_high_k']})", "Medium", "noncondensables"),
        ("CHILLER_CAPACITY_LOSS", f"{run} & ((({QM} - {QE}) / {QE}.clip(lower=1) * 100) < {L['capacity_dev_alert_pct']})", "Medium", "compressor_wear"),
        ("CHILLER_HIGH_DISCHARGE", f"df['DISCHARGE_TEMP_C'] > {L['discharge_alert_c']}", "High", None),
        ("CHILLER_OIL_FILTER", f"{run} & (df['OIL_FILTER_DP_BAR'] > {L['oil_dp_alert_bar']})", "Medium", "oil_filter"),
        ("CHILLER_CURRENT_IMBALANCE", f"{run} & (df['CURRENT_IMBALANCE_PCT'] > {L['current_imbalance_alert_pct']})", "Medium", "motor_winding"),
        ("CHILLER_WINDING_TEMP_HIGH", f"df['WINDING_TEMP_C'] > {L['winding_alert_c']}", "High", "motor_winding"),
        ("CHILLER_LOW_EFFICIENCY", f"{run} & (df['POWER_KW'] / ({QM} / {TON_KW}).clip(lower=0.5) > {L['kw_per_ton_alert']})", "Low", None),
        ("CHILLER_TRIPPED", "df['TRIP_CODE'] > 0", "Critical", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    run = r.get("running", 1) > 0
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    trips = {1: "High pressure trip", 2: "Low evaporating temperature (freeze) trip", 3: "Discharge temperature trip", 4: "Winding temperature trip"}
    add(r.get("trip_code", 0) > 0, "CHILLER_TRIPPED", "Critical", trips.get(r.get("trip_code"), "Tripped"), "compressor")
    add(run and t["cond_fouling_k"] > L["cond_fouling_alert_k"] and r["subcooling_k"] <= L["subcooling_high_k"], "CHILLER_COND_FOULING", "Medium",
        f"Condenser approach {t['cond_approach_k']:.1f} K, {t['cond_fouling_k']:.1f} K above clean", "condenser", "cond_fouling")
    add(run and t["evap_fouling_k"] > L["evap_fouling_alert_k"] and r["superheat_k"] <= L["superheat_high_k"], "CHILLER_EVAP_FOULING", "Medium",
        f"Evaporator approach {t['evap_approach_k']:.1f} K, {t['evap_fouling_k']:.1f} K above clean", "evaporator", "evap_fouling")
    add(run and r["superheat_k"] > L["superheat_high_k"] and r["subcooling_k"] < L["subcooling_low_k"] + 1.5, "CHILLER_LOW_CHARGE", "High",
        f"Superheat {r['superheat_k']:.1f} K with subcooling {r['subcooling_k']:.1f} K", "evaporator", "low_charge")
    add(run and r["subcooling_k"] > L["subcooling_high_k"], "CHILLER_NONCONDENSABLES", "Medium",
        f"Apparent subcooling {r['subcooling_k']:.1f} K: head pressure above saturation", "condenser", "noncondensables")
    add(run and t["capacity_deviation_pct"] < L["capacity_dev_alert_pct"], "CHILLER_CAPACITY_LOSS", "Medium",
        f"Capacity {t['capacity_deviation_pct']:.1f} % below BITZER data", "compressor", "compressor_wear")
    add(r["discharge_temp_c"] > L["discharge_alert_c"], "CHILLER_HIGH_DISCHARGE", "High",
        f"Discharge gas {r['discharge_temp_c']:.1f} °C", "compressor")
    add(run and r["oil_filter_dp_bar"] > L["oil_dp_alert_bar"], "CHILLER_OIL_FILTER", "Medium",
        f"Oil filter dp {r['oil_filter_dp_bar']:.2f} bar", "compressor", "oil_filter")
    add(run and r["current_imbalance_pct"] > L["current_imbalance_alert_pct"], "CHILLER_CURRENT_IMBALANCE", "Medium",
        f"Phase current imbalance {r['current_imbalance_pct']:.1f} %", "motor", "motor_winding")
    add(r["winding_temp_c"] > L["winding_alert_c"], "CHILLER_WINDING_TEMP_HIGH", "High",
        f"Winding {r['winding_temp_c']:.1f} °C", "motor", "motor_winding")
    add(run and t["kw_per_ton"] > L["kw_per_ton_alert"], "CHILLER_LOW_EFFICIENCY", "Low",
        f"{t['kw_per_ton']:.3f} kW/ton", "compressor")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
