"""Watertight 3D mesh generator, binary STL I/O, mass properties & solid-clash verifier.

Runs under `python3 -B` (NumPy).
Every CAD primitive in `params.py` is tessellated into a strictly closed,
outward-oriented 2-manifold triangle mesh (zero boundary edges, zero
non-manifold edges, strictly positive signed volume).
"""
from __future__ import annotations

import math
import struct
from pathlib import Path
from typing import Iterable

import numpy as np

import params


# ---------------------------------------------------------------------------
# Coordinate helpers
# ---------------------------------------------------------------------------
def _apply_axis(verts: np.ndarray, axis: str) -> np.ndarray:
    """Rotate a canonical Z-aligned mesh to align with 'x', 'y', or 'z' (det=+1)."""
    if axis == "z":
        return verts
    if axis == "x":
        # (x, y, z) -> (z, y, -x)  [det = +1, maps +z -> +x]
        return np.column_stack([verts[:, 2], verts[:, 1], -verts[:, 0]])
    if axis == "y":
        # (x, y, z) -> (x, z, -y)  [det = +1, maps +z -> +y]
        return np.column_stack([verts[:, 0], verts[:, 2], -verts[:, 1]])
    raise ValueError(f"Unsupported axis: {axis}")


def _inv_axis(pts: np.ndarray, axis: str) -> np.ndarray:
    """Inverse of _apply_axis: maps world-shifted points back into canonical Z frame."""
    if axis == "z":
        return pts
    if axis == "x":
        # inverse of (z, y, -x) is (-z_new, y_new, x_new)
        return np.column_stack([-pts[:, 2], pts[:, 1], pts[:, 0]])
    if axis == "y":
        # inverse of (x, z, -y) is (x_new, -z_new, y_new)
        return np.column_stack([pts[:, 0], -pts[:, 2], pts[:, 1]])
    raise ValueError(f"Unsupported axis: {axis}")


# ---------------------------------------------------------------------------
# Watertight primitive tessellators (canonical origin -> translated to center)
# ---------------------------------------------------------------------------
def _mesh_box(dx: float, dy: float, dz: float) -> tuple[np.ndarray, np.ndarray]:
    hx, hy, hz = dx / 2.0, dy / 2.0, dz / 2.0
    v = np.array([
        [-hx, -hy, -hz], [hx, -hy, -hz], [hx, hy, -hz], [-hx, hy, -hz],
        [-hx, -hy,  hz], [hx, -hy,  hz], [hx, hy,  hz], [-hx, hy,  hz],
    ], dtype=np.float64)
    f = np.array([
        [0, 2, 1], [0, 3, 2],  # bottom (-z)
        [4, 5, 6], [4, 6, 7],  # top (+z)
        [0, 1, 5], [0, 5, 4],  # front (-y)
        [2, 3, 7], [2, 7, 6],  # back (+y)
        [1, 2, 6], [1, 6, 5],  # right (+x)
        [3, 0, 4], [3, 4, 7],  # left (-x)
    ], dtype=np.int32)
    return v, f


def _mesh_frustum(r_bot: float, r_top: float, h: float, n: int = 48) -> tuple[np.ndarray, np.ndarray]:
    hz = h / 2.0
    th = np.linspace(0.0, 2.0 * math.pi, n, endpoint=False)
    c, s = np.cos(th), np.sin(th)
    verts = []
    verts.append([0.0, 0.0, -hz])  # 0: bottom center
    verts.append([0.0, 0.0,  hz])  # 1: top center
    for i in range(n):
        verts.append([r_bot * c[i], r_bot * s[i], -hz])  # 2 .. 2+n-1
    for i in range(n):
        verts.append([r_top * c[i], r_top * s[i],  hz])  # 2+n .. 2+2n-1
    v = np.array(verts, dtype=np.float64)
    faces = []
    b0, t0 = 2, 2 + n
    for i in range(n):
        j = (i + 1) % n
        faces.append([0, b0 + j, b0 + i])          # bottom (-z)
        faces.append([1, t0 + i, t0 + j])          # top (+z)
        faces.append([b0 + i, b0 + j, t0 + j])     # side 1
        faces.append([b0 + i, t0 + j, t0 + i])     # side 2
    return v, np.array(faces, dtype=np.int32)


def _mesh_cyl(r: float, h: float, axis: str, n: int = 48) -> tuple[np.ndarray, np.ndarray]:
    v, f = _mesh_frustum(r, r, h, n=n)
    return _apply_axis(v, axis), f


def _mesh_tube(r_in: float, r_out: float, h: float, axis: str, n: int = 48) -> tuple[np.ndarray, np.ndarray]:
    hz = h / 2.0
    th = np.linspace(0.0, 2.0 * math.pi, n, endpoint=False)
    c, s = np.cos(th), np.sin(th)
    # Rings: 0=bot_out, 1=top_out, 2=bot_in, 3=top_in
    bo = np.column_stack([r_out * c, r_out * s, np.full(n, -hz)])
    to = np.column_stack([r_out * c, r_out * s, np.full(n,  hz)])
    bi = np.column_stack([r_in * c,  r_in * s,  np.full(n, -hz)])
    ti = np.column_stack([r_in * c,  r_in * s,  np.full(n,  hz)])
    v = np.vstack([bo, to, bi, ti]).astype(np.float64)
    faces = []
    for i in range(n):
        j = (i + 1) % n
        # Outer wall (normal outward)
        faces.append([i, j, n + j])
        faces.append([i, n + j, n + i])
        # Inner wall (normal inward toward axis)
        faces.append([2 * n + j, 2 * n + i, 3 * n + i])
        faces.append([2 * n + j, 3 * n + i, 3 * n + j])
        # Top ring (+z)
        faces.append([n + i, n + j, 3 * n + j])
        faces.append([n + i, 3 * n + j, 3 * n + i])
        # Bottom ring (-z)
        faces.append([j, i, 2 * n + i])
        faces.append([j, 2 * n + i, 2 * n + j])
    return _apply_axis(v, axis), np.array(faces, dtype=np.int32)


def _mesh_arc_tube(
    r_in: float, r_out: float, h: float, deg0: float, deg1: float, n_per_360: int = 64
) -> tuple[np.ndarray, np.ndarray]:
    span = deg1 - deg0
    if span <= 0.0 or span >= 360.0:
        raise ValueError(f"arc_tube requires 0 < span < 360, got {span}")
    n = max(6, int(round(n_per_360 * span / 360.0)))
    hz = h / 2.0
    th = np.linspace(math.radians(deg0), math.radians(deg1), n + 1)
    c, s = np.cos(th), np.sin(th)
    m = n + 1
    bo = np.column_stack([r_out * c, r_out * s, np.full(m, -hz)])
    to = np.column_stack([r_out * c, r_out * s, np.full(m,  hz)])
    bi = np.column_stack([r_in * c,  r_in * s,  np.full(m, -hz)])
    ti = np.column_stack([r_in * c,  r_in * s,  np.full(m,  hz)])
    v = np.vstack([bo, to, bi, ti]).astype(np.float64)
    faces = []
    for i in range(n):
        j = i + 1
        # Outer wall
        faces.append([i, j, m + j])
        faces.append([i, m + j, m + i])
        # Inner wall
        faces.append([2 * m + j, 2 * m + i, 3 * m + i])
        faces.append([2 * m + j, 3 * m + i, 3 * m + j])
        # Top cap (+z)
        faces.append([m + i, m + j, 3 * m + j])
        faces.append([m + i, 3 * m + j, 3 * m + i])
        # Bottom cap (-z)
        faces.append([j, i, 2 * m + i])
        faces.append([j, 2 * m + i, 2 * m + j])
    # Start radial cap at theta=deg0 (i=0): outward normal points in -theta direction
    faces.append([0, m, 3 * m])
    faces.append([0, 3 * m, 2 * m])
    # End radial cap at theta=deg1 (i=n): outward normal points in +theta direction
    faces.append([n, 2 * m + n, 3 * m + n])
    faces.append([n, 3 * m + n, m + n])
    return v, np.array(faces, dtype=np.int32)


def _mesh_frame(ox: float, oy: float, ix: float, iy: float, h: float) -> tuple[np.ndarray, np.ndarray]:
    """Watertight hollow rectangular frame centered at origin."""
    hox, hoy = ox / 2.0, oy / 2.0
    hix, hiy = ix / 2.0, iy / 2.0
    hz = h / 2.0
    # 4 outer corners (CCW), 4 inner corners (CCW), bottom then top -> 16 vertices
    # 0..3: bot outer, 4..7: top outer, 8..11: bot inner, 12..15: top inner
    outer_xy = [(-hox, -hoy), (hox, -hoy), (hox, hoy), (-hox, hoy)]
    inner_xy = [(-hix, -hiy), (hix, -hiy), (hix, hiy), (-hix, hiy)]
    verts = (
        [[x, y, -hz] for x, y in outer_xy]
        + [[x, y,  hz] for x, y in outer_xy]
        + [[x, y, -hz] for x, y in inner_xy]
        + [[x, y,  hz] for x, y in inner_xy]
    )
    v = np.array(verts, dtype=np.float64)
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        # Outer wall
        faces.append([i, j, 4 + j])
        faces.append([i, 4 + j, 4 + i])
        # Inner wall (facing inward)
        faces.append([8 + j, 8 + i, 12 + i])
        faces.append([8 + j, 12 + i, 12 + j])
        # Top surface (+z)
        faces.append([4 + i, 4 + j, 12 + j])
        faces.append([4 + i, 12 + j, 12 + i])
        # Bottom surface (-z)
        faces.append([j, i, 8 + i])
        faces.append([j, 8 + i, 8 + j])
    return v, np.array(faces, dtype=np.int32)


def build_part_mesh(spec: dict, n_seg: int = 48) -> tuple[np.ndarray, np.ndarray]:
    """Return watertight (verts, faces) in global machine mm coordinates."""
    sh = spec["shape"]
    d = spec["dims"]
    if sh == "box":
        v, f = _mesh_box(*d)
    elif sh == "cyl":
        v, f = _mesh_cyl(d[0], d[1], d[2], n=n_seg)
    elif sh == "tube":
        v, f = _mesh_tube(d[0], d[1], d[2], d[3], n=n_seg)
    elif sh == "arc_tube":
        v, f = _mesh_arc_tube(d[0], d[1], d[2], d[3], d[4], n_per_360=max(48, n_seg))
    elif sh == "frustum":
        v, f = _mesh_frustum(d[0], d[1], d[2], n=n_seg)
    elif sh == "frame":
        v, f = _mesh_frame(*d)
    else:
        raise ValueError(f"Unknown shape: {sh}")
    c = np.asarray(spec["center"], dtype=np.float64)
    return v + c, f


def combine_meshes(meshes: Iterable[tuple[np.ndarray, np.ndarray]]) -> tuple[np.ndarray, np.ndarray]:
    v_list, f_list = [], []
    offset = 0
    for v, f in meshes:
        v_list.append(v)
        f_list.append(f + offset)
        offset += len(v)
    return np.vstack(v_list), np.vstack(f_list)


# ---------------------------------------------------------------------------
# Exact analytical volume, AABB, watertightness & STL I/O
# ---------------------------------------------------------------------------
def analytic_volume_mm3(spec: dict) -> float:
    sh = spec["shape"]
    d = spec["dims"]
    if sh == "box":
        return float(d[0] * d[1] * d[2])
    if sh == "cyl":
        return float(math.pi * d[0] ** 2 * d[1])
    if sh == "tube":
        return float(math.pi * (d[1] ** 2 - d[0] ** 2) * d[2])
    if sh == "arc_tube":
        return float(0.5 * (d[1] ** 2 - d[0] ** 2) * math.radians(d[4] - d[3]) * d[2])
    if sh == "frustum":
        r1, r2, h = d
        return float(math.pi * h / 3.0 * (r1 ** 2 + r1 * r2 + r2 ** 2))
    if sh == "frame":
        ox, oy, ix, iy, h = d
        return float((ox * oy - ix * iy) * h)
    raise ValueError(f"Unknown shape: {sh}")


def mesh_volume_and_com(verts: np.ndarray, faces: np.ndarray) -> tuple[float, np.ndarray, float]:
    """Compute exact signed volume (mm^3), center of mass (mm), and surface area (mm^2)."""
    v0 = verts[faces[:, 0]]
    v1 = verts[faces[:, 1]]
    v2 = verts[faces[:, 2]]
    cross = np.cross(v1, v2)
    signed_v6 = np.einsum("ij,ij->i", v0, cross)
    vol = float(np.sum(signed_v6) / 6.0)
    if abs(vol) > 1e-12:
        tet_com = (v0 + v1 + v2) / 4.0
        com = np.sum(tet_com * (signed_v6[:, None] / 6.0), axis=0) / vol
    else:
        com = np.mean(verts, axis=0)
    e1 = v1 - v0
    e2 = v2 - v0
    area = float(0.5 * np.sum(np.linalg.norm(np.cross(e1, e2), axis=1)))
    return vol, com, area


def check_watertight(faces: np.ndarray) -> dict:
    """Verify closed 2-manifold orientation: every directed edge has an exact twin."""
    e01 = faces[:, [0, 1]]
    e12 = faces[:, [1, 2]]
    e20 = faces[:, [2, 0]]
    edges = np.vstack([e01, e12, e20])
    counts: dict[tuple[int, int], int] = {}
    for u, v in edges.tolist():
        counts[(u, v)] = counts.get((u, v), 0) + 1
    duplicate_directed = sum(1 for c in counts.values() if c != 1)
    boundary = sum(1 for (u, v) in counts if (v, u) not in counts)
    return {
        "is_watertight": bool(boundary == 0 and duplicate_directed == 0),
        "boundary_edges": int(boundary),
        "non_manifold_edges": int(duplicate_directed),
        "triangle_count": int(len(faces)),
    }


def write_binary_stl(path: Path, verts: np.ndarray, faces: np.ndarray, header_text: str) -> None:
    """Write standard binary STL with unit outward face normals."""
    path.parent.mkdir(parents=True, exist_ok=True)
    hdr = header_text.encode("ascii", errors="replace")[:80].ljust(80, b" ")
    v0 = verts[faces[:, 0]]
    v1 = verts[faces[:, 1]]
    v2 = verts[faces[:, 2]]
    normals = np.cross(v1 - v0, v2 - v0)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.where(norms > 1e-12, normals / np.maximum(norms, 1e-12), 0.0)

    n_tri = len(faces)
    dtype = np.dtype([
        ("normal", "<f4", (3,)),
        ("v0", "<f4", (3,)),
        ("v1", "<f4", (3,)),
        ("v2", "<f4", (3,)),
        ("attr", "<u2"),
    ])
    rec = np.zeros(n_tri, dtype=dtype)
    rec["normal"] = normals.astype(np.float32)
    rec["v0"] = v0.astype(np.float32)
    rec["v1"] = v1.astype(np.float32)
    rec["v2"] = v2.astype(np.float32)
    with open(path, "wb") as fh:
        fh.write(hdr)
        fh.write(struct.pack("<I", n_tri))
        fh.write(rec.tobytes())


def inspect_binary_stl(path: Path) -> dict:
    """Independently read a binary STL from disk and verify size, watertightness & volume."""
    raw = path.read_bytes()
    if len(raw) < 84:
        raise ValueError(f"STL too short: {path}")
    n_tri = struct.unpack("<I", raw[80:84])[0]
    expected_bytes = 84 + 50 * n_tri
    if len(raw) != expected_bytes:
        raise ValueError(f"STL size mismatch for {path}: {len(raw)} != {expected_bytes}")
    dtype = np.dtype([
        ("normal", "<f4", (3,)),
        ("v0", "<f4", (3,)),
        ("v1", "<f4", (3,)),
        ("v2", "<f4", (3,)),
        ("attr", "<u2"),
    ])
    rec = np.frombuffer(raw, dtype=dtype, offset=84)
    tris = np.stack([rec["v0"], rec["v1"], rec["v2"]], axis=1).astype(np.float64)
    # Deduplicate vertices at 1e-4 mm (float32 STL tolerance)
    flat = tris.reshape(-1, 3)
    quant = np.round(flat * 1e4).astype(np.int64)
    _, inv = np.unique(quant, axis=0, return_inverse=True)
    # Map unique vertices back to float coordinates
    uniq_idx = np.zeros(int(inv.max()) + 1, dtype=np.int64)
    uniq_idx[inv] = np.arange(len(flat))
    verts = flat[uniq_idx]
    faces = inv.reshape(-1, 3).astype(np.int32)
    wt = check_watertight(faces)
    vol, com, area = mesh_volume_and_com(verts, faces)
    return {
        "file": str(path.name),
        "bytes": int(len(raw)),
        "triangles": int(n_tri),
        "is_watertight": wt["is_watertight"],
        "boundary_edges": wt["boundary_edges"],
        "non_manifold_edges": wt["non_manifold_edges"],
        "volume_mm3": round(vol, 3),
        "surface_area_mm2": round(area, 2),
        "com_mm": [round(float(x), 3) for x in com],
    }


# ---------------------------------------------------------------------------
# Exact Solid-Solid Interference & Functional Clearance Engine
# ---------------------------------------------------------------------------
def part_aabb(spec: dict) -> tuple[np.ndarray, np.ndarray]:
    v, _ = build_part_mesh(spec, n_seg=48)
    return v.min(axis=0), v.max(axis=0)


def points_strictly_inside(spec: dict, pts: np.ndarray, margin: float = 0.05) -> np.ndarray:
    """Return boolean mask of points strictly inside solid by at least `margin` mm."""
    p = pts - np.asarray(spec["center"], dtype=np.float64)
    sh = spec["shape"]
    d = spec["dims"]
    if sh == "box":
        hx, hy, hz = d[0] / 2.0 - margin, d[1] / 2.0 - margin, d[2] / 2.0 - margin
        if hx <= 0 or hy <= 0 or hz <= 0:
            return np.zeros(len(pts), dtype=bool)
        return (np.abs(p[:, 0]) < hx) & (np.abs(p[:, 1]) < hy) & (np.abs(p[:, 2]) < hz)
    if sh == "cyl":
        r, h, axis = d
        q = _inv_axis(p, axis)
        hz = h / 2.0 - margin
        rm = r - margin
        if hz <= 0 or rm <= 0:
            return np.zeros(len(pts), dtype=bool)
        rr = np.hypot(q[:, 0], q[:, 1])
        return (rr < rm) & (np.abs(q[:, 2]) < hz)
    if sh == "tube":
        ri, ro, h, axis = d
        q = _inv_axis(p, axis)
        hz = h / 2.0 - margin
        if hz <= 0 or (ro - ri) <= 2 * margin:
            return np.zeros(len(pts), dtype=bool)
        rr = np.hypot(q[:, 0], q[:, 1])
        return (rr > ri + margin) & (rr < ro - margin) & (np.abs(q[:, 2]) < hz)
    if sh == "arc_tube":
        ri, ro, h, deg0, deg1 = d
        hz = h / 2.0 - margin
        if hz <= 0 or (ro - ri) <= 2 * margin:
            return np.zeros(len(pts), dtype=bool)
        rr = np.hypot(p[:, 0], p[:, 1])
        ang = np.degrees(np.arctan2(p[:, 1], p[:, 0])) % 360.0
        # Handle angular margin in degrees based on radius
        dm = math.degrees(margin / max(ri, 1.0))
        return (
            (rr > ri + margin)
            & (rr < ro - margin)
            & (np.abs(p[:, 2]) < hz)
            & (ang > deg0 + dm)
            & (ang < deg1 - dm)
        )
    if sh == "frustum":
        r1, r2, h = d
        hz = h / 2.0 - margin
        if hz <= 0:
            return np.zeros(len(pts), dtype=bool)
        z_ok = np.abs(p[:, 2]) < hz
        t = (p[:, 2] + h / 2.0) / h
        r_loc = r1 + (r2 - r1) * t - margin
        rr = np.hypot(p[:, 0], p[:, 1])
        return z_ok & (r_loc > 0) & (rr < r_loc)
    if sh == "frame":
        ox, oy, ix, iy, h = d
        hz = h / 2.0 - margin
        if hz <= 0:
            return np.zeros(len(pts), dtype=bool)
        in_outer = (np.abs(p[:, 0]) < ox / 2.0 - margin) & (np.abs(p[:, 1]) < oy / 2.0 - margin)
        out_inner = (np.abs(p[:, 0]) > ix / 2.0 + margin) | (np.abs(p[:, 1]) > iy / 2.0 + margin)
        return in_outer & out_inner & (np.abs(p[:, 2]) < hz)
    raise ValueError(f"Unknown shape: {sh}")


def check_all_interferences(parts: dict[str, dict] | None = None, margin_mm: float = 0.05) -> dict:
    """Exact pairwise solid-solid clash check across all CAD parts."""
    parts = parts or params.PARTS
    names = list(parts.keys())
    aabbs = {k: part_aabb(parts[k]) for k in names}
    clashes = []
    mated_contacts = []
    rng = np.random.default_rng(20261122)

    for i in range(len(names)):
        a = names[i]
        lo_a, hi_a = aabbs[a]
        for j in range(i + 1, len(names)):
            b = names[j]
            lo_b, hi_b = aabbs[b]
            lo = np.maximum(lo_a, lo_b)
            hi = np.minimum(hi_a, hi_b)
            span = hi - lo
            if np.any(span < -0.02):
                continue
            # Check if merely planar contact (one axis span <= 0.02 mm)
            if np.any(span <= 2.0 * margin_mm):
                mated_contacts.append((a, b))
                continue
            # 3D AABB overlap exists -> test true interior solid intersection!
            nx = min(20, max(7, int(math.ceil(span[0] / 3.0))))
            ny = min(20, max(7, int(math.ceil(span[1] / 3.0))))
            nz = min(20, max(7, int(math.ceil(span[2] / 3.0))))
            gx = np.linspace(lo[0] + margin_mm * 0.5, hi[0] - margin_mm * 0.5, nx)
            gy = np.linspace(lo[1] + margin_mm * 0.5, hi[1] - margin_mm * 0.5, ny)
            gz = np.linspace(lo[2] + margin_mm * 0.5, hi[2] - margin_mm * 0.5, nz)
            X, Y, Z = np.meshgrid(gx, gy, gz, indexing="ij")
            grid_pts = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
            rand_pts = lo + rng.random((4000, 3)) * span
            pts = np.vstack([grid_pts, rand_pts])
            hit = points_strictly_inside(parts[a], pts, margin=margin_mm) & points_strictly_inside(
                parts[b], pts, margin=margin_mm
            )
            n_hit = int(np.sum(hit))
            if n_hit > 0:
                box_vol = float(span[0] * span[1] * span[2])
                est_vol = box_vol * (n_hit / len(pts))
                sample = pts[hit][0]
                clashes.append({
                    "part_a": a,
                    "part_b": b,
                    "est_overlap_mm3": round(est_vol, 3),
                    "sample_point_mm": [round(float(x), 2) for x in sample],
                })
    return {
        "pairs_checked": int(len(names) * (len(names) - 1) // 2),
        "solid_clashes": int(len(clashes)),
        "clashes": clashes,
        "mated_contact_pairs": int(len(mated_contacts)),
        "margin_mm": float(margin_mm),
    }


def compute_critical_clearances(parts: dict[str, dict] | None = None) -> dict[str, dict]:
    """Verify key Exp124/Exp125/Exp80 mechanical, vacuum, cryo & optical clearances (mm)."""
    p = parts or params.PARTS
    aabbs = {k: part_aabb(v) for k, v in p.items()}

    def z_gap(lower_k: str, upper_k: str) -> float:
        return round(float(aabbs[upper_k][0][2] - aabbs[lower_k][1][2]), 3)

    def x_gap(left_k: str, right_k: str) -> float:
        return round(float(aabbs[right_k][0][0] - aabbs[left_k][1][0]), 3)

    def y_gap(neg_k: str, pos_k: str) -> float:
        return round(float(aabbs[pos_k][0][1] - aabbs[neg_k][1][1]), 3)

    # Radial gaps
    hda_r = p["s1_energy_filter"]["dims"][1]
    flange_rin = p["s5_chamber_top_flange"]["dims"][0]
    lens_r = p["s2_mini_lens_plate"]["dims"][0]
    ibic_rin = p["s3_ibic_contact_ring"]["dims"][0]
    tile_rout = p["s2_tile_carrier"]["dims"][1]
    mag_bore_r = params.DESIGN_SPECS["magnet_clear_bore_mm"] / 2.0  # 75.0 mm
    aperture_rout = p["s2_aperture_plate"]["dims"][1]
    transfer_rout = p["s1_transfer_lens"]["dims"][1]
    former_rout = p["s6_magnet_former_upper"]["dims"][1]
    chamber_rin = p["s5_chamber_wall_upper"]["dims"][0]
    # Coaxial pedestal between Cryoperm (r=41) and B-coils (r=56)
    cryoperm_rout = p["s6_cryoperm_sleeve"]["dims"][1]
    ped_rin, ped_rout = p["s4_stage_pedestal"]["dims"][0], p["s4_stage_pedestal"]["dims"][1]
    buck_rin = p["s6_coil_b_upper"]["dims"][0]
    # Resonator disk inside Nb Meissner cup & Nb cup inside Cryoperm
    res_r = p["s6_nbtin_resonator_carrier"]["dims"][0]
    nb_rin, nb_rout = p["s6_meissner_cup_wall"]["dims"][0], p["s6_meissner_cup_wall"]["dims"][1]
    cryoperm_rin = p["s6_cryoperm_sleeve"]["dims"][0]
    # Piezo coarse diagonal inside Ø150 mm bore
    coarse_diag_r = p["s4_piezo_coarse_xy"]["dims"][0] * math.sqrt(2.0) / 2.0
    # Cold finger inside 4K shield tube
    cf_z = p["s6_mxc_cold_finger"]["center"][2]
    cf_r = p["s6_mxc_cold_finger"]["dims"][0]
    sh4_z = p["s6_cryo_bridge_4k_shield"]["center"][2]
    sh4_rin = p["s6_cryo_bridge_4k_shield"]["dims"][0]
    cf_radial_gap = round(float(sh4_rin - (abs(sh4_z - cf_z) + cf_r)), 3)

    # Active Arch-B 32x32 (0.50 mm pitch = 16.0x16.0 mm, diag = 22.627 mm) vs S1.6/S2.1 inner bore (Ø28.0 mm)
    min_beam_bore_d = min(
        2.0 * p["s1_transfer_lens"]["dims"][0],
        2.0 * p["s2_aperture_plate"]["dims"][0],
    )
    array_diag_mm = params.DESIGN_SPECS["write_field_mm"] * math.sqrt(2.0)
    array_bore_clr = round(float((min_beam_bore_d - array_diag_mm) / 2.0), 3)

    # Exp130 S5.5 flash window clear aperture (Ø44 mm) vs Ø36 mm beam
    flash_ca_r = p["s5_flash_anneal_duct"]["dims"][0]
    flash_beam_r = params.DESIGN_SPECS["flash_beam_od_mm"] / 2.0
    flash_beam_clr = round(float(flash_ca_r - flash_beam_r), 3)

    # Exp131 M4 4K crossbar switch inside HEMT ring (r_in=88 mm) & clear of coax (|y|>=53 mm)
    hemt_rin = p["s6_hemt_rack_4k"]["dims"][0]
    cb_dx, cb_dy, _ = p["s6_m4_crossbar_4k_mount"]["dims"]
    cb_corner_r = math.hypot(cb_dx / 2.0, cb_dy / 2.0)
    cb_hemt_clr = round(float(hemt_rin - cb_corner_r), 3)
    coax_inner_y = abs(p["s6_coax_4k_still_pos"]["center"][1]) - p["s6_coax_4k_still_pos"]["dims"][0]
    cb_coax_y_clr = round(float(coax_inner_y - cb_dy / 2.0), 3)

    # Exp133 OVC CF63 bellows (r_in=22 mm) vs 4K shield (r_out=10.5 mm) & 4x braids inside 4K shield (r_in=9.0 mm)
    bel_rin = p["s6_ovc_bellows_cf63"]["dims"][0]
    sh4_rout = p["s6_cryo_bridge_4k_shield"]["dims"][1]
    bel_4k_clr = round(float(bel_rin - sh4_rout), 3)
    braid_max_r = 0.0
    for b_idx in range(1, 5):
        bspec = p[f"s6_mxc_braid_{b_idx}"]
        by_m = abs(bspec["center"][1]) + bspec["dims"][1] / 2.0
        bz_m = abs(bspec["center"][2] - sh4_z) + bspec["dims"][2] / 2.0
        braid_max_r = max(braid_max_r, math.hypot(by_m, bz_m))
    braid_4k_clr = round(float(sh4_rin - braid_max_r), 3)
    rv_dr_x_clr = x_gap("s6_pt420_remote_valve_box", "s6_dr_top_flange")

    # Exp139 S5.6 MBE capper clearances (vs UHV top flange, transfer arm, S7 feedthrough panel)
    s56_flange_x_clr = x_gap("s5_chamber_top_flange", "s5_mbe_cf100_flange")
    s56_arm_z_clr = z_gap("s5_transfer_arm", "s5_mbe_cf100_flange")
    s56_s7_x_clr = x_gap("s5_mbe_tmp_neg_pump", "s7_feedthrough_panel")

    # Exp140 S6.5 Cryo-MUX (20 mK TWPA/Purcell, 4K 32-ch HEMT, 96-coax loom) & 2U RFSoC clearances
    dr_sh4_rin = p["s6_shield_4k_lower"]["dims"][0]
    twpa_dx, twpa_dy, _ = p["s6_s65_twpa_purcell_pack"]["dims"]
    twpa_4k_clr = round(float(dr_sh4_rin - math.hypot(twpa_dx / 2.0, twpa_dy / 2.0)), 3)
    s65_hemt_rout = p["s6_s65_hemt_bank_32ch"]["dims"][1]
    s65_hemt_4k_clr = round(float(dr_sh4_rin - s65_hemt_rout), 3)
    s65_loom_m4_x_clr = x_gap("s6_s65_coax_loom_4k_still_pos", "s6_m4_crossbar_4k_mount")
    s65_rfsoc_awg_z_clr = z_gap("s7_awg_rf_mw_bay", "s7_s65_rfsoc_boed_bay")

    # Exp142 Option-Q (S1.6 Multi-Species Cartridge + S9.1 Cryo-qRAM/Fiber Bridge) clearances
    s16_duo_y_clr = y_gap("s1_duoplasmatron", "s1_multi_species_cartridge")
    s16_ph3_y_clr = y_gap("s1_ph3_manifold", "s1_multi_species_cartridge")
    s91_twpa_z_clr = z_gap("s6_s91_qram_bridge_20mk", "s6_s65_twpa_purcell_pack")
    s91_valve_x_clr = x_gap("s6_pt420_valve_stand", "s6_s91_ovc_feedthrough")
    drx = p["s6_dr_flange_4k"]["center"][0]
    loom_r_rel = abs(p["s6_s91_qram_fiber_loom"]["center"][0] - drx)
    loom_rad = p["s6_s91_qram_fiber_loom"]["dims"][0]
    sh4_rout_dr = p["s6_shield_4k_upper"]["dims"][1]
    sh50_rin_dr = p["s6_shield_50k_upper"]["dims"][0]
    s91_loom_shield_clr = round(float(min((loom_r_rel - loom_rad) - sh4_rout_dr, sh50_rin_dr - (loom_r_rel + loom_rad))), 3)

    # Exp143 Option-HPC (S9.HPC 4U+1U 100G RoCEv2 RDMA Decoder Stack) clearances
    s9hpc_aisle_x_clr = x_gap("s7_rack_base", "s7_s9hpc_decoder_node_1")
    s9hpc_n1_n2_z_clr = z_gap("s7_s9hpc_decoder_node_1", "s7_s9hpc_decoder_node_2")
    s9hpc_n2_sw_z_clr = z_gap("s7_s9hpc_decoder_node_2", "s7_s9hpc_rocev2_switch")

    checks = {
        "exp124_archB_wafer_to_minilens_WD_mm": {"value_mm": z_gap("s3_silicon_wafer", "s2_mini_lens_plate"), "min_req_mm": 0.20},
        "beam_array_diagonal_to_bore_clearance_mm": {"value_mm": array_bore_clr, "min_req_mm": 2.0},
        "ibic_ring_to_archB_lens_radial_mm": {"value_mm": round(ibic_rin - lens_r, 3), "min_req_mm": 1.5},
        "tile_carrier_to_magnet_bore_radial_mm": {"value_mm": round(mag_bore_r - tile_rout, 3), "min_req_mm": 5.0},
        "aperture_frame_to_magnet_bore_radial_mm": {"value_mm": round(mag_bore_r - aperture_rout, 3), "min_req_mm": 15.0},
        "transfer_lens_to_magnet_bore_radial_mm": {"value_mm": round(mag_bore_r - transfer_rout, 3), "min_req_mm": 20.0},
        "hda_filter_to_top_flange_bore_radial_mm": {"value_mm": round(flange_rin - hda_r, 3), "min_req_mm": 5.0},
        "piezo_coarse_corner_to_magnet_bore_mm": {"value_mm": round(mag_bore_r - coarse_diag_r, 3), "min_req_mm": 5.0},
        "pedestal_to_cryoperm_radial_mm": {"value_mm": round(ped_rin - cryoperm_rout, 3), "min_req_mm": 3.0},
        "pedestal_to_bucking_coil_radial_mm": {"value_mm": round(buck_rin - ped_rout, 3), "min_req_mm": 3.0},
        "nbtin_disk_inside_nb_meissner_radial_mm": {"value_mm": round(nb_rin - res_r, 3), "min_req_mm": 5.0},
        "nb_meissner_inside_cryoperm_radial_mm": {"value_mm": round(cryoperm_rin - nb_rout, 3), "min_req_mm": 3.0},
        "magnet_former_to_chamber_wall_radial_mm": {"value_mm": round(chamber_rin - former_rout, 3), "min_req_mm": 5.0},
        "cryo_4k_tube_in_36mm_magnet_split_z_mm": {"value_mm": round(min(z_gap("s6_coil_m_lower", "s6_cryo_bridge_4k_shield"), z_gap("s6_cryo_bridge_4k_shield", "s6_coil_m_upper")), 3), "min_req_mm": 0.5},
        "cold_finger_inside_4k_shield_radial_mm": {"value_mm": cf_radial_gap, "min_req_mm": 1.5},
        "dr_frame_to_granite_x_mm": {"value_mm": x_gap("s6_dr_support_frame", "s4_granite_base"), "min_req_mm": 15.0},
        "granite_to_loadlock_stand_x_mm": {"value_mm": x_gap("s4_granite_base", "s5_loadlock_stand"), "min_req_mm": 10.0},
        "transfer_arm_to_s7_panel_x_mm": {"value_mm": x_gap("s5_transfer_arm", "s7_feedthrough_panel"), "min_req_mm": 25.0},
        "turbo_pump_to_granite_y_mm": {"value_mm": y_gap("s5_turbo_pump", "s4_granite_base"), "min_req_mm": 15.0},
        # CAD v4.0 clearances (Exp130 S5.5, Exp131 M4, Exp133 PT420 decoupling)
        "exp130_flash_window_beam_radial_mm": {"value_mm": flash_beam_clr, "min_req_mm": 2.0},
        "exp131_m4_crossbar_to_hemt_radial_mm": {"value_mm": cb_hemt_clr, "min_req_mm": 15.0},
        "exp131_m4_crossbar_to_coax_y_mm": {"value_mm": cb_coax_y_clr, "min_req_mm": 10.0},
        "exp133_bellows_to_4k_shield_radial_mm": {"value_mm": bel_4k_clr, "min_req_mm": 8.0},
        "exp133_braids_inside_4k_shield_radial_mm": {"value_mm": braid_4k_clr, "min_req_mm": 2.0},
        "exp133_remote_valve_to_dr_flange_x_mm": {"value_mm": rv_dr_x_clr, "min_req_mm": 150.0},
        # CAD v5.0 clearances (Exp139 S5.6 MBE capper, Exp140 S6.5 Cryo-MUX & 2U RFSoC)
        "exp139_s56_to_chamber_top_flange_x_mm": {"value_mm": s56_flange_x_clr, "min_req_mm": 100.0},
        "exp139_s56_to_transfer_arm_z_mm": {"value_mm": s56_arm_z_clr, "min_req_mm": 65.0},
        "exp139_s56_to_s7_panel_x_mm": {"value_mm": s56_s7_x_clr, "min_req_mm": 100.0},
        "exp140_s65_twpa_inside_4k_shield_radial_mm": {"value_mm": twpa_4k_clr, "min_req_mm": 15.0},
        "exp140_s65_hemt_to_4k_shield_radial_mm": {"value_mm": s65_hemt_4k_clr, "min_req_mm": 8.0},
        "exp140_s65_coax_loom_to_m4_crossbar_x_mm": {"value_mm": s65_loom_m4_x_clr, "min_req_mm": 5.0},
        "exp140_s65_rfsoc_to_awg_z_mm": {"value_mm": s65_rfsoc_awg_z_clr, "min_req_mm": 10.0},
        # CAD v6.0 clearances (Exp142 Option-Q S1.6/S9.1, Exp143 Option-HPC S9.HPC)
        "exp142_s16_cartridge_to_duoplasmatron_y_mm": {"value_mm": s16_duo_y_clr, "min_req_mm": 20.0},
        "exp142_s16_cartridge_to_ph3_manifold_y_mm": {"value_mm": s16_ph3_y_clr, "min_req_mm": 100.0},
        "exp142_s91_qram_chip_to_s65_twpa_z_mm": {"value_mm": s91_twpa_z_clr, "min_req_mm": 5.0},
        "exp142_s91_ovc_port_to_valve_stand_x_mm": {"value_mm": s91_valve_x_clr, "min_req_mm": 100.0},
        "exp142_s91_fiber_loom_to_4k_50k_shields_mm": {"value_mm": s91_loom_shield_clr, "min_req_mm": 1.5},
        "exp143_s9hpc_to_s7_rack_aisle_x_mm": {"value_mm": s9hpc_aisle_x_clr, "min_req_mm": 40.0},
        "exp143_s9hpc_node1_to_node2_airflow_z_mm": {"value_mm": s9hpc_n1_n2_z_clr, "min_req_mm": 3.0},
        "exp143_s9hpc_switch_to_node2_z_mm": {"value_mm": s9hpc_n2_sw_z_clr, "min_req_mm": 3.0},
    }
    for k, rec in checks.items():
        rec["pass"] = bool(rec["value_mm"] >= rec["min_req_mm"])
    return checks
