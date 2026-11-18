"""The metro escalator twin's expectations (ES-5601, KONE TransitMaster 140, 10 m rise, 30 degrees, 0.5 m/s).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Every expression works on one reading (no history in Monitor).

Motor power (Al-Sharif's measured no-load model + lifting the passengers):
    P_NL = 0.47 x rise + 1.74 kW at rated speed, taken as proportional to the step speed v
    lift power X = (passengers per min / 60) x m x g x rise / 1000 kW       (m = 75 kg per passenger)
    expected P = P_NL x v / v_rated + X / eta (up)   or   - X x eta (down: the passengers drive the band)
    drag ratio = (P - load term) x v_rated / v / P_NL   (1.0 = step band runs as freely as designed)
    energy per passenger = P x 1000 / 60 / passengers per min   (Wh)
Handrail: deviation = (handrail speed / step speed - 1) x 100 %; EN 115-1 normal operation 0 to +2 %, monitor trip at 15 %.
Step chain: expected elongation = e0 + wear rate x run hours; residual = measured - expected; hours to the replacement limit.
Brake (last stop, from the controller's encoder): mean deceleration a under full brake torque, delay t_d, load m_L, direction d.
    Newton along the incline:   (m_eq + m_L) a = F_b + F_f + d m_L g sin(alpha)      (d = +1 up: gravity helps the brake)
    so the brake force         F_b = (m_eq + m_L) a - F_f - d m_L g sin(alpha)
    with F_f = share x P_NL / v_rated the step band friction. Then, for the same brake:
    fully loaded, running down:  a_fd = (F_b + F_f - m_full g sin(alpha)) / (m_eq + m_full),  m_full = 120 kg x rise / riser
    empty:                       a_e  = (F_b + F_f) / m_eq
    stopping distance            s = v_rated t_d + v_rated^2 / (2 a)       -> compared with EN 115-1 0.20 m (empty) to 1.00 m (full, down)
Gearbox: expected oil temperature = ambient + k0 + k1 x 15-min mean power; vibration / commissioning baseline.
Energy saving: kWh/day lost when the stand-by share falls below the expected share.
"""
import math

G = 9.81


def _k(twin):
    d = twin["design"]
    ge, sp, dr, pa, br, hr, ch, gb, sa, en = (d[x] for x in ("geometry", "speed", "drive", "passengers", "brake", "handrail",
                                                            "chain", "gearbox", "safety", "energy"))
    H, alpha = ge["rise_m"], math.radians(ge["inclination_deg"])
    pnl = dr["noload_a_kw_per_m"] * H + dr["noload_b_kw"]
    riser = ge["step_depth_m"] * math.tan(alpha)
    nsteps = H / riser
    vr = sp["rated_ms"]
    return dict(H=H, sin=math.sin(alpha), vr=vr, vsb=sp["standby_ms"], pnl=pnl, eta=dr["eta_load"],
                ff=dr["friction_share"] * pnl * 1000 / vr, m=pa["mass_kg"], duty=pa["duty_h_per_day"],
                riser=riser, nsteps=nsteps, mfull=br["brake_load_kg_per_step"] * nsteps, meq=br["m_eq_kg"],
                td=br["delay_s"], smin=br["stop_min_m"], smax=br["stop_max_m"],
                hmin=hr["tol_min_pct"], hmax=hr["tol_max_pct"], e0=ch["elong0_pct"], w=ch["wear_pct_per_1000h"],
                ealert=ch["alert_pct"], erep=ch["replace_pct"], k0=gb["oil_rise0_k"], k1=gb["oil_k_per_kw"],
                vib0=gb["vib_baseline_mms"], fexp=en["standby_share_expected"])


def _parts(twin):
    k = _k(twin)
    X = f"(df['PASSENGERS_PER_MIN'] / 60 * {k['m'] * G * k['H'] / 1000:.10g})"
    LOAD = f"np.where(df['DIRECTION'] > 0, {X} / {k['eta']}, -{X} * {k['eta']})"
    NL = f"((df['MOTOR_POWER_KW'] - {LOAD}) * {k['vr']} / np.maximum(df['STEP_SPEED_MS'], 0.05))"
    DRAG = f"({NL} / {k['pnl']:.10g})"
    HL = "((df['HANDRAIL_LEFT_MS'] / np.maximum(df['STEP_SPEED_MS'], 0.05) - 1) * 100)"
    HR = "((df['HANDRAIL_RIGHT_MS'] / np.maximum(df['STEP_SPEED_MS'], 0.05) - 1) * 100)"
    CE = f"({k['e0']} + {k['w']} * df['RUN_HOURS'] / 1000)"
    BF = (f"(((({k['meq']} + df['LAST_STOP_LOAD_KG']) * df['LAST_STOP_DECEL_MS2'] - {k['ff']:.10g}"
          f" - df['LAST_STOP_DIR'] * df['LAST_STOP_LOAD_KG'] * {G * k['sin']:.10g})) / 1000)")
    AFD = f"(({BF} * 1000 + {k['ff'] - k['mfull'] * G * k['sin']:.10g}) / {k['meq'] + k['mfull']:.10g})"
    AE = f"(({BF} * 1000 + {k['ff']:.10g}) / {k['meq']})"
    SFD = (f"np.where({AFD} > 0.02, {k['vr']} * df['LAST_STOP_DELAY_S'] + {k['vr'] ** 2 / 2:.10g} / np.maximum({AFD}, 0.02), 9.99)")
    SE = f"({k['vr']} * df['LAST_STOP_DELAY_S'] + {k['vr'] ** 2 / 2:.10g} / np.maximum({AE}, 0.02))"
    OE = f"(df['AMBIENT_TEMP_C'] + {k['k0']} + {k['k1']} * np.maximum(df['MOTOR_POWER_AVG_KW'], 0))"
    return dict(k=k, X=X, LOAD=LOAD, NL=NL, DRAG=DRAG, HL=HL, HR=HR, CE=CE, BF=BF, AFD=AFD, AE=AE, SFD=SFD, SE=SE, OE=OE)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("LOAD_POWER_KW", p["LOAD"]),
        ("POWER_EXPECTED_KW", f"{k['pnl']:.10g} * df['STEP_SPEED_MS'] / {k['vr']} + {p['LOAD']}"),
        ("POWER_RESIDUAL_KW", f"df['MOTOR_POWER_KW'] - ({k['pnl']:.10g} * df['STEP_SPEED_MS'] / {k['vr']} + {p['LOAD']})"),
        ("NOLOAD_POWER_EST_KW", p["NL"]),
        ("DRAG_RATIO", p["DRAG"]),
        ("ENERGY_PER_PAX_WH", "df['MOTOR_POWER_KW'] * 1000 / 60 / np.maximum(df['PASSENGERS_PER_MIN'], 1)"),
        ("HANDRAIL_L_DEV_PCT", p["HL"]),
        ("HANDRAIL_R_DEV_PCT", p["HR"]),
        ("CHAIN_ELONG_EXPECTED_PCT", p["CE"]),
        ("CHAIN_WEAR_RESIDUAL_PCT", f"df['CHAIN_ELONGATION_PCT'] - {p['CE']}"),
        ("CHAIN_HOURS_TO_LIMIT", f"({k['erep']} - df['CHAIN_ELONGATION_PCT']) / {k['w']} * 1000"),
        ("BRAKE_FORCE_KN", p["BF"]),
        ("STOP_DIST_FULL_DOWN_M", p["SFD"]),
        ("STOP_DIST_EMPTY_M", p["SE"]),
        ("STOP_DIST_MODEL_ERR_M", "df['LAST_STOP_DISTANCE_M'] - (df['LAST_STOP_SPEED_MS'] * df['LAST_STOP_DELAY_S']"
                                  " + df['LAST_STOP_SPEED_MS'] ** 2 / 2 / np.maximum(df['LAST_STOP_DECEL_MS2'], 0.02))"),
        ("OIL_TEMP_EXPECTED_C", p["OE"]),
        ("OIL_TEMP_RESIDUAL_C", f"df['GEAR_OIL_TEMP_C'] - {p['OE']}"),
        ("VIB_RATIO", f"df['GEARBOX_VIB_MMS'] / {k['vib0']}"),
        ("SAFETY_TRIPS_24H", "df['TRIPS_COMB_24H'] + df['TRIPS_HANDRAIL_INLET_24H'] + df['TRIPS_STEP_SAG_24H'] + df['TRIPS_ESTOP_24H']"),
        ("STANDBY_LOST_KWH_DAY", f"np.maximum({k['fexp']} - df['STANDBY_SHARE_24H'], 0) * {k['duty'] * k['pnl'] * (1 - k['vsb'] / k['vr']):.10g}"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    x = r["passengers_per_min"] / 60 * float(f"{k['m'] * G * k['H'] / 1000:.10g}")
    load = x / k["eta"] if r["direction"] > 0 else -x * k["eta"]
    pnl = float(f"{k['pnl']:.10g}")
    v = max(r["step_speed_ms"], 0.05)
    nl = (r["motor_power_kw"] - load) * k["vr"] / v
    exp_p = pnl * r["step_speed_ms"] / k["vr"] + load
    hl = (r["handrail_left_ms"] / v - 1) * 100
    hr = (r["handrail_right_ms"] / v - 1) * 100
    ce = k["e0"] + k["w"] * r["run_hours"] / 1000
    ff = float(f"{k['ff']:.10g}")
    gs = float(f"{G * k['sin']:.10g}")
    bf = ((k["meq"] + r["last_stop_load_kg"]) * r["last_stop_decel_ms2"] - ff - r["last_stop_dir"] * r["last_stop_load_kg"] * gs) / 1000
    afd = (bf * 1000 + float(f"{k['ff'] - k['mfull'] * G * k['sin']:.10g}")) / float(f"{k['meq'] + k['mfull']:.10g}")
    ae = (bf * 1000 + ff) / k["meq"]
    h2 = float(f"{k['vr'] ** 2 / 2:.10g}")
    sfd = k["vr"] * r["last_stop_delay_s"] + h2 / max(afd, 0.02) if afd > 0.02 else 9.99
    se = k["vr"] * r["last_stop_delay_s"] + h2 / max(ae, 0.02)
    vs = r["last_stop_speed_ms"]
    oe = r["ambient_temp_c"] + k["k0"] + k["k1"] * max(r["motor_power_avg_kw"], 0)
    return {
        "load_power_kw": load, "power_expected_kw": exp_p, "power_residual_kw": r["motor_power_kw"] - exp_p,
        "noload_power_est_kw": nl, "drag_ratio": nl / pnl,
        "energy_per_pax_wh": r["motor_power_kw"] * 1000 / 60 / max(r["passengers_per_min"], 1),
        "handrail_l_dev_pct": hl, "handrail_r_dev_pct": hr,
        "chain_elong_expected_pct": ce, "chain_wear_residual_pct": r["chain_elongation_pct"] - ce,
        "chain_hours_to_limit": (k["erep"] - r["chain_elongation_pct"]) / k["w"] * 1000,
        "brake_force_kn": bf, "stop_dist_full_down_m": sfd, "stop_dist_empty_m": se,
        "stop_dist_model_err_m": r["last_stop_distance_m"] - (vs * r["last_stop_delay_s"] + vs ** 2 / 2 / max(r["last_stop_decel_ms2"], 0.02)),
        "oil_temp_expected_c": oe, "oil_temp_residual_c": r["gear_oil_temp_c"] - oe, "vib_ratio": r["gearbox_vib_mms"] / k["vib0"],
        "safety_trips_24h": r["trips_comb_24h"] + r["trips_handrail_inlet_24h"] + r["trips_step_sag_24h"] + r["trips_estop_24h"],
        "standby_lost_kwh_day": max(k["fexp"] - r["standby_share_24h"], 0) * float(f"{k['duty'] * k['pnl'] * (1 - k['vsb'] / k['vr']):.10g}"),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    HMIN, HMAX = f"np.minimum({p['HL']}, {p['HR']})", f"np.maximum({p['HL']}, {p['HR']})"
    CW = f"(df['CHAIN_ELONGATION_PCT'] - {p['CE']})"
    m = L["stop_margin_frac"] * k["smax"]
    return [
        ("ESC_STOP_TOO_LONG", f"{p['SFD']} > {k['smax']}", "Critical", "brake_weak"),
        ("ESC_STOP_HARSH", f"{p['SE']} < {k['smin']}", "High", "brake_harsh"),
        ("ESC_HANDRAIL_SLIP", f"{HMIN} < {L['handrail_slip_pct']}", "High", "handrail_slip"),
        ("ESC_CHAIN_ELONG_LIMIT", f"df['CHAIN_ELONGATION_PCT'] > {L['chain_replace_pct']}", "High", "chain_wear"),
        ("ESC_STOP_MARGIN_LOW", f"({p['SFD']} > {m:.6g}) & ({p['SFD']} <= {k['smax']})", "Medium", "brake_weak"),
        ("ESC_HANDRAIL_OUT_OF_TOL", f"(({HMIN} < {k['hmin']}) | ({HMAX} > {k['hmax']})) & ({HMIN} >= {L['handrail_slip_pct']})", "Medium", "handrail_slip"),
        ("ESC_CHAIN_ELONG_ALERT", f"(df['CHAIN_ELONGATION_PCT'] > {L['chain_alert_pct']}) & (df['CHAIN_ELONGATION_PCT'] <= {L['chain_replace_pct']})", "Medium", "chain_wear"),
        ("ESC_CHAIN_WEAR_FAST", f"{CW} > {L['chain_fast_wear_pct']}", "Medium", "chain_wear"),
        ("ESC_DRAG_HIGH", f"{p['DRAG']} > {L['drag_ratio_alert']}", "Medium", "step_band_drag"),
        ("ESC_STEP_SAG_TRIPS", f"df['TRIPS_STEP_SAG_24H'] >= {L['step_sag_trips_alert']}", "Medium", "step_band_drag"),
        ("ESC_GEAR_OIL_HOT", f"(df['GEAR_OIL_TEMP_C'] - {p['OE']}) > {L['oil_residual_alert_k']}", "Medium", "gearbox_wear"),
        ("ESC_GEAR_VIB_HIGH", f"df['GEARBOX_VIB_MMS'] / {k['vib0']} > {L['vib_ratio_alert']}", "Medium", "gearbox_wear"),
        ("ESC_COMB_TRIPS", f"df['TRIPS_COMB_24H'] >= {L['comb_trips_alert']}", "Medium", "comb_damage"),
        ("ESC_STANDBY_UNUSED", f"df['STANDBY_SHARE_24H'] < {L['standby_share_alert']}", "Low", "standby_disabled"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    sfd, se = t["stop_dist_full_down_m"], t["stop_dist_empty_m"]
    hmin, hmax = min(t["handrail_l_dev_pct"], t["handrail_r_dev_pct"]), max(t["handrail_l_dev_pct"], t["handrail_r_dev_pct"])
    e, cw = r["chain_elongation_pct"], t["chain_wear_residual_pct"]
    m = float(f"{L['stop_margin_frac'] * k['smax']:.6g}")
    add(sfd > k["smax"], "ESC_STOP_TOO_LONG", "Critical",
        f"Fully loaded down stop would take {sfd:.2f} m, beyond the EN 115-1 maximum of {k['smax']:.2f} m", "brake", "brake_weak")
    add(se < k["smin"], "ESC_STOP_HARSH", "High",
        f"Empty stop only {se:.2f} m, shorter than the EN 115-1 minimum of {k['smin']:.2f} m: risk of passenger falls", "brake", "brake_harsh")
    add(hmin < L["handrail_slip_pct"], "ESC_HANDRAIL_SLIP", "High",
        f"Handrail {hmin:+.1f} % against the steps: close to the monitor trip at -{twin['design']['handrail']['monitor_trip_pct']:.0f} %", "handrail", "handrail_slip")
    add(e > L["chain_replace_pct"], "ESC_CHAIN_ELONG_LIMIT", "High", f"Step chain elongation {e:.2f} %, beyond the {L['chain_replace_pct']} % replacement limit",
        "step chain", "chain_wear")
    add(m < sfd <= k["smax"], "ESC_STOP_MARGIN_LOW", "Medium", f"Fully loaded down stop would take {sfd:.2f} m (limit {k['smax']:.2f} m)", "brake", "brake_weak")
    add((hmin < k["hmin"] or hmax > k["hmax"]) and hmin >= L["handrail_slip_pct"], "ESC_HANDRAIL_OUT_OF_TOL", "Medium",
        f"Handrail speed {hmin:+.1f} / {hmax:+.1f} % against the steps, outside 0 to +2 %", "handrail", "handrail_slip")
    add(L["chain_alert_pct"] < e <= L["chain_replace_pct"], "ESC_CHAIN_ELONG_ALERT", "Medium", f"Step chain elongation {e:.2f} %: plan the replacement",
        "step chain", "chain_wear")
    add(cw > L["chain_fast_wear_pct"], "ESC_CHAIN_WEAR_FAST", "Medium", f"Chain {cw:+.2f} % longer than the wear line for {r['run_hours']:.0f} run hours: check lubrication",
        "step chain", "chain_wear")
    add(t["drag_ratio"] > L["drag_ratio_alert"], "ESC_DRAG_HIGH", "Medium", f"No-load power {t['noload_power_est_kw']:.1f} kW, {t['drag_ratio']:.2f} x expected",
        "step band", "step_band_drag")
    add(r["trips_step_sag_24h"] >= L["step_sag_trips_alert"], "ESC_STEP_SAG_TRIPS", "Medium", f"{r['trips_step_sag_24h']:.0f} step sag trips in 24 h",
        "step band", "step_band_drag")
    add(t["oil_temp_residual_c"] > L["oil_residual_alert_k"], "ESC_GEAR_OIL_HOT", "Medium",
        f"Gear oil {r['gear_oil_temp_c']:.0f} °C, {t['oil_temp_residual_c']:+.0f} K above what the power explains", "gearbox", "gearbox_wear")
    add(t["vib_ratio"] > L["vib_ratio_alert"], "ESC_GEAR_VIB_HIGH", "Medium", f"Gearbox vibration {r['gearbox_vib_mms']:.1f} mm/s, {t['vib_ratio']:.1f} x baseline",
        "gearbox", "gearbox_wear")
    add(r["trips_comb_24h"] >= L["comb_trips_alert"], "ESC_COMB_TRIPS", "Medium", f"{r['trips_comb_24h']:.0f} comb plate trips in 24 h", "comb plate", "comb_damage")
    add(r["standby_share_24h"] < L["standby_share_alert"], "ESC_STANDBY_UNUSED", "Low",
        f"Stand-by speed used {r['standby_share_24h'] * 100:.0f} % of the time: about {t['standby_lost_kwh_day']:.0f} kWh/day lost", "controller", "standby_disabled")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
