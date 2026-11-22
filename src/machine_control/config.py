"""Machine specification constants, each traced to a registered experiment.

v2.1 (2026-11-23, Carbon RED F1+F3 closure):
- Preserves full backwards compatibility for ``MachineConfig()`` /
  ``MachineConfig.legacy_exp65()`` default arguments.
- Locks ``v224_baseline()`` and ``v300_baseline()`` to the unified Arch-B
  equal-pitch array + Exp124 HDA-HiRes + Exp127 Cold-100K IBIC baseline:
    * ``beamlets = 1024`` (32x32 @ 0.50 mm pitch = 16.0x16.0 mm, diagonal
      22.63 mm < 28.0 mm S1.6/S2.1 bore, 16x 64-ch blanker tiles)
    * ``shot_cycle_s = 0.015`` (15 ms/shot, Exp124 HDA-HiRes; raw write
      capacity 2.95e9 shots/day at 50% duty >> ~1.97e8/day readout limit)
    * ``detector_eta = 0.9994`` (Exp127 Cold-100K / 1.2 us / 1 GOhm @ 5 keV P91)
    * ``NL = 160``, ``56`` chains (8960 ch), ``S6.8=D`` MXC 20 mK, ``f=1%`` Mode B.
- Enforces BOTH alpha=1 and alpha=2 DD feasibility (Exp68 robust spec).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MachineConfig:
    # Operating point (Exp68 robust spec)
    mode: str = "B"                     # epitaxial bath + implanted donors
    abundance_pct: float = 1.0          # robust under alpha=1 and alpha=2
    dd_pulses: int = 64                 # margin-optimal band 64-128
    pulse_error_eps: float = 1e-3       # per-pulse coherence error budget
    require_both_alpha: bool = True     # Exp68: enforce alpha=1 AND alpha=2
    # Selection (Exp59/62 yields at the operating point)
    bath_yield: float = 0.51            # f=1% pulse-aware selection yield
    # Writer / detector (Exp66/67/72/91/124/127)
    implant_energy_keV: float = 10.0    # legacy default; v224/v300 uses 5.0 keV (P91)
    detector_eta: float = 0.99          # C<=0.5 pF pixel diode (Exp72/127)
    stray_survival: float = 0.5         # Exp67 contamination factor s
    shot_cycle_s: float = 1e-3          # legacy Exp65; v224/v300 uses 0.015 s (Exp124 HDA-HiRes)
    spot_sigma_nm: float = 2.0          # Exp66 EUV class; P91 uses 1.5 nm
    # Spectroscopy / loop (Exp50/65/67/116/117)
    spec_sigma_Hz: float = 200.0        # measured-line uncertainty class
    spec_time_s: float = 1.0
    blank_prob: float = 0.5             # failed attempt classified retryable
    max_retries: int = 3
    # Parallelism (Exp65 / Exp70 / Exp78 / Exp112 / Exp124 Arch-B)
    beamlets: int = 1_000_000           # legacy Exp65; v224/v300 locked to 1024 (32x32 @ 0.50 mm)
    beam_pitch_mm: float = 0.032        # legacy 32 um; v224/v300 Arch-B locked to 0.50 mm
    readout_channels: int = 10_000      # legacy Exp70: 5x2000; v224/v300: 56x160=8960
    nl_per_chain: int = 2_000           # multiplexed resonators per readout chain
    readout_chains: int = 5
    duty_cycle: float = 0.5
    # Cryo / magnetic / readout architecture (Exp109/116/117/121/125)
    readout_temp_K: float = 0.020       # MXC 20 mK Elzerman baseline (S6.8=D)
    cryo_stage_class: str = "D"         # D = dilution refrigerator, C = 1 K stage
    readout_mechanism: str = "Elzerman_MXC_20mK"
    readout_visibility: float = 0.99    # single-shot readout visibility
    b_sample_T: float = 1.5             # Exp116/125 sample B-field (T)
    b_resonator_max_T: float = 0.4      # Exp109/125 NbTiN resonator B-field ceiling (T)
    # Quality gates (DESIGN section 1)
    q_min: float = 0.85                 # DD GHZ quality gate (Exp63)
    flip_min: float = 0.99              # calibrated pulse corner gate (Exp61)
    preset_name: str = "legacy_exp65"
    seed: int = 20261020

    @classmethod
    def legacy_exp65(cls, **overrides) -> "MachineConfig":
        """Original 2026-10-20 Exp65-72 baseline snapshot (backwards-compatible)."""
        return cls(**overrides)

    @classmethod
    def v224_baseline(cls, **overrides) -> "MachineConfig":
        """Locked Arch-B / Exp124-127 baseline (synced with DESIGN v3.0):
        - Arch-B equal-pitch array: 1024 beamlets (32x32 @ 0.50 mm = 16.0x16.0 mm,
          diagonal 22.63 mm < 28.0 mm bore; 16x 64-ch blanker tiles)
        - Exp124 HDA-HiRes 10->5 keV P91 column: shot_cycle_s = 0.015 s (15 ms/shot ->
          2.95e9 shots/day @ 50% duty >> readout-limited ~1.97e8/day)
        - Exp127 Cold-100K / 1.2 us / 1 GOhm IBIC: detector_eta = 0.9994 @ 5 keV, C_det=0.5 pF
        - Mode B, f = 1% 29Si epitaxial bath (bath_yield = 0.51), dual-alpha DD
        - Readout: S6.8=D MXC 20 mK Elzerman, NL=160, 56 chains (8960 ch),
          B_sample = 1.5 T, B_res <= 0.4 T (Exp125: 22.3 uT).
        """
        params = dict(
            mode="B",
            abundance_pct=1.0,
            dd_pulses=64,
            pulse_error_eps=1e-3,
            require_both_alpha=True,
            bath_yield=0.51,
            implant_energy_keV=5.0,
            detector_eta=0.9994,
            stray_survival=0.5,
            shot_cycle_s=0.015,
            spot_sigma_nm=1.5,
            spec_sigma_Hz=200.0,
            spec_time_s=1.0,
            blank_prob=0.5,
            max_retries=3,
            beamlets=1_024,
            beam_pitch_mm=0.50,
            nl_per_chain=160,
            readout_chains=56,
            readout_channels=56 * 160,
            duty_cycle=0.5,
            readout_temp_K=0.020,
            cryo_stage_class="D",
            readout_mechanism="Elzerman_MXC_20mK",
            readout_visibility=0.99,
            b_sample_T=1.5,
            b_resonator_max_T=0.4,
            q_min=0.85,
            flip_min=0.99,
            preset_name="v224_baseline",
            seed=20261122,
        )
        params.update(overrides)
        return cls(**params)

    @classmethod
    def v300_baseline(cls, **overrides) -> "MachineConfig":
        """DESIGN.md v3.0 / Exp124-128 canonical baseline (identical locked Arch-B/Cold-100K params)."""
        overrides.setdefault("preset_name", "v300_baseline")
        return cls.v224_baseline(**overrides)

    @classmethod
    def v224_1k_upgrade(cls, **overrides) -> "MachineConfig":
        """Exp117/118 1 K hot-readout PSB cost-reduction alternative:
        - S6.8=C (1 K stage instead of dilution MXC 20 mK)
        - Ancilla-dot Pauli spin blockade (V=0.959, 3.165x averaging penalty)
        - Same locked Arch-B 1024 beamlets @ 15 ms, 5 keV P91, NL=160 x 56 chains.
        """
        params = dict(
            mode="B",
            abundance_pct=1.0,
            dd_pulses=64,
            pulse_error_eps=1e-3,
            require_both_alpha=True,
            bath_yield=0.51,
            implant_energy_keV=5.0,
            detector_eta=0.9994,
            stray_survival=0.5,
            shot_cycle_s=0.015,
            spot_sigma_nm=1.5,
            spec_sigma_Hz=200.0,
            spec_time_s=3.165,
            blank_prob=0.5,
            max_retries=3,
            beamlets=1_024,
            beam_pitch_mm=0.50,
            nl_per_chain=160,
            readout_chains=56,
            readout_channels=56 * 160,
            duty_cycle=0.5,
            readout_temp_K=1.0,
            cryo_stage_class="C",
            readout_mechanism="PSB_1K_ancilla",
            readout_visibility=0.959,
            b_sample_T=1.5,
            b_resonator_max_T=0.4,
            q_min=0.85,
            flip_min=0.99,
            preset_name="v224_1k_upgrade",
            seed=20261122,
        )
        params.update(overrides)
        return cls(**params)


YIELDS_MODE_B = {0.5: 0.26, 1.0: 0.51, 2.0: 0.69, 4.7: 0.66}   # Exp59/62
DD_FEASIBLE = {  # (abundance, alpha) -> Q>=0.85 exists at eps=1e-3 (Exp68)
    (0.5, 1): True, (0.5, 2): True, (1.0, 1): True, (1.0, 2): True,
    (2.0, 1): False, (2.0, 2): True, (4.7, 1): False, (4.7, 2): False,
}


def dd_is_feasible(abundance_pct: float, require_both_alpha: bool = True) -> bool:
    """Return True if DD operating point passes Exp68 Q>=0.85 gate."""
    ok_a2 = DD_FEASIBLE.get((abundance_pct, 2), False)
    if not require_both_alpha:
        return ok_a2
    ok_a1 = DD_FEASIBLE.get((abundance_pct, 1), False)
    return bool(ok_a1 and ok_a2)
