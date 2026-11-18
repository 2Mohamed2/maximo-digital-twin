"""The belt filter press twin's expectations (BP-5001, ANDRITZ SMX-Q 2000 S12 on digested sludge).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Loading (feed flow Qf m3/h, feed solids Sf % DS, belt width W m):
    dry solids in      DS = Qf x Sf x 10                kg/h   (1 % DS = 10 kg/m3)
    hydraulic loading  = Qf / W m3/(m h),  ratio to the maker's capacity  Qf / 45
    solids loading     = DS / W kg/(m h),  ratio to the maker's capacity  DS / 900
Polymer (solution flow Qp L/h at c % active):
    active polymer     P = Qp x c / 100                 kg/h
    specific dose      d = P / (DS / 1000)              kg per tonne of dry solids (= g/kg)
Expected cake dry solids at the live dose, tension and loading (dose-response curve, fitted on a dose trial):
    DSexp = DSmax (1 - exp(-d / d0)) - k_over max(0, d - d_opt) + k_t (min tension - set) - k_load max(0, DS/900 - 1)
    cake residual = measured cake DS - DSexp            (% points; below -2 the cake is wetter than it should be)
Solids capture, mass balance on feed and filtrate (the filtrate meter sees filtrate + wash water):
    filtrate solids    = Qe x TSS / 1000                kg/h
    capture            = 100 (1 - Qe TSS / 1000 / DS)   %
    cake               = DS x capture / 100 / (Sc / 100) / 1000          t/h of wet cake
Water balance: Qe expected = Qf + Qp / 1000 + Qwash - cake / rho_cake; residual = measured - expected (meter check).
Wash nozzles (orifice law): Q = Q0 sqrt(P / P0); open-nozzle ratio = Qwash / (13.6 sqrt(P / 8)).
Belts: lower of the two tension pressures, larger of the two edge offsets, running hours / belt life.
Each expression works on one reading (Monitor keeps no state for the twin); the belt hours come from the PLC counter.
"""
import math


def _g(x):
    """A constant as written into the Monitor expression (8 significant digits), so Python and pandas use the same number."""
    return float(f"{x:.8g}")


def _k(twin):
    d = twin["design"]
    p, po, dr, b, w, c, o = d["press"], d["polymer"], d["dose_response"], d["belts"], d["wash"], d["capture"], d["operation"]
    return dict(W=p["belt_width_m"], qcap=p["feed_capacity_m3h"], scap=p["solids_capacity_kgh"], qw0=p["wash_flow_m3h"],
                pw0=p["wash_pressure_bar"], conc=po["solution_pct"], dmax=dr["ds_max_pct"], d0=dr["d0_kg_t"], dopt=dr["d_opt_kg_t"],
                kover=dr["overdose_pct_per_kg_t"], kt=dr["tension_pct_per_bar"], kl=dr["overload_pct"], tset=b["tension_set_bar"],
                life=b["life_h"], rho=o["cake_density_t_m3"])


def cake_expected(k, dose, tension_min, solids_ratio):
    """The dose-response curve (pure Python; physics.py and the figures use it too)."""
    return (k["dmax"] * (1 - math.exp(-dose / k["d0"])) - k["kover"] * max(0.0, dose - k["dopt"])
            + k["kt"] * (tension_min - k["tset"]) - k["kl"] * max(0.0, solids_ratio - 1))


def _parts(twin):
    k = _k(twin)
    DS = "(df['FEED_FLOW_M3H'] * df['FEED_DS_PCT'] * 10)"
    POLY = f"(df['POLYMER_SOLUTION_LPH'] * {k['conc'] / 100:.8g})"
    DOSE = f"({POLY} / np.maximum({DS} / 1000, 0.001))"
    SR = f"({DS} / {k['scap']})"
    TMIN = "np.minimum(df['TENSION_UPPER_BAR'], df['TENSION_LOWER_BAR'])"
    CE = (f"({k['dmax']} * (1 - np.exp(-{DOSE} / {k['d0']})) - {k['kover']} * np.maximum({DOSE} - {k['dopt']}, 0)"
          f" + {k['kt']} * ({TMIN} - {k['tset']}) - {k['kl']} * np.maximum({SR} - 1, 0))")
    FS = "(df['FILTRATE_FLOW_M3H'] * df['FILTRATE_TSS_MGL'] / 1000)"
    CAP = f"(100 * (1 - {FS} / np.maximum({DS}, 0.001)))"
    CAKE = f"({DS} * {CAP} / 100 / np.maximum(df['CAKE_DS_PCT'] / 100, 0.01) / 1000)"
    QE = f"(df['FEED_FLOW_M3H'] + df['POLYMER_SOLUTION_LPH'] / 1000 + df['WASH_FLOW_M3H'] - {CAKE} / {k['rho']})"
    NOZ = f"(df['WASH_FLOW_M3H'] / ({k['qw0']} * np.sqrt(np.maximum(df['WASH_PRESSURE_BAR'], 0.01) / {k['pw0']})))"
    TRK = "np.maximum(np.abs(df['TRACKING_UPPER_MM']), np.abs(df['TRACKING_LOWER_MM']))"
    return dict(k=k, DS=DS, POLY=POLY, DOSE=DOSE, SR=SR, TMIN=TMIN, CE=CE, FS=FS, CAP=CAP, CAKE=CAKE, QE=QE, NOZ=NOZ, TRK=TRK)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("FEED_DS_KGH", p["DS"]),
        ("HYDRAULIC_LOAD_M3MH", f"df['FEED_FLOW_M3H'] / {k['W']}"),
        ("SOLIDS_LOAD_KGMH", f"{p['DS']} / {k['W']}"),
        ("HYDRAULIC_RATIO", f"df['FEED_FLOW_M3H'] / {k['qcap']}"),
        ("SOLIDS_RATIO", p["SR"]),
        ("POLYMER_ACTIVE_KGH", p["POLY"]),
        ("POLYMER_KG_PER_TDS", p["DOSE"]),
        ("CAKE_DS_EXPECTED_PCT", p["CE"]),
        ("CAKE_DS_RESIDUAL_PCT", f"df['CAKE_DS_PCT'] - {p['CE']}"),
        ("FILTRATE_SOLIDS_KGH", p["FS"]),
        ("CAPTURE_PCT", p["CAP"]),
        ("CAKE_TPH", p["CAKE"]),
        ("FILTRATE_EXPECTED_M3H", p["QE"]),
        ("WATER_BALANCE_M3H", f"df['FILTRATE_FLOW_M3H'] - {p['QE']}"),
        ("NOZZLE_OPEN_RATIO", p["NOZ"]),
        ("WASH_M3_PER_TDS", f"df['WASH_FLOW_M3H'] / np.maximum({p['DS']} / 1000, 0.001)"),
        ("TENSION_MIN_BAR", p["TMIN"]),
        ("TRACKING_MAX_MM", p["TRK"]),
        ("BELT_LIFE_USED_PCT", f"df['BELT_HOURS'] / {k['life']} * 100"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    ds = r["feed_flow_m3h"] * r["feed_ds_pct"] * 10
    poly = r["polymer_solution_lph"] * _g(k["conc"] / 100)
    dose = poly / max(ds / 1000, 0.001)
    sr = ds / k["scap"]
    tmin = min(r["tension_upper_bar"], r["tension_lower_bar"])
    ce = (k["dmax"] * (1 - math.exp(-dose / k["d0"])) - k["kover"] * max(dose - k["dopt"], 0)
          + k["kt"] * (tmin - k["tset"]) - k["kl"] * max(sr - 1, 0))
    fs = r["filtrate_flow_m3h"] * r["filtrate_tss_mgl"] / 1000
    cap = 100 * (1 - fs / max(ds, 0.001))
    cake = ds * cap / 100 / max(r["cake_ds_pct"] / 100, 0.01) / 1000
    qe = r["feed_flow_m3h"] + r["polymer_solution_lph"] / 1000 + r["wash_flow_m3h"] - cake / k["rho"]
    return {
        "feed_ds_kgh": ds, "hydraulic_load_m3mh": r["feed_flow_m3h"] / k["W"], "solids_load_kgmh": ds / k["W"],
        "hydraulic_ratio": r["feed_flow_m3h"] / k["qcap"], "solids_ratio": sr, "polymer_active_kgh": poly,
        "polymer_kg_per_tds": dose, "cake_ds_expected_pct": ce, "cake_ds_residual_pct": r["cake_ds_pct"] - ce,
        "filtrate_solids_kgh": fs, "capture_pct": cap, "cake_tph": cake, "filtrate_expected_m3h": qe,
        "water_balance_m3h": r["filtrate_flow_m3h"] - qe,
        "nozzle_open_ratio": r["wash_flow_m3h"] / (k["qw0"] * math.sqrt(max(r["wash_pressure_bar"], 0.01) / k["pw0"])),
        "wash_m3_per_tds": r["wash_flow_m3h"] / max(ds / 1000, 0.001),
        "tension_min_bar": tmin, "tracking_max_mm": max(abs(r["tracking_upper_mm"]), abs(r["tracking_lower_mm"])),
        "belt_life_used_pct": r["belt_hours"] / k["life"] * 100,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    RUN = "(df['RUNNING'] > 0.5)"
    TRK = p["TRK"]
    return [
        ("BP_TRACKING_LIMIT", f"{TRK} > {L['tracking_limit_mm']}", "Critical", "belt_mistracking"),
        ("BP_CAPTURE_LOW", f"{RUN} & ({p['CAP']} < {L['capture_min_pct']})", "High", "polymer_weak"),
        ("BP_CAKE_DRY_LOW", f"{RUN} & ((df['CAKE_DS_PCT'] - {p['CE']}) < {L['cake_residual_alert_pct']})", "High", "polymer_weak"),
        ("BP_HYDRAULIC_HIGH", f"{RUN} & ((df['FEED_FLOW_M3H'] / {k['qcap']}) > {L['hydraulic_ratio_max']})", "High", "feed_overload"),
        ("BP_WASH_PRESSURE_LOW", f"{RUN} & (df['WASH_PRESSURE_BAR'] < {L['wash_pressure_min_bar']})", "High", "wash_pressure_low"),
        ("BP_SOLIDS_LOAD_HIGH", f"{RUN} & ({p['SR']} > {L['solids_ratio_max']})", "Medium", "feed_overload"),
        ("BP_POLYMER_HIGH", f"{RUN} & ({p['DOSE']} > {L['dose_max_kg_t']})", "Medium", "polymer_overdose"),
        ("BP_WASH_NOZZLES_BLOCKED", f"{RUN} & (df['WASH_PRESSURE_BAR'] >= {L['wash_pressure_min_bar']}) & ({p['NOZ']} < {L['nozzle_ratio_min']})", "Medium", "wash_nozzle_blinding"),
        ("BP_TRACKING_OFF", f"({TRK} > {L['tracking_alert_mm']}) & ({TRK} <= {L['tracking_limit_mm']})", "Medium", "belt_mistracking"),
        ("BP_TENSION_LOW", f"{RUN} & ({p['TMIN']} < {L['tension_min_bar']})", "Medium", "tension_low"),
        ("BP_BELT_HOURS_HIGH", f"df['BELT_HOURS'] > {L['belt_life_h']}", "Medium", "belt_wear"),
        ("BP_FEED_SOLIDS_LOW", f"{RUN} & (df['FEED_DS_PCT'] < {L['feed_ds_min_pct']})", "Low", None),
        ("BP_WATER_BALANCE", f"{RUN} & (np.abs(df['FILTRATE_FLOW_M3H'] - {p['QE']}) > {L['water_balance_alert_m3h']})", "Low", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    run = r["running"] > 0.5
    trk = t["tracking_max_mm"]
    add(trk > L["tracking_limit_mm"], "BP_TRACKING_LIMIT", "Critical",
        f"Belt edge {trk:.0f} mm off centre, past the {L['tracking_limit_mm']:.0f} mm limit: the belt can run off and tear", "belts", "belt_mistracking")
    add(run and t["capture_pct"] < L["capture_min_pct"], "BP_CAPTURE_LOW", "High",
        f"Solids capture {t['capture_pct']:.1f} %: {t['filtrate_solids_kgh']:.0f} kg/h of solids return with the filtrate", "filtrate", "polymer_weak")
    add(run and t["cake_ds_residual_pct"] < L["cake_residual_alert_pct"], "BP_CAKE_DRY_LOW", "High",
        f"Cake {r['cake_ds_pct']:.1f} % DS, {t['cake_ds_residual_pct']:+.1f} points against {t['cake_ds_expected_pct']:.1f} % expected at {t['polymer_kg_per_tds']:.1f} kg/t", "cake", "polymer_weak")
    add(run and t["hydraulic_ratio"] > L["hydraulic_ratio_max"], "BP_HYDRAULIC_HIGH", "High",
        f"Feed {r['feed_flow_m3h']:.0f} m³/h, {t['hydraulic_ratio'] * 100:.0f} % of the {k['qcap']:.0f} m³/h capacity", "feed", "feed_overload")
    add(run and r["wash_pressure_bar"] < L["wash_pressure_min_bar"], "BP_WASH_PRESSURE_LOW", "High",
        f"Wash water {r['wash_pressure_bar']:.1f} bar, below {L['wash_pressure_min_bar']:.0f} bar: the belts are not cleaned", "wash", "wash_pressure_low")
    add(run and t["solids_ratio"] > L["solids_ratio_max"], "BP_SOLIDS_LOAD_HIGH", "Medium",
        f"Solids {t['feed_ds_kgh']:.0f} kg DS/h, {t['solids_ratio'] * 100:.0f} % of the {k['scap']:.0f} kg/h capacity", "feed", "feed_overload")
    add(run and t["polymer_kg_per_tds"] > L["dose_max_kg_t"], "BP_POLYMER_HIGH", "Medium",
        f"Polymer {t['polymer_kg_per_tds']:.1f} kg/t DS, above {L['dose_max_kg_t']:.0f} kg/t ({t['polymer_active_kgh']:.1f} kg/h active)", "polymer", "polymer_overdose")
    add(run and r["wash_pressure_bar"] >= L["wash_pressure_min_bar"] and t["nozzle_open_ratio"] < L["nozzle_ratio_min"], "BP_WASH_NOZZLES_BLOCKED", "Medium",
        f"Wash flow {r['wash_flow_m3h']:.1f} m³/h at {r['wash_pressure_bar']:.1f} bar: only {t['nozzle_open_ratio'] * 100:.0f} % of the nozzles' flow", "wash", "wash_nozzle_blinding")
    add(L["tracking_alert_mm"] < trk <= L["tracking_limit_mm"], "BP_TRACKING_OFF", "Medium",
        f"Belt edge {trk:.0f} mm off centre (alert {L['tracking_alert_mm']:.0f} mm)", "belts", "belt_mistracking")
    add(run and t["tension_min_bar"] < L["tension_min_bar"], "BP_TENSION_LOW", "Medium",
        f"Belt tension {r['tension_upper_bar']:.1f} / {r['tension_lower_bar']:.1f} bar (upper / lower), below {L['tension_min_bar']:.0f} bar", "belts", "tension_low")
    add(r["belt_hours"] > L["belt_life_h"], "BP_BELT_HOURS_HIGH", "Medium",
        f"Belts at {r['belt_hours']:.0f} running hours, {t['belt_life_used_pct']:.0f} % of the {L['belt_life_h']:.0f} h life", "belts", "belt_wear")
    add(run and r["feed_ds_pct"] < L["feed_ds_min_pct"], "BP_FEED_SOLIDS_LOW", "Low", f"Feed only {r['feed_ds_pct']:.1f} % DS", "feed")
    add(run and abs(t["water_balance_m3h"]) > L["water_balance_alert_m3h"], "BP_WATER_BALANCE", "Low",
        f"Filtrate flow {t['water_balance_m3h']:+.1f} m³/h off the water balance: check the flow meters", "filtrate")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
