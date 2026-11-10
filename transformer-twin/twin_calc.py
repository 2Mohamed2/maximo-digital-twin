"""The oil transformer twin's expectations (SGB-SMIT DOTML 1000 kVA, IEC 60076-7, IEEE C57.104 / Duval).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (twin viewer, tests)

Thermal model (IEC 60076-7:2018, distribution ONAN defaults):
  top-oil rise (steady)   dTheta_o = dTheta_or * ((1 + R K^2) / (1 + R))^x        R = Pk/P0
  hot-spot gradient       dTheta_h = H g_r K^y
  ageing rate (paper)     V = 2^((theta_h - 98)/6)   (non-upgraded; upgraded: exp(15000/383 - 15000/(theta_h + 273)))

Why the steady-state formula, and why the IED's equivalent load:
  Monitor evaluates each 5-minute batch of single readings; a PythonExpression cannot integrate the IEC difference
  equations over hours. The oil follows its steady-state target through a first-order lag (k11 tau_o = 180 min), so
  comparing the top oil with the steady value at the *present* load would raise false alarms after every load change.
  The transformer's monitoring IED already keeps a thermal image: it filters the ultimate top-oil rise f(K) and the
  ambient through the same 180-min lag and reports them as the equivalent load K_eq (f(K_eq) = filtered f(K)) and the
  mean ambient. The steady-state formula at (K_eq, mean ambient) then *is* the IEC dynamic top-oil temperature, and the
  residual (measured - expected) stays near zero through load swings; a blocked cooler shows up as a lasting positive
  residual. The hot-spot gradient (tau_w 4 min) is fast enough for the present load.

DGA:
  TDCG = H2 + CH4 + C2H2 + C2H4 + C2H6 + CO; IEEE C57.104-1991 condition 1-4 = the worst gas (and TDCG) against the table.
  Duval Triangle 1 on %CH4 / %C2H4 / %C2H2, applied only when a gas is above its normal level (gate in the twin file).
  Zone codes: 0 normal, 1 PD, 2 T1, 3 T2, 4 T3, 5 D1, 6 D2, 7 DT.
"""
import math

GASES = ["h2", "ch4", "c2h2", "c2h4", "c2h6", "co"]


def _k(twin):
    d = twin["design"]
    th = d["thermal"]
    return dict(S=d["rating"]["s_kva"], P0=d["losses"]["p0_w"], PK=d["losses"]["pk_w"], R=th["R"], x=th["x"], y=th["y"],
                H=th["H"], gr=th["g_r_k"], dor=th["dtheta_or_k"], p20=d["hermetic"]["pressure_at_20c_bar"],
                kp=d["hermetic"]["pressure_per_k_bar"], lim=d["dga"]["ieee_1991_limits_ppm"], gate=d["dga"]["duval_gate"])


def top_oil_steady(k, theta_a, kpu):
    return theta_a + k["dor"] * ((1 + k["R"] * kpu ** 2) / (1 + k["R"])) ** k["x"]


def duval_zone(ch4, c2h4, c2h2):
    """Duval Triangle 1 (percentages of CH4 + C2H4 + C2H2). Returns 1..7."""
    if ch4 >= 98:
        return 1
    if c2h4 < 20 and c2h2 < 4:
        return 2
    if c2h4 < 50 and c2h2 < 4:
        return 3
    if c2h4 >= 50 and c2h2 < 15:
        return 4
    if c2h4 < 23 and c2h2 >= 13:
        return 5
    if (c2h4 >= 23 and c2h2 >= 29) or (23 <= c2h4 < 40 and 13 <= c2h2 < 29):
        return 6
    return 7


def _parts(twin):
    k = _k(twin)
    S, R, x, y = k["S"], k["R"], k["x"], k["y"]
    K = f"(df['LOAD_KVA'].clip(lower=0) / {S})"
    TOE = f"(df['AMBIENT_AVG_C'] + {k['dor']} * ((1 + {R} * df['LOAD_EQ_PU'].clip(lower=0) ** 2) / {1 + R}) ** {x})"
    HSE = f"(df['TOP_OIL_TEMP_C'] + {k['H'] * k['gr']} * {K} ** {y})"
    G = {g: f"df['DGA_{g.upper()}_PPM']" for g in GASES}
    S3 = f"({G['ch4']} + {G['c2h4']} + {G['c2h2']}).clip(lower=0.01)"
    PCH4, PC2H4, PC2H2 = (f"({G[g]} / {S3} * 100)" for g in ("ch4", "c2h4", "c2h2"))
    gt = k["gate"]
    GATE = f"(({G['h2']} > {gt['h2']}) | ({G['ch4']} > {gt['ch4']}) | ({G['c2h4']} > {gt['c2h4']}) | ({G['c2h2']} > {gt['c2h2']}))"
    ZONE = (f"np.where(~{GATE}, 0, np.where({PCH4} >= 98, 1, np.where(({PC2H4} < 20) & ({PC2H2} < 4), 2, "
            f"np.where(({PC2H4} < 50) & ({PC2H2} < 4), 3, np.where(({PC2H4} >= 50) & ({PC2H2} < 15), 4, "
            f"np.where(({PC2H4} < 23) & ({PC2H2} >= 13), 5, np.where((({PC2H4} >= 23) & ({PC2H2} >= 29)) | "
            f"(({PC2H4} >= 23) & ({PC2H4} < 40) & ({PC2H2} >= 13) & ({PC2H2} < 29)), 6, 7)))))))")
    TDCG = "(" + " + ".join(G[g] for g in GASES) + ")"
    L = k["lim"]

    def cond(expr, lims):
        return f"(1 + ({expr} > {lims[0]}).astype(int) + ({expr} > {lims[1]}).astype(int) + ({expr} > {lims[2]}).astype(int))"
    parts = [cond(G[g], L[g]) for g in GASES] + [cond(TDCG, L["tdcg"])]
    IEEE = parts[0]
    for p in parts[1:]:
        IEEE = f"np.maximum({IEEE}, {p})"
    PE = f"({k['p20']} + {k['kp']} * (df['TOP_OIL_TEMP_C'] - 20))"
    return dict(K=K, TOE=TOE, HSE=HSE, PCH4=PCH4, PC2H4=PC2H4, PC2H2=PC2H2, ZONE=ZONE, TDCG=TDCG, IEEE=IEEE, PE=PE, k=k)


def monitor_expressions(twin):
    p, k = _parts(twin), _k(twin)
    return [
        ("LOAD_PU", p["K"]),
        ("TOP_OIL_EXPECTED_C", p["TOE"]),
        ("TOP_OIL_RESIDUAL_K", f"df['TOP_OIL_TEMP_C'] - {p['TOE']}"),
        ("HOT_SPOT_EXPECTED_C", p["HSE"]),
        ("HOT_SPOT_RESIDUAL_K", f"df['WTI_TEMP_C'] - {p['HSE']}"),
        ("AGEING_RATE_V", "np.power(2.0, (df['WTI_TEMP_C'] - 98) / 6)"),
        ("AGEING_RATE_V_UPGRADED", "np.exp(15000 / 383 - 15000 / (df['WTI_TEMP_C'] + 273))"),
        ("LOSS_OF_LIFE_H_PER_DAY", "24 * np.power(2.0, (df['WTI_TEMP_C'] - 98) / 6)"),
        ("LOSSES_KW", f"({k['P0']} + {k['PK']} * {p['K']} ** 2) / 1000"),
        ("PRESSURE_EXPECTED_BAR", p["PE"]),
        ("PRESSURE_RESIDUAL_BAR", f"df['TANK_PRESSURE_BAR'] - {p['PE']}"),
        ("TDCG_PPM", p["TDCG"]),
        ("DUVAL_CH4_PCT", p["PCH4"]),
        ("DUVAL_C2H4_PCT", p["PC2H4"]),
        ("DUVAL_C2H2_PCT", p["PC2H2"]),
        ("DUVAL_ZONE", p["ZONE"]),
        ("IEEE_CONDITION", p["IEEE"]),
        ("CO2_CO_RATIO", "df['DGA_CO2_PPM'] / df['DGA_CO_PPM'].clip(lower=1)"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    K = max(r["load_kva"], 0) / k["S"]
    toe = top_oil_steady(k, r["ambient_avg_c"], max(r["load_eq_pu"], 0))
    hse = r["top_oil_temp_c"] + k["H"] * k["gr"] * K ** k["y"]
    g = {x: r[f"dga_{x}_ppm"] for x in GASES}
    s3 = max(g["ch4"] + g["c2h4"] + g["c2h2"], 0.01)
    pch4, pc2h4, pc2h2 = g["ch4"] / s3 * 100, g["c2h4"] / s3 * 100, g["c2h2"] / s3 * 100
    gt = k["gate"]
    gate = g["h2"] > gt["h2"] or g["ch4"] > gt["ch4"] or g["c2h4"] > gt["c2h4"] or g["c2h2"] > gt["c2h2"]
    zone = duval_zone(pch4, pc2h4, pc2h2) if gate else 0
    tdcg = sum(g.values())
    L = k["lim"]
    cond = lambda v, l: 1 + (v > l[0]) + (v > l[1]) + (v > l[2])
    ieee = max([cond(g[x], L[x]) for x in GASES] + [cond(tdcg, L["tdcg"])])
    v = 2.0 ** ((r["wti_temp_c"] - 98) / 6)
    pe = k["p20"] + k["kp"] * (r["top_oil_temp_c"] - 20)
    return {
        "load_pu": K, "top_oil_expected_c": toe, "top_oil_residual_k": r["top_oil_temp_c"] - toe,
        "hot_spot_expected_c": hse, "hot_spot_residual_k": r["wti_temp_c"] - hse,
        "ageing_rate_v": v, "ageing_rate_v_upgraded": math.exp(15000 / 383 - 15000 / (r["wti_temp_c"] + 273)),
        "loss_of_life_h_per_day": 24 * v, "losses_kw": (k["P0"] + k["PK"] * K ** 2) / 1000,
        "pressure_expected_bar": pe, "pressure_residual_bar": r["tank_pressure_bar"] - pe,
        "tdcg_ppm": tdcg, "duval_ch4_pct": pch4, "duval_c2h4_pct": pc2h4, "duval_c2h2_pct": pc2h2,
        "duval_zone": zone, "ieee_condition": ieee, "co2_co_ratio": r["dga_co2_ppm"] / max(r["dga_co_ppm"], 1),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    Z = p["ZONE"]
    return [
        ("TR_COOLING_DEGRADED", f"((df['TOP_OIL_TEMP_C'] - {p['TOE']}) > {L['top_oil_residual_alert_k']}) & (df['LOAD_EQ_PU'] > {L['steady_load_min_pu']})", "Medium", "cooling_degraded"),
        ("TR_TOP_OIL_HIGH", f"df['TOP_OIL_TEMP_C'] > {L['top_oil_alert_c']}", "High", None),
        ("TR_HOT_SPOT_HIGH", f"df['WTI_TEMP_C'] > {L['hot_spot_alert_c']}", "High", "overload_ageing"),
        ("TR_OVERLOAD", f"df['LOAD_EQ_PU'] > {L['overload_alert_pu']}", "Medium", "overload_ageing"),
        ("TR_AGEING_FAST", f"np.power(2.0, (df['WTI_TEMP_C'] - 98) / 6) > {L['ageing_alert']}", "Low", "overload_ageing"),
        ("TR_PAPER_OVERHEATING", f"df['DGA_CO_PPM'] > {L['co_paper_alert_ppm']}", "Medium", "overload_ageing"),
        ("TR_DGA_THERMAL", f"({Z} == 2) | ({Z} == 3)", "Medium", "thermal_fault_core"),
        ("TR_DGA_T3", f"{Z} == 4", "High", "thermal_fault_core"),
        ("TR_DGA_PD", f"{Z} == 1", "Medium", "partial_discharge"),
        ("TR_DGA_ARCING", f"({Z} == 5) | ({Z} == 6)", "High", "arcing"),
        ("TR_DGA_DT", f"{Z} == 7", "Medium", "arcing"),
        ("TR_DGA_CONDITION", f"{p['IEEE']} >= {L['ieee_condition_alert']}", "High", None),
        ("TR_MOISTURE", f"df['MOISTURE_PPM'] > {L['moisture_alert_ppm']}", "Medium", "moisture_ingress"),
        ("TR_OIL_LOSS", f"(df['OIL_LEVEL_PCT'] < {L['oil_level_alert_pct']}) | ((df['TANK_PRESSURE_BAR'] - {p['PE']}) < {L['pressure_residual_alert_bar']})", "Medium", "oil_leak"),
        ("TR_RELAY_ALARM", "df['RELAY_STATUS'] == 1", "High", None),
        ("TR_RELAY_TRIP", "df['RELAY_STATUS'] >= 2", "Critical", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}
ZONE_NAMES = {0: "normal", 1: "PD", 2: "T1", 3: "T2", 4: "T3", 5: "D1", 6: "D2", 7: "DT"}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    z, zn = t["duval_zone"], ZONE_NAMES[t["duval_zone"]]
    duv = f"Duval {zn}: CH4 {t['duval_ch4_pct']:.0f} %, C2H4 {t['duval_c2h4_pct']:.0f} %, C2H2 {t['duval_c2h2_pct']:.0f} %"
    add(r["relay_status"] >= 2, "TR_RELAY_TRIP", "Critical", "Protection relay tripped the transformer (gas / pressure / temperature)", "relay")
    add(r["relay_status"] == 1, "TR_RELAY_ALARM", "High", "Protection relay alarm (gas / temperature stage 1)", "relay")
    add(t["top_oil_residual_k"] > L["top_oil_residual_alert_k"] and r["load_eq_pu"] > L["steady_load_min_pu"], "TR_COOLING_DEGRADED", "Medium",
        f"Top oil {t['top_oil_residual_k']:.1f} K above IEC 60076-7 at {r['load_eq_pu']:.2f} pu equivalent load", "tank", "cooling_degraded")
    add(r["top_oil_temp_c"] > L["top_oil_alert_c"], "TR_TOP_OIL_HIGH", "High", f"Top oil {r['top_oil_temp_c']:.0f} °C (limit {L['top_oil_alert_c']})", "tank")
    add(r["wti_temp_c"] > L["hot_spot_alert_c"], "TR_HOT_SPOT_HIGH", "High", f"Hot spot {r['wti_temp_c']:.0f} °C (limit {L['hot_spot_alert_c']})", "windings", "overload_ageing")
    add(r["load_eq_pu"] > L["overload_alert_pu"], "TR_OVERLOAD", "Medium", f"Sustained load {r['load_eq_pu']:.2f} pu (equivalent over 3 h)", "windings", "overload_ageing")
    add(t["ageing_rate_v"] > L["ageing_alert"], "TR_AGEING_FAST", "Low", f"Paper ageing x{t['ageing_rate_v']:.1f} ({t['loss_of_life_h_per_day']:.0f} h of life per day)", "windings", "overload_ageing")
    add(r["dga_co_ppm"] > L["co_paper_alert_ppm"], "TR_PAPER_OVERHEATING", "Medium", f"CO {r['dga_co_ppm']:.0f} ppm, CO2/CO {t['co2_co_ratio']:.1f}: paper is overheating", "windings", "overload_ageing")
    add(z in (2, 3), "TR_DGA_THERMAL", "Medium", duv, "core", "thermal_fault_core")
    add(z == 4, "TR_DGA_T3", "High", duv + " (> 700 °C)", "core", "thermal_fault_core")
    add(z == 1, "TR_DGA_PD", "Medium", duv + f", H2 {r['dga_h2_ppm']:.0f} ppm", "windings", "partial_discharge")
    add(z in (5, 6), "TR_DGA_ARCING", "High", duv + f", C2H2 {r['dga_c2h2_ppm']:.0f} ppm", "windings", "arcing")
    add(z == 7, "TR_DGA_DT", "Medium", duv, "windings", "arcing")
    add(t["ieee_condition"] >= L["ieee_condition_alert"], "TR_DGA_CONDITION", "High", f"IEEE C57.104 condition {t['ieee_condition']} (TDCG {t['tdcg_ppm']:.0f} ppm)", "dga")
    add(r["moisture_ppm"] > L["moisture_alert_ppm"], "TR_MOISTURE", "Medium", f"Water in oil {r['moisture_ppm']:.0f} ppm, O2 {r['dga_o2_ppm']:.0f} ppm", "tank", "moisture_ingress")
    add(r["oil_level_pct"] < L["oil_level_alert_pct"] or t["pressure_residual_bar"] < L["pressure_residual_alert_bar"], "TR_OIL_LOSS", "Medium",
        f"Oil level {r['oil_level_pct']:.0f} %, tank pressure {t['pressure_residual_bar']:+.3f} bar vs. expected", "tank", "oil_leak")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
