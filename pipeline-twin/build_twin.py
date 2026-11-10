"""Build twin/pipe-1501.twin.json: PIPE-1501, a 14 km DN 1200 ductile iron water transmission main
(Saint-Gobain PAM NATURAL, class C25, cement-mortar lined) from a pumping station to a hilltop reservoir.

Sources (public, read 2026-11-10):
  Saint-Gobain PAM NATURAL ductile iron pipe data sheets (pamline.com): DN 1200, class C25, nominal iron wall thickness
    13.6 mm, outside diameter 1255 mm, mass 465.56 kg/m, laying length 8.19 m (reference NSC12H80AQ); same DN 1200 C25 /
    13.6 mm row in the NATURAL ZMU sheet (other coating, not used)
    https://www.pamline.com/sites/pamline/files/assets/datasheet/en/WZMSP19STD700_ZMUpipesDN350to1200withSTANDARDsocket_en.pdf
    Third-party EPD for the same pipe: DN 1200, 25 bar, 465.6 kg/m
    https://materials.oneclicklca.com/en/material/coated-steel-pressure-pipe-system-from-ductile-iron-for-drinking-and-raw-water-distribution/64c6963fbe11b61a4362e028
  EN 545 / ISO 2531 pressure terms (PFA allowable operating pressure without surge, PMA allowable maximum operating
    pressure including surge, PEA allowable site test pressure): UK Water Industry IGN 4-21-01
    https://water.org.uk/sites/default/files/wp/2018/11/ign-4-21-01.pdf
    Class C25 -> PFA 25 bar (the class number is the PFA); PMA = 1.2 PFA = 30 bar and PEA = PMA + 5 = 35 bar follow
    the EN 545 rule for pipes (UNVERIFIED for this exact row: PAM's sheet was not readable here).
  Hazen-Williams C = 140 for cement-mortar lined ductile iron (DIPRA flow tests, 97-year-old pipe still C 140):
    https://dipra.org/wp-content/uploads/2025/02/Flow-Test-of-97-Year-Old-Cement-Mortar-Lined-Pipe-English.pdf
    Design-table value C 140 up to DN 1200: https://www.ncrpb.nic.in/NCRBP%20ADB-TA%207055/repository/pdf/clause/table6.1.pdf
    Counterpoint (C declines with internal corrosion / tuberculation): https://www.uni-bell.org/portals/0/ResourceFile/ductile-iron-pipes-hazen-williams-flow-coefficient-declines-over-time.pdf
Physics references (textbook relations, not product data): Darcy-Weisbach with the Swamee-Jain explicit friction factor,
  Hazen-Williams (SI form), Joukowsky surge dp = rho a dv, Korteweg wave speed a = sqrt((K/rho) / (1 + K D / (E e))).
Assumptions (labelled in the twin): cement-mortar lining 6 mm (ISO 4179 band DN 700-1200, UNVERIFIED), internal diameter
  1255 - 2 x 13.6 - 2 x 6 = 1215.8 mm, design roughness k = 0.1 mm (lined pipe incl. joints), E ductile iron 170 GPa,
  route profile and elevations, pump station (3 x 2100 m3/h), surge vessel, sensor set, leak and valve locations.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).parent
OD, E_WALL, LINING = 1.255, 0.0136, 0.006
D = round(OD - 2 * E_WALL - 2 * LINING, 4)               # 1.2158 m
L = 14000.0
K_DESIGN_MM = 0.1
RHO, K_WATER, E_DI = 998.2, 2.19e9, 170e9
A_WAVE = round(math.sqrt(K_WATER / RHO / (1 + K_WATER * (OD - 2 * E_WALL) / (E_DI * E_WALL))), 1)

# route: chainage (m), ground/pipe elevation (m above datum), what is there
STATIONS = [
    {"id": "PT-0", "ch": 0.0, "z": 32.0, "name": "Pump station outlet (after FM-A)"},
    {"id": "PT-1", "ch": 3500.0, "z": 58.0, "name": "Chamber C-1"},
    {"id": "PT-2", "ch": 7000.0, "z": 71.0, "name": "Chamber C-2"},
    {"id": "PT-3", "ch": 10500.0, "z": 79.0, "name": "Chamber C-3"},
    {"id": "PT-4", "ch": 14000.0, "z": 124.0, "name": "Reservoir inlet chamber (before FM-B)"},
]
PROFILE = [[0, 32], [1200, 41], [2500, 52], [3500, 58], [4600, 74], [5600, 88], [6300, 80], [7000, 71], [8200, 66],
           [9500, 64], [10500, 79], [11800, 96], [13000, 112], [14000, 124]]
FEATURES = {"high_point": {"ch": 5600.0, "z": 88.0, "name": "High point HP-1 with air valve AV-3"},
            "line_valve": {"ch": 9500.0, "z": 64.0, "name": "Line valve LV-2 (DN 1200 butterfly, chamber)"},
            "leak_site": {"ch": 8200.0, "z": 66.0, "name": "Leak site used by the demo (between PT-2 and PT-3)"},
            "reservoir": {"floor_z": 126.0, "level_m": [3.0, 8.0], "name": "Hilltop reservoir R-15 (2 x 15,000 m3)"}}


def P(metric, path, label, unit, rng, noise, opc=None):
    return {"metric": metric, "path": path, "label": label, "unit": unit, "range": rng, "noise": noise, "opc": opc}


points = [
    P("flow_in_m3h", "Flow.Inlet", "Flow at the pump station (FM-A, electromagnetic)", "m3/h", [0, 9000], 4.0, "SCADA: FIT-A"),
    P("flow_out_m3h", "Flow.Outlet", "Flow into the reservoir (FM-B, electromagnetic)", "m3/h", [0, 9000], 4.0, "SCADA: FIT-B"),
    P("water_temp_c", "Water.Temperature", "Water temperature (FM-A)", "degC", [0, 45], 0.02, "SCADA: TT-A"),
    P("pressure_ps_bar", "Pressure.PT0", "Pressure at the pump station outlet (PT-0, ch 0.0 km)", "bar(g)", [-1, 40], 0.003, "SCADA: PIT-0"),
    P("pressure_pt1_bar", "Pressure.PT1", "Pressure at chamber C-1 (PT-1, ch 3.5 km)", "bar(g)", [-1, 40], 0.003, "SCADA: PIT-1"),
    P("pressure_pt2_bar", "Pressure.PT2", "Pressure at chamber C-2 (PT-2, ch 7.0 km)", "bar(g)", [-1, 40], 0.003, "SCADA: PIT-2"),
    P("pressure_pt3_bar", "Pressure.PT3", "Pressure at chamber C-3 (PT-3, ch 10.5 km)", "bar(g)", [-1, 40], 0.003, "SCADA: PIT-3"),
    P("pressure_res_bar", "Pressure.PT4", "Pressure at the reservoir inlet chamber (PT-4, ch 14.0 km)", "bar(g)", [-1, 40], 0.003, "SCADA: PIT-4"),
    P("reservoir_level_m", "Reservoir.Level", "Reservoir water level above the floor", "m", [0, 10], 0.005, "SCADA: LIT-R"),
    P("pumps_running", "PumpStation.Running", "Duty pumps running (3 x 2100 m3/h)", "count", [0, 3], 0, "SCADA: pump status"),
    P("surge_pmax_bar", "Transient.PumpStationMax", "Highest pressure at the pump station in the last minute (1 kHz logger)", "bar(g)", [-1, 60], 0.01,
      "High-rate pressure logger at PT-0"),
    P("surge_pmin_hp_bar", "Transient.HighPointMin", "Lowest pressure at high point HP-1 in the last minute (1 kHz logger)", "bar(g)", [-1, 40], 0.01,
      "High-rate pressure logger at HP-1 (AV-3)"),
    P("line_valve_pos_pct", "Valves.LV2Position", "Line valve LV-2 position (limit switch / indicator)", "%", [0, 100], 0, "SCADA: ZT-LV2"),
]

failure_modes = {
    "leak": {"label": "Leak / burst (between PT-2 and PT-3)", "cause": "A failed joint or a cracked barrel lets water out at about km 8.2: less water arrives than leaves the pump station, and downstream of the leak the line carries less flow, so the hydraulic grade line flattens there",
             "detect": ["imbalance_pct", "res_out_bar", "leak_signal_bar", "slope_ratio_4", "leak_ch_km"], "action": "Dispatch a leak crew to the estimated chainage; confirm with acoustic correlation; isolate between LV-2 and the nearest chamber for repair", "default_ramp_min": 2},
    "tuberculation": {"label": "Roughness growth (lining damage, tuberculation)", "cause": "Damaged lining exposes iron; corrosion nodules and biofilm make the wall rougher: the whole line loses more head for the same flow, and the effective Hazen-Williams C falls",
                      "detect": ["c_effective", "k_effective_mm", "headloss_ratio"], "action": "Plan a CCTV / pig inspection; swab or reline the affected sections; review water chemistry (Langelier index)", "default_ramp_min": 3},
    "air_pocket": {"label": "Air pocket at high point HP-1 (air valve AV-3 blocked)", "cause": "The air valve at the high point no longer vents: an air pocket narrows the flow section and adds a local head loss between PT-1 and PT-2",
                   "detect": ["slope_ratio_2", "res_pt2_bar"], "action": "Inspect and clean air valve AV-3 (float stuck, orifice blocked); vent the high point", "default_ramp_min": 2},
    "valve_throttled": {"label": "Line valve LV-2 partly closed", "cause": "The line valve at km 9.5 was left partly closed after maintenance (its indicator still says open): a local head loss appears between PT-2 and PT-3",
                        "detect": ["slope_ratio_3", "res_pt3_bar", "line_valve_pos_pct"], "action": "Check LV-2 on site, open it fully and repair the position indicator", "default_ramp_min": 2},
    "meter_drift": {"label": "Flow meter FM-B drift", "cause": "The reservoir inlet meter reads low (electrode fouling or a lost calibration): the mass balance opens up, but the pressures along the line show no leak",
                    "detect": ["imbalance_pct", "res_out_bar", "leak_signal_bar"], "action": "Verify FM-B against a clamp-on meter or the reservoir level change; clean electrodes and recalibrate", "default_ramp_min": 2},
    "surge_protection": {"label": "Surge vessel failure (pump-trip transients)", "cause": "The surge vessel at the pump station lost its air charge (bladder or compressor fault): every pump trip now sends a near-Joukowsky pressure wave down the line, above PFA at the station and down to vapour pressure at the high point",
                         "detect": ["surge_pmax_bar", "surge_pmin_hp_bar", "joukowsky_bar"], "action": "Restore the surge vessel charge; check the non-return valves; avoid pump starts/stops until fixed", "default_ramp_min": 1},
    "transmitter_fault": {"label": "Pressure transmitter PT-2 drift", "cause": "PT-2 drifts high (diaphragm or zero shift): the head loss looks too small upstream of it and too large downstream, a pattern no hydraulic fault makes",
                          "detect": ["slope_ratio_2", "slope_ratio_3", "res_pt2_bar"], "action": "Check PT-2 against a test gauge; recalibrate or replace", "default_ramp_min": 2},
}

twin = {
    "$comment": "Single source of truth for the PIPE-1501 digital twin: 14 km DN 1200 ductile iron transmission main, Saint-Gobain PAM "
                "NATURAL class C25, cement-mortar lined, pumping to a hilltop reservoir. Pipe data from the PAM data sheets; hydraulics "
                "Darcy-Weisbach / Swamee-Jain, Hazen-Williams as the utility check; transients Joukowsky.",
    "twin": {"id": "urn:maximo:twin:transmissionmain:PIPE-1501", "version": "1.0.0",
             "kind": "Water transmission main with flow meters at both ends, pressure transmitters along the route and transient loggers",
             "standards": {
                 "performance": f"Saint-Gobain PAM NATURAL DN 1200 C25: OD 1255 mm, iron wall 13.6 mm, 465.56 kg/m; PFA 25 / PMA 30 / PEA 35 bar (EN 545)",
                 "hydraulics": "Darcy-Weisbach hf = f L/D v^2/2g, Swamee-Jain f = 0.25 / log10(k/3.7D + 5.74/Re^0.9)^2; Hazen-Williams C (SI) as check",
                 "transients": f"Joukowsky dp = rho a dv, Korteweg wave speed a = {A_WAVE} m/s for DN 1200 C25 ductile iron (computed)",
                 "information_model": "Points named after the SCADA tags of the line (FIT, PIT, LIT, ZT)"}},
    "identification": {"assetnum": "PIPE-1501", "description": "Transmission main 1501 (pump station PS-15 to reservoir R-15)",
                       "manufacturer": "Saint-Gobain PAM", "model": "NATURAL DN 1200 C25 ductile iron, cement-mortar lined",
                       "site": "BEDFORD", "location": "PS-15 to R-15, 14.0 km", "medium": "Treated drinking water"},
    "design": {
        "pipe": {"dn": 1200, "od_m": OD, "wall_iron_m": E_WALL, "lining_m": LINING, "id_m": D, "class": "C25", "material": "ductile iron EN 545",
                 "mass_kg_m": 465.56, "laying_length_m": 8.19, "pfa_bar": 25.0, "pma_bar": 30.0, "pea_bar": 35.0,
                 "lining_note": "cement-mortar lining 6 mm assumed (ISO 4179 band DN 700-1200, unverified)",
                 "pressure_note": "PMA = 1.2 PFA and PEA = PMA + 5 bar per the EN 545 rule; not read from the PAM row"},
        "hydraulics": {"length_m": L, "k_design_mm": K_DESIGN_MM, "c_design_hw": 140, "rho_kg_m3": RHO, "g": 9.80665,
                       "bar_per_m": round(RHO * 9.80665 / 1e5, 6),
                       "viscosity": "nu = 1.792e-6 / (1 + 0.0337 T + 0.000221 T^2) m2/s (Poiseuille fit)",
                       "k_note": "k = 0.1 mm for a lined pipe including joints and bends (assumption); DIPRA flow tests give C ~ 140"},
        "transients": {"wave_speed_ms": A_WAVE, "k_water_pa": K_WATER, "e_iron_pa": E_DI, "surge_vessel_factor": 0.22,
                       "note": "With a working surge vessel a pump trip raises the pressure by about 22 % of Joukowsky (assumed); a failed vessel lets almost the full Joukowsky through"},
        "route": {"stations": STATIONS, "profile": PROFILE, "features": FEATURES, "pumps": {"count": 3, "q_each_m3h": 2100}},
        "meters": {"uncertainty_pct": 0.5, "note": "electromagnetic flow meters, +-0.5 % of reading each (typical)"},
        "demo": {"time_scale": 60, "note": "The plant clock runs 60x real time (one day in 24 min): the pump schedule (3 pumps at night, 2 by day, "
                                           "1 in the evening peak) changes several times per real hour; injected faults ramp in 1-3 min."},
    },
    "telemetry": {"event": "pipeline", "publish_every_s": 5, "device_type": "TRANSMISSION_MAIN",
                  "groups": {"Flow": "Flow meters FM-A / FM-B", "Water": "Water quality at FM-A", "Pressure": "Pressure transmitters PT-0..PT-4",
                             "Reservoir": "Reservoir R-15", "PumpStation": "Pump station PS-15", "Transient": "High-rate pressure loggers",
                             "Valves": "Line valve LV-2"},
                  "points": points},
    "twin_model": {"limits": {"q_min_m3h": 1500, "imbalance_alert_pct": 1.5, "meter_drift_imbalance_pct": 2.0, "leak_split": 0.42, "leak_signal_min_bar": 0.035,
                              "slope_neighbour_min": 0.8, "c_effective_alert": 125, "slope_dev_alert": 0.6, "slope_low": 0.5,
                              "pfa_bar": 25.0, "vacuum_alert_bar": -0.5}},
    "failure_modes": failure_modes,
    "presentation": {
        "category": "Transmission main",
        "kpis": [{"metric": "flow_in_m3h", "label": "Flow in", "unit": "m³/h", "decimals": 0},
                 {"metric": "pressure_ps_bar", "label": "PS outlet", "unit": "bar", "decimals": 2},
                 {"metric": "pressure_res_bar", "label": "Reservoir inlet", "unit": "bar", "decimals": 2},
                 {"metric": "pumps_running", "label": "Pumps", "unit": "", "decimals": 0}],
        "twin_kpis": [{"metric": "imbalance_pct", "label": "Mass balance", "unit": "%", "decimals": 2},
                      {"metric": "c_effective", "label": "Effective C", "unit": "", "decimals": 0}],
        "compare": [
            {"label": "Head loss PS -> reservoir", "measured": "headloss_measured_m", "expected": "headloss_expected_m", "unit": "m", "decimals": 2,
             "basis": "Darcy-Weisbach / Swamee-Jain at the inlet flow, k 0.1 mm, D 1.216 m, L 14 km"},
            {"label": "Pressure PT-1 (km 3.5)", "measured": "pressure_pt1_bar", "expected": "p_exp_pt1_bar", "unit": "bar", "decimals": 3, "basis": "PT-0 + elevation - friction at the inlet flow"},
            {"label": "Pressure PT-2 (km 7.0)", "measured": "pressure_pt2_bar", "expected": "p_exp_pt2_bar", "unit": "bar", "decimals": 3, "basis": "PT-0 + elevation - friction at the inlet flow"},
            {"label": "Pressure PT-3 (km 10.5)", "measured": "pressure_pt3_bar", "expected": "p_exp_pt3_bar", "unit": "bar", "decimals": 3, "basis": "PT-0 + elevation - friction at the inlet flow"},
            {"label": "Pressure PT-4 (reservoir inlet)", "measured": "pressure_res_bar", "expected": "p_exp_res_bar", "unit": "bar", "decimals": 3, "basis": "PT-0 + elevation - friction at the inlet flow"},
            {"label": "Flow out vs. in", "measured": "flow_out_m3h", "expected": "flow_in_m3h", "unit": "m³/h", "decimals": 0, "basis": "mass balance, meters +-0.5 % each"},
            {"label": "Hazen-Williams C", "measured": "c_effective", "expected": "c_design", "unit": "", "decimals": 1, "basis": "from the measured head loss vs. the design pipe"},
            {"label": "Potential surge (Joukowsky)", "measured": "joukowsky_bar", "expected": None, "unit": "bar", "decimals": 1, "basis": f"rho a v, a = {A_WAVE} m/s"},
        ],
        "trends": [{"metric": "imbalance_pct", "label": "Mass balance (%)"}, {"metric": "c_effective", "label": "Effective C"},
                   {"metric": "res_out_bar", "label": "Outlet residual (bar)"}, {"metric": "surge_pmax_bar", "label": "Surge max (bar)"}],
        "design": [
            {"label": "Pipe", "value": "Saint-Gobain PAM NATURAL DN 1200 C25 ductile iron, OD 1255 mm, wall 13.6 mm, cement-mortar lined, 465.56 kg/m"},
            {"label": "Pressures", "value": "PFA 25 / PMA 30 / PEA 35 bar (EN 545 class C25)"},
            {"label": "Line", "value": "14.0 km, PS-15 (32 m) to reservoir R-15 (floor 126 m), high point 88 m at km 5.6; 3 x 2100 m³/h pumps"},
            {"label": "Source", "value": "PAM data sheets (DN 1200 C25 row); 3D built from the route and pipe dimensions, not manufacturer CAD"},
        ],
    },
}

if __name__ == "__main__":
    out = HERE / "twin" / "pipe-1501.twin.json"
    out.parent.mkdir(exist_ok=True)
    json.dump(twin, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("written", out, "D", D, "a", A_WAVE)
