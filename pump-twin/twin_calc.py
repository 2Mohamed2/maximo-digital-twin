"""The twin's physics expectations, generated from the design block of the twin file (KSB curves).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Monitor PythonExpression functions (run in the Monitor pipeline)
  evaluate(twin, reading)   -> the same numbers in Python (twin viewer, tests)
Curves are polynomials in Q at the curve speed n0. At speed n (s = n/n0) the affinity laws give
  Q0 = Q/s,  H = s^2 * H0(Q0),  P = s^3 * P0(Q0),  eta = rho*g*Q0*H0(Q0) / P0(Q0),  NPSHr = s^2 * N0(max(Q0, Qmin))
Each expression uses raw metrics only, so Monitor can evaluate them in any order.
"""
RHO_G = 998.2 * 9.81


def _k(twin):
    d = twin["design"]
    c = d["curves"]
    return dict(n0=float(d["rated_speed_rpm"]), qb=float(d["bep_flow_m3h"]), H=c["head_m"], P=c["shaft_power_kw"],
                N=c["npshr_m"], qmin=float(c["npshr_q_min_m3h"]))


def _poly_expr(coef, x):
    """Horner form, explicit coefficients: c0 + x*(c1 + x*(c2 + x*c3))."""
    e = f"({coef[-1]!r})"
    for c in reversed(coef[:-1]):
        e = f"({c!r} + {x} * {e})"
    return e


def poly(coef, x):
    r = 0.0
    for c in reversed(coef):
        r = r * x + c
    return r


def _parts(twin):
    k = _k(twin)
    S = f"(df['SPEED_RPM'].clip(lower=1) / {k['n0']})"
    Q0 = f"(df['FLOW_M3H'] / {S})"
    H0 = _poly_expr(k["H"], Q0)
    P0 = _poly_expr(k["P"], Q0)
    N0 = _poly_expr(k["N"], f"{Q0}.clip(lower={k['qmin']})")
    HEXP = f"({S}**2 * {H0})"
    EEXP = f"(100 * {RHO_G} * {Q0} / 3600 * {H0} / (1000 * {P0}))"
    NPSHR = f"({S}**2 * {N0})"
    X = f"({Q0} / {k['qb']})"
    return S, X, HEXP, EEXP, NPSHR


def monitor_expressions(twin):
    S, X, HEXP, EEXP, NPSHR = _parts(twin)
    return [
        ("SPEED_RATIO", f"{S}"),
        ("BEP_RATIO", f"{X}"),
        ("HEAD_EXPECTED_M", HEXP),
        ("HEAD_DEVIATION_PCT", f"(df['HEAD_M'] - {HEXP}) / {HEXP}.clip(lower=1) * 100"),
        ("EFF_EXPECTED_PCT", EEXP),
        ("EFF_DEVIATION_PTS", f"df['PUMP_EFFICIENCY_PCT'] - {EEXP}"),
        ("NPSHR_M", NPSHR),
        ("NPSH_MARGIN_M", f"df['NPSHA_M'] - {NPSHR}"),
        ("SPECIFIC_ENERGY_KWH_M3", "df['MOTOR_POWER_KW'] / df['FLOW_M3H'].clip(lower=1)"),
        ("WIRE_TO_WATER_PCT", "df['HYDRAULIC_POWER_KW'] / df['MOTOR_POWER_KW'].clip(lower=0.1) * 100"),
    ]


def expected(twin, q, n):
    """Design values at flow q [m3/h] and speed n [rpm]: (head m, efficiency 0..1, shaft power kW, NPSHr m)."""
    k = _k(twin)
    s = max(n, 1) / k["n0"]
    q0 = q / s
    h0, p0 = poly(k["H"], q0), poly(k["P"], q0)
    eta = RHO_G * q0 / 3600 * h0 / (1000 * p0) if p0 > 0 else 0.0
    return s * s * h0, eta, s ** 3 * p0, s * s * poly(k["N"], max(q0, k["qmin"]))


def evaluate(twin, r):
    """Same formulas on one reading dict (metric names as in the twin file, lower case)."""
    k = _k(twin)
    s = max(r["speed_rpm"], 1) / k["n0"]
    q = r["flow_m3h"]
    hexp, eta, _, npshr = expected(twin, q, r["speed_rpm"])
    eexp = eta * 100
    return {
        "speed_ratio": s,
        "bep_ratio": q / s / k["qb"],
        "head_expected_m": hexp,
        "head_deviation_pct": (r["head_m"] - hexp) / max(hexp, 1) * 100,
        "eff_expected_pct": eexp,
        "eff_deviation_pts": r["pump_efficiency_pct"] - eexp,
        "npshr_m": npshr,
        "npsh_margin_m": r["npsha_m"] - npshr,
        "specific_energy_kwh_m3": r["motor_power_kw"] / max(q, 1),
        "wire_to_water_pct": r["hydraulic_power_kw"] / max(r["motor_power_kw"], 0.1) * 100,
    }


def alert_rules(twin):
    """(alert name, expression, severity, failure mode) generated from the twin limits."""
    L = twin["twin_model"]["limits"]
    S, X, HEXP, EEXP, NPSHR = _parts(twin)
    run = "(df['RUNNING'] > 0)"
    return [
        ("PUMP_BEARING_DEFECT_EARLY", f"{run} & (df['VIB_DE_ENVELOPE'] > {L['envelope_alert_ge']})", "Medium", "bearing_de"),
        ("PUMP_VIBRATION_HIGH", f"{run} & (df['VIB_DE_VEL_RMS'] > {L['vib_alert_mm_s']})", "High", None),
        ("PUMP_BEARING_TEMP_HIGH", f"df['BEARING_DE_TEMP_C'] > {L['bearing_alert_c']}", "High", "bearing_de"),
        ("PUMP_CAVITATION_RISK", f"{run} & ((df['NPSHA_M'] - {NPSHR}) < {L['npsh_margin_alert_m']})", "High", "cavitation"),
        ("PUMP_OFF_BEP", f"{run} & (({X} < {L['bep_ratio_low']}) | ({X} > {L['bep_ratio_high']}))", "Low", None),
        ("PUMP_HEAD_DEGRADED", f"{run} & (((df['HEAD_M'] - {HEXP}) / {HEXP}.clip(lower=1) * 100) < {L['head_deviation_alert_pct']})", "Medium", "impeller_wear"),
        ("PUMP_EFFICIENCY_LOSS", f"{run} & ((df['PUMP_EFFICIENCY_PCT'] - {EEXP}) < {L['eff_deviation_alert_pts']})", "Medium", "impeller_wear"),
        ("PUMP_SEAL_LEAK", f"df['SEAL_LEAK_MLMIN'] > {L['seal_leak_alert_mlmin']}", "Medium", "seal_leak"),
        ("PUMP_CURRENT_IMBALANCE", f"{run} & (df['CURRENT_IMBALANCE_PCT'] > {L['current_imbalance_alert_pct']})", "Medium", "motor_winding"),
        ("PUMP_WINDING_TEMP_HIGH", f"df['WINDING_TEMP_C'] > {L['winding_alert_c']}", "High", "motor_winding"),
        ("PUMP_TRIPPED", "df['TRIP_CODE'] > 0", "Critical", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    """Active conditions on one reading (r) and its twin values (t): the same rules as the Monitor alert rules.
    Returns (list of {name, severity, text, part, failure_mode}, health 0..100)."""
    L = twin["twin_model"]["limits"]
    run = r.get("running", 1) > 0
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    trips = {1: "Vibration trip", 2: "Bearing temperature trip", 3: "Winding temperature trip", 4: "Fluid temperature trip (dead-head)"}
    add(r.get("trip_code", 0) > 0, "PUMP_TRIPPED", "Critical", trips.get(r.get("trip_code"), "Tripped"), "pump")
    add(run and r["vib_de_envelope"] > L["envelope_alert_ge"], "PUMP_BEARING_DEFECT_EARLY", "Medium",
        f"Envelope {r['vib_de_envelope']:.2f} gE > {L['envelope_alert_ge']} gE", "bearing_de", "bearing_de")
    add(run and r["vib_de_vel_rms"] > L["vib_alert_mm_s"], "PUMP_VIBRATION_HIGH", "High",
        f"DE velocity {r['vib_de_vel_rms']:.2f} mm/s > {L['vib_alert_mm_s']} mm/s", "bearing_de")
    add(r["bearing_de_temp_c"] > L["bearing_alert_c"], "PUMP_BEARING_TEMP_HIGH", "High",
        f"DE bearing {r['bearing_de_temp_c']:.1f} °C", "bearing_de", "bearing_de")
    add(run and t["npsh_margin_m"] < L["npsh_margin_alert_m"], "PUMP_CAVITATION_RISK", "High",
        f"NPSH margin {t['npsh_margin_m']:.2f} m < {L['npsh_margin_alert_m']} m", "pump", "cavitation")
    add(run and (t["bep_ratio"] < L["bep_ratio_low"] or t["bep_ratio"] > L["bep_ratio_high"]), "PUMP_OFF_BEP", "Low",
        f"Operating at {t['bep_ratio'] * 100:.0f} % of best-efficiency flow", "pump")
    add(run and t["head_deviation_pct"] < L["head_deviation_alert_pct"], "PUMP_HEAD_DEGRADED", "Medium",
        f"Head {t['head_deviation_pct']:.1f} % below the KSB curve", "pump", "impeller_wear")
    add(run and t["eff_deviation_pts"] < L["eff_deviation_alert_pts"], "PUMP_EFFICIENCY_LOSS", "Medium",
        f"Efficiency {t['eff_deviation_pts']:.1f} pts below the KSB curve", "pump", "impeller_wear")
    add(r["seal_leak_mlmin"] > L["seal_leak_alert_mlmin"], "PUMP_SEAL_LEAK", "Medium",
        f"Seal leakage {r['seal_leak_mlmin']:.0f} ml/min", "seal", "seal_leak")
    add(run and r["current_imbalance_pct"] > L["current_imbalance_alert_pct"], "PUMP_CURRENT_IMBALANCE", "Medium",
        f"Phase current imbalance {r['current_imbalance_pct']:.1f} %", "motor", "motor_winding")
    add(r["winding_temp_c"] > L["winding_alert_c"], "PUMP_WINDING_TEMP_HIGH", "High",
        f"Winding {r['winding_temp_c']:.1f} °C", "motor", "motor_winding")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
