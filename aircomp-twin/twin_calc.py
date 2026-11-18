"""The rotary screw air compressor twin's expectations (AC-4601, Atlas Copco GA 90 fixed speed, load/unload, dryer, receiver).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Notation (one reading): p = package outlet pressure (bar g), pin = inlet pressure (bar a), LF = load share (0..1),
n = load/unload cycles per hour, P = package input power (kW, mean of the window).

Free air delivery (FAD) and flow:
    Q_fad = Q_n x (1.01325 / pin) x (T_in + 273.15) / 273.15          flow meter (normal m3) back to inlet conditions
    FAD_exp(p) = FAD_cagi x (1 - a (p - p_cagi))                       CAGI capacity (ISO 1217 Annex C), corrected for pressure
    FAD ratio = (Q_fad / LF) / FAD_exp                                  free air per loaded minute against the data sheet
Power (CAGI line at the actual pressure):
    P_isen = pin x 1e5 x FAD_exp / 60 x k/(k-1) x ((p + pin)/pin)^((k-1)/k) - 1) / 1000     isentropic power, kW
    P_load = P_isen / eta_isen_cagi                                     package power loaded (reproduces 108.5 kW at 125 psig)
    f_bd = min(n x t_bd / 3600, 1 - LF)                                 share of time blowing down after an unload (~40 s each)
    P_exp = LF x P_load + f_bd x (P_load + P_0) / 2 + (1 - LF - f_bd) x P_0     P_0 = CAGI zero-flow power
    specific power = P / Q_fad, expected = P_exp / (LF x FAD_exp)
Storage and cycling (fill and empty the storage volume V between the load and unload pressures, band dp):
    cycles per hour = 60 x pin x FAD x LF (1 - LF) / (V x dp)           so V_effective = 60 pin FAD LF (1 - LF) / (dp x n)
Leaks (DOE load/unload method, no demand in the plant): leakage = T / (T + t) = load share of the test.
    leak flow = test load share x FAD_exp; leak power = test load share x (P_load - P_0)
Pressure above need: extra power = LF x (P_load(p) - P_load(p - excess)).
Water in the oil (Magnus): p_v = RH x 6.112 exp(17.62 T / (243.12 + T)) hPa at the inlet; at the element outlet the vapour
    pressure is multiplied by the pressure ratio; dew point = 243.12 L / (17.62 - L), L = ln(p_v2 / 6.112).
    margin = element outlet temperature - dew point: the oil must stay hotter than the dew point or water condenses in it.
"""


def _k(twin):
    d = twin["design"]
    c, a, ct, s, o, dr, m, lk = (d[x] for x in ("cagi", "air", "control", "system", "oil", "dryer", "motor", "leak"))
    k = a["k"]
    return dict(fad0=c["fad_m3min"], p0=c["full_load_barg"], af=a["fad_per_bar"], eta=c["eta_isen"], pu=c["p_zero_flow_kw"],
                pfull=c["p_full_kw"], spec_cagi=float(f"{c['p_full_kw'] / c['fad_m3min']:.10g}"),
                cpf=k / (k - 1), km=float(f"{(k - 1) / k:.10g}"), pref=a["inlet_ref_bara"],
                pl=ct["load_barg"], pu_set=ct["unload_barg"], band=float(f"{ct['unload_barg'] - ct['load_barg']:.10g}"), tbd=ct["blowdown_s"],
                vol=float(f"{s['receiver_m3'] + s['piping_m3']:.10g}"), preq=s["header_required_barg"], dpn=s["system_dp_normal_bar"],
                sep_chg=o["separator_dp_change_bar"], sep_new=o["separator_dp_new_bar"], pdp_lim=dr["pdp_class_limit_c"],
                fla=m["fla_a"], sf=m["service_factor"], leak_alert=lk["test_load_alert_pct"])


def p_load(k, p, pin, fad):
    """Package input power loaded (kW) at outlet pressure p (bar g), inlet pin (bar a), free air fad (m3/min)."""
    return pin * 100000 * fad / 60 * k["cpf"] * (((p + pin) / pin) ** k["km"] - 1) / 1000 / k["eta"]


def fad_exp(k, p):
    return k["fad0"] * (1 - k["af"] * (p - k["p0"]))


def p_avg(k, lf, pl, cyc):
    fb = min(cyc * k["tbd"] / 3600, 1 - lf)
    return lf * pl + fb * (pl + k["pu"]) / 2 + (1 - lf - fb) * k["pu"]


def dew_point(t_c, rh_pct, ratio):
    import math
    pv = rh_pct / 100 * 6.112 * math.exp(17.62 * t_c / (243.12 + t_c)) * ratio
    lg = math.log(pv / 6.112)
    return 243.12 * lg / (17.62 - lg)


def _parts(twin):
    k = _k(twin)
    PIN, PD, LF = "df['INLET_PRESSURE_BARA']", "df['DISCHARGE_PRESSURE_BARG']", "(df['LOAD_PCT'] / 100)"
    Q = f"(df['FLOW_NM3MIN'] * (1.01325 / {PIN}) * (df['INLET_TEMP_C'] + 273.15) / 273.15)"
    FE = f"({k['fad0']} * (1 - {k['af']} * ({PD} - {k['p0']})))"
    PLf = lambda p: f"({PIN} * 100000 * {FE} / 60 * {k['cpf']!r} * ((({p} + {PIN}) / {PIN}) ** {k['km']!r} - 1) / 1000 / {k['eta']})"
    PL = PLf(PD)
    FB = f"np.minimum(df['LOAD_CYCLES_PER_H'] * {k['tbd']} / 3600, 1 - {LF})"
    PE = f"({LF} * {PL} + {FB} * ({PL} + {k['pu']}) / 2 + (1 - {LF} - {FB}) * {k['pu']})"
    FL = f"({Q} / np.maximum({LF}, 0.01))"
    SP = f"(df['PACKAGE_POWER_KW'] / {Q})"
    SE = f"({PE} / (np.maximum({LF}, 0.01) * {FE}))"
    EX = f"(df['HEADER_PRESSURE_BARG'] - {k['preq']})"
    T = "df['INLET_TEMP_C']"
    LG = (f"np.log(df['INLET_RH_PCT'] / 100 * np.exp(17.62 * {T} / (243.12 + {T}))"
          f" * (({PD} + df['SEPARATOR_DP_BAR'] + {PIN}) / {PIN}))")
    TD = f"(243.12 * {LG} / (17.62 - {LG}))"
    CY = f"(60 * {PIN} * {FL} * {LF} * (1 - {LF}))"
    return dict(k=k, Q=Q, FE=FE, PL=PL, PLf=PLf, PE=PE, FL=FL, SP=SP, SE=SE, EX=EX, TD=TD, CY=CY, LF=LF, PD=PD)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("FLOW_FAD_M3MIN", p["Q"]),
        ("FAD_EXPECTED_M3MIN", p["FE"]),
        ("FAD_RATIO", f"{p['FL']} / {p['FE']}"),
        ("P_LOAD_EXPECTED_KW", p["PL"]),
        ("POWER_EXPECTED_KW", p["PE"]),
        ("POWER_RATIO", f"df['PACKAGE_POWER_KW'] / {p['PE']}"),
        ("SPEC_POWER_KW_M3MIN", p["SP"]),
        ("SPEC_POWER_EXPECTED", p["SE"]),
        ("SPEC_POWER_RATIO", f"{p['SP']} / {p['SE']}"),
        ("SPEC_POWER_VS_CAGI", f"{p['SP']} / {k['spec_cagi']!r}"),
        ("SYSTEM_DP_BAR", "df['DISCHARGE_PRESSURE_BARG'] - df['HEADER_PRESSURE_BARG']"),
        ("PRESSURE_EXCESS_BAR", p["EX"]),
        ("PRESSURE_EXCESS_KW", f"{p['LF']} * ({p['PL']} - {p['PLf'](p['PD'] + ' - np.maximum(' + p['EX'] + ', 0)')})"),
        ("LEAK_FLOW_M3MIN", f"df['LEAK_TEST_LOAD_PCT'] / 100 * {p['FE']}"),
        ("LEAK_POWER_KW", f"df['LEAK_TEST_LOAD_PCT'] / 100 * ({p['PL']} - {k['pu']})"),
        ("DEW_POINT_ELEMENT_C", p["TD"]),
        ("OIL_DEW_MARGIN_K", f"df['ELEMENT_OUTLET_TEMP_C'] - {p['TD']}"),
        ("CYCLES_EXPECTED_PER_H", f"{p['CY']} / ({k['vol']!r} * {k['band']!r})"),
        ("STORAGE_EFFECTIVE_M3", f"{p['CY']} / ({k['band']!r} * np.maximum(df['LOAD_CYCLES_PER_H'], 0.1))"),
        ("MOTOR_LOAD_PCT", f"df['MOTOR_CURRENT_A'] / {k['fla']} * 100"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    pin, pd, lf = r["inlet_pressure_bara"], r["discharge_pressure_barg"], r["load_pct"] / 100
    q = r["flow_nm3min"] * (1.01325 / pin) * (r["inlet_temp_c"] + 273.15) / 273.15
    fe = fad_exp(k, pd)
    pl = p_load(k, pd, pin, fe)
    pe = p_avg(k, lf, pl, r["load_cycles_per_h"])
    fl = q / max(lf, 0.01)
    sp = r["package_power_kw"] / q
    se = pe / (max(lf, 0.01) * fe)
    ex = r["header_pressure_barg"] - k["preq"]
    td = dew_point(r["inlet_temp_c"], r["inlet_rh_pct"], (pd + r["separator_dp_bar"] + pin) / pin)
    cy = 60 * pin * fl * lf * (1 - lf)
    return {
        "flow_fad_m3min": q, "fad_expected_m3min": fe, "fad_ratio": fl / fe,
        "p_load_expected_kw": pl, "power_expected_kw": pe, "power_ratio": r["package_power_kw"] / pe,
        "spec_power_kw_m3min": sp, "spec_power_expected": se, "spec_power_ratio": sp / se, "spec_power_vs_cagi": sp / k["spec_cagi"],
        "system_dp_bar": pd - r["header_pressure_barg"], "pressure_excess_bar": ex,
        "pressure_excess_kw": lf * (pl - p_load(k, pd - max(ex, 0), pin, fe)),
        "leak_flow_m3min": r["leak_test_load_pct"] / 100 * fe, "leak_power_kw": r["leak_test_load_pct"] / 100 * (pl - k["pu"]),
        "dew_point_element_c": td, "oil_dew_margin_k": r["element_outlet_temp_c"] - td,
        "cycles_expected_per_h": cy / (k["vol"] * k["band"]),
        "storage_effective_m3": cy / (k["band"] * max(r["load_cycles_per_h"], 0.1)),
        "motor_load_pct": r["motor_current_a"] / k["fla"] * 100,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    ex = dict(monitor_expressions(twin))
    return [
        ("AC_ELEMENT_TEMP_HIGH", f"df['ELEMENT_OUTLET_TEMP_C'] > {L['element_temp_alert_c']}", "High", "oil_cooler_fouled"),
        ("AC_OIL_DEW_MARGIN_LOW", f"({ex['OIL_DEW_MARGIN_K']}) < {L['dew_margin_alert_k']}", "High", "thermostat_stuck_open"),
        ("AC_PDP_HIGH", f"df['DRYER_PDP_C'] > {k['pdp_lim']}", "High", "dryer_fault"),
        ("AC_MOTOR_OVERLOAD", f"{ex['MOTOR_LOAD_PCT']} > {L['motor_load_alert_pct']}", "High", None),
        ("AC_SEPARATOR_DP_HIGH", f"df['SEPARATOR_DP_BAR'] > {k['sep_chg']}", "Medium", "separator_clogged"),
        ("AC_POWER_HIGH", f"{ex['POWER_RATIO']} > {L['power_ratio_alert']}", "Medium", "separator_clogged"),
        ("AC_FAD_LOW", f"{ex['FAD_RATIO']} < {L['fad_ratio_alert']}", "Medium", "element_wear"),
        ("AC_SPEC_POWER_HIGH", f"{ex['SPEC_POWER_RATIO']} > {L['spec_power_ratio_alert']}", "Medium", "element_wear"),
        ("AC_LEAK_HIGH", f"df['LEAK_TEST_LOAD_PCT'] > {k['leak_alert']}", "Medium", "leaks_growing"),
        ("AC_PRESSURE_EXCESS", f"{p['EX']} > {L['pressure_excess_alert_bar']}", "Medium", "pressure_setpoint_high"),
        ("AC_CYCLING_HIGH", f"df['LOAD_CYCLES_PER_H'] > {L['cycles_alert_per_h']}", "Medium", "receiver_isolated"),
        ("AC_SYSTEM_DP_HIGH", f"({ex['SYSTEM_DP_BAR']}) > {L['system_dp_alert_bar']}", "Medium", None),
        ("AC_STORAGE_LOW", f"{ex['STORAGE_EFFECTIVE_M3']} < {L['storage_ratio_alert'] * k['vol']:.6g}", "Low", "receiver_isolated"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    add(r["element_outlet_temp_c"] > L["element_temp_alert_c"], "AC_ELEMENT_TEMP_HIGH", "High",
        f"Element outlet {r['element_outlet_temp_c']:.0f} °C with {r['inlet_temp_c']:.0f} °C inlet air: the oil cooler cannot reject the heat", "cooler", "oil_cooler_fouled")
    add(t["oil_dew_margin_k"] < L["dew_margin_alert_k"], "AC_OIL_DEW_MARGIN_LOW", "High",
        f"Element outlet {r['element_outlet_temp_c']:.0f} °C only {t['oil_dew_margin_k']:.1f} K above the dew point ({t['dew_point_element_c']:.0f} °C): water condenses in the oil", "thermostat", "thermostat_stuck_open")
    add(r["dryer_pdp_c"] > k["pdp_lim"], "AC_PDP_HIGH", "High",
        f"Pressure dew point {r['dryer_pdp_c']:+.1f} °C, above +{k['pdp_lim']:.0f} °C (ISO 8573-1 class of the plant)", "dryer", "dryer_fault")
    add(t["motor_load_pct"] > L["motor_load_alert_pct"], "AC_MOTOR_OVERLOAD", "High",
        f"Motor current {r['motor_current_a']:.0f} A, {t['motor_load_pct']:.0f} % of nameplate: beyond the service factor", "motor")
    add(r["separator_dp_bar"] > k["sep_chg"], "AC_SEPARATOR_DP_HIGH", "Medium",
        f"Separator pressure drop {r['separator_dp_bar']:.2f} bar, past the {k['sep_chg']} bar change point", "separator", "separator_clogged")
    add(t["power_ratio"] > L["power_ratio_alert"], "AC_POWER_HIGH", "Medium",
        f"Package power {r['package_power_kw']:.0f} kW, {t['power_ratio']:.2f} × the CAGI line at this pressure and load", "element", "separator_clogged")
    add(t["fad_ratio"] < L["fad_ratio_alert"], "AC_FAD_LOW", "Medium",
        f"Free air per loaded minute {t['fad_ratio'] * t['fad_expected_m3min']:.1f} m³/min, {t['fad_ratio']:.2f} × the data sheet", "element", "element_wear")
    add(t["spec_power_ratio"] > L["spec_power_ratio_alert"], "AC_SPEC_POWER_HIGH", "Medium",
        f"Specific power {t['spec_power_kw_m3min']:.2f} kW per m³/min, {t['spec_power_ratio']:.2f} × expected at this load", "element", "element_wear")
    add(r["leak_test_load_pct"] > k["leak_alert"], "AC_LEAK_HIGH", "Medium",
        f"Leak test: loaded {r['leak_test_load_pct']:.0f} % of the time with no demand, {t['leak_flow_m3min']:.1f} m³/min of leaks", "system", "leaks_growing")
    add(t["pressure_excess_bar"] > L["pressure_excess_alert_bar"], "AC_PRESSURE_EXCESS", "Medium",
        f"Header {r['header_pressure_barg']:.2f} bar g, {t['pressure_excess_bar']:.2f} bar above need: {t['pressure_excess_kw']:.1f} kW", "control", "pressure_setpoint_high")
    add(r["load_cycles_per_h"] > L["cycles_alert_per_h"], "AC_CYCLING_HIGH", "Medium",
        f"{r['load_cycles_per_h']:.0f} load/unload cycles per hour (expected {t['cycles_expected_per_h']:.0f})", "storage", "receiver_isolated")
    add(t["system_dp_bar"] > L["system_dp_alert_bar"], "AC_SYSTEM_DP_HIGH", "Medium",
        f"{t['system_dp_bar']:.2f} bar lost between the compressor and the header: dryer or filters", "system")
    add(t["storage_effective_m3"] < L["storage_ratio_alert"] * k["vol"], "AC_STORAGE_LOW", "Low",
        f"Effective storage {t['storage_effective_m3']:.1f} m³ against {k['vol']:.0f} m³ installed", "storage", "receiver_isolated")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
