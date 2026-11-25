"""Pure-Python ISO 10303-21 AP214 (AUTOMOTIVE_DESIGN) STEP exporter & strict validator.

Emits standards-compliant ``FACETED_BREP`` / ``CLOSED_SHELL`` ``.step`` files with
full part metadata headers and zero external dependencies. Meshes exceeding
``max_faces`` (default ~800) are gracefully simplified via link-condition-preserving
manifold edge collapse or exact-envelope watertight proxy so every emitted STEP
remains compact, strictly closed, and fast to validate while preserving exact
bounding envelope dimensions.
"""
from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .feature_engine import (
    SolidMesh,
    make_box,
    make_cylinder,
    make_tube,
    split_shells,
    verify_watertight,
)
from .part_schema import (
    DESIGN_MATURITY,
    IEC61508_CERTIFIED,
    NO_LAB_MEASUREMENT,
    PartDesign,
    SEMI_S2_CERTIFIED,
)

# ---------------------------------------------------------------------------
# Strict ISO 10303-21 ASCII String & Real Formatting
# ---------------------------------------------------------------------------
_TRANSLIT_MAP = str.maketrans(
    {
        "ı": "i",
        "İ": "I",
        "ş": "s",
        "Ş": "S",
        "ğ": "g",
        "Ğ": "G",
        "ü": "u",
        "Ü": "U",
        "ö": "o",
        "Ö": "O",
        "ç": "c",
        "Ç": "C",
        "µ": "u",
        "μ": "u",
        "Ø": "Dia",
        "ø": "dia",
        "°": "deg",
        "×": "x",
        "–": "-",
        "—": "-",
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "±": "+/-",
        "≤": "<=",
        "≥": ">=",
        "→": "->",
        "↔": "<->",
        "⊥": "PERP",
        "◎": "CONC",
        "⌓": "PROF",
        "⏥": "FLAT",
    }
)


def _step_str(text: str, max_len: int = 240) -> str:
    """Convert arbitrary UTF-8 text to a strict ISO 10303-21 printable ASCII string."""
    s = (text or "").translate(_TRANSLIT_MAP)
    s = s.encode("ascii", errors="replace").decode("ascii")
    s = "".join(ch if 32 <= ord(ch) <= 126 else " " for ch in s)
    s = re.sub(r"\s+", " ", s).strip()[:max_len]
    return s.replace("'", "''")


def _step_real(val: float) -> str:
    """Format float as ISO 10303-21 REAL literal (always contains decimal point)."""
    if abs(val) < 1e-9:
        return "0."
    s = f"{float(val):.6f}".rstrip("0")
    if s == "-0.":
        return "0."
    return s


# ---------------------------------------------------------------------------
# Graceful Watertight Decimation / Exact-Envelope Proxy for Large Meshes
# ---------------------------------------------------------------------------
def _try_manifold_decimate(mesh: SolidMesh, max_faces: int) -> SolidMesh | None:
    """Topology-preserving edge collapse keeping exact bbox extrema and watertightness."""
    v = mesh.vertices.copy()
    f = mesh.faces.copy()
    n_v = len(v)
    n_f = len(f)
    if n_f <= max_faces:
        return mesh

    # Lock extremal vertices on all 6 bbox planes to preserve exact envelope
    bmin = v.min(axis=0)
    bmax = v.max(axis=0)
    locked = np.zeros(n_v, dtype=bool)
    for axis in range(3):
        locked |= np.abs(v[:, axis] - bmin[axis]) <= 1e-6
        locked |= np.abs(v[:, axis] - bmax[axis]) <= 1e-6

    # Build mutable adjacency structures
    alive_f = np.ones(n_f, dtype=bool)
    v_faces: list[set[int]] = [set() for _ in range(n_v)]
    for fi, (a, b, c) in enumerate(f):
        v_faces[int(a)].add(fi)
        v_faces[int(b)].add(fi)
        v_faces[int(c)].add(fi)

    def _face_normal(fi: int) -> np.ndarray:
        a, b, c = f[fi]
        n = np.cross(v[b] - v[a], v[c] - v[a])
        ln = float(np.linalg.norm(n))
        return n / ln if ln > 1e-15 else np.zeros(3)

    # Candidate undirected edges sorted by length
    e_u = np.concatenate([f[:, 0], f[:, 1], f[:, 2]])
    e_v = np.concatenate([f[:, 1], f[:, 2], f[:, 0]])
    lo = np.minimum(e_u, e_v)
    hi = np.maximum(e_u, e_v)
    pairs = np.unique(np.column_stack([lo, hi]), axis=0)
    lengths = np.linalg.norm(v[pairs[:, 1]] - v[pairs[:, 0]], axis=1)
    order = np.argsort(lengths)

    # Union-find map for collapsed vertices
    parent = list(range(n_v))

    def _find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    remaining = n_f
    for idx in order:
        if remaining <= max_faces:
            break
        u = _find(int(pairs[idx, 0]))
        w = _find(int(pairs[idx, 1]))
        if u == w:
            continue
        if locked[u] and locked[w]:
            continue
        if not v_faces[u] or not v_faces[w]:
            continue

        # Neighbor sets of u and w in alive faces
        shared_f = v_faces[u] & v_faces[w]
        if len(shared_f) != 2:
            continue

        nb_u: set[int] = set()
        for fi in v_faces[u]:
            for vid in f[fi]:
                if int(vid) != u:
                    nb_u.add(int(vid))
        nb_w: set[int] = set()
        for fi in v_faces[w]:
            for vid in f[fi]:
                if int(vid) != w:
                    nb_w.add(int(vid))

        # Exact link condition for 2-manifold edge collapse: |N(u) ∩ N(w)| == 2
        if len(nb_u & nb_w) != 2:
            continue

        # Target position: preserve locked vertex if one is locked, else midpoint
        if locked[u]:
            new_pos = v[u].copy()
        elif locked[w]:
            new_pos = v[w].copy()
        else:
            new_pos = 0.5 * (v[u] + v[w])

        # Verify no remaining incident face flips normal or degenerates
        affected = (v_faces[u] | v_faces[w]) - shared_f
        old_u = v[u].copy()
        old_w = v[w].copy()
        ok = True
        pre_normals = {fi: _face_normal(fi) for fi in affected}
        v[u] = new_pos
        v[w] = new_pos
        for fi in affected:
            a, b, c = f[fi]
            # Simulate remapping w -> u
            pa = new_pos if a in (u, w) else v[a]
            pb = new_pos if b in (u, w) else v[b]
            pc = new_pos if c in (u, w) else v[c]
            nn = np.cross(pb - pa, pc - pa)
            ln = float(np.linalg.norm(nn))
            if ln <= 1e-12:
                ok = False
                break
            if float(np.dot(nn / ln, pre_normals[fi])) < 0.35:
                ok = False
                break
        if not ok:
            v[u] = old_u
            v[w] = old_w
            continue

        # Commit collapse w -> u
        v[u] = new_pos
        if locked[w]:
            locked[u] = True
        parent[w] = u
        for fi in shared_f:
            alive_f[fi] = False
            for vid in f[fi]:
                v_faces[int(vid)].discard(fi)
            remaining -= 1
        for fi in list(v_faces[w]):
            if not alive_f[fi]:
                continue
            for k in range(3):
                if f[fi, k] == w:
                    f[fi, k] = u
            v_faces[u].add(fi)
        v_faces[w].clear()

    if remaining > max_faces:
        return None

    kept_f = f[alive_f]
    uniq_v, inv = np.unique(kept_f.ravel(), return_inverse=True)
    dec = SolidMesh(
        vertices=v[uniq_v],
        faces=inv.reshape(-1, 3).astype(np.int32),
        name=mesh.name,
        material=mesh.material,
    )
    if verify_watertight(dec).watertight and dec.n_faces <= max_faces:
        return dec
    return None


def _build_exact_envelope_proxy(mesh: SolidMesh) -> SolidMesh:
    """Build a compact watertight exact-bounding-envelope proxy preserving cylindrical/bore form."""
    bmin, bmax = mesh.bbox()
    dx = max(bmax[0] - bmin[0], 1e-4)
    dy = max(bmax[1] - bmin[1], 1e-4)
    dz = max(bmax[2] - bmin[2], 1e-4)
    cx = 0.5 * (bmin[0] + bmax[0])
    cy = 0.5 * (bmin[1] + bmax[1])
    cz = 0.5 * (bmin[2] + bmax[2])

    # Detect if solid is axisymmetric about Z, X, or Y with circular outer profile
    v = mesh.vertices
    for axis_name, (i0, i1, ia) in (("z", (0, 1, 2)), ("x", (1, 2, 0)), ("y", (0, 2, 1))):
        ext0 = bmax[i0] - bmin[i0]
        ext1 = bmax[i1] - bmin[i1]
        if ext0 > 1e-3 and abs(ext0 - ext1) / max(ext0, ext1) < 0.02:
            c0 = 0.5 * (bmin[i0] + bmax[i0])
            c1 = 0.5 * (bmin[i1] + bmax[i1])
            du = v[:, i0] - c0
            dv = v[:, i1] - c1
            rad = np.hypot(du, dv)
            r_max = float(rad.max())
            # Check outer rim circularity across 16 angular bins
            ang = np.arctan2(dv, du)
            bins = np.floor(((ang + math.pi) / (2.0 * math.pi)) * 16).astype(int) % 16
            bin_max = np.array([rad[bins == b].max() if np.any(bins == b) else 0.0 for b in range(16)])
            if np.all(bin_max > 0.0) and float(bin_max.std() / bin_max.mean()) < 0.045:
                # Axisymmetric circular envelope! Check if hollow (clear central bore)
                r_min = float(rad.min())
                h_ax = bmax[ia] - bmin[ia]
                r_out = 0.5 * 0.5 * (ext0 + ext1)
                # Use multiple of 4 segments (32) so 0/90/180/270 deg vertices hit exact bbox!
                if r_min > 0.12 * r_out and r_min < 0.96 * r_out:
                    return make_tube(
                        r_in=r_min,
                        r_out=r_out,
                        height=h_ax,
                        segments=32,
                        axis=axis_name,
                        center=(cx, cy, cz),
                        name=f"{mesh.name}_step_proxy",
                        material=mesh.material,
                    )
                return make_cylinder(
                    radius=r_out,
                    height=h_ax,
                    segments=32,
                    axis=axis_name,
                    center=(cx, cy, cz),
                    name=f"{mesh.name}_step_proxy",
                    material=mesh.material,
                )

    return make_box(
        dx, dy, dz, center=(cx, cy, cz), name=f"{mesh.name}_step_proxy", material=mesh.material
    )


def prepare_step_mesh(
    mesh: SolidMesh,
    *,
    max_faces: int = 800,
) -> tuple[SolidMesh, str, bool]:
    """Return ``(mesh_for_step, mode_note, was_decimated)`` guaranteed watertight & compact."""
    if mesh.n_faces <= max_faces:
        return mesh, f"exact_full_mesh({mesh.n_faces}_faces)", False

    val = verify_watertight(mesh)
    # Try exact manifold edge collapse if mesh is moderately sized and low-genus
    if mesh.n_faces <= 4500 and val.euler_characteristic >= -40 and val.n_shells == 1:
        dec = _try_manifold_decimate(mesh, max_faces=max_faces)
        if dec is not None:
            return (
                dec,
                f"manifold_decimated({mesh.n_faces}->{dec.n_faces}_faces;exact_bbox)",
                True,
            )

    proxy = _build_exact_envelope_proxy(mesh)
    return (
        proxy,
        f"watertight_envelope_proxy(full_stl_faces={mesh.n_faces};step_faces={proxy.n_faces};exact_bbox)",
        True,
    )


# ---------------------------------------------------------------------------
# ISO 10303-21 AP214 Writer
# ---------------------------------------------------------------------------
def write_step(
    mesh: SolidMesh,
    path: Path | str,
    *,
    part_design: PartDesign | None = None,
    step_mesh: SolidMesh | None = None,
    max_faces: int = 800,
) -> Path:
    """Export ``mesh`` to a valid ISO 10303-21 AP214 (AUTOMOTIVE_DESIGN) ``.step`` file."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if step_mesh is not None:
        export_mesh = step_mesh
        rep_note = f"explicit_step_mesh({step_mesh.n_faces}_faces;full_stl={mesh.n_faces})"
    else:
        export_mesh, rep_note, _ = prepare_step_mesh(mesh, max_faces=max_faces)

    part_id = part_design.part_id if part_design is not None else (mesh.name or out_path.stem)
    part_name = part_design.part_name if part_design is not None else part_id
    mat = part_design.material if part_design is not None else mesh.material
    temp = part_design.temp_stage if part_design is not None else "300 K"
    vac = part_design.vacuum_grade if part_design is not None else "UHV"
    maturity = part_design.design_maturity if part_design is not None else DESIGN_MATURITY
    no_lab = part_design.no_lab_measurement if part_design is not None else NO_LAB_MEASUREMENT
    iec_cert = part_design.iec61508_certified if part_design is not None else IEC61508_CERTIFIED
    semi_cert = part_design.semi_s2_certified if part_design is not None else SEMI_S2_CERTIFIED

    bmin, bmax = mesh.bbox()
    ext = (bmax[0] - bmin[0], bmax[1] - bmin[1], bmax[2] - bmin[2])

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    fname = _step_str(out_path.name)
    desc_1 = _step_str(f"Atom Lithography Machine CAD Part {part_id}")
    desc_2 = _step_str(
        f"{maturity}; no_lab_measurement={str(no_lab).lower()}; "
        f"iec61508_certified={str(iec_cert).lower()}; "
        f"semi_s2_certified={str(semi_cert).lower()}; "
        f"rep={rep_note}; bbox_mm={ext[0]:.3f}x{ext[1]:.3f}x{ext[2]:.3f}"
    )
    prod_desc = _step_str(
        f"Material={mat}; Temp={temp}; Vacuum={vac}; "
        f"BBox={ext[0]:.2f}x{ext[1]:.2f}x{ext[2]:.2f}mm; {rep_note}"
    )

    lines: list[str] = [
        "ISO-10303-21;",
        "HEADER;",
        f"FILE_DESCRIPTION(('{desc_1}','{desc_2}'),'2;1');",
        (
            f"FILE_NAME('{fname}','{ts}',"
            "('Atom Lithography CAD Kernel'),('Hydrogen Mechanical Design'),"
            "'Pure-Python ISO 10303-21 AP214 Writer','hardware.cad_parts.core.step_writer',"
            f"'{_step_str(maturity)}');"
        ),
        "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));",
        "ENDSEC;",
        "DATA;",
    ]

    eid = 0

    def _emit(stmt: str) -> int:
        nonlocal eid
        eid += 1
        lines.append(f"#{eid}={stmt};")
        return eid

    # AP214 Product & Geometric Context Boilerplate
    app_ctx = _emit("APPLICATION_CONTEXT('core data for automotive mechanical design processes')")
    _emit(f"APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,#{app_ctx})")
    prod_ctx = _emit(f"PRODUCT_CONTEXT('',#{app_ctx},'mechanical')")
    prod = _emit(f"PRODUCT('{_step_str(part_id)}','{_step_str(part_name)}','{prod_desc}',(#{prod_ctx}))")
    _emit(f"PRODUCT_RELATED_PRODUCT_CATEGORY('part','',(#{prod}))")
    pdf = _emit(f"PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE('1','{_step_str(maturity)}',#{prod},.NOT_KNOWN.)")
    pdc = _emit(f"PRODUCT_DEFINITION_CONTEXT('part definition',#{app_ctx},'design')")
    pd = _emit(f"PRODUCT_DEFINITION('design','',#{pdf},#{pdc})")
    pds = _emit(f"PRODUCT_DEFINITION_SHAPE('','',#{pd})")

    u_len = _emit("( LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.) )")
    u_ang = _emit("( NAMED_UNIT(*) PLANE_ANGLE_UNIT() SI_UNIT($,.RADIAN.) )")
    u_sol = _emit("( NAMED_UNIT(*) SOLID_ANGLE_UNIT() SI_UNIT($,.STERADIAN.) )")
    unc = _emit(f"UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-04),#{u_len},'distance_accuracy_value','tolerance')")
    gctx = _emit(
        f"( GEOMETRIC_REPRESENTATION_CONTEXT(3) "
        f"GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#{unc})) "
        f"GLOBAL_UNIT_ASSIGNED_CONTEXT((#{u_len},#{u_ang},#{u_sol})) "
        f"REPRESENTATION_CONTEXT('{_step_str(part_id)}','3D') )"
    )

    origin = _emit("CARTESIAN_POINT('Origin',(0.,0.,0.))")
    dir_z = _emit("DIRECTION('Z',(0.,0.,1.))")
    dir_x = _emit("DIRECTION('X',(1.,0.,0.))")
    axis3d = _emit(f"AXIS2_PLACEMENT_3D('World',#{origin},#{dir_z},#{dir_x})")

    # Emit one CLOSED_SHELL + FACETED_BREP per connected shell
    shells = split_shells(export_mesh)
    brep_ids: list[int] = []
    for sh_idx, sh in enumerate(shells):
        pt_ids: list[int] = []
        for vx, vy, vz in sh.vertices:
            pt_ids.append(
                _emit(
                    f"CARTESIAN_POINT('',({_step_real(vx)},{_step_real(vy)},{_step_real(vz)}))"
                )
            )

        face_ids: list[int] = []
        for a, b, c in sh.faces:
            pa, pb, pc = pt_ids[int(a)], pt_ids[int(b)], pt_ids[int(c)]
            pl = _emit(f"POLY_LOOP('',(#{pa},#{pb},#{pc}))")
            fob = _emit(f"FACE_OUTER_BOUND('',#{pl},.T.)")
            fc = _emit(f"FACE('',(#{fob}))")
            face_ids.append(fc)

        face_refs = ",".join(f"#{fid}" for fid in face_ids)
        cs = _emit(f"CLOSED_SHELL('{_step_str(part_id)}_S{sh_idx}',({face_refs}))")
        fb = _emit(f"FACETED_BREP('{_step_str(part_id)}_B{sh_idx}',#{cs})")
        brep_ids.append(fb)

    rep_items = ",".join([f"#{axis3d}"] + [f"#{bid}" for bid in brep_ids])
    fbr = _emit(f"FACETED_BREP_SHAPE_REPRESENTATION('{_step_str(part_id)}',({rep_items}),#{gctx})")
    _emit(f"SHAPE_DEFINITION_REPRESENTATION(#{pds},#{fbr})")

    lines.append("ENDSEC;")
    lines.append("END-ISO-10303-21;")

    out_path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return out_path


# ---------------------------------------------------------------------------
# Strict Independent ISO 10303-21 STEP File Validator
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class StepValidationResult:
    """Validation summary for an ISO 10303-21 AP214 ``.step`` file."""

    valid: bool
    entity_count: int
    closed_shell_count: int
    faceted_brep_count: int
    face_count: int
    poly_loop_count: int
    dangling_refs: tuple[int, ...]
    duplicate_ids: tuple[int, ...]
    has_ap214_schema: bool
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_ENTITY_RE = re.compile(r"^\s*#(\d+)\s*=\s*(.+?)\s*;\s*$", re.DOTALL)
_QUOTED_RE = re.compile(r"'(?:''|[^'])*'")
_REF_RE = re.compile(r"#(\d+)")


def validate_step_file(path: Path | str) -> StepValidationResult:
    """Strictly parse and validate an ISO 10303-21 ``.step`` file.

    Checks:
    - ``ISO-10303-21;``, ``HEADER;``, ``DATA;``, ``ENDSEC;``, ``END-ISO-10303-21;`` framing
    - AP214 ``AUTOMOTIVE_DESIGN`` ``FILE_SCHEMA``
    - Every entity in ``DATA;`` parses with unique ``#id`` and balanced parentheses
    - Zero dangling ``#id`` references anywhere in ``DATA;``
    - At least one ``CLOSED_SHELL``, ``FACETED_BREP``, and ``SHAPE_DEFINITION_REPRESENTATION``
    - Every ``CLOSED_SHELL`` references >= 4 defined faces; every ``POLY_LOOP`` references >= 3 points
    """
    errors: list[str] = []
    p = Path(path)
    if not p.is_file():
        return StepValidationResult(
            valid=False,
            entity_count=0,
            closed_shell_count=0,
            faceted_brep_count=0,
            face_count=0,
            poly_loop_count=0,
            dangling_refs=(),
            duplicate_ids=(),
            has_ap214_schema=False,
            errors=(f"File does not exist: {p}",),
        )

    raw = p.read_text(encoding="ascii", errors="strict")
    stripped = raw.strip()
    if not stripped.startswith("ISO-10303-21;"):
        errors.append("Missing leading 'ISO-10303-21;'")
    if not stripped.endswith("END-ISO-10303-21;"):
        errors.append("Missing trailing 'END-ISO-10303-21;'")
    if "HEADER;" not in stripped:
        errors.append("Missing 'HEADER;' section")
    if "DATA;" not in stripped:
        errors.append("Missing 'DATA;' section")

    # Extract HEADER and DATA blocks
    hdr_m = re.search(r"HEADER;(.*?)ENDSEC;", stripped, re.DOTALL)
    data_m = re.search(r"DATA;(.*?)ENDSEC;", stripped, re.DOTALL)
    if not hdr_m:
        errors.append("Malformed HEADER; ... ENDSEC; section")
    if not data_m:
        errors.append("Malformed DATA; ... ENDSEC; section")

    hdr_text = hdr_m.group(1) if hdr_m else ""
    has_ap214 = "AUTOMOTIVE_DESIGN" in hdr_text and "FILE_SCHEMA" in hdr_text
    if not has_ap214:
        errors.append("Missing AP214 AUTOMOTIVE_DESIGN FILE_SCHEMA in HEADER")
    if "FILE_DESCRIPTION" not in hdr_text or "FILE_NAME" not in hdr_text:
        errors.append("Missing FILE_DESCRIPTION or FILE_NAME in HEADER")

    defined_types: dict[int, str] = {}
    defined_bodies: dict[int, str] = {}
    duplicate_ids: list[int] = []
    all_refs: set[int] = set()

    if data_m:
        data_body = data_m.group(1)
        # Split into statements ending with ';' outside quotes
        stmts: list[str] = []
        buf: list[str] = []
        in_str = False
        i = 0
        n_ch = len(data_body)
        while i < n_ch:
            ch = data_body[i]
            buf.append(ch)
            if ch == "'":
                if in_str and i + 1 < n_ch and data_body[i + 1] == "'":
                    buf.append("'")
                    i += 1
                else:
                    in_str = not in_str
            elif ch == ";" and not in_str:
                stmt = "".join(buf).strip()
                if stmt:
                    stmts.append(stmt)
                buf = []
            i += 1
        if "".join(buf).strip():
            errors.append("Trailing unterminated statement in DATA section")

        for stmt in stmts:
            m = _ENTITY_RE.match(stmt)
            if not m:
                errors.append(f"Unparseable DATA statement: {stmt[:80]}")
                continue
            eid = int(m.group(1))
            rhs = m.group(2).strip()
            if eid in defined_types:
                duplicate_ids.append(eid)

            # Check balanced parens outside quoted strings
            clean_rhs = _QUOTED_RE.sub("''", rhs)
            depth = 0
            for ch in clean_rhs:
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth < 0:
                        break
            if depth != 0:
                errors.append(f"Unbalanced parentheses in entity #{eid}")

            # Extract primary entity type keyword
            if clean_rhs.startswith("("):
                etype = "COMPLEX_ENTITY"
            else:
                etype = clean_rhs.split("(", 1)[0].strip().upper()
            defined_types[eid] = etype
            defined_bodies[eid] = clean_rhs

            for rm in _REF_RE.finditer(clean_rhs):
                all_refs.add(int(rm.group(1)))

    dangling = sorted(ref for ref in all_refs if ref not in defined_types)
    if dangling:
        errors.append(f"Dangling STEP references: {dangling[:10]}")
    if duplicate_ids:
        errors.append(f"Duplicate STEP entity IDs: {duplicate_ids[:10]}")

    closed_shells = [eid for eid, t in defined_types.items() if t == "CLOSED_SHELL"]
    faceted_breps = [
        eid for eid, t in defined_types.items() if t in {"FACETED_BREP", "MANIFOLD_SOLID_BREP"}
    ]
    faces = [
        eid for eid, t in defined_types.items() if t in {"FACE", "FACE_SURFACE", "ADVANCED_FACE"}
    ]
    poly_loops = [eid for eid, t in defined_types.items() if t == "POLY_LOOP"]
    has_sdr = any(t == "SHAPE_DEFINITION_REPRESENTATION" for t in defined_types.values())

    if not closed_shells:
        errors.append("No CLOSED_SHELL entity found")
    if not faceted_breps:
        errors.append("No FACETED_BREP / MANIFOLD_SOLID_BREP entity found")
    if not has_sdr:
        errors.append("No SHAPE_DEFINITION_REPRESENTATION entity found")

    # Verify each CLOSED_SHELL has >= 4 faces and each POLY_LOOP has >= 3 CARTESIAN_POINTs
    for csid in closed_shells:
        refs = [int(x) for x in _REF_RE.findall(defined_bodies[csid])]
        if len(refs) < 4:
            errors.append(f"CLOSED_SHELL #{csid} has fewer than 4 faces ({len(refs)})")
        bad_faces = [r for r in refs if defined_types.get(r) not in {"FACE", "FACE_SURFACE", "ADVANCED_FACE"}]
        if bad_faces:
            errors.append(f"CLOSED_SHELL #{csid} references non-face entities: {bad_faces[:5]}")

    for plid in poly_loops:
        refs = [int(x) for x in _REF_RE.findall(defined_bodies[plid])]
        if len(refs) < 3:
            errors.append(f"POLY_LOOP #{plid} has fewer than 3 points")
        bad_pts = [r for r in refs if defined_types.get(r) != "CARTESIAN_POINT"]
        if bad_pts:
            errors.append(f"POLY_LOOP #{plid} references non-point entities: {bad_pts[:5]}")

    return StepValidationResult(
        valid=(len(errors) == 0),
        entity_count=len(defined_types),
        closed_shell_count=len(closed_shells),
        faceted_brep_count=len(faceted_breps),
        face_count=len(faces),
        poly_loop_count=len(poly_loops),
        dangling_refs=tuple(dangling),
        duplicate_ids=tuple(duplicate_ids),
        has_ap214_schema=has_ap214,
        errors=tuple(errors),
    )
