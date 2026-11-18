"""The slurry pump twin's expectations (SP-4101, Warman 8/6 AH tailings pump on a VSD).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Slurry (from the density gauge and the last lab d50):
    Cv = (SG - 1) / (Ss - 1)            solids by volume          Cw = 100 Cv Ss / SG   solids by mass, %
    HR = 1 - 0.000385 (Ss - 1)(1 + 4/Ss) Cw ln(d50[mm] / 0.0227)   Warman correction; ER = HR
Clear-water curve at the live speed (affinity laws, s = n / n_ref):
    Qref = Q / s,  x = Qref / Q_BEP      Hw = s^2 (a + b Qref + c Qref^2)      eta_w = eta_BEP (2x - x^2)
Expected slurry head and efficiency at the measured flow and speed:   H_exp = HR Hw,  eta_exp = HR eta_w
Measured head from the two pressure gauges, in metres of slurry:      H = (Pd - Ps) / (g SG)
    head ratio = H / H_exp: 1 for a pump as new, lower as the impeller-throatbush gap opens (wear).
    wear rate = (1 - head ratio) x 100 / (hours since the last adjustment / 1000): % head lost per 1000 h.
Power: expected VSD power = SG g Q H_exp / (3600 eta_exp eta_drive) kW; measured efficiency = (Pd - Ps) Q / 3600 / (kW eta_drive).
Line: velocity V = Q / (3600 A); Durand limit deposit velocity VL = FL sqrt(2 g D (Ss - 1)); deposition margin = V / VL.
Suction: NPSHa = (Ps + Patm - Pv) / (g SG); NPSHr = s^2 (r0 + r2 x^2); margin = NPSHa / NPSHr.
Gland: gland water pressure - discharge pressure (must stay positive, by a margin). Bearings: hotter one minus ambient.
Each expression works on one reading (Monitor keeps no state for the twin); the hours since the adjustment come from the plant.
"""
import math

G = 9.80665


def _g(x):
    """A constant as written into the Monitor expression (8 significant digits), so Python and pandas use the same number."""
    return float(f"{x:.8g}")


def _k(twin):
    d = twin["design"]
    p, s, ln, dr, si, gl = d["pump"], d["slurry"], d["line"], d["drive"], d["site"], d["gland"]
    ss = s["solids_sg"]
    area = math.pi / 4 * ln["id_m"] ** 2
    return dict(n0=p["ref_speed_rpm"], a=p["head_coef"][0], b=p["head_coef"][1], c=p["head_coef"][2], qbep=p["q_bep_m3h"],
                eta=p["eff_bep"], r0=p["npshr_coef"][0], r2=p["npshr_coef"][1], ss=ss, sf=s["carrier_sg"],
                cwar=_g(s["warman_k"] * (ss - s["carrier_sg"]) * (1 + 4 / ss)), sgmax=s["sg_max"],
                area=area, vl=_g(ln["durand_fl"] * math.sqrt(2 * G * ln["id_m"] * (ss - 1))), D=ln["id_m"], fl=ln["durand_fl"],
                kw=dr["motor_kw"], ed=dr["drive_eff"], patm=si["patm_kpa"], pv=si["vapour_kpa"],
                gmin=gl["flow_min_lpm"], gmax=gl["flow_max_lpm"], gdp=gl["dp_min_kpa"])


# shared pure-Python helpers (physics.py and the figures use them too) -------------------------------------------------
def warman_hr(k, cw_pct, d50_um):
    return 1 - k["cwar"] * cw_pct * math.log(max(d50_um / 1000 / 0.0227, 1.0))


def cw_of_sg(k, sg):
    return 100 * (sg - 1) / (k["ss"] - 1) * k["ss"] / sg


def water_head(k, q, n):
    s = max(n, 1.0) / k["n0"]
    qr = q / s
    return s * s * (k["a"] + k["b"] * qr + k["c"] * qr * qr)


def water_eff(k, q, n):
    x = q / (max(n, 1.0) / k["n0"]) / k["qbep"]
    return k["eta"] * (2 * x - x * x)


def npshr(k, q, n):
    s = max(n, 1.0) / k["n0"]
    x = q / s / k["qbep"]
    return s * s * (k["r0"] + k["r2"] * x * x)


def _parts(twin):
    k = _k(twin)
    SG = "df['DENSITY_SG']"
    CW = f"(100 * ({SG} - 1) / {k['ss'] - 1:.8g} * {k['ss']} / {SG})"
    HR = f"(1 - {k['cwar']} * {CW} * np.log(np.maximum(df['D50_UM'] / {1000 * 0.0227:.8g}, 1)))"
    S = f"(np.maximum(df['SPEED_RPM'], 1) / {k['n0']})"
    QR = f"(df['FLOW_M3H'] / {S})"
    X = f"({QR} / {k['qbep']})"
    HW = f"({S} ** 2 * ({k['a']} + {k['b']} * {QR} + {k['c']:.8g} * {QR} ** 2))"
    HE = f"({HR} * {HW})"
    HM = f"((df['DISCHARGE_KPA'] - df['SUCTION_KPA']) / ({G} * {SG}))"
    HRAT = f"({HM} / {HE})"
    EE = f"(100 * {HR} * {k['eta']} * (2 * {X} - {X} ** 2))"
    PE = f"({SG} * {G} * df['FLOW_M3H'] / 3600 * {HE} / ({EE} / 100) / {k['ed']})"
    V = f"(df['FLOW_M3H'] / 3600 / {_g(k['area'])})"
    DM = f"({V} / {k['vl']})"
    NA = f"((df['SUCTION_KPA'] + {_g(k['patm'] - k['pv'])}) / ({G} * {SG}))"
    NR = f"({S} ** 2 * ({k['r0']} + {k['r2']} * {X} ** 2))"
    WR = f"((1 - {HRAT}) * 100 / np.maximum(df['HOURS_SINCE_ADJUST'] / 1000, 0.1))"
    return dict(k=k, CW=CW, HR=HR, QR=QR, X=X, HW=HW, HE=HE, HM=HM, HRAT=HRAT, EE=EE, PE=PE, V=V, DM=DM, NA=NA, NR=NR, WR=WR)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("CW_SOLIDS_PCT", p["CW"]),
        ("SLURRY_HR", p["HR"]),
        ("FLOW_REF_M3H", p["QR"]),
        ("BEP_RATIO", p["X"]),
        ("HEAD_WATER_EXPECTED_M", p["HW"]),
        ("HEAD_EXPECTED_M", p["HE"]),
        ("HEAD_MEASURED_M", p["HM"]),
        ("HEAD_RATIO", p["HRAT"]),
        ("EFF_EXPECTED_PCT", p["EE"]),
        ("PUMP_EFF_PCT", f"(df['DISCHARGE_KPA'] - df['SUCTION_KPA']) * df['FLOW_M3H'] / 3600 / (np.maximum(df['MOTOR_KW'], 0.1) * {k['ed']}) * 100"),
        ("POWER_EXPECTED_KW", p["PE"]),
        ("MOTOR_LOAD_PCT", f"df['MOTOR_KW'] / {k['kw']} * 100"),
        ("LINE_VELOCITY_MS", p["V"]),
        ("DEPOSITION_MARGIN", p["DM"]),
        ("NPSH_AVAILABLE_M", p["NA"]),
        ("NPSH_REQUIRED_M", p["NR"]),
        ("NPSH_MARGIN", f"{p['NA']} / {p['NR']}"),
        ("GLAND_DP_KPA", "df['GLAND_KPA'] - df['DISCHARGE_KPA']"),
        ("BEARING_RISE_K", "np.maximum(df['BEARING_DE_C'], df['BEARING_NDE_C']) - df['AMBIENT_C']"),
        ("WEAR_RATE_PCT_KH", p["WR"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    sg = r["density_sg"]
    cw = 100 * (sg - 1) / _g(k["ss"] - 1) * k["ss"] / sg
    hr = 1 - k["cwar"] * cw * math.log(max(r["d50_um"] / _g(1000 * 0.0227), 1))
    s = max(r["speed_rpm"], 1) / k["n0"]
    qr = r["flow_m3h"] / s
    x = qr / k["qbep"]
    hw = s ** 2 * (k["a"] + k["b"] * qr + _g(k["c"]) * qr ** 2)
    he = hr * hw
    hm = (r["discharge_kpa"] - r["suction_kpa"]) / (G * sg)
    hrat = hm / he
    ee = 100 * hr * k["eta"] * (2 * x - x ** 2)
    v = r["flow_m3h"] / 3600 / _g(k["area"])
    na = (r["suction_kpa"] + _g(k["patm"] - k["pv"])) / (G * sg)
    nr = s ** 2 * (k["r0"] + k["r2"] * x ** 2)
    return {
        "cw_solids_pct": cw, "slurry_hr": hr, "flow_ref_m3h": qr, "bep_ratio": x, "head_water_expected_m": hw,
        "head_expected_m": he, "head_measured_m": hm, "head_ratio": hrat, "eff_expected_pct": ee,
        "pump_eff_pct": (r["discharge_kpa"] - r["suction_kpa"]) * r["flow_m3h"] / 3600 / (max(r["motor_kw"], 0.1) * k["ed"]) * 100,
        "power_expected_kw": sg * G * r["flow_m3h"] / 3600 * he / (ee / 100) / k["ed"],
        "motor_load_pct": r["motor_kw"] / k["kw"] * 100, "line_velocity_ms": v, "deposition_margin": v / k["vl"],
        "npsh_available_m": na, "npsh_required_m": nr, "npsh_margin": na / nr,
        "gland_dp_kpa": r["gland_kpa"] - r["discharge_kpa"],
        "bearing_rise_k": max(r["bearing_de_c"], r["bearing_nde_c"]) - r["ambient_c"],
        "wear_rate_pct_kh": (1 - hrat) * 100 / max(r["hours_since_adjust"] / 1000, 0.1),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    RUN = "(df['RUNNING'] > 0.5)"
    HRAT, DM, X = p["HRAT"], p["DM"], p["X"]
    return [
        ("SLY_DEPOSITION_RISK", f"{RUN} & ({DM} < 1)", "High", "line_sanding"),
        ("SLY_HEAD_LOSS_HIGH", f"{RUN} & ({HRAT} < {L['head_loss']})", "High", "impeller_wear"),
        ("SLY_NPSH_LOW", f"{RUN} & (({p['NA']} / {p['NR']}) < {L['npsh_margin']})", "High", "suction_blockage"),
        ("SLY_GLAND_PRESSURE_LOW", f"{RUN} & ((df['GLAND_KPA'] - df['DISCHARGE_KPA']) < {k['gdp']})", "High", "gland_water_loss"),
        ("SLY_BEARING_TEMP_HIGH", f"(np.maximum(df['BEARING_DE_C'], df['BEARING_NDE_C']) - df['AMBIENT_C']) > {L['bearing_rise_k']}", "High", "bearing_failure"),
        ("SLY_MOTOR_OVERLOAD", f"df['MOTOR_KW'] > {k['kw']}", "High", None),
        ("SLY_DEPOSITION_MARGIN", f"{RUN} & ({DM} >= 1) & ({DM} < {L['deposition_margin']})", "Medium", "line_sanding"),
        ("SLY_HEAD_LOW", f"{RUN} & ({HRAT} >= {L['head_loss']}) & ({HRAT} < {L['head_low']})", "Medium", "impeller_wear"),
        ("SLY_WEAR_RATE_HIGH", f"{RUN} & (df['HOURS_SINCE_ADJUST'] > {L['wear_min_hours']}) & ({p['WR']} > {L['wear_rate_pct_kh']})", "Medium", "impeller_wear"),
        ("SLY_BEP_LOW", f"{RUN} & ({X} < {L['bep_min']})", "Medium", "line_sanding"),
        ("SLY_BEP_HIGH", f"{RUN} & ({X} > {L['bep_max']})", "Medium", None),
        ("SLY_GLAND_FLOW_LOW", f"{RUN} & (df['GLAND_FLOW_LPM'] < {k['gmin']})", "Medium", "gland_water_loss"),
        ("SLY_GLAND_FLOW_HIGH", f"df['GLAND_FLOW_LPM'] > {k['gmax']}", "Medium", "packing_wear"),
        ("SLY_VIBRATION_HIGH", f"df['VIBRATION_MMS'] > {L['vibration_mms']}", "Medium", "bearing_failure"),
        ("SLY_DENSITY_HIGH", f"df['DENSITY_SG'] > {k['sgmax']}", "Medium", "density_high"),
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
    hr, dm, x = t["head_ratio"], t["deposition_margin"], t["bep_ratio"]
    add(run and dm < 1, "SLY_DEPOSITION_RISK", "High",
        f"Line velocity {t['line_velocity_ms']:.2f} m/s, below the Durand limit {k['vl']:.2f} m/s: solids settle, the line can sand up", "discharge line", "line_sanding")
    add(run and hr < L["head_loss"], "SLY_HEAD_LOSS_HIGH", "High",
        f"Head {hr * 100:.0f} % of the derated curve at {r['speed_rpm']:.0f} rpm and {r['flow_m3h']:.0f} m³/h: adjust the throatbush or change the wet end", "wet end", "impeller_wear")
    add(run and t["npsh_margin"] < L["npsh_margin"], "SLY_NPSH_LOW", "High",
        f"NPSH available {t['npsh_available_m']:.1f} m, only {t['npsh_margin']:.2f} × required (suction {r['suction_kpa']:.0f} kPa g)", "suction", "suction_blockage")
    add(run and t["gland_dp_kpa"] < k["gdp"], "SLY_GLAND_PRESSURE_LOW", "High",
        f"Gland water {r['gland_kpa']:.0f} kPa, {t['gland_dp_kpa']:+.0f} kPa against discharge {r['discharge_kpa']:.0f} kPa: slurry gets into the packing", "gland", "gland_water_loss")
    add(t["bearing_rise_k"] > L["bearing_rise_k"], "SLY_BEARING_TEMP_HIGH", "High",
        f"Bearing {t['bearing_rise_k']:.0f} K above ambient (DE {r['bearing_de_c']:.0f} °C, NDE {r['bearing_nde_c']:.0f} °C)", "bearings", "bearing_failure")
    add(r["motor_kw"] > k["kw"], "SLY_MOTOR_OVERLOAD", "High", f"VSD power {r['motor_kw']:.0f} kW, above the {k['kw']:.0f} kW motor rating", "drive")
    add(run and 1 <= dm < L["deposition_margin"], "SLY_DEPOSITION_MARGIN", "Medium",
        f"Line velocity {t['line_velocity_ms']:.2f} m/s, only {dm:.2f} × the Durand limit", "discharge line", "line_sanding")
    add(run and L["head_loss"] <= hr < L["head_low"], "SLY_HEAD_LOW", "Medium",
        f"Head {hr * 100:.0f} % of the derated curve at {r['speed_rpm']:.0f} rpm and {r['flow_m3h']:.0f} m³/h", "wet end", "impeller_wear")
    add(run and r["hours_since_adjust"] > L["wear_min_hours"] and t["wear_rate_pct_kh"] > L["wear_rate_pct_kh"], "SLY_WEAR_RATE_HIGH", "Medium",
        f"Head lost {t['wear_rate_pct_kh']:.1f} % per 1000 h since the last adjustment ({r['hours_since_adjust']:.0f} h ago)", "wet end", "impeller_wear")
    add(run and x < L["bep_min"], "SLY_BEP_LOW", "Medium", f"Running at {x * 100:.0f} % of BEP flow: recirculation and wear in the wet end", "pump", "line_sanding")
    add(run and x > L["bep_max"], "SLY_BEP_HIGH", "Medium", f"Running at {x * 100:.0f} % of BEP flow", "pump")
    add(run and r["gland_flow_lpm"] < k["gmin"], "SLY_GLAND_FLOW_LOW", "Medium", f"Gland water {r['gland_flow_lpm']:.1f} L/min, below {k['gmin']:.0f}", "gland", "gland_water_loss")
    add(r["gland_flow_lpm"] > k["gmax"], "SLY_GLAND_FLOW_HIGH", "Medium", f"Gland water {r['gland_flow_lpm']:.0f} L/min, above {k['gmax']:.0f}: packing or sleeve worn", "gland", "packing_wear")
    add(r["vibration_mms"] > L["vibration_mms"], "SLY_VIBRATION_HIGH", "Medium", f"Bearing housing vibration {r['vibration_mms']:.1f} mm/s", "bearings", "bearing_failure")
    add(r["density_sg"] > k["sgmax"], "SLY_DENSITY_HIGH", "Medium",
        f"Slurry SG {r['density_sg']:.2f} ({t['cw_solids_pct']:.0f} % solids), above the design {k['sgmax']:.2f}", "process", "density_high")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
