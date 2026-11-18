"""The electric submersible pump twin's expectations (ESP-2801, Centrilift 400FLEXPump17.5 stages on a VSD).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Pump curve at the VSD frequency (affinity laws, f = VSD frequency, fr = f / 60 Hz):
    Q60 = Q / fr                                  the flow the same impeller speed-ratio gives at 60 Hz
    H(Q, f) = N x fr^2 x (a + b Q60 + c Q60^2)    published stage curve, N stages
    P(Q, f) = N x fr^3 x (p0 + p1 Q60) x SG       brake horsepower
  Recommended range scales with fr too: 500 x fr to 2,600 x fr bbl/d; BEP ratio = Q60 / 1,750.
Measured head from the gauge: H = (Pd - PIP) / (0.433 x SG), SG of the oil-water mix from the water cut.
  head ratio = measured / expected: wear and scale lower it at the same flow; gas lowers it too, but makes the current erratic.
Power: expected VSD output kW = P x 0.7457 / (motor efficiency x cable efficiency); power ratio = measured / expected.
Intake: fluid over pump = (PIP - casing pressure) / (0.433 x SG oil);
  free gas at the intake (GVF): Rs = Rsb x min(PIP / Pb, 1), free gas = (GOR - Rs) x (1 - WC) scf per bbl liquid,
  Bg = 0.00504 z T / p bbl/scf, a gas separator removes a fraction; GVF = Vg / (Vg + 1).
Motor cooling: fluid velocity past the motor v = Q / annulus area (casing ID, motor OD);
  expected rise above intake = rise_ref x (load / load_ref) x sqrt(v_ref / max(v, v_min)).
Insulation: leakage corrected to a reference temperature, halving per 18 °F (10 °C): leak / 2^((T - Tref) / 18).
Each expression works on one reading (Monitor keeps no state for the twin); counters (run days, starts) come from the VSD.
"""
import math

GRAD = 0.433        # psi per ft of fresh water
HHP = 135770.0      # Q[bbl/d] x H[ft] x SG / 135,770 = hydraulic hp
KW = 0.7457         # kW per hp
BBL_FT3 = 5.615


def _g(x):
    """A constant as written into the Monitor expression (8 significant digits), so Python and pandas use the same number."""
    return float(f"{x:.8g}")


def _k(twin):
    d = twin["design"]
    p, m, w, fl = d["pump"], d["motor"], d["well"], d["fluid"]
    area = math.pi / 4 * (w["casing_id_in"] ** 2 - m["od_in"] ** 2) / 144.0
    return dict(N=p["stages"], qmin=p["q_min_bpd"], qmax=p["q_max_bpd"], qbep=p["q_bep_bpd"], a=p["head_coef"][0], b=p["head_coef"][1],
                c=p["head_coef"][2], p0=p["power_coef"][0], p1=p["power_coef"][1], hp=m["rated_hp_60hz"], eff=m["eff"], ceff=m["cable_eff"],
                tlim=m["temp_limit_f"], rref=m["rise_ref_f"], lref=m["load_ref"], vref=m["v_ref_fts"], vmin=m["v_min_fts"],
                depth=w["pump_depth_ft"], perf=w["perf_depth_ft"], pr=w["reservoir_psi"], area=area,
                sgo=fl["sg_oil"], sgw=fl["sg_water"], rsb=fl["rsb_scf_stb"], pb=fl["pb_psi"], z=fl["z"], sep=fl["gas_sep_eff"],
                gvf=fl["gvf_limit_pct"])


# shared pure-Python helpers (physics.py and the figures use them too) -------------------------------------------------
def stage_head(k, q60):
    return k["a"] + k["b"] * q60 + k["c"] * q60 * q60


def stage_bhp(k, q60):
    return k["p0"] + k["p1"] * q60


def pump_head(k, q, f):
    fr = max(f, 1.0) / 60.0
    return k["N"] * fr * fr * stage_head(k, q / fr)


def gvf_pct(k, pip, gor, wc, tin):
    rs = k["rsb"] * min(pip / k["pb"], 1.0)
    vg = (1 - k["sep"]) * (1 - wc / 100) * max(gor - rs, 0.0) * 0.00504 * k["z"] * (tin + 460) / (pip + 14.7)
    return 100 * vg / (vg + 1)


def motor_rise(k, load_pct, v):
    return k["rref"] * (load_pct / 100 / k["lref"]) * math.sqrt(k["vref"] / max(v, k["vmin"]))


def _parts(twin):
    k = _k(twin)
    F = "np.maximum(df['VSD_FREQ_HZ'], 1)"
    FR = f"({F} / 60)"
    Q60 = f"(df['FLOW_BPD'] / {FR})"
    SG = f"(df['WATER_CUT_PCT'] / 100 * {k['sgw']} + (1 - df['WATER_CUT_PCT'] / 100) * {k['sgo']})"
    HM = f"((df['PD_PSI'] - df['PIP_PSI']) / ({GRAD} * {SG}))"
    HE = f"np.maximum({k['N']} * {FR} ** 2 * ({k['a']} + {k['b']} * {Q60} + {k['c']} * {Q60} ** 2), 1)"
    HR = f"({HM} / {HE})"
    BR = f"({Q60} / {k['qbep']})"
    PE = f"({k['N']} * ({k['p0']} + {k['p1']} * {Q60}) * {FR} ** 3 * {SG} * {KW / (k['eff'] * k['ceff']):.8g})"
    SHAFT = f"(np.maximum(df['VSD_KW'], 0.1) * {k['eff'] * k['ceff'] / KW:.8g})"
    LOAD = f"(df['VSD_KW'] * {k['eff'] * k['ceff'] / KW:.8g} / ({k['hp']} * {FR}) * 100)"
    VG = (f"({(1 - k['sep']) * 0.00504 * k['z']:.8g} * (1 - df['WATER_CUT_PCT'] / 100) * np.maximum(df['GOR_SCF_STB'] - {k['rsb']} * "
          f"np.minimum(df['PIP_PSI'] / {k['pb']}, 1), 0) * (df['INTAKE_TEMP_F'] + 460) / (df['PIP_PSI'] + 14.7))")
    V = f"(df['FLOW_BPD'] * {BBL_FT3 / 86400 / k['area']:.8g})"
    RISE = "(df['MOTOR_TEMP_F'] - df['INTAKE_TEMP_F'])"
    REXP = f"({k['rref'] / k['lref']:.8g} * {LOAD} / 100 * np.sqrt({k['vref']} / np.maximum({V}, {k['vmin']})))"
    LC = f"(df['LEAKAGE_UA'] / np.power(2, (df['MOTOR_TEMP_F'] - {twin['twin_model']['limits']['leak_ref_f']}) / 18))"
    PWF = f"(df['PIP_PSI'] + {GRAD} * {SG} * {k['perf'] - k['depth']})"
    return dict(k=k, FR=FR, Q60=Q60, SG=SG, HM=HM, HE=HE, HR=HR, BR=BR, PE=PE, SHAFT=SHAFT, LOAD=LOAD, VG=VG, V=V, RISE=RISE, REXP=REXP, LC=LC, PWF=PWF)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("FLOW_60HZ_BPD", p["Q60"]),
        ("SG_MIX", p["SG"]),
        ("HEAD_MEASURED_FT", p["HM"]),
        ("HEAD_EXPECTED_FT", p["HE"]),
        ("HEAD_RATIO", p["HR"]),
        ("BEP_RATIO", p["BR"]),
        ("POWER_EXPECTED_KW", p["PE"]),
        ("POWER_RATIO", f"df['VSD_KW'] / {p['PE']}"),
        ("LOAD_PCT", p["LOAD"]),
        ("PUMP_EFF_PCT", f"df['FLOW_BPD'] * {p['HM']} * {p['SG']} / {HHP} / {p['SHAFT']} * 100"),
        ("FLUID_OVER_PUMP_FT", f"(df['PIP_PSI'] - df['CASING_PSI']) / ({GRAD} * {k['sgo']})"),
        ("PI_BPD_PSI", f"df['FLOW_BPD'] / np.maximum({k['pr']} - {p['PWF']}, 1)"),
        ("INTAKE_GVF_PCT", f"100 * {p['VG']} / ({p['VG']} + 1)"),
        ("MOTOR_VELOCITY_FTS", p["V"]),
        ("MOTOR_RISE_F", p["RISE"]),
        ("MOTOR_RISE_EXPECTED_F", p["REXP"]),
        ("MOTOR_RISE_RATIO", f"{p['RISE']} / np.maximum({p['REXP']}, 1)"),
        ("LEAKAGE_CORR_UA", p["LC"]),
        ("RUN_LIFE_YEARS", "df['RUN_DAYS'] / 365.25"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    L = twin["twin_model"]["limits"]
    fr = max(r["vsd_freq_hz"], 1) / 60
    q, wc = r["flow_bpd"], r["water_cut_pct"]
    q60 = q / fr
    sg = wc / 100 * k["sgw"] + (1 - wc / 100) * k["sgo"]
    hm = (r["pd_psi"] - r["pip_psi"]) / (GRAD * sg)
    he = max(k["N"] * fr ** 2 * (k["a"] + k["b"] * q60 + k["c"] * q60 ** 2), 1)
    pe = k["N"] * (k["p0"] + k["p1"] * q60) * fr ** 3 * sg * _g(KW / (k["eff"] * k["ceff"]))
    shaft = max(r["vsd_kw"], 0.1) * _g(k["eff"] * k["ceff"] / KW)
    load = r["vsd_kw"] * _g(k["eff"] * k["ceff"] / KW) / (k["hp"] * fr) * 100
    vg = (_g((1 - k["sep"]) * 0.00504 * k["z"]) * (1 - wc / 100) * max(r["gor_scf_stb"] - k["rsb"] * min(r["pip_psi"] / k["pb"], 1), 0)
          * (r["intake_temp_f"] + 460) / (r["pip_psi"] + 14.7))
    v = q * _g(BBL_FT3 / 86400 / k["area"])
    rise = r["motor_temp_f"] - r["intake_temp_f"]
    rexp = _g(k["rref"] / k["lref"]) * load / 100 * math.sqrt(k["vref"] / max(v, k["vmin"]))
    pwf = r["pip_psi"] + GRAD * sg * (k["perf"] - k["depth"])
    return {
        "flow_60hz_bpd": q60, "sg_mix": sg, "head_measured_ft": hm, "head_expected_ft": he, "head_ratio": hm / he,
        "bep_ratio": q60 / k["qbep"], "power_expected_kw": pe, "power_ratio": r["vsd_kw"] / pe, "load_pct": load,
        "pump_eff_pct": q * hm * sg / HHP / shaft * 100,
        "fluid_over_pump_ft": (r["pip_psi"] - r["casing_psi"]) / (GRAD * k["sgo"]),
        "pi_bpd_psi": q / max(k["pr"] - pwf, 1),
        "intake_gvf_pct": 100 * vg / (vg + 1), "motor_velocity_fts": v, "motor_rise_f": rise, "motor_rise_expected_f": rexp,
        "motor_rise_ratio": rise / max(rexp, 1),
        "leakage_corr_ua": r["leakage_ua"] / 2 ** ((r["motor_temp_f"] - L["leak_ref_f"]) / 18),
        "run_life_years": r["run_days"] / 365.25,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    HR, BR, CV, RUN = p["HR"], p["BR"], "df['CURRENT_CV_PCT']", "(df['RUNNING'] > 0.5)"
    LC = p["LC"]
    lo = k["qmin"] / k["qbep"]
    return [
        ("ESP_SHAFT_BROKEN", f"{RUN} & ({HR} < {L['head_broken']}) & ({p['LOAD']} < {L['load_broken_pct']}) & ({CV} <= {L['cv_pct']})", "Critical", "broken_shaft"),
        ("ESP_GAS_LOCK", f"{RUN} & ({BR} < {lo:.8g}) & ({CV} > {L['cv_pct']})", "High", "gas_interference"),
        ("ESP_HEAD_LOSS_HIGH", f"{RUN} & ({HR} >= {L['head_broken']}) & ({HR} < {L['head_loss']}) & ({CV} <= {L['cv_pct']})", "High", "stage_wear"),
        ("ESP_INSULATION_LOW", f"{LC} > {L['leak_limit_ua']}", "High", "motor_insulation"),
        ("ESP_MOTOR_TEMP_LIMIT", f"df['MOTOR_TEMP_F'] > {k['tlim']}", "High", "motor_cooling"),
        ("ESP_HEAD_LOW", f"{RUN} & ({HR} >= {L['head_loss']}) & ({HR} < {L['head_low']}) & ({CV} <= {L['cv_pct']})", "Medium", "scale_deposits"),
        ("ESP_POWER_HIGH", f"{RUN} & ((df['VSD_KW'] / {p['PE']}) > {L['power_high']})", "Medium", "scale_deposits"),
        ("ESP_VIBRATION_HIGH", f"df['VIBRATION_G'] > {L['vibration_g']}", "Medium", "stage_wear"),
        ("ESP_CURRENT_UNSTABLE", f"{RUN} & ({CV} > {L['cv_pct']})", "Medium", "gas_interference"),
        ("ESP_GAS_HIGH", f"(100 * {p['VG']} / ({p['VG']} + 1)) > {k['gvf']}", "Medium", "gas_interference"),
        ("ESP_DOWNTHRUST", f"{RUN} & ({BR} < {lo:.8g}) & ({CV} <= {L['cv_pct']}) & ({HR} >= {L['head_broken']})", "Medium", "inflow_decline"),
        ("ESP_LOW_SUBMERGENCE", f"((df['PIP_PSI'] - df['CASING_PSI']) / ({GRAD} * {k['sgo']})) < {L['submergence_ft']}", "Medium", "inflow_decline"),
        ("ESP_MOTOR_COOLING", f"{RUN} & (({p['RISE']} / np.maximum({p['REXP']}, 1)) > {L['motor_rise_ratio']})", "Medium", "motor_cooling"),
        ("ESP_LEAKAGE_RISING", f"({LC} > {L['leak_rising_x'] * L['leak_base_ua']:.8g}) & ({LC} <= {L['leak_limit_ua']})", "Medium", "motor_insulation"),
        ("ESP_RESTARTS_HIGH", f"df['STARTS_30D'] > {L['starts_30d']}", "Medium", "gas_interference"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    run = r["running"] > 0.5
    hr, br, cv, lc = t["head_ratio"], t["bep_ratio"], r["current_cv_pct"], t["leakage_corr_ua"]
    lo = _g(k["qmin"] / k["qbep"])
    steady = cv <= L["cv_pct"]
    add(run and hr < L["head_broken"] and t["load_pct"] < L["load_broken_pct"] and steady, "ESP_SHAFT_BROKEN", "Critical",
        f"Head {hr * 100:.0f} % of expected with the motor at {t['load_pct']:.0f} % load and a steady current: shaft or coupling broken", "pump", "broken_shaft")
    add(run and br < lo and cv > L["cv_pct"], "ESP_GAS_LOCK", "High",
        f"Flow {r['flow_bpd']:.0f} bbl/d, below the range at {r['vsd_freq_hz']:.0f} Hz, with the current fluctuating {cv:.1f} %: gas lock", "intake", "gas_interference")
    add(run and L["head_broken"] <= hr < L["head_loss"] and steady, "ESP_HEAD_LOSS_HIGH", "High",
        f"Pump head {hr * 100:.0f} % of the curve at {r['flow_bpd']:.0f} bbl/d and {r['vsd_freq_hz']:.1f} Hz", "pump", "stage_wear")
    add(lc > L["leak_limit_ua"], "ESP_INSULATION_LOW", "High", f"Current leakage {lc:.1f} µA at {L['leak_ref_f']:.0f} °F, above {L['leak_limit_ua']:.0f} µA", "motor", "motor_insulation")
    add(r["motor_temp_f"] > k["tlim"], "ESP_MOTOR_TEMP_LIMIT", "High", f"Motor at {r['motor_temp_f']:.0f} °F, above {k['tlim']:.0f} °F", "motor", "motor_cooling")
    add(run and L["head_loss"] <= hr < L["head_low"] and steady, "ESP_HEAD_LOW", "Medium",
        f"Pump head {hr * 100:.0f} % of the curve at {r['flow_bpd']:.0f} bbl/d and {r['vsd_freq_hz']:.1f} Hz", "pump", "scale_deposits")
    add(run and t["power_ratio"] > L["power_high"], "ESP_POWER_HIGH", "Medium",
        f"VSD power {r['vsd_kw']:.1f} kW, {t['power_ratio']:.2f} × the curve at this flow", "pump", "scale_deposits")
    add(r["vibration_g"] > L["vibration_g"], "ESP_VIBRATION_HIGH", "Medium", f"Gauge vibration {r['vibration_g']:.2f} g", "pump", "stage_wear")
    add(run and cv > L["cv_pct"], "ESP_CURRENT_UNSTABLE", "Medium", f"Motor current fluctuates {cv:.1f} % (std / mean over a minute)", "motor", "gas_interference")
    add(t["intake_gvf_pct"] > k["gvf"], "ESP_GAS_HIGH", "Medium",
        f"Free gas at the intake {t['intake_gvf_pct']:.1f} %, above {k['gvf']:.0f} % (PIP {r['pip_psi']:.0f} psi, GOR {r['gor_scf_stb']:.0f})", "intake", "gas_interference")
    add(run and br < lo and steady and hr >= L["head_broken"], "ESP_DOWNTHRUST", "Medium",
        f"Flow {r['flow_bpd']:.0f} bbl/d is {br * 100:.0f} % of BEP, below the recommended range: downthrust", "pump", "inflow_decline")
    add(t["fluid_over_pump_ft"] < L["submergence_ft"], "ESP_LOW_SUBMERGENCE", "Medium",
        f"Only {t['fluid_over_pump_ft']:.0f} ft of fluid over the pump (PIP {r['pip_psi']:.0f} psi)", "well", "inflow_decline")
    add(run and t["motor_rise_ratio"] > L["motor_rise_ratio"], "ESP_MOTOR_COOLING", "Medium",
        f"Motor {t['motor_rise_f']:.0f} °F above the well fluid, {t['motor_rise_ratio']:.1f} × the {t['motor_rise_expected_f']:.0f} °F expected", "motor", "motor_cooling")
    add(_g(L["leak_rising_x"] * L["leak_base_ua"]) < lc <= L["leak_limit_ua"], "ESP_LEAKAGE_RISING", "Medium",
        f"Current leakage {lc:.1f} µA at {L['leak_ref_f']:.0f} °F, {lc / L['leak_base_ua']:.1f} × commissioning", "motor", "motor_insulation")
    add(r["starts_30d"] > L["starts_30d"], "ESP_RESTARTS_HIGH", "Medium", f"{r['starts_30d']:.0f} starts in 30 days", "drive", "gas_interference")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
