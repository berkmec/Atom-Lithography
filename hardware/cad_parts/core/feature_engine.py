"""Watertight 2-manifold triangle-mesh solid builders, mass properties & binary STL I/O.

100% pure Python + NumPy (zero sudo, zero OCCT/cairo dependencies).
Every solid builder produces a strictly watertight, outward-oriented 2-manifold
triangle mesh verified by ``verify_watertight``:
- ``0`` boundary edges (every undirected edge has degree 2)
- ``0`` non-manifold edges
- ``0`` orientation errors (every directed half-edge has an exact opposite twin)
- ``0`` degenerate triangles
- strictly positive signed volume on every connected shell
"""
from __future__ import annotations

import math
import struct
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np

# ---------------------------------------------------------------------------
# Engineering material density table (kg / m^3)
# ---------------------------------------------------------------------------
MATERIAL_DENSITIES_KG_M3: dict[str, float] = {
    "316LN": 8000.0,
    "316L": 8000.0,
    "304 SS": 7930.0,
    "OFHC Cu": 8960.0,
    "Cu": 8960.0,
    "Ti-6Al-4V": 4430.0,
    "Al2O3": 3950.0,
    "AlN": 3260.0,
    "Mo": 10280.0,
    "Invar-36": 8050.0,
    "Zerodur": 2530.0,
    "Si": 2329.0,
    "Nb": 8570.0,
    "NbTi": 6530.0,
    "Mu-metal": 8700.0,
    "Cryoperm": 8700.0,
    "Vespel SP-22": 1650.0,
    "PEEK": 1320.0,
    "Granite": 3000.0,
    "FR4": 1860.0,
    "Rogers": 1860.0,
    "Al 6061": 2700.0,
    "Graphite": 1850.0,
    "Sapphire": 3980.0,
    "SmCo": 8400.0,
    # Additional BOM materials
    "BeCu": 8250.0,
    "Macor": 2520.0,
    "PBN": 2150.0,
    "Fused Silica": 2200.0,
    "PTFE": 2200.0,
    "Soft Iron": 7870.0,
    "Steel": 7850.0,
    "CuNi": 8900.0,
    "Al-Bronze": 7600.0,
    "Au": 19300.0,
    "W": 19250.0,
    "LFP": 2100.0,
}

_DENSITY_ALIASES: tuple[tuple[str, str], ...] = (
    ("vespel", "Vespel SP-22"),
    ("peek", "PEEK"),
    ("granit", "Granite"),
    ("granite", "Granite"),
    ("diyabaz", "Granite"),
    ("zerodur", "Zerodur"),
    ("ule", "Zerodur"),
    ("invar", "Invar-36"),
    ("sapphire", "Sapphire"),
    ("safir", "Sapphire"),
    ("al2o3", "Al2O3"),
    ("alumina", "Al2O3"),
    ("seramik", "Al2O3"),
    ("ceramic", "Al2O3"),
    ("aln", "AlN"),
    ("smco", "SmCo"),
    ("cryoperm", "Cryoperm"),
    ("mu-metal", "Mu-metal"),
    ("mumetal", "Mu-metal"),
    ("nbtin", "Si"),
    ("nbti", "NbTi"),
    ("niobium", "Nb"),
    ("ti-6al-4v", "Ti-6Al-4V"),
    ("titanyum", "Ti-6Al-4V"),
    ("titanium", "Ti-6Al-4V"),
    ("316ln", "316LN"),
    ("316l", "316L"),
    ("304", "304 SS"),
    ("paslanmaz", "316LN"),
    ("stainless", "316LN"),
    ("becu", "BeCu"),
    ("cuni", "CuNi"),
    ("ofhc", "OFHC Cu"),
    ("copper", "OFHC Cu"),
    ("bakir", "OFHC Cu"),
    ("molibden", "Mo"),
    ("molybdenum", "Mo"),
    ("al-bronz", "Al-Bronze"),
    ("rogers", "Rogers"),
    ("fr4", "FR4"),
    ("pcb", "FR4"),
    ("al 6061", "Al 6061"),
    ("6061", "Al 6061"),
    ("aluminyum", "Al 6061"),
    ("aluminum", "Al 6061"),
    ("grafit", "Graphite"),
    ("graphite", "Graphite"),
    ("macor", "Macor"),
    ("pbn", "PBN"),
    ("pirolitik", "PBN"),
    ("fused silica", "Fused Silica"),
    ("erimis", "Fused Silica"),
    ("kuvars", "Fused Silica"),
    ("quartz", "Fused Silica"),
    ("ptfe", "PTFE"),
    ("pfa", "PTFE"),
    ("kapton", "Vespel SP-22"),
    ("yumusak demir", "Soft Iron"),
    ("celik", "Steel"),
    ("steel", "Steel"),
    ("lfp", "LFP"),
    ("28si", "Si"),
    ("silicon", "Si"),
    ("soi", "Si"),
    ("altin", "Au"),
    ("gold", "Au"),
)


def lookup_density_kg_m3(material: str) -> float:
    """Resolve a canonical or BOM material descriptor to density (kg/m^3)."""
    s = (material or "").strip()
    if s in MATERIAL_DENSITIES_KG_M3:
        return MATERIAL_DENSITIES_KG_M3[s]
    low = s.lower()
    exact_short = {
        "cu": "OFHC Cu",
        "nb": "Nb",
        "mo": "Mo",
        "si": "Si",
        "ti": "Ti-6Al-4V",
        "al": "Al 6061",
        "ss": "316LN",
        "au": "Au",
        "w": "W",
    }
    if low in exact_short:
        return MATERIAL_DENSITIES_KG_M3[exact_short[low]]
    # Check primary segment before '/' first when BOM lists composite assemblies
    primary = low.split("/")[0].strip()
    for pat, key in _DENSITY_ALIASES:
        if pat in primary:
            return MATERIAL_DENSITIES_KG_M3[key]
    for pat, key in _DENSITY_ALIASES:
        if pat in low:
            return MATERIAL_DENSITIES_KG_M3[key]
    # Conservative steel/chassis default for generic electronic rack enclosures
    return 7850.0


# ---------------------------------------------------------------------------
# Core Mesh & Verification Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class SolidMesh:
    """Watertight 3D triangle mesh in millimeters (mm)."""

    vertices: np.ndarray  # (N, 3) float64
    faces: np.ndarray     # (M, 3) int32, CCW outward winding
    name: str = ""
    material: str = "316LN"

    def __post_init__(self) -> None:
        self.vertices = np.ascontiguousarray(self.vertices, dtype=np.float64)
        self.faces = np.ascontiguousarray(self.faces, dtype=np.int32)
        if self.vertices.ndim != 2 or self.vertices.shape[1] != 3:
            raise ValueError(f"vertices must have shape (N, 3), got {self.vertices.shape}")
        if self.faces.ndim != 2 or self.faces.shape[1] != 3:
            raise ValueError(f"faces must have shape (M, 3), got {self.faces.shape}")

    @property
    def n_vertices(self) -> int:
        return int(self.vertices.shape[0])

    @property
    def n_faces(self) -> int:
        return int(self.faces.shape[0])

    def bbox(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        mn = self.vertices.min(axis=0)
        mx = self.vertices.max(axis=0)
        return (
            (float(mn[0]), float(mn[1]), float(mn[2])),
            (float(mx[0]), float(mx[1]), float(mx[2])),
        )

    def extents(self) -> tuple[float, float, float]:
        mn, mx = self.bbox()
        return (mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2])

    def copy(self) -> SolidMesh:
        return SolidMesh(
            vertices=self.vertices.copy(),
            faces=self.faces.copy(),
            name=self.name,
            material=self.material,
        )


@dataclass(frozen=True)
class MeshValidationResult:
    """Topological & geometric watertightness report."""

    watertight: bool
    n_vertices: int
    n_faces: int
    n_edges: int
    boundary_edges: int
    non_manifold_edges: int
    orientation_errors: int
    degenerate_faces: int
    n_shells: int
    signed_volume_mm3: float
    min_shell_volume_mm3: float
    surface_area_mm2: float
    euler_characteristic: int
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MassProperties:
    """Exact polyhedral mass, CG, inertia tensor, and bounding box."""

    material: str
    density_kg_m3: float
    volume_mm3: float
    volume_cm3: float
    surface_area_mm2: float
    mass_kg: float
    cg_mm: tuple[float, float, float]
    inertia_kg_mm2: tuple[float, float, float, float, float, float]  # Ixx,Iyy,Izz,Ixy,Ixz,Iyz
    bbox_min_mm: tuple[float, float, float]
    bbox_max_mm: tuple[float, float, float]
    extents_mm: tuple[float, float, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Coordinate & Rigid-Body Transform Helpers
# ---------------------------------------------------------------------------
def _rotation_matrix_from_axis_spec(axis: str | Sequence[float]) -> np.ndarray:
    """Return 3x3 proper rotation matrix (det=+1) mapping local +Z onto ``axis``."""
    if isinstance(axis, str):
        key = axis.strip().lower()
        if key in {"z", "+z"}:
            return np.eye(3, dtype=np.float64)
        if key == "-z":
            return np.array([[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, -1.0]])
        if key in {"x", "+x"}:
            return np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]])
        if key == "-x":
            return np.array([[0.0, 0.0, -1.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0]])
        if key in {"y", "+y"}:
            return np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]])
        if key == "-y":
            return np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])
        raise ValueError(f"Unsupported axis string: {axis!r}")

    vec = np.asarray(axis, dtype=np.float64)
    n = float(np.linalg.norm(vec))
    if n < 1e-12:
        raise ValueError("Axis vector must be non-zero")
    u = vec / n
    z = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    c = float(np.dot(z, u))
    if c > 1.0 - 1e-12:
        return np.eye(3, dtype=np.float64)
    if c < -1.0 + 1e-12:
        return np.array([[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, -1.0]])
    v = np.cross(z, u)
    s = float(np.linalg.norm(v))
    k = np.array(
        [[0.0, -v[2], v[1]], [v[2], 0.0, -v[0]], [-v[1], v[0], 0.0]],
        dtype=np.float64,
    )
    return np.eye(3, dtype=np.float64) + k + (k @ k) * ((1.0 - c) / (s * s))


def _euler_xyz_matrix(rx_deg: float, ry_deg: float, rz_deg: float) -> np.ndarray:
    rx, ry, rz = math.radians(rx_deg), math.radians(ry_deg), math.radians(rz_deg)
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    mx = np.array([[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]])
    my = np.array([[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]])
    mz = np.array([[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]])
    return mz @ my @ mx


def _axis_angle_matrix(axis_vec: Sequence[float], angle_deg: float) -> np.ndarray:
    u = np.asarray(axis_vec, dtype=np.float64)
    n = float(np.linalg.norm(u))
    if n < 1e-12:
        raise ValueError("axis_angle axis must be non-zero")
    u = u / n
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)
    k = np.array(
        [[0.0, -u[2], u[1]], [u[2], 0.0, -u[0]], [-u[1], u[0], 0.0]],
        dtype=np.float64,
    )
    return np.eye(3) * ca + k * sa + np.outer(u, u) * (1.0 - ca)


def _orient_and_place(
    verts: np.ndarray,
    axis: str | Sequence[float] = "z",
    center: Sequence[float] = (0.0, 0.0, 0.0),
) -> np.ndarray:
    rot = _rotation_matrix_from_axis_spec(axis)
    c = np.asarray(center, dtype=np.float64)
    return verts @ rot.T + c


def transform_mesh(
    mesh: SolidMesh,
    *,
    translation: Sequence[float] = (0.0, 0.0, 0.0),
    rotation_deg: Sequence[float] = (0.0, 0.0, 0.0),
    axis_angle: tuple[Sequence[float], float] | None = None,
    scale: float | Sequence[float] = 1.0,
    name: str | None = None,
) -> SolidMesh:
    """Apply scale, rotation (Euler XYZ and/or axis-angle), and translation to ``mesh``."""
    v = mesh.vertices.copy()
    f = mesh.faces.copy()

    if isinstance(scale, (int, float)):
        sv = np.array([float(scale)] * 3, dtype=np.float64)
    else:
        sv = np.asarray(scale, dtype=np.float64)
    v = v * sv
    if float(sv[0] * sv[1] * sv[2]) < 0.0:
        f = f[:, [0, 2, 1]]

    if any(abs(float(a)) > 1e-12 for a in rotation_deg):
        rmat = _euler_xyz_matrix(float(rotation_deg[0]), float(rotation_deg[1]), float(rotation_deg[2]))
        v = v @ rmat.T

    if axis_angle is not None:
        rmat2 = _axis_angle_matrix(axis_angle[0], float(axis_angle[1]))
        v = v @ rmat2.T

    t = np.asarray(translation, dtype=np.float64)
    if np.any(t != 0.0):
        v = v + t

    return SolidMesh(
        vertices=v,
        faces=f,
        name=name if name is not None else mesh.name,
        material=mesh.material,
    )


def merge_solids(
    meshes: Sequence[SolidMesh],
    *,
    name: str = "",
    material: str | None = None,
) -> SolidMesh:
    """Merge multiple watertight solids into a single multi-shell ``SolidMesh``."""
    if not meshes:
        raise ValueError("merge_solids requires at least one SolidMesh")
    v_list: list[np.ndarray] = []
    f_list: list[np.ndarray] = []
    offset = 0
    for m in meshes:
        v_list.append(m.vertices)
        f_list.append(m.faces + offset)
        offset += m.n_vertices
    mat = material if material is not None else meshes[0].material
    return SolidMesh(
        vertices=np.vstack(v_list),
        faces=np.vstack(f_list),
        name=name or meshes[0].name,
        material=mat,
    )


def split_shells(mesh: SolidMesh) -> list[SolidMesh]:
    """Split a multi-shell ``SolidMesh`` into vertex-connected component shells."""
    n_v = mesh.n_vertices
    n_f = mesh.n_faces
    if n_f == 0:
        return []
    adj: list[list[int]] = [[] for _ in range(n_v)]
    for fi, (a, b, c) in enumerate(mesh.faces):
        adj[int(a)].append(fi)
        adj[int(b)].append(fi)
        adj[int(c)].append(fi)

    visited = np.zeros(n_f, dtype=bool)
    shells: list[SolidMesh] = []
    for start_f in range(n_f):
        if visited[start_f]:
            continue
        comp_faces: list[int] = []
        q = deque([start_f])
        visited[start_f] = True
        while q:
            fi = q.popleft()
            comp_faces.append(fi)
            for vi in mesh.faces[fi]:
                for nb in adj[int(vi)]:
                    if not visited[nb]:
                        visited[nb] = True
                        q.append(nb)
        sub_f = mesh.faces[comp_faces]
        uniq_v, inv = np.unique(sub_f.ravel(), return_inverse=True)
        new_v = mesh.vertices[uniq_v]
        new_f = inv.reshape(-1, 3).astype(np.int32)
        shells.append(
            SolidMesh(
                vertices=new_v,
                faces=new_f,
                name=f"{mesh.name}_shell{len(shells)}" if mesh.name else f"shell{len(shells)}",
                material=mesh.material,
            )
        )
    return shells


# ---------------------------------------------------------------------------
# Watertightness & Mass Properties Verification
# ---------------------------------------------------------------------------
def verify_watertight(mesh: SolidMesh) -> MeshValidationResult:
    """Strictly verify 2-manifold watertightness, outward orientation, and shell volumes."""
    errors: list[str] = []
    v = mesh.vertices
    f = mesh.faces
    n_v = mesh.n_vertices
    n_f = mesh.n_faces

    if n_v < 4 or n_f < 4:
        return MeshValidationResult(
            watertight=False,
            n_vertices=n_v,
            n_faces=n_f,
            n_edges=0,
            boundary_edges=0,
            non_manifold_edges=0,
            orientation_errors=0,
            degenerate_faces=n_f,
            n_shells=0,
            signed_volume_mm3=0.0,
            min_shell_volume_mm3=0.0,
            surface_area_mm2=0.0,
            euler_characteristic=0,
            errors=("Mesh has fewer than 4 vertices or 4 faces",),
        )

    if not np.all(np.isfinite(v)):
        errors.append("Non-finite vertex coordinates found")
    if int(f.min()) < 0 or int(f.max()) >= n_v:
        errors.append("Face vertex index out of bounds")
        return MeshValidationResult(
            watertight=False,
            n_vertices=n_v,
            n_faces=n_f,
            n_edges=0,
            boundary_edges=0,
            non_manifold_edges=0,
            orientation_errors=0,
            degenerate_faces=0,
            n_shells=0,
            signed_volume_mm3=0.0,
            min_shell_volume_mm3=0.0,
            surface_area_mm2=0.0,
            euler_characteristic=0,
            errors=tuple(errors),
        )

    # Degenerate face check
    v0 = v[f[:, 0]]
    v1 = v[f[:, 1]]
    v2 = v[f[:, 2]]
    cross = np.cross(v1 - v0, v2 - v0)
    areas = 0.5 * np.linalg.norm(cross, axis=1)
    repeated_idx = (f[:, 0] == f[:, 1]) | (f[:, 1] == f[:, 2]) | (f[:, 2] == f[:, 0])
    degenerate_faces = int(np.sum(repeated_idx | (areas <= 1e-14)))
    if degenerate_faces > 0:
        errors.append(f"{degenerate_faces} degenerate (zero-area or repeated-vertex) faces")

    # Vectorized undirected & directed half-edge audit
    e_u = np.concatenate([f[:, 0], f[:, 1], f[:, 2]]).astype(np.int64)
    e_v = np.concatenate([f[:, 1], f[:, 2], f[:, 0]]).astype(np.int64)
    lo = np.minimum(e_u, e_v)
    hi = np.maximum(e_u, e_v)
    stride = np.int64(n_v)
    undir_keys = lo * stride + hi
    _, undir_counts = np.unique(undir_keys, return_counts=True)
    n_edges = int(undir_counts.size)
    boundary_edges = int(np.sum(undir_counts == 1))
    non_manifold_edges = int(np.sum(undir_counts > 2))

    # Directed half-edge orientation consistency: every (u, v) occurs once and matches (v, u)
    dir_keys = e_u * stride + e_v
    uniq_dir, dir_counts = np.unique(dir_keys, return_counts=True)
    dup_dir = int(np.sum(dir_counts > 1))
    rev_keys = e_v * stride + e_u
    # Fast membership test against sorted uniq_dir
    idx_rev = np.searchsorted(uniq_dir, rev_keys)
    idx_clipped = np.minimum(idx_rev, uniq_dir.size - 1)
    missing_twin = int(np.sum(uniq_dir[idx_clipped] != rev_keys))
    orientation_errors = dup_dir + missing_twin

    if boundary_edges > 0:
        errors.append(f"{boundary_edges} boundary edges (mesh is open)")
    if non_manifold_edges > 0:
        errors.append(f"{non_manifold_edges} non-manifold edges")
    if orientation_errors > 0:
        errors.append(f"{orientation_errors} half-edge orientation errors")

    # Signed volume (total and per connected shell)
    signed_vol = float(np.sum(np.einsum("ij,ij->i", v0, np.cross(v1, v2))) / 6.0)
    surf_area = float(np.sum(areas))
    shells = split_shells(mesh)
    shell_vols: list[float] = []
    for sh in shells:
        sv0 = sh.vertices[sh.faces[:, 0]]
        sv1 = sh.vertices[sh.faces[:, 1]]
        sv2 = sh.vertices[sh.faces[:, 2]]
        shell_vols.append(float(np.sum(np.einsum("ij,ij->i", sv0, np.cross(sv1, sv2))) / 6.0))
    min_shell_vol = min(shell_vols) if shell_vols else 0.0

    if signed_vol <= 0.0:
        errors.append(f"Non-positive signed volume ({signed_vol:.6g} mm^3)")
    if min_shell_vol <= 0.0:
        errors.append(f"Inverted shell detected (min shell volume {min_shell_vol:.6g} mm^3)")

    # Count only referenced vertices for Euler characteristic
    used_v = int(np.unique(f).size)
    euler = used_v - n_edges + n_f

    watertight = (
        len(errors) == 0
        and boundary_edges == 0
        and non_manifold_edges == 0
        and orientation_errors == 0
        and degenerate_faces == 0
        and signed_vol > 0.0
        and min_shell_vol > 0.0
    )

    return MeshValidationResult(
        watertight=watertight,
        n_vertices=n_v,
        n_faces=n_f,
        n_edges=n_edges,
        boundary_edges=boundary_edges,
        non_manifold_edges=non_manifold_edges,
        orientation_errors=orientation_errors,
        degenerate_faces=degenerate_faces,
        n_shells=len(shells),
        signed_volume_mm3=signed_vol,
        min_shell_volume_mm3=min_shell_vol,
        surface_area_mm2=surf_area,
        euler_characteristic=euler,
        errors=tuple(errors),
    )


def compute_mass_props(
    mesh: SolidMesh,
    material: str | None = None,
    density_kg_m3: float | None = None,
) -> MassProperties:
    """Compute exact polyhedral volume, mass, CG, inertia tensor, and bounding box."""
    mat = material if material is not None else mesh.material
    rho = float(density_kg_m3) if density_kg_m3 is not None else lookup_density_kg_m3(mat)

    v = mesh.vertices
    f = mesh.faces
    v0 = v[f[:, 0]]
    v1 = v[f[:, 1]]
    v2 = v[f[:, 2]]

    cross = np.cross(v1 - v0, v2 - v0)
    surf_area = float(0.5 * np.sum(np.linalg.norm(cross, axis=1)))

    # Signed tetrahedral volumes relative to origin (mm^3)
    tet_vol = np.einsum("ij,ij->i", v0, np.cross(v1, v2)) / 6.0
    vol_mm3 = float(np.sum(tet_vol))
    if abs(vol_mm3) < 1e-18:
        cg = np.zeros(3, dtype=np.float64)
        inertia = np.zeros((3, 3), dtype=np.float64)
    else:
        s_vec = v0 + v1 + v2  # (M, 3)
        cg = np.sum(tet_vol[:, None] * s_vec, axis=0) / (4.0 * vol_mm3)

        # Exact tetrahedral covariance matrix C = integral(x x^T dV) about origin:
        # C_tet = (V_tet / 20) * (v0 v0^T + v1 v1^T + v2 v2^T + s s^T)
        w = tet_vol / 20.0
        cov_origin = (
            np.einsum("m,mi,mj->ij", w, v0, v0)
            + np.einsum("m,mi,mj->ij", w, v1, v1)
            + np.einsum("m,mi,mj->ij", w, v2, v2)
            + np.einsum("m,mi,mj->ij", w, s_vec, s_vec)
        )
        # Parallel-axis shift to CG
        cov_cg = cov_origin - vol_mm3 * np.outer(cg, cg)
        # Convert density kg/m^3 -> kg/mm^3 (1e-9)
        rho_mm3 = rho * 1e-9
        trace_c = float(np.trace(cov_cg))
        inertia = rho_mm3 * (trace_c * np.eye(3) - cov_cg)

    mass_kg = vol_mm3 * 1e-9 * rho
    bmin, bmax = mesh.bbox()
    ext = (bmax[0] - bmin[0], bmax[1] - bmin[1], bmax[2] - bmin[2])

    return MassProperties(
        material=mat,
        density_kg_m3=rho,
        volume_mm3=vol_mm3,
        volume_cm3=vol_mm3 * 1e-3,
        surface_area_mm2=surf_area,
        mass_kg=mass_kg,
        cg_mm=(float(cg[0]), float(cg[1]), float(cg[2])),
        inertia_kg_mm2=(
            float(inertia[0, 0]),
            float(inertia[1, 1]),
            float(inertia[2, 2]),
            float(inertia[0, 1]),
            float(inertia[0, 2]),
            float(inertia[1, 2]),
        ),
        bbox_min_mm=bmin,
        bbox_max_mm=bmax,
        extents_mm=ext,
    )


# ---------------------------------------------------------------------------
# Basic Primitives
# ---------------------------------------------------------------------------
def make_box(
    dx: float,
    dy: float,
    dz: float,
    *,
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str = "box",
    material: str = "316LN",
) -> SolidMesh:
    """Create a watertight axis-aligned box centered at ``center``."""
    if dx <= 0.0 or dy <= 0.0 or dz <= 0.0:
        raise ValueError(f"Box dimensions must be positive: {(dx, dy, dz)}")
    hx, hy, hz = dx / 2.0, dy / 2.0, dz / 2.0
    v = np.array(
        [
            [-hx, -hy, -hz],
            [hx, -hy, -hz],
            [hx, hy, -hz],
            [-hx, hy, -hz],
            [-hx, -hy, hz],
            [hx, -hy, hz],
            [hx, hy, hz],
            [-hx, hy, hz],
        ],
        dtype=np.float64,
    ) + np.asarray(center, dtype=np.float64)
    f = np.array(
        [
            [0, 2, 1], [0, 3, 2],  # -z
            [4, 5, 6], [4, 6, 7],  # +z
            [0, 1, 5], [0, 5, 4],  # -y
            [2, 3, 7], [2, 7, 6],  # +y
            [1, 2, 6], [1, 6, 5],  # +x
            [3, 0, 4], [3, 4, 7],  # -x
        ],
        dtype=np.int32,
    )
    return SolidMesh(vertices=v, faces=f, name=name, material=material)


def make_chamfered_box(
    dx: float,
    dy: float,
    dz: float,
    chamfer: float = 1.0,
    *,
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str = "chamfered_box",
    material: str = "316LN",
) -> SolidMesh:
    """Create a watertight box with 45-degree Z-edge vertical chamfers."""
    if chamfer <= 0.0:
        return make_box(dx, dy, dz, center=center, name=name, material=material)
    c = min(float(chamfer), 0.45 * min(dx, dy))
    hx, hy = dx / 2.0, dy / 2.0
    poly = [
        (-hx + c, -hy),
        (hx - c, -hy),
        (hx, -hy + c),
        (hx, hy - c),
        (hx - c, hy),
        (-hx + c, hy),
        (-hx, hy - c),
        (-hx, -hy + c),
    ]
    return make_plate_with_holes(
        outer_poly_2d=poly,
        holes_2d=[],
        thickness=dz,
        center=center,
        name=name,
        material=material,
    )


def make_frustum(
    r_bot: float,
    r_top: float,
    height: float,
    *,
    segments: int = 48,
    axis: str | Sequence[float] = "z",
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str = "frustum",
    material: str = "316LN",
) -> SolidMesh:
    """Create a watertight cylinder or conical frustum along ``axis``."""
    if height <= 0.0 or r_bot <= 0.0 or r_top <= 0.0 or segments < 3:
        raise ValueError("Invalid frustum dimensions or segments")
    hz = height / 2.0
    th = np.linspace(0.0, 2.0 * math.pi, segments, endpoint=False)
    ct, st = np.cos(th), np.sin(th)
    v = np.zeros((2 + 2 * segments, 3), dtype=np.float64)
    v[0] = [0.0, 0.0, -hz]
    v[1] = [0.0, 0.0, hz]
    v[2 : 2 + segments, 0] = r_bot * ct
    v[2 : 2 + segments, 1] = r_bot * st
    v[2 : 2 + segments, 2] = -hz
    v[2 + segments :, 0] = r_top * ct
    v[2 + segments :, 1] = r_top * st
    v[2 + segments :, 2] = hz

    b0, t0 = 2, 2 + segments
    faces: list[list[int]] = []
    for i in range(segments):
        j = (i + 1) % segments
        faces.append([0, b0 + j, b0 + i])
        faces.append([1, t0 + i, t0 + j])
        faces.append([b0 + i, b0 + j, t0 + j])
        faces.append([b0 + i, t0 + j, t0 + i])
    v_out = _orient_and_place(v, axis=axis, center=center)
    return SolidMesh(
        vertices=v_out,
        faces=np.asarray(faces, dtype=np.int32),
        name=name,
        material=material,
    )


def make_cylinder(
    radius: float,
    height: float,
    *,
    segments: int = 48,
    axis: str | Sequence[float] = "z",
    center: Sequence[float] = (0.0, 0.0, 0.0),
    r_top: float | None = None,
    name: str = "cylinder",
    material: str = "316LN",
) -> SolidMesh:
    """Create a watertight solid cylinder (or tapered frustum if ``r_top`` given)."""
    rt = radius if r_top is None else r_top
    return make_frustum(
        r_bot=radius,
        r_top=rt,
        height=height,
        segments=segments,
        axis=axis,
        center=center,
        name=name,
        material=material,
    )


def make_tube(
    r_in: float,
    r_out: float,
    height: float,
    *,
    segments: int = 48,
    axis: str | Sequence[float] = "z",
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str = "tube",
    material: str = "316LN",
) -> SolidMesh:
    """Create a watertight hollow cylindrical tube along ``axis``."""
    if r_in <= 0.0 or r_out <= r_in or height <= 0.0 or segments < 3:
        raise ValueError(f"Invalid tube params: r_in={r_in}, r_out={r_out}, h={height}")
    hz = height / 2.0
    th = np.linspace(0.0, 2.0 * math.pi, segments, endpoint=False)
    ct, st = np.cos(th), np.sin(th)
    n = segments
    bo = np.column_stack([r_out * ct, r_out * st, np.full(n, -hz)])
    to = np.column_stack([r_out * ct, r_out * st, np.full(n, hz)])
    bi = np.column_stack([r_in * ct, r_in * st, np.full(n, -hz)])
    ti = np.column_stack([r_in * ct, r_in * st, np.full(n, hz)])
    v = np.vstack([bo, to, bi, ti])
    faces: list[list[int]] = []
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, n + j])
        faces.append([i, n + j, n + i])
        faces.append([2 * n + j, 2 * n + i, 3 * n + i])
        faces.append([2 * n + j, 3 * n + i, 3 * n + j])
        faces.append([n + i, n + j, 3 * n + j])
        faces.append([n + i, 3 * n + j, 3 * n + i])
        faces.append([j, i, 2 * n + i])
        faces.append([j, 2 * n + i, 2 * n + j])
    v_out = _orient_and_place(v, axis=axis, center=center)
    return SolidMesh(
        vertices=v_out,
        faces=np.asarray(faces, dtype=np.int32),
        name=name,
        material=material,
    )


def make_sphere(
    radius: float,
    *,
    u_seg: int = 32,
    v_seg: int = 16,
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str = "sphere",
    material: str = "Sapphire",
) -> SolidMesh:
    """Create a watertight UV sphere (for sapphire centering balls, lenses, etc.)."""
    if radius <= 0.0 or u_seg < 6 or v_seg < 4:
        raise ValueError("Invalid sphere parameters")
    profile: list[tuple[float, float]] = []
    for k in range(v_seg + 1):
        phi = -0.5 * math.pi + math.pi * (k / v_seg)
        r = 0.0 if (k == 0 or k == v_seg) else radius * math.cos(phi)
        z = radius * math.sin(phi)
        profile.append((r, z))
    return make_revolved_profile(
        profile, segments=u_seg, center=center, name=name, material=material
    )


# ---------------------------------------------------------------------------
# Axisymmetric Revolved Profile Solids (Electrodes, Hemispheres, Bellows)
# ---------------------------------------------------------------------------
def _poly2d_signed_area(pts: Sequence[tuple[float, float]]) -> float:
    n = len(pts)
    area2 = 0.0
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        area2 += x0 * y1 - x1 * y0
    return 0.5 * area2


def make_revolved_profile(
    profile_rz: Sequence[tuple[float, float]],
    *,
    segments: int = 64,
    axis: str | Sequence[float] = "z",
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str = "revolved_solid",
    material: str = "316LN",
) -> SolidMesh:
    """Revolve a closed 2D ``(r, z)`` profile (``r >= 0``) 360 deg around ``axis``.

    Supports BOTH:
    - Annular closed contours (all ``r > 0``): hollow tubes, stepped electrodes,
      edge-welded bellows convolutions, lenses, rings.
    - Axis-touching contours (points with ``r == 0``): closed domes, hemispheres,
      solid stepped shafts, blank flanges, closed-bottom Meissner cups.
    Automatically normalizes profile winding to CCW in the ``(r, z)`` plane so
    normals are guaranteed strictly outward.
    """
    if segments < 6:
        raise ValueError("segments must be >= 6")
    raw = [(float(r), float(z)) for r, z in profile_rz]
    if len(raw) < 3:
        raise ValueError("profile_rz must contain at least 3 points")

    # Remove consecutive duplicate vertices
    pts: list[tuple[float, float]] = []
    for p in raw:
        if p[0] < -1e-9:
            raise ValueError(f"Revolved profile radius cannot be negative: r={p[0]}")
        rp = 0.0 if abs(p[0]) <= 1e-12 else p[0]
        if not pts or (abs(pts[-1][0] - rp) > 1e-12 or abs(pts[-1][1] - p[1]) > 1e-12):
            pts.append((rp, p[1]))
    if len(pts) >= 2 and abs(pts[0][0] - pts[-1][0]) <= 1e-12 and abs(pts[0][1] - pts[-1][1]) <= 1e-12:
        pts.pop()
    if len(pts) < 3:
        raise ValueError("Degenerate revolved profile after deduplication")

    area = _poly2d_signed_area(pts)
    if abs(area) < 1e-14:
        raise ValueError("Revolved profile has zero cross-sectional area")
    if area < 0.0:
        pts = list(reversed(pts))

    th = np.linspace(0.0, 2.0 * math.pi, segments, endpoint=False)
    ct, st = np.cos(th), np.sin(th)

    verts: list[list[float]] = []
    ring_map: list[tuple[bool, int]] = []  # (is_pole, base_vertex_index)
    for r, z in pts:
        if r <= 1e-12:
            ring_map.append((True, len(verts)))
            verts.append([0.0, 0.0, z])
        else:
            ring_map.append((False, len(verts)))
            for i in range(segments):
                verts.append([r * float(ct[i]), r * float(st[i]), z])

    faces: list[list[int]] = []
    m = len(pts)
    for p in range(m):
        q = (p + 1) % m
        p_pole, p_base = ring_map[p]
        q_pole, q_base = ring_map[q]
        if p_pole and q_pole:
            # Segment lies along the internal symmetry axis -> no exterior face
            continue
        if p_pole and not q_pole:
            for i in range(segments):
                j = (i + 1) % segments
                faces.append([p_base, q_base + j, q_base + i])
        elif not p_pole and q_pole:
            for i in range(segments):
                j = (i + 1) % segments
                faces.append([p_base + i, p_base + j, q_base])
        else:
            for i in range(segments):
                j = (i + 1) % segments
                faces.append([p_base + i, p_base + j, q_base + j])
                faces.append([p_base + i, q_base + j, q_base + i])

    v_arr = _orient_and_place(np.asarray(verts, dtype=np.float64), axis=axis, center=center)
    return SolidMesh(
        vertices=v_arr,
        faces=np.asarray(faces, dtype=np.int32),
        name=name,
        material=material,
    )


def make_bellows(
    r_in: float,
    r_out: float,
    length: float,
    n_convolutions: int,
    *,
    wall_thickness: float = 0.15,
    end_cuff_mm: float = 3.0,
    segments: int = 48,
    axis: str | Sequence[float] = "z",
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str = "bellows",
    material: str = "316L",
) -> SolidMesh:
    """Create a watertight thin-walled edge-welded bellows with exact convolutions.

    Geometry has strictly parallel inner and outer convolution flanks so the wall
    never self-intersects for any valid ``r_in < r_out``, ``n_convolutions >= 1``.
    """
    if r_in <= 0.0 or r_out <= r_in:
        raise ValueError("Bellows requires 0 < r_in < r_out")
    if n_convolutions < 1 or length <= 0.0:
        raise ValueError("Bellows requires n_convolutions >= 1 and length > 0")

    cuff = min(max(float(end_cuff_mm), 0.0), 0.2 * length)
    active_len = length - 2.0 * cuff
    if active_len <= 0.0:
        raise ValueError("Bellows length too short for end cuffs")

    t_eff = min(max(float(wall_thickness), 0.05), 0.30 * (r_out - r_in))
    pitch = active_len / float(n_convolutions)
    z_bot = -0.5 * length
    z_start = z_bot + cuff
    z_end = z_start + active_len
    z_top = 0.5 * length

    outer_pts: list[tuple[float, float]] = []
    inner_pts: list[tuple[float, float]] = []

    if cuff > 0.0:
        outer_pts.append((r_in + t_eff, z_bot))
        inner_pts.append((r_in, z_bot))

    for k in range(n_convolutions):
        z0 = z_start + k * pitch
        zm = z0 + 0.5 * pitch
        z1 = z0 + pitch
        outer_pts.extend(
            [
                (r_in + t_eff, z0 + 0.08 * pitch),
                (r_out, zm - 0.12 * pitch),
                (r_out, zm + 0.12 * pitch),
                (r_in + t_eff, z1 - 0.08 * pitch),
            ]
        )
        inner_pts.extend(
            [
                (r_in, z0 + 0.14 * pitch),
                (r_out - t_eff, zm - 0.06 * pitch),
                (r_out - t_eff, zm + 0.06 * pitch),
                (r_in, z1 - 0.14 * pitch),
            ]
        )

    if cuff > 0.0:
        outer_pts.append((r_in + t_eff, z_top))
        inner_pts.append((r_in, z_top))
    else:
        # Cleanly close ends at z_start and z_end
        outer_pts.insert(0, (r_in + t_eff, z_start))
        outer_pts.append((r_in + t_eff, z_end))
        inner_pts.insert(0, (r_in, z_start))
        inner_pts.append((r_in, z_end))

    profile = outer_pts + list(reversed(inner_pts))
    return make_revolved_profile(
        profile, segments=segments, axis=axis, center=center, name=name, material=material
    )


def make_hemisphere_shell(
    r_in: float,
    r_out: float,
    *,
    segments: int = 64,
    lat_steps: int = 20,
    polar_hole_deg: float = 0.0,
    axis: str | Sequence[float] = "z",
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str = "hemisphere_shell",
    material: str = "Ti-6Al-4V",
) -> SolidMesh:
    """Create a watertight hollow hemispherical shell (e.g. HDA-HiRes R0=40 mm electrodes).

    Equatorial base sits at local ``z = 0``, dome rises to ``+z = r_out``.
    If ``polar_hole_deg > 0``, leaves an axial circular aperture at the apex.
    """
    if r_in <= 0.0 or r_out <= r_in:
        raise ValueError("Hemisphere shell requires 0 < r_in < r_out")
    if lat_steps < 4:
        raise ValueError("lat_steps must be >= 4")
    phi_max = 0.5 * math.pi - math.radians(max(0.0, polar_hole_deg))
    phis = np.linspace(0.0, phi_max, lat_steps + 1)

    outer: list[tuple[float, float]] = []
    for k, phi in enumerate(phis):
        is_pole = (polar_hole_deg <= 0.0) and (k == lat_steps)
        r = 0.0 if is_pole else r_out * math.cos(float(phi))
        z = r_out * math.sin(float(phi))
        outer.append((r, z))

    inner: list[tuple[float, float]] = []
    for k, phi in enumerate(reversed(phis)):
        is_pole = (polar_hole_deg <= 0.0) and (k == 0)
        r = 0.0 if is_pole else r_in * math.cos(float(phi))
        z = r_in * math.sin(float(phi))
        inner.append((r, z))

    return make_revolved_profile(
        outer + inner,
        segments=segments,
        axis=axis,
        center=center,
        name=name,
        material=material,
    )


# ---------------------------------------------------------------------------
# 2D Contour Helpers & Polygon-with-Holes Ear-Clipping Engine (Eberly Bridge)
# ---------------------------------------------------------------------------
def rect_2d(
    dx: float,
    dy: float,
    *,
    cx: float = 0.0,
    cy: float = 0.0,
    ccw: bool = True,
) -> list[tuple[float, float]]:
    hx, hy = dx / 2.0, dy / 2.0
    pts = [
        (cx - hx, cy - hy),
        (cx + hx, cy - hy),
        (cx + hx, cy + hy),
        (cx - hx, cy + hy),
    ]
    return pts if ccw else list(reversed(pts))


def circle_2d(
    radius: float,
    *,
    cx: float = 0.0,
    cy: float = 0.0,
    segments: int = 24,
    ccw: bool = True,
    start_angle_deg: float = 0.0,
) -> list[tuple[float, float]]:
    a0 = math.radians(start_angle_deg)
    th = np.linspace(a0, a0 + 2.0 * math.pi, segments, endpoint=False)
    pts = [(cx + radius * float(math.cos(t)), cy + radius * float(math.sin(t))) for t in th]
    return pts if ccw else list(reversed(pts))


def slot_2d(
    length: float,
    width: float,
    *,
    cx: float = 0.0,
    cy: float = 0.0,
    angle_deg: float = 0.0,
    arc_seg: int = 8,
    ccw: bool = True,
) -> list[tuple[float, float]]:
    """Stadium/obround 2D slot contour of overall ``length >= width``."""
    r = width / 2.0
    half_straight = max(0.0, (length - width) / 2.0)
    local: list[tuple[float, float]] = []
    # Right semicircle (-pi/2 .. +pi/2)
    for i in range(arc_seg + 1):
        a = -0.5 * math.pi + math.pi * (i / arc_seg)
        local.append((half_straight + r * math.cos(a), r * math.sin(a)))
    # Left semicircle (+pi/2 .. 3*pi/2)
    for i in range(arc_seg + 1):
        a = 0.5 * math.pi + math.pi * (i / arc_seg)
        local.append((-half_straight + r * math.cos(a), r * math.sin(a)))
    # Remove accidental duplicates when half_straight == 0
    dedup: list[tuple[float, float]] = []
    for p in local:
        if not dedup or math.hypot(p[0] - dedup[-1][0], p[1] - dedup[-1][1]) > 1e-10:
            dedup.append(p)
    if len(dedup) >= 2 and math.hypot(dedup[0][0] - dedup[-1][0], dedup[0][1] - dedup[-1][1]) <= 1e-10:
        dedup.pop()
    rad = math.radians(angle_deg)
    ca, sa = math.cos(rad), math.sin(rad)
    pts = [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in dedup]
    return pts if ccw else list(reversed(pts))


def _cross2d(
    a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]
) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _point_in_triangle_2d(
    p: tuple[float, float],
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    eps: float = 1e-12,
) -> bool:
    c1 = _cross2d(a, b, p)
    c2 = _cross2d(b, c, p)
    c3 = _cross2d(c, a, p)
    return (c1 >= -eps) and (c2 >= -eps) and (c3 >= -eps)


def _splice_hole_eberly(
    poly_indices: list[int],
    hole_indices: list[int],
    coords: list[tuple[float, float]],
) -> list[int]:
    """Splice one CW hole into a CCW outer loop using Eberly's mutually-visible bridge."""
    # Find rightmost vertex M of hole
    m_pos = max(range(len(hole_indices)), key=lambda i: (coords[hole_indices[i]][0], coords[hole_indices[i]][1]))
    m_idx = hole_indices[m_pos]
    mx, my = coords[m_idx]

    # Cast +x ray from M against all edges of poly_indices
    best_x = float("inf")
    best_edge_pos = -1
    hit_is_vertex = False
    hit_vertex_pos = -1

    n = len(poly_indices)
    for i in range(n):
        j = (i + 1) % n
        a_idx, b_idx = poly_indices[i], poly_indices[j]
        ax, ay = coords[a_idx]
        bx, by = coords[b_idx]

        # Skip edges completely left of M or not crossing y = my
        if max(ax, bx) < mx - 1e-12:
            continue
        if (ay > my and by > my) or (ay < my and by < my):
            continue

        if abs(ay - by) <= 1e-13:
            # Horizontal edge at y == my
            if abs(ay - my) <= 1e-12:
                for pos_c, cx_val in ((i, ax), (j, bx)):
                    if cx_val >= mx - 1e-12 and cx_val < best_x:
                        best_x = cx_val
                        best_edge_pos = i
                        hit_is_vertex = True
                        hit_vertex_pos = pos_c
            continue

        # Only consider downward/upward crossings where edge lies on right of interior
        t = (my - ay) / (by - ay)
        if t < -1e-12 or t > 1.0 + 1e-12:
            continue
        ix = ax + t * (bx - ax)
        if ix < mx - 1e-12:
            continue

        if ix < best_x - 1e-12:
            best_x = ix
            best_edge_pos = i
            if t <= 1e-12:
                hit_is_vertex = True
                hit_vertex_pos = i
            elif t >= 1.0 - 1e-12:
                hit_is_vertex = True
                hit_vertex_pos = j
            else:
                hit_is_vertex = False
                hit_vertex_pos = -1
        elif abs(ix - best_x) <= 1e-12 and t <= 1e-12:
            # Prefer a vertex hit when ray passes directly through a vertex
            # Choose the edge whose outgoing/incoming side actually opens toward M
            prev_i = (i - 1) % n
            if _cross2d(coords[poly_indices[prev_i]], (ax, ay), (bx, by)) < 0.0 or ay == my:
                hit_is_vertex = True
                hit_vertex_pos = i
                best_edge_pos = i

    if best_edge_pos < 0:
        raise ValueError("Hole appears to lie outside the outer polygon boundary")

    if hit_is_vertex:
        p_pos = hit_vertex_pos
    else:
        i0 = best_edge_pos
        i1 = (best_edge_pos + 1) % n
        p_pos = i0 if coords[poly_indices[i0]][0] >= coords[poly_indices[i1]][0] else i1
        ix_pt = (best_x, my)
        p_pt = coords[poly_indices[p_pos]]

        # Check all reflex vertices inside triangle (M, I, P)
        # Ensure triangle (M, I, P) is oriented CCW for point-in-triangle test
        t_a, t_b, t_c = (mx, my), ix_pt, p_pt
        if _cross2d(t_a, t_b, t_c) < 0.0:
            t_b, t_c = t_c, t_b

        best_reflex_pos = -1
        best_angle = float("inf")
        best_dist = float("inf")
        for k in range(n):
            if k == p_pos:
                continue
            r_idx = poly_indices[k]
            if r_idx == poly_indices[p_pos]:
                continue
            rp = coords[r_idx]
            prev_p = coords[poly_indices[(k - 1) % n]]
            next_p = coords[poly_indices[(k + 1) % n]]
            # Reflex vertex in CCW polygon has cross <= 0
            if _cross2d(prev_p, rp, next_p) > 1e-12:
                continue
            if _point_in_triangle_2d(rp, t_a, t_b, t_c, eps=1e-12):
                dx = rp[0] - mx
                dy = rp[1] - my
                dist = math.hypot(dx, dy)
                if dist <= 1e-12:
                    continue
                ang = abs(math.atan2(dy, dx))
                if (ang < best_angle - 1e-12) or (abs(ang - best_angle) <= 1e-12 and dist < best_dist):
                    best_angle = ang
                    best_dist = dist
                    best_reflex_pos = k
        if best_reflex_pos >= 0:
            p_pos = best_reflex_pos

    # If the chosen vertex p_idx already appears multiple times in poly_indices (due to prior bridges),
    # pick the occurrence whose angular sector contains the ray from P to M!
    target_p_idx = poly_indices[p_pos]
    occurrences = [k for k, vid in enumerate(poly_indices) if vid == target_p_idx]
    if len(occurrences) > 1:
        p_pt = coords[target_p_idx]
        m_pt = (mx, my)
        chosen = p_pos
        for k in occurrences:
            prev_pt = coords[poly_indices[(k - 1) % n]]
            next_pt = coords[poly_indices[(k + 1) % n]]
            # Check if ray P->M lies strictly inside local CCW sector (prev -> P -> next)
            c_turn = _cross2d(prev_pt, p_pt, next_pt)
            c1 = _cross2d(prev_pt, p_pt, m_pt)
            c2 = _cross2d(p_pt, next_pt, m_pt)
            if c_turn >= 0.0:
                if c1 >= -1e-12 and c2 >= -1e-12:
                    chosen = k
                    break
            else:
                if c1 >= -1e-12 or c2 >= -1e-12:
                    chosen = k
                    break
        p_pos = chosen

    # Rotate hole list to start at m_pos
    rotated_hole = hole_indices[m_pos:] + hole_indices[:m_pos]
    # Splice: ... P, M, hole..., M, P ...
    return (
        poly_indices[: p_pos + 1]
        + rotated_hole
        + [m_idx, poly_indices[p_pos]]
        + poly_indices[p_pos + 1 :]
    )


def triangulate_polygon_with_holes(
    outer_poly: Sequence[tuple[float, float]],
    holes: Sequence[Sequence[tuple[float, float]]] = (),
) -> tuple[list[tuple[float, float]], list[tuple[int, int, int]], list[int], list[list[int]]]:
    """Triangulate a simple 2D polygon with disjoint simple holes via Eberly ear-clipping.

    Returns ``(coords, triangles, outer_indices_ccw, hole_indices_cw_list)``.
    Every emitted triangle is CCW in XY and references ONLY original unique vertex IDs.
    """
    outer = [(float(x), float(y)) for x, y in outer_poly]
    if len(outer) < 3:
        raise ValueError("Outer polygon must have at least 3 vertices")
    if _poly2d_signed_area(outer) < 0.0:
        outer = list(reversed(outer))

    coords: list[tuple[float, float]] = list(outer)
    outer_indices = list(range(len(outer)))

    hole_idx_lists: list[list[int]] = []
    for h in holes:
        hpts = [(float(x), float(y)) for x, y in h]
        if len(hpts) < 3:
            raise ValueError("Each hole polygon must have at least 3 vertices")
        if _poly2d_signed_area(hpts) > 0.0:
            hpts = list(reversed(hpts))  # Holes must be CW
        base = len(coords)
        coords.extend(hpts)
        hole_idx_lists.append(list(range(base, base + len(hpts))))

    # Sort holes by descending max X for bridge insertion
    ordered_holes = sorted(
        hole_idx_lists,
        key=lambda hl: max(coords[i][0] for i in hl),
        reverse=True,
    )

    loop = list(outer_indices)
    for hl in ordered_holes:
        loop = _splice_hole_eberly(loop, hl, coords)

    # Ear-clipping loop
    triangles: list[tuple[int, int, int]] = []
    guard = 0
    max_iters = len(loop) * len(loop) + 100

    while len(loop) > 3:
        guard += 1
        if guard > max_iters:
            raise RuntimeError("Ear-clipping failed to converge (check non-overlapping holes)")

        clipped = False
        n = len(loop)
        # First pass: strict convex ears with positive area; fallback pass allows collinear cleanup
        for allow_collinear in (False, True):
            for i in range(n):
                ia = loop[(i - 1) % n]
                ib = loop[i]
                ic = loop[(i + 1) % n]
                if ia == ib or ib == ic or ia == ic:
                    loop.pop(i)
                    clipped = True
                    break
                a, b, c = coords[ia], coords[ib], coords[ic]
                area2 = _cross2d(a, b, c)
                if not allow_collinear and area2 <= 1e-13:
                    continue
                if allow_collinear and area2 < -1e-13:
                    continue

                if area2 <= 1e-13:
                    # Collinear zero-area vertex on bridge -> prune without emitting degenerate tri
                    loop.pop(i)
                    clipped = True
                    break

                # Ensure no other vertex of the loop lies inside triangle (a, b, c)
                contains_other = False
                for k in range(n):
                    ik = loop[k]
                    if ik == ia or ik == ib or ik == ic:
                        continue
                    pk = coords[ik]
                    # Also skip coincident coordinates at bridge vertices
                    if pk == a or pk == b or pk == c:
                        continue
                    if _point_in_triangle_2d(pk, a, b, c, eps=1e-12):
                        contains_other = True
                        break
                if not contains_other:
                    triangles.append((ia, ib, ic))
                    loop.pop(i)
                    clipped = True
                    break
            if clipped:
                break

        if not clipped:
            raise RuntimeError(
                "No valid ear found during 2D polygon triangulation (check self-intersection)"
            )

    if len(loop) == 3:
        ia, ib, ic = loop
        if ia != ib and ib != ic and ia != ic:
            if _cross2d(coords[ia], coords[ib], coords[ic]) > 1e-13:
                triangles.append((ia, ib, ic))

    return coords, triangles, outer_indices, hole_idx_lists


def make_plate_with_holes(
    outer_poly_2d: Sequence[tuple[float, float]],
    holes_2d: Sequence[Sequence[tuple[float, float]]] = (),
    thickness: float = 5.0,
    *,
    axis: str | Sequence[float] = "z",
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str = "plate_with_holes",
    material: str = "316LN",
) -> SolidMesh:
    """Extrude an arbitrary 2D polygon with arbitrary through-holes/slots into a watertight solid."""
    if thickness <= 0.0:
        raise ValueError(f"Plate thickness must be > 0, got {thickness}")
    coords, tris, outer_idx, hole_lists = triangulate_polygon_with_holes(
        outer_poly_2d, holes_2d
    )
    n = len(coords)
    hz = thickness / 2.0
    v_bot = np.array([[x, y, -hz] for x, y in coords], dtype=np.float64)
    v_top = np.array([[x, y, hz] for x, y in coords], dtype=np.float64)
    verts = np.vstack([v_bot, v_top])

    faces: list[list[int]] = []
    # Top (+z) and bottom (-z) caps
    for a, b, c in tris:
        faces.append([n + a, n + b, n + c])
        faces.append([a, c, b])

    # Outer wall (CCW outer -> outward normals)
    mo = len(outer_idx)
    for k in range(mo):
        u = outer_idx[k]
        w = outer_idx[(k + 1) % mo]
        faces.append([u, w, n + w])
        faces.append([u, n + w, n + u])

    # Hole walls (CW hole -> normals point inward into hole = outward from solid)
    for hl in hole_lists:
        mh = len(hl)
        for k in range(mh):
            u = hl[k]
            w = hl[(k + 1) % mh]
            faces.append([u, w, n + w])
            faces.append([u, n + w, n + u])

    v_out = _orient_and_place(verts, axis=axis, center=center)
    return SolidMesh(
        vertices=v_out,
        faces=np.asarray(faces, dtype=np.int32),
        name=name,
        material=material,
    )


def make_rect_plate_with_features(
    dx: float,
    dy: float,
    thickness: float,
    *,
    circular_holes: Sequence[tuple[float, float, float]] = (),  # (cx, cy, diameter)
    rect_slots: Sequence[tuple[float, float, float, float, float]] = (),  # (cx, cy, length, width, angle_deg)
    hole_segments: int = 16,
    axis: str | Sequence[float] = "z",
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str = "featured_plate",
    material: str = "316LN",
) -> SolidMesh:
    """Create a rectangular plate with arbitrary circular holes and obround slots."""
    outer = rect_2d(dx, dy, ccw=True)
    holes: list[list[tuple[float, float]]] = []
    for cx, cy, diam in circular_holes:
        holes.append(circle_2d(diam / 2.0, cx=cx, cy=cy, segments=hole_segments, ccw=False))
    for cx, cy, length, width, ang in rect_slots:
        holes.append(slot_2d(length, width, cx=cx, cy=cy, angle_deg=ang, ccw=False))
    return make_plate_with_holes(
        outer, holes, thickness=thickness, axis=axis, center=center, name=name, material=material
    )


def make_counterbored_plate(
    outer_poly_2d: Sequence[tuple[float, float]],
    counterbored_holes: Sequence[tuple[float, float, float, float]],  # (cx, cy, thru_diam, cbore_diam)
    total_thickness: float,
    cbore_depth: float,
    *,
    plain_holes_2d: Sequence[Sequence[tuple[float, float]]] = (),
    hole_segments: int = 16,
    axis: str | Sequence[float] = "z",
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str = "counterbored_plate",
    material: str = "316LN",
) -> SolidMesh:
    """Create a single-shell watertight plate with real stepped counterbored pockets."""
    if total_thickness <= 0.0 or cbore_depth <= 0.0 or cbore_depth >= total_thickness:
        raise ValueError("Require 0 < cbore_depth < total_thickness")

    hz = total_thickness / 2.0
    z_bot = -hz
    z_top = hz
    z_step = z_top - cbore_depth

    bot_holes: list[list[tuple[float, float]]] = [list(h) for h in plain_holes_2d]
    top_holes: list[list[tuple[float, float]]] = [list(h) for h in plain_holes_2d]
    n_plain = len(plain_holes_2d)

    for cx, cy, d_thru, d_cbore in counterbored_holes:
        if d_thru <= 0.0 or d_cbore <= d_thru:
            raise ValueError("Counterbore requires 0 < thru_diam < cbore_diam")
        bot_holes.append(circle_2d(d_thru / 2.0, cx=cx, cy=cy, segments=hole_segments, ccw=False))
        top_holes.append(circle_2d(d_cbore / 2.0, cx=cx, cy=cy, segments=hole_segments, ccw=False))

    b_coords, b_tris, b_outer, b_hlists = triangulate_polygon_with_holes(outer_poly_2d, bot_holes)
    t_coords, t_tris, t_outer, t_hlists = triangulate_polygon_with_holes(outer_poly_2d, top_holes)

    verts: list[list[float]] = []
    # 1) Bottom vertices at z_bot
    b_off = len(verts)
    for x, y in b_coords:
        verts.append([x, y, z_bot])
    # 2) Top vertices at z_top
    t_off = len(verts)
    for x, y in t_coords:
        verts.append([x, y, z_top])
    # 3) Step vertices for each counterbored hole at z_step (thru ring + cbore ring)
    step_thru_rings: list[list[int]] = []
    step_cbore_rings: list[list[int]] = []
    for k in range(len(counterbored_holes)):
        th_ring: list[int] = []
        for idx in b_hlists[n_plain + k]:
            x, y = b_coords[idx]
            th_ring.append(len(verts))
            verts.append([x, y, z_step])
        step_thru_rings.append(th_ring)

        cb_ring: list[int] = []
        for idx in t_hlists[n_plain + k]:
            x, y = t_coords[idx]
            cb_ring.append(len(verts))
            verts.append([x, y, z_step])
        step_cbore_rings.append(cb_ring)

    faces: list[list[int]] = []
    # Bottom cap (-Z)
    for a, b, c in b_tris:
        faces.append([b_off + a, b_off + c, b_off + b])
    # Top cap (+Z)
    for a, b, c in t_tris:
        faces.append([t_off + a, t_off + b, t_off + c])

    # Outer perimeter wall (b_outer and t_outer have identical order and count)
    mo = len(b_outer)
    for k in range(mo):
        u_b = b_off + b_outer[k]
        w_b = b_off + b_outer[(k + 1) % mo]
        u_t = t_off + t_outer[k]
        w_t = t_off + t_outer[(k + 1) % mo]
        faces.append([u_b, w_b, w_t])
        faces.append([u_b, w_t, u_t])

    # Plain through-hole walls (full height z_bot -> z_top)
    for p_i in range(n_plain):
        b_hl = b_hlists[p_i]
        t_hl = t_hlists[p_i]
        mh = len(b_hl)
        for k in range(mh):
            u_b, w_b = b_off + b_hl[k], b_off + b_hl[(k + 1) % mh]
            u_t, w_t = t_off + t_hl[k], t_off + t_hl[(k + 1) % mh]
            faces.append([u_b, w_b, w_t])
            faces.append([u_b, w_t, u_t])

    # Stepped counterbored holes
    for k in range(len(counterbored_holes)):
        b_hl = b_hlists[n_plain + k]
        t_hl = t_hlists[n_plain + k]
        s_th = step_thru_rings[k]
        s_cb = step_cbore_rings[k]
        mh = len(b_hl)
        for i in range(mh):
            j = (i + 1) % mh
            # Lower thru-bore wall (z_bot -> z_step)
            faces.append([b_off + b_hl[i], b_off + b_hl[j], s_th[j]])
            faces.append([b_off + b_hl[i], s_th[j], s_th[i]])
            # Horizontal counterbore shelf at z_step (facing +Z!)
            # Note: s_th and s_cb are CW around hole -> (s_th[i] -> s_th[j]) is CW,
            # (s_cb[i] - s_th[i]) is +r -> (+r) x (-theta) = -Z, so reverse to face +Z:
            faces.append([s_th[i], s_th[j], s_cb[j]])
            faces.append([s_th[i], s_cb[j], s_cb[i]])
            # Upper counterbore wall (z_step -> z_top)
            faces.append([s_cb[i], s_cb[j], t_off + t_hl[j]])
            faces.append([s_cb[i], t_off + t_hl[j], t_off + t_hl[i]])

    v_out = _orient_and_place(np.asarray(verts, dtype=np.float64), axis=axis, center=center)
    return SolidMesh(
        vertices=v_out,
        faces=np.asarray(faces, dtype=np.int32),
        name=name,
        material=material,
    )


# ---------------------------------------------------------------------------
# Structured Periodic MEMS Grid Plate (32x32 = 1024 Holes in <30 ms!)
# ---------------------------------------------------------------------------
def make_mems_grid_plate(
    width_x: float,
    width_y: float,
    thickness: float,
    *,
    nx: int = 32,
    ny: int = 32,
    pitch_x: float = 0.50,
    pitch_y: float = 0.50,
    hole_diameter: float = 0.30,
    hole_sub_per_side: int = 2,
    outer_diameter: float | None = None,
    axis: str | Sequence[float] = "z",
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str = "mems_grid_plate",
    material: str = "Si",
) -> SolidMesh:
    """Create a watertight high-density periodic hole plate (e.g. 32x32=1024 MEMS array).

    Uses structured shared-edge cell tiling (``4 * hole_sub_per_side`` vertices per hole)
    stitched seamlessly to a rectangular frame (``width_x × width_y``) OR circular wafer
    boundary (if ``outer_diameter`` is given). Fast vectorized NumPy construction.
    """
    if nx < 1 or ny < 1 or thickness <= 0.0:
        raise ValueError("nx, ny must be >= 1 and thickness > 0")
    if hole_diameter <= 0.0 or hole_diameter >= min(pitch_x, pitch_y) * 0.96:
        raise ValueError("hole_diameter must be strictly smaller than pitch")
    m = max(1, int(hole_sub_per_side))
    grid_w = nx * pitch_x
    grid_h = ny * pitch_y
    if outer_diameter is not None:
        r_outer = outer_diameter / 2.0
        diag = math.hypot(grid_w / 2.0, grid_h / 2.0)
        if r_outer <= diag * 1.02:
            raise ValueError(
                f"outer_diameter ({outer_diameter}) must exceed grid diagonal ({2*diag:.3f})"
            )
    else:
        if width_x <= grid_w + 1e-6 or width_y <= grid_h + 1e-6:
            raise ValueError(
                f"Plate ({width_x}x{width_y}) must strictly exceed grid ({grid_w}x{grid_h})"
            )

    hz = thickness / 2.0
    gx0, gy0 = -0.5 * grid_w, -0.5 * grid_h
    r_hole = 0.5 * hole_diameter

    # Build 2D vertices:
    # A) Grid lattice shared boundary nodes:
    #    - Horizontal grid lines: (ny + 1) lines × (nx * m + 1) points
    #    - Vertical internal edge points: (nx + 1) lines × ny × (m - 1) points
    hx_count = nx * m + 1
    vy_inner = m - 1

    xy_list: list[tuple[float, float]] = []

    # Horizontal grid lines (row iy in 0..ny, col ix_sub in 0..nx*m)
    h_idx = np.zeros((ny + 1, hx_count), dtype=np.int32)
    for iy in range(ny + 1):
        y = gy0 + iy * pitch_y
        for ic in range(hx_count):
            x = gx0 + ic * (pitch_x / m)
            h_idx[iy, ic] = len(xy_list)
            xy_list.append((x, y))

    # Vertical intermediate edge nodes (col ix in 0..nx, row iy in 0..ny-1, sub s in 1..m-1)
    v_idx = np.zeros((nx + 1, ny, max(vy_inner, 1)), dtype=np.int32)
    if vy_inner > 0:
        for ix in range(nx + 1):
            x = gx0 + ix * pitch_x
            for iy in range(ny):
                y_base = gy0 + iy * pitch_y
                for s in range(1, m):
                    v_idx[ix, iy, s - 1] = len(xy_list)
                    xy_list.append((x, y_base + s * (pitch_y / m)))

    # Hole rings & per-cell 2D top triangles
    k_ring = 4 * m
    top_tris: list[tuple[int, int, int]] = []
    hole_rings_ccw: list[list[int]] = []

    for iy in range(ny):
        cy = gy0 + (iy + 0.5) * pitch_y
        for ix in range(nx):
            cx = gx0 + (ix + 0.5) * pitch_x
            # Cell outer perimeter in CCW order (k_ring vertices):
            # Bottom (left->right), Right (bot->top), Top (right->left), Left (top->bot)
            cell_outer: list[int] = []
            c0 = ix * m
            # Bottom: c0 .. c0 + m - 1
            for s in range(m):
                cell_outer.append(int(h_idx[iy, c0 + s]))
            # Right: bottom corner (c0 + m), then v_idx[ix+1, iy, 0..m-2]
            cell_outer.append(int(h_idx[iy, c0 + m]))
            for s in range(vy_inner):
                cell_outer.append(int(v_idx[ix + 1, iy, s]))
            # Top: c0 + m down to c0 + 1
            for s in range(m, 0, -1):
                cell_outer.append(int(h_idx[iy + 1, c0 + s]))
            # Left: top corner (c0), then v_idx[ix, iy, m-2..0]
            cell_outer.append(int(h_idx[iy + 1, c0]))
            for s in range(vy_inner - 1, -1, -1):
                cell_outer.append(int(v_idx[ix, iy, s]))

            # Project each perimeter vertex radially onto circle of radius r_hole
            h_ring: list[int] = []
            for oid in cell_outer:
                px, py = xy_list[oid]
                ang = math.atan2(py - cy, px - cx)
                h_ring.append(len(xy_list))
                xy_list.append((cx + r_hole * math.cos(ang), cy + r_hole * math.sin(ang)))
            hole_rings_ccw.append(h_ring)

            # Stitch cell_outer (CCW) to h_ring (CCW) -> top triangles with +Z normal
            for q in range(k_ring):
                qn = (q + 1) % k_ring
                o0, o1 = cell_outer[q], cell_outer[qn]
                hi0, hi1 = h_ring[q], h_ring[qn]
                top_tris.append((o0, o1, hi1))
                top_tris.append((o0, hi1, hi0))

    # Grid outer boundary loop (CCW)
    grid_loop: list[int] = []
    # Bottom: left to right
    for ic in range(hx_count - 1):
        grid_loop.append(int(h_idx[0, ic]))
    # Right: bot to top
    for iy in range(ny):
        grid_loop.append(int(h_idx[iy, hx_count - 1]))
        for s in range(vy_inner):
            grid_loop.append(int(v_idx[nx, iy, s]))
    # Top: right to left
    for ic in range(hx_count - 1, 0, -1):
        grid_loop.append(int(h_idx[ny, ic]))
    # Left: top to bot
    for iy in range(ny, 0, -1):
        grid_loop.append(int(h_idx[iy, 0]))
        for s in range(vy_inner - 1, -1, -1):
            grid_loop.append(int(v_idx[0, iy - 1, s]))

    # Create outer plate boundary matching grid_loop 1-to-1
    outer_loop: list[int] = []
    if outer_diameter is not None:
        r_out = outer_diameter / 2.0
        for gid in grid_loop:
            gx, gy = xy_list[gid]
            ang = math.atan2(gy, gx)
            outer_loop.append(len(xy_list))
            xy_list.append((r_out * math.cos(ang), r_out * math.sin(ang)))
    else:
        sx = width_x / grid_w
        sy = width_y / grid_h
        for gid in grid_loop:
            gx, gy = xy_list[gid]
            outer_loop.append(len(xy_list))
            xy_list.append((gx * sx, gy * sy))

    # Stitch outer border ring (outer_loop CCW, grid_loop CCW inside)
    nb = len(grid_loop)
    for q in range(nb):
        qn = (q + 1) % nb
        o0, o1 = outer_loop[q], outer_loop[qn]
        g0, g1 = grid_loop[q], grid_loop[qn]
        top_tris.append((o0, o1, g1))
        top_tris.append((o0, g1, g0))

    # Build 3D vertices (bottom 0..N-1, top N..2N-1)
    n2 = len(xy_list)
    xy_arr = np.asarray(xy_list, dtype=np.float64)
    v_bot = np.column_stack([xy_arr, np.full(n2, -hz)])
    v_top = np.column_stack([xy_arr, np.full(n2, hz)])
    verts = np.vstack([v_bot, v_top])

    # Vectorized face assembly
    t_arr = np.asarray(top_tris, dtype=np.int32)
    f_top = t_arr + n2
    f_bot = t_arr[:, [0, 2, 1]]

    # Outer vertical wall
    ol = np.asarray(outer_loop, dtype=np.int32)
    ol_next = np.roll(ol, -1)
    f_ow1 = np.column_stack([ol, ol_next, ol_next + n2])
    f_ow2 = np.column_stack([ol, ol_next + n2, ol + n2])

    # Inner hole vertical walls (h_ring is CCW -> reverse edge to face inward into hole!)
    hr = np.asarray(hole_rings_ccw, dtype=np.int32)  # (nx*ny, k_ring)
    hr_next = np.roll(hr, -1, axis=1)
    u = hr_next.ravel()
    w = hr.ravel()
    f_hw1 = np.column_stack([u, w, w + n2])
    f_hw2 = np.column_stack([u, w + n2, u + n2])

    faces = np.vstack([f_top, f_bot, f_ow1, f_ow2, f_hw1, f_hw2])
    v_out = _orient_and_place(verts, axis=axis, center=center)
    return SolidMesh(vertices=v_out, faces=faces, name=name, material=material)


# ---------------------------------------------------------------------------
# Structured Annular Ring / Flange with Bolt Circle (and Optional Inner Profile)
# ---------------------------------------------------------------------------
def make_ring_with_bolt_circle(
    r_in: float,
    r_out: float,
    thickness: float,
    pcd: float,
    n_bolts: int,
    bolt_diameter: float,
    *,
    sub_per_side: int = 3,
    start_angle_deg: float = 0.0,
    r_band_in: float | None = None,
    r_band_out: float | None = None,
    inner_profile_rz: Sequence[tuple[float, float]] | None = None,
    axis: str | Sequence[float] = "z",
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str = "ring_bolt_circle",
    material: str = "316LN",
) -> SolidMesh:
    """Create a watertight annular ring (or blank disk if ``r_in == 0``) with bolt circle.

    Uses exact radial-sector meshing so bolt holes, outer rim, and inner bore/knife-edge
    profile are stitched into ONE single watertight 2-manifold solid.

    If ``inner_profile_rz`` is provided, it must be an open polyline of ``(r, z)`` points
    going from ``(r_band_in, +thickness/2)`` through the front sealing profile, bore or
    center poles, and rear face/weld neck back to ``(r_band_in, -thickness/2)``.
    """
    if r_out <= 0.0 or thickness <= 0.0 or n_bolts < 3:
        raise ValueError("Require r_out > 0, thickness > 0, n_bolts >= 3")
    if r_in < 0.0 or r_in >= r_out:
        raise ValueError(f"Invalid r_in={r_in}, r_out={r_out}")

    r_pcd = 0.5 * pcd
    r_bolt = 0.5 * bolt_diameter
    if r_bolt <= 0.0:
        raise ValueError("bolt_diameter must be > 0")

    dth = 2.0 * math.pi / float(n_bolts)
    # Check bolt hole fits cleanly inside its angular sector
    half_chord = r_pcd * math.sin(0.5 * dth)
    if r_bolt >= 0.94 * half_chord:
        raise ValueError(
            f"Bolt radius ({r_bolt}) too large for {n_bolts} bolts on PCD {pcd}"
        )

    if r_band_in is None:
        inner_limit = max(r_in, 0.0)
        if r_pcd - r_bolt <= inner_limit + 1e-6:
            raise ValueError(
                f"Bolt circle encroaches inner bore: r_pcd-r_bolt={r_pcd-r_bolt:.3f} <= r_in={inner_limit:.3f}"
            )
        r1 = r_pcd - r_bolt - 0.35 * (r_pcd - r_bolt - inner_limit)
    else:
        r1 = float(r_band_in)
        if r1 >= r_pcd - r_bolt - 1e-6:
            raise ValueError(f"r_band_in ({r1}) must be < r_pcd - r_bolt ({r_pcd - r_bolt})")

    if r_band_out is None:
        if r_pcd + r_bolt >= r_out - 1e-6:
            raise ValueError(
                f"Bolt circle exceeds r_out: r_pcd+r_bolt={r_pcd+r_bolt:.3f} >= r_out={r_out:.3f}"
            )
        r2 = r_pcd + r_bolt + 0.35 * (r_out - r_pcd - r_bolt)
    else:
        r2 = float(r_band_out)
        if r2 <= r_pcd + r_bolt + 1e-6 or r2 >= r_out - 1e-6:
            raise ValueError("r_band_out must lie strictly between r_pcd+r_bolt and r_out")

    m = max(2, int(sub_per_side))
    n_ang = n_bolts * m
    hz = 0.5 * thickness
    th0 = math.radians(start_angle_deg) - 0.5 * dth

    # Precompute uniform angular steps around the circle (CCW: index 0..n_ang-1)
    thetas = th0 + np.arange(n_ang, dtype=np.float64) * (2.0 * math.pi / n_ang)
    ct, st = np.cos(thetas), np.sin(thetas)

    verts: list[list[float]] = []

    def _add_ring(rad: float, z: float) -> list[int]:
        base = len(verts)
        for i in range(n_ang):
            verts.append([rad * float(ct[i]), rad * float(st[i]), z])
        return list(range(base, base + n_ang))

    # Shared rings at r1, r2, r_out (bottom and top)
    r1_bot = _add_ring(r1, -hz)
    r1_top = _add_ring(r1, hz)
    r2_bot = _add_ring(r2, -hz)
    r2_top = _add_ring(r2, hz)
    ro_bot = _add_ring(r_out, -hz)
    ro_top = _add_ring(r_out, hz)

    # Shared radial seam vertices between adjacent sectors along theta_seam = thetas[b*m]
    # For each seam b in 0..n_bolts-1, s in 1..m-1 at radius r1 + (s/m)*(r2-r1)
    seam_bot: list[list[int]] = []
    seam_top: list[list[int]] = []
    for b in range(n_bolts):
        ang = float(thetas[b * m])
        ca, sa = math.cos(ang), math.sin(ang)
        sb: list[int] = []
        st_l: list[int] = []
        for s in range(1, m):
            rr = r1 + (s / float(m)) * (r2 - r1)
            sb.append(len(verts))
            verts.append([rr * ca, rr * sa, -hz])
            st_l.append(len(verts))
            verts.append([rr * ca, rr * sa, hz])
        seam_bot.append(sb)
        seam_top.append(st_l)

    faces: list[list[int]] = []

    # 1) Bolt-hole band sectors [r1, r2]
    k_ring = 4 * m
    for b in range(n_bolts):
        b_next = (b + 1) % n_bolts
        ang_c = th0 + (b + 0.5) * dth
        cx, cy = r_pcd * math.cos(ang_c), r_pcd * math.sin(ang_c)

        # Build sector perimeter in CCW order around bolt center (cx, cy):
        # 1. Bottom seam (theta = seam b, r: r1 -> r2): r1[b*m], seam[b][0..m-2]
        # 2. Outer arc (r = r2, theta: seam b -> seam b+1): r2[b*m .. b*m+m-1]
        # 3. Top seam (theta = seam b+1, r: r2 -> r1): r2[b_next*m], seam[b_next][m-2..0]
        # 4. Inner arc (r = r1, theta: seam b+1 -> seam b): r1[b_next*m .. b*m+1]
        perim_bot: list[int] = []
        perim_top: list[int] = []

        # Bottom seam (r1 -> r2)
        perim_bot.append(r1_bot[b * m])
        perim_top.append(r1_top[b * m])
        for s in range(m - 1):
            perim_bot.append(seam_bot[b][s])
            perim_top.append(seam_top[b][s])

        # Outer arc (r2, theta increasing)
        for s in range(m):
            idx = (b * m + s) % n_ang
            perim_bot.append(r2_bot[idx])
            perim_top.append(r2_top[idx])

        # Top seam (r2 -> r1)
        perim_bot.append(r2_bot[b_next * m])
        perim_top.append(r2_top[b_next * m])
        for s in range(m - 2, -1, -1):
            perim_bot.append(seam_bot[b_next][s])
            perim_top.append(seam_top[b_next][s])

        # Inner arc (r1, theta decreasing from b_next*m down to b*m + 1)
        for s in range(m, 0, -1):
            idx = (b * m + s) % n_ang
            perim_bot.append(r1_bot[idx])
            perim_top.append(r1_top[idx])

        # Project each perimeter vertex radially onto bolt circle (cx, cy, r_bolt)
        hole_bot: list[int] = []
        hole_top: list[int] = []
        for pid in perim_top:
            px, py = verts[pid][0], verts[pid][1]
            phi = math.atan2(py - cy, px - cx)
            hx = cx + r_bolt * math.cos(phi)
            hy = cy + r_bolt * math.sin(phi)
            hole_bot.append(len(verts))
            verts.append([hx, hy, -hz])
            hole_top.append(len(verts))
            verts.append([hx, hy, hz])

        for q in range(k_ring):
            qn = (q + 1) % k_ring
            # Top cap (+Z)
            faces.append([perim_top[q], perim_top[qn], hole_top[qn]])
            faces.append([perim_top[q], hole_top[qn], hole_top[q]])
            # Bottom cap (-Z)
            faces.append([perim_bot[q], hole_bot[qn], perim_bot[qn]])
            faces.append([perim_bot[q], hole_bot[q], hole_bot[qn]])
            # Bolt hole inner cylindrical wall (normals point into hole)
            faces.append([hole_bot[qn], hole_bot[q], hole_top[q]])
            faces.append([hole_bot[qn], hole_top[q], hole_top[qn]])

    # 2) Outer rim annulus (r2 -> r_out) + outer cylindrical wall
    for i in range(n_ang):
        j = (i + 1) % n_ang
        # Top (+Z): inner edge is (j -> i), matching bolt sector's (i -> j)!
        faces.append([r2_top[i], ro_top[i], ro_top[j]])
        faces.append([r2_top[i], ro_top[j], r2_top[j]])
        # Outer cylindrical wall (+r)
        faces.append([ro_bot[i], ro_bot[j], ro_top[j]])
        faces.append([ro_bot[i], ro_top[j], ro_top[i]])
        # Bottom (-Z): inner edge is (i -> j), matching bolt sector's (j -> i)!
        faces.append([r2_bot[i], ro_bot[j], ro_bot[i]])
        faces.append([r2_bot[i], r2_bot[j], ro_bot[j]])

    # 3) Inner region (r <= r1): either custom axisymmetric inner_profile_rz or standard bore/blank
    if inner_profile_rz is None:
        if r_in > 1e-9:
            inner_prof = [(r1, hz), (r_in, hz), (r_in, -hz), (r1, -hz)]
        else:
            inner_prof = [(r1, hz), (0.0, hz), (0.0, -hz), (r1, -hz)]
    else:
        inner_prof = [(float(r), float(z)) for r, z in inner_profile_rz]
        if len(inner_prof) < 3:
            raise ValueError("inner_profile_rz must have >= 3 points")

    # Build intermediate rings for inner_prof[1:-1], reusing r1_top at index 0 and r1_bot at index -1
    prof_rings: list[tuple[bool, list[int] | int]] = [(False, r1_top)]
    for r_p, z_p in inner_prof[1:-1]:
        if r_p <= 1e-12:
            p_idx = len(verts)
            verts.append([0.0, 0.0, z_p])
            prof_rings.append((True, p_idx))
        else:
            prof_rings.append((False, _add_ring(r_p, z_p)))
    prof_rings.append((False, r1_bot))

    # Revolve open polyline from r1_top -> ... -> r1_bot
    # Note: going inward along top face (r decreasing, z=+hz), (r1_top[i] -> r1_top[j]) x (inward) = +Z!
    # That matches revolved_profile CCW convention: [p[i], p[j], q[j]] and [p[i], q[j], q[i]]!
    for seg_i in range(len(prof_rings) - 1):
        p_pole, p_ref = prof_rings[seg_i]
        q_pole, q_ref = prof_rings[seg_i + 1]
        if p_pole and q_pole:
            continue
        if p_pole and not q_pole:
            assert isinstance(p_ref, int) and isinstance(q_ref, list)
            for i in range(n_ang):
                j = (i + 1) % n_ang
                faces.append([p_ref, q_ref[j], q_ref[i]])
        elif not p_pole and q_pole:
            assert isinstance(p_ref, list) and isinstance(q_ref, int)
            for i in range(n_ang):
                j = (i + 1) % n_ang
                faces.append([p_ref[i], p_ref[j], q_ref])
        else:
            assert isinstance(p_ref, list) and isinstance(q_ref, list)
            for i in range(n_ang):
                j = (i + 1) % n_ang
                faces.append([p_ref[i], p_ref[j], q_ref[j]])
                faces.append([p_ref[i], q_ref[j], q_ref[i]])

    v_out = _orient_and_place(np.asarray(verts, dtype=np.float64), axis=axis, center=center)
    return SolidMesh(
        vertices=v_out,
        faces=np.asarray(faces, dtype=np.int32),
        name=name,
        material=material,
    )


# ---------------------------------------------------------------------------
# 3D Swept Tubes & Cryo S-Braids (Rotation-Minimizing Bishop Frames)
# ---------------------------------------------------------------------------
def _bishop_frames(pts: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute rotation-minimizing (parallel-transport) frames along 3D polyline ``pts``."""
    n = len(pts)
    tangents = np.zeros((n, 3), dtype=np.float64)
    for i in range(n):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = pts[i + 1] - pts[i - 1]
        nt = float(np.linalg.norm(t))
        if nt < 1e-12:
            raise ValueError("Swept spine contains duplicate consecutive points")
        tangents[i] = t / nt

    normals = np.zeros((n, 3), dtype=np.float64)
    binormals = np.zeros((n, 3), dtype=np.float64)

    # Initial normal perpendicular to tangents[0]
    ref = np.array([0.0, 0.0, 1.0]) if abs(tangents[0, 2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    n0 = np.cross(tangents[0], ref)
    n0 /= np.linalg.norm(n0)
    normals[0] = n0
    binormals[0] = np.cross(tangents[0], n0)

    for i in range(1, n):
        t_prev, t_curr = tangents[i - 1], tangents[i]
        v = np.cross(t_prev, t_curr)
        sv = float(np.linalg.norm(v))
        if sv < 1e-12:
            normals[i] = normals[i - 1]
        else:
            axis = v / sv
            cos_a = float(np.clip(np.dot(t_prev, t_curr), -1.0, 1.0))
            ang = math.acos(cos_a)
            # Rodrigues rotation of normals[i-1] around axis by ang
            n_prev = normals[i - 1]
            n_new = (
                n_prev * math.cos(ang)
                + np.cross(axis, n_prev) * math.sin(ang)
                + axis * float(np.dot(axis, n_prev)) * (1.0 - math.cos(ang))
            )
            n_new -= float(np.dot(n_new, t_curr)) * t_curr
            normals[i] = n_new / np.linalg.norm(n_new)
        binormals[i] = np.cross(t_curr, normals[i])

    return tangents, normals, binormals


def make_swept_tube(
    spine_pts: Sequence[Sequence[float]],
    r_out: float,
    *,
    r_in: float = 0.0,
    segments: int = 20,
    name: str = "swept_tube",
    material: str = "OFHC Cu",
) -> SolidMesh:
    """Sweep a circular rod (``r_in == 0``) or hollow tube (``r_in > 0``) along a 3D spine."""
    pts = np.asarray(spine_pts, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 3 or pts.shape[0] < 2:
        raise ValueError("spine_pts must have shape (K >= 2, 3)")
    if r_out <= 0.0 or r_in < 0.0 or r_in >= r_out or segments < 6:
        raise ValueError("Invalid swept tube radii or segments")

    _, normals, binormals = _bishop_frames(pts)
    k_pts = len(pts)
    th = np.linspace(0.0, 2.0 * math.pi, segments, endpoint=False)
    ct, st = np.cos(th), np.sin(th)

    verts: list[np.ndarray] = []
    # Outer rings: indices 0 .. k_pts*segments - 1
    for i in range(k_pts):
        ring = pts[i] + r_out * (ct[:, None] * normals[i] + st[:, None] * binormals[i])
        verts.append(ring)

    faces: list[list[int]] = []
    # Outer lateral surface
    for i in range(k_pts - 1):
        b0 = i * segments
        b1 = (i + 1) * segments
        for s in range(segments):
            sn = (s + 1) % segments
            faces.append([b0 + s, b0 + sn, b1 + sn])
            faces.append([b0 + s, b1 + sn, b1 + s])

    if r_in <= 1e-12:
        # Solid rod end caps
        c_start = k_pts * segments
        c_end = c_start + 1
        verts.append(np.vstack([pts[0], pts[-1]]))
        end_base = (k_pts - 1) * segments
        for s in range(segments):
            sn = (s + 1) % segments
            faces.append([c_start, sn, s])
            faces.append([c_end, end_base + s, end_base + sn])
    else:
        # Inner rings: offset in_off = k_pts * segments
        in_off = k_pts * segments
        for i in range(k_pts):
            ring = pts[i] + r_in * (ct[:, None] * normals[i] + st[:, None] * binormals[i])
            verts.append(ring)
        for i in range(k_pts - 1):
            b0 = in_off + i * segments
            b1 = in_off + (i + 1) * segments
            for s in range(segments):
                sn = (s + 1) % segments
                # Reversed winding so normals point inward into bore
                faces.append([b0 + sn, b0 + s, b1 + s])
                faces.append([b0 + sn, b1 + s, b1 + sn])
        # Start and end annular caps
        out_end = (k_pts - 1) * segments
        in_end = in_off + (k_pts - 1) * segments
        for s in range(segments):
            sn = (s + 1) % segments
            # Start cap (normal = -tangent[0])
            faces.append([sn, s, in_off + s])
            faces.append([sn, in_off + s, in_off + sn])
            # End cap (normal = +tangent[-1])
            faces.append([out_end + s, out_end + sn, in_end + sn])
            faces.append([out_end + s, in_end + sn, in_end + s])

    return SolidMesh(
        vertices=np.vstack(verts),
        faces=np.asarray(faces, dtype=np.int32),
        name=name,
        material=material,
    )


def make_s_braid(
    length_mm: float = 100.0,
    s_amplitude_mm: float = 16.0,
    width_mm: float = 10.0,
    thickness_mm: float = 2.0,
    *,
    n_steps: int = 36,
    lug_length_mm: float = 0.0,
    axis: str | Sequence[float] = "z",
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str = "s_braid",
    material: str = "OFHC Cu",
) -> SolidMesh:
    """Create a watertight 3D S-loop flat-ribbon OFHC cryo braid (e.g. S6.9-03)."""
    if length_mm <= 0.0 or width_mm <= 0.0 or thickness_mm <= 0.0 or n_steps < 8:
        raise ValueError("Invalid S-braid dimensions")

    t_param = np.linspace(0.0, 1.0, n_steps)
    # Smooth zero-slope-at-ends S-curve along local Z with lateral S-bow in X
    z = (t_param - 0.5) * length_mm
    x = s_amplitude_mm * np.sin(2.0 * math.pi * t_param) * (np.sin(math.pi * t_param) ** 2)
    y = np.zeros_like(z)
    spine = np.column_stack([x, y, z])

    # Stadium cross-section (16 pts around ribbon profile)
    prof_2d = slot_2d(max(width_mm, thickness_mm), min(width_mm, thickness_mm), arc_seg=4, ccw=True)
    # Swap axes if thickness_mm > width_mm
    sec = np.asarray(prof_2d, dtype=np.float64)
    n_sec = len(sec)

    _, normals, binormals = _bishop_frames(spine)
    verts_list: list[np.ndarray] = []
    for i in range(n_steps):
        # Ribbon width lies along binormal (out-of-bend plane) and thickness along normal (bend plane)
        ring = spine[i] + sec[:, 1:2] * normals[i] + sec[:, 0:1] * binormals[i]
        verts_list.append(ring)

    # Note: verify cross-section orientation in (normals, binormals) plane:
    # sec[:, 0] is along B, sec[:, 1] is along N; B x N = -T, so reverse ring order to be CCW around +T!
    verts_list = [r[::-1] for r in verts_list]

    faces: list[list[int]] = []
    for i in range(n_steps - 1):
        b0 = i * n_sec
        b1 = (i + 1) * n_sec
        for s in range(n_sec):
            sn = (s + 1) % n_sec
            faces.append([b0 + s, b0 + sn, b1 + sn])
            faces.append([b0 + s, b1 + sn, b1 + s])

    c_start = n_steps * n_sec
    c_end = c_start + 1
    verts_list.append(np.vstack([spine[0], spine[-1]]))
    end_base = (n_steps - 1) * n_sec
    for s in range(n_sec):
        sn = (s + 1) % n_sec
        faces.append([c_start, sn, s])
        faces.append([c_end, end_base + s, end_base + sn])

    braid = SolidMesh(
        vertices=_orient_and_place(np.vstack(verts_list), axis=axis, center=center),
        faces=np.asarray(faces, dtype=np.int32),
        name=name,
        material=material,
    )

    if lug_length_mm > 0.0:
        lug_bot = make_box(
            thickness_mm * 2.2,
            width_mm * 1.25,
            lug_length_mm,
            center=(0.0, 0.0, -0.5 * length_mm - 0.5 * lug_length_mm),
            name=f"{name}_lug_bot",
            material=material,
        )
        lug_top = make_box(
            thickness_mm * 2.2,
            width_mm * 1.25,
            lug_length_mm,
            center=(0.0, 0.0, 0.5 * length_mm + 0.5 * lug_length_mm),
            name=f"{name}_lug_top",
            material=material,
        )
        lug_bot = SolidMesh(
            vertices=_orient_and_place(lug_bot.vertices, axis=axis, center=center),
            faces=lug_bot.faces,
            name=lug_bot.name,
            material=material,
        )
        lug_top = SolidMesh(
            vertices=_orient_and_place(lug_top.vertices, axis=axis, center=center),
            faces=lug_top.faces,
            name=lug_top.name,
            material=material,
        )
        return merge_solids([braid, lug_bot, lug_top], name=name, material=material)

    return braid


# ---------------------------------------------------------------------------
# Fast Vectorized Binary STL I/O
# ---------------------------------------------------------------------------
_STL_DTYPE = np.dtype(
    [
        ("normal", "<f4", (3,)),
        ("v0", "<f4", (3,)),
        ("v1", "<f4", (3,)),
        ("v2", "<f4", (3,)),
        ("attr", "<u2"),
    ]
)


def write_binary_stl(
    mesh: SolidMesh,
    path: Path | str,
    *,
    header_text: str = "",
) -> Path:
    """Write ``mesh`` to a compact binary STL file using vectorized NumPy I/O."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    v = mesh.vertices
    f = mesh.faces
    v0 = v[f[:, 0]]
    v1 = v[f[:, 1]]
    v2 = v[f[:, 2]]
    n = np.cross(v1 - v0, v2 - v0)
    n_len = np.linalg.norm(n, axis=1, keepdims=True)
    n_unit = np.divide(n, np.maximum(n_len, 1e-30))

    rec = np.zeros(mesh.n_faces, dtype=_STL_DTYPE)
    rec["normal"] = n_unit.astype(np.float32)
    rec["v0"] = v0.astype(np.float32)
    rec["v1"] = v1.astype(np.float32)
    rec["v2"] = v2.astype(np.float32)
    rec["attr"] = 0

    hdr_str = (
        header_text
        or f"AtomLitho CAD {mesh.name} | M0_M1_DETAILED_CAD_DESIGN_ONLY | mm"
    )
    hdr_bytes = hdr_str.encode("ascii", errors="replace")[:80].ljust(80, b" ")

    with out_path.open("wb") as fh:
        fh.write(hdr_bytes)
        fh.write(struct.pack("<I", mesh.n_faces))
        fh.write(rec.tobytes())

    return out_path


def read_binary_stl(
    path: Path | str,
    *,
    weld_decimals: int = 5,
    name: str = "",
    material: str = "316LN",
) -> SolidMesh:
    """Read a binary STL file back into a vertex-welded ``SolidMesh``."""
    in_path = Path(path)
    data = in_path.read_bytes()
    if len(data) < 84:
        raise ValueError(f"Truncated binary STL file: {in_path}")
    n_tris = struct.unpack("<I", data[80:84])[0]
    expected = 84 + 50 * n_tris
    if len(data) != expected:
        raise ValueError(
            f"STL byte length mismatch ({len(data)} vs expected {expected})"
        )
    rec = np.frombuffer(data, dtype=_STL_DTYPE, count=n_tris, offset=84)
    all_pts = np.stack([rec["v0"], rec["v1"], rec["v2"]], axis=1).reshape(-1, 3).astype(np.float64)
    rounded = np.round(all_pts, decimals=weld_decimals)
    _, uniq_idx, inv = np.unique(rounded, axis=0, return_index=True, return_inverse=True)
    verts = all_pts[uniq_idx]
    faces = inv.reshape(-1, 3).astype(np.int32)
    return SolidMesh(
        vertices=verts,
        faces=faces,
        name=name or in_path.stem,
        material=material,
    )
