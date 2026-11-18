"""A stand-in for ST-6601: the chamber, jacket, door seals, vacuum pump, steam generator, two temperature sensors and the
daily / weekly test results of a STERIVAP HP 669-2 steam sterilizer, with injectable faults.

The real controller sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable cycle records, a
live pressure / temperature trace and fault fingerprints for the tests and the figures.

Steam physics used here: in the chamber, steam (partial pressure p_s) and air (fraction x) share the pressure P:
p_s = (1 - x) P, and the drain sits at Ts(p_s) plus any superheat. The controller regulates on the drain temperature, so
air shows as a higher pressure for the same temperature, not as a colder recorder chart.
"""
import math
import random

_N = [0.0, 0.11670521452767e4, -0.72421316703206e6, -0.17073846940092e2, 0.12020824702470e5, -0.32325550322333e7,
      0.14915108613530e2, -0.48232657361591e4, 0.40511340542057e6, -0.23855557567849, 0.65017534844798e3]


def tsat_c(p_bar_a):
    b = (p_bar_a / 10) ** 0.25
    e = b * b + _N[3] * b + _N[6]
    f = _N[1] * b * b + _N[4] * b + _N[7]
    g = _N[2] * b * b + _N[5] * b + _N[8]
    d = 2 * g / (-f - math.sqrt(f * f - 4 * e * g))
    return (_N[10] + d - math.sqrt((_N[10] + d) ** 2 - 4 * (_N[9] + _N[10] * d))) / 2 - 273.15


def psat_bar(t_c):
    t = t_c + 273.15
    th = t + _N[9] / (t - _N[10])
    a = th * th + _N[1] * th + _N[2]
    b = _N[3] * th * th + _N[4] * th + _N[5]
    c = _N[6] * th * th + _N[7] * th + _N[8]
    return (2 * c / (-b + math.sqrt(b * b - 4 * a * c))) ** 4 * 10


class Sterilizer:
    def __init__(self, twin, seed=1):
        self.t = twin
        d = twin["design"]
        self.pr, self.ut, self.sq, self.va = d["programme"], d["utilities"], d["steam_quality"], d["vacuum"]
        self.ja = d["jacket"]
        self.kwh_kg = (self.ut["hg_kj_kg"] - self.ut["hf_feed_kj_kg"]) / 3600 / self.ut["generator_eff"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.cycles_total, self.cycles_seal = 18240, 1800

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state ---------------------------------------------------------------------------------------------------
    def supply_barg(self):
        return self.sq["supply_nominal_barg"] - 2.3 * self.faults["steam_supply_low"]

    def air_fraction(self):
        f = self.faults
        return 0.002 + abs(self.n(0.0008)) + 0.093 * f["door_seal_wear"] + 0.088 * f["ncg_in_steam"]

    def superheat(self):
        return 0.2 + self.n(0.04) + 3.6 * self.faults["jacket_overheat"]

    def achievable_c(self, supply_barg):
        """Highest drain temperature the supply can give: saturation at supply minus a 0.5 bar drop to the chamber."""
        return tsat_c(supply_barg + 1.01325 - 0.5)

    # one published cycle record + test results ------------------------------------------------------------------
    def measure(self):
        f = self.faults
        sp = self.pr["setpoint_c"]
        supply = self.supply_barg() + self.n(0.03)
        x, sh = self.air_fraction(), self.superheat()
        drift = 1.6 * f["sensor_drift"]
        t1 = min(sp, self.achievable_c(supply)) + self.n(0.05)       # control sensor (regulated)
        t_true = t1 + drift                                          # the sensor reads low by `drift`
        p = psat_bar(t_true - sh) / (1 - x)
        t2 = t_true + self.n(0.05)
        tmin, tmax = t1 - 0.35 - abs(self.n(0.08)), t1 + 0.45 + abs(self.n(0.08))
        held = tmin >= self.pr["band_low_c"]
        hold = self.pr["hold_s"] + 2 + abs(self.n(1.5)) if held else 0.0
        steam = 7.8 + self.n(0.15) + 4.0 * f["drain_trap_passing"]
        energy = (self.ut["energy_base_kwh"] + steam * self.kwh_kg) * (1 + self.n(0.012)) * (1 + 0.35 * f["generator_scaling"])
        jacket_p = psat_bar(t_true + self.ja["above_chamber_nominal_k"] + self.n(0.1) + 6.0 * f["jacket_overheat"])
        vac = self.va["pulse_min_mbar"] + self.n(2.5) + 150 * f["vacuum_pump_wear"]
        bd_dt = 0.3 + 35 * x + abs(self.n(0.08))
        return {
            "chamber_pressure_bar_a": 1.013, "chamber_temp_c": 104.0, "cycle_phase": 0,
            "jacket_pressure_bar_a": round(jacket_p, 4), "steam_supply_bar_g": round(supply, 3), "door_closed": 0,
            "cyc_hold_pressure_bar_a": round(p, 4), "cyc_hold_temp_mean_c": round(t1, 3), "cyc_hold_temp_min_c": round(tmin, 3),
            "cyc_hold_temp_max_c": round(tmax, 3), "cyc_hold_temp2_mean_c": round(t2, 3), "cyc_hold_time_s": round(hold, 1),
            "cyc_jacket_pressure_bar_a": round(jacket_p, 4), "cyc_vac_min_mbar": round(vac, 1), "cyc_result": 1 if held else 0,
            "cyc_steam_kg": round(steam, 2), "cyc_water_l": round(64 + self.n(2) + 10 * f["drain_trap_passing"], 1),
            "cyc_energy_kwh": round(energy, 3), "cycles_total": self.cycles_total, "cycles_since_seal": self.cycles_seal + int(5200 * f["door_seal_wear"]),
            "bd_result": 1 if bd_dt < 2.0 else 0, "bd_delta_t_c": round(bd_dt, 2),
            "bd_equil_time_s": round(8 + abs(self.n(1.0)) + 200 * (x - 0.002), 1),
            "bd_hours_since": round(min(20.0, 3 + abs(self.n(4))), 1),
            "lt_rise_mbar": round(3.5 + abs(self.n(0.8)) + 22 * f["door_seal_wear"], 2),
            "lt_start_mbar": round(vac - 8 + abs(self.n(1)), 1),
            "lt_hours_since": round(min(160.0, 30 + abs(self.n(30))), 1),
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


# phase timeline of one demo cycle (s): (end, phase code)
PHASES = [(24, 1), (32, 2), (52, 3), (58, 4), (76, 5), (82, 6), (90, 0)]


class Plant:
    """The live stand-in used by the twin pages (same interface as the other twins' Plant).

    The sterilizer runs 134 C porous-load cycles back to back, each compressed to `demo.cycle_s` real seconds: three
    vacuum / steam pulses, heat-up, holding, exhaust, drying under vacuum, air admission, then the doors open for unloading.
    At the end of every cycle the cycle record (holding pressure and temperatures, utilities, test results) is refreshed.
    The clock of the day is not used, so the warm-up of the in-browser shim does not matter.
    """

    def __init__(self, twin, seed=6601):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.cycle_s = float(demo.get("cycle_s", 90))
        self.v = Sterilizer(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.tc = 0.0
        self.temp = 105.0
        self.last = self.v.measure()

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.tc = 0.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def _trace(self, tc):
        """Chamber pressure (bar abs) and phase at time tc (s) into the demo cycle."""
        L = self.last
        ph_hold = L["cyc_hold_pressure_bar_a"]
        vac = L["cyc_vac_min_mbar"] / 1000
        phase = next(p for end, p in PHASES if tc < end) if tc < PHASES[-1][0] else 0
        if tc < 24:                                  # three pulses: 4 s down to vacuum, 4 s steam up to 1.5 bar
            k, u = divmod(tc, 8)
            start = 1.013 if k == 0 else 1.5
            p = start + (vac - start) * u / 4 if u < 4 else vac + (1.5 - vac) * (u - 4) / 4
        elif tc < 32:
            p = 1.5 + (ph_hold - 1.5) * (tc - 24) / 8
        elif tc < 52:
            p = ph_hold + 0.01 * math.sin(tc)
        elif tc < 58:
            p = ph_hold + (0.1 - ph_hold) * (tc - 52) / 6
        elif tc < 76:
            p = 0.08
        elif tc < 82:
            p = 0.08 + (1.013 - 0.08) * (tc - 76) / 6
        else:
            p = 1.013
        return p, phase

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.v.faults[k] = f.sev
        self.t += dt * self.scale
        before = self.tc
        self.tc = (self.tc + dt) % self.cycle_s
        if dt > 0 and (before < 82 <= self.tc or (self.tc < before and before < 82)):   # air admission done: cycle complete
            self.v.cycles_total += 1
            self.v.cycles_seal += 1
            self.last = self.v.measure()
        p, phase = self._trace(self.tc)
        x = self.v.air_fraction()
        target = tsat_c(max(p * (1 - x), 0.5)) if phase in (1, 2, 3) and p > 1.0 else 104.0
        if phase == 3:
            target = self.last["cyc_hold_temp_mean_c"]
        self.temp += (target - self.temp) * min(1.0, dt / 3.0) if dt > 0 else 0.0
        return {"pressure": p, "temp": self.temp, "phase": phase, "door_closed": 1 if self.tc < 82 else 0, "tc": self.tc}

    def measure(self, true):
        r = dict(self.last)
        live = self.v.measure()
        r["chamber_pressure_bar_a"] = round(true["pressure"] + self.v.n(0.003), 4)
        r["chamber_temp_c"] = round(true["temp"] + self.v.n(0.05), 2)
        r["cycle_phase"] = true["phase"]
        r["door_closed"] = true["door_closed"]
        r["steam_supply_bar_g"] = live["steam_supply_bar_g"]
        r["jacket_pressure_bar_a"] = live["jacket_pressure_bar_a"]
        r["cycles_total"] = self.v.cycles_total
        r["cycles_since_seal"] = self.last["cycles_since_seal"]
        return r
