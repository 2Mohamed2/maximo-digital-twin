"""The control valve twin's expectations from KSB data (BOA-CVE IMS DN 100 PN 16, Kvs 200, EA-C 40 actuator).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (twin viewer, tests)

Valve model (IEC 60534-2-1 for incompressible flow, water):
  Q = Kv * sqrt(dp / (rho/1000))            Kv in m3/h, dp in bar
  Kv_expected = Kvs * f(h), f linear (KSB standard characteristic), h = position feedback
  Kv_measured = Q / sqrt(p1 - p2)            the valve's own flow coefficient, measured live
  sigma = (p1 - pv) / (p1 - p2)              cavitation index (ISA-RP75.23); pv from the fluid temperature
Actuator: expected stem force = packing friction + unbalanced plug load (dp x seat area), as % of 4.5 kN.
"""
import math

RHO = 1.0          # relative density of chilled water (rho/1000)


def pv_bar(t):
    """vapour pressure of water, bar(a) (Magnus, Alduchov-Eskridge)."""
    return 0.61094 * math.exp(17.625 * t / (t + 243.04)) / 100.0


def _k(twin):
    d = twin["design"]
    v, a = d["valve"], d["actuator"]
    return dict(kvs=v["kvs_m3h"], leak=v["leakage_pct_kvs"] / 100.0, area=v["seat_area_m2"], fmax=a["force_n"],
                fric=a["packing_friction_n"], sig_i=d["cavitation"]["sigma_incipient"], sig_d=d["cavitation"]["sigma_damage"],
                kv_str=d["strainer"]["kv_clean_m3h"])


def _parts(twin):
    k = _k(twin)
    P1, P2, P0 = "df['VALVE_INLET_PRESSURE_BAR']", "df['VALVE_OUTLET_PRESSURE_BAR']", "df['INLET_PRESSURE_BAR']"
    DP = f"({P1} - {P2}).clip(lower=0.005)"
    H = "(df['POSITION_PCT'].clip(lower=0) / 100)"
    KVM = f"(df['FLOW_M3H'] / np.sqrt({DP} / {RHO}))"
    KVE = f"({k['kvs']} * np.maximum({H}, {k['leak']}))"
    T = "df['FLUID_TEMP_C']"
    PV = f"(0.61094 * np.exp(17.625 * {T} / ({T} + 243.04)) / 100)"
    SIG = f"(({P1} - {PV}) / {DP})"
    FE = f"(({k['fric']} + {DP} * 1e5 * {k['area']}) / {k['fmax']} * 100)"
    KVS = f"(df['FLOW_M3H'] / np.sqrt(df['STRAINER_DP_BAR'].clip(lower=0.0002) / {RHO}))"
    return dict(KVM=KVM, KVE=KVE, SIG=SIG, FE=FE, KVS=KVS, H=H, k=k)


def monitor_expressions(twin):
    p = _parts(twin)
    return [
        ("KV_MEASURED", p["KVM"]),
        ("KV_EXPECTED", p["KVE"]),
        ("KV_RATIO", f"{p['KVM']} / {p['KVE']}"),
        ("SIGMA", p["SIG"]),
        ("POSITION_ERROR_PCT", "df['POSITION_CMD_PCT'] - df['POSITION_PCT']"),
        ("FLOW_ERROR_PCT", "(df['FLOW_M3H'] - df['FLOW_SETPOINT_M3H']) / df['FLOW_SETPOINT_M3H'].clip(lower=1) * 100"),
        ("FORCE_EXPECTED_PCT", p["FE"]),
        ("FORCE_DEVIATION_PCT", f"df['ACTUATOR_FORCE_PCT'] - {p['FE']}"),
        ("STRAINER_KV_RATIO", f"{p['KVS']} / {p['k']['kv_str']}"),
        ("VALVE_AUTHORITY", "(df['VALVE_INLET_PRESSURE_BAR'] - df['VALVE_OUTLET_PRESSURE_BAR']) / (df['INLET_PRESSURE_BAR'] - df['RETURN_PRESSURE_BAR']).clip(lower=0.01)"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    dp = max(r["valve_inlet_pressure_bar"] - r["valve_outlet_pressure_bar"], 0.005)
    h = max(r["position_pct"], 0) / 100
    kvm = r["flow_m3h"] / math.sqrt(dp / RHO)
    kve = k["kvs"] * max(h, k["leak"])
    sig = (r["valve_inlet_pressure_bar"] - pv_bar(r["fluid_temp_c"])) / dp
    fe = (k["fric"] + dp * 1e5 * k["area"]) / k["fmax"] * 100
    kvs = r["flow_m3h"] / math.sqrt(max(r["strainer_dp_bar"], 0.0002) / RHO)
    return {
        "kv_measured": kvm, "kv_expected": kve, "kv_ratio": kvm / kve, "sigma": sig,
        "position_error_pct": r["position_cmd_pct"] - r["position_pct"],
        "flow_error_pct": (r["flow_m3h"] - r["flow_setpoint_m3h"]) / max(r["flow_setpoint_m3h"], 1) * 100,
        "force_expected_pct": fe, "force_deviation_pct": r["actuator_force_pct"] - fe,
        "strainer_kv_ratio": kvs / k["kv_str"],
        "valve_authority": dp / max(r["inlet_pressure_bar"] - r["return_pressure_bar"], 0.01),
        "valve_dp_bar": dp,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    open_ = f"({p['H']} > {L['kv_check_min_open']})"
    ratio = f"({p['KVM']} / {p['KVE']})"
    return [
        ("FCV_SEAT_PLUG_WEAR", f"({p['H']} > {L['kv_wear_min_open']}) & ({p['H']} < 0.5) & ({ratio} > {L['kv_ratio_high']})", "Medium", "seat_plug_wear"),
        ("FCV_KV_LOW", f"{open_} & ({ratio} < {L['kv_ratio_low']}) & (df['POSITION_CMD_PCT'] < 99)", "Medium", "position_sensor_drift"),
        ("FCV_CAVITATION", f"({p['H']} > 0.02) & ({p['SIG']} < {k['sig_d']})", "High", "seat_plug_wear"),
        ("FCV_CAVITATION_INCIPIENT", f"({p['H']} > 0.02) & ({p['SIG']} < {k['sig_i']}) & ({p['SIG']} >= {k['sig_d']})", "Low", None),
        ("FCV_STICTION", f"(df['ACTUATOR_FORCE_PCT'] - {p['FE']} > {L['force_dev_alert_pct']}) & (df['ACTUATOR_FORCE_PCT'] <= {L['force_alert_pct']})", "Medium", "stiction"),
        ("FCV_ACTUATOR_OVERLOAD", f"(df['ACTUATOR_TEMP_C'] > {L['actuator_temp_alert_c']}) | (df['ACTUATOR_FORCE_PCT'] > {L['force_alert_pct']})", "High", "actuator_fault"),
        ("FCV_GLAND_LEAK", f"df['GLAND_LEAK_ML_MIN'] > {L['gland_leak_alert_ml_min']}", "Medium", "gland_leak"),
        ("FCV_STRAINER_BLOCKED", f"({p['KVS']} / {k['kv_str']}) < {L['strainer_kv_ratio_alert']}", "Medium", "strainer_blockage"),
        ("FCV_SATURATED", f"(df['POSITION_CMD_PCT'] > 98) & ((df['FLOW_M3H'] - df['FLOW_SETPOINT_M3H']) / df['FLOW_SETPOINT_M3H'].clip(lower=1) * 100 < -{L['flow_error_alert_pct']})", "Medium", None),
        ("FCV_FAULT", "df['FAULT_CODE'] > 0", "Critical", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    h = r["position_pct"] / 100
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    add(r.get("fault_code", 0) > 0, "FCV_FAULT", "Critical", {1: "Actuator over-force stop (EA-C force limit)"}.get(r.get("fault_code"), "Actuator fault"), "actuator")
    add(h > L["kv_wear_min_open"] and h < 0.5 and t["kv_ratio"] > L["kv_ratio_high"], "FCV_SEAT_PLUG_WEAR", "Medium",
        f"Valve passes {(t['kv_ratio'] - 1) * 100:.0f} % more than KSB Kv at {r['position_pct']:.0f} % open", "trim", "seat_plug_wear")
    add(h > L["kv_check_min_open"] and t["kv_ratio"] < L["kv_ratio_low"] and r["position_cmd_pct"] < 99, "FCV_KV_LOW", "Medium",
        f"Valve passes {(1 - t['kv_ratio']) * 100:.0f} % less than KSB Kv at the reported {r['position_pct']:.0f} % open", "actuator", "position_sensor_drift")
    add(h > 0.02 and t["sigma"] < k["sig_d"], "FCV_CAVITATION", "High", f"Cavitation index σ = {t['sigma']:.2f} (damage below {k['sig_d']})", "trim", "seat_plug_wear")
    add(h > 0.02 and k["sig_d"] <= t["sigma"] < k["sig_i"], "FCV_CAVITATION_INCIPIENT", "Low", f"Incipient cavitation, σ = {t['sigma']:.2f}", "trim")
    add(t["force_deviation_pct"] > L["force_dev_alert_pct"] and r["actuator_force_pct"] <= L["force_alert_pct"], "FCV_STICTION", "Medium",
        f"Stem force {t['force_deviation_pct']:.0f} pts above packing friction + dp load (stick-slip)", "stem", "stiction")
    add(r["actuator_temp_c"] > L["actuator_temp_alert_c"] or r["actuator_force_pct"] > L["force_alert_pct"], "FCV_ACTUATOR_OVERLOAD", "High",
        f"Actuator {r['actuator_temp_c']:.0f} °C, force {r['actuator_force_pct']:.0f} %", "actuator", "actuator_fault")
    add(r["gland_leak_ml_min"] > L["gland_leak_alert_ml_min"], "FCV_GLAND_LEAK", "Medium", f"Stem seal leak {r['gland_leak_ml_min']:.1f} ml/min", "stem", "gland_leak")
    add(t["strainer_kv_ratio"] < L["strainer_kv_ratio_alert"], "FCV_STRAINER_BLOCKED", "Medium",
        f"Strainer passes {t['strainer_kv_ratio'] * 100:.0f} % of its clean Kv ({r['inlet_pressure_bar'] - r['valve_inlet_pressure_bar']:.2f} bar)", "strainer", "strainer_blockage")
    add(r["position_cmd_pct"] > 98 and t["flow_error_pct"] < -L["flow_error_alert_pct"], "FCV_SATURATED", "Medium",
        f"Valve fully open, flow {-t['flow_error_pct']:.0f} % below demand", "body")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
