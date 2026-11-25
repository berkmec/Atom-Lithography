"""Verification suite for S5 UHV Chamber, Pumps, Flash/808 nm Optics & 28Si MBE CAD (WP-M3).

Verifies all 23/23 physical parts of S5 (S5.1-01..S5.6-04, excluding non-solid S5.4-02):
1. Exact 23/23 BOM coverage, disjoint module split (11 + 12), zero bom_id aliasing,
   and locked epistemic metadata (M0_M1_DETAILED_CAD_DESIGN_ONLY, no_lab_measurement=True,
   iec61508_certified=False, semi_s2_certified=False).
2. 100% watertightness (0 boundary edges, 0 non-manifold edges, 0 orientation errors,
   positive volume) in memory and round-tripped from binary STL on disk.
3. All 5 manufacturing formats (.stl, .step, .dxf, .svg, .scad) + per-part .json +
   S5_manifest.json exist in hardware/cad_parts/out/S5/ and pass strict kernel validators.
4. Zero intra-subsystem 3D solid-solid clashes across all 253 part pairs AND zero internal
   shell intersections across S5.1-01's 16 welded ISO 3669 CF flanges.
5. Exact coaxial mating alignment across all 15 internal S5 flange/optical interfaces.
6. Explicit BOM-vs-CAD reconciliations (S5.1-01 r=175 vs 182 mm; S5.1-04 500 mm vs 200 mm
   stub; S5.4-01 Dia 100 stock vs Dia 50 working wafer), S7.SAFETY-02 +Y shroud keepout
   clearance, Exp139 S5.6 envelope/mass, and NIST thermal/GD&T stackup PASS.
7. Zero hardcoded host-path leaks across source files and all 139 exported artifacts.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from hardware.cad_parts.core import (
    DESIGN_MATURITY,
    REPO_ROOT,
    list_physical_part_ids,
    read_binary_stl,
    split_shells,
    transform_mesh,
    validate_dxf_file,
    validate_scad_file,
    validate_step_file,
    validate_svg_file,
    verify_watertight,
)
from hardware.cad_parts.core.feature_engine import _euler_xyz_matrix
from hardware.cad_parts.subsystems.s5_optics_mbe import (
    S5_OPTICS_MBE_PART_IDS,
    build_s5_optics_mbe_parts,
    build_s5_parts as build_s5_parts_from_optics,
    export_all as export_all_from_optics,
)
from hardware.cad_parts.subsystems.s5_uhv_pumps import (
    DEFAULT_S5_OUT_DIR,
    S5_RECONCILIATIONS,
    S5_UHV_PUMPS_PART_IDS,
    Z_WAFER_MM,
    _shells_intersect,
    build_s5_parts,
    build_s5_uhv_pumps_parts,
    check_s5_intra_clashes,
    compute_s5_thermal_and_stackup_audits,
    export_all,
)

EXPECTED_S5_IDS = list_physical_part_ids("S5")
S5_OUT_DIR = DEFAULT_S5_OUT_DIR


@pytest.fixture(scope="module")
def s5_parts():
    return build_s5_parts()


@pytest.fixture(scope="module")
def s5_manifest():
    manifest_path = S5_OUT_DIR / "S5_manifest.json"
    if not manifest_path.is_file():
        return export_all(S5_OUT_DIR)
    return json.loads(manifest_path.read_text(encoding="utf-8"))


# ===========================================================================
# 1. Coverage, Disjoint Split & Epistemic Contract
# ===========================================================================
class TestS5CoverageAndSchema:
    def test_exact_23_physical_parts_and_disjoint_split(self, s5_parts) -> None:
        assert len(EXPECTED_S5_IDS) == 23
        assert "S5.4-02" not in EXPECTED_S5_IDS  # SIMS/AFM external service is non-solid
        assert len(S5_UHV_PUMPS_PART_IDS) == 11
        assert len(S5_OPTICS_MBE_PART_IDS) == 12
        assert set(S5_UHV_PUMPS_PART_IDS).isdisjoint(set(S5_OPTICS_MBE_PART_IDS))
        assert set(S5_UHV_PUMPS_PART_IDS) | set(S5_OPTICS_MBE_PART_IDS) == set(EXPECTED_S5_IDS)
        assert list(s5_parts.keys()) == EXPECTED_S5_IDS
        assert set(build_s5_uhv_pumps_parts().keys()) == set(S5_UHV_PUMPS_PART_IDS)
        assert set(build_s5_optics_mbe_parts().keys()) == set(S5_OPTICS_MBE_PART_IDS)
        # Re-exported entry points match identically
        assert build_s5_parts_from_optics is build_s5_parts
        assert export_all_from_optics is export_all

    def test_epistemic_metadata_and_no_aliasing(self, s5_parts) -> None:
        for pid, build in s5_parts.items():
            d = build.design
            assert d.part_id == pid
            assert "-" in d.part_id
            assert d.subsystem == "S5"
            assert d.design_maturity == DESIGN_MATURITY
            assert d.no_lab_measurement is True
            assert d.iec61508_certified is False
            assert d.semi_s2_certified is False
            assert len(d.ports) >= 1, f"{pid} missing PortInterface schedule"
            assert len(d.dimensions) >= 2, f"{pid} missing DimensionCallouts"
            assert len(d.gdt_frames) >= 1, f"{pid} missing GDTFrame"


# ===========================================================================
# 2. 100% Watertightness & Valid 5-Format Artifacts on Disk
# ===========================================================================
class TestS5ArtifactsAndWatertightness:
    @pytest.mark.parametrize("part_id", EXPECTED_S5_IDS)
    def test_part_watertight_and_all_6_files_valid(self, s5_parts, part_id: str) -> None:
        build = s5_parts[part_id]
        val = verify_watertight(build.mesh)
        assert val.watertight, f"{part_id} mesh not watertight: {val.errors}"
        assert val.boundary_edges == 0
        assert val.non_manifold_edges == 0
        assert val.orientation_errors == 0
        assert val.degenerate_faces == 0
        assert val.signed_volume_mm3 > 0.0

        # Verify all 6 exported artifacts exist on disk
        stl_p = S5_OUT_DIR / f"{part_id}.stl"
        step_p = S5_OUT_DIR / f"{part_id}.step"
        dxf_p = S5_OUT_DIR / f"{part_id}.dxf"
        svg_p = S5_OUT_DIR / f"{part_id}.svg"
        scad_p = S5_OUT_DIR / f"{part_id}.scad"
        json_p = S5_OUT_DIR / f"{part_id}.json"
        for fp in (stl_p, step_p, dxf_p, svg_p, scad_p, json_p):
            assert fp.is_file() and fp.stat().st_size > 0, f"Missing/empty artifact: {fp.name}"

        # Binary STL round-trip watertightness check
        stl_mesh = read_binary_stl(stl_p)
        assert stl_mesh.n_faces == build.mesh.n_faces
        stl_val = verify_watertight(stl_mesh)
        assert stl_val.watertight, f"{part_id} disk STL failed watertight: {stl_val.errors}"

        # Strict kernel validators for STEP, DXF, SVG, SCAD
        step_v = validate_step_file(step_p)
        assert step_v.valid, f"{part_id} STEP invalid: {step_v.errors}"
        assert step_v.has_ap214_schema and len(step_v.dangling_refs) == 0

        dxf_v = validate_dxf_file(dxf_p)
        assert dxf_v.valid, f"{part_id} DXF invalid: {dxf_v.errors}"

        svg_v = validate_svg_file(svg_p)
        assert svg_v.valid, f"{part_id} SVG invalid: {svg_v.errors}"

        scad_v = validate_scad_file(scad_p)
        assert scad_v.valid, f"{part_id} SCAD invalid: {scad_v.errors}"

        # Per-part JSON manifest checks
        meta = json.loads(json_p.read_text(encoding="utf-8"))
        assert meta["part_id"] == part_id
        assert meta["artifacts"]["all_valid"] is True
        assert meta["artifacts"]["watertight"] is True
        assert meta["artifacts"]["mass_kg"] > 0.0
        assert meta["epistemic"]["no_lab_measurement"] is True
        assert meta["epistemic"]["iec61508_certified"] is False
        assert meta["epistemic"]["semi_s2_certified"] is False

    def test_summary_manifest_totals(self, s5_manifest) -> None:
        assert s5_manifest["subsystem"] == "S5"
        assert s5_manifest["physical_part_count"] == 23
        assert s5_manifest["excluded_non_solid_part_ids"] == ["S5.4-02"]
        assert s5_manifest["all_watertight"] is True
        assert s5_manifest["all_artifacts_valid"] is True
        assert s5_manifest["intra_subsystem_clash_audit"]["solid_clashes"] == 0
        assert 200.0 < s5_manifest["total_mass_kg"] < 380.0
        assert s5_manifest["total_triangles"] > 50_000


# ===========================================================================
# 3. Zero Intra-Subsystem Clashes & Coaxial Flange Mating
# ===========================================================================
class TestS5ClashesAndCoaxiality:
    def test_zero_intra_subsystem_solid_clashes(self, s5_parts) -> None:
        report = check_s5_intra_clashes(s5_parts)
        assert report["parts_checked"] == 23
        assert report["pairs_checked"] == 253
        assert report["solid_clashes"] == 0, f"Detected S5 clashes: {report['clashes']}"
        assert report["passed"] is True

    def test_chamber_s5_1_01_zero_internal_port_intersections(self, s5_parts) -> None:
        shells = split_shells(s5_parts["S5.1-01"].mesh)
        assert len(shells) >= 20  # Baseplate + wall + 7 pillars + dome + 16 CF flanges
        hits = []
        for i in range(len(shells)):
            for j in range(i + 1, len(shells)):
                if _shells_intersect(shells[i], shells[j]):
                    hits.append((i, j))
        assert hits == [], f"S5.1-01 internal shell intersections: {hits}"

    def test_all_15_mating_interfaces_coaxial(self, s5_parts) -> None:
        mating_pairs = [
            ("S5.1-01", "top_cf250_column", "S5.1-02", "chamber_top_cf250_mate"),
            ("S5.1-01", "port_loadlock_pos_x", "S5.1-03", "main_chamber_gate_in"),
            ("S5.1-03", "transfer_arm_pos_x", "S5.1-04", "loadlock_cf100_mate"),
            ("S5.1-01", "port_pump_neg_y", "S5.2-01", "chamber_cf100_inlet"),
            ("S5.2-01", "vacion_top_tee_port", "S5.2-02", "tee_cf100_inlet"),
            ("S5.1-01", "port_gauge_rga_225", "S5.2-04", "chamber_cf40_mate"),
            ("S5.1-01", "port_rta_flash_140", "S5.3-02", "chamber_cf100_mate"),
            ("S5.3-02", "lamp_head_mount", "S5.3-01", "optical_exit_aperture"),
            ("S5.1-01", "port_pyro_325", "S5.3-03", "chamber_cf40_mate"),
            ("S5.1-01", "port_shutter_212", "S5.3-04", "chamber_cf40_mate"),
            ("S5.1-01", "port_808nm_flash_pos_y", "S5.5-02", "chamber_pos_y_cf63"),
            ("S5.1-03", "mbe_top_cf100", "S5.6-01", "loadlock_cf100_base"),
            ("S5.6-01", "qcm_neg_y_cf40", "S5.6-02", "mbe_qcm_cf40_mate"),
            ("S5.6-01", "pbn_pos_y_cf40", "S5.6-03", "mbe_pbn_cf40_mate"),
            ("S5.6-01", "mbe_tmp_pos_x_cf63", "S5.6-04", "mbe_cf63_inlet"),
        ]

        def world_port(pid: str, pname: str):
            d = s5_parts[pid].design
            port = next(x for x in d.ports if x.name == pname)
            rmat = _euler_xyz_matrix(*d.world_rotation_deg)
            pos = rmat @ np.array(port.position_mm, dtype=np.float64) + np.array(d.world_origin_mm, dtype=np.float64)
            nrm = rmat @ np.array(port.normal, dtype=np.float64)
            return pos, nrm, port

        for pa, na, pb, nb in mating_pairs:
            pos_a, nrm_a, port_a = world_port(pa, na)
            pos_b, nrm_b, port_b = world_port(pb, nb)
            if port_a.kind == "flange":
                assert port_a.standard == port_b.standard, f"Flange mismatch {pa}:{na} vs {pb}:{nb}"
            dot = float(np.dot(nrm_a, nrm_b))
            diff = pos_b - pos_a
            axial_gap = float(np.dot(diff, nrm_a))
            lateral_err = float(np.linalg.norm(diff - axial_gap * nrm_a))
            assert dot < -0.9999, f"Non-opposing normals {pa}:{na} <-> {pb}:{nb}: dot={dot}"
            assert 0.40 <= axial_gap <= 1.20, f"Unexpected mating gap {pa}:{na} <-> {pb}:{nb}: {axial_gap:.3f} mm"
            assert lateral_err < 0.01, f"Lateral offset {pa}:{na} <-> {pb}:{nb}: {lateral_err:.4f} mm"


# ===========================================================================
# 4. Reconciliations, S7.SAFETY-02 Keepout, Exp139 MBE & Thermal Stackups
# ===========================================================================
class TestS5EngineeringSpecifications:
    def test_bom_vs_cad_reconciliations_documented_and_enforced(self, s5_parts) -> None:
        assert set(S5_RECONCILIATIONS.keys()) == {"S5.1-01", "S5.1-04", "S5.4-01"}

        # S5.1-01: R_in=182, R_out=192, 16 CF flanges
        c_design = s5_parts["S5.1-01"].design
        assert len(c_design.ports) == 16
        assert any("182.0" in n and "175" in n for n in c_design.notes)

        # S5.1-04: True 500 mm stroke (overall length >= 620 mm, clears Rack Bay 1 at X=1400)
        arm = s5_parts["S5.1-04"]
        arm_w = transform_mesh(arm.mesh, translation=arm.design.world_origin_mm, rotation_deg=arm.design.world_rotation_deg)
        amn, amx = arm_w.bbox()
        assert (amx[0] - amn[0]) >= 620.0, f"Transfer arm too short for 500 mm stroke: {amx[0]-amn[0]:.1f} mm"
        assert amx[0] < 1200.0, f"Transfer arm encroaches on Rack Bay 1 (X=1400): X_max={amx[0]:.1f} mm"
        assert any("500" in n and "200 mm" in n for n in arm.design.notes)

        # S5.4-01: Dia 50.0 mm working wafer seated in Load-Lock at (420.0, 0.0, Z=[499.225, 500.000]) under S5.6-01 MBE capper
        waf = s5_parts["S5.4-01"]
        waf_w = transform_mesh(waf.mesh, translation=waf.design.world_origin_mm, rotation_deg=waf.design.world_rotation_deg)
        wmn, wmx = waf_w.bbox()
        assert math.isclose(0.5 * (wmn[0] + wmx[0]), 420.0, abs_tol=0.5)
        assert math.isclose(0.5 * (wmn[1] + wmx[1]), 0.0, abs_tol=1.0)
        assert math.isclose(wmn[2], 499.225, abs_tol=0.01)
        assert math.isclose(wmx[2], Z_WAFER_MM, abs_tol=0.01)
        assert 48.5 <= (wmx[0] - wmn[0]) <= 50.1
        assert any("100 mm" in n and "50.0 mm" in n for n in waf.design.notes)

    def test_s7_safety_02_plus_y_shroud_fit_and_keepout(self, s5_parts, s5_manifest) -> None:
        # S5.5 external envelope beyond CF63 flange fits cleanly inside 280x260x220 mm shroud
        fit = s5_manifest["s7_safety_02_shroud_fit"]
        assert fit["fits_inside_shroud_with_margin"] is True
        ext = fit["s55_external_extents_mm"]
        assert ext[0] < 200.0 and ext[1] < 200.0 and ext[2] < 180.0

        # S5.5-02 CF63 sapphire viewport exact specs
        vp_d = s5_parts["S5.5-02"].design
        cf63_port = next(p for p in vp_d.ports if p.standard == "CF63")
        assert cf63_port.bolt_count == 8
        assert math.isclose(cf63_port.pcd_mm, 92.1, abs_tol=0.05)
        assert math.isclose(cf63_port.bore_mm, 44.0, abs_tol=0.05)

        # Verify NO non-S5.5 part intrudes into S7.SAFETY-02 shroud zone (X=[-140,140], Y=[340,600], Z=[390,610])
        shroud_min = np.array([-140.0, 340.0, 390.0])
        shroud_max = np.array([140.0, 600.0, 610.0])
        for pid, build in s5_parts.items():
            if pid.startswith("S5.5-"):
                continue
            wm = transform_mesh(build.mesh, translation=build.design.world_origin_mm, rotation_deg=build.design.world_rotation_deg)
            mn, mx = wm.vertices.min(axis=0), wm.vertices.max(axis=0)
            overlaps = bool(np.all(mx >= shroud_min) and np.all(mn <= shroud_max))
            assert not overlaps, f"Non-S5.5 part {pid} encroaches into S7.SAFETY-02 +Y shroud zone!"

    def test_exp139_s56_mbe_envelope_and_mass(self, s5_parts, s5_manifest) -> None:
        mbe = s5_parts["S5.6-01"]
        mbe_w = transform_mesh(mbe.mesh, translation=mbe.design.world_origin_mm, rotation_deg=mbe.design.world_rotation_deg)
        mn, mx = mbe_w.bbox()
        assert math.isclose(mn[2], 585.5, abs_tol=0.2)
        assert math.isclose(mx[2], 865.0, abs_tol=0.5)
        s56_mass = sum(s5_manifest["parts"][f"S5.6-0{i}"]["mass_kg"] for i in range(1, 5))
        assert 17.5 <= s56_mass <= 25.0, f"S5.6 combined mass out of Exp139 band: {s56_mass:.2f} kg"

    def test_thermal_and_tolerance_audits_pass(self) -> None:
        aud = compute_s5_thermal_and_stackup_audits()
        assert aud["bakeout_clearance_pass"] is True
        assert aud["jacket_radial_clearance_423K_mm"] >= 2.0
        assert aud["magnet_former_cold_clearance"]["passed"] is True
        assert aud["flash_808nm_optical_stackup"]["wc_pass"] is True
        assert aud["flash_808nm_optical_stackup"]["rss_pass"] is True
        assert aud["loadlock_transfer_stackup"]["wc_pass"] is True
        assert aud["loadlock_transfer_stackup"]["rss_pass"] is True


# ===========================================================================
# 5. Zero Host-Path Leaks & Clean Deterministic Export Check
# ===========================================================================
class TestS5PortabilityAndExport:
    def test_zero_host_path_leaks(self) -> None:
        forbidden = ("/" + "home/", "/" + "Users/", "/" + "run/media/", "C:" + "\\")
        files_to_scan: list[Path] = [
            REPO_ROOT / "hardware" / "cad_parts" / "subsystems" / "s5_uhv_pumps.py",
            REPO_ROOT / "hardware" / "cad_parts" / "subsystems" / "s5_optics_mbe.py",
            Path(__file__).resolve(),
        ]
        for fp in sorted(S5_OUT_DIR.iterdir()):
            if fp.is_file() and fp.suffix.lower() in {".step", ".dxf", ".svg", ".scad", ".json"}:
                files_to_scan.append(fp)

        leaks: list[str] = []
        for fp in files_to_scan:
            text = fp.read_text(encoding="utf-8", errors="ignore")
            for tok in forbidden:
                if tok in text:
                    leaks.append(f"{fp.name} contains {tok!r}")
        assert leaks == [], f"Host-path leaks detected: {leaks}"

    def test_export_all_to_temp_dir(self, tmp_path: Path) -> None:
        res = export_all(tmp_path / "S5_tmp")
        assert res["physical_part_count"] == 23
        assert res["all_watertight"] is True
        assert res["all_artifacts_valid"] is True
        assert res["intra_subsystem_clash_audit"]["solid_clashes"] == 0
        # 23 parts x 6 files + 1 S5_manifest.json = 139 files
        assert len(list((tmp_path / "S5_tmp").iterdir())) == 139
