"""The supermarket refrigeration rack twin's expectations (RF-6901, 4 x Danfoss MTZ160-4, R448A, medium temperature).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Saturation temperatures from the measured pressures (R448A is a zeotropic blend: dew and bubble differ by about 6 K):
    T = B / (A - ln p) - C          p in bar a = gauge + 1.01325; one (A, B, C) for the dew line, one for the bubble line
    to = dew(suction), tc = dew(discharge)  (EN 12900 rates compressors at dew-point temperatures)
    superheat = suction gas temperature - to;   subcooling = bubble(discharge) - liquid temperature
Compressor (EN 12900 10-coefficient polynomial per compressor, SH 10 K, SC 0 K):
    X(to, tc) = c1 + c2 to + c3 tc + c4 to^2 + c5 to tc + c6 tc^2 + c7 to^3 + c8 tc to^2 + c9 to tc^2 + c10 tc^3
    running compressors N = capacity % / 100 x 4;  Q_exp = N Q(to, tc),  P_exp = N P(to, tc)
    power ratio = measured power / P_exp;   COP as operated = Q_exp / measured power
Discharge temperature (fitted to the compressor model): T_dis = (T_suc + 273.15) x (p_dis / p_suc)^m - 273.15 (absolute pressures)
Condenser: approach = tc - ambient;  expected = A_d x (Q_exp + P) / Q_rej,d  (heat rejected against the design point).
    The rule only looks when tc is above the minimum of the floating head pressure (+0.5 K): below it the control, not the
    coil, sets the approach.
Charge (receiver level of a tight system, learned): L_exp = L0 + a (T_amb - 20) + b (capacity - 0.6)
    charge deficit (kg) = (L_exp - L) / 100 x V_receiver x rho_liq(T_liquid)
    leak rate (kg/yr) = max(deficit, 0) x 365 / days since the last top-up;  CO2e (t/yr) = leak rate x GWP / 1000
Cold room: coil TD = room air - to (rack suction);  HACCP margin = product limit - warmest product probe.
"""

ABS = 273.15


def _k(twin):
    d = twin["design"]
    c, r, rk, cd, rc, fg, cr = (d[x] for x in ("compressor", "refrigerant", "rack", "condenser", "receiver", "fgas", "coldroom"))
    return dict(n=c["count"], cq=c["poly_q_kw"], cp=c["poly_p_kw"], m=c["discharge_m"], tdmax=c["t_dis_max_c"],
                patm=r["p_atm_bar"], dew=r["dew"], bub=r["bubble"], rho=r["rho_liq_poly"], gwp=r["gwp"],
                tcmin=rk["tc_min_c"], ad=cd["approach_design_k"], qrej=cd["rejection_design_kw"],
                vrec=rc["volume_m3"], l0=rc["level_normal_pct"], la=rc["level_per_k_amb"], ll=rc["level_per_capacity"],
                aref=rc["amb_ref_c"], cref=rc["capacity_ref"], charge=rc["charge_kg"],
                lci=fg["leak_check_interval_d"], lra=fg["leak_rate_alert_pct_yr"],
                tdd=cr["td_design_k"], plim=cr["product_limit_c"], door=cr["door_alert_min_h"])


# plain-Python helpers (also used by physics.py and the figures) ---------------------------------------------------------------
def poly(c, to, tc):
    return (c[0] + c[1] * to + c[2] * tc + c[3] * to ** 2 + c[4] * to * tc + c[5] * tc ** 2 + c[6] * to ** 3
            + c[7] * tc * to ** 2 + c[8] * to * tc ** 2 + c[9] * tc ** 3)


def t_sat(f, p_abs):
    import math
    return f["B"] / (f["A"] - math.log(p_abs)) - f["C"]


def p_sat(f, t_c):
    import math
    return math.exp(f["A"] - f["B"] / (t_c + f["C"]))


def rho_liq(k, t):
    a2, a1, a0 = k["rho"]
    return a2 * t * t + a1 * t + a0


def _p(c, to, tc):
    return (f"({c[0]!r} + {c[1]!r} * {to} + {c[2]!r} * {tc} + {c[3]!r} * {to} ** 2 + {c[4]!r} * {to} * {tc} + {c[5]!r} * {tc} ** 2"
            f" + {c[6]!r} * {to} ** 3 + {c[7]!r} * {tc} * {to} ** 2 + {c[8]!r} * {to} * {tc} ** 2 + {c[9]!r} * {tc} ** 3)")


def _parts(twin):
    k = _k(twin)
    sat = lambda f, col: f"({f['B']!r} / ({f['A']!r} - np.log(df['{col}'] + {k['patm']!r})) - {f['C']!r})"
    TO, TC, TB = sat(k["dew"], "SUCTION_PRESSURE_BARG"), sat(k["dew"], "DISCHARGE_PRESSURE_BARG"), sat(k["bub"], "DISCHARGE_PRESSURE_BARG")
    N = f"(df['CAPACITY_PCT'] / 100 * {k['n']})"
    QE = f"({N} * {_p(k['cq'], TO, TC)})"
    PE = f"({N} * {_p(k['cp'], TO, TC)})"
    PR = (f"((df['DISCHARGE_PRESSURE_BARG'] + {k['patm']!r}) / (df['SUCTION_PRESSURE_BARG'] + {k['patm']!r}))")
    TDE = f"((df['SUCTION_TEMP_C'] + {ABS}) * {PR} ** {k['m']!r} - {ABS})"
    AP = f"({TC} - df['AMBIENT_TEMP_C'])"
    APE = f"({k['ad']!r} * ({QE} + df['RACK_POWER_KW']) / {k['qrej']!r})"
    LE = f"({k['l0']!r} + {k['la']!r} * (df['AMBIENT_TEMP_C'] - {k['aref']!r}) + {k['ll']!r} * (df['CAPACITY_PCT'] / 100 - {k['cref']!r}))"
    a2, a1, a0 = k["rho"]
    RHO = f"({a2!r} * df['LIQUID_TEMP_C'] ** 2 + {a1!r} * df['LIQUID_TEMP_C'] + {a0!r})"
    DEF = f"(({LE} - df['RECEIVER_LEVEL_PCT']) / 100 * {k['vrec']!r} * {RHO})"
    LR = f"(np.maximum({DEF}, 0) * 365 / np.maximum(df['DAYS_SINCE_TOPUP'], 1))"
    return dict(k=k, TO=TO, TC=TC, TB=TB, QE=QE, PE=PE, TDE=TDE, AP=AP, APE=APE, LE=LE, DEF=DEF, LR=LR)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("TO_DEW_C", p["TO"]),
        ("TC_DEW_C", p["TC"]),
        ("TC_BUBBLE_C", p["TB"]),
        ("SUPERHEAT_K", f"df['SUCTION_TEMP_C'] - {p['TO']}"),
        ("SUBCOOLING_K", f"{p['TB']} - df['LIQUID_TEMP_C']"),
        ("Q_EXPECTED_KW", p["QE"]),
        ("P_EXPECTED_KW", p["PE"]),
        ("POWER_RATIO", f"df['RACK_POWER_KW'] / np.maximum({p['PE']}, 1.0)"),
        ("COP_OPS", f"{p['QE']} / np.maximum(df['RACK_POWER_KW'], 1.0)"),
        ("T_DISCHARGE_EXPECTED_C", p["TDE"]),
        ("T_DISCHARGE_RESIDUAL_K", f"df['DISCHARGE_TEMP_C'] - {p['TDE']}"),
        ("COND_APPROACH_K", p["AP"]),
        ("COND_APPROACH_EXPECTED_K", p["APE"]),
        ("RECEIVER_LEVEL_EXPECTED_PCT", p["LE"]),
        ("CHARGE_DEFICIT_KG", p["DEF"]),
        ("LEAK_RATE_KG_YR", p["LR"]),
        ("LEAK_CO2E_T_YR", f"{p['LR']} * {k['gwp']} / 1000"),
        ("COIL_TD_K", f"df['ROOM_AIR_C'] - {p['TO']}"),
        ("PRODUCT_MARGIN_K", f"{k['plim']!r} - df['PRODUCT_TEMP_C']"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    pa = k["patm"]
    ps, pd = r["suction_pressure_barg"] + pa, r["discharge_pressure_barg"] + pa
    to, tc, tb = t_sat(k["dew"], ps), t_sat(k["dew"], pd), t_sat(k["bub"], pd)
    n = r["capacity_pct"] / 100 * k["n"]
    qe, pe = n * poly(k["cq"], to, tc), n * poly(k["cp"], to, tc)
    tde = (r["suction_temp_c"] + ABS) * (pd / ps) ** k["m"] - ABS
    amb = r["ambient_temp_c"]
    ape = k["ad"] * (qe + r["rack_power_kw"]) / k["qrej"]
    le = k["l0"] + k["la"] * (amb - k["aref"]) + k["ll"] * (r["capacity_pct"] / 100 - k["cref"])
    dfc = (le - r["receiver_level_pct"]) / 100 * k["vrec"] * rho_liq(k, r["liquid_temp_c"])
    lr = max(dfc, 0) * 365 / max(r["days_since_topup"], 1)
    return {
        "to_dew_c": to, "tc_dew_c": tc, "tc_bubble_c": tb,
        "superheat_k": r["suction_temp_c"] - to, "subcooling_k": tb - r["liquid_temp_c"],
        "q_expected_kw": qe, "p_expected_kw": pe, "power_ratio": r["rack_power_kw"] / max(pe, 1.0),
        "cop_ops": qe / max(r["rack_power_kw"], 1.0),
        "t_discharge_expected_c": tde, "t_discharge_residual_k": r["discharge_temp_c"] - tde,
        "cond_approach_k": tc - amb, "cond_approach_expected_k": ape,
        "receiver_level_expected_pct": le, "charge_deficit_kg": dfc, "leak_rate_kg_yr": lr, "leak_co2e_t_yr": lr * k["gwp"] / 1000,
        "coil_td_k": r["room_air_c"] - to, "product_margin_k": k["plim"] - r["product_temp_c"],
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    ex = dict(monitor_expressions(twin))
    return [
        ("RF_PRODUCT_TEMP_HIGH", f"df['PRODUCT_TEMP_C'] > {k['plim']!r}", "High", "door_left_open"),
        ("RF_RECEIVER_LOW", f"df['RECEIVER_LEVEL_PCT'] < {L['receiver_low_pct']!r}", "High", "refrigerant_leak"),
        ("RF_LEAK_RATE_HIGH", f"{p['LR']} > {k['lra'] / 100 * k['charge']!r}", "High", "refrigerant_leak"),
        ("RF_SUPERHEAT_LOW", f"({ex['SUPERHEAT_K']}) < {L['superheat_low_k']!r}", "High", "superheat_drift"),
        ("RF_DISCHARGE_TEMP_LIMIT", f"df['DISCHARGE_TEMP_C'] > {k['tdmax']!r}", "High", None),
        ("RF_CHARGE_LOSS", f"{p['DEF']} > {L['charge_loss_alert_kg']!r}", "Medium", "refrigerant_leak"),
        ("RF_SUBCOOLING_LOW", f"({ex['SUBCOOLING_K']}) < {L['subcooling_low_k']!r}", "Medium", "refrigerant_leak"),
        ("RF_DISCHARGE_TEMP_HIGH", f"({ex['T_DISCHARGE_RESIDUAL_K']}) > {L['discharge_residual_alert_k']!r}", "Medium", "compressor_valve_wear"),
        ("RF_POWER_HIGH", f"{ex['POWER_RATIO']} > {L['power_ratio_alert']!r}", "Medium", "compressor_mechanical"),
        ("RF_COND_APPROACH_HIGH", f"({p['TC']} > {k['tcmin'] + 0.5!r}) & ({p['AP']} > {L['approach_ratio_alert']!r} * {p['APE']})", "Medium", "condenser_fouled"),
        ("RF_COIL_TD_HIGH", f"({ex['COIL_TD_K']}) > {k['tdd'] + L['coil_td_margin_k']!r}", "Medium", "evaporator_icing"),
        ("RF_DEFROST_ON_TIME", "df['DEFROST_END_ON_TEMP'] < 0.5", "Medium", "evaporator_icing"),
        ("RF_DOOR_OPEN_LONG", f"df['DOOR_OPEN_MIN_H'] > {k['door']!r}", "Medium", "door_left_open"),
        ("RF_LEAK_CHECK_OVERDUE", f"df['DAYS_SINCE_LEAK_CHECK'] > {k['lci']!r}", "Low", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    add(r["product_temp_c"] > k["plim"], "RF_PRODUCT_TEMP_HIGH", "High",
        f"Warmest product {r['product_temp_c']:.1f} °C, above the {k['plim']:.0f} °C critical limit of the HACCP plan", "coldroom", "door_left_open")
    add(r["receiver_level_pct"] < L["receiver_low_pct"], "RF_RECEIVER_LOW", "High",
        f"Receiver level {r['receiver_level_pct']:.0f} %: the liquid seal is about to be lost", "receiver", "refrigerant_leak")
    add(t["leak_rate_kg_yr"] > k["lra"] / 100 * k["charge"], "RF_LEAK_RATE_HIGH", "High",
        f"Leaking {t['leak_rate_kg_yr']:.0f} kg/yr = {t['leak_co2e_t_yr']:.0f} t CO2e/yr ({t['leak_rate_kg_yr'] / k['charge'] * 100:.0f} % of the charge per year)", "circuit", "refrigerant_leak")
    add(t["superheat_k"] < L["superheat_low_k"], "RF_SUPERHEAT_LOW", "High",
        f"Suction superheat {t['superheat_k']:.1f} K: risk of liquid reaching the compressors", "expansion", "superheat_drift")
    add(r["discharge_temp_c"] > k["tdmax"], "RF_DISCHARGE_TEMP_LIMIT", "High",
        f"Discharge gas {r['discharge_temp_c']:.0f} °C, above the maker's {k['tdmax']:.0f} °C", "compressor")
    add(t["charge_deficit_kg"] > L["charge_loss_alert_kg"], "RF_CHARGE_LOSS", "Medium",
        f"Receiver {r['receiver_level_pct']:.0f} % against {t['receiver_level_expected_pct']:.0f} % expected: about {t['charge_deficit_kg']:.0f} kg of R448A missing", "circuit", "refrigerant_leak")
    add(t["subcooling_k"] < L["subcooling_low_k"], "RF_SUBCOOLING_LOW", "Medium",
        f"Liquid subcooling {t['subcooling_k']:.1f} K: flash gas in the liquid line", "receiver", "refrigerant_leak")
    add(t["t_discharge_residual_k"] > L["discharge_residual_alert_k"], "RF_DISCHARGE_TEMP_HIGH", "Medium",
        f"Discharge {r['discharge_temp_c']:.0f} °C, {t['t_discharge_residual_k']:.0f} K above the expected {t['t_discharge_expected_c']:.0f} °C", "compressor", "compressor_valve_wear")
    add(t["power_ratio"] > L["power_ratio_alert"], "RF_POWER_HIGH", "Medium",
        f"Compressors draw {r['rack_power_kw']:.1f} kW, {t['power_ratio']:.2f} × the maker's polynomial at this to/tc", "compressor", "compressor_mechanical")
    add(t["tc_dew_c"] > k["tcmin"] + 0.5 and t["cond_approach_k"] > L["approach_ratio_alert"] * t["cond_approach_expected_k"], "RF_COND_APPROACH_HIGH", "Medium",
        f"Condensing {t['tc_dew_c']:.1f} °C, {t['cond_approach_k']:.1f} K above ambient (expected {t['cond_approach_expected_k']:.1f} K)", "condenser", "condenser_fouled")
    add(t["coil_td_k"] > k["tdd"] + L["coil_td_margin_k"], "RF_COIL_TD_HIGH", "Medium",
        f"Cold room air {r['room_air_c']:.1f} °C, {t['coil_td_k']:.1f} K above the suction (design {k['tdd']:.0f} K): coil iced", "evaporator", "evaporator_icing")
    add(r["defrost_end_on_temp"] < 0.5, "RF_DEFROST_ON_TIME", "Medium",
        f"Last defrost ran {r['defrost_duration_min']:.0f} min and ended on time, not on coil temperature", "evaporator", "evaporator_icing")
    add(r["door_open_min_h"] > k["door"], "RF_DOOR_OPEN_LONG", "Medium",
        f"Cold room door open {r['door_open_min_h']:.0f} min in the last hour", "coldroom", "door_left_open")
    add(r["days_since_leak_check"] > k["lci"], "RF_LEAK_CHECK_OVERDUE", "Low",
        f"Last F-gas leak check {r['days_since_leak_check']:.0f} days ago (interval {k['lci']:.0f} days)", "circuit")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
