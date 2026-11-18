"""Write twin/ups-6101.twin.json: the data centre UPS twin (UPS-6101).

    python build_twin.py

UPS-6101 is a three-phase, transformer-free, double-conversion (online) UPS that feeds one data hall's IT load: an Eaton 93PM
in its 200 kW frame with four 50 kW uninterruptible power modules (UPMs), sold as 93PM-150(200)-N+1 (150 kW with one spare
module), 400 V, with two external strings of 40 x 12 V VRLA blocks (480 V nominal, 240 cells per string).

Sources and assumptions (every number below is either from a published data sheet or labelled as an assumption in "source"):
  Eaton 93PM UPS 30-200 kW data sheet 93PM01DAT Rev F (August 2013) and the Eaton 93PM brochure (2013): ratings, "93PM-200(200)
    200 kW or 150 kW N+1", 93PM-150(200)-N+1, up to 97 % in double conversion, > 99 % in Energy Saver System (ESS), input PF 0.99,
    ITHD < 3 %, 220/380 to 240/415 V, VRLA 432 V (36 x 12 V) or 480 V (40 x 12 V, 240 cells), inverter overload 10 min 102-110 %,
    IEC 62040-1 / -2 / -3, Web/SNMP and Modbus/Jbus cards, typical ESS transfer 2 ms.
  UK Energy Technology List (ETL), product 70758, model 93PM-150(200)-ZZZ-N+1: 150 kVA, efficiency 96.1 / 96.7 / 96.7 / 96.5 %
    at 25 / 50 / 75 / 100 % of rated power, least efficient normal operating mode VFI.
  CSB HRL12390W data sheet (RA260131): 12 V VRLA-AGM, constant power discharge per battery to 1.75 V/cell at 25 C, internal
    resistance approx. 3.00 mOhm, design life up to 10 years in standby service at 25 C.
  Schneider Electric FAQ FA158934: each 8 C increase in temperature cuts the life of a VRLA battery in half.
  Loss split, ESS losses, thermal resistance, DC-link ripple, limits and the site requirements: ASSUMPTIONS of typical values,
    to be replaced by the factory test report and the commissioning data of your own UPS.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with "


def fit_loss(points, rated_kw):
    """Least-squares fit of loss = a + b P + c P^2 (kW) to (load %, efficiency %) points."""
    xs = [rated_kw * p / 100 for p, _ in points]
    ys = [x * (100 / e - 1) for x, (_, e) in zip(xs, points)]
    rows = [[1.0, x, x * x] for x in xs]
    ata = [[sum(r[i] * r[j] for r in rows) for j in range(3)] for i in range(3)]
    aty = [sum(r[i] * y for r, y in zip(rows, ys)) for i in range(3)]
    m = [row[:] + [v] for row, v in zip(ata, aty)]
    for i in range(3):                                  # Gauss-Jordan elimination
        piv = m[i][i]
        m[i] = [v / piv for v in m[i]]
        for k in range(3):
            if k != i:
                f = m[k][i]
                m[k] = [a - f * b for a, b in zip(m[k], m[i])]
    return [round(m[i][3], 9) for i in range(3)]


EFF_POINTS = [[25, 96.1], [50, 96.7], [75, 96.7], [100, 96.5]]
LOSS = fit_loss(EFF_POINTS, 150.0)

twin = {
    "$comment": "UPS-6101 data centre UPS twin. Expected values in Maximo Monitor from the data sheet, the Energy Technology List efficiency points, the battery data sheet and commissioning data; the UPS, its battery monitor and the room sensors send only what they measure.",
    "twin": {"id": "UPS-6101", "name": "Data centre UPS UPS-6101", "version": "1.0.0", "folder": "ups-twin"},
    "identification": {
        "asset": "UPS-6101", "assetnum": "UPS-6101", "manufacturer": "Eaton",
        "model": "93PM-150(200)-N+1 (200 kW frame, 4 x 50 kW UPM, 150 kW N+1)",
        "description": "Data hall A UPS: three-phase double-conversion, 150 kW N+1, with two VRLA battery strings",
        "site": "Demo data centre, hall A, UPS room 1",
        "topology": "Transformer-free IGBT rectifier and inverter with PWM, double conversion (VFI) with Energy Saver System (ESS) available",
        "modules": "Four 50 kW uninterruptible power modules (UPMs) in parallel, central static bypass",
        "battery": "2 parallel strings x 40 blocks CSB HRL12390W 12 V VRLA-AGM (480 V nominal, 240 cells per string)",
        "monitoring": "UPS network card (SNMP / Modbus TCP), block-level battery monitor, room temperature sensors",
    },
    "design": {
        "ups": {
            "frame_kw": 200.0, "upm_kw": 50.0, "upm_installed": 4, "rated_kw": 150.0, "redundancy": "N+1",
            "voltage_ll_v": 400.0, "frequency_hz": 50.0, "input_pf": 0.99, "input_ithd_pct": 3.0,
            "overload": "inverter 10 min at 102-110 %, 60 s at 111-125 %, 10 s at 126-150 %",
            "battery_nominal_v": 480.0,
            "source": "Eaton 93PM UPS 30-200 kW data sheet 93PM01DAT Rev F (2013) and brochure: 93PM-200(200) is 200 kW or 150 kW N+1, "
                      "93PM-150(200)-N+1 is the 150 kW N+1 version of the 200 kW frame (four 50 kW UPMs), 1.0 output power factor, "
                      "input PF 0.99, ITHD < 3 %, 480 V VRLA option (40 x 12 V, 240 cells).",
        },
        "efficiency": {
            "points_pct_load_eff": EFF_POINTS, "rated_kva": 150.0,
            "loss_a_kw": LOSS[0], "loss_b": LOSS[1], "loss_c_per_kw": LOSS[2],
            "source": "UK Energy Technology List product 70758, Eaton 93PM-150(200)-ZZZ-N+1, 150 kVA: 96.1 / 96.7 / 96.7 / 96.5 % at 25 / 50 / "
                      "75 / 100 % load, mode VFI. Loss curve a + b P + c P^2 fitted to these four points by build_twin.py; the split of "
                      "a and c between the modules (a per module, c shared) is an " + A + "the factory test report of your UPS.",
        },
        "ess": {
            "loss_fixed_kw": 0.25, "loss_frac": 0.005,
            "source": "Eaton: > 99 % efficiency in Energy Saver System (ESS), load on the static bypass with double conversion on demand "
                      "(typical 2 ms transfer). Loss in ESS = 0.25 kW + 0.5 % of the load: " + A + "the ESS efficiency curve of your UPS.",
        },
        "battery": {
            "block": "CSB HRL12390W", "strings": 2, "blocks_per_string": 40, "cells_per_block": 6, "end_v_per_cell": 1.75,
            "table_min": [2, 4, 5, 6, 8, 10, 15, 20, 30, 45, 60, 90],
            "table_w_per_block": [4583, 3970, 3736, 3555, 3190, 2861, 2348, 1943, 1488, 1098, 885, 653],
            "r_block_mohm": 3.0, "design_life_y": 10.0, "life_ref_c": 25.0, "life_halving_k": 8.0, "inverter_eff_on_battery": 0.975,
            "source": "CSB HRL12390W data sheet RA260131: constant power discharge per battery to 10.50 V (1.75 V/cell) at 25 C, internal "
                      "resistance approx. 3.00 mOhm, design life up to 10 years at 25 C. Halving of life per 8 C: Schneider Electric FAQ "
                      "FA158934 (rule of thumb). Two strings of 40 blocks, end voltage 1.75 V/cell and inverter efficiency on battery: "
                      + A + "the battery sizing sheet and the UPS end-of-discharge setting.",
        },
        "thermal": {
            "r_th_k_per_kw": 15.0, "fan_rated_pct": 100.0,
            "source": "Heatsink temperature rise over the cooling air per kW of loss in one module: " + A + "the rise logged at commissioning.",
        },
        "dc_link": {
            "dc_bus_nominal_v": 800.0, "ripple_floor_v": 1.0, "ripple_full_v": 4.0,
            "source": "DC-link voltage and its ripple (peak to peak) with no load and with one module at its rated 50 kW. Rises as the "
                      "electrolytic capacitors lose capacitance and their ESR grows: " + A + "the service data of your UPS.",
        },
        "site": {
            "required_autonomy_min": 10.0, "it_load_design_kw": 110.0,
            "source": "Battery autonomy the operator requires (generator start, transfer and a margin) and the planned IT load of the hall: "
                      + A + "the data centre's design basis.",
        },
        "demo": {"time_scale": 1, "note": "Demo only: the IT load follows a gentle daily swing; failure modes ramp in over minutes of real time."},
    },
    "telemetry": {
        "event": "ups", "publish_every_s": 10, "device_type": "UPS_DOUBLE_CONVERSION",
        "groups": {"Input": "Rectifier input", "Output": "Inverter output, per phase", "UPM": "Power modules, DC link and cooling",
                   "Mode": "Operating mode and events", "Battery": "Battery strings and battery monitor"},
        "points": [
            {"metric": "input_voltage_v", "path": "Input.Voltage", "label": "Input voltage, line to line", "unit": "V"},
            {"metric": "input_power_kw", "path": "Input.Power", "label": "Input active power", "unit": "kW"},
            {"metric": "input_freq_hz", "path": "Input.Frequency", "label": "Input frequency", "unit": "Hz"},
            {"metric": "output_voltage_v", "path": "Output.Voltage", "label": "Output voltage, line to line", "unit": "V"},
            {"metric": "output_power_kw", "path": "Output.Power", "label": "Output active power", "unit": "kW"},
            {"metric": "output_current_l1_a", "path": "Output.CurrentL1", "label": "Output current, phase L1", "unit": "A"},
            {"metric": "output_current_l2_a", "path": "Output.CurrentL2", "label": "Output current, phase L2", "unit": "A"},
            {"metric": "output_current_l3_a", "path": "Output.CurrentL3", "label": "Output current, phase L3", "unit": "A"},
            {"metric": "upm_online", "path": "UPM.Online", "label": "Power modules online", "unit": "count"},
            {"metric": "dc_bus_v", "path": "UPM.DCBus", "label": "DC-link voltage (mean of the modules)", "unit": "V"},
            {"metric": "dc_ripple_v", "path": "UPM.DCRipple", "label": "DC-link ripple, worst module (peak to peak)", "unit": "V"},
            {"metric": "heatsink_temp_max_c", "path": "UPM.HeatsinkMax", "label": "Hottest inverter/rectifier heatsink", "unit": "°C"},
            {"metric": "inlet_air_c", "path": "UPM.InletAir", "label": "Cooling air at the UPS inlet", "unit": "°C"},
            {"metric": "fan_speed_pct", "path": "UPM.FanSpeed", "label": "Slowest cooling fan, % of full speed", "unit": "%"},
            {"metric": "fan_cmd_pct", "path": "UPM.FanCommand", "label": "Fan speed command", "unit": "%"},
            {"metric": "ups_mode", "path": "Mode.Code", "label": "Mode (1 double conversion, 2 ESS, 3 bypass, 4 battery)", "unit": "code"},
            {"metric": "ess_enabled", "path": "Mode.ESSEnabled", "label": "Energy Saver System enabled (1 = yes)", "unit": "code"},
            {"metric": "bypass_events_30d", "path": "Mode.BypassEvents30d", "label": "Transfers to static bypass, last 30 days", "unit": "count"},
            {"metric": "battery_voltage_v", "path": "Battery.Voltage", "label": "Battery voltage", "unit": "V"},
            {"metric": "battery_current_a", "path": "Battery.Current", "label": "Battery current (+ charge)", "unit": "A"},
            {"metric": "battery_temp_c", "path": "Battery.Temperature", "label": "Battery temperature (mean of the blocks)", "unit": "°C"},
            {"metric": "battery_r_max_mohm", "path": "Battery.RMax", "label": "Highest block internal resistance", "unit": "mΩ"},
            {"metric": "battery_soh_pct", "path": "Battery.Capacity", "label": "Capacity found at the last discharge test", "unit": "%"},
            {"metric": "battery_age_days", "path": "Battery.AgeDays", "label": "Days since the strings were installed", "unit": "d"},
            {"metric": "battery_temp_life_c", "path": "Battery.LifeTemp", "label": "Mean battery temperature since installation", "unit": "°C"},
        ],
    },
    "twin_model": {
        "limits": {
            "imbalance_alert_pct": 10.0, "loss_ratio_alert": 1.3, "ripple_ratio_alert": 1.6, "ripple_ratio_limit": 2.4,
            "fan_ratio_alert": 0.85, "heatsink_residual_alert_k": 6.0, "batt_r_ratio_alert": 1.3, "soh_alert_pct": 80.0,
            "batt_temp_alert_c": 30.0, "bypass_events_alert": 2,
        },
        "limits_source": "Phase imbalance, loss ratio, ripple ratio, fan ratio, heatsink residual and bypass-event limits: assumptions. "
                      "Battery resistance 30 % above baseline and capacity below 80 %: typical practice for VRLA (IEEE 1188 practice as "
                      "summarised by battery makers). Battery temperature: 25 C nominal on the data sheet, alert at 30 C (assumption).",
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "dc_capacitor_ageing": {"name": "DC-link capacitor ageing", "part": "upm", "symptoms": "DC-link ripple up at the same load per module",
                                "rules": ["UPS_DC_RIPPLE_LIMIT"], "default_ramp_min": 1.5},
        "fan_wear": {"name": "Cooling fan wear", "part": "cooling", "symptoms": "slowest fan below its command, heatsinks hotter than the losses explain",
                     "rules": ["UPS_FAN_SLOW", "UPS_HEATSINK_RISE_HIGH"], "default_ramp_min": 1.5},
        "upm_failure": {"name": "Power module failed (offline)", "part": "upm", "symptoms": "three modules online, the load no longer fits N+1",
                        "rules": ["UPS_MODULE_OFFLINE", "UPS_REDUNDANCY_LOST"], "default_ramp_min": 0.5},
        "phase_load_growth": {"name": "New IT load on one phase", "part": "load", "symptoms": "L1 current up, imbalance up, worst phase beyond N+1",
                              "rules": ["UPS_PHASE_IMBALANCE", "UPS_REDUNDANCY_LOST"], "default_ramp_min": 1},
        "converter_losses": {"name": "Rectifier / inverter losses up", "part": "upm", "symptoms": "efficiency below the published curve at the same load",
                             "rules": ["UPS_EFFICIENCY_LOW"], "default_ramp_min": 1},
        "battery_ageing": {"name": "Battery ageing (VRLA dry-out, grid corrosion)", "part": "battery",
                           "symptoms": "block resistance up, capacity down, autonomy at the actual load below the requirement",
                           "rules": ["UPS_BATT_R_HIGH", "UPS_BATT_SOH_LOW", "UPS_AUTONOMY_SHORT"], "default_ramp_min": 1.5},
        "battery_room_hot": {"name": "Battery room too hot", "part": "battery", "symptoms": "battery temperature up, ageing twice as fast or more",
                             "rules": ["UPS_BATT_TEMP_HIGH"], "default_ramp_min": 1},
        "bypass_transfers": {"name": "Repeated transfers to static bypass", "part": "bypass", "symptoms": "bypass events counted in 30 days",
                             "rules": ["UPS_BYPASS_EVENTS"], "default_ramp_min": 0.5},
    },
    "presentation": {"title": "UPS-6101 data centre UPS", "dashboard": "UPS_DOUBLE_CONVERSION"},
}

out = HERE / "twin" / "ups-6101.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out, "loss fit a, b, c =", LOSS)
