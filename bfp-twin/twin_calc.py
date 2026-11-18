"""The boiler feed pump twin's expectations (BFP-3301, KSB CHTR barrel pump on a VSD, balance drum, minimum-flow valve).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Pump curve at the live speed (affinity laws, r = n / n_rated):
    H expected = r^2 x H0 + h2 x Q^2            (= r^2 x H(Q / r) for the curve H = H0 + h2 Q^2 at rated speed)
    x = Q / (r x Q_BEP)                         (position on the curve; BEP ratio)
    eta expected = eta_BEP x (2x - x^2)         NPSH3 = r^2 x NPSH3_BEP x (c0 + c2 x^2)     Q_min = 35 % x Q_BEP x r
Measured head: H = (p2 - p1) / (rho g), rho of the water at the mean of the suction and discharge temperatures.
Thermodynamic efficiency (ISO 5198 clause 11, kinetic, elevation and secondary terms left out):
    Eh = (p2 - p1) / rho                        hydraulic energy per kg (J/kg)
    Em = a x (p2 - p1) + cp x (T2 - T1)         energy per kg the shaft gave the water; a = isothermal factor
    eta = Eh / Em
  a, cp and rho: straight lines through the ISO 5198 tables at 100 bar, 150 to 170 degC.
Flow from the shaft power: Q_th = P_shaft x eta / (p2 - p1)   (P_shaft = VSD power x motor and gearbox efficiency).
  Compared with the suction flow meter: a drifting meter shows up as a ratio away from 1.
Balance drum leak-off: expected = q0 x sqrt(dp / dp_ref); worn drum clearance raises the ratio measured / expected.
NPSH available at the suction flange: (p1 abs - p_vap(T1)) / (rho g), p_vap from the Antoine equation.
  From the deaerator side: (p_DA abs - p_vap(T1)) / (rho g) + tank elevation + level - pipe loss(Q).
Bearings: temperature above the oil supply minus the commissioning rise x r^2 = excess.
Each expression works on one reading (Monitor keeps no state for the twin).
"""
import math

G = 9.81
ATM = 1.01325           # bar
MMHG = 0.00133322       # bar per mmHg


def _g(x):
    """A constant as written into the Monitor expression (8 significant digits), so Python and pandas use the same number."""
    return float(f"{x:.8g}")


def _k(twin):
    d = twin["design"]
    p, b, dr, w, s = d["pump"], d["balance"], d["drive"], d["water"], d["suction"]
    br = d["bearings"]
    h2 = (p["h_bep_m"] - p["h_shutoff_m"]) / p["q_bep_m3h"] ** 2
    return dict(n0=p["rated_rpm"], qb=p["q_bep_m3h"], hb=p["h_bep_m"], h0=p["h_shutoff_m"], h2=_g(h2), eb=p["eff_bep"],
                qmf=p["q_min_frac"], n3=p["npsh3_bep_m"], c0=p["npsh3_shape"][0], c2=p["npsh3_shape"][1],
                lo0=b["leakoff_m3h"], dpr=b["dp_ref_bar"], ed=dr["eff_motor_gear"],
                tr=w["t_ref_c"], rho0=w["rho_ref"], rhos=w["rho_slope"], a0=w["a_ref"], as_=w["a_slope"], cp0=w["cp_ref"], cps=w["cp_slope"],
                A=w["antoine"][0], B=w["antoine"][1], C=w["antoine"][2],
                z=s["deaerator_elev_m"], kf=_g(s["pipe_loss_bep_m"] / p["q_bep_m3h"] ** 2),
                toil=br["oil_c"], thr=br["thrust_rise_k"], jr=br["journal_rise_k"])


# shared pure-Python helpers (physics.py, the figures and the post use them too) -------------------------------------------
def rho(k, t):
    return k["rho0"] + k["rhos"] * (t - k["tr"])


def a_iso(k, t):
    return k["a0"] + k["as_"] * (t - k["tr"])


def cp(k, t):
    return k["cp0"] + k["cps"] * (t - k["tr"])


def pvap(k, t):
    """Vapour pressure of water (bar abs), Antoine equation 99..374 degC."""
    return 10 ** (k["A"] - k["B"] / (k["C"] + t)) * MMHG


def tsat(k, p_abs):
    """Saturation temperature (degC) for a pressure in bar abs: the Antoine equation turned round."""
    return k["B"] / (k["A"] - math.log10(p_abs / MMHG)) - k["C"]


def head_curve(k, q, r=1.0):
    return k["h0"] * r * r + k["h2"] * q * q


def eff_curve(k, x):
    return k["eb"] * (2 * x - x * x)


def npsh3(k, x, r=1.0):
    return r * r * k["n3"] * (k["c0"] + k["c2"] * x * x)


def thermo_eff(k, dp_bar, t1, t2):
    tm = (t1 + t2) / 2
    dp = dp_bar * 1e5
    return dp / rho(k, tm) / (a_iso(k, tm) * dp + cp(k, tm) * (t2 - t1))


def _parts(twin):
    k = _k(twin)
    R = f"(np.maximum(df['SPEED_RPM'], 1) / {k['n0']})"
    Q = "df['SUCTION_FLOW_M3H']"
    X = f"({Q} / ({R} * {k['qb']}))"
    TM = "((df['SUCTION_TEMP_C'] + df['DISCHARGE_TEMP_C']) / 2)"
    RHO = f"({k['rho0']} + {k['rhos']} * ({TM} - {k['tr']}))"
    RHOS = f"({k['rho0']} + {k['rhos']} * (df['SUCTION_TEMP_C'] - {k['tr']}))"
    DP = "(df['DISCHARGE_PRESSURE_BAR'] - df['SUCTION_PRESSURE_BAR'])"
    DT = "(df['DISCHARGE_TEMP_C'] - df['SUCTION_TEMP_C'])"
    HM = f"({DP} * 100000 / ({RHO} * {G}))"
    HE = f"({k['h0']} * {R} ** 2 + {k['h2']} * {Q} ** 2)"
    AI = f"({k['a0']} + {k['as_']} * ({TM} - {k['tr']}))"
    CP = f"({k['cp0']} + {k['cps']} * ({TM} - {k['tr']}))"
    ETA = f"({DP} * 100000 / {RHO} / ({AI} * {DP} * 100000 + {CP} * {DT}))"
    EE = f"({k['eb']} * (2 * {X} - {X} ** 2))"
    SH = f"(df['MOTOR_KW'] * {k['ed']})"
    QTH = f"({SH} * 1000 * {ETA} / np.maximum({DP} * 100000, 1) * 3600)"
    LE = f"np.maximum({k['lo0']} * np.sqrt(np.maximum({DP}, 0) / {k['dpr']}), 0.1)"
    MINF = f"({k['qmf'] * k['qb']:.8g} * {R})"
    PV = f"(np.power(10, {k['A']} - {k['B']} / ({k['C']} + df['SUCTION_TEMP_C'])) * {MMHG})"
    NA = f"((df['SUCTION_PRESSURE_BAR'] + {ATM} - {PV}) * 100000 / ({RHOS} * {G}))"
    NDA = (f"((df['DA_PRESSURE_BAR'] + {ATM} - {PV}) * 100000 / ({RHOS} * {G}) + {k['z']} + df['DA_LEVEL_M'] - {k['kf']} * {Q} ** 2)")
    N3 = f"({R} ** 2 * {k['n3']} * ({k['c0']} + {k['c2']} * {X} ** 2))"
    THX = f"(df['THRUST_BEARING_C'] - df['LUBE_OIL_C'] - {k['thr']} * {R} ** 2)"
    JX = f"(np.maximum(df['BEARING_DE_C'], df['BEARING_NDE_C']) - df['LUBE_OIL_C'] - {k['jr']} * {R} ** 2)"
    return dict(k=k, R=R, Q=Q, X=X, RHO=RHO, DP=DP, DT=DT, HM=HM, HE=HE, ETA=ETA, EE=EE, SH=SH, QTH=QTH, LE=LE, MINF=MINF,
                NA=NA, NDA=NDA, N3=N3, THX=THX, JX=JX)


def monitor_expressions(twin):
    p = _parts(twin)
    return [
        ("BEP_RATIO", p["X"]),
        ("HEAD_MEASURED_M", p["HM"]),
        ("HEAD_EXPECTED_M", p["HE"]),
        ("HEAD_RATIO", f"{p['HM']} / {p['HE']}"),
        ("TEMP_RISE_K", p["DT"]),
        ("EFF_THERMO_PCT", f"100 * {p['ETA']}"),
        ("EFF_EXPECTED_PCT", f"100 * {p['EE']}"),
        ("EFF_RATIO", f"{p['ETA']} / np.maximum({p['EE']}, 0.01)"),
        ("SHAFT_POWER_KW", p["SH"]),
        ("FLOW_THERMO_M3H", p["QTH"]),
        ("FLOW_METER_RATIO", f"{p['Q']} / np.maximum({p['QTH']}, 1)"),
        ("LEAKOFF_EXPECTED_M3H", p["LE"]),
        ("LEAKOFF_RATIO", f"df['LEAKOFF_FLOW_M3H'] / {p['LE']}"),
        ("MIN_FLOW_M3H", p["MINF"]),
        ("NPSH_AVAILABLE_M", p["NA"]),
        ("NPSHA_DEAERATOR_M", p["NDA"]),
        ("NPSH3_M", p["N3"]),
        ("NPSH_RATIO", f"{p['NA']} / {p['N3']}"),
        ("THRUST_EXCESS_K", p["THX"]),
        ("JOURNAL_EXCESS_K", p["JX"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    rr = max(r["speed_rpm"], 1) / k["n0"]
    q = r["suction_flow_m3h"]
    x = q / (rr * k["qb"])
    t1, t2 = r["suction_temp_c"], r["discharge_temp_c"]
    tm = (t1 + t2) / 2
    ro, ros = rho(k, tm), rho(k, t1)
    dp = r["discharge_pressure_bar"] - r["suction_pressure_bar"]
    hm = dp * 100000 / (ro * G)
    he = head_curve(k, q, rr)
    eta = dp * 100000 / ro / (a_iso(k, tm) * dp * 100000 + cp(k, tm) * (t2 - t1))
    ee = k["eb"] * (2 * x - x ** 2)
    sh = r["motor_kw"] * k["ed"]
    qth = sh * 1000 * eta / max(dp * 100000, 1) * 3600
    le = max(k["lo0"] * math.sqrt(max(dp, 0) / k["dpr"]), 0.1)
    pv = math.pow(10, k["A"] - k["B"] / (k["C"] + t1)) * MMHG
    na = (r["suction_pressure_bar"] + ATM - pv) * 100000 / (ros * G)
    nda = (r["da_pressure_bar"] + ATM - pv) * 100000 / (ros * G) + k["z"] + r["da_level_m"] - k["kf"] * q ** 2
    n3 = rr ** 2 * k["n3"] * (k["c0"] + k["c2"] * x ** 2)
    return {
        "bep_ratio": x, "head_measured_m": hm, "head_expected_m": he, "head_ratio": hm / he, "temp_rise_k": t2 - t1,
        "eff_thermo_pct": 100 * eta, "eff_expected_pct": 100 * ee, "eff_ratio": eta / max(ee, 0.01),
        "shaft_power_kw": sh, "flow_thermo_m3h": qth, "flow_meter_ratio": q / max(qth, 1),
        "leakoff_expected_m3h": le, "leakoff_ratio": r["leakoff_flow_m3h"] / le, "min_flow_m3h": _g(k["qmf"] * k["qb"]) * rr,
        "npsh_available_m": na, "npsha_deaerator_m": nda, "npsh3_m": n3, "npsh_ratio": na / n3,
        "thrust_excess_k": r["thrust_bearing_c"] - r["lube_oil_c"] - k["thr"] * rr ** 2,
        "journal_excess_k": max(r["bearing_de_c"], r["bearing_nde_c"]) - r["lube_oil_c"] - k["jr"] * rr ** 2,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    RUN = "(df['RUNNING'] > 0.5)"
    Q, MINF = p["Q"], p["MINF"]
    OKF = f"({Q} >= {MINF})"
    HR = f"({p['HM']} / {p['HE']})"
    ER = f"({p['ETA']} / np.maximum({p['EE']}, 0.01))"
    LR = f"(df['LEAKOFF_FLOW_M3H'] / {p['LE']})"
    NR = f"({p['NA']} / {p['N3']})"
    FM = f"({Q} / np.maximum({p['QTH']}, 1))"
    V = "df['VIBRATION_MM_S']"
    return [
        ("BFP_MIN_FLOW_LOW", f"{RUN} & ({Q} < {MINF})", "High", "minflow_valve_stuck"),
        ("BFP_NPSH_MARGIN_LIMIT", f"{RUN} & ({NR} < {L['npsh_limit']})", "High", "npsh_loss"),
        ("BFP_LEAKOFF_LIMIT", f"{RUN} & ({LR} >= {L['leakoff_limit']})", "High", "balance_drum_wear"),
        ("BFP_EFF_LOSS_HIGH", f"{RUN} & {OKF} & ({ER} < {L['eff_loss']})", "High", "impeller_wear"),
        ("BFP_VIBRATION_LIMIT", f"{V} >= {L['vib_limit_mm_s']}", "High", "bearing_degradation"),
        ("BFP_HEAD_LOW", f"{RUN} & {OKF} & ({HR} < {L['head_low']})", "Medium", "impeller_wear"),
        ("BFP_EFF_LOW", f"{RUN} & {OKF} & ({ER} >= {L['eff_loss']}) & ({ER} < {L['eff_low']})", "Medium", "impeller_wear"),
        ("BFP_LEAKOFF_HIGH", f"{RUN} & ({LR} >= {L['leakoff_alert']}) & ({LR} < {L['leakoff_limit']})", "Medium", "balance_drum_wear"),
        ("BFP_NPSH_MARGIN_LOW", f"{RUN} & ({NR} >= {L['npsh_limit']}) & ({NR} < {L['npsh_alert']})", "Medium", "strainer_clogging"),
        ("BFP_STRAINER_DP_HIGH", f"df['STRAINER_DP_BAR'] > {L['strainer_dp_bar']}", "Medium", "strainer_clogging"),
        ("BFP_RECIRC_PASSING", f"(df['RECIRC_VALVE_PCT'] < {L['recirc_closed_pct']}) & (df['RECIRC_FLOW_M3H'] > {L['recirc_passing_m3h']})", "Medium", "recirc_valve_passing"),
        ("BFP_FLOW_MISMATCH", f"{RUN} & {OKF} & (np.abs({FM} - 1) > {L['flow_mismatch']})", "Medium", "flow_meter_drift"),
        ("BFP_THRUST_TEMP_HIGH", f"{p['THX']} > {L['thrust_excess_k']}", "Medium", "balance_drum_wear"),
        ("BFP_JOURNAL_TEMP_HIGH", f"{p['JX']} > {L['journal_excess_k']}", "Medium", "bearing_degradation"),
        ("BFP_VIBRATION_HIGH", f"({V} >= {L['vib_alert_mm_s']}) & ({V} < {L['vib_limit_mm_s']})", "Medium", "npsh_loss"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    run = r["running"] > 0.5
    q, minf = r["suction_flow_m3h"], t["min_flow_m3h"]
    okf = q >= minf
    hr, er, lr, nr, fm = t["head_ratio"], t["eff_ratio"], t["leakoff_ratio"], t["npsh_ratio"], t["flow_meter_ratio"]
    v = r["vibration_mm_s"]
    add(run and q < minf, "BFP_MIN_FLOW_LOW", "High",
        f"Flow through the pump {q:.0f} m³/h, below the {minf:.0f} m³/h minimum at {r['speed_rpm']:.0f} rpm; minimum-flow valve at {r['recirc_valve_pct']:.0f} %",
        "recirculation valve", "minflow_valve_stuck")
    add(run and nr < L["npsh_limit"], "BFP_NPSH_MARGIN_LIMIT", "High",
        f"NPSH available {t['npsh_available_m']:.1f} m is only {nr:.2f} × NPSH3 ({t['npsh3_m']:.1f} m): cavitation risk", "suction", "npsh_loss")
    add(run and lr >= L["leakoff_limit"], "BFP_LEAKOFF_LIMIT", "High",
        f"Balance leak-off {r['leakoff_flow_m3h']:.1f} m³/h, {lr:.2f} × the {t['leakoff_expected_m3h']:.1f} m³/h expected", "balance drum", "balance_drum_wear")
    add(run and okf and er < L["eff_loss"], "BFP_EFF_LOSS_HIGH", "High",
        f"Thermodynamic efficiency {t['eff_thermo_pct']:.1f} %, {er:.2f} × the curve ({t['eff_expected_pct']:.1f} %)", "pump", "impeller_wear")
    add(v >= L["vib_limit_mm_s"], "BFP_VIBRATION_LIMIT", "High", f"Bearing housing vibration {v:.1f} mm/s", "bearings", "bearing_degradation")
    add(run and okf and hr < L["head_low"], "BFP_HEAD_LOW", "Medium",
        f"Pump head {t['head_measured_m']:.0f} m, {hr * 100:.1f} % of the curve at {q:.0f} m³/h and {r['speed_rpm']:.0f} rpm", "pump", "impeller_wear")
    add(run and okf and L["eff_loss"] <= er < L["eff_low"], "BFP_EFF_LOW", "Medium",
        f"Thermodynamic efficiency {t['eff_thermo_pct']:.1f} %, {er:.2f} × the curve ({t['eff_expected_pct']:.1f} %)", "pump", "impeller_wear")
    add(run and L["leakoff_alert"] <= lr < L["leakoff_limit"], "BFP_LEAKOFF_HIGH", "Medium",
        f"Balance leak-off {r['leakoff_flow_m3h']:.1f} m³/h, {lr:.2f} × expected", "balance drum", "balance_drum_wear")
    add(run and L["npsh_limit"] <= nr < L["npsh_alert"], "BFP_NPSH_MARGIN_LOW", "Medium",
        f"NPSH margin ratio {nr:.2f} (available {t['npsh_available_m']:.1f} m, NPSH3 {t['npsh3_m']:.1f} m)", "suction", "strainer_clogging")
    add(r["strainer_dp_bar"] > L["strainer_dp_bar"], "BFP_STRAINER_DP_HIGH", "Medium",
        f"Suction strainer differential pressure {r['strainer_dp_bar']:.2f} bar", "suction", "strainer_clogging")
    add(r["recirc_valve_pct"] < L["recirc_closed_pct"] and r["recirc_flow_m3h"] > L["recirc_passing_m3h"], "BFP_RECIRC_PASSING", "Medium",
        f"{r['recirc_flow_m3h']:.0f} m³/h back to the deaerator with the minimum-flow valve shut", "recirculation valve", "recirc_valve_passing")
    add(run and okf and abs(fm - 1) > L["flow_mismatch"], "BFP_FLOW_MISMATCH", "Medium",
        f"Flow meter {q:.0f} m³/h against {t['flow_thermo_m3h']:.0f} m³/h from shaft power and efficiency ({fm:.2f} ×)", "instrument", "flow_meter_drift")
    add(t["thrust_excess_k"] > L["thrust_excess_k"], "BFP_THRUST_TEMP_HIGH", "Medium",
        f"Thrust bearing {r['thrust_bearing_c']:.1f} °C, {t['thrust_excess_k']:.1f} K above its normal rise", "bearings", "balance_drum_wear")
    add(t["journal_excess_k"] > L["journal_excess_k"], "BFP_JOURNAL_TEMP_HIGH", "Medium",
        f"Journal bearing {max(r['bearing_de_c'], r['bearing_nde_c']):.1f} °C, {t['journal_excess_k']:.1f} K above its normal rise", "bearings", "bearing_degradation")
    add(L["vib_alert_mm_s"] <= v < L["vib_limit_mm_s"], "BFP_VIBRATION_HIGH", "Medium", f"Bearing housing vibration {v:.1f} mm/s", "bearings", "npsh_loss")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
