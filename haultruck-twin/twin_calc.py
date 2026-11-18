"""The mining haul truck twin's expectations (HT-4001, Cat 793F with 50/80 R57 tyres).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Power the truck needs (rimpull x speed), from what the payload monitor, the speedometer and the inclinometer say:
    GVW (t)              = empty weight + payload
    total resistance (%) = grade + rolling resistance          (spec sheet: 1 % per 10 kg/t of rolling resistance)
    wheel power (kW)     = GVW x 9.81 x v (m/s) x total resistance / 100      (0 when the road falls: the brakes retard)
    engine power (kW)    = wheel power / drivetrain efficiency + accessories, at most the rated 1976 kW; idle power at standstill
    expected fuel (L/h)  = zero-load fuel + marginal BSFC x engine power / (1000 x density)          (Willans line)
The engine's own sensors are compared with what that power should produce:
    boost        = b0 + (b_full - b0) x load        exhaust (mean of the banks) = e0 + (e_full - e0) x load
    coolant      = max(regulated temperature, ambient + full-load rise x load)     crankcase = c0 + (c_full - c0) x load
  with load = expected engine power / rated power. Combustion rules only judge readings above half load.
Tyres (Michelin TKPH method):
    cold-equivalent pressure = (P_hot + 101.325) x (T_ambient + 273.15) / (T_tyre + 273.15) - 101.325
    Qm = (Qc + Qv) / 2 per tyre (laden and unladen tyre load, t), the larger of front and rear;  Vm = L / H of the reference cycle
    site TKPH = Qm x Vm x K1(L) x K2,  K2 = 1 / (1 - a x (TA - 38) / Vm),  a = 0.40 above 38 C, 0.25 below
Payload (Cat 10/10/20): mean <= target, at most 10 % of loads above 110 %, none above 120 %.
Oil: iron normalised to 250 h on the oil; hydraulic cleanliness = worst ISO 4406 code above its target.
Engine life: fuel burned / the life target in litres (Cat states the C175-16 life in fuel burned, not hours).
"""

P_ATM = 101.325


def _k(twin):
    d = twin["design"]
    e, f, dt, tr, hr, ty, em, oil = (d["engine"], d["fuel"], d["drivetrain"], d["truck"], d["haul_road"], d["tyres"],
                                     d["engine_model"], d["oil"])
    return dict(rated=e["rated_gross_kw"], idle=e["idle_kw"], acc=dt["accessory_kw"], eta=dt["efficiency"],
                f0=f["zero_load_lph"], bsfc=f["bsfc_marginal_g_kwh"], rho=f["density_kg_l"], life=f["life_target_l"],
                ew=tr["empty_kg"] / 1000, tgt=tr["target_payload_t"], fe=tr["front_empty"], re=tr["rear_empty"],
                fl=tr["front_loaded"], rl=tr["rear_loaded"], rr=hr["rolling_resistance_pct"],
                treg=em["coolant_regulated_c"], rise=em["coolant_rise_full_k"], b0=em["boost_zero_kpa"], bf=em["boost_full_kpa"],
                e0=em["exhaust_zero_c"], ef=em["exhaust_full_c"], c0=em["crankcase_zero_kpa"], cf=em["crankcase_full_kpa"],
                tkph=ty["tkph_rating"], pset=ty["cold_set_kpa"], tload=ty["rated_load_kg"] / 1000, k1x=ty["k1_km"], k1y=ty["k1"],
                tref=ty["k2_ref_c"], ahot=ty["k2_hot"], acold=ty["k2_cold"], tyre_max=ty["temp_alarm_c"],
                fe_lim=oil["fe_per_250h_alert_ppm"], si_lim=oil["si_alert_ppm"], iso=oil["hyd_iso_target"])


def interp(x, xp, fp):
    """np.interp for one value (clamped at both ends)."""
    if x <= xp[0]:
        return fp[0]
    if x >= xp[-1]:
        return fp[-1]
    for i in range(1, len(xp)):
        if x <= xp[i]:
            return fp[i - 1] + (fp[i] - fp[i - 1]) * (x - xp[i - 1]) / (xp[i] - xp[i - 1])


def k2(k, ta, vm):
    a = k["ahot"] if ta > k["tref"] else k["acold"]
    return 1 / (1 - a * (ta - k["tref"]) / vm)


def qm(k, mean_payload):
    """Average load per tyre (t), front and rear, Michelin's Qm = (Qc + Qv) / 2."""
    front = (k["ew"] * k["fe"] / 2 + (k["ew"] + mean_payload) * k["fl"] / 2) / 2
    rear = (k["ew"] * k["re"] / 4 + (k["ew"] + mean_payload) * k["rl"] / 4) / 2
    return front, rear


def engine_power(k, gvw_t, v_kmh, grade):
    wheel = max(gvw_t * 9.81 * v_kmh / 3.6 * (grade + k["rr"]) / 100, 0.0)
    if v_kmh < 1:
        return k["idle"], wheel
    return min(wheel / k["eta"] + k["acc"], k["rated"]), wheel


def _parts(twin):
    k = _k(twin)
    GVW = f"({k['ew']} + df['PAYLOAD_T'])"
    WP = f"np.maximum({GVW} * 9.81 * df['SPEED_KMH'] / 3.6 * (df['GRADE_PCT'] + {k['rr']}) / 100, 0)"
    EP = f"np.where(df['SPEED_KMH'] < 1, {k['idle']}, np.minimum({WP} / {k['eta']} + {k['acc']}, {k['rated']}))"
    LD = f"({EP} / {k['rated']})"
    FX = f"({k['f0']} + {EP} * {k['bsfc'] / (1000 * k['rho'])!r})"
    EXR = f"((df['EXH_LEFT_C'] + df['EXH_RIGHT_C']) / 2 - ({k['e0']} + {k['ef'] - k['e0']} * {LD}))"
    CX = f"np.maximum({k['treg']}, df['AMBIENT_C'] + {k['rise']} * {LD})"
    BB = f"(df['CRANKCASE_KPA'] - ({k['c0']} + {k['cf'] - k['c0']!r} * {LD}))"
    BR = f"(df['BOOST_KPA'] / ({k['b0']} + {k['bf'] - k['b0']} * {LD}))"
    cold = [f"((df['TYRE{i}_KPA'] + {P_ATM}) * (df['AMBIENT_C'] + 273.15) / (df['TYRE{i}_C'] + 273.15) - {P_ATM})" for i in range(1, 7)]
    CM = cold[0]
    for c in cold[1:]:
        CM = f"np.minimum({CM}, {c})"
    CMP = f"({CM} / {k['pset']} * 100)"
    TM = "df['TYRE1_C']"
    for i in range(2, 7):
        TM = f"np.maximum({TM}, df['TYRE{i}_C'])"
    MEAN = "df['SHIFT_PAYLOAD_MEAN_T']"
    QF = f"(({k['ew'] * k['fe'] / 2!r} + ({k['ew']} + {MEAN}) * {k['fl'] / 2!r}) / 2)"
    QR = f"(({k['ew'] * k['re'] / 4!r} + ({k['ew']} + {MEAN}) * {k['rl'] / 4!r}) / 2)"
    VM = "(df['CYCLE_KM'] / (df['CYCLE_MIN'] / 60))"
    K1 = f"np.interp(df['CYCLE_KM'], {k['k1x']}, {k['k1y']})"
    K2 = (f"(1 / (1 - np.where(df['AMBIENT_MAX_C'] > {k['tref']}, {k['ahot']}, {k['acold']}) * (df['AMBIENT_MAX_C'] - {k['tref']}) / {VM}))")
    TK = f"(np.maximum({QF}, {QR}) * {VM} * {K1} * {K2})"
    TL = (f"(np.where(df['PAYLOAD_T'] > 1, np.maximum({GVW} * {k['fl'] / 2!r}, {GVW} * {k['rl'] / 4!r}), "
          f"np.maximum({GVW} * {k['fe'] / 2!r}, {GVW} * {k['re'] / 4!r})) / {k['tload']} * 100)")
    ISO = (f"np.maximum(np.maximum(df['HYD_ISO4'] - {k['iso'][0]}, df['HYD_ISO6'] - {k['iso'][1]}), df['HYD_ISO14'] - {k['iso'][2]})")
    return dict(k=k, GVW=GVW, WP=WP, EP=EP, LD=LD, FX=FX, EXR=EXR, CX=CX, BB=BB, BR=BR, CMP=CMP, TM=TM, TK=TK, TL=TL, ISO=ISO)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("PAYLOAD_PCT", f"df['PAYLOAD_T'] / {k['tgt']} * 100"),
        ("GVW_T", p["GVW"]),
        ("WHEEL_POWER_KW", p["WP"]),
        ("ENGINE_POWER_EXP_KW", p["EP"]),
        ("FUEL_EXP_LPH", p["FX"]),
        ("FUEL_RATIO", f"df['FUEL_LPH'] / {p['FX']}"),
        ("BOOST_RATIO", p["BR"]),
        ("EXH_RESID_C", p["EXR"]),
        ("EXH_SPREAD_C", "np.abs(df['EXH_LEFT_C'] - df['EXH_RIGHT_C'])"),
        ("COOLANT_EXP_C", p["CX"]),
        ("COOLANT_RESID_C", f"df['COOLANT_C'] - {p['CX']}"),
        ("BLOWBY_RESID_KPA", p["BB"]),
        ("FE_PER_250H", "df['OIL_FE_PPM'] * 250 / df['OIL_HOURS']"),
        ("HYD_ISO_EXCESS", p["ISO"]),
        ("TYRE_COLD_MIN_PCT", p["CMP"]),
        ("TYRE_TEMP_MAX_C", p["TM"]),
        ("TYRE_LOAD_PCT", p["TL"]),
        ("TKPH_SITE", p["TK"]),
        ("TKPH_RATIO", f"{p['TK']} / {k['tkph']}"),
        ("FUEL_LIFE_PCT", f"df['FUEL_TOTAL_L'] / {k['life']} * 100"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    gvw = k["ew"] + r["payload_t"]
    ep, wp = engine_power(k, gvw, r["speed_kmh"], r["grade_pct"])
    ld = ep / k["rated"]
    fx = k["f0"] + ep * (k['bsfc'] / (1000 * k['rho']))
    cx = max(k["treg"], r["ambient_c"] + k["rise"] * ld)
    cold = [(r[f"tyre{i}_kpa"] + P_ATM) * (r["ambient_c"] + 273.15) / (r[f"tyre{i}_c"] + 273.15) - P_ATM for i in range(1, 7)]
    qf, qr = qm(k, r["shift_payload_mean_t"])
    vm = r["cycle_km"] / (r["cycle_min"] / 60)
    tk = max(qf, qr) * vm * interp(r["cycle_km"], k["k1x"], k["k1y"]) * k2(k, r["ambient_max_c"], vm)
    if r["payload_t"] > 1:
        tl = max(gvw * k["fl"] / 2, gvw * k["rl"] / 4)
    else:
        tl = max(gvw * k["fe"] / 2, gvw * k["re"] / 4)
    return {
        "payload_pct": r["payload_t"] / k["tgt"] * 100, "gvw_t": gvw, "wheel_power_kw": wp, "engine_power_exp_kw": ep,
        "fuel_exp_lph": fx, "fuel_ratio": r["fuel_lph"] / fx,
        "boost_ratio": r["boost_kpa"] / (k["b0"] + (k["bf"] - k["b0"]) * ld),
        "exh_resid_c": (r["exh_left_c"] + r["exh_right_c"]) / 2 - (k["e0"] + (k["ef"] - k["e0"]) * ld),
        "exh_spread_c": abs(r["exh_left_c"] - r["exh_right_c"]),
        "coolant_exp_c": cx, "coolant_resid_c": r["coolant_c"] - cx,
        "blowby_resid_kpa": r["crankcase_kpa"] - (k["c0"] + float(f"{k['cf'] - k['c0']!r}") * ld),
        "fe_per_250h": r["oil_fe_ppm"] * 250 / r["oil_hours"],
        "hyd_iso_excess": max(r["hyd_iso4"] - k["iso"][0], r["hyd_iso6"] - k["iso"][1], r["hyd_iso14"] - k["iso"][2]),
        "tyre_cold_min_pct": min(cold) / k["pset"] * 100,
        "tyre_temp_max_c": max(r[f"tyre{i}_c"] for i in range(1, 7)),
        "tyre_load_pct": tl / k["tload"] * 100,
        "tkph_site": tk, "tkph_ratio": tk / k["tkph"],
        "fuel_life_pct": r["fuel_total_l"] / k["life"] * 100,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    pol = twin["design"]["payload_policy"]
    p = _parts(twin)
    k = p["k"]
    PP = f"(df['PAYLOAD_T'] / {k['tgt']} * 100)"
    G = f"({p['LD']} > {L['load_gate']})"
    return [
        ("HT_OVERLOAD_120", f"{PP} > {L['payload_max_pct']}", "Critical", None),
        ("HT_PAYLOAD_POLICY", f"(df['SHIFT_OVER110_PCT'] > {pol['over110_share_max_pct']}) | (df['SHIFT_PAYLOAD_MEAN_T'] > {k['tgt']})", "High", "payload_overload"),
        ("HT_EXH_HIGH", f"{G} & ({p['EXR']} > {L['exhaust_resid_alert_c']})", "High", "air_intake_restriction"),
        ("HT_EXH_SPREAD", f"{G} & (np.abs(df['EXH_LEFT_C'] - df['EXH_RIGHT_C']) > {L['exhaust_spread_alert_c']})", "High", "injector_fault"),
        ("HT_COOLANT_HIGH", f"(df['COOLANT_C'] - {p['CX']}) > {L['coolant_resid_alert_k']}", "High", "cooling_degraded"),
        ("HT_TYRE_PRESSURE_LOW", f"{p['CMP']} < {L['tyre_cold_min_pct']}", "High", "tyre_underinflation"),
        ("HT_TYRE_TEMP_HIGH", f"{p['TM']} > {k['tyre_max']}", "High", "tyre_underinflation"),
        ("HT_TKPH_LIMIT", f"({p['TK']} / {k['tkph']}) > {L['tkph_ratio_alert']}", "High", "tkph_exceeded"),
        ("HT_OVERLOAD_110", f"({PP} > {L['payload_warn_pct']}) & ({PP} <= {L['payload_max_pct']})", "Medium", "payload_overload"),
        ("HT_FUEL_HIGH", f"{G} & ((df['FUEL_LPH'] / {p['FX']}) > {L['fuel_ratio_alert']})", "Medium", "air_intake_restriction"),
        ("HT_BOOST_LOW", f"{G} & ({p['BR']} < {L['boost_ratio_alert']})", "Medium", "air_intake_restriction"),
        ("HT_BLOWBY_HIGH", f"{p['BB']} > {L['blowby_resid_alert_kpa']}", "Medium", "dust_ingestion"),
        ("HT_OIL_WEAR", f"(df['OIL_FE_PPM'] * 250 / df['OIL_HOURS']) > {k['fe_lim']}", "Medium", "dust_ingestion"),
        ("HT_OIL_DIRT", f"df['OIL_SI_PPM'] > {k['si_lim']}", "Medium", "dust_ingestion"),
        ("HT_HYD_CLEANLINESS", f"{p['ISO']} > 0", "Medium", "hydraulic_contamination"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}

TYRE_POS = ["front left", "front right", "rear left outer", "rear left inner", "rear right inner", "rear right outer"]


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    pol = twin["design"]["payload_policy"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    pp, ld = t["payload_pct"], t["engine_power_exp_kw"] / k["rated"]
    gate = ld > L["load_gate"]
    add(pp > L["payload_max_pct"], "HT_OVERLOAD_120", "Critical", f"Load of {r['payload_t']:.0f} t is {pp:.0f} % of target: above the 120 % no load may exceed", "payload")
    add(r["shift_over110_pct"] > pol["over110_share_max_pct"] or r["shift_payload_mean_t"] > k["tgt"], "HT_PAYLOAD_POLICY", "High",
        f"Shift: mean payload {r['shift_payload_mean_t']:.0f} t (target {k['tgt']}), {r['shift_over110_pct']:.0f} % of loads above 110 %", "payload", "payload_overload")
    add(gate and t["exh_resid_c"] > L["exhaust_resid_alert_c"], "HT_EXH_HIGH", "High",
        f"Exhaust {t['exh_resid_c']:.0f} K hotter than expected at {ld * 100:.0f} % load", "air intake", "air_intake_restriction")
    add(gate and t["exh_spread_c"] > L["exhaust_spread_alert_c"], "HT_EXH_SPREAD", "High",
        f"Exhaust banks differ by {t['exh_spread_c']:.0f} K (left {r['exh_left_c']:.0f}, right {r['exh_right_c']:.0f} °C)", "fuel system", "injector_fault")
    add(t["coolant_resid_c"] > L["coolant_resid_alert_k"], "HT_COOLANT_HIGH", "High",
        f"Coolant {r['coolant_c']:.0f} °C, {t['coolant_resid_c']:.0f} K above the {t['coolant_exp_c']:.0f} °C expected", "cooling", "cooling_degraded")
    cold = [((r[f"tyre{i}_kpa"] + P_ATM) * (r["ambient_c"] + 273.15) / (r[f"tyre{i}_c"] + 273.15) - P_ATM) / k["pset"] * 100 for i in range(1, 7)]
    worst = cold.index(min(cold))
    add(t["tyre_cold_min_pct"] < L["tyre_cold_min_pct"], "HT_TYRE_PRESSURE_LOW", "High",
        f"Tyre {worst + 1} ({TYRE_POS[worst]}) at {t['tyre_cold_min_pct']:.0f} % of its cold set pressure", "tyres", "tyre_underinflation")
    hot = max(range(6), key=lambda i: r[f"tyre{i + 1}_c"])
    add(t["tyre_temp_max_c"] > k["tyre_max"], "HT_TYRE_TEMP_HIGH", "High", f"Tyre {hot + 1} ({TYRE_POS[hot]}) at {t['tyre_temp_max_c']:.0f} °C", "tyres", "tyre_underinflation")
    add(t["tkph_ratio"] > L["tkph_ratio_alert"], "HT_TKPH_LIMIT", "High",
        f"Site TKPH {t['tkph_site']:.0f} against the tyre's {k['tkph']}: the tyres will overheat on this cycle", "haul cycle", "tkph_exceeded")
    add(L["payload_warn_pct"] < pp <= L["payload_max_pct"], "HT_OVERLOAD_110", "Medium", f"Load of {r['payload_t']:.0f} t is {pp:.0f} % of target", "payload", "payload_overload")
    add(gate and t["fuel_ratio"] > L["fuel_ratio_alert"], "HT_FUEL_HIGH", "Medium",
        f"Fuel {r['fuel_lph']:.0f} L/h, {t['fuel_ratio']:.2f} × expected for the work done", "air intake", "air_intake_restriction")
    add(gate and t["boost_ratio"] < L["boost_ratio_alert"], "HT_BOOST_LOW", "Medium", f"Boost {r['boost_kpa']:.0f} kPa, {t['boost_ratio']:.2f} × expected", "air intake", "air_intake_restriction")
    add(t["blowby_resid_kpa"] > L["blowby_resid_alert_kpa"], "HT_BLOWBY_HIGH", "Medium", f"Crankcase pressure {r['crankcase_kpa']:.2f} kPa, {t['blowby_resid_kpa']:+.2f} kPa vs expected", "engine", "dust_ingestion")
    add(t["fe_per_250h"] > k["fe_lim"], "HT_OIL_WEAR", "Medium", f"Iron {t['fe_per_250h']:.0f} ppm per 250 h on the oil", "engine", "dust_ingestion")
    add(r["oil_si_ppm"] > k["si_lim"], "HT_OIL_DIRT", "Medium", f"Silicon {r['oil_si_ppm']:.0f} ppm: dirt is getting past the air filter", "engine", "dust_ingestion")
    add(t["hyd_iso_excess"] > 0, "HT_HYD_CLEANLINESS", "Medium",
        f"Hydraulic oil ISO {r['hyd_iso4']:.0f}/{r['hyd_iso6']:.0f}/{r['hyd_iso14']:.0f}, target {k['iso'][0]}/{k['iso'][1]}/{k['iso'][2]}", "hydraulics", "hydraulic_contamination")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
