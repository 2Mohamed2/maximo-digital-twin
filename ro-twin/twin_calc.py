"""The RO train twin's expectations (DuPont FilmTec SW30HRLE-440i, 40 vessels x 7 elements, PX energy recovery).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (twin viewer, tests)

Normalisation (ASTM D4516 style; the membrane-feed / concentrate average is used for the feed-side salinity):
  dP_v   = PDIT across the vessel rack               vessel pressure drop (feed to concentrate header)
  C_fc   = (C_feed,membrane + C_conc) / 2           average feed-concentrate salinity
  NDP    = P_feed - dP_v/2 - P_perm - 0.79e-3 (C_fc - C_perm)        net driving pressure, bar
  TCF    = exp(2640 (1/298.15 - 1/(273.15 + T)))    temperature correction factor (FilmTec form)
  NPF    = Q_perm * (NDP_ref / NDP) / TCF           normalised permeate flow (25 C, reference NDP), m3/h
  NSP    = (C_perm / C_fc) * (NDP / NDP_ref)        normalised salt passage (A and B share the TCF, so it cancels)
  NdP    = dP_v * (Qavg_ref / Qavg)^1.5             normalised pressure drop, Qavg = (Q_membrane feed + Q_conc)/2
Each is reported as % of the clean-membrane baseline: the same formulas applied to the clean physics model at build time,
fitted as c0 + c1 T + c2 T^2 (twin file twin_model.baseline). The ASTM formulas use the arithmetic feed-concentrate average;
on a 7-element seawater vessel the flux moves to the lead elements as the water warms, so even clean membranes drift about
1 % per degree C. Dividing by the temperature-dependent clean baseline removes that drift, so a warm intake does not alarm. Cleaning triggers (membrane-manufacturer practice): NPF -10 %, NSP +10 %, NdP +15 %.
The expected permeate flow at today's conditions is NPF_baseline(T) * TCF * NDP / NDP_ref: what clean membranes would make.

Pumps and energy recovery:
  HP pump wire-to-water efficiency = Q (P_d - P_s) / 36 / P_el   vs. the assumed curve eta_bep (1 - 0.8 (Q/Q_bep - 1)^2) eta_motor
  PX efficiency = (Q_hp,out P_hp,out + Q_lp,out P_lp,out) / (Q_conc P_conc + Q_lp,in P_lp,in)
  PX leakage    = (Q_lp,out - Q_lp,in) / Q_conc;  mixing = (C_mf - C_f) Q_mf / ((C_conc - C_f) Q_px,out)
  Specific energy = (P_HP + P_booster) / Q_perm, kWh/m3
"""
import math

KOS = 0.00079


def _k(twin):
    d = twin["design"]
    b = twin["twin_model"]["baseline"]
    hp = d["hp_pump"]
    return dict(ndp_ref=b["ndp_ref_bar"], qavg_ref=b["qavg_ref_m3h"], npf0=b["npf_poly"], nsp0=b["nsp_poly"], ndpn0=b["ndp_poly"],
                eta_bep=hp["eta_bep"], q_bep=hp["q_bep_m3h"], eta_m=hp["eta_motor"])


def poly(c, t):
    """Clean-membrane baseline c0 + c1 T + c2 T^2 (same expression in Python and pandas)."""
    return c[0] + c[1] * t + c[2] * t ** 2


def poly_expr(c):
    return f"({c[0]} + {c[1]} * df['FEED_TEMP_C'] + {c[2]} * df['FEED_TEMP_C'] ** 2)"


def tcf(t):
    return math.exp(2640.0 * (1.0 / 298.15 - 1.0 / (273.15 + t)))


def raw_norm(r, ndp_ref, qavg_ref):
    """Normalised values in absolute units (used at build time for the baseline and by evaluate)."""
    dpv = r["vessel_dp_bar"]
    cfc = (r["membrane_feed_tds_mgl"] + r["concentrate_tds_mgl"]) / 2
    ndp = r["membrane_feed_pressure_bar"] - dpv / 2 - r["permeate_pressure_bar"] - KOS * (cfc - r["permeate_tds_mgl"])
    f = tcf(r["feed_temp_c"])
    qm = r["hp_flow_m3h"] + r["px_hp_out_flow_m3h"]
    qavg = (qm + r["concentrate_flow_m3h"]) / 2
    return {"dpv": dpv, "cfc": cfc, "ndp": ndp, "tcf": f, "qm": qm,
            "npf": r["permeate_flow_m3h"] * (ndp_ref / ndp) / f,
            "nsp": (r["permeate_tds_mgl"] / cfc) * (ndp / ndp_ref),
            "ndpn": dpv * (qavg_ref / qavg) ** 1.5}


def _parts(twin):
    k = _k(twin)
    PF, PP = "df['MEMBRANE_FEED_PRESSURE_BAR']", "df['PERMEATE_PRESSURE_BAR']"
    DPV = "df['VESSEL_DP_BAR']"
    CFC = "((df['MEMBRANE_FEED_TDS_MGL'] + df['CONCENTRATE_TDS_MGL']) / 2)"
    NDP = f"({PF} - {DPV} / 2 - {PP} - {KOS} * ({CFC} - df['PERMEATE_TDS_MGL']))"
    TCF = "np.exp(2640.0 * (1.0 / 298.15 - 1.0 / (273.15 + df['FEED_TEMP_C'])))"
    QM = "(df['HP_FLOW_M3H'] + df['PX_HP_OUT_FLOW_M3H'])"
    QAVG = f"(({QM} + df['CONCENTRATE_FLOW_M3H']) / 2)"
    NPF = f"(df['PERMEATE_FLOW_M3H'] * ({k['ndp_ref']} / {NDP}) / {TCF})"
    NSP = f"((df['PERMEATE_TDS_MGL'] / {CFC}) * ({NDP} / {k['ndp_ref']}))"
    NDPN = f"({DPV} * ({k['qavg_ref']} / {QAVG}) ** 1.5)"
    N0, S0, D0 = poly_expr(k["npf0"]), poly_expr(k["nsp0"]), poly_expr(k["ndpn0"])
    NPFP, NSPP, NDPP = f"({NPF} / {N0} * 100)", f"({NSP} / {S0} * 100)", f"({NDPN} / {D0} * 100)"
    QE = f"({N0} * {TCF} * {NDP} / {k['ndp_ref']})"
    HPETA = "(df['HP_FLOW_M3H'] * (df['HP_DISCHARGE_PRESSURE_BAR'] - df['HP_SUCTION_PRESSURE_BAR']) / 36 / df['HP_POWER_KW'].clip(lower=1) * 100)"
    HPETAE = f"({k['eta_bep']} * (1 - 0.8 * (df['HP_FLOW_M3H'] / {k['q_bep']} - 1) ** 2) * {k['eta_m']} * 100)"
    PXEFF = ("((df['PX_HP_OUT_FLOW_M3H'] * df['PX_HP_OUT_PRESSURE_BAR'] + df['PX_LP_OUT_FLOW_M3H'] * df['PX_LP_OUT_PRESSURE_BAR']) / "
             "(df['CONCENTRATE_FLOW_M3H'] * df['CONCENTRATE_PRESSURE_BAR'] + df['PX_LP_IN_FLOW_M3H'] * df['PX_LP_IN_PRESSURE_BAR']) * 100)")
    PXLK = "((df['PX_LP_OUT_FLOW_M3H'] - df['PX_LP_IN_FLOW_M3H']) / df['CONCENTRATE_FLOW_M3H'].clip(lower=1) * 100)"
    MIX = (f"((df['MEMBRANE_FEED_TDS_MGL'] - df['FEED_TDS_MGL']) * {QM} / "
           "((df['CONCENTRATE_TDS_MGL'] - df['FEED_TDS_MGL']).clip(lower=1) * df['PX_HP_OUT_FLOW_M3H'].clip(lower=1)) * 100)")
    B = [f"df['BANK{i}_PERMEATE_TDS_MGL']" for i in range(1, 5)]
    BANK = f"(np.maximum(np.maximum({B[0]}, {B[1]}), np.maximum({B[2]}, {B[3]})) / (({B[0]} + {B[1]} + {B[2]} + {B[3]}) / 4).clip(lower=1))"
    SEC = "((df['HP_POWER_KW'] + df['BOOSTER_POWER_KW']) / df['PERMEATE_FLOW_M3H'].clip(lower=1))"
    REC = f"(df['PERMEATE_FLOW_M3H'] / {QM} * 100)"
    return dict(NDP=NDP, NPFP=NPFP, NSPP=NSPP, NDPP=NDPP, QE=QE, HPETA=HPETA, HPETAE=HPETAE, PXEFF=PXEFF, PXLK=PXLK, MIX=MIX,
                BANK=BANK, SEC=SEC, REC=REC, TCF=TCF, k=k)


def monitor_expressions(twin):
    p = _parts(twin)
    return [
        ("NDP_BAR", p["NDP"]),
        ("TCF", p["TCF"]),
        ("NPF_PCT", p["NPFP"]),
        ("NSP_PCT", p["NSPP"]),
        ("NDP_NORM_PCT", p["NDPP"]),
        ("PERMEATE_EXPECTED_M3H", p["QE"]),
        ("PERMEATE_DEVIATION_PCT", f"(df['PERMEATE_FLOW_M3H'] / {p['QE']} - 1) * 100"),
        ("RECOVERY_PCT", p["REC"]),
        ("HP_PUMP_EFF_PCT", p["HPETA"]),
        ("HP_PUMP_EFF_EXPECTED_PCT", p["HPETAE"]),
        ("HP_PUMP_EFF_DEV_PTS", f"{p['HPETA']} - {p['HPETAE']}"),
        ("PX_EFF_PCT", p["PXEFF"]),
        ("PX_LEAKAGE_PCT", p["PXLK"]),
        ("PX_MIXING_PCT", p["MIX"]),
        ("BANK_TDS_RATIO", p["BANK"]),
        ("SEC_KWH_M3", p["SEC"]),
        ("SALT_REJECTION_PCT", "(1 - df['PERMEATE_TDS_MGL'] / df['MEMBRANE_FEED_TDS_MGL']) * 100"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    n = raw_norm(r, k["ndp_ref"], k["qavg_ref"])
    T = r["feed_temp_c"]
    n0, s0, d0 = poly(k["npf0"], T), poly(k["nsp0"], T), poly(k["ndpn0"], T)
    qe = n0 * n["tcf"] * n["ndp"] / k["ndp_ref"]
    hpe = r["hp_flow_m3h"] * (r["hp_discharge_pressure_bar"] - r["hp_suction_pressure_bar"]) / 36 / max(r["hp_power_kw"], 1) * 100
    hpx = k["eta_bep"] * (1 - 0.8 * (r["hp_flow_m3h"] / k["q_bep"] - 1) ** 2) * k["eta_m"] * 100
    pxe = ((r["px_hp_out_flow_m3h"] * r["px_hp_out_pressure_bar"] + r["px_lp_out_flow_m3h"] * r["px_lp_out_pressure_bar"]) /
           (r["concentrate_flow_m3h"] * r["concentrate_pressure_bar"] + r["px_lp_in_flow_m3h"] * r["px_lp_in_pressure_bar"]) * 100)
    b = [r[f"bank{i}_permeate_tds_mgl"] for i in range(1, 5)]
    return {
        "ndp_bar": n["ndp"], "tcf": n["tcf"],
        "npf_pct": n["npf"] / n0 * 100, "nsp_pct": n["nsp"] / s0 * 100, "ndp_norm_pct": n["ndpn"] / d0 * 100,
        "permeate_expected_m3h": qe, "permeate_deviation_pct": (r["permeate_flow_m3h"] / qe - 1) * 100,
        "recovery_pct": r["permeate_flow_m3h"] / n["qm"] * 100,
        "hp_pump_eff_pct": hpe, "hp_pump_eff_expected_pct": hpx, "hp_pump_eff_dev_pts": hpe - hpx,
        "px_eff_pct": pxe,
        "px_leakage_pct": (r["px_lp_out_flow_m3h"] - r["px_lp_in_flow_m3h"]) / max(r["concentrate_flow_m3h"], 1) * 100,
        "px_mixing_pct": ((r["membrane_feed_tds_mgl"] - r["feed_tds_mgl"]) * n["qm"] /
                          (max(r["concentrate_tds_mgl"] - r["feed_tds_mgl"], 1) * max(r["px_hp_out_flow_m3h"], 1)) * 100),
        "bank_tds_ratio": max(b) / max(sum(b) / 4, 1),
        "sec_kwh_m3": (r["hp_power_kw"] + r["booster_power_kw"]) / max(r["permeate_flow_m3h"], 1),
        "salt_rejection_pct": (1 - r["permeate_tds_mgl"] / r["membrane_feed_tds_mgl"]) * 100,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    NPF, NSP, NDP = p["NPFP"], p["NSPP"], p["NDPP"]
    return [
        ("RO_NPF_LOW", f"{NPF} < {L['npf_low_pct']}", "Medium", None),
        ("RO_NSP_HIGH", f"{NSP} > {L['nsp_high_pct']}", "Low", None),
        ("RO_BIOFOULING", f"{NDP} > {L['ndp_high_pct']}", "Medium", "biofouling"),
        ("RO_SCALING", f"({NPF} < {L['scaling_npf_pct']}) & ({NSP} > {L['scaling_nsp_pct']}) & ({NDP} < {L['scaling_ndp_max_pct']})", "Medium", "scaling"),
        ("RO_OXIDATION", f"({NSP} > {L['oxidation_nsp_pct']}) & ({NPF} > {L['oxidation_npf_pct']})", "High", "oxidation"),
        ("RO_OXIDANT_IN_FEED", f"df['FEED_ORP_MV'] > {L['orp_alert_mv']}", "High", "oxidation"),
        ("RO_BANK_LEAK", f"{p['BANK']} > {L['bank_ratio_alert']}", "Medium", "oring_leak"),
        ("RO_HP_PUMP", f"({p['HPETA']} - {p['HPETAE']}) < -{L['hp_eff_dev_alert_pts']}", "Medium", "hp_pump_wear"),
        ("RO_ERD", f"({p['PXEFF']} < {L['px_eff_alert_pct']}) | ({p['MIX']} > {L['px_mixing_alert_pct']}) | ({p['PXLK']} > {L['px_leakage_alert_pct']})", "Medium", "erd_leakage"),
        ("RO_CARTRIDGE_DP", f"df['CF_DP_BAR'] > {L['cf_dp_alert_bar']}", "Medium", "cartridge_clogging"),
        ("RO_LOW_SUCTION", f"df['HP_SUCTION_PRESSURE_BAR'] < {L['suction_low_bar']}", "High", "cartridge_clogging"),
        ("RO_PRESSURE_HIGH", f"df['MEMBRANE_FEED_PRESSURE_BAR'] > {L['feed_pressure_alert_bar']}", "High", None),
        ("RO_PERMEATE_QUALITY", f"df['PERMEATE_TDS_MGL'] > {L['permeate_tds_alert_mgl']}", "Medium", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    npf, nsp, ndp = t["npf_pct"], t["nsp_pct"], t["ndp_norm_pct"]
    trio = f"NPF {npf:.0f} %, NSP {nsp:.0f} %, NdP {ndp:.0f} %"
    add(npf < L["npf_low_pct"], "RO_NPF_LOW", "Medium", f"Normalised permeate flow {npf:.0f} % of clean: clean-in-place due ({trio})", "membranes")
    add(nsp > L["nsp_high_pct"], "RO_NSP_HIGH", "Low", f"Normalised salt passage {nsp:.0f} % of clean ({trio})", "membranes")
    add(ndp > L["ndp_high_pct"], "RO_BIOFOULING", "Medium", f"Normalised pressure drop {ndp:.0f} % of clean: fouling at the lead elements ({trio})",
        "lead", "biofouling")
    add(npf < L["scaling_npf_pct"] and nsp > L["scaling_nsp_pct"] and ndp < L["scaling_ndp_max_pct"], "RO_SCALING", "Medium",
        f"Flow down and salt passage up with a normal pressure drop: scale on the tail elements ({trio})", "tail", "scaling")
    add(nsp > L["oxidation_nsp_pct"] and npf > L["oxidation_npf_pct"], "RO_OXIDATION", "High",
        f"Salt passage and flow both up: oxidised membrane ({trio})", "membranes", "oxidation")
    add(r["feed_orp_mv"] > L["orp_alert_mv"], "RO_OXIDANT_IN_FEED", "High", f"Feed ORP {r['feed_orp_mv']:.0f} mV: chlorine reaching the membranes", "intake", "oxidation")
    add(t["bank_tds_ratio"] > L["bank_ratio_alert"], "RO_BANK_LEAK", "Medium",
        f"Bank permeate salinity {t['bank_tds_ratio']:.2f} x the train average: O-ring / interconnector leak "
        f"(banks {r['bank1_permeate_tds_mgl']:.0f}/{r['bank2_permeate_tds_mgl']:.0f}/{r['bank3_permeate_tds_mgl']:.0f}/{r['bank4_permeate_tds_mgl']:.0f} mg/L)",
        "permeate", "oring_leak")
    add(t["hp_pump_eff_dev_pts"] < -L["hp_eff_dev_alert_pts"], "RO_HP_PUMP", "Medium",
        f"HP pump {t['hp_pump_eff_pct']:.1f} % wire-to-water vs. {t['hp_pump_eff_expected_pct']:.1f} % expected", "hp_pump", "hp_pump_wear")
    add(t["px_eff_pct"] < L["px_eff_alert_pct"] or t["px_mixing_pct"] > L["px_mixing_alert_pct"] or t["px_leakage_pct"] > L["px_leakage_alert_pct"],
        "RO_ERD", "Medium", f"PX efficiency {t['px_eff_pct']:.1f} %, leakage {t['px_leakage_pct']:.1f} %, mixing {t['px_mixing_pct']:.1f} %", "erd", "erd_leakage")
    add(r["cf_dp_bar"] > L["cf_dp_alert_bar"], "RO_CARTRIDGE_DP", "Medium", f"Cartridge filter dP {r['cf_dp_bar']:.2f} bar: change the cartridges", "cartridge",
        "cartridge_clogging")
    add(r["hp_suction_pressure_bar"] < L["suction_low_bar"], "RO_LOW_SUCTION", "High", f"HP pump suction {r['hp_suction_pressure_bar']:.2f} bar(g)", "hp_pump",
        "cartridge_clogging")
    add(r["membrane_feed_pressure_bar"] > L["feed_pressure_alert_bar"], "RO_PRESSURE_HIGH", "High",
        f"Membrane feed pressure {r['membrane_feed_pressure_bar']:.1f} bar (element limit 83 bar)", "membranes")
    add(r["permeate_tds_mgl"] > L["permeate_tds_alert_mgl"], "RO_PERMEATE_QUALITY", "Medium", f"Permeate {r['permeate_tds_mgl']:.0f} mg/L TDS", "permeate")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
