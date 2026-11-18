"""The pressure relief valve twin's expectations (PSV-2601, conventional spring-loaded PRV, API 526 J orifice).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Operating margin (spring-loaded valves simmer and leak when the operating pressure gets close to set):
    operating ratio = drum pressure / set x 100        watch from 90 %, act from 95 %
Capacity (API 520 Part I, vapour in critical flow, SI units: A mm2, W kg/h, P1 kPa abs, T K):
    A_required = W / (C Kd P1 Kb Kc) x sqrt(T Z / M)
    C = 0.03948 sqrt(k (2/(k+1))^((k+1)/(k-1)))        P1 = set x (1 + overpressure) + atmospheric
    W = load factor x vapour feed (governing case: blocked outlet, API 521); T = live drum temperature
    rated capacity of the installed orifice = A_eff x C Kd P1 Kb Kc / sqrt(T Z / M)       (API 526 effective area)
    capacity utilisation = A_required / A_eff x 100
Installation (values recorded at full lift):
    inlet loss = (drum - valve inlet) / set x 100          API 520 Part II: within 3 % of set
    built-up back pressure = outlet / set x 100            API 520 Part I: within 10 % of set (conventional valve)
    opening = open pressure / set x 100; accumulation = (peak - MAWP) / MAWP x 100 (ASME: 10 % for one valve)
Leak (passing) detection: acoustic level above background AND outlet pipe temperature away from ambient, while the drum
    is below the simmer zone and the valve is not lifting (gas passing usually cools the pipe, liquid warms it).
Bench test (API 576 / API 527):
    pop deviation = (as-found - set) / set x 100          tolerance +-3 % (ASME, above 70 psig)
    drift rate = (as-found - previous as-left) / set x 100 / years in service
    seat leak ratio = bubbles per minute at 90 % of set / API 527 limit
Risk-based interval (fleet + this valve):
    fleet lambda = chi2(conf; 2n+2) / (2 x valve-years)    (upper bound of the fail-to-open rate from bench-test history)
    POFOD(T) = 1 - (1 - exp(-lambda T)) / (lambda T)      -> T_fleet where POFOD = target
    RBI interval = min(code maximum, T_fleet, drift allowance / |drift rate|)
"""
import math

ATM_BAR = 1.01325


def chi2_ppf_even(p, dof):
    """Chi-square quantile for an even number of degrees of freedom (closed-form CDF, bisection)."""
    k = dof // 2
    cdf = lambda x: 1 - math.exp(-x / 2) * sum((x / 2) ** i / math.factorial(i) for i in range(k))
    lo, hi = 0.0, 500.0
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if cdf(mid) < p else (lo, mid)
    return (lo + hi) / 2


def pofod(lam, t):
    """Average probability of failure on demand over a test interval t (years) for a constant fail-to-open rate lam (/y)."""
    x = lam * t
    return 1 - (1 - math.exp(-x)) / x if x > 0 else 0.0


def interval_for(lam, target):
    """Test interval (years) at which the average POFOD reaches the target."""
    lo, hi = 1e-6, 200.0
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if pofod(lam, mid) < target else (lo, mid)
    return (lo + hi) / 2


def api520_c(k):
    return 0.03948 * math.sqrt(k * (2 / (k + 1)) ** ((k + 1) / (k - 1)))


def api520_area_mm2(w_kgh, t_k, z, mw, k, p1_kpa, kd=0.975, kb=1.0, kc=1.0):
    return w_kgh / (api520_c(k) * kd * p1_kpa * kb * kc) * math.sqrt(t_k * z / mw)


def _k(twin):
    d = twin["design"]
    v, va, fl, rl, ln, ac, bn, rb = (d["vessel"], d["valve"], d["fluid"], d["relief"], d["lines"], d["acoustic"],
                                      d["bench"], d["rbi"])
    c = api520_c(fl["k"])
    p1 = (v["set_barg"] * (1 + v["overpressure_pct"] / 100) + ATM_BAR) * 100.0
    lam = chi2_ppf_even(rb["confidence"], 2 * rb["fleet_failures"] + 2) / (2 * rb["fleet_valve_years"])
    tfleet = interval_for(lam, rb["pofod_target"])
    return dict(set=v["set_barg"], mawp=v["mawp_barg"], acc=v["accumulation_limit_pct"], c=c, p1=p1,
                kd=va["kd"], kb=va["kb"], kc=va["kc"], aeff=va["area_eff_mm2"], mw=fl["mw"], kk=fl["k"], z=fl["z"],
                lf=rl["load_factor"], feed=rl["design_feed_kgh"], inlet_lim=ln["inlet_loss_limit_pct"], bp_lim=ln["builtup_bp_limit_pct"],
                bg=ac["background_counts"], tol=bn["set_tolerance_pct"], bpm=bn["seat_leak_limit_bpm"],
                planned=rb["planned_interval_y"], codemax=rb["code_max_interval_y"], lam=lam, tfleet=tfleet,
                cap=min(rb["code_max_interval_y"], tfleet), allow=rb["drift_allow_pct"], cdk=c * va["kd"] * p1 * va["kb"] * va["kc"])


def _parts(twin):
    k = _k(twin)
    s = k["set"]
    SQ = f"np.sqrt((df['VESSEL_TEMP_C'] + 273.15) * {k['z']} / {k['mw']})"
    LOAD = f"({k['lf']} * df['VAPOUR_FEED_KGH'])"
    AREQ = f"({LOAD} * {SQ} / {k['cdk']!r})"
    OP = f"(df['VESSEL_PRESSURE_BARG'] / {s} * 100)"
    DRIFT = f"((df['TEST_ASFOUND_BARG'] - df['TEST_PREV_ASLEFT_BARG']) / {s} * 100 / (df['TEST_INTERVAL_H'] / 8760))"
    RBI = f"np.minimum({k['cap']:.6g}, {k['allow']} / np.maximum(np.abs({DRIFT}), 0.05))"
    return dict(k=k, SQ=SQ, LOAD=LOAD, AREQ=AREQ, OP=OP, DRIFT=DRIFT, RBI=RBI,
                UTIL=f"({AREQ} / {k['aeff']} * 100)", EXC=f"(df['ACOUSTIC_LEVEL'] - {k['bg']})", DT="(df['OUTLET_TEMP_C'] - df['AMBIENT_TEMP_C'])",
                INL=f"((df['LIFT_VESSEL_BARG'] - df['LIFT_INLET_BARG']) / {s} * 100)", BU=f"(df['LIFT_OUTLET_BARG'] / {s} * 100)",
                OPEN=f"(df['LIFT_OPEN_BARG'] / {s} * 100)", ACC=f"((df['LIFT_PEAK_BARG'] - {k['mawp']}) / {k['mawp']} * 100)",
                POP=f"((df['TEST_ASFOUND_BARG'] - {s}) / {s} * 100)")


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("OP_RATIO_PCT", p["OP"]),
        ("RELIEF_LOAD_KGH", p["LOAD"]),
        ("REQUIRED_AREA_MM2", p["AREQ"]),
        ("RATED_CAPACITY_KGH", f"{k['aeff'] * k['cdk']!r} / {p['SQ']}"),
        ("CAPACITY_UTIL_PCT", p["UTIL"]),
        ("ACOUSTIC_EXCESS", p["EXC"]),
        ("OUTLET_DT_K", p["DT"]),
        ("INLET_LOSS_PCT", p["INL"]),
        ("BUILTUP_BP_PCT", p["BU"]),
        ("SUPERIMPOSED_BP_PCT", f"df['HEADER_PRESSURE_BARG'] / {k['set']} * 100"),
        ("OPEN_PCT_OF_SET", p["OPEN"]),
        ("ACCUMULATION_PCT", p["ACC"]),
        ("POP_DEV_PCT", p["POP"]),
        ("DRIFT_RATE_PCT_Y", p["DRIFT"]),
        ("SEAT_LEAK_RATIO", f"df['TEST_SEAT_BPM'] / {k['bpm']}"),
        ("RBI_INTERVAL_Y", p["RBI"]),
        ("TEST_DUE_RATIO", f"df['TEST_HOURS_SINCE'] / {k['planned'] * 8760:.6g}"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    s = k["set"]
    sq = math.sqrt((r["vessel_temp_c"] + 273.15) * k["z"] / k["mw"])
    load = k["lf"] * r["vapour_feed_kgh"]
    areq = load * sq / k["cdk"]
    drift = (r["test_asfound_barg"] - r["test_prev_asleft_barg"]) / s * 100 / (r["test_interval_h"] / 8760)
    return {
        "op_ratio_pct": r["vessel_pressure_barg"] / s * 100, "relief_load_kgh": load, "required_area_mm2": areq,
        "rated_capacity_kgh": k["aeff"] * k["cdk"] / sq, "capacity_util_pct": areq / k["aeff"] * 100,
        "acoustic_excess": r["acoustic_level"] - k["bg"], "outlet_dt_k": r["outlet_temp_c"] - r["ambient_temp_c"],
        "inlet_loss_pct": (r["lift_vessel_barg"] - r["lift_inlet_barg"]) / s * 100, "builtup_bp_pct": r["lift_outlet_barg"] / s * 100,
        "superimposed_bp_pct": r["header_pressure_barg"] / s * 100, "open_pct_of_set": r["lift_open_barg"] / s * 100,
        "accumulation_pct": (r["lift_peak_barg"] - k["mawp"]) / k["mawp"] * 100, "pop_dev_pct": (r["test_asfound_barg"] - s) / s * 100,
        "drift_rate_pct_y": drift, "seat_leak_ratio": r["test_seat_bpm"] / k["bpm"],
        "rbi_interval_y": min(k["cap"], k["allow"] / max(abs(drift), 0.05)),
        "test_due_ratio": r["test_hours_since"] / (k["planned"] * 8760),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    NL = "(df['LIFT_ACTIVE'] < 0.5)"
    return [
        ("PSV_CAPACITY_SHORT", f"{p['UTIL']} > {L['util_limit_pct']}", "Critical", "relief_load_increase"),
        ("PSV_ACCUMULATION", f"{p['ACC']} > {k['acc']}", "Critical", "valve_sticking"),
        ("PSV_LATE_OPENING", f"{p['OPEN']} > {100 + k['tol']}", "High", "valve_sticking"),
        ("PSV_INLET_LOSS", f"{p['INL']} > {k['inlet_lim']}", "High", "inlet_restriction"),
        ("PSV_BACKPRESSURE_HIGH", f"{p['BU']} > {k['bp_lim']}", "High", "high_backpressure"),
        ("PSV_PASSING", f"({p['EXC']} > {L['acoustic_excess_alert']}) & (np.abs({p['DT']}) > {L['outlet_dt_alert_k']}) & {NL} & ({p['OP']} < {L['simmer_pct']})",
         "High", "seat_passing"),
        ("PSV_NEAR_SET", f"({p['OP']} >= {L['near_set_pct']}) & {NL}", "High", "operating_near_set"),
        ("PSV_TEST_OVERDUE", f"df['TEST_HOURS_SINCE'] > {k['planned'] * 8760:.6g}", "High", "test_overdue"),
        ("PSV_SIMMER_ZONE", f"({p['OP']} >= {L['simmer_pct']}) & ({p['OP']} < {L['near_set_pct']}) & {NL}", "Medium", "operating_near_set"),
        ("PSV_CAPACITY_MARGIN", f"({p['UTIL']} > {L['util_alert_pct']}) & ({p['UTIL']} <= {L['util_limit_pct']})", "Medium", "relief_load_increase"),
        ("PSV_CHATTER", f"(df['LIFT_COUNT_30D'] >= {L['chatter_lifts_30d']}) & (df['LIFT_DURATION_S'] < {L['chatter_duration_s']})", "Medium", "inlet_restriction"),
        ("PSV_POP_DRIFT", f"np.abs({p['POP']}) > {k['tol']}", "Medium", "set_pressure_drift"),
        ("PSV_SEAT_TIGHTNESS", f"df['TEST_SEAT_BPM'] > {k['bpm']}", "Medium", "set_pressure_drift"),
        ("PSV_RBI_INTERVAL_SHORT", f"{p['RBI']} < {k['planned']}", "Medium", "set_pressure_drift"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    nl = r["lift_active"] < 0.5
    op, ut = t["op_ratio_pct"], t["capacity_util_pct"]
    add(ut > L["util_limit_pct"], "PSV_CAPACITY_SHORT", "Critical",
        f"Required relieving rate {t['relief_load_kgh']:.0f} kg/h is {ut:.0f} % of what the J orifice passes ({t['rated_capacity_kgh']:.0f} kg/h)",
        "process", "relief_load_increase")
    add(t["accumulation_pct"] > k["acc"], "PSV_ACCUMULATION", "Critical",
        f"Drum peaked at {r['lift_peak_barg']:.2f} barg in the last lift: {t['accumulation_pct']:.1f} % above MAWP (limit {k['acc']:.0f} %)", "disc", "valve_sticking")
    add(t["open_pct_of_set"] > 100 + k["tol"], "PSV_LATE_OPENING", "High",
        f"Last lift started at {r['lift_open_barg']:.2f} barg, {t['open_pct_of_set']:.1f} % of set (tolerance +{k['tol']:.0f} %)", "disc", "valve_sticking")
    add(t["inlet_loss_pct"] > k["inlet_lim"], "PSV_INLET_LOSS", "High",
        f"Inlet loss {t['inlet_loss_pct']:.1f} % of set at full lift (API 520 Part II: {k['inlet_lim']:.0f} %)", "inlet", "inlet_restriction")
    add(t["builtup_bp_pct"] > k["bp_lim"], "PSV_BACKPRESSURE_HIGH", "High",
        f"Built-up back pressure {r['lift_outlet_barg']:.2f} barg, {t['builtup_bp_pct']:.1f} % of set (conventional valve: {k['bp_lim']:.0f} %)", "outlet", "high_backpressure")
    add(t["acoustic_excess"] > L["acoustic_excess_alert"] and abs(t["outlet_dt_k"]) > L["outlet_dt_alert_k"] and nl and op < L["simmer_pct"],
        "PSV_PASSING", "High", f"Valve passing: acoustic {t['acoustic_excess']:+.0f} counts over background, outlet {t['outlet_dt_k']:+.1f} K from ambient, drum at {op:.0f} % of set",
        "seat", "seat_passing")
    add(op >= L["near_set_pct"] and nl, "PSV_NEAR_SET", "High", f"Drum at {op:.1f} % of set: the valve simmers and the seat wears", "process", "operating_near_set")
    add(r["test_hours_since"] > k["planned"] * 8760, "PSV_TEST_OVERDUE", "High",
        f"Bench test {(r['test_hours_since'] - k['planned'] * 8760):.0f} h overdue", "testing", "test_overdue")
    add(L["simmer_pct"] <= op < L["near_set_pct"] and nl, "PSV_SIMMER_ZONE", "Medium", f"Drum at {op:.1f} % of set: inside the simmer zone", "process", "operating_near_set")
    add(L["util_alert_pct"] < ut <= L["util_limit_pct"], "PSV_CAPACITY_MARGIN", "Medium",
        f"Capacity utilisation {ut:.0f} %: little margin left on the J orifice", "process", "relief_load_increase")
    add(r["lift_count_30d"] >= L["chatter_lifts_30d"] and r["lift_duration_s"] < L["chatter_duration_s"], "PSV_CHATTER", "Medium",
        f"{r['lift_count_30d']:.0f} lifts in 30 days, last one {r['lift_duration_s']:.0f} s: the valve is chattering", "inlet", "inlet_restriction")
    add(abs(t["pop_dev_pct"]) > k["tol"], "PSV_POP_DRIFT", "Medium",
        f"As-found pop {r['test_asfound_barg']:.2f} barg, {t['pop_dev_pct']:+.1f} % from set (tolerance {k['tol']:.0f} %)", "spring", "set_pressure_drift")
    add(r["test_seat_bpm"] > k["bpm"], "PSV_SEAT_TIGHTNESS", "Medium",
        f"Seat leak {r['test_seat_bpm']:.0f} bubbles/min at 90 % of set (API 527: {k['bpm']:.0f})", "seat", "set_pressure_drift")
    add(t["rbi_interval_y"] < k["planned"], "PSV_RBI_INTERVAL_SHORT", "Medium",
        f"Drift {t['drift_rate_pct_y']:+.2f} %/year: safe test interval {t['rbi_interval_y']:.1f} y, shorter than the planned {k['planned']:.0f} y",
        "spring", "set_pressure_drift")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
