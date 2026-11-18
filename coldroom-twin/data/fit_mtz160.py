"""Fit the data the RF-6901 twin uses for its R448A compressors and refrigerant (run once; needs numpy and CoolProp).

    python fit_mtz160.py        -> mtz160_r448a_fit.json

What is published, and what is fitted here
  Danfoss Maneurop MTZ application guidelines AB196386425654en-021701 (2024.02):
    MTZ160-4 displacement 271.55 cm3/rev, 47.25 m3/h at 2900 rpm, 4 cylinders.
    R448A, 50 Hz, EN 12900 rating to = -10 C, tc = 45 C (dew), SC 0 K, SH 10 K: 20140 W, 9.87 kW, 17.11 A, COP 2.04.
    R448A, 50 Hz, ARI rating to = -6.7 C, tc = 48.9 C (dew), SC 0 K, SH 11.1 K: 21830 W, 10.87 kW.
    Maximum discharge gas temperature 135 C; normal suction superheat 5 to 30 K; R448A glide about 6.1 K; GWP 1387 (as stated).
  Hudson Technologies R-448A pressure temperature chart: saturated liquid (bubble) and vapour (dew) pressure in psig against
    temperature, and liquid density in lb/ft3 at -80 ... 120 F.

  ASSUMPTION (fitted here, replace with the maker's EN 12900 coefficients from Danfoss Coolselector2):
    The two published rating points are not a performance map. A simple compressor model (volumetric efficiency with a
    clearance term, overall isentropic efficiency, R448A properties from CoolProp) is calibrated on the EN 12900 point,
    checked against the ARI point, evaluated over to = -20 ... 0 C and tc = 20 ... 55 C, and fitted with the 10-coefficient
    third-order polynomial of EN 12900. The discharge temperature is fitted as T_dis = T_suc x PR^m (kelvin).
"""
import json
from pathlib import Path

import numpy as np
import CoolProp.CoolProp as CP

HERE = Path(__file__).parent
F = "R448A.mix"
PSI = 0.0689476
VS = 47.25 / 3600            # m3/s at 2900 rpm
CLEAR, KAPPA = 0.045, 1.10   # clearance ratio and re-expansion exponent: assumption, typical reciprocating compressor
LOSS = 0.08                  # share of power lost to ambient from the shell: assumption (suction-gas cooled hermetic)

# Hudson Technologies R-448A PT chart (psig): deg F, liquid (bubble), vapour (dew)
HUDSON = [(-40, 4.9, 0.0), (-30, 10.4, 4.4), (-20, 17.0, 9.8), (-10, 24.9, 16.4), (0, 34.2, 24.3), (10, 45.1, 33.6),
          (20, 57.8, 44.6), (30, 72.3, 57.3), (40, 89.0, 72.1), (50, 108.0, 89.0), (60, 129.0, 108.0), (70, 154.0, 130.0),
          (80, 181.0, 155.0), (90, 211.0, 183.0), (100, 244.0, 214.0), (110, 281.0, 249.0), (120, 321.0, 288.0),
          (130, 365.0, 331.0), (140, 414.0, 379.0)]
DENS = [(-80, 87.25), (-40, 83.11), (0, 78.66), (40, 73.73), (80, 68.03), (120, 60.91)]   # lb/ft3


def antoine(tc, pa):
    """Fit T(C) = B / (A - ln p) - C to (T, p bar a) by a grid over C and linear least squares for A, B."""
    best = None
    for c in np.arange(200.0, 320.0, 0.25):
        x = 1.0 / (tc + c)
        M = np.vstack([np.ones_like(x), -x]).T
        (a, b), *_ = np.linalg.lstsq(M, np.log(pa), rcond=None)
        t_fit = b / (a - np.log(pa)) - c
        err = np.max(np.abs(t_fit - tc))
        if best is None or err < best[0]:
            best = (err, a, b, c)
    return {"A": round(float(best[1]), 6), "B": round(float(best[2]), 4), "C": round(float(best[3]), 2), "max_err_K": round(float(best[0]), 3)}


def state(to, tc, sh):
    ps = CP.PropsSI("P", "T", to + 273.15, "Q", 1, F)
    pc = CP.PropsSI("P", "T", tc + 273.15, "Q", 1, F)
    ts = to + sh + 273.15
    hs, ss, ds = (CP.PropsSI(k, "T", ts, "P", ps, F) for k in ("H", "S", "D"))
    hl = CP.PropsSI("H", "P", pc, "Q", 0, F)
    his = CP.PropsSI("H", "P", pc, "S", ss, F)
    return ps, pc, ts, hs, ds, hl, his


def model(to, tc, sh, d, eta):
    ps, pc, ts, hs, ds, hl, his = state(to, tc, sh)
    pr = pc / ps
    ev = 1 - CLEAR * (pr ** (1 / KAPPA) - 1) - d
    m = ev * VS * ds
    q = m * (hs - hl) / 1000
    p = m * (his - hs) / eta / 1000
    hd = hs + p * 1000 * (1 - LOSS) / m
    td = CP.PropsSI("T", "P", pc, "H", hd, F) - 273.15
    return q, p, td, pr, ts - 273.15


def calibrate():
    # volumetric loss d from the capacity, efficiency from the power, at the EN 12900 point
    d, eta = 0.05, 0.6
    for _ in range(30):
        q, p, *_ = model(-10, 45, 10, d, eta)
        d += (q - 20.14) / 20.14 * 0.8 * (1 - d)
        eta *= p / 9.87
    return d, eta


def poly_terms(to, tc):
    return np.array([np.ones_like(to), to, tc, to ** 2, to * tc, tc ** 2, to ** 3, tc * to ** 2, to * tc ** 2, tc ** 3]).T


if __name__ == "__main__":
    t = np.array([(f - 32) / 1.8 for f, _, _ in HUDSON])
    pb = np.array([l * PSI + 1.01325 for _, l, _ in HUDSON])
    pd = np.array([v * PSI + 1.01325 for _, _, v in HUDSON])
    dew, bub = antoine(t, pd), antoine(t, pb)
    td = np.array([(f - 32) / 1.8 for f, _ in DENS])
    rho = np.array([x * 16.0185 for _, x in DENS])
    rc = np.polyfit(td, rho, 2)
    d, eta = calibrate()
    q1, p1, t1, *_ = model(-10, 45, 10, d, eta)
    q2, p2, t2, *_ = model(-6.7, 48.9, 11.1, d, eta)
    TO, TC, Q, P, TD, PRR, TS = [], [], [], [], [], [], []
    for to in np.arange(-20, 0.1, 2.5):
        for tc in np.arange(20, 55.1, 2.5):
            q, p, tdis, pr, ts = model(to, tc, 10, d, eta)
            TO.append(to); TC.append(tc); Q.append(q); P.append(p); TD.append(tdis); PRR.append(pr); TS.append(ts)
    TO, TC, Q, P, TD, PRR, TS = map(np.array, (TO, TC, Q, P, TD, PRR, TS))
    X = poly_terms(TO, TC)
    cq, *_ = np.linalg.lstsq(X, Q, rcond=None)
    cp, *_ = np.linalg.lstsq(X, P, rcond=None)
    eq = np.max(np.abs(X @ cq - Q) / Q) * 100
    ep = np.max(np.abs(X @ cp - P) / P) * 100
    # discharge: T_dis_K = T_suc_K * PR^m
    mexp = float(np.sum(np.log((TD + 273.15) / (TS + 273.15)) * np.log(PRR)) / np.sum(np.log(PRR) ** 2))
    etd = np.max(np.abs((TS + 273.15) * PRR ** mexp - 273.15 - TD))
    out = {
        "compressor": "Danfoss Maneurop MTZ160-4 (R448A, 50 Hz)",
        "published": {"en12900": {"to": -10, "tc": 45, "sh": 10, "sc": 0, "q_w": 20140, "p_kw": 9.87, "i_a": 17.11, "cop": 2.04},
                      "ari": {"to": -6.7, "tc": 48.9, "sh": 11.1, "sc": 0, "q_w": 21830, "p_kw": 10.87},
                      "displacement_m3h": 47.25, "rpm": 2900, "cylinders": 4, "t_dis_max_c": 135,
                      "source": "Danfoss application guidelines Maneurop MT/MTZ, AB196386425654en-021701 (2024.02)"},
        "model": {"clearance": CLEAR, "kappa": KAPPA, "shell_loss": LOSS, "vol_loss_d": round(d, 5), "eta_overall": round(eta, 5),
                  "check_en12900": {"q_kw": round(q1, 3), "p_kw": round(p1, 3), "t_dis_c": round(t1, 1)},
                  "check_ari": {"q_kw": round(q2, 3), "p_kw": round(p2, 3), "t_dis_c": round(t2, 1),
                                "q_dev_pct": round((q2 / 21.83 - 1) * 100, 2), "p_dev_pct": round((p2 / 10.87 - 1) * 100, 2)}},
        "polynomial": {"form": "X = c1 + c2 to + c3 tc + c4 to^2 + c5 to tc + c6 tc^2 + c7 to^3 + c8 tc to^2 + c9 to tc^2 + c10 tc^3 (to, tc dew, C)",
                       "range": "to -20 ... 0 C, tc 20 ... 55 C, SH 10 K, SC 0 K",
                       "q_kw": [float(f"{c:.8g}") for c in cq], "p_kw": [float(f"{c:.8g}") for c in cp],
                       "max_fit_err_pct": {"q": round(float(eq), 3), "p": round(float(ep), 3)}},
        "discharge": {"m": round(mexp, 5), "max_fit_err_K": round(float(etd), 2)},
        "r448a": {"dew": dew, "bubble": bub, "rho_liq_poly": [float(f"{c:.8g}") for c in rc],
                  "source": "Hudson Technologies R-448A pressure temperature chart (psig converted to bar a with 1.01325 bar), "
                            "liquid density table (lb/ft3 x 16.0185); fitted here"},
    }
    (HERE / "mtz160_r448a_fit.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
