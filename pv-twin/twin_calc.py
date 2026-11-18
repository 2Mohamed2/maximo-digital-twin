"""The utility PV block twin's expectations (PV-3101: one string inverter, 24 strings, one weather station).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Weather station -> what the array should give (PVWatts v5 DC model, Sandia cell temperature):
    T_cell  = T_module(back) + G/1000 x 3 C
    f_T     = 1 + gamma x (T_cell - 25)                     gamma = -0.29 %/C (module data sheet)
    W(age)  = 1 - 1 % x min(age, 1) - 0.40 % x max(age - 1, 0)   (the module's linear power warranty)
    P_dc,exp = N x Pmax,STC x G/1000 x f_T x (1 + bifacial gain) x (1 - DC losses) x W(age)      (a clean array)
Soiling (IEC 61724-1 soiling ratio, two reference cells side by side, one washed daily, one never washed):
    SR = G_unwashed / G_clean            soiling loss = 1 - SR
Performance index and its soiling-corrected value:
    PI = P_dc / P_dc,exp                 PI_corr = PI / SR     (what is left once the dust is explained)
Inverter (PVWatts v5 part-load curve, eta_nom = European efficiency of the data sheet):
    z = P_dc / (P_ac0 / eta_nom)         eta = eta_nom / 0.9637 x (-0.0162 z - 0.0059 / z + 0.9858)
    AC limit = min(derating curve at the ambient temperature, setpoint x P_ac0)
    P_ac,exp = min(eta x P_dc, AC limit)       clipping loss = max(eta(P_avail) x P_avail - AC limit, 0),  P_avail = P_dc,exp x SR
Performance ratio (IEC 61724-1), instantaneous:
    PR = P_ac / (P0 x G / 1000)          PR_T = PR / f_T    (temperature-corrected to 25 C)
Strings: mean current and the lowest string / mean (a failed string or a string with bypass diodes on stands out).
Inverter heat: T_inv,exp = T_amb + heat rise x P_ac / P_ac0.
Insulation: the inverter measures the array's insulation resistance before it connects; IEC 62109-2 sets the floor
    Vmax PV / 30 mA = 1500 V / 30 mA = 50 kOhm.
"""
import math

N_STR = 24


def _k(twin):
    d = twin["design"]
    m, a, inv, ec, dr, ins, w, cl = (d["module"], d["array"], d["inverter"], d["efficiency_curve"], d["derating"],
                                     d["insulation"], d["weather"], d["cleaning"])
    n_mod = a["modules_per_string"] * a["strings"]
    p0 = n_mod * m["pmax_w"] / 1000.0
    pac0 = inv["p_ac_max_kw"]
    cost = cl["cost_usd_per_module"] * n_mod
    e_day = p0 * cl["specific_yield_kwh_per_kwp_day"]
    trig = math.sqrt(2 * cost * cl["soiling_rate_per_day"] / (e_day * cl["energy_price_usd_per_kwh"]))
    return dict(n_mod=n_mod, n_str=a["strings"], p0=p0, gam=m["gamma_pmax_pct_per_c"] / 100, alpha=m["alpha_isc_pct_per_c"] / 100,
                imp=m["imp_a"], vmp=m["vmp_v"], mps=a["modules_per_string"], bif=a["rear_irradiance_ratio"] * m["bifaciality"],
                dcl=a["dc_loss_frac"], d1=m["degradation_first_year_pct"] / 100, dn=m["degradation_annual_pct"] / 100,
                pac0=pac0, en=ec["eta_nom"], ea=ec["eta_nom"] / ec["eta_ref"], pdc0=pac0 / ec["eta_nom"],
                dt=w["cell_delta_t_c"], gmin=w["g_min_wm2"], dT=dr["temp_c"], dP=dr["p_kw"], rise=dr["heat_rise_full_load_k"],
                riso_lim=ins["riso_limit_kohm"], riso_alert=ins["riso_alert_kohm"],
                clean_cost=cost, e_day=e_day, soil_rate=cl["soiling_rate_per_day"], price=cl["energy_price_usd_per_kwh"],
                soil_trigger_pct=trig * 100, clean_interval_d=trig / cl["soiling_rate_per_day"])


def interp(x, xs, ys):
    """np.interp for one value (flat outside the end points)."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            return ys[i - 1] + (ys[i] - ys[i - 1]) * (x - xs[i - 1]) / (xs[i] - xs[i - 1])
    return ys[-1]


def eta_curve(k, p_dc):
    """PVWatts v5 inverter efficiency at DC power p_dc (kW); p_dc floored at 1 kW like the Monitor expression."""
    z = max(p_dc, 1) / k["pdc0"]
    return max(k["ea"] * (-0.0162 * z - 0.0059 / z + 0.9858), 0)


def warranty(k, age):
    return 1 - k["d1"] * min(age, 1) - k["dn"] * max(age - 1, 0)


def ac_limit(k, t_amb, setpoint_pct):
    return min(interp(t_amb, k["dT"], k["dP"]), k["pac0"] * setpoint_pct / 100)


def strings(r):
    return [r[f"i_s{i:02d}_a"] for i in range(1, N_STR + 1)]


def _parts(twin):
    k = _k(twin)
    R = repr
    G, GS = "df['POA_WM2']", "df['POA_SOILED_WM2']"
    TC = f"(df['MODULE_TEMP_C'] + {G} / 1000 * {R(k['dt'])})"
    TF = f"(1 + {R(k['gam'])} * ({TC} - 25))"
    W = f"(1 - {R(k['d1'])} * np.minimum(df['YEARS_IN_SERVICE'], 1) - {R(k['dn'])} * np.maximum(df['YEARS_IN_SERVICE'] - 1, 0))"
    DCE = f"({R(k['p0'])} * {G} / 1000 * {TF} * {R(1 + k['bif'])} * {R(1 - k['dcl'])} * {W})"
    SR = f"({GS} / np.maximum({G}, 1))"
    PI = f"(df['P_DC_KW'] / np.maximum({DCE}, 0.1))"
    PIC = f"({PI} / np.maximum({SR}, 0.01))"

    def ETA(x):
        z = f"(np.maximum({x}, 1) / {R(k['pdc0'])})"
        return f"np.maximum({R(k['ea'])} * (-0.0162 * {z} - 0.0059 / {z} + 0.9858), 0)"
    ETAE = ETA("df['P_DC_KW']")
    ETAM = "(df['P_AC_KW'] / np.maximum(df['P_DC_KW'], 0.1))"
    LIM = f"np.minimum(np.interp(df['AMBIENT_TEMP_C'], {k['dT']}, {k['dP']}), {R(k['pac0'])} * df['SETPOINT_PCT'] / 100)"
    PAV = f"({DCE} * {SR})"
    S = [f"df['I_S{i:02d}_A']" for i in range(1, N_STR + 1)]
    MEAN = "((" + " + ".join(S) + f") / {N_STR})"
    MINR = f"(np.minimum.reduce([{', '.join(S)}]) / np.maximum({MEAN}, 0.01))"
    TIE = f"(df['AMBIENT_TEMP_C'] + {R(k['rise'])} * df['P_AC_KW'] / {R(k['pac0'])})"
    LOSS = f"((1 - {SR}) * 100)"
    return dict(k=k, TC=TC, TF=TF, W=W, DCE=DCE, SR=SR, PI=PI, PIC=PIC, ETA=ETA, ETAE=ETAE, ETAM=ETAM, LIM=LIM, PAV=PAV,
                MEAN=MEAN, MINR=MINR, TIE=TIE, LOSS=LOSS)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    R = repr
    return [
        ("CELL_TEMP_C", p["TC"]),
        ("TEMP_FACTOR", p["TF"]),
        ("DC_EXPECTED_KW", p["DCE"]),
        ("SOILING_RATIO", p["SR"]),
        ("SOILING_LOSS_PCT", p["LOSS"]),
        ("SOILING_LOSS_KW", f"{p['DCE']} * (1 - {p['SR']})"),
        ("PERF_INDEX", p["PI"]),
        ("PERF_INDEX_CORR", p["PIC"]),
        ("INV_EFF_EXPECTED", p["ETAE"]),
        ("INV_EFF_MEASURED", p["ETAM"]),
        ("AC_LIMIT_KW", p["LIM"]),
        ("AC_EXPECTED_KW", f"np.minimum({p['ETAE']} * df['P_DC_KW'], {p['LIM']})"),
        ("CLIPPING_LOSS_KW", f"np.maximum({p['ETA'](p['PAV'])} * {p['PAV']} - {p['LIM']}, 0)"),
        ("PR_INST", f"(df['P_AC_KW'] / np.maximum({R(k['p0'])} * df['POA_WM2'] / 1000, 0.1))"),
        ("PR_TEMP_CORR", f"(df['P_AC_KW'] / np.maximum({R(k['p0'])} * df['POA_WM2'] / 1000, 0.1)) / {p['TF']}"),
        ("STRING_MEAN_A", p["MEAN"]),
        ("STRING_EXPECTED_A", f"({R(k['imp'])} * df['POA_WM2'] / 1000 * (1 + {R(k['alpha'])} * ({p['TC']} - 25)) * {R(1 + k['bif'])} * {R(1 - k['dcl'])} * {p['W']} * {p['SR']})"),
        ("STRING_MIN_RATIO", p["MINR"]),
        ("INV_TEMP_EXPECTED_C", p["TIE"]),
        ("INV_TEMP_EXCESS_K", f"df['INV_TEMP_C'] - {p['TIE']}"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    g = r["poa_wm2"]
    tc = r["module_temp_c"] + g / 1000 * k["dt"]
    tf = 1 + k["gam"] * (tc - 25)
    w = warranty(k, r["years_in_service"])
    dce = k["p0"] * g / 1000 * tf * (1 + k["bif"]) * (1 - k["dcl"]) * w
    sr = r["poa_soiled_wm2"] / max(g, 1)
    pi = r["p_dc_kw"] / max(dce, 0.1)
    pic = pi / max(sr, 0.01)
    etae = eta_curve(k, r["p_dc_kw"])
    etam = r["p_ac_kw"] / max(r["p_dc_kw"], 0.1)
    lim = ac_limit(k, r["ambient_temp_c"], r["setpoint_pct"])
    pav = dce * sr
    s = strings(r)
    mean = sum(s) / N_STR
    pr = r["p_ac_kw"] / max(k["p0"] * g / 1000, 0.1)
    tie = r["ambient_temp_c"] + k["rise"] * r["p_ac_kw"] / k["pac0"]
    return {
        "cell_temp_c": tc, "temp_factor": tf, "dc_expected_kw": dce, "soiling_ratio": sr, "soiling_loss_pct": (1 - sr) * 100,
        "soiling_loss_kw": dce * (1 - sr), "perf_index": pi, "perf_index_corr": pic, "inv_eff_expected": etae,
        "inv_eff_measured": etam, "ac_limit_kw": lim, "ac_expected_kw": min(etae * r["p_dc_kw"], lim),
        "clipping_loss_kw": max(eta_curve(k, pav) * pav - lim, 0), "pr_inst": pr, "pr_temp_corr": pr / tf,
        "string_mean_a": mean,
        "string_expected_a": k["imp"] * g / 1000 * (1 + k["alpha"] * (tc - 25)) * (1 + k["bif"]) * (1 - k["dcl"]) * w * sr,
        "string_min_ratio": min(s) / max(mean, 0.01),
        "inv_temp_expected_c": tie, "inv_temp_excess_k": r["inv_temp_c"] - tie,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    R = repr
    DAY = f"(df['POA_WM2'] >= {R(k['gmin'])})"
    ON = "(df['INV_RUNNING'] > 0.5)"
    FREE = f"(df['P_AC_KW'] < {R(L['limited_frac'])} * df['P_MAX_KW'])"
    trig = R(k["soil_trigger_pct"])
    return [
        ("PV_RISO_TRIP", f"df['RISO_KOHM'] < {R(k['riso_lim'])}", "Critical", "ground_fault"),
        ("PV_INVERTER_DOWN", f"{DAY} & (df['INV_RUNNING'] < 0.5)", "High", "ground_fault"),
        ("PV_STRING_OPEN", f"{DAY} & {ON} & ({p['MINR']} < {R(L['string_open_ratio'])})", "High", "string_open"),
        ("PV_DC_UNDERPERFORM", f"{DAY} & {ON} & {FREE} & ({p['PIC']} < {R(L['pi_low'])})", "High", "module_degradation"),
        ("PV_CLEANING_DUE", f"{DAY} & ({p['LOSS']} >= {trig})", "Medium", "soiling"),
        ("PV_STRING_LOW", f"{DAY} & {ON} & ({p['MINR']} >= {R(L['string_open_ratio'])}) & ({p['MINR']} < {R(L['string_low_ratio'])})", "Medium", "string_bypass"),
        ("PV_RISO_LOW", f"(df['RISO_KOHM'] >= {R(k['riso_lim'])}) & (df['RISO_KOHM'] < {R(k['riso_alert'])})", "Medium", "ground_fault"),
        ("PV_INV_EFF_LOW", f"{ON} & (df['P_DC_KW'] > {R(L['min_dc_frac'] * k['pac0'])}) & ({p['ETAM']} < {p['ETAE']} - {R(L['eff_drop'])})", "Medium", "inverter_efficiency"),
        ("PV_INV_HOT", f"{ON} & ((df['INV_TEMP_C'] - {p['TIE']}) > {R(L['inv_temp_excess_k'])})", "Medium", "inverter_cooling"),
        ("PV_DERATE_EARLY", f"{ON} & (df['P_MAX_KW'] < {p['LIM']} - {R(L['derate_margin_kw'])})", "Medium", "inverter_cooling"),
        ("PV_IRRADIANCE_SENSOR", f"{DAY} & (({ON} & {FREE} & ({p['PI']} > {R(L['sensor_pi_high'])})) | ({p['SR']} > {R(L['sensor_sr_high'])}))", "Medium", "irradiance_sensor"),
        ("PV_SOILING_HIGH", f"{DAY} & ({p['LOSS']} >= {R(L['soiling_alert_pct'])}) & ({p['LOSS']} < {trig})", "Low", "soiling"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    day = r["poa_wm2"] >= k["gmin"]
    on = r["inv_running"] > 0.5
    free = r["p_ac_kw"] < L["limited_frac"] * r["p_max_kw"]
    minr, loss, s = t["string_min_ratio"], t["soiling_loss_pct"], strings(r)
    worst = s.index(min(s)) + 1
    add(r["riso_kohm"] < k["riso_lim"], "PV_RISO_TRIP", "Critical",
        f"Insulation resistance {r['riso_kohm']:.0f} kΩ, below {k['riso_lim']:.0f} kΩ: ground fault, the inverter must not connect", "cables", "ground_fault")
    add(day and r["inv_running"] < 0.5, "PV_INVERTER_DOWN", "High", f"Inverter off grid at {r['poa_wm2']:.0f} W/m²", "inverter", "ground_fault")
    add(day and on and minr < L["string_open_ratio"], "PV_STRING_OPEN", "High",
        f"String S{worst:02d} at {min(s):.1f} A while the mean is {t['string_mean_a']:.1f} A: open string", "string", "string_open")
    add(day and on and free and t["perf_index_corr"] < L["pi_low"], "PV_DC_UNDERPERFORM", "High",
        f"DC power {t['perf_index_corr'] * 100:.1f} % of expected once soiling is removed", "modules", "module_degradation")
    add(day and loss >= k["soil_trigger_pct"], "PV_CLEANING_DUE", "Medium",
        f"Soiling loss {loss:.1f} %, past the economic cleaning point {k['soil_trigger_pct']:.1f} %", "array", "soiling")
    add(day and on and L["string_open_ratio"] <= minr < L["string_low_ratio"], "PV_STRING_LOW", "Medium",
        f"String S{worst:02d} at {minr * 100:.0f} % of the mean", "string", "string_bypass")
    add(k["riso_lim"] <= r["riso_kohm"] < k["riso_alert"], "PV_RISO_LOW", "Medium", f"Insulation resistance {r['riso_kohm']:.0f} kΩ", "cables", "ground_fault")
    add(on and r["p_dc_kw"] > L["min_dc_frac"] * k["pac0"] and t["inv_eff_measured"] < t["inv_eff_expected"] - L["eff_drop"], "PV_INV_EFF_LOW", "Medium",
        f"Efficiency {t['inv_eff_measured'] * 100:.1f} % against {t['inv_eff_expected'] * 100:.1f} % on the curve", "inverter", "inverter_efficiency")
    add(on and t["inv_temp_excess_k"] > L["inv_temp_excess_k"], "PV_INV_HOT", "Medium",
        f"Inverter {r['inv_temp_c']:.0f} °C, {t['inv_temp_excess_k']:.0f} K above expected", "inverter", "inverter_cooling")
    add(on and r["p_max_kw"] < t["ac_limit_kw"] - L["derate_margin_kw"], "PV_DERATE_EARLY", "Medium",
        f"Inverter limits itself to {r['p_max_kw']:.0f} kW; its curve allows {t['ac_limit_kw']:.0f} kW at {r['ambient_temp_c']:.0f} °C", "inverter", "inverter_cooling")
    add(day and ((on and free and t["perf_index"] > L["sensor_pi_high"]) or t["soiling_ratio"] > L["sensor_sr_high"]), "PV_IRRADIANCE_SENSOR", "Medium",
        f"Performance index {t['perf_index']:.2f} and soiling ratio {t['soiling_ratio']:.2f}: the clean reference cell reads low", "weather station", "irradiance_sensor")
    add(day and L["soiling_alert_pct"] <= loss < k["soil_trigger_pct"], "PV_SOILING_HIGH", "Low", f"Soiling loss {loss:.1f} %", "array", "soiling")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
