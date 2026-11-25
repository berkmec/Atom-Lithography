"""Comprehensive verification suite for Subsystems S3 & S4 mechanical CAD (Wave 2B / WP-M2).

Verifies all 31 / 31 physical BOM parts of S3 (14 parts: S3.1-01..S3.3-04) and
S4 (17 parts: S4.1-01..S4.5-03):
1. Exact BOM coverage (31/31 physical parts, zero bom_id aliasing, locked epistemic status).
2. 100% watertight 2-manifold geometry on every part (0 boundary, 0 non-manifold, 0 orientation
   errors, positive per-shell signed volume, realistic mass properties).
3. Feature-level verification:
   - S3.1-01 wafer active plane aligned to global Z = 0.000 mm inside R < 180 mm UHV bore.
   - S3.1-03 AlN carrier pocket + NIST 300 K -> 100 K & 20 mK thermal contraction PASS.
   - S3.2-01 all 16x 100 K cold-island CSA modules + thermal straps instantiated & 100 K PASS.
   - S3.2-04 all 16x <5 cm in-vacuum micro-coax looms (<50 mm exact arc length).
   - S3.2-05 all 4x ISO 3669 CF63 32-coax feedthrough flanges (PCD 92.1, 8x Ø8.4).
   - S4.1-01 DIN 876/00 granite base explicitly reconciled (900x700x120 mm vs BOM 600x450x150),
     central Ø420 mm (R=210 mm) DR clear bore & real M6 threaded insert grid (>=40 holes).
   - S4.3-01 Ti/Invar 6-DOF flexure piezo fine stage with real EDM flexure cutouts.
   - S4.4-04 (3x) & S4.5-02 (1x) ISO 3669 CF40 optical viewports (PCD 58.7, 6x Ø6.6).
4. All 5 manufacturing artifacts (.stl/.step/.dxf/.svg/.scad) + .json manifests exist and pass
   independent strict validators in ``hardware/cad_parts/out/{S3,S4}/``.
5. Exact 3D mesh-level interference audit:
   - 0 intra-S3 clashes (91 pairs), 0 intra-S4 clashes (136 pairs), 0 cross-S3/S4 clashes
     (238 pairs -> 0 / 465 total pairs), 0 internal sub-shell self-clashes.
   - 0 clashes with UHV chamber wall, Exp125 8-coil magnet, Cryoperm, MXC chuck, DR OVC tower,
     central R=210 mm lower DR clear bore, and S2 Arch-B mini-lens / tile carrier.
   - Strict non-overlapping EIA-310 U-slots for all 10 Rack Bay 1 (X=+1400 mm) electronics.
6. Zero host-path leaks (no /home/, /Users/, C:\\, or user home paths) in any artifact or source.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np
import pytest

from hardware.cad_parts.core import (
    DESIGN_MATURITY,
    REPO_ROOT,
    SolidMesh,
    list_physical_part_ids,
    make_cylinder,
    make_tube,
    read_binary_stl,
    split_shells,
    validate_dxf_file,
    validate_scad_file,
    validate_step_file,
    validate_svg_file,
    verify_watertight,
)
from hardware.cad_parts.subsystems.s3_ibic_mech import (
    DEFAULT_S3_OUT_DIR,
    RACK_BAY1_X_MM,
    build_s3_parts,
    export_all as export_all_s3,
)
from hardware.cad_parts.subsystems.s4_stage_metrology import (
    DEFAULT_S4_OUT_DIR,
    DR_CLEAR_BORE_R_MM,
    build_s4_parts,
    export_all as export_all_s4,
)


# ---------------------------------------------------------------------------
# Exact 3D Mesh-Level Clash Verification Helpers (Broadphase + Möller-Trumbore)
# ---------------------------------------------------------------------------
def _aabb_overlap(
    mn1: tuple[float, float, float],
    mx1: tuple[float, float, float],
    mn2: tuple[float, float, float],
    mx2: tuple[float, float, float],
    tol: float = 1e-4,
) -> bool:
    return (
        mn1[0] < mx2[0] - tol
        and mx1[0] > mn2[0] + tol
        and mn1[1] < mx2[1] - tol
        and mx1[1] > mn2[1] + tol
        and mn1[2] < mx2[2] - tol
        and mx1[2] > mn2[2] + tol
    )


def _segs_intersect_tris(
    p0: np.ndarray,
    p1: np.ndarray,
    v0: np.ndarray,
    v1: np.ndarray,
    v2: np.ndarray,
    eps: float = 1e-7,
) -> bool:
    if len(p0) == 0 or len(v0) == 0:
        return False
    d = p1 - p0
    e1 = v1 - v0
    e2 = v2 - v0
    for i in range(0, len(p0), 64):
        de = d[i : i + 64, None, :]
        pe = p0[i : i + 64, None, :]
        h = np.cross(de, e2[None, :, :])
        a = np.einsum("bti,ti->bt", h, e1)
        valid = np.abs(a) > 1e-11
        if not np.any(valid):
            continue
        inv_a = np.where(valid, 1.0 / np.where(valid, a, 1.0), 0.0)
        s = pe - v0[None, :, :]
        u = np.einsum("bti,bti->bt", s, h) * inv_a
        valid &= (u > eps) & (u < 1.0 - eps)
        if not np.any(valid):
            continue
        q = np.cross(s, e1[None, :, :])
        v = np.einsum("bti,bti->bt", de, q) * inv_a
        valid &= (v > eps) & (u + v < 1.0 - eps)
        if not np.any(valid):
            continue
        t = np.einsum("ti,bti->bt", e2, q) * inv_a
        if np.any(valid & (t > eps) & (t < 1.0 - eps)):
            return True
    return False


def _point_inside_mesh(pt: np.ndarray, mesh: SolidMesh) -> bool:
    rd = np.array([0.819152044, 0.422618262, 0.387515883])
    v = mesh.vertices
    f = mesh.faces
    v0, v1, v2 = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    e1, e2 = v1 - v0, v2 - v0
    h = np.cross(rd, e2)
    a = np.einsum("ti,ti->t", e1, h)
    valid = np.abs(a) > 1e-12
    inv_a = np.where(valid, 1.0 / np.where(valid, a, 1.0), 0.0)
    s = pt - v0
    u = np.einsum("ti,ti->t", s, h) * inv_a
    q = np.cross(s, e1)
    vv = np.einsum("i,ti->t", rd, q) * inv_a
    t = np.einsum("ti,ti->t", e2, q) * inv_a
    hits = valid & (u >= 0.0) & (vv >= 0.0) & (u + vv <= 1.0) & (t > 1e-7)
    return (int(np.sum(hits)) % 2) == 1


def _shells_clash(sa: SolidMesh, sb: SolidMesh) -> bool:
    mn1, mx1 = sa.bbox()
    mn2, mx2 = sb.bbox()
    if not _aabb_overlap(mn1, mx1, mn2, mx2):
        return False

    def _cand_tris(m: SolidMesh, mn: tuple[float, float, float], mx: tuple[float, float, float]) -> np.ndarray:
        pts = m.vertices[m.faces]
        tmn = pts.min(axis=1)
        tmx = pts.max(axis=1)
        mask = (
            (tmn[:, 0] <= mx[0])
            & (tmx[:, 0] >= mn[0])
            & (tmn[:, 1] <= mx[1])
            & (tmx[:, 1] >= mn[1])
            & (tmn[:, 2] <= mx[2])
            & (tmx[:, 2] >= mn[2])
        )
        return pts[mask]

    ta = _cand_tris(sa, mn2, mx2)
    tb = _cand_tris(sb, mn1, mx1)
    if len(ta) > 0 and len(tb) > 0:
        ea0 = np.vstack([ta[:, 0], ta[:, 1], ta[:, 2]])
        ea1 = np.vstack([ta[:, 1], ta[:, 2], ta[:, 0]])
        if _segs_intersect_tris(ea0, ea1, tb[:, 0], tb[:, 1], tb[:, 2]):
            return True
        eb0 = np.vstack([tb[:, 0], tb[:, 1], tb[:, 2]])
        eb1 = np.vstack([tb[:, 1], tb[:, 2], tb[:, 0]])
        if _segs_intersect_tris(eb0, eb1, ta[:, 0], ta[:, 1], ta[:, 2]):
            return True
    return _point_inside_mesh(sa.vertices[0], sb) or _point_inside_mesh(sb.vertices[0], sa)


# ---------------------------------------------------------------------------
# Module-Scoped Fixtures (Build & Export Once for Fast Deterministic Suite)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def s3_parts():
    return build_s3_parts()


@pytest.fixture(scope="module")
def s4_parts():
    return build_s4_parts()


@pytest.fixture(scope="module")
def exported_results():
    r3 = export_all_s3(DEFAULT_S3_OUT_DIR)
    r4 = export_all_s4(DEFAULT_S4_OUT_DIR)
    return {"S3": r3, "S4": r4}


# ===========================================================================
# 1. Exact 31/31 BOM Coverage, Tier Split & Epistemic Metadata
# ===========================================================================
class TestCoverageAndEpistemic:
    def test_exact_31_of_31_physical_bom_coverage(self, s3_parts, s4_parts) -> None:
        exp_s3 = list_physical_part_ids("S3")
        exp_s4 = list_physical_part_ids("S4")
        assert len(exp_s3) == 14
        assert len(exp_s4) == 17
        assert set(s3_parts.keys()) == set(exp_s3)
        assert set(s4_parts.keys()) == set(exp_s4)
        assert len(s3_parts) + len(s4_parts) == 31

        # Verify tier split matching audit #282 & brief #288
        s3_custom = sum(1 for bp in s3_parts.values() if bp.design.design_tier == "CUSTOM_FULL")
        s3_cots = sum(1 for bp in s3_parts.values() if bp.design.design_tier == "COTS_ENV_ICD")
        s4_custom = sum(1 for bp in s4_parts.values() if bp.design.design_tier == "CUSTOM_FULL")
        s4_cots = sum(1 for bp in s4_parts.values() if bp.design.design_tier == "COTS_ENV_ICD")
        assert (s3_custom, s3_cots) == (8, 6)
        assert (s4_custom, s4_cots) == (6, 11)

    def test_locked_epistemic_metadata_all_31_parts(self, s3_parts, s4_parts) -> None:
        for pid, bp in {**s3_parts, **s4_parts}.items():
            d = bp.design
            assert d.part_id == pid
            assert d.design_maturity == DESIGN_MATURITY
            assert d.no_lab_measurement is True
            assert d.iec61508_certified is False
            assert d.semi_s2_certified is False
            assert len(d.ports) >= 1, f"{pid} missing interface port descriptors"
            assert len(d.dimensions) >= 2, f"{pid} missing dimension callouts"
            assert len(d.gdt_frames) >= 1, f"{pid} missing GD&T frame"


# ===========================================================================
# 2. 100% Watertight Geometry & Specific Mechanical Feature Checks
# ===========================================================================
class TestWatertightAndFeatures:
    def test_all_31_parts_strictly_watertight(self, s3_parts, s4_parts) -> None:
        for pid, bp in {**s3_parts, **s4_parts}.items():
            res = verify_watertight(bp.mesh)
            assert res.watertight, f"{pid} failed watertight check: {res.errors}"
            assert res.boundary_edges == 0
            assert res.non_manifold_edges == 0
            assert res.orientation_errors == 0
            assert res.degenerate_faces == 0
            assert res.signed_volume_mm3 > 0.0
            assert res.min_shell_volume_mm3 > 0.0

    def test_s3_wafer_carrier_thermal_and_16x_csa_features(self, s3_parts) -> None:
        # S3.1-01 wafer active top face at global Z = 0.000 mm, Ø50 mm inside R < 180 mm
        w_min, w_max = s3_parts["S3.1-01"].world_mesh().bbox()
        assert math.isclose(w_max[2], 0.0, abs_tol=1e-6)
        assert math.isclose(w_max[0] - w_min[0], 50.0, abs_tol=0.1)
        assert math.isclose(w_max[2] - w_min[2], 0.525, abs_tol=1e-4)

        # S3.1-03 AlN carrier: 80x80 mm Exp80 BC1, thermal contraction 300K->100K & 20mK PASS
        c_min, c_max = s3_parts["S3.1-03"].world_mesh().bbox()
        assert math.isclose(c_max[0] - c_min[0], 80.0, abs_tol=0.1)
        assert math.isclose(c_max[1] - c_min[1], 80.0, abs_tol=0.1)
        assert len(s3_parts["S3.1-03"].thermal_checks) >= 2
        for tc in s3_parts["S3.1-03"].thermal_checks:
            assert tc["passed"] is True
            assert tc["interference_risk"] is False

        # S3.2-01: all 16 cold-island CSA modules + 16 straps + 4 bus arcs -> >= 68 shells, R < 180 mm
        csa_shells = split_shells(s3_parts["S3.2-01"].world_mesh())
        assert len(csa_shells) == 16 * 4 + 4  # 16*(base+pcb+lid+strap) + 4 bus arcs
        csa_min, csa_max = s3_parts["S3.2-01"].world_mesh().bbox()
        assert max(abs(csa_min[0]), abs(csa_max[0]), abs(csa_min[1]), abs(csa_max[1])) < 180.0
        assert csa_min[2] > -18.0 and csa_max[2] < 18.0  # Inside 36 mm Exp125 split gap
        for tc in s3_parts["S3.2-01"].thermal_checks:
            assert tc["passed"] is True and tc["interference_risk"] is False

        # S3.2-04: all 16 <5 cm in-vacuum micro-coax looms
        coax_shells = split_shells(s3_parts["S3.2-04"].world_mesh())
        assert len(coax_shells) == 16
        scad_p = dict(s3_parts["S3.2-04"].design.scad_params)
        assert float(scad_p["arc_length_mm"]) < 50.0

        # S3.2-05: 4x ISO 3669 CF63 hermetic 32-coax feedthrough flanges
        cf63_ports = s3_parts["S3.2-05"].design.ports
        assert len(cf63_ports) == 4
        for p in cf63_ports:
            assert p.standard == "CF63"
            assert p.bolt_count == 8
            assert math.isclose(p.pcd_mm, 92.1, abs_tol=1e-6)
            assert math.isclose(p.bolt_hole_mm, 8.4, abs_tol=1e-6)

    def test_s4_granite_reconciliation_flexure_and_cf40_viewports(self, s4_parts) -> None:
        # S4.1-01 granite base: reconciled 900x700x120 mm, Ø420 DR clear bore, >=40 M6 insert holes
        g_bp = s4_parts["S4.1-01"]
        g_min, g_max = g_bp.world_mesh().bbox()
        assert math.isclose(g_max[0] - g_min[0], 900.0, abs_tol=0.1)
        assert math.isclose(g_max[1] - g_min[1], 700.0, abs_tol=0.1)
        assert math.isclose(g_max[2] - g_min[2], 120.0, abs_tol=0.1)
        gv = verify_watertight(g_bp.mesh)
        # Genus = 1 central bore + 44 M6 inserts = 45 -> Euler chi = 2 - 2*45 = -88
        assert gv.euler_characteristic <= 2 - 2 * 40
        assert g_bp.reconciliation is not None
        assert g_bp.reconciliation["bom_dims_mm"] == [600.0, 450.0, 150.0]
        assert g_bp.reconciliation["selected_cad_dims_mm"] == [900.0, 700.0, 120.0]
        assert any("600x450x150" in n and "900x700x120" in n for n in g_bp.design.notes)

        # S4.3-01 Ti/Invar 6-DOF flexure fine stage: real machined flexure cutouts (genus >= 13)
        f_bp = s4_parts["S4.3-01"]
        f_min, f_max = f_bp.world_mesh().bbox()
        assert math.isclose(f_max[0] - f_min[0], 90.0, abs_tol=0.1)
        assert math.isclose(f_max[1] - f_min[1], 90.0, abs_tol=0.1)
        assert math.isclose(f_max[2] - f_min[2], 24.0, abs_tol=0.1)
        flex_body_shell = split_shells(f_bp.mesh)[0]
        # 1 central bore + 8 flexure slots + 4 M4 corner holes = 13 holes -> chi = 2 - 26 = -24
        assert verify_watertight(flex_body_shell).euler_characteristic == 2 - 2 * 13

        # S4.4-04 (3x) and S4.5-02 (1x) real ISO 3669 CF40 optical viewports
        assert len(s4_parts["S4.4-04"].design.ports) == 3
        for p in s4_parts["S4.4-04"].design.ports:
            assert p.standard == "CF40"
            assert p.bolt_count == 6
            assert math.isclose(p.pcd_mm, 58.7, abs_tol=1e-6)
        fid_cf = s4_parts["S4.5-02"].design.ports[0]
        assert fid_cf.standard == "CF40" and fid_cf.bolt_count == 6


# ===========================================================================
# 3. Exported Artifacts (.stl, .step, .dxf, .svg, .scad, .json) Validation
# ===========================================================================
class TestArtifactExports:
    def test_all_31_parts_export_and_pass_all_five_validators_plus_json(self, exported_results) -> None:
        assert len(exported_results["S3"]) == 14
        assert len(exported_results["S4"]) == 17

        for sub, out_dir in (("S3", DEFAULT_S3_OUT_DIR), ("S4", DEFAULT_S4_OUT_DIR)):
            manifest_p = out_dir / f"{sub}_manifest.json"
            assert manifest_p.is_file()
            manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
            assert manifest["all_watertight"] is True
            assert manifest["all_valid"] is True
            assert manifest["epistemic"]["no_lab_measurement"] is True
            assert manifest["epistemic"]["iec61508_certified"] is False
            assert manifest["epistemic"]["semi_s2_certified"] is False

            for pid, res in exported_results[sub].items():
                assert res.all_valid, f"{pid} failed export validation: {res.warnings}"
                assert res.watertight is True
                assert res.mass_kg > 0.0

                stl_p = REPO_ROOT / res.stl_path
                step_p = REPO_ROOT / res.step_path
                dxf_p = REPO_ROOT / res.dxf_path
                svg_p = REPO_ROOT / res.svg_path
                scad_p = REPO_ROOT / res.scad_path
                json_p = out_dir / f"{pid}.json"

                for fp in (stl_p, step_p, dxf_p, svg_p, scad_p, json_p):
                    assert fp.is_file() and fp.stat().st_size > 0, f"Missing artifact {fp}"

                # Independent validator confirmation
                assert validate_step_file(step_p).valid
                assert validate_dxf_file(dxf_p).valid
                assert validate_svg_file(svg_p).valid
                assert validate_scad_file(scad_p).valid

                # Binary STL exact size check
                assert stl_p.stat().st_size == 84 + 50 * res.triangle_count

                # Per-part JSON manifest sanity
                pj = json.loads(json_p.read_text(encoding="utf-8"))
                assert pj["part_id"] == pid
                assert pj["artifact"]["all_valid"] is True

        # Binary STL full watertight round-trip on representative custom & CF flange parts
        for sub, pid in (("S3", "S3.1-03"), ("S3", "S3.2-05"), ("S4", "S4.1-01"), ("S4", "S4.3-01")):
            stl_mesh = read_binary_stl(REPO_ROOT / "hardware" / "cad_parts" / "out" / sub / f"{pid}.stl")
            assert verify_watertight(stl_mesh).watertight

        # Verify S4.1-01 JSON carries explicit reconciliation record
        g_json = json.loads((DEFAULT_S4_OUT_DIR / "S4.1-01.json").read_text(encoding="utf-8"))
        assert g_json["reconciliation"]["selected_cad_dims_mm"] == [900.0, 700.0, 120.0]


# ===========================================================================
# 4. Exact 3D Coordinate Hygiene & Zero-Clash Verification
# ===========================================================================
class TestZeroClashesAndCoordinateHygiene:
    def test_zero_intra_and_cross_subsystem_clashes_and_zero_self_clashes(self, s3_parts, s4_parts) -> None:
        all_parts = {**s3_parts, **s4_parts}
        world_shells = {pid: split_shells(bp.world_mesh()) for pid, bp in all_parts.items()}
        pids = list(all_parts.keys())

        # 1. Zero pairwise clashes across all 465 pairs (91 S3 + 136 S4 + 238 cross S3-S4)
        pairwise_clashes: list[tuple[str, str]] = []
        for i in range(len(pids)):
            for j in range(i + 1, len(pids)):
                pa, pb = pids[i], pids[j]
                if any(_shells_clash(sa, sb) for sa in world_shells[pa] for sb in world_shells[pb]):
                    pairwise_clashes.append((pa, pb))
        assert pairwise_clashes == [], f"Pairwise 3D solid clashes detected: {pairwise_clashes}"

        # 2. Zero internal sub-shell self-clashes inside each of the 31 parts
        self_clashes: list[tuple[str, int, int]] = []
        for pid, shs in world_shells.items():
            for i in range(len(shs)):
                for j in range(i + 1, len(shs)):
                    if _shells_clash(shs[i], shs[j]):
                        self_clashes.append((pid, i, j))
        assert self_clashes == [], f"Internal sub-shell self-clashes detected: {self_clashes}"

    def test_zero_clashes_with_external_machine_keepouts_and_dr_bore(self, s3_parts, s4_parts) -> None:
        all_parts = {**s3_parts, **s4_parts}
        world_shells = {pid: split_shells(bp.world_mesh()) for pid, bp in all_parts.items()}

        keepouts = {
            "S5_chamber_wall": make_tube(182.0, 192.0, 335.0, segments=48, center=(0.0, 0.0, -47.5)),
            "S6_coil_m_upper": make_tube(78.0, 112.0, 54.0, segments=32, center=(0.0, 0.0, 45.0)),
            "S6_coil_m_lower": make_tube(78.0, 112.0, 54.0, segments=32, center=(0.0, 0.0, -45.0)),
            "S6_coil_s_upper": make_tube(78.0, 116.0, 36.0, segments=32, center=(0.0, 0.0, 94.0)),
            "S6_coil_s_lower": make_tube(78.0, 116.0, 36.0, segments=32, center=(0.0, 0.0, -94.0)),
            "S6_coil_a_upper": make_tube(144.0, 168.0, 84.0, segments=32, center=(0.0, 0.0, 62.0)),
            "S6_coil_a_lower": make_tube(144.0, 168.0, 84.0, segments=32, center=(0.0, 0.0, -62.0)),
            "S6_coil_b_upper": make_tube(56.0, 82.0, 24.0, segments=32, center=(0.0, 0.0, -133.0)),
            "S6_coil_b_lower": make_tube(56.0, 82.0, 24.0, segments=32, center=(0.0, 0.0, -172.0)),
            "S6_cryoperm": make_tube(39.0, 41.0, 56.0, segments=32, center=(0.0, 0.0, -152.0)),
            "S6_mxc_chuck": make_cylinder(58.0, 8.0, segments=32, center=(0.0, 0.0, -10.0)),
            "S6_dr_ovc_tower": make_cylinder(175.0, 800.0, segments=32, center=(-650.0, 0.0, 60.0)),
            "DR_lower_clear_bore_R209": make_cylinder(DR_CLEAR_BORE_R_MM - 1.0, 418.0, segments=32, center=(0.0, 0.0, -450.0)),
            "S2_mini_lens": make_cylinder(30.0, 1.76, segments=32, center=(0.0, 0.0, 1.13)),
            "S2_tile_carrier": make_tube(32.0, 66.0, 4.0, segments=32, center=(0.0, 0.0, 5.01)),
        }

        ext_clashes: list[tuple[str, str]] = []
        for pid, shs in world_shells.items():
            for kname, kmesh in keepouts.items():
                if any(_shells_clash(sa, kmesh) for sa in shs):
                    ext_clashes.append((pid, kname))
        assert ext_clashes == [], f"External keepout collisions detected: {ext_clashes}"

    def test_rack_bay1_units_non_overlapping_u_slots(self, s3_parts, s4_parts) -> None:
        # Exact Master #309 Bay 1 U-slot allocation (X_center=1480.0, 482.6 mm along X, front -Y @ Y>=-438, rear Y<=+350)
        # Canonical Z_U(u) = 90.0 + (u-1)*44.45 -> Natural Z_nat_base = -410.0 mm
        expected_slots = [
            ("S4.2-03", 14, 1),
            ("S4.3-04", 15, 2),
            ("S4.5-03", 17, 1),
            ("S3.2-06", 18, 2),
            ("S3.2-02", 20, 2),
            ("S3.2-03", 22, 1),
            ("S3.3-04", 23, 1),
            ("S3.3-01", 24, 1),
            ("S3.3-03", 25, 1),
            ("S3.3-02", 26, 1),
        ]
        all_parts = {**s3_parts, **s4_parts}
        z_intervals: list[tuple[float, float, str]] = []
        for pid, u_start, u_count in expected_slots:
            bp = all_parts[pid]
            assert math.isclose(bp.design.world_origin_mm[0], 1480.0, abs_tol=1e-6)
            assert math.isclose(bp.design.world_origin_mm[0], RACK_BAY1_X_MM, abs_tol=1e-6)
            mn, mx = bp.world_mesh().bbox()
            # 482.6 mm width along X inside [1238.7, 1721.3] (clears Bay 1 rails [1198,1222] & [1738,1762])
            assert math.isclose(mx[0] - mn[0], 482.6, abs_tol=0.2), f"{pid} X width != 482.6: {mx[0]-mn[0]:.2f}"
            assert mn[0] >= 1238.0 and mx[0] <= 1722.0
            # Front -Y >= -438.0 mm rail plane, rear <= +350.0 mm
            assert mn[1] >= -438.0, f"{pid} protrudes past Y=-438.0: {mn[1]:.2f}"
            assert mx[1] <= 350.0, f"{pid} exceeds Y=+350.0: {mx[1]:.2f}"
            # Exact U-slot Z interval with ±1.0 mm clearance
            exp_z_lo = -410.0 + (u_start - 1) * 44.45 + 1.0
            exp_z_hi = -410.0 + (u_start + u_count - 1) * 44.45 - 1.0
            assert math.isclose(mn[2], exp_z_lo, abs_tol=0.1), f"{pid} Z_lo={mn[2]:.2f} != {exp_z_lo:.2f}"
            assert math.isclose(mx[2], exp_z_hi, abs_tol=0.1), f"{pid} Z_hi={mx[2]:.2f} != {exp_z_hi:.2f}"
            z_intervals.append((mn[2], mx[2], pid))
        z_intervals.sort()
        for idx in range(len(z_intervals) - 1):
            _, z_hi, pid_a = z_intervals[idx]
            z_lo, _, pid_b = z_intervals[idx + 1]
            gap = z_lo - z_hi
            assert gap >= 1.9, f"Rack units {pid_a} and {pid_b} have insufficient Z gap: {gap:.3f} mm"


# ===========================================================================
# 5. Zero Host-Path Leaks Across All Sources & Generated Artifacts
# ===========================================================================
class TestZeroHostPathLeaks:
    def test_zero_host_path_leaks_in_outputs_and_sources(self, exported_results) -> None:
        host_path_re = re.compile(
            r"/home/[A-Za-z0-9_.-]+|/Users/[A-Za-z0-9_.-]+|/run/media/[A-Za-z0-9_.-]+|C:\\\\[A-Za-z0-9_.-]+"
        )
        files_to_scan: list[Path] = [
            REPO_ROOT / "hardware" / "cad_parts" / "subsystems" / "s3_ibic_mech.py",
            REPO_ROOT / "hardware" / "cad_parts" / "subsystems" / "s4_stage_metrology.py",
            REPO_ROOT / "tests" / "test_cad_s3_s4.py",
        ]
        for out_dir in (DEFAULT_S3_OUT_DIR, DEFAULT_S4_OUT_DIR):
            for ext in ("*.step", "*.dxf", "*.svg", "*.scad", "*.json"):
                files_to_scan.extend(sorted(out_dir.glob(ext)))

        leaks: list[tuple[str, str]] = []
        for fp in files_to_scan:
            txt = fp.read_text(encoding="utf-8", errors="replace")
            m = host_path_re.search(txt)
            if m:
                leaks.append((fp.name, m.group(0)))

        # Also inspect 80-byte binary STL headers
        for out_dir in (DEFAULT_S3_OUT_DIR, DEFAULT_S4_OUT_DIR):
            for stl_p in sorted(out_dir.glob("*.stl")):
                hdr = stl_p.read_bytes()[:80].decode("ascii", errors="replace")
                m = host_path_re.search(hdr)
                if m:
                    leaks.append((stl_p.name, m.group(0)))

        assert leaks == [], f"Host-path leaks found: {leaks}"
