"""Write twin/cl-5101.twin.json: the chlorine contact tank (clearwell) twin (CL-5101).

    python build_twin.py

CL-5101 is the chlorine contact tank (clearwell) after the filters of a conventional surface water treatment works. Sodium
hypochlorite is dosed at the clearwell inlet by a flow-paced dosing pump with a residual trim; two free chlorine analysers
watch the outlet, one at the inlet. The twin computes CT (residual x T10) and compares it with the CT the US EPA tables require
at the water's temperature, pH and residual, at the actual level and flow.

Sources (every number is either from these sources or labelled as an assumption in "source"):
  US EPA, Disinfection Profiling and Benchmarking Technical Guidance Manual, EPA 815-R-20-003 (June 2020):
    Eq. 4-1 CTcalc = C x T; Eq. 4-2 TDT = V / Q (V at the low water level); Eq. 4-3 T = TDT x BF; Table 4-2 baffling factors
    (unbaffled 0.1, poor 0.3, average 0.5, superior 0.7, perfect 1.0); Eq. 5-1 log Giardia = 3 x CTcalc / CT99.9;
    Eq. 5-2 log virus = 4 x CTcalc / CT99.99; Table B-2 (virus, free chlorine, pH 6-9); Appendix H regression of Smith et al.
    (1995) for CT99.9 of Giardia by free chlorine.
  40 CFR 141.72(b): 3-log Giardia and 4-log virus removal and/or inactivation; residual entering the distribution system not
    below 0.2 mg/L for more than 4 hours. 40 CFR 141.65: MRDL chlorine 4.0 mg/L as Cl2.
  WHO Guidelines for Drinking-water Quality, 4th ed. (Table 8.16): chlorine guideline value 5 mg/L; free chlorine >= 0.5 mg/L
    after at least 30 min contact at pH < 8.0; >= 0.2 mg/L at the point of delivery.
  Hach CL17sc installation manual DOC023.97.80614: 0.03 to 10 mg/L, one reading every 150 s, accuracy +-5 % or +-0.04 mg/L.
  Grundfos SMART Digital S data booklet: DDA 30-4, setting range 0.03 to 30 l/h, 4 bar; FCM variant with FlowControl, flow
    measurement and 0/4-20 mA input; FlowControl needs at least 2 bar back pressure.
  PHTA fact sheet "Sodium hypochlorite (liquid chlorine)" (2020): 12.5 % sodium hypochlorite half-life about 180 days at 25 C
    and 48 days at 35 C.
  Morris (1966): pKa of HOCl = 3000/T - 10.0686 + 0.0253 T (T in K), textbook relation.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with your works' drawings, tracer study and operating data"

twin = {
    "$comment": "CL-5101 chlorine contact tank twin. Expected values in Maximo Monitor from the EPA CT method, the tank geometry and the dosing data; the device sends only what it measures.",
    "twin": {"id": "CL-5101", "name": "Chlorine contact tank CL-5101", "version": "1.0.0", "folder": "chlorine-twin"},
    "identification": {
        "asset": "CL-5101", "assetnum": "CL-5101", "manufacturer": "Civil structure (works-built); Hach; Grundfos",
        "model": "Baffled rectangular clearwell with hypochlorite dosing",
        "description": "Chlorine contact tank (clearwell) after the filters of a surface water treatment works: primary disinfection with sodium hypochlorite",
        "tank": "Rectangular reinforced-concrete clearwell, 40 m x 20 m, 5.0 m top water level, inlet and outlet without baffles",
        "analysers": "Hach CL17sc colorimetric (DPD) free chlorine analysers: one at the inlet after mixing, two at the outlet (A controls, B checks)",
        "dosing": "Grundfos SMART Digital DDA 30-4 FCM diaphragm dosing pump (duty), flow-paced with residual trim, 0/4-20 mA setpoint",
        "chemical": "Sodium hypochlorite, 12.5 trade % (about 125 g/L available chlorine) delivered to a 15 m3 storage tank",
    },
    "design": {
        "clearwell": {
            "length_m": 40.0, "width_m": 20.0, "level_max_m": 5.0, "level_min_op_m": 2.5, "level_normal_m": 4.0,
            "baffling_factor": 0.3,
            "source": "Geometry and operating levels: " + A + ". Baffling factor 0.3 = 'poor' in EPA 815-R-20-003 Table 4-2 "
                      "(single or multiple unbaffled inlets and outlets, no intra-basin baffles); replace with T10/TDT from a tracer study.",
        },
        "flow": {"design_m3h": 1000.0, "peak_m3h": 1500.0, "source": "Works design and peak hourly flow: " + A},
        "disinfection": {
            "giardia_log_required": 0.5, "virus_log_required": 2.0,
            "removal_credit_giardia": 2.5, "removal_credit_virus": 2.0,
            "residual_target_mgl": 1.0, "entry_min_mgl": 0.2, "mrdl_mgl": 4.0, "who_gv_mgl": 5.0,
            "source": "40 CFR 141.72(b): 3-log Giardia and 4-log virus in total; residual entering distribution >= 0.2 mg/L. "
                      "40 CFR 141.65: MRDL 4.0 mg/L. WHO GDWQ: guideline value 5 mg/L. Removal credit for conventional filtration "
                      "(2.5-log Giardia, 2-log virus) is the credit commonly granted by the state; " + A + ". Residual target: " + A,
        },
        "ct": {
            "giardia_lt": {"a": 0.353, "b": 12.006, "c0": 2.46, "ct": -0.073, "cc": 0.125, "cph": 0.389},
            "giardia_ge": {"a": 0.361, "b": -2.261, "c0": 2.69, "ct": -0.065, "cc": 0.111, "cph": 0.361},
            "t_split_c": 12.5,
            "virus_t_c": [0.5, 5, 10, 15, 20, 25], "virus_ct99_99": [12, 8, 6, 4, 3, 2],
            "source": "EPA 815-R-20-003 Appendix H (regression of Smith et al. 1995, CT99.9 = a I (b + exp(c0 + ct T + cc C + cph pH)), "
                      "below and from 12.5 C) and Table B-2 (CT for 4-log virus by free chlorine, pH 6-9, interpolated linearly).",
        },
        "chemistry": {"pka_a": 3000.0, "pka_b": -10.0686, "pka_c": 0.0253,
                      "demand_immediate_mgl": 0.4, "decay_per_h": 0.05,
                      "source": "HOCl pKa: Morris (1966) textbook relation. Immediate chlorine demand of the filtered water and "
                                "first-order bulk decay rate in the clearwell: " + A + " (measure with a bottle decay test)."},
        "dosing": {
            "pump": "Grundfos DDA 30-4 FCM", "pump_max_lh": 30.0, "pump_min_lh": 0.03, "pump_max_bar": 4.0, "flowcontrol_min_bar": 2.0,
            "dose_design_mgl": 1.6, "dose_sp_max_mgl": 3.5, "strength_config_gl": 125.0,
            "source": "Pump range, pressure and FlowControl back pressure: Grundfos SMART Digital S data booklet. Design dose, PLC "
                      "dose limit and the hypochlorite strength configured in the PLC: " + A,
        },
        "hypochlorite": {
            "delivered_gl": 125.0, "half_life_25c_d": 180.0, "half_life_35c_d": 48.0, "tank_m3": 15.0,
            "source": "Half-lives of 12.5 % sodium hypochlorite at 25 and 35 C: PHTA fact sheet (2020). The twin uses a first-order "
                      "approximation k(T) = ln2 / 180 d x (180/48)^((T - 25)/10) at the tank temperature. Real decomposition is closer to "
                      "second order and faster at higher strength: replace with your supplier's data. Delivered strength (12.5 trade % "
                      "= about 125 g/L available chlorine) and tank volume: " + A,
        },
        "analyser": {"model": "Hach CL17sc", "range_mgl": [0.03, 10.0], "interval_s": 150, "accuracy_pct": 5.0, "accuracy_mgl": 0.04,
                     "source": "Hach CL17sc installation manual (DOC023.97.80614): range, 150 s interval, accuracy +-5 % or +-0.04 mg/L (0 to 5 mg/L)."},
        "demo": {"time_scale": 60, "note": "Demo only: the plant clock runs 60 times faster, so one day of demand (and clearwell level) passes in 24 minutes."},
    },
    "telemetry": {
        "event": "clearwell", "publish_every_s": 10, "device_type": "CHLORINE_CONTACT_TANK",
        "groups": {"Flow": "Flows through the clearwell", "Clearwell": "Clearwell level", "Water": "Water quality at the outlet",
                   "Chlorine": "Free chlorine analysers", "Dosing": "Hypochlorite dosing pump and PLC loop", "Hypo": "Hypochlorite storage"},
        "points": [
            {"metric": "flow_in_m3h", "path": "Flow.Filtered", "label": "Filtered water flow into the clearwell", "unit": "m³/h"},
            {"metric": "flow_out_m3h", "path": "Flow.Outlet", "label": "Flow out to the high-lift pumps", "unit": "m³/h"},
            {"metric": "level_m", "path": "Clearwell.Level", "label": "Clearwell water level", "unit": "m"},
            {"metric": "temp_c", "path": "Water.Temperature", "label": "Water temperature at the outlet", "unit": "°C"},
            {"metric": "ph", "path": "Water.pH", "label": "pH at the outlet", "unit": "pH"},
            {"metric": "cl_in_mgl", "path": "Chlorine.Inlet", "label": "Free chlorine after the dosing point (inlet)", "unit": "mg/L"},
            {"metric": "cl_out_a_mgl", "path": "Chlorine.OutletA", "label": "Free chlorine at the outlet, analyser A (controls)", "unit": "mg/L"},
            {"metric": "cl_out_b_mgl", "path": "Chlorine.OutletB", "label": "Free chlorine at the outlet, analyser B (check)", "unit": "mg/L"},
            {"metric": "dose_sp_mgl", "path": "Dosing.DoseSetpoint", "label": "Dose setpoint after the residual trim (PLC)", "unit": "mg/L"},
            {"metric": "pump_sp_lh", "path": "Dosing.PumpSetpoint", "label": "Flow-paced pump setpoint sent to the pump", "unit": "L/h"},
            {"metric": "pump_flow_lh", "path": "Dosing.PumpFlow", "label": "Dosing flow measured by the pump (FCM)", "unit": "L/h"},
            {"metric": "pump_pressure_bar", "path": "Dosing.Backpressure", "label": "Pump discharge pressure", "unit": "bar"},
            {"metric": "pump_alarm", "path": "Dosing.FlowControlAlarm", "label": "FlowControl alarm (1 = air or gas in the head)", "unit": "code"},
            {"metric": "hypo_level_pct", "path": "Hypo.TankLevel", "label": "Hypochlorite tank level", "unit": "%"},
            {"metric": "hypo_temp_c", "path": "Hypo.TankTemp", "label": "Hypochlorite tank temperature", "unit": "°C"},
            {"metric": "hypo_age_d", "path": "Hypo.AgeDays", "label": "Days since the hypochlorite was delivered", "unit": "d"},
            {"metric": "hypo_delivered_gl", "path": "Hypo.DeliveredStrength", "label": "Strength on delivery (certificate or assay)", "unit": "g/L"},
        ],
    },
    "twin_model": {
        "limits": {
            "ct_ratio_alert": 1.5, "ct_ratio_limit": 1.0, "residual_low_mgl": 0.7, "analyser_diff_mgl": 0.2,
            "pump_dev_frac": 0.15, "hypo_strength_low_gl": 100.0, "hypo_days_left_min": 5.0, "demand_high_mgl": 1.0,
            "decay_high_per_h": 0.12, "trim_ratio_alert": 1.5, "ph_max": 8.0, "level_low_m": 2.5,
            "$comment": "ph_max 8.0 follows the WHO condition for effective chlorination (pH < 8.0); level_low_m is the minimum operating level used for T10 in the CT design. Other limits: assumptions.",
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "cold_peak_drawdown": {"name": "Cold water at peak flow, clearwell drawn down", "part": "clearwell",
                               "symptoms": "temperature near 0.5 C, outflow 1.5 x design, level below the minimum operating level: T10 and CT collapse",
                               "rules": ["CL_CT_FAIL", "CL_CT_MARGIN_LOW", "CL_LEVEL_LOW"], "default_ramp_min": 1.5},
        "dose_pump_gas_lock": {"name": "Dosing pump gas lock (hypochlorite off-gassing)", "part": "dosing pump",
                               "symptoms": "measured dosing flow far below setpoint, trim saturates, residual and CT fall",
                               "rules": ["DOSE_PUMP_DEVIATION", "CL_TRIM_HIGH", "CL_OUTLET_LOW", "CL_ENTRY_LOW", "CL_CT_MARGIN_LOW", "CL_CT_FAIL"],
                               "default_ramp_min": 1},
        "hypo_strength_loss": {"name": "Hypochlorite strength loss in storage (old, hot)", "part": "hypochlorite tank",
                               "symptoms": "tank warm and old: strength far below delivery, trim raises the dose",
                               "rules": ["HYPO_STRENGTH_LOW", "CL_TRIM_HIGH"], "default_ramp_min": 1.5},
        "demand_rise": {"name": "Chlorine demand rise (raw water change, filter breakthrough)", "part": "water quality",
                        "symptoms": "dose minus inlet residual grows, trim raises the dose, decay normal",
                        "rules": ["CL_DEMAND_HIGH", "CL_TRIM_HIGH"], "default_ramp_min": 1},
        "analyser_drift": {"name": "Outlet analyser A reads high (reagent or optics)", "part": "analyser",
                           "symptoms": "A and B disagree; the trim follows A, so the real residual falls",
                           "rules": ["CL_ANALYSER_MISMATCH", "CL_OUTLET_LOW"], "default_ramp_min": 1},
        "clearwell_decay": {"name": "Fast chlorine decay in the clearwell (sediment, biofilm)", "part": "clearwell",
                            "symptoms": "inlet residual rises to hold the outlet; decay rate per hour grows",
                            "rules": ["CL_DECAY_HIGH", "CL_TRIM_HIGH"], "default_ramp_min": 1},
        "ph_high": {"name": "pH high (caustic or lime overdose upstream)", "part": "water quality",
                    "symptoms": "pH above 8: less HOCl, CT required up by about 1.7 x",
                    "rules": ["CL_PH_HIGH", "CL_CT_MARGIN_LOW"], "default_ramp_min": 0.5},
    },
    "presentation": {"title": "CL-5101 chlorine contact tank", "dashboard": "CHLORINE_CONTACT_TANK"},
}

out = HERE / "twin" / "cl-5101.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
