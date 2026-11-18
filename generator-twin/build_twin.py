"""Write twin/gen-3401.twin.json: the turbo-generator twin (GEN-3401).

    python build_twin.py

GEN-3401 is a large two-pole, air-cooled synchronous generator (cylindrical rotor, 3000 rpm, 50 Hz) driven by a gas turbine
in a power plant. It is modelled on the Siemens Energy SGen5-1000A family: totally enclosed, the air circulates through
water-cooled air coolers (TEWAC), the rotor winding is directly cooled by radial air flow. The plant control system sends
the electrical values, the exciter sends field voltage and current, the stator slot RTDs and the air and water temperatures
come through the generator protection / DCS, an online partial discharge (PD) monitor sends its trend, a flux-probe
analyser sends the shorted-turn count, and the machinery protection system sends shaft vibration and bearing temperatures.

Sources (public):
  Siemens Energy SGen-1000A product page: SGen5-1000A (50 Hz) 180 to 370 MVA, efficiency up to 98.9 %, designed power
      factor 0.80, terminal voltage 10.5 to 20 kV; direct radial air cooling of the rotor winding.
  IEC 60034-1 (text of the 2010 edition checked): a.c. stator windings of machines of 5 000 kVA or more are measured with
      embedded temperature detectors (ETD); Table 7 limits of temperature rise for windings indirectly cooled by air,
      item 1a ETD: 85 K class 130 (B), 110 K class 155 (F); item 4a (cylindrical-rotor field windings, resistance method):
      90 K class B, 110 K class F; Table 9 item 4: the ETD limit is reduced by 1 K per kV (or part) from 12 kV up to 24 kV;
      reference cold coolant 40 C. Resistance method with k = 235 for copper.
  Textbook (for example Kundur, Power System Stability and Control, ch. 5): round-rotor phasor E = V + j Xd I, the
      capability (P-Q) chart limits: armature current circle, field current circle centred at -V^2/Xd, load angle limit.
Assumptions (labelled in "source"): the rating chosen inside the family range, Xd, field current and resistance, every
  thermal coefficient (in practice fitted from the heat-run test and a few months of healthy data), PD levels and every
  alarm limit. Replace them with the maker's data sheet, capability diagram, V-curves, heat-run report and your PD
  monitor supplier's statistics.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with "
SE = "Siemens Energy SGen-1000A product page (SGen5-1000A, 50 Hz: 180-370 MVA, efficiency up to 98.9 %, designed power factor 0.80, 10.5-20 kV)"
V_KV = 15.75
ETD_LIMIT_K = 85 - (int(V_KV - 12 + 0.999))   # IEC 60034-1 Table 7 item 1a class B ETD, Table 9 item 4: -1 K per kV (or part) above 12 kV

twin = {
    "$comment": "GEN-3401 turbo-generator twin. Expected field current, temperatures and capability margins computed in Maximo Monitor from "
                "the rating, the machine constants and the heat-run data; the generator sends only what it measures.",
    "twin": {"id": "GEN-3401", "name": "Turbo-generator GEN-3401", "version": "1.0.0", "folder": "generator-twin"},
    "identification": {
        "asset": "GEN-3401", "assetnum": "GEN-3401", "manufacturer": "Siemens Energy (family)",
        "model": "SGen5-1000A class air-cooled 2-pole generator (rating below is an assumption inside the family range)",
        "description": "Gas turbine generator of a combined-cycle power plant: 2-pole cylindrical rotor, air-cooled (TEWAC), static excitation",
        "cooling": "Totally enclosed, air circulated by shaft fans through water-cooled air coolers; rotor winding directly cooled by radial air",
        "excitation": "Static excitation through slip rings; automatic voltage regulator (AVR) with over- and under-excitation limiters",
        "monitoring": "Stator slot RTDs, cold/hot air and cooler water temperatures, online PD monitor (coupling capacitors), flux probe in the air gap, proximity probes and bearing RTDs",
        "site": "A combined-cycle power plant (generic)",
    },
    "design": {
        "rating": {"s_mva": 300.0, "p_mw": 240.0, "pf": 0.80, "v_kv": V_KV, "f_hz": 50.0, "rpm": 3000.0, "efficiency_pct": 98.9,
                   "source": SE + ". The 300 MVA / 15.75 kV rating is an " + A + "your generator's rating plate"},
        "electrical": {"xd_pu": 2.0, "if_rated_a": 2300.0, "rf20_ohm": 0.13, "k_cu": 235.0, "turns_per_pole": 96,
                       "source": "Synchronous reactance Xd (unsaturated), field current at rated output, field winding resistance at 20 C and turns per pole: "
                                 + A + "the maker's data sheet, V-curves and test report. k = 235 for copper (IEC 60034-1 resistance method)."},
        "thermal": {"coolant_ref_c": 40.0, "stator_rise_limit_k": float(ETD_LIMIT_K), "rotor_rise_limit_k": 90.0,
                    "stator_core_k": 12.0, "stator_cu_k": 55.0, "rtd_mean_ratio": 0.92, "rotor_rise_k": 70.0,
                    "air_rise0_k": 8.0, "air_rise1_k": 16.0, "approach0_k": 6.0, "approach1_k": 3.0,
                    "source": f"Limits: IEC 60034-1 Table 7, class 130 (B) temperature rise used on a class 155 (F) insulation system (typical practice): "
                              f"stator ETD 85 K minus {85 - ETD_LIMIT_K} K for {V_KV} kV (Table 9 item 4) = {ETD_LIMIT_K} K; rotor (item 4a, resistance) 90 K; "
                              "above 40 C cold air. Model coefficients (rise = core x (V/Vn)^2 + copper x (I/In)^2, air rise, cooler approach): "
                              + A + "the heat-run test report and a few months of healthy data"},
        "pd": {"qm_normal_mv": 110.0, "coupling": "80 pF capacitive couplers on each phase at the terminals",
               "source": "Online PD peak magnitude Qm in mV from 80 pF couplers: " + A + "the first months of your own PD trend and the PD supplier's statistics for this voltage class"},
        "bearings": {"metal_over_oil_k": 28.0, "load_k": 4.0, "vib_normal_um": 45.0,
                     "source": "Journal bearing metal temperature above oil inlet and shaft relative vibration baseline (proximity probes, peak-to-peak): " + A + "the commissioning records"},
        "cooling": {"water_in_c": 28.0, "oil_in_c": 45.0, "source": "Cooler water and lube oil inlet temperatures: " + A + "the plant design data"},
        "demo": {"time_scale": 60, "p_mean_pu": 0.70, "q_mean_pu": 0.33,
                 "note": "Demo only: one real second is one plant minute; the dispatch wanders between about 165 and 240 MW and the AVR holds 0.3 to 0.45 pu reactive power."},
    },
    "telemetry": {
        "event": "generator", "publish_every_s": 10, "device_type": "TURBO_GENERATOR_AIR",
        "groups": {"Elec": "Generator terminals", "Exc": "Excitation (field)", "Stator": "Stator winding RTDs", "Cooling": "Air and cooler water",
                   "PD": "Online partial discharge monitor", "Rotor": "Flux probe analyser", "Bearings": "Bearings and shaft vibration"},
        "points": [
            {"metric": "active_power_mw", "path": "Elec.P", "label": "Active power", "unit": "MW"},
            {"metric": "reactive_power_mvar", "path": "Elec.Q", "label": "Reactive power (+ lagging, over-excited)", "unit": "Mvar"},
            {"metric": "terminal_voltage_kv", "path": "Elec.Voltage", "label": "Terminal voltage (line-to-line)", "unit": "kV"},
            {"metric": "stator_current_a", "path": "Elec.Current", "label": "Stator current", "unit": "A"},
            {"metric": "frequency_hz", "path": "Elec.Frequency", "label": "Frequency", "unit": "Hz"},
            {"metric": "field_voltage_v", "path": "Exc.FieldVoltage", "label": "Field voltage", "unit": "V"},
            {"metric": "field_current_a", "path": "Exc.FieldCurrent", "label": "Field current", "unit": "A"},
            {"metric": "stator_rtd_max_c", "path": "Stator.RTDMax", "label": "Hottest stator slot RTD", "unit": "°C"},
            {"metric": "stator_rtd_mean_c", "path": "Stator.RTDMean", "label": "Mean of the stator slot RTDs", "unit": "°C"},
            {"metric": "cold_air_c", "path": "Cooling.ColdAir", "label": "Cold air (cooler outlet, into the generator)", "unit": "°C"},
            {"metric": "hot_air_c", "path": "Cooling.HotAir", "label": "Hot air (out of the generator, into the cooler)", "unit": "°C"},
            {"metric": "cooler_water_in_c", "path": "Cooling.WaterIn", "label": "Cooler water inlet", "unit": "°C"},
            {"metric": "pd_qm_mv", "path": "PD.Qm", "label": "PD peak magnitude Qm (worst phase)", "unit": "mV"},
            {"metric": "pd_qm_6mo_mv", "path": "PD.Qm6mo", "label": "PD Qm six months ago, same load and temperature band", "unit": "mV"},
            {"metric": "pd_nqn", "path": "PD.NQN", "label": "PD normalised quantity number (worst phase)", "unit": "mV/s"},
            {"metric": "shorted_turns", "path": "Rotor.ShortedTurns", "label": "Shorted turns found by the flux probe (worst pole)", "unit": "count"},
            {"metric": "oil_in_c", "path": "Bearings.OilIn", "label": "Lube oil inlet", "unit": "°C"},
            {"metric": "brg_de_temp_c", "path": "Bearings.DETemp", "label": "Drive-end journal bearing metal temperature", "unit": "°C"},
            {"metric": "brg_nde_temp_c", "path": "Bearings.NDETemp", "label": "Non-drive-end journal bearing metal temperature", "unit": "°C"},
            {"metric": "vib_de_um", "path": "Bearings.VibDE", "label": "Shaft relative vibration, drive end (peak-to-peak)", "unit": "µm"},
            {"metric": "vib_nde_um", "path": "Bearings.VibNDE", "label": "Shaft relative vibration, non-drive end (peak-to-peak)", "unit": "µm"},
        ],
    },
    "twin_model": {
        "limits": {
            "stator_residual_k": 8.0, "rtd_spread_k": 12.0, "cold_air_max_c": 40.0, "cooler_approach_k": 12.0,
            "pd_qm_alert_mv": 400.0, "pd_trend_ratio": 2.0, "pd_trend_min_mv": 150.0,
            "field_ratio_alert": 1.04, "shorted_turns_alert": 0.5, "load_angle_max_deg": 70.0, "field_current_max_pu": 1.0,
            "stator_current_max_pu": 1.0, "bearing_residual_k": 8.0, "vib_alert_um": 120.0,
            "source": "Every alarm limit is an " + A + "the maker's alarm list, the PD supplier's guidance and your protection settings. "
                      "Temperature limits (stator 40 + %d C, rotor 40 + 90 C) follow IEC 60034-1 class B rise. A doubling of PD in six months is a "
                      "common rule of thumb for a significant trend, not a figure from a standard." % ETD_LIMIT_K,
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "cooler_fouling": {"name": "Air cooler fouling (water side)", "part": "cooler",
                           "symptoms": "cold air and cooler approach up; every temperature up, but the stator residual stays normal",
                           "rules": ["GEN_COOLER_APPROACH", "GEN_COLD_AIR_HIGH"], "default_ramp_min": 1.5},
        "stator_vent_blockage": {"name": "Stator ventilation duct blockage (local)", "part": "stator",
                                 "symptoms": "one slot RTD runs hot for its load and cold air; the mean barely moves",
                                 "rules": ["GEN_STATOR_RESIDUAL", "GEN_RTD_SPREAD"], "default_ramp_min": 1.0},
        "stator_insulation_pd": {"name": "Stator insulation deterioration (slot / end-winding discharge)", "part": "insulation",
                                 "symptoms": "PD magnitude rises and doubles within six months",
                                 "rules": ["GEN_PD_TREND", "GEN_PD_HIGH"], "default_ramp_min": 1.5},
        "rotor_shorted_turns": {"name": "Rotor winding shorted turns", "part": "rotor",
                                "symptoms": "more field current for the same P and Q; the flux probe counts the shorted turns",
                                "rules": ["GEN_FIELD_CURRENT_HIGH", "GEN_SHORTED_TURNS"], "default_ramp_min": 1.0},
        "bearing_wear": {"name": "Drive-end journal bearing wear / wipe", "part": "bearing",
                         "symptoms": "bearing metal hot for its oil temperature, shaft vibration up",
                         "rules": ["GEN_BEARING_TEMP", "GEN_VIB_HIGH"], "default_ramp_min": 1.0},
        "under_excitation": {"name": "Under-excitation (AVR or limiter fault)", "part": "excitation",
                             "symptoms": "reactive power swings leading; load angle near the stability limit",
                             "rules": ["GEN_LOAD_ANGLE_HIGH"], "default_ramp_min": 0.5},
        "over_excitation": {"name": "Over-excitation (over-excitation limiter fault)", "part": "excitation",
                            "symptoms": "field and stator current above rating; rotor and stator temperatures above their limits",
                            "rules": ["GEN_ROTOR_OVERLOAD", "GEN_ROTOR_TEMP_HIGH", "GEN_STATOR_OVERLOAD", "GEN_STATOR_TEMP_LIMIT"], "default_ramp_min": 0.5},
    },
    "presentation": {"title": "GEN-3401 turbo-generator", "dashboard": "TURBO_GENERATOR_AIR"},
}

out = HERE / "twin" / "gen-3401.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
