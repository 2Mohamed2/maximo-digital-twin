"""The feeder protection relay twin's expectations (PR-7201, ABB REF615 on an 11 kV feeder).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

Overcurrent operate time (IEC 60255-151, inverse time):
      M = I / Is                      I = highest phase current in the fault record, Is = start value x CT primary
      t = TMS x (k / (M^alpha - 1) + c)   IEC normal inverse: k = 0.14, alpha = 0.02, c = 0
  The relay's own accuracy in inverse time mode is +/-5 % of the theoretical value or +/-20 ms, whichever is larger:
      tolerance = max(0.05 x t, 20 ms);   error ratio = |t measured - t expected| / tolerance
  An error ratio above 1 means the relay did not trip on the curve that the approved settings describe.
Breaker (from the relay's own event records):
      opening ratio = opening time / baseline;   breaker failure margin = CB failure delay - opening time
      clearing time = relay operate time + breaker opening time
  Contact wear: the relay sums I^y x t over every break (SSCBR accumulated energy, y = 2). The allowance is the number
  of breaks at rated short-circuit current the interrupters allow: allowance = N x Isc^2 x t_arc.
      wear % = accumulated / allowance x 100;   breaks left at rated current = (allowance - accumulated) / (Isc^2 x t_arc)
Supervision:
      CT mismatch = |Io calculated from the phases - Io measured by the core-balance CT| / CT primary   (CCSPVC idea)
      DC % = auxiliary DC / nominal;   trip DC margin = auxiliary DC - 70 % of nominal (IEC 62271-1 trip coil minimum)
      GOOSE miss % = missed / (subscriptions x window / heartbeat) x 100
      settings OK = 1 when the checksum and the active group equal the approved values held on the Maximo asset
"""


def _k(twin):
    d = twin["design"]
    f, o, b, s, dc = d["feeder"], d["overcurrent"], d["breaker"], d["supervision"], d["dc"]
    isc2t = b["isc_rated_ka"] ** 2 * b["arc_time_s"]
    return dict(ct=f["ct_primary_a"], is_a=o["start_value_in"] * f["ct_primary_a"], tms=o["tms"], kk=o["k"], al=o["alpha"], cc=o["c"],
                acc_pct=o["accuracy_pct"], acc_ms=o["accuracy_ms"], base=b["open_baseline_ms"], bf=b["bf_delay_ms"],
                bfm=b["bf_margin_alert_ms"], isc2t=isc2t, allow=isc2t * b["breaks_at_rated"], ccs=s["ccs_start_in"],
                gexp=s["goose_subscriptions"] * s["goose_window_s"] / s["goose_heartbeat_s"], gmiss=s["goose_miss_alert_pct"],
                glat=s["goose_latency_alert_ms"], sync=s["sync_offset_alert_us"], crc=s["settings_checksum_approved"],
                grp=s["setting_group_approved"], proof=s["trip_path_proof_days"], un=dc["nominal_v"],
                relay_min=dc["nominal_v"] * dc["relay_min_pct"] / 100, coil_min=dc["nominal_v"] * dc["trip_coil_min_pct"] / 100,
                load=f["load_nominal_a"])


def curve_time_s(k, m, tms=None, kk=None, al=None, cc=None):
    """Operate time (s) of an IEC 60255-151 / IEEE C37.112 inverse curve at current multiple m (m > 1)."""
    tms = k["tms"] if tms is None else tms
    kk, al, cc = (k["kk"], k["al"], k["cc"]) if kk is None else (kk, al, cc)
    return tms * (kk / (m ** al - 1) + cc)


def _parts(twin):
    k = _k(twin)
    M = f"(df['FAULT_CURRENT_A'] / {k['is_a']})"
    ME = f"np.maximum({M}, 1.05)"
    EXP = f"(1000 * {k['tms']} * ({k['kk']} / ({ME} ** {k['al']} - 1) + {k['cc']}))"
    ERR = f"(df['FAULT_OPERATE_MS'] - {EXP})"
    TOL = f"np.maximum({k['acc_pct'] / 100} * {EXP}, {k['acc_ms']})"
    RATIO = f"(np.abs({ERR}) / {TOL})"
    OK = f"np.where((df['SETTINGS_CRC'] == {k['crc']}) & (df['ACTIVE_GROUP'] == {k['grp']}), 1, 0)"
    CTM = f"(np.abs(df['IO_CALC_A'] - df['IO_MEAS_A']) / {k['ct']})"
    GM = f"(df['GOOSE_MISSED'] / {k['gexp']} * 100)"
    WEAR = f"(df['CB_WEAR_KA2S'] / {k['allow']:.6g} * 100)"
    return dict(k=k, M=M, EXP=EXP, ERR=ERR, TOL=TOL, RATIO=RATIO, OK=OK, CTM=CTM, GM=GM, WEAR=WEAR)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("PICKUP_MULTIPLE", p["M"]),
        ("OPERATE_EXPECTED_MS", p["EXP"]),
        ("OPERATE_ERROR_MS", p["ERR"]),
        ("OPERATE_TOLERANCE_MS", p["TOL"]),
        ("OPERATE_ERROR_RATIO", p["RATIO"]),
        ("CLEARING_TIME_MS", "df['FAULT_OPERATE_MS'] + df['CB_OPEN_MS']"),
        ("CB_OPEN_RATIO", f"df['CB_OPEN_MS'] / {k['base']}"),
        ("BF_MARGIN_MS", f"{k['bf']} - df['CB_OPEN_MS']"),
        ("CB_WEAR_PCT", p["WEAR"]),
        ("BREAKS_LEFT_AT_RATED", f"({k['allow']:.6g} - df['CB_WEAR_KA2S']) / {k['isc2t']:.6g}"),
        ("SETTINGS_OK", p["OK"]),
        ("SYNC_OFFSET_ABS_US", "np.abs(df['SYNC_OFFSET_US'])"),
        ("DC_PCT_OF_NOMINAL", f"df['AUX_DC_V'] / {k['un']} * 100"),
        ("TRIP_DC_MARGIN_V", f"df['AUX_DC_V'] - {k['coil_min']:.6g}"),
        ("CT_MISMATCH_IN", p["CTM"]),
        ("LOAD_PCT_OF_PICKUP", f"df['LOAD_CURRENT_A'] / {k['is_a']} * 100"),
        ("GOOSE_MISS_PCT", p["GM"]),
    ]


def evaluate(twin, r):
    k = _k(twin)
    m = r["fault_current_a"] / k["is_a"]
    exp = 1000 * k["tms"] * (k["kk"] / (max(m, 1.05) ** k["al"] - 1) + k["cc"])
    err = r["fault_operate_ms"] - exp
    tol = max(k["acc_pct"] / 100 * exp, k["acc_ms"])
    return {
        "pickup_multiple": m, "operate_expected_ms": exp, "operate_error_ms": err, "operate_tolerance_ms": tol,
        "operate_error_ratio": abs(err) / tol,
        "clearing_time_ms": r["fault_operate_ms"] + r["cb_open_ms"],
        "cb_open_ratio": r["cb_open_ms"] / k["base"], "bf_margin_ms": k["bf"] - r["cb_open_ms"],
        "cb_wear_pct": r["cb_wear_ka2s"] / k["allow"] * 100,
        "breaks_left_at_rated": (k["allow"] - r["cb_wear_ka2s"]) / k["isc2t"],
        "settings_ok": 1 if (r["settings_crc"] == k["crc"] and r["active_group"] == k["grp"]) else 0,
        "sync_offset_abs_us": abs(r["sync_offset_us"]),
        "dc_pct_of_nominal": r["aux_dc_v"] / k["un"] * 100, "trip_dc_margin_v": r["aux_dc_v"] - k["coil_min"],
        "ct_mismatch_in": abs(r["io_calc_a"] - r["io_meas_a"]) / k["ct"],
        "load_pct_of_pickup": r["load_current_a"] / k["is_a"] * 100,
        "goose_miss_pct": r["goose_missed"] / k["gexp"] * 100,
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    return [
        ("PROT_SELF_SUPERVISION", "df['IRF_ALARM'] > 0.5", "Critical", None),
        ("PROT_TCS_ALARM", "df['TCS_ALARM'] > 0.5", "Critical", "trip_circuit_open"),
        ("PROT_DC_TRIP_RISK", f"df['AUX_DC_V'] < {k['coil_min']:.6g}", "Critical", "dc_supply_low"),
        ("PROT_SETTINGS_MISMATCH", f"{p['OK']} < 0.5", "High", "settings_change"),
        ("PROT_TIMING_DEVIATION", f"{p['RATIO']} > {L['operate_error_ratio_alert']}", "High", "settings_change"),
        ("PROT_BF_MARGIN_LOW", f"({k['bf']} - df['CB_OPEN_MS']) < {k['bfm']}", "High", "breaker_slow"),
        ("PROT_CB_WEAR_LIMIT", f"{p['WEAR']} >= {L['wear_limit_pct']}", "High", "contact_wear"),
        ("PROT_CT_SUPERVISION", f"{p['CTM']} > {k['ccs']}", "High", "ct_circuit_fault"),
        ("PROT_CB_SLOW", f"(df['CB_OPEN_MS'] / {k['base']}) > {L['cb_open_ratio_alert']}", "Medium", "breaker_slow"),
        ("PROT_CB_WEAR", f"{p['WEAR']} >= {L['wear_alert_pct']}", "Medium", "contact_wear"),
        ("PROT_DC_LOW", f"df['AUX_DC_V'] < {k['relay_min']:.6g}", "Medium", "dc_supply_low"),
        ("PROT_TIME_SYNC", f"(df['SYNC_OK'] < 0.5) | (np.abs(df['SYNC_OFFSET_US']) > {k['sync']})", "Medium", "time_sync_loss"),
        ("PROT_GOOSE_DEGRADED", f"({p['GM']} > {k['gmiss']}) | (df['GOOSE_MAX_LATENCY_MS'] > {k['glat']})", "Medium", "goose_degraded"),
        ("PROT_TRIP_PATH_UNPROVEN", f"df['TRIP_VERIFIED_DAYS'] > {k['proof']}", "Medium", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    add(r["irf_alarm"] > 0.5, "PROT_SELF_SUPERVISION", "Critical", "Internal relay fault: the relay has blocked its protection functions", "relay")
    add(r["tcs_alarm"] > 0.5, "PROT_TCS_ALARM", "Critical", "Trip circuit supervision alarm: the relay cannot trip the breaker", "trip circuit", "trip_circuit_open")
    add(r["aux_dc_v"] < k["coil_min"], "PROT_DC_TRIP_RISK", "Critical",
        f"Auxiliary DC {r['aux_dc_v']:.0f} V, below the {k['coil_min']:.0f} V a trip coil needs (70 % of {k['un']:.0f} V)", "dc supply", "dc_supply_low")
    add(t["settings_ok"] < 0.5, "PROT_SETTINGS_MISMATCH", "High",
        f"Active settings (checksum {int(r['settings_crc'])}, group {int(r['active_group'])}) differ from the approved record", "settings", "settings_change")
    add(t["operate_error_ratio"] > L["operate_error_ratio_alert"], "PROT_TIMING_DEVIATION", "High",
        f"Last fault: tripped in {r['fault_operate_ms']:.0f} ms, curve says {t['operate_expected_ms']:.0f} ms ± {t['operate_tolerance_ms']:.0f} ms",
        "settings", "settings_change")
    add(t["bf_margin_ms"] < k["bfm"], "PROT_BF_MARGIN_LOW", "High",
        f"Breaker opened in {r['cb_open_ms']:.0f} ms: only {t['bf_margin_ms']:.0f} ms before breaker failure trips the busbar", "breaker", "breaker_slow")
    add(t["cb_wear_pct"] >= L["wear_limit_pct"], "PROT_CB_WEAR_LIMIT", "High", f"Interrupter wear {t['cb_wear_pct']:.0f} % of the allowance", "breaker", "contact_wear")
    add(t["ct_mismatch_in"] > k["ccs"], "PROT_CT_SUPERVISION", "High",
        f"Residual from phases {r['io_calc_a']:.0f} A vs core-balance CT {r['io_meas_a']:.0f} A ({t['ct_mismatch_in']:.2f} × In)", "CT circuit", "ct_circuit_fault")
    add(t["cb_open_ratio"] > L["cb_open_ratio_alert"], "PROT_CB_SLOW", "Medium",
        f"Breaker opening time {r['cb_open_ms']:.0f} ms, {t['cb_open_ratio']:.2f} × the baseline", "breaker", "breaker_slow")
    add(t["cb_wear_pct"] >= L["wear_alert_pct"], "PROT_CB_WEAR", "Medium", f"Interrupter wear {t['cb_wear_pct']:.0f} %, {t['breaks_left_at_rated']:.0f} breaks left at rated current",
        "breaker", "contact_wear")
    add(r["aux_dc_v"] < k["relay_min"], "PROT_DC_LOW", "Medium",
        f"Auxiliary DC {r['aux_dc_v']:.0f} V, below the relay's supply range ({k['relay_min']:.0f} V)", "dc supply", "dc_supply_low")
    add(r["sync_ok"] < 0.5 or abs(r["sync_offset_us"]) > k["sync"], "PROT_TIME_SYNC", "Medium",
        f"Time sync {'lost' if r['sync_ok'] < 0.5 else 'poor'}: offset {r['sync_offset_us']:.0f} µs", "time sync", "time_sync_loss")
    add(t["goose_miss_pct"] > k["gmiss"] or r["goose_max_latency_ms"] > k["glat"], "PROT_GOOSE_DEGRADED", "Medium",
        f"GOOSE: {r['goose_missed']:.0f} missed or late ({t['goose_miss_pct']:.1f} %), worst {r['goose_max_latency_ms']:.1f} ms", "station bus", "goose_degraded")
    add(r["trip_verified_days"] > k["proof"], "PROT_TRIP_PATH_UNPROVEN", "Medium",
        f"Trip path last proven {r['trip_verified_days']:.0f} days ago", "testing")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
