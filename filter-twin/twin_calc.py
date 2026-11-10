"""The gravity filter twin's expectations (FLT-1401: anthracite over sand on a Leopold Universal Type S underdrain).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (twin viewer, tests)

Hydraulics (laminar flow through the media; all expected values at the live rate and water temperature):
  viscosity ratio      mu/mu20 = 10^(247.8/(T+133.15) - 247.8/153.15)            (Vogel equation)
  clean bed (media)    h_c = (h_anth0 + h_sand0) x (v/v0) x mu/mu20               (Carman-Kozeny at the design rate v0)
  underdrain           h_u = h_ud0 x (v/v0)^2                                      (orifice / cap losses, turbulent)
  stored solids        M = UFRV x TSS, UFRV = run volume / area (m3/m2), TSS = 1.5 x the PLC run-average settled NTU
  deposit              h_d = k x M x (v/v0) x mu/mu20
  expected media loss  h_c + h_d; residual = measured - expected; deposit ratio = (measured - h_c) / h_d
Why the PLC run average: Monitor evaluates single 5-minute readings and cannot integrate turbidity over a 30-hour run;
  the filter PLC already keeps the run totaliser and the run-average settled turbidity, so UFRV x average NTU is the
  stored solids without any history in Monitor.
Backwash expansion (anthracite, Richardson-Zaki):
  settling w = R g d^2 / (18 nu + sqrt(0.75 R g d^3)) (Ferguson & Church), Re = w d / nu, n = 4.45 Re^-0.1
  e = (v_b / w)^(1/n), expansion = (1 - e0)/(1 - e) - 1   (checked only while washing water flows, v_b > 10 m/h)
"""
import math

G = 9.81


def _k(twin):
    d = twin["design"]
    h, a = d["hydraulics"], d["media"]["anthracite"]
    return dict(A=d["cell"]["area_m2"], v0=d["operation"]["rate_design_m_h"], ha=h["clean_anthracite_m"], hs=h["clean_sand_m"],
                hu=h["clean_underdrain_m"], rho=h["rho"], K=d["deposit"]["k_m_per_kg_m2"], tss=d["deposit"]["tss_per_ntu"],
                R=a["sg"] - 1, d=a["d_eq_mm"] / 1000.0, e0=a["porosity"])


def mu(t):
    return 2.414e-5 * 10 ** (247.8 / (t + 133.15))


def mu_rel(t):
    return 10 ** (247.8 / (t + 133.15) - 247.8 / 153.15)


def expansion_expected(k, t, vb_mh):
    if vb_mh <= 0.1:
        return 0.0
    nu = mu(t) / k["rho"]
    w = k["R"] * G * k["d"] ** 2 / (18 * nu + math.sqrt(0.75 * k["R"] * G * k["d"] ** 3))
    n = 4.45 * (w * k["d"] / nu) ** -0.1
    e = min(0.95, max(k["e0"], (vb_mh / 3600.0 / w) ** (1 / n)))
    return ((1 - k["e0"]) / (1 - e) - 1) * 100


def _parts(twin):
    k = _k(twin)
    T = "df['WATER_TEMP_C']"
    MUR = f"np.power(10.0, 247.8 / ({T} + 133.15) - {247.8 / 153.15})"
    RATE = f"(df['FLOW_M3H'] / {k['A']})"
    VR = f"({RATE} / {k['v0']})"
    CLEAN = f"({k['ha'] + k['hs']} * {VR} * {MUR})"
    UDE = f"({k['hu']} * {VR} ** 2)"
    UFRV = f"(df['RUN_VOLUME_M3'] / {k['A']})"
    SOL = f"({UFRV} * df['SETTLED_TURBIDITY_AVG_NTU'] * {k['tss']} / 1000)"
    DEP = f"({k['K']} * {SOL} * {VR} * {MUR})"
    MEXP = f"({CLEAN} + {DEP})"
    RES = f"(df['HEADLOSS_MEDIA_M'] - {MEXP})"
    RATIO = f"((df['HEADLOSS_MEDIA_M'] - {CLEAN}) / {DEP}.clip(lower=0.05))"
    NU = f"(2.414e-5 * np.power(10.0, 247.8 / ({T} + 133.15)) / {k['rho']})"
    W = f"({k['R'] * G * k['d'] ** 2} / (18 * {NU} + {math.sqrt(0.75 * k['R'] * G * k['d'] ** 3)}))"
    N = f"(4.45 * np.power({W} * {k['d']} / {NU}, -0.1))"
    VB = f"(df['BACKWASH_FLOW_M3H'] / {k['A']})"
    E = f"np.clip(np.power(({VB} / 3600.0) / {W}, 1.0 / {N}), {k['e0']}, 0.95)"
    EXP = f"np.where({VB} > 0.1, ((1 - {k['e0']}) / (1 - {E}) - 1) * 100, 0.0)"
    XR = f"np.where((df['FILTER_STATE'] == 1) & ({VB} > 10), df['BED_EXPANSION_PCT'] / np.maximum({EXP}, 1.0), 1.0)"
    UDR = f"(df['UNDERDRAIN_DP_M'] / {UDE}.clip(lower=0.01))"
    FE = "((df['FLOW_M3H'] - df['FLOW_SETPOINT_M3H']) / df['FLOW_SETPOINT_M3H'].clip(lower=1) * 100)"
    return dict(MUR=MUR, RATE=RATE, CLEAN=CLEAN, UDE=UDE, UFRV=UFRV, SOL=SOL, DEP=DEP, MEXP=MEXP, RES=RES, RATIO=RATIO,
                EXP=EXP, XR=XR, UDR=UDR, FE=FE, k=k)


def monitor_expressions(twin):
    p = _parts(twin)
    return [
        ("RATE_M_H", p["RATE"]),
        ("VISCOSITY_RATIO", p["MUR"]),
        ("CLEAN_BED_EXPECTED_M", p["CLEAN"]),
        ("UNDERDRAIN_EXPECTED_M", p["UDE"]),
        ("UFRV_M3_M2", p["UFRV"]),
        ("SOLIDS_LOAD_KG_M2", p["SOL"]),
        ("DEPOSIT_EXPECTED_M", p["DEP"]),
        ("HEADLOSS_MEDIA_EXPECTED_M", p["MEXP"]),
        ("HEADLOSS_RESIDUAL_M", p["RES"]),
        ("DEPOSIT_RATIO", p["RATIO"]),
        ("UNDERDRAIN_RATIO", p["UDR"]),
        ("EXPANSION_EXPECTED_PCT", p["EXP"]),
        ("EXPANSION_RATIO", p["XR"]),
        ("FLOW_ERROR_PCT", p["FE"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    T = r["water_temp_c"]
    mur = mu_rel(T)
    rate = r["flow_m3h"] / k["A"]
    vr = rate / k["v0"]
    clean = (k["ha"] + k["hs"]) * vr * mur
    ude = k["hu"] * vr ** 2
    ufrv = r["run_volume_m3"] / k["A"]
    sol = ufrv * r["settled_turbidity_avg_ntu"] * k["tss"] / 1000
    dep = k["K"] * sol * vr * mur
    mexp = clean + dep
    exp = expansion_expected(k, T, r["backwash_flow_m3h"] / k["A"])
    return {
        "rate_m_h": rate, "viscosity_ratio": mur, "clean_bed_expected_m": clean, "underdrain_expected_m": ude,
        "ufrv_m3_m2": ufrv, "solids_load_kg_m2": sol, "deposit_expected_m": dep, "headloss_media_expected_m": mexp,
        "headloss_residual_m": r["headloss_media_m"] - mexp,
        "deposit_ratio": (r["headloss_media_m"] - clean) / max(dep, 0.05),
        "underdrain_ratio": r["underdrain_dp_m"] / max(ude, 0.01),
        "expansion_expected_pct": exp,
        "expansion_ratio": r["bed_expansion_pct"] / max(exp, 1.0) if r["filter_state"] == 1 and r["backwash_flow_m3h"] / k["A"] > 10 else 1.0,
        "flow_error_pct": (r["flow_m3h"] - r["flow_setpoint_m3h"]) / max(r["flow_setpoint_m3h"], 1) * 100,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    F0 = f"((df['FILTER_STATE'] == 0) & ({p['RATE']} > {L['rate_min_m_h']}))"
    RES, RATIO, TU, PC = p["RES"], p["RATIO"], "df['EFFLUENT_TURBIDITY_NTU']", "df['PARTICLE_COUNT_ML']"
    PH = "df['BED_PRESSURE_HEAD_M']"
    return [
        ("FLT_MUDBALLS", f"{F0} & ({RES} > {L['headloss_residual_high_m']}) & ({RATIO} < {L['deposit_ratio_alert']}) & ({PH} > {L['pressure_head_alert_m']})", "Medium", "mudballs"),
        ("FLT_MEDIA_LOSS", f"{F0} & (df['BED_DEPTH_M'] < {L['bed_depth_alert_m']})", "Medium", "media_loss"),
        ("FLT_AIR_BINDING", f"{F0} & ({PH} < {L['pressure_head_alert_m']})", "High", "air_binding"),
        ("FLT_SHORT_CIRCUIT", f"{F0} & ({RES} < {L['headloss_residual_low_m']}) & ({TU} > {L['turbidity_warn_ntu']}) & ({PC} > {L['particles_clean_ml']})", "High", "short_circuiting"),
        ("FLT_UNDERDRAIN", f"({F0} & ({p['UDR']} < {L['underdrain_ratio_alert']})) | ((df['FILTER_STATE'] == 1) & ({p['XR']} < {L['expansion_ratio_alert']}))", "High", "underdrain_failure"),
        ("FLT_RATE_CONTROL", f"{F0} & (np.abs({p['FE']}) > {L['flow_error_alert_pct']})", "Medium", "valve_sticking"),
        ("FLT_COAGULATION", f"{F0} & ({RATIO} >= {L['deposit_ratio_alert']}) & ({p['UFRV']} > {L['deposit_ufrv_min_m']}) & ({RES} > {L['headloss_residual_high_m']}) & ({PH} > {L['pressure_head_alert_m']})", "Medium", "coagulation_upset"),
        ("FLT_BREAKTHROUGH", f"{F0} & ({TU} > {L['turbidity_alert_ntu']}) & ({PC} > {L['particles_breakthrough_ml']})", "High", "coagulation_upset"),
        ("FLT_TURBIDIMETER", f"{F0} & ({TU} > {L['turbidity_warn_ntu']}) & ({PC} < {L['particles_clean_ml']})", "Medium", "turbidimeter_drift"),
        ("FLT_TERMINAL_HEADLOSS", f"{F0} & (df['HEADLOSS_TOTAL_M'] > {L['terminal_headloss_m']})", "Low", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}
STATES = {0: "filtering", 1: "backwash", 2: "filter-to-waste", 3: "standby"}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    f0 = r["filter_state"] == 0 and t["rate_m_h"] > L["rate_min_m_h"]
    res, ratio, tu, pc, ph = t["headloss_residual_m"], t["deposit_ratio"], r["effluent_turbidity_ntu"], r["particle_count_ml"], r["bed_pressure_head_m"]
    add(f0 and res > L["headloss_residual_high_m"] and ratio < L["deposit_ratio_alert"] and ph > L["pressure_head_alert_m"], "FLT_MUDBALLS", "Medium",
        f"Media head loss {res:+.2f} m above the model from the start of the run (clean bed fouled)", "media", "mudballs")
    add(f0 and r["bed_depth_m"] < L["bed_depth_alert_m"], "FLT_MEDIA_LOSS", "Medium",
        f"Media depth {r['bed_depth_m']:.2f} m (design 0.90 m): anthracite lost", "anthracite", "media_loss")
    add(f0 and ph < L["pressure_head_alert_m"], "FLT_AIR_BINDING", "High",
        f"Negative head {ph:.2f} m at the anthracite/sand interface: air binding", "anthracite", "air_binding")
    add(f0 and res < L["headloss_residual_low_m"] and tu > L["turbidity_warn_ntu"] and pc > L["particles_clean_ml"], "FLT_SHORT_CIRCUIT", "High",
        f"Head loss {res:+.2f} m below the model with {tu:.2f} NTU, {pc:.0f}/mL: water bypasses the media", "media", "short_circuiting")
    add((f0 and t["underdrain_ratio"] < L["underdrain_ratio_alert"]) or (r["filter_state"] == 1 and t["expansion_ratio"] < L["expansion_ratio_alert"]),
        "FLT_UNDERDRAIN", "High",
        f"Underdrain loss {t['underdrain_ratio'] * 100:.0f} % of expected; backwash expansion {t['expansion_ratio'] * 100:.0f} % of Richardson-Zaki", "underdrain", "underdrain_failure")
    add(f0 and abs(t["flow_error_pct"]) > L["flow_error_alert_pct"], "FLT_RATE_CONTROL", "Medium",
        f"Flow {t['flow_error_pct']:+.0f} % off setpoint, valve at {r['effluent_valve_pct']:.0f} %", "valve", "valve_sticking")
    add(f0 and ratio >= L["deposit_ratio_alert"] and t["ufrv_m3_m2"] > L["deposit_ufrv_min_m"] and res > L["headloss_residual_high_m"] and ph > L["pressure_head_alert_m"],
        "FLT_COAGULATION", "Medium", f"Head loss builds {ratio:.1f}x faster than the stored solids explain: weak floc", "media", "coagulation_upset")
    add(f0 and tu > L["turbidity_alert_ntu"] and pc > L["particles_breakthrough_ml"], "FLT_BREAKTHROUGH", "High",
        f"Breakthrough: {tu:.2f} NTU and {pc:.0f} particles/mL in the filtered water", "effluent", "coagulation_upset")
    add(f0 and tu > L["turbidity_warn_ntu"] and pc < L["particles_clean_ml"], "FLT_TURBIDIMETER", "Medium",
        f"Turbidimeter {tu:.2f} NTU but particle counter {pc:.0f}/mL (clean water): instrument drift", "effluent", "turbidimeter_drift")
    add(f0 and r["headloss_total_m"] > L["terminal_headloss_m"], "FLT_TERMINAL_HEADLOSS", "Low",
        f"Total head loss {r['headloss_total_m']:.2f} m: backwash due", "media")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
