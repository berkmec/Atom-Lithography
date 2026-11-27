"""Unit tests for legacy qcell physics modules: src/qcell/fet4k.py and src/qcell/cell6d.py.

Closes OBS-149 coverage gap by exercising BSIM4-style compact nFET equations (including
4 K cryogenic parameter regime) and 6D programmable phase-field cell dynamics on small,
deterministic grids.
"""
from __future__ import annotations

import numpy as np
import pytest

from qcell import cell6d, fet4k


# ---------------------------------------------------------------------------
# src/qcell/fet4k.py unit tests
# ---------------------------------------------------------------------------


def test_fet_params_cox_and_immutable_at() -> None:
    p = fet4k.FetParams()
    expected_cox = fet4k.EPS0 * 3.9 / p.tox
    assert p.cox == pytest.approx(expected_cox, rel=1e-12)
    assert p.cox > 0.0

    p_cryo = p.at(T=4.0, vt0=0.68, mu=0.12)
    assert p.T == pytest.approx(300.0)
    assert p.vt0 == pytest.approx(0.52)
    assert p_cryo.T == pytest.approx(4.0)
    assert p_cryo.vt0 == pytest.approx(0.68)
    assert p_cryo.mu == pytest.approx(0.12)
    assert p_cryo.cox == pytest.approx(p.cox)


def test_fet_vt_body_effect_and_forward_bias_clamp() -> None:
    p = fet4k.FetParams()
    # At zero body bias Vbs=0, Vt equals Vt0 identically
    assert float(fet4k.vt(p, 0.0)) == pytest.approx(p.vt0, abs=1e-15)

    # Reverse body bias (Vbs < 0) raises threshold voltage; forward bias (Vbs > 0) lowers it
    vt_rev = float(fet4k.vt(p, -0.5))
    vt_fwd = float(fet4k.vt(p, 0.4))
    assert vt_rev > p.vt0 > vt_fwd

    # Extreme forward bias above phis must clamp safely without NaN
    vt_clamped = float(fet4k.vt(p, p.phis + 2.0))
    assert np.isfinite(vt_clamped)
    assert vt_clamped == pytest.approx(float(fet4k.vt(p, p.phis - 1e-3)), rel=1e-12)


def test_fet_vde_smooth_min_limits_and_monotonicity() -> None:
    p = fet4k.FetParams()
    vds_sat, vov = fet4k.vdsat(p, vgs=1.2, vbs=0.0)
    assert vov > 0.6
    assert 0.0 < vds_sat < vov

    vds_grid = np.linspace(0.0, 2.5, 51)
    vde_vals = fet4k.vde(p, vds_grid, vds_sat)
    assert np.all(np.isfinite(vde_vals))
    assert np.all(np.diff(vde_vals) >= 0.0), "vde must be monotonically non-decreasing in Vds"
    # Linear limit (Vds << Vdsat): vde ~= Vds
    assert float(fet4k.vde(p, 0.05, vds_sat)) == pytest.approx(0.05, abs=0.015)
    # Deep saturation limit (Vds >> Vdsat): vde -> Vdsat
    assert float(fet4k.vde(p, 5.0, vds_sat)) == pytest.approx(float(vds_sat), abs=0.005)


def test_fet_id_per_w_physics_and_4k_stability() -> None:
    for temp_k in (300.0, 4.0):
        p = fet4k.FetParams().at(T=temp_k)
        # Zero drain-source bias yields identically zero drain current
        assert float(fet4k.id_per_w(p, vgs=1.2, vds=0.0, vbs=0.0)) == pytest.approx(0.0, abs=1e-15)

        # Monotonic increase with Vgs in strong inversion
        vgs_sweep = np.array([0.8, 1.0, 1.2, 1.5, 1.8])
        id_vgs = fet4k.id_per_w(p, vgs=vgs_sweep, vds=1.0, vbs=0.0)
        assert np.all(np.isfinite(id_vgs))
        assert np.all(id_vgs > 0.0)
        assert np.all(np.diff(id_vgs) > 0.0)

        # Monotonic increase with Vds (linear + channel-length modulation lam > 0)
        vds_sweep = np.array([0.05, 0.2, 0.5, 1.0, 1.8])
        id_vds = fet4k.id_per_w(p, vgs=1.2, vds=vds_sweep, vbs=0.0)
        assert np.all(np.diff(id_vds) > 0.0)

        # Forward body bias increases Id by lowering Vt
        id_vbs0 = float(fet4k.id_per_w(p, vgs=1.0, vds=1.0, vbs=0.0))
        id_vbs_fwd = float(fet4k.id_per_w(p, vgs=1.0, vds=1.0, vbs=0.3))
        assert id_vbs_fwd > id_vbs0


def test_fet_impact_ionization_current_scaling() -> None:
    p = fet4k.FetParams()
    # Negligible impact ionization at low Vds below saturation
    iii_low = float(fet4k.iii_per_w(p, vgs=1.2, vds=0.05, vbs=0.0))
    iii_mid = float(fet4k.iii_per_w(p, vgs=1.2, vds=1.5, vbs=0.0))
    iii_high = float(fet4k.iii_per_w(p, vgs=1.2, vds=2.4, vbs=0.0))
    assert np.isfinite(iii_low) and iii_low >= 0.0
    assert iii_high > iii_mid > iii_low
    assert iii_high > 1e-10

    # Increasing beta0 exponentially suppresses impact ionization
    p_high_beta = p.at(beta0=p.beta0 * 1.5)
    assert float(fet4k.iii_per_w(p_high_beta, 1.2, 2.2, 0.0)) < float(
        fet4k.iii_per_w(p, 1.2, 2.2, 0.0)
    )


# ---------------------------------------------------------------------------
# src/qcell/cell6d.py unit tests
# ---------------------------------------------------------------------------


def test_cell6d_disk_and_droplet_detection() -> None:
    cell = cell6d.Cell6D(n=12, L=12.0, R=3.0, seed=7)
    # Empty field has zero droplets
    empty = cell.droplets(cell.phi)
    assert empty["n"] == 0
    assert empty["radii"] == []
    assert empty["centres"] == []

    # Centered spherical droplet detected with radius ~ R and center ~ [L/2, L/2, L/2]
    phi_disk = cell.disk(R=3.0)
    assert phi_disk.shape == (12, 12, 12)
    assert float(phi_disk.min()) >= 0.0
    assert float(phi_disk.max()) <= 1.0
    assert phi_disk[6, 6, 6] > 0.9

    drops = cell.droplets(phi_disk, thr=0.5, r_min=1.0)
    assert drops["n"] == 1
    assert drops["radii"][0] == pytest.approx(3.0, abs=0.45)
    for coord in drops["centres"][0]:
        assert coord == pytest.approx(5.5, abs=0.6)


def test_cell6d_operators_free_energy_reaction_and_laplacian() -> None:
    cell = cell6d.Cell6D(n=8, L=8.0, R=2.0, seed=0)

    # Double-well free energy derivative roots at -1, 0, +1
    roots = cell._free_energy_derivative(np.array([-1.0, 0.0, 1.0]))
    assert np.allclose(roots, 0.0, atol=1e-15)
    assert float(cell._free_energy_derivative(np.array([0.5]))[0]) < 0.0
    assert float(cell._free_energy_derivative(np.array([1.5]))[0]) > 0.0

    # Chemical reaction: production inside cell, pure decay outside
    rxn_in = cell._chem_reaction(chem=np.zeros((2, 2)), phi=np.ones((2, 2)))
    rxn_out = cell._chem_reaction(chem=np.ones((2, 2)), phi=np.zeros((2, 2)))
    assert np.allclose(rxn_in, cell.nu_prod)
    assert np.allclose(rxn_out, -cell.nu_deg)

    # Periodic 3D Laplacian: zero on constant field, exact discrete eigenvalue on sinusoid
    assert np.allclose(cell._laplacian(np.full((8, 8, 8), 3.14)), 0.0, atol=1e-14)
    k = 2.0 * np.pi / cell.L
    wave = np.sin(k * cell.X[0])
    lap = cell._laplacian(wave)
    discrete_eig = 2.0 * (np.cos(k * cell.dx) - 1.0) / (cell.dx**2)
    assert np.allclose(lap, discrete_eig * wave, atol=1e-12)


def test_cell6d_division_and_program6d_execution() -> None:
    cell = cell6d.Cell6D(n=8, L=8.0, R=2.0, seed=123)
    cell.phi[:] = cell.disk(R=2.5)
    cell.chem[:] = 1.0
    cell.rep[:] = cell.rep_threshold + 0.1

    phi_before = cell.phi.copy()
    phi_after, rep_after = cell._division_dynamics(cell.phi, cell.rep)
    assert cell.division_events == 1
    dividing = phi_before > 0.5
    assert np.all(rep_after[dividing] == 0.0)
    assert float(phi_after[dividing].mean()) < float(phi_before[dividing].mean())

    # Program6D compilation and instruction sequencing
    prog = cell6d.Program6D()
    prog.add_instruction("GROW", [0.1, 0.0, 0.0, 0.0, 0.0, 0.0], duration=1)
    prog.add_instruction("DIVIDE", [0.0] * 6, duration=1)
    prog.add_instruction("STEER", [0.0, 0.2, 0.0, 0.0, 0.0, 0.0], duration=1)
    prog.add_instruction("REPLICATE", [0.0] * 6, duration=1)
    prog.add_instruction("IDLE", [0.0] * 6, duration=1)
    compiled = prog.compile(cell.n, cell.L)
    assert compiled.shape == (6, cell.n, cell.n, cell.n)
    assert np.allclose(compiled[0], 0.1)
    assert np.allclose(compiled[1], 0.6)

    cell.load_program(compiled)
    cell.prog_instructions = list(prog.instructions)
    for _ in range(5):
        cell._execute_instruction()
    assert cell.prog_idx == 5
    assert np.any(cell.elec != 0.0)


def test_run_6d_simulation_deterministic_and_bounded() -> None:
    cfg = {
        "n": 8,
        "L": 8.0,
        "R": 2.2,
        "seed": 42,
        "fuel": 0.6,
        "T": 0.10,
        "dt": 0.02,
        "store_every": 2,
        "program": [
            {"op": "GROW", "params": [0.05, 0.0, 0.0, 0.0, 0.0, 0.0], "duration": 2},
            {"op": "IDLE", "params": [0.0] * 6, "duration": 3},
        ],
        "E_ext_func": lambda t: [np.full((8, 8, 8), 0.05 * np.sin(t))],
    }
    cell_a, res_a = cell6d.run_6d_simulation(cfg)
    cell_b, res_b = cell6d.run_6d_simulation(cfg)

    assert np.all(np.isfinite(res_a["final_phi"]))
    assert np.all(np.isfinite(res_a["final_chem"]))
    assert float(res_a["final_phi"].min()) >= -1.5
    assert float(res_a["final_phi"].max()) <= 1.5
    assert float(res_a["final_chem"].min()) >= 0.0
    assert float(res_a["final_chem"].max()) <= 2.0
    assert res_a["energy_consumed"] > 0.0
    assert np.allclose(res_a["final_phi"], res_b["final_phi"], atol=1e-12)
    assert np.allclose(res_a["final_chem"], res_b["final_chem"], atol=1e-12)
    assert res_a["energy_consumed"] == pytest.approx(res_b["energy_consumed"], rel=1e-12)
    assert cell_a.prog_idx == cell_b.prog_idx == 2
