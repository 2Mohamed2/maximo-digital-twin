"""The Francis hydro unit twin's expectations (HYD-3601, vertical Francis turbine-generator).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Flow (Winter-Kennedy, index method of IEC 60041):  Q = k sqrt(dp)            dp in kPa, Q in m3/s
Heads (m of water, rho = 1000 kg/m3, g = 9.81 m/s2):
    head at the spiral inlet  Hsp = z_spiral + p / (rho g) + v_in^2 / 2g           v_in = Q / A_spiral_inlet
    net head                  H   = Hsp - (z_tailwater + v_out^2 / 2g)             v_out = Q / A_draft_tube_outlet
    head loss intake->spiral  dH  = z_headwater - Hsp;  expected (Darcy-Weisbach) = (f L / D + sum K) / (2 g A^2) x Q^2
Hill chart (IEC 60193 factors, E = g H):
    nED = n D / sqrt(E)  (n in rev/s),  QED = Q / (D^2 sqrt(E)),  q = QED / QED_bep
    dn = nED / nED_bep - 1,  dq = q - 1 - tilt x dn
    eta_expected = eta_max - a_part min(dq,0)^2 - a_over max(dq,0)^2 - b dn^2     (turbine efficiency)
    eta_measured = P / (eta_gen rho g Q H);  deficit (points) = 100 (eta_expected - eta_measured)
    P_expected = eta_expected eta_gen rho g Q H;  lost MW = P_expected - P
Guide vanes: QED expected from the opening = QED_bep x opening / opening_bep; ratio = q / (opening / opening_bep).
Cavitation (Thoma number, IEC 60193): sigma_plant = (NPSE / g) / H
    NPSE / g = (p_atm - p_vapour) / (rho g) - (z_runner - z_tailwater)          p_vapour by Tetens: 0.61078 exp(17.27 T / (T + 237.3)) kPa
    sigma_required = sigma_bep (1 + s_over max(q-1, 0) + s_part max(1-q, 0));  margin = sigma_plant / sigma_required
Draft tube: expected pulsation (% of H, peak-to-peak) = base + rope x exp(-((q - q_rope) / width)^2);
    vortex rope precession frequency = 0.3 x n (0.2 to 0.4 x runner frequency in the literature).
Bearings (L = P / rated): TGB oil expected = cooling water + a0 + a1 L; TGB pad expected = TGB oil (measured) + b0 + b1 L.
"""
import math


def _k(twin):
    d = twin["design"]
    hc, u, lv, ww, fl, cv, dt, br, gv = (d["hill_chart"], d["unit"], d["levels"], d["waterway"], d["flow"], d["cavitation"],
                                         d["draft_tube"], d["bearings"], d["governor"])
    g, rho = u["g"], u["rho"]
    a_pipe = math.pi * ww["diameter_m"] ** 2 / 4
    kl = (ww["friction_f"] * ww["length_m"] / ww["diameter_m"] + ww["k_minor"]) / (2 * g * a_pipe ** 2)
    return dict(D=u["runner_d_m"], n=u["speed_rpm"], rated=u["rated_mw"], eg=u["eta_gen"], gate=u["gate_bep_pct"], g=g, rho=rho,
                ned=hc["ned_bep"], qed=hc["qed_bep"], emax=hc["eta_model_max"] + hc["step_up"], ap=hc["a_part"], ao=hc["a_over"],
                bs=hc["b_speed"], tilt=hc["tilt"], zref=lv["z_ref_m"], zsp=lv["z_spiral_m"], hw=lv["headwater_m"], tw=lv["tailwater_m"],
                kl=float(f"{kl:.6g}"), ain=float(f"{math.pi * ww['spiral_inlet_d_m'] ** 2 / 4:.6g}"), adt=ww["draft_outlet_m2"],
                wk=fl["wk_k"], s0=cv["sigma_bep"], so=cv["slope_over"], sp=cv["slope_part"],
                base=dt["base_pct"], rope=dt["rope_pct"], rq=dt["rope_q"], rw=dt["rope_width"], rfr=dt["rope_freq_ratio"],
                a0=br["oil_a0"], a1=br["oil_a1"], b0=br["pad_b0"], b1=br["pad_b1"], c0=br["thrust_c0"], c1=br["thrust_c1"],
                oil=gv["oil_nominal_bar"])


def hill(k, ned, qed):
    """Expected turbine efficiency (fraction) at (nED, QED)."""
    dn = ned / k["ned"] - 1
    dq = qed / k["qed"] - 1 - k["tilt"] * dn
    return k["emax"] - k["ap"] * min(dq, 0) ** 2 - k["ao"] * max(dq, 0) ** 2 - k["bs"] * dn ** 2


def sigma_required(k, q):
    return k["s0"] * (1 + k["so"] * max(q - 1, 0) + k["sp"] * max(1 - q, 0))


def pv_kpa(t_c):
    return 0.61078 * math.exp(17.27 * t_c / (t_c + 237.3))


def _parts(twin):
    k = _k(twin)
    g, rho = k["g"], k["rho"]
    Q = f"({k['wk']} * np.sqrt(df['WK_DP_KPA']))"
    HSP = f"({k['zsp']} + df['SPIRAL_PRESSURE_BAR'] * 100000 / ({rho * g}) + ({Q} / {k['ain']}) ** 2 / {2 * g})"
    H = f"({HSP} - (df['TAILWATER_LEVEL_M'] + ({Q} / {k['adt']}) ** 2 / {2 * g}))"
    LOSS = f"(df['HEADWATER_LEVEL_M'] - {HSP})"
    LR = f"({LOSS} / ({k['kl']} * {Q} ** 2))"
    NED = f"(df['SPEED_RPM'] / 60 * {k['D']} / np.sqrt({g} * {H}))"
    QED = f"({Q} / ({k['D'] ** 2:.6g} * np.sqrt({g} * {H})))"
    QR = f"({QED} / {k['qed']})"
    DN = f"({NED} / {k['ned']} - 1)"
    DQ = f"({QR} - 1 - {k['tilt']} * {DN})"
    EE = f"(100 * ({k['emax']:.6g} - {k['ap']} * np.minimum({DQ}, 0) ** 2 - {k['ao']} * np.maximum({DQ}, 0) ** 2 - {k['bs']} * {DN} ** 2))"
    EM = f"(100 * df['ACTIVE_POWER_MW'] * 1000000 / ({k['eg'] * rho * g:.6g} * {Q} * {H}))"
    DEF = f"({EE} - {EM})"
    PE = f"({EE} / 100 * {k['eg'] * rho * g:.6g} * {Q} * {H} / 1000000)"
    GFR = f"({QR} / (df['GATE_POSITION_PCT'] / {k['gate']}))"
    PV = "(0.61078 * np.exp(17.27 * df['WATER_TEMP_C'] / (df['WATER_TEMP_C'] + 237.3)))"
    SIGP = f"(((df['AMBIENT_PRESSURE_KPA'] - {PV}) * 1000 / {rho * g} - ({k['zref']} - df['TAILWATER_LEVEL_M'])) / {H})"
    SIGR = f"({k['s0']} * (1 + {k['so']} * np.maximum({QR} - 1, 0) + {k['sp']} * np.maximum(1 - {QR}, 0)))"
    DTE = f"({k['base']} + {k['rope']} * np.exp(-(({QR} - {k['rq']}) / {k['rw']}) ** 2))"
    LD = f"(df['ACTIVE_POWER_MW'] / {k['rated']})"
    OILR = f"(df['TGB_OIL_TEMP_C'] - (df['COOLING_WATER_TEMP_C'] + {k['a0']} + {k['a1']} * {LD}))"
    PADR = f"(df['TGB_PAD_TEMP_C'] - (df['TGB_OIL_TEMP_C'] + {k['b0']} + {k['b1']} * {LD}))"
    return dict(k=k, Q=Q, H=H, LOSS=LOSS, LR=LR, NED=NED, QED=QED, QR=QR, EE=EE, EM=EM, DEF=DEF, PE=PE, GFR=GFR, SIGP=SIGP,
                SIGR=SIGR, DTE=DTE, OILR=OILR, PADR=PADR)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("FLOW_M3S", p["Q"]),
        ("NET_HEAD_M", p["H"]),
        ("HEAD_LOSS_M", p["LOSS"]),
        ("HEAD_LOSS_RATIO", p["LR"]),
        ("N_ED", p["NED"]),
        ("Q_ED", p["QED"]),
        ("Q_RATIO", p["QR"]),
        ("EFF_EXPECTED_PCT", p["EE"]),
        ("EFF_MEASURED_PCT", p["EM"]),
        ("EFF_DEFICIT_PTS", p["DEF"]),
        ("POWER_EXPECTED_MW", p["PE"]),
        ("LOST_MW", f"{p['PE']} - df['ACTIVE_POWER_MW']"),
        ("GATE_FLOW_RATIO", p["GFR"]),
        ("SIGMA_PLANT", p["SIGP"]),
        ("SIGMA_REQUIRED", p["SIGR"]),
        ("SIGMA_MARGIN", f"{p['SIGP']} / {p['SIGR']}"),
        ("DT_PULSATION_EXPECTED_PCT", p["DTE"]),
        ("ROPE_FREQ_HZ", f"{k['rfr']} * df['SPEED_RPM'] / 60"),
        ("TGB_OIL_RESIDUAL_C", p["OILR"]),
        ("TGB_PAD_RESIDUAL_C", p["PADR"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    g, rho = k["g"], k["rho"]
    Q = k["wk"] * math.sqrt(r["wk_dp_kpa"])
    hsp = k["zsp"] + r["spiral_pressure_bar"] * 100000 / (rho * g) + (Q / k["ain"]) ** 2 / (2 * g)
    H = hsp - (r["tailwater_level_m"] + (Q / k["adt"]) ** 2 / (2 * g))
    loss = r["headwater_level_m"] - hsp
    ned = r["speed_rpm"] / 60 * k["D"] / math.sqrt(g * H)
    qed = Q / (float(f"{k['D'] ** 2:.6g}") * math.sqrt(g * H))
    qr = qed / k["qed"]
    egrg = float(f"{k['eg'] * rho * g:.6g}")
    k2 = dict(k, emax=float(f"{k['emax']:.6g}"))
    ee = 100 * hill(k2, ned, qed)
    em = 100 * r["active_power_mw"] * 1000000 / (egrg * Q * H)
    pe = ee / 100 * egrg * Q * H / 1000000
    sigp = ((r["ambient_pressure_kpa"] - pv_kpa(r["water_temp_c"])) * 1000 / (rho * g) - (k["zref"] - r["tailwater_level_m"])) / H
    sigr = sigma_required(k, qr)
    ld = r["active_power_mw"] / k["rated"]
    return {
        "flow_m3s": Q, "net_head_m": H, "head_loss_m": loss, "head_loss_ratio": loss / (k["kl"] * Q ** 2),
        "n_ed": ned, "q_ed": qed, "q_ratio": qr, "eff_expected_pct": ee, "eff_measured_pct": em, "eff_deficit_pts": ee - em,
        "power_expected_mw": pe, "lost_mw": pe - r["active_power_mw"],
        "gate_flow_ratio": qr / (r["gate_position_pct"] / k["gate"]),
        "sigma_plant": sigp, "sigma_required": sigr, "sigma_margin": sigp / sigr,
        "dt_pulsation_expected_pct": k["base"] + k["rope"] * math.exp(-((qr - k["rq"]) / k["rw"]) ** 2),
        "rope_freq_hz": k["rfr"] * r["speed_rpm"] / 60,
        "tgb_oil_residual_c": r["tgb_oil_temp_c"] - (r["cooling_water_temp_c"] + k["a0"] + k["a1"] * ld),
        "tgb_pad_residual_c": r["tgb_pad_temp_c"] - (r["tgb_oil_temp_c"] + k["b0"] + k["b1"] * ld),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    RUN = "(df['UNIT_STATE'] > 0.5)"
    return [
        ("HYD_EFF_DEFICIT_HIGH", f"{RUN} & ({p['DEF']} > {L['eff_deficit_high_pts']})", "High", "runner_wear"),
        ("HYD_GOV_OIL_PRESSURE_LOW", f"df['GOV_OIL_PRESSURE_BAR'] < {L['gov_oil_min_bar']}", "High", "governor_servo_fault"),
        ("HYD_SIGMA_MARGIN_LOW", f"{RUN} & (({p['SIGP']} / {p['SIGR']}) < {L['sigma_margin_min']})", "High", "low_tailwater"),
        ("HYD_DT_PULSATION_HIGH", f"{RUN} & (df['DT_PULSATION_PCT'] > {L['dt_pulsation_pct']})", "High", "rough_zone_operation"),
        ("HYD_SHAFT_RUNOUT_HIGH", f"{RUN} & (df['SHAFT_RUNOUT_UM'] > {L['runout_um']})", "High", "guide_bearing_wear"),
        ("HYD_THRUST_BRG_TEMP_HIGH", f"df['THRUST_PAD_TEMP_C'] > {L['thrust_pad_max_c']}", "High", "bearing_cooling_loss"),
        ("HYD_EFF_DEFICIT", f"{RUN} & ({p['DEF']} > {L['eff_deficit_pts']})", "Medium", "runner_wear"),
        ("HYD_GATE_FLOW_HIGH", f"{RUN} & ({p['GFR']} > {L['gate_flow_ratio']})", "Medium", "guide_vane_leakage"),
        ("HYD_GATE_TRACKING", f"{RUN} & (np.abs(df['GATE_SETPOINT_PCT'] - df['GATE_POSITION_PCT']) > {L['gate_dev_pct']})", "Medium", "governor_servo_fault"),
        ("HYD_ROUGH_ZONE", f"{RUN} & ({p['QR']} >= {L['rough_q_min']}) & ({p['QR']} <= {L['rough_q_max']})", "Medium", "rough_zone_operation"),
        ("HYD_TGB_TEMP_RESIDUAL", f"{RUN} & ({p['PADR']} > {L['tgb_pad_residual_c']})", "Medium", "guide_bearing_wear"),
        ("HYD_COOLING_WATER_LOW", f"df['COOLING_WATER_FLOW_PCT'] < {L['cooling_flow_min_pct']}", "Medium", "bearing_cooling_loss"),
        ("HYD_HEAD_LOSS_HIGH", f"{RUN} & ({p['QR']} >= {L['head_loss_q_min']}) & ({p['LR']} > {L['head_loss_ratio']})", "Medium", "intake_head_loss"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    run = r["unit_state"] > 0.5
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    add(run and t["eff_deficit_pts"] > L["eff_deficit_high_pts"], "HYD_EFF_DEFICIT_HIGH", "High",
        f"Turbine efficiency {t['eff_measured_pct']:.1f} %, {t['eff_deficit_pts']:.1f} points below the hill chart: {t['lost_mw']:.1f} MW lost", "runner", "runner_wear")
    add(r["gov_oil_pressure_bar"] < L["gov_oil_min_bar"], "HYD_GOV_OIL_PRESSURE_LOW", "High",
        f"Governor oil pressure {r['gov_oil_pressure_bar']:.1f} bar, below {L['gov_oil_min_bar']:.0f} bar", "governor", "governor_servo_fault")
    add(run and t["sigma_margin"] < L["sigma_margin_min"], "HYD_SIGMA_MARGIN_LOW", "High",
        f"Plant sigma {t['sigma_plant']:.3f} is only {t['sigma_margin']:.2f} x the {t['sigma_required']:.3f} the runner needs (tailwater {r['tailwater_level_m']:.1f} m)",
        "draft tube / runner", "low_tailwater")
    add(run and r["dt_pulsation_pct"] > L["dt_pulsation_pct"], "HYD_DT_PULSATION_HIGH", "High",
        f"Draft tube pulsation {r['dt_pulsation_pct']:.1f} % of head (vortex rope near {t['rope_freq_hz']:.2f} Hz)", "draft tube", "rough_zone_operation")
    add(run and r["shaft_runout_um"] > L["runout_um"], "HYD_SHAFT_RUNOUT_HIGH", "High",
        f"Shaft runout {r['shaft_runout_um']:.0f} µm p-p at the turbine guide bearing, above {L['runout_um']:.0f}", "guide bearing", "guide_bearing_wear")
    add(r["thrust_pad_temp_c"] > L["thrust_pad_max_c"], "HYD_THRUST_BRG_TEMP_HIGH", "High",
        f"Thrust pad {r['thrust_pad_temp_c']:.1f} °C, above {L['thrust_pad_max_c']:.0f} °C", "cooling", "bearing_cooling_loss")
    add(run and t["eff_deficit_pts"] > L["eff_deficit_pts"], "HYD_EFF_DEFICIT", "Medium",
        f"Turbine efficiency {t['eff_deficit_pts']:.1f} points below the hill chart at nED {t['n_ed']:.3f}, QED {t['q_ed']:.3f}", "runner", "runner_wear")
    add(run and t["gate_flow_ratio"] > L["gate_flow_ratio"], "HYD_GATE_FLOW_HIGH", "Medium",
        f"Flow {t['gate_flow_ratio']:.2f} x what the guide vane opening explains", "guide vanes", "guide_vane_leakage")
    add(run and abs(r["gate_setpoint_pct"] - r["gate_position_pct"]) > L["gate_dev_pct"], "HYD_GATE_TRACKING", "Medium",
        f"Guide vanes at {r['gate_position_pct']:.1f} %, governor asks {r['gate_setpoint_pct']:.1f} %", "governor", "governor_servo_fault")
    add(run and L["rough_q_min"] <= t["q_ratio"] <= L["rough_q_max"], "HYD_ROUGH_ZONE", "Medium",
        f"Unit at {t['q_ratio'] * 100:.0f} % of the BEP flow: inside the part-load rough zone", "draft tube", "rough_zone_operation")
    add(run and t["tgb_pad_residual_c"] > L["tgb_pad_residual_c"], "HYD_TGB_TEMP_RESIDUAL", "Medium",
        f"Turbine guide bearing pad {t['tgb_pad_residual_c']:+.1f} K above its oil + load model", "guide bearing", "guide_bearing_wear")
    add(r["cooling_water_flow_pct"] < L["cooling_flow_min_pct"], "HYD_COOLING_WATER_LOW", "Medium",
        f"Bearing cooling water at {r['cooling_water_flow_pct']:.0f} % of design", "cooling", "bearing_cooling_loss")
    add(run and t["q_ratio"] >= L["head_loss_q_min"] and t["head_loss_ratio"] > L["head_loss_ratio"], "HYD_HEAD_LOSS_HIGH", "Medium",
        f"Head loss intake to spiral {t['head_loss_m']:.2f} m, {t['head_loss_ratio']:.1f} x Darcy-Weisbach", "waterway", "intake_head_loss")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
