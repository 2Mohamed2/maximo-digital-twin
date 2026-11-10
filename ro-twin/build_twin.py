"""Build twin/ro-1201.twin.json: a seawater reverse osmosis (SWRO) train with DuPont FilmTec SW30HRLE-440i elements
and Energy Recovery PX Q300 isobaric energy recovery devices.

Sources (public, read 2026-11-10):
  DuPont (Dow) FilmTec SW30HRLE-440i product information, Form No. 609-03001-1009
    https://assets.freshwatersystems.com/images/zzqghmufhrkoz2lqxdev/sw30hrle-440i-spec.pdf
    product page https://www.dupont.com/products/filmtecsw30hrle440i.html
    active area 440 ft2 (41 m2); max operating pressure 83 bar; permeate 31 m3/d; stabilised salt rejection 99.80 %,
    minimum 99.65 %; boron 92 %; test 32,000 mg/L NaCl, 55.2 bar (800 psi), 25 C, pH 8, 8 % recovery; permeate flow of an
    element +/-15 %; feed spacer 28 mil; element 1,016 mm net length (iLEC), 201 mm OD, 29 mm permeate tube ID, 8-inch
    vessel; max element dP 1.0 bar, max vessel dP 3.4 bar; max 45 C; pH 2-11 continuous, 1-13 cleaning; SDI <= 5;
    free chlorine < 0.1 mg/L.
  Energy Recovery PX Q Series brochure (Nov 2024) and 2024 Water Products Catalog
    https://energyrecovery.com/wp-content/uploads/2023/11/Q-Series_Product-Brochure.pdf
    https://energyrecovery.com/wp-content/uploads/2023/11/Energy-Recovery-2024-Water-Products-Catalog.pdf
    PX Q series: peak efficiency up to 98 %, up to 83 bar, concentrate flow 4.5-90.9 m3/h, PX Q400 < 3 % volumetric
    mixing, 30-year design life, 99.8 % uptime. The flow range of the PX Q300 (~50-71 m3/h) is read off the brochure's
    bar chart (approximate).
  Normalisation and cleaning criteria: ASTM D4516 "Standard Practice for Standardizing Reverse Osmosis Performance Data"
    (catalogue page https://standards.iteh.ai/catalog/standards/astm/898d2b2a-45cd-407c-acd0-c51230dacb32/astm-d4516-00 ;
    the standard itself is paywalled, not read) and Water Technology "Membrane cleaning fundamentals"
    https://www.watertechonline.com/home/article/14171304/membrane-cleaning-fundamentals-cleaning-criteria-and-normalization-of-reverse-osmosis-systems
    (clean when normalised permeate flow falls 10-15 %, normalised salt passage rises 5-10 %, normalised dP rises 15 %).
  TCF exp(2640 (1/298 - 1/T)) is the FilmTec membrane temperature correction for T >= 25 C (FilmTec technical manual,
    https://www.lenntech.com/data-sheets/filmtec-system-design-l.pdf, not re-read: unverified). Osmotic pressure
    0.79 bar per 1,000 mg/L is the usual seawater rule of thumb (simplification; real seawater is ~0.7-0.8).
Assumptions (not published for one product, labelled in the twin): train size (40 x 7 elements, 160 m3/h, 43 %
  recovery), seawater 38,500 mg/L / 27 C, element dP law, HP pump and booster efficiencies, PX lubrication 1 % and
  mixing 2 %, cartridge filter dP, the sensor set and tag numbers.
"""
import json
import statistics
from pathlib import Path

import physics
import twin_calc

HERE = Path(__file__).parent

KDP = 0.0060                     # element dP = k Qavg^1.5: 0.35 bar at 15 m3/h average flow (assumed, inside the 1.0 bar limit)
TEST = {"permeate_m3d": 31.0, "recovery": 0.08, "nacl_mgl": 32000.0, "rejection": 0.998, "pressure_bar": 55.16, "temp_c": 25.0, "kdp": KDP}
A, B = physics.fit_ab(TEST)


def P(metric, path, label, unit, rng, noise, opc=None):
    return {"metric": metric, "path": path, "label": label, "unit": unit, "range": rng, "noise": noise, "opc": opc}


def tag(t):
    return f"OPC UA ns=2;s=RO1201.{t}.PV"


points = [
    P("feed_flow_m3h", "Intake.FeedFlow", "Seawater feed flow (after cartridge filters)", "m3/h", [0, 600], 0.6, tag("FIT-1201")),
    P("feed_tds_mgl", "Intake.FeedTDS", "Seawater salinity (conductivity as TDS)", "mg/L", [0, 60000], 15, tag("AIT-1201")),
    P("feed_temp_c", "Intake.FeedTemperature", "Seawater temperature", "degC", [0, 50], 0.03, tag("TIT-1201")),
    P("feed_ph", "Intake.FeedPH", "Feed pH", "pH", [0, 14], 0.005, tag("AIT-1202")),
    P("feed_orp_mv", "Intake.FeedORP", "Feed ORP (oxidant after dechlorination)", "mV", [-500, 1000], 1.5, tag("AIT-1203")),
    P("cf_inlet_pressure_bar", "Cartridge.InletPressure", "Cartridge filter inlet pressure", "bar(g)", [0, 10], 0.005, tag("PIT-1201")),
    P("cf_dp_bar", "Cartridge.DifferentialPressure", "Cartridge filter differential pressure", "bar", [0, 5], 0.004, tag("PDIT-1201")),
    P("hp_suction_pressure_bar", "HPPump.SuctionPressure", "HP pump suction pressure", "bar(g)", [-1, 10], 0.005, tag("PIT-1202")),
    P("hp_discharge_pressure_bar", "HPPump.DischargePressure", "HP pump discharge pressure", "bar(g)", [0, 100], 0.03, tag("PIT-1203")),
    P("hp_flow_m3h", "HPPump.Flow", "HP pump flow", "m3/h", [0, 400], 0.25, tag("FIT-1203")),
    P("hp_power_kw", "HPPump.Power", "HP pump motor power (VFD)", "kW", [0, 800], 0.4, tag("JIT-1203")),
    P("hp_speed_pct", "HPPump.Speed", "HP pump speed (VFD)", "%", [0, 110], 0.05, tag("SIT-1203")),
    P("px_hp_out_pressure_bar", "ERD.HPOutletPressure", "PX high-pressure outlet (to booster)", "bar(g)", [0, 100], 0.03, tag("PIT-1205")),
    P("px_lp_in_pressure_bar", "ERD.LPInletPressure", "PX low-pressure inlet (seawater)", "bar(g)", [-1, 10], 0.005, tag("PIT-1204")),
    P("px_lp_out_pressure_bar", "ERD.LPOutletPressure", "PX low-pressure outlet (brine to outfall)", "bar(g)", [-1, 10], 0.005, tag("PIT-1206")),
    P("px_hp_out_flow_m3h", "ERD.HPOutletFlow", "PX high-pressure outlet flow", "m3/h", [0, 400], 0.25, tag("FIT-1205")),
    P("px_lp_in_flow_m3h", "ERD.LPInletFlow", "PX low-pressure inlet flow", "m3/h", [0, 400], 0.25, tag("FIT-1204")),
    P("px_lp_out_flow_m3h", "ERD.LPOutletFlow", "PX low-pressure outlet flow (brine reject)", "m3/h", [0, 400], 0.25, tag("FIT-1206")),
    P("booster_power_kw", "ERD.BoosterPower", "Booster (circulation) pump power", "kW", [0, 200], 0.08, tag("JIT-1205")),
    P("membrane_feed_pressure_bar", "Membranes.FeedPressure", "Membrane feed pressure (vessel inlet header)", "bar(g)", [0, 100], 0.03, tag("PIT-1207")),
    P("membrane_feed_tds_mgl", "Membranes.FeedTDS", "Membrane feed salinity (after PX mixing)", "mg/L", [0, 80000], 15, tag("AIT-1207")),
    P("vessel_dp_bar", "Membranes.DifferentialPressure", "Pressure vessel differential pressure (feed to concentrate header)", "bar", [0, 6], 0.004, tag("PDIT-1207")),
    P("concentrate_pressure_bar", "Membranes.ConcentratePressure", "Concentrate pressure (vessel outlet header)", "bar(g)", [0, 100], 0.03, tag("PIT-1208")),
    P("concentrate_flow_m3h", "Membranes.ConcentrateFlow", "Concentrate flow", "m3/h", [0, 400], 0.25, tag("FIT-1208")),
    P("concentrate_tds_mgl", "Membranes.ConcentrateTDS", "Concentrate salinity", "mg/L", [0, 120000], 25, tag("AIT-1208")),
    P("permeate_pressure_bar", "Permeate.Pressure", "Permeate back pressure", "bar(g)", [-1, 10], 0.003, tag("PIT-1209")),
    P("permeate_flow_m3h", "Permeate.Flow", "Permeate flow", "m3/h", [0, 300], 0.15, tag("FIT-1209")),
    P("permeate_tds_mgl", "Permeate.TDS", "Permeate salinity (train)", "mg/L", [0, 5000], 0.6, tag("AIT-1209")),
    P("bank1_permeate_tds_mgl", "Permeate.Bank1TDS", "Permeate salinity, bank 1 (vessels 1-10)", "mg/L", [0, 5000], 0.6, tag("AIT-1211")),
    P("bank2_permeate_tds_mgl", "Permeate.Bank2TDS", "Permeate salinity, bank 2 (vessels 11-20)", "mg/L", [0, 5000], 0.6, tag("AIT-1212")),
    P("bank3_permeate_tds_mgl", "Permeate.Bank3TDS", "Permeate salinity, bank 3 (vessels 21-30)", "mg/L", [0, 5000], 0.6, tag("AIT-1213")),
    P("bank4_permeate_tds_mgl", "Permeate.Bank4TDS", "Permeate salinity, bank 4 (vessels 31-40)", "mg/L", [0, 5000], 0.6, tag("AIT-1214")),
]

failure_modes = {
    "biofouling": {"label": "Biofouling (lead elements)", "cause": "Biofilm grows in the feed spacer of the first elements: the feed-concentrate pressure drop climbs first, permeate flow follows",
                   "detect": ["ndp_norm_pct", "npf_pct", "membrane_feed_pressure_bar"], "action": "Clean in place (high-pH clean first); review chlorination/dechlorination and the pretreatment SDI", "default_ramp_min": 3},
    "scaling": {"label": "Scaling (tail elements)", "cause": "Sparingly soluble salts (CaCO3, CaSO4) precipitate where the brine is most concentrated: permeate flow falls and salt passage rises at the tail, pressure drop barely moves",
                "detect": ["npf_pct", "nsp_pct", "ndp_norm_pct"], "action": "Clean in place (low-pH clean); check the antiscalant dose and the recovery", "default_ramp_min": 3},
    "oxidation": {"label": "Membrane oxidation (chlorine breakthrough)", "cause": "Dechlorination (SBS) fails and free chlorine reaches the polyamide: ORP jumps, then flow and salt passage both rise for good",
                  "detect": ["feed_orp_mv", "nsp_pct", "npf_pct"], "action": "Stop the train, restore SBS dosing; autopsy one element; damaged elements must be replaced", "default_ramp_min": 2},
    "oring_leak": {"label": "O-ring / interconnector leak (bank 3)", "cause": "A rolled or cut interconnector O-ring lets feed into the permeate tube of one vessel: the permeate of that bank turns salty while the train flow is normal",
                   "detect": ["bank_tds_ratio", "bank3_permeate_tds_mgl", "permeate_tds_mgl"], "action": "Probe the vessels of bank 3 (permeate conductivity profile), replace the O-rings / interconnector", "default_ramp_min": 2},
    "hp_pump_wear": {"label": "HP pump wear", "cause": "Impeller and wear-ring wear in the multi-stage HP pump: the same head and flow take more power",
                     "detect": ["hp_pump_eff_dev_pts", "hp_power_kw", "sec_kwh_m3"], "action": "Plan an overhaul: wear rings, impellers, balance drum; check the vibration trend", "default_ramp_min": 3},
    "erd_leakage": {"label": "Energy recovery device leakage / mixing", "cause": "Worn PX rotor or seals: more lubrication flow goes to the brine, more brine mixes into the membrane feed, the booster works harder",
                    "detect": ["px_eff_pct", "px_leakage_pct", "px_mixing_pct"], "action": "Check PX flow balance and lubrication flow; inspect the rotor and sleeve of the worst unit", "default_ramp_min": 3},
    "cartridge_clogging": {"label": "Cartridge filter clogging", "cause": "Solids from the pretreatment load the 5-micron cartridges: the filter dP rises and the HP pump and PX suction pressure fall",
                           "detect": ["cf_dp_bar", "hp_suction_pressure_bar"], "action": "Change the cartridges; look upstream for media filter or coagulation upsets", "default_ramp_min": 3},
    "feed_temperature": {"label": "Warm intake (not a fault)", "cause": "The seawater warms 7 C (season, outfall recirculation): the membranes pass more water and more salt, so feed pressure falls and permeate salinity rises. The normalised values stay flat, so the twin raises no alarm",
                         "detect": ["feed_temp_c", "tcf", "npf_pct", "nsp_pct"], "action": "None: normalisation separates temperature from membrane condition", "default_ramp_min": 3},
}

design = {
    "seawater": {"tds_mgl": 38500.0, "temp_c": 27.0, "temp_swing_c": 1.2, "tds_swing_mgl": 300.0, "orp_mv": 220.0,
                 "assumed": "open intake after dual-media filtration and SBS dechlorination; values assumed"},
    "membrane": {"element": "DuPont FilmTec SW30HRLE-440i", "area_m2": physics.AREA, "a": round(A, 6), "b": round(B, 6), "kdp": KDP,
                 "test": TEST, "max_pressure_bar": 83, "max_element_dp_bar": 1.0, "max_vessel_dp_bar": 3.4, "max_temp_c": 45,
                 "free_chlorine_mgl": 0.1, "spacer_mil": 28, "length_mm": 1016, "od_mm": 201, "permeate_tube_id_mm": 29,
                 "basis": "A (L/m2/h/bar) and B (L/m2/h) fitted with physics.element() to the data-sheet test point; k_dp assumed"},
    "train": {"vessels": 40, "elements_per_vessel": 7, "banks": 4, "permeate_setpoint_m3h": 160.0, "recovery": 0.43,
              "max_pressure_bar": 82.0, "permeate_pressure_bar": 0.6, "oring_leak_frac": 0.004,
              "average_flux_lmh": round(160.0 * 1000 / (40 * 7 * physics.AREA), 1),
              "assumed": "train size, recovery and permeate setpoint are a typical one-pass SWRO design (assumed)"},
    "hp_pump": {"type": "multi-stage horizontal centrifugal, VFD", "eta_bep": 0.82, "q_bep_m3h": 162.0, "eta_motor": 0.96,
                "head_rated_bar": 62.0, "assumed": "efficiency curve eta_bep (1 - 0.8 (Q/Qbep - 1)^2) assumed"},
    "erd": {"type": "3 x Energy Recovery PX Q300 (isobaric)", "units": 3, "lubrication_frac": 0.01, "mixing_frac": 0.02,
            "hp_dp_bar": 0.5, "lp_out_pressure_bar": 2.3,
            "assumed": "lubrication 1 %, volumetric mixing 2 % (below the < 3 % ERI quotes for the Q400) and the PX pressure losses are assumed"},
    "booster": {"eta": 0.78, "eta_motor": 0.95, "assumed": "booster (circulation) pump efficiency assumed"},
    "cartridge": {"rating_um": 5, "dp_clean_bar": 0.35, "design_flow_m3h": 372.0, "supply_pressure_bar": 3.6,
                  "assumed": "clean dP and supply pressure assumed; dP rises with Q^2"},
    "cleaning_triggers": {"npf_drop_pct": 10, "nsp_rise_pct": 10, "ndp_rise_pct": 15,
                          "source": "Water Technology, Membrane cleaning fundamentals (ASTM D4516 normalisation)"},
    "demo": {"time_scale": 1, "note": "Real time. Fouling that takes weeks in a plant is compressed into a 2-3 minute ramp when a "
                                      "failure mode is injected; Clear all restores the clean membranes."},
}

limits = {"npf_low_pct": 90.0, "nsp_high_pct": 110.0, "ndp_high_pct": 115.0,
          "scaling_npf_pct": 94.0, "scaling_nsp_pct": 105.0, "scaling_ndp_max_pct": 110.0,
          "oxidation_nsp_pct": 130.0, "oxidation_npf_pct": 103.0, "orp_alert_mv": 400.0,
          "bank_ratio_alert": 1.3, "hp_eff_dev_alert_pts": 4.0,
          "px_eff_alert_pct": 95.0, "px_mixing_alert_pct": 5.0, "px_leakage_alert_pct": 3.5,
          "cf_dp_alert_bar": 1.0, "suction_low_bar": 1.0, "feed_pressure_alert_bar": 80.0, "permeate_tds_alert_mgl": 500.0}

twin = {
    "$comment": "Single source of truth for the RO-1201 digital twin: one seawater reverse osmosis train (40 pressure vessels x 7 "
                "DuPont FilmTec SW30HRLE-440i elements, 3 Energy Recovery PX Q300). Membrane data from the DuPont data sheet; "
                "normalisation per ASTM D4516; train sizing and pump data are assumptions.",
    "twin": {"id": "urn:maximo:twin:reverseosmosis:RO-1201", "version": "1.0.0",
             "kind": "Seawater reverse osmosis train with isobaric energy recovery",
             "standards": {
                 "performance": f"DuPont FilmTec SW30HRLE-440i: 41 m2, 31 m3/d and 99.80 % at 32,000 mg/L / 55.2 bar / 25 C / 8 %; "
                                f"fitted A {A:.3f} L/m2/h/bar, B {B:.4f} L/m2/h",
                 "normalisation": "ASTM D4516: normalised permeate flow, normalised salt passage, normalised pressure drop",
                 "energy_recovery": "Energy Recovery PX Q series: isobaric, up to 98 % efficiency, < 3 % mixing (Q400)",
                 "information_model": "OPC UA tags named after ISA-5.1 instrument numbers (FIT, PIT, PDIT, AIT, TIT, JIT, SIT)"}},
    "identification": {"assetnum": "RO-1201", "description": "Seawater RO train 1201 (40 x 7 SW30HRLE-440i, PX energy recovery)",
                       "manufacturer": "DuPont FilmTec / Energy Recovery", "model": "SW30HRLE-440i x 280, PX Q300 x 3",
                       "site": "BEDFORD", "location": "BEDFORD desalination plant / RO hall / train 1201",
                       "medium": "Seawater 38,500 mg/L TDS, 27 C"},
    "design": design,
    "telemetry": {"event": "ro", "publish_every_s": 5, "device_type": "REVERSE_OSMOSIS_TRAIN",
                  "groups": {"Intake": "Seawater after pretreatment", "Cartridge": "5-micron cartridge filters", "HPPump": "High-pressure pump",
                             "ERD": "Pressure exchangers and booster pump", "Membranes": "Pressure vessel rack", "Permeate": "Permeate and bank conductivity"},
                  "points": points},
    "twin_model": {"limits": limits},
    "failure_modes": failure_modes,
    "presentation": {
        "category": "Reverse osmosis train",
        "kpis": [{"metric": "permeate_flow_m3h", "label": "Permeate", "unit": "m³/h", "decimals": 1},
                 {"metric": "membrane_feed_pressure_bar", "label": "Feed pressure", "unit": "bar", "decimals": 1},
                 {"metric": "permeate_tds_mgl", "label": "Permeate TDS", "unit": "mg/L", "decimals": 0},
                 {"metric": "feed_temp_c", "label": "Seawater", "unit": "°C", "decimals": 1}],
        "twin_kpis": [{"metric": "npf_pct", "label": "Norm. flow", "unit": "%", "decimals": 1},
                      {"metric": "sec_kwh_m3", "label": "Specific energy", "unit": "kWh/m³", "decimals": 2}],
        "compare": [
            {"label": "Permeate flow", "measured": "permeate_flow_m3h", "expected": "permeate_expected_m3h", "unit": "m³/h", "decimals": 1,
             "basis": "clean membranes at today's NDP and temperature: NPF0 x TCF x NDP / NDP_ref"},
            {"label": "Normalised permeate flow", "measured": "npf_pct", "expected": None, "unit": "%", "decimals": 1, "basis": "ASTM D4516; clean below 90 %"},
            {"label": "Normalised salt passage", "measured": "nsp_pct", "expected": None, "unit": "%", "decimals": 1, "basis": "ASTM D4516; clean above 110 %"},
            {"label": "Normalised pressure drop", "measured": "ndp_norm_pct", "expected": None, "unit": "%", "decimals": 1, "basis": "dP x (Qavg_ref/Qavg)^1.5; clean above 115 %"},
            {"label": "HP pump efficiency", "measured": "hp_pump_eff_pct", "expected": "hp_pump_eff_expected_pct", "unit": "%", "decimals": 1,
             "basis": "wire-to-water, assumed curve 0.82 (1 - 0.8 (Q/162 - 1)²) x 0.96"},
            {"label": "PX efficiency", "measured": "px_eff_pct", "expected": None, "unit": "%", "decimals": 1, "basis": "ΣQ·P out / ΣQ·P in; ERI up to 98 %"},
            {"label": "PX mixing", "measured": "px_mixing_pct", "expected": None, "unit": "%", "decimals": 1, "basis": "salinity rise of the membrane feed; ERI < 3 % (Q400)"},
            {"label": "Specific energy", "measured": "sec_kwh_m3", "expected": None, "unit": "kWh/m³", "decimals": 2, "basis": "(HP + booster) / permeate"},
            {"label": "Bank TDS ratio", "measured": "bank_tds_ratio", "expected": None, "unit": "x", "decimals": 2, "basis": "worst bank / train average; leak above 1.3"},
        ],
        "trends": [{"metric": "npf_pct", "label": "Normalised flow (%)"}, {"metric": "nsp_pct", "label": "Normalised salt passage (%)"},
                   {"metric": "ndp_norm_pct", "label": "Normalised dP (%)"}, {"metric": "sec_kwh_m3", "label": "Specific energy (kWh/m³)"}],
        "design": [
            {"label": "Element", "value": "DuPont FilmTec SW30HRLE-440i: 41 m², 31 m³/d, 99.80 % (32 g/L NaCl, 55.2 bar, 25 °C), max 83 bar"},
            {"label": "Train", "value": "40 vessels x 7 elements (11,480 m²), 160 m³/h permeate, 43 % recovery, ~13.9 L/m²h (assumed)"},
            {"label": "Energy recovery", "value": "3 x Energy Recovery PX Q300 isobaric + booster; HP pump 0.82 BEP (assumed)"},
            {"label": "Source", "value": "DuPont data sheet 609-03001; ERI PX Q brochure; ASTM D4516; 3D built from published element dimensions, not manufacturer CAD"},
        ],
    },
}


def calibrate(tw):
    """Clean-membrane baseline: run the clean, noise-free plant from 14 to 40 C at three salinities, apply the
    normalisation formulas and fit each normalised value as c0 + c1 T + c2 T^2."""
    import copy
    import numpy as np
    rows = []
    for dtds in (-400.0, 0.0, 400.0):
        for temp in range(14, 41):
            t2 = copy.deepcopy(tw)
            t2["design"]["seawater"].update(temp_c=float(temp), temp_swing_c=0.0, tds_swing_mgl=0.0,
                                            tds_mgl=t2["design"]["seawater"]["tds_mgl"] + dtds)
            p = physics.Plant(t2, seed=3)
            p.rng.gauss = lambda mu, sd: 0.0
            for _ in range(4):
                r = p.step(60.0)
            rows.append(r)
    pivot = next(r for r in rows[27:54] if abs(r["feed_temp_c"] - tw["design"]["seawater"]["temp_c"]) < 0.01)
    ref = twin_calc.raw_norm(pivot, 1.0, 1.0)
    ndp_ref = round(ref["ndp"], 3)
    qavg_ref = round((ref["qm"] + pivot["concentrate_flow_m3h"]) / 2, 2)
    n = [twin_calc.raw_norm(r, ndp_ref, qavg_ref) for r in rows]
    T = np.array([r["feed_temp_c"] for r in rows])
    fit = {}
    for key, out in (("npf", "npf_poly"), ("nsp", "nsp_poly"), ("ndpn", "ndp_poly")):
        y = np.array([x[key] for x in n])
        c2, c1, c0 = np.polyfit(T, y, 2)
        fit[out] = [float(f"{c0:.8g}"), float(f"{c1:.8g}"), float(f"{c2:.8g}")]
        resid = y / twin_calc.poly(fit[out], T) * 100 - 100
        print(f"  {key:5s} baseline fit 14-40 C, +/-400 mg/L: residual {resid.min():+.2f} .. {resid.max():+.2f} %")
    base = {"ndp_ref_bar": ndp_ref, "qavg_ref_m3h": qavg_ref, **fit,
            "basis": "normalised values of the clean, noise-free physics model at 14-40 C and 38,100-38,900 mg/L, "
                     "fitted as c0 + c1 T + c2 T^2 by build_twin.py (NPF in m3/h, NSP as a fraction, NdP in bar)"}
    return base


if __name__ == "__main__":
    base = calibrate(twin)
    twin["twin_model"]["baseline"] = base
    # spread of the clean normalised values (should stay within a few %) including a warm and a cold sweep
    import copy
    spread = []
    for dt_c in (-5.0, 0.0, 8.0):
        tw = copy.deepcopy(twin)
        tw["design"]["seawater"]["temp_c"] += dt_c
        p = physics.Plant(tw, seed=5)
        for _ in range(12):
            r = p.step(600.0)
            e = twin_calc.evaluate(twin, r)
            spread.append((r["feed_temp_c"], r["membrane_feed_pressure_bar"], r["permeate_tds_mgl"], e["npf_pct"], e["nsp_pct"], e["ndp_norm_pct"],
                           e["sec_kwh_m3"], e["px_eff_pct"], e["px_mixing_pct"]))
    print(f"A {A:.4f} L/m2/h/bar  B {B:.5f} L/m2/h  baseline {base}")
    print("  T C    Pf bar  Cp mg/L  NPF %  NSP %  NdP %  SEC   PXeff  mix")
    for s in spread[::3]:
        print("  " + "  ".join(f"{v:6.2f}" for v in s))
    out = HERE / "twin" / "ro-1201.twin.json"
    out.parent.mkdir(exist_ok=True)
    json.dump(twin, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("written", out)
