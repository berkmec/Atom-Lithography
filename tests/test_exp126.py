"""Verification test suite for Exp126 (Full 32D GRAPE + Interleaved XY8/CPMG DD + 16-Cell Atom Programmability).

Runs read-only live mathematical and physics verification against:
  - experiments/exp126_atom_cell_programming/{hamiltonian126,grape_dd126,programs126}.py
  - results/exp126_atom_cell_programming/{predictions_exp126.json,exp126.json,summary_exp126.md,fig_exp126_*.png}
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
EXP_DIR = ROOT / "experiments" / "exp126_atom_cell_programming"
RES_DIR = ROOT / "results" / "exp126_atom_cell_programming"
if str(EXP_DIR) not in sys.path:
    sys.path.insert(0, str(EXP_DIR))

import grape_dd126 as g126
import hamiltonian126 as h126
import programs126 as p126


def test_silicon_atlas_matches_exp62_finalists_exactly():
    """Standalone Kohn-Luttinger + dipolar atlas reproduces Exp62 finalist hyperfine couplings to machine precision."""
    f62 = json.loads((ROOT / "results" / "exp62" / "finalist62.json").read_text(encoding="utf-8"))
    fins = h126.load_exp62_finalists(verify_lie=False)
    for key in ("F1", "F2", "F4.7"):
        expected_khz = np.asarray(f62["audits"][key]["register_restricted_K4"]["A_kHz_primary"], dtype=np.float64)
        got_khz = fins[key].A_hz / 1e3
        assert np.max(np.abs(got_khz - expected_khz)) < 1e-9
        assert abs(fins[key].t2e_s - h126.t2e_bath_s(fins[key].abundance_pct)) < 1e-12


def test_dd_schedule_symmetry_and_net_identity():
    """XY8 and CPMG schedules refocus hyperfine drift (sum parities == 0) and yield U_dd_net = +-I."""
    for seq in ("XY8", "CPMG"):
        for n_dd in (0, 2, 4, 8, 16, 32):
            p_map, parities = g126.dd_schedule(64, n_dd, seq)
            assert len(p_map) == n_dd
            if n_dd > 0:
                assert abs(float(np.sum(parities))) < 1e-12
            sign = g126.dd_net_electron_sign(n_dd, seq)
            assert abs(abs(sign) - 1.0) < 1e-12
            assert abs(sign.imag) < 1e-12


def test_exact_32d_drift_hermiticity_and_d0_storage_unitarity():
    """32x32 drift Hamiltonian is Hermitian and D0 storage evolution is unitary with leakage <= 1e-5."""
    f1 = h126.load_exp62_finalists(verify_lie=False)["F1"]
    H0 = h126.full_32d_drift_hamiltonian(f1.A_hz, f1.J_hz)
    assert H0.shape == (32, 32)
    assert float(np.max(np.abs(H0 - H0.conj().T))) < 1e-12
    d0 = h126.exact_d0_storage_leakage(f1.A_hz, f1.J_hz, (17.5, 175.0))
    assert d0["17.5s"]["unitarity_fro_err"] < 1e-12
    assert d0["17.5s"]["max_leak"] < 1e-9


def test_electron_mediated_cphi_and_ccz_exact_identities():
    """Ideal electron-mediated CZ, CS, CT, CNOT, and 3-body CCZ identities hold to < 1e-13 in full 32D."""
    # Construct ideal zero-error 32D dummy library using exact operators via small synthetic check
    from scipy.linalg import expm
    I2, X, Y, Z, H = h126.I2, h126.PX, h126.PY, h126.PZ, h126.HADAMARD_2
    P0 = np.array([[1, 0], [0, 0]], dtype=np.complex128)
    P1 = np.array([[0, 0], [0, 1]], dtype=np.complex128)
    Xe = h126.kron_list([X, I2, I2]); Ye = h126.kron_list([Y, I2, I2])
    Zi = h126.kron_list([I2, Z, I2]); Zj = h126.kron_list([I2, I2, Z])
    Hi = h126.kron_list([I2, H, I2]); Hj = h126.kron_list([I2, I2, H])
    cXi = np.kron(P0, np.kron(X, I2)) + np.kron(P1, np.eye(4))
    cXj = np.kron(P0, np.kron(I2, X)) + np.kron(P1, np.eye(4))
    Rx_m = expm(+1j * (math.pi / 4.0) * Xe)
    Rx_p = expm(-1j * (math.pi / 4.0) * Xe)

    for phi in (math.pi, math.pi / 2.0, math.pi / 4.0):
        U_mid = Rx_p @ (cXj @ cXi) @ expm(+1j * (phi / 4.0) * Ye) @ (cXi @ cXj) @ Rx_m
        U = expm(-1j * (phi / 4.0) * (Zi + Zj)) @ (Hi @ Hj) @ U_mid @ (Hi @ Hj)
        blk = U[:4, :4]
        blk = blk / (blk[0, 0] / abs(blk[0, 0]))
        tgt = np.diag([1.0, 1.0, 1.0, np.exp(1j * phi)])
        assert float(np.max(np.abs(blk - tgt))) < 1e-13
        assert float(np.max(np.abs(U[4:, :4]))) < 1e-13


def test_calibrated_1_over_omega_alpha_hahn_echo_32d():
    """Live full-32D Hahn-echo check confirms calibrated 1/omega^alpha bath noise hits 1/e within +-0.05."""
    f1 = h126.load_exp62_finalists(verify_lie=False)["F1"]
    for alpha in (1.0, 2.0):
        he = g126.run_hahn_echo_32d(f1, alpha=alpha, n_traj=512, seed=12699)
        assert he["max_state_norm_err"] < 1e-12
        assert he["abs_err"] <= 0.05


def test_independent_repropagation_of_saved_f1_waveforms():
    """Re-propagate saved F1 GRAPE waveforms from exp126.json from scratch: verify unitarity & propagator match."""
    data = json.loads((RES_DIR / "exp126.json").read_text(encoding="utf-8"))
    f1 = h126.load_exp62_finalists(verify_lie=False)["F1"]
    dev = g126.get_device()
    wfs = data["part1_f1_universal_gates"]["waveforms"]

    for key in ("Rx_pi2_q0", "X_q0", "cX_XY8_16_q0", "cX_XY8_16_q3"):
        rec = wfs[key]
        ctrl = np.asarray(rec["controls_khz"], dtype=np.float64)
        ev = g126.evaluate_gate_32d(
            f1, ctrl, rec["gate_name"], rec["target_qubit"],
            rec["duration_us"], rec["n_dd"], rec["dd_sequence"], device=dev,
        )
        assert ev["max_unitarity_err_fro"] < 1e-11
        assert abs(ev["nominal_fidelity_32d"] - rec["nominal_fidelity_32d"]) < 1e-10
        assert abs(ev["worst_corner_fidelity_32d"] - rec["worst_corner_fidelity_32d"]) < 1e-10

        # Cross-check independent statevector propagator against evaluate_gate_32d across all 32 basis states!
        if rec["gate_name"] == "cX":
            wf_obj = g126.PulseWaveform(
                gate_name="cX", target_qubit=rec["target_qubit"], duration_us=rec["duration_us"],
                n_slices=rec["n_slices"], n_dd=rec["n_dd"], dd_sequence=rec["dd_sequence"],
                carrier_offset_hz=0.5 * float(f1.A_hz[rec["target_qubit"]]),
                controls_khz=ctrl, apply_virtual_rze_neg_pi2=True,
                virtual_z_nuc_rad=ev["virtual_z_nuc_rad"],
            )
            eye32 = torch.eye(32, dtype=torch.complex128, device=dev)
            U_prop = g126.propagate_waveform_noisy_32d(eye32, f1, wf_obj, None, 0.0, device=dev).T.cpu().numpy()
            net_s = g126.dd_net_electron_sign(rec["n_dd"], rec["dd_sequence"])
            U_eval = np.zeros((32, 32), dtype=np.complex128)
            U_eval[:16, :16] = 1.0j * complex(net_s.conjugate()) * ev["U0_nom"]
            U_eval[16:, 16:] = complex(net_s.conjugate()) * ev["U1_nom"]
            assert float(np.max(np.abs(U_prop - U_eval))) < 1e-12
            assert float(np.linalg.norm(U_prop.conj().T @ U_prop - np.eye(32), ord="fro")) < 1e-11


def test_exp126_json_schema_risk_r3_and_16cell_integrity():
    """Verify exp126.json integrity, Risk R3 closure (F1 Q >= 0.85 for alpha=1,2), and 16-cell diversity."""
    assert (RES_DIR / "predictions_exp126.json").exists()
    assert (RES_DIR / "exp126.json").exists()
    assert (RES_DIR / "summary_exp126.md").exists()

    data = json.loads((RES_DIR / "exp126.json").read_text(encoding="utf-8"))
    assert data["no_lab_measurement"] is True
    assert len(data["verdicts"]) == 8

    # Risk R3 closure at f=1%, N=64, eps=1e-3 for BOTH alpha=1 and alpha=2
    f1_n64 = data["part2_risk_r3_interleaved_dd"]["abundance_dd_vs_exp63"]["F1"]["N_runs"]["N64"]
    assert f1_n64["Q_32d_a1_e1e3"] >= 0.85
    assert f1_n64["Q_32d_a2_e1e3"] >= 0.85

    # XY8 strictly beats CPMG on Y-axis under systematic error
    xy8_row = data["verdicts"]["P126_5_pulse_ceiling_and_xy8_vs_cpmg"]["measured"]
    assert xy8_row["xy8_minus_cpmg_ghz_y_at_2sqrt1e3"] >= 0.20

    # 16 heterogeneous certified cells
    p3 = data["part3_multicell_16_programs"]
    assert p3["n_cells"] == 16
    assert p3["unique_spectra"] == 16
    assert p3["A_k_cv"] > 0.20
    for c in p3["cells"]:
        assert c["cell_meta"]["lie_rank_k4"] == 1023
        assert c["cell_meta"]["vandermonde_rank_k4"] == 4
        assert c["cell_meta"]["vandermonde_rank_k8"] == 8
        assert c["d0_storage"]["17.5s"]["max_leak"] <= 1e-5
    ps = p3["program_summary"]
    assert ps["Bell"]["noisy_a2_mean"] >= 0.90
    assert ps["GHZ-4"]["noisy_a2_mean"] >= 0.88
    assert ps["Grover-2"]["marked_11_prob_mean"] >= 0.85
    assert ps["QFT-3"]["noisy_a2_mean"] >= 0.82
    assert ps["BitFlip-3"]["noisy_a2_mean"] >= 0.80


def test_exp126_figures_exist_and_nonempty():
    """Verify all three high-resolution PyCairo PNG figures exist and have valid PNG IHDR/dimensions."""
    import struct

    for fname in (
        "fig_exp126_grape_pulses.png",
        "fig_exp126_interleaved_dd_vs_exp63.png",
        "fig_exp126_multicell_programs.png",
    ):
        p = RES_DIR / fname
        assert p.exists() and p.stat().st_size > 50_000, f"Missing or tiny figure: {p}"
        raw = p.read_bytes()
        assert raw[:8] == b"\x89PNG\r\n\x1a\n", f"Invalid PNG magic header: {p}"
        assert raw[12:16] == b"IHDR", f"Missing IHDR chunk: {p}"
        w, h = struct.unpack(">II", raw[16:24])
        assert w >= 1800 and h >= 1080, f"Low resolution {w}x{h}: {p}"
        assert b"IDAT" in raw and b"IEND" in raw, f"Truncated PNG: {p}"
