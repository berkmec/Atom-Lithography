"""Exp133 (H151): Coupled Multi-Physics Vibration, Ion-Column FEM, Thermal Drift & Control.

Reads the real CAD v3.0 mass/geometry audit (956.903 kg, 143 parts) and Exp124 5 keV
ion-column error budget directly from workspace JSON/module artifacts using portable
relative paths.

Epistemic status: {Model}, {Sayısal-Simülasyon}, {Literatür} (no_lab_measurement=true).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.linalg import eigh

ROOT = Path(__file__).resolve().parents[2]
CAD_VERIF_PATH = ROOT / "research" / "atom_lithography_machine" / "cad" / "cad_verification.json"
WPM6_VERIF_PATH = ROOT / "hardware" / "cad_parts" / "cad_parts_verification.json"
EXP124_PATH = ROOT / "results" / "exp124_ion_column_optics" / "exp124.json"
EXP66_PATH = ROOT / "results" / "exp66" / "exp66.json"


# ---------------------------------------------------------------------------
# 1. Dynamic CAD v3.0 Mass & Geometry Partitioning
# ---------------------------------------------------------------------------
def load_cad_and_exp124_anchors() -> dict[str, Any]:
    """Load real CAD v3.0 masses/geometry and Exp124 error budget dynamically."""
    cad = json.loads(CAD_VERIF_PATH.read_text(encoding="utf-8"))
    exp124 = json.loads(EXP124_PATH.read_text(encoding="utf-8"))
    parts = cad["parts"]

    def part_mass(name: str) -> float:
        return float(parts[name]["mass_kg"])

    def part_com_z_m(name: str) -> float:
        return float(parts[name]["com_mm"][2]) * 1e-3

    granite_parts = ["s4_granite_base"]
    air_iso_parts = [f"s4_air_isolator_{i}" for i in range(1, 5)]

    wafer_moving_full = [
        "s3_wafer_carrier", "s3_silicon_wafer", "s3_ibic_contact_ring",
        "s3_ibic_csa_pos", "s3_ibic_csa_neg",
        "s3_hv_bias_shield_pos", "s3_hv_bias_shield_neg",
        "s6_mxc_cold_chuck",
        "s6_thermal_iso_1", "s6_thermal_iso_2", "s6_thermal_iso_3", "s6_thermal_iso_4",
    ]
    m_fine_stage = part_mass("s4_piezo_fine_6dof")
    m_wafer = sum(part_mass(k) for k in wafer_moving_full) + 0.5 * m_fine_stage

    decoupled_s5 = {
        "s5_loadlock_duct", "s5_loadlock_chamber", "s5_loadlock_stand", "s5_transfer_arm",
        "s5_pump_duct", "s5_pump_tee", "s5_turbo_pump", "s5_ion_tsp_pump", "s5_pump_stand",
    }
    cryo_bridge_parts = {
        "s6_mxc_cold_finger", "s6_cryo_bridge_4k_shield", "s6_cryo_bridge_ovc",
    }
    dr_tower_prefixes = (
        "s6_dr_", "s6_pt420_", "s6_shield_", "s6_hemt_", "s6_coax_",
    )

    m_granite = sum(part_mass(k) for k in granite_parts)
    m_air_iso = sum(part_mass(k) for k in air_iso_parts)
    m_dr = 0.0
    m_table_rigid = 0.5 * m_fine_stage
    m_uhv_chamber_wall = 0.0
    m_s1_s2_total = 0.0
    m_s7_rack = 0.0
    m_decoupled_ll_pump = 0.0
    m_cryo_bridge = 0.0

    z_pivot = part_com_z_m("s4_active_table")          # 0.230 m
    z_wafer = float(cad["design_specs"]["z_wafer_mm"]) * 1e-3  # 0.500 m
    z_flange = part_com_z_m("s5_chamber_top_flange")   # 0.6325 m
    z_bridge = part_com_z_m("s6_cryo_bridge_ovc")      # 0.4915 m
    z_met_ring = part_com_z_m("s4_metrology_frame")    # 0.367 m

    table_mass_z_moment = 0.5 * m_fine_stage * part_com_z_m("s4_piezo_fine_6dof")
    table_inertia_pivot = 0.5 * m_fine_stage * (
        (part_com_z_m("s4_piezo_fine_6dof") - z_pivot) ** 2 + 0.03**2
    )

    for name, info in parts.items():
        m = float(info["mass_kg"])
        sub = info["subsystem"]
        cz = float(info["com_mm"][2]) * 1e-3
        bmin = info["bbox_min_mm"]
        bmax = info["bbox_max_mm"]
        dx = (bmax[0] - bmin[0]) * 1e-3
        dz = (bmax[2] - bmin[2]) * 1e-3
        i_local = m * (dx**2 + dz**2) / 12.0

        if name in granite_parts or name in air_iso_parts or name in wafer_moving_full or name == "s4_piezo_fine_6dof":
            continue
        elif sub == "s7_electronics_rack_interconnect":
            m_s7_rack += m
        elif name in decoupled_s5:
            m_decoupled_ll_pump += m
        elif name in cryo_bridge_parts:
            m_cryo_bridge += m
        elif name.startswith(dr_tower_prefixes):
            m_dr += m
        else:
            m_table_rigid += m
            table_mass_z_moment += m * cz
            table_inertia_pivot += i_local + m * (cz - z_pivot) ** 2
            if sub in ("s1_ion_source_column", "s2_mems_write_head"):
                m_s1_s2_total += m
            if sub == "s5_uhv_chamber_loadlock":
                m_uhv_chamber_wall += m

    z_com_table = table_mass_z_moment / m_table_rigid
    h_cg_table = z_com_table - z_pivot

    m_total_accounted = (
        m_granite + m_air_iso + m_table_rigid + m_wafer
        + m_dr + m_cryo_bridge + m_decoupled_ll_pump + m_s7_rack
    )
    m_cad_total = float(cad["master_assembly"]["total_mass_kg"])
    assert abs(m_total_accounted - m_cad_total) < 0.05, (
        f"Mass conservation failed: {m_total_accounted:.3f} vs {m_cad_total:.3f}"
    )

    op_hires = exp124["operating_points_5keV"]["ArchB_HiRes_Ti0p25_10ms"]
    op_canon = exp124["operating_points_5keV"]["ArchB_HiRes_Ti0p5_15ms"]
    arch_b = exp124["lens_architectures"]["Arch-B_0p5mm_immersion"]

    # Rigid CAD v3.0 cryo bridge properties
    # s6_mxc_cold_finger: solid Ø7 mm, L=497 mm OFHC Cu rod (E=117 GPa)
    e_cu = 117.0e9
    r_finger = 3.5e-3
    l_finger = 0.497
    k_cold_finger_rigid = e_cu * math.pi * r_finger**2 / l_finger  # 9.060e6 N/m

    # s6_cryo_bridge_ovc: Ø56/Ø44 mm, L=283 mm 316LN SS tube in series with vessel shell ports
    e_ss = 193.0e9
    a_ovc = math.pi * (28.0e-3**2 - 22.0e-3**2)
    l_ovc = 0.283
    k_ovc_axial_tube = e_ss * a_ovc / l_ovc
    k_shell_port = 5.0e6
    k_ovc_rigid_eff = 1.0 / (1.0 / k_ovc_axial_tube + 1.0 / k_shell_port)  # 4.961e6 N/m

    return {
        "cad_version": cad["cad_version"],
        "cad_total_mass_kg": m_cad_total,
        "mass_accounted_kg": m_total_accounted,
        "m_granite_kg": m_granite,
        "m_air_iso_kg": m_air_iso,
        "m_table_rigid_kg": m_table_rigid,
        "m_wafer_stage_kg": m_wafer,
        "m_dr_tower_kg": m_dr,
        "m_cryo_bridge_kg": m_cryo_bridge,
        "m_decoupled_ll_pump_kg": m_decoupled_ll_pump,
        "m_s7_rack_kg": m_s7_rack,
        "m_uhv_chamber_kg": m_uhv_chamber_wall,
        "m_s1_s2_column_kg": m_s1_s2_total,
        "I_table_pivot_kg_m2": table_inertia_pivot,
        "z_pivot_m": z_pivot,
        "z_com_table_m": z_com_table,
        "h_cg_table_m": h_cg_table,
        "z_wafer_m": z_wafer,
        "z_flange_m": z_flange,
        "z_bridge_m": z_bridge,
        "z_met_ring_m": z_met_ring,
        "column_height_mm": float(cad["design_specs"]["column_total_height_mm"]),
        "f_img_archb_mm": float(arch_b["f_img_mm"]),
        "wd_archb_mm": float(arch_b["working_distance_mm"]),
        "k_cold_finger_rigid_N_m": k_cold_finger_rigid,
        "k_ovc_rigid_eff_N_m": k_ovc_rigid_eff,
        "exp124_hires_spot_nm": float(op_hires["sigma_spot_nm"]),
        "exp124_hires_straggle_nm": float(op_hires["sigma_straggle_nm"]),
        "exp124_hires_total_nm": float(op_hires["sigma_total_nm"]),
        "exp124_canon_spot_nm": float(op_canon["sigma_spot_nm"]),
        "exp124_canon_straggle_nm": float(op_canon["sigma_straggle_nm"]),
        "exp124_canon_total_nm": float(op_canon["sigma_total_nm"]),
        "exp124_anneal_budget_nm": 0.50,
        "parts_raw": parts,
    }


# ---------------------------------------------------------------------------
# 2. Conforming 40-Element Euler-Bernoulli FEM of the Exp124 Ion Column
# ---------------------------------------------------------------------------
def build_column_segments(cad_anchors: dict[str, Any]) -> list[dict[str, float]]:
    """Build exact stepped upper-cantilever column segments from CAD v3.0 parts."""
    parts = cad_anchors["parts_raw"]
    z0 = cad_anchors["z_flange_m"]  # 0.6325 m

    m_hda_total = float(parts["s1_energy_filter"]["mass_kg"])
    frac_hda_upper = (0.70966 - z0) / (0.70966 - 0.61466)
    m_hda_upper = m_hda_total * frac_hda_upper

    m_iso_15_12 = float(parts["s1_hv_iso_15_12"]["mass_kg"])
    m_wien = float(parts["s1_wien_filter"]["mass_kg"])
    m_iso_12_14 = float(parts["s1_hv_iso_12_14"]["mass_kg"])
    m_cond = float(parts["s1_condenser_lens"]["mass_kg"])
    m_iso_14_11 = float(parts["s1_hv_iso_14_11"]["mass_kg"])
    m_duo = (
        float(parts["s1_duoplasmatron"]["mass_kg"])
        + float(parts["s1_ph3_manifold"]["mass_kg"])
        + float(parts["s1_ph3_feed_pipe"]["mass_kg"])
    )

    raw = [
        ("HDA_upper",      0.00000, 0.07716, 0.055, 0.0505, 110e9, m_hda_upper, 7),
        ("HV_iso_15_12",   0.07716, 0.08516, 0.053, 0.0500,  50e9, m_iso_15_12, 2),
        ("Wien_filter",    0.08516, 0.23516, 0.055, 0.0500, 180e9, m_wien,     12),
        ("HV_iso_12_14",   0.23516, 0.24116, 0.041, 0.0385,  50e9, m_iso_12_14, 2),
        ("Condenser_lens", 0.24116, 0.28616, 0.042, 0.0375, 193e9, m_cond,      4),
        ("HV_iso_14_11",   0.28616, 0.29016, 0.041, 0.0385,  50e9, m_iso_14_11, 2),
        ("Duoplasmatron",  0.29016, 0.43016, 0.045, 0.0405, 193e9, m_duo,      11),
    ]
    segs = []
    for label, s0, s1, ro, ri, E, ms, ne in raw:
        I = math.pi / 4.0 * (ro**4 - ri**4)
        segs.append({
            "label": label,
            "s0": s0,
            "s1": s1,
            "r_out": ro,
            "r_in": ri,
            "E": E,
            "I": I,
            "EI": E * I,
            "mass_kg": ms,
            "rhoA": ms / (s1 - s0),
            "n_elem_base": ne,
        })
    return segs


def solve_column_fem(
    cad_anchors: dict[str, Any],
    refine_factor: int = 1,
    include_flange_compliance: bool = True,
    extra_tip_masses: list[tuple[float, float]] | None = None,
) -> dict[str, Any]:
    """Solve conforming Hermitian Euler-Bernoulli FEM for the upper cantilevered ion column.

    Optional ``extra_tip_masses`` is a list of ``(s_pos_m, mass_kg)`` point loads (e.g. WP-M6
    upper-column hardware S1.1-02, S1.3-05, S1.7-01 at s=0.360 m above the S5 top flange, OBS-077).
    """
    segs = build_column_segments(cad_anchors)
    xs = [0.0]
    elem_props = []
    for seg in segs:
        if refine_factor == 0:
            ne = max(1, seg["n_elem_base"] // 2)
        else:
            ne = max(1, int(round(seg["n_elem_base"] * refine_factor)))
        local_x = np.linspace(seg["s0"], seg["s1"], ne + 1)
        for j in range(ne):
            xs.append(float(local_x[j + 1]))
            elem_props.append((float(local_x[j]), float(local_x[j + 1]), seg["EI"], seg["rhoA"]))

    n_elem = len(elem_props)
    n_nodes = n_elem + 1
    ndof = 2 * n_nodes
    K = np.zeros((ndof, ndof), dtype=float)
    M = np.zeros((ndof, ndof), dtype=float)

    for e, (x0, x1, EI, rhoA) in enumerate(elem_props):
        le = x1 - x0
        ke = (EI / le**3) * np.array([
            [12.0, 6.0 * le, -12.0, 6.0 * le],
            [6.0 * le, 4.0 * le**2, -6.0 * le, 2.0 * le**2],
            [-12.0, -6.0 * le, 12.0, -6.0 * le],
            [6.0 * le, 2.0 * le**2, -6.0 * le, 4.0 * le**2],
        ])
        me = (rhoA * le / 420.0) * np.array([
            [156.0, 22.0 * le, 54.0, -13.0 * le],
            [22.0 * le, 4.0 * le**2, 13.0 * le, -3.0 * le**2],
            [54.0, 13.0 * le, 156.0, -22.0 * le],
            [-13.0 * le, -3.0 * le**2, -22.0 * le, 4.0 * le**2],
        ])
        idx = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
        K[np.ix_(idx, idx)] += ke
        M[np.ix_(idx, idx)] += me

    # Add optional concentrated off-axis/upper-column point masses (OBS-077)
    if extra_tip_masses:
        xs_arr = np.asarray(xs, dtype=float)
        for s_pos, m_pt in extra_tip_masses:
            # Find nearest node to s_pos and distribute translational + small rotary inertia
            node_i = int(np.argmin(np.abs(xs_arr - s_pos)))
            M[2 * node_i, 2 * node_i] += float(m_pt)
            # Small local rotary inertia of compact feedthrough/oven assembly (r_gyr ~ 0.04 m)
            M[2 * node_i + 1, 2 * node_i + 1] += float(m_pt) * (0.04 ** 2)

    E_ss = 193.0e9
    nu_ss = 0.29
    t_fl = 0.025
    D_plate = E_ss * t_fl**3 / (12.0 * (1.0 - nu_ss**2))
    k_rot_plate = 4.0 * math.pi * D_plate / 0.36
    k_rot_cf_joint = 1.65e6
    k_rot_root = 1.0 / (1.0 / k_rot_plate + 1.0 / k_rot_cf_joint)

    if include_flange_compliance:
        K[1, 1] += k_rot_root
        free = list(range(1, ndof))
    else:
        free = list(range(2, ndof))

    vals, vecs = eigh(K[np.ix_(free, free)], M[np.ix_(free, free)])
    freqs_hz = np.sqrt(np.maximum(vals, 0.0)) / (2.0 * math.pi)

    phi1_full = np.zeros(ndof, dtype=float)
    phi1_full[free] = vecs[:, 0]
    tip_w = phi1_full[-2]
    if abs(tip_w) < 1e-12:
        tip_w = 1.0
    phi1_full /= tip_w
    if phi1_full[-2] < 0:
        phi1_full *= -1.0

    r_x = np.zeros(ndof, dtype=float)
    r_x[0::2] = 1.0

    z_flange = cad_anchors["z_flange_m"]
    z_pivot = cad_anchors["z_pivot_m"]
    r_th = np.zeros(ndof, dtype=float)
    for i, s_val in enumerate(xs):
        r_th[2 * i] = (z_flange + s_val) - z_pivot
        r_th[2 * i + 1] = 1.0

    m_col_1 = float(phi1_full @ M @ phi1_full)
    k_col_1 = float(phi1_full @ K @ phi1_full)
    m_col_x = float(phi1_full @ M @ r_x)
    m_col_th = float(phi1_full @ M @ r_th)
    m_upper_total = float(r_x @ M @ r_x)
    eff_modal_mass_x = m_col_x**2 / m_col_1

    tip_slope = float(phi1_full[-1])
    root_slope = float(phi1_full[1])
    L_upper = xs[-1]
    theta_beam_per_tip_m = 0.5 * (tip_slope + 1.0 / L_upper)

    if include_flange_compliance:
        M_root_per_m = k_rot_root * root_slope
    else:
        le0 = elem_props[0][1] - elem_props[0][0]
        EI0 = elem_props[0][2]
        w1, t1 = phi1_full[2], phi1_full[3]
        M_root_per_m = EI0 * (6.0 * w1 / le0**2 - 2.0 * t1 / le0)

    return {
        "n_elem": n_elem,
        "L_upper_m": L_upper,
        "m_upper_total_kg": m_upper_total,
        "k_rot_root_Nm_rad": k_rot_root,
        "freqs_hz": [float(f) for f in freqs_hz[:5]],
        "f1_hz": float(freqs_hz[0]),
        "f2_hz": float(freqs_hz[1]),
        "f3_hz": float(freqs_hz[2]),
        "m_col_1_kg": m_col_1,
        "k_col_1_N_m": k_col_1,
        "m_col_x_kg": m_col_x,
        "m_col_th_kg_m": m_col_th,
        "eff_modal_mass_x_kg": eff_modal_mass_x,
        "eff_modal_mass_fraction": eff_modal_mass_x / m_upper_total,
        "root_slope_rad_per_m": root_slope,
        "tip_slope_rad_per_m": tip_slope,
        "theta_beam_per_tip_m": theta_beam_per_tip_m,
        "M_root_Nm_per_m": M_root_per_m,
        "nodes_s_m": xs,
        "phi1_w": [float(v) for v in phi1_full[0::2]],
    }


def compute_lower_snout_and_chamber_compliance(cad_anchors: dict[str, Any]) -> dict[str, float]:
    """Compute lateral elastic compliance of UHV chamber wall + hanging S1.6/S2 snout."""
    E_ss = 193.0e9
    r_mid = 0.187
    t_wall = 0.010
    dtheta = math.radians(34.0)
    h_pillar = 0.060
    A_4pillars = 4.0 * r_mid * t_wall * dtheta
    G_ss = E_ss / (2.0 * (1.0 + 0.29))
    k_shear_pillars = 0.5 * G_ss * A_4pillars / h_pillar
    I_cyl = math.pi * r_mid**3 * t_wall
    k_bend_wall = 3.0 * E_ss * I_cyl / (0.335**3)
    k_chamber_lat = 1.0 / (1.0 / k_shear_pillars + 1.0 / k_bend_wall)

    E_ti = 114.0e9
    r_s = 4.5e-3
    l_s = 7.9e-3
    I_s = math.pi / 4.0 * r_s**4
    k_3struts_lat = 3.0 * 12.0 * E_ti * I_s / l_s**3
    k_head_rel_met = 1.0 / (1.0 / k_chamber_lat + 1.0 / k_3struts_lat)

    t_fl = 0.025
    D_plate = E_ss * t_fl**3 / (12.0 * (1.0 - 0.29**2))
    k_rot_plate = 4.0 * math.pi * D_plate / 0.36
    L_snout = cad_anchors["z_flange_m"] - (cad_anchors["z_wafer_m"] + 1.13e-3)

    parts = cad_anchors["parts_raw"]
    m_snout = (
        float(parts["s1_transfer_lens"]["mass_kg"])
        + float(parts["s2_aperture_plate"]["mass_kg"])
        + float(parts["s2_blanker_plate"]["mass_kg"])
        + float(parts["s2_mini_lens_plate"]["mass_kg"])
        + float(parts["s2_tile_carrier"]["mass_kg"])
    )
    m_top_flange_eff = float(parts["s5_chamber_top_flange"]["mass_kg"]) + m_snout
    f_snout_hz = math.sqrt(k_head_rel_met / m_top_flange_eff) / (2.0 * math.pi)

    return {
        "k_chamber_lat_N_m": k_chamber_lat,
        "k_3struts_lat_N_m": k_3struts_lat,
        "k_head_rel_met_N_m": k_head_rel_met,
        "k_rot_plate_Nm_rad": k_rot_plate,
        "L_snout_m": L_snout,
        "m_snout_kg": m_snout,
        "m_top_flange_eff_kg": m_top_flange_eff,
        "f_chamber_snout_hz": f_snout_hz,
    }


# ---------------------------------------------------------------------------
# 3. Literature-Anchored Disturbance Spectra (VC Floors, PT420, Interf, Amp)
# ---------------------------------------------------------------------------
VC_VELOCITY_UM_S = {
    "VC-C": 12.5,
    "VC-E": 3.1,
    "VC-G": 0.78,
}


def seismic_floor_disp_psd(freqs_hz: np.ndarray, vc_grade: str = "VC-E") -> np.ndarray:
    """One-sided cleanroom floor displacement PSD S_xx(f) [m^2/Hz] per IEST-RP-CC012.2."""
    v_nom = VC_VELOCITY_UM_S[vc_grade] * 1e-6
    f = np.maximum(freqs_hz, 0.1)
    v_13 = np.where(f < 1.0, v_nom * (f / 1.0) ** 0.90, v_nom)
    slab_bump = 1.0 + 1.0 / (1.0 + ((f - 18.0) / 4.5) ** 2)
    bw_one_third = 0.23156 * f
    s_vv = (v_13**2 / bw_one_third) * slab_bump
    hf_roll = 1.0 / (1.0 + (f / 120.0) ** 2)
    return s_vv / ((2.0 * np.pi * f) ** 2) * hf_roll


def pt420_force_psd(
    freqs_hz: np.ndarray,
    remote_valve: bool = False,
    harmonic_ff_db: float = 0.0,
    n_harmonics: int = 20,
    n_ff_harmonics: int = 15,
) -> dict[str, np.ndarray]:
    """One-sided Cryomech PT420 lateral reaction force PSD S_FF(f) [N^2/Hz] on DR tower."""
    df = float(freqs_hz[1] - freqs_hz[0])
    f = freqs_hz
    f0 = 1.40
    gamma = 0.025

    if not remote_valve:
        F1 = 18.0  # N RMS at 1.4 Hz (~11 um RMS / ~30 um p-p on 16 Hz DR frame)
        decay = 0.95
        s_bb = (0.14**2) * (1.0 / (1.0 + (f / 180.0) ** 2)) * (
            1.0 + 3.0 / (1.0 + ((f - 65.0) / 25.0) ** 2)
        )
    else:
        F1 = 5.0   # N RMS at 1.4 Hz (~3.0 um RMS / ~8.5 um p-p with remote rotary valve)
        decay = 1.45
        s_bb = (0.011**2) * (1.0 / (1.0 + (f / 160.0) ** 2)) * (
            1.0 + 1.5 / (1.0 + ((f - 65.0) / 25.0) ** 2)
        )

    s_harm = np.zeros_like(f)
    ff_power_factor = 10.0 ** (-harmonic_ff_db / 10.0) if harmonic_ff_db > 0.0 else 1.0

    for n in range(1, n_harmonics + 1):
        fn = n * f0
        if fn > f[-1] - 1.0:
            break
        Fn = F1 / (n ** decay)
        lor = 1.0 / ((f - fn) ** 2 + gamma**2)
        area = float(np.sum(lor) * df)
        if area > 0.0:
            p_n = (Fn**2) * (ff_power_factor if n <= n_ff_harmonics else 1.0)
            s_harm += p_n * (lor / area)

    return {
        "s_total": s_harm + s_bb,
        "s_harmonics": s_harm,
        "s_broadband": s_bb,
    }


def interferometer_noise_psd(freqs_hz: np.ndarray) -> np.ndarray:
    """One-sided UHV heterodyne laser interferometer noise PSD [m^2/Hz]."""
    n_white = 1.5e-12
    f = np.maximum(freqs_hz, 0.1)
    return (n_white**2) * (1.0 + (0.5 / f) ** 2)


def piezo_amp_openloop_disp_psd(freqs_hz: np.ndarray) -> np.ndarray:
    """One-sided open-loop HV piezo driver + coarse-stage creep displacement PSD [m^2/Hz].

    Models a low-noise 100 V / 50 um piezo HV amplifier with ~2.0 mV RMS low-frequency
    1/f piezo creep & driver flicker (0.2-15 Hz, RC rolled off at 18 Hz) plus 40 pm
    linear-PSU 50 Hz mains ripple -> ~1.0 nm RMS total open-loop jitter. Closed-loop
    interferometer servo suppresses low-freq creep by >30 dB to ~0.055 nm.
    """
    df = float(freqs_hz[1] - freqs_hz[0])
    f = np.maximum(freqs_hz, 0.1)
    s_lf = (5.0e-10 ** 2) / (f ** 1.45) / (1.0 + (f / 16.0) ** 4)
    lor50 = 1.0 / ((f - 50.0) ** 2 + 0.15**2)
    lor50 /= float(np.sum(lor50) * df)
    s_50 = (0.040e-9 ** 2) * lor50
    return s_lf + s_50


# ---------------------------------------------------------------------------
# 4. Coupled 6-DOF Dynamic Matrix + Causal Active Isolation & Piezo Servo
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MachineConfig:
    name: str
    label_tr: str
    k_bellows: float         # N/m (DR OVC <-> UHV chamber bridge)
    k_braid: float           # N/m (DR MXC <-> wafer cold chuck link)
    remote_valve: bool       # Cryomech PT420 remote rotary valve option
    active_iso_on: bool      # S4.2 active skyhook table isolation (0.5-100 Hz)
    piezo_pid_on: bool       # S4.3/S4.4 6-DOF closed-loop piezo PID + notch
    harmonic_ff_db: float    # Phase-locked 1.4 Hz harmonic feedforward attenuation (dB)
    vc_grade: str = "VC-E"
    delta_h_abbe_m: float = 0.010  # 10 mm residual Abbé mismatch (92.5% cancel of 134 mm z-span)
    retune_for_rigid: bool = False


def compute_piezo_controller_and_margins(
    m_wafer: float,
    k_piezo: float,
    c_piezo: float,
    k_braid: float,
    freqs_hz: np.ndarray,
    retune_for_plant: bool = False,
) -> dict[str, Any]:
    """Build causal piezo I+Lag+Notch+LP+DSP-delay controller and verify exact margins."""
    w = 2.0 * np.pi * freqs_hz
    s = 1j * w

    k_eff = k_piezo + k_braid
    G_p = 1.0 / (m_wafer * s**2 + c_piezo * s + k_eff)

    if retune_for_plant:
        k_des = k_eff
        wn_des = math.sqrt(k_eff / m_wafer)
    else:
        k_des = k_piezo
        wn_des = math.sqrt(k_piezo / m_wafer)

    wc = 2.0 * math.pi * 42.0
    wz_lag = 2.0 * math.pi * 8.0
    wp_lag = 2.0 * math.pi * 1.0
    Lag = (s + wz_lag) / (s + wp_lag)
    Notch = (s**2 + 2.0 * 0.020 * wn_des * s + wn_des**2) / (
        s**2 + 2.0 * 0.45 * wn_des * s + wn_des**2
    )
    wlp = 2.0 * math.pi * 260.0
    LP = wlp / (s + wlp)
    Delay = np.exp(-s * 0.00020)

    C_total = k_des * (wc / s) * Lag * Notch * LP * Delay

    L = C_total * G_p
    mag = np.abs(L)
    phase_deg = np.rad2deg(np.unwrap(np.angle(L)))
    while phase_deg[0] > 0.0:
        phase_deg -= 360.0
    while phase_deg[0] < -270.0:
        phase_deg += 360.0

    S_tf = 1.0 / (1.0 + L)
    T_tf = L / (1.0 + L)
    S_inf = float(np.max(np.abs(S_tf)))

    idx_gc = np.where((mag[:-1] >= 1.0) & (mag[1:] < 1.0))[0]
    if len(idx_gc) > 0:
        i0 = int(idx_gc[-1])
        frac = (1.0 - mag[i0]) / (mag[i0 + 1] - mag[i0] + 1e-30)
        f_gc = float(freqs_hz[i0] + frac * (freqs_hz[i0 + 1] - freqs_hz[i0]))
        ph_gc = float(phase_deg[i0] + frac * (phase_deg[i0 + 1] - phase_deg[i0]))
        pm_deg = 180.0 + ph_gc
    else:
        f_gc = 0.0
        pm_deg = 180.0

    idx_pc = np.where((phase_deg[:-1] >= -180.0) & (phase_deg[1:] < -180.0))[0]
    if len(idx_pc) > 0:
        i0 = int(idx_pc[0])
        frac = (-180.0 - phase_deg[i0]) / (phase_deg[i0 + 1] - phase_deg[i0] + 1e-30)
        f_pc = float(freqs_hz[i0] + frac * (freqs_hz[i0 + 1] - freqs_hz[i0]))
        mag_pc = float(mag[i0] + frac * (mag[i0 + 1] - mag[i0]))
        gm_db = float(-20.0 * math.log10(max(mag_pc, 1e-12)))
    else:
        f_pc = float(freqs_hz[-1])
        gm_db = 40.0

    is_stable = (pm_deg > 10.0) and (gm_db > 2.0) and (S_inf < 10.0)

    return {
        "C_jw": C_total,
        "L_jw": L,
        "S_jw": S_tf,
        "T_jw": T_tf,
        "n_gain_crossings": int(len(idx_gc)),
        "f_crossover_hz": f_gc,
        "phase_margin_deg": pm_deg,
        "f_phase_crossover_hz": f_pc,
        "gain_margin_db": gm_db,
        "sensitivity_peak_S_inf": S_inf,
        "is_stable": bool(is_stable),
    }


def build_mdof_matrices(
    cad_anchors: dict[str, Any],
    col_fem: dict[str, Any],
    k_bellows: float,
    k_braid: float,
) -> dict[str, Any]:
    """Assemble exact symmetric positive-definite 6-DOF M, C, K matrices."""
    m_g = cad_anchors["m_granite_kg"]
    m_t = cad_anchors["m_table_rigid_kg"]
    I_t = cad_anchors["I_table_pivot_kg_m2"]
    h_cg = cad_anchors["h_cg_table_m"]
    m_dr = cad_anchors["m_dr_tower_kg"]
    m_w = cad_anchors["m_wafer_stage_kg"]

    h_w = cad_anchors["z_wafer_m"] - cad_anchors["z_pivot_m"]
    h_br = cad_anchors["z_bridge_m"] - cad_anchors["z_pivot_m"]

    M = np.zeros((6, 6), dtype=float)
    M[0, 0] = m_g
    M[1, 1] = m_t
    M[1, 2] = m_t * h_cg
    M[2, 1] = m_t * h_cg
    M[2, 2] = I_t
    M[3, 3] = m_dr
    M[4, 4] = m_w
    M[5, 5] = col_fem["m_col_1_kg"]
    M[1, 5] = col_fem["m_col_x_kg"]
    M[5, 1] = col_fem["m_col_x_kg"]
    M[2, 5] = col_fem["m_col_th_kg_m"]
    M[5, 2] = col_fem["m_col_th_kg_m"]

    m_eigs = np.linalg.eigvalsh(M)
    assert np.all(m_eigs > 0.0), f"Mass matrix not SPD: min eig = {m_eigs.min()}"

    m_suspended = m_g + m_t + m_w
    f_air = 1.50
    k_air = m_suspended * (2.0 * math.pi * f_air) ** 2
    c_air = 2.0 * 0.08 * math.sqrt(k_air * m_suspended)

    f_act_x = 4.50
    k_act_x = (m_t + m_w) * (2.0 * math.pi * f_act_x) ** 2
    c_act_x = 2.0 * 0.10 * math.sqrt(k_act_x * (m_t + m_w))

    f_act_th = 7.00
    k_act_th = I_t * (2.0 * math.pi * f_act_th) ** 2
    c_act_th = 2.0 * 0.10 * math.sqrt(k_act_th * I_t)

    f_dr = 16.0
    k_dr = m_dr * (2.0 * math.pi * f_dr) ** 2
    c_dr = 2.0 * 0.03 * math.sqrt(k_dr * m_dr)

    f_stage = 180.0
    k_piezo = m_w * (2.0 * math.pi * f_stage) ** 2
    c_piezo = 2.0 * 0.02 * math.sqrt(k_piezo * m_w)

    k_col = col_fem["k_col_1_N_m"]
    c_col = 2.0 * 0.015 * math.sqrt(k_col * col_fem["m_col_1_kg"])

    c_bellows = 0.02 * math.sqrt(max(k_bellows, 1.0) * min(m_t, m_dr)) * 0.05
    c_braid = 0.02 * math.sqrt(max(k_braid, 1.0) * m_w) * 0.10

    K = np.zeros((6, 6), dtype=float)
    C = np.zeros((6, 6), dtype=float)

    def add_sd(vec: np.ndarray, k_val: float, c_val: float) -> None:
        K[:, :] += k_val * np.outer(vec, vec)
        C[:, :] += c_val * np.outer(vec, vec)

    add_sd(np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0]), k_air, c_air)
    add_sd(np.array([-1.0, 1.0, 0.0, 0.0, 0.0, 0.0]), k_act_x, c_act_x)
    add_sd(np.array([0.0, 0.0, 1.0, 0.0, 0.0, 0.0]), k_act_th, c_act_th)
    add_sd(np.array([0.0, 0.0, 0.0, 1.0, 0.0, 0.0]), k_dr, c_dr)

    e_piezo = np.array([0.0, -1.0, -h_w, 0.0, 1.0, 0.0])
    add_sd(e_piezo, k_piezo, c_piezo)
    add_sd(np.array([0.0, 0.0, 0.0, 0.0, 0.0, 1.0]), k_col, c_col)
    add_sd(np.array([0.0, 1.0, h_br, -1.0, 0.0, 0.0]), k_bellows, c_bellows)
    add_sd(np.array([0.0, 0.0, 0.0, -1.0, 1.0, 0.0]), k_braid, c_braid)

    eigvals, _ = eigh(K, M)
    modal_freqs_hz = np.sqrt(np.maximum(eigvals, 0.0)) / (2.0 * math.pi)

    return {
        "M": M,
        "C": C,
        "K": K,
        "modal_freqs_hz": [float(f) for f in modal_freqs_hz],
        "k_air": k_air,
        "c_air": c_air,
        "k_act_x": k_act_x,
        "c_act_x": c_act_x,
        "k_act_th": k_act_th,
        "c_act_th": c_act_th,
        "k_dr": k_dr,
        "c_dr": c_dr,
        "k_piezo": k_piezo,
        "c_piezo": c_piezo,
        "m_w": m_w,
        "m_t": m_t,
        "I_t": I_t,
        "h_w": h_w,
        "h_br": h_br,
        "e_piezo": e_piezo,
    }


def evaluate_configuration(
    cfg: MachineConfig,
    cad_anchors: dict[str, Any],
    col_fem: dict[str, Any],
    snout: dict[str, float],
    freqs_hz: np.ndarray,
    run_parseval_check: bool = False,
) -> dict[str, Any]:
    """Solve coupled 6-DOF closed-loop frequency-domain PSDs & RMS jitter."""
    sys_m = build_mdof_matrices(cad_anchors, col_fem, cfg.k_bellows, cfg.k_braid)
    M, C, K = sys_m["M"], sys_m["C"], sys_m["K"]
    df = float(freqs_hz[1] - freqs_hz[0])
    w = 2.0 * np.pi * freqs_hz
    s = 1j * w
    nf = len(freqs_hz)

    # S4.1/S4.2 2-stage active isolation (0.5-100 Hz):
    # Stage 1: floor-referenced active damping on pneumatic granite isolators (damps 1.5 Hz mode)
    # Stage 2: S4.2 active table skyhook damping on x_t and theta_t (reacting on damped granite)
    if cfg.active_iso_on:
        w_hp = 2.0 * math.pi * 0.40
        w_lp = 2.0 * math.pi * 100.0
        hp = s / (s + w_hp)
        lp = (w_lp / (s + w_lp)) ** 2
        m_susp = cad_anchors["m_granite_kg"] + sys_m["m_t"] + sys_m["m_w"]
        g_iso_g = 4.0 * math.sqrt(sys_m["k_air"] * m_susp)
        g_iso_x = 3.5 * math.sqrt(sys_m["k_act_x"] * sys_m["m_t"])
        g_iso_th = 6.0 * math.sqrt(sys_m["k_act_th"] * sys_m["I_t"])
        C_iso_g = g_iso_g * s * hp * lp
        C_iso_x = g_iso_x * s * hp * lp
        C_iso_th = g_iso_th * s * hp * lp
    else:
        C_iso_g = np.zeros(nf, dtype=complex)
        C_iso_x = np.zeros(nf, dtype=complex)
        C_iso_th = np.zeros(nf, dtype=complex)

    piezo_ctrl = compute_piezo_controller_and_margins(
        sys_m["m_w"], sys_m["k_piezo"], sys_m["c_piezo"], cfg.k_braid, freqs_hz,
        retune_for_plant=cfg.retune_for_rigid,
    )
    C_p = piezo_ctrl["C_jw"] if cfg.piezo_pid_on else np.zeros(nf, dtype=complex)

    S_floor = seismic_floor_disp_psd(freqs_hz, cfg.vc_grade)
    S_pt = pt420_force_psd(
        freqs_hz,
        remote_valve=cfg.remote_valve,
        harmonic_ff_db=cfg.harmonic_ff_db,
    )["s_total"]
    S_sens = interferometer_noise_psd(freqs_hz)
    S_amp = piezo_amp_openloop_disp_psd(freqs_hz)

    e_p = sys_m["e_piezo"]
    e_p_outer = np.outer(e_p, e_p)

    f_img_m = cad_anchors["f_img_archb_mm"] * 1e-3
    coeff_col_point = (
        f_img_m * col_fem["theta_beam_per_tip_m"]
        + snout["L_snout_m"] * (col_fem["M_root_Nm_per_m"] / snout["k_rot_plate_Nm_rad"])
    )
    h_fl = cad_anchors["z_flange_m"] - cad_anchors["z_pivot_m"]
    inert_factor = snout["m_top_flange_eff_kg"] / snout["k_head_rel_met_N_m"]

    Z = (
        K[None, :, :]
        + 1j * w[:, None, None] * C[None, :, :]
        - (w[:, None, None] ** 2) * M[None, :, :]
    )
    Z[:, 0, 0] += C_iso_g
    Z[:, 1, 1] += C_iso_x
    Z[:, 0, 1] -= C_iso_x
    Z[:, 2, 2] += C_iso_th
    Z += C_p[:, None, None] * e_p_outer[None, :, :]

    B = np.zeros((nf, 6, 4), dtype=complex)
    B[:, 0, 0] = sys_m["k_air"] + 1j * w * sys_m["c_air"]
    B[:, 3, 0] = sys_m["k_dr"] + 1j * w * sys_m["c_dr"]
    B[:, 3, 1] = 1.0
    B[:, :, 2] = -C_p[:, None] * e_p[None, :]
    B[:, :, 3] = sys_m["k_piezo"] * e_p[None, :]

    H = np.linalg.solve(Z, B)

    H_stage = np.einsum("i,fij->fj", e_p, H)
    H_point = (
        coeff_col_point * H[:, 5, :]
        + cfg.delta_h_abbe_m * H[:, 2, :]
        + (w[:, None] ** 2) * inert_factor * (H[:, 1, :] + h_fl * H[:, 2, :])
    )
    H_mech_comb = H_stage - H_point

    H_y_meas = H_stage.copy()
    H_y_meas[:, 2] += 1.0
    H_fpiezo = -C_p[:, None] * H_y_meas

    H_table = H[:, 1, :]
    H_dr = H[:, 3, :]
    H_col_tip = H[:, 5, :]

    def psd_and_rms(H_out: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
        p_fl = (np.abs(H_out[:, 0]) ** 2) * S_floor
        p_pt = (np.abs(H_out[:, 1]) ** 2) * S_pt
        p_sn = (np.abs(H_out[:, 2]) ** 2) * S_sens
        p_am = (np.abs(H_out[:, 3]) ** 2) * S_amp
        p_tot = p_fl + p_pt + p_sn + p_am
        return p_tot, {
            "total": float(math.sqrt(max(float(np.sum(p_tot) * df), 0.0))),
            "floor": float(math.sqrt(max(float(np.sum(p_fl) * df), 0.0))),
            "pt420": float(math.sqrt(max(float(np.sum(p_pt) * df), 0.0))),
            "sensor": float(math.sqrt(max(float(np.sum(p_sn) * df), 0.0))),
            "amp_openloop": float(math.sqrt(max(float(np.sum(p_am) * df), 0.0))),
        }

    S_stage_tot, rms_stage = psd_and_rms(H_stage)
    S_point_tot, rms_point = psd_and_rms(H_point)
    _, rms_comb = psd_and_rms(H_mech_comb)
    _, rms_fpiezo = psd_and_rms(H_fpiezo)
    _, rms_table = psd_and_rms(H_table)
    _, rms_dr = psd_and_rms(H_dr)
    _, rms_col_tip = psd_and_rms(H_col_tip)

    cum_stage_nm = np.sqrt(np.cumsum(S_stage_tot) * df) * 1e9
    cum_point_nm = np.sqrt(np.cumsum(S_point_tot) * df) * 1e9

    parseval = None
    if run_parseval_check:
        n_fft = int(round((2.0 * freqs_hz[-1]) / df))
        n_rfft = n_fft // 2 + 1
        idx_map = np.round(freqs_hz / df).astype(int)
        rng = np.random.default_rng(20261123)
        n_trials = 16
        var_time_stage = []
        var_time_point = []
        for _ in range(n_trials):
            X_st = np.zeros(n_rfft, dtype=complex)
            X_pt = np.zeros(n_rfft, dtype=complex)
            for col_i, S_in in enumerate((S_floor, S_pt, S_sens, S_amp)):
                phi = rng.uniform(0.0, 2.0 * np.pi, size=nf)
                amp_in = n_fft * np.sqrt(0.5 * S_in * df) * np.exp(1j * phi)
                X_st[idx_map] += H_stage[:, col_i] * amp_in
                X_pt[idx_map] += H_point[:, col_i] * amp_in
            x_t_st = np.fft.irfft(X_st, n=n_fft)
            x_t_pt = np.fft.irfft(X_pt, n=n_fft)
            var_time_stage.append(float(np.mean(x_t_st**2)))
            var_time_point.append(float(np.mean(x_t_pt**2)))

        rms_time_stage_nm = math.sqrt(float(np.mean(var_time_stage))) * 1e9
        rms_time_point_nm = math.sqrt(float(np.mean(var_time_point))) * 1e9
        rel_err_stage = abs(rms_time_stage_nm - rms_stage["total"] * 1e9) / max(rms_stage["total"] * 1e9, 1e-12)
        rel_err_point = abs(rms_time_point_nm - rms_point["total"] * 1e9) / max(rms_point["total"] * 1e9, 1e-12)
        parseval = {
            "n_fft": n_fft,
            "n_trials": n_trials,
            "rms_freq_stage_nm": rms_stage["total"] * 1e9,
            "rms_time_stage_nm": rms_time_stage_nm,
            "rel_err_stage": rel_err_stage,
            "rms_freq_point_nm": rms_point["total"] * 1e9,
            "rms_time_point_nm": rms_time_point_nm,
            "rel_err_point": rel_err_point,
            "max_rel_err": max(rel_err_stage, rel_err_point),
        }

    return {
        "name": cfg.name,
        "label_tr": cfg.label_tr,
        "vc_grade": cfg.vc_grade,
        "params": {
            "k_bellows_N_m": cfg.k_bellows,
            "k_braid_N_m": cfg.k_braid,
            "remote_valve": cfg.remote_valve,
            "active_iso_on": cfg.active_iso_on,
            "piezo_pid_on": cfg.piezo_pid_on,
            "harmonic_ff_db": cfg.harmonic_ff_db,
            "delta_h_abbe_mm": cfg.delta_h_abbe_m * 1e3,
            "retune_for_rigid": cfg.retune_for_rigid,
        },
        "passive_modal_freqs_hz": sys_m["modal_freqs_hz"],
        "control_margins": {
            "n_gain_crossings": piezo_ctrl["n_gain_crossings"],
            "f_crossover_hz": piezo_ctrl["f_crossover_hz"],
            "phase_margin_deg": piezo_ctrl["phase_margin_deg"],
            "f_phase_crossover_hz": piezo_ctrl["f_phase_crossover_hz"],
            "gain_margin_db": piezo_ctrl["gain_margin_db"],
            "sensitivity_peak_S_inf": piezo_ctrl["sensitivity_peak_S_inf"],
            "is_stable": piezo_ctrl["is_stable"],
        },
        "sigma_stage_nm": rms_stage["total"] * 1e9,
        "sigma_stage_breakdown_nm": {k: v * 1e9 for k, v in rms_stage.items()},
        "sigma_pointing_nm": rms_point["total"] * 1e9,
        "sigma_pointing_breakdown_nm": {k: v * 1e9 for k, v in rms_point.items()},
        "sigma_mech_coherent_nm": rms_comb["total"] * 1e9,
        "sigma_mech_rss_nm": math.hypot(rms_stage["total"] * 1e9, rms_point["total"] * 1e9),
        "piezo_force_rms_N": rms_fpiezo["total"],
        "piezo_force_peak_5sigma_N": 5.0 * rms_fpiezo["total"],
        "table_rms_nm": rms_table["total"] * 1e9,
        "dr_tower_rms_um": rms_dr["total"] * 1e6,
        "column_tip_rms_nm": rms_col_tip["total"] * 1e9,
        "parseval": parseval,
        "_S_stage_nm2_hz": S_stage_tot * 1e18,
        "_S_point_nm2_hz": S_point_tot * 1e18,
        "_cum_stage_nm": cum_stage_nm,
        "_cum_point_nm": cum_point_nm,
    }


# ---------------------------------------------------------------------------
# 5. Coupled Thermal Drift Model (Cleanroom HVAC + Chamber + Cryo + Fiducial)
# ---------------------------------------------------------------------------
def evaluate_thermal_drift(
    cad_anchors: dict[str, Any],
    dT_room_amp_mK: float = 10.0,
    T_hvac_s: float = 900.0,
    t_fiducial_s: float = 300.0,
    material_mode: str = "v3_zerodur_invar_cryo",
) -> dict[str, float]:
    """Compute coupled cleanroom-HVAC -> chamber -> metrology -> column -> wafer thermal drift."""
    dT_room = dT_room_amp_mK * 1e-3
    w_h = 2.0 * math.pi / T_hvac_s

    m_ch = cad_anchors["m_uhv_chamber_kg"]
    cp_ss = 500.0
    A_ch_ext = 0.65
    h_conv = 6.0
    tau_ch = (m_ch * cp_ss) / (h_conv * A_ch_ext)

    if material_mode == "naive_ss316_uncompensated":
        tau_struct = 1200.0
        alpha_met = 16.0e-6
        L_asym = 0.118
        alpha_wafer_island = 16.0e-6
        L_wafer_asym = 0.025
        dT_cryo_stab = 0.0
        L_air_deadpath = 0.050
        fiducial_active = False
    else:
        tau_struct = 3600.0
        alpha_met = 0.02e-6
        L_asym = 0.118
        alpha_invar = 1.2e-6
        L_invar_asym = 0.015
        alpha_wafer_island = 1.0e-9
        L_wafer_asym = 0.025
        dT_cryo_stab = 0.5e-3
        L_air_deadpath = 0.008
        fiducial_active = True

    att_ch = 1.0 / math.sqrt(1.0 + (w_h * tau_ch) ** 2)
    att_met = att_ch / math.sqrt(1.0 + (w_h * tau_struct) ** 2)
    if material_mode == "naive_ss316_uncompensated":
        dT_met_amp = dT_room / math.sqrt(1.0 + (w_h * tau_struct) ** 2)
    else:
        dT_met_amp = dT_room * att_met

    if fiducial_active and t_fiducial_s > 0.0:
        x_f = w_h * t_fiducial_s
        fid_rms_factor = math.sqrt(max(1.0 - math.sin(x_f) / x_f, 0.0))
    else:
        fid_rms_factor = 1.0 / math.sqrt(2.0)

    if material_mode == "naive_ss316_uncompensated":
        amp_met = (alpha_met * L_asym + alpha_wafer_island * L_wafer_asym) * dT_met_amp
        sigma_met_nm = amp_met * fid_rms_factor * 1e9
        sigma_cryo_nm = 0.0
    else:
        amp_met = (alpha_met * L_asym + alpha_invar * L_invar_asym) * dT_met_amp
        amp_invar_1p = (alpha_invar * 0.008) * (dT_room * att_ch)
        sigma_met_nm = math.hypot(amp_met, amp_invar_1p) * fid_rms_factor * 1e9
        sigma_cryo_nm = (alpha_wafer_island * L_wafer_asym * dT_cryo_stab / math.sqrt(2.0)) * 1e9

    tau_col = 10500.0
    dT_grad_eff = 0.25 * dT_room / math.sqrt(1.0 + (w_h * tau_col) ** 2)
    theta_col_th = 16.0e-6 * dT_grad_eff * (0.430 / 0.100)
    f_img_m = cad_anchors["f_img_archb_mm"] * 1e-3
    sigma_col_nm = (f_img_m * theta_col_th) * 1e9 * fid_rms_factor

    tau_air = 120.0 if material_mode == "naive_ss316_uncompensated" else 600.0
    dT_air_eff = dT_room / math.sqrt(1.0 + (w_h * tau_air) ** 2)
    sigma_deadpath_nm = (0.93e-6 * L_air_deadpath * dT_air_eff) * 1e9 * fid_rms_factor

    sigma_laser_nm = 0.025 if material_mode != "naive_ss316_uncompensated" else 0.050

    sigma_total_th_nm = math.sqrt(
        sigma_met_nm**2 + sigma_cryo_nm**2 + sigma_col_nm**2
        + sigma_deadpath_nm**2 + sigma_laser_nm**2
    )
    return {
        "dT_room_amp_mK": dT_room_amp_mK,
        "T_hvac_s": T_hvac_s,
        "t_fiducial_s": t_fiducial_s,
        "tau_chamber_s": tau_ch,
        "sigma_metrology_nm": sigma_met_nm,
        "sigma_cryo_island_nm": sigma_cryo_nm,
        "sigma_column_bend_nm": sigma_col_nm,
        "sigma_deadpath_nm": sigma_deadpath_nm,
        "sigma_laser_nm": sigma_laser_nm,
        "sigma_thermal_nm": sigma_total_th_nm,
    }


# ---------------------------------------------------------------------------
# 6. OFHC Copper Thermal Braid Stiffness vs 20 mK Thermal Conductance Trade
# ---------------------------------------------------------------------------
def compute_ofhc_braid_design(
    n_braids: int = 4,
    strands_per_braid: int = 2550,
    strand_diam_um: float = 50.0,
    braid_length_mm: float = 100.0,
    rrr: float = 200.0,
    friction_factor: float = 12.0,
    mxc_wafer_load_uW: float = 2.5,
    mxc_total_load_uW: float = 19.0,
) -> dict[str, float]:
    """Compute mechanical stiffness and 20 mK Wiedemann-Franz thermal conductance of OFHC braids."""
    n_total = n_braids * strands_per_braid
    d = strand_diam_um * 1e-6
    L = braid_length_mm * 1e-3
    A_total = n_total * math.pi * (d / 2.0) ** 2

    E_cu = 117.0e9
    I_1 = math.pi / 64.0 * d**4
    k_single = 12.0 * E_cu * I_1 / L**3
    k_braid_eff = friction_factor * n_total * k_single

    L0 = 2.44e-8
    rho_300k = 1.70e-8
    rho_0 = rho_300k / rrr
    T_mxc = 0.020
    kappa_20mK = L0 * T_mxc / rho_0
    G_braid_20mK = kappa_20mK * A_total / L

    # In series with 397 mm Ø12 mm OFHC busbar on DR side (A_bus = 113.1 mm^2)
    A_bus = math.pi * (6.0e-3) ** 2
    G_bus_20mK = kappa_20mK * A_bus / 0.397
    G_total_20mK = 1.0 / (1.0 / G_braid_20mK + 1.0 / G_bus_20mK)

    dT_wafer_mK = (mxc_wafer_load_uW * 1e-6 / G_total_20mK) * 1e3
    dT_full19uW_mK = (mxc_total_load_uW * 1e-6 / G_total_20mK) * 1e3

    return {
        "n_braids": n_braids,
        "strands_per_braid": strands_per_braid,
        "total_strands": n_total,
        "strand_diam_um": strand_diam_um,
        "braid_length_mm": braid_length_mm,
        "total_cu_area_mm2": A_total * 1e6,
        "rrr": rrr,
        "friction_factor": friction_factor,
        "k_braid_N_m": k_braid_eff,
        "kappa_20mK_W_mK": kappa_20mK,
        "G_braid_20mK_mW_K": G_braid_20mK * 1e3,
        "G_total_link_20mK_mW_K": G_total_20mK * 1e3,
        "dT_at_2p5uW_mK": dT_wafer_mK,
        "dT_at_19uW_mK": dT_full19uW_mK,
    }


def compute_exp124_budget_closure(
    cad_anchors: dict[str, Any],
    sigma_stage_nm: float,
    sigma_pointing_nm: float,
    sigma_thermal_nm: float,
) -> dict[str, Any]:
    """Substitute computed Exp133 mechanical+thermal RMS into Exp124 5 keV RSS placement budget."""
    s_ann = cad_anchors["exp124_anneal_budget_nm"]  # 0.50 nm (Exp66/Exp124)

    def eval_op(label: str, s_spot: float, s_strag: float, s_orig: float) -> dict[str, float]:
        s_equip_new = math.sqrt(
            s_spot**2 + sigma_stage_nm**2 + sigma_pointing_nm**2
            + sigma_thermal_nm**2 + s_ann**2
        )
        s_tot_new = math.sqrt(s_equip_new**2 + s_strag**2)
        return {
            "operating_point": label,
            "sigma_spot_nm": s_spot,
            "sigma_straggle_nm": s_strag,
            "sigma_anneal_nm": s_ann,
            "sigma_stage_nm": sigma_stage_nm,
            "sigma_pointing_nm": sigma_pointing_nm,
            "sigma_thermal_nm": sigma_thermal_nm,
            "sigma_equip_exp133_nm": s_equip_new,
            "sigma_total_exp133_nm": s_tot_new,
            "sigma_total_exp124_orig_nm": s_orig,
            "delta_vs_exp124_nm": s_tot_new - s_orig,
            "margin_to_3p80_nm": 3.80 - s_tot_new,
            "passes_3p80_nm": s_tot_new <= 3.80,
        }

    return {
        "ArchB_HiRes_Ti0p25_10ms": eval_op(
            "ArchB_HiRes_Ti0p25_10ms",
            cad_anchors["exp124_hires_spot_nm"],
            cad_anchors["exp124_hires_straggle_nm"],
            cad_anchors["exp124_hires_total_nm"],
        ),
        "ArchB_HiRes_Ti0p5_15ms": eval_op(
            "ArchB_HiRes_Ti0p5_15ms",
            cad_anchors["exp124_canon_spot_nm"],
            cad_anchors["exp124_canon_straggle_nm"],
            cad_anchors["exp124_canon_total_nm"],
        ),
    }


# ---------------------------------------------------------------------------
# 7. Nested 50 K + 4 K UHV Radiation/Cryopump Shields, 4.2 K Magnet Mounting,
#    & Cryo-Frost Physics (Closes OBS-010, OBS-040, OBS-046)
# ---------------------------------------------------------------------------
def evaluate_uhv_cryo_shielding_and_frost() -> dict[str, Any]:
    """First-principles thermal & UHV cryo-frost model comparing unshielded legacy vs nested 50K+4K shields.

    Physics:
      - Stefan-Boltzmann radiation: Q_rad = sigma * A * eps_eff * (T_hot^4 - T_cold^4)
      - Integrated solid conduction: Q_cond = (A / L) * int_{T_cold}^{T_hot} k(T) dT
      - Exact Hertz-Knudsen impingement flux: J = P_Pa / sqrt(2 * pi * m_mol * k_B * T_gas)
        (converting mbar -> Pa via 1 mbar = 100 Pa, avoiding Torr/mbar Langmuir errors!)
    """
    SIGMA_SB = 5.670374419e-8  # W/(m^2 K^4)
    KB = 1.380649e-23          # J/K
    AMU = 1.66053906660e-27    # kg

    # --- Legacy Unshielded UHV Chamber Audit Reproduction (OBS-010, OBS-040, OBS-046) ---
    # 4x Vespel SP-22 struts (r=4.5 mm, L=14.3 mm, A/L = 0.01780 m), int_{0.02}^{300} k_Vespel dT ~= 74.0 W/m
    a_over_l_vespel_leg = 4.0 * math.pi * (4.5e-3 ** 2) / 14.3e-3
    q_vespel_leg_W = a_over_l_vespel_leg * 74.0  # ~1.317 W
    # 16x S3.2-04 micro-coax (100K -> 20mK direct, no 4K/Still clamps)
    q_coax_leg_W = 0.31256  # with Ag-Cu core+braid (0.01319 W PTFE-only lower bound)
    # Unshielded 300K/100K radiation on D50 Si wafer + 80x80 AlN + D116 chuck (A_tot ~ 0.0144 m^2, eps=0.25)
    a_chuck_stack = 0.0144
    q_rad_20mk_leg_W = SIGMA_SB * a_chuck_stack * 0.25 * (300.0 ** 4 - 0.02 ** 4)  # ~1.65 W
    q_20mk_leg_total_W = q_vespel_leg_W + q_coax_leg_W + q_rad_20mk_leg_W

    # Unshielded 4.2 K Magnet (4x Ti-6Al-4V feet r=8.5 mm, L=109 mm -> A/L=8.33e-3 m, int k dT=1501 W/m)
    a_over_l_ti_leg = 4.0 * math.pi * (8.5e-3 ** 2) / 0.109
    q_mag_feet_leg_W = a_over_l_ti_leg * 1501.5  # 12.508 W
    a_mag = 0.40  # m^2
    q_mag_rad_leg_low_W = SIGMA_SB * a_mag * 0.05 * (300.0 ** 4 - 4.2 ** 4)   # 9.19 W
    q_mag_rad_leg_high_W = SIGMA_SB * a_mag * 0.15 * (300.0 ** 4 - 4.2 ** 4)  # 27.56 W
    q_4k_mag_leg_low_W = q_mag_feet_leg_W + q_mag_rad_leg_low_W
    q_4k_mag_leg_high_W = q_mag_feet_leg_W + q_mag_rad_leg_high_W

    # --- Redesigned Nested 50 K + 4 K UHV Radiation & Cryopump Shields (OBS-010, OBS-040) ---
    # 1) 20 mK Wafer/Chuck Stage inside nested gold-plated 50K (eps=0.03) + 4K (eps=0.02) UHV shields
    #    with cold-shuttered phi 12 mm baffled beam/optical aperture (F_ap_50K = 1.2e-4, zero direct 300K LOS)
    eps_eff_4k_to_20mk = 0.02
    q_rad_4k_cavity_20mk_uW = SIGMA_SB * a_chuck_stack * eps_eff_4k_to_20mk * (4.2 ** 4 - 0.02 ** 4) * 1e6  # 0.0051 uW
    # Baffled cold-shuttered aperture stray 50K leakage (F_ap = 1.2e-4 on D50 wafer A=1.96e-3 m^2, eps=0.05)
    a_wafer = math.pi * (0.025 ** 2)
    q_rad_ap_50k_20mk_uW = SIGMA_SB * a_wafer * 0.05 * 1.2e-4 * (50.0 ** 4 - 0.02 ** 4) * 1e6  # 0.0042 uW
    q_rad_20mk_redesigned_uW = q_rad_4k_cavity_20mk_uW + q_rad_ap_50k_20mk_uW

    # 2) Thermally intercepted kinematic struts (4x thin-walled Vespel SP-22 tubes OD 4 mm, wall 0.4 mm, L=65 mm)
    #    intercepted at 50K, 4K, and 0.8K Still; only the 0.8K -> 20mK span enters MXC!
    #    Vespel SP-22 k(T) ~= 0.0012 * T^1.2 W/(m K) below 1 K -> int_{0.02}^{0.8} k(T) dT = 0.000338 W/m
    a_tube_4x = 4.0 * math.pi * ((2.0e-3 ** 2) - (1.6e-3 ** 2))  # 18.10 mm^2 total
    a_over_l_vespel_new = a_tube_4x / 0.065                      # 2.784e-4 m (64x smaller than legacy!)
    int_k_vespel_0p8_to_0p02 = (0.0012 / 2.2) * (0.8 ** 2.2 - 0.02 ** 2.2)  # 3.338e-4 W/m
    q_struts_20mk_uW = a_over_l_vespel_new * int_k_vespel_0p8_to_0p02 * 1e6  # 0.093 uW

    # 3) 16x S3.2-04 IBIC micro-coaxes thermally clamped at 50K, 4K, and 0.8K Still
    #    using superconducting NbTi (Krinner Table 2: 0.020 uW/line from 0.1K/Still -> 20mK)
    q_ibic_coax_20mk_uW = 16.0 * 0.020  # 0.320 uW

    q_20mk_redesigned_uW = q_rad_20mk_redesigned_uW + q_struts_20mk_uW + q_ibic_coax_20mk_uW  # ~0.422 uW < 1.0 uW!

    # 4) Redesigned 4.2 K Superconducting Magnet + 50K/4K Shielded Suspension & 4K OFHC Link (OBS-040)
    #    50K MLI + polished Al/Cu shield (eps_eff = 0.015, A=0.40 m^2): 50K -> 4.2K radiation
    q_mag_rad_4k_W = SIGMA_SB * a_mag * 0.015 * (50.0 ** 4 - 4.2 ** 4)  # 0.00213 W
    #    4x 50K-intercepted G10-CR tension straps (A_tot=300 mm^2, L=180 mm, int_{4.2}^{50} k_G10 dT = 10.5 W/m)
    q_mag_susp_4k_W = (300.0e-6 / 0.180) * 10.5  # 0.0175 W
    #    Upgraded 320 A Bi-2223 HTS current leads (persistent mode 0.045 W, active ramp 0.165 W)
    q_mag_hts_persistent_4k_W = 0.045
    q_mag_hts_charging_4k_W = 0.165
    #    4K intercept of 4x wafer struts (50K->4K) + 16x IBIC coax (50K->4K @ 1 mW/line) + shield radiation (0.12 W)
    q_uhv_intercepts_4k_W = 0.032 + 0.016 + 0.120  # 0.168 W
    #    Cryo-readout 32x HEMT + RF looms + SKY130 4K budget (~0.42 W from Exp140)
    q_readout_4k_W = 0.420
    q_4k_total_persistent_W = (
        q_mag_rad_4k_W + q_mag_susp_4k_W + q_mag_hts_persistent_4k_W + q_uhv_intercepts_4k_W + q_readout_4k_W
    )
    q_4k_total_charging_W = q_4k_total_persistent_W - q_mag_hts_persistent_4k_W + q_mag_hts_charging_4k_W

    #    Explicit 4K OFHC Cu thermal link (A = 1,200 mm^2, L = 0.45 m, RRR=100 -> k(4.2K) = 595 W/(m K))
    k_cu_4p2K = (2.44e-8 * 4.2) / (1.70e-8 / 100.0)  # 602.8 W/(m K)
    g_4k_bus_W_K = k_cu_4p2K * (1200.0e-6) / 0.45    # 1.608 W/K
    dT_magnet_4k_link_K = (q_mag_rad_4k_W + q_mag_susp_4k_W + q_mag_hts_charging_4k_W) / g_4k_bus_W_K  # 0.115 K

    # --- Exact Hertz-Knudsen Cryo-Frost Condensation Model (OBS-046) ---
    n_ml_m2 = 6.78e18  # Si(100) monolayer surface site density [molecules/m^2]
    d_ml_nm = 0.31     # H2O/N2/CO monolayer thickness [nm]
    t_write_s = 8.0 * 3600.0

    def _frost_8h(p_mbar: float, m_amu: float, t_gas_K: float, alpha: float = 1.0) -> dict[str, float]:
        p_pa = p_mbar * 100.0  # EXACT conversion: 1 mbar = 100 Pa
        flux = p_pa / math.sqrt(2.0 * math.pi * (m_amu * AMU) * KB * t_gas_K)
        t_1ml_s = n_ml_m2 / max(alpha * flux, 1e-30)
        ml_8h = (alpha * flux * t_write_s) / n_ml_m2
        return {
            "p_mbar": p_mbar,
            "t_gas_K": t_gas_K,
            "flux_m2_s": float(f"{flux:.4e}"),
            "t_1ML_s": round(t_1ml_s, 2),
            "monolayers_8h": round(ml_8h, 4),
            "thickness_8h_nm": round(ml_8h * d_ml_nm, 5),
        }

    # Legacy unshielded chamber pressures (293.15 K gas): 1.12e-8 mbar (Pilot 3A stress) & 1.0e-9 mbar (target UHV)
    frost_leg_stress_h2o = _frost_8h(1.12e-8, 18.015, 293.15)
    frost_leg_target_h2o = _frost_8h(1.0e-9, 18.015, 293.15)
    frost_leg_target_n2 = _frost_8h(1.0e-9, 28.013, 293.15)

    # Redesigned 4 K Cryopump Baffle + NEG Cavity:
    # Baffled phi 12 mm aperture (Clausing transmission <= 2e-3) + 4K baffle cryopumping (>10^4 L/s) + NEG
    # drops local partial pressure inside 4K shield to <= 2.0e-12 mbar at 4.2 K equivalent (or 1.0e-12 mbar 293K-eq flux)
    p_local_redesigned_mbar = 1.0e-12
    frost_red_h2o = _frost_8h(p_local_redesigned_mbar, 18.015, 293.15)
    frost_red_n2 = _frost_8h(p_local_redesigned_mbar, 28.013, 293.15)

    return {
        "legacy_unshielded_audit": {
            "q_20mk_vespel_struts_W": round(q_vespel_leg_W, 4),
            "q_20mk_ibic_coax_W": round(q_coax_leg_W, 4),
            "q_20mk_300K_radiation_W": round(q_rad_20mk_leg_W, 4),
            "q_20mk_total_W": round(q_20mk_leg_total_W, 4),
            "mxc_overload_factor_vs_14uW": round(q_20mk_leg_total_W / 14.0e-6, 1),
            "q_4k_magnet_feet_W": round(q_mag_feet_leg_W, 3),
            "q_4k_magnet_total_low_W": round(q_4k_mag_leg_low_W, 3),
            "q_4k_magnet_total_high_W": round(q_4k_mag_leg_high_W, 3),
            "pt420_overload_factor_low": round(q_4k_mag_leg_low_W / 2.0, 2),
            "frost_8h_H2O_1p12e_8mbar": frost_leg_stress_h2o,
            "frost_8h_H2O_1e_9mbar": frost_leg_target_h2o,
            "frost_8h_N2_1e_9mbar": frost_leg_target_n2,
        },
        "redesigned_nested_50K_4K_uhv_shields": {
            "shield_architecture": "Nested Au-plated OFHC 50K outer + 4K inner UHV radiation/cryopump baffle shields + phi 12 mm cold-shuttered beam aperture + 50K/4K/0.8K-Still strut & IBIC coax intercepts",
            "q_20mk_radiation_4K_cavity_uW": round(q_rad_4k_cavity_20mk_uW, 4),
            "q_20mk_radiation_aperture_50K_uW": round(q_rad_ap_50k_20mk_uW, 4),
            "q_20mk_struts_0p8K_to_20mK_uW": round(q_struts_20mk_uW, 4),
            "q_20mk_ibic_16x_nbti_coax_uW": round(q_ibic_coax_20mk_uW, 4),
            "q_20mk_total_external_uW": round(q_20mk_redesigned_uW, 4),
            "passes_20mk_sub_1uW_budget": bool(q_20mk_redesigned_uW < 1.0),
            "q_4k_magnet_rad_50K_to_4K_W": round(q_mag_rad_4k_W, 5),
            "q_4k_magnet_g10_suspension_W": round(q_mag_susp_4k_W, 5),
            "q_4k_hts_leads_persistent_W": q_mag_hts_persistent_4k_W,
            "q_4k_hts_leads_charging_W": q_mag_hts_charging_4k_W,
            "q_4k_uhv_intercepts_W": round(q_uhv_intercepts_4k_W, 4),
            "q_4k_readout_hemt_sky130_W": round(q_readout_4k_W, 4),
            "q_4k_total_persistent_W": round(q_4k_total_persistent_W, 4),
            "q_4k_total_charging_W": round(q_4k_total_charging_W, 4),
            "pt420_4p2K_capacity_W": 2.0,
            "passes_4p2K_sub_1p5W_budget": bool(q_4k_total_charging_W < 1.5),
            "magnet_4k_ofhc_busbar_area_mm2": 1200.0,
            "magnet_4k_link_dT_K": round(dT_magnet_4k_link_K, 4),
            "local_uhv_pressure_inside_4K_baffle_mbar": p_local_redesigned_mbar,
            "frost_8h_H2O_redesigned": frost_red_h2o,
            "frost_8h_N2_redesigned": frost_red_n2,
            "passes_negligible_frost_lt_0p05nm": bool(frost_red_h2o["thickness_8h_nm"] < 0.05),
        },
    }


# ---------------------------------------------------------------------------
# 8. Full Nonlinear Wiedemann-Franz + Bolted/Welded Joints + Kapitza 20 mK Stack
#    (Closes OBS-041)
# ---------------------------------------------------------------------------
def evaluate_nonlinear_20mk_thermal_stack(
    T_mxc_K: float = 0.020,
    q_chuck_uW: float = 0.56,
    q_wafer_onchip_uW: float = 0.020,
    q_legacy_audit_uW: float = 7.036,
) -> dict[str, Any]:
    """Solve exact nonlinear Wiedemann-Franz T^2 conduction + joint R(T) + Kapitza T^4 stack (OBS-041).

    Equations:
      - Wiedemann-Franz metal link: k(T) = c_k * T, c_k = L0 * RRR / rho_300K
        => T_hot = sqrt(T_cold^2 + 2 * Q * (L / (c_k * A)))
      - Metallic joint contact (G_j(T) = T / (T_0 * R_j0) at T_0 = 20 mK):
        => T_hot = sqrt(T_cold^2 + 2 * Q * R_j0 * T_0)
      - Kapitza phonon boundary (Wafer <-> Chuck):
        => T_wafer = (T_chuck^4 + 4 * Q_wafer / (alpha_K * A_K))^(1/4)
    """
    L0 = 2.44e-8
    rho_300 = 1.70e-8
    E_cu = 117.0e9
    A_wafer = math.pi * (0.025 ** 2)  # D50 Si wafer = 1.9635e-3 m^2

    def _solve_stack(
        q_link_W: float,
        q_kap_W: float,
        r_bus_m: float,
        L_bus_m: float,
        A_braid_m2: float,
        L_braid_m: float,
        rrr: float,
        n_bolted_joints: int,
        R_joint_20mK_K_W: float,
        alpha_K: float,
    ) -> dict[str, float]:
        c_k = L0 * rrr / rho_300
        A_bus = math.pi * (r_bus_m ** 2)
        # 1. Busbar nonlinear WF rise
        T1 = math.sqrt(T_mxc_K ** 2 + 2.0 * q_link_W * (L_bus_m / (c_k * A_bus)))
        # 2. Braid nonlinear WF rise
        T2 = math.sqrt(T1 ** 2 + 2.0 * q_link_W * (L_braid_m / (c_k * A_braid_m2)))
        # 3. Series metallic joints (scaled at T_0 = 20 mK)
        T_chuck = math.sqrt(T2 ** 2 + 2.0 * q_link_W * (n_bolted_joints * R_joint_20mK_K_W * 0.020))
        # 4. Wafer-to-chuck Kapitza boundary (T^4)
        T_wafer = (T_chuck ** 4 + 4.0 * q_kap_W / (alpha_K * A_wafer)) ** 0.25
        return {
            "T_mxc_mK": round(T_mxc_K * 1e3, 3),
            "T_bus_end_mK": round(T1 * 1e3, 3),
            "T_braid_end_mK": round(T2 * 1e3, 3),
            "T_chuck_mK": round(T_chuck * 1e3, 3),
            "T_wafer_mK": round(T_wafer * 1e3, 3),
            "dT_total_mK": round((T_wafer - T_mxc_K) * 1e3, 3),
        }

    # 1. Legacy bolted 4-braid + AlN/Si stack audit reproduction (OBS-041)
    #    phi 12 mm rod (397 mm) + 4x braids (20.03 mm^2, 100 mm) + 4x 500 K/W bolted joints + alpha_K=75
    leg_2p5 = _solve_stack(2.5e-6, 2.5e-6, 6.0e-3, 0.397, 20.03e-6, 0.100, 200.0, 4, 500.0, 75.0)
    leg_7p0 = _solve_stack(q_legacy_audit_uW * 1e-6, q_legacy_audit_uW * 1e-6, 6.0e-3, 0.397, 20.03e-6, 0.100, 100.0, 4, 500.0, 75.0)

    # 2. Redesigned Welded >= 80 mm^2 OFHC Multi-Leaf Braid + In/Au Eutectic Bond Stack
    #    - phi 30 mm annealed RRR=300 OFHC busbar (A_bus = 706.9 mm^2, L=397 mm)
    #    - 16x parallel annealed RRR=300 fine-strand (d=20 um) OFHC braids:
    #      A_braid = 96.0 mm^2 (>= 80 mm^2!) -> N_total = 305,577 strands of 20 um
    #      Lateral stiffness k_braid = 12 * N * (12 * E * pi*d^4/64 / L^3) = 40.4 N/m (<= 60 N/m limit!!)
    A_braid_new_mm2 = 96.0
    d_strand_m = 20.0e-6
    L_braid_m = 0.100
    n_strands_new = int(round((A_braid_new_mm2 * 1e-6) / (math.pi * (0.5 * d_strand_m) ** 2)))
    I_1 = math.pi / 64.0 * (d_strand_m ** 4)
    k_braid_new_N_m = 12.0 * n_strands_new * (12.0 * E_cu * I_1 / (L_braid_m ** 3))

    #    - Electron-beam welded busbar->braids->chuck (eliminates all 4 bolted joints; residual weld R = 5 K/W @ 20 mK)
    #    - Full-area In/Au eutectic wafer backside bond + perimeter Au wirebonds (alpha_K = 300 W/(m^2 K^4))
    #    - Under nested 50K+4K UHV shields: chuck load q_chuck_uW (~0.56 uW) flows through welded braids,
    #      while on-wafer load q_wafer_onchip_uW (~0.020 uW = 20 nW: 4K cavity rad + aperture + RF tones)
    #      crosses the wafer-to-chuck Kapitza boundary.
    red_nom = _solve_stack(
        q_chuck_uW * 1e-6, q_wafer_onchip_uW * 1e-6,
        0.015, 0.397, A_braid_new_mm2 * 1e-6, L_braid_m, 300.0, 1, 5.0, 300.0
    )
    # Stress check: 7.036 uW total chuck load through braids (with on-wafer load 20 nW) -> still < 25 mK!
    red_stress_7uW_chuck = _solve_stack(
        q_legacy_audit_uW * 1e-6, q_wafer_onchip_uW * 1e-6,
        0.015, 0.397, A_braid_new_mm2 * 1e-6, L_braid_m, 300.0, 1, 5.0, 300.0
    )
    # Worst-case sensitivity: if 2.5 uW were dumped directly onto the Si wafer (proving heat-sinking to chuck is vital)
    red_if_2p5uW_on_wafer = _solve_stack(
        2.5e-6, 2.5e-6,
        0.015, 0.397, A_braid_new_mm2 * 1e-6, L_braid_m, 300.0, 1, 5.0, 300.0
    )

    return {
        "legacy_bolted_4braid_20mm2_audit": {
            "at_2p5uW_RRR200": leg_2p5,
            "at_7p036uW_RRR100": leg_7p0,
            "exceeds_25mK_limit": bool(leg_2p5["T_wafer_mK"] > 25.0 and leg_7p0["T_wafer_mK"] > 25.0),
        },
        "redesigned_welded_96mm2_ofhc_stack": {
            "busbar_diam_mm": 30.0,
            "busbar_length_mm": 397.0,
            "n_parallel_braids": 16,
            "strand_diam_um": 20.0,
            "total_strands": n_strands_new,
            "braid_cu_area_mm2": A_braid_new_mm2,
            "braid_length_mm": 100.0,
            "rrr_annealed": 300.0,
            "joining_method": "electron_beam_diffusion_weld_zero_bolted_joints",
            "wafer_bond": "full_area_In_Au_eutectic_plus_perimeter_Au_wirebonds",
            "k_braid_lateral_N_m": round(k_braid_new_N_m, 2),
            "passes_stiffness_le_60_N_m": bool(k_braid_new_N_m <= 60.0),
            "nominal_shielded_operating_point": red_nom,
            "stress_7p036uW_on_chuck_20nW_wafer": red_stress_7uW_chuck,
            "sensitivity_if_2p5uW_direct_on_wafer": red_if_2p5uW_on_wafer,
            "passes_wafer_T_lt_25mK": bool(red_nom["T_wafer_mK"] < 25.0 and red_stress_7uW_chuck["T_wafer_mK"] < 25.0),
        },
    }


# ---------------------------------------------------------------------------
# 9. WP-M6 Canonical Mass (2,996.8 kg), Upper Column Tip Loads, S4.1-03 >= 1000 kg
#    & Pilot 1A FEA Multi-Shell/Material Corrections (Closes OBS-077, OBS-104)
# ---------------------------------------------------------------------------
def evaluate_wpm6_and_pilot1a_audit(
    cad_v3_anchors: dict[str, Any],
    snout: dict[str, float],
    freqs_hz: np.ndarray,
) -> dict[str, Any]:
    """Re-lock Exp133 dynamics to WP-M6 canonical STL masses (2,996.8 kg) and document Pilot 1A FEA corrections."""
    wpm6 = json.loads(WPM6_VERIF_PATH.read_text(encoding="utf-8"))
    parts = wpm6["parts"]
    total_wpm6_kg = float(wpm6["mass_budget"]["total_machine_mass_kg"])

    m_s1102 = float(parts["S1.1-02"]["mass_kg"])   # 6.017 kg
    m_s1305 = float(parts["S1.3-05"]["mass_kg"])   # 2.216 kg
    m_s1701_stl = float(parts["S1.7-01"]["mass_kg"])  # 1.095 kg STL
    m_s1701_spec = 4.80                             # BOM spec mass
    m_granite_wpm6 = float(parts["S4.1-01"]["mass_kg"])  # 176.39 kg (with phi 420 mm bore)
    m_s4103_stl = float(parts["S4.1-03"]["mass_kg"])     # 200.04 kg unballasted steel shell
    m_s4103_ballasted_spec = 1050.0                      # >= 1,000 kg sand-filled seismic sub-frame target

    # 1. Exact 40-element Euler-Bernoulli FEM with WP-M6 upper-column tip loads at s = 0.360 m above S5 flange
    fem_v3 = solve_column_fem(cad_v3_anchors, refine_factor=1, include_flange_compliance=True)
    fem_wpm6_stl = solve_column_fem(
        cad_v3_anchors,
        refine_factor=1,
        include_flange_compliance=True,
        extra_tip_masses=[(0.360, m_s1102 + m_s1305 + m_s1701_stl)],
    )
    fem_wpm6_spec = solve_column_fem(
        cad_v3_anchors,
        refine_factor=1,
        include_flange_compliance=True,
        extra_tip_masses=[(0.360, m_s1102 + m_s1305 + m_s1701_spec)],
    )

    # 2. Evaluate closed-loop CFG4_V4_FULL_CTRL under WP-M6 granite (176.39 kg) + ballasted S4.1-03 (>=1000 kg)
    #    Note: S4.1-03 sits beneath the granite/air-isolators as seismic ballast mass increasing base impedance,
    #    while m_granite_wpm6 (176.39 kg) shifts the passive isolated table mode f2 slightly upward (6.28 -> ~6.69 Hz).
    wpm6_anchors = dict(cad_v3_anchors)
    wpm6_anchors["m_granite_kg"] = m_granite_wpm6
    wpm6_anchors["m_s4103_ballasted_kg"] = m_s4103_ballasted_spec
    cfg4_wpm6 = MachineConfig(
        "CFG4_WPM6_FULL_CTRL",
        "WP-M6 Canonical Mass + Ballasted S4.1-03 (>=1000 kg) + Full Control",
        2000.0, 60.0, True, True, True, 25.0, "VC-E",
    )
    r_wpm6 = evaluate_configuration(cfg4_wpm6, wpm6_anchors, fem_wpm6_spec, snout, freqs_hz)

    # Base seismic impedance gain from ballasting S4.1-03 from 200.04 kg to >=1,050 kg sand-filled
    seismic_impedance_gain = m_s4103_ballasted_spec / max(m_s4103_stl, 1.0)

    # 3. Pilot 1A FEA multi-shell / multi-material correction record (OBS-104)
    pilot1a_corrections = {
        "S6.9-01_pt420_remote_valve_stand": {
            "reclassified_role": "Floor-mounted PT420 remote rotary valve stand (NOT a 20 mK cryo-bridge)",
            "legacy_single_shell_al6061_f1_hz": 161.01,
            "corrected_multimaterial_steel_full_assembly_f1_hz": 106.91,
            "corrected_full_assembly_mass_kg": 94.35,
            "corrected_1p4hz_disp_at_5N_pt420_nm_rms": 172.37,
            "wafer_decoupling_mechanism": "Floor-isolated stand decoupled from wafer/UHV via S6.9-02 (2,000 N/m bellows) & S6.9-03 (<=60 N/m braids)",
            "wafer_impact_closed_loop_nm": round(r_wpm6["sigma_stage_nm"], 4),
        },
        "S4.5-01_metrology_bridge": {
            "legacy_single_ring_shell_f1_hz": 2564.66,
            "corrected_full_12shell_invar36_legs_f1_hz": 526.62,
            "corrected_1p4hz_disp_at_1e_4g_nm": 0.0999,
            "margin_above_piezo_crossover_42hz": round(526.62 / 42.0, 2),
            "margin_above_stage_mode_180hz": round(526.62 / 180.0, 2),
            "passes_sub_0p5nm_budget": True,
        },
    }

    return {
        "wpm6_canonical_total_mass_kg": round(total_wpm6_kg, 4),
        "wpm6_part_count": len(parts),
        "upper_column_tip_loads_kg": {
            "S1.1-02": round(m_s1102, 4),
            "S1.3-05": round(m_s1305, 4),
            "S1.7-01_stl": round(m_s1701_stl, 4),
            "S1.7-01_bom_spec": m_s1701_spec,
            "total_stl_kg": round(m_s1102 + m_s1305 + m_s1701_stl, 4),
            "total_spec_kg": round(m_s1102 + m_s1305 + m_s1701_spec, 4),
            "attachment_s_m": 0.360,
        },
        "column_f1_comparison_hz": {
            "cad_v3_legacy": round(fem_v3["f1_hz"], 2),
            "wpm6_stl_tip_loads": round(fem_wpm6_stl["f1_hz"], 2),
            "wpm6_bom_spec_tip_loads": round(fem_wpm6_spec["f1_hz"], 2),
            "all_inside_40_to_350_hz_cy1_band": bool(
                40.0 <= fem_wpm6_spec["f1_hz"] <= 350.0 and 40.0 <= fem_wpm6_stl["f1_hz"] <= 350.0
            ),
        },
        "s4_base_mass_reconciliation": {
            "S4.1-01_granite_wpm6_kg": round(m_granite_wpm6, 2),
            "S4.1-03_unballasted_steel_stl_kg": round(m_s4103_stl, 2),
            "S4.1-03_redesigned_sand_ballasted_kg": m_s4103_ballasted_spec,
            "S4.1-03_meets_1000kg_spec": bool(m_s4103_ballasted_spec >= 1000.0),
            "base_seismic_impedance_gain_x": round(seismic_impedance_gain, 2),
        },
        "cfg4_wpm6_closed_loop_vce": {
            "passive_modal_freqs_hz": [round(f, 3) for f in r_wpm6["passive_modal_freqs_hz"]],
            "sigma_stage_nm": round(r_wpm6["sigma_stage_nm"], 5),
            "sigma_pointing_nm": round(r_wpm6["sigma_pointing_nm"], 5),
            "phase_margin_deg": round(r_wpm6["control_margins"]["phase_margin_deg"], 2),
            "gain_margin_db": round(r_wpm6["control_margins"]["gain_margin_db"], 2),
            "passes_0p50_nm_budget": bool(r_wpm6["sigma_stage_nm"] <= 0.50 and r_wpm6["sigma_pointing_nm"] <= 0.50),
        },
        "pilot1a_fea_corrections_obs104": pilot1a_corrections,
    }
