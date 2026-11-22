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
    implanted: int          # actual ions that landed (incl. undetected strays)
    shots_fired: int


class CountedWriter:
    def __init__(self, eta: float, rng: np.random.Generator):
        if not (0.0 < eta <= 1.0):
            raise ValueError("eta must be in (0, 1]")
        self.eta = float(eta)
        self.rng = rng
        self.total_shots = 0

    def fire_single(self) -> ShotRecord:
        k = 1 if self.eta >= 1.0 else int(self.rng.geometric(self.eta))
        self.total_shots += k
        return ShotRecord(intended=1, implanted=k, shots_fired=k)

    def effective_yield(self, p: float, s: float) -> float:
        """Analytic attempt-yield degradation E[s^(K-1)] (Exp67 closed form)."""
        if self.eta >= 1.0:
            return p
        return p * self.eta / (1.0 - (1.0 - self.eta) * s)
