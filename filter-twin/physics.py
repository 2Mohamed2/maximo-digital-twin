"""Physics model of FLT-1401 (rapid gravity dual-media filter on a Leopold Universal Type S underdrain): the stand-in for the real cell.

Per step (dt real seconds; the plant clock runs `time_scale` times faster, see design.demo):
  demand     plant flow split: the cell's flow setpoint follows a day profile (0.85-1.05 x 480 m3/h); constant-level
             control keeps ~1.5 m of water above the media by opening the effluent valve as head loss grows
  settled    settled-water turbidity ~2.2 NTU with a day swing; TSS = 1.5 x NTU
  run        stored solids M (kg/m2) = integral of rate x TSS; deposit head loss grows with M (k 2.58 m per kg/m2) and scales
             with rate and viscosity; clean-bed loss Carman-Kozeny; underdrain ~ v^2; breakthrough when M nears the capacity
  backwash   triggered by total head loss >= 2.4 m, run >= 36 h, or effluent >= 0.3 NTU for 30 min: drain-down 5 min,
             air scour 4 min (60 m/h), water 8 min (55 m/h, bed expansion by Richardson-Zaki), then filter-to-waste 20 min
             with the ripening turbidity peak
  faults     mudballs raise the clean bed; media_loss lowers the bed depth; air_binding drops the level and adds air-pocket
             loss (negative head at the interface); short_circuiting bypasses the media; underdrain_failure lowers the
             underdrain loss, spoils the backwash and lets particles through; valve_sticking makes the flow hunt;
             coagulation_upset: more solids, faster head loss, lower capacity; turbidimeter_drift: the instrument reads high
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


# backwash sequence, plant minutes
SEQ = [("drain", 5), ("air", 4), ("water", 8)]


class Plant:
    def __init__(self, twin, seed=1401):
        self.twin, self.rng = twin, random.Random(seed)
        self.d = twin["design"]
        self.k = tc._k(twin)
        self.scale = float(self.d.get("demo", {}).get("time_scale", 1))
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0                    # plant clock, seconds
        self.running, self.trip = True, 0
        self.state = 0                  # 0 filtering, 1 backwash, 2 filter-to-waste, 3 standby
        self.phase, self.phase_t = None, 0.0
        self.run_h, self.run_vol, self.M, self.D = 6.0, 0.0, 0.0, 0.0
        self.c_sum, self.c_n = 0.0, 0
        self.since_bw_min = 600.0
        self.high_turb_min = 0.0
        self.bw_count = 4120
        self.flow = self.d["operation"]["flow_design_m3h"]
        self.valve = 35.0
        self.c_bias = 0.0
        self.c_avg = 2.2
        # start part-way into a run
        rate = self.flow / self.k["A"]
        self.run_vol = rate * self.k["A"] * self.run_h
        self.M = rate * self.run_h * 2.2 * self.k["tss"] / 1000
        self.D = self.k["K"] * self.M
        self.c_sum, self.c_n = 2.2 * 100, 100

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.trip, self.running = 0, True

    def fault_state(self):
        return {k: round(v.sev, 3) for k, v in self.faults.items()}

    # ---------------------------------------------------------------- helpers
    def setpoint(self):
        h = (self.t / 3600.0) % 24
        return self.d["operation"]["flow_design_m3h"] * (0.95 + 0.07 * math.sin((h - 10) / 24 * 2 * math.pi) + 0.02 * math.sin(self.t / 5300))

    def settled(self):
        h = (self.t / 3600.0) % 24
        self.c_bias = 0.999 * self.c_bias + self.rng.gauss(0, 0.004)
        c = 2.2 + 0.35 * math.sin((h - 15) / 24 * 2 * math.pi) + self.c_bias
        return max(0.6, c + 1.6 * self.faults["coagulation_upset"].sev)

    def temp(self):
        h = (self.t / 3600.0) % 24
        return 18.0 + 1.2 * math.sin((h - 16) / 24 * 2 * math.pi)

    def start_backwash(self):
        self.state, self.phase, self.phase_t = 1, 0, 0.0
        self.bw_count += 1

    # ---------------------------------------------------------------- step
    def step(self, dt=1.0):
        f, d, k = self.faults, self.d, self.k
        for x in f.values():
            x.step(dt)
        pdt = dt * self.scale
        pmin, ph = pdt / 60.0, pdt / 3600.0
        self.t += pdt
        T = self.temp()
        mur = tc.mu_rel(T)
        C = self.settled()
        sp = self.setpoint()
        op = d["operation"]
        mud, loss, air, sc = f["mudballs"].sev, f["media_loss"].sev, f["air_binding"].sev, f["short_circuiting"].sev
        ud, vs, co, td = f["underdrain_failure"].sev, f["valve_sticking"].sev, f["coagulation_upset"].sev, f["turbidimeter_drift"].sev
        anth_depth = d["media"]["anthracite"]["depth_m"] * (1 - 0.25 * loss)
        bw_flow, air_flow, expansion, level = 0.0, 0.0, 0.0, d["cell"]["water_depth_m"]
        flow, hunt = 0.0, 0.0
        if self.state == 1:                                           # backwash sequence
            self.phase_t += pmin
            name, dur = SEQ[self.phase]
            if name == "drain":
                level = d["cell"]["water_depth_m"] * max(0.0, 1 - self.phase_t / dur) * 0.8 + 0.2
            elif name == "air":
                level, air_flow = 0.2, d["backwash"]["air_m_h"] * k["A"] * (1 - 0.3 * ud)
            else:
                bw_flow = d["backwash"]["rate_m_h"] * k["A"]
                level = 0.6 + 0.5 * min(1.0, self.phase_t / 3)
                expansion = tc.expansion_expected(k, T, bw_flow / k["A"]) * (1 - 0.55 * ud)
            if self.phase_t >= dur:
                self.phase, self.phase_t = self.phase + 1, 0.0
                if self.phase >= len(SEQ):                             # clean bed, start filter-to-waste
                    self.state, self.phase = 2, None
                    self.run_h, self.run_vol, self.M, self.D, self.c_sum, self.c_n = 0.0, 0.0, 0.0, 0.0, 0.0, 0
                    self.since_bw_min = 0.0
            self.valve = 0.0
        else:
            # rate control: the effluent valve follows the setpoint; a sticking valve makes the flow hunt (stick-slip)
            stick = ((self.t / 60.0) % 23) / 23.0
            hunt = vs * 0.16 * (2 * abs(2 * stick - 1) - 1)
            flow = sp * (1 + hunt)
            self.since_bw_min += pmin
            if self.state == 2 and self.since_bw_min >= op["ftw_min"]:
                self.state = 0
        self.flow = flow
        rate = flow / k["A"]
        vr = rate / k["v0"]
        # run accounting (filtering and filter-to-waste)
        if self.state in (0, 2):
            self.run_h += ph
            self.run_vol += flow * ph
            tss = C * d["deposit"]["tss_per_ntu"]
            dM = rate * tss / 1000 * ph
            self.M += dM
            self.D += k["K"] * (1 + 2.0 * co) * dM
            self.c_sum += C
            self.c_n += 1
        self.c_avg = self.c_sum / self.c_n if self.c_n else C
        # head losses (m)
        clean_a = k["ha"] * (anth_depth / d["media"]["anthracite"]["depth_m"]) * (1 + 0.6 * mud) * vr * mur
        clean_s = k["hs"] * (1 + 0.6 * mud) * vr * mur
        dep = self.D * vr * mur
        share = d["deposit"]["anthracite_share"] + 0.3 * air
        pockets = 0.8 * air * min(1.0, vr)
        h_anth = (clean_a + share * dep + pockets) * (1 - 0.3 * sc)
        h_media = (clean_a + clean_s + dep + pockets) * (1 - 0.3 * sc)
        h_ud = k["hu"] * vr ** 2 * (1 - 0.55 * ud)
        if self.state != 1:
            level = d["cell"]["water_depth_m"] - 1.2 * air
        h_tot = h_media + h_ud
        head = level + anth_depth - h_anth
        if self.state in (0, 2):
            self.valve = max(5.0, min(100.0, 18 + 30 * h_tot + 9 * (vr - 1) + 150 * hunt))
        # effluent quality: base + ripening after backwash + breakthrough + fault paths
        cap = d["deposit"]["capacity_kg_m2"] * (1 - 0.6 * co)
        ripen = 0.32 * math.exp(-self.since_bw_min / 10.0) * (1 + 1.5 * ud)
        brk = 0.9 / (1 + math.exp(-(self.M - cap) / 0.06))
        turb = 0.045 + 0.008 * C + ripen + brk + 0.27 * sc + 0.12 * ud + 0.03 * loss + 0.06 * co
        if self.state == 1:
            turb = 0.0
        particles = 15 + 400 * max(0.0, turb - 0.05) if self.state != 1 else 0.0
        reading = turb + 0.30 * td if self.state != 1 else 0.0
        # backwash triggers (PLC): head loss, run time, effluent turbidity reading sustained 30 min
        if self.state == 0:
            self.high_turb_min = self.high_turb_min + pmin if reading >= op["breakthrough_backwash_ntu"] else 0.0
            if h_tot >= op["terminal_headloss_m"] or self.run_h >= op["max_run_h"] or self.high_turb_min >= 30:
                self.high_turb_min = 0.0
                self.start_backwash()
        bed = (anth_depth + d["media"]["sand"]["depth_m"]) if self.state != 1 else 0.0
        return {"filter_state": self.state, "flow_m3h": flow, "flow_setpoint_m3h": sp, "effluent_valve_pct": self.valve,
                "water_level_m": level, "headloss_media_m": h_media if self.state != 1 else 0.0,
                "underdrain_dp_m": h_ud if self.state != 1 else 0.0, "headloss_total_m": h_tot if self.state != 1 else 0.0,
                "bed_pressure_head_m": head if self.state != 1 else level,
                "settled_turbidity_ntu": C, "settled_turbidity_avg_ntu": self.c_avg, "effluent_turbidity_ntu": reading,
                "particle_count_ml": particles, "water_temp_c": T, "run_time_h": self.run_h, "run_volume_m3": self.run_vol,
                "backwash_flow_m3h": bw_flow, "air_scour_nm3h": air_flow, "bed_expansion_pct": expansion,
                "bed_depth_m": bed if self.state != 1 else anth_depth + d["media"]["sand"]["depth_m"],
                "backwash_count": self.bw_count}

    def measure(self, true):
        out = {}
        for p in self.twin["telemetry"]["points"]:
            k = p["metric"]
            v = true[k]
            if p["noise"] and not (k in ("bed_expansion_pct", "backwash_flow_m3h", "air_scour_nm3h") and v == 0):
                v = v + self.rng.gauss(0, p["noise"])
            lo, hi = p["range"]
            v = max(lo, min(hi, v))
            out[k] = int(v) if k in ("filter_state", "backwash_count") else round(v, 4 if abs(v) < 10 else 2)
        return out
