"""Build twin/ugc-801.twin.json: a 3.6 km 132 kV XLPE underground circuit (three single cores in trefoil, cross-bonded)
with distributed temperature sensing (DTS) fibre, on a Prysmian 132 kV XLPE 1200 mm2 Al cable.

Sources (public, read 2026-11-10):
  Prysmian data sheet R89BD901200MIJNE "132 kV XLP 1200 mm2 Al LS0H SC IEC 60840" (version 05-oct-21)
    https://mx.prysmian.com/sites/mx.prysmian.com/files/media/documents/R89BD901200MIJNE%20132%20kV%20XLP%201200%20mm2%20Al%20IEC.pdf
    conductor Al compact class 2, 1200 mm2, diameter 41.85 mm; conductor screen 1.2 mm (45.63); XLPE 16.0 mm (77.63);
    insulation screen 1.6 mm (80.83); water-blocking tape 0.3 mm (81.43); copper wire screen 50 x 2.052 mm = 165 mm2 (86.39);
    water-blocking tape 0.25 mm (87.39); aluminium tape 0.2 mm (88.00); LS0H jacket 5.0 mm, outer diameter 98.4 mm;
    R20 dc 0.0247 ohm/km; capacitance 0.2402 uF/km; Um 145 kV, Up 650 kV; 90 C continuous, 250 C short circuit;
    short circuit 160 kA conductor / 31.5 kA screen (0.5 s); 11 408 kg/km; bending radius 2.46 m (laying) / 1.97 m.
  Current ratings are NOT in the data sheet: the twin computes them with the IEC 60287-1-1 / 60287-2-1 steady-state method
    (formulas as published in the standard; material constants from its tables: rho XLPE 3.5 K.m/W, tan delta 0.001,
    alpha20 Al 0.00403 /K, Cu 0.00393 /K). Background on HV ratings: https://elek.com/articles/high-voltage-power-cable-current-ratings/
  Transient behaviour (IEC 60853 two time constants) is represented by a fast cable lag and a slow soil lag (demo-compressed).
Assumptions (labelled in the twin): route 3.6 km, burial depth 1.2 m (trefoil touching, direct buried, rho soil 1.2 K.m/W,
  soil ambient 25 C), road crossing in PE ducts in concrete at 1.8 m (km 1.80-2.10), cross-bonded in two major sections
  (joints every 600 m), residual sheath loss factor 0.02 when cross-bonded, DTS fibre in the screen of the middle phase,
  PD measured with an HFCT on the earth lead of joint J4, IR sensor on the outdoor sealing end A.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).parent
F, U0 = 50.0, 132e3 / math.sqrt(3)
W = 2 * math.pi * F

# ---------------- Prysmian construction (mm) ----------------
DC, D_INS_SCR, DI, D_WB, D_SCR, DA, DE = 41.85, 80.83, 77.63, 81.43, 86.39, 88.00, 98.4
R20 = 0.0247e-3                    # ohm/m dc at 20 C
ALPHA_AL, ALPHA_CU = 0.00403, 0.00393
C = 0.2402e-6 / 1000               # F/m
TAND = 0.001
SCREEN_MM2 = 165.0

# ---------------- IEC 60287-1-1 losses ----------------
r90 = R20 * (1 + ALPHA_AL * 70)
xs4 = (8 * math.pi * F / r90 * 1e-7 * 1.0) ** 2           # ks = 1 (compact round stranded)
ys = xs4 / (192 + 0.8 * xs4)
dc_s = DC / DE                                             # trefoil touching: axial spacing = outer diameter
fp = xs4 / (192 + 0.8 * xs4)                               # kp = 1 (extruded insulation)
yp = fp * dc_s ** 2 * (0.312 * dc_s ** 2 + 1.18 / (fp + 0.27))
WD = W * C * U0 ** 2 * TAND                                # dielectric loss W/m per phase
ds = (D_WB + D_SCR) / 2                                    # mean diameter of the wire screen
rs20 = 1.7241e-8 / (SCREEN_MM2 * 1e-6)
rs = rs20 * (1 + ALPHA_CU * 50)                            # screen at ~70 C
xm = 2 * W * 1e-7 * math.log(2 * DE / ds)                  # trefoil
r_ac90 = r90 * (1 + ys + yp)
lam_solid = rs / r_ac90 / (1 + (rs / xm) ** 2)             # both-ends (solid) bonding: circulating currents
LAM_XB = 0.02                                              # cross-bonded: residual (assumed, imperfect section balance)

# ---------------- IEC 60287-2-1 thermal resistances (K.m/W) ----------------
RHO_XLPE, RHO_JACKET = 3.5, 3.5
t1 = (DA - DC) / 2 - (DA - D_WB) / 2                        # conductor to screen: semicons + XLPE + tape
T1 = RHO_XLPE / (2 * math.pi) * math.log(1 + 2 * t1 / DC)
t3 = (DE - DA) / 2
T3 = RHO_JACKET / (2 * math.pi) * math.log(1 + 2 * t3 / DA)
RHO_SOIL, DEPTH, DEPTH_X = 1.2, 1.2, 1.8
u = 2 * DEPTH / (DE / 1000)
T4N = 1.5 / math.pi * RHO_SOIL * (math.log(2 * u) - 0.630)          # trefoil touching, direct buried
# road crossing: each cable in a 160 mm PE duct (SDR 17) in a concrete bank at 1.8 m
T4P = 1.87 / (1 + 0.1 * (0.312 + 0.0037 * 55) * DE)                 # cable to duct (plastic duct, theta_m 55 C)
T4PP = 3.5 / (2 * math.pi) * math.log(160 / 141.2)                  # duct wall
ux = 2 * DEPTH_X / 0.160
T4PPP = 1.5 / math.pi * RHO_SOIL * (math.log(2 * ux) - 0.630)       # duct group, trefoil formula on the duct diameter
T4X = T4P + T4PP + T4PPP
THETA_MAX, SOIL_AMB = 90.0, 25.0


def rating(t4, theta_amb=SOIL_AMB, lam=LAM_XB):
    num = THETA_MAX - theta_amb - WD * (0.5 * T1 + (T3 + t4))
    den = r_ac90 * (T1 + (1 + lam) * (T3 + t4))
    return math.sqrt(num / den)


I_N, I_X = rating(T4N), rating(T4X)
I_X_SOLID = rating(T4X, lam=lam_solid)
LENGTH_KM, NSEG = 3.6, 12
SEG_KM = LENGTH_KM / NSEG
CROSS_SEG = 6                                    # 0-based: km 1.80-2.10 (road crossing)
JOINTS = {"J1": 0.6, "J2": 1.2, "J3": 1.8, "J4": 2.4, "J5": 3.0}


def P(metric, path, label, unit, rng, noise, opc=None):
    return {"metric": metric, "path": path, "label": label, "unit": unit, "range": rng, "noise": noise, "opc": opc}


points = [
    P("current_l1_a", "Load.CurrentL1", "Load current L1", "A", [0, 2000], 1.0, "IEC 61850: MMXU.A.phsA"),
    P("current_l2_a", "Load.CurrentL2", "Load current L2", "A", [0, 2000], 1.0, "IEC 61850: MMXU.A.phsB"),
    P("current_l3_a", "Load.CurrentL3", "Load current L3", "A", [0, 2000], 1.0, "IEC 61850: MMXU.A.phsC"),
    P("load_eq_a", "Rttr.EquivalentCurrent", "Equivalent current over the soil time constant (RTTR unit)", "A", [0, 2000], 0.5,
      "IEC 61850: ZCAB (thermal image)"),
    P("voltage_kv", "Load.Voltage", "Voltage (line to line)", "kV", [0, 160], 0.05, "IEC 61850: MMXU.PPV"),
    P("soil_ambient_c", "Soil.AmbientTemp", "Soil ambient at cable depth (reference, 5 m from the trench)", "degC", [-10, 60], 0.05),
    P("air_temp_c", "Weather.AirTemp", "Air temperature at the terminations", "degC", [-20, 60], 0.1, "IEC 61850: MMET.EnvTmp"),
] + [P(f"dts_seg{i + 1:02d}_c", f"Dts.Segment{i + 1:02d}", f"DTS max temperature km {i * SEG_KM:.1f}-{(i + 1) * SEG_KM:.1f}"
        + (" (road crossing)" if i == CROSS_SEG else ""), "degC", [-10, 150], 0.15) for i in range(NSEG)] + [
    P("dts_max_c", "Dts.MaxTemp", "DTS hottest point on the route (screen temperature)", "degC", [-10, 150], 0.15, "IEC 61850: STMP.Tmp"),
    P("dts_max_km", "Dts.MaxLocation", "DTS hottest point location", "km", [0, 4], 0.0),
    P("dts_fibre_km", "Dts.FibreLength", "DTS measured fibre length (signal end)", "km", [0, 5], 0.0),
    P("sheath_current_a", "Bonding.SheathCurrent", "Sheath current at the earthing link (J3)", "A", [0, 800], 0.4),
    P("sheath_voltage_v", "Bonding.SheathVoltage", "Sheath standing voltage at link box J2", "V", [0, 400], 0.3),
    P("sheath_leakage_ma", "Bonding.JacketLeakage", "Jacket leakage current (sheath voltage limiters)", "mA", [0, 100], 0.02),
    P("pd_joint_pc", "Pd.JointJ4", "Partial discharge, joint J4 (HFCT on the earth lead)", "pC", [0, 5000], 1.5, "IEC 61850: SPDC"),
    P("pd_term_pc", "Pd.TerminationA", "Partial discharge, sealing end A", "pC", [0, 5000], 1.5, "IEC 61850: SPDC"),
    P("term_a_temp_c", "Termination.TempA", "Sealing end A connector temperature (IR)", "degC", [-20, 200], 0.2),
]

failure_modes = {
    "soil_drying": {"label": "Soil drying at the road crossing", "cause": "Heat from the cables dries the backfill around the ducts under the road: its thermal resistivity climbs from 1.2 towards 2.5 K.m/W, the crossing runs hotter for the same load and can run away thermally",
                    "detect": ["dts_seg07_c", "crossing_residual_k", "conductor_temp_c", "rating_utilisation"], "action": "Derate the circuit now; re-bed the crossing in a stabilised, low-resistivity backfill (or add a water/cooling measure)", "default_ramp_min": 3},
    "joint_pd": {"label": "Partial discharge in joint J4", "cause": "A void or a contaminated interface in the pre-moulded joint discharges every cycle; the HFCT on the earth lead sees it long before the joint fails",
                 "detect": ["pd_joint_pc"], "action": "Confirm with a UHF / acoustic PD survey; plan a joint replacement in the next outage", "default_ramp_min": 2},
    "cross_bonding_fault": {"label": "Cross-bonding fault (link box J2)", "cause": "Water in link box J2 shorts the cross-bonding: the screens act as if solidly bonded, circulating currents flow and heat the whole major section",
                            "detect": ["sheath_current_a", "sheath_ratio", "sheath_voltage_v", "conductor_temp_c"], "action": "Open and dry link box J2, replace the sheath voltage limiters, seal the box; verify the bonding with a sheath current test", "default_ramp_min": 2},
    "termination_overheating": {"label": "Sealing end A connector overheating", "cause": "A loose or corroded compression connector at the outdoor sealing end: contact resistance grows and the lug runs hot",
                                "detect": ["term_a_temp_c", "term_residual_k"], "action": "Thermographic check, then re-make the connector in the next outage", "default_ramp_min": 3},
    "overload": {"label": "Sustained overload", "cause": "Load transferred from a parallel circuit stays above the circuit's dynamic rating: the conductor heads for 90 C at the crossing",
                 "detect": ["load_eq_a", "rating_utilisation", "conductor_temp_c"], "action": "Re-dispatch or shed load; use the dynamic rating, not the static one, to decide how long it can last", "default_ramp_min": 3},
    "jacket_damage": {"label": "Outer jacket damage", "cause": "Third-party digging scraped the jacket: water reaches the screen and leakage current through the sheath voltage limiters rises; corrosion follows",
                      "detect": ["sheath_leakage_ma"], "action": "Locate the fault with a sheath fault locator, repair the jacket before the screen corrodes", "default_ramp_min": 2},
    "dts_fibre_break": {"label": "DTS fibre break", "cause": "The DTS fibre is cut or a splice fails: the interrogator only sees the fibre up to the break; the route beyond is blind. This is a sensor fault, not a cable fault",
                        "detect": ["dts_fibre_km", "dts_seg07_c"], "action": "OTDR the fibre, repair the splice; meanwhile rate the circuit from the load model only", "default_ramp_min": 1},
}

THERMAL = {
    "r20_ohm_m": R20, "alpha20": ALPHA_AL, "r90_dc_ohm_m": round(r90, 10), "ys": round(ys, 5), "yp": round(yp, 5),
    "r90_ac_ohm_m": round(r_ac90, 10), "wd_w_m": round(WD, 4), "tan_delta": TAND, "c_f_m": C,
    "T1": round(T1, 5), "T3": round(T3, 5), "T4_normal": round(T4N, 4), "T4_crossing": round(T4X, 4),
    "T4_crossing_parts": {"cable_to_duct": round(T4P, 4), "duct_wall": round(T4PP, 4), "external": round(T4PPP, 4)},
    "lambda1_cross_bonded": LAM_XB, "lambda1_solid": round(lam_solid, 4), "rho_soil": RHO_SOIL, "soil_ambient_c": SOIL_AMB,
    "depth_m": DEPTH, "depth_crossing_m": DEPTH_X, "theta_max_c": THETA_MAX,
    "rating_normal_a": round(I_N, 1), "rating_crossing_a": round(I_X, 1), "rating_crossing_solid_bonded_a": round(I_X_SOLID, 1),
    "tau_cable_min": 30.0, "tau_soil_min": 600.0,
    "basis": "IEC 60287-1-1 / 60287-2-1 steady state from the Prysmian construction; IEC 60853-style two time constants "
             "(cable 30 min, soil 10 h) for the transient (assumed values, demo-compressed)",
}

twin = {
    "$comment": "Single source of truth for the UGC-801 digital twin: 3.6 km 132 kV XLPE underground circuit, three Prysmian "
                "1200 mm2 Al single cores in trefoil, cross-bonded, with DTS fibre. Construction from the Prysmian data sheet; "
                "ratings computed with IEC 60287 (not published by Prysmian).",
    "twin": {"id": "urn:maximo:twin:hvcable:UGC-801", "version": "1.0.0",
             "kind": "132 kV XLPE underground cable circuit with DTS, PD and bonding monitoring",
             "standards": {
                 "construction": "Prysmian R89BD901200MIJNE 132 kV XLP 1200 mm2 Al LS0H, IEC 60840",
                 "rating": "IEC 60287-1-1 (losses, sheath loss factor) and IEC 60287-2-1 (thermal resistances), steady state",
                 "transient": "IEC 60853 idea: cable and soil time constants; real-time thermal rating (RTTR) from DTS + load",
                 "information_model": "Points named after IEC 61850 logical nodes (MMXU, ZCAB, STMP, SPDC, MMET)"}},
    "identification": {"assetnum": "UGC-801", "description": "132 kV underground cable circuit 801 (substation A to substation B)",
                       "manufacturer": "Prysmian", "model": "132 kV XLPE 1x1200 mm2 Al LS0H (R89BD901200MIJNE)",
                       "site": "Demo transmission network", "location": "Substation A - substation B, 3.6 km route",
                       "medium": "Direct buried trefoil, road crossing in ducts, cross-bonded"},
    "design": {
        "cable": {"conductor": "Al compact class 2, 1200 mm2", "conductor_d_mm": DC, "insulation_mm": 16.0, "insulation_screen_d_mm": D_INS_SCR,
                  "screen": "50 x 2.052 mm Cu wires (165 mm2) + Al tape", "screen_mean_d_mm": round(ds, 2), "outer_d_mm": DE,
                  "r20_ohm_km": 0.0247, "capacitance_uf_km": 0.2402, "um_kv": 145, "up_kv": 650, "theta_max_c": 90, "theta_sc_c": 250,
                  "sc_conductor_ka_05s": 160, "sc_screen_ka_05s": 31.5, "mass_kg_km": 11408, "bending_radius_m": [2.46, 1.97]},
        "circuit": {"u_kv": 132, "length_km": LENGTH_KM, "formation": "trefoil touching", "bonding": "cross-bonded, 2 major sections",
                    "joints": JOINTS, "link_boxes": {"J1": "cross-bond", "J2": "cross-bond", "J3": "earth", "J4": "cross-bond", "J5": "cross-bond"},
                    "crossing_km": [CROSS_SEG * SEG_KM, (CROSS_SEG + 1) * SEG_KM], "segments": NSEG, "segment_km": SEG_KM,
                    "crossing_segment": CROSS_SEG + 1,
                    "assumed": "route, depth, soil, bonding layout and sensor positions are assumptions of the demo circuit"},
        "thermal": THERMAL,
        "terminations": {"type": "outdoor sealing ends (porcelain/composite)", "connector_rise_k_at_1000a": 12.0,
                         "note": "connector temperature rise over air ~ k I^2 (assumed for the IR check)"},
        "sheath": {"expected_ratio": 0.03, "note": "cross-bonded: sheath current a few % of the load; solid bonding (fault) gives tens of %"},
        "demo": {"time_scale": 60, "note": "The plant clock runs 60x real time (one day in 24 min): the 10-h soil time constant plays "
                                           "out in 10 minutes and the 30-min cable time constant in 30 s; injected faults ramp in 1-3 min."},
    },
    "telemetry": {"event": "cable", "publish_every_s": 5, "device_type": "HV_CABLE_XLPE",
                  "groups": {"Load": "Load (CTs and VTs)", "Rttr": "Real-time thermal rating unit", "Soil": "Reference soil sensor",
                             "Weather": "Weather station", "Dts": "Distributed temperature sensing (fibre in the screen)",
                             "Bonding": "Link boxes and sheath", "Pd": "Partial discharge (HFCT)", "Termination": "Outdoor sealing ends"},
                  "points": points},
    "twin_model": {"limits": {"conductor_alert_c": 85.0, "conductor_max_c": 90.0, "crossing_residual_alert_k": 6.0, "steady_load_min_a": 150,
                              "utilisation_alert": 1.0, "utilisation_warn": 0.9, "sheath_ratio_alert": 0.12, "sheath_voltage_alert_v": 120,
                              "leakage_alert_ma": 1.0, "pd_alert_pc": 100, "pd_high_pc": 500, "term_residual_alert_k": 15.0,
                              "fibre_shortfall_km": 0.05}},
    "failure_modes": failure_modes,
    "presentation": {
        "category": "Underground cable",
        "kpis": [{"metric": "current_l2_a", "label": "Load", "unit": "A", "decimals": 0},
                 {"metric": "dts_max_c", "label": "DTS max", "unit": "°C", "decimals": 1},
                 {"metric": "dts_seg07_c", "label": "Road crossing", "unit": "°C", "decimals": 1},
                 {"metric": "pd_joint_pc", "label": "PD joint J4", "unit": "pC", "decimals": 0}],
        "twin_kpis": [{"metric": "conductor_temp_c", "label": "Conductor (est.)", "unit": "°C", "decimals": 1},
                      {"metric": "rating_utilisation", "label": "Rating used", "unit": "x", "decimals": 2}],
        "compare": [
            {"label": "Road crossing screen temperature", "measured": "dts_seg07_c", "expected": "crossing_expected_c", "unit": "°C", "decimals": 1,
             "basis": "IEC 60287 at the equivalent current and soil ambient (T4 crossing, rho 1.2 K.m/W)"},
            {"label": "Conductor temperature (hot spot)", "measured": "conductor_temp_c", "expected": None, "unit": "°C", "decimals": 1,
             "basis": "DTS screen temperature + Wc T1 + Wd T1/2 (RTTR)"},
            {"label": "Dynamic rating (crossing)", "measured": "load_eq_a", "expected": "rating_a", "unit": "A", "decimals": 0,
             "basis": "IEC 60287 at the live soil ambient, cross-bonded"},
            {"label": "Sheath current", "measured": "sheath_current_a", "expected": "sheath_expected_a", "unit": "A", "decimals": 1,
             "basis": "cross-bonded: about 3 % of the load"},
            {"label": "Sealing end A", "measured": "term_a_temp_c", "expected": "term_expected_c", "unit": "°C", "decimals": 1,
             "basis": "air + 12 K at 1000 A, ~ I² (assumed)"},
            {"label": "Joint losses", "measured": "losses_kw_km", "expected": None, "unit": "kW/km", "decimals": 1, "basis": "3 (I²R(1+λ1) + Wd)"},
        ],
        "trends": [{"metric": "crossing_residual_k", "label": "Crossing vs. IEC (K)"}, {"metric": "conductor_temp_c", "label": "Conductor (°C)"},
                   {"metric": "rating_utilisation", "label": "Rating used"}, {"metric": "sheath_ratio", "label": "Sheath / load"}],
        "design": [
            {"label": "Cable", "value": "Prysmian 132 kV XLPE 1x1200 mm² Al, 16 mm XLPE, Cu wire screen 165 mm², LS0H, Ø 98.4 mm"},
            {"label": "Circuit", "value": "3.6 km, trefoil at 1.2 m, road crossing in ducts at 1.8 m, cross-bonded (joints every 600 m)"},
            {"label": "Ratings (IEC 60287)", "value": f"{I_N:.0f} A buried, {I_X:.0f} A at the crossing (soil 25 °C, 1.2 K.m/W); solid-bonded {I_X_SOLID:.0f} A"},
            {"label": "Source", "value": "Prysmian data sheet R89BD901200MIJNE; ratings computed (IEC 60287); 3D built procedurally, not manufacturer CAD"},
        ],
    },
}

if __name__ == "__main__":
    out = HERE / "twin" / "ugc-801.twin.json"
    out.parent.mkdir(exist_ok=True)
    json.dump(twin, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("written", out)
    for k in ("r90_ac_ohm_m", "ys", "yp", "wd_w_m", "T1", "T3", "T4_normal", "T4_crossing", "lambda1_solid",
              "rating_normal_a", "rating_crossing_a", "rating_crossing_solid_bonded_a"):
        print(f"  {k} = {THERMAL[k]}")
