"""Write twin/ahu-6401.twin.json: the air handling unit twin (AHU-6401).

    python build_twin.py

AHU-6401 ventilates one office floor: a Swegon GOLD RX size 20 with a rotary heat exchanger (wheel), glass-fibre bag
filters, direct-driven GOLD Wing+ fans with EC/PM motors and the factory-fitted IQlogic controller, plus a water heating
coil and a chilled-water cooling coil in the supply duct. The building management system (BMS) reads it over BACnet/IP.
The supply airflow follows the CO2 in the extract air (demand-controlled ventilation, DCV).

Sources and assumptions (every number below is either from a named source or labelled as an assumption in "source"):
  Swegon GOLD RX product page: size 20 airflow 0.3 to 1.8 m3/s (Ecodesign), rotary exchanger versions MPE / STE / MTE,
    GOLD Wing+ fans with IE5 EC/PM motors, glass-fibre supply and outdoor air filters, filter holder tight enough for
    ePM1 85 % (F9), IQlogic controls.
  Swegon GOLD RX sizing catalogue (2025-02-21), size 014/020: rated motor shaft power per fan for size 020, 2.4 kW
    (alternative 3.4 kW), 3 x 400 V 50 Hz.
  Swegon GOLD controls page: Modbus TCP / RTU, Metasys N2, Exoline and BACnet IP out of the box; integrated filter
    pressure sensors; SFP, fan power and temperature efficiency monitored in real time.
  Passive House Institute component database, Swegon GOLD F RX STE Aluminium 20 (certified 2023): airflow range 2520 to
    4500 m3/h, specific electric power 0.44 Wh/m3, heat recovery rate 83 %.
  SFP = electric power of the fans / airflow (EN 16798-3, formerly EN 13779). Air density 1.2 kg/m3, cp 1.006 kJ/kg K
    (textbook). Fan affinity: on a fixed duct system the pressure rises with flow squared.
  Everything else (design airflow, pressures, fan efficiency, coil sizes, CO2 generation, prices) is an ASSUMPTION
    labelled as such: replace it with the AHU Design printout of your unit and your own site data.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with your AHU Design selection printout / site data"

# Design point (assumptions inside the published ranges)
Q_D = 1.0                        # m3/s supply = extract at design (3600 m3/h)
ETA_FAN = 0.62                   # fan + motor + EC drive total efficiency
DP_SUP, DP_EXT = 520.0, 460.0    # Pa total pressure rise per fan at design, clean filters
SFP_D = (DP_SUP + DP_EXT) / ETA_FAN / 1000          # kW/(m3/s), both fans, = 1.58
PHI_SEL = 0.44                                      # Wh/m3 (PHI database)

twin = {
    "$comment": "AHU-6401 air handling unit twin. Expected values in Maximo Monitor from the Swegon and Passive House data and fan, heat recovery and coil balances; the unit sends only what it measures.",
    "twin": {"id": "AHU-6401", "name": "Air handling unit AHU-6401", "version": "1.0.0", "folder": "ahu-twin"},
    "identification": {
        "asset": "AHU-6401", "assetnum": "AHU-6401", "manufacturer": "Swegon",
        "model": "GOLD RX 20 (rotary heat exchanger, IQlogic controls)",
        "description": "Office floor air handling unit: rotary heat recovery, ePM1 bag filters, duct heating and cooling coils, EC fans, CO2-controlled, BACnet/IP",
        "unit": "Swegon GOLD RX size 20, indoor, rotary heat exchanger, supply and extract fans GOLD Wing+ with IE5 EC/PM motors",
        "filters": "Glass-fibre bag filters: supply ePM1, extract ePM10 (ISO 16890 classes, assumption of the selected options)",
        "coils": "Low-temperature hot water heating coil and chilled water cooling coil in the supply duct, each with a two-way valve and a heat meter",
        "controls": "Swegon IQlogic, BACnet/IP to the building management system; supply airflow from the extract air CO2 (DCV)",
        "service": "Mechanical ventilation of one open-plan office floor, about 100 workplaces",
    },
    "design": {
        "unit": {
            "size": 20, "airflow_min_m3s": 0.3, "airflow_max_m3s": 1.8, "motor_shaft_kw_per_fan": 2.4,
            "phi_airflow_m3h": [2520, 4500], "phi_sel_wh_m3": PHI_SEL, "phi_heat_recovery_pct": 83,
            "source": "Swegon GOLD RX product page: size 20 airflow 0.3 to 1.8 m3/s (Ecodesign). Swegon GOLD RX sizing catalogue 2025-02-21: "
                      "motor shaft power per fan 2.4 kW (alt. 3.4 kW) for size 020. Passive House Institute component database, GOLD F RX STE "
                      "Aluminium 20: airflow 2520 to 4500 m3/h, specific electric power 0.44 Wh/m3, heat recovery rate 83 %.",
        },
        "airflow": {
            "design_m3s": Q_D, "min_m3s": 0.45, "max_m3s": 1.2, "rho_kg_m3": 1.2, "cp_kj_kgk": 1.006,
            "source": "Design airflow 1.0 m3/s (3600 m3/h, inside the PHI certified range and the size 20 range), DCV minimum 0.45 and maximum "
                      "1.2 m3/s: " + A + ". Air density and heat capacity: textbook values at about 20 C.",
        },
        "fans": {
            "eta_total": ETA_FAN, "dp_supply_pa": DP_SUP, "dp_extract_pa": DP_EXT, "sfp_design_kw_m3s": round(SFP_D, 4),
            "sfp_phi_kw_m3s": round(PHI_SEL * 3.6, 4),
            "source": "Total pressure rise per fan at design with clean filters (filter, wheel, casing, coils and ducts) and total fan efficiency "
                      "(impeller, EC/PM motor and drive): " + A + ". Together they give SFP = (520 + 460) / 0.62 = 1.58 kW/(m3/s) for both fans, "
                      "the same as the PHI certified 0.44 Wh/m3 x 3.6 = 1.58 kW/(m3/s). On the fixed duct system the pressure outside the "
                      "filter rises with flow squared (fan affinity laws); the efficiency is taken constant over the DCV range (assumption).",
        },
        "filters": {
            "supply_class": "ePM1 >= 50 %", "extract_class": "ePM10 >= 50 %",
            "supply_clean_pa": 70.0, "extract_clean_pa": 50.0, "flow_exponent": 1.5,
            "source": "ISO 16890 classes of the selected glass-fibre bag filters, initial pressure drop at design flow, and the exponent of the "
                      "pressure drop against flow (between 1 for laminar and 2 for turbulent flow through the media): " + A
                      + ". The GOLD filter holder is rated for ePM1 85 % bypass leakage (Swegon product page).",
        },
        "heat_recovery": {
            "type": "rotary heat exchanger (wheel), condensation rotor", "eta_design": 0.83, "eta_per_flow": 0.08, "eta_cap": 0.90,
            "source": "Design supply temperature ratio at balanced design flow 0.83, taken from the PHI certified heat recovery rate of 83 % "
                      "(the PHI rate is an effective rate measured by PHI's own method, a conservative stand-in for the EN 308 dry temperature "
                      "ratio). Change of the ratio with flow (-0.08 per 100 % of design flow, more contact time at low flow) and its cap: " + A
                      + ". With unequal flows the supply-side ratio is scaled by extract / supply flow when the extract flow is smaller.",
        },
        "coils": {
            "heating_kw": 40.0, "cooling_kw": 30.0, "supply_setpoint_c": 20.0,
            "source": "Heating and cooling coil capacities at full valve opening and the supply air setpoint: " + A
                      + ". The valve position is taken proportional to the duty (assumption: equal-percentage valve on a coil gives a near-linear "
                        "duty against position). The supply fan motor sits in the air stream: all its electric power ends up as heat in the supply air.",
        },
        "ventilation": {
            "persons_design": 100, "persons_peak": 90, "co2_outdoor_ppm": 420.0, "co2_setpoint_ppm": 900.0,
            "co2_per_person_ls": 0.0052, "design_ls_person": 10.0, "extract_base_c": 21.5, "extract_rise_c": 1.0,
            "source": "Design occupancy, peak occupancy, outdoor CO2, DCV CO2 setpoint, design outdoor air per person and room temperature: " + A
                      + ". CO2 generation 0.0052 l/s per sedentary adult: a commonly quoted value (assumption); Persily and de Jonge (2017) "
                        "give rates by age, sex and activity, replace it with theirs. Steady-state CO2 balance: CO2_room = CO2_out + G x N / Q.",
        },
        "economics": {
            "electricity_eur_kwh": 0.25, "heat_eur_kwh": 0.10, "hours_per_year": 4000, "filter_set_eur": 350.0,
            "loading_pa_per_month": 12.0, "heating_hours": 2500, "heating_mean_outdoor_c": 5.0,
            "source": "Electricity and heat prices, operating hours, cost of one set of supply bag filters with labour, the rate at which the "
                      "supply filter pressure drop rises at design flow, and the heating season: " + A + ".",
        },
        "weather": {"outdoor_mean_c": 0.0, "outdoor_swing_c": 4.0,
                    "source": "Demo weather: a winter day, 0 C mean with a 4 K daily swing (warmest at 15:00). Assumption for the stand-in only."},
        "demo": {"time_scale": 1,
                 "note": "Demo only: the plant clock is the visitor's local time (office hours fill the floor, nights run at the DCV minimum); faults ramp in over minutes, where real filters load over months."},
    },
    "telemetry": {
        "event": "ahu", "publish_every_s": 10, "device_type": "AIR_HANDLING_UNIT",
        "groups": {"Air": "Supply and extract airflow", "Fan": "Fan electric power", "Filter": "Filter pressure drops",
                   "Temp": "Air temperatures", "HR": "Rotary heat exchanger", "Coil": "Heating and cooling coils", "Room": "Room air quality and occupancy"},
        "points": [
            {"metric": "supply_flow_m3s", "path": "Air.SupplyFlow", "label": "Supply airflow", "unit": "m3/s"},
            {"metric": "extract_flow_m3s", "path": "Air.ExtractFlow", "label": "Extract airflow", "unit": "m3/s"},
            {"metric": "supply_fan_kw", "path": "Fan.SupplyPower", "label": "Supply fan electric power", "unit": "kW"},
            {"metric": "extract_fan_kw", "path": "Fan.ExtractPower", "label": "Extract fan electric power", "unit": "kW"},
            {"metric": "supply_filter_pa", "path": "Filter.SupplyDP", "label": "Supply (outdoor air) filter pressure drop", "unit": "Pa"},
            {"metric": "extract_filter_pa", "path": "Filter.ExtractDP", "label": "Extract air filter pressure drop", "unit": "Pa"},
            {"metric": "t_outdoor_c", "path": "Temp.Outdoor", "label": "Outdoor air temperature (ODA)", "unit": "°C"},
            {"metric": "t_extract_c", "path": "Temp.Extract", "label": "Extract air temperature (ETA)", "unit": "°C"},
            {"metric": "t_after_hr_c", "path": "Temp.AfterHR", "label": "Supply air after the wheel", "unit": "°C"},
            {"metric": "t_supply_c", "path": "Temp.Supply", "label": "Supply air temperature (SUP)", "unit": "°C"},
            {"metric": "t_exhaust_c", "path": "Temp.Exhaust", "label": "Exhaust air temperature (EHA)", "unit": "°C"},
            {"metric": "wheel_speed_pct", "path": "HR.WheelSpeed", "label": "Rotor speed command", "unit": "%"},
            {"metric": "heating_valve_pct", "path": "Coil.HeatingValve", "label": "Heating valve position", "unit": "%"},
            {"metric": "cooling_valve_pct", "path": "Coil.CoolingValve", "label": "Cooling valve position", "unit": "%"},
            {"metric": "heating_kw", "path": "Coil.HeatingPower", "label": "Heating coil power (heat meter)", "unit": "kW"},
            {"metric": "cooling_kw", "path": "Coil.CoolingPower", "label": "Cooling coil power (chilled water meter)", "unit": "kW"},
            {"metric": "co2_ppm", "path": "Room.CO2", "label": "CO2 in the extract air", "unit": "ppm"},
            {"metric": "occupancy", "path": "Room.Occupancy", "label": "People on the floor (people counter)", "unit": "count"},
        ],
    },
    "twin_model": {
        "limits": {
            "filter_dirty_ratio": 2.0, "filter_limit_ratio": 3.0, "filter_low_ratio": 0.5, "extract_filter_ratio": 2.5,
            "sfp_ratio_alert": 1.15, "fan_eff_ratio_alert": 0.85, "hr_dev_alert": -0.10, "hr_min_wheel_pct": 95.0, "hr_min_dt_k": 8.0,
            "coil_on_kw": 1.0, "valve_closed_pct": 2.0, "coil_balance_alert_k": 1.5,
            "occ_mismatch_min": 15.0, "occ_mismatch_frac": 0.25, "vent_alert_ls": 7.0, "vent_min_persons": 20.0,
            "flow_balance_alert": 0.10,
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "filter_loading": {"name": "Supply filter loading (dust)", "part": "filters",
                           "symptoms": "supply filter pressure drop above clean at today's flow; fan power and SFP up",
                           "rules": ["AHU_FILTER_SUP_DIRTY", "AHU_FILTER_SUP_LIMIT", "AHU_SFP_HIGH"], "default_ramp_min": 1.5},
        "filter_bypass": {"name": "Torn or badly seated supply filter (bypass)", "part": "filters",
                          "symptoms": "supply filter pressure drop far below clean at today's flow: unfiltered air bypasses",
                          "rules": ["AHU_FILTER_SUP_LOW"], "default_ramp_min": 0.5},
        "fan_degradation": {"name": "Supply fan degradation (dirty impeller, EC motor or drive)", "part": "fans",
                            "symptoms": "supply fan power above expected for its flow and pressure; SFP up with normal filters",
                            "rules": ["AHU_FAN_EFF_LOW", "AHU_SFP_HIGH"], "default_ramp_min": 1.5},
        "wheel_slip": {"name": "Rotor drive belt slipping or broken", "part": "heat recovery",
                       "symptoms": "temperature ratio of the wheel far below expected with the rotor commanded to full speed; heating coil works harder",
                       "rules": ["AHU_HR_EFF_LOW"], "default_ramp_min": 1},
        "heating_valve_passing": {"name": "Heating valve passing (does not close)", "part": "coils",
                                  "symptoms": "heat meter shows heat with the valve closed; the cooling coil opens to take it away again",
                                  "rules": ["AHU_HEAT_VALVE_PASSING", "AHU_SIMULT_HEAT_COOL"], "default_ramp_min": 1},
        "supply_temp_drift": {"name": "Supply air temperature sensor drift", "part": "sensors",
                              "symptoms": "the coil heat balance from the air temperatures disagrees with the heat meters",
                              "rules": ["AHU_COIL_BALANCE"], "default_ramp_min": 1},
        "co2_sensor_drift": {"name": "CO2 sensor drifting low", "part": "sensors",
                             "symptoms": "occupancy implied by CO2 below the people count; DCV cuts the airflow, outdoor air per person falls",
                             "rules": ["AHU_CO2_OCC_MISMATCH", "AHU_UNDERVENTILATION"], "default_ramp_min": 1},
        "extract_blockage": {"name": "Extract duct blocked (fire damper closed, grilles covered)", "part": "ducts",
                             "symptoms": "extract airflow well below supply; extract fan works against a higher pressure",
                             "rules": ["AHU_FLOW_IMBALANCE", "AHU_SFP_HIGH"], "default_ramp_min": 0.5},
    },
    "presentation": {"title": "AHU-6401 air handling unit", "dashboard": "AIR_HANDLING_UNIT"},
}

out = HERE / "twin" / "ahu-6401.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out, "SFP design", round(SFP_D, 4), "PHI", PHI_SEL * 3.6)
