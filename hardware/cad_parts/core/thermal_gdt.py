"""NIST cryogenic integrated thermal contraction & RSS/WC GD&T tolerance stackup.

Provides:
- ``integrated_thermal_contraction(material, t_final_k, t_ref_k=293.15)``:
  Real NIST Cryogenic Material Properties Database (Marquardt/Le/Radebaugh,
  Ekin Appendix A2, Swenson Si, Schott Zerodur) integrated linear thermal
  contraction ``ΔL/L = (L(T) - L(T_ref)) / L(T_ref)`` from 300 K down to
  100 K, 50 K, 4 K, and 20 mK (plus bakeout up to 423 K).
- ``check_cold_clearance(...)``: Differential thermal contraction clearance
  and crush/interference verifier for nested cylinders/flanges/carriers.
- ``check_tolerance_stack(...)``: Worst-case (WC), RSS, and modified-RSS (1.5x)
  1D GD&T tolerance stackup analyzer with dominant-contributor attribution.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Sequence

import numpy as np

# Temperature grid (K) spanning 20 mK MXC through 150 C UHV bakeout
TEMP_GRID_K: tuple[float, ...] = (
    0.02,
    4.0,
    20.0,
    50.0,
    77.0,
    100.0,
    150.0,
    200.0,
    250.0,
    293.15,
    300.0,
    423.15,
)

# Integrated linear thermal expansion (L(T) - L(293.15 K)) / L(293.15 K)
# Dimensionless strain (negative on cooling below 293.15 K for normal materials).
# Reference: NIST Cryogenic Material Properties (Marquardt et al. 2000),
# Ekin (2006) Table A2.1, Swenson (1983) for Si, Schott TIE-37 for Zerodur.
NIST_THERMAL_CONTRACTION_TABLE: dict[str, tuple[float, ...]] = {
    # 316LN / 304L Austenitic Stainless Steel: -2.97e-3 at 4 K
    "316LN": (
        -2.970e-3, -2.970e-3, -2.968e-3, -2.960e-3, -2.890e-3, -2.790e-3,
        -2.290e-3, -1.560e-3, -0.730e-3, 0.0, +0.109e-3, +2.150e-3,
    ),
    # OFHC Copper (C10100): -3.26e-3 at 4 K
    "OFHC Cu": (
        -3.260e-3, -3.260e-3, -3.257e-3, -3.200e-3, -3.020e-3, -2.830e-3,
        -2.220e-3, -1.490e-3, -0.710e-3, 0.0, +0.114e-3, +2.210e-3,
    ),
    # Ti-6Al-4V (Grade 5 Titanium): -1.73e-3 at 4 K
    "Ti-6Al-4V": (
        -1.730e-3, -1.730e-3, -1.728e-3, -1.710e-3, -1.620e-3, -1.530e-3,
        -1.220e-3, -0.820e-3, -0.390e-3, 0.0, +0.059e-3, +1.180e-3,
    ),
    # Aluminum 6061-T6: -4.15e-3 at 4 K
    "Al 6061": (
        -4.150e-3, -4.150e-3, -4.145e-3, -4.100e-3, -3.930e-3, -3.700e-3,
        -2.960e-3, -2.010e-3, -0.970e-3, 0.0, +0.158e-3, +3.120e-3,
    ),
    # Invar-36 (Fe-36Ni): -0.40e-3 at 4 K
    "Invar-36": (
        -0.400e-3, -0.400e-3, -0.398e-3, -0.380e-3, -0.345e-3, -0.310e-3,
        -0.230e-3, -0.150e-3, -0.070e-3, 0.0, +0.008e-3, +0.260e-3,
    ),
    # Alumina / Sapphire (Al2O3): -0.72e-3 at 4 K
    "Al2O3": (
        -0.720e-3, -0.720e-3, -0.720e-3, -0.718e-3, -0.700e-3, -0.680e-3,
        -0.590e-3, -0.430e-3, -0.220e-3, 0.0, +0.038e-3, +0.840e-3,
    ),
    # Aluminum Nitride (AlN): -0.60e-3 at 4 K
    "AlN": (
        -0.600e-3, -0.600e-3, -0.600e-3, -0.598e-3, -0.580e-3, -0.560e-3,
        -0.480e-3, -0.350e-3, -0.180e-3, 0.0, +0.031e-3, +0.640e-3,
    ),
    # Single-crystal Silicon (Si): -0.216e-3 at 4 K (Swenson 1983, slight CTE sign flip <120 K)
    "Si": (
        -0.216e-3, -0.216e-3, -0.216e-3, -0.219e-3, -0.227e-3, -0.232e-3,
        -0.226e-3, -0.181e-3, -0.100e-3, 0.0, +0.018e-3, +0.380e-3,
    ),
    # Zerodur (Class 0 ultra-low expansion glass-ceramic): ~+0.04e-3 at 4 K
    "Zerodur": (
        +0.040e-3, +0.040e-3, +0.040e-3, +0.039e-3, +0.035e-3, +0.030e-3,
        +0.020e-3, +0.010e-3, +0.004e-3, 0.0, +0.0003e-3, +0.007e-3,
    ),
    # High-purity Niobium (Nb): -1.43e-3 at 4 K
    "Nb": (
        -1.430e-3, -1.430e-3, -1.428e-3, -1.410e-3, -1.330e-3, -1.230e-3,
        -0.960e-3, -0.640e-3, -0.305e-3, 0.0, +0.050e-3, +0.960e-3,
    ),
    # Vespel SP-22 (40% graphite-filled polyimide): -6.90e-3 at 4 K
    "Vespel SP-22": (
        -6.900e-3, -6.900e-3, -6.850e-3, -6.600e-3, -6.150e-3, -5.800e-3,
        -4.550e-3, -3.100e-3, -1.500e-3, 0.0, +0.260e-3, +5.100e-3,
    ),
    # PEEK (Polyether ether ketone): -8.70e-3 at 4 K
    "PEEK": (
        -8.700e-3, -8.700e-3, -8.620e-3, -8.300e-3, -7.800e-3, -7.400e-3,
        -5.800e-3, -3.950e-3, -1.900e-3, 0.0, +0.320e-3, +6.500e-3,
    ),
    # Additional machine materials (Molybdenum, NbTi, Mu-metal/Cryoperm, BeCu, PTFE, Fused Silica)
    "Mo": (
        -0.950e-3, -0.950e-3, -0.948e-3, -0.935e-3, -0.880e-3, -0.815e-3,
        -0.640e-3, -0.430e-3, -0.205e-3, 0.0, +0.033e-3, +0.650e-3,
    ),
    "NbTi": (
        -1.870e-3, -1.870e-3, -1.868e-3, -1.840e-3, -1.730e-3, -1.610e-3,
        -1.260e-3, -0.840e-3, -0.400e-3, 0.0, +0.060e-3, +1.150e-3,
    ),
    "Mu-metal": (
        -2.300e-3, -2.300e-3, -2.295e-3, -2.260e-3, -2.140e-3, -2.010e-3,
        -1.600e-3, -1.080e-3, -0.520e-3, 0.0, +0.088e-3, +1.700e-3,
    ),
    "BeCu": (
        -3.160e-3, -3.160e-3, -3.155e-3, -3.100e-3, -2.930e-3, -2.740e-3,
        -2.160e-3, -1.460e-3, -0.690e-3, 0.0, +0.115e-3, +2.280e-3,
    ),
    "PTFE": (
        -21.400e-3, -21.400e-3, -21.100e-3, -20.100e-3, -19.200e-3, -18.200e-3,
        -15.400e-3, -12.100e-3, -7.800e-3, 0.0, +0.900e-3, +18.000e-3,
    ),
    "Fused Silica": (
        +0.070e-3, +0.070e-3, +0.068e-3, +0.062e-3, +0.052e-3, +0.042e-3,
        +0.024e-3, +0.010e-3, +0.002e-3, 0.0, +0.004e-3, +0.072e-3,
    ),
    "Graphite": (
        -0.500e-3, -0.500e-3, -0.498e-3, -0.485e-3, -0.455e-3, -0.425e-3,
        -0.340e-3, -0.230e-3, -0.110e-3, 0.0, +0.020e-3, +0.420e-3,
    ),
}

# Material name alias resolver (handles BOM mixed strings cleanly)
_THERMAL_ALIASES: tuple[tuple[str, str], ...] = (
    ("vespel", "Vespel SP-22"),
    ("peek", "PEEK"),
    ("ptfe", "PTFE"),
    ("pfa", "PTFE"),
    ("zerodur", "Zerodur"),
    ("ule", "Zerodur"),
    ("invar", "Invar-36"),
    ("fused silica", "Fused Silica"),
    ("erimis silika", "Fused Silica"),
    ("erimis-silika", "Fused Silica"),
    ("kuvars", "Fused Silica"),
    ("quartz", "Fused Silica"),
    ("sapphire", "Al2O3"),
    ("safir", "Al2O3"),
    ("al2o3", "Al2O3"),
    ("alumina", "Al2O3"),
    ("seramik", "Al2O3"),
    ("aln", "AlN"),
    ("nbtin", "Si"),  # thin film on Si substrate
    ("nbti", "NbTi"),
    ("niobium", "Nb"),
    ("cryoperm", "Mu-metal"),
    ("mu-metal", "Mu-metal"),
    ("mumetal", "Mu-metal"),
    ("ti-6al-4v", "Ti-6Al-4V"),
    ("titanyum", "Ti-6Al-4V"),
    ("titanium", "Ti-6Al-4V"),
    ("316ln", "316LN"),
    ("316l", "316LN"),
    ("304", "316LN"),
    ("paslanmaz", "316LN"),
    ("stainless", "316LN"),
    ("ss", "316LN"),
    ("becu", "BeCu"),
    ("ofhc", "OFHC Cu"),
    ("copper", "OFHC Cu"),
    ("bakir", "OFHC Cu"),
    ("al 6061", "Al 6061"),
    ("6061", "Al 6061"),
    ("aluminyum", "Al 6061"),
    ("aluminum", "Al 6061"),
    ("molibden", "Mo"),
    ("molybdenum", "Mo"),
    ("grafit", "Graphite"),
    ("graphite", "Graphite"),
    ("28si", "Si"),
    ("silicon", "Si"),
    ("soi", "Si"),
)


def resolve_thermal_material(material: str) -> str:
    """Resolve a canonical or BOM material name to a NIST contraction table key."""
    key = material.strip()
    if key in NIST_THERMAL_CONTRACTION_TABLE:
        return key
    low = key.lower()
    # Exact short symbols
    if low in {"cu", "nb", "mo", "si", "ti", "al"}:
        short_map = {
            "cu": "OFHC Cu",
            "nb": "Nb",
            "mo": "Mo",
            "si": "Si",
            "ti": "Ti-6Al-4V",
            "al": "Al 6061",
        }
        return short_map[low]
    for pattern, canonical in _THERMAL_ALIASES:
        if pattern in low:
            return canonical
    raise KeyError(
        f"Unsupported thermal material {material!r}; available keys: "
        f"{sorted(NIST_THERMAL_CONTRACTION_TABLE)}"
    )


def integrated_thermal_contraction(
    material: str,
    t_final_k: float,
    t_ref_k: float = 293.15,
) -> float:
    """Return dimensionless integrated linear strain ``(L(T_final) - L(T_ref)) / L(T_ref)``.

    Negative values indicate contraction on cooling (e.g. ``316LN`` at 4 K ≈ ``-0.00297``).
    Values below 0.02 K clamp to 0.02 K (full cryogenic saturation); values above
    423.15 K linearly extrapolate from the 300..423.15 K slope.
    """
    canonical = resolve_thermal_material(material)
    temps = np.asarray(TEMP_GRID_K, dtype=np.float64)
    strains = np.asarray(NIST_THERMAL_CONTRACTION_TABLE[canonical], dtype=np.float64)

    def _strain_vs_293(t_k: float) -> float:
        if t_k <= temps[0]:
            return float(strains[0])
        if t_k <= temps[-1]:
            return float(np.interp(t_k, temps, strains))
        slope = (strains[-1] - strains[-2]) / (temps[-1] - temps[-2])
        return float(strains[-1] + slope * (t_k - temps[-1]))

    e_final = _strain_vs_293(float(t_final_k))
    e_ref = _strain_vs_293(float(t_ref_k))
    # Exact conversion: L(T_final)/L(T_ref) - 1 = (1 + e_final)/(1 + e_ref) - 1
    return (1.0 + e_final) / (1.0 + e_ref) - 1.0


def cold_dimension_mm(
    nominal_mm: float,
    material: str,
    t_final_k: float,
    t_ref_k: float = 293.15,
) -> float:
    """Compute contracted/expanded dimension (mm) at ``t_final_k``."""
    return float(nominal_mm) * (1.0 + integrated_thermal_contraction(material, t_final_k, t_ref_k))


# ---------------------------------------------------------------------------
# Differential thermal clearance checker
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ColdClearanceResult:
    """Result of cryogenic differential contraction clearance verification."""

    outer_material: str
    inner_material: str
    t_cold_k: float
    t_ref_k: float
    warm_outer_id_mm: float
    warm_inner_od_mm: float
    cold_outer_id_mm: float
    cold_inner_od_mm: float
    outer_strain: float
    inner_strain: float
    warm_radial_clearance_mm: float
    cold_nominal_radial_clearance_mm: float
    cold_worst_case_radial_clearance_mm: float
    delta_radial_clearance_mm: float
    min_required_radial_clearance_mm: float
    interference_risk: bool
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_cold_clearance(
    outer_material: str,
    inner_material: str,
    nominal_outer_id_mm: float,
    nominal_inner_od_mm: float,
    t_cold_k: float,
    *,
    t_ref_k: float = 293.15,
    min_required_radial_clearance_mm: float = 0.05,
    outer_id_tol_mm: float = 0.0,
    inner_od_tol_mm: float = 0.0,
) -> ColdClearanceResult:
    """Check radial clearance between a nested outer bore and inner cylinder at ``t_cold_k``.

    Positive ``outer_id_tol_mm`` / ``inner_od_tol_mm`` represent bilateral diameter
    tolerances (±tol on diameter), reducing worst-case radial clearance by
    ``(abs(outer_id_tol_mm) + abs(inner_od_tol_mm)) / 2``.
    """
    e_out = integrated_thermal_contraction(outer_material, t_cold_k, t_ref_k)
    e_in = integrated_thermal_contraction(inner_material, t_cold_k, t_ref_k)
    cold_id = float(nominal_outer_id_mm) * (1.0 + e_out)
    cold_od = float(nominal_inner_od_mm) * (1.0 + e_in)
    warm_rad = 0.5 * (float(nominal_outer_id_mm) - float(nominal_inner_od_mm))
    cold_nom_rad = 0.5 * (cold_id - cold_od)
    tol_rad = 0.5 * (abs(float(outer_id_tol_mm)) + abs(float(inner_od_tol_mm)))
    cold_wc_rad = cold_nom_rad - tol_rad
    return ColdClearanceResult(
        outer_material=resolve_thermal_material(outer_material),
        inner_material=resolve_thermal_material(inner_material),
        t_cold_k=float(t_cold_k),
        t_ref_k=float(t_ref_k),
        warm_outer_id_mm=float(nominal_outer_id_mm),
        warm_inner_od_mm=float(nominal_inner_od_mm),
        cold_outer_id_mm=cold_id,
        cold_inner_od_mm=cold_od,
        outer_strain=e_out,
        inner_strain=e_in,
        warm_radial_clearance_mm=warm_rad,
        cold_nominal_radial_clearance_mm=cold_nom_rad,
        cold_worst_case_radial_clearance_mm=cold_wc_rad,
        delta_radial_clearance_mm=cold_nom_rad - warm_rad,
        min_required_radial_clearance_mm=float(min_required_radial_clearance_mm),
        interference_risk=(cold_wc_rad <= 0.0),
        passed=(cold_wc_rad >= float(min_required_radial_clearance_mm)),
    )


# ---------------------------------------------------------------------------
# Tolerance stackup calculator (Worst-Case, RSS, Modified-RSS)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ToleranceContributor:
    """One 1D tolerance chain element with signed sensitivity (+1 or -1)."""

    name: str
    nominal_mm: float
    tol_plus_mm: float
    tol_minus_mm: float | None = None
    sign: float = 1.0
    sensitivity: float = 1.0

    def __post_init__(self) -> None:
        if self.tol_minus_mm is None:
            object.__setattr__(self, "tol_minus_mm", -abs(self.tol_plus_mm))
        if self.tol_plus_mm < self.tol_minus_mm:  # type: ignore[operator]
            raise ValueError(
                f"Contributor {self.name!r}: tol_plus_mm < tol_minus_mm"
            )

    @property
    def midpoint_shift_mm(self) -> float:
        return 0.5 * (self.tol_plus_mm + float(self.tol_minus_mm))  # type: ignore[arg-type]

    @property
    def half_band_mm(self) -> float:
        return 0.5 * (self.tol_plus_mm - float(self.tol_minus_mm))  # type: ignore[arg-type]


@dataclass(frozen=True)
class ToleranceStackResult:
    """Worst-case, RSS, and 1.5x Bender-RSS tolerance stackup analysis."""

    nominal_mm: float
    mean_mm: float
    wc_half_band_mm: float
    wc_min_mm: float
    wc_max_mm: float
    rss_half_band_mm: float
    rss_min_mm: float
    rss_max_mm: float
    modified_rss_half_band_mm: float
    modified_rss_min_mm: float
    modified_rss_max_mm: float
    target_min_mm: float | None
    target_max_mm: float | None
    wc_pass: bool
    rss_pass: bool
    modified_rss_pass: bool
    variance_shares_pct: tuple[tuple[str, float], ...]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["variance_shares_pct"] = dict(self.variance_shares_pct)
        return d


def check_tolerance_stack(
    contributors: Sequence[ToleranceContributor | dict[str, Any]],
    *,
    target_min_mm: float | None = None,
    target_max_mm: float | None = None,
    modified_rss_factor: float = 1.5,
) -> ToleranceStackResult:
    """Compute Worst-Case, RSS, and Modified-RSS stackup for a 1D chain."""
    if not contributors:
        raise ValueError("contributors must be non-empty")

    items: list[ToleranceContributor] = []
    for c in contributors:
        if isinstance(c, ToleranceContributor):
            items.append(c)
        elif isinstance(c, dict):
            items.append(ToleranceContributor(**c))
        else:
            raise TypeError(f"Unsupported contributor type: {type(c)!r}")

    nominal = 0.0
    mean = 0.0
    wc_half = 0.0
    var_terms: list[tuple[str, float]] = []

    for it in items:
        k = float(it.sign) * float(it.sensitivity)
        nominal += k * float(it.nominal_mm)
        mean += k * (float(it.nominal_mm) + it.midpoint_shift_mm)
        eff_half = abs(k) * it.half_band_mm
        wc_half += eff_half
        var_terms.append((it.name, eff_half * eff_half))

    total_var = sum(v for _, v in var_terms)
    rss_half = math.sqrt(total_var)
    mod_half = float(modified_rss_factor) * rss_half

    wc_min, wc_max = mean - wc_half, mean + wc_half
    rss_min, rss_max = mean - rss_half, mean + rss_half
    mod_min, mod_max = mean - mod_half, mean + mod_half

    def _within(lo: float, hi: float) -> bool:
        if target_min_mm is not None and lo < target_min_mm - 1e-12:
            return False
        if target_max_mm is not None and hi > target_max_mm + 1e-12:
            return False
        return True

    shares = tuple(
        (name, (100.0 * v / total_var) if total_var > 0.0 else 0.0)
        for name, v in var_terms
    )

    return ToleranceStackResult(
        nominal_mm=nominal,
        mean_mm=mean,
        wc_half_band_mm=wc_half,
        wc_min_mm=wc_min,
        wc_max_mm=wc_max,
        rss_half_band_mm=rss_half,
        rss_min_mm=rss_min,
        rss_max_mm=rss_max,
        modified_rss_half_band_mm=mod_half,
        modified_rss_min_mm=mod_min,
        modified_rss_max_mm=mod_max,
        target_min_mm=target_min_mm,
        target_max_mm=target_max_mm,
        wc_pass=_within(wc_min, wc_max),
        rss_pass=_within(rss_min, rss_max),
        modified_rss_pass=_within(mod_min, mod_max),
        variance_shares_pct=shares,
    )
