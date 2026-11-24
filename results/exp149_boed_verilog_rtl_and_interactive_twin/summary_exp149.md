# Exp149 (H167): Gerçek EDA Doğrulamalı (`Icarus Verilog` + `Verilator` + `Yosys`) `Q16.16 BOED-FPGA` Verilog RTL ve Sıfır-Bağımlılıklı HTML5 Parametrik Model Gezgini

**Deney / Hipotez:** `exp149_boed_verilog_rtl_and_interactive_twin` (`H167`, sürüm `7.2-real-eda`)  
**RTL Dizini:** `rtl/boed_fpga/` (`12` dosya: `4` sentezlenebilir `.v`, `2` ROM `.hex`, `golden_vectors.mem`, `tb_boed_q16_core.v`, `tb_boed_top_16ch.v`, `zu48dr_boed_250mhz.xdc`, `Makefile`, `README.md`)  
**İnteraktif HTML5 Model Gezgini:** `docs/digital_twin_interactive.html` (**`78,7 KB`** [`78.675` bayt], `5` sekme, sıfır harici CDN/HTTP)  
**Veri & Görsel:** `results/exp149_boed_verilog_rtl_and_interactive_twin/{predictions_exp149.json, exp149.json, baseline_eda_audit.json, yosys_xcup_core_stat.json, yosys_xc7_core_stat.json, yosys_ecp5_core_stat.json, yosys_xcup_top16_stat.json, fig_exp149_rtl_fpga_arch.png}` (`2400×1400`)

---

## 1. Epistemik Sınır ve Gerçek EDA Doğrulama Beyanı

| Bileşen | Epistemik Etiket | Doğrulama Kapsamı |
| :--- | :--- | :--- |
| `rtl/boed_fpga/` IEEE 1364-2005 Verilog RTL | **`{Real-EDA-Verified}`** (`no_external_eda_sim = false`) | Makinede köksüz (rootless) `oss-cad-suite` üzerinden gerçek **Verilator 5.055 (`--lint-only -Wall`, `0` uyarı/hata)**, **Icarus Verilog 14.0 (`-g2012 -Wall`) + `vvp` (`64/64` çeşitli vektör + `4`-kanallı AXI4-Stream `0 LSB` / `584` çevrim)** ve **Yosys 0.71+101 (`check -assert`, `synth_xilinx -family xcup/xc7`, `synth_ecp5`)** bizzat çalıştırılmıştır |
| FPGA kaynak sayımları & zamanlama kapanışı | **`{Yosys-Pre-PnR-Measured}`** (`no_vendor_vivado_pnr = true`, `no_lab_measurement_rtl = true`) | Yosys ön-P&R teknoloji-eşlemeli hücre sayımları (`LUT`, `FF`, `RAMB18E2`/`DP16KD`, `DSP48E2`/`MULT18X18D`) doğrudan ölçülmüş ve analitik Vivado son-P&R tahmininden açıkça ayrılmıştır; satıcı Vivado P&R zamanlama kapanışı ve fiziksel ZU48DR kart ölçümü henüz yapılmamıştır |
| `docs/digital_twin_interactive.html` içindeki `S1–S9` / `ibm_marrakesh` | `{Model}` / **`{Canlı-Donanım-IBM-QPU}`** | `S1–S9` CAD/BOM/qLDPC/GRAPE/Ön Emniyet kavramsal `M0` modellerdir; `ibm_marrakesh` (`156Q`, `job_id = dc1tdo2nj2vs73dfrfl0`) süperiletken bulut QPU kontrol vekilidir (`0` gizli anahtar sızıntısı) |

> `Yazar != Denetçi` kuralı gereği kapanış onayı (`KABUL`) sıfır-bağlamlı `Carbon` denetimine aittir.

---

## 2. Ampirik Taban Çizgisi Denetimi ve Düzeltilen `5` Gerçek Donanım Hatası

`boed_q16_core.v` dosyasına tek bir satır dokunulmadan önce, köksüz `oss-cad-suite` kurulumuyla özgün RTL üzerinde doğrudan `iverilog + vvp` ve `verilator --lint-only -Wall` çalıştırılarak **5 gerçek donanım/simülasyon hatası** ampirik olarak kanıtlanmış (`baseline_eda_audit.json`) ve kök-nedende onarılmıştır:

| # | Konum | Ampirik Taban Hatası (Önce) | Kök-Neden Onarımı (Sonra) |
| :---: | :--- | :--- | :--- |
| **1** | `boed_q16_core.v` `L455–470` | Aynı `always @(posedge clk)` bloğunda `max_lp_reg`'e `4` şeritli yarışan `<=` ataması (son şerit önceki büyük değeri ezer) | Birleşik `4`-yollu karşılaştırıcı ağacı (`lane01_max`, `lane23_max`, `beat_max`) ile tek temiz `max_lp_reg <= beat_max` |
| **2** | `boed_q16_core.v` `L483–486` vs `L201–211` | `S_PASS2` içinde `1`-çevrim BRAM okuma gecikmesi uyumsuzluğu: tüm `64/64` vektörde sistematik **`+10.240 LSB` (`+40,00 Hz` = `+1` vuruş / `4` şerit)** ortalama kayması, `0.` vuruşta bayat `0` ağırlığı ve `250.` vuruşun düşmesi | `p2_rd_valid`, `p2_rd_beat_idx`, `p2_rd_act` + `33`-bit taşma-güvenli `max_lp - bank_rd_data` boru hattı ile `0..250` vuruşlarının `1:1` hizalanması |
| **3** | `boed_q16_core.v` `L268–281`, `L519–536` & `XDC L35–38` | Sahte tek-çevrim birleşik `48b/64b` `/` bölme işleci + `48`-bit `(acc_m2 <<< 16)` kırpması + `32`-bit `post_ex2_q16` / `post_mean_b_q8^2` taşması (`std_q4 = 0` bozulması) + sahte `set_multicycle_path -setup 16` | **Sıfır `/` işleci!** `3` paralel gerçek bit-seri geri-yüklemeli kaydır-çıkar (`18 / 21 / 35` çevrim) tam sayı bölme FSM'i + `36b/44b` taşma-güvenli varyans + XDC çok-çevrim muafiyetinin kaldırılması |
| **4** | `boed_q16_core.v` `L502–504` | Tek çevrimde zincirli `48b * 16b * 16b` çarpma + `4`-yollu `48`-bit toplama | `df^2` ön-kayıt + tek-DSP çarpım kaydı + ikili `48`-bit toplama ağacı + son biriktirme boru hattı (`250 MHz` temiz) |
| **5** | `boed_q16_core.v` `L324` & `tb_boed_q16_core.v` | Ters Fisher işareti `next_sign_neg = ~r_step_idx[0]` (`next_probe_off_q8` tüm `64` adımda zıt işaret) + `tb` yükselen kenar yarışı (`64/64` vektörde `mu_off_q8 = x`) + Verilator `-Wall` `40` uyarı | `next_sign_neg = r_step_idx[0]` düzeltmesi + temiz `negedge clk` uyaranı + sıfırlamasız gerçek BRAM çıkarımı + **`0` Verilator `-Wall` uyarısı** |

---

## 3. Gerçek EDA Simülasyon ve Yosys Sentez Sonuçları

### 3.1. `rtl/boed_fpga/` Modülleri ve `Verilator` / `Icarus Verilog` Doğrulaması (`1.193` Sentezlenebilir LOC)

| Modül / Testbench | Satır (`wc -l`) | Gerçek EDA Doğrulama Çıktısı |
| :--- | :---: | :--- |
| `boed_lut_rom.v` | `95` | `verilator -Wall`: `0` uyarı; Yosys: `1× RAMB18E2` / `RAMB18E1` / `DP16KD`, `0` bit fark (`1.024/1.024` ROM sözcüğü) |
| `boed_isqrt_cordic.v` | `88` | `verilator -Wall`: `0` uyarı; `vvp`: `13/13` köşe durumu `0 LSB` / `16` çevrim (`+ 1.000` Python vektörü) |
| `boed_q16_core.v` | `833` | `verilator -Wall`: `0` uyarı; `0` `/` işleci; `vvp`: **`64/64` çeşitli vektör (`8` rejim) `0 LSB` / `584` çevrim (`2,336 µs`)** + `8/8` SPRT `0 LSB` / `4` çevrim (`16,0 ns`) |
| `boed_top_16ch.v` | `177` | `verilator -Wall`: `0` uyarı; `yosys check -assert`: `0` hata/latch; `vvp` (`tb_boed_top_16ch.v`): **`4/4` eşzamanlı AXI4-Stream kanal + geri-basınç + SPRT `0 LSB` / `584` çevrim** |

Genişletilmiş `golden_vectors.mem` (`N = 64` adet `288`-bit vektör = `8` rejim × `8` ardışık adım): `clean_neg`, `clean_pos`, `crowded_doublet`, `edge_of_grid_left` (`-4.650 Hz`, `ex2_q16 > 1,48×10¹⁰ > 2³²`), `edge_of_grid_right` (`+4.720 Hz`), `high_noise` (`σ_n = 0,35`), `zero_signal_dark_site`, `sharp_snr_int32_sat` (`σ_n = 0,03`).

### 3.2. Gerçek Ölçülen Yosys Ön-P&R Sentez Sayımları (`xcup`, `xc7`, `ecp5`) vs Analitik Vivado Tahmini

| Hedef | Yosys Komutu (`pre-P&R`) | `LUT` (+`SRL16E`) | `FF` | `BRAM` (`BRAM36`-eşd.) | `DSP` / `MULT` | `CARRY` | `ZU48DR` Doluluğu |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :---: |
| `boed_q16_core` (`xcup`) | `synth_xilinx -family xcup` | `6.357` (`6.229+128`) | `3.690` | `12 RAMB18E2` (`6,0`) | `99 DSP48E2` | `1.076` | `%1,49` LUT / `%2,32` DSP |
| `boed_top_16ch` (`xcup`) | `synth_xilinx -family xcup` | **`102.886`** (`100.838+2.048`) | **`59.157`** | **`192 RAMB18E2` (`96,0`)** | **`1.584 DSP48E2`** | `17.216` | **`%24,19` LUT / `%6,96` FF / `%8,89` BRAM / `%37,08` DSP** |
| `boed_q16_core` (`xc7`) | `synth_xilinx -family xc7` | `5.467` (`5.339+128`) | `3.080` | `12 RAMB18E1` (`6,0`) | `99 DSP48E1` | `935` | 7-Serisi referans |
| `boed_q16_core` (`ecp5`) | `synth_ecp5` | `3.871` (`LUT4`) | `4.448` (`TRELLIS_FF`) | `12 DP16KD` (`6,0`) | `106 MULT18X18D` | `2.252` (`CCU2C`) | Lattice ECP5 referans |
| *Analitik Vivado Tahmini (`16` kanal, `fpga_boed_dsp.py`)* | *Model tahmini (son-P&R DSP paketleme varsayımı; Vivado koşulmadı)* | *`67.200`* | *`81.600`* | *`64 BRAM36`* | *`448 DSP48E2`* | *—* | *`%15,80` LUT / `%9,59` FF / `%5,93` BRAM / `%10,49` DSP* |

> **Dürüst Karşılaştırma:** Gerçek Yosys ön-P&R sentezi, paylaşımsız tam `32×32` `Q16.16` çarpmaların çekirdek başına `99 DSP48E2` (`16` kanalda `1.584 / 4.272 = %37,08`) ve `12 RAMB18E2` (`16` kanalda `96 BRAM36-eq = %8,89`) tükettiğini göstermiştir; önceki analitik el tahmini (`28 DSP/çekirdek`) `32×32` DSP bölünmesini iyimser varsaymış, buna karşın FF sayısını olduğundan fazla tahmin etmiştir (`81,6k` vs ölçülen `59,2k`). Gerçek Yosys ön-P&R sayımlarının tamamı `ZU48DR` içine rahatça sığar (`0,0 W` kriyo ısı yükü).

---

## 4. Karar Tablosu (`RV1 – RV8`: `8/8 PASS`)

| Karar Kimliği | Ölçülen Gerçek EDA Sonucu | Eşik | Durum |
| :--- | :--- | :--- | :---: |
| `RV1_SYNTHESIZABLE_RTL_LINT_ZERO_VIOLATIONS` | `4` modül (`1.193` LOC), `0` yasak yapı, **`0` `/` bölme işleci**, **`0` Verilator `-Wall` uyarısı** (`core + top16`) | `0` ihlal/uyarı | `PASS` |
| `RV2_ROM_HEX_BIT_EXACT_PARITY` | `rom_loglik_p0.hex` (`512`) + `rom_loglik_p1.hex` (`512`) = **`0` bit fark** | `0` bit fark | `PASS` |
| `RV3_GOLDEN_VECTORS_64_ZERO_LSB_PARITY` | Gerçek `iverilog + vvp`: `64/64` (`8` rejim) `mu/std/next = 0 LSB`, `8/8` SPRT `0 LSB`, `13/13` `isqrt` `0 LSB`, `4/4` `top16` AXI4-Stream kanal `0 LSB` | `0` LSB | `PASS` |
| `RV4_CYCLE_COUNT_584_AND_TIMING_XDC` | Gerçek `vvp`: `584` çevrim (`2,336 µs @ 250 MHz`), SPRT `4` çevrim (`16,0 ns`), XDC `4,000 ns` (`0` sahte multicycle muafiyeti) | `584` cyc & `4,0 ns` | `PASS` |
| `RV5_ZU48DR_16CH_RESOURCE_BUDGET_CLOSURE` | Gerçek Yosys `xcup_top16`: **`%37,08` DSP, `%8,89` BRAM36-eq, `%24,19` LUT, `%6,96` FF** (ZU48DR sığar, `0,0 W` kriyo) | ZU48DR sığar | `PASS` |
| `RV6_INTERACTIVE_HTML5_TWIN_ZERO_CDN_LIVE_DATA` | `docs/digital_twin_interactive.html` (`78.675` bayt), `5` sekme, `0` harici CDN, gerçek EDA + `ibm_marrakesh` verisi | `0` CDN + canlı veri | `PASS` |
| `RV7_ARTIFACTS_PORTABILITY_VISUAL_AND_TESTS` | `0` hardcoded yol, `0` sızıntı, `0` GFM hatası, `2400×1400` PNG görsel onaylı | Tam hijyen | `PASS` |
| `RV8_REAL_EDA_IVERILOG_VERILATOR_YOSYS` | `Verilator 5.055` + `Icarus Verilog 14.0` + `Yosys 0.71+101` (`check -assert` + `xcup/xc7/ecp5/top16`) `100% PASS` | Tüm gerçek EDA geçer | `PASS` |

---

## 5. Çalıştırma Komutları

```bash
# Doğrudan RTL üzerinde gerçek Verilator lint + Icarus Verilog simülasyon + Yosys sentez
make -C rtl/boed_fpga all
make -C rtl/boed_fpga synth-xcup synth-xc7 synth-ecp5 synth-top16

# Tam Exp149 boru hattı (gerçek EDA + Yosys + HTML5 Dijital İkiz + 2400x1400 grafik)
PYTHONPATH=src python3 -B experiments/exp149_boed_verilog_rtl_and_interactive_twin/run_exp149.py
/usr/bin/python3 -B experiments/exp149_boed_verilog_rtl_and_interactive_twin/plot_exp149.py

# Testler (gerçek iverilog + verilator + yosys çalıştırır)
python3 -B -m pytest -p no:cacheprovider -v tests/test_exp149.py tests/test_exp140.py
```
