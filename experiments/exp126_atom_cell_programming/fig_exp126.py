"""Exp126 high-resolution publication-grade figures using pure PyCairo + PIL (/usr/bin/python3 -B).

Reads results/exp126_atom_cell_programming/exp126.json and generates:
  1. results/exp126_atom_cell_programming/fig_exp126_grape_pulses.png
  2. results/exp126_atom_cell_programming/fig_exp126_interleaved_dd_vs_exp63.png
  3. results/exp126_atom_cell_programming/fig_exp126_multicell_programs.png
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import List, Sequence, Tuple

import cairo

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results" / "exp126_atom_cell_programming"
DATA_JSON = OUT_DIR / "exp126.json"

# Clean scientific palette (colorblind-friendly Okabe-Ito inspired)
BG = (0.985, 0.988, 0.994)
PANEL_BG = (1.0, 1.0, 1.0)
GRID = (0.88, 0.90, 0.93)
AXIS = (0.20, 0.24, 0.30)
TEXT = (0.12, 0.15, 0.20)
MUTED = (0.42, 0.47, 0.54)

BLUE = (0.09, 0.42, 0.72)
ORANGE = (0.89, 0.45, 0.08)
GREEN = (0.11, 0.60, 0.38)
RED = (0.80, 0.20, 0.22)
PURPLE = (0.48, 0.28, 0.68)
TEAL = (0.05, 0.56, 0.62)
GOLD = (0.82, 0.64, 0.08)
GRAY = (0.50, 0.54, 0.60)


def _new_canvas(w: int, h: int, title: str, subtitle: str) -> Tuple[cairo.ImageSurface, cairo.Context]:
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*BG)
    ctx.rectangle(0, 0, w, h)
    ctx.fill()

    # Header bar
    ctx.set_source_rgb(0.11, 0.16, 0.24)
    ctx.rectangle(0, 0, w, 86)
    ctx.fill()

    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(26)
    ctx.set_source_rgb(1.0, 1.0, 1.0)
    ctx.move_to(36, 40)
    ctx.show_text(title)

    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(15)
    ctx.set_source_rgb(0.80, 0.86, 0.93)
    ctx.move_to(36, 68)
    ctx.show_text(subtitle)
    return surf, ctx


def _draw_text(ctx: cairo.Context, x: float, y: float, text: str, size: float = 14,
               bold: bool = False, color: Tuple[float, float, float] = TEXT,
               align: str = "left", angle: float = 0.0) -> None:
    ctx.save()
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)
    ctx.set_source_rgb(*color)
    ext = ctx.text_extents(text)
    ctx.translate(x, y)
    if angle != 0.0:
        ctx.rotate(angle)
    dx = 0.0
    if align == "center":
        dx = -ext.width / 2.0 - ext.x_bearing
    elif align == "right":
        dx = -ext.width - ext.x_bearing
    ctx.move_to(dx, 0.0)
    ctx.show_text(text)
    ctx.restore()


class Axes:
    def __init__(self, ctx: cairo.Context, x0: float, y0: float, w: float, h: float,
                 xmin: float, xmax: float, ymin: float, ymax: float,
                 title: str, xlabel: str = "", ylabel: str = "") -> None:
        self.ctx = ctx
        self.x0, self.y0, self.w, self.h = x0, y0, w, h
        self.xmin, self.xmax, self.ymin, self.ymax = xmin, xmax, ymin, ymax

        # Panel frame
        ctx.set_source_rgb(*PANEL_BG)
        ctx.rectangle(x0, y0, w, h)
        ctx.fill()
        ctx.set_source_rgb(*AXIS)
        ctx.set_line_width(1.6)
        ctx.rectangle(x0, y0, w, h)
        ctx.stroke()

        _draw_text(ctx, x0, y0 - 12, title, size=17, bold=True, color=TEXT, align="left")
        if xlabel:
            _draw_text(ctx, x0 + w / 2.0, y0 + h + 44, xlabel, size=14, bold=True, color=AXIS, align="center")
        if ylabel:
            _draw_text(ctx, x0 - 58, y0 + h / 2.0, ylabel, size=14, bold=True, color=AXIS,
                       align="center", angle=-math.pi / 2.0)

    def px(self, x: float) -> float:
        return self.x0 + (x - self.xmin) / (self.xmax - self.xmin) * self.w

    def py(self, y: float) -> float:
        return self.y0 + self.h - (y - self.ymin) / (self.ymax - self.ymin) * self.h

    def draw_grid(self, xticks: Sequence[Tuple[float, str]], yticks: Sequence[Tuple[float, str]]) -> None:
        ctx = self.ctx
        ctx.set_line_width(1.0)
        for xv, lbl in xticks:
            px = self.px(xv)
            if self.x0 <= px <= self.x0 + self.w + 1:
                ctx.set_source_rgb(*GRID)
                ctx.move_to(px, self.y0)
                ctx.line_to(px, self.y0 + self.h)
                ctx.stroke()
                ctx.set_source_rgb(*AXIS)
                ctx.move_to(px, self.y0 + self.h)
                ctx.line_to(px, self.y0 + self.h + 6)
                ctx.stroke()
                if lbl:
                    _draw_text(ctx, px, self.y0 + self.h + 22, lbl, size=12.5, color=MUTED, align="center")
        for yv, lbl in yticks:
            py = self.py(yv)
            if self.y0 - 1 <= py <= self.y0 + self.h + 1:
                ctx.set_source_rgb(*GRID)
                ctx.move_to(self.x0, py)
                ctx.line_to(self.x0 + self.w, py)
                ctx.stroke()
                ctx.set_source_rgb(*AXIS)
                ctx.move_to(self.x0 - 6, py)
                ctx.line_to(self.x0, py)
                ctx.stroke()
                if lbl:
                    _draw_text(ctx, self.x0 - 10, py + 4, lbl, size=12.5, color=MUTED, align="right")

    def plot_line(self, xs: Sequence[float], ys: Sequence[float], color: Tuple[float, float, float],
                  lw: float = 2.4, dashed: bool = False, marker: str = "") -> None:
        ctx = self.ctx
        ctx.save()
        ctx.rectangle(self.x0, self.y0, self.w, self.h)
        ctx.clip()
        ctx.set_source_rgb(*color)
        ctx.set_line_width(lw)
        if dashed:
            ctx.set_dash([7.0, 5.0])
        for i, (xv, yv) in enumerate(zip(xs, ys)):
            px, py = self.px(xv), self.py(yv)
            if i == 0:
                ctx.move_to(px, py)
            else:
                ctx.line_to(px, py)
        ctx.stroke()
        ctx.set_dash([])
        if marker:
            for xv, yv in zip(xs, ys):
                px, py = self.px(xv), self.py(yv)
                if marker == "o":
                    ctx.arc(px, py, 4.8, 0, 2 * math.pi)
                    ctx.fill()
                elif marker == "s":
                    ctx.rectangle(px - 4.2, py - 4.2, 8.4, 8.4)
                    ctx.fill()
                elif marker == "d":
                    ctx.move_to(px, py - 5.5); ctx.line_to(px + 5.5, py)
                    ctx.line_to(px, py + 5.5); ctx.line_to(px - 5.5, py); ctx.close_path()
                    ctx.fill()
        ctx.restore()

    def plot_step(self, t_edges: Sequence[float], vals: Sequence[float], color: Tuple[float, float, float],
                  lw: float = 2.0, alpha: float = 1.0) -> None:
        ctx = self.ctx
        ctx.save()
        ctx.rectangle(self.x0, self.y0, self.w, self.h)
        ctx.clip()
        ctx.set_source_rgba(color[0], color[1], color[2], alpha)
        ctx.set_line_width(lw)
        for i, v in enumerate(vals):
            x1, x2 = self.px(t_edges[i]), self.px(t_edges[i + 1])
            py = self.py(v)
            if i == 0:
                ctx.move_to(x1, py)
            else:
                ctx.line_to(x1, py)
            ctx.line_to(x2, py)
        ctx.stroke()
        ctx.restore()

    def hline(self, yv: float, color: Tuple[float, float, float], lw: float = 1.6,
              dashed: bool = True, label: str = "", label_x_frac: float = 0.98) -> None:
        ctx = self.ctx
        py = self.py(yv)
        ctx.save()
        ctx.set_source_rgb(*color)
        ctx.set_line_width(lw)
        if dashed:
            ctx.set_dash([6.0, 4.0])
        ctx.move_to(self.x0, py)
        ctx.line_to(self.x0 + self.w, py)
        ctx.stroke()
        ctx.set_dash([])
        if label:
            _draw_text(ctx, self.x0 + self.w * label_x_frac, py - 6, label,
                       size=12, bold=True, color=color, align="right")
        ctx.restore()

    def draw_legend(self, items: Sequence[Tuple[str, Tuple[float, float, float], bool]],
                    x: float, y: float, w_box: float = 260) -> None:
        ctx = self.ctx
        row_h = 22
        h_box = 14 + row_h * len(items)
        ctx.save()
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.93)
        ctx.rectangle(x, y, w_box, h_box)
        ctx.fill()
        ctx.set_source_rgb(0.75, 0.78, 0.84)
        ctx.set_line_width(1.1)
        ctx.rectangle(x, y, w_box, h_box)
        ctx.stroke()
        for idx, (lbl, col, dashed) in enumerate(items):
            yy = y + 18 + idx * row_h
            ctx.set_source_rgb(*col)
            ctx.set_line_width(2.8)
            if dashed:
                ctx.set_dash([5.0, 4.0])
            ctx.move_to(x + 10, yy - 4)
            ctx.line_to(x + 36, yy - 4)
            ctx.stroke()
            ctx.set_dash([])
            _draw_text(ctx, x + 44, yy, lbl, size=12, color=TEXT, align="left")
        ctx.restore()


# ---------------------------------------------------------------------------
# FIGURE 1: GRAPE Pulses, Interleaved XY8 Markers, DDRF Headroom & Universal Gates
# ---------------------------------------------------------------------------
def build_fig1_grape_pulses(data: dict) -> Path:
    W, H = 1920, 1200
    surf, ctx = _new_canvas(
        W, H,
        "Exp126 — Full-32D Minimax-Robust GRAPE Waveforms, DDRF Crosstalk Suppression & Universal Gates (F1, f=1%)",
        "31P electron + 4x 29Si nuclei (exact dipolar J_ij + 448 bath spectators) | +-400 Hz x +-2% corners | no_lab_measurement=true",
    )

    p1 = data["part1_f1_universal_gates"]
    wfs = p1["waveforms"]
    wf_cx3 = wfs["cX_XY8_16_q3"]
    wf_rx0 = wfs["Rx_pi2_q0"]
    wf_x0 = wfs["X_q0"]

    # Panel A (Top-Left): cX_XY8_16 q3 (hardest: min_gap=6.89 kHz!)
    axA = Axes(ctx, 95, 145, 830, 415, 0.0, 500.0, -16.5, 16.5,
               "A. Interleaved XY8-GRAPE cX (e->q3, min_gap=6.89 kHz, N_dd=16)",
               "Time t (us)", "RF Control Amplitude (kHz)")
    axA.draw_grid(
        [(v, f"{v:g}") for v in range(0, 501, 100)],
        [(v, f"{v:+.0f}") for v in (-15, -10, -5, 0, 5, 10, 15)],
    )
    axA.hline(0.0, GRAY, lw=1.0, dashed=False)
    t_edges = [i * 500.0 / 64.0 for i in range(65)]
    ux3 = [c[0] for c in wf_cx3["controls_khz"]]
    uy3 = [c[1] for c in wf_cx3["controls_khz"]]
    # Draw 16 XY8 electron pi-pulse vertical markers at (p+0.5)*500/16 us
    xy8_pat = ["X", "Y", "X", "Y", "Y", "X", "Y", "X"]
    for p_idx in range(16):
        tp = (p_idx + 0.5) * 500.0 / 16.0
        px = axA.px(tp)
        col = GREEN if xy8_pat[p_idx % 8] == "X" else PURPLE
        ctx.save()
        ctx.set_source_rgba(col[0], col[1], col[2], 0.35)
        ctx.set_line_width(1.4)
        ctx.set_dash([3.0, 3.0])
        ctx.move_to(px, axA.y0)
        ctx.line_to(px, axA.y0 + axA.h)
        ctx.stroke()
        ctx.restore()
        _draw_text(ctx, px, axA.y0 + 14, xy8_pat[p_idx % 8], size=10.5, bold=True, color=col, align="center")

    axA.plot_step(t_edges, ux3, BLUE, lw=2.3)
    axA.plot_step(t_edges, uy3, ORANGE, lw=2.1)
    axA.draw_legend([
        ("u_x(t) RF I-quadrature (kHz)", BLUE, False),
        ("u_y(t) RF Q-quadrature (kHz)", ORANGE, False),
        ("XY8 Electron pi_X / pi_Y pulses (16)", GREEN, True),
    ], axA.x0 + 16, axA.y0 + axA.h - 92, w_box=305)
    _draw_text(
        ctx, axA.x0 + axA.w - 14, axA.y0 + axA.h - 14,
        f"32D Nom F={wf_cx3['nominal_fidelity_32d']:.5f} | Worst Corner={wf_cx3['worst_corner_fidelity_32d']:.4f}",
        size=12.5, bold=True, color=BLUE, align="right",
    )

    # Panel B (Top-Right): Single-qubit Rx(pi/2) & X waveforms on q0
    axB = Axes(ctx, 1030, 145, 830, 415, 0.0, 500.0, -10.0, 12.0,
               "B. Eigen-Frame Single-Qubit GRAPE Waveforms (q0, |0_e> Eigenstate)",
               "Time t (us)", "RF Control Amplitude (kHz)")
    axB.draw_grid(
        [(v, f"{v:g}") for v in range(0, 501, 100)],
        [(v, f"{v:+.0f}") for v in (-10, -5, 0, 5, 10)],
    )
    axB.hline(0.0, GRAY, lw=1.0, dashed=False)
    axB.plot_step(t_edges, [c[0] for c in wf_rx0["controls_khz"]], TEAL, lw=2.3)
    axB.plot_step(t_edges, [c[1] for c in wf_rx0["controls_khz"]], GREEN, lw=1.8)
    axB.plot_step(t_edges, [c[0] for c in wf_x0["controls_khz"]], RED, lw=2.2)
    axB.plot_step(t_edges, [c[1] for c in wf_x0["controls_khz"]], GOLD, lw=1.8)
    axB.draw_legend([
        (f"Rx(pi/2) u_x  (Nom={wf_rx0['nominal_fidelity_32d']:.5f}, WC={wf_rx0['worst_corner_fidelity_32d']:.4f})", TEAL, False),
        ("Rx(pi/2) u_y", GREEN, False),
        (f"X(pi) u_x     (Nom={wf_x0['nominal_fidelity_32d']:.5f}, WC={wf_x0['worst_corner_fidelity_32d']:.4f})", RED, False),
        ("X(pi) u_y", GOLD, False),
    ], axB.x0 + axB.w - 448, axB.y0 + 16, w_box=434)

    # Panel C (Bottom-Left): DDRF Hyperfine-Refocusing Crosstalk Discovery & GRAPE Recovery
    ddrf = p1["ddrf_headroom_diagnostic"]
    axC = Axes(ctx, 95, 680, 830, 420, -0.5, 8.5, 0.0, 1.12,
               "C. Interleaved XY8 DDRF Spectator Crosstalk Discovery & GRAPE Recovery (F1 q3)",
               "Pulse Scheme / N_dd per 500 us Gate", "448-Bath Spectator Overlap & 32D Fidelity")
    axC.draw_grid([], [(v, f"{v:.1f}") for v in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)])
    axC.hline(0.99, GREEN, lw=1.4, dashed=True, label="0.99 target", label_x_frac=0.56)

    bar_specs = []
    for r in ddrf["gauss500_vs_ndd"]:
        bar_specs.append((f"G500\nN={r['n_dd_per_gate']}", r["spectator_overlap_all448"], r["min_spectator_retention_nom"], RED))
    for r in ddrf["grape_ndd16_vs_bound"]:
        bar_specs.append((f"GRAPE\n{int(r['bound_kHz'])}k", r["spectator_overlap_all448"], r["nominal_fidelity_32d"], BLUE))

    for i, (lbl, v_ovl, v_sec, col) in enumerate(bar_specs):
        xc = i
        bw = 0.34
        # Bar 1: all-448 spectator overlap
        x1, x2 = axC.px(xc - bw), axC.px(xc - 0.02)
        y1, y2 = axC.py(v_ovl), axC.py(0.0)
        ctx.set_source_rgb(*col)
        ctx.rectangle(x1, y1, x2 - x1, y2 - y1)
        ctx.fill()
        # Bar 2: secondary (min ret for GAUSS, 32D nom F for GRAPE)
        x3, x4 = axC.px(xc + 0.02), axC.px(xc + bw)
        y3, y4 = axC.py(v_sec), axC.py(0.0)
        col2 = ORANGE if col == RED else GREEN
        ctx.set_source_rgb(*col2)
        ctx.rectangle(x3, y3, x4 - x3, y4 - y3)
        ctx.fill()
        txt = f"{v_ovl:.3f}" if v_ovl >= 0.01 else f"{v_ovl:.1e}"
        _draw_text(ctx, axC.px(xc - bw / 2), axC.py(v_ovl) - 6, txt, size=10.5, bold=True, color=col, align="center")
        parts = lbl.split("\n")
        _draw_text(ctx, axC.px(xc), axC.y0 + axC.h + 18, parts[0], size=11.5, bold=True, color=TEXT, align="center")
        _draw_text(ctx, axC.px(xc), axC.y0 + axC.h + 33, parts[1], size=11, color=MUTED, align="center")

    axC.draw_legend([
        ("GAUSS500: 448-bath spectator overlap (collapses!)", RED, False),
        ("GAUSS500: worst single spectator retention", ORANGE, False),
        ("GRAPE (N=16): 448-bath spectator overlap (recovers!)", BLUE, False),
        ("GRAPE (N=16): full-32D nominal gate fidelity", GREEN, False),
    ], axC.x0 + 235, axC.y0 + 115, w_box=388)

    # Panel D (Bottom-Right): Universal Gate Set + All 6 Pairs CZ/CNOT on F1
    axD = Axes(ctx, 1030, 680, 830, 420, -0.6, 9.6, 0.88, 1.012,
               "D. F1 Universal Gate Set & All 6 Electron-Mediated CZ Pairs (Full 32D)",
               "Gate / Qubit Pair", "Full-32D Gate / Subspace Process Fidelity")
    axD.draw_grid([], [(v, f"{v:.2f}") for v in (0.88, 0.90, 0.92, 0.94, 0.96, 0.98, 1.00)])
    axD.hline(0.985, GREEN, lw=1.3, dashed=True, label="0.985 noiseless", label_x_frac=0.98)
    axD.hline(0.90, ORANGE, lw=1.3, dashed=True, label="0.90 noisy", label_x_frac=0.80)

    gs = p1["gates_summary"]
    items_d = [
        ("Rx(p/2)", min(r["nominal_fidelity_32d"] for r in gs["Rx_pi2"]), min(r["worst_corner_fidelity_32d"] for r in gs["Rx_pi2"])),
        ("Ry(p/2)", min(r["nominal_fidelity_32d"] for r in gs["Ry_pi2"]), min(r["worst_corner_fidelity_32d"] for r in gs["Ry_pi2"])),
        ("X(pi)", min(r["nominal_fidelity_32d"] for r in gs["X"]), min(r["worst_corner_fidelity_32d"] for r in gs["X"])),
        ("cX_XY8", min(r["nominal_fidelity_32d"] for r in gs["cX_XY8_16"]), min(r["worst_corner_fidelity_32d"] for r in gs["cX_XY8_16"])),
    ]
    for cz_id, cz_n in zip(p1["two_qubit_cz_ideal"], p1["two_qubit_cz_noisy_a2_e1e3"]):
        i, j = cz_id["pair"]
        items_d.append((f"CZ({i},{j})", cz_id["subspace_process_fidelity"], cz_n["noisy_process_fidelity_mean"]))

    for idx, (lbl, v_hi, v_lo) in enumerate(items_d):
        bw = 0.34
        x1, x2 = axD.px(idx - bw), axD.px(idx - 0.02)
        ctx.set_source_rgb(*BLUE)
        ctx.rectangle(x1, axD.py(max(v_hi, 0.88)), x2 - x1, axD.py(0.88) - axD.py(max(v_hi, 0.88)))
        ctx.fill()
        x3, x4 = axD.px(idx + 0.02), axD.px(idx + bw)
        col_s = TEAL if idx < 4 else ORANGE
        ctx.set_source_rgb(*col_s)
        ctx.rectangle(x3, axD.py(max(v_lo, 0.88)), x4 - x3, axD.py(0.88) - axD.py(max(v_lo, 0.88)))
        ctx.fill()
        _draw_text(ctx, axD.px(idx), axD.y0 + axD.h + 20, lbl, size=11.5, bold=True, color=TEXT, align="center")
        _draw_text(ctx, axD.px(idx + bw / 2), axD.py(max(v_lo, 0.88)) - 5, f"{v_lo:.3f}",
                   size=9.5, bold=True, color=col_s, align="center")

    axD.draw_legend([
        ("Nominal / Noiseless 32D Fidelity (worst of q0..q3 or pair)", BLUE, False),
        ("1Q/cX: Worst Static Corner (+-400 Hz x +-2%)", TEAL, False),
        ("CZ(i,j): Noisy Process F (f=1%, alpha=2, eps=1e-3)", ORANGE, False),
    ], axD.x0 + 18, axD.y0 + axD.h - 92, w_box=395)

    out_path = OUT_DIR / "fig_exp126_grape_pulses.png"
    surf.write_to_png(str(out_path))
    return out_path


# ---------------------------------------------------------------------------
# FIGURE 2: Risk R3 Closure — Interleaved XY8 vs Exp63 & XY8 vs CPMG
# ---------------------------------------------------------------------------
def build_fig2_dd_vs_exp63(data: dict) -> Path:
    W, H = 1920, 1200
    surf, ctx = _new_canvas(
        W, H,
        "Exp126 — Risk R3 Hamiltonian Closure: Interleaved XY8-GRAPE vs Exp63 Analytical Model & XY8 vs CPMG",
        "Full 32D colored 1/omega^alpha bath trajectories (n_traj=256-512) + stochastic/systematic electron pi-pulse errors | no_lab_measurement=true",
    )

    p2 = data["part2_risk_r3_interleaved_dd"]

    # Panel A (Top-Left): 32D Hahn-Echo Calibration across 4 Finalists
    axA = Axes(ctx, 95, 145, 830, 415, -0.6, 3.6, 0.0, 0.58,
               "A. Full-32D Hahn-Echo Bath Calibration W_echo(T2e) vs 1/e",
               "Exp62 Finalist Cell (T2e_ms)", "Measured 32D Echo Coherence W(T2e)")
    axA.draw_grid([], [(v, f"{v:.2f}") for v in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5)])
    inv_e = math.exp(-1.0)
    axA.hline(inv_e, RED, lw=2.0, dashed=True, label=f"1/e = {inv_e:.4f}", label_x_frac=0.68)
    # +-0.05 tolerance band
    ctx.save()
    ctx.set_source_rgba(RED[0], RED[1], RED[2], 0.08)
    ctx.rectangle(axA.x0, axA.py(inv_e + 0.05), axA.w, axA.py(inv_e - 0.05) - axA.py(inv_e + 0.05))
    ctx.fill()
    ctx.restore()

    hc = p2["hahn_echo_calibration_32d"]
    ab_keys = ["F0.5", "F1", "F2", "F4.7"]
    for idx, key in enumerate(ab_keys):
        w1 = hc[key]["alpha_1"]["coherence_W"]
        w2 = hc[key]["alpha_2"]["coherence_W"]
        t2 = hc[key]["alpha_1"]["t2e_ms"]
        bw = 0.30
        ctx.set_source_rgb(*BLUE)
        ctx.rectangle(axA.px(idx - bw), axA.py(w1), axA.px(idx - 0.02) - axA.px(idx - bw), axA.py(0.0) - axA.py(w1))
        ctx.fill()
        ctx.set_source_rgb(*ORANGE)
        ctx.rectangle(axA.px(idx + 0.02), axA.py(w2), axA.px(idx + bw) - axA.px(idx + 0.02), axA.py(0.0) - axA.py(w2))
        ctx.fill()
        _draw_text(ctx, axA.px(idx - bw / 2), axA.py(w1) + 18, f"{w1:.3f}", size=11, bold=True, color=(1.0, 1.0, 1.0), align="center")
        _draw_text(ctx, axA.px(idx + bw / 2), axA.py(w2) + 18, f"{w2:.3f}", size=11, bold=True, color=(1.0, 1.0, 1.0), align="center")
        _draw_text(ctx, axA.px(idx), axA.y0 + axA.h + 20, f"{key} ({t2:.2f} ms)", size=12, bold=True, color=TEXT, align="center")

    axA.draw_legend([
        ("alpha = 1 (1/f bath, n_traj=512)", BLUE, False),
        ("alpha = 2 (1/f^2 OU spectral diffusion, n_traj=512)", ORANGE, False),
        ("Exact target 1/e +- 0.05 band", RED, True),
    ], axA.x0 + 16, axA.y0 + 16, w_box=350)

    # Panel B (Top-Right): F1 GHZ-4 Fidelity vs N_total (32D vs Exp63 beta=1)
    sweep = p2["f1_ghz4_ndd_sweep"]
    x_pos = list(range(len(sweep)))
    n_labels = [str(r["N_total"]) for r in sweep]
    axB = Axes(ctx, 1030, 145, 830, 415, -0.3, len(sweep) - 0.7, 0.45, 1.02,
               "B. F1 (f=1%, T2e=1.27 ms) Interleaved XY8 GHZ-4 vs N_total Pulses",
               "Total Electron pi-Pulses N_total across T_tot = 2.0 ms", "GHZ-4 Fidelity Q (with 448 Spectators)")
    axB.draw_grid([(i, lbl) for i, lbl in zip(x_pos, n_labels)],
                  [(v, f"{v:.2f}") for v in (0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0)])
    axB.hline(0.85, RED, lw=1.8, dashed=True, label="Q = 0.85 threshold", label_x_frac=0.98)

    y_32d_a2 = [r["results"]["a2_e0.001"]["Q_32d"] for r in sweep]
    y_32d_a1 = [r["results"]["a1_e0.001"]["Q_32d"] for r in sweep]
    y_32d_e0 = [r["results"]["a2_e0"]["Q_32d"] for r in sweep]
    y_32d_e2 = [r["results"]["a2_e0.01"]["Q_32d"] for r in sweep]
    axB.plot_line(x_pos, y_32d_e0, GREEN, lw=2.2, dashed=True, marker="d")
    axB.plot_line(x_pos, y_32d_a2, BLUE, lw=2.8, marker="o")
    axB.plot_line(x_pos, y_32d_a1, TEAL, lw=2.5, marker="s")
    axB.plot_line(x_pos, y_32d_e2, RED, lw=2.2, dashed=True, marker="o")

    # Overlay Exp63 analytical points where defined (N=0, 8, 64, 128)
    e63_x, e63_a2, e63_a1 = [], [], []
    for i, r in enumerate(sweep):
        v2 = r["results"]["a2_e0.001"]["Q_exp63_beta1"]
        v1 = r["results"]["a1_e0.001"]["Q_exp63_beta1"]
        if v2 is not None:
            e63_x.append(i); e63_a2.append(v2); e63_a1.append(v1)
    axB.plot_line(e63_x, e63_a2, ORANGE, lw=2.0, dashed=True, marker="s")
    axB.plot_line(e63_x, e63_a1, PURPLE, lw=1.8, dashed=True, marker="d")

    axB.draw_legend([
        ("32D XY8-GRAPE: a=2, eps=0 (ideal pi)", GREEN, True),
        ("32D XY8-GRAPE: a=2, eps=1e-3 (real)", BLUE, False),
        ("32D XY8-GRAPE: a=1, eps=1e-3 (real)", TEAL, False),
        ("Exp63 analytical beta=1: a=2, eps=1e-3", ORANGE, True),
        ("Exp63 analytical beta=1: a=1, eps=1e-3", PURPLE, True),
        ("32D XY8-GRAPE: a=2, eps=1e-2 (ceiling)", RED, True),
    ], axB.x0 + 185, axB.y0 + axB.h - 154, w_box=300)

    # Panel C (Bottom-Left): All 4 Abundances (F0.5, F1, F2, F4.7) at N=64 — 32D vs Exp63
    ab_tbl = p2["abundance_dd_vs_exp63"]
    axC = Axes(ctx, 95, 680, 830, 420, -0.6, 3.6, 0.45, 1.02,
               "C. Abundance Sweep at N_total=64 (eps=1e-3): Full-32D XY8 vs Exp63",
               "Epitaxial 29Si Abundance Cell", "GHZ-4 Fidelity Q (N=64, eps=1e-3)")
    axC.draw_grid([], [(v, f"{v:.2f}") for v in (0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0)])
    axC.hline(0.85, RED, lw=1.8, dashed=True, label="Q = 0.85 gate", label_x_frac=0.98)

    for idx, key in enumerate(ab_keys):
        n64 = ab_tbl[key]["N_runs"]["N64"]
        vals = [
            (n64["Q_32d_a2_e1e3"], BLUE),
            (n64["Q_exp63_a2_e1e3"], ORANGE),
            (n64["Q_32d_a1_e1e3"], TEAL),
            (n64["Q_exp63_a1_e1e3"], PURPLE),
        ]
        bw = 0.17
        offs = [-0.28, -0.09, +0.09, +0.28]
        for (v, col), dx in zip(vals, offs):
            x1, x2 = axC.px(idx + dx - bw / 2), axC.px(idx + dx + bw / 2)
            y1, y2 = axC.py(max(v, 0.45)), axC.py(0.45)
            ctx.set_source_rgb(*col)
            ctx.rectangle(x1, y1, x2 - x1, y2 - y1)
            ctx.fill()
            _draw_text(ctx, axC.px(idx + dx), y1 - 5, f"{v:.2f}", size=9.5, bold=True, color=col, align="center")
        yld = int(round(ab_tbl[key]["yield_frac_exp59_62"] * 100))
        _draw_text(ctx, axC.px(idx), axC.y0 + axC.h + 20, f"{key} (Y={yld}%)", size=12, bold=True, color=TEXT, align="center")

    axC.draw_legend([
        ("32D XY8-GRAPE (alpha=2, true beta=3)", BLUE, False),
        ("Exp63 analytical (alpha=2, beta=1)", ORANGE, False),
        ("32D XY8-GRAPE (alpha=1, true beta=2)", TEAL, False),
        ("Exp63 analytical (alpha=1, beta=1)", PURPLE, False),
    ], axC.x0 + 18, axC.y0 + axC.h - 110, w_box=310)

    # Panel D (Bottom-Right): XY8 vs CPMG under Systematic Over-Rotation Error
    xc = p2["xy8_vs_cpmg_systematic"]["sweep"]
    dts = [r["delta_theta_rad"] * 1e3 for r in xc]  # mrad
    axD = Axes(ctx, 1030, 680, 830, 420, -4.0, 106.0, 0.0, 1.05,
               "D. Universal-Axis Protection at N=64: XY8 vs CPMG Systematic Over-Rotation",
               "Systematic Electron pi-Pulse Over-Rotation Error delta_theta (mrad)", "GHZ-4 Fidelity (f=1%, alpha=2)")
    axD.draw_grid([(v, f"{v:g}") for v in (0, 20, 40, 60, 80, 100)],
                  [(v, f"{v:.1f}") for v in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)])
    axD.hline(0.85, GRAY, lw=1.3, dashed=True, label="0.85", label_x_frac=0.98)

    axD.plot_line(dts, [r["ghz_x_xy8"] for r in xc], BLUE, lw=2.6, marker="o")
    axD.plot_line(dts, [r["ghz_y_xy8"] for r in xc], GREEN, lw=2.8, marker="s")
    axD.plot_line(dts, [r["ghz_x_cpmg"] for r in xc], ORANGE, lw=2.2, dashed=True, marker="d")
    axD.plot_line(dts, [r["ghz_y_cpmg"] for r in xc], RED, lw=2.8, marker="o")

    # Mark 2*sqrt(1e-3) = 63.25 mrad vertical guide
    px_ref = axD.px(2.0 * math.sqrt(1e-3) * 1e3)
    ctx.save()
    ctx.set_source_rgba(PURPLE[0], PURPLE[1], PURPLE[2], 0.55)
    ctx.set_line_width(1.5); ctx.set_dash([4.0, 4.0])
    ctx.move_to(px_ref, axD.y0); ctx.line_to(px_ref, axD.y0 + axD.h); ctx.stroke()
    ctx.restore()
    _draw_text(ctx, px_ref + 6, axD.y0 + 24, "eps_1pulse = 1e-3", size=11.5, bold=True, color=PURPLE, align="left")

    axD.draw_legend([
        ("XY8: GHZ_X (X-axis — self-compensated!)", BLUE, False),
        ("XY8: GHZ_Y (Y-axis — self-compensated!)", GREEN, False),
        ("CPMG: GHZ_X (collapses under interleaved RF!)", ORANGE, True),
        ("CPMG: GHZ_Y (collapses coherently!)", RED, False),
    ], axD.x0 + 18, axD.y0 + axD.h - 110, w_box=345)

    out_path = OUT_DIR / "fig_exp126_interleaved_dd_vs_exp63.png"
    surf.write_to_png(str(out_path))
    return out_path


# ---------------------------------------------------------------------------
# FIGURE 3: 16-Cell Heterogeneous Multi-Cell Atom Programmability
# ---------------------------------------------------------------------------
def build_fig3_multicell(data: dict) -> Path:
    W, H = 1920, 1200
    surf, ctx = _new_canvas(
        W, H,
        "Exp126 — 16 Heterogeneous Silicon Atom Cells Executing 5 Compiled Quantum Programs (Full 32D)",
        "Each cell drawn from independent random f=1% 29Si bath (Lie=1023/1023, unique {A_k}) -> cell-specific GRAPE/XY8 schedule | no_lab_measurement=true",
    )

    p3 = data["part3_multicell_16_programs"]
    cells = p3["cells"]
    ps = p3["program_summary"]
    pnames = ["Bell", "GHZ-4", "QFT-3", "BitFlip-3", "Grover-2"]

    # Panel A (Top-Left): Unique Random Hyperfine Spectra {A_k} across 16 Cells
    axA = Axes(ctx, 95, 145, 830, 415, -0.7, 15.7, 0.0, 2600.0,
               f"A. Spectral Heterogeneity Across 16 Certified Cells (A_k CV = {p3['A_k_cv']*100:.1f}%)",
               "Certified Atom Cell Index (0..15, Independent f=1% Clouds)", "Measured Hyperfine Coupling |A_k| (kHz)")
    axA.draw_grid([(i, str(i)) for i in range(16)],
                  [(v, f"{v:g}") for v in (0, 500, 1000, 1500, 2000, 2500)])
    q_cols = [BLUE, ORANGE, GREEN, PURPLE]
    for ci, rec in enumerate(cells):
        a_khz = sorted([abs(x) for x in rec["cell_meta"]["A_kHz"]], reverse=True)
        # vertical stem connecting min to max A_k
        ctx.set_source_rgba(GRAY[0], GRAY[1], GRAY[2], 0.45)
        ctx.set_line_width(1.8)
        ctx.move_to(axA.px(ci), axA.py(min(a_khz)))
        ctx.line_to(axA.px(ci), axA.py(max(a_khz)))
        ctx.stroke()
        for qk, aval in enumerate(a_khz):
            ctx.set_source_rgb(*q_cols[qk])
            ctx.arc(axA.px(ci), axA.py(min(aval, 2550.0)), 5.0, 0, 2 * math.pi)
            ctx.fill()
    axA.draw_legend([
        ("Qubit 0 (strongest |A_k| in K=4)", BLUE, False),
        ("Qubit 1 (2nd strongest)", ORANGE, False),
        ("Qubit 2 (3rd strongest)", GREEN, False),
        ("Qubit 3 (weakest in K=4)", PURPLE, False),
    ], axA.x0 + axA.w - 255, axA.y0 + 14, w_box=242)

    # Panel B (Top-Right): 5-Program Summary Across All 16 Cells (Ideal, Worst Corner, Noisy Mean +- Min/Max)
    axB = Axes(ctx, 1030, 145, 830, 415, -0.6, 4.6, 0.70, 1.03,
               "B. 16-Cell Logical Program Fidelity: Ideal vs Static Corner vs Noisy (f=1%)",
               "Compiled Logical Quantum Program", "Full-32D Program Fidelity (16-Cell Mean & Range)")
    axB.draw_grid([], [(v, f"{v:.2f}") for v in (0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00)])
    axB.hline(0.85, RED, lw=1.4, dashed=True, label="0.85 ref", label_x_frac=0.98)

    for idx, pname in enumerate(pnames):
        s = ps[pname]
        v_id = s["ideal_mean"]
        v_wc = s["worst_corner_mean"]
        v_n2 = s["noisy_a2_mean"]
        v_min = s["noisy_a2_min"]
        v_max = s["noisy_a2_max"]
        bw = 0.22
        for dx, val, col in [(-0.24, v_id, BLUE), (0.0, v_wc, TEAL), (+0.24, v_n2, ORANGE)]:
            x1, x2 = axB.px(idx + dx - bw / 2), axB.px(idx + dx + bw / 2)
            y1, y2 = axB.py(max(val, 0.70)), axB.py(0.70)
            ctx.set_source_rgb(*col)
            ctx.rectangle(x1, y1, x2 - x1, y2 - y1)
            ctx.fill()
        px_w = axB.px(idx + 0.24)
        ctx.set_source_rgb(*TEXT)
        ctx.set_line_width(2.0)
        ctx.move_to(px_w, axB.py(max(v_min, 0.70)))
        ctx.line_to(px_w, axB.py(min(v_max, 1.00)))
        ctx.stroke()
        for cap_y in (max(v_min, 0.70), min(v_max, 1.00)):
            ctx.move_to(px_w - 5, axB.py(cap_y))
            ctx.line_to(px_w + 5, axB.py(cap_y))
            ctx.stroke()
        _draw_text(ctx, px_w, axB.py(min(v_max, 1.00)) - 7, f"{v_n2:.3f}", size=11, bold=True, color=ORANGE, align="center")
        lbl_p = "BitFlip-3 (unenc=0)" if pname == "BitFlip-3" else pname
        _draw_text(ctx, axB.px(idx), axB.y0 + axB.h + 20, lbl_p, size=11.8, bold=True, color=TEXT, align="center")

    axB.draw_legend([
        ("Ideal Noiseless 32D (16-cell mean)", BLUE, False),
        ("Static Corner (+-400 Hz x +-2% mean)", TEAL, False),
        ("Noisy f=1%, a=2, eps=1e-3 (mean + min/max)", ORANGE, False),
    ], axB.x0 + 18, axB.y0 + axB.h - 90, w_box=340)

    # Panel C (Bottom, Full Width): 16 Cells x 5 Programs Noisy Fidelity Heatmap Matrix
    hx0, hy0, hw, hh = 150, 675, 1710, 445
    _draw_text(ctx, hx0, hy0 - 16,
               "C. Per-Cell Certified Execution Matrix — Noisy 32D Fidelity (f=1%, alpha=2, eps=1e-3, Synchronized 16x Parallel Array)",
               size=17, bold=True, color=TEXT)

    n_rows = len(pnames)
    n_cols = len(cells)
    cw = hw / n_cols
    ch = hh / n_rows

    def heat_color(val: float) -> Tuple[float, float, float]:
        # Smooth perceptual ramp: 0.75 (amber/orange) -> 0.88 (teal-green) -> 0.97 (deep emerald)
        t = max(0.0, min(1.0, (val - 0.78) / 0.19))
        if t < 0.5:
            u = t * 2.0
            r = 0.95 * (1 - u) + 0.85 * u
            g = 0.65 * (1 - u) + 0.92 * u
            b = 0.35 * (1 - u) + 0.65 * u
        else:
            u = (t - 0.5) * 2.0
            r = 0.85 * (1 - u) + 0.16 * u
            g = 0.92 * (1 - u) + 0.66 * u
            b = 0.65 * (1 - u) + 0.44 * u
        return (r, g, b)

    for r_idx, pname in enumerate(pnames):
        ry = hy0 + r_idx * ch
        _draw_text(ctx, hx0 - 14, ry + ch / 2.0 + 5, pname, size=14, bold=True, color=TEXT, align="right")
        for c_idx, rec in enumerate(cells):
            cx = hx0 + c_idx * cw
            val = rec["programs"][pname]["noisy_a2_e1e3_fidelity"]
            col = heat_color(val)
            ctx.set_source_rgb(*col)
            ctx.rectangle(cx + 1.5, ry + 1.5, cw - 3.0, ch - 3.0)
            ctx.fill()
            ctx.set_source_rgb(0.95, 0.96, 0.98)
            ctx.set_line_width(1.0)
            ctx.rectangle(cx + 1.5, ry + 1.5, cw - 3.0, ch - 3.0)
            ctx.stroke()
            txt_col = (1.0, 1.0, 1.0) if val >= 0.92 else TEXT
            _draw_text(ctx, cx + cw / 2.0, ry + ch / 2.0 + 5, f"{val:.3f}",
                       size=12.5, bold=True, color=txt_col, align="center")

    for c_idx, rec in enumerate(cells):
        cx = hx0 + c_idx * cw + cw / 2.0
        gap = rec["cell_meta"]["min_gap_kHz"]
        _draw_text(ctx, cx, hy0 + hh + 20, f"C{c_idx:02d}", size=12, bold=True, color=TEXT, align="center")
        _draw_text(ctx, cx, hy0 + hh + 36, f"{gap:.1f}k", size=10.5, color=MUTED, align="center")
    _draw_text(ctx, hx0 + hw / 2.0, hy0 + hh + 60,
               "Heterogeneous Cell ID & Minimum Bath Spectral Gap (kHz) — Inter-Cell J(1 um) = 9.5e-9 Hz | 16x Parallel Speedup",
               size=13.5, bold=True, color=AXIS, align="center")

    out_path = OUT_DIR / "fig_exp126_multicell_programs.png"
    surf.write_to_png(str(out_path))
    return out_path


def main() -> None:
    data = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    f1 = build_fig1_grape_pulses(data)
    f2 = build_fig2_dd_vs_exp63(data)
    f3 = build_fig3_multicell(data)
    print(f"Generated figures:\n  {f1}\n  {f2}\n  {f3}", flush=True)


if __name__ == "__main__":
    main()
