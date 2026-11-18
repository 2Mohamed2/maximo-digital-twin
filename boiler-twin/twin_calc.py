"""The steam boiler twin's expectations (BL-4501, three-pass shell boiler with economiser, 10 t/h at 13 bar g, natural gas).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Steam side (steam table fits, x = ln(p_abs)):
    Tsat, h' (boiling water), h'' (saturated steam) = c0 + c1 x + c2 x^2;  feedwater h(T) = a T + b T^2 + c T^3
Direct (input-output) efficiency, boundary = boiler + economiser:
    blowdown         B = feed flow - steam flow                                                  [kg/h]
    heat output      Q_out = (S (h'' - h_fw) + B (h' - h_fw)) / 3600                              [kW]
    fuel input       Q_fuel = gas flow (Nm3/h) x LHV (MJ/Nm3) / 3.6                               [kW]
    efficiency       eta_direct = 100 x Q_out / Q_fuel                                           [% of LHV]
Indirect (losses) efficiency, EN 12953-11 / ASME PTC 4 idea:
    Siegert flue gas loss  qA = f (t_stack - t_air) / CO2,  CO2 = CO2max (1 - O2/21),  f = f0 + (f5 - f0) O2 / 5
    radiation loss         qR = qR,full / load
    eta_indirect = 100 - qA - qR
  The two efficiencies must agree. When they do not, a meter is wrong (gas flow, steam flow or the LHV).
Expected at today's load and steam pressure (what a clean boiler would do):
    boiler exit       T_exit,exp = Tsat + 60 K x load^0.5           (about 60 K above the steam temperature at full load)
    economiser        effectiveness = (T_exit - T_stack) / (T_exit - T_feed);  design value from the design stack temperature
    stack             T_stack,exp = T_exit,exp - eps_design (T_exit,exp - T_feed)
    efficiency        eta_expected = 100 - qA(T_stack,exp, O2 design) - qR
    flue gas dp       dp ratio = dp / (dp_full x load^1.8)
  Fire-side fouling (soot): exit temperature up AND gas-side pressure drop up. Water-side scale: exit temperature up, dp normal.
  The economiser takes back most of the exit temperature rise, so fire-side fouling hardly moves the stack: watch the exit.
Water chemistry (mass balance of dissolved solids):
    cycles of concentration = boiler water conductivity / feedwater conductivity
    blowdown needed (% of steam) = 100 x C_feed / (C_setpoint - C_feed)
Feed pump: margin = discharge pressure - steam pressure; expected discharge = p0 - k (feed t/h)^2.
Money: extra fuel = Q_fuel x (1 - eta_indirect / eta_expected)  [kW], priced and turned into CO2 in the post.
"""


def _k(twin):
    d = twin["design"]
    b, fw, bw, c, ht, fp, ts, st = (d["boiler"], d["feedwater"], d["boiler_water"], d["combustion"], d["heat_transfer"],
                                    d["feed_pump"], d["tests"], d["steam_table"])
    k = dict(rated=b["rated_steam_kgh"], p_op=b["operating_pressure_barg"], tfw=fw["temp_in_c"], cf_d=fw["cond_design_uscm"],
             hard=fw["hardness_alert_mmol_l"], cset=bw["cond_setpoint_uscm"], calert=bw["cond_alert_uscm"],
             lhv=c["lhv_mj_nm3"], co2m=c["co2max_pct"], f0=c["siegert_f_o2_0"], f5=c["siegert_f_o2_5"], o2d=c["o2_design_pct"],
             eak=c["ea_k"], tair=c["air_ref_c"], rad=c["radiation_loss_full_load_pct"], co=c["co_alert_ppm"],
             app=ht["exit_approach_full_load_k"], appn=ht["exit_approach_load_exp"], stack_d=ht["stack_design_c"],
             dp_d=ht["flue_dp_full_load_mbar"], dpn=ht["flue_dp_load_exp"], p0=fp["shutoff_barg"], kp=fp["k_bar_per_th2"],
             marg=fp["margin_alert_bar"], lvl=fp["level_alert_mm"], lwco=ts["lwco_test_interval_h"], sv=ts["sv_test_interval_h"],
             grace=ts["grace_factor"], ts=st["tsat"], hf=st["hf"], hg=st["hg"], liq=st["liquid"], patm=st["p_atm_bar"])
    k["tsat_d"] = tsat(k, k["p_op"])
    k["texit_d"] = k["tsat_d"] + k["app"]
    k["eps_d"] = (k["texit_d"] - k["stack_d"]) / (k["texit_d"] - k["tfw"])
    k["bd_d"] = 100 * k["cf_d"] / (k["cset"] - k["cf_d"])
    return k


# --- plain Python physics (also used by physics.py and the figures) ---------------------------------------------------
def _poly(c, x):
    return c[0] + c[1] * x + c[2] * x * x


def tsat(k, p_barg):
    import math
    return _poly(k["ts"], math.log(p_barg + k["patm"]))


def h_boil(k, p_barg):
    import math
    return _poly(k["hf"], math.log(p_barg + k["patm"]))


def h_steam(k, p_barg):
    import math
    return _poly(k["hg"], math.log(p_barg + k["patm"]))


def h_liq(k, t):
    a, b, c = k["liq"]
    return a * t + b * t * t + c * t ** 3


def t_liq(k, h):
    """Inverse of h_liq by Newton (for the economiser water outlet in the stand-in)."""
    t = h / 4.2
    for _ in range(20):
        a, b, c = k["liq"]
        t -= (h_liq(k, t) - h) / (a + 2 * b * t + 3 * c * t * t)
    return t


def siegert(k, t_fg, o2, t_air):
    f = k["f0"] + (k["f5"] - k["f0"]) * o2 / 5
    return f * (t_fg - t_air) / (k["co2m"] * (1 - o2 / 21))


def rad_loss(k, load):
    return k["rad"] / max(load, 0.2)


# --- Monitor expressions ----------------------------------------------------------------------------------------------
def _parts(twin):
    k = _k(twin)
    X = f"np.log(df['STEAM_PRESSURE_BARG'] + {k['patm']})"
    pl = lambda c: f"({c[0]} + {c[1]} * {X} + {c[2]} * {X} ** 2)"
    TS, HF, HG = pl(k["ts"]), pl(k["hf"]), pl(k["hg"])
    a, b, c = k["liq"]
    T = "df['FEED_TEMP_C']"
    HFW = f"({a} * {T} + {b} * {T} ** 2 + {c} * {T} ** 3)"
    LOAD = f"(df['STEAM_FLOW_KGH'] / {k['rated']})"
    LM = f"np.maximum({LOAD}, 0.2)"
    FUEL = f"(df['GAS_FLOW_NM3H'] * {k['lhv']} / 3.6)"
    BD = "(df['FEED_FLOW_KGH'] - df['STEAM_FLOW_KGH'])"
    QOUT = f"((df['STEAM_FLOW_KGH'] * ({HG} - {HFW}) + {BD} * ({HF} - {HFW})) / 3600)"
    df5 = (k["f5"] - k["f0"]) / 5

    def SG(tfg, o2):
        return f"(({k['f0']} + {df5!r} * {o2}) * ({tfg} - df['AIR_TEMP_C']) / ({k['co2m']} * (1 - {o2} / 21)))"
    RAD = f"({k['rad']} / {LM})"
    QA = SG("df['STACK_C']", "df['O2_PCT']")
    EIND = f"(100 - {QA} - {RAD})"
    EDIR = f"(100 * {QOUT} / {FUEL})"
    TEX = f"({TS} + {k['app']} * {LM} ** {k['appn']})"
    STX = f"({TEX} - {k['eps_d']!r} * ({TEX} - df['FEED_TEMP_C']))"
    EEXP = f"(100 - {SG(STX, k['o2d'])} - {RAD})"
    DPR = f"(df['FLUE_DP_MBAR'] / ({k['dp_d']} * {LM} ** {k['dpn']}))"
    ECO = "((df['FLUE_EXIT_C'] - df['STACK_C']) / (df['FLUE_EXIT_C'] - df['FEED_TEMP_C']))"
    return dict(k=k, TS=TS, HF=HF, HG=HG, HFW=HFW, LOAD=LOAD, FUEL=FUEL, BD=BD, QOUT=QOUT, QA=QA, EIND=EIND, EDIR=EDIR,
                TEX=TEX, STX=STX, EEXP=EEXP, DPR=DPR, ECO=ECO, RAD=RAD)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("TSAT_C", p["TS"]),
        ("H_STEAM_KJKG", p["HG"]),
        ("LOAD_PCT", f"100 * {p['LOAD']}"),
        ("FUEL_INPUT_KW", p["FUEL"]),
        ("BLOWDOWN_KGH", p["BD"]),
        ("BLOWDOWN_PCT", f"100 * {p['BD']} / df['STEAM_FLOW_KGH']"),
        ("HEAT_OUTPUT_KW", p["QOUT"]),
        ("EFF_DIRECT_PCT", p["EDIR"]),
        ("EXCESS_AIR_PCT", f"{k['eak']} * df['O2_PCT'] / (21 - df['O2_PCT'])"),
        ("FLUE_LOSS_PCT", p["QA"]),
        ("EFF_INDIRECT_PCT", p["EIND"]),
        ("EFF_EXPECTED_PCT", p["EEXP"]),
        ("EFF_GAP_PCT", f"{p['EDIR']} - {p['EIND']}"),
        ("EXIT_TEMP_RESIDUAL_K", f"df['FLUE_EXIT_C'] - {p['TEX']}"),
        ("FLUE_DP_RATIO", p["DPR"]),
        ("ECO_EFFECTIVENESS", p["ECO"]),
        ("STACK_RESIDUAL_K", f"df['STACK_C'] - {p['STX']}"),
        ("CYCLES_OF_CONCENTRATION", "df['BOILER_COND_USCM'] / df['FEED_COND_USCM']"),
        ("FEED_MARGIN_BAR", "df['FEED_PUMP_P_BARG'] - df['STEAM_PRESSURE_BARG']"),
        ("EXCESS_FUEL_KW", f"{p['FUEL']} * (1 - {p['EIND']} / {p['EEXP']})"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    load = r["steam_flow_kgh"] / k["rated"]
    lm = max(load, 0.2)
    ts, hb, hg, hfw = tsat(k, r["steam_pressure_barg"]), h_boil(k, r["steam_pressure_barg"]), h_steam(k, r["steam_pressure_barg"]), h_liq(k, r["feed_temp_c"])
    fuel = r["gas_flow_nm3h"] * k["lhv"] / 3.6
    bd = r["feed_flow_kgh"] - r["steam_flow_kgh"]
    qout = (r["steam_flow_kgh"] * (hg - hfw) + bd * (hb - hfw)) / 3600
    rad = k["rad"] / lm
    qa = siegert(k, r["stack_c"], r["o2_pct"], r["air_temp_c"])
    eind = 100 - qa - rad
    edir = 100 * qout / fuel
    tex = ts + k["app"] * lm ** k["appn"]
    stx = tex - k["eps_d"] * (tex - r["feed_temp_c"])
    eexp = 100 - siegert(k, stx, k["o2d"], r["air_temp_c"]) - rad
    return {
        "tsat_c": ts, "h_steam_kjkg": hg, "load_pct": 100 * load, "fuel_input_kw": fuel, "blowdown_kgh": bd,
        "blowdown_pct": 100 * bd / r["steam_flow_kgh"], "heat_output_kw": qout, "eff_direct_pct": edir,
        "excess_air_pct": k["eak"] * r["o2_pct"] / (21 - r["o2_pct"]), "flue_loss_pct": qa, "eff_indirect_pct": eind,
        "eff_expected_pct": eexp, "eff_gap_pct": edir - eind, "exit_temp_residual_k": r["flue_exit_c"] - tex,
        "flue_dp_ratio": r["flue_dp_mbar"] / (k["dp_d"] * lm ** k["dpn"]),
        "eco_effectiveness": (r["flue_exit_c"] - r["stack_c"]) / (r["flue_exit_c"] - r["feed_temp_c"]),
        "stack_residual_k": r["stack_c"] - stx, "cycles_of_concentration": r["boiler_cond_uscm"] / r["feed_cond_uscm"],
        "feed_margin_bar": r["feed_pump_p_barg"] - r["steam_pressure_barg"], "excess_fuel_kw": fuel * (1 - eind / eexp),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    EXR = f"(df['FLUE_EXIT_C'] - {p['TEX']})"
    BDN = "(100 * df['FEED_COND_USCM'] / (" + str(k["cset"]) + " - df['FEED_COND_USCM']))"
    return [
        ("BLR_CO_HIGH", f"df['CO_PPM'] > {k['co']}", "High", None),
        ("BLR_TDS_HIGH", f"df['BOILER_COND_USCM'] > {k['calert']}", "High", "tds_control_fault"),
        ("BLR_LEVEL_DEVIATION", f"np.abs(df['DRUM_LEVEL_MM']) > {k['lvl']}", "High", "feed_pump_wear"),
        ("BLR_HARDNESS", f"df['FEED_HARDNESS_MMOL'] > {k['hard']}", "High", "waterside_scale"),
        ("BLR_LWCO_TEST_OVERDUE", f"df['LWCO_TEST_HOURS_SINCE'] > {k['grace'] * k['lwco']}", "High", "safety_tests_overdue"),
        ("BLR_FIRESIDE_FOULING", f"({EXR} > {L['exit_residual_alert_k']}) & ({p['DPR']} > {L['flue_dp_ratio_alert']})", "Medium", "fireside_fouling"),
        ("BLR_WATERSIDE_SCALE", f"({EXR} > {L['exit_residual_alert_k']}) & ({p['DPR']} <= {L['flue_dp_ratio_alert']})", "Medium", "waterside_scale"),
        ("BLR_ECO_EFFECTIVENESS_LOW", f"{p['ECO']} < {L['eco_effectiveness_alert']}", "Medium", "economiser_fouling"),
        ("BLR_STACK_HIGH", f"(df['STACK_C'] - {p['STX']}) > {L['stack_residual_alert_k']}", "Medium", "economiser_fouling"),
        ("BLR_EXCESS_AIR_HIGH", f"df['O2_PCT'] > {L['o2_high_alert_pct']}", "Medium", "excess_air_high"),
        ("BLR_EFF_LOW", f"{p['EIND']} < {p['EEXP']} - {L['eff_drop_alert_pct']}", "Medium", "excess_air_high"),
        ("BLR_EFF_MISMATCH", f"np.abs({p['EDIR']} - {p['EIND']}) > {L['eff_gap_alert_pct']}", "Medium", None),
        ("BLR_BLOWDOWN_HIGH", f"(100 * {p['BD']} / df['STEAM_FLOW_KGH']) > {L['blowdown_factor_alert']} * {BDN}", "Medium", "blowdown_valve_passing"),
        ("BLR_FEED_MARGIN_LOW", f"(df['FEED_PUMP_P_BARG'] - df['STEAM_PRESSURE_BARG']) < {k['marg']}", "Medium", "feed_pump_wear"),
        ("BLR_SV_TEST_OVERDUE", f"df['SV_TEST_HOURS_SINCE'] > {k['grace'] * k['sv']}", "Medium", "safety_tests_overdue"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    exr, dpr = t["exit_temp_residual_k"], t["flue_dp_ratio"]
    bdn = 100 * r["feed_cond_uscm"] / (k["cset"] - r["feed_cond_uscm"])
    add(r["co_ppm"] > k["co"], "BLR_CO_HIGH", "High", f"CO {r['co_ppm']:.0f} ppm: incomplete combustion, check the burner air", "burner")
    add(r["boiler_cond_uscm"] > k["calert"], "BLR_TDS_HIGH", "High",
        f"Boiler water {r['boiler_cond_uscm']:.0f} µS/cm, above {k['calert']:.0f}: foaming and carry-over risk", "blowdown", "tds_control_fault")
    add(abs(r["drum_level_mm"]) > k["lvl"], "BLR_LEVEL_DEVIATION", "High",
        f"Water level {r['drum_level_mm']:+.0f} mm from normal: level control cannot hold it", "feed pump", "feed_pump_wear")
    add(r["feed_hardness_mmol"] > k["hard"], "BLR_HARDNESS", "High",
        f"Feedwater hardness {r['feed_hardness_mmol']:.3f} mmol/l: softener breakthrough, scale forming", "water side", "waterside_scale")
    add(r["lwco_test_hours_since"] > k["grace"] * k["lwco"], "BLR_LWCO_TEST_OVERDUE", "High",
        f"Low-water limiters last tested {r['lwco_test_hours_since']:.0f} h ago (interval {k['lwco']:.0f} h)", "safety devices", "safety_tests_overdue")
    add(exr > L["exit_residual_alert_k"] and dpr > L["flue_dp_ratio_alert"], "BLR_FIRESIDE_FOULING", "Medium",
        f"Boiler exit {exr:+.0f} K above a clean boiler, gas-side dp {dpr:.2f} x expected: soot in the tubes", "smoke tubes", "fireside_fouling")
    add(exr > L["exit_residual_alert_k"] and dpr <= L["flue_dp_ratio_alert"], "BLR_WATERSIDE_SCALE", "Medium",
        f"Boiler exit {exr:+.0f} K above a clean boiler with a normal gas-side dp: scale on the water side", "water side", "waterside_scale")
    add(t["eco_effectiveness"] < L["eco_effectiveness_alert"], "BLR_ECO_EFFECTIVENESS_LOW", "Medium",
        f"Economiser effectiveness {t['eco_effectiveness']:.2f} (design {k['eps_d']:.2f})", "economiser", "economiser_fouling")
    add(t["stack_residual_k"] > L["stack_residual_alert_k"], "BLR_STACK_HIGH", "Medium",
        f"Stack {r['stack_c']:.0f} °C, {t['stack_residual_k']:+.0f} K above expected", "economiser", "economiser_fouling")
    add(r["o2_pct"] > L["o2_high_alert_pct"], "BLR_EXCESS_AIR_HIGH", "Medium",
        f"O2 {r['o2_pct']:.1f} % (excess air {t['excess_air_pct']:.0f} %), design {k['o2d']:.1f} %", "burner", "excess_air_high")
    add(t["eff_indirect_pct"] < t["eff_expected_pct"] - L["eff_drop_alert_pct"], "BLR_EFF_LOW", "Medium",
        f"Efficiency {t['eff_indirect_pct']:.1f} % against {t['eff_expected_pct']:.1f} % expected: {t['excess_fuel_kw']:.0f} kW of extra fuel", "boiler", "excess_air_high")
    add(abs(t["eff_gap_pct"]) > L["eff_gap_alert_pct"], "BLR_EFF_MISMATCH", "Medium",
        f"Direct {t['eff_direct_pct']:.1f} % vs indirect {t['eff_indirect_pct']:.1f} %: check the gas and steam meters", "meters")
    add(t["blowdown_pct"] > L["blowdown_factor_alert"] * bdn, "BLR_BLOWDOWN_HIGH", "Medium",
        f"Blowdown {t['blowdown_pct']:.1f} % of steam, the water chemistry needs {bdn:.1f} %", "blowdown", "blowdown_valve_passing")
    add(t["feed_margin_bar"] < k["marg"], "BLR_FEED_MARGIN_LOW", "Medium",
        f"Feed pump only {t['feed_margin_bar']:.1f} bar above the boiler pressure", "feed pump", "feed_pump_wear")
    add(r["sv_test_hours_since"] > k["grace"] * k["sv"], "BLR_SV_TEST_OVERDUE", "Medium",
        f"Safety valves last lifted {r['sv_test_hours_since']:.0f} h ago (interval {k['sv']:.0f} h)", "safety devices", "safety_tests_overdue")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
