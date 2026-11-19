"""Write twin/gis-7401.twin.json: the gas-insulated switchgear bay twin (GIS-7401).

    python build_twin.py

GIS-7401 is one 132 kV cable feeder bay of an indoor gas-insulated substation, built from Hitachi Energy ELK-04 C 145 kV
switchgear: busbar disconnector and earthing switch, SF6 circuit breaker with current transformers, line disconnector with
earthing switches and cable sealing end, and voltage transformer, in four SF6 gas compartments.

Sources and assumptions (every number below is either from these sources or labelled as an assumption in "source"):
  Hitachi Energy ELK-04 C up to 145 kV product page: 145 kV, 50/60 Hz, 275 kV (1 min), 650 kV (1.2/50 us), 3150 A busbar and
    feeder, 40 kA breaking and short-time (3 s), 108 kA peak, bay width 800 mm, ambient -30 ... +55 C, indoor / outdoor.
  IEC 62271-203:2022 (ed. 3) summary of changes: type-test tightness for gases with GWP > 1000 reduced from 0.5 % to 0.1 % per
    year per gas compartment.
  Regulation (EU) 2024/573, Annex I: GWP100 of SF6 = 24 300; Art. 6: leakage detection on switchgear >= 500 t CO2e installed
    from 1 January 2017.
  NIST Chemistry WebBook (fluid properties of sulfur hexafluoride): the 55 density points below, used to fit the SF6 equation
    of state the twin uses (pressure + temperature -> density -> pressure at 20 C).
  Gas compartment layout, volumes, filling / alarm / minimum functional densities, breaker and switch timings, coil, motor,
  wear allowance, moisture, decomposition and partial discharge limits: ASSUMPTIONS of a typical bay at this rating, to be
  replaced by the gas schematic, the type-test and routine-test reports and the operating manual of your own switchgear.
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
A = "assumption: typical value, replace with your switchgear's gas schematic, routine test report and manual"

# NIST Chemistry WebBook, SF6 isotherms (T K, p MPa abs, density kg/m3), 263.15 ... 333.15 K, 0.30 ... 0.80 MPa
NIST = [
    (263.15, 0.30, 21.129), (263.15, 0.35, 24.894), (263.15, 0.40, 28.739), (263.15, 0.45, 32.670), (263.15, 0.50, 36.692),
    (263.15, 0.55, 40.812), (263.15, 0.60, 45.037), (263.15, 0.65, 49.376), (263.15, 0.70, 53.837), (263.15, 0.75, 58.431),
    (263.15, 0.80, 63.171), (273.15, 0.30, 20.222), (273.15, 0.35, 23.794), (273.15, 0.40, 27.430), (273.15, 0.45, 31.135),
    (273.15, 0.50, 34.912), (273.15, 0.55, 38.766), (273.15, 0.60, 42.701), (273.15, 0.65, 46.722), (273.15, 0.70, 50.834),
    (273.15, 0.75, 55.044), (273.15, 0.80, 59.359), (293.15, 0.30, 18.651), (293.15, 0.35, 21.902), (293.15, 0.40, 25.197),
    (293.15, 0.45, 28.538), (293.15, 0.50, 31.927), (293.15, 0.55, 35.366), (293.15, 0.60, 38.857), (293.15, 0.65, 42.401),
    (293.15, 0.70, 46.002), (293.15, 0.75, 49.662), (293.15, 0.80, 53.384), (313.15, 0.30, 17.330), (313.15, 0.35, 20.322),
    (313.15, 0.40, 23.346), (313.15, 0.45, 26.402), (313.15, 0.50, 29.491), (313.15, 0.55, 32.615), (313.15, 0.60, 35.775),
    (313.15, 0.65, 38.971), (313.15, 0.70, 42.204), (313.15, 0.75, 45.477), (313.15, 0.80, 48.789), (333.15, 0.30, 16.198),
    (333.15, 0.35, 18.975), (333.15, 0.40, 21.775), (333.15, 0.45, 24.599), (333.15, 0.50, 27.447), (333.15, 0.55, 30.320),
    (333.15, 0.60, 33.218), (333.15, 0.65, 36.142), (333.15, 0.70, 39.093), (333.15, 0.75, 42.070), (333.15, 0.80, 45.076),
]
R_SF6 = 8.314462618 / 0.146055          # J/(kg K), molar mass of SF6 146.055 g/mol


def fit_eos():
    """Z(p, T) = 1 + p (a0 + a1/T + a2/T^2) + a3 p^2 / T   (p in MPa)  -> density from a reading;
       p20 = rho R 293.15 (1 + q1 rho + q2 rho^2)               -> pressure at 20 C from a density (20 C isotherm)."""
    d = np.array(NIST)
    T, p, rho = d[:, 0], d[:, 1], d[:, 2]
    Z = p * 1e6 / (rho * R_SF6 * T)
    a, *_ = np.linalg.lstsq(np.c_[p, p / T, p / T ** 2, p * p / T], Z - 1, rcond=None)
    m = T == 293.15
    q, *_ = np.linalg.lstsq(np.c_[rho[m], rho[m] ** 2], Z[m] - 1, rcond=None)
    rho_fit = p * 1e6 / ((1 + a[0] * p + a[1] * p / T + a[2] * p / T ** 2 + a[3] * p * p / T) * R_SF6 * T)
    p20_fit = rho[m] * R_SF6 * 293.15 * (1 + q[0] * rho[m] + q[1] * rho[m] ** 2) / 1e6
    return ([float(f"{x:.8g}") for x in a], [float(f"{x:.8g}") for x in q],
            float(np.max(np.abs(rho_fit / rho - 1))) * 100, float(np.max(np.abs(p20_fit / p[m] - 1))) * 100)


a, q, err_rho, err_p20 = fit_eos()

COMP = {
    "cb": {"name": "Circuit breaker + current transformers", "volume_m3": 0.55, "fill_mpa": 0.70, "alarm_mpa": 0.64, "minimum_mpa": 0.62,
           "heat_k": 9.0},
    "bb": {"name": "Busbar disconnector + earthing switch (bay part of the busbar)", "volume_m3": 0.80, "fill_mpa": 0.60, "alarm_mpa": 0.55,
           "minimum_mpa": 0.52, "heat_k": 5.0},
    "ld": {"name": "Line disconnector + earthing switches + cable sealing end", "volume_m3": 0.45, "fill_mpa": 0.60, "alarm_mpa": 0.55,
           "minimum_mpa": 0.52, "heat_k": 4.0},
    "vt": {"name": "Voltage transformer", "volume_m3": 0.35, "fill_mpa": 0.60, "alarm_mpa": 0.55, "minimum_mpa": 0.52,
           "heat_k": 3.0},
}

points = []
GAS_GROUP = {"cb": "GasCB", "bb": "GasBB", "ld": "GasLD", "vt": "GasVT"}
for c, g in GAS_GROUP.items():
    points += [
        {"metric": f"gas_{c}_p_mpa", "path": f"{g}.Pressure", "label": f"Gas pressure, {c.upper()} compartment (absolute)", "unit": "MPa abs"},
        {"metric": f"gas_{c}_t_c", "path": f"{g}.Temperature", "label": f"Gas temperature, {c.upper()} compartment", "unit": "°C"},
        {"metric": f"gas_{c}_slope_kpa_yr", "path": f"{g}.TrendP20", "label": f"30-day trend of the pressure at 20 °C, {c.upper()} (gas monitor)", "unit": "kPa/yr"},
        {"metric": f"gas_{c}_h2o_ppmv", "path": f"{g}.Moisture", "label": f"Moisture in the gas, {c.upper()} compartment", "unit": "ppmv"},
        {"metric": f"pd_{c}_dbm", "path": f"PD.{c.upper()}Amplitude", "label": f"UHF partial discharge peak, {c.upper()} sensor", "unit": "dBm"},
        {"metric": f"pd_{c}_pps", "path": f"PD.{c.upper()}Pulses", "label": f"UHF partial discharge pulses per second, {c.upper()} sensor", "unit": "1/s"},
    ]
points += [
    {"metric": "cb_so2_ppmv", "path": "GasCB.SO2", "label": "SO2 in the CB compartment, last gas analysis", "unit": "ppmv"},
    {"metric": "cb_open_ms", "path": "Breaker.OpenTime", "label": "Opening time, last operation (slowest pole)", "unit": "ms"},
    {"metric": "cb_close_ms", "path": "Breaker.CloseTime", "label": "Closing time, last operation (slowest pole)", "unit": "ms"},
    {"metric": "cb_armature_ms", "path": "Breaker.ArmatureTime", "label": "Trip coil current: time to the armature dip, last opening", "unit": "ms"},
    {"metric": "cb_trip_coil_a", "path": "Breaker.TripCoilPeak", "label": "Trip coil peak current, last opening", "unit": "A"},
    {"metric": "cb_charge_s", "path": "Breaker.ChargeTime", "label": "Spring charging motor run time, last charge", "unit": "s"},
    {"metric": "cb_wear_ka2s", "path": "Breaker.WearI2t", "label": "Contact wear: sum of I²·t arcing, worst pole", "unit": "kA²s"},
    {"metric": "cb_ops", "path": "Breaker.Operations", "label": "Breaker operations since commissioning", "unit": "count"},
    {"metric": "ds1_motor_a", "path": "Switches.DS1MotorPeak", "label": "Busbar disconnector DS1: motor peak current, last operation", "unit": "A"},
    {"metric": "ds1_time_s", "path": "Switches.DS1Time", "label": "Busbar disconnector DS1: operating time, last operation", "unit": "s"},
    {"metric": "es2_motor_a", "path": "Switches.ES2MotorPeak", "label": "Line earthing switch ES2: motor peak current, last operation", "unit": "A"},
    {"metric": "es2_time_s", "path": "Switches.ES2Time", "label": "Line earthing switch ES2: operating time, last operation", "unit": "s"},
    {"metric": "vt_bay_kv", "path": "Instr.VTBay", "label": "Bay voltage transformer, phase-to-phase (primary)", "unit": "kV"},
    {"metric": "vt_bus_kv", "path": "Instr.VTBus", "label": "Busbar voltage transformer, phase-to-phase (primary)", "unit": "kV"},
    {"metric": "ct_prot_a", "path": "Instr.CTProtection", "label": "Feeder current, protection core", "unit": "A"},
    {"metric": "ct_meas_a", "path": "Instr.CTMetering", "label": "Feeder current, metering core", "unit": "A"},
    {"metric": "amb_t_c", "path": "Bay.Ambient", "label": "GIS hall air temperature", "unit": "°C"},
]

twin = {
    "$comment": "GIS-7401 gas-insulated switchgear bay twin. Expected values in Maximo Monitor from the maker's ratings, the gas schematic and NIST SF6 data; the bay sends only what its IEDs measure.",
    "twin": {"id": "GIS-7401", "name": "Gas-insulated switchgear bay GIS-7401", "version": "1.0.0", "folder": "gis-twin"},
    "identification": {
        "asset": "GIS-7401", "assetnum": "GIS-7401", "manufacturer": "Hitachi Energy", "model": "ELK-04 C 145 kV",
        "description": "132 kV cable feeder bay 4 of an indoor gas-insulated substation (one bay, four SF6 gas compartments)",
        "site": "Demo transmission substation (indoor GIS hall)",
        "bay": "Single busbar section, busbar disconnector DS1 + earthing switch ES1, circuit breaker CB with CTs, line disconnector DS2 + earthing switch ES2 + fast earthing switch FES, VT, cable sealing end",
        "monitoring": "Gas density transmitters per compartment, UHF partial discharge sensors, breaker and switch monitoring in the bay controller (IEC 61850)",
    },
    "design": {
        "rating": {"ur_kv": 145.0, "system_kv": 132.0, "fr_hz": "50/60", "ud_kv": 275, "up_kv": 650, "ir_a": 3150, "isc_ka": 40, "tk_s": 3,
                   "ip_ka": 108, "bay_width_mm": 800, "ambient_c": [-30, 55], "installation": "indoor / outdoor",
                   "source": "Hitachi Energy, Gas-insulated switchgear ELK-04 C up to 145 kV, product page technical data"},
        "compartments": {**COMP, "source": "Four gas compartments per bay, volumes, rated filling, alarm and minimum functional pressures "
                                           "(absolute, at 20 °C), gas heating at rated current: " + A},
        "sf6": {"gas": "SF6", "molar_mass_g_mol": 146.055, "r_j_kgk": round(R_SF6, 6), "gwp100": 24300, "co2e_detection_t": 500,
                "eos_a": a, "eos_q": q, "eos_max_err_rho_pct": round(err_rho, 3), "eos_max_err_p20_pct": round(err_p20, 4),
                "eos_range": "263.15 ... 333.15 K, 0.30 ... 0.80 MPa abs",
                "source": "Z(p,T) = 1 + p (a0 + a1/T + a2/T^2) + a3 p^2/T and p20 = rho R 293.15 (1 + q1 rho + q2 rho^2), least-squares fits of the "
                          "NIST Chemistry WebBook SF6 isotherms listed in build_twin.py. GWP100 24 300 and the 500 t CO2e leakage-detection threshold: Regulation (EU) 2024/573."},
        "tightness": {"type_test_pct_yr": 0.1, "class_pct_yr": 0.5,
                      "source": "IEC 62271-203:2022 reduced the type-test tightness requirement for gases with GWP > 1000 from 0.5 % to 0.1 % per year per gas "
                                "compartment. The twin alerts at 0.5 %/year (the older class most installed bays were tested to)."},
        "breaker": {"mechanism": "stored-energy spring", "open_ms": 25.0, "close_ms": 55.0, "armature_ms": 7.0, "coil_v": 110.0, "coil_r_ohm": 55.0,
                    "charge_s": 15.0, "wear_allow_ka2s": 480.0, "wear_note": "20 interruptions of 40 kA with 15 ms of arcing",
                    "source": "Spring mechanism, operating times, trip coil, charging time and I²t wear allowance: " + A},
        "switches": {"ds1_motor_a": 2.5, "ds1_time_s": 4.0, "es2_motor_a": 2.5, "es2_time_s": 3.0,
                     "source": "Disconnector and earthing switch motor-drive peak current and operating time from the routine test: " + A},
        "gas_quality": {"h2o_alert_ppmv": 300.0, "so2_alert_ppmv": 5.0,
                        "source": "Moisture and SO2 action levels in service: " + A + " (IEC 60480 gives the limits for re-use of recovered gas, not these)"},
        "pd": {"noise_dbm": -72.0, "alert_dbm": -50.0, "alert_pps": 20.0,
               "source": "UHF sensor noise floor and the PD alarm (amplitude and pulse rate together), set at commissioning after the sensitivity check of IEC TS 62478: " + A},
        "instr": {"vt_drift_alert_pct": 1.0, "ct_mismatch_alert_pct": 2.0, "vt_class": "0.5",
                  "source": "Two class 0.5 voltage transformers may differ by up to 1 %; protection and metering core of the same CT should agree within 2 % at load: " + A},
        "load": {"peak_a": 900.0, "min_a": 300.0, "hall_c": 24.0, "hall_swing_c": 5.0,
                 "source": "Daily load profile of the feeder and GIS hall temperature: " + A},
        "demo": {"time_scale": 60, "op_every_s": 30,
                 "note": "Demo only: the plant clock runs 60 times faster, and the breaker and the switches are operated every 30 s of real time so their timings refresh; leak and wear figures come from the failure modes, not from the demo clock."},
    },
    "telemetry": {
        "event": "gis", "publish_every_s": 10, "device_type": "GIS_BAY",
        "groups": {"GasCB": "Circuit breaker compartment", "GasBB": "Busbar disconnector compartment", "GasLD": "Line disconnector compartment",
                   "GasVT": "Voltage transformer compartment", "PD": "UHF partial discharge monitor", "Breaker": "Circuit breaker monitoring",
                   "Switches": "Disconnector and earthing switch drives", "Instr": "Instrument transformers", "Bay": "Bay and hall"},
        "points": points,
    },
    "twin_model": {
        "limits": {"leak_pct_yr": 0.5, "days_to_alarm": 90.0, "above_fill_mpa": 0.015, "open_ratio": 1.15, "armature_ratio": 1.25,
                   "charge_ratio": 1.3, "wear_pct": 80.0, "ds_motor_ratio": 1.3, "ds_time_ratio": 1.25,
                   "h2o_ppmv": 300.0, "so2_ppmv": 5.0, "pd_dbm": -50.0, "pd_pps": 20.0, "vt_drift_pct": 1.0, "ct_mismatch_pct": 2.0,
                   "coil_dev": 0.2},
        "health_index": {"penalty_at_limit": 60, "u_max": 1.5,
                         "note": "Each part = 100 - 60 x the worst indicator's distance to its limit (0 = normal value, 1 = at the limit, capped at 1.5). Bay = the weakest part."},
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "cb_compartment_leak": {"name": "SF6 leak, circuit breaker compartment", "part": "gas",
                                "symptoms": "pressure at 20 °C falls, 30-day trend negative, leak rate above the tightness class, days to the alarm density shrink",
                                "rules": ["GIS_LEAK_RATE_HIGH", "GIS_DENSITY_ALARM_SOON", "GIS_DENSITY_ALARM"], "default_ramp_min": 1.5},
        "density_sensor_drift": {"name": "Gas density sensor drift, busbar compartment", "part": "gas",
                                 "symptoms": "reading above the filled density with a rising trend: physically impossible without a gas top-up, so the sensor drifts (and would hide a leak)",
                                 "rules": ["GIS_DENSITY_ABOVE_FILL"], "default_ramp_min": 1},
        "cb_slow_mechanism": {"name": "Breaker mechanism slow (lubrication, latch)", "part": "breaker",
                              "symptoms": "opening time and trip coil armature time up, coil current and charging normal",
                              "rules": ["GIS_CB_SLOW_OPEN", "GIS_CB_TRIP_COIL"], "default_ramp_min": 1},
        "cb_contact_wear": {"name": "Arcing contact wear after fault interruptions", "part": "breaker",
                            "symptoms": "I²t sum near the allowance, SO2 from arcing rises in the CB compartment",
                            "rules": ["GIS_CB_WEAR_HIGH", "GIS_SO2_HIGH"], "default_ramp_min": 1},
        "ds_motor_wear": {"name": "Disconnector drive stiff (gearbox, linkage)", "part": "switches",
                          "symptoms": "DS1 motor peak current and operating time up", "rules": ["GIS_DS_MOTOR_HIGH", "GIS_DS_SLOW"], "default_ramp_min": 1},
        "moisture_ingress": {"name": "Moisture ingress, line disconnector compartment", "part": "gas",
                             "symptoms": "moisture ppmv rises in one compartment, density normal", "rules": ["GIS_MOISTURE_HIGH"], "default_ramp_min": 1},
        "internal_pd": {"name": "Internal partial discharge (particle, floating electrode), busbar compartment", "part": "gas",
                        "symptoms": "UHF amplitude and pulse rate rise on one sensor only", "rules": ["GIS_PD_DETECTED"], "default_ramp_min": 0.5},
        "vt_drift": {"name": "Voltage transformer output drift", "part": "instr",
                     "symptoms": "bay VT reads away from the busbar VT with the disconnectors closed", "rules": ["GIS_VT_DRIFT"], "default_ramp_min": 1},
    },
    "presentation": {"title": "GIS-7401 gas-insulated switchgear bay", "dashboard": "GIS_BAY"},
}

if __name__ == "__main__":
    out = HERE / "twin" / "gis-7401.twin.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
    print("written", out, f"EOS fit: density {err_rho:.3f} %, p20 {err_p20:.4f} %")
