"""Pure-Python Parametric OpenSCAD (``.scad``) module emitter & syntax validator.

Emits clean, human-readable, fully parametric OpenSCAD modules per exact
``part_id`` featuring:
- Complete engineering & epistemic header comments
- Named top-level parametric variables (dimensions, bolt circles, bores, custom params)
- Real CSG ``difference()`` / ``union()`` / ``rotate_extrude()`` geometry for
  boxes, cylinders, tubes, ISO 3669 ConFlat flanges with bolt circles & knife-edge
  recesses, through-holes, slots, and 32x32 MEMS grids
- World mounting transform invocation comments (``translate([...]) rotate([...])``)
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

from .cf_flanges import CF_SPECS
from .feature_engine import MassProperties, SolidMesh, compute_mass_props
from .part_schema import (
    DESIGN_MATURITY,
    IEC61508_CERTIFIED,
    NO_LAB_MEASUREMENT,
    PartDesign,
    PortInterface,
    SEMI_S2_CERTIFIED,
)


def sanitize_scad_id(part_id: str) -> str:
    """Convert a BOM ``part_id`` (e.g. ``S7.SAFETY-02``) into a valid OpenSCAD identifier."""
    cleaned = re.sub(r"[^0-9A-Za-z_]", "_", part_id.strip())
    if cleaned and cleaned[0].isdigit():
        cleaned = f"p_{cleaned}"
    return cleaned or "part"


# ---------------------------------------------------------------------------
# Declarative Parametric CSG Feature Descriptors for Subsystem Designers
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ScadFeature:
    """Declarative CSG operation rendered inside a part's parametric OpenSCAD module.

    Supported ``op`` types:
    - ``"add_box"``: ``params = {"dx": ..., "dy": ..., "dz": ...}``
    - ``"add_cylinder"``: ``params = {"d": ..., "h": ...}`` (optional ``"d2"``)
    - ``"add_tube"``: ``params = {"od": ..., "id": ..., "h": ...}``
    - ``"add_cf_flange"``: ``params = {"size": "CF100", "blank": False}``
    - ``"add_revolve"``: ``params = {"points": [(r, z), ...]}``
    - ``"cut_hole"``: ``params = {"d": ..., "h": ...}``
    - ``"cut_bolt_circle"``: ``params = {"pcd": ..., "bolt_d": ..., "count": ..., "h": ...}``
    - ``"cut_slot"``: ``params = {"length": ..., "width": ..., "h": ...}``
    - ``"cut_grid_holes"``: ``params = {"nx": 32, "ny": 32, "pitch_x": 0.5, "pitch_y": 0.5, "hole_d": 0.3, "h": ...}``
    - ``"raw"``: ``params = {"code": "..."}``
    """

    op: str
    params: dict[str, Any]
    translate: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotate: tuple[float, float, float] = (0.0, 0.0, 0.0)
    comment: str = ""

    @property
    def is_cut(self) -> bool:
        return self.op.startswith("cut_")


def _wrap_transform(lines: list[str], tr: tuple[float, float, float], rot: tuple[float, float, float], indent: str) -> list[str]:
    has_tr = any(abs(v) > 1e-9 for v in tr)
    has_rot = any(abs(v) > 1e-9 for v in rot)
    prefix = ""
    if has_tr:
        prefix += f"translate([{tr[0]:.3f}, {tr[1]:.3f}, {tr[2]:.3f}]) "
    if has_rot:
        prefix += f"rotate([{rot[0]:.3f}, {rot[1]:.3f}, {rot[2]:.3f}]) "
    if not prefix:
        return [f"{indent}{ln}" for ln in lines]
    if len(lines) == 1:
        return [f"{indent}{prefix}{lines[0]}"]
    out = [f"{indent}{prefix}{{"]
    for ln in lines:
        out.append(f"{indent}  {ln}")
    out.append(f"{indent}}}")
    return out


def _render_feature(feat: ScadFeature, indent: str = "    ") -> list[str]:
    out: list[str] = []
    if feat.comment:
        out.append(f"{indent}// {feat.comment}")
    p = feat.params
    op = feat.op
    body: list[str] = []

    if op == "add_box":
        body = [f"cube([{p['dx']:.3f}, {p['dy']:.3f}, {p['dz']:.3f}], center=true);"]
    elif op == "add_cylinder":
        if "d2" in p:
            body = [f"cylinder(d1={p['d']:.3f}, d2={p['d2']:.3f}, h={p['h']:.3f}, center=true);"]
        else:
            body = [f"cylinder(d={p['d']:.3f}, h={p['h']:.3f}, center=true);"]
    elif op == "add_tube":
        body = [
            "difference() {",
            f"  cylinder(d={p['od']:.3f}, h={p['h']:.3f}, center=true);",
            f"  cylinder(d={p['id']:.3f}, h={p['h'] + 2.0:.3f}, center=true);",
            "}",
        ]
    elif op == "add_cf_flange":
        sp = CF_SPECS[str(p["size"]).upper()]
        blank = bool(p.get("blank", False))
        bore_d = 0.0 if blank else float(p.get("bore_id", sp.bore_id_mm))
        body = [
            "difference() {",
            f"  cylinder(d={sp.od_mm:.3f}, h={sp.thickness_mm:.3f}, center=true);",
        ]
        if bore_d > 0.0:
            body.append(f"  cylinder(d={bore_d:.3f}, h={sp.thickness_mm + 2.0:.3f}, center=true);")
        body.extend(
            [
                f"  translate([0, 0, {0.5 * sp.thickness_mm - sp.gasket_recess_depth_mm:.3f}]) "
                f"cylinder(d={sp.gasket_od_mm:.3f}, h={sp.gasket_recess_depth_mm + 0.5:.3f});",
                f"  for (i = [0 : {sp.bolt_count} - 1])",
                f"    rotate([0, 0, i * 360 / {sp.bolt_count}])",
                f"      translate([{0.5 * sp.pcd_mm:.3f}, 0, 0])",
                f"        cylinder(d={sp.bolt_hole_mm:.3f}, h={sp.thickness_mm + 2.0:.3f}, center=true);",
                "}",
            ]
        )
    elif op == "add_revolve":
        pts_s = ", ".join(f"[{float(r):.4f}, {float(z):.4f}]" for r, z in p["points"])
        body = [f"rotate_extrude(angle=360) polygon(points=[{pts_s}]);"]
    elif op == "cut_hole":
        body = [f"cylinder(d={p['d']:.3f}, h={p['h']:.3f}, center=true);"]
    elif op == "cut_bolt_circle":
        cnt = int(p["count"])
        body = [
            f"for (i = [0 : {cnt} - 1])",
            f"  rotate([0, 0, i * 360 / {cnt}])",
            f"    translate([{0.5 * float(p['pcd']):.3f}, 0, 0])",
            f"      cylinder(d={float(p['bolt_d']):.3f}, h={float(p['h']):.3f}, center=true);",
        ]
    elif op == "cut_slot":
        length = float(p["length"])
        width = float(p["width"])
        h = float(p["h"])
        dx = max(0.0, length - width)
        body = [
            "hull() {",
            f"  translate([{-0.5 * dx:.3f}, 0, 0]) cylinder(d={width:.3f}, h={h:.3f}, center=true);",
            f"  translate([{0.5 * dx:.3f}, 0, 0]) cylinder(d={width:.3f}, h={h:.3f}, center=true);",
            "}",
        ]
    elif op == "cut_grid_holes":
        nx, ny = int(p["nx"]), int(p["ny"])
        px, py = float(p["pitch_x"]), float(p["pitch_y"])
        hd, h = float(p["hole_d"]), float(p["h"])
        body = [
            f"for (ix = [0 : {nx} - 1])",
            f"  for (iy = [0 : {ny} - 1])",
            f"    translate([(ix - {(nx - 1) / 2.0:.3f}) * {px:.4f}, (iy - {(ny - 1) / 2.0:.3f}) * {py:.4f}, 0])",
            f"      cylinder(d={hd:.4f}, h={h:.3f}, center=true);",
        ]
    elif op == "raw":
        body = [str(p["code"])]
    else:
        raise ValueError(f"Unsupported ScadFeature op: {op!r}")

    out.extend(_wrap_transform(body, feat.translate, feat.rotate, indent))
    return out


def _rotation_for_normal(n: tuple[float, float, float]) -> tuple[float, float, float]:
    nx, ny, nz = n
    if abs(nz - 1.0) < 1e-3:
        return (0.0, 0.0, 0.0)
    if abs(nz + 1.0) < 1e-3:
        return (180.0, 0.0, 0.0)
    if abs(nx - 1.0) < 1e-3:
        return (0.0, 90.0, 0.0)
    if abs(nx + 1.0) < 1e-3:
        return (0.0, -90.0, 0.0)
    if abs(ny - 1.0) < 1e-3:
        return (-90.0, 0.0, 0.0)
    if abs(ny + 1.0) < 1e-3:
        return (90.0, 0.0, 0.0)
    return (0.0, 0.0, 0.0)


def _synthesize_default_features(
    mesh: SolidMesh,
    part_design: PartDesign | None,
) -> list[ScadFeature]:
    """Synthesize clean parametric OpenSCAD CSG features from mesh extents & ports."""
    bmin, bmax = mesh.bbox()
    dx = max(bmax[0] - bmin[0], 0.1)
    dy = max(bmax[1] - bmin[1], 0.1)
    dz = max(bmax[2] - bmin[2], 0.1)
    cx = 0.5 * (bmin[0] + bmax[0])
    cy = 0.5 * (bmin[1] + bmax[1])
    cz = 0.5 * (bmin[2] + bmax[2])

    feats: list[ScadFeature] = []
    # Check if outer shape is cylindrical in XY
    if abs(dx - dy) / max(dx, dy) < 0.025:
        feats.append(
            ScadFeature(
                op="add_cylinder",
                params={"d": 0.5 * (dx + dy), "h": dz},
                translate=(cx, cy, cz),
                comment="Primary cylindrical body envelope",
            )
        )
    else:
        feats.append(
            ScadFeature(
                op="add_box",
                params={"dx": dx, "dy": dy, "dz": dz},
                translate=(cx, cy, cz),
                comment="Primary prismatic body envelope",
            )
        )

    # Emit port bores & bolt circles as real difference() cutouts
    ports: Sequence[PortInterface] = part_design.ports if part_design else ()
    for port in ports:
        rot = _rotation_for_normal(port.normal)
        cut_depth = max(dx, dy, dz) + 2.0
        if port.bore_mm > 0.0:
            feats.append(
                ScadFeature(
                    op="cut_hole",
                    params={"d": port.bore_mm, "h": cut_depth},
                    translate=port.position_mm,
                    rotate=rot,
                    comment=f"Port {port.name} ({port.standard}) bore Ø{port.bore_mm:.2f} mm",
                )
            )
        if port.pcd_mm > 0.0 and port.bolt_count > 0 and port.bolt_hole_mm > 0.0:
            feats.append(
                ScadFeature(
                    op="cut_bolt_circle",
                    params={
                        "pcd": port.pcd_mm,
                        "bolt_d": port.bolt_hole_mm,
                        "count": port.bolt_count,
                        "h": cut_depth,
                    },
                    translate=port.position_mm,
                    rotate=rot,
                    comment=f"Port {port.name} bolt circle {port.bolt_count}xØ{port.bolt_hole_mm:.1f} @ PCD {port.pcd_mm:.1f}",
                )
            )
    return feats


# ---------------------------------------------------------------------------
# OpenSCAD Writer
# ---------------------------------------------------------------------------
def write_scad(
    mesh: SolidMesh,
    path: Path | str,
    *,
    part_design: PartDesign | None = None,
    features: Sequence[ScadFeature] | None = None,
    mass_props: MassProperties | None = None,
    fn_segments: int = 64,
) -> Path:
    """Emit a parametric OpenSCAD ``.scad`` module file for one BOM ``part_id``."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    mp = mass_props if mass_props is not None else compute_mass_props(
        mesh, material=(part_design.material if part_design else mesh.material)
    )
    part_id = part_design.part_id if part_design else (mesh.name or out_path.stem)
    parent_id = part_design.parent_bom_id if part_design else "-"
    subsystem = part_design.subsystem if part_design else "-"
    part_name = part_design.part_name if part_design else part_id
    mat = part_design.material if part_design else mesh.material
    temp = part_design.temp_stage if part_design else "300 K"
    vac = part_design.vacuum_grade if part_design else "UHV 1e-9 mbar"
    tol = part_design.tolerance_spec if part_design else "ISO 2768-mK"
    origin = part_design.world_origin_mm if part_design else (0.0, 0.0, 0.0)
    rot_deg = part_design.world_rotation_deg if part_design else (0.0, 0.0, 0.0)
    maturity = part_design.design_maturity if part_design else DESIGN_MATURITY
    no_lab = part_design.no_lab_measurement if part_design else NO_LAB_MEASUREMENT
    iec = part_design.iec61508_certified if part_design else IEC61508_CERTIFIED
    semi = part_design.semi_s2_certified if part_design else SEMI_S2_CERTIFIED

    mod_name = f"part_{sanitize_scad_id(part_id)}"
    ex, ey, ez = mp.extents_mm

    feat_list = list(features) if features is not None else _synthesize_default_features(mesh, part_design)
    add_feats = [f for f in feat_list if not f.is_cut]
    cut_feats = [f for f in feat_list if f.is_cut]

    lines: list[str] = [
        "// ============================================================================",
        f"// Atom Lithography Machine — Parametric OpenSCAD Module ({part_id})",
        "// ============================================================================",
        f"// part_id           : {part_id}",
        f"// parent_bom_id     : {parent_id}",
        f"// subsystem         : {subsystem}",
        f"// part_name         : {part_name}",
        f"// material          : {mat}",
        f"// temp_stage        : {temp}",
        f"// vacuum_grade      : {vac}",
        f"// tolerance         : {tol}",
        f"// computed_mass_kg  : {mp.mass_kg:.5f}",
        f"// envelope_mm       : {ex:.3f} x {ey:.3f} x {ez:.3f}",
        f"// design_maturity   : {maturity}",
        f"// no_lab_measurement: {str(no_lab).lower()}",
        f"// iec61508_certified: {str(iec).lower()}",
        f"// semi_s2_certified : {str(semi).lower()}",
        "// Units: millimeters (mm)",
        "// ============================================================================",
        "",
        f"$fn = {int(fn_segments)};",
        "",
        "// Nominal bounding envelope parameters (mm)",
        f"bbox_x = {ex:.4f};",
        f"bbox_y = {ey:.4f};",
        f"bbox_z = {ez:.4f};",
    ]

    # User-specified parametric variables
    if part_design is not None and part_design.scad_params:
        lines.append("")
        lines.append("// Part-specific parametric dimensions")
        for k, v in part_design.scad_params:
            ident = sanitize_scad_id(k)
            if isinstance(v, str):
                esc = v.replace('"', '\\"')
                lines.append(f'{ident} = "{esc}";')
            elif isinstance(v, bool):
                lines.append(f"{ident} = {'true' if v else 'false'};")
            else:
                lines.append(f"{ident} = {v};")

    # Port interface parameter declarations
    if part_design is not None and part_design.ports:
        lines.append("")
        lines.append("// Interface / port parameters (mm)")
        for p in part_design.ports:
            p_id = sanitize_scad_id(p.name)
            if p.od_mm > 0.0:
                lines.append(f"port_{p_id}_od = {p.od_mm:.3f};")
            if p.bore_mm > 0.0:
                lines.append(f"port_{p_id}_bore = {p.bore_mm:.3f};")
            if p.pcd_mm > 0.0:
                lines.append(f"port_{p_id}_pcd = {p.pcd_mm:.3f};")
            if p.bolt_count > 0:
                lines.append(f"port_{p_id}_bolts = {p.bolt_count};")

    lines.extend(["", f"module {mod_name}() {{"])
    if cut_feats:
        lines.append("  difference() {")
        lines.append("    union() {")
        for af in add_feats:
            lines.extend(_render_feature(af, indent="      "))
        lines.append("    }")
        for cf in cut_feats:
            lines.extend(_render_feature(cf, indent="    "))
        lines.append("  }")
    else:
        lines.append("  union() {")
        for af in add_feats:
            lines.extend(_render_feature(af, indent="    "))
        lines.append("  }")
    lines.append("}")
    lines.extend(
        [
            "",
            "// World assembly mounting transform (global machine frame, mm / deg):",
            (
                f"// translate([{origin[0]:.3f}, {origin[1]:.3f}, {origin[2]:.3f}]) "
                f"rotate([{rot_deg[0]:.3f}, {rot_deg[1]:.3f}, {rot_deg[2]:.3f}]) "
                f"{mod_name}();"
            ),
            "",
            f"{mod_name}();",
            "",
        ]
    )

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Strict Independent OpenSCAD Syntax & Metadata Validator
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ScadValidationResult:
    """Validation report for a parametric OpenSCAD ``.scad`` module."""

    valid: bool
    module_name: str
    balanced_delimiters: bool
    has_parameters: bool
    has_csg_primitives: bool
    has_mounting_transform: bool
    has_epistemic_header: bool
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_scad_file(path: Path | str) -> ScadValidationResult:
    """Validate balanced syntax, module declaration, CSG primitives, and epistemic header."""
    errors: list[str] = []
    p = Path(path)
    if not p.is_file():
        return ScadValidationResult(
            valid=False,
            module_name="",
            balanced_delimiters=False,
            has_parameters=False,
            has_csg_primitives=False,
            has_mounting_transform=False,
            has_epistemic_header=False,
            errors=(f"SCAD file does not exist: {p}",),
        )

    text = p.read_text(encoding="utf-8")

    # Strip line comments and strings before checking delimiter balance
    code_lines = []
    for ln in text.splitlines():
        code_lines.append(re.sub(r"//.*$", "", ln))
    code = "\n".join(code_lines)
    code_no_str = re.sub(r'"(?:\\.|[^"])*"', '""', code)

    stack: list[str] = []
    pairs = {"}": "{", ")": "(", "]": "["}
    balanced = True
    for ch in code_no_str:
        if ch in "{([":
            stack.append(ch)
        elif ch in "})]":
            if not stack or stack[-1] != pairs[ch]:
                balanced = False
                break
            stack.pop()
    if stack:
        balanced = False
    if not balanced:
        errors.append("Unbalanced braces/parentheses/brackets in .scad code")

    mod_m = re.search(r"\bmodule\s+(part_[0-9A-Za-z_]+)\s*\(", code)
    mod_name = mod_m.group(1) if mod_m else ""
    if not mod_name:
        errors.append("Missing 'module part_<id>()' declaration")

    has_params = bool(re.search(r"^\s*[A-Za-z_$][A-Za-z0-9_]*\s*=\s*.+;", code, re.MULTILINE))
    if not has_params:
        errors.append("No parametric variable declarations found")

    has_csg = any(
        kw in code
        for kw in ("cylinder(", "cube(", "rotate_extrude(", "polyhedron(", "difference()", "union()")
    )
    if not has_csg:
        errors.append("No OpenSCAD CSG primitives found")

    has_mount = "translate([" in text and "rotate([" in text
    if not has_mount:
        errors.append("Missing world mounting transform comment")

    has_epistemic = (
        DESIGN_MATURITY in text
        and bool(re.search(r"no_lab_measurement\s*:\s*true", text))
        and bool(re.search(r"iec61508_certified\s*:\s*false", text))
        and bool(re.search(r"semi_s2_certified\s*:\s*false", text))
    )
    if not has_epistemic:
        errors.append("Missing epistemic status header lines")

    return ScadValidationResult(
        valid=(len(errors) == 0),
        module_name=mod_name,
        balanced_delimiters=balanced,
        has_parameters=has_params,
        has_csg_primitives=has_csg,
        has_mounting_transform=has_mount,
        has_epistemic_header=has_epistemic,
        errors=tuple(errors),
    )
