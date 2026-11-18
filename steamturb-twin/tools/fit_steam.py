"""Fit the twin's short steam correlations to IAPWS-IF97 and report their errors (development tool, run once).

    pip install iapws numpy
    python tools/fit_steam.py
Prints the coefficients written in build_twin.py (design.steam_props) and the largest errors against IF97:
  h(P, T)  = a0 + a1 T + a2 T^2 + c1 (T/600)^-n P + c2 (T/600)^-m P^2       superheated steam enthalpy, kJ/kg
  P.v(P,T) = b0 T + b1 (T/600)^-n P + b2 (T/600)^-m P^2                     kJ/kg
  dh_isentropic = k / (k - 1) P1 v1 (1 - (P2/P1)^((k-1)/k))                  best k over the HP operating range
  log10(p_sat [mbar]) = A - B / (T [C] + C)                                  25 to 70 C
P in bar(a), T in K unless noted. Grid: 5 to 125 bar(a), saturation + 20 K to 560 C.
"""
import numpy as np
from iapws import IAPWS97

TR = 600.0


def fit():
    rows = []
    for p in np.linspace(5, 125, 25):
        ts = IAPWS97(P=p / 10, x=1).T
        for t in np.linspace(ts + 20, 833.15, 30):
            s = IAPWS97(P=p / 10, T=t)
            rows.append((p, t, s.h, s.v * p * 100))
    P, T, H, PV = np.array(rows).T
    best = None
    for n in np.arange(2, 10.01, 0.5):
        for m in np.arange(4, 16.01, 1):
            A = np.c_[np.ones_like(T), T, T ** 2, (T / TR) ** -n * P, (T / TR) ** -m * P ** 2]
            co, *_ = np.linalg.lstsq(A, H, rcond=None)
            err = np.abs(A @ co - H).max()
            if best is None or err < best[0]:
                best = (err, n, m, co)
    print("h: max error %.2f kJ/kg, n=%g m=%g, a0 a1 a2 c1 c2 =" % best[:3], best[3])
    bv = None
    for n in np.arange(2, 10.01, 0.5):
        for m in np.arange(4, 16.01, 1):
            A = np.c_[T, (T / TR) ** -n * P, (T / TR) ** -m * P ** 2]
            co, *_ = np.linalg.lstsq(A, PV, rcond=None)
            err = np.abs(A @ co / PV - 1).max()
            if bv is None or err < bv[0]:
                bv = (err, n, m, co)
    print("Pv: max error %.3f %%, n=%g m=%g, b0 b1 b2 =" % (bv[0] * 100, bv[1], bv[2]), bv[3])
    b0, b1, b2 = bv[3]
    pv = lambda p, t: b0 * t + b1 * (t / TR) ** -bv[1] * p + b2 * (t / TR) ** -bv[2] * p * p
    cases = []
    for p1 in (60, 75, 90, 100, 110):
        for t1 in (460, 480, 500, 520):
            for p2 in (8, 10, 12, 14, 16):
                st = IAPWS97(P=p1 / 10, T=t1 + 273.15)
                out = IAPWS97(P=p2 / 10, s=st.s)
                if out.x < 1:          # the HP section ends superheated: skip wet end points
                    continue
                cases.append((p1, t1 + 273.15, p2, st.h - out.h))
    c = np.array(cases)
    ks = np.arange(1.25, 1.35, 0.001)
    errs = [np.abs(k / (k - 1) * pv(c[:, 0], c[:, 1]) * (1 - (c[:, 2] / c[:, 0]) ** ((k - 1) / k)) / c[:, 3] - 1).max() for k in ks]
    i = int(np.argmin(errs))
    print("k_hp = %.3f, max error of the isentropic drop %.2f %%" % (ks[i], errs[i] * 100))
    tc = np.linspace(25, 70, 46)
    ps = np.array([IAPWS97(T=t + 273.15, x=0).P * 1e4 for t in tc])
    A = np.c_[np.ones_like(tc), -1 / (tc + 234.0)]
    co, *_ = np.linalg.lstsq(A, np.log10(ps), rcond=None)
    print("Antoine (C = 234): A = %.8f B = %.8f, max error %.3f %%" % (co[0], co[1], np.abs(10 ** (A @ co) / ps - 1).max() * 100))


if __name__ == "__main__":
    fit()
