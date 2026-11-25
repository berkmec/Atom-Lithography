"""Comprehensive verification suite for the pure-Python mechanical CAD kernel (WP-M0).

Tests every module in ``hardware/cad_parts/core/``:
1. ``part_schema.py``: frozen dataclasses, exact BOM part_id loading (180 total, 164 physical),
   zero bom_id aliasing enforcement, epistemic metadata defaults.
2. ``feature_engine.py``: watertightness (0 boundary, 0 non-manifold, 0 orientation errors,
   positive signed volume) for boxes, cylinders, tubes, spheres, revolved bellows (28 conv),
   HDA-HiRes hemispheres, arbitrary polygon-with-holes, counterbored plates, 32x32=1024 MEMS
   aperture plates, bolt-circle rings, 3D swept tubes & cryo S-braids, transforms, exact
   analytical mass/CG/inertia tensor verification, binary STL round-trip, and negative
   detection of open/inverted meshes.
3. ``cf_flanges.py``: all 8 ISO 3669 ConFlat sizes (CF16..CF400) exact PCD/bolt count/hole Ø
   + watertight flange, blank, weld-neck, and stepped optical viewport solids + all 4 ISO-K
   sizes (DN50..DN250).
4. ``step_writer.py``: ISO 10303-21 AP214 export (exact + decimated/proxy for >800-face meshes),
   exact bbox preservation, strict validator passing valid files and rejecting dangling refs.
5. ``dxf_writer.py``: AC1009 R12 3-view orthographic export with all 5 required layers
   (OUTLINE, HIDDEN, CENTER, DIMS, TITLEBLOCK), strict validator + negative check.
6. ``svg_gdt_writer.py``: ISO 128 / ASME Y14.5 well-formed XML, strict white-paper academic
   palette (#FFFFFF/#111827/#1B365D/#64748B, zero flashy colors), 4 views, GD&T frames,
   datum triangles, Ra surface finish, epistemic stamp + negative flashy-color rejection.
7. ``scad_writer.py``: parametric OpenSCAD module emitter with real difference() bolt circles,
   slots, MEMS grids, mounting transforms, header metadata + negative syntax rejection.
8. ``thermal_gdt.py``: real NIST cryogenic contraction signs/magnitudes (300K->100K->50K->4K->20mK)
   for all 12 core materials, cold-clearance pass & interference catch, RSS/WC stackup exact math.
9. ``export_part_artifacts``: end-to-end 5-artifact pipeline verification.
"""
from __future__ import annotations

import dataclasses
import math
from pathlib import Path

import numpy as np
import pytest

from hardware.cad_parts.core import (
    APPROVED_ACADEMIC_PALETTE,
    CF_SPECS,
    COLOR_CANVAS,
    DESIGN_MATURITY,
    ISO_K_SPECS,
    MATERIAL_DENSITIES_KG_M3,
    NIST_THERMAL_CONTRACTION_TABLE,
    REQUIRED_DXF_LAYERS,
    DimensionCallout,
    GDTFrame,
    PartDesign,
    PortInterface,
    ScadFeature,
    SolidMesh,
    ToleranceContributor,
    check_cold_clearance,
    check_tolerance_stack,
    circle_2d,
    cold_dimension_mm,
    compute_mass_props,
    export_part_artifacts,
    get_bom_row,
    integrated_thermal_contraction,
    list_physical_part_ids,
    load_bom_table,
    lookup_density_kg_m3,
    make_bellows,
    make_box,
    make_cf_blank_flange,
    make_cf_flange,
    make_cf_port_interface,
    make_cf_viewport,
    make_cf_weld_neck,
    make_chamfered_box,
    make_counterbored_plate,
    make_cylinder,
    make_hemisphere_shell,
    make_isok_flange,
    make_mems_grid_plate,
    make_part_design_from_bom,
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
    sanitize_scad_id,
    slot_2d,
    transform_mesh,
    validate_dxf_file,
    validate_scad_file,
    validate_step_file,
    validate_svg_file,
    verify_watertight,
    write_binary_stl,
    write_dxf,
    write_scad,
    write_step,
    write_svg_gdt,
)


# ===========================================================================
# 1. Part Schema & Zero-Aliasing BOM Loader
# ===========================================================================
class TestPartSchemaAndBom:
    def test_bom_counts_and_exact_keying(self) -> None:
        table = load_bom_table()
        assert len(table) == 180
        phys = list_physical_part_ids()
        assert len(phys) == 164
        # Verify exact subsystem physical counts matching audit #282
        expected_sub = {
            "S1": 23,
            "S2": 15,
            "S3": 14,
            "S4": 17,
            "S5": 23,
            "S6": 40,
            "S7": 19,
            "S9": 13,
        }
        for sub, cnt in expected_sub.items():
            assert len(list_physical_part_ids(subsystem=sub)) == cnt
        assert len(list_physical_part_ids(subsystem="S8")) == 0

    def test_zero_bom_id_aliasing(self) -> None:
        # Exact part_ids resolve cleanly
        assert get_bom_row("S1.7-01").subsystem == "S1"
        assert get_bom_row("S6.11-01").subsystem == "S6"
        assert get_bom_row("S9.4-01").subsystem == "S9"
        assert get_bom_row("S7.SAFETY-02").subsystem == "S7"

        # Parent bom_id aliases MUST fail loudly
        for alias in ("S1.6", "S6.5", "S9.1", "S7.SAFETY"):
            with pytest.raises(KeyError, match="Aliased parent_bom_id"):
                get_bom_row(alias)

        # PartDesign also rejects parent_bom_id aliases
        with pytest.raises(ValueError, match="exact BOM part_id"):
            PartDesign(
                part_id="S1.6",
                parent_bom_id="S1.6",
                subsystem="S1",
                part_name="Bad alias",
            )

    def test_frozen_dataclasses_and_epistemic_metadata(self) -> None:
        pd = make_part_design_from_bom("S1.5-01")
        assert pd.part_id == "S1.5-01"
        assert pd.parent_bom_id == "S1.5"
        assert pd.design_tier == "CUSTOM_FULL"
        assert pd.design_maturity == DESIGN_MATURITY
        assert pd.no_lab_measurement is True
        assert pd.iec61508_certified is False
        assert pd.semi_s2_certified is False
        with pytest.raises(dataclasses.FrozenInstanceError):
            pd.part_id = "MUTATED"  # type: ignore[misc]

        port = PortInterface(
            name="inlet_cf100",
            kind="flange",
            position_mm=(0.0, 0.0, 50.0),
            normal=(0.0, 0.0, 2.0),  # auto-normalized
            standard="CF100",
            mating_part_id="S5.1-01",
            bore_mm=101.6,
            od_mm=152.0,
            pcd_mm=130.2,
            bolt_count=16,
            bolt_hole_mm=8.4,
        )
        assert math.isclose(port.normal[2], 1.0, rel_tol=1e-9)

        dc = DimensionCallout("OD", 152.0, 0.05, -0.05, prefix="Ø")
        assert "Ø152.00" in dc.format_text() and "±0.05" in dc.format_text()

        gdt = GDTFrame("perpendicularity", 0.010, diameter_zone=True, datum_primary="A")
        assert gdt.glyph() == "⊥"
        assert gdt.tolerance_text() == "Ø0.010"


# ===========================================================================
# 2. Feature Engine: Watertight Solids, Mass Properties & Binary STL
# ===========================================================================
class TestFeatureEngine:
    def test_primitives_and_transforms_watertight(self) -> None:
        solids = [
            make_box(40.0, 30.0, 20.0),
            make_chamfered_box(40.0, 30.0, 20.0, chamfer=3.0),
            make_cylinder(15.0, 50.0, axis="x"),
            make_cylinder(15.0, 50.0, r_top=8.0, axis="y"),
            make_tube(10.0, 15.0, 60.0, axis="z"),
            make_sphere(5.0),
        ]
        for s in solids:
            r = verify_watertight(s)
            assert r.watertight, f"{s.name} failed: {r}"
            assert r.boundary_edges == 0
            assert r.non_manifold_edges == 0
            assert r.orientation_errors == 0
            assert r.signed_volume_mm3 > 0.0

        # Transform preserves volume and watertightness
        b = make_box(20.0, 10.0, 5.0)
        bt = transform_mesh(
            b,
            translation=(100.0, -50.0, 250.0),
            rotation_deg=(30.0, 45.0, 60.0),
            axis_angle=([1.0, 1.0, 1.0], 25.0),
        )
        rt = verify_watertight(bt)
        assert rt.watertight
        assert math.isclose(rt.signed_volume_mm3, 1000.0, rel_tol=1e-6)

    def test_revolved_bellows_and_hemisphere_watertight(self) -> None:
        # S6.9-02 exact 28-convolution edge-welded bellows (ID=44, OD=68, L=120, t=0.15)
        bellows = make_bellows(
            r_in=22.0, r_out=34.0, length=120.0, n_convolutions=28, wall_thickness=0.15
        )
        rb = verify_watertight(bellows)
        assert rb.watertight, f"Bellows failed: {rb}"
        assert rb.boundary_edges == 0 and rb.non_manifold_edges == 0
        bmin, bmax = bellows.bbox()
        assert math.isclose(bmax[2] - bmin[2], 120.0, abs_tol=1e-6)
        assert math.isclose(bmax[0] - bmin[0], 68.0, abs_tol=0.15)

        # S1.5-01 concentric HDA-HiRes inner/outer hemispheres (R0=40 mm)
        h_in = make_hemisphere_shell(r_in=32.0, r_out=36.0, segments=64, lat_steps=20)
        h_out = make_hemisphere_shell(r_in=44.0, r_out=48.0, segments=64, lat_steps=20)
        for h, ri, ro in ((h_in, 32.0, 36.0), (h_out, 44.0, 48.0)):
            rh = verify_watertight(h)
            assert rh.watertight, f"Hemisphere failed: {rh}"
            # Analytical hemisphere shell volume = (2/3)*pi*(ro^3 - ri^3)
            v_exact = (2.0 / 3.0) * math.pi * (ro**3 - ri**3)
            assert math.isclose(rh.signed_volume_mm3, v_exact, rel_tol=0.015)

        # Axisymmetric multi-step Einzel/decel electrode (CW input auto-normalized)
        stepped_cw = [(15.0, 0.0), (15.0, 20.0), (35.0, 20.0), (35.0, 5.0), (25.0, 5.0), (25.0, 0.0)]
        elec = make_revolved_profile(stepped_cw, segments=48)
        assert verify_watertight(elec).watertight

    def test_plates_with_holes_slots_counterbores_and_32x32_mems(self) -> None:
        # Arbitrary polygon with multiple circular holes + angled slots
        plate = make_rect_plate_with_features(
            100.0,
            80.0,
            10.0,
            circular_holes=[(-30.0, -20.0, 8.0), (30.0, -20.0, 8.0), (30.0, 20.0, 8.0), (-30.0, 20.0, 8.0)],
            rect_slots=[(0.0, 0.0, 30.0, 10.0, 25.0)],
        )
        rp = verify_watertight(plate)
        assert rp.watertight
        assert rp.euler_characteristic == 2 - 2 * 5  # genus 5 (4 holes + 1 slot)

        # Stepped counterbored plate (single watertight shell)
        cb = make_counterbored_plate(
            rect_2d(80.0, 50.0),
            counterbored_holes=[(-20.0, 0.0, 6.0, 11.0), (20.0, 0.0, 6.0, 11.0)],
            total_thickness=14.0,
            cbore_depth=6.0,
        )
        rcb = verify_watertight(cb)
        assert rcb.watertight
        assert rcb.n_shells == 1
        assert rcb.euler_characteristic == 2 - 2 * 2

        # 32x32 = 1024-hole Arch-B MEMS aperture wafer (S2.1-01: 0.50 mm pitch, D=0.30 mm, Ø28 mm)
        mems = make_mems_grid_plate(
            width_x=24.0,
            width_y=24.0,
            thickness=0.030,
            nx=32,
            ny=32,
            pitch_x=0.50,
            pitch_y=0.50,
            hole_diameter=0.30,
            outer_diameter=28.0,
            material="Si",
        )
        rm = verify_watertight(mems)
        assert rm.watertight, f"32x32 MEMS failed: {rm}"
        assert rm.boundary_edges == 0
        assert rm.non_manifold_edges == 0
        assert rm.orientation_errors == 0
        assert rm.euler_characteristic == 2 - 2 * 1024  # Exact genus 1024!
        # Analytical wafer area minus 1024 octagonal holes
        r_h = 0.15
        oct_area = 2.0 * math.sqrt(2.0) * (r_h**2)
        expected_vol = (math.pi * 14.0**2 - 1024 * oct_area) * 0.030
        assert math.isclose(rm.signed_volume_mm3, expected_vol, rel_tol=0.01)

    def test_swept_tube_and_cryo_s_braid_watertight(self) -> None:
        spine = [[0, 0, 0], [15, 5, 20], [25, 20, 45], [10, 35, 70], [0, 35, 95]]
        coax = make_swept_tube(spine, r_out=2.2, r_in=1.2, segments=20, material="CuNi")
        rod = make_swept_tube(spine, r_out=2.2, r_in=0.0, segments=20, material="OFHC Cu")
        assert verify_watertight(coax).watertight
        assert verify_watertight(rod).watertight

        braid = make_s_braid(
            length_mm=100.0, s_amplitude_mm=15.0, width_mm=10.0, thickness_mm=2.0, lug_length_mm=12.0
        )
        rb = verify_watertight(braid)
        assert rb.watertight
        assert rb.n_shells == 3

    def test_exact_mass_cg_inertia_and_material_table(self) -> None:
        # Check all 20 required materials exist with physical densities
        required_mats = [
            "316LN", "OFHC Cu", "Ti-6Al-4V", "Al2O3", "AlN", "Mo", "Invar-36",
            "Zerodur", "Si", "Nb", "NbTi", "Mu-metal", "Cryoperm", "Vespel SP-22",
            "PEEK", "Granite", "FR4", "Rogers", "Al 6061", "Graphite", "Sapphire", "SmCo",
        ]
        for mat in required_mats:
            rho = lookup_density_kg_m3(mat)
            assert 1000.0 <= rho <= 20000.0, f"Unexpected density for {mat}: {rho}"

        # Analytical box inertia verification: a=60, b=40, c=20 mm shifted to (10, -5, 30)
        a, b, c = 60.0, 40.0, 20.0
        box = make_box(a, b, c, center=(10.0, -5.0, 30.0), material="OFHC Cu")
        mp = compute_mass_props(box, material="OFHC Cu")
        expected_mass = (a * b * c * 1e-9) * 8960.0
        assert math.isclose(mp.mass_kg, expected_mass, rel_tol=1e-9)
        assert np.allclose(mp.cg_mm, (10.0, -5.0, 30.0), atol=1e-9)
        ixx, iyy, izz, ixy, ixz, iyz = mp.inertia_kg_mm2
        assert math.isclose(ixx, expected_mass * (b**2 + c**2) / 12.0, rel_tol=1e-8)
        assert math.isclose(iyy, expected_mass * (a**2 + c**2) / 12.0, rel_tol=1e-8)
        assert math.isclose(izz, expected_mass * (a**2 + b**2) / 12.0, rel_tol=1e-8)
        assert abs(ixy) < 1e-12 and abs(ixz) < 1e-12 and abs(iyz) < 1e-12

    def test_verify_watertight_rejects_broken_meshes(self) -> None:
        box = make_box(10.0, 10.0, 10.0)
        # Missing face -> open boundary edges
        open_mesh = SolidMesh(box.vertices, box.faces[:-1])
        ro = verify_watertight(open_mesh)
        assert not ro.watertight
        assert ro.boundary_edges == 3

        # Inverted normals -> negative signed volume
        inv_mesh = SolidMesh(box.vertices, box.faces[:, [0, 2, 1]])
        ri = verify_watertight(inv_mesh)
        assert not ri.watertight
        assert ri.signed_volume_mm3 < 0.0

    def test_binary_stl_roundtrip(self, tmp_path: Path) -> None:
        flange = make_cf_flange("CF40")
        stl_p = write_binary_stl(flange, tmp_path / "cf40.stl")
        assert stl_p.stat().st_size == 84 + 50 * flange.n_faces
        loaded = read_binary_stl(stl_p)
        rl = verify_watertight(loaded)
        assert rl.watertight
        assert math.isclose(
            rl.signed_volume_mm3, verify_watertight(flange).signed_volume_mm3, rel_tol=1e-4
        )


# ===========================================================================
# 3. ISO 3669 ConFlat & ISO-K Flanges
# ===========================================================================
class TestCfAndIsoKFlanges:
    @pytest.mark.parametrize(
        "size,bolts,hole_d,pcd",
        [
            ("CF16", 6, 4.3, 27.0),
            ("CF40", 6, 6.6, 58.7),
            ("CF63", 8, 8.4, 92.1),
            ("CF100", 16, 8.4, 130.2),
            ("CF150", 20, 8.4, 181.0),
            ("CF200", 24, 8.4, 231.8),
            ("CF250", 32, 8.4, 284.2),
            ("CF400", 40, 8.4, 431.8),
        ],
    )
    def test_all_cf_sizes_specs_and_watertight(
        self, size: str, bolts: int, hole_d: float, pcd: float
    ) -> None:
        sp = CF_SPECS[size]
        assert sp.bolt_count == bolts
        assert math.isclose(sp.bolt_hole_mm, hole_d, abs_tol=1e-6)
        assert math.isclose(sp.pcd_mm, pcd, abs_tol=1e-6)

        flange = make_cf_flange(size)
        rf = verify_watertight(flange)
        assert rf.watertight, f"{size} flange not watertight: {rf}"
        assert rf.euler_characteristic == 2 - 2 * (bolts + 1)

        blank = make_cf_blank_flange(size)
        rb = verify_watertight(blank)
        assert rb.watertight, f"{size} blank not watertight: {rb}"
        assert rb.euler_characteristic == 2 - 2 * bolts

        wn = make_cf_weld_neck(size, neck_length=35.0)
        rw = verify_watertight(wn)
        assert rw.watertight, f"{size} weld-neck not watertight: {rw}"
        bmin, bmax = wn.bbox()
        assert math.isclose(bmax[2] - bmin[2], sp.thickness_mm + 35.0, abs_tol=1e-5)

    def test_cf_viewport_and_all_isok_flanges(self) -> None:
        # S5.5-02 CF63 sapphire viewport (Ø50x8 mm window, Ø44 mm clear aperture)
        vp = make_cf_viewport(
            "CF63", clear_aperture=44.0, window_diameter=50.0, window_thickness=8.0, axis="+y"
        )
        rvp = verify_watertight(vp)
        assert rvp.watertight
        assert rvp.n_shells == 2  # Flange housing + sapphire window

        port = make_cf_port_interface("CF63", "flash_vp", (0.0, 192.0, 500.0), (0.0, 1.0, 0.0), mating_part_id="S5.1-01")
        assert port.bolt_count == 8 and math.isclose(port.pcd_mm, 92.1)

        for sz in ("DN50", "DN100", "DN160", "DN250"):
            assert sz in ISO_K_SPECS
            fl = make_isok_flange(sz, neck_length=25.0)
            bl = make_isok_flange(sz, blank=True)
            assert verify_watertight(fl).watertight
            assert verify_watertight(bl).watertight


# ===========================================================================
# 4. ISO 10303-21 AP214 STEP Exporter & Validator
# ===========================================================================
class TestStepWriter:
    def test_step_exact_and_decimated_and_validator(self, tmp_path: Path) -> None:
        pd = make_part_design_from_bom("S5.5-02")
        # Exact mesh (<= 800 faces): CF40 flange (552 faces)
        cf40 = make_cf_flange("CF40")
        p1 = write_step(cf40, tmp_path / "cf40.step", part_design=pd, max_faces=800)
        v1 = validate_step_file(p1)
        assert v1.valid, f"STEP validation failed: {v1.errors}"
        assert v1.has_ap214_schema
        assert v1.closed_shell_count == 1
        assert v1.face_count == cf40.n_faces
        assert len(v1.dangling_refs) == 0

        # Large mesh (> 800 faces): 32x32 MEMS wafer (50,688 faces) -> compact proxy <= 800
        mems = make_mems_grid_plate(24.0, 24.0, 0.030, nx=32, ny=32, outer_diameter=28.0)
        p2 = write_step(mems, tmp_path / "mems.step", part_design=make_part_design_from_bom("S2.1-01"), max_faces=800)
        v2 = validate_step_file(p2)
        assert v2.valid, f"MEMS STEP failed: {v2.errors}"
        assert v2.face_count <= 800
        assert v2.closed_shell_count >= 1
        assert len(v2.dangling_refs) == 0

        # Multi-shell STEP export (CF63 sapphire viewport = 2 closed shells)
        vp = make_cf_viewport("CF63", clear_aperture=44.0, window_diameter=50.0, window_thickness=8.0)
        p_vp = write_step(vp, tmp_path / "vp.step", part_design=pd, max_faces=1200)
        v_vp = validate_step_file(p_vp)
        assert v_vp.valid, f"Viewport STEP failed: {v_vp.errors}"
        assert v_vp.closed_shell_count == 2
        assert v_vp.faceted_brep_count == 2

        # Manifold decimation path on a ~1200-face low-genus revolved solid (reduced <= 800)
        rev = make_revolved_profile(
            [(20.0, 0.0), (45.0, 0.0), (45.0, 15.0), (35.0, 20.0), (35.0, 60.0), (20.0, 60.0)],
            segments=96,
        )
        assert rev.n_faces > 800
        p_dec = write_step(rev, tmp_path / "rev_dec.step", part_design=pd, max_faces=800)
        v_dec = validate_step_file(p_dec)
        assert v_dec.valid, f"Decimated STEP failed: {v_dec.errors}"
        assert v_dec.face_count <= 800

        # Negative test: corrupt a reference -> validator MUST reject dangling #id!
        broken = tmp_path / "broken.step"
        txt = p1.read_text(encoding="ascii")
        txt = txt.replace("FACETED_BREP(", "FACETED_BREP(#999999,", 1)
        broken.write_text(txt, encoding="ascii")
        vb = validate_step_file(broken)
        assert not vb.valid
        assert 999999 in vb.dangling_refs


# ===========================================================================
# 5. ASCII AutoCAD DXF (AC1009 / R12) Writer & Validator
# ===========================================================================
class TestDxfWriter:
    def test_dxf_export_layers_and_validator(self, tmp_path: Path) -> None:
        pd = make_part_design_from_bom(
            "S5.5-02",
            ports=(make_cf_port_interface("CF63", "seal_face", (0.0, 0.0, 8.75), (0.0, 0.0, 1.0)),),
            dimensions=(DimensionCallout("OD", 113.5, 0.1, -0.1, prefix="Ø"),),
        )
        mesh = make_cf_flange("CF63")
        dxf_p = write_dxf(mesh, tmp_path / "S5.5-02.dxf", part_design=pd)
        vd = validate_dxf_file(dxf_p)
        assert vd.valid, f"DXF validation failed: {vd.errors}"
        assert vd.version == "AC1009"
        for layer in REQUIRED_DXF_LAYERS:
            assert layer in vd.layers_defined
        assert vd.entity_counts.get("LINE", 0) > 20
        assert vd.entity_counts.get("CIRCLE", 0) >= 1
        assert vd.entity_counts.get("TEXT", 0) >= 5

        # Negative test: truncate EOF -> validator MUST fail
        bad = tmp_path / "bad.dxf"
        bad.write_text("\n".join(dxf_p.read_text().splitlines()[:-2]) + "\n", encoding="ascii")
        assert not validate_dxf_file(bad).valid


# ===========================================================================
# 6. ISO 128 / ASME Y14.5 White-Paper Academic SVG GD&T Writer & Validator
# ===========================================================================
class TestSvgGdtWriter:
    def test_svg_academic_palette_gdt_and_xml(self, tmp_path: Path) -> None:
        pd = make_part_design_from_bom(
            "S1.5-01",
            ports=(make_cf_port_interface("CF100", "mount_cf100", (0.0, 0.0, 0.0), (0.0, 0.0, 1.0)),),
            dimensions=(
                DimensionCallout("R0", 40.0, 0.005, -0.005, prefix="R"),
                DimensionCallout("OD", 110.0, 0.05, -0.05, prefix="Ø"),
            ),
            gdt_frames=(
                GDTFrame("profile_surface", 0.005, datum_primary="A", datum_secondary="B", feature_note="HEMISPHERE R0=40"),
                GDTFrame("concentricity", 0.005, diameter_zone=True, datum_primary="B", feature_note="INNER/OUTER SHELL"),
                GDTFrame("perpendicularity", 0.010, diameter_zone=True, datum_primary="A"),
                GDTFrame("flatness", 0.005, datum_primary=""),
            ),
            surface_finish_ra_um=0.2,
        )
        mesh = make_hemisphere_shell(36.0, 44.0)
        svg_p = write_svg_gdt(mesh, tmp_path / "S1.5-01.svg", part_design=pd)
        vs = validate_svg_file(svg_p)
        assert vs.valid, f"SVG validation failed: {vs.errors}"
        assert vs.well_formed_xml
        assert vs.white_canvas
        assert vs.academic_palette_only
        assert len(vs.disallowed_colors) == 0
        assert vs.has_all_four_views
        assert vs.has_gdt_glyphs
        assert vs.has_epistemic_stamp

        txt = svg_p.read_text(encoding="utf-8")
        for sym in ("⊥", "◎", "⌓", "⏥", "Ra 0.2 µm", COLOR_CANVAS):
            assert sym in txt

        # Negative test: inject a flashy neon cyan color -> validator MUST reject!
        flashy = tmp_path / "flashy.svg"
        flashy.write_text(txt.replace("#1B365D", "#00FFFF", 1), encoding="utf-8")
        vf = validate_svg_file(flashy)
        assert not vf.valid
        assert "#00FFFF" in vf.disallowed_colors

    def test_svg_layout_no_overflow_no_overlap_and_clean_truncation(self, tmp_path: Path) -> None:
        from hardware.cad_parts.core.svg_gdt_writer import _truncate_clean

        # 1) Exhaustive 180-row BOM clean truncation: 0 length overflow, 0 unmatched parens
        bom = load_bom_table()
        for pid, row in bom.items():
            for val, lim in (
                (row.part_name, 66),
                (row.material, 25),
                (row.temp_stage, 22),
                (row.vacuum_grade, 22),
                (row.tolerance, 26),
            ):
                out = _truncate_clean(val, lim)
                assert len(out) <= lim, f"{pid}: {out!r} exceeds {lim}"
                assert out.count("(") == out.count(")"), f"{pid}: unmatched '(' in {out!r}"
                assert out.count("[") == out.count("]"), f"{pid}: unmatched '[' in {out!r}"

        assert _truncate_clean("300 K (150 C bakeout)", 20) == "300 K (150 C…)"
        assert _truncate_clean("300 K (150 C bakeout)", 22) == "300 K (150 C bakeout)"
        assert _truncate_clean("MAIN CYLINDER INNER BORE", 22) == "MAIN CYLINDER INNER…"
        assert "=" not in _truncate_clean(
            "SOI MEMS apertur plakasi (Arch-B es-adimli 0.50 mm, 32x32=1024 demetcik)", 58
        )

        # 2) Stress-test SVG with long S5.1-01 datums, 5 GD&T frames, long BOM strings & bakeout temp
        pd = make_part_design_from_bom(
            "S5.1-01",
            datums=(
                ("A", "BOTTOM CF400 MOUNTING FACE (Z=260.0 MM, FLATNESS 0.05)"),
                ("B", "MAIN CYLINDER INNER BORE AXIS (Ø364.0 MM, ELECTRO-POLISHED)"),
                ("C", "+X LOAD-LOCK CF100 PORT AXIS (AZ=0 DEG, INDEX KEYWAY)"),
            ),
            ports=(
                make_cf_port_interface("CF400", "bottom_cf400_base", (0.0, 0.0, -200.0), (0.0, 0.0, -1.0), mating_part_id="S4.2-01"),
                make_cf_port_interface("CF250", "top_cf250_column", (0.0, 0.0, 200.0), (0.0, 0.0, 1.0), mating_part_id="S5.1-02"),
            ),
            gdt_frames=(
                GDTFrame("flatness", 0.050, datum_primary="", feature_note="CF400/CF250 KNIFE-EDGE SEALING FACES (ALL PORTS)"),
                GDTFrame("perpendicularity", 0.100, diameter_zone=True, datum_primary="A", feature_note="VESSEL AXIS B TO BOTTOM CF400 DATUM A"),
                GDTFrame("concentricity", 0.100, diameter_zone=True, datum_primary="B", feature_note="TOP CF250 COLUMN PORT TO CHAMBER AXIS"),
                GDTFrame("position", 0.150, diameter_zone=True, datum_primary="A", datum_secondary="B", datum_tertiary="C", feature_note="13X RADIAL CF PORT AXES"),
                GDTFrame("profile_surface", 0.200, datum_primary="A", datum_secondary="B", feature_note="GENERAL MACHINED UHV CHAMBER WALL"),
            ),
            surface_finish_ra_um=0.2,
        )
        mesh = make_cf_flange("CF250")
        svg_p = write_svg_gdt(mesh, tmp_path / "S5.1-01_stress.svg", part_design=pd)
        vs = validate_svg_file(svg_p, check_layout=True)
        assert vs.valid, f"SVG layout check failed: {vs.errors}"

        # 3) Negative layout tests: overflowing DATUMS line & unmatched paren MUST fail check_layout=True
        raw = svg_p.read_text(encoding="utf-8")
        overflow_p = tmp_path / "overflow.svg"
        overflow_p.write_text(
            raw.replace(
                "DATUMS:",
                "DATUMS: " + "X" * 120,
                1,
            ),
            encoding="utf-8",
        )
        assert not validate_svg_file(overflow_p, check_layout=True).valid

        unbal_p = tmp_path / "unbal.svg"
        unbal_p.write_text(
            raw.replace("300 K (150 C bakeout)", "300 K (150 C bakeout", 1),
            encoding="utf-8",
        )
        assert not validate_svg_file(unbal_p, check_layout=True).valid


# ===========================================================================
# 7. Parametric OpenSCAD Writer & Validator
# ===========================================================================
class TestScadWriter:
    def test_scad_parametric_module_and_validator(self, tmp_path: Path) -> None:
        pd = make_part_design_from_bom(
            "S7.SAFETY-02",
            world_origin_mm=(0.0, 240.0, 500.0),
            world_rotation_deg=(0.0, 0.0, 90.0),
            scad_params=(("wall_mm", 3.0), ("shroud_w", 280.0), ("aperture_d", 44.0)),
            ports=(make_cf_port_interface("CF63", "viewport_mate", (0.0, 0.0, 0.0), (0.0, 1.0, 0.0)),),
        )
        mesh = make_box(280.0, 260.0, 220.0)
        feats = [
            ScadFeature("add_box", {"dx": 280.0, "dy": 260.0, "dz": 220.0}, comment="3 mm steel OD8 shroud"),
            ScadFeature("add_cf_flange", {"size": "CF63"}, translate=(0.0, -130.0, 0.0), rotate=(90.0, 0.0, 0.0)),
            ScadFeature("cut_slot", {"length": 60.0, "width": 12.0, "h": 25.0}, translate=(0.0, 0.0, 110.0)),
        ]
        scad_p = write_scad(mesh, tmp_path / "S7.SAFETY-02.scad", part_design=pd, features=feats)
        vsc = validate_scad_file(scad_p)
        assert vsc.valid, f"SCAD validation failed: {vsc.errors}"
        assert vsc.module_name == "part_S7_SAFETY_02"
        txt = scad_p.read_text(encoding="utf-8")
        assert "difference()" in txt
        assert "translate([0.000, 240.000, 500.000])" in txt

        # Negative test: unbalanced brace -> validator MUST reject!
        bad = tmp_path / "bad.scad"
        bad.write_text(txt + "\n{\n", encoding="utf-8")
        assert not validate_scad_file(bad).valid


# ===========================================================================
# 8. NIST Cryogenic Thermal Contraction & GD&T Tolerance Stackup
# ===========================================================================
class TestThermalAndToleranceGdt:
    def test_nist_contraction_signs_and_magnitudes(self) -> None:
        # All 12 core cryogenic materials present
        core_mats = [
            "316LN", "OFHC Cu", "Ti-6Al-4V", "Al 6061", "Invar-36",
            "Al2O3", "AlN", "Si", "Zerodur", "Nb", "Vespel SP-22", "PEEK",
        ]
        for m in core_mats:
            assert m in NIST_THERMAL_CONTRACTION_TABLE
            assert math.isclose(integrated_thermal_contraction(m, 293.15, 293.15), 0.0, abs_tol=1e-12)

        # Verify published NIST 293K -> 4K magnitudes & physical ordering:
        # |PEEK| > |Vespel| > |Al 6061| > |OFHC Cu| > |316LN| > |Ti-6Al-4V| > |Nb| > |Al2O3| > |AlN| > |Invar-36| > |Si| > |Zerodur|
        e_peek = integrated_thermal_contraction("PEEK", 4.0)
        e_vesp = integrated_thermal_contraction("Vespel SP-22", 4.0)
        e_al = integrated_thermal_contraction("Al 6061", 4.0)
        e_cu = integrated_thermal_contraction("OFHC Cu", 4.0)
        e_ss = integrated_thermal_contraction("316LN", 4.0)
        e_ti = integrated_thermal_contraction("Ti-6Al-4V", 4.0)
        e_nb = integrated_thermal_contraction("Nb", 4.0)
        e_al2o3 = integrated_thermal_contraction("Al2O3", 4.0)
        e_aln = integrated_thermal_contraction("AlN", 4.0)
        e_inv = integrated_thermal_contraction("Invar-36", 4.0)
        e_si = integrated_thermal_contraction("Si", 4.0)
        e_zero = integrated_thermal_contraction("Zerodur", 4.0)

        assert e_peek < e_vesp < e_al < e_cu < e_ss < e_ti < e_nb < e_al2o3 < e_aln < e_inv < e_si < 0.0
        assert abs(e_zero) < 1e-4  # Ultra-low-expansion Zerodur
        assert math.isclose(e_ss, -2.97e-3, rel_tol=0.02)
        assert math.isclose(e_cu, -3.26e-3, rel_tol=0.02)
        assert math.isclose(e_al, -4.15e-3, rel_tol=0.02)

        # Cryogenic saturation: 20 mK equals 4 K within 1e-6
        assert abs(integrated_thermal_contraction("OFHC Cu", 0.02) - e_cu) < 1e-6
        # Bakeout heating (423.15 K) gives positive expansion
        assert integrated_thermal_contraction("316LN", 423.15) > 0.0015
        # Monotonic cooling from 300K -> 100K -> 50K -> 4K for metals
        assert (
            integrated_thermal_contraction("316LN", 300.0)
            > integrated_thermal_contraction("316LN", 100.0)
            > integrated_thermal_contraction("316LN", 50.0)
            >= integrated_thermal_contraction("316LN", 4.0)
        )

    def test_cold_clearance_pass_and_crush_detection(self) -> None:
        # Case 1: Outer Al 6061 (ID=100.2 mm) shrinks much more than inner Al2O3 (OD=100.0 mm) at 4 K!
        # Warm radial clearance = 0.10 mm, differential shrinkage ~ (4.15 - 0.72)e-3 * 50 = 0.1715 mm -> CRUSH!
        crush = check_cold_clearance(
            "Al 6061", "Al2O3", nominal_outer_id_mm=100.2, nominal_inner_od_mm=100.0, t_cold_k=4.0
        )
        assert crush.interference_risk is True
        assert crush.passed is False
        assert crush.cold_nominal_radial_clearance_mm < 0.0

        # Case 2: Outer Nb (ID=64.0 mm) & Cryoperm-10 (OD=78.0 mm inside ID=82.0 mm) -> generous clearance
        ok = check_cold_clearance(
            "316LN",
            "Nb",
            nominal_outer_id_mm=80.0,
            nominal_inner_od_mm=69.0,
            t_cold_k=0.02,
            min_required_radial_clearance_mm=1.0,
            outer_id_tol_mm=0.1,
            inner_od_tol_mm=0.1,
        )
        assert ok.interference_risk is False
        assert ok.passed is True
        assert cold_dimension_mm(100.0, "316LN", 4.0) < 99.75

    def test_tolerance_stack_wc_and_rss(self) -> None:
        # 3-part stackup: nominal = 10.0 + 20.0 - 29.75 = 0.250 mm (working distance!)
        contribs = [
            ToleranceContributor("lens_housing", 10.0, 0.003, -0.003, sign=+1.0),
            ToleranceContributor("spacer_ring", 20.0, 0.004, -0.004, sign=+1.0),
            ToleranceContributor("wafer_datum", 29.75, 0.000, 0.000, sign=-1.0),
        ]
        res = check_tolerance_stack(contribs, target_min_mm=0.244, target_max_mm=0.256)
        assert math.isclose(res.nominal_mm, 0.250, abs_tol=1e-9)
        assert math.isclose(res.wc_half_band_mm, 0.007, abs_tol=1e-9)
        assert math.isclose(res.rss_half_band_mm, 0.005, abs_tol=1e-9)
        assert res.rss_pass is True
        assert res.wc_pass is False  # 0.250 ± 0.007 exceeds [0.244, 0.256]
        shares = dict(res.variance_shares_pct)
        assert math.isclose(shares["lens_housing"], 36.0, abs_tol=1e-6)
        assert math.isclose(shares["spacer_ring"], 64.0, abs_tol=1e-6)


# ===========================================================================
# 9. End-to-End 5-Artifact Export Pipeline
# ===========================================================================
class TestEndToEndPipeline:
    def test_export_part_artifacts_all_five_formats(self, tmp_path: Path) -> None:
        pd = make_part_design_from_bom(
            "S6.9-02",
            ports=(
                make_cf_port_interface("CF63", "ovc_left", (0.0, 0.0, -60.0), (0.0, 0.0, -1.0), mating_part_id="S6.8-04"),
                make_cf_port_interface("CF63", "ovc_right", (0.0, 0.0, 60.0), (0.0, 0.0, 1.0), mating_part_id="S5.1-01"),
            ),
            dimensions=(
                DimensionCallout("ID", 44.0, 0.1, -0.1, prefix="Ø"),
                DimensionCallout("OD", 68.0, 0.1, -0.1, prefix="Ø"),
                DimensionCallout("L_ACT", 120.0, 0.5, -0.5),
            ),
            scad_params=(("bellows_id", 44.0), ("bellows_od", 68.0), ("n_conv", 28)),
        )
        bellows = make_bellows(22.0, 34.0, 120.0, n_convolutions=28, wall_thickness=0.15, segments=32)
        fl_bot = make_cf_flange("CF63", bore_id=44.0, center=(0.0, 0.0, -68.75), axis="-z")
        fl_top = make_cf_flange("CF63", bore_id=44.0, center=(0.0, 0.0, 68.75), axis="+z")
        asm = merge_solids([bellows, fl_bot, fl_top], name="S6.9-02", material="316L")

        res = export_part_artifacts(pd, asm, tmp_path / "S6", flat=True)
        assert res.all_valid, f"End-to-end export failed: {res.warnings}"
        assert res.watertight is True
        assert res.boundary_edges == 0
        assert res.non_manifold_edges == 0
        assert res.mass_kg > 0.5
        assert res.design_maturity == DESIGN_MATURITY
        assert res.no_lab_measurement is True
        assert res.iec61508_certified is False
        assert res.semi_s2_certified is False
        for rel_p in (res.stl_path, res.step_path, res.scad_path, res.dxf_path, res.svg_path):
            assert Path(rel_p).is_file()

    def test_export_32x32_mems_plate_subdir_layout(self, tmp_path: Path) -> None:
        pd = make_part_design_from_bom(
            "S2.1-01",
            material="Si",
            dimensions=(
                DimensionCallout("PITCH", 0.50, 0.00005, -0.00005, prefix="32x32 "),
                DimensionCallout("OD", 28.0, 0.02, -0.02, prefix="Ø"),
            ),
            scad_params=(("grid_n", 32), ("pitch_mm", 0.50), ("aperture_d", 0.30)),
        )
        mems = make_mems_grid_plate(
            24.0, 24.0, 0.030, nx=32, ny=32, pitch_x=0.50, pitch_y=0.50,
            hole_diameter=0.30, outer_diameter=28.0, material="Si",
        )
        scad_feats = [
            ScadFeature("add_cylinder", {"d": 28.0, "h": 0.030}, comment="30 um SOI wafer"),
            ScadFeature(
                "cut_grid_holes",
                {"nx": 32, "ny": 32, "pitch_x": 0.50, "pitch_y": 0.50, "hole_d": 0.30, "h": 0.10},
                comment="32x32 = 1024 Arch-B beamlet apertures",
            ),
        ]
        res = export_part_artifacts(pd, mems, tmp_path / "S2", scad_features=scad_feats, flat=False)
        assert res.all_valid, f"MEMS export failed: {res.warnings}"
        assert res.triangle_count == mems.n_faces
        assert validate_step_file(res.step_path).face_count <= 800
        assert "for (ix = [0 : 32 - 1])" in Path(res.scad_path).read_text(encoding="utf-8")
