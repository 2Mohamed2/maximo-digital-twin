"""Write twin/es-5601.twin.json: the heavy-duty metro escalator twin (ES-5601).

    python build_twin.py

ES-5601 is an up escalator from a metro platform to the ticket hall: a KONE TransitMaster 140 public transport escalator,
10 m rise, 30 degrees, 1000 mm steps, 0.5 m/s, with stand-by (slow) speed when nobody is travelling.

Sources (every number below is either from these or labelled as an assumption in its "source" text):
  KONE TransitMaster 140 "Options and planning dimensions" brochure: inclination 27.3 / 30 deg, step width 1000 mm, rise up to
    18 m, speeds 0.5 / 0.65 / 0.75 m/s (0.4 m/s with inverter), outside roller step chains (rollers 100 x 25 mm), duty
    cycle 20-24 h/day, typical service life up to 150,000 h, stand-by speed operation, auxiliary brake standard above 6 m
    rise, handrail speed monitor, broken step chain switches, comb plate impact switches, step sag switches, missing step
    monitor, speed sensor (EN 115-1:2008 + A1:2010 as printed in the brochure).
  KONE TransitMaster 140 EPD (2021): representative unit 10 m rise, 30 deg, 1000 mm, 0.5 m/s, automatic start/stop,
    max. capacity 6000 persons/h (EN 115-1 for 0.5 m/s), 20 h/day 7 days/week, 25-year reference service life,
    19,428 kg, 87,327 kWh/year (ISO 25745-3 methodology).
  L. Al-Sharif, "The two modes of failure of escalator braking systems" (12th Symposium on Lift & Escalator Technologies):
    no-load power P_NL = 0.47 r + 1.74 kW (r = rise in m); 75 kg per passenger; EN 115 stopping distances
    0.50 m/s: 0.20 to 1.00 m (max: fully loaded, down; min: empty); ASME A17.1-2010/CSA B44-10 max deceleration 0.91 m/s2.
  EN 115-1 brake load for a 1000 mm step: 120 kg per step, steps = rise / riser height (as commonly quoted; check your edition).
  Handrail: 0 to +2 % relative to the steps in normal operation; handrail speed monitor stops the escalator on more than
    15 % deviation for more than 15 s (EN 115-1:2008+A1 as reported by secondary sources; check your edition).
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with the data of your own escalator (manufacturer's commissioning report / service records)"

twin = {
    "$comment": "ES-5601 metro escalator twin. Expected values in Maximo Monitor from KONE data, EN 115-1 limits and published escalator physics; the controller sends only what it measures.",
    "twin": {"id": "ES-5601", "name": "Metro escalator ES-5601", "version": "1.0.0", "folder": "escalator-twin"},
    "identification": {
        "asset": "ES-5601", "assetnum": "ES-5601", "manufacturer": "KONE", "model": "TransitMaster 140",
        "description": "Heavy-duty public transport escalator, platform to ticket hall (up), 10 m rise",
        "type": "Heavy-duty (public service) escalator, outside roller step chains, stand-by speed operation",
        "location": "Metro station, platform level to ticket hall (generic)",
        "drive": "Electric motor and gearbox at the upper landing, driving the step chain sprockets; operational brake on the motor shaft, auxiliary brake on the main drive shaft",
        "controller": "Escalator controller with speed sensor, handrail speed monitor, chain elongation sensor and safety circuit diagnostics",
    },
    "design": {
        "geometry": {
            "rise_m": 10.0, "inclination_deg": 30.0, "step_width_mm": 1000, "step_depth_m": 0.40, "flat_steps": 3,
            "source": "Rise, inclination and step width: KONE TransitMaster 140 EPD representative unit (10 m, 30 deg, 1000 mm) and brochure "
                      "(rise up to 18 m, 27.3 or 30 deg, 1000 mm). Three flat steps at each landing: brochure note (EN 115-1, rise above 6 m). "
                      "Step depth 0.40 m: " + A,
        },
        "speed": {
            "rated_ms": 0.5, "standby_ms": 0.2,
            "source": "Rated speed 0.5 m/s: EPD representative unit (brochure: 0.5, 0.65, 0.75 m/s). Stand-by speed operation: brochure; the "
                      "stand-by speed value 0.2 m/s is an " + A,
        },
        "drive": {
            "noload_a_kw_per_m": 0.47, "noload_b_kw": 1.74, "eta_load": 0.85, "friction_share": 0.40, "motor_rated_kw": 30.0,
            "source": "No-load power at rated speed P_NL = 0.47 x rise + 1.74 kW: Al-Sharif (measurement-based model of escalator power). "
                      "Efficiency of the drive for the passenger load (motor + gearbox), share of the no-load power that is mechanical "
                      "friction at the step band, motor rating: " + A,
        },
        "passengers": {
            "mass_kg": 75.0, "max_capacity_ph": 6000, "duty_h_per_day": 20.0, "annual_kwh_epd": 87327,
            "source": "75 kg per passenger: Al-Sharif. Max. capacity 6000 persons/h (EN 115-1 for 0.5 m/s), 20 h/day, 87,327 kWh/year "
                      "(ISO 25745-3 method, automatic start/stop unit): KONE TransitMaster 140 EPD.",
        },
        "brake": {
            "brake_load_kg_per_step": 120.0, "stop_min_m": 0.20, "stop_max_m": 1.00, "decel_asme_ms2": 0.91,
            "m_eq_kg": 16000.0, "delay_s": 0.35,
            "source": "Stopping distance window for 0.50 m/s, 0.20 m (empty) to 1.00 m (fully loaded, down): EN 115-1 as tabulated by "
                      "Al-Sharif. Brake load 120 kg per 1000 mm step, steps = rise / riser: EN 115-1 as commonly quoted (check your "
                      "edition). ASME A17.1/CSA B44 maximum deceleration 0.91 m/s2: as quoted by Al-Sharif (for comparison only). "
                      "Equivalent moving mass of step band, chains, handrails and rotating parts at the steps, and the delay from the "
                      "stop command until full brake torque: " + A,
        },
        "handrail": {
            "tol_min_pct": 0.0, "tol_max_pct": 2.0, "monitor_trip_pct": 15.0, "monitor_trip_s": 15.0, "nominal_pct": 1.0,
            "source": "Handrail speed 0 to +2 % of the step speed in normal operation; monitor stops the escalator at more than 15 % "
                      "deviation for more than 15 s: EN 115-1 as reported by secondary sources (check the clause of your edition). "
                      "Nominal +1 % setting: " + A,
        },
        "chain": {
            "elong0_pct": 0.10, "wear_pct_per_1000h": 0.0070, "alert_pct": 1.0, "replace_pct": 1.5, "fast_wear_pct": 0.30,
            "source": "Outside roller step chains (rollers 100 x 25 mm): KONE brochure. Initial elongation after running-in, wear rate, "
                      "alert and replacement elongation: " + A + " (the chain maker's wear limit)",
        },
        "gearbox": {
            "oil_rise0_k": 18.0, "oil_k_per_kw": 1.2, "oil_alert_k": 10.0, "vib_baseline_mms": 1.2, "vib_ratio_alert": 2.5,
            "source": "Gear oil temperature above ambient at no load and per kW of 15-minute mean motor power, vibration baseline at "
                      "commissioning, alert levels: " + A,
        },
        "safety": {
            "comb_trips_alert": 3, "step_sag_trips_alert": 2,
            "source": "Safety devices (comb plate impact, handrail inlet, step sag, emergency stop): KONE brochure. Alert counts per 24 h: " + A,
        },
        "energy": {
            "standby_share_expected": 0.25, "standby_share_alert": 0.10,
            "source": "Share of running time at stand-by speed expected for this station's traffic, and the alert level: " + A,
        },
        "usage": {"run_hours_now": 62000.0, "service_life_h": 150000,
                  "source": "Typical service life up to 150,000 h: KONE brochure. Run hours of this unit: " + A},
        "demo": {
            "time_scale": 1, "train_every_s": 150, "train_peak_ppm": 90.0, "train_tau_s": 25.0, "standby_after_s": 10,
            "stop_every_s": 10, "ambient_c": 22.0,
            "note": "Demo only: a train arrives every 150 s of real time and its passengers ride up in a burst; the escalator drops to "
                    "stand-by speed when nobody has entered for 10 s. A stop is recorded every 10 s so the brake values update often; "
                    "in service they come from the last real stop (night shutdown, emergency stop or safety trip).",
        },
    },
    "telemetry": {
        "event": "escalator", "publish_every_s": 10, "device_type": "ESCALATOR_HEAVY_DUTY",
        "groups": {"Drive": "Motor and step band", "Load": "Passengers", "Handrail": "Handrail speeds", "Chain": "Step chain",
                   "Gearbox": "Gearbox", "Env": "Environment", "Brake": "Last stop (brake)", "Safety": "Safety circuit trips, last 24 h",
                   "Usage": "Run hours and energy saving"},
        "points": [
            {"metric": "motor_power_kw", "path": "Drive.Power", "label": "Motor input power", "unit": "kW"},
            {"metric": "motor_power_avg_kw", "path": "Drive.Power15", "label": "Motor input power, 15-minute mean", "unit": "kW"},
            {"metric": "step_speed_ms", "path": "Drive.StepSpeed", "label": "Step band speed", "unit": "m/s"},
            {"metric": "run_mode", "path": "Drive.Mode", "label": "Mode (2 rated speed, 1 stand-by speed, 0 stopped)", "unit": "code"},
            {"metric": "direction", "path": "Drive.Direction", "label": "Direction (1 up, -1 down)", "unit": "code"},
            {"metric": "passengers_per_min", "path": "Load.Flow", "label": "Passengers entering per minute (landing counter)", "unit": "1/min"},
            {"metric": "handrail_left_ms", "path": "Handrail.Left", "label": "Left handrail speed", "unit": "m/s"},
            {"metric": "handrail_right_ms", "path": "Handrail.Right", "label": "Right handrail speed", "unit": "m/s"},
            {"metric": "chain_elongation_pct", "path": "Chain.Elongation", "label": "Step chain elongation", "unit": "%"},
            {"metric": "gear_oil_temp_c", "path": "Gearbox.OilTemp", "label": "Gear oil temperature", "unit": "°C"},
            {"metric": "gearbox_vib_mms", "path": "Gearbox.Vibration", "label": "Gearbox vibration velocity (RMS)", "unit": "mm/s"},
            {"metric": "ambient_temp_c", "path": "Env.Ambient", "label": "Machine space temperature", "unit": "°C"},
            {"metric": "last_stop_distance_m", "path": "Brake.Distance", "label": "Stopping distance of the last stop", "unit": "m"},
            {"metric": "last_stop_decel_ms2", "path": "Brake.Deceleration", "label": "Mean deceleration under full brake torque, last stop", "unit": "m/s²"},
            {"metric": "last_stop_delay_s", "path": "Brake.Delay", "label": "Delay from stop command to full brake torque, last stop", "unit": "s"},
            {"metric": "last_stop_speed_ms", "path": "Brake.Speed", "label": "Step speed at the last stop command", "unit": "m/s"},
            {"metric": "last_stop_load_kg", "path": "Brake.Load", "label": "Passenger load at the last stop (controller estimate)", "unit": "kg"},
            {"metric": "last_stop_dir", "path": "Brake.Direction", "label": "Direction at the last stop (1 up, -1 down)", "unit": "code"},
            {"metric": "trips_comb_24h", "path": "Safety.Comb", "label": "Comb plate impact switch trips, 24 h", "unit": "count"},
            {"metric": "trips_handrail_inlet_24h", "path": "Safety.HandrailInlet", "label": "Handrail inlet switch trips, 24 h", "unit": "count"},
            {"metric": "trips_step_sag_24h", "path": "Safety.StepSag", "label": "Step sag / missing step trips, 24 h", "unit": "count"},
            {"metric": "trips_estop_24h", "path": "Safety.EStop", "label": "Passenger emergency stops, 24 h", "unit": "count"},
            {"metric": "run_hours", "path": "Usage.RunHours", "label": "Run hours since commissioning", "unit": "h"},
            {"metric": "standby_share_24h", "path": "Usage.StandbyShare", "label": "Share of running time at stand-by speed, 24 h", "unit": "-"},
        ],
    },
    "twin_model": {
        "limits": {
            "drag_ratio_alert": 1.3, "stop_margin_frac": 0.85, "handrail_slip_pct": -10.0,
            "chain_alert_pct": 1.0, "chain_replace_pct": 1.5, "chain_fast_wear_pct": 0.30,
            "oil_residual_alert_k": 10.0, "vib_ratio_alert": 2.5, "comb_trips_alert": 3, "step_sag_trips_alert": 2,
            "standby_share_alert": 0.10,
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "brake_weak": {"name": "Brake lining worn / brake too weak", "part": "brake",
                       "symptoms": "longer delay and less brake force: the predicted fully loaded down stop leaves the EN 115-1 window",
                       "rules": ["ESC_STOP_MARGIN_LOW", "ESC_STOP_TOO_LONG"], "default_ramp_min": 1.5},
        "brake_harsh": {"name": "Brake set too hard (harsh stop)", "part": "brake",
                        "symptoms": "short delay and high brake force: an empty stop shorter than the EN 115-1 minimum, passengers may fall",
                        "rules": ["ESC_STOP_HARSH"], "default_ramp_min": 1},
        "handrail_slip": {"name": "Handrail drive slip (worn friction wheel, handrail stretch)", "part": "handrail",
                          "symptoms": "left handrail slower than the steps, first outside 0 to +2 %, then close to the monitor trip",
                          "rules": ["ESC_HANDRAIL_OUT_OF_TOL", "ESC_HANDRAIL_SLIP"], "default_ramp_min": 1.5},
        "chain_wear": {"name": "Step chain wear (lubrication failure)", "part": "step chain",
                       "symptoms": "elongation grows faster than the wear line of the run hours, then reaches the replacement limit",
                       "rules": ["ESC_CHAIN_WEAR_FAST", "ESC_CHAIN_ELONG_ALERT", "ESC_CHAIN_ELONG_LIMIT"], "default_ramp_min": 1.5},
        "step_band_drag": {"name": "Step band drag (worn step rollers, misaligned tracks)", "part": "step band",
                           "symptoms": "no-load power up at the same passenger flow, step sag trips",
                           "rules": ["ESC_DRAG_HIGH", "ESC_STEP_SAG_TRIPS"], "default_ramp_min": 1},
        "gearbox_wear": {"name": "Gearbox wear or low oil", "part": "gearbox",
                         "symptoms": "gear oil hotter than the power explains, vibration up",
                         "rules": ["ESC_GEAR_OIL_HOT", "ESC_GEAR_VIB_HIGH"], "default_ramp_min": 1},
        "comb_damage": {"name": "Comb plate damage (broken teeth, debris)", "part": "comb plate",
                        "symptoms": "repeated comb plate impact switch trips",
                        "rules": ["ESC_COMB_TRIPS"], "default_ramp_min": 0.5},
        "standby_disabled": {"name": "Energy-saving stand-by speed disabled", "part": "controller",
                             "symptoms": "escalator stays at rated speed with nobody on it; energy per passenger up",
                             "rules": ["ESC_STANDBY_UNUSED"], "default_ramp_min": 0.5},
    },
    "presentation": {"title": "ES-5601 metro escalator", "dashboard": "ESCALATOR_HEAVY_DUTY"},
}

out = HERE / "twin" / "es-5601.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
