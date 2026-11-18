"""Write twin/pm-5501.twin.json: the railway point machine twin (PM-5501).

    python build_twin.py

PM-5501 is an electro-mechanical point machine of the Siemens S700K type driving one switch (turnout) with external
locking. A condition monitoring unit (CMU) in the interlocking's equipment room clamps onto the three motor phases and
records the power curve of every throw; it reduces each curve to a few numbers per phase (unlock, drive, lock) and keeps
them until the next throw. The interlocking reports detection and trailing; the point heating controller reports the
heater state and current.

Sources (checked) and assumptions:
  Siemens Mobility, "S 700 K point machine: setting points reliably" (brochure, order no. A19100-V100-B802-V3-7600):
    throwing force 5,500 N, retention force 7,000 N, max. permitted restoring force of the blades 1,400 N, trailing
    resistance 9,000 + 500 N, stroke 150 / 220 mm, throwing time 5 s (150 mm) / 6 s (220 mm), rated current 2 A,
    starting current 8 A (at 400 V 3~ 50 Hz and 45 ohm core resistance), max. line resistance 54 ohm, weight approx.
    120 kg, IP54 to IEC 60529, -30 to +70 C, MTBF around 550,000 h, general overhaul after one million throws.
  Bian, Yang, Huang, Xu, Liu, Zio, "Degradation detection method for railway point machines" (arXiv:1809.02349):
    S700K power curve in four phases: start-release (about 1 s, peak 1 to 2 kW), switch (about 3 s, about 0.5 kW),
    lock (about 1 s), indication (slow-release about 0.2 kW, about 1.6 s), about 6.6 s in all; unlocking fault with a
    phase-1 peak of about 4.2 kW; a stuck drive rod or a blocked detector rod run at 0.5 to 1 kW until the time limit.
  Everything else (no-load power, efficiency, temperature coefficients, heater rating, alarm limits, time limit) is an
  ASSUMPTION of a typical value, labelled in each "source" string, to be replaced by your own machine's commissioning
  record (reference curve) and the maintainer's standards.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

SIE = "Siemens S 700 K point machine brochure, technical data (A19100-V100-B802-V3-7600)"
BIAN = "Bian et al., Degradation detection method for railway point machines (arXiv:1809.02349), S700K power curve"
A = "assumption: typical value, replace with the reference curve recorded at commissioning of your own machine"

twin = {
    "$comment": "PM-5501 point machine twin. Expected values in Maximo Monitor from the maker's data sheet and the commissioning reference curve; the CMU sends only what it measures on each throw.",
    "twin": {"id": "PM-5501", "name": "Point machine PM-5501", "version": "1.0.0", "folder": "points-twin"},
    "identification": {
        "asset": "PM-5501", "assetnum": "PM-5501", "manufacturer": "Siemens",
        "model": "S700K point machine (220 mm stroke, 400 V 3~)",
        "description": "Point machine of a main-line turnout with external clamp locks, with a condition monitoring unit on the motor supply",
        "turnout": "Main-line turnout, switch blades with external clamp locks, one S700K at the toe (typical layout, no real site)",
        "monitoring": "Condition monitoring unit (CMU) on the three motor phases: power curve per throw, split into unlock, drive and lock",
        "heating": "Electric point heating with its own controller (switch-on below a rail temperature set point)",
    },
    "design": {
        "machine": {
            "throwing_force_n": 5500.0, "retention_force_n": 7000.0, "restoring_force_max_n": 1400.0,
            "trailing_resistance_n": 9000.0, "stroke_mm": 220.0, "throw_time_s": 6.0,
            "rated_current_a": 2.0, "starting_current_a": 8.0, "supply_v": 400.0, "line_resistance_max_ohm": 54.0,
            "weight_kg": 120.0, "ip": "IP54", "temp_min_c": -30.0, "temp_max_c": 70.0,
            "mtbf_h": 550000.0, "overhaul_throws": 1000000.0,
            "source": SIE + ". Throwing time, rated and starting current are given for 400 V 3~ 50 Hz and 45 ohm core resistance.",
        },
        "curve": {
            "unlock_s": 1.0, "drive_s": 4.0, "lock_s": 1.0,
            "drive_power_w": 500.0, "unlock_peak_w": 1500.0, "unlock_peak_fault_w": 4200.0,
            "source": BIAN + ": phases start-release about 1 s (peak 1 to 2 kW), switch about 3 s at about 0.5 kW, lock about 1 s; "
                      "unlocking fault peak about 4.2 kW. The split 1 / 4 / 1 s is that curve stretched to the 6 s of the data sheet "
                      "(assumption); replace it with your commissioning reference curve.",
        },
        "model": {
            "no_load_w": 280.0, "efficiency": 0.35, "start_energy_j": 150.0,
            "force_ref_n": 2000.0, "t_low_c": 10.0, "t_high_c": 40.0, "k_cold_n_per_k": 20.0, "k_hot_n_per_k": 25.0,
            "source": "Electrical power = no-load power + force x speed / efficiency, with the throw bar moving at the nominal "
                      "speed (stroke / throwing time). No-load power, overall efficiency (motor x gear x ball screw), start "
                      "energy and the drive force of the turnout at 10 to 40 C rail temperature: " + A + ". Check: they give "
                      "about 0.5 kW while driving and about 0.86 kW when the clutch slips at 5.5 kN, as in the published S700K "
                      "curves. Temperature correction (cold: lubricant and chairs; hot: rail expansion and blade bending): " + A + ".",
        },
        "control": {
            "time_limit_s": 15.0, "detection_delay_s": 0.3,
            "source": "Motor run-time limit of the interlocking and normal delay from motor off to detection: " + A + ".",
        },
        "heating": {
            "switch_on_c": 3.0, "rated_current_a": 13.0,
            "source": "Point heating switch-on temperature and rated current (about 3 kW at 230 V per turnout): " + A + ".",
        },
        "demo": {"time_scale": 1, "throw_every_s": 20,
                 "note": "Demo only: the interlocking throws the points every 20 s of real time, alternating normal and reverse, so a new throw is recorded often."},
    },
    "telemetry": {
        "event": "points", "publish_every_s": 10, "device_type": "POINT_MACHINE_CM",
        "groups": {"Throw": "Last throw: times and direction", "Power": "Last throw: power curve by phase", "Motor": "Motor supply",
                   "Detection": "Detection and trailing from the interlocking", "Weather": "Rail and air temperature",
                   "Heater": "Point heating", "Service": "Throw counters"},
        "points": [
            {"metric": "throw_direction", "path": "Throw.Direction", "label": "Direction of the last throw (1 to reverse, 0 to normal)", "unit": "code"},
            {"metric": "throw_time_s", "path": "Throw.Time", "label": "Throw time, motor on to motor off", "unit": "s"},
            {"metric": "unlock_time_s", "path": "Throw.UnlockTime", "label": "Unlock phase duration", "unit": "s"},
            {"metric": "drive_time_s", "path": "Throw.DriveTime", "label": "Drive phase duration", "unit": "s"},
            {"metric": "lock_time_s", "path": "Throw.LockTime", "label": "Lock phase duration", "unit": "s"},
            {"metric": "unlock_peak_w", "path": "Power.UnlockPeak", "label": "Peak power at the start (unlock)", "unit": "W"},
            {"metric": "drive_power_mean_w", "path": "Power.DriveMean", "label": "Mean power in the drive phase", "unit": "W"},
            {"metric": "drive_power_peak_w", "path": "Power.DrivePeak", "label": "Highest power in the drive phase", "unit": "W"},
            {"metric": "lock_power_mean_w", "path": "Power.LockMean", "label": "Mean power in the lock phase", "unit": "W"},
            {"metric": "energy_kj", "path": "Power.Energy", "label": "Electrical energy of the whole throw", "unit": "kJ"},
            {"metric": "motor_voltage_v", "path": "Motor.Voltage", "label": "Motor voltage (line to line) during the drive phase", "unit": "V"},
            {"metric": "drive_current_a", "path": "Motor.DriveCurrent", "label": "Motor current in the drive phase", "unit": "A"},
            {"metric": "start_current_a", "path": "Motor.StartCurrent", "label": "Starting current", "unit": "A"},
            {"metric": "detection_ok", "path": "Detection.Ok", "label": "End position detected after the last throw (1 = yes)", "unit": "code"},
            {"metric": "detection_delay_s", "path": "Detection.Delay", "label": "Motor off to detection", "unit": "s"},
            {"metric": "detection_losses_24h", "path": "Detection.Losses24h", "label": "Losses of detection while lying, last 24 h", "unit": "count"},
            {"metric": "trailed", "path": "Detection.Trailed", "label": "Points trailed (trailing clutch released)", "unit": "code"},
            {"metric": "air_temp_c", "path": "Weather.Air", "label": "Air temperature", "unit": "°C"},
            {"metric": "rail_temp_c", "path": "Weather.Rail", "label": "Rail temperature at the switch", "unit": "°C"},
            {"metric": "heater_on", "path": "Heater.On", "label": "Point heating switched on (1 = on)", "unit": "code"},
            {"metric": "heater_current_a", "path": "Heater.Current", "label": "Point heating current", "unit": "A"},
            {"metric": "throws_total", "path": "Service.Throws", "label": "Throws since installation", "unit": "count"},
            {"metric": "throws_since_overhaul", "path": "Service.ThrowsSinceOverhaul", "label": "Throws since the last general overhaul", "unit": "count"},
        ],
    },
    "twin_model": {
        "limits": {
            "force_ratio_warn": 1.25, "force_ratio_alert": 1.6, "lock_force_ratio_alert": 1.6, "clutch_fraction": 0.9,
            "energy_ratio_alert": 1.2, "throw_time_ratio_alert": 1.25, "unlock_peak_alert_w": 2500.0,
            "voltage_ratio_alert": 0.9, "detection_losses_alert": 2, "heater_fraction_alert": 0.5, "overhaul_fraction": 0.9,
            "source": "Alarm limits of the twin: assumption, typical practice for current-curve monitoring; tune them on your own fleet.",
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "lubrication_loss": {"name": "Slide chairs dry (lubrication loss)", "part": "turnout",
                             "symptoms": "drive-phase power and force rise week by week, energy per throw up, throw slightly slower",
                             "rules": ["PTS_FORCE_RISING", "PTS_FORCE_HIGH", "PTS_ENERGY_HIGH"], "default_ramp_min": 1.5},
        "obstruction": {"name": "Obstruction in the switch (ballast stone, object)", "part": "turnout",
                        "symptoms": "blade stops short, lock cannot engage, clutch slips until the time limit, no detection",
                        "rules": ["PTS_DETECTION_LOST", "PTS_CLUTCH_LIMIT", "PTS_THROW_SLOW", "PTS_ENERGY_HIGH"], "default_ramp_min": 0.5},
        "ice_heater": {"name": "Point heating failed in frost (ice at the toe)", "part": "heating",
                       "symptoms": "heater on but no current, lock-phase force rises as ice builds between blade and stock rail",
                       "rules": ["PTS_HEATER_FAIL", "PTS_LOCK_FORCE_HIGH"], "default_ramp_min": 1},
        "unlock_tight": {"name": "Blade too tight against the stock rail (adjustment, creep)", "part": "turnout",
                         "symptoms": "very high power peak at the start of the throw, the rest of the curve normal",
                         "rules": ["PTS_UNLOCK_PEAK_HIGH"], "default_ramp_min": 1},
        "detector_adjust": {"name": "Detector rods out of adjustment", "part": "detection",
                            "symptoms": "detection drops out while the points lie (train vibration), detection late after a throw",
                            "rules": ["PTS_DETECTION_FLICKER"], "default_ramp_min": 1},
        "supply_low": {"name": "Low motor voltage (supply or cable)", "part": "supply",
                       "symptoms": "voltage at the machine low, more current for the same power", "rules": ["PTS_SUPPLY_LOW"], "default_ramp_min": 1},
        "trailed": {"name": "Points trailed by a train", "part": "detection",
                    "symptoms": "trailing clutch released, detection lost: the points must be examined before use",
                    "rules": ["PTS_TRAILED", "PTS_DETECTION_LOST"], "default_ramp_min": 0.5},
    },
    "presentation": {"title": "PM-5501 point machine", "dashboard": "POINT_MACHINE_CM"},
}

out = HERE / "twin" / "pm-5501.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
