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


class Factory:
    def __init__(
        self,
        cfg: MachineConfig | None = None,
        selector=None,
        cal_mode: str = "spectral",
    ):
        self.cfg = cfg or MachineConfig()
        self.cal_mode = str(cal_mode)
        self.rng = np.random.default_rng(self.cfg.seed)
        self.writer = CountedWriter(self.cfg.detector_eta, self.rng)
        self.spec = Spectrometer(self.cfg.spec_sigma_Hz, self.cfg.blank_prob, self.rng)
        self.selector = selector or StochasticSelector(self.cfg.bath_yield, self.rng)
        self.dd_ok = dd_is_feasible(self.cfg.abundance_pct, self.cfg.require_both_alpha)

    def _attempt(self):
        """One donor shot (Mode B): counted write + selection + measure + calibrate."""
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
        # matching Exp65 measure-capacity accounting.
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
        return (cal, meas.lines_Hz), shot.shots_fired

    def run(self, slots: int, cert_path: str | Path | None = None) -> FactoryReport:
        certs: list[Certificate] = []
        shots0, specs0 = self.writer.total_shots, self.spec.sessions
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
                    if self.spec.classify_failure() == "consumed":
                        used_subsites += 1
            total_subsites += used_subsites
            if cal is not None and self.dd_ok:
                cal_res, lines = cal
                certs.append(Certificate(
                    register_id=f"ALM-{s:06d}",
                    slot=s,
                    attempts=attempts,
                    shots=slot_shots,
                    min_spacing_Hz=cal_res.min_spacing_Hz,
                    dd_quality_gate=True,
                    lines_Hz=[float(v) for v in lines],
                ))
        n = len(certs)
        shots = self.writer.total_shots - shots0
        specs = self.spec.sessions - specs0
        # Exp65 analytic cross-check (same formulas, analytic expectations)
        p_eff = self.writer.effective_yield(self.cfg.bath_yield, self.cfg.stray_survival)
        q = 1.0 - p_eff
        slot_p = 1.0 - q ** self.cfg.max_retries
        exp_attempts = sum(q ** i for i in range(self.cfg.max_retries)) / max(slot_p, 1e-12)
        analytic = self._analytic_rate(exp_attempts)
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
        )
        if cert_path:
            out = Path(cert_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("w", encoding="utf-8") as f:
                for c in certs:
                    f.write(json.dumps(asdict(c)) + "\n")
        return rep

    def _analytic_rate(self, exp_attempts_per_register: float) -> float:
        day = 86400.0
        shots_per = exp_attempts_per_register * (1.0 / self.cfg.detector_eta)
        write = self.cfg.beamlets / (shots_per * self.cfg.shot_cycle_s) * day
        measure = self.cfg.readout_channels / (
            exp_attempts_per_register * self.cfg.spec_time_s
        ) * day
        return min(write, measure) * self.cfg.duty_cycle
