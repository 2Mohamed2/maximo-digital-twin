"""Write twin/sp-4101.twin.json: the centrifugal slurry pump twin (SP-4101).

    python build_twin.py

SP-4101 pumps flotation tailings from the tailings sump of a mineral processing plant to the thickener through a
long steel discharge line. It is a horizontal, rubber-lined, end-suction centrifugal slurry pump of the Warman AH range
(size 8/6: 8 in suction, 6 in discharge) with an adjustable throatbush, a water-flushed packed gland and grease-lubricated
roller bearings, driven through a variable speed drive (VSD) that holds the sump level.

Sources and assumptions (every number below is either published or labelled as an assumption in "source"):
  Weir Minerals, Warman horizontal slurry pump brochure: AH range for "highly abrasive/dense slurries in processes from
    cyclone feed to regrind, flotation and tailings", rubber or alloy bolt-in liners, adjustable throatbush, WRT impeller
    and throatbush; the 8/6 envelope of the AH quick selection guide (approximate clear water performance) reaches about
    73 m of head and roughly 300 to 1,100 m3/h. The CURVE OF THIS PUMP (shut-off head, BEP, efficiency, NPSHr) is an
    ASSUMPTION drawn inside that envelope: replace it with the Weir curve sheet of your pump.
  Warman (Walker) slurry correction, as implemented in AFT Impulse (docs.aft.com, Slurry Pump De-rating, Warman method):
      HR = 1 - 0.000385 (Ss - Sf) (1 + 4/Ss) Cm ln(d50 / 0.0227),  d50 in mm, Cm = solids by mass in %
    used here without its impeller-size correction; the efficiency ratio is taken equal to HR (common practice, assumption).
  Durand limit deposit velocity: VL = FL sqrt(2 g D (Ss - 1)) (textbook); FL is an ASSUMPTION read from the Durand chart.
  Gland water: one maker's published figure for a flushed gland (McLanahan H-type): 1-5 gpm (0.2-1 m3/h) at 3-5 psi
    (20-25 kPa) above pump discharge pressure. Used as typical practice; take your own pump manual's figure.
  Everything else (line, motor, bearings, vibration, limits): ASSUMPTIONS of a typical installation, labelled below.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with "
BRO = ("Weir Minerals, Warman horizontal slurry pump brochure (AH range, quick selection guide), "
       "https://global.weir/globalassets/resources/product-pdfs/warman/warman-horizontal-slurry-pump-brochure.pdf")
AFT = "AFT Impulse documentation, Slurry Pump De-rating (Warman method), https://docs.aft.com/impulse10/Slurry_Pump_De_rating.html"

LINE_ID = 0.254
K_FRIC = 18.0 / 700.0 ** 2          # m of slurry per (m3/h)^2: 18 m of friction at the 700 m3/h duty

twin = {
    "$comment": "SP-4101 slurry pump twin. Expected values in Maximo Monitor from the pump's clear-water curve, a published slurry correction and the line design; the device sends only what it measures.",
    "twin": {"id": "SP-4101", "name": "Tailings slurry pump SP-4101", "version": "1.0.0", "folder": "slurry-twin"},
    "identification": {
        "asset": "SP-4101", "assetnum": "SP-4101", "manufacturer": "Weir Minerals",
        "model": "Warman 8/6 AH, rubber lined (curve: assumption inside the published AH 8/6 envelope)",
        "description": "Flotation tailings pump, tailings sump to thickener, on a variable speed drive",
        "pump": "Horizontal end-suction centrifugal slurry pump, Warman AH range, size 8/6 (8 in suction, 6 in discharge)",
        "wet_end": "Natural rubber liners (frame plate liner, cover plate liner), closed impeller, adjustable throatbush",
        "seal": "Packed gland with clean flushing water (full-flow gland)",
        "bearings": "Grease-lubricated roller bearing cartridge, drive end (DE) and non-drive end (NDE)",
        "drive": "Variable speed drive and induction motor through a V-belt drive; the VSD holds the sump level",
    },
    "design": {
        "pump": {
            "ref_speed_rpm": 1000.0, "impeller_mm": 550.0,
            "head_coef": [50.0, 0.0, -50.0 * 0.16 / 900.0 ** 2],
            "q_bep_m3h": 900.0, "eff_bep": 0.75,
            "npshr_coef": [2.0, 2.5],
            "max_speed_rpm": 1150.0,
            "source": BRO + ". Range, duty class and the adjustable throatbush are from the brochure. head_coef: clear-water head "
                      "H = a + b Q + c Q^2 (m, m3/h) at ref_speed_rpm, shut-off 50 m, BEP 900 m3/h at 42 m and 75 % efficiency; "
                      "efficiency = eff_bep x (2x - x^2) with x = Q / Q_BEP; NPSHr = (r0 + r2 x^2) m: " + A + "the Weir curve sheet "
                      "of your pump (impeller, speed, NPSHr). Affinity laws (Q ~ n, H ~ n^2): textbook.",
        },
        "slurry": {
            "solids_sg": 2.70, "d50_um": 100.0, "cw_design_pct": 45.0, "sg_max": 1.50, "carrier_sg": 1.0,
            "warman_k": 0.000385,
            "source": AFT + ". Warman correction HR = 1 - 0.000385 (Ss - Sf)(1 + 4/Ss) Cm ln(d50/0.0227), d50 in mm, Cm in % by "
                      "mass; ER = HR (assumption). Solids SG 2.70 (silicate tailings), d50 100 um, 45 % solids by mass, maximum "
                      "mixture SG 1.50: " + A + "your metallurgical design criteria and the lab results.",
        },
        "line": {
            "id_m": LINE_ID, "length_m": 1500.0, "static_head_m": 12.0, "friction_k": K_FRIC, "durand_fl": 1.05,
            "sump_level_m": 2.3,
            "source": A + "the line design: 10 in steel line (ID 254 mm), 1.5 km to the thickener, 12 m static lift, 18 m friction "
                      "at 700 m3/h, sump level 2.3 m above the pump centreline. Durand FL = 1.05 read from the Durand chart for "
                      "fine sand at this concentration (assumption); VL = FL sqrt(2 g D (Ss - 1)).",
        },
        "drive": {"motor_kw": 200.0, "drive_eff": 0.94,
                  "source": A + "the motor nameplate and the VSD data (motor x VSD x belt efficiency at this load)."},
        "site": {"patm_kpa": 101.3, "vapour_kpa": 3.17, "slurry_temp_c": 25.0,
                 "source": "Vapour pressure of water at 25 °C, 3.17 kPa: steam tables. Atmospheric pressure 101.3 kPa (sea level): "
                           + A + "the value at your plant's altitude."},
        "gland": {"flow_nominal_lpm": 10.0, "flow_min_lpm": 4.0, "flow_max_lpm": 25.0, "dp_min_kpa": 20.0, "supply_kpa": 560.0,
                  "source": "Flushed gland: 1-5 gpm (0.2-1 m3/h) at 3-5 psi (20-25 kPa) above pump discharge pressure, McLanahan "
                            "slurry pump page (H-type gland), https://www.mclanahan.com/products/slurry-pumps; used as typical "
                            "practice. Nominal 10 L/min and the alarm band 4-25 L/min: " + A + "your pump manual."},
        "operation": {"flow_setpoint_m3h": 700.0, "hours_since_adjust_start": 600.0,
                      "source": A + "the plant's tailings flow at design throughput and the date of the last throatbush adjustment."},
        "demo": {"time_scale": 60, "note": "Demo only: the plant clock runs 60 times faster, so the hours since the last impeller adjustment grow quickly."},
    },
    "telemetry": {
        "event": "slurry", "publish_every_s": 10, "device_type": "SLURRY_PUMP_VSD",
        "groups": {"VSD": "Variable speed drive", "Process": "Flow, density and pressures", "Lab": "Last lab sample of the tailings",
                   "Gland": "Gland flushing water", "Bearing": "Bearing housing", "Wear": "Wet end history"},
        "points": [
            {"metric": "running", "path": "VSD.Running", "label": "Pump running (1 = yes)", "unit": "code"},
            {"metric": "speed_rpm", "path": "VSD.PumpSpeed", "label": "Pump speed (VSD speed / belt ratio)", "unit": "rpm"},
            {"metric": "motor_kw", "path": "VSD.OutputPower", "label": "VSD output power", "unit": "kW"},
            {"metric": "flow_m3h", "path": "Process.Flow", "label": "Discharge flow (magnetic flow meter)", "unit": "m³/h"},
            {"metric": "density_sg", "path": "Process.Density", "label": "Slurry density (SG, density gauge)", "unit": "SG"},
            {"metric": "suction_kpa", "path": "Process.SuctionPressure", "label": "Suction pressure", "unit": "kPa g"},
            {"metric": "discharge_kpa", "path": "Process.DischargePressure", "label": "Discharge pressure", "unit": "kPa g"},
            {"metric": "d50_um", "path": "Lab.D50", "label": "Median particle size d50, last sample", "unit": "µm"},
            {"metric": "gland_flow_lpm", "path": "Gland.Flow", "label": "Gland water flow", "unit": "L/min"},
            {"metric": "gland_kpa", "path": "Gland.Pressure", "label": "Gland water pressure", "unit": "kPa g"},
            {"metric": "bearing_de_c", "path": "Bearing.TempDE", "label": "Bearing temperature, drive end", "unit": "°C"},
            {"metric": "bearing_nde_c", "path": "Bearing.TempNDE", "label": "Bearing temperature, non-drive end", "unit": "°C"},
            {"metric": "vibration_mms", "path": "Bearing.Vibration", "label": "Bearing housing vibration (RMS velocity)", "unit": "mm/s"},
            {"metric": "ambient_c", "path": "Bearing.Ambient", "label": "Ambient temperature at the pump", "unit": "°C"},
            {"metric": "hours_since_adjust", "path": "Wear.HoursSinceAdjust", "label": "Running hours since the last impeller / throatbush adjustment", "unit": "h"},
        ],
    },
    "twin_model": {
        "limits": {
            "head_low": 0.93, "head_loss": 0.85, "wear_rate_pct_kh": 5.0, "wear_min_hours": 200.0,
            "bep_min": 0.70, "bep_max": 1.15, "deposition_margin": 1.10, "npsh_margin": 1.3,
            "bearing_rise_k": 45.0, "vibration_mms": 7.1,
            "source": A + "your own operating practice and the vendor's allowable operating region (see the %BEP limits of your "
                      "edition of ANSI/HI 12.1-12.6). Head ratio 0.93 / 0.85 of the derated curve, 5 % head lost per 1,000 h, 70 to "
                      "115 % of BEP flow, line velocity 10 % above the Durand limit, NPSH margin 1.3, bearing 45 K above ambient, 7.1 mm/s.",
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "impeller_wear": {"name": "Impeller and throatbush wear (gap opens)", "part": "wet end",
                          "symptoms": "head down at the same speed and flow, the VSD speeds up to hold the flow, efficiency and margin to motor rating fall",
                          "rules": ["SLY_HEAD_LOW", "SLY_HEAD_LOSS_HIGH", "SLY_WEAR_RATE_HIGH"], "default_ramp_min": 1.5},
        "line_sanding": {"name": "Low throughput, line sanding", "part": "discharge line",
                         "symptoms": "flow falls below the deposition velocity, a bed forms, friction rises, pump far left of BEP",
                         "rules": ["SLY_DEPOSITION_MARGIN", "SLY_DEPOSITION_RISK", "SLY_BEP_LOW"], "default_ramp_min": 1.5},
        "suction_blockage": {"name": "Suction blocked (tramp, rubber, scale in the suction spool)", "part": "suction",
                             "symptoms": "suction pressure falls, NPSH available falls towards NPSH required",
                             "rules": ["SLY_NPSH_LOW"], "default_ramp_min": 1},
        "gland_water_loss": {"name": "Gland water lost (pump, strainer, valve)", "part": "gland",
                             "symptoms": "gland water pressure below discharge pressure, flow low: slurry enters the packing",
                             "rules": ["SLY_GLAND_PRESSURE_LOW", "SLY_GLAND_FLOW_LOW"], "default_ramp_min": 0.5},
        "packing_wear": {"name": "Gland packing or shaft sleeve worn", "part": "gland",
                         "symptoms": "gland water flow far above normal at normal pressure", "rules": ["SLY_GLAND_FLOW_HIGH"], "default_ramp_min": 1},
        "bearing_failure": {"name": "Bearing damage (contamination, lubrication)", "part": "bearings",
                            "symptoms": "drive-end bearing hotter than ambient explains, vibration up", "rules": ["SLY_BEARING_TEMP_HIGH", "SLY_VIBRATION_HIGH"],
                            "default_ramp_min": 1},
        "density_high": {"name": "Slurry density above design (thickener underflow or mill upset)", "part": "process",
                         "symptoms": "SG above the design maximum, slurry correction lower, discharge pressure up",
                         "rules": ["SLY_DENSITY_HIGH"], "default_ramp_min": 1},
    },
    "presentation": {"title": "SP-4101 tailings slurry pump", "dashboard": "SLURRY_PUMP_VSD"},
}

vl = twin["design"]["line"]["durand_fl"] * math.sqrt(2 * 9.80665 * LINE_ID * (twin["design"]["slurry"]["solids_sg"] - 1))
twin["design"]["line"]["note"] = f"Durand limit deposit velocity for this line: {vl:.2f} m/s"

out = HERE / "twin" / "sp-4101.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
