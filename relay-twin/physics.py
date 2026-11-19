"""A stand-in for PR-7201: the REF615 relay, its feeder, its breaker, the station bus and the DC supply, with injectable faults.

The real relay sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings, fault
records and fault fingerprints for the tests and the figures.
"""
import math
import random

CRC_OTHER = 2862933555          # checksum of a setting file that is not the approved one


class Relay:
    def __init__(self, twin, seed=1):
        self.t = twin
        d = twin["design"]
        self.f, self.o, self.b, self.s, self.dc = d["feeder"], d["overcurrent"], d["breaker"], d["supervision"], d["dc"]
        self.is_a = self.o["start_value_in"] * self.f["ct_primary_a"]
        self.allow = self.b["isc_rated_ka"] ** 2 * self.b["arc_time_s"] * self.b["breaks_at_rated"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.count = 37

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true behaviour -------------------------------------------------------------------------------------------------
    def operate_ms(self, current_a):
        """Relay operate time for a fault current: the curve of the settings really active, plus the output contact."""
        tms = self.o["tms"] * (1 + 0.6 * self.faults["settings_change"])
        m = max(current_a / self.is_a, 1.05)
        return 1000 * tms * (self.o["k"] / (m ** self.o["alpha"] - 1) + self.o["c"]) * (1 + self.n(0.006)) + 6.0 + self.n(1.0)

    def open_ms(self):
        return self.b["open_baseline_ms"] * (1 + 1.6 * self.faults["breaker_slow"]) + self.n(1.2)

    def fault_record(self):
        i = self.rnd.uniform(1500.0, 4800.0)
        return {"fault_current_a": round(i, 1), "fault_operate_ms": round(self.operate_ms(i), 1), "cb_open_ms": round(self.open_ms(), 1)}

    # one published message --------------------------------------------------------------------------------------------
    def measure(self, record=None):
        f = self.faults
        rec = record or self.fault_record()
        load = self.f["load_nominal_a"] + self.n(4.0)
        io_meas = abs(2.0 + self.n(0.3))
        io_calc = abs(io_meas + self.n(0.6) + load * f["ct_circuit_fault"])
        sync_lost = f["time_sync_loss"] > 0.3
        return {
            "load_current_a": round(load, 1), "io_calc_a": round(io_calc, 2), "io_meas_a": round(io_meas, 2),
            "fault_current_a": rec["fault_current_a"], "fault_operate_ms": rec["fault_operate_ms"], "fault_count": self.count,
            "cb_open_ms": rec["cb_open_ms"],
            "cb_wear_ka2s": round(self.allow * (0.35 + 0.75 * f["contact_wear"]) + abs(self.n(1.0)), 2),
            "tcs_alarm": 1 if f["trip_circuit_open"] > 0.5 else 0,
            "settings_crc": self.s["settings_checksum_approved"] if f["settings_change"] < 0.05 else CRC_OTHER,
            "active_group": self.s["setting_group_approved"], "irf_alarm": 0,
            "sync_ok": 0 if sync_lost else 1, "sync_offset_us": round(self.n(0.25) + 4000 * f["time_sync_loss"], 2),
            "goose_missed": int(abs(self.n(0.8))) + int(300 * f["goose_degraded"]),
            "goose_max_latency_ms": round(1.8 + abs(self.n(0.3)) + 18 * f["goose_degraded"], 2),
            "aux_dc_v": round(self.dc["float_v"] - 52 * f["dc_supply_low"] + self.n(0.3), 2),
            "trip_verified_days": round(120 + abs(self.n(30)), 1),
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

    The feeder carries its load. Every `demo.fault_every_s` real seconds a short circuit occurs on the feeder: the relay
    picks up, trips on its curve, the breaker opens and recloses 3 s later. The relay stores the fault record (current,
    operate time, breaker opening time) and that record is what the twin checks until the next fault. With the trip
    circuit open the relay cannot trip the breaker, so no new record is made (in a real substation the upstream
    protection or the breaker failure scheme would clear the fault).
    """
    OPEN_S = 3.0

    def __init__(self, twin, seed=7201):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.every = float(demo.get("fault_every_s", 45))
        self.r = Relay(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.timer, self.open_left = 0.0, 0.0
        self.last = self.r.fault_record()
        self.last_proof_t = self.t - 120 * 86400

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.timer, self.open_left, self.running, self.trip = 0.0, 0.0, True, 0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.r.faults[k] = f.sev
        self.t += dt * self.scale
        fault_now = False
        if self.open_left > 0:
            self.open_left = max(0.0, self.open_left - dt)
            if self.open_left == 0:
                self.running, self.trip = True, 0
        self.timer += dt
        if self.timer >= self.every:
            self.timer = 0.0
            if self.r.faults["trip_circuit_open"] <= 0.5:
                fault_now = True
                self.last = self.r.fault_record()
                self.r.count += 1
                self.last_proof_t = self.t
                self.running, self.trip, self.open_left = False, 1, self.OPEN_S
        load = self.twin["design"]["feeder"]["load_nominal_a"] * (1 + 0.05 * math.sin(self.t / 900.0))
        return {"current_a": self.last["fault_current_a"] if fault_now else (0.0 if not self.running else load),
                "breaker_closed": self.running, "fault": fault_now}

    def measure(self, true):
        r = self.r.measure(self.last)
        r["trip_verified_days"] = round((self.t - self.last_proof_t) / 86400, 3)
        if not true["breaker_closed"]:
            r["load_current_a"] = round(abs(self.r.n(0.2)), 1)
            r["io_calc_a"] = round(abs(self.r.n(0.05)), 2)
            r["io_meas_a"] = round(abs(self.r.n(0.05)), 2)
        return r
