"""Write twin/pm-4301.twin.json: the paper machine dryer section twin (PM-4301).

    python build_twin.py

PM-4301 is the dryer section of a board machine making testliner: 50 steam-heated cast iron cylinders of 1.83 m
diameter in four steam groups, a cascade steam and condensate system (fresh steam to the main groups, their blow-through
steam to the intermediate group, and on to the wet-end group), a closed hood with pocket ventilation (PV) air. Every
cylinder has a Kadant Johnson PT2X steam joint with a cantilever stationary syphon.

Sources and assumptions (every number below is either from a named source or labelled as an assumption in "source"):
  Kadant Johnson PT2X steam joint and syphon system brochure (2020) and product page: standard pressure 160 psig (11 barg),
    upgradeable to 200 psig (14 barg); standard temperature 400 F (204 C), upgradeable 450 F (232 C); 500 rpm; maximum
    design speed 8000 fpm (2500 m/min).
  TAPPI TIP 0404-31 "Recommended dryer differential pressures": for properly sized stationary syphons the operating
    differential pressure is normally 15-35 kPa (2-5 psi); blow-through of a stationary syphon is typically 10-15 % (mass)
    of the condensing load and rises with the differential pressure; condensate rims above about 300-350 m/min.
  TAPPI TIP 0404-33 "Dryer section performance monitoring": steam-to-surface temperature difference 15-30 C in
    well-performing dryer sections (higher at the wet end); top machines use about 1.3 kg steam per kg water evaporated;
    PV air 82-93 C recommended; inconsistent surface temperatures in the main drying zone indicate marginal drainage.
  Saturated steam: saturation temperature and latent heat from the IAPWS-IF97 steam tables (textbook values).
  Machine size, grade, groups, pressures, hood air and prices: ASSUMPTIONS of a typical board machine, labelled below.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with your machine's data"

# Saturated steam (IAPWS-IF97, textbook tables): absolute pressure bar -> saturation temperature C, latent heat kJ/kg
STEAM_P = [1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 12.0, 14.0]
STEAM_T = [99.61, 111.35, 120.21, 133.52, 143.61, 151.83, 158.83, 164.95, 170.41, 179.88, 187.96, 195.04]
STEAM_HFG = [2257.5, 2226.0, 2201.6, 2163.5, 2133.4, 2107.4, 2085.8, 2066.0, 2047.5, 2014.6, 1985.4, 1959.0]

twin = {
    "$comment": "PM-4301 dryer section twin. Expected values in Maximo Monitor from the machine design, the steam tables and TAPPI dryer guidelines; the machine sends only what it measures.",
    "twin": {"id": "PM-4301", "name": "Dryer section PM-4301", "version": "1.0.0", "folder": "dryer-twin"},
    "identification": {
        "asset": "PM-4301", "assetnum": "PM-4301", "manufacturer": "Board machine dryer section, 50 cylinders, Kadant Johnson",
        "model": "PT2X steam joints with cantilever stationary syphons",
        "description": "Dryer section of a testliner board machine: 50 steam-heated cylinders in 4 cascade steam groups, closed hood",
        "cylinders": "50 cast iron dryer cylinders, 1.83 m (6 ft) diameter, 5.7 m face, single-tier and double-felted groups (typical design)",
        "steam_joints": "Kadant Johnson PT2X steam joint and cantilever stationary syphon on every cylinder",
        "steam_system": "Cascade: fresh steam to the main groups 3 and 4, their blow-through steam via a separator and thermocompressor to group 2, group 2 blow-through to group 1",
        "hood": "Closed hood with supply and exhaust fans, heat recovery and pocket ventilation (PV) air",
        "grade": "Testliner, 125 g/m2",
    },
    "design": {
        "machine": {
            "speed_mpm": 750.0, "width_m": 5.5, "basis_weight_gsm": 125.0, "reel_moisture_pct": 8.0, "press_dryness_pct": 48.0,
            "source": "Design grade and speed of the machine: reel width (trim), speed, basis weight at the reel, reel moisture and sheet dryness after the press section: " + A + ".",
        },
        "cylinders": {
            "count": 50, "diameter_m": 1.83, "face_m": 5.7, "groups": [6, 12, 20, 12], "mawp_barg": 11.0,
            "source": "1.83 m (6 ft) cylinders and the split into four steam groups (wet end, intermediate, main, dry end) are typical of a board machine: "
                      + A + ". Maximum allowable working pressure of the cylinders from their pressure vessel nameplate: assumption, set equal to the PT2X standard pressure (11 barg).",
        },
        "steam_joint": {
            "model": "Kadant Johnson PT2X", "pressure_std_barg": 11.0, "pressure_max_barg": 14.0, "temp_std_c": 204.0, "temp_max_c": 232.0,
            "rpm_max": 500, "speed_max_mpm": 2500,
            "source": "Kadant Johnson PT2X steam joint and syphon system brochure (2020): standard pressure 160 psig (11 barg), upgradeable 200 psig (14 barg); "
                      "standard temperature 400 F (204 C), upgradeable 450 F (232 C); 500 rpm; maximum design speed 8000 fpm (2500 m/min).",
        },
        "steam": {
            "p_barg": [1.0, 2.5, 4.5, 4.0], "dp_kpa": 25.0, "dt_surface_c": [35.0, 22.0, 20.0, 18.0],
            "dp_min_kpa": 15.0, "dp_max_kpa": 35.0, "bt_design_pct": 12.5, "bt_dp_ref_kpa": 25.0,
            "ssc_design": 1.35, "vent_design_pct": 0.5, "t_sheet_c": 60.0, "spread_design_k": 5.0,
            "table_p_bara": STEAM_P, "table_tsat_c": STEAM_T, "table_hfg_kjkg": STEAM_HFG,
            "source": "Group steam pressures and steam-to-surface temperature differences at design: " + A + " (inside the 15-30 C of TAPPI TIP 0404-33 for groups 2 to 4; "
                      "the wet-end group runs a larger difference, as the TIP notes). Differential pressure 25 kPa inside the 15-35 kPa TAPPI TIP 0404-31 gives for "
                      "stationary syphons. Blow-through 12.5 % of the condensing load at 25 kPa (middle of the TIP's typical 10-15 %), scaled with the square root of the "
                      "differential pressure: assumption (an orifice-like fit; replace with your syphon maker's performance curve). Specific steam consumption at design "
                      "1.35 kg/kg (TAPPI TIP 0404-33: top machines about 1.3): assumption. Normal venting 0.5 % of the steam: assumption. Sheet evaporation temperature "
                      "60 C used for the drying coefficient: assumption. Normal spread between a group's mean and its coldest cylinder 5 K: assumption. "
                      "Steam table: IAPWS-IF97 saturation temperature and latent heat (textbook).",
        },
        "hood": {
            "exhaust_humidity_gkg": 160.0, "supply_humidity_gkg": 15.0, "supply_exhaust_ratio": 0.80, "pv_air_c": 88.0, "pocket_humidity_gkg": 150.0,
            "source": "Hood exhaust humidity at design, supply air humidity after heat recovery, supply-to-exhaust air ratio of the closed hood (the rest of the exhaust is "
                      "room air drawn in at the openings) and pocket humidity: " + A + ". PV air temperature 88 C, inside the 82-93 C recommended by TAPPI TIP 0404-33.",
        },
        "economics": {
            "steam_price_usd_t": 25.0, "hours_per_year": 8400,
            "source": "Steam price and running hours per year: assumption, replace with your mill's steam cost and machine availability.",
        },
        "demo": {"time_scale": 60, "speed_swing": 0.02, "speed_period_s": 600,
                 "note": "Demo only: the plant clock runs 60 times faster and the speed swings 2 % over 10 minutes so the curves move; faults ramp in over minutes, where a worn syphon or a filled fabric takes weeks."},
    },
    "telemetry": {
        "event": "dryer", "publish_every_s": 10, "device_type": "PAPER_DRYER_SECTION",
        "groups": {"Machine": "Speed, grade and sheet moisture (QCS)", "Steam": "Fresh steam, vent, main condensate and blow-through",
                   "G1": "Steam group 1 (wet end)", "G2": "Steam group 2 (intermediate)", "G3": "Steam group 3 (main)", "G4": "Steam group 4 (dry end)",
                   "Hood": "Hood air and pocket ventilation"},
        "points": [
            {"metric": "speed_mpm", "path": "Machine.Speed", "label": "Machine speed", "unit": "m/min"},
            {"metric": "basis_weight_gsm", "path": "Machine.BasisWeight", "label": "Basis weight at the reel (QCS)", "unit": "g/m²"},
            {"metric": "reel_moisture_pct", "path": "Machine.ReelMoisture", "label": "Moisture at the reel (QCS)", "unit": "%"},
            {"metric": "press_dryness_pct", "path": "Machine.PressDryness", "label": "Sheet dryness entering the dryer section", "unit": "%"},
            {"metric": "steam_total_kgh", "path": "Steam.Total", "label": "Fresh steam to the dryer section", "unit": "kg/h"},
            {"metric": "vent_kgh", "path": "Steam.Vent", "label": "Steam vented to the vent condenser", "unit": "kg/h"},
            {"metric": "cond_main_kgh", "path": "Steam.CondensateMain", "label": "Condensate from groups 3 and 4 (condensing load)", "unit": "kg/h"},
            {"metric": "bt_main_kgh", "path": "Steam.BlowThroughMain", "label": "Blow-through steam from groups 3 and 4 (separator vapour)", "unit": "kg/h"},
        ] + [p for g in range(1, 5) for p in (
            {"metric": f"p{g}_barg", "path": f"G{g}.Pressure", "label": f"Group {g} steam pressure", "unit": "bar g"},
            {"metric": f"dp{g}_kpa", "path": f"G{g}.DP", "label": f"Group {g} differential pressure (steam to condensate header)", "unit": "kPa"},
            {"metric": f"ts{g}_c", "path": f"G{g}.SurfaceMean", "label": f"Group {g} mean cylinder surface temperature", "unit": "°C"},
            {"metric": f"tsmin{g}_c", "path": f"G{g}.SurfaceMin", "label": f"Group {g} coldest cylinder surface temperature", "unit": "°C"},
        )] + [
            {"metric": "hood_humidity_gkg", "path": "Hood.ExhaustHumidity", "label": "Hood exhaust humidity", "unit": "g/kg dry air"},
            {"metric": "hood_exh_temp_c", "path": "Hood.ExhaustTemp", "label": "Hood exhaust temperature", "unit": "°C"},
            {"metric": "hood_exhaust_kgs", "path": "Hood.ExhaustAir", "label": "Hood exhaust air (dry air)", "unit": "kg/s"},
            {"metric": "hood_supply_kgs", "path": "Hood.SupplyAir", "label": "Hood supply air (dry air)", "unit": "kg/s"},
            {"metric": "pv_air_temp_c", "path": "Hood.PVTemp", "label": "Pocket ventilation air temperature", "unit": "°C"},
            {"metric": "pocket_humidity_gkg", "path": "Hood.PocketHumidity", "label": "Pocket humidity, main group", "unit": "g/kg dry air"},
        ],
    },
    "twin_model": {
        "limits": {
            "cold_cyl_alert_k": 12.0, "dt_surface_alert_c": 30.0, "bt_ratio_high": 1.5, "bt_ratio_low": 0.65, "vent_alert_pct": 2.0,
            "ssc_alert": 1.50, "dry_coef_ratio_low": 0.87, "pocket_humidity_alert_gkg": 200.0, "hood_humidity_low_gkg": 120.0,
            "hood_humidity_high_gkg": 200.0, "air_balance_low": 0.7, "air_balance_high": 0.9, "balance_mismatch_pct": 8.0,
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "flooded_cylinder": {"name": "Flooded cylinder (broken or lifted syphon)", "part": "syphon",
                             "symptoms": "one cylinder of group 3 runs far colder than the rest of its group; pressure and differential pressure normal",
                             "rules": ["DRY_COLD_CYLINDER"], "default_ramp_min": 1},
        "low_dp": {"name": "Differential pressure lost in group 3 (thermocompressor or DP control)", "part": "steam",
                   "symptoms": "group 3 DP low, the whole group runs colder, blow-through falls", "rules": ["DRY_DP_LOW", "DRY_SURF_DT_HIGH", "DRY_BLOWTHROUGH_LOW"],
                   "default_ramp_min": 1},
        "syphon_wear": {"name": "Eroded syphon elbows and shoes in group 4", "part": "syphon",
                        "symptoms": "blow-through well above what the DP explains; surfaces only slightly colder", "rules": ["DRY_BLOWTHROUGH_HIGH"], "default_ramp_min": 1.5},
        "vent_valve_passing": {"name": "Vent valve passing (steam to the vent condenser)", "part": "steam",
                               "symptoms": "vented steam up, specific steam consumption up, sheet-side and steam-side balance still agree",
                               "rules": ["DRY_VENT_HIGH", "DRY_SSC_HIGH"], "default_ramp_min": 1},
        "fabric_filling": {"name": "Dryer fabric filled (low permeability)", "part": "fabric",
                           "symptoms": "pocket humidity up, steam pressure raised to hold reel moisture, less evaporation per degree of surface temperature",
                           "rules": ["DRY_RATE_LOW", "DRY_POCKET_HUMID_HIGH"], "default_ramp_min": 1.5},
        "hood_exhaust_high": {"name": "Too much hood exhaust air", "part": "hood",
                              "symptoms": "exhaust humidity low (heating air that carries little water), supply/exhaust ratio low",
                              "rules": ["DRY_HOOD_HUMID_LOW", "DRY_AIR_BALANCE"], "default_ramp_min": 1},
        "hood_exhaust_low": {"name": "Hood exhaust fan short of air", "part": "hood",
                             "symptoms": "exhaust humidity high (condensation and drips in the hood), supply/exhaust ratio above 1",
                             "rules": ["DRY_HOOD_HUMID_HIGH", "DRY_AIR_BALANCE"], "default_ramp_min": 1},
        "steam_meter_drift": {"name": "Fresh steam flow meter reading low", "part": "instrument",
                              "symptoms": "specific steam consumption looks better than it is; sheet-side and steam-side evaporation disagree",
                              "rules": ["DRY_BALANCE_MISMATCH"], "default_ramp_min": 1},
    },
    "presentation": {"title": "PM-4301 dryer section", "dashboard": "PAPER_DRYER_SECTION"},
}

out = HERE / "twin" / "pm-4301.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
