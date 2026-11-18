"""Write twin/bess-3501.twin.json: the grid battery energy storage container twin (BESS-3501).

    python build_twin.py

BESS-3501 is one 10-ft LFP battery container of a grid-scale battery energy storage system (BESS): four battery strings of
396 cells in series (280 Ah lithium iron phosphate), a battery management system (BMS), an embedded HVAC unit, flammable
gas and off-gas detection, and a bidirectional power conversion system (PCS, the inverter) that connects it to the grid.

Sources and assumptions (every number below is either from a published data sheet or labelled as an assumption in "source"):
  Delta Electronics, LFP Battery Container (M Series) data sheet 2024/07: 280 Ah LFP cells, 396S-1P strings, 18 modules per
    string, 1089 to 1386 V DC, 1416 kWh per battery container (4 strings), recommended DoD 95 %, 3080 A, built-in HVAC,
    heat/smoke/gas/flood/humidity/door sensors, gas venting + aerosol + sprinkler, UL 9540A, UL 1973, IEC 62619, UN 38.3.
  EVE LF280K cell specification (as reproduced by a distributor): 3.2 V, 280 Ah, 2.5 to 3.65 V, AC resistance <= 0.25 mOhm,
    >= 6000 cycles at 0.5C and 25 C to 80 % capacity. The container data sheet does not name its cell maker: the LF280K is
    used as a typical 280 Ah LFP cell.
  String resistance, PCS losses, HVAC capacity and COP, ageing constants, gas alarm settings: ASSUMPTIONS of typical values,
    to be replaced by the commissioning and acceptance test data of your own system.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with "

twin = {
    "$comment": "BESS-3501 battery energy storage container twin. Expected values in Maximo Monitor from data sheet, cell specification and commissioning data; the BMS, PCS and HVAC send only what they measure.",
    "twin": {"id": "BESS-3501", "name": "Battery energy storage container BESS-3501", "version": "1.0.0", "folder": "bess-twin"},
    "identification": {
        "asset": "BESS-3501", "assetnum": "BESS-3501", "manufacturer": "Delta Electronics",
        "model": "LFP Battery Container EBSB-CE2818S4PP0Y1 (4 strings, 1416 kWh)",
        "description": "Grid battery energy storage container 3501: 1.4 MWh LFP, BMS, embedded HVAC, with its PCS",
        "site": "Demo grid battery site, block 35",
        "battery": "4 strings x 396 cells in series (18 modules of 22 cells), 280 Ah LFP, 1089 to 1386 V DC",
        "pcs": "Bidirectional power conversion system (inverter), 700 kW for this container (assumption)",
        "hvac": "Embedded HVAC (two air-conditioning units in the container)",
        "safety": "Flammable gas detectors, off-gas detector, smoke and heat detectors, gas venting, aerosol extinguisher, sprinkler",
    },
    "design": {
        "container": {
            "nameplate_kwh": 1416.0, "strings": 4, "cells_series": 396, "modules_per_string": 18, "cells_per_module": 22,
            "cell_ah": 280.0, "dc_v_min": 1089.0, "dc_v_max": 1386.0, "dod": 0.95, "max_current_a": 3080.0,
            "dims_mm": [2438, 2990, 2896], "mass_kg": 16000, "operating_c": [-30, 50],
            "accuracy": "voltage +-0.5 %, current +-1 %, temperature +-2 C, SoC <= 5 %",
            "sensors": "heat x2, smoke x2, gas x2, flood x2, humidity x4, door x4",
            "certification": "UL 9540A, UL 1973, IEC 62619 including fire propagation, UN 38.3, IEC 62477",
            "source": "Delta Electronics LFP Battery Container data sheet (2024/07), battery container IEC version with 4 strings (EBSB-CE2818S4PP0Y1).",
        },
        "cell": {
            "type": "LFP prismatic 280 Ah (for example EVE LF280K)", "nominal_v": 3.2, "v_max": 3.65, "v_min": 2.5,
            "r_ac_mohm": 0.25, "cycle_life": 6000, "cycle_life_end_pct": 80.0, "cycle_life_c_rate": 0.5, "cycle_life_temp_c": 25.0,
            "charge_c": [0, 55], "discharge_c": [-20, 55], "mass_kg": 5.42,
            "source": "EVE LF280K cell specification as reproduced by a distributor (evlithium.com). The container data sheet does not name the cell maker: "
                      + A + "the cell data sheet of your own container.",
        },
        "electrical": {
            "r_string_ohm": 0.18, "pcs_rated_kw": 700.0, "pcs_noload_kw": 3.0, "pcs_loss_rated_kw": 12.0,
            "coulombic_eff": 1.0,
            "source": "String DC resistance (396 cells at about 0.40 mOhm DC each plus busbars and fuses), PCS rating (0.5C of the container), "
                      "PCS no-load loss and loss at rated power (peak efficiency about 98.5 %): " + A + "the PCS efficiency curve and the "
                      "commissioning (IEC 62933-2-1 style) round-trip test of your system.",
        },
        "hvac": {
            "units": 2, "cooling_kw_35c": 25.0, "derate_per_k": 0.015, "cop_35c": 2.8, "cop_slope_per_k": 0.02,
            "supply_setpoint_c": 20.0, "airflow_m3h": 6000.0, "aux_internal_kw": 1.2, "ua_kw_per_k": 0.10, "rho_cp_kj_m3k": 1.206,
            "source": "Total rated cooling of the two units at 35 C outdoor, capacity loss per kelvin above 35 C, COP at 35 C and its slope, "
                      "supply-air setpoint, rated airflow, internal auxiliary load (BMS, lights, fans) and envelope + solar gain UA: "
                      + A + "the HVAC data sheet and the container heat-load calculation.",
        },
        "ageing": {
            "k_cyc_pct_per_efc": 20.0 / 6000.0, "k_cal_pct_sqrt_year": 2.0, "t_ref_c": 25.0, "t_double_k": 15.0,
            "source": "Cycle fade 20 % over 6000 equivalent full cycles at 25 C (from the cell cycle life); calendar fade 2 % x sqrt(years) at 25 C; "
                      "both ageing rates double every 15 K: " + A + "the cell maker's ageing model or your own capacity test history.",
        },
        "service": {
            "required_usable_kwh": 1100.0, "augment_lead_years": 2.0,
            "source": "Usable energy the container must still deliver to meet its share of the site's contract, and the lead time to procure, "
                      "permit and install augmentation: " + A + "the site's offtake contract and augmentation plan.",
        },
        "safety": {
            "offgas_alert_ppm": 10.0, "lel_alert_pct": 10.0, "temp_rate_alert_c_min": 1.0, "cell_temp_alert_c": 50.0,
            "imd_ohm_per_v": 100.0,
            "source": "Off-gas (electrolyte vapour) and flammable gas alarm settings, cell temperature rise-rate and high-temperature alerts, "
                      "insulation monitor alarm (ohm per volt of the highest DC voltage): " + A + "the settings of your detectors, BMS and insulation monitor.",
        },
        "demo": {"time_scale": 24, "rest_s": 60,
                 "note": "Demo only: the battery runs 24 times faster, so a full discharge or charge at 700 kW takes about four minutes of real time, "
                         "with one minute of rest between them. The life counters (days, equivalent full cycles) come from the asset, not from the demo clock."},
    },
    "telemetry": {
        "event": "bess", "publish_every_s": 10, "device_type": "BESS_LFP_CONTAINER",
        "groups": {"Battery": "Container battery (BMS)", "Cells": "Cell voltage and temperature extremes (BMS)", "HVAC": "Embedded HVAC",
                   "PCS": "Power conversion system", "Safety": "Gas detection and insulation", "Energy": "24-hour energy counters",
                   "Life": "Life counters (BMS)"},
        "points": [
            {"metric": "soc_pct", "path": "Battery.SOC", "label": "State of charge (BMS)", "unit": "%"},
            {"metric": "soh_bms_pct", "path": "Battery.SOH", "label": "State of health, capacity (BMS)", "unit": "%"},
            {"metric": "dc_voltage_v", "path": "Battery.Voltage", "label": "DC voltage of the container", "unit": "V"},
            {"metric": "dc_current_a", "path": "Battery.Current", "label": "DC current, 4 strings (+ discharge)", "unit": "A"},
            {"metric": "cell_v_max_v", "path": "Cells.VMax", "label": "Highest cell voltage", "unit": "V"},
            {"metric": "cell_v_min_v", "path": "Cells.VMin", "label": "Lowest cell voltage", "unit": "V"},
            {"metric": "cell_v_spread_rest_mv", "path": "Cells.SpreadAtRest", "label": "Cell voltage spread at the last rest", "unit": "mV"},
            {"metric": "cell_t_max_c", "path": "Cells.TMax", "label": "Highest cell temperature", "unit": "°C"},
            {"metric": "cell_t_min_c", "path": "Cells.TMin", "label": "Lowest cell temperature", "unit": "°C"},
            {"metric": "cell_t_avg_c", "path": "Cells.TAvg", "label": "Mean cell temperature", "unit": "°C"},
            {"metric": "cell_t_max_rate_c_min", "path": "Cells.TMaxRate", "label": "Rise rate of the hottest cell", "unit": "°C/min"},
            {"metric": "hvac_supply_air_c", "path": "HVAC.Supply", "label": "HVAC supply air temperature", "unit": "°C"},
            {"metric": "hvac_return_air_c", "path": "HVAC.Return", "label": "HVAC return air temperature", "unit": "°C"},
            {"metric": "hvac_airflow_m3h", "path": "HVAC.Airflow", "label": "HVAC airflow (fan speed x rated)", "unit": "m³/h"},
            {"metric": "hvac_power_kw", "path": "HVAC.Power", "label": "HVAC electrical power", "unit": "kW"},
            {"metric": "ambient_c", "path": "HVAC.Ambient", "label": "Outdoor air temperature", "unit": "°C"},
            {"metric": "ac_power_kw", "path": "PCS.ACPower", "label": "PCS AC power (+ to grid)", "unit": "kW"},
            {"metric": "pcs_dc_power_kw", "path": "PCS.DCPower", "label": "PCS DC power (+ from battery)", "unit": "kW"},
            {"metric": "pcs_running", "path": "PCS.Running", "label": "PCS running (1) or stopped / tripped (0)", "unit": "code"},
            {"metric": "offgas_ppm", "path": "Safety.OffGas", "label": "Electrolyte off-gas detector", "unit": "ppm"},
            {"metric": "gas_lel_pct", "path": "Safety.LEL", "label": "Flammable gas (H2 / CO)", "unit": "% LEL"},
            {"metric": "insulation_kohm", "path": "Safety.Insulation", "label": "DC insulation resistance to earth", "unit": "kΩ"},
            {"metric": "energy_charged_24h_kwh", "path": "Energy.Charged24h", "label": "AC energy charged, last 24 h", "unit": "kWh"},
            {"metric": "energy_discharged_24h_kwh", "path": "Energy.Discharged24h", "label": "AC energy discharged, last 24 h", "unit": "kWh"},
            {"metric": "aux_energy_24h_kwh", "path": "Energy.Aux24h", "label": "Auxiliary energy (HVAC, BMS), last 24 h", "unit": "kWh"},
            {"metric": "efc_count", "path": "Life.EFC", "label": "Equivalent full cycles since commissioning", "unit": "count"},
            {"metric": "days_in_service", "path": "Life.Days", "label": "Days since commissioning", "unit": "d"},
            {"metric": "life_cell_temp_avg_c", "path": "Life.TAvg", "label": "Mean cell temperature since commissioning", "unit": "°C"},
        ],
    },
    "twin_model": {
        "limits": {
            "offgas_alert_ppm": 10.0, "lel_alert_pct": 10.0, "temp_rate_alert_c_min": 1.0, "cell_temp_alert_c": 50.0,
            "t_spread_alert_c": 8.0, "rest_spread_alert_mv": 30.0, "r_excess_alert_mohm": 0.30, "min_string_current_a": 50.0,
            "hvac_load_alert": 0.90, "cop_ratio_alert": 0.75, "supply_dev_alert_c": 4.0, "soh_residual_alert_pct": -3.0,
            "pcs_loss_ratio_alert": 1.5, "rte_deficit_alert_pct": 3.0,
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "weak_module": {"name": "Weak cell or module (high resistance)", "part": "battery",
                        "symptoms": "cell voltage spread grows with current, one cell runs hotter",
                        "rules": ["BESS_WEAK_CELL_R", "BESS_CELL_T_SPREAD_HIGH"], "default_ramp_min": 1.5},
        "cell_imbalance": {"name": "Cell imbalance (balancing fault, SOC drift)", "part": "bms",
                           "symptoms": "voltage spread at rest grows, usable energy shrinks at both ends",
                           "rules": ["BESS_CELL_IMBALANCE"], "default_ramp_min": 1.5},
        "hvac_degraded": {"name": "HVAC degraded (refrigerant loss, fouled condenser)", "part": "hvac",
                          "symptoms": "COP falls, supply air drifts above the setpoint, cells warmer",
                          "rules": ["BESS_HVAC_COP_LOW", "BESS_HVAC_SUPPLY_HIGH"], "default_ramp_min": 1},
        "capacity_fade_fast": {"name": "Capacity fading faster than the ageing model", "part": "battery",
                               "symptoms": "BMS state of health below the model, augmentation date moves closer",
                               "rules": ["BESS_SOH_BELOW_MODEL", "BESS_AUGMENT_DUE"], "default_ramp_min": 1},
        "thermal_runaway_precursor": {"name": "Thermal runaway precursor (internal short, venting cell)", "part": "safety",
                                      "symptoms": "off-gas detected, hottest cell rising fast, temperature spread grows; the BMS trips the PCS",
                                      "rules": ["BESS_OFFGAS_DETECTED", "BESS_CELL_TEMP_RATE", "BESS_CELL_T_SPREAD_HIGH"], "default_ramp_min": 0.5},
        "pcs_degradation": {"name": "PCS losses up (IGBT, filter, cooling fan)", "part": "pcs",
                            "symptoms": "PCS loss above its curve, round-trip efficiency down",
                            "rules": ["BESS_PCS_LOSS_HIGH", "BESS_RTE_LOW"], "default_ramp_min": 1},
        "insulation_fault": {"name": "DC insulation fault (ground fault)", "part": "battery",
                             "symptoms": "insulation resistance to earth falls below the monitor setting",
                             "rules": ["BESS_INSULATION_LOW"], "default_ramp_min": 1},
    },
    "presentation": {"title": "BESS-3501 battery energy storage container", "dashboard": "BESS_LFP_CONTAINER"},
}

out = HERE / "twin" / "bess-3501.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
