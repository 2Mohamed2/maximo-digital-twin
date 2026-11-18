"""Write twin/psv-2601.twin.json: the spring-loaded pressure relief valve twin (PSV-2601).

    python build_twin.py

PSV-2601 protects a light-hydrocarbon vapour drum on a refinery unit. It is a conventional (unbalanced) direct spring-loaded
pressure relief valve with an API 526 "J" orifice, size 3J4 (3 in inlet, 4 in outlet), metal seat, discharging to the
flare header. A wireless acoustic transmitter clamped on the outlet pipe listens for lifts and for leakage through the seat.

Sources and assumptions (every number below is either from a published source or labelled as an assumption in "source"):
  Valve: Emerson Crosby J-Series data sheet (VCTDS-00597-EN): JOS-E conventional, built to API 526 and API 527; J orifice
    1.287 sq.in (830 sq.mm) API effective area; 3J4 with Class 300 inlet / Class 150 outlet: maximum set pressure
    740 psig (51.0 barg) at -20 to +100 F, back pressure limit 285 psig (19.6 barg) at 100 F; the same data sheet lists the
    Rosemount 708 wireless acoustic transmitter as a monitoring option.
  API 526: effective orifice areas D to T (0.110 to 26.0 sq.in).
  API 520 Part I (gas/vapour, critical flow, SI units):  A = W / (C Kd P1 Kb Kc) x sqrt(T Z / M),
    C = 0.03948 sqrt(k (2/(k+1))^((k+1)/(k-1))), Kd = 0.975 with API effective areas, P1 = set + overpressure + atmospheric.
  API 520 Part II: non-recoverable inlet loss to a conventional PRV within 3 % of set.
  API 520 Part I: built-up back pressure on a conventional PRV within 10 % of set at 10 % overpressure.
  ASME Section VIII / Section XIII: single valve, accumulation 10 % of MAWP; set pressure tolerance +-3 % above 70 psig.
  API 527: metal-seated valve, air at 90 % of set, 15 to 1000 psig set, orifices larger than F: 20 bubbles per minute.
  API 510 / API 576: test interval at most 5 years in typical process service (10 years in clean, non-fouling service).
  Process data (MAWP, vapour properties, relief load, line losses, acoustic background) and the fleet bench-test history:
    ASSUMPTIONS of a typical drum, to be replaced by the relief study (API 521) and the test records of your own valve.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with your relief study / data sheet"

twin = {
    "$comment": "PSV-2601 spring-loaded pressure relief valve twin. Expected values in Maximo Monitor from the relief study, API 520/526 and the bench-test records; the gateway sends only what is measured or recorded.",
    "twin": {"id": "PSV-2601", "name": "Pressure relief valve PSV-2601", "version": "1.0.0", "folder": "psv-twin"},
    "identification": {
        "asset": "PSV-2601", "assetnum": "PSV-2601", "manufacturer": "Emerson (Crosby)",
        "model": "Crosby J-Series JOS-E, size 3J4 (J orifice), conventional, metal seat",
        "description": "Pressure relief valve on the overhead vapour drum D-2601, discharging to the flare header",
        "valve": "Direct spring-loaded, full nozzle, conventional (no bellows); API 526 J orifice, 1.287 sq.in effective area; inlet ASME Class 300, outlet Class 150",
        "acoustic": "Rosemount 708 wireless acoustic transmitter on the outlet pipe (acoustic level 0-255 counts and pipe temperature, WirelessHART)",
        "protected": "Vapour drum D-2601, MAWP 15.0 barg (assumption)",
    },
    "design": {
        "vessel": {"mawp_barg": 15.0, "set_barg": 15.0, "overpressure_pct": 10.0, "accumulation_limit_pct": 10.0,
                   "operating_barg": 12.0, "temp_c": 60.0,
                   "source": "Set pressure = MAWP; single valve, non-fire case: overpressure and accumulation 10 % of MAWP "
                             "(ASME Section VIII / XIII). MAWP, operating pressure and temperature: " + A},
        "valve": {"orifice": "J", "area_eff_mm2": 830.0, "area_eff_in2": 1.287, "kd": 0.975, "kb": 1.0, "kc": 1.0,
                  "size": "3J4", "max_set_barg": 51.0, "max_backpressure_barg": 19.6,
                  "source": "API 526 J orifice effective area 1.287 sq.in (830 sq.mm); Kd 0.975 with API effective areas (API 520 Part I); "
                            "Kb = 1 for a conventional valve in critical flow, Kc = 1 (no rupture disc). Maximum set 740 psig (51.0 barg) "
                            "and back pressure limit 285 psig (19.6 barg) for 3J4 Class 300 x 150: Crosby J-Series data sheet."},
        "fluid": {"name": "light hydrocarbon vapour (propane-rich)", "mw": 44.1, "k": 1.13, "z": 0.85,
                  "source": "Relieving vapour: molar mass, Cp/Cv and compressibility at relieving conditions: " + A},
        "relief": {"governing_case": "blocked vapour outlet (API 521)", "load_factor": 1.0, "design_feed_kgh": 11200.0,
                   "source": "Governing case blocked outlet: the relief load equals the vapour flow into the drum (load_factor x feed). "
                             "Design vapour feed: " + A},
        "lines": {"inlet_loss_design_pct": 1.6, "inlet_loss_limit_pct": 3.0, "builtup_bp_design_pct": 5.0, "builtup_bp_limit_pct": 10.0,
                  "source": "Inlet loss at rated flow (non-recoverable, API 520 Part II limit 3 % of set) and built-up back pressure "
                            "(conventional valve, API 520 Part I limit 10 % of set at 10 % overpressure). Design values of the line "
                            "calculations: " + A},
        "acoustic": {"background_counts": 22.0, "lift_counts": 150.0,
                     "source": "Rosemount 708 acoustic level 0-255 counts. Background with the valve shut and the lift level: " + A
                               + " (set during commissioning)."},
        "bench": {"set_tolerance_pct": 3.0, "seat_leak_limit_bpm": 20.0, "seat_test_pct_of_set": 90.0,
                  "source": "Set pressure tolerance +-3 % above 70 psig (ASME). API 527 metal seat, air, set 15-1000 psig, orifice "
                            "larger than F: 20 bubbles per minute at 90 % of set."},
        "rbi": {"planned_interval_y": 4.0, "code_max_interval_y": 5.0, "pofod_target": 0.02,
                "fleet_failures": 3, "fleet_valve_years": 900.0, "confidence": 0.90, "drift_allow_pct": 3.0,
                "source": "Planned test interval = 4-year turnaround cycle (assumption). API 510 / API 576: at most 5 years in typical "
                          "process service. Target POFOD 0.02 (98 % reliability on demand, a typical target for safety-critical PRVs). "
                          "Fleet history: 3 fail-to-open findings at the as-found bench test in 900 valve-years of similar PSVs: " + A
                          + ". A fail-to-open here means as-found pop above set + 10 % or no pop at all (site definition)."},
        "demo": {"time_scale": 60, "lift_every_s": 75, "lift_s": 8,
                 "note": "Demo only: the plant clock runs 60 times faster and a short process upset lifts the valve every 75 s of real "
                         "time so the lift tags update often; lift and test counters come from the failure modes, not from the demo clock."},
    },
    "telemetry": {
        "event": "psv", "publish_every_s": 60, "device_type": "PSV_SPRING_API526",
        "groups": {"Process": "Protected drum", "Acoustic": "Acoustic transmitter on the outlet", "Ambient": "Weather",
                   "Header": "Flare header", "Lift": "Last lift (from the acoustic event log)", "Test": "Last bench test (API 576 shop record)"},
        "points": [
            {"metric": "vessel_pressure_barg", "path": "Process.Pressure", "label": "Drum pressure", "unit": "bar g"},
            {"metric": "vessel_temp_c", "path": "Process.Temperature", "label": "Drum vapour temperature", "unit": "°C"},
            {"metric": "vapour_feed_kgh", "path": "Process.VapourFeed", "label": "Vapour flow into the drum", "unit": "kg/h"},
            {"metric": "acoustic_level", "path": "Acoustic.Level", "label": "Acoustic level on the outlet pipe", "unit": "counts"},
            {"metric": "outlet_temp_c", "path": "Acoustic.Temperature", "label": "Outlet pipe temperature", "unit": "°C"},
            {"metric": "ambient_temp_c", "path": "Ambient.Temperature", "label": "Ambient temperature", "unit": "°C"},
            {"metric": "header_pressure_barg", "path": "Header.Pressure", "label": "Flare header pressure (superimposed back pressure)", "unit": "bar g"},
            {"metric": "lift_active", "path": "Lift.Active", "label": "Valve lifting now (1 = yes)", "unit": "code"},
            {"metric": "lift_open_barg", "path": "Lift.OpenPressure", "label": "Drum pressure when the last lift started", "unit": "bar g"},
            {"metric": "lift_peak_barg", "path": "Lift.PeakPressure", "label": "Peak drum pressure during the last lift", "unit": "bar g"},
            {"metric": "lift_vessel_barg", "path": "Lift.VesselPressure", "label": "Drum pressure at full lift", "unit": "bar g"},
            {"metric": "lift_inlet_barg", "path": "Lift.InletPressure", "label": "Pressure at the valve inlet at full lift", "unit": "bar g"},
            {"metric": "lift_outlet_barg", "path": "Lift.OutletPressure", "label": "Outlet pressure at full lift (built-up back pressure)", "unit": "bar g"},
            {"metric": "lift_duration_s", "path": "Lift.Duration", "label": "Duration of the last lift", "unit": "s"},
            {"metric": "lift_count_30d", "path": "Lift.Count30", "label": "Lifts in the last 30 days", "unit": "count"},
            {"metric": "lift_count_365d", "path": "Lift.Count365", "label": "Lifts in the last 365 days", "unit": "count"},
            {"metric": "test_asfound_barg", "path": "Test.AsFoundPop", "label": "As-found pop pressure at the last bench test", "unit": "bar g"},
            {"metric": "test_prev_asleft_barg", "path": "Test.PrevAsLeftPop", "label": "As-left pop pressure at the test before", "unit": "bar g"},
            {"metric": "test_interval_h", "path": "Test.Interval", "label": "Time in service between the two tests", "unit": "h"},
            {"metric": "test_seat_bpm", "path": "Test.SeatLeak", "label": "As-found seat leakage at 90 % of set (API 527)", "unit": "bubbles/min"},
            {"metric": "test_hours_since", "path": "Test.HoursSince", "label": "Hours in service since the last bench test", "unit": "h"},
        ],
    },
    "twin_model": {
        "limits": {
            "simmer_pct": 90.0, "near_set_pct": 95.0, "util_alert_pct": 90.0, "util_limit_pct": 100.0,
            "acoustic_excess_alert": 15.0, "outlet_dt_alert_k": 5.0, "chatter_lifts_30d": 6, "chatter_duration_s": 10.0,
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "seat_passing": {"name": "Seat leakage (passing) in service", "part": "seat",
                         "symptoms": "acoustic level above background and outlet pipe temperature off ambient while the drum is well below set",
                         "rules": ["PSV_PASSING"], "default_ramp_min": 1},
        "operating_near_set": {"name": "Operating pressure too close to set", "part": "process",
                               "symptoms": "drum pressure above 90 % then 95 % of set: simmer, seat damage, product to flare",
                               "rules": ["PSV_SIMMER_ZONE", "PSV_NEAR_SET"], "default_ramp_min": 1.5},
        "set_pressure_drift": {"name": "Set pressure drift and seat wear (found at the bench test)", "part": "spring",
                               "symptoms": "as-found pop outside tolerance, seat leak above API 527, drift rate shortens the safe interval",
                               "rules": ["PSV_POP_DRIFT", "PSV_SEAT_TIGHTNESS", "PSV_RBI_INTERVAL_SHORT"], "default_ramp_min": 0.5},
        "valve_sticking": {"name": "Valve sticking: opens late (fouling, corrosion, polymer)", "part": "disc",
                           "symptoms": "the last lift started above set + tolerance and the drum peak passed MAWP + 10 %",
                           "rules": ["PSV_LATE_OPENING", "PSV_ACCUMULATION"], "default_ramp_min": 1},
        "inlet_restriction": {"name": "Inlet line restriction (fouling, wrong block valve, long inlet)", "part": "inlet",
                              "symptoms": "inlet loss above 3 % of set, short repeated lifts (chatter)",
                              "rules": ["PSV_INLET_LOSS", "PSV_CHATTER"], "default_ramp_min": 1},
        "high_backpressure": {"name": "High built-up back pressure (outlet or flare header)", "part": "outlet",
                              "symptoms": "outlet pressure during the lift above 10 % of set on a conventional valve",
                              "rules": ["PSV_BACKPRESSURE_HIGH"], "default_ramp_min": 1},
        "relief_load_increase": {"name": "Relief load above rated capacity (debottlenecked feed)", "part": "process",
                                 "symptoms": "vapour feed up: required relieving rate approaches, then exceeds, what the J orifice can pass",
                                 "rules": ["PSV_CAPACITY_MARGIN", "PSV_CAPACITY_SHORT"], "default_ramp_min": 1.5},
        "test_overdue": {"name": "Bench test overdue", "part": "testing", "symptoms": "hours since the last bench test above the planned interval",
                         "rules": ["PSV_TEST_OVERDUE"], "default_ramp_min": 0.5},
    },
    "presentation": {"title": "PSV-2601 pressure relief valve", "dashboard": "PSV_SPRING_API526"},
}

out = HERE / "twin" / "psv-2601.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
