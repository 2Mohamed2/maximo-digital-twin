"""The point machine twin's expectations (PM-5501, Siemens S700K type, 220 mm stroke).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

The power curve of one throw (what the condition monitoring unit records on the three motor phases):
  unlock  the clamp lock opens; a short peak (starting current + breakaway), then the power settles
  drive   the throw bar pulls the switch blades across; the power is flat if the slide chairs are good
  lock    the blade closes on the stock rail and the clamp lock engages; the motor stops on the end-position contacts
Force at the throw bar from the electrical power. The induction motor runs at an almost constant speed, so the throw bar
moves at the nominal speed v = stroke / throwing time (data sheet), even while the friction clutch slips:
      P = P0 + F x v / eta            ->   F = eta x (P - P0) / v
  P0 = no-load power (magnetising and gear losses), eta = overall efficiency (motor x gearbox x ball screw).
Expected drive force with a temperature correction (cold: stiff lubricant and chairs; hot: rail expansion, blades bend):
      F_exp = F_ref + k_cold x max(0, T_low - T_rail) + k_hot x max(0, T_rail - T_high)
Energy per throw: E_exp = P0 x t_nominal + stroke x F_exp / eta + E_start (the starting transient).
Clutch margin: the clutch limits the force to the throwing force of the data sheet (5,500 N); a force near it means the
machine is pushing against something it cannot move.
"""

SQ3 = 1.7320508075688772


def _k(twin):
    d = twin["design"]
    m, c, md, ct, h = d["machine"], d["curve"], d["model"], d["control"], d["heating"]
    v = m["stroke_mm"] / 1000.0 / m["throw_time_s"]
    return dict(fc=m["throwing_force_n"], stroke=m["stroke_mm"], t_nom=m["throw_time_s"], u_nom=m["supply_v"],
                overhaul=m["overhaul_throws"], v=v, p0=md["no_load_w"], eta=md["efficiency"], e0=md["start_energy_j"],
                fref=md["force_ref_n"], tl=md["t_low_c"], th=md["t_high_c"], kc=md["k_cold_n_per_k"], kh=md["k_hot_n_per_k"],
                peak=c["unlock_peak_w"], t_lim=ct["time_limit_s"], ih=h["rated_current_a"], ton=h["switch_on_c"],
                cf=md["efficiency"] / v)


def force_expected(k, t_rail):
    return k["fref"] + k["kc"] * max(0.0, k["tl"] - t_rail) + k["kh"] * max(0.0, t_rail - k["th"])


def energy_expected_kj(k, f_exp):
    return (k["p0"] * k["t_nom"] + k["stroke"] / 1000.0 * f_exp / k["eta"] + k["e0"]) / 1000.0


def _parts(twin):
    k = _k(twin)
    cf, p0 = repr(k['cf']), k["p0"]
    FD = f"({cf} * (df['DRIVE_POWER_MEAN_W'] - {p0}))"
    FP = f"({cf} * (df['DRIVE_POWER_PEAK_W'] - {p0}))"
    FL = f"({cf} * (df['LOCK_POWER_MEAN_W'] - {p0}))"
    FE = (f"({k['fref']} + {k['kc']} * np.maximum(0, {k['tl']} - df['RAIL_TEMP_C'])"
          f" + {k['kh']} * np.maximum(0, df['RAIL_TEMP_C'] - {k['th']}))")
    EE = (f"(({k['p0'] * k['t_nom'] + k['e0']!r} + {k['stroke'] / 1000.0 / k['eta']!r} * {FE}) / 1000)")
    return dict(k=k, FD=FD, FP=FP, FL=FL, FE=FE, EE=EE)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("THROW_SPEED_MM_S", f"{k['stroke']} / df['THROW_TIME_S']"),
        ("THROW_TIME_RATIO", f"df['THROW_TIME_S'] / {k['t_nom']}"),
        ("DRIVE_FORCE_N", p["FD"]),
        ("DRIVE_FORCE_PEAK_N", p["FP"]),
        ("LOCK_FORCE_N", p["FL"]),
        ("FORCE_EXPECTED_N", p["FE"]),
        ("FORCE_RATIO", f"{p['FD']} / {p['FE']}"),
        ("LOCK_FORCE_RATIO", f"{p['FL']} / {p['FE']}"),
        ("CLUTCH_MARGIN_N", f"{k['fc']} - np.maximum({p['FP']}, {p['FL']})"),
        ("ENERGY_EXPECTED_KJ", p["EE"]),
        ("ENERGY_RATIO", f"df['ENERGY_KJ'] / {p['EE']}"),
        ("UNLOCK_PEAK_RATIO", f"df['UNLOCK_PEAK_W'] / {k['peak']}"),
        ("VOLTAGE_RATIO", f"df['MOTOR_VOLTAGE_V'] / {k['u_nom']}"),
        ("POWER_FACTOR", f"df['DRIVE_POWER_MEAN_W'] / ({SQ3} * df['MOTOR_VOLTAGE_V'] * df['DRIVE_CURRENT_A'])"),
        ("HEATER_DEFICIT_A", f"df['HEATER_ON'] * {k['ih']} - df['HEATER_CURRENT_A']"),
        ("OVERHAUL_USED_PCT", f"df['THROWS_SINCE_OVERHAUL'] / {k['overhaul']} * 100"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    cf, p0 = k["cf"], k["p0"]
    fd = cf * (r["drive_power_mean_w"] - p0)
    fp = cf * (r["drive_power_peak_w"] - p0)
    fl = cf * (r["lock_power_mean_w"] - p0)
    fe = force_expected(k, r["rail_temp_c"])
    ee = energy_expected_kj(k, fe)
    return {
        "throw_speed_mm_s": k["stroke"] / r["throw_time_s"], "throw_time_ratio": r["throw_time_s"] / k["t_nom"],
        "drive_force_n": fd, "drive_force_peak_n": fp, "lock_force_n": fl, "force_expected_n": fe,
        "force_ratio": fd / fe, "lock_force_ratio": fl / fe, "clutch_margin_n": k["fc"] - max(fp, fl),
        "energy_expected_kj": ee, "energy_ratio": r["energy_kj"] / ee,
        "unlock_peak_ratio": r["unlock_peak_w"] / k["peak"], "voltage_ratio": r["motor_voltage_v"] / k["u_nom"],
        "power_factor": r["drive_power_mean_w"] / (SQ3 * r["motor_voltage_v"] * r["drive_current_a"]),
        "heater_deficit_a": r["heater_on"] * k["ih"] - r["heater_current_a"],
        "overhaul_used_pct": r["throws_since_overhaul"] / k["overhaul"] * 100,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    FR, LR = f"({p['FD']} / {p['FE']})", f"({p['FL']} / {p['FE']})"
    clutch = L["clutch_fraction"] * k["fc"]
    return [
        ("PTS_DETECTION_LOST", "df['DETECTION_OK'] < 0.5", "Critical", "obstruction"),
        ("PTS_TRAILED", "df['TRAILED'] > 0.5", "Critical", "trailed"),
        ("PTS_CLUTCH_LIMIT", f"np.maximum({p['FP']}, {p['FL']}) > {clutch:.6g}", "High", "obstruction"),
        ("PTS_FORCE_HIGH", f"{FR} > {L['force_ratio_alert']}", "High", "lubrication_loss"),
        ("PTS_HEATER_FAIL", f"(df['HEATER_ON'] > 0.5) & (df['HEATER_CURRENT_A'] < {L['heater_fraction_alert'] * k['ih']:.6g})", "High", "ice_heater"),
        ("PTS_FORCE_RISING", f"({FR} > {L['force_ratio_warn']}) & ({FR} <= {L['force_ratio_alert']})", "Medium", "lubrication_loss"),
        ("PTS_ENERGY_HIGH", f"df['ENERGY_KJ'] / {p['EE']} > {L['energy_ratio_alert']}", "Medium", "lubrication_loss"),
        ("PTS_LOCK_FORCE_HIGH", f"({LR} > {L['lock_force_ratio_alert']}) & ({p['FL']} <= {clutch:.6g})", "Medium", "ice_heater"),
        ("PTS_THROW_SLOW", f"df['THROW_TIME_S'] / {k['t_nom']} > {L['throw_time_ratio_alert']}", "Medium", "obstruction"),
        ("PTS_UNLOCK_PEAK_HIGH", f"df['UNLOCK_PEAK_W'] > {L['unlock_peak_alert_w']}", "Medium", "unlock_tight"),
        ("PTS_SUPPLY_LOW", f"df['MOTOR_VOLTAGE_V'] / {k['u_nom']} < {L['voltage_ratio_alert']}", "Medium", "supply_low"),
        ("PTS_DETECTION_FLICKER", f"df['DETECTION_LOSSES_24H'] >= {L['detection_losses_alert']}", "Medium", "detector_adjust"),
        ("PTS_OVERHAUL_DUE", f"df['THROWS_SINCE_OVERHAUL'] > {L['overhaul_fraction'] * k['overhaul']:.6g}", "Low", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    clutch = L["clutch_fraction"] * k["fc"]
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    fr, lr = t["force_ratio"], t["lock_force_ratio"]
    fmax = max(t["drive_force_peak_n"], t["lock_force_n"])
    add(r["detection_ok"] < 0.5, "PTS_DETECTION_LOST", "Critical", "No end-position detection after the last throw: points out of use, signals at danger", "detection", "obstruction")
    add(r["trailed"] > 0.5, "PTS_TRAILED", "Critical", "Points trailed: trailing clutch released, examine the switch before use", "detection", "trailed")
    add(fmax > clutch, "PTS_CLUTCH_LIMIT", "High", f"Force {fmax:.0f} N, at the clutch limit of {k['fc']:.0f} N: the machine pushes against something", "turnout", "obstruction")
    add(fr > L["force_ratio_alert"], "PTS_FORCE_HIGH", "High", f"Drive force {t['drive_force_n']:.0f} N, {fr:.2f} x expected at {r['rail_temp_c']:.0f} °C rail", "turnout", "lubrication_loss")
    add(r["heater_on"] > 0.5 and r["heater_current_a"] < L["heater_fraction_alert"] * k["ih"], "PTS_HEATER_FAIL", "High",
        f"Point heating on but drawing {r['heater_current_a']:.1f} A of {k['ih']:.0f} A", "heating", "ice_heater")
    add(L["force_ratio_warn"] < fr <= L["force_ratio_alert"], "PTS_FORCE_RISING", "Medium", f"Drive force {fr:.2f} x expected: plan lubrication", "turnout", "lubrication_loss")
    add(t["energy_ratio"] > L["energy_ratio_alert"], "PTS_ENERGY_HIGH", "Medium", f"Energy per throw {r['energy_kj']:.2f} kJ, {t['energy_ratio']:.2f} x expected", "turnout", "lubrication_loss")
    add(lr > L["lock_force_ratio_alert"] and t["lock_force_n"] <= clutch, "PTS_LOCK_FORCE_HIGH", "Medium",
        f"Lock-phase force {t['lock_force_n']:.0f} N, {lr:.2f} x expected: resistance at the toe", "turnout", "ice_heater")
    add(t["throw_time_ratio"] > L["throw_time_ratio_alert"], "PTS_THROW_SLOW", "Medium", f"Throw took {r['throw_time_s']:.1f} s against {k['t_nom']:.0f} s", "machine", "obstruction")
    add(r["unlock_peak_w"] > L["unlock_peak_alert_w"], "PTS_UNLOCK_PEAK_HIGH", "Medium", f"Start peak {r['unlock_peak_w']:.0f} W: blade held tight at unlocking", "turnout", "unlock_tight")
    add(t["voltage_ratio"] < L["voltage_ratio_alert"], "PTS_SUPPLY_LOW", "Medium", f"Motor voltage {r['motor_voltage_v']:.0f} V ({t['voltage_ratio'] * 100:.0f} %)", "supply", "supply_low")
    add(r["detection_losses_24h"] >= L["detection_losses_alert"], "PTS_DETECTION_FLICKER", "Medium",
        f"Detection lost {r['detection_losses_24h']:.0f} times in 24 h while lying", "detection", "detector_adjust")
    add(r["throws_since_overhaul"] > L["overhaul_fraction"] * k["overhaul"], "PTS_OVERHAUL_DUE", "Low",
        f"{r['throws_since_overhaul']:.0f} throws since overhaul ({t['overhaul_used_pct']:.0f} % of {k['overhaul']:.0f})", "machine")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
