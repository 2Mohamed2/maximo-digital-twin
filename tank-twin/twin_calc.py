"""The crude oil storage tank twin's expectations (TK-2701, external floating roof).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Inventory from one gauge reading (API MPMS Ch. 12.1.1 sequence, Ch. 11.1 Table 54A for the VCF):
    TOV  = A x level                                   total observed volume (constant cross-section A replaces the strapping table)
    FW   = A x free water level
    CTSh = 1 + 2 a dTs + a^2 dTs^2,  dTs = T - 15      steel shell grows with temperature (Ts = product temperature here)
    VCF  = exp(-a15 dT (1 + 0.8 a15 dT)), a15 = K0 / rho15^2, dT = T - 15
    FRA  = roof mass / (rho15 x VCF)  when the roof floats (it displaces its own weight of liquid), else 0
    GOV  = (TOV - FW) x CTSh - FRA ;  GSV = GOV x VCF  (m3 at 15 degC) ;  mass = GSV x rho15
Mass balance:
    movement imbalance = GSV(closing gauge) - GSV(opening gauge) - metered volume (at 15 degC, + in, - out)
    static loss rate   = (GSV(start of the quiet period) - GSV(end)) / hours           (a leak shows here, a meter error does not)
Overfill (API 2350): time to HH = (HH - level) x A / net fill rate.
Floating roof (Archimedes): expected draft = roof mass / (rho_obs x roof area); measured draft = level + rim height - mean roof rim
    height; tilt = highest - lowest of the three roof rim heights.
Inspection (API 653): corrosion rate = (previous - present thickness) / years between;
    bottom minimum remaining thickness at the next internal inspection MRT = t - rate x years still to go;
    shell external UT interval = min((t - t_min) / (2 x rate), 15 years).
"""
import math


def _k(twin):
    d = twin["design"]
    g, p, r, o, s, b = d["geometry"], d["product"], d["roof"], d["overfill"], d["shell"], d["bottom"]
    return dict(A=g["area_m2"], a=g["shell_alpha_per_c"], tb=g["strapping_base_temp_c"], k0=p["k0"], k1=p["k1"],
                m=r["mass_kg"], ar=r["roof_area_m2"], rim=r["rim_height_m"] * 1000, leg=r["leg_height_m"] * 1000,
                ch=o["ch_m"] * 1000, hh=o["hh_m"] * 1000, mw=o["mw_m"] * 1000, rt=o["response_time_min"],
                stmin=s["tmin_mm"], utcap=s["ut_interval_cap_y"], btmin=b["tmin_next_mm"], bint=b["internal_interval_y"])


def float_mm(k, rho=850.0):
    """Level (mm) above which the roof floats: leg height + nominal draft (fixed, from the nominal density)."""
    return k["leg"] + k["m"] / (rho * k["ar"]) * 1000


# ---- the same arithmetic in Python and as pandas strings ---------------------------------------------------------------------
def vcf(k, t, rho):
    al = k["k0"] / rho ** 2 + k["k1"] / rho
    dt = t - 15.0
    return math.exp(-al * dt * (1 + 0.8 * al * dt))


def ctsh(k, t):
    d = t - k["tb"]
    return 1 + 2 * k["a"] * d + k["a"] ** 2 * d ** 2


def gsv(k, level, t, water, rho, fl):
    v = vcf(k, t, rho)
    fra = k["m"] / (rho * v) if level >= fl else 0.0
    gov = (k["A"] * level / 1000 - k["A"] * water / 1000) * ctsh(k, t) - fra
    return gov * v


def _vcf_s(k, T, R="df['DENSITY15_KGM3']"):
    al = f"({k['k0']} / {R} ** 2 + {k['k1']} / {R})"
    return f"np.exp(-{al} * ({T} - 15.0) * (1 + 0.8 * {al} * ({T} - 15.0)))"


def _ctsh_s(k, T):
    return f"(1 + 2 * {k['a']} * ({T} - {k['tb']}) + {k['a']} ** 2 * ({T} - {k['tb']}) ** 2)"


def _gsv_s(k, L, T, fl):
    R, W = "df['DENSITY15_KGM3']", "df['WATER_LEVEL_MM']"
    V = _vcf_s(k, T)
    FRA = f"np.where({L} >= {fl}, {k['m']} / ({R} * {V}), 0.0)"
    return f"((({k['A']} * {L} / 1000 - {k['A']} * {W} / 1000) * {_ctsh_s(k, T)} - {FRA}) * {V})"


def _parts(twin):
    k = _k(twin)
    fl = float_mm(k)
    c = lambda n: f"df['{n}']"
    L, T = c("LEVEL_MM"), c("PRODUCT_TEMP_C")
    GSV = _gsv_s(k, L, T, fl)
    GMO, GMC = _gsv_s(k, c("MV_OPEN_LEVEL_MM"), c("MV_OPEN_TEMP_C"), fl), _gsv_s(k, c("MV_CLOSE_LEVEL_MM"), c("MV_CLOSE_TEMP_C"), fl)
    GSO, GSC = _gsv_s(k, c("ST_OPEN_LEVEL_MM"), c("ST_OPEN_TEMP_C"), fl), _gsv_s(k, c("ST_CLOSE_LEVEL_MM"), c("ST_CLOSE_TEMP_C"), fl)
    IMB = f"({GMC} - {GMO} - df['MV_METER_M3'])"
    PCT = f"({IMB} / np.maximum(np.abs(df['MV_METER_M3']), 1.0) * 100)"
    LOSS = f"(({GSO} - {GSC}) / np.maximum(df['ST_HOURS'], 0.1))"
    NET = "(df['INFLOW_M3H'] - df['OUTFLOW_M3H'])"
    TTH = f"np.where({NET} > 1.0, np.maximum({k['hh']} - {L}, 0.0) * {k['A']} / 1000 / np.maximum({NET}, 1.0) * 60, 9999.0)"
    HMAX = "np.maximum(np.maximum(df['ROOF_H1_MM'], df['ROOF_H2_MM']), df['ROOF_H3_MM'])"
    HMIN = "np.minimum(np.minimum(df['ROOF_H1_MM'], df['ROOF_H2_MM']), df['ROOF_H3_MM'])"
    HMEAN = "((df['ROOF_H1_MM'] + df['ROOF_H2_MM'] + df['ROOF_H3_MM']) / 3)"
    DRAFT_EXP = f"({k['m']} / (df['DENSITY15_KGM3'] * {_vcf_s(k, T)} * {k['ar']}) * 1000)"
    RATIO = f"(({L} + {k['rim']} - {HMEAN}) / {DRAFT_EXP})"
    BR = "((df['BOTTOM_T_PREV_MM'] - df['BOTTOM_T_MM']) / np.maximum(df['BOTTOM_YEARS_BETWEEN'], 0.1))"
    MRT = f"(df['BOTTOM_T_MM'] - {BR} * np.maximum({k['bint']} - df['YEARS_SINCE_INTERNAL'], 0.0))"
    SR = "((df['SHELL_T_PREV_MM'] - df['SHELL_T_MM']) / np.maximum(df['SHELL_YEARS_BETWEEN'], 0.1))"
    UTI = f"np.minimum((df['SHELL_T_MM'] - {k['stmin']}) / (2 * np.maximum({SR}, 0.001)), {k['utcap']})"
    return dict(k=k, fl=fl, L=L, T=T, GSV=GSV, IMB=IMB, PCT=PCT, LOSS=LOSS, TTH=TTH, HMAX=HMAX, HMIN=HMIN, RATIO=RATIO,
                BR=BR, MRT=MRT, SR=SR, UTI=UTI)


def monitor_expressions(twin):
    p = _parts(twin)
    k, L, T = p["k"], p["L"], p["T"]
    V = _vcf_s(k, T)
    return [
        ("TOV_M3", f"{k['A']} * {L} / 1000"),
        ("CTSH", _ctsh_s(k, T)),
        ("VCF", V),
        ("FRA_M3", f"np.where({L} >= {p['fl']}, {k['m']} / (df['DENSITY15_KGM3'] * {V}), 0.0)"),
        ("GSV_M3", p["GSV"]),
        ("MASS_T", f"{p['GSV']} * df['DENSITY15_KGM3'] / 1000"),
        ("ROOM_TO_HH_M3", f"({k['hh']} - {L}) * {k['A']} / 1000"),
        ("TIME_TO_HH_MIN", p["TTH"]),
        ("GAUGE_DIFF_MM", f"{L} - df['LEVEL2_MM']"),
        ("MV_IMBALANCE_M3", p["IMB"]),
        ("MV_IMBALANCE_PCT", p["PCT"]),
        ("STATIC_LOSS_M3H", p["LOSS"]),
        ("ROOF_TILT_MM", f"{p['HMAX']} - {p['HMIN']}"),
        ("ROOF_DRAFT_RATIO", p["RATIO"]),
        ("BOTTOM_RATE_MM_Y", p["BR"]),
        ("BOTTOM_MRT_MM", p["MRT"]),
        ("BOTTOM_LIFE_Y", f"(df['BOTTOM_T_MM'] - {k['btmin']}) / np.maximum({p['BR']}, 0.001)"),
        ("SHELL_RATE_MM_Y", p["SR"]),
        ("SHELL_UT_INTERVAL_Y", p["UTI"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    fl = float_mm(k)
    rho, w, L, T = r["density15_kgm3"], r["water_level_mm"], r["level_mm"], r["product_temp_c"]
    g = lambda lv, tt: gsv(k, lv, tt, w, rho, fl)
    v = vcf(k, T, rho)
    G = g(L, T)
    imb = g(r["mv_close_level_mm"], r["mv_close_temp_c"]) - g(r["mv_open_level_mm"], r["mv_open_temp_c"]) - r["mv_meter_m3"]
    net = r["inflow_m3h"] - r["outflow_m3h"]
    hs = (r["roof_h1_mm"], r["roof_h2_mm"], r["roof_h3_mm"])
    draft_exp = k["m"] / (rho * v * k["ar"]) * 1000
    br = (r["bottom_t_prev_mm"] - r["bottom_t_mm"]) / max(r["bottom_years_between"], 0.1)
    sr = (r["shell_t_prev_mm"] - r["shell_t_mm"]) / max(r["shell_years_between"], 0.1)
    return {
        "tov_m3": k["A"] * L / 1000, "ctsh": ctsh(k, T), "vcf": v,
        "fra_m3": k["m"] / (rho * v) if L >= fl else 0.0,
        "gsv_m3": G, "mass_t": G * rho / 1000,
        "room_to_hh_m3": (k["hh"] - L) * k["A"] / 1000,
        "time_to_hh_min": max(k["hh"] - L, 0.0) * k["A"] / 1000 / max(net, 1.0) * 60 if net > 1.0 else 9999.0,
        "gauge_diff_mm": L - r["level2_mm"],
        "mv_imbalance_m3": imb, "mv_imbalance_pct": imb / max(abs(r["mv_meter_m3"]), 1.0) * 100,
        "static_loss_m3h": (g(r["st_open_level_mm"], r["st_open_temp_c"]) - g(r["st_close_level_mm"], r["st_close_temp_c"])) / max(r["st_hours"], 0.1),
        "roof_tilt_mm": max(hs) - min(hs),
        "roof_draft_ratio": (L + k["rim"] - sum(hs) / 3) / draft_exp,
        "bottom_rate_mm_y": br, "bottom_mrt_mm": r["bottom_t_mm"] - br * max(k["bint"] - r["years_since_internal"], 0.0),
        "bottom_life_y": (r["bottom_t_mm"] - k["btmin"]) / max(br, 0.001),
        "shell_rate_mm_y": sr, "shell_ut_interval_y": min((r["shell_t_mm"] - k["stmin"]) / (2 * max(sr, 0.001)), k["utcap"]),
    }


def alert_rules(twin):
    Lm = twin["twin_model"]["limits"]
    p = _parts(twin)
    k, L = p["k"], p["L"]
    land = p["fl"] + Lm["roof_landing_margin_mm"]
    return [
        ("TANK_LEVEL_CH", f"({L} >= {k['ch']}) | (df['LEVEL2_MM'] >= {k['ch']})", "Critical", "overfill"),
        ("TANK_STATIC_LOSS", f"(df['ST_HOURS'] >= {Lm['static_min_hours']}) & ({p['LOSS']} > {Lm['static_loss_m3h']})", "Critical", "bottom_leak"),
        ("TANK_LEVEL_HH", f"(({L} >= {k['hh']}) | (df['HH_SWITCH'] > 0.5)) & ({L} < {k['ch']}) & (df['LEVEL2_MM'] < {k['ch']})", "High", "overfill"),
        ("TANK_ROOF_TILT", f"({p['HMAX']} - {p['HMIN']}) > {Lm['roof_tilt_alert_mm']}", "High", "roof_tilt"),
        ("TANK_RIM_GAS", f"df['RIM_GAS_LEL_PCT'] > {Lm['rim_lel_alert_pct']}", "High", "rim_seal_damage"),
        ("TANK_BOTTOM_MRT", f"{p['MRT']} < {k['btmin']}", "High", "bottom_corrosion"),
        ("TANK_SHELL_TMIN", f"df['SHELL_T_MM'] < {k['stmin']}", "High", None),
        ("TANK_OVERFILL_TIME", f"({p['TTH']} < {k['rt']}) & ({L} < {k['hh']}) & (df['HH_SWITCH'] < 0.5)", "Medium", "overfill"),
        ("TANK_GAUGE_MISMATCH", f"np.abs({L} - df['LEVEL2_MM']) > {Lm['gauge_diff_alert_mm']}", "Medium", "gauge_drift"),
        ("TANK_METER_IMBALANCE", f"(np.abs(df['MV_METER_M3']) >= {Lm['meter_min_volume_m3']}) & (np.abs({p['PCT']}) > {Lm['meter_imbalance_pct']})", "Medium", "meter_error"),
        ("TANK_ROOF_LOW", f"({L} >= {land}) & ({p['RATIO']} > {Lm['roof_draft_ratio_alert']})", "Medium", "roof_drain_blocked"),
        ("TANK_ROOF_LANDING", f"{L} < {land}", "Medium", None),
        ("TANK_BOTTOM_RATE", f"{p['BR']} > {Lm['bottom_rate_alert_mm_y']}", "Medium", "bottom_corrosion"),
        ("TANK_UT_OVERDUE", f"df['YEARS_SINCE_UT'] > {p['UTI']}", "Medium", None),
        ("TANK_INTERNAL_OVERDUE", f"df['YEARS_SINCE_INTERNAL'] > {k['bint']}", "Medium", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    Lm = twin["twin_model"]["limits"]
    k = _k(twin)
    land = float_mm(k) + Lm["roof_landing_margin_mm"]
    L = r["level_mm"]
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    add(L >= k["ch"] or r["level2_mm"] >= k["ch"], "TANK_LEVEL_CH", "Critical",
        f"Level {max(L, r['level2_mm']) / 1000:.3f} m at or above critical high {k['ch'] / 1000:.3f} m", "operation", "overfill")
    add(r["st_hours"] >= Lm["static_min_hours"] and t["static_loss_m3h"] > Lm["static_loss_m3h"], "TANK_STATIC_LOSS", "Critical",
        f"Tank lost {t['static_loss_m3h']:.2f} m³/h at 15 °C over a {r['st_hours']:.0f} h quiet period", "bottom", "bottom_leak")
    add((L >= k["hh"] or r["hh_switch"] > 0.5) and L < k["ch"] and r["level2_mm"] < k["ch"], "TANK_LEVEL_HH", "High",
        f"High-high level: ATG {L / 1000:.3f} m, independent alarm {'ON' if r['hh_switch'] > 0.5 else 'off'} (HH {k['hh'] / 1000:.3f} m)", "operation", "overfill")
    add(t["roof_tilt_mm"] > Lm["roof_tilt_alert_mm"], "TANK_ROOF_TILT", "High", f"Roof tilt {t['roof_tilt_mm']:.0f} mm across the three sensors", "roof", "roof_tilt")
    add(r["rim_gas_lel_pct"] > Lm["rim_lel_alert_pct"], "TANK_RIM_GAS", "High", f"Gas above the rim seal {r['rim_gas_lel_pct']:.0f} % LEL", "seal", "rim_seal_damage")
    add(t["bottom_mrt_mm"] < k["btmin"], "TANK_BOTTOM_MRT", "High",
        f"Bottom at the next internal inspection {t['bottom_mrt_mm']:.2f} mm, below {k['btmin']} mm", "bottom", "bottom_corrosion")
    add(r["shell_t_mm"] < k["stmin"], "TANK_SHELL_TMIN", "High", f"Shell {r['shell_t_mm']:.2f} mm, below t_min {k['stmin']} mm", "shell")
    add(t["time_to_hh_min"] < k["rt"] and L < k["hh"] and r["hh_switch"] < 0.5, "TANK_OVERFILL_TIME", "Medium",
        f"High-high in {t['time_to_hh_min']:.0f} min at the present rate, less than the {k['rt']:.0f} min response time", "operation", "overfill")
    add(abs(t["gauge_diff_mm"]) > Lm["gauge_diff_alert_mm"], "TANK_GAUGE_MISMATCH", "Medium",
        f"ATG and independent radar differ by {t['gauge_diff_mm']:+.0f} mm", "gauge", "gauge_drift")
    add(abs(r["mv_meter_m3"]) >= Lm["meter_min_volume_m3"] and abs(t["mv_imbalance_pct"]) > Lm["meter_imbalance_pct"], "TANK_METER_IMBALANCE", "Medium",
        f"Last movement: tank {t['mv_imbalance_m3']:+.0f} m³ ({t['mv_imbalance_pct']:+.2f} %) against the meter", "meter", "meter_error")
    add(L >= land and t["roof_draft_ratio"] > Lm["roof_draft_ratio_alert"], "TANK_ROOF_LOW", "Medium",
        f"Roof floats {t['roof_draft_ratio']:.2f} x deeper than its weight explains", "roof", "roof_drain_blocked")
    add(L < land, "TANK_ROOF_LANDING", "Medium", f"Level {L / 1000:.2f} m: roof landed or close to its legs", "roof")
    add(t["bottom_rate_mm_y"] > Lm["bottom_rate_alert_mm_y"], "TANK_BOTTOM_RATE", "Medium", f"Bottom corrosion {t['bottom_rate_mm_y']:.2f} mm/y", "bottom", "bottom_corrosion")
    add(r["years_since_ut"] > t["shell_ut_interval_y"], "TANK_UT_OVERDUE", "Medium",
        f"Shell UT survey {r['years_since_ut']:.1f} y old, interval {t['shell_ut_interval_y']:.1f} y", "shell")
    add(r["years_since_internal"] > k["bint"], "TANK_INTERNAL_OVERDUE", "Medium", f"Internal inspection {r['years_since_internal']:.1f} y ago", "bottom")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
