"""Write twin/pv-3101.twin.json: the utility PV block twin (PV-3101).

    python build_twin.py

PV-3101 is one inverter block of a ground-mounted utility PV plant: one Huawei SUN2000-330KTL-H1 string inverter (6 MPPT),
24 strings of 27 JinkoSolar Tiger Neo JKM580N-72HL4-BDV bifacial modules on fixed-tilt open racks (648 modules, 375.84 kWp),
and the block's weather station: a clean (washed) reference cell in the plane of array, a second reference cell left
unwashed (soiling station), a module back-of-module temperature sensor, ambient temperature and wind speed.

Sources and assumptions (every number below is either from a data sheet / standard or labelled as an assumption in "source"):
  JinkoSolar data sheet JKM560-580N-72HL4-BDV-F6-EN (2023): STC and NOCT values of the 580 W module, temperature
    coefficients (Pmax -0.29 %/C, Voc -0.25 %/C, Isc +0.045 %/C), NOCT 45 C, bifacial factor 80 +/- 5 %, max system voltage
    1500 V, max series fuse 30 A, linear power warranty (99 % after year 1, -0.40 %/year, 87.4 % after 30 years).
  Huawei SUN2000-330KTL-H1 data sheet and product page: 330 kVA / 330 kW max (cos phi = 1), 300 kW nominal, max efficiency
    99.0 %, European efficiency 98.8 %, 6 MPPT, 65 A per MPPT, 4/5/5/4/5/5 inputs, 1500 V max, MPPT range 500-1500 V,
    operating temperature -25 to 60 C, DC insulation resistance detection, string fault monitoring.
  IEC 61724-1:2021: performance ratio, temperature-corrected performance ratio, soiling ratio.
  PVWatts v5 (Dobos, NREL/TP-6A20-62641, 2014): DC power model and the inverter part-load efficiency curve.
  Sandia array performance model (King et al., SAND2004-3535): cell temperature = back-of-module temperature + G/1000 x 3 C.
  IEC 62109-2:2011 clause 4.8.2: minimum array insulation resistance = max PV voltage / 30 mA.
  Inverter temperature derating curve, heat rise, Riso alert level, losses, soiling rate, cleaning cost and energy price:
    ASSUMPTIONS, labelled below, to be replaced by the inverter user manual, the plant design report and your O&M contract.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with "
JINKO = "JinkoSolar data sheet JKM560-580N-72HL4-BDV-F6-EN (2023), column JKM580N-72HL4-BDV"
HUAWEI = "Huawei SUN2000-330KTL-H1 data sheet and product page (solar.huawei.com)"

N_STRINGS = 24
twin = {
    "$comment": "PV-3101 utility PV block twin. Expected values in Maximo Monitor from module and inverter data sheets and IEC 61724-1; the block sends only what it measures.",
    "twin": {"id": "PV-3101", "name": "Utility PV block PV-3101", "version": "1.0.0", "folder": "pv-twin"},
    "identification": {
        "asset": "PV-3101", "assetnum": "PV-3101", "manufacturer": "Huawei SUN2000-330KTL-H1 + JinkoSolar",
        "model": "Tiger Neo JKM580N-72HL4-BDV (24 strings x 27)",
        "description": "PV block 31, inverter 01: 375.84 kWp DC / 330 kVA AC, fixed-tilt bifacial array with weather station",
        "inverter": "Huawei SUN2000-330KTL-H1 smart string inverter, 6 MPPT, 1500 V",
        "module": "JinkoSolar Tiger Neo N-type JKM580N-72HL4-BDV, 580 Wp bifacial dual glass, 144 half cells",
        "array": "24 strings x 27 modules = 648 modules, 4 strings per MPPT, fixed tilt, 2 modules in portrait, open rack",
        "weather_station": "Clean plane-of-array reference cell (washed daily), unwashed soiling reference cell, back-of-module PT100, ambient temperature, wind speed",
    },
    "design": {
        "module": {
            "pmax_w": 580.0, "vmp_v": 42.59, "imp_a": 13.62, "voc_v": 51.47, "isc_a": 14.37, "efficiency_pct": 22.45,
            "pmax_noct_w": 436.0, "gamma_pmax_pct_per_c": -0.29, "beta_voc_pct_per_c": -0.25, "alpha_isc_pct_per_c": 0.045,
            "noct_c": 45.0, "bifaciality": 0.80, "max_system_v": 1500.0, "max_series_fuse_a": 30.0, "cells": 144,
            "dimensions_mm": [2278, 1134, 30], "weight_kg": 32.0,
            "degradation_first_year_pct": 1.0, "degradation_annual_pct": 0.40, "warranty_30y_pct": 87.4,
            "certification": "IEC 61215 (2016), IEC 61730 (2016) as printed on the data sheet",
            "source": JINKO + ": STC 580 Wp, Vmp 42.59 V, Imp 13.62 A, Voc 51.47 V, Isc 14.37 A, 22.45 %; NOCT 436 Wp; temperature "
                      "coefficients; NOCT 45 +/- 2 C; bifacial factor 80 +/- 5 %; 1500 V DC (IEC); 30 A fuse; linear warranty.",
        },
        "array": {
            "modules_per_string": 27, "strings": N_STRINGS, "strings_per_mppt": 4, "mppt": 6,
            "rear_irradiance_ratio": 0.07, "dc_loss_frac": 0.02, "site_min_temp_c": -5.0, "tilt_deg": 25,
            "source": "String sizing: 27 x Voc at the site minimum temperature must stay below 1500 V (module and inverter limit). "
                      "Rear/front irradiance ratio 0.07 on a fixed-tilt 2P table, DC wiring + mismatch loss 2 %, site minimum -5 C, tilt 25 deg: "
                      + A + "your plant design report (PVsyst or similar).",
        },
        "inverter": {
            "p_ac_max_kw": 330.0, "p_ac_nom_kw": 300.0, "eta_max": 0.990, "eta_euro": 0.988,
            "mppt": 6, "max_current_per_mppt_a": 65.0, "max_isc_per_mppt_a": 115.0, "inputs_per_mppt": [4, 5, 5, 4, 5, 5],
            "v_max": 1500.0, "mppt_v_min": 500.0, "mppt_v_max": 1500.0, "start_v": 550.0, "op_temp_c": [-25, 60],
            "source": HUAWEI + ": 330,000 VA / 330,000 W (cos phi 1), nominal 300,000 W, max efficiency 99.0 %, European 98.8 %, "
                      "6 MPPT, 65 A / 115 A per MPPT, 4/5/5/4/5/5 inputs, 1500 V, 500-1500 V MPPT, start 550 V, -25 to 60 C.",
        },
        "efficiency_curve": {
            "eta_nom": 0.988, "eta_ref": 0.9637,
            "source": "PVWatts v5 part-load curve (Dobos 2014, NREL/TP-6A20-62641): eta = eta_nom/eta_ref x (-0.0162 z - 0.0059/z + 0.9858), "
                      "z = Pdc / (Pac0/eta_nom). eta_nom set to the European efficiency 98.8 %, which puts the peak of the curve at 99.0 % "
                      "(the data sheet maximum).",
        },
        "derating": {
            "temp_c": [40.0, 50.0, 60.0], "p_kw": [330.0, 300.0, 165.0], "heat_rise_full_load_k": 15.0,
            "source": "Active power limit against ambient temperature and internal temperature rise at full load: " + A
                      + "the derating curve in the SUN2000 user manual. Huawei states the operating range -25 to 60 C but the data sheet gives no curve.",
        },
        "insulation": {
            "riso_limit_kohm": 50.0, "riso_alert_kohm": 500.0, "riso_typical_kohm": 3000.0,
            "source": "Limit = 1500 V / 30 mA = 50 kOhm (IEC 62109-2:2011 clause 4.8.2: the inverter must not connect below Vmax PV / 30 mA). "
                      "Alert 500 kOhm and a dry-array value of about 3 MOhm: " + A + "the commissioning insulation test (IEC 62446-1) of your array.",
        },
        "weather": {
            "g_min_wm2": 300.0, "cell_delta_t_c": 3.0, "g_stc_wm2": 1000.0,
            "source": "Rules run only above 300 W/m2 in the plane of array (" + A + "the filter in your O&M contract). Cell temperature = "
                      "back-of-module temperature + G/1000 x 3 C (Sandia array performance model, open rack).",
        },
        "plant": {"years_in_service": 3.2, "source": "Years since commercial operation, sent by the plant SCADA."},
        "cleaning": {
            "soiling_rate_per_day": 0.003, "cost_usd_per_module": 0.15, "energy_price_usd_per_kwh": 0.04,
            "specific_yield_kwh_per_kwp_day": 6.0,
            "source": "Soiling rate 0.3 %/day, cleaning cost 0.15 USD per module (water truck + crew), energy price 0.04 USD/kWh, "
                      "6 kWh/kWp/day: " + A + "your soiling station history, O&M contract and power purchase agreement.",
        },
        "demo": {"time_scale": 30, "night_speedup": 10, "start_hour": 10.0,
                 "note": "Demo only: the plant clock runs 30 times faster by day and 300 times faster by night, so a whole day passes in about 30 minutes."},
    },
    "telemetry": {
        "event": "pvblock", "publish_every_s": 60, "device_type": "PV_BLOCK_STRING_INV",
        "groups": {"Weather": "Weather station of the block", "Inverter": "String inverter", "Plant": "Plant controller and SCADA",
                   "Strings": "String currents measured by the inverter"},
        "points": [
            {"metric": "poa_wm2", "path": "Weather.POA", "label": "Plane-of-array irradiance, clean reference cell", "unit": "W/m²"},
            {"metric": "poa_soiled_wm2", "path": "Weather.POASoiled", "label": "Plane-of-array irradiance, unwashed reference cell", "unit": "W/m²"},
            {"metric": "module_temp_c", "path": "Weather.ModuleTemp", "label": "Back-of-module temperature", "unit": "°C"},
            {"metric": "ambient_temp_c", "path": "Weather.Ambient", "label": "Ambient air temperature", "unit": "°C"},
            {"metric": "wind_ms", "path": "Weather.Wind", "label": "Wind speed", "unit": "m/s"},
            {"metric": "p_dc_kw", "path": "Inverter.PDC", "label": "DC input power (all MPPTs)", "unit": "kW"},
            {"metric": "v_dc_v", "path": "Inverter.VDC", "label": "Mean MPPT voltage", "unit": "V"},
            {"metric": "p_ac_kw", "path": "Inverter.PAC", "label": "AC active power", "unit": "kW"},
            {"metric": "inv_running", "path": "Inverter.State", "label": "Inverter on grid (1 = on grid)", "unit": "code"},
            {"metric": "inv_temp_c", "path": "Inverter.Temperature", "label": "Inverter internal temperature", "unit": "°C"},
            {"metric": "p_max_kw", "path": "Inverter.PMaxAvailable", "label": "Active power the inverter can deliver now (its own limit)", "unit": "kW"},
            {"metric": "riso_kohm", "path": "Inverter.Riso", "label": "DC insulation resistance (last start-up test)", "unit": "kΩ"},
            {"metric": "setpoint_pct", "path": "Plant.Setpoint", "label": "Active power setpoint from the plant controller", "unit": "%"},
            {"metric": "years_in_service", "path": "Plant.YearsInService", "label": "Years since commercial operation", "unit": "y"},
        ] + [{"metric": f"i_s{i:02d}_a", "path": f"Strings.S{i:02d}", "label": f"String {i:02d} current (MPPT {(i - 1) // 4 + 1})", "unit": "A"}
             for i in range(1, N_STRINGS + 1)],
    },
    "twin_model": {
        "limits": {
            "soiling_alert_pct": 3.0, "pi_low": 0.92, "string_open_ratio": 0.10, "string_low_ratio": 0.90,
            "eff_drop": 0.015, "inv_temp_excess_k": 10.0, "derate_margin_kw": 16.5, "limited_frac": 0.98,
            "min_dc_frac": 0.10, "sensor_pi_high": 1.06, "sensor_sr_high": 1.03,
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "soiling": {"name": "Soiling (dust on the modules)", "part": "array",
                    "symptoms": "unwashed reference cell falls behind the clean one; DC power falls by the same fraction; corrected performance normal",
                    "rules": ["PV_SOILING_HIGH", "PV_CLEANING_DUE"], "default_ramp_min": 1.5},
        "string_open": {"name": "String open (blown fuse, burnt connector)", "part": "string",
                        "symptoms": "one string current at zero, the others normal", "rules": ["PV_STRING_OPEN"], "default_ramp_min": 0.5},
        "string_bypass": {"name": "Cracked cells / bypass diodes on in one string", "part": "string",
                          "symptoms": "one string 20 to 30 % below the others", "rules": ["PV_STRING_LOW"], "default_ramp_min": 1},
        "module_degradation": {"name": "Module degradation faster than warranty (PID, LeTID)", "part": "modules",
                               "symptoms": "all strings low together; soiling-corrected performance index falls", "rules": ["PV_DC_UNDERPERFORM"], "default_ramp_min": 1.5},
        "ground_fault": {"name": "Insulation fault / ground fault on the DC side", "part": "cables",
                         "symptoms": "insulation resistance falls; below 50 kOhm the inverter will not connect", "rules": ["PV_RISO_LOW", "PV_RISO_TRIP", "PV_INVERTER_DOWN"], "default_ramp_min": 1},
        "inverter_cooling": {"name": "Inverter cooling degraded (fan, clogged filter)", "part": "inverter",
                             "symptoms": "internal temperature above expected; the inverter derates below its curve", "rules": ["PV_INV_HOT", "PV_DERATE_EARLY"], "default_ramp_min": 1},
        "inverter_efficiency": {"name": "Inverter power stage losses (IGBT, filter)", "part": "inverter",
                                "symptoms": "AC / DC below the efficiency curve", "rules": ["PV_INV_EFF_LOW"], "default_ramp_min": 1},
        "irradiance_sensor": {"name": "Clean reference cell dirty or drifting", "part": "weather station",
                              "symptoms": "performance index above 1 and soiling ratio above 1: physically impossible", "rules": ["PV_IRRADIANCE_SENSOR"], "default_ramp_min": 1},
    },
    "presentation": {"title": "PV-3101 utility PV block", "dashboard": "PV_BLOCK_STRING_INV"},
}

out = HERE / "twin" / "pv-3101.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
