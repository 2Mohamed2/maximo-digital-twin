"""The gas turbine twin's expectations (GT-501, Siemens Energy SGT-400 13 MW, calibrated cycle stand-in).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (twin viewer, tests)

Performance model:
  theta = T1/288.15, delta = P1/101.325                     referred (corrected) conditions at the compressor inlet
  x = P / (delta * 12.9 MW)                                 corrected load, y = T1 in C
  expected fuel/delta, CDP/delta, CDT, EGT, NGG = 2-D polynomials in (x, y), fitted at build time to the CLEAN
  calibrated cycle at site conditions (twin file `expected_fit`)
  heat rate = fuel x LHV x 3600 / P (kJ/kWh), deviation in % against the expected heat rate
  compressor isentropic efficiency eta_c = T1 (PR^0.2857 - 1)/(T2 - T1), PR = CDP / P1, against the design value
  exhaust: average, spread (max - min) of the 6 thermocouples, and two robust indicators against the mean of the
  middle four: tc_low_dev (one TC far below = a sensor fault) and tc_high_dev (one sector hot = a burner fault)
"""
import math

TCS = [f"EGT_TC{i}_C" for i in range(1, 7)]


def _k(twin):
    f, d = twin["expected_fit"], twin["design"]
    return dict(f=f, terms=f["terms"], prated=d["rating"]["power_mw"], lhv=d["machine"]["fuel_lhv_mj_kg"] * 1000,
                eta_c=d["cycle"]["eta_c"] * 100)


def _poly(coef, terms, X, Y):
    out = []
    for c, (i, j) in zip(coef, terms):
        t = f"{c!r}"
        if i:
            t += f" * {X}" + (f"**{i}" if i > 1 else "")
        if j:
            t += f" * {Y}" + (f"**{j}" if j > 1 else "")
        out.append(t)
    return "(" + " + ".join(out) + ")"


def _polyv(coef, terms, x, y):
    return sum(c * x ** i * y ** j for c, (i, j) in zip(coef, terms))


def _parts(twin):
    k = _k(twin)
    f, T = k["f"], k["terms"]
    DE = "(df['INLET_PRESSURE_KPA'] / 101.325)"
    TH = "((df['INLET_TEMP_C'] + 273.15) / 288.15)"
    X = f"(df['POWER_MW'].clip(lower=0) / ({DE} * {k['prated']}))"
    Y = "df['INLET_TEMP_C']"
    S = "(" + " + ".join(f"df['{c}']" for c in TCS) + ")"
    MX = "df[" + repr(TCS) + "].max(axis=1)"
    MN = "df[" + repr(TCS) + "].min(axis=1)"
    MID = f"(({S} - {MX} - {MN}) / 4)"
    FUEL_E = f"({_poly(f['fuel_rel'], T, X, Y)} * {DE})"
    HR = f"(df['FUEL_FLOW_KG_S'] * {k['lhv']} * 3600 / (df['POWER_MW'].clip(lower=0.2) * 1000))"
    HRE = f"({FUEL_E} * {k['lhv']} * 3600 / (df['POWER_MW'].clip(lower=0.2) * 1000))"
    PR = "(df['CDP_BAR'] * 100 / df['INLET_PRESSURE_KPA'])"
    ETA = f"((df['INLET_TEMP_C'] + 273.15) * ({PR}.clip(lower=1.01) ** 0.2857142857 - 1) / (df['CDT_C'] - df['INLET_TEMP_C']).clip(lower=1) * 100)"
    return dict(DE=DE, TH=TH, X=X, Y=Y, S=S, MX=MX, MN=MN, MID=MID, FUEL_E=FUEL_E, HR=HR, HRE=HRE, PR=PR, ETA=ETA,
                CDPE=f"({_poly(f['cdp_rel'], T, X, Y)} * {DE})", CDTE=_poly(f["cdt"], T, X, Y), EGTE=_poly(f["egt"], T, X, Y),
                NGGE=_poly(f["ngg"], T, X, Y), k=k)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("THETA", p["TH"]),
        ("DELTA", p["DE"]),
        ("LOAD_CORR", p["X"]),
        ("EGT_AVG_C", f"{p['S']} / 6"),
        ("EGT_SPREAD_K", f"{p['MX']} - {p['MN']}"),
        ("TC_LOW_DEV_K", f"{p['MID']} - {p['MN']}"),
        ("TC_HIGH_DEV_K", f"{p['MX']} - {p['MID']}"),
        ("HEAT_RATE_KJ_KWH", p["HR"]),
        ("HR_EXPECTED_KJ_KWH", p["HRE"]),
        ("HR_DEV_PCT", f"({p['HR']} / {p['HRE']} - 1) * 100"),
        ("EFFICIENCY_PCT", f"360000 / {p['HR']}"),
        ("FUEL_EXPECTED_KG_S", p["FUEL_E"]),
        ("CDP_EXPECTED_BAR", p["CDPE"]),
        ("CDP_DEV_PCT", f"(df['CDP_BAR'] / {p['CDPE']} - 1) * 100"),
        ("CDT_EXPECTED_C", p["CDTE"]),
        ("EGT_EXPECTED_C", p["EGTE"]),
        ("EGT_DEV_K", f"{p['S']} / 6 - {p['EGTE']}"),
        ("NGG_EXPECTED_PCT", p["NGGE"]),
        ("NGG_CORR_PCT", f"df['NGG_PCT'] / np.sqrt({p['TH']})"),
        ("PRESSURE_RATIO", p["PR"]),
        ("ETA_C_PCT", p["ETA"]),
        ("ETA_C_EXPECTED_PCT", f"df['INLET_TEMP_C'] * 0 + {k['eta_c']}"),
        ("ETA_C_DEV_PTS", f"{p['ETA']} - {k['eta_c']}"),
        ("POWER_CORR_MW", f"df['POWER_MW'] / ({p['DE']} * np.sqrt({p['TH']}))"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    f, T = k["f"], k["terms"]
    de = r["inlet_pressure_kpa"] / 101.325
    th = (r["inlet_temp_c"] + 273.15) / 288.15
    x = max(r["power_mw"], 0) / (de * k["prated"])
    y = r["inlet_temp_c"]
    tcs = [r[f"egt_tc{i}_c"] for i in range(1, 7)]
    s, mx, mn = sum(tcs), max(tcs), min(tcs)
    mid = (s - mx - mn) / 4
    p = max(r["power_mw"], 0.2)
    fuel_e = _polyv(f["fuel_rel"], T, x, y) * de
    hr = r["fuel_flow_kg_s"] * k["lhv"] * 3600 / (p * 1000)
    hre = fuel_e * k["lhv"] * 3600 / (p * 1000)
    pr = r["cdp_bar"] * 100 / r["inlet_pressure_kpa"]
    eta = (r["inlet_temp_c"] + 273.15) * (max(pr, 1.01) ** 0.2857142857 - 1) / max(r["cdt_c"] - r["inlet_temp_c"], 1) * 100
    cdpe = _polyv(f["cdp_rel"], T, x, y) * de
    egte = _polyv(f["egt"], T, x, y)
    return {
        "theta": th, "delta": de, "load_corr": x, "egt_avg_c": s / 6, "egt_spread_k": mx - mn,
        "tc_low_dev_k": mid - mn, "tc_high_dev_k": mx - mid,
        "heat_rate_kj_kwh": hr, "hr_expected_kj_kwh": hre, "hr_dev_pct": (hr / hre - 1) * 100, "efficiency_pct": 360000 / hr if hr else 0.0,
        "fuel_expected_kg_s": fuel_e, "cdp_expected_bar": cdpe, "cdp_dev_pct": (r["cdp_bar"] / cdpe - 1) * 100,
        "cdt_expected_c": _polyv(f["cdt"], T, x, y), "egt_expected_c": egte, "egt_dev_k": s / 6 - egte,
        "ngg_expected_pct": _polyv(f["ngg"], T, x, y), "ngg_corr_pct": r["ngg_pct"] / math.sqrt(th),
        "pressure_ratio": pr, "eta_c_pct": eta, "eta_c_expected_pct": k["eta_c"], "eta_c_dev_pts": eta - k["eta_c"],
        "power_corr_mw": r["power_mw"] / (de * math.sqrt(th)),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    RUN = f"((df['POWER_MW'] > {L['min_load_frac'] * k['prated']}) & (df['FAULT_CODE'] == 0))"
    LOW, HIGH = f"({p['MID']} - {p['MN']})", f"({p['MX']} - {p['MID']})"
    SPREAD = f"({p['MX']} - {p['MN']})"
    ETAD = f"({p['ETA']} - {k['eta_c']})"
    return [
        ("GT_COMPRESSOR_FOULING", f"{RUN} & ({ETAD} < {L['eta_c_dev_alert_pts']})", "Medium", "compressor_fouling"),
        ("GT_HOT_SECTION", f"{RUN} & (({p['S']} / 6 - {p['EGTE']}) > {L['egt_dev_alert_k']}) & ({ETAD} > {L['eta_c_dev_alert_pts'] * 0.6})", "Medium", "hot_section"),
        ("GT_HEAT_RATE_HIGH", f"{RUN} & ((({p['HR']} / {p['HRE']} - 1) * 100) > {L['hr_dev_alert_pct']})", "Low", None),
        ("GT_EGT_SPREAD", f"{RUN} & ({SPREAD} > {L['egt_spread_alert_k']}) & ({SPREAD} <= {L['egt_spread_trip_k']}) & ({LOW} < {L['tc_low_alert_k']})", "High", "burner_fault"),
        ("GT_EGT_SPREAD_TRIP_LEVEL", f"{RUN} & ({SPREAD} > {L['egt_spread_trip_k']}) & ({LOW} < {L['tc_low_alert_k']})", "Critical", "burner_fault"),
        ("GT_EGT_TC_FAULT", f"{RUN} & ({LOW} > {L['tc_low_alert_k']}) & ({HIGH} < {L['tc_high_quiet_k']})", "Low", "thermocouple_fault"),
        ("GT_INLET_FILTER_DP", f"(df['INLET_FILTER_DP_PA'] > {L['filter_dp_alert_pa']}) & (df['INLET_FILTER_DP_PA'] <= {L['filter_dp_high_pa']})", "Medium", "inlet_filter"),
        ("GT_INLET_FILTER_DP_HIGH", f"df['INLET_FILTER_DP_PA'] > {L['filter_dp_high_pa']}", "High", "inlet_filter"),
        ("GT_GG_VIBRATION", f"df['GG_VIB_MM_S'] > {L['gg_vib_alert_mm_s']}", "Medium", None),
        ("GT_PT_BEARING", f"(df['PT_PROX_UM'] > {L['pt_prox_alert_um']}) | (df['BRG_PT_TEMP_C'] > {L['brg_temp_alert_c']})", "High", "bearing_wear"),
        ("GT_LUBE_OIL_HOT", f"df['LUBE_OIL_TEMP_C'] > {L['lube_temp_alert_c']}", "Medium", "lube_cooler"),
        ("GT_TRIP", "df['FAULT_CODE'] > 0", "Critical", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}
TRIPS = {2: "Trip: lube oil header temperature", 3: "Trip: power turbine shaft vibration"}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    run = r["power_mw"] > L["min_load_frac"] * twin["design"]["rating"]["power_mw"] and r.get("fault_code", 0) == 0
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    add(r.get("fault_code", 0) > 0, "GT_TRIP", "Critical", TRIPS.get(r.get("fault_code"), "Protection trip"), "package")
    add(run and t["eta_c_dev_pts"] < L["eta_c_dev_alert_pts"], "GT_COMPRESSOR_FOULING", "Medium",
        f"Compressor efficiency {t['eta_c_pct']:.1f} % ({t['eta_c_dev_pts']:+.1f} pts), heat rate {t['hr_dev_pct']:+.1f} %: wash", "compressor", "compressor_fouling")
    add(run and t["egt_dev_k"] > L["egt_dev_alert_k"] and t["eta_c_dev_pts"] > L["eta_c_dev_alert_pts"] * 0.6, "GT_HOT_SECTION", "Medium",
        f"Exhaust {t['egt_dev_k']:+.0f} K above the twin at {r['power_mw']:.1f} MW, compressor clean", "ct", "hot_section")
    add(run and t["hr_dev_pct"] > L["hr_dev_alert_pct"], "GT_HEAT_RATE_HIGH", "Low", f"Heat rate {t['hr_dev_pct']:+.1f} % above the twin", "combustor")
    sp, lo, hi = t["egt_spread_k"], t["tc_low_dev_k"], t["tc_high_dev_k"]
    add(run and L["egt_spread_alert_k"] < sp <= L["egt_spread_trip_k"] and lo < L["tc_low_alert_k"], "GT_EGT_SPREAD", "High",
        f"EGT spread {sp:.0f} K (one sector {hi:.0f} K hot): burner", "combustor", "burner_fault")
    add(run and sp > L["egt_spread_trip_k"] and lo < L["tc_low_alert_k"], "GT_EGT_SPREAD_TRIP_LEVEL", "Critical", f"EGT spread {sp:.0f} K at trip level", "combustor", "burner_fault")
    add(run and lo > L["tc_low_alert_k"] and hi < L["tc_high_quiet_k"], "GT_EGT_TC_FAULT", "Low",
        f"One exhaust thermocouple {lo:.0f} K below the others, no hot sector: sensor fault", "exhaust", "thermocouple_fault")
    dp = r["inlet_filter_dp_pa"]
    add(L["filter_dp_alert_pa"] < dp <= L["filter_dp_high_pa"], "GT_INLET_FILTER_DP", "Medium", f"Inlet filter dp {dp:.0f} Pa (alarm {L['filter_dp_alert_pa']:.0f})", "inlet", "inlet_filter")
    add(dp > L["filter_dp_high_pa"], "GT_INLET_FILTER_DP_HIGH", "High", f"Inlet filter dp {dp:.0f} Pa (shutdown level {L['filter_dp_high_pa']:.0f})", "inlet", "inlet_filter")
    add(r["gg_vib_mm_s"] > L["gg_vib_alert_mm_s"], "GT_GG_VIBRATION", "Medium", f"Gas generator casing {r['gg_vib_mm_s']:.1f} mm/s", "gg")
    add(r["pt_prox_um"] > L["pt_prox_alert_um"] or r["brg_pt_temp_c"] > L["brg_temp_alert_c"], "GT_PT_BEARING", "High",
        f"PT shaft {r['pt_prox_um']:.0f} µm pk-pk, drain {r['brg_pt_temp_c']:.0f} °C", "pt", "bearing_wear")
    add(r["lube_oil_temp_c"] > L["lube_temp_alert_c"], "GT_LUBE_OIL_HOT", "Medium", f"Lube oil header {r['lube_oil_temp_c']:.1f} °C", "lube", "lube_cooler")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
