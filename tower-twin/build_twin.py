"""Build twin/ct-301.twin.json: BAC FXV-0812B-16D-L closed-circuit cooling tower, calibrated to BAC's rating.

Sources (cad/bac, BAC public downloads, kept out of git):
  fxv_engineering_data.pdf  BAC FXV Engineering Data (B014, 2023-06-30): nominal tons, fan HP, CFM, spray pump,
                            coil volume, weights and dimensions per model
  fxv-0812b-1220-4.sat      BAC 3D CAD of the FXV-0812B (Autodesk Inventor ACIS export)
BAC rating basis (engineering data note 1): 1 nominal ton = 3 USGPM of water cooled 95 -> 85 F at 78 F wet bulb.
"""
import json
import math
from pathlib import Path

import twin_calc as tc

HERE = Path(__file__).parent
GPM = 0.2271247          # m3/h per USGPM
CFM = 0.000471947        # m3/s per CFM
HP = 0.7457              # kW per HP
F2C = lambda f: (f - 32) / 1.8

MODEL = "FXV-0812B-16D-L"
TONS, FAN_HP, AIR_CFM = 131, 15, 83810                      # BAC engineering data, FXV-0812B-16D-L
SPRAY_GPM, PUMP_HP, COIL_GAL = 719, 5, 117                  # BAC engineering data, FXV-0812 / 0812B-16D
WEIGHT_LB, H_FT, L_FT = 15560, 15.25, 12.0

flow_nom = TONS * 3 * GPM                                   # m3/h (393 USGPM)
t_in, t_out, t_wb = F2C(95), F2C(85), F2C(78)
cp = 4.18 * 0.998 / 3.6 * 1.0                               # kW per (m3/h K): water at ~30 C (rho 996, cp 4.18)
cp = round(996 * 4.18 / 3600, 5)
q_nom = cp * flow_nom * (t_in - t_out)
rho_air = 1.15                                              # kg/m3, humid air at the fan (~30 C)
ma0 = AIR_CFM * CFM * rho_air
fan_kw = FAN_HP * HP * 0.88 / 0.917                         # 88 % motor load at full speed, IE3 efficiency 91.7 %


def calibrate():
    twin = {"design": {"thermal": {"UA0_kW_K": 1.0}, "fan": {"air_flow_kg_s": ma0, "motor_power_kw_at_100pct": fan_kw,
                                                            "fan_rpm_at_100pct": 1},
                       "coil": {"fluid_flow_m3h": flow_nom}, "water_cp_kW_per_m3h_K": cp,
                       "spray": {"flow_m3h": 1, "pressure_bar": 1},
                       "water": {"makeup_conductivity_us_cm": 1, "drift_rate_pct": 0}}}
    lo, hi = 1.0, 2000.0
    for _ in range(80):
        mid = (lo + hi) / 2
        twin["design"]["thermal"]["UA0_kW_K"] = mid
        if tc.expected_q(twin, t_in, t_wb, flow_nom, 100) < q_nom:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2, twin


UA0, _cal = calibrate()


def P(metric, path, label, unit, rng, noise, opc=None):
    return {"metric": metric, "path": path, "label": label, "unit": unit, "range": rng, "noise": noise, "opc": opc}


points = [
    P("fluid_in_temp_c", "Fluid.EnteringTemp", "Process fluid entering (from CH-201 condenser)", "degC", [0, 60], 0.03, "haystack: entering condenser water temp sensor"),
    P("fluid_out_temp_c", "Fluid.LeavingTemp", "Process fluid leaving (to CH-201 condenser)", "degC", [0, 60], 0.03, "haystack: leaving condenser water temp sensor"),
    P("fluid_out_setpoint_c", "Fluid.LeavingTempSetpoint", "Leaving fluid setpoint", "degC", [10, 45], 0, "haystack: leaving water temp sp"),
    P("fluid_flow_m3h", "Fluid.Flow", "Process fluid flow", "m3/h", [0, 150], 0.3, "haystack: condenser water flow sensor"),
    P("coil_dp_bar", "Fluid.CoilPressureDrop", "Coil pressure drop", "bar", [0, 3], 0.004),
    P("heat_rejected_kw", "Fluid.HeatRejected", "Heat rejected (flow x range)", "kW", [0, 900], 0),
    P("ambient_dry_bulb_c", "Ambient.DryBulb", "Ambient dry bulb", "degC", [-20, 60], 0.05, "haystack: outside air temp sensor"),
    P("ambient_wet_bulb_c", "Ambient.WetBulb", "Ambient wet bulb", "degC", [-20, 40], 0.05, "haystack: outside air wetBulb sensor"),
    P("ambient_rh_pct", "Ambient.RelativeHumidity", "Ambient relative humidity", "%", [0, 100], 0.3, "haystack: outside air humidity sensor"),
    P("fan_speed_pct", "Fan.SpeedCommand", "Fan VFD speed", "%", [0, 100], 0, "haystack: fan vfd speed cmd"),
    P("fan_rpm", "Fan.ShaftSpeed", "Fan shaft speed (proximity sensor)", "rpm", [0, 600], 0.8),
    P("fan_power_kw", "Fan.MotorPower", "Fan motor power", "kW", [0, 20], 0.03, "haystack: fan elec power sensor"),
    P("fan_current_a", "Fan.MotorCurrent", "Fan motor current", "A", [0, 40], 0.05),
    P("fan_current_imbalance_pct", "Fan.CurrentImbalance", "Fan motor current imbalance", "%", [0, 30], 0.05),
    P("fan_winding_temp_c", "Fan.WindingTemp", "Fan motor winding temperature", "degC", [0, 200], 0.1),
    P("fan_vib_mm_s", "Fan.Vibration", "Fan bearing vibration (velocity RMS)", "mm/s", [0, 40], 0.05),
    P("fan_bearing_temp_c", "Fan.BearingTemp", "Fan bearing temperature", "degC", [0, 150], 0.1),
    P("spray_flow_m3h", "Spray.Flow", "Spray water flow", "m3/h", [0, 250], 0.5),
    P("spray_pressure_bar", "Spray.HeaderPressure", "Spray header pressure", "bar", [0, 2], 0.002),
    P("spray_pump_power_kw", "Spray.PumpPower", "Spray pump power", "kW", [0, 8], 0.02),
    P("basin_temp_c", "Basin.WaterTemp", "Basin water temperature", "degC", [0, 50], 0.05),
    P("basin_level_pct", "Basin.Level", "Basin level", "%", [0, 100], 0.2),
    P("makeup_flow_m3h", "Water.MakeupFlow", "Make-up water flow", "m3/h", [0, 5], 0.005),
    P("blowdown_flow_m3h", "Water.BlowdownFlow", "Blowdown flow", "m3/h", [0, 3], 0.002),
    P("conductivity_us_cm", "Water.Conductivity", "Basin water conductivity", "uS/cm", [0, 6000], 4),
    P("water_m3", "Plant.WaterTotal", "Make-up water total", "m3", [0, 1e7], 0),
    P("energy_kwh", "Plant.EnergyTotal", "Fan and pump energy total", "kWh", [0, 1e9], 0),
    P("run_hours", "Plant.RunHours", "Run hours", "h", [0, 1e6], 0),
    P("running", "Plant.Running", "Running", "0/1", [0, 1], 0),
    P("trip_code", "Plant.TripCode", "Protection trip (0 none, 1 fan vibration, 2 motor winding)", "code", [0, 9], 0),
]

failure_modes = {
    "coil_scaling": {"label": "Coil scaling (external)", "cause": "Mineral scale on the outside of the coil tubes insulates them from the spray film",
                     "detect": ["out_temp_deviation_k", "capacity_ratio_pct", "fan_speed_pct"], "action": "Inspect and descale the coil; review water treatment and cycles",
                     "default_ramp_min": 30},
    "nozzle_blockage": {"label": "Spray nozzle blockage", "cause": "Debris and scale plug spray nozzles: dry patches on the coil",
                        "detect": ["spray_pressure_bar", "spray_flow_m3h", "nozzle_k_ratio", "out_temp_deviation_k"],
                        "action": "Clean spray branches and nozzles; check basin strainer", "default_ramp_min": 20},
    "fan_bearing": {"label": "Fan bearing wear", "cause": "Lubrication loss and wear in the fan shaft bearings",
                    "detect": ["fan_vib_mm_s", "fan_bearing_temp_c"], "action": "Grease or replace fan bearings; check alignment", "default_ramp_min": 20},
    "belt_slip": {"label": "Fan belt slip", "cause": "Worn or loose V-belts: the fan turns slower than the motor drives it",
                  "detect": ["fan_rpm", "belt_slip_pct", "fan_power_kw", "out_temp_deviation_k"], "action": "Re-tension or replace the belts", "default_ramp_min": 15},
    "fan_motor_winding": {"label": "Fan motor winding / supply imbalance", "cause": "Insulation ageing or a weak phase: unbalanced currents heat the winding",
                          "detect": ["fan_current_imbalance_pct", "fan_winding_temp_c", "fan_power_kw"], "action": "Megger the motor, check supply and terminals", "default_ramp_min": 20},
    "drift_eliminator": {"label": "Drift eliminator damage", "cause": "Displaced or broken eliminator blades let spray droplets escape with the air",
                         "detect": ["makeup_flow_m3h", "unaccounted_water_m3h"], "action": "Re-seat or replace eliminator sections", "default_ramp_min": 15},
    "water_treatment": {"label": "Blowdown failure (water treatment)", "cause": "Blowdown valve stuck closed: dissolved solids concentrate in the basin",
                        "detect": ["conductivity_us_cm", "blowdown_flow_m3h", "cycles_of_concentration"], "action": "Free the blowdown valve; check the conductivity controller", "default_ramp_min": 10},
}

twin = {
    "$comment": f"Single source of truth for the CT-301 digital twin: BAC {MODEL} closed-circuit cooling tower serving the CH-201 condenser. "
                "Thermal performance calibrated to BAC's published nominal rating; geometry from BAC 3D CAD.",
    "twin": {"id": "urn:maximo:twin:coolingtower:CT-301", "version": "1.0.0",
             "kind": "Closed-circuit cooling tower (evaporative fluid cooler), induced draft, combined flow",
             "standards": {
                 "performance": f"BAC FXV Engineering Data: {MODEL} = {TONS} nominal tons, i.e. {TONS * 3} USGPM cooled 95 -> 85 F at 78 F wet bulb "
                                f"({q_nom:.0f} kW, {flow_nom:.1f} m3/h, 35.0 -> 29.4 C at 25.6 C); CTI certified",
                 "thermal_model": "Braun effectiveness model for evaporative heat exchangers (air treated as a stream with cs = dh_sat/dT), "
                                  f"UA calibrated to the BAC rating: UA0 = {UA0:.2f} kW/K",
                 "psychrometrics": "Saturation pressure by Magnus (Alduchov-Eskridge); enthalpy of saturated air at 101.325 kPa",
                 "fans": "Fan affinity laws: air flow proportional to speed, power to speed cubed",
                 "information_model": "Points named after BACnet objects with Project Haystack tags"}},
    "identification": {"assetnum": "CT-301", "description": "Closed-circuit cooling tower 301 (CH-201 condenser loop)",
                       "manufacturer": "Baltimore Aircoil Company (BAC)", "model": MODEL,
                       "site": "Demo district cooling plant", "location": "Roof / CT-301",
                       "medium": "Condenser water (closed loop) 35/30 C; spray water open circuit"},
    "design": {
        "water_cp_kW_per_m3h_K": cp,
        "rating": {"tons": TONS, "q_kW": round(q_nom, 1), "fluid_flow_m3h": round(flow_nom, 2), "t_in_C": round(t_in, 2),
                   "t_out_C": round(t_out, 2), "wet_bulb_C": round(t_wb, 2), "source": "BAC FXV Engineering Data, note 1"},
        "thermal": {"UA0_kW_K": round(UA0, 3), "ua_air_exponent": 0.6, "ua_fluid_exponent": 0.2},
        "coil": {"fluid_flow_m3h": round(flow_nom, 2), "volume_l": round(COIL_GAL * 3.785, 0), "connection": "4 in, beveled for welding",
                 "dp_bar_at_rated_flow": 0.55, "dp_note": "assumed (not in BAC engineering data)"},
        "fan": {"motor_hp": FAN_HP, "motor_kw": round(FAN_HP * HP, 2), "motor_power_kw_at_100pct": round(fan_kw, 2),
                "air_flow_cfm": AIR_CFM, "air_flow_kg_s": round(ma0, 2), "fans": 2, "fan_diameter_m": 1.55,
                "fan_rpm_at_100pct": 420, "rpm_note": "fan speed assumed (belt drive ratio not in BAC engineering data)",
                "min_speed_pct": 20},
        "spray": {"flow_m3h": round(SPRAY_GPM * GPM, 1), "pump_hp": PUMP_HP, "pump_power_kw": round(PUMP_HP * HP * 0.85 / 0.89, 2),
                  "pressure_bar": 0.35, "pressure_note": "header pressure assumed"},
        "water": {"makeup_conductivity_us_cm": 500, "conductivity_setpoint_us_cm": 2000, "drift_rate_pct": 0.001,
                  "latent_kJ_kg": tc.LATENT_KJ_KG, "evaporation_share": tc.EVAP_SHARE},
        "dimensions": {"length_m": round(L_FT * 0.3048, 2), "height_m": round(H_FT * 0.3048, 2), "operating_weight_kg": round(WEIGHT_LB * 0.4536)},
        "control": {"fluid_out_setpoint_C": 30.0, "loop": "fan VFD PI on leaving fluid temperature"},
        "load": {"served_by": "CH-201 condenser (heat of cooling + compressor power)", "design_heat_kW": 344, "design_flow_m3h": 57.5},
    },
    "telemetry": {"event": "tower", "publish_every_s": 5, "device_type": "COOLING_TOWER_CLOSED",
                  "groups": {"Fluid": "Process fluid (condenser water)", "Ambient": "Ambient air", "Fan": "Fans and drive",
                             "Spray": "Spray water system", "Basin": "Cold-water basin", "Water": "Water balance", "Plant": "Plant and state"},
                  "points": points},
    "twin_model": {"limits": {"out_dev_alert_k": 1.0, "nozzle_ratio_alert": 1.3, "belt_slip_alert_pct": 4.0, "vib_alert_mm_s": 4.5,
                              "vib_trip_mm_s": 11.0, "bearing_alert_c": 80, "imbalance_alert_pct": 5.0, "winding_alert_c": 130,
                              "winding_trip_c": 155, "unaccounted_water_alert_m3h": 0.25, "conductivity_alert_us_cm": 2800}},
    "failure_modes": failure_modes,
    "presentation": {
        "category": "Closed-circuit cooling tower",
        "kpis": [{"metric": "heat_rejected_kw", "label": "Heat rejected", "unit": "kW", "decimals": 0},
                 {"metric": "fluid_out_temp_c", "label": "Leaving fluid", "unit": "°C", "decimals": 1},
                 {"metric": "ambient_wet_bulb_c", "label": "Wet bulb", "unit": "°C", "decimals": 1},
                 {"metric": "fan_speed_pct", "label": "Fan speed", "unit": "%", "decimals": 0}],
        "twin_kpis": [{"metric": "out_temp_deviation_k", "label": "Leaving fluid vs. BAC rating", "unit": "K", "decimals": 2},
                      {"metric": "approach_k", "label": "Approach", "unit": "K", "decimals": 2}],
        "compare": [
            {"label": "Heat rejected", "measured": "heat_rejected_kw", "expected": "q_expected_kw", "unit": "kW", "decimals": 1,
             "basis": "BAC rating, Braun effectiveness at measured wet bulb, flow and fan speed"},
            {"label": "Leaving fluid", "measured": "fluid_out_temp_c", "expected": "fluid_out_expected_c", "unit": "°C", "decimals": 2,
             "basis": "BAC rating at measured conditions"},
            {"label": "Fan power", "measured": "fan_power_kw", "expected": "fan_power_expected_kw", "unit": "kW", "decimals": 2,
             "basis": "Fan affinity law: power ~ speed^3"},
            {"label": "Approach to wet bulb", "measured": "approach_k", "expected": None, "unit": "K", "decimals": 2, "basis": "Leaving fluid - wet bulb"},
            {"label": "Belt slip", "measured": "belt_slip_pct", "expected": None, "unit": "%", "decimals": 1, "basis": "Fan rpm vs. VFD command"},
            {"label": "Spray nozzle resistance", "measured": "nozzle_k_ratio", "expected": None, "unit": "x clean", "decimals": 2,
             "basis": "(p/p0) / (Q/Q0)^2"},
            {"label": "Unaccounted water", "measured": "unaccounted_water_m3h", "expected": None, "unit": "m³/h", "decimals": 3,
             "basis": "Make-up - evaporation - blowdown - rated drift"},
        ],
        "trends": [{"metric": "out_temp_deviation_k", "label": "Leaving fluid deviation K"}, {"metric": "approach_k", "label": "Approach K"},
                   {"metric": "belt_slip_pct", "label": "Belt slip %"}, {"metric": "nozzle_k_ratio", "label": "Nozzle resistance x"}],
        "design": [
            {"label": "Unit", "value": f"BAC {MODEL}, {TONS} nominal tons, CTI certified, combined flow coil + fill"},
            {"label": "Rating", "value": f"{q_nom:.0f} kW: {flow_nom:.1f} m³/h 35.0 -> 29.4 °C at 25.6 °C wet bulb"},
            {"label": "Fans", "value": f"2 axial fans, {FAN_HP} HP VFD drive, {AIR_CFM:,} CFM ({ma0:.1f} kg/s air)"},
            {"label": "Spray", "value": f"{SPRAY_GPM} USGPM ({SPRAY_GPM * GPM:.0f} m³/h) spray pump, {PUMP_HP} HP; coil {COIL_GAL} gal"},
        ],
    },
}

if __name__ == "__main__":
    (HERE / "twin").mkdir(exist_ok=True)
    json.dump(twin, open(HERE / "twin" / "ct-301.twin.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    chk = tc.expected_q(twin, t_in, t_wb, flow_nom, 100)
    print(f"rating {q_nom:.1f} kW at {flow_nom:.2f} m3/h, UA0 {UA0:.3f} kW/K, model {chk:.1f} kW, air {ma0:.2f} kg/s")
    for wb in (22, 24, 26.5, 28):
        for sp in (40, 70, 100):
            q = tc.expected_q(twin, 35.0, wb, 57.5, sp)
            print(f"  CH-201 duty 57.5 m3/h in 35 C, WB {wb}: speed {sp} % -> {q:.0f} kW, out {35 - q / (cp * 57.5):.2f} C")
