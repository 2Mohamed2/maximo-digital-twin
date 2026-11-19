"""A stand-in for AMI-7301: one LV feeder with 24 customers, its check meter, smart meters and data concentrator.

The real head-end sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model solves the feeder with complex phasors (phase
and neutral conductors, the transformer impedance, constant-power loads), which is fuller than the twin's linear formulas,
so the twin's residuals show a realistic modelling error. Pure Python: math and random only.
"""
import cmath
import math
import random

A120 = cmath.exp(-2j * math.pi / 3)
PH = [1, A120, A120 * A120]                      # L1, L2, L3 unit phasors
HEAVY = [0, 1, 2, 0, 1, 2,  0, 1, 2, 0, 2, 1,  0, 0, 0, 0, 1, 2,  0, 0, 1, 0, 2, 0]   # heavy terminal of each customer
THIEF, VACANT, EOL = 21, 9, 23                  # customer indices: bypass at cabinet D, an empty house at B, end-of-feeder meter
LOST = [6, 7, 8, 10, 11, 12, 13, 14, 15, 16]    # meters behind the noisy PLC segment (cabinets B and C)


def profile(h):
    """Diversified residential load per customer as a share of its evening peak (assumption, used by the stand-in only)."""
    pts = [(0, .16), (5, .13), (7, .38), (8.5, .45), (12, .32), (16, .38), (18, .80), (19.5, 1.0), (21, .85), (23, .32), (24, .16)]
    h %= 24
    for (h0, v0), (h1, v1) in zip(pts, pts[1:]):
        if h0 <= h <= h1:
            return v0 + (v1 - v0) * (h - h0) / (h1 - h0)
    return pts[0][1]


class Feeder:
    def __init__(self, twin, seed=1):
        self.tw = twin
        d = twin["design"]
        self.net, self.tr, self.me, self.ld = d["network"], d["transformer"], d["meters"], d["load"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        kt = self.net["derived"]["temp_factor"]
        self.z = [complex(s["r20_ohm_km"] * kt * s["length_m"] / 1000, s["x_ohm_km"] * s["length_m"] / 1000) for s in self.net["sections"]]
        sv = self.net["service"]
        self.zs = complex(sv["r20_ohm_km"] * kt * sv["length_m"] / 1000, sv["x_ohm_km"] * sv["length_m"] / 1000)
        vb = 400.0
        zb = vb * vb / (self.tr["rating_kva"] * 1000)
        ur = self.tr["pk_w"] / (self.tr["rating_kva"] * 1000)
        uk = self.tr["uk_pct"] / 100
        self.zt = complex(ur * zb, math.sqrt(uk * uk - ur * ur) * zb)
        self.node = [i // 6 for i in range(24)]
        r = random.Random(73)
        self.scale = [r.uniform(0.6, 1.45) for _ in range(24)]
        self.err = [r.uniform(-0.004, 0.004) for _ in range(24)]       # in-service error of each customer meter (class B: MPE 1 %)
        self.cerr = [r.uniform(-0.002, 0.002) for _ in range(3)]       # check meter + CT error per phase (class 0.5S)
        self.tanphi = math.tan(math.acos(self.net["pf"]))

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state ------------------------------------------------------------------------------------------------------
    def loads(self, hour):
        """Per customer, per meter terminal: active power (W)."""
        f = self.faults
        pk, night = self.ld["kw_per_customer_peak"] * 1000, self.ld["kw_per_customer_night"] * 1000
        base = profile(hour)
        out = []
        for c in range(24):
            p = pk * base * self.scale[c] * max(0.3, 1 + self.n(0.12))
            p = max(p, night * 0.5 * self.scale[c])
            if c == VACANT:
                p = 800.0 * max(0.3, 1 + self.n(0.1)) if f["relay_stuck"] >= 0.3 else 0.0
            w = [0.2, 0.2, 0.2]
            w[HEAVY[c]] = 0.6
            out.append([p * x for x in w])
        return out

    def state(self, hour):
        f = self.faults
        P = self.loads(hour)
        rot = [1 if (f["phase_mismapping"] > 0 and self.node[c] == 2 and c - 12 < round(6 * f["phase_mismapping"])) else 0 for c in range(24)]
        theft = 2500.0 * f["bypass_theft"]
        zn_extra = 2.0 * f["loose_neutral"]
        e0 = self.net["no_load_v"] * (1 + 0.05 * f["tap_setting"])
        U = [[e0 * PH[p] for p in range(3)] for _ in range(5)]           # node 0 = busbar, 1..4 = cabinets A..D
        for _ in range(6):
            Ic = []                                                     # per customer, per network phase (complex A)
            for c in range(24):
                k = self.node[c] + 1
                ic = [0j, 0j, 0j]
                for t in range(3):
                    p = (t + rot[c]) % 3
                    s = complex(P[c][t], P[c][t] * self.tanphi)
                    ic[p] += (s / U[k][p]).conjugate()
                if c == THIEF and theft > 0:
                    ic[0] += (complex(theft, 0) / U[k][0]).conjugate()
                Ic.append(ic)
            Isec = []
            for s in range(4):
                Isec.append([sum(Ic[c][p] for c in range(24) if self.node[c] >= s) for p in range(3)])
            U0 = [e0 * PH[p] - self.zt * Isec[0][p] for p in range(3)]
            E, VN = list(U0), 0j
            newU = [U0]
            for s in range(4):
                zn = self.z[s] + (zn_extra if s == 3 else 0)
                E = [E[p] - self.z[s] * Isec[s][p] for p in range(3)]
                VN = VN + zn * sum(Isec[s])
                newU.append([E[p] - VN for p in range(3)])
            U = newU
        # meters: voltage at the meter terminals (after the service cable) and metered power
        meters = []
        for c in range(24):
            k = self.node[c] + 1
            ret = sum(Ic[c])
            um = [U[k][p] - self.zs * Ic[c][p] - self.zs * ret for p in range(3)]
            pt = []
            for t in range(3):
                p = (t + rot[c]) % 3
                i_t = (complex(P[c][t], P[c][t] * self.tanphi) / U[k][p]).conjugate()
                pt.append((um[p] * i_t.conjugate()).real * (1 + self.err[c]))
            meters.append({"node": "ABCD"[self.node[c]], "v": [abs(x) for x in um], "p_terminal": pt,
                           "i_service": [abs(x) for x in Ic[c]], "p_metered": sum(pt)})
        loss = sum(abs(Isec[s][p]) ** 2 * self.z[s].real for s in range(4) for p in range(3))
        loss += sum(abs(sum(Isec[s])) ** 2 * (self.z[s].real + (zn_extra if s == 3 else 0)) for s in range(4))
        loss += sum((sum(abs(x) ** 2 for x in Ic[c]) + abs(sum(Ic[c])) ** 2) * self.zs.real for c in range(24))
        pin = [(U0[p] * Isec[0][p].conjugate()).real for p in range(3)]
        return {"U": U, "Ihead": Isec[0], "pin": pin, "meters": meters, "rot": rot, "loss_w": loss, "theft_w": theft,
                "load_w": sum(sum(x) for x in P), "hour": hour % 24}

    # one published message (one 15-minute interval) ------------------------------------------------------------------
    def measure(self, hour, st=None):
        f = self.faults
        st = st or self.state(hour)
        dt = self.me["interval_min"] / 60.0
        pin = [st["pin"][p] * (1 + self.cerr[p]) for p in range(3)]
        pin = [x + self.me["meter_w_per_phase"] * 24 + self.me["concentrator_w"] / 3 for x in pin]
        if f["ct_polarity"] >= 0.5:
            pin[1] = -pin[1]
        imp = [round(max(x, 0) * dt / 1000 + abs(self.n(0.0004)), 4) for x in pin]
        exp_ = round(sum(max(-x, 0) for x in pin) * dt / 1000, 4)
        lost = set(LOST[:round(len(LOST) * f["concentrator_comms"])])
        cust = [0.0, 0.0, 0.0]
        vs = []
        for c, m in enumerate(st["meters"]):
            if c in lost:
                continue
            for t in range(3):
                cust[t] += m["p_terminal"][t] * dt / 1000                # the head-end maps terminal t to network phase t
            vs += m["v"]
        ih = [abs(x) for x in st["Ihead"]]
        i_n = abs(sum(st["Ihead"]))
        ub = [abs(x) for x in st["U"][0]]
        eol = st["meters"][EOL]["v"]
        return {
            "feeder_kwh_l1": imp[0], "feeder_kwh_l2": imp[1], "feeder_kwh_l3": imp[2], "feeder_kwh_export": exp_,
            "feeder_i_l1": round(ih[0] * (1 + self.n(0.002)), 2), "feeder_i_l2": round(ih[1] * (1 + self.n(0.002)), 2),
            "feeder_i_l3": round(ih[2] * (1 + self.n(0.002)), 2), "feeder_i_n": round(i_n * (1 + self.n(0.003)), 2),
            "v_bus_l1": round(ub[0] + self.n(0.08), 2), "v_bus_l2": round(ub[1] + self.n(0.08), 2), "v_bus_l3": round(ub[2] + self.n(0.08), 2),
            "cust_kwh_l1": round(cust[0], 4), "cust_kwh_l2": round(cust[1], 4), "cust_kwh_l3": round(cust[2], 4),
            "reads_ok": 24 - len(lost), "reads_24h_pct": round(min(100.0, 99.7 + self.n(0.1)) - 40 * f["concentrator_comms"], 2),
            "v_min_cust": round(min(vs) + self.n(0.08), 2), "v_max_cust": round(max(vs) + self.n(0.08), 2),
            "v_end_l1": round(eol[0] + self.n(0.08), 2), "v_end_l2": round(eol[1] + self.n(0.08), 2), "v_end_l3": round(eol[2] + self.n(0.08), 2),
            "tamper_events_24h": 1 if f["bypass_theft"] > 0.2 else 0,
            "clock_offset_max_s": round(1.2 + abs(self.n(0.6)) + 110 * f["clock_drift"], 1),
            "relays_cmd_open": 1, "relays_open": 0 if f["relay_stuck"] >= 0.3 else 1,
            "kwh_on_open_relays": round(st["meters"][VACANT]["p_metered"] * dt / 1000, 4),
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

    t is the plant clock in seconds of the day. step(dt) advances it by dt x time_scale, so with a 10 s publish period each
    reading is one 15-minute interval. Warm-up steps of 2 s or more (the in-browser shim) do not move the clock, so the page
    opens at the visitor's local time.
    """
    def __init__(self, twin, seed=7301):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.start = float(demo.get("start_hour", 19.0)) * 3600
        self.f = Feeder(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = self.start
        self.running, self.trip = True, 0
        self.last = None

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.t = self.start

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def hour(self):
        return (self.t / 3600.0) % 24

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.f.faults[k] = f.sev
        if dt >= 2.0:          # in-browser warm-up: the clock stays on the visitor's time and nothing needs solving
            return {"hour": self.hour(), "state": None}
        self.t += dt * self.scale
        st = self.f.state(self.hour())
        self.last = st
        return {"hour": st["hour"], "load_kw": st["load_w"] / 1000, "loss_kw": st["loss_w"] / 1000, "theft_kw": st["theft_w"] / 1000,
                "v_end": [abs(x) for x in st["U"][4]], "state": st}

    def measure(self, true):
        return self.f.measure(true["hour"], true.get("state"))
