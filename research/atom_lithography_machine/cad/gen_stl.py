"""Generate 8 watertight binary STL meshes + comprehensive cad_verification.json.

Runs under `python3 -B` (NumPy).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

import mesh_engine
import params

CAD_DIR = Path(__file__).resolve().parent
STL_DIR = CAD_DIR / "stl"


def main() -> None:
    STL_DIR.mkdir(parents=True, exist_ok=True)
    all_meshes: list[tuple[np.ndarray, np.ndarray]] = []
    sub_reports: dict[str, dict] = {}
    part_reports: dict[str, dict] = {}
    total_mass = 0.0
    weighted_com = np.zeros(3, dtype=np.float64)
    total_vol_mm3 = 0.0

    for sub_key, meta in params.SUBSYSTEMS.items():
        sub_parts = params.subsystem_parts(sub_key)
        sub_meshes = []
        sub_mass = 0.0
        sub_com_num = np.zeros(3, dtype=np.float64)
        sub_vol = 0.0

        for pname, spec in sub_parts.items():
            v, f = mesh_engine.build_part_mesh(spec, n_seg=48)
            wt = mesh_engine.check_watertight(f)
            vol_m, com_m, area_m = mesh_engine.mesh_volume_and_com(v, f)
            vol_a = mesh_engine.analytic_volume_mm3(spec)
            dens = params.part_density(spec)
            mass_kg = float(spec["mass_override_kg"]) if "mass_override_kg" in spec else (vol_a * 1e-9) * dens
            lo, hi = v.min(axis=0), v.max(axis=0)

            assert wt["is_watertight"], f"Part {pname} is not watertight: {wt}"
            assert vol_m > 0.0, f"Part {pname} has non-positive volume: {vol_m}"

            sub_meshes.append((v, f))
            all_meshes.append((v, f))
            sub_mass += mass_kg
            sub_vol += vol_a
            sub_com_num += com_m * mass_kg

            part_reports[pname] = {
                "subsystem": sub_key,
                "bom_id": spec["bom_id"],
                "label_tr": spec["label_tr"],
                "shape": spec["shape"],
                "material": spec["material"],
                "tol_mm": spec["tol_mm"],
                "triangles": wt["triangle_count"],
                "is_watertight": wt["is_watertight"],
                "volume_analytic_mm3": round(vol_a, 3),
                "volume_mesh_mm3": round(vol_m, 3),
                "mass_kg": round(mass_kg, 4),
                "com_mm": [round(float(x), 2) for x in com_m],
                "bbox_min_mm": [round(float(x), 2) for x in lo],
                "bbox_max_mm": [round(float(x), 2) for x in hi],
            }

        sv, sf = mesh_engine.combine_meshes(sub_meshes)
        stl_path = STL_DIR / f"{sub_key}.stl"
        mesh_engine.write_binary_stl(
            stl_path, sv, sf, f"ALM {params.CAD_VERSION} {meta['code']} {sub_key}"
        )
        stl_disk = mesh_engine.inspect_binary_stl(stl_path)
        assert stl_disk["is_watertight"], f"STL {stl_path.name} failed disk watertight check!"
        assert stl_disk["volume_mm3"] > 0.0, f"STL {stl_path.name} has non-positive volume!"

        sub_com = sub_com_num / max(sub_mass, 1e-12)
        sub_lo, sub_hi = sv.min(axis=0), sv.max(axis=0)
        sub_reports[sub_key] = {
            "code": meta["code"],
            "title_tr": meta["title_tr"],
            "drawing_no": meta["drawing_no"],
            "part_count": len(sub_parts),
            "stl": stl_disk,
            "mass_kg": round(sub_mass, 3),
            "volume_cm3": round(sub_vol / 1000.0, 2),
            "com_mm": [round(float(x), 2) for x in sub_com],
            "bbox_min_mm": [round(float(x), 2) for x in sub_lo],
            "bbox_max_mm": [round(float(x), 2) for x in sub_hi],
            "bbox_span_mm": [round(float(x), 2) for x in (sub_hi - sub_lo)],
        }
        total_mass += sub_mass
        weighted_com += sub_com_num
        total_vol_mm3 += sub_vol
        print(
            f"STL_OK {stl_path.name:38s} tri={stl_disk['triangles']:5d} "
            f"wt={stl_disk['is_watertight']} mass={sub_mass:7.2f} kg"
        )

    # Full master assembly STL
    mv, mf = mesh_engine.combine_meshes(all_meshes)
    master_stl = STL_DIR / "atom_litho_machine.stl"
    mesh_engine.write_binary_stl(
        master_stl, mv, mf, f"ALM {params.CAD_VERSION} Master Assembly s=0.5"
    )
    master_disk = mesh_engine.inspect_binary_stl(master_stl)
    assert master_disk["is_watertight"], "Master STL failed disk watertight check!"
    assert master_disk["volume_mm3"] > 0.0, "Master STL has non-positive volume!"
    print(
        f"STL_OK {master_stl.name:38s} tri={master_disk['triangles']:5d} "
        f"wt={master_disk['is_watertight']} mass={total_mass:7.2f} kg"
    )

    # Exact solid-solid clash check & clearances
    interference = mesh_engine.check_all_interferences(params.PARTS, margin_mm=0.05)
    clearances = mesh_engine.compute_critical_clearances(params.PARTS)

    # Exp80 s=0.5 golden envelope, Exp124 column & Exp125 magnet audits
    ds = params.DESIGN_SPECS
    carrier_diag = ds["carrier_size_mm"] * math.sqrt(2.0)
    chamber_vol_L = (
        math.pi * (ds["chamber_r_in_mm"] ** 2) * ds["chamber_inner_height_mm"] * 1e-6
    )
    ref_vol_ratio = chamber_vol_L / ds["chamber_ref_volume_L"]
    exp80_checks = {
        "scale_s": ds["envelope_scale_s"],
        "bc1_carrier_ge_25mm": {
            "value_mm": ds["carrier_size_mm"],
            "limit_mm": 25.0,
            "pass": ds["carrier_size_mm"] >= 25.0,
        },
        "bc1_in_vacuum_bore_gt_carrier_diag": {
            "value_mm": ds["magnet_clear_bore_mm"],
            "carrier_diag_mm": round(carrier_diag, 2),
            "radial_margin_mm": round((ds["magnet_clear_bore_mm"] - carrier_diag) / 2.0, 2),
            "pass": ds["magnet_clear_bore_mm"] >= carrier_diag + 30.0,
        },
        "bc4_chamber_volume_one_eighth": {
            "value_L": round(chamber_vol_L, 3),
            "ref_s1_L": ds["chamber_ref_volume_L"],
            "ratio_to_s1": round(ref_vol_ratio, 5),
            "target_ratio": 0.125,
            "pass": abs(ref_vol_ratio - 0.125) / 0.125 <= 0.05,
        },
    }
    # Exp124 8-stage column audit
    exp124_stage_keys = [
        "s2_mini_lens_plate", "s2_blanker_plate", "s2_aperture_plate",
        "s1_transfer_lens", "s1_energy_filter", "s1_wien_filter",
        "s1_condenser_lens", "s1_duoplasmatron",
    ]
    exp124_col_top = part_reports["s1_duoplasmatron"]["bbox_max_mm"][2]
    exp124_col_h = round(exp124_col_top - ds["z_wafer_mm"], 2)
    exp124_col_mass = round(sum(part_reports[k]["mass_kg"] for k in exp124_stage_keys), 2)
    exp124_col_od = round(max(part_reports[k]["bbox_max_mm"][0] - part_reports[k]["bbox_min_mm"][0] for k in exp124_stage_keys), 2)
    s16_bore = round(2.0 * params.PARTS["s1_transfer_lens"]["dims"][0], 3)
    s21_bore = round(2.0 * params.PARTS["s2_aperture_plate"]["dims"][0], 3)
    arr_diag = round(ds["write_field_mm"] * math.sqrt(2.0), 3)
    arr_bore_clr = clearances["beam_array_diagonal_to_bore_clearance_mm"]["value_mm"]
    exp124_audit = {
        "exp124_synced": ds["exp124_synced"],
        "active_array": f"{ds['beamlet_array_grid']} = {ds['beamlet_count']} beamlets @ {ds['beamlet_pitch_mm']:.2f} mm pitch ({ds['write_field_mm']:.1f}x{ds['write_field_mm']:.1f} mm)",
        "blanker_tile_count": ds["blanker_tile_count"],
        "beam_array_diagonal_mm": arr_diag,
        "s1_6_transfer_bore_mm": s16_bore,
        "s2_1_aperture_bore_mm": s21_bore,
        "beam_array_diagonal_to_bore_clearance_mm": arr_bore_clr,
        "total_column_height_mm": exp124_col_h,
        "target_height_mm": 562.66,
        "max_od_mm": exp124_col_od,
        "target_od_mm": 110.0,
        "wd_mm": clearances["exp124_archB_wafer_to_minilens_WD_mm"]["value_mm"],
        "target_wd_mm": 0.25,
        "stage_mass_kg": exp124_col_mass,
        "target_mass_kg": 25.92,
        "pass": (
            abs(exp124_col_h - 562.66) < 0.02
            and abs(exp124_col_od - 110.0) < 0.02
            and abs(exp124_col_mass - 25.92) < 0.02
            and abs(s16_bore - 28.0) < 0.01
            and abs(s21_bore - 28.0) < 0.01
            and arr_bore_clr > 2.0
        ),
    }
    # Exp125 8-coil cryo-magnet & shields audit
    exp125_coil_keys = [
        "s6_coil_m_upper", "s6_coil_m_lower", "s6_coil_s_upper", "s6_coil_s_lower",
        "s6_coil_a_upper", "s6_coil_a_lower", "s6_coil_b_upper", "s6_coil_b_lower",
    ]
    res_z_loc = round(params.PARTS["s6_nbtin_resonator_carrier"]["center"][2] - ds["z_wafer_mm"], 2)
    split_gap = round(part_reports["s6_coil_m_upper"]["bbox_min_mm"][2] - part_reports["s6_coil_m_lower"]["bbox_max_mm"][2], 2)
    former_od = round(part_reports["s6_magnet_former_upper"]["bbox_max_mm"][0] - part_reports["s6_magnet_former_upper"]["bbox_min_mm"][0], 2)
    exp125_audit = {
        "exp125_synced": ds["exp125_synced"],
        "coil_count": sum(1 for k in exp125_coil_keys if k in params.PARTS),
        "clear_bore_mm": ds["magnet_clear_bore_mm"],
        "midplane_split_gap_mm": split_gap,
        "former_od_mm": former_od,
        "resonator_z_loc_mm": res_z_loc,
        "resonator_od_mm": round(2.0 * params.PARTS["s6_nbtin_resonator_carrier"]["dims"][0], 2),
        "nb_meissner_r_mm": list(params.PARTS["s6_meissner_cup_wall"]["dims"][:2]),
        "cryoperm_r_mm": list(params.PARTS["s6_cryoperm_sleeve"]["dims"][:2]),
        "pass": (
            all(k in params.PARTS for k in exp125_coil_keys)
            and abs(split_gap - 36.0) < 0.02
            and abs(former_od - 352.0) < 0.02
            and abs(res_z_loc - (-155.0)) < 0.02
        ),
    }
    exp84_modal = {
        "blanker_f1_fea_hz": ds["blanker_f1_fea_hz"],
        "blanker_f1_analytic_hz": ds["blanker_f1_analytic_hz"],
        "fea_analytic_ratio": round(ds["blanker_f1_fea_hz"] / ds["blanker_f1_analytic_hz"], 4),
        "servo_bw_hz": 1000.0,
        "margin_ratio_over_servo": round(ds["blanker_f1_fea_hz"] / 1000.0, 1),
        "pass": ds["blanker_f1_fea_hz"] > 100_000.0,
    }
    # Exp130 S5.5 ms-flash annealing optical head audit
    s55_parts = ("s5_flash_window", "s5_flash_safety_shutter", "s5_flash_anneal_head", "s5_flash_dichroic_pyrometer", "s5_flash_fiber_collimator")
    exp130_audit = {
        "exp130_synced": ds["exp130_synced"],
        "wavelength_nm": ds["flash_laser_wavelength_nm"],
        "pulse_ms": ds["flash_pulse_ms"],
        "fluence_J_cm2": ds["flash_fluence_J_cm2"],
        "window_ca_mm": round(2.0 * params.PARTS["s5_flash_anneal_duct"]["dims"][0], 2),
        "beam_od_mm": ds["flash_beam_od_mm"],
        "homogenizer_dims_mm": list(params.PARTS["s5_flash_anneal_head"]["dims"]),
        "pyrometer_dt_us": ds["flash_pyrometer_dt_us"],
        "sigma_anneal_nm": ds["flash_sigma_anneal_nm"],
        "all_s55_parts_present": all(k in params.PARTS for k in s55_parts),
        "pass": (
            ds["exp130_synced"]
            and all(k in params.PARTS for k in s55_parts)
            and clearances["exp130_flash_window_beam_radial_mm"]["pass"]
        ),
    }
    # Exp131 M4 cavity-QED bus & 4K crossbar switch audit
    exp131_audit = {
        "exp131_synced": ds["exp131_synced"],
        "epi_cap_nm": ds["m4_epi_cap_nm"],
        "bus_impedance_ohm": ds["m4_bus_impedance_ohm"],
        "bus_L_res_um": ds["m4_bus_L_res_um"],
        "B_M4_T": ds["m4_B_field_T"],
        "crossbar_gates_4k": ds["m4_crossbar_gates_4k"],
        "crossbar_pcb_present": "s6_m4_crossbar_4k_pcb" in params.PARTS and "s6_m4_crossbar_4k_mount" in params.PARTS,
        "pass": (
            ds["exp131_synced"]
            and ("s6_m4_crossbar_4k_pcb" in params.PARTS)
            and clearances["exp131_m4_crossbar_to_hemt_radial_mm"]["pass"]
            and clearances["exp131_m4_crossbar_to_coax_y_mm"]["pass"]
        ),
    }
    # Exp133 PT420 mechanical decoupling & closed-loop jitter audit
    bellows_span = round(
        part_reports["s6_ovc_bellows_flange_uhv"]["bbox_max_mm"][0]
        - part_reports["s6_ovc_bellows_flange_dr"]["bbox_min_mm"][0],
        2,
    )
    valve_offset = round(
        abs(params.PARTS["s6_pt420_coldhead"]["center"][0] - params.PARTS["s6_pt420_remote_valve_box"]["center"][0]),
        2,
    )
    braid_keys = [f"s6_mxc_braid_{i}" for i in range(1, 5)]
    exp133_audit = {
        "exp133_synced": ds["exp133_synced"],
        "bellows_id_mm": round(2.0 * params.PARTS["s6_ovc_bellows_cf63"]["dims"][0], 2),
        "bellows_od_mm": round(2.0 * params.PARTS["s6_ovc_bellows_rib_1"]["dims"][1], 2),
        "bellows_active_length_mm": bellows_span,
        "bellows_k_N_m": ds["ovc_bellows_k_N_m"],
        "bellows_k_max_N_m": ds["ovc_bellows_k_max_N_m"],
        "braid_count": sum(1 for k in braid_keys if k in params.PARTS),
        "braid_k_N_m": ds["mxc_braid_k_N_m"],
        "braid_k_max_N_m": ds["mxc_braid_k_max_N_m"],
        "braid_dT_mK": ds["mxc_braid_dT_mK"],
        "dr_busbar_od_mm": round(2.0 * params.PARTS["s6_mxc_cold_finger"]["dims"][0], 2),
        "dr_busbar_length_mm": round(params.PARTS["s6_mxc_cold_finger"]["dims"][1], 2),
        "remote_valve_offset_mm": valve_offset,
        "flex_he_length_mm": ds["pt420_flex_he_length_mm"],
        "sigma_stage_nm": ds["exp133_sigma_stage_nm"],
        "sigma_pointing_nm": ds["exp133_sigma_pointing_nm"],
        "sigma_thermal_nm": ds["exp133_sigma_thermal_nm"],
        "pass": (
            ds["exp133_synced"]
            and abs(bellows_span - 120.0) < 0.2
            and abs(valve_offset - 500.0) < 0.2
            and all(k in params.PARTS for k in braid_keys)
            and ("s6_pt420_remote_valve_box" in params.PARTS)
            and clearances["exp133_bellows_to_4k_shield_radial_mm"]["pass"]
            and clearances["exp133_braids_inside_4k_shield_radial_mm"]["pass"]
            and clearances["exp133_remote_valve_to_dr_flange_x_mm"]["pass"]
        ),
    }
    legacy_cleanup = {
        "maglev_removed": not any("maglev" in k.lower() for k in params.PARTS),
        "piezo_6dof_present": "s4_piezo_fine_6dof" in params.PARTS and "s4_piezo_coarse_xy" in params.PARTS,
        "dr_s68_present": "s6_dr_flange_mxc" in params.PARTS and "s6_pt420_coldhead" in params.PARTS,
        "energy_filter_hda_present": "s1_energy_filter" in params.PARTS,
        "exp125_8coil_magnet_present": all(k in params.PARTS for k in exp125_coil_keys),
        "exp130_s55_flash_present": exp130_audit["all_s55_parts_present"],
        "exp131_m4_4k_crossbar_present": exp131_audit["crossbar_pcb_present"],
        "exp133_pt420_decoupled_present": exp133_audit["pass"],
    }

    total_com = weighted_com / max(total_mass, 1e-12)
    mlo, mhi = mv.min(axis=0), mv.max(axis=0)
    all_pass = (
        interference["solid_clashes"] == 0
        and all(v["pass"] for v in clearances.values())
        and all(v["pass"] for v in exp80_checks.values() if isinstance(v, dict))
        and exp124_audit["pass"]
        and exp125_audit["pass"]
        and exp84_modal["pass"]
        and exp130_audit["pass"]
        and exp131_audit["pass"]
        and exp133_audit["pass"]
        and all(legacy_cleanup.values())
        and master_disk["is_watertight"]
    )

    report = {
        "cad_version": params.CAD_VERSION,
        "units": params.UNITS,
        "tolerance_std": params.GENERAL_TOLERANCE_STD,
        "no_lab_measurement": params.NO_LAB_MEASUREMENT,
        "overall_pass": bool(all_pass),
        "design_specs": ds,
        "legacy_cleanup": legacy_cleanup,
        "master_assembly": {
            "part_count": len(params.PARTS),
            "subsystem_count": len(params.SUBSYSTEMS),
            "total_mass_kg": round(total_mass, 3),
            "total_volume_L": round(total_vol_mm3 * 1e-6, 3),
            "center_of_mass_mm": [round(float(x), 2) for x in total_com],
            "bbox_min_mm": [round(float(x), 2) for x in mlo],
            "bbox_max_mm": [round(float(x), 2) for x in mhi],
            "bbox_span_mm": [round(float(x), 2) for x in (mhi - mlo)],
            "stl": master_disk,
        },
        "interference_audit": interference,
        "critical_clearances": clearances,
        "exp80_golden_envelope_audit": exp80_checks,
        "exp124_column_audit": exp124_audit,
        "exp125_magnet_audit": exp125_audit,
        "exp84_modal_audit": exp84_modal,
        "exp130_flash_audit": exp130_audit,
        "exp131_m4_audit": exp131_audit,
        "exp133_decoupling_audit": exp133_audit,
        "subsystems": sub_reports,
        "parts": part_reports,
    }

    out_json = CAD_DIR / "cad_verification.json"
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"VERIFICATION_WRITTEN overall_pass={all_pass} clashes={interference['solid_clashes']} "
        f"mass={total_mass:.2f} kg CoM={[round(float(x), 1) for x in total_com]}"
    )


if __name__ == "__main__":
    main()
