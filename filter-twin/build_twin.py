"""Build twin/flt-1401.twin.json: rapid gravity dual-media filter cell FLT-1401 (anthracite over sand, Leopold underdrain).

Sources (public, read 2026-11-10):
  Underdrain: Xylem Leopold Universal Type S with I.M.S. cap (sintered PE media retainer, no support gravel).
    Leopold product presentation: Type S max backwash 90 m/h, max air scour 120 m/h, laterals up to 30 m
    https://kh.aquaenergyexpo.com/wp-content/uploads/2022/11/Leopold-Product-Presentation.pdf
    Air scour range 1-5 scfm/ft2 (Universal Type S/SL): https://www.environmental-expert.com/products/leopold-model-type-s-water-treatment-water-filtration-technology-142865
    I.M.S. 200 / 1000 media retainers: https://www.wateronline.com/doc/leopold-ims-media-retainers-0001
  Media (AWWA B100):
    Anthracite #1.5 (Clack): effective size 0.85-0.95 mm, uniformity coefficient < 1.7, specific gravity 1.6
      https://www.clackcorp.com/wp-content/uploads/2024/06/Anthracite.pdf
    Filter sand (Clack): effective size 0.45-0.55 mm, UC <= 1.6, SG 2.65-2.75; Covia FILTERSIL SG 2.65, meets AWWA B100
      https://pureaqua.com/clack-filter-sand-filtration-media , https://www.coviacorp.com/media/yuyndqpy/filtersil_tds_portage_021_0719_wtr_eng.pdf
    Dual media "20 inches of anthracite over sand" and ES 0.45-0.6 mm, UC <= 1.7: TM 5-813-3 (US Army design manual)
      https://buildingcriteria1.tpub.com/ufc_3_230_08a/ufc_3_230_08a0017.htm
  Design and operation:
    Rapid filter rates 5-10 m/h; total available head 1.8-3.0 m: https://www.waterandwastewater.com/sand-filtration-design-tips-optimization/
    Backwash bed expansion 15-30 %, 20 % normal; colder water expands the bed more:
      https://actat.wvu.edu/files/d/638db309-5274-42c9-a8c3-7f8be496c607/filter-backwashing.pdf
  Turbidity: US EPA IESWTR combined filter effluent <= 0.3 NTU in 95 % of monthly readings, never > 1 NTU; continuous
    individual filter monitoring: https://webarchive.library.unt.edu/web/20080916143239/http:/epa.gov/safewater/mdbp/qrg_ieswtr.pdf
  Physics (textbook, e.g. MWH Water Treatment: Principles and Design; Crittenden et al.):
    clean-bed head loss Carman-Kozeny per layer (laminar): h/L = 180 mu (1-e)^2 v / (rho g e^3 (psi d)^2)
    water viscosity (Vogel): mu = 2.414e-5 * 10^(247.8/(T+133.15)) Pa s
    terminal settling velocity of natural grains: Ferguson & Church (2004), w = R g d^2 / (C1 nu + sqrt(0.75 C2 R g d^3)), C1 18, C2 1
    backwash expansion: Richardson-Zaki, e_e = (v_b / v_t)^(1/n), n = 4.45 Re_t^-0.1 (1 < Re < 500)
Assumptions (not published for one product; labelled in the twin): cell 60 m2, 0.6 m anthracite (d_eq 1.0 mm) over
  0.3 m sand (d_eq 0.55 mm), porosities 0.50 / 0.42, sphericities 0.70 / 0.80, underdrain + I.M.S. cap head loss
  0.12 m at 8 m/h, deposit coefficient and storage capacity, TSS = 1.5 x NTU, 1.5 m water above the media,
  backwash 55 m/h with 60 m/h air scour, terminal head loss 2.4 m, run limit 36 h.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).parent

AREA = 60.0                 # m2, one cell (two 30 m2 halves either side of the central gullet), assumed
V0 = 8.0                    # m/h design filtration rate
G, RHO = 9.81, 998.0


def mu(t):
    return 2.414e-5 * 10 ** (247.8 / (t + 133.15))


MU20 = mu(20.0)
ANTH = dict(depth_m=0.60, d_eq_mm=1.00, es_mm=[0.85, 0.95], uc_max=1.7, sg=1.60, porosity=0.50, sphericity=0.70)
SAND = dict(depth_m=0.30, d_eq_mm=0.55, es_mm=[0.45, 0.55], uc_max=1.6, sg=2.65, porosity=0.42, sphericity=0.80)


def ck(layer, v_mh, t=20.0):
    """Carman-Kozeny clean-bed head loss of one layer, m."""
    v = v_mh / 3600.0
    e, d = layer["porosity"], layer["sphericity"] * layer["d_eq_mm"] / 1000.0
    return 180 * mu(t) * (1 - e) ** 2 * v / (RHO * G * e ** 3 * d ** 2) * layer["depth_m"]


H_ANTH0, H_SAND0, H_UD0 = ck(ANTH, V0), ck(SAND, V0), 0.12


def settling(layer, t=20.0):
    """Ferguson & Church terminal settling velocity (m/s) and Re."""
    nu = mu(t) / RHO
    R, d = layer["sg"] - 1, layer["d_eq_mm"] / 1000.0
    w = R * G * d ** 2 / (18 * nu + math.sqrt(0.75 * 1.0 * R * G * d ** 3))
    return w, w * d / nu


VT20, RE20 = settling(ANTH)


def expansion(vb_mh, t=20.0):
    w, re = settling(ANTH, t)
    n = 4.45 * re ** -0.1
    e = min(0.95, max(ANTH["porosity"], (vb_mh / 3600.0 / w) ** (1 / n)))
    return ((1 - ANTH["porosity"]) / (1 - e) - 1) * 100


def P(metric, path, label, unit, rng, noise, opc=None):
    return {"metric": metric, "path": path, "label": label, "unit": unit, "range": rng, "noise": noise, "opc": opc}


Q0 = V0 * AREA
points = [
    P("filter_state", "Filter.State", "Filter state (0 filtering, 1 backwash, 2 filter-to-waste, 3 standby)", "code", [0, 3], 0, "ISA-88 unit state"),
    P("flow_m3h", "Filter.Flow", "Filtered water flow (effluent magmeter)", "m3/h", [0, 900], 1.0, "haystack: water filter flow sensor"),
    P("flow_setpoint_m3h", "Filter.FlowSetpoint", "Flow setpoint (plant demand split)", "m3/h", [0, 900], 0, "haystack: water filter flow sp"),
    P("effluent_valve_pct", "Filter.EffluentValvePosition", "Effluent rate-control valve position", "%", [0, 100], 0.1, "haystack: valve sensor"),
    P("water_level_m", "Filter.WaterLevel", "Water depth above the media surface", "m", [0, 3], 0.003, "haystack: water level sensor"),
    P("headloss_media_m", "Media.HeadLoss", "Head loss across the media (piezometers top/bottom)", "m", [0, 4], 0.004),
    P("underdrain_dp_m", "Underdrain.HeadLoss", "Underdrain + I.M.S. cap head loss (media bottom to plenum)", "m", [0, 2], 0.002),
    P("headloss_total_m", "Filter.HeadLossTotal", "Total filter head loss (DP transmitter)", "m", [0, 4], 0.004),
    P("bed_pressure_head_m", "Media.InterfacePressureHead", "Pressure head at the anthracite/sand interface (piezometer)", "m", [-3, 4], 0.004),
    P("settled_turbidity_ntu", "Influent.Turbidity", "Settled (filter influent) water turbidity", "NTU", [0, 50], 0.02, "haystack: water turbidity sensor"),
    P("settled_turbidity_avg_ntu", "Influent.TurbidityRunAverage", "Settled turbidity, PLC average since the last backwash", "NTU", [0, 50], 0),
    P("effluent_turbidity_ntu", "Effluent.Turbidity", "Filtered water turbidity (individual filter turbidimeter)", "NTU", [0, 5], 0.003, "haystack: water turbidity sensor"),
    P("particle_count_ml", "Effluent.ParticleCount", "Filtered water particle count > 2 um", "1/mL", [0, 5000], 1.5),
    P("water_temp_c", "Influent.Temperature", "Water temperature", "degC", [0, 40], 0.03, "haystack: water temp sensor"),
    P("run_time_h", "Run.Time", "Filter run time since the last backwash", "h", [0, 100], 0),
    P("run_volume_m3", "Run.Volume", "Filtered volume since the last backwash (totaliser)", "m3", [0, 100000], 0),
    P("backwash_flow_m3h", "Backwash.Flow", "Backwash water flow", "m3/h", [0, 6000], 3.0),
    P("air_scour_nm3h", "Backwash.AirFlow", "Air scour flow", "Nm3/h", [0, 8000], 3.0),
    P("bed_expansion_pct", "Backwash.BedExpansion", "Media bed expansion during backwash (sonar)", "%", [0, 80], 0.15),
    P("bed_depth_m", "Media.BedDepth", "Settled media depth (sonar, filtering)", "m", [0, 1.5], 0.002),
    P("backwash_count", "Run.BackwashCount", "Backwashes since commissioning", "count", [0, 1e7], 0),
]

failure_modes = {
    "mudballs": {"label": "Mudballs / media fouling", "cause": "Incomplete backwashing leaves mud balls and coated grains: the clean bed loses porosity",
                 "detect": ["headloss_residual_m", "deposit_ratio"], "action": "Extended air scour backwash; inspect the bed (core sample), replace media if needed", "default_ramp_min": 6},
    "media_loss": {"label": "Anthracite loss", "cause": "Over-expansion during backwash carries anthracite over the wash troughs",
                   "detect": ["bed_depth_m", "headloss_residual_m"], "action": "Check backwash rate vs. water temperature, trough height; top up anthracite", "default_ramp_min": 6},
    "air_binding": {"label": "Air binding (negative head)", "cause": "Head loss in the anthracite exceeds the static head: dissolved air comes out and blocks pores",
                    "detect": ["bed_pressure_head_m", "headloss_residual_m"], "action": "Raise the water level over the media, backwash earlier, check for supersaturation", "default_ramp_min": 4},
    "short_circuiting": {"label": "Short-circuiting (cracks, wall channels)", "cause": "Cracks and wall separation let water bypass the media",
                         "detect": ["headloss_residual_m", "effluent_turbidity_ntu", "particle_count_ml"], "action": "Backwash with air scour, inspect wall gaps; filter to waste until stable", "default_ramp_min": 4},
    "underdrain_failure": {"label": "Underdrain / media retainer failure", "cause": "A broken lateral or I.M.S. cap: uneven backwash, boils, media in the clearwell",
                           "detect": ["underdrain_ratio", "expansion_ratio", "particle_count_ml"], "action": "Take the cell out of service; inspect laterals and caps", "default_ramp_min": 5},
    "valve_sticking": {"label": "Effluent control valve sticking", "cause": "Worn actuator or packing: the rate-control valve sticks and jumps, flow hunts",
                       "detect": ["flow_error_pct", "effluent_valve_pct"], "action": "Service the valve actuator and positioner; retune the level/flow loop", "default_ramp_min": 3},
    "coagulation_upset": {"label": "Coagulation upset (weak floc)", "cause": "Wrong coagulant dose or pH: fine floc penetrates deep, head loss climbs fast, early breakthrough",
                          "detect": ["deposit_ratio", "effluent_turbidity_ntu", "particle_count_ml"], "action": "Jar test; correct coagulant / polymer dose and pH; shorten runs", "default_ramp_min": 5},
    "turbidimeter_drift": {"label": "Turbidimeter fouling / drift", "cause": "Fouled flow cell or lamp drift: the turbidimeter reads high while the water is clean",
                           "detect": ["effluent_turbidity_ntu", "particle_count_ml"], "action": "Clean and recalibrate the turbidimeter (formazin / StablCal)", "default_ramp_min": 3},
}

twin = {
    "$comment": "Single source of truth for the FLT-1401 digital twin: rapid gravity dual-media filter cell (anthracite over sand) "
                "on a Xylem Leopold Universal Type S underdrain with I.M.S. cap, in the filter block of a conventional water "
                "treatment plant. Media per AWWA B100 (Clack anthracite / filter sand data); clean-bed head loss Carman-Kozeny, "
                "backwash expansion Richardson-Zaki with Ferguson-Church settling velocity.",
    "twin": {"id": "urn:maximo:twin:gravityfilter:FLT-1401", "version": "1.0.0",
             "kind": "Rapid gravity dual-media filter with head-loss, turbidity and backwash instrumentation",
             "standards": {
                 "media": "AWWA B100 filter media: anthracite ES 0.85-0.95 mm UC < 1.7 SG 1.6; sand ES 0.45-0.55 mm UC <= 1.6 SG 2.65",
                 "underdrain": "Leopold Universal Type S + I.M.S. cap: backwash <= 90 m/h, air scour <= 120 m/h",
                 "turbidity": "US EPA IESWTR: combined filter effluent <= 0.3 NTU (95 %), never > 1 NTU; individual filters monitored continuously",
                 "physics": "Carman-Kozeny clean-bed head loss, deposit head loss proportional to stored solids, Richardson-Zaki expansion",
                 "information_model": "Points named after ISA-88 unit states with Project Haystack tags"}},
    "identification": {"assetnum": "FLT-1401", "description": "Rapid gravity filter 14 cell 01 (dual media)",
                       "manufacturer": "Xylem Leopold", "model": "Universal Type S underdrain + I.M.S. cap, anthracite/sand",
                       "site": "BEDFORD", "location": "Filter block / cell 01", "medium": "Settled surface water"},
    "design": {
        "cell": {"area_m2": AREA, "length_m": 10.0, "width_m": 6.0, "water_depth_m": 1.5, "area_note": "assumed"},
        "media": {"anthracite": ANTH, "sand": SAND, "note": "depths, d_eq, porosity and sphericity assumed within AWWA B100 grades"},
        "underdrain": {"type": "Leopold Universal Type S, I.M.S. cap", "headloss_at_design_m": H_UD0, "headloss_note": "assumed",
                       "max_backwash_m_h": 90, "max_air_m_h": 120},
        "operation": {"rate_design_m_h": V0, "flow_design_m3h": Q0, "terminal_headloss_m": 2.4, "max_run_h": 36,
                      "breakthrough_backwash_ntu": 0.3, "ftw_min": 20, "available_head_range_m": [1.8, 3.0]},
        "backwash": {"rate_m_h": 55.0, "air_m_h": 60.0, "air_min": 4, "water_min": 8, "target_expansion_pct": 20,
                     "expansion_range_pct": [15, 30]},
        "hydraulics": {"mu20_pa_s": MU20, "rho": RHO, "clean_anthracite_m": round(H_ANTH0, 4), "clean_sand_m": round(H_SAND0, 4),
                       "clean_underdrain_m": H_UD0, "basis": "Carman-Kozeny at 8 m/h, 20 C; laminar media loss ~ v mu; underdrain ~ v^2"},
        "deposit": {"tss_per_ntu": 1.5, "k_m_per_kg_m2": 2.58, "anthracite_share": 0.7, "capacity_kg_m2": 1.10,
                    "note": "deposit head loss = k x stored solids x (v/v0) x (mu/mu20); capacity sets breakthrough (assumed)"},
        "settling": {"vt20_m_s": round(VT20, 5), "re20": round(RE20, 2), "n20": round(4.45 * RE20 ** -0.1, 3),
                     "expansion_at_design_pct": round(expansion(55.0), 1), "c1": 18.0, "c2": 1.0},
        "turbidity": {"effluent_goal_ntu": 0.1, "goal_note": "utility goal (assumed); regulatory 0.3 NTU 95 %, 1 NTU max",
                      "regulatory_ntu": 0.3, "max_ntu": 1.0},
        "demo": {"time_scale": 60, "note": "plant clock runs 60x real time: a 30 h filter run takes 30 min"},
    },
    "telemetry": {"event": "filter", "publish_every_s": 5, "device_type": "GRAVITY_FILTER",
                  "groups": {"Filter": "Filter cell", "Media": "Media bed", "Underdrain": "Underdrain", "Influent": "Settled water",
                             "Effluent": "Filtered water", "Run": "Run counters", "Backwash": "Backwash"},
                  "points": points},
    "twin_model": {"limits": {"headloss_residual_high_m": 0.15, "headloss_residual_low_m": -0.15, "deposit_ratio_alert": 1.6,
                              "deposit_ufrv_min_m": 30.0, "bed_depth_alert_m": 0.85, "pressure_head_alert_m": 0.0,
                              "underdrain_ratio_alert": 0.7, "expansion_ratio_alert": 0.7, "flow_error_alert_pct": 8.0,
                              "turbidity_alert_ntu": 0.3, "turbidity_warn_ntu": 0.15, "particles_breakthrough_ml": 100,
                              "particles_clean_ml": 50, "terminal_headloss_m": 2.4, "rate_min_m_h": 4.0}},
    "failure_modes": failure_modes,
    "presentation": {
        "category": "Gravity filter",
        "kpis": [{"metric": "flow_m3h", "label": "Flow", "unit": "m³/h", "decimals": 0},
                 {"metric": "headloss_total_m", "label": "Head loss", "unit": "m", "decimals": 2},
                 {"metric": "effluent_turbidity_ntu", "label": "Turbidity", "unit": "NTU", "decimals": 3},
                 {"metric": "run_time_h", "label": "Run time", "unit": "h", "decimals": 1}],
        "twin_kpis": [{"metric": "headloss_residual_m", "label": "Head loss vs. model", "unit": "m", "decimals": 2},
                      {"metric": "ufrv_m3_m2", "label": "UFRV", "unit": "m³/m²", "decimals": 0}],
        "compare": [
            {"label": "Media head loss", "measured": "headloss_media_m", "expected": "headloss_media_expected_m", "unit": "m", "decimals": 3,
             "basis": "Carman-Kozeny clean bed + deposit (k 2.58 m per kg/m²) at the live rate and temperature"},
            {"label": "Clean-bed head loss", "measured": None, "expected": "clean_bed_expected_m", "unit": "m", "decimals": 3,
             "basis": "anthracite 0.6 m + sand 0.3 m, Carman-Kozeny, viscosity at the water temperature"},
            {"label": "Underdrain head loss", "measured": "underdrain_dp_m", "expected": "underdrain_expected_m", "unit": "m", "decimals": 3,
             "basis": "0.12 m at 8 m/h, ~ v² (assumed)"},
            {"label": "Interface pressure head", "measured": "bed_pressure_head_m", "expected": None, "unit": "m", "decimals": 2, "basis": "< 0 = negative head, air binding"},
            {"label": "Filtration rate", "measured": "rate_m_h", "expected": None, "unit": "m/h", "decimals": 2, "basis": "design 8 m/h"},
            {"label": "Stored solids", "measured": "solids_load_kg_m2", "expected": None, "unit": "kg/m²", "decimals": 3, "basis": "UFRV x settled TSS (1.5 x NTU)"},
            {"label": "Bed expansion (backwash)", "measured": "bed_expansion_pct", "expected": "expansion_expected_pct", "unit": "%", "decimals": 1,
             "basis": "Richardson-Zaki, anthracite, at the live backwash rate and temperature"},
        ],
        "trends": [{"metric": "headloss_residual_m", "label": "Head loss vs. model (m)"}, {"metric": "effluent_turbidity_ntu", "label": "Effluent turbidity (NTU)"},
                   {"metric": "deposit_ratio", "label": "Deposit ratio"}, {"metric": "ufrv_m3_m2", "label": "UFRV (m³/m²)"}],
        "design": [
            {"label": "Cell", "value": "60 m², 8 m/h (480 m³/h), 1.5 m water over the media, terminal head loss 2.4 m (assumed)"},
            {"label": "Media", "value": "0.6 m anthracite ES 0.85-0.95 mm SG 1.6 over 0.3 m sand ES 0.45-0.55 mm SG 2.65 (AWWA B100)"},
            {"label": "Underdrain", "value": "Xylem Leopold Universal Type S + I.M.S. cap; backwash 55 m/h with 60 m/h air scour"},
            {"label": "Source", "value": "Leopold, Clack, Covia data; EPA IESWTR; 3D built from typical dimensions, not manufacturer CAD"},
        ],
    },
}

if __name__ == "__main__":
    out = HERE / "twin" / "flt-1401.twin.json"
    out.parent.mkdir(exist_ok=True)
    json.dump(twin, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("written", out)
    print(f"clean bed at 8 m/h 20 C: anthracite {H_ANTH0:.3f} m, sand {H_SAND0:.3f} m, underdrain {H_UD0:.3f} m")
    print(f"anthracite vt {VT20 * 3600:.0f} m/h Re {RE20:.1f}; expansion at 55 m/h {expansion(55):.1f} % (20 C), {expansion(55, 10):.1f} % (10 C), {expansion(55, 30):.1f} % (30 C)")
