"""Write twin/st-3201.twin.json: the industrial steam turbine twin (ST-3201).

    python build_twin.py

ST-3201 is a single-casing condensing steam turbine with one controlled extraction, driving a 50 Hz generator directly at
3000 rpm. The frame is the Siemens Energy SST-400 (public envelope: up to 65 MW, live steam up to 140 bar(a) / 540 C, up to
7,100 rpm, condensing exhaust up to 0.5 bar(a), controlled extraction up to 40 bar(a) / 450 C, geared or direct drive to
50 and 60 Hz generators). The design point of THIS unit (100 bar(a) / 500 C, 200 t/h, extraction at 12 bar(a)) is an
ASSUMPTION inside that envelope: replace it with the heat balance diagram and the data sheet of your own turbine.

Sources and assumptions (every number below is either from a public source or labelled as an assumption in "source"):
  Siemens Energy industrial steam turbines page: SST-400 envelope (quoted above).
  IAPWS-IF97 (IAPWS R7-97(2012)): steam enthalpy and P.v; the twin uses short correlations fitted to it by
      tools/fit_steam.py (needs the iapws package; run it once, the coefficients are written below).
  Steam turbine physics (textbook): isentropic enthalpy drop with an isentropic index k, Stodola / first-stage pressure
      proportional to flow, the Willans line (power linear in steam flow), condenser saturation pressure.
  ISO 20816-2 (land-based steam turbines and generators above 40 MW, fluid-film bearings, 1500/1800/3000/3600 r/min):
      bearing housing vibration zone boundaries B/C 7.5 and C/D 11.8 mm/s r.m.s. at 3000 r/min, as commonly quoted from
      its Table A.1: check them against your own copy.
  Efficiencies, first-stage pressure, valve lift, condenser, thrust and vibration values: ASSUMPTIONS of a typical size.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with your OEM heat balance / data sheet"

# Heat balance points (main steam flow t/h, extraction flow t/h, generator output MW) at the rated steam conditions
# (100 bar(a), 500 C, condenser 86 mbar(a)). Written by tools/heat_balance.py from the stand-in model; in a real twin
# these are the points of the OEM heat balance diagrams. The Willans line is fitted to them in twin_calc._k().
HEAT_BALANCE = [[140.0, 20.0, 37.6355], [140.0, 50.0, 32.3129], [140.0, 80.0, 26.9903], [170.0, 20.0, 46.6413], [170.0, 50.0, 41.3687], [170.0, 80.0, 36.0961], [200.0, 20.0, 55.5612], [200.0, 50.0, 50.3053], [200.0, 80.0, 45.0494], [215.0, 20.0, 59.9729], [215.0, 50.0, 54.7128], [215.0, 80.0, 49.4527]]
CORR = {"mw_per_bar_main": -0.0006, "mw_per_k_main": 0.0903, "mw_per_mbar_cond": -0.04066, "cond_exponent": 0.1597}

twin = {
    "$comment": "ST-3201 condensing extraction steam turbine twin. Expected values in Maximo Monitor from the heat balance, the steam property correlations and the design data; the device sends only what it measures.",
    "twin": {"id": "ST-3201", "name": "Steam turbine ST-3201", "version": "1.0.0", "folder": "steamturb-twin"},
    "identification": {
        "asset": "ST-3201", "assetnum": "ST-3201", "manufacturer": "Siemens Energy",
        "model": "SST-400 frame (single casing, condensing with one controlled extraction)",
        "description": "Turbine-generator of a cogeneration plant: process steam extraction at 12 bar(a), condensing exhaust",
        "drive": "Direct drive to a 50 Hz two-pole generator, 3000 rpm",
        "governing": "Nozzle governing: governor (HP control) valves feed the first-stage nozzle groups; extraction control valve to the LP section",
        "condenser": "Water-cooled surface condenser",
    },
    "design": {
        "frame": {"power_max_mw": 65.0, "inlet_bara_max": 140.0, "inlet_c_max": 540.0, "speed_max_rpm": 7100,
                  "exhaust_condensing_bara_max": 0.5, "extraction_controlled_bara_max": 40.0,
                  "source": "Siemens Energy industrial steam turbines page, SST-400 technical data (checked 2026-11)"},
        "rated": {"main_flow_th": 200.0, "main_press_bara": 100.0, "main_temp_c": 500.0, "ext_press_bara": 12.0,
                  "ext_flow_th": 50.0, "cond_press_mbar": 86.0, "speed_rpm": 3000.0, "mech_gen_eff": 0.975,
                  "source": "Design point of this unit, inside the SST-400 envelope: " + A},
        "hp_section": {"eta_rated_pct": 80.0, "eta_curv_pts": 25.0, "wheel_press_rated_bara": 72.0,
                       "source": "HP section (inlet to extraction) isentropic efficiency at rated flow, its fall at part load "
                                 "(eta = eta_rated - curv x (1 - flow/rated)^2, nozzle governing) and the first-stage (wheel chamber) "
                                 "pressure at rated flow: " + A},
        "lp_section": {"eta_rated_pct": 82.0, "k_isentropic": 1.19,
                       "source": "LP section (extraction to condenser) efficiency including wetness losses: " + A
                                 + ". k = 1.19 matches the IAPWS-IF97 isentropic drop from 12 bar(a) / 248 C to 60-150 mbar within 1 % (stand-in only)."},
        "valves": {"gv_lift_rated_pct": 80.0,
                   "source": "Governor valve lift at rated flow; flow through the choked valves taken proportional to lift x P1 / sqrt(T1): " + A},
        "condenser": {"cw_in_c": 28.0, "cw_rise_k": 10.0, "ttd_k": 5.0,
                      "source": "Cooling water inlet temperature, rise at rated LP flow and terminal temperature difference (TTD) of the clean condenser: " + A},
        "mechanical": {"vib_normal_mms": 2.4, "thrust_pos_normal_mm": 0.05, "thrust_pad_normal_c": 72.0,
                       "source": "Normal bearing housing vibration, rotor axial position and thrust pad temperature: " + A},
        "steam_props": {
            "t_ref_k": 600.0,
            "h": {"a0": 1996.72817, "a1": 1.70062946, "a2": 2.95708033e-04, "c1": -1.64999356, "c2": -1.34772194e-02, "n": 2.0, "m": 9.0},
            "pv": {"b0": 0.46088254, "b1": -0.482389, "b2": -0.00270654, "n": 2.5, "m": 9.0},
            "k_hp": 1.286,
            "antoine": {"A": 8.21118462, "B": 1737.94135822, "C": 234.0},
            "source": "Correlations fitted to IAPWS-IF97 (iapws Python package) by tools/fit_steam.py. h(P,T) [kJ/kg] = a0 + a1 T + a2 T^2 + "
                      "c1 (T/600)^-n P + c2 (T/600)^-m P^2, within 5.9 kJ/kg of IF97 from 5 to 125 bar(a) and saturation + 20 K to 560 C; "
                      "P.v [kJ/kg] = b0 T + b1 (T/600)^-n P + b2 (T/600)^-m P^2 within 0.5 %; isentropic drop with k = 1.286 within 0.25 % "
                      "from 60-110 bar(a), 460-520 C to 8-16 bar(a); HP efficiency within -0.2 / +0.7 points of IF97 over the operating range. "
                      "Saturation: log10(p [mbar]) = A - B / (T [C] + C), within 0.03 % from 25 to 70 C.",
        },
        "heat_balance": {"points": HEAT_BALANCE, "corrections": CORR,
                         "source": "Heat balance points (main flow t/h, extraction flow t/h, MW) at rated steam conditions and the correction "
                                   "factors for main steam pressure, temperature and condenser pressure (slope at the rated condenser pressure; "
                                   "the curve flattens as (p/p_r)^x). Here computed from the stand-in model "
                                   "(tools/heat_balance.py): " + A},
        "economics": {"power_price_eur_mwh": 80.0, "source": "Value of one MWh of electricity at the plant: assumption, replace with your own"},
        "demo": {"time_scale": 1, "note": "Demo only: the load and the extraction demand swing slowly with the plant clock; faults ramp in over the default ramp time."},
    },
    "telemetry": {
        "event": "steamturb", "publish_every_s": 10, "device_type": "STEAM_TURBINE_EXTRACTION",
        "groups": {"Steam": "Main steam at the turbine stop valve", "HP": "HP section", "Extraction": "Controlled extraction to process",
                   "Condenser": "Exhaust and condenser", "Generator": "Generator output", "Valves": "Governor and extraction valves",
                   "Rotor": "Speed", "Bearings": "Bearing housing vibration", "Thrust": "Thrust bearing"},
        "points": [
            {"metric": "main_flow_th", "path": "Steam.Flow", "label": "Main steam flow", "unit": "t/h"},
            {"metric": "main_press_bara", "path": "Steam.Pressure", "label": "Main steam pressure", "unit": "bar a"},
            {"metric": "main_temp_c", "path": "Steam.Temperature", "label": "Main steam temperature", "unit": "°C"},
            {"metric": "wheel_press_bara", "path": "HP.WheelChamberPressure", "label": "First-stage (wheel chamber) pressure", "unit": "bar a"},
            {"metric": "ext_press_bara", "path": "Extraction.Pressure", "label": "Extraction pressure", "unit": "bar a"},
            {"metric": "ext_temp_c", "path": "Extraction.Temperature", "label": "Extraction temperature", "unit": "°C"},
            {"metric": "ext_flow_th", "path": "Extraction.Flow", "label": "Extraction flow to process", "unit": "t/h"},
            {"metric": "cond_press_mbar", "path": "Condenser.Pressure", "label": "Condenser (exhaust) pressure", "unit": "mbar a"},
            {"metric": "cw_in_c", "path": "Condenser.CWInlet", "label": "Cooling water inlet temperature", "unit": "°C"},
            {"metric": "cw_out_c", "path": "Condenser.CWOutlet", "label": "Cooling water outlet temperature", "unit": "°C"},
            {"metric": "power_mw", "path": "Generator.Power", "label": "Generator active power", "unit": "MW"},
            {"metric": "gv_lift_pct", "path": "Valves.GovernorLift", "label": "Governor valve lift", "unit": "%"},
            {"metric": "ev_lift_pct", "path": "Valves.ExtractionLift", "label": "Extraction control valve (LP) lift", "unit": "%"},
            {"metric": "speed_rpm", "path": "Rotor.Speed", "label": "Rotor speed", "unit": "rpm"},
            {"metric": "vib_brg1_mms", "path": "Bearings.Vib1", "label": "Bearing 1 (turbine front) housing vibration", "unit": "mm/s"},
            {"metric": "vib_brg2_mms", "path": "Bearings.Vib2", "label": "Bearing 2 (turbine rear) housing vibration", "unit": "mm/s"},
            {"metric": "thrust_pos_mm", "path": "Thrust.Position", "label": "Rotor axial position", "unit": "mm"},
            {"metric": "thrust_pad_c", "path": "Thrust.PadTemp", "label": "Thrust pad temperature (active side)", "unit": "°C"},
        ],
    },
    "twin_model": {
        "limits": {
            "hp_eff_low_pts": -3.0, "hp_eff_very_low_pts": -7.0, "wheel_ratio_high": 1.04, "wheel_ratio_low": 0.97,
            "power_dev_low_pct": -1.5, "cond_press_dev_mbar": 15.0, "ttd_high_k": 9.0, "valve_ratio_low": 0.92,
            "vib_bc_mms": 7.5, "vib_cd_mms": 11.8, "thrust_pos_mm": 0.25, "thrust_pad_c": 95.0,
            "source": "Vibration: ISO 20816-2 zone boundaries at 3000 r/min as commonly quoted (check your copy). Others: " + A,
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "hp_deposits": {"name": "Deposits on the HP blading (silica, salts)", "part": "hp",
                        "symptoms": "first-stage pressure up at the same flow, HP efficiency down, output down",
                        "rules": ["ST_WHEEL_PRESS_HIGH", "ST_HP_EFF_LOW", "ST_POWER_LOW"], "default_ramp_min": 1.5},
        "solid_particle_erosion": {"name": "Solid particle erosion of the first-stage nozzles and HP blades", "part": "hp",
                                   "symptoms": "HP efficiency well down, first-stage pressure down at the same flow, output down",
                                   "rules": ["ST_WHEEL_PRESS_LOW", "ST_HP_EFF_VERY_LOW", "ST_POWER_LOW"], "default_ramp_min": 1.5},
        "lp_blade_damage": {"name": "LP blade erosion or damage (moisture erosion, lost shroud)", "part": "lp",
                            "symptoms": "output down with a healthy HP section and a normal condenser",
                            "rules": ["ST_POWER_LOW"], "default_ramp_min": 1.0},
        "condenser_fouling": {"name": "Condenser fouling or air in-leakage", "part": "condenser",
                              "symptoms": "TTD and condenser pressure up against the cooling water; output down but as expected for that backpressure",
                              "rules": ["ST_COND_PRESS_HIGH", "ST_TTD_HIGH"], "default_ramp_min": 1.0},
        "governor_valve": {"name": "Governor valve deposits or linkage fault", "part": "valves",
                           "symptoms": "more lift needed for the same steam flow",
                           "rules": ["ST_VALVE_CAPACITY_LOW"], "default_ramp_min": 1.0},
        "rotor_unbalance": {"name": "Rotor unbalance or bow (blade loss, rub, uneven deposits)", "part": "rotor",
                            "symptoms": "bearing vibration up into ISO 20816-2 zone C",
                            "rules": ["ST_VIB_ZONE_C"], "default_ramp_min": 1.0},
        "thrust_bearing_wear": {"name": "Thrust bearing wear or overload", "part": "thrust",
                                "symptoms": "rotor moves axially, thrust pad temperature up",
                                "rules": ["ST_THRUST_POS", "ST_THRUST_TEMP"], "default_ramp_min": 1.0},
    },
    "presentation": {"title": "ST-3201 steam turbine", "dashboard": "STEAM_TURBINE_EXTRACTION"},
}

out = HERE / "twin" / "st-3201.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
