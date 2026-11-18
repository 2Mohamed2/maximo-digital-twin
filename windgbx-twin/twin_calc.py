"""The wind turbine drivetrain twin's expectations (WTG-3001, Vestas V90-2.0 MW).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Power (IEC 61400-12-1 air density normalisation, pitch-regulated turbine):
    rho  = B x 100 / (R0 x (T + 273.15))          B in hPa, T in C, R0 = 287.05 J/(kg K)
    Vn   = V x (rho / rho0)^(1/3)                  rho0 = 1.225 kg/m3, the density of the published power curve
    P_expected = power curve interpolated at Vn;  residual = P - P_expected;  ratio = P / max(P_expected, 50 kW)
Temperatures (load-and-ambient models, L = P / rated power):
    oil expected      = T_ambient + a0 + a1 L
    HSS bearing exp.  = T_oil (measured) + b0 + b1 L      a bearing fault raises this residual; a cooler fault does not
    main bearing exp. = T_ambient + m0 + m1 L
Vibration (CMS band values against a load-dependent baseline, ratio = measured / (c0 + c1 L)):
    planetary mesh frequency = Z_ring x rotor speed / 60 (ring fixed, carrier on the rotor)
    HSS bearing outer-race defect frequency BPFO = n/2 x (1 - d/D cos phi) x generator speed / 60
Oil (ISO 4406): scale number R = ceil(log2(102.4 x N)), N = particles per mL >= 4, 6 or 14 um(c): code R covers more than
    10 x 2^(R-11) and up to 10 x 2^(R-10) per mL (code 10: 5 to 10, code 14: 80 to 160); the printed table rounds above code 16.
Yaw: estimated power loss = 1 - cos(yaw error)^3 (the cube law; measured exponents in the literature are often lower).
"""
import math


def _k(twin):
    d = twin["design"]
    ro, pc, de, dt, hb, th, vb, oil = (d["rotor"], d["power_curve"], d["density"], d["drivetrain"], d["hss_bearing"],
                                       d["thermal"], d["vibration"], d["oil"])
    ratio = (1 + dt["z_ring"] / dt["z_sun"]) * dt["z_wheel2"] / dt["z_pinion2"] * dt["z_wheel3"] / dt["z_pinion3"]
    bpfo = hb["rollers"] / 2 * (1 - hb["roller_d_mm"] / hb["pitch_d_mm"] * math.cos(math.radians(hb["contact_deg"])))
    return dict(rated=ro["rated_kw"], ws=pc["wind_ms"], kw=pc["power_kw"], rho0=pc["rho_ref"], R0=de["R0"], ratio=ratio,
                zr=dt["z_ring"], bpfo=bpfo, a0=th["oil_a0"], a1=th["oil_a1"], b0=th["hss_b0"], b1=th["hss_b1"],
                m0=th["mb_m0"], m1=th["mb_m1"], p0=vb["planet0"], p1=vb["planet1"], e0=vb["hssenv0"], e1=vb["hssenv1"],
                q0=vb["mbenv0"], q1=vb["mbenv1"], g0=vb["gbxrms0"], g1=vb["gbxrms1"],
                iso6=oil["iso_target"][1], iso14=oil["iso_target"][2], fe=oil["fe_limit_24h"], oilmax=oil["oil_max_c"])


def interp(x, xp, fp):
    """np.interp(x, xp, fp, left=0, right=0) for one value, in plain Python."""
    if x < xp[0] or x > xp[-1]:
        return 0.0
    for i in range(len(xp) - 1):
        if x <= xp[i + 1]:
            return fp[i] + (x - xp[i]) * (fp[i + 1] - fp[i]) / (xp[i + 1] - xp[i])
    return fp[-1]


def iso_code(n):
    return float(math.ceil(math.log2(max(n * 102.4, 1))))


def _parts(twin):
    k = _k(twin)
    RHO = f"(df['AMBIENT_PRESSURE_HPA'] * 100 / ({k['R0']} * (df['AMBIENT_TEMP_C'] + 273.15)))"
    VN = f"(df['WIND_SPEED_MS'] * ({RHO} / {k['rho0']}) ** (1 / 3))"
    PE = f"np.interp({VN}, {k['ws']}, {k['kw']}, left=0, right=0)"
    LD = f"(df['ACTIVE_POWER_KW'] / {k['rated']})"
    OE = f"(df['AMBIENT_TEMP_C'] + {k['a0']} + {k['a1']} * {LD})"
    HE = f"(df['GBX_OIL_TEMP_C'] + {k['b0']} + {k['b1']} * {LD})"
    ME = f"(df['AMBIENT_TEMP_C'] + {k['m0']} + {k['m1']} * {LD})"
    ISO = lambda c: f"np.ceil(np.log2(np.maximum(df['{c}'] * 102.4, 1)))"
    VP = f"(df['VIB_PLANET_MESH'] / ({k['p0']} + {k['p1']} * {LD}))"
    VH = f"(df['VIB_HSS_BRG_ENV'] / ({k['e0']} + {k['e1']} * {LD}))"
    VM = f"(df['VIB_MB_ENV'] / ({k['q0']} + {k['q1']} * {LD}))"
    PR = f"(df['ACTIVE_POWER_KW'] / np.maximum({PE}, 50))"
    return dict(k=k, RHO=RHO, VN=VN, PE=PE, LD=LD, OE=OE, HE=HE, ME=ME, ISO=ISO, VP=VP, VH=VH, VM=VM, PR=PR)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("AIR_DENSITY", p["RHO"]),
        ("WIND_NORM_MS", p["VN"]),
        ("POWER_EXPECTED_KW", p["PE"]),
        ("POWER_RESIDUAL_KW", f"df['ACTIVE_POWER_KW'] - {p['PE']}"),
        ("POWER_RATIO", p["PR"]),
        ("GBX_OIL_EXPECTED_C", p["OE"]),
        ("GBX_OIL_RESIDUAL_C", f"df['GBX_OIL_TEMP_C'] - {p['OE']}"),
        ("HSS_BRG_EXPECTED_C", p["HE"]),
        ("HSS_BRG_RESIDUAL_C", f"df['GBX_HSS_BRG_TEMP_C'] - {p['HE']}"),
        ("MAIN_BRG_EXPECTED_C", p["ME"]),
        ("MAIN_BRG_RESIDUAL_C", f"df['MAIN_BRG_TEMP_C'] - {p['ME']}"),
        ("ISO4406_4UM", p["ISO"]("PC_4UM_PER_ML")),
        ("ISO4406_6UM", p["ISO"]("PC_6UM_PER_ML")),
        ("ISO4406_14UM", p["ISO"]("PC_14UM_PER_ML")),
        ("PLANET_MESH_HZ", f"{k['zr']} * df['ROTOR_RPM'] / 60"),
        ("HSS_BPFO_HZ", f"{k['bpfo']:.6g} * df['GEN_RPM'] / 60"),
        ("VIB_PLANET_RATIO", p["VP"]),
        ("VIB_HSS_BRG_RATIO", p["VH"]),
        ("VIB_MB_RATIO", p["VM"]),
        ("YAW_LOSS_PCT", "(1 - np.cos(np.radians(df['YAW_ERROR_DEG'])) ** 3) * 100"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    rho = r["ambient_pressure_hpa"] * 100 / (k["R0"] * (r["ambient_temp_c"] + 273.15))
    vn = r["wind_speed_ms"] * (rho / k["rho0"]) ** (1 / 3)
    pe = interp(vn, k["ws"], k["kw"])
    ld = r["active_power_kw"] / k["rated"]
    oe = r["ambient_temp_c"] + k["a0"] + k["a1"] * ld
    he = r["gbx_oil_temp_c"] + k["b0"] + k["b1"] * ld
    me = r["ambient_temp_c"] + k["m0"] + k["m1"] * ld
    return {
        "air_density": rho, "wind_norm_ms": vn, "power_expected_kw": pe, "power_residual_kw": r["active_power_kw"] - pe,
        "power_ratio": r["active_power_kw"] / max(pe, 50),
        "gbx_oil_expected_c": oe, "gbx_oil_residual_c": r["gbx_oil_temp_c"] - oe,
        "hss_brg_expected_c": he, "hss_brg_residual_c": r["gbx_hss_brg_temp_c"] - he,
        "main_brg_expected_c": me, "main_brg_residual_c": r["main_brg_temp_c"] - me,
        "iso4406_4um": iso_code(r["pc_4um_per_ml"]), "iso4406_6um": iso_code(r["pc_6um_per_ml"]), "iso4406_14um": iso_code(r["pc_14um_per_ml"]),
        "planet_mesh_hz": k["zr"] * r["rotor_rpm"] / 60, "hss_bpfo_hz": float(f"{k['bpfo']:.6g}") * r["gen_rpm"] / 60,
        "vib_planet_ratio": r["vib_planet_mesh"] / (k["p0"] + k["p1"] * ld),
        "vib_hss_brg_ratio": r["vib_hss_brg_env"] / (k["e0"] + k["e1"] * ld),
        "vib_mb_ratio": r["vib_mb_env"] / (k["q0"] + k["q1"] * ld),
        "yaw_loss_pct": (1 - math.cos(math.radians(r["yaw_error_deg"])) ** 3) * 100,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    RUN = "(df['TURBINE_STATE'] > 0.5)"
    return [
        ("GBX_OIL_TEMP_HIGH", f"{RUN} & (df['GBX_OIL_TEMP_C'] > {k['oilmax']})", "High", "oil_cooler_fouling"),
        ("GBX_HSS_BRG_VIB", f"{RUN} & ({p['VH']} > {L['hss_env_ratio']})", "High", "hss_bearing_damage"),
        ("GBX_FERROUS_PARTICLES", f"df['FE_PARTICLES_24H'] > {k['fe']}", "High", "hss_bearing_damage"),
        ("GBX_VIB_OVERALL", f"{RUN} & (df['VIB_GBX_RMS_MMS'] > {L['gbx_rms_mms']})", "High", "planet_gear_pitting"),
        ("MB_VIB_ENV", f"{RUN} & ({p['VM']} > {L['mb_env_ratio']})", "High", "main_bearing_wear"),
        ("GBX_HSS_BRG_TEMP", f"{RUN} & ((df['GBX_HSS_BRG_TEMP_C'] - {p['HE']}) > {L['hss_residual_c']})", "Medium", "hss_bearing_damage"),
        ("GBX_OIL_TEMP_RESIDUAL", f"{RUN} & ((df['GBX_OIL_TEMP_C'] - {p['OE']}) > {L['oil_residual_c']})", "Medium", "oil_cooler_fouling"),
        ("GBX_PLANET_MESH_VIB", f"{RUN} & ({p['VP']} > {L['planet_ratio']})", "Medium", "planet_gear_pitting"),
        ("OIL_CLEANLINESS", f"({p['ISO']('PC_6UM_PER_ML')} > {k['iso6']}) | ({p['ISO']('PC_14UM_PER_ML')} > {k['iso14']})", "Medium", "oil_contamination"),
        ("MB_TEMP_RESIDUAL", f"{RUN} & ((df['MAIN_BRG_TEMP_C'] - {p['ME']}) > {L['mb_residual_c']})", "Medium", "main_bearing_wear"),
        ("WTG_YAW_MISALIGNMENT", f"{RUN} & (np.abs(df['YAW_ERROR_DEG']) > {L['yaw_alert_deg']})", "Medium", "yaw_misalignment"),
        ("WTG_UNDERPERFORMANCE", f"{RUN} & ({p['VN']} >= {L['underperf_vmin_ms']}) & ({p['VN']} <= {L['underperf_vmax_ms']}) & ({p['PR']} < {L['underperf_ratio']})",
         "Medium", "rotor_performance_loss"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    run = r["turbine_state"] > 0.5
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    add(run and r["gbx_oil_temp_c"] > k["oilmax"], "GBX_OIL_TEMP_HIGH", "High",
        f"Gearbox oil {r['gbx_oil_temp_c']:.1f} °C, above the {k['oilmax']:.0f} °C limit", "cooling", "oil_cooler_fouling")
    add(run and t["vib_hss_brg_ratio"] > L["hss_env_ratio"], "GBX_HSS_BRG_VIB", "High",
        f"Envelope at the HSS bearing outer-race frequency ({t['hss_bpfo_hz']:.0f} Hz) {t['vib_hss_brg_ratio']:.1f} × baseline", "gearbox", "hss_bearing_damage")
    add(r["fe_particles_24h"] > k["fe"], "GBX_FERROUS_PARTICLES", "High",
        f"{r['fe_particles_24h']:.0f} ferrous wear particles in 24 h (limit {k['fe']})", "gearbox", "hss_bearing_damage")
    add(run and r["vib_gbx_rms_mms"] > L["gbx_rms_mms"], "GBX_VIB_OVERALL", "High",
        f"Gearbox overall vibration {r['vib_gbx_rms_mms']:.1f} mm/s rms, above {L['gbx_rms_mms']}", "gearbox", "planet_gear_pitting")
    add(run and t["vib_mb_ratio"] > L["mb_env_ratio"], "MB_VIB_ENV", "High",
        f"Main bearing envelope {t['vib_mb_ratio']:.1f} × baseline", "main bearing", "main_bearing_wear")
    add(run and t["hss_brg_residual_c"] > L["hss_residual_c"], "GBX_HSS_BRG_TEMP", "Medium",
        f"HSS bearing {t['hss_brg_residual_c']:+.1f} K above oil + load model", "gearbox", "hss_bearing_damage")
    add(run and t["gbx_oil_residual_c"] > L["oil_residual_c"], "GBX_OIL_TEMP_RESIDUAL", "Medium",
        f"Gearbox oil {t['gbx_oil_residual_c']:+.1f} K above ambient + load model", "cooling", "oil_cooler_fouling")
    add(run and t["vib_planet_ratio"] > L["planet_ratio"], "GBX_PLANET_MESH_VIB", "Medium",
        f"Planetary mesh band ({t['planet_mesh_hz']:.1f} Hz) {t['vib_planet_ratio']:.1f} × baseline", "gearbox", "planet_gear_pitting")
    add(t["iso4406_6um"] > k["iso6"] or t["iso4406_14um"] > k["iso14"], "OIL_CLEANLINESS", "Medium",
        f"Oil cleanliness {t['iso4406_4um']:.0f}/{t['iso4406_6um']:.0f}/{t['iso4406_14um']:.0f}, target -/{k['iso6']}/{k['iso14']}", "lubrication", "oil_contamination")
    add(run and t["main_brg_residual_c"] > L["mb_residual_c"], "MB_TEMP_RESIDUAL", "Medium",
        f"Main bearing {t['main_brg_residual_c']:+.1f} K above ambient + load model", "main bearing", "main_bearing_wear")
    add(run and abs(r["yaw_error_deg"]) > L["yaw_alert_deg"], "WTG_YAW_MISALIGNMENT", "Medium",
        f"Yaw error {r['yaw_error_deg']:+.1f}° (about {t['yaw_loss_pct']:.0f} % power lost)", "yaw", "yaw_misalignment")
    add(run and L["underperf_vmin_ms"] <= t["wind_norm_ms"] <= L["underperf_vmax_ms"] and t["power_ratio"] < L["underperf_ratio"],
        "WTG_UNDERPERFORMANCE", "Medium",
        f"Power {r['active_power_kw']:.0f} kW is {t['power_ratio'] * 100:.0f} % of the {t['power_expected_kw']:.0f} kW expected at {t['wind_norm_ms']:.1f} m/s (normalised)",
        "rotor", "rotor_performance_loss")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
