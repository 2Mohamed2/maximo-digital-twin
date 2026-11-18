"""Write twin/ad-4901.twin.json: the mesophilic anaerobic sludge digester twin (AD-4901).

    python build_twin.py

AD-4901 is one mesophilic anaerobic digester of a municipal wastewater treatment plant: a 3000 m3 heated, mixed concrete
tank fed with thickened primary + surplus activated sludge, an external sludge/water heat exchanger, two top-entry mixers,
a double-membrane gas holder and one biogas CHP unit (2G agenitor 406, biogas rating) that supplies the heat.

Sources and assumptions (every number below is either from a checked source or labelled as an assumption in "source"):
  US EPA Fact Sheet "Multi-stage anaerobic digestion" (EPA 832-F-06-031): biogas 55-70 % CH4; heat content 18,630-26,080 kJ/m3;
    temperature changes > ~1 C per day can upset the process; optimum pH 6.8-7.2; single-stage mesophilic SRT ~20 d and
    VS loading 2.57 kg/m3.d on average (Sieger 2001); gas 14-16 ft3/lb VS destroyed (Wilson et al.); foaming; grit and
    scum reduce the effective volume; cleaning about every 5 years.
  40 CFR Part 503 Appendix B: anaerobic digestion as a PSRP, mean cell residence time 15 d at 35-55 C.
  40 CFR 503.33(b)(1): vector attraction reduction, volatile solids reduced by at least 38 %.
  Ohio EPA operator formula sheet: VSR = (in - out) / (in - in x out) (Van Kleeck).
  2G Energy, agenitor product page: agenitor 406 biogas ct135-B-0: 275 kW el, 260 kW th, 42.5 % el, 40.2 % th.
  Methane lower heating value 35.887 MJ/m3 at 0 C = 9.97 kWh/m3 (natural gas data table, cementkilns.co.uk).
  Hach (Inizan, Pons, Myers), VFA monitoring paper: slow down or stop feeding when FOS/TAC rises above 0.6 (empirical).
  Volume, feed, sludge composition, heat exchanger, losses, mixer power and all other alarm limits: ASSUMPTIONS of a
  typical plant, to be replaced by the design report and the operating data of your own digester.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with the design report / operating data of your own digester"

twin = {
    "$comment": "AD-4901 mesophilic anaerobic digester twin. Expected values in Maximo Monitor from the design data below; the plant sends only what it measures.",
    "twin": {"id": "AD-4901", "name": "Anaerobic digester AD-4901", "version": "1.0.0", "folder": "digester-twin"},
    "identification": {
        "asset": "AD-4901", "assetnum": "AD-4901", "manufacturer": "Civil works + 2G Energy (CHP)",
        "model": "Mesophilic anaerobic digester, 3000 m3, with 2G agenitor 406 biogas CHP",
        "description": "Mesophilic anaerobic digester no. 1 of a municipal wastewater treatment plant (primary + surplus activated sludge)",
        "tank": "Cylindrical concrete tank with conical floor and fixed roof, 3000 m3 working volume, insulated",
        "mixing": "Two top-entry mechanical mixers in draft tubes",
        "heating": "External sludge / hot water heat exchanger on the recirculation loop, hot water from the CHP",
        "gas": "Double-membrane gas holder, gas to the CHP, surplus to a boiler or the flare",
        "chp": "2G agenitor 406 biogas CHP (ct135-B-0): 275 kW electrical, 260 kW thermal",
    },
    "design": {
        "tank": {
            "volume_m3": 3000.0, "diameter_m": 16.0, "liquid_height_m": 15.0, "freeboard_m": 1.5,
            "ua_wall_kw_k": 0.70, "ambient_design_c": 10.0,
            "source": "Working volume, geometry, freeboard and heat loss coefficient of walls, roof and floor (about 1150 m2 at 0.6 W/m2K): " + A,
        },
        "process": {
            "temp_set_c": 37.0, "feed_flow_m3d": 150.0, "feed_ds_pct": 5.0, "feed_vs_pct": 72.0, "feed_temp_c": 15.0,
            "sludge_density_kg_m3": 1000.0, "vsr_design_pct": 52.0, "gas_yield_m3_kgvsd": 0.94, "ch4_design_pct": 63.0,
            "fostac_normal": 0.22,
            "source": "Mesophilic set point, feed (thickened primary + surplus activated sludge), solids and VS contents, VS reduction, "
                      "gas per kg VS destroyed and methane content: " + A + ". Checked against US EPA fact sheet EPA 832-F-06-031: "
                      "single-stage mesophilic SRT about 20 d, VS loading 2.57 kg/m3.d on average, biogas 55-70 % methane, "
                      "14-16 ft3 gas per lb VS destroyed (0.87-1.0 m3/kg), optimum pH 6.8-7.2.",
        },
        "energy": {
            "ch4_lhv_kwh_m3": 9.97,
            "source": "Methane lower heating value 35.887 MJ/m3 at 0 C = 9.97 kWh per normal m3 (natural gas data, cementkilns.co.uk). "
                      "Gas volumes in this twin are normal m3 (0 C, 1.013 bar).",
        },
        "heat_exchanger": {
            "ua_design_kw_k": 9.0, "recirc_flow_m3h": 30.0, "hw_flow_m3h": 10.0, "hw_supply_c": 63.0, "hw_supply_max_c": 80.0,
            "water_heat_kwh_m3k": 1.163,
            "source": "External tube-in-tube heat exchanger: clean UA (sized with margin, so a clean exchanger holds 37 C with about 63 C hot water), sludge recirculation and hot water flows, hot water supply "
                      "temperature and its limit: " + A + ". 1.163 kWh/m3K = volumetric heat capacity of water (4.187 MJ/m3K / 3.6).",
        },
        "mixing": {"power_design_kw": 15.0, "n_mixers": 2,
                   "source": "Two top-entry mixers, 15 kW absorbed in total (5 W/m3): " + A},
        "chp": {
            "model": "2G agenitor 406 biogas, configuration ct135-B-0", "power_el_kw": 275.0, "heat_kw": 260.0,
            "eta_el": 0.425, "eta_th": 0.402,
            "source": "2G Energy agenitor product page, biogas table: agenitor 406 ct135-B-0, 275 kW electrical, 260 kW thermal, "
                      "electrical efficiency 42.5 %, thermal efficiency 40.2 % (400 V, NOx < 0.5 g/Nm3 at 5 % O2).",
        },
        "demo": {"time_scale": 1,
                 "note": "Demo only: the stand-in digester has no clock. Lab values (DS, VS, FOS/TAC) and the tracer-test active volume "
                         "would change once a day or once a year on a real plant; in the demo they follow the injected faults within minutes."},
    },
    "telemetry": {
        "event": "digester", "publish_every_s": 10, "device_type": "ANAEROBIC_DIGESTER",
        "groups": {"Feed": "Raw sludge feed (flow meter + daily lab)", "Digester": "Tank temperatures, pH and level",
                   "Lab": "Daily lab values of the digester", "Mixing": "Mixers", "Gas": "Biogas line and gas holder",
                   "Heating": "Heat exchanger and hot water", "CHP": "Combined heat and power unit", "Test": "Tracer test"},
        "points": [
            {"metric": "feed_flow_m3d", "path": "Feed.Flow24h", "label": "Raw sludge fed, last 24 h", "unit": "m³/d"},
            {"metric": "feed_ds_pct", "path": "Feed.DS", "label": "Feed dry solids (lab)", "unit": "%"},
            {"metric": "feed_vs_pct", "path": "Feed.VS", "label": "Feed volatile solids, % of DS (lab)", "unit": "%"},
            {"metric": "feed_temp_c", "path": "Feed.Temperature", "label": "Feed sludge temperature", "unit": "°C"},
            {"metric": "temp_top_c", "path": "Digester.TempTop", "label": "Digester temperature, top", "unit": "°C"},
            {"metric": "temp_mid_c", "path": "Digester.TempMid", "label": "Digester temperature, middle", "unit": "°C"},
            {"metric": "temp_bottom_c", "path": "Digester.TempBottom", "label": "Digester temperature, bottom", "unit": "°C"},
            {"metric": "ph", "path": "Digester.pH", "label": "Digester pH", "unit": "pH"},
            {"metric": "foam_layer_m", "path": "Digester.Foam", "label": "Foam layer above the liquid (radar + foam probe)", "unit": "m"},
            {"metric": "fos_tac", "path": "Lab.FOSTAC", "label": "FOS/TAC (volatile acids / alkalinity)", "unit": "ratio"},
            {"metric": "digested_vs_pct", "path": "Lab.DigestedVS", "label": "Digested sludge volatile solids, % of DS", "unit": "%"},
            {"metric": "active_volume_pct", "path": "Test.ActiveVolume", "label": "Active volume from the last tracer test", "unit": "%"},
            {"metric": "mixer_power_kw", "path": "Mixing.Power", "label": "Mixers absorbed power, total", "unit": "kW"},
            {"metric": "biogas_flow_m3h", "path": "Gas.Flow", "label": "Biogas production", "unit": "Nm³/h"},
            {"metric": "ch4_pct", "path": "Gas.CH4", "label": "Methane in biogas", "unit": "%"},
            {"metric": "h2s_ppm", "path": "Gas.H2S", "label": "Hydrogen sulphide in biogas", "unit": "ppm"},
            {"metric": "holder_fill_pct", "path": "Gas.HolderFill", "label": "Gas holder filling", "unit": "%"},
            {"metric": "hx_sludge_flow_m3h", "path": "Heating.SludgeFlow", "label": "Sludge through the heat exchanger", "unit": "m³/h"},
            {"metric": "hx_sludge_in_c", "path": "Heating.SludgeIn", "label": "Sludge into the heat exchanger", "unit": "°C"},
            {"metric": "hx_sludge_out_c", "path": "Heating.SludgeOut", "label": "Sludge out of the heat exchanger", "unit": "°C"},
            {"metric": "hw_flow_m3h", "path": "Heating.WaterFlow", "label": "Hot water flow", "unit": "m³/h"},
            {"metric": "hw_supply_c", "path": "Heating.WaterSupply", "label": "Hot water supply temperature", "unit": "°C"},
            {"metric": "hw_return_c", "path": "Heating.WaterReturn", "label": "Hot water return temperature", "unit": "°C"},
            {"metric": "ambient_temp_c", "path": "Heating.Ambient", "label": "Outdoor air temperature", "unit": "°C"},
            {"metric": "chp_gas_m3h", "path": "CHP.GasFlow", "label": "Biogas to the CHP", "unit": "Nm³/h"},
            {"metric": "chp_power_kw", "path": "CHP.Power", "label": "CHP electrical output", "unit": "kW"},
        ],
    },
    "twin_model": {
        "limits": {
            "fostac_warn": 0.4, "fostac_high": 0.6, "ph_low": 6.8, "ch4_low_pct": 55.0, "gas_ratio_low": 0.8,
            "temp_low_k": 1.5, "ua_ratio_low": 0.7, "spread_k": 2.0, "mixing_ratio_low": 0.6, "active_volume_low_pct": 85.0,
            "srt_min_d": 15.0, "vsr_min_pct": 38.0, "foam_max_m": 0.8, "h2s_max_ppm": 500.0, "chp_eff_ratio_low": 0.9,
            "source": "FOS/TAC 0.6: Hach paper (slow down or stop feeding above 0.6, empirical); pH 6.8: lower end of the optimum range "
                      "in EPA 832-F-06-031; CH4 55 %: lower end of the 55-70 % range in the same fact sheet; SRT 15 d: 40 CFR 503 "
                      "Appendix B (anaerobic digestion PSRP at 35-55 C); VSR 38 %: 40 CFR 503.33(b)(1). All other limits: " + A
                      + ". H2S limit: replace with the fuel gas specification of your CHP maker.",
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "souring": {"name": "Souring (organic overload, VFA build-up)", "part": "biology",
                    "symptoms": "FOS/TAC up, pH down, methane down, less gas than the VS destroyed should give",
                    "rules": ["DIG_FOSTAC_RISING", "DIG_FOSTAC_HIGH", "DIG_PH_LOW", "DIG_CH4_LOW", "DIG_GAS_YIELD_LOW"], "default_ramp_min": 1.5},
        "hx_fouling": {"name": "Heat exchanger fouling (sludge cake, scale)", "part": "heating",
                       "symptoms": "UA of the heat exchanger down, hot water hotter, digester cools", "rules": ["DIG_HX_FOULED", "DIG_TEMP_LOW"],
                       "default_ramp_min": 1.5},
        "mixing_failure": {"name": "Mixing failure (mixer tripped, ragged impeller)", "part": "mixing",
                           "symptoms": "mixer power down, temperature spread top to bottom up (stratification)",
                           "rules": ["DIG_MIXING_LOW", "DIG_STRATIFIED"], "default_ramp_min": 1},
        "grit_accumulation": {"name": "Grit and scum accumulation (lost volume)", "part": "tank",
                              "symptoms": "tracer test active volume down, effective SRT below 15 days",
                              "rules": ["DIG_ACTIVE_VOLUME_LOW", "DIG_SRT_LOW"], "default_ramp_min": 1.5},
        "foaming": {"name": "Foaming (filaments, feed shock)", "part": "tank", "symptoms": "foam layer grows into the freeboard",
                    "rules": ["DIG_FOAM_HIGH"], "default_ramp_min": 1},
        "h2s_high": {"name": "Hydrogen sulphide high (iron dosing lost)", "part": "gas", "symptoms": "H2S in the biogas above the CHP limit",
                     "rules": ["DIG_H2S_HIGH"], "default_ramp_min": 1},
        "chp_degradation": {"name": "CHP efficiency loss (ignition, valves, turbocharger)", "part": "chp",
                            "symptoms": "less electricity per kWh of methane", "rules": ["DIG_CHP_EFF_LOW"], "default_ramp_min": 1},
    },
    "presentation": {"title": "AD-4901 anaerobic digester", "dashboard": "ANAEROBIC_DIGESTER"},
}

out = HERE / "twin" / "ad-4901.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
