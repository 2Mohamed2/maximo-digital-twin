"""The traction motor twin's expectations (TM-5401, motor 1 of a Siemens Vectron AC locomotive, 6.4 MW, Bo'Bo').

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Tractive effort (per motor = locomotive / 4):
    available effort   F_av = min(F_start, P x 3.6 / v)           constant effort up to the base speed, then constant power
    expected effort    F_exp = demand / 100 x F_av                 the driver's demand is a share of what is available
    measured effort    F_meas = torque x gear x eta_gear / r_wheel  from the torque the inverter estimates
    wheel speed        v_w = rpm / gear x pi x D x 60 / 10^6 (km/h)  creep = (v_w - v) / max(v, 5) x 100 %
  net creep = creep - creep measured while coasting (a wrong wheel-diameter parameter shows in both and cancels out)
Current per torque (induction motor, rotor flux control):
    I_exp = sqrt( (I_m x min(1, n_b/n))^2 + (k_t x max(1, n/n_b) x T)^2 )   field weakening above the base speed n_b
Winding thermal model (steady state on the 30-minute thermal RMS current, so no history is needed in Monitor):
    T_stator,exp = T_air + rise_rated x (I_rms30 / I_rated)^2 x (flow_rated / flow)^0.8
    ageing rate  = 2 ^ ((T_stator + hot-spot allowance - T_ref) / 10)      (10 K halving rule; 1 = design ageing)
Bearings: T_DE,exp = T_air + rise_max x rpm_avg30 / rpm_max ;  BPFO = rpm/60 x z/2 x (1 - d/D_p)
Insulation: IR at 40 C = IR x 2 ^ ((T_test - 40) / 10)
Inverter: T_baseplate,exp = T_coolant + R_th x P_loss,  P_loss = P_rated,loss x (s x i + (1 - s) x i^2),  i = I_rms5 / I_rated
    IGBT power cycling (LESIT): N_f = A x dTj^-alpha x exp(Ea / (kB x (Tm + 273.15)));  life (years) = N_f / (cycles per day x 365)
"""
import math


def _k(twin):
    d = twin["design"]
    m, th, b, ins, cv = d["motor"], d["thermal"], d["bearings"], d["insulation"], d["converter"]
    return dict(P=m["power_kw"], F0=m["start_te_kn"], g=m["gear_ratio"], eg=m["gear_eff"], ir=m["rated_current_a"], im=m["magnetising_a"],
                nb=m["base_rpm"], nmax=m["max_rpm"], tr=m["rated_torque_knm"], kt=m["kt_a_per_knm"],
                air=th["air_nominal_c"], rise=th["rise_rated_k"], fr=th["flow_rated_pct"], fx=th["flow_exponent"], hs=th["hotspot_allowance_k"],
                tref=th["life_ref_c"], half=th["halving_k"], cls=th["insulation_class_c"], clife=th["class_life_h"],
                bk=b["rise_at_max_k"], z=b["rollers"], bd=b["roller_d_mm"], bp=b["pitch_d_mm"],
                irhalf=ins["ir_halving_k"], ir_new=ins["ir_new_40c_mohm"],
                lr=cv["loss_rated_kw"], ls=cv["loss_linear_share"], rth=cv["rth_k_per_kw"], la=cv["lesit_a"], lal=cv["lesit_alpha"],
                eakb=cv["lesit_ea_j"] / cv["kb_j_per_k"], life=cv["design_life_years"])


def _c(k):
    """Constants folded once, used identically by the pandas expressions and by evaluate()."""
    return dict(ws=math.pi * 60 / (k["g"] * 1e6), te=k["g"] * k["eg"] * 2000, pv=k["P"] * 3.6, bpfo=k["z"] / 2 * (1 - k["bd"] / k["bp"]) / 60,
                brg=k["bk"] / k["nmax"], igbt=k["rth"] * k["lr"])


def nf_lesit(k, swing, mean_c):
    return k["la"] * swing ** -k["lal"] * math.exp(k["eakb"] / (mean_c + 273.15))


def te_available(k, v):
    return min(k["F0"], k["P"] * 3.6 / max(v, 1))


def _parts(twin):
    k = _k(twin)
    c = _c(k)
    L = twin["twin_model"]["limits"]
    WS = f"(df['MOTOR_RPM'] * {c['ws']!r} * df['WHEEL_D_MM'])"
    CR = f"(({WS} - df['SPEED_KMH']) / np.maximum(df['SPEED_KMH'], 5) * 100)"
    CN = f"({CR} - df['CREEP_COAST_PCT'])"
    TA = f"np.minimum({k['F0']!r}, {c['pv']!r} / np.maximum(df['SPEED_KMH'], 1))"
    TE = f"(df['DEMAND_PCT'] / 100 * {TA})"
    TM = f"(df['MOTOR_TORQUE_KNM'] * {c['te']!r} / df['WHEEL_D_MM'])"
    N = "np.maximum(df['MOTOR_RPM'], 1)"
    IE = (f"np.sqrt(({k['im']!r} * np.minimum(1, {k['nb']!r} / {N})) ** 2 + ({k['kt']!r} * np.maximum(1, {N} / {k['nb']!r})"
          f" * np.abs(df['MOTOR_TORQUE_KNM'])) ** 2)")
    SE = f"(df['AIR_IN_C'] + {k['rise']!r} * (df['CURRENT_RMS30_A'] / {k['ir']!r}) ** 2 * ({k['fr']!r} / np.maximum(df['BLOWER_FLOW_PCT'], 10)) ** {k['fx']!r})"
    AG = f"(2 ** ((df['STATOR_C'] + {k['hs']!r} - {k['tref']!r}) / {k['half']!r}))"
    BE = f"(df['AIR_IN_C'] + {c['brg']!r} * df['RPM_AVG30'])"
    I5 = f"(df['CURRENT_RMS5_A'] / {k['ir']!r})"
    GE = f"(df['COOLANT_C'] + {c['igbt']!r} * ({k['ls']!r} * {I5} + {1 - k['ls']!r} * {I5} ** 2))"
    NF = f"({k['la']!r} * df['IGBT_TJ_SWING_K'] ** -{k['lal']!r} * np.exp({k['eakb']!r} / (df['IGBT_TJ_MEAN_C'] + 273.15)))"
    LY = f"({NF} / (np.maximum(df['IGBT_CYCLES_DAY'], 1) * 365))"
    return dict(k=k, c=c, L=L, WS=WS, CR=CR, CN=CN, TA=TA, TE=TE, TM=TM, IE=IE, SE=SE, AG=AG, BE=BE, GE=GE, NF=NF, LY=LY)


def monitor_expressions(twin):
    p = _parts(twin)
    k, c, L = p["k"], p["c"], p["L"]
    return [
        ("WHEEL_SPEED_KMH", p["WS"]),
        ("CREEP_PCT", p["CR"]),
        ("CREEP_NET_PCT", p["CN"]),
        ("TE_AVAILABLE_KN", p["TA"]),
        ("TE_EXPECTED_KN", p["TE"]),
        ("TE_MEASURED_KN", p["TM"]),
        ("TE_RATIO", f"np.where({p['TE']} > {L['te_min_kn']!r}, {p['TM']} / np.maximum({p['TE']}, {L['te_min_kn']!r}), 1.0)"),
        ("CURRENT_EXPECTED_A", p["IE"]),
        ("CURRENT_RATIO", f"df['MOTOR_CURRENT_A'] / {p['IE']}"),
        ("STATOR_EXPECTED_C", p["SE"]),
        ("STATOR_RESIDUAL_K", f"df['STATOR_C'] - {p['SE']}"),
        ("AGING_RATE", p["AG"]),
        ("BEARING_DE_EXPECTED_C", p["BE"]),
        ("BEARING_DE_RESIDUAL_K", f"df['BEARING_DE_C'] - {p['BE']}"),
        ("BPFO_HZ", f"df['MOTOR_RPM'] * {c['bpfo']!r}"),
        ("IR_40C_MOHM", f"df['IR_MOHM'] * 2 ** ((df['IR_TEMP_C'] - 40) / {k['irhalf']!r})"),
        ("IGBT_BASEPLATE_EXPECTED_C", p["GE"]),
        ("IGBT_BASEPLATE_RESIDUAL_K", f"df['IGBT_BASEPLATE_C'] - {p['GE']}"),
        ("IGBT_CYCLES_TO_FAILURE", p["NF"]),
        ("IGBT_LIFE_YEARS", p["LY"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    c = _c(k)
    L = twin["twin_model"]["limits"]
    ws = r["motor_rpm"] * c["ws"] * r["wheel_d_mm"]
    cr = (ws - r["speed_kmh"]) / max(r["speed_kmh"], 5) * 100
    ta = min(k["F0"], c["pv"] / max(r["speed_kmh"], 1))
    te = r["demand_pct"] / 100 * ta
    tm = r["motor_torque_knm"] * c["te"] / r["wheel_d_mm"]
    n = max(r["motor_rpm"], 1)
    ie = math.sqrt((k["im"] * min(1, k["nb"] / n)) ** 2 + (k["kt"] * max(1, n / k["nb"]) * abs(r["motor_torque_knm"])) ** 2)
    se = r["air_in_c"] + k["rise"] * (r["current_rms30_a"] / k["ir"]) ** 2 * (k["fr"] / max(r["blower_flow_pct"], 10)) ** k["fx"]
    be = r["air_in_c"] + c["brg"] * r["rpm_avg30"]
    i5 = r["current_rms5_a"] / k["ir"]
    ge = r["coolant_c"] + c["igbt"] * (k["ls"] * i5 + (1 - k["ls"]) * i5 ** 2)
    nf = k["la"] * r["igbt_tj_swing_k"] ** -k["lal"] * math.exp(k["eakb"] / (r["igbt_tj_mean_c"] + 273.15))
    return {
        "wheel_speed_kmh": ws, "creep_pct": cr, "creep_net_pct": cr - r["creep_coast_pct"],
        "te_available_kn": ta, "te_expected_kn": te, "te_measured_kn": tm,
        "te_ratio": tm / max(te, L["te_min_kn"]) if te > L["te_min_kn"] else 1.0,
        "current_expected_a": ie, "current_ratio": r["motor_current_a"] / ie,
        "stator_expected_c": se, "stator_residual_k": r["stator_c"] - se,
        "aging_rate": 2 ** ((r["stator_c"] + k["hs"] - k["tref"]) / k["half"]),
        "bearing_de_expected_c": be, "bearing_de_residual_k": r["bearing_de_c"] - be,
        "bpfo_hz": r["motor_rpm"] * c["bpfo"],
        "ir_40c_mohm": r["ir_mohm"] * 2 ** ((r["ir_temp_c"] - 40) / k["irhalf"]),
        "igbt_baseplate_expected_c": ge, "igbt_baseplate_residual_k": r["igbt_baseplate_c"] - ge,
        "igbt_cycles_to_failure": nf, "igbt_life_years": nf / (max(r["igbt_cycles_day"], 1) * 365),
    }


def alert_rules(twin):
    p = _parts(twin)
    k, L = p["k"], p["L"]
    TR = f"({p['TM']} / np.maximum({p['TE']}, {L['te_min_kn']!r}))"
    return [
        ("TM_TE_SHORTFALL", f"({p['TE']} > {L['te_min_kn']!r}) & ({TR} < {L['te_ratio_alert']!r}) & ({p['CN']} <= {L['creep_alert_pct']!r})", "High", "rotor_cage_damage"),
        ("TM_INSULATION_LOW", f"(df['IR_MOHM'] * 2 ** ((df['IR_TEMP_C'] - 40) / {k['irhalf']!r})) < {L['ir_40c_min_mohm']!r}", "High", "insulation_moisture"),
        ("TM_BEARING_HOT", f"(df['BEARING_DE_C'] - {p['BE']}) > {L['bearing_residual_alert_k']!r}", "High", "bearing_lubrication"),
        ("TM_IGBT_HOT", f"(df['IGBT_BASEPLATE_C'] - {p['GE']}) > {L['igbt_residual_alert_k']!r}", "High", "inverter_cooling"),
        ("TM_AGING_FAST", f"{p['AG']} > {L['aging_rate_alert']!r}", "Medium", "cooling_ducts_blocked"),
        ("TM_WINDING_RESIDUAL", f"((df['STATOR_C'] - {p['SE']}) > {L['winding_residual_alert_k']!r}) & (df['CURRENT_RMS30_A'] > {L['load_min_frac'] * k['ir']!r})", "Medium", "cooling_ducts_blocked"),
        ("TM_VENT_FLOW_LOW", f"df['BLOWER_FLOW_PCT'] < {L['vent_flow_alert_pct']!r}", "Medium", "blower_degraded"),
        ("TM_BEARING_ENVELOPE", f"df['ENV_BPFO_G'] > {L['envelope_alert_g']!r}", "Medium", "bearing_outer_race"),
        ("TM_WHEEL_SLIP", f"({p['CN']} > {L['creep_alert_pct']!r}) & (df['DEMAND_PCT'] > 5)", "Medium", "low_adhesion"),
        ("TM_SLIP_EVENTS", f"df['SLIP_EVENTS_100KM'] > {L['slip_events_alert']!r}", "Medium", "low_adhesion"),
        ("TM_CURRENT_HIGH", f"((df['MOTOR_CURRENT_A'] / {p['IE']}) > {L['current_ratio_alert']!r}) & (np.abs(df['MOTOR_TORQUE_KNM']) > {0.2 * k['tr']!r})", "Medium", "rotor_cage_damage"),
        ("TM_IGBT_LIFE_SHORT", f"{p['LY']} < {L['igbt_life_alert_years']!r}", "Medium", "inverter_cooling"),
        ("TM_CREEP_OFFSET", f"np.abs(df['CREEP_COAST_PCT']) > {L['creep_offset_alert_pct']!r}", "Low", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    te, tr = t["te_expected_kn"], t["te_measured_kn"] / max(t["te_expected_kn"], L["te_min_kn"])
    add(te > L["te_min_kn"] and tr < L["te_ratio_alert"] and t["creep_net_pct"] <= L["creep_alert_pct"], "TM_TE_SHORTFALL", "High",
        f"Effort {t['te_measured_kn']:.1f} kN for {te:.1f} kN demanded ({tr * 100:.0f} %) with normal creep", "rotor", "rotor_cage_damage")
    add(t["ir_40c_mohm"] < L["ir_40c_min_mohm"], "TM_INSULATION_LOW", "High",
        f"Insulation resistance {t['ir_40c_mohm']:.0f} MΩ at 40 °C, below {L['ir_40c_min_mohm']:.0f} MΩ", "stator", "insulation_moisture")
    add(t["bearing_de_residual_k"] > L["bearing_residual_alert_k"], "TM_BEARING_HOT", "High",
        f"Drive-end bearing {r['bearing_de_c']:.0f} °C, {t['bearing_de_residual_k']:.0f} K above what the speed explains", "bearing", "bearing_lubrication")
    add(t["igbt_baseplate_residual_k"] > L["igbt_residual_alert_k"], "TM_IGBT_HOT", "High",
        f"IGBT baseplate {r['igbt_baseplate_c']:.0f} °C, {t['igbt_baseplate_residual_k']:.0f} K above what the current explains", "inverter", "inverter_cooling")
    add(t["aging_rate"] > L["aging_rate_alert"], "TM_AGING_FAST", "Medium",
        f"Insulation ageing {t['aging_rate']:.1f} × the design rate (winding {r['stator_c']:.0f} °C)", "stator", "cooling_ducts_blocked")
    add(t["stator_residual_k"] > L["winding_residual_alert_k"] and r["current_rms30_a"] > L["load_min_frac"] * k["ir"], "TM_WINDING_RESIDUAL", "Medium",
        f"Winding {r['stator_c']:.0f} °C, {t['stator_residual_k']:.0f} K above what load and air flow explain", "stator", "cooling_ducts_blocked")
    add(r["blower_flow_pct"] < L["vent_flow_alert_pct"], "TM_VENT_FLOW_LOW", "Medium",
        f"Blower flow {r['blower_flow_pct']:.0f} % of rated", "blower", "blower_degraded")
    add(r["env_bpfo_g"] > L["envelope_alert_g"], "TM_BEARING_ENVELOPE", "Medium",
        f"Envelope {r['env_bpfo_g']:.2f} g at the outer-race frequency ({t['bpfo_hz']:.0f} Hz)", "bearing", "bearing_outer_race")
    add(t["creep_net_pct"] > L["creep_alert_pct"] and r["demand_pct"] > 5, "TM_WHEEL_SLIP", "Medium",
        f"Creep {t['creep_net_pct']:.1f} % under traction (normal below {L['creep_alert_pct']:.0f} %)", "wheelset", "low_adhesion")
    add(r["slip_events_100km"] > L["slip_events_alert"], "TM_SLIP_EVENTS", "Medium",
        f"{r['slip_events_100km']:.0f} slip corrections in the last 100 km", "wheelset", "low_adhesion")
    add(t["current_ratio"] > L["current_ratio_alert"] and abs(r["motor_torque_knm"]) > 0.2 * k["tr"], "TM_CURRENT_HIGH", "Medium",
        f"Current {r['motor_current_a']:.0f} A, {t['current_ratio']:.2f} × what the torque needs", "rotor", "rotor_cage_damage")
    add(t["igbt_life_years"] < L["igbt_life_alert_years"], "TM_IGBT_LIFE_SHORT", "Medium",
        f"IGBT power-cycling life {t['igbt_life_years']:.0f} years at the present cycles (design {k['life']:.0f})", "inverter", "inverter_cooling")
    add(abs(r["creep_coast_pct"]) > L["creep_offset_alert_pct"], "TM_CREEP_OFFSET", "Low",
        f"Creep {r['creep_coast_pct']:.1f} % while coasting: check the wheel diameter parameter", "wheelset")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
