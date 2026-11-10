"""Build twin/ohl-901.twin.json: 132 kV overhead line span, ACSR "Drake" 795 kcmil 26/7 (ASTM B232), line sensor + weather station.

Sources (public, read 2026-11-10):
  Southwire ACSR (ASTM B232) "Weights, Measurements, Electrical and Engineering Data", SPEC 80100:
    https://cabletechsupport.southwire.com/tile/26/spec/80100/?country=CA
    Drake 795.0 kcmil 26/7: Al area 0.6247 in2, total 0.7264 in2, Al strand 0.1749 in, steel strand 0.1360 in,
    core 0.4080 in, OD 1.108 in, weight Al 749.2 / total 1094 lb/1000 ft, rated breaking strength 31,500 lb (std),
    DC resistance at 20 C 0.1129 ohm/mile
  Southwire product page 795-26/7 ACSR/GA2 DRAKE: OD 28.13 mm, 1627 kg/km, continuous operating temperature 75 C,
    emergency 100 C: https://www.southwire.com/wire-cable/bare-aluminum-overhead-transmission-distribution/acsr/p/10154308
  Southwire ACSR catalogue row for Drake (as quoted by the catalogue copy on Scribd, https://www.scribd.com/doc/311240211/ACSR-pdf):
    AC resistance at 75 C 0.0263 ohm/1000 ft, ampacity 907 A (75 C conductor, 25 C ambient, 2 ft/s wind, sun)  [UNVERIFIED:
    read from a search excerpt of the catalogue, not the PDF itself]
  IEEE Std 738 (calculating the current-temperature relationship of bare overhead conductors): heat-balance equations
  Thermal expansion and final modulus of 26/7 ACSR: typical values 18.9e-6 /K and 76 GPa [UNVERIFIED for this catalogue;
    the WBSEDCL ACSR specification lists 17.8e-6 /K and 80 GPa for 30/7 and 19.8e-6 /K and 75 GPa for 6/7,
    https://www.wbsedcl.in/irj/go/km/docs/internet/webpage/techspec/SPEC_ACSR_CONDDUCTOR.pdf]
  Line monitor modelled on the Lindsey TLM (conductor temperature, current, LiDAR clearance, inclination):
    https://lindsey-usa.com/sensors/transmission-line-monitor/
Assumptions (labelled in the twin file): 132 kV single circuit, 350 m level ruling span, everyday tension 20 % RBS at
  20 C, attachment height 19.5 m, 7.0 m minimum ground clearance, 3.0 m vegetation clearance, emissivity / absorptivity
  0.8 / 0.8 (aged conductor), AC resistance at 25 C derived from the DC value, alarm limits for joints, leakage current
  and vibration (typical public values, not a utility standard).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import twin_calc as tc  # noqa: E402

IN, LB, FT, MILE = 0.0254, 0.45359237, 0.3048, 1609.344
D = 1.108 * IN
A_AL, A_TOT = 0.6247 * IN * IN, 0.7264 * IN * IN
M_AL, M_TOT = 749.2 * LB / (1000 * FT), 1094 * LB / (1000 * FT)
M_ST = M_TOT - M_AL
RBS = 31500 * LB * 9.80665
R20_DC = 0.1129 / MILE
R75_AC = 0.0263 / (1000 * FT)
ALPHA_AL = 0.00403                                       # 1350-H19 aluminium, 61.2 % IACS
AC_DC = R75_AC / (R20_DC * (1 + ALPHA_AL * 55))         # AC/DC ratio implied at 75 C, applied at 25 C as well
R25_AC = R20_DC * (1 + ALPHA_AL * 5) * AC_DC
MCP = M_AL * 955 + M_ST * 476                          # J/(m K): aluminium 955, steel 476 J/(kg K)

conductor = {"code_word": "Drake", "standard": "ASTM B232 ACSR", "size_kcmil": 795.0, "stranding": "26/7 (Al/steel)",
             "diameter_m": round(D, 5), "area_al_m2": round(A_AL, 8), "area_total_m2": round(A_TOT, 8),
             "mass_kg_m": round(M_TOT, 4), "mass_al_kg_m": round(M_AL, 4), "mass_steel_kg_m": round(M_ST, 4),
             "rated_breaking_strength_n": round(RBS), "r_dc_20c_ohm_m": round(R20_DC, 9),
             "r_ac_25c_ohm_m": round(R25_AC, 9), "r_ac_75c_ohm_m": round(R75_AC, 9), "ac_dc_ratio": round(AC_DC, 4),
             "r_note": "AC 75 C from the Southwire catalogue (0.0263 ohm/kft, 60 Hz); AC 25 C derived = DC 20 C x (1 + 0.00403 x 5) x the same AC/DC ratio",
             "final_modulus_pa": 76e9, "expansion_per_k": 18.9e-6, "mech_note": "typical 26/7 ACSR values, not from the Southwire table (UNVERIFIED)",
             "emissivity": 0.8, "absorptivity": 0.8, "surface_note": "aged conductor (assumption; Southwire rates with emissivity 0.5)",
             "heat_capacity_j_mk": round(MCP, 1), "max_operating_c": 75, "emergency_c": 100,
             "strands": {"al_dia_m": round(0.1749 * IN, 5), "steel_dia_m": round(0.1360 * IN, 5), "core_dia_m": round(0.4080 * IN, 5),
                         "al_layers": [10, 16], "steel": 7}}
line = {"voltage_kv": 132, "circuits": 1, "phases": 3, "ruling_span_m": 350.0, "everyday_temp_c": 20.0,
        "everyday_tension_n": round(0.20 * RBS), "everyday_tension_pct_rbs": 20, "attachment_height_m": 19.5,
        "phase_spacing_m": 5.0, "azimuth_deg": 75.0, "elevation_m": 120.0, "frequency_hz": 50,
        "assumed": "132 kV single circuit, 350 m level ruling span, everyday tension 20 % RBS at 20 C, lower phase attachment 19.5 m, azimuth 75 deg"}

# ---------------------------------------------------------------- sag-tension fit (clean conductor)
temps = np.linspace(-10, 130, 57)
st = tc.state_change(conductor, line, temps)
sags = np.array([s for _, s in st])
c_sag = np.polynomial.polynomial.polyfit(temps, sags, 3)
c_inv = np.polynomial.polynomial.polyfit(sags, temps, 3)
fit_err = float(np.max(np.abs(np.polynomial.polynomial.polyval(temps, c_sag) - sags)))
inv_err = float(np.max(np.abs(np.polynomial.polynomial.polyval(sags, c_inv) - temps)))

# ---------------------------------------------------------------- ratings (IEEE 738, this implementation)
K = {"D": D, "eps": 0.8, "abs": 0.8, "He": line["elevation_m"], "r25": R25_AC, "mR": (R75_AC - R25_AC) / 50}
STATIC = dict(ta=40.0, v=0.61, phi=math.pi / 2, g=1000.0)
static_a = tc.ampacity(K, 75, STATIC["ta"], STATIC["v"], STATIC["phi"], STATIC["g"])
K_sw = dict(K, eps=0.5, abs=0.5)
check_sw = tc.ampacity(K_sw, 75, 25, 0.61, math.pi / 2, 1000.0)


def P(metric, path, label, unit, rng, noise, opc=None):
    return {"metric": metric, "path": path, "label": label, "unit": unit, "range": rng, "noise": noise, "opc": opc}


points = [
    P("line_current_a", "Line.Current", "Line current (line monitor, phase L1)", "A", [0, 2500], 1.5, "IEC 61850: MMXU.A.phsA"),
    P("line_voltage_kv", "Line.Voltage", "Line voltage (substation)", "kV", [0, 170], 0.08, "IEC 61850: MMXU.PPV"),
    P("active_power_mw", "Line.ActivePower", "Active power flow (substation)", "MW", [-400, 400], 0.2, "IEC 61850: MMXU.TotW"),
    P("conductor_temp_c", "Conductor.Temperature", "Conductor temperature (line monitor)", "degC", [-30, 250], 0.2, "IEC 61850: STMP.Tmp"),
    P("joint_temp_c", "Conductor.JointTemperature", "Mid-span compression joint temperature (second line monitor)", "degC", [-30, 300], 0.25, "IEC 61850: STMP.Tmp (joint)"),
    P("clearance_m", "Span.GroundClearance", "Ground clearance at mid-span (LiDAR)", "m", [0, 40], 0.02, "IEC 61850: GGIO.AnIn (clearance)"),
    P("vegetation_distance_m", "Span.VegetationDistance", "Distance to the nearest vegetation below the span (LiDAR)", "m", [0, 30], 0.03),
    P("ambient_temp_c", "Weather.AmbientTemperature", "Ambient temperature (weather station)", "degC", [-40, 60], 0.1, "IEC 61850: MMET.EnvTmp"),
    P("wind_speed_ms", "Weather.WindSpeed", "Wind speed (weather station, conductor height)", "m/s", [0, 40], 0.08, "IEC 61850: MMET.HorWdSpd"),
    P("wind_dir_deg", "Weather.WindDirection", "Wind direction (from north)", "deg", [0, 360], 1.5, "IEC 61850: MMET.HorWdDir"),
    P("solar_wm2", "Weather.SolarIrradiance", "Global solar irradiance (pyranometer)", "W/m2", [0, 1400], 4.0, "IEC 61850: MMET.HorInsol"),
    P("humidity_pct", "Weather.Humidity", "Relative humidity", "%", [0, 100], 0.4, "IEC 61850: MMET.EnvHum"),
    P("leakage_current_ma", "Insulator.LeakageCurrent", "Insulator string leakage current (peak, tower 2 L1)", "mA", [0, 200], 0.05),
    P("vibration_um", "Conductor.AeolianVibration", "Aeolian vibration, bending amplitude p-p at 89 mm from the clamp", "um", [0, 1000], 1.0),
]

failure_modes = {
    "joint_hotspot": {"label": "Mid-span joint degradation", "cause": "A compression joint loses contact (corrosion, poor crimp): its resistance rises, so it runs hotter than the conductor next to it, more so at high current, until it fails",
                      "detect": ["joint_delta_k", "joint_temp_c"], "action": "Thermographic check from the ground or air; replace the joint (or add a shunt sleeve) at the next outage", "default_ramp_min": 3},
    "conductor_creep": {"label": "Excess sag (conductor creep)", "cause": "The aluminium has crept or the conductor was overstretched in a past overload: the span sags more than its temperature explains",
                        "detect": ["clearance_residual_m", "tc_sag_diff_k", "clearance_m"], "action": "Survey the span; re-sag (re-tension) the conductor and check the clearance at the maximum operating temperature", "default_ramp_min": 3},
    "vegetation_encroachment": {"label": "Vegetation encroachment", "cause": "Trees below the span grow into the clearance zone; on a hot afternoon the sagging conductor gets closer still",
                                "detect": ["vegetation_distance_m"], "action": "Raise a vegetation work order: trim or remove the trees below the span", "default_ramp_min": 3},
    "insulator_pollution": {"label": "Insulator pollution", "cause": "Dust, salt or industrial deposits on the insulator string become conductive when wet: leakage current rises, most at dawn when the humidity is high",
                            "detect": ["leakage_current_ma", "humidity_pct"], "action": "Wash the insulators (live washing) or replace them with silicone / RTV-coated units", "default_ramp_min": 3},
    "overload_beyond_dlr": {"label": "Overload beyond the dynamic rating", "cause": "The current exceeds what today's weather can cool: the conductor heats past its maximum operating temperature, sags towards the ground and anneals the aluminium",
                            "detect": ["load_pct_dlr", "conductor_temp_c", "clearance_m"], "action": "Re-dispatch or switch to cut the flow below the dynamic rating; inspect for annealing after a long excursion", "default_ramp_min": 2},
    "damper_loss": {"label": "Vibration damper lost", "cause": "A Stockbridge damper has slipped or lost a weight: aeolian vibration in steady low winds grows and fatigues the strands at the clamp",
                    "detect": ["vibration_um", "wind_speed_ms"], "action": "Replace or reposition the damper; inspect the strands at the suspension clamp", "default_ramp_min": 3},
    "sensor_fault": {"label": "Conductor temperature sensor fault", "cause": "The line monitor's temperature probe has lost contact: it reads low, while the heat balance and the measured sag both say the conductor is hotter",
                     "detect": ["tc_residual_k", "tc_sag_diff_k"], "action": "Do not trust the sensor for ratings: fall back to the heat-balance temperature, then service the line monitor", "default_ramp_min": 2},
}

twin = {
    "$comment": "Single source of truth for the OHL-901 digital twin: one 132 kV overhead line span with ACSR Drake 795 kcmil 26/7 conductor, "
                "a line monitor on the lower phase and a weather station. Conductor data from Southwire (ASTM B232); heat balance IEEE 738.",
    "twin": {"id": "urn:maximo:twin:overheadline:OHL-901", "version": "1.0.0",
             "kind": "Overhead line span with line monitor (conductor temperature, current, LiDAR clearance) and weather station",
             "standards": {
                 "conductor": "Southwire ACSR (ASTM B232) Drake 795 kcmil 26/7: OD 28.14 mm, 1.628 kg/m, RBS 140.1 kN, R_dc20 0.0702 ohm/km, R_ac75 0.0863 ohm/km",
                 "thermal": "IEEE Std 738 heat balance (Joule, solar, convective, radiative), steady state and transient; dynamic line rating at 75 C",
                 "sag": "Ruling-span change of state, parabolic approximation, elastic + thermal strain (no creep model); fitted as a cubic of conductor temperature",
                 "information_model": "Points named after IEC 61850 logical nodes (MMXU, STMP, MMET, GGIO)"}},
    "identification": {"assetnum": "OHL-901", "description": "132 kV overhead line 901, span 14-15 (lower phase L1)",
                       "manufacturer": "Southwire (conductor)", "model": "ACSR Drake 795 kcmil 26/7",
                       "site": "Demo transmission network", "location": "Line 901 / towers 14-15",
                       "medium": "Bare ACSR conductor, 350 m span, lattice towers"},
    "design": {
        "conductor": conductor,
        "line": line,
        "ratings": {"static_a": round(static_a, 1), "static_basis": "IEEE 738 at 75 C, 40 C ambient, 0.61 m/s wind at 90 deg, 1000 W/m2 (conservative seasonal assumptions)",
                    "check_southwire_a": round(check_sw, 1), "check_note": "this implementation with emissivity/absorptivity 0.5, 25 C, 0.61 m/s, 1000 W/m2 at 75 C; Southwire lists 907 A (their sun model may differ)"},
        "sag_fit": {"sag_from_tc": [round(float(x), 9) for x in c_sag], "tc_from_sag": [round(float(x), 7) for x in c_inv],
                    "range_c": [-10, 130], "max_error_m": round(fit_err, 4), "max_error_inv_c": round(inv_err, 3),
                    "table": [{"tc": float(t), "tension_kn": round(h / 1000, 2), "sag_m": round(s, 3)} for t, (h, s) in zip(temps[::4], st[::4])]},
        "clearances": {"ground_min_m": 7.0, "vegetation_min_m": 3.0, "note": "assumed minimum clearances for 132 kV (utility practice varies)"},
        "weather_model": {"solar": "global irradiance x absorptivity x D (simplified vs. IEEE 738 solar position model)"},
        "monitor": {"line_monitor": "Clamp-on line monitor modelled on the Lindsey TLM: conductor temperature, current, LiDAR clearance; second unit at the mid-span joint",
                    "weather": "Weather station on tower 15 at conductor height", "insulator": "Leakage-current sensor on the tower 15 L1 insulator string",
                    "vibration": "Aeolian vibration recorder at the tower 14 suspension clamp (bending amplitude, IEEE 1368 method)"},
        "demo": {"time_scale": 30, "note": "The plant clock runs 30x real time (one day in 48 min): the conductor's ~20 min thermal time constant plays out in about 40 s, "
                                           "so weather and load changes are visible during a demo."},
    },
    "telemetry": {"event": "line", "publish_every_s": 5, "device_type": "OVERHEAD_LINE",
                  "groups": {"Line": "Electrical (substation and line monitor)", "Conductor": "Line monitors on the conductor",
                             "Span": "LiDAR clearances at mid-span", "Weather": "Weather station", "Insulator": "Insulator string"},
                  "points": points},
    "twin_model": {"limits": {"tc_max_c": 75, "tc_emergency_c": 100, "tc_residual_alert_k": 10.0, "tc_sag_diff_alert_k": 12.0, "sensor_sag_agree_k": 6.0,
                              "clearance_residual_alert_m": 0.6, "ground_clearance_min_m": 7.0, "vegetation_min_m": 3.0,
                              "joint_delta_alert_k": 10.0, "joint_delta_critical_k": 25.0, "leakage_alert_ma": 5.0, "leakage_high_ma": 15.0,
                              "vibration_alert_um": 150.0,
                              "basis": "joint delta-T after NETA MTS infrared guidance (typical, unverified); leakage-current and vibration (IEEE 1368 safe bending amplitude for ACSR) limits are typical public values, assumed"}},
    "failure_modes": failure_modes,
    "presentation": {
        "category": "Overhead line",
        "kpis": [{"metric": "line_current_a", "label": "Current", "unit": "A", "decimals": 0},
                 {"metric": "conductor_temp_c", "label": "Conductor", "unit": "°C", "decimals": 1},
                 {"metric": "clearance_m", "label": "Clearance", "unit": "m", "decimals": 2},
                 {"metric": "wind_speed_ms", "label": "Wind", "unit": "m/s", "decimals": 1}],
        "twin_kpis": [{"metric": "dlr_a", "label": "Dynamic rating", "unit": "A", "decimals": 0},
                      {"metric": "load_pct_dlr", "label": "Load of DLR", "unit": "%", "decimals": 0}],
        "compare": [
            {"label": "Conductor temperature", "measured": "conductor_temp_c", "expected": "tc_expected_c", "unit": "°C", "decimals": 1,
             "basis": "IEEE 738 steady heat balance at the live current and weather"},
            {"label": "Dynamic line rating", "measured": "line_current_a", "expected": "dlr_a", "unit": "A", "decimals": 0,
             "basis": f"IEEE 738 at 75 °C with the live weather (static rating {static_a:.0f} A)"},
            {"label": "Ground clearance", "measured": "clearance_m", "expected": "clearance_expected_m", "unit": "m", "decimals": 2,
             "basis": "19.5 m attachment − sag at the measured conductor temperature (change of state)"},
            {"label": "Temperature from sag", "measured": "conductor_temp_c", "expected": "tc_from_sag_c", "unit": "°C", "decimals": 1,
             "basis": "conductor temperature that explains the measured sag"},
            {"label": "Joint vs. conductor", "measured": "joint_delta_k", "expected": None, "unit": "K", "decimals": 1, "basis": "alert > 10 K, failing > 25 K"},
            {"label": "Joule / solar heating", "measured": "joule_w_m", "expected": "solar_w_m", "unit": "W/m", "decimals": 1, "basis": "I²R(Tc) / absorptivity × irradiance × D"},
            {"label": "Emergency rating (100 °C)", "measured": "line_current_a", "expected": "dlr_emergency_a", "unit": "A", "decimals": 0, "basis": "IEEE 738 at 100 °C"},
        ],
        "trends": [{"metric": "dlr_a", "label": "Dynamic rating (A)"}, {"metric": "tc_residual_k", "label": "Conductor vs. IEEE 738 (K)"},
                   {"metric": "clearance_residual_m", "label": "Clearance vs. expected (m)"}, {"metric": "joint_delta_k", "label": "Joint ΔT (K)"}],
        "design": [
            {"label": "Conductor", "value": "ACSR Drake 795 kcmil 26/7 (ASTM B232): OD 28.14 mm, 1.628 kg/m, RBS 140 kN, Rac75 0.0863 Ω/km"},
            {"label": "Span", "value": "132 kV single circuit, 350 m ruling span, 20 % RBS at 20 °C, attachment 19.5 m (assumed)"},
            {"label": "Ratings", "value": f"75 °C continuous / 100 °C emergency (Southwire); static {static_a:.0f} A at 40 °C, 0.61 m/s, full sun"},
            {"label": "Source", "value": "Southwire ACSR data (SPEC 80100, Drake product page); IEEE 738; 3D built procedurally, not manufacturer CAD"},
        ],
    },
}

if __name__ == "__main__":
    out = HERE / "twin" / "ohl-901.twin.json"
    out.parent.mkdir(exist_ok=True)
    json.dump(twin, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("written", out)
    print(f"D {D*1000:.2f} mm  A {A_TOT*1e6:.1f} mm2  m {M_TOT:.3f} kg/m  RBS {RBS/1000:.1f} kN  R20dc {R20_DC*1e5:.3f}e-5  R25ac {R25_AC*1e5:.3f}e-5  R75ac {R75_AC*1e5:.3f}e-5  AC/DC {AC_DC:.4f}  mCp {MCP:.0f}")
    print(f"static rating {static_a:.0f} A; Southwire-condition check {check_sw:.0f} A (catalogue 907 A)")
    print(f"sag fit max error {fit_err*1000:.1f} mm, inverse {inv_err:.2f} K")
    for t, (h, s) in zip(temps[::4], st[::4]):
        print(f"  {t:6.1f} C  H {h/1000:6.2f} kN  sag {s:5.2f} m  clearance {line['attachment_height_m']-s:5.2f} m")
