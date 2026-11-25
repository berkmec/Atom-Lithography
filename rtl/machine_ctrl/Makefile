# Makefile for rtl/machine_ctrl/ - Real EDA Linting, Simulation & Synthesis
# Portably resolves rootless OSS CAD Suite from PATH or $(HOME)/.local/oss-cad-suite/bin

EDA_BIN   := $(shell if command -v iverilog >/dev/null 2>&1; then dirname $$(command -v iverilog); elif [ -d "$(HOME)/.local/oss-cad-suite/bin" ]; then echo "$(HOME)/.local/oss-cad-suite/bin"; else echo ""; fi)
IVERILOG  := $(if $(EDA_BIN),$(EDA_BIN)/iverilog,iverilog)
VVP       := $(if $(EDA_BIN),$(EDA_BIN)/vvp,vvp)
VERILATOR := $(if $(EDA_BIN),$(EDA_BIN)/verilator,verilator)
YOSYS     := $(if $(EDA_BIN),$(EDA_BIN)/yosys,yosys)

BOED_SRCS := ../boed_fpga/boed_lut_rom.v ../boed_fpga/boed_isqrt_cordic.v ../boed_fpga/boed_q16_core.v
CTRL_SRCS := blanker_array_ctrl.v uhv_interlock_fsm.v aom_pid_ctrl.v spi_dac_hv_ctrl.v cryo_mux_ddc_ctrl.v uart_axi_regmap.v
TOP_SRCS  := $(BOED_SRCS) $(CTRL_SRCS) fpga_top_machine_ctrl.v

.PHONY: all lint sim sim-blanker sim-interlock sim-pid sim-spi sim-ddc sim-top check synth-xcup synth-xc7 synth-ecp5 synth-all clean

all: lint sim check

lint:
	$(VERILATOR) --lint-only -Wall --top-module blanker_array_ctrl blanker_array_ctrl.v
	$(VERILATOR) --lint-only -Wall --top-module uhv_interlock_fsm uhv_interlock_fsm.v
	$(VERILATOR) --lint-only -Wall --top-module aom_pid_ctrl aom_pid_ctrl.v
	$(VERILATOR) --lint-only -Wall --top-module spi_dac_hv_ctrl spi_dac_hv_ctrl.v
	$(VERILATOR) --lint-only -Wall --top-module cryo_mux_ddc_ctrl cryo_mux_ddc_ctrl.v
	$(VERILATOR) --lint-only -Wall -GN_CH=32 --top-module cryo_mux_ddc_ctrl cryo_mux_ddc_ctrl.v
	$(VERILATOR) --lint-only -Wall --top-module uart_axi_regmap uart_axi_regmap.v
	$(VERILATOR) --lint-only -Wall --top-module fpga_top_machine_ctrl $(TOP_SRCS)

sim: sim-blanker sim-interlock sim-pid sim-spi sim-ddc sim-top

sim-blanker:
	$(IVERILOG) -g2012 -Wall -o /tmp/sim_blanker_array_ctrl blanker_array_ctrl.v tb_blanker_array_ctrl.v
	$(VVP) /tmp/sim_blanker_array_ctrl
	rm -f /tmp/sim_blanker_array_ctrl

sim-interlock:
	$(IVERILOG) -g2012 -Wall -o /tmp/sim_uhv_interlock_fsm uhv_interlock_fsm.v tb_uhv_interlock_fsm.v
	$(VVP) /tmp/sim_uhv_interlock_fsm
	rm -f /tmp/sim_uhv_interlock_fsm

sim-pid:
	$(IVERILOG) -g2012 -Wall -o /tmp/sim_aom_pid_ctrl aom_pid_ctrl.v tb_aom_pid_ctrl.v
	$(VVP) /tmp/sim_aom_pid_ctrl
	rm -f /tmp/sim_aom_pid_ctrl

sim-spi:
	$(IVERILOG) -g2012 -Wall -o /tmp/sim_spi_dac_hv_ctrl spi_dac_hv_ctrl.v tb_spi_dac_hv_ctrl.v
	$(VVP) /tmp/sim_spi_dac_hv_ctrl
	rm -f /tmp/sim_spi_dac_hv_ctrl

sim-ddc:
	$(IVERILOG) -g2012 -Wall -o /tmp/sim_cryo_mux_ddc_ctrl cryo_mux_ddc_ctrl.v tb_cryo_mux_ddc_ctrl.v
	$(VVP) /tmp/sim_cryo_mux_ddc_ctrl
	rm -f /tmp/sim_cryo_mux_ddc_ctrl

sim-top:
	$(IVERILOG) -g2012 -Wall -o /tmp/sim_fpga_top_machine_ctrl $(TOP_SRCS) tb_fpga_top_machine_ctrl.v
	$(VVP) /tmp/sim_fpga_top_machine_ctrl
	rm -f /tmp/sim_fpga_top_machine_ctrl

check:
	$(YOSYS) -q -p "read_verilog $(TOP_SRCS); hierarchy -check -top fpga_top_machine_ctrl; proc; opt; check -assert"

synth-xcup:
	$(YOSYS) -q -p "read_verilog $(TOP_SRCS); synth_xilinx -family xcup -top fpga_top_machine_ctrl; stat"

synth-xc7:
	$(YOSYS) -q -p "read_verilog $(TOP_SRCS); synth_xilinx -family xc7 -top fpga_top_machine_ctrl; stat"

synth-ecp5:
	$(YOSYS) -q -p "read_verilog $(TOP_SRCS); synth_ecp5 -top fpga_top_machine_ctrl; stat"

synth-all: synth-xcup synth-xc7 synth-ecp5

clean:
	rm -f /tmp/sim_blanker_array_ctrl /tmp/sim_uhv_interlock_fsm /tmp/sim_aom_pid_ctrl \
	      /tmp/sim_spi_dac_hv_ctrl /tmp/sim_cryo_mux_ddc_ctrl /tmp/sim_fpga_top_machine_ctrl
