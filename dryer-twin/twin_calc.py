"""The paper machine dryer section twin's expectations (PM-4301, 50 cylinders, cascade steam system, closed hood).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Sheet side (what the sheet loses):
    production P = speed (m/min) x 60 x width (m) x basis weight (g/m2) / 1e6               [t/h at the reel]
    fibre F = P x 1000 x (1 - reel moisture / 100)                                            [kg/h bone dry]
    water evaporated E = F x ((100 - d_in) / d_in - m / (100 - m))                            [kg/h]
  d_in = dryness entering the dryers (%), m = reel moisture (%).
    evaporation rate = E / (n x pi x D x face)                                                [kg/m2 h of cylinder shell]
    specific steam consumption SSC = fresh steam / E                                          [kg steam / kg water]
  TAPPI TIP 0404-33: top machines use about 1.3 kg/kg. Steam cost per tonne = fresh steam x price / P.
Steam side (what the steam gives):
    saturation temperature T_sat(p) and latent heat h_fg(p) from the IAPWS-IF97 steam table (np.interp on absolute pressure)
    steam-side evaporation E_s = (fresh steam - vent) x h_fg(p3) / q,   q = SSC_design x h_fg(p3 design) x (1 - vent_design)
    balance residual = E / E_s - 1: a meter (steam flow, QCS moisture, press dryness) is wrong when the two disagree.
Condensate removal (TAPPI TIP 0404-31 and 0404-33):
    steam-to-surface difference dT_g = T_sat(p_g) - mean surface temperature of group g     (well-performing: 15-30 C)
    cold cylinder = group mean - coldest cylinder of the group                               (one flooded cylinder)
    differential pressure of every group                                                     (stationary syphons: 15-35 kPa)
    blow-through % = separator vapour / condensate of groups 3 and 4 x 100                  (typically 10-15 %)
    expected blow-through = bt_design x sqrt(DP / DP_ref)       (orifice-like fit; replace with your syphon curve)
Drying (fabric and pockets):
    drying coefficient K = E / sum_g(A_g x (T_surface_g - T_sheet)), compared with its design value: the evaporation the
    machine gets per degree of hot surface. A filled fabric or wet pockets lower it; a flooded group does not.
Hood: exhaust humidity, and the supply/exhaust air ratio of the closed hood.
"""
import math

P0 = 1.01325          # bar, atmosphere
GROUPS = (1, 2, 3, 4)


def interp(x, xs, ys):
    """Linear interpolation clamped at the ends, the same as numpy.interp."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            return ys[i - 1] + (x - xs[i - 1]) * (ys[i] - ys[i - 1]) / (xs[i] - xs[i - 1])
    return ys[-1]


def tsat(k, p_barg):
    return interp(p_barg + P0, k["tp"], k["tt"])


def hfg(k, p_barg):
    return interp(p_barg + P0, k["tp"], k["th"])


def evaporation(m_speed, width, bw, moist, dry_in):
    """(production t/h, fibre kg/h, water evaporated kg/h) from the sheet side."""
    prod = m_speed * 60 * width * bw / 1e6
    fib = prod * 1000 * (1 - moist / 100)
    return prod, fib, fib * ((100 - dry_in) / dry_in - moist / (100 - moist))


def _k(twin):
    d = twin["design"]
    m, c, s, h, ec = d["machine"], d["cylinders"], d["steam"], d["hood"], d["economics"]
    k = dict(tp=s["table_p_bara"], tt=s["table_tsat_c"], th=s["table_hfg_kjkg"])
    acyl = math.pi * c["diameter_m"] * c["face_m"]
    ag = [n * acyl for n in c["groups"]]
    prod_d, fib_d, evap_d = evaporation(m["speed_mpm"], m["width_m"], m["basis_weight_gsm"], m["reel_moisture_pct"], m["press_dryness_pct"])
    ts_d = [tsat(k, p) - dt for p, dt in zip(s["p_barg"], s["dt_surface_c"])]
    kd_d = evap_d / sum(a * (t - s["t_sheet_c"]) for a, t in zip(ag, ts_d))
    q = s["ssc_design"] * hfg(k, s["p_barg"][2]) * (1 - s["vent_design_pct"] / 100)
    k.update(width=m["width_m"], acyl=acyl, ag=ag, atot=sum(ag), prod_d=prod_d, fib_d=fib_d, evap_d=evap_d, ts_d=ts_d, kd_d=kd_d, q=q,
             tsh=s["t_sheet_c"], ssc_d=s["ssc_design"], bt_d=s["bt_design_pct"], dp_ref=s["bt_dp_ref_kpa"], dp_d=s["dp_kpa"],
             dp_lo=s["dp_min_kpa"], dp_hi=s["dp_max_kpa"], vent_d=s["vent_design_pct"], p_d=s["p_barg"], dt_d=s["dt_surface_c"],
             price=ec["steam_price_usd_t"], hy=ec["hours_per_year"], mawp=c["mawp_barg"], n=c["count"], groups=c["groups"],
             hum_d=h["exhaust_humidity_gkg"], hum_s=h["supply_humidity_gkg"], ratio_d=h["supply_exhaust_ratio"])
    return k


def _parts(twin):
    k = _k(twin)
    TS = lambda g: f"np.interp(df['P{g}_BARG'] + {P0}, {k['tp']}, {k['tt']})"
    HF = f"np.interp(df['P3_BARG'] + {P0}, {k['tp']}, {k['th']})"
    PROD = f"(df['SPEED_MPM'] * 60 * {k['width']} * df['BASIS_WEIGHT_GSM'] / 1000000)"
    FIB = f"({PROD} * 1000 * (1 - df['REEL_MOISTURE_PCT'] / 100))"
    EV = f"({FIB} * ((100 - df['PRESS_DRYNESS_PCT']) / df['PRESS_DRYNESS_PCT'] - df['REEL_MOISTURE_PCT'] / (100 - df['REEL_MOISTURE_PCT'])))"
    SSC = f"(df['STEAM_TOTAL_KGH'] / {EV})"
    mx = lambda xs: xs[0] if len(xs) == 1 else f"np.maximum({xs[0]}, {mx(xs[1:])})"
    mn = lambda xs: xs[0] if len(xs) == 1 else f"np.minimum({xs[0]}, {mn(xs[1:])})"
    DT = mx([f"({TS(g)} - df['TS{g}_C'])" for g in (2, 3, 4)])
    CC = mx([f"(df['TS{g}_C'] - df['TSMIN{g}_C'])" for g in GROUPS])
    DPMIN = mn([f"df['DP{g}_KPA']" for g in GROUPS])
    DPMAX = mx([f"df['DP{g}_KPA']" for g in GROUPS])
    BT = "(df['BT_MAIN_KGH'] / df['COND_MAIN_KGH'] * 100)"
    BTE = f"({k['bt_d']} * np.sqrt(np.maximum((df['DP3_KPA'] + df['DP4_KPA']) / 2, 0) / {k['dp_ref']}))"
    BTR = f"({BT} / {BTE})"
    VP = "(df['VENT_KGH'] / df['STEAM_TOTAL_KGH'] * 100)"
    AB = "(df['HOOD_SUPPLY_KGS'] / df['HOOD_EXHAUST_KGS'])"
    DEN = "(" + " + ".join(f"{a!r} * (df['TS{g}_C'] - {k['tsh']})" for g, a in zip(GROUPS, k["ag"])) + ")"
    KR = f"({EV} / {DEN} / {k['kd_d']!r})"
    ES = f"((df['STEAM_TOTAL_KGH'] - df['VENT_KGH']) * {HF} / {k['q']!r} / 1000)"
    RES = f"(({EV} / 1000 / {ES} - 1) * 100)"
    return dict(k=k, TS=TS, HF=HF, PROD=PROD, FIB=FIB, EV=EV, SSC=SSC, DT=DT, CC=CC, DPMIN=DPMIN, DPMAX=DPMAX, BT=BT, BTE=BTE, BTR=BTR,
                VP=VP, AB=AB, KR=KR, ES=ES, RES=RES)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("PRODUCTION_TH", p["PROD"]),
        ("FIBRE_TH", f"{p['FIB']} / 1000"),
        ("EVAP_TH", f"{p['EV']} / 1000"),
        ("EVAP_RATE_KGM2H", f"{p['EV']} / {k['atot']!r}"),
        ("SPEC_STEAM_KGKG", p["SSC"]),
        ("STEAM_COST_USD_T", f"df['STEAM_TOTAL_KGH'] / 1000 * {k['price']} / {p['PROD']}"),
        ("EXCESS_STEAM_KUSD_Y", f"(df['STEAM_TOTAL_KGH'] - {k['ssc_d']} * {p['EV']}) / 1000 * {k['price']} * {k['hy']} / 1000"),
        ("TSAT_MAIN_C", p["TS"](3)),
        ("DT_SURF_MAX_C", p["DT"]),
        ("COLD_CYL_MAX_K", p["CC"]),
        ("DP_MIN_KPA", p["DPMIN"]),
        ("DP_MAX_KPA", p["DPMAX"]),
        ("BLOWTHROUGH_PCT", p["BT"]),
        ("BT_EXPECTED_PCT", p["BTE"]),
        ("BT_RATIO", p["BTR"]),
        ("VENT_PCT", p["VP"]),
        ("AIR_BALANCE", p["AB"]),
        ("DRY_COEF_RATIO", p["KR"]),
        ("EVAP_STEAMSIDE_TH", p["ES"]),
        ("BALANCE_RESIDUAL_PCT", p["RES"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    prod, fib, ev = evaporation(r["speed_mpm"], k["width"], r["basis_weight_gsm"], r["reel_moisture_pct"], r["press_dryness_pct"])
    ts = {g: tsat(k, r[f"p{g}_barg"]) for g in GROUPS}
    bt = r["bt_main_kgh"] / r["cond_main_kgh"] * 100
    bte = k["bt_d"] * math.sqrt(max((r["dp3_kpa"] + r["dp4_kpa"]) / 2, 0) / k["dp_ref"])
    den = sum(a * (r[f"ts{g}_c"] - k["tsh"]) for g, a in zip(GROUPS, k["ag"]))
    es = (r["steam_total_kgh"] - r["vent_kgh"]) * hfg(k, r["p3_barg"]) / k["q"] / 1000
    return {
        "production_th": prod, "fibre_th": fib / 1000, "evap_th": ev / 1000, "evap_rate_kgm2h": ev / k["atot"],
        "spec_steam_kgkg": r["steam_total_kgh"] / ev,
        "steam_cost_usd_t": r["steam_total_kgh"] / 1000 * k["price"] / prod,
        "excess_steam_kusd_y": (r["steam_total_kgh"] - k["ssc_d"] * ev) / 1000 * k["price"] * k["hy"] / 1000,
        "tsat_main_c": ts[3],
        "dt_surf_max_c": max(ts[g] - r[f"ts{g}_c"] for g in (2, 3, 4)),
        "cold_cyl_max_k": max(r[f"ts{g}_c"] - r[f"tsmin{g}_c"] for g in GROUPS),
        "dp_min_kpa": min(r[f"dp{g}_kpa"] for g in GROUPS), "dp_max_kpa": max(r[f"dp{g}_kpa"] for g in GROUPS),
        "blowthrough_pct": bt, "bt_expected_pct": bte, "bt_ratio": bt / bte,
        "vent_pct": r["vent_kgh"] / r["steam_total_kgh"] * 100,
        "air_balance": r["hood_supply_kgs"] / r["hood_exhaust_kgs"],
        "dry_coef_ratio": ev / den / k["kd_d"],
        "evap_steamside_th": es, "balance_residual_pct": (ev / 1000 / es - 1) * 100,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    return [
        ("DRY_COLD_CYLINDER", f"{p['CC']} > {L['cold_cyl_alert_k']}", "High", "flooded_cylinder"),
        ("DRY_DP_LOW", f"{p['DPMIN']} < {k['dp_lo']}", "High", "low_dp"),
        ("DRY_SURF_DT_HIGH", f"{p['DT']} > {L['dt_surface_alert_c']}", "Medium", "low_dp"),
        ("DRY_DP_HIGH", f"{p['DPMAX']} > {k['dp_hi']}", "Medium", None),
        ("DRY_BLOWTHROUGH_HIGH", f"{p['BTR']} > {L['bt_ratio_high']}", "Medium", "syphon_wear"),
        ("DRY_BLOWTHROUGH_LOW", f"{p['BTR']} < {L['bt_ratio_low']}", "Medium", "low_dp"),
        ("DRY_VENT_HIGH", f"{p['VP']} > {L['vent_alert_pct']}", "Medium", "vent_valve_passing"),
        ("DRY_SSC_HIGH", f"{p['SSC']} > {L['ssc_alert']}", "Medium", "vent_valve_passing"),
        ("DRY_RATE_LOW", f"{p['KR']} < {L['dry_coef_ratio_low']}", "Medium", "fabric_filling"),
        ("DRY_POCKET_HUMID_HIGH", f"df['POCKET_HUMIDITY_GKG'] > {L['pocket_humidity_alert_gkg']}", "Medium", "fabric_filling"),
        ("DRY_HOOD_HUMID_LOW", f"df['HOOD_HUMIDITY_GKG'] < {L['hood_humidity_low_gkg']}", "Medium", "hood_exhaust_high"),
        ("DRY_HOOD_HUMID_HIGH", f"df['HOOD_HUMIDITY_GKG'] > {L['hood_humidity_high_gkg']}", "High", "hood_exhaust_low"),
        ("DRY_AIR_BALANCE", f"({p['AB']} < {L['air_balance_low']}) | ({p['AB']} > {L['air_balance_high']})", "Medium", "hood_exhaust_high"),
        ("DRY_BALANCE_MISMATCH", f"np.abs({p['RES']}) > {L['balance_mismatch_pct']}", "Medium", "steam_meter_drift"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    cold_g = max(GROUPS, key=lambda g: r[f"ts{g}_c"] - r[f"tsmin{g}_c"])
    dt_g = max((2, 3, 4), key=lambda g: tsat(k, r[f"p{g}_barg"]) - r[f"ts{g}_c"])
    dp_g = min(GROUPS, key=lambda g: r[f"dp{g}_kpa"])
    hi_g = max(GROUPS, key=lambda g: r[f"dp{g}_kpa"])
    ab = t["air_balance"]
    add(t["cold_cyl_max_k"] > L["cold_cyl_alert_k"], "DRY_COLD_CYLINDER", "High",
        f"A cylinder in group {cold_g} is {t['cold_cyl_max_k']:.0f} K colder than its group: flooded, check its syphon", "syphon", "flooded_cylinder")
    add(t["dp_min_kpa"] < k["dp_lo"], "DRY_DP_LOW", "High",
        f"Group {dp_g} differential pressure {t['dp_min_kpa']:.0f} kPa, below the {k['dp_lo']:.0f} kPa stationary syphons need", "steam", "low_dp")
    add(t["dt_surf_max_c"] > L["dt_surface_alert_c"], "DRY_SURF_DT_HIGH", "Medium",
        f"Group {dt_g} surface {t['dt_surf_max_c']:.0f} K below its steam temperature: condensate building up", "steam", "low_dp")
    add(t["dp_max_kpa"] > k["dp_hi"], "DRY_DP_HIGH", "Medium",
        f"Group {hi_g} differential pressure {t['dp_max_kpa']:.0f} kPa: more blow-through than needed", "steam")
    add(t["bt_ratio"] > L["bt_ratio_high"], "DRY_BLOWTHROUGH_HIGH", "Medium",
        f"Blow-through {t['blowthrough_pct']:.0f} % of the condensing load, {t['bt_ratio']:.1f} x what the DP explains: worn syphons", "syphon", "syphon_wear")
    add(t["bt_ratio"] < L["bt_ratio_low"], "DRY_BLOWTHROUGH_LOW", "Medium",
        f"Blow-through only {t['blowthrough_pct']:.1f} % ({t['bt_ratio']:.2f} x expected): syphons not passing steam", "steam", "low_dp")
    add(t["vent_pct"] > L["vent_alert_pct"], "DRY_VENT_HIGH", "Medium", f"{t['vent_pct']:.1f} % of the steam vented to the condenser", "steam", "vent_valve_passing")
    add(t["spec_steam_kgkg"] > L["ssc_alert"], "DRY_SSC_HIGH", "Medium",
        f"{t['spec_steam_kgkg']:.2f} kg steam per kg water: {t['excess_steam_kusd_y']:.0f} k$ a year above design", "steam", "vent_valve_passing")
    add(t["dry_coef_ratio"] < L["dry_coef_ratio_low"], "DRY_RATE_LOW", "Medium",
        f"Evaporation per degree of hot surface {t['dry_coef_ratio']:.2f} x design: fabric or pockets holding the vapour", "fabric", "fabric_filling")
    add(r["pocket_humidity_gkg"] > L["pocket_humidity_alert_gkg"], "DRY_POCKET_HUMID_HIGH", "Medium",
        f"Pocket humidity {r['pocket_humidity_gkg']:.0f} g/kg: vapour not leaving the pockets", "fabric", "fabric_filling")
    add(r["hood_humidity_gkg"] < L["hood_humidity_low_gkg"], "DRY_HOOD_HUMID_LOW", "Medium",
        f"Hood exhaust humidity {r['hood_humidity_gkg']:.0f} g/kg: heating more air than the water needs", "hood", "hood_exhaust_high")
    add(r["hood_humidity_gkg"] > L["hood_humidity_high_gkg"], "DRY_HOOD_HUMID_HIGH", "High",
        f"Hood exhaust humidity {r['hood_humidity_gkg']:.0f} g/kg: condensation and drips in the hood", "hood", "hood_exhaust_low")
    add(ab < L["air_balance_low"] or ab > L["air_balance_high"], "DRY_AIR_BALANCE", "Medium",
        f"Supply/exhaust air {ab:.2f}, outside {L['air_balance_low']} to {L['air_balance_high']}", "hood", "hood_exhaust_high")
    add(abs(t["balance_residual_pct"]) > L["balance_mismatch_pct"], "DRY_BALANCE_MISMATCH", "Medium",
        f"Sheet-side evaporation {t['evap_th']:.1f} t/h vs steam-side {t['evap_steamside_th']:.1f} t/h: check the steam meter and the QCS", "instrument", "steam_meter_drift")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
