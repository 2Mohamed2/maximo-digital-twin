"""The sewage lift station twin's expectations (LS-5201: wet well + 2 x Flygt NP 3153 duty/standby + rising main).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Levels are metres above the wet-well floor; flows in l/s; A is the wet-well plan area (m2). A rate of 1 mm/min in a well
of A m2 is A / 60 l/s.

Wet well as a flowmeter (mass balance, one reading):
    inflow           = A x level rate / 60 + rising main flow
    time to spill    = A x (spill level - level) / (inflow - station capacity)   only when the inflow is above what both
                       pumps can pump (station capacity Q2, from the pump and system curves at the design level)
Drawdown test (logged by the PLC for each pump cycle; inflow taken as constant during the run):
    pump flow        = A x (fall rate during the run + rise rate before the start) / 60
    pump head        = p x 10^5 / (rho g) + z_gauge - level            (velocity head neglected)
    expected flow    = Q0 x sqrt((H0 - H) / (H0 - Hd))                 (curve H = H0 - (H0 - Hd) (Q / Q0)^2)
    expected power   = rho g Q H / (eta x eta_motor), eta = eta0 (2x - x^2), x = Q / Q0, at the expected flow for this
                       head; written as rho g Q0 H / (eta0 eta_motor (2 - x)) so it stays finite near shut-off
    flow ratio < 1 and power ratio > 1 at the same head = ragging; flow ratio < 1 and power ratio <= 1 = wear
Rising main: friction head = p x 10^5 / (rho g) - (z_out - z_gauge) (the well level cancels); resistance ratio =
    friction / (k0 Q^2), k0 from the duty point at the design level. Velocity = Q / pipe area.
Check valve: backflow = A x (rise rate after the stop - rise rate before the start) / 60;
    reverse velocity at closure (Joukowsky) v = (peak pressure - static pressure) x 10^5 / (rho a).
Pump inlet (ANSI/HI 9.8): S min = D (1 + 2.3 F_D), F_D = V / sqrt(g D), V = Q0 / (pi D^2 / 4); margin = (level - z_inlet) / S min.
Duty: starts in the last hour (max of the two pumps), run-hour imbalance |h1 - h2| / (h1 + h2) over 7 days.
"""
import math


def _k(twin):
    d = twin["design"]
    p, w, m, i = d["pump"], d["well"], d["main"], d["inflow"]
    g, rho = 9.81, m["rho_kg_m3"]
    area = math.pi * w["diameter_m"] ** 2 / 4
    qd, hd, h0 = p["duty_flow_ls"], p["duty_head_m"], p["shutoff_head_m"]
    a = h0 - hd
    lref = (w["stop_m"] + w["start_m"]) / 2
    k0 = (hd - (m["outlet_z_m"] - lref)) / qd ** 2
    q_par = math.sqrt((h0 - (m["outlet_z_m"] - lref)) / (a / qd ** 2 + 4 * k0))      # per pump, two in parallel
    din = p["inlet_d_m"]
    v_in = qd / 1000 / (math.pi * din ** 2 / 4)
    fd = v_in / math.sqrt(g * din)
    pcoef = 1e5 / (rho * g)
    return dict(area=area, a60=area / 60, vfac=area * 1000 / 60, qd=qd, hd=hd, h0=h0, a=a, eta0=p["eta_bep"], etam=p["motor_eff"],
                pc=rho * g / 1e6, pcoef=pcoef, zo=m["outlet_z_m"], zg=m["gauge_z_m"], am=math.pi * m["inner_d_m"] ** 2 / 4,
                k0=k0, lref=lref, q2=2 * q_par, static_bar=(m["outlet_z_m"] - m["gauge_z_m"]) / pcoef, jk=rho * m["wave_speed_ms"] / 1e5,
                din=din, zin=p["inlet_z_m"], v_in=v_in, fd=fd, sreq=din * (1 + 2.3 * fd),
                stop=w["stop_m"], start=w["start_m"], start2=w["start2_m"], high=w["high_m"], spill=w["spill_m"],
                dry=i["dry_avg_ls"], amp=i["dry_amp_ls"], storm=i["storm_ls"], maxstarts=p["maker"]["max_starts_h"])


def head_curve(k, q):
    return k["h0"] - k["a"] * (q / k["qd"]) ** 2


def power_exp(k, h):
    """Input power (kW) of a clean pump on its curve at head h."""
    x = math.sqrt(max(k["h0"] - h, 0) / k["a"])
    return k["pc"] * k["qd"] * h / (k["eta0"] * k["etam"] * (2 - x))


def _parts(twin):
    k = _k(twin)
    LV, CL = "df['LEVEL_M']", "df['CYC_LEVEL_M']"
    INF = f"({k['a60']:.10g} * df['LEVEL_RATE_MM_MIN'] + df['MAIN_FLOW_LS'])"
    EXC = f"({INF} - {k['q2']:.10g})"
    TTS = (f"np.where({EXC} > 0.1, np.minimum({k['vfac']:.10g} * np.maximum({k['spill']} - {LV}, 0) / np.maximum({EXC}, 0.1), 999), 999)")
    QV = f"({k['a60']:.10g} * (df['CYC_DRAW_MM_MIN'] + df['CYC_FILL_MM_MIN']))"
    HM = f"(df['CYC_DISCHARGE_BAR'] * {k['pcoef']:.10g} + {k['zg']} - {CL})"
    X = f"np.sqrt(np.maximum({k['h0']} - {HM}, 0) / {k['a']})"
    QE = f"({k['qd']} * {X})"
    FR = f"({QV} / np.maximum({QE}, 1))"
    PE = f"({k['pc'] * k['qd'] / (k['eta0'] * k['etam']):.10g} * {HM} / (2 - {X}))"
    PR = f"(df['CYC_POWER_KW'] / {PE})"
    RR = f"((df['CYC_DISCHARGE_BAR'] * {k['pcoef']:.10g} - {k['zo'] - k['zg']:.10g}) / ({k['k0']:.10g} * np.maximum({QV}, 1) ** 2))"
    BF = f"({k['a60']:.10g} * (df['CYC_AFTER_STOP_MM_MIN'] - df['CYC_FILL_MM_MIN']))"
    RV = f"((df['CYC_STOP_PEAK_BAR'] - {k['static_bar']:.10g}) / {k['jk']:.10g})"
    ST = "np.maximum(df['P1_STARTS_1H'], df['P2_STARTS_1H'])"
    IMB = "(np.abs(df['P1_RUN_H_7D'] - df['P2_RUN_H_7D']) / np.maximum(df['P1_RUN_H_7D'] + df['P2_RUN_H_7D'], 1))"
    VEL = f"({QV} / {k['am'] * 1000:.10g})"
    SM = f"(({LV} - {k['zin']}) / {k['sreq']:.10g})"
    return dict(k=k, LV=LV, INF=INF, EXC=EXC, TTS=TTS, QV=QV, HM=HM, X=X, QE=QE, FR=FR, PE=PE, PR=PR, RR=RR, BF=BF, RV=RV, ST=ST,
                IMB=IMB, VEL=VEL, SM=SM)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("INFLOW_LS", p["INF"]),
        ("INFLOW_RATIO", f"{p['INF']} / {k['qd']}"),
        ("FREEBOARD_M", f"{k['spill']} - {p['LV']}"),
        ("TIME_TO_SPILL_MIN", p["TTS"]),
        ("CYCLE_INFLOW_LS", f"{k['a60']:.10g} * df['CYC_FILL_MM_MIN']"),
        ("PUMP_FLOW_VOL_LS", p["QV"]),
        ("PUMP_HEAD_M", p["HM"]),
        ("PUMP_FLOW_EXPECTED_LS", p["QE"]),
        ("PUMP_FLOW_RATIO", p["FR"]),
        ("PUMP_POWER_EXPECTED_KW", p["PE"]),
        ("PUMP_POWER_RATIO", p["PR"]),
        ("SPECIFIC_ENERGY_KWH_M3", f"df['CYC_POWER_KW'] / (np.maximum({p['QV']}, 1) * 3.6)"),
        ("MAIN_RESISTANCE_RATIO", p["RR"]),
        ("MAIN_VELOCITY_MS", p["VEL"]),
        ("BACKFLOW_LS", p["BF"]),
        ("REVERSE_VELOCITY_MS", p["RV"]),
        ("STARTS_MAX_1H", p["ST"]),
        ("RUN_IMBALANCE", p["IMB"]),
        ("SUBMERGENCE_MARGIN", p["SM"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    lv = r["level_m"]
    inf = k["a60"] * r["level_rate_mm_min"] + r["main_flow_ls"]
    exc = inf - k["q2"]
    tts = min(k["vfac"] * max(k["spill"] - lv, 0) / max(exc, 0.1), 999) if exc > 0.1 else 999
    qv = k["a60"] * (r["cyc_draw_mm_min"] + r["cyc_fill_mm_min"])
    hm = r["cyc_discharge_bar"] * k["pcoef"] + k["zg"] - r["cyc_level_m"]
    x = math.sqrt(max(k["h0"] - hm, 0) / k["a"])
    qe = k["qd"] * x
    pe = k["pc"] * k["qd"] / (k["eta0"] * k["etam"]) * hm / (2 - x)
    return {
        "inflow_ls": inf, "inflow_ratio": inf / k["qd"], "freeboard_m": k["spill"] - lv, "time_to_spill_min": tts,
        "cycle_inflow_ls": k["a60"] * r["cyc_fill_mm_min"],
        "pump_flow_vol_ls": qv, "pump_head_m": hm, "pump_flow_expected_ls": qe, "pump_flow_ratio": qv / max(qe, 1),
        "pump_power_expected_kw": pe, "pump_power_ratio": r["cyc_power_kw"] / pe,
        "specific_energy_kwh_m3": r["cyc_power_kw"] / (max(qv, 1) * 3.6),
        "main_resistance_ratio": (r["cyc_discharge_bar"] * k["pcoef"] - (k["zo"] - k["zg"])) / (k["k0"] * max(qv, 1) ** 2),
        "main_velocity_ms": qv / (k["am"] * 1000),
        "backflow_ls": k["a60"] * (r["cyc_after_stop_mm_min"] - r["cyc_fill_mm_min"]),
        "reverse_velocity_ms": (r["cyc_stop_peak_bar"] - k["static_bar"]) / k["jk"],
        "starts_max_1h": max(r["p1_starts_1h"], r["p2_starts_1h"]),
        "run_imbalance": abs(r["p1_run_h_7d"] - r["p2_run_h_7d"]) / max(r["p1_run_h_7d"] + r["p2_run_h_7d"], 1),
        "submergence_margin": (lv - k["zin"]) / k["sreq"],
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    LV, FR, PR = p["LV"], p["FR"], p["PR"]
    m = L["level_mismatch_m"]
    return [
        ("LS_SPILL_RISK", f"{p['TTS']} < {L['spill_time_alert_min']}", "Critical", "storm_inflow"),
        ("LS_LEVEL_HIGH", f"{LV} > {k['high']}", "High", "storm_inflow"),
        ("LS_LEVEL_SENSOR_MISMATCH", f"((df['FLOAT_HIGH'] > 0.5) & ({LV} < {k['high'] - m:.10g})) | ((df['FLOAT_HIGH'] < 0.5) & ({LV} > {k['high'] + m:.10g}))",
         "High", "level_sensor_fault"),
        ("LS_RAGGING", f"({FR} < {L['flow_ratio_alert']}) & ({PR} > {L['power_ratio_rag']})", "High", "impeller_ragging"),
        ("LS_MAIN_RESISTANCE_HIGH", f"{p['RR']} > {L['resistance_ratio_alert']}", "High", "main_restriction"),
        ("LS_SUBMERGENCE_LOW", f"{p['SM']} < {L['submergence_margin_min']}", "High", None),
        ("LS_INFLOW_ABOVE_CAPACITY", f"({p['INF']} / {k['qd']}) > {L['inflow_ratio_alert']}", "Medium", "storm_inflow"),
        ("LS_PUMP_FLOW_LOW", f"{FR} < {L['flow_ratio_alert']}", "Medium", "impeller_ragging"),
        ("LS_PUMP_WEAR", f"({FR} < {L['flow_ratio_alert']}) & ({PR} <= {L['power_ratio_rag']})", "Medium", "impeller_wear"),
        ("LS_CHECK_VALVE_PASSING", f"{p['BF']} > {L['backflow_alert_ls']}", "Medium", "check_valve_passing"),
        ("LS_CHECK_VALVE_SLAM", f"{p['RV']} > {L['reverse_velocity_alert_ms']}", "Medium", "check_valve_slam"),
        ("LS_SEAL_LEAK", "(df['P1_LEAK'] > 0.5) | (df['P2_LEAK'] > 0.5)", "Medium", "seal_leak"),
        ("LS_STARTS_HIGH", f"{p['ST']} > {L['starts_alert_h']}", "Medium", None),
        ("LS_ALTERNATION_IMBALANCE", f"{p['IMB']} > {L['imbalance_alert']}", "Low", None),
        ("LS_MAIN_VELOCITY_LOW", f"{p['VEL']} < {L['velocity_min_ms']}", "Low", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    m = L["level_mismatch_m"]
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    lv, fr, pr = r["level_m"], t["pump_flow_ratio"], t["pump_power_ratio"]
    add(t["time_to_spill_min"] < L["spill_time_alert_min"], "LS_SPILL_RISK", "Critical",
        f"Inflow {t['inflow_ls']:.0f} l/s is above what both pumps can lift: the well spills in {t['time_to_spill_min']:.0f} min", "wet well", "storm_inflow")
    add(lv > k["high"], "LS_LEVEL_HIGH", "High", f"Wet-well level {lv:.2f} m, above the high level {k['high']} m", "wet well", "storm_inflow")
    add((r["float_high"] > 0.5 and lv < k["high"] - m) or (r["float_high"] < 0.5 and lv > k["high"] + m), "LS_LEVEL_SENSOR_MISMATCH", "High",
        f"Backup float {'tripped' if r['float_high'] > 0.5 else 'not tripped'} while the radar reads {lv:.2f} m", "instrument", "level_sensor_fault")
    add(fr < L["flow_ratio_alert"] and pr > L["power_ratio_rag"], "LS_RAGGING", "High",
        f"Pump {r['cyc_pump']:.0f}: {fr * 100:.0f} % of the curve flow at {pr * 100:.0f} % of the clean power for this head: rags on the impeller", "pump", "impeller_ragging")
    add(t["main_resistance_ratio"] > L["resistance_ratio_alert"], "LS_MAIN_RESISTANCE_HIGH", "High",
        f"Rising main resistance {t['main_resistance_ratio']:.1f} x design: partial blockage or air pocket", "rising main", "main_restriction")
    add(t["submergence_margin"] < L["submergence_margin_min"], "LS_SUBMERGENCE_LOW", "High",
        f"Level {lv:.2f} m leaves the pump inlet {t['submergence_margin']:.2f} x the ANSI/HI 9.8 minimum submergence", "wet well")
    add(t["inflow_ratio"] > L["inflow_ratio_alert"], "LS_INFLOW_ABOVE_CAPACITY", "Medium",
        f"Inflow {t['inflow_ls']:.0f} l/s, {t['inflow_ratio']:.2f} x the firm capacity of one pump", "catchment", "storm_inflow")
    add(fr < L["flow_ratio_alert"], "LS_PUMP_FLOW_LOW", "Medium",
        f"Pump {r['cyc_pump']:.0f} drew down {t['pump_flow_vol_ls']:.1f} l/s, {fr * 100:.0f} % of the curve at {t['pump_head_m']:.1f} m", "pump", "impeller_ragging")
    add(fr < L["flow_ratio_alert"] and pr <= L["power_ratio_rag"], "LS_PUMP_WEAR", "Medium",
        f"Pump {r['cyc_pump']:.0f}: flow {fr * 100:.0f} % of the curve with normal power: impeller or insert ring wear", "pump", "impeller_wear")
    add(t["backflow_ls"] > L["backflow_alert_ls"], "LS_CHECK_VALVE_PASSING", "Medium",
        f"About {t['backflow_ls']:.1f} l/s flows back from the main after the stop", "check valve", "check_valve_passing")
    add(t["reverse_velocity_ms"] > L["reverse_velocity_alert_ms"], "LS_CHECK_VALVE_SLAM", "Medium",
        f"Stop peak {r['cyc_stop_peak_bar']:.2f} bar: the valve closed against {t['reverse_velocity_ms']:.2f} m/s of reverse flow", "check valve", "check_valve_slam")
    add(r["p1_leak"] > 0.5 or r["p2_leak"] > 0.5, "LS_SEAL_LEAK", "Medium",
        f"Leakage sensor FLS 10 tripped on {'P1' if r['p1_leak'] > 0.5 else 'P2'}: water in the inspection chamber", "pump", "seal_leak")
    add(t["starts_max_1h"] > L["starts_alert_h"], "LS_STARTS_HIGH", "Medium",
        f"{t['starts_max_1h']:.0f} starts in the last hour (pump allows {k['maxstarts']})", "pump")
    add(t["run_imbalance"] > L["imbalance_alert"], "LS_ALTERNATION_IMBALANCE", "Low",
        f"Run hours P1 {r['p1_run_h_7d']:.0f} h / P2 {r['p2_run_h_7d']:.0f} h over 7 days: duty is not alternating", "control")
    add(t["main_velocity_ms"] < L["velocity_min_ms"], "LS_MAIN_VELOCITY_LOW", "Low",
        f"Rising main velocity {t['main_velocity_ms']:.2f} m/s, below the self-cleansing {L['velocity_min_ms']} m/s", "rising main")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
