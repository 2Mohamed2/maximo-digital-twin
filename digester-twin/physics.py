"""A stand-in for AD-4901: the digester, its feed, heat exchanger, mixers, gas line and CHP, with injectable faults.

The real plant sends the same points (see telemetry.points in the twin file). Nothing here is used by Monitor: the
expected values are computed in Monitor from the twin file only. This model only produces believable readings and fault
fingerprints for the tests, the figures and the live pages. Pure Python (math, random): it also runs in the browser.
"""
import math
import random


def _hx(ua, m_s, t_s_in, m_w, t_w_in, cw):
    """Counter-flow heat exchanger, effectiveness-NTU. Flows in m3/h, cw in kWh/m3K. Returns heat (kW)."""
    cs, cwat = m_s * cw, m_w * cw
    cmin, cmax = min(cs, cwat), max(cs, cwat)
    ntu, cr = ua / cmin, cmin / cmax
    eff = (1 - math.exp(-ntu * (1 - cr))) / (1 - cr * math.exp(-ntu * (1 - cr)))
    return eff * cmin * (t_w_in - t_s_in)


class Digester:
    def __init__(self, twin, seed=1):
        self.tw = twin
        d = twin["design"]
        self.tk, self.p, self.hx, self.mx, self.ch = d["tank"], d["process"], d["heat_exchanger"], d["mixing"], d["chp"]
        self.lhv = d["energy"]["ch4_lhv_kwh_m3"]
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}
        self.holder = 55.0

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # heating: the controller raises the hot water temperature until the heat matches the demand, up to its limit ---------
    def heating(self, q, t_feed, t_amb):
        p, hx, cw = self.p, self.hx, self.hx["water_heat_kwh_m3k"]
        ua = hx["ua_design_kw_k"] * (1 - 0.6 * self.faults["hx_fouling"])
        m_s, m_w = hx["recirc_flow_m3h"] + q / 24, hx["hw_flow_m3h"]

        def at(tdig):
            t_in = (hx["recirc_flow_m3h"] * tdig + q / 24 * t_feed) / m_s
            need = q / 24 * cw * (tdig - t_feed) + self.tk["ua_wall_kw_k"] * (tdig - t_amb)
            return t_in, need
        tdig = p["temp_set_c"]
        t_in, need = at(tdig)
        lo, hi = t_in + 0.5, hx["hw_supply_max_c"]
        for _ in range(60):                      # supply temperature that delivers the demand at the set point
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if _hx(ua, m_s, t_in, m_w, mid, cw) < need else (lo, mid)
        ts = (lo + hi) / 2
        if _hx(ua, m_s, t_in, m_w, hx["hw_supply_max_c"], cw) < need:   # cannot keep the set point: the tank cools
            ts = hx["hw_supply_max_c"]
            a, b = t_feed + 1, p["temp_set_c"]
            for _ in range(60):
                mid = (a + b) / 2
                ti, nd = at(mid)
                a, b = (mid, b) if _hx(ua, m_s, ti, m_w, ts, cw) > nd else (a, mid)
            tdig = (a + b) / 2
            t_in, need = at(tdig)
        qh = _hx(ua, m_s, t_in, m_w, ts, cw)
        return dict(tdig=tdig, t_in=t_in, t_out=t_in + qh / (m_s * cw), ts=ts, tr=ts - qh / (m_w * cw), m_s=m_s, m_w=m_w, q=qh)

    def true_state(self):
        f, p, ch = self.faults, self.p, self.ch
        q = p["feed_flow_m3d"] * (1 + self.n(0.012))
        t_feed, t_amb = p["feed_temp_c"] + self.n(0.3), self.tk["ambient_design_c"] + self.n(0.8)
        h = self.heating(q, t_feed, t_amb)
        active = 95.0 - 27.0 * f["grit_accumulation"]
        vsr = p["vsr_design_pct"] - 8.0 * f["souring"] - 5.0 * f["grit_accumulation"] - 1.5 * (p["temp_set_c"] - h["tdig"]) / 3
        vin = p["feed_vs_pct"]
        vsl = q * p["sludge_density_kg_m3"] / 1e4 * p["feed_ds_pct"] * vin
        gas = vsl * vsr / 100 * p["gas_yield_m3_kgvsd"] / 24 * (1 - 0.38 * f["souring"])
        ch4 = p["ch4_design_pct"] - 13.0 * f["souring"]
        full = ch["power_el_kw"] / ch["eta_el"] / (ch4 / 100 * self.lhv)          # CHP gas at full load
        chp_gas = min(full, gas)
        return dict(q=q, t_feed=t_feed, t_amb=t_amb, h=h, active=active, vsr=vsr, vin=vin, gas=gas, ch4=ch4, chp_gas=chp_gas,
                    mix=1 - 0.65 * f["mixing_failure"], foam=0.12 + 1.1 * f["foaming"])

    def measure(self, s=None):
        s = s or self.true_state()
        f, p, h = self.faults, self.p, s["h"]
        vi, vsr = s["vin"] / 100, s["vsr"] / 100
        vo = vi * (1 - vsr) / (1 - vi * vsr)
        strat = 0.4 + 4.3 * f["mixing_failure"]
        td = h["tdig"]
        eff = self.ch["eta_el"] * (1 - 0.17 * f["chp_degradation"])
        fuel = s["chp_gas"] * s["ch4"] / 100 * self.lhv
        self.holder = max(5.0, min(95.0, self.holder + self.n(0.4)))
        return {
            "feed_flow_m3d": round(s["q"], 2), "feed_ds_pct": round(p["feed_ds_pct"] + self.n(0.05), 3),
            "feed_vs_pct": round(s["vin"] + self.n(0.15), 2), "feed_temp_c": round(s["t_feed"], 2),
            "temp_top_c": round(td + 0.25 * strat + self.n(0.05), 2), "temp_mid_c": round(td - 0.05 * strat + self.n(0.05), 2),
            "temp_bottom_c": round(td - 0.75 * strat + self.n(0.05), 2),
            "ph": round(7.15 - 0.62 * f["souring"] + self.n(0.02), 2), "foam_layer_m": round(max(0.0, s["foam"] + self.n(0.02)), 3),
            "fos_tac": round(max(0.05, p["fostac_normal"] + 0.6 * f["souring"] + self.n(0.01)), 3),
            "digested_vs_pct": round(100 * vo + self.n(0.15), 2), "active_volume_pct": round(s["active"] + self.n(0.5), 1),
            "mixer_power_kw": round(self.mx["power_design_kw"] * s["mix"] + self.n(0.15), 2),
            "biogas_flow_m3h": round(s["gas"] * (1 + self.n(0.01)), 2), "ch4_pct": round(s["ch4"] + self.n(0.3), 2),
            "h2s_ppm": round(max(0.0, 140 + 760 * f["h2s_high"] + self.n(8)), 1), "holder_fill_pct": round(self.holder, 1),
            "hx_sludge_flow_m3h": round(h["m_s"] + self.n(0.2), 2), "hx_sludge_in_c": round(h["t_in"] + self.n(0.03), 2),
            "hx_sludge_out_c": round(h["t_out"] + self.n(0.03), 2), "hw_flow_m3h": round(h["m_w"] * (1 + self.n(0.004)), 3),
            "hw_supply_c": round(h["ts"] + self.n(0.05), 2), "hw_return_c": round(h["tr"] + self.n(0.05), 2),
            "ambient_temp_c": round(s["t_amb"], 2), "chp_gas_m3h": round(s["chp_gas"] * (1 + self.n(0.005)), 2),
            "chp_power_kw": round(fuel * eff * (1 + self.n(0.006)), 1),
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

    The digester runs at steady state; the faults ramp in and out. The clock (t) only moves the gas holder level and the
    mixer angle for the 3D page: the process itself does not depend on the time of day.
    """

    def __init__(self, twin, seed=4901):
        self.twin = twin
        self.d = Digester(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.angle = 0.0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.d.holder = 55.0

    def fault_state(self):
        return {k: round(f.sev, 3) for k, f in self.faults.items()}

    def step(self, dt=1.0):
        for k, f in self.faults.items():
            f.step(dt)
            self.d.faults[k] = f.sev
        self.t += dt
        if dt >= 2.0:                            # browser warm-up: nothing to integrate, skip the heat balance
            return None
        s = self.d.true_state()
        self.angle = (self.angle + dt * 2 * math.pi * 0.5 * s["mix"]) % (2 * math.pi)
        s["angle"] = self.angle
        return s

    def measure(self, true):
        return self.d.measure(true or self.d.true_state())
