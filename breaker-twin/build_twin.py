"""Build twin/cb-701.twin.json: Siemens Energy 3AP1 FG 145 kV SF6 live-tank circuit breaker, spring-operated.

Sources (public, read 2026-11-10):
  PEHLA type-test report 14253 Bs-1, test object 3AP1FG-145 kV-3150 A-40 kA-50/60 Hz, Siemens AG, ratings assigned by
    the manufacturer: 145 kV, 3150 A, 40 kA (3 s), 108 kA peak, O-0.3 s-CO-3 min-CO, SF6 rated filling pressure 0.70 MPa abs
    at 20 C and minimum functional pressure 0.60 MPa abs at 20 C (interruption and insulation), spring drive, one
    interrupter unit per pole, rated opening time 23 ms, rated closing time 54 ms, 110 V DC trip/close coils,
    400 V AC auxiliaries, -30 .. +40 C, class M2 / C2.
    https://storage.mtender.gov.md/get/2f123df3-715a-4fc2-a719-68d0ea926856-1741698160278
  Siemens environmental product declaration "3AP1 FG 145 kV": weight 1400 kg, SF6 8.1 kg, SF6 leakage 0.2 % p.a.
    https://assets.new.siemens.com/siemens/assets/api/uuid:931fc05b4ae7677cddcc78bfd4fcd84fe5990159/umwelt-en.pdf
  Siemens high-voltage circuit breakers brochure (3AP live tank): 145 kV up to 4000 A / 40 kA, rated break time 3 cycles,
    O-0.3 s-CO-3 min-CO or CO-15 s-CO, stored-energy spring mechanism with 10,000 operating cycles guaranteed,
    maintenance-free for 25 years or 6,000 operating cycles, first inspection after 12 years or 3,000 operating cycles.
    https://assets.new.siemens.com/siemens/assets/api/uuid:c6c2736114efb659835d0207f4aab828f672d783/leistungsschalter-produktbroschuere.pdf
  Contact wear by accumulated interrupted current, sum of I^y per pole against the manufacturer's endurance curve,
    exponent y typically 1.4-2.2 (ABB Relion breaker monitoring manuals, US patents 6466023 / 7123461):
    https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6466023
Assumptions (not published for this product, labelled in the twin): SF6 alarm density 0.62 MPa (lockout taken as the
  0.60 MPa minimum functional pressure), ideal-gas isochore for the 20 C compensation, wear exponent 1.8 and an
  allowance of 20 interruptions at 40 kA per pole, trip coil resistance, opening/closing time sensitivity to the
  control voltage, spring charging time and motor current, pole temperature rise at rated current, heater rating,
  pole spacing and heights of the 3D model.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
UR_KV, IR_A, ISC_KA = 145.0, 3150.0, 40.0
P_FILL, P_MIN, P_ALARM = 0.70, 0.60, 0.62          # MPa abs at 20 C (alarm assumed)
WEAR_Y, WEAR_N = 1.8, 20
ALLOW = WEAR_N * ISC_KA ** WEAR_Y                   # kA^y per pole


def P(metric, path, label, unit, rng, noise, opc=None):
    return {"metric": metric, "path": path, "label": label, "unit": unit, "range": rng, "noise": noise, "opc": opc}


points = [
    P("breaker_position", "Switch.Position", "Breaker position (1 closed, 0 open)", "code", [0, 1], 0, "IEC 61850: XCBR.Pos"),
    P("load_current_l1_a", "Load.CurrentL1", "Line current L1", "A", [0, 5000], 3.0, "IEC 61850: MMXU.A.phsA"),
    P("load_current_l2_a", "Load.CurrentL2", "Line current L2", "A", [0, 5000], 3.0, "IEC 61850: MMXU.A.phsB"),
    P("load_current_l3_a", "Load.CurrentL3", "Line current L3", "A", [0, 5000], 3.0, "IEC 61850: MMXU.A.phsC"),
    P("ambient_temp_c", "Ambient.Temperature", "Ambient temperature", "degC", [-40, 60], 0.1, "IEC 61850: MMET.EnvTmp"),
    P("sf6_pressure_mpa", "Gas.Pressure", "SF6 pressure (absolute, at gas temperature)", "MPa", [0, 1.2], 0.0008, "IEC 61850: SIMG.Pres"),
    P("sf6_gas_temp_c", "Gas.Temperature", "SF6 gas temperature (density sensor)", "degC", [-40, 80], 0.1, "IEC 61850: SIMG.Tmp"),
    P("sf6_density_p20_mpa", "Gas.DensityP20", "SF6 density, temperature-compensated to 20 C (density monitor output)", "MPa", [0, 1.2], 0.0006,
      "IEC 61850: SIMG.Den"),
    P("density_contact", "Gas.MonitorContacts", "Density monitor contacts: 0 normal, 1 alarm, 2 lockout", "code", [0, 2], 0,
      "IEC 61850: SIMG.InsAlm / InsBlk"),
    P("pole_temp_l1_c", "Pole.TemperatureL1", "Pole L1 terminal temperature (wireless sensor)", "degC", [-40, 150], 0.15, "IEC 61850: STMP.Tmp"),
    P("pole_temp_l2_c", "Pole.TemperatureL2", "Pole L2 terminal temperature (wireless sensor)", "degC", [-40, 150], 0.15, "IEC 61850: STMP.Tmp"),
    P("pole_temp_l3_c", "Pole.TemperatureL3", "Pole L3 terminal temperature (wireless sensor)", "degC", [-40, 150], 0.15, "IEC 61850: STMP.Tmp"),
    P("control_voltage_v", "Control.VoltageDC", "Control voltage (DC station battery)", "V", [0, 150], 0.2, "IEC 61850: ZBAT.Vol"),
    P("last_open_time_ms", "Mechanism.OpenTime", "Last opening time (trip command to contact separation)", "ms", [0, 200], 0.15,
      "IEC 61850: SCBR.OpTmOpn"),
    P("last_close_time_ms", "Mechanism.CloseTime", "Last closing time (close command to contact touch)", "ms", [0, 300], 0.25,
      "IEC 61850: SCBR.OpTmCls"),
    P("trip_coil_peak_a", "Coils.TripPeak", "Trip coil peak current, last opening", "A", [0, 10], 0.01, "IEC 61850: SCBR.ColOpnA"),
    P("close_coil_peak_a", "Coils.ClosePeak", "Close coil peak current, last closing", "A", [0, 10], 0.01, "IEC 61850: SCBR.ColClsA"),
    P("spring_charge_time_s", "Mechanism.ChargeTime", "Spring charging time, last charge", "s", [0, 120], 0.1, "IEC 61850: SCBR.ChaMotTm"),
    P("spring_motor_current_a", "Mechanism.MotorCurrent", "Spring charging motor current, last charge (mean)", "A", [0, 20], 0.03,
      "IEC 61850: SCBR.ChaMotA"),
    P("spring_charged", "Mechanism.SpringCharged", "Closing spring charged (1 yes, 0 no)", "code", [0, 1], 0, "IEC 61850: SCBR.ChaSt"),
    P("last_interrupted_ka", "Interruption.LastCurrent", "Highest pole current at the last opening", "kA", [0, 63], 0.0, "IEC 61850: SCBR.AccAbr"),
    P("wear_sum_l1", "Interruption.WearSumL1", "Accumulated interrupted current sum(I^1.8), pole L1", "kA^1.8", [0, 1e6], 0, "IEC 61850: SCBR.AccAbr.phsA"),
    P("wear_sum_l2", "Interruption.WearSumL2", "Accumulated interrupted current sum(I^1.8), pole L2", "kA^1.8", [0, 1e6], 0, "IEC 61850: SCBR.AccAbr.phsB"),
    P("wear_sum_l3", "Interruption.WearSumL3", "Accumulated interrupted current sum(I^1.8), pole L3", "kA^1.8", [0, 1e6], 0, "IEC 61850: SCBR.AccAbr.phsC"),
    P("operation_count", "Interruption.OperationCount", "Operating cycles (counter)", "count", [0, 1e7], 0, "IEC 61850: XCBR.OpCnt"),
    P("cabinet_temp_c", "Cabinet.Temperature", "Operating mechanism cabinet temperature", "degC", [-40, 80], 0.1, "IEC 61850: STMP.Tmp"),
    P("cabinet_humidity_pct", "Cabinet.Humidity", "Operating mechanism cabinet relative humidity", "%", [0, 100], 0.3, "IEC 61850: MMET.Hum"),
    P("heater_current_a", "Cabinet.HeaterCurrent", "Anti-condensation heater current", "A", [0, 5], 0.01),
]

failure_modes = {
    "sf6_leak": {"label": "SF6 leak", "cause": "A leaking flange seal or density-monitor fitting: the gas density falls. Below the alarm density the breaker must be refilled; at the lockout density it may no longer interrupt and is blocked",
                 "detect": ["sf6_p20_calc_mpa", "sf6_density_p20_mpa", "density_contact"], "action": "Locate the leak (camera / sniffer), repair the seal, refill to 0.70 MPa abs at 20 C; report the SF6 emission", "default_ramp_min": 4},
    "contact_wear": {"label": "Contact wear (repeated fault trips)", "cause": "A fault-prone line makes the breaker interrupt short-circuit currents again and again: the arcing contacts and nozzle erode, and the main contacts heat up",
                     "detect": ["wear_max_pct", "wear_l2_pct", "pole_residual_max_k"], "action": "Plan an interrupter overhaul (arcing contacts, nozzle); clear the line fault cause", "default_ramp_min": 4},
    "mechanism_lubrication": {"label": "Slow mechanism (lubrication)", "cause": "Grease in the operating mechanism has aged or the linkage is corroded: opening and closing get slower, which lengthens the arcing time and stresses the interrupter",
                              "detect": ["open_time_dev_ms", "close_time_dev_ms"], "action": "Service the operating mechanism: clean and re-lubricate the linkage and latches, check the damper", "default_ramp_min": 3},
    "trip_coil": {"label": "Trip coil degradation", "cause": "Shorted turns, a corroded terminal or a sticky plunger in the trip coil: less current, a slower release of the latch, and in the end a breaker that will not trip",
                  "detect": ["trip_coil_ratio", "open_time_dev_ms"], "action": "Measure the trip coil resistance and the trip circuit; replace the coil; check the second trip coil", "default_ramp_min": 3},
    "spring_motor": {"label": "Spring charging motor fault", "cause": "Worn motor brushes or gearbox: the closing spring takes longer to charge and the motor draws more current. After an O-0.3 s-CO trip the breaker may not be ready to close again",
                     "detect": ["charge_time_ratio", "spring_motor_current_a"], "action": "Overhaul or replace the charging motor and gearbox; check the motor supply", "default_ramp_min": 3},
    "heater_fault": {"label": "Cabinet heater failure", "cause": "The anti-condensation heater in the mechanism cabinet has failed: humidity rises, water condenses on the mechanism and auxiliary contacts, corrosion follows",
                     "detect": ["heater_current_a", "cabinet_humidity_pct"], "action": "Replace the heater and its thermostat; dry the cabinet and inspect for corrosion", "default_ramp_min": 3},
    "density_monitor_drift": {"label": "Density monitor drift", "cause": "The temperature-compensated density monitor reads high: it would not alarm on a real leak. The twin compensates the raw pressure and temperature itself and sees the difference",
                              "detect": ["density_monitor_dev_mpa"], "action": "Check the density monitor against a calibrated reference; replace it", "default_ramp_min": 3},
}

twin = {
    "$comment": "Single source of truth for the CB-701 digital twin: Siemens Energy 3AP1 FG 145 kV SF6 live-tank circuit breaker "
                "with stored-energy spring mechanism, on a 132 kV line bay. Ratings from the PEHLA type-test report and Siemens documents; "
                "SF6 density, contact wear, operating times, coils and spring charging monitored against them.",
    "twin": {"id": "urn:maximo:twin:circuitbreaker:CB-701", "version": "1.0.0",
             "kind": "SF6 live-tank high-voltage circuit breaker with spring-operated mechanism",
             "standards": {
                 "performance": f"Siemens 3AP1 FG 145 kV: {IR_A:.0f} A, {ISC_KA:.0f} kA, O-0.3 s-CO-3 min-CO, SF6 {P_FILL} / {P_MIN} MPa abs at 20 C, "
                                "opening 23 ms, closing 54 ms, M2 / C2",
                 "standard": "IEC 62271-100 (circuit breakers), IEC 62271-1 (common specifications, temperature rise)",
                 "density": "SF6 density compensated to 20 C with the ideal-gas isochore p20 = p x 293.15 / T (assumption: the real "
                            "SF6 isochore is close to straight in -30..+60 C; a manufacturer pressure-temperature curve would refine it)",
                 "wear": f"Contact wear = sum of I^{WEAR_Y} per pole against an allowance of {WEAR_N} interruptions at {ISC_KA:.0f} kA "
                         "(exponent and allowance assumed; the manufacturer's endurance curve sets them)",
                 "information_model": "Points named after IEC 61850 logical nodes (XCBR, SCBR, SIMG, MMXU, STMP)"}},
    "identification": {"assetnum": "CB-701", "description": "Circuit breaker 701 (132 kV line bay L7)",
                       "manufacturer": "Siemens Energy", "model": "3AP1 FG 145 kV 3150 A 40 kA",
                       "site": "Demo transmission substation", "location": "132 kV switchyard / line bay L7",
                       "medium": "SF6 0.70 MPa abs at 20 C, spring-operated, one interrupter per pole"},
    "design": {
        "rating": {"ur_kv": UR_KV, "ir_a": IR_A, "isc_ka": ISC_KA, "ip_ka": 108, "tk_s": 3, "fr_hz": 50, "ud_kv": 275, "up_kv": 650,
                   "operating_sequence": "O-0.3 s-CO-3 min-CO", "class": "M2 / C2", "break_time": "3 cycles",
                   "ambient_c": [-30, 40], "system_kv": 132},
        "sf6": {"fill_mpa_abs_20c": P_FILL, "min_functional_mpa_abs_20c": P_MIN, "alarm_mpa_abs_20c": P_ALARM,
                "lockout_mpa_abs_20c": P_MIN, "early_warning_mpa_abs_20c": round(P_FILL - 0.02, 3), "mass_kg": 8.1,
                "leakage_pct_per_year": 0.2, "r_specific_j_kgk": 56.92,
                "note": "alarm density assumed; lockout = minimum functional pressure; early warning = fill - 0.02 MPa (twin's own)"},
        "mechanism": {"type": "stored-energy spring", "open_time_ms": 23.0, "close_time_ms": 54.0, "coil_voltage_v": 110.0,
                      "trip_coil_r_ohm": 50.0, "close_coil_r_ohm": 50.0, "open_ms_per_v": 0.08, "close_ms_per_v": 0.15,
                      "charge_time_s": 12.0, "motor_current_a": 3.0, "aux_supply_v_ac": 400,
                      "endurance_cycles": 10000, "maintenance_free_cycles": 6000, "first_inspection_cycles": 3000,
                      "assumed": "coil resistance, voltage sensitivity of the operating times, charging time and motor current are assumptions"},
        "wear": {"exponent": WEAR_Y, "allowance_n_at_isc": WEAR_N, "allowance_ka_y": round(ALLOW, 1),
                 "basis": "sum of I^y per pole (y 1.4-2.2 typical), allowance assumed: 20 interruptions at 40 kA"},
        "thermal": {"pole_rise_at_ir_k": 35.0, "iec_limit_rise_k": 65.0, "tau_min": 20.0,
                    "basis": "pole terminal temperature rise ~ (I/Ir)^2; 35 K at 3150 A assumed (IEC 62271-1 allows 65 K for silver-coated contacts)"},
        "cabinet": {"heater_current_a": 0.55, "humidity_alert_pct": 85},
        "mass_kg": 1400, "pole_spacing_m": 2.0, "dimensions_assumed": "pole spacing 2.0 m, interrupter top ~5.2 m above ground (3D model only)",
        "demo": {"time_scale": 60, "op_every_s": 90, "note": "The plant clock runs 60x real time for the load day and the pole temperatures; the breaker "
                                                             "opens and recloses every 90 real seconds so that operating times, coils and spring charging update often. "
                                                             "Leak, wear and drift are compressed to minutes."},
    },
    "telemetry": {"event": "breaker", "publish_every_s": 5, "device_type": "CIRCUIT_BREAKER_SF6",
                  "groups": {"Switch": "Position", "Load": "Line currents (CTs)", "Ambient": "Weather", "Gas": "SF6 density monitoring",
                             "Pole": "Pole terminal temperatures", "Control": "DC control supply", "Mechanism": "Spring mechanism",
                             "Coils": "Trip and close coils", "Interruption": "Interrupted current and counters", "Cabinet": "Mechanism cabinet"},
                  "points": points},
    "twin_model": {"limits": {"open_time_dev_alert_ms": 3.0, "close_time_dev_alert_ms": 5.0, "trip_coil_ratio_alert": 0.8,
                              "charge_time_ratio_alert": 1.3, "wear_alert_pct": 80.0, "wear_limit_pct": 100.0,
                              "pole_residual_alert_k": 10.0, "pole_check_min_a": 600.0, "density_monitor_dev_alert_mpa": 0.015,
                              "heater_min_a": 0.2, "humidity_alert_pct": 85.0, "inspection_cycles": 3000}},
    "failure_modes": failure_modes,
    "presentation": {
        "category": "Circuit breaker",
        "kpis": [{"metric": "sf6_density_p20_mpa", "label": "SF6 p20", "unit": "MPa", "decimals": 3},
                 {"metric": "load_current_l1_a", "label": "Current L1", "unit": "A", "decimals": 0},
                 {"metric": "last_open_time_ms", "label": "Open time", "unit": "ms", "decimals": 1},
                 {"metric": "operation_count", "label": "Operations", "unit": "", "decimals": 0}],
        "twin_kpis": [{"metric": "sf6_margin_alarm_mpa", "label": "SF6 margin to alarm", "unit": "MPa", "decimals": 3},
                      {"metric": "wear_max_pct", "label": "Contact wear", "unit": "%", "decimals": 1}],
        "compare": [
            {"label": "SF6 density (p20)", "measured": "sf6_density_p20_mpa", "expected": "sf6_p20_calc_mpa", "unit": "MPa", "decimals": 3,
             "basis": "monitor output vs. the twin's own compensation of pressure and gas temperature"},
            {"label": "Opening time", "measured": "last_open_time_ms", "expected": "open_time_expected_ms", "unit": "ms", "decimals": 1,
             "basis": "23 ms rated, corrected for the control voltage"},
            {"label": "Closing time", "measured": "last_close_time_ms", "expected": "close_time_expected_ms", "unit": "ms", "decimals": 1,
             "basis": "54 ms rated, corrected for the control voltage"},
            {"label": "Trip coil peak current", "measured": "trip_coil_peak_a", "expected": "trip_coil_expected_a", "unit": "A", "decimals": 2,
             "basis": "control voltage / coil resistance (50 Ω assumed)"},
            {"label": "Spring charging time", "measured": "spring_charge_time_s", "expected": "charge_time_expected_s", "unit": "s", "decimals": 1,
             "basis": "12 s (assumed)"},
            {"label": "Pole L2 temperature rise", "measured": "pole_rise_l2_k", "expected": "pole_rise_expected_k", "unit": "K", "decimals": 1,
             "basis": "35 K x (I/Ir)², IEC 62271-1 limit 65 K"},
            {"label": "Contact wear (worst pole)", "measured": "wear_max_pct", "expected": None, "unit": "%", "decimals": 1,
             "basis": "sum I^1.8 vs. 20 x 40 kA^1.8"},
        ],
        "trends": [{"metric": "sf6_p20_calc_mpa", "label": "SF6 p20 (MPa)"}, {"metric": "wear_max_pct", "label": "Contact wear (%)"},
                   {"metric": "open_time_dev_ms", "label": "Opening time deviation (ms)"}, {"metric": "pole_residual_max_k", "label": "Pole hot spot (K)"}],
        "design": [
            {"label": "Breaker", "value": "Siemens Energy 3AP1 FG 145 kV, 3150 A, 40 kA, O-0.3 s-CO-3 min-CO, M2 / C2, 1400 kg"},
            {"label": "SF6", "value": "8.1 kg, 0.70 MPa abs fill / 0.60 MPa minimum functional at 20 °C, 0.2 %/year leakage"},
            {"label": "Mechanism", "value": "Stored-energy spring, opening 23 ms, closing 54 ms, 110 V DC coils, 10,000 cycles"},
            {"label": "Source", "value": "PEHLA type-test report 14253 Bs-1, Siemens EPD and brochure; 3D built from typical dimensions, not manufacturer CAD"},
        ],
    },
}

if __name__ == "__main__":
    out = HERE / "twin" / "cb-701.twin.json"
    out.parent.mkdir(exist_ok=True)
    json.dump(twin, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("written", out)
