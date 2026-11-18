"""The process centrifugal compressor twin's expectations (K-2301, API 617 barrel compressor, motor + VSD).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Gas and flow (one reading, suction conditions P1 [bar a], T1 [K]):
    R = 8314.46 / MW                         specific gas constant, J/(kg K)
    rho1 = P1 x 1e5 / (Z R T1)               suction density
    Q = 3600 C sqrt(dp / rho1)               actual inlet flow, m3/h, from the suction flow element (dp in Pa)
    m = Q / 3600 x rho1                      mass flow, kg/s
Polytropic head and efficiency from measured P and T (ASME PTC 10, ideal-gas form with an average Z):
    m_p = (n - 1) / n = ln(T2 / T1) / ln(P2 / P1)      polytropic exponent of the measured path
    eta_p = ((k - 1) / k) / m_p                          polytropic efficiency
    H_p = Z R T1 (PR^m_p - 1) / m_p = Z R (T2 - T1) / m_p   polytropic head, J/kg
    gas power = m H_p / eta_p = m Z R (T2 - T1) k / (k - 1)  (= m cp dT)
Map and fan laws (one compressor, one gas, speed N):
    x = Q / (Q0 N / N0)                                  reduced flow: 1 = rated point, flow scales with speed
    H_expected = (N / N0)^2 H0 (c0 + c1 x + c2 x^2)      head scales with speed squared
    eta_expected = eta0 (1 - curv (x - 1)^2)             efficiency stays on the same curve at the same x
Surge (the surge line is the parabola H ~ Q^2 through the surge points of every speed):
    Q_surge(H) = x_s Q0 sqrt(H / (h_s H0)),  h_s = c0 + c1 x_s + c2 x_s^2
    surge margin = (Q - Q_surge(H_p)) / Q x 100 %, at the head the compressor makes now
API 617 shop-test vibration limit, for reference: 25.4 sqrt(12000 / N) um pp, not more than 25.4 um.
"""
R_UNIV = 8314.46


def _k(twin):
    d = twin["design"]
    g, mp, fe, a, dr = d["gas"], d["map"], d["flow_element"], d["anti_surge"], d["drive"]
    R = R_UNIV / g["mw_kg_kmol"]
    xs = mp["surge_x"]
    hs = mp["head_c0"] + mp["head_c1"] * xs + mp["head_c2"] * xs ** 2
    r10 = lambda v: float(f"{v:.10g}")
    zr, cpf = r10(g["z"] * R), g["k"] / (g["k"] - 1)
    return dict(R=R, z=g["z"], kap=g["k"], zr=zr, cpf=cpf, zrc=r10(zr * cpf), km=r10((g["k"] - 1) / g["k"]),
                qs0=r10(xs * mp["flow_rated_m3h"]), hsh0=r10(hs * mp["head_rated_kjkg"]),
                n0=mp["speed_rated_rpm"], q0=mp["flow_rated_m3h"], h0=mp["head_rated_kjkg"], e0=mp["eta_rated"],
                c0=mp["head_c0"], c1=mp["head_c1"], c2=mp["head_c2"], curv=mp["eta_curv"], xs=xs, hs=hs,
                C=fe["c_m2"], scl=a["control_margin_pct"], asv=a["valve_capacity_m3h"], eff=dr["drive_train_eff"])


def head_map(k, x):
    """Head at rated speed as a fraction of H0, at reduced flow x."""
    return k["c0"] + k["c1"] * x + k["c2"] * x * x


def eta_map(k, x):
    return k["e0"] * (1 - k["curv"] * (x - 1) ** 2)


def q_surge(k, head_kjkg):
    """Surge flow (m3/h actual inlet) at a given polytropic head."""
    return k["qs0"] * (head_kjkg / k["hsh0"]) ** 0.5


def _parts(twin):
    k = _k(twin)
    T1 = "(df['SUCTION_TEMP_C'] + 273.15)"
    T2 = "(df['DISCHARGE_TEMP_C'] + 273.15)"
    RHO = f"(df['SUCTION_PRESSURE_BARA'] * 100000 / ({k['zr']!r} * {T1}))"
    Q = f"(3600 * {k['C']} * np.sqrt(df['FLOW_DP_MBAR'] * 100 / {RHO}))"
    MF = f"({Q} / 3600 * {RHO})"
    PR = "(df['DISCHARGE_PRESSURE_BARA'] / df['SUCTION_PRESSURE_BARA'])"
    MP = f"(np.log({T2} / {T1}) / np.log({PR}))"
    ETA = f"({k['km']!r} / {MP})"
    H = f"({k['zr']!r} * ({T2} - {T1}) / {MP} / 1000)"
    SR = f"(df['SPEED_RPM'] / {k['n0']})"
    X = f"({Q} / ({k['q0']} * {SR}))"
    HE = f"({SR} ** 2 * {k['h0']} * ({k['c0']} + {k['c1']} * {X} + {k['c2']} * {X} ** 2))"
    EE = f"({k['e0']} * (1 - {k['curv']} * ({X} - 1) ** 2))"
    QS = f"({k['qs0']!r} * np.sqrt({H} / {k['hsh0']!r}))"
    SM = f"(({Q} - {QS}) / {Q} * 100)"
    GP = f"({MF} * {k['zrc']!r} * ({T2} - {T1}) / 1000)"
    PW = f"(df['DRIVER_POWER_KW'] * {k['eff']} / {GP})"
    return dict(k=k, RHO=RHO, Q=Q, MF=MF, PR=PR, MP=MP, ETA=ETA, H=H, SR=SR, X=X, HE=HE, EE=EE, QS=QS, SM=SM, GP=GP, PW=PW)


def monitor_expressions(twin):
    p = _parts(twin)
    return [
        ("RHO1_KG_M3", p["RHO"]),
        ("Q_ACT_M3H", p["Q"]),
        ("MASS_FLOW_KG_S", p["MF"]),
        ("PRESSURE_RATIO", p["PR"]),
        ("POLY_EXPONENT_M", p["MP"]),
        ("ETA_POLY", p["ETA"]),
        ("HEAD_POLY_KJKG", p["H"]),
        ("SPEED_RATIO", p["SR"]),
        ("FLOW_REDUCED", p["X"]),
        ("HEAD_EXPECTED_KJKG", p["HE"]),
        ("HEAD_RATIO", f"{p['H']} / {p['HE']}"),
        ("ETA_EXPECTED", p["EE"]),
        ("ETA_DEV_PTS", f"({p['ETA']} - {p['EE']}) * 100"),
        ("Q_SURGE_M3H", p["QS"]),
        ("SURGE_MARGIN_PCT", p["SM"]),
        ("GAS_POWER_KW", p["GP"]),
        ("POWER_RATIO", p["PW"]),
        ("VENT_FLOW_MAX_NM3H", "np.maximum(df['VENT_FLOW_DE_NM3H'], df['VENT_FLOW_NE_NM3H'])"),
        ("VIB_MAX_UM", "np.maximum(df['VIB_DE_UM'], df['VIB_NE_UM'])"),
        ("VIB_LIMIT_API617_UM", "np.minimum(25.4, 25.4 * np.sqrt(12000 / df['SPEED_RPM']))"),
    ]


def evaluate(twin, r):
    import math
    k = _k(twin)
    t1, t2 = r["suction_temp_c"] + 273.15, r["discharge_temp_c"] + 273.15
    rho = r["suction_pressure_bara"] * 100000 / (k["zr"] * t1)
    q = 3600 * k["C"] * math.sqrt(r["flow_dp_mbar"] * 100 / rho)
    mf = q / 3600 * rho
    pr = r["discharge_pressure_bara"] / r["suction_pressure_bara"]
    mp = math.log(t2 / t1) / math.log(pr)
    eta = k["km"] / mp
    h = k["zr"] * (t2 - t1) / mp / 1000
    sr = r["speed_rpm"] / k["n0"]
    x = q / (k["q0"] * sr)
    he = sr ** 2 * k["h0"] * head_map(k, x)
    ee = eta_map(k, x)
    qs = q_surge(k, h)
    gp = mf * k["zrc"] * (t2 - t1) / 1000
    return {
        "rho1_kg_m3": rho, "q_act_m3h": q, "mass_flow_kg_s": mf, "pressure_ratio": pr, "poly_exponent_m": mp,
        "eta_poly": eta, "head_poly_kjkg": h, "speed_ratio": sr, "flow_reduced": x, "head_expected_kjkg": he,
        "head_ratio": h / he, "eta_expected": ee, "eta_dev_pts": (eta - ee) * 100, "q_surge_m3h": qs,
        "surge_margin_pct": (q - qs) / q * 100, "gas_power_kw": gp, "power_ratio": r["driver_power_kw"] * k["eff"] / gp,
        "vent_flow_max_nm3h": max(r["vent_flow_de_nm3h"], r["vent_flow_ne_nm3h"]),
        "vib_max_um": max(r["vib_de_um"], r["vib_ne_um"]),
        "vib_limit_api617_um": min(25.4, 25.4 * math.sqrt(12000 / r["speed_rpm"])),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    SM = p["SM"]
    lo, hi = L["surge_margin_limit_pct"], L["surge_margin_alert_pct"]
    return [
        ("CC_SURGE_MARGIN_LOW", f"{SM} < {lo}", "High", "asv_stuck"),
        ("CC_ASV_DEVIATION", f"np.abs(df['ASC_OUTPUT_PCT'] - df['RECYCLE_VALVE_PCT']) > {L['asv_dev_alert_pct']}", "High", "asv_stuck"),
        ("CC_SEAL_GAS_DP_LOW", f"df['SEAL_GAS_DP_BAR'] < {L['seal_gas_dp_alert_bar']}", "High", "seal_gas_supply"),
        ("CC_SEAL_VENT_HIGH", f"np.maximum(df['VENT_FLOW_DE_NM3H'], df['VENT_FLOW_NE_NM3H']) > {L['vent_flow_alert_nm3h']}", "High", "seal_primary_wear"),
        ("CC_VIBRATION_HIGH", f"np.maximum(df['VIB_DE_UM'], df['VIB_NE_UM']) > {L['vib_alert_um']}", "High", "rotor_unbalance"),
        ("CC_THRUST_TEMP_HIGH", f"df['THRUST_TEMP_C'] > {L['thrust_temp_alert_c']}", "High", "thrust_overload"),
        ("CC_SURGE_CONTROL_LINE", f"({SM} >= {lo}) & ({SM} < {hi})", "Medium", "surge_approach"),
        ("CC_EFFICIENCY_LOW", f"({p['ETA']} - {p['EE']}) * 100 < {L['eta_dev_alert_pts']}", "Medium", "impeller_fouling"),
        ("CC_HEAD_LOW", f"{p['H']} / {p['HE']} < {L['head_ratio_alert']}", "Medium", "impeller_fouling"),
        ("CC_POWER_MISMATCH", f"np.abs({p['PW']} - 1) > {L['power_dev_alert']}", "Medium", "discharge_tt_drift"),
        ("CC_AXIAL_POSITION", f"np.abs(df['AXIAL_POS_MM']) > {L['axial_alert_mm']}", "Medium", "thrust_overload"),
        ("CC_BEARING_TEMP_HIGH", f"np.maximum(df['BRG_TEMP_DE_C'], df['BRG_TEMP_NE_C']) > {L['journal_temp_alert_c']}", "Medium", None),
        ("CC_RECYCLE_OPEN", f"df['RECYCLE_VALVE_PCT'] > {L['recycle_open_alert_pct']}", "Low", "surge_approach"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    sm, lo, hi = t["surge_margin_pct"], L["surge_margin_limit_pct"], L["surge_margin_alert_pct"]
    dev = abs(r["asc_output_pct"] - r["recycle_valve_pct"])
    add(sm < lo, "CC_SURGE_MARGIN_LOW", "High", f"Surge margin {sm:.1f} %, below {lo:.0f} %: the compressor is past its control line", "anti-surge", "asv_stuck")
    add(dev > L["asv_dev_alert_pct"], "CC_ASV_DEVIATION", "High",
        f"Recycle valve at {r['recycle_valve_pct']:.0f} % while the anti-surge controller asks {r['asc_output_pct']:.0f} %", "anti-surge", "asv_stuck")
    add(r["seal_gas_dp_bar"] < L["seal_gas_dp_alert_bar"], "CC_SEAL_GAS_DP_LOW", "High",
        f"Seal gas only {r['seal_gas_dp_bar']:.2f} bar over the reference pressure", "seal", "seal_gas_supply")
    add(t["vent_flow_max_nm3h"] > L["vent_flow_alert_nm3h"], "CC_SEAL_VENT_HIGH", "High",
        f"Primary vent flow {t['vent_flow_max_nm3h']:.1f} Nm³/h (DE {r['vent_flow_de_nm3h']:.1f}, NDE {r['vent_flow_ne_nm3h']:.1f})", "seal", "seal_primary_wear")
    add(t["vib_max_um"] > L["vib_alert_um"], "CC_VIBRATION_HIGH", "High", f"Shaft vibration {t['vib_max_um']:.0f} µm pp", "rotor", "rotor_unbalance")
    add(r["thrust_temp_c"] > L["thrust_temp_alert_c"], "CC_THRUST_TEMP_HIGH", "High", f"Thrust bearing at {r['thrust_temp_c']:.0f} °C", "bearing", "thrust_overload")
    add(lo <= sm < hi, "CC_SURGE_CONTROL_LINE", "Medium", f"Surge margin {sm:.1f} %: running on the anti-surge control line", "anti-surge", "surge_approach")
    add(t["eta_dev_pts"] < L["eta_dev_alert_pts"], "CC_EFFICIENCY_LOW", "Medium",
        f"Polytropic efficiency {t['eta_poly'] * 100:.1f} %, {t['eta_dev_pts']:+.1f} points against the map", "aero", "impeller_fouling")
    add(t["head_ratio"] < L["head_ratio_alert"], "CC_HEAD_LOW", "Medium",
        f"Polytropic head {t['head_poly_kjkg']:.0f} kJ/kg, {t['head_ratio']:.2f} × the map at this speed", "aero", "impeller_fouling")
    add(abs(t["power_ratio"] - 1) > L["power_dev_alert"], "CC_POWER_MISMATCH", "Medium",
        f"Shaft power {t['power_ratio']:.2f} × the gas power from P and T: check the instruments", "instrument", "discharge_tt_drift")
    add(abs(r["axial_pos_mm"]) > L["axial_alert_mm"], "CC_AXIAL_POSITION", "Medium", f"Rotor axial position {r['axial_pos_mm']:+.2f} mm", "bearing", "thrust_overload")
    add(max(r["brg_temp_de_c"], r["brg_temp_ne_c"]) > L["journal_temp_alert_c"], "CC_BEARING_TEMP_HIGH", "Medium",
        f"Journal bearing at {max(r['brg_temp_de_c'], r['brg_temp_ne_c']):.0f} °C", "bearing")
    add(r["recycle_valve_pct"] > L["recycle_open_alert_pct"], "CC_RECYCLE_OPEN", "Low",
        f"Recycle valve {r['recycle_valve_pct']:.0f} % open: gas compressed twice", "anti-surge", "surge_approach")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
