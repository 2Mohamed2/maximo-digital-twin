"""The 400 Hz ground power unit twin's expectations (GPU-5901, 90 kVA solid-state GPU under a boarding bridge).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Load (per reading, from the three output voltages and currents at the GPU terminals):
    S = (Ua Ia + Ub Ib + Uc Ic) / 1000  kVA,   load % = S / S_rated,   PF = P_out / S
Voltage drop along the aircraft cable (per phase, the usual short-line approximation):
    dU = I x (R cos phi + X sin phi),   R = r x L,  X = x(400 Hz) x L
  At 400 Hz the reactance is eight times its 50 Hz value, so X, not R, carries most of the drop. The GPU raises its output
  by the expected drop so that the aircraft sees 115 V:  U_out setpoint = 115 + dU_expected.
  The plug-head voltage sense gives the drop actually measured: dU_measured = mean(U_out) - mean(U_connector).
  drop ratio = dU_measured / dU_expected: 1 when the cable and connector are as modelled.
  At the aircraft connector the voltage must stay inside 113..118 V (MIL-STD-704 108..118 V inside the aircraft, minus up
  to 5 V of aircraft wiring, as UFC 3-555-01N writes it); unbalance = max - min of the three connector voltages.
Efficiency (loss model fitted to the data sheet):
    P_loss = P0 + k x S^2,   P0 = no-load loss,   k from the efficiency at full load and PF 0.8
    loss excess = (P_in - P_out) - P_loss expected
Cooling:
    heat-sink residual = T_heatsink - (T_ambient + Rth x measured loss): positive = the cooling removes less heat than at commissioning
APU replacement (while the aircraft is on the GPU and its APU is off):
    fuel avoided = APU fuel flow,   CO2 avoided = fuel x 3.16 - P_in x grid factor   (kg/h)
"""
import math


def _k(twin):
    d = twin["design"]
    ra, ef, cb, al, th, we, ap = (d["rating"], d["efficiency"], d["cable"], d["aircraft_limits"], d["thermal"], d["wear"], d["apu"])
    p_full = ef["eff_full_kva"] * ef["pf"]
    kq = float(f'{(p_full / ef["eff_full"] - p_full - ef["no_load_loss_kw"]) / ef["eff_full_kva"] ** 2:.6g}')
    return dict(kva=ra["kva"], vn=ra["v_ln_nom"], fn=ra["f_nom_hz"], ftol=ra["f_nom_hz"] * ra["freq_tol_pct"] / 100,
                thd_spec=ra["thd_spec_pct"], ovl=ra["overload_pct_600s"], p0=ef["no_load_loss_kw"], kq=kq,
                r=round(cb["r_mohm_per_m"] * cb["length_m"] / 1000, 9), x=round(cb["x_mohm_per_m_400hz"] * cb["length_m"] / 1000, 9),
                vmin=al["conn_min_v"], vmax=al["conn_max_v"], thd_lim=al["thd_limit_pct"], rth=th["rth_k_per_kw"],
                c_life=we["contactor_life_ops"], p_life=we["connector_life_cycles"],
                fuel=ap["fuel_kg_h"], co2f=ap["co2_per_kg_fuel"], grid=ap["grid_kg_co2_per_kwh"])


def loss_expected(k, kva):
    return k["p0"] + k["kq"] * kva ** 2


def eff_expected(k, kva, pf=0.8):
    p = kva * pf
    return p / (p + loss_expected(k, kva)) if p > 0 else 0.0


def drop_expected(k, i, pf):
    pf = min(max(pf, 0.0), 1.0)
    return i * (k["r"] * pf + k["x"] * math.sqrt(1 - pf * pf))


def _parts(twin):
    k = _k(twin)
    S = "((df['U_OUT_A'] * df['I_A'] + df['U_OUT_B'] * df['I_B'] + df['U_OUT_C'] * df['I_C']) / 1000)"
    PF = f"np.clip(df['P_OUT_KW'] / np.maximum({S}, 0.1), 0, 1)"
    I = "((df['I_A'] + df['I_B'] + df['I_C']) / 3)"
    UO = "((df['U_OUT_A'] + df['U_OUT_B'] + df['U_OUT_C']) / 3)"
    UC = "((df['CONN_V_A'] + df['CONN_V_B'] + df['CONN_V_C']) / 3)"
    UMIN = "np.minimum(np.minimum(df['CONN_V_A'], df['CONN_V_B']), df['CONN_V_C'])"
    UMAX = "np.maximum(np.maximum(df['CONN_V_A'], df['CONN_V_B']), df['CONN_V_C'])"
    DE = f"({I} * ({k['r']:.6g} * {PF} + {k['x']:.6g} * np.sqrt(1 - {PF} ** 2)))"
    DM = f"({UO} - {UC})"
    LM = "(df['P_IN_KW'] - df['P_OUT_KW'])"
    LE = f"({k['p0']} + {k['kq']:.6g} * {S} ** 2)"
    ON = "(df['CONTACTOR'] > 0.5)"
    return dict(k=k, S=S, PF=PF, I=I, UO=UO, UC=UC, UMIN=UMIN, UMAX=UMAX, DE=DE, DM=DM, LM=LM, LE=LE, ON=ON,
                LP=f"({S} / {k['kva']} * 100)")


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("LOAD_KVA", p["S"]),
        ("LOAD_PCT", p["LP"]),
        ("LOAD_PF", p["PF"]),
        ("V_CONN_AVG", p["UC"]),
        ("V_CONN_MIN", p["UMIN"]),
        ("V_UNBALANCE_V", f"{p['UMAX']} - {p['UMIN']}"),
        ("CABLE_DROP_EXPECTED_V", p["DE"]),
        ("CABLE_DROP_MEASURED_V", p["DM"]),
        ("CABLE_DROP_RATIO", f"{p['DM']} / np.maximum({p['DE']}, 0.2)"),
        ("V_OUT_SETPOINT_V", f"{k['vn']} + {p['DE']}"),
        ("REGULATION_ERROR_V", f"{p['UO']} - ({k['vn']} + {p['DE']})"),
        ("FREQ_DEV_HZ", f"df['FREQ_HZ'] - {k['fn']}"),
        ("LOSS_MEASURED_KW", p["LM"]),
        ("LOSS_EXPECTED_KW", p["LE"]),
        ("LOSS_EXCESS_KW", f"{p['LM']} - {p['LE']}"),
        ("EFFICIENCY", "df['P_OUT_KW'] / np.maximum(df['P_IN_KW'], 0.1)"),
        ("EFFICIENCY_EXPECTED", f"df['P_OUT_KW'] / np.maximum(df['P_OUT_KW'] + {p['LE']}, 0.1)"),
        ("HEATSINK_RESIDUAL_K", f"df['HEATSINK_C'] - (df['AMBIENT_C'] + {k['rth']} * {p['LM']})"),
        ("APU_FUEL_AVOIDED_KG_H", f"{p['ON']} * (1 - df['APU_RUNNING']) * {k['fuel']}"),
        ("CO2_AVOIDED_KG_H", f"{p['ON']} * (1 - df['APU_RUNNING']) * {k['fuel'] * k['co2f']:.6g} - df['P_IN_KW'] * {k['grid']}"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    s = (r["u_out_a"] * r["i_a"] + r["u_out_b"] * r["i_b"] + r["u_out_c"] * r["i_c"]) / 1000
    pf = min(max(r["p_out_kw"] / max(s, 0.1), 0.0), 1.0)
    i = (r["i_a"] + r["i_b"] + r["i_c"]) / 3
    uo = (r["u_out_a"] + r["u_out_b"] + r["u_out_c"]) / 3
    cv = (r["conn_v_a"], r["conn_v_b"], r["conn_v_c"])
    uc = sum(cv) / 3
    de = i * (k["r"] * pf + k["x"] * math.sqrt(1 - pf ** 2))
    dm = uo - uc
    lm = r["p_in_kw"] - r["p_out_kw"]
    le = k["p0"] + k["kq"] * s ** 2
    on = 1.0 if r["contactor"] > 0.5 else 0.0
    return {
        "load_kva": s, "load_pct": s / k["kva"] * 100, "load_pf": pf,
        "v_conn_avg": uc, "v_conn_min": min(cv), "v_unbalance_v": max(cv) - min(cv),
        "cable_drop_expected_v": de, "cable_drop_measured_v": dm, "cable_drop_ratio": dm / max(de, 0.2),
        "v_out_setpoint_v": k["vn"] + de, "regulation_error_v": uo - (k["vn"] + de),
        "freq_dev_hz": r["freq_hz"] - k["fn"],
        "loss_measured_kw": lm, "loss_expected_kw": le, "loss_excess_kw": lm - le,
        "efficiency": r["p_out_kw"] / max(r["p_in_kw"], 0.1), "efficiency_expected": r["p_out_kw"] / max(r["p_out_kw"] + le, 0.1),
        "heatsink_residual_k": r["heatsink_c"] - (r["ambient_c"] + k["rth"] * lm),
        "apu_fuel_avoided_kg_h": on * (1 - r["apu_running"]) * k["fuel"],
        "co2_avoided_kg_h": on * (1 - r["apu_running"]) * (k["fuel"] * k["co2f"]) - r["p_in_kw"] * k["grid"],
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    ON, LP = p["ON"], p["LP"]
    LOADED = f"{ON} & ({LP} > {L['min_load_pct']})"
    THD = "df['THD_V_PCT']"
    return [
        ("GPU_CONN_VOLTAGE_LOW", f"{ON} & ({p['UMIN']} < {k['vmin']})", "High", "cable_compensation_mismatch"),
        ("GPU_CONN_VOLTAGE_HIGH", f"{ON} & ({p['UMAX']} > {k['vmax']})", "High", None),
        ("GPU_THD_LIMIT", f"{THD} > {k['thd_lim']}", "High", "output_filter_aging"),
        ("GPU_OVERLOAD", f"{LP} > {k['ovl']}", "High", None),
        ("GPU_HEATSINK_HOT", f"df['HEATSINK_C'] > {L['hs_max_c']}", "High", "cooling_degraded"),
        ("GPU_REGULATION_ERROR", f"{LOADED} & (np.abs({p['UO']} - ({k['vn']} + {p['DE']})) > {L['regulation_err_v']})", "Medium", "voltage_regulation_fault"),
        ("GPU_CABLE_DROP_HIGH", f"{LOADED} & ({p['DM']} / np.maximum({p['DE']}, 0.2) > {L['drop_ratio_alert']})", "Medium", "cable_compensation_mismatch"),
        ("GPU_PHASE_UNBALANCE", f"{ON} & ({p['UMAX']} - {p['UMIN']} > {L['unbalance_v']})", "Medium", "connector_pin_wear"),
        ("GPU_FREQ_OUT_OF_SPEC", f"np.abs(df['FREQ_HZ'] - {k['fn']}) > {k['ftol']:.6g}", "Medium", None),
        ("GPU_THD_HIGH", f"({THD} > {k['thd_spec']}) & ({THD} <= {k['thd_lim']})", "Medium", "output_filter_aging"),
        ("GPU_EFFICIENCY_LOW", f"{LOADED} & ({p['LM']} - {p['LE']} > {L['loss_excess_kw']})", "Medium", "power_stage_losses"),
        ("GPU_HEATSINK_FOULED", f"df['HEATSINK_C'] - (df['AMBIENT_C'] + {k['rth']} * {p['LM']}) > {L['hs_residual_k']}", "Medium", "cooling_degraded"),
        ("GPU_CONTACTOR_LIFE", f"df['CONTACTOR_OPS'] > {k['c_life'] * L['contactor_life_pct'] / 100:.6g}", "Medium", "contactor_wear"),
        ("GPU_CONNECTOR_CYCLES", f"df['PLUG_CYCLES'] > {k['p_life'] * L['connector_cycles_pct'] / 100:.6g}", "Medium", "connector_pin_wear"),
        ("GPU_APU_RUNNING", f"{ON} & (df['APU_RUNNING'] > 0.5)", "Medium", "apu_left_running"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    on = r["contactor"] > 0.5
    loaded = on and t["load_pct"] > L["min_load_pct"]
    cv = (r["conn_v_a"], r["conn_v_b"], r["conn_v_c"])
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    add(on and min(cv) < k["vmin"], "GPU_CONN_VOLTAGE_LOW", "High",
        f"{min(cv):.1f} V at the aircraft connector, below {k['vmin']:.0f} V", "connector", "cable_compensation_mismatch")
    add(on and max(cv) > k["vmax"], "GPU_CONN_VOLTAGE_HIGH", "High", f"{max(cv):.1f} V at the aircraft connector, above {k['vmax']:.0f} V", "connector")
    add(r["thd_v_pct"] > k["thd_lim"], "GPU_THD_LIMIT", "High", f"Voltage THD {r['thd_v_pct']:.1f} %, above the {k['thd_lim']:.0f} % aircraft limit",
        "filter", "output_filter_aging")
    add(t["load_pct"] > k["ovl"], "GPU_OVERLOAD", "High", f"Load {t['load_pct']:.0f} % of {k['kva']:.0f} kVA", "converter")
    add(r["heatsink_c"] > L["hs_max_c"], "GPU_HEATSINK_HOT", "High", f"Heat sink {r['heatsink_c']:.0f} °C, above {L['hs_max_c']:.0f} °C", "cooling", "cooling_degraded")
    add(loaded and abs(t["regulation_error_v"]) > L["regulation_err_v"], "GPU_REGULATION_ERROR", "Medium",
        f"Output {t['regulation_error_v']:+.1f} V from its setpoint {t['v_out_setpoint_v']:.1f} V", "control", "voltage_regulation_fault")
    add(loaded and t["cable_drop_ratio"] > L["drop_ratio_alert"], "GPU_CABLE_DROP_HIGH", "Medium",
        f"Cable drop {t['cable_drop_measured_v']:.1f} V, {t['cable_drop_ratio']:.2f} x the cable model", "cable", "cable_compensation_mismatch")
    add(on and t["v_unbalance_v"] > L["unbalance_v"], "GPU_PHASE_UNBALANCE", "Medium",
        f"Connector phases {cv[0]:.1f} / {cv[1]:.1f} / {cv[2]:.1f} V: {t['v_unbalance_v']:.1f} V apart", "connector", "connector_pin_wear")
    add(abs(t["freq_dev_hz"]) > k["ftol"], "GPU_FREQ_OUT_OF_SPEC", "Medium", f"Frequency {r['freq_hz']:.2f} Hz, outside 400 ± {k['ftol']:.1f} Hz", "control")
    add(k["thd_spec"] < r["thd_v_pct"] <= k["thd_lim"], "GPU_THD_HIGH", "Medium", f"Voltage THD {r['thd_v_pct']:.1f} %, above the {k['thd_spec']:.0f} % of the data sheet",
        "filter", "output_filter_aging")
    add(loaded and t["loss_excess_kw"] > L["loss_excess_kw"], "GPU_EFFICIENCY_LOW", "Medium",
        f"Losses {t['loss_measured_kw']:.1f} kW, {t['loss_excess_kw']:.1f} kW above the model; efficiency {t['efficiency'] * 100:.1f} %", "converter", "power_stage_losses")
    add(t["heatsink_residual_k"] > L["hs_residual_k"], "GPU_HEATSINK_FOULED", "Medium",
        f"Heat sink {t['heatsink_residual_k']:.0f} K hotter than its losses explain", "cooling", "cooling_degraded")
    add(r["contactor_ops"] > k["c_life"] * L["contactor_life_pct"] / 100, "GPU_CONTACTOR_LIFE", "Medium",
        f"Output contactor at {r['contactor_ops'] / k['c_life'] * 100:.0f} % of its rated operations", "contactor", "contactor_wear")
    add(r["plug_cycles"] > k["p_life"] * L["connector_cycles_pct"] / 100, "GPU_CONNECTOR_CYCLES", "Medium",
        f"Connector head mated {r['plug_cycles']:.0f} times, rated {k['p_life']}", "connector", "connector_pin_wear")
    add(on and r["apu_running"] > 0.5, "GPU_APU_RUNNING", "Medium",
        f"APU running while on ground power: {k['fuel']:.0f} kg/h of fuel not saved", "aircraft", "apu_left_running")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
