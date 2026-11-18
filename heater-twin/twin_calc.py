"""The fired heater twin's expectations (H-2401, crude charge heater, 4 passes, natural draft).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Process side (what the crude takes up):
    absorbed duty Q_abs = m (t/h) / 3.6 x cp_eff x (COT - T_in) / 1000            [MW]
  cp_eff = design duty / (design charge x (COT - T_in)) holds the sensible heat and the vaporisation in the coil.
Fire side (what the fuel gives):
    fired duty Q_fired = fuel (kg/h) / 3600 x LHV (MJ/kg)                        [MW]
    thermal efficiency  = Q_abs / Q_fired
Flue-gas side (the same efficiency, measured another way):
    excess air EA % = 92 x O2 / (21 - O2)                     (O2 dry, refinery fuel gas)
    flue gas per kg fuel = 1 + A0 x (1 + EA/100)               (A0 = stoichiometric air, 17.2 kg/kg for methane)
    stack loss % = flue gas x cp_fg x (T_stack - T_air) / (LHV x 1000) x 100
    efficiency from the flue gas = 100 - stack loss - radiation loss
  The two efficiencies must agree. When they do not, a meter is wrong (fuel flow, charge flow or LHV analyser).
  Extra fuel cost against the design efficiency: Q_abs x (100/eff - 100/eff_design) x 8760 h x 3.6 GJ/MWh x price.
Tubes:
    peak flux q = q_avg x peak factor x Q_abs / Q_design
    clean TMT  = COT + q x (1/h_i + t/k_wall)                (hottest tube: the radiant outlet)
    coke layer = (TMT_max - clean TMT) / q x k_coke           (extra thermal resistance, as a thickness)
    pass pressure drop ratio = dP / (dP_design x (flow / flow_design)^1.8)
  Coking: TMT and pressure drop of the same pass both rise at the same duty and flow.
  Flame impingement: TMT of one pass rises, its pressure drop and flow stay normal, burner pressure rises.
Creep (API 530 idea, Larson-Miller):
    hoop stress = P x (Do - t) / (2 t);  LMP = a - b x log10(stress)
    rupture time t_r = 10^(1000 x LMP / T_K - C);  remaining life = (1 - life used) x t_r / 8760   [years at today's TMT, capped at 100]
"""
import math

C2K = 273.15
CAP_Y = 100.0     # creep life is shown up to 100 years ("more than 100 years" above)


def _k(twin):
    d = twin["design"]
    p, c, b, dr, t, cr, ec = d["process"], d["combustion"], d["burners"], d["draft"], d["tubes"], d["creep"], d["economics"]
    cp = p["duty_mw"] * 1000 / (p["charge_th"] / 3.6 * (p["cot_c"] - p["inlet_c"]))
    ea_d = c["ea_k"] * c["o2_design_pct"] / (21 - c["o2_design_pct"])
    loss_d = (1 + c["air_stoich_kg_kg"] * (1 + ea_d / 100)) * c["cp_fluegas_kj_kgk"] * (c["stack_design_c"] - c["ambient_design_c"]) / (c["lhv_mj_kg"] * 1000) * 100
    eff_d = 100 - loss_d - c["radiation_loss_pct"]
    fired_d = p["duty_mw"] / eff_d * 100
    fuel_d = fired_d / c["lhv_mj_kg"] * 3600
    q0 = t["flux_avg_kw_m2"] * t["peak_factor"]
    rc = 1 / t["h_inside_w_m2k"] + t["wall_nominal_mm"] / 1000 / t["k_wall_w_mk"]
    return dict(cp=cp, tin=p["inlet_c"], cot=p["cot_c"], duty=p["duty_mw"], fpass=p["charge_th"] / p["passes"], dp=p["pass_dp_bar"],
                nexp=p["dp_flow_exponent"], ek=c["ea_k"], a0=c["air_stoich_kg_kg"], cpg=c["cp_fluegas_kj_kgk"], rad=c["radiation_loss_pct"],
                st_d=c["stack_design_c"], st_k=c["stack_per_duty_c"], ea_d=ea_d, eff_d=eff_d, fired_d=fired_d, fuel_d=fuel_d,
                pb=b["fuel_pressure_design_barg"], q0=q0, rc=rc, kc=t["k_coke_w_mk"], tmt_d=t["tmt_design_c"], do=t["od_mm"],
                tw=t["wall_inspected_mm"], lc=cr["lmp_c"], la=cr["lmp_a"], lb=cr["lmp_b"], used=cr["life_used_at_inspection"],
                yrs=cr["years_alert"], price=ec["fuel_price_usd_gj"], co2=ec["co2_kg_gj"], hy=ec["hours_per_year"],
                h_fb=dr["firebox_height_m"], dpm=dr["draft_per_m_mmh2o"])


def excess_air(k, o2):
    return k["ek"] * o2 / (21 - o2)


def stack_loss(k, o2, t_stack, t_air, lhv):
    return (1 + k["a0"] * (1 + excess_air(k, o2) / 100)) * k["cpg"] * (t_stack - t_air) / (lhv * 1000) * 100


def creep_years(k, tmt_c, p_barg):
    s = p_barg / 10 * (k["do"] - k["tw"]) / (2 * k["tw"])
    lmp = k["la"] - k["lb"] * math.log10(s)
    return (1 - k["used"]) * 10 ** (1000 * lmp / (tmt_c + C2K) - k["lc"]) / 8760


def _parts(twin):
    k = _k(twin)
    P = ["A", "B", "C", "D"]
    TOT = "(" + " + ".join(f"df['FLOW_{p}_TH']" for p in P) + ")"
    QA = f"({TOT} / 3.6 * {k['cp']} * (df['COT_C'] - df['INLET_TEMP_C']) / 1000)"
    QF = "(df['FUEL_FLOW_KGH'] / 3600 * df['FUEL_LHV_MJKG'])"
    EA = f"({k['ek']} * df['O2_PCT'] / (21 - df['O2_PCT']))"
    SL = f"((1 + {k['a0']} * (1 + {EA} / 100)) * {k['cpg']} * (df['STACK_TEMP_C'] - df['AMBIENT_TEMP_C']) / (df['FUEL_LHV_MJKG'] * 1000) * 100)"
    EF = f"(100 - {SL} - {k['rad']})"
    TE = f"({QA} / {QF} * 100)"
    mx = lambda cols: f"np.maximum(np.maximum({cols[0]}, {cols[1]}), np.maximum({cols[2]}, {cols[3]}))"
    mn = lambda cols: f"np.minimum(np.minimum({cols[0]}, {cols[1]}), np.minimum({cols[2]}, {cols[3]}))"
    flows = [f"df['FLOW_{p}_TH']" for p in P]
    tmts = [f"df['TMT_{p}_C']" for p in P]
    IMB = f"(({mx(flows)} - {mn(flows)}) / ({TOT} / 4) * 100)"
    DPR = mx([f"(df['DP_{p}_BAR'] / ({k['dp']} * (df['FLOW_{p}_TH'] / {k['fpass']}) ** {k['nexp']}))" for p in P])
    TMX = f"({mx(tmts)})"
    SPR = f"({mx(tmts)} - {mn(tmts)})"
    FLX = f"({k['q0']} * {QA} / {k['duty']})"
    TCL = f"(df['COT_C'] + {FLX} * 1000 * {k['rc']})"
    COK = f"(({TMX} - {TCL}) / ({FLX} * 1000) * {k['kc']} * 1000)"
    BPR = f"((df['FUEL_PRESSURE_BARG'] + 1.01325) / ({k['pb'] + 1.01325} * df['FUEL_FLOW_KGH'] / {k['fuel_d']}))"
    SIG = f"(df['INLET_PRESSURE_BARG'] / 10 * {(k['do'] - k['tw']) / (2 * k['tw'])})"
    CRL = (f"np.minimum({1 - k['used']} * 10 ** (1000 * ({k['la']} - {k['lb']} * np.log10({SIG})) / ({TMX} + {C2K}) - {k['lc']}) / 8760, {CAP_Y})")
    SR = f"(df['STACK_TEMP_C'] - ({k['st_d']} + {k['st_k']} * ({QA} / {k['duty']} - 1)))"
    COST = f"({QA} * (100 / {EF} - {100 / k['eff_d']}) * {k['hy'] * 3.6 * k['price'] / 1000})"
    return dict(k=k, TOT=TOT, QA=QA, QF=QF, EA=EA, SL=SL, EF=EF, TE=TE, IMB=IMB, DPR=DPR, TMX=TMX, SPR=SPR, FLX=FLX, TCL=TCL,
                COK=COK, BPR=BPR, SIG=SIG, CRL=CRL, SR=SR, COST=COST)


def monitor_expressions(twin):
    p = _parts(twin)
    return [
        ("CHARGE_TH", p["TOT"]),
        ("ABSORBED_DUTY_MW", p["QA"]),
        ("FIRED_DUTY_MW", p["QF"]),
        ("THERMAL_EFF_PCT", p["TE"]),
        ("EXCESS_AIR_PCT", p["EA"]),
        ("STACK_LOSS_PCT", p["SL"]),
        ("EFF_FLUEGAS_PCT", p["EF"]),
        ("EFF_RESIDUAL_PCT", f"{p['TE']} - {p['EF']}"),
        ("STACK_RISE_C", p["SR"]),
        ("FUEL_COST_EXCESS_KUSD_Y", p["COST"]),
        ("FLOW_IMBALANCE_PCT", p["IMB"]),
        ("DP_RATIO_MAX", p["DPR"]),
        ("TMT_MAX_C", p["TMX"]),
        ("TMT_SPREAD_C", p["SPR"]),
        ("PEAK_FLUX_KWM2", p["FLX"]),
        ("TMT_CLEAN_C", p["TCL"]),
        ("COKE_MM", p["COK"]),
        ("BURNER_P_RATIO", p["BPR"]),
        ("HOOP_STRESS_MPA", p["SIG"]),
        ("CREEP_LIFE_Y", p["CRL"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    P = "abcd"
    flows = [r[f"flow_{p}_th"] for p in P]
    tmts = [r[f"tmt_{p}_c"] for p in P]
    tot = sum(flows)
    qa = tot / 3.6 * k["cp"] * (r["cot_c"] - r["inlet_temp_c"]) / 1000
    qf = r["fuel_flow_kgh"] / 3600 * r["fuel_lhv_mjkg"]
    ea = excess_air(k, r["o2_pct"])
    sl = stack_loss(k, r["o2_pct"], r["stack_temp_c"], r["ambient_temp_c"], r["fuel_lhv_mjkg"])
    ef = 100 - sl - k["rad"]
    te = qa / qf * 100
    flx = k["q0"] * qa / k["duty"]
    tcl = r["cot_c"] + flx * 1000 * k["rc"]
    tmx = max(tmts)
    sig = r["inlet_pressure_barg"] / 10 * (k["do"] - k["tw"]) / (2 * k["tw"])
    return {
        "charge_th": tot, "absorbed_duty_mw": qa, "fired_duty_mw": qf, "thermal_eff_pct": te, "excess_air_pct": ea,
        "stack_loss_pct": sl, "eff_fluegas_pct": ef, "eff_residual_pct": te - ef,
        "stack_rise_c": r["stack_temp_c"] - (k["st_d"] + k["st_k"] * (qa / k["duty"] - 1)),
        "fuel_cost_excess_kusd_y": qa * (100 / ef - 100 / k["eff_d"]) * k["hy"] * 3.6 * k["price"] / 1000,
        "flow_imbalance_pct": (max(flows) - min(flows)) / (tot / 4) * 100,
        "dp_ratio_max": max(r[f"dp_{p}_bar"] / (k["dp"] * (r[f"flow_{p}_th"] / k["fpass"]) ** k["nexp"]) for p in P),
        "tmt_max_c": tmx, "tmt_spread_c": tmx - min(tmts), "peak_flux_kwm2": flx, "tmt_clean_c": tcl,
        "coke_mm": (tmx - tcl) / (flx * 1000) * k["kc"] * 1000,
        "burner_p_ratio": (r["fuel_pressure_barg"] + 1.01325) / ((k["pb"] + 1.01325) * r["fuel_flow_kgh"] / k["fuel_d"]),
        "hoop_stress_mpa": sig,
        "creep_life_y": min((1 - k["used"]) * 10 ** (1000 * (k["la"] - k["lb"] * math.log10(sig)) / (tmx + C2K) - k["lc"]) / 8760, CAP_Y),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    return [
        ("HTR_TMT_LIMIT", f"{p['TMX']} > {k['tmt_d']}", "Critical", "coking"),
        ("HTR_COKE_BUILDUP", f"{p['COK']} > {L['coke_alert_mm']}", "High", "coking"),
        ("HTR_CREEP_LIFE_LOW", f"{p['CRL']} < {k['yrs']}", "High", "coking"),
        ("HTR_DRAFT_LOW", f"df['ARCH_DRAFT_MMH2O'] > {L['draft_alert_mmh2o']}", "High", "draft_loss"),
        ("HTR_O2_LOW", f"df['O2_PCT'] < {L['o2_low_pct']}", "High", "air_starvation"),
        ("HTR_TMT_ALERT", f"({p['TMX']} > {L['tmt_alert_c']}) & ({p['TMX']} <= {k['tmt_d']})", "Medium", "coking"),
        ("HTR_PASS_DP_HIGH", f"{p['DPR']} > {L['dp_ratio_alert']}", "Medium", "coking"),
        ("HTR_PASS_IMBALANCE", f"{p['IMB']} > {L['imbalance_alert_pct']}", "Medium", "pass_imbalance"),
        ("HTR_FLAME_IMPINGEMENT", f"({p['SPR']} > {L['tmt_spread_alert_c']}) & ({p['DPR']} <= {L['dp_ratio_alert']}) & ({p['IMB']} <= {L['imbalance_alert_pct']})",
         "Medium", "flame_impingement"),
        ("HTR_BURNER_DP_HIGH", f"{p['BPR']} > {L['burner_p_ratio_alert']}", "Medium", "flame_impingement"),
        ("HTR_CO_HIGH", f"df['CO_PPM'] > {L['co_alert_ppm']}", "Medium", "air_starvation"),
        ("HTR_EXCESS_AIR_HIGH", f"{p['EA']} > {L['excess_air_alert_pct']}", "Medium", "excess_air_high"),
        ("HTR_EFF_LOW", f"{p['EF']} < {k['eff_d'] - L['eff_drop_alert_pts']}", "Medium", "convection_fouling"),
        ("HTR_STACK_HIGH", f"{p['SR']} > {L['stack_rise_alert_c']}", "Medium", "convection_fouling"),
        ("HTR_EFF_MISMATCH", f"np.abs({p['TE']} - {p['EF']}) > {L['eff_mismatch_alert_pts']}", "Medium", "fuel_meter_drift"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    tmx, dpr, imb = t["tmt_max_c"], t["dp_ratio_max"], t["flow_imbalance_pct"]
    hot = "ABCD"[max(range(4), key=lambda i: r[f"tmt_{'abcd'[i]}_c"])]
    add(tmx > k["tmt_d"], "HTR_TMT_LIMIT", "Critical", f"Pass {hot} tube skin at {tmx:.0f} °C, above the design TMT of {k['tmt_d']:.0f} °C", "coil", "coking")
    add(t["coke_mm"] > L["coke_alert_mm"], "HTR_COKE_BUILDUP", "High",
        f"Skin {tmx - t['tmt_clean_c']:.0f} K hotter than a clean tube: about {t['coke_mm']:.1f} mm of coke", "coil", "coking")
    add(t["creep_life_y"] < k["yrs"], "HTR_CREEP_LIFE_LOW", "High",
        f"At {tmx:.0f} °C the tubes have {t['creep_life_y']:.1f} years of creep life left", "coil", "coking")
    add(r["arch_draft_mmh2o"] > L["draft_alert_mmh2o"], "HTR_DRAFT_LOW", "High",
        f"Arch pressure {r['arch_draft_mmh2o']:+.1f} mm H2O: not enough draft, flue gas may leak out", "draft", "draft_loss")
    add(r["o2_pct"] < L["o2_low_pct"], "HTR_O2_LOW", "High", f"O2 {r['o2_pct']:.1f} %: firing short of air", "air", "air_starvation")
    add(L["tmt_alert_c"] < tmx <= k["tmt_d"], "HTR_TMT_ALERT", "Medium", f"Pass {hot} tube skin at {tmx:.0f} °C, close to the design TMT", "coil", "coking")
    add(dpr > L["dp_ratio_alert"], "HTR_PASS_DP_HIGH", "Medium", f"Pass pressure drop {dpr:.2f} x expected at its flow", "coil", "coking")
    add(imb > L["imbalance_alert_pct"], "HTR_PASS_IMBALANCE", "Medium", f"Pass flows differ by {imb:.0f} % of the mean", "coil", "pass_imbalance")
    add(t["tmt_spread_c"] > L["tmt_spread_alert_c"] and dpr <= L["dp_ratio_alert"] and imb <= L["imbalance_alert_pct"], "HTR_FLAME_IMPINGEMENT", "Medium",
        f"Pass {hot} skin {t['tmt_spread_c']:.0f} K above the coolest pass with normal flow and pressure drop: flame on the tubes", "burners", "flame_impingement")
    add(t["burner_p_ratio"] > L["burner_p_ratio_alert"], "HTR_BURNER_DP_HIGH", "Medium",
        f"Burner gas pressure {t['burner_p_ratio']:.2f} x expected for the fuel flow: tips plugging", "burners", "flame_impingement")
    add(r["co_ppm"] > L["co_alert_ppm"], "HTR_CO_HIGH", "Medium", f"CO {r['co_ppm']:.0f} ppm: incomplete combustion", "air", "air_starvation")
    add(t["excess_air_pct"] > L["excess_air_alert_pct"], "HTR_EXCESS_AIR_HIGH", "Medium",
        f"Excess air {t['excess_air_pct']:.0f} % (O2 {r['o2_pct']:.1f} %)", "air", "excess_air_high")
    add(t["eff_fluegas_pct"] < k["eff_d"] - L["eff_drop_alert_pts"], "HTR_EFF_LOW", "Medium",
        f"Efficiency {t['eff_fluegas_pct']:.1f} % against {k['eff_d']:.1f} % design: {t['fuel_cost_excess_kusd_y']:.0f} k$ a year of extra fuel", "convection", "convection_fouling")
    add(t["stack_rise_c"] > L["stack_rise_alert_c"], "HTR_STACK_HIGH", "Medium", f"Stack {t['stack_rise_c']:.0f} K hotter than expected at this duty", "convection", "convection_fouling")
    add(abs(t["eff_residual_pct"]) > L["eff_mismatch_alert_pts"], "HTR_EFF_MISMATCH", "Medium",
        f"Efficiency from the meters {t['thermal_eff_pct']:.1f} % vs from the flue gas {t['eff_fluegas_pct']:.1f} %: check the fuel meter", "instrument", "fuel_meter_drift")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
