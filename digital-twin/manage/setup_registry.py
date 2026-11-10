"""Maximo Digital Twin: twin registry in Manage, the standard Maximo way (no database configuration).

  1. asset specification attributes  TWINURL, TWINDEVTYPE, TWINDEVICE, TWINMODEL, TWINVERSION
  2. classification DIGITALTWIN (use with ASSET) carrying those attributes
  3. the twinned assets, classified DIGITALTWIN with their attribute values

    python setup_registry.py            # create what is missing, update attribute values
Re-runnable. Data only, through the standard object structures MXAPIASSETATTRIBUTE, MXAPICLASSSTRUCTURE, MXAPIASSET.
"""
import json
from pathlib import Path

import maximo

ORG = "EAGLENA"
ATTRS = [  # id, description
    ("TWINURL", "Digital twin: live twin service URL"),
    ("TWINDEVTYPE", "Digital twin: Maximo Monitor device type"),
    ("TWINDEVICE", "Digital twin: Maximo Monitor device id"),
    ("TWINMODEL", "Digital twin: manufacturer and model of the twinned asset"),
    ("TWINVERSION", "Digital twin: twin definition version"),
]
CLASS_ID = "DIGITALTWIN"
TWINS = json.loads((Path(__file__).parent / "twins.json").read_text(encoding="utf-8"))


def ensure_attributes():
    have = {a["assetattrid"] for a in maximo.find("mxapiassetattribute", 'assetattrid="TWIN%"', "assetattrid")}
    for aid, desc in ATTRS:
        if aid in have:
            print(f"attribute {aid}: exists")
            continue
        code, r = maximo.call("POST", "/os/mxapiassetattribute?lean=1",
                              {"assetattrid": aid, "description": desc, "datatype": "ALN", "orgid": ORG})
        print(f"attribute {aid}: HTTP {code} {'' if code < 300 else r}")


def ensure_class():
    found = maximo.find("mxapiclassstructure", f'classificationid="{CLASS_ID}"', "classstructureid,classificationid")
    if found:
        print(f"classification {CLASS_ID}: exists ({found[0]['classstructureid']})")
        return found[0]["classstructureid"]
    body = {"classificationid": CLASS_ID, "hierarchypath": CLASS_ID,       # top-level class (BMXAA5592E without it)
            "description": "Digital twin (Maximo Digital Twin)", "orgid": ORG,
            "classusewith": [{"objectname": "ASSET", "objectvalue": "ASSET", "topLevel": True}],
            "classspec": [{"assetattrid": aid, "orgid": ORG,
                           "classspecusewith": [{"objectname": "ASSET", "objectvalue": "ASSET", "sequence": i + 1,
                                                 "useinspec": True}]} for i, (aid, _) in enumerate(ATTRS)]}
    code, r = maximo.call("POST", "/os/mxapiclassstructure?lean=1", body,
                          {"properties": "classstructureid,classificationid"})
    print(f"classification {CLASS_ID}: HTTP {code} {r if code >= 300 else r.get('classstructureid')}")
    return r.get("classstructureid")


def ensure_assets(csid):
    for t in TWINS:
        spec = [{"assetattrid": aid, "alnvalue": t[k]} for aid, k in
                [("TWINURL", "url"), ("TWINDEVTYPE", "devtype"), ("TWINDEVICE", "device"),
                 ("TWINMODEL", "model"), ("TWINVERSION", "version")]]
        found = maximo.find("mxapiasset", f'assetnum="{t["assetnum"]}" and siteid="{t["siteid"]}"',
                            "assetnum,href,assetspec{assetspecid,assetattrid,alnvalue}")
        body = {"assetnum": t["assetnum"], "siteid": t["siteid"], "description": t["description"],
                "classstructureid": csid, "assetspec": spec}
        if found:
            have = {s["assetattrid"]: s for s in found[0].get("assetspec", [])}
            if all(have.get(s["assetattrid"], {}).get("alnvalue") == s["alnvalue"] for s in spec):
                print(f"asset {t['assetnum']}: up to date")
                continue
            for s in spec:                       # existing spec rows are updated by their key (BMXAA1339E otherwise)
                if s["assetattrid"] in have:
                    s["assetspecid"] = have[s["assetattrid"]]["assetspecid"]
            href = found[0]["href"].split("/maximo/api")[-1]
            code, r = maximo.call("POST", href + "?lean=1", body,
                                  {"x-method-override": "PATCH", "patchtype": "MERGE"})
            print(f"asset {t['assetnum']}: updated HTTP {code} {'' if code < 300 else r}")
        else:
            code, r = maximo.call("POST", "/os/mxapiasset?lean=1", body)
            print(f"asset {t['assetnum']}: created HTTP {code} {'' if code < 300 else r}")


if __name__ == "__main__":
    ensure_attributes()
    csid = ensure_class()
    if csid:
        ensure_assets(csid)
