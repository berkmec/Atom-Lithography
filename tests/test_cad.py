"""Automated verification suite for Atom Lithography Machine CAD v6.0 (S1–S7 + Option-Q/HPC).

Verifies:
1. `params.py` v6.0 synchronization (no legacy maglev, golden s=0.5, Exp124..143 locked).
2. All 8 parametric `.scad` files exist and match `gen_scad.py` deterministically.
3. All 8 binary `.stl` files parse cleanly from disk, are strictly watertight
   (0 boundary edges, 0 non-manifold edges), and have strictly positive volume.
4. Zero solid-solid clashes across all part pairs and 100% pass on 40/40 critical clearances.
5. `cad_verification.json` consistency + Exp80/84/124..143 compliance (exact 1,108.14 kg).
6. All 10 ISO/ANSI technical drawings (.svg + .png >= 1800x1200), `preview_machine.png`,
   and preserved historical v3/v4/v5 overview dashboards.
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CAD_DIR = ROOT / "research" / "atom_lithography_machine" / "cad"
sys.path.insert(0, str(CAD_DIR))

import gen_scad  # noqa: E402
import mesh_engine  # noqa: E402
import params  # noqa: E402

EXPECTED_SUBSYSTEMS = [
    "s1_ion_source_column",
    "s2_mems_write_head",
    "s3_ibic_detector_assembly",
    "s4_piezo_stage_interferometry",
    "s5_uhv_chamber_loadlock",
    "s6_cryo_dr_magnet_readout",
    "s7_electronics_rack_interconnect",
]

EXPECTED_DRAWINGS = [
    "01_s1_ion_source_column",
    "02_s2_mems_write_head",
    "03_s3_ibic_detector_assembly",
    "04_s4_piezo_stage_interferometry",
    "05_s5_uhv_chamber_loadlock",
    "06_s6_cryo_dr_magnet_readout",
    "07_s7_electronics_rack_interconnect",
    "08_atom_litho_assembly",
    "09_atom_litho_cutaway",
    "10_atom_litho_exploded",
]


def _read_png_dimensions(path: Path) -> tuple[int, int]:
    raw = path.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n", f"Not a valid PNG signature: {path.name}"
    assert raw[12:16] == b"IHDR", f"Missing IHDR chunk: {path.name}"
    w, h = struct.unpack(">II", raw[16:24])
    return int(w), int(h)


def test_params_v3_sync_and_no_legacy_maglev():
    assert params.GOLDEN_SCALE_S == pytest.approx(0.5)
    assert params.NO_LAB_MEASUREMENT is True
    assert list(params.SUBSYSTEMS.keys()) == EXPECTED_SUBSYSTEMS
    assert not any("maglev" in k.lower() for k in params.PARTS), "Legacy maglev part still present!"
    for req_key in (
        "s1_duoplasmatron", "s1_condenser_lens", "s1_wien_filter", "s1_energy_filter", "s1_transfer_lens",
        "s2_aperture_plate", "s2_blanker_plate", "s2_mini_lens_plate", "s2_tile_carrier",
        "s3_ibic_contact_ring", "s3_ibic_csa_pos", "s3_wafer_carrier",
        "s4_granite_base", "s4_active_table", "s4_piezo_coarse_xy", "s4_piezo_fine_6dof",
        "s4_metrology_frame", "s4_interferometer_x",
        "s5_chamber_wall_upper", "s5_loadlock_chamber", "s5_turbo_pump", "s5_flash_anneal_head",
        "s6_coil_m_upper", "s6_coil_m_lower", "s6_coil_s_upper", "s6_coil_s_lower",
        "s6_coil_a_upper", "s6_coil_a_lower", "s6_coil_b_upper", "s6_coil_b_lower",
        "s6_meissner_cup_wall", "s6_meissner_chimney", "s6_cryoperm_sleeve",
        "s6_nbtin_resonator_carrier", "s6_dr_flange_50k", "s6_dr_flange_4k",
        "s6_dr_flange_still", "s6_dr_flange_cp", "s6_dr_flange_mxc", "s6_pt420_coldhead",
        "s6_hemt_rack_4k", "s7_host_gpu_server", "s7_awg_rf_mw_bay", "s7_fpga_blanker_bay",
    ):
        assert req_key in params.PARTS, f"Missing required CAD part: {req_key}"
    assert params.DESIGN_SPECS["exp124_synced"] is True
    assert params.DESIGN_SPECS["exp125_synced"] is True
    assert params.DESIGN_SPECS["exp127_synced"] is True
    assert params.DESIGN_SPECS["exp130_synced"] is True
    assert params.DESIGN_SPECS["exp131_synced"] is True
    assert params.DESIGN_SPECS["exp133_synced"] is True
    assert params.DESIGN_SPECS["exp139_synced"] is True
    assert params.DESIGN_SPECS["exp140_synced"] is True
    assert params.DESIGN_SPECS["exp142_synced"] is True
    assert params.DESIGN_SPECS["exp143_synced"] is True
    assert params.CAD_VERSION.startswith("6.0-")
    # CAD v4.0/v5.0/v6.0 required new solid parts
    for v6_key in (
        "s1_multi_species_neck", "s1_multi_species_cartridge",
        "s5_flash_safety_shutter", "s5_flash_anneal_head", "s5_flash_dichroic_pyrometer", "s5_flash_fiber_collimator",
        "s5_mbe_cf100_flange", "s5_mbe_source_body", "s5_mbe_top_feedthrough",
        "s5_mbe_qcm_valve", "s5_mbe_pbn_heater_fg", "s5_mbe_tmp_neg_pump",
        "s6_m4_crossbar_4k_mount", "s6_m4_crossbar_4k_pcb",
        "s6_ovc_bellows_flange_uhv", "s6_ovc_bellows_cf63", "s6_ovc_bellows_flange_dr", "s6_ovc_bridge_dr_stub",
        "s6_mxc_braid_1", "s6_mxc_braid_2", "s6_mxc_braid_3", "s6_mxc_braid_4",
        "s6_pt420_valve_stand", "s6_pt420_remote_valve_box", "s6_pt420_flex_he_bottom",
        "s6_s65_twpa_purcell_pack", "s6_s65_hemt_bank_32ch",
        "s6_s65_coax_loom_300k_50k_pos", "s6_s65_coax_loom_cp_mxc_neg",
        "s6_s91_ovc_feedthrough", "s6_s91_qram_bridge_20mk", "s6_s91_qram_fiber_loom",
        "s7_s65_rfsoc_boed_bay",
        "s7_s9hpc_rail_psu_kit", "s7_s9hpc_decoder_node_1", "s7_s9hpc_decoder_node_2",
        "s7_s9hpc_rocev2_switch", "s7_s9hpc_qsfp28_fiber_duct",
    ):
        assert v6_key in params.PARTS, f"Missing CAD v6.0 part: {v6_key}"
    # Option A co-pitched Arch-B 32x32 @ 0.50 mm = 16.0x16.0 mm (diag 22.627 mm), Ø28.0 mm bore
    assert params.DESIGN_SPECS["beamlet_count"] == 1024
    assert params.DESIGN_SPECS["beamlet_pitch_mm"] == pytest.approx(0.50)
    assert params.DESIGN_SPECS["write_field_mm"] == pytest.approx(16.0)
    assert params.DESIGN_SPECS["blanker_tile_count"] == 16
    assert 2.0 * params.PARTS["s1_transfer_lens"]["dims"][0] == pytest.approx(28.0)
    assert 2.0 * params.PARTS["s2_aperture_plate"]["dims"][0] == pytest.approx(28.0)
    for pname, spec in params.PARTS.items():
        assert spec["material"] in params.MATERIALS, f"Unknown material for {pname}"
        assert params.part_density(spec) > 0.0
        assert spec["tol_mm"] > 0.0


def test_all_8_scad_files_exist_and_sync():
    parts_dir = CAD_DIR / "parts"
    for sub in EXPECTED_SUBSYSTEMS:
        p = parts_dir / f"{sub}.scad"
        assert p.is_file(), f"Missing SCAD file: {p}"
        expected = gen_scad.emit_subsystem_scad(sub)
        assert p.read_text(encoding="utf-8") == expected, f"SCAD out of sync: {p.name}"
    master = CAD_DIR / "atom_litho_machine.scad"
    assert master.is_file()
    assert master.read_text(encoding="utf-8") == gen_scad.emit_master_scad()


@pytest.mark.parametrize("stem", EXPECTED_SUBSYSTEMS + ["atom_litho_machine"])
def test_all_8_stl_files_watertight_and_positive_volume(stem: str):
    stl_path = CAD_DIR / "stl" / f"{stem}.stl"
    assert stl_path.is_file(), f"Missing STL file: {stl_path}"
    info = mesh_engine.inspect_binary_stl(stl_path)
    assert info["triangles"] > 0
    assert info["is_watertight"] is True, f"STL not watertight: {info}"
    assert info["boundary_edges"] == 0
    assert info["non_manifold_edges"] == 0
    assert info["volume_mm3"] > 0.0


def test_zero_solid_clashes_and_all_critical_clearances():
    inter = mesh_engine.check_all_interferences(params.PARTS, margin_mm=0.05)
    assert inter["solid_clashes"] == 0, f"Detected solid clashes: {inter['clashes']}"
    clearances = mesh_engine.compute_critical_clearances(params.PARTS)
    failed = {k: v for k, v in clearances.items() if not v["pass"]}
    assert not failed, f"Failed critical clearances: {failed}"


def test_verification_json_and_exp80_exp84_compliance():
    vpath = CAD_DIR / "cad_verification.json"
    assert vpath.is_file()
    ver = json.loads(vpath.read_text(encoding="utf-8"))
    assert ver["overall_pass"] is True
    assert ver["interference_audit"]["solid_clashes"] == 0
    assert ver["master_assembly"]["part_count"] == len(params.PARTS)
    assert ver["master_assembly"]["stl"]["is_watertight"] is True
    assert 500.0 < ver["master_assembly"]["total_mass_kg"] < 2500.0
    # Exp80 s=0.5 golden envelope compliance
    e80 = ver["exp80_golden_envelope_audit"]
    assert e80["bc1_carrier_ge_25mm"]["pass"] is True
    assert e80["bc1_in_vacuum_bore_gt_carrier_diag"]["pass"] is True
    assert e80["bc4_chamber_volume_one_eighth"]["pass"] is True
    # Exp124 8-stage column & Option-A Ø28 mm bore clearance exact lock
    e124 = ver["exp124_column_audit"]
    assert e124["pass"] is True and e124["exp124_synced"] is True
    assert e124["total_column_height_mm"] == pytest.approx(562.66, abs=0.02)
    assert e124["max_od_mm"] == pytest.approx(110.0, abs=0.02)
    assert e124["wd_mm"] == pytest.approx(0.25, abs=0.01)
    assert e124["stage_mass_kg"] == pytest.approx(25.92, abs=0.02)
    assert e124["s1_6_transfer_bore_mm"] == pytest.approx(28.0, abs=0.01)
    assert e124["s2_1_aperture_bore_mm"] == pytest.approx(28.0, abs=0.01)
    assert e124["beam_array_diagonal_mm"] == pytest.approx(22.627, abs=0.01)
    assert e124["beam_array_diagonal_to_bore_clearance_mm"] == pytest.approx(2.686, abs=0.01)
    clr_beam = ver["critical_clearances"]["beam_array_diagonal_to_bore_clearance_mm"]
    assert clr_beam["pass"] is True and clr_beam["value_mm"] == pytest.approx(2.686, abs=0.01)
    # Exp125 8-coil cryo-magnet & shields exact lock
    e125 = ver["exp125_magnet_audit"]
    assert e125["pass"] is True and e125["exp125_synced"] is True
    assert e125["coil_count"] == 8
    assert e125["clear_bore_mm"] == pytest.approx(150.0, abs=0.02)
    assert e125["midplane_split_gap_mm"] == pytest.approx(36.0, abs=0.02)
    assert e125["former_od_mm"] == pytest.approx(352.0, abs=0.02)
    assert e125["resonator_z_loc_mm"] == pytest.approx(-155.0, abs=0.02)
    assert e125["resonator_od_mm"] == pytest.approx(50.0, abs=0.02)
    assert e125["nb_meissner_r_mm"] == [32.0, 34.5]
    assert e125["cryoperm_r_mm"] == [39.0, 41.0]
    # Exp84 modal compliance
    assert ver["exp84_modal_audit"]["pass"] is True
    assert ver["exp84_modal_audit"]["blanker_f1_fea_hz"] == pytest.approx(2591027.0)
    # CAD v4.0 audits (Exp130 S5.5, Exp131 M4, Exp133 PT420 decoupling)
    e130 = ver["exp130_flash_audit"]
    assert e130["pass"] is True and e130["exp130_synced"] is True
    assert e130["window_ca_mm"] == pytest.approx(44.0, abs=0.05)
    assert e130["homogenizer_dims_mm"] == [84.0, 88.0, 84.0]
    e131 = ver["exp131_m4_audit"]
    assert e131["pass"] is True and e131["exp131_synced"] is True
    assert e131["crossbar_gates_4k"] == 968
    assert e131["epi_cap_nm"] == pytest.approx(8.0)
    assert e131["B_M4_T"] == pytest.approx(0.1785)
    e133 = ver["exp133_decoupling_audit"]
    assert e133["pass"] is True and e133["exp133_synced"] is True
    assert e133["bellows_id_mm"] == pytest.approx(44.0, abs=0.1)
    assert e133["bellows_od_mm"] == pytest.approx(68.0, abs=0.1)
    assert e133["bellows_active_length_mm"] == pytest.approx(120.0, abs=0.2)
    assert e133["braid_count"] == 4
    assert e133["remote_valve_offset_mm"] == pytest.approx(500.0, abs=0.2)
    assert e133["flex_he_length_mm"] == pytest.approx(600.0, abs=0.5)
    assert len(ver["critical_clearances"]) >= 40
    # Legacy cleanup
    assert all(ver["legacy_cleanup"].values())


def test_cad_v5_exp139_s56_mbe_capper_locked():
    ver = json.loads((CAD_DIR / "cad_verification.json").read_text(encoding="utf-8"))
    spec_path = ROOT / "results" / "exp139_epi_cap_process_integration" / "s56_hardware_spec.json"
    assert spec_path.is_file()
    s56_spec = json.loads(spec_path.read_text(encoding="utf-8"))["s56_hardware_spec"]
    e139 = ver["exp139_s56_audit"]
    assert e139["pass"] is True and e139["exp139_synced"] is True
    assert e139["part_count"] == 6
    assert e139["total_mass_kg"] == pytest.approx(s56_spec["mass_power_cryo"]["total_mass_kg"], abs=0.02)
    assert e139["flange_od_mm"] == pytest.approx(s56_spec["cad_v5_geometry"]["flange_od_mm"], abs=0.05)
    assert e139["bore_id_mm"] == pytest.approx(s56_spec["cad_v5_geometry"]["bore_id_mm"], abs=0.05)
    assert e139["z_span_mm"][0] == pytest.approx(585.1, abs=0.15)
    assert e139["z_span_mm"][1] == pytest.approx(865.0, abs=0.1)
    clr = ver["critical_clearances"]
    assert clr["exp139_s56_to_chamber_top_flange_x_mm"]["pass"] is True
    assert clr["exp139_s56_to_chamber_top_flange_x_mm"]["value_mm"] == pytest.approx(119.0, abs=0.2)
    assert clr["exp139_s56_to_transfer_arm_z_mm"]["pass"] is True
    assert clr["exp139_s56_to_transfer_arm_z_mm"]["value_mm"] >= 70.0
    assert clr["exp139_s56_to_s7_panel_x_mm"]["pass"] is True


def test_cad_v5_exp140_s65_cryo_mux_and_rfsoc_locked():
    ver = json.loads((CAD_DIR / "cad_verification.json").read_text(encoding="utf-8"))
    spec_path = ROOT / "results" / "exp140_cryo_fpga_boed_mux_readout" / "s65_hardware_spec.json"
    assert spec_path.is_file()
    s65_spec = json.loads(spec_path.read_text(encoding="utf-8"))
    e140 = ver["exp140_s65_audit"]
    assert e140["pass"] is True and e140["exp140_synced"] is True
    assert e140["module_scale_cells"] == 1024
    assert e140["cold_part_count"] == 12
    assert e140["rack_part_count"] == 1
    assert e140["cold_mass_kg"] == pytest.approx(s65_spec["totals_1024_cell_module"]["cryo_cold_mass_kg"], abs=0.02)
    assert e140["rack_mass_kg"] == pytest.approx(11.50, abs=0.02)
    assert e140["total_mass_kg"] == pytest.approx(s65_spec["totals_1024_cell_module"]["total_mass_kg"], abs=0.02)
    assert e140["twpa_pack_dims_mm"] == [180.0, 140.0, 55.0]
    assert e140["rfsoc_bay_dims_mm"][1:] == [482.6, 88.9]
    clr = ver["critical_clearances"]
    for k in (
        "exp140_s65_twpa_inside_4k_shield_radial_mm",
        "exp140_s65_hemt_to_4k_shield_radial_mm",
        "exp140_s65_coax_loom_to_m4_crossbar_x_mm",
        "exp140_s65_rfsoc_to_awg_z_mm",
    ):
        assert clr[k]["pass"] is True, f"Failed S6.5 clearance {k}: {clr[k]}"


def test_cad_v6_exp142_option_q_locked():
    ver = json.loads((CAD_DIR / "cad_verification.json").read_text(encoding="utf-8"))
    spec_path = ROOT / "results" / "exp142_option_q_multispecies_qram" / "s9q_hardware_spec.json"
    assert spec_path.is_file()
    s9q_spec = json.loads(spec_path.read_text(encoding="utf-8"))["totals_option_q_plus_s1_multi"]
    e142 = ver["exp142_s9q_audit"]
    assert e142["pass"] is True and e142["exp142_synced"] is True
    assert e142["s16_part_count"] == 2
    assert e142["s91_part_count"] == 3
    assert e142["s16_mass_kg"] == pytest.approx(s9q_spec["s16_multispecies_mass_kg"], abs=0.02)
    assert e142["s91_mass_kg"] == pytest.approx(s9q_spec["s91_cryo_qram_mass_kg"], abs=0.02)
    assert e142["total_mass_kg"] == pytest.approx(s9q_spec["total_mass_kg"], abs=0.02)
    assert e142["s16_cartridge_center_mm"] == [0.0, 110.0, 992.66]
    assert e142["s91_chip_dims_mm"] == [60.0, 30.0, 16.0]
    clr = ver["critical_clearances"]
    for k in (
        "exp142_s16_cartridge_to_duoplasmatron_y_mm",
        "exp142_s16_cartridge_to_ph3_manifold_y_mm",
        "exp142_s91_qram_chip_to_s65_twpa_z_mm",
        "exp142_s91_ovc_port_to_valve_stand_x_mm",
        "exp142_s91_fiber_loom_to_4k_50k_shields_mm",
    ):
        assert clr[k]["pass"] is True, f"Failed Option-Q clearance {k}: {clr[k]}"
    assert clr["exp142_s16_cartridge_to_duoplasmatron_y_mm"]["value_mm"] == pytest.approx(27.0, abs=0.1)
    assert clr["exp142_s91_qram_chip_to_s65_twpa_z_mm"]["value_mm"] == pytest.approx(8.5, abs=0.1)


def test_cad_v6_exp143_option_hpc_locked():
    ver = json.loads((CAD_DIR / "cad_verification.json").read_text(encoding="utf-8"))
    spec_path = ROOT / "results" / "exp143_d3_grape_m4_and_hpc_decoder" / "s9hpc_hardware_spec.json"
    assert spec_path.is_file()
    s9hpc_spec = json.loads(spec_path.read_text(encoding="utf-8"))["totals_base_4u_option_hpc_module"]
    e143 = ver["exp143_s9hpc_audit"]
    assert e143["pass"] is True and e143["exp143_synced"] is True
    assert e143["part_count"] == 5
    assert e143["total_mass_kg"] == pytest.approx(s9hpc_spec["total_mass_kg"], abs=0.02)
    assert e143["decoder_nodes_4u_dims_mm"] == [482.6, 780.0, 177.8]
    assert e143["switch_1u_dims_mm"] == [482.6, 380.0, 44.5]
    assert e143["room_temp_power_W"] == pytest.approx(2195.0, abs=0.5)
    assert e143["cryo_load_W"] == pytest.approx(0.0, abs=1e-6)
    clr = ver["critical_clearances"]
    for k in (
        "exp143_s9hpc_to_s7_rack_aisle_x_mm",
        "exp143_s9hpc_node1_to_node2_airflow_z_mm",
        "exp143_s9hpc_switch_to_node2_z_mm",
    ):
        assert clr[k]["pass"] is True, f"Failed Option-HPC clearance {k}: {clr[k]}"


def test_cad_v6_total_mass_bridge_exact():
    ver = json.loads((CAD_DIR / "cad_verification.json").read_text(encoding="utf-8"))
    ma = ver["master_assembly"]
    assert ma["part_count"] == 199
    assert ma["total_mass_kg"] == pytest.approx(1108.137, abs=0.02)
    # Exact v5.0 (1034.937 kg) + Option-Q (9.200 kg) + Option-HPC (64.000 kg)
    assert ver["subsystems"]["s1_ion_source_column"]["mass_kg"] == pytest.approx(30.777, abs=0.02)
    assert ver["subsystems"]["s6_cryo_dr_magnet_readout"]["mass_kg"] == pytest.approx(285.320, abs=0.02)
    assert ver["subsystems"]["s7_electronics_rack_interconnect"]["mass_kg"] == pytest.approx(293.747, abs=0.02)


def test_legacy_overview_dashboards_preserved():
    ddir = CAD_DIR / "drawings"
    for fname in ("00_v3_overview_dashboard.png", "00_v4_overview_dashboard.png", "00_v5_overview_dashboard.png"):
        p = ddir / fname
        assert p.is_file() and p.stat().st_size > 100_000, f"Preserved dashboard missing/corrupt: {fname}"
        w, h = _read_png_dimensions(p)
        assert w >= 1800 and h >= 1200


def test_cad_portability_no_hardcoded_host_paths():
    forbidden = ["/" + "home/" + "berk", "/" + "run/" + "media/" + "berk"]
    for p in list(CAD_DIR.glob("*.py")) + [CAD_DIR / "README.md", CAD_DIR / "cad_verification.json", Path(__file__).resolve()]:
        txt = p.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in txt, f"Hardcoded path '{needle}' in {p.name}"


@pytest.mark.parametrize("stem", EXPECTED_DRAWINGS)
def test_all_10_technical_drawings_svg_and_highres_png(stem: str):
    ddir = CAD_DIR / "drawings"
    svg_p = ddir / f"{stem}.svg"
    png_p = ddir / f"{stem}.png"
    assert svg_p.is_file() and svg_p.stat().st_size > 20_000, f"Invalid SVG: {svg_p}"
    svg_head = svg_p.read_text(encoding="utf-8")[:500]
    assert "<svg" in svg_head
    assert png_p.is_file() and png_p.stat().st_size > 50_000, f"Invalid PNG: {png_p}"
    w, h = _read_png_dimensions(png_p)
    assert w >= 1800 and h >= 1200, f"Resolution too low for {png_p.name}: {w}x{h}"


def test_preview_machine_png_and_readme():
    prev = CAD_DIR / "preview_machine.png"
    assert prev.is_file()
    w, h = _read_png_dimensions(prev)
    assert w >= 1600 and h >= 900
    readme = (CAD_DIR / "README.md").read_text(encoding="utf-8")
    assert "s=0,5" in readme and "S6.8" in readme
