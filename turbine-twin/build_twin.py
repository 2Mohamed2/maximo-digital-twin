"""Build twin/gt-501.twin.json: Siemens Energy SGT-400 (13 MW power generation) gas turbine generator set.

Sources (public):
  Siemens Energy SGT-400 product page  https://www.siemens-energy.com/global/en/home/products-services/product/sgt-400.html
      13 MW power generation: 12.9 MWe, 35.0 % efficiency, heat rate 10,294 kJ/kWh, pressure ratio 17.1, exhaust flow
      40.0 kg/s, exhaust temperature 555 C, power turbine 9,500 rpm; 11-stage transonic axial compressor, 2-stage compressor
      turbine, 2-stage free power turbine, 6 reverse-flow tubular can-annular DLE combustors; package 83,825 kg, 14.0 x 3.1 x 4.3 m
  Siemens Energy SGT-400 poster (PDF) gives 34.8 % / 10,354 kJ/kWh / PR 16.9 for the same rating: the product page values are used.
  Ambient correction cross-check: GPSA Engineering Data Book curves as quoted by rotating-machine.blogspot.com (2021):
      power x1.25 at -19 C, x0.83 at 40 C; heat rate x0.92 at -29 C, x1.10 at 45 C.
  Compressor fouling magnitude: Meher-Homji, Bromley, Stalder, "Gas Turbine Performance Deterioration and Compressor
      Washing", 2nd Middle East Turbomachinery Symposium 2013 (5 % flow + 2.5 pts efficiency = "normal" fouling).
  EGT spread: US patent 6,003,296 (~60 F normal, 150-160 F trip indication); ISO 10816-4 casing velocity zones 9.3 / 14.7 mm/s
      (as quoted in a vendor manual); inlet filter dp 1,500 Pa alarm / 2,000 Pa shutdown (an operator manual, control.com).
Assumptions (labelled in the file): natural gas LHV 50 MJ/kg, 6 exhaust thermocouples, gearbox to a 4-pole 50 Hz generator
  (1,500 rpm), gearbox x generator efficiency 0.96, compressor isentropic efficiency 0.86. The cycle constants are a
  calibrated stand-in (physics.calibrate), not Siemens data.
"""
import json
import math
from pathlib import Path

import numpy as np

import physics

HERE = Path(__file__).parent
ISO = dict(power_mw=12.9, heat_rate_kj_kwh=10294, efficiency_pct=35.0, pressure_ratio=17.1, exhaust_flow_kg_s=40.0,
           exhaust_temp_c=555.0, pt_speed_rpm=9500, lhv_mj_kg=50.0)
TERMS = [(i, j) for i in range(4) for j in range(3)]          # x^i * y^j, x = corrected load, y = T1 (C)


def P(metric, path, label, unit, rng, noise, opc=None):
    return {"metric": metric, "path": path, "label": label, "unit": unit, "range": rng, "noise": noise, "opc": opc}


points = [
    P("ambient_temp_c", "Inlet.AmbientTemperature", "Ambient temperature", "degC", [-40, 60], 0.05),
    P("ambient_pressure_kpa", "Inlet.AmbientPressure", "Ambient pressure", "kPa(a)", [80, 110], 0.01),
    P("inlet_temp_c", "Inlet.CompressorInletTemperature", "Compressor inlet temperature T1", "degC", [-40, 60], 0.05),
    P("inlet_pressure_kpa", "Inlet.CompressorInletPressure", "Compressor inlet pressure P1 (after the filter)", "kPa(a)", [80, 110], 0.01),
    P("inlet_filter_dp_pa", "Inlet.FilterDifferentialPressure", "Inlet filter differential pressure", "Pa", [0, 4000], 2.0),
    P("ngg_pct", "GasGenerator.Speed", "Gas generator speed NGG", "%", [0, 110], 0.02),
    P("npt_rpm", "PowerTurbine.Speed", "Power turbine speed NPT", "rpm", [0, 11000], 1.0),
    P("cdp_bar", "Compressor.DischargePressure", "Compressor discharge pressure CDP (P2)", "bar(a)", [0, 30], 0.005),
    P("cdt_c", "Compressor.DischargeTemperature", "Compressor discharge temperature CDT (T2)", "degC", [-40, 600], 0.2),
] + [P(f"egt_tc{i}_c", f"Exhaust.TC{i}", f"Exhaust thermocouple {i}", "degC", [-40, 800], 0.4) for i in range(1, 7)] + [
    P("fuel_flow_kg_s", "Fuel.MassFlow", "Fuel gas mass flow", "kg/s", [0, 2], 0.0008),
    P("fuel_gas_pressure_bar", "Fuel.SupplyPressure", "Fuel gas supply pressure", "bar(g)", [0, 40], 0.02),
    P("fuel_gas_temp_c", "Fuel.Temperature", "Fuel gas temperature", "degC", [-20, 80], 0.05),
    P("power_mw", "Generator.ActivePower", "Generator active power", "MW", [0, 20], 0.01),
    P("gg_vib_mm_s", "GasGenerator.CasingVibration", "Gas generator casing vibration (velocity)", "mm/s", [0, 50], 0.04),
    P("pt_prox_um", "PowerTurbine.ShaftVibration", "Power turbine bearing shaft vibration (proximity, pk-pk)", "um", [0, 250], 0.4),
    P("gen_vib_mm_s", "Generator.BearingVibration", "Generator bearing vibration (velocity)", "mm/s", [0, 50], 0.03),
    P("lube_oil_pressure_bar", "LubeOil.HeaderPressure", "Lube oil header pressure", "bar(g)", [0, 6], 0.005),
    P("lube_oil_temp_c", "LubeOil.HeaderTemperature", "Lube oil header temperature", "degC", [0, 120], 0.05),
    P("brg_gg_temp_c", "GasGenerator.BearingDrainTemperature", "Gas generator bearing drain temperature", "degC", [0, 160], 0.1),
    P("brg_pt_temp_c", "PowerTurbine.BearingDrainTemperature", "Power turbine bearing drain temperature", "degC", [0, 160], 0.1),
    P("brg_gen_temp_c", "Generator.BearingTemperature", "Generator bearing temperature", "degC", [0, 160], 0.1),
    P("running_hours", "Counters.RunningHours", "Fired hours", "h", [0, 1e6], 0),
    P("starts", "Counters.Starts", "Starts", "count", [0, 1e6], 0),
    P("washes", "Counters.OfflineWashes", "Off-line compressor washes", "count", [0, 1e5], 0),
    P("fault_code", "Control.TripCode", "Protection trip (0 none, 2 lube oil temperature, 3 PT shaft vibration)", "code", [0, 9], 0),
]

failure_modes = {
    "compressor_fouling": {"label": "Compressor fouling", "cause": "Airborne dust, salt and oil mist that pass the filter stick to the compressor blades: less air, lower compressor efficiency",
                           "detect": ["eta_c_dev_pts", "hr_dev_pct", "cdp_dev_pct", "egt_dev_k"],
                           "action": "On-line wash now; schedule an off-line (crank) wash, which restores virtually all of the lost power", "default_ramp_min": 30},
    "hot_section": {"label": "Hot-section degradation", "cause": "Erosion, coating loss or blocked cooling passages in the compressor turbine: lower turbine efficiency",
                    "detect": ["egt_dev_k", "hr_dev_pct", "ngg_expected_pct"], "action": "Borescope inspection of the combustor and compressor turbine; plan the hot-section overhaul", "default_ramp_min": 30},
    "burner_fault": {"label": "Burner / fuel nozzle fault (one can hot)", "cause": "A partly blocked or eroded fuel nozzle sends a hot streak downstream of one of the six combustor cans",
                     "detect": ["egt_spread_k", "tc_high_dev_k"], "action": "Check the burner of the hot sector (swirl-corrected); inspect the can and its transition duct", "default_ramp_min": 10},
    "thermocouple_fault": {"label": "Exhaust thermocouple fault", "cause": "One exhaust thermocouple (TC5) drifts low or goes open-circuit: the sensor, not the engine",
                           "detect": ["tc_low_dev_k", "egt_spread_k"], "action": "Replace the thermocouple; do not chase a combustion problem", "default_ramp_min": 5},
    "inlet_filter": {"label": "Inlet filter clogging", "cause": "Dust load on the filter elements raises the pressure drop; less air reaches the compressor",
                     "detect": ["inlet_filter_dp_pa"], "action": "Pulse-clean or replace the filter elements", "default_ramp_min": 20},
    "bearing_wear": {"label": "Power turbine bearing wear", "cause": "Worn tilting-pad bearing on the power turbine: shaft vibration and drain temperature rise",
                     "detect": ["pt_prox_um", "brg_pt_temp_c"], "action": "Plan a bearing inspection; trend the shaft orbit; check oil quality", "default_ramp_min": 20},
    "lube_cooler": {"label": "Lube oil cooler fouling", "cause": "Fouled oil cooler or a failed cooler fan: the lube oil header temperature rises and every bearing runs hotter",
                    "detect": ["lube_oil_temp_c", "brg_gg_temp_c"], "action": "Clean the lube oil cooler; check the cooler fans and the thermostatic valve", "default_ramp_min": 15},
}


def build():
    cyc = physics.calibrate(ISO)
    twin = {
        "$comment": "Single source of truth for the GT-501 digital twin: Siemens Energy SGT-400 13 MW gas turbine generator set. Data-sheet values from "
                    "Siemens Energy's public SGT-400 product page; the cycle constants are a calibrated thermodynamic stand-in, not Siemens data.",
        "twin": {"id": "urn:maximo:twin:gasturbine:GT-501", "version": "1.0.0",
                 "kind": "Two-shaft industrial gas turbine generator set",
                 "standards": {
                     "performance": "Siemens Energy SGT-400 13 MW power generation, ISO: 12.9 MWe, 35.0 %, heat rate 10,294 kJ/kWh, PR 17.1, "
                                    "exhaust 40.0 kg/s at 555 C, PT 9,500 rpm",
                     "corrected_parameters": "theta = T1/288.15 K, delta = P1/101.325 kPa; corrected speed N/sqrt(theta)",
                     "compressor_efficiency": "eta_c = T1 (PR^((gamma-1)/gamma) - 1) / (T2 - T1), gamma = 1.4",
                     "vibration": "Casing velocity zones 9.3 / 14.7 mm/s (ISO 10816-4 as quoted publicly); ISO 20816-4 values not verified",
                     "egt_spread": "Typical public values (US 6,003,296: ~60 F normal, 150-160 F trip): alarm 45 K, trip level 80 K. Not Siemens limits.",
                     "information_model": "Points named after a typical gas turbine control system tag list"}},
        "identification": {"assetnum": "GT-501", "description": "Gas turbine generator set 501",
                           "manufacturer": "Siemens Energy", "model": "SGT-400 13 MW",
                           "site": "Demo power plant", "location": "GT hall / unit 501",
                           "medium": "Natural gas, dry low emission"},
        "design": {
            "rating": {**ISO, "efficiency_pct": 35.0, "basis": "ISO 15 C, 101.325 kPa, 60 % RH, no inlet/exhaust losses",
                       "gg_speed_note": "gas generator speed shown in % (100 % = the ISO base-load speed of the stand-in; Siemens' rpm not published)"},
            "machine": {"compressor": "11-stage transonic axial", "compressor_turbine": "2-stage", "power_turbine": "2-stage, free",
                        "combustion": "6 reverse-flow tubular can-annular DLE combustors", "exhaust_tcs": 6,
                        "exhaust_tc_note": "6 exhaust thermocouples assumed (count not published)",
                        "package_m": [14.0, 3.1, 4.3], "package_mass_kg": 83825,
                        "gearbox": "PT 9,500 rpm -> 1,500 rpm 4-pole 50 Hz generator (assumed)", "fuel_lhv_mj_kg": 50.0,
                        "fuel_note": "natural gas LHV 50 MJ/kg assumed"},
            "cycle": {**cyc, "note": "calibrated stand-in: eta_c, gamma, combustor loss, eta_b and L fixed; cp_g, eta_t, T4, K1, K2, Wc0 "
                                     "fitted to the ISO data-sheet point (12.9 MW, 35.0 %, 555 C, 40 kg/s, PR 17.1). Not Siemens data."},
            "site": {"t_mean_c": 31.0, "t_swing_c": 7.0, "p0_kpa": 100.9, "demand_base_mw": 7.4, "demand_peak_mw": 3.2,
                     "note": "Gulf-coast site, 24-38 C day; plant load profile assumed"},
            "inlet": {"filter_dp_clean_pa": 450.0, "filter_note": "clean filter dp at ISO air flow, assumed"},
            "exhaust": {"dp_kpa": 1.5, "note": "exhaust/HRSG back-pressure, assumed"},
            "limits_control": {"ngg_max": 1.03, "t4_max_c": round(cyc["T4_iso"] - 273.15, 1), "ramp_mw_min": 1.3},
        },
        "telemetry": {"event": "turbine", "publish_every_s": 5, "device_type": "GAS_TURBINE",
                      "groups": {"Inlet": "Air inlet and filter", "GasGenerator": "Gas generator", "Compressor": "Compressor",
                                 "Exhaust": "Exhaust thermocouples", "Fuel": "Fuel gas", "PowerTurbine": "Power turbine",
                                 "Generator": "Generator", "LubeOil": "Lube oil system", "Counters": "Counters", "Control": "Control"},
                      "points": points},
        "twin_model": {"limits": {"min_load_frac": 0.3, "eta_c_dev_alert_pts": -1.0, "egt_dev_alert_k": 12.0, "hr_dev_alert_pct": 3.0,
                                  "egt_spread_alert_k": 45.0, "egt_spread_trip_k": 80.0, "tc_low_alert_k": 40.0, "tc_high_quiet_k": 25.0,
                                  "filter_dp_alert_pa": 1500.0, "filter_dp_high_pa": 2000.0, "gg_vib_alert_mm_s": 9.3, "gg_vib_high_mm_s": 14.7,
                                  "pt_prox_alert_um": 75.0, "pt_prox_trip_um": 125.0, "brg_temp_alert_c": 110.0,
                                  "lube_temp_alert_c": 65.0, "lube_temp_trip_c": 80.0},
                       "limits_basis": "Typical public values (see standards); set from site baselines in a real installation"},
        "failure_modes": failure_modes,
        "presentation": {
            "category": "Gas turbine",
            "kpis": [{"metric": "power_mw", "label": "Power", "unit": "MW", "decimals": 2},
                     {"metric": "inlet_temp_c", "label": "T1", "unit": "°C", "decimals": 1},
                     {"metric": "ngg_pct", "label": "NGG", "unit": "%", "decimals": 1},
                     {"metric": "cdp_bar", "label": "CDP", "unit": "bar(a)", "decimals": 2}],
            "twin_kpis": [{"metric": "hr_dev_pct", "label": "Heat rate vs. twin", "unit": "%", "decimals": 1},
                          {"metric": "egt_spread_k", "label": "EGT spread", "unit": "K", "decimals": 0}],
            "compare": [
                {"label": "Heat rate", "measured": "heat_rate_kj_kwh", "expected": "hr_expected_kj_kwh", "unit": "kJ/kWh", "decimals": 0,
                 "basis": "Calibrated cycle at this load and T1 (SGT-400 ISO 10,294 kJ/kWh)"},
                {"label": "Exhaust temperature (average)", "measured": "egt_avg_c", "expected": "egt_expected_c", "unit": "°C", "decimals": 1,
                 "basis": "Calibrated cycle (ISO 555 °C)"},
                {"label": "Compressor discharge pressure", "measured": "cdp_bar", "expected": "cdp_expected_bar", "unit": "bar(a)", "decimals": 2,
                 "basis": "Calibrated cycle x delta (ISO PR 17.1)"},
                {"label": "Compressor discharge temperature", "measured": "cdt_c", "expected": "cdt_expected_c", "unit": "°C", "decimals": 1, "basis": "Calibrated cycle"},
                {"label": "Gas generator speed", "measured": "ngg_pct", "expected": "ngg_expected_pct", "unit": "%", "decimals": 1, "basis": "Calibrated cycle"},
                {"label": "Compressor isentropic efficiency", "measured": "eta_c_pct", "expected": "eta_c_expected_pct", "unit": "%", "decimals": 1,
                 "basis": "From PR and T2/T1, gamma 1.4"},
                {"label": "EGT spread", "measured": "egt_spread_k", "expected": None, "unit": "K", "decimals": 0, "basis": "max - min of 6 TCs; alarm 45 K"},
            ],
            "trends": [{"metric": "hr_dev_pct", "label": "Heat rate deviation %"}, {"metric": "eta_c_dev_pts", "label": "Compressor efficiency pts"},
                       {"metric": "egt_dev_k", "label": "EGT deviation K"}, {"metric": "egt_spread_k", "label": "EGT spread K"}],
            "design": [
                {"label": "Gas turbine", "value": "Siemens Energy SGT-400, 13 MW power generation: 12.9 MWe, 35.0 %, 10,294 kJ/kWh, PR 17.1, 40.0 kg/s at 555 °C"},
                {"label": "Machine", "value": "11-stage compressor, 2-stage compressor turbine, 2-stage free power turbine at 9,500 rpm, 6 can-annular DLE combustors"},
                {"label": "Package", "value": "14.0 x 3.1 x 4.3 m, 83,825 kg; gearbox to a 4-pole 50 Hz generator (assumed)"},
                {"label": "Duty", "value": "Gulf-coast site, 24-38 °C day, plant load 7-11 MW"},
                {"label": "Source", "value": "Siemens Energy SGT-400 product page; cycle constants calibrated to it (not Siemens data); 3D visual built from the published package dimensions"},
            ],
        },
    }
    twin["expected_fit"] = fit(twin)
    return twin


def fit(twin):
    """2-D polynomials of the CLEAN plant at site conditions: x = P / (delta * 12.9 MW), y = T1 (C)."""
    pl = physics.Plant(twin)
    X, Y, out = [], [], {k: [] for k in ("fuel_rel", "cdp_rel", "cdt", "egt", "ngg")}
    p0 = twin["design"]["site"]["p0_kpa"]
    t4max = twin["design"]["cycle"]["T4_iso"]
    for T0 in np.arange(-5, 49, 2.0):
        for dT4 in np.arange(0, 560, 15.0):
            s = pl.steady(float(T0), p0, t4max - dT4, {}, 450.0)
            if s is None or s["n"] > twin["design"]["limits_control"]["ngg_max"] or s["power_w"] < 2.5e6:
                continue
            de = s["P1"] / physics.P_ISO
            x = s["power_w"] / 1e6 / (de * ISO["power_mw"])
            X.append(x)
            Y.append(float(T0))
            out["fuel_rel"].append(s["mf"] / de)
            out["cdp_rel"].append(s["PR"] * s["P1"] / 100.0 / de)
            out["cdt"].append(s["T2"] - 273.15)
            out["egt"].append(s["T5"] - 273.15)
            out["ngg"].append(s["n"] * 100)
    X, Y = np.array(X), np.array(Y)
    A = np.stack([X ** i * Y ** j for i, j in TERMS], axis=1)
    res = {"x": "POWER_MW / (delta * 12.9)", "y": "T1 degC", "terms": [list(t) for t in TERMS], "n_points": int(len(X)),
           "x_range": [round(float(X.min()), 3), round(float(X.max()), 3)], "y_range": [-5, 47]}
    for k, v in out.items():
        v = np.array(v)
        coef, *_ = np.linalg.lstsq(A, v, rcond=None)
        err = A @ coef - v
        res[k] = [float(f"{c:.10g}") for c in coef]
        res[k + "_max_err"] = round(float(np.abs(err).max()), 4)
    res["base_load_iso"] = base_load(twin)
    return res


def base_load(twin):
    """Available power and heat rate at base load vs T1, ISO pressure and no losses (ratio to ISO), for the GPSA check."""
    c = twin["design"]["cycle"]
    cy = physics.Cycle(c)
    nmax = twin["design"]["limits_control"]["ngg_max"]
    rows = []
    for T in range(-30, 51, 2):
        T1 = T + 273.15
        t4 = c["T4_iso"]
        s = cy.solve(T1, physics.P_ISO, physics.P_ISO, t4, {})
        if s["n"] > nmax:                      # cold day: gas generator speed limit, not the firing temperature
            lo, hi = t4 - 500, t4
            for _ in range(40):
                mid = (lo + hi) / 2
                sm = cy.solve(T1, physics.P_ISO, physics.P_ISO, mid, {})
                if sm["n"] > nmax:
                    hi = mid
                else:
                    lo = mid
            s = cy.solve(T1, physics.P_ISO, physics.P_ISO, lo, {})
        hr = s["mf"] * ISO["lhv_mj_kg"] * 1000 * 3600 / (s["power_w"] / 1000)
        rows.append([T, round(s["power_w"] / 1e6 / ISO["power_mw"], 4), round(hr / ISO["heat_rate_kj_kwh"], 4), round(s["n"] * 100, 2)])
    return rows


if __name__ == "__main__":
    tw = build()
    out = HERE / "twin" / "gt-501.twin.json"
    json.dump(tw, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    f = tw["expected_fit"]
    bl = {r[0]: r for r in f["base_load_iso"]}
    print("base load vs GPSA: -20 C", bl[-20][1:3], "(GPSA power x1.25 at -19)  40 C", bl[40][1:3], "(GPSA x0.83)  44 C", bl[44][1:3], "(GPSA HR x1.10 at 45)")
    print("written", out, "fit points", f["n_points"], {k: f[k] for k in f if k.endswith("_max_err")})
    c = tw["design"]["cycle"]
    print("calibration: eta_c", c["eta_c"], "eta_t", c["eta_t"], "cp_g", c["cp_g"], "L", c["L"], "T4", c["iso_check"]["T4_c"], "C")
