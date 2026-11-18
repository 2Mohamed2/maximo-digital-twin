"""The road bridge twin's expectations (BR-6001: bearings, expansion joints and deck of a 3-span composite girder bridge).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Thermal movement (EN 1991-1-5 uniform temperature component, alpha from EN 1994-2 5.4.2.5):
  effective bridge temperature  Te = w x T_slab + (1 - w) x T_girder
  expected movement of a support at distance L from the fixed bearing:   u = alpha x L x (Te - T0)
  expected joint opening:   gap = gap(T0) - alpha x L x (Te - T0)            (the deck closes the joint as it warms)
  residual = measured - expected.  A seized bearing stops moving while u keeps changing; a blocked joint stops closing.
Pier P2 head (guided sliding bearing on top):
  the deck pushes the pier head with the bearing friction force F = mu x n x N, so the head moves delta = F / k and tilts
  theta = 1.5 x delta / H (cantilever). Turned round: mu_est = theta x H x k / (1.5 x n x N).  PTFE: mu <= 3 % (EN 1337-2).
  A seized bearing: no sliding, but the pier head still moves (it is dragged by the deck): theta far above friction level.
Joint A2 consistency: total gap + bearing A2 movement = gap(T0) for a rigid deck end. A non-zero closure is a sensor fault.
Modular joint: the control springs share the movement equally between the gaps; spread = max gap - min gap.
Deck strain under traffic: expected peak strain = c x W (W = gross weight of the vehicle from the WIM station); a higher ratio
  means a softer girder (lost composite action, cracking). Static strain: expected = k x (T_slab - T_girder) from the
  temperature difference; the rest is restraint (a blocked joint compresses the deck).
Bearing wear: remaining life = (path capacity - accumulated path) / path over the last 365 days; PTFE protrusion expected
  from the path: h = h0 - wear per km x path.
"""


def _k(twin):
    d = twin["design"]
    g, th, j, b, dk = d["geometry"], d["thermal"], d["joints"], d["bearing_p2"], d["deck"]
    a = th["alpha_per_k"]
    return dict(alpha=a, t0=th["t0_c"], temin=th["te_min_c"], temax=th["te_max_c"], w=th["slab_weight"],
                a_a1=a * g["exp_length_a1_m"] * 1000, a_p2=a * g["exp_length_p2_m"] * 1000, a_a2=a * g["exp_length_a2_m"] * 1000,
                g0a1=j["a1_gap_t0_mm"], g0a2=j["a2_gap_t0_mm"], gmax=j["a2_gap_max_mm"], gmin=j["a2_gap_min_mm"],
                n=b["bearings_per_support"], N=b["permanent_load_kn"], mu_d=b["mu_design"], mu_max=b["mu_max"],
                H=b["pier_height_m"], kp=b["pier_stiffness_kn_per_mm"],
                cmu=b["pier_height_m"] * b["pier_stiffness_kn_per_mm"] / (1.5 * b["bearings_per_support"] * b["permanent_load_kn"]),
                h0=b["sliding_gap_new_mm"], kw=b["sliding_gap_wear_mm_per_km"], cap=b["path_capacity_m"], rate_d=b["path_rate_design_m_per_y"],
                cs=dk["strain_per_kn_ue"], kdt=dk["strain_per_dt_ue"], E=dk["steel_e_mpa"], legal=dk["legal_gross_kn"])


def tilt_from_mu(k, mu):
    """Pier head tilt (mrad) for a bearing friction coefficient mu (both bearings sliding the same way)."""
    return mu / k["cmu"]


def _parts(twin):
    k = _k(twin)
    TE = f"({k['w']} * df['SLAB_TEMP_C'] + {1 - k['w']:.6g} * df['GIRDER_TEMP_C'])"
    DT = f"({TE} - {k['t0']})"
    EP2 = f"({k['a_p2']:.6g} * {DT})"
    EA2 = f"({k['a_a2']:.6g} * {DT})"
    TOT = "(df['JOINT_A2_GAP1_MM'] + df['JOINT_A2_GAP2_MM'] + df['JOINT_A2_GAP3_MM'])"
    GEA2 = f"({k['g0a2']} - {EA2})"
    GRA2 = f"({TOT} - {GEA2})"
    GRA1 = f"(df['JOINT_A1_GAP_MM'] - ({k['g0a1']} - {k['a_a1']:.6g} * {DT}))"
    GMAX = "np.maximum(np.maximum(df['JOINT_A2_GAP1_MM'], df['JOINT_A2_GAP2_MM']), df['JOINT_A2_GAP3_MM'])"
    GMIN = "np.minimum(np.minimum(df['JOINT_A2_GAP1_MM'], df['JOINT_A2_GAP2_MM']), df['JOINT_A2_GAP3_MM'])"
    RP2 = f"(df['BEARING_P2_DISP_MM'] - {EP2})"
    CLO = f"({TOT} + df['BEARING_A2_DISP_MM'] - {k['g0a2']})"
    MU = f"({k['cmu']:.6g} * np.abs(df['PIER_P2_TILT_MRAD']))"
    SRES = f"(df['STRAIN_STATIC_UE'] - {k['kdt']} * (df['SLAB_TEMP_C'] - df['GIRDER_TEMP_C']))"
    SEXP = f"({k['cs']} * df['WIM_LAST_HEAVY_KN'])"
    SR = f"(df['STRAIN_PEAK_UE'] / {SEXP})"
    LIFE = f"(({k['cap']} - df['BEARING_P2_PATH_M']) / np.maximum(df['BEARING_P2_PATH_RATE_M_Y'], 1.0))"
    return dict(k=k, TE=TE, DT=DT, EP2=EP2, EA2=EA2, TOT=TOT, GEA2=GEA2, GRA2=GRA2, GRA1=GRA1, GMAX=GMAX, GMIN=GMIN,
                RP2=RP2, CLO=CLO, MU=MU, SRES=SRES, SEXP=SEXP, SR=SR, LIFE=LIFE)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("TE_EFFECTIVE_C", p["TE"]),
        ("SLAB_GIRDER_DIFF_K", "df['SLAB_TEMP_C'] - df['GIRDER_TEMP_C']"),
        ("MOVE_EXP_P2_MM", p["EP2"]),
        ("RES_P2_MM", p["RP2"]),
        ("MOVE_EXP_A2_MM", p["EA2"]),
        ("RES_A2_MM", f"df['BEARING_A2_DISP_MM'] - {p['EA2']}"),
        ("GAP_RES_A1_MM", p["GRA1"]),
        ("GAP_A2_TOTAL_MM", p["TOT"]),
        ("GAP_EXP_A2_MM", p["GEA2"]),
        ("GAP_RES_A2_MM", p["GRA2"]),
        ("GAP_SPREAD_A2_MM", f"{p['GMAX']} - {p['GMIN']}"),
        ("CLOSURE_A2_MM", p["CLO"]),
        ("FRICTION_COEFF_EST", p["MU"]),
        ("STRAIN_STATIC_RES_UE", p["SRES"]),
        ("STRAIN_EXPECTED_UE", p["SEXP"]),
        ("STRAIN_RATIO", p["SR"]),
        ("SLIDING_GAP_EXPECTED_MM", f"{k['h0']} - {k['kw']} * df['BEARING_P2_PATH_M'] / 1000"),
        ("WEAR_LIFE_YEARS", p["LIFE"]),
        ("PATH_USED_PCT", f"df['BEARING_P2_PATH_M'] / {k['cap']} * 100"),
    ]


def evaluate(twin, r):
    k = _k(twin)
    te = k["w"] * r["slab_temp_c"] + (1 - k["w"]) * r["girder_temp_c"]
    dt = te - k["t0"]
    ep2, ea2 = k["a_p2"] * dt, k["a_a2"] * dt
    g = (r["joint_a2_gap1_mm"], r["joint_a2_gap2_mm"], r["joint_a2_gap3_mm"])
    tot = g[0] + g[1] + g[2]
    gea2 = k["g0a2"] - ea2
    sexp = k["cs"] * r["wim_last_heavy_kn"]
    return {
        "te_effective_c": te, "slab_girder_diff_k": r["slab_temp_c"] - r["girder_temp_c"],
        "move_exp_p2_mm": ep2, "res_p2_mm": r["bearing_p2_disp_mm"] - ep2,
        "move_exp_a2_mm": ea2, "res_a2_mm": r["bearing_a2_disp_mm"] - ea2,
        "gap_res_a1_mm": r["joint_a1_gap_mm"] - (k["g0a1"] - k["a_a1"] * dt),
        "gap_a2_total_mm": tot, "gap_exp_a2_mm": gea2, "gap_res_a2_mm": tot - gea2,
        "gap_spread_a2_mm": max(g) - min(g), "closure_a2_mm": tot + r["bearing_a2_disp_mm"] - k["g0a2"],
        "friction_coeff_est": k["cmu"] * abs(r["pier_p2_tilt_mrad"]),
        "strain_static_res_ue": r["strain_static_ue"] - k["kdt"] * (r["slab_temp_c"] - r["girder_temp_c"]),
        "strain_expected_ue": sexp, "strain_ratio": r["strain_peak_ue"] / sexp,
        "sliding_gap_expected_mm": k["h0"] - k["kw"] * r["bearing_p2_path_m"] / 1000,
        "wear_life_years": (k["cap"] - r["bearing_p2_path_m"]) / max(r["bearing_p2_path_rate_m_y"], 1.0),
        "path_used_pct": r["bearing_p2_path_m"] / k["cap"] * 100,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    return [
        ("BR_BEARING_SEIZED", f"(np.abs({p['RP2']}) > {L['bearing_residual_mm']}) & (np.abs(df['PIER_P2_TILT_MRAD']) > {L['pier_tilt_mrad']})", "High", "bearing_seized"),
        ("BR_PIER_TILT", f"np.abs(df['PIER_P2_TILT_MRAD']) > {L['pier_tilt_mrad']}", "High", "bearing_seized"),
        ("BR_JOINT_BLOCKED", f"({p['GRA2']} > {L['joint_residual_mm']}) | ({p['GRA1']} > {L['joint_residual_mm']})", "High", "joint_blocked"),
        ("BR_DECK_RESTRAINT", f"np.abs({p['SRES']}) > {L['restraint_strain_ue']}", "High", "joint_blocked"),
        ("BR_JOINT_GAP_LIMIT", f"({p['GMAX']} > {k['gmax']}) | ({p['GMIN']} < {k['gmin']})", "High", "joint_control_failure"),
        ("BR_STRAIN_RATIO_HIGH", f"{p['SR']} > {L['strain_ratio']}", "High", "girder_stiffness_loss"),
        ("BR_BEARING_FRICTION_HIGH", f"{p['MU']} > {k['mu_max']}", "Medium", "ptfe_wear"),
        ("BR_SLIDING_GAP_LOW", f"df['BEARING_P2_SLIDING_GAP_MM'] < {L['sliding_gap_min_mm']}", "Medium", "ptfe_wear"),
        ("BR_WEAR_RATE_HIGH", f"df['BEARING_P2_PATH_RATE_M_Y'] > {L['path_rate_factor'] * k['rate_d']:.6g}", "Medium", "sliding_path_fast"),
        ("BR_WEAR_LIFE_LOW", f"{p['LIFE']} < {L['wear_life_min_y']}", "Medium", "sliding_path_fast"),
        ("BR_JOINT_GAP_UNEVEN", f"({p['GMAX']} - {p['GMIN']}) > {L['gap_spread_mm']}", "Medium", "joint_control_failure"),
        ("BR_JOINT_IMPACT", f"df['JOINT_A2_IMPACT_G'] > {L['impact_g']}", "Medium", "joint_control_failure"),
        ("BR_OVERWEIGHT_TRAFFIC", f"df['WIM_OVERWEIGHT_24H'] > {L['overweight_24h']}", "Medium", "overweight_traffic"),
        ("BR_SENSOR_MISMATCH", f"np.abs({p['CLO']}) > {L['closure_mm']}", "Low", "displacement_sensor"),
        ("BR_TEMP_OUTSIDE_DESIGN", f"({p['TE']} > {k['temax']}) | ({p['TE']} < {k['temin']})", "Low", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    tilt = abs(r["pier_p2_tilt_mrad"])
    g = (r["joint_a2_gap1_mm"], r["joint_a2_gap2_mm"], r["joint_a2_gap3_mm"])
    life = t["wear_life_years"]
    add(abs(t["res_p2_mm"]) > L["bearing_residual_mm"] and tilt > L["pier_tilt_mrad"], "BR_BEARING_SEIZED", "High",
        f"Bearing P2 at {r['bearing_p2_disp_mm']:.1f} mm, expected {t['move_exp_p2_mm']:.1f} mm at Te {t['te_effective_c']:.1f} °C, while the pier tilts {r['pier_p2_tilt_mrad']:.2f} mrad",
        "bearing", "bearing_seized")
    add(tilt > L["pier_tilt_mrad"], "BR_PIER_TILT", "High", f"Pier P2 head tilt {r['pier_p2_tilt_mrad']:.2f} mrad (limit {L['pier_tilt_mrad']})", "pier", "bearing_seized")
    add(t["gap_res_a2_mm"] > L["joint_residual_mm"] or t["gap_res_a1_mm"] > L["joint_residual_mm"], "BR_JOINT_BLOCKED", "High",
        f"Joint A2 open {t['gap_a2_total_mm']:.1f} mm, expected {t['gap_exp_a2_mm']:.1f} mm (A1 residual {t['gap_res_a1_mm']:+.1f} mm): the joint does not close",
        "joint_a2", "joint_blocked")
    add(abs(t["strain_static_res_ue"]) > L["restraint_strain_ue"], "BR_DECK_RESTRAINT", "High",
        f"Restraint strain {t['strain_static_res_ue']:+.0f} µε ({t['strain_static_res_ue'] * k['E'] / 1e6:+.0f} MPa in the steel)", "deck", "joint_blocked")
    add(max(g) > k["gmax"] or min(g) < k["gmin"], "BR_JOINT_GAP_LIMIT", "High",
        f"Joint A2 gaps {g[0]:.0f} / {g[1]:.0f} / {g[2]:.0f} mm: outside {k['gmin']:.0f} to {k['gmax']:.0f} mm", "joint_a2", "joint_control_failure")
    add(t["strain_ratio"] > L["strain_ratio"], "BR_STRAIN_RATIO_HIGH", "High",
        f"Peak strain {r['strain_peak_ue']:.0f} µε under a {r['wim_last_heavy_kn']:.0f} kN vehicle: {t['strain_ratio']:.2f} x the model", "deck", "girder_stiffness_loss")
    add(t["friction_coeff_est"] > k["mu_max"], "BR_BEARING_FRICTION_HIGH", "Medium",
        f"Bearing P2 friction about {t['friction_coeff_est'] * 100:.1f} % (PTFE maximum {k['mu_max'] * 100:.0f} %)", "bearing", "ptfe_wear")
    add(r["bearing_p2_sliding_gap_mm"] < L["sliding_gap_min_mm"], "BR_SLIDING_GAP_LOW", "Medium",
        f"PTFE protrusion {r['bearing_p2_sliding_gap_mm']:.2f} mm, below {L['sliding_gap_min_mm']} mm", "bearing", "ptfe_wear")
    add(r["bearing_p2_path_rate_m_y"] > L["path_rate_factor"] * k["rate_d"], "BR_WEAR_RATE_HIGH", "Medium",
        f"Sliding path {r['bearing_p2_path_rate_m_y']:.0f} m in 365 days, design {k['rate_d']:.0f} m", "bearing", "sliding_path_fast")
    add(life < L["wear_life_min_y"], "BR_WEAR_LIFE_LOW", "Medium", f"Sliding material life left about {life:.1f} years", "bearing", "sliding_path_fast")
    add(max(g) - min(g) > L["gap_spread_mm"], "BR_JOINT_GAP_UNEVEN", "Medium",
        f"Joint A2 gaps differ by {max(g) - min(g):.0f} mm (limit {L['gap_spread_mm']:.0f})", "joint_a2", "joint_control_failure")
    add(r["joint_a2_impact_g"] > L["impact_g"], "BR_JOINT_IMPACT", "Medium", f"Joint A2 impact {r['joint_a2_impact_g']:.1f} g under traffic", "joint_a2", "joint_control_failure")
    add(r["wim_overweight_24h"] > L["overweight_24h"], "BR_OVERWEIGHT_TRAFFIC", "Medium",
        f"{r['wim_overweight_24h']:.0f} vehicles above {k['legal']:.0f} kN in 24 h", "wim", "overweight_traffic")
    add(abs(t["closure_a2_mm"]) > L["closure_mm"], "BR_SENSOR_MISMATCH", "Low",
        f"Joint A2 gap + bearing A2 movement off by {t['closure_a2_mm']:+.1f} mm: check the transducers", "sensor", "displacement_sensor")
    add(t["te_effective_c"] > k["temax"] or t["te_effective_c"] < k["temin"], "BR_TEMP_OUTSIDE_DESIGN", "Low",
        f"Effective bridge temperature {t['te_effective_c']:.1f} °C outside the design range {k['temin']:.0f} to {k['temax']:.0f} °C", "deck")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
