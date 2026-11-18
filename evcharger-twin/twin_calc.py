"""The DC fast charger twin's expectations (EV-7001, alpitronic hypercharger HYC400, 4 x 100 kW, two liquid-cooled CCS2 outlets).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Conversion efficiency. The charger switches on only the Power-Stacks it needs (n active) and shares the power between them.
The loss of one stack is a no-load part plus a conduction part, fitted in build_twin.py to the two published points (97.7 % at
full load, 98.2 % peak):
      loss_stack(p) = a + c p^2                        (kW, p = kW carried by the stack)
      loss_expected(P, n) = n a + c P^2 / n            (P = total DC output, kW)
      efficiency expected = P / (P + loss_expected);  loss ratio = (P_AC - P_DC) / loss_expected
  The ratio is only judged above 50 kW, where the loss is large enough to measure with the AC and DC meters.
Power-Stack cooling: heat sink rise over the inlet air, expected = R_th x (measured loss / n). A rise above that, with the
  losses explained, points at the air path (filter, fan), not the semiconductors.
Cable cooling (liquid-cooled CCS2 cable, both cables in parallel on one cooling unit):
      heat in the cables      Q = (I1^2 + I2^2) x R_loop                        (W)
      coolant rise expected   dT = Q / (2 x flow x rho / 60 x cp)               (K, flow in l/min per cable)
  DC contact temperature: the NTC at the contact sits on the coolant, plus the I^2 heating of the contact itself:
      contact rise expected   = k x (I / 1000)^2 over the coolant return; contact ratio = measured rise / expected
  (I floored at 150 A in the denominator so that a cable at rest never gives a large ratio).
Insulation (IEC 61851-23 practice): R / V_max in ohm per volt: warning below 500, fault below 100.
Charge starts (rolling 24 h counters from the CSMS):
      success = (attempted - failed comm - failed auth - failed safety - failed other - aborted) / attempted
Uptime (23 CFR 680.116): mu = (525600 - (T_outage - T_excluded)) / 525600 x 100, required > 97 %.
Metering: deviation = (calibrated meter - charger's own measurement) / charger's own x 100 on the last completed session.
"""


def _k(twin):
    d = twin["design"]
    ch, e, th, cb, sf, av = d["charger"], d["efficiency"], d["stack_thermal"], d["cable"], d["safety"], d["availability"]
    return dict(stacks=ch["stacks"], skw=ch["stack_kw"], a=e["loss_a_kw"], c=e["loss_c_per_kw"], rth=th["r_th_k_per_kw"],
                rl=cb["r_loop_ohm"], kc=cb["contact_k_per_ka2"], rho=cb["coolant_density_kg_per_l"], cp=cb["coolant_cp_j_per_kgk"],
                qn=cb["flow_nominal_lpm"], vref=sf["insulation_ref_v"], warn=sf["insulation_warn_ohm_per_v"],
                fault=sf["insulation_fault_ohm_per_v"], mpy=av["minutes_per_year"], up=av["uptime_required_pct"])


def loss_expected(k, p, n):
    """Expected loss (kW) at total DC output p (kW) with n stacks active."""
    n = max(n, 1)
    return k["a"] * n + k["c"] * p ** 2 / n


def _parts(twin):
    k = _k(twin)
    N = "np.maximum(df['STACKS_ACTIVE'], 1)"
    DC = "((df['DC_VOLTAGE_C1_V'] * df['DC_CURRENT_C1_A'] + df['DC_VOLTAGE_C2_V'] * df['DC_CURRENT_C2_A']) / 1000)"
    LOSS = f"(df['AC_INPUT_KW'] - {DC})"
    LEXP = f"({k['a']} * {N} + {k['c']} * {DC} ** 2 / {N})"
    LR = f"({LOSS} / {LEXP})"
    SRE = f"({k['rth']} * np.maximum({LOSS}, 0) / {N})"
    SRR = f"((df['STACK_TEMP_MAX_C'] - df['AMBIENT_C']) / np.maximum({SRE}, 0.5))"
    HEAT = f"((df['DC_CURRENT_C1_A'] ** 2 + df['DC_CURRENT_C2_A'] ** 2) * {k['rl']})"
    CRE = f"({HEAT} / (2 * np.maximum(df['COOLANT_FLOW_LPM'], 0.1) * {k['rho'] / 60:.9g} * {k['cp']}))"
    CR = {i: f"((df['CONTACT_TEMP_C{i}_C'] - df['COOLANT_RETURN_C']) / ({k['kc']} * (np.maximum(df['DC_CURRENT_C{i}_A'], 150) / 1000) ** 2))"
          for i in (1, 2)}
    INS = f"(df['INSULATION_KOHM'] * 1000 / {k['vref']})"
    A = "np.maximum(df['STARTS_ATTEMPTED_24H'], 1)"
    SUC = (f"(100 * (df['STARTS_ATTEMPTED_24H'] - df['STARTS_FAILED_COMM_24H'] - df['STARTS_FAILED_AUTH_24H'] - df['STARTS_FAILED_SAFETY_24H']"
           f" - df['STARTS_FAILED_OTHER_24H'] - df['SESSIONS_ABORTED_24H']) / {A})")
    FC = f"(100 * df['STARTS_FAILED_COMM_24H'] / {A})"
    FA = f"(100 * df['STARTS_FAILED_AUTH_24H'] / {A})"
    UP = f"(({k['mpy']} - (df['OUTAGE_MIN_365D'] - df['OUTAGE_EXCLUDED_MIN_365D'])) / {k['mpy']} * 100)"
    MD = "(100 * (df['LAST_SESSION_METER_KWH'] - df['LAST_SESSION_INTERNAL_KWH']) / np.maximum(df['LAST_SESSION_INTERNAL_KWH'], 0.1))"
    return dict(k=k, N=N, DC=DC, LOSS=LOSS, LEXP=LEXP, LR=LR, SRE=SRE, SRR=SRR, HEAT=HEAT, CRE=CRE, CR1=CR[1], CR2=CR[2],
                INS=INS, SUC=SUC, FC=FC, FA=FA, UP=UP, MD=MD)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("DC_POWER_KW", p["DC"]),
        ("LOSS_KW", p["LOSS"]),
        ("LOSS_EXPECTED_KW", p["LEXP"]),
        ("EFFICIENCY_PCT", f"100 * {p['DC']} / np.maximum(df['AC_INPUT_KW'], 0.001)"),
        ("EFFICIENCY_EXPECTED_PCT", f"100 * {p['DC']} / ({p['DC']} + {p['LEXP']})"),
        ("LOSS_RATIO", p["LR"]),
        ("STACK_RISE_EXPECTED_K", p["SRE"]),
        ("STACK_RISE_RATIO", p["SRR"]),
        ("POWER_AVAILABLE_KW", f"df['STACKS_AVAILABLE'] * {k['skw']}"),
        ("CABLE_HEAT_W", p["HEAT"]),
        ("COOLANT_RISE_EXPECTED_K", p["CRE"]),
        ("COOLANT_RISE_RATIO", f"(df['COOLANT_RETURN_C'] - df['COOLANT_SUPPLY_C']) / np.maximum({p['CRE']}, 0.5)"),
        ("CONTACT_RATIO_C1", p["CR1"]),
        ("CONTACT_RATIO_C2", p["CR2"]),
        ("INSULATION_OHM_PER_V", p["INS"]),
        ("START_SUCCESS_PCT", p["SUC"]),
        ("FAIL_COMM_PCT", p["FC"]),
        ("FAIL_AUTH_PCT", p["FA"]),
        ("UPTIME_PCT", p["UP"]),
        ("METER_DEV_PCT", p["MD"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    n = max(r["stacks_active"], 1)
    dc = (r["dc_voltage_c1_v"] * r["dc_current_c1_a"] + r["dc_voltage_c2_v"] * r["dc_current_c2_a"]) / 1000
    loss = r["ac_input_kw"] - dc
    lexp = k["a"] * n + k["c"] * dc ** 2 / n
    sre = k["rth"] * max(loss, 0) / n
    heat = (r["dc_current_c1_a"] ** 2 + r["dc_current_c2_a"] ** 2) * k["rl"]
    cre = heat / (2 * max(r["coolant_flow_lpm"], 0.1) * float(f"{k['rho'] / 60:.9g}") * k["cp"])
    cr = {i: (r[f"contact_temp_c{i}_c"] - r["coolant_return_c"]) / (k["kc"] * (max(r[f"dc_current_c{i}_a"], 150) / 1000) ** 2) for i in (1, 2)}
    a = max(r["starts_attempted_24h"], 1)
    fails = (r["starts_failed_comm_24h"] + r["starts_failed_auth_24h"] + r["starts_failed_safety_24h"]
             + r["starts_failed_other_24h"] + r["sessions_aborted_24h"])
    return {
        "dc_power_kw": dc, "loss_kw": loss, "loss_expected_kw": lexp,
        "efficiency_pct": 100 * dc / max(r["ac_input_kw"], 0.001), "efficiency_expected_pct": 100 * dc / (dc + lexp),
        "loss_ratio": loss / lexp, "stack_rise_expected_k": sre,
        "stack_rise_ratio": (r["stack_temp_max_c"] - r["ambient_c"]) / max(sre, 0.5),
        "power_available_kw": r["stacks_available"] * k["skw"], "cable_heat_w": heat, "coolant_rise_expected_k": cre,
        "coolant_rise_ratio": (r["coolant_return_c"] - r["coolant_supply_c"]) / max(cre, 0.5),
        "contact_ratio_c1": cr[1], "contact_ratio_c2": cr[2],
        "insulation_ohm_per_v": r["insulation_kohm"] * 1000 / k["vref"],
        "start_success_pct": 100 * (r["starts_attempted_24h"] - fails) / a,
        "fail_comm_pct": 100 * r["starts_failed_comm_24h"] / a, "fail_auth_pct": 100 * r["starts_failed_auth_24h"] / a,
        "uptime_pct": (k["mpy"] - (r["outage_min_365d"] - r["outage_excluded_min_365d"])) / k["mpy"] * 100,
        "meter_dev_pct": 100 * (r["last_session_meter_kwh"] - r["last_session_internal_kwh"]) / max(r["last_session_internal_kwh"], 0.1),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    att = f"(df['STARTS_ATTEMPTED_24H'] >= {L['min_attempts']})"
    return [
        ("CHG_INSULATION_FAULT", f"{p['INS']} < {k['fault']}", "Critical", "insulation_degradation"),
        ("CHG_CONTACTOR_WELDED", "df['CONTACTOR_WELD'] > 0.5", "Critical", "contactor_welded"),
        ("CHG_STACK_DERATED", f"df['STACKS_AVAILABLE'] < {k['stacks'] - 0.5}", "High", "power_stack_failure"),
        ("CHG_COOLANT_FLOW_LOW", f"df['COOLANT_FLOW_LPM'] < {L['coolant_flow_min_lpm']}", "High", "coolant_flow_low"),
        ("CHG_CONTACT_TEMP_HIGH", f"np.maximum(df['CONTACT_TEMP_C1_C'], df['CONTACT_TEMP_C2_C']) > {L['contact_temp_alert_c']}", "High", "contact_wear"),
        ("CHG_UPTIME_LOW", f"{p['UP']} < {k['up']}", "High", "contactor_welded"),
        ("CHG_SUCCESS_LOW", f"{att} & ({p['SUC']} < {L['success_min_pct']})", "High", None),
        ("CHG_PAYMENT_OFFLINE", f"(df['PAYMENT_TERMINAL_OK'] < 0.5) | (df['OCPP_HEARTBEAT_AGE_S'] > {L['heartbeat_max_s']})", "High", "payment_backend_fault"),
        ("CHG_EFFICIENCY_LOW", f"({p['DC']} >= {L['min_power_for_eff_kw']}) & ({p['LR']} > {L['loss_ratio_alert']})", "Medium", "stack_cooling_ageing"),
        ("CHG_STACK_HOT", f"({p['DC']} >= {L['min_power_for_eff_kw']}) & ({p['SRR']} > {L['stack_rise_ratio_alert']})", "Medium", "stack_cooling_ageing"),
        ("CHG_CONTACT_WEAR", f"np.maximum({p['CR1']}, {p['CR2']}) > {L['contact_ratio_alert']}", "Medium", "contact_wear"),
        ("CHG_INSULATION_WARN", f"({p['INS']} >= {k['fault']}) & ({p['INS']} < {k['warn']})", "Medium", "insulation_degradation"),
        ("CHG_FAIL_COMM", f"{att} & ({p['FC']} > {L['fail_reason_max_pct']})", "Medium", "vehicle_comm_failures"),
        ("CHG_FAIL_AUTH", f"{att} & ({p['FA']} > {L['fail_reason_max_pct']})", "Medium", "payment_backend_fault"),
        ("CHG_METER_DEVIATION", f"np.abs({p['MD']}) > {L['meter_dev_max_pct']}", "Medium", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    att = r["starts_attempted_24h"] >= L["min_attempts"]
    dc_ok = t["dc_power_kw"] >= L["min_power_for_eff_kw"]
    ins = t["insulation_ohm_per_v"]
    tmax = max(r["contact_temp_c1_c"], r["contact_temp_c2_c"])
    crm = max(t["contact_ratio_c1"], t["contact_ratio_c2"])
    add(ins < k["fault"], "CHG_INSULATION_FAULT", "Critical",
        f"Insulation {r['insulation_kohm']:.0f} kΩ = {ins:.0f} Ω/V, below {k['fault']:.0f} Ω/V: the charger must not start", "cable", "insulation_degradation")
    add(r["contactor_weld"] > 0.5, "CHG_CONTACTOR_WELDED", "Critical", "Welded DC contactor detected: outlet 2 locked out", "contactor", "contactor_welded")
    add(r["stacks_available"] < k["stacks"] - 0.5, "CHG_STACK_DERATED", "High",
        f"{r['stacks_available']:.0f} of {k['stacks']} Power-Stacks available: {t['power_available_kw']:.0f} kW left", "power stack", "power_stack_failure")
    add(r["coolant_flow_lpm"] < L["coolant_flow_min_lpm"], "CHG_COOLANT_FLOW_LOW", "High",
        f"Coolant flow {r['coolant_flow_lpm']:.2f} l/min per cable, below {L['coolant_flow_min_lpm']}", "cooling unit", "coolant_flow_low")
    add(tmax > L["contact_temp_alert_c"], "CHG_CONTACT_TEMP_HIGH", "High",
        (f"DC contact at {tmax:.0f} °C, {k_off(twin) - tmax:.0f} K below the {k_off(twin):.0f} °C switch-off" if tmax < k_off(twin)
         else f"DC contact at {tmax:.0f} °C, at or above the {k_off(twin):.0f} °C switch-off: the charger must derate"), "connector", "contact_wear")
    add(t["uptime_pct"] < k["up"], "CHG_UPTIME_LOW", "High", f"Uptime {t['uptime_pct']:.2f} % over 365 days, below {k['up']:.0f} %", "availability", "contactor_welded")
    add(att and t["start_success_pct"] < L["success_min_pct"], "CHG_SUCCESS_LOW", "High",
        f"Only {t['start_success_pct']:.0f} % of {r['starts_attempted_24h']:.0f} charge starts succeeded in 24 h", "sessions")
    add(r["payment_terminal_ok"] < 0.5 or r["ocpp_heartbeat_age_s"] > L["heartbeat_max_s"], "CHG_PAYMENT_OFFLINE", "High",
        f"Payment terminal {'offline' if r['payment_terminal_ok'] < 0.5 else 'online'}, last OCPP message {r['ocpp_heartbeat_age_s']:.0f} s ago",
        "payment", "payment_backend_fault")
    add(dc_ok and t["loss_ratio"] > L["loss_ratio_alert"], "CHG_EFFICIENCY_LOW", "Medium",
        f"Loss {t['loss_kw']:.2f} kW at {t['dc_power_kw']:.0f} kW, {t['loss_ratio']:.2f} x the efficiency curve", "power stack", "stack_cooling_ageing")
    add(dc_ok and t["stack_rise_ratio"] > L["stack_rise_ratio_alert"], "CHG_STACK_HOT", "Medium",
        f"Heat sinks {r['stack_temp_max_c'] - r['ambient_c']:.0f} K over the air, {t['stack_rise_ratio']:.2f} x what the losses explain", "power stack", "stack_cooling_ageing")
    add(crm > L["contact_ratio_alert"], "CHG_CONTACT_WEAR", "Medium",
        f"DC contact heats {crm:.2f} x faster with current than a clean contact", "connector", "contact_wear")
    add(k["fault"] <= ins < k["warn"], "CHG_INSULATION_WARN", "Medium", f"Insulation {ins:.0f} Ω/V, below the {k['warn']:.0f} Ω/V warning", "cable", "insulation_degradation")
    add(att and t["fail_comm_pct"] > L["fail_reason_max_pct"], "CHG_FAIL_COMM", "Medium",
        f"{r['starts_failed_comm_24h']:.0f} starts ({t['fail_comm_pct']:.0f} %) failed in the vehicle handshake", "communication", "vehicle_comm_failures")
    add(att and t["fail_auth_pct"] > L["fail_reason_max_pct"], "CHG_FAIL_AUTH", "Medium",
        f"{r['starts_failed_auth_24h']:.0f} starts ({t['fail_auth_pct']:.0f} %) failed at authorisation or payment", "payment", "payment_backend_fault")
    add(abs(t["meter_dev_pct"]) > L["meter_dev_max_pct"], "CHG_METER_DEVIATION", "Medium",
        f"Billing meter and charger differ by {t['meter_dev_pct']:+.2f} % on the last session", "meter")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health


def k_off(twin):
    return twin["design"]["cable"]["contact_switch_off_c"]
