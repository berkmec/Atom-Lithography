"""Spectroscopy model: noisy line measurement + blank/consumed classification
(Exp50 measurement band; Exp67 retry classification)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Measurement:
    lines_Hz: np.ndarray    # measured transition frequencies (noisy)
    donor_present: bool


class Spectrometer:
    def __init__(self, sigma_Hz: float, blank_prob: float, rng: np.random.Generator):
        self.sigma_Hz = float(sigma_Hz)
        self.blank_prob = float(blank_prob)
        self.rng = rng
        self.sessions = 0

    def measure(self, true_lines_Hz: np.ndarray, donor_present: bool) -> Measurement:
        self.sessions += 1
        noisy = true_lines_Hz + self.rng.normal(0.0, self.sigma_Hz, size=len(true_lines_Hz))
        return Measurement(lines_Hz=noisy, donor_present=donor_present)

    def classify_failure(self) -> str:
        """Failed slot: 'blank' (retry in place) or 'consumed' (fresh sub-site)."""
        return "blank" if self.rng.random() < self.blank_prob else "consumed"
