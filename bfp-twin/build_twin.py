"""Write twin/bfp-3301.twin.json: the boiler feed pump twin (BFP-3301).

    python build_twin.py

BFP-3301 is boiler feed pump A of a steam power unit (two 50 % pumps in parallel). It is a multistage barrel-type
pump (KSB CHTR, API 610 / ISO 13709 type BB5) with a balance drum, driven by an electric motor on a variable speed
drive (VSD) through a step-up gearbox. It takes saturated water from the deaerator, which stands about 25 m above the
pump, and sends it through the HP heaters to the boiler drum. A minimum-flow (recirculation) valve on the discharge
returns water to the deaerator when the flow through the pump falls too low; the balance drum leak-off also returns
to the deaerator through its own flow meter.

Sources and assumptions (every number below is either published or labelled as an assumption in "source"):
  KSB CHTR leaflet 2701.022/01-EN (11.25) and KSB product page: horizontal radially split multistage barrel pump to
    API 610 (ISO 13709) type BB5, balance drum for the axial thrust, first stage optionally double suction for low NPSH,
    flow <= 1450 m3/h at 50 Hz, head <= 4000 m, <= 400 bar, speed 7000 rpm (envelope only: KSB publishes no curve
    for a single size, so the duty point and the curves below are ASSUMPTIONS of a typical size, to be replaced by
    the certified performance curve of your pump).
  ISO 5198:1987 clause 11 (thermodynamic method): Eh = Vm (p2 - p1), Em = a (p2 - p1) + cp (T2 - T1), eta = Eh / Em
    (kinetic, elevation and secondary terms left out here); a, cp and density of water at 100 bar from its tables 15,
    16 and 17 (150, 160 and 170 degC), linearised around 160 degC.
  Vapour pressure of water: Antoine equation, constants for 99 to 374 degC (A 8.14019, B 1810.94, C 244.485, mmHg, degC).
  Affinity laws (Q ~ n, H ~ n^2, P ~ n^3, NPSH ~ n^2): textbook.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with "
KSB = ("KSB CHTR barrel pull-out pump: leaflet 2701.022/01-EN (11.25) and product page https://www.ksb.com/en-ro/lc/C38A "
       "(API 610 / ISO 13709 type BB5, balance drum, flow <= 1450 m3/h, head <= 4000 m, <= 400 bar, 7000 rpm)")
ISO = "ISO 5198:1987, clause 11 and tables 15 (isothermal factor a), 16 (density) and 17 (cp), column 100 bar"

twin = {
    "$comment": "BFP-3301 boiler feed pump twin. Expected values in Maximo Monitor from the pump curves, the affinity laws, the ISO 5198 thermodynamic method and the plant design; the device sends only what it measures.",
    "twin": {"id": "BFP-3301", "name": "Boiler feed pump BFP-3301", "version": "1.0.0", "folder": "bfp-twin"},
    "identification": {
        "asset": "BFP-3301", "assetnum": "BFP-3301", "manufacturer": "KSB",
        "model": "CHTR barrel pull-out pump (API 610 type BB5), size and stages as an assumed selection",
        "description": "Boiler feed pump A (2 x 50 %) of a steam power unit, VSD motor drive, balance drum leak-off and minimum-flow valve",
        "pump": "KSB CHTR, multistage barrel type, double-suction first stage, balance drum, 6 stages (assumed selection)",
        "drive": "Medium-voltage induction motor on a variable speed drive, step-up gearbox to pump speed",
        "minflow": "Automatic recirculation (minimum-flow) control valve on the discharge, back to the deaerator",
        "balance": "Balance drum leak-off line back to the deaerator with its own flow meter",
        "bearings": "Two journal bearings and a tilting-pad thrust bearing, forced-oil lubrication",
    },
    "design": {
        "pump": {
            "rated_rpm": 5300.0, "q_bep_m3h": 520.0, "h_bep_m": 2050.0, "h_shutoff_m": 2520.0, "eff_bep": 0.81,
            "stages": 6, "q_min_frac": 0.35, "npsh3_bep_m": 14.0, "npsh3_shape": [0.5, 0.5],
            "source": KSB + ". The duty point inside that envelope is an " + A + "the certified test curve of your pump: BEP "
                      "520 m3/h and 2,050 m at 5,300 rpm, 81 % efficiency, shut-off head 2,520 m (1.23 x BEP head), head curve "
                      "H = H0 + h2 Q^2 through those two points, efficiency curve eta_BEP x (2x - x^2) with x = Q / Q_BEP, "
                      "NPSH3 = 14 m x (0.5 + 0.5 x^2) at BEP speed (double-suction first stage), minimum continuous flow 35 % "
                      "of the BEP flow at the same speed.",
        },
        "balance": {"leakoff_m3h": 15.0, "dp_ref_bar": 183.0,
                    "source": A + "the pump vendor's balance drum leak-off figure at the rated differential pressure (here about "
                                  "3 % of the BEP flow). Leak-off through the drum clearance grows with the square root of the "
                                  "pressure across it."},
        "drive": {"eff_motor_gear": 0.955, "rated_kw": 4000.0,
                  "source": A + "the motor and gearbox data sheets (motor 97 % x gearbox 98.5 %), measured as VSD output power."},
        "water": {"t_ref_c": 160.0, "rho_ref": 913.0, "rho_slope": -0.98, "a_ref": 0.5973e-3, "a_slope": -0.00328e-3,
                  "cp_ref": 4303.7, "cp_slope": 2.74, "antoine": [8.14019, 1810.94, 244.485],
                  "source": ISO + ": rho 913.0 kg/m3 at 160 degC (903.2 at 170), a 0.6286 / 0.5973 / 0.5630 x 1e-3 m3/kg at 150 / 160 / "
                            "170 degC, cp 4277.8 / 4303.7 / 4332.6 J/(kg K): straight lines through them. Vapour pressure: Antoine "
                            "equation for water, 99 to 374 degC, log10(p mmHg) = 8.14019 - 1810.94 / (244.485 + T degC)."},
        "suction": {"deaerator_elev_m": 25.0, "level_normal_m": 1.5, "da_pressure_bar": 5.12, "pipe_loss_bep_m": 1.2,
                    "strainer_dp_clean_bar": 0.04,
                    "source": A + "the plant layout (deaerator storage tank floor 25 m above the pump suction), the deaerator "
                                  "normal level and operating pressure (5.12 bar g, saturated at 160 degC), the suction pipe loss "
                                  "at the BEP flow and the clean strainer pressure drop."},
        "system": {"h_static_m": 1760.0, "h_at_rated_m": 2000.0, "q_rated_m3h": 500.0, "unit_mw": 300.0, "load_flow_m3h": 425.0,
                   "source": A + "the feedwater system: head the pump must give to put the rated 500 m3/h per pump into the boiler "
                                 "drum (static part: drum pressure and elevation), a 300 MW unit, this pump carrying half the feed."},
        "bearings": {"oil_c": 45.0, "thrust_rise_k": 30.0, "journal_rise_k": 22.0, "vib_base_mm_s": 2.0,
                     "source": A + "the commissioning values of your pump: bearing temperature rise above the oil supply at rated "
                                   "speed (scaled with speed squared) and the bearing housing vibration."},
        "demo": {"time_scale": 1, "note": "Demo only: the plant runs in real time; faults ramp in over a minute or so."},
    },
    "telemetry": {
        "event": "bfp", "publish_every_s": 10, "device_type": "BOILER_FEED_PUMP",
        "groups": {"Pump": "Pump flows, pressures and temperatures", "Drive": "VSD and motor", "Deaerator": "Deaerator (suction source)",
                   "Bearings": "Bearings and vibration", "Unit": "Unit"},
        "points": [
            {"metric": "running", "path": "Drive.Running", "label": "Pump running (1 = yes)", "unit": "code"},
            {"metric": "speed_rpm", "path": "Drive.PumpSpeed", "label": "Pump shaft speed", "unit": "rpm"},
            {"metric": "motor_kw", "path": "Drive.Power", "label": "VSD output power to the motor", "unit": "kW"},
            {"metric": "suction_flow_m3h", "path": "Pump.SuctionFlow", "label": "Flow into the pump (suction flow meter)", "unit": "m³/h"},
            {"metric": "suction_pressure_bar", "path": "Pump.SuctionPressure", "label": "Suction pressure", "unit": "bar g"},
            {"metric": "discharge_pressure_bar", "path": "Pump.DischargePressure", "label": "Discharge pressure", "unit": "bar g"},
            {"metric": "suction_temp_c", "path": "Pump.SuctionTemperature", "label": "Suction temperature (precision RTD)", "unit": "°C"},
            {"metric": "discharge_temp_c", "path": "Pump.DischargeTemperature", "label": "Discharge temperature (precision RTD)", "unit": "°C"},
            {"metric": "leakoff_flow_m3h", "path": "Pump.BalanceLeakoff", "label": "Balance drum leak-off flow", "unit": "m³/h"},
            {"metric": "recirc_valve_pct", "path": "Pump.RecircValve", "label": "Minimum-flow valve position (0 = closed)", "unit": "%"},
            {"metric": "recirc_flow_m3h", "path": "Pump.RecircFlow", "label": "Recirculation flow back to the deaerator", "unit": "m³/h"},
            {"metric": "strainer_dp_bar", "path": "Pump.StrainerDP", "label": "Suction strainer differential pressure", "unit": "bar"},
            {"metric": "da_pressure_bar", "path": "Deaerator.Pressure", "label": "Deaerator pressure", "unit": "bar g"},
            {"metric": "da_level_m", "path": "Deaerator.Level", "label": "Deaerator storage tank level", "unit": "m"},
            {"metric": "bearing_de_c", "path": "Bearings.DriveEnd", "label": "Drive-end journal bearing temperature", "unit": "°C"},
            {"metric": "bearing_nde_c", "path": "Bearings.NonDriveEnd", "label": "Non-drive-end journal bearing temperature", "unit": "°C"},
            {"metric": "thrust_bearing_c", "path": "Bearings.Thrust", "label": "Thrust bearing pad temperature (active side)", "unit": "°C"},
            {"metric": "lube_oil_c", "path": "Bearings.OilSupply", "label": "Lube oil supply temperature", "unit": "°C"},
            {"metric": "vibration_mm_s", "path": "Bearings.Vibration", "label": "Bearing housing vibration, highest (RMS velocity)", "unit": "mm/s"},
            {"metric": "unit_load_mw", "path": "Unit.Load", "label": "Unit electrical load", "unit": "MW"},
        ],
    },
    "twin_model": {
        "limits": {
            "head_low": 0.95, "eff_low": 0.95, "eff_loss": 0.90, "leakoff_alert": 1.5, "leakoff_limit": 2.0,
            "npsh_alert": 1.5, "npsh_limit": 1.2, "strainer_dp_bar": 0.5, "flow_mismatch": 0.08,
            "recirc_closed_pct": 2.0, "recirc_passing_m3h": 20.0, "thrust_excess_k": 10.0, "journal_excess_k": 10.0,
            "vib_alert_mm_s": 4.5, "vib_limit_mm_s": 7.1,
            "source": A + "your own operating practice and the vendor's limits. Head and efficiency 5 % / 10 % below the curve, "
                      "leak-off 1.5 x / 2 x the expected value, NPSH margin ratio 1.5 / 1.2, strainer 0.5 bar, flow meter and "
                      "thermodynamic flow 8 % apart, bearing 10 K above the commissioning rise, vibration 4.5 / 7.1 mm/s (check "
                      "the ISO 10816-7 zone limits for your pump category and power).",
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "impeller_wear": {"name": "Impeller and wear-ring wear (internal recirculation)", "part": "pump",
                          "symptoms": "head and thermodynamic efficiency down at the same flow and speed, VSD speed up to keep the feed flow",
                          "rules": ["BFP_HEAD_LOW", "BFP_EFF_LOW", "BFP_EFF_LOSS_HIGH"], "default_ramp_min": 1.5},
        "balance_drum_wear": {"name": "Balance drum clearance wear", "part": "balance drum",
                              "symptoms": "leak-off flow up against the expected value, thrust bearing hotter, efficiency slightly down",
                              "rules": ["BFP_LEAKOFF_HIGH", "BFP_LEAKOFF_LIMIT", "BFP_THRUST_TEMP_HIGH"], "default_ramp_min": 1.5},
        "minflow_valve_stuck": {"name": "Minimum-flow valve fails to open at low load", "part": "recirculation valve",
                                "symptoms": "unit load falls, valve stays shut, flow through the pump below its minimum (demo lowers the load)",
                                "rules": ["BFP_MIN_FLOW_LOW"], "default_ramp_min": 1},
        "recirc_valve_passing": {"name": "Minimum-flow valve passing (seat leak)", "part": "recirculation valve",
                                 "symptoms": "recirculation flow with the valve shut, more speed and power for the same feed",
                                 "rules": ["BFP_RECIRC_PASSING"], "default_ramp_min": 1},
        "npsh_loss": {"name": "NPSH loss: deaerator pressure decay and low level (cavitation)", "part": "suction",
                      "symptoms": "deaerator pressure falls faster than the suction water cools, level low, NPSH margin gone, vibration up",
                      "rules": ["BFP_NPSH_MARGIN_LOW", "BFP_NPSH_MARGIN_LIMIT", "BFP_VIBRATION_HIGH"], "default_ramp_min": 1},
        "strainer_clogging": {"name": "Suction strainer clogging", "part": "suction",
                              "symptoms": "strainer differential pressure up, suction pressure and NPSH margin down",
                              "rules": ["BFP_STRAINER_DP_HIGH", "BFP_NPSH_MARGIN_LOW"], "default_ramp_min": 1.5},
        "bearing_degradation": {"name": "Journal bearing degradation", "part": "bearings",
                                "symptoms": "journal bearing temperature above its normal rise, vibration up",
                                "rules": ["BFP_JOURNAL_TEMP_HIGH", "BFP_VIBRATION_HIGH", "BFP_VIBRATION_LIMIT"], "default_ramp_min": 1.5},
        "flow_meter_drift": {"name": "Suction flow transmitter drift", "part": "instrument",
                             "symptoms": "metered flow disagrees with the flow from shaft power and thermodynamic efficiency",
                             "rules": ["BFP_FLOW_MISMATCH"], "default_ramp_min": 1},
    },
    "presentation": {"title": "BFP-3301 boiler feed pump", "dashboard": "BOILER_FEED_PUMP"},
}

out = HERE / "twin" / "bfp-3301.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
