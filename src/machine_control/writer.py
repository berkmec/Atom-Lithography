"""Counted-ion writer model (Exp67): fire until the detector counts.

With per-ion detection efficiency eta, the number actually implanted per
intended single ion is Geometric(eta); each stray ion multiplies the attempt
success probability by the survival factor s.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ShotRecord:
    intended: int
    implanted: int          # actual ions that landed (0 on false-positive noise trigger)
    shots_fired: int
    false_positive: bool = False


class CountedWriter:
    def __init__(
        self,
        eta: float,
        rng: np.random.Generator,
        false_positive_rate: float = 0.0,
    ):
        if not (0.0 < eta <= 1.0):
            raise ValueError("eta must be in (0, 1]")
        if not (0.0 <= false_positive_rate < 1.0):
            raise ValueError("false_positive_rate must be in [0, 1)")
        self.eta = float(eta)
        self.false_positive_rate = float(false_positive_rate)
        self.rng = rng
        self.total_shots = 0
        self.total_false_positives = 0

    def fire_single(self) -> ShotRecord:
        if self.false_positive_rate > 0.0 and self.rng.random() < self.false_positive_rate:
            self.total_shots += 1
            self.total_false_positives += 1
            return ShotRecord(intended=1, implanted=0, shots_fired=1, false_positive=True)
        k = 1 if self.eta >= 1.0 else int(self.rng.geometric(self.eta))
        self.total_shots += k
        return ShotRecord(intended=1, implanted=k, shots_fired=k, false_positive=False)

    def effective_yield(self, p: float, s: float) -> float:
        """Analytic attempt-yield degradation (1 - p_fp) * E[s^(K-1)] (Exp67 + Exp127)."""
        base = p if self.eta >= 1.0 else p * self.eta / (1.0 - (1.0 - self.eta) * s)
        return float((1.0 - self.false_positive_rate) * base)
