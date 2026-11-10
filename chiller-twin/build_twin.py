"""Generate twin/ch-201.twin.json from the BITZER data in data/ (re-runnable)."""
import json
import math
from pathlib import Path

HERE = Path(__file__).parent
fit = json.load(open(HERE / "data" / "bitzer_csh8583_en12900_fit.json"))
sat = json.load(open(HERE / "data" / "r134a_sat.json"))
cpw = 4.19 * 998 / 3600   # kW per (m3/h * K) for water

# evaporator design (BITZER SQD2507207-11-6037): 280 kW, 12 -> 7 C, 48.06 m3/h, to 3.06 C
lm_e = ((12 - 3.06) - (7 - 3.06)) / math.log((12 - 3.06) / (7 - 3.06))
UAe = 280 / lm_e
# condenser design (BITZER K2923T 2-pass): 344 kW at tc 40 C, cw 30 -> 35.2 C, 57.5 m3/h
lm_c = ((40 - 30) - (40 - 35.2)) / math.log((40 - 30) / (40 - 35.2))
UAc = 344 / lm_c


def P(m, path, label, unit, lo, hi, noise, tag):
    return {"metric": m, "path": path, "label": label, "unit": unit, "range": [lo, hi], "noise": noise, "opc": tag}


tw = {
    "$comment": "Single source of truth for the CH-201 digital twin: water-cooled screw chiller built from BITZER components. "
                "Performance from BITZER SOFTWARE v7.2.1.1 (EN 12900) and BITZER heat-exchanger selections.",
    "twin": {
        "id": "urn:maximo:twin:chiller:CH-201", "version": "1.0.0",
        "kind": "Water-cooled screw chiller (R134a): compressor, condenser, evaporator",
        "standards": {
            "performance": "Compressor: BITZER SOFTWARE v7.2.1.1 calculations to EN 12900 (10 K superheat, 0 K subcooling), "
                           "fitted to the EN 12900 10-coefficient polynomial (max deviation 0.2 % capacity, 0.1 % power)",
            "information_model": "Chiller points named after BACnet chiller objects with Project Haystack tags",
            "rating": "Efficiency as COP and kW/ton (AHRI 550/590 metrics); 1 ton of refrigeration = 3.517 kW",
            "heat_exchangers": "Evaporator BITZER SQD2507207-11-6037 and condenser BITZER K2923T 2-pass from BITZER SOFTWARE "
                               "selections; fouling as series resistance (1/U = 1/U_clean + Rf)",
            "refrigerant": "R134a saturation from standard property tables (Antoine fit, max error 0.08 %)"}},
    "identification": {
        "assetnum": "CH-201", "description": "Water-cooled screw chiller 201 (district cooling)",
        "manufacturer": "BITZER", "model": "CSH8583-125Y + K2923T + SQD2507207",
        "site": "Demo district cooling plant", "location": "Chiller hall / CH-201",
        "medium": "Chilled water 12/7 C, condenser water 30/35 C, refrigerant R134a"},
    "design": {
        "refrigerant": "R134a", "r134a_sat": sat,
        "compressor": {
            "model": "BITZER CSH8583-125Y-40P",
            "type": "Semi-hermetic compact screw, slide-valve capacity control 25-100 % (stepless)",
            "displacement_m3h": 470, "max_power_kw": 120.0, "max_current_a": 196.0, "rated_voltage_v": 400,
            "oil_charge_dm3": 18.0, "weight_kg": 860,
            "design_point": {"to": 3, "tc": 40, "Q_kW": 280, "P_kW": 63.8, "I_A": 113.5, "m_kgh": 6610, "tdis_C": 61.9, "COP": 4.38},
            "en12900": {k: fit[k] for k in ["Q_kW", "P_kW", "I_A", "m_kgh", "tdis_C"]},
            "en12900_form": fit["form"], "validity": fit["validity"],
            "part_load_power": {"$comment": "Slide-valve screw at part load: P/P100 = a + (1-a)*slide. a = 0.30 is a typical "
                                            "slide-valve value (an assumption, labelled as such)", "a": 0.30}},
        "evaporator": {
            "model": "BITZER SQD2507207-11-6037 (dry expansion, water on shell side)", "design_kW": 280,
            "chw_in_C": 12, "chw_out_C": 7, "chw_flow_m3h": 48.06, "to_C": 3.06, "pressure_drop_kPa": 42.4,
            "UA_kW_K": round(UAe, 2), "U_clean_kW_m2K": 2.0, "Rf_design_m2K_W": 0.000018},
        "condenser": {
            "model": "BITZER K2923T 2-pass shell and tube", "design_kW": 344, "cw_in_C": 30, "cw_out_C": 35.2,
            "cw_flow_m3h": 57.5, "tc_C": 40, "pressure_drop_bar": 0.36, "UA_kW_K": round(UAc, 2), "U_clean_kW_m2K": 2.5,
            "Rf_design_m2K_W": 0.00004, "receiver_dm3": 67.0, "max_charge_R134a_kg": 73.9, "weight_kg": 221},
        "water_cp_kW_per_m3h_K": round(cpw, 4),
        "chw_setpoint_C": 7.0, "design_superheat_K": 5.0, "design_subcooling_K": 4.0, "ambient_C": 35.0},
    "telemetry": {
        "event": "chiller", "publish_every_s": 5, "device_type": "CHILLER_SCREW",
        "groups": {"Evaporator": "Evaporator / chilled water", "Condenser": "Condenser / condenser water",
                   "Compressor": "Compressor and oil", "Electrical": "Motor and supply", "Plant": "Plant and state"},
        "points": [
            P("chw_in_temp_c", "Evaporator.EnteringWaterTemp", "Chilled water entering", "degC", 0, 30, 0.03, "haystack: entering chilled water temp sensor"),
            P("chw_out_temp_c", "Evaporator.LeavingWaterTemp", "Chilled water leaving (supply)", "degC", 0, 30, 0.03, "haystack: leaving chilled water temp sensor"),
            P("chw_flow_m3h", "Evaporator.WaterFlow", "Chilled water flow", "m3/h", 0, 100, 0.3, "haystack: chilled water flow sensor"),
            P("evap_pressure_bar", "Evaporator.RefrigerantPressure", "Evaporating pressure", "bar(a)", 0, 10, 0.005, "BACnet chiller: evaporator refrigerant pressure"),
            P("evap_sat_temp_c", "Evaporator.SaturatedTemp", "Evaporating temperature (saturated)", "degC", -20, 30, 0.03, "BACnet chiller: evaporator saturated temperature"),
            P("suction_temp_c", "Evaporator.SuctionTemp", "Suction gas temperature", "degC", -20, 40, 0.05, "suction temperature"),
            P("superheat_k", "Evaporator.Superheat", "Suction superheat", "K", 0, 40, 0.05, "superheat"),
            P("cw_in_temp_c", "Condenser.EnteringWaterTemp", "Condenser water entering", "degC", 0, 50, 0.03, "haystack: entering condenser water temp sensor"),
            P("cw_out_temp_c", "Condenser.LeavingWaterTemp", "Condenser water leaving", "degC", 0, 60, 0.03, "haystack: leaving condenser water temp sensor"),
            P("cw_flow_m3h", "Condenser.WaterFlow", "Condenser water flow", "m3/h", 0, 120, 0.3, "haystack: condenser water flow sensor"),
            P("cond_pressure_bar", "Condenser.RefrigerantPressure", "Condensing pressure", "bar(a)", 0, 30, 0.01, "BACnet chiller: condenser refrigerant pressure"),
            P("cond_sat_temp_c", "Condenser.SaturatedTemp", "Condensing temperature (saturated)", "degC", 0, 80, 0.03, "BACnet chiller: condenser saturated temperature"),
            P("liquid_temp_c", "Condenser.LiquidTemp", "Liquid line temperature", "degC", 0, 80, 0.05, "liquid temperature"),
            P("subcooling_k", "Condenser.Subcooling", "Liquid subcooling", "K", 0, 30, 0.05, "subcooling"),
            P("slide_pct", "Compressor.SlideValve", "Slide valve (capacity)", "%", 0, 100, 0.2, "BACnet chiller: percent load"),
            P("discharge_temp_c", "Compressor.DischargeTemp", "Discharge gas temperature", "degC", 0, 150, 0.1, "discharge temperature"),
            P("oil_temp_c", "Compressor.OilTemp", "Oil temperature (PTC sensor)", "degC", 0, 130, 0.1, "oil temperature"),
            P("oil_filter_dp_bar", "Compressor.OilFilterDp", "Oil filter pressure drop", "bar", 0, 5, 0.005, "oil filter differential pressure"),
            P("oil_level_pct", "Compressor.OilLevel", "Oil level (OLC-D1)", "%", 0, 100, 0.2, "oil level"),
            P("vib_mm_s", "Compressor.Vibration", "Compressor vibration RMS", "mm/s", 0, 30, 0.03, "vibration"),
            P("power_kw", "Electrical.Power", "Compressor power input", "kW", 0, 160, 0.15, "BACnet chiller: power"),
            P("current_a", "Electrical.Current", "Motor current", "A", 0, 260, 0.3, "BACnet chiller: current"),
            P("current_imbalance_pct", "Electrical.CurrentImbalance", "Phase current imbalance", "%", 0, 30, 0.05, None),
            P("voltage_v", "Electrical.Voltage", "Supply voltage", "V", 0, 450, 0.5, None),
            P("winding_temp_c", "Electrical.WindingTemp", "Motor winding temperature (SE-E4 PTC)", "degC", 0, 180, 0.1, None),
            P("cooling_kw", "Plant.CoolingCapacity", "Cooling delivered", "kW", 0, 500, 0.6, "BACnet chiller: cooling capacity"),
            P("chw_setpoint_c", "Plant.ChwSetpoint", "Chilled water setpoint", "degC", 0, 20, 0, "setpoint"),
            P("energy_kwh", "Plant.Energy", "Energy total", "kWh", 0, 1e9, 0, None),
            P("run_hours", "Plant.RunHours", "Run hours", "h", 0, 200000, 0, None),
            P("starts", "Plant.Starts", "Compressor starts", "count", 0, 100000, 0, None),
            P("running", "Plant.Running", "Running", "0/1", 0, 1, 0, None),
            P("trip_code", "Plant.TripCode", "Protection trip (0 none, 1 HP, 2 LP, 3 discharge, 4 winding)", "code", 0, 9, 0, None)]},
    "twin_model": {"limits": {
        "cond_fouling_alert_k": 1.5, "evap_fouling_alert_k": 1.2, "superheat_high_k": 12, "subcooling_low_k": 1.5,
        "subcooling_high_k": 7.5, "capacity_dev_alert_pct": -8, "power_dev_alert_pct": 8, "discharge_alert_c": 95,
        "discharge_trip_c": 110, "oil_dp_alert_bar": 1.5, "current_imbalance_alert_pct": 5, "winding_alert_c": 110,
        "winding_trip_c": 130, "vib_alert_mm_s": 7.1, "hp_trip_bar": 16.0, "lp_trip_c": -1.0, "kw_per_ton_alert": 0.95}},
    "failure_modes": {
        "cond_fouling": {"label": "Condenser tube fouling / scaling", "cause": "Scale and biofilm in condenser-water tubes raise thermal resistance",
                         "detect": ["cond_approach_k", "cond_pressure_bar", "power_kw", "discharge_temp_c"],
                         "action": "Clean condenser tubes (brush or chemical); check water treatment", "default_ramp_min": 30},
        "evap_fouling": {"label": "Evaporator fouling", "cause": "Dirt and biofilm in the chilled-water circuit",
                         "detect": ["evap_approach_k", "evap_sat_temp_c", "cooling_kw"],
                         "action": "Clean evaporator; check chilled-water strainers and treatment", "default_ramp_min": 30},
        "low_charge": {"label": "Refrigerant undercharge (leak)", "cause": "A refrigerant leak reduces the charge; the evaporator starves",
                       "detect": ["superheat_k", "subcooling_k", "evap_sat_temp_c", "cooling_kw"],
                       "action": "Leak test, repair and recharge (F-gas record)", "default_ramp_min": 30},
        "noncondensables": {"label": "Non-condensable gases in the circuit", "cause": "Air or nitrogen left after service raises head pressure",
                            "detect": ["subcooling_k", "cond_pressure_bar", "cond_approach_k", "power_kw"],
                            "action": "Purge non-condensables; check the service procedure", "default_ramp_min": 20},
        "compressor_wear": {"label": "Compressor rotor / bearing wear (internal leakage)", "cause": "Rotor tip and bearing wear increase internal leakage",
                            "detect": ["capacity_deviation_pct", "discharge_temp_c", "vib_mm_s"],
                            "action": "Compressor inspection; plan an overhaul", "default_ramp_min": 30},
        "oil_filter": {"label": "Oil filter clogging", "cause": "Oil degradation and debris load the filter",
                       "detect": ["oil_filter_dp_bar", "oil_temp_c"], "action": "Replace the oil filter; oil analysis", "default_ramp_min": 20},
        "motor_winding": {"label": "Motor winding / supply imbalance", "cause": "Insulation degradation or phase imbalance",
                          "detect": ["current_imbalance_pct", "winding_temp_c"], "action": "Insulation test; check supply and terminals", "default_ramp_min": 25},
        "cw_flow_loss": {"label": "Condenser water flow loss", "cause": "Condenser pump or cooling tower fault",
                         "detect": ["cw_flow_m3h", "cond_pressure_bar", "discharge_temp_c"],
                         "action": "Check condenser pump, strainers and valves; protection trips on high pressure", "default_ramp_min": 2}},
    "presentation": {
        "category": "Water-cooled chiller",
        "kpis": [{"metric": "cooling_kw", "label": "Cooling", "unit": "kW", "decimals": 0},
                 {"metric": "power_kw", "label": "Power", "unit": "kW", "decimals": 1},
                 {"metric": "chw_out_temp_c", "label": "CHW supply", "unit": "°C", "decimals": 1},
                 {"metric": "slide_pct", "label": "Slide", "unit": "%", "decimals": 0}],
        "twin_kpis": [{"metric": "kw_per_ton", "label": "kW/ton", "unit": "", "decimals": 3},
                      {"metric": "cond_fouling_k", "label": "Condenser approach vs. clean", "unit": "K", "decimals": 2}],
        "compare": [
            {"label": "Cooling capacity", "measured": "cooling_kw", "expected": "q_expected_kw", "unit": "kW", "decimals": 1, "basis": "BITZER EN 12900 polynomial at measured to/tc and slide"},
            {"label": "Compressor power", "measured": "power_kw", "expected": "p_expected_kw", "unit": "kW", "decimals": 1, "basis": "BITZER EN 12900 polynomial, slide-valve part load"},
            {"label": "Condenser approach", "measured": "cond_approach_k", "expected": "cond_approach_expected_k", "unit": "K", "decimals": 2, "basis": "BITZER K2923T clean UA at design water flow"},
            {"label": "Evaporator approach", "measured": "evap_approach_k", "expected": "evap_approach_expected_k", "unit": "K", "decimals": 2, "basis": "BITZER SQD evaporator clean UA"},
            {"label": "COP", "measured": "cop", "expected": "cop_expected", "unit": "", "decimals": 2, "basis": "Cooling / power"},
            {"label": "kW per ton", "measured": "kw_per_ton", "expected": None, "unit": "kW/TR", "decimals": 3, "basis": "Power / (cooling / 3.517)"}],
        "trends": [{"metric": "cond_fouling_k", "label": "Condenser fouling K"}, {"metric": "capacity_deviation_pct", "label": "Capacity deviation %"},
                   {"metric": "kw_per_ton", "label": "kW/ton"}, {"metric": "superheat_k", "label": "Superheat K"}],
        "design": [{"label": "Compressor", "value": "BITZER CSH8583-125Y-40P, 470 m³/h, 120 kW max, slide 25-100 %"},
                   {"label": "Condenser", "value": "BITZER K2923T 2-pass, 344 kW at 40 °C, 57.5 m³/h"},
                   {"label": "Evaporator", "value": "BITZER SQD2507207-11-6037, 280 kW at 3 °C, 48.1 m³/h"},
                   {"label": "Design point", "value": "280 kW cooling, 63.8 kW power, COP 4.38 (3/40 °C)"}]}}

if __name__ == "__main__":
    (HERE / "twin").mkdir(exist_ok=True)
    json.dump(tw, open(HERE / "twin" / "ch-201.twin.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("UAe %.2f kW/K, UAc %.2f kW/K, %d points" % (UAe, UAc, len(tw["telemetry"]["points"])))
