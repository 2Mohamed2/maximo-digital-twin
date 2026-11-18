"""A stand-in for RP-2901: pumping unit, rod string, insert pump, well and rod pump controller, with injectable faults.

The real rod pump controller sends the same points (see telemetry.points in the twin file). Nothing here is used by
Monitor: the expected values are computed in Monitor from the twin file only. This model only produces believable
card features, pressures, rates and motor currents, and the fingerprint of each failure mode, for the tests and figures.
"""
import math
import random


class Well:
    PART_DEPTH_FT = 3000.0          # where the rod string parts in the rod_part failure mode (in the 3/4 in section)

    def __init__(self, twin, seed=1):
        self.t = twin
        d = twin["design"]
        self.u, self.r, self.p, self.f, self.o = d["unit"], d["rods"], d["pump"], d["fluid"], d["operation"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        secs = self.r["sections"]
        self.wr = sum(s["weight_lb_ft"] * s["length_ft"] for s in secs)
        above, left = 0.0, self.PART_DEPTH_FT
        for s in secs:
            ln = min(left, s["length_ft"])
            above += s["weight_lb_ft"] * ln
            left -= ln
        self.wr_above = above
        self.er = sum(12 * s["length_ft"] / (s["area_in2"] * self.r["modulus_psi"]) for s in secs)
        self.ap = math.pi / 4 * self.p["plunger_in"] ** 2
        self.grad = self.f["gradient_psi_ft"] * self.f["sg"]

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # true state ---------------------------------------------------------------------------------------------------
    def state(self):
        f, o = self.faults, self.o
        spm, s = self.u["spm"], self.u["stroke_in"]
        pt = o["tubing_pressure_psi"] - 40 * f["tubing_leak"]
        pc = o["casing_pressure_psi"] + 100 * f["gas_interference"]
        pip = (o["pip_psi"] - 195 * f["fluid_pound"] + 250 * f["gas_interference"] + 100 * f["tubing_leak"]
               + 80 * f["worn_pump"] + 150 * f["rod_part"])
        fo = (self.ap * (pt + self.grad * self.p["depth_ft"] - pip) * (1 - 0.10 * f["tubing_leak"]) * (1 - 0.05 * f["worn_pump"])
              * (1 - 0.97 * f["rod_part"]))
        wr = self.wr * (1 - f["rod_part"]) + self.wr_above * f["rod_part"]
        wrf = wr * (1 - 0.128 * self.f["sg"])
        acc = s * spm ** 2 / 70500
        drag = 3600 * f["paraffin_drag"]
        pprl = wrf + fo + acc * wr + drag
        mprl = wrf - acc * wr - drag
        fill = 93.0 - 38 * f["fluid_pound"] - 33 * f["gas_interference"] - 5 * f["worn_pump"]
        fill *= (1 - f["rod_part"])
        runtime = min(100.0, o["runtime_pct"] + 12 * max(f["fluid_pound"], f["gas_interference"]) + 10 * f["tubing_leak"])
        gross = s - fo * self.er + 2.5
        net = gross * fill / 100
        pd = 0.1166 * self.p["plunger_in"] ** 2 * net * spm * runtime / 100
        flow = pd * o["ve_expected"] * (1 - 0.5 * f["tubing_leak"]) * (1 - 0.42 * f["worn_pump"]) * (1 - f["rod_part"])
        cbe = self.u["cbe_lb"] * (1 - 0.22 * f["counterbalance_shift"])
        tu, td = (pprl - cbe) * s / 2000, (cbe - mprl) * s / 2000
        return dict(spm=spm, s=s, pt=pt, pc=pc, pip=pip, fo=fo, pprl=pprl, mprl=mprl, fill=fill, runtime=runtime, gross=gross,
                    net=net, flow=flow, tu=tu, td=td, tv=2.0 + 28 * f["worn_pump"])

    # one published message ------------------------------------------------------------------------------------------
    def measure(self):
        x = self.state()
        fill = max(0.0, min(100.0, x["fill"] + self.n(0.8)))
        gross = x["gross"] + self.n(0.3)
        tu, td = x["tu"], x["td"]
        return {
            "running": 1, "spm": round(x["spm"] + self.n(0.02), 2), "surface_stroke_in": round(x["s"] + self.n(0.1), 2),
            "runtime_pct": round(min(100.0, x["runtime"] + abs(self.n(0.3)) * (1 if x["runtime"] < 99.5 else 0)), 1),
            "pumpoff_cycles_24h": 0 if x["runtime"] >= 99.5 else 12,
            "pprl_lb": round(x["pprl"] + self.n(40), 0), "mprl_lb": round(x["mprl"] + self.n(40), 0),
            "pump_fillage_pct": round(fill, 1), "pump_gross_stroke_in": round(gross, 2), "pump_net_stroke_in": round(gross * fill / 100, 2),
            "pump_fluid_load_lb": round(x["fo"] + self.n(35), 0), "tv_load_loss_pct": round(max(0.0, x["tv"] + self.n(0.5)), 1),
            "tubing_pressure_psi": round(x["pt"] + self.n(1.0), 1), "casing_pressure_psi": round(x["pc"] + self.n(1.0), 1),
            "pip_psi": round(x["pip"] + self.n(3.0), 1), "flow_bpd": round(max(0.0, x["flow"] + self.n(1.5)), 1),
            "motor_kw": round(4 + 0.032 * (abs(tu) + abs(td)) + self.n(0.2), 2),
            "current_up_a": round(12 + 0.12 * max(0.0, tu) + self.n(0.3), 1), "current_down_a": round(12 + 0.12 * max(0.0, td) + self.n(0.3), 1),
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

    The unit strokes at its real speed so the 3D beam moves like the real one. With pump-off control working, the RPC
    stops the unit for a short idle period every POC_EVERY_S seconds (demo cadence) and starts it again; with fluid pound
    or gas interference the run time is 100 % and it never stops.
    """
    POC_EVERY_S, POC_IDLE_S = 120.0, 15.0

    def __init__(self, twin, seed=2901):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.w = Well(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.crank, self.timer = 0.0, 0.0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.crank, self.timer, self.running = 0.0, 0.0, True

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.w.faults[k] = f.sev
        self.t += dt * self.scale
        x = self.w.state()
        self.timer += dt
        poc = x["runtime"] < 99.5
        self.running = not (poc and self.timer % self.POC_EVERY_S > self.POC_EVERY_S - self.POC_IDLE_S)
        if self.running:
            self.crank = (self.crank + 360.0 * x["spm"] / 60.0 * dt) % 360.0
        # polished rod position (0 = bottom) and an approximate surface load at this crank angle
        pos = x["s"] / 2 * (1 - math.cos(math.radians(self.crank)))
        up = self.crank < 180
        load = (x["pprl"] if up else x["mprl"]) - (x["pprl"] - x["mprl"]) * 0.15 * math.sin(math.radians(self.crank * 2)) ** 2
        return {"crank_deg": round(self.crank, 1), "position_in": round(pos, 2), "load_lb": round(load, 0), "running": self.running}

    def measure(self, true):
        r = self.w.measure()
        r["running"] = 1 if true["running"] else 0
        return r
