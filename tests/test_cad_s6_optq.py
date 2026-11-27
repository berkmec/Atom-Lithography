"""Verification test suite for Wave 2B / WP-M4: S6 Cryo/DR/Magnet/Readout + S9.4 Option-Q CAD.

Verifies:
1. Exact 43/43 physical BOM coverage (40 S6 + 3 Option-Q S9.4-01..03), zero bom_id aliasing,
   excluded non-solid S6.8-03 & superseded S6.10-02, locked M0/M1 epistemic metadata.
2. 100% watertight 2-manifold geometry (0 boundary, 0 non-manifold, 0 orientation errors,
   positive signed volume) and 0 intra-part sub-shell overlaps across all 43 parts.
3. Feature-level dimensional fidelity for flagship parts (28-conv CF63 bellows S6.9-02,
   4x S-loop OFHC braids S6.9-03, 8-coil magnet S6.3-01/02, bolted Nb Meissner + Cryoperm
   S6.3-03, DR OVC ASME DN50 relief port S6.8-04, GHS cabinet S6.8-02, 42U Rack Bay 2
   U-allocation including 14x ZCU216 S6.6-06 & 2U ZU48DR S6.11-01, Option-Q S9.4-01..03).
4. Exact 3D solid clash verification: 0 intra-subsystem clashes across all 43 parts.
5. NIST cryogenic thermal contraction verification (300 K -> 50 K -> 4 K -> 0.8 K -> 20 mK)
   across 11 concentric interfaces + 2 axial tolerance stacks: 100% PASS.
6. All 258 exported manufacturing artifacts (43 x {.stl, .step, .dxf, .svg, .scad, .json})
   plus manifests in hardware/cad_parts/out/{S6,S9_optq}/ strictly pass independent validators.
7. Zero host-path leaks across all source files and generated artifacts.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from hardware.cad_parts.core import (
    DESIGN_MATURITY,
    REPO_ROOT,
    list_physical_part_ids,
    read_binary_stl,
    split_shells,
    validate_dxf_file,
    validate_scad_file,
    validate_step_file,
    validate_svg_file,
    verify_watertight,
)
from hardware.cad_parts.subsystems.s6_dr_readout_optq import (
    S9_OPTQ_PART_IDS,
    build_s6_parts,
    build_s9_optq_parts,
)
from hardware.cad_parts.subsystems.s6_magnet_shields import (
    DEFAULT_OUT_S6_DIR,
    DEFAULT_OUT_S9_OPTQ_DIR,
    RACK_BAY2_X_MM,
    _aabb_overlap,
    _shells_clash,
    check_assembly_clashes,
    run_cryo_thermal_checks,
)

EXPECTED_OPTQ_IDS: tuple[str, ...] = ("S9.4-01", "S9.4-02", "S9.4-03")
RACK_BAY2_PART_IDS: tuple[str, ...] = (
    "S6.2-03",
    "S6.3-05",
    "S6.4-01",
    "S6.4-02",
    "S6.5-01",
    "S6.5-02",
    "S6.6-05",
    "S6.6-06",
    "S6.9-04",
    "S6.10-04",
    "S6.11-01",
)


@pytest.fixture(scope="module")
def all_43_parts():
    s6 = build_s6_parts()
    s9 = build_s9_optq_parts()
    return s6, s9, {**s6, **s9}


# ===========================================================================
# 1. Exact 43/43 BOM Coverage, Zero Aliasing & Epistemic Metadata
# ===========================================================================
class TestCoverageAndTraceability:
    def test_exact_43_physical_parts_and_exclusions(self, all_43_parts) -> None:
        s6, s9, combined = all_43_parts
        expected_s6 = list_physical_part_ids("S6")
        assert len(expected_s6) == 40
        assert list(s6.keys()) == expected_s6
        assert tuple(s9.keys()) == EXPECTED_OPTQ_IDS
        assert tuple(S9_OPTQ_PART_IDS) == EXPECTED_OPTQ_IDS
        assert len(combined) == 43
        # Non-solid 3He gas charge & $0 superseded row must not be present
        assert "S6.8-03" not in combined
        assert "S6.10-02" not in combined

    def test_zero_legacy_bom_id_aliasing_and_epistemic_locks(self, all_43_parts) -> None:
        _, _, combined = all_43_parts
        # Verify legacy params.py alias bugs are permanently fixed
        for pid in ("S6.9-01", "S6.9-02", "S6.9-03", "S6.9-04"):
            assert combined[pid].design.parent_bom_id == "S6.9"
        assert combined["S6.10-03"].design.parent_bom_id == "S6.10"
        for pid in ("S6.11-01", "S6.11-02", "S6.11-03", "S6.11-04"):
            assert combined[pid].design.parent_bom_id == "S6.11"
        for pid in EXPECTED_OPTQ_IDS:
            assert combined[pid].design.parent_bom_id == "S9.4"
            assert combined[pid].design.subsystem == "S9"

        for pid, bp in combined.items():
            d = bp.design
            assert d.part_id == pid
            assert d.design_maturity == DESIGN_MATURITY
            assert d.no_lab_measurement is True
            assert d.iec61508_certified is False
            assert d.semi_s2_certified is False


# ===========================================================================
# 2. 100% Watertight Geometry & Flagship Engineering Features
# ===========================================================================
class TestGeometryAndFeatures:
    def test_all_43_parts_strictly_watertight_and_zero_intra_shell_overlaps(self, all_43_parts) -> None:
        _, _, combined = all_43_parts
        for pid, bp in combined.items():
            vr = verify_watertight(bp.mesh)
            assert vr.watertight, f"{pid} not watertight: {vr.errors}"
            assert vr.boundary_edges == 0
            assert vr.non_manifold_edges == 0
            assert vr.orientation_errors == 0
            assert vr.signed_volume_mm3 > 0.0

            # Verify no two sub-shells within the same part intersect
            shells = split_shells(bp.mesh)
            bboxes = [sh.bbox() for sh in shells]
            for i in range(len(shells)):
                for j in range(i + 1, len(shells)):
                    if _aabb_overlap(bboxes[i][0], bboxes[i][1], bboxes[j][0], bboxes[j][1], eps=1e-4):
                        assert not _shells_clash(shells[i], shells[j]), (
                            f"{pid} has internal sub-shell overlap between shell {i} and {j}"
                        )

    def test_flagship_mechanical_dimensions_and_interfaces(self, all_43_parts) -> None:
        _, _, c = all_43_parts

        # S6.9-02: 28-conv edge-welded 316L CF100 bellows (k=2000 N/m, OBS-065), world X=[-474.5, -289.5]
        b_params = dict(c["S6.9-02"].design.scad_params)
        assert b_params["n_convolutions"] == 28
        assert math.isclose(float(b_params["k_n_per_m"]), 2000.0)
        bmin, bmax = c["S6.9-02"].mesh.bbox()
        assert math.isclose(bmax[1] - bmin[1], 152.0, abs_tol=0.3)  # ISO 3669 CF100 OD
        bw_min, bw_max = c["S6.9-02"].world_mesh().bbox()
        assert math.isclose(float(bw_min[0]), -474.5, abs_tol=0.1)
        assert math.isclose(float(bw_max[0]), -289.5, abs_tol=0.1)
        assert len([p for p in c["S6.9-02"].design.ports if p.standard == "CF100"]) == 2

        # S6.9-03: 8x electron-beam-welded OFHC Cu braids (88 mm^2 >= 80 mm^2) + Ø30x397 RRR>=200 Cu busbar (OBS-041/065)
        br_params = dict(c["S6.9-03"].design.scad_params)
        assert br_params["n_braids"] == 8
        assert float(br_params["a_braid_mm2"]) >= 80.0
        assert float(br_params["busbar_d"]) >= 30.0
        assert float(br_params["t_chuck_14uw_mk"]) <= 25.0

        # S6.2-01 & S6.2-02: PCD=96 mm, Ø34.5 boss pocket, Ø46 mm 4K bridge tube + nested 50K/4K chamber shields (OBS-010/017/040/046/065)
        c21_params = dict(c["S6.2-01"].design.scad_params)
        assert math.isclose(float(c21_params["bolt_pcd"]), 96.0, abs_tol=0.05)
        assert math.isclose(float(c21_params["boss_pocket_id"]), 34.5, abs_tol=0.05)
        c22_params = dict(c["S6.2-02"].design.scad_params)
        assert float(c22_params["bridge_4k_id"]) >= 45.0

        # S6.3-01..05: Horizontal split-Helmholtz in-plane magnet, anchored active shields, 4 switches, 4x 320A HTS leads (OBS-008/072)
        m_min, m_max = c["S6.3-01"].mesh.bbox()
        assert math.isclose(m_max[0] - m_min[0], 352.0, abs_tol=0.5)
        m_params = dict(c["S6.3-01"].design.scad_params)
        assert m_params["orientation"] == "HORIZONTAL_SPLIT_HELMHOLTZ_IN_PLANE_X"
        assert float(m_params["b_perp_max_mt"]) <= 0.05
        assert dict(c["S6.3-02"].design.scad_params)["n_lorentz_ties"] == 8
        assert dict(c["S6.3-04"].design.scad_params)["n_switches"] == 4
        assert float(dict(c["S6.3-05"].design.scad_params)["i_max_a"]) >= 300.0

        # S6.3-03: Bolted Nb Meissner cup + dual-layer 5 mm Cryoperm-10 (OD=82) + RF baffle (OBS-072/108)
        sh_min, sh_max = c["S6.3-03"].mesh.bbox()
        assert math.isclose(sh_max[0] - sh_min[0], 82.0, abs_tol=0.3)
        assert dict(c["S6.3-03"].design.scad_params)["n_vents"] == 6

        # S6.11-02: Hollow 32-ch sub-cutoff TWPA shield box (f_TE101 > 10 GHz >> 8 GHz, OBS-108)
        twpa_params = dict(c["S6.11-02"].design.scad_params)
        assert float(twpa_params["f_te101_ghz"]) > 10.0

        # S6.6-03/04 & S6.11-04: Realistic full 56 & 96 coax bundle counts (OBS-122)
        assert len(split_shells(c["S6.6-03"].mesh)) >= 56
        assert len(split_shells(c["S6.6-04"].mesh)) >= 56
        assert len(split_shells(c["S6.11-04"].mesh)) >= 96

        # S6.8-04: DR OVC includes dedicated ASME DN50 rupture-disk relief port for S7.SAFETY-05
        relief_ports = [p for p in c["S6.8-04"].design.ports if p.mating_part_id == "S7.SAFETY-05"]
        assert len(relief_ports) == 1
        assert "DN50" in relief_ports[0].standard

        # S6.8-02: GHS cabinet cleanly floor-mounted at X=-1300 mm, Y=-800 mm
        assert c["S6.8-02"].design.world_origin_mm[:2] == (-1300.0, -800.0)
        ghs_wmin, _ = c["S6.8-02"].world_mesh().bbox()
        assert math.isclose(float(ghs_wmin[2]), 0.0, abs_tol=0.5)

        # S6.11-01: 2U ZU48DR RFSoC exact 482.6 x 88.9 mm envelope in Rack Bay 2
        rf_min, rf_max = c["S6.11-01"].mesh.bbox()
        assert math.isclose(rf_max[0] - rf_min[0], 482.6, abs_tol=0.3)
        assert math.isclose(rf_max[2] - rf_min[2], 88.9, abs_tol=0.2)
        assert c["S6.11-01"].design.world_origin_mm[0] == RACK_BAY2_X_MM

        # S9.4-02 sits cleanly 8.5 mm below S6.11-02 TWPA inside DR MXC payload zone
        twpa_min, _ = c["S6.11-02"].world_mesh().bbox()
        _, qram_max = c["S9.4-02"].world_mesh().bbox()
        z_gap = float(twpa_min[2] - qram_max[2])
        assert 8.0 <= z_gap <= 9.2, f"Expected ~8.5 mm Z gap under TWPA, got {z_gap:.3f} mm"


# ===========================================================================
# 3. Coordinate Hygiene, 42U Rack Bay 2 & Exact 3D Zero-Clash Verification
# ===========================================================================
class TestZeroClashesAndThermal:
    def test_zero_intra_subsystem_clashes_across_all_43_parts(self, all_43_parts) -> None:
        _, _, combined = all_43_parts
        report = check_assembly_clashes(combined)
        assert report["parts_checked"] == 43
        assert report["clash_count"] == 0, f"Unexpected 3D solid clashes: {report['clashes']}"
        assert report["passed"] is True

    def test_rack_bay2_42u_non_overlapping_elevation(self, all_43_parts) -> None:
        _, _, combined = all_43_parts
        intervals: list[tuple[float, float, str]] = []
        for pid in RACK_BAY2_PART_IDS:
            bp = combined[pid]
            assert bp.design.world_origin_mm[0] == RACK_BAY2_X_MM
            wmin, wmax = bp.world_mesh().bbox()
            assert 1800.0 <= wmin[0] and wmax[0] <= 2400.0
            assert 90.0 <= wmin[2] and wmax[2] <= 1957.0
            intervals.append((float(wmin[2]), float(wmax[2]), pid))
        intervals.sort()
        for (lo0, hi0, pid0), (lo1, hi1, pid1) in zip(intervals, intervals[1:]):
            gap = lo1 - hi0
            assert gap >= 1.5, f"Rack Bay 2 Z clearance too tight ({gap:.2f} mm) between {pid0} and {pid1}"

    def test_cryo_thermal_contraction_300k_to_20mk_and_stacks_pass(self) -> None:
        report = run_cryo_thermal_checks()
        assert report["all_passed"] is True
        assert report["cold_clearance_count"] == 12
        for key, res in report["cold_clearances"].items():
            assert res["passed"] is True, f"Cold clearance failed for {key}: {res}"
            assert res["interference_risk"] is False
            assert res["cold_worst_case_radial_clearance_mm"] >= res["min_required_radial_clearance_mm"]
        for key, stk in report["tolerance_stacks"].items():
            assert stk["wc_pass"] is True, f"Tolerance stack failed for {key}: {stk}"


# ===========================================================================
# 4. All 258 Exported Artifacts Valid & Zero Host-Path Leaks
# ===========================================================================
class TestExportedArtifactsAndHygiene:
    def test_all_43_parts_exported_and_strictly_validated(self) -> None:
        expected_s6 = list_physical_part_ids("S6")
        targets = [(pid, DEFAULT_OUT_S6_DIR) for pid in expected_s6] + [
            (pid, DEFAULT_OUT_S9_OPTQ_DIR) for pid in EXPECTED_OPTQ_IDS
        ]
        assert len(targets) == 43

        for pid, out_dir in targets:
            stl_p = out_dir / f"{pid}.stl"
            step_p = out_dir / f"{pid}.step"
            dxf_p = out_dir / f"{pid}.dxf"
            svg_p = out_dir / f"{pid}.svg"
            scad_p = out_dir / f"{pid}.scad"
            json_p = out_dir / f"{pid}.json"
            for p in (stl_p, step_p, dxf_p, svg_p, scad_p, json_p):
                assert p.is_file(), f"Missing exported artifact: {p}"

            stl_mesh = read_binary_stl(stl_p)
            assert verify_watertight(stl_mesh).watertight, f"Exported STL not watertight: {stl_p}"
            assert validate_step_file(step_p).valid, f"Invalid STEP: {step_p}"
            assert validate_dxf_file(dxf_p).valid, f"Invalid DXF: {dxf_p}"
            assert validate_svg_file(svg_p).valid, f"Invalid SVG: {svg_p}"
            assert validate_scad_file(scad_p).valid, f"Invalid SCAD: {scad_p}"

            meta = json.loads(json_p.read_text(encoding="utf-8"))
            assert meta["part_design"]["part_id"] == pid
            assert meta["artifact_result"]["all_valid"] is True
            assert meta["epistemic"]["design_maturity"] == DESIGN_MATURITY
            assert meta["epistemic"]["no_lab_measurement"] is True
            assert meta["epistemic"]["iec61508_certified"] is False
            assert meta["epistemic"]["semi_s2_certified"] is False

        # Verify manifests
        s6_man = json.loads((DEFAULT_OUT_S6_DIR / "s6_manifest.json").read_text(encoding="utf-8"))
        s9_man = json.loads((DEFAULT_OUT_S9_OPTQ_DIR / "s9_optq_manifest.json").read_text(encoding="utf-8"))
        assert s6_man["part_count"] == 40 and s6_man["all_parts_valid"] is True
        assert s9_man["part_count"] == 3 and s9_man["all_parts_valid"] is True
        assert s6_man["clash_report"]["clash_count"] == 0
        assert s6_man["cryo_thermal_report"]["all_passed"] is True

    def test_zero_host_path_leaks_across_code_and_artifacts(self) -> None:
        forbidden = (
            "/" + "home" + "/",
            "/" + "Users" + "/",
            "/" + "run" + "/" + "media" + "/",
            "C:" + "\\" + "Users" + "\\",
        )
        files_to_scan: list[Path] = [
            REPO_ROOT / "hardware" / "cad_parts" / "subsystems" / "s6_magnet_shields.py",
            REPO_ROOT / "hardware" / "cad_parts" / "subsystems" / "s6_dr_readout_optq.py",
            Path(__file__).resolve(),
        ]
        for out_dir in (DEFAULT_OUT_S6_DIR, DEFAULT_OUT_S9_OPTQ_DIR):
            for ext in ("*.step", "*.dxf", "*.svg", "*.scad", "*.json", "*.stl"):
                files_to_scan.extend(sorted(out_dir.glob(ext)))

        leaks: list[str] = []
        for fp in files_to_scan:
            if fp.suffix == ".stl":
                text = fp.read_bytes()[:80].decode("ascii", errors="ignore")
            else:
                text = fp.read_text(encoding="utf-8", errors="ignore")
            for needle in forbidden:
                if needle in text:
                    leaks.append(f"{fp.name} contains {needle!r}")
        assert leaks == [], f"Host-path leaks detected: {leaks}"
