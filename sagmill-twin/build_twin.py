"""Write twin/ml-3901.twin.json: the SAG mill twin (ML-3901).

    python build_twin.py

ML-3901 is the semi-autogenous grinding (SAG) mill of an SABC circuit (SAG mill, ball mill, pebble crusher) at a copper
concentrator. It is a mill at the top of the published Metso Outotec Select SAG range: 9.0 m diameter, 4.5 m effective
grinding length (EGL), 7,800 kW installed, driven through a ring gear and pinion by an induction motor and a reducer, and
carried on two trunnion bearings with hydrostatic lift pockets. Steel shell liners and lifters protect the shell.

Sources (public):
  Metso Outotec Select horizontal grinding mills leaflet (4297-03-19-EN): SAG models 3.80 to 9.00 m diameter, 1.90 to
      4.50 m EGL, 400 to 7,800 kW installed; scope: rotating mill structure, gear and guard, bearing housings, main reducer,
      induction drivetrain, start-up set of lining.
  Austin (1990) SAG mill power model, as written and checked by A. Doll (Procemin 2013, "A comparison of SAG mill power
      models"): P_shell = K D^2.5 L (1 - A J) [(1 - eps) (rho_s / wc) J + 0.6 Jb (rho_b - rho_s / wc)] phi (1 - 0.1 / 2^(9 - 10 phi))
      with K = 10.6, A = 1.03, eps = 0.3, wc = 0.80, rho_b = 7.8 t/m3, D inside the liners; plus 5 % for the cone ends;
      0.931 between motor input and mill shell. (Doll's worked example, 7.7 m x 3.35 m, J 0.226, Jb 0.135, 75 % critical:
      2,965 kW for the cylinder; this file's twin_calc reproduces it.)
  Morrell SMC Test coarse-particle specific energy (Morrell, technical note, appendix A, as reproduced by 911metallurgist):
      Wa = K1 Mia 4 (x2^f(x2) - x1^f(x1)), f(x) = -(0.295 + x / 1,000,000), x2 = 750 um, x1 = feed P80 (um),
      K1 = 0.95 for circuits with a recycle pebble crusher, 1.0 without.
  Critical speed (textbook): n_c = 42.3 / sqrt(D) rpm, D in m.
  Bearing pressure as a load indicator: the trunnion bearing oil pressure is a function of the mill load (911metallurgist,
      AG/SAG grinding circuit control); above about 35 to 37 % filling the power falls as the load rises (overload).
Assumptions (labelled in "source"): liner thickness, mass and wear rate, empty mill mass, bearing effective area, the
  site calibration of Wa, ore properties, every alarm limit.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with "

twin = {
    "$comment": "ML-3901 SAG mill twin. Expected values in Maximo Monitor from the mill datasheet, a published power model and the ore's SMC test results; the device sends only what it measures.",
    "twin": {"id": "ML-3901", "name": "SAG mill ML-3901", "version": "1.0.0", "folder": "sagmill-twin"},
    "identification": {
        "asset": "ML-3901", "assetnum": "ML-3901", "manufacturer": "Metso Outotec",
        "model": "Select SAG mill, 9.0 m diameter x 4.5 m EGL class (top of the published Select range)",
        "description": "Primary SAG mill of the SABC grinding circuit (SAG mill, pebble crusher, ball mill)",
        "drive": "Ring gear and single pinion, main reducer, induction motor (fixed speed)",
        "bearings": "Two trunnion bearings with hydrostatic lift pockets, one lube system",
        "liners": "Steel shell liners with lifter bars, steel head liners, discharge grates and pulp lifters",
    },
    "design": {
        "mill": {
            "d_shell_m": 9.0, "egl_m": 4.5, "installed_kw": 7800.0, "cone_allowance": 0.05,
            "speed_fraction_design": 0.75, "crit_const": 42.3,
            "source": "Metso Outotec Select horizontal grinding mills leaflet: SAG 3.80-9.00 m diameter, 1.90-4.50 m EGL, "
                      "400-7,800 kW installed; this mill is taken at the top of that range (" + A + "your mill datasheet). "
                      "Critical speed n_c = 42.3 / sqrt(D) rpm (textbook). Cone-end allowance +5 % (Doll 2013). Design speed 75 % of critical: " + A + "your datasheet.",
        },
        "power_model": {
            "K": 10.6, "A": 1.03, "eps": 0.3, "wc": 0.80, "rho_ball": 7.8, "drive_eff": 0.931,
            "source": "Austin (1990) SAG power model with K = 10.6, A = 1.03, bed porosity 0.3, charge solids 0.80, balls 7.8 t/m3, "
                      "as written by Doll (Procemin 2013); motor input to mill shell 0.931 (Doll). Power at the mill shell.",
        },
        "liners": {
            "t_new_mm": 150.0, "t_min_mm": 50.0, "mass_new_t": 140.0, "plan_life_kt": 6000.0,
            "source": "Effective shell liner thickness new and at the reline limit, liner mass new, planned liner life in kilotonnes "
                      "milled (wear assumed linear with tonnage): " + A + "the liner supplier's design and your own wear scans.",
        },
        "mass": {
            "empty_ex_liners_t": 420.0, "a_eff_m2": 0.50,
            "source": "Rotating mass of the empty mill without liners, and the effective lift area of one trunnion bearing that turns pocket "
                      "pressure into load: " + A + "the mill datasheet and a bearing pressure calibration at a grind-out (empty mill) and a crash stop.",
        },
        "charge": {
            "j_design": 0.28, "jb_design": 0.12, "j_overload": 0.35,
            "source": "Total filling and ball filling (fractions of mill volume) at design; filling above which the power falls as the load "
                      "rises. 911metallurgist (AG/SAG control): power drops above about 35-37 % filling. Design fillings: " + A + "your process design.",
        },
        "ore": {
            "mia_design": 18.0, "sg_design": 2.75, "f80_mm_design": 120.0, "K1": 0.95, "x2_um": 750.0, "wa_share": 1.0,
            "source": "Morrell SMC equation Wa = K1 Mia 4 (750^f(750) - x1^f(x1)), f(x) = -(0.295 + x/1e6), K1 = 0.95 with a pebble crusher. "
                      "Mia, ore density and feed F80 at design: " + A + "your SMC tests and the ore block model. wa_share = SAG mill specific energy "
                      "(motor) divided by Wa at the commissioning survey: " + A + "your own survey.",
        },
        "bearings": {"lube_supply_c": 40.0, "rise_normal_k": 5.0,
                     "source": "Lube oil supply temperature and normal bearing temperature rise above the oil: " + A + "the bearing maker's manual."},
        "gear": {"pinion_vib_normal": 2.0, "gear_dt_normal_k": 3.0,
                 "source": "Normal pinion bearing vibration and normal temperature difference across the ring gear face (infrared scanner): " + A + "your baseline."},
        "demo": {"time_scale": 60, "note": "Demo only: the plant clock runs 60 times faster so the tonnage counter moves; the charge settles in about 20 s of real time."},
    },
    "telemetry": {
        "event": "sagmill", "publish_every_s": 10, "device_type": "SAG_MILL",
        "groups": {"Drive": "Motor, speed and ring gear", "Bearing": "Trunnion bearings and lube oil", "Ore": "Feed and ore properties",
                   "Charge": "Ball charge tracker", "Liner": "Liner wear counters and scans"},
        "points": [
            {"metric": "motor_power_kw", "path": "Drive.Power", "label": "Mill motor power", "unit": "kW"},
            {"metric": "mill_speed_rpm", "path": "Drive.Speed", "label": "Mill speed", "unit": "rpm"},
            {"metric": "pinion_vib_mm_s", "path": "Drive.PinionVibration", "label": "Pinion bearing vibration velocity (RMS)", "unit": "mm/s"},
            {"metric": "motor_vib_mm_s", "path": "Drive.MotorVibration", "label": "Motor bearing vibration velocity (RMS)", "unit": "mm/s"},
            {"metric": "gear_dt_k", "path": "Drive.GearFaceDeltaT", "label": "Ring gear temperature difference across the face", "unit": "K"},
            {"metric": "brg_fe_pressure_bar", "path": "Bearing.FeedEndPressure", "label": "Feed-end trunnion bearing pocket pressure", "unit": "bar"},
            {"metric": "brg_de_pressure_bar", "path": "Bearing.DischargeEndPressure", "label": "Discharge-end trunnion bearing pocket pressure", "unit": "bar"},
            {"metric": "brg_fe_temp_c", "path": "Bearing.FeedEndTemperature", "label": "Feed-end bearing temperature", "unit": "°C"},
            {"metric": "brg_de_temp_c", "path": "Bearing.DischargeEndTemperature", "label": "Discharge-end bearing temperature", "unit": "°C"},
            {"metric": "lube_oil_temp_c", "path": "Bearing.LubeSupplyTemperature", "label": "Lube oil supply temperature", "unit": "°C"},
            {"metric": "feed_tph", "path": "Ore.FeedRate", "label": "Fresh feed rate (belt scale)", "unit": "t/h"},
            {"metric": "feed_f80_mm", "path": "Ore.FeedF80", "label": "Feed P80 (image analysis on the feed belt)", "unit": "mm"},
            {"metric": "ore_mia", "path": "Ore.Mia", "label": "Coarse ore work index Mia of the blend (ore tracking)", "unit": "kWh/t"},
            {"metric": "ore_sg", "path": "Ore.Density", "label": "Ore density of the blend", "unit": "t/m³"},
            {"metric": "ball_charge_pct", "path": "Charge.BallFilling", "label": "Ball filling (tracker: last grind-out + balls added - wear)", "unit": "%"},
            {"metric": "liner_kt", "path": "Liner.TonnesSinceReline", "label": "Tonnes milled since the last reline", "unit": "kt"},
            {"metric": "liner_scan_mm", "path": "Liner.ScanThickness", "label": "Shell liner thickness at the last laser scan", "unit": "mm"},
            {"metric": "liner_scan_kt", "path": "Liner.ScanTonnes", "label": "Tonnes since reline at the last scan", "unit": "kt"},
        ],
    },
    "twin_model": {
        "limits": {
            "j_overload_pct": 35.0, "j_loaded_pct": 33.0, "power_ratio_low": 0.92, "se_ratio_high": 1.20,
            "liner_wear_ratio_high": 1.25, "reline_days_alert": 30.0, "brg_rise_alert_k": 10.0, "brg_temp_limit_c": 65.0,
            "brg_split_alert": 0.10, "gear_dt_alert_k": 8.0, "pinion_vib_alert": 4.5, "pinion_vib_limit": 7.1, "ball_charge_high_pct": 15.0,
            "source": "Alarm limits: " + A + "your operating practice. Vibration 4.5 / 7.1 mm/s are typical zone boundaries B/C and C/D "
                      "of ISO 20816-3 for large rigidly mounted machines; take the values for your machine group and support from the standard.",
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "charge_overload": {"name": "Mill overload (charge builds up, slurry pools)", "part": "charge",
                            "symptoms": "bearing pressure and filling rise while the power falls below the model",
                            "rules": ["SAG_OVERLOAD_RISK", "SAG_POWER_DROP_LOADED"], "default_ramp_min": 1.5},
        "liner_wear_fast": {"name": "Shell liners wearing faster than planned", "part": "liners",
                            "symptoms": "laser scan thinner than the tonnage predicts; reline date moves forward",
                            "rules": ["SAG_LINER_WEAR_FAST", "SAG_RELINE_DUE"], "default_ramp_min": 1},
        "lifter_profile_loss": {"name": "Lifters worn flat or packed (grinding efficiency loss)", "part": "liners",
                                "symptoms": "specific energy above the SMC model; throughput down at the same power",
                                "rules": ["SAG_SE_HIGH"], "default_ramp_min": 1},
        "ball_overcharge": {"name": "Ball charge too high", "part": "charge",
                            "symptoms": "ball filling up, power above the drive rating, more liner and ball breakage",
                            "rules": ["SAG_BALL_CHARGE_HIGH", "SAG_GEAR_OVERPOWER"], "default_ramp_min": 1},
        "bearing_lube": {"name": "Trunnion bearing lubrication degraded (feed end)", "part": "bearing",
                         "symptoms": "bearing temperature rises above the oil supply, then past its limit",
                         "rules": ["SAG_BRG_TEMP_HIGH"], "default_ramp_min": 1},
        "pocket_leak": {"name": "Bearing lift pocket leak or pressure transmitter drift", "part": "bearing",
                        "symptoms": "one bearing pressure falls, the load split moves, the charge estimate goes wrong",
                        "rules": ["SAG_BRG_SPLIT"], "default_ramp_min": 0.5},
        "gear_misalignment": {"name": "Ring gear / pinion misalignment", "part": "gear",
                              "symptoms": "temperature difference across the gear face and pinion vibration rise",
                              "rules": ["SAG_GEAR_DT_HIGH", "SAG_PINION_VIB_HIGH"], "default_ramp_min": 1},
    },
    "presentation": {"title": "ML-3901 SAG mill", "dashboard": "SAG_MILL"},
}

out = HERE / "twin" / "ml-3901.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
