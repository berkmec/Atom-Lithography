"""Atom Lithography Machine control & CellISA programming stack (v2.0).

Implements the write -> detect -> measure -> select -> calibrate factory loop
(Exp57-122/127) plus the CellISA quantum/atom-cell pulse compiler and full
Hilbert-space verifier. No physical hardware exists; all device parameters
are model-anchored ({Model}).
"""
__all__ = [
    "config",
    "writer",
    "spectroscopy",
    "selector",
    "pulse_engine",
    "calibrator",
    "programmer",
    "factory",
    "sim",
]
__version__ = "2.0.0"
