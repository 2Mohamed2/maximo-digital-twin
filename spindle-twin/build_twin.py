"""Write twin/mc-4801.twin.json: the CNC machining centre main spindle twin (MC-4801).

    python build_twin.py

MC-4801 is the main spindle of a vertical machining centre in a job shop: a GMN HCS 230 - 20000/40 HSK-A63 motor spindle
(built-in motor, angular contact ball bearings with oil-air lubrication, automatic HSK-A63 tool clamping, water-cooled
housing). The CNC publishes spindle speed, drive power, the active tool and the cut it is making (MTConnect or OPC UA for
Machine Tools); the spindle's own sensors add bearing and motor temperatures, a thermal growth sensor, vibration, the
clamping force at each tool change and a shock (crash) sensor.

Sources (public):
  GMN milling spindles page, HCS series table (gmn.de): HCS 230 - 20000 / 40: max. speed 20,000 rpm, power 40 kW at
      4,500 rpm, torque 85 Nm, housing 230 mm, bearing bore 70 mm, lubrication OL (oil-air), tool interface HSK-A 63.
  GMN data sheet of the sister spindle HCS 230 - 20000/25 HSK-A63 (copy on sparepartsnow.de): motor protection PT1000,
      oil-air lubrication, bearing temperature monitoring at the first bearing, OTT clamping system HSK-A63 (DIN 69893),
      rotary union, encoder. Used for the sensor list only; its power figures are not used.
  Roehm HSK brochure: HSK A63 clamping sets, actuating force 6 kN, clamping force 18 kN.
  Sandvik Coromant "Formulas and definitions for milling" (metric): net power Pc = ae ap vf kc / (60 x 10^6) kW,
      torque Mc = Pc x 30 x 10^3 / (pi n) Nm, metal removal rate Q = ap ae vf / 1000 cm3/min.
  Kienzle specific cutting force (textbook): kc = kc1.1 x h^(-mc) x (1 - gamma0 / 100); mean chip thickness over the
      engagement arc from geometry: hm = fz (1 - cos phi) / phi, cos phi = 1 - 2 ae / Dc.
  Rolling bearing defect frequency (textbook): BPFO = Z/2 x (1 - Dw/dm cos alpha) x f_shaft.
  ISO 21940-11 (balance quality grade G), as commonly applied: permissible residual unbalance U = 9549 G m / n (g mm).
Assumptions (labelled in "source"): the S1 curve above the base speed, the idle (no-load) power, the work material
  coefficients, the bearing geometry, the thermal and vibration baselines, every alarm limit, the tool data.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with "
GMN = "GMN milling spindles page (gmn.de), HCS series table, line HCS 230 - 20000 / 40"

twin = {
    "$comment": "MC-4801 machining centre main spindle twin. Expected cutting power from the Kienzle specific cutting force of the cut the CNC reports, "
                "expected temperatures and thermal growth from the mean speed, defect frequencies from the bearing geometry; the machine sends only what it measures.",
    "twin": {"id": "MC-4801", "name": "Machining centre MC-4801 main spindle", "version": "1.0.0", "folder": "spindle-twin"},
    "identification": {
        "asset": "MC-4801", "assetnum": "MC-4801", "manufacturer": "GMN", "model": "HCS 230 - 20000/40 HSK-A63 motor spindle",
        "description": "Main spindle of a 3-axis vertical machining centre (job shop, steel and aluminium parts)",
        "spindle": "Motor spindle, 230 mm housing, built-in motor, oil-air lubricated angular contact ball bearings (70 mm bore at the front)",
        "tool_interface": "HSK-A63 (DIN 69893) with automatic clamping set (disc spring pack, drawbar, hydraulic release)",
        "cooling": "Water-cooled housing and motor from the machine's spindle chiller",
        "cnc": "CNC with an MTConnect agent or an OPC UA server for machine tools (OPC 40501-1)",
        "site": "A machining job shop (generic)",
    },
    "design": {
        "spindle": {"n_max_rpm": 20000.0, "p_rated_kw": 40.0, "n_base_rpm": 4500.0, "t_rated_nm": 85.0, "housing_mm": 230.0,
                    "bearing_bore_mm": 70.0, "lubrication": "oil-air", "interface": "HSK-A63",
                    "source": GMN + ". Above the base speed the twin takes constant power up to n max: " + A
                              + "the S1 power curve of your spindle's data sheet (GMN's sister HCS 230 - 20000/25 shows power falling near n max)"},
        "drive": {"eta": 0.90, "idle_p0_kw": 0.25, "idle_p1_kw_per_krpm": 0.03, "idle_p2_kw_per_krpm2": 0.004,
                  "source": "Idle (no-load) power = p0 + p1 (n/1000) + p2 (n/1000)^2 from bearing friction and windage, and the motor efficiency at load: "
                            + A + "an air-cut test of this spindle at five speeds at commissioning"},
        "material": {"name": "C45 (1.0503) steel, normalised, ISO P", "kc1_n_mm2": 1700.0, "mc": 0.25,
                     "source": "Kienzle coefficients kc1.1 and mc of the work material: " + A + "your tool maker's material data (they vary with the material and its heat treatment)"},
        "bearing": {"type": "angular contact ball bearing, 70 mm bore (7014 size), hybrid (ceramic balls)", "balls": 21, "ball_d_mm": 11.1,
                    "pitch_d_mm": 90.0, "contact_deg": 15.0,
                    "source": "Bore 70 mm from the " + GMN + ". Ball count, ball diameter and contact angle: " + A + "the bearing maker's data or its published defect frequency factors"},
        "thermal": {"front_f0": 4.0, "front_f1": 1.0, "rear_r0": 3.0, "rear_r1": 0.8, "motor_m0": 5.0, "motor_m1": 1.2,
                    "growth_g0_um": 2.0, "growth_g1_um": 2.2,
                    "source": "Expected bearing temperature = coolant inlet + c0 + c1 x (mean speed / 1000 rpm); motor = coolant inlet + m0 + m1 x mean power (kW); "
                              "Z thermal growth of the spindle nose = g0 + g1 x (mean speed / 1000 rpm). " + A
                              + "the spindle thermal test (ISO 230-3) and a fit on a few weeks of healthy data of this spindle"},
        "vibration": {"env0_g": 0.30, "env1_g": 0.50, "v1x0_mms": 0.20, "v1x1_mms": 0.60,
                      "source": "Envelope acceleration at the front bearing BPFO = e0 + e1 x (n / n max) (g); 1x vibration velocity = v0 + v1 x (n / 10,000 rpm)^2 (mm/s). "
                                + A + "the baseline learnt with balanced tools on this spindle"},
        "clamping": {"nominal_kn": 18.0, "actuating_kn": 6.0,
                     "source": "Roehm HSK brochure, HSK A63 clamping set: clamping force 18 kN, actuating force 6 kN. The alarm fractions in twin_model.limits are assumptions"},
        "cooling": {"flow_nominal_lpm": 8.0, "inlet_c": 22.0, "oilair_nominal_bar": 4.5,
                    "source": "Spindle chiller flow, inlet set point and oil-air supply pressure: " + A + "the spindle maker's installation data"},
        "balance": {"grade_g": 2.5,
                    "source": "Balance quality grade G 2.5, commonly applied to machine tool spindles and tool assemblies (ISO 21940-11): " + A + "the grade in your tool balancing specification"},
        "demo": {"time_scale": 10, "op_s": 90, "change_s": 10, "mean_tau_s": 300,
                 "note": "Demo only: one real second is ten machine seconds. The stand-in machine runs a four-operation part program in a loop "
                         "(roughing, face milling, pocketing, finishing, each 90 machine seconds plus a 10 s tool change); the edge keeps 5-minute mean speed and power."},
        "program": {"operations": [
        {"op": "Rough side milling", "tool": 1, "dc_mm": 20.0, "z": 4, "mass_kg": 1.3, "rake_deg": 6.0, "vc_m_min": 200.0, "fz_mm": 0.08, "ap_mm": 20.0, "ae_mm": 6.0},
        {"op": "Face milling", "tool": 2, "dc_mm": 63.0, "z": 5, "mass_kg": 2.4, "rake_deg": 6.0, "vc_m_min": 220.0, "fz_mm": 0.15, "ap_mm": 2.5, "ae_mm": 45.0},
        {"op": "Pocket, trochoidal", "tool": 3, "dc_mm": 12.0, "z": 3, "mass_kg": 1.0, "rake_deg": 6.0, "vc_m_min": 250.0, "fz_mm": 0.06, "ap_mm": 18.0, "ae_mm": 1.2},
        {"op": "Finish contour", "tool": 4, "dc_mm": 8.0, "z": 4, "mass_kg": 0.8, "rake_deg": 6.0, "vc_m_min": 300.0, "fz_mm": 0.04, "ap_mm": 10.0, "ae_mm": 0.3},
        ],
            "source": "The stand-in part program (tools, cutting data, tool masses with HSK holder): " + A + "your CAM data; the CNC sends the values of the active cut"},
    },
    "telemetry": {
        "event": "spindle", "publish_every_s": 10, "device_type": "CNC_MOTOR_SPINDLE",
        "groups": {"Spindle": "Spindle speed and drive power (CNC)", "Tool": "Active tool (CNC tool table)", "Cut": "Active cut (CNC program / CAM)",
                   "Temp": "Spindle temperatures", "Cooling": "Spindle cooling and lubrication", "Thermal": "Thermal growth sensor",
                   "Vib": "Spindle vibration sensor", "Clamp": "Tool clamping", "Shock": "Crash (shock) sensor"},
        "points": [
            {"metric": "speed_rpm", "path": "Spindle.Speed", "label": "Spindle speed, actual", "unit": "rpm"},
            {"metric": "speed_avg_rpm", "path": "Spindle.SpeedMean", "label": "Spindle speed, 5-minute mean", "unit": "rpm"},
            {"metric": "power_kw", "path": "Spindle.Power", "label": "Spindle drive active power", "unit": "kW"},
            {"metric": "power_avg_kw", "path": "Spindle.PowerMean", "label": "Spindle drive power, 5-minute mean", "unit": "kW"},
            {"metric": "running", "path": "Spindle.Running", "label": "Spindle turning (1 = yes)", "unit": "code"},
            {"metric": "tool_number", "path": "Tool.Number", "label": "Active tool number", "unit": "code"},
            {"metric": "tool_diameter_mm", "path": "Tool.Diameter", "label": "Cutting diameter of the active tool", "unit": "mm"},
            {"metric": "tool_teeth", "path": "Tool.Teeth", "label": "Number of teeth of the active tool", "unit": "count"},
            {"metric": "tool_rake_deg", "path": "Tool.Rake", "label": "Rake angle of the active tool", "unit": "°"},
            {"metric": "tool_mass_kg", "path": "Tool.Mass", "label": "Mass of the tool assembly (tool + HSK holder)", "unit": "kg"},
            {"metric": "in_cut", "path": "Cut.InCut", "label": "Tool in the material (1 = cutting)", "unit": "code"},
            {"metric": "ap_mm", "path": "Cut.Ap", "label": "Axial depth of cut of the active operation", "unit": "mm"},
            {"metric": "ae_mm", "path": "Cut.Ae", "label": "Radial width of cut of the active operation", "unit": "mm"},
            {"metric": "feed_mm_min", "path": "Cut.Feed", "label": "Path feed rate, actual", "unit": "mm/min"},
            {"metric": "front_brg_temp_c", "path": "Temp.FrontBearing", "label": "Front bearing temperature", "unit": "°C"},
            {"metric": "rear_brg_temp_c", "path": "Temp.RearBearing", "label": "Rear bearing temperature", "unit": "°C"},
            {"metric": "motor_temp_c", "path": "Temp.Motor", "label": "Motor winding temperature (PT1000)", "unit": "°C"},
            {"metric": "coolant_in_c", "path": "Cooling.InletTemp", "label": "Spindle cooling water inlet temperature", "unit": "°C"},
            {"metric": "coolant_out_c", "path": "Cooling.OutletTemp", "label": "Spindle cooling water outlet temperature", "unit": "°C"},
            {"metric": "coolant_flow_lpm", "path": "Cooling.Flow", "label": "Spindle cooling water flow", "unit": "L/min"},
            {"metric": "oilair_pressure_bar", "path": "Cooling.OilAirPressure", "label": "Oil-air lubrication supply pressure", "unit": "bar"},
            {"metric": "z_growth_um", "path": "Thermal.GrowthZ", "label": "Axial thermal growth of the spindle nose", "unit": "µm"},
            {"metric": "vib_1x_mms", "path": "Vib.OneX", "label": "Vibration velocity at 1x spindle speed", "unit": "mm/s"},
            {"metric": "vib_env_g", "path": "Vib.EnvelopeBPFO", "label": "Envelope acceleration at the front bearing outer-race frequency", "unit": "g"},
            {"metric": "clamp_force_kn", "path": "Clamp.Force", "label": "Clamping force measured at the last tool change", "unit": "kN"},
            {"metric": "shock_max_g_24h", "path": "Shock.Max24h", "label": "Highest shock at the spindle nose, last 24 h", "unit": "g"},
            {"metric": "shock_count_total", "path": "Shock.Count", "label": "Shocks above the crash threshold since the last rebuild", "unit": "count"},
        ],
    },
    "twin_model": {
        "limits": {
            "power_ratio_alert": 1.30, "wear_min_cut_kw": 1.5, "front_residual_c": 6.0, "rear_residual_c": 6.0, "motor_residual_c": 10.0,
            "growth_residual_um": 8.0, "env_ratio": 3.0, "v1x_ratio": 2.5, "clamp_warn_ratio": 0.85, "clamp_low_ratio": 0.70,
            "coolant_flow_min_lpm": 5.0, "oilair_min_bar": 3.5, "crash_g": 10.0, "running_rpm": 100.0,
            "source": "Alarm limits: " + A + "your fleet statistics, the spindle maker's limits and the clamping set maker's minimum clamping force",
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "bearing_damage": {"name": "Front bearing damage (outer-race spall)", "part": "bearings",
                           "symptoms": "envelope at the outer-race frequency grows, front bearing runs hotter than the speed model predicts",
                           "rules": ["SP_BRG_ENV", "SP_FRONT_BRG_TEMP"], "default_ramp_min": 1.5},
        "lubrication_starvation": {"name": "Oil-air lubrication starved (blocked line, empty tank)", "part": "lubrication",
                                   "symptoms": "oil-air pressure low, both bearings hotter than the model, vibration still normal",
                                   "rules": ["SP_OILAIR_LOW", "SP_FRONT_BRG_TEMP", "SP_REAR_BRG_TEMP"], "default_ramp_min": 1},
        "cooling_failure": {"name": "Spindle cooling lost (chiller, hose, blocked jacket)", "part": "cooling",
                            "symptoms": "cooling flow low, motor much hotter than its load explains, spindle grows more than the thermal model",
                            "rules": ["SP_COOLING_FLOW_LOW", "SP_MOTOR_TEMP", "SP_THERMAL_GROWTH"], "default_ramp_min": 1},
        "tool_imbalance": {"name": "Unbalanced tool assembly (or chips on the HSK taper)", "part": "tool",
                           "symptoms": "vibration at 1x spindle speed well above the balanced baseline, bearings normal",
                           "rules": ["SP_IMBALANCE"], "default_ramp_min": 0.5},
        "clamping_force_loss": {"name": "Clamping force loss (disc springs fatigued, clamping set dry)", "part": "clamping",
                                "symptoms": "clamping force at tool change falls below the clamping set's nominal value",
                                "rules": ["SP_CLAMP_FORCE_WARN", "SP_CLAMP_FORCE_LOW"], "default_ramp_min": 1},
        "tool_wear": {"name": "Worn cutting tool", "part": "tool",
                      "symptoms": "spindle power above the Kienzle cutting power of the same cut, everything else normal",
                      "rules": ["SP_TOOL_WEAR"], "default_ramp_min": 1},
        "spindle_crash": {"name": "Spindle crash (collision of tool or head)", "part": "spindle",
                          "symptoms": "shock above the crash threshold, then 1x vibration up (bent tool or holder, damaged taper)",
                          "rules": ["SP_CRASH", "SP_IMBALANCE"], "default_ramp_min": 0.5},
    },
    "presentation": {"title": "MC-4801 machining centre main spindle", "dashboard": "CNC_MOTOR_SPINDLE"},
}

out = HERE / "twin" / "mc-4801.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
