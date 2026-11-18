"""Write twin/wtg-3001.twin.json: the wind turbine drivetrain twin (WTG-3001).

    python build_twin.py

WTG-3001 is a Vestas V90-2.0 MW (50 Hz) on an onshore wind farm: 90 m rotor, pitch regulated with variable speed, a main
shaft on its main bearing, a three-stage gearbox (one planetary stage and two helical stages) and a 4-pole doubly fed
asynchronous generator. The turbine controller sends SCADA 10-minute averages; a condition monitoring system (CMS) on the
drivetrain sends vibration band values and an inline oil particle counter sends ISO 4406 counts and a ferrous particle count.

Sources (public):
  Vestas V90-1.8/2.0 MW brochure (06/2009-EN), technical data: rated power 2,000 kW, cut-in 4 m/s, rated 12 m/s, cut-out
      25 m/s, rotor 90 m, swept area 6,362 m2, nominal 14.5 rpm, operational interval 9.3-16.6 rpm, 50 Hz 4-pole
      asynchronous generator with variable speed, 3-stage planetary/helical gearbox, hub heights 80/95/105 m (IEC IIA),
      operating temperature -20 to 40 C; condition monitoring system offered as an option.
  Power curve: OEDB wind turbine library entry "V90/2000" as shipped with windpowerlib (power_curves.csv), 3.5 to 16.5 m/s;
      it matches the brochure chart (cut-in 4 m/s, 2,000 kW from about 12 m/s). Held flat to the 25 m/s cut-out.
  IEC 61400-12-1 (power performance): 10-minute air density rho = B / (R0 T), R0 = 287.05 J/(kg K); for a turbine with
      active power control the wind speed is normalised: Vn = V (rho / rho0)^(1/3). (Quoted in a TU Delft MSc thesis on
      power curve warranties.) The humidity term of the 2017 edition is left out here (assumption).
  ISO 4406: the scale number of a size channel (>= 4, 6, 14 um(c)) doubles per step: code 10 is more than 5 and up to 10
      particles per mL, code 12 is 20 to 40, code 15 is 160 to 320 (the printed table rounds above code 16).
  Bearing defect frequency (textbook): BPFO = n/2 x f_shaft x (1 - d/D cos(phi)). Gear mesh = teeth x shaft speed.
Assumptions (labelled in "source"): gearbox tooth counts, the HSS bearing geometry, the thermal and vibration baseline
  coefficients (in practice fitted on a few months of healthy data), every alarm limit, the site pressure and the TSR.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with "
BRO = "Vestas V90-1.8/2.0 MW brochure (06/2009-EN), technical data"

WS = [3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0, 13.5,
      14.0, 14.5, 15.0, 15.5, 16.0, 16.5, 25.0]
KW = [0.0, 42.2, 93.3, 145.2, 211.3, 284.2, 390.9, 491.5, 601.1, 731.8, 884.5, 1087.6, 1247.1, 1429.6, 1594.3, 1742.9, 1861.2,
      1948.1, 1993.3, 2003.5, 2007.0, 2007.7, 2007.3, 2007.4, 2007.0, 2006.8, 2006.7, 2006.5, 2006.5]

twin = {
    "$comment": "WTG-3001 wind turbine drivetrain twin. Expected power from the published power curve with the IEC 61400-12-1 air density "
                "normalisation; expected temperatures and vibration bands from load-and-ambient models; the turbine sends only what it measures.",
    "twin": {"id": "WTG-3001", "name": "Wind turbine WTG-3001 drivetrain", "version": "1.0.0", "folder": "windgbx-twin"},
    "identification": {
        "asset": "WTG-3001", "assetnum": "WTG-3001", "manufacturer": "Vestas", "model": "V90-2.0 MW (50 Hz)",
        "description": "Onshore wind turbine, drivetrain twin: main bearing, three-stage gearbox and doubly fed generator",
        "rotor": "3 blades, 90 m diameter, pitch regulated with variable speed",
        "gearbox": "3-stage: 1 planetary stage + 2 helical stages",
        "generator": "4-pole doubly fed (wound-rotor) asynchronous generator, 50 Hz, with a rotor-side converter",
        "cms": "Drivetrain condition monitoring system (accelerometers on main bearing, gearbox and generator) + inline oil particle counter",
        "site": "An onshore wind farm, hub height 80 m (generic)",
    },
    "design": {
        "rotor": {"rated_kw": 2000.0, "cut_in_ms": 4.0, "rated_ms": 12.0, "cut_out_ms": 25.0, "diameter_m": 90.0, "swept_m2": 6362.0,
                  "rotor_rpm_nominal": 14.5, "rotor_rpm_min": 9.3, "rotor_rpm_max": 16.6, "hub_height_m": 80.0,
                  "source": BRO + ". IEC wind class IIA at 80 m hub height."},
        "power_curve": {"wind_ms": WS, "power_kw": KW, "rho_ref": 1.225,
                        "source": "OEDB wind turbine library, turbine type V90/2000 (windpowerlib power_curves.csv), 3.5 to 16.5 m/s; held flat "
                                  "to the 25 m/s cut-out as in the brochure chart. Reference density 1.225 kg/m3: " + A + "the warranted power curve of your contract"},
        "density": {"R0": 287.05, "exponent": 1 / 3,
                    "source": "IEC 61400-12-1 air density from 10-min pressure and temperature, normalisation of wind speed for active power control turbines"},
        "drivetrain": {"z_ring": 99, "z_sun": 21, "n_planets": 3, "z_wheel2": 85, "z_pinion2": 23, "z_wheel3": 96, "z_pinion3": 18,
                       "poles": 4, "grid_hz": 50.0, "tsr_opt": 8.0,
                       "source": "Gearbox type and generator from the " + BRO + ". Tooth counts (ratio about 1:113) and the optimum tip speed ratio: "
                                 + A + "the gearbox data sheet (tooth counts are needed for the mesh frequencies)"},
        "hss_bearing": {"rollers": 14, "roller_d_mm": 32.0, "pitch_d_mm": 150.0, "contact_deg": 0.0,
                        "source": "High-speed shaft bearing (cylindrical roller, generator side): " + A + "the bearing maker's geometry or its published defect frequency factors"},
        "thermal": {"oil_a0": 32.0, "oil_a1": 18.0, "hss_b0": 4.0, "hss_b1": 10.0, "mb_m0": 8.0, "mb_m1": 14.0,
                    "source": "Expected temperature = ambient (or oil) + c0 + c1 x load fraction. " + A + "a least-squares fit on 3 months of healthy SCADA data of this turbine"},
        "vibration": {"planet0": 0.6, "planet1": 1.2, "hssmesh0": 2.0, "hssmesh1": 5.0, "hssenv0": 0.8, "hssenv1": 0.6, "mbenv0": 0.15, "mbenv1": 0.15,
                      "gbxrms0": 1.2, "gbxrms1": 1.6,
                      "source": "CMS band values (m/s2) and gearbox overall velocity (mm/s, 10-1000 Hz) = b0 + b1 x load fraction. " + A + "the CMS baseline learnt on this turbine"},
        "oil": {"iso_target": [None, 15, 12], "fe_limit_24h": 15, "oil_max_c": 80.0,
                "source": "Oil cleanliness target -/15/12 (ISO 4406), ferrous particles per 24 h and maximum sump temperature: " + A + "the gearbox maker's lubrication specification"},
        "site": {"pressure_hpa": 980.0, "ambient_c": 15.0,
                 "source": "Site about 300 m above sea level: " + A + "the met mast or nacelle barometer of the site"},
        "demo": {"time_scale": 60, "wind_mean_ms": 9.5, "ambient_c": 25.0,
                 "note": "Demo only: one real second is one plant minute, so one 10-minute SCADA record is published every 10 real seconds; wind follows a random walk around 9.5 m/s on a warm day so every rule can show."},
    },
    "telemetry": {
        "event": "wtg", "publish_every_s": 10, "device_type": "WIND_TURBINE_DFIG",
        "groups": {"Wind": "Nacelle anemometer and vane (10-min means)", "Ambient": "Ambient conditions", "Grid": "Active power and state",
                   "Rotor": "Rotor, pitch and speeds", "Gearbox": "Gearbox temperatures", "MainBearing": "Main bearing",
                   "Generator": "Generator temperatures", "CMS": "Condition monitoring system band values", "Oil": "Inline oil particle counter"},
        "points": [
            {"metric": "wind_speed_ms", "path": "Wind.Speed", "label": "Nacelle wind speed, 10-min mean", "unit": "m/s"},
            {"metric": "yaw_error_deg", "path": "Wind.YawError", "label": "Wind direction relative to the nacelle, 10-min mean", "unit": "°"},
            {"metric": "ambient_temp_c", "path": "Ambient.Temperature", "label": "Ambient temperature", "unit": "°C"},
            {"metric": "ambient_pressure_hpa", "path": "Ambient.Pressure", "label": "Ambient air pressure", "unit": "hPa"},
            {"metric": "active_power_kw", "path": "Grid.ActivePower", "label": "Active power, 10-min mean", "unit": "kW"},
            {"metric": "turbine_state", "path": "Grid.State", "label": "Turbine state (1 = producing)", "unit": "code"},
            {"metric": "rotor_rpm", "path": "Rotor.Speed", "label": "Rotor speed", "unit": "rpm"},
            {"metric": "gen_rpm", "path": "Rotor.GeneratorSpeed", "label": "Generator speed", "unit": "rpm"},
            {"metric": "pitch_deg", "path": "Rotor.Pitch", "label": "Blade pitch angle", "unit": "°"},
            {"metric": "gbx_oil_temp_c", "path": "Gearbox.OilSump", "label": "Gearbox oil sump temperature", "unit": "°C"},
            {"metric": "gbx_hss_brg_temp_c", "path": "Gearbox.HSSBearing", "label": "Gearbox high-speed shaft bearing temperature", "unit": "°C"},
            {"metric": "main_brg_temp_c", "path": "MainBearing.Temperature", "label": "Main bearing temperature", "unit": "°C"},
            {"metric": "gen_winding_temp_c", "path": "Generator.Winding", "label": "Generator stator winding temperature", "unit": "°C"},
            {"metric": "gen_brg_temp_c", "path": "Generator.Bearing", "label": "Generator drive-end bearing temperature", "unit": "°C"},
            {"metric": "nacelle_temp_c", "path": "Ambient.Nacelle", "label": "Nacelle air temperature", "unit": "°C"},
            {"metric": "vib_planet_mesh", "path": "CMS.PlanetMesh", "label": "Gearbox acceleration at the planetary gear mesh frequency", "unit": "m/s²"},
            {"metric": "vib_hss_mesh", "path": "CMS.HSSMesh", "label": "Gearbox acceleration at the high-speed gear mesh frequency", "unit": "m/s²"},
            {"metric": "vib_hss_brg_env", "path": "CMS.HSSBearingEnv", "label": "Envelope acceleration at the HSS bearing outer-race frequency", "unit": "m/s²"},
            {"metric": "vib_mb_env", "path": "CMS.MainBearingEnv", "label": "Envelope acceleration at the main bearing", "unit": "m/s²"},
            {"metric": "vib_gbx_rms_mms", "path": "CMS.GearboxOverall", "label": "Gearbox overall vibration velocity, 10-1000 Hz rms", "unit": "mm/s"},
            {"metric": "pc_4um_per_ml", "path": "Oil.Count4", "label": "Particles >= 4 um(c) per mL", "unit": "/mL"},
            {"metric": "pc_6um_per_ml", "path": "Oil.Count6", "label": "Particles >= 6 um(c) per mL", "unit": "/mL"},
            {"metric": "pc_14um_per_ml", "path": "Oil.Count14", "label": "Particles >= 14 um(c) per mL", "unit": "/mL"},
            {"metric": "fe_particles_24h", "path": "Oil.Ferrous24h", "label": "Ferrous wear particles counted, last 24 h", "unit": "count"},
        ],
    },
    "twin_model": {
        "limits": {
            "underperf_ratio": 0.88, "underperf_vmin_ms": 5.0, "underperf_vmax_ms": 11.0, "yaw_alert_deg": 8.0,
            "oil_residual_c": 6.0, "hss_residual_c": 5.0, "mb_residual_c": 6.0,
            "planet_ratio": 2.0, "hss_env_ratio": 2.5, "mb_env_ratio": 2.5, "gbx_rms_mms": 4.5,
            "source": "Alarm limits: " + A + "your fleet statistics. The gearbox overall velocity limit stands for the zone boundary of ISO 10816-21 "
                      "Annex A at your measurement position (that standard's zones are for acceptance, not for early fault detection).",
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "hss_bearing_damage": {"name": "Gearbox HSS bearing damage (axial cracks, spalling)", "part": "gearbox",
                               "symptoms": "bearing runs hotter than oil + load predict, ferrous particles appear, later the envelope at BPFO grows",
                               "rules": ["GBX_HSS_BRG_TEMP", "GBX_FERROUS_PARTICLES", "GBX_HSS_BRG_VIB"], "default_ramp_min": 1.5},
        "planet_gear_pitting": {"name": "Planetary gear tooth pitting", "part": "gearbox",
                                "symptoms": "band at the planetary mesh frequency grows, overall vibration and ferrous particles follow, temperatures normal",
                                "rules": ["GBX_PLANET_MESH_VIB", "GBX_VIB_OVERALL", "GBX_FERROUS_PARTICLES"], "default_ramp_min": 1.5},
        "oil_cooler_fouling": {"name": "Gearbox oil cooler fouled or fan failed", "part": "cooling",
                               "symptoms": "oil hotter than ambient + load predict, the bearing follows the oil (its own residual stays normal)",
                               "rules": ["GBX_OIL_TEMP_RESIDUAL", "GBX_OIL_TEMP_HIGH"], "default_ramp_min": 1},
        "oil_contamination": {"name": "Oil contamination (filter bypass, ingress)", "part": "lubrication",
                              "symptoms": "ISO 4406 codes rise above the target, no ferrous particles, temperatures normal",
                              "rules": ["OIL_CLEANLINESS"], "default_ramp_min": 1},
        "main_bearing_wear": {"name": "Main bearing wear", "part": "main bearing",
                              "symptoms": "main bearing hotter than the model, envelope at the main bearing grows",
                              "rules": ["MB_TEMP_RESIDUAL", "MB_VIB_ENV"], "default_ramp_min": 1.5},
        "yaw_misalignment": {"name": "Yaw misalignment (vane offset or yaw control fault)", "part": "yaw",
                             "symptoms": "10-min mean wind direction off the rotor axis, power below the curve",
                             "rules": ["WTG_YAW_MISALIGNMENT", "WTG_UNDERPERFORMANCE"], "default_ramp_min": 0.5},
        "rotor_performance_loss": {"name": "Rotor performance loss (blade erosion, pitch offset)", "part": "rotor",
                                   "symptoms": "power below the density-corrected curve at partial load, yaw normal",
                                   "rules": ["WTG_UNDERPERFORMANCE"], "default_ramp_min": 1},
    },
    "presentation": {"title": "WTG-3001 wind turbine drivetrain", "dashboard": "WIND_TURBINE_DFIG"},
}

out = HERE / "twin" / "wtg-3001.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
