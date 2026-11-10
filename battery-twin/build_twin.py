"""Build twin/bat-1001.twin.json: substation 110 V DC system, EnerSys PowerSafe OPzV 6 OPzV 420 battery (54 cells)
with a thyristor charger, an insulation monitor and a battery monitoring system (cell voltages, temperatures, ohmic values).

Sources (public, read 2026-11-10):
  EnerSys PowerSafe OPzV range summary EMEA-EN-RS-PS-OPzV-0923
    https://www.enersys.com/4ac062/globalassets/documents/product-documentation/powersafe/opzv/emea/en-rs-emea-powersafe-opzv-0923.pdf
    6 OPzV 420: 465 Ah (10 h to 1.80 Vpc @ 20 C), 465 Ah (8 h to 1.75 Vpc @ 25 C), 145 x 206 x 520 mm, 36.5 kg,
    short-circuit current 4043 A, internal resistance 0.51 mOhm; tubular gel VRLA, 20-year design life at 20 C,
    float 2.25 Vpc at 20 C, operating range -10 to +45 C, IEC 60896-21/-22, "Very Long Life" (Eurobat)
  EnerSys PowerSafe OPzV installation, operating and maintenance instructions (en-opzv-om-006)
    https://www.enersys.com/493bb4/globalassets/documents/product-documentation/powersafe/opzv/emea/en-opzv-om-006.pdf
    float voltage vs temperature: -10 C 2.37, 0 C 2.33, 10 C 2.29, 20 C 2.25, 30 C 2.23, 40 C 2.21 Vpc;
    cell float voltages within +-4.5 % of the mean after 6 months; boost 2.33-2.40 Vpc, current <= 4 x I10;
    AC ripple current <= 5 A per 100 Ah C10 in standby; capacity vs temperature (5-12 h): -10 C 0.60, 0 C 0.78,
    10 C 0.90, 20 C 1.00, 30 C 1.05, 40 C 1.07; end-of-discharge 1.80 Vpc for 8-24 h; best life +10 to +30 C
  Charger: 6-pulse thyristor bridge with an LC DC filter, float/boost, +-1 % regulation, as in public substation
    specifications (e.g. ADMIE TD-87 / TD-105, https://www.admie.gr); example product family Benning THYROTRONIC
    (24-220 V DC, float/boost/equalise; https://pdf.directindustry.com/pdf/benning/thyrotronic/12342-376931.html).
  Ohmic thresholds (typical, not EnerSys): +20 % over baseline = investigate (Fluke battery test guide,
    https://www.fluke.com/en-ie/learn/blog/energy-efficiency/recommended-battery-tests), +50 % = act
    (Vertiv/BATTCON, https://www.vertiv.com/48dc60/globalassets/documents/battcon-static-assets/2013/batteries-die-in-thirds.pdf);
    end of life at 80 % capacity (same Vertiv source).
Assumptions (labelled in the twin): 110 V system with 54 cells; standing DC load ~12 A plus trip/close events; required
  autonomy 10 h; float current 0.35 mA/Ah at 2.25 Vpc and 20 C, doubling per 10 K and per +25 mV/cell; ageing doubles
  per 10 K above 20 C (Arrhenius rule of thumb; some guides quote 8 K above 25 C); ohmic value falls ~0.6 %/K;
  intercell connector 0.05 mOhm; charger rating 50 A; insulation monitor (pole-to-earth voltages, insulation resistance).
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
N_CELLS, C10, RI, ISC = 54, 465.0, 0.51, 4043.0


def P(metric, path, label, unit, rng, noise, opc=None):
    return {"metric": metric, "path": path, "label": label, "unit": unit, "range": rng, "noise": noise, "opc": opc}


points = [
    P("dc_bus_voltage_v", "DCBus.Voltage", "DC bus voltage", "V", [0, 160], 0.03, "IEC 61850: ZBAT.Vol / MMDC.Vol"),
    P("battery_voltage_v", "Battery.Voltage", "Battery string voltage", "V", [0, 160], 0.03, "IEC 61850: ZBAT.Vol"),
    P("battery_current_a", "Battery.Current", "Battery current (+ charge, - discharge)", "A", [-500, 500], 0.004, "IEC 61850: ZBAT.Amp"),
    P("load_current_a", "DCBus.LoadCurrent", "DC load current (protection, control, SCADA, comms)", "A", [0, 300], 0.05, "IEC 61850: MMDC.Amp"),
    P("charger_current_a", "Charger.Current", "Charger output current", "A", [0, 120], 0.05, "IEC 61850: ZBTC.Amp"),
    P("charger_ac_on", "Charger.ACSupply", "Charger AC supply (1 on, 0 lost)", "flag", [0, 1], 0, "IEC 61850: ZBTC.ACFail"),
    P("charger_mode", "Charger.Mode", "Charger mode (0 float, 1 boost, 2 off)", "code", [0, 2], 0, "IEC 61850: ZBTC.ChaMod"),
    P("ripple_current_a", "Charger.RippleCurrent", "AC ripple current into the battery (rms)", "A", [0, 100], 0.05, "IEC 61850: ZBTC.RplAmp"),
    P("ripple_voltage_mv", "Charger.RippleVoltage", "Ripple voltage on the DC bus (rms)", "mV", [0, 5000], 3, "IEC 61850: ZBTC.RplVol"),
    P("room_temp_c", "Room.Temperature", "Battery room temperature", "degC", [-10, 60], 0.05, "IEC 61850: MMET.EnvTmp"),
    P("battery_temp_c", "Battery.Temperature", "Battery temperature (pilot cells, mean)", "degC", [-10, 70], 0.03, "IEC 61850: ZBAT.Tmp"),
    P("cell_temp_max_c", "Cells.TemperatureMax", "Hottest cell / connector-side temperature", "degC", [-10, 90], 0.05),
    P("cell_v_mean", "Cells.VoltageMean", "Cell voltage, mean", "V", [0, 3], 0.0005, "BMS"),
    P("cell_v_min", "Cells.VoltageMin", "Cell voltage, lowest", "V", [0, 3], 0.0005, "BMS"),
    P("cell_v_max", "Cells.VoltageMax", "Cell voltage, highest", "V", [0, 3], 0.0005, "BMS"),
    P("cell_v_worst_no", "Cells.WorstVoltageCell", "Cell with the largest voltage deviation", "no.", [1, N_CELLS], 0, "BMS"),
    P("ri_mean_mohm", "Cells.ResistanceMean", "Internal (ohmic) resistance, mean of the cells", "mOhm", [0, 10], 0.002, "BMS ohmic test"),
    P("ri_max_mohm", "Cells.ResistanceMax", "Internal (ohmic) resistance, highest cell", "mOhm", [0, 10], 0.002, "BMS ohmic test"),
    P("ri_max_no", "Cells.ResistanceMaxCell", "Cell with the highest ohmic value", "no.", [1, N_CELLS], 0, "BMS"),
    P("conn_r_max_mohm", "Cells.ConnectionResistanceMax", "Intercell connection resistance, highest", "mOhm", [0, 50], 0.002, "BMS strap test"),
    P("conn_temp_max_c", "Cells.ConnectorTemperatureMax", "Hottest intercell connector (IR sensor)", "degC", [-10, 150], 0.08),
    P("soc_pct", "Battery.StateOfCharge", "State of charge (BMS coulomb count)", "%", [0, 100], 0.03, "IEC 61850: ZBAT.BatSt"),
    P("insulation_kohm", "Earth.InsulationResistance", "DC system insulation resistance to earth", "kOhm", [0, 5000], 1.0, "IMD"),
    P("pos_earth_v", "Earth.PositiveToEarth", "Positive pole to earth", "V", [-160, 160], 0.05, "IMD"),
    P("neg_earth_v", "Earth.NegativeToEarth", "Negative pole to earth", "V", [-160, 160], 0.05, "IMD"),
]

failure_modes = {
    "weak_cell": {"label": "Weak cell (dry-out, high resistance)",
                  "cause": "One cell loses water and active material: its ohmic value climbs well above the string, it floats high and sags first on discharge; the string loses capacity",
                  "detect": ["ri_ratio_max", "cell_dev_max_pct", "ri_max_no"], "action": "Replace the cell (match age/type), then re-baseline the ohmic values", "default_ramp_min": 3},
    "loose_connection": {"label": "Loose intercell connection",
                         "cause": "A connector bolt lost its torque (23-25 Nm for M10): the joint resistance rises, it heats under current and can melt the terminal during a discharge",
                         "detect": ["conn_r_ratio", "conn_temp_max_c"], "action": "Isolate, clean and re-torque the connector to 23-25 Nm; check the terminal for heat damage", "default_ramp_min": 2},
    "thermal_runaway": {"label": "Thermal runaway (VRLA)",
                        "cause": "Heat and float current feed each other: a hot, dried cell takes more current, which makes more heat; the string temperature climbs above the room",
                        "detect": ["float_current_ratio", "battery_temp_rise_k", "battery_current_a"], "action": "Drop to a reduced float voltage or open the battery breaker; ventilate; replace the affected cells", "default_ramp_min": 3},
    "charger_ripple": {"label": "Charger filter failure (high ripple)",
                       "cause": "A failed smoothing capacitor in the thyristor charger's DC filter: AC ripple current flows through the battery and heats it, shortening its life",
                       "detect": ["ripple_per_100ah", "ripple_voltage_mv"], "action": "Repair the charger DC filter (capacitors); verify ripple below 5 A per 100 Ah", "default_ramp_min": 2},
    "ground_fault": {"label": "DC earth fault (positive pole)",
                     "cause": "Damaged cable insulation or moisture in a junction box: the positive pole leaks to earth, the pole-to-earth voltages shift; a second fault could trip a breaker by itself",
                     "detect": ["insulation_kohm", "pole_imbalance_pct"], "action": "Locate the faulty circuit with the insulation monitor's feeder search; repair the insulation", "default_ramp_min": 2},
    "float_setting": {"label": "Float voltage mis-set (no temperature compensation)",
                      "cause": "The charger runs a fixed, too-high float voltage and ignores the battery temperature: the cells are overcharged, dry out and age faster",
                      "detect": ["float_v_residual_mv", "float_current_ratio"], "action": "Restore the charger's temperature-compensated float setting (2.25 Vpc at 20 C)", "default_ramp_min": 1},
    "ventilation_failure": {"label": "Battery room cooling failure",
                            "cause": "The battery room air conditioning stops: room and battery temperature climb past 30 C and every 10 K roughly halves the remaining life",
                            "detect": ["room_temp_c", "battery_temp_c", "ageing_rate_v"], "action": "Restore the room cooling; record the time spent hot against the battery life", "default_ramp_min": 3},
    "capacity_fade": {"label": "End of life (capacity fade)",
                      "cause": "The whole string has aged: ohmic values have risen across all cells, the capacity is near 80 % and the backup time no longer meets the 10 h requirement",
                      "detect": ["ri_ratio_mean", "autonomy_h", "capacity_est_pct"], "action": "Run a capacity test (IEC 60896 / IEEE 1188) and plan the battery replacement", "default_ramp_min": 3},
}

DESIGN = {
    "cell": {"maker": "EnerSys", "type": "PowerSafe OPzV 6 OPzV 420", "technology": "VRLA, tubular positive plate, gel electrolyte",
             "c10_ah": C10, "c8_25c_ah": 465.0, "nominal_v": 2.0, "ri_mohm": RI, "isc_a": ISC, "mass_kg": 36.5,
             "dims_mm": {"length": 145, "width": 206, "height": 520}, "design_life_years_20c": 20,
             "terminal": "M10, 23-25 Nm", "operating_range_c": [-10, 45], "best_range_c": [10, 30]},
    "string": {"cells": N_CELLS, "nominal_v": 2.0 * N_CELLS, "system": "110 V DC (54 cells, assumption)",
               "end_voltage_vpc": 1.80, "racks": "2 racks x 2 tiers x 14 positions (54 used)"},
    "float": {"vpc_20c": 2.25, "table_c": [-10, 0, 10, 20, 30, 40], "table_vpc": [2.37, 2.33, 2.29, 2.25, 2.23, 2.21],
              "cell_tolerance_pct": 4.5, "boost_vpc": [2.33, 2.40], "boost_current_limit_x_i10": 4,
              "float_current_ma_per_ah_20c": 0.35, "float_current_doubling_k": 10.0, "float_current_doubling_mv": 25.0,
              "float_current_note": "float current model assumed (typical VRLA gel), not EnerSys data"},
    "capacity_vs_temp": {"table_c": [-10, 0, 10, 20, 30, 40], "factor_5_12h": [0.60, 0.78, 0.90, 1.00, 1.05, 1.07]},
    "ripple": {"limit_a_per_100ah": 5.0, "limit_a": round(5.0 * C10 / 100, 2)},
    "ohmic": {"baseline_mohm": RI, "temp_coeff_per_k": -0.006, "warn_ratio": 1.2, "act_ratio": 1.5,
              "note": "baseline = EnerSys internal resistance at 20 C; ratios +20 % / +50 % are public field practice, not EnerSys limits; temperature coefficient assumed",
              "capacity_model": "capacity estimate = 1 - 0.65 x (mean ohmic ratio - 1), clipped 0.3-1 (empirical, assumed)"},
    "connection": {"baseline_mohm": 0.05, "alert_ratio": 3.0, "note": "solid copper insulated intercell connectors; baseline assumed"},
    "ageing": {"ref_c": 20.0, "doubling_k": 10.0, "rule": "rule of thumb: life halves per 10 K above 20 C (some guides: 8 K above 25 C)"},
    "load": {"standing_a": 12.0, "required_autonomy_h": 10.0, "note": "protection relays, control, SCADA RTU, telecom; assumed"},
    "charger": {"type": "6-pulse thyristor rectifier with LC DC filter", "rating_a": 50.0, "regulation_pct": 1.0,
                "temperature_compensation": True, "example": "Benning THYROTRONIC family (24-220 V DC); rating assumed"},
    "insulation": {"healthy_kohm": 1500.0, "alert_kohm": 50.0, "imbalance_alert_pct": 30.0,
                   "note": "insulation monitoring device (IMD) with pole-to-earth voltmeters; limits typical, assumed"},
    "demo": {"time_scale": 60, "note": "The plant clock runs 60x real time (one day in 24 min). Each plant night at 02:00 the "
                                       "charger AC supply is lost for 90 plant minutes (a mains dip test), so the battery "
                                       "carries the load and the discharge shows within 90 real seconds. Fault effects are "
                                       "compressed to minutes; Clear all restores the healthy cells."},
}

twin = {
    "$comment": "Single source of truth for the BAT-1001 digital twin: 110 V substation DC system with an EnerSys PowerSafe OPzV "
                "6 OPzV 420 battery (54 cells, 465 Ah C10), a thyristor charger and a battery monitoring system.",
    "twin": {"id": "urn:maximo:twin:dcbattery:BAT-1001", "version": "1.0.0",
             "kind": "Substation DC system: stationary VRLA battery, charger, insulation monitor, battery monitoring system",
             "standards": {
                 "performance": f"EnerSys 6 OPzV 420: C10 {C10:.0f} Ah to 1.80 Vpc at 20 C, Ri {RI} mOhm, Isc {ISC:.0f} A, float 2.25 Vpc at 20 C",
                 "operation": "EnerSys OPzV O&M: float temperature compensation table, +-4.5 % cell tolerance, ripple <= 5 A/100 Ah, capacity factors vs temperature",
                 "monitoring": "Ohmic trending per IEEE 1188 practice (+20 % investigate, +50 % act; typical public values); capacity test per IEC 60896 / IEEE 1188",
                 "information_model": "Points named after IEC 61850 logical nodes ZBAT (battery), ZBTC (charger), MMDC (DC measurement)"}},
    "identification": {"assetnum": "BAT-1001", "description": "Substation DC system 1001 (110 V battery and charger)",
                       "manufacturer": "EnerSys", "model": "PowerSafe OPzV 6 OPzV 420 (54 cells)",
                       "site": "Demo transmission substation", "location": "Substation control building / battery room",
                       "medium": "VRLA gel, 110 V DC, 465 Ah"},
    "design": DESIGN,
    "telemetry": {"event": "battery", "publish_every_s": 5, "device_type": "DC_BATTERY_SYSTEM",
                  "groups": {"DCBus": "DC bus and load", "Battery": "Battery string", "Charger": "Rectifier / charger",
                             "Room": "Battery room", "Cells": "Battery monitoring system (per cell, summarised)",
                             "Earth": "Insulation monitoring device"},
                  "points": points},
    "twin_model": {"limits": {"float_v_residual_alert_mv": 30.0, "float_current_ratio_alert": 3.0, "temp_rise_alert_k": 5.0,
                              "cell_dev_alert_pct": 4.5, "ri_warn_ratio": 1.2, "ri_act_ratio": 1.5, "ri_rule": "warn: worst cell > 1.2x baseline; weak cell: worst cell > 1.5x the string mean", "conn_ratio_alert": 3.0,
                              "conn_temp_rise_alert_k": 10.0, "ripple_alert_a_per_100ah": 5.0, "insulation_alert_kohm": 50.0,
                              "imbalance_alert_pct": 30.0, "room_temp_alert_c": 30.0, "battery_temp_alert_c": 35.0,
                              "ri_mean_alert_ratio": 1.3, "autonomy_alert_h": 10.0, "low_voltage_vpc": 1.85}},
    "failure_modes": failure_modes,
    "presentation": {
        "category": "DC battery system",
        "kpis": [{"metric": "dc_bus_voltage_v", "label": "DC bus", "unit": "V", "decimals": 1},
                 {"metric": "battery_current_a", "label": "Battery current", "unit": "A", "decimals": 2},
                 {"metric": "battery_temp_c", "label": "Battery temperature", "unit": "°C", "decimals": 1},
                 {"metric": "soc_pct", "label": "State of charge", "unit": "%", "decimals": 0}],
        "twin_kpis": [{"metric": "float_v_residual_mv", "label": "Float vs. EnerSys", "unit": "mV/cell", "decimals": 0},
                      {"metric": "ri_ratio_max", "label": "Worst cell ohmic ratio", "unit": "x", "decimals": 2}],
        "compare": [
            {"label": "Float voltage per cell", "measured": "float_vpc", "expected": "float_vpc_expected", "unit": "V", "decimals": 3,
             "basis": "EnerSys OPzV temperature compensation table at the battery temperature (2.25 Vpc at 20 °C)"},
            {"label": "Float current", "measured": "battery_current_a", "expected": "float_current_expected_a", "unit": "A", "decimals": 2,
             "basis": "0.35 mA/Ah × 465 Ah at 2.25 Vpc and 20 °C, ×2 per 10 K and per +25 mV/cell (assumed model)"},
            {"label": "Worst cell ohmic value", "measured": "ri_max_mohm", "expected": "ri_expected_mohm", "unit": "mΩ", "decimals": 3,
             "basis": "EnerSys 0.51 mΩ at 20 °C, −0.6 %/K; +20 % investigate, +50 % act"},
            {"label": "Cell voltage deviation", "measured": "cell_dev_max_pct", "expected": None, "unit": "%", "decimals": 2, "basis": "EnerSys: within ±4.5 % of the mean on float"},
            {"label": "Ripple current", "measured": "ripple_per_100ah", "expected": None, "unit": "A/100 Ah", "decimals": 2, "basis": "EnerSys: ≤ 5 A per 100 Ah C10"},
            {"label": "Backup time", "measured": "autonomy_h", "expected": None, "unit": "h", "decimals": 1, "basis": "SOC × C10 × capacity(T) × capacity estimate / load; required 10 h"},
            {"label": "Insulation to earth", "measured": "insulation_kohm", "expected": None, "unit": "kΩ", "decimals": 0, "basis": "alert < 50 kΩ (typical)"},
        ],
        "trends": [{"metric": "float_v_residual_mv", "label": "Float vs. EnerSys (mV/cell)"}, {"metric": "ri_max_vs_mean", "label": "Worst cell vs. string mean"},
                   {"metric": "float_current_ratio", "label": "Float current ratio"}, {"metric": "autonomy_h", "label": "Backup time (h)"}],
        "design": [
            {"label": "Battery", "value": "EnerSys PowerSafe OPzV 6 OPzV 420 × 54 cells: 465 Ah C10, 0.51 mΩ, 4043 A short circuit, 20-year design life at 20 °C"},
            {"label": "Float", "value": "2.25 Vpc at 20 °C with the EnerSys compensation table (2.37 at −10 °C … 2.21 at 40 °C); ripple ≤ 5 A/100 Ah"},
            {"label": "Assumed", "value": "110 V system (54 cells), 12 A standing load, 10 h autonomy, float-current and ageing models, 50 A thyristor charger"},
            {"label": "Source", "value": "EnerSys OPzV range summary 0923 and O&M manual; 3D built from published cell dimensions, not manufacturer CAD"},
        ],
    },
}

if __name__ == "__main__":
    out = HERE / "twin" / "bat-1001.twin.json"
    out.parent.mkdir(exist_ok=True)
    json.dump(twin, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("written", out)
