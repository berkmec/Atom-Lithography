# Exp146 (H164): Atom Litografisi Makinesi `v6.0` Master Dijital İkiz ve `SHA-256` Dosya Bütünlüğü Özeti (Provenans)

**Deney / Hipotez:** `exp146_v6_digital_twin` (`H164`)  
**Provenans Özet Dosyası:** `results/exp146_v6_digital_twin/v6_digital_twin_cert.json` *(yalnızca dosya bütünlüğü/provenans özetidir; fiziksel veya mühendislik sertifikasyonu değildir)*  
**Kanonik `v6_digital_twin_cert.json` `SHA-256` (tam 64-hex):**  
`ca3f0e0267263bacb973f46c3cc2d321c0f204075ea232f4094758e1a9abf1d7`  
**IBM QPU Kontrol Vekili Ham Sayım Defteri `ibm_qpu_live_results.json` `SHA-256` (tam 64-hex):**  
`02b7a19d1704662c6424e76f4971e21b04a98d48230a917c9682853b3ca1fc5a`  
**Görsel:** `results/exp146_v6_digital_twin/fig_exp146_v6_digital_twin.png` (`2400×1400`)

---

## 1. Epistemik Sınır ve Kapsam

| Alan | Epistemik Etiket | Gerçek Fiziksel Ölçüm Durumu |
| :--- | :--- | :--- |
| Silikon `³¹P` atom litografisi, `CAD v6.0` (nominal statik geometri), `BOM v6.0`, `D3` GRAPE, `qLDPC`, `Option-Q/HPC`, `auto_recal.py` | `{Model}` / `{Sayısal-Simülasyon}` / `{Varsayım}` / `{Liste-Çapası}` | `no_lab_measurement = true`, `no_supplier_quotes = true` (`TRL 1–2 / M0` tasarım aşaması) |
| **`CellISA v4.0` → OpenQASM 3.0 → `C1/C2/C3` kontrol, DD, Bell, `d=3` QEC ve `Q16.16` BOED (silikon-dışı kontrol vekili)** | **`{Canlı-Donanım-IBM-QPU}`** | **Gerçek 156-kübitlik `ibm_marrakesh` (IBM Heron r2) süperiletken bulut QPU üzerinde yazılım/kontrol vekili olarak çalıştırıldı (`job_id = dc1tdo2nj2vs73dfrfl0`, `32,54 s`, `16 PUB × 4.096 shot`, `0` gizli anahtar sızıntısı; ham sayımlar `Exp146` içinde bağımsız yeniden hesaplandı — silikon `³¹P` atom donanımının fiziksel doğrulaması değildir)** |

> `Yazar != Denetçi` kuralı gereği bu özet yalnızca deneysel/sayısal yürütme çıktısını belgeler; kapanış onayı (`KABUL`) sıfır-bağlamlı `Carbon` denetimine aittir.

---

## 2. Ön-Kayıtlı Karar Tablosu (`DT6_1 – DT6_8`: `8/8 PASS`)

| Karar Kimliği | Konu | Temel Ölçüm | Durum |
| :--- | :--- | :--- | :---: |
| `DT6_1_LEDGER_CAD_BOM_SHA256_LOCK` | `24/24` Defter + Donanım Kilidi | `22` deney (`Exp124–145`) + `CAD v6.0` (`199` parça, `1.108,137 kg`, `0/19.701` çakışma, `40/40` boşluk, `39.536` STL) + `BOM v6.0` (`174` parça, `Base $5,248M` / `Full $5,548M`, `$0,00` köprü, `0,0000 kg` kütle uyumu, `9-RFQ %77,67 / %92,61`) + canlı QPU `SHA-256` | `PASS` |
| `DT6_2_D3_GRAPE_M4_PHYSICAL_CLOSURE` | `D3` GRAPE `M4` Kapı Kapanışı (`Exp143`) | `K=8` Fourier (`0,894 µs` muhaf. / `1,126 µs` yankılı, `%100 <= 300 MHz`, CPTP temiz): yankılı `Q=1e6, S=0,390` `p_2q = %0,3951 <= %0,45`; `S=0,25` `p_2q = %0,3369` (`F_avg = %99,73`, `F_Bell = %99,69`), canlı `Exp138` MWPM `Λ_D3_phys = 2,8253`, `100L` yüzey kodu `679 → 100` kriyostat (`6,79×`) | `PASS` |
| `DT6_3_QLDPC_BB144_SINGLE_CRYOSTAT_REVOLUTION` | `qLDPC [[144,12,12]]` Devrimi (`Exp144`) | `P_cell = 20 µm → L_max = 268,3 µm <= 300 µm` (`0` rezonatör yeniden tasarımı); `f*=%1,5+2MV/m`, `N_cand=8` → `%99,635` blok / `%99,941` `108L` yonga verimi; `D3+` (`%0,30`) `2,1×10⁻⁵/1L`; `120L` tek `LD400` kriyostatta (`108L` = `1` kriyostat, `$63.827/L_sys`, `W3` silikon `$0,0085/L_fab`) | `PASS` |
| `DT6_4_OPTION_Q_AND_S1_MULTI_PLATFORM` | `Option-Q` ve `S1-Multi` (`Exp142`) | `5`-kademe Chebyshev `50 Ω ↔ 3 kΩ` (`0,000375 dB`, `5,20 GHz`); `F_SWAP_rt(³¹P) = 0,98575`; `8.403×–25.122×` bellek ömrü (`+0,78 µW @ 20 mK`); `10 km` `¹⁶⁷Er` `1.352,3 Hz` (`F = 0,9474`); `7,5 keV ¹²¹Sb` `-%41,46` yanal saçılma | `PASS` |
| `DT6_5_OPTION_HPC_ROCEV2_DECODER_CLOSURE` | `Option-HPC` `100G` RDMA (`Exp143`) | `τ_ingest = 777,0 ns`; `d=37` SC E2E `6,339 µs < 6,70 µs` (`backlog-free`); `qLDPC 108L` ortalama E2E `2,3245 µs < 2,62 µs` tek `4U` `$132k` rafta (`2.195 W`, `0,0 W` kriyo) | `PASS` |
| `DT6_6_LIVE_IBM_MARRAKESH_AND_CELLISA40_AUTOREKAL` | `ibm_marrakesh` Kontrol Vekili + `CellISA v4.0` + `auto_recal` (`Exp145`) | `ibm_marrakesh` (`dc1tdo2nj2vs73dfrfl0`, `0` sızıntı, silikon-dışı süperiletken vekil): Bare `0,3325` → Echo `0,9224` → XY4 `0,9280` (`+59,55 pp`), Bell `F = 0,9733`, `d=3` `5,16× / 7,83×` (`postsel 0,000%`), `Q16.16 BOED` `3` nokta `120,106 kHz` (`1,6 Hz` vs FP64); `20` v4.0 / `17` v3.5 opcode; `auto_recal` `4/4 PASS` | `PASS` |
| `DT6_7_V3_TO_V6_EVOLUTION_AND_MODULAR_ECONOMICS` | `v3.0 → v6.0` Evrim ve Modüler Ekonomi | `M3 Base $5,248M` (`P>100M = %4,37`) vs `M3 Full $5,548M` (`P>100M = %4,92`, `FOAK 5y %6,90`); `100L` kriyostat `679 → 100 → 1`; `$/L_sys` `$14,94M → $2,76M → $63,8k` (`234,06×` düşüş) | `PASS` |
| `DT6_8_CRYPTO_V6_CERT_PORTABILITY_AND_TESTS` | `SHA-256` Dosya Bütünlüğü ve Yazılım Regresyonu | Kanonik 64-hex `SHA-256` dosya özeti doğrulandı (`verify_v6_certificate = True` — yalnızca provenans), `0` hardcoded yol, `0` sızıntı, `0` GFM hatası, tüm `28` Atom Litografi regresyon test dosyası %100 geçer | `PASS` |

---

## 3. `v3.0 → v4.0 → v5.0 → v6.0` Evrim ve Modüler Ekonomi Özeti

| Mimari / Yapılandırma | Parça (BOM / CAD) | Makine Kütlesi (`kg`) | Nominal BOM (`$`) | Program `P50` (`$M`) | `P(>100M)` (`%`) | `100L` Kriyostat | `$/L_sys` (`5y P50`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `v3.0` Base (Yalnız `M1–M3`) | `145 / 143` | `956,903` | `$4.189.600` | `—` | `—` | `—` | `—` |
| `v4.0` Base (`Exp135`, `S5.5` + `PT420`) | `159 / 170` | `993,267` | `$4.609.600` | `—` | `—` | `—` (`Λ < 1`) | `—` |
| `v5.0` Base (`Exp141`, `D2` SC `d=99`) | `167 / 189` | `1.034,937` | `$5.247.800` | `$34,50M` | `%4,37` | `679` | `$14.939.541` |
| `v6.0` `+Option-HPC` (`D3` GRAPE SC `d=33–37`) | `170 / —` | `1.098,937` | `$5.379.800` | `$35,26M` | `%4,60` | `100` (`6,8×`) | `$2.759.442` (`5,4×`) |
| `v6.0` `+Option-Q` (`S9.4` qRAM + `S1.7` Multi) | `171 / —` | `1.044,137` | `$5.415.800` | `$35,49M` | `%4,67` | `—` | `—` |
| **`v6.0` Full (`Option-Q` + `Option-HPC` + `qLDPC 108L`)** | **`174 / 199`** | **`1.108,137`** | **`$5.547.800`** | **`$36,25M`** | **`%4,92`** *(FOAK `%6,90`)* | **`1`** (**`679×`**) | **`$63.827`** (**`234,1×`**) |

---

## 4. `SHA-256` Dosya Bütünlüğü Özeti (`24/24` Birincil + `1` IBM QPU Kontrol Vekili — Yalnızca Provenans)

Tüm `24` birincil artefakt (`Exp124–Exp145` + `cad_verification.json` + `BOM_DETAILED.csv`) ve `ibm_qpu_live_results.json` disk üzerinden okunarak `v6_digital_twin_cert.json` içine tam 64-hex `SHA-256` ile gömülmüştür *(not: `SHA-256` özeti yalnızca dosya bütünlüğü ve veri provenansı kaydıdır; fiziksel veya mühendislik doğrulaması/sertifikasyonu değildir)*. Kanonik JSON (`sort_keys=True, separators=(",", ":")`) özeti:

- **`v6_digital_twin_cert.json` `SHA-256`:** `ca3f0e0267263bacb973f46c3cc2d321c0f204075ea232f4094758e1a9abf1d7`
- **`cad_verification.json` (`CAD v6.0`) `SHA-256`:** `1e2f9dae2fdaa891be663aafcad10e603610ffde2813cd5e19b13ddcf1fbecf9`
- **`BOM_DETAILED.csv` (`BOM v6.0`) `SHA-256`:** `a5b013df2702ba076df2606a6a580f7f084d1bbe6c01c1535e0b814516835b64`
- **`ibm_qpu_live_results.json` (`ibm_marrakesh`) `SHA-256`:** `02b7a19d1704662c6424e76f4971e21b04a98d48230a917c9682853b3ca1fc5a`
- **Tarihsel `v5_digital_twin_cert.json` (korundu, dokunulmadı):** `2828e8ce8d9388f7cba5490b2d05add930aadc5fe6d3ba4295f0380f816d43d1`

---

## 5. Çalıştırma Komutları

```bash
# Master v6.0 Dijital İkiz ve v6_digital_twin_cert.json üretimi
PYTHONPATH=src python3 -B experiments/exp146_v6_digital_twin/run_exp146.py

# 2400x1400 4-panelli grafik üretimi (Cairo)
/usr/bin/python3 -B experiments/exp146_v6_digital_twin/plot_exp146.py

# Exp146 testleri
python3 -B -m pytest -p no:cacheprovider -v tests/test_exp146.py
```
