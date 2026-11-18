"""The sucker-rod pumping system twin's expectations (RP-2901, beam pumping unit + rod string + insert pump + RPC).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)

The rod pump controller (RPC) measures the surface card (polished rod load against position) every stroke and solves the
damped wave equation of the rod string (Gibbs) to get the pump card at the plunger. It reports features of both cards:
peak and minimum polished rod load (PPRL, MPRL), the plunger gross and net stroke, the fillage (net / gross) and the fluid
load on the pump card. Monitor stays stateless: every expression below works on one reading.

Expected loads (conventional unit, API TR 11L notation, Mills acceleration factor):
    Wr  = sum(weight per ft x length) of the rod sections         (rods in air)
    Wrf = Wr x (1 - 0.128 G)                                       (rods in fluid: steel 490 lb/ft3)
    Fo  = Ap x (Pt + 0.433 G L - PIP),  Ap = pi/4 D^2              (fluid load on the plunger = 0.340 G D^2 H)
    a   = S N^2 / 70,500                                           (acceleration factor, S in in, N in strokes/min)
    PPRL expected = Wrf + Fo + a Wr        MPRL expected = Wrf - a Wr
Gearbox torque, simple conventional-unit form (torque factor taken as S/2 at the peak):
    T_up = (PPRL - CBE) S/2     T_down = (CBE - MPRL) S/2         gearbox loading = max / API rating
Rod stress at the top rod against the modified Goodman diagram (API RP 11BR):
    Smax = PPRL / A_top,  Smin = MPRL / A_top,  Sa = (T/4 + 0.5625 Smin) x SF,   rod loading = Smax / Sa
Production:
    gross stroke expected = S - Fo x sum(12 L / (A E))             (rod stretch, anchored tubing, overtravel neglected)
    pump displacement PD  = 0.1166 x net stroke x N x D^2 x run time    (bbl/d)
    volumetric efficiency = measured liquid rate / PD
    submergence = (PIP - casing pressure) / (0.433 G)              (liquid above the pump intake)
"""
import math


def _k(twin):
    d = twin["design"]
    u, r, p, f, o = d["unit"], d["rods"], d["pump"], d["fluid"], d["operation"]
    secs = r["sections"]
    wr = sum(s["weight_lb_ft"] * s["length_ft"] for s in secs)
    g = f["sg"]
    grad = f["gradient_psi_ft"] * g
    dp = p["plunger_in"]
    return dict(wr=wr, wrf=wr * (1 - 0.128 * g), g=g, grad=grad, ap=math.pi / 4 * dp ** 2, d2=dp ** 2, depth=p["depth_ft"],
                er=sum(12 * s["length_ft"] / (s["area_in2"] * r["modulus_psi"]) for s in secs), atop=secs[0]["area_in2"],
                tmin=r["tensile_min_psi"], sf=r["service_factor"], cbe=u["cbe_lb"], gb=u["gearbox_rating_inlb"],
                st=u["structure_rating_lb"], stroke=u["stroke_in"], fill_sp=o["pumpoff_fillage_pct"], ve=o["ve_expected"])


def _parts(twin):
    k = _k(twin)
    SUB = f"((df['PIP_PSI'] - df['CASING_PRESSURE_PSI']) / {k['grad']:.6g})"
    FO = f"({k['ap']:.6g} * (df['TUBING_PRESSURE_PSI'] + {k['grad'] * k['depth']:.6g} - df['PIP_PSI']))"
    FLR = f"(df['PUMP_FLUID_LOAD_LB'] / {FO})"
    ACC = "(df['SURFACE_STROKE_IN'] * df['SPM'] ** 2 / 70500)"
    PE = f"({k['wrf']:.6g} + {FO} + {k['wr']:.6g} * {ACC})"
    ME = f"({k['wrf']:.6g} - {k['wr']:.6g} * {ACC})"
    TU = f"((df['PPRL_LB'] - {k['cbe']:.6g}) * df['SURFACE_STROKE_IN'] / 2000)"
    TD = f"(({k['cbe']:.6g} - df['MPRL_LB']) * df['SURFACE_STROKE_IN'] / 2000)"
    GB = f"(np.maximum({TU}, {TD}) / {k['gb'] / 1000:.6g} * 100)"
    RL = f"(df['PPRL_LB'] / {k['atop']:.6g} / (({k['tmin'] / 4:.6g} + 0.5625 * df['MPRL_LB'] / {k['atop']:.6g}) * {k['sf']:.6g}) * 100)"
    PD = f"({0.1166 * k['d2']:.6g} * df['PUMP_NET_STROKE_IN'] * df['SPM'] * df['RUNTIME_PCT'] / 100)"
    VE = f"(df['FLOW_BPD'] / np.maximum({PD}, 1))"
    BAL = "(df['CURRENT_DOWN_A'] / np.maximum(df['CURRENT_UP_A'], 0.1))"
    return dict(k=k, SUB=SUB, FO=FO, FLR=FLR, ACC=ACC, PE=PE, ME=ME, TU=TU, TD=TD, GB=GB, RL=RL, PD=PD, VE=VE, BAL=BAL)


def monitor_expressions(twin):
    p = _parts(twin)
    k = p["k"]
    return [
        ("SUBMERGENCE_FT", p["SUB"]),
        ("FO_EXPECTED_LB", p["FO"]),
        ("FLUID_LOAD_RATIO", p["FLR"]),
        ("ACCEL_FACTOR", p["ACC"]),
        ("PPRL_EXPECTED_LB", p["PE"]),
        ("MPRL_EXPECTED_LB", p["ME"]),
        ("PPRL_RATIO", f"df['PPRL_LB'] / {p['PE']}"),
        ("MPRL_RATIO", f"df['MPRL_LB'] / {p['ME']}"),
        ("STRUCTURE_LOAD_PCT", f"df['PPRL_LB'] / {k['st']:.6g} * 100"),
        ("ROD_LOADING_PCT", p["RL"]),
        ("TORQUE_UP_KINLB", p["TU"]),
        ("TORQUE_DOWN_KINLB", p["TD"]),
        ("GEARBOX_LOAD_PCT", p["GB"]),
        ("CBE_IDEAL_LB", "((df['PPRL_LB'] + df['MPRL_LB']) / 2)"),
        ("BALANCE_RATIO", p["BAL"]),
        ("GROSS_STROKE_EXPECTED_IN", f"(df['SURFACE_STROKE_IN'] - {p['FO']} * {k['er']:.6g})"),
        ("PUMP_DISPLACEMENT_BPD", p["PD"]),
        ("VOL_EFF", p["VE"]),
        ("ENERGY_KWH_PER_BBL", "(df['MOTOR_KW'] * 24 * df['RUNTIME_PCT'] / 100 / np.maximum(df['FLOW_BPD'], 1))"),
    ]


def _r6(x):
    """The constants exactly as they are written into the Monitor expressions (6 significant digits)."""
    return float(f"{x:.6g}")


def evaluate(twin, r):
    k = {a: (_r6(b) if isinstance(b, float) else b) for a, b in _k(twin).items()}
    grad_l = _r6(k["grad"] * k["depth"])
    sub = (r["pip_psi"] - r["casing_pressure_psi"]) / k["grad"]
    fo = k["ap"] * (r["tubing_pressure_psi"] + grad_l - r["pip_psi"])
    acc = r["surface_stroke_in"] * r["spm"] ** 2 / 70500
    pe = k["wrf"] + fo + k["wr"] * acc
    me = k["wrf"] - k["wr"] * acc
    tu = (r["pprl_lb"] - k["cbe"]) * r["surface_stroke_in"] / 2000
    td = (k["cbe"] - r["mprl_lb"]) * r["surface_stroke_in"] / 2000
    sa = (_r6(k["tmin"] / 4) + 0.5625 * r["mprl_lb"] / k["atop"]) * k["sf"]
    pd = _r6(0.1166 * k["d2"]) * r["pump_net_stroke_in"] * r["spm"] * r["runtime_pct"] / 100
    return {
        "submergence_ft": sub, "fo_expected_lb": fo, "fluid_load_ratio": r["pump_fluid_load_lb"] / fo, "accel_factor": acc,
        "pprl_expected_lb": pe, "mprl_expected_lb": me, "pprl_ratio": r["pprl_lb"] / pe, "mprl_ratio": r["mprl_lb"] / me,
        "structure_load_pct": r["pprl_lb"] / k["st"] * 100, "rod_loading_pct": r["pprl_lb"] / k["atop"] / sa * 100,
        "torque_up_kinlb": tu, "torque_down_kinlb": td, "gearbox_load_pct": max(tu, td) / _r6(k["gb"] / 1000) * 100,
        "cbe_ideal_lb": (r["pprl_lb"] + r["mprl_lb"]) / 2, "balance_ratio": r["current_down_a"] / max(r["current_up_a"], 0.1),
        "gross_stroke_expected_in": r["surface_stroke_in"] - fo * k["er"], "pump_displacement_bpd": pd,
        "vol_eff": r["flow_bpd"] / max(pd, 1),
        "energy_kwh_per_bbl": r["motor_kw"] * 24 * r["runtime_pct"] / 100 / max(r["flow_bpd"], 1),
    }


def alert_rules(twin):
    L = twin["twin_model"]["limits"]
    p = _parts(twin)
    k = p["k"]
    FLR, VE, SUB, GB = p["FLR"], p["VE"], p["SUB"], p["GB"]
    card = f"({FLR} >= {L['fluid_load_lost_ratio']})"
    fill = "df['PUMP_FILLAGE_PCT']"
    return [
        ("RP_ROD_PART", f"{FLR} < {L['fluid_load_lost_ratio']}", "Critical", "rod_part"),
        ("RP_GEARBOX_OVERLOAD", f"{GB} >= {L['gearbox_limit_pct']}", "High", "paraffin_drag"),
        ("RP_STRUCTURE_OVERLOAD", f"df['PPRL_LB'] > {k['st']:.6g}", "High", None),
        ("RP_ROD_OVERSTRESS", f"{p['RL']} > {L['rod_loading_limit_pct']}", "High", "paraffin_drag"),
        ("RP_FLUID_POUND", f"({fill} < {k['fill_sp']}) & ({SUB} < {L['submergence_low_ft']}) & (df['RUNTIME_PCT'] > {L['runtime_poc_pct']}) & {card}",
         "High", "fluid_pound"),
        ("RP_PUMP_LEAK", f"(df['TV_LOAD_LOSS_PCT'] > {L['tv_loss_alert_pct']}) & {card}", "High", "worn_pump"),
        ("RP_TUBING_LEAK", f"({VE} < {L['ve_alert']}) & (df['TV_LOAD_LOSS_PCT'] <= {L['tv_loss_alert_pct']}) & ({fill} >= {k['fill_sp']}) & {card}",
         "High", "tubing_leak"),
        ("RP_GAS_INTERFERENCE", f"({fill} < {k['fill_sp']}) & ({SUB} >= {L['submergence_gas_ft']}) & {card}", "Medium", "gas_interference"),
        ("RP_PRODUCTION_LOW", f"({VE} < {L['ve_alert']}) & {card}", "Medium", "tubing_leak"),
        ("RP_PPRL_HIGH", f"df['PPRL_LB'] / {p['PE']} > {L['pprl_ratio_alert']}", "Medium", "paraffin_drag"),
        ("RP_MPRL_LOW", f"(df['MPRL_LB'] / {p['ME']} < {L['mprl_ratio_alert']}) & {card}", "Medium", "paraffin_drag"),
        ("RP_GEARBOX_HIGH", f"({GB} >= {L['gearbox_warn_pct']}) & ({GB} < {L['gearbox_limit_pct']})", "Medium", None),
        ("RP_OUT_OF_BALANCE", f"({p['BAL']} < {L['balance_low']}) | ({p['BAL']} > {L['balance_high']})", "Medium", "counterbalance_shift"),
        ("RP_UNDERPUMPED", f"({SUB} > {L['submergence_high_ft']}) & ({fill} >= {L['full_fillage_pct']}) & (df['RUNTIME_PCT'] >= {L['runtime_poc_pct']})",
         "Low", None),
    ]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}


def conditions(twin, r, t):
    L = twin["twin_model"]["limits"]
    k = _k(twin)
    out = []

    def add(cond, name, sev, text, part, fm=None):
        if cond:
            out.append({"name": name, "severity": sev, "text": text, "part": part, "failure_mode": fm})
    flr, ve, sub, gb, fill = t["fluid_load_ratio"], t["vol_eff"], t["submergence_ft"], t["gearbox_load_pct"], r["pump_fillage_pct"]
    card = flr >= L["fluid_load_lost_ratio"]
    add(flr < L["fluid_load_lost_ratio"], "RP_ROD_PART", "Critical",
        f"Fluid load on the pump card only {flr * 100:.0f} % of the {t['fo_expected_lb']:.0f} lb expected: the rods are not lifting the fluid (parted rods or unseated pump)",
        "rods", "rod_part")
    add(gb >= L["gearbox_limit_pct"], "RP_GEARBOX_OVERLOAD", "High", f"Gearbox peak torque {max(t['torque_up_kinlb'], t['torque_down_kinlb']):.0f} kin-lb, {gb:.0f} % of the API rating",
        "pumping unit", "paraffin_drag")
    add(r["pprl_lb"] > k["st"], "RP_STRUCTURE_OVERLOAD", "High", f"PPRL {r['pprl_lb']:.0f} lb above the {k['st']:.0f} lb structure rating", "pumping unit")
    add(t["rod_loading_pct"] > L["rod_loading_limit_pct"], "RP_ROD_OVERSTRESS", "High",
        f"Top rod at {t['rod_loading_pct']:.0f} % of the modified Goodman allowable stress", "rods", "paraffin_drag")
    add(fill < k["fill_sp"] and sub < L["submergence_low_ft"] and r["runtime_pct"] > L["runtime_poc_pct"] and card, "RP_FLUID_POUND", "High",
        f"Fillage {fill:.0f} % with only {sub:.0f} ft of liquid over the pump and {r['runtime_pct']:.0f} % run time: fluid pound, pump-off control not stopping",
        "pump", "fluid_pound")
    add(r["tv_load_loss_pct"] > L["tv_loss_alert_pct"] and card, "RP_PUMP_LEAK", "High",
        f"Traveling valve check lost {r['tv_load_loss_pct']:.0f} % of the fluid load in 5 s: worn plunger / barrel or leaking traveling valve", "pump", "worn_pump")
    add(ve < L["ve_alert"] and r["tv_load_loss_pct"] <= L["tv_loss_alert_pct"] and fill >= k["fill_sp"] and card, "RP_TUBING_LEAK", "High",
        f"Full pump ({fill:.0f} %) and tight valves, but only {ve * 100:.0f} % of the pumped volume reaches the surface: hole in the tubing", "tubing", "tubing_leak")
    add(fill < k["fill_sp"] and sub >= L["submergence_gas_ft"] and card, "RP_GAS_INTERFERENCE", "Medium",
        f"Fillage {fill:.0f} % although {sub:.0f} ft of liquid stands over the pump: free gas in the pump", "pump", "gas_interference")
    add(ve < L["ve_alert"] and card, "RP_PRODUCTION_LOW", "Medium",
        f"Liquid rate {r['flow_bpd']:.0f} bbl/d is {ve * 100:.0f} % of the pump displacement {t['pump_displacement_bpd']:.0f} bbl/d", "well", "tubing_leak")
    add(t["pprl_ratio"] > L["pprl_ratio_alert"], "RP_PPRL_HIGH", "Medium", f"PPRL {r['pprl_lb']:.0f} lb, {t['pprl_ratio']:.2f} x expected", "rods", "paraffin_drag")
    add(t["mprl_ratio"] < L["mprl_ratio_alert"] and card, "RP_MPRL_LOW", "Medium", f"MPRL {r['mprl_lb']:.0f} lb, {t['mprl_ratio']:.2f} x expected", "rods", "paraffin_drag")
    add(L["gearbox_warn_pct"] <= gb < L["gearbox_limit_pct"], "RP_GEARBOX_HIGH", "Medium", f"Gearbox at {gb:.0f} % of its rating", "pumping unit")
    add(t["balance_ratio"] < L["balance_low"] or t["balance_ratio"] > L["balance_high"], "RP_OUT_OF_BALANCE", "Medium",
        f"Peak current down / up = {t['balance_ratio']:.2f}: unit out of counterbalance", "pumping unit", "counterbalance_shift")
    add(sub > L["submergence_high_ft"] and fill >= L["full_fillage_pct"] and r["runtime_pct"] >= L["runtime_poc_pct"], "RP_UNDERPUMPED", "Low",
        f"{sub:.0f} ft of liquid over a full pump running all day: the well can give more", "well")
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
