"""Write twin/ev-7001.twin.json: the public DC fast charger twin (EV-7001).

    python build_twin.py

EV-7001 is one public DC fast charger at a motorway charging hub: an alpitronic hypercharger HYC400 with four 100 kW
Power-Stacks (400 kW), two CCS2 outlets with liquid-cooled cables, a payment terminal, a calibrated DC meter per outlet,
and an OCPP connection to the operator's charging station management system (CSMS).

Sources and assumptions (every number below is either from a published data sheet or labelled as an assumption in "source"):
  alpitronic HYC400 data sheet (Datasheet_HYC400_v02-1, 2026) and the HYC400 product page: 400 kW from four Power-Stacks,
    100 kW each (one stack 100 kW, max. 300 A; four stacks max. 2 x 600 A), granularity 50 kW, 150-1000 V DC, CCS2 up to 600 A,
    efficiency up to 97.7 % at full load and up to 98.2 % peak, standby 43 W, 400 V AC, max. 630 A input, PF > 0.99 at full
    load, -30 to +55 C, IP54, 2185 x 732 x 663 mm, OCPP 1.6 J and 2.0.1 J, ISO 15118 / DIN SPEC 70121, IEC 61851-1 and
    IEC 61851-23, DC meters to the German calibration law and MID, card / QR payment, RFID.
  Phoenix Contact CHARX connect professional EV-T2HPCC-DC500A-5,0M (item 1494471) data sheet: liquid-cooled CCS2 cable,
    500 A permanent (up to 40 C ambient), up to 700 A boost, 1000 V, 150 A with a failed cooling unit, cooling capacity
    900 W for 5 m, flow 2 l/min, 50/50 water-glycol, NTC sensors at the DC contacts, switch-off temperature 90 C,
    0.00078 ohm/m per power core at 20 C, IEC 62196-3-1. Used as the typical cable of this class: the HYC400 data sheet does
    not name its cable maker.
  IEC 61851-23 insulation monitoring as commonly applied (TI reference design TIDUEZ8, Bender isoEV425): warning below
    500 ohm/V, fault below 100 ohm/V.
  23 CFR 680.116(b) (US NEVI): port uptime = (525600 - (T_outage - T_excluded)) / 525600 x 100, required > 97 %.
  Efficiency curve shape, thermal resistances, contact heating, coolant properties, session counters and alert limits:
    ASSUMPTIONS of typical values, to be replaced by the factory test report and the commissioning data of your own charger.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with "

# Efficiency: loss per Power-Stack = a + c P^2 (P in kW per stack), fitted to the two published points:
#   97.7 % at full load (100 kW per stack) and a 98.2 % peak. With loss = a + c P^2 the efficiency peaks where a = c P^2,
#   so loss/P = 2 sqrt(a c) at the peak. Two equations, two unknowns (the root with the peak below full load is kept).
ETA_FULL, ETA_PEAK, STACK_KW = 0.977, 0.982, 100.0
L_FULL = STACK_KW * (1 / ETA_FULL - 1)              # kW lost per stack at full load
AC = ((1 / ETA_PEAK - 1) / 2) ** 2                    # a x c
_c = (L_FULL + math.sqrt(L_FULL ** 2 - 4 * STACK_KW ** 2 * AC)) / (2 * STACK_KW ** 2)
LOSS_C = round(_c, 9)
LOSS_A = round(AC / _c, 6)
P_PEAK = round(math.sqrt(LOSS_A / LOSS_C), 2)

# Cable: two power cores per pole (5 x 25 mm2 = 2 + 2 + PE) -> loop resistance of the DC+ and DC- path
R_CORE, LEN, CORES = 0.00078, 5.0, 2
R_LOOP = round(2 * LEN * R_CORE / CORES, 6)

twin = {
    "$comment": "EV-7001 public DC fast charger twin. Expected values in Maximo Monitor from the charger data sheet, the cable data sheet, the insulation monitoring practice of IEC 61851-23 and the uptime rule of the operator's funding programme; the charger, its cooling unit and the CSMS send only what they measure and count.",
    "twin": {"id": "EV-7001", "name": "DC fast charger EV-7001", "version": "1.0.0", "folder": "evcharger-twin"},
    "identification": {
        "asset": "EV-7001", "assetnum": "EV-7001", "manufacturer": "alpitronic",
        "model": "hypercharger HYC400 (4 x 100 kW Power-Stacks, 400 kW, 2 x CCS2)",
        "description": "Public DC fast charger, bay 1 of a motorway charging hub: two CCS2 outlets, liquid-cooled cables, card payment, OCPP to the CSMS",
        "site": "Demo motorway charging hub, bays 1 and 2",
        "power": "Four 100 kW Power-Stacks shared dynamically between the two outlets in 50 kW steps",
        "cable": "Liquid-cooled CCS2 HPC cable, 5 m, 500 A permanent (for example Phoenix Contact CHARX connect professional 1494471)",
        "backend": "OCPP 2.0.1 J to the operator's charging station management system (CSMS); payment terminal for cards; MID / calibration-law DC meter per outlet",
    },
    "design": {
        "charger": {
            "rated_kw": 400.0, "stacks": 4, "stack_kw": STACK_KW, "granularity_kw": 50.0, "outlets": 2,
            "v_min": 150.0, "v_max": 1000.0, "outlet_max_a": 600.0, "standby_w": 43.0,
            "eta_full": ETA_FULL, "eta_peak": ETA_PEAK,
            "source": "alpitronic HYC400 data sheet: 4 Power-Stacks of 100 kW, granularity 50 kW, 150-1000 V DC, CCS2 up to 600 A, "
                      "efficiency up to 97.7 % at full load, up to 98.2 % peak, standby 43 W.",
        },
        "efficiency": {
            "loss_a_kw": LOSS_A, "loss_c_per_kw": LOSS_C, "peak_at_kw_per_stack": P_PEAK,
            "source": "Loss per active stack = a + c x P^2, fitted to the two published points (97.7 % at 100 kW per stack, 98.2 % peak). "
                      "The shape (no-load loss + conduction loss) is an " + A + "the efficiency curve of the factory test report.",
        },
        "stack_thermal": {
            "r_th_k_per_kw": 12.0,
            "source": "Hottest heat sink rise over the cabinet air inlet per kW lost in one stack: " + A + "the commissioning trend at full power.",
        },
        "cable": {
            "length_m": LEN, "rated_a": 500.0, "boost_a": 700.0, "failed_cooling_a": 150.0, "r_core_ohm_per_m": R_CORE,
            "cores_per_pole": CORES, "r_loop_ohm": R_LOOP, "cooling_capacity_w": 900.0, "flow_nominal_lpm": 2.0,
            "contact_switch_off_c": 90.0, "contact_k_per_ka2": 120.0,
            "coolant_density_kg_per_l": 1.07, "coolant_cp_j_per_kgk": 3350.0,
            "source": "Phoenix Contact CHARX connect professional 1494471 (5 m): 500 A permanent up to 40 C, 700 A boost, 150 A with a failed "
                      "cooling unit, cooling capacity 900 W, flow 2 l/min, switch-off at 90 C at the DC contacts, 0.00078 ohm/m per power core "
                      "at 20 C. Two power cores per pole (loop resistance " + f"{R_LOOP} ohm" + "), the contact rise over the coolant "
                      "(120 K per kA^2: 30 K at 500 A), and the density and specific heat of 50/50 glycol: " + A + "the cable maker's thermal data.",
        },
        "safety": {
            "insulation_warn_ohm_per_v": 500.0, "insulation_fault_ohm_per_v": 100.0, "insulation_ref_v": 1000.0,
            "source": "Insulation monitoring of the DC output (IEC 61851-23 as commonly applied, IEC 61557-8 devices): warning below "
                      "500 ohm/V, fault below 100 ohm/V, referred to the 1000 V maximum output voltage (500 kohm and 100 kohm).",
        },
        "availability": {
            "minutes_per_year": 525600, "uptime_required_pct": 97.0, "uptime_network_target_pct": 99.0,
            "source": "US NEVI rule 23 CFR 680.116(b): each port > 97 % average annual uptime, mu = (525600 - (T_outage - T_excluded)) / "
                      "525600 x 100. UK Public Charge Point Regulations 2023: rapid network 99 % reliable on average (shown for comparison).",
        },
        "sessions": {
            "success_target_pct": 95.0,
            "source": "Charge-start success target of the operator: " + A + "your own service level. Counters are rolling 24 h values "
                      "kept by the CSMS from the OCPP transaction events.",
        },
        "site": {"ambient_nominal_c": 25.0, "coolant_supply_over_ambient_k": 5.0, "ac_voltage_v": 400.0,
                 "source": "Hub conditions for the demo: " + A + "your site."},
        "demo": {"time_scale": 10, "battery_kwh": [77.0, 62.0], "note": "Demo only: the plant clock runs 10 times faster so a full session lasts about two minutes; "
                 "the 24 h and 365 d counters come from the failure modes, not from the demo clock."},
    },
    "telemetry": {
        "event": "evcharger", "publish_every_s": 10, "device_type": "EV_CHARGER_DC",
        "groups": {"Grid": "AC supply", "Out1": "Outlet 1 (CCS2)", "Out2": "Outlet 2 (CCS2)", "Stacks": "Power-Stacks",
                   "Cooling": "Cable cooling unit", "Site": "Site", "Safety": "Insulation and contactors",
                   "Sessions": "Charge starts, rolling 24 h (CSMS)", "Availability": "Outage minutes, rolling 365 d (CSMS)",
                   "Backend": "Payment and OCPP", "Meter": "Last completed session"},
        "points": [
            {"metric": "ac_input_kw", "path": "Grid.ACPower", "label": "AC input power", "unit": "kW"},
            {"metric": "ac_voltage_v", "path": "Grid.ACVoltage", "label": "AC supply voltage, line to line", "unit": "V"},
            {"metric": "dc_voltage_c1_v", "path": "Out1.Voltage", "label": "Outlet 1 DC voltage", "unit": "V"},
            {"metric": "dc_current_c1_a", "path": "Out1.Current", "label": "Outlet 1 DC current", "unit": "A"},
            {"metric": "contact_temp_c1_c", "path": "Out1.ContactTemp", "label": "Outlet 1 hottest DC contact (NTC in the connector)", "unit": "°C"},
            {"metric": "status_c1", "path": "Out1.Status", "label": "Outlet 1 status (0 available, 1 charging, 2 faulted)", "unit": "code"},
            {"metric": "dc_voltage_c2_v", "path": "Out2.Voltage", "label": "Outlet 2 DC voltage", "unit": "V"},
            {"metric": "dc_current_c2_a", "path": "Out2.Current", "label": "Outlet 2 DC current", "unit": "A"},
            {"metric": "contact_temp_c2_c", "path": "Out2.ContactTemp", "label": "Outlet 2 hottest DC contact (NTC in the connector)", "unit": "°C"},
            {"metric": "status_c2", "path": "Out2.Status", "label": "Outlet 2 status (0 available, 1 charging, 2 faulted)", "unit": "code"},
            {"metric": "stacks_available", "path": "Stacks.Available", "label": "Power-Stacks available", "unit": "count"},
            {"metric": "stacks_active", "path": "Stacks.Active", "label": "Power-Stacks switched on now", "unit": "count"},
            {"metric": "stack_temp_max_c", "path": "Stacks.TempMax", "label": "Hottest Power-Stack heat sink", "unit": "°C"},
            {"metric": "coolant_supply_c", "path": "Cooling.Supply", "label": "Coolant to the cables", "unit": "°C"},
            {"metric": "coolant_return_c", "path": "Cooling.Return", "label": "Coolant back from the cables", "unit": "°C"},
            {"metric": "coolant_flow_lpm", "path": "Cooling.Flow", "label": "Coolant flow per cable", "unit": "l/min"},
            {"metric": "ambient_c", "path": "Site.Ambient", "label": "Cabinet air inlet temperature", "unit": "°C"},
            {"metric": "insulation_kohm", "path": "Safety.Insulation", "label": "DC output insulation resistance, last check", "unit": "kΩ"},
            {"metric": "contactor_weld", "path": "Safety.ContactorWeld", "label": "Welded DC contactor detected (1 = yes)", "unit": "code"},
            {"metric": "starts_attempted_24h", "path": "Sessions.Attempts", "label": "Charge starts attempted, 24 h", "unit": "count"},
            {"metric": "starts_failed_comm_24h", "path": "Sessions.FailComm", "label": "Failed: vehicle communication (ISO 15118 / DIN 70121), 24 h", "unit": "count"},
            {"metric": "starts_failed_auth_24h", "path": "Sessions.FailAuth", "label": "Failed: authorisation or payment, 24 h", "unit": "count"},
            {"metric": "starts_failed_safety_24h", "path": "Sessions.FailSafety", "label": "Failed: insulation or contactor self-test, 24 h", "unit": "count"},
            {"metric": "starts_failed_other_24h", "path": "Sessions.FailOther", "label": "Failed: other causes, 24 h", "unit": "count"},
            {"metric": "sessions_aborted_24h", "path": "Sessions.Aborted", "label": "Sessions stopped by the charger, 24 h", "unit": "count"},
            {"metric": "outage_min_365d", "path": "Availability.Outage", "label": "Outage minutes of the worse port, 365 d", "unit": "min"},
            {"metric": "outage_excluded_min_365d", "path": "Availability.Excluded", "label": "Excluded outage minutes (grid, vandalism, planned), 365 d", "unit": "min"},
            {"metric": "payment_terminal_ok", "path": "Backend.PaymentTerminal", "label": "Payment terminal online (1 = yes)", "unit": "code"},
            {"metric": "ocpp_heartbeat_age_s", "path": "Backend.Heartbeat", "label": "Seconds since the last OCPP message to the CSMS", "unit": "s"},
            {"metric": "last_session_meter_kwh", "path": "Meter.Billed", "label": "Last session energy, calibrated DC meter", "unit": "kWh"},
            {"metric": "last_session_internal_kwh", "path": "Meter.Internal", "label": "Last session energy, charger's own measurement", "unit": "kWh"},
        ],
    },
    "twin_model": {
        "limits": {
            "min_power_for_eff_kw": 50.0, "loss_ratio_alert": 1.35, "stack_rise_ratio_alert": 1.4,
            "coolant_flow_min_lpm": 1.4, "contact_ratio_alert": 1.6, "contact_ratio_min_a": 150.0, "contact_temp_alert_c": 80.0,
            "success_min_pct": 90.0, "fail_reason_max_pct": 8.0, "min_attempts": 10, "meter_dev_max_pct": 1.0,
            "heartbeat_max_s": 300.0,
        },
        "$limits_source": "Alert limits: " + A + "your operator's service levels. 80 C is 10 K below the cable's 90 C switch-off; 1.4 l/min is 70 % of the cable's 2 l/min.",
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it (at full severity).",
        "power_stack_failure": {"name": "Power-Stack failure (output derated)", "part": "power stack",
                                "symptoms": "one stack out of service: 300 kW left to share between the two outlets",
                                "rules": ["CHG_STACK_DERATED"], "default_ramp_min": 0.5},
        "stack_cooling_ageing": {"name": "Power-Stack ageing or clogged air filter", "part": "power stack",
                                 "symptoms": "losses above the efficiency curve, heat sinks hotter than the losses explain",
                                 "rules": ["CHG_EFFICIENCY_LOW", "CHG_STACK_HOT"], "default_ramp_min": 1.5},
        "coolant_flow_low": {"name": "Cable cooling flow low (pump wear, blocked filter)", "part": "cooling unit",
                             "symptoms": "flow falls, coolant returns hotter, less margin before the cable must derate",
                             "rules": ["CHG_COOLANT_FLOW_LOW"], "default_ramp_min": 1},
        "contact_wear": {"name": "Worn or dirty DC contacts, outlet 1", "part": "connector",
                         "symptoms": "contact temperature rises faster with current than the coolant explains",
                         "rules": ["CHG_CONTACT_WEAR", "CHG_CONTACT_TEMP_HIGH"], "default_ramp_min": 1.5},
        "insulation_degradation": {"name": "Insulation fault on the DC output (moisture in cable or connector)", "part": "cable",
                                   "symptoms": "insulation resistance falls, the pre-charge check refuses to start",
                                   "rules": ["CHG_INSULATION_FAULT", "CHG_SUCCESS_LOW"], "default_ramp_min": 1.5},
        "contactor_welded": {"name": "Welded DC contactor, outlet 2", "part": "contactor",
                             "symptoms": "weld check fails, outlet 2 locked out, outage minutes grow",
                             "rules": ["CHG_CONTACTOR_WELDED", "CHG_UPTIME_LOW"], "default_ramp_min": 1},
        "vehicle_comm_failures": {"name": "Vehicle communication failures (control pilot / PLC modem)", "part": "communication",
                                  "symptoms": "charge starts fail during the ISO 15118 / DIN 70121 handshake",
                                  "rules": ["CHG_FAIL_COMM", "CHG_SUCCESS_LOW"], "default_ramp_min": 1},
        "payment_backend_fault": {"name": "Payment terminal or backend link fault", "part": "payment",
                                  "symptoms": "terminal offline, card payments rejected, OCPP messages late",
                                  "rules": ["CHG_PAYMENT_OFFLINE", "CHG_FAIL_AUTH", "CHG_SUCCESS_LOW"], "default_ramp_min": 1},
    },
    "presentation": {"title": "EV-7001 DC fast charger", "dashboard": "EV_CHARGER_DC"},
}

out = HERE / "twin" / "ev-7001.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out, f"loss a={LOSS_A} kW, c={LOSS_C} /kW, peak at {P_PEAK} kW per stack, R_loop={R_LOOP} ohm")
