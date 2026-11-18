"""Heat balance points and correction factors of the stand-in model, for the twin file (design.heat_balance).

    python tools/heat_balance.py
Prints HEAT_BALANCE and CORR to paste into build_twin.py. In a real twin these come from the OEM heat balance diagrams
and correction curves; here they come from the healthy stand-in at the rated steam conditions.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from physics import Turbine  # noqa: E402

TW = json.load(open(HERE / "twin" / "st-3201.twin.json", encoding="utf-8"))
r = TW["design"]["rated"]
t = Turbine(TW)
P0, T0, PC0 = r["main_press_bara"], r["main_temp_c"], r["cond_press_mbar"]
mw = lambda m, e, p=P0, tt=T0, pc=PC0: t.true_state(m, e, p, tt, pc)["mw"]
pts = [[m, e, round(mw(m, e), 4)] for m in (140.0, 170.0, 200.0, 215.0) for e in (20.0, 50.0, 80.0)]
corr = {"mw_per_bar_main": round((mw(200, 50, P0 + 2) - mw(200, 50, P0 - 2)) / 4, 4),
        "mw_per_k_main": round((mw(200, 50, P0, T0 + 5) - mw(200, 50, P0, T0 - 5)) / 10, 4),
        "mw_per_mbar_cond": round((mw(200, 50, P0, T0, PC0 + 2) - mw(200, 50, P0, T0, PC0 - 2)) / 4, 5),
        "cond_exponent": round((TW["design"]["lp_section"]["k_isentropic"] - 1) / TW["design"]["lp_section"]["k_isentropic"], 4)}
print("HEAT_BALANCE =", json.dumps(pts))
print("CORR =", json.dumps(corr))
