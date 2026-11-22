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

from .config import MachineConfig
from .factory import Factory
from .programmer import AtomCellProgrammer, builtin_program


def config_from_preset(preset: str) -> MachineConfig:
    key = preset.strip().lower()
    if key == "v300":
        return MachineConfig.v300_baseline()
    if key == "v224":
        return MachineConfig.v224_baseline()
    if key == "1k":
        return MachineConfig.v224_1k_upgrade()
    if key == "legacy":
        return MachineConfig.legacy_exp65()
    raise ValueError(f"Unknown preset '{preset}'; expected v300, v224, legacy, or 1k")


def main(argv: list[str] | None = None):
    ap = argparse.ArgumentParser(description="Atom Lithography Machine control & CellISA CLI (v2.1)")
    ap.add_argument("--slots", type=int, default=2000)
    ap.add_argument("--preset", choices=["v300", "v224", "legacy", "1k"], default="v300")
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
