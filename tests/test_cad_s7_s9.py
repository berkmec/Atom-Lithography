"""Comprehensive verification suite for Wave 2B WP-M5 mechanical CAD deliverables:
- Subsystem S7 (19 physical parts: S7.1-01..S7.SAFETY-06, excl. $0 superseded S7.1-04)
- Subsystem S9 non-OptQ (10 physical parts: S9.1-01..S9.3-03 + S9.HPC-01..03)

Verifies:
1. Exact 29/29 BOM physical part coverage & zero bom_id aliasing.
2. 100% watertight solid meshes (0 boundary, 0 non-manifold, 0 orientation errors).
3. Zero inter-part shell clashes across all 29 parts + explicit physical clearances
   around S5.1-01, S5.5 +Y optics, S6.8-01 DR OVC, S1.6-01/02, S6.8-02, Bay 1/2, UPS & HPC.
4. Canonical Exp150 S7.SAFETY-01..06 mass check (355.0 kg exact) & Exp143 S9.HPC-01..03 (64.0 kg exact).
5. Cryogenic 300 K -> 4 K cold-clearance verification for S7.3-01/02.
6. All 5 manufacturing artifacts (.stl/.step/.dxf/.svg/.scad) + .json valid for 29/29 parts.
7. Locked epistemic flags (iec61508_certified=False, semi_s2_certified=False, no_lab_measurement=True)
   and zero host-path leaks across every exported file and source module.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from hardware.cad_parts.core import (
    DESIGN_MATURITY,
    REPO_ROOT,
    check_cold_clearance,
    compute_mass_props,
    get_bom_row,
    list_physical_part_ids,
    read_binary_stl,
    split_shells,
    validate_dxf_file,
    validate_scad_file,
    validate_step_file,
    validate_svg_file,
    verify_watertight,
)
from hardware.cad_parts.subsystems import s7_racks_safety, s9_spares_hpc
from hardware.cad_parts.subsystems.s7_racks_safety import (
    RACK_BAY1_X_MM,
    RACK_BAY2_X_MM,
    S7_OUT_DIR,
    S7_SAFETY_TARGET_MASS_KG,
    build_s7_parts,
)
from hardware.cad_parts.subsystems.s9_spares_hpc import (
    HPC_STACK_X_MM,
    HPC_STACK_Y_MM,
    S9_HPC_TARGET_MASS_KG,
    S9_OUT_DIR,
    build_s9_spares_hpc_parts,
)


def _aabb_overlap(
    a_min: tuple[float, float, float],
    a_max: tuple[float, float, float],
    b_min: tuple[float, float, float],
    b_max: tuple[float, float, float],
    tol: float = 1e-4,
) -> bool:
    return (
        min(a_max[0], b_max[0]) - max(a_min[0], b_min[0]) > tol
        and min(a_max[1], b_max[1]) - max(a_min[1], b_min[1]) > tol
        and min(a_max[2], b_max[2]) - max(a_min[2], b_min[2]) > tol
    )


@pytest.fixture(scope="module")
def built_s7() -> dict[str, s7_racks_safety.BuiltPart]:
    return build_s7_parts()


@pytest.fixture(scope="module")
def built_s9() -> dict[str, s7_racks_safety.BuiltPart]:
    return build_s9_spares_hpc_parts()


@pytest.fixture(scope="module")
def all_29_parts(
    built_s7: dict[str, s7_racks_safety.BuiltPart],
    built_s9: dict[str, s7_racks_safety.BuiltPart],
) -> dict[str, s7_racks_safety.BuiltPart]:
    return {**built_s7, **built_s9}


@pytest.fixture(scope="module")
def exported_results() -> dict[str, object]:
    r7 = s7_racks_safety.export_all(S7_OUT_DIR)
    r9 = s9_spares_hpc.export_all(S9_OUT_DIR)
    return {**r7, **r9}


# ===========================================================================
# 1. Exact 29/29 BOM Physical Part Coverage & Zero Aliasing
# ===========================================================================
class TestCoverageAndSchema:
    def test_exact_29_of_29_part_ids(
        self,
        built_s7: dict[str, s7_racks_safety.BuiltPart],
        built_s9: dict[str, s7_racks_safety.BuiltPart],
    ) -> None:
        expected_s7 = list_physical_part_ids("S7")
        expected_s9 = [p for p in list_physical_part_ids("S9") if not p.startswith("S9.4-")]
        assert len(expected_s7) == 19
        assert len(expected_s9) == 10
        assert "S7.1-04" not in expected_s7  # $0 superseded row excluded
        assert set(built_s7.keys()) == set(expected_s7)
        assert set(built_s9.keys()) == set(expected_s9)
        assert len(built_s7) + len(built_s9) == 29

    def test_bom_cross_reference_and_epistemic_locks(
        self,
        all_29_parts: dict[str, s7_racks_safety.BuiltPart],
    ) -> None:
        for pid, bp in all_29_parts.items():
            row = get_bom_row(pid)
            pd = bp.design
            assert pd.part_id == row.part_id
            assert pd.parent_bom_id == row.parent_bom_id
            assert pd.subsystem == row.subsystem
            assert pd.design_maturity == DESIGN_MATURITY
            assert pd.no_lab_measurement is True
            assert pd.iec61508_certified is False
            assert pd.semi_s2_certified is False
            assert len(pd.ports) >= 1, f"{pid} missing PortInterface"
            assert len(pd.dimensions) >= 2, f"{pid} missing DimensionCallouts"
            assert len(pd.gdt_frames) >= 1, f"{pid} missing GDTFrame"


# ===========================================================================
# 2. 100% Watertight Geometry & Physical Mass Verification
# ===========================================================================
class TestWatertightAndMass:
    def test_all_29_parts_strictly_watertight(
        self,
        all_29_parts: dict[str, s7_racks_safety.BuiltPart],
    ) -> None:
        for pid, bp in sorted(all_29_parts.items()):
            v = verify_watertight(bp.mesh)
            assert v.watertight, f"{pid} NOT watertight: {v}"
            assert v.boundary_edges == 0, f"{pid} has {v.boundary_edges} boundary edges"
            assert v.non_manifold_edges == 0, f"{pid} has {v.non_manifold_edges} non-manifold edges"
            assert v.orientation_errors == 0, f"{pid} has {v.orientation_errors} orientation errors"
            assert v.degenerate_faces == 0, f"{pid} has {v.degenerate_faces} degenerate faces"
            assert v.signed_volume_mm3 > 0.0
            assert v.min_shell_volume_mm3 > 0.0
            mp = compute_mass_props(bp.mesh, material=bp.design.material, density_kg_m3=bp.density_kg_m3)
            assert mp.mass_kg > 0.0
            assert 250.0 <= mp.density_kg_m3 <= 12000.0, f"{pid} unrealistic density {mp.density_kg_m3:.1f} kg/m3"

    def test_s7_safety_masses_match_exp150_exact_355kg(
        self,
        built_s7: dict[str, s7_racks_safety.BuiltPart],
    ) -> None:
        spec_path = REPO_ROOT / "results" / "exp150_industrial_safety_fmea_hazop" / "s_safety_spec.json"
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        spec_masses = {item["part_id"]: float(item["mass_kg_total"]) for item in spec["items"]}
        assert spec_masses == S7_SAFETY_TARGET_MASS_KG

        total_safety_kg = 0.0
        for pid, expected_kg in spec_masses.items():
            bp = built_s7[pid]
            mp = compute_mass_props(bp.mesh, material=bp.design.material, density_kg_m3=bp.density_kg_m3)
            assert math.isclose(mp.mass_kg, expected_kg, rel_tol=1e-4), (
                f"{pid} mass {mp.mass_kg:.4f} kg != Exp150 spec {expected_kg:.4f} kg"
            )
            assert bp.design.iec61508_certified is False
            assert bp.design.semi_s2_certified is False
            total_safety_kg += mp.mass_kg
        assert math.isclose(total_safety_kg, 355.0, abs_tol=0.05)

    def test_s9_hpc_masses_match_exp143_exact_64kg(
        self,
        built_s9: dict[str, s7_racks_safety.BuiltPart],
    ) -> None:
        spec_path = REPO_ROOT / "results" / "exp143_d3_grape_m4_and_hpc_decoder" / "s9hpc_hardware_spec.json"
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        spec_masses = {item["part_id"]: float(item["mass_kg_total"]) for item in spec["items"]}
        assert spec_masses == S9_HPC_TARGET_MASS_KG

        total_hpc_kg = 0.0
        for pid, expected_kg in spec_masses.items():
            bp = built_s9[pid]
            mp = compute_mass_props(bp.mesh, material=bp.design.material, density_kg_m3=bp.density_kg_m3)
            assert math.isclose(mp.mass_kg, expected_kg, rel_tol=1e-4), (
                f"{pid} mass {mp.mass_kg:.4f} kg != Exp143 spec {expected_kg:.4f} kg"
            )
            total_hpc_kg += mp.mass_kg
        assert math.isclose(total_hpc_kg, 64.0, abs_tol=0.05)

    def test_cryo_4k_cold_clearance_s7_3(self) -> None:
        c_socket = check_cold_clearance(
            "PEEK",
            "Si",
            nominal_outer_id_mm=8.25,
            nominal_inner_od_mm=8.00,
            t_cold_k=4.0,
            min_required_radial_clearance_mm=0.04,
            outer_id_tol_mm=0.02,
            inner_od_tol_mm=0.01,
        )
        assert c_socket.passed is True
        assert c_socket.interference_risk is False

        c_carrier = check_cold_clearance(
            "Invar-36",
            "Si",
            nominal_outer_id_mm=16.0,
            nominal_inner_od_mm=15.8,
            t_cold_k=4.0,
            min_required_radial_clearance_mm=0.05,
        )
        assert c_carrier.passed is True
        assert c_carrier.interference_risk is False


# ===========================================================================
# 3. Coordinate Hygiene: Zero Intra-Subsystem Clashes & Global Keepout Checks
# ===========================================================================
class TestCoordinateHygieneAndClearances:
    def test_zero_inter_part_shell_clashes_across_all_29_parts(
        self,
        all_29_parts: dict[str, s7_racks_safety.BuiltPart],
    ) -> None:
        shells_by_part = {
            pid: [sh.bbox() for sh in split_shells(bp.mesh)]
            for pid, bp in all_29_parts.items()
        }
        pids = sorted(all_29_parts.keys())
        clashes: list[tuple[str, int, str, int]] = []
        for i, p1 in enumerate(pids):
            for p2 in pids[i + 1 :]:
                for a, bb1 in enumerate(shells_by_part[p1]):
                    for b, bb2 in enumerate(shells_by_part[p2]):
                        if _aabb_overlap(bb1[0], bb1[1], bb2[0], bb2[1], tol=1e-4):
                            clashes.append((p1, a, p2, b))
        assert clashes == [], f"Found {len(clashes)} shell clashes: {clashes[:10]}"

    def test_s7_safety_02_clears_s51_chamber_and_s55_optics(
        self,
        built_s7: dict[str, s7_racks_safety.BuiltPart],
    ) -> None:
        shroud_shells = [sh.bbox() for sh in split_shells(built_s7["S7.SAFETY-02"].mesh)]
        bmin, bmax = built_s7["S7.SAFETY-02"].mesh.bbox()
        # Canonical datum Z_FLOOR=0, Z_WAFER=+500; Y in [+340, +620], Z shroud body in [390.0, 622.0]
        assert bmin[1] >= 339.9
        assert bmax[1] <= 620.1
        assert bmin[1] - 192.0 >= 140.0
        assert math.isclose(bmin[2], 390.0, abs_tol=0.1)

        # S5.1-01 UHV vessel keepout box (R=192 mm, Z_canon in [275, 645])
        s51_box = ((-192.0, -192.0, 275.0), (192.0, 192.0, 645.0))
        # S5.5 +Y 808 nm optical head + dichroic pyrometer (top Z=601.7 mm!) + collimator keepout box
        s55_optics_box = ((-63.0, 340.0, 443.0), (63.0, 467.0, 602.0))
        for bb in shroud_shells:
            assert not _aabb_overlap(bb[0], bb[1], s51_box[0], s51_box[1]), "S7.SAFETY-02 clashes S5.1-01!"
            assert not _aabb_overlap(bb[0], bb[1], s55_optics_box[0], s55_optics_box[1]), "S7.SAFETY-02 clashes S5.5 optics!"

    def test_s7_safety_05_dn50_nozzle_clears_dr_ovc_wall(
        self,
        built_s7: dict[str, s7_racks_safety.BuiltPart],
    ) -> None:
        s05_shells = [sh.bbox() for sh in split_shells(built_s7["S7.SAFETY-05"].mesh)]
        # S6.8-04 DR OVC cylinder keepout box at X=-650 (R=198 mm, Y in [-198, +198], Z in [160, 990])
        ovc_box = ((-848.0, -198.0, 160.0), (-452.0, 198.0, 990.0))
        # S5.1-01 main chamber + S6.9 cryo bridge keepout box
        s51_bridge_box = ((-475.0, -225.0, 275.0), (225.0, 225.0, 645.0))
        for bb in s05_shells:
            assert not _aabb_overlap(bb[0], bb[1], ovc_box[0], ovc_box[1]), "S7.SAFETY-05 clashes S6.8-04 DR OVC!"
            assert not _aabb_overlap(bb[0], bb[1], s51_bridge_box[0], s51_bridge_box[1]), "S7.SAFETY-05 clashes S5.1/S6.9!"
        # Confirm DN50 rupture-disk nozzle shell mates S6.8-04 +Y port at X=-650, Y in [198.5, 410], Z=820
        nozzle_found = any(
            (-690.0 <= 0.5 * (bb[0][0] + bb[1][0]) <= -610.0)
            and (198.4 <= bb[0][1] and bb[1][1] <= 410.0)
            and (780.0 <= 0.5 * (bb[0][2] + bb[1][2]) <= 860.0)
            for bb in s05_shells
        )
        assert nozzle_found, "ASME DN50 rupture-disk nozzle missing on S6.8-04 +Y port (-650, +198.5..410, 820)"
        # Confirm floor quench dump bank sits cleanly in X=[750, 1010], Y=[180, 440], Z=[0, 390]
        quench_found = any(
            (749.9 <= bb[0][0] and bb[1][0] <= 1010.1)
            and (179.9 <= bb[0][1] and bb[1][1] <= 440.1)
            and (-0.1 <= bb[0][2] and bb[1][2] <= 390.1)
            for bb in s05_shells
        )
        assert quench_found, "1.563 Ohm floor quench bank missing in X=[750,1010], Y=[180,440], Z=[0,390]"

    def test_s7_safety_01_clears_s16_and_s68_ghs(
        self,
        built_s7: dict[str, s7_racks_safety.BuiltPart],
    ) -> None:
        s01_shells = [sh.bbox() for sh in split_shells(built_s7["S7.SAFETY-01"].mesh)]
        s16_box = ((-1600.0, 750.0, 0.0), (-1100.0, 1870.0, 2500.0))
        s68_ghs_box = ((-1600.0, -1100.0, 0.0), (-1000.0, -500.0, 2000.0))
        for bb in s01_shells:
            assert not _aabb_overlap(bb[0], bb[1], s16_box[0], s16_box[1]), "S7.SAFETY-01 clashes S1.6-01/02!"
            assert not _aabb_overlap(bb[0], bb[1], s68_ghs_box[0], s68_ghs_box[1]), "S7.SAFETY-01 clashes S6.8-02 GHS!"

    def test_racks_ups_hpc_and_4x_estop_layout(
        self,
        built_s7: dict[str, s7_racks_safety.BuiltPart],
        built_s9: dict[str, s7_racks_safety.BuiltPart],
    ) -> None:
        # Canonical datum check: Z_FLOOR = 0.0, Z_WAFER = +500.0
        assert s7_racks_safety.Z_FLOOR_MM == 0.0
        assert s7_racks_safety.Z_WAFER_MM == 500.0
        assert RACK_BAY1_X_MM == 1480.0
        assert RACK_BAY2_X_MM == 2100.0

        # 2x 42U cabinets span Bay 1 (X=[1180,1780], 19.5 mm clear of S5.1-04 foot 1160.5) & Bay 2 (X=[1800,2400])
        bmin_cab, bmax_cab = built_s7["S7.4-03"].mesh.bbox()
        assert math.isclose(bmin_cab[0], 1180.0, abs_tol=1.0)
        assert bmin_cab[0] - 1160.5 >= 19.0
        assert math.isclose(bmax_cab[0], 2400.0, abs_tol=1.0)
        assert math.isclose(bmin_cab[2], 0.0, abs_tol=0.5)

        # Verify Master Bay 1 U14-U35 (Z in [667.85, 1645.75]) is 100% open for S4/S3/S1/S2
        u14_u35_box = ((1238.0, -445.0, 668.0), (1722.0, 350.0, 1645.5))
        for pid in ("S7.1-01", "S7.1-02", "S7.1-03", "S7.2-01", "S7.2-02", "S7.2-03", "S7.4-01", "S7.4-02", "S7.4-04", "S7.SAFETY-03"):
            for sh in split_shells(built_s7[pid].mesh):
                bb = sh.bbox()
                assert not _aabb_overlap(bb[0], bb[1], u14_u35_box[0], u14_u35_box[1]), f"{pid} intrudes into Bay 1 U14-U35!"

        # S7.SAFETY-04 UPS clears Bay 2 in X and S9.HPC in Y
        bmin_ups, bmax_ups = built_s7["S7.SAFETY-04"].mesh.bbox()
        bmin_hpc, bmax_hpc = built_s9["S9.HPC-01"].mesh.bbox()
        assert bmin_ups[0] - bmax_cab[0] >= 25.0
        assert bmin_ups[1] - bmax_hpc[1] >= 80.0
        assert math.isclose(bmin_ups[2], 0.0, abs_tol=0.5)
        assert math.isclose(0.5 * (bmin_hpc[0] + bmax_hpc[0]), HPC_STACK_X_MM, abs_tol=1.0)
        assert math.isclose(0.5 * (bmin_hpc[1] + bmax_hpc[1]), HPC_STACK_Y_MM, abs_tol=20.0)

        # 4x perimeter E-Stop pedestals present at room corners (±1900, ±1900)
        s03_shells = [sh.bbox() for sh in split_shells(built_s7["S7.SAFETY-03"].mesh)]
        for cx, cy in ((-1900.0, -1900.0), (1900.0, -1900.0), (1900.0, 1900.0), (-1900.0, 1900.0)):
            assert any(
                abs(0.5 * (bb[0][0] + bb[1][0]) - cx) < 5.0 and abs(0.5 * (bb[0][1] + bb[1][1]) - cy) < 5.0
                for bb in s03_shells
            ), f"Missing E-Stop pedestal at corner ({cx}, {cy})"


# ===========================================================================
# 4. Full 5-Artifact + JSON Export, Format Validators & Zero Host-Path Leaks
# ===========================================================================
class TestExportsAndPortability:
    def test_all_29_parts_export_valid_artifacts_and_json(
        self,
        exported_results: dict[str, object],
    ) -> None:
        assert len(exported_results) == 29
        for pid, res in sorted(exported_results.items()):
            assert res.all_valid, f"{pid} export invalid: {res.warnings}"
            assert res.watertight is True
            assert res.boundary_edges == 0
            assert res.non_manifold_edges == 0
            assert res.iec61508_certified is False
            assert res.semi_s2_certified is False
            assert res.no_lab_measurement is True

            out_dir = S7_OUT_DIR if pid.startswith("S7") else S9_OUT_DIR
            stl_p = out_dir / f"{pid}.stl"
            step_p = out_dir / f"{pid}.step"
            dxf_p = out_dir / f"{pid}.dxf"
            svg_p = out_dir / f"{pid}.svg"
            scad_p = out_dir / f"{pid}.scad"
            json_p = out_dir / f"{pid}.json"

            for p in (stl_p, step_p, dxf_p, svg_p, scad_p, json_p):
                assert p.is_file(), f"Missing exported file: {p}"

            # Binary STL size + watertight round-trip
            assert stl_p.stat().st_size == 84 + 50 * res.triangle_count
            loaded_stl = read_binary_stl(stl_p)
            assert verify_watertight(loaded_stl).watertight

            # Strict format validators
            assert validate_step_file(step_p).valid
            assert validate_dxf_file(dxf_p).valid
            assert validate_svg_file(svg_p).valid
            assert validate_scad_file(scad_p).valid

            # JSON manifest integrity
            doc = json.loads(json_p.read_text(encoding="utf-8"))
            assert doc["part_design"]["part_id"] == pid
            assert doc["part_design"]["epistemic"]["iec61508_certified"] is False
            assert doc["part_design"]["epistemic"]["semi_s2_certified"] is False
            assert doc["part_design"]["epistemic"]["no_lab_measurement"] is True
            assert doc["artifact"]["all_valid"] is True
            assert len(doc["shell_bboxes_mm"]) >= 1

        # Verify summary manifests exist and match totals
        s7_man = json.loads((S7_OUT_DIR / "S7_manifest.json").read_text(encoding="utf-8"))
        s9_man = json.loads((S9_OUT_DIR / "S9_spares_hpc_manifest.json").read_text(encoding="utf-8"))
        assert s7_man["part_count"] == 19 and s7_man["all_valid"] is True
        assert math.isclose(s7_man["s7_safety_total_mass_kg"], 355.0, abs_tol=0.05)
        assert s9_man["part_count"] == 10 and s9_man["all_valid"] is True
        assert math.isclose(s9_man["option_hpc_total_mass_kg"], 64.0, abs_tol=0.05)

    def test_zero_host_path_leaks_across_all_outputs_and_sources(
        self,
        exported_results: dict[str, object],
    ) -> None:
        assert len(exported_results) == 29
        forbidden_tokens = ("/home/", "/Users/", "C:\\", "/run/media/")
        scan_files: list[Path] = [
            REPO_ROOT / "hardware" / "cad_parts" / "subsystems" / "s7_racks_safety.py",
            REPO_ROOT / "hardware" / "cad_parts" / "subsystems" / "s9_spares_hpc.py",
        ]
        for out_dir in (S7_OUT_DIR, S9_OUT_DIR):
            for ext in ("*.step", "*.dxf", "*.svg", "*.scad", "*.json"):
                scan_files.extend(sorted(out_dir.glob(ext)))

        assert len(scan_files) >= 2 + 29 * 5 + 2
        leaks: list[str] = []
        for fpath in scan_files:
            txt = fpath.read_text(encoding="utf-8", errors="replace")
            for tok in forbidden_tokens:
                if tok in txt:
                    leaks.append(f"{fpath.relative_to(REPO_ROOT)} contains {tok!r}")
        assert leaks == [], f"Host-path leaks detected: {leaks[:10]}"
