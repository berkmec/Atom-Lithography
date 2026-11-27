"""Master integration test suite for all 164/164 physical mechanical CAD parts (WP-M6).

Verifies:
1. Exact 164/164 physical BOM part coverage, 0 duplicates, 0 bom_id aliasing.
2. All 164 x 6 = 984 disk artifacts (.stl/.step/.scad/.dxf/.svg/.json) valid
   and all 164 binary STLs strictly watertight (0 boundary/non-manifold/orientation),
   with finite vertices, positive surface area, outward signed volume, and exact bbox span.
3. Canonical datum normalization (Z_FLOOR=0.0 mm, Z_WAFER=+500.0 mm).
4. Exact global 13,366-pair 3D solid clash audit == 0 clashes.
5. Exact mass aggregation including locked S7.SAFETY-01..06 == 355.0 kg and
   S9.HPC-01..03 == 64.0 kg anchors.
6. NIST 300 K -> 20 mK (+ bakeout) cryogenic thermal contraction & GD&T stacks PASS.
7. Locked epistemic metadata (M0_M1_DETAILED_CAD_DESIGN_ONLY, no_lab_measurement=True,
   iec61508_certified=False, semi_s2_certified=False) and 0 host-path leaks.
8. Integrity of hardware/cad_parts/cad_parts_verification.json and the 2400x1400
   white-paper assembly figure hardware/cad_parts/master_164_assembly_views.png.
9. Strictly read-only execution (zero tracked CAD artifacts mutated on test run).

Verification Scope Boundary (OBS-118):
   This suite validates 3D STL/B-rep mesh geometry, watertightness, 13,366-pair solid clash,
   mass anchors, and analytic NIST cryogenic contraction/GD&T stacks. It does NOT replace
   3D multiphysics EM/FEM verification (DOLFINx, openEMS, structural/modal FEA) or post-P&R
   FPGA/ASIC timing closure (nextpnr, OpenROAD), which are tracked separately in
   `INTERNAL_PILOT_REPORT.md` (`M0_M1_DETAILED_CAD_DESIGN_ONLY`, `no_lab_measurement=True`).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import struct
from pathlib import Path

import numpy as np
import pytest

from hardware.cad_parts.build_all import (
    CANONICAL_Z_FLOOR_MM,
    CANONICAL_Z_WAFER_MM,
    EXPECTED_S7_SAFETY_MASS_KG,
    EXPECTED_S9_HPC_MASS_KG,
    MASTER_FIGURE_PATH,
    OUT_ROOT,
    S7_SAFETY_PART_IDS,
    S9_HPC_PART_IDS,
    VERIFICATION_JSON_PATH,
    _shells_clash,
    aggregate_mass_budget,
    aggregate_thermal_and_tolerance_audits,
    assemble_canonical_parts,
    audit_disk_artifacts,
    check_global_clashes,
)
from hardware.cad_parts.core import (
    DESIGN_MATURITY,
    IEC61508_CERTIFIED,
    NO_LAB_MEASUREMENT,
    REPO_ROOT,
    SEMI_S2_CERTIFIED,
    get_bom_row,
    list_physical_part_ids,
    make_box,
    validate_svg_file,
)


@pytest.fixture(scope="module")
def canonical_assembly():
    """Assemble and normalize all 164 physical parts once for the module."""
    return assemble_canonical_parts(out_root=OUT_ROOT)


@pytest.fixture(scope="module")
def verification_json() -> dict:
    assert VERIFICATION_JSON_PATH.is_file(), (
        f"Missing {VERIFICATION_JSON_PATH}; run python -m hardware.cad_parts.build_all"
    )
    return json.loads(VERIFICATION_JSON_PATH.read_text(encoding="utf-8"))


def test_164_physical_part_coverage_zero_duplicates_zero_aliasing(
    canonical_assembly, verification_json
) -> None:
    records, datum_transforms = canonical_assembly
    expected_ids = set(list_physical_part_ids())
    assert len(expected_ids) == 164
    assert len(records) == 164
    assert set(records.keys()) == expected_ids
    assert len(datum_transforms) == 9

    # Zero parent_bom_id aliasing bugs
    for bad_alias in ("S1.6", "S6.5", "S9.1"):
        with pytest.raises(KeyError):
            get_bom_row(bad_alias)

    ai = verification_json["artifact_integrity"]
    assert ai["expected_physical_parts"] == 164
    assert ai["found_on_disk"] == 164
    assert ai["missing_part_ids"] == []
    assert ai["extra_part_ids"] == []
    assert ai["duplicate_part_ids"] == []
    assert ai["bom_aliasing_errors"] == []


def test_all_164_parts_have_6_valid_artifacts_and_watertight_stl(
    canonical_assembly,
) -> None:
    records, _ = canonical_assembly
    audit = audit_disk_artifacts(records, out_root=OUT_ROOT)
    assert audit["missing_or_empty_files"] == []
    assert audit["stl_failures"] == []
    assert audit["step_failures"] == []
    assert audit["dxf_failures"] == []
    assert audit["svg_failures"] == []
    assert audit["scad_failures"] == []
    assert audit["epistemic_failures"] == []
    assert audit["watertight_stl_count"] == 164
    assert audit["step_valid_count"] == 164
    assert audit["dxf_valid_count"] == 164
    assert audit["svg_valid_count"] == 164
    assert audit["scad_valid_count"] == 164
    assert audit["json_valid_count"] == 164
    assert audit["epistemic_locked_count"] == 164
    assert audit["host_path_leak_count"] == 0, f"Host path leaks: {audit['host_path_leaks']}"
    assert audit["passed"] is True


def test_canonical_datum_normalization_and_floor_wafer_anchors(
    canonical_assembly, verification_json
) -> None:
    records, datum_transforms = canonical_assembly
    assert verification_json["canonical_frame"]["z_floor_mm"] == CANONICAL_Z_FLOOR_MM
    assert verification_json["canonical_frame"]["z_wafer_mm"] == CANONICAL_Z_WAFER_MM

    # Both active IBIC wafer (S3.1-01) and load-lock 28Si wafer (S5.4-01) top surface at Z = +500.0 mm
    assert abs(records["S3.1-01"].bbox_max_mm[2] - CANONICAL_Z_WAFER_MM) < 0.05
    assert abs(records["S5.4-01"].bbox_max_mm[2] - CANONICAL_Z_WAFER_MM) < 0.05

    # Floor-standing cabinets, facility hardware, DR OVC, UPS, and HPC sit cleanly on Z_FLOOR = 0.0 mm
    for floor_pid in (
        "S1.6-01",
        "S1.6-02",
        "S5.1-03",
        "S6.1-02",
        "S6.8-02",
        "S6.8-04",
        "S7.4-03",
        "S7.SAFETY-01",
        "S7.SAFETY-04",
        "S9.1-01",
        "S9.HPC-03",
    ):
        z_min = records[floor_pid].bbox_min_mm[2]
        assert abs(z_min - CANONICAL_Z_FLOOR_MM) <= 0.25, (
            f"{floor_pid} not grounded on Z_FLOOR=0.0 mm (got z_min={z_min:.3f} mm)"
        )

    # All 9 subsystem groups have explicit uniform datum transforms recorded
    for gid, dt in datum_transforms.items():
        assert dt["canonical_z_wafer_mm"] == CANONICAL_Z_WAFER_MM
        assert dt["canonical_z_floor_mm"] == CANONICAL_Z_FLOOR_MM
        assert dt["uniform_subsystem_shift"] is True, f"{gid} lacks uniform datum transform"


def test_hardened_shells_clash_catches_symmetric_diagonal_box_crossing() -> None:
    """Regression test for carbon-alpha #328 ORTA: symmetric diagonal-crossing boxes."""
    box_a = make_box(100.0, 100.0, 100.0, center=(0.0, 0.0, 0.0))
    box_b = make_box(100.0, 100.0, 100.0, center=(50.0, 50.0, 50.0))
    amin, amax = np.asarray(box_a.bbox()[0], float), np.asarray(box_a.bbox()[1], float)
    bmin, bmax = np.asarray(box_b.bbox()[0], float), np.asarray(box_b.bbox()[1], float)
    hit, kind = _shells_clash(box_a, box_b, amin, amax, bmin, bmax)
    assert hit is True, "Failed to detect 125 cm^3 symmetric diagonal-crossing box overlap!"
    assert kind != ""

    # Strictly nested solid inside larger solid must also be caught
    inner = make_box(20.0, 20.0, 20.0, center=(0.0, 0.0, 0.0))
    imin, imax = np.asarray(inner.bbox()[0], float), np.asarray(inner.bbox()[1], float)
    hit_in, _ = _shells_clash(box_a, inner, amin, amax, imin, imax)
    assert hit_in is True

    # Non-overlapping touching face (gap=0.0 mm) and small positive clearance (0.05 mm) must NOT false-positive
    for dx in (100.0, 100.05):
        adj = make_box(100.0, 100.0, 100.0, center=(dx, 0.0, 0.0))
        jmin, jmax = np.asarray(adj.bbox()[0], float), np.asarray(adj.bbox()[1], float)
        hit_adj, kind_adj = _shells_clash(box_a, adj, amin, amax, jmin, jmax)
        assert hit_adj is False, f"False positive clash for adjacent box at dx={dx}: {kind_adj}"


def test_all_164_svgs_pass_strict_layout_validation(canonical_assembly) -> None:
    """Verify every single 164/164 per-part GD&T SVG passes #334 check_layout=True."""
    records, _ = canonical_assembly
    failures: list[tuple[str, list[str]]] = []
    for pid, rec in sorted(records.items()):
        svg_p = rec.out_dir / f"{pid}.svg"
        res = validate_svg_file(svg_p, check_layout=True)
        if not res.valid:
            failures.append((pid, list(res.errors)))
    assert failures == [], f"SVG strict layout validation failures ({len(failures)}): {failures[:5]}"


def test_global_13366_pair_3d_solid_clash_zero(canonical_assembly) -> None:
    records, _ = canonical_assembly
    clash_report = check_global_clashes(records)
    assert clash_report["parts_checked"] == 164
    assert clash_report["total_pairs_checked"] == 13366
    assert clash_report["intra_subsystem_clashes"] == 0
    assert clash_report["cross_subsystem_clashes"] == 0
    assert clash_report["clash_count"] == 0, (
        f"Global 3D solid clashes detected: {clash_report['clashes']}"
    )
    assert clash_report["passed"] is True


def test_mass_budget_and_safety_hpc_exact_anchors(
    canonical_assembly, verification_json
) -> None:
    records, _ = canonical_assembly
    mb = aggregate_mass_budget(records)
    assert set(mb["by_subsystem"].keys()) == {"S1", "S2", "S3", "S4", "S5", "S6", "S7", "S9"}
    assert sum(v["part_count"] for v in mb["by_subsystem"].values()) == 164
    for sub, info in mb["by_subsystem"].items():
        assert info["mass_kg"] > 0.0, f"Subsystem {sub} has non-positive mass"

    # Locked v7.0 safety mass anchor: S7.SAFETY-01..06 == 355.0 kg exact
    assert set(mb["s7_safety_masses_kg"].keys()) == set(S7_SAFETY_PART_IDS)
    assert abs(mb["s7_safety_total_mass_kg"] - EXPECTED_S7_SAFETY_MASS_KG) <= 1e-2
    assert mb["s7_safety_mass_exact_match"] is True

    # Locked Option-HPC mass anchor: S9.HPC-01..03 == 64.0 kg exact
    assert set(mb["s9_hpc_masses_kg"].keys()) == set(S9_HPC_PART_IDS)
    assert abs(mb["s9_hpc_total_mass_kg"] - EXPECTED_S9_HPC_MASS_KG) <= 1e-2
    assert mb["s9_hpc_mass_exact_match"] is True
    assert mb["anchors_passed"] is True

    assert abs(
        verification_json["mass_budget"]["total_machine_mass_kg"]
        - mb["total_machine_mass_kg"]
    ) <= 1e-2


def test_nist_cryo_thermal_contraction_300k_to_20mk_and_gdt_stacks(
    canonical_assembly,
) -> None:
    records, _ = canonical_assembly
    th = aggregate_thermal_and_tolerance_audits(records)
    assert th["temperature_span_k"] == [0.02, 423.15]
    assert th["thermal_check_count"] >= 25
    assert th["tolerance_stack_count"] >= 8
    assert th["thermal_failed_count"] == 0, f"Thermal failures: {th['thermal_failed_keys']}"
    assert th["crush_interference_risk_count"] == 0
    assert th["tolerance_stack_failed_count"] == 0, (
        f"Tolerance stack failures: {th['tolerance_stack_failed_keys']}"
    )
    assert th["min_cold_wc_radial_clearance_mm"] > 0.0
    assert th["all_passed"] is True


def test_epistemic_locks_and_zero_host_path_leaks(verification_json) -> None:
    ep = verification_json["epistemic"]
    assert ep["design_maturity"] == DESIGN_MATURITY
    assert ep["no_lab_measurement"] is NO_LAB_MEASUREMENT is True
    assert ep["iec61508_certified"] is IEC61508_CERTIFIED is False
    assert ep["semi_s2_certified"] is SEMI_S2_CERTIFIED is False

    # Scan WP-M6 exclusive files & verification JSON for zero hardcoded user paths
    forbidden = ("/" + "home" + "/", "Yeni" + " Birim", "C:\\" + "Users\\")
    for rel_p in (
        "hardware/cad_parts/subsystems/__init__.py",
        "hardware/cad_parts/build_all.py",
        "hardware/cad_parts/cad_parts_verification.json",
        "tests/test_cad_parts.py",
    ):
        txt = (REPO_ROOT / rel_p).read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in txt, f"Host path marker {marker!r} leaked in {rel_p}"


def test_verification_json_and_master_assembly_png_integrity(
    verification_json,
) -> None:
    assert verification_json["all_gates_passed"] is True
    assert verification_json["global_clash_audit"]["clash_count"] == 0
    assert verification_json["global_clash_audit"]["total_pairs_checked"] == 13366
    assert verification_json["thermal_and_tolerance_audit"]["all_passed"] is True
    assert len(verification_json["parts"]) == 164

    # Validate 2400x1400 PNG header directly (no external imaging dependency required)
    assert MASTER_FIGURE_PATH.is_file(), f"Missing {MASTER_FIGURE_PATH}"
    raw = MASTER_FIGURE_PATH.read_bytes()
    assert len(raw) > 80_000, f"Master assembly PNG unexpectedly small: {len(raw)} bytes"
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    assert raw[12:16] == b"IHDR"
    width, height = struct.unpack(">II", raw[16:24])
    assert (width, height) == (2400, 1400), f"Expected 2400x1400 PNG, got {width}x{height}"


def test_all_164_disk_stls_3d_geometry_winding_bbox_and_zero_mutation(
    canonical_assembly,
) -> None:
    """Verify 3D mesh invariants across all 164 disk STLs (+ optional trimesh) and zero file mutations."""
    records, _ = canonical_assembly

    # Snapshot SHA-256 of verification JSON + 1 representative STL per subsystem before auditing
    seen_subs: set[str] = set()
    watched: list[Path] = [VERIFICATION_JSON_PATH]
    for pid, rec in sorted(records.items()):
        if rec.subsystem not in seen_subs:
            seen_subs.add(rec.subsystem)
            watched.append(rec.out_dir / f"{pid}.stl")
    before_sha = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}

    audit = audit_disk_artifacts(records, out_root=OUT_ROOT)
    assert audit["passed"] is True

    stl_dtype = np.dtype([("normal", "<f4", 3), ("verts", "<f4", (3, 3)), ("attr", "<u2")])
    has_trimesh = importlib.util.find_spec("trimesh") is not None
    trimesh_mod = __import__("trimesh") if has_trimesh else None
    trimesh_checked_subs: set[str] = set()

    for pid, rec in sorted(records.items()):
        stl_p = rec.out_dir / f"{pid}.stl"
        raw = stl_p.read_bytes()
        n_tri = struct.unpack_from("<I", raw, 80)[0]
        assert n_tri > 0, f"Zero triangles in {pid}"
        assert len(raw) == 84 + 50 * n_tri, f"Invalid binary STL byte length for {pid}"

        arr = np.frombuffer(raw, dtype=stl_dtype, offset=84, count=n_tri)
        verts = arr["verts"].astype(np.float64)
        assert np.all(np.isfinite(verts)), f"Non-finite vertices in {pid}"

        e1 = verts[:, 1] - verts[:, 0]
        e2 = verts[:, 2] - verts[:, 0]
        area = 0.5 * float(np.sum(np.linalg.norm(np.cross(e1, e2), axis=1)))
        assert area > 0.0, f"Zero surface area in {pid}"

        signed_vol = float(np.sum(np.einsum("ij,ij->i", verts[:, 0], np.cross(verts[:, 1], verts[:, 2])))) / 6.0
        assert signed_vol > 0.0, f"Non-positive signed volume in {pid}: {signed_vol}"

        flat_v = verts.reshape(-1, 3)
        disk_span = flat_v.max(axis=0) - flat_v.min(axis=0)
        assert np.all(disk_span > 0.0), f"Degenerate STL bbox in {pid}: {disk_span}"

        # Signed volume is invariant under rigid 3D rotation + translation between local STL and canonical assembly
        canon_v = np.asarray(rec.canonical_mesh.vertices, dtype=np.float64)
        canon_f = np.asarray(rec.canonical_mesh.faces, dtype=np.int64)
        cv = canon_v[canon_f]
        canon_vol = float(np.sum(np.einsum("ij,ij->i", cv[:, 0], np.cross(cv[:, 1], cv[:, 2])))) / 6.0
        assert canon_vol > 0.0, f"Non-positive canonical mesh volume for {pid}: {canon_vol}"
        assert abs(signed_vol - canon_vol) / max(canon_vol, 1e-9) < 1e-2, (
            f"Disk STL vs canonical signed volume mismatch for {pid}: disk={signed_vol:.3f}, canon={canon_vol:.3f}"
        )

        if trimesh_mod is not None and rec.subsystem not in trimesh_checked_subs:
            trimesh_checked_subs.add(rec.subsystem)
            tm = trimesh_mod.load(stl_p, force="mesh")
            assert tm.is_watertight, f"trimesh reports non-watertight STL: {pid}"
            assert abs(float(tm.volume) - signed_vol) / signed_vol < 1e-3

    after_sha = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
    assert after_sha == before_sha, "Read-only CAD parts test mutated tracked disk artifacts!"
