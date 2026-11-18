"""Write twin/dh-7101.twin.json: the district heating building substation twin (DH-7101).

    python build_twin.py

DH-7101 is an indirect district heating substation in the plant room of a small apartment building: a brazed plate heat
exchanger for space heating behind a motorised control valve and a differential pressure controller, an instantaneous
domestic hot water (DHW) heat exchanger with a DHW circulation loop, a weather-compensating controller and an ultrasonic
heat meter in the primary return. Reference product: Danfoss Termix VVX-I (fact sheet AM017486470696en-010401),
heat meter Kamstrup MULTICAL 403, controller Danfoss ECL Comfort 310.

Sources and assumptions (every number below is either from a named source or labelled as an assumption in "source"):
  Danfoss Termix VVX-I fact sheet: heating HE x-3 row 31 kW at primary 70/40 °C, secondary 60/35 °C, primary 906 l/h;
    DHW capacity 33-55 kW; PN 10, Tmax 120 °C.
  Kamstrup MULTICAL 403 data sheet: qp sizes 0.6 ... 15 m³/h (1.5 used), ΔΘ 3-178 K, Pt500 pair, M-Bus / wireless M-Bus,
    MPE of a class 2 meter per EN 1434-1: Ef = 2 + 0.02 qp/q (max 5 %), Et = 0.5 + 3 ΔΘmin/ΔΘ, Ec = 0.5 + ΔΘmin/ΔΘ.
  Danfoss VF 2 / VF 3 data sheet: valve authority a = Δp valve open / (Δp valve open + Δp rest), ideal 0.5, range 0.4-0.7.
  Energiföretagen F:101 (Swedish DH substation regulation): DHW out 55 °C, at least 50 °C at the taps and in the whole
    circulation loop; primary return at most 3 K above the secondary return of the space heating exchanger; network
    differential pressure 0.1-0.6 MPa.
  HSE (UK) legionella guidance: hot water distributed so that it reaches 50 °C at the outlets within 1 minute.
  Østergaard & Svendsen (2019), quoting Frederiksen & Werner: a 1 K higher return costs a DH utility on average
    EUR 0.15 per MWh delivered (range 0.03-0.38).
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with the data of your own substation"
VVX = "Danfoss Termix VVX-I fact sheet (AM017486470696en-010401), heating exchanger x-3 row"

# Heating exchanger design point (fact sheet row) and the UA it implies
Q_SH, TPS, TPR, TSS, TSR, MP_D = 31.0, 70.0, 40.0, 60.0, 35.0, 0.906
K_WATER = 1.15
dt1, dt2 = TPS - TSS, TPR - TSR
LMTD_D = (dt1 - dt2) / math.log(dt1 / dt2)
UA_D = Q_SH / LMTD_D
MS_D = Q_SH / (K_WATER * (TSS - TSR))
KVS, DP_HEX_D, DP_SET = 1.6, 18.0, 70.0
DPV100 = (MP_D / KVS) ** 2 * 100.0

twin = {
    "$comment": "DH-7101 district heating substation twin. Expected values in Maximo Monitor from the substation, heat meter and valve data; the controller and the meter send only what they measure.",
    "twin": {"id": "DH-7101", "name": "District heating substation DH-7101", "version": "1.0.0", "folder": "dhsub-twin"},
    "identification": {
        "asset": "DH-7101", "assetnum": "DH-7101", "manufacturer": "Danfoss",
        "model": "Termix VVX-I (indirect space heating, instantaneous domestic hot water)",
        "description": "Building substation of a small apartment block: space heating 31 kW, domestic hot water with circulation, heat meter in the primary return",
        "heat_meter": "Kamstrup MULTICAL 403, ultrasonic, qp 1.5 m³/h, Pt500 sensor pair, M-Bus",
        "controller": "Danfoss ECL Comfort 310 weather-compensating controller",
        "control_valve": "Motorised 2-way control valve on the primary side of the heating exchanger, behind a self-acting differential pressure controller",
    },
    "design": {
        "heating": {
            "q_kw": Q_SH, "primary_supply_c": TPS, "primary_return_c": TPR, "secondary_supply_c": TSS, "secondary_return_c": TSR,
            "primary_flow_m3h": MP_D, "secondary_flow_m3h": round(MS_D, 4), "lmtd_k": round(LMTD_D, 4), "ua_kw_k": round(UA_D, 4),
            "ua_flow_exponent": 0.65, "film_split": 0.5,
            "source": VVX + ": 31 kW, primary 70/40 °C, secondary 60/35 °C, primary flow 906 l/h. The secondary flow, the LMTD and UA = Q / LMTD are "
                      "computed from that row. UA flow exponent 0.65 and an equal split of the film resistances between the two sides at design: " + A + " (plate heat exchangers: film coefficient roughly proportional to velocity^0.6-0.7).",
        },
        "dhw": {
            "q_kw": 40.0, "setpoint_c": 58.0, "min_supply_c": 55.0, "min_circulation_c": 50.0, "cold_water_c": 10.0,
            "circulation_flow_m3h": 0.2, "tap_threshold_lpm": 1.0,
            "source": "DHW heat exchanger 40 kW: assumption inside the 33-55 kW DHW range of the Termix VVX-I fact sheet. Minimum 55 °C out of the heater and 50 °C in the whole "
                      "circulation loop: Energiföretagen F:101 (Swedish DH substation regulation), consistent with the HSE guidance of 50 °C at the outlets within one minute. "
                      "Setpoint 58 °C, cold water 10 °C and circulation flow 0.2 m³/h: " + A + ".",
        },
        "curve": {
            "room_c": 20.0, "outdoor_design_c": -12.0, "supply_max_c": 60.0, "supply_min_c": 25.0,
            "source": "Weather compensation (heat curve) as in the Danfoss ECL Comfort 310 operating guide (desired flow temperature against outdoor temperature): "
                      "here a straight line from 60 °C at the design outdoor temperature of -12 °C to the room temperature at 20 °C outdoor, limited to 25-60 °C. "
                      "Design outdoor temperature and the straight line: " + A + ".",
        },
        "valve": {
            "kvs_m3h": KVS, "rangeability": 50.0, "dp_setpoint_kpa": DP_SET, "dp_hex_design_kpa": DP_HEX_D, "dp_network_kpa": 250.0,
            "dpv100_kpa": round(DPV100, 4), "authority_design": round(DPV100 / DP_SET, 4),
            "source": "Valve authority a = Δp of the fully open valve / Δp across valve and exchanger, ideal 0.5, preferred 0.4-0.7 (Danfoss VF 2 / VF 3 data sheet). "
                      "Kvs 1.6 m³/h, equal-percentage characteristic with rangeability 50, differential pressure controller set to 70 kPa, exchanger primary pressure "
                      "drop 18 kPa at design flow: " + A + ". Network differential pressure 250 kPa: " + A + ", inside the 0.1-0.6 MPa of F:101.",
        },
        "meter": {
            "qp_m3h": 1.5, "dtheta_min_k": 3.0, "accuracy_class": 2, "k_kwh_m3k": K_WATER,
            "source": "Kamstrup MULTICAL 403 data sheet: qp 1.5 m³/h, ΔΘ 3-178 K, MPE of a class 2 meter per EN 1434-1 (Ef, Et, Ec). Heat coefficient 1.15 kWh/(m³·K) "
                      "= ρ·cp / 3600 of water at about 45 °C (990 kg/m³ × 4.18 kJ/(kg·K)); a meter uses the temperature-dependent coefficient of EN 1434, about 1 % different.",
        },
        "economics": {
            "annual_heat_mwh": 80.0, "operator_cost_eur_per_mwh_k": 0.15, "operator_cost_range": [0.03, 0.38],
            "copenhagen_cooling_low_k": 27.0, "copenhagen_cooling_high_k": 37.0, "copenhagen_eur_per_mwh_k": 0.72,
            "source": "Annual heat of the building 80 MWh: " + A + ". Cost of 1 K higher return to the utility, EUR 0.15 per MWh (27 Swedish utilities, range 0.03-0.38), and the "
                      "Copenhagen cooling tariff (extra charge below 27 K annual cooling, discount above 37 K, EUR 0.72 per K and MWh): Østergaard & Svendsen, Energy 2019.",
        },
        "network": {"supply_c": 70.0, "source": "District heating supply temperature at the building in the heating season: " + A + " (the fact sheet row is designed for 70 °C)."},
        "demo": {"time_scale": 60, "outdoor_min_c": -4.0, "outdoor_max_c": 6.0, "outdoor_period_s": 1200, "tap_share": 0.2,
                 "note": "Demo only: the outdoor temperature swings between -4 and +6 °C over 20 minutes of real time, and hot water is tapped about a fifth of the time. "
                         "The page looks the same whenever it is opened: the stand-in does not follow the time of day."},
    },
    "telemetry": {
        "event": "dhsub", "publish_every_s": 10, "device_type": "DH_SUBSTATION",
        "groups": {"Meter": "Heat meter (primary return)", "Primary": "Primary side sensors of the controller",
                   "Heating": "Space heating circuit", "Valve": "Control valve and differential pressure", "DHW": "Domestic hot water"},
        "points": [
            {"metric": "hm_t_supply_c", "path": "Meter.T1", "label": "Heat meter supply temperature T1", "unit": "°C"},
            {"metric": "hm_t_return_c", "path": "Meter.T2", "label": "Heat meter return temperature T2", "unit": "°C"},
            {"metric": "hm_flow_m3h", "path": "Meter.Flow", "label": "Heat meter flow", "unit": "m³/h"},
            {"metric": "hm_power_kw", "path": "Meter.Power", "label": "Heat meter power", "unit": "kW"},
            {"metric": "hm_info_code", "path": "Meter.Info", "label": "Heat meter info code (0 = no error)", "unit": "code"},
            {"metric": "p_supply_c", "path": "Primary.SupplyTemp", "label": "Primary supply temperature (controller sensor)", "unit": "°C"},
            {"metric": "p_return_c", "path": "Primary.ReturnTemp", "label": "Primary return temperature, common (controller sensor)", "unit": "°C"},
            {"metric": "sh_p_return_c", "path": "Primary.HeatingReturn", "label": "Primary return after the heating exchanger", "unit": "°C"},
            {"metric": "outdoor_c", "path": "Heating.Outdoor", "label": "Outdoor temperature", "unit": "°C"},
            {"metric": "sh_flow_c", "path": "Heating.FlowTemp", "label": "Heating flow (secondary supply) temperature", "unit": "°C"},
            {"metric": "sh_flow_set_c", "path": "Heating.FlowSetpoint", "label": "Heating flow temperature setpoint in the controller", "unit": "°C"},
            {"metric": "sh_return_c", "path": "Heating.ReturnTemp", "label": "Heating return (secondary return) temperature", "unit": "°C"},
            {"metric": "sh_pump_flow_m3h", "path": "Heating.PumpFlow", "label": "Heating circulator flow (pump estimate)", "unit": "m³/h"},
            {"metric": "valve_pos_pct", "path": "Valve.Position", "label": "Control valve position", "unit": "%"},
            {"metric": "valve_reversals_h", "path": "Valve.ReversalsPerHour", "label": "Valve direction reversals, last hour (controller counter)", "unit": "1/h"},
            {"metric": "sh_flow_rms_k", "path": "Valve.FlowTempRms", "label": "RMS of flow temperature minus setpoint, last 15 min", "unit": "K"},
            {"metric": "dp_section_kpa", "path": "Valve.DiffPressure", "label": "Differential pressure across valve and heating exchanger", "unit": "kPa"},
            {"metric": "dhw_c", "path": "DHW.SupplyTemp", "label": "Domestic hot water temperature leaving the heater", "unit": "°C"},
            {"metric": "dhw_flow_lpm", "path": "DHW.TapFlow", "label": "Domestic hot water tapping flow", "unit": "l/min"},
            {"metric": "cw_c", "path": "DHW.ColdWater", "label": "Cold water temperature", "unit": "°C"},
            {"metric": "dhw_circ_return_c", "path": "DHW.CirculationReturn", "label": "DHW circulation return temperature", "unit": "°C"},
        ],
    },
    "twin_model": {
        "limits": {
            "return_excess_alert_k": 3.0, "ua_ratio_alert": 0.7, "sec_flow_ratio_alert": 1.25, "curve_offset_alert_k": 5.0,
            "supply_shortfall_alert_k": 5.0, "bypass_mix_alert_k": 7.5, "meter_temp_dev_alert_k": 1.0, "authority_alert": 0.4,
            "hunting_reversals_alert_h": 20.0, "hunting_rms_alert_k": 1.5, "ua_min_load": 0.45,
        },
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "hex_fouling": {"name": "Heating exchanger fouling (sludge, magnetite)", "part": "heating exchanger",
                        "symptoms": "UA below expected at the same flows, primary flow and primary return up", "rules": ["DH_UA_LOW"], "default_ramp_min": 1.5},
        "secondary_overflow": {"name": "Heating circuit over-flow (unbalanced radiators, pump too high)", "part": "heating circuit",
                               "symptoms": "circulator flow above design, small secondary ΔT, high secondary and primary return",
                               "rules": ["DH_SEC_FLOW_HIGH", "DH_RETURN_HIGH"], "default_ramp_min": 1},
        "curve_too_high": {"name": "Heat curve raised in the controller", "part": "controller",
                           "symptoms": "flow setpoint above the curve, rooms too warm, higher return",
                           "rules": ["DH_CURVE_HIGH", "DH_RETURN_HIGH"], "default_ramp_min": 1},
        "primary_bypass": {"name": "Primary short circuit (leaking valve or open bypass)", "part": "primary pipework",
                           "symptoms": "hot supply water mixes into the return, common return above the heating exchanger return",
                           "rules": ["DH_PRIMARY_BYPASS", "DH_RETURN_HIGH"], "default_ramp_min": 1},
        "meter_sensor_fault": {"name": "Heat meter supply sensor out of its pocket", "part": "heat meter",
                               "symptoms": "meter T1 below the controller's supply sensor, energy under-registered",
                               "rules": ["DH_METER_TEMP_MISMATCH", "DH_METER_ERROR"], "default_ramp_min": 0.5},
        "dp_controller_fault": {"name": "Differential pressure controller failed open", "part": "control valve",
                                "symptoms": "full network Δp across the valve, low authority, valve hunting",
                                "rules": ["DH_AUTHORITY_LOW", "DH_VALVE_HUNTING"], "default_ramp_min": 1},
        "dhw_circulation_fault": {"name": "DHW circulation pump failed or loop unbalanced", "part": "DHW circulation",
                                  "symptoms": "circulation return below 50 °C: legionella risk in the risers",
                                  "rules": ["DH_DHW_CIRC_LOW"], "default_ramp_min": 1},
        "dhw_setpoint_low": {"name": "DHW temperature set too low", "part": "DHW controller",
                             "symptoms": "hot water leaves the heater below 55 °C and the loop below 50 °C",
                             "rules": ["DH_DHW_TEMP_LOW", "DH_DHW_CIRC_LOW"], "default_ramp_min": 1},
    },
    "presentation": {"title": "DH-7101 district heating substation", "dashboard": "DH_SUBSTATION"},
}

out = HERE / "twin" / "dh-7101.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out, f"UA {UA_D:.3f} kW/K, LMTD {LMTD_D:.3f} K, secondary flow {MS_D:.3f} m3/h, authority {DPV100 / DP_SET:.3f}")
