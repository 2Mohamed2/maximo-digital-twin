"""The SAG mill twin's expectations (ML-3901, SAG mill of an SABC circuit, ring gear drive, trunnion bearings).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Liners (wear assumed linear with tonnage since the last reline):
    expected thickness  t = t_new - r x kt,  r = (t_new - t_min) / planned life (kt)
    diameter inside the liners  D = D_shell - 2 t
    measured wear rate from the last laser scan = (t_new - t_scan) / kt_scan; wear ratio = measured / planned rate
    tonnes left = (t_scan - t_min) / measured rate - (kt - kt_scan);  days left = tonnes left / (feed rate x 24)
Charge from the bearing pressures (hydrostatic lift pockets carry the whole rotating mass):
    M_total = (p_FE + p_DE) x 1e5 x A_eff / g / 1000 (t);  M_charge = M_total - (M_empty + M_liner,new x t / t_new)
    M_charge / V = (1 - eps)(Jb rho_b + (J - Jb) rho_s) + eps J rho_p   ->  solved for the total filling J
    with V = pi/4 D^2 L and rho_p = 1 / (wc / rho_s + 1 - wc), the pulp that fills the voids.
Power (Austin 1990, as written by Doll 2013; power at the mill shell, +5 % for the cone ends, / 0.931 to the motor):
    P = K D^2.5 L (1 - A J) [(1 - eps)(rho_s / wc) J + 0.6 Jb (rho_b - rho_s / wc)] phi (1 - 0.1 / 2^(9 - 10 phi))
    phi = speed / n_c,  n_c = 42.3 / sqrt(D) rpm
Specific energy against ore hardness (Morrell SMC equation for the coarse part, feed P80 down to 750 um):
    Wa = K1 Mia 4 (750^f(750) - x1^f(x1)),  f(x) = -(0.295 + x / 1e6),  x1 = feed P80 in um
    measured specific energy = motor power / feed rate;  ratio = measured / (wa_share x Wa)
Overload: filling above about 35 % with the power below the model (the charge stops lifting: power falls as load rises).
"""
import math


def _k(twin):
    d = twin["design"]
    m, pm, li, ms, ch, o, b, g = (d["mill"], d["power_model"], d["liners"], d["mass"], d["charge"], d["ore"], d["bearings"], d["gear"])
    return dict(D=m["d_shell_m"], L=m["egl_m"], inst=m["installed_kw"], cone=m["cone_allowance"], cc=m["crit_const"],
                phi=m["speed_fraction_design"], K=pm["K"], A=pm["A"], eps=pm["eps"], wc=pm["wc"], rb=pm["rho_ball"], eta=pm["drive_eff"],
                tn=li["t_new_mm"], tmin=li["t_min_mm"], mln=li["mass_new_t"], life=li["plan_life_kt"],
                rate=(li["t_new_mm"] - li["t_min_mm"]) / li["plan_life_kt"], me=ms["empty_ex_liners_t"], aeff=ms["a_eff_m2"],
                ct=ms["a_eff_m2"] * 1e5 / 9.81 / 1000, j=ch["j_design"], jb=ch["jb_design"], jo=ch["j_overload"],
                mia=o["mia_design"], sg=o["sg_design"], f80=o["f80_mm_design"], K1=o["K1"], x2=o["x2_um"], share=o["wa_share"],
                oil=b["lube_supply_c"])


def fx(x):
    return -(0.295 + x / 1e6)


def wa(k, mia, f80_mm):
    """Morrell coarse-particle specific energy (kWh/t) from feed P80 (mm) to 750 um."""
    x1 = f80_mm * 1000
    return k["K1"] * mia * 4 * (k["x2"] ** fx(k["x2"]) - x1 ** fx(x1))


def austin_shell(k, D, J, Jb, sg, phi):
    """Austin (1990) power at the mill shell (kW), cylinder + cone allowance."""
    w = k["wc"]
    return ((1 + k["cone"]) * k["K"] * D ** 2.5 * k["L"] * (1 - k["A"] * J) * ((1 - k["eps"]) * (sg / w) * J + 0.6 * Jb * (k["rb"] - sg / w))
            * phi * (1 - 0.1 / 2 ** (9 - 10 * phi)))


def pulp_density(k, sg):
    return 1 / (k["wc"] / sg + 1 - k["wc"])


def filling(k, m_charge, D, Jb, sg):
    """Total filling J from the charge mass (t), the diameter inside the liners and the ball filling."""
    v = math.pi / 4 * D ** 2 * k["L"]
    e = k["eps"]
    return (m_charge / v - (1 - e) * Jb * (k["rb"] - sg)) / ((1 - e) * sg + e * pulp_density(k, sg))


def _parts(twin):
    k = _k(twin)
    e, w = k["eps"], k["wc"]
    TE = f"({k['tn']} - {k['rate']:.10g} * df['LINER_KT'])"
    D = f"({k['D']} - 2 * {TE} / 1000)"
    PHI = f"(df['MILL_SPEED_RPM'] * np.sqrt({D}) / {k['cc']})"
    MC = f"((df['BRG_FE_PRESSURE_BAR'] + df['BRG_DE_PRESSURE_BAR']) * {k['ct']:.10g} - ({k['me']} + {k['mln'] / k['tn']:.10g} * {TE}))"
    SG = "df['ORE_SG']"
    JB = "(df['BALL_CHARGE_PCT'] / 100)"
    RP = f"(1 / ({w} / {SG} + {1 - w:.10g}))"
    V = f"({math.pi / 4 * k['L']:.10g} * {D} ** 2)"
    J = f"(({MC} / {V} - {1 - e:.10g} * {JB} * ({k['rb']} - {SG})) / ({1 - e:.10g} * {SG} + {e} * {RP}))"
    PS = (f"({(1 + k['cone']) * k['K'] * k['L']:.10g} * {D} ** 2.5 * (1 - {k['A']} * {J}) * ({1 - e:.10g} * ({SG} / {w}) * {J}"
          f" + 0.6 * {JB} * ({k['rb']} - {SG} / {w})) * {PHI} * (1 - 0.1 / np.power(2, 9 - 10 * {PHI})))")
    PE = f"({PS} / {k['eta']})"
    X1 = "(df['FEED_F80_MM'] * 1000)"
    WA = f"({k['K1'] * 4:.10g} * df['ORE_MIA'] * ({k['x2'] ** fx(k['x2']):.10g} - np.power({X1}, -(0.295 + {X1} / 1000000))))"
    SE = "(df['MOTOR_POWER_KW'] / df['FEED_TPH'])"
    MR = f"(({k['tn']} - df['LINER_SCAN_MM']) / df['LINER_SCAN_KT'])"
    REM = f"((df['LINER_SCAN_MM'] - {k['tmin']}) / {MR} - (df['LINER_KT'] - df['LINER_SCAN_KT']))"
    RISE = "(np.maximum(df['BRG_FE_TEMP_C'], df['BRG_DE_TEMP_C']) - df['LUBE_OIL_TEMP_C'])"
    SPLIT = "((df['BRG_FE_PRESSURE_BAR'] - df['BRG_DE_PRESSURE_BAR']) / (df['BRG_FE_PRESSURE_BAR'] + df['BRG_DE_PRESSURE_BAR']))"
    return dict(k=k, TE=TE, D=D, PHI=PHI, MC=MC, J=J, PE=PE, WA=WA, SE=SE, MR=MR, REM=REM, RISE=RISE, SPLIT=SPLIT)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("LINER_EXPECTED_MM", p["TE"]),
        ("D_EFF_M", p["D"]),
        ("CRIT_SPEED_PCT", f"100 * {p['PHI']}"),
        ("CHARGE_MASS_T", p["MC"]),
        ("FILLING_PCT", f"100 * {p['J']}"),
        ("POWER_EXPECTED_KW", p["PE"]),
        ("POWER_RATIO", f"df['MOTOR_POWER_KW'] / {p['PE']}"),
        ("SE_KWH_T", p["SE"]),
        ("WA_KWH_T", p["WA"]),
        ("SE_RATIO", f"{p['SE']} / ({k['share']} * {p['WA']})"),
        ("THROUGHPUT_EXPECTED_TPH", f"df['MOTOR_POWER_KW'] / ({k['share']} * {p['WA']})"),
        ("LINER_WEAR_RATIO", f"{p['MR']} / {k['rate']:.10g}"),
        ("LINER_REMAINING_KT", p["REM"]),
        ("RELINE_DAYS", f"{p['REM']} * 1000 / (df['FEED_TPH'] * 24)"),
        ("BRG_SPLIT", p["SPLIT"]),
        ("BRG_RISE_MAX_K", p["RISE"]),
        ("GEAR_LOAD_RATIO", f"df['MOTOR_POWER_KW'] / {k['inst']}"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    te = k["tn"] - k["rate"] * r["liner_kt"]
    D = k["D"] - 2 * te / 1000
    phi = r["mill_speed_rpm"] * math.sqrt(D) / k["cc"]
    mc = (r["brg_fe_pressure_bar"] + r["brg_de_pressure_bar"]) * k["ct"] - (k["me"] + k["mln"] / k["tn"] * te)
    jb, sg = r["ball_charge_pct"] / 100, r["ore_sg"]
    J = filling(k, mc, D, jb, sg)
    pe = austin_shell(k, D, J, jb, sg, phi) / k["eta"]
    w = wa(k, r["ore_mia"], r["feed_f80_mm"])
    se = r["motor_power_kw"] / r["feed_tph"]
    mr = (k["tn"] - r["liner_scan_mm"]) / r["liner_scan_kt"]
    rem = (r["liner_scan_mm"] - k["tmin"]) / mr - (r["liner_kt"] - r["liner_scan_kt"])
    fe, de = r["brg_fe_pressure_bar"], r["brg_de_pressure_bar"]
    return {
        "liner_expected_mm": te, "d_eff_m": D, "crit_speed_pct": 100 * phi, "charge_mass_t": mc, "filling_pct": 100 * J,
        "power_expected_kw": pe, "power_ratio": r["motor_power_kw"] / pe, "se_kwh_t": se, "wa_kwh_t": w,
        "se_ratio": se / (k["share"] * w), "throughput_expected_tph": r["motor_power_kw"] / (k["share"] * w),
        "liner_wear_ratio": mr / k["rate"], "liner_remaining_kt": rem, "reline_days": rem * 1000 / (r["feed_tph"] * 24),
        "brg_split": (fe - de) / (fe + de), "brg_rise_max_k": max(r["brg_fe_temp_c"], r["brg_de_temp_c"]) - r["lube_oil_temp_c"],
        "gear_load_ratio": r["motor_power_kw"] / k["inst"],
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    JP, PR = f"(100 * {p['J']})", f"(df['MOTOR_POWER_KW'] / {p['PE']})"
    TMAX = "np.maximum(df['BRG_FE_TEMP_C'], df['BRG_DE_TEMP_C'])"
    return [
        ("SAG_POWER_DROP_LOADED", f"({JP} > {L['j_loaded_pct']}) & ({PR} < {L['power_ratio_low']})", "Critical", "charge_overload"),
        ("SAG_OVERLOAD_RISK", f"{JP} > {L['j_overload_pct']}", "High", "charge_overload"),
        ("SAG_RELINE_DUE", f"({p['REM']} * 1000 / (df['FEED_TPH'] * 24)) < {L['reline_days_alert']}", "High", "liner_wear_fast"),
        ("SAG_BRG_TEMP_HIGH", f"{TMAX} > {L['brg_temp_limit_c']}", "High", "bearing_lube"),
        ("SAG_PINION_VIB_HIGH", f"df['PINION_VIB_MM_S'] > {L['pinion_vib_limit']}", "High", "gear_misalignment"),
        ("SAG_GEAR_OVERPOWER", f"df['MOTOR_POWER_KW'] > {k['inst']}", "High", "ball_overcharge"),
        ("SAG_LINER_WEAR_FAST", f"({p['MR']} / {k['rate']:.10g}) > {L['liner_wear_ratio_high']}", "Medium", "liner_wear_fast"),
        ("SAG_SE_HIGH", f"({p['SE']} / ({k['share']} * {p['WA']})) > {L['se_ratio_high']}", "Medium", "lifter_profile_loss"),
        ("SAG_BRG_RISE_HIGH", f"({p['RISE']} > {L['brg_rise_alert_k']}) & ({TMAX} <= {L['brg_temp_limit_c']})", "Medium", "bearing_lube"),
        ("SAG_BRG_SPLIT", f"np.abs({p['SPLIT']}) > {L['brg_split_alert']}", "Medium", "pocket_leak"),
        ("SAG_GEAR_DT_HIGH", f"df['GEAR_DT_K'] > {L['gear_dt_alert_k']}", "Medium", "gear_misalignment"),
        ("SAG_PINION_VIB_ALERT", f"(df['PINION_VIB_MM_S'] > {L['pinion_vib_alert']}) & (df['PINION_VIB_MM_S'] <= {L['pinion_vib_limit']})", "Medium", "gear_misalignment"),
        ("SAG_BALL_CHARGE_HIGH", f"df['BALL_CHARGE_PCT'] > {L['ball_charge_high_pct']}", "Medium", "ball_overcharge"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    jp, pr = t["filling_pct"], t["power_ratio"]
    tmax = max(r["brg_fe_temp_c"], r["brg_de_temp_c"])
    v = r["pinion_vib_mm_s"]
    add(jp > L["j_loaded_pct"] and pr < L["power_ratio_low"], "SAG_POWER_DROP_LOADED", "Critical",
        f"Filling {jp:.1f} % and power only {pr:.2f} x the model: the mill is overloading, cut the feed", "charge", "charge_overload")
    add(jp > L["j_overload_pct"], "SAG_OVERLOAD_RISK", "High", f"Filling {jp:.1f} % from the bearing pressures, above {L['j_overload_pct']:.0f} %", "charge", "charge_overload")
    add(t["reline_days"] < L["reline_days_alert"], "SAG_RELINE_DUE", "High",
        f"Shell liners reach {k['tmin']:.0f} mm in {t['reline_days']:.0f} days at the current feed rate", "liners", "liner_wear_fast")
    add(tmax > L["brg_temp_limit_c"], "SAG_BRG_TEMP_HIGH", "High", f"Trunnion bearing at {tmax:.1f} °C, above {L['brg_temp_limit_c']:.0f} °C", "bearing", "bearing_lube")
    add(v > L["pinion_vib_limit"], "SAG_PINION_VIB_HIGH", "High", f"Pinion bearing vibration {v:.1f} mm/s, above {L['pinion_vib_limit']}", "gear", "gear_misalignment")
    add(r["motor_power_kw"] > k["inst"], "SAG_GEAR_OVERPOWER", "High",
        f"Motor power {r['motor_power_kw']:.0f} kW, above the {k['inst']:.0f} kW the gear set is rated for", "gear", "ball_overcharge")
    add(t["liner_wear_ratio"] > L["liner_wear_ratio_high"], "SAG_LINER_WEAR_FAST", "Medium",
        f"Last scan shows {t['liner_wear_ratio']:.2f} x the planned wear rate", "liners", "liner_wear_fast")
    add(t["se_ratio"] > L["se_ratio_high"], "SAG_SE_HIGH", "Medium",
        f"Specific energy {t['se_kwh_t']:.2f} kWh/t, {t['se_ratio']:.2f} x the SMC model for this ore", "liners", "lifter_profile_loss")
    add(t["brg_rise_max_k"] > L["brg_rise_alert_k"] and tmax <= L["brg_temp_limit_c"], "SAG_BRG_RISE_HIGH", "Medium",
        f"Bearing {t['brg_rise_max_k']:.1f} K above the oil supply", "bearing", "bearing_lube")
    add(abs(t["brg_split"]) > L["brg_split_alert"], "SAG_BRG_SPLIT", "Medium",
        f"Bearing pressures FE {r['brg_fe_pressure_bar']:.1f} / DE {r['brg_de_pressure_bar']:.1f} bar: split {t['brg_split']:+.2f}", "bearing", "pocket_leak")
    add(r["gear_dt_k"] > L["gear_dt_alert_k"], "SAG_GEAR_DT_HIGH", "Medium", f"Ring gear {r['gear_dt_k']:.1f} K hotter on one side of the face", "gear", "gear_misalignment")
    add(L["pinion_vib_alert"] < v <= L["pinion_vib_limit"], "SAG_PINION_VIB_ALERT", "Medium", f"Pinion bearing vibration {v:.1f} mm/s", "gear", "gear_misalignment")
    add(r["ball_charge_pct"] > L["ball_charge_high_pct"], "SAG_BALL_CHARGE_HIGH", "Medium",
        f"Ball filling {r['ball_charge_pct']:.1f} %, above {L['ball_charge_high_pct']:.0f} %", "charge", "ball_overcharge")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
