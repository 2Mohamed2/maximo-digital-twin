"""The machining centre main spindle twin's expectations (MC-4801, GMN HCS 230 - 20000/40 HSK-A63 motor spindle).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Expected spindle power for the cut the CNC reports (milling, Kienzle specific cutting force):
    vc  = pi x Dc x n / 1000                      m/min
    fz  = vf / (n x z)                            mm per tooth
    phi = arccos(1 - 2 ae / Dc)                   engagement angle (rad), side or face milling with the tool centred
    hm  = fz x (1 - cos phi) / phi = 2 fz ae / (Dc phi)       mean chip thickness over the arc (geometry)
    kc  = kc1.1 x hm^(-mc) x (1 - gamma0 / 100)  N/mm2 (Kienzle, with the usual rake angle correction)
    Pc  = ae x ap x vf x kc / (60 x 10^6)         kW (Sandvik Coromant milling formula); Q = ap ae vf / 1000 cm3/min
    P expected = in_cut x Pc / eta + P idle(n),   P idle = p0 + p1 (n/1000) + p2 (n/1000)^2 (air-cut test)
    power ratio = P measured / max(P expected, 0.5 kW): a worn tool needs more power for the same cut.
Available power (S1): min(P rated, T rated x 2 pi n / 60): constant torque up to the base speed, then constant power.
Torque from power (Sandvik): M = P x 30 x 10^3 / (pi n).
Temperatures and growth against the 5-minute mean speed and power (the edge keeps the means, so each reading stands alone):
    front bearing expected = T coolant in + f0 + f1 x n_mean/1000; rear the same with r0, r1
    motor expected         = T coolant in + m0 + m1 x P_mean
    Z growth expected      = g0 + g1 x n_mean/1000 (from the ISO 230-3 spindle thermal test)
Vibration:
    BPFO = Z/2 x (1 - Dw/dm cos alpha) x n/60;  envelope ratio = measured / (e0 + e1 n/n_max)
    1x ratio = measured 1x velocity / (v0 + v1 (n/10,000)^2)
Balance (ISO 21940-11, as commonly applied): U per = 9549 x G x m / n  (g mm, m in kg, n in rpm).
Clamping: force ratio = measured clamping force / nominal force of the HSK-A63 clamping set.
"""
import math


def _k(twin):
    d = twin["design"]
    sp, dr, ma, br, th, vb, cl, co = (d["spindle"], d["drive"], d["material"], d["bearing"], d["thermal"], d["vibration"],
                                      d["clamping"], d["cooling"])
    bpfo = br["balls"] / 2 * (1 - br["ball_d_mm"] / br["pitch_d_mm"] * math.cos(math.radians(br["contact_deg"])))
    bpfi = br["balls"] / 2 * (1 + br["ball_d_mm"] / br["pitch_d_mm"] * math.cos(math.radians(br["contact_deg"])))
    return dict(nmax=sp["n_max_rpm"], prated=sp["p_rated_kw"], tr=sp["t_rated_nm"], nbase=sp["n_base_rpm"],
                eta=dr["eta"], p0=dr["idle_p0_kw"], p1=dr["idle_p1_kw_per_krpm"], p2=dr["idle_p2_kw_per_krpm2"],
                kc1=ma["kc1_n_mm2"], mc=ma["mc"], bpfo=round(bpfo, 6), bpfi=round(bpfi, 6),
                f0=th["front_f0"], f1=th["front_f1"], r0=th["rear_r0"], r1=th["rear_r1"], m0=th["motor_m0"], m1=th["motor_m1"],
                g0=th["growth_g0_um"], g1=th["growth_g1_um"], e0=vb["env0_g"], e1=vb["env1_g"], v0=vb["v1x0_mms"], v1=vb["v1x1_mms"],
                clamp=cl["nominal_kn"], G=d["balance"]["grade_g"], flow=co["flow_nominal_lpm"])


def _parts(twin):
    k = _k(twin)
    N = "np.maximum(df['SPEED_RPM'], 1)"
    AE = "np.maximum(df['AE_MM'], 0.01)"
    PHI = f"np.arccos(np.clip(1 - 2 * {AE} / df['TOOL_DIAMETER_MM'], -1, 1))"
    FZ = f"(df['FEED_MM_MIN'] / ({N} * df['TOOL_TEETH']))"
    HM = f"np.maximum(2 * {FZ} * {AE} / (df['TOOL_DIAMETER_MM'] * {PHI}), 0.0001)"
    KC = f"({k['kc1']} * {HM} ** (-{k['mc']}) * (1 - df['TOOL_RAKE_DEG'] / 100))"
    PC = f"(df['AE_MM'] * df['AP_MM'] * df['FEED_MM_MIN'] * {KC} / 60000000)"
    PI = f"({k['p0']} + {k['p1']} * df['SPEED_RPM'] / 1000 + {k['p2']} * (df['SPEED_RPM'] / 1000) ** 2)"
    PE = f"(df['IN_CUT'] * {PC} / {k['eta']} + {PI})"
    PR = f"(df['POWER_KW'] / np.maximum({PE}, 0.5))"
    PA = f"np.minimum({k['prated']}, {k['tr']} * 2 * np.pi * df['SPEED_RPM'] / 60 / 1000)"
    FR = f"(df['FRONT_BRG_TEMP_C'] - (df['COOLANT_IN_C'] + {k['f0']} + {k['f1']} * df['SPEED_AVG_RPM'] / 1000))"
    RR = f"(df['REAR_BRG_TEMP_C'] - (df['COOLANT_IN_C'] + {k['r0']} + {k['r1']} * df['SPEED_AVG_RPM'] / 1000))"
    MR = f"(df['MOTOR_TEMP_C'] - (df['COOLANT_IN_C'] + {k['m0']} + {k['m1']} * df['POWER_AVG_KW']))"
    GR = f"(df['Z_GROWTH_UM'] - ({k['g0']} + {k['g1']} * df['SPEED_AVG_RPM'] / 1000))"
    ER = f"(df['VIB_ENV_G'] / ({k['e0']} + {k['e1']} * df['SPEED_RPM'] / {k['nmax']}))"
    VR = f"(df['VIB_1X_MMS'] / ({k['v0']} + {k['v1']} * (df['SPEED_RPM'] / 10000) ** 2))"
    return dict(k=k, N=N, FZ=FZ, HM=HM, KC=KC, PC=PC, PI=PI, PE=PE, PR=PR, PA=PA, FR=FR, RR=RR, MR=MR, GR=GR, ER=ER, VR=VR)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("CUT_SPEED_M_MIN", "np.pi * df['TOOL_DIAMETER_MM'] * df['SPEED_RPM'] / 1000"),
        ("FEED_PER_TOOTH_MM", p["FZ"]),
        ("CHIP_THICK_MEAN_MM", p["HM"]),
        ("KC_N_MM2", p["KC"]),
        ("MRR_CM3_MIN", "df['IN_CUT'] * df['AP_MM'] * df['AE_MM'] * df['FEED_MM_MIN'] / 1000"),
        ("CUT_POWER_KW", p["PC"]),
        ("IDLE_POWER_KW", p["PI"]),
        ("POWER_EXPECTED_KW", p["PE"]),
        ("POWER_RATIO", p["PR"]),
        ("POWER_AVAILABLE_KW", p["PA"]),
        ("SPINDLE_TORQUE_NM", f"df['POWER_KW'] * 30000 / (np.pi * {p['N']})"),
        ("FRONT_BRG_RESIDUAL_C", p["FR"]),
        ("REAR_BRG_RESIDUAL_C", p["RR"]),
        ("MOTOR_TEMP_RESIDUAL_C", p["MR"]),
        ("GROWTH_RESIDUAL_UM", p["GR"]),
        ("BPFO_HZ", f"{k['bpfo']} * df['SPEED_RPM'] / 60"),
        ("ENV_RATIO", p["ER"]),
        ("VIB_1X_RATIO", p["VR"]),
        ("UNBALANCE_PERMISSIBLE_GMM", f"9549 * {k['G']} * df['TOOL_MASS_KG'] / {p['N']}"),
        ("CLAMP_FORCE_RATIO", f"df['CLAMP_FORCE_KN'] / {k['clamp']}"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    n = max(r["speed_rpm"], 1)
    ae = max(r["ae_mm"], 0.01)
    dc = r["tool_diameter_mm"]
    phi = math.acos(min(1.0, max(-1.0, 1 - 2 * ae / dc)))
    fz = r["feed_mm_min"] / (n * r["tool_teeth"])
    hm = max(2 * fz * ae / (dc * phi), 0.0001)
    kc = k["kc1"] * hm ** (-k["mc"]) * (1 - r["tool_rake_deg"] / 100)
    pc = r["ae_mm"] * r["ap_mm"] * r["feed_mm_min"] * kc / 60000000
    pi_ = k["p0"] + k["p1"] * r["speed_rpm"] / 1000 + k["p2"] * (r["speed_rpm"] / 1000) ** 2
    pe = r["in_cut"] * pc / k["eta"] + pi_
    na = r["speed_avg_rpm"] / 1000
    return {
        "cut_speed_m_min": math.pi * dc * r["speed_rpm"] / 1000, "feed_per_tooth_mm": fz, "chip_thick_mean_mm": hm, "kc_n_mm2": kc,
        "mrr_cm3_min": r["in_cut"] * r["ap_mm"] * r["ae_mm"] * r["feed_mm_min"] / 1000, "cut_power_kw": pc, "idle_power_kw": pi_,
        "power_expected_kw": pe, "power_ratio": r["power_kw"] / max(pe, 0.5),
        "power_available_kw": min(k["prated"], k["tr"] * 2 * math.pi * r["speed_rpm"] / 60 / 1000),
        "spindle_torque_nm": r["power_kw"] * 30000 / (math.pi * n),
        "front_brg_residual_c": r["front_brg_temp_c"] - (r["coolant_in_c"] + k["f0"] + k["f1"] * na),
        "rear_brg_residual_c": r["rear_brg_temp_c"] - (r["coolant_in_c"] + k["r0"] + k["r1"] * na),
        "motor_temp_residual_c": r["motor_temp_c"] - (r["coolant_in_c"] + k["m0"] + k["m1"] * r["power_avg_kw"]),
        "growth_residual_um": r["z_growth_um"] - (k["g0"] + k["g1"] * na),
        "bpfo_hz": k["bpfo"] * r["speed_rpm"] / 60,
        "env_ratio": r["vib_env_g"] / (k["e0"] + k["e1"] * r["speed_rpm"] / k["nmax"]),
        "vib_1x_ratio": r["vib_1x_mms"] / (k["v0"] + k["v1"] * (r["speed_rpm"] / 10000) ** 2),
        "unbalance_permissible_gmm": 9549 * k["G"] * r["tool_mass_kg"] / n,
        "clamp_force_ratio": r["clamp_force_kn"] / k["clamp"],
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    RUN = f"(df['SPEED_RPM'] > {L['running_rpm']})"
    CR = f"(df['CLAMP_FORCE_KN'] / {k['clamp']})"
    return [
        ("SP_CRASH", f"df['SHOCK_MAX_G_24H'] > {L['crash_g']}", "Critical", "spindle_crash"),
        ("SP_CLAMP_FORCE_LOW", f"{CR} < {L['clamp_low_ratio']}", "High", "clamping_force_loss"),
        ("SP_BRG_ENV", f"{RUN} & ({p['ER']} > {L['env_ratio']})", "High", "bearing_damage"),
        ("SP_OILAIR_LOW", f"df['OILAIR_PRESSURE_BAR'] < {L['oilair_min_bar']}", "High", "lubrication_starvation"),
        ("SP_COOLING_FLOW_LOW", f"df['COOLANT_FLOW_LPM'] < {L['coolant_flow_min_lpm']}", "High", "cooling_failure"),
        ("SP_POWER_ABOVE_AVAILABLE", f"{RUN} & (df['POWER_KW'] > {p['PA']})", "High", None),
        ("SP_FRONT_BRG_TEMP", f"{p['FR']} > {L['front_residual_c']}", "Medium", "bearing_damage"),
        ("SP_REAR_BRG_TEMP", f"{p['RR']} > {L['rear_residual_c']}", "Medium", "lubrication_starvation"),
        ("SP_MOTOR_TEMP", f"{p['MR']} > {L['motor_residual_c']}", "Medium", "cooling_failure"),
        ("SP_THERMAL_GROWTH", f"{p['GR']} > {L['growth_residual_um']}", "Medium", "cooling_failure"),
        ("SP_IMBALANCE", f"{RUN} & ({p['VR']} > {L['v1x_ratio']})", "Medium", "tool_imbalance"),
        ("SP_CLAMP_FORCE_WARN", f"({CR} < {L['clamp_warn_ratio']}) & ({CR} >= {L['clamp_low_ratio']})", "Medium", "clamping_force_loss"),
        ("SP_TOOL_WEAR", f"{RUN} & (df['IN_CUT'] > 0.5) & ({p['PC']} >= {L['wear_min_cut_kw']}) & ({p['PR']} > {L['power_ratio_alert']})", "Medium", "tool_wear"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    run = r["speed_rpm"] > L["running_rpm"]
    cr = t["clamp_force_ratio"]
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    add(r["shock_max_g_24h"] > L["crash_g"], "SP_CRASH", "Critical",
        f"Shock of {r['shock_max_g_24h']:.0f} g at the spindle nose in the last 24 h (crash threshold {L['crash_g']:.0f} g)", "spindle", "spindle_crash")
    add(cr < L["clamp_low_ratio"], "SP_CLAMP_FORCE_LOW", "High",
        f"Clamping force {r['clamp_force_kn']:.1f} kN, {cr * 100:.0f} % of the {k['clamp']:.0f} kN nominal", "clamping", "clamping_force_loss")
    add(run and t["env_ratio"] > L["env_ratio"], "SP_BRG_ENV", "High",
        f"Envelope at the front bearing outer-race frequency ({t['bpfo_hz']:.0f} Hz) {t['env_ratio']:.1f} × baseline", "bearings", "bearing_damage")
    add(r["oilair_pressure_bar"] < L["oilair_min_bar"], "SP_OILAIR_LOW", "High",
        f"Oil-air pressure {r['oilair_pressure_bar']:.2f} bar, below {L['oilair_min_bar']} bar", "lubrication", "lubrication_starvation")
    add(r["coolant_flow_lpm"] < L["coolant_flow_min_lpm"], "SP_COOLING_FLOW_LOW", "High",
        f"Spindle cooling flow {r['coolant_flow_lpm']:.1f} L/min, below {L['coolant_flow_min_lpm']:.0f} L/min", "cooling", "cooling_failure")
    add(run and r["power_kw"] > t["power_available_kw"], "SP_POWER_ABOVE_AVAILABLE", "High",
        f"Spindle power {r['power_kw']:.1f} kW above the {t['power_available_kw']:.1f} kW available (S1) at {r['speed_rpm']:.0f} rpm", "spindle")
    add(t["front_brg_residual_c"] > L["front_residual_c"], "SP_FRONT_BRG_TEMP", "Medium",
        f"Front bearing {t['front_brg_residual_c']:+.1f} K above the speed model", "bearings", "bearing_damage")
    add(t["rear_brg_residual_c"] > L["rear_residual_c"], "SP_REAR_BRG_TEMP", "Medium",
        f"Rear bearing {t['rear_brg_residual_c']:+.1f} K above the speed model", "bearings", "lubrication_starvation")
    add(t["motor_temp_residual_c"] > L["motor_residual_c"], "SP_MOTOR_TEMP", "Medium",
        f"Motor winding {t['motor_temp_residual_c']:+.1f} K above the load model", "cooling", "cooling_failure")
    add(t["growth_residual_um"] > L["growth_residual_um"], "SP_THERMAL_GROWTH", "Medium",
        f"Spindle nose grew {t['growth_residual_um']:+.1f} µm more than the thermal model", "cooling", "cooling_failure")
    add(run and t["vib_1x_ratio"] > L["v1x_ratio"], "SP_IMBALANCE", "Medium",
        f"1x vibration {r['vib_1x_mms']:.2f} mm/s, {t['vib_1x_ratio']:.1f} × the balanced baseline (tool T{r['tool_number']:.0f})", "tool", "tool_imbalance")
    add(L["clamp_low_ratio"] <= cr < L["clamp_warn_ratio"], "SP_CLAMP_FORCE_WARN", "Medium",
        f"Clamping force {r['clamp_force_kn']:.1f} kN, {cr * 100:.0f} % of nominal", "clamping", "clamping_force_loss")
    add(run and r["in_cut"] > 0.5 and t["cut_power_kw"] >= L["wear_min_cut_kw"] and t["power_ratio"] > L["power_ratio_alert"], "SP_TOOL_WEAR", "Medium",
        f"Spindle power {r['power_kw']:.1f} kW is {t['power_ratio']:.2f} × the {t['power_expected_kw']:.1f} kW this cut needs (tool T{r['tool_number']:.0f})", "tool", "tool_wear")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
