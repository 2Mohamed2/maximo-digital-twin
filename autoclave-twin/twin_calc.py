"""The steam sterilizer twin's expectations (ST-6601, BMT STERIVAP HP 669-2, 134 C porous-load cycle).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Saturated steam check (IAPWS-IF97 region 4, p in MPa, T in K):
    Ts(p):  beta = p^0.25;  E = beta^2 + n3 beta + n6;  F = n1 beta^2 + n4 beta + n7;  G = n2 beta^2 + n5 beta + n8
            D = 2G / (-F - sqrt(F^2 - 4EG));  Ts = (n10 + D - sqrt((n10 + D)^2 - 4 (n9 + n10 D))) / 2          (Eq. 31)
    ps(T):  theta = T + n9 / (T - n10);  A = theta^2 + n1 theta + n2;  B = n3 theta^2 + n4 theta + n5;
            C = n6 theta^2 + n7 theta + n8;  ps = (2C / (-B + sqrt(B^2 - 4AC)))^4                             (Eq. 30)
  In pure saturated steam the drain temperature equals Ts(chamber pressure). The deviation
      SAT_DEV = T_drain - Ts(P_chamber)
  is negative when air or other non-condensable gas is present (the steam has only part of the pressure: Dalton) and
  positive when the steam is superheated. UK guidance (HTM 01-01 Part C) allows 2 K. The air share follows from Dalton:
      air fraction = max(0, 1 - ps(T_drain) / P_chamber)        (0 when the steam is at or above saturation)
Lethality of the holding stage, conservative (lowest temperature for the whole holding time):
      F0 = hold minutes x 10^((T_min - 121.1) / 10)            (equivalent minutes at 121.1 C, z = 10 K)
Vacuum leak test: rate = rise / 10 min against 13 mbar per 10 min.
Energy: electric steam generator; expected kWh = base + steam kg x (hg - hf_feed) / 3600 / efficiency.
"""
import math

N = [0.0, 0.11670521452767e4, -0.72421316703206e6, -0.17073846940092e2, 0.12020824702470e5, -0.32325550322333e7,
     0.14915108613530e2, -0.48232657361591e4, 0.40511340542057e6, -0.23855557567849, 0.65017534844798e3]


def tsat_k(p_mpa):
    """IAPWS-IF97 Eq. (31): saturation temperature (K) at pressure p (MPa)."""
    b = p_mpa ** 0.25
    e = b * b + N[3] * b + N[6]
    f = N[1] * b * b + N[4] * b + N[7]
    g = N[2] * b * b + N[5] * b + N[8]
    d = 2 * g / (-f - math.sqrt(f * f - 4 * e * g))
    return (N[10] + d - math.sqrt((N[10] + d) ** 2 - 4 * (N[9] + N[10] * d))) / 2


def psat_mpa(t_k):
    """IAPWS-IF97 Eq. (30): saturation pressure (MPa) at temperature T (K)."""
    th = t_k + N[9] / (t_k - N[10])
    a = th * th + N[1] * th + N[2]
    b = N[3] * th * th + N[4] * th + N[5]
    c = N[6] * th * th + N[7] * th + N[8]
    return (2 * c / (-b + math.sqrt(b * b - 4 * a * c))) ** 4


def tsat_c(p_bar_a):
    return tsat_k(p_bar_a / 10) - 273.15


def psat_bar(t_c):
    return psat_mpa(t_c + 273.15) * 10


def _k(twin):
    d = twin["design"]
    pr, sa, le, te, sq, ja, va, ut, ds = (d["programme"], d["saturation"], d["lethality"], d["tests"], d["steam_quality"],
                                          d["jacket"], d["vacuum"], d["utilities"], d["door_seal"])
    kwh_kg = (ut["hg_kj_kg"] - ut["hf_feed_kj_kg"]) / 3600 / ut["generator_eff"]
    return dict(lo=pr["band_low_c"], hi=pr["band_high_c"], hold=pr["hold_s"], minhold=pr["min_hold_s"], sp=pr["setpoint_c"],
                tref=le["t_ref_c"], z=le["z_k"], lhold=te["leak_hold_min"], llim=te["leak_limit_mbar"], equil=te["equil_max_s"],
                vac=va["pulse_min_mbar"], smax=ut["steam_max_kg"], wmax=ut["water_max_l"], base=ut["energy_base_kwh"],
                kwh_kg=kwh_kg, seal=ds["life_cycles"], nominal=sq["supply_nominal_barg"],
                f0_req=pr["hold_s"] / 60 * 10 ** ((pr["band_low_c"] - le["t_ref_c"]) / le["z_k"]))


def _ts(p):
    """pandas expression: saturation temperature (C) of a pressure expression in bar abs."""
    n = N
    B = f"(({p} / 10) ** 0.25)"
    E = f"({B} ** 2 + {n[3]!r} * {B} + {n[6]!r})"
    F = f"({n[1]!r} * {B} ** 2 + {n[4]!r} * {B} + {n[7]!r})"
    G = f"({n[2]!r} * {B} ** 2 + {n[5]!r} * {B} + {n[8]!r})"
    D = f"(2 * {G} / (-{F} - np.sqrt({F} ** 2 - 4 * {E} * {G})))"
    return f"(({n[10]!r} + {D} - np.sqrt(({n[10]!r} + {D}) ** 2 - 4 * ({n[9]!r} + {n[10]!r} * {D}))) / 2 - 273.15)"


def _ps(t):
    """pandas expression: saturation pressure (bar abs) of a temperature expression in C."""
    n = N
    TK = f"({t} + 273.15)"
    TH = f"({TK} + {n[9]!r} / ({TK} - {n[10]!r}))"
    A = f"({TH} ** 2 + {n[1]!r} * {TH} + {n[2]!r})"
    B = f"({n[3]!r} * {TH} ** 2 + {n[4]!r} * {TH} + {n[5]!r})"
    C = f"({n[6]!r} * {TH} ** 2 + {n[7]!r} * {TH} + {n[8]!r})"
    return f"((2 * {C} / (-{B} + np.sqrt({B} ** 2 - 4 * {A} * {C}))) ** 4 * 10)"


def _parts(twin):
    k = _k(twin)
    TS = _ts("df['CYC_HOLD_PRESSURE_BAR_A']")
    SD = f"(df['CYC_HOLD_TEMP_MEAN_C'] - {TS})"
    PS = _ps("df['CYC_HOLD_TEMP_MEAN_C']")
    AIR = f"(np.maximum(1 - {PS} / df['CYC_HOLD_PRESSURE_BAR_A'], 0) * 100)"
    TJ = _ts("df['CYC_JACKET_PRESSURE_BAR_A']")
    EE = f"({k['base']} + df['CYC_STEAM_KG'] * {k['kwh_kg']:.10g})"
    F0 = f"(df['CYC_HOLD_TIME_S'] / 60 * 10 ** ((df['CYC_HOLD_TEMP_MIN_C'] - {k['tref']}) / {k['z']}))"
    return dict(k=k, TS=TS, SD=SD, AIR=AIR, TJ=TJ, EE=EE, F0=F0)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("TSAT_HOLD_C", p["TS"]),
        ("SAT_DEV_K", p["SD"]),
        ("AIR_FRACTION_PCT", p["AIR"]),
        ("BAND_MARGIN_LOW_K", f"df['CYC_HOLD_TEMP_MIN_C'] - {k['lo']}"),
        ("BAND_MARGIN_HIGH_K", f"{k['hi']} - df['CYC_HOLD_TEMP_MAX_C']"),
        ("HOLD_TIME_RATIO", f"df['CYC_HOLD_TIME_S'] / {k['hold']}"),
        ("F0_HOLD_MIN", p["F0"]),
        ("F0_MARGIN", f"{p['F0']} / {k['f0_req']:.10g}"),
        ("SENSOR_DIFF_K", "np.abs(df['CYC_HOLD_TEMP2_MEAN_C'] - df['CYC_HOLD_TEMP_MEAN_C'])"),
        ("TSAT_JACKET_C", p["TJ"]),
        ("JACKET_ABOVE_CHAMBER_K", f"{p['TJ']} - df['CYC_HOLD_TEMP_MEAN_C']"),
        ("LEAK_RATE_MBAR_MIN", f"df['LT_RISE_MBAR'] / {k['lhold']}"),
        ("LEAK_RATIO", f"df['LT_RISE_MBAR'] / {k['llim']}"),
        ("EQUIL_RATIO", f"df['BD_EQUIL_TIME_S'] / {k['equil']}"),
        ("VACUUM_RATIO", f"df['CYC_VAC_MIN_MBAR'] / {k['vac']}"),
        ("STEAM_RATIO", f"df['CYC_STEAM_KG'] / {k['smax']}"),
        ("WATER_RATIO", f"df['CYC_WATER_L'] / {k['wmax']}"),
        ("ENERGY_EXPECTED_KWH", p["EE"]),
        ("ENERGY_RATIO", f"df['CYC_ENERGY_KWH'] / {p['EE']}"),
        ("SEAL_LIFE_USED_PCT", f"df['CYCLES_SINCE_SEAL'] / {k['seal']} * 100"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    ts = tsat_c(r["cyc_hold_pressure_bar_a"])
    tj = tsat_c(r["cyc_jacket_pressure_bar_a"])
    ee = k["base"] + r["cyc_steam_kg"] * k["kwh_kg"]
    f0 = r["cyc_hold_time_s"] / 60 * 10 ** ((r["cyc_hold_temp_min_c"] - k["tref"]) / k["z"])
    return {
        "tsat_hold_c": ts, "sat_dev_k": r["cyc_hold_temp_mean_c"] - ts,
        "air_fraction_pct": max(1 - psat_bar(r["cyc_hold_temp_mean_c"]) / r["cyc_hold_pressure_bar_a"], 0.0) * 100,
        "band_margin_low_k": r["cyc_hold_temp_min_c"] - k["lo"], "band_margin_high_k": k["hi"] - r["cyc_hold_temp_max_c"],
        "hold_time_ratio": r["cyc_hold_time_s"] / k["hold"], "f0_hold_min": f0, "f0_margin": f0 / k["f0_req"],
        "sensor_diff_k": abs(r["cyc_hold_temp2_mean_c"] - r["cyc_hold_temp_mean_c"]),
        "tsat_jacket_c": tj, "jacket_above_chamber_k": tj - r["cyc_hold_temp_mean_c"],
        "leak_rate_mbar_min": r["lt_rise_mbar"] / k["lhold"], "leak_ratio": r["lt_rise_mbar"] / k["llim"],
        "equil_ratio": r["bd_equil_time_s"] / k["equil"], "vacuum_ratio": r["cyc_vac_min_mbar"] / k["vac"],
        "steam_ratio": r["cyc_steam_kg"] / k["smax"], "water_ratio": r["cyc_water_l"] / k["wmax"],
        "energy_expected_kwh": ee, "energy_ratio": r["cyc_energy_kwh"] / ee,
        "seal_life_used_pct": r["cycles_since_seal"] / k["seal"] * 100,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    SD, TJ, EE = p["SD"], p["TJ"], p["EE"]
    return [
        ("AC_HOLD_NOT_MET", f"(df['CYC_HOLD_TIME_S'] < {k['hold']}) | (df['CYC_HOLD_TEMP_MIN_C'] < {k['lo']}) | (df['CYC_HOLD_TEMP_MAX_C'] > {k['hi']})",
         "Critical", "steam_supply_low"),
        ("AC_AIR_IN_CHAMBER", f"{SD} < -{L['sat_dev_k']}", "High", "door_seal_wear"),
        ("AC_SUPERHEAT", f"{SD} > {L['sat_dev_k']}", "High", "jacket_overheat"),
        ("AC_BD_FAIL", f"(df['BD_RESULT'] < 0.5) | (df['BD_DELTA_T_C'] >= {L['bd_fail_k']})", "High", "door_seal_wear"),
        ("AC_LEAK_FAIL", f"df['LT_RISE_MBAR'] > {L['leak_limit_mbar']}", "High", "door_seal_wear"),
        ("AC_LEAK_RISING", f"(df['LT_RISE_MBAR'] > {L['leak_warn_mbar']}) & (df['LT_RISE_MBAR'] <= {L['leak_limit_mbar']})", "Medium", "door_seal_wear"),
        ("AC_EQUILIBRATION_SLOW", f"df['BD_EQUIL_TIME_S'] > {L['equil_max_s']}", "Medium", "door_seal_wear"),
        ("AC_VACUUM_WEAK", f"df['CYC_VAC_MIN_MBAR'] > {L['vac_alert_mbar']}", "Medium", "vacuum_pump_wear"),
        ("AC_JACKET_HOT", f"({TJ} - df['CYC_HOLD_TEMP_MEAN_C']) > {L['jacket_alert_k']}", "Medium", "jacket_overheat"),
        ("AC_SUPPLY_LOW", f"df['STEAM_SUPPLY_BAR_G'] < {L['supply_alert_barg']}", "Medium", "steam_supply_low"),
        ("AC_SENSOR_DISAGREE", f"np.abs(df['CYC_HOLD_TEMP2_MEAN_C'] - df['CYC_HOLD_TEMP_MEAN_C']) > {L['sensor_diff_k']}", "Medium", "sensor_drift"),
        ("AC_STEAM_HIGH", f"df['CYC_STEAM_KG'] / {k['smax']} > {L['steam_alert_ratio']}", "Medium", "drain_trap_passing"),
        ("AC_ENERGY_HIGH", f"df['CYC_ENERGY_KWH'] / {EE} > {L['energy_alert_ratio']}", "Medium", "generator_scaling"),
        ("AC_TESTS_OVERDUE", f"(df['BD_HOURS_SINCE'] > {L['bd_overdue_h']}) | (df['LT_HOURS_SINCE'] > {L['leak_overdue_h']})", "Medium", None),
        ("AC_SEAL_LIFE", f"df['CYCLES_SINCE_SEAL'] > {L['seal_life_cycles']}", "Low", "door_seal_wear"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    sd = t["sat_dev_k"]
    add(r["cyc_hold_time_s"] < k["hold"] or r["cyc_hold_temp_min_c"] < k["lo"] or r["cyc_hold_temp_max_c"] > k["hi"], "AC_HOLD_NOT_MET", "Critical",
        f"Holding {r['cyc_hold_time_s']:.0f} s between {r['cyc_hold_temp_min_c']:.1f} and {r['cyc_hold_temp_max_c']:.1f} °C: "
        f"needs {k['hold']:.0f} s inside {k['lo']:.0f}-{k['hi']:.0f} °C. Load not released", "chamber", "steam_supply_low")
    add(sd < -L["sat_dev_k"], "AC_AIR_IN_CHAMBER", "High",
        f"Drain {-sd:.1f} K colder than saturated steam at {r['cyc_hold_pressure_bar_a']:.3f} bar: about {t['air_fraction_pct']:.1f} % air or gas", "chamber", "door_seal_wear")
    add(sd > L["sat_dev_k"], "AC_SUPERHEAT", "High", f"Drain {sd:.1f} K hotter than saturated steam at the chamber pressure: superheated steam", "chamber", "jacket_overheat")
    add(r["bd_result"] < 0.5 or r["bd_delta_t_c"] >= L["bd_fail_k"], "AC_BD_FAIL", "High",
        f"Bowie-Dick failed: test-pack centre {r['bd_delta_t_c']:.1f} K below the drain at the start of holding. Sterilizer out of use", "chamber", "door_seal_wear")
    add(r["lt_rise_mbar"] > L["leak_limit_mbar"], "AC_LEAK_FAIL", "High",
        f"Vacuum leak test failed: {r['lt_rise_mbar']:.1f} mbar in 10 min (limit {L['leak_limit_mbar']:.0f})", "door", "door_seal_wear")
    add(L["leak_warn_mbar"] < r["lt_rise_mbar"] <= L["leak_limit_mbar"], "AC_LEAK_RISING", "Medium",
        f"Leak test {r['lt_rise_mbar']:.1f} mbar in 10 min, {t['leak_ratio'] * 100:.0f} % of the limit", "door", "door_seal_wear")
    add(r["bd_equil_time_s"] > L["equil_max_s"], "AC_EQUILIBRATION_SLOW", "Medium",
        f"Equilibration {r['bd_equil_time_s']:.0f} s, more than {L['equil_max_s']:.0f} s", "chamber", "door_seal_wear")
    add(r["cyc_vac_min_mbar"] > L["vac_alert_mbar"], "AC_VACUUM_WEAK", "Medium",
        f"Air-removal pulses reach only {r['cyc_vac_min_mbar']:.0f} mbar (usual {k['vac']:.0f})", "vacuum pump", "vacuum_pump_wear")
    add(t["jacket_above_chamber_k"] > L["jacket_alert_k"], "AC_JACKET_HOT", "Medium",
        f"Jacket {t['jacket_above_chamber_k']:.1f} K above the chamber", "jacket", "jacket_overheat")
    add(r["steam_supply_bar_g"] < L["supply_alert_barg"], "AC_SUPPLY_LOW", "Medium",
        f"Steam supply {r['steam_supply_bar_g']:.2f} bar g (nominal {k['nominal']:.1f})", "steam generator", "steam_supply_low")
    add(t["sensor_diff_k"] > L["sensor_diff_k"], "AC_SENSOR_DISAGREE", "Medium",
        f"Control and independent recorder differ by {t['sensor_diff_k']:.2f} K", "instrumentation", "sensor_drift")
    add(t["steam_ratio"] > L["steam_alert_ratio"], "AC_STEAM_HIGH", "Medium",
        f"{r['cyc_steam_kg']:.1f} kg of steam per cycle, {t['steam_ratio']:.2f} x the data sheet maximum", "drain", "drain_trap_passing")
    add(t["energy_ratio"] > L["energy_alert_ratio"], "AC_ENERGY_HIGH", "Medium",
        f"{r['cyc_energy_kwh']:.2f} kWh for {r['cyc_steam_kg']:.1f} kg of steam: {t['energy_ratio']:.2f} x expected", "steam generator", "generator_scaling")
    add(r["bd_hours_since"] > L["bd_overdue_h"] or r["lt_hours_since"] > L["leak_overdue_h"], "AC_TESTS_OVERDUE", "Medium",
        f"Bowie-Dick {r['bd_hours_since']:.0f} h ago, leak test {r['lt_hours_since']:.0f} h ago", "testing")
    add(r["cycles_since_seal"] > L["seal_life_cycles"], "AC_SEAL_LIFE", "Low",
        f"Door seals {r['cycles_since_seal']:.0f} cycles old (renew at {L['seal_life_cycles']})", "door", "door_seal_wear")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
