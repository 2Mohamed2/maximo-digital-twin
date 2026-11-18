"""The turbo-generator twin's expectations (GEN-3401, 2-pole air-cooled synchronous generator).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Per unit (pu) on the rating: P, Q in pu of S_rated; V in pu of the rated voltage; I in pu of the rated current
In = S / (sqrt(3) V).

Operating point on the capability (P-Q) chart, round-rotor phasor E = V + j Xd I (textbook, unsaturated):
    E = sqrt((V + Q Xd / V)^2 + (P Xd / V)^2)        internal voltage, pu
    load angle  delta = atan2(P Xd / V, V + Q Xd / V)
    expected field current  If_exp = If_rated x E / E_rated   (E_rated = E at rated P, Q and V)
  Capability limits: armature current I <= 1 pu, field current If <= If_rated, load angle <= delta_max.
  Field current ratio = If measured / If_exp: above 1 means the rotor needs more ampere-turns than designed for the
  same P and Q: shorted turns (or a wrong Xd).
Rotor winding temperature from the field resistance (IEC 60034-1 resistance method, k = 235 for copper):
    T_rotor = (Vf / If) / R20 x (235 + 20) - 235
Stator winding (slot RTDs, IEC 60034-1 ETD method), load-and-coolant model fitted on the heat run:
    T_rtd_exp = T_cold_air + core x (V/Vn)^2 + copper x (I/In)^2         (I^2 R losses grow with the square of the current)
    residual = T_rtd_max - T_rtd_exp;  spread = T_rtd_max - T_rtd_mean
    limit = 40 C + class B rise for the ETD method at this voltage (IEC 60034-1 Tables 7 and 9)
    relative thermal ageing = 2 ^ ((T_rtd_max - limit) / 10)    (10 K rule of thumb: 1 = ageing at the limit temperature)
Air coolers: hot air expected = cold air + a0 + a1 (I/In)^2 ; approach = cold air - cooler water inlet.
Online PD (IEC 60034-27-2 / IEEE 1434 practice): Qm against an alert level, and the trend Qm / Qm six months ago.
Bearings: metal temperature residual = T_metal - (T_oil_in + m0 + m1 P/P_rated).
"""
import math

SQ3 = math.sqrt(3)


def _k(twin):
    d = twin["design"]
    ra, el, th, br = d["rating"], d["electrical"], d["thermal"], d["bearings"]
    s, v = ra["s_mva"], ra["v_kv"]
    xd = el["xd_pu"]
    pr, qr = ra["pf"], math.sqrt(1 - ra["pf"] ** 2)
    e_rated = math.sqrt((1 + qr * xd) ** 2 + (pr * xd) ** 2)
    return dict(s=s, v=v, p_rated=ra["p_mw"], i_rated=round(s * 1e6 / (SQ3 * v * 1e3), 6), xd=xd, e_rated=e_rated,
                ifr=el["if_rated_a"], r20=el["rf20_ohm"], kcu=el["k_cu"], tpp=el["turns_per_pole"],
                core=th["stator_core_k"], cu=th["stator_cu_k"], a0=th["air_rise0_k"], a1=th["air_rise1_k"],
                t_stator=th["coolant_ref_c"] + th["stator_rise_limit_k"], t_rotor=th["coolant_ref_c"] + th["rotor_rise_limit_k"],
                m0=br["metal_over_oil_k"], m1=br["load_k"])


def _parts(twin):
    k = _k(twin)
    P = f"(df['ACTIVE_POWER_MW'] / {k['s']})"
    Q = f"(df['REACTIVE_POWER_MVAR'] / {k['s']})"
    V = f"(df['TERMINAL_VOLTAGE_KV'] / {k['v']})"
    I = f"(df['STATOR_CURRENT_A'] / {k['i_rated']!r})"
    EX = f"({V} + {Q} * {k['xd']} / {V})"
    EY = f"({P} * {k['xd']} / {V})"
    E = f"np.sqrt({EX} ** 2 + {EY} ** 2)"
    IFE = f"({k['ifr'] / k['e_rated']:.6f} * {E})"
    TR = f"(df['FIELD_VOLTAGE_V'] / df['FIELD_CURRENT_A'] / {k['r20']} * ({k['kcu']} + 20) - {k['kcu']})"
    TE = f"(df['COLD_AIR_C'] + {k['core']} * {V} ** 2 + {k['cu']} * {I} ** 2)"
    BE = f"(df['OIL_IN_C'] + {k['m0']} + {k['m1']} * df['ACTIVE_POWER_MW'] / {k['p_rated']})"
    BM = "np.maximum(df['BRG_DE_TEMP_C'], df['BRG_NDE_TEMP_C'])"
    DL = f"(np.degrees(np.arctan2({EY}, {EX})))"
    return dict(k=k, P=P, Q=Q, V=V, I=I, E=E, IFE=IFE, TR=TR, TE=TE, BE=BE, BM=BM, DL=DL)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("APPARENT_POWER_PU", f"np.sqrt({p['P']} ** 2 + {p['Q']} ** 2)"),
        ("STATOR_CURRENT_PU", p["I"]),
        ("INTERNAL_EMF_PU", p["E"]),
        ("LOAD_ANGLE_DEG", p["DL"]),
        ("FIELD_CURRENT_EXPECTED_A", p["IFE"]),
        ("FIELD_CURRENT_RATIO", f"df['FIELD_CURRENT_A'] / {p['IFE']}"),
        ("FIELD_CURRENT_PU", f"df['FIELD_CURRENT_A'] / {k['ifr']}"),
        ("ROTOR_TEMP_C", p["TR"]),
        ("STATOR_RTD_EXPECTED_C", p["TE"]),
        ("STATOR_RTD_RESIDUAL_K", f"df['STATOR_RTD_MAX_C'] - {p['TE']}"),
        ("STATOR_RTD_SPREAD_K", "df['STATOR_RTD_MAX_C'] - df['STATOR_RTD_MEAN_C']"),
        ("STATOR_HEADROOM_K", f"{k['t_stator']} - df['STATOR_RTD_MAX_C']"),
        ("THERMAL_AGEING_RATE", f"2 ** ((df['STATOR_RTD_MAX_C'] - {k['t_stator']}) / 10)"),
        ("HOT_AIR_EXPECTED_C", f"df['COLD_AIR_C'] + {k['a0']} + {k['a1']} * {p['I']} ** 2"),
        ("HOT_AIR_RESIDUAL_K", f"df['HOT_AIR_C'] - (df['COLD_AIR_C'] + {k['a0']} + {k['a1']} * {p['I']} ** 2)"),
        ("COOLER_APPROACH_K", "df['COLD_AIR_C'] - df['COOLER_WATER_IN_C']"),
        ("PD_TREND_RATIO", "df['PD_QM_MV'] / df['PD_QM_6MO_MV']"),
        ("BEARING_TEMP_EXPECTED_C", p["BE"]),
        ("BEARING_TEMP_RESIDUAL_K", f"{p['BM']} - {p['BE']}"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    P, Q = r["active_power_mw"] / k["s"], r["reactive_power_mvar"] / k["s"]
    V, I = r["terminal_voltage_kv"] / k["v"], r["stator_current_a"] / k["i_rated"]
    ex, ey = V + Q * k["xd"] / V, P * k["xd"] / V
    e = math.sqrt(ex ** 2 + ey ** 2)
    ife = k["ifr"] / k["e_rated"] * e
    te = r["cold_air_c"] + k["core"] * V ** 2 + k["cu"] * I ** 2
    hae = r["cold_air_c"] + k["a0"] + k["a1"] * I ** 2
    be = r["oil_in_c"] + k["m0"] + k["m1"] * r["active_power_mw"] / k["p_rated"]
    return {
        "apparent_power_pu": math.sqrt(P ** 2 + Q ** 2), "stator_current_pu": I, "internal_emf_pu": e,
        "load_angle_deg": math.degrees(math.atan2(ey, ex)),
        "field_current_expected_a": ife, "field_current_ratio": r["field_current_a"] / ife, "field_current_pu": r["field_current_a"] / k["ifr"],
        "rotor_temp_c": r["field_voltage_v"] / r["field_current_a"] / k["r20"] * (k["kcu"] + 20) - k["kcu"],
        "stator_rtd_expected_c": te, "stator_rtd_residual_k": r["stator_rtd_max_c"] - te,
        "stator_rtd_spread_k": r["stator_rtd_max_c"] - r["stator_rtd_mean_c"],
        "stator_headroom_k": k["t_stator"] - r["stator_rtd_max_c"],
        "thermal_ageing_rate": 2 ** ((r["stator_rtd_max_c"] - k["t_stator"]) / 10),
        "hot_air_expected_c": hae, "hot_air_residual_k": r["hot_air_c"] - hae,
        "cooler_approach_k": r["cold_air_c"] - r["cooler_water_in_c"],
        "pd_trend_ratio": r["pd_qm_mv"] / r["pd_qm_6mo_mv"],
        "bearing_temp_expected_c": be, "bearing_temp_residual_k": max(r["brg_de_temp_c"], r["brg_nde_temp_c"]) - be,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    return [
        ("GEN_ROTOR_TEMP_HIGH", f"{p['TR']} > {k['t_rotor']}", "High", "over_excitation"),
        ("GEN_STATOR_TEMP_LIMIT", f"df['STATOR_RTD_MAX_C'] > {k['t_stator']}", "High", "over_excitation"),
        ("GEN_LOAD_ANGLE_HIGH", f"{p['DL']} > {L['load_angle_max_deg']}", "High", "under_excitation"),
        ("GEN_ROTOR_OVERLOAD", f"df['FIELD_CURRENT_A'] / {k['ifr']} > {L['field_current_max_pu']}", "High", "over_excitation"),
        ("GEN_PD_HIGH", f"df['PD_QM_MV'] > {L['pd_qm_alert_mv']}", "High", "stator_insulation_pd"),
        ("GEN_VIB_HIGH", f"np.maximum(df['VIB_DE_UM'], df['VIB_NDE_UM']) > {L['vib_alert_um']}", "High", "bearing_wear"),
        ("GEN_STATOR_OVERLOAD", f"{p['I']} > {L['stator_current_max_pu']}", "Medium", "over_excitation"),
        ("GEN_STATOR_RESIDUAL", f"(df['STATOR_RTD_MAX_C'] - {p['TE']}) > {L['stator_residual_k']}", "Medium", "stator_vent_blockage"),
        ("GEN_RTD_SPREAD", f"(df['STATOR_RTD_MAX_C'] - df['STATOR_RTD_MEAN_C']) > {L['rtd_spread_k']}", "Medium", "stator_vent_blockage"),
        ("GEN_COLD_AIR_HIGH", f"df['COLD_AIR_C'] > {L['cold_air_max_c']}", "Medium", "cooler_fouling"),
        ("GEN_COOLER_APPROACH", f"(df['COLD_AIR_C'] - df['COOLER_WATER_IN_C']) > {L['cooler_approach_k']}", "Medium", "cooler_fouling"),
        ("GEN_PD_TREND", f"(df['PD_QM_MV'] / df['PD_QM_6MO_MV'] > {L['pd_trend_ratio']}) & (df['PD_QM_MV'] > {L['pd_trend_min_mv']})", "Medium", "stator_insulation_pd"),
        ("GEN_FIELD_CURRENT_HIGH", f"df['FIELD_CURRENT_A'] / {p['IFE']} > {L['field_ratio_alert']}", "Medium", "rotor_shorted_turns"),
        ("GEN_SHORTED_TURNS", f"df['SHORTED_TURNS'] > {L['shorted_turns_alert']}", "Medium", "rotor_shorted_turns"),
        ("GEN_BEARING_TEMP", f"({p['BM']} - {p['BE']}) > {L['bearing_residual_k']}", "Medium", "bearing_wear"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    vm = max(r["vib_de_um"], r["vib_nde_um"])
    add(t["rotor_temp_c"] > k["t_rotor"], "GEN_ROTOR_TEMP_HIGH", "High",
        f"Rotor winding at {t['rotor_temp_c']:.0f} °C (from its resistance), above the {k['t_rotor']:.0f} °C limit", "rotor", "over_excitation")
    add(r["stator_rtd_max_c"] > k["t_stator"], "GEN_STATOR_TEMP_LIMIT", "High",
        f"Hottest stator RTD {r['stator_rtd_max_c']:.1f} °C, above the {k['t_stator']:.0f} °C limit", "stator", "over_excitation")
    add(t["load_angle_deg"] > L["load_angle_max_deg"], "GEN_LOAD_ANGLE_HIGH", "High",
        f"Load angle {t['load_angle_deg']:.0f}° at {r['reactive_power_mvar']:.0f} Mvar: close to losing synchronism", "excitation", "under_excitation")
    add(t["field_current_pu"] > L["field_current_max_pu"], "GEN_ROTOR_OVERLOAD", "High",
        f"Field current {r['field_current_a']:.0f} A, {t['field_current_pu']:.2f} × rated", "excitation", "over_excitation")
    add(r["pd_qm_mv"] > L["pd_qm_alert_mv"], "GEN_PD_HIGH", "High", f"PD Qm {r['pd_qm_mv']:.0f} mV, above {L['pd_qm_alert_mv']:.0f} mV", "insulation", "stator_insulation_pd")
    add(vm > L["vib_alert_um"], "GEN_VIB_HIGH", "High", f"Shaft vibration {vm:.0f} µm pk-pk, above {L['vib_alert_um']:.0f}", "bearing", "bearing_wear")
    add(t["stator_current_pu"] > L["stator_current_max_pu"], "GEN_STATOR_OVERLOAD", "Medium",
        f"Stator current {r['stator_current_a']:.0f} A, {t['stator_current_pu']:.2f} × rated", "stator", "over_excitation")
    add(t["stator_rtd_residual_k"] > L["stator_residual_k"], "GEN_STATOR_RESIDUAL", "Medium",
        f"Hottest RTD {t['stator_rtd_residual_k']:+.1f} K above the load-and-cold-air model", "stator", "stator_vent_blockage")
    add(t["stator_rtd_spread_k"] > L["rtd_spread_k"], "GEN_RTD_SPREAD", "Medium",
        f"Hottest RTD {t['stator_rtd_spread_k']:.1f} K above the mean of all slot RTDs", "stator", "stator_vent_blockage")
    add(r["cold_air_c"] > L["cold_air_max_c"], "GEN_COLD_AIR_HIGH", "Medium", f"Cold air {r['cold_air_c']:.1f} °C, above {L['cold_air_max_c']:.0f} °C", "cooler", "cooler_fouling")
    add(t["cooler_approach_k"] > L["cooler_approach_k"], "GEN_COOLER_APPROACH", "Medium",
        f"Cooler approach {t['cooler_approach_k']:.1f} K (cold air − water inlet)", "cooler", "cooler_fouling")
    add(t["pd_trend_ratio"] > L["pd_trend_ratio"] and r["pd_qm_mv"] > L["pd_trend_min_mv"], "GEN_PD_TREND", "Medium",
        f"PD Qm {t['pd_trend_ratio']:.1f} × its value six months ago", "insulation", "stator_insulation_pd")
    add(t["field_current_ratio"] > L["field_ratio_alert"], "GEN_FIELD_CURRENT_HIGH", "Medium",
        f"Field current {t['field_current_ratio']:.3f} × expected for {r['active_power_mw']:.0f} MW and {r['reactive_power_mvar']:.0f} Mvar", "rotor", "rotor_shorted_turns")
    add(r["shorted_turns"] > L["shorted_turns_alert"], "GEN_SHORTED_TURNS", "Medium", f"Flux probe: {r['shorted_turns']:.0f} shorted turns on the worst pole", "rotor", "rotor_shorted_turns")
    add(t["bearing_temp_residual_k"] > L["bearing_residual_k"], "GEN_BEARING_TEMP", "Medium",
        f"Bearing metal {t['bearing_temp_residual_k']:+.1f} K above expected for its oil temperature", "bearing", "bearing_wear")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
