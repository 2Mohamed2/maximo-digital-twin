"""The passenger elevator twin's expectations (EL-5701, KONE MonoSpace 500, 1000 kg, 1.6 m/s).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Hoisting (traction, counterweight = car + k Q):
  The car side and the counterweight side differ by the out-of-balance mass L - k Q (L = load in the car, Q = rated load,
  k = balance ratio). At constant speed the drive must hold that weight and overcome the running friction F_f (guide
  shoes, rope bending, sheave bearings), which always acts against the motion:
      F = (L - k Q) g + d F_f                d = +1 going up, -1 going down        force referred to the car (N)
      T = F r / i                            motor torque, r = sheave radius, i = roping ratio (2:1)
  The controller sends the constant-speed torque and the load of the last up trip and of the last down trip. With
  F_up = T_up i / r and F_dn = T_dn i / r the two equations solve for the two unknowns of the hoistway:
      F_f  (apparent friction)  = (F_up - F_dn - (L_up - L_dn) g) / 2
      k    (apparent balance)   = (L_up + L_dn - (F_up + F_dn) / g) / (2 Q)
  A counterweight out of balance moves both torques the same way; friction moves them apart. The twin tells them apart.
Brake: the drive's automatic test pushes the motor against the closed brake; the twin divides the torque the brake held
  by the torque needed to hold 1.25 Q against the counterweight: (1.25 - k) Q g r / i.
Doors: closing time and peak operator current against the commissioning baseline; reopenings and re-levellings per
  100 starts (with at least 20 starts in the denominator, so a quiet night hour does not make a rate out of one event).
Energy (reference cycle measured at commissioning, as ISO 25745-1 describes):
      running energy per trip = (E_24h - P_standby x 24 h) / trips
      expected per trip       = e_start + e_metre x (distance / trips)
Ropes: trips since the rope change against the expected rope life. Traffic: starts per hour against the rated starts.
"""


def _k(twin):
    d = twin["design"]
    c, h, dr, br, e = d["car"], d["hoist"], d["doors"], d["brake"], d["energy"]
    r = h["sheave_d_m"] / 2
    return dict(Q=c["rated_load_kg"], kb=h["balance_ratio"], r=r, i=h["roping"], ff=h["friction_kn"], g=h["g"],
                v=c["speed_ms"], open0=dr["open_time_s"], close0=dr["close_time_s"], amp0=dr["close_current_a"],
                stop_acc=d["ride"]["stop_accuracy_mm"], lev_acc=d["ride"]["level_accuracy_mm"],
                brl=br["test_required_load_ratio"], e0=e["e_start_wh"], em=e["e_metre_wh"], psb=e["standby_w"],
                rope=d["ropes"]["life_trips"], starts=d["traffic"]["rated_starts_per_h"],
                travel=d["shaft"]["travel_m"], stops=d["shaft"]["stops"])


def f_per_nm(k):
    """Newtons at the car per newton-metre of motor torque: i / r."""
    return k["i"] / k["r"]


def brake_required_nm(k):
    """Torque needed to hold brl x Q in the car against the counterweight."""
    return (k["brl"] - k["kb"]) * k["Q"] * k["g"] * k["r"] / k["i"]


def torque_expected(k, load, d, ff=None, kb=None):
    """Constant-speed motor torque (N m) for a car load (kg) and direction d (+1 up, -1 down)."""
    ff = k["ff"] if ff is None else ff
    kb = k["kb"] if kb is None else kb
    return ((load - kb * k["Q"]) * k["g"] + d * ff * 1000) * k["r"] / k["i"]


def _parts(twin):
    k = _k(twin)
    L = twin["twin_model"]["limits"]
    c = f_per_nm(k) / 1000
    UF = f"(df['UP_TORQUE_NM'] * {c})"
    DF = f"(df['DOWN_TORQUE_NM'] * {c})"
    FA = f"(({UF} - {DF} - (df['UP_LOAD_KG'] - df['DOWN_LOAD_KG']) * {k['g'] / 1000}) / 2)"
    BA = f"((df['UP_LOAD_KG'] + df['DOWN_LOAD_KG'] - ({UF} + {DF}) * {1000 / k['g']}) / {2 * k['Q'] / 100})"
    rr = k["r"] / k["i"]
    UE = f"(((df['UP_LOAD_KG'] - {k['kb'] * k['Q']}) * {k['g']} + {k['ff'] * 1000}) * {rr})"
    DE = f"(((df['DOWN_LOAD_KG'] - {k['kb'] * k['Q']}) * {k['g']} - {k['ff'] * 1000}) * {rr})"
    ST = f"np.maximum(df['STARTS_1H'], {L['rate_min_starts']})"
    TR = "np.maximum(df['TRIPS_24H'], 1)"
    EPT = f"((df['ENERGY_KWH_24H'] - {k['psb'] * 24 / 1000}) * 1000 / {TR})"
    EEX = f"({k['e0']} + {k['em']} * df['DISTANCE_M_24H'] / {TR})"
    BR = f"(df['BRAKE_TEST_TORQUE_NM'] / {brake_required_nm(k)})"
    return dict(k=k, UF=UF, DF=DF, FA=FA, BA=BA, UE=UE, DE=DE, ST=ST, EPT=EPT, EEX=EEX, BR=BR)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("UP_FORCE_KN", p["UF"]),
        ("DOWN_FORCE_KN", p["DF"]),
        ("FRICTION_APPARENT_KN", p["FA"]),
        ("BALANCE_APPARENT_PCT", p["BA"]),
        ("BALANCE_DEV_PCT", f"{p['BA']} - {k['kb'] * 100}"),
        ("UP_TORQUE_EXPECTED_NM", p["UE"]),
        ("DOWN_TORQUE_EXPECTED_NM", p["DE"]),
        ("UP_TORQUE_RESIDUAL_NM", f"df['UP_TORQUE_NM'] - {p['UE']}"),
        ("DOWN_TORQUE_RESIDUAL_NM", f"df['DOWN_TORQUE_NM'] - {p['DE']}"),
        ("DOOR_CLOSE_RATIO", f"df['DOOR_CLOSE_TIME_S'] / {k['close0']}"),
        ("DOOR_CURRENT_RATIO", f"df['DOOR_CLOSE_CURRENT_A'] / {k['amp0']}"),
        ("REOPEN_RATE_PCT", f"df['DOOR_REOPENS_1H'] / {p['ST']} * 100"),
        ("RELEVEL_RATE_PCT", f"df['RELEVELS_1H'] / {p['ST']} * 100"),
        ("BRAKE_TEST_RATIO", p["BR"]),
        ("ENERGY_PER_TRIP_WH", p["EPT"]),
        ("ENERGY_EXPECTED_WH", p["EEX"]),
        ("ENERGY_RATIO", f"{p['EPT']} / {p['EEX']}"),
        ("ROPE_LIFE_USED_PCT", f"df['TRIPS_SINCE_ROPE_CHANGE'] / {k['rope'] / 100}"),
        ("STARTS_RATIO", f"df['STARTS_1H'] / {k['starts']}"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    L = twin["twin_model"]["limits"]
    c = f_per_nm(k) / 1000
    uf, df_ = r["up_torque_nm"] * c, r["down_torque_nm"] * c
    fa = (uf - df_ - (r["up_load_kg"] - r["down_load_kg"]) * (k["g"] / 1000)) / 2
    ba = (r["up_load_kg"] + r["down_load_kg"] - (uf + df_) * (1000 / k["g"])) / (2 * k["Q"] / 100)
    ue, de = torque_expected(k, r["up_load_kg"], 1), torque_expected(k, r["down_load_kg"], -1)
    st = max(r["starts_1h"], L["rate_min_starts"])
    tr = max(r["trips_24h"], 1)
    ept = (r["energy_kwh_24h"] - k["psb"] * 24 / 1000) * 1000 / tr
    eex = k["e0"] + k["em"] * r["distance_m_24h"] / tr
    return {
        "up_force_kn": uf, "down_force_kn": df_, "friction_apparent_kn": fa, "balance_apparent_pct": ba,
        "balance_dev_pct": ba - k["kb"] * 100, "up_torque_expected_nm": ue, "down_torque_expected_nm": de,
        "up_torque_residual_nm": r["up_torque_nm"] - ue, "down_torque_residual_nm": r["down_torque_nm"] - de,
        "door_close_ratio": r["door_close_time_s"] / k["close0"], "door_current_ratio": r["door_close_current_a"] / k["amp0"],
        "reopen_rate_pct": r["door_reopens_1h"] / st * 100, "relevel_rate_pct": r["relevels_1h"] / st * 100,
        "brake_test_ratio": r["brake_test_torque_nm"] / brake_required_nm(k),
        "energy_per_trip_wh": ept, "energy_expected_wh": eex, "energy_ratio": ept / eex,
        "rope_life_used_pct": r["trips_since_rope_change"] / (k["rope"] / 100), "starts_ratio": r["starts_1h"] / k["starts"],
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    return [
        ("EL_BRAKE_TEST_FAIL", f"{p['BR']} < {L['brake_margin_limit']}", "Critical", "brake_wear"),
        ("EL_DOOR_LOCK_FAIL", f"df['DOOR_LOCK_FAILS_24H'] > {L['lock_fails_alert']}", "High", "door_lock_fault"),
        ("EL_LEVELLING", f"df['LEVEL_ERROR_MAX_MM'] > {k['stop_acc']}", "High", "levelling_drift"),
        ("EL_BRAKE_MARGIN_LOW", f"({p['BR']} < {L['brake_margin_alert']}) & ({p['BR']} >= {L['brake_margin_limit']})", "Medium", "brake_wear"),
        ("EL_BRAKE_TEST_OVERDUE", f"df['BRAKE_TEST_HOURS_SINCE'] > {L['brake_test_max_h']}", "Medium", None),
        ("EL_DOOR_SLOW", f"(df['DOOR_CLOSE_TIME_S'] / {k['close0']}) > {L['door_close_ratio_alert']}", "Medium", "door_obstruction"),
        ("EL_DOOR_CURRENT_HIGH", f"(df['DOOR_CLOSE_CURRENT_A'] / {k['amp0']}) > {L['door_current_ratio_alert']}", "Medium", "door_obstruction"),
        ("EL_DOOR_REOPENS", f"(df['DOOR_REOPENS_1H'] / {p['ST']} * 100) > {L['reopen_rate_alert_pct']}", "Medium", "light_curtain_fault"),
        ("EL_BALANCE_OFF", f"np.abs({p['BA']} - {k['kb'] * 100}) > {L['balance_dev_alert_pct']}", "Medium", "counterweight_imbalance"),
        ("EL_FRICTION_HIGH", f"{p['FA']} > {L['friction_alert_kn']}", "Medium", "guide_friction_high"),
        ("EL_RIDE_LATERAL", f"df['VIB_LATERAL_MG'] > {L['vib_lateral_alert_mg']}", "Medium", "guide_friction_high"),
        ("EL_RELEVEL_HIGH", f"(df['RELEVELS_1H'] / {p['ST']} * 100) > {L['relevel_rate_alert_pct']}", "Medium", "levelling_drift"),
        ("EL_ENERGY_HIGH", f"({p['EPT']} / {p['EEX']}) > {L['energy_ratio_alert']}", "Medium", "regen_lost"),
        ("EL_ROPE_LIFE", f"(df['TRIPS_SINCE_ROPE_CHANGE'] / {k['rope'] / 100}) > {L['rope_life_alert_pct']}", "Medium", None),
        ("EL_STARTS_HIGH", f"df['STARTS_1H'] > {k['starts']}", "Low", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    br, bd = t["brake_test_ratio"], t["balance_dev_pct"]
    add(br < L["brake_margin_limit"], "EL_BRAKE_TEST_FAIL", "Critical",
        f"Brake held only {br:.2f} x the test torque: take the elevator out of service", "brake", "brake_wear")
    add(r["door_lock_fails_24h"] > L["lock_fails_alert"], "EL_DOOR_LOCK_FAIL", "High",
        f"{r['door_lock_fails_24h']:.0f} closings in 24 h without the door lock contact made", "doors", "door_lock_fault")
    add(r["level_error_max_mm"] > k["stop_acc"], "EL_LEVELLING", "High",
        f"Car stopped {r['level_error_max_mm']:.0f} mm from the landing (limit ±{k['stop_acc']:.0f} mm): trip hazard", "hoist", "levelling_drift")
    add(L["brake_margin_limit"] <= br < L["brake_margin_alert"], "EL_BRAKE_MARGIN_LOW", "Medium",
        f"Brake held {br:.2f} x the test torque, below {L['brake_margin_alert']}", "brake", "brake_wear")
    add(r["brake_test_hours_since"] > L["brake_test_max_h"], "EL_BRAKE_TEST_OVERDUE", "Medium",
        f"Last automatic brake test {r['brake_test_hours_since']:.0f} h ago", "brake")
    add(t["door_close_ratio"] > L["door_close_ratio_alert"], "EL_DOOR_SLOW", "Medium",
        f"Doors close in {r['door_close_time_s']:.1f} s, {t['door_close_ratio']:.2f} x the commissioning time", "doors", "door_obstruction")
    add(t["door_current_ratio"] > L["door_current_ratio_alert"], "EL_DOOR_CURRENT_HIGH", "Medium",
        f"Door operator draws {r['door_close_current_a']:.2f} A on closing, {t['door_current_ratio']:.2f} x baseline", "doors", "door_obstruction")
    add(t["reopen_rate_pct"] > L["reopen_rate_alert_pct"], "EL_DOOR_REOPENS", "Medium",
        f"Doors reopened on {t['reopen_rate_pct']:.0f} % of closings in the last hour", "doors", "light_curtain_fault")
    add(abs(bd) > L["balance_dev_alert_pct"], "EL_BALANCE_OFF", "Medium",
        f"Counterweight balances {t['balance_apparent_pct']:.0f} % of the rated load, design {k['kb'] * 100:.0f} %", "hoist", "counterweight_imbalance")
    add(t["friction_apparent_kn"] > L["friction_alert_kn"], "EL_FRICTION_HIGH", "Medium",
        f"Running friction {t['friction_apparent_kn']:.2f} kN, design {k['ff']:.2f} kN", "guides", "guide_friction_high")
    add(r["vib_lateral_mg"] > L["vib_lateral_alert_mg"], "EL_RIDE_LATERAL", "Medium",
        f"Horizontal vibration {r['vib_lateral_mg']:.0f} mg peak-to-peak", "guides", "guide_friction_high")
    add(t["relevel_rate_pct"] > L["relevel_rate_alert_pct"], "EL_RELEVEL_HIGH", "Medium",
        f"Re-levelled after {t['relevel_rate_pct']:.0f} % of the stops in the last hour", "hoist", "levelling_drift")
    add(t["energy_ratio"] > L["energy_ratio_alert"], "EL_ENERGY_HIGH", "Medium",
        f"{t['energy_per_trip_wh']:.1f} Wh per trip, {t['energy_ratio']:.2f} x the reference cycle", "drive", "regen_lost")
    add(t["rope_life_used_pct"] > L["rope_life_alert_pct"], "EL_ROPE_LIFE", "Medium",
        f"Ropes at {t['rope_life_used_pct']:.0f} % of their expected life in trips: plan the rope change", "ropes")
    add(r["starts_1h"] > k["starts"], "EL_STARTS_HIGH", "Low", f"{r['starts_1h']:.0f} starts in the last hour, rated {k['starts']}", "drive")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
