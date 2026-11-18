"""Write twin/bp-5001.twin.json: the belt filter press twin (BP-5001).

    python build_twin.py

BP-5001 dewaters anaerobically digested sludge (primary + waste activated) at a municipal wastewater treatment plant.
It is a high-pressure belt filter press of the ANDRITZ SMX-Q range, size 2000, with 12 S-rolls: polymer conditioning,
an extra-long gravity (thickening) zone, a camber wedge, then the high-pressure S-roll zone. Each belt has its own
pneumatic tensioning roll and its own automatic tracking (pivoting regulating roll, air bellows, edge feeler plate), and
a spray pipe with a cleaning brush washes each belt continuously.

Sources and assumptions (every number below is either published or labelled as an assumption in "source"):
  ANDRITZ, "Revolutionary dewatering technology: ANDRITZ belt presses for the environment industry" (brochure, PDF):
    SMX-Q 2000 feed capacity up to 45 m3/h and average dry solids throughput 900 kg/h ("based on specific feed solids,
    results will vary depending on sludge type"), average wash water consumption 13.6 m3/h at 8 bar (g), 8 or 12 S-rolls,
    motor drive 2 x 1.5 kW for the S12 version, machine width 3,100 mm, length 6,206 mm max., height 1,633 mm;
    tracking by a pivoting regulating roll with two air spring bellows and a feeler plate; tensioning by one roll per
    belt with pneumatic cylinders. The BELT WIDTH (2.0 m) is an ASSUMPTION read from the size number.
  US EPA, Biosolids Technology Fact Sheet: Belt Filter Press, EPA 832-F-00-057 (September 2000), Table 1: anaerobically
    digested primary + WAS: feed solids 3 to 9 %, polymer 2 to 8 g/kg, cake solids 18 to 44 %. Belt life averages about
    2,700 running hours (range 400 to 12,000).
  Solids capture by mass balance (textbook): capture = 1 - filtrate solids / feed solids, with the filtrate flow measured
    after the wash water has joined it.
  Dose-response curve, tension and loading effects, polymer solution strength, limits: ASSUMPTIONS, labelled below.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with "
BRO = ("ANDRITZ brochure 'ANDRITZ belt presses for the environment industry' (SME-Q / SMX-Q), range table, "
       "https://www.andritz.com/resource/blob/367524/4b043c480ac94c510e61c16377e30923/pb-belt-press-env-en-v09-web-data.pdf")
EPA = ("US EPA, Biosolids Technology Fact Sheet: Belt Filter Press, EPA 832-F-00-057 (September 2000), "
       "https://19january2021snapshot.epa.gov/sites/static/files/documents/BiosolidsTechSheetBeltFilterPress.pdf")

twin = {
    "$comment": "BP-5001 belt filter press twin. Expected values in Maximo Monitor from the maker's capacity table, a dose-response curve fitted on site and a mass balance; the device sends only what it measures.",
    "twin": {"id": "BP-5001", "name": "Sludge dewatering belt filter press BP-5001", "version": "1.0.0", "folder": "beltpress-twin"},
    "identification": {
        "asset": "BP-5001", "assetnum": "BP-5001", "manufacturer": "ANDRITZ",
        "model": "SMX-Q 2000, 12 S-rolls (high-pressure belt filter press)",
        "description": "Digested sludge dewatering press, municipal wastewater treatment plant, with polymer conditioning",
        "press": "Twin-belt filter press: gravity (thickening) zone, camber wedge, 12-roll S-zone (high pressure)",
        "belts": "Two woven polyester filter belts, each with a pneumatic tensioning roll and an automatic tracking system",
        "wash": "One spray pipe with cleaning brush per belt, booster pump at 8 bar (g)",
        "polymer": "Powder polymer make-down unit and a progressive cavity dosing pump into the feed line (in-line mixer)",
        "feed": "Progressive cavity sludge feed pump from the digested sludge storage tank",
    },
    "design": {
        "press": {
            "belt_width_m": 2.0, "feed_capacity_m3h": 45.0, "solids_capacity_kgh": 900.0, "s_rolls": 12,
            "drive_kw": 3.0, "wash_flow_m3h": 13.6, "wash_pressure_bar": 8.0,
            "source": BRO + ". SMX-Q 2000: feed capacity up to 45 m3/h, average dry solids throughput 900 kg/h (at the maker's "
                      "feed solids), wash water 13.6 m3/h at 8 bar (g), drive 2 x 1.5 kW (S12). Belt width 2.0 m: " + A
                      + "the belt width on your press's data sheet.",
        },
        "sludge": {
            "type": "anaerobically digested primary + waste activated sludge", "feed_ds_pct": 3.5, "feed_ds_min_pct": 2.0,
            "source": EPA + ", Table 1: digested primary + WAS, feed 3 to 9 % solids, polymer 2 to 8 g/kg, cake 18 to 44 % solids. "
                      "Design feed 3.5 %, low alert 2.0 %: " + A + "your digester and storage data.",
        },
        "polymer": {
            "solution_pct": 0.25, "dose_design_kg_t": 6.0, "dose_max_kg_t": 8.0, "price_eur_kg": 3.0,
            "source": "Polymer dose in kg of active polymer per tonne of dry solids; the EPA range for this sludge is 2 to 8 g/kg (= kg/t), "
                      "used here as the alert above 8 kg/t. Make-down solution strength 0.25 % active, design dose 6 kg/t, price "
                      "3 EUR/kg active: " + A + "your make-down set point, jar tests and polymer contract.",
        },
        "dose_response": {
            "ds_max_pct": 26.0, "d0_kg_t": 2.0, "d_opt_kg_t": 7.0, "overdose_pct_per_kg_t": 0.4,
            "tension_pct_per_bar": 1.0, "overload_pct": 4.0,
            "source": "Expected cake dry solids at the live dose d (kg/t): DSmax (1 - exp(-d / d0)) - k_over max(0, d - d_opt), "
                      "plus k_t x (lower belt tension - set point) and minus k_load x max(0, solids loading ratio - 1). A saturating "
                      "dose-response with a mild overdose penalty is the usual shape of jar and full-scale dose trials; the "
                      "coefficients are " + A + "a dose trial on your press (cake DS at 4 to 6 doses).",
        },
        "belts": {
            "tension_set_bar": 5.0, "tension_min_bar": 4.0, "tracking_alert_mm": 20.0, "tracking_limit_mm": 35.0,
            "life_h": 2700.0, "hours_start": 1500.0, "speed_mpm": 4.0,
            "source": "Belt life averages about 2,700 running hours (range 400 to 12,000): " + EPA + ". Tension cylinder pressure "
                      "5.0 bar (alert 4.0), belt edge offset alert 20 mm and limit 35 mm from the centre line, belt speed 4 m/min: "
                      + A + "the press manual and the position of your belt-run-off limit switches.",
        },
        "wash": {
            "pressure_min_bar": 6.0, "nozzle_ratio_min": 0.80,
            "source": "Nozzle flow follows Q = Q0 sqrt(P / P0) (orifice law, textbook) with Q0 = 13.6 m3/h at P0 = 8 bar (g) from the "
                      "ANDRITZ range table. Pressure alert 6.0 bar, open-nozzle ratio alert 0.80: " + A + "your own practice.",
        },
        "capture": {
            "capture_min_pct": 90.0, "capture_design_pct": 96.5, "cake_residual_alert_pct": -2.0, "water_balance_alert_m3h": 4.0,
            "source": "Solids capture = 1 - (filtrate flow x filtrate TSS) / (feed flow x feed solids): mass balance, textbook. "
                      "Design capture 96.5 %, alert below 90 %, cake DS more than 2 points below the dose-response curve, water "
                      "balance residual above 4 m3/h: " + A + "your performance guarantee and plant practice.",
        },
        "operation": {
            "feed_flow_m3h": 22.0, "cake_density_t_m3": 1.0, "disposal_eur_t": 60.0,
            "source": A + "the plant's daily sludge production (22 m3/h for one shift pattern), cake bulk density about 1 t/m3 and the "
                      "cake haulage and disposal price per wet tonne.",
        },
        "demo": {"time_scale": 60,
                 "note": "Demo only: the plant clock runs 60 times faster, so the running hours of the belts grow quickly. Feed solids drift slowly as the storage tank level changes."},
    },
    "telemetry": {
        "event": "beltpress", "publish_every_s": 10, "device_type": "BELT_FILTER_PRESS",
        "groups": {"Run": "Press status", "Feed": "Sludge feed", "Polymer": "Polymer dosing", "Cake": "Dewatered cake",
                   "Filtrate": "Filtrate and wash water return", "Wash": "Belt wash", "Belts": "Belt tension, tracking and drive"},
        "points": [
            {"metric": "running", "path": "Run.Running", "label": "Press running (1 = yes)", "unit": "code"},
            {"metric": "feed_flow_m3h", "path": "Feed.Flow", "label": "Sludge feed flow (magnetic flow meter)", "unit": "m³/h"},
            {"metric": "feed_ds_pct", "path": "Feed.DrySolids", "label": "Feed dry solids (inline microwave solids meter)", "unit": "% DS"},
            {"metric": "polymer_solution_lph", "path": "Polymer.SolutionFlow", "label": "Polymer solution flow (0.25 % active)", "unit": "L/h"},
            {"metric": "cake_ds_pct", "path": "Cake.DrySolids", "label": "Cake dry solids (online NIR cake sensor)", "unit": "% DS"},
            {"metric": "filtrate_flow_m3h", "path": "Filtrate.Flow", "label": "Filtrate + wash water return flow", "unit": "m³/h"},
            {"metric": "filtrate_tss_mgl", "path": "Filtrate.TSS", "label": "Filtrate suspended solids (optical TSS probe)", "unit": "mg/L"},
            {"metric": "wash_pressure_bar", "path": "Wash.Pressure", "label": "Wash water pressure at the spray pipes", "unit": "bar g"},
            {"metric": "wash_flow_m3h", "path": "Wash.Flow", "label": "Wash water flow, both belts", "unit": "m³/h"},
            {"metric": "tension_upper_bar", "path": "Belts.TensionUpper", "label": "Upper belt tensioning cylinder pressure", "unit": "bar"},
            {"metric": "tension_lower_bar", "path": "Belts.TensionLower", "label": "Lower belt tensioning cylinder pressure", "unit": "bar"},
            {"metric": "tracking_upper_mm", "path": "Belts.TrackingUpper", "label": "Upper belt edge offset from centre (feeler)", "unit": "mm"},
            {"metric": "tracking_lower_mm", "path": "Belts.TrackingLower", "label": "Lower belt edge offset from centre (feeler)", "unit": "mm"},
            {"metric": "belt_speed_mpm", "path": "Belts.Speed", "label": "Belt speed", "unit": "m/min"},
            {"metric": "drive_kw", "path": "Belts.DrivePower", "label": "Belt drive power", "unit": "kW"},
            {"metric": "belt_hours", "path": "Belts.Hours", "label": "Running hours of the installed belts", "unit": "h"},
        ],
    },
    "twin_model": {
        "limits": {
            "capture_min_pct": 90.0, "cake_residual_alert_pct": -2.0, "hydraulic_ratio_max": 1.0, "solids_ratio_max": 1.0,
            "dose_max_kg_t": 8.0, "wash_pressure_min_bar": 6.0, "nozzle_ratio_min": 0.80, "tension_min_bar": 4.0,
            "tracking_alert_mm": 20.0, "tracking_limit_mm": 35.0, "belt_life_h": 2700.0, "feed_ds_min_pct": 2.0,
            "water_balance_alert_m3h": 4.0,
            "source": "See design: capacity from the ANDRITZ range table, dose and belt life from the EPA fact sheet, the rest "
                      "assumptions to replace with your own limits.",
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "polymer_weak": {"name": "Polymer make-down weak (powder feeder bridging, aged solution)", "part": "polymer",
                         "symptoms": "the dosing pump runs normally but less active polymer reaches the sludge: cake wetter than the dose-response curve, capture falls, filtrate dirty",
                         "rules": ["BP_CAKE_DRY_LOW", "BP_CAPTURE_LOW"], "default_ramp_min": 1.5},
        "polymer_overdose": {"name": "Polymer overdose (dose set point left high)", "part": "polymer",
                             "symptoms": "specific polymer consumption above the range, cake no drier (past the optimum), cost up",
                             "rules": ["BP_POLYMER_HIGH"], "default_ramp_min": 1},
        "feed_overload": {"name": "Feed above capacity (feed pump speed too high)", "part": "feed",
                          "symptoms": "hydraulic and solids loading above the maker's capacity, cake wetter as expected, capture slips",
                          "rules": ["BP_HYDRAULIC_HIGH", "BP_SOLIDS_LOAD_HIGH"], "default_ramp_min": 1},
        "belt_wear": {"name": "Filter belt worn out (past its life, torn seam)", "part": "belts",
                      "symptoms": "running hours past the belt life, fines pass the open weave: filtrate solids up, capture down, cake normal",
                      "rules": ["BP_CAPTURE_LOW", "BP_BELT_HOURS_HIGH"], "default_ramp_min": 1.5},
        "wash_nozzle_blinding": {"name": "Wash nozzles blocked, belt blinding", "part": "wash",
                                 "symptoms": "wash flow low at normal pressure, the belt is not cleaned, drainage falls: cake wetter than expected",
                                 "rules": ["BP_WASH_NOZZLES_BLOCKED", "BP_CAKE_DRY_LOW"], "default_ramp_min": 1.5},
        "wash_pressure_low": {"name": "Wash water pressure low (booster pump, strainer)", "part": "wash",
                              "symptoms": "pressure below the minimum, flow falls with it (nozzles open)", "rules": ["BP_WASH_PRESSURE_LOW"], "default_ramp_min": 1},
        "belt_mistracking": {"name": "Belt mistracking (tracking bellows leak, feeler stuck)", "part": "belts",
                             "symptoms": "upper belt edge drifts off centre towards the run-off limit switch",
                             "rules": ["BP_TRACKING_OFF", "BP_TRACKING_LIMIT"], "default_ramp_min": 1},
        "tension_low": {"name": "Belt tension low (air leak on the tensioning cylinder)", "part": "belts",
                        "symptoms": "tension pressure below the set point, less pressure on the cake: drier cake lost, as the curve expects",
                        "rules": ["BP_TENSION_LOW"], "default_ramp_min": 1},
    },
    "presentation": {"title": "BP-5001 belt filter press", "dashboard": "BELT_FILTER_PRESS"},
}

d = twin["design"]
dose = d["polymer"]["dose_design_kg_t"]
dr = d["dose_response"]
twin["design"]["dose_response"]["note"] = (f"Expected cake at the design dose {dose} kg/t: "
                                           f"{dr['ds_max_pct'] * (1 - math.exp(-dose / dr['d0_kg_t'])):.1f} % DS")

out = HERE / "twin" / "bp-5001.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
