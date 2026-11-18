"""Write twin/cr-6301.twin.json: the chilled-water computer room air handler twin (CR-6301).

    python build_twin.py

CR-6301 is a downflow chilled-water computer room air handler (CRAH) on the raised floor of a data hall: a Vertiv Liebert PCW
PH081DC with two EC plug fans, a chilled water coil with filters on the coil face, a modulating chilled water valve, a return
temperature/humidity sensor, a supply air sensor and remote temperature/humidity sensors at the rack inlets and in the hot aisle.

Sources and assumptions (every number below is either from a published document or labelled as an assumption in "source"):
  Vertiv Liebert PCW brochure, Asia-Pacific (TM-EN-AP-4-2-1-21-12, 2021), downflow table, model PH081DC: cooling capacity 83.3 kW,
    sensible cooling capacity 83.3 kW at 29.5 C DB / 32 % RH return air, airflow 20,000 m3/h, 2 fans, external static pressure
    20 Pa, chilled water supply 10 C and return 16.5 C; 2050 x 890 mm footprint, 2570 mm high, 590 kg with the fan module.
  Vertiv Liebert PCW guide specifications SL-70836 Rev A (02-22), the same family for the Americas (PW035-PW170): EC plug fans,
    nominal 3.5 kW (4.7 hp) motors, two for the PW070 and PW080, max 1800 rpm; MERV 8 or MERV 11 filters (ASHRAE 52.2) on the
    coil face with a filter clog alarm; 2-way or 3-way modulating chilled water valve with electronic actuator; return T/H,
    supply air and up to 10 remote T/H sensors; fan speed control on return, remote, delta T or underfloor static pressure;
    BACnet IP, Modbus TCP and SNMP on the iCOM controller.
  ASHRAE TC 9.9 thermal guidelines (2021, a guideline), as summarised by secondary sources: recommended server inlet 18-27 C,
    dew point -9 to 15 C; class A1 allowable 15-32 C.
  Textbook: sensible heat Q = m cp dT, counterflow LMTD and UA, fan affinity laws, Magnus dew point formula.
  Fan power, pressure drops, coil scaling exponents, valve size, IT load and all alarm limits: ASSUMPTIONS of typical values,
  to be replaced by the unit's selection printout, the commissioning report and the site's own setpoints.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with "

twin = {
    "$comment": "CR-6301 chilled-water CRAH twin. Expected values in Maximo Monitor from the maker's rating, the coil and fan physics and the site setpoints; the unit controller, the BTU meter and the remote sensors send only what they measure.",
    "twin": {"id": "CR-6301", "name": "Computer room air handler CR-6301", "version": "1.0.0", "folder": "crah-twin"},
    "identification": {
        "asset": "CR-6301", "assetnum": "CR-6301", "manufacturer": "Vertiv",
        "model": "Liebert PCW PH081DC (downflow, chilled water, 2 EC fans)",
        "description": "Data hall B computer room air handler 1 of 4 (N+1): chilled water, downflow onto the raised floor",
        "site": "Demo data centre, hall B, raised floor, cold aisle containment",
        "unit": "Perimeter chilled-water CRAH, draw-through coil, filters on the coil face, EC plug fans in the floor void",
        "fans": "2 direct-driven backward-curved EC plug fans, continuous speed control from the unit controller",
        "valve": "2-way modulating chilled water valve with electronic actuator",
        "controller": "Vertiv Liebert iCOM unit controller (BACnet IP / Modbus TCP / SNMP)",
        "sensors": "Return T/H, supply air temperature, remote T/H at the rack inlets (max of 6) and in the hot aisle, filter differential pressure, underfloor static pressure, BTU meter on the unit's chilled water branch",
    },
    "design": {
        "rating": {
            "q_sensible_kw": 83.3, "airflow_m3h": 20000.0, "return_air_c": 29.5, "return_rh_pct": 32.0,
            "chw_supply_c": 10.0, "chw_return_c": 16.5, "esp_pa": 20.0, "fans": 2,
            "source": "Vertiv Liebert PCW brochure (Asia-Pacific, TM-EN-AP-4-2-1-21-12), downflow model PH081DC: sensible cooling "
                      "capacity 83.3 kW (equal to the total capacity, SHR 1.0) at 29.5 C DB / 32 % RH return air, 20,000 m3/h, 2 fans, "
                      "ESP 20 Pa, chilled water 10 C supply / 16.5 C return.",
        },
        "coil": {
            "air_exp": 0.6, "water_exp": 0.25, "airflow_at": "supply",
            "source": "The rated UA is computed from the rating point with a counterflow LMTD (the real coil is cross-counterflow, a "
                      "few rows deep: the LMTD form is an approximation that is the same in the twin and its check). The airflow is "
                      "taken at supply-air density (the fans sit after the coil). UA scaling with airflow and water flow, "
                      "UA = UA_rated x (V/V_rated)^0.6 x (F/F_rated)^0.25: " + A + "the coil selection printout at 3 or 4 flows.",
        },
        "fan": {
            "power_rated_kw": 3.4, "dp_total_rated_pa": 300.0, "filter_dp_clean_pa": 60.0, "filter_exp": 1.6,
            "speed_at_rated_pct": 85.0, "motor_kw_each": 3.5,
            "source": "Motors: nominal 3.5 kW each (Vertiv guide specifications SL-70836 for the PW070/PW080 of the same family). "
                      "Absorbed power of both fans at 20,000 m3/h with clean filters (3.4 kW), total pressure the fans make at that "
                      "airflow (300 Pa: 20 Pa ESP + coil, filter, cabinet and fan inlet), clean filter drop at 20,000 m3/h (60 Pa, "
                      "MERV 8 on the coil face), filter drop exponent 1.6 and fan speed at the rated airflow: " + A + "the unit's "
                      "selection printout and the commissioning report.",
        },
        "valve": {
            "flow_max_m3h": 13.0, "characteristic": "linear installed (assumption)",
            "source": "Chilled water flow with the valve fully open at the available differential pressure: " + A + "the balancing "
                      "report of the branch. The rated water flow, 11.0 m3/h, follows from 83.3 kW and 10/16.5 C.",
        },
        "site": {
            "it_load_kw": 60.0, "it_dt_k": 12.0, "supply_setpoint_c": 20.0, "underfloor_setpoint_pa": 20.0,
            "dewpoint_target_c": 9.0, "units": 4, "redundancy": "N+1",
            "source": "IT load carried by this unit, temperature rise across the servers, supply air setpoint, underfloor static "
                      "pressure setpoint and dew point target of the hall: " + A + "the hall's design basis and the BMS setpoints.",
        },
        "envelope": {
            "recommended_low_c": 18.0, "recommended_high_c": 27.0, "allowable_a1_high_c": 32.0,
            "dewpoint_low_c": -9.0, "dewpoint_high_c": 15.0,
            "source": "ASHRAE TC 9.9 thermal guidelines for data processing environments (2021, a guideline, not a standard), as "
                      "summarised by secondary sources: recommended server inlet 18 to 27 C dry bulb, dew point -9 to 15 C; class A1 "
                      "allowable up to 32 C. Measured at the server inlet, not at the CRAH.",
        },
        "air": {"cp_kj_kgk": 1.006, "rho_const": 353.05, "water_cp_kj_kgk": 4.19, "water_rho": 1000.0,
                "magnus_a": 17.625, "magnus_b": 243.04,
                "source": "Dry air cp 1.006 kJ/kg K; air density = 101325 / (287.05 x T) = 353.05 / T(K) at sea level; water "
                          "cp 4.19 kJ/kg K and 1000 kg/m3; Magnus dew point coefficients 17.625 and 243.04 C (textbook values)."},
        "demo": {"time_scale": 1, "hunting_period_s": 80,
                 "note": "Demo: the plant clock runs in real time; a failure mode ramps in over about a minute. The IT load swings a few per cent over the day."},
    },
    "telemetry": {
        "event": "crah", "publish_every_s": 10, "device_type": "CRAH_CHILLED_WATER",
        "groups": {"Air": "Return and supply air at the unit", "Rack": "Remote sensors at the rack inlets and in the hot aisle",
                   "Water": "Chilled water branch (BTU meter)", "Valve": "Chilled water valve", "Fan": "EC fans",
                   "Filter": "Filters on the coil face", "Humidity": "Humidity control", "Control": "Setpoints and floor pressure"},
        "points": [
            {"metric": "return_air_c", "path": "Air.ReturnTemp", "label": "Return air temperature", "unit": "°C"},
            {"metric": "return_rh_pct", "path": "Air.ReturnRH", "label": "Return air relative humidity", "unit": "%"},
            {"metric": "supply_air_c", "path": "Air.SupplyTemp", "label": "Supply air temperature", "unit": "°C"},
            {"metric": "rack_inlet_c", "path": "Rack.InletTemp", "label": "Server inlet temperature (max of the remote sensors)", "unit": "°C"},
            {"metric": "rack_inlet_rh_pct", "path": "Rack.InletRH", "label": "Server inlet relative humidity", "unit": "%"},
            {"metric": "rack_outlet_c", "path": "Rack.OutletTemp", "label": "Hot aisle temperature (server outlet)", "unit": "°C"},
            {"metric": "chw_supply_c", "path": "Water.SupplyTemp", "label": "Chilled water supply temperature", "unit": "°C"},
            {"metric": "chw_return_c", "path": "Water.ReturnTemp", "label": "Chilled water return temperature", "unit": "°C"},
            {"metric": "chw_flow_m3h", "path": "Water.Flow", "label": "Chilled water flow", "unit": "m³/h"},
            {"metric": "valve_pos_pct", "path": "Valve.Position", "label": "Chilled water valve position", "unit": "%"},
            {"metric": "valve_reversals_h", "path": "Valve.Reversals", "label": "Valve direction reversals, last hour", "unit": "count"},
            {"metric": "fan_speed_pct", "path": "Fan.Speed", "label": "EC fan speed", "unit": "%"},
            {"metric": "airflow_m3h", "path": "Fan.Airflow", "label": "Airflow (from the fan inlet rings)", "unit": "m³/h"},
            {"metric": "fan_power_kw", "path": "Fan.Power", "label": "Fan electrical power, both fans", "unit": "kW"},
            {"metric": "filter_dp_pa", "path": "Filter.PressureDrop", "label": "Filter differential pressure", "unit": "Pa"},
            {"metric": "humidifier_pct", "path": "Humidity.Humidifier", "label": "Humidifier output", "unit": "%"},
            {"metric": "supply_setpoint_c", "path": "Control.SupplySetpoint", "label": "Supply air setpoint", "unit": "°C"},
            {"metric": "underfloor_pa", "path": "Control.UnderfloorPressure", "label": "Underfloor static pressure", "unit": "Pa"},
            {"metric": "unit_on", "path": "Control.UnitOn", "label": "Unit running (1 = on)", "unit": "code"},
        ],
    },
    "twin_model": {
        "limits": {
            "coil_balance_tol": 0.15, "ua_ratio_alert": 0.75, "chw_dt_low_k": 4.5, "valve_saturated_pct": 95.0,
            "supply_over_sp_k": 1.5, "filter_ratio_alert": 2.0, "fan_power_ratio_alert": 1.2, "sfp_alert_w_m3s": 550.0,
            "bypass_alert": 0.25, "recirc_alert_k": 5.0, "valve_reversals_alert_h": 30.0, "dp_mismatch_k": 2.5,
            "source": A + "the site's operating procedures; the inlet and dew point limits come from design.envelope.",
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "coil_fouling": {"name": "Coil fouling (dust on the fins, scale in the tubes)", "part": "coil",
                         "symptoms": "UA falls, the valve opens further for the same load, the water comes back colder (low delta T), at the end the supply air cannot be held",
                         "rules": ["CRAH_UA_LOW", "CRAH_CHW_DT_LOW", "CRAH_VALVE_SATURATED"], "default_ramp_min": 1.5},
        "filter_loading": {"name": "Filters loaded with dust", "part": "filter",
                           "symptoms": "filter pressure drop up at the same airflow, fans speed up to hold the floor pressure, fan power follows the extra pressure",
                           "rules": ["CRAH_FILTER_DIRTY"], "default_ramp_min": 1.5},
        "fan_degradation": {"name": "EC fan degradation (dirty impeller, bearing wear, one module derated)", "part": "fan",
                            "symptoms": "more power than the fan law expects for the airflow and pressure, filters normal",
                            "rules": ["CRAH_FAN_POWER_HIGH"], "default_ramp_min": 1.5},
        "bypass_air": {"name": "Bypass airflow (open cable cut-outs, misplaced perforated tiles)", "part": "airflow",
                       "symptoms": "cold air returns to the unit without passing a server: return temperature low, airflow and fan power up",
                       "rules": ["CRAH_BYPASS_HIGH", "CRAH_SFP_HIGH"], "default_ramp_min": 1},
        "recirculation": {"name": "Hot air recirculation (cold aisle short of air, missing blanking panels)", "part": "airflow",
                          "symptoms": "the servers draw more air than reaches the cold aisle and pull their own exhaust back in: floor pressure and airflow down, server inlet much warmer than the supply air, inlet leaves the recommended envelope",
                          "rules": ["CRAH_RECIRC_HIGH", "CRAH_INLET_HIGH"], "default_ramp_min": 1},
        "valve_hunting": {"name": "Chilled water valve hunting (control loop tuning, actuator play)", "part": "valve",
                          "symptoms": "valve reverses direction many times an hour, supply air swings around the setpoint",
                          "rules": ["CRAH_VALVE_HUNTING"], "default_ramp_min": 0.5},
        "humidity_sensor_drift": {"name": "Return humidity sensor drifting low", "part": "humidity",
                                  "symptoms": "controller humidifies a room that is already humid: dew point at the rack inlet rises, the two humidity sensors disagree",
                                  "rules": ["CRAH_RH_SENSOR_MISMATCH", "CRAH_DEWPOINT_HIGH"], "default_ramp_min": 1.5},
        "supply_sensor_drift": {"name": "Supply air sensor reading low", "part": "sensor",
                                "symptoms": "the air side shows more heat than the water side carries; the room runs warmer than the setpoint suggests",
                                "rules": ["CRAH_COIL_BALANCE"], "default_ramp_min": 1},
    },
    "presentation": {"title": "CR-6301 chilled-water computer room air handler", "dashboard": "CRAH_CHILLED_WATER"},
}

out = HERE / "twin" / "cr-6301.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
