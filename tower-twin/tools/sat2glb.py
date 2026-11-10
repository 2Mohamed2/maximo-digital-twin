"""Tessellate an ACIS text (.sat) solid into a GLB for the twin viewer, without changing the source file.

BAC publishes FXV 3D CAD as ACIS .sat (Autodesk Inventor export). Open-source CAD kernels do not read ACIS, so this
reads the B-rep directly: faces -> loops -> coedges -> edges (straight lines and ellipse arcs sampled), then
  plane faces            earcut in the plane (outer loop + holes)
  cylinder / cone / torus faces  two full-circle loops -> ring strip; otherwise unwrapped (angle, height) earcut
NURBS intersection curves (intcurve) are approximated by their end points. Units: the file's model units (inches
for BAC) are scaled to metres. Z is up in the file; the GLB is written Y-up for three.js.

    python -I sat2glb.py <in.sat> <out.glb>
"""
import math
import sys

import mapbox_earcut as earcut
import numpy as np
import trimesh


def parse(path):
    txt = open(path, encoding="latin1").read()
    lines = txt.split("\n")
    unit_mm = float(lines[2].split()[0])
    body = "\n".join(lines[3:])
    recs = [r.strip().split() for r in body.split("#")]
    return recs, unit_mm


def ref(tok):
    return int(tok[1:]) if tok.startswith("$") else -1


def vec(t, i):
    return np.array([float(t[i]), float(t[i + 1]), float(t[i + 2])])


class Sat:
    def __init__(self, path):
        self.r, self.unit_mm = parse(path)

    def point_of_vertex(self, v):
        return vec(self.r[ref(self.r[v][5])], 4)

    def edge_poly(self, e):
        t = self.r[e]
        v0, s0, v1, s1, cur, sense = ref(t[4]), float(t[5]), ref(t[6]), float(t[7]), ref(t[9]), t[10]
        p0, p1 = self.point_of_vertex(v0), self.point_of_vertex(v1)
        c = self.r[cur] if cur >= 0 else ["none"]
        if c[0] == "ellipse-curve":
            ctr, nrm, maj, ratio = vec(c, 4), vec(c, 7), vec(c, 10), float(c[13])
            nrm = nrm / np.linalg.norm(nrm)
            minor = np.cross(nrm, maj) * ratio
            n = max(2, int(abs(s1 - s0) / (2 * math.pi) * 48) + 1)
            out = []
            for s in np.linspace(s0, s1, n):
                u = s if sense == "forward" else -s
                out.append(ctr + math.cos(u) * maj + math.sin(u) * minor)
            out[0], out[-1] = p0, p1
            return out
        return [p0, p1]

    def loop_poly(self, lp):
        first = ref(self.r[lp][5])
        pts, ce, guard = [], first, 0
        while True:
            t = self.r[ce]
            poly = self.edge_poly(ref(t[7]))
            if t[8] == "reversed":
                poly = poly[::-1]
            pts.extend(poly[:-1])
            ce = ref(t[4])
            guard += 1
            if ce == first or ce < 0 or guard > 5000:
                break
        return np.array(pts)

    def faces(self):
        for i, t in enumerate(self.r):
            if t and t[0] == "face":
                loops, lp = [], ref(t[5])
                while lp >= 0:
                    loops.append(self.loop_poly(lp))
                    lp = ref(self.r[lp][4])
                yield self.r[ref(t[8])], t[9], loops


def frame(n):
    n = n / np.linalg.norm(n)
    a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(n, a)
    u /= np.linalg.norm(u)
    return u, np.cross(n, u), n


def area2(p):
    return 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])


def tri2d(loops2d, loops3d):
    """earcut: largest loop is the outer boundary, the others are holes."""
    loops2d = [l for l in loops2d if len(l) >= 3]
    loops3d = [l for l in loops3d if len(l) >= 3]
    if not loops2d:
        return None, None
    order = sorted(range(len(loops2d)), key=lambda k: -abs(area2(loops2d[k])))
    v2 = np.concatenate([loops2d[k] for k in order]).astype(np.float64)
    v3 = np.concatenate([loops3d[k] for k in order])
    rings = np.cumsum([len(loops2d[k]) for k in order]).astype(np.uint32)
    idx = earcut.triangulate_float64(v2, rings)
    return v3, np.array(idx, dtype=np.int64).reshape(-1, 3)


def ring(loop, ctr, axis, u, v, n=48):
    """resample a closed loop around an axis at n equal angles (for full-circle loops)."""
    d = loop - ctr
    ang = np.arctan2(d @ v, d @ u)
    o = np.argsort(ang)
    ang, pts = ang[o], loop[o]
    ang = np.concatenate([ang[-1:] - 2 * math.pi, ang, ang[:1] + 2 * math.pi])
    pts = np.concatenate([pts[-1:], pts, pts[:1]])
    g = np.linspace(-math.pi, math.pi, n, endpoint=False)
    return np.stack([np.interp(g, ang, pts[:, k]) for k in range(3)], axis=1)


def full_circle(loop, ctr, u, v):
    d = loop - ctr
    ang = np.unwrap(np.arctan2(d @ v, d @ u))
    return len(loop) > 8 and abs(ang[-1] - ang[0]) > 1.6 * math.pi


def tess_face(surf, sense, loops):
    kind = surf[0]
    if kind == "plane-surface":
        u, v, n = frame(vec(surf, 7))
        l2 = [np.stack([l @ u, l @ v], axis=1) for l in loops]
        V, F = tri2d(l2, loops)
        if V is None:
            return None
        if len(F) and np.dot(np.cross(V[F[0, 1]] - V[F[0, 0]], V[F[0, 2]] - V[F[0, 0]]), n) * (1 if sense == "forward" else -1) < 0:
            F = F[:, ::-1]
        return V, F
    if kind in ("cone-surface", "torus-surface"):
        ctr, axis = vec(surf, 4), vec(surf, 7)
        u, v, a = frame(axis)
        if len(loops) == 2 and all(full_circle(l, ctr, u, v) for l in loops):
            r0, r1 = ring(loops[0], ctr, a, u, v), ring(loops[1], ctr, a, u, v)
            n = len(r0)
            V = np.concatenate([r0, r1])
            F = []
            for i in range(n):
                j = (i + 1) % n
                F += [[i, j, n + i], [j, n + j, n + i]]
            return V, np.array(F)
        rad = float(surf[10]) if kind == "torus-surface" else max(np.linalg.norm(vec(surf, 10)), 1e-6)
        l2 = []
        for l in loops:
            d = l - ctr
            ang = np.unwrap(np.arctan2(d @ v, d @ u))
            h = d @ a if kind == "cone-surface" else (d @ a) + np.hypot(d @ u, d @ v)
            l2.append(np.stack([ang * rad, h], axis=1))
        return tri2d(l2, loops)
    # other surfaces (spline): fan from the outer loop
    V, F = tri2d([np.stack([l @ frame(np.cross(l[1] - l[0], l[2] - l[0]) + 1e-9)[0],
                            l @ frame(np.cross(l[1] - l[0], l[2] - l[0]) + 1e-9)[1]], axis=1) for l in loops if len(l) >= 3],
                 [l for l in loops if len(l) >= 3])
    return (V, F) if V is not None else None


FANS = [(-35.8125, -19.6875), (35.8125, -19.6875)]   # FXV fan axes (model units), from the fan cowl cylinders
FAN_R, FAN_Z = 30.2, (166.0, 183.0)                  # inside the cowl, between deck and cowl top


def part_of(V):
    """casing, or fan_1 / fan_2 when the whole face lies inside a fan cowl (blades, hub): the viewer spins them."""
    for k, (x, y) in enumerate(FANS):
        r = np.hypot(V[:, 0] - x, V[:, 1] - y)
        if r.max() < FAN_R and V[:, 2].min() > FAN_Z[0] and V[:, 2].max() < FAN_Z[1]:
            return f"fan_{k + 1}"
    return "casing"


def main(src, dst):
    s = Sat(src)
    parts, skipped = {}, 0
    for surf, sense, loops in s.faces():
        try:
            out = tess_face(surf, sense, loops)
        except Exception:
            out = None
        if out is None or out[1] is None or not len(out[1]):
            skipped += 1
            continue
        V, F = out
        Vs, Fs = parts.setdefault(part_of(V), ([], []))
        Fs.append(F + sum(len(v) for v in Vs))
        Vs.append(V)
    scene = trimesh.Scene()
    for name, (Vs, Fs) in parts.items():
        V = np.concatenate(Vs) * s.unit_mm / 1000.0          # model units -> m
        V = V[:, [0, 2, 1]] * np.array([1, 1, -1])            # Z-up -> Y-up
        m = trimesh.Trimesh(V, np.concatenate(Fs)[:, ::-1], process=True)
        scene.add_geometry(m, node_name=name, geom_name=name)
        print(f"  {name}: {len(m.faces)} triangles")
    scene.export(dst)
    b = scene.bounds
    print(f"{src}: {skipped} faces skipped, size {b[1] - b[0]} m")


if __name__ == "__main__":
    main(*sys.argv[1:3])
