"""The battery energy storage container twin's expectations (BESS-3501, 1416 kWh LFP, BMS, HVAC, PCS).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Cells (the BMS sends the extremes):
  string current          I_str = I / 4
  spread now (mV)         = (V_cell max - V_cell min) x 1000
  extra resistance (mOhm) = (spread now - spread at the last rest) / max(|I_str|, 10)
      A cell that is out of balance shows its offset at rest and under load alike; a weak (high-resistance) cell adds
      R x I under load only. Subtracting the rest spread leaves the resistance part.
Heat and HVAC:
  battery heat (kW) = 4 x I_str^2 x R_string / 1000
  heat load (kW)    = battery heat + internal auxiliaries + UA x (T_ambient - T_return)
  cooling (kW)      = rho.cp x airflow / 3600 x (T_return - T_supply)
  capacity (kW)     = Q_35 x (1 - d x (T_ambient - 35));  load ratio = heat load / capacity
  COP               = cooling / HVAC power;  expected COP = COP_35 x (1 - s x (T_ambient - 35))
State of health (capacity fade = calendar + cycle, both doubling every 15 K):
  f_T       = 2 ^ ((T_life - 25) / 15)
  SOH model = 100 - f_T x (k_cal x sqrt(days / 365) + k_cyc x EFC)
  fade rate = f_T x (k_cyc x EFC per year + k_cal / (2 sqrt(years))) x (100 - SOH_BMS) / (100 - SOH model)
  years to augmentation = (SOH_BMS - SOH_min) / fade rate,  SOH_min = E_required / (E_nameplate x DoD)
PCS and round trip:
  PCS loss = |P_dc - P_ac|;  expected loss = P0 + k x P_ac^2;  efficiency = 1 - loss / max(|P_dc|, |P_ac|)
  RTE (AC to AC, last 24 h) = E_discharged / E_charged;  expected RTE = eta_PCS^2 x eta_dc,discharge x eta_dc,charge at rated power
"""


def _k(twin):
    d = twin["design"]
    c, e, h, a, s, sf, ce = d["container"], d["electrical"], d["hvac"], d["ageing"], d["service"], d["safety"], d["cell"]
    k = dict(nom=c["nameplate_kwh"], ns=c["strings"], nc=c["cells_series"], dod=c["dod"], vmaxc=ce["v_max"], vminc=ce["v_min"],
             vnom=c["cells_series"] * ce["nominal_v"], rstr=e["r_string_ohm"], prated=e["pcs_rated_kw"], p0=e["pcs_noload_kw"],
             kl=(e["pcs_loss_rated_kw"] - e["pcs_noload_kw"]) / e["pcs_rated_kw"] ** 2,
             q35=h["cooling_kw_35c"], der=h["derate_per_k"], cop35=h["cop_35c"], cops=h["cop_slope_per_k"], sup=h["supply_setpoint_c"],
             air=h["airflow_m3h"], aux=h["aux_internal_kw"], ua=h["ua_kw_per_k"], rcp=h["rho_cp_kj_m3k"],
             kcyc=a["k_cyc_pct_per_efc"], kcal=a["k_cal_pct_sqrt_year"], tref=a["t_ref_c"], tdbl=a["t_double_k"],
             ereq=s["required_usable_kwh"], lead=s["augment_lead_years"],
             imd=sf["imd_ohm_per_v"] * c["dc_v_max"] / 1000.0)
    k["sohmin"] = k["ereq"] / (k["nom"] * k["dod"]) * 100
    k["istr_rated"] = k["prated"] * 1000 / (k["vnom"] * k["ns"])
    k.update(rte_parts(k, 1.0, 1.0))
    return k


def rte_parts(k, p_frac=1.0, loss_factor=1.0):
    """Round-trip efficiency (AC to AC) of one full cycle at p_frac x rated power, PCS losses x loss_factor."""
    p = k["prated"] * p_frac
    eta_pcs = 1 - loss_factor * (k["p0"] + k["kl"] * p ** 2) / p
    x = (p * 1000 / (k["vnom"] * k["ns"])) * k["rstr"] / k["vnom"]
    eta_dis, eta_ch = 1 - x, 1 / (1 + x)
    return dict(eta_pcs=eta_pcs, eta_dis=eta_dis, eta_ch=eta_ch, rte=eta_pcs ** 2 * eta_dis * eta_ch * 100)


def _parts(twin):
    k = _k(twin)
    ISTR = "(df['DC_CURRENT_A'] / 4)"
    SPR = "((df['CELL_V_MAX_V'] - df['CELL_V_MIN_V']) * 1000)"
    RX = f"(({SPR} - df['CELL_V_SPREAD_REST_MV']) / np.maximum(np.abs({ISTR}), 10))"
    TSP = "(df['CELL_T_MAX_C'] - df['CELL_T_MIN_C'])"
    BH = f"({k['ns']} * {ISTR} ** 2 * {k['rstr']} / 1000)"
    HL = f"({BH} + {k['aux']} + {k['ua']} * (df['AMBIENT_C'] - df['HVAC_RETURN_AIR_C']))"
    CO = f"({k['rcp'] / 3600!r} * df['HVAC_AIRFLOW_M3H'] * (df['HVAC_RETURN_AIR_C'] - df['HVAC_SUPPLY_AIR_C']))"
    CAP = f"({k['q35']} * (1 - {k['der']} * (df['AMBIENT_C'] - 35)))"
    COP = f"({CO} / np.maximum(df['HVAC_POWER_KW'], 0.1))"
    COPE = f"({k['cop35']} * (1 - {k['cops']} * (df['AMBIENT_C'] - 35)))"
    FT = f"np.power(2.0, (df['LIFE_CELL_TEMP_AVG_C'] - {k['tref']}) / {k['tdbl']})"
    DAYS = "np.maximum(df['DAYS_IN_SERVICE'], 1)"
    SOHM = f"(100 - {FT} * ({k['kcal']} * np.sqrt({DAYS} / 365) + {k['kcyc']!r} * df['EFC_COUNT']))"
    RATE = (f"({FT} * ({k['kcyc']!r} * df['EFC_COUNT'] / {DAYS} * 365 + {k['kcal']} / (2 * np.sqrt({DAYS} / 365)))"
            f" * np.maximum(100 - df['SOH_BMS_PCT'], 0.1) / (100 - {SOHM}))")
    YTA = f"((df['SOH_BMS_PCT'] - {k['sohmin']!r}) / {RATE})"
    RTE = "(df['ENERGY_DISCHARGED_24H_KWH'] / np.maximum(df['ENERGY_CHARGED_24H_KWH'], 1) * 100)"
    PL = "np.abs(df['PCS_DC_POWER_KW'] - df['AC_POWER_KW'])"
    PLR = f"({PL} / ({k['p0']} + {k['kl']!r} * df['AC_POWER_KW'] ** 2))"
    PEFF = f"(100 * (1 - {PL} / np.maximum(np.maximum(np.abs(df['PCS_DC_POWER_KW']), np.abs(df['AC_POWER_KW'])), 1)))"
    return dict(k=k, ISTR=ISTR, SPR=SPR, RX=RX, TSP=TSP, BH=BH, HL=HL, CO=CO, CAP=CAP, COP=COP, COPE=COPE, SOHM=SOHM,
                RATE=RATE, YTA=YTA, RTE=RTE, PL=PL, PLR=PLR, PEFF=PEFF)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("STRING_CURRENT_A", p["ISTR"]),
        ("CELL_V_SPREAD_MV", p["SPR"]),
        ("CELL_R_EXCESS_MOHM", p["RX"]),
        ("CELL_T_SPREAD_C", p["TSP"]),
        ("BATTERY_HEAT_KW", p["BH"]),
        ("HEAT_LOAD_KW", p["HL"]),
        ("HVAC_COOLING_KW", p["CO"]),
        ("HVAC_CAPACITY_KW", p["CAP"]),
        ("HVAC_LOAD_RATIO", f"{p['HL']} / {p['CAP']}"),
        ("HVAC_COP", p["COP"]),
        ("HVAC_COP_RATIO", f"{p['COP']} / {p['COPE']}"),
        ("SOH_MODEL_PCT", p["SOHM"]),
        ("SOH_RESIDUAL_PCT", f"df['SOH_BMS_PCT'] - {p['SOHM']}"),
        ("USABLE_ENERGY_KWH", f"{k['nom'] * k['dod']:.6g} * df['SOH_BMS_PCT'] / 100"),
        ("SOH_FADE_PCT_PER_YEAR", p["RATE"]),
        ("YEARS_TO_AUGMENT", p["YTA"]),
        ("RTE_AC_PCT", p["RTE"]),
        ("PCS_LOSS_KW", p["PL"]),
        ("PCS_LOSS_RATIO", p["PLR"]),
        ("PCS_EFFICIENCY_PCT", p["PEFF"]),
    ]


def evaluate(twin, r):
    import math
    k = _k(twin)
    istr = r["dc_current_a"] / 4
    spr = (r["cell_v_max_v"] - r["cell_v_min_v"]) * 1000
    rx = (spr - r["cell_v_spread_rest_mv"]) / max(abs(istr), 10)
    bh = k["ns"] * istr ** 2 * k["rstr"] / 1000
    hl = bh + k["aux"] + k["ua"] * (r["ambient_c"] - r["hvac_return_air_c"])
    co = k["rcp"] / 3600 * r["hvac_airflow_m3h"] * (r["hvac_return_air_c"] - r["hvac_supply_air_c"])
    cap = k["q35"] * (1 - k["der"] * (r["ambient_c"] - 35))
    cop = co / max(r["hvac_power_kw"], 0.1)
    cope = k["cop35"] * (1 - k["cops"] * (r["ambient_c"] - 35))
    ft = 2.0 ** ((r["life_cell_temp_avg_c"] - k["tref"]) / k["tdbl"])
    days = max(r["days_in_service"], 1)
    sohm = 100 - ft * (k["kcal"] * math.sqrt(days / 365) + k["kcyc"] * r["efc_count"])
    rate = (ft * (k["kcyc"] * r["efc_count"] / days * 365 + k["kcal"] / (2 * math.sqrt(days / 365)))
            * max(100 - r["soh_bms_pct"], 0.1) / (100 - sohm))
    pl = abs(r["pcs_dc_power_kw"] - r["ac_power_kw"])
    return {
        "string_current_a": istr, "cell_v_spread_mv": spr, "cell_r_excess_mohm": rx,
        "cell_t_spread_c": r["cell_t_max_c"] - r["cell_t_min_c"], "battery_heat_kw": bh, "heat_load_kw": hl,
        "hvac_cooling_kw": co, "hvac_capacity_kw": cap, "hvac_load_ratio": hl / cap, "hvac_cop": cop, "hvac_cop_ratio": cop / cope,
        "soh_model_pct": sohm, "soh_residual_pct": r["soh_bms_pct"] - sohm,
        "usable_energy_kwh": k["nom"] * k["dod"] * r["soh_bms_pct"] / 100,
        "soh_fade_pct_per_year": rate, "years_to_augment": (r["soh_bms_pct"] - k["sohmin"]) / rate,
        "rte_ac_pct": r["energy_discharged_24h_kwh"] / max(r["energy_charged_24h_kwh"], 1) * 100,
        "pcs_loss_kw": pl, "pcs_loss_ratio": pl / (k["p0"] + k["kl"] * r["ac_power_kw"] ** 2),
        "pcs_efficiency_pct": 100 * (1 - pl / max(abs(r["pcs_dc_power_kw"]), abs(r["ac_power_kw"]), 1)),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    return [
        ("BESS_OFFGAS_DETECTED", f"(df['OFFGAS_PPM'] > {L['offgas_alert_ppm']}) | (df['GAS_LEL_PCT'] > {L['lel_alert_pct']})", "Critical", "thermal_runaway_precursor"),
        ("BESS_CELL_TEMP_RATE", f"df['CELL_T_MAX_RATE_C_MIN'] > {L['temp_rate_alert_c_min']}", "Critical", "thermal_runaway_precursor"),
        ("BESS_CELL_TEMP_HIGH", f"df['CELL_T_MAX_C'] > {L['cell_temp_alert_c']}", "High", None),
        ("BESS_CELL_V_LIMIT", f"(df['CELL_V_MAX_V'] > {k['vmaxc']}) | (df['CELL_V_MIN_V'] < {k['vminc']})", "High", None),
        ("BESS_INSULATION_LOW", f"df['INSULATION_KOHM'] < {k['imd']:.6g}", "High", "insulation_fault"),
        ("BESS_HVAC_MARGIN_LOW", f"{p['HL']} / {p['CAP']} > {L['hvac_load_alert']}", "High", None),
        ("BESS_WEAK_CELL_R", f"({p['RX']} > {L['r_excess_alert_mohm']}) & (np.abs({p['ISTR']}) > {L['min_string_current_a']})", "High", "weak_module"),
        ("BESS_CELL_T_SPREAD_HIGH", f"{p['TSP']} > {L['t_spread_alert_c']}", "Medium", "weak_module"),
        ("BESS_CELL_IMBALANCE", f"df['CELL_V_SPREAD_REST_MV'] > {L['rest_spread_alert_mv']}", "Medium", "cell_imbalance"),
        ("BESS_HVAC_COP_LOW", f"{p['COP']} / {p['COPE']} < {L['cop_ratio_alert']}", "Medium", "hvac_degraded"),
        ("BESS_HVAC_SUPPLY_HIGH", f"(df['HVAC_SUPPLY_AIR_C'] - {k['sup']}) > {L['supply_dev_alert_c']}", "Medium", "hvac_degraded"),
        ("BESS_SOH_BELOW_MODEL", f"(df['SOH_BMS_PCT'] - {p['SOHM']}) < {L['soh_residual_alert_pct']}", "Medium", "capacity_fade_fast"),
        ("BESS_AUGMENT_DUE", f"{p['YTA']} < {k['lead']}", "Medium", "capacity_fade_fast"),
        ("BESS_PCS_LOSS_HIGH", f"{p['PLR']} > {L['pcs_loss_ratio_alert']}", "Medium", "pcs_degradation"),
        ("BESS_RTE_LOW", f"{p['RTE']} < {k['rte'] - L['rte_deficit_alert_pct']!r}", "Medium", "pcs_degradation"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    add(r["offgas_ppm"] > L["offgas_alert_ppm"] or r["gas_lel_pct"] > L["lel_alert_pct"], "BESS_OFFGAS_DETECTED", "Critical",
        f"Off-gas {r['offgas_ppm']:.0f} ppm, flammable gas {r['gas_lel_pct']:.1f} % LEL: a cell is venting", "safety", "thermal_runaway_precursor")
    add(r["cell_t_max_rate_c_min"] > L["temp_rate_alert_c_min"], "BESS_CELL_TEMP_RATE", "Critical",
        f"Hottest cell rising {r['cell_t_max_rate_c_min']:.2f} °C/min", "safety", "thermal_runaway_precursor")
    add(r["cell_t_max_c"] > L["cell_temp_alert_c"], "BESS_CELL_TEMP_HIGH", "High", f"Hottest cell {r['cell_t_max_c']:.1f} °C", "battery")
    add(r["cell_v_max_v"] > k["vmaxc"] or r["cell_v_min_v"] < k["vminc"], "BESS_CELL_V_LIMIT", "High",
        f"Cell voltage {r['cell_v_min_v']:.3f} to {r['cell_v_max_v']:.3f} V, outside {k['vminc']} to {k['vmaxc']} V", "battery")
    add(r["insulation_kohm"] < k["imd"], "BESS_INSULATION_LOW", "High",
        f"Insulation {r['insulation_kohm']:.0f} kΩ, below {k['imd']:.0f} kΩ", "battery", "insulation_fault")
    add(t["hvac_load_ratio"] > L["hvac_load_alert"], "BESS_HVAC_MARGIN_LOW", "High",
        f"Heat load {t['heat_load_kw']:.1f} kW is {t['hvac_load_ratio'] * 100:.0f} % of the HVAC capacity at {r['ambient_c']:.0f} °C", "hvac")
    add(t["cell_r_excess_mohm"] > L["r_excess_alert_mohm"] and abs(t["string_current_a"]) > L["min_string_current_a"], "BESS_WEAK_CELL_R", "High",
        f"One cell has {t['cell_r_excess_mohm']:.2f} mΩ more resistance than its neighbours", "battery", "weak_module")
    add(t["cell_t_spread_c"] > L["t_spread_alert_c"], "BESS_CELL_T_SPREAD_HIGH", "Medium",
        f"Cell temperature spread {t['cell_t_spread_c']:.1f} K", "battery", "weak_module")
    add(r["cell_v_spread_rest_mv"] > L["rest_spread_alert_mv"], "BESS_CELL_IMBALANCE", "Medium",
        f"Cell voltage spread at rest {r['cell_v_spread_rest_mv']:.0f} mV", "bms", "cell_imbalance")
    add(t["hvac_cop_ratio"] < L["cop_ratio_alert"], "BESS_HVAC_COP_LOW", "Medium",
        f"HVAC COP {t['hvac_cop']:.2f}, {t['hvac_cop_ratio'] * 100:.0f} % of expected", "hvac", "hvac_degraded")
    add(r["hvac_supply_air_c"] - k["sup"] > L["supply_dev_alert_c"], "BESS_HVAC_SUPPLY_HIGH", "Medium",
        f"Supply air {r['hvac_supply_air_c']:.1f} °C, setpoint {k['sup']:.0f} °C", "hvac", "hvac_degraded")
    add(t["soh_residual_pct"] < L["soh_residual_alert_pct"], "BESS_SOH_BELOW_MODEL", "Medium",
        f"SOH {r['soh_bms_pct']:.1f} %, {t['soh_residual_pct']:+.1f} points against the ageing model", "battery", "capacity_fade_fast")
    add(t["years_to_augment"] < k["lead"], "BESS_AUGMENT_DUE", "Medium",
        f"Usable energy reaches {k['ereq']:.0f} kWh in {t['years_to_augment']:.1f} years: start augmentation now", "battery", "capacity_fade_fast")
    add(t["pcs_loss_ratio"] > L["pcs_loss_ratio_alert"], "BESS_PCS_LOSS_HIGH", "Medium",
        f"PCS loss {t['pcs_loss_kw']:.1f} kW, {t['pcs_loss_ratio']:.2f} x its curve", "pcs", "pcs_degradation")
    add(t["rte_ac_pct"] < k["rte"] - L["rte_deficit_alert_pct"], "BESS_RTE_LOW", "Medium",
        f"Round-trip efficiency {t['rte_ac_pct']:.1f} %, expected {k['rte']:.1f} %", "pcs", "pcs_degradation")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
