"""Maximo Monitor configuration for any Maximo Digital Twin asset, generated from its twin file. Re-runnable.

    python twin_monitor.py CH-201 --key-file ~/.mas-control-room/monitor-api-key.properties \
        --api https://<monitor-api-host> [--step type|device|functions|alerts|dashboard|all]

The asset is looked up in ../manage/twins.json (twin folder, live twin URL, device type). From the twin folder:
  twin/*.twin.json   telemetry points -> device type metrics (jsonPath "d." + point path), identification -> dimensions
  twin_calc.py       monitor_expressions() -> PythonExpression functions, alert_rules() -> AlertExpression rules
  presentation       -> the device type dashboard (live 3D twin card, performance card, KPI and trend cards)
The device token is written once, outside git, to ~/.mas-control-room/<slug>-device-<cluster>.json.
"""
import argparse
import importlib.util
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
import uuid as _uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REG = json.loads((Path(__file__).resolve().parents[1] / "manage" / "twins.json").read_text(encoding="utf-8"))
CTX = ssl._create_unverified_context()          # the cluster's router certificate (demo)
SCHEDULE = {"starting_at": "00:00:00", "every": "5T"}


class Monitor:
    def __init__(self, api, props):
        self.base = api.rstrip("/")
        self.h = {"x-api-key": props["key"], "x-api-token": props["token"], "tenantId": props["tenant"],
                  "mam_user_email": "maxadmin@ibm.com", "Content-Type": "application/json", "Accept": "application/json"}

    def call(self, method, path, body=None, ok_fail=False):
        r = urllib.request.Request(self.base + path, method=method, headers=self.h,
                                   data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(r, context=CTX, timeout=120) as f:
                t = f.read()
                try:
                    return json.loads(t) if t else {}
                except ValueError:          # some endpoints (DELETE) answer with plain text
                    return {"text": t.decode(errors="replace")[:200]}
        except urllib.error.HTTPError as e:
            msg = f"{method} {path}: HTTP {e.code} {e.read()[:500]!r}"
            if ok_fail:
                return {"error": msg}
            raise SystemExit(msg)


def items(x):
    if isinstance(x, list):
        return x
    for k in ("results", "data", "items", "content", "deviceTypes", "devices"):
        if isinstance(x, dict) and isinstance(x.get(k), list):
            return x[k]
    return []


class Twin:
    def __init__(self, assetnum):
        self.reg = next((r for r in REG if r["assetnum"] == assetnum), None)
        if not self.reg:
            raise SystemExit(f"{assetnum} is not in manage/twins.json")
        self.dir = ROOT / self.reg["dir"]
        self.doc = json.load(open(next((self.dir / "twin").glob("*.twin.json")), encoding="utf-8"))
        spec = importlib.util.spec_from_file_location(f"twin_calc_{self.reg['dir'].replace('-', '_')}", self.dir / "twin_calc.py")
        self.calc = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(self.dir))
        spec.loader.exec_module(self.calc)
        self.dtype = self.reg["devtype"]
        self.url = self.reg["url"].rstrip("/")
        self.slug = self.reg["dir"]
        self.calc_names = {n for n, _ in self.calc.monitor_expressions(self.doc)}

    def dims(self):
        i, t = self.doc["identification"], self.doc["twin"]
        d = {"ASSETNUM": i["assetnum"], "MANUFACTURER": i.get("manufacturer", ""), "MODEL": i.get("model", "")[:250],
             "SITE": i.get("site", ""), "LOCATION": i.get("location", ""), "MEDIUM": i.get("medium", "")[:250],
             "TWIN_ID": t["id"], "TWIN_VERSION": t["version"],
             "TWIN_URL": f"{self.url}/?embed=1&device={i['assetnum']}", "CURVES_URL": f"{self.url}/curves?embed=1"}
        for row in self.doc.get("presentation", {}).get("design", []):
            k = "DESIGN_" + "".join(c if c.isalnum() else "_" for c in row["label"].upper()).strip("_")
            d[k[:30]] = row["value"][:250]
        return d


def find_type(m, name):
    return {t["name"]: t for t in items(m.call("POST", "/api/v2/core/deviceTypes/search", {"pageSize": 200, "pageNumber": 0}))}.get(name)


def step_type(m, tw):
    t = find_type(m, tw.dtype)
    if t:
        print(f"{tw.dtype} exists ({t['uuid']})")
        return t["uuid"]
    ev = tw.doc["telemetry"]["event"]
    metrics = [{"name": p["metric"].upper(), "type": "METRIC", "columnType": "NUMBER", "eventName": ev,
                "jsonPath": "d." + p["path"], "displayName": f"{p['label']} ({p['unit']})"[:60]}
               for p in tw.doc["telemetry"]["points"]]
    t = m.call("POST", "/api/v2/core/deviceTypes", {
        "name": tw.dtype, "description": f"{tw.doc['twin']['kind']} digital twin ({tw.doc['twin']['id']} v{tw.doc['twin']['version']})"[:250],
        "dataItemDto": metrics})
    m.call("POST", f"/api/v2/core/deviceTypes/{t['uuid']}/dimensions", [{"name": k, "columnType": "LITERAL"} for k in tw.dims()])
    print(f"created {tw.dtype} ({t['uuid']}) with {len(metrics)} metrics")
    return t["uuid"]


def step_device(m, tw, uuid, api, props):
    did = tw.doc["identification"]["assetnum"]
    cluster = api.split("instdb2-")[-1].split(".")[0] if "instdb2-" in api else "cluster"
    dev_file = Path(os.path.expanduser(f"~/.mas-control-room/{tw.slug}-device-{cluster}.json"))
    have = {d.get("deviceId") or d.get("name") for d in items(m.call("GET", f"/api/v2/core/deviceTypes/{uuid}/devices"))}
    if did not in have:
        out = items(m.call("POST", f"/api/v2/deviceTypes/{uuid}/devices", [{"name": did, "alias": did}]))
        tok = next((d.get("authToken") for d in out if d.get("name") == did), None)
        if not tok:
            raise SystemExit(f"no token returned: {out}")
        host = api.replace("https://", "").replace(".api.monitor.", ".messaging.iot.").split("/")[0]
        dev_file.write_text(json.dumps({"host": host, "tenant": props["tenant"], "type": tw.dtype, "type_uuid": uuid,
                                        "id": did, "token": tok, "event": tw.doc["telemetry"]["event"]}, indent=1),
                            encoding="utf-8")
        print(f"registered {did}; token written to {dev_file}")
    else:
        print(f"{did} exists" + ("" if dev_file.is_file() else f" (WARNING: no token file {dev_file})"))
    have_dims = {d.get("name") for d in items(m.call("GET", f"/api/v2/core/deviceTypes/{uuid}/dimensions", ok_fail=True))}
    new = [k for k in tw.dims() if k not in have_dims]
    if new and have_dims:
        m.call("POST", f"/api/v2/core/deviceTypes/{uuid}/dimensions", [{"name": k, "columnType": "LITERAL"} for k in new], ok_fail=True)
    rows = [{"id": did, "name": k, "type": "LITERAL", "value": v} for k, v in tw.dims().items()]
    for i in range(0, len(rows), 20):
        m.call("POST", f"/api/v2/core/deviceTypes/{uuid}/devices/dimensions", rows[i:i + 20])
    print(f"dimensions set ({len(rows)})")


REPLACE = False


def ensure_fn(m, uuid, out, body):
    have = items(m.call("GET", f"/api/v2/core/deviceTypes/{uuid}/kpiFunctions"))
    old = [k for k in have if out in (k.get("output") or {}).values()]
    if old and not REPLACE:
        return "exists"
    for k in old:
        if (k.get("input") or {}) == body["input"]:
            return "unchanged"
        r = m.call("DELETE", f"/api/v2/core/deviceTypes/{uuid}/kpiFunctions/{k['name']}", ok_fail=True)
        if "error" in r:
            return "delete failed: " + r["error"][:200]
    r = m.call("POST", f"/api/v2/core/deviceTypes/{uuid}/kpiFunctions",
               {**body, "enabled": True, "schedule": SCHEDULE, "backtrack": {}, "outputMeta": {out: {"transient": False}}},
               ok_fail=True)
    return r["error"][:400] if "error" in r else "created"


def step_functions(m, tw, uuid):
    who = tw.doc["identification"]["assetnum"]
    for out, expr in tw.calc.monitor_expressions(tw.doc):
        print(out, ensure_fn(m, uuid, out, {"catalogFunctionName": "PythonExpression",
                                            "description": f"{who} twin: {out.lower()} from manufacturer data",
                                            "input": {"expression": expr}, "output": {"output_name": out}}))


def step_alerts(m, tw, uuid):
    for name, expr, sev, fm in tw.calc.alert_rules(tw.doc):
        label = tw.doc["failure_modes"][fm]["label"] if fm else "condition limit"
        print(name, ensure_fn(m, uuid, name, {"catalogFunctionName": "AlertExpression",
                                              "description": f"{tw.doc['identification']['assetnum']} twin: {label}",
                                              "input": {"expression": expr, "Severity": sev, "Status": "New"},
                                              "output": {"alert_name": name}}))


# ---------------------------------------------------------------- dashboard
_NS = _uuid.UUID("6a1d3c55-2b0f-4f7e-9d1e-3a8c5b2f7e10")


def _id(k):
    return str(_uuid.uuid5(_NS, k))


def dashboard(tw):
    ev, calc, an = tw.doc["telemetry"]["event"], tw.calc_names, tw.doc["identification"]["assetnum"]
    pres = tw.doc["presentation"]

    def attr(mtr, agg):
        x = {"id": f"{mtr}_{agg}", "attribute": mtr, "aggregator": agg}
        if mtr not in calc:
            x["eventName"] = ev
        return x

    def known(mtr):
        if not mtr:                      # comparison rows with only an expected (or only a measured) value
            return False
        return mtr.upper() in calc or any(p["metric"] == mtr for p in tw.doc["telemetry"]["points"])

    def value(k, title, its):
        its = [x for x in its if known(x[0])]
        return {"id": _id(an + k), "title": title, "size": "MEDIUM", "type": "VALUE", "timeRange": "lastHour",
                "content": {"attributes": [{"dataSourceId": f"{x[0].upper()}_last", "label": x[1], "unit": x[2].replace("degC", "°C"),
                                            "precision": x[3]} for x in its]},
                "dataSource": {"range": {"interval": "hour", "count": -1, "type": "rolling"},
                               "attributes": [attr(x[0].upper(), "last") for x in its]}}

    def trend(k, title, series, ylabel):
        series = [s for s in series if known(s[0])]
        return {"id": _id(an + k), "title": title, "size": "LARGEWIDE", "type": "TIMESERIES", "timeRange": "last24Hours",
                "content": {"series": [{"dataSourceId": f"{s[0].upper()}_mean", "label": s[1]} for s in series],
                            "xLabel": "Time", "yLabel": ylabel, "includeZeroOnYaxis": False, "timeDataSourceId": "timestamp"},
                "dataSource": {"range": {"interval": "hour", "count": -24, "type": "rolling"}, "timeGrain": "hour",
                               "attributes": [attr(s[0].upper(), "mean") for s in series]}}

    model = tw.reg["model"]
    cards = [
        {"id": _id(an + "twin3d"), "title": f"{an} digital twin · {model} (live 3D)", "size": "XLARGE", "type": "THIRD_PARTY",
         "timeRange": "lastHour", "customContent": {"type": "DIMENSION", "value": "TWIN_URL"},
         "dataSource": {"range": {"interval": "hour", "count": -1, "type": "rolling"}, "groupBy": ["deviceid"],
                        "attributes": [{"id": "TWIN_URL", "attribute": "TWIN_URL", "dataItemId": "TWIN_URL"}]}},
        {"id": _id(an + "curves"), "title": f"{an} performance · manufacturer data vs. live operating point", "size": "XLARGE",
         "type": "THIRD_PARTY", "timeRange": "lastHour", "customContent": {"type": "URL", "value": f"{tw.url}/curves?embed=1"},
         "dataSource": {"range": {"interval": "hour", "count": -1, "type": "rolling"}}},
        value("now", "Operating point (latest)", [(k["metric"], k["label"], k["unit"], k["decimals"]) for k in pres["kpis"]]),
        value("twin", "Twin: expected vs. measured (latest)",
              [(c["expected"], "Expected " + c["label"].lower(), c["unit"], c["decimals"]) for c in pres["compare"] if c.get("expected")][:4]),
        value("tk", "Twin indicators (latest)", [(k["metric"], k["label"], k["unit"], k["decimals"]) for k in pres["twin_kpis"]]),
    ]
    for c in pres["compare"]:
        if c.get("expected") and known(c["measured"]) and known(c["expected"]):
            cards.append(trend("cmp" + c["measured"], f"{c['label']}: measured vs. expected ({c.get('basis', 'twin')})"[:120],
                               [(c["measured"], "Measured"), (c["expected"], "Expected (twin)")], c["unit"] or c["label"]))
        if len(cards) >= 8:
            break
    cards.append(trend("res", "Twin residuals and condition indicators", [(t["metric"], t["label"]) for t in pres["trends"]], "value"))
    return {"title": "Digital twin", "cards": cards}


def step_dashboard(m, tw, uuid):
    title = f"{tw.doc['identification']['assetnum']} digital twin"
    path = f"/api/v2/core/deviceTypes/{uuid}/dashboards"
    have = next((d for d in items(m.call("GET", path)) if d.get("name") == title), None)
    body = {"name": title, "type": "DEVICE_TYPE", "isEnabled": True, "sequenceNumber": 1, "dashboardMetadataJson": dashboard(tw)}
    if have:
        body["dashboardMetaId"] = have["dashboardMetaId"]
        m.call("PUT", f"{path}/{have['dashboardMetaId']}", body)
    else:
        have = m.call("POST", path, body)
    did = have.get("dashboardMetaId")
    print(f"dashboard {did}: {m.base.replace('.api.monitor.', '.monitor.')}/dashboard/{tw.dtype}/dashboards/{did}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("assetnum")
    ap.add_argument("--key-file", required=True)
    ap.add_argument("--api", required=True)
    ap.add_argument("--step", default="all", choices=["type", "device", "functions", "alerts", "dashboard", "all"])
    ap.add_argument("--replace", action="store_true", help="replace functions/rules whose expression changed")
    a = ap.parse_args()
    global REPLACE
    REPLACE = a.replace
    props = dict(l.split("=", 1) for l in open(os.path.expanduser(a.key_file), encoding="utf-8").read().splitlines()
                 if "=" in l and not l.startswith("#"))
    tw = Twin(a.assetnum)
    m = Monitor(a.api, props)
    uuid = step_type(m, tw) if a.step in ("type", "all") else (find_type(m, tw.dtype) or {}).get("uuid")
    if not uuid:
        raise SystemExit(f"{tw.dtype} not found; run --step type first")
    if a.step in ("device", "all"):
        step_device(m, tw, uuid, a.api, props)
    if a.step in ("functions", "all"):
        step_functions(m, tw, uuid)
    if a.step in ("alerts", "all"):
        step_alerts(m, tw, uuid)
    if a.step in ("dashboard", "all"):
        step_dashboard(m, tw, uuid)


if __name__ == "__main__":
    main()
