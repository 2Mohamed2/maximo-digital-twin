"""Build twin/uv-1601.twin.json: TrojanUVSwiftSC D12 closed-vessel UV reactor (12 LPHO amalgam lamps) for drinking water.

Sources (public, read 2026-11-10):
  TrojanUVSwiftSC brochure (Trojan Technologies, 0518), https://trojanuv.com/resources//Products/TrojanUVSwiftSC/TrojanUVSwiftSC_Brochure.pdf
    D12: 12 high-output amalgam (LPHO) lamps in quartz sleeves, DVGW bioassay-validated dose 40 mJ/cm2 (EPA validation
    up to 186 mJ/cm2 for 4-log virus on D-series), nominal UVT range 70-98 % (D-series), water 1-40 C, 316L chamber
    10 bar, DN300 (12") flanges, dry 195 kg / wet 390 kg, 2 UV sensors per DVGW (1 per 10 lamps) / 1 per EPA,
    electronic variable-output ballasts 60-100 % (dose pacing), automatic fluorocarbon sleeve wiper, family flow range
    4.5-2,525 m3/h, DVGW-approved photodiode UV sensor, Modbus/PROFINET to SCADA.
    (Trojan's 2025 edition (0925) of the brochure lists the D12 chamber at 230 kg dry / 413 kg wet; the 0518 values are used.)
  US EPA Ultraviolet Disinfection Guidance Manual for the LT2ESWTR (EPA 815-R-06-007, Nov 2006),
    https://www.epa.gov/system/files/documents/2022-10/ultraviolet-disinfection-guidance-manual-2006.pdf
    Table 1.4 UV dose requirements (40 CFR 141.720(d)(1)); Table 2.1 LPHO lamps 8,000-12,000 h, 1.5-10 W/cm, 254 nm;
    1.4.4 off-specification rule (>= 95 % of the monthly volume treated within validated conditions);
    Table 4.2 typical alarms (lamp age, low validated dose, low UV intensity, low UVT, high flow, wiper failure,
    lamp/ballast failure, low level, high temperature); fouling/aging factor definition.
  Amalgam lamp ageing: "in excess of 16,000 hours with only a 20% degradation" (Ushio low-pressure amalgam specification,
    https://www.ushio.com/files/specifications/low-pressure-uv-amalgam.pdf). The twin puts the 0.80 end-of-lamp-life
    factor at 12,000 h (the upper LPHO life in UVDGM Table 2.1): conservative, labelled as an assumption.
Assumptions (not published per model, labelled in the twin): lamp power 320 W; validated flow limit 800 m3/h and
  minimum UVT 80 % for this reactor; design point 650 m3/h at 94 % UVT; fouling factor 0.90; sensor geometry
  (3 cm water layer to the sensor window, 6 cm mean water layer); calculated-dose equation form and its constant;
  dose-pacing setpoint 46 mJ/cm2 (40 x 1.15); wipe every 4 h; trip at 55 C reactor temperature.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).parent
N_LAMPS, LAMP_KW = 12, 0.32
LIFE_H, EOL = 12000.0, 0.80
FOUL = 0.90
LS_CM, W_CM = 3.0, 6.0
S0 = 250.0                         # W/m2 at the sensor: new lamps, clean sleeves, 100 % power, UVT 100 % (assumed)
Q_DESIGN, UVT_DESIGN, REQ = 650.0, 94.0, 40.0


def g_factor(uvt):
    """reactor-average / sensor attenuation (Beer-Lambert over the mean water layer vs. the sensor water layer)."""
    uva = max(-math.log10(uvt / 100), 1e-4)
    phi = (1 - 10 ** (-uva * W_CM)) / (uva * W_CM * math.log(10))
    return phi / 10 ** (-uva * LS_CM)


TS_D = (UVT_DESIGN / 100) ** LS_CM
KC = REQ * Q_DESIGN / (EOL * FOUL * TS_D * g_factor(UVT_DESIGN))     # RED = KC * (S/S0) * G(UVA) / Q


def P(metric, path, label, unit, rng, noise, opc=None):
    return {"metric": metric, "path": path, "label": label, "unit": unit, "range": rng, "noise": noise, "opc": opc}


points = [
    P("flow_m3h", "Process.Flow", "Flow through the reactor (dedicated flow meter)", "m3/h", [0, 1500], 1.0, "Modbus: flow input (AI)"),
    P("uvt_pct", "Process.UVT", "UV transmittance at 254 nm, 1 cm (online UVT analyser)", "%", [40, 100], 0.05, "Modbus: UVT input (AI)"),
    P("water_temp_c", "Process.WaterTemp", "Water temperature at the inlet", "degC", [0, 45], 0.03),
    P("reactor_temp_c", "Reactor.Temperature", "Reactor water temperature (top of chamber)", "degC", [0, 95], 0.05, "Modbus: chamber temperature"),
    P("uv_intensity_1_wm2", "Reactor.UVSensor1", "UV intensity, sensor 1 (lamps 1-6)", "W/m2", [0, 400], 0.3, "Modbus: UV sensor 1"),
    P("uv_intensity_2_wm2", "Reactor.UVSensor2", "UV intensity, sensor 2 (lamps 7-12)", "W/m2", [0, 400], 0.3, "Modbus: UV sensor 2"),
    P("ballast_power_pct", "Ballast.PowerSetpoint", "Ballast power setpoint (dose pacing, 60-100 %)", "%", [0, 100], 0, "Modbus: power level"),
    P("lamp_power_kw", "Ballast.LampPower", "Lamp power drawn (all ballasts)", "kW", [0, 6], 0.004),
    P("lamps_on", "Lamps.On", "Lamps lit (of 12)", "count", [0, 12], 0, "Modbus: lamp status"),
    P("lamp_hours", "Lamps.Hours", "Lamp elapsed time", "h", [0, 30000], 0, "Modbus: lamp hours"),
    P("ballast_temp_c", "Ballast.Temperature", "Ballast heat-sink temperature (control panel)", "degC", [0, 100], 0.1),
    P("wiper_status", "Wiper.Status", "Sleeve wiper: 0 idle, 1 wiping, 2 fault", "code", [0, 2], 0, "Modbus: wiper status"),
    P("wiper_cycles", "Wiper.Cycles", "Wiper cycles (counter)", "count", [0, 1e9], 0),
    P("reactor_status", "Controller.Status", "Reactor: 0 disinfecting, 1 alarm, 2 shut down (high temperature)", "code", [0, 2], 0, "Modbus: system status"),
    P("volume_month_m3", "Totaliser.MonthVolume", "Water treated this month", "m3", [0, 1e9], 0),
    P("offspec_month_m3", "Totaliser.MonthOffSpecVolume", "Water treated off-specification this month (controller)", "m3", [0, 1e9], 0),
]

failure_modes = {
    "lamp_failure": {"label": "Lamp / ballast failure (lamps out)", "cause": "A lamp or its ballast fails: the lamp group loses output, the sensor watching it drops and the controller turns the other lamps up (dose pacing). Two lamps out at full severity",
                     "detect": ["lamps_on", "uv_intensity_1_wm2", "dose_calc_mjcm2"], "action": "Replace the lamp (and ballast if it is the cause); check the sleeve is not cracked", "default_ramp_min": 2},
    "lamp_end_of_life": {"label": "Lamps past end of life", "cause": "Lamp hours run past the validated 12,000 h: output falls below the end-of-lamp-life factor the dose was validated with",
                         "detect": ["lamp_hours", "age_factor", "dose_calc_mjcm2"], "action": "Replace all 12 lamps; reset the lamp-hour counter", "default_ramp_min": 2},
    "sleeve_fouling": {"label": "Sleeve fouling (wiper failure)", "cause": "The wiper drive stalls; hardness and iron/manganese deposit on the warm quartz sleeves: less UV reaches the water at the same lamp power and UVT",
                       "detect": ["intensity_ratio", "wiper_status", "dose_calc_mjcm2"], "action": "Repair the wiper drive; clean the sleeves chemically; check feed hardness / Fe / Mn", "default_ramp_min": 3},
    "uvt_drop": {"label": "Feed UVT drop (water quality)", "cause": "Raw water changes (rain, algae, humic matter): the water absorbs more UV. Intensity falls but exactly as the UVT explains - the reactor is fine, the water is not",
                 "detect": ["uvt_pct", "dose_calc_mjcm2", "intensity_ratio"], "action": "Check the upstream treatment (coagulation, filtration); the reactor runs at full power; consider reducing flow", "default_ramp_min": 3},
    "sensor_drift": {"label": "UV sensor drift", "cause": "Sensor 1 window or photodiode ages: it reads low while sensor 2 and the twin's expectation do not - the controller wastes power pacing up",
                     "detect": ["sensor_ratio", "uv_intensity_1_wm2"], "action": "Check sensor 1 against the reference sensor; clean the window or replace and recalibrate", "default_ramp_min": 3},
    "ballast_fault": {"label": "Ballast / power supply fault", "cause": "A ballast overheats and derates: the lamps draw less power than the controller commands, and the heat-sink runs hot",
                      "detect": ["ballast_dev_pct", "ballast_temp_c", "lamp_power_kw"], "action": "Check the control panel cooling and the ballast; replace the ballast board", "default_ramp_min": 2},
    "high_flow": {"label": "Flow above the validated range", "cause": "Another reactor trips or demand jumps: this reactor carries more than its validated flow, residence time and dose fall",
                  "detect": ["flow_m3h", "dose_calc_mjcm2"], "action": "Bring a standby reactor on line or throttle the flow; count the off-specification volume", "default_ramp_min": 2},
    "no_flow_overheat": {"label": "No flow, lamps on (overheating)", "cause": "An isolation valve closes while the lamps stay on: the trapped water heats up until the high-temperature trip shuts the lamps down (risk to sleeves and water hammer on restart)",
                         "detect": ["flow_m3h", "reactor_temp_c", "reactor_status"], "action": "Interlock the lamps with the flow; let the reactor cool before restart; vent and refill slowly", "default_ramp_min": 1},
}

DOSE_TABLE = {"dose_mjcm2": {"crypto": [0, 1.6, 2.5, 3.9, 5.8, 8.5, 12, 15, 22],
                             "giardia": [0, 1.5, 2.1, 3.0, 5.2, 7.7, 11, 15, 22],
                             "virus": [0, 39, 58, 79, 100, 121, 143, 163, 186]},
              "log": [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
              "source": "US EPA UVDGM Table 1.4 / 40 CFR 141.720(d)(1); log credit read between the table points, capped at 4"}

twin = {
    "$comment": "Single source of truth for the UV-1601 digital twin: TrojanUVSwiftSC D12 closed-vessel UV reactor with 12 LPHO amalgam lamps "
                "for drinking-water disinfection. Reactor data from the Trojan brochure; dose requirements, lamp data and alarms from the US EPA UVDGM.",
    "twin": {"id": "urn:maximo:twin:uvreactor:UV-1601", "version": "1.0.0",
             "kind": "Closed-vessel UV disinfection reactor (drinking water) with UV sensors, UVT analyser and automatic wiper",
             "standards": {
                 "performance": "TrojanUVSwiftSC D12: 12 LPHO amalgam lamps, DVGW-validated 40 mJ/cm2, UVT 70-98 %, 1-40 C, 10 bar, DN300, "
                                "2 UV sensors, variable ballasts 60-100 %, automatic wiper",
                 "dose": "Calculated-dose approach (US EPA UVDGM): RED = K (S/S0) G(UVA) / Q with the sensor intensity S, UV absorbance UVA "
                         "and flow Q; equation form and constant are this twin's calibration, not Trojan's validation equation",
                 "credit": "Log inactivation from US EPA UVDGM Table 1.4 (40 CFR 141.720(d)(1)); off-specification rule: >= 95 % of the monthly volume "
                           "within validated conditions (40 CFR 141.720(d)(3))",
                 "information_model": "Points named after the controller's Modbus / PROFINET I/O (UV intensity, lamp status, power level, wiper)"}},
    "identification": {"assetnum": "UV-1601", "description": "UV disinfection reactor 1601 (treated water, train 1)",
                       "manufacturer": "Trojan Technologies", "model": "TrojanUVSwiftSC D12",
                       "site": "BEDFORD", "location": "UV building / train 1, after the filters",
                       "medium": "Filtered drinking water, 1-40 C"},
    "design": {
        "reactor": {"model": "TrojanUVSwiftSC D12", "lamps": N_LAMPS, "lamp_type": "low-pressure high-output (LPHO) amalgam, 254 nm",
                    "lamp_kw": LAMP_KW, "lamp_kw_note": "320 W per lamp assumed (UVDGM Table 2.1: LPHO 1.5-10 W/cm)",
                    "flange": "DN300 (12 in)", "material": "316L stainless steel", "max_pressure_bar": 10,
                    "mass_dry_kg": 195, "mass_wet_kg": 390, "mass_note": "brochure 0518; the 2025 edition (0925) lists 230 / 413 kg", "water_volume_m3": 0.19, "uv_sensors": 2, "sensor_groups": [[1, 6], [7, 12]],
                    "wiper": "automatic, fluorocarbon wipers, motor-driven", "ballast": "electronic, variable output 60-100 %",
                    "dimensions_cm": {"A": 173, "B": 150, "D": 35, "E": 30, "F": 178}, "dimensions_note": "Trojan drawing letters A-F for D12; used for the 3D proportions"},
        "validation": {"required_dose_mjcm2": REQ, "basis": "DVGW W 294 bioassay (Trojan, D-series)", "uvt_range_pct": [70, 98],
                       "validated_flow_max_m3h": 800, "validated_uvt_min_pct": 80, "water_temp_c": [1, 40],
                       "assumed": "flow limit 800 m3/h and minimum UVT 80 % for this unit are assumptions (Trojan publishes the family range only)"},
        "dose_model": {"S0_wm2": S0, "Ls_cm": LS_CM, "w_cm": W_CM, "Kc": round(KC, 3), "design_flow_m3h": Q_DESIGN, "design_uvt_pct": UVT_DESIGN,
                       "eol_factor": EOL, "fouling_factor": FOUL,
                       "note": "Kc set so that the design flow at 94 % UVT gets 40 mJ/cm2 at the end-of-lamp-life and fouling factors (0.80 x 0.90)"},
        "lamp_ageing": {"life_h": LIFE_H, "eol_factor": EOL, "law": "linear output loss to 0.80 at 12,000 h", "replace_at_h": 11000,
                        "basis": "UVDGM Table 2.1 LPHO 8,000-12,000 h; Ushio amalgam lamps: 20 % degradation over > 16,000 h. 0.80 at 12,000 h is this twin's (conservative) assumption"},
        "clean_sleeve_factor": 0.97, "wipe_every_h": 4,
        "dose_pacing": {"setpoint_mjcm2": round(REQ * 1.15, 1), "min_pct": 60, "max_pct": 100, "note": "40 mJ/cm2 x 1.15 margin (assumed)"},
        "thermal": {"trip_c": 55, "alert_c": 45},
        "credit_table": DOSE_TABLE,
        "demo": {"time_scale": 60, "note": "The plant clock runs 60x real time: lamp hours advance one hour per real minute (the lamps are "
                                           "replaced at 11,000 h automatically), a month of volume counters is 12 real hours, and the "
                                           "trapped water heats to the trip in a few minutes when the flow stops."},
    },
    "telemetry": {"event": "uv", "publish_every_s": 5, "device_type": "UV_DISINFECTION",
                  "groups": {"Process": "Flow and water quality", "Reactor": "Chamber and UV sensors", "Ballast": "Ballasts and lamp power",
                             "Lamps": "Lamp status", "Wiper": "Sleeve wiper", "Controller": "Reactor controller", "Totaliser": "Monthly volumes"},
                  "points": points},
    "twin_model": {"limits": {"intensity_ratio_alert": 0.85, "sensor_ratio_tol": 0.10, "ballast_dev_alert_pct": -10, "ballast_temp_alert_c": 60,
                              "reactor_temp_alert_c": 45, "no_flow_m3h": 25, "offspec_month_alert_pct": 5.0}},
    "failure_modes": failure_modes,
    "presentation": {
        "category": "UV disinfection",
        "kpis": [{"metric": "flow_m3h", "label": "Flow", "unit": "m³/h", "decimals": 0},
                 {"metric": "uvt_pct", "label": "UVT", "unit": "%", "decimals": 1},
                 {"metric": "ballast_power_pct", "label": "Power", "unit": "%", "decimals": 0},
                 {"metric": "lamps_on", "label": "Lamps", "unit": "of 12", "decimals": 0}],
        "twin_kpis": [{"metric": "dose_calc_mjcm2", "label": "UV dose", "unit": "mJ/cm²", "decimals": 1},
                      {"metric": "intensity_ratio", "label": "Intensity vs. twin", "unit": "x", "decimals": 2}],
        "compare": [
            {"label": "UV dose (validated, from sensors)", "measured": "dose_calc_mjcm2", "expected": "dose_expected_mjcm2", "unit": "mJ/cm²", "decimals": 1,
             "basis": "measured: lower sensor, UVT, flow; expected: lamp age and power, clean sleeves"},
            {"label": "UV intensity (mean of 2 sensors)", "measured": "intensity_mean_wm2", "expected": "intensity_expected_wm2", "unit": "W/m²", "decimals": 1,
             "basis": "S0 250 W/m² × power × age factor × clean sleeve 0.97 × UVT³ (3 cm water)"},
            {"label": "Lamp power", "measured": "lamp_power_kw", "expected": "lamp_power_expected_kw", "unit": "kW", "decimals": 2,
             "basis": "12 × 0.32 kW × setpoint × lamps lit"},
            {"label": "Reactor temperature", "measured": "reactor_temp_c", "expected": "reactor_temp_expected_c", "unit": "°C", "decimals": 1,
             "basis": "inlet + lamp heat / (1.163 kWh/m³K × flow)"},
            {"label": "Log credit Cryptosporidium", "measured": "log_crypto", "expected": None, "unit": "log", "decimals": 2, "basis": "UVDGM Table 1.4"},
            {"label": "Log credit virus", "measured": "log_virus", "expected": None, "unit": "log", "decimals": 2, "basis": "UVDGM Table 1.4 (186 mJ/cm² = 4 log)"},
            {"label": "Off-spec volume this month", "measured": "offspec_month_pct", "expected": None, "unit": "%", "decimals": 2, "basis": "≤ 5 % (95 % rule)"},
        ],
        "trends": [{"metric": "dose_calc_mjcm2", "label": "UV dose (mJ/cm²)"}, {"metric": "intensity_ratio", "label": "Intensity vs. twin"},
                   {"metric": "sensor_ratio", "label": "Sensor 1 / sensor 2"}, {"metric": "offspec_month_pct", "label": "Off-spec volume %"}],
        "design": [
            {"label": "Reactor", "value": "TrojanUVSwiftSC D12: 12 LPHO amalgam lamps, DVGW 40 mJ/cm², UVT 70-98 %, DN300, 316L, 10 bar"},
            {"label": "Assumed", "value": "320 W per lamp, max 800 m³/h, min UVT 80 %, design 650 m³/h at 94 %, fouling 0.90, EOLL 0.80"},
            {"label": "Credit", "value": "US EPA UVDGM Table 1.4: 12 mJ/cm² = 3-log Cryptosporidium; 95 % monthly volume rule"},
            {"label": "Source", "value": "TrojanUVSwiftSC brochure; US EPA UVDGM 2006; 3D built from Trojan's published dimensions, not manufacturer CAD"},
        ],
    },
}

if __name__ == "__main__":
    out = HERE / "twin" / "uv-1601.twin.json"
    out.parent.mkdir(exist_ok=True)
    json.dump(twin, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("written", out, "Kc", round(KC, 2))
