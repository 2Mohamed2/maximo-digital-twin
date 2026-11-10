"""Physics model of UV-1601 (TrojanUVSwiftSC D12, 12 LPHO amalgam lamps) at a drinking-water works: the stand-in for the real reactor.

Per step (dt real seconds; the plant clock runs `time_scale` times faster, see the twin file design.demo):
  flow      treated-water demand: day swing 470-650 m3/h around a slow random walk
  water     UVT 93-95 % (filtered surface water), inlet temperature 11-13 C
  lamps     12 lamps in two groups of 6 (one UV sensor per group); output = power fraction x age factor (linear to 0.80
            at 12,000 h) x sleeve transmittance (0.97 clean, a small saw-tooth between wipes); lamp hours run with the
            plant clock and the lamps are changed at 11,000 h (planned replacement)
  sensors   each sensor sees its own group through Ls = 3 cm of water: S = S0 (lit/6) P age sleeve 10^(-UVA Ls)
  control   dose pacing: the controller computes the validated dose from the lower sensor, UVT and flow (the twin's
            equation) and moves the ballast setpoint 60-100 % to hold 46 mJ/cm2
  heat      0.19 m3 of water in the chamber, lamp heat in, flow carries it out: exact first-order step; trip at 55 C
            (lamps off, status 2) until the operator resets with the reactor below 45 C and the flow back
  totals    month volume and off-specification volume (dose < 40, flow > 800, UVT < 80 %) - a month is 30 plant days
  faults    lamp_failure: lamps 1-2 out; lamp_end_of_life: lamp hours run to 14,500 h (lamp change skipped);
            sleeve_fouling: wiper stalls, sleeves to 0.67; uvt_drop: UVT to 72 %; sensor_drift: sensor 1 reads 0.75 x;
            ballast_fault: lamps get 0.70 x the commanded power, heat-sink +30 K; high_flow: flow to 950 m3/h;
            no_flow_overheat: flow to 0 with the lamps on
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


CW = 4186.0          # J/(kg K)
WATER_KG = 190.0     # chamber water
UA = 25.0            # W/K from the chamber to the room (assumed)


class Plant:
    def __init__(self, twin, seed=1601):
        self.twin, self.rng = twin, random.Random(seed)
        self.d = twin["design"]
        self.k = tc._k(twin)
        self.scale = float(self.d.get("demo", {}).get("time_scale", 1))
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 10 * 86400.0 + 6 * 3600       # plant clock: day 10 of the month, 06:00
        self.flow_bias = 0.0
        self.lamp_hours = 5200.0
        self.pct = 85.0
        self.t_water = 12.0
        self.t_reactor = 12.0
        self.trip = 0
        self.wipes = 41250
        self.vol = 10 * 24 * 560.0
        self.off = 310.0
        self.month = int(self.t // (30 * 86400))
        self.last_wipe = self.t
        self.n = self.k["n"]

    # ---------------------------------------------------------------- operator / sim hooks
    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        if self.faults["no_flow_overheat"].target < 0.9 and self.t_reactor < 45:
            self.trip = 0

    @property
    def running(self):
        return not self.trip

    def fault_state(self):
        return {k: round(v.sev, 3) for k, v in self.faults.items()}

    def demand(self):
        h = (self.t / 3600.0) % 24
        self.flow_bias = 0.999 * self.flow_bias + self.rng.gauss(0, 0.6)
        return 560 + 80 * math.sin((h - 9.0) / 24 * 2 * math.pi) + 15 * math.sin(self.t / 20000) + self.flow_bias

    # ---------------------------------------------------------------- step
    def step(self, dt=1.0):
        f, k = self.faults, self.k
        for x in f.values():
            x.step(dt)
        pdt = dt * self.scale
        self.t += pdt
        # process
        q = self.demand()
        q += f["high_flow"].sev * (950 - q)
        q *= 1 - f["no_flow_overheat"].sev
        q = max(q, 0.0)
        uvt = 94.0 + 0.6 * math.sin(self.t / 31000) + 0.2 * math.sin(self.t / 4100)
        uvt -= f["uvt_drop"].sev * (uvt - 72.0)
        self.t_water = 12.0 + 0.8 * math.sin(self.t / 86400 / 30 * 2 * math.pi)
        # lamps
        if not self.trip:
            self.lamp_hours += pdt / 3600
        if self.lamp_hours >= self.d["lamp_ageing"]["replace_at_h"]:
            self.lamp_hours = 0.0                                   # planned lamp change
        hours = self.lamp_hours + f["lamp_end_of_life"].sev * max(0.0, 14500 - self.lamp_hours)
        age = tc.age_factor(k, hours)
        out_g1 = 6 - (2 if f["lamp_failure"].sev > 0.5 else (1 if f["lamp_failure"].sev > 0.15 else 0))
        lit = [0, 0] if self.trip else [out_g1, 6]
        lamps_on = sum(lit)
        derate = 1 - 0.30 * f["ballast_fault"].sev
        pfrac = self.pct / 100 * derate
        # sleeves and wiper
        foul = f["sleeve_fouling"].sev
        wiper_fault = foul > 0.3
        every = self.d["wipe_every_h"] * 3600
        self.last_wipe = min(self.last_wipe, self.t)                 # the runtime may move the clock back to the time of day
        if not wiper_fault and self.t - self.last_wipe >= every:
            self.last_wipe = self.t
            self.wipes += 1
        since = (self.t - self.last_wipe) / every
        wiping = (not wiper_fault) and (self.t - self.last_wipe) < 180
        sleeve = self.d["clean_sleeve_factor"] * (1.005 - 0.012 * min(since, 1.0)) - 0.30 * foul
        # sensors (Beer-Lambert through Ls)
        _, ts, _ = tc.g_factor(k, uvt)
        base = k["S0"] * pfrac * age * sleeve * ts
        s1 = base * lit[0] / 6 * (1 - 0.25 * f["sensor_drift"].sev)
        s2 = base * lit[1] / 6
        power = k["kw"] * lamps_on * pfrac
        # dose pacing (controller uses the same equation as the twin)
        dose_ctl = tc.dose(k, min(s1, s2), uvt, q) if lamps_on else 0.0
        sp = self.d["dose_pacing"]
        if lamps_on and dose_ctl > 0:
            self.pct *= (sp["setpoint_mjcm2"] / dose_ctl) ** min(0.25 * dt, 1.0)
        self.pct = max(sp["min_pct"], min(sp["max_pct"], self.pct))
        # heat balance (exact first-order step over pdt)
        mdot = q / 3600 * 1000
        heat = power * 1000 * 0.9
        cap = WATER_KG * CW
        cond = mdot * CW + UA
        t_eq = (heat + mdot * CW * self.t_water + UA * 22.0) / cond
        self.t_reactor = t_eq + (self.t_reactor - t_eq) * math.exp(-pdt * cond / cap)
        if self.t_reactor > self.d["thermal"]["trip_c"]:
            self.trip = 1
        t_ballast = 30 + 12 * pfrac + 30 * f["ballast_fault"].sev if not self.trip else 26.0
        # totals
        m = int(self.t // (30 * 86400))
        if m != self.month:
            self.month, self.vol, self.off = m, 0.0, 0.0
        dv = q * pdt / 3600
        self.vol += dv
        if dv > 0 and (dose_ctl < k["req"] or q > k["qmax"] or uvt < k["uvtmin"]):
            self.off += dv
        status = 2 if self.trip else (1 if (lamps_on < self.n or wiper_fault or dose_ctl < k["req"]) else 0)
        return {"flow_m3h": q, "uvt_pct": uvt, "water_temp_c": self.t_water, "reactor_temp_c": self.t_reactor,
                "uv_intensity_1_wm2": s1, "uv_intensity_2_wm2": s2, "ballast_power_pct": 0.0 if self.trip else self.pct,
                "lamp_power_kw": power, "lamps_on": lamps_on, "lamp_hours": hours, "ballast_temp_c": t_ballast,
                "wiper_status": 2 if wiper_fault else (1 if wiping else 0), "wiper_cycles": self.wipes,
                "reactor_status": status, "volume_month_m3": self.vol, "offspec_month_m3": self.off,
                # not telemetry: for the viewer
                "_age": age, "_sleeve": sleeve, "_dose_ctl": dose_ctl}

    def measure(self, true):
        out = {}
        for p in self.twin["telemetry"]["points"]:
            k = p["metric"]
            v = true[k]
            if p["noise"]:
                v = v + self.rng.gauss(0, p["noise"])
            lo, hi = p["range"]
            v = max(lo, min(hi, v))
            out[k] = int(round(v)) if k in ("lamps_on", "wiper_status", "reactor_status", "wiper_cycles") else round(v, 4 if abs(v) < 10 else 2)
        return out
