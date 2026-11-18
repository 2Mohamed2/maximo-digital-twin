"""A stand-in for UPS-6101: the four power modules, the DC links, the cooling fans, the static bypass and the two VRLA
battery strings with their monitor, feeding a data hall's IT load, with injectable faults.

The real UPS network card, battery monitor and room sensors send the same points (see telemetry.points in the twin file).
Nothing here is used by Monitor: the expected values are computed in Monitor from the twin file only. This model only
produces believable readings and fault fingerprints for the tests, the figures and the live pages.
"""
import math
import random

V_PH = 400.0 / math.sqrt(3)
PF_LOAD = 0.99          # IT load with power-factor-corrected supplies (assumption, used only to make currents)
SHARES = (0.995, 0.985, 1.02)


class Ups:
    def __init__(self, twin, seed=1):
        self.tw = twin
        d = twin["design"]
        self.u, self.e, self.b, self.th, self.dc = d["ups"], d["efficiency"], d["battery"], d["thermal"], d["dc_link"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.age_days, self.t_life = 1170.0, 23.8

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state ---------------------------------------------------------------------------------------------------
    def loss(self, p, n):
        e, ni = self.e, self.u["upm_installed"]
        return (n * e["loss_a_kw"] / ni + e["loss_b"] * p + e["loss_c_per_kw"] * p * p * ni / n) * (1 + 0.6 * self.faults["converter_losses"])

    def true_state(self, load_kw=110.0, inlet_c=24.0, room_c=23.5):
        """One operating point: IT load (kW, balanced as in the hall's design), UPS inlet air and battery room temperature."""
        f = self.faults
        n = self.u["upm_installed"] - (1 if f["upm_failure"] > 0.5 else 0)
        extra = 16.0 * f["phase_load_growth"]          # new racks plugged into phase L1
        ph = [load_kw / 3 * s for s in SHARES]
        ph[0] += extra
        p = sum(ph)
        loss = self.loss(p, n)
        per = loss / n
        cmd = max(30.0, min(100.0, 35.0 + 45.0 * per / 1.5 + 2.0 * (inlet_c - 24.0)))
        rise = self.th["r_th_k_per_kw"] * per * (1 + 0.8 * f["fan_wear"])
        ripple = (self.dc["ripple_floor_v"] + (self.dc["ripple_full_v"] - self.dc["ripple_floor_v"]) * p / n / self.u["upm_kw"]) * (1 + 2.0 * f["dc_capacitor_ageing"])
        return dict(p=p, ph=ph, n=n, loss=loss, cmd=cmd, fan=cmd * (1 - 0.3 * f["fan_wear"]), hs=inlet_c + rise, inlet=inlet_c,
                    ripple=ripple, tb=room_c + 1.0 + 13.0 * f["battery_room_hot"],
                    soh=95.5 - 50.5 * f["battery_ageing"], rmax=self.b["r_block_mohm"] * 1.07 * (1 + 0.6 * f["battery_ageing"]),
                    byp=round(0.4 + 6.0 * f["bypass_transfers"]), mode=1)

    # one published message ------------------------------------------------------------------------------------------
    def measure(self, s=None):
        s = s or self.true_state()
        n = self.n
        pout = s["p"] + n(0.08)
        nblk = self.b["blocks_per_string"]
        return {
            "input_voltage_v": round(400.0 + n(1.5), 1), "input_power_kw": round(s["p"] + s["loss"] + n(0.08), 2),
            "input_freq_hz": round(50.0 + n(0.02), 3),
            "output_voltage_v": round(400.0 + n(0.4), 1), "output_power_kw": round(pout, 2),
            "output_current_l1_a": round(s["ph"][0] * 1000 / (V_PH * PF_LOAD) * (1 + n(0.003)), 1),
            "output_current_l2_a": round(s["ph"][1] * 1000 / (V_PH * PF_LOAD) * (1 + n(0.003)), 1),
            "output_current_l3_a": round(s["ph"][2] * 1000 / (V_PH * PF_LOAD) * (1 + n(0.003)), 1),
            "upm_online": s["n"], "dc_bus_v": round(self.dc["dc_bus_nominal_v"] + n(1.0), 1),
            "dc_ripple_v": round(s["ripple"] * (1 + n(0.03)), 2),
            "heatsink_temp_max_c": round(s["hs"] + n(0.3), 2), "inlet_air_c": round(s["inlet"] + n(0.1), 2),
            "fan_speed_pct": round(s["fan"] * (1 + n(0.01)), 1), "fan_cmd_pct": round(s["cmd"], 1),
            "ups_mode": s["mode"], "ess_enabled": 0, "bypass_events_30d": s["byp"],
            "battery_voltage_v": round(nblk * 13.65 + n(0.3), 1), "battery_current_a": round(0.6 + n(0.05), 2),
            "battery_temp_c": round(s["tb"] + n(0.15), 2), "battery_r_max_mohm": round(s["rmax"] * (1 + n(0.01)), 3),
            "battery_soh_pct": round(s["soh"] + n(0.4), 1),
            "battery_age_days": round(self.age_days, 2), "battery_temp_life_c": round(self.t_life, 2),
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

    The IT load of the hall swings gently over the day around its design value (more servers busy in the afternoon), the
    UPS inlet air follows the room cooling, and the UPS stays in double conversion. P.t is the visitor's local time in
    seconds; during the warm-up (dt >= 2 s) the clock is ignored so the page opens at a normal operating point.
    """

    def __init__(self, twin, seed=6101):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.base = twin["design"]["site"]["it_load_design_kw"]
        self.u = Ups(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.running, self.trip = True, 0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.u.faults[k] = f.sev
        self.t += dt * self.scale
        self.u.age_days += dt * self.scale / 86400
        day = 0.0 if dt >= 2.0 else math.sin(2 * math.pi * ((self.t % 86400) / 86400 - 0.375))
        load = self.base * (1 + 0.035 * day) + self.u.n(0.4)
        return self.u.true_state(load, 24.0 + 0.6 * day, 23.5 + 0.3 * day)

    def measure(self, true):
        return self.u.measure(true)
