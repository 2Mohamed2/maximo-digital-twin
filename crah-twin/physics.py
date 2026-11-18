"""A stand-in for CR-6301: the chilled water coil, the valve, the EC fans, the filters and the air paths of the data hall
(servers, bypass and recirculation), with injectable faults.

The real unit controller, BTU meter and remote sensors send the same points (see telemetry.points in the twin file).
Nothing here is used by Monitor: the expected values are computed in Monitor from the twin file only. This model only
produces believable readings and fault fingerprints for the tests, the figures and the live pages.

Air paths (steady state): the servers draw m_it = Q_IT / (cp dT_IT). A fraction r of what they draw is their own hot exhaust
(recirculation); a fraction BF of what the unit supplies goes straight back to it (bypass). Then
    unit airflow  m_c = (1 - r) m_it / (1 - BF)
    T_out - T_sup = dT_IT / (1 - r),  T_in = T_sup + r dT_IT / (1 - r),  T_ret = BF T_sup + (1 - BF) T_out
and the unit removes exactly Q_IT. The coil is a counterflow exchanger (effectiveness-NTU) with UA from the twin's scaling law;
the controller finds the water flow that holds the supply air at its setpoint, up to the valve's maximum flow.
"""
import math
import random

import twin_calc as tc


class Crah:
    def __init__(self, twin, seed=1):
        self.tw = twin
        self.k = tc._k(twin)
        d = twin["design"]
        self.si, self.fa, self.demo = d["site"], d["fan"], d.get("demo", {})
        self.rnd = random.Random(seed)
        self.faults = {k: 0.0 for k in twin["failure_modes"] if not k.startswith("$")}

    def set_fault(self, name, severity):
        self.faults[name] = max(0.0, min(1.0, severity))

    def clear(self):
        for k in self.faults:
            self.faults[k] = 0.0

    def n(self, s):
        return self.rnd.gauss(0, s)

    # coil ------------------------------------------------------------------------------------------------------------
    def ua(self, v, fw):
        k = self.k
        return k["ua"] * (v / k["v"]) ** k["ea"] * (fw / k["fw"]) ** k["ew"] * (1 - 0.5 * self.faults["coil_fouling"])

    def supply_for(self, q, m_air, v, fw, tchws):
        """Supply air temperature when the coil removes q kW with water flow fw (counterflow effectiveness-NTU)."""
        k = self.k
        ca, cw = m_air * k["cp"], fw * k["rw"] / 3600 * k["cw"]
        cmin, cmax = min(ca, cw), max(ca, cw)
        ntu, cr = self.ua(v, fw) / cmin, cmin / cmax
        e = math.exp(-ntu * (1 - cr))
        eps = (1 - e) / (1 - cr * e) if cr < 0.999 else ntu / (1 + ntu)
        return tchws + q / (eps * cmin) - q / ca

    # true state --------------------------------------------------------------------------------------------------------
    def true_state(self, q_it=None, phase=None, tchws=10.0):
        f, k, si = self.faults, self.k, self.si
        q_it = si["it_load_kw"] if q_it is None else q_it
        phase = self.rnd.uniform(0, 2 * math.pi) if phase is None else phase
        drift = 3.0 * f["supply_sensor_drift"]
        target = si["supply_setpoint_c"] + drift            # the controller holds the (drifted) sensor on its setpoint
        r = 0.08 + 0.32 * f["recirculation"]
        bf = 0.08 + 0.24 * f["bypass_air"]
        dt_it = si["it_dt_k"]
        m_it = q_it / (k["cp"] * dt_it)
        m_c = (1 - r) * m_it / (1 - bf)
        ca = m_c * k["cp"]

        def at(fw):
            ts = target
            for _ in range(3):
                v = m_c / (k["rc"] / (ts + 273.15)) * 3600
                ts = self.supply_for(q_it, m_c, v, fw, tchws)
            return ts, v
        lo, hi = 0.2, k["fmax"]
        if at(hi)[0] > target:
            fw = hi
        else:
            for _ in range(50):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if at(mid)[0] > target else (lo, mid)
            fw = (lo + hi) / 2
        hunt = f["valve_hunting"]
        fw = min(k["fmax"], fw * (1 + 0.35 * hunt * math.sin(phase)))
        ts, v = at(fw)
        t_out = ts + dt_it / (1 - r)
        t_in = ts + r * dt_it / (1 - r)
        t_ret = bf * ts + (1 - bf) * t_out
        # fans
        x = v / k["v"]
        dpf_clean = k["dpf"] * x ** k["ef"]
        dpf = dpf_clean * (1 + 2.0 * f["filter_loading"])
        extra = dpf - dpf_clean
        power = (k["p"] * x ** 3 + v / 3600 * extra / (k["eta"] * 1000)) * (1 + 0.4 * f["fan_degradation"])
        speed = self.fa["speed_at_rated_pct"] * x * math.sqrt(1 + extra / (k["dpt"] * x * x)) * (1 + 0.12 * f["fan_degradation"])
        # humidity
        dp_true = self.si["dewpoint_target_c"] + 7.5 * f["humidity_sensor_drift"]
        return dict(q=q_it, ts=ts, ts_read=ts - drift, sp=si["supply_setpoint_c"], t_in=t_in, t_out=t_out, t_ret=t_ret,
                    v=v, fw=fw, tchws=tchws, tchwr=tchws + q_it / (fw * k["rw"] / 3600 * k["cw"]),
                    valve=100 * fw / k["fmax"], dpf=dpf, power=power, speed=min(100.0, speed), dp=dp_true,
                    rh_off=18.0 * f["humidity_sensor_drift"], hum=8.0 + 92.0 * f["humidity_sensor_drift"],
                    rev=4.0 + 80.0 * hunt, bf=bf, r=r,
                    floor=si["underfloor_setpoint_pa"] - 9.0 * f["recirculation"])

    # one published message ------------------------------------------------------------------------------------------
    def measure(self, s=None):
        s = s or self.true_state()
        n, k = self.n, self.k
        rh_ret = tc.rh_from_dp(k, s["t_ret"], s["dp"]) - s["rh_off"]
        rh_in = tc.rh_from_dp(k, s["t_in"], s["dp"])
        return {
            "return_air_c": round(s["t_ret"] + n(0.08), 2), "return_rh_pct": round(max(5.0, rh_ret + n(0.4)), 1),
            "supply_air_c": round(s["ts_read"] + n(0.08), 2),
            "rack_inlet_c": round(s["t_in"] + n(0.1), 2), "rack_inlet_rh_pct": round(rh_in + n(0.4), 1),
            "rack_outlet_c": round(s["t_out"] + n(0.15), 2),
            "chw_supply_c": round(s["tchws"] + n(0.05), 2), "chw_return_c": round(s["tchwr"] + n(0.05), 2),
            "chw_flow_m3h": round(s["fw"] * (1 + n(0.008)), 3), "valve_pos_pct": round(min(100.0, s["valve"] + n(0.3)), 1),
            "valve_reversals_h": max(0, int(round(s["rev"] + n(1.5)))),
            "fan_speed_pct": round(s["speed"] + n(0.2), 1), "airflow_m3h": round(s["v"] * (1 + n(0.006)), 0),
            "fan_power_kw": round(s["power"] * (1 + n(0.01)), 3), "filter_dp_pa": round(s["dpf"] * (1 + n(0.02)), 1),
            "humidifier_pct": round(s["hum"], 1), "supply_setpoint_c": s["sp"],
            "underfloor_pa": round(s["floor"] + n(0.4), 1), "unit_on": 1,
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

    The IT load on the unit swings a few per cent over the day around its design value (more jobs in the afternoon), the
    chilled water supply wanders by a few tenths of a degree, and the valve oscillates when 'valve_hunting' is active.
    P.t is the visitor's local time in seconds; during the warm-up (dt >= 2 s) the clock is ignored so the page opens at a
    normal operating point.
    """

    def __init__(self, twin, seed=6301):
        self.twin = twin
        demo = twin["design"].get("demo", {})
        self.scale = float(demo.get("time_scale", 1))
        self.period = float(demo.get("hunting_period_s", 80))
        self.base = twin["design"]["site"]["it_load_kw"]
        self.u = Crah(twin, seed)
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        self.load = self.base

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
        day = 0.0 if dt >= 2.0 else math.sin(2 * math.pi * ((self.t % 86400) / 86400 - 0.375))
        self.load += (self.base * (1 + 0.04 * day) - self.load) * min(1.0, 0.05 * dt) + self.u.n(0.15) * min(1.0, dt)
        tchws = 10.0 + 0.2 * day + self.u.n(0.03)
        phase = 2 * math.pi * (self.t % self.period) / self.period
        return self.u.true_state(self.load, phase, tchws)

    def measure(self, true):
        return self.u.measure(true)
