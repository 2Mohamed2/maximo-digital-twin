"""Write twin/ac-4601.twin.json: the oil-injected rotary screw air compressor twin (AC-4601).

    python build_twin.py

AC-4601 is the base-load compressor of a plant compressed air system: an Atlas Copco GA 90 oil-injected rotary screw
compressor, fixed speed, air-cooled, 125 psi variant, with load/unload control, followed by a refrigerant dryer, line filters,
an air receiver and the plant header.

Sources and assumptions (every number below is either from a published source or labelled as an assumption in "source"):
  Atlas Copco CAGI data sheet "GA90-125 AC" (Rotary Compressor: Fixed Speed, dated 9/20/2023): rated capacity 588.3 acfm
    at a full load operating pressure of 125 psig, maximum full flow operating pressure 132 psig, drive motor 125 hp at
    95.4 %, fan motor 3.0 hp at 89.5 %, package input power at zero flow 20.7 kW, at rated capacity 108.5 kW, specific package
    input power 18.4 kW/100 cfm, isentropic efficiency 81.44 %. Capacity measured to ISO 1217 Annex C.
  US DOE / Compressed Air Challenge, "Improving Compressed Air System Performance: a sourcebook for industry" (3rd edition):
    leak test by load/unload timing, Leakage (%) = T x 100 / (T + t); well maintained systems below 5 to 10 %, poorly
    maintained 20 to 30 %; about 1 % more energy per 2 psi (0.14 bar) more discharge pressure at full flow; separator 2 to 3
    psid when new, change at 10 to 12 psid; sump blow-down when unloading takes about 40 s.
  ISO 8573-1 humidity classes as commonly quoted: class 4 pressure dew point <= +3 C, class 5 <= +7 C.
  Magnus formula for the saturation pressure of water vapour over water (coefficients 6.112 hPa, 17.62, 243.12 C).
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with the values of your own compressor and system"
CFM = 0.0283168                      # m3 per cubic foot
PSI = 0.0689476                      # bar per psi
HP = 0.7457                          # kW per hp

twin = {
    "$comment": "AC-4601 rotary screw air compressor twin. Expected values in Maximo Monitor from the CAGI data sheet and the system design; the controller and meters send only what they measure.",
    "twin": {"id": "AC-4601", "name": "Plant air compressor AC-4601", "version": "1.0.0", "folder": "aircomp-twin"},
    "identification": {
        "asset": "AC-4601", "assetnum": "AC-4601", "manufacturer": "Atlas Copco",
        "model": "GA 90, 125 psi, air-cooled, fixed speed (CAGI data sheet GA90-125 AC)",
        "description": "Base-load plant air compressor: oil-injected rotary screw, load/unload, with refrigerant dryer and receiver",
        "type": "Single-stage oil-injected rotary screw compressor package, fixed speed, load/unload (inlet valve) control",
        "controller": "Compressor controller (Elektronikon on this model): pressures, element outlet temperature, load/unload counters",
        "dryer": "Refrigerant dryer downstream of the compressor (integrated Full Feature dryer or a separate one), electronic condensate drain",
        "storage": "Wet air receiver after the dryer, plus the pipework of the header",
    },
    "design": {
        "cagi": {
            "fad_acfm": 588.3, "full_load_psig": 125.0, "max_full_flow_psig": 132.0,
            "motor_hp": 125.0, "motor_eff": 0.954, "fan_hp": 3.0, "fan_eff": 0.895,
            "p_zero_flow_kw": 20.7, "p_full_kw": 108.5, "spec_kw_100cfm": 18.4, "eta_isen": 0.8144,
            "fad_m3min": round(588.3 * CFM, 4), "full_load_barg": round(125.0 * PSI, 4), "max_full_flow_barg": round(132.0 * PSI, 4),
            "source": "Atlas Copco CAGI data sheet GA90-125 AC (Rotary Compressor: Fixed Speed, 9/20/2023), items 3 to 13. Capacity "
                      "to ISO 1217 Annex C, actual cubic feet per minute at inlet conditions. Metric values converted here "
                      "(1 cfm = 0.0283168 m3/min, 1 psi = 0.0689476 bar).",
        },
        "air": {
            "inlet_ref_bara": 1.0, "k": 1.4, "fad_per_bar": 0.02,
            "source": "Isentropic power of dry air (k = 1.4) from the inlet to the package outlet; with 1.0 bar a inlet it reproduces "
                      "the CAGI full-load power from the CAGI isentropic efficiency. Change of free air delivery with outlet "
                      "pressure, 2 % per bar: " + A + " (use the maker's FAD table for the pressure variants).",
        },
        "control": {
            "load_barg": 7.5, "unload_barg": 8.5, "blowdown_s": 40.0,
            "source": "Loading and unloading pressures in the controller: " + A + ". The unload pressure stays below the CAGI "
                      "maximum full flow pressure (132 psig, 9.10 bar g). Sump blow-down of about 40 s after unloading: DOE "
                      "compressed air sourcebook.",
        },
        "system": {
            "receiver_m3": 10.0, "piping_m3": 2.0, "header_required_barg": 7.0, "system_dp_normal_bar": 0.35,
            "demand_normal_m3min": 11.7,
            "source": "Receiver volume and header pipework, the lowest header pressure the most demanding user needs, the pressure "
                      "drop through dryer and filters at normal flow, and the normal plant demand (free air): " + A + ".",
        },
        "oil": {
            "element_out_normal_c": 82.0, "cooler_approach_k": 38.0, "separator_dp_new_bar": 0.17, "separator_dp_change_bar": 0.7,
            "source": "Element outlet temperature held by the thermostatic valve, approach of the oil cooler with the thermostat "
                      "fully open (element outlet minus inlet air at full load): " + A + ". Separator element: about 2 to 3 psid "
                      "(0.14 to 0.21 bar) when new and change at 10 to 12 psid (0.69 to 0.83 bar), DOE compressed air sourcebook.",
        },
        "dryer": {
            "pdp_normal_c": 4.0, "iso8573_class": 5, "pdp_class_limit_c": 7.0,
            "source": "Plant specification ISO 8573-1 humidity class 5 (pressure dew point <= +7 C, as commonly quoted); refrigerant "
                      "dryer pressure dew point in normal operation: " + A + ".",
        },
        "motor": {
            "voltage_v": 460.0, "power_factor": 0.88, "fla_a": 140.0, "service_factor": 1.15,
            "source": "Motor supply voltage, power factor at load, nameplate full-load current and service factor: " + A
                      + " (read them from the motor nameplate). DOE sourcebook: a screw package at full capacity and full-load "
                      "pressure often runs at about 110 % of motor nameplate, inside a 15 % service factor.",
        },
        "leak": {
            "test_load_normal_pct": 6.0, "test_load_alert_pct": 10.0,
            "source": "Leak test: load share of the compressor when nothing in the plant uses air (weekend or night window), "
                      "recorded by the controller. DOE compressed air sourcebook: below 5 to 10 % in a well maintained system, "
                      "about 20 % in a typical poorly maintained plant. Normal value of this plant: " + A + ".",
        },
        "demo": {"time_scale": 1, "note": "Demo only: the stand-in runs in real time; failure modes ramp in over about a minute so their fingerprints appear quickly."},
    },
    "telemetry": {
        "event": "aircomp", "publish_every_s": 10, "device_type": "SCREW_AIR_COMPRESSOR",
        "groups": {"Air": "Pressures, inlet conditions and flow", "Machine": "Power, current and load/unload (controller, last 15 minutes)",
                   "Oil": "Oil circuit and separator", "Dryer": "Refrigerant dryer", "Leak": "Last no-demand leak test"},
        "points": [
            {"metric": "discharge_pressure_barg", "path": "Air.DischargePressure", "label": "Package outlet pressure, mean of the last 15 min", "unit": "bar g"},
            {"metric": "header_pressure_barg", "path": "Air.HeaderPressure", "label": "Header pressure after dryer, filters and receiver", "unit": "bar g"},
            {"metric": "inlet_pressure_bara", "path": "Air.InletPressure", "label": "Ambient (inlet) pressure", "unit": "bar a"},
            {"metric": "inlet_temp_c", "path": "Air.InletTemperature", "label": "Compressor inlet air temperature", "unit": "°C"},
            {"metric": "inlet_rh_pct", "path": "Air.InletHumidity", "label": "Inlet air relative humidity", "unit": "%"},
            {"metric": "flow_nm3min", "path": "Air.Flow", "label": "Plant flow meter after the dryer (normal m³, 0 °C, 1.01325 bar)", "unit": "Nm³/min"},
            {"metric": "package_power_kw", "path": "Machine.PackagePower", "label": "Package input power, mean of the last 15 min", "unit": "kW"},
            {"metric": "motor_current_a", "path": "Machine.MotorCurrent", "label": "Main motor current while loaded", "unit": "A"},
            {"metric": "load_pct", "path": "Machine.LoadShare", "label": "Share of time loaded, last 15 min", "unit": "%"},
            {"metric": "load_cycles_per_h", "path": "Machine.LoadCycles", "label": "Load/unload cycles per hour, last 15 min", "unit": "1/h"},
            {"metric": "loaded", "path": "Machine.Loaded", "label": "Loaded now (1) or unloaded (0)", "unit": "code"},
            {"metric": "element_outlet_temp_c", "path": "Oil.ElementOutletTemp", "label": "Compressor element outlet temperature", "unit": "°C"},
            {"metric": "separator_dp_bar", "path": "Oil.SeparatorDP", "label": "Oil separator element pressure drop", "unit": "bar"},
            {"metric": "dryer_pdp_c", "path": "Dryer.PressureDewPoint", "label": "Dryer pressure dew point", "unit": "°C"},
            {"metric": "leak_test_load_pct", "path": "Leak.NoDemandLoad", "label": "Load share in the last no-demand leak test", "unit": "%"},
        ],
    },
    "twin_model": {
        "limits": {
            "power_ratio_alert": 1.04, "fad_ratio_alert": 0.90, "spec_power_ratio_alert": 1.25, "system_dp_alert_bar": 0.7,
            "pressure_excess_alert_bar": 1.0, "cycles_alert_per_h": 60.0, "storage_ratio_alert": 0.5,
            "element_temp_alert_c": 100.0, "dew_margin_alert_k": 10.0, "motor_load_alert_pct": 115.0,
            "source": "Alert limits: " + A + ". Separator change point, PDP class limit, leak alert and motor service factor are in "
                      "design.oil, design.dryer, design.leak and design.motor. Set the element temperature alert below the "
                      "controller's own warning and shut-down settings.",
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "leaks_growing": {"name": "Leaks growing in the distribution system", "part": "system",
                          "symptoms": "no-demand leak test load share rises; the compressor runs loaded longer for the same production",
                          "rules": ["AC_LEAK_HIGH"], "default_ramp_min": 1},
        "pressure_setpoint_high": {"name": "Pressure set point raised above need", "part": "control",
                                   "symptoms": "header pressure well above what the users need; power up about 1 % per 0.14 bar",
                                   "rules": ["AC_PRESSURE_EXCESS"], "default_ramp_min": 0.5},
        "separator_clogged": {"name": "Oil separator element clogged", "part": "separator",
                              "symptoms": "separator pressure drop past the change point; power above the CAGI line at the same outlet pressure",
                              "rules": ["AC_SEPARATOR_DP_HIGH", "AC_POWER_HIGH"], "default_ramp_min": 1.5},
        "element_wear": {"name": "Element wear or inlet valve not opening fully", "part": "element",
                         "symptoms": "less free air per loaded minute; load share and specific power up",
                         "rules": ["AC_FAD_LOW", "AC_SPEC_POWER_HIGH"], "default_ramp_min": 1.5},
        "oil_cooler_fouled": {"name": "Oil cooler fouled (dust on the fins)", "part": "cooler",
                              "symptoms": "element outlet temperature climbs above the thermostat setting, worst on hot days",
                              "rules": ["AC_ELEMENT_TEMP_HIGH"], "default_ramp_min": 1},
        "thermostat_stuck_open": {"name": "Thermostatic valve stuck open", "part": "thermostat",
                                  "symptoms": "element outlet runs cold, close to the dew point of the compressed air: water condenses in the oil",
                                  "rules": ["AC_OIL_DEW_MARGIN_LOW"], "default_ramp_min": 1},
        "dryer_fault": {"name": "Dryer fault (refrigerant loss or drain stuck)", "part": "dryer",
                        "symptoms": "pressure dew point above the ISO 8573-1 class of the plant",
                        "rules": ["AC_PDP_HIGH"], "default_ramp_min": 1},
        "receiver_isolated": {"name": "Receiver isolated (valve shut) or full of water", "part": "storage",
                              "symptoms": "load/unload cycles per hour multiply, effective storage collapses, unloaded power never reached",
                              "rules": ["AC_CYCLING_HIGH", "AC_STORAGE_LOW"], "default_ramp_min": 0.5},
    },
    "presentation": {"title": "AC-4601 rotary screw air compressor", "dashboard": "SCREW_AIR_COMPRESSOR"},
}

out = HERE / "twin" / "ac-4601.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
