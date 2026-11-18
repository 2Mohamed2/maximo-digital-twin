"""Write twin/rf-6901.twin.json: the supermarket refrigeration rack twin (RF-6901).

    python build_twin.py

RF-6901 is the medium-temperature (chilled) compressor rack of a supermarket: four Danfoss Maneurop MTZ160-4
reciprocating compressors in parallel on a common suction and discharge, refrigerant R448A (an HFO/HFC blend), an
air-cooled condenser on the roof, a liquid receiver with a level sensor, and the chilled display cases and cold rooms it
feeds. The rack controller stages the compressors to hold the suction pressure. One of the cold rooms (+2 C, chilled
products) is twinned with it: room air, warmest product probe, door contact and the defrost of its evaporator.

Sources and assumptions (every number below is either from a published source or labelled as an assumption in "source"):
  Danfoss application guidelines "Maneurop reciprocating compressors MT/MTZ" AB196386425654en-021701 (2024.02):
    MTZ160-4 displacement 47.25 m3/h at 2900 rpm, 4 cylinders; R448A EN 12900 rating (to -10 C, tc 45 C, SC 0 K, SH 10 K)
    20140 W, 9.87 kW, 17.11 A, COP 2.04; ARI rating (-6.7 / 48.9 C, SH 11.1 K) 21830 W, 10.87 kW; maximum discharge gas
    temperature 135 C; normal suction superheat 5 to 30 K, set expansion superheat at least 8 to 10 K; R448A glide about
    6.1 K and GWP 1387 as stated there.
  The 10-coefficient EN 12900 polynomial for capacity and power: FITTED in data/fit_mtz160.py to a compressor model
    calibrated on the two published points (ASSUMPTION: replace with Danfoss Coolselector2 coefficients).
  Hudson Technologies R-448A pressure temperature chart: bubble and dew pressures and liquid density (fitted in data/).
  F-gas leak-check intervals by tonnes CO2 equivalent (Regulation (EU) 2024/573, Article 5, as tabled by the Irish EPA):
    5 to 50 t: 12 months (24 with a leakage detection system); 50 to 500 t: 6 (12); 500 t and more: 3 (6).
  Rack set points, receiver, charge, cold room, load profile and alarm limits: ASSUMPTIONS of a typical store.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
FIT = json.loads((HERE / "data" / "mtz160_r448a_fit.json").read_text(encoding="utf-8"))
A = "assumption: typical value, replace with the value of your own rack and store"

CHARGE_KG, GWP = 160.0, 1387
CO2E = CHARGE_KG * GWP / 1000
LDS = False
BANDS = [(500, 3, 6), (50, 6, 12), (5, 12, 24)]
MONTHS = next((no if not LDS else yes) for lim, no, yes in BANDS if CO2E >= lim)

twin = {
    "$comment": "RF-6901 supermarket refrigeration rack twin. Expected values in Maximo Monitor from the compressor maker's rating data, the refrigerant's saturation data and the rack design; the rack controller, the cold room controller and the energy meter send only what they measure.",
    "twin": {"id": "RF-6901", "name": "Supermarket refrigeration rack RF-6901", "version": "1.0.0", "folder": "coldroom-twin"},
    "identification": {
        "asset": "RF-6901", "assetnum": "RF-6901", "manufacturer": "Danfoss (compressors); rack by a pack builder",
        "model": "4 × Maneurop MTZ160-4 reciprocating compressors, R448A, medium temperature",
        "description": "Medium-temperature (chilled) refrigeration rack of a supermarket: display cases and cold rooms at -10 °C suction",
        "type": "HFO/HFC compressor rack (multi-compressor pack), R448A, direct expansion, air-cooled condenser, liquid receiver",
        "refrigerant": "R448A (R32/R125/R134a/R1234yf/R1234ze(E) 26/26/21/20/7 %), safety class A1, zeotropic (glide about 6 K)",
        "controller": "Rack controller (pack controller): suction pressure control by compressor staging, condenser fan control, receiver level, alarms",
        "coldroom": "Chilled cold room +2 °C with its own case/room controller: air and product probes, door contact, electric defrost",
    },
    "design": {
        "compressor": {
            "model": "Danfoss Maneurop MTZ160-4", "count": 4, "displacement_m3h": 47.25, "rpm": 2900, "cylinders": 4,
            "rating_en12900": FIT["published"]["en12900"], "rating_ari": FIT["published"]["ari"],
            "t_dis_max_c": 135.0,
            "poly_q_kw": FIT["polynomial"]["q_kw"], "poly_p_kw": FIT["polynomial"]["p_kw"],
            "poly_range": FIT["polynomial"]["range"], "poly_fit_err_pct": FIT["polynomial"]["max_fit_err_pct"],
            "model_check_ari": FIT["model"]["check_ari"],
            "discharge_m": FIT["discharge"]["m"], "discharge_fit_err_k": FIT["discharge"]["max_fit_err_K"],
            "source": "Displacement, rating points and the 135 °C discharge limit: Danfoss application guidelines Maneurop MT/MTZ "
                      "AB196386425654en-021701 (2024.02). Polynomial coefficients (capacity and power per compressor, to and tc at "
                      "dew point, SH 10 K, SC 0 K) and the discharge exponent m: assumption, fitted in data/fit_mtz160.py to a "
                      "compressor model calibrated on the EN 12900 point and checked against the ARI point "
                      f"({FIT['model']['check_ari']['q_dev_pct']:+.2f} % capacity, {FIT['model']['check_ari']['p_dev_pct']:+.2f} % power); "
                      "replace with the maker's EN 12900 coefficients (Danfoss Coolselector2).",
        },
        "refrigerant": {
            "name": "R448A", "gwp": GWP, "glide_k": 6.1, "p_atm_bar": 1.01325,
            "dew": FIT["r448a"]["dew"], "bubble": FIT["r448a"]["bubble"], "rho_liq_poly": FIT["r448a"]["rho_liq_poly"],
            "source": "Saturation: T = B / (A - ln p) - C (p in bar a), fitted to the Hudson Technologies R-448A pressure "
                      "temperature chart (psig + 1.01325 bar); liquid density kg/m3 = quadratic in T (C) fitted to the same "
                      "sheet's density table. GWP 1387 and glide about 6.1 K as stated by Danfoss (AB196386425654en); Regulation "
                      "(EU) 2024/573 gives its own GWP values in its annexes: use the figure your F-gas report requires.",
        },
        "rack": {
            "to_set_c": -10.0, "tc_min_c": 20.0, "sh_normal_k": 14.0, "sc_normal_k": 3.0,
            "source": "Suction set point (dew) for chilled cases and rooms, minimum condensing temperature of the floating head "
                      "pressure control, normal superheat at the rack suction header and liquid subcooling at the receiver "
                      "outlet: " + A + ".",
        },
        "condenser": {
            "approach_design_k": 8.0, "rejection_design_kw": 100.0,
            "source": "Air-cooled condenser: condensing temperature (dew) minus ambient at the design heat rejection, fans at "
                      "full speed: " + A + " (from the condenser selection sheet). The approach is taken proportional to the "
                      "heat rejected.",
        },
        "receiver": {
            "volume_m3": 0.150, "level_normal_pct": 36.0, "level_per_k_amb": -0.15, "level_per_capacity": -4.0,
            "amb_ref_c": 20.0, "capacity_ref": 0.60, "charge_kg": CHARGE_KG,
            "source": "Receiver volume, total system charge and the normal receiver level of a tight system, with its drift "
                      "per K of ambient and per unit of running capacity (more liquid held in the condenser and the liquid "
                      "lines): " + A + ". Learn the three level coefficients from the first weeks after a verified leak "
                      "check and a weighed charge.",
        },
        "fgas": {
            "charge_co2e_t": round(CO2E, 1), "leak_detection_system": LDS, "leak_check_months": MONTHS,
            "leak_check_interval_d": round(MONTHS * 365 / 12, 1), "leak_rate_alert_pct_yr": 10.0,
            "source": "Charge x GWP / 1000 = tonnes CO2 equivalent. Leak-check interval by CO2e band (Regulation (EU) 2024/573 "
                      "Article 5, as tabled by the Irish EPA F-gas FAQ): 5 to 50 t 12 months (24 with a leakage detection "
                      "system), 50 to 500 t 6 months (12), 500 t and more 3 months (6). Leak-rate alert of 10 % of the charge "
                      "per year: " + A + ".",
        },
        "coldroom": {
            "air_set_c": 2.0, "td_design_k": 12.0, "product_limit_c": 5.0, "door_alert_min_h": 10.0, "defrost_max_min": 40.0,
            "source": "Cold room air set point, design temperature difference room air minus rack suction (dew), critical limit "
                      "of the HACCP plan for the chilled products in this room, door-open alert and the defrost safety time: "
                      + A + " (the product limit comes from your own HACCP plan and the national rules for chilled food).",
        },
        "load": {
            "base_kw": 50.0, "open_kw": 6.0, "per_k_amb_kw": 0.6, "open_from_h": 7, "open_to_h": 22,
            "source": "Refrigeration load of the cases and rooms on this rack: night (blinds down), store open, ambient effect: " + A + ".",
        },
        "demo": {"time_scale": 1, "note": "Demo only: the stand-in runs in real time on the visitor's clock (store hours and ambient follow the time of day); failure modes ramp in over about a minute."},
    },
    "telemetry": {
        "event": "coldroom", "publish_every_s": 10, "device_type": "REFRIGERATION_RACK",
        "groups": {"Suction": "Suction header", "Discharge": "Discharge header", "Liquid": "Receiver and liquid line",
                   "Rack": "Compressors and energy meter (means of the last 15 min)", "Ambient": "Outdoor air at the condenser",
                   "ColdRoom": "Twinned cold room (+2 °C)", "Log": "F-gas logbook (published by the gateway from Manage)"},
        "points": [
            {"metric": "suction_pressure_barg", "path": "Suction.Pressure", "label": "Suction header pressure", "unit": "bar g"},
            {"metric": "suction_temp_c", "path": "Suction.Temperature", "label": "Suction gas temperature at the header", "unit": "°C"},
            {"metric": "discharge_pressure_barg", "path": "Discharge.Pressure", "label": "Discharge header pressure", "unit": "bar g"},
            {"metric": "discharge_temp_c", "path": "Discharge.Temperature", "label": "Discharge gas temperature, hottest compressor", "unit": "°C"},
            {"metric": "liquid_temp_c", "path": "Liquid.Temperature", "label": "Liquid temperature after the receiver", "unit": "°C"},
            {"metric": "receiver_level_pct", "path": "Liquid.ReceiverLevel", "label": "Liquid receiver level", "unit": "%"},
            {"metric": "rack_power_kw", "path": "Rack.Power", "label": "Compressor input power (energy meter), mean of 15 min", "unit": "kW"},
            {"metric": "capacity_pct", "path": "Rack.Capacity", "label": "Running capacity (share of the four compressors), mean of 15 min", "unit": "%"},
            {"metric": "compressors_running", "path": "Rack.Running", "label": "Compressors running now", "unit": "count"},
            {"metric": "ambient_temp_c", "path": "Ambient.Temperature", "label": "Ambient air temperature at the condenser", "unit": "°C"},
            {"metric": "room_air_c", "path": "ColdRoom.AirTemp", "label": "Cold room air temperature (return air)", "unit": "°C"},
            {"metric": "product_temp_c", "path": "ColdRoom.ProductTemp", "label": "Warmest product probe in the cold room", "unit": "°C"},
            {"metric": "door_open_min_h", "path": "ColdRoom.DoorOpen", "label": "Door open time, last hour", "unit": "min/h"},
            {"metric": "defrost_end_on_temp", "path": "ColdRoom.DefrostEndOnTemp", "label": "Last defrost ended on coil temperature (1) or on time (0)", "unit": "code"},
            {"metric": "defrost_duration_min", "path": "ColdRoom.DefrostDuration", "label": "Duration of the last defrost", "unit": "min"},
            {"metric": "days_since_topup", "path": "Log.DaysSinceTopUp", "label": "Days since the last refrigerant top-up (charge verified)", "unit": "d"},
            {"metric": "days_since_leak_check", "path": "Log.DaysSinceLeakCheck", "label": "Days since the last F-gas leak check", "unit": "d"},
        ],
    },
    "twin_model": {
        "limits": {
            "power_ratio_alert": 1.10, "discharge_residual_alert_k": 15.0, "superheat_low_k": 5.0, "subcooling_low_k": 1.0,
            "approach_ratio_alert": 1.6, "receiver_low_pct": 10.0, "charge_loss_alert_kg": 8.0, "coil_td_margin_k": 2.5,
            "source": "Alert limits: " + A + ". The 135 °C discharge limit is the maker's (design.compressor), the superheat "
                      "alert sits at the low end of the 5 to 30 K Danfoss quotes as normal at the compressor suction, the product "
                      "limit and the door alert are in design.coldroom, the leak-rate alert and the leak-check interval in design.fgas.",
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "refrigerant_leak": {"name": "Refrigerant leak", "part": "circuit",
                             "symptoms": "receiver level below the level a tight system has at this ambient and load; kg lost and CO2e per year grow; at the end the receiver runs empty and the subcooling disappears",
                             "rules": ["RF_CHARGE_LOSS", "RF_LEAK_RATE_HIGH", "RF_RECEIVER_LOW", "RF_SUBCOOLING_LOW"], "default_ramp_min": 1.5},
        "condenser_fouled": {"name": "Condenser fouled (dirt, leaves, a fan down)", "part": "condenser",
                             "symptoms": "condensing temperature far above ambient for the heat rejected; compressor power up with it",
                             "rules": ["RF_COND_APPROACH_HIGH"], "default_ramp_min": 1},
        "compressor_valve_wear": {"name": "Compressor valve plate leaking (one compressor)", "part": "compressor",
                                  "symptoms": "gas re-compressed inside the compressor: discharge temperature above the expected one, more running capacity for the same load",
                                  "rules": ["RF_DISCHARGE_TEMP_HIGH"], "default_ramp_min": 1},
        "compressor_mechanical": {"name": "Compressor mechanical or motor losses", "part": "compressor",
                                  "symptoms": "electrical power above the maker's polynomial at the measured suction and condensing temperatures",
                                  "rules": ["RF_POWER_HIGH"], "default_ramp_min": 1},
        "superheat_drift": {"name": "Expansion valve superheat drift (flood-back)", "part": "expansion",
                            "symptoms": "superheat at the suction header falls towards zero: liquid can reach the compressors",
                            "rules": ["RF_SUPERHEAT_LOW"], "default_ramp_min": 1},
        "evaporator_icing": {"name": "Cold room evaporator icing (defrost heater failed)", "part": "evaporator",
                             "symptoms": "defrost ends on time instead of on temperature; room air rises, coil temperature difference grows",
                             "rules": ["RF_COIL_TD_HIGH", "RF_DEFROST_ON_TIME"], "default_ramp_min": 1},
        "door_left_open": {"name": "Cold room door left open or heavy traffic", "part": "coldroom",
                           "symptoms": "door open many minutes per hour; warm moist air in, products warm past the HACCP critical limit",
                           "rules": ["RF_DOOR_OPEN_LONG", "RF_PRODUCT_TEMP_HIGH"], "default_ramp_min": 0.5},
    },
    "presentation": {"title": "RF-6901 supermarket refrigeration rack", "dashboard": "REFRIGERATION_RACK"},
}

out = HERE / "twin" / "rf-6901.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out, "CO2e", round(CO2E, 1), "t, leak check every", MONTHS, "months")
