"""Write twin/ami-7301.twin.json: the metering system of one low-voltage feeder (AMI-7301).

    python build_twin.py

AMI-7301 is the advanced metering infrastructure (AMI) of one 400 V feeder: a CT-connected check meter on the LV terminals
of a 250 kVA distribution transformer that feeds only this feeder, 24 three-phase customer smart meters in four street
cabinets (6 meters per cabinet), and the PLC data concentrator and head-end system (HES) that read them every 15 minutes.

Sources (public, read 2026-11-19):
  Landis+Gyr E350 series 2 ZxF100Ax/Cx three-phase residential meter, Technical Data D000027981 en g (12.12.2012),
  https://cdn.yesss.co.uk/documents/59632.pdf : 3 x 230/400 V, 50 Hz, IEC class 1 active (IEC 62053-21) / MID class B
  (EN 50470-3) for ZMF110Cx, Imax 80 or 100 A, voltage-circuit power 0.45 W per phase (typical), disconnector 100 A,
  UC3 to IEC 62055-31, optical interface IEC 62056-21, communication modules (PLC, GSM/GPRS, Ethernet).
  Itron ACE SL7000 brochure EL.0019.1-EN-02/12, https://lam.itron.com/o/commerce-media/accounts/-1/attachments/3809712 :
  transformer connected class 0.2S / 0.5S / C, CT connection Ib 1 A Imax 10 A, DLMS-COSEM (IEC 62056), voltage quality
  thresholds, magnet detection, optional terminal cover detection, 16 load-profile channels.
  Commission Regulation (EU) 548/2014 Annex I Table I.1 (https://legislation.gov.uk/eur/2014/548/annex/I/division/1/adopted):
  250 kVA liquid-immersed, Tier 2: load losses Ak 2350 W, no-load losses A0-10 % 270 W.
  NAYY-J 4x185 SE and 4x95 SE aluminium cable: conductor resistance 0.164 and 0.32 ohm/km at 20 C (manufacturer data
  sheet as quoted in a search excerpt; matches the IEC 60228 values). NYY-J 4x16 copper service cable: 1.15 ohm/km
  (IEC 60228 class 2, Lapp table T11).
Assumptions (labelled in "source"): feeder lengths and cable sizes, 420 V transformer no-load voltage, uk 4 %, cable
reactance 0.08 ohm/km, 40 C mean conductor temperature, 0.95 power factor, the residential load shape, the concentrator's
own consumption, every alarm limit (typical revenue protection and network practice, not a utility standard).
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

A = "assumption: typical value, replace with your network model (GIS), cable records and HES configuration"

SECTIONS = [  # transformer -> cabinet A -> B -> C -> D
    {"name": "TX-A", "to": "A", "length_m": 120, "cable": "NAYY-J 4x185 SE", "r20_ohm_km": 0.164, "x_ohm_km": 0.08, "customers": 6},
    {"name": "A-B", "to": "B", "length_m": 120, "cable": "NAYY-J 4x185 SE", "r20_ohm_km": 0.164, "x_ohm_km": 0.08, "customers": 6},
    {"name": "B-C", "to": "C", "length_m": 120, "cable": "NAYY-J 4x95 SE", "r20_ohm_km": 0.32, "x_ohm_km": 0.08, "customers": 6},
    {"name": "C-D", "to": "D", "length_m": 120, "cable": "NAYY-J 4x95 SE", "r20_ohm_km": 0.32, "x_ohm_km": 0.08, "customers": 6},
]
SERVICE = {"cable": "NYY-J 4x16 RM (copper)", "length_m": 20, "r20_ohm_km": 1.15, "x_ohm_km": 0.08}
TEMP_C, ALPHA = 40.0, 0.00403
N = sum(s["customers"] for s in SECTIONS)


def derived():
    """Effective resistances of the radial feeder, seen from the transformer, for the twin's stateless formulas.

    f_k = share of the customers beyond the start of section k (the current in section k is f_k x the head current if
    every customer draws the same). Voltage drop to the last cabinet: sum f_k Z_k. I2R loss: sum f_k^2 R_k. The 24 service
    cables each carry I/N, so together they add R_service / N to both.
    """
    kt = 1 + ALPHA * (TEMP_C - 20)
    left, rd, xd, rl = N, 0.0, 0.0, 0.0
    for s in SECTIONS:
        f = left / N
        r = s["r20_ohm_km"] * kt * s["length_m"] / 1000
        x = s["x_ohm_km"] * s["length_m"] / 1000
        rd += f * r
        xd += f * x
        rl += f * f * r
        left -= s["customers"]
    rs = SERVICE["r20_ohm_km"] * kt * SERVICE["length_m"] / 1000
    return {"r_drop_ohm": round(rd + rs / N, 6), "x_drop_ohm": round(xd, 6), "r_loss_ohm": round(rl + rs / N, 6),
            "temp_factor": round(kt, 5), "r_service_ohm": round(rs, 6)}


twin = {
    "$comment": "AMI-7301: the metering system of one LV feeder. Expected values in Maximo Monitor from the network model, the meter and transformer data; the head-end sends only what the meters measure.",
    "twin": {"id": "AMI-7301", "name": "LV feeder metering system AMI-7301", "version": "1.0.0", "folder": "ami-twin"},
    "identification": {
        "asset": "AMI-7301", "assetnum": "AMI-7301", "manufacturer": "Landis+Gyr E350 customer meters, Itron ACE SL7000 check meter,",
        "model": "PLC data concentrator and head-end system (AMI)",
        "description": "Metering system of LV feeder 1 of a 250 kVA distribution substation: check meter, 24 smart meters, data concentrator",
        "customer_meter": "Landis+Gyr E350 series 2 ZMF110Cx three-phase direct-connected meter with disconnector, 3 x 230/400 V, 5(100) A, IEC class 1 / MID class B, PLC communication module",
        "check_meter": "Itron ACE SL7000 transformer-connected meter, class 0.5S, on 300/5 A CTs at the transformer LV terminals",
        "concentrator": "PLC data concentrator in the substation (DLMS/COSEM over PLC to the meters, IP backhaul to the head-end system)",
        "transformer": "250 kVA 20/0.42 kV liquid-immersed distribution transformer, Dyn11, feeding this one LV feeder",
    },
    "design": {
        "network": {
            "voltage_nominal_v": 230.0, "no_load_v": 242.5, "frequency_hz": 50, "pf": 0.95, "temp_c": TEMP_C, "alpha_per_k": ALPHA,
            "sections": SECTIONS, "service": SERVICE, "customers": N,
            "derived": derived(),
            "source": "Radial feeder: four 120 m sections to four street cabinets with 6 customers each, cable types from the "
                      "network records. Resistances at 20 C: NAYY-J 4x185 SE 0.164 ohm/km, 4x95 SE 0.32 ohm/km (manufacturer data, "
                      "= IEC 60228), service cable NYY-J 4x16 copper 1.15 ohm/km (IEC 60228 class 2). Corrected to 40 C with "
                      "alpha = 0.00403 /K (commonly quoted for aluminium). Lengths, reactance 0.08 ohm/km, 40 C, pf 0.95, 420 V "
                      "no-load voltage: " + A + ".",
        },
        "transformer": {
            "rating_kva": 250.0, "uk_pct": 4.0, "pk_w": 2350.0, "po_w": 270.0, "tap_pct": 0.0,
            "source": "Load and no-load losses: maximum values of Commission Regulation (EU) 548/2014 Table I.1, Tier 2, 250 kVA "
                      "liquid-immersed (Ak 2350 W, A0-10 % 270 W). uk 4 % and the 0 % tap position: " + A + ".",
        },
        "meters": {
            "interval_min": 15, "n_meters": N, "meter_w_per_phase": 0.45, "concentrator_w": 5.0,
            "customer_class": "IEC 62053-21 class 1 / MID class B (MPE 1 % from Itr to Imax at +5 to +30 C)",
            "check_class": "IEC 62053-22 class 0.5S (meter) on class 0.5S CTs (assumption)",
            "source": "E350 series 2 technical data: voltage-circuit active power 0.45 W per phase (typical), not registered by the "
                      "meter itself but seen by the check meter. Check meter: ACE SL7000 class 0.5S, CT connection Ib 1 A Imax 10 A "
                      "(Itron brochure); CT ratio 300/5 A class 0.5S and concentrator consumption 5 W: " + A + ".",
        },
        "load": {
            "kw_per_customer_peak": 2.4, "kw_per_customer_night": 0.35,
            "source": "Residential diversified load shape (night, morning and evening peaks) used by the stand-in only: " + A + ".",
        },
        "demo": {"time_scale": 90, "start_hour": 19.0,
                 "note": "Demo only: the plant clock runs 90 times faster, so each published reading (every 10 s) is one 15-minute "
                         "meter interval and a day passes in 16 minutes. The page opens at the visitor's local time."},
    },
    "telemetry": {
        "event": "ami", "publish_every_s": 10, "device_type": "AMI_LV_FEEDER",
        "groups": {"Feeder": "Check meter at the transformer LV terminals (one 15-minute interval)",
                   "Customers": "Customer smart meters, summed by the head-end per phase of the network model",
                   "Voltage": "Voltages at the meters (10-minute means inside the interval)", "Health": "Meter and head-end health"},
        "points": [
            {"metric": "feeder_kwh_l1", "path": "Feeder.EnergyL1", "label": "Check meter import energy, phase L1", "unit": "kWh"},
            {"metric": "feeder_kwh_l2", "path": "Feeder.EnergyL2", "label": "Check meter import energy, phase L2", "unit": "kWh"},
            {"metric": "feeder_kwh_l3", "path": "Feeder.EnergyL3", "label": "Check meter import energy, phase L3", "unit": "kWh"},
            {"metric": "feeder_kwh_export", "path": "Feeder.EnergyExport", "label": "Check meter export energy, all phases", "unit": "kWh"},
            {"metric": "feeder_i_l1", "path": "Feeder.CurrentL1", "label": "Feeder current L1 (interval mean)", "unit": "A"},
            {"metric": "feeder_i_l2", "path": "Feeder.CurrentL2", "label": "Feeder current L2 (interval mean)", "unit": "A"},
            {"metric": "feeder_i_l3", "path": "Feeder.CurrentL3", "label": "Feeder current L3 (interval mean)", "unit": "A"},
            {"metric": "feeder_i_n", "path": "Feeder.CurrentN", "label": "Feeder neutral current (interval mean)", "unit": "A"},
            {"metric": "v_bus_l1", "path": "Voltage.BusL1", "label": "LV busbar voltage L1-N", "unit": "V"},
            {"metric": "v_bus_l2", "path": "Voltage.BusL2", "label": "LV busbar voltage L2-N", "unit": "V"},
            {"metric": "v_bus_l3", "path": "Voltage.BusL3", "label": "LV busbar voltage L3-N", "unit": "V"},
            {"metric": "cust_kwh_l1", "path": "Customers.EnergyL1", "label": "Sum of customer meters on L1 (network model phase)", "unit": "kWh"},
            {"metric": "cust_kwh_l2", "path": "Customers.EnergyL2", "label": "Sum of customer meters on L2 (network model phase)", "unit": "kWh"},
            {"metric": "cust_kwh_l3", "path": "Customers.EnergyL3", "label": "Sum of customer meters on L3 (network model phase)", "unit": "kWh"},
            {"metric": "reads_ok", "path": "Customers.ReadsOK", "label": "Customer meters read for this interval", "unit": "count"},
            {"metric": "reads_24h_pct", "path": "Customers.DailyReadPct", "label": "Interval reads received, last 24 h", "unit": "%"},
            {"metric": "v_min_cust", "path": "Voltage.MinCustomer", "label": "Lowest voltage at any customer meter", "unit": "V"},
            {"metric": "v_max_cust", "path": "Voltage.MaxCustomer", "label": "Highest voltage at any customer meter", "unit": "V"},
            {"metric": "v_end_l1", "path": "Voltage.EndL1", "label": "End-of-feeder meter voltage L1-N (cabinet D)", "unit": "V"},
            {"metric": "v_end_l2", "path": "Voltage.EndL2", "label": "End-of-feeder meter voltage L2-N (cabinet D)", "unit": "V"},
            {"metric": "v_end_l3", "path": "Voltage.EndL3", "label": "End-of-feeder meter voltage L3-N (cabinet D)", "unit": "V"},
            {"metric": "tamper_events_24h", "path": "Health.TamperEvents", "label": "Terminal cover open / magnetic field events, last 24 h", "unit": "count"},
            {"metric": "clock_offset_max_s", "path": "Health.ClockOffsetMax", "label": "Largest meter clock offset found at the last read", "unit": "s"},
            {"metric": "relays_cmd_open", "path": "Health.RelaysCommandedOpen", "label": "Meters whose disconnector was commanded open", "unit": "count"},
            {"metric": "relays_open", "path": "Health.RelaysOpen", "label": "Meters reporting the disconnector open", "unit": "count"},
            {"metric": "kwh_on_open_relays", "path": "Health.EnergyOnOpenRelays", "label": "Energy registered by meters commanded open", "unit": "kWh"},
        ],
    },
    "twin_model": {
        "limits": {
            "coverage_min_pct": 99.0, "ntl_alert_pct": 3.0, "ntl_negative_pct": 2.0, "phase_spread_pct": 8.0,
            "export_alert_kwh": 0.05, "neutral_shift_v": 8.0, "en50160_low_v": 207.0, "en50160_high_v": 253.0,
            "bus_low_v": 226.0, "bus_high_v": 246.0, "clock_offset_s": 10.0, "relay_kwh": 0.01,
        },
        "source": "Unexplained loss 3 % and negative loss 2 % of the feeder energy, phase spread 8 points, neutral shift 8 V, busbar "
                  "band 226-246 V, clock offset 10 s, coverage 99 %: assumptions (typical revenue protection and network practice). "
                  "207 / 253 V: 230 V +/- 10 %, the EN 50160 LV band as commonly quoted.",
    },
    "failure_modes": {
        "$comment": "Each failure mode: what degrades, how it shows, the rules that see it.",
        "bypass_theft": {"name": "Meter bypass (energy theft)", "part": "customer meter",
                         "symptoms": "feeder energy above the customer sum plus losses, on one phase; terminal cover opened",
                         "rules": ["AMI_LOSS_UNEXPLAINED", "AMI_TAMPER"], "default_ramp_min": 1},
        "ct_polarity": {"name": "Check meter CT wired reversed on L2", "part": "check meter",
                        "symptoms": "one phase registers as export; customers exceed the feeder", "rules": ["AMI_LOSS_NEGATIVE", "AMI_REVERSE_ENERGY"],
                        "default_ramp_min": 0.5},
        "phase_mismapping": {"name": "Wrong phase in the network model (cabinet C)", "part": "network model",
                             "symptoms": "total balance fine, one phase shows loss and another a gain", "rules": ["AMI_PHASE_MAPPING"],
                             "default_ramp_min": 1},
        "loose_neutral": {"name": "Loose neutral connection in cabinet D", "part": "LV network",
                          "symptoms": "end-of-feeder phase voltages split apart; one goes high, one low", "rules": ["AMI_NEUTRAL_SHIFT", "AMI_VOLTAGE_OUT"],
                          "default_ramp_min": 1.5},
        "tap_setting": {"name": "Transformer off-load tap set too high", "part": "transformer",
                        "symptoms": "busbar and every meter high by the same amount", "rules": ["AMI_BUS_VOLTAGE"], "default_ramp_min": 1},
        "concentrator_comms": {"name": "Data concentrator loses a PLC segment", "part": "concentrator",
                               "symptoms": "meters behind cabinets B and C not read; apparent loss is not real", "rules": ["AMI_READS_LOW"],
                               "default_ramp_min": 1},
        "clock_drift": {"name": "Meter clock drift (sync failing)", "part": "customer meter",
                        "symptoms": "clock offset grows at every read; intervals shift", "rules": ["AMI_CLOCK_DRIFT"], "default_ramp_min": 1.5},
        "relay_stuck": {"name": "Disconnector stuck closed", "part": "customer meter",
                        "symptoms": "a meter commanded open still reports closed and registers energy", "rules": ["AMI_RELAY_MISMATCH"],
                        "default_ramp_min": 0.5},
    },
    "presentation": {"title": "AMI-7301 LV feeder metering system", "dashboard": "AMI_LV_FEEDER"},
}

out = HERE / "twin" / "ami-7301.twin.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(twin, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", out, twin["design"]["network"]["derived"])
