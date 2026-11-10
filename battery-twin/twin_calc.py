"""The substation DC battery twin's expectations (EnerSys PowerSafe OPzV 6 OPzV 420 x 54, 110 V DC).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (twin viewer, tests)

Model (EnerSys data + labelled assumptions in the twin file):
  float voltage per cell     Vpc = battery voltage / 54; expected = EnerSys compensation table at the battery temperature
                             (2.37 Vpc at -10 C ... 2.25 at 20 C ... 2.21 at 40 C, linear between points)
  float current              I_exp = 0.35 mA/Ah x C10 x 2^((T - 20)/10) x 2^((Vpc - 2.25)/0.025)   (typical VRLA, assumed)
  ohmic value                Ri_exp = 0.51 mOhm x (1 - 0.006 (T - 20)); ratio worst cell and mean vs. expected;
                             a weak cell is judged against the string mean (> 1.5x), an aged string against the baseline (mean > 1.3x)
  cell balance               largest deviation of a cell from the string mean, % (EnerSys: within +-4.5 % on float)
  ripple                     A per 100 Ah C10 (EnerSys: <= 5)
  ageing                     V = 2^((T - 20)/10)  (life halves per 10 K above 20 C; rule of thumb)
  backup time                SOC x C10 x capacity factor(T) x capacity estimate / load current
                             capacity factor from EnerSys (5-12 h): -10 C 0.60 ... 20 C 1.00 ... 40 C 1.07
                             capacity estimate = 1 - 0.65 (mean ohmic ratio - 1), clipped 0.3-1 (empirical, assumed)
  earth                      pole imbalance = (V+e + V-e) / (V+e - V-e) x 100; 0 % = balanced
Float checks apply only when the charger has AC and is in float mode; the thermal-runaway check also needs SOC >= 98 %.
"""
import numpy as np


def _k(twin):
    d = twin["design"]
    f, c, o = d["float"], d["cell"], d["ohmic"]
    return dict(n=d["string"]["cells"], c10=c["c10_ah"], ri=o["baseline_mohm"], tc=o["temp_coeff_per_k"],
                ft=f["table_c"], fv=f["table_vpc"], kf=f["float_current_ma_per_ah_20c"] / 1000.0,
                dk=f["float_current_doubling_k"], dmv=f["float_current_doubling_mv"] / 1000.0,
                ct=d["capacity_vs_temp"]["table_c"], cf=d["capacity_vs_temp"]["factor_5_12h"],
                cr=d["connection"]["baseline_mohm"], ak=d["ageing"]["doubling_k"], aref=d["ageing"]["ref_c"])


def _parts(twin):
    k = _k(twin)
    T = "df['BATTERY_TEMP_C']"
    VPC = f"(df['BATTERY_VOLTAGE_V'] / {k['n']})"
    VEXP = f"np.interp({T}, {k['ft']}, {k['fv']})"
    IEXP = f"({k['kf'] * k['c10']} * np.power(2.0, ({T} - 20) / {k['dk']}) * np.power(2.0, ({VPC} - 2.25) / {k['dmv']}))"
    RIE = f"({k['ri']} * (1 + {k['tc']} * ({T} - 20)))"
    MEAN = "df['CELL_V_MEAN'].clip(lower=0.1)"
    DEV = f"(np.maximum(df['CELL_V_MAX'] - df['CELL_V_MEAN'], df['CELL_V_MEAN'] - df['CELL_V_MIN']) / {MEAN} * 100)"
    RIM = f"(df['RI_MEAN_MOHM'] / {RIE})"
    CAPEST = f"(1 - 0.65 * ({RIM} - 1)).clip(lower=0.3, upper=1.0)"
    CAPT = f"np.interp({T}, {k['ct']}, {k['cf']})"
    AUT = f"(df['SOC_PCT'] / 100 * {k['c10']} * {CAPT} * {CAPEST} / df['LOAD_CURRENT_A'].clip(lower=1))"
    IMB = "((df['POS_EARTH_V'] + df['NEG_EARTH_V']) / (df['POS_EARTH_V'] - df['NEG_EARTH_V']).clip(lower=1) * 100)"
    FLOAT = "((df['CHARGER_AC_ON'] == 1) & (df['CHARGER_MODE'] == 0))"
    return dict(T=T, VPC=VPC, VEXP=VEXP, IEXP=IEXP, RIE=RIE, DEV=DEV, RIM=RIM, CAPEST=CAPEST, CAPT=CAPT, AUT=AUT, IMB=IMB, FLOAT=FLOAT, k=k)


def monitor_expressions(twin):
    p, k = _parts(twin), _k(twin)
    return [
        ("FLOAT_VPC", p["VPC"]),
        ("FLOAT_VPC_EXPECTED", p["VEXP"]),
        ("FLOAT_V_RESIDUAL_MV", f"({p['VPC']} - {p['VEXP']}) * 1000"),
        ("FLOAT_CURRENT_EXPECTED_A", p["IEXP"]),
        ("FLOAT_CURRENT_RATIO", f"df['BATTERY_CURRENT_A'] / {p['IEXP']}"),
        ("BATTERY_TEMP_RISE_K", "df['BATTERY_TEMP_C'] - df['ROOM_TEMP_C']"),
        ("CELL_DEV_MAX_PCT", p["DEV"]),
        ("RI_EXPECTED_MOHM", p["RIE"]),
        ("RI_RATIO_MAX", f"df['RI_MAX_MOHM'] / {p['RIE']}"),
        ("RI_RATIO_MEAN", p["RIM"]),
        ("RI_MAX_VS_MEAN", "df['RI_MAX_MOHM'] / df['RI_MEAN_MOHM'].clip(lower=0.001)"),
        ("CONN_R_RATIO", f"df['CONN_R_MAX_MOHM'] / {k['cr']}"),
        ("CONN_TEMP_RISE_K", "df['CONN_TEMP_MAX_C'] - df['BATTERY_TEMP_C']"),
        ("RIPPLE_PER_100AH", f"df['RIPPLE_CURRENT_A'] / {k['c10']} * 100"),
        ("POLE_IMBALANCE_PCT", p["IMB"]),
        ("AGEING_RATE_V", f"np.power(2.0, ({p['T']} - {k['aref']}) / {k['ak']})"),
        ("CAPACITY_FACTOR_T", p["CAPT"]),
        ("CAPACITY_EST_PCT", f"{p['CAPEST']} * 100"),
        ("AUTONOMY_H", p["AUT"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    T = r["battery_temp_c"]
    vpc = r["battery_voltage_v"] / k["n"]
    vexp = float(np.interp(T, k["ft"], k["fv"]))
    iexp = k["kf"] * k["c10"] * 2.0 ** ((T - 20) / k["dk"]) * 2.0 ** ((vpc - 2.25) / k["dmv"])
    rie = k["ri"] * (1 + k["tc"] * (T - 20))
    mean = max(r["cell_v_mean"], 0.1)
    dev = max(r["cell_v_max"] - r["cell_v_mean"], r["cell_v_mean"] - r["cell_v_min"]) / mean * 100
    rim = r["ri_mean_mohm"] / rie
    capest = min(1.0, max(0.3, 1 - 0.65 * (rim - 1)))
    capt = float(np.interp(T, k["ct"], k["cf"]))
    aut = r["soc_pct"] / 100 * k["c10"] * capt * capest / max(r["load_current_a"], 1)
    imb = (r["pos_earth_v"] + r["neg_earth_v"]) / max(r["pos_earth_v"] - r["neg_earth_v"], 1) * 100
    return {
        "float_vpc": vpc, "float_vpc_expected": vexp, "float_v_residual_mv": (vpc - vexp) * 1000,
        "float_current_expected_a": iexp, "float_current_ratio": r["battery_current_a"] / iexp,
        "battery_temp_rise_k": T - r["room_temp_c"], "cell_dev_max_pct": dev,
        "ri_expected_mohm": rie, "ri_ratio_max": r["ri_max_mohm"] / rie, "ri_ratio_mean": rim,
        "ri_max_vs_mean": r["ri_max_mohm"] / max(r["ri_mean_mohm"], 0.001),
        "conn_r_ratio": r["conn_r_max_mohm"] / k["cr"], "conn_temp_rise_k": r["conn_temp_max_c"] - T,
        "ripple_per_100ah": r["ripple_current_a"] / k["c10"] * 100, "pole_imbalance_pct": imb,
        "ageing_rate_v": 2.0 ** ((T - k["aref"]) / k["ak"]), "capacity_factor_t": capt,
        "capacity_est_pct": capest * 100, "autonomy_h": aut,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    F = p["FLOAT"]
    RES = f"(({p['VPC']} - {p['VEXP']}) * 1000)"
    RAT = f"(df['BATTERY_CURRENT_A'] / {p['IEXP']})"
    RIX = f"(df['RI_MAX_MOHM'] / {p['RIE']})"
    RVM = "(df['RI_MAX_MOHM'] / df['RI_MEAN_MOHM'].clip(lower=0.001))"
    return [
        ("BAT_THERMAL_RUNAWAY", f"{F} & (df['SOC_PCT'] >= 98) & ({RAT} > {L['float_current_ratio_alert']}) & ((df['BATTERY_TEMP_C'] - df['ROOM_TEMP_C']) > {L['temp_rise_alert_k']})", "Critical", "thermal_runaway"),
        ("BAT_FLOAT_VOLTAGE", f"{F} & ({RES}.abs() > {L['float_v_residual_alert_mv']})", "Medium", "float_setting"),
        ("BAT_CELL_IMBALANCE", f"{F} & ({p['DEV']} > {L['cell_dev_alert_pct']})", "Medium", "weak_cell"),
        ("BAT_WEAK_CELL", f"{RVM} > {L['ri_act_ratio']}", "High", "weak_cell"),
        ("BAT_CELL_RI_HIGH", f"({RIX} > {L['ri_warn_ratio']}) & ({RVM} <= {L['ri_act_ratio']})", "Low", None),
        ("BAT_LOOSE_CONNECTION", f"((df['CONN_R_MAX_MOHM'] / {k['cr']}) > {L['conn_ratio_alert']}) | ((df['CONN_TEMP_MAX_C'] - df['BATTERY_TEMP_C']) > {L['conn_temp_rise_alert_k']})", "High", "loose_connection"),
        ("BAT_RIPPLE_HIGH", f"(df['RIPPLE_CURRENT_A'] / {k['c10']} * 100) > {L['ripple_alert_a_per_100ah']}", "Medium", "charger_ripple"),
        ("BAT_EARTH_FAULT", f"(df['INSULATION_KOHM'] < {L['insulation_alert_kohm']}) | ({p['IMB']}.abs() > {L['imbalance_alert_pct']})", "High", "ground_fault"),
        ("BAT_ROOM_HOT", f"df['ROOM_TEMP_C'] > {L['room_temp_alert_c']}", "Medium", "ventilation_failure"),
        ("BAT_TEMP_HIGH", f"df['BATTERY_TEMP_C'] > {L['battery_temp_alert_c']}", "High", "ventilation_failure"),
        ("BAT_CAPACITY_LOW", f"({p['RIM']} > {L['ri_mean_alert_ratio']}) | ({p['AUT']} < {L['autonomy_alert_h']})", "High", "capacity_fade"),
        ("BAT_LOW_VOLTAGE", f"({p['VPC']} < {L['low_voltage_vpc']})", "High", None),
        ("BAT_ON_BATTERY", "df['CHARGER_AC_ON'] == 0", "Low", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    fl = r["charger_ac_on"] == 1 and r["charger_mode"] == 0
    add(fl and r["soc_pct"] >= 98 and t["float_current_ratio"] > L["float_current_ratio_alert"] and t["battery_temp_rise_k"] > L["temp_rise_alert_k"],
        "BAT_THERMAL_RUNAWAY", "Critical", f"Float current {r['battery_current_a']:.2f} A = {t['float_current_ratio']:.1f}x expected, battery {t['battery_temp_rise_k']:.1f} K above the room",
        "cells", "thermal_runaway")
    add(fl and abs(t["float_v_residual_mv"]) > L["float_v_residual_alert_mv"], "BAT_FLOAT_VOLTAGE", "Medium",
        f"Float {t['float_vpc']:.3f} V/cell vs. EnerSys {t['float_vpc_expected']:.3f} at {r['battery_temp_c']:.1f} °C ({t['float_v_residual_mv']:+.0f} mV/cell)", "charger", "float_setting")
    add(fl and t["cell_dev_max_pct"] > L["cell_dev_alert_pct"], "BAT_CELL_IMBALANCE", "Medium",
        f"Cell {int(r['cell_v_worst_no'])} deviates {t['cell_dev_max_pct']:.1f} % from the string mean (limit ±4.5 %)", "cells", "weak_cell")
    add(t["ri_max_vs_mean"] > L["ri_act_ratio"], "BAT_WEAK_CELL", "High",
        f"Cell {int(r['ri_max_no'])} ohmic value {r['ri_max_mohm']:.3f} mΩ = {t['ri_max_vs_mean']:.2f}x the string mean ({t['ri_ratio_max']:.2f}x baseline)", "cells", "weak_cell")
    add(t["ri_ratio_max"] > L["ri_warn_ratio"] and t["ri_max_vs_mean"] <= L["ri_act_ratio"], "BAT_CELL_RI_HIGH", "Low",
        f"Ohmic values above baseline: worst cell {int(r['ri_max_no'])} at {t['ri_ratio_max']:.2f}x (investigate > {L['ri_warn_ratio']})", "cells")
    add(t["conn_r_ratio"] > L["conn_ratio_alert"] or t["conn_temp_rise_k"] > L["conn_temp_rise_alert_k"], "BAT_LOOSE_CONNECTION", "High",
        f"Intercell connection {r['conn_r_max_mohm']:.2f} mΩ ({t['conn_r_ratio']:.0f}x), connector {t['conn_temp_rise_k']:+.1f} K above the cells", "connector", "loose_connection")
    add(t["ripple_per_100ah"] > L["ripple_alert_a_per_100ah"], "BAT_RIPPLE_HIGH", "Medium",
        f"Ripple {r['ripple_current_a']:.1f} A = {t['ripple_per_100ah']:.1f} A/100 Ah (EnerSys limit 5)", "charger", "charger_ripple")
    add(r["insulation_kohm"] < L["insulation_alert_kohm"] or abs(t["pole_imbalance_pct"]) > L["imbalance_alert_pct"], "BAT_EARTH_FAULT", "High",
        f"Insulation {r['insulation_kohm']:.0f} kΩ, +pole {r['pos_earth_v']:.1f} V / −pole {r['neg_earth_v']:.1f} V to earth ({t['pole_imbalance_pct']:+.0f} %)", "dcboard", "ground_fault")
    add(r["room_temp_c"] > L["room_temp_alert_c"], "BAT_ROOM_HOT", "Medium", f"Battery room {r['room_temp_c']:.1f} °C (best ≤ 30 °C)", "room", "ventilation_failure")
    add(r["battery_temp_c"] > L["battery_temp_alert_c"], "BAT_TEMP_HIGH", "High",
        f"Battery {r['battery_temp_c']:.1f} °C: ageing x{t['ageing_rate_v']:.1f}", "cells", "ventilation_failure")
    add(t["ri_ratio_mean"] > L["ri_mean_alert_ratio"] or t["autonomy_h"] < L["autonomy_alert_h"], "BAT_CAPACITY_LOW", "High",
        f"Estimated capacity {t['capacity_est_pct']:.0f} %, backup time {t['autonomy_h']:.1f} h (required {L['autonomy_alert_h']:.0f} h)", "cells", "capacity_fade")
    add(t["float_vpc"] < L["low_voltage_vpc"], "BAT_LOW_VOLTAGE", "High", f"Battery {t['float_vpc']:.3f} V/cell (alarm < {L['low_voltage_vpc']})", "cells")
    add(r["charger_ac_on"] == 0, "BAT_ON_BATTERY", "Low", f"Charger AC supply lost: battery carries {r['load_current_a']:.1f} A, SOC {r['soc_pct']:.0f} %", "charger")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
