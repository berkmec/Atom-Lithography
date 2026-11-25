# `rtl/machine_ctrl/` — Unified AXI4-Lite & UART 8N1 Register Map (`REGMAP.md`)

**Top Module:** `fpga_top_machine_ctrl` (`100.0 MHz` `sys_clk`, `10.0 ns` period)  
**Address Space:** 16-bit byte-addressed, 32-bit aligned (`0x0000` – `0x06FF`)  
**Host Access:**
1. **UART 8N1 Serial Bridge (`uart_axi_regmap.v`, default `115,200 baud` @ `100 MHz`, `baud_div = 868`):**
   - **Write (`7 B` RX → `1 B` TX):** `[0x57 'W'][addr_hi][addr_lo][wdata3][wdata2][wdata1][wdata0]` → `[0x4B 'K']` (`OKAY`) or `[0x45 'E']` (`ERR`)
   - **Read (`3 B` RX → `5 B` TX):** `[0x52 'R'][addr_hi][addr_lo]` → `[0x44 'D'][rdata3][rdata2][rdata1][rdata0]`
2. **Direct External AXI4-Lite Slave (`ext_axil_*`):** Zynq UltraScale+ PS (`ZU48DR`) direct register port via fixed-priority 2:1 arbiter (UART priority over external port; single-cycle B/R responses).

> **Epistemic Notice:** Every read-only epistemic register (`0x0008`, `0x011C`) hardwires `CERTIFIED = 0` (`bit 0`) and `DESIGN_ONLY_NOT_CERTIFIED = 1` (`bit 1`). This RTL is a preliminary M0/M1 hardware design verified with real open-source EDA tools (`Verilator`, `Icarus Verilog`, `Yosys`), **not** IEC 61508 / SEMI S2 certified and **not** Vivado post-P&R or lab-measured.

---

## Hard-Wired Internal Safety Override Bus (Non-Bypassable)

```text
  il_ch_a_ok[7:0], il_ch_b_ok[7:0] (1 = HEALTHY, 0 = TRIP / OPEN-WIRE)
                │
                ▼
     ┌─────────────────────┐
     │  uhv_interlock_fsm  │  1oo2D Voting + Discrepancy Monitor + WDT
     └──────────┬──────────┘
                │ interlock_trip_out / ~safe_*_en  (<= 2 clocks = <= 20 ns @ 100 MHz, < 1 us)
                ├──────────────────────────────┬──────────────────────────────┐
                ▼                              ▼                              ▼
    ┌───────────────────────┐      ┌───────────────────────┐      ┌───────────────────────┐
    │  blanker_array_ctrl   │      │     aom_pid_ctrl      │      │    spi_dac_hv_ctrl    │
    │ interlock_blank_force │      │    interlock_abort    │      │     hv_safe_clamp     │
    │ -> tile_beam_en = 0   │      │ -> aom_drive_q16 = 0  │      │ -> hv_clr_n = 0 AND   │
    │ -> tile_sdata   = 0   │      │ -> aom_rf_en     = 0  │      │    8-ch 20'h00000 SPI │
    │    (0-cycle comb +    │      │ (+ hardwired T>=1687K │      │    zero burst + LDAC) │
    │     1-cycle latch)    │      │    over-temp abort)   │      │                       │
    └───────────────────────┘      └───────────────────────┘      └───────────────────────┘
```

---

## Block 0 (`0x0000 – 0x00FF`): Global Identification & Epistemic Status

| Offset | Name | Access | Reset | Bit Fields & Description |
| :--- | :--- | :---: | :---: | :--- |
| `0x0000` | `CHIP_ID` | RO | `0x414C4D02` | ASCII `"ALM\x02"` — Atom Lithography Machine Stage-2 FPGA Control Brain |
| `0x0004` | `VERSION` | RO | `0x00020001` | Major `[31:16] = 2`, Minor `[15:0] = 1` |
| `0x0008` | `EPISTEMIC_STATUS` | RO | `0xD001530E` | `[0]` `CERTIFIED=0`, `[1]` `DESIGN_ONLY_NOT_CERTIFIED=1`, `[2]` `NO_LAB_MEASUREMENT=1`, `[3]` `NO_VENDOR_VIVADO_PNR=1`, `[15:8]` `'S'`, `[31:16]` `0xD001` |
| `0x000C` | `GLOBAL_STATUS` | RO | `0x00000050` | `[2:0]` `il_fsm_state`, `[4]` `interlock_trip_out`, `[5]` `blk_busy`, `[6]` `blk_safe_blanked`, `[7]` `pid_abort_active`, `[8]` `spi_busy`, `[9]` `ddc_busy`, `[10]` `boed_busy`, `[15]` `il_cfg_locked`, `[16]` `uart_bridge_busy`, `[31:24]` `uart_rx_err_cnt[7:0]` |
| `0x0010` | `SCRATCH_REG` | RW | `0x00000000` | 32-bit R/W host loopback register |
| `0x0014` | `UPTIME_CYCLES` | RO | `0x00000000` | Free-running 32-bit `sys_clk` cycle counter |

---

## Block 1 (`0x0100 – 0x01FF`): UHV & Facility 1oo2D Safety Interlock (`uhv_interlock_fsm.v`)

**BOM:** `S5.5-04, S7.4-04, S7.SAFETY-01..06`

| Offset | Name | Access | Reset | Bit Fields & Description |
| :--- | :--- | :---: | :---: | :--- |
| `0x0100` | `IL_CTRL` | RW | `0x00003F00` | `[0]` `run_enable_cmd`, `[1]` `wdt_en` (**write-locked when `il_cfg_locked=1`**), `[2]` `sw_estop`, `[3]` `reset_cmd_a` (W1P; Channel B reset is strictly hardwired to physical `il_hw_reset_b` — zero SW bypass!), `[4]` reserved/ignored (`0`), `[5]` `wdt_kick` (W1P), `[13:8]` `subsys_en_mask` `{magnet, ph3, uhv_valve, hv, laser, blanker}`, `[16]` `il_cfg_locked` (RO; latches `1` on entering `ST_SAFE_DWELL`/`ST_ARMED`/`ST_RUN`, cleared only by `rst_n` or physical `il_hw_reset_b` service-unlock in `ST_SAFE_BOOT`/`ST_FAULT_LATCHED`) |
| `0x0104` | `IL_STATUS` | RO | `0x00008008` | `[2:0]` `fsm_state` (`0=SAFE_BOOT, 1=FAULT_LATCHED, 2=SAFE_DWELL, 3=ARMED, 4=RUN`), `[3]` `interlock_trip_out`, `[9:4]` `{safe_magnet_en, safe_ph3_valve_en, safe_uhv_valve_en, safe_hv_en, safe_laser_en, safe_blanker_en}`, `[13:10]` `first_fault_code` (`1..8` sensors, `9` discrep, `10` WDT, `11` SW E-Stop), `[14]` `CERTIFIED=0`, `[15]` `DESIGN_ONLY_NOT_CERTIFIED=1`, `[31:16]` `trip_counter` |
| `0x0108` | `IL_FAULT_LATCH` | RO | `0x00000000` | `[7:0]` `sensor_fault_latched` (`0=UHV, 1=LASER_DOOR, 2=ODH_O2<19.5%, 3=PH3_L1, 4=PH3_L2, 5=HV, 6=QUENCH, 7=ESTOP`), `[8]` `discrep_fault_latched`, `[9]` `wdt_fault_latched`, `[10]` `sw_estop_latched`, `[23:16]` `discrep_ch_latched[7:0]` |
| `0x010C` | `IL_LIVE_SENSORS` | RO | `0x00000000` | `[7:0]` `ch_a_sync`, `[15:8]` `ch_b_sync`, `[23:16]` `ch_a_sync ^ ch_b_sync` (live discrepancy) |
| `0x0110` | `IL_DISCREP_WIN` | RW* | `0x00000064` | `[15:0]` Cross-channel discrepancy debounce window in `sys_clk` cycles (default `100` = `1.0 us`; **write-locked when `il_cfg_locked=1`**) |
| `0x0114` | `IL_WDT_TIMEOUT` | RW* | `0x00989680` | `[31:0]` Hardware watchdog heartbeat timeout cycles (default `10,000,000` = `100 ms`; **write-locked when `il_cfg_locked=1`**) |
| `0x0118` | `IL_DWELL_CYCLES` | RW* | `0x0BEBC200` | `[31:0]` Safe-dwell continuous healthy confirmation cycles (default `200,000,000` = `2.0 s`; **write-locked when `il_cfg_locked=1`**) |
| `0x011C` | `IL_EPISTEMIC_CSR` | RO | `0xD001530E` | Read-only hardwired `DESIGN_ONLY_NOT_CERTIFIED` register (`[0]=0`, `[1]=1`) |

---

## Block 2 (`0x0200 – 0x02FF`): 32×32 Blanker Array Controller (`blanker_array_ctrl.v`)

**BOM:** `S2.2-01, S2.4-01, S2.4-02, S3.3-01, S3.3-02`

| Offset | Name | Access | Reset | Bit Fields & Description |
| :--- | :--- | :---: | :---: | :--- |
| `0x0200` | `BLK_CTRL` | RW | `0x00000010` | `[0]` `frame_start` (W1P), `[1]` `sticky_clr` (W1P), `[2]` `interlock_clr` (W1P), `[3]` `auto_offset_en`, `[19:4]` `sclk_div[15:0]` |
| `0x0204` | `BLK_STATUS` | RO | `0x00000002` | `[0]` `busy`, `[1]` `safe_blanked`, `[2]` `interlock_latched`, `[3]` `frame_done_sticky`, `[4]` `interlock_abort_sticky`, `[5]` `any_tile_abort`, `[6]` `all_tiles_done`, `[26:16]` `active_unblank_cnt[10:0]` |
| `0x0208` | `BLK_OFFSET` | RW | `0x00000000` | `[15:0]` signed `dx_pitch`, `[31:16]` signed `dy_pitch` (step-and-stitch array pitch shift) |
| `0x020C` | `BLK_TILE_EN_MASK` | RW | `0x0000FFFF` | `[15:0]` Per-tile (16 × 64-ch) enable mask |
| `0x0210` | `BLK_TILE_DONE` | RO | `0x00000000` | `[15:0]` Sticky tile completion bitmap (`tile_done_sticky`) |
| `0x0214` | `BLK_TILE_ABORT` | RO | `0x00000000` | `[15:0]` Sticky tile abort bitmap (`tile_abort_sticky`) |
| `0x0218` | `BLK_MEM_ADDR` | RW | `0x00000000` | `[4:0]` row index `0..31`, `[8]` bank select (`0 = 1024b pattern RAM`, `1 = 1024b dead-channel mask RAM`) |
| `0x021C` | `BLK_MEM_DATA` | RW | `0x00000000` | 32-bit row word (cols `0..31`) R/W for selected row and bank |

---

## Block 3 (`0x0300 – 0x03FF`): Q16.16 AOM Laser PID Controller (`aom_pid_ctrl.v`)

**BOM:** `S5.3-03, S5.5-01, S5.5-03, S1.4-03` (`Q16.16`: `1.0 = 65,536 = 0x00010000`)

| Offset | Name | Access | Reset | Bit Fields & Description |
| :--- | :--- | :---: | :---: | :--- |
| `0x0300` | `PID_CTRL` | RW | `0x00000010` | `[0]` `enable`, `[1]` `pyro_en`, `[2]` `abort_clr` (W1P), `[3]` `state_reset` (W1P), `[7:4]` `dead_time_taps[3:0]` (`0..15`), `[8]` `sw_sample_trigger` (W1P) |
| `0x0304` | `PID_STATUS` | RO | `0x012C0010` | `[0]` `busy`, `[1]` `out_valid_sticky`, `[2]` `saturated`, `[3]` `overtemp_latched`, `[4]` `abort_active`, `[5]` `aom_rf_en`, `[31:16]` `last_temp_k` (K; hardwired abort `>= 1687 K`) |
| `0x0308` | `PID_KP` | RW | `0x00006B85` | Proportional gain `kp` in Q16.16 (default `0.42`) |
| `0x030C` | `PID_KI` | RW | `0x00005C29` | Integral gain `ki` in Q16.16 (default `0.36`) |
| `0x0310` | `PID_KD` | RW | `0x00000CCD` | Filtered derivative-on-measurement gain `kd` in Q16.16 (default `0.05`) |
| `0x0314` | `PID_KAW` | RW | `0x0000A666` | Back-calculation anti-windup gain `kaw` in Q16.16 (default `0.65`) |
| `0x0318` | `PID_MIN_GAIN` | RW | `0x0000A666` | Lower output clamp in Q16.16 (default `0.65`) |
| `0x031C` | `PID_MAX_GAIN` | RW | `0x00016666` | Upper output clamp in Q16.16 (default `1.40`) |
| `0x0320` | `PID_SETPOINT` | RW | `0x00010000` | Normalized laser power setpoint in Q16.16 (default `1.00`) |
| `0x0324` | `PID_BIAS` | RW | `0x00010000` | Feedforward nominal bias in Q16.16 (default `1.00`) |
| `0x0328` | `PID_KT_PYRO` | RW | `0x00000027` | Pyrometer trim gain `kt` in Q16.16 / K (default `39`) |
| `0x032C` | `PID_TEMP_CFG` | RW | `0x012C012C` | `[15:0]` `temp_ref_k` (K), `[31:16]` `sw_temp_meas_k` (K; max-gated with external sensor) |
| `0x0330` | `PID_SW_MEAS` | RW | `0x00010000` | Signed Q16.16 software-injected photodiode measurement |
| `0x0334` | `PID_DRIVE_OUT` | RO | `0x00000000` | Signed Q16.16 `aom_drive_q16` (forced `0` on interlock or `T >= 1687 K`) |
| `0x0338` | `PID_INTEG_OUT` | RO | `0x00000000` | Signed Q16.16 integrator state `integ_q16` |
| `0x033C` | `PID_URAW_OUT` | RO | `0x00000000` | Signed Q16.16 pre-clamp control output `u_raw_q16` |

---

## Block 4 (`0x0400 – 0x04FF`): 8-Channel 20-Bit SPI DAC HV Controller (`spi_dac_hv_ctrl.v`)

**BOM:** `S1.2-03, S1.3-03, S2.3-04, S3.2-02, S6.7-02, S6.10-03, S6.10-04`

| Offset | Name | Access | Reset | Bit Fields & Description |
| :--- | :--- | :---: | :---: | :--- |
| `0x0400` | `SPI_CTRL` | RW | `0x0004FF02` | `[0]` `start_update` (W1P), `[1]` `update_all`, `[15:8]` `ch_update_mask[7:0]`, `[31:16]` `sclk_div[15:0]` |
| `0x0404` | `SPI_STATUS` | RO | `0x00000004` | `[0]` `busy`, `[1]` `done_sticky`, `[2]` `hw_hv_clamp`, `[3]` `clamp_zero_seq_done`, `[7:4]` `cur_ch`, `[31:8]` `last_tx_frame[23:0]` |
| `0x0410..0x042C` | `SPI_DAC_CH0..7` | RW | `0x00000000` | `[19:0]` 20-bit DAC code for channel `0..7` (`0x0410 + 4*ch`; forced `0` when `hw_hv_clamp=1`) |

---

## Block 5 (`0x0500 – 0x05FF`): Cryo MUX Multi-Tone DDC Controller (`cryo_mux_ddc_ctrl.v`)

**BOM:** `S6.6-06, S6.11-01` (`N_CH = 8` default, parameterizable up to `32` tones)

| Offset | Name | Access | Reset | Bit Fields & Description |
| :--- | :--- | :---: | :---: | :--- |
| `0x0500` | `DDC_CTRL` | RW | `0x00C80700` | `[0]` `enable`, `[1]` `soft_clear` (W1P), `[2]` `mf_en`, `[3]` `sw_adc_push` (W1P), `[12:8]` `num_ch_m1[4:0]`, `[31:16]` `win_len[15:0]` (default `200` = `2.0 us @ 100 MSPS`) |
| `0x0504` | `DDC_STATUS` | RO | `0x00000000` | `[0]` `busy`, `[1]` `readout_done_sticky`, `[2]` `m_axis_tvalid`, `[15:8]` `sample_cnt[7:0]`, `[31:16]` `window_count[15:0]` |
| `0x0508` | `DDC_QUBIT_MASK` | RO | `0x00000000` | `[N_CH-1:0]` Qubit readout discrimination bitmask (`1 = |1>`, `0 = |0>`) |
| `0x050C` | `DDC_CH_SEL` | RW | `0x00000000` | `[4:0]` Channel selector `0..N_CH-1` for `0x0510..0x0528` |
| `0x0510` | `DDC_PHASE_INC` | RW | `0x00000000` | `[23:0]` 24-bit NCO phase increment for selected channel (write commits) |
| `0x0514` | `DDC_ROT_COEFF` | RW | `0x00007FFF` | `[15:0]` signed `rot_cos` Q1.15, `[31:16]` signed `rot_sin` Q1.15 (write commits) |
| `0x0518` | `DDC_THRESH` | RW | `0x00000000` | Signed 32-bit rotated-axis threshold for selected channel (write commits) |
| `0x051C` | `DDC_SW_ADC` | RW | `0x7FFF0000` | `[15:0]` signed ADC sample, `[31:16]` signed Q1.15 matched-filter weight (for CSR injection) |
| `0x0520` | `DDC_RES_I` | RO | `0x00000000` | Signed 32-bit integrated I result for selected channel |
| `0x0524` | `DDC_RES_Q` | RO | `0x00000000` | Signed 32-bit integrated Q result for selected channel |
| `0x0528` | `DDC_RES_PROJ` | RO | `0x00000000` | Signed 32-bit rotated-axis projection for selected channel |

---

## Block 6 (`0x0600 – 0x06FF`): BOED Q16.16 Accelerator Wrapper (`../boed_fpga/boed_q16_core.v`)

**BOM:** `S6.11-01, S8.3-03` (read-only instantiation of v7.2 verified `boed_q16_core`)

| Offset | Name | Access | Reset | Bit Fields & Description |
| :--- | :--- | :---: | :---: | :--- |
| `0x0600` | `BOED_CTRL` | RW | `0x00000000` | `[0]` `sprt_start` (W1P), `[1]` `sprt_reset_llr` (W1P), `[2]` `step_start` (W1P), `[3]` `ddc_autofeed_en` (routes `cryo_mux_ddc_ctrl` AXI4-Stream directly into SPRT), `[15:8]` `step_idx[7:0]` |
| `0x0604` | `BOED_STATUS` | RO | `0x00000000` | `[0]` `busy`, `[1]` `step_done_sticky`, `[2]` `sprt_done_sticky`, `[3]` `sprt_decision_valid`, `[4]` `sprt_donor_present`, `[31:16]` `cycle_count` (`584` cycles per Stage-2 BOED step) |
| `0x0608` | `BOED_SPRT_Y` | RW | `0x00000000` | Stage-0 SPRT measurement `sprt_y_q16` |
| `0x060C` | `BOED_SPRT_HALF` | RW | `0x00000000` | Stage-0 SPRT `sprt_half_sig_q16` |
| `0x0610` | `BOED_SPRT_SCALE` | RW | `0x00010000` | Stage-0 SPRT `sprt_scale_q16` |
| `0x0614` | `BOED_SPRT_THRESH` | RW | `0x00020000` | Stage-0 SPRT `sprt_thresh_q16` |
| `0x0618` | `BOED_SPRT_LLR` | RO | `0x00000000` | Stage-0 SPRT accumulated `sprt_llr_q16` |
| `0x061C` | `BOED_PRIOR_ADDR` | RW | `0x00000000` | `[9:0]` Posterior SRAM prior bin address (`0..1000`) |
| `0x0620` | `BOED_PRIOR_DATA` | RW | `0x00000000` | Writing commits `prior_load_lp_q16` to `BOED_PRIOR_ADDR` |
| `0x0624` | `BOED_F_INIT_HZ` | RW | `0x00007530` | Signed 32-bit `f_init_hz` |
| `0x0628` | `BOED_F_PROBE_HZ` | RW | `0x00007530` | Signed 32-bit `f_probe_hz` |
| `0x062C` | `BOED_Y_MEAS_Q16` | RW | `0x00000000` | Signed Q16.16 `y_meas_q16` |
| `0x0630` | `BOED_INV_GAMMA` | RW | `0x00004189` | Unsigned `inv_gamma_q24` |
| `0x0634` | `BOED_INV_2VAR` | RW | `0x00010000` | Signed `inv_2var_q16` |
| `0x0638` | `BOED_FISHER_CFG` | RW | `0x57802416` | `[15:0]` `delta_fisher_q4`, `[31:16]` `max_off_q4` |
| `0x063C` | `BOED_MU_OFF_Q8` | RO | `0x00000000` | Posterior mean frequency offset `mu_off_q8` |
| `0x0640` | `BOED_STD_Q4` | RO | `0x00000000` | `[15:0]` Posterior standard deviation `std_q4` |
| `0x0644` | `BOED_NEXT_PROBE` | RO | `0x00000000` | Fisher optimal next probe offset `next_probe_off_q8` |
