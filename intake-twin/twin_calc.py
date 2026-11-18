"""The cooling water intake twin's expectations (INT-3701: fine band screen with spray wash + circulating water pump).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Levels are metres above the screen channel invert. Q is the CW flow of the line (m3/s), UP and DN the levels upstream and
downstream of the screen, SEA the tide gauge at the intake mouth.

Screen (orifice law: head loss grows with the square of the velocity through the open area):
    dh            = UP - DN
    dh_clean      = dh0 x (Q / Q0)^2 x (h0 / UP)^2       (the wetted screen area grows with the water depth UP)
    blinding      = 1 - sqrt(dh_clean / dh)              (fraction of the open area lost: dh = dh_clean / (1 - b)^2)
    v_through     = Q / (open area x screen width x UP)  (through-screen velocity on the clean open area)
    v_approach    = Q / (channel width x UP)
Intake culvert: loss = SEA - UP, expected loss = loss0 x (Q / Q0)^2.
Pump suction (ANSI/HI 9.8): S = DN - bell clearance; S_req = D (1 + 2.3 F_D), F_D = V / sqrt(g D), V = Q / (pi D^2 / 4).
Pump (curve from the test sheet): H = p x 1e5 / (rho g) + z_gauge - DN (velocity head neglected);
    H_expected = H0 - (H0 - Hd) x (Q / Q0)^2;  efficiency = rho g Q H / P;  expected = eta0 x (2x - x^2), x = Q / Q0.
Drive: expected torque = T0 + k x dh (the differential presses the elements on their guides).
Spray wash: nozzles pass Qw = C x sqrt(p); nozzle ratio = (Qw / Qw0) / sqrt(p / p0) = C / C0 (1 = clean nozzles).
Condenser: waterbox pressure drop ratio = dp / (dp0 x (Q / Q0)^2) (debris carried over plugs the tube sheet).
"""
import math


def _k(twin):
    d = twin["design"]
    s, w, p, i = d["screen"], d["wash"], d["pump"], d["intake"]
    rho, g = i["rho_kg_m3"], i["g"]
    D = p["bell_d_m"]
    area = math.pi * D * D / 4
    return dict(dh0=s["dh_clean_m"], q0=s["dh_ref_flow_m3s"], h0=s["dh_ref_depth_m"], phi=s["open_area"], ws=s["screen_width_m"],
                wc=s["channel_width_m"], hs=s["high_speed_dh_m"], t0=s["torque0_pct"], kt=s["torque_per_m_pct"],
                vlo=s["speed_low_m_min"], vhi=s["speed_high_m_min"],
                pw0=w["pressure_bar"], qw0=w["flow_m3h"], wsh=w["shutoff_bar"],
                qd=p["duty_flow_m3s"], hd=p["duty_head_m"], h00=p["shutoff_head_m"], eta0=p["eta_bep"], D=D, area=area,
                cb=p["bell_clearance_m"], zg=p["gauge_elev_m"], rho=rho, g=g, pcoef=1e5 / (rho * g), ecoef=rho * g / 1000,
                cs=2.3 * D / (area * math.sqrt(g * D)), cl0=i["culvert_loss_m"], cdp0=i["cond_dp_bar"], tmax=i["cw_inlet_max_c"],
                sea0=i["mean_sea_m"], amp=i["tide_amp_m"], period=i["tide_period_h"], share=i["line_share"])


def s_req(k, q):
    """ANSI/HI 9.8 minimum submergence for flow q: D (1 + 2.3 F_D) = D + cs x q."""
    return k["D"] + k["cs"] * q


def head_exp(k, q):
    return k["h00"] - (k["h00"] - k["hd"]) * (q / k["qd"]) ** 2


def eta_exp(k, q):
    x = q / k["qd"]
    return k["eta0"] * (2 * x - x * x)


def _parts(twin):
    k = _k(twin)
    Q, UP, DN, SEA = "df['CW_FLOW_M3S']", "df['LEVEL_UP_M']", "df['LEVEL_DOWN_M']", "df['SEA_LEVEL_M']"
    DH = f"({UP} - {DN})"
    DHC = f"({k['dh0']} * ({Q} / {k['q0']}) ** 2 * ({k['h0']} / {UP}) ** 2)"
    SUB = f"({DN} - {k['cb']})"
    SR = f"({k['D']} + {k['cs']:.10g} * {Q})"
    HM = f"(df['PUMP_DISCHARGE_BAR'] * {k['pcoef']:.10g} + {k['zg']} - {DN})"
    HE = f"({k['h00']} - {k['h00'] - k['hd']:.10g} * ({Q} / {k['qd']}) ** 2)"
    EF = f"({k['ecoef']:.10g} * {Q} * {HM} / np.maximum(df['PUMP_POWER_KW'], 1.0))"
    EE = f"({k['eta0']} * (2 * {Q} / {k['qd']} - ({Q} / {k['qd']}) ** 2))"
    TE = f"({k['t0']} + {k['kt']} * {DH})"
    CUL = f"({SEA} - {UP})"
    CULE = f"({k['cl0']} * (np.maximum({Q}, 0.1) / {k['q0']}) ** 2)"
    NZ = f"((df['WASH_FLOW_M3H'] / {k['qw0']}) / np.sqrt(np.maximum(df['WASH_PRESSURE_BAR'], 0.1) / {k['pw0']}))"
    CDP = f"(df['COND_DP_BAR'] / ({k['cdp0']} * (np.maximum({Q}, 0.1) / {k['q0']}) ** 2))"
    BL = f"np.clip(1 - np.sqrt({DHC} / np.maximum({DH}, 0.001)), 0, 1)"
    return dict(k=k, Q=Q, UP=UP, DN=DN, DH=DH, DHC=DHC, SUB=SUB, SR=SR, HM=HM, HE=HE, EF=EF, EE=EE, TE=TE, CUL=CUL, CULE=CULE,
                NZ=NZ, CDP=CDP, BL=BL)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("DH_M", p["DH"]),
        ("DH_CLEAN_M", p["DHC"]),
        ("DH_RATIO", f"{p['DH']} / {p['DHC']}"),
        ("BLINDING", p["BL"]),
        ("V_THROUGH_SCREEN", f"{p['Q']} / ({k['phi'] * k['ws']:.10g} * {p['UP']})"),
        ("V_APPROACH", f"{p['Q']} / ({k['wc']} * {p['UP']})"),
        ("CULVERT_LOSS_M", p["CUL"]),
        ("CULVERT_LOSS_RATIO", f"{p['CUL']} / {p['CULE']}"),
        ("SUBMERGENCE_M", p["SUB"]),
        ("SUBMERGENCE_REQ_M", p["SR"]),
        ("SUBMERGENCE_MARGIN", f"{p['SUB']} / {p['SR']}"),
        ("PUMP_HEAD_M", p["HM"]),
        ("PUMP_HEAD_EXPECTED_M", p["HE"]),
        ("PUMP_HEAD_RATIO", f"{p['HM']} / {p['HE']}"),
        ("PUMP_EFF", p["EF"]),
        ("PUMP_EFF_RATIO", f"{p['EF']} / {p['EE']}"),
        ("TORQUE_EXPECTED_PCT", p["TE"]),
        ("TORQUE_RESIDUAL_PCT", f"df['SCREEN_TORQUE_PCT'] - {p['TE']}"),
        ("WASH_NOZZLE_RATIO", p["NZ"]),
        ("COND_DP_RATIO", p["CDP"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    q, up, dn, sea = r["cw_flow_m3s"], r["level_up_m"], r["level_down_m"], r["sea_level_m"]
    dh = up - dn
    dhc = k["dh0"] * (q / k["q0"]) ** 2 * (k["h0"] / up) ** 2
    sub = dn - k["cb"]
    sr = k["D"] + k["cs"] * q
    hm = r["pump_discharge_bar"] * k["pcoef"] + k["zg"] - dn
    he = k["h00"] - (k["h00"] - k["hd"]) * (q / k["qd"]) ** 2
    ef = k["ecoef"] * q * hm / max(r["pump_power_kw"], 1.0)
    ee = k["eta0"] * (2 * q / k["qd"] - (q / k["qd"]) ** 2)
    te = k["t0"] + k["kt"] * dh
    cul = sea - up
    cule = k["cl0"] * (max(q, 0.1) / k["q0"]) ** 2
    nz = (r["wash_flow_m3h"] / k["qw0"]) / math.sqrt(max(r["wash_pressure_bar"], 0.1) / k["pw0"])
    cdp = r["cond_dp_bar"] / (k["cdp0"] * (max(q, 0.1) / k["q0"]) ** 2)
    bl = min(1.0, max(0.0, 1 - math.sqrt(dhc / max(dh, 0.001))))
    return {
        "dh_m": dh, "dh_clean_m": dhc, "dh_ratio": dh / dhc, "blinding": bl,
        "v_through_screen": q / (k["phi"] * k["ws"] * up), "v_approach": q / (k["wc"] * up),
        "culvert_loss_m": cul, "culvert_loss_ratio": cul / cule,
        "submergence_m": sub, "submergence_req_m": sr, "submergence_margin": sub / sr,
        "pump_head_m": hm, "pump_head_expected_m": he, "pump_head_ratio": hm / he,
        "pump_eff": ef, "pump_eff_ratio": ef / ee, "pump_eff_expected": ee,
        "torque_expected_pct": te, "torque_residual_pct": r["screen_torque_pct"] - te,
        "wash_nozzle_ratio": nz, "cond_dp_ratio": cdp,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    DH = p["DH"]
    return [
        ("INT_DP_HIGH_HIGH", f"{DH} > {L['dh_high_high_m']}", "Critical", "debris_surge"),
        ("INT_SUBMERGENCE_LOW", f"({p['SUB']} / {p['SR']}) < {L['submergence_margin_min']}", "High", "culvert_fouling"),
        ("INT_DP_HIGH", f"({DH} > {L['dh_high_m']}) & ({DH} <= {L['dh_high_high_m']})", "High", "debris_surge"),
        ("INT_SCREEN_BYPASS", f"({DH} / {p['DHC']}) < {L['bypass_ratio']}", "High", "seal_carryover"),
        ("INT_DRIVE_TORQUE_HIGH", f"(df['SCREEN_SPEED_M_MIN'] > 0.5) & ((df['SCREEN_TORQUE_PCT'] - {p['TE']}) > {L['torque_residual_alert_pct']})", "High", "drive_chain_wear"),
        ("INT_PUMP_VIBRATION", f"df['PUMP_VIB_MM_S'] > {L['vibration_alert_mm_s']}", "High", "culvert_fouling"),
        ("INT_SCREEN_BLINDING", f"{p['BL']} > {L['blinding_alert']}", "Medium", "debris_surge"),
        ("INT_WASH_DUTY_HIGH", f"df['HIGH_SPEED_H_24H'] > {L['high_speed_h_alert']}", "Medium", "mesh_biofouling"),
        ("INT_WASH_NOZZLES_BLOCKED", f"{p['NZ']} < {L['nozzle_ratio_alert']}", "Medium", "spray_nozzle_blockage"),
        ("INT_WASH_PRESSURE_LOW", f"df['WASH_PRESSURE_BAR'] < {L['wash_pressure_low_bar']}", "Medium", "wash_pump_wear"),
        ("INT_PUMP_HEAD_LOW", f"({p['HM']} / {p['HE']}) < {L['head_ratio_alert']}", "Medium", "cw_pump_wear"),
        ("INT_PUMP_EFF_LOW", f"({p['EF']} / {p['EE']}) < {L['eff_ratio_alert']}", "Medium", "cw_pump_wear"),
        ("INT_CULVERT_LOSS_HIGH", f"({p['CUL']} / {p['CULE']}) > {L['culvert_ratio_alert']}", "Medium", "culvert_fouling"),
        ("INT_COND_DP_HIGH", f"{p['CDP']} > {L['cond_dp_ratio_alert']}", "Medium", "seal_carryover"),
        ("INT_CW_INLET_HIGH", f"df['CW_IN_C'] > {k['tmax']}", "Medium", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    dh = t["dh_m"]
    add(dh > L["dh_high_high_m"], "INT_DP_HIGH_HIGH", "Critical",
        f"Screen differential {dh:.2f} m, above the high-high {L['dh_high_high_m']} m: screen at risk, pump bay falling", "screen", "debris_surge")
    add(t["submergence_margin"] < L["submergence_margin_min"], "INT_SUBMERGENCE_LOW", "High",
        f"Bell submergence {t['submergence_m']:.2f} m, below the ANSI/HI 9.8 minimum {t['submergence_req_m']:.2f} m: vortex risk", "pump", "culvert_fouling")
    add(L["dh_high_m"] < dh <= L["dh_high_high_m"], "INT_DP_HIGH", "High", f"Screen differential {dh:.2f} m", "screen", "debris_surge")
    add(t["dh_ratio"] < L["bypass_ratio"], "INT_SCREEN_BYPASS", "High",
        f"Screen differential only {t['dh_ratio']:.2f} x clean: water is passing the mesh, debris carried over", "screen", "seal_carryover")
    add(r["screen_speed_m_min"] > 0.5 and t["torque_residual_pct"] > L["torque_residual_alert_pct"], "INT_DRIVE_TORQUE_HIGH", "High",
        f"Drive torque {r['screen_torque_pct']:.0f} %, {t['torque_residual_pct']:.0f} points above the line for this differential", "screen drive", "drive_chain_wear")
    add(r["pump_vib_mm_s"] > L["vibration_alert_mm_s"], "INT_PUMP_VIBRATION", "High", f"CW pump vibration {r['pump_vib_mm_s']:.1f} mm/s", "pump", "culvert_fouling")
    add(t["blinding"] > L["blinding_alert"], "INT_SCREEN_BLINDING", "Medium", f"{t['blinding'] * 100:.0f} % of the screen open area blinded", "screen", "debris_surge")
    add(r["high_speed_h_24h"] > L["high_speed_h_alert"], "INT_WASH_DUTY_HIGH", "Medium",
        f"Screen at high speed {r['high_speed_h_24h']:.0f} h of the last 24 h", "screen", "mesh_biofouling")
    add(t["wash_nozzle_ratio"] < L["nozzle_ratio_alert"], "INT_WASH_NOZZLES_BLOCKED", "Medium",
        f"Spray nozzles pass {t['wash_nozzle_ratio'] * 100:.0f} % of their design flow at this pressure", "wash", "spray_nozzle_blockage")
    add(r["wash_pressure_bar"] < L["wash_pressure_low_bar"], "INT_WASH_PRESSURE_LOW", "Medium",
        f"Spray-wash pressure {r['wash_pressure_bar']:.2f} bar", "wash", "wash_pump_wear")
    add(t["pump_head_ratio"] < L["head_ratio_alert"], "INT_PUMP_HEAD_LOW", "Medium",
        f"CW pump head {t['pump_head_m']:.1f} m, {t['pump_head_ratio'] * 100:.0f} % of the curve", "pump", "cw_pump_wear")
    add(t["pump_eff_ratio"] < L["eff_ratio_alert"], "INT_PUMP_EFF_LOW", "Medium",
        f"CW pump efficiency {t['pump_eff'] * 100:.0f} %, {t['pump_eff_ratio'] * 100:.0f} % of the curve", "pump", "cw_pump_wear")
    add(t["culvert_loss_ratio"] > L["culvert_ratio_alert"], "INT_CULVERT_LOSS_HIGH", "Medium",
        f"Intake culvert loses {t['culvert_loss_m']:.2f} m, {t['culvert_loss_ratio']:.1f} x expected", "intake", "culvert_fouling")
    add(t["cond_dp_ratio"] > L["cond_dp_ratio_alert"], "INT_COND_DP_HIGH", "Medium",
        f"Condenser waterbox pressure drop {r['cond_dp_bar']:.2f} bar, {t['cond_dp_ratio']:.2f} x expected", "condenser", "seal_carryover")
    add(r["cw_in_c"] > k["tmax"], "INT_CW_INLET_HIGH", "Medium",
        f"Condenser inlet {r['cw_in_c']:.1f} °C, above the {k['tmax']:.0f} °C design", "condenser")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
