"""The steam trap twin's expectations (ST-4701, Spirax Sarco TD52M thermodynamic trap, and its 800-trap population).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Saturation temperature (IAPWS-IF97 region 4 backward equation, p in MPa, T in K):
    beta = p^0.25;  E = beta^2 + n3 beta + n6;  F = n1 beta^2 + n4 beta + n7;  G = n2 beta^2 + n5 beta + n8
    D = 2G / (-F - sqrt(F^2 - 4EG));  Ts = (n10 + D - sqrt((n10 + D)^2 - 4 (n9 + n10 D))) / 2
Is the trap draining?  A healthy trap inlet sits at saturation (minus a small clamp-on offset):
    subcooling = Ts - inlet temperature;  excess = subcooling - offset
    excess > 12 K with flow noise: condensate backing up;  excess > 30 K and silent: blocked cold.
Is the trap passing steam?  Rosemount 708 acoustic level against two lines that grow with the differential pressure dp:
    expected (healthy) = a0 + a1 dp;   full open = open0 + open1 dp
    leak fraction = clip((level - expected) / (full open - expected), 0, 1), counted as steam only when the inlet is at
    saturation (a loud trap with a subcooled inlet is passing water, not steam).
Steam loss (Napier, saturated steam through an orifice to atmosphere, US DOE tip sheet Cd 0.72):
    W [lb/h] = 51.43 x Cd x A [sq.in] x P [psia]  ->  W [kg/h] = 0.5244 x Cd x A [mm2] x P [bar abs]
    loss now = leak fraction x W(failed-open orifice);  cost = loss x hours x price;  CO2 = loss x hours x (hg - hfw) / eta x EF
Population (trap survey records):
    failed-open share = failed open / total;  population loss = failed open x W;  failure rate = new failed open in 365 d / total
    best survey interval (failures appear at rate r per year, each costs c per year until found, a survey costs S):
        yearly cost = r c T / 2 + S / T   ->   T* = sqrt(2 S / (r c))
"""
import math

N = [0.0, 0.11670521452767e4, -0.72421316703206e6, -0.17073846940092e2, 0.12020824702470e5, -0.32325550322333e7,
     0.14915108613530e2, -0.48232657361591e4, 0.40511340542057e6, -0.23855557567849, 0.65017534844798e3]
LB_KG, PSI_BAR, MM2_IN2 = 0.45359237, 14.503773773, 645.16


def tsat_k(p_mpa):
    """IAPWS-IF97 Eq. (31): saturation temperature (K) at pressure p (MPa)."""
    b = p_mpa ** 0.25
    e = b * b + N[3] * b + N[6]
    f = N[1] * b * b + N[4] * b + N[7]
    g = N[2] * b * b + N[5] * b + N[8]
    d = 2 * g / (-f - math.sqrt(f * f - 4 * e * g))
    return (N[10] + d - math.sqrt((N[10] + d) ** 2 - 4 * (N[9] + N[10] * d))) / 2


def napier_kgh(d_mm, p_bara, cd, c_lbh=51.43):
    """Saturated steam through an orifice of diameter d_mm at p_bara, discharging to atmosphere (kg/h)."""
    k = c_lbh * LB_KG * PSI_BAR / MM2_IN2
    return k * cd * math.pi / 4 * d_mm ** 2 * p_bara


def _k(twin):
    d = twin["design"]
    st, lk, ac, th, cy, ec, po, tr = (d["steam"], d["leak"], d["acoustic"], d["thermal"], d["cycling"], d["economics"],
                                      d["population"], d["trap"])
    kflow = lk["napier_c_lbh"] * LB_KG * PSI_BAR / MM2_IN2 * lk["cd"] * math.pi / 4 * lk["orifice_mm"] ** 2   # kg/h per bar abs
    co2 = (st["hg_kj_kg"] - st["h_feedwater_kj_kg"]) / 1000 / ec["boiler_efficiency"] * ec["ef_kg_co2_per_gj"] / 1000  # kg CO2 / kg steam
    return dict(atm=st["atm_bar"], kflow=kflow, co2=co2, a0=ac["a0_counts"], a1=ac["a1_counts_per_bar"], o0=ac["open0_counts"],
                o1=ac["open1_counts_per_bar"], off=th["surface_offset_c"], cyc=cy["design_cycles_per_min"],
                price=ec["steam_price_per_t"], hours=ec["hours_per_year"], scost=ec["survey_cost_per_trap"],
                rate_open=po["design_fail_open_rate_pct_y"], rate_cold=po["design_fail_cold_rate_pct_y"],
                total=po["traps_total"], pline=st["line_pressure_barg"], pmob=tr["pmob_pct"], mindp=tr["min_dp_bar"])


def _parts(twin):
    k = _k(twin)
    n = N
    B = f"(((df['LINE_PRESSURE_BARG'] + {k['atm']}) / 10) ** 0.25)"
    E = f"({B} ** 2 + {n[3]!r} * {B} + {n[6]!r})"
    F = f"({n[1]!r} * {B} ** 2 + {n[4]!r} * {B} + {n[7]!r})"
    G = f"({n[2]!r} * {B} ** 2 + {n[5]!r} * {B} + {n[8]!r})"
    D = f"(2 * {G} / (-{F} - np.sqrt({F} ** 2 - 4 * {E} * {G})))"
    TS = f"(({n[10]!r} + {D} - np.sqrt(({n[10]!r} + {D}) ** 2 - 4 * ({n[9]!r} + {n[10]!r} * {D}))) / 2 - 273.15)"
    SUB = f"({TS} - df['INLET_TEMP_C'])"
    EXC = f"({SUB} - {k['off']})"
    DP = "(df['LINE_PRESSURE_BARG'] - df['OUTLET_PRESSURE_BARG'])"
    AE = f"({k['a0']} + {k['a1']} * {DP})"
    AO = f"({k['o0']} + {k['o1']} * {DP})"
    LF = f"np.clip((df['ACOUSTIC_LEVEL'] - {AE}) / ({AO} - {AE}), 0, 1)"
    FULL = f"({k['kflow']:.10g} * (df['LINE_PRESSURE_BARG'] + {k['atm']}))"
    LOSS = f"({LF} * {FULL} * ({EXC} < {twin['twin_model']['limits']['backing_up_excess_c']}))"
    PLOSS = f"(df['POP_FAILED_OPEN'] * {FULL})"
    CY = f"({FULL} * {k['hours'] * k['price'] / 1000:.10g})"
    TSTAR = f"(365 * np.sqrt(2 * {k['scost']} * df['POP_TRAPS_TOTAL'] / (np.maximum(df['POP_NEW_FAILED_OPEN_365D'], 1) * {CY})))"
    return dict(k=k, TS=TS, SUB=SUB, EXC=EXC, DP=DP, AE=AE, LF=LF, FULL=FULL, LOSS=LOSS, PLOSS=PLOSS, TSTAR=TSTAR)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    yr = k["hours"] / 1000
    return [
        ("TSAT_C", p["TS"]),
        ("SUBCOOL_C", p["SUB"]),
        ("SUBCOOL_EXCESS_C", p["EXC"]),
        ("DP_BAR", p["DP"]),
        ("BACKPRESSURE_PCT", "df['OUTLET_PRESSURE_BARG'] / df['LINE_PRESSURE_BARG'] * 100"),
        ("ACOUSTIC_EXPECTED", p["AE"]),
        ("ACOUSTIC_RATIO", f"df['ACOUSTIC_LEVEL'] / {p['AE']}"),
        ("LEAK_FRACTION", p["LF"]),
        ("CYCLE_RATIO", f"df['CYCLE_RATE_PER_MIN'] / {k['cyc']}"),
        ("LOSS_FULL_OPEN_KGH", p["FULL"]),
        ("STEAM_LOSS_KGH", p["LOSS"]),
        ("STEAM_LOSS_COST_Y", f"{p['LOSS']} * {yr * k['price']:.10g}"),
        ("STEAM_LOSS_CO2_T_Y", f"{p['LOSS']} * {yr * k['co2']:.10g}"),
        ("POP_FAILED_OPEN_PCT", "df['POP_FAILED_OPEN'] / df['POP_TRAPS_TOTAL'] * 100"),
        ("POP_FAILED_COLD_PCT", "df['POP_FAILED_COLD'] / df['POP_TRAPS_TOTAL'] * 100"),
        ("POP_LOSS_KGH", p["PLOSS"]),
        ("POP_LOSS_COST_Y", f"{p['PLOSS']} * {yr * k['price']:.10g}"),
        ("POP_CO2_T_Y", f"{p['PLOSS']} * {yr * k['co2']:.10g}"),
        ("POP_FAIL_RATE_PCT_Y", "df['POP_NEW_FAILED_OPEN_365D'] / df['POP_TRAPS_TOTAL'] * 100"),
        ("SURVEY_INTERVAL_OPT_D", p["TSTAR"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    L = twin["twin_model"]["limits"]
    ts = tsat_k((r["line_pressure_barg"] + k["atm"]) / 10) - 273.15
    sub = ts - r["inlet_temp_c"]
    exc = sub - k["off"]
    dp = r["line_pressure_barg"] - r["outlet_pressure_barg"]
    ae, ao = k["a0"] + k["a1"] * dp, k["o0"] + k["o1"] * dp
    lf = min(1.0, max(0.0, (r["acoustic_level"] - ae) / (ao - ae)))
    full = k["kflow"] * (r["line_pressure_barg"] + k["atm"])
    loss = lf * full * (1.0 if exc < L["backing_up_excess_c"] else 0.0)
    ploss = r["pop_failed_open"] * full
    yr = k["hours"] / 1000
    cy = full * k["hours"] * k["price"] / 1000
    return {
        "tsat_c": ts, "subcool_c": sub, "subcool_excess_c": exc, "dp_bar": dp,
        "backpressure_pct": r["outlet_pressure_barg"] / r["line_pressure_barg"] * 100,
        "acoustic_expected": ae, "acoustic_ratio": r["acoustic_level"] / ae, "leak_fraction": lf,
        "cycle_ratio": r["cycle_rate_per_min"] / k["cyc"], "loss_full_open_kgh": full, "steam_loss_kgh": loss,
        "steam_loss_cost_y": loss * yr * k["price"], "steam_loss_co2_t_y": loss * yr * k["co2"],
        "pop_failed_open_pct": r["pop_failed_open"] / r["pop_traps_total"] * 100,
        "pop_failed_cold_pct": r["pop_failed_cold"] / r["pop_traps_total"] * 100,
        "pop_loss_kgh": ploss, "pop_loss_cost_y": ploss * yr * k["price"], "pop_co2_t_y": ploss * yr * k["co2"],
        "pop_fail_rate_pct_y": r["pop_new_failed_open_365d"] / r["pop_traps_total"] * 100,
        "survey_interval_opt_d": 365 * math.sqrt(2 * k["scost"] * r["pop_traps_total"] / (max(r["pop_new_failed_open_365d"], 1) * cy)),
    }


def survey_cost_y(twin, t_days, new_open_per_y, total=None, full_kgh=None):
    """Yearly cost of failed-open traps (lost steam) + manual surveys for a survey interval of t_days."""
    k = _k(twin)
    total = total or k["total"]
    full = full_kgh or k["kflow"] * (k["pline"] + k["atm"])
    c = full * k["hours"] * k["price"] / 1000
    t = t_days / 365
    return new_open_per_y * c * t / 2, k["scost"] * total / t


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    OK = f"(df['INLET_TEMP_C'] > df['AMBIENT_TEMP_C'] + {L['sensor_ambient_margin_c']})"
    STEAM = f"({p['EXC']} < {L['backing_up_excess_c']})"
    LF, EXC = p["LF"], p["EXC"]
    AR = f"(df['ACOUSTIC_LEVEL'] / {p['AE']})"
    return [
        ("TRAP_BLOW_THROUGH", f"({LF} >= {L['leak_fraction_blow']}) & {STEAM} & {OK}", "High", "failed_open"),
        ("TRAP_COLD", f"({EXC} > {L['cold_excess_c']}) & ({AR} < {L['cold_acoustic_ratio']}) & {OK}", "High", "blocked_cold"),
        ("POP_FAILED_OPEN_HIGH", f"df['POP_FAILED_OPEN'] / df['POP_TRAPS_TOTAL'] * 100 > {L['failed_open_alert_pct']}", "High", "survey_lapsed"),
        ("TRAP_LEAKING", f"({LF} >= {L['leak_fraction_alert']}) & ({LF} < {L['leak_fraction_blow']}) & {STEAM} & {OK}", "Medium", "disc_wear"),
        ("TRAP_RAPID_CYCLING", f"df['CYCLE_RATE_PER_MIN'] / {k['cyc']} > {L['rapid_ratio_alert']}", "Medium", "disc_wear"),
        ("TRAP_BACKING_UP", f"({EXC} > {L['backing_up_excess_c']}) & ({AR} >= {L['cold_acoustic_ratio']}) & {OK}", "Medium", "condensate_overload"),
        ("TRAP_BACKPRESSURE_HIGH", f"df['OUTLET_PRESSURE_BARG'] / df['LINE_PRESSURE_BARG'] * 100 > {L['pmob_pct']}", "Medium", "backpressure_high"),
        ("POP_FAILED_COLD_HIGH", f"df['POP_FAILED_COLD'] / df['POP_TRAPS_TOTAL'] * 100 > {L['failed_cold_alert_pct']}", "Medium", "survey_lapsed"),
        ("POP_SURVEY_OVERDUE", f"df['SURVEY_DAYS_SINCE'] > {L['survey_overdue_factor']} * {p['TSTAR']}", "Medium", "survey_lapsed"),
        ("POP_FAIL_RATE_HIGH", f"df['POP_NEW_FAILED_OPEN_365D'] / df['POP_TRAPS_TOTAL'] * 100 > {L['fail_rate_alert_factor'] * k['rate_open']}", "Medium", "population_ageing"),
        ("TRAP_DP_LOW", f"{p['DP']} < {L['min_dp_bar']}", "Low", None),
        ("TRAP_SENSOR_SUSPECT", f"df['INLET_TEMP_C'] <= df['AMBIENT_TEMP_C'] + {L['sensor_ambient_margin_c']}", "Low", "sensor_fault"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    ok = r["inlet_temp_c"] > r["ambient_temp_c"] + L["sensor_ambient_margin_c"]
    steam = t["subcool_excess_c"] < L["backing_up_excess_c"]
    lf, exc, ar = t["leak_fraction"], t["subcool_excess_c"], t["acoustic_ratio"]
    add(lf >= L["leak_fraction_blow"] and steam and ok, "TRAP_BLOW_THROUGH", "High",
        f"Blowing steam: leak fraction {lf:.2f}, about {t['steam_loss_kgh']:.1f} kg/h lost", "disc / seat", "failed_open")
    add(exc > L["cold_excess_c"] and ar < L["cold_acoustic_ratio"] and ok, "TRAP_COLD", "High",
        f"Silent and {t['subcool_c']:.0f} K below saturation: drip leg not draining", "strainer / inlet", "blocked_cold")
    add(t["pop_failed_open_pct"] > L["failed_open_alert_pct"], "POP_FAILED_OPEN_HIGH", "High",
        f"{t['pop_failed_open_pct']:.1f} % of traps failed open, {t['pop_loss_kgh'] / 1000:.2f} t/h of steam lost", "population", "survey_lapsed")
    add(L["leak_fraction_alert"] <= lf < L["leak_fraction_blow"] and steam and ok, "TRAP_LEAKING", "Medium",
        f"Passing steam: leak fraction {lf:.2f}, about {t['steam_loss_kgh']:.1f} kg/h", "disc", "disc_wear")
    add(t["cycle_ratio"] > L["rapid_ratio_alert"], "TRAP_RAPID_CYCLING", "Medium",
        f"Cycling {r['cycle_rate_per_min']:.1f} per minute, {t['cycle_ratio']:.1f} x design", "disc", "disc_wear")
    add(exc > L["backing_up_excess_c"] and ar >= L["cold_acoustic_ratio"] and ok, "TRAP_BACKING_UP", "Medium",
        f"Condensate backing up: inlet {t['subcool_c']:.0f} K below saturation", "application", "condensate_overload")
    add(t["backpressure_pct"] > L["pmob_pct"], "TRAP_BACKPRESSURE_HIGH", "Medium",
        f"Discharge at {t['backpressure_pct']:.0f} % of the steam pressure (TD52M limit {L['pmob_pct']:.0f} %)", "condensate return", "backpressure_high")
    add(t["pop_failed_cold_pct"] > L["failed_cold_alert_pct"], "POP_FAILED_COLD_HIGH", "Medium",
        f"{t['pop_failed_cold_pct']:.1f} % of traps failed cold", "population", "survey_lapsed")
    add(r["survey_days_since"] > L["survey_overdue_factor"] * t["survey_interval_opt_d"], "POP_SURVEY_OVERDUE", "Medium",
        f"Last survey {r['survey_days_since']:.0f} d ago; best interval {t['survey_interval_opt_d']:.0f} d", "population", "survey_lapsed")
    add(t["pop_fail_rate_pct_y"] > L["fail_rate_alert_factor"] * k["rate_open"], "POP_FAIL_RATE_HIGH", "Medium",
        f"{t['pop_fail_rate_pct_y']:.1f} % of traps failed open in 365 d (design {k['rate_open']:.0f} %)", "population", "population_ageing")
    add(t["dp_bar"] < L["min_dp_bar"], "TRAP_DP_LOW", "Low", f"Differential {t['dp_bar']:.2f} bar, below the {L['min_dp_bar']} bar minimum", "application")
    add(not ok, "TRAP_SENSOR_SUSPECT", "Low", f"Pipe temperature {r['inlet_temp_c']:.0f} °C near ambient: transmitter loose?", "monitor", "sensor_fault")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
