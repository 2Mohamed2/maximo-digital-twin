"""Physics model of BAT-1001 (110 V substation DC system, EnerSys PowerSafe OPzV 6 OPzV 420 x 54): the stand-in for the real battery.

Per step (dt real seconds; the plant clock runs `time_scale` times faster, see the twin file design.demo):
  room      battery room held near 23 C by its air conditioning (+-1.5 K day swing); ventilation_failure lets it
            drift towards 40 C
  load      standing DC load ~12 A (protection relays, control, RTU, telecom) with small daily variation
  charger   6-pulse thyristor charger in float mode, temperature compensated to the EnerSys table at the battery
            temperature, current limit 50 A; each plant night 02:00-03:30 its AC supply is lost (mains dip test) and
            the battery carries the load, then recharges (constant voltage, current tapering with the Ah deficit)
  cells     54 cells in series, each with its own ohmic value (0.51 mOhm +-4 %, -0.6 %/K), capacity and a small float
            voltage offset; the string voltage is shared; on discharge cell voltage = OCV(SOC) - I Ri
  float     float current 0.35 mA/Ah x 465 Ah at 2.25 Vpc and 20 C, x2 per 10 K and per +25 mV/cell; in a VRLA cell
            the float power becomes heat (recombination), which is what drives thermal runaway
  thermal   battery temperature follows the room through a first-order lag (time constant shortened for the demo)
            plus float, ripple and I2R heating
  earth     insulation monitor: balanced bridge (100 kOhm each pole) plus the leakage of the cabling
  faults    weak_cell (cell 17), loose_connection (strap 27-28), thermal_runaway, charger_ripple, ground_fault,
            float_setting, ventilation_failure, capacity_fade
"""
import math
import random

import numpy as np

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


WEAK, STRAP = 16, 26          # cell 17 (index 16) is the weak cell; strap between cells 27 and 28 (index 26)
OUTAGE = (2.0, 3.5)           # plant hours of the nightly charger AC loss
C_TH = 4.0e5                  # J/K, battery thermal capacity (shortened for the demo; real string ~1.8e6 J/K)
R_TH = 0.025                  # K/W, battery to room
RB = 100.0                    # kOhm, insulation monitor bridge per pole


class Plant:
    def __init__(self, twin, seed=1001):
        self.twin, self.rng = twin, random.Random(seed)
        self.d = twin["design"]
        self.k = tc._k(twin)
        self.n = self.d["string"]["cells"]
        self.scale = float(self.d.get("demo", {}).get("time_scale", 1))
        self.faults = {k: Fault() for k in twin["failure_modes"] if not k.startswith("$")}
        self.t = 0.0
        self.running, self.trip = True, 0
        g = random.Random(seed + 7)
        self.ri0 = [self.k["ri"] * (1 + g.uniform(-0.04, 0.04)) for _ in range(self.n)]
        self.voff = [g.uniform(-0.007, 0.007) for _ in range(self.n)]     # fraction of the mean float voltage
        self.cap0 = [g.uniform(0.98, 1.03) for _ in range(self.n)]
        self.room = 23.0
        self.tbat = 23.4
        self.tconn = 23.4
        self.deficit = 0.0               # Ah removed since the last full charge
        self.load_bias = 0.0
        self.lastv = 121.5

    def set_fault(self, name, severity, ramp_s):
        self.faults[name].set(severity, ramp_s)

    def clear_faults(self, ramp_s=5):
        for f in self.faults.values():
            f.set(0.0, ramp_s)

    def reset(self):
        self.trip, self.running = 0, True

    def fault_state(self):
        return {k: round(v.sev, 3) for k, v in self.faults.items()}

    # ---------------------------------------------------------------- helpers
    def vf(self, T):
        return float(np.interp(T, self.k["ft"], self.k["fv"]))

    @staticmethod
    def ocv(soc):
        return 2.13 - 0.16 * (1 - max(0.0, min(1.0, soc)))

    # ---------------------------------------------------------------- step
    def step(self, dt=1.0):
        f, d, k, n = self.faults, self.d, self.k, self.n
        for x in f.values():
            x.step(dt)
        pdt = dt * self.scale
        self.t += pdt
        h = (self.t / 3600.0) % 24
        # room: air conditioning, or drifting hot when it fails
        vent = f["ventilation_failure"].sev
        room_target = 23.0 + 1.5 * math.sin((h - 10.0) / 24 * 2 * math.pi) + 17.0 * vent
        self.room += (room_target - self.room) * (1 - math.exp(-pdt / 2400.0))
        # load
        self.load_bias = 0.998 * self.load_bias + self.rng.gauss(0, 0.01)
        load = 12.0 + 0.8 * math.sin((h - 8) / 24 * 2 * math.pi) + self.load_bias
        ac = 0 if OUTAGE[0] <= h < OUTAGE[1] else 1
        mode = 0 if ac else 2
        # cell parameters
        T = self.tbat
        fade = f["capacity_fade"].sev
        weak = f["weak_cell"].sev
        ri = [self.ri0[i] * (1 + k["tc"] * (T - 20)) * (1 + 0.45 * fade) * (1 + 1.6 * weak if i == WEAK else 1) for i in range(n)]
        cap = [self.cap0[i] * (1 - 0.30 * fade) * (1 - 0.40 * weak if i == WEAK else 1) for i in range(n)]
        conn = [0.05 * (1 + 80 * f["loose_connection"].sev if i == STRAP else 1) for i in range(n - 1)]
        c10 = k["c10"]
        # charger set point: temperature compensated, or a fixed high float when mis-set
        fs = f["float_setting"].sev
        vset_pc = (1 - fs) * self.vf(T) + fs * 2.33
        # float current (VRLA): Ah-based, temperature and overvoltage driven; runaway multiplies it
        run = f["thermal_runaway"].sev
        i_float = k["kf"] * c10 * 2 ** ((T - 20) / k["dk"]) * 2 ** ((vset_pc - 2.25) / k["dmv"])
        i_float *= (1 + 0.6 * weak) * (1 + 90 * run)
        i_float = min(i_float, 60.0)
        if ac:
            i_chg_need = 0.3 * self.deficit + i_float                    # CV recharge taper + float
            i_bat = min(i_chg_need, 50.0 - load)                        # charger current limit 50 A
            self.deficit = max(0.0, self.deficit - max(0.0, i_bat - i_float) * pdt / 3600)
            vpc_mean = vset_pc if i_bat < 50.0 - load - 1e-6 else vset_pc - 0.02
            soc_cells = [1 - self.deficit / (c10 * cap[i]) for i in range(n)]
            cells = [vpc_mean * (1 + self.voff[i]) for i in range(n)]
            if weak > 0:                                              # a dried-out cell floats high, the rest share less
                cells[WEAK] = vpc_mean * (1 + self.voff[WEAK] + 0.065 * weak)
            s = sum(cells)
            cells = [c * vpc_mean * n / s for c in cells]
            vstr = vpc_mean * n
            vbus = vstr
        else:
            i_bat = -load
            self.deficit += load * pdt / 3600
            soc_cells = [1 - self.deficit / (c10 * cap[i]) for i in range(n)]
            cells = [self.ocv(soc_cells[i]) + i_bat * ri[i] / 1000 + 0.3 * self.voff[i] * 2.0 for i in range(n)]
            vstr = sum(cells) + i_bat * sum(conn) / 1000
            vbus = vstr - 0.05
        soc = max(0.0, min(1.0, 1 - self.deficit / (c10 * float(np.mean(cap)) )))
        # ripple (charger running only)
        rip_a = (3.0 + 30.0 * f["charger_ripple"].sev) if ac else 0.0
        rip_mv = rip_a * (sum(ri) + sum(conn) + 2.0) if ac else 0.0      # string + cable impedance (mOhm) -> mV
        # thermal: float power is heat in VRLA (recombination), plus ripple and I2R
        p_heat = max(i_bat, 0) * vstr * (1.0 if self.deficit < 0.5 else 0.15) + rip_a ** 2 * sum(ri) / 1000 + i_bat ** 2 * sum(ri) / 1000
        self.tbat += ((self.room + p_heat * R_TH) - self.tbat) * (1 - math.exp(-pdt / (C_TH * R_TH)))
        self.tbat = min(self.tbat, 75.0)
        p_conn = i_bat ** 2 * conn[STRAP] / 1000
        self.tconn += ((self.tbat + 6.0 * p_conn) - self.tconn) * (1 - math.exp(-pdt / 600.0))
        # earth: balanced bridge + leakage on the positive pole
        gf = f["ground_fault"].sev
        rleak = 1e6 if gf < 1e-3 else 15.0 / max(gf, 1e-3) ** 1.5      # kOhm
        rp = 1 / (1 / RB + 1 / rleak)
        pos = vbus * rp / (rp + RB)
        neg = pos - vbus
        ins = 1 / (1 / 1500.0 + 1 / rleak)
        cell_t = [T + (0.6 * weak if i == WEAK else 0.0) for i in range(n)]
        dev = [abs(c - float(np.mean(cells))) for c in cells]
        worst = int(np.argmax(dev))
        rmax = int(np.argmax(ri))
        self.cells_v, self.cells_ri = cells, ri
        return {"dc_bus_voltage_v": vbus, "battery_voltage_v": vstr, "battery_current_a": i_bat, "load_current_a": load,
                "charger_current_a": (load + i_bat) if ac else 0.0, "charger_ac_on": ac, "charger_mode": mode,
                "ripple_current_a": rip_a, "ripple_voltage_mv": rip_mv, "room_temp_c": self.room, "battery_temp_c": T,
                "cell_temp_max_c": max(max(cell_t), self.tconn), "cell_v_mean": float(np.mean(cells)), "cell_v_min": min(cells),
                "cell_v_max": max(cells), "cell_v_worst_no": worst + 1, "ri_mean_mohm": float(np.mean(ri)), "ri_max_mohm": ri[rmax],
                "ri_max_no": rmax + 1, "conn_r_max_mohm": max(conn), "conn_temp_max_c": self.tconn, "soc_pct": soc * 100,
                "insulation_kohm": ins, "pos_earth_v": pos, "neg_earth_v": neg}

    def measure(self, true):
        out = {}
        for p in self.twin["telemetry"]["points"]:
            k = p["metric"]
            v = true[k]
            if p["noise"]:
                v = v + self.rng.gauss(0, p["noise"])
            lo, hi = p["range"]
            v = max(lo, min(hi, v))
            out[k] = int(v) if k in ("charger_ac_on", "charger_mode", "cell_v_worst_no", "ri_max_no") else round(v, 4 if abs(v) < 10 else 2)
        # per-cell detail of the battery monitoring system (for the viewer; not part of the MQTT payload)
        out["cells_v"] = [round(v, 4) for v in getattr(self, "cells_v", [])]
        out["cells_ri"] = [round(v, 4) for v in getattr(self, "cells_ri", [])]
        return out
