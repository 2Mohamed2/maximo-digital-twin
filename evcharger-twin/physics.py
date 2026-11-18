"""A stand-in for EV-7001: the four Power-Stacks, the two liquid-cooled CCS2 cables and their cooling unit, the insulation
monitor and contactors, the payment terminal and the CSMS counters, charging two cars, with injectable faults.

The real charger, its OCPP messages and the CSMS send the same points (see telemetry.points in the twin file). Nothing here
is used by Monitor: the expected values are computed in Monitor from the twin file only. This model only produces believable
readings and fault fingerprints for the tests, the figures and the live pages. Pure Python (math, random): it also runs in
the browser.
"""
import math
import random


class Charger:
    def __init__(self, twin, seed=1):
        self.tw = twin
        d = twin["design"]
        self.ch, self.e, self.th, self.cb, self.site = d["charger"], d["efficiency"], d["stack_thermal"], d["cable"], d["site"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.meter_drift_pct = 0.0
        self.last_e = 48.6                       # kWh of the last completed session (charger's own measurement)

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    def available(self):
        return self.ch["stacks"] - (1 if self.faults["power_stack_failure"] > 0.5 else 0)

    # true state ---------------------------------------------------------------------------------------------------
    def true_state(self, i1=400.0, v1=760.0, i2=150.0, v2=420.0, amb=25.0):
        """One operating point: current and voltage asked by the car on each outlet, and the inlet air temperature."""
        f, e, cb = self.faults, self.e, self.cb
        if f["contactor_welded"] > 0.5:
            i2 = 0.0                                             # outlet 2 locked out
        avail = self.available()
        p = (v1 * i1 + v2 * i2) / 1000
        cap = avail * self.ch["stack_kw"]
        if p > cap:                                              # dynamic allocation: share what is left
            i1, i2 = i1 * cap / p, i2 * cap / p
            p = cap
        n = 0 if p <= 0 else min(avail, max(1, math.ceil(p / 95.0)))
        if n:
            loss = (n * e["loss_a_kw"] + e["loss_c_per_kw"] * p * p / n) * (1 + 0.6 * f["stack_cooling_ageing"])
            hs = amb + self.th["r_th_k_per_kw"] * loss / n * (1 + 0.8 * f["stack_cooling_ageing"])
        else:
            loss, hs = self.ch["standby_w"] / 1000, amb + 1.0
        heat = (i1 ** 2 + i2 ** 2) * cb["r_loop_ohm"]
        flow = cb["flow_nominal_lpm"] * (1 - 0.65 * f["coolant_flow_low"])
        sup = amb + self.site["coolant_supply_over_ambient_k"]
        ret = sup + heat / (2 * flow * cb["coolant_density_kg_per_l"] / 60 * cb["coolant_cp_j_per_kgk"])
        k = cb["contact_k_per_ka2"]
        return dict(i1=i1, v1=v1 if i1 > 0 else 0.0, i2=i2, v2=v2 if i2 > 0 else 0.0, p=p, n=n, avail=avail, ac=p + loss, hs=hs,
                    amb=amb, flow=flow, sup=sup, ret=ret,
                    t1=ret + k * (i1 / 1000) ** 2 * (1 + 2.5 * f["contact_wear"]), t2=ret + k * (i2 / 1000) ** 2,
                    ins=8000.0 * math.exp(-5.2 * f["insulation_degradation"]), weld=1 if f["contactor_welded"] > 0.5 else 0)

    # one published message ------------------------------------------------------------------------------------------
    def measure(self, s=None):
        s = s or self.true_state()
        f, n = self.faults, self.n
        att = round(72 + n(3))
        e_int = self.last_e
        return {
            "ac_input_kw": round(s["ac"] * (1 + n(0.0003)) + n(0.02), 3), "ac_voltage_v": round(self.site["ac_voltage_v"] + n(1.5), 1),
            "dc_voltage_c1_v": round(s["v1"] + (n(0.3) if s["i1"] > 0 else 0), 1), "dc_current_c1_a": round(s["i1"] * (1 + n(0.0003)) if s["i1"] > 0 else 0.0, 1),
            "contact_temp_c1_c": round(s["t1"] + n(0.2), 2), "status_c1": 1 if s["i1"] > 0 else 0,
            "dc_voltage_c2_v": round(s["v2"] + (n(0.3) if s["i2"] > 0 else 0), 1), "dc_current_c2_a": round(s["i2"] * (1 + n(0.0003)) if s["i2"] > 0 else 0.0, 1),
            "contact_temp_c2_c": round(s["t2"] + n(0.2), 2), "status_c2": 2 if s["weld"] else (1 if s["i2"] > 0 else 0),
            "stacks_available": s["avail"], "stacks_active": s["n"], "stack_temp_max_c": round(s["hs"] + n(0.3), 2),
            "coolant_supply_c": round(s["sup"] + n(0.1), 2), "coolant_return_c": round(s["ret"] + n(0.1), 2),
            "coolant_flow_lpm": round(s["flow"] * (1 + n(0.01)), 3), "ambient_c": round(s["amb"] + n(0.1), 2),
            "insulation_kohm": round(s["ins"] * (1 + n(0.03)), 1), "contactor_weld": s["weld"],
            "starts_attempted_24h": att,
            "starts_failed_comm_24h": round(1 + abs(n(0.35)) + 16 * f["vehicle_comm_failures"]),
            "starts_failed_auth_24h": round(1 + abs(n(0.35)) + 14 * f["payment_backend_fault"]),
            "starts_failed_safety_24h": round(22 * min(1.0, max(0.0, (f["insulation_degradation"] - 0.8) / 0.2))),
            "starts_failed_other_24h": round(abs(n(0.35))),
            "sessions_aborted_24h": round(1 + abs(n(0.3))),
            "outage_min_365d": round(2600 + abs(n(20)) + 16000 * f["contactor_welded"]), "outage_excluded_min_365d": 900,
            "payment_terminal_ok": 0 if f["payment_backend_fault"] > 0.5 else 1,
            "ocpp_heartbeat_age_s": round(30 + abs(n(8)) + 600 * f["payment_backend_fault"], 0),
            "last_session_meter_kwh": round(e_int * (1 + self.meter_drift_pct / 100 + n(0.0005)), 3),
            "last_session_internal_kwh": round(e_int, 3),
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


# Two typical cars: an 800 V class car on outlet 1 and a 400 V class car on outlet 2 (assumed charging curves, not a maker's)
CARS = [dict(v0=640.0, dv=200.0, imax=500.0, knee=0.55, iend=120.0, stop=0.85),
        dict(v0=340.0, dv=80.0, imax=400.0, knee=0.50, iend=80.0, stop=0.82)]


class Session:
    def __init__(self, car, cap_kwh, rnd, gap_s):
        self.car, self.cap, self.rnd = car, cap_kwh, rnd
        self.soc, self.e, self.gap = None, 0.0, gap_s

    def ask(self):
        """Current and voltage the car asks for now (0 when no car is plugged in)."""
        if self.soc is None:
            return 0.0, 0.0
        c = self.car
        i = c["imax"] if self.soc < c["knee"] else c["imax"] - (c["imax"] - c["iend"]) * (self.soc - c["knee"]) / (c["stop"] - c["knee"])
        return max(i, c["iend"]), c["v0"] + c["dv"] * self.soc

    def step(self, dt_plant, p_kw, blocked=False):
        """Advance by dt_plant seconds at p_kw delivered. Returns the session energy when a session ends, else None."""
        if self.soc is None:
            self.gap -= dt_plant
            if self.gap <= 0 and not blocked:
                self.soc, self.e = 0.10 + 0.1 * self.rnd.random(), 0.0
            return None
        de = p_kw * dt_plant / 3600
        self.e += de
        self.soc += de / self.cap
        if self.soc >= self.car["stop"]:
            done, self.soc, self.gap = self.e, None, 120 + 120 * self.rnd.random()
            return done
        return None


class Plant:
    """The live stand-in used by the twin pages (same interface as the other twins' Plant).

    Cars arrive at both outlets one after the other (a busy motorway hub, so the clock of the day is not used): each charges
    from 10-20 % to about 85 %, then the bay stays empty for 2 to 4 minutes of plant time. The plant clock runs
    `demo.time_scale` times faster than real time, so a session lasts about two minutes on the page.
    """

    def __init__(self, twin, seed=7001):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        caps = demo.get("battery_kwh", [77.0, 62.0])
        self.c = Charger(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.s = [Session(CARS[0], caps[0], self.c.rnd, 0.0), Session(CARS[1], caps[1], self.c.rnd, 150.0)]
        self.t = 0.0
        self.running, self.trip = True, 0
        self.last = None

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.running, self.trip = True, 0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.c.faults[k] = f.sev
        dtp = dt * self.scale
        self.t += dtp
        (i1, v1), (i2, v2) = self.s[0].ask(), self.s[1].ask()
        st = self.c.true_state(i1, v1, i2, v2, self.c.site["ambient_nominal_c"])
        if dtp > 0:
            for j, sess in enumerate(self.s):
                p = (st["v1"] * st["i1"] if j == 0 else st["v2"] * st["i2"]) / 1000
                done = sess.step(dtp, p, blocked=(j == 1 and st["weld"] == 1))
                if done is not None:
                    self.c.last_e = round(done, 3)
        self.last = st
        return st

    def measure(self, true):
        return self.c.measure(true)
