"""A stand-in for RF-6901: the compressor rack, its condenser and receiver, the store's refrigeration load and one cold room, with injectable faults.

The real rack controller, cold room controller and energy meter send the same points (see telemetry.points in the twin
file). Nothing here is used by Monitor: the expected values are computed in Monitor from the twin file only. This model
only produces believable readings and fault fingerprints for the tests, the figures and the live twin pages.

How the stand-in works: the store's cases and rooms ask for a refrigeration load that follows the time of day (store open
or night blinds down) and the ambient temperature. The rack controller holds the suction at its set point and runs as
much compressor capacity as the load needs (the maker's polynomial at the actual to and tc). The condenser rejects load +
power with an approach proportional to the heat; the head pressure floats down to a minimum condensing temperature.
The receiver holds what the rest of the circuit does not: a leak takes its liquid first. Pure Python + math/random only
(it also runs in the browser under Pyodide).
"""
import math
import random

import twin_calc as tc


class Rack:
    def __init__(self, twin, seed=1):
        self.tw = twin
        self.d = twin["design"]
        self.k = tc._k(twin)
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0                # plant time, s since midnight (local)

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state -------------------------------------------------------------------------------------------------------
    def true_state(self):
        k, f, d = self.k, self.faults, self.d
        h = (self.t / 3600.0) % 24
        amb = 20.0 + 7.0 * math.sin(2 * math.pi * (h - 9) / 24)
        ld = d["load"]
        open_ = 1.0 if ld["open_from_h"] <= h < ld["open_to_h"] else 0.0
        load = ld["base_kw"] + ld["open_kw"] * open_ + ld["per_k_amb_kw"] * (amb - 20) + 5.0 * f["door_left_open"]
        rk = d["rack"]
        to = rk["to_set_c"]
        tcd = max(k["tcmin"], amb + 6.0)
        for _ in range(4):                                     # condensing temperature and power settle together
            qc, pc = tc.poly(k["cq"], to, tcd), tc.poly(k["cp"], to, tcd)
            neq = load / (qc * (1 - 0.05 * f["compressor_valve_wear"]))   # one of four compressors loses 20 % of its gas
            power = neq * pc * (1 + 0.18 * f["compressor_mechanical"])
            app = k["ad"] * (load + power) / k["qrej"] * (1 + 1.4 * f["condenser_fouled"])
            tcd = max(k["tcmin"], amb + app)
        cap = min(1.0, neq / k["n"])
        sh = rk["sh_normal_k"] - 11.0 * f["superheat_drift"]
        tsuc = to + sh
        ps, pd = tc.p_sat(k["dew"], to), tc.p_sat(k["dew"], tcd)
        tdis = (tsuc + 273.15) * (pd / ps) ** k["m"] - 273.15 + 28.0 * f["compressor_valve_wear"]
        rc = d["receiver"]
        lost = 52.0 * f["refrigerant_leak"]
        tb = tc.t_sat(k["bub"], pd)
        tliq = tb - rk["sc_normal_k"]
        rho = tc.rho_liq(k, tliq)
        level = (k["l0"] + k["la"] * (amb - k["aref"]) + k["ll"] * (cap - k["cref"])) - lost / (k["vrec"] * rho) * 100
        if level < 12.0:                                     # liquid seal lost: vapour reaches the liquid line
            tliq = tb - 0.3
        cr = d["coldroom"]
        room = cr["air_set_c"] + 0.3 * math.sin(2 * math.pi * self.t / 1800) + 3.5 * f["evaporator_icing"] + 1.8 * f["door_left_open"]
        prod = cr["air_set_c"] + 0.8 + 1.2 * f["evaporator_icing"] + 3.2 * f["door_left_open"]
        door = 4.0 + 2.0 * open_ + 22.0 * f["door_left_open"]
        return dict(h=h, amb=amb, open=open_, load=load, to=to, tc=tcd, neq=neq, cap=cap, power=power, sh=sh, tsuc=tsuc,
                    ps=ps, pd=pd, tdis=tdis, tliq=tliq, level=level, room=room, prod=prod, door=door,
                    running=min(k["n"], max(1, math.ceil(neq - 0.05))), ice=f["evaporator_icing"], lost=lost)

    # one published message ----------------------------------------------------------------------------------------------
    def measure(self, s=None):
        s = s or self.true_state()
        pa = self.k["patm"]
        ice = s["ice"] > 0.5
        return {
            "suction_pressure_barg": round(s["ps"] - pa + self.n(0.01), 3),
            "suction_temp_c": round(s["tsuc"] + self.n(0.2), 2),
            "discharge_pressure_barg": round(s["pd"] - pa + self.n(0.03), 3),
            "discharge_temp_c": round(s["tdis"] + self.n(0.5), 2),
            "liquid_temp_c": round(s["tliq"] + self.n(0.1), 2),
            "receiver_level_pct": round(s["level"] + self.n(0.3), 2),
            "rack_power_kw": round(s["power"] * (1 + self.n(0.006)), 2),
            "capacity_pct": round(s["cap"] * 100 + self.n(0.3), 2),
            "compressors_running": s["running"],
            "ambient_temp_c": round(s["amb"] + self.n(0.1), 2),
            "room_air_c": round(s["room"] + self.n(0.1), 2),
            "product_temp_c": round(s["prod"] + self.n(0.08), 2),
            "door_open_min_h": round(max(0.0, s["door"] + self.n(0.3)), 1),
            "defrost_end_on_temp": 0 if ice else 1,
            "defrost_duration_min": round(18.0 + 22.0 * s["ice"] + self.n(0.5), 1),
            "days_since_topup": round(150.0 + self.t / 86400.0, 2),
            "days_since_leak_check": round(60.0 + self.t / 86400.0, 2),
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

    The plant clock is the time of day in seconds: the store opens at 07:00 and closes at 22:00, and the ambient peaks
    in the afternoon. The published values are window means from the controllers, so one reading is enough.
    """

    def __init__(self, twin, seed=6901):
        self.twin = twin
        self.scale = float(twin["design"].get("demo", {}).get("time_scale", 1))
        self.r = Rack(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        for k, f in self.faults.items():
            f.sev = f.target = 0.0
            self.r.faults[k] = 0.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.r.faults[k] = f.sev
        self.t += dt * self.scale
        self.r.t = self.t
        return self.r.true_state()

    def measure(self, true):
        return self.r.measure(true)
