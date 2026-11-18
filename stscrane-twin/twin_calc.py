"""The ship-to-shore container crane twin's expectations (QC-5801, Liebherr STS, Super Post Panamax size).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Hoist (constant-power drive between the rated-load speed and the empty-spreader speed, from the maker's data sheet):
    hoisted mass M (t)        = payload + spreader and headblock (PA)
    rated power at the rope   = (SWL + PA) x 9.81 x v_rated / 60                       (kW, v in m/min)
    expected top speed        = min(v_empty, rated power x 60 / (M x 9.81))            (the maker's speed-load curve)
    expected drive power      = M x 9.81 x v / 60 / efficiency                         (at the measured steady speed v)
    power ratio               = measured / expected        (a dragging brake or a stiff gearbox costs power)
Design working period (ISO 12482:2014, counters kept by the crane management system, f1 = 1.0 for automatic recording):
    work cycles (Annex A.2)       f1 x Ca                                   against DN (U7: 2 000 000)
    cumulative loading (A.3/A.4)  f1 x sum((Pi / P)^3)                      against Kp x DN = DC (A7: 500 000)
    hoist mechanism (Annex B)     f1 x sum(ti x ((Pi + PA)/(P + PA))^3 + tR,i x (PA/(P + PA))^3)   against DM (M8: 12 500 h)
    years left at the current rate = (limit - used) / (use of the last 30 days x 365 / 30)
    spectrum factor as operated    km = weighted hoist hours / hoist hours
Hoist ropes (ISO 4309:2017, 6.4.2): uniform decrease (%) = (d_ref - d_measured) / d_nominal x 100; rope life in moves.
Trolley wheels: wear rate = (d_new - d) / km travelled x 1000, against the expected rate.
Wind: gust at the top of the crane / in-service limit (20 m/s on the data sheet).
"""

G = 9.81


def _k(twin):
    d = twin["design"]
    ra, h, tr, ga, c, ro, br, sp, op = (d["rated"], d["hoist"], d["trolley"], d["gantry"], d["classification"], d["rope"],
                                        d["brake"], d["spreader"], d["operation"])
    swl, pa = ra["swl_twin_t"], ra["attachment_t"]
    return dict(swl=swl, pa=pa, vr=h["speed_rated_mpm"], ve=h["speed_empty_mpm"], eta=h["efficiency"],
                prated=(swl + pa) * G * h["speed_rated_mpm"] / 60,
                wnew=tr["wheel_new_mm"], wmin=tr["wheel_min_mm"], wexp=tr["wear_mm_per_1000km"],
                wind=ga["wind_in_service_ms"], dn=c["dn_cycles"], dc=c["dc_cycles"], dm=c["dm_hours"], f1=c["f1"], kp=c["kp"],
                rnom=ro["nominal_mm"], rref=ro["ref_mm"], rsl=ro["dia_slight_pct"], rdis=ro["dia_discard_pct"], rlife=ro["life_moves"],
                brel=br["release_alert_ms"], bmin=br["pad_min_mm"], twl=sp["faults_per_1000_alert"], mph=op["moves_per_hour"])


def speed_exp(k, payload_t):
    """The maker's speed-load curve: constant power between rated load and the empty spreader."""
    return min(k["ve"], k["prated"] * 60 / ((payload_t + k["pa"]) * G))


def power_exp(k, payload_t, v_mpm):
    return (payload_t + k["pa"]) * G * v_mpm / 60 / k["eta"]


def _parts(twin):
    k = _k(twin)
    f1 = k["f1"]
    M = f"(df['LAST_LOAD_T'] + {k['pa']})"
    SE = f"np.minimum({k['ve']}, {k['prated'] * 60 / G!r} / {M})"
    PE = f"({M} * {G / 60 / k['eta']!r} * df['LAST_LIFT_SPEED_MPM'])"
    PR = f"(df['LAST_LIFT_POWER_KW'] / {PE})"
    YR = 365 / 30
    CY = f"(({k['dn']} - {f1} * df['MOVES_TOTAL']) / np.maximum({f1 * YR!r} * df['MOVES_30D'], 1e-6))"
    SY = f"(({k['dc']} - {f1} * df['STRUCT_EQUIV']) / np.maximum({f1 * YR!r} * df['STRUCT_EQUIV_30D'], 1e-6))"
    HY = f"(({k['dm']} - {f1} * df['HOIST_EQUIV_H']) / np.maximum({f1 * YR!r} * df['HOIST_EQUIV_30D_H'], 1e-6))"
    FIRST = f"np.minimum(np.minimum({CY}, {SY}), {HY})"
    RD = f"(({k['rref']} - df['ROPE_DIA_MM']) / {k['rnom']} * 100)"
    TWL = "(df['TWL_FAULTS_24H'] / np.maximum(df['TWL_CYCLES_24H'], 1) * 1000)"
    TW = f"(({k['wnew']} - df['TROLLEY_WHEEL_MM']) / np.maximum(df['TROLLEY_KM_SINCE_CHANGE'], 1) * 1000 / {k['wexp']})"
    WR = f"(df['WIND_MS'] / {k['wind']})"
    return dict(k=k, M=M, SE=SE, PE=PE, PR=PR, CY=CY, SY=SY, HY=HY, FIRST=FIRST, RD=RD, TWL=TWL, TW=TW, WR=WR)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    f1 = k["f1"]
    return [
        ("LOAD_PCT", f"df['LAST_LOAD_T'] / {k['swl']} * 100"),
        ("HOIST_SPEED_EXP_MPM", p["SE"]),
        ("HOIST_POWER_EXP_KW", p["PE"]),
        ("HOIST_POWER_RATIO", p["PR"]),
        ("MOVES_RATIO", f"df['MOVES_PER_HOUR'] / {k['mph']}"),
        ("CYCLES_USED_PCT", f"{f1} * df['MOVES_TOTAL'] / {k['dn']} * 100"),
        ("CYCLES_LEFT_Y", p["CY"]),
        ("STRUCT_USED_PCT", f"{f1} * df['STRUCT_EQUIV'] / {k['dc']} * 100"),
        ("STRUCT_LEFT_Y", p["SY"]),
        ("HOIST_DWP_USED_PCT", f"{f1} * df['HOIST_EQUIV_H'] / {k['dm']} * 100"),
        ("HOIST_DWP_LEFT_Y", p["HY"]),
        ("KM_LIFETIME", "df['HOIST_EQUIV_H'] / np.maximum(df['HOIST_HOURS'], 1e-6)"),
        ("KM_30D", "df['HOIST_EQUIV_30D_H'] / np.maximum(df['HOIST_HOURS_30D'], 1e-6)"),
        ("DWP_FIRST_LIMIT_Y", p["FIRST"]),
        ("ROPE_DIA_DECREASE_PCT", p["RD"]),
        ("ROPE_LIFE_USED_PCT", f"df['ROPE_MOVES_SINCE_CHANGE'] / {k['rlife']} * 100"),
        ("TWL_FAULTS_PER_1000", p["TWL"]),
        ("TROLLEY_WEAR_RATIO", p["TW"]),
        ("TROLLEY_WHEEL_LEFT_MM", f"df['TROLLEY_WHEEL_MM'] - {k['wmin']}"),
        ("WIND_RATIO", p["WR"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    f1, yr = k["f1"], 365 / 30
    se = min(k["ve"], k["prated"] * 60 / G / (r["last_load_t"] + k["pa"]))
    pe = (r["last_load_t"] + k["pa"]) * (G / 60 / k["eta"]) * r["last_lift_speed_mpm"]
    cy = (k["dn"] - f1 * r["moves_total"]) / max(f1 * yr * r["moves_30d"], 1e-6)
    sy = (k["dc"] - f1 * r["struct_equiv"]) / max(f1 * yr * r["struct_equiv_30d"], 1e-6)
    hy = (k["dm"] - f1 * r["hoist_equiv_h"]) / max(f1 * yr * r["hoist_equiv_30d_h"], 1e-6)
    return {
        "load_pct": r["last_load_t"] / k["swl"] * 100,
        "hoist_speed_exp_mpm": se, "hoist_power_exp_kw": pe, "hoist_power_ratio": r["last_lift_power_kw"] / pe,
        "moves_ratio": r["moves_per_hour"] / k["mph"],
        "cycles_used_pct": f1 * r["moves_total"] / k["dn"] * 100, "cycles_left_y": cy,
        "struct_used_pct": f1 * r["struct_equiv"] / k["dc"] * 100, "struct_left_y": sy,
        "hoist_dwp_used_pct": f1 * r["hoist_equiv_h"] / k["dm"] * 100, "hoist_dwp_left_y": hy,
        "km_lifetime": r["hoist_equiv_h"] / max(r["hoist_hours"], 1e-6), "km_30d": r["hoist_equiv_30d_h"] / max(r["hoist_hours_30d"], 1e-6),
        "dwp_first_limit_y": min(min(cy, sy), hy),
        "rope_dia_decrease_pct": (k["rref"] - r["rope_dia_mm"]) / k["rnom"] * 100,
        "rope_life_used_pct": r["rope_moves_since_change"] / k["rlife"] * 100,
        "twl_faults_per_1000": r["twl_faults_24h"] / max(r["twl_cycles_24h"], 1) * 1000,
        "trolley_wear_ratio": (k["wnew"] - r["trolley_wheel_mm"]) / max(r["trolley_km_since_change"], 1) * 1000 / k["wexp"],
        "trolley_wheel_left_mm": r["trolley_wheel_mm"] - k["wmin"],
        "wind_ratio": r["wind_ms"] / k["wind"],
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    ACT = "(df['CRANE_ACTIVE'] > 0.5)"
    return [
        ("STS_WIND_LIMIT", f"{ACT} & ({p['WR']} >= 1)", "Critical", "wind_operation"),
        ("STS_ROPE_DISCARD", f"{p['RD']} >= {k['rdis']}", "Critical", "rope_wear"),
        ("STS_HOIST_POWER_HIGH", f"{p['PR']} > {L['hoist_power_ratio_alert']}", "High", "brake_drag"),
        ("STS_BRAKE_PAD_LOW", f"df['BRAKE_PAD_MM'] < {k['bmin']}", "High", "brake_pad_wear"),
        ("STS_SNAG", "df['SNAG_EVENTS_24H'] >= 1", "High", "snag_overload"),
        ("STS_OVERLOAD", f"df['PEAK_LOAD_24H_T'] > {k['swl']}", "High", "snag_overload"),
        ("STS_TROLLEY_WHEEL_MIN", f"(df['TROLLEY_WHEEL_MM'] - {k['wmin']}) < {L['trolley_wheel_left_alert_mm']}", "High", "trolley_wheel_wear"),
        ("STS_DWP_SA_DUE", f"{p['FIRST']} < {L['dwp_years_alert']}", "High", None),
        ("STS_WIND_HIGH", f"{ACT} & ({p['WR']} >= {L['wind_warn_ratio']}) & ({p['WR']} < 1)", "Medium", "wind_operation"),
        ("STS_ROPE_DIAMETER", f"({p['RD']} >= {k['rsl']}) & ({p['RD']} < {k['rdis']})", "Medium", "rope_wear"),
        ("STS_ROPE_LIFE", f"df['ROPE_MOVES_SINCE_CHANGE'] > {k['rlife']}", "Medium", "rope_wear"),
        ("STS_BRAKE_SLOW", f"df['BRAKE_RELEASE_MS'] > {k['brel']}", "Medium", "brake_drag"),
        ("STS_TWISTLOCK_FAULTS", f"{p['TWL']} > {k['twl']}", "Medium", "twistlock_faults"),
        ("STS_TROLLEY_WEAR_RATE", f"{p['TW']} > {L['trolley_wear_ratio_alert']}", "Medium", "trolley_wheel_wear"),
        ("STS_MOVES_LOW", f"{ACT} & ((df['MOVES_PER_HOUR'] / {k['mph']}) < {L['moves_ratio_alert']})", "Low", "twistlock_faults"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    act = r["crane_active"] > 0.5
    wr, rd = t["wind_ratio"], t["rope_dia_decrease_pct"]
    add(act and wr >= 1, "STS_WIND_LIMIT", "Critical",
        f"Wind {r['wind_ms']:.1f} m/s at the top of the crane while working: above the {k['wind']:.0f} m/s in-service limit", "structure", "wind_operation")
    add(rd >= k["rdis"], "STS_ROPE_DISCARD", "Critical",
        f"Hoist rope {r['rope_dia_mm']:.2f} mm: {rd:.1f} % below its reference, discard at {k['rdis']} % (ISO 4309)", "hoist ropes", "rope_wear")
    add(t["hoist_power_ratio"] > L["hoist_power_ratio_alert"], "STS_HOIST_POWER_HIGH", "High",
        f"Hoist drew {r['last_lift_power_kw']:.0f} kW for {r['last_load_t']:.1f} t at {r['last_lift_speed_mpm']:.0f} m/min: {t['hoist_power_ratio']:.2f} × expected", "hoist", "brake_drag")
    add(r["brake_pad_mm"] < k["bmin"], "STS_BRAKE_PAD_LOW", "High", f"Hoist brake pad {r['brake_pad_mm']:.1f} mm, minimum {k['bmin']:.1f} mm", "hoist brake", "brake_pad_wear")
    add(r["snag_events_24h"] >= 1, "STS_SNAG", "High", f"{r['snag_events_24h']:.0f} snag events in 24 h: inspect the ropes, sheaves and headblock", "spreader", "snag_overload")
    add(r["peak_load_24h_t"] > k["swl"], "STS_OVERLOAD", "High",
        f"Load-cell peak {r['peak_load_24h_t']:.0f} t, {r['peak_load_24h_t'] / k['swl'] * 100:.0f} % of the {k['swl']:.0f} t safe working load", "hoist", "snag_overload")
    add(t["trolley_wheel_left_mm"] < L["trolley_wheel_left_alert_mm"], "STS_TROLLEY_WHEEL_MIN", "High",
        f"Trolley wheel {r['trolley_wheel_mm']:.1f} mm, {t['trolley_wheel_left_mm']:.1f} mm above the discard diameter", "trolley", "trolley_wheel_wear")
    add(t["dwp_first_limit_y"] < L["dwp_years_alert"], "STS_DWP_SA_DUE", "High",
        f"A design limit is reached in {t['dwp_first_limit_y']:.1f} years: special assessment due before the next annual inspection (ISO 12482)", "crane")
    add(act and L["wind_warn_ratio"] <= wr < 1, "STS_WIND_HIGH", "Medium", f"Wind {r['wind_ms']:.1f} m/s, {wr * 100:.0f} % of the in-service limit", "structure", "wind_operation")
    add(k["rsl"] <= rd < k["rdis"], "STS_ROPE_DIAMETER", "Medium", f"Hoist rope {rd:.1f} % below its reference diameter", "hoist ropes", "rope_wear")
    add(r["rope_moves_since_change"] > k["rlife"], "STS_ROPE_LIFE", "Medium",
        f"Ropes have made {r['rope_moves_since_change']:.0f} moves, {t['rope_life_used_pct']:.0f} % of their expected life", "hoist ropes", "rope_wear")
    add(r["brake_release_ms"] > k["brel"], "STS_BRAKE_SLOW", "Medium", f"Hoist brake released in {r['brake_release_ms']:.0f} ms (alert above {k['brel']:.0f})", "hoist brake", "brake_drag")
    add(t["twl_faults_per_1000"] > k["twl"], "STS_TWISTLOCK_FAULTS", "Medium",
        f"{r['twl_faults_24h']:.0f} twistlock faults in {r['twl_cycles_24h']:.0f} cycles: {t['twl_faults_per_1000']:.1f} per 1000", "spreader", "twistlock_faults")
    add(t["trolley_wear_ratio"] > L["trolley_wear_ratio_alert"], "STS_TROLLEY_WEAR_RATE", "Medium",
        f"Trolley wheels wear {t['trolley_wear_ratio']:.1f} × faster than expected", "trolley", "trolley_wheel_wear")
    add(act and t["moves_ratio"] < L["moves_ratio_alert"], "STS_MOVES_LOW", "Low",
        f"{r['moves_per_hour']:.0f} moves per hour against {k['mph']:.0f} expected", "operation", "twistlock_faults")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
