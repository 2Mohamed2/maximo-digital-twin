"""Write twin/e-2501.twin.json: the shell-and-tube heat exchanger twin (E-2501).

    python build_twin.py

E-2501 is a crude / kerosene exchanger at the cold end of a refinery crude preheat train: hot kerosene product from the
crude column (shell side) heats the crude from the tank farm (tube side) before the desalter. TEMA type AES (front head A:
channel with removable cover, shell E: one pass, rear head S: floating head with backing device), four tube passes.

Sources and assumptions (every number below is either from a published source or labelled as an assumption in "source"):
  Process duty and geometry: D. Q. Kern, Process Heat Transfer (McGraw-Hill, 1950), Example 7.3 "Calculation of a
  kerosene-crude oil exchanger": 43,800 lb/h of 42 API kerosene, 390 -> 200 F; 149,000 lb/h of 34 API crude, 100 -> 170 F;
  cp 0.605 and 0.49 Btu/lb F; 21 1/4 in ID shell, 158 tubes 1 in OD, 16 ft long, 1 1/4 in square pitch, 4 tube passes,
  baffles 5 in apart; 10 psi pressure drop allowed on each side; combined dirt factor 0.003 h ft2 F/Btu. Converted to SI here.
  Formulas: LMTD with the F correction for one shell pass and an even number of tube passes (Bowman, Mueller and Nagle
  1940, as used in the TEMA standards and heat transfer textbooks), effectiveness-NTU for the same arrangement, fouling
  resistance Rf = 1/U_actual - 1/U_clean, Kern's shell-side correlation (h ~ Re^0.55), turbulent tube side (h ~ Re^0.8),
  pressure drop ~ flow^1.8.
  Film coefficients, clean pressure drops, line pressures, crude density, product colour and all money figures:
  ASSUMPTIONS of a typical size, to be replaced by the values on your own exchanger data sheet (HTRI / HTFS rating) and
  your own fuel price and furnace efficiency.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with your exchanger data sheet / rating run"
KERN = "Kern, Process Heat Transfer, Example 7.3 (kerosene-crude oil exchanger), converted to SI"

LB, IN, FT = 0.45359237, 0.0254, 0.3048
F2C = lambda f: round((f - 32) / 1.8, 2)
BTU_LBF = 4.1868                       # 1 Btu/(lb F) = 4.1868 kJ/(kg K)
RD_SI = 0.17611                        # 1 h ft2 F/Btu = 0.17611 m2 K/W

n_tubes, od_in, l_ft, passes = 158, 1.0, 16.0, 4
id_in = 0.81                           # 1 in OD 13 BWG tube, ID 0.81 in (Kern Table 10)
area = round(n_tubes * math.pi * od_in * IN * l_ft * FT, 2)
flow_area = round(n_tubes / passes * math.pi / 4 * (id_in * IN) ** 2, 6)

twin = {
    "$comment": "E-2501 crude / kerosene exchanger twin. Expected values in Maximo Monitor from the exchanger data sheet; the device sends only what it measures.",
    "twin": {"id": "E-2501", "name": "Crude / kerosene exchanger E-2501", "version": "1.0.0", "folder": "hex-twin"},
    "identification": {
        "asset": "E-2501", "assetnum": "E-2501", "manufacturer": "Shell-and-tube exchanger built to TEMA class R and API 660,",
        "model": "TEMA size 21-192 type AES (21 1/4 in shell, 16 ft tubes, 4 tube passes)",
        "description": "Crude / kerosene product exchanger, cold end of the crude preheat train (crude in the tubes, kerosene in the shell)",
        "front_head": "A: channel with removable cover (tube side can be cleaned without breaking the piping)",
        "shell": "E: one-pass shell, single segmental baffles",
        "rear_head": "S: floating head with backing device (bundle can be pulled for cleaning)",
        "service": "Tube side: crude oil from the tank farm to the desalter. Shell side: kerosene product from the crude column side stripper to rundown.",
    },
    "design": {
        "process": {
            "crude_flow_t_h": round(149000 * LB / 1000, 3), "crude_in_c": F2C(100), "crude_out_c": F2C(170),
            "crude_cp_kj_kgk": round(0.49 * BTU_LBF, 4), "crude_api": 34,
            "kero_flow_t_h": round(43800 * LB / 1000, 3), "kero_in_c": F2C(390), "kero_out_c": F2C(200),
            "kero_cp_kj_kgk": round(0.605 * BTU_LBF, 4), "kero_api": 42,
            "crude_density_kg_m3": 830.0,
            "source": KERN + ". Crude density at the mean tube-side temperature: " + A,
        },
        "geometry": {
            "tema_type": "AES", "tema_size": "21-192", "shell_id_mm": round(21.25 * 25.4, 1), "n_tubes": n_tubes,
            "tube_od_mm": od_in * 25.4, "tube_id_mm": round(id_in * 25.4, 2), "tube_length_m": round(l_ft * FT, 3),
            "pitch_mm": 1.25 * 25.4, "layout": "square", "tube_passes": passes, "shell_passes": 1, "baffle_spacing_mm": 5 * 25.4,
            "area_m2": area, "tube_flow_area_m2": flow_area,
            "source": KERN + ". Outside area = tubes x pi x OD x length; tube-side flow area = tubes / passes x pi/4 x ID^2.",
        },
        "thermal": {
            "hio_w_m2k": 640.0, "ho_w_m2k": 1100.0, "r_wall_m2k_w": 0.00005,
            "exp_tube": 0.8, "exp_shell": 0.55,
            "rf_design_m2k_w": round(0.003 * RD_SI, 6),
            "source": "Clean film coefficients at design flows (tube side referred to the outside area) and wall resistance: " + A
                      + ". Flow exponents: turbulent tube side h ~ Re^0.8 (Dittus-Boelter / Sieder-Tate); shell side h ~ Re^0.55 (Kern). "
                        "Fouling allowance: the combined dirt factor 0.003 h ft2 F/Btu of " + KERN,
        },
        "hydraulics": {
            "dp_tube_clean_bar": 0.45, "dp_shell_clean_bar": 0.24, "dp_allow_bar": round(10 * 0.0689476, 3), "dp_exp": 1.8,
            "crude_pressure_barg": 18.0, "kero_pressure_barg": 7.0,
            "source": "Allowed pressure drop 10 psi per side: " + KERN + ". Clean pressure drops at design flow and line pressures: " + A
                      + ". Pressure drop ~ flow^1.8 for turbulent flow (friction factor ~ Re^-0.2).",
        },
        "product": {
            "saybolt_normal": 25.0, "source": "Kerosene Saybolt colour (ASTM D156 scale, -16 darkest to +30 lightest) of clean product: " + A,
        },
        "economics": {
            "furnace_efficiency": 0.85, "carry_through": 0.7, "fuel_price_usd_gj": 6.0, "co2_kg_gj": 56.1,
            "cleaning_cost_usd": 40000.0, "fouling_days_to_allowance": 365.0,
            "source": "Furnace efficiency, fraction of the lost duty that reaches the furnace (the exchangers downstream recover part of it), "
                      "fuel price, cost of one bundle cleaning and fouling rate: " + A
                      + ". CO2 factor for natural gas 56.1 kg/GJ: IPCC 2006 Guidelines, Vol. 2, Ch. 2, Table 2.2 (net calorific basis).",
        },
        "demo": {"time_scale": 60,
                 "note": "Demo only: the plant clock runs 60 times faster, so the daily swing of throughput and inlet temperatures shows in minutes. Fouling in a real exchanger takes months; in the demo the failure modes ramp in over about a minute."},
    },
    "telemetry": {
        "event": "hex", "publish_every_s": 60, "device_type": "SHELL_TUBE_HEX",
        "groups": {"Crude": "Tube side: crude oil", "Kero": "Shell side: kerosene product", "Product": "Kerosene product quality"},
        "points": [
            {"metric": "crude_flow_t_h", "path": "Crude.Flow", "label": "Crude flow (tube side)", "unit": "t/h"},
            {"metric": "crude_in_c", "path": "Crude.InletTemp", "label": "Crude inlet temperature", "unit": "°C"},
            {"metric": "crude_out_c", "path": "Crude.OutletTemp", "label": "Crude outlet temperature", "unit": "°C"},
            {"metric": "dp_tube_bar", "path": "Crude.DP", "label": "Tube-side pressure drop", "unit": "bar"},
            {"metric": "crude_pressure_barg", "path": "Crude.Pressure", "label": "Crude inlet pressure", "unit": "bar g"},
            {"metric": "kero_flow_t_h", "path": "Kero.Flow", "label": "Kerosene flow (shell side)", "unit": "t/h"},
            {"metric": "kero_in_c", "path": "Kero.InletTemp", "label": "Kerosene inlet temperature", "unit": "°C"},
            {"metric": "kero_out_c", "path": "Kero.OutletTemp", "label": "Kerosene outlet temperature", "unit": "°C"},
            {"metric": "dp_shell_bar", "path": "Kero.DP", "label": "Shell-side pressure drop", "unit": "bar"},
            {"metric": "kero_pressure_barg", "path": "Kero.Pressure", "label": "Kerosene inlet pressure", "unit": "bar g"},
            {"metric": "kero_saybolt", "path": "Product.SayboltColour", "label": "Kerosene colour, online analyser (Saybolt)", "unit": "Saybolt"},
        ],
    },
    "twin_model": {
        "limits": {
            "rf_warn_pct": 60.0, "rf_limit_pct": 100.0, "rf_negative_m2k_w": -0.00005,
            "dp_ratio_high": 1.3, "dp_ratio_low": 0.8, "u_ratio_bypass": 0.85,
            "balance_alert_pct": 5.0, "saybolt_warn": 22.0, "saybolt_alert": 18.0, "leak_dp_min_bar": 1.0,
            "velocity_min_m_s": 1.0, "fuel_penalty_alert_usd_day": 50.0,
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "tube_fouling": {"name": "Crude-side fouling (salts, sediment, asphaltenes in the tubes)", "part": "tubes",
                         "symptoms": "Rf up, tube-side pressure drop up at the same flow, duty down, furnace fuel up",
                         "rules": ["HEX_FOULING_LIMIT", "HEX_DP_TUBE_HIGH", "HEX_DP_TUBE_LIMIT", "HEX_FUEL_PENALTY"], "default_ramp_min": 1.5},
        "shell_fouling": {"name": "Kerosene-side fouling (corrosion products on the bundle)", "part": "shell",
                          "symptoms": "Rf up, shell-side pressure drop up, tube-side pressure drop normal",
                          "rules": ["HEX_FOULING_LIMIT", "HEX_DP_SHELL_HIGH", "HEX_FUEL_PENALTY"], "default_ramp_min": 1.5},
        "partition_leak": {"name": "Pass partition gasket leak (crude bypasses tube passes)", "part": "channel",
                           "symptoms": "U down but tube-side pressure drop down: looks like fouling, is not",
                           "rules": ["HEX_BYPASS_SUSPECT", "HEX_DP_TUBE_LOW", "HEX_FUEL_PENALTY"], "default_ramp_min": 1},
        "tube_leak": {"name": "Tube leak (crude into the kerosene)", "part": "tubes",
                      "symptoms": "kerosene colour drops while the crude side is at the higher pressure; the heat balance hardly moves at this cold end",
                      "rules": ["HEX_TUBE_LEAK", "HEX_PRODUCT_COLOUR"], "default_ramp_min": 1},
        "ti_drift": {"name": "Crude outlet temperature transmitter drift", "part": "instrument",
                     "symptoms": "cold-side duty exceeds hot-side duty; the exchanger looks cleaner than clean",
                     "rules": ["HEX_COLD_DUTY_EXCESS", "HEX_RF_NEGATIVE"], "default_ramp_min": 1},
        "low_throughput": {"name": "Long run at low throughput (low tube velocity)", "part": "operation",
                           "symptoms": "crude velocity below the threshold where crude fouling speeds up; U clean expected falls with flow, no false fouling",
                           "rules": ["HEX_VELOCITY_LOW"], "default_ramp_min": 0.5},
    },
    "presentation": {"title": "E-2501 crude / kerosene exchanger", "dashboard": "SHELL_TUBE_HEX"},
}

out = HERE / "twin" / "e-2501.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
