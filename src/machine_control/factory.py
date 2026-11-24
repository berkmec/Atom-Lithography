"""Factory orchestrator: write -> detect -> measure -> select -> calibrate.

Produces per-register certificates and throughput metrics that cross-check
against the Exp65 analytic pipeline model and v2.24 golden-band presets.

v2.0 (2026-11-22):
- Enforces BOTH alpha=1 and alpha=2 DD feasibility (Exp68 robust spec) when
  ``cfg.require_both_alpha`` is True.
- Applies stray-ion survival factor ``s`` consistently in AtlasSelector mode as
  well as StochasticSelector mode.
- Tracks ``total_subsites`` in ``FactoryReport`` (previously unused local var).
- Supports selectable calibration mode (``spectral`` default, ``shaped``, ``grape``).

v2.1 (Step 2A real 1% 29Si lattice-bath upgrade):
- Adds ``bath_mode="real_si29"`` (and ``Factory.with_real_si29_bath(...)``)
  running genuine 45,214-site diamond-cubic silicon 1% 29Si bath clouds
  (full ~452-spin clutter forest + dipolar broadening + T2* envelope + B_perp)
  through ``AdaptiveBOEDSpectroscopy`` and ``calibrate(...)``.
- Preserves 100% backwards compatibility with all existing ``bath_mode="synthetic"``
  workflows, CLI signatures, and tests.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from .calibrator import calibrate
from .config import MachineConfig, dd_is_feasible
from .selector import StochasticSelector
from .spectroscopy import Spectrometer
from .writer import CountedWriter


@dataclass
class Certificate:
    register_id: str
    slot: int
    attempts: int
    shots: int
    min_spacing_Hz: float
    dd_quality_gate: bool
    lines_Hz: list
    b_perp_Hz: list | None = None
    bath_mode: str = "synthetic"


@dataclass
class FactoryReport:
    slots: int
    certified: int
    slot_success: float
    shots_total: int
    specs_total: int
    shots_per_register: float
    specs_per_register: float
    certified_per_day_analytic: float
    certificates: list = field(default_factory=list)
    total_subsites: int = 0
    preset_name: str = "legacy_exp65"
    total_spec_time_s: float = 0.0
    mean_spec_time_ms: float = 0.0
    early_aborts: int = 0
    bath_mode: str = "synthetic"
    real_bath_attempts: int = 0
    real_bath_mean_spins: float = 0.0
    real_bath_sub_linewidth_warnings: int = 0
    real_bath_a_par_rmse_Hz: float | None = None
    real_bath_b_perp_rmse_Hz: float | None = None


class Factory:
    def __init__(
        self,
        cfg: MachineConfig | None = None,
        selector=None,
        cal_mode: str = "spectral",
        adaptive_spec=None,
        bath_mode: str = "synthetic",
        estimate_b_perp: bool = True,
    ):
        if bath_mode not in ("synthetic", "real_si29"):
            raise ValueError(f"Unknown bath_mode '{bath_mode}'; expected 'synthetic' or 'real_si29'")
        self.cfg = cfg or MachineConfig()
        self.cal_mode = str(cal_mode)
        self.bath_mode = str(bath_mode)
        self.estimate_b_perp = bool(estimate_b_perp)
        self.rng = np.random.default_rng(self.cfg.seed)
        self.writer = CountedWriter(self.cfg.detector_eta, self.rng)
        self.spec = Spectrometer(self.cfg.spec_sigma_Hz, self.cfg.blank_prob, self.rng)
        self.selector = selector or StochasticSelector(self.cfg.bath_yield, self.rng)
        self.dd_ok = dd_is_feasible(self.cfg.abundance_pct, self.cfg.require_both_alpha)
        self.adaptive_spec = adaptive_spec
        if self.adaptive_spec is None and self.bath_mode == "real_si29":
            from .adaptive_spectroscopy import AdaptiveBOEDSpectroscopy
            self.adaptive_spec = AdaptiveBOEDSpectroscopy(
                rng=np.random.default_rng(self.cfg.seed + 132),
                estimate_b_perp=self.estimate_b_perp,
            )
        elif self.adaptive_spec is None and self.cfg.spectroscopy_mode == "bayesian":
            from .adaptive_spectroscopy import BayesianSpectrometer
            self.adaptive_spec = BayesianSpectrometer(rng=np.random.default_rng(self.cfg.seed + 132))
        self._last_failure_kind: str | None = None
        self._real_bath_spin_counts: list[int] = []
        self._real_bath_a_errs: list[float] = []
        self._real_bath_b_errs: list[float] = []
        self._real_bath_sub_lw_warnings: int = 0

    @classmethod
    def with_real_si29_bath(
        cls,
        cfg: MachineConfig | None = None,
        selector=None,
        cal_mode: str = "spectral",
        adaptive_spec=None,
        estimate_b_perp: bool = True,
    ) -> "Factory":
        """Construct a Factory operating in real diamond-cubic Si 29Si lattice-bath mode."""
        use_cfg = cfg if cfg is not None else MachineConfig.v400_bayesian()
        return cls(
            cfg=use_cfg,
            selector=selector,
            cal_mode=cal_mode,
            adaptive_spec=adaptive_spec,
            bath_mode="real_si29",
            estimate_b_perp=estimate_b_perp,
        )

    def _attempt_real_si29(self):
        """One donor shot through genuine diamond-cubic Si 29Si bath + AdaptiveBOEDSpectroscopy."""
        from .adaptive_spectroscopy import SPECTRAL_GATE_HZ, generate_real_si29_bath_spectrum

        shot = self.writer.fire_single()
        self.spec.sessions += 1
        self._last_failure_kind = None

        stray_contaminated = False
        if shot.implanted > 1:
            surv_prob = self.cfg.stray_survival ** (shot.implanted - 1)
            if self.rng.random() >= surv_prob:
                stray_contaminated = True

        site_indices = None
        donor_present = True
        is_stoch = isinstance(self.selector, StochasticSelector)
        if not is_stoch:
            # Real AtlasSelector: pull exact occupied lattice indices from its deterministic draw
            _atlas_res = self.selector.attempt()
            if hasattr(self.selector, "_seed59") and hasattr(self.selector, "n_sites") and hasattr(self.selector, "m"):
                rng_cloud = np.random.default_rng(
                    self.selector._seed59(self.selector.seed + self.selector.counter - 1)
                )
                site_indices = np.sort(
                    rng_cloud.choice(self.selector.n_sites, size=self.selector.m, replace=False)
                )
            donor_present = True
        else:
            p_blank_attempt = max(0.0, min(1.0, (1.0 - self.cfg.bath_yield) * self.cfg.blank_prob))
            if self.rng.random() < p_blank_attempt:
                donor_present = False

        cand = generate_real_si29_bath_spectrum(
            rng=self.rng,
            abundance_pct=self.cfg.abundance_pct,
            donor_present=donor_present,
            b_field_T=self.cfg.b_sample_T,
            site_indices=site_indices,
        )
        if donor_present:
            self._real_bath_spin_counts.append(int(cand.metadata.get("n_bath_spins", 0)))

        boed_res = self.adaptive_spec.inspect_candidate(cand)
        if not boed_res.accepted or stray_contaminated:
            self._last_failure_kind = "blank" if boed_res.classification == "blank" else "consumed"
            return None, shot.shots_fired

        # Record honest localization error and any sub-linewidth leakage against ground-truth bath
        if cand.all_a_par_Hz is not None and len(cand.all_a_par_Hz) > 0:
            all_abs = np.abs(cand.all_a_par_Hz)
            for k, fhat in enumerate(boed_res.estimated_lines_Hz):
                j = int(np.argmin(np.abs(all_abs - fhat)))
                self._real_bath_a_errs.append(float(fhat - all_abs[j]))
                if cand.all_transition_gaps_Hz is not None and float(cand.all_transition_gaps_Hz[j]) < SPECTRAL_GATE_HZ:
                    self._real_bath_sub_lw_warnings += 1
                if (
                    boed_res.estimated_b_perp_Hz is not None
                    and cand.all_b_perp_Hz is not None
                    and k < len(boed_res.estimated_b_perp_Hz)
                ):
                    self._real_bath_b_errs.append(float(boed_res.estimated_b_perp_Hz[k] - cand.all_b_perp_Hz[j]))

        cal = calibrate(
            boed_res.estimated_lines_Hz,
            mode=self.cal_mode,
            b_field_T=self.cfg.b_sample_T,
            flip_min=self.cfg.flip_min,
        )
        if not cal.certified:
            self._last_failure_kind = "consumed"
            return None, shot.shots_fired
        b_perp_out = (
            [float(v) for v in boed_res.estimated_b_perp_Hz]
            if boed_res.estimated_b_perp_Hz is not None
            else None
        )
        return (cal, boed_res.estimated_lines_Hz, b_perp_out), shot.shots_fired

    def _attempt(self):
        """One donor shot (Mode B): counted write + selection + measure + calibrate."""
        if self.bath_mode == "real_si29":
            return self._attempt_real_si29()

        self._last_failure_kind = None
        shot = self.writer.fire_single()
        is_stoch = isinstance(self.selector, StochasticSelector)
        if is_stoch:
            p_eff = self.writer.effective_yield(self.cfg.bath_yield, self.cfg.stray_survival)
            res = self.selector.attempt(p_eff)
        else:
            # Real AtlasSelector: apply stray-ion contamination explicitly for k > 1
            res = self.selector.attempt()
            if res.success and shot.implanted > 1:
                surv_prob = self.cfg.stray_survival ** (shot.implanted - 1)
                if self.rng.random() >= surv_prob:
                    res.success = False
                    res.true_lines_Hz = None
                    res.info["stray_contaminated"] = True

        # A spectroscopy session is spent on every attempt (how failure is discovered),
        # matching Exp65 measure-capacity accounting; in Bayesian BOED mode, blank/crowded
        # candidates early-abort in < 15 ms instead of wasting 1.0 s.
        if self.adaptive_spec is not None:
            from .adaptive_spectroscopy import (
                CandidateSpectrum,
                compute_min_transition_spacing_Hz,
                sample_candidate_population,
            )
            self.spec.sessions += 1
            if not res.success or res.true_lines_Hz is None:
                is_blank = (self.rng.random() < self.cfg.blank_prob)
                if is_blank:
                    cand = CandidateSpectrum("blank", False, np.zeros(0, dtype=float), 0.0)
                else:
                    # Randomized crowded donor candidate (colliding pair or <8 lines)
                    cand = sample_candidate_population(1, self.rng, p_working=0.0, p_crowded=1.0)[0]
                self.adaptive_spec.inspect_candidate(cand)
                return None, shot.shots_fired
            true_l = np.sort(np.abs(np.asarray(res.true_lines_Hz, dtype=float)))
            cand = CandidateSpectrum("working", True, true_l, compute_min_transition_spacing_Hz(true_l))
            boed_res = self.adaptive_spec.inspect_candidate(cand)
            if not boed_res.accepted:
                return None, shot.shots_fired
            cal = calibrate(
                boed_res.estimated_lines_Hz,
                mode=self.cal_mode,
                b_field_T=self.cfg.b_sample_T,
                flip_min=self.cfg.flip_min,
            )
            if not cal.certified:
                return None, shot.shots_fired
            return (cal, boed_res.estimated_lines_Hz, None), shot.shots_fired

        if not res.success:
            self.spec.measure(np.zeros(1), donor_present=False)
            return None, shot.shots_fired
        meas = self.spec.measure(res.true_lines_Hz, donor_present=True)
        cal = calibrate(
            meas.lines_Hz,
            mode=self.cal_mode,
            b_field_T=self.cfg.b_sample_T,
            flip_min=self.cfg.flip_min,
        )
        if not cal.certified:
            return None, shot.shots_fired
        return (cal, meas.lines_Hz, None), shot.shots_fired

    def run(self, slots: int, cert_path: str | Path | None = None) -> FactoryReport:
        certs: list[Certificate] = []
        shots0, specs0 = self.writer.total_shots, self.spec.sessions
        spec_ms0 = self.adaptive_spec.total_time_ms if self.adaptive_spec is not None else 0.0
        aborts0 = self.adaptive_spec.early_aborts if self.adaptive_spec is not None else 0
        rb_spins0 = len(self._real_bath_spin_counts)
        rb_a0 = len(self._real_bath_a_errs)
        rb_b0 = len(self._real_bath_b_errs)
        rb_sw0 = self._real_bath_sub_lw_warnings
        total_subsites = 0
        for s in range(slots):
            used_subsites = 1
            cal = None
            attempts = 0
            slot_shots = 0
            while attempts < self.cfg.max_retries and cal is None:
                attempts += 1
                cal, fired = self._attempt()
                slot_shots += fired
                if cal is None and attempts < self.cfg.max_retries:
                    fail_kind = self._last_failure_kind or self.spec.classify_failure()
                    if fail_kind == "consumed":
                        used_subsites += 1
            total_subsites += used_subsites
            if cal is not None and self.dd_ok:
                cal_res, lines, b_perp = cal
                certs.append(Certificate(
                    register_id=f"ALM-{s:06d}",
                    slot=s,
                    attempts=attempts,
                    shots=slot_shots,
                    min_spacing_Hz=cal_res.min_spacing_Hz,
                    dd_quality_gate=True,
                    lines_Hz=[float(v) for v in lines],
                    b_perp_Hz=b_perp,
                    bath_mode=self.bath_mode,
                ))
        n = len(certs)
        shots = self.writer.total_shots - shots0
        specs = self.spec.sessions - specs0
        if self.adaptive_spec is not None:
            tot_spec_ms = self.adaptive_spec.total_time_ms - spec_ms0
            early_aborts = self.adaptive_spec.early_aborts - aborts0
        else:
            tot_spec_ms = specs * self.cfg.spec_time_s * 1e3
            early_aborts = 0
        mean_spec_ms = float(tot_spec_ms / specs) if specs else 0.0

        rb_spins_run = self._real_bath_spin_counts[rb_spins0:]
        rb_a_run = self._real_bath_a_errs[rb_a0:]
        rb_b_run = self._real_bath_b_errs[rb_b0:]
        rb_sw_run = self._real_bath_sub_lw_warnings - rb_sw0
        rb_a_rmse = (
            float(np.sqrt(np.mean(np.square(rb_a_run)))) if rb_a_run else None
        )
        rb_b_rmse = (
            float(np.sqrt(np.mean(np.square(rb_b_run)))) if rb_b_run else None
        )

        # Exp65/132 analytic cross-check (uses measured mean_spec_s when adaptive_spec is active)
        p_eff = self.writer.effective_yield(self.cfg.bath_yield, self.cfg.stray_survival)
        q = 1.0 - p_eff
        slot_p = 1.0 - q ** self.cfg.max_retries
        exp_attempts = sum(q ** i for i in range(self.cfg.max_retries)) / max(slot_p, 1e-12)
        eff_spec_s = (mean_spec_ms * 1e-3) if (self.adaptive_spec is not None and specs > 0) else self.cfg.spec_time_s
        analytic = self._analytic_rate(exp_attempts, spec_time_s_override=eff_spec_s)
        rep = FactoryReport(
            slots=slots,
            certified=n,
            slot_success=float(n / slots) if slots else 0.0,
            shots_total=int(shots),
            specs_total=int(specs),
            shots_per_register=float(shots / n) if n else float("inf"),
            specs_per_register=float(specs / n) if n else float("inf"),
            certified_per_day_analytic=float(analytic),
            certificates=certs,
            total_subsites=total_subsites,
            preset_name=self.cfg.preset_name,
            total_spec_time_s=float(tot_spec_ms * 1e-3),
            mean_spec_time_ms=mean_spec_ms,
            early_aborts=int(early_aborts),
            bath_mode=self.bath_mode,
            real_bath_attempts=len(rb_spins_run),
            real_bath_mean_spins=float(np.mean(rb_spins_run)) if rb_spins_run else 0.0,
            real_bath_sub_linewidth_warnings=int(rb_sw_run),
            real_bath_a_par_rmse_Hz=rb_a_rmse,
            real_bath_b_perp_rmse_Hz=rb_b_rmse,
        )
        if cert_path:
            out = Path(cert_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("w", encoding="utf-8") as f:
                for c in certs:
                    f.write(json.dumps(asdict(c)) + "\n")
        return rep

    def _analytic_rate(self, exp_attempts_per_register: float, spec_time_s_override: float | None = None) -> float:
        day = 86400.0
        t_spec = self.cfg.spec_time_s if spec_time_s_override is None else float(spec_time_s_override)
        shots_per = exp_attempts_per_register * (1.0 / self.cfg.detector_eta)
        write = self.cfg.beamlets / (shots_per * self.cfg.shot_cycle_s) * day
        measure = self.cfg.readout_channels / (exp_attempts_per_register * max(t_spec, 1e-9)) * day
        return min(write, measure) * self.cfg.duty_cycle
