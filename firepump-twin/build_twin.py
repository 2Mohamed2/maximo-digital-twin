"""Write twin/fp-6501.twin.json: the electric fire pump twin (FP-6501).

    python build_twin.py

FP-6501 is the fire pump of a sprinkler and standpipe system: an A-C Fire Pump 8100 Series 8x6x18F horizontal split-case
pump (curve A-8853, 1780 rpm, 1000 gpm, UL listed / FM approved pressure range 72-122 psi for this casing), driven by a
125 hp electric motor through a flexible coupling, started by a listed electric fire pump controller, with a small jockey
(pressure maintenance) pump that keeps the system full and pressurised.

Sources and assumptions (every number below is either from a document that was checked or labelled as an assumption):
  A-C Fire Pump performance curve A-8853 (8x6x18F, 8100 Series, 1780 rpm, 1000 GPM, FP 2.0, October 2012), PDF on the maker's
  web page: impeller diameters 13.0 to 17.2 in, 6 vanes, approval pressure range 72-122 psi UL & FM. The head and BHP points of
  the 16 in impeller (curve "B") were READ FROM THE CURVE IMAGE (about +/- 1.5 psi and +/- 2 hp): they are not a table published
  by the maker. Replace them with the certified test curve that ships with your own pump (serial number).
  NFPA 20: shut-off head not above 140 % of rated head; at least 150 % of rated capacity at not less than 65 % of rated head.
  NFPA 20 annex: jockey stop = churn + minimum static suction; jockey start >= 10 psi below stop; fire pump start 5 psi below
  the jockey start.
  NFPA 25: annual flow test at churn, 100 % and 150 % of rated flow; speed-corrected net pressure at each point at least 95 %
  of the reference curve (manufacturer's curve, original unadjusted field acceptance test or nameplate, depending on edition).
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent

A = "assumption: typical value, replace with "
CURVE_SRC = ("A-C Fire Pump curve A-8853 (8x6x18F, 8100 Series, 1780 rpm, 1000 GPM), 16 in impeller (curve B): points read from "
             "the published curve image, about +/- 1.5 psi / +/- 2 hp. Replace with the certified shop test curve of your pump.")

# Curve B (16 in impeller) read from curve A-8853: flow gpm -> total head psi, and -> brake horsepower
Q = [0, 250, 500, 750, 1000, 1250, 1500, 1750, 2000]
H = [112.8, 113.1, 112.2, 110.1, 107.1, 101.8, 94.9, 85.3, 72.7]
P = [48.3, 57.3, 69.1, 81.3, 92.7, 101.7, 107.8, 111.1, 112.2]
qs = np.array(Q, float) / 1000.0           # fit in thousands of gpm for well-conditioned coefficients
h3 = np.polyfit(qs, H, 3)[::-1]            # h0 + h1 q + h2 q^2 + h3 q^3, q in kgpm
p3 = np.polyfit(qs, P, 3)[::-1]
fitH = [float(np.polyval(h3[::-1], q)) for q in qs]
res = max(abs(a - b) for a, b in zip(fitH, H))

rated_q, rated_n = 1000.0, 1780.0
rated_p = round(float(np.polyval(h3[::-1], 1.0)), 1)
churn = round(float(h3[0]), 1)
min_static = 50.0
j_stop = round(churn + min_static)
j_start = j_stop - 10
fp_start = j_start - 5

twin = {
    "$comment": "FP-6501 fire pump twin. Expected values in Maximo Monitor from the listed pump curve, NFPA 20 / NFPA 25 rules and the controller settings; the controller and the test rig send only what they measure.",
    "twin": {"id": "FP-6501", "name": "Fire pump FP-6501", "version": "1.0.0", "folder": "firepump-twin"},
    "identification": {
        "asset": "FP-6501", "assetnum": "FP-6501", "manufacturer": "A-C Fire Pump",
        "model": "8100 Series 8x6x18F horizontal split-case fire pump, curve A-8853, 16 in impeller",
        "description": "Electric fire pump of the sprinkler and standpipe system of a distribution warehouse (one pump, city water supply)",
        "driver": "125 hp, 1780 rpm, 460 V 3-phase induction motor (open drip-proof), flexible coupling",
        "controller": "Listed electric fire pump controller, across-the-line start, pressure transducer and event log",
        "jockey": "Vertical multistage jockey (pressure maintenance) pump with its own controller",
        "listing": "UL listed and FM approved for 1000 gpm at 72-122 psi (8x6x18F casing, per curve A-8853)",
    },
    "design": {
        "pump": {
            "rated_flow_gpm": rated_q, "rated_speed_rpm": rated_n, "rated_net_psi": rated_p, "impeller_in": 16.0,
            "impeller_max_in": 17.2, "impeller_min_in": 13.0, "vanes": 6, "approval_range_psi": [72, 122],
            "curve_flow_gpm": Q, "curve_head_psi": H, "curve_bhp": P,
            "head_poly_kgpm": [round(float(c), 6) for c in h3], "bhp_poly_kgpm": [round(float(c), 6) for c in p3],
            "fit_max_residual_psi": round(res, 2),
            "source": CURVE_SRC + " Rated pressure = the curve at 1000 gpm; the fit is a cubic in thousands of gpm (largest residual "
                      f"{res:.2f} psi). The curve is total head in psi; the twin uses it as net pressure (discharge - suction), as NFPA 25 "
                      "test sheets do, and neglects the velocity pressure difference between the 8 in and 6 in flanges.",
        },
        "nfpa20": {"churn_max_pct": 140.0, "peak_flow_pct": 150.0, "peak_min_pct": 65.0,
                   "source": "NFPA 20 (Installation of Stationary Pumps for Fire Protection): shut-off head not above 140 % of rated head; "
                             "150 % of rated capacity at not less than 65 % of rated head."},
        "nfpa25": {"min_ratio": 0.95, "churn_test_interval_days": 7, "flow_test_interval_days": 365, "electric_min_run_min": 10,
                   "source": "NFPA 25 (Inspection, Testing and Maintenance of Water-Based Fire Protection Systems): annual flow test at churn, "
                             "100 % and 150 %; speed-corrected net pressure at least 95 % of the reference curve; electric no-flow test of at "
                             "least 10 min. NFPA 25 allows a MONTHLY no-flow test for most electric pumps; this site keeps a weekly test "
                             "(site programme, the twin's interval)."},
        "motor": {"rated_hp": 125.0, "fla_a": 156.0, "voltage_v": 460.0, "efficiency": 0.945, "power_factor": 0.87,
                  "service_factor": 1.15,
                  "source": A + "the motor nameplate. 125 hp is chosen above the 16 in curve's largest power (about 112 bhp); full-load "
                            "current, efficiency and power factor are typical of a 125 hp 460 V 4-pole motor."},
        "settings": {"churn_psi": churn, "min_static_suction_psi": min_static, "nominal_static_suction_psi": 55.0,
                     "jockey_stop_psi": j_stop, "jockey_start_psi": j_start, "fire_pump_start_psi": fp_start,
                     "time_to_run_s": 4.0, "jockey_flow_gpm": 10.0,
                     "source": "NFPA 20 annex method: jockey stop = churn (curve at 0 gpm) + minimum static suction; jockey start 10 psi below "
                               "the stop; fire pump start 5 psi below the jockey start. Minimum and nominal static suction of the city main, "
                               "normal time to run of an across-the-line start and the jockey pump flow: " + A + "the water authority's "
                               "flow test, the controller's commissioning record and the jockey pump data sheet."},
        "supply": {"residual_at_peak_psi": 32.0, "suction_min_psi": 20.0,
                   "source": "Suction pressure at 150 % flow during the acceptance test, and the minimum the water authority allows at the "
                             "suction flange: " + A + "your water authority's limit. NFPA 20 is commonly quoted as allowing the suction "
                             "pressure to fall to 0 psi at 150 % flow; many authorities ask for 20 psi."},
        "demo": {"time_scale": 60, "churn_every_s": 60, "churn_run_s": 20,
                 "note": "Demo only: the controller runs a no-flow (churn) test every 60 s of real time instead of every week, and the "
                         "stored annual flow test follows the injected fault directly, as if the test were repeated."},
    },
    "telemetry": {
        "event": "firepump", "publish_every_s": 10, "device_type": "FIRE_PUMP_ELECTRIC",
        "groups": {"Pump": "Pump pressures, flow and speed", "Motor": "Motor supply", "Controller": "Fire pump controller",
                   "Jockey": "Jockey pump and system", "Churn": "Last no-flow (churn) test", "FlowTest": "Last annual flow test",
                   "Room": "Pump room", "Test": "Test calendar"},
        "points": [
            {"metric": "suction_psi", "path": "Pump.Suction", "label": "Suction pressure", "unit": "psi"},
            {"metric": "discharge_psi", "path": "Pump.Discharge", "label": "Discharge pressure (= system pressure at standby)", "unit": "psi"},
            {"metric": "flow_gpm", "path": "Pump.Flow", "label": "Flow through the test meter (0 at churn and standby)", "unit": "gpm"},
            {"metric": "speed_rpm", "path": "Pump.Speed", "label": "Pump speed", "unit": "rpm"},
            {"metric": "pump_running", "path": "Controller.Running", "label": "Fire pump running (1 = running)", "unit": "code"},
            {"metric": "motor_current_a", "path": "Motor.Current", "label": "Motor current (average of 3 phases)", "unit": "A"},
            {"metric": "supply_voltage_v", "path": "Motor.Voltage", "label": "Supply voltage at the controller", "unit": "V"},
            {"metric": "last_start_psi", "path": "Controller.StartPressure", "label": "System pressure at the last automatic start", "unit": "psi"},
            {"metric": "time_to_run_s", "path": "Controller.TimeToRun", "label": "Last start: start signal to motor running", "unit": "s"},
            {"metric": "auto_starts_30d", "path": "Controller.AutoStarts30d", "label": "Automatic starts on low pressure, not tests, last 30 days", "unit": "count"},
            {"metric": "jockey_starts_24h", "path": "Jockey.Starts24h", "label": "Jockey pump starts, last 24 h", "unit": "count"},
            {"metric": "jockey_run_min_24h", "path": "Jockey.RunMinutes24h", "label": "Jockey pump running time, last 24 h", "unit": "min"},
            {"metric": "churn_net_psi", "path": "Churn.NetPressure", "label": "Net pressure at the end of the last churn test", "unit": "psi"},
            {"metric": "churn_rpm", "path": "Churn.Speed", "label": "Speed during the last churn test", "unit": "rpm"},
            {"metric": "churn_packing_c", "path": "Churn.PackingTemp", "label": "Packing gland temperature at the end of the last churn test", "unit": "°C"},
            {"metric": "ft_rated_gpm", "path": "FlowTest.RatedFlow", "label": "Annual test, 100 % point: flow", "unit": "gpm"},
            {"metric": "ft_rated_net_psi", "path": "FlowTest.RatedNet", "label": "Annual test, 100 % point: net pressure", "unit": "psi"},
            {"metric": "ft_rated_rpm", "path": "FlowTest.RatedSpeed", "label": "Annual test, 100 % point: speed", "unit": "rpm"},
            {"metric": "ft_peak_gpm", "path": "FlowTest.PeakFlow", "label": "Annual test, 150 % point: flow", "unit": "gpm"},
            {"metric": "ft_peak_net_psi", "path": "FlowTest.PeakNet", "label": "Annual test, 150 % point: net pressure", "unit": "psi"},
            {"metric": "ft_peak_rpm", "path": "FlowTest.PeakSpeed", "label": "Annual test, 150 % point: speed", "unit": "rpm"},
            {"metric": "ft_peak_suction_psi", "path": "FlowTest.PeakSuction", "label": "Annual test, 150 % point: suction pressure", "unit": "psi"},
            {"metric": "room_temp_c", "path": "Room.Temperature", "label": "Pump room temperature", "unit": "°C"},
            {"metric": "days_since_churn", "path": "Test.DaysSinceChurn", "label": "Days since the last churn test", "unit": "d"},
            {"metric": "days_since_flow_test", "path": "Test.DaysSinceFlowTest", "label": "Days since the last annual flow test", "unit": "d"},
        ],
    },
    "twin_model": {
        "limits": {
            "curve_ratio_min": 0.95, "churn_dev_max": 0.05, "peak_min_pct": 65.0, "suction_min_psi": 20.0,
            "static_suction_alert_psi": 45.0, "jockey_starts_max": 24, "leak_gpm_max": 1.0, "start_psi_dev_max": 5.0,
            "time_to_run_max_s": 10.0, "packing_max_c": 70.0, "room_min_c": 4.4, "churn_overdue_days": 10, "flow_test_overdue_days": 395,
        },
        "source": "95 % (NFPA 25) and 65 % (NFPA 20) are from the standards. Room 4.4 °C (40 °F) is the pump-room minimum commonly applied "
                  "for electric pumps in NFPA 25 weekly inspections. Every other limit: " + A + "your own maintenance strategy.",
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "impeller_wear": {"name": "Impeller and wear-ring wear", "part": "pump",
                          "symptoms": "churn pressure a few % low; annual test points fall below 95 % of the curve, most at 150 %",
                          "rules": ["FP_CHURN_DEVIATION", "FP_CURVE_DEGRADED"], "default_ramp_min": 1.5},
        "weak_supply": {"name": "Weak water supply or partly closed suction valve", "part": "supply",
                        "symptoms": "static suction low; suction at 150 % flow below the authority minimum", "rules": ["FP_SUPPLY_STATIC_LOW", "FP_SUCTION_LOW_TEST"],
                        "default_ramp_min": 1},
        "system_leak": {"name": "Leak in the sprinkler system", "part": "system", "symptoms": "jockey pump starts many times a day; make-up flow above 1 gpm",
                        "rules": ["FP_JOCKEY_CYCLING", "FP_LEAK_HIGH"], "default_ramp_min": 1},
        "jockey_failed": {"name": "Jockey pump failed", "part": "jockey", "symptoms": "no jockey starts, system pressure below the jockey start; the fire pump starts on its own",
                          "rules": ["FP_JOCKEY_FAILED", "FP_UNPLANNED_STARTS"], "default_ramp_min": 0.5},
        "pressure_sensing_drift": {"name": "Controller pressure transducer drift", "part": "controller",
                                   "symptoms": "the fire pump starts far from its set pressure", "rules": ["FP_START_PRESSURE_OFF"], "default_ramp_min": 1},
        "starter_fault": {"name": "Starter or contactor fault", "part": "controller", "symptoms": "time from start signal to running grows",
                          "rules": ["FP_START_SLOW"], "default_ramp_min": 1},
        "packing_overtight": {"name": "Packing overtightened or dry", "part": "pump", "symptoms": "no drip at the glands, packing hot at the end of the churn test",
                              "rules": ["FP_PACKING_HOT"], "default_ramp_min": 1},
        "tests_skipped": {"name": "Churn and flow tests skipped", "part": "testing", "symptoms": "days since the last churn test and the last flow test grow",
                          "rules": ["FP_CHURN_TEST_OVERDUE", "FP_FLOW_TEST_OVERDUE"], "default_ramp_min": 1},
    },
    "presentation": {"title": "FP-6501 electric fire pump", "dashboard": "FIRE_PUMP_ELECTRIC"},
}
twin["identification"]["pump"] = ("Horizontal split-case, single stage, 8x6 casing (8 in suction, 6 in discharge), 6-vane impeller trimmed to 16 in "
                                  "(the trim is an assumption: replace with your pump's nameplate)")

out = HERE / "twin" / "fp-6501.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out, f"rated {rated_p} psi, churn {churn} psi, settings {j_stop}/{j_start}/{fp_start}, fit residual {res:.2f} psi")
