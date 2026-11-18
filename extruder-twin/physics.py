"""A stand-in for EX-4401: the screw, barrel heating, feed bush, screen changer, pipe head and gearbox, with injectable faults.

The real extruder sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests and the figures. Pure Python (math, random), so it also runs in the browser (Pyodide).

The line's weight control holds the throughput at its set point by trimming the screw speed, so a screw that conveys less
per turn shows up as a higher screw speed at the same output.
"""
import math
import random

SQ3 = math.sqrt(3)


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


class Extruder:
    def __init__(self, twin, seed=1):
        self.t = twin
        d = twin["design"]
        self.d = d
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        h = d["heating"]
        self.ir = [kw * 1000.0 / (SQ3 * h["voltage_v"]) for kw in h["zone_kw"]]
        lo, hi = d["line"]["lot_mfr_range"]
        self.mfr = 0.5 * (lo + hi)

    def set_fault(self, name, severity):
        self.faults[name] = _clamp(severity)

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    def new_lot(self):
        lo, hi = self.d["line"]["lot_mfr_range"]
        self.mfr = round(self.rnd.uniform(lo, hi), 3)

    # true state ------------------------------------------------------------------------------------------------------
    def bush_target(self):
        return self.d["line"]["feed_bush_normal_c"] + 50.0 * self.faults["feed_bush_cooling_loss"]

    def clearance_true(self):
        return 1.0 + 2.8 * self.faults["screw_barrel_wear"]

    def state(self, n_rpm, bush_c):
        """Everything that follows from a screw speed and a feed bush temperature (iterated: pressure <-> leakage <-> melt)."""
        d, f = self.d, self.faults
        c, rh, me, w, th = d["conveying"], d["rheology"], d["melt"], d["wear"], d["thrust"]
        mat = d["material"]
        loss_feed = 0.12 * _clamp((bush_c - 50.0) / 35.0)
        cl = self.clearance_true()
        tm, ptip = rh["melt_t_ref_c"], th["p_design_bar"]
        for _ in range(4):
            loss_wear = w["leak_k"] * (cl ** 3 - 1) * ptip / th["p_design_bar"]
            q = c["specific_rate_kg_h_rpm"] * (1 - loss_wear - loss_feed) * n_rpm
            flow = ((max(q, 1.0) / rh["q_ref_kg_h"]) ** rh["power_law_n"] * (mat["mfr_ref_g10min"] / self.mfr) ** rh["mfr_exponent"]
                    * math.exp(-rh["temp_coeff_per_k"] * (tm - rh["melt_t_ref_c"])))
            pdie = rh["die_p_ref_bar"] * flow * (1 + 0.25 * f["die_restriction"])
            dp = rh["screen_dp_clean_bar"] * flow * (1 + 6.0 * f["screen_pack_clogging"])
            ptip = pdie + dp
            tm = (me["t0_c"] + me["k_rpm"] * (n_rpm - me["n_ref_rpm"]) + dp * 1e5 / (mat["melt_density_kg_m3"] * mat["melt_cp_kj_kgk"] * 1000.0)
                  + 11.0 * f["screw_barrel_wear"])
        return dict(n=n_rpm, bush=bush_c, q=q, loss_wear=loss_wear, loss_feed=loss_feed, pdie=pdie, dp=dp, ptip=ptip, tm=tm)

    def steady_speed(self, bush_c):
        """Screw speed the weight control settles at to hold the set output."""
        qset, q0 = self.d["conveying"]["output_set_kg_h"], self.d["conveying"]["specific_rate_kg_h_rpm"]
        nn = qset / q0
        for _ in range(6):
            s = self.state(nn, bush_c)
            nn = qset / (q0 * (1 - s["loss_wear"] - s["loss_feed"]))
        return nn

    # one published message ------------------------------------------------------------------------------------------
    def reading(self, s):
        d, f = self.d, self.faults
        dr, h, ln, gb = d["drive"], d["heating"], d["line"], d["gearbox"]
        fm = (d["material"]["mfr_ref_g10min"] / self.mfr) ** dr["mfr_exponent"]
        p = ((dr["no_load_kw"] + dr["drive_kwh_kg"] * s["q"] * fm) * (1 + 0.4 * s["loss_wear"]) * (1 + 0.03 * f["die_restriction"])
             + self.n(0.6))
        n_meas = s["n"] + self.n(0.05)
        torque = 9.549 * p * dr["efficiency"] / s["n"] * (1 + self.n(0.004))
        amb = ln["ambient_c"] + self.n(0.2)
        shaft = p * dr["efficiency"]
        zones = [h["set_c"][i] + self.n(0.5) for i in range(5)]
        zones[2] -= 5.0 * f["heater_band_failure"]
        zones = [z - 2.0 * f["barrel_cooling_stuck"] for z in zones]
        amps = [self.ir[i] * (1 + self.n(0.008)) for i in range(5)]
        amps[2] *= 1 - f["heater_band_failure"] / 3.0
        r = {
            "screw_speed_rpm": round(n_meas, 2), "motor_power_kw": round(p, 2), "motor_torque_knm": round(torque, 3),
            "output_kg_h": round(s["q"] * (1 + self.n(0.002)), 1), "feed_bush_temp_c": round(s["bush"] + self.n(0.3), 1),
        }
        for i in range(5):
            r[f"zone{i + 1}_temp_c"] = round(zones[i], 1)
        for i in range(5):
            r[f"zone{i + 1}_heater_a"] = round(amps[i], 2)
        r.update({
            "heater_power_kw": round(h["heater_kw_at_rate"] + 45.0 * f["barrel_cooling_stuck"] + self.n(0.4), 2),
            "p_screen_in_bar": round(s["ptip"] * (1 + self.n(0.003)), 1), "p_die_bar": round(s["pdie"] * (1 + self.n(0.003)), 1),
            "melt_temp_c": round(s["tm"] + self.n(0.3), 1),
            "gearbox_oil_temp_c": round(amb + gb["oil_k_per_kw"] * shaft + 12.0 * f["gearbox_bearing_damage"] + self.n(0.3), 1),
            "gearbox_vib_mm_s": round(max(0.2, 1.4 + 4.8 * f["gearbox_bearing_damage"] + self.n(0.05)), 2),
            "ambient_temp_c": round(amb, 1), "lot_mfr_g10min": self.mfr, "running": 1,
        })
        return r

    def measure(self):
        """A steady reading at the current faults (new resin lot each time, as in a long history)."""
        self.new_lot()
        bush = self.bush_target()
        return self.reading(self.state(self.steady_speed(bush), bush))


class Fault:
    """A failure mode whose severity ramps towards a target (0..1)."""
    def __init__(self):
        self.sev, self.target, self.rate = 0.0, 0.0, 0.0

    def set(self, target, ramp_s):
        self.target = _clamp(target)
        self.rate = abs(self.target - self.sev) / max(ramp_s, 1.0)

    def step(self, dt):
        if self.sev < self.target:
            self.sev = min(self.target, self.sev + self.rate * dt)
        elif self.sev > self.target:
            self.sev = max(self.target, self.sev - self.rate * dt)


class Plant:
    """The live stand-in used by the twin pages (same interface as the other twins' Plant).

    The line holds its set output: the screw speed follows the weight control with a 5 s lag, the feed bush temperature
    follows its cooling with a 20 s lag, and a new resin lot (another melt flow rate inside the grade's range) arrives every
    10 minutes. The clock of day plays no part, so the page opens in a sensible state at any hour.
    """
    TAU_N, TAU_BUSH, LOT_S = 5.0, 20.0, 600.0

    def __init__(self, twin, seed=4401):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.x = Extruder(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.reset()

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.bush = self.x.bush_target()
        self.n = self.x.steady_speed(self.bush)
        self.lot_timer = 0.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.x.faults[k] = f.sev
        self.t += dt * self.scale
        self.lot_timer += dt
        if self.lot_timer >= self.LOT_S:
            self.lot_timer = 0.0
            self.x.new_lot()
        if dt > 0:
            self.bush += min(1.0, dt / self.TAU_BUSH) * (self.x.bush_target() - self.bush)
            self.n += min(1.0, dt / self.TAU_N) * (self.x.steady_speed(self.bush) - self.n)
        return self.x.state(self.n, self.bush)

    def measure(self, true):
        return self.x.reading(true)
