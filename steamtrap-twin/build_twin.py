"""Write twin/st-4701.twin.json: the steam trap twin (ST-4701 and the trap population it belongs to).

    python build_twin.py

ST-4701 is a 1/2 in Spirax Sarco TD52M thermodynamic steam trap draining a drip leg on a 10 bar g saturated steam main.
An Emerson Rosemount 708 wireless acoustic transmitter is clamped on the pipe just upstream of the trap: it sends the
acoustic level (0-255 counts) and the pipe temperature over WirelessHART. The steam trap monitoring software adds the
cycling rate it derives from the acoustic signal, and the trap survey records add the population statistics of the
800 traps on the same steam distribution system.

Sources and assumptions (every number below is either from a checked source or labelled as an assumption in "source"):
  Spirax Sarco TI-P068-18 (TD52M): sizes 3/8 to 1 in, PMO 42 bar g, TMO 425 C, minimum operating differential 0.25 bar,
    back pressure must not exceed 80 % of the upstream pressure, cold hydraulic test 95 bar g.
  US DOE Steam Tip Sheet #1 (Jan 2012): steam loss of a leaking trap through a re-entrant orifice, Cd 0.72, to atmosphere
    (1/8 in at 150 psig: 75.8 lb/h); 15-30 % of traps failed after 3-5 years without maintenance; < 5 % with a programme.
  Napier's formula for saturated steam through an orifice: W = A x P / 70 (lb/s, sq.in, psia) = 51.43 x A x P lb/h.
  IAPWS-IF97 (IAPWS R7-97(2012)) region 4 backward equation Ts(p) for the saturation temperature.
  Steam tables (IAPWS-based): 11 bar abs (10 bar g): Ts 184.06 C, hg 2780.65 kJ/kg; 1.2 bar abs: hf 439.36 kJ/kg.
  IPCC 2006 default emission factor for natural gas: 56.1 t CO2 / TJ (net calorific value).
  Acoustic levels, cycling rate, steam price, survey cost, population size and failure rates: ASSUMPTIONS, to be replaced
  by your own baseline readings, energy price and trap survey history.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with "

twin = {
    "$comment": "ST-4701 steam trap twin. Expected values in Maximo Monitor from the trap data sheet, steam tables, the orifice "
                "equation and the trap survey history; the gateway sends only what is measured or counted.",
    "twin": {"id": "ST-4701", "name": "Steam trap ST-4701 and its trap population", "version": "1.0.0", "folder": "steamtrap-twin"},
    "identification": {
        "asset": "ST-4701", "assetnum": "ST-4701", "manufacturer": "Spirax Sarco",
        "model": "TD52M 1/2 in thermodynamic steam trap (screwed, stainless steel)",
        "description": "Drip-leg trap on the 10 bar g saturated steam main, one of 800 traps on the site steam distribution system",
        "trap_class": "Thermodynamic (EN 26704 / ISO 6704 classification: actuated by fluid dynamics)",
        "monitor": "Emerson Rosemount 708 wireless acoustic transmitter (acoustic level and pipe temperature, WirelessHART)",
        "service": "Steam main drainage (drip leg), condensate discharged to the condensate return",
    },
    "design": {
        "trap": {
            "size_in": 0.5, "pmo_barg": 42.0, "tmo_c": 425.0, "min_dp_bar": 0.25, "pmob_pct": 80.0, "hydro_test_barg": 95.0,
            "source": "Spirax Sarco TI-P068-18 TD52M, TD52MLC, TD52MA and TD52MLCA thermodynamic steam traps: sizes 3/8, 1/2, "
                      "3/4 and 1 in; PMO 42 bar g for saturated steam; TMO 425 C at 42 bar g; minimum operating differential "
                      "0.25 bar; back pressure not above 80 % of the upstream pressure; cold hydraulic test 95 bar g.",
        },
        "steam": {
            "line_pressure_barg": 10.0, "hg_kj_kg": 2780.65, "h_feedwater_kj_kg": 439.36, "atm_bar": 1.01325,
            "source": "Steam main design pressure 10 bar g (" + A + "your steam main). Steam tables (IAPWS-based): hg at 11 bar abs "
                      "2780.65 kJ/kg; feed water from a deaerator at about 105 C, hf at 1.2 bar abs 439.36 kJ/kg (" + A + "your feed water temperature).",
        },
        "leak": {
            "orifice_mm": 3.175, "cd": 0.72, "napier_c_lbh": 51.43,
            "source": "Failed-open trap modelled as a 1/8 in (3.175 mm) re-entrant orifice discharging to atmosphere with a "
                      "discharge coefficient of 0.72, as in the US DOE Steam Tip Sheet #1 table (Boiler Efficiency Institute). "
                      "Napier: W = A x P / 70 lb/s (A sq.in, P psia), i.e. 51.43 x A x P lb/h. The equivalent orifice of a real "
                      "failed trap is an " + A + "the orifice of your trap model or a measured leak.",
        },
        "acoustic": {
            "a0_counts": 25.0, "a1_counts_per_bar": 2.0, "open0_counts": 60.0, "open1_counts_per_bar": 9.0,
            "leak_fraction_alert": 0.15, "leak_fraction_blow": 0.5,
            "source": "Rosemount 708 acoustic level, 0 to 255 counts. Expected level of a healthy thermodynamic trap = a0 + a1 x "
                      "differential pressure; level of a trap blowing fully open = open0 + open1 x differential pressure: " + A +
                      "a baseline taken on your own trap when new and on a known failed trap of the same model.",
        },
        "thermal": {
            "surface_offset_c": 6.0, "backing_up_excess_c": 12.0, "cold_excess_c": 30.0, "sensor_ambient_margin_c": 15.0,
            "source": "Clamp-on pipe surface temperature of a healthy trap inlet sits a few kelvin below the saturation "
                      "temperature (insulation and clamp losses): " + A + "the offset measured on your installation.",
        },
        "cycling": {
            "design_cycles_per_min": 2.0, "rapid_ratio_alert": 3.0,
            "source": "Cycling rate of a thermodynamic trap on a steam main drip leg at the design condensate load: " + A +
                      "the rate counted on your trap when new. A worn disc makes the trap cycle much faster before it blows through.",
        },
        "economics": {
            "steam_price_per_t": 25.0, "hours_per_year": 8000.0, "boiler_efficiency": 0.85, "ef_kg_co2_per_gj": 56.1,
            "survey_cost_per_trap": 12.0,
            "source": "Steam price 25 per tonne (any currency; the DOE tip sheet example uses $10 per 1000 lb = $22 per tonne), "
                      "8000 h per year in service, gas-fired boiler efficiency 85 % on net calorific value, cost of one manual "
                      "survey visit per trap 12: " + A + "your energy price, operating hours, boiler efficiency and survey contract. "
                      "Emission factor of natural gas 56.1 kg CO2 per GJ (IPCC 2006 default, net calorific value).",
        },
        "population": {
            "traps_total": 800, "design_fail_open_rate_pct_y": 6.0, "design_fail_cold_rate_pct_y": 3.0,
            "failed_open_alert_pct": 5.0, "failed_cold_alert_pct": 3.0, "survey_overdue_factor": 1.5,
            "source": "800 traps on the site steam distribution system, surveyed as one population. New failures per year: 6 % "
                      "failed open and 3 % failed cold (" + A + "the rates from your own survey history). Alert when more than "
                      "5 % of the population is failed open: the US DOE tip sheet gives less than 5 % for a site with a regular "
                      "programme and 15 to 30 % after 3 to 5 years without one. Failed-cold alert 3 %: " + A + "your own target.",
        },
        "demo": {"time_scale": 1, "note": "Demo only: the trap cycles in real time; the population counters come from the failure "
                                          "modes, not from the demo clock."},
    },
    "telemetry": {
        "event": "steamtrap", "publish_every_s": 10, "device_type": "STEAM_TRAP_TD",
        "groups": {"Trap": "Rosemount 708 on the trap inlet and the trap discharge", "Steam": "Steam main", "Site": "Site conditions",
                   "Population": "Trap survey and monitoring records of the 800 traps"},
        "points": [
            {"metric": "acoustic_level", "path": "Trap.Acoustic", "label": "Acoustic level at the trap (Rosemount 708)", "unit": "counts"},
            {"metric": "inlet_temp_c", "path": "Trap.InletTemperature", "label": "Pipe surface temperature at the trap inlet", "unit": "°C"},
            {"metric": "cycle_rate_per_min", "path": "Trap.CycleRate", "label": "Trap cycles per minute (from the acoustic signal)", "unit": "1/min"},
            {"metric": "outlet_pressure_barg", "path": "Trap.OutletPressure", "label": "Pressure in the trap discharge line", "unit": "bar g"},
            {"metric": "line_pressure_barg", "path": "Steam.Pressure", "label": "Steam main pressure", "unit": "bar g"},
            {"metric": "line_temp_c", "path": "Steam.Temperature", "label": "Steam main temperature", "unit": "°C"},
            {"metric": "ambient_temp_c", "path": "Site.Ambient", "label": "Ambient temperature", "unit": "°C"},
            {"metric": "pop_traps_total", "path": "Population.Total", "label": "Traps in the population", "unit": "count"},
            {"metric": "pop_failed_open", "path": "Population.FailedOpen", "label": "Traps failed open (blowing or leaking) now", "unit": "count"},
            {"metric": "pop_failed_cold", "path": "Population.FailedCold", "label": "Traps failed cold (blocked) now", "unit": "count"},
            {"metric": "pop_new_failed_open_365d", "path": "Population.NewFailedOpen365", "label": "New failed-open traps found in the last 365 days", "unit": "count"},
            {"metric": "survey_days_since", "path": "Population.DaysSinceSurvey", "label": "Days since the last full trap survey", "unit": "d"},
        ],
    },
    "twin_model": {
        "limits": {
            "leak_fraction_alert": 0.15, "leak_fraction_blow": 0.5, "backing_up_excess_c": 12.0, "cold_excess_c": 30.0,
            "cold_acoustic_ratio": 0.5, "sensor_ambient_margin_c": 15.0, "rapid_ratio_alert": 3.0, "pmob_pct": 80.0,
            "min_dp_bar": 0.25, "failed_open_alert_pct": 5.0, "failed_cold_alert_pct": 3.0, "survey_overdue_factor": 1.5,
            "fail_rate_alert_factor": 1.5,
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "failed_open": {"name": "Trap failed open (blowing steam)", "part": "disc / seat",
                        "symptoms": "acoustic level near the full-open level, inlet at saturation temperature, no cycling",
                        "rules": ["TRAP_BLOW_THROUGH"], "default_ramp_min": 1},
        "disc_wear": {"name": "Disc and seat wear (rapid cycling, leaking)", "part": "disc",
                      "symptoms": "cycling several times faster than design, acoustic level above expected, inlet at saturation",
                      "rules": ["TRAP_RAPID_CYCLING", "TRAP_LEAKING"], "default_ramp_min": 1.5},
        "blocked_cold": {"name": "Trap blocked cold (dirt, strainer, closed valve)", "part": "strainer / inlet",
                         "symptoms": "no sound, inlet far below saturation: condensate stands in the drip leg",
                         "rules": ["TRAP_COLD"], "default_ramp_min": 1},
        "condensate_overload": {"name": "Condensate load above trap capacity", "part": "application",
                                "symptoms": "trap stays open, water noise, inlet subcooled: condensate backing up",
                                "rules": ["TRAP_BACKING_UP"], "default_ramp_min": 1},
        "backpressure_high": {"name": "High back pressure in the discharge line", "part": "condensate return",
                              "symptoms": "discharge pressure above 80 % of the steam pressure, condensate backing up",
                              "rules": ["TRAP_BACKPRESSURE_HIGH", "TRAP_BACKING_UP"], "default_ramp_min": 1},
        "sensor_fault": {"name": "Acoustic transmitter loose or detached", "part": "monitor",
                         "symptoms": "pipe temperature reads ambient, acoustic level at the floor",
                         "rules": ["TRAP_SENSOR_SUSPECT"], "default_ramp_min": 0.5},
        "survey_lapsed": {"name": "Trap survey lapsed (population)", "part": "population",
                          "symptoms": "days since survey grow; failed-open and failed-cold traps accumulate",
                          "rules": ["POP_SURVEY_OVERDUE", "POP_FAILED_OPEN_HIGH", "POP_FAILED_COLD_HIGH"], "default_ramp_min": 1},
        "population_ageing": {"name": "Population failure rate rising (ageing, poor steam quality)", "part": "population",
                              "symptoms": "new failed-open traps per year well above the design rate",
                              "rules": ["POP_FAIL_RATE_HIGH"], "default_ramp_min": 1},
    },
    "presentation": {"title": "ST-4701 steam trap and population", "dashboard": "STEAM_TRAP_TD"},
}

out = HERE / "twin" / "st-4701.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out)
