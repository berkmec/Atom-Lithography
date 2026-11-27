"""CLI: run the Atom Lithography Machine factory & CellISA program simulator.

Usage:
    PYTHONPATH=src python -m machine_control.sim --slots 2000 \
        [--preset v224|legacy|1k] [--atlas] \
        [--cal-mode spectral|shaped|grape] \
        [--program bell|ghz|qft3|repcode3] [--program-cells 3] \
        [--certs out.jsonl] [--prog-certs prog.jsonl]
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import math
from typing import Any

import numpy as np

from .config import (
    MachineConfig,
    elzerman_thermal_error,
    elzerman_zeeman_splitting_ueV,
    kapitza_electron_temp_K,
)
from .factory import Factory
from .programmer import AtomCellProgrammer, builtin_program


@dataclass(frozen=True)
class ElzermanSETConfig:
    """Dynamic microscopic rf-SET Kapitza + tunnel-rate + T1 readout parameters."""
    b_field_T: float = 0.1785            # M4 resonance field (vs 1.5 T standalone Elzerman)
    t_phonon_K: float = 0.020            # MXC phonon lattice temperature [K]
    set_power_W: float = 1.0e-13         # 0.1 pW SET reservoir dissipation
    set_volume_m3: float = 2.0e-19       # SET reservoir volume [m^3]
    mw_power_W: float = 0.0              # Optional MW pulse dissipation in feed/2DEG [W]
    mw_volume_m3: float = 2.0e-12        # MW dissipation reservoir volume [m^3]
    kapitza_sigma_W_m3_K5: float = 1.0e8 # Electron-phonon coupling Sigma [W/(m^3 K^5)]
    gamma_tunnel_kHz: float = 25.0       # Bare donor-SET tunnel rate Gamma_0 [kHz]
    t1_spin_us: float = 500.0            # Donor electron spin T1 [us]
    readout_window_us: float = 100.0     # Readout integration window [us]
    tau_snr10_us: float = 62.7           # Exp125 rf-SET integration time for SNR=10 [us]
    n_shots: int = 2000                  # Monte Carlo shots per spin state


def simulate_elzerman_set_readout(
    cfg: ElzermanSETConfig | None = None,
    seed: int = 2026013,
) -> dict[str, Any]:
    """Dynamic Monte Carlo rf-SET Elzerman readout model with Kapitza T^5 electron heating.

    Couples:
      1. Sub-kelvin electron-phonon Kapitza bottleneck: P = Sigma * V * (T_e^5 - T_ph^5)
         for SET reservoir bias dissipation and optional MW pulse heating.
      2. Zeeman splitting E_Z(B) vs k_B T_e Fermi-Dirac tunnel rates (Gamma_out^up,
         Gamma_in^down, and thermal dark-tunneling Gamma_dark^down).
      3. Time-domain Monte Carlo trajectory simulation of spin-|up> and spin-|down>
         blips competing against spin-T1 relaxation and Exp125 rf-SET shot/HEMT noise.
    """
    c = cfg or ElzermanSETConfig()
    rng = np.random.default_rng(int(seed))

    t_e_set = kapitza_electron_temp_K(
        c.t_phonon_K, c.set_power_W, c.set_volume_m3, c.kapitza_sigma_W_m3_K5
    )
    t_e_mw = (
        kapitza_electron_temp_K(
            c.t_phonon_K, c.mw_power_W, c.mw_volume_m3, c.kapitza_sigma_W_m3_K5
        )
        if c.mw_power_W > 0.0
        else c.t_phonon_K
    )
    t_e_K = max(t_e_set, t_e_mw)

    e_z_ueV = elzerman_zeeman_splitting_ueV(c.b_field_T)
    p_fermi = elzerman_thermal_error(c.b_field_T, t_e_K)

    # Fermi-Dirac weighted tunnel rates [1/us]
    g0_per_us = max(1e-6, float(c.gamma_tunnel_kHz) * 1e-3)
    gamma_out_up = g0_per_us * (1.0 - p_fermi)     # desired |up> tunnel-out rate
    gamma_dark_dn = g0_per_us * p_fermi            # thermal dark tunnel-out of |down>
    gamma_in_dn = g0_per_us * (1.0 - p_fermi)      # reload rate into |down>
    gamma_t1 = 1.0 / max(1e-3, float(c.t1_spin_us))
    t_ro = max(1.0, float(c.readout_window_us))

    # Analytic reference errors for a typical blip window
    tau_blip_ref = min(t_ro * 0.5, 1.0 / max(gamma_in_dn, 1e-6))
    snr_ref = 10.0 * math.sqrt(max(tau_blip_ref, 1e-6) / max(c.tau_snr10_us, 1e-6))
    err_shot_analytic = 0.5 * math.erfc(snr_ref / (2.0 * math.sqrt(2.0)))
    err_t1_analytic = 1.0 - math.exp(-t_ro * gamma_t1)

    # Time-domain Monte Carlo for n_shots of |up> and n_shots of |down>
    n = max(100, int(c.n_shots))
    # --- Spin |up>: competes between tunnel-out (gamma_out_up) and T1 decay (gamma_t1) ---
    t_out_up = rng.exponential(1.0 / max(gamma_out_up, 1e-9), size=n)
    t_decay_up = rng.exponential(1.0 / max(gamma_t1, 1e-9), size=n)
    escaped_up = (t_out_up < t_ro) & (t_out_up < t_decay_up)
    # Blip duration before reload (truncated by end of readout window)
    t_reload_up = rng.exponential(1.0 / max(gamma_in_dn, 1e-9), size=n)
    blip_up = np.where(escaped_up, np.minimum(t_reload_up, t_ro - t_out_up), 0.0)
    # Shot/HEMT noise detection probability on observed blip (threshold at 0.5 * signal)
    snr_up = 10.0 * np.sqrt(np.maximum(blip_up, 0.0) / max(c.tau_snr10_us, 1e-6))
    # Matched-filter noisy statistic for each shot: mean = snr_up (if escaped) else 0, std = 1
    z_up = snr_up + rng.normal(0.0, 1.0, size=n)
    thr_z = 0.5 * max(snr_ref, 1.0)
    det_up = z_up >= thr_z
    # Include thermal Fermi initialization/level-broadening floor for |up> missed-escape
    mc_err_up = float(1.0 - np.mean(det_up))

    # --- Spin |down>: false blip via thermal Fermi dark tunneling or shot noise ---
    if gamma_dark_dn > 1e-12:
        t_dark_dn = rng.exponential(1.0 / gamma_dark_dn, size=n)
        dark_escaped = t_dark_dn < t_ro
        t_reload_dn = rng.exponential(1.0 / max(gamma_in_dn, 1e-9), size=n)
        blip_dn = np.where(dark_escaped, np.minimum(t_reload_dn, t_ro - t_dark_dn), 0.0)
    else:
        dark_escaped = np.zeros(n, dtype=bool)
        blip_dn = np.zeros(n, dtype=float)
    snr_dn = 10.0 * np.sqrt(np.maximum(blip_dn, 0.0) / max(c.tau_snr10_us, 1e-6))
    z_dn = snr_dn + rng.normal(0.0, 1.0, size=n)
    det_dn_false = z_dn >= thr_z
    mc_err_dn = float(np.mean(det_dn_false))

    mc_total_err = 0.5 * (mc_err_up + mc_err_dn)
    # Total fidelity cannot exceed (1 - p_fermi) thermal ceiling
    readout_fid = max(0.5, min(1.0 - mc_total_err, 1.0 - p_fermi))
    viable = bool(readout_fid >= 0.99 and p_fermi < 0.01)

    return {
        "model": "dynamic_rf_set_kapitza_t5_elzerman_mc",
        "b_field_T": float(c.b_field_T),
        "t_phonon_K": float(c.t_phonon_K),
        "t_e_set_K": round(t_e_set, 6),
        "t_e_mw_K": round(t_e_mw, 6),
        "t_e_K": round(t_e_K, 6),
        "E_Z_ueV": round(e_z_ueV, 4),
        "thermal_fermi_error": round(p_fermi, 6),
        "shot_noise_error_analytic": round(err_shot_analytic, 6),
        "t1_decay_error_analytic": round(err_t1_analytic, 6),
        "snr_ref": round(snr_ref, 4),
        "mc_error_up": round(mc_err_up, 6),
        "mc_error_down": round(mc_err_dn, 6),
        "mc_total_error": round(mc_total_err, 6),
        "readout_fidelity": round(readout_fid, 6),
        "elzerman_viable": viable,
        "recommended_mechanism": "Elzerman_MXC_20mK" if viable else "Dispersive_PSB_M4_TWPA",
        "n_shots": n,
    }


def config_from_preset(preset: str) -> MachineConfig:
    key = preset.strip().lower()
    if key == "v400":
        return MachineConfig.v400_bayesian()
    if key == "v400_real_si29":
        return MachineConfig.v400_real_si29()
    if key in ("m4", "v400_m4_dispersive"):
        return MachineConfig.v400_m4_dispersive()
    if key == "v300":
        return MachineConfig.v300_baseline()
    if key == "v224":
        return MachineConfig.v224_baseline()
    if key == "1k":
        return MachineConfig.v224_1k_upgrade()
    if key == "legacy":
        return MachineConfig.legacy_exp65()
    raise ValueError(
        f"Unknown preset '{preset}'; expected v400, v400_real_si29, m4, v300, v224, legacy, or 1k"
    )


def main(argv: list[str] | None = None):
    ap = argparse.ArgumentParser(description="Atom Lithography Machine control & CellISA v3.0 CLI")
    ap.add_argument("--slots", type=int, default=2000)
    ap.add_argument("--preset", choices=["v400", "v300", "v224", "legacy", "1k"], default="v300")
    ap.add_argument(
        "--atlas",
        action="store_true",
        help="verification mode: real Exp48 selection per attempt (slow)",
    )
    ap.add_argument(
        "--cal-mode",
        choices=["spectral", "shaped", "grape"],
        default="spectral",
        help="per-register calibration mode",
    )
    ap.add_argument(
        "--program",
        choices=["bell", "ghz", "qft3", "repcode3"],
        default=None,
        help="optional CellISA program to compile and verify on certified cells",
    )
    ap.add_argument(
        "--program-mode",
        choices=["shaped", "grape"],
        default="shaped",
        help="pulse synthesis backend for CellISA program compilation",
    )
    ap.add_argument(
        "--program-cells",
        type=int,
        default=3,
        help="number of certified cells to run ARRAY_EXEC on when --program is set",
    )
    ap.add_argument("--certs", default=None, help="output JSONL path for register certificates")
    ap.add_argument("--prog-certs", default=None, help="output JSONL path for program certificates")
    args = ap.parse_args(argv)

    cfg = config_from_preset(args.preset)
    selector = None
    if args.atlas:
        from .selector import AtlasSelector
        selector = AtlasSelector(cfg.abundance_pct)

    rep = Factory(cfg=cfg, selector=selector, cal_mode=args.cal_mode).run(
        args.slots, cert_path=args.certs
    )
    print(
        f"preset={cfg.preset_name} slots={rep.slots} certified={rep.certified} "
        f"slot_success={rep.slot_success:.3f}"
    )
    print(
        f"shots/register={rep.shots_per_register:.2f} "
        f"specs/register={rep.specs_per_register:.2f} "
        f"subsites={rep.total_subsites}"
    )
    print(f"analytic certified/day (Exp65/v224 formulas) = {rep.certified_per_day_analytic:.4g}")

    if args.program and rep.certificates:
        prog = builtin_program(args.program)
        programmer = AtomCellProgrammer(
            b_field_T=cfg.b_sample_T,
            pulse_mode=args.program_mode,
            readout_visibility=cfg.readout_visibility,
            pulse_error_eps=cfg.pulse_error_eps,
        )
        chosen = rep.certificates[: max(1, min(args.program_cells, len(rep.certificates)))]
        res = programmer.execute_array(
            chosen, prog, verify_corners=True, out_jsonl=args.prog_certs
        )
        for sched, pcert in res:
            print(
                f"  [CellISA {pcert.program_name}] {pcert.register_id}: "
                f"pulses={pcert.pulse_count} dur={pcert.total_duration_us:.1f}us "
                f"F_nom={pcert.nominal_state_fidelity:.4f} "
                f"F_corner_min={pcert.corner_min_fidelity:.4f} "
                f"dd_gain={pcert.dd_coherence_gain} "
                f"cert={pcert.certified} sha256={pcert.sha256[:12]}..."
            )
    return rep


if __name__ == "__main__":
    main()
