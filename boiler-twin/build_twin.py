"""Write twin/bl-4501.twin.json: the industrial steam boiler twin (BL-4501).

    python build_twin.py

BL-4501 is a gas-fired three-pass shell (fire-tube) steam boiler of the Bosch UNIVERSAL UL-S type, size 10,000 kg/h with a
16 bar safety pressure (the "UL-S 10,000 x 16" of Bosch's own heat-recovery case study), with an integrated economiser, a
modulating natural gas burner with O2 trim, continuous feedwater level control, automatic TDS blowdown and a feed pump.

Sources and assumptions (every number below is either from a published source or labelled as an assumption in "source"):
  Bosch UL-S product page and steam boiler catalogue: three-pass flame tube / smoke tube, 1,250 to 28,000 kg/h, up to 30 bar,
    up to 235 C, economiser "up to 7 %" fuel saving, the equipment list (low-level limiter, level transducer, pressure limiter,
    full-lift safety valve, automatic conductivity measurement and desalting, quick shut-off blow-down valve, economiser).
  boiler-planning.com (Bosch Industriekessel's planning guide): the UL-S 10,000 x 16 case study (10,000 kg/h, p avg 13 bar,
    blowdown 5 %, boiler 88.9 %, with economiser 95.4 %); flue gas at the boiler outlet about 60 K above the steam temperature;
    economiser outlet 120 to 140 C; Siegert factors and CO2max for natural gas H; air temperature 25 C per EN 12953-11;
    deaerator feedwater not colder than 103 C; blowdown 3 to 5 % of the feedwater.
  Spirax Sarco, Controlling TDS in the boiler water: TDS (ppm) = 0.7 x conductivity (uS/cm); larger shell boilers run up to
    3,500 ppm.
  Saturated steam table (engineering toolbox, IAPWS values): fitted below, used for Tsat, h' and h'' and liquid enthalpy.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with"

# Saturated steam table (absolute pressure bar, Tsat C, h' kJ/kg, h'' kJ/kg), engineeringtoolbox.com saturated steam table
STEAM = [(6, 158.84, 670.43, 2755.46), (8, 170.42, 720.94, 2767.46), (10, 179.88, 762.60, 2776.16), (12, 187.96, 798.42, 2782.73),
         (14, 195.04, 830.05, 2787.79), (16, 201.37, 858.54, 2791.73), (18, 207.11, 884.55, 2794.81), (20, 212.37, 908.56, 2797.21)]
# Saturated liquid (T C, h' kJ/kg) at lower pressures, same table, for the liquid enthalpy fit h(T) = a T + b T^2 + c T^3
LIQ = [(99.63, 417.51), (102.32, 428.84), (104.81, 439.36), (120.23, 504.71), (133.54, 561.44), (143.63, 604.68), (151.85, 640.12)] \
    + [(t, h) for _, t, h, _ in STEAM]


def lstsq(rows, cols):
    """Least squares by the normal equations (pure Python): rows = [(x_vector, y)]."""
    n = cols
    m = [[sum(r[0][i] * r[0][j] for r in rows) for j in range(n)] + [sum(r[0][i] * r[1] for r in rows)] for i in range(n)]
    for i in range(n):
        piv = m[i][i]
        m[i] = [v / piv for v in m[i]]
        for k in range(n):
            if k != i:
                f = m[k][i]
                m[k] = [a - f * b for a, b in zip(m[k], m[i])]
    return [m[i][n] for i in range(n)]


def fit_lnp(idx):
    return [round(c, 6) for c in lstsq([([1.0, math.log(r[0]), math.log(r[0]) ** 2], r[idx]) for r in STEAM], 3)]


steam_fit = {"tsat": fit_lnp(1), "hf": fit_lnp(2), "hg": fit_lnp(3)}
liq_fit = [round(c, 10) for c in lstsq([([t, t * t, t ** 3], h) for t, h in LIQ], 3)]
ERR_T = max(abs(sum(c * math.log(r[0]) ** i for i, c in enumerate(steam_fit['tsat'])) - r[1]) for r in STEAM)
ERR_H = max([abs(sum(c * math.log(r[0]) ** i for i, c in enumerate(steam_fit[k])) - r[j]) for r in STEAM for k, j in (('hf', 2), ('hg', 3))]
            + [abs(liq_fit[0] * t + liq_fit[1] * t * t + liq_fit[2] * t ** 3 - h) for t, h in LIQ])

twin = {
    "$comment": "BL-4501 shell steam boiler twin. Expected values in Maximo Monitor from the maker's data, the steam table and the combustion formulas; the boiler sends only what it measures.",
    "twin": {"id": "BL-4501", "name": "Steam boiler BL-4501", "version": "1.0.0", "folder": "boiler-twin"},
    "identification": {
        "asset": "BL-4501", "assetnum": "BL-4501", "manufacturer": "Bosch Industriekessel",
        "model": "UNIVERSAL UL-S 10,000 x 16 (three-pass shell boiler with integrated economiser)",
        "description": "Process steam boiler, gas-fired, 10 t/h saturated steam at 13 bar g, plant utilities boiler house",
        "type": "Three-pass shell boiler: flame tube (1st pass), wetback reversing chamber, smoke tubes (2nd and 3rd pass)",
        "burner": "Modulating natural gas burner with O2 trim (burner make is project specific)",
        "economiser": "Integrated flue gas heat exchanger ECO, feedwater side",
        "controls": "Boiler control BCO: continuous level control, automatic conductivity measurement and desalting, low-level limiters, pressure limiter",
    },
    "design": {
        "boiler": {
            "rated_steam_kgh": 10000.0, "safety_pressure_barg": 16.0, "operating_pressure_barg": 13.0,
            "source": "Bosch UL-S 10,000 x 16 case study on boiler-planning.com (system steam output 10,000 kg/h, p avg = 13 bar, safety pressure 16 bar in the size code); UL-S range 1,250 to 28,000 kg/h, up to 30 bar, from the Bosch UL-S product page",
        },
        "feedwater": {
            "temp_in_c": 103.0, "cond_design_uscm": 240.0, "hardness_alert_mmol_l": 0.02,
            "source": "Feedwater from a thermal deaerator, not colder than 103 C (boiler-planning.com). Feedwater conductivity 240 uS/cm: "
                      + A + " your softened make-up and condensate return mix. Residual hardness alert 0.02 mmol/l: " + A + " the limit of EN 12953-10 for your boiler and your water treatment contract",
        },
        "boiler_water": {
            "cond_setpoint_uscm": 5000.0, "cond_alert_uscm": 6000.0, "tds_per_uscm": 0.7,
            "source": "Conductivity setpoint 5,000 uS/cm (= 3,500 ppm TDS at 0.7 ppm per uS/cm, the level Spirax Sarco gives for larger shell boilers) and alert 6,000 uS/cm: "
                      + A + " the boiler maker's water specification and EN 12953-10",
        },
        "combustion": {
            "fuel": "natural gas H", "lhv_mj_nm3": 36.0, "co2max_pct": 11.94, "siegert_f_o2_0": 0.4731, "siegert_f_o2_5": 0.4469,
            "o2_design_pct": 3.0, "ea_k": 87.0, "air_ref_c": 25.0, "radiation_loss_full_load_pct": 0.4, "co_alert_ppm": 100.0,
            "source": "Siegert flue gas loss qA = f (t_fg - t_air) / CO2 with CO2 = CO2max (1 - O2/21); natural gas H: CO2max 11.94 %, f 0.4731 at 0 % O2 and 0.4469 at 5 % O2, "
                      "linear in between; air reference 25 C per EN 12953-11 (all boiler-planning.com, Combustion efficiency). Excess air = 87 x O2/(21 - O2): fit to the "
                      "air-ratio table on the same page (lambda 1.15 at 3.09 % O2). LHV 36.0 MJ/Nm3: " + A + " your gas supplier's net calorific value. "
                      "Design O2 3.0 % and radiation loss 0.4 % at full load: " + A + " the commissioning report of your burner and boiler. CO alert 100 ppm: " + A + " your burner setting report",
        },
        "heat_transfer": {
            "exit_approach_full_load_k": 60.0, "exit_approach_load_exp": 0.5, "stack_design_c": 120.0,
            "flue_dp_full_load_mbar": 12.0, "flue_dp_load_exp": 1.8,
            "source": "Flue gas at the boiler outlet about 60 K above the steam temperature and economiser outlet 120 to 140 C (boiler-planning.com); the lower end, 120 C, "
                      "reproduces the 95.4 % of the UL-S 10,000 x 16 case study with the Siegert formula. Approach falling with load^0.5, flue gas pressure drop 12 mbar "
                      "at full load rising with load^1.8: " + A + " your boiler's acceptance test data",
        },
        "feed_pump": {
            "shutoff_barg": 19.5, "k_bar_per_th2": 0.01814, "margin_alert_bar": 2.0, "level_alert_mm": 50.0,
            "source": "Multistage feed pump curve p = p0 - k (feed t/h)^2: 19.5 bar g at shut-off, 17.5 bar g at 10.5 t/h. Margin alert 2 bar over the steam pressure "
                      "(control valve, economiser and non-return valve), level deviation alert 50 mm from the normal water level: " + A + " your pump data sheet and boiler control settings",
        },
        "tests": {
            "lwco_test_interval_h": 24.0, "sv_test_interval_h": 168.0, "grace_factor": 1.25,
            "source": "Functional test of the low-water limiters daily and a manual lift of the safety valves weekly: " + A
                      + " the intervals of your national rules (for example for operation without constant supervision) and the maker's operating manual",
        },
        "economics": {
            "gas_price_usd_mwh": 36.0, "co2_t_per_tj": 56.1, "hours_per_year": 6000.0,
            "source": "CO2 56.1 t/TJ for natural gas (IPCC 2006 default, net calorific value basis). Gas price 36 USD/MWh (10 USD/GJ) and 6,000 h a year: " + A + " your own contract and running hours",
        },
        "steam_table": {
            "fit": "x = ln(p_abs in bar): y = c0 + c1 x + c2 x^2 for Tsat (C), h' and h'' (kJ/kg), 6 to 20 bar abs; liquid h(T) = a T + b T^2 + c T^3 for 100 to 212 C",
            "tsat": steam_fit["tsat"], "hf": steam_fit["hf"], "hg": steam_fit["hg"], "liquid": liq_fit, "p_atm_bar": 1.013,
            "source": f"Least-squares fits to the saturated steam table (engineeringtoolbox.com, IAPWS values); worst error {ERR_T:.2f} K and {ERR_H:.1f} kJ/kg in the range",
        },
        "demo": {"time_scale": 1, "load_min": 0.6, "load_max": 1.0, "load_period_s": 900,
                 "note": "Demo only: the steam demand swings between 60 and 100 % over 15 minutes so the load-corrected expectations are seen working; test counters advance with the plant clock."},
    },
    "telemetry": {
        "event": "boiler", "publish_every_s": 10, "device_type": "STEAM_BOILER_SHELL",
        "groups": {"Steam": "Steam output", "Feed": "Feedwater and feed pump", "Fuel": "Gas and burner", "Flue": "Flue gas",
                   "Water": "Boiler water and blowdown", "Test": "Safety test history"},
        "points": [
            {"metric": "steam_flow_kgh", "path": "Steam.Flow", "label": "Steam flow", "unit": "kg/h"},
            {"metric": "steam_pressure_barg", "path": "Steam.Pressure", "label": "Steam pressure", "unit": "bar g"},
            {"metric": "drum_level_mm", "path": "Steam.Level", "label": "Water level from normal water level", "unit": "mm"},
            {"metric": "feed_flow_kgh", "path": "Feed.Flow", "label": "Feedwater flow", "unit": "kg/h"},
            {"metric": "feed_temp_c", "path": "Feed.TempIn", "label": "Feedwater temperature into the economiser", "unit": "°C"},
            {"metric": "eco_water_out_c", "path": "Feed.TempEcoOut", "label": "Feedwater temperature out of the economiser", "unit": "°C"},
            {"metric": "feed_pump_p_barg", "path": "Feed.PumpPressure", "label": "Feed pump discharge pressure", "unit": "bar g"},
            {"metric": "feed_cond_uscm", "path": "Feed.Conductivity", "label": "Feedwater conductivity", "unit": "µS/cm"},
            {"metric": "feed_hardness_mmol", "path": "Feed.Hardness", "label": "Feedwater residual hardness", "unit": "mmol/l"},
            {"metric": "gas_flow_nm3h", "path": "Fuel.GasFlow", "label": "Natural gas flow", "unit": "Nm³/h"},
            {"metric": "burner_load_pct", "path": "Fuel.FiringRate", "label": "Burner firing rate", "unit": "%"},
            {"metric": "air_temp_c", "path": "Fuel.AirTemp", "label": "Combustion air temperature", "unit": "°C"},
            {"metric": "flue_exit_c", "path": "Flue.BoilerExit", "label": "Flue gas at the boiler outlet (economiser inlet)", "unit": "°C"},
            {"metric": "stack_c", "path": "Flue.Stack", "label": "Flue gas after the economiser (stack)", "unit": "°C"},
            {"metric": "o2_pct", "path": "Flue.O2", "label": "O2 in the dry flue gas", "unit": "%"},
            {"metric": "co_ppm", "path": "Flue.CO", "label": "CO in the flue gas", "unit": "ppm"},
            {"metric": "flue_dp_mbar", "path": "Flue.DP", "label": "Flue gas pressure drop, furnace to stack", "unit": "mbar"},
            {"metric": "boiler_cond_uscm", "path": "Water.Conductivity", "label": "Boiler water conductivity", "unit": "µS/cm"},
            {"metric": "blowdown_valve_pct", "path": "Water.BlowdownValve", "label": "TDS blowdown valve opening", "unit": "%"},
            {"metric": "lwco_test_hours_since", "path": "Test.HoursSinceLWCO", "label": "Hours since the last low-water limiter test", "unit": "h"},
            {"metric": "sv_test_hours_since", "path": "Test.HoursSinceSV", "label": "Hours since the last safety valve lift test", "unit": "h"},
        ],
    },
    "twin_model": {
        "limits": {
            "eff_drop_alert_pct": 1.0, "eff_gap_alert_pct": 2.5, "exit_residual_alert_k": 20.0, "flue_dp_ratio_alert": 1.25,
            "eco_effectiveness_alert": 0.78, "stack_residual_alert_k": 15.0, "o2_high_alert_pct": 4.5,
            "blowdown_factor_alert": 1.6,
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "fireside_fouling": {"name": "Fire-side fouling (soot in the smoke tubes)", "part": "smoke tubes",
                             "symptoms": "boiler exit temperature up at the same load, flue gas pressure drop up; the economiser hides most of the efficiency loss",
                             "rules": ["BLR_FIRESIDE_FOULING"], "default_ramp_min": 1.5},
        "waterside_scale": {"name": "Water-side scale (hardness breakthrough)", "part": "water side",
                            "symptoms": "feedwater hardness up, boiler exit temperature up at the same load, flue gas pressure drop normal",
                            "rules": ["BLR_HARDNESS", "BLR_WATERSIDE_SCALE"], "default_ramp_min": 1.5},
        "economiser_fouling": {"name": "Economiser fouling", "part": "economiser",
                               "symptoms": "economiser effectiveness down, stack temperature up, efficiency down",
                               "rules": ["BLR_ECO_EFFECTIVENESS_LOW", "BLR_STACK_HIGH", "BLR_EFF_LOW"], "default_ramp_min": 1.5},
        "excess_air_high": {"name": "Excess air too high (O2 trim drift, air leak)", "part": "burner",
                            "symptoms": "O2 up, flue gas loss up at the same stack temperature",
                            "rules": ["BLR_EXCESS_AIR_HIGH", "BLR_EFF_LOW"], "default_ramp_min": 1},
        "tds_control_fault": {"name": "TDS control fault (blowdown valve stuck, probe fouled)", "part": "blowdown",
                              "symptoms": "boiler water conductivity above its setpoint and rising: foaming and carry-over risk",
                              "rules": ["BLR_TDS_HIGH"], "default_ramp_min": 1},
        "blowdown_valve_passing": {"name": "Blowdown valve passing", "part": "blowdown",
                                   "symptoms": "feed flow well above steam flow, boiler water far below its setpoint: hot water and chemicals to drain",
                                   "rules": ["BLR_BLOWDOWN_HIGH"], "default_ramp_min": 1},
        "feed_pump_wear": {"name": "Feed pump wear", "part": "feed pump",
                           "symptoms": "discharge pressure below the pump curve, margin over the boiler pressure gone, level sags",
                           "rules": ["BLR_FEED_MARGIN_LOW", "BLR_LEVEL_DEVIATION"], "default_ramp_min": 1},
        "safety_tests_overdue": {"name": "Low-water limiter and safety valve tests skipped", "part": "safety devices",
                                 "symptoms": "hours since the last limiter test and the last safety valve lift grow past their intervals",
                                 "rules": ["BLR_LWCO_TEST_OVERDUE", "BLR_SV_TEST_OVERDUE"], "default_ramp_min": 0.5},
    },
    "presentation": {"title": "BL-4501 steam boiler", "dashboard": "STEAM_BOILER_SHELL"},
}

out = HERE / "twin" / "bl-4501.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
print("fits", steam_fit, liq_fit)
