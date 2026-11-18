"""The emergency shutdown valve twin's expectations (ESDV-2101, final element of a SIL 2 SIF).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Valve signature (from each partial stroke test, PST):
  The digital valve controller vents the actuator until the valve starts to close (pressure Pc), then fills it again until the
  valve is back fully open (pressure Po). In actuator pressure units:
      spring (measured)   = (Po + Pc) / 2        expected: spring_open_bar (bench set)
      friction (measured) = (Po - Pc) / 2        expected: f0 + k x line pressure (trunnion seats are pressure-energised)
  closing torque margin = spring x end_ratio / (friction x seat_ratio): the torque the spring still has at the end of the
  closing stroke, divided by the torque the valve needs to seat. Company specifications ask for 1.5 to 2.
Stroke: closing time of the last full stroke against the factory baseline and against the SRS requirement.
PFDavg as operated (IEC 61508-6, imperfect partial and proof testing):
      PFD_FE = PSTC x lDU x Tpst/2 + (PTC - PSTC) x lDU x TI/2 + (1 - PTC) x lDU x LT/2 + bypass hours / 8760
  with Tpst = the PST interval actually achieved over the last 12 months (sent by the PST scheduler), and the SIF total
  PFD = PFD_FE + sensors + logic solver. The SIL band follows IEC 61511 (SIL 2: 1e-3 <= PFDavg < 1e-2).
"""


def _k(twin):
    d = twin["design"]
    s, r, g, st = d["sif"], d["reliability"], d["signature"], d["stroke"]
    return dict(ps=s["pfd_sensors"], pl=s["pfd_logic"], req=s["required_closure_s"], sil=s["sil_target"],
                lam=r["lambda_du_per_h"], pstc=r["pst_coverage"], ptc=r["proof_coverage"], tpst=r["pst_interval_h"],
                ti=r["proof_interval_h"], lt=r["mission_time_h"], spring=g["spring_open_bar"], f0=g["friction0_bar"],
                kf=g["friction_per_bar"], er=g["spring_end_ratio"], sr=g["seat_ratio"], base=st["close_baseline_s"])


def pfd_fe(k, tpst, bypass_h=0.0):
    """PFDavg of the final element for a PST interval tpst (h) and bypass hours per year."""
    lam = k["lam"]
    return (k["pstc"] * lam * tpst / 2 + (k["ptc"] - k["pstc"]) * lam * k["ti"] / 2
            + (1 - k["ptc"]) * lam * k["lt"] / 2 + bypass_h / 8760)


def _parts(twin):
    k = _k(twin)
    FE = f"({k['f0']} + {k['kf']} * df['PST_LINE_PRESSURE_BAR'])"
    FM = "((df['PST_P_OPEN_END_BAR'] - df['PST_P_CLOSE_START_BAR']) / 2)"
    SM = "((df['PST_P_OPEN_END_BAR'] + df['PST_P_CLOSE_START_BAR']) / 2)"
    TM = f"({SM} * {k['er']} / ({FM} * {k['sr']}))"
    lam, pstc, ptc = k["lam"], k["pstc"], k["ptc"]
    PFE = (f"({pstc * lam / 2:.6g} * df['PST_INTERVAL_ACHIEVED_H'] + {(ptc - pstc) * lam * k['ti'] / 2:.6g}"
           f" + {(1 - ptc) * lam * k['lt'] / 2:.6g} + df['BYPASS_HOURS_365D'] / 8760)")
    PSIF = f"({PFE} + {k['ps'] + k['pl']:.6g})"
    PNOW = (f"np.minimum({pstc * lam:.6g} * df['PST_HOURS_SINCE'] + {(ptc - pstc) * lam:.6g} * df['PROOF_HOURS_SINCE']"
            f" + {(1 - ptc) * lam:.6g} * df['OVERHAUL_HOURS_SINCE'] + df['BYPASS_ACTIVE'], 1)")
    return dict(k=k, FE=FE, FM=FM, SM=SM, TM=TM, PFE=PFE, PSIF=PSIF, PNOW=PNOW)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("FRICTION_EXPECTED_BAR", p["FE"]),
        ("FRICTION_MEASURED_BAR", p["FM"]),
        ("FRICTION_RATIO", f"{p['FM']} / {p['FE']}"),
        ("SPRING_MEASURED_BAR", p["SM"]),
        ("SPRING_DEV_BAR", f"{p['SM']} - {k['spring']}"),
        ("CLOSE_START_EXPECTED_BAR", f"{k['spring']} - {p['FE']}"),
        ("OPEN_END_EXPECTED_BAR", f"{k['spring']} + {p['FE']}"),
        ("TORQUE_MARGIN", p["TM"]),
        ("AIR_MARGIN_BAR", "df['SUPPLY_PRESSURE_BAR'] - df['PST_P_OPEN_END_BAR']"),
        ("STROKE_RATIO", f"df['LAST_CLOSE_TIME_S'] / {k['base']}"),
        ("STROKE_MARGIN_S", f"{k['req']} - df['LAST_CLOSE_TIME_S']"),
        ("PFD_FE_OPS", p["PFE"]),
        ("PFD_SIF_OPS", p["PSIF"]),
        ("RRF_SIF_OPS", f"1 / {p['PSIF']}"),
        ("SIL_ACHIEVED", f"np.where({p['PSIF']} < 0.001, 3, np.where({p['PSIF']} < 0.01, 2, np.where({p['PSIF']} < 0.1, 1, 0)))"),
        ("PFD_NOW", p["PNOW"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    fe = k["f0"] + k["kf"] * r["pst_line_pressure_bar"]
    fm = (r["pst_p_open_end_bar"] - r["pst_p_close_start_bar"]) / 2
    sm = (r["pst_p_open_end_bar"] + r["pst_p_close_start_bar"]) / 2
    pfe = pfd_fe(k, r["pst_interval_achieved_h"], r["bypass_hours_365d"])
    psif = pfe + k["ps"] + k["pl"]
    lam = k["lam"]
    pnow = min(k["pstc"] * lam * r["pst_hours_since"] + (k["ptc"] - k["pstc"]) * lam * r["proof_hours_since"]
               + (1 - k["ptc"]) * lam * r["overhaul_hours_since"] + r["bypass_active"], 1)
    return {
        "friction_expected_bar": fe, "friction_measured_bar": fm, "friction_ratio": fm / fe,
        "spring_measured_bar": sm, "spring_dev_bar": sm - k["spring"],
        "close_start_expected_bar": k["spring"] - fe, "open_end_expected_bar": k["spring"] + fe,
        "torque_margin": sm * k["er"] / (fm * k["sr"]),
        "air_margin_bar": r["supply_pressure_bar"] - r["pst_p_open_end_bar"],
        "stroke_ratio": r["last_close_time_s"] / k["base"], "stroke_margin_s": k["req"] - r["last_close_time_s"],
        "pfd_fe_ops": pfe, "pfd_sif_ops": psif, "rrf_sif_ops": 1 / psif,
        "sil_achieved": 3 if psif < 0.001 else 2 if psif < 0.01 else 1 if psif < 0.1 else 0,
        "pfd_now": pnow,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    TM, FR = p["TM"], f"({p['FM']} / {p['FE']})"
    ST = f"(df['LAST_CLOSE_TIME_S'] / {k['base']})"
    m = L["travel_mismatch_pct"]
    return [
        ("ESD_STROKE_TOO_SLOW", f"df['LAST_CLOSE_TIME_S'] > {k['req']}", "Critical", "sov_exhaust_restriction"),
        ("ESD_PST_FAILED", "df['PST_RESULT'] < 0.5", "High", "stem_seat_sticking"),
        ("ESD_TORQUE_MARGIN_LIMIT", f"{TM} < {L['torque_margin_limit']}", "High", "stem_seat_sticking"),
        ("ESD_SIL_DRIFT", f"{p['PSIF']} >= {10 ** -k['sil']:.6g}", "High", "pst_not_run"),
        ("ESD_PROOF_OVERDUE", f"df['PROOF_HOURS_SINCE'] > {k['ti']}", "High", None),
        ("ESD_BYPASS_LONG", f"(df['BYPASS_ACTIVE'] > 0.5) & (df['BYPASS_ACTIVE_H'] > {L['bypass_alert_h']})", "High", "bypass_left_on"),
        ("ESD_TORQUE_MARGIN_LOW", f"({TM} < {L['torque_margin_alert']}) & ({TM} >= {L['torque_margin_limit']})", "Medium", "stem_seat_sticking"),
        ("ESD_FRICTION_HIGH", f"{FR} > {L['friction_ratio_alert']}", "Medium", "stem_seat_sticking"),
        ("ESD_SPRING_WEAK", f"({p['SM']} - {k['spring']}) < {L['spring_dev_alert_bar']}", "Medium", "spring_relaxation"),
        ("ESD_STROKE_SLOW", f"({ST} > {L['stroke_ratio_alert']}) & (df['LAST_CLOSE_TIME_S'] <= {k['req']})", "Medium", "sov_exhaust_restriction"),
        ("ESD_AIR_MARGIN", f"(df['SUPPLY_PRESSURE_BAR'] - df['PST_P_OPEN_END_BAR']) < {L['air_margin_alert_bar']}", "Medium", "air_supply_low"),
        ("ESD_POSITION_MISMATCH", f"((df['LIMIT_OPEN'] > 0.5) & (df['TRAVEL_PCT'] < {100 - m})) | ((df['LIMIT_CLOSED'] > 0.5) & (df['TRAVEL_PCT'] > {m}))"
                                  " | ((df['LIMIT_OPEN'] > 0.5) & (df['LIMIT_CLOSED'] > 0.5))", "Medium", "position_feedback"),
        ("ESD_PST_OVERDUE", f"df['PST_HOURS_SINCE'] > {L['pst_overdue_factor'] * k['tpst']}", "Medium", "pst_not_run"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    m = L["travel_mismatch_pct"]
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    tm, fr = t["torque_margin"], t["friction_ratio"]
    add(r["last_close_time_s"] > k["req"], "ESD_STROKE_TOO_SLOW", "Critical",
        f"Closed in {r['last_close_time_s']:.1f} s, slower than the {k['req']:.0f} s the SRS requires", "solenoid", "sov_exhaust_restriction")
    add(r["pst_result"] < 0.5, "ESD_PST_FAILED", "High", f"Last PST failed (lowest travel {r['pst_travel_reached_pct']:.0f} %): dangerous failure detected",
        "valve", "stem_seat_sticking")
    add(tm < L["torque_margin_limit"], "ESD_TORQUE_MARGIN_LIMIT", "High", f"Closing torque margin {tm:.2f}, below {L['torque_margin_limit']}", "valve", "stem_seat_sticking")
    add(t["pfd_sif_ops"] >= 10 ** -k["sil"], "ESD_SIL_DRIFT", "High",
        f"PFDavg as operated {t['pfd_sif_ops']:.2e}: SIF no longer meets SIL {k['sil']}", "testing", "pst_not_run")
    add(r["proof_hours_since"] > k["ti"], "ESD_PROOF_OVERDUE", "High", f"Proof test {r['proof_hours_since'] - k['ti']:.0f} h overdue", "testing")
    add(r["bypass_active"] > 0.5 and r["bypass_active_h"] > L["bypass_alert_h"], "ESD_BYPASS_LONG", "High",
        f"SIF bypassed for {r['bypass_active_h']:.0f} h", "sis", "bypass_left_on")
    add(L["torque_margin_limit"] <= tm < L["torque_margin_alert"], "ESD_TORQUE_MARGIN_LOW", "Medium", f"Closing torque margin {tm:.2f}", "valve", "stem_seat_sticking")
    add(fr > L["friction_ratio_alert"], "ESD_FRICTION_HIGH", "Medium", f"Friction {t['friction_measured_bar']:.2f} bar, {fr:.2f} x expected", "valve", "stem_seat_sticking")
    add(t["spring_dev_bar"] < L["spring_dev_alert_bar"], "ESD_SPRING_WEAK", "Medium", f"Spring {t['spring_measured_bar']:.2f} bar, {t['spring_dev_bar']:+.2f} bar vs bench set",
        "actuator", "spring_relaxation")
    add(t["stroke_ratio"] > L["stroke_ratio_alert"] and r["last_close_time_s"] <= k["req"], "ESD_STROKE_SLOW", "Medium",
        f"Closed in {r['last_close_time_s']:.1f} s, {t['stroke_ratio']:.2f} x the baseline", "solenoid", "sov_exhaust_restriction")
    add(t["air_margin_bar"] < L["air_margin_alert_bar"], "ESD_AIR_MARGIN", "Medium", f"Supply only {t['air_margin_bar']:.2f} bar above the pressure that holds the valve open",
        "air", "air_supply_low")
    add((r["limit_open"] > 0.5 and r["travel_pct"] < 100 - m) or (r["limit_closed"] > 0.5 and r["travel_pct"] > m)
        or (r["limit_open"] > 0.5 and r["limit_closed"] > 0.5), "ESD_POSITION_MISMATCH", "Medium",
        f"Limit switches ZSO {r['limit_open']:.0f} / ZSC {r['limit_closed']:.0f} disagree with travel {r['travel_pct']:.0f} %", "feedback", "position_feedback")
    add(r["pst_hours_since"] > L["pst_overdue_factor"] * k["tpst"], "ESD_PST_OVERDUE", "Medium", f"Last successful PST {r['pst_hours_since']:.0f} h ago", "testing", "pst_not_run")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
