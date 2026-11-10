"""The 132 kV XLPE cable twin's expectations (Prysmian 1x1200 mm2 Al, IEC 60287, DTS real-time thermal rating).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (twin viewer, tests)

Losses and thermal circuit (IEC 60287-1-1 / 60287-2-1, per phase, per metre):
  R(theta) = R20 (1 + alpha (theta - 20)) (1 + ys + yp)          ac resistance (skin + proximity, trefoil)
  Wc = I^2 R(theta_c)   Wd = omega C U0^2 tan delta             conductor and dielectric losses
  screen rise over soil ambient   (Wc (1 + lambda1) + Wd) (T3 + T4)
  conductor rise over screen      Wc T1 + Wd T1 / 2
  rating I = sqrt((90 - theta_a - Wd (T1/2 + T3 + T4)) / (R90 (T1 + (1 + lambda1)(T3 + T4))))

Why the equivalent current (like the transformer twin's thermal image):
  Monitor evaluates single 5-minute readings; it cannot integrate the soil's 10-hour thermal response. The real-time
  thermal rating (RTTR) unit already filters I^2 through the soil time constant and reports it as the equivalent current
  I_eq. The steady-state IEC 60287 screen temperature at (I_eq, soil ambient) then follows the measured DTS temperature
  through load swings, and a lasting positive residual at the road crossing means the soil there has dried out.
  The conductor-over-screen rise has a ~30 min time constant and uses the present current.
Conductor temperature (RTTR estimate): DTS screen temperature at the hottest point + Wc T1 + Wd T1/2, with R evaluated by
  two fixed-point steps (closed form, so Monitor and Python give identical numbers).
"""
import math

NSEG = 12


def _k(twin):
    d = twin["design"]
    th = d["thermal"]
    return dict(R20=th["r20_ohm_m"], a=th["alpha20"], f=1 + th["ys"] + th["yp"], R90=th["r90_ac_ohm_m"], WD=th["wd_w_m"],
                T1=th["T1"], T3=th["T3"], T4N=th["T4_normal"], T4X=th["T4_crossing"], lam=th["lambda1_cross_bonded"],
                tmax=th["theta_max_c"], L=d["circuit"]["length_km"], kterm=d["terminations"]["connector_rise_k_at_1000a"],
                sh=d["sheath"]["expected_ratio"])


def r_ac(k, theta):
    return k["R20"] * (1 + k["a"] * (theta - 20)) * k["f"]


def screen_expected(k, ta, ieq, t4):
    """Steady IEC 60287 screen temperature at the equivalent current (two closed-form steps for R(theta_c))."""
    i2 = ieq * ieq
    tc1 = ta + i2 * r_ac(k, ta + 40) * (k["T1"] + (1 + k["lam"]) * (k["T3"] + t4)) + k["WD"] * (k["T1"] / 2 + k["T3"] + t4)
    return ta + (i2 * r_ac(k, tc1) * (1 + k["lam"]) + k["WD"]) * (k["T3"] + t4)


def conductor_from_screen(k, ts, i):
    i2 = i * i
    tc0 = ts + i2 * r_ac(k, ts + 10) * k["T1"] + k["WD"] * k["T1"] / 2
    return ts + i2 * r_ac(k, tc0) * k["T1"] + k["WD"] * k["T1"] / 2


def rating(k, ta, t4):
    num = k["tmax"] - ta - k["WD"] * (0.5 * k["T1"] + k["T3"] + t4)
    return math.sqrt(max(num, 0.0) / (k["R90"] * (k["T1"] + (1 + k["lam"]) * (k["T3"] + t4))))


def _parts(twin):
    k = _k(twin)
    R = lambda th: f"({k['R20']} * (1 + {k['a']} * (({th}) - 20)) * {k['f']})"
    I = "((df['CURRENT_L1_A'] + df['CURRENT_L2_A'] + df['CURRENT_L3_A']) / 3)"
    IEQ = "df['LOAD_EQ_A'].clip(lower=0)"
    TA = "df['SOIL_AMBIENT_C']"

    def scr(t4):
        tc1 = (f"({TA} + {IEQ} ** 2 * {R(TA + ' + 40')} * {k['T1'] + (1 + k['lam']) * (k['T3'] + t4)} "
               f"+ {k['WD'] * (k['T1'] / 2 + k['T3'] + t4)})")
        return f"({TA} + ({IEQ} ** 2 * {R(tc1)} * {1 + k['lam']} + {k['WD']}) * {k['T3'] + t4})"
    TS = "df['DTS_MAX_C']"
    TC0 = f"({TS} + {I} ** 2 * {R(TS + ' + 10')} * {k['T1']} + {k['WD'] * k['T1'] / 2})"
    TC = f"({TS} + {I} ** 2 * {R(TC0)} * {k['T1']} + {k['WD'] * k['T1'] / 2})"
    t4 = k["T4X"]
    RAT = (f"np.sqrt(({k['tmax']} - {TA} - {k['WD'] * (0.5 * k['T1'] + k['T3'] + t4)}).clip(lower=0) / "
           f"{k['R90'] * (k['T1'] + (1 + k['lam']) * (k['T3'] + t4))})")
    TE = f"(df['AIR_TEMP_C'] + {k['kterm']} * ({I} / 1000) ** 2)"
    FOK = f"(df['DTS_FIBRE_KM'] >= {k['L']} - {twin['twin_model']['limits']['fibre_shortfall_km']})"
    return dict(R=R, I=I, IEQ=IEQ, XE=scr(k["T4X"]), NE=scr(k["T4N"]), TC=TC, RAT=RAT, TE=TE, FOK=FOK, k=k)


def monitor_expressions(twin):
    p, k = _parts(twin), _k(twin)
    return [
        ("LOAD_A", p["I"]),
        ("CROSSING_EXPECTED_C", p["XE"]),
        ("CROSSING_RESIDUAL_K", f"df['DTS_SEG07_C'] - {p['XE']}"),
        ("NORMAL_EXPECTED_C", p["NE"]),
        ("CONDUCTOR_TEMP_C", p["TC"]),
        ("RATING_A", p["RAT"]),
        ("RATING_UTILISATION", f"{p['IEQ']} / {p['RAT']}.clip(lower=1)"),
        ("SHEATH_EXPECTED_A", f"{k['sh']} * {p['I']}"),
        ("SHEATH_RATIO", f"df['SHEATH_CURRENT_A'] / {p['I']}.clip(lower=1)"),
        ("TERM_EXPECTED_C", p["TE"]),
        ("TERM_RESIDUAL_K", f"df['TERM_A_TEMP_C'] - {p['TE']}"),
        ("LOSSES_KW_KM", f"3 * ({p['I']} ** 2 * {p['R'](p['TC'])} * {1 + k['lam']} + {k['WD']})"),
        ("FIBRE_SHORTFALL_KM", f"{k['L']} - df['DTS_FIBRE_KM']"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    i = (r["current_l1_a"] + r["current_l2_a"] + r["current_l3_a"]) / 3
    ieq = max(r["load_eq_a"], 0.0)
    ta = r["soil_ambient_c"]
    xe = screen_expected(k, ta, ieq, k["T4X"])
    ne = screen_expected(k, ta, ieq, k["T4N"])
    tc = conductor_from_screen(k, r["dts_max_c"], i)
    rat = rating(k, ta, k["T4X"])
    te = r["air_temp_c"] + k["kterm"] * (i / 1000) ** 2
    return {
        "load_a": i, "crossing_expected_c": xe, "crossing_residual_k": r["dts_seg07_c"] - xe, "normal_expected_c": ne,
        "conductor_temp_c": tc, "rating_a": rat, "rating_utilisation": ieq / max(rat, 1),
        "sheath_expected_a": k["sh"] * i, "sheath_ratio": r["sheath_current_a"] / max(i, 1),
        "term_expected_c": te, "term_residual_k": r["term_a_temp_c"] - te,
        "losses_kw_km": 3 * (i * i * r_ac(k, tc) * (1 + k["lam"]) + k["WD"]), "fibre_shortfall_km": k["L"] - r["dts_fibre_km"],
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    return [
        ("UGC_CONDUCTOR_LIMIT", f"{p['FOK']} & ({p['TC']} > {L['conductor_max_c']})", "Critical", "overload"),
        ("UGC_CONDUCTOR_HOT", f"{p['FOK']} & ({p['TC']} > {L['conductor_alert_c']}) & ({p['TC']} <= {L['conductor_max_c']})", "High", "overload"),
        ("UGC_CROSSING_HOT", f"{p['FOK']} & ((df['DTS_SEG07_C'] - {p['XE']}) > {L['crossing_residual_alert_k']}) & ({p['IEQ']} > {L['steady_load_min_a']})", "Medium", "soil_drying"),
        ("UGC_OVERLOAD", f"({p['IEQ']} / {p['RAT']}.clip(lower=1)) > {L['utilisation_alert']}", "High", "overload"),
        ("UGC_RATING_HIGH", f"(({p['IEQ']} / {p['RAT']}.clip(lower=1)) > {L['utilisation_warn']}) & (({p['IEQ']} / {p['RAT']}.clip(lower=1)) <= {L['utilisation_alert']})", "Low", None),
        ("UGC_BONDING_FAULT", f"((df['SHEATH_CURRENT_A'] / {p['I']}.clip(lower=1)) > {L['sheath_ratio_alert']}) & ({p['I']} > 100)", "High", "cross_bonding_fault"),
        ("UGC_JACKET_LEAKAGE", f"df['SHEATH_LEAKAGE_MA'] > {L['leakage_alert_ma']}", "Medium", "jacket_damage"),
        ("UGC_PD_JOINT", f"(df['PD_JOINT_PC'] > {L['pd_alert_pc']}) & (df['PD_JOINT_PC'] <= {L['pd_high_pc']})", "Medium", "joint_pd"),
        ("UGC_PD_JOINT_HIGH", f"df['PD_JOINT_PC'] > {L['pd_high_pc']}", "High", "joint_pd"),
        ("UGC_PD_TERMINATION", f"df['PD_TERM_PC'] > {L['pd_alert_pc']}", "Medium", None),
        ("UGC_TERMINATION_HOT", f"(df['TERM_A_TEMP_C'] - {p['TE']}) > {L['term_residual_alert_k']}", "Medium", "termination_overheating"),
        ("UGC_DTS_FIBRE", f"~{p['FOK']}", "Medium", "dts_fibre_break"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    fok = r["dts_fibre_km"] >= k["L"] - L["fibre_shortfall_km"]
    tc, u = t["conductor_temp_c"], t["rating_utilisation"]
    add(fok and tc > L["conductor_max_c"], "UGC_CONDUCTOR_LIMIT", "Critical", f"Conductor {tc:.0f} °C at km {r['dts_max_km']:.2f} (limit 90 °C)", "cable", "overload")
    add(fok and L["conductor_alert_c"] < tc <= L["conductor_max_c"], "UGC_CONDUCTOR_HOT", "High", f"Conductor {tc:.0f} °C at km {r['dts_max_km']:.2f}", "cable", "overload")
    add(fok and t["crossing_residual_k"] > L["crossing_residual_alert_k"] and r["load_eq_a"] > L["steady_load_min_a"], "UGC_CROSSING_HOT", "Medium",
        f"Road crossing {t['crossing_residual_k']:.1f} K above IEC 60287 at {r['load_eq_a']:.0f} A: soil drying out", "crossing", "soil_drying")
    add(u > L["utilisation_alert"], "UGC_OVERLOAD", "High", f"Equivalent load {r['load_eq_a']:.0f} A = {u * 100:.0f} % of the dynamic rating {t['rating_a']:.0f} A", "cable", "overload")
    add(L["utilisation_warn"] < u <= L["utilisation_alert"], "UGC_RATING_HIGH", "Low", f"{u * 100:.0f} % of the dynamic rating", "cable")
    add(t["sheath_ratio"] > L["sheath_ratio_alert"] and t["load_a"] > 100, "UGC_BONDING_FAULT", "High",
        f"Sheath current {r['sheath_current_a']:.0f} A = {t['sheath_ratio'] * 100:.0f} % of the load (cross-bonded: ~3 %)", "linkbox", "cross_bonding_fault")
    add(r["sheath_leakage_ma"] > L["leakage_alert_ma"], "UGC_JACKET_LEAKAGE", "Medium", f"Jacket leakage {r['sheath_leakage_ma']:.1f} mA", "cable", "jacket_damage")
    add(L["pd_alert_pc"] < r["pd_joint_pc"] <= L["pd_high_pc"], "UGC_PD_JOINT", "Medium", f"PD {r['pd_joint_pc']:.0f} pC at joint J4", "joint", "joint_pd")
    add(r["pd_joint_pc"] > L["pd_high_pc"], "UGC_PD_JOINT_HIGH", "High", f"PD {r['pd_joint_pc']:.0f} pC at joint J4", "joint", "joint_pd")
    add(r["pd_term_pc"] > L["pd_alert_pc"], "UGC_PD_TERMINATION", "Medium", f"PD {r['pd_term_pc']:.0f} pC at sealing end A", "termination")
    add(t["term_residual_k"] > L["term_residual_alert_k"], "UGC_TERMINATION_HOT", "Medium",
        f"Sealing end A {r['term_a_temp_c']:.0f} °C, {t['term_residual_k']:.0f} K above expected", "termination", "termination_overheating")
    add(not fok, "UGC_DTS_FIBRE", "Medium", f"DTS sees only {r['dts_fibre_km']:.2f} of {k['L']:.1f} km: fibre break, route beyond is blind", "dts", "dts_fibre_break")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
