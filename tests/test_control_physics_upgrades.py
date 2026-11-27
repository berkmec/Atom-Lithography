"""Physics verification tests for upgraded control & quantum-bus models in auto_recal.py and programmer.py.

Tests conservation laws, physical monotonicity, algebraic invariants, and edge cases across
all 6 upgraded physics engines:
  1. AutoRecalController.mitigate_vacuum_spike (2-chamber differential-pumping UHV ODE)
  2. AutoRecalController.mitigate_laser_power_drift (1D nonlinear Si FVM PDE + AOM lag + anti-windup PID)
  3. AutoRecalController.mitigate_blanker_dead_channels (wafer-stage step-and-stitch planner)
  4. MultiCellProgrammer.execute_echo_cz (16D Strang-split Lindblad + multi-OU 1/f Choi evolution)
  5. MultiCellProgrammer.execute_mux_readout (Exp140 dispersive Lorentzian + Purcell + TWPA + erfc)
  6. MultiCellProgrammer.execute_qldpc_round (exact GF(2) BB parity checks + BP-OSD decoding)
"""
from __future__ import annotations

from pathlib import Path
import time

import numpy as np
import pytest

from src.machine_control.auto_recal import (
    AutoRecalController,
    T_MELT_SI,
    cp_si,
    k_si,
)
from src.machine_control.factory import Certificate
from src.machine_control.programmer import (
    MultiCellProgrammer,
    _get_bb_code_algebra,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _make_pair_certs() -> tuple[Certificate, Certificate]:
    c0 = Certificate(
        register_id="PHY-CELL-0",
        slot=0,
        attempts=1,
        shots=1,
        min_spacing_Hz=12_000.0,
        dd_quality_gate=True,
        lines_Hz=[120_000.0, 92_000.0, 68_000.0, 48_000.0],
    )
    c1 = Certificate(
        register_id="PHY-CELL-1",
        slot=1,
        attempts=1,
        shots=1,
        min_spacing_Hz=12_500.0,
        dd_quality_gate=True,
        lines_Hz=[122_000.0, 95_000.0, 71_000.0, 50_000.0],
    )
    return c0, c1


# ===========================================================================
# 1. S5 UHV Vacuum Spike — 2-Chamber Differential-Pumping ODE
# ===========================================================================

def test_vacuum_ode_monotonicity_valve_latency_and_protection():
    ctrl = AutoRecalController(seed=2026145)

    r_lo = ctrl.mitigate_vacuum_spike(peak_pressure_torr=3.5e-8)
    r_md = ctrl.mitigate_vacuum_spike(peak_pressure_torr=3.5e-7)
    r_hi = ctrl.mitigate_vacuum_spike(peak_pressure_torr=3.5e-6)

    assert "solve_ivp" in r_lo["ode_solver"]
    assert len(r_lo["trajectory_summary"]) >= 8
    assert r_lo["passed"] is True
    assert r_lo["blanker_latency_us"] < 1.0
    assert 15.0 <= r_lo["gate_valve_closure_ms"] <= 30.0
    # Finite valve closure latency causes non-zero burst exposure even with <1 us beam blanking
    assert r_lo["exposure_langmuir_burst_excess"] > 0.0
    assert r_lo["excess_monolayer_coverage_frac"] > 0.0
    assert r_lo["valve_excess_protection_factor"] > 10.0

    # Strict monotonicity with burst magnitude
    assert r_lo["peak_ch2_wafer_torr"] < r_md["peak_ch2_wafer_torr"] < r_hi["peak_ch2_wafer_torr"]
    assert r_lo["exposure_langmuir_burst_excess"] < r_md["exposure_langmuir_burst_excess"] < r_hi["exposure_langmuir_burst_excess"]
    assert r_lo["surface_monolayer_coverage_frac"] < r_md["surface_monolayer_coverage_frac"] < r_hi["surface_monolayer_coverage_frac"]
    assert r_lo["pumpdown_recovery_s"] < r_md["pumpdown_recovery_s"] < r_hi["pumpdown_recovery_s"]

    # Slower mechanical gate valve strictly increases excess wafer exposure
    r_v15 = ctrl.mitigate_vacuum_spike(peak_pressure_torr=3.5e-8, valve_closure_ms=15.0)
    r_v30 = ctrl.mitigate_vacuum_spike(peak_pressure_torr=3.5e-8, valve_closure_ms=30.0)
    assert r_v30["exposure_langmuir_burst_excess"] > r_v15["exposure_langmuir_burst_excess"]
    assert r_v30["peak_ch2_wafer_torr"] > r_v15["peak_ch2_wafer_torr"]
    assert r_v30["excess_monolayer_coverage_frac"] > r_v15["excess_monolayer_coverage_frac"]


def test_vacuum_ode_edge_cases_subthreshold_and_catastrophic():
    ctrl = AutoRecalController(seed=2026145)

    # Sub-threshold fluctuation (< 1e-8 Torr) must NOT falsely trip interlock
    r_sub = ctrl.mitigate_vacuum_spike(peak_pressure_torr=4.0e-9)
    assert r_sub["interlock_trip_detected"] is False
    assert r_sub["gate_valve_locked"] is False
    assert r_sub["beam_paused"] is False
    assert r_sub["passed"] is True

    # Catastrophic burst saturates Langmuir coverage (< 1.0) and honestly fails spec
    r_cat = ctrl.mitigate_vacuum_spike(peak_pressure_torr=1.0e-4)
    assert r_cat["interlock_trip_detected"] is True
    assert 0.01 < r_cat["surface_monolayer_coverage_frac"] < 1.0
    assert r_cat["passed"] is False


# ===========================================================================
# 2. S5.5 Laser Power Drift — Nonlinear 1D Si PDE + AOM Lag + Anti-Windup PID
# ===========================================================================

def test_laser_nonlinear_si_pde_conservation_inertia_and_pid_control():
    # Verify Exp130 NIST-JANAF silicon k(T) decreases and cp(T) increases with T
    assert float(k_si(300.0)) > float(k_si(1000.0)) > float(k_si(1530.0))
    assert float(cp_si(300.0)) < float(cp_si(1000.0)) < float(cp_si(1530.0))

    ctrl = AutoRecalController(seed=2026145)
    res = ctrl.mitigate_laser_power_drift(drift_pct=8.0)

    assert res["passed"] is True
    assert res["reference_energy_balance_rel_err"] < 1e-4
    assert 1515.0 <= res["reference_T_peak_K"] <= 1550.0
    assert res["worst_uncontrolled_sigma_nm"] > 0.50
    assert res["worst_controlled_sigma_nm"] <= 0.50
    assert res["max_abs_delta_T_peak_K"] <= 5.0

    for lbl in ("surge_plus", "drop_minus"):
        c = res["cases"][lbl]
        assert c["energy_balance_rel_err"] < 1e-4
        assert c["aom_saturated"] is False
        assert c["controlled_T_peak_K"] < T_MELT_SI
        assert c["controlled_activation_frac"] >= 0.99

    # Verify thermal inertia directly: surface temperature lags laser turn-on and peaks near end of pulse
    rng = np.random.default_rng(7)
    ref_run = ctrl._simulate_laser_flash_run(1.0, False, None, rng, aom_tau_us=15.0, aom_dead_time_us=10.0)
    assert 0.70 <= ref_run["t_peak_ms"] <= 1.05
    # Early pulse T(t=0.1 ms) is far below T_peak due to finite Si thermal mass
    idx_early = int(np.argmin(np.abs(ref_run["t_s"] - 1.0e-4)))
    assert ref_run["T_surf_K"][idx_early] < 0.65 * ref_run["T_peak_K"]
    # Post-pulse radiative + conductive cooling drops surface temperature strongly
    assert ref_run["T_surf_K"][-1] < 0.50 * ref_run["T_peak_K"]


def test_laser_aom_lag_degrades_settling_and_extreme_drift_saturates():
    ctrl = AutoRecalController(seed=2026145)
    r_fast = ctrl.mitigate_laser_power_drift(drift_pct=8.0, aom_tau_us=10.0, aom_dead_time_us=10.0)
    r_slow = ctrl.mitigate_laser_power_drift(drift_pct=8.0, aom_tau_us=80.0, aom_dead_time_us=30.0)
    assert r_slow["servo_settling_us"] > r_fast["servo_settling_us"]

    # Extreme +75% surge exceeds AOM authority (1.75 * 0.65 = 1.1375 > 1.0): must saturate and fail!
    r_sat = ctrl.mitigate_laser_power_drift(drift_pct=75.0)
    assert r_sat["cases"]["surge_plus"]["aom_saturated"] is True
    assert r_sat["cases"]["surge_plus"]["passed"] is False
    assert r_sat["passed"] is False


# ===========================================================================
# 3. S3 Blanker Dead Channels — Wafer-Stage Step-and-Stitch Planner
# ===========================================================================

def test_blanker_step_and_stitch_single_interior_dead_and_honest_throughput():
    ctrl = AutoRecalController(seed=2026145)

    # Single interior dead channel (15, 16) CANNOT be teleported to perimeter (-1, k) at 100% throughput!
    r1 = ctrl.mitigate_blanker_dead_channels(dead_coords_override=[(15, 16)])
    assert r1["compensation_mode"] == "wafer_stage_step_and_stitch"
    assert r1["dead_channels_detected"] == 1
    assert r1["channels_remapped"] == 1
    assert r1["stitch_passes_required"] == 1
    assert r1["wafer_site_coverage_after_pct"] == 100.0
    assert r1["zero_coordinate_mismatch"] is True
    assert r1["max_coordinate_mismatch_um"] == 0.0
    assert r1["all_assigned_beamlets_live"] is True
    assert r1["zero_double_exposure"] is True
    # Honest throughput MUST be strictly < 100% whenever any stitch pass is needed
    assert 50.0 < r1["throughput_after_recal_pct"] < 100.0
    assert r1["stitch_overhead_time_ms"] > 0.0
    assert r1["passed"] is True

    # Verify exact coordinate math on sample remapping entry
    m0 = r1["sample_remappings"][0]
    rb, cb = m0["assigned_live_coord"]
    dr, dc = m0["stage_offset_pitch"]
    assert (rb + dr, cb + dc) == (15, 16)
    assert (rb, cb) != (15, 16)
    assert 0 <= rb < 32 and 0 <= cb < 32


def test_blanker_step_and_stitch_monotonicity_and_edge_cases():
    ctrl = AutoRecalController(seed=2026145)

    r0 = ctrl.mitigate_blanker_dead_channels(dead_fraction=0.0)
    r5 = ctrl.mitigate_blanker_dead_channels(dead_fraction=0.05)
    r40 = ctrl.mitigate_blanker_dead_channels(dead_fraction=0.40)
    r100 = ctrl.mitigate_blanker_dead_channels(dead_fraction=1.0)

    # 0% dead -> 0 stitch passes, exact 100% throughput
    assert r0["stitch_passes_required"] == 0
    assert r0["throughput_after_recal_pct"] == 100.0
    assert r0["passed"] is True

    # 5% dead -> 51 channels covered with zero mismatch and honest <100% throughput
    assert r5["dead_channels_detected"] == 51
    assert r5["channels_remapped"] == 51
    assert r5["wafer_site_coverage_after_pct"] == 100.0
    assert r5["zero_coordinate_mismatch"] is True
    assert 45.0 <= r5["throughput_after_recal_pct"] < 100.0
    assert r5["passed"] is True

    # Higher dead fraction increases stitch passes/overhead and lowers effective throughput
    assert r40["stitch_passes_required"] >= r5["stitch_passes_required"]
    assert r40["stitch_overhead_time_ms"] > r5["stitch_overhead_time_ms"]
    assert r40["throughput_after_recal_pct"] < r5["throughput_after_recal_pct"]

    # 100% dead -> unrecoverable
    assert r100["channels_remapped"] == 0
    assert r100["throughput_after_recal_pct"] == 0.0
    assert r100["passed"] is False


# ===========================================================================
# 4. ECHO_CZ — 16D Strang-Split Lindblad + Multi-OU 1/f Choi Propagator
# ===========================================================================

def test_echo_cz_noiseless_unitary_cptp_and_echo_suppression():
    c0, c1 = _make_pair_certs()

    # Exact noiseless unitary limit
    mcp_ideal = MultiCellProgrammer(bus_kappa_MHz=0.0, t2_electron_us=1.0e9)
    r_id = mcp_ideal.execute_echo_cz(c0, c1, s_eps_uev=0.0, echo_pulses=1, eps_rot=0.0)
    assert r_id["echo_process_fidelity"] > 0.9999
    assert r_id["echo_cz_bell_fidelity"] > 0.9999
    assert abs(r_id["echo_entangling_phase_over_pi"] - 1.0) < 1e-3
    assert r_id["cavity_leakage_prob"] < 1e-4

    # Nominal noisy case: CPTP invariants + Nielsen identity + echo suppression
    mcp = MultiCellProgrammer()
    r1 = mcp.execute_echo_cz(c0, c1, s_eps_uev=1.0, echo_pulses=1)
    r2 = mcp.execute_echo_cz(c0, c1, s_eps_uev=1.0, echo_pulses=2)

    assert r1["cptp_audit"]["max_trace_err"] < 1e-12
    assert r1["cptp_audit"]["max_herm_err"] < 1e-12
    assert r1["cptp_audit"]["min_eigval"] > -1e-10
    assert r1["pauli_error_budget"]["pauli_sum"] == pytest.approx(1.0, abs=1e-6)
    expected_favg = (4.0 * r1["echo_process_fidelity"] + 1.0) / 5.0
    assert r1["echo_avg_gate_fidelity"] == pytest.approx(expected_favg, abs=1e-5)

    assert r1["echo_cz_bell_fidelity"] > r1["bare_cz_bell_fidelity"] + 0.15
    assert r1["echo_process_fidelity"] > r1["bare_process_fidelity"] + 0.15
    assert r2["echo_process_fidelity"] > r1["echo_process_fidelity"]


def test_echo_cz_physical_monotonicity_kappa_detuning_noise_and_hops():
    c0, c1 = _make_pair_certs()

    # Higher resonator linewidth kappa strictly degrades fidelity (physical M4 g=1.5, Delta=18 MHz)
    f_k025 = MultiCellProgrammer(bus_kappa_MHz=0.025).execute_echo_cz(c0, c1, s_eps_uev=1.0)
    f_k10 = MultiCellProgrammer(bus_kappa_MHz=0.10).execute_echo_cz(c0, c1, s_eps_uev=1.0)
    f_k50 = MultiCellProgrammer(bus_kappa_MHz=0.50).execute_echo_cz(c0, c1, s_eps_uev=1.0)
    assert f_k025["echo_cz_bell_fidelity"] > f_k10["echo_cz_bell_fidelity"] > f_k50["echo_cz_bell_fidelity"]
    assert f_k025["echo_process_fidelity"] > f_k10["echo_process_fidelity"] > f_k50["echo_process_fidelity"]

    # Pure cavity-QED detuning sweep (s_eps=0, T2=inf): smaller Delta strictly increases cavity-loss
    # infidelity (~ pi * kappa / (2 * Delta)) and cavity leakage!
    f_d18_c = MultiCellProgrammer(bus_detuning_MHz=18.0, bus_kappa_MHz=0.05, t2_electron_us=1.0e9).execute_echo_cz(c0, c1, s_eps_uev=0.0)
    f_d10_c = MultiCellProgrammer(bus_detuning_MHz=10.0, bus_kappa_MHz=0.05, t2_electron_us=1.0e9).execute_echo_cz(c0, c1, s_eps_uev=0.0)
    f_d06_c = MultiCellProgrammer(bus_detuning_MHz=6.0, bus_kappa_MHz=0.05, t2_electron_us=1.0e9).execute_echo_cz(c0, c1, s_eps_uev=0.0)
    assert f_d18_c["echo_cz_bell_fidelity"] > f_d10_c["echo_cz_bell_fidelity"] > f_d06_c["echo_cz_bell_fidelity"]
    assert f_d18_c["echo_process_fidelity"] > f_d10_c["echo_process_fidelity"] > f_d06_c["echo_process_fidelity"]
    assert f_d18_c["cavity_leakage_prob"] < f_d10_c["cavity_leakage_prob"] < f_d06_c["cavity_leakage_prob"]

    # Deep non-dispersive regime under 1/f noise: pushing Delta too low with strong kappa degrades fidelity
    f_d6_n = MultiCellProgrammer(bus_detuning_MHz=6.0, bus_kappa_MHz=0.50).execute_echo_cz(c0, c1, s_eps_uev=1.0)
    f_d3_n = MultiCellProgrammer(bus_detuning_MHz=3.0, bus_kappa_MHz=0.50).execute_echo_cz(c0, c1, s_eps_uev=1.0)
    f_d1p5_n = MultiCellProgrammer(bus_detuning_MHz=1.5, bus_kappa_MHz=0.50).execute_echo_cz(c0, c1, s_eps_uev=1.0)
    assert f_d6_n["echo_cz_bell_fidelity"] > f_d3_n["echo_cz_bell_fidelity"] > f_d1p5_n["echo_cz_bell_fidelity"]

    # Pure bosonic cavity-loss check (no double-counted Purcell): kappa=0.05 -> 0.20 at Delta=18, T2=inf
    c_k05 = MultiCellProgrammer(bus_kappa_MHz=0.05, t2_electron_us=1.0e9).execute_echo_cz(c0, c1, s_eps_uev=0.0, eps_rot=0.0)
    c_k20 = MultiCellProgrammer(bus_kappa_MHz=0.20, t2_electron_us=1.0e9).execute_echo_cz(c0, c1, s_eps_uev=0.0, eps_rot=0.0)
    assert c_k05["echo_cz_bell_fidelity"] > c_k20["echo_cz_bell_fidelity"]
    # Matches continuous-time quantum-optics loss ~ pi * kappa / (2 * Delta) = pi * 0.05 / 36.0
    assert abs((1.0 - c_k05["echo_cz_bell_fidelity"]) - (np.pi * 0.05 / 36.0)) < 1.5e-3

    # Shorter Exp137 pi-pulse (15 ns) outperforms slower 40 ns echo pulse under 1/f noise
    mcp = MultiCellProgrammer()
    r_pi15 = mcp.execute_echo_cz(c0, c1, s_eps_uev=1.0, pi_pulse_us=0.015)
    r_pi40 = mcp.execute_echo_cz(c0, c1, s_eps_uev=1.0, pi_pulse_us=0.040)
    assert r_pi15["echo_cz_bell_fidelity"] >= r_pi40["echo_cz_bell_fidelity"]

    # Stronger 1/f noise amplitude degrades both bare and echoed fidelity
    r_s0 = mcp.execute_echo_cz(c0, c1, s_eps_uev=0.0)
    r_s1 = mcp.execute_echo_cz(c0, c1, s_eps_uev=1.0)
    r_s2 = mcp.execute_echo_cz(c0, c1, s_eps_uev=2.0)
    assert r_s0["bare_cz_bell_fidelity"] > r_s1["bare_cz_bell_fidelity"] > r_s2["bare_cz_bell_fidelity"]
    assert r_s0["echo_process_fidelity"] > r_s1["echo_process_fidelity"] > r_s2["echo_process_fidelity"]

    # Multi-hop bus degrades fidelity monotonically
    r_h1 = mcp.execute_echo_cz(c0, c1, hop_distance=1)
    r_h2 = mcp.execute_echo_cz(c0, c1, hop_distance=2)
    assert r_h1["echo_cz_bell_fidelity"] > r_h2["echo_cz_bell_fidelity"]
    assert r_h2["total_duration_us"] == pytest.approx(2.0 * r_h1["total_duration_us"], rel=1e-4)


# ===========================================================================
# 5. MUX_READOUT — Dispersive Lorentzian + Purcell + TWPA + erfc Physics
# ===========================================================================

def test_mux_readout_nmux_ceiling_purcell_kappa_twpa_and_tau_tradeoff():
    mcp = MultiCellProgrammer()
    cells = [f"C{i}" for i in range(8)]

    # Exp140 N_mux ceiling: 16 > 32 >= 0.990 > 64 (< 0.990)
    m16 = mcp.execute_mux_readout(cells, n_mux=16, tau_ro_us=2.0)
    m32 = mcp.execute_mux_readout(cells, n_mux=32, tau_ro_us=2.0)
    m64 = mcp.execute_mux_readout(cells, n_mux=64, tau_ro_us=2.0)
    assert m16["per_cell_readout_fidelity"] > m32["per_cell_readout_fidelity"] > m64["per_cell_readout_fidelity"]
    assert m32["per_cell_readout_fidelity"] >= 0.990
    assert m64["per_cell_readout_fidelity"] < 0.990
    assert m64["twpa_backoff_dB"] > m32["twpa_backoff_dB"]
    assert m64["mean_lorentzian_xt"] > m32["mean_lorentzian_xt"] > m16["mean_lorentzian_xt"]
    assert m32["batch_joint_readout_fidelity"] < m32["per_cell_readout_fidelity"]

    # Smaller dispersive detuning / removing Purcell filter increases Gamma_P and degrades fidelity
    m_small_det = mcp.execute_mux_readout(cells, n_mux=32, tau_ro_us=2.0, detuning_r_MHz=250.0, use_purcell_filter=False)
    m_no_pf = mcp.execute_mux_readout(cells, n_mux=32, tau_ro_us=2.0, use_purcell_filter=False)
    assert m_no_pf["purcell_gamma_kHz"] > 100.0 * m32["purcell_gamma_kHz"]
    assert m_no_pf["t1_eff_us"] < m32["t1_eff_us"]
    assert m_no_pf["per_cell_readout_fidelity"] < m32["per_cell_readout_fidelity"]
    assert m_small_det["per_cell_readout_fidelity"] < m_no_pf["per_cell_readout_fidelity"]

    # Higher kappa_ro broadens Lorentzian wing crosstalk and degrades fidelity
    m_wide_k = mcp.execute_mux_readout(cells, n_mux=32, tau_ro_us=2.0, kappa_ro_MHz=8.0)
    assert m_wide_k["mean_lorentzian_xt"] > m32["mean_lorentzian_xt"]
    assert m_wide_k["per_cell_readout_fidelity"] < m32["per_cell_readout_fidelity"]

    # Disabling TWPA or increasing TWPA noise temp lowers SNR and fidelity
    m_no_twpa = mcp.execute_mux_readout(cells, n_mux=32, tau_ro_us=2.0, use_twpa=False)
    m_hot_twpa = mcp.execute_mux_readout(cells, n_mux=32, tau_ro_us=2.0, twpa_tn_K=1.5)
    assert m_no_twpa["t_sys_K"] > m_hot_twpa["t_sys_K"] > m32["t_sys_K"]
    assert m_no_twpa["mean_snr"] < m_hot_twpa["mean_snr"] < m32["mean_snr"]
    assert m_no_twpa["per_cell_readout_fidelity"] < m_hot_twpa["per_cell_readout_fidelity"] < m32["per_cell_readout_fidelity"]

    # Integration time tradeoff: too short (low SNR) and too long (T1 decay) both lose to 2.0 us
    m_short = mcp.execute_mux_readout(cells, n_mux=32, tau_ro_us=0.25)
    m_long = mcp.execute_mux_readout(cells, n_mux=32, tau_ro_us=40.0)
    assert m32["per_cell_readout_fidelity"] > m_short["per_cell_readout_fidelity"]
    assert m32["per_cell_readout_fidelity"] > m_long["per_cell_readout_fidelity"]
    assert m_long["err_t1"] > 10.0 * m32["err_t1"]


# ===========================================================================
# 6. QLDPC_ROUND — Real GF(2) BB Parity Checks & BP-OSD Decoding
# ===========================================================================

@pytest.mark.parametrize("code_name,exp_n,exp_k,exp_d,exp_feed", [
    ("BB_72_12_6", 72, 12, 6, 3),
    ("BB_144_12_12", 144, 12, 12, 5),
    ("BB_288_12_18", 288, 12, 18, 9),
])
def test_qldpc_gf2_css_algebra_and_fast_zero_error_round(code_name, exp_n, exp_k, exp_d, exp_feed):
    mcp = MultiCellProgrammer()
    t0 = time.perf_counter()
    res = mcp.execute_qldpc_round(code_name=code_name, p_phys=0.0, rounds=1, n_shots=64)
    elapsed_s = time.perf_counter() - t0

    assert elapsed_s < 1.0
    assert res["n_data"] == exp_n
    assert res["n_logical"] == exp_k
    assert res["distance"] == exp_d
    assert res["feedlines_required"] == exp_feed
    assert res["css_commutativity_verified"] is True
    assert res["symplectic_logical_verified"] is True
    assert res["nonzero_syndrome_events_Z"] == 0
    assert res["nonzero_syndrome_events_X"] == 0
    assert res["n_logical_errors"] == 0
    assert res["p_logical_per_round_est"] == 0.0
    assert res["syndrome_valid_frac"] == 1.0


def test_qldpc_real_gf2_syndrome_extraction_decoding_and_logical_homology():
    mcp = MultiCellProgrammer()
    alg = _get_bb_code_algebra("BB_144_12_12")
    H_X, H_Z, L_X, L_Z = alg["H_X"], alg["H_Z"], alg["L_X"], alg["L_Z"]

    # 1. Zero-error deterministic injection
    z_vec = np.zeros(144, dtype=np.uint8)
    r0 = mcp.execute_qldpc_round("BB_144_12_12", injected_x_error=z_vec, injected_z_error=z_vec)
    assert r0["syndrome_Z_weight"] == 0
    assert r0["syndrome_X_weight"] == 0
    assert r0["decoded_syndrome_matched"] is True
    assert r0["logical_error_Z_observable"] is False
    assert r0["logical_error_X_observable"] is False

    # 2. Inject weight-3 X error + weight-2 Z error -> exact GF(2) parity checks & clean BP-OSD recovery
    e_x = np.zeros(144, dtype=np.uint8)
    e_x[[3, 41, 107]] = 1
    e_z = np.zeros(144, dtype=np.uint8)
    e_z[[12, 88]] = 1
    r_err = mcp.execute_qldpc_round("BB_144_12_12", p_phys=0.01, injected_x_error=e_x, injected_z_error=e_z)

    expected_syn_z = ((e_x @ H_Z.T) & 1).tolist()
    expected_syn_x = ((e_z @ H_X.T) & 1).tolist()
    assert r_err["syndrome_Z_vector"] == expected_syn_z
    assert r_err["syndrome_X_vector"] == expected_syn_x
    assert r_err["syndrome_Z_weight"] > 0
    assert r_err["syndrome_X_weight"] > 0
    assert r_err["decoded_syndrome_matched"] is True
    assert r_err["logical_error_Z_observable"] is False
    assert r_err["logical_error_X_observable"] is False
    assert r_err["p_logical_per_round_est"] == 0.0

    # 3. Inject exact nontrivial CSS logical X operator L_X[0]:
    # MUST produce identically zero Z-syndrome and trigger a logical Z observable flip!
    r_log = mcp.execute_qldpc_round("BB_144_12_12", injected_x_error=L_X[0])
    assert r_log["syndrome_Z_weight"] == 0
    assert r_log["correction_weight_X"] == 0
    assert r_log["logical_error_Z_observable"] is True
    assert r_log["p_logical_per_round_est"] == 1.0

    # 4. Monte Carlo sub-threshold vs above-threshold decoding transition
    t0 = time.perf_counter()
    mc_sub = mcp.execute_qldpc_round("BB_144_12_12", p_phys=0.002, rounds=1, n_shots=200, seed=77)
    assert (time.perf_counter() - t0) < 1.0
    assert mc_sub["nonzero_syndrome_events_Z"] > 0
    assert mc_sub["syndrome_valid_frac"] == 1.0
    assert mc_sub["p_logical_per_round_est"] < 0.01

    mc_hi = mcp.execute_qldpc_round("BB_144_12_12", p_phys=0.08, rounds=1, n_shots=120, seed=77)
    assert mc_hi["syndrome_valid_frac"] == 1.0
    assert mc_hi["n_osd_triggered"] > 0
    assert mc_hi["p_logical_per_round_est"] > 0.15


# ===========================================================================
# 7. Hyperfine Q16.16 BOED Integration & Zero Hardcoded Host Paths
# ===========================================================================

def test_hyperfine_boed_and_zero_hardcoded_host_paths():
    ctrl = AutoRecalController(seed=2026145)
    r_hf = ctrl.mitigate_hyperfine_thermal_drift(drift_Hz=350.0)
    assert r_hf["passed"] is True
    assert r_hf["max_relock_time_ms"] < 5.0
    assert r_hf["max_residual_error_Hz"] < 100.0

    bad_a = "/" + "home/berk"
    bad_b = "/" + "run/media/berk"
    for fp in (
        REPO_ROOT / "src" / "machine_control" / "auto_recal.py",
        REPO_ROOT / "src" / "machine_control" / "programmer.py",
        REPO_ROOT / "tests" / "test_control_physics_upgrades.py",
    ):
        txt = fp.read_text(encoding="utf-8")
        assert bad_a not in txt, f"Hardcoded host path found in {fp.name}"
        assert bad_b not in txt, f"Hardcoded mount path found in {fp.name}"


# ===========================================================================
# 8. Regression Tests for OBS-082, OBS-085, OBS-125, OBS-147
# ===========================================================================

def test_obs082_fpga_1687k_melt_abort_and_short_laser_pulse_no_index_error():
    from src.machine_control.auto_recal import AutoRecalConfig

    # 1) Extreme +75% surge trips hardwired 1687 K Si-melt RF abort -> servo_aom_gain == 0.0
    ctrl = AutoRecalController(seed=2026145)
    r_surge = ctrl.mitigate_laser_power_drift(drift_pct=75.0)
    surge_case = r_surge["cases"]["surge_plus"]
    assert surge_case["melt_abort_triggered"] is True
    assert surge_case["servo_aom_gain"] == 0.0
    assert surge_case["passed"] is False

    # 2) Short laser pulse (< 0.2 ms) must NOT raise IndexError
    ctrl_short = AutoRecalController(AutoRecalConfig(laser_pulse_nom_ms=0.1), seed=2026145)
    r_short = ctrl_short.mitigate_laser_power_drift(drift_pct=8.0)
    assert r_short["reference_T_peak_K"] > 300.0
    assert "surge_plus" in r_short["cases"]


def test_obs125_auto_recal_1d_spatial_ted_51ms_cooldown_and_updated_nominal():
    from src.machine_control.auto_recal import AutoRecalConfig

    cfg = AutoRecalConfig()
    assert cfg.sigma_anneal_nom_nm >= 0.39  # updated from stale 0.34 nm

    ctrl = AutoRecalController(cfg, seed=2026145)
    rng = np.random.default_rng(7)
    ref = ctrl._simulate_laser_flash_run(1.0, False, None, rng, aom_tau_us=15.0, aom_dead_time_us=10.0)
    # 51 ms total cooldown horizon (matching Exp130, not truncated 16 ms)
    assert ref["t_s"][-1] >= 0.050
    # Coupled 1D spatial TED PDE nominal sigma matches Exp130 (~0.39-0.41 nm)
    assert 0.37 <= ref["sigma_anneal_nm"] <= 0.43


def test_obs147_uhv_midpoint_checks_p2_and_blanker_latency_coupled_in_ode():
    ctrl = AutoRecalController(seed=2026145)

    # 1) Increasing blanker_latency_us strictly increases beam-on Langmuir & monolayer exposure inside ODE
    r_fast = ctrl.mitigate_vacuum_spike(peak_pressure_torr=3.5e-7, blanker_latency_us=0.05)
    r_slow = ctrl.mitigate_vacuum_spike(peak_pressure_torr=3.5e-7, blanker_latency_us=500.0)
    assert r_slow["exposure_langmuir_beam_on"] > r_fast["exposure_langmuir_beam_on"]
    assert r_slow["beam_on_monolayer_coverage_frac"] > r_fast["beam_on_monolayer_coverage_frac"]

    # 2) Wafer-chamber-origin spike (wafer_burst_fraction=1.0) trips interlock & locks at midpoint via p2_mid
    r_wafer = ctrl.mitigate_vacuum_spike(peak_pressure_torr=3.5e-8, wafer_burst_fraction=1.0)
    assert r_wafer["interlock_trip_detected"] is True
    assert r_wafer["locked_at_midpoint"] is True
    assert r_wafer["peak_ch2_wafer_torr"] >= 1.0e-8


def test_obs085_echo_cz_aligned_with_physical_m4_bus_dynamics():
    c0, c1 = _make_pair_certs()
    mcp = MultiCellProgrammer()
    r = mcp.execute_echo_cz(c0, c1, s_eps_uev=1.0, echo_pulses=1)
    # Physical Exp131/137 M4 flip-flop bus (~2 us gate, NOT 0.175 us; realistic 1/f error, NOT 0.975!)
    assert 1.5 <= r["cz_duration_us"] <= 2.5
    assert 0.75 <= r["echo_cz_bell_fidelity"] <= 0.92
    assert r["echo_cz_bell_fidelity"] > r["bare_cz_bell_fidelity"] + 0.15
