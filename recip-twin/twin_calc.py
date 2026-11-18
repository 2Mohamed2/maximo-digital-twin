"""The reciprocating compressor twin's expectations (K-2201, Ariel KBU/2, two stages, hydrogen make-up).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Pressures in bar g, temperatures in °C, forces in kN. atm = 1.01325 bar.

Internal pressures (Ariel calculation method: the valves cost a few percent of the flange pressure):
    Psi = (Ps + atm) x (1 - loss_s)        Pdi = (Pd + atm) x (1 + loss_d)        Rint = Pdi / Psi
Expected discharge temperature (Ariel: suction preheat, then isentropic compression with k):
    e = (k - 1) / k,   f = 0.02 + 0.002 x bore(in)
    Tsph = Ts x (1 - f) / (1 - f x Rint^e)         (closed form of Tsph = Ts + f (Td - Ts))
    Td   = Tsph x Rint^e                            (kelvin)
Volumetric efficiency and capacity (textbook form, Z ratio 1):
    r = (Pd + atm) / (Ps + atm),   VE = 1 - r/100 - C (r^(1/k) - 1)
    displacement = (A_he + A_ce) x stroke x rpm;   expected flow (Nm³/h) = VE x displacement x 60 x (Ps+atm)/atm x 273.15/Ts
Gas rod load at the crosshead pin (Ariel, internal gauge pressures; frame ratings are on gas load):
    compression RLc = A_he x Pdi_g - A_ce x Psi_g      tension RLt = A_ce x Pdi_g - A_he x Psi_g
    (kN = m² x bar x 100), each divided by the Ariel rating (80,000 lbf compression, 75,000 lbf tension).
Valve health from the cover temperatures (a leaking valve passes hot gas back and forth and runs hot):
    suction cover rise   = cover - suction gas of its stage (healthy: a few K)
    discharge cover dev. = cover - expected discharge temperature of its stage
    peer spread          = |head end - crank end| for the same valve function on the same cylinder
Combined pin load (gas + inertia) and its reversal are computed over the crank angle by pin_load_curve() and
reversal(): Ariel uses them for the reversal check (30 degrees, 25 %), not for the frame rating.
"""
import math

ATM = 1.01325
IN = 0.0254
LBF = 4.4482216152605


def _r(x):
    return float(f"{x:.10g}")


def _k(twin):
    d = twin["design"]
    fr, g, s1, s2 = d["frame"], d["gas"], d["stages"][0], d["stages"][1]
    stroke = fr["stroke_in"] * IN
    arod = math.pi / 4 * (fr["rod_diameter_in"] * IN) ** 2
    k = dict(atm=ATM, kg=g["k"], e=_r((g["k"] - 1) / g["k"]), ik=_r(1 / g["k"]), stroke=_r(stroke), arod=_r(arod),
             rt=_r(fr["rod_load_tension_lbf"] * LBF / 1000), rc=_r(fr["rod_load_compression_lbf"] * LBF / 1000),
             rpm=d["operation"]["rpm"], lube=d["lube"]["design_cycle_s"],
             xb1=d["crosshead"]["baseline_g"][0], xb2=d["crosshead"]["baseline_g"][1],
             tdlim=d["temperature"]["td_limit_c"], tdalarm=d["temperature"]["td_alarm_c"])
    for i, s in ((1, s1), (2, s2)):
        ahe = math.pi / 4 * (s["bore_in"] * IN) ** 2
        k[f"ahe{i}"], k[f"ace{i}"] = _r(ahe), _r(ahe - arod)
        k[f"c{i}"], k[f"ls{i}"], k[f"ld{i}"] = s["clearance"], s["loss_suction"], s["loss_discharge"]
        k[f"f{i}"] = _r(0.02 + 0.002 * s["bore_in"])
        k[f"disp{i}"] = _r((2 * ahe - arod) * stroke)          # m³ per revolution, both ends
        k[f"m{i}"] = s["recip_mass_kg"]
    return k


def _parts(twin):
    k = _k(twin)
    D = lambda m: f"df['{m.upper()}']"
    P = {}
    for i in (1, 2):
        ps, pd, ts = D(f"ps{i}_barg"), D(f"pd{i}_barg"), D(f"ts{i}_c")
        PSI = f"(({ps} + {ATM}) * {1 - k[f'ls{i}']!r})"
        PDI = f"(({pd} + {ATM}) * {1 + k[f'ld{i}']!r})"
        R = f"({PDI} / {PSI})"
        RE = f"({R} ** {k['e']!r})"
        f = k[f"f{i}"]
        TDE = f"(({ts} + 273.15) * {_r(1 - f)!r} / (1 - {f!r} * {RE}) * {RE} - 273.15)"
        RF = f"(({pd} + {ATM}) / ({ps} + {ATM}))"
        VE = f"(1 - {RF} / 100 - {k[f'c{i}']!r} * ({RF} ** {k['ik']!r} - 1))"
        PSG, PDG = f"({PSI} - {ATM})", f"({PDI} - {ATM})"
        RLC = f"(({k[f'ahe{i}']!r} * {PDG} - {k[f'ace{i}']!r} * {PSG}) * 100 / {k['rc']!r} * 100)"
        RLT = f"(({k[f'ace{i}']!r} * {PDG} - {k[f'ahe{i}']!r} * {PSG}) * 100 / {k['rt']!r} * 100)"
        P.update({f"R{i}": R, f"TDE{i}": TDE, f"VE{i}": VE, f"RLC{i}": RLC, f"RLT{i}": RLT})
    P["FLOWE"] = (f"({P['VE1']} * {k['disp1']!r} * {D('speed_rpm')} * 60 * ({D('ps1_barg')} + {ATM}) / {ATM}"
                  f" * 273.15 / ({D('ts1_c')} + 273.15))")
    mx = lambda a, b: f"np.maximum({a}, {b})"
    P["RLMAX"] = mx(mx(P["RLC1"], P["RLT1"]), mx(P["RLC2"], P["RLT2"]))
    P["SRISE"] = mx(mx(f"({D('tv1_he_s_c')} - {D('ts1_c')})", f"({D('tv1_ce_s_c')} - {D('ts1_c')})"),
                    mx(f"({D('tv2_he_s_c')} - {D('ts2_c')})", f"({D('tv2_ce_s_c')} - {D('ts2_c')})"))
    P["DDEV"] = mx(mx(f"({D('tv1_he_d_c')} - {P['TDE1']})", f"({D('tv1_ce_d_c')} - {P['TDE1']})"),
                   mx(f"({D('tv2_he_d_c')} - {P['TDE2']})", f"({D('tv2_ce_d_c')} - {P['TDE2']})"))
    ab = lambda a, b: f"np.abs({D(a)} - {D(b)})"
    P["SPREAD"] = mx(mx(ab("tv1_he_s_c", "tv1_ce_s_c"), ab("tv1_he_d_c", "tv1_ce_d_c")),
                     mx(ab("tv2_he_s_c", "tv2_ce_s_c"), ab("tv2_he_d_c", "tv2_ce_d_c")))
    P["LUBE"] = f"({k['lube']!r} / {D('lube_cycle_s')})"
    P["XH"] = mx(f"({D('xhead_acc1_g')} / {k['xb1']!r})", f"({D('xhead_acc2_g')} / {k['xb2']!r})")
    P["TDR1"] = f"({D('td1_c')} - {P['TDE1']})"
    P["TDR2"] = f"({D('td2_c')} - {P['TDE2']})"
    P["CAP"] = f"({D('flow_nm3h')} / {P['FLOWE']})"
    return k, P


def monitor_expressions(twin):
    k, P = _parts(twin)
    return [
        ("RINT_S1", P["R1"]), ("RINT_S2", P["R2"]),
        ("TD_EXPECTED_S1_C", P["TDE1"]), ("TD_EXPECTED_S2_C", P["TDE2"]),
        ("TD_RESIDUAL_S1_K", P["TDR1"]), ("TD_RESIDUAL_S2_K", P["TDR2"]),
        ("VE_S1", P["VE1"]), ("VE_S2", P["VE2"]),
        ("FLOW_EXPECTED_NM3H", P["FLOWE"]), ("CAPACITY_RATIO", P["CAP"]),
        ("ROD_LOAD_C_S1_PCT", P["RLC1"]), ("ROD_LOAD_T_S1_PCT", P["RLT1"]),
        ("ROD_LOAD_C_S2_PCT", P["RLC2"]), ("ROD_LOAD_T_S2_PCT", P["RLT2"]),
        ("ROD_LOAD_MAX_PCT", P["RLMAX"]),
        ("SUCT_COVER_RISE_MAX_K", P["SRISE"]), ("DISCH_COVER_DEV_MAX_K", P["DDEV"]), ("VALVE_PEER_SPREAD_K", P["SPREAD"]),
        ("LUBE_RATE_RATIO", P["LUBE"]), ("XHEAD_VIB_RATIO", P["XH"]),
    ]


# ---- the same numbers in Python ----------------------------------------------------------------------------------------
def stage(k, i, ps, pd, ts):
    """Internal ratio, expected discharge temperature, VE and gas rod loads (% of rating) of stage i."""
    psi = (ps + ATM) * (1 - k[f"ls{i}"])
    pdi = (pd + ATM) * (1 + k[f"ld{i}"])
    R = pdi / psi
    re = R ** k["e"]
    f = k[f"f{i}"]
    tde = (ts + 273.15) * _r(1 - f) / (1 - f * re) * re - 273.15
    rf = (pd + ATM) / (ps + ATM)
    ve = 1 - rf / 100 - k[f"c{i}"] * (rf ** k["ik"] - 1)
    psg, pdg = psi - ATM, pdi - ATM
    rlc = (k[f"ahe{i}"] * pdg - k[f"ace{i}"] * psg) * 100 / k["rc"] * 100
    rlt = (k[f"ace{i}"] * pdg - k[f"ahe{i}"] * psg) * 100 / k["rt"] * 100
    return dict(R=R, tde=tde, ve=ve, rlc=rlc, rlt=rlt, rf=rf)


def flow_expected(k, ve1, rpm, ps1, ts1):
    return ve1 * k["disp1"] * rpm * 60 * (ps1 + ATM) / ATM * 273.15 / (ts1 + 273.15)


def evaluate(twin, r):
    k = _k(twin)
    s1 = stage(k, 1, r["ps1_barg"], r["pd1_barg"], r["ts1_c"])
    s2 = stage(k, 2, r["ps2_barg"], r["pd2_barg"], r["ts2_c"])
    fe = flow_expected(k, s1["ve"], r["speed_rpm"], r["ps1_barg"], r["ts1_c"])
    return {
        "rint_s1": s1["R"], "rint_s2": s2["R"], "td_expected_s1_c": s1["tde"], "td_expected_s2_c": s2["tde"],
        "td_residual_s1_k": r["td1_c"] - s1["tde"], "td_residual_s2_k": r["td2_c"] - s2["tde"],
        "ve_s1": s1["ve"], "ve_s2": s2["ve"], "flow_expected_nm3h": fe, "capacity_ratio": r["flow_nm3h"] / fe,
        "rod_load_c_s1_pct": s1["rlc"], "rod_load_t_s1_pct": s1["rlt"], "rod_load_c_s2_pct": s2["rlc"], "rod_load_t_s2_pct": s2["rlt"],
        "rod_load_max_pct": max(s1["rlc"], s1["rlt"], s2["rlc"], s2["rlt"]),
        "suct_cover_rise_max_k": max(r["tv1_he_s_c"] - r["ts1_c"], r["tv1_ce_s_c"] - r["ts1_c"], r["tv2_he_s_c"] - r["ts2_c"], r["tv2_ce_s_c"] - r["ts2_c"]),
        "disch_cover_dev_max_k": max(r["tv1_he_d_c"] - s1["tde"], r["tv1_ce_d_c"] - s1["tde"], r["tv2_he_d_c"] - s2["tde"], r["tv2_ce_d_c"] - s2["tde"]),
        "valve_peer_spread_k": max(abs(r["tv1_he_s_c"] - r["tv1_ce_s_c"]), abs(r["tv1_he_d_c"] - r["tv1_ce_d_c"]),
                                   abs(r["tv2_he_s_c"] - r["tv2_ce_s_c"]), abs(r["tv2_he_d_c"] - r["tv2_ce_d_c"])),
        "lube_rate_ratio": k["lube"] / r["lube_cycle_s"],
        "xhead_vib_ratio": max(r["xhead_acc1_g"] / k["xb1"], r["xhead_acc2_g"] / k["xb2"]),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    k, P = _parts(twin)
    D = lambda m: f"df['{m.upper()}']"
    return [
        ("RECIP_ROD_LOAD_LIMIT", f"{P['RLMAX']} > {L['rod_load_limit_pct']}", "Critical", "discharge_pressure_high"),
        ("RECIP_ROD_LOAD_HIGH", f"({P['RLMAX']} > {L['rod_load_alert_pct']}) & ({P['RLMAX']} <= {L['rod_load_limit_pct']})", "High", "discharge_pressure_high"),
        ("RECIP_TD_HIGH", f"np.maximum({D('td1_c')}, {D('td2_c')}) > {k['tdalarm']}", "High", None),
        ("RECIP_PACKING_LEAK", f"np.maximum({D('packing_vent1_nm3h')}, {D('packing_vent2_nm3h')}) > {L['packing_vent_alert_nm3h']}", "High", "packing_leak"),
        ("RECIP_LUBE_LOW", f"{P['LUBE']} < {L['lube_rate_ratio_alert']}", "High", "lube_starvation"),
        ("RECIP_XHEAD_VIB", f"{P['XH']} > {L['xhead_ratio_alert']}", "High", "crosshead_wear"),
        ("RECIP_SUCTION_VALVE_LEAK", f"{P['SRISE']} > {L['suction_cover_rise_alert_k']}", "Medium", "suction_valve_leak"),
        ("RECIP_DISCHARGE_VALVE_LEAK", f"{P['DDEV']} > {L['discharge_cover_dev_alert_k']}", "Medium", "discharge_valve_leak"),
        ("RECIP_VALVE_PEER_SPREAD", f"{P['SPREAD']} > {L['valve_peer_spread_alert_k']}", "Medium", "discharge_valve_leak"),
        ("RECIP_TD_DEVIATION_S1", f"{P['TDR1']} > {L['td_residual_alert_k']}", "Medium", "discharge_valve_leak"),
        ("RECIP_TD_DEVIATION_S2", f"{P['TDR2']} > {L['td_residual_alert_k']}", "Medium", "ring_wear"),
        ("RECIP_CAPACITY_LOW", f"{P['CAP']} < {L['capacity_ratio_alert']}", "Medium", "discharge_valve_leak"),
        ("RECIP_ROD_DROP", f"np.maximum({D('rod_drop1_mm')}, {D('rod_drop2_mm')}) > {L['rod_drop_alert_mm']}", "Medium", "rider_band_wear"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    rl = t["rod_load_max_pct"]
    add(rl > L["rod_load_limit_pct"], "RECIP_ROD_LOAD_LIMIT", "Critical", f"Gas rod load {rl:.0f} % of the Ariel frame rating", "running gear", "discharge_pressure_high")
    add(L["rod_load_alert_pct"] < rl <= L["rod_load_limit_pct"], "RECIP_ROD_LOAD_HIGH", "High", f"Gas rod load {rl:.0f} % of the frame rating", "running gear", "discharge_pressure_high")
    tdm = max(r["td1_c"], r["td2_c"])
    add(tdm > k["tdalarm"], "RECIP_TD_HIGH", "High", f"Discharge temperature {tdm:.0f} °C, above the {k['tdalarm']:.0f} °C alarm", "process")
    pv = max(r["packing_vent1_nm3h"], r["packing_vent2_nm3h"])
    add(pv > L["packing_vent_alert_nm3h"], "RECIP_PACKING_LEAK", "High", f"Packing vent {pv:.2f} Nm³/h", "packing", "packing_leak")
    add(t["lube_rate_ratio"] < L["lube_rate_ratio_alert"], "RECIP_LUBE_LOW", "High",
        f"Divider block cycle {r['lube_cycle_s']:.0f} s: lube rate {t['lube_rate_ratio'] * 100:.0f} % of setting", "lube", "lube_starvation")
    add(t["xhead_vib_ratio"] > L["xhead_ratio_alert"], "RECIP_XHEAD_VIB", "High", f"Crosshead acceleration {t['xhead_vib_ratio']:.1f} x baseline", "running gear", "crosshead_wear")
    add(t["suct_cover_rise_max_k"] > L["suction_cover_rise_alert_k"], "RECIP_SUCTION_VALVE_LEAK", "Medium",
        f"A suction valve cover is {t['suct_cover_rise_max_k']:.0f} K above its suction gas", "valves", "suction_valve_leak")
    add(t["disch_cover_dev_max_k"] > L["discharge_cover_dev_alert_k"], "RECIP_DISCHARGE_VALVE_LEAK", "Medium",
        f"A discharge valve cover is {t['disch_cover_dev_max_k']:.0f} K above the expected discharge temperature", "valves", "discharge_valve_leak")
    add(t["valve_peer_spread_k"] > L["valve_peer_spread_alert_k"], "RECIP_VALVE_PEER_SPREAD", "Medium",
        f"Head and crank end covers differ by {t['valve_peer_spread_k']:.0f} K", "valves", "discharge_valve_leak")
    add(t["td_residual_s1_k"] > L["td_residual_alert_k"], "RECIP_TD_DEVIATION_S1", "Medium",
        f"Stage 1 discharge {r['td1_c']:.0f} °C, {t['td_residual_s1_k']:.0f} K above expected", "cylinder", "discharge_valve_leak")
    add(t["td_residual_s2_k"] > L["td_residual_alert_k"], "RECIP_TD_DEVIATION_S2", "Medium",
        f"Stage 2 discharge {r['td2_c']:.0f} °C, {t['td_residual_s2_k']:.0f} K above expected", "cylinder", "ring_wear")
    add(t["capacity_ratio"] < L["capacity_ratio_alert"], "RECIP_CAPACITY_LOW", "Medium",
        f"Flow {t['capacity_ratio'] * 100:.0f} % of the capacity expected from clearance and ratio", "cylinder", "discharge_valve_leak")
    rd = max(r["rod_drop1_mm"], r["rod_drop2_mm"])
    add(rd > L["rod_drop_alert_mm"], "RECIP_ROD_DROP", "Medium", f"Rod drop {rd:.2f} mm: rider bands worn", "cylinder", "rider_band_wear")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health


# ---- crank-angle model: gas + inertia load at the crosshead pin and its reversal ---------------------------------------
def pin_load_curve(twin, i, ps, pd, rpm=None, step=2, he_active=True):
    """[(crank deg, gas kN, inertia kN, combined kN)] for stage i over one revolution (positive = compression).

    Ideal indicator diagram per end with the stage clearance: re-expansion and compression with exponent k between the
    internal suction and discharge pressures. 0 degrees = piston at the head-end dead centre.
    """
    k = _k(twin)
    rg = twin["design"]["running_gear"]
    rpm = rpm or k["rpm"]
    cr, lr, C, kg = k["stroke"] / 2, rg["conrod_length_m"], k[f"c{i}"], k["kg"]
    lam = cr / lr
    psi = (ps + ATM) * (1 - k[f"ls{i}"])
    pdi = (pd + ATM) * (1 + k[f"ld{i}"])
    w = rpm * 2 * math.pi / 60

    def pos(th):            # fraction of the stroke travelled from the head-end dead centre
        return (cr * (1 - math.cos(th)) + lr * (1 - math.sqrt(1 - (lam * math.sin(th)) ** 2))) / (2 * cr)

    def p_end(s, going_out):
        """pressure in an end whose volume fraction is C + s; going_out = volume growing."""
        if going_out:
            p = pdi * (C / (C + s)) ** kg
            return max(p, psi)
        p = psi * ((1 + C) / (C + s)) ** kg
        return min(p, pdi)
    out = []
    for deg in range(0, 360, step):
        th = math.radians(deg)
        s = pos(th)
        he_out = deg < 180                       # head-end volume grows on the first half turn
        phe = p_end(s, he_out) if he_active else psi
        pce = p_end(1 - s, not he_out)
        gas = ((phe - ATM) * k[f"ahe{i}"] - (pce - ATM) * k[f"ace{i}"]) * 100
        acc = -w * w * cr * (math.cos(th) + lam * math.cos(2 * th))
        inert = k[f"m{i}"] * acc / 1000
        out.append((deg, gas, inert, gas + inert))
    return out


def reversal(curve):
    """(degrees of the shorter load direction, magnitude % = smaller peak / larger peak) for a pin load curve."""
    step = curve[1][0] - curve[0][0]
    comp = sum(step for c in curve if c[3] > 0)
    tens = sum(step for c in curve if c[3] < 0)
    pc = max(c[3] for c in curve)
    pt = -min(c[3] for c in curve)
    return min(comp, tens), (min(pc, pt) / max(pc, pt) * 100 if min(pc, pt) > 0 else 0.0)
