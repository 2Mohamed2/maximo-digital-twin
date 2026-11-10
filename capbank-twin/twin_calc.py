"""The shunt capacitor bank twin's expectations (CAP-1101: 24 Vishay ESTA 10.1 kV / 400 kvar internally fused units,
33 kV ungrounded double-wye with neutral unbalance protection, current-limiting series reactors).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (twin viewer, tests)

Bank physics:
  reactive power          Q = V_LL^2 * w * C_phase   (C_phase = both wyes' legs of one phase in parallel)
  per leg                 2 series levels x 2 parallel units; per unit S series groups x N parallel elements,
                          each element protected by its own internal fuse
  blown fuses             f elements lost in one group: that group keeps (N - f)/N of its capacitance, so it takes a
                          larger share of the unit voltage:  V_group / V_group,healthy = S * a / (S - 1 + a),  a = N / (N - f)
                          (the remaining elements of that group see this overvoltage; IEC 60871-1 allows 1.10 Un)
  neutral unbalance       ungrounded double wye, neutrals tied through a CT: a leg admittance change dY gives
                          In = |dY| V_ph 3Y / (6Y + dY)   (exact phasor solution in bank_circuit(); the IEEE C37.99
                          method: compute In per failed element, alarm on the first, trip before the remaining elements
                          pass 110 % voltage)
  cross-check             the same failures make the three phase currents unequal; their spread is a second, independent
                          estimate of failed elements. A neutral reading of ~0 with a clear phase spread means the
                          unbalance protection is blind (CT circuit open)
  harmonics               parallel resonance of the bank with the network at h_r = sqrt(Ssc / Q); currents at h near h_r
                          are amplified. IEEE 18 continuous limits: 110 % rms voltage, 120 % peak voltage,
                          135 % rms current, 135 % kvar
  series reactor          expected temperature = ambient + dT_rated * (I_rms / I_rated)^2
"""
import cmath
import math

W = 2 * math.pi * 50


def _k(twin):
    d = twin["design"]
    u, b, p = d["unit"], d["bank"], d["protection"]
    return dict(S=u["series_groups"], N=u["elements_per_group"], cu=u["capacitance_uf"], un=u["rated_kv"],
                cph=b["capacitance_per_phase_uf"], vn=b["nominal_kv"], lvl=b["series_levels"],
                iph=b["rated_phase_current_a"], inh=p["inherent_unbalance_a_per_kv"], k1=p["neutral_a_per_element_per_kv"],
                a1=p["asym_pct_per_element"], ssc=d["network"]["ssc_mva"], dtr=d["reactor"]["dt_rated_k"],
                ir=d["reactor"]["rated_current_a"])


# ---------------------------------------------------------------- exact bank circuit (build, physics, viewer table)
def unit_c(cu, S, N, f):
    """Capacitance of one unit (uF) with f blown fuses in one of its S groups."""
    if f <= 0:
        return cu
    f = min(f, N - 1)
    return S * cu / (S - 1 + N / (N - f))


def bank_circuit(v_ll_kv, legs_c_uf):
    """Ungrounded double wye, neutrals tied through the unbalance CT.
    legs_c_uf: {"A": [Ca, Cb, Cc], "B": [Ca, Cb, Cc]} leg capacitances in uF.
    Returns phase currents (A, rms), neutral current (A), reactive power (Mvar)."""
    vph = v_ll_kv * 1000 / math.sqrt(3)
    V = [cmath.rect(vph, 0), cmath.rect(vph, -2 * math.pi / 3), cmath.rect(vph, 2 * math.pi / 3)]
    Y = {g: [1j * W * c * 1e-6 for c in legs_c_uf[g]] for g in ("A", "B")}
    ysum = sum(Y["A"]) + sum(Y["B"])
    vn = (sum(y * v for y, v in zip(Y["A"], V)) + sum(y * v for y, v in zip(Y["B"], V))) / ysum
    ia = [y * (v - vn) for y, v in zip(Y["A"], V)]
    ib = [y * (v - vn) for y, v in zip(Y["B"], V)]
    iph = [a + b for a, b in zip(ia, ib)]
    i_n = sum(ia)
    q = sum(((v - vn) * ((a + b).conjugate())).imag for v, a, b in zip(V, ia, ib)) / 1e6
    return {"i_phase": [abs(x) for x in iph], "i_neutral": abs(i_n), "q_mvar": -q}


def leg_c(cu, S, N, f, levels=2, parallel=2):
    """Leg capacitance (uF): `levels` series levels of `parallel` units; f failures in the first unit of level 1."""
    lv1 = unit_c(cu, S, N, f) + (parallel - 1) * cu
    lv = parallel * cu
    return 1 / (1 / lv1 + (levels - 1) / lv)


def group_overvoltage(S, N, f):
    """Voltage on the remaining elements of a group with f blown fuses, relative to healthy (1.0 = no change)."""
    f = max(0.0, min(f, N - 1))
    a = N / (N - f)
    return S * a / (S - 1 + a)


def amplification(h, h_r, q_damp=8.0):
    """Harmonic current amplification of the bank against the network (damped parallel resonance)."""
    x = h / h_r
    return 1 / math.sqrt((1 - x * x) ** 2 + (x / q_damp) ** 2)


# ---------------------------------------------------------------- Monitor expressions
def _parts(twin):
    k = _k(twin)
    V = "df['BUS_VOLTAGE_KV']"
    QE = f"({V} ** 2 * {W} * {k['cph']} * 1e-6)"
    IM = "((df['BANK_CURRENT_L1_A'] + df['BANK_CURRENT_L2_A'] + df['BANK_CURRENT_L3_A']) / 3)"
    IMAX = "np.maximum(np.maximum(df['BANK_CURRENT_L1_A'], df['BANK_CURRENT_L2_A']), df['BANK_CURRENT_L3_A'])"
    IMIN = "np.minimum(np.minimum(df['BANK_CURRENT_L1_A'], df['BANK_CURRENT_L2_A']), df['BANK_CURRENT_L3_A'])"
    ASYM = f"(({IMAX} - {IMIN}) / {IM}.clip(lower=1) * 100)"
    INC = f"(df['NEUTRAL_CURRENT_A'] - {k['inh']} * {V}).clip(lower=0)"
    FE = f"({INC} / ({k['k1']} * {V}.clip(lower=1)))"
    FA = f"(({ASYM} - 0.0) / {k['a1']})"
    FEC = f"{FE}.clip(lower=0, upper={k['N'] - 1})"
    A = f"({k['N']} / ({k['N']} - {FEC}))"
    OV = f"({k['S']} * {A} / ({k['S'] - 1} + {A}))"
    UPU = f"({V} / {math.sqrt(3)} / {k['lvl']} / {k['un']})"
    IRMS = f"({IM} / {k['iph']})"
    RTE = f"(df['AMBIENT_TEMP_C'] + {k['dtr']} * ({IM} / {k['ir']}) ** 2)"
    return dict(QE=QE, IM=IM, ASYM=ASYM, INC=INC, FE=FE, FA=FA, OV=OV, UPU=UPU, IRMS=IRMS, RTE=RTE, k=k)


def monitor_expressions(twin):
    p, k = _parts(twin), _k(twin)
    return [
        ("Q_EXPECTED_MVAR", p["QE"]),
        ("Q_DEVIATION_PCT", f"np.where(df['BREAKER_CLOSED'] > 0, (df['BANK_Q_MVAR'] / {p['QE']} - 1) * 100, 0)"),
        ("CURRENT_EXPECTED_A", f"df['BREAKER_CLOSED'] * {p['QE']} * 1e6 / ({math.sqrt(3)} * df['BUS_VOLTAGE_KV'].clip(lower=1) * 1000)"),
        ("CURRENT_RMS_PU", p["IRMS"]),
        ("UNIT_VOLTAGE_PU", p["UPU"]),
        ("NEUTRAL_COMPENSATED_A", p["INC"]),
        ("FAILED_ELEMENTS_EST", p["FE"]),
        ("PHASE_ASYMMETRY_PCT", p["ASYM"]),
        ("FAILED_FROM_ASYMMETRY", p["FA"]),
        ("ELEMENT_OVERVOLTAGE_PCT", f"({p['OV']} - 1) * 100"),
        ("ELEMENT_VOLTAGE_PU", f"{p['UPU']} * {p['OV']}"),
        ("REACTOR_TEMP_EXPECTED_C", p["RTE"]),
        ("REACTOR_RESIDUAL_K", f"df['REACTOR_TEMP_C'] - {p['RTE']}"),
        ("RESONANCE_ORDER", f"np.sqrt({k['ssc']} / df['BANK_Q_MVAR'].clip(lower=0.1))"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    V = r["bus_voltage_kv"]
    qe = V ** 2 * W * k["cph"] * 1e-6
    im = (r["bank_current_l1_a"] + r["bank_current_l2_a"] + r["bank_current_l3_a"]) / 3
    imax = max(r["bank_current_l1_a"], r["bank_current_l2_a"], r["bank_current_l3_a"])
    imin = min(r["bank_current_l1_a"], r["bank_current_l2_a"], r["bank_current_l3_a"])
    asym = (imax - imin) / max(im, 1) * 100
    inc = max(0.0, r["neutral_current_a"] - k["inh"] * V)
    fe = inc / (k["k1"] * max(V, 1))
    ov = group_overvoltage(k["S"], k["N"], fe)
    upu = V / math.sqrt(3) / k["lvl"] / k["un"]
    rte = r["ambient_temp_c"] + k["dtr"] * (im / k["ir"]) ** 2
    closed = r["breaker_closed"] > 0
    return {
        "q_expected_mvar": qe,
        "q_deviation_pct": (r["bank_q_mvar"] / qe - 1) * 100 if closed else 0.0,
        "current_expected_a": r["breaker_closed"] * qe * 1e6 / (math.sqrt(3) * max(V, 1) * 1000),
        "current_rms_pu": im / k["iph"],
        "unit_voltage_pu": upu,
        "neutral_compensated_a": inc,
        "failed_elements_est": fe,
        "phase_asymmetry_pct": asym,
        "failed_from_asymmetry": asym / k["a1"],
        "element_overvoltage_pct": (ov - 1) * 100,
        "element_voltage_pu": upu * ov,
        "reactor_temp_expected_c": rte,
        "reactor_residual_k": r["reactor_temp_c"] - rte,
        "resonance_order": math.sqrt(k["ssc"] / max(r["bank_q_mvar"], 0.1)),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    CL = "(df['BREAKER_CLOSED'] > 0)"
    return [
        ("CAP_ELEMENT_FAILURES", f"{CL} & ({p['FE']} >= {L['failed_alarm']}) & ({p['FE']} < {L['failed_trip']})", "Medium", "element_failures"),
        ("CAP_UNBALANCE_TRIP_LEVEL", f"{CL} & ({p['FE']} >= {L['failed_trip']})", "High", "element_failures"),
        ("CAP_PROTECTION_BLIND", f"{CL} & ({p['FA']} >= {L['blind_asym_elements']}) & ({p['FE']} < {L['failed_alarm']})", "High", "neutral_ct_fault"),
        ("CAP_UNIT_PRESSURE", "df['PRESSURE_SWITCH_COUNT'] > 0", "High", "can_bulging"),
        ("CAP_Q_LOW", f"{CL} & ((df['BANK_Q_MVAR'] / {p['QE']} - 1) * 100 < {L['q_low_pct']})", "Medium", "element_failures"),
        ("CAP_OVERVOLTAGE", f"{CL} & ({p['UPU']} > {L['unit_voltage_alert_pu']})", "Medium", "overvoltage_stress"),
        ("CAP_PEAK_VOLTAGE", f"{CL} & (df['PEAK_VOLTAGE_PU'] > {L['peak_voltage_pu']})", "High", "overvoltage_stress"),
        ("CAP_HARMONIC_CURRENT", f"{CL} & ((df['CURRENT_THD_PCT'] > {L['current_thd_alert_pct']}) | ({p['IRMS']} > {L['rms_current_pu']}))", "Medium", "harmonic_resonance"),
        ("CAP_REACTOR_HOT", f"{CL} & ({p['IRMS']} > 0.5) & ((df['REACTOR_TEMP_C'] - {p['RTE']}) > {L['reactor_residual_alert_k']})", "Medium", "reactor_overheating"),
        ("CAP_RESTRIKE", f"df['LAST_SWITCH_OVERVOLTAGE_PU'] > {L['switch_overvoltage_alert_pu']}", "High", "restrike"),
        ("CAP_AMBIENT_HIGH", f"df['AMBIENT_TEMP_C'] > {L['ambient_alert_c']}", "Low", None),
        ("CAP_RELAY_ALARM", "df['RELAY_STATUS'] == 1", "Medium", None),
        ("CAP_RELAY_TRIP", "df['RELAY_STATUS'] >= 2", "Critical", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    cl = r["breaker_closed"] > 0
    fe, fa = t["failed_elements_est"], t["failed_from_asymmetry"]
    add(r["relay_status"] >= 2, "CAP_RELAY_TRIP", "Critical", "Unbalance protection tripped the bank breaker", "relay")
    add(r["relay_status"] == 1, "CAP_RELAY_ALARM", "Medium", "Unbalance protection alarm stage", "relay")
    add(cl and L["failed_alarm"] <= fe < L["failed_trip"], "CAP_ELEMENT_FAILURES", "Medium",
        f"Neutral {t['neutral_compensated_a']:.3f} A = about {fe:.1f} blown element fuse(s); the rest of that group runs at "
        f"+{t['element_overvoltage_pct']:.1f} % voltage", "units", "element_failures")
    add(cl and fe >= L["failed_trip"], "CAP_UNBALANCE_TRIP_LEVEL", "High",
        f"About {fe:.1f} blown fuses in one group: remaining elements at +{t['element_overvoltage_pct']:.1f} % (trip level > 10 %)", "units", "element_failures")
    add(cl and fa >= L["blind_asym_elements"] and fe < L["failed_alarm"], "CAP_PROTECTION_BLIND", "High",
        f"Phase currents differ by {t['phase_asymmetry_pct']:.2f} % (about {fa:.1f} failed elements) but the neutral CT reads "
        f"{r['neutral_current_a']:.3f} A: unbalance protection is blind", "neutral_ct", "neutral_ct_fault")
    add(r["pressure_switch_count"] > 0, "CAP_UNIT_PRESSURE", "High",
        f"{r['pressure_switch_count']} unit pressure switch(es) operated: a can is bulging", "units", "can_bulging")
    add(cl and t["q_deviation_pct"] < L["q_low_pct"], "CAP_Q_LOW", "Medium",
        f"Bank gives {t['q_deviation_pct']:.1f} % less Mvar than Q = V²ωC expects", "units", "element_failures")
    add(cl and t["unit_voltage_pu"] > L["unit_voltage_alert_pu"], "CAP_OVERVOLTAGE", "Medium",
        f"Units at {t['unit_voltage_pu'] * 100:.0f} % of rated voltage (bus {r['bus_voltage_kv']:.1f} kV)", "bus", "overvoltage_stress")
    add(cl and r["peak_voltage_pu"] > L["peak_voltage_pu"], "CAP_PEAK_VOLTAGE", "High",
        f"Peak voltage {r['peak_voltage_pu'] * 100:.0f} % of rated (IEEE 18 limit 120 %)", "bus", "overvoltage_stress")
    add(cl and (r["current_thd_pct"] > L["current_thd_alert_pct"] or t["current_rms_pu"] > L["rms_current_pu"]), "CAP_HARMONIC_CURRENT", "Medium",
        f"Bank current THD {r['current_thd_pct']:.0f} % (7th {r['current_h7_pct']:.0f} %), rms {t['current_rms_pu'] * 100:.0f} % of rated; "
        f"resonance near h = {t['resonance_order']:.1f}", "reactor", "harmonic_resonance")
    add(cl and t["current_rms_pu"] > 0.5 and t["reactor_residual_k"] > L["reactor_residual_alert_k"], "CAP_REACTOR_HOT", "Medium",
        f"Series reactor {r['reactor_temp_c']:.0f} °C, {t['reactor_residual_k']:.0f} K above expected", "reactor", "reactor_overheating")
    add(r["last_switch_overvoltage_pu"] > L["switch_overvoltage_alert_pu"], "CAP_RESTRIKE", "High",
        f"Last de-energisation reached {r['last_switch_overvoltage_pu']:.1f} pu: the breaker restruck", "breaker", "restrike")
    add(r["ambient_temp_c"] > L["ambient_alert_c"], "CAP_AMBIENT_HIGH", "Low",
        f"Ambient {r['ambient_temp_c']:.0f} °C above the units' +{L['ambient_alert_c']} °C temperature category", "units")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
