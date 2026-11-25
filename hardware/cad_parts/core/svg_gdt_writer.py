"""Pure-Python ISO 128 / ASME Y14.5 serious IEEE/academic white-paper SVG GD&T drawing writer.

Zero cairo dependency — emits crisp, strictly well-formed UTF-8 SVG vector
engineering sheets featuring:
- Restrained academic white-paper palette ONLY:
  ``#FFFFFF`` canvas, ``#111827`` crisp ink, ``#1B365D`` dimension/GD&T navy,
  ``#64748B`` hidden/center slate, ``#CBD5E1`` hairlines, ``#F8FAFC`` header tint.
  ZERO flashy/neon colors.
- Aligned 3-view orthographic projections (Top XY, Front XZ, Right YZ) +
  Isometric wireframe view with XYZ triad.
- Dimension lines with filled arrowheads, Datum A/B/C triangles, boxed ASME Y14.5
  GD&T feature control frames (``⊥``, ``◎``, ``⌓``, ``⏥``, ``⌖``, ``∥``), ISO 1302
  surface finish ``Ra`` symbol, port/interface schedule, and complete ISO 7200
  engineering + epistemic title block.
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from html import escape as xml_escape
from pathlib import Path
from typing import Any

from .dxf_writer import ProjectedView, extract_iso_view, extract_ortho_view
from .feature_engine import MassProperties, SolidMesh, compute_mass_props
from .part_schema import (
    DESIGN_MATURITY,
    GENERAL_TOLERANCE_STD,
    GDTFrame,
    IEC61508_CERTIFIED,
    NO_LAB_MEASUREMENT,
    PartDesign,
    SEMI_S2_CERTIFIED,
)

# Strictly locked IEEE/academic white-paper palette
COLOR_CANVAS = "#FFFFFF"
COLOR_INK = "#111827"
COLOR_DIM = "#1B365D"
COLOR_MUTED = "#64748B"
COLOR_RULE = "#CBD5E1"
COLOR_HEADER_BG = "#F8FAFC"
COLOR_SUBTEXT = "#334155"

APPROVED_ACADEMIC_PALETTE: frozenset[str] = frozenset(
    {
        COLOR_CANVAS,
        COLOR_INK,
        COLOR_DIM,
        COLOR_MUTED,
        COLOR_RULE,
        COLOR_HEADER_BG,
        COLOR_SUBTEXT,
    }
)

SHEET_W = 1680.0
SHEET_H = 1188.0  # Exact A3 landscape ratio (sqrt(2):1)

_BRACKET_PAIRS: dict[str, str] = {"(": ")", "[": "]", "{": "}"}
_BRACKET_CLOSERS: dict[str, str] = {")": "(", "]": "[", "}": "{"}


def _unclosed_bracket_stack(text: str) -> list[tuple[str, int]]:
    stack: list[tuple[str, int]] = []
    for idx, ch in enumerate(text):
        if ch in _BRACKET_PAIRS:
            stack.append((ch, idx))
        elif ch in _BRACKET_CLOSERS and stack and stack[-1][0] == _BRACKET_CLOSERS[ch]:
            stack.pop()
    return stack


def _truncate_clean(text: str, max_len: int) -> str:
    """Truncate text cleanly at word boundaries without dangling delimiters/parentheses.

    Guarantees:
    - ``len(result) <= max_len``
    - No unmatched opening ``(``, ``[``, ``{`` left unclosed when truncated
    - Clean word/clause break with Unicode ellipsis ``…`` (no trailing ``=``, ``-``, ``,``, ``/``)
    """
    s = " ".join((text or "").split())
    if max_len <= 0:
        return ""
    if len(s) <= max_len:
        return s
    if max_len <= 3:
        return s[:max_len]

    budget = max_len - 1  # Reserve 1 char for '…'
    cand = s[:budget]
    next_ch = s[budget] if budget < len(s) else " "

    # Prefer breaking at a clean word/clause boundary unless already on one
    if next_ch not in " ,;/|)]}":
        best_cut = -1
        for sep in (" ", ",", ";", "/", "|"):
            pos = cand.rfind(sep)
            if pos > best_cut:
                best_cut = pos
        if best_cut >= max(4, budget // 2):
            cand = cand[:best_cut]

    cand = cand.rstrip(" ,;:/|-+=—–")

    # Resolve any unmatched opening parentheses/brackets cleanly
    stack = _unclosed_bracket_stack(cand)
    while stack:
        _, open_pos = stack[-1]
        inside = cand[open_pos + 1 :].strip()
        alnum_inside = sum(c.isalnum() for c in inside)
        closing_needed = "".join(_BRACKET_PAIRS[c] for c, _ in reversed(stack))

        if alnum_inside >= 4:
            if len(cand) + 1 + len(closing_needed) <= max_len:
                inner_clean = cand.rstrip(" ,;:/|-+=—–")
                if len(inner_clean) > open_pos + 1:
                    return f"{inner_clean}…{closing_needed}"
            # Trim inside the bracket to leave room for '…)' at a clean word boundary
            sub_budget = max_len - 1 - len(closing_needed)
            if sub_budget > open_pos + 4:
                sub = cand[:sub_budget]
                sp = sub.rfind(" ")
                if sp > open_pos + 2:
                    sub = sub[:sp]
                sub = sub.rstrip(" ,;:/|-+=—–")
                if (
                    len(sub) > open_pos + 2
                    and sum(c.isalnum() for c in sub[open_pos + 1 :]) >= 3
                    and _unclosed_bracket_stack(sub) == stack
                ):
                    return f"{sub}…{closing_needed}"

        # Otherwise drop the incomplete trailing parenthetical clause cleanly
        before = cand[:open_pos].rstrip(" ,;:/|-+=—–")
        if before:
            cand = before
            stack = _unclosed_bracket_stack(cand)
        else:
            sub = cand[: max(1, max_len - 1 - len(closing_needed))].rstrip(" ,;:/|-+=—–")
            return f"{sub}…{closing_needed}"

    cand = cand.rstrip(" ,;:/|-+=—–")
    if not cand:
        cand = s[: max(1, max_len - 1)].rstrip()
    return f"{cand}…"


def _fmt_scale(scale_px_per_mm: float) -> str:
    """Express drawing scale cleanly in engineering notation (assuming ~3.78 px/mm)."""
    ratio = scale_px_per_mm / 3.7795275591
    if ratio >= 1.0:
        if ratio >= 10.0:
            return f"{round(ratio)}:1"
        return f"{ratio:.1f}:1"
    inv = 1.0 / max(ratio, 1e-6)
    if inv >= 10.0:
        return f"1:{round(inv)}"
    return f"1:{inv:.1f}"


def _segments_to_path_d(
    segs,
    u_min: float,
    v_min: float,
    ox: float,
    oy_bottom: float,
    scale: float,
) -> str:
    """Convert (K, 4) 2D segments into one compact SVG path string (Y inverted for SVG)."""
    if segs.size == 0:
        return ""
    parts: list[str] = []
    for u1, v1, u2, v2 in segs:
        x1 = ox + (u1 - u_min) * scale
        y1 = oy_bottom - (v1 - v_min) * scale
        x2 = ox + (u2 - u_min) * scale
        y2 = oy_bottom - (v2 - v_min) * scale
        parts.append(f"M{x1:.2f},{y1:.2f}L{x2:.2f},{y2:.2f}")
    return "".join(parts)


def _draw_h_dim(
    out: list[str],
    x1: float,
    x2: float,
    y_edge: float,
    y_dim: float,
    label: str,
) -> None:
    sign = 1.0 if y_dim >= y_edge else -1.0
    out.append(
        f'<line x1="{x1:.1f}" y1="{y_edge + sign * 4:.1f}" x2="{x1:.1f}" y2="{y_dim + sign * 6:.1f}" '
        f'stroke="{COLOR_DIM}" stroke-width="0.9"/>'
    )
    out.append(
        f'<line x1="{x2:.1f}" y1="{y_edge + sign * 4:.1f}" x2="{x2:.1f}" y2="{y_dim + sign * 6:.1f}" '
        f'stroke="{COLOR_DIM}" stroke-width="0.9"/>'
    )
    out.append(
        f'<line x1="{x1:.1f}" y1="{y_dim:.1f}" x2="{x2:.1f}" y2="{y_dim:.1f}" '
        f'stroke="{COLOR_DIM}" stroke-width="1.1" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>'
    )
    xm = 0.5 * (x1 + x2)
    tw = max(len(label) * 7.2 + 12.0, 44.0)
    out.append(
        f'<rect x="{xm - tw / 2:.1f}" y="{y_dim - 9:.1f}" width="{tw:.1f}" height="17" fill="{COLOR_CANVAS}"/>'
    )
    out.append(
        f'<text x="{xm:.1f}" y="{y_dim + 4:.1f}" text-anchor="middle" '
        f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="11.5" '
        f'font-weight="600" fill="{COLOR_DIM}">{xml_escape(label)}</text>'
    )


def _draw_v_dim(
    out: list[str],
    x_edge: float,
    x_dim: float,
    y_top: float,
    y_bot: float,
    label: str,
) -> None:
    sign = 1.0 if x_dim >= x_edge else -1.0
    out.append(
        f'<line x1="{x_edge + sign * 4:.1f}" y1="{y_top:.1f}" x2="{x_dim + sign * 6:.1f}" y2="{y_top:.1f}" '
        f'stroke="{COLOR_DIM}" stroke-width="0.9"/>'
    )
    out.append(
        f'<line x1="{x_edge + sign * 4:.1f}" y1="{y_bot:.1f}" x2="{x_dim + sign * 6:.1f}" y2="{y_bot:.1f}" '
        f'stroke="{COLOR_DIM}" stroke-width="0.9"/>'
    )
    out.append(
        f'<line x1="{x_dim:.1f}" y1="{y_top:.1f}" x2="{x_dim:.1f}" y2="{y_bot:.1f}" '
        f'stroke="{COLOR_DIM}" stroke-width="1.1" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>'
    )
    ym = 0.5 * (y_top + y_bot)
    th = max(len(label) * 7.0 + 12.0, 44.0)
    out.append(
        f'<rect x="{x_dim - 9:.1f}" y="{ym - th / 2:.1f}" width="18" height="{th:.1f}" fill="{COLOR_CANVAS}"/>'
    )
    out.append(
        f'<text x="{x_dim + 4:.1f}" y="{ym:.1f}" text-anchor="middle" '
        f'transform="rotate(-90 {x_dim:.1f} {ym:.1f})" '
        f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="11.5" '
        f'font-weight="600" fill="{COLOR_DIM}">{xml_escape(label)}</text>'
    )


def _draw_datum_triangle(
    out: list[str],
    x_attach: float,
    y_attach: float,
    letter: str,
    *,
    direction: str = "down",
) -> None:
    """Draw an ISO 5459 / ASME Y14.5 filled datum triangle + boxed datum letter."""
    if direction == "down":
        pts = f"{x_attach - 7:.1f},{y_attach:.1f} {x_attach + 7:.1f},{y_attach:.1f} {x_attach:.1f},{y_attach + 10:.1f}"
        lx, ly = x_attach, y_attach + 10.0
        bx, by = x_attach - 11.0, y_attach + 22.0
        out.append(f'<polygon points="{pts}" fill="{COLOR_DIM}"/>')
        out.append(
            f'<line x1="{lx:.1f}" y1="{ly:.1f}" x2="{lx:.1f}" y2="{by:.1f}" stroke="{COLOR_DIM}" stroke-width="1.2"/>'
        )
    elif direction == "left":
        pts = f"{x_attach:.1f},{y_attach - 7:.1f} {x_attach:.1f},{y_attach + 7:.1f} {x_attach - 10:.1f},{y_attach:.1f}"
        bx, by = x_attach - 42.0, y_attach - 11.0
        out.append(f'<polygon points="{pts}" fill="{COLOR_DIM}"/>')
        out.append(
            f'<line x1="{x_attach - 10:.1f}" y1="{y_attach:.1f}" x2="{bx + 22:.1f}" y2="{y_attach:.1f}" '
            f'stroke="{COLOR_DIM}" stroke-width="1.2"/>'
        )
    else:  # right
        pts = f"{x_attach:.1f},{y_attach - 7:.1f} {x_attach:.1f},{y_attach + 7:.1f} {x_attach + 10:.1f},{y_attach:.1f}"
        bx, by = x_attach + 20.0, y_attach - 11.0
        out.append(f'<polygon points="{pts}" fill="{COLOR_DIM}"/>')
        out.append(
            f'<line x1="{x_attach + 10:.1f}" y1="{y_attach:.1f}" x2="{bx:.1f}" y2="{y_attach:.1f}" '
            f'stroke="{COLOR_DIM}" stroke-width="1.2"/>'
        )

    out.append(
        f'<rect x="{bx:.1f}" y="{by:.1f}" width="22" height="22" fill="{COLOR_CANVAS}" '
        f'stroke="{COLOR_DIM}" stroke-width="1.3"/>'
    )
    out.append(
        f'<text x="{bx + 11:.1f}" y="{by + 15.5:.1f}" text-anchor="middle" '
        f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="13" '
        f'font-weight="700" fill="{COLOR_DIM}">{xml_escape(letter)}</text>'
    )


def _draw_gdt_frame(
    out: list[str],
    x: float,
    y: float,
    frame: GDTFrame,
    *,
    max_right_x: float = 1608.0,
) -> float:
    """Draw one ASME Y14.5 boxed GD&T feature control frame. Returns frame width."""
    h = 22.0
    sym_w = 26.0
    tol_txt = frame.tolerance_text()
    tol_w = max(60.0, len(tol_txt) * 8.0 + 14.0)
    datums = frame.datums()
    d_w = 22.0
    total_w = sym_w + tol_w + len(datums) * d_w

    out.append(
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{total_w:.1f}" height="{h:.1f}" '
        f'fill="{COLOR_CANVAS}" stroke="{COLOR_DIM}" stroke-width="1.2"/>'
    )
    # Symbol cell
    out.append(
        f'<text x="{x + sym_w / 2:.1f}" y="{y + 15.5:.1f}" text-anchor="middle" '
        f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="14" '
        f'fill="{COLOR_DIM}">{xml_escape(frame.glyph())}</text>'
    )
    cx = x + sym_w
    out.append(
        f'<line x1="{cx:.1f}" y1="{y:.1f}" x2="{cx:.1f}" y2="{y + h:.1f}" stroke="{COLOR_DIM}" stroke-width="1.1"/>'
    )
    # Tolerance cell
    out.append(
        f'<text x="{cx + tol_w / 2:.1f}" y="{y + 15.0:.1f}" text-anchor="middle" '
        f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="11.5" '
        f'font-weight="600" fill="{COLOR_INK}">{xml_escape(tol_txt)}</text>'
    )
    cx += tol_w
    for d in datums:
        out.append(
            f'<line x1="{cx:.1f}" y1="{y:.1f}" x2="{cx:.1f}" y2="{y + h:.1f}" stroke="{COLOR_DIM}" stroke-width="1.1"/>'
        )
        out.append(
            f'<text x="{cx + d_w / 2:.1f}" y="{y + 15.0:.1f}" text-anchor="middle" '
            f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="11.5" '
            f'font-weight="700" fill="{COLOR_DIM}">{xml_escape(d)}</text>'
        )
        cx += d_w

    if frame.feature_note:
        note_x = x + total_w + 10.0
        avail_px = max_right_x - note_x
        max_chars = int(avail_px / 6.3)
        if max_chars >= 6:
            clean_note = _truncate_clean(frame.feature_note, min(max_chars, 42))
            out.append(
                f'<text x="{note_x:.1f}" y="{y + 15.0:.1f}" '
                f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="10" '
                f'fill="{COLOR_SUBTEXT}">{xml_escape(clean_note)}</text>'
            )
    return total_w


def _draw_surface_finish_symbol(out: list[str], x: float, y: float, ra_um: float) -> None:
    """Draw ISO 1302 machining surface texture checkmark with ``Ra`` value."""
    # Machined triangle checkmark (ISO 1302 material removal required)
    out.append(
        f'<path d="M{x:.1f},{y + 8:.1f} L{x + 7:.1f},{y + 20:.1f} L{x + 19:.1f},{y:.1f} '
        f'L{x + 56:.1f},{y:.1f}" fill="none" stroke="{COLOR_INK}" stroke-width="1.3"/>'
    )
    out.append(
        f'<line x1="{x:.1f}" y1="{y + 8:.1f}" x2="{x + 14.2:.1f}" y2="{y + 8:.1f}" '
        f'stroke="{COLOR_INK}" stroke-width="1.1"/>'
    )
    out.append(
        f'<text x="{x + 21:.1f}" y="{y - 3:.1f}" '
        f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="11" '
        f'font-weight="600" fill="{COLOR_INK}">Ra {ra_um:.2g} µm</text>'
    )


def _draw_third_angle_symbol(out: list[str], cx: float, cy: float) -> None:
    """Draw ISO 128 third-angle projection cone & concentric-circles symbol."""
    # Frustum on left
    out.append(
        f'<polygon points="{cx - 34:.1f},{cy - 6:.1f} {cx - 10:.1f},{cy - 11:.1f} '
        f'{cx - 10:.1f},{cy + 11:.1f} {cx - 34:.1f},{cy + 6:.1f}" '
        f'fill="none" stroke="{COLOR_INK}" stroke-width="1.1"/>'
    )
    # Concentric circles on right
    out.append(f'<circle cx="{cx + 14:.1f}" cy="{cy:.1f}" r="11" fill="none" stroke="{COLOR_INK}" stroke-width="1.1"/>')
    out.append(f'<circle cx="{cx + 14:.1f}" cy="{cy:.1f}" r="6" fill="none" stroke="{COLOR_INK}" stroke-width="1.1"/>')
    # Centerlines
    out.append(
        f'<line x1="{cx - 40:.1f}" y1="{cy:.1f}" x2="{cx + 30:.1f}" y2="{cy:.1f}" '
        f'stroke="{COLOR_MUTED}" stroke-width="0.7" stroke-dasharray="6,3,1.5,3"/>'
    )
    out.append(
        f'<line x1="{cx + 14:.1f}" y1="{cy - 16:.1f}" x2="{cx + 14:.1f}" y2="{cy + 16:.1f}" '
        f'stroke="{COLOR_MUTED}" stroke-width="0.7" stroke-dasharray="6,3,1.5,3"/>'
    )


def _default_gdt_frames(part_design: PartDesign | None) -> tuple[GDTFrame, ...]:
    if part_design is not None and part_design.gdt_frames:
        return part_design.gdt_frames
    return (
        GDTFrame("flatness", 0.010, datum_primary="", feature_note="DATUM A MOUNTING SURFACE"),
        GDTFrame("perpendicularity", 0.020, diameter_zone=True, datum_primary="A", feature_note="PRIMARY AXIS / FLANGE"),
        GDTFrame("concentricity", 0.015, diameter_zone=True, datum_primary="B", feature_note="BORE / OPTICAL AXIS"),
        GDTFrame("profile_surface", 0.050, datum_primary="A", datum_secondary="B", feature_note="GENERAL MACHINED PROFILE"),
    )


# ---------------------------------------------------------------------------
# Main SVG Engineering Drawing Writer
# ---------------------------------------------------------------------------
def write_svg_gdt(
    mesh: SolidMesh,
    path: Path | str,
    *,
    part_design: PartDesign | None = None,
    mass_props: MassProperties | None = None,
) -> Path:
    """Export an ISO 128 / ASME Y14.5 white-paper academic 2D GD&T drawing ``.svg``."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    ports = part_design.ports if part_design is not None else ()
    mp = mass_props if mass_props is not None else compute_mass_props(
        mesh, material=(part_design.material if part_design else mesh.material)
    )

    front = extract_ortho_view(mesh, "front", ports=ports)
    top = extract_ortho_view(mesh, "top", ports=ports)
    right = extract_ortho_view(mesh, "right", ports=ports)
    iso = extract_iso_view(mesh)

    # Compute uniform orthographic scale so Top (XY), Front (XZ), and Right (YZ) fit cleanly
    # Drawing workspace: x in [50, 1080], y in [55, 1125] (right column x in [1095, 1630] holds Iso + GD&T + Title Block)
    avail_w = 880.0
    avail_h = 840.0
    total_ortho_w = front.width + right.width
    total_ortho_h = front.height + top.height
    scale = min(
        avail_w / max(total_ortho_w, 1e-3),
        avail_h / max(total_ortho_h, 1e-3),
    )
    # Clamp individual view extents to keep generous margins for dimensions
    max_view_w = 520.0
    max_view_h = 420.0
    scale = min(
        scale,
        max_view_w / max(front.width, 1e-3),
        max_view_w / max(right.width, 1e-3),
        max_view_h / max(front.height, 1e-3),
        max_view_h / max(top.height, 1e-3),
    )

    fw_px = front.width * scale
    fh_px = front.height * scale
    tw_px = top.width * scale
    th_px = top.height * scale
    rw_px = right.width * scale
    rh_px = right.height * scale

    # Aligned third-angle placement inside left workspace [50..1075, 55..1125]
    gap_x = 125.0
    gap_y = 115.0
    block_w = fw_px + gap_x + rw_px
    block_h = th_px + gap_y + fh_px
    base_x = 85.0 + max(0.0, 0.5 * (950.0 - block_w))
    base_y_top = 80.0 + max(0.0, 0.5 * (960.0 - block_h))

    top_ox = base_x
    top_oy_bot = base_y_top + th_px

    front_ox = base_x
    front_oy_bot = top_oy_bot + gap_y + fh_px

    right_ox = base_x + fw_px + gap_x
    right_oy_bot = front_oy_bot

    # Fit isometric wireframe inside upper-right box [1100..1620, 65..435]
    iso_box_x, iso_box_y, iso_box_w, iso_box_h = 1105.0, 68.0, 515.0, 355.0
    iso_scale = min(
        (iso_box_w - 70.0) / max(iso.width, 1e-3),
        (iso_box_h - 75.0) / max(iso.height, 1e-3),
    )
    iso_w_px = iso.width * iso_scale
    iso_h_px = iso.height * iso_scale
    iso_ox = iso_box_x + 0.5 * (iso_box_w - iso_w_px)
    iso_oy_bot = iso_box_y + 28.0 + 0.5 * (iso_box_h - 32.0 + iso_h_px)

    part_id = part_design.part_id if part_design else (mesh.name or out_path.stem)
    parent_id = part_design.parent_bom_id if part_design else "-"
    subsystem = part_design.subsystem if part_design else "-"
    part_name = part_design.part_name if part_design else part_id
    tier = part_design.design_tier if part_design else "CUSTOM_FULL"
    mat = part_design.material if part_design else mesh.material
    temp = part_design.temp_stage if part_design else "300 K"
    vac = part_design.vacuum_grade if part_design else "UHV 1e-9 mbar"
    tol = part_design.tolerance_spec if part_design else GENERAL_TOLERANCE_STD
    ra_um = part_design.surface_finish_ra_um if part_design else 0.8
    qty = part_design.qty if part_design else 1
    maturity = part_design.design_maturity if part_design else DESIGN_MATURITY
    no_lab = part_design.no_lab_measurement if part_design else NO_LAB_MEASUREMENT
    iec = part_design.iec61508_certified if part_design else IEC61508_CERTIFIED
    semi = part_design.semi_s2_certified if part_design else SEMI_S2_CERTIFIED

    out: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(SHEET_W)}" height="{int(SHEET_H)}" '
            f'viewBox="0 0 {int(SHEET_W)} {int(SHEET_H)}">'
        ),
        f"  <title>{xml_escape(part_id)} — {xml_escape(part_name)} (ISO 128 / ASME Y14.5)</title>",
        "  <defs>",
        (
            f'    <marker id="arrow-end" viewBox="0 0 10 6" refX="9" refY="3" '
            f'markerWidth="8" markerHeight="5" orient="auto">'
            f'<path d="M0,0 L10,3 L0,6 Z" fill="{COLOR_DIM}"/></marker>'
        ),
        (
            f'    <marker id="arrow-start" viewBox="0 0 10 6" refX="1" refY="3" '
            f'markerWidth="8" markerHeight="5" orient="auto">'
            f'<path d="M10,0 L0,3 L10,6 Z" fill="{COLOR_DIM}"/></marker>'
        ),
        "  </defs>",
        # Pure white academic paper canvas
        f'  <rect x="0" y="0" width="{int(SHEET_W)}" height="{int(SHEET_H)}" fill="{COLOR_CANVAS}"/>',
        # Outer ISO border & inner drawing frame
        f'  <rect x="18" y="18" width="{int(SHEET_W - 36)}" height="{int(SHEET_H - 36)}" '
        f'fill="none" stroke="{COLOR_INK}" stroke-width="1.2"/>',
        f'  <rect x="38" y="38" width="{int(SHEET_W - 76)}" height="{int(SHEET_H - 76)}" '
        f'fill="none" stroke="{COLOR_INK}" stroke-width="2.0"/>',
    ]

    # ISO A3 zone grid markers (1..8 horizontal, A..F vertical)
    for col in range(8):
        zx = 38.0 + col * (SHEET_W - 76.0) / 8.0
        if col > 0:
            out.append(f'  <line x1="{zx:.1f}" y1="18" x2="{zx:.1f}" y2="38" stroke="{COLOR_MUTED}" stroke-width="0.8"/>')
            out.append(f'  <line x1="{zx:.1f}" y1="{SHEET_H - 38:.1f}" x2="{zx:.1f}" y2="{SHEET_H - 18:.1f}" stroke="{COLOR_MUTED}" stroke-width="0.8"/>')
        cx_lbl = zx + (SHEET_W - 76.0) / 16.0
        out.append(
            f'  <text x="{cx_lbl:.1f}" y="32" text-anchor="middle" '
            f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="10" fill="{COLOR_MUTED}">{col + 1}</text>'
        )
        out.append(
            f'  <text x="{cx_lbl:.1f}" y="{SHEET_H - 24:.1f}" text-anchor="middle" '
            f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="10" fill="{COLOR_MUTED}">{col + 1}</text>'
        )
    for row, ch in enumerate("ABCDEF"):
        zy = 38.0 + row * (SHEET_H - 76.0) / 6.0
        if row > 0:
            out.append(f'  <line x1="18" y1="{zy:.1f}" x2="38" y2="{zy:.1f}" stroke="{COLOR_MUTED}" stroke-width="0.8"/>')
            out.append(f'  <line x1="{SHEET_W - 38:.1f}" y1="{zy:.1f}" x2="{SHEET_W - 18:.1f}" y2="{zy:.1f}" stroke="{COLOR_MUTED}" stroke-width="0.8"/>')
        cy_lbl = zy + (SHEET_H - 76.0) / 12.0 + 3.5
        out.append(
            f'  <text x="28" y="{cy_lbl:.1f}" text-anchor="middle" '
            f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="10" fill="{COLOR_MUTED}">{ch}</text>'
        )
        out.append(
            f'  <text x="{SHEET_W - 28:.1f}" y="{cy_lbl:.1f}" text-anchor="middle" '
            f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="10" fill="{COLOR_MUTED}">{ch}</text>'
        )

    # Vertical divider separating orthographic sheet from right engineering panel
    out.append(f'  <line x1="1088" y1="38" x2="1088" y2="{SHEET_H - 38:.1f}" stroke="{COLOR_RULE}" stroke-width="1.0"/>')

    # --- Render 3 Orthographic Views ---
    def _render_ortho(
        pv: ProjectedView,
        ox: float,
        oy_bot: float,
        view_id: str,
        *,
        title_offset_y: float = 24.0,
    ) -> None:
        w_px = pv.width * scale
        h_px = pv.height * scale
        oy_top = oy_bot - h_px
        out.append(f'  <g id="{view_id}">')
        # Hidden lines first (dashed slate)
        hd = _segments_to_path_d(pv.hidden_segments, pv.u_min, pv.v_min, ox, oy_bot, scale)
        if hd:
            out.append(
                f'    <path d="{hd}" fill="none" stroke="{COLOR_MUTED}" '
                f'stroke-width="0.85" stroke-dasharray="5,3.5"/>'
            )
        # Symmetry centerlines (dash-dot slate)
        cm_x = ox + 0.5 * w_px
        cm_y = oy_top + 0.5 * h_px
        out.append(
            f'    <line x1="{ox - 16:.1f}" y1="{cm_y:.1f}" x2="{ox + w_px + 16:.1f}" y2="{cm_y:.1f}" '
            f'stroke="{COLOR_MUTED}" stroke-width="0.8" stroke-dasharray="10,4,2,4"/>'
        )
        out.append(
            f'    <line x1="{cm_x:.1f}" y1="{oy_top - 16:.1f}" x2="{cm_x:.1f}" y2="{oy_bot + 16:.1f}" '
            f'stroke="{COLOR_MUTED}" stroke-width="0.8" stroke-dasharray="10,4,2,4"/>'
        )
        # Bolt-circle PCD / port center circles
        for pcu, pcv, pr in pv.center_circles:
            cx_p = ox + (pcu - pv.u_min) * scale
            cy_p = oy_bot - (pcv - pv.v_min) * scale
            r_p = pr * scale
            if r_p > 2.0:
                out.append(
                    f'    <circle cx="{cx_p:.2f}" cy="{cy_p:.2f}" r="{r_p:.2f}" fill="none" '
                    f'stroke="{COLOR_MUTED}" stroke-width="0.85" stroke-dasharray="8,3,2,3"/>'
                )
        # Visible outlines (crisp academic ink)
        vd = _segments_to_path_d(pv.visible_segments, pv.u_min, pv.v_min, ox, oy_bot, scale)
        if vd:
            out.append(
                f'    <path d="{vd}" fill="none" stroke="{COLOR_INK}" '
                f'stroke-width="1.45" stroke-linecap="round" stroke-linejoin="round"/>'
            )
        # View title
        out.append(
            f'    <text x="{ox + 0.5 * w_px:.1f}" y="{oy_top - title_offset_y:.1f}" text-anchor="middle" '
            f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="12" '
            f'font-weight="700" letter-spacing="0.6" fill="{COLOR_DIM}">{xml_escape(pv.name)}</text>'
        )
        out.append("  </g>")

    _render_ortho(top, top_ox, top_oy_bot, "view-top", title_offset_y=24.0)
    _render_ortho(front, front_ox, front_oy_bot, "view-front", title_offset_y=48.0)
    _render_ortho(right, right_ox, right_oy_bot, "view-right", title_offset_y=48.0)

    # Orthographic bounding dimensions (mm)
    ex, ey, ez = mp.extents_mm
    _draw_h_dim(out, front_ox, front_ox + fw_px, front_oy_bot, front_oy_bot + 34.0, f"{ex:.2f} mm")
    _draw_v_dim(out, front_ox, front_ox - 34.0, front_oy_bot - fh_px, front_oy_bot, f"{ez:.2f} mm")
    _draw_v_dim(out, top_ox, top_ox - 34.0, top_oy_bot - th_px, top_oy_bot, f"{ey:.2f} mm")
    _draw_h_dim(out, right_ox, right_ox + rw_px, right_oy_bot, right_oy_bot + 34.0, f"{ey:.2f} mm")

    # Datum triangles A, B, C cleanly positioned with generous clearance from titles & dimension lines
    out.append('  <g id="datum-callouts">')
    # Datum A: attached to a clean extension line off the bottom-right face of FRONT (XZ)
    out.append(
        f'    <line x1="{front_ox + fw_px + 4:.1f}" y1="{front_oy_bot:.1f}" '
        f'x2="{front_ox + fw_px + 34:.1f}" y2="{front_oy_bot:.1f}" '
        f'stroke="{COLOR_DIM}" stroke-width="1.0"/>'
    )
    _draw_datum_triangle(out, front_ox + fw_px + 22.0, front_oy_bot, "A", direction="down")
    # Datum B: attached to top vertical centerline of FRONT (XZ) (y = oy_top - 14; title sits at oy_top - 48)
    _draw_datum_triangle(out, front_ox + 0.50 * fw_px, front_oy_bot - fh_px - 14.0, "B", direction="right")
    # Datum C: attached to right horizontal centerline extension of TOP (XY)
    _draw_datum_triangle(out, top_ox + tw_px + 16.0, top_oy_bot - 0.50 * th_px, "C", direction="right")
    out.append("  </g>")

    # --- Isometric Wireframe Box (upper right) ---
    out.append('  <g id="view-isometric">')
    out.append(
        f'    <rect x="{iso_box_x:.1f}" y="{iso_box_y:.1f}" width="{iso_box_w:.1f}" height="{iso_box_h:.1f}" '
        f'fill="{COLOR_CANVAS}" stroke="{COLOR_RULE}" stroke-width="1.0"/>'
    )
    out.append(
        f'    <rect x="{iso_box_x:.1f}" y="{iso_box_y:.1f}" width="{iso_box_w:.1f}" height="24" '
        f'fill="{COLOR_HEADER_BG}" stroke="{COLOR_RULE}" stroke-width="1.0"/>'
    )
    out.append(
        f'    <text x="{iso_box_x + 12:.1f}" y="{iso_box_y + 16:.1f}" '
        f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="11.5" '
        f'font-weight="700" fill="{COLOR_DIM}">ISOMETRIC VIEW (3D WIREFRAME, NOT TO SCALE)</text>'
    )
    iso_hd = _segments_to_path_d(iso.hidden_segments, iso.u_min, iso.v_min, iso_ox, iso_oy_bot, iso_scale)
    if iso_hd:
        out.append(
            f'    <path d="{iso_hd}" fill="none" stroke="{COLOR_RULE}" stroke-width="0.7" stroke-dasharray="3,3"/>'
        )
    iso_vd = _segments_to_path_d(iso.visible_segments, iso.u_min, iso.v_min, iso_ox, iso_oy_bot, iso_scale)
    if iso_vd:
        out.append(
            f'    <path d="{iso_vd}" fill="none" stroke="{COLOR_INK}" stroke-width="1.15" stroke-linejoin="round"/>'
        )
    # Compact isometric XYZ triad in lower-left of isometric box
    tx, ty = iso_box_x + 34.0, iso_box_y + iso_box_h - 24.0
    out.append(f'    <line x1="{tx:.1f}" y1="{ty:.1f}" x2="{tx + 22:.1f}" y2="{ty - 11:.1f}" stroke="{COLOR_DIM}" stroke-width="1.2"/>')
    out.append(f'    <line x1="{tx:.1f}" y1="{ty:.1f}" x2="{tx - 20:.1f}" y2="{ty - 11:.1f}" stroke="{COLOR_DIM}" stroke-width="1.2"/>')
    out.append(f'    <line x1="{tx:.1f}" y1="{ty:.1f}" x2="{tx:.1f}" y2="{ty - 24:.1f}" stroke="{COLOR_DIM}" stroke-width="1.2"/>')
    out.append(f'    <text x="{tx + 25:.1f}" y="{ty - 10:.1f}" font-family="DejaVu Sans, sans-serif" font-size="9.5" fill="{COLOR_DIM}">X</text>')
    out.append(f'    <text x="{tx - 29:.1f}" y="{ty - 10:.1f}" font-family="DejaVu Sans, sans-serif" font-size="9.5" fill="{COLOR_DIM}">Y</text>')
    out.append(f'    <text x="{tx - 3:.1f}" y="{ty - 27:.1f}" font-family="DejaVu Sans, sans-serif" font-size="9.5" fill="{COLOR_DIM}">Z</text>')
    out.append("  </g>")

    # --- GD&T Control Frames + Surface Finish + Key Dimensions Panel (middle right) ---
    gdt_x, gdt_y, gdt_w, gdt_h = 1105.0, 438.0, 515.0, 392.0
    out.append('  <g id="gdt-panel">')
    out.append(
        f'    <rect x="{gdt_x:.1f}" y="{gdt_y:.1f}" width="{gdt_w:.1f}" height="{gdt_h:.1f}" '
        f'fill="{COLOR_CANVAS}" stroke="{COLOR_RULE}" stroke-width="1.0"/>'
    )
    out.append(
        f'    <rect x="{gdt_x:.1f}" y="{gdt_y:.1f}" width="{gdt_w:.1f}" height="24" '
        f'fill="{COLOR_HEADER_BG}" stroke="{COLOR_RULE}" stroke-width="1.0"/>'
    )
    out.append(
        f'    <text x="{gdt_x + 12:.1f}" y="{gdt_y + 16:.1f}" '
        f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="11.5" '
        f'font-weight="700" fill="{COLOR_DIM}">GD&amp;T FEATURE CONTROL FRAMES (ASME Y14.5 / ISO 1101)</text>'
    )

    # ISO 1302 Surface finish callout in upper-right of GD&T box
    _draw_surface_finish_symbol(out, gdt_x + gdt_w - 102.0, gdt_y + 36.0, ra_um)

    frames = _default_gdt_frames(part_design)
    cur_y = gdt_y + 32.0
    for idx_f, fr in enumerate(frames[:5]):
        # Avoid overlapping the Ra surface finish symbol on the top rows
        row_right_x = (gdt_x + gdt_w - 112.0) if idx_f < 2 else (gdt_x + gdt_w - 12.0)
        _draw_gdt_frame(out, gdt_x + 12.0, cur_y, fr, max_right_x=row_right_x)
        cur_y += 27.0

    # Datums summary block (wrapped cleanly across aligned rows strictly inside x <= 1610)
    cur_y += 3.0
    out.append(f'    <line x1="{gdt_x:.1f}" y1="{cur_y:.1f}" x2="{gdt_x + gdt_w:.1f}" y2="{cur_y:.1f}" stroke="{COLOR_RULE}" stroke-width="0.9"/>')
    cur_y += 14.0
    datums_list = part_design.datums if part_design else (("A", "MOUNTING PLANE"), ("B", "PRIMARY AXIS"), ("C", "INDEX"))
    out.append(
        f'    <text x="{gdt_x + 12:.1f}" y="{cur_y:.1f}" '
        f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="9.5" '
        f'font-weight="700" fill="{COLOR_DIM}">DATUMS:</text>'
    )
    datum_x = gdt_x + 68.0  # 1173.0 -> 437 px available strictly inside x <= 1610
    for d_idx, (dk, dv) in enumerate(datums_list[:3]):
        d_clean = _truncate_clean(dv, 54)
        out.append(
            f'    <text x="{datum_x:.1f}" y="{cur_y + d_idx * 13.5:.1f}" '
            f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="9.5" '
            f'font-weight="600" fill="{COLOR_DIM}">[{xml_escape(dk)}] {xml_escape(d_clean)}</text>'
        )
    cur_y += max(1, len(datums_list[:3])) * 13.5

    # Ports / Key Dimensions schedule inside lower half of GD&T box
    cur_y += 5.0
    out.append(f'    <line x1="{gdt_x:.1f}" y1="{cur_y:.1f}" x2="{gdt_x + gdt_w:.1f}" y2="{cur_y:.1f}" stroke="{COLOR_RULE}" stroke-width="0.9"/>')
    cur_y += 14.0
    if ports:
        out.append(
            f'    <text x="{gdt_x + 12:.1f}" y="{cur_y:.1f}" '
            f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="10" '
            f'font-weight="700" fill="{COLOR_DIM}">INTERFACES / PORTS ({len(ports)}):</text>'
        )
        cur_y += 14.5
        for p in ports[:4]:
            if cur_y > gdt_y + gdt_h - 8.0:
                break
            mate = f" -> {p.mating_part_id}" if p.mating_part_id else ""
            pcd_s = f" PCD {p.pcd_mm:.1f} ({p.bolt_count}xØ{p.bolt_hole_mm:.1f})" if p.pcd_mm > 0 else ""
            line_txt = _truncate_clean(f"• {p.name} [{p.standard}]{pcd_s}{mate}", 74)
            out.append(
                f'    <text x="{gdt_x + 16:.1f}" y="{cur_y:.1f}" '
                f'font-family="DejaVu Sans Mono, monospace" font-size="9.2" '
                f'fill="{COLOR_INK}">{xml_escape(line_txt)}</text>'
            )
            cur_y += 13.5
    if part_design is not None and part_design.dimensions and cur_y < gdt_y + gdt_h - 22.0:
        out.append(
            f'    <text x="{gdt_x + 12:.1f}" y="{cur_y + 3:.1f}" '
            f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="10" '
            f'font-weight="700" fill="{COLOR_DIM}">CRITICAL DIMENSIONS:</text>'
        )
        cur_y += 17.5
        for dc in part_design.dimensions[:4]:
            if cur_y > gdt_y + gdt_h - 8.0:
                break
            dim_txt = _truncate_clean(f"{dc.label}: {dc.format_text()}", 74)
            out.append(
                f'    <text x="{gdt_x + 16:.1f}" y="{cur_y:.1f}" '
                f'font-family="DejaVu Sans Mono, monospace" font-size="9.2" '
                f'fill="{COLOR_INK}">{xml_escape(dim_txt)}</text>'
            )
            cur_y += 13.5
    out.append("  </g>")

    # --- ISO 7200 Engineering & Epistemic Title Block (lower right) ---
    tb_x, tb_y, tb_w, tb_h = 1105.0, 845.0, 515.0, 295.0
    out.append('  <g id="title-block">')
    out.append(
        f'    <rect x="{tb_x:.1f}" y="{tb_y:.1f}" width="{tb_w:.1f}" height="{tb_h:.1f}" '
        f'fill="{COLOR_CANVAS}" stroke="{COLOR_INK}" stroke-width="1.8"/>'
    )
    # Row 1: Header band with Part ID & Subsystem
    out.append(
        f'    <rect x="{tb_x:.1f}" y="{tb_y:.1f}" width="{tb_w:.1f}" height="46" '
        f'fill="{COLOR_HEADER_BG}" stroke="{COLOR_INK}" stroke-width="1.2"/>'
    )
    out.append(
        f'    <text x="{tb_x + 12:.1f}" y="{tb_y + 18:.1f}" '
        f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="9.5" '
        f'font-weight="600" fill="{COLOR_MUTED}">ATOM LITHOGRAPHY MACHINE — EXACT BOM PART DRAWING ({xml_escape(subsystem)} / {xml_escape(tier)})</text>'
    )
    out.append(
        f'    <text x="{tb_x + 12:.1f}" y="{tb_y + 39:.1f}" '
        f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="18" '
        f'font-weight="700" fill="{COLOR_DIM}">{xml_escape(part_id)}</text>'
    )
    out.append(
        f'    <text x="{tb_x + tb_w - 12:.1f}" y="{tb_y + 38:.1f}" text-anchor="end" '
        f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="11" '
        f'font-weight="600" fill="{COLOR_SUBTEXT}">QTY: {qty} | PARENT: {xml_escape(parent_id)}</text>'
    )

    # Row 2: Part Name
    r2_y = tb_y + 46.0
    out.append(f'    <line x1="{tb_x:.1f}" y1="{r2_y + 34:.1f}" x2="{tb_x + tb_w:.1f}" y2="{r2_y + 34:.1f}" stroke="{COLOR_INK}" stroke-width="1.0"/>')
    out.append(
        f'    <text x="{tb_x + 12:.1f}" y="{r2_y + 13:.1f}" '
        f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="8.5" fill="{COLOR_MUTED}">DESCRIPTION</text>'
    )
    out.append(
        f'    <text x="{tb_x + 12:.1f}" y="{r2_y + 28:.1f}" '
        f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="11" '
        f'font-weight="600" fill="{COLOR_INK}">{xml_escape(_truncate_clean(part_name, 66))}</text>'
    )

    # Row 3: Material / Temp / Vacuum (3 columns)
    r3_y = r2_y + 34.0
    out.append(f'    <line x1="{tb_x:.1f}" y1="{r3_y + 44:.1f}" x2="{tb_x + tb_w:.1f}" y2="{r3_y + 44:.1f}" stroke="{COLOR_INK}" stroke-width="1.0"/>')
    c1 = tb_x + 195.0
    c2 = tb_x + 345.0
    out.append(f'    <line x1="{c1:.1f}" y1="{r3_y:.1f}" x2="{c1:.1f}" y2="{r3_y + 44:.1f}" stroke="{COLOR_RULE}" stroke-width="1.0"/>')
    out.append(f'    <line x1="{c2:.1f}" y1="{r3_y:.1f}" x2="{c2:.1f}" y2="{r3_y + 44:.1f}" stroke="{COLOR_RULE}" stroke-width="1.0"/>')

    for x_col, lbl, val_s, fsz in (
        (tb_x + 10.0, "MATERIAL", _truncate_clean(mat, 25), "10.5"),
        (c1 + 10.0, "OPERATING TEMP", _truncate_clean(temp, 22), "10"),
        (c2 + 10.0, "VACUUM GRADE", _truncate_clean(vac, 22), "10.5"),
    ):
        out.append(
            f'    <text x="{x_col:.1f}" y="{r3_y + 14:.1f}" '
            f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="8.5" fill="{COLOR_MUTED}">{lbl}</text>'
        )
        out.append(
            f'    <text x="{x_col:.1f}" y="{r3_y + 33:.1f}" '
            f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="{fsz}" '
            f'font-weight="600" fill="{COLOR_INK}">{xml_escape(val_s)}</text>'
        )

    # Row 4: Tolerance / Mass & Volume / CG
    r4_y = r3_y + 44.0
    out.append(f'    <line x1="{tb_x:.1f}" y1="{r4_y + 48:.1f}" x2="{tb_x + tb_w:.1f}" y2="{r4_y + 48:.1f}" stroke="{COLOR_INK}" stroke-width="1.0"/>')
    out.append(f'    <line x1="{c1:.1f}" y1="{r4_y:.1f}" x2="{c1:.1f}" y2="{r4_y + 48:.1f}" stroke="{COLOR_RULE}" stroke-width="1.0"/>')
    out.append(f'    <line x1="{c2:.1f}" y1="{r4_y:.1f}" x2="{c2:.1f}" y2="{r4_y + 48:.1f}" stroke="{COLOR_RULE}" stroke-width="1.0"/>')

    cgx = 0.0 if abs(mp.cg_mm[0]) < 1e-9 else mp.cg_mm[0]
    cgy = 0.0 if abs(mp.cg_mm[1]) < 1e-9 else mp.cg_mm[1]
    cgz = 0.0 if abs(mp.cg_mm[2]) < 1e-9 else mp.cg_mm[2]
    for x_col, lbl, val1, val2 in (
        (tb_x + 10.0, "TOLERANCE / FINISH", _truncate_clean(tol, 26), f"Ra {ra_um:.2g} µm | {GENERAL_TOLERANCE_STD}"),
        (c1 + 10.0, "MASS / VOLUME", f"{mp.mass_kg:.4f} kg", f"{mp.volume_cm3:.2f} cm³"),
        (c2 + 10.0, "CENTER OF GRAVITY (mm)", f"X={cgx:.2f}  Y={cgy:.2f}", f"Z={cgz:.2f}"),
    ):
        out.append(
            f'    <text x="{x_col:.1f}" y="{r4_y + 13:.1f}" '
            f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="8.5" fill="{COLOR_MUTED}">{lbl}</text>'
        )
        out.append(
            f'    <text x="{x_col:.1f}" y="{r4_y + 29:.1f}" '
            f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="10.5" '
            f'font-weight="600" fill="{COLOR_INK}">{xml_escape(val1)}</text>'
        )
        out.append(
            f'    <text x="{x_col:.1f}" y="{r4_y + 42:.1f}" '
            f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="9.5" '
            f'fill="{COLOR_SUBTEXT}">{xml_escape(val2)}</text>'
        )

    # Row 5: Envelope / Scale / Projection symbol
    r5_y = r4_y + 48.0
    out.append(f'    <line x1="{tb_x:.1f}" y1="{r5_y + 48:.1f}" x2="{tb_x + tb_w:.1f}" y2="{r5_y + 48:.1f}" stroke="{COLOR_INK}" stroke-width="1.0"/>')
    out.append(f'    <line x1="{tb_x + 250:.1f}" y1="{r5_y:.1f}" x2="{tb_x + 250:.1f}" y2="{r5_y + 48:.1f}" stroke="{COLOR_RULE}" stroke-width="1.0"/>')
    out.append(f'    <line x1="{tb_x + 380:.1f}" y1="{r5_y:.1f}" x2="{tb_x + 380:.1f}" y2="{r5_y + 48:.1f}" stroke="{COLOR_RULE}" stroke-width="1.0"/>')

    out.append(
        f'    <text x="{tb_x + 10:.1f}" y="{r5_y + 14:.1f}" '
        f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="8.5" fill="{COLOR_MUTED}">ENVELOPE (dX × dY × dZ)</text>'
    )
    out.append(
        f'    <text x="{tb_x + 10:.1f}" y="{r5_y + 34:.1f}" '
        f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="11" '
        f'font-weight="600" fill="{COLOR_INK}">{ex:.2f} × {ey:.2f} × {ez:.2f} mm</text>'
    )
    out.append(
        f'    <text x="{tb_x + 260:.1f}" y="{r5_y + 14:.1f}" '
        f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="8.5" fill="{COLOR_MUTED}">UNITS / SCALE</text>'
    )
    out.append(
        f'    <text x="{tb_x + 260:.1f}" y="{r5_y + 34:.1f}" '
        f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="11" '
        f'font-weight="600" fill="{COLOR_INK}">mm | {_fmt_scale(scale)}</text>'
    )
    out.append(
        f'    <text x="{tb_x + 448:.1f}" y="{r5_y + 12:.1f}" text-anchor="middle" '
        f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="8" fill="{COLOR_MUTED}">THIRD-ANGLE</text>'
    )
    _draw_third_angle_symbol(out, tb_x + 450.0, r5_y + 30.0)

    # Row 6: Mandatory Epistemic Disclaimer Stamp
    r6_y = r5_y + 48.0
    out.append(
        f'    <rect x="{tb_x:.1f}" y="{r6_y:.1f}" width="{tb_w:.1f}" height="{tb_y + tb_h - r6_y:.1f}" '
        f'fill="{COLOR_HEADER_BG}" stroke="{COLOR_INK}" stroke-width="1.2"/>'
    )
    out.append(
        f'    <text x="{tb_x + 12:.1f}" y="{r6_y + 20:.1f}" '
        f'font-family="DejaVu Sans Mono, monospace" font-size="9.5" '
        f'font-weight="700" fill="{COLOR_DIM}">STATUS: {xml_escape(maturity)}</text>'
    )
    out.append(
        f'    <text x="{tb_x + 12:.1f}" y="{r6_y + 38:.1f}" '
        f'font-family="DejaVu Sans Mono, monospace" font-size="9" '
        f'fill="{COLOR_SUBTEXT}">no_lab_measurement={str(no_lab).lower()} | '
        f'iec61508_certified={str(iec).lower()} | semi_s2_certified={str(semi).lower()}</text>'
    )
    out.append(
        f'    <text x="{tb_x + 12:.1f}" y="{r6_y + 56:.1f}" '
        f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="9" '
        f'fill="{COLOR_MUTED}">ALL DIMENSIONS IN MILLIMETERS. DO NOT SCALE DRAWING. REMOVE ALL BURRS.</text>'
    )
    out.append("  </g>")
    out.append("</svg>")

    out_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Strict Independent SVG XML & White-Paper Palette Validator
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SvgValidationResult:
    """Validation report for an ISO 128 / ASME Y14.5 SVG engineering drawing."""

    valid: bool
    well_formed_xml: bool
    white_canvas: bool
    academic_palette_only: bool
    disallowed_colors: tuple[str, ...]
    has_all_four_views: bool
    has_gdt_glyphs: bool
    has_epistemic_stamp: bool
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_HEX_COLOR_RE = re.compile(r"#[0-9A-Fa-f]{6}\b")
_GDT_GLYPHS = frozenset({"⊥", "◎", "⌓", "⏥", "⌖", "∥", "○", "⌭", "⎯", "↗"})


def validate_svg_file(
    path: Path | str,
    *,
    check_layout: bool = False,
) -> SvgValidationResult:
    """Strictly verify XML well-formedness, white-paper palette, 4 views, GD&T & epistemic stamp.

    When ``check_layout=True``, also verifies typographic layout invariants:
    - All text inside ``gdt-panel`` and ``title-block`` fits strictly inside ``x <= 1620``.
    - Zero unmatched opening parentheses ``(`` in rendered text elements.
    - ``FRONT (XZ)`` view title has positive vertical clearance above Datum ``[B]``.
    """
    errors: list[str] = []
    p = Path(path)
    if not p.is_file():
        return SvgValidationResult(
            valid=False,
            well_formed_xml=False,
            white_canvas=False,
            academic_palette_only=False,
            disallowed_colors=(),
            has_all_four_views=False,
            has_gdt_glyphs=False,
            has_epistemic_stamp=False,
            errors=(f"SVG file does not exist: {p}",),
        )

    text = p.read_text(encoding="utf-8")
    try:
        root = ET.fromstring(text)
        well_formed = True
    except ET.ParseError as exc:
        return SvgValidationResult(
            valid=False,
            well_formed_xml=False,
            white_canvas=False,
            academic_palette_only=False,
            disallowed_colors=(),
            has_all_four_views=False,
            has_gdt_glyphs=False,
            has_epistemic_stamp=False,
            errors=(f"XML parse error: {exc}",),
        )

    if not root.tag.endswith("svg"):
        errors.append(f"Root tag is not <svg>: {root.tag}")
    if "viewBox" not in root.attrib:
        errors.append("Missing viewBox attribute on <svg>")

    # Palette audit: every hex color must belong to APPROVED_ACADEMIC_PALETTE
    found_colors = {m.group(0).upper() for m in _HEX_COLOR_RE.finditer(text)}
    disallowed = sorted(c for c in found_colors if c not in APPROVED_ACADEMIC_PALETTE)
    palette_ok = len(disallowed) == 0
    if not palette_ok:
        errors.append(f"Non-academic/flashy hex colors detected: {disallowed}")

    white_canvas = f'fill="{COLOR_CANVAS}"' in text
    if not white_canvas:
        errors.append("Missing #FFFFFF white-paper canvas background")

    # View presence audit
    ids = {el.attrib.get("id", "") for el in root.iter()}
    req_views = {"view-top", "view-front", "view-right", "view-isometric"}
    has_views = req_views.issubset(ids)
    if not has_views:
        errors.append(f"Missing required view groups: {sorted(req_views - ids)}")

    # GD&T glyph audit
    has_gdt = any(g in text for g in _GDT_GLYPHS)
    if not has_gdt:
        errors.append("No ASME Y14.5 GD&T symbol glyphs found in SVG")

    if "Ra " not in text:
        errors.append("Missing ISO 1302 surface finish Ra callout")

    has_epistemic = (
        DESIGN_MATURITY in text
        and "no_lab_measurement=true" in text
        and "iec61508_certified=false" in text
        and "semi_s2_certified=false" in text
    )
    if not has_epistemic:
        errors.append("Missing required epistemic metadata stamp in title block")

    if check_layout:
        # 1) Check right-panel text bounds (gdt-panel & title-block strictly <= x=1620) & balanced parens
        for grp_id in ("gdt-panel", "title-block"):
            for grp in root.iter():
                if grp.attrib.get("id") != grp_id:
                    continue
                for el in grp.iter():
                    if not el.tag.endswith("text"):
                        continue
                    txt = (el.text or "").strip()
                    if not txt:
                        continue
                    if txt.count("(") != txt.count(")"):
                        errors.append(f"Unmatched parenthesis in {grp_id}: {txt!r}")
                    anchor = el.attrib.get("text-anchor", "start")
                    if anchor == "start":
                        tx = float(el.attrib.get("x", "0"))
                        fsz = float(el.attrib.get("font-size", "10"))
                        # Conservative glyph advance estimate (~0.62 * font-size for DejaVu Sans/Mono)
                        est_right = tx + len(txt) * fsz * 0.62
                        if est_right > 1620.0:
                            errors.append(
                                f"Text overflows {grp_id} right border (est x={est_right:.1f} > 1620): {txt!r}"
                            )
        # 2) Check FRONT (XZ) title vertical clearance above Datum [B] box
        front_title_y: float | None = None
        datum_b_top_y: float | None = None
        for el in root.iter():
            if el.tag.endswith("text"):
                txt = (el.text or "").strip()
                if txt == "FRONT (XZ)":
                    front_title_y = float(el.attrib.get("y", "0"))
                elif txt == "B" and el.attrib.get("font-size") == "13":
                    # Datum box top is text_y - 15.5
                    datum_b_top_y = float(el.attrib.get("y", "0")) - 15.5
        if front_title_y is not None and datum_b_top_y is not None:
            if front_title_y + 4.0 >= datum_b_top_y:
                errors.append(
                    f"FRONT (XZ) title (y={front_title_y:.1f}) overlaps Datum [B] box top (y={datum_b_top_y:.1f})"
                )

    return SvgValidationResult(
        valid=(len(errors) == 0),
        well_formed_xml=well_formed,
        white_canvas=white_canvas,
        academic_palette_only=palette_ok,
        disallowed_colors=tuple(disallowed),
        has_all_four_views=has_views,
        has_gdt_glyphs=has_gdt,
        has_epistemic_stamp=has_epistemic,
        errors=tuple(errors),
    )
