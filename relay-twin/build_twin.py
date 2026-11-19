"""Write twin/pr-7201.twin.json: the feeder protection relay twin (PR-7201).

    python build_twin.py

PR-7201 is an ABB Relion REF615 feeder protection and control relay on an 11 kV outgoing feeder of a distribution
substation. It trips the feeder's vacuum circuit breaker, talks to the station bus over IEC 61850 (MMS reports, GOOSE),
is time-synchronised by PTP (IEEE 1588 v2, power profile) and is supplied from the 110 V DC station battery.

Sources and assumptions (every number below is either from a checked source or labelled as an assumption in "source"):
  ABB REF615 Product Guide 1MRS756379 U (product version 5.0 FP1, 2021): PHLPTOC start value 0.05...5.00 x In,
    time multiplier 0.05...15.00, curve types (9 = IEC Norm. inv., 10 = IEC Very inv., 12 = IEC Ext. inv., ...),
    operate time accuracy in inverse time mode +/-5.0 % of the theoretical value or +/-20 ms, CCBRBRF delays
    0...60000 ms, CCSPVC start value 0.05...0.20 x In, TCS current drain ~1.5 mA, auxiliary supply type 1 DC
    variation 80...120 % of Un, PTP (IEEE 1588) v2 with power profile (grandmaster accuracy +/-1 us), SNTP, IRIG-B,
    GOOSE "<10 ms data exchange between the devices".
  IEC 60255-151: inverse-time characteristic t = TMS x (k / ((I/Is)^alpha - 1) + c); IEC curves have c = 0:
    normal (standard) inverse k 0.14 alpha 0.02, very inverse 13.5 / 1, extremely inverse 80 / 2.
  IEEE C37.112 curves t = TD x (A / (M^p - 1) + B), constants as printed in relay manuals: MI 0.0515 / 0.114 / 0.02,
    VI 19.61 / 0.491 / 2, EI 28.2 / 0.1217 / 2 (reference only; this relay is set on an IEC curve).
  IEC 62271-1 (2007 ed., 5.8.2): a shunt opening release (trip coil) shall operate between 70 % (d.c.) and 110 % of its
    rated supply voltage.
  Feeder data, breaker timing, wear allowance, GOOSE subscriptions, settings checksum: ASSUMPTIONS, labelled below.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with your protection settings sheet / breaker data sheet"
PG = "ABB REF615 Product Guide 1MRS756379 U (5.0 FP1)"

twin = {
    "$comment": "PR-7201 feeder protection relay twin. Expected values in Maximo Monitor from the settings sheet, IEC 60255-151 and the relay and breaker data; the relay sends only what it measures and records.",
    "twin": {"id": "PR-7201", "name": "Feeder protection relay PR-7201", "version": "1.0.0", "folder": "relay-twin"},
    "identification": {
        "asset": "PR-7201", "assetnum": "PR-7201", "manufacturer": "ABB",
        "model": "Relion REF615 feeder protection and control (product version 5.0 FP1)",
        "description": "Protection relay of 11 kV outgoing feeder F07 in a distribution substation (IEC 61850 station bus)",
        "protected_object": "11 kV cable feeder, vacuum circuit breaker Q0, CTs 400/1 A",
        "breaker": "11 kV vacuum circuit breaker with spring mechanism and shunt trip coil, 110 V DC (generic)",
        "station_bus": "IEC 61850-8-1 MMS and GOOSE over PRP, PTP (IEEE 1588 v2, power profile) from the station grandmaster",
    },
    "design": {
        "feeder": {
            "voltage_kv": 11.0, "ct_primary_a": 400.0, "ct_secondary_a": 1.0, "load_nominal_a": 210.0,
            "source": "Feeder rating and CT ratio: " + A,
        },
        "overcurrent": {
            "function": "PHLPTOC (IEC 61850 logical node PTOC), stage 1 low",
            "start_value_in": 0.90, "tms": 0.15, "curve": "IEC normal inverse (curve type 9)", "k": 0.14, "alpha": 0.02, "c": 0.0,
            "accuracy_pct": 5.0, "accuracy_ms": 20.0,
            "curves": {
                "IEC normal inverse": {"k": 0.14, "alpha": 0.02, "c": 0.0},
                "IEC very inverse": {"k": 13.5, "alpha": 1.0, "c": 0.0},
                "IEC extremely inverse": {"k": 80.0, "alpha": 2.0, "c": 0.0},
                "IEEE moderately inverse": {"k": 0.0515, "alpha": 0.02, "c": 0.114},
                "IEEE very inverse": {"k": 19.61, "alpha": 2.0, "c": 0.491},
                "IEEE extremely inverse": {"k": 28.2, "alpha": 2.0, "c": 0.1217},
            },
            "source": "Curve formula and IEC constants: IEC 60255-151. IEEE constants as printed in relay manuals (IEEE C37.112 form). "
                      "Setting ranges and accuracy (+/-5.0 % of the theoretical value or +/-20 ms in inverse time mode): " + PG
                      + ". Start value 0.90 x In and TMS 0.15 on IEC normal inverse: " + A,
        },
        "breaker": {
            "open_baseline_ms": 45.0, "bf_delay_ms": 150.0, "bf_margin_alert_ms": 40.0,
            "isc_rated_ka": 25.0, "arc_time_s": 0.010, "breaks_at_rated": 50, "wear_exponent": 2.0,
            "source": "Opening time from trip command to open position, breaker failure delay (CCBRBRF 'CB failure delay', range 0...60000 ms "
                      "in the " + PG + "), rated short-circuit breaking current, arcing time per break and the number of breaks at rated current "
                      "the interrupters allow: " + A + ". Wear sum I^y x t with y = 2, as the relay's SSCBR accumulated energy does.",
        },
        "supervision": {
            "ccs_start_in": 0.10, "goose_subscriptions": 4, "goose_heartbeat_s": 1.0, "goose_window_s": 600.0,
            "goose_miss_alert_pct": 1.0, "goose_latency_alert_ms": 10.0, "sync_offset_alert_us": 1000.0,
            "settings_checksum_approved": 1514967522, "setting_group_approved": 1,
            "trip_path_proof_days": 2190,
            "source": "CCSPVC start value range 0.05...0.20 x In, GOOSE data exchange < 10 ms, 1 ms event time stamp resolution "
                      "(offset limit 1000 us): " + PG + ". 4 subscribed GOOSE data sets with a 1 s heartbeat, 1 % miss limit, and the "
                      "approved settings checksum (the settings-management tool's fingerprint of the approved setting file, kept on the "
                      "Maximo asset): " + A + ". 2190 days = 6 years, the NERC PRC-005-6 Table 1-5 maximum interval for verifying a trip coil.",
        },
        "dc": {
            "nominal_v": 110.0, "float_v": 121.0, "relay_min_pct": 80.0, "trip_coil_min_pct": 70.0,
            "source": "Relay type 1 supply: DC variation 80...120 % of Un (" + PG + "). Trip coil: IEC 62271-1 shunt opening release "
                      "70...110 % of rated supply voltage (d.c.). Float voltage 121 V of a 110 V station battery: " + A,
        },
        "demo": {"time_scale": 1, "fault_every_s": 45,
                 "note": "Demo only: a short circuit on the feeder every 45 s of real time, cleared by the relay and the breaker, so the "
                         "fault record (current, operate time, breaker opening time) updates often. A real feeder sees a few faults a year."},
    },
    "telemetry": {
        "event": "relay", "publish_every_s": 10, "device_type": "PROTECTION_RELAY_IED",
        "groups": {"Meas": "Load and residual currents", "Fault": "Last fault record (COMTRADE / fault recorder)",
                   "Breaker": "Breaker monitoring by the relay", "Settings": "Settings fingerprint", "Supervision": "Self-supervision",
                   "Sync": "Time synchronisation", "Goose": "GOOSE subscriptions", "Supply": "Auxiliary supply", "Test": "Proof of the trip path"},
        "points": [
            {"metric": "load_current_a", "path": "Meas.LoadCurrent", "label": "Highest phase load current (primary)", "unit": "A"},
            {"metric": "io_calc_a", "path": "Meas.IoCalculated", "label": "Residual current calculated from the three phase CTs", "unit": "A"},
            {"metric": "io_meas_a", "path": "Meas.IoMeasured", "label": "Residual current measured by the core-balance CT", "unit": "A"},
            {"metric": "fault_current_a", "path": "Fault.Current", "label": "Highest phase current in the last fault record (primary)", "unit": "A"},
            {"metric": "fault_operate_ms", "path": "Fault.OperateTime", "label": "Relay operate time, fault inception to trip output, last fault", "unit": "ms"},
            {"metric": "fault_count", "path": "Fault.Count", "label": "Faults cleared since commissioning", "unit": "count"},
            {"metric": "cb_open_ms", "path": "Breaker.OpenTime", "label": "Breaker opening time, trip output to open position, last trip", "unit": "ms"},
            {"metric": "cb_wear_ka2s", "path": "Breaker.AccumulatedI2t", "label": "Accumulated I²t of the worst pole (SSCBR, y = 2)", "unit": "kA²s"},
            {"metric": "tcs_alarm", "path": "Breaker.TCS", "label": "Trip circuit supervision alarm (1 = alarm)", "unit": "code"},
            {"metric": "settings_crc", "path": "Settings.Checksum", "label": "Checksum of the active setting file", "unit": "code"},
            {"metric": "active_group", "path": "Settings.ActiveGroup", "label": "Active setting group", "unit": "code"},
            {"metric": "irf_alarm", "path": "Supervision.IRF", "label": "Internal relay fault (1 = protection blocked)", "unit": "code"},
            {"metric": "sync_ok", "path": "Sync.Locked", "label": "Synchronised to the PTP grandmaster (1 = yes)", "unit": "code"},
            {"metric": "sync_offset_us", "path": "Sync.Offset", "label": "Clock offset from the grandmaster", "unit": "µs"},
            {"metric": "goose_missed", "path": "Goose.Missed", "label": "GOOSE messages missed or late, last 10 min", "unit": "count"},
            {"metric": "goose_max_latency_ms", "path": "Goose.MaxLatency", "label": "Highest GOOSE transfer time, last 10 min", "unit": "ms"},
            {"metric": "aux_dc_v", "path": "Supply.AuxDC", "label": "Auxiliary DC voltage at the relay", "unit": "V"},
            {"metric": "trip_verified_days", "path": "Test.TripPathVerified", "label": "Days since the trip path was last proven (fault trip or test)", "unit": "d"},
        ],
    },
    "twin_model": {
        "limits": {
            "operate_error_ratio_alert": 1.0, "cb_open_ratio_alert": 1.3, "wear_alert_pct": 80.0, "wear_limit_pct": 100.0,
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "settings_change": {"name": "Unauthorised or unrecorded settings change", "part": "settings",
                            "symptoms": "settings checksum no longer matches the Maximo record; the next fault trips on a different curve",
                            "rules": ["PROT_SETTINGS_MISMATCH", "PROT_TIMING_DEVIATION"], "default_ramp_min": 0.5},
        "trip_circuit_open": {"name": "Trip circuit open (coil, wiring or auxiliary contact)", "part": "trip circuit",
                              "symptoms": "trip circuit supervision current lost: the relay can no longer trip the breaker",
                              "rules": ["PROT_TCS_ALARM"], "default_ramp_min": 0.5},
        "breaker_slow": {"name": "Breaker mechanism slow (lubrication, latch, spring)", "part": "breaker",
                         "symptoms": "opening time after each trip grows; margin to the breaker failure timer shrinks",
                         "rules": ["PROT_CB_SLOW", "PROT_BF_MARGIN_LOW"], "default_ramp_min": 1.5},
        "contact_wear": {"name": "Interrupter contact wear", "part": "breaker",
                         "symptoms": "accumulated I²t climbs towards the interrupter allowance",
                         "rules": ["PROT_CB_WEAR", "PROT_CB_WEAR_LIMIT"], "default_ramp_min": 1.5},
        "time_sync_loss": {"name": "Loss of time synchronisation (PTP grandmaster or network)", "part": "time sync",
                           "symptoms": "relay no longer locked; clock offset drifts; event and fault records lose their common time",
                           "rules": ["PROT_TIME_SYNC"], "default_ramp_min": 1},
        "dc_supply_low": {"name": "Station DC supply low (charger or battery)", "part": "dc supply",
                          "symptoms": "auxiliary DC falls below the relay's supply range, then below the trip coil's minimum",
                          "rules": ["PROT_DC_LOW", "PROT_DC_TRIP_RISK"], "default_ramp_min": 1},
        "goose_degraded": {"name": "GOOSE messages lost or late (station bus)", "part": "station bus",
                           "symptoms": "missed and late GOOSE messages: blocking and breaker failure signals may not arrive in time",
                           "rules": ["PROT_GOOSE_DEGRADED"], "default_ramp_min": 1},
        "ct_circuit_fault": {"name": "CT secondary circuit open or shorted", "part": "CT circuit",
                             "symptoms": "residual current from the phases disagrees with the core-balance CT",
                             "rules": ["PROT_CT_SUPERVISION"], "default_ramp_min": 0.5},
    },
    "presentation": {"title": "PR-7201 feeder protection relay", "dashboard": "PROTECTION_RELAY_IED",
                     "kpis": [{"metric": "fault_operate_ms"}, {"metric": "cb_open_ms"}]},
}

out = HERE / "twin" / "pr-7201.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
