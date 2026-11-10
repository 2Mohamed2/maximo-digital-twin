"""Physics model of BLW-1301 (Aerzen AT 150-0.8 S-G5 turbo blower) aerating one activated-sludge basin through
Sanitaire Silver Series II membrane discs: the stand-in for the real plant.

Per step (dt real seconds; the plant clock runs `time_scale` times faster, see the twin file design.demo):
  influent  day profile of flow and ammonia to this aeration train; the true oxygen demand follows it (+/- a slow
            unmeasured drift of a few percent)
  control   DO PI on the control probe (setpoint 2.0 mg/L) -> airflow setpoint, limited to the blower turndown
  blower    VFD turbo: pressure rise dp = dp_shut n^2 - b Q^2; the speed n follows from the system pressure; when the
            system needs more than the blower can give at full speed, the flow drops to the intersection
  system    grid pressure = static submergence + diffuser DWP(q) + grid loss; discharge = grid + header loss (+ a
            throttled zone valve); inlet filter dp ~ Q^2
  oxygen    AOTR = Q x 0.2997 x SOTE(q) x alpha F x (beta Cs*(T) - C)/Cs*(20) x theta^(T-20); dC/dt = (AOTR - demand)/V
  motor     power = adiabatic power / wire-to-air efficiency; winding, VFD and bearing temperatures follow load
  faults    diffuser_fouling: DWP up, F down; membrane_tear: part of the air leaves as coarse bubbles, DWP down;
            inlet_filter: filter dp up; bearing_wear: vibration, bearing temperature, efficiency down;
            surge_approach: a zone valve sticks part-closed (header loss up, margin to surge down);
            do_probe_drift: the control probe reads high; vfd_overheating: VFD cooling fan failure
"""
import math
import random

import twin_calc as tc


class Fault:
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
    def __init__(self, twin, seed=1301):
        self.twin, self.rng = twin, random.Random(seed)
        self.d = twin["design"]
        self.k = tc._k(twin)
        self.scale = float(self.d.get("demo", {}).get("time_scale", 1))
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0                      # plant clock, seconds of day
        self.running, self.trip = True, 0
        self.C = 2.0                      # basin DO, mg/L
        self.Q = 3000.0                   # airflow, Nm3/h
        self.integ = 3000.0
        self.drift = 0.0
        self.T = {"motor": 85.0, "vfd": 42.0, "bearing": 62.0}
        self.hours = 21840.0

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.trip, self.running = 0, True

    def fault_state(self):
        return {k: round(v.sev, 3) for k, v in self.faults.items()}

    # ------------------------------------------------------------------ helpers
    def influent(self):
        h = (self.t / 3600.0) % 24
        p = self.d["process"]
        q = p["inflow_base_m3h"] + p["inflow_am_m3h"] * math.exp(-((h - 11) / 3.5) ** 2) + p["inflow_pm_m3h"] * math.exp(-((h - 20) / 2.5) ** 2)
        nh4 = p["nh4_base_mgl"] + p["nh4_peak_mgl"] * math.exp(-((h - 12.5) / 4.0) ** 2)
        return q, nh4

    def water_temp(self):
        h = (self.t / 3600.0) % 24
        return self.d["process"]["water_temp_c"] + 0.6 * math.sin((h - 9) / 24 * 2 * math.pi)

    def air_temp(self):
        h = (self.t / 3600.0) % 24
        return self.d["site"]["air_temp_mean_c"] + self.d["site"]["air_temp_swing_c"] * math.sin((h - 9) / 24 * 2 * math.pi)

    def system(self, Q):
        """Grid and discharge pressure (mbar g) for an airflow, with the fault effects."""
        k, f = self.k, self.faults
        q = Q / k["n"]
        dwp = (k["dwp0"] + k["dwp1"] * q) * (1 - 0.8 * f["membrane_tear"].sev) + 45 * f["diffuser_fouling"].sev
        grid = 98.0665 * k["Z"] + dwp + k["kgrid"] * (Q / k["qref"]) ** 2
        valve = 250 * f["surge_approach"].sev * (Q / 2400)
        dis = grid + k["kpipe"] * (Q / k["qref"]) ** 2 + valve
        return grid, dis

    def blower_dp(self, Q, n):
        b = self.d["blower"]
        return b["dp_shutoff_mbar"] * n * n - (b["dp_shutoff_mbar"] - b["pressure_max_mbar"]) * (Q / b["flow_max_nm3h"]) ** 2

    # ------------------------------------------------------------------ step
    def step(self, dt=1.0):
        f, d, k = self.faults, self.d, self.k
        for x in f.values():
            x.step(dt)
        pdt = dt * self.scale               # plant seconds
        self.t += pdt
        hrs = pdt / 3600.0
        qin, nh4 = self.influent()
        self.drift = 0.999 * self.drift + self.rng.gauss(0, 0.002)
        o2_true = qin * (k["cc"] + 4.57 * k["fn"] * nh4 / 1000) * (1 + max(-0.05, min(0.05, self.drift)))
        Tw = self.water_temp()
        Ta = self.air_temp()
        p_amb = d["site"]["ambient_pressure_mbar"]
        # control probe (drift reads high) and DO PI -> airflow setpoint
        do_ctrl_true = self.C + 0.15
        do_out_true = self.C - 0.25 - 0.7 * f["membrane_tear"].sev
        do_ctrl_meas = do_ctrl_true + 1.5 * f["do_probe_drift"].sev
        sp = d["control"]["do_setpoint_mgl"]
        err = sp - do_ctrl_meas
        b = d["blower"]
        qmin = b["flow_min_nm3h"]
        if self.running:
            self.integ = max(qmin, min(b["flow_max_nm3h"], self.integ + d["control"]["ki_nm3h_per_mgl_h"] * err * hrs))
            qsp = max(qmin, min(b["flow_max_nm3h"], self.integ + d["control"]["kp_nm3h_per_mgl"] * err))
        else:
            qsp = 0.0
        # blower: the flow the system lets it deliver at full speed at most
        if self.running:
            Q = qsp
            for _ in range(30):
                g, dis = self.system(Q)
                if self.blower_dp(Q, 1.0) >= dis:
                    break
                Q *= 0.97
            self.Q += (Q - self.Q) * min(1.0, dt / 2.0)
        else:
            self.Q += (0 - self.Q) * min(1.0, dt / 2.0)
        Q = max(self.Q, 0.0)
        grid, dis = self.system(max(Q, 1.0))
        if not self.running:
            grid, dis = 98.0665 * k["Z"] * 0.0, 0.0
        n = math.sqrt(max(0.0, (dis + (b["dp_shutoff_mbar"] - b["pressure_max_mbar"]) * (Q / b["flow_max_nm3h"]) ** 2) / b["dp_shutoff_mbar"])) if self.running else 0.0
        filt = b["filter_dp_clean_mbar"] * (Q / b["flow_max_nm3h"]) ** 2 * (1 + 12 * f["inlet_filter"].sev)
        # power

        pin = p_amb - filt
        pr = (pin + dis) / pin
        vin = max(Q, 1) * (1013.25 / pin) * ((Ta + 273.15) / 273.15) / 3600
        pad = 3.5 * pin * 100 * vin * (pr ** (0.4 / 1.4) - 1) / 1000
        eta = (k["eta0"] - k["eta_c"] * (Q / k["qmax"] - k["qbep"]) ** 2) * (1 - 0.10 * f["bearing_wear"].sev)
        power = pad / eta if self.running else 0.0
        # surge protection
        qs = k["qsref"] * math.sqrt(max(dis, 0) / k["dpsref"])
        if self.running and Q > 100 and (Q - qs) / Q < 0.0 and not self.trip:
            self.trip, self.running = 1, False
        # temperatures
        self.T["vfd"] += ((Ta + 10 + 0.12 * power + 34 * f["vfd_overheating"].sev) - self.T["vfd"]) * min(1, pdt / 1800)
        self.T["motor"] += ((Ta + 40 + 0.45 * power + 25 * f["vfd_overheating"].sev) - self.T["motor"]) * min(1, pdt / 2400)
        self.T["bearing"] += ((Ta + 30 + 18 * n + 32 * f["bearing_wear"].sev) - self.T["bearing"]) * min(1, pdt / 1800)
        if self.running and self.T["vfd"] > b["vfd_trip_c"] and not self.trip:
            self.trip, self.running = 2, False
        vib = (0.8 + 0.6 * n + 5.2 * f["bearing_wear"].sev) if self.running else 0.05
        # oxygen transfer
        q = max(Q, 1) / k["n"]
        sote_fine = k["sote_m"] * k["Z"] * (q / k["qd"]) ** (-k["sn"])
        fb = 0.4 * f["membrane_tear"].sev
        sote = (1 - fb) * sote_fine + fb * d["oxygen"]["sote_coarse_per_m"] * k["Z"]
        af = k["af"] * (1 - 0.3 * f["diffuser_fouling"].sev)
        cst = tc.cs_water(Tw) * p_amb / 1013.25 * (1 + k["deff"] * k["Z"] / 10.33)
        cs20 = tc.cs_water(20) * (1 + k["deff"] * k["Z"] / 10.33)
        aotr = Q * tc.O2_PER_NM3 * sote * af * max(k["beta"] * cst - self.C, 0) / cs20 * k["theta"] ** (Tw - 20)
        self.C = max(0.0, min(9.0, self.C + (aotr - o2_true) * 1000 / d["process"]["basin_volume_m3"] * hrs))
        dis_t = Ta + (Ta + 273.15) * (pr ** (0.4 / 1.4) - 1) / 0.80 if self.running else Ta + 3
        if self.running:
            self.hours += hrs
        return {"ambient_pressure_mbar": p_amb, "inlet_temp_c": Ta, "inlet_filter_dp_mbar": filt, "discharge_pressure_mbar": dis,
                "discharge_temp_c": dis_t, "airflow_nm3h": Q, "airflow_setpoint_nm3h": qsp, "grid_pressure_mbar": grid,
                "speed_pct": n * 100, "motor_power_kw": power, "motor_current_a": power * 1000 / (math.sqrt(3) * 400 * 0.95),
                "motor_temp_c": self.T["motor"], "vfd_temp_c": self.T["vfd"], "bearing_temp_c": self.T["bearing"],
                "vibration_mm_s": vib, "do_control_mgl": max(0.0, do_ctrl_meas), "do_outlet_mgl": max(0.0, do_out_true),
                "do_setpoint_mgl": sp, "water_temp_c": Tw, "influent_flow_m3h": qin, "influent_nh4_mgl": nh4,
                "run_hours": self.hours, "trip_code": self.trip}

    def measure(self, true):
        out = {}
        for p in self.twin["telemetry"]["points"]:
            k = p["metric"]
            v = true[k]
            if p["noise"]:
                v = v + self.rng.gauss(0, p["noise"])
            lo, hi = p["range"]
            v = max(lo, min(hi, v))
            out[k] = int(v) if k == "trip_code" else round(v, 4 if abs(v) < 10 else 2)
        return out
