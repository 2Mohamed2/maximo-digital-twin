"""The LV feeder metering twin's expectations (AMI-7301: check meter, 24 smart meters, data concentrator).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Every reading is one 15-minute interval (dt = 0.25 h). Each expression works on that one reading only.

Energy balance:
    feeder energy  E_F = E_F1 + E_F2 + E_F3          (check meter at the transformer LV terminals)
    customer sum   E_C = E_C1 + E_C2 + E_C3          (head-end, per phase of the network model)
    technical loss E_T = dt x [ R_loss x (I1^2 + I2^2 + I3^2) + R_loss x IN^2 + P_meters ] / 1000
        R_loss = sum f_k^2 R_k + R_service / N        f_k = share of the customers beyond the start of section k
        P_meters = 3 x 0.45 W x N + concentrator (voltage circuits the customer meters do not register)
    unexplained (non-technical) loss  NTL = E_F - E_C - E_T,   NTL % = 100 x NTL / E_F
    per phase: NTL_p % = 100 x (E_Fp - E_Cp - E_Tp) / (E_F / 3), E_Tp = dt (R_loss Ip^2 + R_loss IN^2 / 3 + P_meters / 3)
  The transformer losses (no-load + load x (S/Sr)^2) are upstream of the check meter: shown, never subtracted.
  The balance is only judged when every meter was read (coverage >= 99 %); the phase split only when the neutral is sound
  (a shifted neutral moves power between the phases by itself).
Voltage along the feeder (simple radial load flow with the measured head currents):
    V_end expected = V_bus avg - I avg x (R_drop cos phi + X_drop sin phi),  R_drop = sum f_k R_k + R_service / N
    cos phi = P / (V I) from the check meter.  The average of the three phase voltages hardly moves when the neutral point
    shifts (the three projections cancel), so the residual of the average sees the phase conductors; the spread of the
    three end voltages, beyond what the current unbalance explains, sees the neutral:
    spread excess = (max - min of V_end) - (max - min of V_bus) - (I max - I min) x R_drop - sqrt(3) x IN x R_drop
  EN 50160 (as commonly quoted): 230 V +/- 10 % -> 207 to 253 V for 10-minute means.
"""

SQ3 = 1.7320508075688772


def _g(v):
    """The constant exactly as it is written into the Monitor expression (6 significant digits)."""
    return float(f"{v:.6g}")


def _k(twin):
    d = twin["design"]
    n, t, m = d["network"], d["transformer"], d["meters"]
    dv = n["derived"]
    dt = m["interval_min"] / 60.0
    pm = 3 * m["meter_w_per_phase"] * m["n_meters"] + m["concentrator_w"]
    return dict(dt=dt, n=m["n_meters"], rl=dv["r_loss_ohm"], rd=dv["r_drop_ohm"], xd=dv["x_drop_ohm"], pm=pm,
                sr=t["rating_kva"], pk=t["pk_w"], po=t["po_w"], vn=n["voltage_nominal_v"], v0=n["no_load_v"])


def _parts(twin):
    k = _k(twin)
    c = lambda s: f"df['{s.upper()}']"
    FK = f"({c('feeder_kwh_l1')} + {c('feeder_kwh_l2')} + {c('feeder_kwh_l3')})"
    CK = f"({c('cust_kwh_l1')} + {c('cust_kwh_l2')} + {c('cust_kwh_l3')})"
    COV = f"({c('reads_ok')} / {k['n']} * 100)"
    a = k["dt"] / 1000
    TL = (f"({a:.6g} * ({k['rl']} * ({c('feeder_i_l1')} ** 2 + {c('feeder_i_l2')} ** 2 + {c('feeder_i_l3')} ** 2)"
          f" + {k['rl']} * {c('feeder_i_n')} ** 2 + {k['pm']:.6g}))")
    NTL = f"({FK} - {CK} - {TL})"
    NTLP = f"({NTL} / {FK} * 100)"

    def ph(p):
        return (f"(({c('feeder_kwh_l' + p)} - {c('cust_kwh_l' + p)} - {a:.6g} * ({k['rl']} * {c('feeder_i_l' + p)} ** 2"
                f" + {k['rl'] / 3:.6g} * {c('feeder_i_n')} ** 2 + {k['pm'] / 3:.6g})) / ({FK} / 3) * 100)")
    P1, P2, P3 = ph("1"), ph("2"), ph("3")
    mx = lambda x, y, z: f"np.maximum(np.maximum({x}, {y}), {z})"
    mn = lambda x, y, z: f"np.minimum(np.minimum({x}, {y}), {z})"
    SPR = f"({mx(P1, P2, P3)} - {mn(P1, P2, P3)})"
    VB = f"(({c('v_bus_l1')} + {c('v_bus_l2')} + {c('v_bus_l3')}) / 3)"
    VE = f"(({c('v_end_l1')} + {c('v_end_l2')} + {c('v_end_l3')}) / 3)"
    IA = f"(({c('feeder_i_l1')} + {c('feeder_i_l2')} + {c('feeder_i_l3')}) / 3)"
    VI = f"({c('v_bus_l1')} * {c('feeder_i_l1')} + {c('v_bus_l2')} * {c('feeder_i_l2')} + {c('v_bus_l3')} * {c('feeder_i_l3')})"
    PF = f"np.minimum({FK} * 1000 / {k['dt']} / {VI}, 1)"
    VEX = f"({VB} - {IA} * ({k['rd']} * {PF} + {k['xd']} * np.sqrt(1 - {PF} ** 2)))"
    ve = [c(f"v_end_l{i}") for i in "123"]
    vb = [c(f"v_bus_l{i}") for i in "123"]
    ii = [c(f"feeder_i_l{i}") for i in "123"]
    SPX = (f"(({mx(*ve)} - {mn(*ve)}) - ({mx(*vb)} - {mn(*vb)}) - ({mx(*ii)} - {mn(*ii)}) * {k['rd']}"
           f" - {SQ3 * k['rd']:.6g} * {c('feeder_i_n')})")
    LD = f"({VI} / 1000 / {k['sr']} * 100)"
    return dict(k=k, FK=FK, CK=CK, COV=COV, TL=TL, NTL=NTL, NTLP=NTLP, P1=P1, P2=P2, P3=P3, SPR=SPR, VB=VB, VE=VE, VEX=VEX,
                SPX=SPX, LD=LD)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    L = twin["twin_model"]["limits"]
    return [
        ("FEEDER_KWH", p["FK"]),
        ("CUST_KWH", p["CK"]),
        ("READ_COVERAGE_PCT", p["COV"]),
        ("TECH_LOSS_KWH", p["TL"]),
        ("TECH_LOSS_PCT", f"{p['TL']} / {p['FK']} * 100"),
        ("NTL_KWH", p["NTL"]),
        ("NTL_PCT", p["NTLP"]),
        ("NTL_L1_PCT", p["P1"]),
        ("NTL_L2_PCT", p["P2"]),
        ("NTL_L3_PCT", p["P3"]),
        ("PHASE_SPREAD_PCT", p["SPR"]),
        ("V_BUS_AVG", p["VB"]),
        ("V_END_EXPECTED", p["VEX"]),
        ("V_END_RESIDUAL", f"{p['VE']} - {p['VEX']}"),
        ("V_END_SPREAD_EXCESS", p["SPX"]),
        ("V_MAX_HEADROOM", f"{L['en50160_high_v']} - df['V_MAX_CUST']"),
        ("V_MIN_HEADROOM", f"df['V_MIN_CUST'] - {L['en50160_low_v']}"),
        ("TRAFO_LOAD_PCT", p["LD"]),
        ("TRAFO_LOSS_KWH", f"{k['dt']} * ({k['po']} + {k['pk']} * ({p['LD']} / 100) ** 2) / 1000"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    L = twin["twin_model"]["limits"]
    dt, rl, rd, xd, pm = k["dt"], k["rl"], k["rd"], k["xd"], k["pm"]
    a = _g(dt / 1000)
    fk = r["feeder_kwh_l1"] + r["feeder_kwh_l2"] + r["feeder_kwh_l3"]
    ck = r["cust_kwh_l1"] + r["cust_kwh_l2"] + r["cust_kwh_l3"]
    cov = r["reads_ok"] / k["n"] * 100
    i1, i2, i3, i_n = r["feeder_i_l1"], r["feeder_i_l2"], r["feeder_i_l3"], r["feeder_i_n"]
    tl = a * (rl * (i1 ** 2 + i2 ** 2 + i3 ** 2) + rl * i_n ** 2 + _g(pm))
    ntl = fk - ck - tl
    ph = {}
    for p, i in (("1", i1), ("2", i2), ("3", i3)):
        ph[p] = (r["feeder_kwh_l" + p] - r["cust_kwh_l" + p] - a * (rl * i ** 2 + _g(rl / 3) * i_n ** 2 + _g(pm / 3))) / (fk / 3) * 100
    vb = (r["v_bus_l1"] + r["v_bus_l2"] + r["v_bus_l3"]) / 3
    ve = (r["v_end_l1"] + r["v_end_l2"] + r["v_end_l3"]) / 3
    ia = (i1 + i2 + i3) / 3
    vi = r["v_bus_l1"] * i1 + r["v_bus_l2"] * i2 + r["v_bus_l3"] * i3
    pf = min(fk * 1000 / dt / vi, 1)
    vex = vb - ia * (rd * pf + xd * (1 - pf ** 2) ** 0.5)
    vend = (r["v_end_l1"], r["v_end_l2"], r["v_end_l3"])
    vbus = (r["v_bus_l1"], r["v_bus_l2"], r["v_bus_l3"])
    spx = (max(vend) - min(vend)) - (max(vbus) - min(vbus)) - (max(i1, i2, i3) - min(i1, i2, i3)) * rd - _g(SQ3 * rd) * i_n
    ld = vi / 1000 / k["sr"] * 100
    return {
        "feeder_kwh": fk, "cust_kwh": ck, "read_coverage_pct": cov, "tech_loss_kwh": tl, "tech_loss_pct": tl / fk * 100,
        "ntl_kwh": ntl, "ntl_pct": ntl / fk * 100, "ntl_l1_pct": ph["1"], "ntl_l2_pct": ph["2"], "ntl_l3_pct": ph["3"],
        "phase_spread_pct": max(ph.values()) - min(ph.values()), "v_bus_avg": vb, "v_end_expected": vex,
        "v_end_residual": ve - vex, "v_end_spread_excess": spx,
        "v_max_headroom": L["en50160_high_v"] - r["v_max_cust"], "v_min_headroom": r["v_min_cust"] - L["en50160_low_v"],
        "trafo_load_pct": ld, "trafo_loss_kwh": dt * (k["po"] + k["pk"] * (ld / 100) ** 2) / 1000,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    cov_ok = f"({p['COV']} >= {L['coverage_min_pct']})"
    N, hi, lo = p["NTLP"], L["ntl_alert_pct"], L["ntl_negative_pct"]
    bus_ok = f"({p['VB']} <= {L['bus_high_v']}) & ({p['VB']} >= {L['bus_low_v']})"
    return [
        ("AMI_LOSS_UNEXPLAINED", f"{cov_ok} & ({N} > {hi})", "High", "bypass_theft"),
        ("AMI_LOSS_NEGATIVE", f"{cov_ok} & ({N} < {-lo})", "High", "ct_polarity"),
        ("AMI_TAMPER", "df['TAMPER_EVENTS_24H'] > 0.5", "High", "bypass_theft"),
        ("AMI_NEUTRAL_SHIFT", f"{p['SPX']} > {L['neutral_shift_v']}", "High", "loose_neutral"),
        ("AMI_RELAY_MISMATCH", f"((df['RELAYS_CMD_OPEN'] - df['RELAYS_OPEN']) > 0.5) | (df['KWH_ON_OPEN_RELAYS'] > {L['relay_kwh']})", "High", "relay_stuck"),
        ("AMI_PHASE_MAPPING", f"{cov_ok} & ({N} <= {hi}) & ({N} >= {-lo}) & ({p['SPX']} <= {L['neutral_shift_v']}) & ({p['SPR']} > {L['phase_spread_pct']})", "Medium", "phase_mismapping"),
        ("AMI_REVERSE_ENERGY", f"df['FEEDER_KWH_EXPORT'] > {L['export_alert_kwh']}", "Medium", "ct_polarity"),
        ("AMI_VOLTAGE_OUT", f"((df['V_MIN_CUST'] < {L['en50160_low_v']}) | (df['V_MAX_CUST'] > {L['en50160_high_v']})) & {bus_ok}", "Medium", "loose_neutral"),
        ("AMI_BUS_VOLTAGE", f"({p['VB']} > {L['bus_high_v']}) | ({p['VB']} < {L['bus_low_v']})", "Medium", "tap_setting"),
        ("AMI_READS_LOW", f"{p['COV']} < {L['coverage_min_pct']}", "Medium", "concentrator_comms"),
        ("AMI_CLOCK_DRIFT", f"df['CLOCK_OFFSET_MAX_S'] > {L['clock_offset_s']}", "Low", "clock_drift"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    cov_ok = t["read_coverage_pct"] >= L["coverage_min_pct"]
    n = t["ntl_pct"]
    bus_ok = L["bus_low_v"] <= t["v_bus_avg"] <= L["bus_high_v"]
    worst = max(("L1", t["ntl_l1_pct"]), ("L2", t["ntl_l2_pct"]), ("L3", t["ntl_l3_pct"]), key=lambda x: x[1])
    add(cov_ok and n > L["ntl_alert_pct"], "AMI_LOSS_UNEXPLAINED", "High",
        f"Unexplained loss {n:.1f} % ({t['ntl_kwh']:.2f} kWh in 15 min), mostly on {worst[0]}", "customer meter", "bypass_theft")
    add(cov_ok and n < -L["ntl_negative_pct"], "AMI_LOSS_NEGATIVE", "High",
        f"Customers registered {-t['ntl_kwh']:.2f} kWh more than the feeder delivered ({n:.1f} %): check meter under-reads", "check meter", "ct_polarity")
    add(r["tamper_events_24h"] > 0.5, "AMI_TAMPER", "High", f"{r['tamper_events_24h']:.0f} terminal cover / magnetic field event(s) in 24 h", "customer meter", "bypass_theft")
    add(t["v_end_spread_excess"] > L["neutral_shift_v"], "AMI_NEUTRAL_SHIFT", "High",
        f"End-of-feeder phase voltages {r['v_end_l1']:.0f} / {r['v_end_l2']:.0f} / {r['v_end_l3']:.0f} V: {t['v_end_spread_excess']:.1f} V more spread than the unbalance explains",
        "LV network", "loose_neutral")
    add((r["relays_cmd_open"] - r["relays_open"]) > 0.5 or r["kwh_on_open_relays"] > L["relay_kwh"], "AMI_RELAY_MISMATCH", "High",
        f"{r['relays_cmd_open']:.0f} disconnector(s) commanded open, {r['relays_open']:.0f} confirmed; {r['kwh_on_open_relays']:.2f} kWh registered", "customer meter", "relay_stuck")
    add(cov_ok and -L["ntl_negative_pct"] <= n <= L["ntl_alert_pct"] and t["v_end_spread_excess"] <= L["neutral_shift_v"]
        and t["phase_spread_pct"] > L["phase_spread_pct"], "AMI_PHASE_MAPPING", "Medium",
        f"Total balance fine ({n:.1f} %) but phases differ by {t['phase_spread_pct']:.1f} points (L1 {t['ntl_l1_pct']:+.1f}, L2 {t['ntl_l2_pct']:+.1f}, L3 {t['ntl_l3_pct']:+.1f} %)",
        "network model", "phase_mismapping")
    add(r["feeder_kwh_export"] > L["export_alert_kwh"], "AMI_REVERSE_ENERGY", "Medium",
        f"Check meter registers {r['feeder_kwh_export']:.2f} kWh export on a feeder without generation", "check meter", "ct_polarity")
    add((r["v_min_cust"] < L["en50160_low_v"] or r["v_max_cust"] > L["en50160_high_v"]) and bus_ok, "AMI_VOLTAGE_OUT", "Medium",
        f"Customer voltages {r['v_min_cust']:.0f} to {r['v_max_cust']:.0f} V, outside {L['en50160_low_v']:.0f}-{L['en50160_high_v']:.0f} V, busbar normal", "LV network", "loose_neutral")
    add(not bus_ok, "AMI_BUS_VOLTAGE", "Medium",
        f"Busbar {t['v_bus_avg']:.1f} V, outside {L['bus_low_v']:.0f}-{L['bus_high_v']:.0f} V: transformer tap or MV voltage", "transformer", "tap_setting")
    add(not cov_ok, "AMI_READS_LOW", "Medium",
        f"Only {r['reads_ok']:.0f} of {twin['design']['meters']['n_meters']} meters read ({t['read_coverage_pct']:.0f} %): balance not judged", "concentrator", "concentrator_comms")
    add(r["clock_offset_max_s"] > L["clock_offset_s"], "AMI_CLOCK_DRIFT", "Low", f"A meter clock is {r['clock_offset_max_s']:.0f} s off", "customer meter", "clock_drift")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
