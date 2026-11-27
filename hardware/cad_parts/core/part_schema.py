"""Frozen CAD part schema, BOM loader (exact part_id), and epistemic contract.

Zero-aliasing contract:
- Every mechanical part is keyed strictly by exact ``part_id`` from
  ``research/atom_lithography_machine/BOM_DETAILED.csv`` (e.g. ``S1.7-01``,
  ``S6.11-01``, ``S7.SAFETY-02``, ``S9.4-01``).
- ``parent_bom_id`` aliases (``S1.6``, ``S6.5``, ``S9.1``) are NEVER accepted
  as part lookup keys.
- Every design and exported artifact carries explicit epistemic status:
  ``design_maturity="M0_M1_DETAILED_CAD_DESIGN_ONLY"``,
  ``no_lab_measurement=True``, ``iec61508_certified=False``,
  ``semi_s2_certified=False``.
"""
from __future__ import annotations

import csv
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Epistemic constants (locked for Stage-2 M0/M1 design-only deliverables)
# ---------------------------------------------------------------------------
DESIGN_MATURITY: str = "M0_M1_DETAILED_CAD_DESIGN_ONLY"
NO_LAB_MEASUREMENT: bool = True
IEC61508_CERTIFIED: bool = False
SEMI_S2_CERTIFIED: bool = False
GENERAL_TOLERANCE_STD: str = "ISO 2768-mK"
DRAWING_STANDARD: str = "ISO 128 / ASME Y14.5-2018"
STEP_PROTOCOL: str = "ISO 10303-21 AP214 (AUTOMOTIVE_DESIGN)"
SOURCE_BOM_VERSION: str = "v7.0"

VALID_DESIGN_TIERS: frozenset[str] = frozenset(
    {"CUSTOM_FULL", "COTS_ENV_ICD", "KIT_OR_ALIAS"}
)

VALID_PORT_KINDS: frozenset[str] = frozenset(
    {
        "flange",
        "connector",
        "thermal",
        "optical",
        "bolt",
        "gas",
        "rf",
        "vacuum",
        "mechanical",
        "electrical",
        "cooling",
    }
)

# Active non-solid BOM rows (fab NRE / analytical service / isotope gas charge)
NON_SOLID_PART_IDS: frozenset[str] = frozenset(
    {"S2.1-02", "S2.2-02", "S2.3-02", "S5.4-02", "S6.8-03"}
)

# Superseded $0 v4 rows replaced in v5
SUPERSEDED_PART_IDS: frozenset[str] = frozenset({"S6.10-02", "S7.1-04"})

# Canonical ISO 1101 / ASME Y14.5 GD&T symbol map
GDT_SYMBOL_MAP: dict[str, str] = {
    "perpendicularity": "⊥",
    "⊥": "⊥",
    "concentricity": "◎",
    "coaxiality": "◎",
    "◎": "◎",
    "profile_surface": "⌓",
    "profile": "⌓",
    "⌓": "⌓",
    "profile_line": "⌒",
    "⌒": "⌒",
    "flatness": "⏥",
    "⏥": "⏥",
    "position": "⌖",
    "true_position": "⌖",
    "⌖": "⌖",
    "parallelism": "∥",
    "∥": "∥",
    "circularity": "○",
    "roundness": "○",
    "○": "○",
    "cylindricity": "⌭",
    "⌭": "⌭",
    "straightness": "⎯",
    "⎯": "⎯",
    "runout": "↗",
    "↗": "↗",
    "total_runout": "⌰",
    "⌰": "⌰",
    "symmetry": "⌯",
    "⌯": "⌯",
    "angularity": "∠",
    "∠": "∠",
}

# Portable repository root resolution (no hardcoded user home paths)
REPO_ROOT: Path = Path(__file__).resolve().parents[3]
DEFAULT_BOM_PATH: Path = (
    REPO_ROOT / "research" / "atom_lithography_machine" / "BOM_DETAILED.csv"
)


# ---------------------------------------------------------------------------
# Frozen dataclasses
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BomRow:
    """Single exact-keyed row from ``BOM_DETAILED.csv``."""

    part_id: str
    parent_bom_id: str
    subsystem: str
    part_name: str
    qty: int | float
    unit: str
    material: str
    key_spec: str
    tolerance: str
    temp_stage: str
    vacuum_grade: str
    procurement_class: str
    parent_cost_class: str
    usd_low: float
    usd_nom: float
    usd_high: float
    cad_module: str
    epistemic_tag: str
    notes: str

    @property
    def is_software(self) -> bool:
        return self.procurement_class.upper() == "IN-HOUSE"

    @property
    def is_superseded(self) -> bool:
        return self.part_id in SUPERSEDED_PART_IDS or (
            not self.is_software and self.usd_nom == 0.0
        )

    @property
    def is_physical_solid(self) -> bool:
        return (
            not self.is_software
            and not self.is_superseded
            and self.part_id not in NON_SOLID_PART_IDS
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PortInterface:
    """Mechanical, vacuum flange, connector, thermal, optical, or bolt interface."""

    name: str
    kind: str
    position_mm: tuple[float, float, float]
    normal: tuple[float, float, float]
    standard: str
    mating_part_id: str = ""
    bore_mm: float = 0.0
    od_mm: float = 0.0
    pcd_mm: float = 0.0
    bolt_count: int = 0
    bolt_hole_mm: float = 0.0
    bolt_spec: str = ""
    frame: str = "local"
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("PortInterface.name must be non-empty")
        if self.kind not in VALID_PORT_KINDS:
            raise ValueError(
                f"Invalid PortInterface.kind={self.kind!r}; expected one of {sorted(VALID_PORT_KINDS)}"
            )
        nx, ny, nz = self.normal
        nlen = math.sqrt(nx * nx + ny * ny + nz * nz)
        if nlen < 1e-12:
            raise ValueError(f"PortInterface {self.name!r} has zero normal vector")
        if abs(nlen - 1.0) > 1e-6:
            object.__setattr__(
                self, "normal", (nx / nlen, ny / nlen, nz / nlen)
            )
        if len(self.position_mm) != 3:
            raise ValueError("PortInterface.position_mm must be a 3-tuple")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DimensionCallout:
    """Engineering dimension callout for DXF/SVG 2D manufacturing drawings."""

    label: str
    nominal_mm: float
    tol_plus_mm: float = 0.05
    tol_minus_mm: float = -0.05
    view: str = "front"
    unit: str = "mm"
    prefix: str = ""
    suffix: str = ""
    is_basic: bool = False
    datum_ref: str = ""
    decimals: int = 2

    def __post_init__(self) -> None:
        if self.view not in {"front", "top", "right", "iso", "section", "general"}:
            raise ValueError(f"Unsupported DimensionCallout view: {self.view!r}")
        if self.tol_plus_mm < self.tol_minus_mm:
            raise ValueError(
                f"DimensionCallout {self.label!r}: tol_plus_mm ({self.tol_plus_mm}) "
                f"< tol_minus_mm ({self.tol_minus_mm})"
            )

    def format_text(self) -> str:
        fmt = f"{{:.{self.decimals}f}}"
        nom_s = fmt.format(self.nominal_mm)
        if self.is_basic:
            return f"[{self.prefix}{nom_s}]{self.suffix}"
        if abs(self.tol_plus_mm + self.tol_minus_mm) < 1e-9:
            tol_v = abs(self.tol_plus_mm)
            if tol_v == 0.0:
                return f"{self.prefix}{nom_s}{self.suffix}"
            tol_dec = max(self.decimals, 3 if tol_v < 0.01 else 2)
            return f"{self.prefix}{nom_s} ±{tol_v:.{tol_dec}f}{self.suffix}"
        tol_dec = max(
            self.decimals,
            3 if min(abs(self.tol_plus_mm), abs(self.tol_minus_mm)) < 0.01 else 2,
        )
        return (
            f"{self.prefix}{nom_s} "
            f"{self.tol_plus_mm:+.{tol_dec}f}/{self.tol_minus_mm:+.{tol_dec}f}"
            f"{self.suffix}"
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["formatted"] = self.format_text()
        return d


@dataclass(frozen=True)
class GDTFrame:
    """ISO 1101 / ASME Y14.5 geometric dimensioning & tolerancing feature control frame."""

    symbol: str
    tolerance_mm: float
    diameter_zone: bool = False
    material_condition: str = ""
    datum_primary: str = "A"
    datum_secondary: str = ""
    datum_tertiary: str = ""
    feature_note: str = ""

    def __post_init__(self) -> None:
        key = self.symbol.strip().lower() if self.symbol.isascii() else self.symbol.strip()
        if key not in GDT_SYMBOL_MAP:
            raise ValueError(
                f"Unknown GD&T symbol {self.symbol!r}; supported: {sorted(GDT_SYMBOL_MAP)}"
            )
        if self.tolerance_mm <= 0.0:
            raise ValueError(
                f"GDTFrame.tolerance_mm must be positive, got {self.tolerance_mm}"
            )
        if self.material_condition not in {"", "M", "L", "S", "Ⓜ", "Ⓛ"}:
            raise ValueError(
                f"Invalid material_condition {self.material_condition!r}"
            )

    def glyph(self) -> str:
        key = self.symbol.strip().lower() if self.symbol.isascii() else self.symbol.strip()
        return GDT_SYMBOL_MAP[key]

    def tolerance_text(self) -> str:
        prefix = "Ø" if self.diameter_zone else ""
        if self.tolerance_mm < 0.001:
            val = f"{self.tolerance_mm:.4f}"
        elif self.tolerance_mm < 0.1:
            val = f"{self.tolerance_mm:.3f}"
        else:
            val = f"{self.tolerance_mm:.2f}"
        mc = {"M": "Ⓜ", "L": "Ⓛ"}.get(self.material_condition, self.material_condition)
        return f"{prefix}{val}{mc}"

    def datums(self) -> tuple[str, ...]:
        return tuple(
            d for d in (self.datum_primary, self.datum_secondary, self.datum_tertiary) if d
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["glyph"] = self.glyph()
        d["tolerance_text"] = self.tolerance_text()
        return d


@dataclass(frozen=True)
class PartDesign:
    """Complete frozen mechanical design specification for one exact BOM ``part_id``."""

    part_id: str
    parent_bom_id: str
    subsystem: str
    part_name: str
    design_tier: str = "CUSTOM_FULL"
    material: str = "316LN"
    temp_stage: str = "300 K"
    temp_k: float = 300.0
    vacuum_grade: str = "UHV 1e-9 mbar"
    tolerance_spec: str = GENERAL_TOLERANCE_STD
    surface_finish_ra_um: float = 0.8
    qty: int = 1
    procurement_class: str = "CUS"
    world_origin_mm: tuple[float, float, float] = (0.0, 0.0, 0.0)
    world_rotation_deg: tuple[float, float, float] = (0.0, 0.0, 0.0)
    ports: tuple[PortInterface, ...] = ()
    dimensions: tuple[DimensionCallout, ...] = ()
    gdt_frames: tuple[GDTFrame, ...] = ()
    datums: tuple[tuple[str, str], ...] = (
        ("A", "PRIMARY MOUNTING PLANE"),
        ("B", "DATUM AXIS / BORE CENTERLINE"),
        ("C", "ANGULAR INDEX / BOLT ORIENTATION"),
    )
    notes: tuple[str, ...] = ()
    scad_params: tuple[tuple[str, float | int | str], ...] = ()
    target_mass_kg: float | None = None
    # Explicit epistemic status metadata (locked defaults)
    design_maturity: str = DESIGN_MATURITY
    no_lab_measurement: bool = NO_LAB_MEASUREMENT
    iec61508_certified: bool = IEC61508_CERTIFIED
    semi_s2_certified: bool = SEMI_S2_CERTIFIED

    def __post_init__(self) -> None:
        if not self.part_id or not self.part_id.strip():
            raise ValueError("PartDesign.part_id must be non-empty")
        if "-" not in self.part_id:
            raise ValueError(
                f"PartDesign.part_id must be an exact BOM part_id (e.g. 'S1.1-01'), "
                f"not a parent_bom_id alias: {self.part_id!r}"
            )
        if self.design_tier not in VALID_DESIGN_TIERS:
            raise ValueError(
                f"Invalid design_tier={self.design_tier!r}; expected one of {sorted(VALID_DESIGN_TIERS)}"
            )
        if self.temp_k <= 0.0:
            raise ValueError(f"PartDesign.temp_k must be > 0 K, got {self.temp_k}")
        if self.surface_finish_ra_um <= 0.0:
            raise ValueError(
                f"PartDesign.surface_finish_ra_um must be > 0, got {self.surface_finish_ra_um}"
            )
        if len(self.world_origin_mm) != 3 or len(self.world_rotation_deg) != 3:
            raise ValueError("world_origin_mm and world_rotation_deg must be 3-tuples")

    def epistemic_metadata(self) -> dict[str, Any]:
        return {
            "design_maturity": self.design_maturity,
            "no_lab_measurement": self.no_lab_measurement,
            "iec61508_certified": self.iec61508_certified,
            "semi_s2_certified": self.semi_s2_certified,
            "general_tolerance_std": GENERAL_TOLERANCE_STD,
            "drawing_standard": DRAWING_STANDARD,
            "step_protocol": STEP_PROTOCOL,
            "source_bom_version": SOURCE_BOM_VERSION,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "part_id": self.part_id,
            "parent_bom_id": self.parent_bom_id,
            "subsystem": self.subsystem,
            "part_name": self.part_name,
            "design_tier": self.design_tier,
            "material": self.material,
            "temp_stage": self.temp_stage,
            "temp_k": self.temp_k,
            "vacuum_grade": self.vacuum_grade,
            "tolerance_spec": self.tolerance_spec,
            "surface_finish_ra_um": self.surface_finish_ra_um,
            "qty": self.qty,
            "procurement_class": self.procurement_class,
            "world_origin_mm": list(self.world_origin_mm),
            "world_rotation_deg": list(self.world_rotation_deg),
            "ports": [p.to_dict() for p in self.ports],
            "dimensions": [d.to_dict() for d in self.dimensions],
            "gdt_frames": [g.to_dict() for g in self.gdt_frames],
            "datums": [list(dt) for dt in self.datums],
            "notes": list(self.notes),
            "scad_params": {k: v for k, v in self.scad_params},
            "target_mass_kg": self.target_mass_kg,
            "epistemic": self.epistemic_metadata(),
        }


@dataclass(frozen=True)
class PartArtifactResult:
    """Verified build and export manifest entry for one physical BOM part."""

    part_id: str
    subsystem: str
    design_tier: str
    stl_path: str
    step_path: str
    scad_path: str
    dxf_path: str
    svg_path: str
    watertight: bool
    boundary_edges: int
    non_manifold_edges: int
    signed_volume_mm3: float
    surface_area_mm2: float
    mass_kg: float
    cg_mm: tuple[float, float, float]
    bbox_min_mm: tuple[float, float, float]
    bbox_max_mm: tuple[float, float, float]
    inertia_kg_mm2: tuple[float, float, float, float, float, float]
    triangle_count: int
    vertex_count: int
    step_valid: bool
    dxf_valid: bool
    svg_valid: bool
    scad_valid: bool
    design_maturity: str = DESIGN_MATURITY
    no_lab_measurement: bool = NO_LAB_MEASUREMENT
    iec61508_certified: bool = IEC61508_CERTIFIED
    semi_s2_certified: bool = SEMI_S2_CERTIFIED
    warnings: tuple[str, ...] = ()

    @property
    def all_valid(self) -> bool:
        return (
            self.watertight
            and self.boundary_edges == 0
            and self.non_manifold_edges == 0
            and self.signed_volume_mm3 > 0.0
            and self.step_valid
            and self.dxf_valid
            and self.svg_valid
            and self.scad_valid
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["all_valid"] = self.all_valid
        return d


# ---------------------------------------------------------------------------
# BOM loader (strict exact part_id keying — zero bom_id aliasing)
# ---------------------------------------------------------------------------
_BOM_CACHE: dict[Path, dict[str, BomRow]] = {}


def _parse_num(val: str) -> float:
    s = (val or "").strip()
    if not s or s in {"--", "—", "-"}:
        return 0.0
    return float(s)


def _parse_qty(val: str) -> int | float:
    f = _parse_num(val)
    return int(round(f)) if abs(f - round(f)) < 1e-9 else f


def parse_nominal_temp_k(temp_stage: str) -> float:
    """Extract lowest critical operating temperature (K) from a BOM temp_stage string."""
    s = (temp_stage or "").strip()
    if not s:
        return 300.0
    # Strip parenthetical exclusion clauses like "(aktif sogutmali; 20 mK disinda)"
    s_clean = re.sub(r"\([^)]*(?:disinda|dışında|outside)[^)]*\)", "", s, flags=re.IGNORECASE)
    mk = re.findall(r"(\d+(?:\.\d+)?)\s*mK", s_clean)
    if mk:
        return min(float(x) for x in mk) * 1e-3
    ks = re.findall(r"(\d+(?:\.\d+)?)\s*K\b", s_clean)
    if ks:
        return min(float(x) for x in ks)
    cs = re.findall(r"(\d+(?:\.\d+)?)\s*C\b", s_clean)
    if cs:
        return min(float(x) for x in cs) + 273.15
    return 300.0


def load_bom_table(bom_path: Path | str | None = None) -> dict[str, BomRow]:
    """Load ``BOM_DETAILED.csv`` strictly keyed by exact ``part_id`` (zero aliasing)."""
    path = Path(bom_path).resolve() if bom_path is not None else DEFAULT_BOM_PATH.resolve()
    if path in _BOM_CACHE:
        return dict(_BOM_CACHE[path])

    if not path.is_file():
        raise FileNotFoundError(f"BOM_DETAILED.csv not found at {path}")

    table: dict[str, BomRow] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for idx, row in enumerate(reader, start=2):
            pid = (row.get("part_id") or "").strip()
            if not pid:
                raise ValueError(f"Empty part_id at {path}:{idx}")
            if pid in table:
                raise ValueError(f"Duplicate part_id {pid!r} at {path}:{idx}")
            bom_row = BomRow(
                part_id=pid,
                parent_bom_id=(row.get("parent_bom_id") or "").strip(),
                subsystem=(row.get("subsystem") or "").strip(),
                part_name=(row.get("part_name") or "").strip(),
                qty=_parse_qty(row.get("qty", "1")),
                unit=(row.get("unit") or "").strip(),
                material=(row.get("material") or "").strip(),
                key_spec=(row.get("key_spec") or "").strip(),
                tolerance=(row.get("tolerance") or "").strip(),
                temp_stage=(row.get("temp_stage") or "").strip(),
                vacuum_grade=(row.get("vacuum_grade") or "").strip(),
                procurement_class=(row.get("procurement_class") or "").strip(),
                parent_cost_class=(row.get("parent_cost_class") or "").strip(),
                usd_low=_parse_num(row.get("usd_low", "0")),
                usd_nom=_parse_num(row.get("usd_nom", "0")),
                usd_high=_parse_num(row.get("usd_high", "0")),
                cad_module=(row.get("cad_module") or "").strip(),
                epistemic_tag=(row.get("epistemic_tag") or "").strip(),
                notes=(row.get("notes") or "").strip(),
            )
            table[pid] = bom_row

    _BOM_CACHE[path] = table
    return dict(table)


def get_bom_row(part_id: str, bom_path: Path | str | None = None) -> BomRow:
    """Look up a BOM row by exact ``part_id``; rejects ``parent_bom_id`` aliases."""
    table = load_bom_table(bom_path)
    key = part_id.strip()
    if key not in table:
        matching_parents = [
            r.part_id for r in table.values() if r.parent_bom_id == key
        ]
        if matching_parents:
            raise KeyError(
                f"Aliased parent_bom_id {key!r} is forbidden! "
                f"Use exact part_id instead: {matching_parents}"
            )
        raise KeyError(f"Unknown exact part_id: {key!r}")
    return table[key]


def list_physical_part_ids(
    subsystem: str | None = None,
    bom_path: Path | str | None = None,
) -> list[str]:
    """Return exact ``part_id``s of all 164 physical solid BOM parts (or by subsystem)."""
    table = load_bom_table(bom_path)
    out = [
        pid
        for pid, row in table.items()
        if row.is_physical_solid and (subsystem is None or row.subsystem == subsystem)
    ]
    return out


def infer_design_tier(row: BomRow) -> str:
    """Infer default Stage-2 CAD design tier from BOM procurement/subsystem metadata."""
    if row.subsystem == "S9" and row.parent_bom_id in {"S9.1", "S9.2", "S9.3"}:
        return "KIT_OR_ALIAS"
    pclass = row.procurement_class.upper()
    if pclass in {"CUS", "R&D", "CUS/R&D"}:
        return "CUSTOM_FULL"
    return "COTS_ENV_ICD"


def make_part_design_from_bom(
    part_id: str,
    *,
    design_tier: str | None = None,
    material: str | None = None,
    temp_k: float | None = None,
    surface_finish_ra_um: float = 0.8,
    world_origin_mm: tuple[float, float, float] = (0.0, 0.0, 0.0),
    world_rotation_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ports: tuple[PortInterface, ...] = (),
    dimensions: tuple[DimensionCallout, ...] = (),
    gdt_frames: tuple[GDTFrame, ...] = (),
    datums: tuple[tuple[str, str], ...] | None = None,
    notes: tuple[str, ...] = (),
    scad_params: tuple[tuple[str, float | int | str], ...] = (),
    target_mass_kg: float | None = None,
    bom_path: Path | str | None = None,
) -> PartDesign:
    """Build a frozen ``PartDesign`` pre-populated from exact ``BOM_DETAILED.csv`` row."""
    row = get_bom_row(part_id, bom_path=bom_path)
    tier = design_tier if design_tier is not None else infer_design_tier(row)
    mat = material if material is not None else row.material
    tk = temp_k if temp_k is not None else parse_nominal_temp_k(row.temp_stage)
    tol = row.tolerance if row.tolerance and row.tolerance != "—" else GENERAL_TOLERANCE_STD
    combined_notes = (row.key_spec,) + tuple(notes) if row.key_spec else tuple(notes)

    kwargs: dict[str, Any] = {
        "part_id": row.part_id,
        "parent_bom_id": row.parent_bom_id,
        "subsystem": row.subsystem,
        "part_name": row.part_name,
        "design_tier": tier,
        "material": mat,
        "temp_stage": row.temp_stage or f"{tk:g} K",
        "temp_k": tk,
        "vacuum_grade": row.vacuum_grade or "Atmosfer",
        "tolerance_spec": tol,
        "surface_finish_ra_um": surface_finish_ra_um,
        "qty": int(round(row.qty)),
        "procurement_class": row.procurement_class,
        "world_origin_mm": world_origin_mm,
        "world_rotation_deg": world_rotation_deg,
        "ports": tuple(ports),
        "dimensions": tuple(dimensions),
        "gdt_frames": tuple(gdt_frames),
        "notes": combined_notes,
        "scad_params": tuple(scad_params),
        "target_mass_kg": target_mass_kg,
    }
    if datums is not None:
        kwargs["datums"] = tuple(datums)
    return PartDesign(**kwargs)
