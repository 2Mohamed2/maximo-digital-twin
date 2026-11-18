"""The shell-and-tube heat exchanger twin's expectations (E-2501, crude / kerosene, TEMA AES, 1 shell pass, 4 tube passes).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Duty from each side (W in t/h, so W/3.6 is kg/s; cp in kJ/kg K; Q in kW):
    Q_hot = W_kero/3.6 x cp_kero x (Tk_in - Tk_out)      Q_cold = W_crude/3.6 x cp_crude x (Tc_out - Tc_in)
    balance = (Q_hot - Q_cold) / Q x 100 %, with Q = (Q_hot + Q_cold) / 2
Rating (LMTD with the F correction for one shell pass and an even number of tube passes):
    dT1 = Tk_in - Tc_out, dT2 = Tk_out - Tc_in, LMTD = (dT1 - dT2) / ln(dT1 / dT2)
    R = (Tk_in - Tk_out) / (Tc_out - Tc_in), P = (Tc_out - Tc_in) / (Tk_in - Tc_in), S = sqrt(R^2 + 1)
    F = S ln((1 - P) / (1 - R P)) / ((R - 1) ln((2 - P (R + 1 - S)) / (2 - P (R + 1 + S))))
    U_actual = Q x 1000 / (A x F x LMTD)                       (W/m2 K)
Clean U at the actual flows (film coefficients from the data sheet, scaled with flow):
    U_clean = 1 / (1 / (hio x (Wc/Wc0)^0.8) + 1 / (ho x (Wk/Wk0)^0.55) + R_wall)
    Rf = 1/U_actual - 1/U_clean, compared with the design fouling allowance (Kern / TEMA dirt factor)
Effectiveness-NTU (same arrangement): Cmin = min(C_hot, C_cold), Cr = Cmin / Cmax, NTU = U A / Cmin,
    eps = 2 / (1 + Cr + S' (1 + e) / (1 - e)), S' = sqrt(1 + Cr^2), e = exp(-NTU S')
    Q_clean = eps(U_clean) x Cmin x (Tk_in - Tc_in): the duty the exchanger would give today if it were clean.
Lost duty and money: lost = Q_clean - Q; extra furnace fuel = lost x carry-through / furnace efficiency.
Pressure drop: ratio = dP / (dP_clean x (W/W0)^1.8). Fouling raises it; a pass partition leak (bypass) lowers it.
"""


def _k(twin):
    d = twin["design"]
    p, g, th, hy, ec = d["process"], d["geometry"], d["thermal"], d["hydraulics"], d["economics"]
    return dict(wc0=p["crude_flow_t_h"], wk0=p["kero_flow_t_h"], cpc=p["crude_cp_kj_kgk"], cpk=p["kero_cp_kj_kgk"],
                rho=p["crude_density_kg_m3"], area=g["area_m2"], at=g["tube_flow_area_m2"],
                hio=th["hio_w_m2k"], ho=th["ho_w_m2k"], rw=th["r_wall_m2k_w"], et=th["exp_tube"], es=th["exp_shell"],
                rfd=th["rf_design_m2k_w"], dpt0=hy["dp_tube_clean_bar"], dps0=hy["dp_shell_clean_bar"], dpa=hy["dp_allow_bar"],
                ed=hy["dp_exp"], eff=ec["furnace_efficiency"], carry=ec["carry_through"], price=ec["fuel_price_usd_gj"],
                co2=ec["co2_kg_gj"], sayn=d["product"]["saybolt_normal"])


# ---- plain-Python building blocks (also used by physics.py and the figures) ---------------------------------------------
def f_corr(R, P):
    """F correction factor, one shell pass, even number of tube passes (clipped as in the Monitor expression)."""
    import math
    S = math.sqrt(R * R + 1)
    a = math.log(max((1 - P) / max(1 - R * P, 1e-6), 1e-6))
    b = math.log(max((2 - P * (R + 1 - S)) / max(2 - P * (R + 1 + S), 1e-6), 1e-6))
    return min(max(S * a / ((R - 1) * b), 0.3), 1.0)


def eps_12(ntu, cr):
    """Effectiveness, one shell pass, even number of tube passes."""
    import math
    s = math.sqrt(1 + cr * cr)
    e = math.exp(-ntu * s)
    return 2 / (1 + cr + s * (1 + e) / (1 - e))


def u_clean(k, wc, wk):
    return 1 / (1 / (k["hio"] * (wc / k["wc0"]) ** k["et"]) + 1 / (k["ho"] * (wk / k["wk0"]) ** k["es"]) + k["rw"])


def duty(k, u, wc, wk, tki, tci):
    """Duty (kW) of the exchanger with overall coefficient u (W/m2 K) at flows wc, wk (t/h) and inlet temperatures."""
    ch, cc = wk / 3.6 * k["cpk"], wc / 3.6 * k["cpc"]
    cmin, cmax = min(ch, cc), max(ch, cc)
    return eps_12(u * k["area"] / (cmin * 1000), cmin / cmax) * cmin * (tki - tci)


# ---- Monitor expressions ----------------------------------------------------------------------------------------------
def _parts(twin):
    k = _k(twin)
    WC, WK = "df['CRUDE_FLOW_T_H']", "df['KERO_FLOW_T_H']"
    TCI, TCO, TKI, TKO = "df['CRUDE_IN_C']", "df['CRUDE_OUT_C']", "df['KERO_IN_C']", "df['KERO_OUT_C']"
    CH, CC = f"({WK} / 3.6 * {k['cpk']})", f"({WC} / 3.6 * {k['cpc']})"
    QH = f"({CH} * ({TKI} - {TKO}))"
    QC = f"({CC} * ({TCO} - {TCI}))"
    Q = f"(({QH} + {QC}) / 2)"
    D1, D2 = f"np.maximum({TKI} - {TCO}, 0.1)", f"np.maximum({TKO} - {TCI}, 0.1)"
    LM = f"np.where(np.abs({D1} - {D2}) < 1e-9, {D1}, ({D1} - {D2}) / np.log({D1} / {D2}))"
    R = f"(({TKI} - {TKO}) / ({TCO} - {TCI}))"
    P = f"(({TCO} - {TCI}) / ({TKI} - {TCI}))"
    S = f"np.sqrt({R} ** 2 + 1)"
    FA = f"np.log(np.maximum((1 - {P}) / np.maximum(1 - {R} * {P}, 1e-6), 1e-6))"
    FB = f"np.log(np.maximum((2 - {P} * ({R} + 1 - {S})) / np.maximum(2 - {P} * ({R} + 1 + {S}), 1e-6), 1e-6))"
    F = f"np.clip({S} * {FA} / (({R} - 1) * {FB}), 0.3, 1.0)"
    UA = f"({Q} * 1000 / ({k['area']} * {F} * {LM}))"
    UC = (f"(1 / (1 / ({k['hio']} * ({WC} / {k['wc0']}) ** {k['et']}) + 1 / ({k['ho']} * ({WK} / {k['wk0']}) ** {k['es']})"
          f" + {k['rw']}))")
    RF = f"(1 / {UA} - 1 / {UC})"
    CMIN, CMAX = f"np.minimum({CH}, {CC})", f"np.maximum({CH}, {CC})"
    CR = f"({CMIN} / {CMAX})"
    SS = f"np.sqrt(1 + {CR} ** 2)"
    EX = f"np.exp(-({UC} * {k['area']} / ({CMIN} * 1000)) * {SS})"
    QCL = f"(2 / (1 + {CR} + {SS} * (1 + {EX}) / (1 - {EX})) * {CMIN} * ({TKI} - {TCI}))"
    LOST = f"({QCL} - {Q})"
    FUEL_GJ = f"(np.maximum({LOST}, 0) * {k['carry']} / {k['eff']} * 0.0864)"
    DPTR = f"(df['DP_TUBE_BAR'] / ({k['dpt0']} * ({WC} / {k['wc0']}) ** {k['ed']}))"
    DPSR = f"(df['DP_SHELL_BAR'] / ({k['dps0']} * ({WK} / {k['wk0']}) ** {k['ed']}))"
    BAL = f"(({QH} - {QC}) / {Q} * 100)"
    VEL = f"({WC} / 3.6 / {k['rho']} / {k['at']})"
    return dict(k=k, QH=QH, QC=QC, Q=Q, LM=LM, F=F, UA=UA, UC=UC, RF=RF, QCL=QCL, LOST=LOST, FUEL_GJ=FUEL_GJ,
                DPTR=DPTR, DPSR=DPSR, BAL=BAL, VEL=VEL, CMIN=CMIN, WC=WC)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("Q_HOT_KW", p["QH"]),
        ("Q_COLD_KW", p["QC"]),
        ("Q_KW", p["Q"]),
        ("BALANCE_PCT", p["BAL"]),
        ("LMTD_K", p["LM"]),
        ("F_CORR", p["F"]),
        ("U_ACTUAL_W_M2K", p["UA"]),
        ("U_CLEAN_W_M2K", p["UC"]),
        ("U_RATIO", f"{p['UA']} / {p['UC']}"),
        ("RF_M2K_W", p["RF"]),
        ("RF_USED_PCT", f"{p['RF']} / {k['rfd']} * 100"),
        ("EFFECTIVENESS", f"{p['QH']} / ({p['CMIN']} * (df['KERO_IN_C'] - df['CRUDE_IN_C']))"),
        ("Q_CLEAN_KW", p["QCL"]),
        ("LOST_DUTY_KW", p["LOST"]),
        ("FUEL_PENALTY_USD_DAY", f"{p['FUEL_GJ']} * {k['price']}"),
        ("CO2_T_DAY", f"{p['FUEL_GJ']} * {k['co2']} / 1000"),
        ("DP_TUBE_RATIO", p["DPTR"]),
        ("DP_SHELL_RATIO", p["DPSR"]),
        ("DP_TUBE_AT_DESIGN_BAR", f"df['DP_TUBE_BAR'] * ({k['wc0']} / {p['WC']}) ** {k['ed']}"),
        ("TUBE_VELOCITY_M_S", p["VEL"]),
    ]


def evaluate(twin, r):
    import math
    k = _k(twin)
    wc, wk = r["crude_flow_t_h"], r["kero_flow_t_h"]
    tci, tco, tki, tko = r["crude_in_c"], r["crude_out_c"], r["kero_in_c"], r["kero_out_c"]
    ch, cc = wk / 3.6 * k["cpk"], wc / 3.6 * k["cpc"]
    qh, qc = ch * (tki - tko), cc * (tco - tci)
    q = (qh + qc) / 2
    d1, d2 = max(tki - tco, 0.1), max(tko - tci, 0.1)
    lm = d1 if abs(d1 - d2) < 1e-9 else (d1 - d2) / math.log(d1 / d2)
    R, P = (tki - tko) / (tco - tci), (tco - tci) / (tki - tci)
    F = f_corr(R, P)
    ua = q * 1000 / (k["area"] * F * lm)
    uc = u_clean(k, wc, wk)
    rf = 1 / ua - 1 / uc
    cmin, cmax = min(ch, cc), max(ch, cc)
    qcl = eps_12(uc * k["area"] / (cmin * 1000), cmin / cmax) * cmin * (tki - tci)
    lost = qcl - q
    fuel_gj = max(lost, 0) * k["carry"] / k["eff"] * 0.0864
    return {
        "q_hot_kw": qh, "q_cold_kw": qc, "q_kw": q, "balance_pct": (qh - qc) / q * 100, "lmtd_k": lm, "f_corr": F,
        "u_actual_w_m2k": ua, "u_clean_w_m2k": uc, "u_ratio": ua / uc, "rf_m2k_w": rf, "rf_used_pct": rf / k["rfd"] * 100,
        "effectiveness": qh / (cmin * (tki - tci)), "q_clean_kw": qcl, "lost_duty_kw": lost,
        "fuel_penalty_usd_day": fuel_gj * k["price"], "co2_t_day": fuel_gj * k["co2"] / 1000,
        "dp_tube_ratio": r["dp_tube_bar"] / (k["dpt0"] * (wc / k["wc0"]) ** k["ed"]),
        "dp_shell_ratio": r["dp_shell_bar"] / (k["dps0"] * (wk / k["wk0"]) ** k["ed"]),
        "dp_tube_at_design_bar": r["dp_tube_bar"] * (k["wc0"] / wc) ** k["ed"],
        "tube_velocity_m_s": wc / 3.6 / k["rho"] / k["at"],
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    USED = f"({p['RF']} / {k['rfd']} * 100)"
    UR = f"({p['UA']} / {p['UC']})"
    DPAD = f"(df['DP_TUBE_BAR'] * ({k['wc0']} / {p['WC']}) ** {k['ed']})"
    NOBYP = f"({p['DPTR']} >= {L['dp_ratio_low']})"
    return [
        ("HEX_TUBE_LEAK", f"(df['KERO_SAYBOLT'] < {L['saybolt_alert']}) & (df['CRUDE_PRESSURE_BARG'] - df['KERO_PRESSURE_BARG'] > {L['leak_dp_min_bar']})", "Critical", "tube_leak"),
        ("HEX_FOULING_LIMIT", f"({USED} > {L['rf_limit_pct']}) & {NOBYP}", "High", "tube_fouling"),
        ("HEX_DP_TUBE_LIMIT", f"{DPAD} > {k['dpa']}", "High", "tube_fouling"),
        ("HEX_BYPASS_SUSPECT", f"({UR} < {L['u_ratio_bypass']}) & ({p['DPTR']} < {L['dp_ratio_low']})", "High", "partition_leak"),
                ("HEX_FOULING_WARN", f"({USED} > {L['rf_warn_pct']}) & ({USED} <= {L['rf_limit_pct']}) & {NOBYP}", "Medium", "tube_fouling"),
        ("HEX_PRODUCT_COLOUR", f"df['KERO_SAYBOLT'] < {L['saybolt_warn']}", "Medium", "tube_leak"),
        ("HEX_DP_TUBE_HIGH", f"{p['DPTR']} > {L['dp_ratio_high']}", "Medium", "tube_fouling"),
        ("HEX_DP_SHELL_HIGH", f"{p['DPSR']} > {L['dp_ratio_high']}", "Medium", "shell_fouling"),
        ("HEX_DP_TUBE_LOW", f"{p['DPTR']} < {L['dp_ratio_low']}", "Medium", "partition_leak"),
        ("HEX_HOT_DUTY_EXCESS", f"{p['BAL']} > {L['balance_alert_pct']}", "Medium", None),
        ("HEX_COLD_DUTY_EXCESS", f"{p['BAL']} < {-L['balance_alert_pct']}", "Medium", "ti_drift"),
        ("HEX_VELOCITY_LOW", f"{p['VEL']} < {L['velocity_min_m_s']}", "Medium", "low_throughput"),
        ("HEX_FUEL_PENALTY", f"{p['FUEL_GJ']} * {k['price']} > {L['fuel_penalty_alert_usd_day']}", "Medium", "tube_fouling"),
        ("HEX_RF_NEGATIVE", f"{p['RF']} < {L['rf_negative_m2k_w']}", "Low", "ti_drift"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    used, bal, dptr, dpsr = t["rf_used_pct"], t["balance_pct"], t["dp_tube_ratio"], t["dp_shell_ratio"]
    nobyp = dptr >= L["dp_ratio_low"]
    dpl = r["crude_pressure_barg"] - r["kero_pressure_barg"]
    add(r["kero_saybolt"] < L["saybolt_alert"] and dpl > L["leak_dp_min_bar"], "HEX_TUBE_LEAK", "Critical",
        f"Kerosene colour {r['kero_saybolt']:+.0f} Saybolt with the crude side {dpl:.1f} bar higher: crude is leaking into the kerosene",
        "tubes", "tube_leak")
    add(used > L["rf_limit_pct"] and nobyp, "HEX_FOULING_LIMIT", "High",
        f"Fouling resistance {t['rf_m2k_w'] * 1e4:.2f} × 10⁻⁴ m²K/W: {used:.0f} % of the design allowance used", "bundle", "tube_fouling")
    add(t["dp_tube_at_design_bar"] > k["dpa"], "HEX_DP_TUBE_LIMIT", "High",
        f"Tube-side pressure drop {t['dp_tube_at_design_bar']:.2f} bar at design flow, above the {k['dpa']:.2f} bar allowed", "tubes", "tube_fouling")
    add(t["u_ratio"] < L["u_ratio_bypass"] and dptr < L["dp_ratio_low"], "HEX_BYPASS_SUSPECT", "High",
        f"U only {t['u_ratio'] * 100:.0f} % of clean while the tube-side pressure drop fell to {dptr:.2f} × expected: crude is bypassing passes",
        "channel", "partition_leak")
    add(L["rf_warn_pct"] < used <= L["rf_limit_pct"] and nobyp, "HEX_FOULING_WARN", "Medium",
        f"{used:.0f} % of the fouling allowance used", "bundle", "tube_fouling")
    add(r["kero_saybolt"] < L["saybolt_warn"], "HEX_PRODUCT_COLOUR", "Medium",
        f"Kerosene colour {r['kero_saybolt']:+.0f} Saybolt, below {L['saybolt_warn']:+.0f}", "product", "tube_leak")
    add(dptr > L["dp_ratio_high"], "HEX_DP_TUBE_HIGH", "Medium", f"Tube-side pressure drop {dptr:.2f} × expected at this flow", "tubes", "tube_fouling")
    add(dpsr > L["dp_ratio_high"], "HEX_DP_SHELL_HIGH", "Medium", f"Shell-side pressure drop {dpsr:.2f} × expected at this flow", "shell", "shell_fouling")
    add(dptr < L["dp_ratio_low"], "HEX_DP_TUBE_LOW", "Medium", f"Tube-side pressure drop only {dptr:.2f} × expected at this flow", "channel", "partition_leak")
    add(bal > L["balance_alert_pct"], "HEX_HOT_DUTY_EXCESS", "Medium", f"Kerosene gives {bal:.1f} % more heat than the crude takes: check the instruments", "instrument")
    add(bal < -L["balance_alert_pct"], "HEX_COLD_DUTY_EXCESS", "Medium", f"Crude takes {-bal:.1f} % more heat than the kerosene gives: check the instruments", "instrument", "ti_drift")
    add(t["tube_velocity_m_s"] < L["velocity_min_m_s"], "HEX_VELOCITY_LOW", "Medium",
        f"Crude velocity {t['tube_velocity_m_s']:.2f} m/s, below {L['velocity_min_m_s']} m/s: fouling speeds up", "operation", "low_throughput")
    add(t["fuel_penalty_usd_day"] > L["fuel_penalty_alert_usd_day"], "HEX_FUEL_PENALTY", "Medium",
        f"Lost duty {t['lost_duty_kw']:.0f} kW costs {t['fuel_penalty_usd_day']:.0f} $/day of furnace fuel", "economics", "tube_fouling")
    add(t["rf_m2k_w"] < L["rf_negative_m2k_w"], "HEX_RF_NEGATIVE", "Low",
        f"Rated cleaner than clean (Rf {t['rf_m2k_w'] * 1e4:.2f} × 10⁻⁴ m²K/W): an instrument reads wrong", "instrument", "ti_drift")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health


# ---- cleaning economics (plain Python, for the post and the figures; not a Monitor function) ----------------------------
def penalty_usd_day(twin, rf):
    """Extra furnace fuel ($/day) at design flows and inlet temperatures when the fouling resistance is rf (m2 K/W)."""
    k = _k(twin)
    p = twin["design"]["process"]
    wc, wk, tki, tci = p["crude_flow_t_h"], p["kero_flow_t_h"], p["kero_in_c"], p["crude_in_c"]
    uc = u_clean(k, wc, wk)
    lost = duty(k, uc, wc, wk, tki, tci) - duty(k, 1 / (1 / uc + rf), wc, wk, tki, tci)
    return max(lost, 0) * k["carry"] / k["eff"] * 0.0864 * k["price"]


def cleaning_cycle(twin, days):
    """Average cost per day ($/day) of cleaning every `days` days: (cleaning cost + fuel penalty over the cycle) / days.
    Fouling grows linearly from zero after each cleaning and reaches the design allowance after fouling_days_to_allowance."""
    ec = twin["design"]["economics"]
    rate = twin["design"]["thermal"]["rf_design_m2k_w"] / ec["fouling_days_to_allowance"]
    n = max(1, int(days))
    fuel = sum(penalty_usd_day(twin, rate * (i + 0.5) * days / n) for i in range(n)) * days / n
    return (ec["cleaning_cost_usd"] + fuel) / days, fuel


def best_interval(twin, lo=60, hi=3000):
    """Cleaning interval (days) with the lowest average cost per day."""
    best = min(range(lo, hi + 1, 5), key=lambda d: cleaning_cycle(twin, d)[0])
    return best, cleaning_cycle(twin, best)[0]
