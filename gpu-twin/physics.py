"""A stand-in for GPU-5901: the 400 Hz converter, its output contactor, the 28 m aircraft cable and connector, the cooling
and the parked aircraft (load and APU), with injectable faults.

The real device sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests, the figures and the live pages. Pure Python (math, random), so it also runs in Pyodide.
"""
import math
import random


class GPU:
    """One steady reading at a given aircraft load. Faults are severities 0..1."""

    def __init__(self, twin, seed=1):
        self.tw = twin
        d = twin["design"]
        self.ra, self.ef, self.cb, self.th, self.ap = d["rating"], d["efficiency"], d["cable"], d["thermal"], d["apu"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        pf = self.ef["eff_full_kva"] * self.ef["pf"]
        self.kq = (pf / self.ef["eff_full"] - pf - self.ef["no_load_loss_kw"]) / self.ef["eff_full_kva"] ** 2
        self.r = self.cb["r_mohm_per_m"] * self.cb["length_m"] / 1000
        self.x = self.cb["x_mohm_per_m_400hz"] * self.cb["length_m"] / 1000

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    def loss(self, kva):
        """True converter loss (kW): the data-sheet model plus the 'power_stage_losses' fault (constant extra loss)."""
        return self.ef["no_load_loss_kw"] + self.kq * kva ** 2 + 2.5 * self.faults["power_stage_losses"]

    def state(self, kva=None, pf=None, connected=True, ambient=30.0):
        kva = self.ap["aircraft_load_kva"] if kva is None else kva
        pf = self.ap["aircraft_pf"] if pf is None else pf
        if not connected:
            kva = 0.0
        loss = self.loss(kva)
        return {"connected": connected, "kva": kva, "pf": pf, "ambient": ambient, "loss": loss,
                "heatsink": ambient + self.th["rth_k_per_kw"] * loss + 40.0 * self.faults["cooling_degraded"]}

    def measure(self, s=None, counters=None):
        """One published message for the true state s (default: aircraft on the GPU at its nominal load)."""
        s = s or self.state()
        f = self.faults
        vn = self.ra["v_ln_nom"]
        on = s["connected"]
        pf = s["pf"]
        sin = math.sqrt(1 - pf * pf)
        u_out, i_ph, conn = [], [], []
        for ph, imb in enumerate((1.0, 1.01, 0.99)):
            i = s["kva"] * 1000 / (3 * vn) * imb if on else 0.0
            de = i * (self.r * pf + self.x * sin)                             # the GPU's own cable model (= the twin's)
            u = vn + de - 3.5 * f["voltage_regulation_fault"] + self.n(0.12)
            act = de * (1 + 1.2 * f["cable_compensation_mismatch"])           # a longer / other cable than the model
            if ph == 0:
                act += i * 0.025 * f["connector_pin_wear"] * pf               # worn pin on phase A: extra contact resistance
            c = u - act + self.n(0.08) if on else u + self.n(0.08)
            u_out.append(u), i_ph.append(max(0.0, i + (self.n(0.3) if on else 0.0))), conn.append(c)
        s_kva = sum(a * b for a, b in zip(u_out, i_ph)) / 1000
        p_out = s_kva * pf
        loss = s["loss"] + self.n(0.04)
        c = counters or {}
        return {
            "u_out_a": round(u_out[0], 3), "u_out_b": round(u_out[1], 3), "u_out_c": round(u_out[2], 3),
            "i_a": round(i_ph[0], 2), "i_b": round(i_ph[1], 2), "i_c": round(i_ph[2], 2),
            "freq_hz": round(self.ra["f_nom_hz"] + self.n(0.02), 3), "p_out_kw": round(p_out, 3),
            "thd_v_pct": round(max(0.3, self.ra["thd_typ_pct"] + 5.0 * f["output_filter_aging"] + self.n(0.08)), 3),
            "conn_v_a": round(conn[0], 3), "conn_v_b": round(conn[1], 3), "conn_v_c": round(conn[2], 3),
            "p_in_kw": round(p_out + loss, 3), "heatsink_c": round(s["heatsink"] + self.n(0.4), 2), "ambient_c": round(s["ambient"] + self.n(0.2), 2),
            "contactor": 1 if on else 0, "apu_running": 1 if (on and f["apu_left_running"] > 0.5) else 0,
            "contactor_ops": int(c.get("contactor_ops", 61840) + 50000 * f["contactor_wear"]),
            "plug_cycles": int(c.get("plug_cycles", 2460) + 4000 * f["connector_pin_wear"]),
            "supply_hours_ytd": round(c.get("supply_hours_ytd", 3120.0), 1),
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

    Turnarounds repeat: the aircraft is on the GPU for `demo.turn_connected_min` plant minutes (load wandering around the
    nominal aircraft load), then the stand is empty for `demo.turn_gap_min`. The plant clock runs `demo.time_scale` times
    faster than real time. The cycle does not depend on the time of day, so the page opens in a sensible state at any hour.
    The heat sink follows its losses with a first-order lag.
    """
    TAU_S = 600.0     # heat-sink thermal time constant, plant seconds (assumption)

    def __init__(self, twin, seed=5901):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.on_s = 60.0 * float(demo.get("turn_connected_min", 40))
        self.cycle_s = self.on_s + 60.0 * float(demo.get("turn_gap_min", 10))
        self.g = GPU(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.reset()

    def reset(self):
        self.phase = 120.0
        self.hs = None
        self.counters = {"contactor_ops": 61840, "plug_cycles": 2460, "supply_hours_ytd": 3120.0}
        self.turn = 0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.g.faults[k] = f.sev
        pdt = dt * self.scale
        self.t += pdt
        was_on = self.phase < self.on_s
        self.phase = (self.phase + pdt) % self.cycle_s
        on = self.phase < self.on_s
        if on and not was_on:
            self.turn += 1
            self.counters["contactor_ops"] += 1
            self.counters["plug_cycles"] += 1
        if on:
            self.counters["supply_hours_ytd"] += pdt / 3600
        x = self.phase / self.on_s
        nom = self.g.ap["aircraft_load_kva"]
        kva = nom * (0.85 + 0.15 * math.sin(math.pi * x) + 0.05 * math.sin(7 * math.pi * x + self.turn))
        s = self.g.state(kva, self.g.ap["aircraft_pf"], on, 30.0 + 2.0 * math.sin(self.t / 7200))
        if self.hs is None or pdt <= 0:
            self.hs = s["heatsink"] if self.hs is None else self.hs
        else:
            a = 1 - math.exp(-pdt / self.TAU_S)
            self.hs += (s["heatsink"] - self.hs) * a
        s["heatsink"] = self.hs
        return s

    def measure(self, true):
        return self.g.measure(true, self.counters)
