"""The fire pump twin's expectations (FP-6501, electric horizontal split-case fire pump with jockey pump and controller).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

The listed curve (net pressure against flow at the rated speed N0 = 1780 rpm) is a cubic fitted to the maker's curve:
      H(Q) = h0 + h1 q + h2 q^2 + h3 q^3,  q = Q / 1000 gpm
Affinity laws (speed correction, as NFPA 25 asks before a test is compared with the curve). A point measured at speed n:
      Q_corr = Q x N0 / n        P_corr = P x (N0 / n)^2
  so the pump at speed n should give  P_expected(Q, n) = (n / N0)^2 x H(Q x N0 / n).
NFPA 20 (listing envelope): churn <= 140 % of rated net pressure, net pressure at 150 % of rated flow >= 65 % of rated.
NFPA 25 (annual flow test): at the 100 % and 150 % points the speed-corrected net pressure must be at least 95 % of the
  reference curve at the corrected flow:  ratio = P_corr / H(Q_corr) >= 0.95.  The weekly churn test gives one more point
  between annual tests: churn ratio = P_churn x (N0 / n)^2 / H(0).
Motor current expected: I = BHP(Q_corr) x (n / N0)^3 x 745.7 / (sqrt(3) x V x efficiency x power factor).
Jockey pump: the make-up flow over a day is the system's leakage:  leak (gpm) = jockey flow x run minutes / 1440.
"""
import math


def _k(twin):
    d = twin["design"]
    p, s, m, sp, L = d["pump"], d["settings"], d["motor"], d["supply"], twin["twin_model"]["limits"]
    return dict(h=p["head_poly_kgpm"], b=p["bhp_poly_kgpm"], q0=p["rated_flow_gpm"], n0=p["rated_speed_rpm"], p0=p["rated_net_psi"],
                fla=m["fla_a"], v0=m["voltage_v"], eff=m["efficiency"], pf=m["power_factor"], jf=s["jockey_flow_gpm"],
                jstart=s["jockey_start_psi"], jstop=s["jockey_stop_psi"], fpstart=s["fire_pump_start_psi"], smin=L["suction_min_psi"])


def H(k, q_gpm):
    """Curve net pressure (psi) at the rated speed, flow in gpm."""
    q = q_gpm / 1000.0
    h = k["h"]
    return h[0] + h[1] * q + h[2] * q * q + h[3] * q * q * q


def BHP(k, q_gpm):
    q = q_gpm / 1000.0
    b = k["b"]
    return b[0] + b[1] * q + b[2] * q * q + b[3] * q * q * q


def _poly(c, x):
    return f"({c[0]} + {c[1]} * {x} + {c[2]} * {x} ** 2 + {c[3]} * {x} ** 3)"


def _parts(twin):
    k = _k(twin)
    n0 = k["n0"]
    S = "np.maximum(df['SPEED_RPM'], 300)"
    RUN = "((df['PUMP_RUNNING'] > 0.5) & (df['SPEED_RPM'] > 300))"
    QL = f"(df['FLOW_GPM'] * {n0} / {S} / 1000)"
    PEXP = f"(({S} / {n0}) ** 2 * {_poly(k['h'], QL)})"
    IEXP = f"({_poly(k['b'], QL)} * ({S} / {n0}) ** 3 * {745.7 / (math.sqrt(3) * k['eff'] * k['pf']):.9g} / df['SUPPLY_VOLTAGE_V'])"
    NET = "(df['DISCHARGE_PSI'] - df['SUCTION_PSI'])"
    CC = f"(df['CHURN_NET_PSI'] * ({n0} / df['CHURN_RPM']) ** 2)"
    RQ = f"(df['FT_RATED_GPM'] * {n0} / df['FT_RATED_RPM'])"
    RP = f"(df['FT_RATED_NET_PSI'] * ({n0} / df['FT_RATED_RPM']) ** 2)"
    PQ = f"(df['FT_PEAK_GPM'] * {n0} / df['FT_PEAK_RPM'])"
    PP = f"(df['FT_PEAK_NET_PSI'] * ({n0} / df['FT_PEAK_RPM']) ** 2)"
    RR = f"({RP} / {_poly(k['h'], f'({RQ} / 1000)')})"
    PR = f"({PP} / {_poly(k['h'], f'({PQ} / 1000)')})"
    CR = f"({CC} / {k['h'][0]})"
    LEAK = f"(df['JOCKEY_RUN_MIN_24H'] * {k['jf']} / 1440)"
    return dict(k=k, S=S, RUN=RUN, PEXP=PEXP, IEXP=IEXP, NET=NET, CC=CC, RQ=RQ, RP=RP, PQ=PQ, PP=PP, RR=RR, PR=PR, CR=CR, LEAK=LEAK)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("NET_PSI", p["NET"]),
        ("EXPECTED_NET_PSI", f"np.where({p['RUN']}, {p['PEXP']}, 0)"),
        ("LIVE_PERF_RATIO", f"np.where({p['RUN']}, {p['NET']} / {p['PEXP']}, 1)"),
        ("EXPECTED_CURRENT_A", f"np.where({p['RUN']}, {p['IEXP']}, 0)"),
        ("MOTOR_LOAD_PCT", f"df['MOTOR_CURRENT_A'] / {k['fla']} * 100"),
        ("CHURN_NET_CORR_PSI", p["CC"]),
        ("CHURN_RATIO", p["CR"]),
        ("CHURN_PCT_RATED", f"{p['CC']} / {k['p0']} * 100"),
        ("FT_RATED_GPM_CORR", p["RQ"]),
        ("FT_RATED_NET_CORR_PSI", p["RP"]),
        ("FT_RATED_RATIO", p["RR"]),
        ("FT_PEAK_GPM_CORR", p["PQ"]),
        ("FT_PEAK_NET_CORR_PSI", p["PP"]),
        ("FT_PEAK_RATIO", p["PR"]),
        ("FT_PEAK_PCT_RATED", f"{p['PP']} / {k['p0']} * 100"),
        ("FT_MIN_RATIO", f"np.minimum({p['RR']}, {p['PR']})"),
        ("JOCKEY_LEAK_GPM", p["LEAK"]),
        ("START_PSI_DEV", f"df['LAST_START_PSI'] - {k['fpstart']}"),
        ("SUCTION_MARGIN_TEST_PSI", f"df['FT_PEAK_SUCTION_PSI'] - {k['smin']}"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    n0 = k["n0"]
    s = max(r["speed_rpm"], 300)
    run = r["pump_running"] > 0.5 and r["speed_rpm"] > 300
    ql = r["flow_gpm"] * n0 / s
    pexp = (s / n0) ** 2 * H(k, ql)
    iexp = BHP(k, ql) * (s / n0) ** 3 * float(f"{745.7 / (math.sqrt(3) * k['eff'] * k['pf']):.9g}") / r["supply_voltage_v"]
    net = r["discharge_psi"] - r["suction_psi"]
    cc = r["churn_net_psi"] * (n0 / r["churn_rpm"]) ** 2
    rq, rp = r["ft_rated_gpm"] * n0 / r["ft_rated_rpm"], r["ft_rated_net_psi"] * (n0 / r["ft_rated_rpm"]) ** 2
    pq, pp = r["ft_peak_gpm"] * n0 / r["ft_peak_rpm"], r["ft_peak_net_psi"] * (n0 / r["ft_peak_rpm"]) ** 2
    rr, pr = rp / H(k, rq), pp / H(k, pq)
    return {
        "net_psi": net, "expected_net_psi": pexp if run else 0.0, "live_perf_ratio": net / pexp if run else 1.0,
        "expected_current_a": iexp if run else 0.0, "motor_load_pct": r["motor_current_a"] / k["fla"] * 100,
        "churn_net_corr_psi": cc, "churn_ratio": cc / k["h"][0], "churn_pct_rated": cc / k["p0"] * 100,
        "ft_rated_gpm_corr": rq, "ft_rated_net_corr_psi": rp, "ft_rated_ratio": rr,
        "ft_peak_gpm_corr": pq, "ft_peak_net_corr_psi": pp, "ft_peak_ratio": pr, "ft_peak_pct_rated": pp / k["p0"] * 100,
        "ft_min_ratio": min(rr, pr), "jockey_leak_gpm": r["jockey_run_min_24h"] * k["jf"] / 1440,
        "start_psi_dev": r["last_start_psi"] - k["fpstart"], "suction_margin_test_psi": r["ft_peak_suction_psi"] - k["smin"],
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    return [
        ("FP_PEAK_BELOW_65", f"{p['PP']} / {k['p0']} * 100 < {L['peak_min_pct']}", "Critical", None),
        ("FP_CURVE_DEGRADED", f"np.minimum({p['RR']}, {p['PR']}) < {L['curve_ratio_min']}", "High", "impeller_wear"),
        ("FP_SUCTION_LOW_TEST", f"df['FT_PEAK_SUCTION_PSI'] < {L['suction_min_psi']}", "High", "weak_supply"),
        ("FP_JOCKEY_FAILED", f"(df['JOCKEY_STARTS_24H'] < 0.5) & (df['PUMP_RUNNING'] < 0.5) & (df['DISCHARGE_PSI'] < {k['jstart']})", "High", "jockey_failed"),
        ("FP_START_SLOW", f"df['TIME_TO_RUN_S'] > {L['time_to_run_max_s']}", "High", "starter_fault"),
        ("FP_ROOM_COLD", f"df['ROOM_TEMP_C'] < {L['room_min_c']}", "High", None),
        ("FP_FLOW_TEST_OVERDUE", f"df['DAYS_SINCE_FLOW_TEST'] > {L['flow_test_overdue_days']}", "High", "tests_skipped"),
        ("FP_CHURN_DEVIATION", f"np.abs({p['CR']} - 1) > {L['churn_dev_max']}", "Medium", "impeller_wear"),
        ("FP_SUPPLY_STATIC_LOW", f"(df['PUMP_RUNNING'] < 0.5) & (df['SUCTION_PSI'] < {L['static_suction_alert_psi']})", "Medium", "weak_supply"),
        ("FP_JOCKEY_CYCLING", f"df['JOCKEY_STARTS_24H'] > {L['jockey_starts_max']}", "Medium", "system_leak"),
        ("FP_LEAK_HIGH", f"{p['LEAK']} > {L['leak_gpm_max']}", "Medium", "system_leak"),
        ("FP_UNPLANNED_STARTS", "df['AUTO_STARTS_30D'] > 0.5", "Medium", "jockey_failed"),
        ("FP_START_PRESSURE_OFF", f"np.abs(df['LAST_START_PSI'] - {k['fpstart']}) > {L['start_psi_dev_max']}", "Medium", "pressure_sensing_drift"),
        ("FP_PACKING_HOT", f"df['CHURN_PACKING_C'] > {L['packing_max_c']}", "Medium", "packing_overtight"),
        ("FP_CHURN_TEST_OVERDUE", f"df['DAYS_SINCE_CHURN'] > {L['churn_overdue_days']}", "Medium", "tests_skipped"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    add(t["ft_peak_pct_rated"] < L["peak_min_pct"], "FP_PEAK_BELOW_65", "Critical",
        f"At 150 % flow the pump gave {t['ft_peak_pct_rated']:.0f} % of rated pressure: below the NFPA 20 listing minimum of {L['peak_min_pct']:.0f} %", "pump")
    add(t["ft_min_ratio"] < L["curve_ratio_min"], "FP_CURVE_DEGRADED", "High",
        f"Annual flow test at {t['ft_min_ratio'] * 100:.1f} % of the curve (100 % point {t['ft_rated_ratio'] * 100:.1f} %, 150 % point {t['ft_peak_ratio'] * 100:.1f} %): below 95 %",
        "pump", "impeller_wear")
    add(r["ft_peak_suction_psi"] < L["suction_min_psi"], "FP_SUCTION_LOW_TEST", "High",
        f"Suction fell to {r['ft_peak_suction_psi']:.1f} psi at 150 % flow, below {L['suction_min_psi']:.0f} psi", "supply", "weak_supply")
    add(r["jockey_starts_24h"] < 0.5 and r["pump_running"] < 0.5 and r["discharge_psi"] < k["jstart"], "FP_JOCKEY_FAILED", "High",
        f"System at {r['discharge_psi']:.0f} psi, below the jockey start ({k['jstart']:.0f} psi), and no jockey start in 24 h", "jockey", "jockey_failed")
    add(r["time_to_run_s"] > L["time_to_run_max_s"], "FP_START_SLOW", "High", f"Last start took {r['time_to_run_s']:.1f} s from signal to running", "controller", "starter_fault")
    add(r["room_temp_c"] < L["room_min_c"], "FP_ROOM_COLD", "High", f"Pump room at {r['room_temp_c']:.1f} °C, below {L['room_min_c']} °C", "room")
    add(r["days_since_flow_test"] > L["flow_test_overdue_days"], "FP_FLOW_TEST_OVERDUE", "High",
        f"Last annual flow test {r['days_since_flow_test']:.0f} days ago", "testing", "tests_skipped")
    add(abs(t["churn_ratio"] - 1) > L["churn_dev_max"], "FP_CHURN_DEVIATION", "Medium",
        f"Churn {t['churn_net_corr_psi']:.1f} psi at rated speed, {(t['churn_ratio'] - 1) * 100:+.1f} % from the curve", "pump", "impeller_wear")
    add(r["pump_running"] < 0.5 and r["suction_psi"] < L["static_suction_alert_psi"], "FP_SUPPLY_STATIC_LOW", "Medium",
        f"Static suction {r['suction_psi']:.1f} psi, below {L['static_suction_alert_psi']:.0f} psi", "supply", "weak_supply")
    add(r["jockey_starts_24h"] > L["jockey_starts_max"], "FP_JOCKEY_CYCLING", "Medium", f"Jockey pump started {r['jockey_starts_24h']:.0f} times in 24 h", "jockey", "system_leak")
    add(t["jockey_leak_gpm"] > L["leak_gpm_max"], "FP_LEAK_HIGH", "Medium", f"Make-up flow {t['jockey_leak_gpm']:.2f} gpm: the system is leaking", "system", "system_leak")
    add(r["auto_starts_30d"] > 0.5, "FP_UNPLANNED_STARTS", "Medium", f"{r['auto_starts_30d']:.0f} automatic fire pump starts in 30 days without a fire or a test", "controller", "jockey_failed")
    add(abs(r["last_start_psi"] - k["fpstart"]) > L["start_psi_dev_max"], "FP_START_PRESSURE_OFF", "Medium",
        f"Last start at {r['last_start_psi']:.1f} psi, set point {k['fpstart']:.0f} psi", "controller", "pressure_sensing_drift")
    add(r["churn_packing_c"] > L["packing_max_c"], "FP_PACKING_HOT", "Medium", f"Packing at {r['churn_packing_c']:.0f} °C after the churn test", "pump", "packing_overtight")
    add(r["days_since_churn"] > L["churn_overdue_days"], "FP_CHURN_TEST_OVERDUE", "Medium", f"Last churn test {r['days_since_churn']:.0f} days ago", "testing", "tests_skipped")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
