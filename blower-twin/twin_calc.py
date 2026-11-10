"""The aeration blower twin's expectations (Aerzen AT 150-0.8 S-G5 turbo blower, Sanitaire Silver Series II discs).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (twin viewer, tests)

Air side (the blower and the pipework):
  expected grid pressure   p_grid = rho g Z (static submergence) + DWP(q) (diffuser) + k_grid (Q/Qref)^2
                           q = airflow per disc; DWP(q) = dwp0 + dwp1 q for clean EPDM membranes
  header loss              p_discharge - p_grid = k_pipe (Q/Qref)^2 when the zone valves are open
  pressure ratio           PR = (p_inlet + p_discharge) / p_inlet, p_inlet = ambient - inlet filter dp
  adiabatic power          P_ad = k/(k-1) p_in V_in (PR^((k-1)/k) - 1), V_in = actual inlet m3/s
  expected motor power     P_ad / eta_wire(Q/Qmax) (wire-to-air efficiency, assumed curve)
  surge                    surge flow at the present pressure rise: Q_s = Q_sref sqrt(dp / dp_sref); margin = (Q - Q_s)/Q

Oxygen side (the basin):
  oxygen demand            from the influent analyzers: O2 [kg/h] = Q_in (c_carbon + 4.57 f_nit NH4 / 1000)
  SOTE (clean)             sote_per_m Z (q / q_ref)^-n            (Sanitaire: about 6.5 % per m of submergence)
  oxygen per Nm3 of air    0.2997 kg O2/Nm3 x SOTE
  field transfer           AOTR = SOTR alpha F (beta Cs_T* - C) / Cs_20* theta^(T-20)     (ASCE 2-06 / EPA fine pore manual form)
                           Cs* = Cs(T) (p_amb / 1013.25) (1 + d_eff Z / 10.33)   effective saturation at depth
  expected airflow         O2 demand / (oxygen per Nm3 x alpha F_design x driving force)    -> air ratio = Q / expected
  specific energy          motor kW / O2 demand (kWh per kg O2)
A clean grid with design alpha F needs about the expected air; fouling (F down, DWP up) or a torn membrane
(coarse bubbles, pressure down) needs more; a DO probe that reads high makes the controller give less.
"""
import math

KAPPA = 1.4
O2_PER_NM3 = 0.2997          # kg O2 per Nm3 of air (20.95 % vol, 1.429 kg/Nm3 O2)


def cs_water(t):
    """Dissolved-oxygen saturation in clean water at 1 atm, mg/L (APHA / Benson-Krause polynomial)."""
    return 14.652 - 0.41022 * t + 0.007991 * t ** 2 - 0.000077774 * t ** 3


def _k(twin):
    d = twin["design"]
    b, g, ox, pr, sv = d["blower"], d["grid"], d["oxygen"], d["process"], d["surge"]
    return dict(qmax=b["flow_max_nm3h"], dpmax=b["pressure_max_mbar"], eta0=b["eta_wire_bep"], qbep=b["flow_bep_frac"],
                eta_c=b["eta_wire_curv"], n=g["discs"], Z=g["submergence_m"], dwp0=g["dwp0_mbar"], dwp1=g["dwp1_mbar_per_nm3h"],
                kgrid=g["k_grid_mbar"], kpipe=g["k_pipe_mbar"], qref=b["flow_max_nm3h"],
                sote_m=ox["sote_per_m"], qd=ox["q_ref_nm3h"], sn=ox["sote_exp"], af=ox["alpha_f_design"], beta=ox["beta"],
                theta=ox["theta"], deff=ox["d_eff_frac"], cc=pr["carbon_o2_kg_m3"], fn=pr["nitrified_frac"],
                qsref=sv["q_sref_nm3h"], dpsref=sv["dp_sref_mbar"])


def _parts(twin):
    k = _k(twin)
    Q = "df['AIRFLOW_NM3H'].clip(lower=1)"
    q = f"({Q} / {k['n']})"
    STATIC = 98.0665 * k["Z"]
    PG = f"({STATIC} + {k['dwp0']} + {k['dwp1']} * {q} + {k['kgrid']} * ({Q} / {k['qref']}) ** 2)"
    PIPE = f"({k['kpipe']} * ({Q} / {k['qref']}) ** 2)"
    PIN = "(df['AMBIENT_PRESSURE_MBAR'] - df['INLET_FILTER_DP_MBAR'])"
    PR = f"(({PIN} + df['DISCHARGE_PRESSURE_MBAR']) / {PIN})"
    VIN = f"({Q} * (1013.25 / {PIN}) * ((df['INLET_TEMP_C'] + 273.15) / 273.15) / 3600)"
    PAD = f"({KAPPA / (KAPPA - 1)} * {PIN} * 100 * {VIN} * ({PR} ** {(KAPPA - 1) / KAPPA} - 1) / 1000)"
    ETA = f"({k['eta0']} - {k['eta_c']} * ({Q} / {k['qmax']} - {k['qbep']}) ** 2)"
    PEXP = f"(({PAD} / {ETA}).clip(lower=0.5))"
    QS = f"({k['qsref']} * np.sqrt(df['DISCHARGE_PRESSURE_MBAR'].clip(lower=0) / {k['dpsref']}))"
    MARGIN = f"(({Q} - {QS}) / {Q} * 100)"
    O2D = f"(df['INFLUENT_FLOW_M3H'] * ({k['cc']} + 4.57 * {k['fn']} * df['INFLUENT_NH4_MGL'] / 1000))"
    SOTE = f"({k['sote_m']} * {k['Z']} * ({q} / {k['qd']}) ** (-{k['sn']}))"
    T = "df['WATER_TEMP_C']"
    CST = f"((14.652 - 0.41022 * {T} + 0.007991 * {T} ** 2 - 0.000077774 * {T} ** 3) * df['AMBIENT_PRESSURE_MBAR'] / 1013.25 * (1 + {k['deff']} * {k['Z']} / 10.33))"
    CS20 = cs_water(20) * (1 + k["deff"] * k["Z"] / 10.33)
    DO = "((df['DO_CONTROL_MGL'] + df['DO_OUTLET_MGL']) / 2)"
    DF = f"(({k['beta']} * {CST} - {DO}).clip(lower=0.1) / {CS20} * {k['theta']} ** ({T} - 20))"
    AIRX = f"({O2D} / ({O2_PER_NM3} * {SOTE} * {k['af']} * {DF}))"
    return dict(Q=Q, PG=PG, PIPE=PIPE, PIN=PIN, PR=PR, PAD=PAD, ETA=ETA, PEXP=PEXP, QS=QS, MARGIN=MARGIN, O2D=O2D, SOTE=SOTE,
                DF=DF, AIRX=AIRX, k=k)


def monitor_expressions(twin):
    p = _parts(twin)
    return [
        ("GRID_PRESSURE_EXPECTED_MBAR", p["PG"]),
        ("GRID_PRESSURE_RESIDUAL_MBAR", f"df['GRID_PRESSURE_MBAR'] - {p['PG']}"),
        ("HEADER_LOSS_MBAR", "df['DISCHARGE_PRESSURE_MBAR'] - df['GRID_PRESSURE_MBAR']"),
        ("HEADER_LOSS_RESIDUAL_MBAR", f"df['DISCHARGE_PRESSURE_MBAR'] - df['GRID_PRESSURE_MBAR'] - {p['PIPE']}"),
        ("PRESSURE_RATIO", p["PR"]),
        ("POWER_ADIABATIC_KW", p["PAD"]),
        ("POWER_EXPECTED_KW", p["PEXP"]),
        ("POWER_RESIDUAL_PCT", f"(df['MOTOR_POWER_KW'] - {p['PEXP']}) / {p['PEXP']} * 100"),
        ("WIRE_TO_AIR_EFF_PCT", f"{p['PAD']} / df['MOTOR_POWER_KW'].clip(lower=1) * 100"),
        ("SURGE_FLOW_NM3H", p["QS"]),
        ("SURGE_MARGIN_PCT", p["MARGIN"]),
        ("O2_DEMAND_KGH", p["O2D"]),
        ("SOTE_EXPECTED_PCT", f"{p['SOTE']} * 100"),
        ("AIRFLOW_EXPECTED_NM3H", p["AIRX"]),
        ("AIR_RATIO", f"{p['Q']} / {p['AIRX']}"),
        ("SPECIFIC_ENERGY_KWH_KG", f"df['MOTOR_POWER_KW'] / {p['O2D']}.clip(lower=1)"),
        ("SPECIFIC_ENERGY_EXPECTED_KWH_KG", f"{p['PEXP']} * ({p['AIRX']} / {p['Q']}) / {p['O2D']}.clip(lower=1)"),
        ("DO_SPREAD_MGL", "df['DO_CONTROL_MGL'] - df['DO_OUTLET_MGL']"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    Q = max(r["airflow_nm3h"], 1)
    q = Q / k["n"]
    pg = 98.0665 * k["Z"] + k["dwp0"] + k["dwp1"] * q + k["kgrid"] * (Q / k["qref"]) ** 2
    pipe = k["kpipe"] * (Q / k["qref"]) ** 2
    pin = r["ambient_pressure_mbar"] - r["inlet_filter_dp_mbar"]
    pr = (pin + r["discharge_pressure_mbar"]) / pin
    vin = Q * (1013.25 / pin) * ((r["inlet_temp_c"] + 273.15) / 273.15) / 3600
    pad = KAPPA / (KAPPA - 1) * pin * 100 * vin * (pr ** ((KAPPA - 1) / KAPPA) - 1) / 1000
    eta = k["eta0"] - k["eta_c"] * (Q / k["qmax"] - k["qbep"]) ** 2
    pexp = max(pad / eta, 0.5)
    qs = k["qsref"] * math.sqrt(max(r["discharge_pressure_mbar"], 0) / k["dpsref"])
    o2d = r["influent_flow_m3h"] * (k["cc"] + 4.57 * k["fn"] * r["influent_nh4_mgl"] / 1000)
    sote = k["sote_m"] * k["Z"] * (q / k["qd"]) ** (-k["sn"])
    T = r["water_temp_c"]
    cst = cs_water(T) * r["ambient_pressure_mbar"] / 1013.25 * (1 + k["deff"] * k["Z"] / 10.33)
    cs20 = cs_water(20) * (1 + k["deff"] * k["Z"] / 10.33)
    do = (r["do_control_mgl"] + r["do_outlet_mgl"]) / 2
    df_ = max(k["beta"] * cst - do, 0.1) / cs20 * k["theta"] ** (T - 20)
    airx = o2d / (O2_PER_NM3 * sote * k["af"] * df_)
    return {
        "grid_pressure_expected_mbar": pg, "grid_pressure_residual_mbar": r["grid_pressure_mbar"] - pg,
        "header_loss_mbar": r["discharge_pressure_mbar"] - r["grid_pressure_mbar"],
        "header_loss_residual_mbar": r["discharge_pressure_mbar"] - r["grid_pressure_mbar"] - pipe,
        "pressure_ratio": pr, "power_adiabatic_kw": pad, "power_expected_kw": pexp,
        "power_residual_pct": (r["motor_power_kw"] - pexp) / pexp * 100,
        "wire_to_air_eff_pct": pad / max(r["motor_power_kw"], 1) * 100,
        "surge_flow_nm3h": qs, "surge_margin_pct": (Q - qs) / Q * 100,
        "o2_demand_kgh": o2d, "sote_expected_pct": sote * 100, "airflow_expected_nm3h": airx, "air_ratio": Q / airx,
        "specific_energy_kwh_kg": r["motor_power_kw"] / max(o2d, 1),
        "specific_energy_expected_kwh_kg": pexp * (airx / Q) / max(o2d, 1),
        "do_spread_mgl": r["do_control_mgl"] - r["do_outlet_mgl"],
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    RES = f"(df['GRID_PRESSURE_MBAR'] - {p['PG']})"
    AIR = f"({p['Q']} / {p['AIRX']})"
    RUN = f"(df['AIRFLOW_NM3H'] > {L['running_flow_nm3h']})"
    return [
        ("BLW_DIFFUSER_FOULING", f"{RUN} & ({RES} > {L['grid_residual_high_mbar']}) & ({AIR} > {L['air_ratio_high']})", "Medium", "diffuser_fouling"),
        ("BLW_DIFFUSER_TEAR", f"{RUN} & ({RES} < {L['grid_residual_low_mbar']})", "High", "membrane_tear"),
        ("BLW_AIR_DEMAND_HIGH", f"{RUN} & ({AIR} > {L['air_ratio_alarm']})", "Low", None),
        ("BLW_INLET_FILTER", f"(df['INLET_FILTER_DP_MBAR'] > {L['filter_dp_alert_mbar']}) & (df['INLET_FILTER_DP_MBAR'] <= {L['filter_dp_high_mbar']})", "Medium", "inlet_filter"),
        ("BLW_INLET_FILTER_HIGH", f"df['INLET_FILTER_DP_MBAR'] > {L['filter_dp_high_mbar']}", "High", "inlet_filter"),
        ("BLW_SURGE_MARGIN", f"{RUN} & ({p['MARGIN']} < {L['surge_margin_alert_pct']})", "High", "surge_approach"),
        ("BLW_VALVE_THROTTLED", f"{RUN} & ((df['DISCHARGE_PRESSURE_MBAR'] - df['GRID_PRESSURE_MBAR'] - {p['PIPE']}) > {L['header_residual_alert_mbar']})", "Medium", "surge_approach"),
        ("BLW_BEARING", f"(df['VIBRATION_MM_S'] > {L['vibration_alert_mm_s']}) | (df['BEARING_TEMP_C'] > {L['bearing_temp_alert_c']})", "Medium", "bearing_wear"),
        ("BLW_EFFICIENCY_LOW", f"{RUN} & (((df['MOTOR_POWER_KW'] - {p['PEXP']}) / {p['PEXP']} * 100) > {L['power_residual_alert_pct']})", "Low", "bearing_wear"),
        ("BLW_DO_PROBE", f"{RUN} & ((df['DO_CONTROL_MGL'] - df['DO_OUTLET_MGL']).abs() > {L['do_spread_alert_mgl']}) & ({RES} >= {L['grid_residual_low_mbar']})", "Medium", "do_probe_drift"),
        ("BLW_DO_LOW", f"df['DO_OUTLET_MGL'] < {L['do_low_alert_mgl']}", "High", None),
        ("BLW_VFD_HOT", f"(df['VFD_TEMP_C'] > {L['vfd_temp_alert_c']}) | (df['MOTOR_TEMP_C'] > {L['motor_temp_alert_c']})", "High", "vfd_overheating"),
        ("BLW_TRIP", "df['TRIP_CODE'] > 0", "Critical", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    out = []
    run = r["airflow_nm3h"] > L["running_flow_nm3h"]

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    add(r["trip_code"] > 0, "BLW_TRIP", "Critical", {1: "Blower tripped: surge protection", 2: "Blower tripped: VFD over-temperature"}.get(r["trip_code"], "Blower tripped"), "blower")
    add(run and t["grid_pressure_residual_mbar"] > L["grid_residual_high_mbar"] and t["air_ratio"] > L["air_ratio_high"], "BLW_DIFFUSER_FOULING", "Medium",
        f"Grid pressure {t['grid_pressure_residual_mbar']:+.0f} mbar above clean diffusers and {t['air_ratio']:.2f}x the expected air for the oxygen demand", "grid", "diffuser_fouling")
    add(run and t["grid_pressure_residual_mbar"] < L["grid_residual_low_mbar"], "BLW_DIFFUSER_TEAR", "High",
        f"Grid pressure {t['grid_pressure_residual_mbar']:+.0f} mbar below clean diffusers: torn membrane or broken pipe (coarse bubbles)", "grid", "membrane_tear")
    add(run and t["air_ratio"] > L["air_ratio_alarm"], "BLW_AIR_DEMAND_HIGH", "Low", f"Airflow {t['air_ratio']:.2f}x what the oxygen demand needs with clean diffusers", "grid")
    add(L["filter_dp_alert_mbar"] < r["inlet_filter_dp_mbar"] <= L["filter_dp_high_mbar"], "BLW_INLET_FILTER", "Medium",
        f"Inlet filter dp {r['inlet_filter_dp_mbar']:.0f} mbar (alert {L['filter_dp_alert_mbar']})", "filter", "inlet_filter")
    add(r["inlet_filter_dp_mbar"] > L["filter_dp_high_mbar"], "BLW_INLET_FILTER_HIGH", "High",
        f"Inlet filter dp {r['inlet_filter_dp_mbar']:.0f} mbar: change the filter mats", "filter", "inlet_filter")
    add(run and t["surge_margin_pct"] < L["surge_margin_alert_pct"], "BLW_SURGE_MARGIN", "High",
        f"Surge margin {t['surge_margin_pct']:.0f} % ({r['airflow_nm3h']:.0f} Nm³/h vs surge {t['surge_flow_nm3h']:.0f} at {r['discharge_pressure_mbar']:.0f} mbar)", "blower", "surge_approach")
    add(run and t["header_loss_residual_mbar"] > L["header_residual_alert_mbar"], "BLW_VALVE_THROTTLED", "Medium",
        f"Header loss {t['header_loss_mbar']:.0f} mbar, {t['header_loss_residual_mbar']:.0f} mbar above open valves: a zone valve is throttled", "header", "surge_approach")
    add(r["vibration_mm_s"] > L["vibration_alert_mm_s"] or r["bearing_temp_c"] > L["bearing_temp_alert_c"], "BLW_BEARING", "Medium",
        f"Vibration {r['vibration_mm_s']:.1f} mm/s, bearing {r['bearing_temp_c']:.0f} °C", "blower", "bearing_wear")
    add(run and t["power_residual_pct"] > L["power_residual_alert_pct"], "BLW_EFFICIENCY_LOW", "Low",
        f"Motor power {t['power_residual_pct']:+.0f} % above the expected for this flow and pressure", "blower", "bearing_wear")
    add(run and abs(t["do_spread_mgl"]) > L["do_spread_alert_mgl"] and t["grid_pressure_residual_mbar"] >= L["grid_residual_low_mbar"], "BLW_DO_PROBE", "Medium",
        f"Control DO {r['do_control_mgl']:.1f} vs outlet DO {r['do_outlet_mgl']:.1f} mg/L with an intact grid: control probe reads high", "do", "do_probe_drift")
    add(r["do_outlet_mgl"] < L["do_low_alert_mgl"], "BLW_DO_LOW", "High", f"Outlet DO {r['do_outlet_mgl']:.1f} mg/L: nitrification at risk", "basin")
    add(r["vfd_temp_c"] > L["vfd_temp_alert_c"] or r["motor_temp_c"] > L["motor_temp_alert_c"], "BLW_VFD_HOT", "High",
        f"VFD {r['vfd_temp_c']:.0f} °C, motor winding {r['motor_temp_c']:.0f} °C", "vfd", "vfd_overheating")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
