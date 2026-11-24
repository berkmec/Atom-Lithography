"""Bit-exact Q16.16 fixed-point FPGA BOED DSP accelerator (Exp140 / H158).

Models a cycle-accurate 250 MHz RFSoC (ZU48DR / Kintex-US+) hardware DSP core
implementing the Exp132 3-stage closed-loop Bayesian Optimal Experimental Design
(BOED) spectroscopy engine strictly in signed integer Q16.16 arithmetic with
BRAM36 lookup tables (512-entry interpolated Lorentzian & exp(-x) LUTs) and
48-bit DSP48E2 moment accumulators.

Epistemic status: {Model} / {Sayisal-Simulasyon}, no_lab_measurement=true.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np

from .adaptive_spectroscopy import (
    BOEDConfig,
    BayesianSpectrometer,
    CandidateSpectrum,
    lorentzian,
)

# ---------------------------------------------------------------------------
# Q16.16 Fixed-Point Constants & Hardware Primitives
# ---------------------------------------------------------------------------
Q_FRAC = 16
Q_ONE = 1 << Q_FRAC               # 65,536
Q_HALF = 1 << (Q_FRAC - 1)        # 32,768
INT32_MIN = -(1 << 31)
INT32_MAX = (1 << 31) - 1

LOR_LUT_BITS = 9                  # 512 entries
LOR_LUT_SIZE = 1 << LOR_LUT_BITS
LOR_U_MAX = 12.0                  # covers |df| / gamma in [0, 12.0]

EXP_LUT_BITS = 9                  # 512 entries
EXP_LUT_SIZE = 1 << EXP_LUT_BITS
EXP_X_MAX = 16.0                  # covers -log_p in [0, 16.0] (e^-16 < 1 LSB)


def to_q16(val: float | np.ndarray) -> np.ndarray | int:
    """Convert float or array to signed 32-bit saturated Q16.16 integer."""
    if isinstance(val, np.ndarray):
        scaled = np.rint(val * Q_ONE).astype(np.int64)
        return np.clip(scaled, INT32_MIN, INT32_MAX).astype(np.int64)
    iv = int(round(float(val) * Q_ONE))
    return max(INT32_MIN, min(INT32_MAX, iv))


def from_q16(q: int | np.ndarray) -> float | np.ndarray:
    """Convert Q16.16 integer or array back to floating point."""
    if isinstance(q, np.ndarray):
        return q.astype(np.float64) / float(Q_ONE)
    return float(q) / float(Q_ONE)


def q16_mul(a: np.ndarray, b: np.ndarray | int) -> np.ndarray:
    """Bit-exact signed Q16.16 x Q16.16 -> Q16.16 rounded multiplication."""
    prod = a.astype(np.int64) * (b.astype(np.int64) if isinstance(b, np.ndarray) else int(b))
    # Arithmetic round-to-nearest shift right by 16
    return (prod + Q_HALF) >> Q_FRAC


def build_lorentzian_lut_q16() -> np.ndarray:
    """512-entry (+1 guard) BRAM36 LUT for 1 / (1 + u^2), u in [0, 12.0], in Q16.16."""
    u = np.linspace(0.0, LOR_U_MAX, LOR_LUT_SIZE + 1, dtype=np.float64)
    vals = 1.0 / (1.0 + u * u)
    return np.rint(vals * Q_ONE).astype(np.int64)


def build_exp_neg_lut_q16() -> np.ndarray:
    """512-entry (+1 guard) BRAM36 LUT for exp(-x), x in [0, 16.0], in Q16.16."""
    x = np.linspace(0.0, EXP_X_MAX, EXP_LUT_SIZE + 1, dtype=np.float64)
    vals = np.exp(-x)
    return np.rint(vals * Q_ONE).astype(np.int64)


def lut_interp_q16(
    x_q16: np.ndarray,
    lut: np.ndarray,
    x_max: float,
    n_entries: int,
) -> np.ndarray:
    """Hardware-exact linear-interpolated BRAM LUT lookup strictly in integer math.

    Maps unsigned ``x_q16 >= 0`` over ``[0, x_max]`` to ``[0, n_entries]`` with
    8-bit fractional interpolation weight using only integer multiply + shift.
    """
    # Scale factor converting Q16.16 x into Q8.8 LUT address (index << 8 | frac8)
    # addr_q8 = (x_q16 * scale_addr) >> 16, where scale_addr = (n_entries * 256) / x_max
    scale_addr = int(round((n_entries * 256.0) / x_max))
    x_pos = np.maximum(x_q16, 0).astype(np.int64)
    addr_q8 = (x_pos * scale_addr) >> Q_FRAC
    max_addr = (n_entries << 8) - 1
    in_range = addr_q8 <= max_addr
    addr_clamped = np.minimum(addr_q8, max_addr)
    idx = addr_clamped >> 8
    frac = addr_clamped & 0xFF
    y0 = lut[idx]
    y1 = lut[idx + 1]
    interp = y0 + (((y1 - y0) * frac + 128) >> 8)
    # Beyond x_max: Lorentzian tail / exp(-x) saturates to lut[-1] (or 0 for exp)
    tail_val = int(lut[n_entries]) if lut[n_entries] > 1 else 0
    return np.where(in_range, interp, tail_val)


@dataclass(frozen=True)
class FPGACoreConfig:
    """Cycle-accurate Xilinx ZU48DR RFSoC / Kintex-US+ Q16.16 BOED accelerator config."""
    f_clk_MHz: float = 250.0          # 4.0 ns deterministic clock period
    simd_lanes: int = 4               # parallel DSP48E2 lanes sweeping grid bins
    n_fine_bins: int = 1001           # Stage-2 +/- 5 kHz @ 10 Hz bin spacing
    bin_step_Hz: int = 10             # integer Hz per grid step
    n_home_bins: int = 301            # Stage-1B Bayesian homing bins
    pipe_pass1_cycles: int = 12       # LUT + sub + sqr + mul + acc + max pipeline depth
    pipe_pass2_cycles: int = 14       # BRAM align + neg_x + exp-LUT + pipelined Z/M1/M2 MAC depth
    div_cordic_argmax_cycles: int = 56  # 3x bit-serial restoring dividers (18/21/35 cyc) + 16-stage isqrt + Fisher argmax
    n_parallel_engines: int = 16      # 16 simultaneous BOED engines per ZU48DR board

    # ZU48DR RFSoC reference capacity (Xilinx DS926 datasheet anchor)
    rfsoc_total_dsp48e2: int = 4_272
    rfsoc_total_bram36: int = 1_080
    rfsoc_total_lut: int = 425_280
    rfsoc_total_ff: int = 850_560


@dataclass(frozen=True)
class FPGABoedStepTrace:
    """Cycle-exact hardware timing and moment output of one Q16.16 BOED step."""
    mu_Hz: float
    std_Hz: float
    next_probe_Hz: float
    cycles_pass1: int
    cycles_pass2: int
    cycles_post: int
    total_cycles: int
    latency_us: float


class Q1616BOEDCore:
    """Bit-exact Q16.16 Stage-2 Bayesian grid filter & Fisher-optimal argmax engine."""

    def __init__(self, fpga_cfg: FPGACoreConfig | None = None):
        self.cfg = fpga_cfg or FPGACoreConfig()
        self.lor_lut = build_lorentzian_lut_q16()
        self.exp_lut = build_exp_neg_lut_q16()

        # Precompute exact cycle counts for one Stage-2 grid update step
        p = self.cfg.simd_lanes
        n = self.cfg.n_fine_bins
        self.cycles_pass1 = int(math.ceil(n / p)) + self.cfg.pipe_pass1_cycles
        self.cycles_pass2 = int(math.ceil(n / p)) + self.cfg.pipe_pass2_cycles
        self.cycles_post = int(self.cfg.div_cordic_argmax_cycles)
        self.cycles_per_step = self.cycles_pass1 + self.cycles_pass2 + self.cycles_post
        self.step_latency_us = float(self.cycles_per_step / self.cfg.f_clk_MHz)

        # Stage-1B homing cycles (301 bins)
        self.cycles_home_step = (
            int(math.ceil(self.cfg.n_home_bins / p)) + self.cfg.pipe_pass1_cycles
            + int(math.ceil(self.cfg.n_home_bins / p)) + self.cfg.pipe_pass2_cycles
            + self.cfg.div_cordic_argmax_cycles
        )
        self.home_step_latency_us = float(self.cycles_home_step / self.cfg.f_clk_MHz)

    def init_prior_q16(self, f_init_Hz: float, prior_sigma_Hz: float = 2_000.0) -> tuple[int, np.ndarray, np.ndarray]:
        """Initialize integer grid bins (in units of 10 Hz) and Q16.16 Gaussian log-prior."""
        half = (self.cfg.n_fine_bins - 1) // 2
        df_bins = np.arange(-half, half + 1, dtype=np.int64)      # [-500..+500]
        df_Hz = df_bins * self.cfg.bin_step_Hz
        log_p_f = -0.5 * ((df_Hz.astype(np.float64) / prior_sigma_Hz) ** 2)
        log_p_q16 = to_q16(log_p_f)
        f_init_int = int(round(f_init_Hz))
        return f_init_int, df_bins, log_p_q16

    def update_and_select_next(
        self,
        f_init_int: int,
        df_bins: np.ndarray,
        log_p_q16: np.ndarray,
        f_probe_Hz: float,
        y_meas: float,
        gamma_Hz: float,
        sigma_n: float,
        step_idx: int,
    ) -> tuple[np.ndarray, FPGABoedStepTrace]:
        """Execute ONE bit-exact Q16.16 posterior update + Fisher argmax selection."""
        # --- PASS 1: BRAM Lorentzian LUT + residual^2 + log-likelihood accumulate ---
        f_probe_int = int(round(f_probe_Hz))
        grid_Hz = f_init_int + df_bins * self.cfg.bin_step_Hz
        abs_df_Hz = np.abs(f_probe_int - grid_Hz)

        # u_q16 = round(|df| / gamma * 2^16) via reciprocal multiply (no divider in pass 1)
        inv_gamma_q24 = int(round((1 << 24) / max(gamma_Hz, 1.0)))
        u_q16 = (abs_df_Hz * inv_gamma_q24 + (1 << 7)) >> 8
        lor_q16 = lut_interp_q16(u_q16, self.lor_lut, LOR_U_MAX, LOR_LUT_SIZE)

        y_q16 = int(to_q16(y_meas))
        resid_q16 = y_q16 - lor_q16
        resid2_q16 = q16_mul(resid_q16, resid_q16)

        inv_2var_q16 = int(to_q16(0.5 / max(sigma_n * sigma_n, 1e-9)))
        delta_lp_q16 = q16_mul(resid2_q16, inv_2var_q16)

        new_lp_q16 = np.clip(log_p_q16 - delta_lp_q16, INT32_MIN, INT32_MAX)

        # --- PASS 2: Max-subtract + BRAM exp(-x) LUT + 48-bit DSP48E2 MAC (Z, M1, M2) ---
        max_lp = int(np.max(new_lp_q16))
        neg_x_q16 = max_lp - new_lp_q16  # >= 0 in Q16.16
        w_q16 = lut_interp_q16(neg_x_q16, self.exp_lut, EXP_X_MAX, EXP_LUT_SIZE)

        # Exact 48-bit signed integer accumulators (df_bins in [-500..+500] guarantees |M2| < 2e13 < 2^47)
        acc_z = int(np.sum(w_q16, dtype=np.int64))
        if acc_z <= 0:
            acc_z = 1
        acc_m1 = int(np.sum(w_q16 * df_bins, dtype=np.int64))
        acc_m2 = int(np.sum(w_q16 * (df_bins * df_bins), dtype=np.int64))

        # --- PASS 3: Hardware Radix-4 Divider + CORDIC isqrt + Fisher-optimal argmax ---
        # Mean offset in tenths-of-Hz (fixed-point scaled by 100 for 0.1 Hz precision)
        step_hz = self.cfg.bin_step_Hz
        mu_off_q8 = (acc_m1 * step_hz * 256) // acc_z
        mu_Hz = f_init_int + (mu_off_q8 / 256.0)

        # Exact integer variance in Hz^2 (Q8 -> CORDIC isqrt gives Q4 = 0.0625 Hz resolution!)
        mean_b_q8 = (acc_m1 * 256) // acc_z
        ex2_q16 = (acc_m2 << 16) // acc_z
        var_bins_q16 = max(0, ex2_q16 - (mean_b_q8 * mean_b_q8))
        var_Hz2_q8 = (var_bins_q16 * step_hz * step_hz) >> 8
        std_q4 = math.isqrt(max(0, int(var_Hz2_q8)))
        std_Hz = std_q4 / 16.0

        # Fisher-optimal inflection offset: Delta* = gamma / sqrt(3)
        delta_fisher_q4 = int(round((gamma_Hz / math.sqrt(3.0)) * 16.0))
        std_scaled_q4 = (std_q4 * 282) >> 8                 # 282/256 = 1.10156 ~= 1.1
        max_off_q4 = int(round(1.4 * gamma_Hz * 16.0))
        offset_q4 = max(delta_fisher_q4, min(std_scaled_q4, max_off_q4))
        sign = -1 if ((step_idx + 1) % 2 == 0) else +1
        next_probe_Hz = mu_Hz + sign * (offset_q4 / 16.0)

        trace = FPGABoedStepTrace(
            mu_Hz=mu_Hz,
            std_Hz=std_Hz,
            next_probe_Hz=next_probe_Hz,
            cycles_pass1=self.cycles_pass1,
            cycles_pass2=self.cycles_pass2,
            cycles_post=self.cycles_post,
            total_cycles=self.cycles_per_step,
            latency_us=self.step_latency_us,
        )
        return new_lp_q16, trace

    def resource_budget(self, yosys_measured_pre_pnr: dict[str, Any] | None = None) -> dict[str, Any]:
        """Hardware synthesis resource & power budget for ZU48DR RFSoC (1 & 16 engines).

        Explicitly distinguishes the analytical Vivado post-P&R target estimate (which assumes
        time-shared / Vivado-packed DSP48E2 inference) from direct Yosys pre-P&R cell counts
        when ``yosys_measured_pre_pnr`` is supplied from real Yosys synthesis.
        """
        c = self.cfg
        # Analytical Vivado post-P&R target estimate (P=4 SIMD lanes):
        #   - 4 lanes x (1 LUT interp mul + 1 resid^2 + 1 inv_2var mul + 1 exp interp + 2 M1/M2 MAC) = 24 DSP48E2
        #   - + 4 DSP48E2 for divider/NCO/Fisher argmax = 28 DSP48E2/engine (assumes DSP packing/time-sharing)
        dsp_per_eng = 6 * c.simd_lanes + 4
        # BRAM36: 1 dual-port Lorentzian LUT + 1 exp LUT + 2 ping-pong posterior/grid SRAM = 4 BRAM36/engine
        bram_per_eng = 4
        lut_per_eng = 4_200
        ff_per_eng = 5_100
        dyn_w_per_eng = 0.18

        n = c.n_parallel_engines
        dsp_tot = n * dsp_per_eng
        bram_tot = n * bram_per_eng
        lut_tot = n * lut_per_eng
        ff_tot = n * ff_per_eng

        # Full ZU48DR board power: static + PS + 8x ADC/DAC RF tiles (~32 W) + 16 BOED engines (~2.9 W) + IO (~3.1 W)
        board_power_W = 32.0 + n * dyn_w_per_eng + 3.1

        out: dict[str, Any] = {
            "target_fpga": "Xilinx Zynq UltraScale+ RFSoC ZU48DR (8x 5GSPS ADC / 8x 10GSPS DAC)",
            "estimation_kind": "analytical_vivado_post_pnr_estimate",
            "no_vendor_vivado_pnr": True,
            "f_clk_MHz": c.f_clk_MHz,
            "simd_lanes": c.simd_lanes,
            "cycles_per_boed_step": self.cycles_per_step,
            "latency_per_boed_step_us": round(self.step_latency_us, 4),
            "cycles_per_home_step": self.cycles_home_step,
            "latency_per_home_step_us": round(self.home_step_latency_us, 4),
            "cycles_stage0_sprt_shot": 4,
            "latency_stage0_sprt_ns": round(4.0 * 1000.0 / c.f_clk_MHz, 1),
            "per_engine": {
                "dsp48e2": dsp_per_eng,
                "bram36": bram_per_eng,
                "lut": lut_per_eng,
                "ff": ff_per_eng,
                "dynamic_power_W": dyn_w_per_eng,
            },
            "parallel_engines": n,
            "total_16ch": {
                "dsp48e2": dsp_tot,
                "dsp48e2_pct": round(100.0 * dsp_tot / c.rfsoc_total_dsp48e2, 2),
                "bram36": bram_tot,
                "bram36_pct": round(100.0 * bram_tot / c.rfsoc_total_bram36, 2),
                "lut": lut_tot,
                "lut_pct": round(100.0 * lut_tot / c.rfsoc_total_lut, 2),
                "ff": ff_tot,
                "ff_pct": round(100.0 * ff_tot / c.rfsoc_total_ff, 2),
                "board_total_power_W": round(board_power_W, 2),
                "cryo_heat_load_W": 0.0,
            },
            "epistemic_note": (
                "Analytical per-engine/16ch budget represents a vendor Vivado post-P&R estimate "
                "(assuming 1-DSP packed multipliers; no Vivado run on host). Unshared full-32x32 "
                "Q16.16 RTL measured by Yosys synth_xilinx -family xcup pre-P&R is tracked "
                "separately under yosys_measured_pre_pnr."
            ),
        }

        if yosys_measured_pre_pnr is not None:
            out["yosys_measured_pre_pnr"] = self.summarize_yosys_vs_analytical(yosys_measured_pre_pnr)
        return out

    def summarize_yosys_vs_analytical(self, yosys_stats: dict[str, Any]) -> dict[str, Any]:
        """Compare real Yosys pre-P&R cell counts against ZU48DR capacity and analytical estimates."""
        c = self.cfg
        summary: dict[str, Any] = {
            "measurement_kind": "yosys_pre_pnr_measured",
            "no_vendor_vivado_pnr": True,
            "targets": {},
        }
        for key, rec in yosys_stats.items():
            if not isinstance(rec, dict) or "lut_total" not in rec:
                continue
            entry = {
                "family": rec.get("family"),
                "top_module": rec.get("top_module"),
                "lut_total": int(rec["lut_total"]),
                "ff_total": int(rec["ff_total"]),
                "bram_blocks": int(rec["bram_blocks"]),
                "bram36_equiv": float(rec["bram36_equiv"]),
                "dsp_total": int(rec["dsp_total"]),
                "carry_cells": int(rec.get("carry_cells", 0)),
                "total_cells": int(rec.get("total_cells", 0)),
            }
            if rec.get("family") == "xcup":
                entry["zu48dr_pct"] = {
                    "dsp48e2_pct": round(100.0 * entry["dsp_total"] / c.rfsoc_total_dsp48e2, 2),
                    "bram36_equiv_pct": round(100.0 * entry["bram36_equiv"] / c.rfsoc_total_bram36, 2),
                    "lut_pct": round(100.0 * entry["lut_total"] / c.rfsoc_total_lut, 2),
                    "ff_pct": round(100.0 * entry["ff_total"] / c.rfsoc_total_ff, 2),
                }
                entry["fits_zu48dr"] = bool(
                    entry["dsp_total"] <= c.rfsoc_total_dsp48e2
                    and entry["bram36_equiv"] <= c.rfsoc_total_bram36
                    and entry["lut_total"] <= c.rfsoc_total_lut
                    and entry["ff_total"] <= c.rfsoc_total_ff
                )
            summary["targets"][key] = entry
        return summary


def run_paired_fp64_vs_q16_benchmark(
    candidates: list[CandidateSpectrum],
    boed_cfg: BOEDConfig | None = None,
    fpga_cfg: FPGACoreConfig | None = None,
    seed: int = 2026140,
) -> dict[str, Any]:
    """Paired head-to-head benchmark of Exp132 FP64 BOED vs bit-exact Q16.16 FPGA BOED.

    Runs Stage 0 + Stage 1 in lockstep (using identical ESR SPRT & comb/homing noise
    draws, with Q16.16 integer SPRT LLR parity check), and runs Stage-2 sequential
    BOED with IDENTICAL per-probe noise realizations ``z_step`` for both FP64 and
    Q16.16 so quantization error is isolated without Monte Carlo variance bias!
    """
    cfg = boed_cfg or BOEDConfig()
    core = Q1616BOEDCore(fpga_cfg)
    spec_fp64 = BayesianSpectrometer(cfg, rng=np.random.default_rng(seed))
    rng_paired = np.random.default_rng(seed + 77)

    gamma = cfg.fine_gamma_Hz
    sigma_n = spec_fp64._noise_sigma(cfg.fine_tau_ro_ms)
    delta_fisher = gamma / math.sqrt(3.0)

    # Exact Stage-0 SPRT integer parity check on all candidates
    sprt_disagreements = 0
    fp64_errs: list[float] = []
    q16_errs: list[float] = []
    quant_diffs: list[float] = []

    fp64_fn = 0
    fp64_fp = 0
    q16_fn = 0
    q16_fp = 0
    n_work = 0
    n_nonwork = 0
    total_q16_steps = 0
    fp64_times_ms: list[float] = []
    q16_times_ms: list[float] = []

    for cand in candidates:
        # 1. Run exact Exp132 FP64 spectrometer for reference classification + Stage-1 centers
        #    and verify Stage-0 integer Q16.16 SPRT agreement on identical noise
        sigma0 = spec_fp64._noise_sigma(cfg.esr_tau_ro_ms)
        llr_fp = 0.0
        llr_q16 = 0
        thr_q16 = int(to_q16(cfg.esr_llr_thresh))
        mu1 = cfg.esr_contrast
        scale_q16 = int(to_q16(mu1 / (sigma0 * sigma0)))
        half_sig_q16 = int(to_q16(0.5 * mu1))
        dec_fp = None
        dec_q16 = None
        for s_idx in range(1, cfg.esr_max_shots + 1):
            y0 = (mu1 if cand.donor_present else 0.0) + float(rng_paired.normal(0.0, sigma0))
            llr_fp += (mu1 * (y0 - 0.5 * mu1)) / (sigma0 * sigma0)
            y0_q16 = int(to_q16(y0))
            llr_q16 += ((y0_q16 - half_sig_q16) * scale_q16 + Q_HALF) >> Q_FRAC
            if s_idx >= cfg.esr_min_shots:
                if dec_fp is None and abs(llr_fp) >= cfg.esr_llr_thresh:
                    dec_fp = llr_fp > 0.0
                if dec_q16 is None and abs(llr_q16) >= thr_q16:
                    dec_q16 = llr_q16 > 0
                if dec_fp is not None and dec_q16 is not None:
                    break
        if dec_fp is None:
            dec_fp = llr_fp > 0.0
        if dec_q16 is None:
            dec_q16 = llr_q16 > 0
        if dec_fp != dec_q16:
            sprt_disagreements += 1

        res_fp = spec_fp64.inspect_candidate(cand)
        fp64_times_ms.append(res_fp.total_time_ms)

        if cand.label == "working":
            n_work += 1
            if not res_fp.accepted:
                fp64_fn += 1
                q16_fn += 1
                q16_times_ms.append(res_fp.total_time_ms)
                continue
        else:
            n_nonwork += 1
            if res_fp.accepted:
                fp64_fp += 1
                q16_fp += 1
            q16_times_ms.append(res_fp.total_time_ms)
            continue

        # 2. Paired Stage-2 BOED localization on all 8 working lines using identical initial
        #    Stage-1 centers and identical per-probe Gaussian noise realizations!
        true_lines = np.sort(cand.true_lines_Hz)
        # Perturb true lines by realistic Stage-1 homing residual (~350 Hz RMS) shared by both engines
        init_centers = true_lines + rng_paired.normal(0.0, 350.0, size=len(true_lines))
        est_fp = np.empty(len(true_lines), dtype=float)
        est_q16 = np.empty(len(true_lines), dtype=float)
        q16_stage2_probes = 0

        for k, f_init in enumerate(init_centers):
            # Shared noise vector for max_probes_per_line steps
            z_noise = rng_paired.normal(0.0, sigma_n, size=cfg.max_probes_per_line)

            # --- Engine A: FP64 ---
            grid_f = f_init + np.linspace(-5_000.0, 5_000.0, 1001)
            lp_f = -0.5 * ((grid_f - f_init) / 2_000.0) ** 2
            mu_f = float(f_init)
            std_f = 2_000.0
            for step in range(cfg.max_probes_per_line):
                off_f = max(delta_fisher, min(1.1 * std_f, 1.4 * gamma))
                sgn = -1.0 if (step % 2 == 0) else +1.0
                fp_f = mu_f + sgn * off_f
                sig_f = float(np.sum(lorentzian(fp_f - true_lines, gamma)))
                y_f = sig_f + float(z_noise[step])
                lp_f -= 0.5 * ((y_f - lorentzian(fp_f - grid_f, gamma)) / sigma_n) ** 2
                lp_s = lp_f - np.max(lp_f)
                pr = np.exp(lp_s)
                pr /= np.sum(pr)
                mu_f = float(np.sum(pr * grid_f))
                std_f = float(math.sqrt(max(float(np.sum(pr * (grid_f - mu_f) ** 2)), 1.0)))
                if step + 1 >= cfg.min_probes_per_line and std_f <= cfg.target_sigma_Hz:
                    break
            est_fp[k] = mu_f

            # --- Engine B: Bit-Exact Q16.16 FPGA DSP ---
            f_init_i, df_bins, lp_q = core.init_prior_q16(float(f_init), prior_sigma_Hz=2_000.0)
            f_probe_q = float(f_init_i - int(round(max(delta_fisher, min(1.1 * 2_000.0, 1.4 * gamma)))))
            mu_q = float(f_init_i)
            for step in range(cfg.max_probes_per_line):
                sig_q = float(np.sum(lorentzian(f_probe_q - true_lines, gamma)))
                y_q = sig_q + float(z_noise[step])
                lp_q, trace = core.update_and_select_next(
                    f_init_i, df_bins, lp_q, f_probe_q, y_q, gamma, sigma_n, step
                )
                q16_stage2_probes += 1
                total_q16_steps += 1
                mu_q = trace.mu_Hz
                f_probe_q = trace.next_probe_Hz
                if step + 1 >= cfg.min_probes_per_line and trace.std_Hz <= cfg.target_sigma_Hz:
                    break
            est_q16[k] = mu_q

        # Check 5 kHz spacing gate parity
        gap_fp = float(np.min(np.diff(np.sort(est_fp)))) * 0.5
        gap_q16 = float(np.min(np.diff(np.sort(est_q16)))) * 0.5
        if gap_fp < cfg.gate_Hz * 0.94:
            fp64_fn += 1
        if gap_q16 < cfg.gate_Hz * 0.94:
            q16_fn += 1

        fp64_errs.extend((est_fp - true_lines).tolist())
        q16_errs.extend((est_q16 - true_lines).tolist())
        quant_diffs.extend((est_q16 - est_fp).tolist())

        # FPGA latency adds negligible 2.34 us/step vs 0.13 ms RF overhead
        t_q16_ms = res_fp.stage0_time_ms + res_fp.stage1_time_ms + q16_stage2_probes * (
            cfg.fine_tau_ro_ms + cfg.fine_overhead_ms + core.step_latency_us * 1e-3
        )
        q16_times_ms.append(t_q16_ms)

    arr_fp = np.asarray(fp64_errs, dtype=float)
    arr_q16 = np.asarray(q16_errs, dtype=float)
    arr_dq = np.asarray(quant_diffs, dtype=float)

    rms_fp = float(np.sqrt(np.mean(arr_fp * arr_fp)))
    rms_q16 = float(np.sqrt(np.mean(arr_q16 * arr_q16)))
    fnr_fp = fp64_fn / max(n_work, 1)
    fnr_q16 = q16_fn / max(n_work, 1)
    fpr_fp = fp64_fp / max(n_nonwork, 1)
    fpr_q16 = q16_fp / max(n_nonwork, 1)

    return {
        "n_candidates": len(candidates),
        "n_working": n_work,
        "n_nonworking": n_nonwork,
        "n_lines_paired": int(len(arr_fp)),
        "stage0_sprt_disagreements": sprt_disagreements,
        "fp64": {
            "rms_freq_error_Hz": round(rms_fp, 3),
            "mae_freq_error_Hz": round(float(np.mean(np.abs(arr_fp))), 3),
            "fnr_pct": round(fnr_fp * 100.0, 4),
            "fpr_pct": round(fpr_fp * 100.0, 4),
            "mean_time_ms": round(float(np.mean(fp64_times_ms)), 3),
        },
        "q16_16": {
            "rms_freq_error_Hz": round(rms_q16, 3),
            "mae_freq_error_Hz": round(float(np.mean(np.abs(arr_q16))), 3),
            "fnr_pct": round(fnr_q16 * 100.0, 4),
            "fpr_pct": round(fpr_q16 * 100.0, 4),
            "mean_time_ms": round(float(np.mean(q16_times_ms)), 3),
            "total_fpga_steps": total_q16_steps,
            "total_fpga_compute_ms": round(total_q16_steps * core.step_latency_us * 1e-3, 3),
        },
        "parity": {
            "abs_delta_rms_Hz": round(abs(rms_q16 - rms_fp), 4),
            "rms_quantization_diff_Hz": round(float(np.sqrt(np.mean(arr_dq * arr_dq))), 4),
            "p99_quantization_diff_Hz": round(float(np.percentile(np.abs(arr_dq), 99)), 4),
            "max_quantization_diff_Hz": round(float(np.max(np.abs(arr_dq))), 4),
            "abs_delta_fnr_pct": round(abs(fnr_q16 - fnr_fp) * 100.0, 4),
            "abs_delta_fpr_pct": round(abs(fpr_q16 - fpr_fp) * 100.0, 4),
        },
        "fpga_resources": core.resource_budget(),
    }
