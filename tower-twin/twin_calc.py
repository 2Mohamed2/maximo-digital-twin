"""The cooling tower twin's expectations from BAC rating data (FXV-0812B-16D-L closed-circuit cooling tower).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (twin viewer, tests)

Thermal model (Braun's effectiveness model for evaporative heat exchangers, closed form):
  the air side is treated as a stream with an equivalent specific heat cs = dh_sat/dT (secant between the fluid
  inlet temperature and the entering wet bulb), so the coil behaves like a counterflow exchanger between
  the process fluid (C_f = m_f * cp) and air (C_a = m_a * cs) with driving difference (T_in - T_wb):
      Q = eps * C_min * (T_in - T_wb),   eps = (1 - e^(-N(1-Cr))) / (1 - Cr e^(-N(1-Cr))),   N = UA / C_min
      UA = UA_0 * (m_a / m_a0)^0.6 * (m_f / m_f0)^0.2         (air-side film dominated)
  UA_0 is calibrated so the model reproduces BAC's published nominal rating exactly (see build_twin.py).
  Air flow follows the fan VFD speed (fan affinity law); fan power follows speed^3.
"""
import math

P_ATM = 101.325        # kPa
LATENT_KJ_KG = 2430.0  # latent heat of evaporation at ~30 C
EVAP_SHARE = 0.9       # share of the heat rejected by evaporation (closed-circuit coolers: ~85-90 %)


def pws(t):
    """saturation vapour pressure over water, kPa (Magnus, Alduchov-Eskridge)."""
    return 0.61094 * math.exp(17.625 * t / (t + 243.04))


def h_sat(t):
    """enthalpy of saturated moist air, kJ/kg dry air."""
    p = pws(t)
    w = 0.622 * p / (P_ATM - p)
    return 1.006 * t + w * (2501.0 + 1.86 * t)


def _hs_expr(t):
    p = f"(0.61094 * np.exp(17.625 * {t} / ({t} + 243.04)))"
    return f"(1.006 * {t} + 0.622 * {p} / ({P_ATM} - {p}) * (2501.0 + 1.86 * {t}))"


def _k(twin):
    d = twin["design"]
    return dict(UA0=d["thermal"]["UA0_kW_K"], ma0=d["fan"]["air_flow_kg_s"], mf0=d["coil"]["fluid_flow_m3h"],
                cp=d["water_cp_kW_per_m3h_K"], P0=d["fan"]["motor_power_kw_at_100pct"], rpm0=d["fan"]["fan_rpm_at_100pct"],
                sq0=d["spray"]["flow_m3h"], sp0=d["spray"]["pressure_bar"], cond_mu=d["water"]["makeup_conductivity_us_cm"],
                drift=d["water"]["drift_rate_pct"] / 100.0)


def expected_q(twin, t_in, t_wb, flow_m3h, speed_pct):
    """BAC-calibrated heat rejection (kW) at the measured inlet temperature, wet bulb, fluid flow and fan speed."""
    k = _k(twin)
    ma = k["ma0"] * max(speed_pct, 1.0) / 100.0
    dt = max(t_in - t_wb, 0.05)
    cs = (h_sat(t_in) - h_sat(t_wb)) / dt
    ca, cf = ma * cs, k["cp"] * max(flow_m3h, 0.1)
    cmin, cmax = min(ca, cf), max(ca, cf)
    cr = min(cmin / cmax, 0.995)
    ua = k["UA0"] * (ma / k["ma0"]) ** 0.6 * (max(flow_m3h, 0.1) / k["mf0"]) ** 0.2
    n = ua / cmin
    e = math.exp(-n * (1 - cr))
    eps = (1 - e) / (1 - cr * e)
    return eps * cmin * dt


def _parts(twin):
    k = _k(twin)
    TI, TO, WB, F, S = "df['FLUID_IN_TEMP_C']", "df['FLUID_OUT_TEMP_C']", "df['AMBIENT_WET_BULB_C']", \
        "df['FLUID_FLOW_M3H'].clip(lower=0.1)", "df['FAN_SPEED_PCT'].clip(lower=1)"
    MA = f"({k['ma0']} * {S} / 100)"
    DT = f"({TI} - {WB}).clip(lower=0.05)"
    CS = f"(({_hs_expr(TI)} - {_hs_expr(WB)}) / {DT})"
    CA, CF = f"({MA} * {CS})", f"({k['cp']} * {F})"
    CMIN, CMAX = f"np.minimum({CA}, {CF})", f"np.maximum({CA}, {CF})"
    CR = f"({CMIN} / {CMAX}).clip(upper=0.995)"
    UA = f"({k['UA0']} * ({MA} / {k['ma0']}) ** 0.6 * ({F} / {k['mf0']}) ** 0.2)"
    N = f"({UA} / {CMIN})"
    E = f"np.exp(-{N} * (1 - {CR}))"
    QE = f"((1 - {E}) / (1 - {CR} * {E}) * {CMIN} * {DT})"
    QM = f"({k['cp']} * df['FLUID_FLOW_M3H'] * ({TI} - {TO}))"
    TOE = f"({TI} - {QE} / {CF})"
    PE = f"({k['P0']} * ({S} / 100) ** 3)"
    EV = f"({EVAP_SHARE} * {QM}.clip(lower=0) / {LATENT_KJ_KG} * 3.6)"
    return dict(QE=QE, QM=QM, TOE=TOE, PE=PE, EV=EV, S=S, k=k)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("Q_EXPECTED_KW", p["QE"]),
        ("FLUID_OUT_EXPECTED_C", p["TOE"]),
        ("OUT_TEMP_DEVIATION_K", f"df['FLUID_OUT_TEMP_C'] - {p['TOE']}"),
        ("CAPACITY_RATIO_PCT", f"{p['QM']} / {p['QE']}.clip(lower=1) * 100"),
        ("APPROACH_K", "df['FLUID_OUT_TEMP_C'] - df['AMBIENT_WET_BULB_C']"),
        ("RANGE_K", "df['FLUID_IN_TEMP_C'] - df['FLUID_OUT_TEMP_C']"),
        ("FAN_POWER_EXPECTED_KW", p["PE"]),
        ("FAN_POWER_DEVIATION_PCT", f"(df['FAN_POWER_KW'] - {p['PE']}) / {p['PE']}.clip(lower=0.2) * 100"),
        ("BELT_SLIP_PCT", f"(1 - df['FAN_RPM'] / ({k['rpm0']} * {p['S']} / 100)) * 100"),
        ("NOZZLE_K_RATIO", f"(df['SPRAY_PRESSURE_BAR'] / {k['sp0']}) / ((df['SPRAY_FLOW_M3H'].clip(lower=1) / {k['sq0']}) ** 2)"),
        ("EVAPORATION_EXPECTED_M3H", p["EV"]),
        ("UNACCOUNTED_WATER_M3H", f"df['MAKEUP_FLOW_M3H'] - {p['EV']} - df['BLOWDOWN_FLOW_M3H'] - {k['drift']} * df['SPRAY_FLOW_M3H']"),
        ("CYCLES_OF_CONCENTRATION", f"df['CONDUCTIVITY_US_CM'] / {k['cond_mu']}"),
        ("AUX_KW_PER_KW", f"(df['FAN_POWER_KW'] + df['SPRAY_PUMP_POWER_KW']) / {p['QM']}.clip(lower=1)"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    qe = expected_q(twin, r["fluid_in_temp_c"], r["ambient_wet_bulb_c"], r["fluid_flow_m3h"], r["fan_speed_pct"])
    qm = k["cp"] * r["fluid_flow_m3h"] * (r["fluid_in_temp_c"] - r["fluid_out_temp_c"])
    toe = r["fluid_in_temp_c"] - qe / (k["cp"] * max(r["fluid_flow_m3h"], 0.1))
    s = max(r["fan_speed_pct"], 1.0)
    pe = k["P0"] * (s / 100) ** 3
    ev = EVAP_SHARE * max(qm, 0) / LATENT_KJ_KG * 3.6
    return {
        "q_expected_kw": qe, "fluid_out_expected_c": toe, "out_temp_deviation_k": r["fluid_out_temp_c"] - toe,
        "capacity_ratio_pct": qm / max(qe, 1) * 100, "approach_k": r["fluid_out_temp_c"] - r["ambient_wet_bulb_c"],
        "range_k": r["fluid_in_temp_c"] - r["fluid_out_temp_c"], "fan_power_expected_kw": pe,
        "fan_power_deviation_pct": (r["fan_power_kw"] - pe) / max(pe, 0.2) * 100,
        "belt_slip_pct": (1 - r["fan_rpm"] / (k["rpm0"] * s / 100)) * 100,
        "nozzle_k_ratio": (r["spray_pressure_bar"] / k["sp0"]) / (max(r["spray_flow_m3h"], 1) / k["sq0"]) ** 2,
        "evaporation_expected_m3h": ev,
        "unaccounted_water_m3h": r["makeup_flow_m3h"] - ev - r["blowdown_flow_m3h"] - k["drift"] * r["spray_flow_m3h"],
        "cycles_of_concentration": r["conductivity_us_cm"] / k["cond_mu"],
        "aux_kw_per_kw": (r["fan_power_kw"] + r["spray_pump_power_kw"]) / max(qm, 1),
        "heat_rejected_kw": qm,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    run = "(df['RUNNING'] > 0)"
    dev = f"(df['FLUID_OUT_TEMP_C'] - {p['TOE']})"
    nz = f"((df['SPRAY_PRESSURE_BAR'] / {k['sp0']}) / ((df['SPRAY_FLOW_M3H'].clip(lower=1) / {k['sq0']}) ** 2))"
    slip = f"((1 - df['FAN_RPM'] / ({k['rpm0']} * {p['S']} / 100)) * 100)"
    unacc = f"(df['MAKEUP_FLOW_M3H'] - {p['EV']} - df['BLOWDOWN_FLOW_M3H'] - {k['drift']} * df['SPRAY_FLOW_M3H'])"
    return [
        ("CT_COIL_SCALING", f"{run} & ({dev} > {L['out_dev_alert_k']}) & ({nz} < {L['nozzle_ratio_alert']}) & ({slip} < {L['belt_slip_alert_pct']})", "Medium", "coil_scaling"),
        ("CT_NOZZLE_BLOCKAGE", f"{run} & ({nz} > {L['nozzle_ratio_alert']})", "Medium", "nozzle_blockage"),
        ("CT_BELT_SLIP", f"{run} & (df['FAN_SPEED_PCT'] > 30) & ({slip} > {L['belt_slip_alert_pct']})", "Medium", "belt_slip"),
        ("CT_FAN_VIBRATION", f"{run} & (df['FAN_VIB_MM_S'] > {L['vib_alert_mm_s']})", "Medium", "fan_bearing"),
        ("CT_FAN_BEARING_TEMP", f"df['FAN_BEARING_TEMP_C'] > {L['bearing_alert_c']}", "High", "fan_bearing"),
        ("CT_FAN_MOTOR_IMBALANCE", f"{run} & (df['FAN_CURRENT_IMBALANCE_PCT'] > {L['imbalance_alert_pct']})", "Medium", "fan_motor_winding"),
        ("CT_FAN_WINDING_TEMP", f"df['FAN_WINDING_TEMP_C'] > {L['winding_alert_c']}", "High", "fan_motor_winding"),
        ("CT_DRIFT_LOSS", f"{run} & ({unacc} > {L['unaccounted_water_alert_m3h']})", "Medium", "drift_eliminator"),
        ("CT_WATER_TREATMENT", f"df['CONDUCTIVITY_US_CM'] > {L['conductivity_alert_us_cm']}", "Medium", "water_treatment"),
        ("CT_CAPACITY_LIMIT", f"{run} & (df['FAN_SPEED_PCT'] > 98) & (df['FLUID_OUT_TEMP_C'] > df['FLUID_OUT_SETPOINT_C'] + 1.5)", "Low", None),
        ("CT_TRIPPED", "df['TRIP_CODE'] > 0", "Critical", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    run = r.get("running", 1) > 0
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    trips = {1: "Fan vibration switch trip", 2: "Fan motor winding (PTC) trip"}
    add(r.get("trip_code", 0) > 0, "CT_TRIPPED", "Critical", trips.get(r.get("trip_code"), "Tripped"), "fan")
    add(run and t["out_temp_deviation_k"] > L["out_dev_alert_k"] and t["nozzle_k_ratio"] < L["nozzle_ratio_alert"]
        and t["belt_slip_pct"] < L["belt_slip_alert_pct"], "CT_COIL_SCALING", "Medium",
        f"Leaving fluid {t['out_temp_deviation_k']:.1f} K warmer than BAC rating at this fan speed", "coil", "coil_scaling")
    add(run and t["nozzle_k_ratio"] > L["nozzle_ratio_alert"], "CT_NOZZLE_BLOCKAGE", "Medium",
        f"Spray nozzle resistance x{t['nozzle_k_ratio']:.2f} of clean", "spray", "nozzle_blockage")
    add(run and r["fan_speed_pct"] > 30 and t["belt_slip_pct"] > L["belt_slip_alert_pct"], "CT_BELT_SLIP", "Medium",
        f"Fan {t['belt_slip_pct']:.1f} % slower than the drive commands", "fan", "belt_slip")
    add(run and r["fan_vib_mm_s"] > L["vib_alert_mm_s"], "CT_FAN_VIBRATION", "Medium",
        f"Fan vibration {r['fan_vib_mm_s']:.1f} mm/s", "fan", "fan_bearing")
    add(r["fan_bearing_temp_c"] > L["bearing_alert_c"], "CT_FAN_BEARING_TEMP", "High",
        f"Fan bearing {r['fan_bearing_temp_c']:.0f} °C", "fan", "fan_bearing")
    add(run and r["fan_current_imbalance_pct"] > L["imbalance_alert_pct"], "CT_FAN_MOTOR_IMBALANCE", "Medium",
        f"Fan motor current imbalance {r['fan_current_imbalance_pct']:.1f} %", "motor", "fan_motor_winding")
    add(r["fan_winding_temp_c"] > L["winding_alert_c"], "CT_FAN_WINDING_TEMP", "High",
        f"Fan motor winding {r['fan_winding_temp_c']:.0f} °C", "motor", "fan_motor_winding")
    add(run and t["unaccounted_water_m3h"] > L["unaccounted_water_alert_m3h"], "CT_DRIFT_LOSS", "Medium",
        f"{t['unaccounted_water_m3h'] * 1000:.0f} l/h make-up not explained by evaporation, blowdown and rated drift", "eliminators", "drift_eliminator")
    add(r["conductivity_us_cm"] > L["conductivity_alert_us_cm"], "CT_WATER_TREATMENT", "Medium",
        f"Basin conductivity {r['conductivity_us_cm']:.0f} µS/cm ({t['cycles_of_concentration']:.1f} cycles)", "basin", "water_treatment")
    add(run and r["fan_speed_pct"] > 98 and r["fluid_out_temp_c"] > r["fluid_out_setpoint_c"] + 1.5, "CT_CAPACITY_LIMIT", "Low",
        f"Fans at full speed, leaving fluid {r['fluid_out_temp_c']:.1f} °C above setpoint", "coil")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
