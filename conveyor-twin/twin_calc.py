"""The overland belt conveyor twin's expectations (CV-3801).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Expected drive power (ISO 5048, the long-conveyor form with coefficient C):
    q_G   = Q / (3.6 v)                                   load per metre (kg/m) from the belt weigher and the belt speed
    F_H   = C f L g [q_RO + q_RU + 2 q_B + q_G]          main + secondary resistances, C = (L + L0) / L
    F_St  = q_G H g                                       lifting the ore
    F_U   = F_H + F_St                                    peripheral force at the drive pulley
    P_M   = F_U v / eta                                   expected motor power, compared with motor 1 + motor 2
  The same equation solved for f with the measured power gives the apparent friction factor: the conveyor's overall
  running resistance in one number (0.02 for a healthy, well-aligned conveyor).
Drive pulley (Euler-Eytelwein, ISO 5048 eq. 10):
    T2_min = F_U / (e^(mu phi) - 1)                      slack-side tension needed so the pulley does not slip
    T2     = take-up force / 2                            gravity take-up on the slack side just after the drive
    slip margin = T2 / T2_min
    slip   = (v_pulley - v_belt) / v_pulley               expected: elastic creep only, F_U / K (K = belt stiffness)
Take-up and belt length:
    elastic take-up travel = F_U L / (4 K)               carry side stretched by about F_U / 2 on average, carriage moves half
    permanent elongation   = (x - x0 - elastic) / L      x = carriage position, x0 = position with the new belt at standstill
Belt safety factor = rated strength x width / (T2 + F_U).
Load sharing: |P1 - P2| / (P1 + P2). Idlers: hottest idler minus ambient.
"""
import math


def _k(twin):
    d = twin["design"]
    r, b, i, rs, dr, tu = d["route"], d["belt"], d["idlers"], d["resistance"], d["drive"], d["takeup"]
    L = r["length_m"]
    return dict(L=L, H=r["lift_m"], qB=b["q_b_kg_m"], qRO=i["q_ro_kg_m"], qRU=i["q_ru_kg_m"], f=rs["f"], g=rs["g"],
                C=(L + rs["L0_m"]) / L, eta=dr["eta"], mu=dr["mu"], phi=math.radians(dr["wrap_deg"]), K=b["stiffness_n"],
                kn=b["strength_n_per_mm"] * b["width_m"] * 1000 / 1000, prated=dr["motor_rated_kw"], v0=dr["speed_ms"],
                mcw=tu["counterweight_t"], travel=tu["travel_m"], x0=tu["x0_m"], rho=d["material"]["bulk_density_t_m3"])


def euler(k):
    """e^(mu phi): the largest T1/T2 the drive pulley can hold without slipping."""
    return math.exp(k["mu"] * k["phi"])


def takeup_force_expected_kn(k):
    return k["mcw"] * k["g"]


def _parts(twin):
    k = _k(twin)
    V = "np.maximum(df['BELT_SPEED_MS'], 0.1)"
    QG = f"(df['TONNAGE_TPH'] / (3.6 * {V}))"
    CFLG = k["C"] * k["f"] * k["L"] * k["g"]
    CLG = k["C"] * k["L"] * k["g"]
    QS = f"({k['qRO'] + k['qRU'] + 2 * k['qB']} + {QG})"
    FH = f"({CFLG} * {QS})"
    FST = f"({QG} * {k['H'] * k['g']})"
    FUE = f"(({FH} + {FST}) / 1000)"
    PE = f"({FUE} * {V} / {k['eta']})"
    PM = "(df['MOTOR1_POWER_KW'] + df['MOTOR2_POWER_KW'])"
    FUM = f"({PM} * {k['eta']} / {V})"
    SLIP = "((df['DRIVE_PULLEY_SPEED_MS'] - df['BELT_SPEED_MS']) / np.maximum(df['DRIVE_PULLEY_SPEED_MS'], 0.1) * 100)"
    CREEP = f"({FUM} * {1000 / k['K'] * 100})"
    T2 = "(df['TAKEUP_FORCE_KN'] / 2)"
    T2MIN = f"({FUM} / {euler(k) - 1})"
    EL = f"({FUM} * {1000 * k['L'] / (4 * k['K'])})"
    ELONG = f"((df['TAKEUP_POSITION_M'] - {k['x0']} - {EL}) / {k['L'] / 100})"
    return dict(k=k, V=V, QG=QG, QS=QS, FH=FH, FST=FST, FUE=FUE, PE=PE, PM=PM, FUM=FUM, SLIP=SLIP, CREEP=CREEP, T2=T2,
                T2MIN=T2MIN, EL=EL, ELONG=ELONG, CLG=CLG)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("LOAD_KG_M", p["QG"]),
        ("RESIST_MAIN_KN", f"{p['FH']} / 1000"),
        ("RESIST_SLOPE_KN", f"{p['FST']} / 1000"),
        ("FU_EXPECTED_KN", p["FUE"]),
        ("POWER_EXPECTED_KW", p["PE"]),
        ("POWER_MEASURED_KW", p["PM"]),
        ("POWER_RESIDUAL_KW", f"{p['PM']} - {p['PE']}"),
        ("POWER_RATIO", f"{p['PM']} / {p['PE']}"),
        ("FU_MEASURED_KN", p["FUM"]),
        ("FRICTION_APPARENT", f"({p['FUM']} * 1000 - {p['FST']}) / ({p['CLG']} * {p['QS']})"),
        ("LOAD_IMBALANCE_PCT", f"np.abs(df['MOTOR1_POWER_KW'] - df['MOTOR2_POWER_KW']) / np.maximum({p['PM']}, 1) * 100"),
        ("SLIP_PCT", p["SLIP"]),
        ("CREEP_EXPECTED_PCT", p["CREEP"]),
        ("SLIP_EXCESS_PCT", f"{p['SLIP']} - {p['CREEP']}"),
        ("T2_MIN_KN", p["T2MIN"]),
        ("SLIP_MARGIN", f"{p['T2']} / np.maximum({p['T2MIN']}, 1)"),
        ("TAKEUP_ELASTIC_M", p["EL"]),
        ("BELT_ELONGATION_PCT", p["ELONG"]),
        ("BELT_SAFETY_FACTOR", f"{k['kn']} / ({p['T2']} + {p['FUM']})"),
        ("IDLER_DT_K", "df['IDLER_MAX_TEMP_C'] - df['AMBIENT_TEMP_C']"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    v = max(r["belt_speed_ms"], 0.1)
    qg = r["tonnage_tph"] / (3.6 * v)
    qs = k["qRO"] + k["qRU"] + 2 * k["qB"] + qg
    fh = k["C"] * k["f"] * k["L"] * k["g"] * qs
    fst = qg * k["H"] * k["g"]
    fue = (fh + fst) / 1000
    pe = fue * v / k["eta"]
    pm = r["motor1_power_kw"] + r["motor2_power_kw"]
    fum = pm * k["eta"] / v
    slip = (r["drive_pulley_speed_ms"] - r["belt_speed_ms"]) / max(r["drive_pulley_speed_ms"], 0.1) * 100
    creep = fum * 1000 / k["K"] * 100
    t2 = r["takeup_force_kn"] / 2
    t2min = fum / (euler(k) - 1)
    el = fum * 1000 * k["L"] / (4 * k["K"])
    return {
        "load_kg_m": qg, "resist_main_kn": fh / 1000, "resist_slope_kn": fst / 1000, "fu_expected_kn": fue,
        "power_expected_kw": pe, "power_measured_kw": pm, "power_residual_kw": pm - pe, "power_ratio": pm / pe,
        "fu_measured_kn": fum, "friction_apparent": (fum * 1000 - fst) / (k["C"] * k["L"] * k["g"] * qs),
        "load_imbalance_pct": abs(r["motor1_power_kw"] - r["motor2_power_kw"]) / max(pm, 1) * 100,
        "slip_pct": slip, "creep_expected_pct": creep, "slip_excess_pct": slip - creep, "t2_min_kn": t2min,
        "slip_margin": t2 / max(t2min, 1), "takeup_elastic_m": el,
        "belt_elongation_pct": (r["takeup_position_m"] - k["x0"] - el) / (k["L"] / 100),
        "belt_safety_factor": k["kn"] / (t2 + fum), "idler_dt_k": r["idler_max_temp_c"] - r["ambient_temp_c"],
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    DT = "(df['IDLER_MAX_TEMP_C'] - df['AMBIENT_TEMP_C'])"
    SG = "df['SPLICE_MAX_GROWTH_MM']"
    TR = "np.maximum(np.abs(df['TRACKING_HEAD_MM']), np.abs(df['TRACKING_TAIL_MM']))"
    return [
        ("CV_SPLICE_CRITICAL", f"{SG} > {L['splice_growth_limit_mm']}", "Critical", "splice_failure"),
        ("CV_MOTOR_OVERLOAD", f"np.maximum(df['MOTOR1_POWER_KW'], df['MOTOR2_POWER_KW']) > {k['prated']}", "High", "load_share_imbalance"),
        ("CV_SLIP", f"({p['SLIP']} - {p['CREEP']}) > {L['slip_excess_pct']}", "High", "lagging_wear"),
        ("CV_SLIP_MARGIN_LOW", f"({p['T2']} / np.maximum({p['T2MIN']}, 1)) < {L['slip_margin_alert']}", "High", "takeup_jammed"),
        ("CV_IDLER_CRITICAL", f"{DT} > {L['idler_dt_critical_k']}", "High", "idler_bearing_failure"),
        ("CV_MISTRACKING_SEVERE", f"{TR} > {L['tracking_limit_mm']}", "High", "mistracking"),
        ("CV_POWER_HIGH", f"({p['PM']} / {p['PE']}) > {L['power_ratio_alert']}", "Medium", "high_resistance"),
        ("CV_LOAD_SHARE", f"(np.abs(df['MOTOR1_POWER_KW'] - df['MOTOR2_POWER_KW']) / np.maximum({p['PM']}, 1) * 100) > {L['load_imbalance_pct']}", "Medium", "load_share_imbalance"),
        ("CV_TAKEUP_TENSION_LOW", f"df['TAKEUP_FORCE_KN'] < {L['takeup_tension_ratio'] * takeup_force_expected_kn(k)}", "Medium", "takeup_jammed"),
        ("CV_TAKEUP_TRAVEL_END", f"df['TAKEUP_POSITION_M'] > {L['takeup_travel_ratio'] * k['travel']}", "Medium", "belt_stretch"),
        ("CV_BELT_STRETCH", f"{p['ELONG']} > {L['elongation_alert_pct']}", "Medium", "belt_stretch"),
        ("CV_IDLER_HOT", f"({DT} > {L['idler_dt_alert_k']}) & ({DT} <= {L['idler_dt_critical_k']})", "Medium", "idler_bearing_failure"),
        ("CV_SPLICE_GROWTH", f"({SG} > {L['splice_growth_alert_mm']}) & ({SG} <= {L['splice_growth_limit_mm']})", "Medium", "splice_failure"),
        ("CV_MISTRACKING", f"({TR} > {L['tracking_alert_mm']}) & ({TR} <= {L['tracking_limit_mm']})", "Medium", "mistracking"),
        ("CV_COVER_WORN", f"df['TOP_COVER_MIN_MM'] < {L['cover_min_mm']}", "Medium", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    dt, sg = t["idler_dt_k"], r["splice_max_growth_mm"]
    tr = max(abs(r["tracking_head_mm"]), abs(r["tracking_tail_mm"]))
    pmax = max(r["motor1_power_kw"], r["motor2_power_kw"])
    tfe = takeup_force_expected_kn(k)
    add(sg > L["splice_growth_limit_mm"], "CV_SPLICE_CRITICAL", "Critical",
        f"Splice {r['splice_worst_id']:.0f} is {sg:.1f} mm longer than at installation: stop and inspect before it pulls apart", "belt", "splice_failure")
    add(pmax > k["prated"], "CV_MOTOR_OVERLOAD", "High", f"A motor draws {pmax:.0f} kW, above its {k['prated']:.0f} kW rating", "drive", "load_share_imbalance")
    add(t["slip_excess_pct"] > L["slip_excess_pct"], "CV_SLIP", "High",
        f"Belt slips {t['slip_excess_pct']:.2f} % on the drive pulley beyond elastic creep", "drive", "lagging_wear")
    add(t["slip_margin"] < L["slip_margin_alert"], "CV_SLIP_MARGIN_LOW", "High",
        f"Slack-side tension {r['takeup_force_kn'] / 2:.0f} kN is {t['slip_margin']:.2f} x the {t['t2_min_kn']:.0f} kN the drive needs", "takeup", "takeup_jammed")
    add(dt > L["idler_dt_critical_k"], "CV_IDLER_CRITICAL", "High", f"An idler is {dt:.0f} K above ambient: seized bearing, fire risk", "idlers", "idler_bearing_failure")
    add(tr > L["tracking_limit_mm"], "CV_MISTRACKING_SEVERE", "High", f"Belt {tr:.0f} mm off centre: edge damage and spillage", "belt", "mistracking")
    add(t["power_ratio"] > L["power_ratio_alert"], "CV_POWER_HIGH", "Medium",
        f"Drive power {t['power_measured_kw']:.0f} kW is {t['power_ratio']:.2f} x the ISO 5048 expectation (apparent f {t['friction_apparent']:.4f})", "route", "high_resistance")
    add(t["load_imbalance_pct"] > L["load_imbalance_pct"], "CV_LOAD_SHARE", "Medium",
        f"Motors share the load {r['motor1_power_kw']:.0f} / {r['motor2_power_kw']:.0f} kW ({t['load_imbalance_pct']:.0f} % imbalance)", "drive", "load_share_imbalance")
    add(r["takeup_force_kn"] < L["takeup_tension_ratio"] * tfe, "CV_TAKEUP_TENSION_LOW", "Medium",
        f"Take-up force {r['takeup_force_kn']:.0f} kN, expected {tfe:.0f} kN from the counterweight", "takeup", "takeup_jammed")
    add(r["takeup_position_m"] > L["takeup_travel_ratio"] * k["travel"], "CV_TAKEUP_TRAVEL_END", "Medium",
        f"Take-up carriage at {r['takeup_position_m']:.2f} m of {k['travel']:.1f} m travel", "takeup", "belt_stretch")
    add(t["belt_elongation_pct"] > L["elongation_alert_pct"], "CV_BELT_STRETCH", "Medium",
        f"Belt permanently {t['belt_elongation_pct']:.3f} % longer than when new", "belt", "belt_stretch")
    add(L["idler_dt_alert_k"] < dt <= L["idler_dt_critical_k"], "CV_IDLER_HOT", "Medium", f"An idler is {dt:.0f} K above ambient", "idlers", "idler_bearing_failure")
    add(L["splice_growth_alert_mm"] < sg <= L["splice_growth_limit_mm"], "CV_SPLICE_GROWTH", "Medium",
        f"Splice {r['splice_worst_id']:.0f} has grown {sg:.1f} mm", "belt", "splice_failure")
    add(L["tracking_alert_mm"] < tr <= L["tracking_limit_mm"], "CV_MISTRACKING", "Medium", f"Belt {tr:.0f} mm off centre", "belt", "mistracking")
    add(r["top_cover_min_mm"] < L["cover_min_mm"], "CV_COVER_WORN", "Medium", f"Top cover down to {r['top_cover_min_mm']:.1f} mm", "belt")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
