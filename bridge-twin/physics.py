"""A stand-in for BR-6001: deck temperatures, bearing and joint movements, pier tilt, deck strain and the weigh-in-motion
station, with injectable faults.

The real bridge sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the expected
values are computed in Monitor from the twin file only. This model only produces believable readings and fault fingerprints
for the tests, the figures and the live pages. Pure Python (math, random): it also runs in the browser (Pyodide).

Mechanics of the stand-in (one summer day, the deck free to expand from the fixed bearing on P1):
  the deck moves alpha x L x (Te - T0) at each support; the pier P2 head is pushed by the bearing friction (Coulomb, sign of
  the movement); a seized bearing stops sliding and the pier head is dragged with the deck; a blocked joint holds the deck end
  at A2, so part of the expansion becomes compressive strain; failed control springs let one modular gap close.
"""
import math
import random

import twin_calc as tc


class Bridge:
    def __init__(self, twin, seed=1):
        self.twin = twin
        self.k = tc._k(twin)
        d = twin["design"]
        self.demo, self.b = d["demo"], d["bearing_p2"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.path0 = self.b["path_rate_design_m_per_y"] * self.b["service_years"]

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # temperatures over the day ------------------------------------------------------------------------------------
    def temps(self, h):
        dm = self.demo
        c = lambda mean, amp, peak: mean + amp * math.cos(2 * math.pi * (h - peak) / 24)
        return c(dm["air_mean_c"], dm["air_amp_c"], 15.0), c(dm["slab_mean_c"], dm["slab_amp_c"], 14.5), c(dm["girder_mean_c"], dm["girder_amp_c"], 16.5)

    def te_rate(self, h):
        """dTe/dt in K per hour (sign gives the direction the deck slides)."""
        dm, w = self.demo, self.k["w"]
        s = lambda amp, peak: -amp * 2 * math.pi / 24 * math.sin(2 * math.pi * (h - peak) / 24)
        return w * s(dm["slab_amp_c"], 14.5) + (1 - w) * s(dm["girder_amp_c"], 16.5)

    # true state -------------------------------------------------------------------------------------------------------
    def true_state(self, h):
        k, f, dm = self.k, self.faults, self.demo
        air, slab, girder = self.temps(h)
        te = k["w"] * slab + (1 - k["w"]) * girder
        dt = te - k["t0"]
        ep2, ea2, ea1 = k["a_p2"] * dt, k["a_a2"] * dt, k["a_a1"] * dt
        # blocked joint at A2: the deck end is held since Te = blocked_since; part of the expansion becomes strain
        jb, rf, tb = f["joint_blocked"], dm["restraint_factor"], dm["blocked_since_te_c"]
        held = jb * rf * max(0.0, te - tb)
        u_a2 = ea2 - k["a_a2"] * held
        u_p2deck = ep2 - k["a_p2"] * held
        restraint = -held * k["alpha"] * 1e6
        # bearing P2: friction drags the pier head; a seized bearing does not slide at all
        s = f["bearing_seized"]
        u_stuck = k["a_p2"] * (dm["seized_since_te_c"] - k["t0"])
        slide = u_p2deck + s * (u_stuck - u_p2deck)
        mu = k["mu_d"] + 0.027 * f["ptfe_wear"]
        direction = math.tanh(self.te_rate(h) / 0.3)
        head = (u_p2deck - slide) + direction * k["n"] * mu * k["N"] / k["kp"]
        tilt = 1.5 * head / k["H"]
        # modular joint A2: total opening shared by the control springs
        tot = k["g0a2"] - u_a2
        c = f["joint_control_failure"]
        g2 = tot / 3
        g3 = max(0.0, tot / 3 - 28.0 * c)
        g1 = tot - g2 - g3
        return {"h": h, "air": air, "slab": slab, "girder": girder, "te": te, "u_p2": slide, "u_a2": u_a2, "tilt": tilt,
                "gap_a1": k["g0a1"] - ea1, "g": (g1, g2, g3), "impact": 3.0 + 6.0 * c, "restraint": restraint, "mu": mu}

    def vehicle(self):
        """Gross weight (kN) of a heavy vehicle in the slow lane."""
        w = 300.0 + self.n(80.0) + 150.0 * self.faults["overweight_traffic"]
        return max(120.0, min(700.0, w))

    def reading(self, s, w, path):
        k, f = self.k, self.faults
        g1, g2, g3 = (max(0.0, x + self.n(0.3)) for x in s["g"])
        rate = self.b["path_rate_design_m_per_y"] * (1 + 2.75 * f["sliding_path_fast"]) + self.n(5.0)
        return {
            "slab_temp_c": round(s["slab"] + self.n(0.15), 2), "girder_temp_c": round(s["girder"] + self.n(0.15), 2),
            "air_temp_c": round(s["air"] + self.n(0.2), 2),
            "bearing_p2_disp_mm": round(s["u_p2"] + self.n(0.2), 2),
            "bearing_p2_sliding_gap_mm": round(self.b["sliding_gap_new_mm"] - self.b["sliding_gap_wear_mm_per_km"] * path / 1000
                                               - 1.2 * f["ptfe_wear"] + self.n(0.02), 3),
            "bearing_p2_path_m": round(path, 1), "bearing_p2_path_rate_m_y": round(rate, 1),
            "bearing_a2_disp_mm": round(s["u_a2"] + 15.0 * f["displacement_sensor"] + self.n(0.2), 2),
            "pier_p2_tilt_mrad": round(s["tilt"] + self.n(0.01), 4),
            "joint_a1_gap_mm": round(s["gap_a1"] + self.n(0.3), 2),
            "joint_a2_gap1_mm": round(g1, 2), "joint_a2_gap2_mm": round(g2, 2), "joint_a2_gap3_mm": round(g3, 2),
            "joint_a2_impact_g": round(max(0.5, s["impact"] + self.n(0.3)), 2),
            "strain_static_ue": round(k["kdt"] * (s["slab"] - s["girder"]) + s["restraint"] + self.n(2.0), 1),
            "strain_peak_ue": round(k["cs"] * w * (1 + 0.35 * f["girder_stiffness_loss"]) * (1 + self.n(0.02)), 1),
            "wim_last_heavy_kn": round(w, 1), "wim_heavy_24h": int(round(2400 + self.n(60))),
            "wim_overweight_24h": int(max(0, round(3 + self.n(1.2) + 60 * f["overweight_traffic"]))),
        }

    def measure(self, h=10.0):
        return self.reading(self.true_state(h), self.vehicle(), self.path0)


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

    t is the plant clock in seconds; it runs `demo.time_scale` times faster than real time, so one bridge day lasts 24 minutes.
    A heavy vehicle crosses about every 15 real seconds; the bearing's sliding path accumulates at its current rate.
    """
    VEHICLE_EVERY_S = 15.0

    def __init__(self, twin, seed=6001):
        self.twin = twin
        self.scale = float(twin["design"].get("demo", {}).get("time_scale", 1))
        self.b = Bridge(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 10 * 3600.0
        self.running, self.trip = True, 0
        self.path = self.b.path0
        self.w = 300.0
        self.since_vehicle = 0.0

    def hour(self):
        return (self.t / 3600.0) % 24

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.path = self.b.path0
        self.since_vehicle = 0.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.b.faults[k] = f.sev
        self.t += dt * self.scale
        rate = self.b.b["path_rate_design_m_per_y"] * (1 + 2.75 * self.b.faults["sliding_path_fast"])
        self.path += rate * dt * self.scale / (365 * 86400)
        self.since_vehicle += dt
        if self.since_vehicle >= self.VEHICLE_EVERY_S:
            self.since_vehicle = 0.0
            self.w = self.b.vehicle()
        return self.b.true_state(self.hour())

    def measure(self, true):
        return self.b.reading(true, self.w, self.path)
