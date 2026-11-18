"""The membrane bioreactor train twin's expectations (MBR-5301, submerged hollow-fibre ultrafiltration).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Flux and permeability (constant-flux operation, suction side):
    J  = Q x 1000 / A_in_service                       L/(m²·h), "LMH"; A_in_service = 40.0 m² x modules x cassettes in service
    K  = J / (TMP / 100)                               L/(m²·h·bar); TMP in kPa, 100 kPa = 1 bar
Temperature correction to 20 °C (the permeate is water: flux at a given TMP is inversely proportional to its viscosity):
    mu(T) = A exp(B / (T + 273.15 - C))                Vogel-Fulcher-Tammann fit for water, A = 0.02939 mPa·s, B = 507.88 K, C = 149.3 K
    TCF   = mu(T) / mu(20 °C)                          > 1 below 20 °C
    K20   = K x TCF
Fouling, from records the PLC keeps (Monitor works on one reading at a time):
    K20 after the last maintenance clean (MC) = J_mc / (TMP_after / 100) x TCF(T_mc)
    fouling rate (%/day)    = (K20_mc - K20) / K20_mc x 100 / days since the MC (at least one day)
    days to recovery clean  = (K20 - K_trigger) / (daily loss of K20)
    MC recovery (%)         = (TMP_before / TMP_after - 1) x 100   (same flux and temperature, minutes apart)
    irreversible loss (%)   = (1 - K20 after the last recovery clean / K20 of new fibres) x 100
    reversible loss (%)     = (1 - K20 / K20 after the last recovery clean) x 100
Air scour:
    SADm = air / A_in_service   Nm³/(m²·h)      SADp = air / Q   Nm³ per m³ of permeate
"""
import math


def _k(twin):
    d = twin["design"]
    m, tr, op, p, v, a, c = d["module"], d["train"], d["operation"], d["permeability"], d["viscosity"], d["aeration"], d["cleaning"]
    return dict(am=m["area_m2"] * tr["modules_per_cassette"], ncass=tr["cassettes"], area=tr["area_m2"], tmpmax=m["tmp_max_kpa"],
                jd=op["flux_design_lmh"], k0=p["k_new_20_lmhbar"], ktrig=p["k_rc_trigger_lmhbar"], klow=p["k_very_low_lmhbar"],
                va=v["a_mpas"], vb=v["b_k"], vc=v["c_k"], sadm=a["sadm_design"], mci=c["mc_interval_h"], rci=c["rc_interval_h"])


def mu(k, t):
    """Water viscosity (mPa·s) at t °C."""
    return k["va"] * math.exp(k["vb"] / (t + 273.15 - k["vc"]))


def tcf(k, t):
    """Viscosity ratio mu(t) / mu(20 °C): multiply a permeability at t by it to get the permeability at 20 °C."""
    return math.exp(k["vb"] / (t + 273.15 - k["vc"]) - k["vb"] / (293.15 - k["vc"]))


def _parts(twin):
    k = _k(twin)
    T = lambda col: f"np.exp({k['vb']} / (df['{col}'] + {273.15 - k['vc']:.2f}) - {k['vb'] / (293.15 - k['vc']):.12g})"
    J = f"(df['PERMEATE_FLOW_M3H'] * 1000 / ({k['am']} * df['CASSETTES_IN_SERVICE']))"
    TCF = T("ML_TEMP_C")
    K20 = f"({J} / (df['TMP_KPA'] / 100) * {TCF})"
    KMC = f"(df['MC_FLUX_LMH'] / (df['MC_TMP_AFTER_KPA'] / 100) * {T('MC_TEMP_C')})"
    DAYS = "(np.maximum(df['HOURS_SINCE_MC'], 24) / 24)"
    LOSS = f"(({KMC} - {K20}) / {DAYS})"
    RATE = f"({LOSS} / {KMC} * 100)"
    DRC = f"(({K20} - {k['ktrig']}) / np.maximum({LOSS}, 0.01))"
    SADM = f"(df['AIR_SCOUR_NM3H'] / ({k['am']} * df['CASSETTES_IN_SERVICE']))"
    MCR = "((df['MC_TMP_BEFORE_KPA'] / df['MC_TMP_AFTER_KPA'] - 1) * 100)"
    IRR = f"((1 - df['RC_PERM20_LMHBAR'] / {k['k0']}) * 100)"
    return dict(k=k, J=J, TCF=TCF, K20=K20, KMC=KMC, RATE=RATE, DRC=DRC, SADM=SADM, MCR=MCR, IRR=IRR)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("FLUX_LMH", p["J"]),
        ("FLUX_RATIO", f"{p['J']} / {k['jd']}"),
        ("TCF", p["TCF"]),
        ("PERM_LMH_BAR", f"{p['J']} / (df['TMP_KPA'] / 100)"),
        ("PERM20_LMH_BAR", p["K20"]),
        ("PERM20_RATIO", f"{p['K20']} / {k['k0']}"),
        ("TMP_CLEAN_KPA", f"{p['J']} * {p['TCF']} / df['RC_PERM20_LMHBAR'] * 100"),
        ("TMP_MARGIN_KPA", f"{k['tmpmax']} - df['TMP_KPA']"),
        ("PERM20_AFTER_MC", p["KMC"]),
        ("FOULING_RATE_PCT_D", p["RATE"]),
        ("DAYS_TO_RC", p["DRC"]),
        ("MC_RECOVERY_PCT", p["MCR"]),
        ("IRREVERSIBLE_LOSS_PCT", p["IRR"]),
        ("REVERSIBLE_LOSS_PCT", f"(1 - {p['K20']} / df['RC_PERM20_LMHBAR']) * 100"),
        ("SADM", p["SADM"]),
        ("SADM_RATIO", f"{p['SADM']} / {k['sadm']}"),
        ("SADP", "df['AIR_SCOUR_NM3H'] / df['PERMEATE_FLOW_M3H']"),
        ("SPEC_ENERGY_KWH_M3", "(df['SCOUR_BLOWER_KW'] + df['PERMEATE_PUMP_KW']) / df['PERMEATE_FLOW_M3H']"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    am = k["am"] * r["cassettes_in_service"]
    j = r["permeate_flow_m3h"] * 1000 / am
    f = tcf(k, r["ml_temp_c"])
    kt = j / (r["tmp_kpa"] / 100)
    k20 = kt * f
    kmc = r["mc_flux_lmh"] / (r["mc_tmp_after_kpa"] / 100) * tcf(k, r["mc_temp_c"])
    days = max(r["hours_since_mc"], 24) / 24
    loss = (kmc - k20) / days
    sadm = r["air_scour_nm3h"] / am
    return {
        "flux_lmh": j, "flux_ratio": j / k["jd"], "tcf": f, "perm_lmh_bar": kt, "perm20_lmh_bar": k20, "perm20_ratio": k20 / k["k0"],
        "tmp_clean_kpa": j * f / r["rc_perm20_lmhbar"] * 100, "tmp_margin_kpa": k["tmpmax"] - r["tmp_kpa"],
        "perm20_after_mc": kmc, "fouling_rate_pct_d": loss / kmc * 100, "days_to_rc": (k20 - k["ktrig"]) / max(loss, 0.01),
        "mc_recovery_pct": (r["mc_tmp_before_kpa"] / r["mc_tmp_after_kpa"] - 1) * 100,
        "irreversible_loss_pct": (1 - r["rc_perm20_lmhbar"] / k["k0"]) * 100,
        "reversible_loss_pct": (1 - k20 / r["rc_perm20_lmhbar"]) * 100,
        "sadm": sadm, "sadm_ratio": sadm / k["sadm"], "sadp": r["air_scour_nm3h"] / r["permeate_flow_m3h"],
        "spec_energy_kwh_m3": (r["scour_blower_kw"] + r["permeate_pump_kw"]) / r["permeate_flow_m3h"],
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    K20 = p["K20"]
    TU = "df['PERMEATE_TURBIDITY_NTU']"
    return [
        ("MBR_INTEGRITY_BREACH", f"{TU} > {L['turbidity_breach_ntu']}", "Critical", "fibre_breakage"),
        ("MBR_TMP_HIGH", f"df['TMP_KPA'] > {L['tmp_high_kpa']}", "High", "sludging"),
        ("MBR_PERM_VERY_LOW", f"{K20} < {k['klow']}", "High", "sludging"),
        ("MBR_SCOUR_LOW", f"{p['SADM']} / {k['sadm']} < {L['sadm_ratio_min']}", "High", "air_scour_low"),
        ("MBR_PERM_LOW", f"({K20} >= {k['klow']}) & ({K20} < {k['ktrig']})", "Medium", "irreversible_fouling"),
        ("MBR_CLEAN_DUE_SOON", f"({K20} >= {k['ktrig']}) & ({p['DRC']} < {L['days_to_rc_alert']})", "Medium", "poor_filterability"),
        ("MBR_FOULING_FAST", f"{p['RATE']} > {L['fouling_rate_alert_pct_d']}", "Medium", "poor_filterability"),
        ("MBR_MC_INEFFECTIVE", f"{p['MCR']} < {L['mc_recovery_min_pct']}", "Medium", "irreversible_fouling"),
        ("MBR_IRREVERSIBLE_HIGH", f"{p['IRR']} > {L['irreversible_alert_pct']}", "Medium", "irreversible_fouling"),
        ("MBR_FLUX_HIGH", f"{p['J']} / {k['jd']} > {L['flux_ratio_alert']}", "Medium", "peak_flux"),
        ("MBR_TURBIDITY_HIGH", f"({TU} > {L['turbidity_alert_ntu']}) & ({TU} <= {L['turbidity_breach_ntu']})", "Medium", "fibre_breakage"),
        ("MBR_MLSS_HIGH", f"df['MLSS_MGL'] > {L['mlss_max_mgl']}", "Medium", "sludging"),
        ("MBR_FILTERABILITY_POOR", f"df['SLUDGE_TTF_S'] > {L['ttf_max_s']}", "Medium", "poor_filterability"),
        ("MBR_MC_OVERDUE", f"df['HOURS_SINCE_MC'] > {L['mc_overdue_factor'] * k['mci']}", "Medium", "mc_skipped"),
        ("MBR_RC_OVERDUE", f"df['HOURS_SINCE_RC'] > {L['rc_overdue_factor'] * k['rci']}", "Low", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    tu, k20 = r["permeate_turbidity_ntu"], t["perm20_lmh_bar"]
    add(tu > L["turbidity_breach_ntu"], "MBR_INTEGRITY_BREACH", "Critical",
        f"Permeate turbidity {tu:.2f} NTU, above {L['turbidity_breach_ntu']} NTU: broken fibres, isolate the cassette and run an integrity test", "membrane", "fibre_breakage")
    add(r["tmp_kpa"] > L["tmp_high_kpa"], "MBR_TMP_HIGH", "High",
        f"TMP {r['tmp_kpa']:.1f} kPa, above {L['tmp_high_kpa']:.0f} kPa (module limit {k['tmpmax']:.0f} kPa)", "membrane", "sludging")
    add(k20 < k["klow"], "MBR_PERM_VERY_LOW", "High", f"Permeability {k20:.0f} L/(m²·h·bar) at 20 °C, below {k['klow']:.0f}", "membrane", "sludging")
    add(t["sadm_ratio"] < L["sadm_ratio_min"], "MBR_SCOUR_LOW", "High",
        f"Air scour {t['sadm']:.3f} Nm³/(m²·h), {t['sadm_ratio'] * 100:.0f} % of design", "air", "air_scour_low")
    add(k["klow"] <= k20 < k["ktrig"], "MBR_PERM_LOW", "Medium",
        f"Permeability {k20:.0f} L/(m²·h·bar) at 20 °C, below the recovery-clean trigger {k['ktrig']:.0f}", "membrane", "irreversible_fouling")
    add(k20 >= k["ktrig"] and t["days_to_rc"] < L["days_to_rc_alert"], "MBR_CLEAN_DUE_SOON", "Medium",
        f"At this fouling rate the recovery-clean trigger is {t['days_to_rc']:.1f} days away", "membrane", "poor_filterability")
    add(t["fouling_rate_pct_d"] > L["fouling_rate_alert_pct_d"], "MBR_FOULING_FAST", "Medium",
        f"Permeability falling {t['fouling_rate_pct_d']:.1f} % per day since the last maintenance clean", "membrane", "poor_filterability")
    add(t["mc_recovery_pct"] < L["mc_recovery_min_pct"], "MBR_MC_INEFFECTIVE", "Medium",
        f"Last maintenance clean recovered only {t['mc_recovery_pct']:.1f} % of permeability", "cleaning", "irreversible_fouling")
    add(t["irreversible_loss_pct"] > L["irreversible_alert_pct"], "MBR_IRREVERSIBLE_HIGH", "Medium",
        f"{t['irreversible_loss_pct']:.0f} % of the new-fibre permeability no longer comes back after a recovery clean", "membrane", "irreversible_fouling")
    add(t["flux_ratio"] > L["flux_ratio_alert"], "MBR_FLUX_HIGH", "Medium",
        f"Flux {t['flux_lmh']:.1f} L/(m²·h) on {r['cassettes_in_service']:.0f} cassettes, {t['flux_ratio']:.2f} x design", "operation", "peak_flux")
    add(L["turbidity_alert_ntu"] < tu <= L["turbidity_breach_ntu"], "MBR_TURBIDITY_HIGH", "Medium",
        f"Permeate turbidity {tu:.2f} NTU, above {L['turbidity_alert_ntu']} NTU", "membrane", "fibre_breakage")
    add(r["mlss_mgl"] > L["mlss_max_mgl"], "MBR_MLSS_HIGH", "Medium", f"MLSS {r['mlss_mgl']:.0f} mg/L in the membrane tank", "biology", "sludging")
    add(r["sludge_ttf_s"] > L["ttf_max_s"], "MBR_FILTERABILITY_POOR", "Medium", f"Time-to-filter {r['sludge_ttf_s']:.0f} s, above {L['ttf_max_s']:.0f} s", "biology", "poor_filterability")
    add(r["hours_since_mc"] > L["mc_overdue_factor"] * k["mci"], "MBR_MC_OVERDUE", "Medium",
        f"Last maintenance clean {r['hours_since_mc']:.0f} h ago (plan every {k['mci']:.0f} h)", "cleaning", "mc_skipped")
    add(r["hours_since_rc"] > L["rc_overdue_factor"] * k["rci"], "MBR_RC_OVERDUE", "Low", f"Last recovery clean {r['hours_since_rc']:.0f} h ago", "cleaning")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
