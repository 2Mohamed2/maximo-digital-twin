"""Physics model of CAP-1101 (24 Vishay ESTA 10.1 kV / 400 kvar internally fused units, 33 kV ungrounded double wye) on a
substation bus: the stand-in for the real bank.

Per step (dt real seconds; the plant clock runs `time_scale` times faster, see the twin file design.demo):
  bus       33 kV bus with a day profile (lower at the afternoon peak, higher at night); the bank lifts it by about
            Q / Ssc while it is in
  switching VAR controller: bank in at 06:00, out at 23:00 plant time; every opening records the peak overvoltage
  circuit   exact phasor solution of the double wye (twin_calc.bank_circuit) with the true leg capacitances: blown
            element fuses (in one group of one unit, leg A-a) lower that leg; phase currents, neutral current and Q follow
  harmonics converter currents at the 5th and 7th, amplified by the bank / network parallel resonance h_r = sqrt(Ssc/Q)
  reactor   current-limiting air-core reactor: first-order temperature toward ambient + dT_rated (I/I_rated)^2
  relay     neutral unbalance relay on the (measured) neutral CT current: alarm at 0.5, trip at 2.5 estimated blown fuses;
            a trip opens the breaker and latches until the operator reset
  faults    element_failures (up to 2 fuses), can_bulging (up to 4 fuses + pressure switch, trips), overvoltage_stress
            (bank left in at light load, bus +12 %), harmonic_resonance (Ssc 700 -> 410 MVA, 7th source 3 -> 8 %),
            reactor_overheating (+35 K), neutral_ct_fault (CT reads 3 % while 3 fuses blow), restrike (opening overvoltage
            2.6-2.9 pu; a switching cycle every ~90 s real)
"""
import math
import random

import twin_calc as tc


class Fault:
    def __init__(self):
        self.sev, self.target, self.rate = 0.0, 0.0, 0.0

    def set(self, target, ramp_s):
        self.target = max(0.0, min(1.0, target))
        self.rate = abs(self.target - self.sev) / max(ramp_s, 1.0)

    def step(self, dt):
        if self.sev < self.target:
            self.sev = min(self.target, self.sev + self.rate * dt)
        elif self.sev > self.target:
            self.sev = max(self.target, self.sev - self.rate * dt)


class Plant:
    def __init__(self, twin, seed=1101):
        self.twin, self.rng = twin, random.Random(seed)
        self.d = twin["design"]
        self.k = tc._k(twin)
        self.scale = float(self.d.get("demo", {}).get("time_scale", 1))
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.closed = 1
        self.ops = 18240
        self.last_ov = 1.12
        self.t_react = 30.0
        self.relay = 0
        self.cycle_timer = 0.0
        self.forced_open = 0.0
        self.v_bias = 0.0
        u, b = self.d["unit"], self.d["bank"]
        self.cu, self.S, self.N = u["capacitance_uf"], u["series_groups"], u["elements_per_group"]
        self.cleg = b["leg_capacitance_uf"]
        self.tol = 0.0006

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        if self.blown() < 2.5:
            self.trip, self.running, self.relay = 0, True, 0

    def fault_state(self):
        return {k: round(v.sev, 3) for k, v in self.faults.items()}

    def blown(self):
        f = self.faults
        n = min(2, int(f["element_failures"].sev * 2.999))
        n += int(f["can_bulging"].sev * 4.999)
        n += int(f["neutral_ct_fault"].sev * 3.999)
        return min(n, self.N - 1)

    def in_window(self):
        h = (self.t / 3600.0) % 24
        sw = self.d["switching"]
        return sw["energise_h"] <= h < sw["deenergise_h"]

    def step(self, dt=1.0):
        f, d = self.faults, self.d
        for x in f.values():
            x.step(dt)
        pdt = dt * self.scale
        self.t += pdt
        h = (self.t / 3600.0) % 24
        amb = 34.0 + 9.0 * math.sin((h - 9.0) / 24 * 2 * math.pi) + 0.3 * math.sin(self.t / 7000)
        # VAR controller (+ overvoltage stress: left in at night) and the restrike demo cycle
        want = self.in_window() or f["overvoltage_stress"].sev > 0.05
        if f["restrike"].sev > 0.05:
            self.cycle_timer += dt
            if self.cycle_timer > 90:
                self.cycle_timer = 0.0
                self.forced_open = 20.0
        if self.forced_open > 0:
            self.forced_open -= dt
            want = False
        want = want and not self.trip
        if self.closed and not want:                       # opening: record the overvoltage of this de-energisation
            self.ops += 1
            rs = f["restrike"].sev
            self.last_ov = (d["switching"]["normal_overvoltage_pu"] + self.rng.uniform(-0.03, 0.03)) if rs < 0.3 else \
                2.6 + 0.3 * rs + self.rng.uniform(-0.05, 0.05)
        if not self.closed and want:
            self.ops += 1
        if f["restrike"].sev == 0 and f["restrike"].target == 0 and self.last_ov > 2.0:
            self.last_ov = d["switching"]["normal_overvoltage_pu"]       # demo: Clear all = breaker overhauled
        self.closed = 1 if want else 0
        # bus voltage: day profile, bank lift, light-load overvoltage
        self.v_bias = 0.995 * self.v_bias + self.rng.gauss(0, 0.0004)
        load = 0.55 + 0.35 * math.exp(-((h - 15.0) / 4.0) ** 2) + 0.15 * math.exp(-((h - 21.0) / 2.0) ** 2)
        vpu = 1.035 - 0.05 * load + self.v_bias
        ssc = d["network"]["ssc_mva"] - (d["network"]["ssc_mva"] - d["network"]["ssc_weak_mva"]) * f["harmonic_resonance"].sev
        if self.closed:
            vpu += 8.5 / ssc
        vpu += 0.12 * f["overvoltage_stress"].sev
        V = d["bank"]["nominal_kv"] * vpu
        # circuit with the true leg capacitances
        nb = self.blown()
        ca = tc.leg_c(self.cu, self.S, self.N, nb) * (1 + self.tol)
        circ = tc.bank_circuit(V, {"A": [ca, self.cleg, self.cleg], "B": [self.cleg, self.cleg, self.cleg]})
        q = circ["q_mvar"] if self.closed else 0.0
        h_r = math.sqrt(ssc / max(q, 0.5)) if self.closed else 99.0
        src5 = d["network"]["source_h5_pct"]
        src7 = d["network"]["source_h7_pct"] + 5.0 * f["harmonic_resonance"].sev
        i5 = src5 * tc.amplification(5, h_r, d["network"]["q_damp"]) if self.closed else 0.0
        i7 = src7 * tc.amplification(7, h_r, d["network"]["q_damp"]) if self.closed else 0.0
        thd = math.hypot(i5, i7)
        rmsf = math.sqrt(1 + (thd / 100) ** 2)
        iph = [x * rmsf if self.closed else 0.0 for x in circ["i_phase"]]
        i_mean = sum(iph) / 3
        upu = V / math.sqrt(3) / d["bank"]["series_levels"] / d["unit"]["rated_kv"]
        peak = upu * (1 + i5 / 100 / 5 + i7 / 100 / 7) if self.closed else 0.0
        vthd = math.hypot(i5 / 5, i7 / 7) * 0.35 + 1.2 if self.closed else 1.0
        # neutral CT (open secondary under neutral_ct_fault)
        ct = 1.0 - 0.97 * min(1.0, f["neutral_ct_fault"].sev * 1.5)
        i_n = circ["i_neutral"] * ct if self.closed else 0.0
        # reactor temperature
        r = d["reactor"]
        target = amb + r["dt_rated_k"] * (i_mean / r["rated_current_a"]) ** 2 + 35.0 * f["reactor_overheating"].sev * (1 if self.closed else 0.2)
        self.t_react += (target - self.t_react) * (1 - math.exp(-pdt / (r["tau_min"] * 60)))
        # unbalance relay on the measured neutral current
        k = self.k
        est = max(0.0, i_n - k["inh"] * V) / (k["k1"] * V) if self.closed else 0.0
        if self.closed and est >= self.d["protection"]["trip_elements"]:
            self.trip, self.running = 1, False
        self.relay = 2 if self.trip else (1 if est >= self.d["protection"]["alarm_elements"] else 0)
        press = 1 if f["can_bulging"].sev > 0.6 else 0
        return {"bus_voltage_kv": V, "bank_current_l1_a": iph[0], "bank_current_l2_a": iph[1], "bank_current_l3_a": iph[2],
                "bank_q_mvar": q, "current_thd_pct": thd, "current_h7_pct": i7, "current_h5_pct": i5, "voltage_thd_pct": vthd,
                "peak_voltage_pu": peak, "neutral_current_a": i_n, "breaker_closed": self.closed, "switching_ops": self.ops,
                "last_switch_overvoltage_pu": self.last_ov, "reactor_temp_c": self.t_react, "ambient_temp_c": amb,
                "pressure_switch_count": press, "relay_status": self.relay}

    def measure(self, true):
        out = {}
        ints = ("breaker_closed", "switching_ops", "pressure_switch_count", "relay_status")
        for p in self.twin["telemetry"]["points"]:
            key = p["metric"]
            v = true[key]
            off = not true["breaker_closed"] and (key.startswith("bank_") or key.startswith("current_") or key in ("neutral_current_a", "peak_voltage_pu"))
            if p["noise"] and not off:
                v = v + self.rng.gauss(0, p["noise"])
            lo, hi = p["range"]
            v = max(lo, min(hi, v))
            out[key] = int(v) if key in ints else round(v, 5 if abs(v) < 1 else (4 if abs(v) < 10 else 3))
        return out
