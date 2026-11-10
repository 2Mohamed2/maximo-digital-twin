"""The transmission main twin's expectations (PIPE-1501, DN 1200 ductile iron, Saint-Gobain PAM NATURAL C25).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (twin viewer, tests)

Hydraulics (steady, incompressible):
  v = Q / (pi D^2 / 4),   Re = v D / nu(T),   nu = 1.792e-6 / (1 + 0.0337 T + 0.000221 T^2)
  Swamee-Jain   f = 0.25 / log10(k / (3.7 D) + 5.74 / Re^0.9)^2          (explicit Colebrook, k = design roughness)
  friction slope S = f / D * v^2 / (2 g)   [m head per m of pipe];  expected head loss = S L
  head at a transmitter H = z + p / (rho g)  [p in bar: 1 m = 0.0979 bar]
  expected pressure at station i, from PT-0 and the inlet flow:  p_i = p_0 + (z_0 - z_i - S x_i) * rho g
  segment slope ratio r_j = measured head drop over segment j / (S * segment length)    (1 = as designed)
  effective Hazen-Williams C (SI): C = (10.67 L Q^1.852 / (hf D^4.8704))^(1/1.852)
  effective roughness: invert Swamee-Jain with the measured f:  k = 3.7 D (10^(-0.5/sqrt f) - 5.74 / Re^0.9)
Leak / meter logic:
  mass balance (Q_in - Q_out) / Q_in; with a leak at x the line carries Q_in up to x and Q_out after it, so
  hf_measured = S(Q_in) x + S(Q_out) (L - x)  ->  x = (hf_measured - S(Q_out) L) / (S(Q_in) - S(Q_out))
  a leak also lifts the outlet pressure above the no-leak expectation (less flow, less friction downstream);
  a drifting outlet meter opens the balance but leaves every pressure where the inlet flow says it should be.
  leak signal = what a leak of the imbalance size at mid-line would add to the outlet pressure, (S(Q_in) - S(Q_out)) L/2;
  a real leak at x adds (L - x)/(L/2) of it, a meter adds nothing: the rule splits at 0.42 x the signal, and only when
  the signal is above the transmitters' noise (0.035 bar), otherwise only the mass-balance alert is raised.
Transients: Joukowsky potential surge dp = rho a v (a from the Korteweg formula in the twin file); the high-rate
  loggers report the minute's highest pressure at the pump station and lowest at the high point.
"""
import math

G = 9.80665


def _k(twin):
    d = twin["design"]
    p, h, st = d["pipe"], d["hydraulics"], d["route"]["stations"]
    return dict(D=p["id_m"], L=h["length_m"], k=h["k_design_mm"] / 1000, bpm=h["bar_per_m"], rho=h["rho_kg_m3"],
                A=math.pi * p["id_m"] ** 2 / 4, z=[s["z"] for s in st], x=[s["ch"] for s in st], a=d["transients"]["wave_speed_ms"],
                pfa=p["pfa_bar"], pma=p["pma_bar"])


P_COLS = ["PRESSURE_PS_BAR", "PRESSURE_PT1_BAR", "PRESSURE_PT2_BAR", "PRESSURE_PT3_BAR", "PRESSURE_RES_BAR"]
P_KEYS = [c.lower() for c in P_COLS]


def nu(t):
    return 1.792e-6 / (1 + 0.0337 * t + 0.000221 * t * t)


def slope(k, q_m3h, t):
    """friction slope (m/m) at a flow (m3/h) and water temperature, Darcy-Weisbach + Swamee-Jain."""
    q = max(q_m3h, 1.0) / 3600
    v = q / k["A"]
    re = v * k["D"] / nu(t)
    f = 0.25 / math.log10(k["k"] / (3.7 * k["D"]) + 5.74 / re ** 0.9) ** 2
    return f / k["D"] * v * v / (2 * G)


def _parts(twin):
    k = _k(twin)
    D, L, A, bpm = k["D"], k["L"], k["A"], k["bpm"]
    T = "df['WATER_TEMP_C']"
    NU = f"(1.792e-6 / (1 + 0.0337 * {T} + 0.000221 * {T} ** 2))"

    def sl(qcol):
        Q = f"(df['{qcol}'].clip(lower=1) / 3600)"
        V = f"({Q} / {A})"
        RE = f"({V} * {D} / {NU})"
        F = f"(0.25 / np.log10({k['k'] / (3.7 * D)} + 5.74 / {RE} ** 0.9) ** 2)"
        return dict(Q=Q, V=V, RE=RE, F=F, S=f"({F} / {D} * {V} ** 2 / {2 * G})")
    i, o = sl("FLOW_IN_M3H"), sl("FLOW_OUT_M3H")
    H = [f"({z} + df['{c}'] / {bpm})" for z, c in zip(k["z"], P_COLS)]
    HLM = f"({H[0]} - {H[4]})"
    HLE = f"({i['S']} * {L})"
    PEXP = [f"(df['PRESSURE_PS_BAR'] + ({k['z'][0]} - {k['z'][j]} - {i['S']} * {k['x'][j]}) * {bpm})" for j in range(5)]
    R = [f"(({H[j - 1]} - {H[j]}) / ({i['S']} * {k['x'][j] - k['x'][j - 1]}))" for j in range(1, 5)]
    IMB = "((df['FLOW_IN_M3H'] - df['FLOW_OUT_M3H']) / df['FLOW_IN_M3H'].clip(lower=1) * 100)"
    CE = f"(({10.67 * L} * {i['Q']} ** 1.852 / ({HLM}.clip(lower=0.01) * {D ** 4.8704})) ** (1 / 1.852))"
    CD = f"(({10.67 * L} * {i['Q']} ** 1.852 / ({HLE} * {D ** 4.8704})) ** (1 / 1.852))"
    FM = f"({HLM}.clip(lower=0.01) * {D * 2 * G} / ({L} * {i['V']} ** 2))"
    KE = f"(1000 * {3.7 * D} * (10 ** (-0.5 / np.sqrt({FM})) - 5.74 / {i['RE']} ** 0.9)).clip(lower=0)"
    XL = f"((({HLM} - {o['S']} * {L}) / ({i['S']} - {o['S']}).clip(lower=1e-9)) / 1000).clip(lower=0, upper={L / 1000})"
    JK = f"({k['rho'] * k['a'] / 1e5} * {i['V']})"
    LS = f"(({i['S']} - {o['S']}) * {L / 2 * bpm})"
    return dict(k=k, i=i, o=o, H=H, HLM=HLM, HLE=HLE, PEXP=PEXP, R=R, IMB=IMB, CE=CE, CD=CD, KE=KE, XL=XL, JK=JK, LS=LS)


def monitor_expressions(twin):
    p = _parts(twin)
    i = p["i"]
    out = [
        ("VELOCITY_MS", i["V"]),
        ("REYNOLDS", i["RE"]),
        ("FRICTION_FACTOR", i["F"]),
        ("HEADLOSS_EXPECTED_M", p["HLE"]),
        ("HEADLOSS_MEASURED_M", p["HLM"]),
        ("HEADLOSS_RATIO", f"{p['HLM']} / {p['HLE']}"),
        ("C_EFFECTIVE", p["CE"]),
        ("C_DESIGN", p["CD"]),
        ("K_EFFECTIVE_MM", p["KE"]),
        ("IMBALANCE_PCT", p["IMB"]),
        ("IMBALANCE_M3H", "df['FLOW_IN_M3H'] - df['FLOW_OUT_M3H']"),
    ]
    names = ["PT1", "PT2", "PT3", "RES"]
    for j, n in enumerate(names, start=1):
        out.append((f"P_EXP_{n}_BAR", p["PEXP"][j]))
    for j, n in enumerate(["PT1", "PT2", "PT3", "OUT"], start=1):
        out.append((f"RES_{n}_BAR", f"df['{P_COLS[j]}'] - {p['PEXP'][j]}"))
    for j in range(4):
        out.append((f"SLOPE_RATIO_{j + 1}", p["R"][j]))
    out += [
        ("LEAK_CH_KM", p["XL"]),
        ("LEAK_SIGNAL_BAR", p["LS"]),
        ("JOUKOWSKY_BAR", p["JK"]),
        ("SURGE_MARGIN_BAR", f"{p['k']['pma']} - df['SURGE_PMAX_BAR']"),
    ]
    return out


def evaluate(twin, r):
    k = _k(twin)
    D, L, A, bpm = k["D"], k["L"], k["A"], k["bpm"]
    t = r["water_temp_c"]
    qi, qo = r["flow_in_m3h"], r["flow_out_m3h"]
    q = max(qi, 1.0) / 3600
    v = q / A
    re = v * D / nu(t)
    f = 0.25 / math.log10(k["k"] / (3.7 * D) + 5.74 / re ** 0.9) ** 2
    s = f / D * v * v / (2 * G)
    so = slope(k, qo, t)
    H = [z + r[c] / bpm for z, c in zip(k["z"], P_KEYS)]
    hlm, hle = H[0] - H[4], s * L
    pexp = [r["pressure_ps_bar"] + (k["z"][0] - k["z"][j] - s * k["x"][j]) * bpm for j in range(5)]
    rat = [(H[j - 1] - H[j]) / (s * (k["x"][j] - k["x"][j - 1])) for j in range(1, 5)]
    hl_c = max(hlm, 0.01)
    fm = hl_c * D * 2 * G / (L * v * v)
    ke = max(0.0, 1000 * 3.7 * D * (10 ** (-0.5 / math.sqrt(fm)) - 5.74 / re ** 0.9))
    xl = min(max((hlm - so * L) / max(s - so, 1e-9) / 1000, 0.0), L / 1000)
    out = {
        "velocity_ms": v, "reynolds": re, "friction_factor": f, "headloss_expected_m": hle, "headloss_measured_m": hlm,
        "headloss_ratio": hlm / hle,
        "c_effective": (10.67 * L * q ** 1.852 / (hl_c * D ** 4.8704)) ** (1 / 1.852),
        "c_design": (10.67 * L * q ** 1.852 / (hle * D ** 4.8704)) ** (1 / 1.852),
        "k_effective_mm": ke, "imbalance_pct": (qi - qo) / max(qi, 1) * 100, "imbalance_m3h": qi - qo,
        "leak_ch_km": xl, "leak_signal_bar": (s - so) * L / 2 * bpm, "joukowsky_bar": k["rho"] * k["a"] / 1e5 * v, "surge_margin_bar": k["pma"] - r["surge_pmax_bar"],
    }
    for j, n in enumerate(["pt1", "pt2", "pt3", "res"], start=1):
        out[f"p_exp_{n}_bar"] = pexp[j]
    for j, n in enumerate(["pt1", "pt2", "pt3", "out"], start=1):
        out[f"res_{n}_bar"] = r[P_KEYS[j]] - pexp[j]
    for j in range(4):
        out[f"slope_ratio_{j + 1}"] = rat[j]
    return out


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    R, IMB, LS = p["R"], p["IMB"], p["LS"]
    nm = L["slope_neighbour_min"]
    QOK = f"(df['FLOW_IN_M3H'] > {L['q_min_m3h']})"
    RES = f"(df['PRESSURE_RES_BAR'] - {p['PEXP'][4]})"
    dev = L["slope_dev_alert"]
    lo = L["slope_low"]
    tx = " | ".join(f"(({R[j]} < {lo}) & ({R[j + 1]} > {2 - lo})) | (({R[j]} > {2 - lo}) & ({R[j + 1]} < {lo}))" for j in range(3))
    return [
        ("PIPE_MASS_BALANCE", f"{QOK} & ({IMB} > {L['imbalance_alert_pct']})", "Medium", None),
        ("PIPE_LEAK", f"{QOK} & ({IMB} > {L['imbalance_alert_pct']}) & ({LS} > {L['leak_signal_min_bar']}) & ({RES} > {L['leak_split']} * {LS})", "High", "leak"),
        ("PIPE_FLOW_METER_DRIFT", f"{QOK} & ({IMB} > {L['meter_drift_imbalance_pct']}) & ({LS} > {L['leak_signal_min_bar']}) & ({RES} <= {L['leak_split']} * {LS})", "Medium", "meter_drift"),
        ("PIPE_ROUGHNESS", f"{QOK} & ({p['CE']} < {L['c_effective_alert']}) & ({IMB}.abs() < {L['imbalance_alert_pct']}) & "
                           f"({R[0]} > 1.15) & ({R[1]} > 1.15) & ({R[2]} > 1.15) & ({R[3]} > 1.15)", "Medium", "tuberculation"),
        ("PIPE_AIR_POCKET", f"{QOK} & (({R[1]} - ({R[0]} + {R[2]} + {R[3]}) / 3) > {dev}) & ({R[0]} > {nm}) & ({R[2]} > {nm})", "Medium", "air_pocket"),
        ("PIPE_VALVE_THROTTLED", f"{QOK} & (({R[2]} - ({R[0]} + {R[1]} + {R[3]}) / 3) > {dev}) & ({R[1]} > {nm}) & ({R[3]} > {nm})", "Medium", "valve_throttled"),
        ("PIPE_TRANSMITTER_SUSPECT", f"{QOK} & ({tx})", "Low", "transmitter_fault"),
        ("PIPE_SURGE_ABOVE_PFA", f"df['SURGE_PMAX_BAR'] > {L['pfa_bar']}", "High", "surge_protection"),
        ("PIPE_COLUMN_SEPARATION", f"df['SURGE_PMIN_HP_BAR'] < {L['vacuum_alert_bar']}", "High", "surge_protection"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}
PT_NAMES = ["PT-1", "PT-2", "PT-3"]


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    qok = r["flow_in_m3h"] > L["q_min_m3h"]
    imb, res = t["imbalance_pct"], t["res_out_bar"]
    R = [t[f"slope_ratio_{j}"] for j in range(1, 5)]
    lo, dev, nm = L["slope_low"], L["slope_dev_alert"], L["slope_neighbour_min"]
    ls, split = t["leak_signal_bar"], L["leak_split"]
    add(qok and imb > L["imbalance_alert_pct"], "PIPE_MASS_BALANCE", "Medium",
        f"{t['imbalance_m3h']:.0f} m³/h ({imb:.1f} %) leave the pump station but do not reach the reservoir", "line")
    add(qok and imb > L["imbalance_alert_pct"] and ls > L["leak_signal_min_bar"] and res > split * ls, "PIPE_LEAK", "High",
        f"Leak of about {t['imbalance_m3h']:.0f} m³/h near km {t['leak_ch_km']:.1f} (outlet pressure {res * 1000:+.0f} mbar vs. no-leak hydraulics)", "leak", "leak")
    add(qok and imb > L["meter_drift_imbalance_pct"] and ls > L["leak_signal_min_bar"] and res <= split * ls, "PIPE_FLOW_METER_DRIFT", "Medium",
        f"Mass balance {imb:.1f} % but the outlet pressure ({res * 1000:+.0f} mbar) shows no leak (a real one would lift it ~{ls * 1000:.0f} mbar): suspect FM-B", "meter_b", "meter_drift")
    add(qok and t["c_effective"] < L["c_effective_alert"] and abs(imb) < L["imbalance_alert_pct"] and min(R) > 1.15, "PIPE_ROUGHNESS", "Medium",
        f"Effective C {t['c_effective']:.0f} (design {t['c_design']:.0f}), k {t['k_effective_mm']:.2f} mm: the whole line loses {(t['headloss_ratio'] - 1) * 100:.0f} % more head", "pipe", "tuberculation")
    add(qok and R[1] - (R[0] + R[2] + R[3]) / 3 > dev and R[0] > nm and R[2] > nm, "PIPE_AIR_POCKET", "Medium",
        f"Extra head loss between PT-1 and PT-2 (x{R[1]:.2f} of design): air at high point HP-1, check air valve AV-3", "high_point", "air_pocket")
    add(qok and R[2] - (R[0] + R[1] + R[3]) / 3 > dev and R[1] > nm and R[3] > nm, "PIPE_VALVE_THROTTLED", "Medium",
        f"Extra head loss between PT-2 and PT-3 (x{R[2]:.2f} of design) while LV-2 reports {r['line_valve_pos_pct']:.0f} % open", "line_valve", "valve_throttled")
    sus = [PT_NAMES[j] for j in range(3) if (R[j] < lo and R[j + 1] > 2 - lo) or (R[j] > 2 - lo and R[j + 1] < lo)]
    add(qok and bool(sus), "PIPE_TRANSMITTER_SUSPECT", "Low",
        f"{', '.join(sus)} disagrees with both neighbours (head drop x{R[0]:.2f} / x{R[1]:.2f} / x{R[2]:.2f} / x{R[3]:.2f}): check the transmitter", "pt2", "transmitter_fault")
    add(r["surge_pmax_bar"] > L["pfa_bar"], "PIPE_SURGE_ABOVE_PFA", "High",
        f"Transient peak {r['surge_pmax_bar']:.1f} bar at the pump station, above PFA {L['pfa_bar']:.0f} bar (Joukowsky {t['joukowsky_bar']:.1f} bar)", "pump_station", "surge_protection")
    add(r["surge_pmin_hp_bar"] < L["vacuum_alert_bar"], "PIPE_COLUMN_SEPARATION", "High",
        f"Pressure at high point HP-1 fell to {r['surge_pmin_hp_bar']:.2f} bar: vapour cavity / column separation risk", "high_point", "surge_protection")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
