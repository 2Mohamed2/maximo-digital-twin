"""The anaerobic digester twin's expectations (AD-4901, mesophilic, sewage sludge).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Loading and retention (V = working volume, Q = raw sludge fed per day, no sludge recycle so SRT = HRT):
    HRT = V / Q                       SRT effective = V x active volume fraction (last tracer test) / Q
    VS load (kg/d) = Q x density x DS x VS          OLR = VS load / V   (kg VS per m3 per day)
Volatile solids reduction (Van Kleeck; fixed solids pass through unchanged), with VS as fractions of DS:
    VSR = (VSin - VSout) / (VSin - VSin x VSout)
Expected gas: biogas (Nm3/h) = VS load x VSR x yield (Nm3 per kg VS destroyed) / 24
    gas yield ratio = measured / expected;  specific gas production SGP = biogas x 24 / VS load (Nm3 per kg VS fed)
Energy: methane power (kW) = biogas x CH4 x 9.97 kWh/Nm3 (lower heating value of methane)
    CHP electrical efficiency = CHP power / (CHP gas x CH4 x 9.97);  CHP heat expected = CHP fuel x eta_th (data sheet)
Heat: delivered = hot water flow x 1.163 x (supply - return)        (kW; 1.163 kWh/m3K for water)
    demand expected = Q/24 x 1.163 x (T set - T feed) + UA wall x (T set - T outdoor)
    heat exchanger UA = delivered / LMTD, LMTD = (dT1 - dT2) / ln(dT1 / dT2), dT1 = supply - sludge out, dT2 = return - sludge in
Mixing: specific power (W/m3) = mixer power / V; stratification = max - min of the top, middle and bottom temperatures.
Stability: FOS/TAC (volatile organic acids / total inorganic carbonate alkalinity, Nordmann titration) is read directly.
"""


def _k(twin):
    d = twin["design"]
    tk, p, e, hx, mx, ch = d["tank"], d["process"], d["energy"], d["heat_exchanger"], d["mixing"], d["chp"]
    return dict(V=tk["volume_m3"], uaw=tk["ua_wall_kw_k"], tset=p["temp_set_c"], rho=p["sludge_density_kg_m3"],
                y=p["gas_yield_m3_kgvsd"], lhv=e["ch4_lhv_kwh_m3"], ua=hx["ua_design_kw_k"], cw=hx["water_heat_kwh_m3k"],
                pmix=mx["power_design_kw"], eel=ch["eta_el"], eth=ch["eta_th"])


def _parts(twin):
    k = _k(twin)
    V, rho = k["V"], k["rho"]
    VSL = f"(df['FEED_FLOW_M3D'] * {rho / 1e4:.6g} * df['FEED_DS_PCT'] * df['FEED_VS_PCT'])"
    VSR = ("((df['FEED_VS_PCT'] / 100 - df['DIGESTED_VS_PCT'] / 100)"
           " / (df['FEED_VS_PCT'] / 100 - df['FEED_VS_PCT'] * df['DIGESTED_VS_PCT'] / 10000))")
    GEX = f"({VSL} * {VSR} * {k['y']} / 24)"
    HD = f"(df['HW_FLOW_M3H'] * {k['cw']} * (df['HW_SUPPLY_C'] - df['HW_RETURN_C']))"
    HN = (f"(df['FEED_FLOW_M3D'] / 24 * {k['cw']} * ({k['tset']} - df['FEED_TEMP_C'])"
          f" + {k['uaw']} * ({k['tset']} - df['AMBIENT_TEMP_C']))")
    D1 = "(df['HW_SUPPLY_C'] - df['HX_SLUDGE_OUT_C'])"
    D2 = "(df['HW_RETURN_C'] - df['HX_SLUDGE_IN_C'])"
    LM = f"(({D1} - {D2}) / np.log({D1} / {D2}))"
    TM = "((df['TEMP_TOP_C'] + df['TEMP_MID_C'] + df['TEMP_BOTTOM_C']) / 3)"
    TS = ("(np.maximum(np.maximum(df['TEMP_TOP_C'], df['TEMP_MID_C']), df['TEMP_BOTTOM_C'])"
          " - np.minimum(np.minimum(df['TEMP_TOP_C'], df['TEMP_MID_C']), df['TEMP_BOTTOM_C']))")
    CF = f"(df['CHP_GAS_M3H'] * df['CH4_PCT'] / 100 * {k['lhv']})"
    SRT = f"({V} * df['ACTIVE_VOLUME_PCT'] / 100 / df['FEED_FLOW_M3D'])"
    return dict(k=k, VSL=VSL, VSR=VSR, GEX=GEX, HD=HD, HN=HN, LM=LM, TM=TM, TS=TS, CF=CF, SRT=SRT)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    V = k["V"]
    return [
        ("HRT_D", f"{V} / df['FEED_FLOW_M3D']"),
        ("SRT_EFFECTIVE_D", p["SRT"]),
        ("VS_LOAD_KGD", p["VSL"]),
        ("OLR_KGVS_M3D", f"{p['VSL']} / {V}"),
        ("VSR_PCT", f"100 * {p['VSR']}"),
        ("VS_DESTROYED_KGD", f"{p['VSL']} * {p['VSR']}"),
        ("BIOGAS_EXPECTED_M3H", p["GEX"]),
        ("GAS_YIELD_RATIO", f"df['BIOGAS_FLOW_M3H'] / {p['GEX']}"),
        ("SGP_M3_KGVS", f"df['BIOGAS_FLOW_M3H'] * 24 / {p['VSL']}"),
        ("METHANE_POWER_KW", f"df['BIOGAS_FLOW_M3H'] * df['CH4_PCT'] / 100 * {k['lhv']}"),
        ("TEMP_MEAN_C", p["TM"]),
        ("TEMP_SPREAD_K", p["TS"]),
        ("MIXING_W_M3", f"df['MIXER_POWER_KW'] * 1000 / {V}"),
        ("HEAT_DELIVERED_KW", p["HD"]),
        ("HEAT_DEMAND_KW", p["HN"]),
        ("HX_UA_RATIO", f"{p['HD']} / {p['LM']} / {k['ua']}"),
        ("CHP_EFF_EL", f"df['CHP_POWER_KW'] / {p['CF']}"),
        ("CHP_HEAT_EXPECTED_KW", f"{p['CF']} * {k['eth']}"),
        ("HEAT_COVER_RATIO", f"{p['CF']} * {k['eth']} / {p['HN']}"),
    ]


def evaluate(twin, r):
    import math
    k = _k(twin)
    V = k["V"]
    vsl = r["feed_flow_m3d"] * k["rho"] / 1e4 * r["feed_ds_pct"] * r["feed_vs_pct"]
    vi, vo = r["feed_vs_pct"] / 100, r["digested_vs_pct"] / 100
    vsr = (vi - vo) / (vi - r["feed_vs_pct"] * r["digested_vs_pct"] / 10000)
    gex = vsl * vsr * k["y"] / 24
    hd = r["hw_flow_m3h"] * k["cw"] * (r["hw_supply_c"] - r["hw_return_c"])
    hn = r["feed_flow_m3d"] / 24 * k["cw"] * (k["tset"] - r["feed_temp_c"]) + k["uaw"] * (k["tset"] - r["ambient_temp_c"])
    d1, d2 = r["hw_supply_c"] - r["hx_sludge_out_c"], r["hw_return_c"] - r["hx_sludge_in_c"]
    lm = (d1 - d2) / math.log(d1 / d2)
    ts = (r["temp_top_c"], r["temp_mid_c"], r["temp_bottom_c"])
    cf = r["chp_gas_m3h"] * r["ch4_pct"] / 100 * k["lhv"]
    return {
        "hrt_d": V / r["feed_flow_m3d"],
        "srt_effective_d": V * r["active_volume_pct"] / 100 / r["feed_flow_m3d"],
        "vs_load_kgd": vsl, "olr_kgvs_m3d": vsl / V, "vsr_pct": 100 * vsr, "vs_destroyed_kgd": vsl * vsr,
        "biogas_expected_m3h": gex, "gas_yield_ratio": r["biogas_flow_m3h"] / gex, "sgp_m3_kgvs": r["biogas_flow_m3h"] * 24 / vsl,
        "methane_power_kw": r["biogas_flow_m3h"] * r["ch4_pct"] / 100 * k["lhv"],
        "temp_mean_c": (ts[0] + ts[1] + ts[2]) / 3, "temp_spread_k": max(ts) - min(ts),
        "mixing_w_m3": r["mixer_power_kw"] * 1000 / V,
        "heat_delivered_kw": hd, "heat_demand_kw": hn, "hx_ua_ratio": hd / lm / k["ua"],
        "chp_eff_el": r["chp_power_kw"] / cf, "chp_heat_expected_kw": cf * k["eth"], "heat_cover_ratio": cf * k["eth"] / hn,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    return [
        ("DIG_FOSTAC_HIGH", f"df['FOS_TAC'] >= {L['fostac_high']}", "High", "souring"),
        ("DIG_PH_LOW", f"df['PH'] < {L['ph_low']}", "High", "souring"),
        ("DIG_TEMP_LOW", f"{p['TM']} < {k['tset'] - L['temp_low_k']}", "High", "hx_fouling"),
        ("DIG_SRT_LOW", f"{p['SRT']} < {L['srt_min_d']}", "High", "grit_accumulation"),
        ("DIG_FOAM_HIGH", f"df['FOAM_LAYER_M'] > {L['foam_max_m']}", "High", "foaming"),
        ("DIG_FOSTAC_RISING", f"(df['FOS_TAC'] >= {L['fostac_warn']}) & (df['FOS_TAC'] < {L['fostac_high']})", "Medium", "souring"),
        ("DIG_CH4_LOW", f"df['CH4_PCT'] < {L['ch4_low_pct']}", "Medium", "souring"),
        ("DIG_GAS_YIELD_LOW", f"df['BIOGAS_FLOW_M3H'] / {p['GEX']} < {L['gas_ratio_low']}", "Medium", "souring"),
        ("DIG_HX_FOULED", f"{p['HD']} / {p['LM']} / {k['ua']} < {L['ua_ratio_low']}", "Medium", "hx_fouling"),
        ("DIG_STRATIFIED", f"{p['TS']} > {L['spread_k']}", "Medium", "mixing_failure"),
        ("DIG_MIXING_LOW", f"df['MIXER_POWER_KW'] < {L['mixing_ratio_low'] * k['pmix']:.6g}", "Medium", "mixing_failure"),
        ("DIG_ACTIVE_VOLUME_LOW", f"df['ACTIVE_VOLUME_PCT'] < {L['active_volume_low_pct']}", "Medium", "grit_accumulation"),
        ("DIG_VSR_LOW", f"100 * {p['VSR']} < {L['vsr_min_pct']}", "Medium", None),
        ("DIG_H2S_HIGH", f"df['H2S_PPM'] > {L['h2s_max_ppm']}", "Medium", "h2s_high"),
        ("DIG_CHP_EFF_LOW", f"df['CHP_POWER_KW'] / {p['CF']} < {L['chp_eff_ratio_low'] * k['eel']:.6g}", "Medium", "chp_degradation"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    ft = r["fos_tac"]
    add(ft >= L["fostac_high"], "DIG_FOSTAC_HIGH", "High", f"FOS/TAC {ft:.2f}: acids are winning over the buffer, cut the feed", "biology", "souring")
    add(r["ph"] < L["ph_low"], "DIG_PH_LOW", "High", f"pH {r['ph']:.2f}, below {L['ph_low']}: methane formers inhibited", "biology", "souring")
    add(t["temp_mean_c"] < k["tset"] - L["temp_low_k"], "DIG_TEMP_LOW", "High",
        f"Digester at {t['temp_mean_c']:.1f} °C, {k['tset'] - t['temp_mean_c']:.1f} K below the {k['tset']:.0f} °C set point", "heating", "hx_fouling")
    add(t["srt_effective_d"] < L["srt_min_d"], "DIG_SRT_LOW", "High",
        f"Effective SRT {t['srt_effective_d']:.1f} d, below the {L['srt_min_d']:.0f} d of 40 CFR 503 Appendix B", "tank", "grit_accumulation")
    add(r["foam_layer_m"] > L["foam_max_m"], "DIG_FOAM_HIGH", "High", f"Foam layer {r['foam_layer_m']:.2f} m in the freeboard: gas line at risk", "tank", "foaming")
    add(L["fostac_warn"] <= ft < L["fostac_high"], "DIG_FOSTAC_RISING", "Medium", f"FOS/TAC {ft:.2f}, above {L['fostac_warn']}: watch the feed", "biology", "souring")
    add(r["ch4_pct"] < L["ch4_low_pct"], "DIG_CH4_LOW", "Medium", f"Methane {r['ch4_pct']:.1f} %, below {L['ch4_low_pct']:.0f} %", "gas", "souring")
    add(t["gas_yield_ratio"] < L["gas_ratio_low"], "DIG_GAS_YIELD_LOW", "Medium",
        f"Biogas {r['biogas_flow_m3h']:.0f} Nm³/h, {t['gas_yield_ratio'] * 100:.0f} % of the {t['biogas_expected_m3h']:.0f} expected from the VS destroyed", "biology", "souring")
    add(t["hx_ua_ratio"] < L["ua_ratio_low"], "DIG_HX_FOULED", "Medium", f"Heat exchanger UA {t['hx_ua_ratio'] * 100:.0f} % of clean", "heating", "hx_fouling")
    add(t["temp_spread_k"] > L["spread_k"], "DIG_STRATIFIED", "Medium", f"Top to bottom spread {t['temp_spread_k']:.1f} K: the tank is stratifying", "mixing", "mixing_failure")
    add(r["mixer_power_kw"] < L["mixing_ratio_low"] * k["pmix"], "DIG_MIXING_LOW", "Medium",
        f"Mixers absorb {r['mixer_power_kw']:.1f} kW of {k['pmix']:.0f} kW ({t['mixing_w_m3']:.1f} W/m³)", "mixing", "mixing_failure")
    add(r["active_volume_pct"] < L["active_volume_low_pct"], "DIG_ACTIVE_VOLUME_LOW", "Medium",
        f"Tracer test: only {r['active_volume_pct']:.0f} % of the volume is active (grit, scum, dead zones)", "tank", "grit_accumulation")
    add(t["vsr_pct"] < L["vsr_min_pct"], "DIG_VSR_LOW", "Medium", f"VS reduction {t['vsr_pct']:.1f} %, below the {L['vsr_min_pct']:.0f} % of 40 CFR 503.33(b)(1)", "biology")
    add(r["h2s_ppm"] > L["h2s_max_ppm"], "DIG_H2S_HIGH", "Medium", f"H2S {r['h2s_ppm']:.0f} ppm, above the CHP limit {L['h2s_max_ppm']:.0f} ppm", "gas", "h2s_high")
    add(t["chp_eff_el"] < L["chp_eff_ratio_low"] * k["eel"], "DIG_CHP_EFF_LOW", "Medium",
        f"CHP electrical efficiency {t['chp_eff_el'] * 100:.1f} %, data sheet {k['eel'] * 100:.1f} %", "chp", "chp_degradation")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
