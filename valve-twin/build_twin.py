"""Build twin/fcv-401.twin.json: KSB BOA-CVE IMS DN 100 PN 16 control valve with EA-C 40 actuator.

Sources (cad/ksb, kept out of git):
  KSB_7520.1_BOA-CVE_EN.pdf   KSB type series booklet 7520.1/23-EN (BOA-CVE C/CS/W/IMS/EKB/IMS EKB):
                              Table 7/8 programme overview (DN 100: Kvs 160/200/250/300 m3/h, stroke 28/34/42/57 mm;
                              EA-C 40 closing pressure 5 bar at 0.05 % of Kvs, 2.5 bar drop-tight),
                              Table 10 (linear characteristic, leakage 0.05 % of Kvs, -10..+120 C),
                              Table 11 (EA-C 40 4.5 kN, 0.45-0.9 mm/s, 0/2-10 V or 4-20 mA, 24 V AC/DC),
                              Table 16/17 (DN 100 valve 10.5 kg; EA-C 40 6.0 kg)
  BOA-CVE_IMS_DN_100_PN_16_EA-C_40_B04A.glb / .stp   KSB 3D CAD (3dfindit / KSB PARTcommunity, CADENAS)
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).parent
KVS, STROKE = 200.0, 34.0
SEAT_D = 0.100                       # seat ~ DN (assumption for the unbalanced plug load)


def P(metric, path, label, unit, rng, noise, opc=None):
    return {"metric": metric, "path": path, "label": label, "unit": unit, "range": rng, "noise": noise, "opc": opc}


points = [
    P("flow_setpoint_m3h", "Control.FlowSetpoint", "Flow setpoint (building demand)", "m3/h", [0, 250], 0, "haystack: chilled water flow sp"),
    P("flow_m3h", "Valve.Flow", "Flow (BOA-Control IMS measuring section)", "m3/h", [0, 250], 0.25, "haystack: chilled water flow sensor"),
    P("fluid_temp_c", "Valve.FluidTemp", "Fluid temperature (IMS sensor)", "degC", [-10, 120], 0.03, "haystack: chilled water temp sensor"),
    P("inlet_pressure_bar", "Line.SupplyPressure", "Supply pressure upstream of the strainer", "bar(a)", [0, 16], 0.004, "haystack: pressure sensor"),
    P("strainer_dp_bar", "Line.StrainerDifferentialPressure", "Strainer differential pressure", "bar", [0, 2], 0.0003),
    P("valve_inlet_pressure_bar", "Valve.InletPressure", "Valve inlet pressure p1", "bar(a)", [0, 16], 0.004),
    P("valve_outlet_pressure_bar", "Valve.OutletPressure", "Valve outlet pressure p2", "bar(a)", [0, 16], 0.004),
    P("return_pressure_bar", "Line.ReturnPressure", "Return pressure (network)", "bar(a)", [0, 16], 0.004),
    P("position_cmd_pct", "Actuator.PositionSetpoint", "Position setpoint (2-10 V)", "%", [0, 100], 0, "haystack: valve cmd"),
    P("position_pct", "Actuator.PositionFeedback", "Position feedback (2-10 V)", "%", [0, 100], 0.05, "haystack: valve sensor"),
    P("stem_travel_mm", "Actuator.Stroke", "Stem travel", "mm", [0, 60], 0.02),
    P("actuator_force_pct", "Actuator.Force", "Actuator stem force (of 4.5 kN)", "%", [0, 120], 0.3),
    P("actuator_power_w", "Actuator.Power", "Actuator power", "W", [0, 120], 0.2),
    P("actuator_temp_c", "Actuator.MotorTemp", "Actuator motor temperature", "degC", [-20, 120], 0.1),
    P("body_vibration_mm_s", "Valve.Vibration", "Valve body vibration (cavitation noise)", "mm/s", [0, 40], 0.03),
    P("gland_leak_ml_min", "Valve.GlandLeak", "Stem seal leak detector", "ml/min", [0, 200], 0.02),
    P("travel_total_m", "Actuator.TravelTotal", "Accumulated stem travel", "m", [0, 1e6], 0),
    P("reversals", "Actuator.Reversals", "Direction reversals", "count", [0, 1e9], 0),
    P("fault_code", "Actuator.FaultCode", "Actuator fault (0 none, 1 over-force stop)", "code", [0, 9], 0),
]

failure_modes = {
    "seat_plug_wear": {"label": "Seat and plug wear (cavitation erosion)", "cause": "Cavitation and wire-drawing erode the plug contour and seat: the valve passes more than its Kv at small openings",
                       "detect": ["kv_ratio", "sigma", "body_vibration_mm_s"], "action": "Replace plug and seat; review sizing (Kvs) and the network differential pressure at night", "default_ramp_min": 20},
    "stiction": {"label": "Stem stiction (packing friction)", "cause": "Dry or over-tightened packing: the stem sticks, then jumps, and the loop hunts",
                 "detect": ["actuator_force_pct", "force_deviation_pct", "position_error_pct", "reversals"], "action": "Service the stem seal; check stem for scoring", "default_ramp_min": 15},
    "gland_leak": {"label": "Stem seal (gland) leak", "cause": "Worn EPDM profile ring on the stem lets water escape", "detect": ["gland_leak_ml_min"],
                   "action": "Replace the stem seal (profile ring)", "default_ramp_min": 10},
    "actuator_fault": {"label": "Actuator gear / motor wear", "cause": "Worn gear train and motor: more power and heat for the same force, slower stroke",
                       "detect": ["actuator_power_w", "actuator_temp_c", "position_error_pct"], "action": "Replace or overhaul the EA-C actuator", "default_ramp_min": 15},
    "position_sensor_drift": {"label": "Position feedback drift", "cause": "Feedback potentiometer drifts: the reported opening no longer matches the plug",
                              "detect": ["kv_ratio", "position_pct"], "action": "Recalibrate the actuator (KSB parameterisation unit / PC tool)", "default_ramp_min": 10},
    "strainer_blockage": {"label": "Upstream strainer blockage", "cause": "Debris collects in the strainer: less pressure reaches the valve, which opens wider to compensate",
                          "detect": ["strainer_kv_ratio", "position_pct", "flow_error_pct"], "action": "Clean the strainer basket", "default_ramp_min": 20},
}

twin = {
    "$comment": "Single source of truth for the FCV-401 digital twin: KSB BOA-CVE IMS DN 100 control valve with EA-C 40 electric actuator on the "
                "chilled-water side of a district-cooling energy transfer station. Valve and actuator data from KSB type series booklet 7520.1/23-EN.",
    "twin": {"id": "urn:maximo:twin:controlvalve:FCV-401", "version": "1.0.0",
             "kind": "Globe control valve with electric actuator and integrated flow measurement",
             "standards": {
                 "performance": f"KSB 7520.1/23-EN: BOA-CVE IMS DN 100 PN 16, Kvs {KVS:.0f} m3/h, stroke {STROKE:.0f} mm, linear characteristic, "
                                "leakage 0.05 % of Kvs; EA-C 40 actuator 4.5 kN, 0.45-0.9 mm/s",
                 "sizing": "IEC 60534-2-1 flow equation for incompressible fluids, Q = Kv sqrt(dp / (rho/1000))",
                 "cavitation": "Cavitation index sigma = (p1 - pv)/(p1 - p2) per ISA-RP75.23; limits are typical globe-valve values, not KSB data",
                 "information_model": "Points named after BACnet objects with Project Haystack tags"}},
    "identification": {"assetnum": "FCV-401", "description": "Chilled-water control valve 401 (ETS building B4)",
                       "manufacturer": "KSB", "model": "BOA-CVE IMS DN 100 PN 16 EA-C 40",
                       "site": "Demo district cooling plant", "location": "Energy transfer station B4 / primary chilled water",
                       "medium": "Chilled water 6-8 C, PN 16"},
    "design": {
        "valve": {"dn": 100, "pn": 16, "kvs_m3h": KVS, "kvs_options_m3h": [160, 200, 250, 300], "stroke_mm": STROKE, "characteristic": "linear",
                  "leakage_pct_kvs": 0.05, "seat_area_m2": round(math.pi * SEAT_D ** 2 / 4, 5), "seat_note": "seat diameter assumed = DN",
                  "closing_pressure_bar": 5.0, "fluid_temp_range_c": [-10, 120], "weight_kg": 10.5, "face_to_face_mm": 350},
        "actuator": {"type": "EA-C 40 continuous-action", "force_n": 4500, "speed_mm_s": [0.45, 0.9], "speed_set_mm_s": 0.6, "signal": "2-10 V DC (0/2-10 V or 4-20 mA)",
                     "supply": "24 V AC/DC", "weight_kg": 6.0, "packing_friction_n": 600, "friction_note": "packing friction assumed"},
        "strainer": {"kv_clean_m3h": 600, "note": "Y-strainer upstream, clean Kv assumed"},
        "system": {"design_flow_m3h": 120, "hx_kv_m3h": 170, "hx_note": "plate heat exchanger + piping, 0.5 bar at 120 m3/h (assumed)",
                   "supply_pressure_bar_a": 3.2, "network_dp_bar_day": 1.05, "network_dp_bar_night": 1.85},
        "cavitation": {"sigma_incipient": 2.0, "sigma_damage": 1.3, "basis": "typical globe valve (ISA-RP75.23), assumed"},
        "control": {"loop": "BMS flow PI -> actuator position setpoint", "deadband_pct": 0.5},
    },
    "telemetry": {"event": "valve", "publish_every_s": 5, "device_type": "CONTROL_VALVE",
                  "groups": {"Control": "Control loop", "Valve": "Valve body and IMS measurement", "Line": "Line pressures",
                             "Actuator": "EA-C actuator"},
                  "points": points},
    "twin_model": {"limits": {"kv_check_min_open": 0.08, "kv_wear_min_open": 0.005, "kv_ratio_high": 1.15, "kv_ratio_low": 0.85, "force_dev_alert_pct": 15,
                              "position_error_alert_pct": 1.5, "actuator_temp_alert_c": 75, "force_alert_pct": 95,
                              "gland_leak_alert_ml_min": 2.0, "strainer_kv_ratio_alert": 0.6, "flow_error_alert_pct": 5}},
    "failure_modes": failure_modes,
    "presentation": {
        "category": "Control valve",
        "kpis": [{"metric": "flow_m3h", "label": "Flow", "unit": "m³/h", "decimals": 1},
                 {"metric": "position_pct", "label": "Opening", "unit": "%", "decimals": 1},
                 {"metric": "valve_inlet_pressure_bar", "label": "p1", "unit": "bar(a)", "decimals": 2},
                 {"metric": "actuator_force_pct", "label": "Stem force", "unit": "%", "decimals": 0}],
        "twin_kpis": [{"metric": "kv_ratio", "label": "Kv vs. KSB", "unit": "x", "decimals": 3},
                      {"metric": "sigma", "label": "Cavitation index σ", "unit": "", "decimals": 2}],
        "compare": [
            {"label": "Flow coefficient Kv", "measured": "kv_measured", "expected": "kv_expected", "unit": "m³/h", "decimals": 1,
             "basis": "KSB Kvs 200, linear characteristic at the reported opening"},
            {"label": "Stem force", "measured": "actuator_force_pct", "expected": "force_expected_pct", "unit": "%", "decimals": 1,
             "basis": "Packing friction + dp x seat area, of EA-C 40 4.5 kN"},
            {"label": "Flow", "measured": "flow_m3h", "expected": "flow_setpoint_m3h", "unit": "m³/h", "decimals": 1, "basis": "BMS demand"},
            {"label": "Position", "measured": "position_pct", "expected": "position_cmd_pct", "unit": "%", "decimals": 1, "basis": "2-10 V setpoint"},
            {"label": "Cavitation index σ", "measured": "sigma", "expected": None, "unit": "", "decimals": 2, "basis": "(p1 - pv)/(p1 - p2); incipient < 2.0"},
            {"label": "Valve authority", "measured": "valve_authority", "expected": None, "unit": "", "decimals": 2, "basis": "valve dp / circuit dp"},
            {"label": "Strainer Kv ratio", "measured": "strainer_kv_ratio", "expected": None, "unit": "x clean", "decimals": 2, "basis": "Kv 600 clean"},
        ],
        "trends": [{"metric": "kv_ratio", "label": "Kv ratio"}, {"metric": "sigma", "label": "Sigma"},
                   {"metric": "position_error_pct", "label": "Position error %"}, {"metric": "force_deviation_pct", "label": "Force deviation pts"}],
        "design": [
            {"label": "Valve", "value": f"KSB BOA-CVE IMS DN 100 PN 16, Kvs {KVS:.0f} m³/h, stroke {STROKE:.0f} mm, linear, 0.05 % Kvs leakage"},
            {"label": "Actuator", "value": "KSB EA-C 40, 4.5 kN, 0.45-0.9 mm/s, 2-10 V, 24 V AC/DC"},
            {"label": "Duty", "value": "ETS B4 chilled water, 120 m³/h design, network dp 1.05 bar day / 1.85 bar night"},
            {"label": "Source", "value": "KSB type series booklet 7520.1/23-EN; KSB 3D CAD via 3dfindit"},
        ],
    },
}

if __name__ == "__main__":
    json.dump(twin, open(HERE / "twin" / "fcv-401.twin.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("written", HERE / "twin" / "fcv-401.twin.json")
