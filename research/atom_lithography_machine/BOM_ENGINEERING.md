# Atom Litografi Makinesi — Parça-Düzeyi Mühendislik BOM Analizi (`BOM_ENGINEERING.md` — `BOM v7.0 / Doküman v7.1`)

> **Epistemik Beyan (`TRL 1–2 / M0`, `no_lab_measurement=true`, `no_supplier_quotes=true`):** Bu belge, kanonik 40 satırlık `BOM.csv` (`SHA-256: cee02adfd207e37bbbc6b66982226b27fa87c2be528ede2b762f72840759cfc2` — kesinlikle değiştirilmemiştir) dosyasının `BOM_DETAILED.csv` altında **`v7.0` için 180 fiziksel parça/alt-montaj satırına** (`167` `M3 v5.0 Base` + `7` `v6.0` Modüler Opsiyon [`4` `Option-Q` + `3` `Option-HPC`] + `6` `v7.0` `S7.SAFETY` sertifikasız ön emniyet tasarım paketi; `169` fiyatlı + `9` `$0` yazılım + `2` `v5.0`'da değiştirilen `$0` çift-sayım önleme satırı) açılmış parametrik maliyet çözümlemesidir. **Hiçbir satır gerçek tedarikçi fiyat teklifi değildir ve `S7.SAFETY` herhangi bir emniyet sertifikasyonu değildir** (`SEMI`, `SEMI S2` için sertifika vermez; `IEC 61508 SIL-3` bağımsız fonksiyonel emniyet değerlendirmesi gerektirir). Tüm USD değerleri satır-genişletilmiş toplamlar olup `{Liste-Çapası}` (`%13,4`), `{Model-Kalibrasyon-Exp114}` (`%42,7`), `{Varsayım}` (`%43,9`) veya `{Program-NRE-Kapsam}` (`S8` yazılım, `$0` donanım) etiketlidir.

**Tarih:** 2026-11-24 *(`v7.1` epistemik temizlik & `v7.0` ön emniyet tasarım kiti entegrasyonu: `M3 Base` ve `M3 v6.0 Full` aynen korundu + `Exp150` `S7.SAFETY-01..06` ön tasarım hedefi eklendi)*  
**Birincil Donanım Şartname Girdileri (Salt-Okunur Doğrulamalı):**
- `results/exp139_epi_cap_process_integration/s56_hardware_spec.json` (`S5.6`: `22,40 kg`, `$67k/$95k/$145k`)
- `results/exp140_cryo_fpga_boed_mux_readout/s65_hardware_spec.json` (`Exp140 S6.5` → BOM `S6.11`: `19,27 kg`, `$456,4k/$629,2k/$925,2k`)
- `results/exp142_option_q_multispecies_qram/s9q_hardware_spec.json` (`Option-Q`: `S1.7-01` + `S9.4-01..03`, `9,20 kg`, `$118k/$168k/$242k`)
- `results/exp143_d3_grape_m4_and_hpc_decoder/s9hpc_hardware_spec.json` (`Option-HPC`: `S9.HPC-01..03`, `64,00 kg`, `$98k/$132k/$181k`, `2.195 W` / `0 W` kriyo)
- `results/exp150_industrial_safety_fmea_hazop/s_safety_spec.json` (`S7.SAFETY-01..06`: `6` kalem, **`355,0 kg`** harici temizoda tesis emniyeti, **`1.090,0 W`**, **`0,0 W` kriyo**, **`$92k/$145k/$220k`** [`M3 v6.0 Full`'ün `%2,61`'i])

---

## 1. Modüler `v7.0` Yapılandırma Matrisi & Şasi-Üstü vs Tesis Kütle Ayrımı

`v7.0` aşamasında **`M1 Base` (`$2.466.120`)**, **`M3 v5.0 Base` (`167` parça, `$5.247.800`)** ve **`M3 v6.0 Full` (`174` parça, `$5.547.800`)** kesinlikle bozulmadan korunmuş, `Exp150` **`S7.SAFETY-01..06`** (`+$145.000`, `355,0 kg` tesis/zemin emniyet suite'i) temiz biçimde eklenmiştir:

- **Kütle Ayrımı (`0,0000 kg` `CAD v6.0` Eşleşmesi):** Makine şasisi üstü (`on-frame`) `CAD v6.0` kütlesi **`1.108,137 kg`** (`199` parça) değişmez; `S7.SAFETY-01..06` (**`355,000 kg`**) harici temizoda zemin sertifikasız `M0` ön emniyet tasarım paketi (`facility-adjacent preliminary safety target`) olarak ayrı tutulur → toplam tesis yükü **`1.463,137 kg`**.
- **Muhafazakâr Brüt vs Potansiyel Başlangıç-Kalemi Çakışma Şeffaflığı:** `S7.SAFETY` (`+$145.000`) tam brüt ön emniyet tasarım bütçesi olarak eklendiğinde `M3 v7.0 Full = $5.692.800` verir. Çekirdek makinedeki başlangıç koruma kalemleri (`S1.6-01/02` `$58k` + `S5.5-04` `$9k` + `S7.1-03` `$2,2k` + `S7.4-04` `$7k` = `$76,2k`) yedekli Katman-1/2 yerine tamamen ikame edilirse net alt sınır `$5.616.600` olur; bütçe planlaması muhafazakâr brüt **`$5.692.800`** üzerinden kilitlenmiştir.

| Yapılandırma | Parça | Donanım Alt (`P10`) | Donanım Nominal (`P50`) | Donanım Üst (`P90`) | Kütle (`Şasi / Tesis`) | `M3 Base` Farkı (`Δ`) | Kullanım & Bütçe Kapsamı |
|---|---:|---:|---:|---:|---|---:|---|
| **`M1 Base` Prototip** *(korundu)* | 167 *(ölçekli)* | `$1.454.996` | **`$2.466.120`** | `$4.400.788` | — | `−$2.781.680` | Tek-demet `³¹P⁺` + `20 mK` DR + `S5.5/S5.6` + `1× ZU48DR` |
| **`M1 + Safety`** *(not)* | 173 *(ölçekli)* | `$1.546.996` | **`$2.611.120`** | `$4.620.788` | `+355,0 kg` tesis | `−$2.636.680` | `M1` + sertifikasız `M0` ön emniyet kiti (`SEMI S2`/`SIL-3` hedef referanslı) |
| **`M3 v5.0` Pilot (`256`-hücre)** | 167 *(8-hat)* | — | **`$4.790.400`** | — | — | `−$457.400` | Kademeli `256`-hücreli `M4` başlangıç seçeneği |
| **`M3 v5.0 Base`** *(korundu)* | **167** | `$3.039.400` | **`$5.247.800`** | `$9.525.900` | `1.034,937 kg / —` | **`$0`** | Çekirdek `1.024`-demetcik + `S5.6` + `S6.5/S6.11` Cryo-MUX |
| **`M3 Base + Safety` *(Faz-1 Önerilen)*** | **173** | `$3.131.400` | **`$5.392.800`** | `$9.745.900` | `1.034,937 / +355,0 kg` | **`+$145.000`** | **+Ön Emniyet Kiti (Sertifikasız `M0`) & `P(Prog>$100M)=%4,67 < %5` (`CU3 PASS`)** |
| **`M3 v6.0 Full` (`Opt-Q + Opt-HPC`)** *(korundu)* | **174** | `$3.255.400` | **`$5.547.800`** | `$9.948.900` | `1.108,137 kg / —` | `+$300.000` | `Base` + `Option-Q` (`+$168k, 9,2 kg`) + `Option-HPC` (`+$132k, 64 kg`) |
| **`M3 v7.0 Full (+Ön Emniyet Kiti, Sertifikasız M0)`** | **180** | **`$3.347.400`** | **`$5.692.800`** | **`$10.168.900`** | **`1.108,137 / +355,0 kg`** | **`+$445.000`** | Tam `v7.0` (Faz-1 `Base+Safety` + Faz-2 `Option-Q/HPC`; toplam `1.463,137 kg`) |

### 1.1 Alt-Sistem Bazlı Tam Uzlaştırma Tablosu (`Exp122` vs `M1 Base` vs `M3 v7.0 Full (+Ön Emniyet Kiti, Sertifikasız M0)`)

| Alt Sistem | Parça Sayısı | `Exp122` Kanonik (`@$720/u`) | `M1 Base` Prototip (Nom `[P10–P90]`) | `M3 v7.0 Full` `BOM_DETAILED` (Nom `[P10–P90]`) | `M3 v7 − Exp122` Farkı (`Δ`) | Farkın Kök Mühendislik Nedeni |
|---|---:|---:|---:|---:|---:|---|
| **S1** Kaynak, Kolon & `S1.7` Multi | 23 | `$237.600` | `$319.750` `[$183k–$585k]` | `$484.000` `[$286k–$858k]` | **`+$246.400`** | `v5` `S1` (`$416k`) + `v6` `Option-Q` `S1.7-01` `S1-Multi` (`+$68k`, `4,80 kg`) |
| **S2** MEMS Çok-Demet Kafa | 18 | `$10.633` | `$147.750` `[$80k–$289k]` | `$775.500` `[$392k–$1.606k]` | **`+$764.867`** | Sabit MEMS maske/DRIE/TSV/bonding NRE (`$370k`) + `Arch-B` `1.024` plakalar + SKY130 |
| **S3** IBIC Algılama | 14 | `$146.081` | `$88.550` `[$48k–$168k]` | `$224.000` `[$120k–$428k]` | **`+$77.919`** | `Exp127` kilitli `100 K` soğuk-ada `16×8` `LTC6268` CSA (`1,2 µs / 1 GΩ`) + trim DAC |
| **S4** Konum & Titreşim | 17 | `$241.200` | `$233.920` `[$142k–$411k]` | `$253.000` `[$152k–$446k]` | **`+$11.800`** | `Exp122` ile `%4,9` uyum (`Renishaw XL-80` + `PI PIMars` UHV piezo + aktif tabla) |
| **S5** Vakum, `S5.5` Flaş & `S5.6` MBE | 24 | `$163.800` | `$358.300` `[$219k–$625k]` | `$433.000` `[$260k–$764k]` | **`+$269.200`** | `v3` UHV + `v4` `S5.5` flaş (`$95k`) + `v5` `S5.6` In-Situ `²⁸Si` MBE (`$95k`, `22,40 kg`) |
| **S6** Kriyo, DR, Mıknatıs, Okuma & MUX | 42 | `$1.578.650` | `$1.171.150` `[$700k–$2.048k]` | `$2.794.100` `[$1.683k–$4.844k]` | **`+$1.215.450`** | `S6.6` (`$680.400`) & `S6.8` (`$720.000`) birebir; `Exp125` + `S6.9/10` + `S6.11` (`+$629,2k`) |
| **S7** Kontrol & **`v7` `S7.SAFETY`** | 20 | `$153.281` | `$104.450` `[$60k–$192k]` | `$349.200` `[$207k–$598k]` | **`+$195.919`** | `v5/v6` `S7` (`$204,2k`) + **`v7.0` `S7.SAFETY-01..06` ön emniyet tasarım hedefi (`+$145k`, `355,0 kg` tesis; sertifikasız `M0`)** |
| **S8** Yazılım & RTL | 9 | `$0` | `$0` | `$0` | **`$0`** | Proje-içi yazılım/RTL (`machine_control`, `CellISA v4.0`, `auto_recal.py`, `fpga_boed_dsp.py`) |
| **S9** Sarf, Yedek & `v6` `S9.4`/`S9.HPC` | 13 | `$0` | `$42.250` `[$22k–$82k]` | `$380.000` `[$246k–$624k]` | **`+$380.000`** | `v3` Yedekler (`$148k`) + `Option-Q` `S9.4` (`+$100k`) + `Option-HPC` `S9.HPC` (`+$132k`) |
| **TOPLAM (`v7.0 Full`)** | **180** | **`$2.531.244`** | **`$2.466.120`** `[$1,45M–$4,40M]` | **`$5.692.800`** `[$3,35M–$10,17M]` | **`+$3.161.556`** | **Uzlaştırma & köprü hatası: `$0,00` (`v6 Full $5.547.800 + $145.000 = $5.692.800`)** |

### 1.2 Kurumsal Delta Köprüsü (`Exp122` → `v5.0 Base` → `v6.0 Full` → `v7.0 Full (+Ön Emniyet Kiti, Sertifikasız M0)`)

| Köprü Adımı | Tutar (USD) | Kütle (`Şasi` / `Tesis`) | Açıklama |
|---|---:|---|---|
| **`Exp122` Merkez Bazı (`3.515,62u @ $720`)** | `$2.531.244` | — | `40` kanonik satır (`BOM.csv` SHA-256 korundu) |
| `+ v3.0` (`+$1.658.356`) + `v4.0` (`+$420.000`) + `v5.0` Net (`+$638.200`) | `+$2.716.556` | `1.034,937 kg` şasi | `S5.6` (`$95k`) + `S6.11` (`$629,2k`) `− $86k` çift-sayım kredisi |
| **`= M3 v5.0 Base` (`167` parça — DEĞİŞMEDİ)** | **`$5.247.800`** | **`1.034,937 kg` şasi** | Çekirdek `1.024`-hücreli taban (`$0,00` sapma) |
| `+ v6.0` `Option-Q` (`+$168.000`, `9,20 kg`) + `Option-HPC` (`+$132.000`, `64,00 kg`) | `+$300.000` | `+73,200 kg` şasi | `s9q_hardware_spec.json` & `s9hpc_hardware_spec.json` birebir |
| **`= M3 v6.0 Full` (`174` parça — DEĞİŞMEDİ)** | **`$5.547.800`** | **`1.108,137 kg` şasi** | **`CAD v6.0` şasi kütlesiyle `0,0000 kg` fark!** |
| `+ v7.0` **`S7.SAFETY-01..06`** (`Exp150` sertifikasız `M0` ön emniyet kiti — `SEMI S2`/`SIL-3` hedef referanslı) | **`+$145.000`** | **`+355,000 kg` tesis** | `s_safety_spec.json` (`$92k/$145k/$220k`, `1.090 W`, `0 W` kriyo) birebir |
| **`= M3 v7.0 Full (+Ön Emniyet Kiti, Sertifikasız M0)` (`180` parça)** | **`$5.692.800`** | **`1.463,137 kg` toplam** | **Köprü & kütle hatası: `$0,00` / `0,0000 kg` (`$50M` sınırının `8,8×` altı)** |

---

## 2. Tedarik Sınıfı ve Epistemik Dağılım (`BOM_DETAILED.csv v7.0`, `180` Parça)

| Tedarik Sınıfı | Parça Sayısı | `M3 v7.0` Alt (`P10`) | `M3 v7.0` Nominal (`P50`) | `M3 v7.0` Üst (`P90`) | `M3 v7.0` Nominal Payı |
|---|---:|---:|---:|---:|---:|
| **`COTS`** (Rafta/Katalog) | 68 | `$1.048.700` | `$1.775.700` | `$3.117.700` | **`%31,2`** |
| **`CUS`** (Özel Üretim, Bilinen Teknoloji) | 63 | `$863.300` | `$1.502.400` | `$2.705.500` | **`%26,4`** |
| **`R&D`** (Gösterimsiz / AR-GE Gerekli) | 14 | `$832.000` | `$1.490.000` | `$2.857.000` | **`%26,2`** |
| **`COTS/CUS`** (Katalog Uyarlama) | 22 | `$530.400` | `$789.700` | `$1.225.700` | `%13,9` |
| **`CUS/R&D`** (Özel + AR-GE Sınırı) | 4 | `$73.000` | `$135.000` | `$263.000` | `%2,4` |
| **`IN-HOUSE`** (`S8` Yazılım/RTL) | 9 | `$0` | `$0` | `$0` | `%0,0` *(HW)* |
| **TOPLAM (`v7.0 Full`)** | **180** | **`$3.347.400`** | **`$5.692.800`** | **`$10.168.900`** | **`%100,0`** |

- **Epistemik Dağılım (`M3 v7.0 Full` Nominal):** `{Liste-Çapası}`: `21` parça (`$762.100`, `%13,4`) | `{Model-Kalibrasyon-Exp114}`: `93` parça (`$2.429.700`, `%42,7`) | `{Varsayım}`: `57` parça (`$2.501.000`, `%43,9`) | `{Program-NRE-Kapsam}`: `9` parça (`$0`).

---

## 3. Çapraz Referanslar

- Parça listesi (`v7.0`, `180` satır): `research/atom_lithography_machine/BOM_DETAILED.csv`
- Kanonik sınıf listesi (değişmez): `research/atom_lithography_machine/BOM.csv` (`SHA-256: cee02adfd207e37bbbc6b66982226b27fa87c2be528ede2b762f72840759cfc2`)
- Tedarikçi teklif teknik şartnameleri (`10` paket = `RFQ-01..RFQ-10`, nominal `%78,2` / MC varyans `%92,6`): `research/atom_lithography_machine/RFQ_SPECIFICATIONS.md`
- 100k Monte Carlo & EVPI deneyi (`v7.0`): `results/exp128_bom_sensitivity/summary_exp128.md` ve `exp128.json`
- Birincil şartnameler: `s56_hardware_spec.json`, `s65_hardware_spec.json`, `s9q_hardware_spec.json`, `s9hpc_hardware_spec.json`, `s_safety_spec.json`
