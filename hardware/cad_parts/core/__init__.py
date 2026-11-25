"""Pure-Python mechanical CAD & manufacturing export kernel (Wave 2A / WP-M0).

Public entry point imported by subsystem designers (``WP-M1..M5``) and the
assembly integrator (``WP-M6``) to design, verify, and export all 164 physical
BOM parts into watertight binary STL, ISO 10303-21 AP214 STEP, parametric
OpenSCAD, ASCII R12 DXF, and ISO 128 / ASME Y14.5 white-paper SVG GD&T sheets.
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .cf_flanges import (
    CF_SPECS,
    ISO_K_SPECS,
    CFSpec,
    IsoKSpec,
    get_cf_spec,
    get_isok_spec,
    make_cf_blank_flange,
    make_cf_flange,
    make_cf_port_interface,
    make_cf_viewport,
    make_cf_weld_neck,
    make_isok_flange,
)
from .dxf_writer import (
    REQUIRED_DXF_LAYERS,
    DxfValidationResult,
    ProjectedView,
    extract_iso_view,
    extract_ortho_view,
    validate_dxf_file,
    write_dxf,
)
from .feature_engine import (
    MATERIAL_DENSITIES_KG_M3,
    MassProperties,
    MeshValidationResult,
    SolidMesh,
    circle_2d,
    compute_mass_props,
    lookup_density_kg_m3,
    make_bellows,
    make_box,
    make_chamfered_box,
    make_counterbored_plate,
    make_cylinder,
    make_frustum,
    make_hemisphere_shell,
    make_mems_grid_plate,
    make_plate_with_holes,
    make_rect_plate_with_features,
    make_revolved_profile,
    make_ring_with_bolt_circle,
    make_s_braid,
    make_sphere,
    make_swept_tube,
    make_tube,
    merge_solids,
    read_binary_stl,
    rect_2d,
    slot_2d,
    split_shells,
    transform_mesh,
    triangulate_polygon_with_holes,
    verify_watertight,
    write_binary_stl,
)
from .part_schema import (
    DEFAULT_BOM_PATH,
    DESIGN_MATURITY,
    DRAWING_STANDARD,
    GDT_SYMBOL_MAP,
    GENERAL_TOLERANCE_STD,
    IEC61508_CERTIFIED,
    NO_LAB_MEASUREMENT,
    NON_SOLID_PART_IDS,
    REPO_ROOT,
    SEMI_S2_CERTIFIED,
    SOURCE_BOM_VERSION,
    STEP_PROTOCOL,
    SUPERSEDED_PART_IDS,
    VALID_DESIGN_TIERS,
    VALID_PORT_KINDS,
    BomRow,
    DimensionCallout,
    GDTFrame,
    PartArtifactResult,
    PartDesign,
    PortInterface,
    get_bom_row,
    infer_design_tier,
    list_physical_part_ids,
    load_bom_table,
    make_part_design_from_bom,
    parse_nominal_temp_k,
)
from .scad_writer import (
    ScadFeature,
    ScadValidationResult,
    sanitize_scad_id,
    validate_scad_file,
    write_scad,
)
from .step_writer import (
    StepValidationResult,
    prepare_step_mesh,
    validate_step_file,
    write_step,
)
from .svg_gdt_writer import (
    APPROVED_ACADEMIC_PALETTE,
    COLOR_CANVAS,
    COLOR_DIM,
    COLOR_INK,
    COLOR_MUTED,
    SvgValidationResult,
    validate_svg_file,
    write_svg_gdt,
)
from .thermal_gdt import (
    NIST_THERMAL_CONTRACTION_TABLE,
    TEMP_GRID_K,
    ColdClearanceResult,
    ToleranceContributor,
    ToleranceStackResult,
    check_cold_clearance,
    check_tolerance_stack,
    cold_dimension_mm,
    integrated_thermal_contraction,
    resolve_thermal_material,
)


def export_part_artifacts(
    part_design: PartDesign,
    mesh: SolidMesh,
    out_dir: Path | str,
    *,
    scad_features: Sequence[ScadFeature] | None = None,
    step_mesh: SolidMesh | None = None,
    max_step_faces: int = 800,
    density_kg_m3: float | None = None,
    flat: bool = True,
) -> PartArtifactResult:
    """Verify and export all 5 manufacturing artifacts (.stl/.step/.scad/.dxf/.svg) for one part.

    When ``flat=True`` (default), writes ``<out_dir>/<part_id>.{stl,step,scad,dxf,svg}``.
    When ``flat=False``, writes into format subdirectories under ``<out_dir>``.
    """
    base = Path(out_dir)
    pid = part_design.part_id
    if flat:
        stl_p = base / f"{pid}.stl"
        step_p = base / f"{pid}.step"
        scad_p = base / f"{pid}.scad"
        dxf_p = base / f"{pid}.dxf"
        svg_p = base / f"{pid}.svg"
    else:
        stl_p = base / "stl" / f"{pid}.stl"
        step_p = base / "step" / f"{pid}.step"
        scad_p = base / "scad" / f"{pid}.scad"
        dxf_p = base / "dxf" / f"{pid}.dxf"
        svg_p = base / "svg" / f"{pid}.svg"

    val = verify_watertight(mesh)
    mp = compute_mass_props(mesh, material=part_design.material, density_kg_m3=density_kg_m3)

    write_binary_stl(mesh, stl_p, header_text=f"{pid} | {part_design.design_maturity} | mm")
    write_step(mesh, step_p, part_design=part_design, step_mesh=step_mesh, max_faces=max_step_faces)
    write_scad(mesh, scad_p, part_design=part_design, features=scad_features, mass_props=mp)
    write_dxf(mesh, dxf_p, part_design=part_design, mass_props=mp)
    write_svg_gdt(mesh, svg_p, part_design=part_design, mass_props=mp)

    step_val = validate_step_file(step_p)
    dxf_val = validate_dxf_file(dxf_p)
    svg_val = validate_svg_file(svg_p)
    scad_val = validate_scad_file(scad_p)

    warnings: list[str] = []
    warnings.extend(val.errors)
    warnings.extend(step_val.errors)
    warnings.extend(dxf_val.errors)
    warnings.extend(svg_val.errors)
    warnings.extend(scad_val.errors)

    # Store repository-relative POSIX paths when inside REPO_ROOT for portability
    def _rel(p: Path) -> str:
        try:
            return p.resolve().relative_to(REPO_ROOT).as_posix()
        except ValueError:
            return p.as_posix()

    return PartArtifactResult(
        part_id=pid,
        subsystem=part_design.subsystem,
        design_tier=part_design.design_tier,
        stl_path=_rel(stl_p),
        step_path=_rel(step_p),
        scad_path=_rel(scad_p),
        dxf_path=_rel(dxf_p),
        svg_path=_rel(svg_p),
        watertight=val.watertight,
        boundary_edges=val.boundary_edges,
        non_manifold_edges=val.non_manifold_edges,
        signed_volume_mm3=val.signed_volume_mm3,
        surface_area_mm2=val.surface_area_mm2,
        mass_kg=mp.mass_kg,
        cg_mm=mp.cg_mm,
        bbox_min_mm=mp.bbox_min_mm,
        bbox_max_mm=mp.bbox_max_mm,
        inertia_kg_mm2=mp.inertia_kg_mm2,
        triangle_count=mesh.n_faces,
        vertex_count=mesh.n_vertices,
        step_valid=step_val.valid,
        dxf_valid=dxf_val.valid,
        svg_valid=svg_val.valid,
        scad_valid=scad_val.valid,
        design_maturity=part_design.design_maturity,
        no_lab_measurement=part_design.no_lab_measurement,
        iec61508_certified=part_design.iec61508_certified,
        semi_s2_certified=part_design.semi_s2_certified,
        warnings=tuple(warnings),
    )


__all__ = [
    # Schema & BOM
    "BomRow",
    "PortInterface",
    "DimensionCallout",
    "GDTFrame",
    "PartDesign",
    "PartArtifactResult",
    "DESIGN_MATURITY",
    "NO_LAB_MEASUREMENT",
    "IEC61508_CERTIFIED",
    "SEMI_S2_CERTIFIED",
    "GENERAL_TOLERANCE_STD",
    "DRAWING_STANDARD",
    "STEP_PROTOCOL",
    "SOURCE_BOM_VERSION",
    "VALID_DESIGN_TIERS",
    "VALID_PORT_KINDS",
    "NON_SOLID_PART_IDS",
    "SUPERSEDED_PART_IDS",
    "GDT_SYMBOL_MAP",
    "REPO_ROOT",
    "DEFAULT_BOM_PATH",
    "load_bom_table",
    "get_bom_row",
    "list_physical_part_ids",
    "infer_design_tier",
    "parse_nominal_temp_k",
    "make_part_design_from_bom",
    # Feature Engine
    "SolidMesh",
    "MeshValidationResult",
    "MassProperties",
    "MATERIAL_DENSITIES_KG_M3",
    "lookup_density_kg_m3",
    "verify_watertight",
    "compute_mass_props",
    "transform_mesh",
    "merge_solids",
    "split_shells",
    "make_box",
    "make_chamfered_box",
    "make_cylinder",
    "make_frustum",
    "make_tube",
    "make_sphere",
    "make_revolved_profile",
    "make_bellows",
    "make_hemisphere_shell",
    "rect_2d",
    "circle_2d",
    "slot_2d",
    "triangulate_polygon_with_holes",
    "make_plate_with_holes",
    "make_rect_plate_with_features",
    "make_counterbored_plate",
    "make_mems_grid_plate",
    "make_ring_with_bolt_circle",
    "make_swept_tube",
    "make_s_braid",
    "write_binary_stl",
    "read_binary_stl",
    # CF & ISO-K Flanges
    "CFSpec",
    "IsoKSpec",
    "CF_SPECS",
    "ISO_K_SPECS",
    "get_cf_spec",
    "get_isok_spec",
    "make_cf_flange",
    "make_cf_blank_flange",
    "make_cf_weld_neck",
    "make_cf_viewport",
    "make_isok_flange",
    "make_cf_port_interface",
    # STEP
    "StepValidationResult",
    "prepare_step_mesh",
    "write_step",
    "validate_step_file",
    # DXF & Ortho Projection
    "REQUIRED_DXF_LAYERS",
    "ProjectedView",
    "DxfValidationResult",
    "extract_ortho_view",
    "extract_iso_view",
    "write_dxf",
    "validate_dxf_file",
    # SVG GD&T
    "APPROVED_ACADEMIC_PALETTE",
    "COLOR_CANVAS",
    "COLOR_INK",
    "COLOR_DIM",
    "COLOR_MUTED",
    "SvgValidationResult",
    "write_svg_gdt",
    "validate_svg_file",
    # OpenSCAD
    "ScadFeature",
    "ScadValidationResult",
    "sanitize_scad_id",
    "write_scad",
    "validate_scad_file",
    # Thermal & GD&T Stackup
    "TEMP_GRID_K",
    "NIST_THERMAL_CONTRACTION_TABLE",
    "ColdClearanceResult",
    "ToleranceContributor",
    "ToleranceStackResult",
    "resolve_thermal_material",
    "integrated_thermal_contraction",
    "cold_dimension_mm",
    "check_cold_clearance",
    "check_tolerance_stack",
    # Unified Export Pipeline
    "export_part_artifacts",
]
