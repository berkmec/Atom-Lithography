# Makefile for rtl/boed_fpga/ - Real EDA Linting, Simulation & Synthesis
# Resolves oss-cad-suite rootlessly from PATH or $(HOME)/.local/oss-cad-suite/bin

EDA_BIN := $(shell if command -v iverilog >/dev/null 2>&1; then dirname $$(command -v iverilog); elif [ -d "$(HOME)/.local/oss-cad-suite/bin" ]; then echo "$(HOME)/.local/oss-cad-suite/bin"; else echo ""; fi)
IVERILOG  := $(if $(EDA_BIN),$(EDA_BIN)/iverilog,iverilog)
VVP       := $(if $(EDA_BIN),$(EDA_BIN)/vvp,vvp)
VERILATOR := $(if $(EDA_BIN),$(EDA_BIN)/verilator,verilator)
YOSYS     := $(if $(EDA_BIN),$(EDA_BIN)/yosys,yosys)

CORE_SRCS := boed_lut_rom.v boed_isqrt_cordic.v boed_q16_core.v
TOP_SRCS  := $(CORE_SRCS) boed_top_16ch.v

.PHONY: all lint sim sim-core sim-top16 synth-xcup synth-xc7 synth-ecp5 synth-top16 clean

all: lint sim

lint:
	$(VERILATOR) --lint-only -Wall --top-module boed_q16_core $(CORE_SRCS)
	$(VERILATOR) --lint-only -Wall --top-module boed_top_16ch $(TOP_SRCS)

sim: sim-core sim-top16

sim-core:
	$(IVERILOG) -g2012 -Wall -o /tmp/sim_boed_q16_core $(CORE_SRCS) tb_boed_q16_core.v
	$(VVP) /tmp/sim_boed_q16_core
	rm -f /tmp/sim_boed_q16_core

sim-top16:
	$(IVERILOG) -g2012 -Wall -o /tmp/sim_boed_top_16ch $(TOP_SRCS) tb_boed_top_16ch.v
	$(VVP) /tmp/sim_boed_top_16ch
	rm -f /tmp/sim_boed_top_16ch

synth-xcup:
	$(YOSYS) -p "read_verilog $(CORE_SRCS); synth_xilinx -family xcup -top boed_q16_core; stat"

synth-xc7:
	$(YOSYS) -p "read_verilog $(CORE_SRCS); synth_xilinx -family xc7 -top boed_q16_core; stat"

synth-ecp5:
	$(YOSYS) -p "read_verilog $(CORE_SRCS); synth_ecp5 -top boed_q16_core; stat"

synth-top16:
	$(YOSYS) -p "read_verilog $(TOP_SRCS); synth_xilinx -family xcup -top boed_top_16ch; stat"

clean:
	rm -f /tmp/sim_boed_q16_core /tmp/sim_boed_top_16ch
