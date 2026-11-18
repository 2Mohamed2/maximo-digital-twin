"""Write twin/tk-2701.twin.json: the crude oil storage tank twin (TK-2701).

    python build_twin.py

TK-2701 is an above-ground, vertical, cylindrical, welded steel tank (API 650) with an external floating roof, storing crude oil
in a terminal. It is gauged by a radar automatic tank gauge (ATG) with a second, independent radar for the overfill alarm
(for example an Emerson Rosemount 5900S 2-in-1 radar level gauge, instrument accuracy +/-0.5 mm), a multi-spot average
temperature and water level sensor, flow meters on the receipt and delivery lines, three roof position sensors and a gas
detector above the rim seal. Inspection results (shell and bottom thickness) come from the inspection records.

Sources and assumptions (every number below is either from a standard or labelled as an assumption in "source"):
  API MPMS Chapter 11.1 (Table 54A, generalised crude oils): VCF = exp(-a15 dT (1 + 0.8 a15 dT)), a15 = K0 / rho15^2, K0 = 613.9723.
  API MPMS Chapter 12.1.1 (static tank quantities): GOV = (TOV - FW) x CTSh - FRA, CTSh = 1 + 2 a dT + a^2 dT^2, GSV = GOV x VCF.
  API 2350 (overfill prevention): levels of concern CH, HH, MW; default minimum response time 30 min for a Category 2 tank.
  API 653 (tank inspection): shell t_min = 2.6 (H - 1) D G / (S E) [in, ft, psi]; S = min(0.80 Y, 0.429 T) for the bottom course;
    external UT interval = min(RCA / 2N, 15 years); bottom minimum remaining thickness at the next inspection 0.10 in (2.5 mm)
    when the bottom has no means to detect and contain a leak.
  Tank size, roof mass, plate grades, thicknesses, rates and alarm thresholds: ASSUMPTIONS of a typical terminal tank, to be
  replaced by the tank's calibration (strapping) table, data sheet, roof drawing and inspection reports.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with your tank data sheet / strapping table / inspection report"

# ---- design -------------------------------------------------------------------------------------------------------------
D_M, SHELL_H_M = 40.0, 18.0                      # inside diameter, shell height (assumption)
AREA = math.pi * D_M ** 2 / 4                    # m2 (constant cross-section: replaces the strapping table)
CH_M = 17.0                                      # critical high (assumption: roof seal reaches the shell top structures)
MAX_FILL_M3H, RT_MIN = 2500.0, 30.0              # largest receipt rate; API 2350 default minimum response time, Category 2
RISE_M = MAX_FILL_M3H / AREA * RT_MIN / 60       # level rise in one response time at the largest rate
HH_M = math.floor((CH_M - RISE_M) * 1000) / 1000
MW_M = math.floor((HH_M - RISE_M) * 1000) / 1000

# API 653 shell t_min of the first course (US customary units as in the standard)
Y_PSI, T_PSI, E, G = 38000.0, 70000.0, 1.0, 0.90
S_PSI = min(0.80 * Y_PSI, 0.429 * T_PSI)
D_FT, H_FT = D_M / 0.3048, CH_M / 0.3048
TMIN_IN = max(2.6 * (H_FT - 1) * D_FT * G / (S_PSI * E), 0.1)
TMIN_MM = round(TMIN_IN * 25.4, 2)

ROOF_MASS_KG, RIM_GAP_M = 90000.0, 0.20
ROOF_D = D_M - 2 * RIM_GAP_M

twin = {
    "$comment": "TK-2701 crude oil storage tank twin. Expected values in Maximo Monitor from the tank's design, calibration and inspection data; the device sends only what it measures.",
    "twin": {"id": "TK-2701", "name": "Crude oil storage tank TK-2701", "version": "1.0.0", "folder": "tank-twin"},
    "identification": {
        "asset": "TK-2701", "assetnum": "TK-2701", "manufacturer": "Field-erected welded steel tank (API 650) with external floating roof,",
        "model": "Radar tank gauging with 2-in-1 independent high-high level (for example Emerson Rosemount 5900S)",
        "description": "Crude oil storage tank in a terminal tank farm, external floating roof, 40 m x 18 m",
        "tank": "Vertical cylindrical welded steel tank, flat bottom, API 650, external floating pontoon roof (API 650 Annex C)",
        "gauge": "Radar automatic tank gauge on a still pipe, 2-in-1 housing: ATG + independent radar for the high-high alarm (for example Rosemount 5900S 2-in-1, instrument accuracy +/-0.5 mm)",
        "temperature": "Multi-spot average temperature and water level sensor with a temperature transmitter (for example Rosemount 765 + 2240S)",
        "roof": "Three non-contact roof position sensors at 120 degrees on the shell top, and a gas detector above the rim seal",
        "meters": "Receipt and delivery line flow meters with flow computers (volumes at 15 degC)",
    },
    "design": {
        "geometry": {
            "diameter_m": D_M, "shell_height_m": SHELL_H_M, "area_m2": round(AREA, 3),
            "strapping_base_temp_c": 15.0, "shell_alpha_per_c": 1.12e-5,
            "source": "Inside diameter and shell height: " + A + ". The twin uses a constant cross-section in place of the strapping table "
                      "(API MPMS Ch. 2.2A). Shell expansion coefficient of mild carbon steel 1.12e-5 per degC: assumption, typical value. "
                      "CTSh uses the liquid temperature for the shell (simplification; API MPMS 12.1.1 also weighs in the ambient air for an uninsulated tank).",
        },
        "product": {
            "name": "Crude oil", "density15_nominal": 850.0, "k0": 613.9723, "k1": 0.0, "temp_receipt_c": 38.0,
            "source": "K0 = 613.9723, K1 = 0: generalised crude oils, API MPMS Ch. 11.1 (Table 54A). Nominal density at 15 degC and receipt temperature: " + A,
        },
        "roof": {
            "type": "pontoon", "mass_kg": ROOF_MASS_KG, "rim_gap_m": RIM_GAP_M, "roof_diameter_m": ROOF_D,
            "roof_area_m2": round(math.pi * ROOF_D ** 2 / 4, 3), "rim_height_m": 0.90, "leg_height_m": 1.00,
            "source": "Roof mass (deck, pontoons, legs, seals), rim space, pontoon rim height and operating leg height: " + A + " (roof drawing and weight in the calibration report).",
        },
        "overfill": {
            "category": 2, "response_time_min": RT_MIN, "max_fill_m3h": MAX_FILL_M3H,
            "ch_m": CH_M, "hh_m": HH_M, "mw_m": MW_M, "low_working_m": 3.0,
            "source": "API 2350 levels of concern. CH (critical high): " + A + ". HH and MW: placed one response time apart at the largest fill rate "
                      f"({MAX_FILL_M3H:.0f} m3/h = {RISE_M * 1000:.0f} mm in {RT_MIN:.0f} min); 30 min is API 2350's default minimum response time for a Category 2 tank.",
        },
        "shell": {
            "course1_nominal_mm": 19.0, "y_psi": Y_PSI, "t_psi": T_PSI, "joint_efficiency": E, "design_sg": G,
            "allowable_psi": S_PSI, "tmin_mm": TMIN_MM, "ut_interval_cap_y": 15.0,
            "source": "API 653 t_min = 2.6 (H - 1) D G / (S E), H = CH, S = min(0.80 Y, 0.429 T) for the bottom course, never below 0.1 in; "
                      "external UT interval = min(RCA / 2N, 15 years). Plate grade (Y 38 ksi, T 70 ksi), joint efficiency 1.0, highest SG 0.90, nominal 19 mm: " + A,
        },
        "bottom": {
            "nominal_mm": 8.0, "tmin_next_mm": 2.54, "internal_interval_y": 10.0,
            "source": "API 653: minimum remaining bottom thickness at the next internal inspection 0.10 in (2.54 mm) for a bottom without means to "
                      "detect and contain a leak. Nominal plate 8 mm and a planned 10-year internal inspection interval: " + A,
        },
        "operation": {
            "receipt_m3h": 2000.0, "delivery_m3h": 1500.0, "settle_h": 8.0,
            "source": "Receipt by pipeline at 2000 m3/h up to MW, settling for 8 h, delivery at 1500 m3/h down to the low working level: " + A,
        },
        "demo": {"time_scale": 600,
                 "note": "Demo only: the plant clock runs 600 times faster (one real second = ten plant minutes), so one fill, settle, empty and settle cycle takes about three real minutes."},
    },
    "telemetry": {
        "event": "tank", "publish_every_s": 60, "device_type": "STORAGE_TANK_EFR",
        "groups": {"Gauge": "Automatic tank gauge and independent level", "Flow": "Line flow rates", "Movement": "Last completed movement (tank ticket)",
                   "Static": "Last completed quiet period", "Roof": "Floating roof and rim seal", "Inspection": "Last inspection results"},
        "points": [
            {"metric": "level_mm", "path": "Gauge.Level", "label": "Product level, ATG radar", "unit": "mm"},
            {"metric": "level2_mm", "path": "Gauge.LevelIndependent", "label": "Product level, independent radar (overfill)", "unit": "mm"},
            {"metric": "hh_switch", "path": "Gauge.HHAlarm", "label": "Independent high-high alarm (1 = active)", "unit": "code"},
            {"metric": "water_level_mm", "path": "Gauge.FreeWater", "label": "Free water level at the bottom", "unit": "mm"},
            {"metric": "product_temp_c", "path": "Gauge.Temperature", "label": "Average product temperature", "unit": "°C"},
            {"metric": "ambient_temp_c", "path": "Gauge.Ambient", "label": "Ambient air temperature", "unit": "°C"},
            {"metric": "density15_kgm3", "path": "Gauge.Density15", "label": "Product density at 15 °C (laboratory)", "unit": "kg/m³"},
            {"metric": "inflow_m3h", "path": "Flow.In", "label": "Receipt flow rate", "unit": "m³/h"},
            {"metric": "outflow_m3h", "path": "Flow.Out", "label": "Delivery flow rate", "unit": "m³/h"},
            {"metric": "mv_open_level_mm", "path": "Movement.OpenLevel", "label": "Opening gauge of the last movement", "unit": "mm"},
            {"metric": "mv_open_temp_c", "path": "Movement.OpenTemp", "label": "Opening temperature of the last movement", "unit": "°C"},
            {"metric": "mv_close_level_mm", "path": "Movement.CloseLevel", "label": "Closing gauge of the last movement", "unit": "mm"},
            {"metric": "mv_close_temp_c", "path": "Movement.CloseTemp", "label": "Closing temperature of the last movement", "unit": "°C"},
            {"metric": "mv_meter_m3", "path": "Movement.Metered", "label": "Metered volume of the last movement at 15 °C (+ in, − out)", "unit": "m³"},
            {"metric": "mv_hours", "path": "Movement.Hours", "label": "Duration of the last movement", "unit": "h"},
            {"metric": "st_open_level_mm", "path": "Static.OpenLevel", "label": "Level at the start of the last quiet period", "unit": "mm"},
            {"metric": "st_open_temp_c", "path": "Static.OpenTemp", "label": "Temperature at the start of the last quiet period", "unit": "°C"},
            {"metric": "st_close_level_mm", "path": "Static.CloseLevel", "label": "Level at the end of the last quiet period", "unit": "mm"},
            {"metric": "st_close_temp_c", "path": "Static.CloseTemp", "label": "Temperature at the end of the last quiet period", "unit": "°C"},
            {"metric": "st_hours", "path": "Static.Hours", "label": "Duration of the last quiet period", "unit": "h"},
            {"metric": "roof_h1_mm", "path": "Roof.Height1", "label": "Roof rim height above datum, sensor 1", "unit": "mm"},
            {"metric": "roof_h2_mm", "path": "Roof.Height2", "label": "Roof rim height above datum, sensor 2", "unit": "mm"},
            {"metric": "roof_h3_mm", "path": "Roof.Height3", "label": "Roof rim height above datum, sensor 3", "unit": "mm"},
            {"metric": "rim_gas_lel_pct", "path": "Roof.RimGas", "label": "Hydrocarbon gas above the rim seal", "unit": "% LEL"},
            {"metric": "shell_t_mm", "path": "Inspection.ShellThickness", "label": "Lowest shell thickness, first course, last UT survey", "unit": "mm"},
            {"metric": "shell_t_prev_mm", "path": "Inspection.ShellThicknessPrev", "label": "Same point, previous UT survey", "unit": "mm"},
            {"metric": "shell_years_between", "path": "Inspection.ShellYearsBetween", "label": "Years between the two UT surveys", "unit": "y"},
            {"metric": "years_since_ut", "path": "Inspection.YearsSinceUT", "label": "Years since the last UT survey", "unit": "y"},
            {"metric": "bottom_t_mm", "path": "Inspection.BottomThickness", "label": "Lowest bottom plate thickness, last floor scan", "unit": "mm"},
            {"metric": "bottom_t_prev_mm", "path": "Inspection.BottomThicknessPrev", "label": "Lowest bottom thickness, previous floor scan", "unit": "mm"},
            {"metric": "bottom_years_between", "path": "Inspection.BottomYearsBetween", "label": "Years between the two floor scans", "unit": "y"},
            {"metric": "years_since_internal", "path": "Inspection.YearsSinceInternal", "label": "Years since the last internal inspection", "unit": "y"},
        ],
    },
    "twin_model": {
        "limits": {
            "gauge_diff_alert_mm": 10.0, "meter_imbalance_pct": 0.3, "meter_min_volume_m3": 500.0,
            "static_loss_m3h": 0.4, "static_min_hours": 4.0, "roof_tilt_alert_mm": 100.0, "roof_draft_ratio_alert": 1.3,
            "roof_landing_margin_mm": 300.0, "rim_lel_alert_pct": 10.0, "bottom_rate_alert_mm_y": 0.2,
            "source": "Gauge disagreement 10 mm, tank-versus-meter 0.3 %, static loss 0.4 m3/h over at least 4 h, roof tilt 100 mm, roof draft 1.3 x expected, "
                      "300 mm above the landing height, 10 % LEL above the rim seal, bottom corrosion 0.2 mm/y: " + A,
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "overfill": {"name": "Receipt not stopped at the maximum working level", "part": "operation",
                     "symptoms": "level passes MW, time to HH shrinks, the independent high-high alarm trips the receipt",
                     "rules": ["TANK_OVERFILL_TIME", "TANK_LEVEL_HH", "TANK_LEVEL_CH"], "default_ramp_min": 0.5},
        "gauge_drift": {"name": "Radar gauge drift or still-pipe deposit", "part": "gauge",
                        "symptoms": "ATG and independent radar disagree", "rules": ["TANK_GAUGE_MISMATCH"], "default_ramp_min": 1},
        "bottom_leak": {"name": "Bottom leak", "part": "bottom", "symptoms": "net standard volume falls while the tank is quiet",
                        "rules": ["TANK_STATIC_LOSS"], "default_ramp_min": 0.5},
        "meter_error": {"name": "Flow meter over-reading", "part": "meter", "symptoms": "the tank level moves less than the meter says; quiet periods normal",
                        "rules": ["TANK_METER_IMBALANCE"], "default_ramp_min": 0.5},
        "roof_tilt": {"name": "Floating roof tilt (pontoon leak, seal binding)", "part": "roof", "symptoms": "roof sensors disagree, mean draft normal",
                      "rules": ["TANK_ROOF_TILT"], "default_ramp_min": 1},
        "roof_drain_blocked": {"name": "Roof drain blocked: water on the deck", "part": "roof", "symptoms": "roof floats deeper than its weight explains",
                               "rules": ["TANK_ROOF_LOW"], "default_ramp_min": 1},
        "rim_seal_damage": {"name": "Rim seal damage", "part": "seal", "symptoms": "hydrocarbon gas above the seal", "rules": ["TANK_RIM_GAS"], "default_ramp_min": 1},
        "bottom_corrosion": {"name": "Accelerated bottom corrosion", "part": "bottom", "symptoms": "floor scan shows a high corrosion rate; minimum thickness at the next inspection below the API 653 limit",
                             "rules": ["TANK_BOTTOM_RATE", "TANK_BOTTOM_MRT"], "default_ramp_min": 1.5},
    },
    "presentation": {"title": "TK-2701 crude oil storage tank", "dashboard": "STORAGE_TANK_EFR"},
}

out = HERE / "twin" / "tk-2701.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out, f"HH {HH_M} MW {MW_M} tmin {TMIN_MM} mm S {S_PSI} psi")
