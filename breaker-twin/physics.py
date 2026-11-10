"""Physics model of CB-701 (Siemens Energy 3AP1 FG 145 kV, SF6, spring mechanism) on a 132 kV line bay: the stand-in for the
real breaker.

Per step (dt real seconds; the plant clock runs `time_scale` times faster for the load day and temperatures):
  load      line current day profile (night ~550 A, evening peak ~1100 A), slight phase imbalance
  ambient   day/night swing, hot afternoons
  SF6       a fixed gas mass (density) in a fixed volume: the absolute pressure follows the gas temperature along the
            isochore; a leak lowers the density, the density monitor (with its own compensation) reports p20 and switches
            its alarm / lockout contacts; at lockout the breaker is blocked
  poles     terminal temperature rise ~ (I/Ir)^2 through a first-order lag; worn contacts add resistance on pole L2
  switching the breaker opens and recloses every `op_every_s` real seconds (demo cadence). Each opening records the
            opening time, the trip coil peak current and the interrupted current per pole (sum of I^1.8 accumulates);
            each closing records the closing time, the close coil current, then the charging motor recharges the
            closing spring (charging time and motor current)
  faults    sf6_leak lowers the density; contact_wear makes a fault-prone line trip the breaker on short-circuit current
            every 15 s and heats pole L2; mechanism_lubrication slows both operations; trip_coil lowers the coil
            current and delays the latch; spring_motor slows the charging; heater_fault stops the cabinet heater;
            density_monitor_drift offsets the monitor's own output. Clear all is a demo reset (wear counters back to
            their starting values); the operation counter rolls back before the 3000-cycle inspection
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


WEAR0 = {1: 0.58, 2: 0.63, 3: 0.55}          # fraction of the allowance already used (a breaker some years in service)


class Plant:
    def __init__(self, twin, seed=701):
        self.twin, self.rng = twin, random.Random(seed)
        self.d = twin["design"]
        self.k = tc._k(twin)
        self.scale = float(self.d["demo"]["time_scale"])
        self.op_every = float(self.d["demo"]["op_every_s"])
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0                     # plant clock, seconds of day
        self.real = 0.0                  # real seconds since start (switching cadence)
        self.running, self.trip = True, 0
        self.closed = 1
        self.next_op = 40.0
        self.p20_true = 0.697
        self.t_gas = 25.0
        self.amb = 25.0
        self.load_bias = 0.0
        self.poles = {i: 30.0 for i in (1, 2, 3)}
        self.wear = {i: WEAR0[i] * self.k["allow"] for i in (1, 2, 3)}
        self.ops = 2140
        self.last = {"open_ms": 23.4, "close_ms": 54.6, "trip_a": 2.24, "close_a": 2.24, "charge_s": 12.1, "motor_a": 3.0,
                     "i_ka": 0.8, "charged": 1}
        self.charge_left = 0.0
        self.uc = 112.0
        self.cab_t, self.cab_h = 31.0, 45.0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        """Clear all = demo reset: faults ramp back, and the wear counters and the density return to their pre-demo
        state (in a real breaker wear only resets after an interrupter overhaul)."""
        for f in self.faults.values():
            f.set(0.0, ramp_s)
        self.wear = {i: WEAR0[i] * self.k["allow"] for i in (1, 2, 3)}

    def reset(self):
        self.trip, self.running = 0, True

    def fault_state(self):
        return {k: round(v.sev, 3) for k, v in self.faults.items()}

    # ------------------------------------------------------------------ profiles
    def current(self):
        h = (self.t / 3600.0) % 24
        frac = 0.50 + 0.18 * math.exp(-((h - 9.0) / 2.5) ** 2) + 0.50 * math.exp(-((h - 18.5) / 3.2) ** 2)
        self.load_bias = 0.998 * self.load_bias + self.rng.gauss(0, 0.002)
        return max(150.0, 1100.0 * frac + 300 * self.load_bias)

    def ambient(self):
        h = (self.t / 3600.0) % 24
        return 25.0 + 8.0 * math.sin((h - 9.0) / 24 * 2 * math.pi)

    # ------------------------------------------------------------------ switching
    def _open(self, i_line, fault_trip):
        f, k = self.faults, self.k
        cw = f["contact_wear"].sev
        if fault_trip:                                   # single-phase-to-earth fault on L2, L1 sees part of it
            i_ka = {1: 0.45 * (14 + 22 * cw), 2: 14 + 22 * cw, 3: i_line / 1000}
        else:
            i_ka = {i: i_line / 1000 * (1 + 0.03 * (i - 2)) for i in (1, 2, 3)}
        for i in (1, 2, 3):
            self.wear[i] += i_ka[i] ** 1.8
        lub, coil = f["mechanism_lubrication"].sev, f["trip_coil"].sev
        self.last["open_ms"] = (k["to"] + k["so"] * (k["uc"] - self.uc) + 6.0 * lub + 2.2 * coil + self.rng.gauss(0, 0.3))
        self.last["trip_a"] = self.uc / (k["rtc"] * (1 + 0.55 * coil)) * (1 + self.rng.gauss(0, 0.01))
        self.last["i_ka"] = max(i_ka.values())
        self.closed = 0

    def _close(self):
        f, k = self.faults, self.k
        lub = f["mechanism_lubrication"].sev
        self.last["close_ms"] = k["tc"] + k["sc"] * (k["uc"] - self.uc) + 10.0 * lub + self.rng.gauss(0, 0.5)
        self.last["close_a"] = self.uc / 50.0 * (1 + self.rng.gauss(0, 0.01))
        m = f["spring_motor"].sev
        self.charge_left = k["tch"] * (1 + 1.2 * m) * (1 + self.rng.gauss(0, 0.02))
        self.last["charge_s"] = self.charge_left
        self.last["motor_a"] = 3.0 * (1 + 0.6 * m) * (1 + self.rng.gauss(0, 0.02))
        self.last["charged"] = 0
        self.closed = 1
        self.ops += 1
        if self.ops > 2950:              # demo counter: never drifts into the 3000-cycle inspection by itself
            self.ops = 2140

    # ------------------------------------------------------------------ step
    def step(self, dt=1.0):
        f, k = self.faults, self.k
        for x in f.values():
            x.step(dt)
        self.t = (self.t + dt * self.scale) % 86400
        self.real += dt
        pdt = dt * self.scale
        i_line = self.current()
        amb = self.ambient()
        self.amb += (amb - self.amb) * min(1.0, pdt / 600)
        self.uc += (112.0 + self.rng.gauss(0, 0.2) - self.uc) * 0.2
        # SF6: density falls with a leak (to 0.577 MPa at full severity); the gas follows the ambient plus sun
        self.p20_true = 0.697 - 0.12 * f["sf6_leak"].sev
        h = (self.t / 3600.0) % 24
        sun = 6.0 * max(0.0, math.sin((h - 6.0) / 12 * math.pi))
        self.t_gas += (self.amb + sun - self.t_gas) * min(1.0, pdt / 1800)
        p_abs = self.p20_true * (self.t_gas + 273.15) / 293.15
        p20_mon = self.p20_true + 0.035 * f["density_monitor_drift"].sev + 0.0004 * (self.t_gas - 20) / 20
        contact = 2 if p20_mon < k["lock"] else 1 if p20_mon < k["alarm"] else 0
        blocked = self.p20_true < k["lock"]
        # switching (demo cadence); a fault-prone line trips the breaker every 15 s when contact_wear is injected
        cw = f["contact_wear"].sev
        every = 15.0 if cw > 0.25 else self.op_every
        if self.charge_left > 0:
            self.charge_left -= dt
            if self.charge_left <= 0:
                self.last["charged"] = 1
        if not blocked and self.real >= self.next_op:
            if self.closed:
                self._open(i_line, cw > 0.25)
                self.next_op = self.real + (8.0 if cw > 0.25 else 30.0)
            elif self.last["charged"]:
                self._close()
                self.next_op = self.real + every
        # pole terminal temperatures
        cur = {i: (i_line * (1 + 0.03 * (i - 2)) if self.closed else 0.0) for i in (1, 2, 3)}
        for i in (1, 2, 3):
            extra = 14.0 * cw * (cur[i] / k["ir"]) ** 2 / (1000 / k["ir"]) ** 2 if i == 2 else 0.0
            target = self.amb + 1.2 + k["rise"] * (cur[i] / k["ir"]) ** 2 + extra
            self.poles[i] += (target - self.poles[i]) * min(1.0, pdt / (self.d["thermal"]["tau_min"] * 60))
        # mechanism cabinet: heater keeps it ~6 K above ambient and dry
        hf = f["heater_fault"].sev
        heater = 0.55 * (1 - hf)
        self.cab_t += (self.amb + 6.0 * (1 - hf) - self.cab_t) * min(1.0, pdt / 900)
        self.cab_h += (45.0 + 50.0 * hf - self.cab_h) * min(1.0, pdt / 600)
        return {"breaker_position": self.closed, "load_current_l1_a": cur[1], "load_current_l2_a": cur[2], "load_current_l3_a": cur[3],
                "ambient_temp_c": self.amb, "sf6_pressure_mpa": p_abs, "sf6_gas_temp_c": self.t_gas, "sf6_density_p20_mpa": p20_mon,
                "density_contact": contact, "pole_temp_l1_c": self.poles[1], "pole_temp_l2_c": self.poles[2], "pole_temp_l3_c": self.poles[3],
                "control_voltage_v": self.uc, "last_open_time_ms": self.last["open_ms"], "last_close_time_ms": self.last["close_ms"],
                "trip_coil_peak_a": self.last["trip_a"], "close_coil_peak_a": self.last["close_a"],
                "spring_charge_time_s": self.last["charge_s"], "spring_motor_current_a": self.last["motor_a"],
                "spring_charged": self.last["charged"], "last_interrupted_ka": self.last["i_ka"],
                "wear_sum_l1": self.wear[1], "wear_sum_l2": self.wear[2], "wear_sum_l3": self.wear[3], "operation_count": self.ops,
                "cabinet_temp_c": self.cab_t, "cabinet_humidity_pct": self.cab_h, "heater_current_a": heater}

    def measure(self, true):
        out = {}
        ints = ("breaker_position", "density_contact", "spring_charged", "operation_count")
        for p in self.twin["telemetry"]["points"]:
            k = p["metric"]
            v = true[k]
            if p["noise"]:
                v = v + self.rng.gauss(0, p["noise"])
            lo, hi = p["range"]
            v = max(lo, min(hi, v))
            out[k] = int(v) if k in ints else round(v, 5 if abs(v) < 2 else 3 if abs(v) < 100 else 2)
        return out
