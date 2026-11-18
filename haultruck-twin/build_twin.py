"""Write twin/ht-4001.twin.json: the mining haul truck twin (HT-4001).

    python build_twin.py

HT-4001 is a Caterpillar 793F mechanical-drive mining truck (Cat C175-16 diesel engine, six-speed power shift transmission)
on an open-pit mine, fitted with 50/80 R57 tyres. Its onboard monitoring system (VIMS with the payload monitor) and the
tyre pressure monitoring system send their values through the mine's fleet management system.

Sources (every number below is either from these or labelled "assumption" in its source text):
  Cat 793F specification sheet AEHQ8089 (10-2017): engine C175-16, 1976 kW gross (SAE J1995) at 1750 rpm, bore 175 mm,
    stroke 220 mm, 85 L, torque rise 20 %; nominal payload 226.8 t; target gross machine weight 390 089 kg; operating chassis
    weight 124 586 kg (with 50/80 R57 tyres); body 26 862 to 47 627 kg; weight distribution empty 49/51 %, loaded 33/67 %;
    top speed 60 km/h; gear top speeds 12.9 / 17.4 / 23.8 / 32.1 / 43.6 / 60 km/h; total reduction 28.8:1; fuel tank 2839 L;
    rolling resistance rule 1 % grade per 10 kg/t; fuel API gravity 35, LHV 42 780 kJ/kg; engine life target (Tier 4 Final)
    3 785 411 L of fuel burned before replacement; 10/10/20 overload policy referenced for gross weight limits.
  Michelin Earthmover technical data 2022-23: 50/80 R 57 XDR250 B E4R: TKPH 1286, 24 km per hour max, load 67 000 kg at
    6.5 bar (transport); TKPH method: Qm = (Qc + Qv)/2, Vm = L/H, K1 cycle-length table, K2 = 1/(1 - a (TA - 38)/Vm) with
    a = 0.40 above 38 C and 0.25 below; reference ambient 38 C.
  Net power 1848 kW (SAE J1349) from Cat's 793F product page; accessory load taken as gross minus net.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with "
SPEC = "Cat 793F specification sheet AEHQ8089 (10-2017)"
MICH = "Michelin Earthmover technical data 2022-23, 50/80 R 57 XDR250 B E4R"

GEARS = [12.9, 17.4, 23.8, 32.1, 43.6, 60.0]

twin = {
    "$comment": "HT-4001 mining haul truck twin. Expected values in Maximo Monitor from the truck's specification sheet, the tyre maker's data and the haul road; the truck sends only what it measures.",
    "twin": {"id": "HT-4001", "name": "Mining haul truck HT-4001", "version": "1.0.0", "folder": "haultruck-twin"},
    "identification": {
        "asset": "HT-4001", "assetnum": "HT-4001", "manufacturer": "Caterpillar", "model": "793F mining truck",
        "description": "Rigid-frame mining haul truck, ore and waste haulage from the pit to the crusher and the dumps",
        "engine": "Cat C175-16 four-stroke diesel, 16 cylinders in two banks, 85 L",
        "drivetrain": "Torque converter and six-speed power shift transmission, differential 1.8:1, planetary final drives 16:1",
        "tyres": "Six Michelin 50/80 R 57 XDR250 B E4R (2 front, 4 rear in duals)",
        "onboard": "VIMS onboard monitoring with payload monitor; tyre pressure and temperature monitoring (TPMS)",
    },
    "design": {
        "engine": {
            "rated_gross_kw": 1976.0, "rated_net_kw": 1848.0, "rated_rpm": 1750, "torque_rise_pct": 20,
            "bore_mm": 175, "stroke_mm": 220, "displacement_l": 85, "cylinders": 16,
            "idle_rpm": 700, "idle_kw": 40.0,
            "source": SPEC + ": gross power SAE J1995 at 1750 rpm, bore, stroke, displacement, torque rise. Net power (SAE J1349): Cat 793F "
                      "product page. Idle speed and the 40 kW drawn at idle: " + A + "the engine's performance data (TMI)",
        },
        "fuel": {
            "density_kg_l": 0.849, "lhv_mj_kg": 42.78, "bsfc_marginal_g_kwh": 200.0, "zero_load_lph": 15.0,
            "life_target_l": 3785411.0, "tank_l": 2839,
            "source": SPEC + ": fuel of API gravity 35 at 16 C (density 141.5 / (131.5 + 35) = 0.849 kg/L) and LHV 42 780 kJ/kg; "
                      "Tier 4 Final engine life target 3 785 411 L (1 000 000 gal) burned before replacement; tank 2839 L. "
                      "Willans line fuel = zero-load fuel + marginal BSFC x engine power: " + A + "the engine's fuel map (TMI)",
        },
        "drivetrain": {
            "efficiency": 0.82, "accessory_kw": 128.0, "gear_top_kmh": GEARS, "total_reduction": 28.8,
            "source": SPEC + ": gear top speeds and total reduction 28.8:1. Accessory power = gross 1976 kW minus net 1848 kW (fan, "
                      "alternator, pumps). Engine-to-wheel efficiency 0.82 with the torque converter locked up: " + A + "Cat's rimpull data",
        },
        "truck": {
            "chassis_kg": 124586.0, "body_kg": 38703.0, "empty_kg": 163289.0, "target_payload_t": 226.8, "target_gmw_kg": 390089.0,
            "front_empty": 0.49, "rear_empty": 0.51, "front_loaded": 0.33, "rear_loaded": 0.67, "top_speed_kmh": 60.0,
            "source": SPEC + ": operating chassis weight 124 586 kg (100 % fuel, 50/80 R57 tyres), body weight range 26 862 to 47 627 kg, "
                      "nominal payload 226.8 t, target gross machine weight 390 089 kg, weight distributions. Body weight 38 703 kg: "
                      "assumption, chosen inside the published range so that empty + nominal payload = target gross machine weight",
        },
        "payload_policy": {
            "over110_share_max_pct": 10.0, "single_max_pct": 120.0, "mean_max_pct": 100.0,
            "source": "Cat Mining Truck 10/10/20 overload policy, referenced on the spec sheet: the mean payload must not exceed the "
                      "target, no more than 10 % of loads may exceed 110 % of target, no load may exceed 120 % of target",
        },
        "haul_road": {
            "rolling_resistance_pct": 3.0, "ramp_grade_pct": 10.0, "speed_limit_loaded_kmh": 40.0, "speed_limit_empty_kmh": 50.0,
            "downhill_limit_kmh": 30.0,
            "source": SPEC + " rule: 1 % of grade per 10 kg/t of rolling resistance. 3 % rolling resistance, 10 % ramp and the site "
                      "speed limits: " + A + "the mine's haul road survey and traffic rules",
        },
        "tyres": {
            "model": "Michelin 50/80 R 57 XDR250 B E4R", "count": 6, "tkph_rating": 1286, "max_km_per_h": 24,
            "cold_set_kpa": 650.0, "rated_load_kg": 67000.0,
            "k1_km": [5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 25, 30, 40, 50],
            "k1": [1.00, 1.04, 1.06, 1.09, 1.10, 1.12, 1.14, 1.16, 1.17, 1.18, 1.19, 1.20, 1.21, 1.22, 1.23],
            "k2_ref_c": 38.0, "k2_hot": 0.40, "k2_cold": 0.25,
            "temp_alarm_c": 85.0,
            "source": MICH + ": TKPH 1286; load 67 000 kg per tyre at 6.5 bar (the cold inflation pressure used here); K1 table for cycle "
                      "lengths over 5 km; K2 for ambient temperature against the 38 C reference. Tyre gas temperature alarm 85 C: " + A + "the tyre maker's TPMS settings",
        },
        "engine_model": {
            "coolant_regulated_c": 90.0, "coolant_rise_full_k": 55.0, "boost_zero_kpa": 30.0, "boost_full_kpa": 250.0,
            "exhaust_zero_c": 300.0, "exhaust_full_c": 620.0, "crankcase_zero_kpa": 0.3, "crankcase_full_kpa": 0.9,
            "source": "Expected coolant (thermostat-regulated, then ambient + rise in proportion to engine power), boost, exhaust port "
                      "temperature and crankcase pressure against engine power: " + A + "the truck's own baseline from its first 500 h",
        },
        "oil": {
            "fe_per_250h_alert_ppm": 40.0, "si_alert_ppm": 15.0, "hyd_iso_target": [18, 16, 13], "sample_interval_h": 250,
            "source": "Engine oil wear-metal and silicon limits (ICP spectrometry) and the hydraulic oil cleanliness target (ISO 4406): "
                      + A + "your oil laboratory's limits for the C175 and Cat's contamination control targets",
        },
        "demo": {"time_scale": 15, "cycle_s": 120,
                 "note": "Demo only: one haul cycle (load, haul, ramp, dump, return) runs in 120 s of real time; the plant clock runs 15 times faster. "
                         "Shift statistics, oil results and the lifetime counters come from the failure modes, not from the demo clock."},
    },
    "telemetry": {
        "event": "haultruck", "publish_every_s": 10, "device_type": "MINING_HAUL_TRUCK",
        "groups": {"Payload": "Payload monitor (VIMS)", "Haul": "Speed, grade and the reference haul cycle", "Engine": "Engine (J1939 data via VIMS)",
                   "Ambient": "Ambient temperature", "Tyres": "Tyre pressure and temperature (TPMS)", "OilLab": "Engine oil analysis (last sample)",
                   "Hydraulic": "Hoist and brake oil cleanliness (last sample)"},
        "points": [
            {"metric": "payload_t", "path": "Payload.Current", "label": "Payload of the current load (0 when empty)", "unit": "t"},
            {"metric": "shift_payload_mean_t", "path": "Payload.ShiftMean", "label": "Mean payload this shift", "unit": "t"},
            {"metric": "shift_over110_pct", "path": "Payload.ShiftOver110", "label": "Share of loads above 110 % of target this shift", "unit": "%"},
            {"metric": "shift_loads", "path": "Payload.ShiftLoads", "label": "Loads hauled this shift", "unit": "count"},
            {"metric": "speed_kmh", "path": "Haul.Speed", "label": "Ground speed", "unit": "km/h"},
            {"metric": "grade_pct", "path": "Haul.Grade", "label": "Road grade (+ uphill in the direction of travel)", "unit": "%"},
            {"metric": "gear", "path": "Haul.Gear", "label": "Transmission gear (0 = neutral)", "unit": "code"},
            {"metric": "cycle_km", "path": "Haul.CycleLength", "label": "Length of the reference haul cycle this shift", "unit": "km"},
            {"metric": "cycle_min", "path": "Haul.CycleTime", "label": "Duration of the reference haul cycle", "unit": "min"},
            {"metric": "engine_rpm", "path": "Engine.Speed", "label": "Engine speed", "unit": "rpm"},
            {"metric": "fuel_lph", "path": "Engine.FuelRate", "label": "Fuel rate", "unit": "L/h"},
            {"metric": "boost_kpa", "path": "Engine.Boost", "label": "Intake manifold (boost) pressure", "unit": "kPa g"},
            {"metric": "exh_left_c", "path": "Engine.ExhaustLeft", "label": "Exhaust temperature, left bank", "unit": "°C"},
            {"metric": "exh_right_c", "path": "Engine.ExhaustRight", "label": "Exhaust temperature, right bank", "unit": "°C"},
            {"metric": "coolant_c", "path": "Engine.Coolant", "label": "Engine coolant temperature", "unit": "°C"},
            {"metric": "oil_temp_c", "path": "Engine.OilTemp", "label": "Engine oil temperature", "unit": "°C"},
            {"metric": "oil_kpa", "path": "Engine.OilPressure", "label": "Engine oil pressure", "unit": "kPa"},
            {"metric": "crankcase_kpa", "path": "Engine.Crankcase", "label": "Crankcase pressure (blow-by)", "unit": "kPa"},
            {"metric": "fuel_total_l", "path": "Engine.FuelBurned", "label": "Fuel burned since the engine was new or rebuilt", "unit": "L"},
            {"metric": "engine_hours", "path": "Engine.Hours", "label": "Engine hours since new or rebuilt", "unit": "h"},
            {"metric": "ambient_c", "path": "Ambient.Temp", "label": "Ambient temperature", "unit": "°C"},
            {"metric": "ambient_max_c", "path": "Ambient.ShiftMax", "label": "Highest shade temperature this shift", "unit": "°C"},
        ] + [p for i, pos in enumerate(["front left", "front right", "rear left outer", "rear left inner", "rear right inner", "rear right outer"], 1)
             for p in ({"metric": f"tyre{i}_kpa", "path": f"Tyres.P{i}", "label": f"Tyre {i} ({pos}) pressure, hot", "unit": "kPa g"},
                       {"metric": f"tyre{i}_c", "path": f"Tyres.T{i}", "label": f"Tyre {i} ({pos}) gas temperature", "unit": "°C"})] + [
            {"metric": "oil_fe_ppm", "path": "OilLab.Fe", "label": "Iron in engine oil (last sample)", "unit": "ppm"},
            {"metric": "oil_si_ppm", "path": "OilLab.Si", "label": "Silicon in engine oil (last sample)", "unit": "ppm"},
            {"metric": "oil_soot_pct", "path": "OilLab.Soot", "label": "Soot in engine oil (last sample)", "unit": "%"},
            {"metric": "oil_hours", "path": "OilLab.OilHours", "label": "Hours on the oil when sampled", "unit": "h"},
            {"metric": "hyd_iso4", "path": "Hydraulic.ISO4", "label": "Hydraulic oil ISO 4406 code, particles ≥ 4 µm(c)", "unit": "code"},
            {"metric": "hyd_iso6", "path": "Hydraulic.ISO6", "label": "Hydraulic oil ISO 4406 code, particles ≥ 6 µm(c)", "unit": "code"},
            {"metric": "hyd_iso14", "path": "Hydraulic.ISO14", "label": "Hydraulic oil ISO 4406 code, particles ≥ 14 µm(c)", "unit": "code"},
        ],
    },
    "twin_model": {
        "limits": {
            "payload_warn_pct": 110.0, "payload_max_pct": 120.0, "fuel_ratio_alert": 1.12, "boost_ratio_alert": 0.85,
            "exhaust_resid_alert_c": 70.0, "exhaust_spread_alert_c": 50.0, "coolant_resid_alert_k": 8.0, "blowby_resid_alert_kpa": 0.8,
            "load_gate": 0.5, "tyre_cold_min_pct": 90.0, "tkph_ratio_alert": 1.0,
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "payload_overload": {"name": "Overloading at the shovel", "part": "payload",
                             "symptoms": "loads above 110 % of target, shift mean above target, tyres and frame carry more",
                             "rules": ["HT_OVERLOAD_110", "HT_PAYLOAD_POLICY"], "default_ramp_min": 0.5},
        "air_intake_restriction": {"name": "Air filter plugged (intake restriction)", "part": "air intake",
                                   "symptoms": "boost low, exhaust hot on both banks, more fuel for the same work",
                                   "rules": ["HT_FUEL_HIGH", "HT_BOOST_LOW", "HT_EXH_HIGH"], "default_ramp_min": 1.5},
        "injector_fault": {"name": "Injector fault, right bank", "part": "fuel system", "symptoms": "one bank hotter than the other under load",
                           "rules": ["HT_EXH_SPREAD"], "default_ramp_min": 1},
        "cooling_degraded": {"name": "Radiator core plugged with dust", "part": "cooling", "symptoms": "coolant hotter than expected for the power and ambient",
                             "rules": ["HT_COOLANT_HIGH"], "default_ramp_min": 1.5},
        "dust_ingestion": {"name": "Dust ingestion after the air filter", "part": "engine", "symptoms": "silicon and iron in the oil, blow-by up",
                           "rules": ["HT_OIL_DIRT", "HT_OIL_WEAR", "HT_BLOWBY_HIGH"], "default_ramp_min": 1},
        "hydraulic_contamination": {"name": "Hoist and brake oil contaminated", "part": "hydraulics", "symptoms": "ISO 4406 code above target",
                                    "rules": ["HT_HYD_CLEANLINESS"], "default_ramp_min": 0.5},
        "tyre_underinflation": {"name": "Slow leak, tyre 3 (rear left outer)", "part": "tyres", "symptoms": "cold-equivalent pressure low, tyre runs hot",
                                "rules": ["HT_TYRE_PRESSURE_LOW", "HT_TYRE_TEMP_HIGH"], "default_ramp_min": 1},
        "tkph_exceeded": {"name": "Haul cycle beyond the tyres' TKPH", "part": "haul cycle", "symptoms": "longer, faster cycles on a hot day: site TKPH above the tyre rating",
                          "rules": ["HT_TKPH_LIMIT"], "default_ramp_min": 1},
    },
    "presentation": {"title": "HT-4001 mining haul truck", "dashboard": "MINING_HAUL_TRUCK"},
}

out = HERE / "twin" / "ht-4001.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
