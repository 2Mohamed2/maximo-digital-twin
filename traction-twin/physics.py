"""A stand-in for TM-5401: one traction motor of a Vectron AC locomotive with its inverter, blower, bearings and wheelset,
and injectable faults.

The real TCMS sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the expected
values are computed in Monitor from the twin file only. This model only produces believable readings and fault fingerprints
for the tests, the figures and the live pages.

How the stand-in works: the driver asks for a share of the available effort (the tractive effort curve); the wheel delivers
it unless adhesion caps it, in which case the slip control lets the wheel creep more. The inverter's torque estimate, the
current, the speeds and the temperatures follow from simple physics. Temperatures use the 30-minute (winding, bearings) and
5-minute (inverter) averages, the same averages the TCMS sends, so the stand-in and the twin agree when nothing is wrong.
Faults change the physics only. Regenerative braking is not modelled (the motor is idle while braking here).
Pure Python (math, random): it also runs in the browser under Pyodide.
"""
import math
import random

G = 9.81

# one run: (name, real seconds, demand %, target speed km/h, speed for the steady stand-in)
PHASES = [("standing", 10, 0.0, 0.0, 0.0), ("starting", 20, 100.0, 80.0, 40.0), ("climbing", 80, 100.0, 80.0, 80.0),
          ("cruising", 25, 45.0, 100.0, 100.0), ("coasting", 10, 0.0, 95.0, 95.0), ("braking", 15, 0.0, 0.0, 50.0)]


class Motor:
    D_TRUE = 1210.0                      # actual wheel diameter (mm), equal to the parameter when healthy

    def __init__(self, twin, seed=1):
        self.tw = twin
        d = twin["design"]
        self.lo, self.m, self.th, self.b = d["locomotive"], d["motor"], d["thermal"], d["bearings"]
        self.ins, self.ad, self.cv = d["insulation"], d["adhesion"], d["converter"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.air = self.th["air_nominal_c"]
        self.odo = 412650.0

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    def c(self, s, lim=3.0):
        """Gaussian noise clamped at lim standard deviations (keeps healthy readings inside the alarm bands)."""
        return max(-lim * s, min(lim * s, self.rnd.gauss(0, s)))

    # physics ----------------------------------------------------------------------------------------------------------
    def te_available(self, v):
        return min(self.m["start_te_kn"], self.m["power_kw"] * 3.6 / max(v, 1))

    def adhesion_cap(self):
        mu = self.ad["mu_dry"] - 0.18 * self.faults["low_adhesion"]
        return mu * self.lo["mass_t"] * G / self.lo["axles"]

    def i_expected(self, torque, rpm):
        m = self.m
        n = max(rpm, 1)
        return math.sqrt((m["magnetising_a"] * min(1, m["base_rpm"] / n)) ** 2 + (m["kt_a_per_knm"] * max(1, n / m["base_rpm"]) * abs(torque)) ** 2)

    def rpm_for(self, v, creep):
        return v * (1 + creep / 100) / 3.6 / (math.pi * self.D_TRUE / 1000) * 60 * self.m["gear_ratio"]

    def drive(self, v, demand):
        """Effort, torque, creep, rpm and current for a speed and a demand."""
        f, m = self.faults, self.m
        f_dem = demand / 100 * self.te_available(v)
        cap = self.adhesion_cap()
        if demand > 0 and f_dem > cap:
            f_wheel, creep = cap, 4.0 + 6.0 * f["low_adhesion"]
        else:
            f_wheel, creep = f_dem, self.ad["creep_normal_pct"] * demand / 100
        r_m = self.D_TRUE / 2000
        t_cmd = f_wheel * r_m / (m["gear_ratio"] * m["gear_eff"])
        t_true = t_cmd * (1 - 0.25 * f["rotor_cage_damage"])
        rpm = self.rpm_for(v, creep if v > 0.5 else 0.0)
        cur = self.i_expected(t_cmd, rpm) * (1 + 0.10 * f["rotor_cage_damage"]) if demand > 0 else 0.0
        return {"f": f_wheel, "torque": t_true if demand > 0 else 0.0, "creep": creep, "rpm": rpm, "current": cur}

    def steady(self, phase="climbing"):
        """True steady state for one phase of the run (the stand-in used by the tests): heavy freight duty averages."""
        name, _, demand, _, v = next(p for p in PHASES if p[0] == phase)
        ir = self.m["rated_current_a"]
        return {"phase": name, "speed": v, "demand": demand, "rms30": 0.85 * ir, "rms5": 0.85 * ir, "rpm_avg30": self.rpm_for(70.0, 0.0)}

    # one published message --------------------------------------------------------------------------------------------
    def reading(self, s):
        f, th, cv, ir = self.faults, self.th, self.cv, self.m["rated_current_a"]
        v, demand = s["speed"], s["demand"]
        dr = self.drive(v, demand)
        air = self.air + self.c(0.3)
        flow = th["flow_rated_pct"] * (1 - 0.65 * f["blower_degraded"]) * (1 + self.c(0.01))
        load2 = (s["rms30"] / ir) ** 2
        stator = (air + th["rise_rated_k"] * load2 * (th["flow_rated_pct"] / max(flow, 10)) ** th["flow_exponent"]
                  + 70.0 * f["cooling_ducts_blocked"] * load2 + self.c(1.0))
        brg = self.b["rise_at_max_k"] / self.m["max_rpm"] * s["rpm_avg30"]
        ir40 = self.ins["ir_new_40c_mohm"] * 0.02 ** f["insulation_moisture"] * (1 + self.c(0.03))
        ir_t = 35.0 + self.c(1.0)
        i5 = s["rms5"] / ir
        loss = cv["loss_rated_kw"] * (cv["loss_linear_share"] * i5 + (1 - cv["loss_linear_share"]) * i5 ** 2)
        cool = cv["coolant_nominal_c"] + self.c(0.3)
        speed_meas = max(0.0, v * (1 + self.c(0.002)))
        r = {
            "speed_kmh": round(speed_meas, 2), "demand_pct": round(demand, 1),
            "motor_rpm": round(dr["rpm"] * (1 + self.c(0.001)), 1), "motor_torque_knm": round(dr["torque"] * (1 + self.c(0.01)), 3),
            "motor_current_a": round(dr["current"] * (1 + self.c(0.01)), 1),
            "current_rms30_a": round(s["rms30"], 1), "current_rms5_a": round(s["rms5"], 1), "rpm_avg30": round(s["rpm_avg30"], 1),
            "stator_c": round(stator, 1), "air_in_c": round(air, 1), "blower_flow_pct": round(flow, 1),
            "bearing_de_c": round(air + brg + 35.0 * f["bearing_lubrication"] + self.c(1.0), 1),
            "bearing_nde_c": round(air + 0.8 * brg + self.c(1.0), 1),
            "env_bpfo_g": round(max(0.0, (0.35 + 3.2 * f["bearing_outer_race"]) * min(1.0, dr["rpm"] / 800) * (1 + self.c(0.08))), 3),
            "ir_mohm": round(ir40 / 2 ** ((ir_t - 40) / self.ins["ir_halving_k"]), 1), "ir_temp_c": round(ir_t, 1),
            "wheel_d_mm": self.D_TRUE, "creep_coast_pct": round(self.c(0.05), 3),
            "slip_events_100km": round(max(0.0, 0.5 + 14.0 * f["low_adhesion"] + self.c(0.4)), 1),
            "coolant_c": round(cool, 1),
            "igbt_baseplate_c": round(cool + cv["rth_k_per_kw"] * loss + 16.0 * f["inverter_cooling"] + self.c(0.8), 1),
            "igbt_tj_swing_k": round(40.0 + 18.0 * f["inverter_cooling"] + self.c(0.8), 1),
            "igbt_tj_mean_c": round(78.0 + 22.0 * f["inverter_cooling"] + self.c(0.8), 1),
            "igbt_cycles_day": round(cv["cycles_per_day"] + self.c(3.0)),
            "odometer_km": round(self.odo, 1),
        }
        return r

    def measure(self, phase="climbing"):
        return self.reading(self.steady(phase))


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

    A heavy freight train runs the same 40-minute section again and again: stand at a signal, start, climb a long gradient at
    full demand (power-limited at 80 km/h), cruise, coast, brake. One run takes `demo.cycle_s` real seconds. The 30-minute and
    5-minute averages the TCMS keeps are first-order filters on plant time.
    """

    def __init__(self, twin, seed=5401):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.cycle = float(demo.get("cycle_s", 160))
        self.mo = Motor(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 9 * 3600.0
        self.running, self.trip = True, 0
        self.pos = 0.0
        self.speed = 0.0
        ir = twin["design"]["motor"]["rated_current_a"]
        self.ms30, self.ms5 = (0.8 * ir) ** 2, (0.6 * ir) ** 2
        self.rpm30 = self.mo.rpm_for(60.0, 0.0)
        self.state = None

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.pos, self.speed = 0.0, 0.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def phase(self):
        total = sum(p[1] for p in PHASES)
        x, acc = self.pos / self.cycle * total, 0.0
        for p in PHASES:
            if x < acc + p[1]:
                return p, (x - acc) / p[1]
            acc += p[1]
        return PHASES[-1], 1.0

    def step(self, dt=1.0):
        mo = self.mo
        for k, f in self.faults.items():
            f.step(dt)
            mo.faults[k] = f.sev
        self.t += dt * self.scale
        hour = (self.t / 3600.0) % 24
        mo.air = 26 + 6 * math.sin(2 * math.pi * (hour - 9) / 24)
        self.pos = (self.pos + dt) % self.cycle
        (name, _, demand, target, _), frac = self.phase()
        if dt > 0:
            tau = 8.0 if target > self.speed else 5.0
            self.speed += (target - self.speed) * (1 - math.exp(-dt / tau))
            if target == 0 and self.speed < 0.5:
                self.speed = 0.0
        dr = mo.drive(self.speed, demand)
        if dt > 0:
            h = dt * self.scale
            self.ms30 += (dr["current"] ** 2 - self.ms30) * (1 - math.exp(-h / 1800))
            self.ms5 += (dr["current"] ** 2 - self.ms5) * (1 - math.exp(-h / 300))
            self.rpm30 += (dr["rpm"] - self.rpm30) * (1 - math.exp(-h / 1800))
            mo.odo += self.speed * h / 3600
        self.state = {"phase": name, "speed": self.speed, "demand": demand, "rms30": math.sqrt(self.ms30), "rms5": math.sqrt(self.ms5),
                      "rpm_avg30": self.rpm30, "te_kn": dr["f"], "creep": dr["creep"], "cycle_pos": self.pos / self.cycle}
        return dict(self.state)

    def measure(self, true):
        return self.mo.reading(true)
