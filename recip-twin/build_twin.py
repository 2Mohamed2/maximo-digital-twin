"""Write twin/k-2201.twin.json: the reciprocating process gas compressor twin (K-2201).

    python build_twin.py

K-2201 is the hydrogen make-up compressor of a refinery hydrotreater: an Ariel KBU/2 frame (two throws, horizontal
balanced-opposed, separable) in API 618 configuration, two stages, one double-acting cylinder per stage, driven by a
fixed-speed electric motor.

Sources (every number below is either from these or labelled as an assumption in "source"):
  Ariel KBU/KBZ product page: KBU stroke 5.75 in, frame max 1200 rpm, 2 throws 2,600 bhp, rod load ratings tension
    75,000 lbf / compression 80,000 lbf (total 150,000), piston rod 2.875 in.
  Ariel API 618 brochure: KBU in process service, typical 720 rpm, API 618 Type C distance piece, purged and
    water-cooled packing; Ariel application manual, "Process Rotative Speeds": KBU 750 rpm max in process service.
  Ariel application manual, "Ariel Calculation Method": internal pressures with typical pressure losses, suction
    preheat, Td = Tsph x Rint^((k-1)/k), gas rod loads RLc = Ahe Pdi - Ace Psi, RLt = Ace Pdi - Ahe Psi.
  Ariel application manual, "Minimum Allowable Pin Load Reversal": 30 degrees of crank angle and 25 % magnitude.
  Volumetric efficiency: textbook form VE = 1 - r/100 - C (r^(1/k) - 1) (as in the GPSA Engineering Data Book, sec. 13).
  API 618: predicted discharge temperature limit for hydrogen-rich gas (MW <= 12, lubricated cylinders) 135 C; checked
    through SH/T 3143-2012 5.3.2/5.3.3, which repeats it and puts the alarm 10 C above the maximum predicted value.
  Bores, clearances, gas data, masses, sensor baselines and alert thresholds: ASSUMPTIONS, labelled below.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with the Ariel performance run / data book of your own unit"
ARIEL = "Ariel KBU/KBZ product page (arielcorp.com)"

twin = {
    "$comment": "K-2201 reciprocating hydrogen make-up compressor twin. Expected values in Maximo Monitor from the frame and cylinder data and the gas; the device sends only what it measures.",
    "twin": {"id": "K-2201", "name": "Hydrogen make-up compressor K-2201", "version": "1.0.0", "folder": "recip-twin"},
    "identification": {
        "asset": "K-2201", "assetnum": "K-2201", "manufacturer": "Ariel", "model": "KBU/2 (API 618 configuration)",
        "description": "Hydrotreater hydrogen make-up compressor, two stages, motor driven",
        "frame": "Ariel KBU/2: 2 throws, horizontal balanced-opposed, separable, 5.75 in stroke",
        "cylinders": "Stage 1: one double-acting cylinder on throw 1; stage 2: one double-acting cylinder on throw 2",
        "driver": "Fixed-speed induction motor, 10 poles at 60 Hz (720 rpm)",
        "monitoring": "Valve cover RTDs, rod position (rod drop) probes and crosshead accelerometers to API 670; packing vent flow; lubricator divider block cycle switch",
    },
    "design": {
        "frame": {
            "model": "KBU/2", "throws": 2, "stroke_in": 5.75, "rod_diameter_in": 2.875, "rated_bhp": 2600,
            "max_rpm_frame": 1200, "max_rpm_process": 750, "rod_load_tension_lbf": 75000, "rod_load_compression_lbf": 80000,
            "rod_load_total_lbf": 150000,
            "source": ARIEL + ": stroke, rod diameter, 2-throw rated power, frame speed and internal gas rod load ratings. "
                      "Process speed limit 750 rpm: Ariel application manual, Process Rotative Speeds.",
        },
        "operation": {"rpm": 720.0, "source": "Ariel API 618 brochure: typical rotating speed of the KBU in process service 720 rpm (10-pole motor at 60 Hz)."},
        "gas": {"k": 1.40, "mw": 2.9, "z": 1.0,
                "source": "Hydrogen-rich make-up gas (about 95 % H2): ratio of specific heats, molar mass and compressibility 1 (" + A + ", from the gas analysis)."},
        "stages": [
            {"stage": 1, "throw": 1, "bore_in": 13.0, "clearance": 0.18, "ps_barg": 20.0, "ts_c": 38.0, "pd_barg": 46.0,
             "loss_suction": 0.02, "loss_discharge": 0.02, "recip_mass_kg": 180.0,
             "source": "Bore, average clearance (% of swept volume), reciprocating mass (piston, rod, crosshead) and the operating point: " + A
                       + ". Pressure losses: Ariel typical values by flange pressure (251 to 1000 psia: 2 %)."},
            {"stage": 2, "throw": 2, "bore_in": 9.0, "clearance": 0.22, "ps_barg": 45.5, "ts_c": 40.0, "pd_barg": 100.0,
             "loss_suction": 0.02, "loss_discharge": 0.01, "recip_mass_kg": 140.0,
             "source": "Bore, average clearance, reciprocating mass and the operating point: " + A
                       + ". Pressure losses: Ariel typical values (suction 675 psia: 2 %; discharge above 1001 psia: 1 %)."},
        ],
        "running_gear": {"conrod_length_m": 0.37, "reversal_min_deg": 30.0, "reversal_min_pct": 25.0,
                         "source": "Connecting rod length: " + A + ". Pin load reversal minimum 30 degrees and 25 %: Ariel application manual, Minimum Allowable Pin Load Reversal."},
        "temperature": {"td_limit_c": 135.0, "td_alarm_c": 145.0,
                        "source": "API 618: predicted discharge temperature of lubricated cylinders in hydrogen-rich service (MW <= 12) not above 135 C "
                                  "(checked through SH/T 3143-2012 5.3.2, which repeats it). Alarm 10 C above the maximum predicted value (SH/T 3143-2012 5.3.3); "
                                  "the 135 C limit is used as the maximum predicted value here (assumption)."},
        "valves": {"suction_cover_rise_k": 7.0, "discharge_cover_offset_k": -4.0,
                   "source": "A healthy suction valve cover runs a few kelvin above the suction gas (heat from the cylinder); a discharge cover a few kelvin below the gas: " + A + ", learn it from the first weeks of running."},
        "lube": {"design_cycle_s": 15.0,
                 "source": "Divider block cycle time at the lubricator setting for the normal feed rate: " + A + ", from the Ariel lube sheet of the unit."},
        "crosshead": {"baseline_g": [2.5, 2.5],
                      "source": "Crosshead guide acceleration (peak, filtered) of each throw in good condition: " + A + ", set from the commissioning baseline."},
        "packing": {"vent_normal_nm3h": 0.3, "source": "Packing vent flow of a healthy pressure packing: " + A},
        "rod_drop": {"normal_mm": 0.15, "source": "Rod position at installation of new rider bands: " + A},
        "demo": {"time_scale": 60,
                 "note": "Demo only: the plant clock runs 60 times faster. The compressor runs at a steady operating point; the failure modes ramp in over a few minutes of real time."},
    },
    "telemetry": {
        "event": "recip", "publish_every_s": 60, "device_type": "RECIP_COMPRESSOR_API618",
        "groups": {"Stage1": "Stage 1 suction and discharge", "Stage2": "Stage 2 suction and discharge", "Flow": "Make-up flow and speed",
                   "Valves": "Valve cover temperatures", "Packing": "Packing vents", "Lube": "Cylinder lubrication", "Mech": "Rod position and crosshead vibration (API 670)"},
        "points": [
            {"metric": "ps1_barg", "path": "Stage1.SuctionPressure", "label": "Stage 1 suction pressure", "unit": "bar g"},
            {"metric": "ts1_c", "path": "Stage1.SuctionTemp", "label": "Stage 1 suction temperature", "unit": "°C"},
            {"metric": "pd1_barg", "path": "Stage1.DischargePressure", "label": "Stage 1 discharge pressure", "unit": "bar g"},
            {"metric": "td1_c", "path": "Stage1.DischargeTemp", "label": "Stage 1 discharge temperature", "unit": "°C"},
            {"metric": "ps2_barg", "path": "Stage2.SuctionPressure", "label": "Stage 2 suction pressure (after the interstage cooler)", "unit": "bar g"},
            {"metric": "ts2_c", "path": "Stage2.SuctionTemp", "label": "Stage 2 suction temperature", "unit": "°C"},
            {"metric": "pd2_barg", "path": "Stage2.DischargePressure", "label": "Stage 2 discharge pressure", "unit": "bar g"},
            {"metric": "td2_c", "path": "Stage2.DischargeTemp", "label": "Stage 2 discharge temperature", "unit": "°C"},
            {"metric": "flow_nm3h", "path": "Flow.MakeUp", "label": "Make-up hydrogen flow", "unit": "Nm³/h"},
            {"metric": "speed_rpm", "path": "Flow.Speed", "label": "Compressor speed", "unit": "rpm"},
            {"metric": "tv1_he_s_c", "path": "Valves.C1HeadSuction", "label": "Cylinder 1 head end suction valve cover", "unit": "°C"},
            {"metric": "tv1_he_d_c", "path": "Valves.C1HeadDischarge", "label": "Cylinder 1 head end discharge valve cover", "unit": "°C"},
            {"metric": "tv1_ce_s_c", "path": "Valves.C1CrankSuction", "label": "Cylinder 1 crank end suction valve cover", "unit": "°C"},
            {"metric": "tv1_ce_d_c", "path": "Valves.C1CrankDischarge", "label": "Cylinder 1 crank end discharge valve cover", "unit": "°C"},
            {"metric": "tv2_he_s_c", "path": "Valves.C2HeadSuction", "label": "Cylinder 2 head end suction valve cover", "unit": "°C"},
            {"metric": "tv2_he_d_c", "path": "Valves.C2HeadDischarge", "label": "Cylinder 2 head end discharge valve cover", "unit": "°C"},
            {"metric": "tv2_ce_s_c", "path": "Valves.C2CrankSuction", "label": "Cylinder 2 crank end suction valve cover", "unit": "°C"},
            {"metric": "tv2_ce_d_c", "path": "Valves.C2CrankDischarge", "label": "Cylinder 2 crank end discharge valve cover", "unit": "°C"},
            {"metric": "packing_vent1_nm3h", "path": "Packing.Vent1", "label": "Packing vent flow, throw 1", "unit": "Nm³/h"},
            {"metric": "packing_vent2_nm3h", "path": "Packing.Vent2", "label": "Packing vent flow, throw 2", "unit": "Nm³/h"},
            {"metric": "lube_cycle_s", "path": "Lube.CycleTime", "label": "Cylinder lubricator divider block cycle time", "unit": "s"},
            {"metric": "rod_drop1_mm", "path": "Mech.RodDrop1", "label": "Rod drop (rider band wear), throw 1", "unit": "mm"},
            {"metric": "rod_drop2_mm", "path": "Mech.RodDrop2", "label": "Rod drop (rider band wear), throw 2", "unit": "mm"},
            {"metric": "xhead_acc1_g", "path": "Mech.Crosshead1", "label": "Crosshead guide acceleration, throw 1 (peak)", "unit": "g"},
            {"metric": "xhead_acc2_g", "path": "Mech.Crosshead2", "label": "Crosshead guide acceleration, throw 2 (peak)", "unit": "g"},
        ],
    },
    "twin_model": {
        "limits": {
            "rod_load_alert_pct": 85.0, "rod_load_limit_pct": 100.0, "td_residual_alert_k": 8.0,
            "suction_cover_rise_alert_k": 20.0, "discharge_cover_dev_alert_k": 15.0, "valve_peer_spread_alert_k": 10.0,
            "capacity_ratio_alert": 0.92, "packing_vent_alert_nm3h": 1.5, "lube_rate_ratio_alert": 0.75,
            "rod_drop_alert_mm": 1.0, "xhead_ratio_alert": 2.0,
            "source": "Rod load limits: Ariel ratings (100 %) with an 85 % alert (assumption). Every other threshold: " + A
                      + "; rod drop alert at half of an assumed 2 mm rider band wear allowance.",
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "discharge_valve_leak": {"name": "Leaking discharge valve, cylinder 1 head end", "part": "valves",
                                 "symptoms": "that discharge cover runs hot, stage 1 discharge hotter than expected, capacity down",
                                 "rules": ["RECIP_DISCHARGE_VALVE_LEAK", "RECIP_VALVE_PEER_SPREAD", "RECIP_TD_DEVIATION_S1", "RECIP_CAPACITY_LOW"], "default_ramp_min": 1.5},
        "suction_valve_leak": {"name": "Leaking suction valve, cylinder 2 crank end", "part": "valves",
                               "symptoms": "that suction cover far above the suction gas, stage 2 discharge hotter, interstage pressure up",
                               "rules": ["RECIP_SUCTION_VALVE_LEAK", "RECIP_VALVE_PEER_SPREAD", "RECIP_TD_DEVIATION_S2"], "default_ramp_min": 1.5},
        "ring_wear": {"name": "Piston ring wear, stage 2", "part": "cylinder",
                      "symptoms": "stage 2 discharge hotter than expected, every cover of the cylinder a little warmer, no single hot valve",
                      "rules": ["RECIP_TD_DEVIATION_S2"], "default_ramp_min": 1.5},
        "packing_leak": {"name": "Pressure packing leak, throw 2", "part": "packing", "symptoms": "packing vent flow up",
                         "rules": ["RECIP_PACKING_LEAK"], "default_ramp_min": 1},
        "lube_starvation": {"name": "Cylinder lubrication starved", "part": "lube", "symptoms": "divider block cycles slower than set",
                            "rules": ["RECIP_LUBE_LOW"], "default_ramp_min": 1},
        "rider_band_wear": {"name": "Rider band wear, throw 1", "part": "cylinder", "symptoms": "rod drop grows",
                            "rules": ["RECIP_ROD_DROP"], "default_ramp_min": 1.5},
        "crosshead_wear": {"name": "Crosshead pin or shoe clearance, throw 2", "part": "running gear", "symptoms": "crosshead impacts at reversal grow",
                           "rules": ["RECIP_XHEAD_VIB"], "default_ramp_min": 1},
        "discharge_pressure_high": {"name": "Discharge pressure too high (downstream restriction)", "part": "process",
                                    "symptoms": "stage 2 ratio, discharge temperature and gas rod load up together, residuals normal",
                                    "rules": ["RECIP_ROD_LOAD_HIGH"], "default_ramp_min": 1},
    },
    "presentation": {"title": "K-2201 hydrogen make-up compressor", "dashboard": "RECIP_COMPRESSOR_API618"},
}

out = HERE / "twin" / "k-2201.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
