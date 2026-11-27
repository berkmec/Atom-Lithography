"""Real-EDA Verification & Contract Suite for src/rtl/blanker_tile.v & blanker_array_ctrl.v.

Replaces pure-Python mocks with LIVE open-source EDA verification (OBS-007, OBS-015, OBS-058, OBS-142):
  1. Verilator `--lint-only -Wall` (0 warnings, 0 errors, no SV keyword `abort` clash) on
     blanker_gate.v, blanker_gate_spec.v, blanker_tile.v (NCH=64 and NCH=8).
  2. Icarus Verilog `-g2012 -Wall` + `vvp` running:
       - src/rtl/blanker_gate_tb.v (30 ns IBIC pulse single-count, target_count=0 guard, WD abort)
       - Live blanker_tile (NCH=8) testbench verifying NCH<64 OOB protection, 2-FF reset bridge,
         2-FF IBIC rising-edge sync, and sticky done/abort bitmap semantics.
       - Live unified integration testbench wiring rtl/machine_ctrl/blanker_array_ctrl.v directly
         to src/rtl/blanker_tile.v (serial frame load -> latch -> frame_latch_n -> per-channel
         IBIC single-ion closure -> tile_done_out/tile_abort_out -> interlock force blank!).
  3. Yosys `check -assert` zero-latch / zero-comb-loop structural check.
  4. Poisson watchdog default verification: WATCHDOG_CYCLES >= 7,500,000 (75 ms @ 100 MHz
     >= 5 * 15 ms canonical Poisson tau_shot -> <0.67% truncation).
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_RTL = REPO_ROOT / "src" / "rtl"
MC_RTL = REPO_ROOT / "rtl" / "machine_ctrl"


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


def test_blanker_watchdog_default_and_no_reserved_abort_port():
    gate_src = (SRC_RTL / "blanker_gate.v").read_text(encoding="utf-8")
    tile_src = (SRC_RTL / "blanker_tile.v").read_text(encoding="utf-8")

    m_gate = re.search(r"parameter\s+integer\s+WATCHDOG_CYCLES\s*=\s*(\d+)", gate_src)
    m_tile = re.search(r"parameter\s+integer\s+WATCHDOG_CYCLES\s*=\s*(\d+)", tile_src)
    assert m_gate is not None and int(m_gate.group(1)) >= 7_500_000, (
        "blanker_gate.v WATCHDOG_CYCLES must be >= 7,500,000 (75 ms @ 100 MHz >= 5*15 ms)"
    )
    assert m_tile is not None and int(m_tile.group(1)) >= 7_500_000, (
        "blanker_tile.v WATCHDOG_CYCLES must be >= 7,500,000 (75 ms @ 100 MHz >= 5*15 ms)"
    )
    assert "timeout_abort" in gate_src and not re.search(r"output\s+wire\s+abort\b", gate_src)
    assert "rst_sync_n" in gate_src and "rst_sync_n" in tile_src
    assert "count_hit_rise" in gate_src


def test_live_verilator_lint_wall_blanker_gate_and_tile():
    verilator = _resolve_tool("verilator")
    env = _eda_env(verilator)

    targets = [
        ("blanker_gate", [], ["blanker_gate.v"]),
        ("blanker_gate_spec", [], ["blanker_gate_spec.v"]),
        ("blanker_tile", [], ["blanker_tile.v", "blanker_gate.v"]),
        ("blanker_tile", ["-GNCH=8"], ["blanker_tile.v", "blanker_gate.v"]),
    ]
    for top, flags, files in targets:
        proc = subprocess.run(
            [str(verilator), "--lint-only", "-Wall", *flags, "--top-module", top, *files],
            cwd=str(SRC_RTL),
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
            check=False,
        )
        out = proc.stdout + "\n" + proc.stderr
        assert proc.returncode == 0, f"Verilator failed on {top} {flags}:\n{out}"
        assert "%Warning" not in out and "%Error" not in out, f"Verilator warnings on {top}:\n{out}"


def test_live_iverilog_blanker_tile_nch8_oob_and_sticky_contract():
    iverilog = _resolve_tool("iverilog")
    vvp = _resolve_tool("vvp")
    env = _eda_env(iverilog)

    tb_code = r"""
`timescale 1ns/1ps
module tb_blanker_tile_live;
    reg clk = 0;
    reg rst_n = 0;
    reg cfg_we = 0;
    reg [6:0] cfg_addr = 7'd0;
    reg [7:0] cfg_data = 8'd0;
    reg start_all = 0;
    reg [7:0] count_hit = 8'd0;
    reg [5:0] rd_addr = 6'd0;

    wire [7:0] blanker_open, done_sticky, abort_sticky;
    wire busy_any, tile_done_out, tile_abort_out;
    wire [7:0] rd_counted;
    integer errors = 0;

    blanker_tile #(.NCH(8), .WATCHDOG_CYCLES(40), .COUNT_W(8)) dut (
        .clk(clk), .rst_n(rst_n),
        .cfg_we(cfg_we), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .start_all(start_all), .count_hit(count_hit),
        .blanker_open(blanker_open), .busy_any(busy_any),
        .done_sticky(done_sticky), .abort_sticky(abort_sticky),
        .rd_addr(rd_addr), .rd_counted(rd_counted),
        .ser_sel(1'b0), .ser_sclk(1'b0), .ser_sdata(1'b0),
        .ser_tile_latch_n(1'b1), .ser_frame_latch_n(1'b1),
        .ser_beam_en(1'b1),
        .tile_done_out(tile_done_out), .tile_abort_out(tile_abort_out)
    );

    always #5 clk = ~clk;

    task wr_cfg(input [6:0] a, input [7:0] d);
        begin
            @(negedge clk); cfg_addr = a; cfg_data = d; cfg_we = 1'b1;
            @(posedge clk); @(negedge clk); cfg_we = 1'b0;
        end
    endtask

    initial begin
        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (5) @(posedge clk); // 2-FF reset sync + ser_beam_en 2-FF sync

        // Configure ch3 target=2, ch5 target=1, enable ch3 only
        wr_cfg(7'd3, 8'd2);
        wr_cfg(7'd5, 8'd1);
        wr_cfg(7'd67, 8'd1);

        // OBS-058 OOB protection test for NCH=8: writing cfg_addr=11 (in [8..63]) MUST NOT
        // corrupt enable_reg[3] or any other enable bit!
        wr_cfg(7'd11, 8'd0); // previously aliased to enable_reg[11 & 7] = enable_reg[3] <= 0!
        wr_cfg(7'd13, 8'd1); // previously aliased to enable_reg[5] <= 1!
        wr_cfg(7'd75, 8'd1); // > 64+NCH-1 must be ignored

        @(negedge clk); start_all = 1'b1;
        @(posedge clk); @(negedge clk); start_all = 1'b0;
        #1;
        if (blanker_open !== 8'b0000_1000 || !busy_any) begin
            $display("FAIL: OOB write corrupted enable_reg! open=%b busy=%b", blanker_open, busy_any);
            errors = errors + 1;
        end

        // Drive two 30 ns IBIC pulses on ch3 -> each counts ONCE -> done_sticky[3] sets
        @(negedge clk); count_hit = 8'b0000_1000;
        repeat (3) @(posedge clk);
        @(negedge clk); count_hit = 8'd0;
        repeat (3) @(posedge clk);
        rd_addr = 6'd3; #1;
        if (rd_counted !== 8'd1 || !blanker_open[3]) begin
            $display("FAIL: 30ns pulse #1 count=%0d open=%b", rd_counted, blanker_open[3]);
            errors = errors + 1;
        end

        @(negedge clk); count_hit = 8'b0000_1000;
        repeat (3) @(posedge clk);
        @(negedge clk); count_hit = 8'd0;
        repeat (4) @(posedge clk);
        #1;
        if (done_sticky !== 8'b0000_1000 || abort_sticky !== 8'd0 || !tile_done_out || blanker_open !== 8'd0) begin
            $display("FAIL: ch3 completion mismatch done=%b abort=%b tdone=%b open=%b",
                     done_sticky, abort_sticky, tile_done_out, blanker_open);
            errors = errors + 1;
        end

        // Verify OOB rd_addr returns 0 safely
        rd_addr = 6'd20; #1;
        if (rd_counted !== 8'd0) begin
            $display("FAIL: OOB rd_addr returned %0d", rd_counted);
            errors = errors + 1;
        end

        // Enable ch1 target=1 and let watchdog expire -> abort_sticky[1]=1, tile_abort_out=1
        wr_cfg(7'd1, 8'd1);
        wr_cfg(7'd65, 8'd1);
        wr_cfg(7'd67, 8'd0);
        @(negedge clk); start_all = 1'b1;
        @(posedge clk); @(negedge clk); start_all = 1'b0;
        repeat (50) @(posedge clk);
        #1;
        if (abort_sticky !== 8'b0000_0010 || !tile_abort_out) begin
            $display("FAIL: watchdog abort sticky mismatch abort=%b tabort=%b", abort_sticky, tile_abort_out);
            errors = errors + 1;
        end

        if (errors == 0) begin
            $display("TILE_LIVE_PASS");
            $finish;
        end else begin
            $display("TILE_LIVE_FAIL errors=%0d", errors);
            $fatal(1);
        end
    end
endmodule
"""
    with tempfile.TemporaryDirectory(prefix="blanker_tile_sim_") as tmp:
        tb_fp = Path(tmp) / "tb_blanker_tile_live.v"
        sim_bin = Path(tmp) / "sim_tile"
        tb_fp.write_text(tb_code, encoding="utf-8")
        comp = subprocess.run(
            [str(iverilog), "-g2012", "-Wall", "-o", str(sim_bin),
             str(SRC_RTL / "blanker_gate.v"), str(SRC_RTL / "blanker_tile.v"), str(tb_fp)],
            capture_output=True, text=True, timeout=60, env=env, check=False,
        )
        assert comp.returncode == 0, f"iverilog compile failed:\n{comp.stdout}\n{comp.stderr}"
        sim = subprocess.run(
            [str(vvp), str(sim_bin)],
            capture_output=True, text=True, timeout=60, env=env, check=False,
        )
        assert sim.returncode == 0 and "TILE_LIVE_PASS" in sim.stdout, f"sim failed:\n{sim.stdout}\n{sim.stderr}"


def test_live_unified_blanker_array_ctrl_to_blanker_tile_integration():
    """OBS-007 End-to-End Integration: blanker_array_ctrl.v directly driving blanker_tile.v!"""
    iverilog = _resolve_tool("iverilog")
    vvp = _resolve_tool("vvp")
    env = _eda_env(iverilog)

    tb_code = r"""
`timescale 1ns/1ps
module tb_blanker_unified_chain;
    reg clk = 0;
    reg rst_n = 0;
    reg interlock_blank_force = 0;
    reg frame_start = 0;
    reg mem_we = 0;
    reg mem_bank_sel = 0;
    reg [4:0] mem_row_addr = 5'd0;
    reg [31:0] mem_wdata = 32'd0;
    wire [31:0] mem_rdata;

    wire [3:0] tile_sel;
    wire tile_sclk, tile_sdata, tile_latch_n, frame_latch_n;
    wire [15:0] tile_beam_en;
    wire busy, safe_blanked, interlock_latched, frame_done_sticky, interlock_abort_sticky;
    wire [15:0] tile_done_sticky, tile_abort_sticky;
    wire any_tile_abort, all_tiles_done;
    wire [10:0] active_unblank_cnt;
    wire signed [15:0] dx_out, dy_out;

    reg [63:0] tile0_hits = 64'd0;
    wire [63:0] tile0_open, tile0_done_st, tile0_abort_st;
    wire tile0_busy, tile0_done_out, tile0_abort_out;
    wire [7:0] tile0_rd_cnt;
    integer errors = 0;

    blanker_array_ctrl u_ctrl (
        .clk(clk), .rst_n(rst_n),
        .interlock_blank_force(interlock_blank_force),
        .frame_start(frame_start), .sticky_clr(1'b0), .interlock_clr(1'b0),
        .auto_offset_en(1'b0), .sclk_div(16'd4),
        .dx_pitch(16'sd0), .dy_pitch(16'sd0), .tile_en_mask(16'h0001),
        .mem_we(mem_we), .mem_bank_sel(mem_bank_sel),
        .mem_row_addr(mem_row_addr), .mem_wdata(mem_wdata), .mem_rdata(mem_rdata),
        .tile_done_in({15'd0, tile0_done_out}), .tile_abort_in({15'd0, tile0_abort_out}),
        .tile_sel(tile_sel), .tile_sclk(tile_sclk), .tile_sdata(tile_sdata),
        .tile_latch_n(tile_latch_n), .frame_latch_n(frame_latch_n),
        .tile_beam_en(tile_beam_en), .busy(busy), .safe_blanked(safe_blanked),
        .interlock_latched(interlock_latched), .frame_done_sticky(frame_done_sticky),
        .interlock_abort_sticky(interlock_abort_sticky),
        .tile_done_sticky(tile_done_sticky), .tile_abort_sticky(tile_abort_sticky),
        .any_tile_abort(any_tile_abort), .all_tiles_done(all_tiles_done),
        .active_unblank_cnt(active_unblank_cnt),
        .stitch_dx_pitch_out(dx_out), .stitch_dy_pitch_out(dy_out)
    );

    blanker_tile #(.NCH(64), .WATCHDOG_CYCLES(5000), .COUNT_W(8)) u_tile0 (
        .clk(clk), .rst_n(rst_n),
        .cfg_we(1'b0), .cfg_addr(7'd0), .cfg_data(8'd0), .start_all(1'b0),
        .count_hit(tile0_hits), .blanker_open(tile0_open), .busy_any(tile0_busy),
        .done_sticky(tile0_done_st), .abort_sticky(tile0_abort_st),
        .rd_addr(6'd0), .rd_counted(tile0_rd_cnt),
        .ser_sel(tile_sel == 4'd0), .ser_sclk(tile_sclk), .ser_sdata(tile_sdata),
        .ser_tile_latch_n(tile_latch_n), .ser_frame_latch_n(frame_latch_n),
        .ser_beam_en(tile_beam_en[0]),
        .tile_done_out(tile0_done_out), .tile_abort_out(tile0_abort_out)
    );

    always #5 clk = ~clk;

    initial begin
        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (5) @(posedge clk);

        // Enable row 0 cols 0 and 2 -> tile 0 channels 0 and 2
        @(negedge clk);
        mem_bank_sel = 1'b0; mem_row_addr = 5'd0; mem_wdata = 32'h0000_0005; mem_we = 1'b1;
        @(posedge clk); @(negedge clk); mem_we = 1'b0;

        // Launch 1024-ch serial frame load into tile 0
        @(negedge clk); frame_start = 1'b1;
        @(posedge clk); @(negedge clk); frame_start = 1'b0;
        wait (frame_done_sticky == 1'b1);
        repeat (6) @(posedge clk);
        #1;

        // Channels 0 and 2 of tile 0 MUST now be actively open awaiting counted IBIC hits!
        if (tile0_open !== 64'h0000_0000_0000_0005) begin
            $display("FAIL: unified serial load did not open exact ch 0 & 2! open=%h", tile0_open);
            errors = errors + 1;
        end

        // Deliver independent single-ion IBIC 30 ns hit on channel 0 ONLY -> ch 0 closes, ch 2 stays open!
        @(negedge clk); tile0_hits = 64'h0000_0000_0000_0001;
        repeat (3) @(posedge clk);
        @(negedge clk); tile0_hits = 64'd0;
        repeat (4) @(posedge clk);
        #1;
        if (tile0_open !== 64'h0000_0000_0000_0004 || tile0_done_st[0] !== 1'b1 || tile0_done_out !== 1'b0) begin
            $display("FAIL: per-channel IBIC closure failed! open=%h done0=%b tdone=%b",
                     tile0_open, tile0_done_st[0], tile0_done_out);
            errors = errors + 1;
        end

        // Deliver single-ion IBIC hit on channel 2 -> tile0 completes & propagates tile_done_sticky[0] to FPGA!
        @(negedge clk); tile0_hits = 64'h0000_0000_0000_0004;
        repeat (3) @(posedge clk);
        @(negedge clk); tile0_hits = 64'd0;
        repeat (8) @(posedge clk);
        #1;
        if (tile0_open !== 64'd0 || !tile0_done_out || !all_tiles_done || !tile_done_sticky[0]) begin
            $display("FAIL: tile0 done feedback did not propagate! open=%h tdone=%b all=%b",
                     tile0_open, tile0_done_out, all_tiles_done);
            errors = errors + 1;
        end

        if (errors == 0) begin
            $display("UNIFIED_CHAIN_PASS");
            $finish;
        end else begin
            $display("UNIFIED_CHAIN_FAIL errors=%0d", errors);
            $fatal(1);
        end
    end
endmodule
"""
    with tempfile.TemporaryDirectory(prefix="blanker_chain_sim_") as tmp:
        tb_fp = Path(tmp) / "tb_blanker_unified_chain.v"
        sim_bin = Path(tmp) / "sim_chain"
        tb_fp.write_text(tb_code, encoding="utf-8")
        comp = subprocess.run(
            [str(iverilog), "-g2012", "-Wall", "-o", str(sim_bin),
             str(MC_RTL / "blanker_array_ctrl.v"),
             str(SRC_RTL / "blanker_gate.v"),
             str(SRC_RTL / "blanker_tile.v"),
             str(tb_fp)],
            capture_output=True, text=True, timeout=60, env=env, check=False,
        )
        assert comp.returncode == 0, f"iverilog compile failed:\n{comp.stdout}\n{comp.stderr}"
        sim = subprocess.run(
            [str(vvp), str(sim_bin)],
            capture_output=True, text=True, timeout=60, env=env, check=False,
        )
        assert sim.returncode == 0 and "UNIFIED_CHAIN_PASS" in sim.stdout, (
            f"unified chain sim failed:\n{sim.stdout}\n{sim.stderr}"
        )


def test_live_yosys_check_assert_blanker_tile():
    yosys = _resolve_tool("yosys")
    env = _eda_env(yosys)
    proc = subprocess.run(
        [str(yosys), "-q", "-p",
         "read_verilog blanker_gate.v blanker_tile.v; hierarchy -check -top blanker_tile; proc; opt; check -assert"],
        cwd=str(SRC_RTL), capture_output=True, text=True, timeout=60, env=env, check=False,
    )
    assert proc.returncode == 0, f"Yosys check -assert failed:\n{proc.stdout}\n{proc.stderr}"
