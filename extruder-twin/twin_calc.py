"""The single-screw pipe extruder twin's expectations (EX-4401, KraussMaffei KME 75-36 B/R on a PE 100 pipe line).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Conveying (grooved feed: output linear in screw speed, independent of the head pressure, as the maker states):
    expected output       Q_exp = q0 x N                          q0 = specific rate at commissioning (kg/h per rpm)
    specific rate ratio   SRR   = Q / (q0 x N)                    1.0 = as new; wear and a warm feed bush lower it
    flight clearance      c/c0  = (1 + (1 - SRR) x p_d / (k x p_tip))^(1/3)
      from the leakage model  1 - SRR = k x ((c/c0)^3 - 1) x p_tip / p_d  (leakage over the flights grows with the cube of
      the gap and with the pressure the screw builds); c0 = D / 1000 per side when new, replace at about 4 x c0.
Drive and energy:
    expected drive power  P_exp = P0 + e_d x Q x (MFR_ref / MFR)^a        (stiffer resin, more shear work per kg)
    torque use            T / T_rated,  T_rated = 9.549 x P_rated / N_rated  (kN·m with kW and rpm)
    specific energy       SEC = (P_drive + P_heaters) / Q            kWh/kg; expected with P_exp and the heater power at rate
    melt enthalpy         dh  = (cp x (T_melt - T_hall) + dH_fusion) / 3600   kWh/kg, the least energy the melt must receive
    process efficiency    eta = dh / SEC
Melt flow (power-law melt, viscosity ~ 1/MFR^m, Arrhenius temperature shift):
    flow factor           F = (Q / Q_ref)^n x (MFR_ref / MFR)^m x exp(-b x (T_melt - T_ref))
    die pressure          p_die,exp = p_ref x F;     screen pressure drop  dp_exp = dp_clean x F   (clean screen)
    melt temperature      T_exp = T0 + k_N x (N - N_ref) + dp x 1e5 / (rho x cp_melt)   (adiabatic rise across the screen)
Heating: current while the zone's contactor is on, against the rated current P_zone / (sqrt(3) x 400 V); one open band of
three gives about two thirds.
Thrust bearing (ISO 281, roller bearing L10 = (C/P)^(10/3) revolutions): the axial load is the tip pressure x screw area, so
the life used per hour, relative to the design point, is  (N / N_d) x (p_tip / p_d)^(10/3).
Gearbox: oil temperature against hall temperature + k x shaft power (shaft power = torque x N / 9.549).
"""
import math


def _k(twin):
    d = twin["design"]
    m, c, dr, h, mat, rh, me, w, th, gb, ln = (d["machine"], d["conveying"], d["drive"], d["heating"], d["material"], d["rheology"],
                                               d["melt"], d["wear"], d["thrust"], d["gearbox"], d["line"])
    ir = [kw * 1000.0 / (math.sqrt(3) * h["voltage_v"]) for kw in h["zone_kw"]]
    return dict(D=m["screw_diameter_mm"], q0=c["specific_rate_kg_h_rpm"], nmax=c["max_speed_rpm"], qset=c["output_set_kg_h"],
                prated=dr["rated_power_kw"], nrated=dr["rated_speed_rpm"], p0=dr["no_load_kw"], ed=dr["drive_kwh_kg"], ea=dr["mfr_exponent"],
                eff=dr["efficiency"], trated=9.549 * dr["rated_power_kw"] / dr["rated_speed_rpm"],
                tset=h["set_c"], zkw=h["zone_kw"], ir=ir, ph0=h["heater_kw_at_rate"],
                mfr=mat["mfr_ref_g10min"], cp=mat["cp_kj_kgk"], hf=mat["fusion_kj_kg"], rho=mat["melt_density_kg_m3"], cpm=mat["melt_cp_kj_kgk"],
                pref=rh["die_p_ref_bar"], dp0=rh["screen_dp_clean_bar"], qref=rh["q_ref_kg_h"], n=rh["power_law_n"], m=rh["mfr_exponent"],
                b=rh["temp_coeff_per_k"], tref=rh["melt_t_ref_c"],
                t0=me["t0_c"], nref=me["n_ref_rpm"], kn=me["k_rpm"],
                c0=w["clearance_new_mm"], kl=w["leak_k"], crep=w["replace_ratio"],
                pd=th["p_design_bar"], nd=th["n_design_rpm"], x=th["life_exponent"],
                koil=gb["oil_k_per_kw"], vib_a=gb["vib_alert_mm_s"], vib_h=gb["vib_high_mm_s"], amb=ln["ambient_c"])


def dt_screen(k, dp):
    """Adiabatic melt temperature rise (K) for a pressure drop dp (bar)."""
    return dp * 1e5 / (k["rho"] * k["cpm"] * 1000.0)


def flow_factor(k, q, mfr, tm):
    return (q / k["qref"]) ** k["n"] * (k["mfr"] / mfr) ** k["m"] * math.exp(-k["b"] * (tm - k["tref"]))


def loss_from_clearance(k, ratio, p_tip):
    """Loss of specific rate for a clearance ratio c/c0 at tip pressure p_tip (the leakage model)."""
    return k["kl"] * (ratio ** 3 - 1) * p_tip / k["pd"]


def _parts(twin):
    k = _k(twin)
    N = "np.maximum(df['SCREW_SPEED_RPM'], 1.0)"
    Q = "np.maximum(df['OUTPUT_KG_H'], 1.0)"
    SRR = f"(df['OUTPUT_KG_H'] / ({k['q0']} * {N}))"
    FM = f"(({k['mfr']} / df['LOT_MFR_G10MIN']) ** {k['ea']})"
    DPE = f"({k['p0']} + {k['ed']} * df['OUTPUT_KG_H'] * {FM})"
    FLOW = (f"((({Q} / {k['qref']}) ** {k['n']}) * (({k['mfr']} / df['LOT_MFR_G10MIN']) ** {k['m']})"
            f" * np.exp(-{k['b']} * (df['MELT_TEMP_C'] - {k['tref']})))")
    SEC = f"((df['MOTOR_POWER_KW'] + df['HEATER_POWER_KW']) / {Q})"
    SECE = f"(({k['p0']} + {k['ed']} * {Q} * {FM} + {k['ph0']}) / {Q})"
    DH = f"(({k['cp']} * (df['MELT_TEMP_C'] - df['AMBIENT_TEMP_C']) + {k['hf']}) / 3600)"
    PDE = f"({k['pref']} * {FLOW})"
    DP = "(df['P_SCREEN_IN_BAR'] - df['P_DIE_BAR'])"
    TME = f"({k['t0']} + {k['kn']} * (df['SCREW_SPEED_RPM'] - {k['nref']}) + {DP} * 100000.0 / ({k['rho']} * {k['cpm']} * 1000.0))"
    CL = f"((1 + np.maximum(0.0, 1 - {SRR}) * {k['pd']} / ({k['kl']} * np.maximum(df['P_SCREEN_IN_BAR'], 1.0))) ** (1 / 3))"
    HR = [f"(df['ZONE{i + 1}_HEATER_A'] / {k['ir'][i]!r})" for i in range(5)]
    HMIN = HR[0]
    for h in HR[1:]:
        HMIN = f"np.minimum({HMIN}, {h})"
    ZD = [f"np.abs(df['ZONE{i + 1}_TEMP_C'] - {k['tset'][i]})" for i in range(5)]
    ZMAX = ZD[0]
    for z in ZD[1:]:
        ZMAX = f"np.maximum({ZMAX}, {z})"
    TH = f"(({N} / {k['nd']}) * (np.maximum(df['P_SCREEN_IN_BAR'], 0.0) / {k['pd']}) ** {k['x']!r})"
    OIL = f"(df['GEARBOX_OIL_TEMP_C'] - (df['AMBIENT_TEMP_C'] + {k['koil']} * df['MOTOR_TORQUE_KNM'] * df['SCREW_SPEED_RPM'] / 9.549))"
    return dict(k=k, N=N, Q=Q, SRR=SRR, FM=FM, DPE=DPE, FLOW=FLOW, SEC=SEC, SECE=SECE, DH=DH, PDE=PDE, DP=DP, TME=TME, CL=CL,
                HMIN=HMIN, ZMAX=ZMAX, TH=TH, OIL=OIL)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("OUTPUT_EXPECTED_KG_H", f"{k['q0']} * df['SCREW_SPEED_RPM']"),
        ("SPECIFIC_RATE_RATIO", p["SRR"]),
        ("CLEARANCE_RATIO", p["CL"]),
        ("DRIVE_POWER_EXPECTED_KW", p["DPE"]),
        ("DRIVE_POWER_RATIO", f"df['MOTOR_POWER_KW'] / {p['DPE']}"),
        ("TORQUE_PCT", f"df['MOTOR_TORQUE_KNM'] / {k['trated']!r} * 100"),
        ("SEC_KWH_KG", p["SEC"]),
        ("SEC_EXPECTED_KWH_KG", p["SECE"]),
        ("MELT_ENTHALPY_KWH_KG", p["DH"]),
        ("PROCESS_EFFICIENCY", f"{p['DH']} / {p['SEC']}"),
        ("DIE_PRESSURE_EXPECTED_BAR", p["PDE"]),
        ("DIE_PRESSURE_RATIO", f"df['P_DIE_BAR'] / {p['PDE']}"),
        ("SCREEN_DP_BAR", p["DP"]),
        ("SCREEN_DP_RATIO", f"{p['DP']} / ({k['dp0']} * {p['FLOW']})"),
        ("MELT_TEMP_EXPECTED_C", p["TME"]),
        ("MELT_TEMP_RESIDUAL_K", f"df['MELT_TEMP_C'] - {p['TME']}"),
        ("HEATER_CURRENT_RATIO_MIN", p["HMIN"]),
        ("ZONE_TEMP_DEV_MAX_K", p["ZMAX"]),
        ("THRUST_LIFE_RATE", p["TH"]),
        ("GEARBOX_OIL_RESIDUAL_K", p["OIL"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    n = max(r["screw_speed_rpm"], 1.0)
    q = max(r["output_kg_h"], 1.0)
    srr = r["output_kg_h"] / (k["q0"] * n)
    fm = (k["mfr"] / r["lot_mfr_g10min"]) ** k["ea"]
    dpe = k["p0"] + k["ed"] * r["output_kg_h"] * fm
    flow = (q / k["qref"]) ** k["n"] * (k["mfr"] / r["lot_mfr_g10min"]) ** k["m"] * math.exp(-k["b"] * (r["melt_temp_c"] - k["tref"]))
    sec = (r["motor_power_kw"] + r["heater_power_kw"]) / q
    sece = (k["p0"] + k["ed"] * q * fm + k["ph0"]) / q
    dh = (k["cp"] * (r["melt_temp_c"] - r["ambient_temp_c"]) + k["hf"]) / 3600
    pde = k["pref"] * flow
    dp = r["p_screen_in_bar"] - r["p_die_bar"]
    tme = k["t0"] + k["kn"] * (r["screw_speed_rpm"] - k["nref"]) + dp * 100000.0 / (k["rho"] * k["cpm"] * 1000.0)
    cl = (1 + max(0.0, 1 - srr) * k["pd"] / (k["kl"] * max(r["p_screen_in_bar"], 1.0))) ** (1 / 3)
    hmin = min(r[f"zone{i + 1}_heater_a"] / k["ir"][i] for i in range(5))
    zmax = max(abs(r[f"zone{i + 1}_temp_c"] - k["tset"][i]) for i in range(5))
    th = (n / k["nd"]) * (max(r["p_screen_in_bar"], 0.0) / k["pd"]) ** k["x"]
    oil = r["gearbox_oil_temp_c"] - (r["ambient_temp_c"] + k["koil"] * r["motor_torque_knm"] * r["screw_speed_rpm"] / 9.549)
    return {
        "output_expected_kg_h": k["q0"] * r["screw_speed_rpm"], "specific_rate_ratio": srr, "clearance_ratio": cl,
        "drive_power_expected_kw": dpe, "drive_power_ratio": r["motor_power_kw"] / dpe,
        "torque_pct": r["motor_torque_knm"] / k["trated"] * 100,
        "sec_kwh_kg": sec, "sec_expected_kwh_kg": sece, "melt_enthalpy_kwh_kg": dh, "process_efficiency": dh / sec,
        "die_pressure_expected_bar": pde, "die_pressure_ratio": r["p_die_bar"] / pde,
        "screen_dp_bar": dp, "screen_dp_ratio": dp / (k["dp0"] * flow),
        "melt_temp_expected_c": tme, "melt_temp_residual_k": r["melt_temp_c"] - tme,
        "heater_current_ratio_min": hmin, "zone_temp_dev_max_k": zmax, "thrust_life_rate": th, "gearbox_oil_residual_k": oil,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    SRR, CL = p["SRR"], p["CL"]
    TMR = f"(df['MELT_TEMP_C'] - {p['TME']})"
    SDR = f"({p['DP']} / ({k['dp0']} * {p['FLOW']}))"
    DPR = f"(df['P_DIE_BAR'] / {p['PDE']})"
    return [
        ("EXT_HEAD_PRESSURE_HIGH", f"df['P_SCREEN_IN_BAR'] > {L['head_pressure_max_bar']}", "Critical", "screen_pack_clogging"),
        ("EXT_SCREW_WORN", f"({CL} > {L['clearance_worn']}) & (df['FEED_BUSH_TEMP_C'] <= {L['feed_bush_max_c']})", "High", "screw_barrel_wear"),
        ("EXT_FEED_BUSH_HOT", f"df['FEED_BUSH_TEMP_C'] > {L['feed_bush_max_c']}", "High", "feed_bush_cooling_loss"),
        ("EXT_GEARBOX_VIB_HIGH", f"df['GEARBOX_VIB_MM_S'] > {k['vib_h']}", "High", "gearbox_bearing_damage"),
        ("EXT_TORQUE_HIGH", f"df['MOTOR_TORQUE_KNM'] / {k['trated']!r} * 100 > {L['torque_pct_max']}", "High", None),
        ("EXT_SPECIFIC_RATE_LOW", f"{SRR} < {L['specific_rate_low']}", "Medium", "screw_barrel_wear"),
        ("EXT_MELT_TEMP_HIGH", f"{TMR} > {L['melt_temp_resid_k']}", "Medium", "screw_barrel_wear"),
        ("EXT_SCREEN_CHANGE_DUE", f"{SDR} > {L['screen_dp_ratio_change']}", "Medium", "screen_pack_clogging"),
        ("EXT_THRUST_LIFE_FAST", f"{p['TH']} > {L['thrust_rate_alert']}", "Medium", "screen_pack_clogging"),
        ("EXT_DIE_PRESSURE_DEV", f"np.abs({DPR} - 1) > {L['die_pressure_dev']}", "Medium", "die_restriction"),
        ("EXT_HEATER_BAND_FAILED", f"{p['HMIN']} < {L['heater_current_ratio_min']}", "Medium", "heater_band_failure"),
        ("EXT_ZONE_TEMP_DEV", f"{p['ZMAX']} > {L['zone_dev_max_k']}", "Medium", None),
        ("EXT_GEARBOX_VIB_ALERT", f"(df['GEARBOX_VIB_MM_S'] > {k['vib_a']}) & (df['GEARBOX_VIB_MM_S'] <= {k['vib_h']})", "Medium", "gearbox_bearing_damage"),
        ("EXT_GEARBOX_OIL_HOT", f"{p['OIL']} > {L['gearbox_oil_resid_k']}", "Medium", "gearbox_bearing_damage"),
        ("EXT_SEC_HIGH", f"({p['SEC']} / {p['SECE']}) > {L['sec_ratio_alert']}", "Medium", "barrel_cooling_stuck"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    bush_ok = r["feed_bush_temp_c"] <= L["feed_bush_max_c"]
    sec_ratio = t["sec_kwh_kg"] / t["sec_expected_kwh_kg"]
    add(r["p_screen_in_bar"] > L["head_pressure_max_bar"], "EXT_HEAD_PRESSURE_HIGH", "Critical",
        f"Pressure at the screw tip {r['p_screen_in_bar']:.0f} bar, above {L['head_pressure_max_bar']:.0f} bar (overpressure trip at {L['overpressure_trip_bar']:.0f})",
        "screen changer", "screen_pack_clogging")
    add(t["clearance_ratio"] > L["clearance_worn"] and bush_ok, "EXT_SCREW_WORN", "High",
        f"Flight clearance about {t['clearance_ratio']:.1f} x new (replace near {k['crep']:.0f} x)", "screw", "screw_barrel_wear")
    add(not bush_ok, "EXT_FEED_BUSH_HOT", "High", f"Grooved feed bush at {r['feed_bush_temp_c']:.0f} °C, above {L['feed_bush_max_c']:.0f} °C: check its cooling water",
        "feed throat", "feed_bush_cooling_loss")
    add(r["gearbox_vib_mm_s"] > k["vib_h"], "EXT_GEARBOX_VIB_HIGH", "High", f"Gearbox vibration {r['gearbox_vib_mm_s']:.1f} mm/s, above {k['vib_h']} mm/s",
        "gearbox", "gearbox_bearing_damage")
    add(t["torque_pct"] > L["torque_pct_max"], "EXT_TORQUE_HIGH", "High", f"Screw torque at {t['torque_pct']:.0f} % of rated", "drive")
    add(t["specific_rate_ratio"] < L["specific_rate_low"], "EXT_SPECIFIC_RATE_LOW", "Medium",
        f"Output per rpm {t['specific_rate_ratio'] * 100:.1f} % of commissioning ({r['output_kg_h'] / max(r['screw_speed_rpm'], 1.0):.2f} kg/h per rpm)", "screw", "screw_barrel_wear")
    add(t["melt_temp_residual_k"] > L["melt_temp_resid_k"], "EXT_MELT_TEMP_HIGH", "Medium",
        f"Melt {r['melt_temp_c']:.0f} °C, {t['melt_temp_residual_k']:+.1f} K above expected", "screw", "screw_barrel_wear")
    add(t["screen_dp_ratio"] > L["screen_dp_ratio_change"], "EXT_SCREEN_CHANGE_DUE", "Medium",
        f"Screen pressure drop {t['screen_dp_bar']:.0f} bar, {t['screen_dp_ratio']:.1f} x a clean screen", "screen changer", "screen_pack_clogging")
    add(t["thrust_life_rate"] > L["thrust_rate_alert"], "EXT_THRUST_LIFE_FAST", "Medium",
        f"Thrust bearing life used {t['thrust_life_rate']:.1f} x the design rate", "gearbox", "screen_pack_clogging")
    add(abs(t["die_pressure_ratio"] - 1) > L["die_pressure_dev"], "EXT_DIE_PRESSURE_DEV", "Medium",
        f"Pressure before the head {r['p_die_bar']:.0f} bar, {t['die_pressure_ratio']:.2f} x expected", "pipe head", "die_restriction")
    add(t["heater_current_ratio_min"] < L["heater_current_ratio_min"], "EXT_HEATER_BAND_FAILED", "Medium",
        f"A heating zone draws {t['heater_current_ratio_min'] * 100:.0f} % of its rated current while on: band open", "barrel heating", "heater_band_failure")
    add(t["zone_temp_dev_max_k"] > L["zone_dev_max_k"], "EXT_ZONE_TEMP_DEV", "Medium", f"A barrel zone is {t['zone_temp_dev_max_k']:.0f} K off its set point", "barrel heating")
    add(k["vib_a"] < r["gearbox_vib_mm_s"] <= k["vib_h"], "EXT_GEARBOX_VIB_ALERT", "Medium", f"Gearbox vibration {r['gearbox_vib_mm_s']:.1f} mm/s, above {k['vib_a']} mm/s",
        "gearbox", "gearbox_bearing_damage")
    add(t["gearbox_oil_residual_k"] > L["gearbox_oil_resid_k"], "EXT_GEARBOX_OIL_HOT", "Medium",
        f"Gearbox oil {t['gearbox_oil_residual_k']:+.1f} K above what the load explains", "gearbox", "gearbox_bearing_damage")
    add(sec_ratio > L["sec_ratio_alert"], "EXT_SEC_HIGH", "Medium",
        f"Specific energy {t['sec_kwh_kg']:.3f} kWh/kg, {sec_ratio:.2f} x expected", "barrel cooling", "barrel_cooling_stuck")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
