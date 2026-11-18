"""A stand-in for KL-4201: the kiln, its drive, tyres, shell scanner, preheater, burning zone, grate cooler and stack, with
injectable faults.

The real plant sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and
fault fingerprints for the tests and the figures. Pure Python (math, random): it also runs in the browser (Pyodide).

The fuel follows a heat balance: the true specific heat consumption is the sum of the true losses, so a healthy kiln
closes its balance and every fault that costs heat (cooler, false air, hot shell) also costs fuel.
"""
import math
import random

import twin_calc as tc


class Kiln:
    def __init__(self, twin, seed=1):
        self.twin = twin
        self.k = tc._k(twin)
        d = twin["design"]
        self.kl, self.hb, self.sh, self.bz, self.gs = d["kiln"], d["heat_balance"], d["shell"], d["burning_zone"], d["gas"]
        self.dr, self.ty, self.cool, self.st = d["drive"], d["tyres"], d["cooler"], d["stack"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state ------------------------------------------------------------------------------------------------------
    def true_state(self, load=1.0, ambient=None):
        k, f, hb, ty = self.k, self.faults, self.hb, self.ty
        amb = hb["ambient_design_c"] if ambient is None else ambient
        da = amb - hb["ambient_design_c"]
        cl = k["cl_d"] * load
        speed = k["n_d"] * load                      # the operators hold the kiln filling: speed follows the feed
        # shell scanner
        fr = f["refractory_loss"]
        s_max = self.sh["bz_max_design_c"] + 205.0 * fr + 0.6 * da
        s_mean = self.sh["mean_design_c"] + 12.0 * fr + 0.6 * da
        pos = 14.0 if fr > 0.15 else self.sh["hot_spot_pos_m"]
        # drive and ring
        rg = f["ring_formation"]
        torque = (k["t_e"] + (k["t_d"] - k["t_e"]) * load / (speed / k["n_d"])) * (1 + 0.5 * rg)
        o2_in = self.gs["o2_inlet_design_pct"] - 2.0 * rg
        co_in = self.gs["co_inlet_design_ppm"] + 2500.0 * rg ** 2
        # preheater and false air
        fa_d = self.gs["false_air_design_pct"] / 100
        fa = fa_d + 0.15 * f["false_air"]
        o2c = self.gs["o2_calciner_design_pct"]
        o2x = (o2c + 21 * fa) / (1 + fa)
        ph_flow = hb["ph_gas_nm3_kg"] * cl * (1 + fa) / (1 + fa_d)
        ph_t = hb["ph_exit_design_c"] - 20.0 * f["false_air"] + 0.3 * da
        # cooler
        fc = f["cooler_degradation"]
        ce_t = hb["cooler_exh_design_c"] + 90.0 * fc + 0.5 * da
        cl_out = hb["clinker_out_design_c"] + 120.0 * fc + 0.8 * da
        ce_flow = hb["cooler_exh_nm3_kg"] * cl * (1 + 0.1 * fc)
        sec = self.cool["sec_air_design_c"] - 200.0 * fc
        # burning zone
        bzt = self.bz["bzt_design_c"] - 70.0 * f["burning_zone_cold"]
        nox = k["nox_ref"] * math.exp(k["knox"] * (bzt - k["bzt_d"])) * (1 - 0.15 * rg)
        fl = self.bz["free_lime_design_pct"] + 1.6 * f["burning_zone_cold"]
        # tyres
        tsh = ty["shell_under_tyre2_design_c"] + 0.6 * da
        tty = ty["tyre2_design_c"] + 0.6 * da
        gap2 = ty["cold_gap_mm"] + 5.0 * f["tyre_pad_wear"] - k["alpha"] * k["D"] * 1000 * (tsh - tty)
        s = {"cl": cl, "speed": speed, "amb": amb, "s_max": s_max, "s_mean": s_mean, "pos": pos, "torque": torque,
             "o2_in": o2_in, "co_in": co_in, "o2c": o2c, "o2x": o2x, "ph_flow": ph_flow, "ph_t": ph_t, "ce_t": ce_t,
             "cl_out": cl_out, "ce_flow": ce_flow, "sec": sec, "bzt": bzt, "nox": nox, "fl": fl, "tsh": tsh, "tty": tty,
             "gap2": gap2, "mig2": math.pi * gap2, "mig1": ty["migration_t1_mm"], "mig3": ty["migration_t3_mm"],
             "ov2": ty["ovality_base_pct"] + ty["ovality_per_gap_mm"] * gap2, "lhv": hb["fuel_lhv_mj_kg"]}
        # the true heat consumption is the true heat balance
        r0 = self._reading(s, noise=False)
        r0.update(fuel_kiln_tph=1.0, fuel_calciner_tph=0.0, fuel_lhv_mjkg=1.0)
        shc = tc.evaluate(self.twin, r0)["shc_balance_kjkg"]
        s["shc"] = shc
        s["fuel"] = shc * cl / s["lhv"] / 1000
        s["stack_ref"] = self.st["nox_ref_design_mgnm3"] * nox / k["nox_ref"]
        return s

    def _reading(self, s, noise=True):
        n = self.n if noise else (lambda x: 0.0)
        f = self.faults
        share = self.hb["calciner_share"]
        fuel = s.get("fuel", 0.0)
        o2s = self.st["o2_design_pct"] + n(0.1)
        return {
            "clinker_tph": round(s["cl"] * (1 + n(0.004)), 2), "kiln_speed_rpm": round(s["speed"] + n(0.005), 3),
            "drive_torque_pct": round(s["torque"] * (1 + n(0.01)), 2),
            "drive_power_kw": round(s["torque"] / 100 * self.dr["rated_kw"] * s["speed"] / self.dr["rated_rpm"] * (1 + n(0.01)), 1),
            "fuel_kiln_tph": round(fuel * (1 - share) * (1 + n(0.006)), 3),
            "fuel_calciner_tph": round(fuel * share * (1 - 0.15 * f["fuel_meter_drift"]) * (1 + n(0.006)), 3),
            "fuel_lhv_mjkg": round(s["lhv"] + n(0.08), 3),
            "bzt_c": round(s["bzt"] - 110.0 * f["pyrometer_fouling"] + n(4), 1),
            "free_lime_pct": round(max(0.2, s["fl"] + n(0.1)), 2),
            "nox_inlet_ppm": round(s["nox"] * (1 + n(0.03)), 0),
            "o2_inlet_pct": round(max(0.1, s["o2_in"] + n(0.08)), 2), "co_inlet_ppm": round(max(0.0, s["co_in"] + n(25)), 0),
            "o2_calciner_pct": round(s["o2c"] + n(0.05), 2), "o2_ph_exit_pct": round(s["o2x"] + n(0.05), 2),
            "ph_exit_temp_c": round(s["ph_t"] + n(1.0), 1), "ph_exit_flow_knm3h": round(s["ph_flow"] * (1 + n(0.008)), 2),
            "shell_max_c": round(s["s_max"] + n(3), 1), "shell_max_pos_m": round(s["pos"] + n(0.3), 1),
            "shell_mean_c": round(s["s_mean"] + n(1.5), 1), "ambient_c": round(s["amb"] + n(0.2), 1),
            "tyre1_migration_mm": round(s["mig1"] + n(0.25), 2), "tyre2_migration_mm": round(s["mig2"] + n(0.25), 2),
            "tyre3_migration_mm": round(s["mig3"] + n(0.25), 2), "tyre2_temp_c": round(s["tty"] + n(1.0), 1),
            "shell_t2_c": round(s["tsh"] + n(1.5), 1), "ovality2_pct": round(s["ov2"] + n(0.01), 3),
            "clinker_out_c": round(s["cl_out"] + n(2), 1), "cooler_exh_temp_c": round(s["ce_t"] + n(1.5), 1),
            "cooler_exh_flow_knm3h": round(s["ce_flow"] * (1 + n(0.008)), 2), "sec_air_c": round(s["sec"] + n(8), 0),
            "stack_nox_mgnm3": round(s.get("stack_ref", 0.0) * (21 - o2s) / 11 * (1 + n(0.02)), 1), "stack_o2_pct": round(o2s, 2),
        }

    # one published message ---------------------------------------------------------------------------------------------
    def measure(self, s=None):
        s = s or self.true_state()
        return self._reading(s)


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

    The kiln runs at design output with a slow 3 % swing (demo.load_swing over demo.load_period_s real seconds); the kiln
    speed follows the feed. The ambient swings 4 K over the plant day (only the shells and cooler see it).
    """

    def __init__(self, twin, seed=4201):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.swing = float(demo.get("load_swing", 0.03))
        self.period = float(demo.get("load_period_s", 900))
        self.kiln = Kiln(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.clock = 0.0
        self.running, self.trip = True, 0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.clock = 0.0
        self.running, self.trip = True, 0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.kiln.faults[k] = f.sev
        self.t += dt * self.scale
        self.clock += dt
        load = 1 + self.swing * math.sin(2 * math.pi * self.clock / self.period)
        amb = self.kiln.hb["ambient_design_c"] + 4 * math.sin(2 * math.pi * (self.t / 86400 - 0.375))
        return self.kiln.true_state(load, amb)

    def measure(self, true):
        return self.kiln.measure(true)
