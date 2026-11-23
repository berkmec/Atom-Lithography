# Exp149 (H167): Sentezlenebilir `Q16.16 BOED-FPGA` Verilog RTL ve Sıfır-Bağımlılıklı İnteraktif HTML5 Dijital İkiz

**Deney / Hipotez:** `exp149_boed_verilog_rtl_and_interactive_twin` (`H167`)  
**RTL Dizini:** `rtl/boed_fpga/` (`10` dosya: `4` sentezlenebilir `.v`, `2` ROM `.hex`, `golden_vectors.mem`, `tb_boed_q16_core.v`, `zu48dr_boed_250mhz.xdc`, `README.md`)  
**İnteraktif Dijital İkiz:** `docs/digital_twin_interactive.html` (**`66,6 KB`** [`66.554` bayt, `Exp151 v7.0` yenilemesi; ilk `Exp149` Aşama-A sürümü `53,0 KB`], `5` sekme, sıfır harici CDN/HTTP)  
**Veri & Görsel:** `results/exp149_boed_verilog_rtl_and_interactive_twin/{predictions_exp149.json, exp149.json, fig_exp149_rtl_fpga_arch.png}` (`2400×1400`)

---

## 1. Epistemik Sınır ve Dürüst Doğrulama Beyanı

| Bileşen | Epistemik Etiket | Doğrulama Kapsamı |
| :--- | :--- | :--- |
| `rtl/boed_fpga/` IEEE 1364-2005 Verilog RTL ve `ZU48DR` kaynak bütçesi | `{Model}` / `{Sayısal-Simülasyon}` / `{RTL-Structural-Verified}` | `no_external_eda_sim = true`, `no_lab_measurement_rtl = true` (makinede `iverilog`/`verilator`/`vivado` kurulu değildir; yapısal sentez linter'ı, port/bit-genişliği denetleyicisi ve çevrim-doğru bit-kesin Python eş-doğrulamasıyla denetlenmiştir) |
| `docs/digital_twin_interactive.html` içinde gömülü `S1–S9` CAD/BOM/qLDPC/GRAPE/Emniyet | `{Model}` / `{Varsayım}` | `M0` tasarım aşaması (`Exp151 v7.0` yenilemesiyle `BOM v7.0` `180` parça / `10-RFQ` + `Exp147/148/150` ve `v7_digital_twin_cert.json` kanonik `SHA-256` çapalı) |
| `docs/digital_twin_interactive.html` içinde gömülü `ibm_marrakesh` (`156Q`) sekmesi | **`{Canlı-Donanım-IBM-QPU}`** | Gerçek `156`-kübitlik IBM Heron r2 işlemci verisi (`job_id = dc1tdo2nj2vs73dfrfl0`, `0` gizli anahtar sızıntısı) |

> `Yazar != Denetçi` kuralı gereği kapanış onayı (`KABUL`) sıfır-bağlamlı `Carbon` denetimine aittir.

---

## 2. Sentezlenebilir IEEE 1364-2005 Verilog RTL Mimarisi (`rtl/boed_fpga/`)

`Exp140` (`src/machine_control/fpga_boed_dsp.py`) bit-kesin `Q16.16` Bayesyen Eniyilemeli Deney Tasarımı (`BOED`) hızlandırıcısı `4` temiz sentezlenebilir IEEE 1364-2005 Verilog modülüne indirgenmiştir (`894` satır toplam sentezlenebilir RTL):

| Dosya | Satır (`wc -l`) | Görev ve Zamanlama |
| :--- | :---: | :--- |
| `boed_lut_rom.v` | `82` | Çift-portlu `512`-girdili BRAM36 `Q16.16` ROM + `8`-bit doğrusal enterpolasyon (`2` çevrim gecikme @ `250 MHz`) |
| `boed_isqrt_cordic.v` | `66` | `16`-aşamalı ardışık (pipelined) geri-yüklemeli tamsayı karekök (`32b → 16b`, `1` sonuç/çevrim, `0` LSB hata) |
| `boed_q16_core.v` | `574` | `4`-şeritli SIMD `Q16.16` çekirdek + `4`-çevrim (`16,0 ns`) Stage-0 SPRT + `floor_div_s48` + **`584`-çevrim (`2,336 µs`)** Stage-2 BOED FSM |
| `boed_top_16ch.v` | `172` | `16` paralel `boed_q16_core` (`64` toplam SIMD şeridi) + `128b` giriş / `96b` çıkış `AXI4-Stream` sarmalayıcı ve öncelikli hakem |
| `rom_loglik_p0.hex` / `p1.hex` | `512` × 2 | `build_lorentzian_lut_q16()[:512]` (`guard=0x000001C4`) ve `build_exp_neg_lut_q16()[:512]` (`guard=0x00000000`) |
| `golden_vectors.mem` | `64` | `8` farklı frekans izleme yörüngesinden (`8` adım/yörünge) üretilmiş `256`-bit uyaran + beklenen altın vektör paketi |
| `zu48dr_boed_250mhz.xdc` | `44` | Xilinx `xczu48dr-ffvg1517-2-e` `create_clock -period 4.000` (`250 MHz`), I/O gecikme ve `16`-çevrim çoklu-çevrim bölme kısıtları |
| `tb_boed_q16_core.v` | `187` | `golden_vectors.mem` yükleyen kendi kendini sınayan IEEE-2005 testbench (`cycle_count == 584` ve `0` LSB doğrulaması) |

### Kesin `584`-Çevrim Boru Hattı ve `ZU48DR` Kaynak Bütçesi (`16` Kanal)

- **Stage-0 SPRT Erken İptal:** **`4` çevrim = `16,0 ns`** (`C1: Sub → C2: DSP48 Mul → C3: Q16 Shift → C4: LLR Acc & Threshold`).
- **Stage-2 BOED (`1.001` ızgara kutusu, `P = 4` SIMD şerit):**
  - `S_PASS1` (Lorentzian LUT + artık² + doygun int32 log-sonsal + `max_lp`): `251` vuruş + `12` boru hattı = **`263` çevrim (`1.052 ns`)**
  - `S_PASS2` (`exp(-x)` LUT + `48`-bit DSP48E2 `Z, M1, M2` birikimi): `251` vuruş + `14` boru hattı = **`265` çevrim (`1.060 ns`)**
  - `S_POST` (`floor_div_s48` + `16`-aşamalı `isqrt` + Fisher argmax): **`56` çevrim (`224 ns`)**
  - **Toplam:** **`263 + 265 + 56 = 584` çevrim = `2,336 µs @ 250 MHz`** (`260 µs` RF ince prob süresinin yalnızca `%0,9`'u!).
- **Xilinx ZU48DR RFSoC (`16` kanal):** `448 / 4.272` `DSP48E2` (**`%10,49`**), `64 / 1.080` `BRAM36` (**`%5,93`**), `67.200 / 425.280` `LUT` (**`%15,80`**), `81.600 / 850.560` `FF` (**`%9,59`**), toplam kart gücü `37,98 W` (`300 K` rafta, **`0,0 W` kriyo ısı yükü**).

> **Bit-Kesin Eş-Doğrulamada Yakalanan Gerçek Hata:** İlk eş-doğrulama koşusunda `u_exp_lut` kuyruk/koruma sabiti (`exp(-16) × 65536 = 0,0074 → 0`) yanlışlıkla `7` olarak verilmişti ve sonsal ortalama sapmasına yol açtı; bit-kesin doğrulayıcı bu sabit hatasını hemen yakaladı ve `32'h00000000` düzeltmesiyle tüm **`64/64` altın vektör `0 LSB`** eşitliğine oturdu!

---

## 3. Sıfır-Bağımlılıklı Canlı İnteraktif HTML5 Dijital İkiz (`docs/digital_twin_interactive.html`)

`build_interactive_twin.py` tüm sayıları doğrudan diskteki birincil JSON'lardan (`exp128`, `exp136`, `exp140..150`, `ibm_qpu_live_results.json`, `cad_verification.json`, `BOM_DETAILED.csv v7.0`) okuyarak tek-dosya (**`66,6 KB`** [`66.554` bayt, `Exp151 v7.0` yenilemesi; ilk `Exp149` Aşama-A derlemesi `53,0 KB`], `0` harici CDN/HTTP bağlantısı) çevrimdışı çalışabilir karanlık temalı mühendislik web uygulamasını üretir:

1. **Sekme 1 — Etkileşimli Parametre Gezgini:** `S_ε`, `Q_r`, `f*`, `N_mux`, Wafer (`W1/W2/W3`), QEC Kodu (`Surface Code` / `qLDPC [[144,12,12]]` / `[[288,12,18]]`) ve modüler opsiyon (`+S7.SAFETY`, `+Option-Q`, `+Option-HPC`; Faz-1 `Base+Safety $5,39M [%4,67]` vs `v7 Full $5,69M [%5,22]`) kontrolleri değiştikçe `F_Bell`, `p_2q`, `Λ`, `100L` kriyostat, `$/L_sys`, `$/L_fab`, `M3` BOM, `P(>100M)`, `20 mK` ısı yükü ve log-ölçekli HTML5 Canvas grafiği anında güncellenir.
2. **Sekme 2 — Tıklanabilir `S1–S9` Makine Mimarisi:** `CAD v6.0` (`199` parça, `1.108,137 kg` şasi + `355,0 kg` tesis emniyeti, `0/19.701` çakışma) ve **`BOM v7.0`** (`180` parça, `10-RFQ`) verileriyle etkileşimli SVG alt-sistem inceleyici.
3. **Sekme 3 — Canlı `ibm_marrakesh` (`156Q`) Donanım Sekmesi:** Gerçek `8`-noktalı Ramsey kosinüs saçağı (`1,02–8,00 µs`, `q2 -4,52 kHz` doğal kayma), `3`-noktalı `Q16.16 BOED` (`1,6 Hz` vs `FP64`), `C1` Bare/Echo/XY4 (`+59,5 pp`) / Bell `0,9733` ve `C2` `d=3` (`7,83×`, post-sel `0/7.451`) Canvas grafikleri.
4. **Sekme 4 — Verilog RTL ve `584`-Çevrim FPGA Boru Hattı:** `4`-çevrim SPRT + `584`-çevrim FSM zaman diyagramı, `ZU48DR` kaynak çubukları ve bit-kesin doğrulama tablosu.
5. **Sekme 5 — `v7.0` Bilimsel Kapanış & Emniyet (`Exp147/148/150`):** `Exp147` FeMoco (`16` kriyo, `37,1×`) / RSA-2048 (`291` kriyo, `52,7×`), `Exp148` `¹²¹Sb` `Q-Echo-8` (`0,5800 → 0,99908`, `455,5×` ↓) ve `Exp150` `25` FMEA (`max RPN 280 → 42`) + `S7.SAFETY` tablosu.

---

## 4. Ön-Kayıtlı Karar Tablosu (`RV1 – RV7`: `7/7 PASS`)

| Karar Kimliği | Ölçülen Sonuç | Eşik | Durum |
| :--- | :--- | :--- | :---: |
| `RV1_SYNTHESIZABLE_RTL_LINT_ZERO_VIOLATIONS` | `4` modül (`894` LOC: `82+66+574+172`), `0` yasak yapı, `0` blok/port/genişlik hatası (`4` alt-modül örneği) | `0` ihlal | `PASS` |
| `RV2_ROM_HEX_BIT_EXACT_PARITY` | `rom_loglik_p0.hex` (`512`) + `rom_loglik_p1.hex` (`512`) = **`0` bit fark** | `0` bit fark | `PASS` |
| `RV3_GOLDEN_VECTORS_64_ZERO_LSB_PARITY` | `N=64` BOED (`mu/std/next = 0 LSB`), `N=1.000` `isqrt = 0 LSB`, `N=64` SPRT `= 0 LSB` | `0` LSB | `PASS` |
| `RV4_CYCLE_COUNT_584_AND_TIMING_XDC` | `584` çevrim (`2,336 µs @ 250 MHz`), SPRT `4` çevrim (`16,0 ns`), XDC `4,000 ns` | `584` cyc & `4,0 ns` | `PASS` |
| `RV5_ZU48DR_16CH_RESOURCE_BUDGET_CLOSURE` | `DSP %10,49 < %15`, `BRAM %5,93 < %10`, `LUT %15,80 < %20`, kriyo `0,0 W`, `tb` mevcut | ZU48DR sığar | `PASS` |
| `RV6_INTERACTIVE_HTML5_TWIN_ZERO_CDN_LIVE_DATA` | `docs/digital_twin_interactive.html` (`66,6 KB` `v7.0` / `53,0 KB` ilk derleme), `5` sekme, `0` harici CDN, `9` alt-sistem + canlı `ibm_marrakesh` | `0` CDN + canlı veri | `PASS` |
| `RV7_ARTIFACTS_PORTABILITY_VISUAL_AND_TESTS` | `0` hardcoded yol, `0` sızıntı, `0` GFM hatası, `2400×1400` PNG onaylı, `10/10` test `PASS` | Tam hijyen & test | `PASS` |

---

## 5. Çalıştırma Komutları

```bash
# RTL ROM/altın vektör üretimi, sentez lint, bit-kesin eş-doğrulama ve HTML5 Dijital İkiz derleme
PYTHONPATH=src python3 -B experiments/exp149_boed_verilog_rtl_and_interactive_twin/run_exp149.py

# 2400x1400 4-panelli grafik üretimi (Cairo)
/usr/bin/python3 -B experiments/exp149_boed_verilog_rtl_and_interactive_twin/plot_exp149.py

# Testler
python3 -B -m pytest -p no:cacheprovider -v tests/test_exp149.py
```
