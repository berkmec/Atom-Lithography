"""Master Stage-2 180/180 BOM-to-Artifact Traceability, Hygiene & Epistemic Audit Tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess

from hardware.verify_full_traceability import (
    OPENROAD_MANIFEST_REL,
    PARTS_ICD_DIR_REL,
    REGISTRY_REL,
    REPO_ROOT,
    STAGE2_TEST_FILES,
    V72_TEST_FILES,
    verify_full_traceability,
)


def test_master_180_traceability_gate_all_pass() -> None:
    report = verify_full_traceability(check_gitignore=True)
    assert report["bom_total_rows"] == 180
    assert report["registry_parts_count"] == 180
    assert report["disk_part_icds_count"] == 180
    assert report["unique_registry_paths_checked"] >= 1300
    assert report["missing_in_registry"] == []
    assert report["orphan_in_registry"] == []
    assert report["duplicate_in_registry"] == 0
    assert report["missing_icd_files"] == []
    assert report["orphan_icd_files"] == []
    assert report["broken_links"] == []
    assert report["sha_mismatches"] == []
    assert report["epistemic_violations"] == []
    assert report["cad_ok"] is True
    assert report["pcb_ok"] is True
    assert report["rtl_ok"] is True
    assert report["openroad_ok"] is True
    assert report["gitignored_registry_paths"] == []
    assert report["gitignored_stage2_tests"] == []
    assert report["gitignored_v72_tests"] == []
    assert report["host_path_hits"] == []
    assert report["secret_hits"] == []
    assert report["all_passed"] is True


def test_parts_registry_exact_coverage_counters_and_epistemic_locks() -> None:
    reg = json.loads((REPO_ROOT / REGISTRY_REL).read_text(encoding="utf-8"))
    cs = reg["coverage_summary"]
    assert cs["bom_total_rows"] == 180
    assert cs["unified_part_icds"] == 180
    assert cs["bom_coverage_pct"] == 100.0
    assert cs["by_part_category"] == {
        "PHYSICAL_SOLID": 164,
        "NON_SOLID_PROCESS_SERVICE_GAS": 5,
        "IN_HOUSE_SOFTWARE_RTL_EDA": 9,
        "SUPERSEDED_ZERO_DOLLAR_POINTER": 2,
    }
    assert sum(cs["by_part_category"].values()) == 180
    assert cs["cad_solid_parts"] == 164
    assert cs["cad_global_clashes"] == 0
    assert cs["cad_pairs_checked"] == 13366
    assert cs["cad_thermal_checks_passed"] == 30
    assert cs["cad_gdt_stacks_passed"] == 10
    assert cs["kicad8_boards_count"] == 10
    assert cs["kicad8_total_erc_errors"] == 0
    assert cs["kicad8_total_drc_errors"] == 0
    assert cs["kicad8_total_nets"] == 762
    assert cs["kicad8_total_routed_nets"] == 762
    assert cs["kicad8_total_unrouted_nets"] == 0
    assert cs["kicad8_total_unconnected_items"] == 0
    assert cs["kicad8_total_track_dangling"] == 0
    assert cs["kicad8_total_segments"] == 9895
    assert cs["kicad8_total_vias"] == 2538
    assert cs["kicad8_all_boards_semi_s2_certified_false"] is True
    assert cs["kicad8_all_boards_iec61508_certified_false"] is True
    assert cs["live_ngspice47_decks_count"] == 10
    assert cs["electrical_per_part_icds"] == 95
    assert cs["electrical_union_bom_parts"] == 125
    assert cs["rtl_machine_ctrl_modules"] == 7
    assert cs["rtl_machine_ctrl_loc"] == 3212
    assert cs["rtl_verilator_targets_passed"] == 8
    assert cs["rtl_iverilog_testbenches_passed"] == 6
    assert cs["rtl_yosys_targets_passed"] == 3

    # Verify per-board strict routing & epistemic certification locks across ALL 10 KiCad 8 PCBs
    pcb_anchor = reg["verification_anchors"]["pcb_and_spice"]
    boards = [bd for b in pcb_anchor["bundles"] for bd in b["boards"]]
    assert len(boards) == 10
    for bd in boards:
        assert bd["erc_errors"] == 0, f"ERC errors on {bd['board_name']}"
        assert bd["drc_errors"] == 0, f"DRC errors on {bd['board_name']}"
        assert bd["routed_net_count"] == bd["net_count"], f"Partial routing on {bd['board_name']}"
        assert bd["unrouted_net_count"] == 0, f"Unrouted nets on {bd['board_name']}"
        assert bd["unconnected_items"] == 0, f"Unconnected items on {bd['board_name']}"
        assert bd["track_dangling_count"] == 0, f"Dangling tracks on {bd['board_name']}"
        assert bd["semi_s2_certified"] is False, f"semi_s2_certified not False on {bd['board_name']}"
        assert bd["iec61508_certified"] is False, f"iec61508_certified not False on {bd['board_name']}"

    # Verify conservative UPS runtime breakdown & 0.0 W TIER2_SHED reconciliation
    ups = reg["verification_anchors"]["electrical_power_ups"]
    assert ups["tier1_runtime_min_exp150_nominal_eta090"] == 213.2
    assert ups["tier1_runtime_min_conservative_100pct_dod_incl_350w"] == 189.6
    assert ups["tier1_runtime_min_conservative_90pct_dod_incl_350w"] == 170.6
    assert ups["tier1_conservative_100pct_dod_meets_180min"] is True
    assert ups["tier1_conservative_90pct_dod_meets_180min"] is False
    assert ups["tier2_shed_28part_reconciliation_discrepancy_W"] == 0.0

    # Verify hardened RTL security & BOED 0-LSB gates
    rtl = reg["verification_anchors"]["rtl_machine_ctrl"]
    assert rtl["sw_bypass_rejected"] is True
    assert rtl["cfg_lock_ok"] is True
    assert rtl["boed_0lsb_ok"] is True

    epi = reg["epistemic"]
    assert epi["design_maturity"] == "M0_M1_DESIGN_ONLY"
    assert epi["no_lab_measurement"] is True
    assert epi["no_supplier_quotes"] is True
    assert epi["no_vendor_vivado_pnr"] is True
    assert epi["tapeout_done"] is False
    assert epi["iec61508_certified"] is False
    assert epi["semi_s2_certified"] is False
    assert epi["requires_third_party_safety_assessment"] is True


def test_non_solid_s8_and_superseded_icds_complete() -> None:
    icd_dir = REPO_ROOT / PARTS_ICD_DIR_REL

    # 5 active non-solid NRE / metrology / gas ICDs
    for pid in ("S2.1-02", "S2.2-02", "S2.3-02", "S5.4-02", "S6.8-03"):
        d = json.loads((icd_dir / f"{pid}.json").read_text(encoding="utf-8"))
        assert d["part_category"] == "NON_SOLID_PROCESS_SERVICE_GAS"
        spec = d["specialized_specification"]
        assert spec is not None and spec["mating_physical_part_ids"]
        assert len(spec["reference_artifacts"]) >= 2

    # 9 IN-HOUSE software / RTL / EDA ICDs (S8.1-01..S8.4-02)
    s8_ids = (
        "S8.1-01",
        "S8.1-02",
        "S8.2-01",
        "S8.2-02",
        "S8.3-01",
        "S8.3-02",
        "S8.3-03",
        "S8.4-01",
        "S8.4-02",
    )
    for pid in s8_ids:
        d = json.loads((icd_dir / f"{pid}.json").read_text(encoding="utf-8"))
        assert d["part_category"] == "IN_HOUSE_SOFTWARE_RTL_EDA"
        assert d["artifact_links"]["software_and_eda_files"]
        assert d["artifact_links"]["verification_tests"]

    # Confirm S8.4-02 points to scada_telemetry.py and S8.2-02 points to openroad_signoff_manifest.json
    s842 = json.loads((icd_dir / "S8.4-02.json").read_text(encoding="utf-8"))
    assert "src/machine_control/scada_telemetry.py" in s842["artifact_links"]["software_and_eda_files"]
    s822 = json.loads((icd_dir / "S8.2-02.json").read_text(encoding="utf-8"))
    assert OPENROAD_MANIFEST_REL in s822["artifact_links"]["software_and_eda_files"]

    # 2 $0 superseded pointers
    s610 = json.loads((icd_dir / "S6.10-02.json").read_text(encoding="utf-8"))
    assert s610["part_category"] == "SUPERSEDED_ZERO_DOLLAR_POINTER"
    assert s610["bom_metadata"]["usd_nom"] == 0.0
    assert s610["specialized_specification"]["active_replacement_part_ids"] == [
        "S5.6-01",
        "S5.6-02",
        "S5.6-03",
        "S5.6-04",
    ]

    s714 = json.loads((icd_dir / "S7.1-04.json").read_text(encoding="utf-8"))
    assert s714["part_category"] == "SUPERSEDED_ZERO_DOLLAR_POINTER"
    assert s714["bom_metadata"]["usd_nom"] == 0.0
    assert s714["specialized_specification"]["active_replacement_part_ids"] == ["S6.11-01"]


def test_openroad_signoff_manifest_and_summary_doc() -> None:
    manifest = json.loads((REPO_ROOT / OPENROAD_MANIFEST_REL).read_text(encoding="utf-8"))
    assert manifest["bom_part_id"] == "S8.2-02"
    assert manifest["design_top"] == "blanker_tile"
    assert manifest["epistemic"]["tapeout_done"] is False
    assert manifest["epistemic"]["no_lab_measurement"] is True
    assert manifest["epistemic"]["iec61508_certified"] is False
    assert manifest["epistemic"]["semi_s2_certified"] is False

    # Every whitelisted RTL file in manifest must exist on disk with exact matching SHA-256
    for src in manifest["whitelisted_rtl_sources"]:
        fp = REPO_ROOT / src["path"]
        assert fp.exists(), f"Missing {src['path']}"
        digest = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert digest == src["sha256"], f"SHA mismatch on {src['path']}"

    # Summary doc check
    summary_md = (REPO_ROOT / "hardware" / "DESIGN_BLUEPRINT_180_SUMMARY.md").read_text(encoding="utf-8")
    assert "180 / 180" in summary_md or "180/180" in summary_md
    assert "762 / 762" in summary_md or "762/762" in summary_md
    assert "170.6 min" in summary_md
    assert "no_lab_measurement = true" in summary_md
    assert "iec61508_certified = false" in summary_md
    assert "semi_s2_certified = false" in summary_md
    assert "tapeout_done = false" in summary_md


def test_gitignore_whitelisting_and_zero_junk_or_username_exposure() -> None:
    # Verify all 14 Stage-2 test files and 35 v7.2 test files exist and are NOT ignored
    all_tests = list(STAGE2_TEST_FILES) + list(V72_TEST_FILES)
    assert len(STAGE2_TEST_FILES) == 14
    assert len(V72_TEST_FILES) == 35
    for tf in all_tests:
        assert (REPO_ROOT / tf).exists(), f"Missing test file: {tf}"

    proc = subprocess.run(
        ["git", "check-ignore", "--stdin"],
        cwd=REPO_ROOT,
        input="\n".join(all_tests) + "\n",
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.stdout.strip() == "", f"Test files ignored by .gitignore: {proc.stdout}"

    # Verify ZERO tracked v7.2 files (including all 39 Exp151 locked artifacts) match .gitignore
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()
    proc_tracked = subprocess.run(
        ["git", "check-ignore", "--no-index", "--stdin"],
        cwd=REPO_ROOT,
        input="\n".join(tracked) + "\n",
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc_tracked.stdout.strip() == "", (
        f"Tracked v7.2 files ignored by .gitignore: {proc_tracked.stdout[:400]}"
    )

    # Verify git status exposes ZERO __pycache__, .pyc, .vvp, .vcd, or .log artifacts
    st = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    bad_exposed: list[str] = []
    modified_tracked: list[str] = []
    for line in st.stdout.splitlines():
        if not line.strip():
            continue
        code = line[:2]
        path = line[3:].strip()
        if (
            "__pycache__" in path
            or path.endswith((".pyc", ".pyo", ".vvp", ".vcd", ".log"))
        ):
            bad_exposed.append(path)
        if code != "??":
            modified_tracked.append(f"{code} {path}")

    assert bad_exposed == [], f"Junk/cache/log files exposed by .gitignore: {bad_exposed[:10]}"
    # Only .gitignore is allowed to be modified among pre-existing tracked v7.2 files
    assert all(m.endswith(" .gitignore") for m in modified_tracked), (
        f"Unexpected modification to tracked v7.2 files: {modified_tracked}"
    )

    # Verify zero personal username literal in any Stage-2 file or test
    active_user = Path.home().name
    if active_user and len(active_user) >= 3 and active_user not in {"root", "user", "admin", "runner"}:
        user_pat = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(active_user)}(?![A-Za-z0-9_])", re.IGNORECASE)
        for root in ("hardware", "rtl/machine_ctrl", "results/stage2_rtl_verification", "src/machine_control/scada_telemetry.py", *STAGE2_TEST_FILES):
            rp = REPO_ROOT / root
            files = [rp] if rp.is_file() else [
                p for p in rp.rglob("*")
                if p.is_file() and "__pycache__" not in p.parts and p.suffix.lower() not in {".stl", ".png", ".pyc"}
            ]
            for fp in files:
                txt = fp.read_text(encoding="utf-8", errors="ignore")
                assert not user_pat.search(txt), f"Personal username literal leaked in {fp.relative_to(REPO_ROOT)}"
