"""Comprehensive Real-EDA Verification & Python Bit-Exact Parity Suite for rtl/machine_ctrl/.

Executes real open-source EDA tools (ZERO mocks):
  - Verilator `--lint-only -Wall` on every module + fpga_top_machine_ctrl (0 warnings, 0 pragmas)
  - Icarus Verilog `-g2012 -Wall` + `vvp` on all 6 self-checking testbenches
  - Independent bit-exact Python Q16.16 reference check (0 LSB) for aom_pid_ctrl
  - Independent bit-exact Python Q1.15 NCO/LUT/IQ reference check (0 LSB) for cryo_mux_ddc_ctrl
  - Yosys `check -assert` + real measured pre-P&R synthesis JSON verification (xcup, xc7, ecp5)

Can also be invoked directly (`python tests/test_rtl_machine_ctrl.py --write-audit`) to
regenerate `results/stage2_rtl_verification/{yosys_{xcup,xc7,ecp5}_stat,rtl_machine_ctrl_audit}.json`
from fresh live EDA runs.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RTL_DIR = REPO_ROOT / "rtl" / "machine_ctrl"
AUDIT_DIR = REPO_ROOT / "results" / "stage2_rtl_verification"

BOED_READONLY_SRCS = (
    "../boed_fpga/boed_lut_rom.v",
    "../boed_fpga/boed_isqrt_cordic.v",
    "../boed_fpga/boed_q16_core.v",
)

CTRL_SYNTH_FILES = (
    "blanker_array_ctrl.v",
    "uhv_interlock_fsm.v",
    "aom_pid_ctrl.v",
    "spi_dac_hv_ctrl.v",
    "cryo_mux_ddc_ctrl.v",
    "uart_axi_regmap.v",
    "fpga_top_machine_ctrl.v",
)

TOP_SYNTH_SRCS = BOED_READONLY_SRCS + CTRL_SYNTH_FILES

TESTBENCH_FILES = (
    "tb_blanker_array_ctrl.v",
    "tb_uhv_interlock_fsm.v",
    "tb_aom_pid_ctrl.v",
    "tb_spi_dac_hv_ctrl.v",
    "tb_cryo_mux_ddc_ctrl.v",
    "tb_fpga_top_machine_ctrl.v",
)

# ZU48DR physical resource capacities (Xilinx DS926 Table 1)
ZU48DR_CAPACITY = {
    "lut": 425_280,
    "ff": 850_560,
    "bram36": 1_080,
    "dsp48e2": 4_272,
}


# ---------------------------------------------------------------------------
# Portable Rootless OSS CAD Suite Discovery (Zero Hardcoded Host Paths)
# ---------------------------------------------------------------------------

def resolve_eda_tool(name: str) -> Path | None:
    """Resolve an EDA binary portably from PATH or ~/.local/oss-cad-suite/bin."""
    found = shutil.which(name)
    if found:
        return Path(found).resolve()
    candidates = (
        Path.home() / ".local" / "oss-cad-suite" / "bin" / name,
        Path.home() / ".local" / "bin" / name,
    )
    for cand in candidates:
        if cand.is_file() and os.access(cand, os.X_OK):
            return cand.resolve()
    return None


def _eda_env(tool_path: Path) -> dict[str, str]:
    env = dict(os.environ)
    tool_dir = str(tool_path.parent)
    oss_bin = Path.home() / ".local" / "oss-cad-suite" / "bin"
    prefixes = [tool_dir]
    if oss_bin.is_dir() and str(oss_bin) not in prefixes:
        prefixes.append(str(oss_bin))
    env["PATH"] = os.pathsep.join(prefixes + [env.get("PATH", "")])
    return env


def _sanitize_output(text: str) -> str:
    home_str = str(Path.home())
    out = text.replace(str(REPO_ROOT), "<REPO_ROOT>")
    if home_str and home_str != "/":
        out = out.replace(home_str, "<HOME>")
    return out


def _tool_version(tool_name: str, tool_path: Path) -> str:
    flag = "-V" if tool_name in ("iverilog", "yosys") else "--version"
    if tool_name == "vvp":
        flag = "-V"
    proc = subprocess.run(
        [str(tool_path), flag],
        capture_output=True,
        text=True,
        timeout=15,
        env=_eda_env(tool_path),
        check=False,
    )
    first = (proc.stdout or proc.stderr or "").strip().splitlines()
    return _sanitize_output(first[0]) if first else "unknown"


# ---------------------------------------------------------------------------
# Static Synthesizable Verilog Hygiene Audit
# ---------------------------------------------------------------------------

def _strip_verilog_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.DOTALL)
    src = re.sub(r"//[^\n]*", "", src)
    return src


HOST_PATH_RE = re.compile(r"/home/[A-Za-z0-9_.-]+|/Users/[A-Za-z0-9_.-]+|/run/media/[A-Za-z0-9_.-]+")


def audit_static_rtl_hygiene(rtl_dir: Path = RTL_DIR) -> dict[str, Any]:
    loc_by_file: dict[str, int] = {}
    div_hits: list[str] = []
    pragma_hits: list[str] = []
    forbidden_hits: list[str] = []
    home_str = str(Path.home())
    host_path_hits: list[str] = []

    for fname in CTRL_SYNTH_FILES:
        fp = rtl_dir / fname
        raw = fp.read_text(encoding="utf-8")
        loc_by_file[fname] = len(raw.splitlines())

        if (home_str and home_str != "/" and home_str in raw) or HOST_PATH_RE.search(raw):
            host_path_hits.append(fname)
        if re.search(r"verilator\s+lint_off|synthesis\s+translate_off", raw, flags=re.IGNORECASE):
            pragma_hits.append(fname)

        stripped = _strip_verilog_comments(raw)
        # Check for combinational '/' outside timescale directives and quoted strings
        no_str = re.sub(r'"[^"]*"', '""', stripped)
        for lineno, line in enumerate(no_str.splitlines(), start=1):
            if line.strip().startswith("`timescale"):
                continue
            if "/" in line:
                div_hits.append(f"{fname}:{lineno}: {line.strip()}")
            if re.search(r"\b(real|realtime|initial)\b|\$finish|\$stop", line):
                forbidden_hits.append(f"{fname}:{lineno}: {line.strip()}")

    xdc_raw = (rtl_dir / "fpga_machine_ctrl.xdc").read_text(encoding="utf-8")
    xdc_active = "\n".join(ln for ln in xdc_raw.splitlines() if not ln.strip().startswith("#"))
    m_clk = re.search(r"create_clock\s+.*?-period\s+([0-9.]+)", xdc_active)
    clk_period_ns = float(m_clk.group(1)) if m_clk else 0.0

    return {
        "loc_by_file": loc_by_file,
        "total_ctrl_rtl_loc": sum(loc_by_file.values()),
        "combinational_div_hits": div_hits,
        "pragma_hits": pragma_hits,
        "forbidden_hits": forbidden_hits,
        "host_path_hits": host_path_hits,
        "xdc_clk_period_ns": clk_period_ns,
        "xdc_freq_MHz": round(1000.0 / clk_period_ns, 2) if clk_period_ns > 0 else 0.0,
        "xdc_has_multicycle_waiver": "set_multicycle_path" in xdc_active,
        "passed": bool(
            len(div_hits) == 0
            and len(pragma_hits) == 0
            and len(forbidden_hits) == 0
            and len(host_path_hits) == 0
            and abs(clk_period_ns - 10.0) < 1e-6
            and "set_multicycle_path" not in xdc_active
        ),
    }


# ---------------------------------------------------------------------------
# Bit-Exact Python Reference Models (0-LSB Parity Checks vs Live vvp Output)
# ---------------------------------------------------------------------------

def _s32_sat(val: int) -> int:
    if val > 0x7FFFFFFF:
        return 0x7FFFFFFF
    if val < -0x80000000:
        return -0x80000000
    return val


def _q16_mul_sat(a: int, b: int) -> int:
    return _s32_sat((a * b + 32768) >> 16)


class PyQ16AomPidRef:
    """Bit-exact standalone Python Q16.16 reference model of aom_pid_ctrl.v."""

    KP = 27525
    KI = 23593
    KD = 3277
    KAW = 42598
    MIN_GAIN = 42598
    MAX_GAIN = 91750
    SETPOINT = 65536
    BIAS = 65536
    KT_PYRO = 39

    def __init__(self) -> None:
        self.integ = 0
        self.prev_meas = self.SETPOINT
        self.d_filt = 0
        self.delay_sr = [self.BIAS] * 16

    def step(
        self,
        meas_q16: int,
        temp_meas_k: int,
        temp_ref_k: int,
        pyro_en: int,
        dead_time_taps: int,
    ) -> tuple[int, int, int, int]:
        err_p = _s32_sat(self.SETPOINT - meas_q16)
        if pyro_en and temp_ref_k > 480:
            err_t = _s32_sat((temp_ref_k - temp_meas_k) * self.KT_PYRO)
        else:
            err_t = 0
        err = _s32_sat(err_p + err_t)

        d_raw = _s32_sat(self.prev_meas - meas_q16)
        self.d_filt = (self.d_filt + d_raw) >> 1
        self.prev_meas = meas_q16

        p_term = _q16_mul_sat(self.KP, err)
        i_term = _q16_mul_sat(self.KI, err)
        d_term = _q16_mul_sat(self.KD, self.d_filt)
        u_raw = _s32_sat(_s32_sat(self.BIAS + p_term) + _s32_sat(self.integ + d_term))
        g_cmd = max(self.MIN_GAIN, min(self.MAX_GAIN, u_raw))
        sat = 1 if g_cmd != u_raw else 0
        aw_term = _q16_mul_sat(self.KAW, _s32_sat(g_cmd - u_raw))
        self.integ = _s32_sat(self.integ + _s32_sat(i_term + aw_term))

        drive = g_cmd if dead_time_taps == 0 else self.delay_sr[dead_time_taps - 1]
        self.delay_sr = [g_cmd] + self.delay_sr[:15]
        return drive, u_raw, self.integ, sat


class PyCryoMuxDdcRef:
    """Bit-exact standalone Python Q1.15 NCO/LUT/IQ reference model of cryo_mux_ddc_ctrl.v."""

    def __init__(self, n_ch: int = 8) -> None:
        self.n_ch = n_ch
        self.qsin = [
            int(round(32767.0 * math.sin((k + 0.5) * (math.pi / 2.0) / 256.0)))
            for k in range(256)
        ]
        self.phase_inc = [0] * n_ch
        self.phase_acc = [0] * n_ch
        self.rot_cos = [32767] * n_ch
        self.rot_sin = [0] * n_ch
        self.thresh = [0] * n_ch

    def _nco_sc(self, phi24: int) -> tuple[int, int]:
        quad = (phi24 >> 22) & 0x3
        qidx = (phi24 >> 14) & 0xFF
        s_mag = self.qsin[qidx]
        c_mag = self.qsin[255 - qidx]
        if quad == 0:
            return s_mag, c_mag
        if quad == 1:
            return c_mag, -s_mag
        if quad == 2:
            return -s_mag, -c_mag
        return -c_mag, s_mag

    def run_window(
        self, samples: list[int], weights: list[int], mf_en: bool
    ) -> list[tuple[int, int, int, int]]:
        acc_i = [0] * self.n_ch
        acc_q = [0] * self.n_ch
        for x_raw, w_raw in zip(samples, weights):
            if mf_en:
                x_w = (x_raw * w_raw + 16384) >> 15
                x_w = max(-32768, min(32767, x_w))
            else:
                x_w = x_raw
            for c in range(self.n_ch):
                s_val, c_val = self._nco_sc(self.phase_acc[c])
                self.phase_acc[c] = (self.phase_acc[c] + self.phase_inc[c]) & 0xFFFFFF
                mix_i = (x_w * c_val + 16384) >> 15
                mix_q = (-(x_w * s_val) + 16384) >> 15
                acc_i[c] += mix_i
                acc_q[c] += mix_q

        out: list[tuple[int, int, int, int]] = []
        for c in range(self.n_ch):
            proj = (acc_i[c] * self.rot_cos[c] + acc_q[c] * self.rot_sin[c] + 16384) >> 15
            state = 1 if proj >= self.thresh[c] else 0
            out.append((acc_i[c], acc_q[c], proj, state))
        return out


def _tb_ddc_sample_wave(idx: int) -> int:
    v1 = (((idx * 37 + 11) % 64) - 32) * 180
    v2 = (((idx * 13 + 5) % 32) - 16) * 210
    v3 = 1600 if (idx % 8) < 4 else -1600
    return v1 + v2 + v3


def _tb_ddc_mf_env(idx: int) -> int:
    return (16384 + idx * 480) if idx < 32 else (31744 - (idx - 32) * 480)


# ---------------------------------------------------------------------------
# Live Real-EDA Runners (Verilator, Icarus+vvp, Yosys check & synthesis)
# ---------------------------------------------------------------------------

def run_verilator_lint_all(rtl_dir: Path = RTL_DIR) -> dict[str, Any]:
    verilator_bin = resolve_eda_tool("verilator")
    assert verilator_bin is not None, "verilator not found in PATH or ~/.local/oss-cad-suite/bin"
    env = _eda_env(verilator_bin)

    targets: list[tuple[str, list[str], tuple[str, ...]]] = [
        ("blanker_array_ctrl", [], ("blanker_array_ctrl.v",)),
        ("uhv_interlock_fsm", [], ("uhv_interlock_fsm.v",)),
        ("aom_pid_ctrl", [], ("aom_pid_ctrl.v",)),
        ("spi_dac_hv_ctrl", [], ("spi_dac_hv_ctrl.v",)),
        ("cryo_mux_ddc_ctrl", [], ("cryo_mux_ddc_ctrl.v",)),
        ("cryo_mux_ddc_ctrl_32ch", ["-GN_CH=32"], ("cryo_mux_ddc_ctrl.v",)),
        ("uart_axi_regmap", [], ("uart_axi_regmap.v",)),
        ("fpga_top_machine_ctrl", [], TOP_SYNTH_SRCS),
        ("fpga_top_carrier_wrap", [], TOP_SYNTH_SRCS + ("fpga_top_carrier_wrap.v",)),
    ]

    results: dict[str, Any] = {}
    all_passed = True
    for label, extra_flags, files in targets:
        top_mod = "cryo_mux_ddc_ctrl" if label == "cryo_mux_ddc_ctrl_32ch" else label
        cmd = [str(verilator_bin), "--lint-only", "-Wall", *extra_flags, "--top-module", top_mod, *files]
        proc = subprocess.run(
            cmd, cwd=str(rtl_dir), capture_output=True, text=True, timeout=60, env=env, check=False
        )
        combined = _sanitize_output((proc.stdout + "\n" + proc.stderr).strip())
        warns = [ln for ln in combined.splitlines() if "%Warning" in ln]
        errs = [ln for ln in combined.splitlines() if "%Error" in ln]
        ok = proc.returncode == 0 and len(warns) == 0 and len(errs) == 0
        all_passed = all_passed and ok
        results[label] = {
            "returncode": proc.returncode,
            "warning_count": len(warns),
            "error_count": len(errs),
            "warnings": warns[:10],
            "errors": errs[:10],
            "passed": ok,
        }

    return {
        "tool": "verilator",
        "version": _tool_version("verilator", verilator_bin),
        "flags": "--lint-only -Wall",
        "targets": results,
        "all_passed": all_passed,
    }


def run_iverilog_all_testbenches(rtl_dir: Path = RTL_DIR) -> dict[str, Any]:
    iverilog_bin = resolve_eda_tool("iverilog")
    vvp_bin = resolve_eda_tool("vvp")
    assert iverilog_bin is not None and vvp_bin is not None, "iverilog/vvp not found"
    env = _eda_env(iverilog_bin)

    tb_specs: list[tuple[str, tuple[str, ...]]] = [
        ("tb_blanker_array_ctrl", ("blanker_array_ctrl.v", "tb_blanker_array_ctrl.v")),
        ("tb_uhv_interlock_fsm", ("uhv_interlock_fsm.v", "tb_uhv_interlock_fsm.v")),
        ("tb_aom_pid_ctrl", ("aom_pid_ctrl.v", "tb_aom_pid_ctrl.v")),
        ("tb_spi_dac_hv_ctrl", ("spi_dac_hv_ctrl.v", "tb_spi_dac_hv_ctrl.v")),
        ("tb_cryo_mux_ddc_ctrl", ("cryo_mux_ddc_ctrl.v", "tb_cryo_mux_ddc_ctrl.v")),
        ("tb_fpga_top_machine_ctrl", TOP_SYNTH_SRCS + ("tb_fpga_top_machine_ctrl.v",)),
    ]

    tb_results: dict[str, Any] = {}
    all_passed = True

    with tempfile.TemporaryDirectory(prefix="stage2_rtl_sim_") as tmpdir:
        tmp = Path(tmpdir)
        for tb_name, files in tb_specs:
            sim_bin = tmp / f"sim_{tb_name}"
            comp = subprocess.run(
                [str(iverilog_bin), "-g2012", "-Wall", "-o", str(sim_bin), *files],
                cwd=str(rtl_dir),
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
                check=False,
            )
            comp_txt = _sanitize_output((comp.stdout + "\n" + comp.stderr).strip())
            comp_warns = [ln for ln in comp_txt.splitlines() if "warning:" in ln.lower()]
            if comp.returncode != 0:
                raise RuntimeError(f"iverilog compile failed for {tb_name}:\n{comp_txt}")

            sim = subprocess.run(
                [str(vvp_bin), str(sim_bin)],
                cwd=str(rtl_dir),
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
                check=False,
            )
            sim_txt = _sanitize_output((sim.stdout + "\n" + sim.stderr).strip())
            pass_marker = f"PASS: {tb_name}" in sim_txt
            rec: dict[str, Any] = {
                "compile_returncode": comp.returncode,
                "compile_warning_count": len(comp_warns),
                "vvp_returncode": sim.returncode,
                "pass_marker": pass_marker,
                "raw_stdout": sim_txt,
            }

            # Parse summary metrics & run standalone Python bit-exact checks
            if tb_name == "tb_blanker_array_ctrl":
                m = re.search(
                    r"BLANKER_SUMMARY\s+errors=(\d+)\s+frames_verified=(\d+)\s+bits_per_frame=(\d+)\s+trip_latency_ns=(\d+)",
                    sim_txt,
                )
                assert m is not None, f"Missing BLANKER_SUMMARY:\n{sim_txt}"
                rec.update(
                    errors=int(m.group(1)),
                    frames_verified=int(m.group(2)),
                    bits_per_frame=int(m.group(3)),
                    trip_latency_ns=int(m.group(4)),
                )
                rec["passed"] = bool(
                    pass_marker and comp.returncode == 0 and len(comp_warns) == 0
                    and sim.returncode == 0 and rec["errors"] == 0
                    and rec["bits_per_frame"] == 1024 and rec["trip_latency_ns"] <= 20
                )

            elif tb_name == "tb_uhv_interlock_fsm":
                m = re.search(
                    r"INTERLOCK_SUMMARY\s+errors=(\d+)\s+channels_tested=(\d+)\s+discrep_ok=(\d+)\s+wdt_ok=(\d+)\s+max_trip_ns=(\d+)\s+trips=(\d+)\s+certified=(\d+)\s+design_only=(\d+)",
                    sim_txt,
                )
                assert m is not None, f"Missing INTERLOCK_SUMMARY:\n{sim_txt}"
                rec.update(
                    errors=int(m.group(1)),
                    channels_tested=int(m.group(2)),
                    discrep_ok=bool(int(m.group(3))),
                    wdt_ok=bool(int(m.group(4))),
                    max_trip_ns=int(m.group(5)),
                    trips=int(m.group(6)),
                    status_certified=int(m.group(7)),
                    status_design_only=int(m.group(8)),
                )
                rec["passed"] = bool(
                    pass_marker and len(comp_warns) == 0 and sim.returncode == 0
                    and rec["errors"] == 0 and rec["channels_tested"] == 16
                    and rec["discrep_ok"] and rec["wdt_ok"]
                    and rec["max_trip_ns"] <= 30
                    and rec["status_certified"] == 0 and rec["status_design_only"] == 1
                )

            elif tb_name == "tb_aom_pid_ctrl":
                m = re.search(
                    r"AOM_PID_SUMMARY\s+errors=(\d+)\s+steps=(\d+)\s+max_lsb_err=(\d+)\s+sat_hi=(\d+)\s+sat_lo=(\d+)\s+overtemp_1687k_ok=(\d+)\s+interlock_ok=(\d+)",
                    sim_txt,
                )
                assert m is not None, f"Missing AOM_PID_SUMMARY:\n{sim_txt}"
                # Independent Python Q16.16 0-LSB parity check over every PID_TRACE line!
                py_pid = PyQ16AomPidRef()
                py_max_err = 0
                trace_rows = re.findall(
                    r"PID_TRACE\s+step=(\d+)\s+meas=(-?\d+)\s+tmeas=(\d+)\s+tref=(\d+)\s+pyro=(\d+)\s+taps=(\d+)\s+drive=(-?\d+)\s+uraw=(-?\d+)\s+integ=(-?\d+)\s+sat=(\d+)",
                    sim_txt,
                )
                assert len(trace_rows) == 24, f"Expected 24 PID_TRACE lines, got {len(trace_rows)}"
                for row in trace_rows:
                    _step, meas, tmeas, tref, pyro, taps, drv, uraw, integ, sat = (int(x) for x in row)
                    r_drv, r_uraw, r_integ, r_sat = py_pid.step(meas, tmeas, tref, pyro, taps)
                    py_max_err = max(
                        py_max_err,
                        abs(drv - r_drv),
                        abs(uraw - r_uraw),
                        abs(integ - r_integ),
                        abs(sat - r_sat),
                    )
                rec.update(
                    errors=int(m.group(1)),
                    steps=int(m.group(2)),
                    tb_max_lsb_err=int(m.group(3)),
                    python_ref_max_lsb_err=py_max_err,
                    sat_hi=int(m.group(4)),
                    sat_lo=int(m.group(5)),
                    overtemp_1687k_ok=bool(int(m.group(6))),
                    interlock_ok=bool(int(m.group(7))),
                )
                rec["passed"] = bool(
                    pass_marker and len(comp_warns) == 0 and sim.returncode == 0
                    and rec["errors"] == 0 and rec["tb_max_lsb_err"] == 0
                    and py_max_err == 0 and rec["overtemp_1687k_ok"] and rec["interlock_ok"]
                )

            elif tb_name == "tb_spi_dac_hv_ctrl":
                m = re.search(
                    r"SPI_DAC_SUMMARY\s+errors=(\d+)\s+channels=(\d+)\s+selective_ok=(\d+)\s+full_sync_ldac_ok=(\d+)\s+hv_safe_clamp_zero_ok=(\d+)",
                    sim_txt,
                )
                assert m is not None, f"Missing SPI_DAC_SUMMARY:\n{sim_txt}"
                rec.update(
                    errors=int(m.group(1)),
                    channels=int(m.group(2)),
                    selective_ok=bool(int(m.group(3))),
                    full_sync_ldac_ok=bool(int(m.group(4))),
                    hv_safe_clamp_zero_ok=bool(int(m.group(5))),
                )
                rec["passed"] = bool(
                    pass_marker and len(comp_warns) == 0 and sim.returncode == 0
                    and rec["errors"] == 0 and rec["channels"] == 8
                    and rec["selective_ok"] and rec["full_sync_ldac_ok"] and rec["hv_safe_clamp_zero_ok"]
                )

            elif tb_name == "tb_cryo_mux_ddc_ctrl":
                m = re.search(
                    r"DDC_SUMMARY\s+errors=(\d+)\s+win8_cnt=(\d+)\s+mask8=([0-9a-fA-F]+)\s+tones32_beats=(\d+)\s+mask32=([0-9a-fA-F]+)",
                    sim_txt,
                )
                assert m is not None, f"Missing DDC_SUMMARY:\n{sim_txt}"
                # Independent Python Q1.15 NCO/LUT/IQ/Discriminator bit-exact check!
                py_ddc = PyCryoMuxDdcRef(n_ch=8)
                cfg_table = [
                    (0x040000, 32767, 0, 0),
                    (0x080000, 23170, 23170, -500),
                    (0x0C0000, 0, 32767, 200),
                    (0x100000, -23170, 23170, 0),
                    (0x140000, -32767, 0, -1000),
                    (0x180000, 28377, -16384, 100),
                    (0x1C0000, 16384, 28377, -200),
                    (0x200000, 32767, -8192, 0),
                ]
                for c, (pi, rc, rs, th) in enumerate(cfg_table):
                    py_ddc.phase_inc[c] = pi
                    py_ddc.rot_cos[c] = rc
                    py_ddc.rot_sin[c] = rs
                    py_ddc.thresh[c] = th

                w0_ref = py_ddc.run_window(
                    [_tb_ddc_sample_wave(n) for n in range(64)],
                    [_tb_ddc_mf_env(n) for n in range(64)],
                    mf_en=False,
                )
                w1_ref = py_ddc.run_window(
                    [_tb_ddc_sample_wave(n + 17) for n in range(64)],
                    [_tb_ddc_mf_env(n) for n in range(64)],
                    mf_en=True,
                )
                refs = {0: w0_ref, 1: w1_ref}

                ddc_rows = re.findall(
                    r"DDC8_TRACE\s+win=(\d+)\s+mf=(\d+)\s+ch=(\d+)\s+res_i=(-?\d+)\s+res_q=(-?\d+)\s+proj=(-?\d+)\s+state=(\d+)",
                    sim_txt,
                )
                assert len(ddc_rows) == 16, f"Expected 16 DDC8_TRACE lines, got {len(ddc_rows)}"
                py_ddc_max_err = 0
                for row in ddc_rows:
                    w_i, _mf, ch_i, ri, rq, rp, st = (int(x) for x in row)
                    r_i, r_q, r_p, r_s = refs[w_i][ch_i]
                    py_ddc_max_err = max(
                        py_ddc_max_err,
                        abs(ri - r_i),
                        abs(rq - r_q),
                        abs(rp - r_p),
                        abs(st - r_s),
                    )
                rec.update(
                    errors=int(m.group(1)),
                    win8_cnt=int(m.group(2)),
                    mask8_hex=m.group(3).lower(),
                    tones32_beats=int(m.group(4)),
                    mask32_hex=m.group(5).lower(),
                    python_ref_max_lsb_err=py_ddc_max_err,
                )
                rec["passed"] = bool(
                    pass_marker and len(comp_warns) == 0 and sim.returncode == 0
                    and rec["errors"] == 0 and py_ddc_max_err == 0
                    and rec["tones32_beats"] == 32 and rec["mask32_hex"] == "aaaaaaaa"
                )

            elif tb_name == "tb_fpga_top_machine_ctrl":
                m = re.search(
                    r"TOP_SUMMARY\s+errors=(\d+)\s+uart_ok=(\d+)\s+sw_bypass_rejected=(\d+)\s+cfg_lock_ok=(\d+)\s+"
                    r"boed_cycles=(\d+)\s+boed_mu=(-?\d+)\s+boed_std=(\d+)\s+boed_next=(-?\d+)\s+boed_0lsb_ok=(\d+)\s+"
                    r"ddc_autofeed_ok=(\d+)\s+simultaneous_trip_ns=(\d+)\s+spi_zero_clamp_ok=(\d+)",
                    sim_txt,
                )
                assert m is not None, f"Missing TOP_SUMMARY:\n{sim_txt}"
                rec.update(
                    errors=int(m.group(1)),
                    uart_ok=bool(int(m.group(2))),
                    sw_bypass_rejected=bool(int(m.group(3))),
                    cfg_lock_ok=bool(int(m.group(4))),
                    boed_cycles=int(m.group(5)),
                    boed_mu_off_q8=int(m.group(6)),
                    boed_std_q4=int(m.group(7)),
                    boed_next_probe_q8=int(m.group(8)),
                    boed_0lsb_ok=bool(int(m.group(9))),
                    ddc_autofeed_ok=bool(int(m.group(10))),
                    simultaneous_trip_ns=int(m.group(11)),
                    spi_zero_clamp_ok=bool(int(m.group(12))),
                )
                rec["passed"] = bool(
                    pass_marker and len(comp_warns) == 0 and sim.returncode == 0
                    and rec["errors"] == 0 and rec["uart_ok"]
                    and rec["sw_bypass_rejected"] and rec["cfg_lock_ok"]
                    and rec["boed_cycles"] == 584
                    and rec["boed_mu_off_q8"] == -171749
                    and rec["boed_std_q4"] == 5711
                    and rec["boed_next_probe_q8"] == 5611
                    and rec["boed_0lsb_ok"]
                    and rec["ddc_autofeed_ok"]
                    and rec["simultaneous_trip_ns"] <= 30 and rec["spi_zero_clamp_ok"]
                )

            # Strip verbose raw stdout from saved JSON summaries
            rec.pop("raw_stdout", None)
            all_passed = all_passed and rec["passed"]
            tb_results[tb_name] = rec

    return {
        "simulator": "iverilog -g2012 -Wall + vvp",
        "iverilog_version": _tool_version("iverilog", iverilog_bin),
        "testbenches": tb_results,
        "all_passed": all_passed,
    }


def _extract_yosys_metrics(stat_json: dict[str, Any], family: str, top_module: str) -> dict[str, Any]:
    design = stat_json.get("design", {})
    cells = design.get("num_cells_by_type", {})

    if family in ("xcup", "xc7"):
        lut_pure = sum(int(cells.get(k, 0)) for k in ("LUT1", "LUT2", "LUT3", "LUT4", "LUT5", "LUT6", "INV"))
        srl_total = sum(int(cells.get(k, 0)) for k in ("SRL16E", "SRLC32E"))
        lut_total = lut_pure + srl_total
        ff_total = sum(int(cells.get(k, 0)) for k in ("FDRE", "FDSE", "FDCE", "FDPE"))
        carry_cells = sum(int(cells.get(k, 0)) for k in ("CARRY4", "CARRY8"))
        dsp_key = "DSP48E2" if family == "xcup" else "DSP48E1"
        ramb18_key = "RAMB18E2" if family == "xcup" else "RAMB18E1"
        ramb36_key = "RAMB36E2" if family == "xcup" else "RAMB36E1"
        dsp_total = int(cells.get(dsp_key, 0))
        ramb18 = int(cells.get(ramb18_key, 0))
        ramb36 = int(cells.get(ramb36_key, 0))
        bram_blocks = ramb18 + ramb36
        bram36_equiv = round(ramb36 + 0.5 * ramb18, 2)
    else:  # ecp5
        lut_pure = int(cells.get("LUT4", 0))
        srl_total = 0
        lut_total = lut_pure
        ff_total = int(cells.get("TRELLIS_FF", 0))
        carry_cells = int(cells.get("CCU2C", 0))
        dsp_total = int(cells.get("MULT18X18D", 0))
        bram_blocks = int(cells.get("DP16KD", 0))
        bram36_equiv = round(0.5 * bram_blocks, 2)

    submod_wrappers = {
        "blanker_array_ctrl",
        "uhv_interlock_fsm",
        "aom_pid_ctrl",
        "spi_dac_hv_ctrl",
        "cryo_mux_ddc_ctrl",
        "uart_axi_regmap",
        "boed_q16_core",
        "boed_isqrt_cordic",
        "boed_lut_rom",
    }
    prim_cells = {
        k: int(v) for k, v in sorted(cells.items())
        if not k.startswith("$") and k not in submod_wrappers
    }
    out: dict[str, Any] = {
        "family": family,
        "top_module": top_module,
        "measurement_kind": "yosys_pre_pnr_measured",
        "no_vendor_vivado_pnr": True,
        "no_lab_measurement_rtl": True,
        "iec61508_certified": False,
        "lut_pure": lut_pure,
        "srl_total": srl_total,
        "lut_total": lut_total,
        "ff_total": ff_total,
        "bram_blocks": bram_blocks,
        "bram36_equiv": bram36_equiv,
        "dsp_total": dsp_total,
        "carry_cells": carry_cells,
        "total_cells": sum(prim_cells.values()),
        "cells_by_type": prim_cells,
    }
    if family == "xcup":
        out["zu48dr_pct"] = {
            "lut_pct": round(100.0 * lut_total / ZU48DR_CAPACITY["lut"], 2),
            "ff_pct": round(100.0 * ff_total / ZU48DR_CAPACITY["ff"], 2),
            "bram36_equiv_pct": round(100.0 * bram36_equiv / ZU48DR_CAPACITY["bram36"], 2),
            "dsp48e2_pct": round(100.0 * dsp_total / ZU48DR_CAPACITY["dsp48e2"], 2),
        }
        out["fits_zu48dr"] = all(v < 100.0 for v in out["zu48dr_pct"].values())
    return out


def run_yosys_check_assert(rtl_dir: Path = RTL_DIR) -> dict[str, Any]:
    yosys_bin = resolve_eda_tool("yosys")
    assert yosys_bin is not None, "yosys not found in PATH or ~/.local/oss-cad-suite/bin"
    script = (
        f"read_verilog {' '.join(TOP_SYNTH_SRCS)}; "
        "hierarchy -check -top fpga_top_machine_ctrl; proc; opt; check -assert"
    )
    proc = subprocess.run(
        [str(yosys_bin), "-q", "-p", script],
        cwd=str(rtl_dir),
        capture_output=True,
        text=True,
        timeout=90,
        env=_eda_env(yosys_bin),
        check=False,
    )
    return {
        "tool": "yosys",
        "version": _tool_version("yosys", yosys_bin),
        "returncode": proc.returncode,
        "passed": proc.returncode == 0,
    }


def _run_yosys_family(yosys_bin: Path, rtl_dir: Path, family: str) -> tuple[str, dict[str, Any]]:
    synth_cmd = (
        f"synth_xilinx -family {family} -top fpga_top_machine_ctrl"
        if family in ("xcup", "xc7")
        else "synth_ecp5 -top fpga_top_machine_ctrl"
    )
    with tempfile.TemporaryDirectory(prefix=f"yosys_mc_{family}_") as tmpdir:
        out_json = Path(tmpdir) / f"{family}.json"
        script = f"read_verilog {' '.join(TOP_SYNTH_SRCS)}; {synth_cmd}; tee -q -o {out_json} stat -json"
        proc = subprocess.run(
            [str(yosys_bin), "-q", "-p", script],
            cwd=str(rtl_dir),
            capture_output=True,
            text=True,
            timeout=300,
            env=_eda_env(yosys_bin),
            check=False,
        )
        if proc.returncode != 0 or not out_json.is_file():
            raise RuntimeError(
                f"Yosys failed on {family}:\n{_sanitize_output(proc.stdout + proc.stderr)}"
            )
        raw = json.loads(out_json.read_text(encoding="utf-8"))
        metrics = _extract_yosys_metrics(raw, family, "fpga_top_machine_ctrl")
        metrics["synth_command"] = synth_cmd
        metrics["returncode"] = proc.returncode
        metrics["passed"] = bool(
            proc.returncode == 0
            and metrics["lut_total"] > 0
            and metrics["ff_total"] > 0
            and metrics["bram_blocks"] >= 12
            and metrics["dsp_total"] >= 100
        )
        return family, metrics


def generate_stage2_rtl_audit(write_outputs: bool = True) -> dict[str, Any]:
    """Run complete real-EDA sign-off suite and optionally write Stage-2 audit JSONs."""
    static_audit = audit_static_rtl_hygiene(RTL_DIR)
    verilator_res = run_verilator_lint_all(RTL_DIR)
    iverilog_res = run_iverilog_all_testbenches(RTL_DIR)
    yosys_chk = run_yosys_check_assert(RTL_DIR)

    yosys_bin = resolve_eda_tool("yosys")
    assert yosys_bin is not None
    yosys_targets: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = [pool.submit(_run_yosys_family, yosys_bin, RTL_DIR, fam) for fam in ("xcup", "xc7", "ecp5")]
        for fut in futs:
            fam, rec = fut.result()
            yosys_targets[fam] = rec

    audit = {
        "schema_version": "stage2_rtl_machine_ctrl_audit_v1",
        "top_module": "fpga_top_machine_ctrl",
        "clock_MHz": 100.0,
        "measurement_kind": "real_open_source_eda_verified_pre_pnr",
        "no_external_eda_sim": False,
        "no_vendor_vivado_pnr": True,
        "no_lab_measurement_rtl": True,
        "iec61508_certified": False,
        "semi_s2_certified": False,
        "certification_status": "DESIGN_ONLY_NOT_CERTIFIED",
        "bom_traceability": {
            "blanker_array_ctrl.v": ["S2.2-01", "S2.4-01", "S2.4-02", "S3.3-01", "S3.3-02"],
            "uhv_interlock_fsm.v": [
                "S5.5-04", "S7.4-04", "S7.SAFETY-01", "S7.SAFETY-02",
                "S7.SAFETY-03", "S7.SAFETY-04", "S7.SAFETY-05", "S7.SAFETY-06",
            ],
            "aom_pid_ctrl.v": ["S5.3-03", "S5.5-01", "S5.5-03", "S1.4-03"],
            "spi_dac_hv_ctrl.v": ["S1.2-03", "S1.3-03", "S2.3-04", "S3.2-02", "S6.7-02", "S6.10-03", "S6.10-04"],
            "cryo_mux_ddc_ctrl.v": ["S6.6-06", "S6.11-01"],
            "uart_axi_regmap.v": ["S3.3-01", "S3.3-04", "S7.2-02", "S8.4-02"],
            "fpga_top_machine_ctrl.v": ["S3.3-01", "S3.3-04", "S6.11-01", "S7.2-02", "S8.3-03", "S8.4-02"],
        },
        "static_hygiene": static_audit,
        "verilator_lint": verilator_res,
        "iverilog_simulation": iverilog_res,
        "yosys_check_assert": yosys_chk,
        "yosys_synthesis": {
            "tool": "yosys",
            "version": yosys_chk["version"],
            "targets": yosys_targets,
            "all_passed": all(v["passed"] for v in yosys_targets.values()),
        },
        "all_gates_passed": bool(
            static_audit["passed"]
            and verilator_res["all_passed"]
            and iverilog_res["all_passed"]
            and yosys_chk["passed"]
            and all(v["passed"] for v in yosys_targets.values())
        ),
    }

    if write_outputs:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        for fam in ("xcup", "xc7", "ecp5"):
            (AUDIT_DIR / f"yosys_{fam}_stat.json").write_text(
                json.dumps(yosys_targets[fam], indent=2) + "\n", encoding="utf-8"
            )
        (AUDIT_DIR / "rtl_machine_ctrl_audit.json").write_text(
            json.dumps(audit, indent=2) + "\n", encoding="utf-8"
        )

    return audit


# ---------------------------------------------------------------------------
# Pytest Verification Suite
# ---------------------------------------------------------------------------

def test_all_stage2_rtl_and_audit_files_exist_with_zero_host_path_leaks():
    expected_rtl = list(CTRL_SYNTH_FILES) + list(TESTBENCH_FILES) + [
        "fpga_machine_ctrl.xdc",
        "Makefile",
        "REGMAP.md",
        "README.md",
    ]
    for fname in expected_rtl:
        fp = RTL_DIR / fname
        assert fp.is_file() and fp.stat().st_size > 0, f"Missing or empty RTL deliverable: {fname}"

    expected_audit = [
        "rtl_machine_ctrl_audit.json",
        "yosys_xcup_stat.json",
        "yosys_xc7_stat.json",
        "yosys_ecp5_stat.json",
    ]
    for fname in expected_audit:
        fp = AUDIT_DIR / fname
        assert fp.is_file() and fp.stat().st_size > 0, f"Missing or empty audit artifact: {fname}"

    # Verify zero hardcoded user home/host paths anywhere in deliverables
    home_str = str(Path.home())
    for fp in list(RTL_DIR.iterdir()) + list(AUDIT_DIR.iterdir()):
        if fp.is_file():
            txt = fp.read_text(encoding="utf-8")
            if home_str and home_str != "/":
                assert home_str not in txt, f"Hardcoded host path found in {fp.name}!"
            assert not HOST_PATH_RE.search(txt), f"Hardcoded host path regex hit in {fp.name}!"

    # Regression check for [RTL-SAFE-01]: Channel B reset strictly physical il_hw_reset_b (no SW bypass)
    top_src = (RTL_DIR / "fpga_top_machine_ctrl.v").read_text(encoding="utf-8")
    assert "p_il_reset_b" not in top_src, "Single-channel SW bypass p_il_reset_b must not exist!"
    assert re.search(r"\.reset_cmd_b\s*\(\s*il_hw_reset_b\s*\)", top_src), (
        "uhv_interlock_fsm.reset_cmd_b must connect directly to physical il_hw_reset_b!"
    )
    assert "r_il_cfg_locked" in top_src and "il_cfg_write_en" in top_src, (
        "Safety-config runtime write lock must exist in fpga_top_machine_ctrl.v!"
    )


def test_static_synthesizable_rtl_hygiene_zero_div_zero_pragmas_clean_xdc():
    hyg = audit_static_rtl_hygiene(RTL_DIR)
    assert hyg["passed"] is True, f"Static hygiene failed: {hyg}"
    assert hyg["combinational_div_hits"] == []
    assert hyg["pragma_hits"] == []
    assert hyg["forbidden_hits"] == []
    assert hyg["host_path_hits"] == []
    assert hyg["xdc_clk_period_ns"] == 10.0
    assert hyg["xdc_freq_MHz"] == 100.0
    assert hyg["xdc_has_multicycle_waiver"] is False


def test_live_verilator_lint_wall_zero_warnings_all_modules_and_top():
    res = run_verilator_lint_all(RTL_DIR)
    assert res["all_passed"] is True
    assert len(res["targets"]) == 9
    for mod, rec in res["targets"].items():
        assert rec["passed"] is True, f"Verilator lint failed for {mod}: {rec}"
        assert rec["returncode"] == 0
        assert rec["warning_count"] == 0, f"Verilator warnings on {mod}: {rec['warnings']}"
        assert rec["error_count"] == 0, f"Verilator errors on {mod}: {rec['errors']}"


def test_live_iverilog_vvp_all_6_testbenches_and_bit_exact_python_parity():
    res = run_iverilog_all_testbenches(RTL_DIR)
    assert res["all_passed"] is True
    tbs = res["testbenches"]
    assert len(tbs) == 6

    # 1. Blanker Array Controller
    b = tbs["tb_blanker_array_ctrl"]
    assert b["passed"] is True and b["errors"] == 0
    assert b["frames_verified"] == 2 and b["bits_per_frame"] == 1024
    assert b["trip_latency_ns"] <= 20  # <= 2 clocks @ 100 MHz, strictly < 1000 ns

    # 2. UHV 1oo2D Safety Interlock FSM (2-FF CDC + 1-cycle FSM latch <= 30 ns, glitch-free!)
    il = tbs["tb_uhv_interlock_fsm"]
    assert il["passed"] is True and il["errors"] == 0
    assert il["channels_tested"] == 16
    assert il["discrep_ok"] is True and il["wdt_ok"] is True
    assert il["max_trip_ns"] <= 30
    assert il["status_certified"] == 0 and il["status_design_only"] == 1

    # 3. AOM Q16.16 PID Controller (bit-exact 0-LSB vs Python reference)
    pid = tbs["tb_aom_pid_ctrl"]
    assert pid["passed"] is True and pid["errors"] == 0
    assert pid["steps"] == 24
    assert pid["tb_max_lsb_err"] == 0
    assert pid["python_ref_max_lsb_err"] == 0
    assert pid["sat_hi"] > 0 and pid["sat_lo"] > 0
    assert pid["overtemp_1687k_ok"] is True and pid["interlock_ok"] is True

    # 4. SPI DAC HV 8-ch 20-bit Controller
    spi = tbs["tb_spi_dac_hv_ctrl"]
    assert spi["passed"] is True and spi["errors"] == 0
    assert spi["channels"] == 8
    assert spi["selective_ok"] is True and spi["full_sync_ldac_ok"] is True
    assert spi["hv_safe_clamp_zero_ok"] is True

    # 5. Cryo MUX Multi-Tone DDC (bit-exact 0-LSB vs Python Q1.15 reference + 32-tone TDM)
    ddc = tbs["tb_cryo_mux_ddc_ctrl"]
    assert ddc["passed"] is True and ddc["errors"] == 0
    assert ddc["win8_cnt"] == 2
    assert ddc["python_ref_max_lsb_err"] == 0
    assert ddc["tones32_beats"] == 32 and ddc["mask32_hex"] == "aaaaaaaa"

    # 6. Unified FPGA Machine Control Top-Level Integration
    top = tbs["tb_fpga_top_machine_ctrl"]
    assert top["passed"] is True and top["errors"] == 0
    assert top["uart_ok"] is True
    assert top["sw_bypass_rejected"] is True
    assert top["cfg_lock_ok"] is True
    assert top["boed_cycles"] == 584
    assert top["boed_mu_off_q8"] == -171749
    assert top["boed_std_q4"] == 5711
    assert top["boed_next_probe_q8"] == 5611
    assert top["boed_0lsb_ok"] is True
    assert top["ddc_autofeed_ok"] is True
    assert top["simultaneous_trip_ns"] <= 30
    assert top["spi_zero_clamp_ok"] is True


def test_live_sky130_4k_crossbar_968g_verilator_iverilog_and_yosys():
    """OBS-143: Verify synthesizable 968-gate 4 K Cryo-CMOS crossbar RTL + 8-die daisy-chain TB."""
    xbar_dir = REPO_ROOT / "rtl" / "cryo_crossbar_4k"
    assert (xbar_dir / "sky130_4k_crossbar_121g.v").is_file()
    assert (xbar_dir / "tb_sky130_4k_crossbar_121g.v").is_file()

    verilator_bin = resolve_eda_tool("verilator")
    iverilog_bin = resolve_eda_tool("iverilog")
    vvp_bin = resolve_eda_tool("vvp")
    yosys_bin = resolve_eda_tool("yosys")
    assert verilator_bin and iverilog_bin and vvp_bin and yosys_bin

    vproc = subprocess.run(
        [str(verilator_bin), "--lint-only", "-Wall", "--top-module", "sky130_4k_crossbar_121g",
         "sky130_4k_crossbar_121g.v"],
        cwd=str(xbar_dir), capture_output=True, text=True, timeout=60, env=_eda_env(verilator_bin), check=False,
    )
    assert vproc.returncode == 0 and "%Warning" not in (vproc.stdout + vproc.stderr)

    with tempfile.TemporaryDirectory(prefix="xbar4k_sim_") as tmpdir:
        sim_bin = Path(tmpdir) / "sim_xbar"
        comp = subprocess.run(
            [str(iverilog_bin), "-g2012", "-Wall", "-o", str(sim_bin),
             "sky130_4k_crossbar_121g.v", "tb_sky130_4k_crossbar_121g.v"],
            cwd=str(xbar_dir), capture_output=True, text=True, timeout=60, env=_eda_env(iverilog_bin), check=False,
        )
        assert comp.returncode == 0 and "warning:" not in (comp.stdout + comp.stderr).lower()
        sim = subprocess.run(
            [str(vvp_bin), str(sim_bin)],
            cwd=str(xbar_dir), capture_output=True, text=True, timeout=60, env=_eda_env(vvp_bin), check=False,
        )
        assert sim.returncode == 0
        assert "PASS: tb_sky130_4k_crossbar_121g" in sim.stdout
        assert "total_gates=968" in sim.stdout and "trl=2_pending_4k_pdk" in sim.stdout

    yproc = subprocess.run(
        [str(yosys_bin), "-q", "-p",
         "read_verilog sky130_4k_crossbar_121g.v; hierarchy -check -top sky130_4k_crossbar_121g; proc; opt; check -assert"],
        cwd=str(xbar_dir), capture_output=True, text=True, timeout=60, env=_eda_env(yosys_bin), check=False,
    )
    assert yproc.returncode == 0


def test_openroad_signoff_manifest_honesty_and_sha_integrity():
    """OBS-049 / OBS-112 / OBS-152: Verify honest SKY130 manifest (no fake 0-violation Attempt-2 signoff)."""
    import hashlib
    manifest = json.loads(
        (REPO_ROOT / "hardware" / "eda_flow" / "openroad_signoff_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["tapeout_readiness_status"] == "PRE_FOUNDRY_NCH8_MACRO_PROTOTYPE_NOT_TAPEOUT_READY"
    assert manifest["epistemic"]["tapeout_done"] is False
    assert manifest["epistemic"]["tapeout_ready"] is False
    assert manifest["epistemic"]["foundry_signoff_complete"] is False
    assert manifest["epistemic"]["real_io_pad_cells"] == []

    p4c = manifest["pilot4c_sky130_audit_correction"]
    assert abs(p4c["nch8_true_sync_fmax_tt_25c_1v8_MHz"] - 272.48) < 0.1
    assert abs(p4c["nch8_true_sync_fmax_ss_100c_1v6_MHz"] - 154.08) < 0.1
    assert p4c["missing_pdn_verified"] is True

    att2 = manifest["historical_sky130_signoff_runs_exp76_to_exp123"]["exp123_openroad_2024_antenna_eco"]
    assert att2["attempt2_status"] == "INVALID_DISCONNECTED_NETS"
    assert att2["attempt2_valid_signoff"] is False
    assert att2["attempt2_unrouted_nets_stripped"] == 101

    assert manifest["drc_exclude_cells_audit"]["historical_blanker_tile_synth_v_excluded_cells"] == 1154
    assert manifest["legacy_exp38_exp58_exp64_archive_notice"]["status"] == "ARCHIVED_RD_PROTOTYPE_NOT_MPW_CANDIDATE"

    for src in manifest["whitelisted_rtl_sources"]:
        fp = REPO_ROOT / src["path"]
        assert fp.is_file()
        assert hashlib.sha256(fp.read_bytes()).hexdigest() == src["sha256"]


def test_live_yosys_check_assert_zero_latches_zero_comb_loops():
    chk = run_yosys_check_assert(RTL_DIR)
    assert chk["passed"] is True and chk["returncode"] == 0


def test_real_yosys_synthesis_stat_jsons_and_honest_epistemic_audit():
    audit = json.loads((AUDIT_DIR / "rtl_machine_ctrl_audit.json").read_text(encoding="utf-8"))
    assert audit["all_gates_passed"] is True
    assert audit["no_external_eda_sim"] is False
    assert audit["no_vendor_vivado_pnr"] is True
    assert audit["no_lab_measurement_rtl"] is True
    assert audit["iec61508_certified"] is False
    assert audit["semi_s2_certified"] is False
    assert audit["certification_status"] == "DESIGN_ONLY_NOT_CERTIFIED"

    for fam in ("xcup", "xc7", "ecp5"):
        stat = json.loads((AUDIT_DIR / f"yosys_{fam}_stat.json").read_text(encoding="utf-8"))
        assert stat["passed"] is True
        assert stat["family"] == fam
        assert stat["top_module"] == "fpga_top_machine_ctrl"
        assert stat["measurement_kind"] == "yosys_pre_pnr_measured"
        assert stat["no_vendor_vivado_pnr"] is True
        assert stat["no_lab_measurement_rtl"] is True
        assert stat["iec61508_certified"] is False
        assert stat["lut_total"] > 5_000
        assert stat["ff_total"] > 4_000
        assert stat["bram_blocks"] >= 12
        assert stat["dsp_total"] >= 100
        assert audit["yosys_synthesis"]["targets"][fam]["lut_total"] == stat["lut_total"]
        assert audit["yosys_synthesis"]["targets"][fam]["ff_total"] == stat["ff_total"]
        assert audit["yosys_synthesis"]["targets"][fam]["bram_blocks"] == stat["bram_blocks"]
        assert audit["yosys_synthesis"]["targets"][fam]["dsp_total"] == stat["dsp_total"]

    xcup = json.loads((AUDIT_DIR / "yosys_xcup_stat.json").read_text(encoding="utf-8"))
    assert xcup["fits_zu48dr"] is True
    assert xcup["zu48dr_pct"]["lut_pct"] < 15.0
    assert xcup["zu48dr_pct"]["ff_pct"] < 10.0
    assert xcup["zu48dr_pct"]["bram36_equiv_pct"] < 10.0
    assert xcup["zu48dr_pct"]["dsp48e2_pct"] < 10.0


if __name__ == "__main__":
    if "--write-audit" in sys.argv:
        result = generate_stage2_rtl_audit(write_outputs=True)
        print(json.dumps({
            "all_gates_passed": result["all_gates_passed"],
            "total_ctrl_rtl_loc": result["static_hygiene"]["total_ctrl_rtl_loc"],
            "yosys_summary": {
                fam: {
                    "lut": rec["lut_total"],
                    "ff": rec["ff_total"],
                    "bram_blocks": rec["bram_blocks"],
                    "dsp": rec["dsp_total"],
                }
                for fam, rec in result["yosys_synthesis"]["targets"].items()
            },
        }, indent=2))
        sys.exit(0 if result["all_gates_passed"] else 1)
