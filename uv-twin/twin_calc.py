"""The UV reactor twin's expectations (TrojanUVSwiftSC D12, 12 LPHO amalgam lamps; US EPA UVDGM calculated-dose approach).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (twin viewer, tests)

Dose (reduction-equivalent dose, RED, mJ/cm2) - calculated-dose form (UVDGM 3.x / 6.x):
  UVA        = -log10(UVT / 100)                         UV absorbance of the water, 1 cm, 254 nm
  TS         = 10^(-UVA Ls)                              transmission through the water layer in front of the sensor (Ls cm)
  Phi        = (1 - 10^(-UVA w)) / (UVA w ln10)          mean transmission over the mean water layer w (Beer-Lambert average)
  G          = Phi / TS                                  how much more the water as a whole sees than the sensor says
  RED        = Kc (S / S0) G / Q                         S = lower of the two UV sensors (the validated dose uses the worst one)
  Kc is fixed so the design point (650 m3/h, UVT 94 %) gets 40 mJ/cm2 with the end-of-lamp-life (0.80) and fouling (0.90)
  factors (this is the twin's calibration of the form, not Trojan's validation equation).
Expected UV intensity (what clean sleeves would let the sensors see):
  S_exp      = S0 x (lamp power / installed lamp power) x age factor(lamp hours) x 0.97 (clean sleeve) x TS
  The expectation uses the *measured* lamp power, so dose pacing (60-100 %) and a derating ballast do not look like fouling;
  it uses the lamp hours, so lamp ageing does not either; and UVT, so dirty water does not either. What is left in
  measured / expected is the sleeves (and the sensor windows).
Credit: log inactivation from UVDGM Table 1.4, read between the table points, 4-log at most.
"""
import math

import numpy as np


def _k(twin):
    d = twin["design"]
    m, r, v = d["dose_model"], d["reactor"], d["validation"]
    ct = d["credit_table"]
    return dict(Kc=m["Kc"], S0=m["S0_wm2"], Ls=m["Ls_cm"], w=m["w_cm"], n=r["lamps"], kw=r["lamp_kw"],
                life=d["lamp_ageing"]["life_h"], eol=d["lamp_ageing"]["eol_factor"], clean=d["clean_sleeve_factor"],
                req=v["required_dose_mjcm2"], qmax=v["validated_flow_max_m3h"], uvtmin=v["validated_uvt_min_pct"],
                cdose=ct["dose_mjcm2"], clog=ct["log"])


def g_factor(k, uvt):
    uva = max(-math.log10(uvt / 100), 1e-4)
    ts = 10 ** (-uva * k["Ls"])
    phi = (1 - 10 ** (-uva * k["w"])) / (uva * k["w"] * math.log(10))
    return uva, ts, phi / ts


def age_factor(k, hours):
    return max(1 - (1 - k["eol"]) * hours / k["life"], 0.3)


def dose(k, s, uvt, q):
    _, _, g = g_factor(k, uvt)
    return min(k["Kc"] * (s / k["S0"]) * g / max(q, 10), 999)


def _parts(twin):
    k = _k(twin)
    UVA = "(-np.log10(df['UVT_PCT'] / 100)).clip(lower=0.0001)"
    TS = f"np.power(10.0, -{UVA} * {k['Ls']})"
    PHI = f"((1 - np.power(10.0, -{UVA} * {k['w']})) / ({UVA} * {k['w'] * math.log(10)}))"
    G = f"({PHI} / {TS})"
    Q = "df['FLOW_M3H'].clip(lower=10)"
    SMIN = "np.minimum(df['UV_INTENSITY_1_WM2'], df['UV_INTENSITY_2_WM2'])"
    SMEAN = "((df['UV_INTENSITY_1_WM2'] + df['UV_INTENSITY_2_WM2']) / 2)"
    AGE = f"(1 - {1 - k['eol']} * df['LAMP_HOURS'] / {k['life']}).clip(lower=0.3)"
    PFRAC = f"(df['LAMP_POWER_KW'] / {k['n'] * k['kw']})"
    SEXP = f"({k['S0']} * {PFRAC} * {AGE} * {k['clean']} * {TS})"
    DOSE = f"np.minimum({k['Kc']} * ({SMIN} / {k['S0']}) * {G} / {Q}, 999)"
    DEXP = f"np.minimum({k['Kc']} * ({SEXP} / {k['S0']}) * {G} / {Q}, 999)"
    RATIO = f"({SMEAN} / {SEXP}.clip(lower=0.1))"
    SRATIO = "(df['UV_INTENSITY_1_WM2'] / df['UV_INTENSITY_2_WM2'].clip(lower=0.1))"
    PEXP = f"({k['kw']} * df['LAMPS_ON'] * df['BALLAST_POWER_PCT'] / 100)"
    BDEV = f"((df['LAMP_POWER_KW'] / {PEXP}.clip(lower=0.01) - 1) * 100)"
    OFF = "(df['OFFSPEC_MONTH_M3'] / df['VOLUME_MONTH_M3'].clip(lower=1) * 100)"
    return dict(UVA=UVA, TS=TS, G=G, Q=Q, SMIN=SMIN, SMEAN=SMEAN, AGE=AGE, SEXP=SEXP, DOSE=DOSE, DEXP=DEXP, RATIO=RATIO,
                SRATIO=SRATIO, PEXP=PEXP, BDEV=BDEV, OFF=OFF, k=k)


def monitor_expressions(twin):
    p, k = _parts(twin), _k(twin)
    ct = k["cdose"]
    return [
        ("UVA_PER_CM", p["UVA"]),
        ("DOSE_CALC_MJCM2", p["DOSE"]),
        ("DOSE_EXPECTED_MJCM2", p["DEXP"]),
        ("DOSE_MARGIN_PCT", f"({p['DOSE']} / {k['req']} - 1) * 100"),
        ("INTENSITY_MEAN_WM2", p["SMEAN"]),
        ("INTENSITY_EXPECTED_WM2", p["SEXP"]),
        ("INTENSITY_RATIO", p["RATIO"]),
        ("SENSOR_RATIO", p["SRATIO"]),
        ("AGE_FACTOR", p["AGE"]),
        ("LAMP_POWER_EXPECTED_KW", p["PEXP"]),
        ("BALLAST_DEV_PCT", p["BDEV"]),
        ("REACTOR_TEMP_EXPECTED_C", f"df['WATER_TEMP_C'] + df['LAMP_POWER_KW'] / (1.163 * df['FLOW_M3H'].clip(lower=1))"),
        ("LOG_CRYPTO", f"np.interp({p['DOSE']}, {ct['crypto']}, {k['clog']})"),
        ("LOG_GIARDIA", f"np.interp({p['DOSE']}, {ct['giardia']}, {k['clog']})"),
        ("LOG_VIRUS", f"np.interp({p['DOSE']}, {ct['virus']}, {k['clog']})"),
        ("OFFSPEC_MONTH_PCT", p["OFF"]),
        ("ENERGY_KWH_PER_M3", "df['LAMP_POWER_KW'] / df['FLOW_M3H'].clip(lower=1)"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    uva, ts, g = g_factor(k, r["uvt_pct"])
    q = max(r["flow_m3h"], 10)
    s1, s2 = r["uv_intensity_1_wm2"], r["uv_intensity_2_wm2"]
    smin, smean = min(s1, s2), (s1 + s2) / 2
    age = age_factor(k, r["lamp_hours"])
    sexp = k["S0"] * (r["lamp_power_kw"] / (k["n"] * k["kw"])) * age * k["clean"] * ts
    d = min(k["Kc"] * (smin / k["S0"]) * g / q, 999)
    dexp = min(k["Kc"] * (sexp / k["S0"]) * g / q, 999)
    pexp = k["kw"] * r["lamps_on"] * r["ballast_power_pct"] / 100
    ct = k["cdose"]
    return {
        "uva_per_cm": uva, "dose_calc_mjcm2": d, "dose_expected_mjcm2": dexp, "dose_margin_pct": (d / k["req"] - 1) * 100,
        "intensity_mean_wm2": smean, "intensity_expected_wm2": sexp, "intensity_ratio": smean / max(sexp, 0.1),
        "sensor_ratio": s1 / max(s2, 0.1), "age_factor": age, "lamp_power_expected_kw": pexp,
        "ballast_dev_pct": (r["lamp_power_kw"] / max(pexp, 0.01) - 1) * 100,
        "reactor_temp_expected_c": r["water_temp_c"] + r["lamp_power_kw"] / (1.163 * max(r["flow_m3h"], 1)),
        "log_crypto": float(np.interp(d, ct["crypto"], k["clog"])), "log_giardia": float(np.interp(d, ct["giardia"], k["clog"])),
        "log_virus": float(np.interp(d, ct["virus"], k["clog"])),
        "offspec_month_pct": r["offspec_month_m3"] / max(r["volume_month_m3"], 1) * 100,
        "energy_kwh_per_m3": r["lamp_power_kw"] / max(r["flow_m3h"], 1),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p, k = _parts(twin), _k(twin)
    RUN = "(df['REACTOR_STATUS'] != 2)"
    return [
        ("UV_LOW_DOSE", f"({p['DOSE']} < {k['req']}) & (df['FLOW_M3H'] > {L['no_flow_m3h']})", "High", None),
        ("UV_OFF_SPEC_MONTH", f"{p['OFF']} > {L['offspec_month_alert_pct']}", "High", None),
        ("UV_LOW_UVT", f"df['UVT_PCT'] < {k['uvtmin']}", "High", "uvt_drop"),
        ("UV_HIGH_FLOW", f"df['FLOW_M3H'] > {k['qmax']}", "High", "high_flow"),
        ("UV_LAMP_FAILURE", f"(df['LAMPS_ON'] < {k['n']}) & {RUN}", "High", "lamp_failure"),
        ("UV_LAMP_END_OF_LIFE", f"df['LAMP_HOURS'] > {k['life']}", "Low", "lamp_end_of_life"),
        ("UV_SLEEVE_FOULING", f"({p['RATIO']} < {L['intensity_ratio_alert']}) & (df['LAMPS_ON'] > 0) & {RUN}", "Medium", "sleeve_fouling"),
        ("UV_WIPER_FAULT", "df['WIPER_STATUS'] == 2", "Medium", "sleeve_fouling"),
        ("UV_SENSOR_DRIFT", f"(({p['SRATIO']} - 1).abs() > {L['sensor_ratio_tol']}) & (df['LAMPS_ON'] == {k['n']}) & {RUN}", "Medium", "sensor_drift"),
        ("UV_BALLAST_FAULT", f"(({p['BDEV']} < {L['ballast_dev_alert_pct']}) & (df['LAMPS_ON'] > 0) & (df['BALLAST_POWER_PCT'] > 0)) | "
                             f"(df['BALLAST_TEMP_C'] > {L['ballast_temp_alert_c']})", "Medium", "ballast_fault"),
        ("UV_NO_FLOW", f"(df['FLOW_M3H'] < {L['no_flow_m3h']}) & (df['LAMPS_ON'] > 0)", "Medium", "no_flow_overheat"),
        ("UV_OVERHEAT", f"(df['REACTOR_TEMP_C'] > {L['reactor_temp_alert_c']}) | (df['REACTOR_STATUS'] == 2)", "Critical", "no_flow_overheat"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []
    run = r["reactor_status"] != 2

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    add(r["reactor_temp_c"] > L["reactor_temp_alert_c"] or r["reactor_status"] == 2, "UV_OVERHEAT", "Critical",
        f"Reactor {r['reactor_temp_c']:.0f} °C" + (" - lamps shut down on high temperature" if r["reactor_status"] == 2 else f" (alert {L['reactor_temp_alert_c']} °C)"),
        "chamber", "no_flow_overheat")
    add(t["dose_calc_mjcm2"] < k["req"] and r["flow_m3h"] > L["no_flow_m3h"], "UV_LOW_DOSE", "High",
        f"Validated dose {t['dose_calc_mjcm2']:.1f} mJ/cm² below {k['req']:.0f}: water is off-specification", "chamber")
    add(t["offspec_month_pct"] > L["offspec_month_alert_pct"], "UV_OFF_SPEC_MONTH", "High",
        f"{t['offspec_month_pct']:.1f} % of this month's water off-specification (limit 5 %)", "controller")
    add(r["uvt_pct"] < k["uvtmin"], "UV_LOW_UVT", "High", f"UVT {r['uvt_pct']:.1f} % below the validated {k['uvtmin']} %", "uvt", "uvt_drop")
    add(r["flow_m3h"] > k["qmax"], "UV_HIGH_FLOW", "High", f"Flow {r['flow_m3h']:.0f} m³/h above the validated {k['qmax']}", "inlet", "high_flow")
    add(r["lamps_on"] < k["n"] and run, "UV_LAMP_FAILURE", "High", f"{k['n'] - r['lamps_on']} of {k['n']} lamps out", "lamps", "lamp_failure")
    add(r["lamp_hours"] > k["life"], "UV_LAMP_END_OF_LIFE", "Low",
        f"Lamps at {r['lamp_hours']:.0f} h, past {k['life']:.0f} h (age factor {t['age_factor']:.2f})", "lamps", "lamp_end_of_life")
    add(t["intensity_ratio"] < L["intensity_ratio_alert"] and r["lamps_on"] > 0 and run, "UV_SLEEVE_FOULING", "Medium",
        f"UV intensity {t['intensity_ratio']:.2f} x what clean sleeves give at this power, lamp age and UVT", "sleeves", "sleeve_fouling")
    add(r["wiper_status"] == 2, "UV_WIPER_FAULT", "Medium", "Sleeve wiper fault (drive stalled)", "wiper", "sleeve_fouling")
    add(abs(t["sensor_ratio"] - 1) > L["sensor_ratio_tol"] and r["lamps_on"] == k["n"] and run, "UV_SENSOR_DRIFT", "Medium",
        f"Sensor 1 / sensor 2 = {t['sensor_ratio']:.2f} with all lamps lit", "sensor1", "sensor_drift")
    add((t["ballast_dev_pct"] < L["ballast_dev_alert_pct"] and r["lamps_on"] > 0 and r["ballast_power_pct"] > 0)
        or r["ballast_temp_c"] > L["ballast_temp_alert_c"], "UV_BALLAST_FAULT", "Medium",
        f"Lamp power {t['ballast_dev_pct']:+.0f} % vs. setpoint, ballast {r['ballast_temp_c']:.0f} °C", "panel", "ballast_fault")
    add(r["flow_m3h"] < L["no_flow_m3h"] and r["lamps_on"] > 0, "UV_NO_FLOW", "Medium",
        f"Flow {r['flow_m3h']:.0f} m³/h with {r['lamps_on']} lamps on", "inlet", "no_flow_overheat")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
