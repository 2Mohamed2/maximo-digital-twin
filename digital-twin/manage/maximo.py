"""Small Maximo Manage REST client (API key) used by the Digital Twin setup scripts."""
import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request

CTX = ssl._create_unverified_context()      # cluster router certificate (demo)
BASE = os.environ.get("MAS_MANAGE", "https://wsp.manage.<your-mas-domain>/maximo/api")
KEY_NAME = os.environ.get("MAS_KEY_NAME", "<api-key-name>")


def _key():
    return json.load(open(os.path.expanduser("~/.mas-control-room/mcp.json"), encoding="utf-8"))["keys"][KEY_NAME]


def call(method, path, body=None, headers=None):
    h = {"apikey": _key(), "Accept": "application/json", "Content-Type": "application/json"}
    h.update(headers or {})
    r = urllib.request.Request(BASE + path, method=method, headers=h,
                               data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(r, context=CTX, timeout=120) as f:
            t = f.read()
            return f.status, (json.loads(t) if t else {})
    except urllib.error.HTTPError as e:
        t = e.read()
        try:
            return e.code, json.loads(t)
        except ValueError:
            return e.code, {"text": t.decode(errors="replace")[:500]}


def find(os_name, where, select="*"):
    q = urllib.parse.urlencode({"lean": 1, "oslc.select": select, "oslc.where": where, "oslc.pageSize": 100})
    code, r = call("GET", f"/os/{os_name}?{q}")
    return r.get("member", []) if code == 200 else []
