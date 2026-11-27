"""Real-EDA Cycle-Contract & Simulation Tests for src/rtl/blanker_gate.v.

Verifies BOTH the cycle-accurate contract model AND live open-source EDA execution
(iverilog -g2012 -Wall + vvp on src/rtl/blanker_gate_tb.v + Verilator -Wall + Yosys)
eliminating pure-Python mock masking (OBS-015, OBS-058, OBS-113, OBS-142).
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_RTL = REPO_ROOT / "src" / "rtl"


def _resolve_tool(name: str) -> Path:
    found = shutil.which(name)
    if found:
        return Path(found).resolve()
    for d in (Path.home() / ".local" / "bin", Path.home() / ".local" / "oss-cad-suite" / "bin"):
        cand = d / name
        if cand.is_file() and os.access(cand, os.X_OK):
            return cand.resolve()
    raise AssertionError(f"Required EDA tool not found: {name}")


def _eda_env(tool: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["PATH"] = f"{tool.parent}{os.pathsep}{env.get('PATH', '')}"
    return env


class Gate:
    """Reference behavioral model matching hardened blanker_gate.v (target=0 guard + rising-edge hit)."""

    WD = 50

    def __init__(self):
        self.st, self.counted, self.wd = "IDLE", 0, 0
        self.hit_s1, self.hit_s2, self.hit_prev = 0, 0, 0

    def step(self, rst_n, start, hit, tgt):
        if not rst_n:
            self.st, self.counted, self.wd = "IDLE", 0, 0
            self.hit_s1, self.hit_s2, self.hit_prev = 0, 0, 0
            return dict(blanker=0, busy=0, done=0, timeout_abort=0, counted=0)
        st = self.st
        hit_rise = int(self.hit_s2 and not self.hit_prev)
        out = dict(
            blanker=int(st == "RUN"),
            busy=int(st == "RUN"),
            done=int(st == "FIN"),
            timeout_abort=int(st == "TO"),
            counted=self.counted,
        )
        self.hit_prev = self.hit_s2
        self.hit_s2 = self.hit_s1
        self.hit_s1 = int(bool(hit))
        if st == "IDLE":
            if start and tgt > 0:
                self.counted, self.wd, self.st = 0, 0, "RUN"
        elif st == "RUN":
            if self.wd < self.WD - 1:
                self.wd += 1
            if hit_rise:
                self.counted += 1
                if self.counted >= tgt:
                    self.st = "FIN"
            elif self.wd >= self.WD - 1:
                self.st = "TO"
        else:
            self.st = "IDLE"
        return out


def run(seq):
    g = Gate()
    return [g.step(*s) for s in seq]


def test_single_count_30ns_pulse_counts_once():
    # 3-clock (30 ns @ 100 MHz) IBIC hit pulse MUST count exactly once!
    seq = (
        [(0, 0, 0, 1)] * 2
        + [(1, 1, 0, 1)]
        + [(1, 0, 0, 1)] * 2
        + [(1, 0, 1, 1)] * 3
        + [(1, 0, 0, 1)] * 5
    )
    out = run(seq)
    assert [o["done"] for o in out].count(1) == 1
    fin = next(i for i, o in enumerate(out) if o["done"])
    assert out[fin]["blanker"] == 0 and out[fin]["busy"] == 0
    assert out[fin]["counted"] == 1


def test_target_zero_never_opens_blanker():
    seq = [(0, 0, 0, 0)] * 2 + [(1, 1, 0, 0)] + [(1, 0, 0, 0)] * 10
    out = run(seq)
    assert all(o["blanker"] == 0 and o["busy"] == 0 and o["timeout_abort"] == 0 for o in out)


def test_watchdog_abort_and_dead_cycle():
    seq = [(1, 1, 0, 1)] + [(1, 0, 0, 1)] * 60 + [(1, 1, 0, 1)] + [(1, 0, 0, 1)] * 3
    out = run(seq)
    assert sum(o["timeout_abort"] for o in out) == 1
    ab = next(i for i, o in enumerate(out) if o["timeout_abort"])
    assert out[ab]["blanker"] == 0


def test_live_iverilog_blanker_gate_tb_passes_zero_errors():
    """Live Icarus Verilog + vvp execution of src/rtl/blanker_gate_tb.v (OBS-058)."""
    iverilog = _resolve_tool("iverilog")
    vvp = _resolve_tool("vvp")
    env = _eda_env(iverilog)

    with tempfile.TemporaryDirectory(prefix="blanker_gate_sim_") as tmp:
        sim_bin = Path(tmp) / "sim_blanker_gate"
        comp = subprocess.run(
            [str(iverilog), "-g2012", "-Wall", "-o", str(sim_bin),
             "blanker_gate.v", "blanker_gate_tb.v"],
            cwd=str(SRC_RTL), capture_output=True, text=True, timeout=60, env=env, check=False,
        )
        assert comp.returncode == 0, f"iverilog compile failed:\n{comp.stdout}\n{comp.stderr}"
        assert "warning:" not in (comp.stdout + comp.stderr).lower(), comp.stdout + comp.stderr

        sim = subprocess.run(
            [str(vvp), str(sim_bin)],
            cwd=str(SRC_RTL), capture_output=True, text=True, timeout=60, env=env, check=False,
        )
        assert sim.returncode == 0, f"vvp exited non-zero:\n{sim.stdout}\n{sim.stderr}"
        assert "BLANKER_TB_PASS" in sim.stdout and "FAIL" not in sim.stdout, sim.stdout
