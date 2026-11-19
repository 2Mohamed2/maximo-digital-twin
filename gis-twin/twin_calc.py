"""The gas-insulated switchgear bay twin's expectations (GIS-7401, Hitachi Energy ELK-04 C 145 kV, four SF6 compartments).

One definition, two outputs:
  monitor_expressions(twin) -> pandas expressions for Maximo Monitor PythonExpression functions
  evaluate(twin, reading)   -> the same numbers in Python (tests, figures, the worked example)
Both come from the same formula functions below: they run once on column placeholders (which print themselves as pandas
code) and once on the numbers of a reading, so the two outputs cannot drift apart.

Gas mass balance, per compartment (p = absolute pressure in MPa, T = gas temperature in K):
    Z(p, T) = 1 + p (a0 + a1/T + a2/T^2) + a3 p^2 / T          SF6 compressibility, fitted to NIST data
    rho     = p 1e6 / (R T Z)                                   density, kg/m3 (R = 56.93 J/kg K)
    p20     = rho R 293.15 (1 + q1 rho + q2 rho^2) / 1e6        pressure the same gas has at 20 C (what density monitors show)
    mass    = rho x V                                           kg of SF6 in the compartment
  The gas monitor sends the 30-day trend of p20 (kPa/yr), because Monitor works on one reading at a time. Then
    leak rate (% of the gas per year) = -trend / (rho R 293.15 (1 + 2 q1 rho + 3 q2 rho^2)) x 100   (= -d rho / rho)
    days to the alarm density          = (p20 - p20_alarm) / -trend x 365
  compared with the tightness class (0.5 %/yr; IEC 62271-203:2022 type tests new SF6 compartments to 0.1 %/yr).
Breaker: opening time, trip coil armature time and spring charging time against the routine-test values; contact wear =
  sum of I^2 t (kA^2 s) kept by the bay controller, against the allowance.
Switches: motor peak current and operating time of the busbar disconnector DS1 and the line earthing switch ES2.
Instrument transformers: bay VT against the busbar VT (disconnectors closed); protection core against metering core of the CT.
Bay health index: each of the four parts = 100 - 60 x u_worst, with u = (value - normal) / (limit - normal) clipped to 0..1.5,
  so a part reads 100 when every indicator is normal, 40 with one indicator at its limit and 10 at most 1.5 x beyond.
  The bay health index is the weakest part: a bay is only as available as its worst part.
"""
import math

COMPS = ("cb", "bb", "ld", "vt")
T20 = 293.15


# ---- column placeholders that print themselves as pandas code ----------------------------------------------------------
def _s(x):
    return x.s if isinstance(x, E) else repr(float(x)) if not isinstance(x, int) else str(x)


class E:
    def __init__(self, s):
        self.s = s

    def _b(self, op, o, rev=False):
        return E(f"({_s(o)} {op} {self.s})" if rev else f"({self.s} {op} {_s(o)})")

    __add__ = lambda a, o: a._b("+", o)
    __radd__ = lambda a, o: a._b("+", o, True)
    __sub__ = lambda a, o: a._b("-", o)
    __rsub__ = lambda a, o: a._b("-", o, True)
    __mul__ = lambda a, o: a._b("*", o)
    __rmul__ = lambda a, o: a._b("*", o, True)
    __truediv__ = lambda a, o: a._b("/", o)
    __rtruediv__ = lambda a, o: a._b("/", o, True)
    __pow__ = lambda a, o: a._b("**", o)
    __lt__ = lambda a, o: a._b("<", o)
    __gt__ = lambda a, o: a._b(">", o)
    __and__ = lambda a, o: a._b("&", o)
    __rand__ = lambda a, o: a._b("&", o, True)
    __or__ = lambda a, o: a._b("|", o)
    __ror__ = lambda a, o: a._b("|", o, True)
    __neg__ = lambda a: E(f"(-{a.s})")


def _any_e(xs):
    return any(isinstance(x, E) for x in xs)


def mx(*xs):
    if not _any_e(xs):
        return max(xs)
    out = _s(xs[0])
    for x in xs[1:]:
        out = f"np.maximum({out}, {_s(x)})"
    return E(out)


def mn(*xs):
    if not _any_e(xs):
        return min(xs)
    out = _s(xs[0])
    for x in xs[1:]:
        out = f"np.minimum({out}, {_s(x)})"
    return E(out)


def ab(x):
    return E(f"np.abs({x.s})") if isinstance(x, E) else abs(x)


def clip(x, lo, hi):
    return E(f"np.clip({x.s}, {_s(lo)}, {_s(hi)})") if isinstance(x, E) else min(max(x, lo), hi)


def anyof(*xs):
    out = xs[0]
    for x in xs[1:]:
        out = out | x
    return out


# ---- constants from the twin file ----------------------------------------------------------------------------------------
def _k(twin):
    d = twin["design"]
    s, b, sw, g, pd, ins = d["sf6"], d["breaker"], d["switches"], d["gas_quality"], d["pd"], d["instr"]
    k = dict(R=s["r_j_kgk"], a=s["eos_a"], q=s["eos_q"], gwp=s["gwp100"],
             open=b["open_ms"], close=b["close_ms"], arm=b["armature_ms"], coil=b["coil_v"] / b["coil_r_ohm"], charge=b["charge_s"],
             allow=b["wear_allow_ka2s"], ds1m=sw["ds1_motor_a"], ds1t=sw["ds1_time_s"], es2m=sw["es2_motor_a"], es2t=sw["es2_time_s"],
             noise=pd["noise_dbm"], h2o0=60.0)
    for c in COMPS:
        cc = d["compartments"][c]
        k[c] = dict(V=cc["volume_m3"], fill=cc["fill_mpa"], alarm=cc["alarm_mpa"], minimum=cc["minimum_mpa"], name=cc["name"])
    return k


# ---- the formulas (run on placeholders or on numbers) ------------------------------------------------------------------
def rho(k, r, c):
    p, T = r(f"gas_{c}_p_mpa"), r(f"gas_{c}_t_c") + 273.15
    a = k["a"]
    return p * 1e6 / (k["R"] * T * (1 + p * (a[0] + a[1] / T + a[2] / T ** 2) + a[3] * p ** 2 / T))


def p20(k, r, c):
    d = rho(k, r, c)
    return d * k["R"] * T20 * (1 + k["q"][0] * d + k["q"][1] * d ** 2) / 1e6


def leak_pct(k, r, c):
    d = rho(k, r, c)
    return mx(-r(f"gas_{c}_slope_kpa_yr") * 1000 / (d * k["R"] * T20 * (1 + 2 * k["q"][0] * d + 3 * k["q"][1] * d ** 2)) * 100, 0)


def days(k, r, c):
    return mn(mx((p20(k, r, c) - k[c]["alarm"]) * 1000 / mx(-r(f"gas_{c}_slope_kpa_yr"), 0.01) * 365, 0), 9999)


def u(x, normal, limit, umax=1.5):
    return clip((x - normal) / (limit - normal), 0, umax)


def _formulas(twin, r):
    k, L = _k(twin), twin["twin_model"]["limits"]
    P = {c: p20(k, r, c) for c in COMPS}
    f = {f"p20_{c}_mpa": P[c] for c in COMPS}
    f["sf6_mass_kg"] = rho(k, r, "cb") * k["cb"]["V"] + rho(k, r, "bb") * k["bb"]["V"] + rho(k, r, "ld") * k["ld"]["V"] + rho(k, r, "vt") * k["vt"]["V"]
    LEAK = mx(*[leak_pct(k, r, c) for c in COMPS])
    DAYS = mn(*[days(k, r, c) for c in COMPS])
    f["leak_pct_yr_max"] = LEAK
    f["days_to_alarm_min"] = DAYS
    OPEN = r("cb_open_ms") / k["open"]
    ARM = r("cb_armature_ms") / k["arm"]
    CHG = r("cb_charge_s") / k["charge"]
    WEAR = r("cb_wear_ka2s") / k["allow"] * 100
    COIL = ab(r("cb_trip_coil_a") / k["coil"] - 1)
    f["cb_open_ratio"], f["cb_charge_ratio"], f["cb_wear_pct"] = OPEN, CHG, WEAR
    DSM = mx(r("ds1_motor_a") / k["ds1m"], r("es2_motor_a") / k["es2m"])
    DST = mx(r("ds1_time_s") / k["ds1t"], r("es2_time_s") / k["es2t"])
    f["ds_motor_ratio"] = DSM
    VT = (r("vt_bay_kv") - r("vt_bus_kv")) / r("vt_bus_kv") * 100
    CT = (r("ct_prot_a") - r("ct_meas_a")) / mx(r("ct_meas_a"), 1) * 100
    f["vt_drift_pct"], f["ct_mismatch_pct"] = VT, CT
    PD = mx(*[r(f"pd_{c}_dbm") for c in COMPS])
    H2O = mx(*[r(f"gas_{c}_h2o_ppmv") for c in COMPS])
    f["pd_max_dbm"] = PD
    DEF = mx(*[(k[c]["fill"] - P[c]) / (k[c]["fill"] - k[c]["alarm"]) for c in COMPS])
    hi = lambda *us: 100 - 60 * mx(*us)
    f["hi_cb"] = hi(u(OPEN, 1, L["open_ratio"]), u(ARM, 1, L["armature_ratio"]), u(CHG, 1, L["charge_ratio"]), u(WEAR, 0, L["wear_pct"]),
                    u(COIL, 0, L["coil_dev"]))
    f["hi_ds"] = hi(u(DSM, 1, L["ds_motor_ratio"]), u(DST, 1, L["ds_time_ratio"]))
    f["hi_gas"] = hi(clip(DEF, 0, 1.5), u(LEAK, 0, L["leak_pct_yr"]), u(H2O, k["h2o0"], L["h2o_ppmv"]), u(r("cb_so2_ppmv"), 0, L["so2_ppmv"]),
                     u(PD, k["noise"], L["pd_dbm"]))
    f["hi_it"] = hi(u(ab(VT), 0, L["vt_drift_pct"]), u(ab(CT), 0, L["ct_mismatch_pct"]))
    f["hi_bay"] = mn(f["hi_cb"], f["hi_ds"], f["hi_gas"], f["hi_it"])
    rules = [
        ("GIS_DENSITY_ALARM", anyof(*[P[c] < k[c]["alarm"] for c in COMPS]), "Critical", "cb_compartment_leak"),
        ("GIS_DENSITY_ALARM_SOON", DAYS < L["days_to_alarm"], "High", "cb_compartment_leak"),
        ("GIS_PD_DETECTED", anyof(*[(r(f"pd_{c}_dbm") > L["pd_dbm"]) & (r(f"pd_{c}_pps") > L["pd_pps"]) for c in COMPS]), "High", "internal_pd"),
        ("GIS_SO2_HIGH", r("cb_so2_ppmv") > L["so2_ppmv"], "High", "cb_contact_wear"),
        ("GIS_CB_SLOW_OPEN", OPEN > L["open_ratio"], "High", "cb_slow_mechanism"),
        ("GIS_LEAK_RATE_HIGH", LEAK > L["leak_pct_yr"], "Medium", "cb_compartment_leak"),
        ("GIS_DENSITY_ABOVE_FILL", anyof(*[P[c] > k[c]["fill"] + L["above_fill_mpa"] for c in COMPS]), "Medium", "density_sensor_drift"),
        ("GIS_CB_TRIP_COIL", ARM > L["armature_ratio"], "Medium", "cb_slow_mechanism"),
        ("GIS_CB_CHARGE_SLOW", CHG > L["charge_ratio"], "Medium", None),
        ("GIS_CB_WEAR_HIGH", WEAR > L["wear_pct"], "Medium", "cb_contact_wear"),
        ("GIS_DS_MOTOR_HIGH", DSM > L["ds_motor_ratio"], "Medium", "ds_motor_wear"),
        ("GIS_DS_SLOW", DST > L["ds_time_ratio"], "Medium", "ds_motor_wear"),
        ("GIS_MOISTURE_HIGH", H2O > L["h2o_ppmv"], "Medium", "moisture_ingress"),
        ("GIS_VT_DRIFT", ab(VT) > L["vt_drift_pct"], "Medium", "vt_drift"),
        ("GIS_CT_MISMATCH", ab(CT) > L["ct_mismatch_pct"], "Medium", None),
    ]
    extra = dict(arm_ratio=ARM, ds_time_ratio=DST, h2o_max=H2O, coil_dev=COIL, gas_deficit=DEF,
                 **{f"leak_{c}": leak_pct(k, r, c) for c in COMPS}, **{f"days_{c}": days(k, r, c) for c in COMPS},
                 **{f"rho_{c}": rho(k, r, c) for c in COMPS})
    return f, rules, extra


def _col(name):
    return E(f"df['{name.upper()}']")


def monitor_expressions(twin):
    f, _, _ = _formulas(twin, _col)
    return [(n.upper(), v.s) for n, v in f.items()]


def evaluate(twin, reading):
    f, _, _ = _formulas(twin, lambda n: float(reading[n]))
    return dict(f)


def details(twin, reading):
    """Per-compartment numbers that the rules use inline (density, leak rate, days) for figures and the post."""
    _, _, x = _formulas(twin, lambda n: float(reading[n]))
    return x


def alert_rules(twin):
    _, rules, _ = _formulas(twin, _col)
    return [(n, e.s, sev, fm) for n, e, sev, fm in rules]


SEVERITY_PENALTY = {"Critical": 60, "High": 30, "Medium": 15, "Low": 5}
PART = {"cb_compartment_leak": "gas", "density_sensor_drift": "gas", "internal_pd": "gas", "moisture_ingress": "gas", "cb_slow_mechanism": "breaker",
        "cb_contact_wear": "breaker", "ds_motor_wear": "switches", "vt_drift": "instr", None: "bay"}


def conditions(twin, r, t):
    k, L = _k(twin), twin["twin_model"]["limits"]
    _, rules, x = _formulas(twin, lambda n: float(r[n]))
    worst_p = min(COMPS, key=lambda c: t[f"p20_{c}_mpa"] - k[c]["alarm"])
    worst_leak = max(COMPS, key=lambda c: x[f"leak_{c}"])
    worst_pd = max(COMPS, key=lambda c: r[f"pd_{c}_dbm"])
    worst_h2o = max(COMPS, key=lambda c: r[f"gas_{c}_h2o_ppmv"])
    worst_fill = max(COMPS, key=lambda c: t[f"p20_{c}_mpa"] - k[c]["fill"])
    text = {
        "GIS_DENSITY_ALARM": f"{worst_p.upper()} compartment at {t[f'p20_{worst_p}_mpa']:.3f} MPa (20 °C), below its alarm density {k[worst_p]['alarm']:.2f}",
        "GIS_DENSITY_ALARM_SOON": f"{worst_p.upper()} compartment reaches its alarm density in {t['days_to_alarm_min']:.0f} days at the present leak rate",
        "GIS_PD_DETECTED": f"Partial discharge on the {worst_pd.upper()} sensor: {r[f'pd_{worst_pd}_dbm']:.0f} dBm, {r[f'pd_{worst_pd}_pps']:.0f} pulses/s",
        "GIS_SO2_HIGH": f"SO2 {r['cb_so2_ppmv']:.1f} ppmv in the CB compartment (action level {L['so2_ppmv']:.0f})",
        "GIS_CB_SLOW_OPEN": f"Opening time {r['cb_open_ms']:.1f} ms, {t['cb_open_ratio']:.2f} x the routine test",
        "GIS_LEAK_RATE_HIGH": f"{worst_leak.upper()} compartment loses {t['leak_pct_yr_max']:.2f} % of its gas per year (class {L['leak_pct_yr']} %)",
        "GIS_DENSITY_ABOVE_FILL": f"{worst_fill.upper()} density reads {t[f'p20_{worst_fill}_mpa']:.3f} MPa, above the filled {k[worst_fill]['fill']:.2f}: sensor drift",
        "GIS_CB_TRIP_COIL": f"Trip coil armature time {r['cb_armature_ms']:.1f} ms, {x['arm_ratio']:.2f} x the routine test",
        "GIS_CB_CHARGE_SLOW": f"Spring charging took {r['cb_charge_s']:.1f} s, {t['cb_charge_ratio']:.2f} x normal",
        "GIS_CB_WEAR_HIGH": f"Contact wear {t['cb_wear_pct']:.0f} % of the I²t allowance",
        "GIS_DS_MOTOR_HIGH": f"Switch drive motor current {t['ds_motor_ratio']:.2f} x the routine test",
        "GIS_DS_SLOW": f"Switch operating time {x['ds_time_ratio']:.2f} x the routine test",
        "GIS_MOISTURE_HIGH": f"Moisture {r[f'gas_{worst_h2o}_h2o_ppmv']:.0f} ppmv in the {worst_h2o.upper()} compartment",
        "GIS_VT_DRIFT": f"Bay VT reads {t['vt_drift_pct']:+.2f} % against the busbar VT",
        "GIS_CT_MISMATCH": f"CT protection and metering cores differ by {t['ct_mismatch_pct']:+.2f} %",
    }
    out = []
    for name, cond, sev, fm in rules:
        if cond:
            out.append({"name": name, "severity": sev, "text": text[name], "part": PART[fm], "failure_mode": fm})
    health = max(0, 100 - sum(SEVERITY_PENALTY[c["severity"]] for c in out))
    return out, health
