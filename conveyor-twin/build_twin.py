"""Write twin/cv-3801.twin.json: the overland belt conveyor twin (CV-3801).

    python build_twin.py

CV-3801 is an overland belt conveyor in a mine: it carries crushed ore 2.5 km and 40 m uphill from the primary crusher to the
stockpile. Head drive with one rubber-lagged drive pulley and two 560 kW motors (one on each end of the pulley shaft, VFDs
with master / follower torque sharing), gravity take-up on the slack side just after the drive, three-roll 30 degree carrying
idlers, Fenner Dunlop Steelcord ST2000 belt, 1200 mm wide.

Sources and assumptions (every number below is either from a checked source or labelled as an assumption in "source"):
  ISO 5048:1989 (checked in the published preview): F_U = C f L g [q_RO + q_RU + (2 q_B + q_G)] + q_G H g (+ special
    resistances), C = (L + L0) / L with L0 = 70 to 100 m and C >= 1.02, f = 0.02 basic value, q_G = I_V rho / v,
    P_A = F_U v, P_M = P_A / eta1 with eta1 = 0.85 to 0.95, F2min >= F_Umax / (e^(mu phi) - 1), mu from its Table 4,
    wrap angle phi about 2.8 to 4.2 rad.
  Fenner Dunlop Steelcord datasheet (steelcord-en.pdf): ST2000 cord 5.2 mm, pitch 12.0 mm, carcass 13.3 kg/m2, minimum cover
    4 mm, minimum drive pulley 800 mm, tail / tension / bend 630 mm, snub 500 mm; belt mass = carcass + 1.15 x covers (mm).
  Everything else (idler masses, bulk density, stiffness, take-up, limits): ASSUMPTIONS of a typical overland conveyor.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with your conveyor design report / supplier data"
FD = "Fenner Dunlop Steelcord datasheet (fennerdunlopemea.com, steelcord-en.pdf)"

# belt: Fenner Dunlop Steelcord ST2000, covers 10 mm top + 6 mm bottom
carcass, top, bottom, width = 13.3, 10.0, 6.0, 1.2
belt_kg_m2 = carcass + 1.15 * (top + bottom)
belt_kg_m = round(belt_kg_m2 * width, 2)

twin = {
    "$comment": "CV-3801 overland belt conveyor twin. Expected drive power, tensions, slip and take-up position are computed in Maximo Monitor from the design data (ISO 5048 method); the device sends only what it measures.",
    "twin": {"id": "CV-3801", "name": "Overland belt conveyor CV-3801", "version": "1.0.0", "folder": "conveyor-twin"},
    "identification": {
        "asset": "CV-3801", "assetnum": "CV-3801", "manufacturer": "Fenner Dunlop (belt)",
        "model": "Steelcord ST2000, 1200 mm, RS covers 10 + 6 mm",
        "description": "Overland ore conveyor, primary crusher to stockpile: 2.5 km, +40 m lift, 2 x 560 kW head drive",
        "belt": "Fenner Dunlop Steelcord ST2000 steel cord belt, 1200 mm wide, RS covers (DIN W / ISO D abrasion class) 10 mm top, 6 mm bottom",
        "drive": "Head drive: one rubber-lagged drive pulley (1000 mm), two 560 kW motors with gearboxes and VFDs (master / follower torque sharing)",
        "takeup": "Gravity take-up with 22 t counterweight on the slack side, just after the drive",
        "idlers": "Three-roll 30 degree carrying idlers every 1.2 m, single-roll return idlers every 3.0 m",
        "monitoring": "Belt weigher, non-driven pulley speed encoder, take-up load pins and position, belt tracking sensors at head and tail, fixed idler thermal scanners, steel cord belt scanner",
    },
    "design": {
        "route": {"length_m": 2500.0, "lift_m": 40.0, "source": "Plant layout of the conveyor (centre distance and lift): " + A},
        "belt": {
            "type": "ST2000", "width_m": width, "strength_n_per_mm": 2000.0, "cord_diameter_mm": 5.2, "cord_pitch_mm": 12.0,
            "carcass_kg_m2": carcass, "top_cover_mm": top, "bottom_cover_mm": bottom, "mass_kg_m2": round(belt_kg_m2, 2), "q_b_kg_m": belt_kg_m,
            "min_drive_pulley_mm": 800, "min_bend_pulley_mm": 630,
            "stiffness_n": 96.0e6,
            "source": FD + ": strength, cord diameter and pitch, carcass weight, minimum pulley diameters and the rule belt mass = carcass + "
                      "1.15 x cover thickness (mm). Cover thicknesses 10 + 6 mm and the belt stiffness (force per unit strain, from 0.25 % "
                      "elastic elongation at 10 % of the breaking strength): " + A,
        },
        "idlers": {"q_ro_kg_m": 16.25, "q_ru_kg_m": 5.0, "carry_spacing_m": 1.2, "return_spacing_m": 3.0, "roll_diameter_mm": 133, "trough_deg": 30,
                   "source": "Rotating mass of the idler rolls per metre (3 x 6.5 kg carrying rolls every 1.2 m, 15 kg return roll every 3.0 m): " + A},
        "resistance": {"f": 0.020, "L0_m": 85.0, "g": 9.81,
                       "source": "ISO 5048:1989 clause 5.1.3: basic artificial friction coefficient f = 0.02 (three-roll 30 degree idlers, 108-159 mm rolls, "
                                 "about 5 m/s, 70-110 % load, about 20 C); clause 5.1.2: C = (L + L0) / L with L0 between 70 and 100 m (85 m taken)."},
        "material": {"bulk_density_t_m3": 1.6, "design_tph": 2500.0, "source": "Crushed ore, loose bulk density and design capacity: " + A},
        "drive": {"speed_ms": 4.5, "motors": 2, "motor_rated_kw": 560.0, "eta": 0.92, "pulley_mm": 1000, "mu": 0.35, "wrap_deg": 210.0,
                  "source": "ISO 5048:1989: eta1 between 0.85 and 0.95 (0.92 taken), mu = 0.35 for rubber lagging with herringbone grooves in clean and wet "
                            "conditions (Table 4), wrap angle in the 160-240 degree range. Motor rating, belt speed and pulley size: " + A},
        "takeup": {"counterweight_t": 22.0, "travel_m": 6.0, "x0_m": 1.5,
                   "source": "Gravity take-up: counterweight mass, available carriage travel and the carriage position with the new belt at standstill (x0): " + A},
        "demo": {"time_scale": 1, "tph_mean": 2250.0, "tph_min": 2050.0, "tph_max": 2400.0, "ambient_c": 28.0,
                 "note": "Demo only: the feed from the crusher wanders between 2050 and 2400 t/h; the plant clock runs in real time and the readings do not depend on the time of day."},
    },
    "telemetry": {
        "event": "conveyor", "publish_every_s": 10, "device_type": "BELT_CONVEYOR_OVERLAND",
        "groups": {"Process": "Load and belt speed", "Drive": "Drive pulley and motors", "TakeUp": "Gravity take-up", "Belt": "Belt tracking",
                   "Idlers": "Idler thermal scanners", "Scan": "Steel cord belt scanner", "Status": "Conveyor state"},
        "points": [
            {"metric": "tonnage_tph", "path": "Process.Tonnage", "label": "Belt weigher: mass flow", "unit": "t/h"},
            {"metric": "belt_speed_ms", "path": "Process.BeltSpeed", "label": "Belt speed at a non-driven pulley", "unit": "m/s"},
            {"metric": "drive_pulley_speed_ms", "path": "Drive.PulleySpeed", "label": "Drive pulley surface speed (from motor speed)", "unit": "m/s"},
            {"metric": "motor1_power_kw", "path": "Drive.M1Power", "label": "Motor 1 power (VFD)", "unit": "kW"},
            {"metric": "motor2_power_kw", "path": "Drive.M2Power", "label": "Motor 2 power (VFD)", "unit": "kW"},
            {"metric": "takeup_force_kn", "path": "TakeUp.Force", "label": "Take-up pulley force (load pins)", "unit": "kN"},
            {"metric": "takeup_position_m", "path": "TakeUp.Position", "label": "Take-up carriage position", "unit": "m"},
            {"metric": "tracking_head_mm", "path": "Belt.TrackHead", "label": "Belt off-centre at the head (+ = right)", "unit": "mm"},
            {"metric": "tracking_tail_mm", "path": "Belt.TrackTail", "label": "Belt off-centre at the tail (+ = right)", "unit": "mm"},
            {"metric": "idler_max_temp_c", "path": "Idlers.MaxTemp", "label": "Hottest idler in the last thermal scan", "unit": "°C"},
            {"metric": "idler_hot_count", "path": "Idlers.HotCount", "label": "Idlers more than 20 K above ambient", "unit": "count"},
            {"metric": "ambient_temp_c", "path": "Idlers.Ambient", "label": "Ambient temperature", "unit": "°C"},
            {"metric": "splice_max_growth_mm", "path": "Scan.SpliceGrowthMax", "label": "Largest splice length growth since installation", "unit": "mm"},
            {"metric": "splice_worst_id", "path": "Scan.SpliceWorst", "label": "Number of the splice with the largest growth", "unit": "code"},
            {"metric": "cord_damage_count", "path": "Scan.CordDamage", "label": "Cord damage indications in the last scan", "unit": "count"},
            {"metric": "top_cover_min_mm", "path": "Scan.CoverMin", "label": "Thinnest top cover in the last thickness survey", "unit": "mm"},
            {"metric": "running", "path": "Status.Running", "label": "Conveyor running (1) or stopped (0)", "unit": "code"},
        ],
    },
    "twin_model": {
        "limits": {
            "power_ratio_alert": 1.15, "load_imbalance_pct": 10.0, "slip_excess_pct": 0.5, "slip_margin_alert": 1.1,
            "takeup_tension_ratio": 0.85, "takeup_travel_ratio": 0.85, "elongation_alert_pct": 0.12,
            "idler_dt_alert_k": 20.0, "idler_dt_critical_k": 50.0, "splice_growth_alert_mm": 10.0, "splice_growth_limit_mm": 20.0,
            "tracking_alert_mm": 50.0, "tracking_limit_mm": 100.0, "cover_min_mm": 3.0,
            "source": "Alert limits: " + A + ". Splice growth and cover limits must come from the belt supplier and the splicing contractor.",
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "high_resistance": {"name": "High running resistance (spillage, build-up, cold, sticky idlers)", "part": "route",
                            "symptoms": "drive power above the ISO 5048 expectation at the same tonnage; apparent friction factor up",
                            "rules": ["CV_POWER_HIGH"], "default_ramp_min": 1.5},
        "idler_bearing_failure": {"name": "Idler bearing failure", "part": "idlers", "symptoms": "one idler hot on the thermal scan, then very hot (fire risk)",
                                  "rules": ["CV_IDLER_HOT", "CV_IDLER_CRITICAL"], "default_ramp_min": 1.5},
        "lagging_wear": {"name": "Drive pulley lagging worn or wet and dirty", "part": "drive", "symptoms": "belt slips on the drive pulley with normal take-up tension",
                         "rules": ["CV_SLIP"], "default_ramp_min": 1},
        "takeup_jammed": {"name": "Take-up carriage jammed", "part": "takeup", "symptoms": "take-up force low, slack-side tension below the Euler-Eytelwein minimum, then slip",
                          "rules": ["CV_TAKEUP_TENSION_LOW", "CV_SLIP_MARGIN_LOW", "CV_SLIP"], "default_ramp_min": 1},
        "belt_stretch": {"name": "Permanent belt elongation (stretch)", "part": "belt", "symptoms": "take-up carriage creeps to the end of its travel",
                         "rules": ["CV_TAKEUP_TRAVEL_END", "CV_BELT_STRETCH"], "default_ramp_min": 1.5},
        "splice_failure": {"name": "Steel cord splice deterioration", "part": "belt", "symptoms": "belt scanner shows one splice getting longer",
                           "rules": ["CV_SPLICE_GROWTH", "CV_SPLICE_CRITICAL"], "default_ramp_min": 1.5},
        "mistracking": {"name": "Belt mistracking (misalignment)", "part": "belt", "symptoms": "belt runs off centre at the tail, power a little up",
                        "rules": ["CV_MISTRACKING", "CV_MISTRACKING_SEVERE"], "default_ramp_min": 1},
        "load_share_imbalance": {"name": "Motor load sharing lost", "part": "drive", "symptoms": "one motor carries most of the load and goes over its rating",
                                 "rules": ["CV_LOAD_SHARE", "CV_MOTOR_OVERLOAD"], "default_ramp_min": 0.5},
    },
    "presentation": {"title": "CV-3801 overland belt conveyor", "dashboard": "BELT_CONVEYOR_OVERLAND"},
}

out = HERE / "twin" / "cv-3801.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out, f"(belt {belt_kg_m2:.2f} kg/m2, q_B {belt_kg_m} kg/m)")
