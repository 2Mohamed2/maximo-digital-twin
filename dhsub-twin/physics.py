"""A stand-in for DH-7101: building, heating circuit, plate heat exchangers, control valve, DHW and heat meter, with faults.

The real substation sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests, the figures and the live pages. Pure Python (math, random), so it also runs in the browser.

Building (radiators taken as linear, room held at 20 °C on the design curve):
    Q = Ub (Troom - Tout) = Kr ((Tflow + Tret)/2 - Troom) = k Vs (Tflow - Tret)
Heating exchanger: counterflow effectiveness-NTU with UA = 1 / (Rp + Rs + Rfoul), Rp, Rs ~ flow^-n.
The controller finds the primary flow that holds the flow temperature on its setpoint; the valve opening follows from
the flow, the differential pressure across the section and an equal-percentage characteristic.
"""
import math
import random


def eps_counterflow(ntu, cr):
    if cr > 0.999:
        return ntu / (1 + ntu)
    e = math.exp(-ntu * (1 - cr))
    return (1 - e) / (1 - cr * e)


class Substation:
    def __init__(self, twin, seed=1):
        self.t = twin
        d = twin["design"]
        self.h, self.w, self.c, self.v, self.m = d["heating"], d["dhw"], d["curve"], d["valve"], d["meter"]
        self.net = d["network"]
        self.K = self.m["k_kwh_m3k"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        h = self.h
        self.kr = h["q_kw"] / ((h["secondary_supply_c"] + h["secondary_return_c"]) / 2 - self.c["room_c"])
        self.ub = h["q_kw"] / (self.c["room_c"] - self.c["outdoor_design_c"])

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    def curve(self, t_out):
        c = self.c
        x = c["room_c"] + (self.h["secondary_supply_c"] - c["room_c"]) * (c["room_c"] - t_out) / (c["room_c"] - c["outdoor_design_c"])
        return min(max(x, c["supply_min_c"]), c["supply_max_c"])

    # heating exchanger -----------------------------------------------------------------------------------------------
    def ua(self, mp, ms):
        h, f = self.h, self.faults
        r0 = 1.0 / h["ua_kw_k"]
        rp = h["film_split"] * r0 * (h["primary_flow_m3h"] / max(mp, 1e-4)) ** h["ua_flow_exponent"]
        rs = (1 - h["film_split"]) * r0 * (h["secondary_flow_m3h"] / ms) ** h["ua_flow_exponent"]
        return 1.0 / (rp + rs + 0.9 * r0 * f["hex_fouling"])

    def hex_duty(self, mp, ms, tpin, tsin):
        cp, cs = self.K * mp, self.K * ms
        cmin, cmax = min(cp, cs), max(cp, cs)
        e = eps_counterflow(self.ua(mp, ms) / cmin, cmin / cmax)
        return e * cmin * (tpin - tsin)

    def building(self, tflow, ms, t_out):
        cs = self.K * ms
        q = self.kr * (tflow - t_out) / (1 + self.kr / (2 * cs) + self.kr / self.ub)
        q = max(q, 0.0)
        return q, tflow - q / cs

    def mp_max(self, dp):
        v = self.v
        return math.sqrt(dp / (100.0 / v["kvs_m3h"] ** 2 + v["dp_hex_design_kpa"] / self.h["primary_flow_m3h"] ** 2))

    def heating(self, t_out, tpin, ms, setp, dp):
        """Primary flow, flow temperature, return temperatures and heat of the heating circuit."""
        q, tret = self.building(setp, ms, t_out)
        mmax = self.mp_max(dp)
        if self.hex_duty(mmax, ms, tpin, tret) >= q:
            lo, hi = 1e-4, mmax
            for _ in range(60):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if self.hex_duty(mid, ms, tpin, tret) < q else (lo, mid)
            mp, tflow = (lo + hi) / 2, setp
        else:                       # valve fully open: the flow temperature falls until the exchanger matches the building
            lo, hi = t_out, setp
            for _ in range(60):
                mid = (lo + hi) / 2
                qb, tr = self.building(mid, ms, t_out)
                lo, hi = (mid, hi) if self.hex_duty(mmax, ms, tpin, tr) > qb else (lo, mid)
            mp, tflow = mmax, (lo + hi) / 2
            q, tret = self.building(tflow, ms, t_out)
        tpo = tpin - q / (self.K * mp)
        return dict(mp=mp, tflow=tflow, tret=tret, q=q, tpo=tpo)

    def true_state(self, t_out, tap_lpm, tpin=None):
        f, h, w, v = self.faults, self.h, self.w, self.v
        tpin = self.net["supply_c"] if tpin is None else tpin
        ms = h["secondary_flow_m3h"] * (1 + 1.0 * f["secondary_overflow"])
        setp = self.curve(t_out) + 12.0 * f["curve_too_high"]
        dp = v["dp_setpoint_kpa"] + (v["dp_network_kpa"] - v["dp_setpoint_kpa"]) * f["dp_controller_fault"]
        sh = self.heating(t_out, tpin, ms, setp, dp)
        # valve opening (equal percentage)
        dpv = max(dp - v["dp_hex_design_kpa"] * (sh["mp"] / h["primary_flow_m3h"]) ** 2, 0.5)
        kv = sh["mp"] / math.sqrt(dpv / 100.0)
        pos = 1 + math.log(max(kv / v["kvs_m3h"], 1e-6)) / math.log(v["rangeability"])
        pos = min(max(pos, 0.0), 1.0)
        # DHW: instantaneous heater + circulation loop
        dhw = w["setpoint_c"] - 9.0 * f["dhw_setpoint_low"]
        circ_ret = dhw - 4.5 - 10.0 * f["dhw_circulation_fault"]
        circ = w["circulation_flow_m3h"] * (1 - 0.9 * f["dhw_circulation_fault"])
        tap = tap_lpm * 0.06
        q_dhw = self.K * (tap * (dhw - w["cold_water_c"]) + circ * (dhw - circ_ret))
        tin = (tap * w["cold_water_c"] + circ * circ_ret) / max(tap + circ, 1e-6)
        tpo_dhw = tin + 3.0 + 5.0 * q_dhw / w["q_kw"]
        mp_dhw = q_dhw / (self.K * (tpin - tpo_dhw))
        byp = 0.3 * f["primary_bypass"]
        flow = sh["mp"] + mp_dhw + byp
        t2 = (sh["mp"] * sh["tpo"] + mp_dhw * tpo_dhw + byp * tpin) / flow
        # loop quality: low authority -> high loop gain -> hunting
        a = v["dpv100_kpa"] / dp
        g = v["authority_design"] / a
        return dict(t_out=t_out, tpin=tpin, ms=ms, setp=setp, dp=dp, pos=pos, a=a, g=g, dhw=dhw, circ_ret=circ_ret,
                    tap_lpm=tap_lpm, q_dhw=q_dhw, mp_dhw=mp_dhw, byp=byp, flow=flow, t2=t2, **sh)

    def measure(self, s):
        f, w = self.faults, self.w
        t1 = s["tpin"] + self.n(0.03) - 4.0 * f["meter_sensor_fault"]
        t2 = s["t2"] + self.n(0.03)
        flow = s["flow"] * (1 + self.n(0.004))
        hunt = max(0.0, s["g"] - 1.5)
        return {
            "hm_t_supply_c": round(t1, 2), "hm_t_return_c": round(t2, 2), "hm_flow_m3h": round(flow, 4),
            "hm_power_kw": round(self.K * flow * (t1 - t2), 3), "hm_info_code": 0,
            "p_supply_c": round(s["tpin"] + self.n(0.05), 2), "p_return_c": round(s["t2"] + self.n(0.05), 2),
            "sh_p_return_c": round(s["tpo"] + self.n(0.03), 2), "outdoor_c": round(s["t_out"] + self.n(0.1), 2),
            "sh_flow_c": round(s["tflow"] + self.n(0.1), 2), "sh_flow_set_c": round(s["setp"], 2),
            "sh_return_c": round(s["tret"] + self.n(0.03), 2), "sh_pump_flow_m3h": round(s["ms"] * (1 + self.n(0.004)), 4),
            "valve_pos_pct": round(100 * s["pos"] + self.n(0.5), 1),
            "valve_reversals_h": round(max(0.0, 6 + 25 * hunt + self.n(1.5))), "sh_flow_rms_k": round(abs(0.4 + 0.9 * hunt + self.n(0.05)), 2),
            "dp_section_kpa": round(s["dp"] + self.n(1.0), 1),
            "dhw_c": round(s["dhw"] + self.n(0.3), 2), "dhw_flow_lpm": round(s["tap_lpm"], 2), "cw_c": round(w["cold_water_c"] + self.n(0.1), 2),
            "dhw_circ_return_c": round(s["circ_ret"] + self.n(0.3), 2),
        }


class Fault:
    """A failure mode whose severity ramps towards a target (0..1)."""
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
    """The live stand-in used by the twin pages (same interface as the other twins' Plant).

    The outdoor temperature swings between demo.outdoor_min_c and demo.outdoor_max_c over demo.outdoor_period_s real
    seconds; hot water is tapped in short random draws about demo.tap_share of the time. Both follow the demo clock, not
    the time of day, so the page looks the same whenever it is opened.
    """

    def __init__(self, twin, seed=7101):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.lo, self.hi = float(demo.get("outdoor_min_c", -4)), float(demo.get("outdoor_max_c", 6))
        self.period = float(demo.get("outdoor_period_s", 1200))
        self.share = float(demo.get("tap_share", 0.2))
        self.s = Substation(twin, seed)
        self.rnd = random.Random(seed + 1)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.clock = 0.0
        self.running, self.trip = True, 0
        self.tap_left, self.tap_lpm = 0.0, 0.0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.clock = 0.0
        self.tap_left, self.tap_lpm = 0.0, 0.0
        self.running, self.trip = True, 0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.s.faults[k] = f.sev
        self.t += dt * self.scale
        self.clock += dt
        if self.tap_left > 0:
            self.tap_left -= dt
            if self.tap_left <= 0:
                self.tap_lpm = 0.0
        elif self.rnd.random() < self.share * dt / 40.0:
            self.tap_left, self.tap_lpm = self.rnd.uniform(15, 60), self.rnd.uniform(4, 12)
        mid, amp = (self.lo + self.hi) / 2, (self.hi - self.lo) / 2
        t_out = mid - amp * math.cos(2 * math.pi * self.clock / self.period)
        tpin = self.s.net["supply_c"] + 0.8 * math.sin(2 * math.pi * self.clock / (self.period / 3))
        return self.s.true_state(t_out, self.tap_lpm, tpin)

    def measure(self, true):
        return self.s.measure(true)
