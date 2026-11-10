"""Build twin/cap-1101.twin.json: 33 kV shunt capacitor bank of 24 Vishay ESTA internally fused 1-phase units
(10.1 kV, 400 kvar), ungrounded double wye with neutral unbalance protection and current-limiting series reactors.

Sources (public, read 2026-11-10):
  Vishay ESTA "Pha... HVAC Capacitors 1-Phase", document 13045, rev. 11-Oct-2021
    https://www.vishay.com/docs/13045/phahvac1phase.pdf
    all-film polypropylene / aluminium foil, synthetic oil (non-PCB); average losses < 0.15 W/kvar; internal discharge
    resistors 75 V / 10 min; temperature category -50 C to +55 C; capacitance tolerance -5 % / +10 %; protection internal
    fuses / pressure monitoring device; IEC 60871, ANSI/IEEE 18; 10.1 kV table: 400 kvar at 50 Hz, 40 A, 95 kVp,
    345 x 175 x 685 mm with internal fuses
  Internal fuses in capacitor units (application note, 2006), https://onegrid.com.au/wp-content/uploads/2023/07/BR-EN-TH02-01_2006-internal_fuses_in_cap_units.pdf
    element voltage about 1500-2500 V in internally fused units; a blown fuse loses about 2 % of a unit; the breakdown
    puts an overvoltage on the healthy elements of the group; case-to-terminal faults are left to unbalance protection
  IEEE Std 18-2002 contingency limits 110 % rms voltage, 120 % peak voltage, 135 % rms current, 135 % kvar
    (as quoted in https://electrical-engineering-portal.com/download-center/books-and-guides/power-substations/capacitor-application-issues;
    older editions allowed 180 % current, e.g. https://www.gevernova.com/grid-solutions/products/specs/capacitors/capacrot_spec.pdf)
  IEEE C37.99 (guide for the protection of shunt capacitor banks): method only (In per failed element, alarm on the
    first failure, trip before the remaining elements exceed 110 %); the numbers below are computed from this bank's circuit.
Assumptions (labelled in the twin): 33 kV bus, 50 Hz; 2 series levels x 2 parallel units per leg; 4 series groups x 18
  parallel elements per unit; network short-circuit power 700 MVA (resonance), damping Q 8; series reactor rating; relay
  settings; inherent unbalance from a +0.06 % capacitance tolerance on one leg.
"""
import json
import math
from pathlib import Path

import twin_calc as tc

HERE = Path(__file__).parent
W = tc.W
UN_KV, Q_UNIT_KVAR = 10.1, 400.0
C_UNIT = Q_UNIT_KVAR * 1e3 / (W * (UN_KV * 1e3) ** 2) * 1e6          # uF
S, N = 4, 18                                                           # series groups, elements per group (assumed)
LEVELS, PARALLEL = 2, 2
VN = 33.0
C_LEG = tc.leg_c(C_UNIT, S, N, 0, LEVELS, PARALLEL)
C_PH = 2 * C_LEG
I_UNIT_RATED = Q_UNIT_KVAR / UN_KV                                     # A at rated unit voltage
I_PH_RATED = I_UNIT_RATED * PARALLEL * 2                                # both wyes
TOL = 0.0006                                                           # +0.06 % on leg A-a (inherent unbalance)


def legs(f=0, tol=TOL):
    ca = tc.leg_c(C_UNIT, S, N, f, LEVELS, PARALLEL) * (1 + tol)
    return {"A": [ca, C_LEG, C_LEG], "B": [C_LEG, C_LEG, C_LEG]}


base = tc.bank_circuit(VN, legs(0))
inherent = base["i_neutral"]
one = tc.bank_circuit(VN, legs(1, 0.0))
k1 = one["i_neutral"] / VN
asym1 = (max(one["i_phase"]) - min(one["i_phase"])) / (sum(one["i_phase"]) / 3) * 100
table = []
for f in range(0, 7):
    c = tc.bank_circuit(VN, legs(f, 0.0))
    table.append({"failed": f, "neutral_a_per_kv": round(c["i_neutral"] / VN, 6),
                  "element_overvoltage_pct": round((tc.group_overvoltage(S, N, f) - 1) * 100, 2),
                  "q_mvar_at_33kv": round(c["q_mvar"], 4),
                  "phase_asym_pct": round((max(c["i_phase"]) - min(c["i_phase"])) / (sum(c["i_phase"]) / 3) * 100, 4)})


def P(metric, path, label, unit, rng, noise, opc=None):
    return {"metric": metric, "path": path, "label": label, "unit": unit, "range": rng, "noise": noise, "opc": opc}


points = [
    P("bus_voltage_kv", "Bus.Voltage", "Bus voltage (line to line)", "kV", [0, 45], 0.02, "IEC 61850: MMXU.PPV"),
    P("bank_current_l1_a", "Bank.CurrentL1", "Bank current L1 (rms incl. harmonics)", "A", [0, 400], 0.02, "IEC 61850: MMXU.A.phsA"),
    P("bank_current_l2_a", "Bank.CurrentL2", "Bank current L2", "A", [0, 400], 0.02, "IEC 61850: MMXU.A.phsB"),
    P("bank_current_l3_a", "Bank.CurrentL3", "Bank current L3", "A", [0, 400], 0.02, "IEC 61850: MMXU.A.phsC"),
    P("bank_q_mvar", "Bank.ReactivePower", "Bank reactive power (fundamental)", "Mvar", [0, 15], 0.004, "IEC 61850: MMXU.TotVAr"),
    P("current_thd_pct", "Harmonics.CurrentTHD", "Bank current THD", "%", [0, 200], 0.2, "IEC 61850: MHAI.ThdA"),
    P("current_h7_pct", "Harmonics.CurrentH7", "Bank current, 7th harmonic", "%", [0, 200], 0.15, "IEC 61850: MHAI.HA (h7)"),
    P("current_h5_pct", "Harmonics.CurrentH5", "Bank current, 5th harmonic", "%", [0, 200], 0.1, "IEC 61850: MHAI.HA (h5)"),
    P("voltage_thd_pct", "Harmonics.VoltageTHD", "Bus voltage THD", "%", [0, 50], 0.05, "IEC 61850: MHAI.ThdPhV"),
    P("peak_voltage_pu", "Bank.PeakVoltage", "Peak unit voltage (of rated peak, incl. harmonics)", "pu", [0, 3], 0.003, "IEC 61850: PTOV (crest)"),
    P("neutral_current_a", "Unbalance.NeutralCurrent", "Neutral unbalance current (CT between the wye neutrals)", "A", [0, 20], 0.004,
      "IEC 61850: PTOC / ZCAP neutral"),
    P("breaker_closed", "Switching.BreakerClosed", "Bank breaker closed (1) / open (0)", "code", [0, 1], 0, "IEC 61850: XCBR.Pos"),
    P("switching_ops", "Switching.Operations", "Breaker operations", "count", [0, 1e7], 0, "IEC 61850: XCBR.OpCnt"),
    P("last_switch_overvoltage_pu", "Switching.LastOvervoltage", "Peak overvoltage of the last de-energisation", "pu", [0, 5], 0.01,
      "IEC 61850: RDRE (disturbance record)"),
    P("reactor_temp_c", "Reactor.Temperature", "Series reactor temperature (hottest phase)", "degC", [-20, 250], 0.15, "IEC 61850: ZRCT / STMP"),
    P("ambient_temp_c", "Weather.Ambient", "Ambient temperature", "degC", [-40, 70], 0.1, "IEC 61850: MMET.EnvTmp"),
    P("pressure_switch_count", "Units.PressureSwitches", "Unit pressure monitoring devices operated", "count", [0, 24], 0, "IEC 61850: SIML / GGIO"),
    P("relay_status", "Protection.RelayStatus", "Unbalance relay: 0 normal, 1 alarm, 2 trip", "code", [0, 2], 0, "IEC 61850: PTOC.Str / Op"),
]

failure_modes = {
    "element_failures": {"label": "Element failures (internal fuses blowing)",
                         "cause": "Elements puncture one by one; each internal fuse isolates its element in microseconds. The group loses capacitance, "
                                  "the neutral current steps up and the remaining elements of that group carry more voltage",
                         "detect": ["neutral_current_a", "failed_elements_est", "element_overvoltage_pct"],
                         "action": "Plan an outage: measure the units' capacitance, replace the unit with blown fuses before a third fuse blows", "default_ramp_min": 3},
    "can_bulging": {"label": "Can bulging (internal gassing)",
                    "cause": "A unit with an internal fault gasses: the case swells, its pressure monitoring device operates and more element fuses "
                             "blow until the unbalance relay trips the bank",
                    "detect": ["pressure_switch_count", "neutral_current_a", "relay_status"],
                    "action": "Keep the bank out of service, replace the bulged unit, check the others for case deformation", "default_ramp_min": 2},
    "overvoltage_stress": {"label": "Overvoltage stress (bank left on at light load)",
                           "cause": "The VAR controller leaves the bank in at night: the bus rises, the units run above rated voltage and the crest "
                                    "with harmonics approaches the IEEE 18 peak limit",
                           "detect": ["unit_voltage_pu", "peak_voltage_pu", "bus_voltage_kv"],
                           "action": "Fix the VAR / voltage controller settings; switch the bank out at light load", "default_ramp_min": 2},
    "harmonic_resonance": {"label": "Harmonic resonance (7th)",
                           "cause": "A network change lowers the short-circuit power, the bank's parallel resonance moves to the 7th harmonic "
                                    "and a nearby converter's 7th current is amplified in the bank",
                           "detect": ["current_thd_pct", "current_h7_pct", "current_rms_pu", "resonance_order"],
                           "action": "Change the switching arrangement, detune with a series reactor or add a filter; review the harmonic study", "default_ramp_min": 2},
    "reactor_overheating": {"label": "Series reactor overheating",
                            "cause": "A loose terminal or blocked air paths of the current-limiting reactor: it runs hotter than its current explains",
                            "detect": ["reactor_temp_c", "reactor_residual_k"],
                            "action": "Infrared scan, tighten the terminals, clean the reactor; check for harmonic overload", "default_ramp_min": 3},
    "neutral_ct_fault": {"label": "Unbalance CT open (protection blind)",
                         "cause": "The neutral CT's secondary circuit is open: the relay reads almost nothing while elements keep failing. "
                                  "The phase currents still drift apart",
                         "detect": ["neutral_current_a", "phase_asymmetry_pct", "failed_from_asymmetry"],
                         "action": "Take the bank out, repair the CT circuit, then measure the units", "default_ramp_min": 3},
    "restrike": {"label": "Breaker restrike on opening",
                 "cause": "A worn vacuum or SF6 interrupter restrikes when it opens the bank: the trapped charge drives overvoltages up to ~3 pu",
                 "detect": ["last_switch_overvoltage_pu", "switching_ops"],
                 "action": "Overhaul or replace the capacitor switching breaker; check the surge arresters", "default_ramp_min": 1},
}

twin = {
    "$comment": "Single source of truth for the CAP-1101 digital twin: 33 kV shunt capacitor bank of 24 Vishay ESTA internally fused "
                "1-phase units (10.1 kV, 400 kvar), ungrounded double wye with neutral unbalance protection. Unit data from Vishay doc 13045; "
                "unbalance and overvoltage from the bank circuit (IEEE C37.99 method); limits IEEE 18 / IEC 60871.",
    "twin": {"id": "urn:maximo:twin:capacitorbank:CAP-1101", "version": "1.0.0",
             "kind": "Shunt capacitor bank, ungrounded double wye, internally fused units, neutral unbalance protection",
             "standards": {
                 "performance": f"Vishay ESTA Pha... HVAC 1-phase: {UN_KV} kV, {Q_UNIT_KVAR:.0f} kvar at 50 Hz, internal fuses, < 0.15 W/kvar, "
                                "discharge 75 V / 10 min, -50/+55 C",
                 "protection": "IEEE C37.99 method: neutral current per failed element, alarm on the first, trip before 110 % on the remaining elements",
                 "limits": "IEEE Std 18-2002: 110 % rms voltage, 120 % peak voltage, 135 % rms current, 135 % kvar; IEC 60871-1 1.10 Un",
                 "information_model": "Points named after IEC 61850 logical nodes (MMXU, MHAI, PTOC, PTOV, XCBR, ZRCT, MMET, RDRE)"}},
    "identification": {"assetnum": "CAP-1101", "description": "Shunt capacitor bank 1101 (33 kV bus 1, 8.5 Mvar)",
                       "manufacturer": "Vishay ESTA (units)", "model": "Pha... HVAC 1-phase 10.1 kV 400 kvar, 24 units, double wye",
                       "site": "Demo transmission substation", "location": "Substation 33 kV bus 1 / capacitor bay 1",
                       "medium": "All-film units in synthetic oil, outdoor rack"},
    "design": {
        "unit": {"rated_kv": UN_KV, "kvar_50hz": Q_UNIT_KVAR, "rated_current_a": round(I_UNIT_RATED, 2), "capacitance_uf": round(C_UNIT, 4),
                 "bil_kvp": 95, "losses_w_per_kvar": 0.15, "discharge": "75 V in 10 min", "temperature_category_c": [-50, 55],
                 "tolerance_pct": [-5, 10], "dimensions_mm": [345, 175, 685], "fusing": "internal fuses + pressure monitoring device",
                 "series_groups": S, "elements_per_group": N, "element_kv": round(UN_KV / S, 3),
                 "assumed": "4 series groups x 18 elements per unit (element ~2.5 kV, inside the 1.5-2.5 kV range of the application note)"},
        "bank": {"nominal_kv": VN, "frequency_hz": 50, "connection": "ungrounded double wye, neutrals tied through the unbalance CT",
                 "series_levels": LEVELS, "parallel_units": PARALLEL, "units": 24,
                 "capacitance_per_phase_uf": round(C_PH, 4), "leg_capacitance_uf": round(C_LEG, 4),
                 "q_mvar_at_nominal": round(base["q_mvar"], 3), "q_mvar_at_rated_unit_voltage": 24 * Q_UNIT_KVAR / 1000,
                 "rated_phase_current_a": round(I_PH_RATED, 2), "current_at_nominal_a": round(sum(base["i_phase"]) / 3, 2),
                 "unit_voltage_at_nominal_pu": round(VN / math.sqrt(3) / LEVELS / UN_KV, 4),
                 "assumed": "33 kV bus and the 2 x 2 arrangement per leg are this demo's design"},
        "protection": {"inherent_unbalance_a_per_kv": round(inherent / VN, 7), "neutral_a_per_element_per_kv": round(k1, 7),
                       "neutral_a_per_element_at_nominal": round(k1 * VN, 4), "asym_pct_per_element": round(asym1, 5),
                       "alarm_elements": 0.5, "trip_elements": 2.5, "table": table,
                       "note": "Inherent unbalance from a +0.06 % capacitance tolerance on one leg (assumed), subtracted as the relay's "
                               "commissioning compensation; failures assumed in one group (worst case, as in C37.99 settings)"},
        "network": {"ssc_mva": 700.0, "ssc_weak_mva": 410.0, "q_damp": 8.0, "source_h5_pct": 2.0, "source_h7_pct": 3.0,
                    "resonance_order_nominal": round(math.sqrt(700.0 / base["q_mvar"]), 2),
                    "assumed": "short-circuit power, harmonic source currents and damping are assumptions for this demo network"},
        "reactor": {"type": "air-core current-limiting reactor, one per phase", "rated_current_a": 200.0, "dt_rated_k": 55.0, "tau_min": 20.0,
                    "assumed": "reactor rating and temperature rise are assumptions"},
        "switching": {"energise_h": 6.0, "deenergise_h": 23.0, "normal_overvoltage_pu": 1.15,
                      "note": "VAR controller switches the bank in at 06:00 and out at 23:00 plant time"},
        "ieee18_limits": {"rms_voltage_pu": 1.10, "peak_voltage_pu": 1.20, "rms_current_pu": 1.35, "kvar_pu": 1.35},
        "demo": {"time_scale": 30, "note": "The plant clock runs 30x real time (one day in 48 min). Element failures are counted as whole "
                                           "fuses; the restrike fault forces a switching cycle about every 90 s so the event shows within minutes."},
    },
    "telemetry": {"event": "capbank", "publish_every_s": 5, "device_type": "CAPACITOR_BANK",
                  "groups": {"Bus": "33 kV bus", "Bank": "Bank currents and power", "Harmonics": "Power quality IED",
                             "Unbalance": "Neutral unbalance CT", "Switching": "Bank breaker", "Reactor": "Series reactors",
                             "Weather": "Weather station", "Units": "Unit pressure switches", "Protection": "Unbalance relay"},
                  "points": points},
    "twin_model": {"limits": {"failed_alarm": 0.5, "failed_trip": 2.5, "blind_asym_elements": 2.0, "q_low_pct": -2.0,
                              "unit_voltage_alert_pu": 1.05, "peak_voltage_pu": 1.20, "current_thd_alert_pct": 25.0, "rms_current_pu": 1.35,
                              "reactor_residual_alert_k": 15.0, "switch_overvoltage_alert_pu": 2.0, "ambient_alert_c": 55}},
    "failure_modes": failure_modes,
    "presentation": {
        "category": "Capacitor bank",
        "kpis": [{"metric": "bank_q_mvar", "label": "Q", "unit": "Mvar", "decimals": 2},
                 {"metric": "bus_voltage_kv", "label": "Bus", "unit": "kV", "decimals": 2},
                 {"metric": "neutral_current_a", "label": "Neutral", "unit": "A", "decimals": 3},
                 {"metric": "current_thd_pct", "label": "THD", "unit": "%", "decimals": 1}],
        "twin_kpis": [{"metric": "failed_elements_est", "label": "Blown fuses (est.)", "unit": "", "decimals": 1},
                      {"metric": "element_overvoltage_pct", "label": "Element overvoltage", "unit": "%", "decimals": 1}],
        "compare": [
            {"label": "Reactive power", "measured": "bank_q_mvar", "expected": "q_expected_mvar", "unit": "Mvar", "decimals": 3,
             "basis": f"Q = V²ωC, C = {C_PH:.2f} µF per phase (24 x 400 kvar at 10.1 kV)"},
            {"label": "Bank current (mean)", "measured": None, "expected": "current_expected_a", "unit": "A", "decimals": 1, "basis": "Q / (√3 V)"},
            {"label": "Neutral current (compensated)", "measured": "neutral_compensated_a", "expected": None, "unit": "A", "decimals": 3,
             "basis": f"{k1 * VN:.3f} A per blown fuse at 33 kV"},
            {"label": "Blown fuses, from the neutral", "measured": "failed_elements_est", "expected": None, "unit": "", "decimals": 2,
             "basis": "alarm 0.5, trip 2.5"},
            {"label": "Blown fuses, from phase currents", "measured": "failed_from_asymmetry", "expected": None, "unit": "", "decimals": 2,
             "basis": f"{asym1:.3f} % phase spread per blown fuse"},
            {"label": "Element voltage", "measured": "element_voltage_pu", "expected": None, "unit": "pu", "decimals": 3, "basis": "IEC 60871-1 1.10 Un"},
            {"label": "Series reactor", "measured": "reactor_residual_k", "expected": "reactor_temp_expected_c", "unit": "K / °C", "decimals": 1,
             "basis": "ambient + 55 K x (I / 200 A)²"},
        ],
        "trends": [{"metric": "failed_elements_est", "label": "Blown fuses (est.)"}, {"metric": "q_deviation_pct", "label": "Q vs. V²ωC (%)"},
                   {"metric": "current_thd_pct", "label": "Current THD (%)"}, {"metric": "reactor_residual_k", "label": "Reactor vs. expected (K)"}],
        "design": [
            {"label": "Units", "value": "24 x Vishay ESTA 10.1 kV 400 kvar internally fused, < 0.15 W/kvar, -50/+55 °C"},
            {"label": "Bank", "value": f"33 kV ungrounded double wye, 2 series x 2 parallel per leg, {base['q_mvar']:.2f} Mvar at 33 kV"},
            {"label": "Protection", "value": f"neutral unbalance CT: {k1 * VN:.3f} A per blown fuse, alarm 1 fuse, trip 3 fuses (> 10 % on the rest)"},
            {"label": "Source", "value": "Vishay doc 13045 (units); bank design, network and reactor assumed; 3D drawn from the unit dimensions, not CAD"},
        ],
    },
}

if __name__ == "__main__":
    out = HERE / "twin" / "cap-1101.twin.json"
    out.parent.mkdir(exist_ok=True)
    json.dump(twin, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("written", out)
    print(f"C_unit {C_UNIT:.3f} uF, C_phase {C_PH:.3f} uF, Q@33kV {base['q_mvar']:.3f} Mvar, I@33kV {sum(base['i_phase']) / 3:.1f} A, "
          f"inherent {inherent:.4f} A, In/element {k1 * VN:.4f} A, asym/element {asym1:.4f} %, h_r {math.sqrt(700 / base['q_mvar']):.2f}")
    for row in table:
        print(row)
