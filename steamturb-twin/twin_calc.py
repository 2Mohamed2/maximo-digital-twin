"""The steam turbine twin's expectations (ST-3201, condensing turbine with one controlled extraction, SST-400 frame).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Steam properties (short correlations fitted to IAPWS-IF97, coefficients in design.steam_props; P in bar(a), T in K):
    h(P, T)   = a0 + a1 T + a2 T^2 + c1 (T/600)^-n P + c2 (T/600)^-m P^2           enthalpy, kJ/kg (superheated)
    Pv(P, T)  = b0 T + b1 (T/600)^-n P + b2 (T/600)^-m P^2                         P x v, kJ/kg
HP section (main steam 1 -> extraction e), both ends superheated, so the efficiency comes from pressures and temperatures:
    dh_actual    = h(P1, T1) - h(Pe, Te)
    dh_isentropic = k / (k - 1) x P1 v1 x (1 - (Pe / P1)^((k - 1) / k))            isentropic index k fitted to IF97
    eta_HP = dh_actual / dh_isentropic;   expected eta = eta_rated - curv x (1 - m / m_rated)^2  (nozzle governing)
First stage (wheel chamber) pressure: the stages behind the first stage pass a flow proportional to the pressure in front
of them (Stodola / law of the cone with a large pressure ratio), so at constant blade-path area
    p_wheel_expected = p_wheel_rated x (m / m_rated) x sqrt(T1 / T1_rated)
    ratio = p_wheel / p_wheel_expected:  > 1 the path is narrower (deposits), < 1 it is wider (erosion)
Expected output (Willans line fitted to the heat balance, plus correction factors as in an ASME PTC 6 / IEC 60953 test):
    P_expected = a m_main + b m_extraction + c + kP (P1 - P1r) + kT (T1 - T1r) + kC p_r / x ((p_cond / p_r)^x - 1)
    (the backpressure correction curve has slope kC MW/mbar at the rated condenser pressure p_r and flattens as x < 1)
Condenser: T_sat = B / (A - log10 p) - C (Antoine form fitted to IF97, p in mbar), TTD = T_sat - T_cw,out,
    p_expected = 10^(A - B / (T_cw,out + TTD_design + C));  backpressure loss = the same correction curve between p_expected and p_cond
Governor valves (choked): m_expected = m_rated x (lift / lift_rated) x (P1 / P1r) x sqrt(T1r / T1)
Vibration: the higher bearing housing velocity against the ISO 20816-2 zone boundaries (3000 r/min).
"""
import math

C2K = 273.15


def _willans(points):
    """Least-squares fit P = a m + b e + c to the heat balance points [m, e, P] (normal equations, Cramer's rule)."""
    n = len(points)
    sm = sum(p[0] for p in points); se = sum(p[1] for p in points); sp = sum(p[2] for p in points)
    smm = sum(p[0] ** 2 for p in points); see = sum(p[1] ** 2 for p in points); sme = sum(p[0] * p[1] for p in points)
    smp = sum(p[0] * p[2] for p in points); sep = sum(p[1] * p[2] for p in points)
    M = [[smm, sme, sm], [sme, see, se], [sm, se, n]]
    y = [smp, sep, sp]

    def det(a):
        return (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
                + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    d = det(M)
    out = []
    for j in range(3):
        Mj = [[y[i] if c == j else M[i][c] for c in range(3)] for i in range(3)]
        out.append(float(f"{det(Mj) / d:.10g}"))
    return out


def _k(twin):
    d = twin["design"]
    ra, hp, lp, va, co, sp, hb = d["rated"], d["hp_section"], d["lp_section"], d["valves"], d["condenser"], d["steam_props"], d["heat_balance"]
    wa, wb, wc = _willans(hb["points"])
    cr = hb["corrections"]
    return dict(m0=ra["main_flow_th"], p0=ra["main_press_bara"], t0=ra["main_temp_c"], pe0=ra["ext_press_bara"], e0=ra["ext_flow_th"],
                pc0=ra["cond_press_mbar"], n0=ra["speed_rpm"], emg=ra["mech_gen_eff"],
                eta0=hp["eta_rated_pct"], curv=hp["eta_curv_pts"], pw0=hp["wheel_press_rated_bara"],
                eta_lp=lp["eta_rated_pct"], k_lp=lp["k_isentropic"], lift0=va["gv_lift_rated_pct"],
                cw_in=co["cw_in_c"], cw_rise=co["cw_rise_k"], ttd0=co["ttd_k"],
                tr=sp["t_ref_k"], H=sp["h"], V=sp["pv"], k=sp["k_hp"], ant=sp["antoine"],
                wa=wa, wb=wb, wc=wc, kP=cr["mw_per_bar_main"], kT=cr["mw_per_k_main"], kC=cr["mw_per_mbar_cond"], xc=cr["cond_exponent"],
                price=d["economics"]["power_price_eur_mwh"])


# steam properties: numbers -----------------------------------------------------------------------------------------------
def h_pt(k, p, tk):
    H, tr = k["H"], k["tr"]
    return H["a0"] + H["a1"] * tk + H["a2"] * tk * tk + H["c1"] * (tk / tr) ** -H["n"] * p + H["c2"] * (tk / tr) ** -H["m"] * p * p


def pv_pt(k, p, tk):
    V, tr = k["V"], k["tr"]
    return V["b0"] * tk + V["b1"] * (tk / tr) ** -V["n"] * p + V["b2"] * (tk / tr) ** -V["m"] * p * p


def dh_isen(k, p1, tk1, p2, kk=None):
    kk = kk or k["k"]
    return kk / (kk - 1) * pv_pt(k, p1, tk1) * (1 - (p2 / p1) ** ((kk - 1) / kk))


def psat_mbar(k, tc):
    a = k["ant"]
    return 10 ** (a["A"] - a["B"] / (tc + a["C"]))


def tsat_c(k, p_mbar):
    a = k["ant"]
    return a["B"] / (a["A"] - math.log10(p_mbar)) - a["C"]


def t_from_h(k, p, h):
    """Inverse of h_pt at pressure p (bisection, K). Used by the stand-in and the figures only."""
    lo, hi = 300.0, 900.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if h_pt(k, p, mid) < h else (lo, mid)
    return (lo + hi) / 2


def eta_expected(k, flow):
    return k["eta0"] - k["curv"] * (1 - flow / k["m0"]) ** 2


def power_expected(k, m, e, p1, t1, pc):
    return (k["wa"] * m + k["wb"] * e + k["wc"] + k["kP"] * (p1 - k["p0"]) + k["kT"] * (t1 - k["t0"])
            + k["kC"] * k["pc0"] / k["xc"] * ((pc / k["pc0"]) ** k["xc"] - 1))


# steam properties: pandas strings --------------------------------------------------------------------------------------
def _hs(k, P, T):
    H, tr = k["H"], k["tr"]
    return (f"({H['a0']!r} + {H['a1']!r} * {T} + {H['a2']!r} * {T} ** 2 + {H['c1']!r} * ({T} / {tr!r}) ** -{H['n']!r} * {P}"
            f" + {H['c2']!r} * ({T} / {tr!r}) ** -{H['m']!r} * {P} ** 2)")


def _pvs(k, P, T):
    V, tr = k["V"], k["tr"]
    return f"({V['b0']!r} * {T} + {V['b1']!r} * ({T} / {tr!r}) ** -{V['n']!r} * {P} + {V['b2']!r} * ({T} / {tr!r}) ** -{V['m']!r} * {P} ** 2)"


def _parts(twin):
    k = _k(twin)
    a = k["ant"]
    P1, T1, PE, TE = "df['MAIN_PRESS_BARA']", f"(df['MAIN_TEMP_C'] + {C2K})", "df['EXT_PRESS_BARA']", f"(df['EXT_TEMP_C'] + {C2K})"
    kk = k["k"]
    H1, HE = _hs(k, P1, T1), _hs(k, PE, TE)
    DHA = f"({H1} - {HE})"
    DHS = f"({kk / (kk - 1)!r} * {_pvs(k, P1, T1)} * (1 - ({PE} / {P1}) ** {(kk - 1) / kk!r}))"
    EFF = f"(100 * {DHA} / {DHS})"
    EEXP = f"({k['eta0']!r} - {k['curv']!r} * (1 - df['MAIN_FLOW_TH'] / {k['m0']!r}) ** 2)"
    WEXP = f"({k['pw0']!r} * (df['MAIN_FLOW_TH'] / {k['m0']!r}) * np.sqrt({T1} / {k['t0'] + C2K!r}))"
    PEXP = (f"({k['wa']!r} * df['MAIN_FLOW_TH'] + {k['wb']!r} * df['EXT_FLOW_TH'] + {k['wc']!r}"
            f" + {k['kP']!r} * (df['MAIN_PRESS_BARA'] - {k['p0']!r}) + {k['kT']!r} * (df['MAIN_TEMP_C'] - {k['t0']!r})"
            f" + {k['kC'] * k['pc0'] / k['xc']!r} * ((df['COND_PRESS_MBAR'] / {k['pc0']!r}) ** {k['xc']!r} - 1))")
    TSAT = f"({a['B']!r} / ({a['A']!r} - np.log10(df['COND_PRESS_MBAR'])) - {a['C']!r})"
    PCEXP = f"(10 ** ({a['A']!r} - {a['B']!r} / (df['CW_OUT_C'] + {k['ttd0']!r} + {a['C']!r})))"
    VR = f"(df['MAIN_FLOW_TH'] / ({k['m0']!r} * (df['GV_LIFT_PCT'] / {k['lift0']!r}) * (df['MAIN_PRESS_BARA'] / {k['p0']!r}) * np.sqrt({k['t0'] + C2K!r} / {T1})))"
    return dict(k=k, H1=H1, HE=HE, DHA=DHA, DHS=DHS, EFF=EFF, EEXP=EEXP, EDEV=f"({EFF} - {EEXP})", WEXP=WEXP,
                WR=f"(df['WHEEL_PRESS_BARA'] / {WEXP})", PEXP=PEXP, PDEV=f"(100 * (df['POWER_MW'] - {PEXP}) / {PEXP})",
                TSAT=TSAT, TTD=f"({TSAT} - df['CW_OUT_C'])", PCEXP=PCEXP, PCDEV=f"(df['COND_PRESS_MBAR'] - {PCEXP})", VR=VR,
                VMAX="np.maximum(df['VIB_BRG1_MMS'], df['VIB_BRG2_MMS'])")


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("H_MAIN_KJKG", p["H1"]),
        ("H_EXT_KJKG", p["HE"]),
        ("DH_HP_ACTUAL_KJKG", p["DHA"]),
        ("DH_HP_ISEN_KJKG", p["DHS"]),
        ("HP_EFF_PCT", p["EFF"]),
        ("HP_EFF_EXPECTED_PCT", p["EEXP"]),
        ("HP_EFF_DEV_PTS", p["EDEV"]),
        ("WHEEL_PRESS_EXPECTED_BARA", p["WEXP"]),
        ("WHEEL_PRESS_RATIO", p["WR"]),
        ("POWER_EXPECTED_MW", p["PEXP"]),
        ("POWER_DEV_PCT", p["PDEV"]),
        ("LOST_MW", f"({p['PEXP']} - df['POWER_MW'])"),
        ("LOST_EUR_H", f"({p['PEXP']} - df['POWER_MW']) * {k['price']!r}"),
        ("COND_TSAT_C", p["TSAT"]),
        ("COND_TTD_K", p["TTD"]),
        ("COND_PRESS_EXPECTED_MBAR", p["PCEXP"]),
        ("COND_PRESS_DEV_MBAR", p["PCDEV"]),
        ("BACKPRESSURE_LOSS_MW", f"{-k['kC'] * k['pc0'] / k['xc']!r} * ((df['COND_PRESS_MBAR'] / {k['pc0']!r}) ** {k['xc']!r} - ({p['PCEXP']} / {k['pc0']!r}) ** {k['xc']!r})"),
        ("VALVE_FLOW_RATIO", p["VR"]),
        ("VIB_MAX_MMS", p["VMAX"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    t1, te = r["main_temp_c"] + C2K, r["ext_temp_c"] + C2K
    h1, he = h_pt(k, r["main_press_bara"], t1), h_pt(k, r["ext_press_bara"], te)
    dha, dhs = h1 - he, dh_isen(k, r["main_press_bara"], t1, r["ext_press_bara"])
    eff = 100 * dha / dhs
    eexp = eta_expected(k, r["main_flow_th"])
    wexp = k["pw0"] * (r["main_flow_th"] / k["m0"]) * math.sqrt(t1 / (k["t0"] + C2K))
    pexp = power_expected(k, r["main_flow_th"], r["ext_flow_th"], r["main_press_bara"], r["main_temp_c"], r["cond_press_mbar"])
    tsat = tsat_c(k, r["cond_press_mbar"])
    pcexp = psat_mbar(k, r["cw_out_c"] + k["ttd0"])
    pcdev = r["cond_press_mbar"] - pcexp
    mexp = k["m0"] * (r["gv_lift_pct"] / k["lift0"]) * (r["main_press_bara"] / k["p0"]) * math.sqrt((k["t0"] + C2K) / t1)
    return {
        "h_main_kjkg": h1, "h_ext_kjkg": he, "dh_hp_actual_kjkg": dha, "dh_hp_isen_kjkg": dhs,
        "hp_eff_pct": eff, "hp_eff_expected_pct": eexp, "hp_eff_dev_pts": eff - eexp,
        "wheel_press_expected_bara": wexp, "wheel_press_ratio": r["wheel_press_bara"] / wexp,
        "power_expected_mw": pexp, "power_dev_pct": 100 * (r["power_mw"] - pexp) / pexp,
        "lost_mw": pexp - r["power_mw"], "lost_eur_h": (pexp - r["power_mw"]) * k["price"],
        "cond_tsat_c": tsat, "cond_ttd_k": tsat - r["cw_out_c"], "cond_press_expected_mbar": pcexp,
        "cond_press_dev_mbar": pcdev, "backpressure_loss_mw": -k["kC"] * k["pc0"] / k["xc"] * ((r["cond_press_mbar"] / k["pc0"]) ** k["xc"] - (pcexp / k["pc0"]) ** k["xc"]),
        "valve_flow_ratio": r["main_flow_th"] / mexp, "vib_max_mms": max(r["vib_brg1_mms"], r["vib_brg2_mms"]),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    ED, WR, PD, VM = p["EDEV"], p["WR"], p["PDEV"], p["VMAX"]
    return [
        ("ST_VIB_ZONE_D", f"{VM} >= {L['vib_cd_mms']}", "High", None),
        ("ST_HP_EFF_VERY_LOW", f"{ED} <= {L['hp_eff_very_low_pts']}", "High", "solid_particle_erosion"),
        ("ST_THRUST_POS", f"np.abs(df['THRUST_POS_MM']) > {L['thrust_pos_mm']}", "High", "thrust_bearing_wear"),
        ("ST_POWER_LOW", f"{PD} < {L['power_dev_low_pct']}", "Medium", "lp_blade_damage"),
        ("ST_HP_EFF_LOW", f"({ED} <= {L['hp_eff_low_pts']}) & ({ED} > {L['hp_eff_very_low_pts']})", "Medium", "hp_deposits"),
        ("ST_WHEEL_PRESS_HIGH", f"{WR} > {L['wheel_ratio_high']}", "Medium", "hp_deposits"),
        ("ST_WHEEL_PRESS_LOW", f"{WR} < {L['wheel_ratio_low']}", "Medium", "solid_particle_erosion"),
        ("ST_COND_PRESS_HIGH", f"{p['PCDEV']} > {L['cond_press_dev_mbar']}", "Medium", "condenser_fouling"),
        ("ST_TTD_HIGH", f"{p['TTD']} > {L['ttd_high_k']}", "Medium", "condenser_fouling"),
        ("ST_VALVE_CAPACITY_LOW", f"{p['VR']} < {L['valve_ratio_low']}", "Medium", "governor_valve"),
        ("ST_VIB_ZONE_C", f"({VM} >= {L['vib_bc_mms']}) & ({VM} < {L['vib_cd_mms']})", "Medium", "rotor_unbalance"),
        ("ST_THRUST_TEMP", f"df['THRUST_PAD_C'] > {L['thrust_pad_c']}", "Medium", "thrust_bearing_wear"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    ed, wr, pd, vm = t["hp_eff_dev_pts"], t["wheel_press_ratio"], t["power_dev_pct"], t["vib_max_mms"]
    add(vm >= L["vib_cd_mms"], "ST_VIB_ZONE_D", "High", f"Bearing vibration {vm:.1f} mm/s: ISO 20816-2 zone D", "rotor")
    add(ed <= L["hp_eff_very_low_pts"], "ST_HP_EFF_VERY_LOW", "High",
        f"HP efficiency {t['hp_eff_pct']:.1f} %, {ed:+.1f} points against {t['hp_eff_expected_pct']:.1f} % expected", "hp", "solid_particle_erosion")
    add(abs(r["thrust_pos_mm"]) > L["thrust_pos_mm"], "ST_THRUST_POS", "High", f"Rotor axial position {r['thrust_pos_mm']:+.2f} mm", "thrust", "thrust_bearing_wear")
    add(pd < L["power_dev_low_pct"], "ST_POWER_LOW", "Medium",
        f"Output {r['power_mw']:.1f} MW, {pd:+.1f} % against {t['power_expected_mw']:.1f} MW expected ({t['lost_mw']:.2f} MW lost)", "lp", "lp_blade_damage")
    add(L["hp_eff_very_low_pts"] < ed <= L["hp_eff_low_pts"], "ST_HP_EFF_LOW", "Medium",
        f"HP efficiency {t['hp_eff_pct']:.1f} %, {ed:+.1f} points against expected", "hp", "hp_deposits")
    add(wr > L["wheel_ratio_high"], "ST_WHEEL_PRESS_HIGH", "Medium",
        f"First-stage pressure {r['wheel_press_bara']:.1f} bar(a), {wr:.3f} x expected: blade path narrower", "hp", "hp_deposits")
    add(wr < L["wheel_ratio_low"], "ST_WHEEL_PRESS_LOW", "Medium",
        f"First-stage pressure {r['wheel_press_bara']:.1f} bar(a), {wr:.3f} x expected: blade path wider", "hp", "solid_particle_erosion")
    add(t["cond_press_dev_mbar"] > L["cond_press_dev_mbar"], "ST_COND_PRESS_HIGH", "Medium",
        f"Condenser {r['cond_press_mbar']:.0f} mbar, {t['cond_press_dev_mbar']:+.0f} mbar against the cooling water ({t['backpressure_loss_mw']:.2f} MW)",
        "condenser", "condenser_fouling")
    add(t["cond_ttd_k"] > L["ttd_high_k"], "ST_TTD_HIGH", "Medium", f"Condenser TTD {t['cond_ttd_k']:.1f} K", "condenser", "condenser_fouling")
    add(t["valve_flow_ratio"] < L["valve_ratio_low"], "ST_VALVE_CAPACITY_LOW", "Medium",
        f"Governor valves pass {t['valve_flow_ratio']:.2f} x the expected flow at {r['gv_lift_pct']:.0f} % lift", "valves", "governor_valve")
    add(L["vib_bc_mms"] <= vm < L["vib_cd_mms"], "ST_VIB_ZONE_C", "Medium", f"Bearing vibration {vm:.1f} mm/s: ISO 20816-2 zone C", "rotor", "rotor_unbalance")
    add(r["thrust_pad_c"] > L["thrust_pad_c"], "ST_THRUST_TEMP", "Medium", f"Thrust pad {r['thrust_pad_c']:.0f} °C", "thrust", "thrust_bearing_wear")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
