"""Write twin/k-2301.twin.json: the process centrifugal compressor twin (K-2301).

    python build_twin.py

K-2301 is a single-section process gas compressor on a refinery unit: a single-shaft, vertically split (barrel) centrifugal
compressor built to API 617, six impellers on one shaft, driven by an electric motor with a variable speed drive (VSD) through
a speed-increasing gearbox. Tandem dry gas seals at both shaft ends, tilting-pad journal and thrust bearings, and
non-contacting proximity probes (API 670) for radial vibration and axial position. An anti-surge controller opens a recycle
valve from discharge back to suction when the operating point comes close to surge.

Sources and assumptions (every number below is either from a published source or labelled as an assumption in "source"):
  Siemens Energy single-shaft centrifugal compressors, product page: vertically split (barrel) casings, volume flow 250 to
    600,000 m3/h, discharge pressure up to 1,000 bar, speed up to 25,000 rpm, up to 10 impellers per casing, built to API 617.
    K-2301 sits well inside that envelope; its own performance map below is an ASSUMPTION of typical shape.
  John Crane Type 28XP dry gas seal, product page: up to 180 bar, 200 m/s, -140 to 315 C, single, double-opposed or tandem.
  ASME PTC 10 (polytropic head and efficiency from measured pressures and temperatures), here in its ideal-gas form with an
    average compressibility factor Z.
  Fan laws (affinity laws) for one compressor at different speeds: Q ~ N, H ~ N^2, P ~ N^3.
  Anti-surge: control line 3 to 10 % of inlet flow to the right of the surge line; recycle valve sized for 1.8 to 2.2 times
    the surge flow (Ghanbariannaeeni and Ghazanfarihashemi, Pipeline & Gas Journal, March 2012).
  API 617 shop-test shaft vibration limit: 25.4 x sqrt(12000 / N) um peak-to-peak, not more than 25.4 um (1 mil).
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with the values of your own machine"

twin = {
    "$comment": "K-2301 process centrifugal compressor twin. Expected values in Maximo Monitor from the compressor map, the gas data and the protection settings; the device sends only what it measures.",
    "twin": {"id": "K-2301", "name": "Process gas compressor K-2301", "version": "1.0.0", "folder": "centcomp-twin"},
    "identification": {
        "asset": "K-2301", "assetnum": "K-2301", "manufacturer": "Siemens Energy (compressor family); map of this twin assumed",
        "model": "Single-shaft centrifugal compressor, vertically split (barrel) casing, API 617",
        "description": "Process gas compressor of a refinery unit, one section, six impellers, motor + VSD + gearbox",
        "casing": "Vertically split (barrel) casing, one section, 6 closed impellers, balance piston",
        "driver": "Induction motor with variable speed drive and speed-increasing gearbox",
        "seals": "Tandem dry gas seals at both ends (for example John Crane Type 28XP), nitrogen separation seals",
        "bearings": "Tilting-pad journal bearings (drive end, non-drive end) and double-acting tilting-pad thrust bearing",
        "protection": "API 670 machinery protection system: X/Y proximity probes at each journal bearing, two axial position probes, bearing RTDs",
        "anti_surge": "Anti-surge controller with recycle valve from discharge (after the cooler) back to suction",
    },
    "design": {
        "gas": {
            "mw_kg_kmol": 22.0, "k": 1.20, "z": 0.98,
            "source": "Light hydrocarbon process gas: molar mass, ratio of specific heats cp/cv and average compressibility over the "
                      "compression, from the process data sheet. " + A + " (use the gas analysis and an equation of state).",
        },
        "map": {
            "speed_rated_rpm": 10500.0, "flow_rated_m3h": 15000.0, "head_rated_kjkg": 160.0, "eta_rated": 0.80,
            "head_c0": 0.76, "head_c1": 1.04, "head_c2": -0.80, "eta_curv": 0.90,
            "surge_x": 0.70, "stonewall_x": 1.25, "impellers": 6,
            "source": "Compressor performance map at rated speed (actual inlet flow, polytropic head, polytropic efficiency), as on "
                      "the vendor's predicted performance curves, fitted as head = H0 (c0 + c1 x + c2 x^2) and efficiency = eta0 "
                      "(1 - curv (x - 1)^2) with x = Q / (Q0 N/N0); surge at x = 0.70, stonewall at x = 1.25. " + A
                      + ". The envelope (flow, speed, impellers) is inside the Siemens Energy barrel compressor range.",
        },
        "process": {
            "suction_bara": 3.5, "suction_temp_c": 40.0, "discharge_bara": 11.9, "flow_normal_m3h": 14000.0,
            "source": "Normal operating point from the process data sheet: suction drum pressure and temperature, discharge header "
                      "pressure, normal actual inlet flow. " + A,
        },
        "flow_element": {
            "c_m2": 0.0458,
            "source": "Suction flow element (venturi or orifice) constant: Q = C sqrt(dp / rho), from the flow element sizing sheet "
                      "(gives 250 mbar at rated flow). " + A,
        },
        "anti_surge": {
            "control_margin_pct": 10.0, "valve_capacity_m3h": 21000.0,
            "source": "Surge control line 10 % of flow to the right of the surge line (published practice: 3 to 10 %); recycle valve "
                      "sized for 2.0 times the surge flow at rated speed (published practice: 1.8 to 2.2 times). Pipeline & Gas Journal, "
                      "March 2012. Values for this machine: " + A,
        },
        "drive": {
            "drive_train_eff": 0.97,
            "source": "Gas power / shaft power at the motor: bearing, seal and gearbox losses. " + A,
        },
        "seals": {
            "vent_flow_normal_nm3h": 1.5, "seal_gas_dp_normal_bar": 1.0,
            "seal_limits_pressure_bar": 180.0, "seal_limits_speed_ms": 200.0,
            "source": "Tandem dry gas seal; Type 28XP limits 180 bar and 200 m/s from the John Crane product page. Normal primary vent "
                      "flow and seal gas differential pressure over the reference (balance line) pressure: " + A
                      + " (use the seal vendor's leakage data and the seal support system data sheet).",
        },
        "bearings": {
            "journal_temp_normal_c": 85.0, "thrust_temp_normal_c": 80.0, "oil_supply_temp_c": 45.0, "oil_supply_bar": 2.5,
            "vib_normal_um": 15.0,
            "source": "Normal bearing metal temperatures, lube oil supply and shaft vibration (peak-to-peak) at rated speed: " + A
                      + " (use the commissioning baseline of your machine).",
        },
        "demo": {"time_scale": 1, "note": "Demo only: the stand-in runs in real time; failure modes ramp in over about a minute so their fingerprints appear quickly."},
    },
    "telemetry": {
        "event": "centcomp", "publish_every_s": 60, "device_type": "CENTRIFUGAL_COMPRESSOR",
        "groups": {"Process": "Suction and discharge conditions", "Machine": "Speed and power", "Surge": "Anti-surge controller and recycle valve",
                   "Seal": "Dry gas seal support system", "Bearing": "Bearings and shaft (API 670 probes)", "Oil": "Lube oil supply"},
        "points": [
            {"metric": "suction_pressure_bara", "path": "Process.SuctionPressure", "label": "Suction pressure", "unit": "bar a"},
            {"metric": "suction_temp_c", "path": "Process.SuctionTemperature", "label": "Suction temperature", "unit": "°C"},
            {"metric": "discharge_pressure_bara", "path": "Process.DischargePressure", "label": "Discharge pressure", "unit": "bar a"},
            {"metric": "discharge_temp_c", "path": "Process.DischargeTemperature", "label": "Discharge temperature", "unit": "°C"},
            {"metric": "flow_dp_mbar", "path": "Process.FlowDP", "label": "Suction flow element differential pressure", "unit": "mbar"},
            {"metric": "speed_rpm", "path": "Machine.Speed", "label": "Compressor shaft speed", "unit": "rpm"},
            {"metric": "driver_power_kw", "path": "Machine.DriverPower", "label": "Motor shaft power (from the VSD)", "unit": "kW"},
            {"metric": "asc_output_pct", "path": "Surge.ControllerOutput", "label": "Anti-surge controller output (valve demand)", "unit": "%"},
            {"metric": "recycle_valve_pct", "path": "Surge.ValvePosition", "label": "Recycle valve position feedback", "unit": "%"},
            {"metric": "seal_gas_dp_bar", "path": "Seal.SealGasDP", "label": "Seal gas supply over reference pressure", "unit": "bar"},
            {"metric": "vent_flow_de_nm3h", "path": "Seal.PrimaryVentDE", "label": "Primary vent flow, drive end", "unit": "Nm³/h"},
            {"metric": "vent_flow_ne_nm3h", "path": "Seal.PrimaryVentNDE", "label": "Primary vent flow, non-drive end", "unit": "Nm³/h"},
            {"metric": "brg_temp_de_c", "path": "Bearing.JournalTempDE", "label": "Journal bearing temperature, drive end", "unit": "°C"},
            {"metric": "brg_temp_ne_c", "path": "Bearing.JournalTempNDE", "label": "Journal bearing temperature, non-drive end", "unit": "°C"},
            {"metric": "thrust_temp_c", "path": "Bearing.ThrustTemp", "label": "Thrust bearing temperature, active side", "unit": "°C"},
            {"metric": "axial_pos_mm", "path": "Bearing.AxialPosition", "label": "Rotor axial position (0 = commissioning)", "unit": "mm"},
            {"metric": "vib_de_um", "path": "Bearing.VibrationDE", "label": "Shaft vibration, drive end (larger of X and Y)", "unit": "µm pp"},
            {"metric": "vib_ne_um", "path": "Bearing.VibrationNDE", "label": "Shaft vibration, non-drive end (larger of X and Y)", "unit": "µm pp"},
            {"metric": "oil_supply_temp_c", "path": "Oil.SupplyTemp", "label": "Lube oil supply temperature", "unit": "°C"},
            {"metric": "oil_supply_bar", "path": "Oil.SupplyPressure", "label": "Lube oil supply pressure", "unit": "bar g"},
        ],
    },
    "twin_model": {
        "limits": {
            "surge_margin_alert_pct": 15.0, "surge_margin_limit_pct": 5.0, "recycle_open_alert_pct": 10.0, "asv_dev_alert_pct": 10.0,
            "eta_dev_alert_pts": -3.0, "head_ratio_alert": 0.95, "power_dev_alert": 0.06,
            "vent_flow_alert_nm3h": 6.0, "seal_gas_dp_alert_bar": 0.5,
            "journal_temp_alert_c": 105.0, "thrust_temp_alert_c": 110.0, "axial_alert_mm": 0.30, "vib_alert_um": 50.0,
            "source": "Alarm set points: " + A + " (copy them from the anti-surge controller, the API 670 monitor and the seal panel)",
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "impeller_fouling": {"name": "Impeller and diffuser fouling", "part": "aero",
                             "symptoms": "polytropic efficiency and head below the map at the same reduced flow; speed and power up to hold the discharge pressure",
                             "rules": ["CC_EFFICIENCY_LOW", "CC_HEAD_LOW"], "default_ramp_min": 1.5},
        "surge_approach": {"name": "Turndown towards surge (low process flow)", "part": "process",
                           "symptoms": "process flow falls, the anti-surge controller holds the control line by recycling gas",
                           "rules": ["CC_SURGE_CONTROL_LINE", "CC_RECYCLE_OPEN"], "default_ramp_min": 1},
        "asv_stuck": {"name": "Anti-surge valve stuck closed during a turndown", "part": "anti-surge",
                      "symptoms": "controller asks the valve to open, position stays shut, surge margin collapses",
                      "rules": ["CC_ASV_DEVIATION", "CC_SURGE_MARGIN_LOW"], "default_ramp_min": 1},
        "seal_primary_wear": {"name": "Dry gas seal primary ring wear (drive end)", "part": "seal",
                              "symptoms": "primary vent flow of one seal rises, the other end unchanged",
                              "rules": ["CC_SEAL_VENT_HIGH"], "default_ramp_min": 1.5},
        "seal_gas_supply": {"name": "Seal gas supply low (filter blocked or booster failed)", "part": "seal",
                            "symptoms": "seal gas pressure over the reference falls: unfiltered process gas can reach the seal faces",
                            "rules": ["CC_SEAL_GAS_DP_LOW"], "default_ramp_min": 1},
        "thrust_overload": {"name": "Thrust overload (balance piston labyrinth wear)", "part": "bearing",
                            "symptoms": "thrust bearing temperature up, rotor moves towards the active thrust pads",
                            "rules": ["CC_THRUST_TEMP_HIGH", "CC_AXIAL_POSITION"], "default_ramp_min": 1.5},
        "rotor_unbalance": {"name": "Rotor unbalance (deposits shed from an impeller)", "part": "rotor",
                            "symptoms": "shaft vibration up at running speed, temperatures normal", "rules": ["CC_VIBRATION_HIGH"], "default_ramp_min": 0.5},
        "discharge_tt_drift": {"name": "Discharge temperature transmitter drift", "part": "instrument",
                               "symptoms": "efficiency looks low but the motor power does not agree with the gas power",
                               "rules": ["CC_EFFICIENCY_LOW", "CC_POWER_MISMATCH"], "default_ramp_min": 1},
    },
    "presentation": {"title": "K-2301 process centrifugal compressor", "dashboard": "CENTRIFUGAL_COMPRESSOR"},
}

out = HERE / "twin" / "k-2301.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
