"""The cement rotary kiln twin's expectations (KL-4201: 4.8 m x 74 m kiln, 5-stage preheater + calciner, grate cooler).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Specific heat consumption (SHC), measured two ways (kJ per kg clinker):
    from the fuel:  SHC_fuel = (fuel_kiln + fuel_calciner) [t/h] x LHV [MJ/kg] / clinker [t/h] x 1000
    from a heat balance on measured losses:
        SHC_bal = H_theor + preheater exit gas + shell + cooler exhaust air + clinker leaving the cooler + cooler wall + other
        preheater exit gas  = V_gas [Nm3/h] x cp_gas x (T_exit - T_amb) / clinker [kg/h]
        cooler exhaust air  = V_air [Nm3/h] x cp_air x (T_exh - T_amb) / clinker [kg/h]
        clinker out         = c_out x (T_clinker_out - T_amb)
        shell               = pi D L x q(T_mean) x 3.6 / clinker [t/h]          (q in kW/m2)
        q(T)                = eps sigma (T^4 - Ta^4) + h (T - Ta)                (Stefan-Boltzmann + convection, kelvin)
  The two must agree; when they do not, a meter is wrong (coal feeder, LHV, gas flow). SHC_fuel - design = excess.
Cooler efficiency (recuperation):
    eta = 1 - (cooler exhaust air + clinker out + cooler wall) / (c_in x (T_clinker_in - T_amb))
False air across the preheater (O2 balance, air at 21 % O2 mixing into the gas):
    false air % of the calciner gas = (O2_exit - O2_calciner) / (21 - O2_exit) x 100
Lining at the hottest shell point (one-dimensional conduction, brick + coating in series):
    equivalent lining = k_brick x (T_hot_face - T_shell_max) / q(T_shell_max)
Kiln drive: torque_expected = T_empty + (T_design - T_empty) x (output / output_design) x (speed_design / speed)
  (the material hold-up is output x residence time, and the residence time scales with 1 / speed); ratio = measured / expected.
Burning zone: NOx_expected = NOx_ref x exp(k (BZT - BZT_design)); ratio = NOx / NOx_expected.
  Burning zone cold: both fall together (ratio near 1). Pyrometer fouled: BZT falls alone (ratio far from 1).
Tyre 2: hot gap = migration / pi; expected hot gap = cold gap - alpha x D x (T_shell - T_tyre).
Stack NOx at the reference O2 (2010/75/EU Annex VI Part 7): E_ref = E_meas x (21 - 10) / (21 - O2_meas).
"""
import math

SB = 5.670e-8
C2K = 273.15


def _k(twin):
    d = twin["design"]
    kl, hb, sh, bz, gs, dr, ty, st = (d["kiln"], d["heat_balance"], d["shell"], d["burning_zone"], d["gas"], d["drive"],
                                      d["tyres"], d["stack"])
    area = math.pi * kl["diameter_m"] * kl["length_m"]
    return dict(D=kl["diameter_m"], area=area, cl_d=kl["clinker_design_tph"], n_d=kl["speed_design_rpm"],
                ht=hb["h_theor_kjkg"], oth=hb["other_losses_kjkg"], cw=hb["cooler_wall_kjkg"], cpg=hb["cp_gas_kj_nm3k"],
                cpa=hb["cp_air_kj_nm3k"], cout=hb["c_clinker_out_kj_kgk"], cin=hb["c_clinker_in_kj_kgk"], tin=hb["clinker_in_c"],
                shc_d=hb["shc_design_kjkg"], eps=sh["emissivity"], hc=sh["h_conv_w_m2k"], kb=sh["k_brick_w_mk"], thf=sh["hot_face_c"],
                bzt_d=bz["bzt_design_c"], nox_ref=bz["nox_ref_ppm"], knox=bz["nox_k_per_k"],
                t_d=dr["torque_design_pct"], t_e=dr["torque_empty_pct"], alpha=ty["alpha_per_k"], gap0=ty["cold_gap_mm"],
                o2ref=st["o2_reference_pct"])


def q_shell(k, ts, ta):
    """Heat flux from the shell to the surroundings, W/m2 (radiation + convection)."""
    return k["eps"] * SB * ((ts + C2K) ** 4 - (ta + C2K) ** 4) + k["hc"] * (ts - ta)


def lining_mm(k, ts, ta):
    return k["kb"] * (k["thf"] - ts) / q_shell(k, ts, ta) * 1000


def _parts(twin):
    k = _k(twin)
    CL = "df['CLINKER_TPH']"
    TA = "df['AMBIENT_C']"

    def Q(col):
        return (f"({k['eps'] * SB!r} * ((df['{col}'] + {C2K}) ** 4 - ({TA} + {C2K}) ** 4) + {k['hc']} * (df['{col}'] - {TA}))")
    SF = f"((df['FUEL_KILN_TPH'] + df['FUEL_CALCINER_TPH']) * df['FUEL_LHV_MJKG'] / {CL} * 1000)"
    SL = f"({k['area']!r} * {Q('SHELL_MEAN_C')} / 1000 * 3.6 / {CL})"
    PH = f"(df['PH_EXIT_FLOW_KNM3H'] * {k['cpg']} * (df['PH_EXIT_TEMP_C'] - {TA}) / {CL})"
    CE = f"(df['COOLER_EXH_FLOW_KNM3H'] * {k['cpa']} * (df['COOLER_EXH_TEMP_C'] - {TA}) / {CL})"
    CO = f"({k['cout']} * (df['CLINKER_OUT_C'] - {TA}))"
    SB_ = f"({k['ht']} + {PH} + {SL} + {CE} + {CO} + {k['cw'] + k['oth']})"
    CEF = f"(100 * (1 - ({CE} + {CO} + {k['cw']}) / ({k['cin']} * ({k['tin']} - {TA}))))"
    FA = "(100 * (df['O2_PH_EXIT_PCT'] - df['O2_CALCINER_PCT']) / (21 - df['O2_PH_EXIT_PCT']))"
    LN = f"({k['kb']} * ({k['thf']} - df['SHELL_MAX_C']) / {Q('SHELL_MAX_C')} * 1000)"
    TE = f"({k['t_e']} + {k['t_d'] - k['t_e']} * ({CL} / {k['cl_d']!r}) * ({k['n_d']} / df['KILN_SPEED_RPM']))"
    NE = f"({k['nox_ref']} * np.exp({k['knox']} * (df['BZT_C'] - {k['bzt_d']})))"
    GE = f"({k['gap0']} - {k['alpha'] * k['D'] * 1000!r} * (df['SHELL_T2_C'] - df['TYRE2_TEMP_C']))"
    MX = "np.maximum(np.maximum(df['TYRE1_MIGRATION_MM'], df['TYRE2_MIGRATION_MM']), df['TYRE3_MIGRATION_MM'])"
    MN = "np.minimum(np.minimum(df['TYRE1_MIGRATION_MM'], df['TYRE2_MIGRATION_MM']), df['TYRE3_MIGRATION_MM'])"
    SN = f"(df['STACK_NOX_MGNM3'] * {21 - k['o2ref']} / (21 - df['STACK_O2_PCT']))"
    return dict(k=k, SF=SF, SL=SL, PH=PH, CE=CE, CO=CO, SB=SB_, CEF=CEF, FA=FA, LN=LN, TE=TE, NE=NE, GE=GE, MX=MX, MN=MN, SN=SN)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("SHC_FUEL_KJKG", p["SF"]),
        ("SHELL_LOSS_KJKG", p["SL"]),
        ("PH_EXIT_LOSS_KJKG", p["PH"]),
        ("COOLER_EXH_LOSS_KJKG", p["CE"]),
        ("CLINKER_OUT_LOSS_KJKG", p["CO"]),
        ("SHC_BALANCE_KJKG", p["SB"]),
        ("SHC_MISMATCH_PCT", f"100 * ({p['SF']} / {p['SB']} - 1)"),
        ("SHC_EXCESS_KJKG", f"{p['SF']} - {k['shc_d']}"),
        ("COOLER_EFF_PCT", p["CEF"]),
        ("FALSE_AIR_PCT", p["FA"]),
        ("LINING_EQ_MM", p["LN"]),
        ("TORQUE_EXPECTED_PCT", p["TE"]),
        ("TORQUE_RATIO", f"df['DRIVE_TORQUE_PCT'] / {p['TE']}"),
        ("NOX_EXPECTED_PPM", p["NE"]),
        ("NOX_RATIO", f"df['NOX_INLET_PPM'] / {p['NE']}"),
        ("TYRE2_GAP_MM", "df['TYRE2_MIGRATION_MM'] / 3.14159"),
        ("TYRE2_GAP_EXPECTED_MM", p["GE"]),
        ("MIGRATION_MAX_MM", p["MX"]),
        ("MIGRATION_MIN_MM", p["MN"]),
        ("STACK_NOX_REF_MGNM3", p["SN"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    cl, ta = r["clinker_tph"], r["ambient_c"]
    sf = (r["fuel_kiln_tph"] + r["fuel_calciner_tph"]) * r["fuel_lhv_mjkg"] / cl * 1000
    sl = k["area"] * q_shell(k, r["shell_mean_c"], ta) / 1000 * 3.6 / cl
    ph = r["ph_exit_flow_knm3h"] * k["cpg"] * (r["ph_exit_temp_c"] - ta) / cl
    ce = r["cooler_exh_flow_knm3h"] * k["cpa"] * (r["cooler_exh_temp_c"] - ta) / cl
    co = k["cout"] * (r["clinker_out_c"] - ta)
    sb = k["ht"] + ph + sl + ce + co + (k["cw"] + k["oth"])
    te = k["t_e"] + (k["t_d"] - k["t_e"]) * (cl / k["cl_d"]) * (k["n_d"] / r["kiln_speed_rpm"])
    ne = k["nox_ref"] * math.exp(k["knox"] * (r["bzt_c"] - k["bzt_d"]))
    m = (r["tyre1_migration_mm"], r["tyre2_migration_mm"], r["tyre3_migration_mm"])
    return {
        "shc_fuel_kjkg": sf, "shell_loss_kjkg": sl, "ph_exit_loss_kjkg": ph, "cooler_exh_loss_kjkg": ce, "clinker_out_loss_kjkg": co,
        "shc_balance_kjkg": sb, "shc_mismatch_pct": 100 * (sf / sb - 1), "shc_excess_kjkg": sf - k["shc_d"],
        "cooler_eff_pct": 100 * (1 - (ce + co + k["cw"]) / (k["cin"] * (k["tin"] - ta))),
        "false_air_pct": 100 * (r["o2_ph_exit_pct"] - r["o2_calciner_pct"]) / (21 - r["o2_ph_exit_pct"]),
        "lining_eq_mm": lining_mm(k, r["shell_max_c"], ta),
        "torque_expected_pct": te, "torque_ratio": r["drive_torque_pct"] / te,
        "nox_expected_ppm": ne, "nox_ratio": r["nox_inlet_ppm"] / ne,
        "tyre2_gap_mm": r["tyre2_migration_mm"] / 3.14159,
        "tyre2_gap_expected_mm": k["gap0"] - float(f"{k['alpha'] * k['D'] * 1000!r}") * (r["shell_t2_c"] - r["tyre2_temp_c"]),
        "migration_max_mm": max(m), "migration_min_mm": min(m),
        "stack_nox_ref_mgnm3": r["stack_nox_mgnm3"] * (21 - k["o2ref"]) / (21 - r["stack_o2_pct"]),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    nb = L["nox_ratio_band"]
    NR = f"(df['NOX_INLET_PPM'] / {p['NE']})"
    return [
        ("KLN_LINING_THIN", f"{p['LN']} < {L['brick_min_mm']}", "Critical", "refractory_loss"),
        ("KLN_SHELL_HOT", f"df['SHELL_MAX_C'] > {L['shell_hot_c']}", "High", "refractory_loss"),
        ("KLN_MIGRATION_LOW", f"{p['MN']} < {L['migration_low_mm']}", "High", None),
        ("KLN_BZ_COLD", f"df['NOX_INLET_PPM'] < {L['nox_low_ppm']}", "High", "burning_zone_cold"),
        ("KLN_NOX_STACK_HIGH", f"{p['SN']} > {L['stack_nox_limit_mgnm3']}", "High", None),
        ("KLN_TORQUE_HIGH", f"(df['DRIVE_TORQUE_PCT'] / {p['TE']}) > {L['torque_ratio_alert']}", "Medium", "ring_formation"),
        ("KLN_INLET_O2_LOW", f"df['O2_INLET_PCT'] < {L['o2_inlet_low_pct']}", "Medium", "ring_formation"),
        ("KLN_FALSE_AIR_HIGH", f"{p['FA']} > {L['false_air_alert_pct']}", "Medium", "false_air"),
        ("KLN_COOLER_EFF_LOW", f"{p['CEF']} < {L['cooler_eff_alert_pct']}", "Medium", "cooler_degradation"),
        ("KLN_SHC_HIGH", f"({p['SF']} - {p['k']['shc_d']}) > {L['shc_excess_alert_kjkg']}", "Medium", "cooler_degradation"),
        ("KLN_SHC_MISMATCH", f"np.abs(100 * ({p['SF']} / {p['SB']} - 1)) > {L['shc_mismatch_pct']}", "Medium", "fuel_meter_drift"),
        ("KLN_FREE_LIME_HIGH", f"df['FREE_LIME_PCT'] > {L['free_lime_alert_pct']}", "Medium", "burning_zone_cold"),
        ("KLN_PYRO_MISMATCH", f"({NR} > {nb}) | ({NR} < {1 / nb:.6g})", "Medium", "pyrometer_fouling"),
        ("KLN_MIGRATION_HIGH", f"{p['MX']} > {L['migration_high_mm']}", "Medium", "tyre_pad_wear"),
        ("KLN_OVALITY_HIGH", f"df['OVALITY2_PCT'] > {L['ovality_alert_pct']}", "Medium", "tyre_pad_wear"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    nb = L["nox_ratio_band"]
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    add(t["lining_eq_mm"] < L["brick_min_mm"], "KLN_LINING_THIN", "Critical",
        f"Equivalent lining {t['lining_eq_mm']:.0f} mm at {r['shell_max_pos_m']:.0f} m: below {L['brick_min_mm']:.0f} mm", "refractory", "refractory_loss")
    add(r["shell_max_c"] > L["shell_hot_c"], "KLN_SHELL_HOT", "High",
        f"Shell hot spot {r['shell_max_c']:.0f} °C at {r['shell_max_pos_m']:.0f} m from the outlet", "refractory", "refractory_loss")
    add(t["migration_min_mm"] < L["migration_low_mm"], "KLN_MIGRATION_LOW", "High",
        f"Tyre migration only {t['migration_min_mm']:.1f} mm/rev: gap closing, shell constriction risk", "tyres")
    add(r["nox_inlet_ppm"] < L["nox_low_ppm"], "KLN_BZ_COLD", "High",
        f"Kiln inlet NOx {r['nox_inlet_ppm']:.0f} ppm: burning zone cooling", "process", "burning_zone_cold")
    add(t["stack_nox_ref_mgnm3"] > L["stack_nox_limit_mgnm3"], "KLN_NOX_STACK_HIGH", "High",
        f"Stack NOx {t['stack_nox_ref_mgnm3']:.0f} mg/Nm³ at 10 % O2, above {L['stack_nox_limit_mgnm3']:.0f}", "stack")
    add(t["torque_ratio"] > L["torque_ratio_alert"], "KLN_TORQUE_HIGH", "Medium",
        f"Drive torque {r['drive_torque_pct']:.0f} %, {t['torque_ratio']:.2f} x expected for the load", "kiln", "ring_formation")
    add(r["o2_inlet_pct"] < L["o2_inlet_low_pct"], "KLN_INLET_O2_LOW", "Medium",
        f"Kiln inlet O2 {r['o2_inlet_pct']:.1f} %, CO {r['co_inlet_ppm']:.0f} ppm", "kiln", "ring_formation")
    add(t["false_air_pct"] > L["false_air_alert_pct"], "KLN_FALSE_AIR_HIGH", "Medium",
        f"False air {t['false_air_pct']:.1f} % across the preheater (O2 {r['o2_calciner_pct']:.1f} → {r['o2_ph_exit_pct']:.1f} %)", "preheater", "false_air")
    add(t["cooler_eff_pct"] < L["cooler_eff_alert_pct"], "KLN_COOLER_EFF_LOW", "Medium",
        f"Cooler efficiency {t['cooler_eff_pct']:.1f} %, clinker out {r['clinker_out_c']:.0f} °C", "cooler", "cooler_degradation")
    add(t["shc_excess_kjkg"] > L["shc_excess_alert_kjkg"], "KLN_SHC_HIGH", "Medium",
        f"Heat consumption {t['shc_fuel_kjkg']:.0f} kJ/kg, {t['shc_excess_kjkg']:+.0f} vs design", "process", "cooler_degradation")
    add(abs(t["shc_mismatch_pct"]) > L["shc_mismatch_pct"], "KLN_SHC_MISMATCH", "Medium",
        f"Fuel says {t['shc_fuel_kjkg']:.0f}, heat balance says {t['shc_balance_kjkg']:.0f} kJ/kg ({t['shc_mismatch_pct']:+.1f} %)", "instruments", "fuel_meter_drift")
    add(r["free_lime_pct"] > L["free_lime_alert_pct"], "KLN_FREE_LIME_HIGH", "Medium",
        f"Free lime {r['free_lime_pct']:.1f} %", "process", "burning_zone_cold")
    add(t["nox_ratio"] > nb or t["nox_ratio"] < float(f"{1 / nb:.6g}"), "KLN_PYRO_MISMATCH", "Medium",
        f"NOx {r['nox_inlet_ppm']:.0f} ppm is {t['nox_ratio']:.2f} x what {r['bzt_c']:.0f} °C should give: check the pyrometer", "instruments", "pyrometer_fouling")
    add(t["migration_max_mm"] > L["migration_high_mm"], "KLN_MIGRATION_HIGH", "Medium",
        f"Tyre migration {t['migration_max_mm']:.1f} mm/rev (gap {t['migration_max_mm'] / math.pi:.1f} mm)", "tyres", "tyre_pad_wear")
    add(r["ovality2_pct"] > L["ovality_alert_pct"], "KLN_OVALITY_HIGH", "Medium",
        f"Shell ovality at tyre 2 {r['ovality2_pct']:.2f} %, above {L['ovality_alert_pct']} %", "tyres", "tyre_pad_wear")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
