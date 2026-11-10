"""The overhead line twin's expectations (OHL-901, ACSR Drake 795 kcmil 26/7, IEEE 738 heat balance, sag-tension).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (twin viewer, tests)

Heat balance (IEEE Std 738, SI form), per metre of conductor:
  I^2 R(Tc) + qs  =  qc + qr                                  (steady state)
  m Cp dTc/dt     =  I^2 R(Tc) + qs - qc - qr                 (transient, physics.py)
  R(Tc)   AC resistance, linear between 25 and 75 C (Southwire data; see the twin file)
  qs      solar heat gain = absorptivity x global irradiance x D  (simplified: the weather station's pyranometer
          replaces the IEEE solar-position model; labelled in the twin file)
  qc      convective cooling = max(forced qc1, forced qc2, natural qcn) with the wind-direction factor K_angle
            qc1 = K (1.01 + 1.35 Re^0.52) kf (Tc - Ta)      qc2 = K 0.754 Re^0.6 kf (Tc - Ta)
            qcn = 3.645 rho^0.5 D^0.75 (Tc - Ta)^1.25        Re = D rho V / mu
            K   = 1.194 - cos(phi) + 0.194 cos(2 phi) + 0.368 sin(2 phi), phi = wind angle to the conductor axis
            air properties mu, rho, kf at the film temperature (IEEE 738 polynomials)
  qr      radiative cooling = 17.8 D emissivity [((Tc+273)/100)^4 - ((Ta+273)/100)^4]

What Monitor computes (single 5-minute readings, no iteration inside an expression):
  DLR_A              dynamic line rating at the maximum operating temperature (75 C): closed form
                     I = sqrt((qc + qr - qs) / R(75)) with the live weather; the same at 100 C (emergency)
  TC_EXPECTED_C      steady conductor temperature for the live current and weather. Because R(Tc) is linear, the
                     balance h(Tc) (Tc - Ta) = I^2 R(Tc) + qs solves in closed form for a given cooling coefficient
                     h = (qc + qr)/(Tc - Ta): Tc = Ta + (I^2 R(Ta) + qs) / (h - I^2 dR/dT). One step from the guess
                     T0 = Ta + 5 + 60 (I/1000)^2 gives T1; h is then taken at (T0 + T1)/2. With the air properties at
                     the film temperature Ta + 20 K this agrees with the full bisection within ~3 K up to 160 C
                     (test_twin.py checks a grid of currents, ambients, winds and irradiance)
  SAG / CLEARANCE    expected sag from the measured conductor temperature: a cubic fitted at build time to the
                     ruling-span change-of-state equation (parabolic approximation, elastic + thermal strain); the
                     conductor temperature implied by the measured clearance is the inverse cubic
"""
import math

import numpy as np

G = 9.81


# ------------------------------------------------------------------ constants from the twin file
def _k(twin):
    d = twin["design"]
    c, ln, w = d["conductor"], d["line"], d["weather_model"]
    r25, r75 = c["r_ac_25c_ohm_m"], c["r_ac_75c_ohm_m"]
    return dict(D=c["diameter_m"], eps=c["emissivity"], abs=c["absorptivity"], He=ln["elevation_m"],
                r25=r25, mR=(r75 - r25) / 50.0, tmax=c["max_operating_c"], temerg=c["emergency_c"],
                az=ln["azimuth_deg"], h_att=ln["attachment_height_m"], sag=d["sag_fit"]["sag_from_tc"],
                tc_from_sag=d["sag_fit"]["tc_from_sag"], static_a=d["ratings"]["static_a"],
                mcp=c["heat_capacity_j_mk"])


# ------------------------------------------------------------------ IEEE 738 in Python (exact, used by physics.py)
def air(tfilm, he):
    mu = 1.458e-6 * (tfilm + 273) ** 1.5 / (tfilm + 383.4)
    rho = (1.293 - 1.525e-4 * he + 6.379e-9 * he ** 2) / (1 + 0.00367 * tfilm)
    kf = 2.424e-2 + 7.477e-5 * tfilm - 4.407e-9 * tfilm ** 2
    return mu, rho, kf


def k_angle(phi):
    return 1.194 - math.cos(phi) + 0.194 * math.cos(2 * phi) + 0.368 * math.sin(2 * phi)


def wind_phi(wind_dir_deg, az_deg):
    """angle between the wind and the conductor axis, 0..pi/2 (radians)."""
    return math.asin(min(1.0, abs(math.sin(math.radians(wind_dir_deg - az_deg)))))


def qc(k, tc, ta, v, phi, tfilm=None):
    tf = (tc + ta) / 2 if tfilm is None else tfilm
    mu, rho, kf = air(tf, k["He"])
    dt = tc - ta
    re = k["D"] * rho * max(v, 0.0) / mu
    ka = k_angle(phi)
    q1 = ka * (1.01 + 1.35 * re ** 0.52) * kf * dt
    q2 = ka * 0.754 * re ** 0.6 * kf * dt
    qn = 3.645 * rho ** 0.5 * k["D"] ** 0.75 * max(dt, 0.0) ** 1.25
    return max(q1, q2, qn)


def qr(k, tc, ta):
    return 17.8 * k["D"] * k["eps"] * (((tc + 273) / 100) ** 4 - ((ta + 273) / 100) ** 4)


def qs(k, g):
    return k["abs"] * max(g, 0.0) * k["D"]


def r_ac(k, tc):
    return k["r25"] + k["mR"] * (tc - 25.0)


def steady_tc(k, i, ta, v, phi, g):
    """exact IEEE 738 steady conductor temperature (bisection)."""
    lo, hi = ta - 5.0, ta + 300.0
    for _ in range(60):
        mid = (lo + hi) / 2
        f = i * i * r_ac(k, mid) + qs(k, g) - qc(k, mid, ta, v, phi) - qr(k, mid, ta)
        lo, hi = (mid, hi) if f > 0 else (lo, mid)
    return (lo + hi) / 2


def ampacity(k, tc, ta, v, phi, g):
    return math.sqrt(max(0.0, qc(k, tc, ta, v, phi) + qr(k, tc, ta) - qs(k, g)) / r_ac(k, tc))


# ------------------------------------------------------------------ sag-tension (build time)
def state_change(cond, line, tc_list):
    """Ruling-span change of state (parabolic): L = S + w^2 S^3 / (24 H^2); L(T) = L0 (1 + a (T - T0) + (H - H0)/(E A)).
    Returns horizontal tension H (N) and mid-span sag (m) for each conductor temperature."""
    w = cond["mass_kg_m"] * G
    S, EA, a = line["ruling_span_m"], cond["final_modulus_pa"] * cond["area_total_m2"], cond["expansion_per_k"]
    H0, T0 = line["everyday_tension_n"], line["everyday_temp_c"]
    L0 = S + w * w * S ** 3 / (24 * H0 * H0)
    out = []
    for t in tc_list:
        lo, hi = 1000.0, 3 * H0
        for _ in range(80):
            H = (lo + hi) / 2
            f = (S + w * w * S ** 3 / (24 * H * H)) - L0 * (1 + a * (t - T0) + (H - H0) / EA)
            lo, hi = (H, hi) if f > 0 else (lo, H)
        H = (lo + hi) / 2
        out.append((H, w * S * S / (8 * H)))
    return out


def poly(c, x):
    return sum(ci * x ** i for i, ci in enumerate(c))


# ------------------------------------------------------------------ pandas expressions
def _phi_expr(k):
    return f"np.arcsin(np.abs(np.sin(np.radians(df['WIND_DIR_DEG'] - {k['az']}))))"


def _air_expr(k, tf):
    he = k["He"]
    mu = f"(1.458e-6 * ({tf} + 273) ** 1.5 / ({tf} + 383.4))"
    rho = f"((1.293 - {1.525e-4 * he} + {6.379e-9 * he * he}) / (1 + 0.00367 * {tf}))"
    kf = f"(2.424e-2 + 7.477e-5 * {tf} - 4.407e-9 * {tf} ** 2)"
    return mu, rho, kf


def _kangle_expr(x):
    """K_angle with phi = asin(|sin x|), x = wind direction - line azimuth: cos phi = |cos x|, cos 2phi = cos 2x, sin 2phi = |sin 2x|."""
    return f"(1.194 - np.abs(np.cos({x})) + 0.194 * np.cos(2 * {x}) + 0.368 * np.abs(np.sin(2 * {x})))"


def _forced_coef_expr(k, tf, ta_v_phi):
    """forced-convection coefficient (W/m/K) = K_angle max(1.01 + 1.35 Re^0.52, 0.754 Re^0.6) kf."""
    ta, v, phi = ta_v_phi
    mu, rho, kf = _air_expr(k, tf)
    re = f"({k['D']} * {rho} * {v}.clip(lower=0) / {mu})"
    return f"({_kangle_expr(phi)} * np.maximum(1.01 + 1.35 * {re} ** 0.52, 0.754 * {re} ** 0.6) * {kf})", rho


def _h_expr(k, t, ta, cf, rho):
    """cooling coefficient h(T) = (qc + qr)/(T - Ta) with forced coefficient cf (fixed film), natural and radiation."""
    dt = f"(({t}) - {ta}).clip(lower=0.5)"
    nat = f"(3.645 * {rho} ** 0.5 * {k['D'] ** 0.75} * {dt} ** 0.25)"
    rad = f"({17.8 * k['D'] * k['eps']} * ((({t}) + 273) ** 4 / 1e8 - ({ta} + 273) ** 4 / 1e8) / {dt})"
    return f"(np.maximum({cf}, {nat}) + {rad})"


def _closed_expr(k, h, i, g):
    """Tc = Ta + (I^2 R(Ta) + qs) / (h - I^2 mR)   (h(Tc - Ta) = I^2 R(Tc) + qs with R linear in Tc)."""
    return (f"(df['AMBIENT_TEMP_C'] + ({i} ** 2 * ({k['r25'] - 25 * k['mR']} + {k['mR']} * df['AMBIENT_TEMP_C']) + "
            f"{k['abs'] * k['D']} * {g}.clip(lower=0)) / ({h} - {i} ** 2 * {k['mR']}))")


def _parts(twin):
    k = _k(twin)
    TA, V, I, GS = "df['AMBIENT_TEMP_C']", "df['WIND_SPEED_MS']", "df['LINE_CURRENT_A']", "df['SOLAR_WM2']"
    PHI = _phi_expr(k)
    X = f"np.radians(df['WIND_DIR_DEG'] - {k['az']})"
    # expected conductor temperature: film at Ta + 20 K, two fixed-point steps
    cf, rho = _forced_coef_expr(k, f"({TA} + 20)", (TA, V, X))
    t0 = f"({TA} + 5 + 60 * ({I} / 1000) ** 2)"
    t1 = _closed_expr(k, _h_expr(k, t0, TA, cf, rho), I, GS)
    TCE = _closed_expr(k, _h_expr(k, f"(({t0} + {t1}) / 2)", TA, cf, rho), I, GS)

    def dlr(tc):
        tf = f"(({tc} + {TA}) / 2)"
        cfx, rhox = _forced_coef_expr(k, tf, (TA, V, X))
        dt = f"({tc} - {TA})"
        qcx = f"np.maximum({cfx} * {dt}, 3.645 * {rhox} ** 0.5 * {k['D'] ** 0.75} * {dt}.clip(lower=0) ** 1.25)"
        qrx = f"({17.8 * k['D'] * k['eps']} * ({(tc + 273) ** 4 / 1e8} - ({TA} + 273) ** 4 / 1e8))"
        return f"np.sqrt(({qcx} + {qrx} - {k['abs'] * k['D']} * {GS}.clip(lower=0)).clip(lower=0) / {k['r25'] + k['mR'] * (tc - 25)})"
    TC = "df['CONDUCTOR_TEMP_C']"
    s = k["sag"]
    SAGE = f"({s[0]} + {s[1]} * {TC} + {s[2]} * {TC} ** 2 + {s[3]} * {TC} ** 3)"
    SAGM = f"({k['h_att']} - df['CLEARANCE_M'])"
    t = k["tc_from_sag"]
    TCS = f"({t[0]} + {t[1]} * {SAGM} + {t[2]} * {SAGM} ** 2 + {t[3]} * {SAGM} ** 3)"
    return dict(k=k, TCE=TCE, DLR=dlr(k["tmax"]), DLRE=dlr(k["temerg"]), SAGE=SAGE, SAGM=SAGM, TCS=TCS, PHI=PHI)


def monitor_expressions(twin):
    p, k = _parts(twin), _k(twin)
    return [
        ("WIND_ANGLE_DEG", f"np.degrees({p['PHI']})"),
        ("R_AC_OHM_KM", f"({k['r25']} + {k['mR']} * (df['CONDUCTOR_TEMP_C'] - 25)) * 1000"),
        ("JOULE_W_M", f"df['LINE_CURRENT_A'] ** 2 * ({k['r25']} + {k['mR']} * (df['CONDUCTOR_TEMP_C'] - 25))"),
        ("SOLAR_W_M", f"{k['abs'] * k['D']} * df['SOLAR_WM2'].clip(lower=0)"),
        ("TC_EXPECTED_C", p["TCE"]),
        ("TC_RESIDUAL_K", f"df['CONDUCTOR_TEMP_C'] - {p['TCE']}"),
        ("DLR_A", p["DLR"]),
        ("DLR_EMERGENCY_A", p["DLRE"]),
        ("LOAD_PCT_DLR", f"df['LINE_CURRENT_A'] / ({p['DLR']}).clip(lower=1) * 100"),
        ("DLR_GAIN_PCT", f"(({p['DLR']}) / {k['static_a']} - 1) * 100"),
        ("SAG_MEASURED_M", p["SAGM"]),
        ("SAG_EXPECTED_M", p["SAGE"]),
        ("CLEARANCE_EXPECTED_M", f"{k['h_att']} - {p['SAGE']}"),
        ("CLEARANCE_RESIDUAL_M", f"df['CLEARANCE_M'] - ({k['h_att']} - {p['SAGE']})"),
        ("TC_FROM_SAG_C", p["TCS"]),
        ("TC_SAG_DIFF_K", f"df['CONDUCTOR_TEMP_C'] - {p['TCS']}"),
        ("JOINT_DELTA_K", "df['JOINT_TEMP_C'] - df['CONDUCTOR_TEMP_C']"),
    ]


# ------------------------------------------------------------------ the same numbers in Python
def _tc_expected(k, i, ta, v, phi, g):
    mu, rho, kf = air(ta + 20, k["He"])
    re = k["D"] * rho * max(v, 0.0) / mu
    cf = k_angle(phi) * max(1.01 + 1.35 * re ** 0.52, 0.754 * re ** 0.6) * kf

    def h(t):
        dt = max(t - ta, 0.5)
        nat = 3.645 * rho ** 0.5 * k["D"] ** 0.75 * dt ** 0.25
        rad = 17.8 * k["D"] * k["eps"] * ((t + 273) ** 4 / 1e8 - (ta + 273) ** 4 / 1e8) / dt
        return max(cf, nat) + rad

    def closed(hh):
        return ta + (i * i * (k["r25"] - 25 * k["mR"] + k["mR"] * ta) + k["abs"] * k["D"] * max(g, 0.0)) / (hh - i * i * k["mR"])
    t0 = ta + 5 + 60 * (i / 1000) ** 2           # starting guess grows with I^2
    t1 = closed(h(t0))
    return closed(h((t0 + t1) / 2))               # cooling at the midpoint damps the fixed-point oscillation


def _dlr(k, tc, ta, v, phi, g):
    tf = (tc + ta) / 2
    mu, rho, kf = air(tf, k["He"])
    re = k["D"] * rho * max(v, 0.0) / mu
    cf = k_angle(phi) * max(1.01 + 1.35 * re ** 0.52, 0.754 * re ** 0.6) * kf
    dt = tc - ta
    q_c = max(cf * dt, 3.645 * rho ** 0.5 * k["D"] ** 0.75 * max(dt, 0.0) ** 1.25)
    q_r = 17.8 * k["D"] * k["eps"] * ((tc + 273) ** 4 / 1e8 - (ta + 273) ** 4 / 1e8)
    return math.sqrt(max(0.0, q_c + q_r - k["abs"] * k["D"] * max(g, 0.0)) / (k["r25"] + k["mR"] * (tc - 25)))


def evaluate(twin, r):
    k = _k(twin)
    phi = math.asin(min(1.0, abs(math.sin(math.radians(r["wind_dir_deg"] - k["az"])))))
    i, ta, v, g, tc = r["line_current_a"], r["ambient_temp_c"], r["wind_speed_ms"], r["solar_wm2"], r["conductor_temp_c"]
    tce = _tc_expected(k, i, ta, v, phi, g)
    dlr = _dlr(k, k["tmax"], ta, v, phi, g)
    sage = poly(k["sag"], tc)
    sagm = k["h_att"] - r["clearance_m"]
    tcs = poly(k["tc_from_sag"], sagm)
    rac = k["r25"] + k["mR"] * (tc - 25)
    return {
        "wind_angle_deg": math.degrees(phi), "r_ac_ohm_km": rac * 1000, "joule_w_m": i * i * rac,
        "solar_w_m": k["abs"] * k["D"] * max(g, 0.0), "tc_expected_c": tce, "tc_residual_k": tc - tce,
        "dlr_a": dlr, "dlr_emergency_a": _dlr(k, k["temerg"], ta, v, phi, g), "load_pct_dlr": i / max(dlr, 1) * 100,
        "dlr_gain_pct": (dlr / k["static_a"] - 1) * 100, "sag_measured_m": sagm, "sag_expected_m": sage,
        "clearance_expected_m": k["h_att"] - sage, "clearance_residual_m": r["clearance_m"] - (k["h_att"] - sage),
        "tc_from_sag_c": tcs, "tc_sag_diff_k": tc - tcs, "joint_delta_k": r["joint_temp_c"] - tc,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    I = "df['LINE_CURRENT_A']"
    return [
        ("OHL_OVER_DLR", f"({I} > ({p['DLR']})) & (df['CONDUCTOR_TEMP_C'] > {L['tc_max_c'] - 5})", "High", "overload_beyond_dlr"),
        ("OHL_CONDUCTOR_HOT", f"df['CONDUCTOR_TEMP_C'] > {L['tc_max_c']}", "High", "overload_beyond_dlr"),
        ("OHL_CONDUCTOR_EMERGENCY", f"df['CONDUCTOR_TEMP_C'] > {L['tc_emergency_c']}", "Critical", None),
        ("OHL_JOINT_HOT", f"((df['JOINT_TEMP_C'] - df['CONDUCTOR_TEMP_C']) > {L['joint_delta_alert_k']}) & "
                          f"((df['CONDUCTOR_TEMP_C'] - {p['TCS']}) > -{L['sensor_sag_agree_k']})", "Medium", "joint_hotspot"),
        ("OHL_JOINT_CRITICAL", f"((df['JOINT_TEMP_C'] - df['CONDUCTOR_TEMP_C']) > {L['joint_delta_critical_k']}) & "
                               f"((df['CONDUCTOR_TEMP_C'] - {p['TCS']}) > -{L['sensor_sag_agree_k']})", "High", "joint_hotspot"),
        ("OHL_SAG_EXCESS", f"((df['CLEARANCE_M'] - ({p['k']['h_att']} - {p['SAGE']})) < -{L['clearance_residual_alert_m']}) & "
                           f"((df['CONDUCTOR_TEMP_C'] - {p['TCS']}) < -{L['tc_sag_diff_alert_k']}) & "
                           f"((df['CONDUCTOR_TEMP_C'] - {p['TCE']}) > -{L['tc_residual_alert_k']})", "Medium", "conductor_creep"),
        ("OHL_CLEARANCE_LOW", f"df['CLEARANCE_M'] < {L['ground_clearance_min_m']}", "Critical", None),
        ("OHL_VEGETATION", f"df['VEGETATION_DISTANCE_M'] < {L['vegetation_min_m']}", "High", "vegetation_encroachment"),
        ("OHL_SENSOR_SUSPECT", f"((df['CONDUCTOR_TEMP_C'] - {p['TCE']}) < -{L['tc_residual_alert_k']}) & "
                               f"((df['CONDUCTOR_TEMP_C'] - {p['TCS']}) < -{L['tc_sag_diff_alert_k']})", "Medium", "sensor_fault"),
        ("OHL_INSULATOR_LEAKAGE", f"df['LEAKAGE_CURRENT_MA'] > {L['leakage_alert_ma']}", "Medium", "insulator_pollution"),
        ("OHL_INSULATOR_FLASHOVER_RISK", f"df['LEAKAGE_CURRENT_MA'] > {L['leakage_high_ma']}", "High", "insulator_pollution"),
        ("OHL_VIBRATION", f"df['VIBRATION_UM'] > {L['vibration_alert_um']}", "Medium", "damper_loss"),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    i, tc = r["line_current_a"], r["conductor_temp_c"]
    k = _k(twin)
    add(i > t["dlr_a"] and tc > L["tc_max_c"] - 5, "OHL_OVER_DLR", "High",
        f"Current {i:.0f} A above the dynamic rating {t['dlr_a']:.0f} A for this weather", "conductor", "overload_beyond_dlr")
    add(tc > L["tc_max_c"], "OHL_CONDUCTOR_HOT", "High", f"Conductor {tc:.0f} °C (maximum operating {L['tc_max_c']} °C)", "conductor", "overload_beyond_dlr")
    add(tc > L["tc_emergency_c"], "OHL_CONDUCTOR_EMERGENCY", "Critical", f"Conductor {tc:.0f} °C above the emergency limit {L['tc_emergency_c']} °C", "conductor")
    sensor_ok = t["tc_sag_diff_k"] > -L["sensor_sag_agree_k"]           # conductor probe agrees with the sag
    add(t["joint_delta_k"] > L["joint_delta_alert_k"] and sensor_ok, "OHL_JOINT_HOT", "Medium",
        f"Mid-span joint {t['joint_delta_k']:.1f} K hotter than the conductor at {i:.0f} A", "joint", "joint_hotspot")
    add(t["joint_delta_k"] > L["joint_delta_critical_k"] and sensor_ok, "OHL_JOINT_CRITICAL", "High",
        f"Mid-span joint {t['joint_delta_k']:.0f} K hotter than the conductor: joint failing", "joint", "joint_hotspot")
    add(t["clearance_residual_m"] < -L["clearance_residual_alert_m"] and t["tc_sag_diff_k"] < -L["tc_sag_diff_alert_k"]
        and t["tc_residual_k"] > -L["tc_residual_alert_k"], "OHL_SAG_EXCESS", "Medium",
        f"Sag {-t['clearance_residual_m']:.2f} m more than the conductor temperature explains (sag says {t['tc_from_sag_c']:.0f} °C, sensor {tc:.0f} °C)",
        "conductor", "conductor_creep")
    add(r["clearance_m"] < L["ground_clearance_min_m"], "OHL_CLEARANCE_LOW", "Critical",
        f"Ground clearance {r['clearance_m']:.2f} m below the {L['ground_clearance_min_m']} m minimum", "span")
    add(r["vegetation_distance_m"] < L["vegetation_min_m"], "OHL_VEGETATION", "High",
        f"Vegetation {r['vegetation_distance_m']:.1f} m from the conductor (minimum {L['vegetation_min_m']} m)", "vegetation", "vegetation_encroachment")
    add(t["tc_residual_k"] < -L["tc_residual_alert_k"] and t["tc_sag_diff_k"] < -L["tc_sag_diff_alert_k"], "OHL_SENSOR_SUSPECT", "Medium",
        f"Conductor sensor reads {tc:.0f} °C; heat balance expects {t['tc_expected_c']:.0f} °C and the sag says {t['tc_from_sag_c']:.0f} °C",
        "sensor", "sensor_fault")
    add(r["leakage_current_ma"] > L["leakage_alert_ma"], "OHL_INSULATOR_LEAKAGE", "Medium",
        f"Insulator leakage current {r['leakage_current_ma']:.1f} mA at {r['humidity_pct']:.0f} % RH", "insulator", "insulator_pollution")
    add(r["leakage_current_ma"] > L["leakage_high_ma"], "OHL_INSULATOR_FLASHOVER_RISK", "High",
        f"Leakage current {r['leakage_current_ma']:.0f} mA: pollution flashover risk", "insulator", "insulator_pollution")
    add(r["vibration_um"] > L["vibration_alert_um"], "OHL_VIBRATION", "Medium",
        f"Aeolian vibration {r['vibration_um']:.0f} µm p-p at {r['wind_speed_ms']:.1f} m/s (limit {L['vibration_alert_um']})", "damper", "damper_loss")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
