"""The data centre UPS twin's expectations (UPS-6101, Eaton 93PM-150(200)-N+1, four 50 kW modules, two VRLA strings).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Efficiency (double conversion, VFI). The published efficiency points (Energy Technology List, 25/50/75/100 % load) are
turned into a loss curve, fitted once in build_twin.py:
      loss(P) = a + b P + c P^2                               (kW, P = output power in kW, all four modules online)
  a is the no-load loss (fans, control, magnetising: per module), b P the switching loss (shared), c P^2 the conduction
  loss (I^2 R). With n modules online, each carries P / n, so
      loss_expected(P, n) = n a / 4 + b P + c P^2 x 4 / n      efficiency expected = P / (P + loss_expected)
  The measured loss is input power - output power; loss ratio = measured / expected (only in double conversion).
Energy Saver System (ESS): load on the static bypass, loss = f0 + k P (assumption from "> 99 %"). The saving if ESS
  were used all year: (loss_expected - loss_ess) x 8.76 MWh per year per kW.
Redundancy (N+1). Each module carries a third of its 50 kW on each phase, so the worst phase decides:
      P_phase,max = P_out x I_max / (I1 + I2 + I3)
      redundancy margin = (n - 1) x 50 kW - 3 x P_phase,max      (< 0: one more module failure drops the load to bypass)
      imbalance = (I_max - I_avg) / I_avg x 100 %
Cooling: heatsink rise over the inlet air, expected = R_th x (measured loss / n). Fan health = slowest fan speed / command.
DC link: ripple expected = floor + (full - floor) x (P_out / n) / 50 kW; ratio measured / expected grows as the
  electrolytic capacitors lose capacitance and their ESR rises.
Battery autonomy at the actual load (constant power discharge table of the block, to 1.75 V/cell):
      W per block = P_out x 1000 / eta_inverter / (strings x blocks)
      autonomy = t_table(W per block / SOH), interpolated in log(W) - log(t) between the data sheet points.
  A battery with 70 % of its capacity behaves like a new one asked for 1/0.7 times the power.
Battery ageing: ageing factor = 2^((T - 25) / 8) (life halves per 8 K); expected life = 10 y x 2^(-max(T_life - 25, 0) / 8)
  (no credit is taken for a battery kept cooler than 25 C: the data sheet gives 10 years at 25 C).
"""
import math


def _k(twin):
    d = twin["design"]
    u, e, s, b, th, dc, site = d["ups"], d["efficiency"], d["ess"], d["battery"], d["thermal"], d["dc_link"], d["site"]
    return dict(rated=u["rated_kw"], upm=u["upm_kw"], ninst=u["upm_installed"], a=e["loss_a_kw"], b=e["loss_b"], c=e["loss_c_per_kw"],
                f0=s["loss_fixed_kw"], fk=s["loss_frac"], nblk=b["strings"] * b["blocks_per_string"], tmin=b["table_min"],
                tw=b["table_w_per_block"], etab=b["inverter_eff_on_battery"], r0=b["r_block_mohm"], life=b["design_life_y"],
                tref=b["life_ref_c"], halv=b["life_halving_k"], rth=th["r_th_k_per_kw"], rp0=dc["ripple_floor_v"],
                rp1=dc["ripple_full_v"], req=site["required_autonomy_min"])


def loss_expected(k, p, n):
    """Expected double-conversion loss (kW) at output p (kW) with n modules online."""
    n = max(n, 1)
    return n * k["a"] / k["ninst"] + k["b"] * p + k["c"] * p * p * k["ninst"] / n


def _interp(x, xp, fp):
    """numpy.interp for one value (xp increasing), clamped at the ends."""
    if x <= xp[0]:
        return fp[0]
    if x >= xp[-1]:
        return fp[-1]
    for i in range(1, len(xp)):
        if x <= xp[i]:
            return fp[i - 1] + (x - xp[i - 1]) * (fp[i] - fp[i - 1]) / (xp[i] - xp[i - 1])
    return fp[-1]


def _tables(k):
    """log(W) increasing and the matching log(minutes), from the data sheet table."""
    lw = [math.log(w) for w in reversed(k["tw"])]
    lt = [math.log(t) for t in reversed(k["tmin"])]
    return lw, lt


def autonomy_min(k, p_kw, soh_pct):
    """Minutes to 1.75 V/cell at a constant output p_kw with the battery at soh_pct % of its capacity."""
    w = p_kw * 1000 / k["etab"] / k["nblk"] / (max(soh_pct, 1.0) / 100)
    lw, lt = _tables(k)
    return math.exp(_interp(math.log(max(w, 1e-6)), lw, lt))


def _parts(twin):
    k = _k(twin)
    N = "np.maximum(df['UPM_ONLINE'], 1)"
    P = "df['OUTPUT_POWER_KW']"
    LM = f"(df['INPUT_POWER_KW'] - {P})"
    LE = f"({N} * {k['a'] / k['ninst']:.9g} + {k['b']:.9g} * {P} + {k['c'] * k['ninst']:.9g} * {P} ** 2 / {N})"
    IS = "(df['OUTPUT_CURRENT_L1_A'] + df['OUTPUT_CURRENT_L2_A'] + df['OUTPUT_CURRENT_L3_A'])"
    IM = "np.maximum(np.maximum(df['OUTPUT_CURRENT_L1_A'], df['OUTPUT_CURRENT_L2_A']), df['OUTPUT_CURRENT_L3_A'])"
    PM = f"({P} * {IM} / {IS})"
    MARG = f"((np.round({N}) - 1) * {k['upm']} - 3 * {PM})"
    LESS = f"({k['f0']} + {k['fk']} * {P})"
    RISE = "(df['HEATSINK_TEMP_MAX_C'] - df['INLET_AIR_C'])"
    RISEX = f"({k['rth']} * {LM} / {N})"
    RIP = f"(df['DC_RIPPLE_V'] / ({k['rp0']} + {k['rp1'] - k['rp0']:.9g} * {P} / {N} / {k['upm']}))"
    BW = f"({P} * 1000 / {k['etab']} / {k['nblk']})"
    lw, lt = _tables(k)
    AUT = (f"np.exp(np.interp(np.log(np.maximum({BW} / (np.maximum(df['BATTERY_SOH_PCT'], 1.0) / 100), 1e-6)), "
           f"[{', '.join(repr(v) for v in lw)}], [{', '.join(repr(v) for v in lt)}]))")
    return dict(k=k, N=N, P=P, LM=LM, LE=LE, IS=IS, IM=IM, PM=PM, MARG=MARG, LESS=LESS, RISE=RISE, RISEX=RISEX, RIP=RIP, BW=BW, AUT=AUT)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("LOAD_PCT", f"{p['P']} / {k['rated']} * 100"),
        ("EFF_MEASURED_PCT", f"{p['P']} / df['INPUT_POWER_KW'] * 100"),
        ("LOSS_MEASURED_KW", p["LM"]),
        ("LOSS_EXPECTED_KW", p["LE"]),
        ("EFF_EXPECTED_PCT", f"{p['P']} / ({p['P']} + {p['LE']}) * 100"),
        ("LOSS_RATIO", f"{p['LM']} / {p['LE']}"),
        ("LOSS_ESS_KW", p["LESS"]),
        ("ESS_SAVING_MWH_Y", f"({p['LE']} - {p['LESS']}) * 8.76"),
        ("PHASE_IMBALANCE_PCT", f"(3 * {p['IM']} / {p['IS']} - 1) * 100"),
        ("PHASE_MAX_KW", p["PM"]),
        ("REDUNDANCY_MARGIN_KW", p["MARG"]),
        ("HEATSINK_RISE_K", p["RISE"]),
        ("HEATSINK_RISE_EXPECTED_K", p["RISEX"]),
        ("FAN_SPEED_RATIO", "df['FAN_SPEED_PCT'] / np.maximum(df['FAN_CMD_PCT'], 1)"),
        ("DC_RIPPLE_RATIO", p["RIP"]),
        ("BATT_R_RATIO", f"df['BATTERY_R_MAX_MOHM'] / {k['r0']}"),
        ("BATT_BLOCK_W", p["BW"]),
        ("AUTONOMY_MIN", p["AUT"]),
        ("BATT_AGEING_FACTOR", f"2 ** ((df['BATTERY_TEMP_C'] - {k['tref']}) / {k['halv']})"),
        ("BATT_LIFE_REMAINING_Y", f"{k['life']} * 2 ** (-np.maximum(df['BATTERY_TEMP_LIFE_C'] - {k['tref']}, 0) / {k['halv']}) - df['BATTERY_AGE_DAYS'] / 365"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    n = max(r["upm_online"], 1)
    p = r["output_power_kw"]
    lm = r["input_power_kw"] - p
    le = loss_expected(k, p, n)
    i1, i2, i3 = r["output_current_l1_a"], r["output_current_l2_a"], r["output_current_l3_a"]
    isum, imax = i1 + i2 + i3, max(i1, i2, i3)
    pm = p * imax / isum
    less = k["f0"] + k["fk"] * p
    bw = p * 1000 / k["etab"] / k["nblk"]
    return {
        "load_pct": p / k["rated"] * 100, "eff_measured_pct": p / r["input_power_kw"] * 100,
        "loss_measured_kw": lm, "loss_expected_kw": le, "eff_expected_pct": p / (p + le) * 100, "loss_ratio": lm / le,
        "loss_ess_kw": less, "ess_saving_mwh_y": (le - less) * 8.76,
        "phase_imbalance_pct": (3 * imax / isum - 1) * 100, "phase_max_kw": pm,
        "redundancy_margin_kw": (round(n) - 1) * k["upm"] - 3 * pm,
        "heatsink_rise_k": r["heatsink_temp_max_c"] - r["inlet_air_c"], "heatsink_rise_expected_k": k["rth"] * lm / n,
        "fan_speed_ratio": r["fan_speed_pct"] / max(r["fan_cmd_pct"], 1),
        "dc_ripple_ratio": r["dc_ripple_v"] / (k["rp0"] + (k["rp1"] - k["rp0"]) * p / n / k["upm"]),
        "batt_r_ratio": r["battery_r_max_mohm"] / k["r0"], "batt_block_w": bw,
        "autonomy_min": autonomy_min(k, p, r["battery_soh_pct"]),
        "batt_ageing_factor": 2 ** ((r["battery_temp_c"] - k["tref"]) / k["halv"]),
        "batt_life_remaining_y": k["life"] * 2 ** (-max(r["battery_temp_life_c"] - k["tref"], 0) / k["halv"]) - r["battery_age_days"] / 365,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    RR = p["RIP"]
    return [
        ("UPS_ON_BATTERY", "np.abs(df['UPS_MODE'] - 4) < 0.5", "High", None),
        ("UPS_ON_BYPASS", "np.abs(df['UPS_MODE'] - 3) < 0.5", "High", None),
        ("UPS_AUTONOMY_SHORT", f"{p['AUT']} < {k['req']}", "High", "battery_ageing"),
        ("UPS_REDUNDANCY_LOST", f"{p['MARG']} < 0", "High", "upm_failure"),
        ("UPS_DC_RIPPLE_LIMIT", f"{RR} > {L['ripple_ratio_limit']}", "High", "dc_capacitor_ageing"),
        ("UPS_MODULE_OFFLINE", f"df['UPM_ONLINE'] < {k['ninst'] - 0.5}", "Medium", "upm_failure"),
        ("UPS_PHASE_IMBALANCE", f"(3 * {p['IM']} / {p['IS']} - 1) * 100 > {L['imbalance_alert_pct']}", "Medium", "phase_load_growth"),
        ("UPS_DC_RIPPLE_HIGH", f"({RR} > {L['ripple_ratio_alert']}) & ({RR} <= {L['ripple_ratio_limit']})", "Medium", "dc_capacitor_ageing"),
        ("UPS_FAN_SLOW", f"df['FAN_SPEED_PCT'] / np.maximum(df['FAN_CMD_PCT'], 1) < {L['fan_ratio_alert']}", "Medium", "fan_wear"),
        ("UPS_HEATSINK_RISE_HIGH", f"({p['RISE']} - {p['RISEX']}) > {L['heatsink_residual_alert_k']}", "Medium", "fan_wear"),
        ("UPS_EFFICIENCY_LOW", f"(np.abs(df['UPS_MODE'] - 1) < 0.5) & ({p['LM']} / {p['LE']} > {L['loss_ratio_alert']})", "Medium", "converter_losses"),
        ("UPS_BATT_R_HIGH", f"df['BATTERY_R_MAX_MOHM'] / {k['r0']} > {L['batt_r_ratio_alert']}", "Medium", "battery_ageing"),
        ("UPS_BATT_SOH_LOW", f"df['BATTERY_SOH_PCT'] < {L['soh_alert_pct']}", "Medium", "battery_ageing"),
        ("UPS_BATT_TEMP_HIGH", f"df['BATTERY_TEMP_C'] > {L['batt_temp_alert_c']}", "Medium", "battery_room_hot"),
        ("UPS_BYPASS_EVENTS", f"df['BYPASS_EVENTS_30D'] > {L['bypass_events_alert']}", "Medium", "bypass_transfers"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    mode = r["ups_mode"]
    rr = t["dc_ripple_ratio"]
    res = t["heatsink_rise_k"] - t["heatsink_rise_expected_k"]
    add(abs(mode - 4) < 0.5, "UPS_ON_BATTERY", "High", f"On battery: {t['autonomy_min']:.0f} min left at {r['output_power_kw']:.0f} kW", "battery")
    add(abs(mode - 3) < 0.5, "UPS_ON_BYPASS", "High", "Load on static bypass: no protection from the mains", "bypass")
    add(t["autonomy_min"] < k["req"], "UPS_AUTONOMY_SHORT", "High",
        f"Battery autonomy {t['autonomy_min']:.1f} min at {r['output_power_kw']:.0f} kW, below the {k['req']:.0f} min required", "battery", "battery_ageing")
    add(t["redundancy_margin_kw"] < 0, "UPS_REDUNDANCY_LOST", "High",
        f"Not N+1: worst phase needs {3 * t['phase_max_kw']:.0f} kW, {round(max(r['upm_online'], 1)) - 1:.0f} modules give {(round(max(r['upm_online'], 1)) - 1) * k['upm']:.0f} kW",
        "load", "upm_failure")
    add(rr > L["ripple_ratio_limit"], "UPS_DC_RIPPLE_LIMIT", "High", f"DC-link ripple {r['dc_ripple_v']:.1f} V, {rr:.2f} x expected", "upm", "dc_capacitor_ageing")
    add(r["upm_online"] < k["ninst"] - 0.5, "UPS_MODULE_OFFLINE", "Medium", f"{r['upm_online']:.0f} of {k['ninst']} power modules online", "upm", "upm_failure")
    add(t["phase_imbalance_pct"] > L["imbalance_alert_pct"], "UPS_PHASE_IMBALANCE", "Medium",
        f"Phase imbalance {t['phase_imbalance_pct']:.1f} % (L1 {r['output_current_l1_a']:.0f} A, L2 {r['output_current_l2_a']:.0f} A, L3 {r['output_current_l3_a']:.0f} A)",
        "load", "phase_load_growth")
    add(L["ripple_ratio_alert"] < rr <= L["ripple_ratio_limit"], "UPS_DC_RIPPLE_HIGH", "Medium",
        f"DC-link ripple {r['dc_ripple_v']:.1f} V, {rr:.2f} x expected", "upm", "dc_capacitor_ageing")
    add(t["fan_speed_ratio"] < L["fan_ratio_alert"], "UPS_FAN_SLOW", "Medium",
        f"Slowest fan at {r['fan_speed_pct']:.0f} % for a command of {r['fan_cmd_pct']:.0f} %", "cooling", "fan_wear")
    add(res > L["heatsink_residual_alert_k"], "UPS_HEATSINK_RISE_HIGH", "Medium",
        f"Heatsink {t['heatsink_rise_k']:.1f} K above the inlet air, {res:.1f} K more than the losses explain", "cooling", "fan_wear")
    add(abs(mode - 1) < 0.5 and t["loss_ratio"] > L["loss_ratio_alert"], "UPS_EFFICIENCY_LOW", "Medium",
        f"Efficiency {t['eff_measured_pct']:.2f} % against {t['eff_expected_pct']:.2f} % on the curve: losses {t['loss_ratio']:.2f} x expected", "upm", "converter_losses")
    add(t["batt_r_ratio"] > L["batt_r_ratio_alert"], "UPS_BATT_R_HIGH", "Medium",
        f"Highest block resistance {r['battery_r_max_mohm']:.2f} mΩ, {t['batt_r_ratio']:.2f} x baseline", "battery", "battery_ageing")
    add(r["battery_soh_pct"] < L["soh_alert_pct"], "UPS_BATT_SOH_LOW", "Medium", f"Last capacity test {r['battery_soh_pct']:.0f} %: below {L['soh_alert_pct']:.0f} %",
        "battery", "battery_ageing")
    add(r["battery_temp_c"] > L["batt_temp_alert_c"], "UPS_BATT_TEMP_HIGH", "Medium",
        f"Battery at {r['battery_temp_c']:.1f} °C: ageing {t['batt_ageing_factor']:.1f} x as fast as at 25 °C", "battery", "battery_room_hot")
    add(r["bypass_events_30d"] > L["bypass_events_alert"], "UPS_BYPASS_EVENTS", "Medium",
        f"{r['bypass_events_30d']:.0f} transfers to static bypass in 30 days", "bypass", "bypass_transfers")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
