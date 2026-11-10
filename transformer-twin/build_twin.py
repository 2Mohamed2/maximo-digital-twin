"""Build twin/tr-601.twin.json: SGB-SMIT DOTML 1000 kVA hermetic oil distribution transformer (ONAN).

Sources (public, read 2026-11-10):
  SGB-SMIT oil distribution transformers 50-2500 kVA, selection table (24 kV class) and the 1000 kVA product detail page
    https://www.sgb-smit.com/products/oil-distribution-transformers/oil-distribution-transformers-50-kva-up-to-2500-kva/selection-12kv
    1000 kVA: P0 693 W (selection table), Pk 7600 W, uk 6 %, total 3530 kg, oil 690 kg, core 1455 kg, windings 600 kg,
    L x W x H 1550 x 980 x 1650 mm, Um 24 kV / 1.1 kV, hermetic, porcelain HV bushings, off-circuit tap changer,
    thermometer pocket, max ambient 40 C, altitude <= 1000 m, DIN EN 50588 / EN 60076-1.
  IEC 60076-7:2018 loading guide, thermal model and distribution-transformer (ONAN) defaults as implemented in the
    Alliander open-source transformer-thermal-model (MPL-2.0):
    https://github.com/alliander-opensource/transformer-thermal-model (transformer/distribution.py, aging.py, docs)
  DGA: IEEE C57.104-1991 condition table (TJH2b guideline, https://facilityresults.com/wp-content/uploads/2019/10/FR-IEEE-DISSOLVED-GAS-ANALYSIS-GUIDELINES.pdf)
       Duval Triangle 1 zones per IEEE C57.104-2019 6.2.3 (https://www.hvassets.com/en/post/the-duval-triangle-for-transformer-fault-diagnosis)
  Online DGA monitor modelled on Qualitrol Serveron TM8 (8 gases + moisture), https://www.qualitrolcorp.com/?p=1313
Assumptions (not published by SGB-SMIT, labelled in the twin): rated voltages 20 kV / 0.42 kV, vector group Dyn5,
  cooling ONAN (implied by the hermetic corrugated tank), H = 1.2, non-upgraded paper, hermetic tank pressure law,
  sensor set (monitoring IED with thermal image, DGPT2-style protection relay).
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).parent
S_KVA, U_LV, P0, PK = 1000.0, 420.0, 693.0, 7600.0
I_LV = S_KVA * 1000 / (math.sqrt(3) * U_LV)


def P(metric, path, label, unit, rng, noise, opc=None):
    return {"metric": metric, "path": path, "label": label, "unit": unit, "range": rng, "noise": noise, "opc": opc}


points = [
    P("load_current_l1_a", "Load.CurrentL1", "LV load current L1", "A", [0, 3000], 2.0, "IEC 61850: MMXU.A.phsA"),
    P("load_current_l2_a", "Load.CurrentL2", "LV load current L2", "A", [0, 3000], 2.0, "IEC 61850: MMXU.A.phsB"),
    P("load_current_l3_a", "Load.CurrentL3", "LV load current L3", "A", [0, 3000], 2.0, "IEC 61850: MMXU.A.phsC"),
    P("neutral_current_a", "Load.CurrentN", "LV neutral current", "A", [0, 1000], 0.8, "IEC 61850: MMXU.A.neut"),
    P("lv_voltage_v", "Load.VoltageLL", "LV voltage (line to line)", "V", [0, 500], 0.4, "IEC 61850: MMXU.PPV"),
    P("load_kva", "Load.ApparentPower", "Load (apparent power)", "kVA", [0, 2500], 1.5, "IEC 61850: MMXU.TotVA"),
    P("power_factor", "Load.PowerFactor", "Power factor", "", [0, 1], 0.002, "IEC 61850: MMXU.TotPF"),
    P("load_eq_pu", "Thermal.EquivalentLoad", "Equivalent load over the oil time constant (IED thermal image)", "pu", [0, 3], 0.002,
      "IEC 61850: YPTR / STMP (thermal image)"),
    P("ambient_temp_c", "Thermal.Ambient", "Ambient temperature", "degC", [-40, 60], 0.1, "IEC 61850: MMET.EnvTmp"),
    P("ambient_avg_c", "Thermal.AmbientMean", "Ambient, mean over the oil time constant (IED)", "degC", [-40, 60], 0.05),
    P("top_oil_temp_c", "Thermal.TopOil", "Top-oil temperature (thermometer pocket)", "degC", [-40, 150], 0.2, "IEC 61850: STMP.Tmp (top oil)"),
    P("wti_temp_c", "Thermal.WindingHotSpot", "Winding temperature indicator (thermal image of the hot spot)", "degC", [-40, 200], 0.3,
      "IEC 61850: STMP.Tmp (winding)"),
    P("tank_pressure_bar", "Tank.Pressure", "Tank pressure (hermetic, gauge)", "bar(g)", [-0.5, 1.0], 0.003, "IEC 61850: SIML.Pres"),
    P("oil_level_pct", "Tank.OilLevel", "Oil level (cover gauge)", "%", [0, 120], 0.15, "IEC 61850: SIML.Lev"),
    P("tap_position", "Tank.TapPosition", "Off-circuit tap position (1..5, 3 = rated)", "pos", [1, 5], 0, "IEC 61850: YLTC.TapPos"),
    P("relay_status", "Protection.RelayStatus", "Protection relay (DGPT2-style): 0 normal, 1 alarm, 2 trip", "code", [0, 2], 0,
      "IEC 61850: SIML.GasInsAlm / Trip"),
    P("dga_h2_ppm", "DGA.H2", "Hydrogen H2 (online DGA)", "ppm", [0, 20000], 0.6, "IEC 61850: SIML.H2ppm"),
    P("dga_o2_ppm", "DGA.O2", "Oxygen O2 (online DGA)", "ppm", [0, 50000], 15, "IEC 61850: SIML.O2ppm"),
    P("dga_co_ppm", "DGA.CO", "Carbon monoxide CO (online DGA)", "ppm", [0, 20000], 3, "IEC 61850: SIML.COppm"),
    P("dga_co2_ppm", "DGA.CO2", "Carbon dioxide CO2 (online DGA)", "ppm", [0, 50000], 15, "IEC 61850: SIML.CO2ppm"),
    P("dga_ch4_ppm", "DGA.CH4", "Methane CH4 (online DGA)", "ppm", [0, 20000], 0.4, "IEC 61850: SIML.CH4ppm"),
    P("dga_c2h2_ppm", "DGA.C2H2", "Acetylene C2H2 (online DGA)", "ppm", [0, 5000], 0.05, "IEC 61850: SIML.C2H2ppm"),
    P("dga_c2h4_ppm", "DGA.C2H4", "Ethylene C2H4 (online DGA)", "ppm", [0, 20000], 0.3, "IEC 61850: SIML.C2H4ppm"),
    P("dga_c2h6_ppm", "DGA.C2H6", "Ethane C2H6 (online DGA)", "ppm", [0, 20000], 0.3, "IEC 61850: SIML.C2H6ppm"),
    P("moisture_ppm", "DGA.Moisture", "Moisture in oil", "ppm", [0, 200], 0.15, "IEC 61850: SIML.H2O"),
]

failure_modes = {
    "cooling_degraded": {"label": "Cooling degraded (fins blocked)", "cause": "Corrugated fins fouled, painted over or boxed in: the tank sheds less heat, so the top oil runs hotter than IEC 60076-7 expects for the same load and ambient",
                         "detect": ["top_oil_residual_k", "top_oil_temp_c", "wti_temp_c"], "action": "Clean the fins, restore free air around the tank; check the enclosure ventilation", "default_ramp_min": 3},
    "overload_ageing": {"label": "Sustained overload (paper ageing)", "cause": "Load kept above 1.2 pu: the winding hot spot passes 120 C, the paper ages many times faster and gives off CO and CO2",
                        "detect": ["load_eq_pu", "wti_temp_c", "ageing_rate_v", "dga_co_ppm"], "action": "Shift load to a neighbouring substation or upgrade the transformer; record the loss of life", "default_ramp_min": 3},
    "thermal_fault_core": {"label": "Thermal fault (core / connection hot spot)", "cause": "A poor joint or a circulating-current loop in the core heats the oil locally: methane first, then ethylene as the temperature passes 700 C (Duval T1 -> T3). The WTI cannot see it",
                           "detect": ["dga_ch4_ppm", "dga_c2h4_ppm", "duval_zone", "ieee_condition"], "action": "Plan an internal inspection: check winding and tap-changer connections, core earthing and clamping", "default_ramp_min": 3},
    "partial_discharge": {"label": "Partial discharge", "cause": "Voids or a sharp edge in the insulation discharge in the oil: hydrogen dominates with a trace of methane (Duval PD)",
                          "detect": ["dga_h2_ppm", "duval_zone"], "action": "Confirm with an acoustic or UHF PD test; plan an outage and drying/repair", "default_ramp_min": 2},
    "arcing": {"label": "Arcing (high-energy discharge)", "cause": "A flashover between turns or to earth: acetylene and hydrogen jump (Duval D1/D2); at full severity the protection relay trips the transformer",
               "detect": ["dga_c2h2_ppm", "dga_h2_ppm", "duval_zone", "relay_status"], "action": "Do not re-energise: test (ratio, winding resistance, insulation) and repair or replace", "default_ramp_min": 2},
    "moisture_ingress": {"label": "Moisture ingress (seal leak)", "cause": "A failing gasket lets humid air in: water in oil rises (more when warm), oxygen rises, breakdown strength falls and the paper ages faster",
                         "detect": ["moisture_ppm", "dga_o2_ppm"], "action": "Find and replace the seal; dry the oil (and the active part if the paper is wet)", "default_ramp_min": 3},
    "oil_leak": {"label": "Oil leak (hermetic tank)", "cause": "A weeping weld, valve or bushing gasket: the oil level and the tank pressure fall below what the oil temperature explains",
                 "detect": ["oil_level_pct", "tank_pressure_bar", "pressure_residual_bar"], "action": "Locate and fix the leak, top up with dried oil, check the gas/pressure relay", "default_ramp_min": 3},
}

THERMAL = {"x": 0.8, "y": 1.6, "k11": 1.0, "k21": 1.0, "k22": 2.0, "tau_o_min": 180.0, "tau_w_min": 4.0,
           "dtheta_or_k": 60.0, "g_r_k": 23.0, "H": 1.2, "R": round(PK / P0, 4),
           "basis": "IEC 60076-7:2018 distribution transformer ONAN defaults as in the Alliander transformer-thermal-model "
                    "(distribution.py); H = 1.2 library default (IEC range 1.1-1.3, assumption); R = Pk/P0 from SGB-SMIT data"}

twin = {
    "$comment": "Single source of truth for the TR-601 digital twin: SGB-SMIT DOTML 1000 kVA hermetic oil distribution transformer, "
                "ONAN, in a district substation. Ratings and losses from the SGB-SMIT product data; thermal model IEC 60076-7; DGA IEEE C57.104 / Duval.",
    "twin": {"id": "urn:maximo:twin:oiltransformer:TR-601", "version": "1.0.0",
             "kind": "Oil-immersed distribution transformer (hermetic, ONAN) with online DGA",
             "standards": {
                 "performance": f"SGB-SMIT DOTML 1000 kVA: P0 {P0:.0f} W, Pk {PK:.0f} W, uk 6 %, oil 690 kg, total 3530 kg",
                 "thermal": "IEC 60076-7:2018 loading guide: top-oil and hot-spot difference equations, ageing rate V, loss of life",
                 "dga": "IEEE C57.104-1991 condition table (1-4) and Duval Triangle 1 (IEEE C57.104-2019 6.2.3); the second D2 band "
                        "(23 <= C2H4 < 40 % and 13 <= C2H2 < 29 %) is taken from the original Duval triangle and is unverified",
                 "information_model": "Points named after IEC 61850 logical nodes (MMXU, STMP, SIML, YPTR, YLTC)"}},
    "identification": {"assetnum": "TR-601", "description": "Distribution transformer 601 (substation S6, 20/0.42 kV)",
                       "manufacturer": "SGB-SMIT", "model": "DOTML 1000 kVA 24 kV hermetic",
                       "site": "Demo distribution network", "location": "Substation S6 / transformer bay 1",
                       "medium": "Mineral oil, hermetic corrugated tank, ONAN"},
    "design": {
        "rating": {"s_kva": S_KVA, "u_hv_kv": 20.0, "u_lv_v": U_LV, "i_lv_rated_a": round(I_LV, 1), "um_hv_kv": 24, "um_lv_kv": 1.1,
                   "vector_group": "Dyn5", "uk_pct": 6.0, "cooling": "ONAN", "frequency_hz": 50,
                   "assumed": "rated voltages 20 kV / 0.42 kV, Dyn5 and ONAN are assumptions; SGB-SMIT publishes Um 24 / 1.1 kV only"},
        "losses": {"p0_w": P0, "pk_w": PK, "loss_combination": "AA0Ak (EN 50588)", "R": THERMAL["R"]},
        "mass": {"total_kg": 3530, "oil_kg": 690, "core_kg": 1455, "windings_kg": 600},
        "dimensions_mm": {"length": 1550, "width": 980, "height": 1650},
        "sound": {"lpa_db_0_3m": 34, "lwa_db": 45},
        "tap_changer": {"type": "off-circuit", "positions": 5, "step_pct": 2.5, "rated_position": 3},
        "site_limits": {"max_ambient_c": 40, "altitude_m": 1000},
        "thermal": THERMAL,
        "ageing": {"paper": "non-thermally upgraded (assumption)", "ref_hot_spot_c": 98.0,
                   "v_non_upgraded": "2^((theta_h - 98)/6)", "v_upgraded": "exp(15000/383 - 15000/(theta_h + 273))",
                   "normal_life_h": 180000},
        "loading_limits": {"normal_cyclic": {"top_oil_c": 105, "hot_spot_c": 120, "current_pu": 1.5},
                           "long_term_emergency": {"top_oil_c": 115, "hot_spot_c": 140, "current_pu": 1.8},
                           "short_term_emergency": {"top_oil_c": 115, "hot_spot_c": 160, "current_pu": 2.0}},
        "hermetic": {"pressure_at_20c_bar": 0.02, "pressure_per_k_bar": 0.0035,
                     "note": "Hermetic tank gauge pressure rises with the oil temperature (corrugated fins expand); law assumed"},
        "dga": {"monitor": "Online DGA (modelled on Qualitrol Serveron TM8: 8 gases + moisture)",
                "ieee_1991_limits_ppm": {"h2": [100, 700, 1800], "ch4": [120, 400, 1000], "c2h2": [35, 50, 80],
                                         "c2h4": [50, 100, 200], "c2h6": [65, 100, 150], "co": [350, 570, 1400],
                                         "tdcg": [720, 1920, 4630]},
                "duval_gate": {"h2": 100, "ch4": 120, "c2h4": 50, "c2h2": 1.0,
                               "note": "Duval Triangle 1 is applied only once a gas is above its normal level (IEC 60599)"},
                "duval_zones": {"0": "normal (no fault gas)", "1": "PD partial discharge", "2": "T1 thermal < 300 C",
                                "3": "T2 thermal 300-700 C", "4": "T3 thermal > 700 C", "5": "D1 low-energy discharge",
                                "6": "D2 high-energy discharge", "7": "DT thermal + electrical"}},
        "demo": {"time_scale": 60, "note": "The plant clock runs 60x real time (one day in 24 min) so a thermal transient with a "
                                           "180-min oil time constant plays out in about 3 minutes; gas changes after an injected fault are "
                                           "compressed to 1-3 min, and Clear all resets the oil to its pre-fault gas levels."},
    },
    "telemetry": {"event": "transformer", "publish_every_s": 5, "device_type": "OIL_TRANSFORMER",
                  "groups": {"Load": "LV load (CTs and VTs)", "Thermal": "Temperatures and the IED thermal image",
                             "Tank": "Tank, oil level, tap changer", "Protection": "Gas / pressure / temperature relay",
                             "DGA": "Online dissolved-gas analysis"},
                  "points": points},
    "twin_model": {"limits": {"top_oil_residual_alert_k": 8.0, "steady_load_min_pu": 0.25, "top_oil_alert_c": 105, "hot_spot_alert_c": 120,
                              "overload_alert_pu": 1.2, "ageing_alert": 2.0, "moisture_alert_ppm": 25, "oil_level_alert_pct": 90,
                              "pressure_residual_alert_bar": -0.05, "co_paper_alert_ppm": 570, "ieee_condition_alert": 3}},
    "failure_modes": failure_modes,
    "presentation": {
        "category": "Oil transformer",
        "kpis": [{"metric": "load_kva", "label": "Load", "unit": "kVA", "decimals": 0},
                 {"metric": "top_oil_temp_c", "label": "Top oil", "unit": "°C", "decimals": 1},
                 {"metric": "wti_temp_c", "label": "Hot spot (WTI)", "unit": "°C", "decimals": 1},
                 {"metric": "dga_h2_ppm", "label": "H2", "unit": "ppm", "decimals": 0}],
        "twin_kpis": [{"metric": "top_oil_residual_k", "label": "Top oil vs. IEC", "unit": "K", "decimals": 1},
                      {"metric": "ageing_rate_v", "label": "Ageing rate V", "unit": "x", "decimals": 2}],
        "compare": [
            {"label": "Top-oil temperature", "measured": "top_oil_temp_c", "expected": "top_oil_expected_c", "unit": "°C", "decimals": 1,
             "basis": "IEC 60076-7 at the equivalent load and mean ambient (dTheta_or 60 K, x 0.8, R 11.0)"},
            {"label": "Winding hot spot", "measured": "wti_temp_c", "expected": "hot_spot_expected_c", "unit": "°C", "decimals": 1,
             "basis": "measured top oil + H g_r K^y (H 1.2, g_r 23 K, y 1.6)"},
            {"label": "Total losses", "measured": "losses_kw", "expected": None, "unit": "kW", "decimals": 2, "basis": "P0 0.693 kW + Pk 7.6 kW x K²"},
            {"label": "Ageing rate V", "measured": "ageing_rate_v", "expected": None, "unit": "x", "decimals": 2, "basis": "2^((θh − 98)/6), 1 = normal"},
            {"label": "Tank pressure", "measured": "tank_pressure_bar", "expected": "pressure_expected_bar", "unit": "bar(g)", "decimals": 3,
             "basis": "hermetic tank: 0.02 bar + 0.0035 bar/K above 20 °C (assumed)"},
            {"label": "TDCG", "measured": "tdcg_ppm", "expected": None, "unit": "ppm", "decimals": 0, "basis": "IEEE C57.104 condition 1 ≤ 720"},
            {"label": "Duval zone", "measured": "duval_zone", "expected": None, "unit": "", "decimals": 0, "basis": "0 normal, 1 PD, 2-4 T1-T3, 5-6 D1-D2, 7 DT"},
        ],
        "trends": [{"metric": "top_oil_residual_k", "label": "Top oil vs. IEC (K)"}, {"metric": "ageing_rate_v", "label": "Ageing rate V"},
                   {"metric": "tdcg_ppm", "label": "TDCG (ppm)"}, {"metric": "ieee_condition", "label": "IEEE condition"}],
        "design": [
            {"label": "Transformer", "value": "SGB-SMIT DOTML 1000 kVA hermetic, Um 24/1.1 kV, uk 6 %, P0 693 W, Pk 7600 W"},
            {"label": "Assumed", "value": "20 kV / 0.42 kV Dyn5, ONAN, non-upgraded paper, H = 1.2"},
            {"label": "Thermal", "value": "IEC 60076-7 ONAN: dTheta_or 60 K, g_r 23 K, x 0.8, y 1.6, tau_o 180 min, tau_w 4 min"},
            {"label": "Source", "value": "SGB-SMIT product data (1000 kVA, 24 kV class); 3D built from published dimensions, not manufacturer CAD"},
        ],
    },
}

if __name__ == "__main__":
    out = HERE / "twin" / "tr-601.twin.json"
    out.parent.mkdir(exist_ok=True)
    json.dump(twin, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("written", out)
