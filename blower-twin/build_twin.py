"""Build twin/blw-1301.twin.json: aeration blower BLW-1301 (Aerzen AT 150-0.8 S-G5 turbo blower) feeding Sanitaire
Silver Series II membrane disc diffusers in one activated-sludge basin, DO-controlled.

Sources (copies in _check/src, kept out of git):
  Aerzen catalogue, AT 150-0.8 S-G5 "The New Generation 5 Turbo Blower Unit":
    https://catalog.aerzen.com/item/blowers-compressors-spare-parts/turbo-blowers/at-150-0-8-s-g5
    volume flow 4800 m3/h, max operating pressure 800 mbar, motor power 150 hp, weight 650 kg,
    1855 x 1435 x 1501 mm (L x W x H), discharge port 10" ANSI, noise up to 80 dB; G5 range 4,000-13,200 m3/h,
    frequency-controlled and oil-free
  Xylem / Sanitaire "Aeration products" brochure (460 master AU, 03-2020):
    https://prod.xylem.com/siteassets/brand/sanitaire/resources/brochure/460_master-au_update_03-2020.pdf
    Silver Series II: EPDM, 178 or 229 mm, airflow 0.8-7 Nm3/h per disc, SOTE approx. 6.5 % per m of submergence,
    SAE 2.5-6 kg O2/kWh; service life 10 years or more; coarse-bubble wide-band diffusers SOTE 1.6-2.5 % per m
  Oxygen transfer form (alpha, F, beta, theta, Cs at depth): ASCE/EWRI 2-06 and US EPA Fine Pore Aeration design
    manual (EPA/625/1-89/023), standard textbook form; Cs(T) polynomial APHA / Benson-Krause. Not reproduced here.
Assumptions (not published for this unit): blower map shape (shut-off 1050 mbar, surge line through 2100 Nm3/h at
800 mbar), wire-to-air efficiency curve (74 % peak), turndown to 1900 Nm3/h, diffuser DWP, alpha F 0.55, the basin
and its influent, alarm limits (typical values).
"""
import json
from pathlib import Path

HERE = Path(__file__).parent


def P(metric, path, label, unit, rng, noise, opc=None):
    return {"metric": metric, "path": path, "label": label, "unit": unit, "range": rng, "noise": noise, "opc": opc}


points = [
    P("ambient_pressure_mbar", "Site.AmbientPressure", "Ambient pressure", "mbar(a)", [900, 1100], 0.3),
    P("inlet_temp_c", "Blower.InletTemp", "Blower inlet air temperature", "degC", [-20, 60], 0.05),
    P("inlet_filter_dp_mbar", "Blower.InletFilterDp", "Inlet filter differential pressure", "mbar", [0, 100], 0.1),
    P("discharge_pressure_mbar", "Blower.DischargePressure", "Blower discharge pressure", "mbar(g)", [0, 1100], 0.8, "Aerzen AERtronic: discharge pressure"),
    P("discharge_temp_c", "Blower.DischargeTemp", "Blower discharge temperature", "degC", [-20, 160], 0.2),
    P("airflow_nm3h", "Header.Airflow", "Airflow to the basin (thermal mass flow meter)", "Nm3/h", [0, 6000], 6.0),
    P("airflow_setpoint_nm3h", "Control.AirflowSetpoint", "Airflow setpoint (DO controller)", "Nm3/h", [0, 6000], 0),
    P("grid_pressure_mbar", "Basin.GridPressure", "Diffuser grid pressure (drop leg)", "mbar(g)", [0, 1100], 0.8),
    P("speed_pct", "Blower.Speed", "Blower speed (VFD)", "%", [0, 110], 0.1),
    P("motor_power_kw", "Blower.MotorPower", "Motor power (VFD input)", "kW", [0, 200], 0.15),
    P("motor_current_a", "Blower.MotorCurrent", "Motor current", "A", [0, 400], 0.3),
    P("motor_temp_c", "Blower.MotorWindingTemp", "Motor winding temperature", "degC", [-20, 200], 0.2),
    P("vfd_temp_c", "Blower.VfdTemp", "VFD heat-sink temperature", "degC", [-20, 120], 0.2),
    P("bearing_temp_c", "Blower.BearingTemp", "Bearing temperature", "degC", [-20, 160], 0.2),
    P("vibration_mm_s", "Blower.Vibration", "Blower vibration (velocity rms)", "mm/s", [0, 30], 0.03),
    P("do_control_mgl", "Basin.DOControl", "Dissolved oxygen, control probe (mid-basin)", "mg/L", [0, 20], 0.03, "haystack: dissolved oxygen sensor"),
    P("do_outlet_mgl", "Basin.DOOutlet", "Dissolved oxygen, outlet probe", "mg/L", [0, 20], 0.03),
    P("do_setpoint_mgl", "Control.DOSetpoint", "DO setpoint", "mg/L", [0, 10], 0),
    P("water_temp_c", "Basin.WaterTemp", "Mixed-liquor temperature", "degC", [0, 40], 0.03),
    P("influent_flow_m3h", "Influent.Flow", "Influent flow to this train", "m3/h", [0, 2000], 1.5),
    P("influent_nh4_mgl", "Influent.NH4", "Influent ammonium (online analyzer)", "mg/L", [0, 100], 0.2),
    P("run_hours", "Blower.RunHours", "Blower running hours", "h", [0, 1e6], 0),
    P("trip_code", "Blower.TripCode", "Trip (0 none, 1 surge, 2 VFD over-temperature)", "code", [0, 9], 0),
]

failure_modes = {
    "diffuser_fouling": {"label": "Diffuser fouling (biofilm / scale)", "cause": "Biofilm and scale on the EPDM membranes: higher dynamic wet pressure and fewer, larger bubbles (lower alpha F)",
                         "detect": ["grid_pressure_residual_mbar", "air_ratio", "specific_energy_kwh_kg"], "action": "Bump/flex the membranes (air bump) or acid-clean the grid; plan membrane replacement", "default_ramp_min": 15},
    "membrane_tear": {"label": "Torn membrane / broken grid pipe", "cause": "A split membrane or a cracked pipe lets air out as coarse bubbles: lower grid pressure, much less oxygen transfer, uneven DO",
                      "detect": ["grid_pressure_residual_mbar", "air_ratio", "do_spread_mgl"], "action": "Drain the zone, inspect the grid, replace torn discs / repair the pipe", "default_ramp_min": 10},
    "inlet_filter": {"label": "Inlet filter clogging", "cause": "Dust and pollen load the inlet filter mats: the blower sucks at lower pressure and uses more power",
                     "detect": ["inlet_filter_dp_mbar", "power_residual_pct"], "action": "Change the inlet filter mats", "default_ramp_min": 15},
    "bearing_wear": {"label": "Bearing / impeller wear", "cause": "Worn bearing or eroded impeller: more vibration, a hotter bearing and lower wire-to-air efficiency",
                     "detect": ["vibration_mm_s", "bearing_temp_c", "power_residual_pct"], "action": "Vibration analysis; service the bearing and impeller (Aerzen service)", "default_ramp_min": 15},
    "surge_approach": {"label": "Zone valve stuck part-closed (surge risk)", "cause": "A zone air valve sticks part-closed: the header loses more pressure and the blower runs closer to its surge line, especially at night",
                       "detect": ["header_loss_residual_mbar", "surge_margin_pct", "discharge_pressure_mbar"], "action": "Free the zone valve and check its actuator; review the most-open-valve logic", "default_ramp_min": 10},
    "do_probe_drift": {"label": "DO probe reads high", "cause": "A fouled or drifting control DO probe reads high: the controller gives too little air and the basin under-aerates",
                       "detect": ["do_spread_mgl", "grid_pressure_residual_mbar", "do_outlet_mgl"], "action": "Clean and calibrate the DO probe (luminescent cap check)", "default_ramp_min": 10},
    "vfd_overheating": {"label": "VFD cooling fault", "cause": "The VFD cabinet fan fails or its filter blocks: heat-sink and motor temperatures climb towards trip",
                        "detect": ["vfd_temp_c", "motor_temp_c"], "action": "Replace the cabinet fan / filter mats; check the room ventilation", "default_ramp_min": 15},
}

twin = {
    "$comment": "Single source of truth for the BLW-1301 digital twin: Aerzen AT 150-0.8 S-G5 turbo blower aerating one activated-sludge "
                "basin through Sanitaire Silver Series II membrane discs under DO control. Blower data from the Aerzen catalogue, "
                "diffuser data from the Sanitaire brochure; map shape, efficiency curve, basin and limits are assumptions (labelled).",
    "twin": {"id": "urn:maximo:twin:aerationblower:BLW-1301", "version": "1.0.0",
             "kind": "Turbo aeration blower with fine-bubble diffused aeration and DO control",
             "standards": {
                 "performance": "Aerzen AT 150-0.8 S-G5: 4800 m3/h, 800 mbar max, 150 hp, 650 kg (Aerzen catalogue)",
                 "diffusers": "Sanitaire Silver Series II EPDM discs: 0.8-7 Nm3/h per disc, SOTE approx. 6.5 % per m (Xylem brochure 03-2020)",
                 "oxygen_transfer": "AOTR = SOTR alpha F (beta Cs*(T) - C)/Cs*(20) theta^(T-20) (ASCE 2-06 / EPA fine pore manual form)",
                 "power": "Adiabatic compression power / wire-to-air efficiency (efficiency curve assumed)",
                 "information_model": "Points named after the blower controller signals with Project Haystack tags"}},
    "identification": {"assetnum": "BLW-1301", "description": "Aeration blower 1301 (activated sludge train 1)",
                       "manufacturer": "Aerzen", "model": "AT 150-0.8 S-G5 turbo blower",
                       "site": "BEDFORD", "location": "Wastewater treatment works / blower building / aeration train 1",
                       "medium": "Air to fine-bubble membrane diffusers"},
    "design": {
        "blower": {"type": "Turbo blower, oil-free, frequency-controlled (Generation 5)", "flow_max_nm3h": 4800, "pressure_max_mbar": 800,
                   "motor_hp": 150, "motor_kw": 112, "weight_kg": 650, "dimensions_mm": [1855, 1435, 1501],
                   "flow_min_nm3h": 1900, "turndown_note": "turndown to about 40 % assumed",
                   "dp_shutoff_mbar": 1050, "map_note": "dp = dp_shutoff n^2 - (dp_shutoff - 800) (Q/4800)^2, assumed map shape",
                   "eta_wire_bep": 0.74, "flow_bep_frac": 0.75, "eta_wire_curv": 0.6, "eta_note": "wire-to-air efficiency curve assumed",
                   "filter_dp_clean_mbar": 9, "vfd_trip_c": 85},
        "surge": {"q_sref_nm3h": 2100, "dp_sref_mbar": 800, "note": "surge line Q_s = 2100 sqrt(dp/800) Nm3/h, assumed"},
        "grid": {"diffuser": "Sanitaire Silver Series II, 229 mm EPDM disc", "discs": 1200, "submergence_m": 4.5,
                 "flow_per_disc_range_nm3h": [0.8, 7.0], "dwp0_mbar": 25, "dwp1_mbar_per_nm3h": 4, "dwp_note": "dynamic wet pressure assumed",
                 "k_grid_mbar": 10, "k_pipe_mbar": 25, "pipe_note": "losses at 4800 Nm3/h, assumed"},
        "oxygen": {"sote_per_m": 0.065, "q_ref_nm3h": 3.0, "sote_exp": 0.15, "sote_coarse_per_m": 0.02,
                   "alpha_f_design": 0.55, "beta": 0.95, "theta": 1.024, "d_eff_frac": 0.4,
                   "note": "SOTE 6.5 %/m from Sanitaire; flux exponent, alpha F, beta, d_eff typical values (assumed)"},
        "process": {"basin_volume_m3": 3500, "inflow_base_m3h": 330, "inflow_am_m3h": 160, "inflow_pm_m3h": 110,
                    "nh4_base_mgl": 28, "nh4_peak_mgl": 9, "carbon_o2_kg_m3": 0.13, "nitrified_frac": 0.85, "water_temp_c": 22,
                    "note": "one aeration train; oxygen demand = Q_in (0.13 + 4.57 x 0.85 NH4/1000) kg/h, assumed"},
        "control": {"do_setpoint_mgl": 2.0, "kp_nm3h_per_mgl": 600, "ki_nm3h_per_mgl_h": 1800},
        "site": {"ambient_pressure_mbar": 1008, "air_temp_mean_c": 24, "air_temp_swing_c": 6},
        "demo": {"time_scale": 60, "note": "plant clock runs 60x real time: one plant day = 24 min"},
    },
    "telemetry": {"event": "blower", "publish_every_s": 5, "device_type": "AERATION_BLOWER",
                  "groups": {"Site": "Site", "Blower": "Turbo blower", "Header": "Air header", "Basin": "Aeration basin",
                             "Control": "DO control", "Influent": "Influent analyzers"},
                  "points": points},
    "twin_model": {"limits": {"running_flow_nm3h": 500, "grid_residual_high_mbar": 25, "grid_residual_low_mbar": -15, "air_ratio_high": 1.15, "air_ratio_alarm": 1.35,
                              "filter_dp_alert_mbar": 25, "filter_dp_high_mbar": 40, "surge_margin_alert_pct": 10,
                              "header_residual_alert_mbar": 60, "vibration_alert_mm_s": 4.5, "bearing_temp_alert_c": 95,
                              "power_residual_alert_pct": 8, "do_spread_alert_mgl": 0.9, "do_low_alert_mgl": 0.8,
                              "vfd_temp_alert_c": 62, "motor_temp_alert_c": 135,
                              "note": "typical alarm values, not Aerzen settings"}},
    "failure_modes": failure_modes,
    "presentation": {
        "category": "Aeration blower",
        "kpis": [{"metric": "airflow_nm3h", "label": "Airflow", "unit": "Nm³/h", "decimals": 0},
                 {"metric": "discharge_pressure_mbar", "label": "Discharge", "unit": "mbar", "decimals": 0},
                 {"metric": "do_control_mgl", "label": "DO", "unit": "mg/L", "decimals": 2},
                 {"metric": "motor_power_kw", "label": "Power", "unit": "kW", "decimals": 1}],
        "twin_kpis": [{"metric": "air_ratio", "label": "Air vs. twin", "unit": "x", "decimals": 2},
                      {"metric": "specific_energy_kwh_kg", "label": "Energy", "unit": "kWh/kg O2", "decimals": 2}],
        "compare": [
            {"label": "Grid pressure", "measured": "grid_pressure_mbar", "expected": "grid_pressure_expected_mbar", "unit": "mbar", "decimals": 0,
             "basis": "4.5 m submergence + clean-disc DWP + grid loss"},
            {"label": "Airflow", "measured": "airflow_nm3h", "expected": "airflow_expected_nm3h", "unit": "Nm³/h", "decimals": 0,
             "basis": "Oxygen demand / (SOTE 6.5 %/m x alpha F 0.55 x driving force)"},
            {"label": "Motor power", "measured": "motor_power_kw", "expected": "power_expected_kw", "unit": "kW", "decimals": 1,
             "basis": "Adiabatic power / wire-to-air efficiency"},
            {"label": "Specific energy", "measured": "specific_energy_kwh_kg", "expected": "specific_energy_expected_kwh_kg", "unit": "kWh/kg O2", "decimals": 2,
             "basis": "kW per kg O2 of demand"},
            {"label": "Surge margin", "measured": "surge_margin_pct", "expected": None, "unit": "%", "decimals": 0, "basis": "alert < 10 %"},
            {"label": "Header loss", "measured": "header_loss_mbar", "expected": None, "unit": "mbar", "decimals": 0, "basis": "discharge - grid"},
            {"label": "DO spread (control - outlet)", "measured": "do_spread_mgl", "expected": None, "unit": "mg/L", "decimals": 2, "basis": "about 0.4 mg/L normally"},
        ],
        "trends": [{"metric": "grid_pressure_residual_mbar", "label": "Grid pressure vs. clean"}, {"metric": "air_ratio", "label": "Air ratio"},
                   {"metric": "power_residual_pct", "label": "Power vs. expected %"}, {"metric": "surge_margin_pct", "label": "Surge margin %"}],
        "design": [
            {"label": "Blower", "value": "Aerzen AT 150-0.8 S-G5 turbo, 4800 m³/h, 800 mbar max, 150 hp, oil-free, VFD"},
            {"label": "Diffusers", "value": "1200 Sanitaire Silver Series II 229 mm EPDM discs at 4.5 m submergence"},
            {"label": "Basin", "value": "3500 m³ activated-sludge train, DO setpoint 2.0 mg/L (assumed)"},
            {"label": "Source", "value": "Aerzen catalogue AT 150-0.8 S-G5; Xylem/Sanitaire aeration brochure 03-2020"},
        ],
    },
}

if __name__ == "__main__":
    json.dump(twin, open(HERE / "twin" / "blw-1301.twin.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("written", HERE / "twin" / "blw-1301.twin.json")
