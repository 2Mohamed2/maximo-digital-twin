"""The hot WFI loop twin's expectations (WFI-6701, hot water-for-injection storage and distribution loop).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Flow and turbulence (EU GMP Annex 1 6.9):
      v = Q / 3600 / (pi/4 x D^2)                      return velocity at the end of the loop, the lowest in the loop
      Re = rho x v x D / mu                            rho and mu of water at the return temperature
      rho(T) = 1000 x (1 - (T + 288.9414) / (508929.2 x (T + 68.12963)) x (T - 3.9863)^2)     (Tanaka form, kg/m3)
      mu(T)  = 2.414e-5 x 10^(247.8 / (T + 273.15 - 140))                                     (Vogel, Pa s)
  Hot water is very fluid (mu at 80 C is about a third of mu at 20 C), so Re is far above 4000 whenever water moves:
  the qualified return velocity is the real criterion.
Temperature (Annex 1 6.10, e.g. constant circulation above 70 C): loop minimum = min(supply, return, tank).
  Heat lost by the loop = rho x cp x Q x (T_supply - T_return).
Conductivity (USP <645> Stage 1): the raw (non-compensated) conductivity is compared with the table value at the
  temperature step not greater than the measured temperature (5 C steps, no interpolation):
      limit = TABLE[floor(T / 5)],   ratio = conductivity / limit
TOC (USP <643>, Ph. Eur.): ratio = TOC / 500 ppb.
Pump: expected differential pressure dp = dp0 x (n/n0)^2 - k x Q^2; hydraulic power = Q x dp / 36 (kW, Q in m3/h, dp in bar);
  efficiency = hydraulic power / shaft power. Seal: quench water warms up when hot WFI leaks past the product-side seal.
Cooler (double tube sheet): WFI-side pressure minus chilled water pressure must stay positive; telltale wet = leak.
Dead leg: branch temperature below the loop minimum means the branch does not exchange with the loop.
Vent filter: housing temperature minus tank temperature must stay positive, or vapour condenses on the membrane.
Sample results (LIMS): microbial count / 10 CFU per 100 mL and endotoxin / 0.25 EU/mL.
"""
import math


def _k(twin):
    d = twin["design"]
    lp, tp, fl, w, q, p = d["loop"], d["temperature"], d["flow"], d["water"], d["quality"], d["pump"]
    return dict(ds=lp["supply_id_mm"] / 1000, dr=lp["return_id_mm"] / 1000, q0=lp["supply_flow_m3h"],
                tset=tp["supply_setpoint_c"], cp=w["cp_kj_kgk"], va=w["visc_a_pas"], vb=w["visc_b_k"], vc=w["visc_c_k"],
                table=list(q["usp645_stage1_us_cm"]), step=q["usp645_step_c"], toc=q["toc_limit_ppb"],
                eu=q["endotoxin_limit_eu_ml"], cfu=q["micro_action_cfu_100ml"],
                n0=p["speed_rpm"], dp0=p["dp0_bar"], kq=p["k_bar_per_m3h2"], eff=p["eff_design"], qin=p["quench_in_c"])


def area(dm):
    return math.pi / 4 * dm * dm


def rho(t):
    """Density of water, kg/m3 (Tanaka et al. 2001 form)."""
    return 1000 * (1 - (t + 288.9414) / (508929.2 * (t + 68.12963)) * (t - 3.9863) ** 2)


def mu(k, t):
    """Dynamic viscosity of water, Pa s (Vogel equation)."""
    return k["va"] * 10 ** (k["vb"] / (t + 273.15 - k["vc"]))


def stage1(k, t):
    """USP <645> Stage 1 limit at the table step not greater than t (uS/cm)."""
    i = min(len(k["table"]) - 1, max(0, int(math.floor(t / k["step"]))))
    return k["table"][i]


def dp_expected(k, q, n):
    return k["dp0"] * (n / k["n0"]) ** 2 - k["kq"] * q * q


def _parts(twin):
    k = _k(twin)
    TR = "df['RETURN_TEMP_C']"
    RHO = f"(1000 * (1 - ({TR} + 288.9414) / (508929.2 * ({TR} + 68.12963)) * ({TR} - 3.9863) ** 2))"
    MU = f"({k['va']} * np.power(10, {k['vb']} / ({TR} + {273.15 - k['vc']:.6g})))"
    VR = f"(df['RETURN_FLOW_M3H'] / 3600 / {area(k['dr'])!r})"
    LIM = (f"np.array({k['table']})[np.clip(np.floor({TR} / {k['step']}), 0, {len(k['table']) - 1}).astype(int)]")
    DPE = f"({k['dp0']} * (df['PUMP_SPEED_RPM'] / {k['n0']}) ** 2 - {k['kq']} * df['SUPPLY_FLOW_M3H'] ** 2)"
    TMIN = "np.minimum(np.minimum(df['SUPPLY_TEMP_C'], df['RETURN_TEMP_C']), df['TANK_TEMP_C'])"
    return dict(k=k, RHO=RHO, MU=MU, VR=VR, LIM=LIM, DPE=DPE, TMIN=TMIN)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("POU_DRAW_M3H", "df['SUPPLY_FLOW_M3H'] - df['RETURN_FLOW_M3H']"),
        ("SUPPLY_VELOCITY_MS", f"df['SUPPLY_FLOW_M3H'] / 3600 / {area(k['ds'])!r}"),
        ("RETURN_VELOCITY_MS", p["VR"]),
        ("RETURN_DENSITY_KGM3", p["RHO"]),
        ("RETURN_VISCOSITY_MPAS", f"{p['MU']} * 1000"),
        ("RETURN_REYNOLDS", f"{p['RHO']} * {p['VR']} * {k['dr']} / {p['MU']}"),
        ("LOOP_MIN_TEMP_C", p["TMIN"]),
        ("LOOP_HEAT_LOSS_KW", f"{p['RHO']} * {k['cp']} * df['RETURN_FLOW_M3H'] / 3600 * (df['SUPPLY_TEMP_C'] - df['RETURN_TEMP_C'])"),
        ("COND_STAGE1_LIMIT", p["LIM"]),
        ("COND_RATIO", f"df['COND_US_CM'] / {p['LIM']}"),
        ("TOC_RATIO", f"df['TOC_PPB'] / {k['toc']}"),
        ("PUMP_DP_EXPECTED_BAR", p["DPE"]),
        ("PUMP_DP_RATIO", f"df['PUMP_DP_BAR'] / {p['DPE']}"),
        ("PUMP_EFFICIENCY", "df['SUPPLY_FLOW_M3H'] * df['PUMP_DP_BAR'] / 36 / df['PUMP_POWER_KW']"),
        ("SEAL_QUENCH_RISE_C", f"df['SEAL_QUENCH_TEMP_C'] - {k['qin']}"),
        ("COOLER_DP_BAR", "df['COOLER_WFI_BAR'] - df['COOLER_CW_BAR']"),
        ("DEADLEG_DELTA_C", f"{p['TMIN']} - df['DEADLEG_TEMP_C']"),
        ("VENT_FILTER_MARGIN_C", "df['VENT_FILTER_TEMP_C'] - df['TANK_TEMP_C']"),
        ("MICRO_RATIO", f"df['MICRO_CFU_100ML'] / {k['cfu']}"),
        ("ENDOTOXIN_RATIO", f"df['ENDOTOXIN_EU_ML'] / {k['eu']}"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    tr = r["return_temp_c"]
    rh, m = rho(tr), mu(k, tr)
    vr = r["return_flow_m3h"] / 3600 / area(k["dr"])
    lim = stage1(k, tr)
    dpe = dp_expected(k, r["supply_flow_m3h"], r["pump_speed_rpm"])
    tmin = min(r["supply_temp_c"], tr, r["tank_temp_c"])
    return {
        "pou_draw_m3h": r["supply_flow_m3h"] - r["return_flow_m3h"],
        "supply_velocity_ms": r["supply_flow_m3h"] / 3600 / area(k["ds"]),
        "return_velocity_ms": vr,
        "return_density_kgm3": rh,
        "return_viscosity_mpas": m * 1000,
        "return_reynolds": rh * vr * k["dr"] / m,
        "loop_min_temp_c": tmin,
        "loop_heat_loss_kw": rh * k["cp"] * r["return_flow_m3h"] / 3600 * (r["supply_temp_c"] - tr),
        "cond_stage1_limit": lim,
        "cond_ratio": r["cond_us_cm"] / lim,
        "toc_ratio": r["toc_ppb"] / k["toc"],
        "pump_dp_expected_bar": dpe,
        "pump_dp_ratio": r["pump_dp_bar"] / dpe,
        "pump_efficiency": r["supply_flow_m3h"] * r["pump_dp_bar"] / 36 / r["pump_power_kw"],
        "seal_quench_rise_c": r["seal_quench_temp_c"] - k["qin"],
        "cooler_dp_bar": r["cooler_wfi_bar"] - r["cooler_cw_bar"],
        "deadleg_delta_c": tmin - r["deadleg_temp_c"],
        "vent_filter_margin_c": r["vent_filter_temp_c"] - r["tank_temp_c"],
        "micro_ratio": r["micro_cfu_100ml"] / k["cfu"],
        "endotoxin_ratio": r["endotoxin_eu_ml"] / k["eu"],
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    TMIN, VR = p["TMIN"], p["VR"]
    CR = f"(df['COND_US_CM'] / {p['LIM']})"
    DPR = f"(df['PUMP_DP_BAR'] / {p['DPE']})"
    return [
        ("WFI_COOLER_LEAK", "df['COOLER_TELLTALE'] > 0.5", "Critical", "cooler_leak"),
        ("WFI_TEMP_LOW", f"{TMIN} < {L['temp_low_c']}", "High", "heating_loss"),
        ("WFI_VELOCITY_LOW", f"{VR} < {L['velocity_min_ms']}", "High", "over_draw"),
        ("WFI_COND_STAGE1_FAIL", f"{CR} > 1", "High", "generator_upset"),
        ("WFI_TOC_LIMIT", f"df['TOC_PPB'] > {L['toc_limit_ppb']}", "High", "generator_upset"),
        ("WFI_MICRO_ACTION", f"(df['MICRO_CFU_100ML'] >= {L['micro_action_cfu']}) | (df['ENDOTOXIN_EU_ML'] >= {L['endotoxin_limit_eu_ml']})", "High", "biofilm_deadleg"),
        ("WFI_COOLER_DP_LOW", f"(df['COOLER_WFI_BAR'] - df['COOLER_CW_BAR']) < {L['cooler_dp_min_bar']}", "High", "cooler_leak"),
        ("WFI_TEMP_MARGIN_LOW", f"({TMIN} < {L['temp_margin_c']}) & ({TMIN} >= {L['temp_low_c']})", "Medium", "heating_loss"),
        ("WFI_COND_ALERT", f"({CR} > {L['cond_alert_ratio']}) & ({CR} <= 1)", "Medium", "generator_upset"),
        ("WFI_TOC_ALERT", f"(df['TOC_PPB'] > {L['toc_alert_ppb']}) & (df['TOC_PPB'] <= {L['toc_limit_ppb']})", "Medium", "generator_upset"),
        ("WFI_PUMP_HEAD_LOW", f"{DPR} < {L['pump_head_ratio_min']}", "Medium", "pump_wear"),
        ("WFI_SEAL_LEAK", f"(df['SEAL_QUENCH_TEMP_C'] - {p['k']['qin']}) > {L['seal_rise_max_c']}", "Medium", "seal_wear"),
        ("WFI_DEADLEG_COLD", f"({TMIN} - df['DEADLEG_TEMP_C']) > {L['deadleg_delta_c']}", "Medium", "biofilm_deadleg"),
        ("WFI_SUBLOOP_SANITISE_DUE", f"df['SUBLOOP_COLD_H'] > {L['subloop_cold_max_h']}", "Medium", "biofilm_deadleg"),
        ("WFI_VENT_FILTER_COLD", f"(df['VENT_FILTER_TEMP_C'] - df['TANK_TEMP_C']) < {L['vent_margin_min_c']}", "Medium", "vent_heater_fail"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    tmin, vr, cr, dpr = t["loop_min_temp_c"], t["return_velocity_ms"], t["cond_ratio"], t["pump_dp_ratio"]
    add(r["cooler_telltale"] > 0.5, "WFI_COOLER_LEAK", "Critical", "Telltale between the cooler tube sheets is wet: a tube sheet leaks; isolate the point of use",
        "cooler", "cooler_leak")
    add(tmin < L["temp_low_c"], "WFI_TEMP_LOW", "High", f"Loop minimum {tmin:.1f} °C, below {L['temp_low_c']:.0f} °C: no longer self-sanitising",
        "heater", "heating_loss")
    add(vr < L["velocity_min_ms"], "WFI_VELOCITY_LOW", "High", f"Return velocity {vr:.2f} m/s, below the qualified {L['velocity_min_ms']} m/s "
        f"({t['pou_draw_m3h']:.1f} m³/h drawn)", "points of use", "over_draw")
    add(cr > 1, "WFI_COND_STAGE1_FAIL", "High", f"Conductivity {r['cond_us_cm']:.2f} µS/cm above the USP <645> Stage 1 limit "
        f"{t['cond_stage1_limit']:.1f} at {r['return_temp_c']:.1f} °C", "water quality", "generator_upset")
    add(r["toc_ppb"] > L["toc_limit_ppb"], "WFI_TOC_LIMIT", "High", f"TOC {r['toc_ppb']:.0f} ppb above {L['toc_limit_ppb']:.0f} ppb", "water quality", "generator_upset")
    add(r["micro_cfu_100ml"] >= L["micro_action_cfu"] or r["endotoxin_eu_ml"] >= L["endotoxin_limit_eu_ml"], "WFI_MICRO_ACTION", "High",
        f"Last sample {r['micro_cfu_100ml']:.0f} CFU/100 mL, endotoxin {r['endotoxin_eu_ml']:.3f} EU/mL: action level reached", "points of use", "biofilm_deadleg")
    add(t["cooler_dp_bar"] < L["cooler_dp_min_bar"], "WFI_COOLER_DP_LOW", "High", f"Cooler WFI side only {t['cooler_dp_bar']:+.2f} bar above the chilled water",
        "cooler", "cooler_leak")
    add(L["temp_low_c"] <= tmin < L["temp_margin_c"], "WFI_TEMP_MARGIN_LOW", "Medium", f"Loop minimum {tmin:.1f} °C, below {L['temp_margin_c']:.0f} °C",
        "heater", "heating_loss")
    add(L["cond_alert_ratio"] < cr <= 1, "WFI_COND_ALERT", "Medium", f"Conductivity at {cr * 100:.0f} % of the Stage 1 limit", "water quality", "generator_upset")
    add(L["toc_alert_ppb"] < r["toc_ppb"] <= L["toc_limit_ppb"], "WFI_TOC_ALERT", "Medium", f"TOC {r['toc_ppb']:.0f} ppb, above the {L['toc_alert_ppb']:.0f} ppb alert level",
        "water quality", "generator_upset")
    add(dpr < L["pump_head_ratio_min"], "WFI_PUMP_HEAD_LOW", "Medium", f"Pump gives {dpr * 100:.0f} % of the curve's pressure at {r['supply_flow_m3h']:.1f} m³/h",
        "pump", "pump_wear")
    add(t["seal_quench_rise_c"] > L["seal_rise_max_c"], "WFI_SEAL_LEAK", "Medium", f"Seal quench water {t['seal_quench_rise_c']:.0f} K warmer than its inlet",
        "pump seal", "seal_wear")
    add(t["deadleg_delta_c"] > L["deadleg_delta_c"], "WFI_DEADLEG_COLD", "Medium", f"Worst branch {r['deadleg_temp_c']:.1f} °C, {t['deadleg_delta_c']:.0f} K below the loop",
        "points of use", "biofilm_deadleg")
    add(r["subloop_cold_h"] > L["subloop_cold_max_h"], "WFI_SUBLOOP_SANITISE_DUE", "Medium", f"Cooled sub-loop below 65 °C for {r['subloop_cold_h']:.1f} h without a hot flush",
        "points of use", "biofilm_deadleg")
    add(t["vent_filter_margin_c"] < L["vent_margin_min_c"], "WFI_VENT_FILTER_COLD", "Medium", f"Vent filter {t['vent_filter_margin_c']:+.1f} K against the tank: condensation risk",
        "tank vent filter", "vent_heater_fail")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
