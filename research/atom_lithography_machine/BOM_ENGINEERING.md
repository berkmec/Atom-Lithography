# Atom Litografi Makinesi — Parça-Düzeyi Mühendislik BOM Analizi (`BOM_ENGINEERING.md` — `v5.0`)

> **Epistemik Beyan (`no_lab_measurement=true`, `no_supplier_quotes=true`):** Bu belge, kanonik 40 satırlık `BOM.csv` (`SHA-256: cee02adfd207e37bbbc6b66982226b27fa87c2be528ede2b762f72840759cfc2` — kesinlikle değiştirilmemiştir) dosyasının `BOM_DETAILED.csv` altında **`v5.0` için 167 fiziksel parça/alt-montaj satırına** (`145` `v3.0` + `14` `v4.0` + `8` `v5.0` parça; `156` fiyatlı + `9` `$0` yazılım + `2` `v5.0`'da değiştirilen `$0` çift-sayım önleme satırı) açılmış mühendislik çözümlemesidir. **Hiçbir satır gerçek tedarikçi fiyat teklifi değildir.** Tüm USD değerleri `M3 v5.0` (`1.024`-hücreli tam `M4` Cryo-MUX + Yerinde `S5.6` `²⁸Si` UHV MBE Capper) için satır-genişletilmiş toplamlar olup `{Liste-Çapası}` (`%13,5`), `{Model-Kalibrasyon-Exp114}` (`%46,3`), `{Varsayım}` (`%40,2`) veya `{Program-NRE-Kapsam}` (`S8` yazılım, `$0` donanım) etiketlidir.

**Tarih:** 2026-11-23 *(`v5.0` tam donanım entegrasyonu: `Exp124–Exp134` + `Exp139` `S5.6` + `Exp140` `S6.5/S6.11`)*  
**Birincil `v5.0` Girdileri (Salt-Okunur Doğrulamalı):** `results/exp139_epi_cap_process_integration/s56_hardware_spec.json` (`S5.6`: `22,4 kg`, `$67k/$95k/$145k`) ve `results/exp140_cryo_fpga_boed_mux_readout/s65_hardware_spec.json` (`Exp140 S6.5` → BOM `S6.11`: `19,27 kg` [`7,77 kg` soğuk + `11,50 kg` raf], `$456,4k/$629,2k/$925,2k`).

---

## 1. Yönetici Özeti ve `Exp122` → `M3 v3.0` → `M3 v4.0` → `M3 v5.0` Tam `$0,00` Köprüsü

Kanonik `BOM.csv` (`40` satır) `Exp122` merkezinde **`$2.531.244`** verir. `v3.0` (`145` parça) **`$4.189.600`**, `v4.0` (`159` parça, `+$420k`) **`$4.609.600`** nominal tabanını oluşturur. **`v5.0`** aşamasında iki yeni fiziksel alt-sistem eklenirken **çift-sayım önleme kuralı** (`−$86.000` kredi) sıkı biçimde uygulanmıştır:

- **Brüt Yeni `v5.0` Donanım (`+$724.200` nom `[$523,4k–$1.070,2k]`, `41,67 kg`):**
  1. **`S5.6` In-Situ `²⁸Si` UHV MBE Capper & FG/H Passivation (`Exp139`, `4` parça, `22,4 kg`):** **`+$95.000`** (`$67k–$145k`).
  2. **`S6.11` (`Exp140 S6.5` — kanonik `BOM.csv` `S6.5`=`RF/ENDOR` satırıyla kimlik çakışmasını önlemek için `S6.11-01..04` altında eşlendi; `1.024`-hücreli Cryo-MUX `32×` TWPA/Purcell/HEMT + `96`-coax + `ZU48DR Q16.16` BOED-FPGA, `4` parça, `19,27 kg`):** **`+$629.200`** (`$456,4k–$925,2k`).
- **Açık Çift-Sayım Önleme Kredisi (`v4.0 → v5.0`, `−$86.000` nom `[−$48k / −$86k / −$161k]`):**
  1. `S6.10-02` (`v4.0` harici 10-yonga `8 nm` `²⁸Si` kaplama lotu) → `S5.6` yerinde MBE (`>1.000` yonga) tarafından ikame edildi: **`−$54.000`** (`$0` satır olarak izlenebilir korundu).
  2. `S6.10-04` (`v4.0` `5 GHz` RF + `20-bit` DC dipol kapı elektroniği) → `5 GHz` RF sürücü yarısı `S6.11-01` `ZU48DR` `32` Direct-RF zincirine taşındı, yalnız `$20k` ultra-düşük gürültülü DC dipol bias DAC korundu: **`−$20.000`**.
  3. `S7.1-04` (`v4.0` ayrık `S8` BOED çıkarım GPU düğümü) → `S6.11-01` `ZU48DR Q16.16` BOED-FPGA (`2,336 µs/adım`) tarafından ikame edildi: **`−$12.000`** (`$0` satır olarak korundu).
- **Net `v5.0` Artışı & İki Ölçek Seçeneği:**
  - **`M3 v5.0` Tam `1.024`-Hücreli `M4` Cryo-MUX + `S5.6` MBE (`167` parça):** `v4.0 $4.609.600 + $724.200 − $86.000` = **`$5.247.800`** nominal (`$3.039.400–$9.525.900`, net **`+$638.200`** [`+%13,85`], **`$0,00` köprü hatası**).
  - **`M3 v5.0` Pilot (`256`-hücreli / `8`-hat `S6.5` alt-seti: `1× ZU48DR $29k + 1/4` kriyo `$142,8k = $171,8k`):** **`$4.790.400`** nominal (net `+$180,8k` vs `v4.0`).
  - **`M1 v5.0` Tek-Demet Laboratuvar Prototipi:** **`$2.466.120`** nominal (`$1,45M–$4,40M`, `M3 v5.0`'ın `%47,0`'ı; `S5.6` tam + `1× ZU48DR` + `1` test TWPA/HEMT/koaksiyel zinciri).
  - **`10.000`-Hücreli `M4` Ölçekleme Notu (`Exp140` `s65_hardware_spec.json`):** Tek `LD400/PT420` kriyostatın tavanı **`2.887` hücredir** (`20 mK MXC` dar boğazı); `10.000`-hücreli `M4` sistemi için **`≥ 4` modüler `LD400/PT420`** kriyostat (`43,63 µW @ 20 mK`, `3,94 W @ 4 K`) zorunludur.

### 1.1 Alt-Sistem Bazlı Tam Uzlaştırma Tablosu (`Exp122` vs `M1 v5.0` vs `M3 v5.0`)

| Alt Sistem | Parça Sayısı | `Exp122` Kanonik (`@$720/u`) | `M1 v5.0` Prototip (Nom `[P10–P90]`) | `M3 v5.0` `BOM_DETAILED` (Nom `[P10–P90]`) | `M3 − Exp122` Farkı (`Δ`) | Farkın Kök Mühendislik Nedeni |
|---|---:|---:|---:|---:|---:|---|
| **S1** Kaynak & Kolon | 22 | `$237.600` | `$319.750` `[$183k–$585k]` | `$416.000` `[$238k–$762k]` | **`+$178.400`** | `Exp124` `Arch-B` `10→5 keV` yavaşlatma + `HDA-HiRes` (`0,453 eV`) + Wien (`0,45 T`) + `PH₃` kabin/yıkayıcı |
| **S2** MEMS Çok-Demet Kafa | 18 | `$10.633` | `$147.750` `[$80k–$289k]` | `$775.500` `[$392k–$1.606k]` | **`+$764.867`** | Sabit MEMS maske/DRIE/TSV/bonding NRE (`$370k`) + `Arch-B` `0,50 mm` `32×32=1.024` plakalar + SKY130 |
| **S3** IBIC Algılama | 14 | `$146.081` | `$88.550` `[$48k–$168k]` | `$224.000` `[$120k–$428k]` | **`+$77.919`** | `Exp127` kilitli `100 K` soğuk-ada `16×8` `LTC6268` CSA (`1,2 µs / 1 GΩ, η=0,99936`) + trim DAC |
| **S4** Konum & Titreşim | 17 | `$241.200` | `$233.920` `[$142k–$411k]` | `$253.000` `[$152k–$446k]` | **`+$11.800`** | `Exp122` ile `%4,9` içinde uyum (`Renishaw XL-80` + `PI PIMars` UHV piezo + aktif tabla + Invar) |
| **S5** Vakum, `S5.5` Flaş & **`S5.6` MBE** | 24 | `$163.800` | `$358.300` `[$219k–$625k]` | `$433.000` `[$260k–$764k]` | **`+$269.200`** | `v3.0` UHV (`+$79,2k`) + `v4.0` `S5.5` flaş (`+$95k`, `Exp139` `43,49 J/cm²` `$0` HW reçete) + **`v5.0` `S5.6` In-Situ `²⁸Si` UHV MBE (`+$95k`, `22,4 kg`)** |
| **S6** Kriyo, DR, Mıknatıs, Okuma, `PT420`, `M4` & **`S6.5/S6.11` MUX** | 42 | `$1.578.650` | `$1.171.150` `[$700k–$2.048k]` | `$2.794.100` `[$1.683k–$4.844k]` | **`+$1.215.450`** | `S6.6` (`$680.400`) & `S6.8` (`$720.000`) `Exp122` ile **kuruşu kuruşuna eşit**; `Exp125` (`+$347,3k`) + `v4.0` `S6.9` (`+$68k`) + `S6.10` net (`$171k`, `−$74k` kredi) + **`v5.0` `S6.11` [`Exp140 S6.5`] `32`-hat TWPA/HEMT/coax/ZU48DR (`+$629,2k`, `19,27 kg`)** |
| **S7** Kontrol & Hesaplama | 14 | `$153.281` | `$104.450` `[$60k–$192k]` | `$204.200` `[$115k–$378k]` | **`+$50.919`** | `2× Lambda Vector` + AWG + SKY130 + EMI/PLC (`S7.1-04` `$12k` BOED GPU `S6.11-01` ZU48DR ile ikame edilerek `$0` yapıldı) |
| **S8** Yazılım & RTL (`+BOED/v3.5`) | 9 | `$0` | `$0` | `$0` | **`$0`** | Proje-içi yazılım/RTL (`machine_control`, `CellISA v3.5`, `fpga_boed_dsp.py`, `blanker_tile`, GRAPE/XY8); işçilik Program NRE içinde |
| **S9** Sarf & Yedekler | 7 | `$0` | `$42.250` `[$22k–$82k]` | `$148.000` `[$78k–$297k]` | **`+$148.000`** | Kalibrasyon yongaları (`$35k`), 1 yıllık gaz/katot (`$18k`), yedek MEMS + 4 yedek kriyo-LNA + bakım kiti (`$95k`) |
| **TOPLAM (`v5.0`)** | **167** | **`$2.531.244`** | **`$2.466.120`** `[$1,45M–$4,40M]` | **`$5.247.800`** `[$3,04M–$9,53M]` | **`+$2.716.556`** | **Uzlaştırma hatası: `$0,00` (`M3 v4.0 $4,610M + $724,2k − $86k = $5,248M`)** |

### 1.2 Kurumsal Delta Köprüsü & Kütle Doğrulaması (`Exp122` → `v3.0` → `v4.0` → `v5.0`)

| Köprü Adımı | Tutar (USD) | Kütle (`v5.0`) | Açıklama |
|---|---:|---:|---|
| **`Exp122` Merkez Bazı (`3.515,62u @ $720`)** | `$2.531.244` | — | `40` kanonik satır (`BOM.csv` SHA-256 korundu) |
| `+ v3.0` Mühendislik Deltaları (`S2`, `COTS/UHV`, `Exp125`, `S9`, `Exp124`, `Exp127`) | `+$1.658.356` | — | `145` parça `v3.0` tabanı |
| **`= M3 v3.0` Ara Toplam** | **`$4.189.600`** | — | `Exp134` `v3.0` çapası (`$0,00` sapma) |
| `+ v4.0` Paketi (`S5.5 $95k + S6.9 $68k + S6.10 $245k + S7.1-04 $12k`) | `+$420.000` | — | `159` parça `v4.0` tabanı (`Exp130/131/132/133/134`) |
| **`= M3 v4.0` Ara Toplam** | **`$4.609.600`** | — | `Exp128 v4.0` / `Exp134` çapası (`$0,00` sapma) |
| `+ v5.0` `S5.6` In-Situ `²⁸Si` UHV MBE Capper + FG/H (`Exp139`, `4` parça) | `+$95.000` | **`22,40 kg`** | `11,8 + 3,4 + 4,2 + 3,0 kg` (`s56_hardware_spec.json` birebir) |
| `+ v5.0` `S6.11` (`Exp140 S6.5`) `1.024`-Hücre Cryo-MUX + `ZU48DR` (`4` parça) | `+$629.200` | **`19,27 kg`** | `11,50 kg` raf + `7,77 kg` soğuk (`2,72 + 1,02 + 4,03 kg`, `s65_hardware_spec.json` birebir) |
| `− v4.0 → v5.0` Çift-Sayım Önleme Kredisi (`S6.10-02 −$54k`, `S6.10-04 −$20k`, `S7.1-04 −$12k`) | **`−$86.000`** | — | Harici kaplama lotu, 5 GHz RF sürücü ve ayrık BOED GPU çift-sayımı sıfırlandı |
| **`= M3 v5.0 BOM_DETAILED` Tam `1.024`-Hücre Toplamı (`167` parça)** | **`$5.247.800`** | **`+41,67 kg`** | **Aritmetik & kütle köprü hatası: `$0,00` / `0,000 kg` (`$50M` sınırının `9,5×` altı)** |

---

## 2. Tedarik Sınıfı ve Epistemik Dağılım (`BOM_DETAILED.csv v5.0`, `167` Parça)

| Tedarik Sınıfı | Parça Sayısı | `M3 v5.0` Alt (`P10`) | `M3 v5.0` Nominal (`P50`) | `M3 v5.0` Üst (`P90`) | `M3 v5.0` Nominal Payı |
|---|---:|---:|---:|---:|---:|
| **`COTS`** (Rafta/Katalog) | 65 | `$1.016.200` | `$1.724.200` | `$3.040.200` | **`%32,9`** |
| **`R&D`** (Gösterimsiz / AR-GE Gerekli) | 13 | `$800.000` | `$1.444.000` | `$2.789.000` | **`%27,5`** |
| **`CUS`** (Özel Üretim, Bilinen Teknoloji) | 59 | `$763.300` | `$1.358.400` | `$2.497.500` | **`%25,9`** |
| **`COTS/CUS`** (Katalog Uyarlama) | 17 | `$386.900` | `$586.200` | `$936.200` | `%11,2` |
| **`CUS/R&D`** (Özel + AR-GE Sınırı) | 4 | `$73.000` | `$135.000` | `$263.000` | `%2,6` |
| **`IN-HOUSE`** (`S8` Yazılım/RTL + `CellISA v3.5`) | 9 | `$0` | `$0` | `$0` | `%0,0` *(HW)* |
| **TOPLAM (`v5.0`)** | **167** | **`$3.039.400`** | **`$5.247.800`** | **`$9.525.900`** | **`%100,0`** |

- **Epistemik Dağılım (`M3 v5.0` Nominal):** `{Liste-Çapası}`: `18` parça (`$710.600`, `%13,5`) | `{Model-Kalibrasyon-Exp114}`: `93` parça (`$2.429.700`, `%46,3`) | `{Varsayım}`: `47` parça (`$2.107.500`, `%40,2`) | `{Program-NRE-Kapsam}`: `9` parça (`$0`).

---

## 3. Çapraz Referanslar

- Parça listesi (`v5.0`, `167` satır): `research/atom_lithography_machine/BOM_DETAILED.csv`
- Kanonik sınıf listesi (değişmez): `research/atom_lithography_machine/BOM.csv` (`SHA-256: cee02adfd207e37bbbc6b66982226b27fa87c2be528ede2b762f72840759cfc2`)
- Tedarikçi teklif teknik şartnameleri (`8` paket = `RFQ-01..RFQ-08`, nominal `%76,4` / MC varyans `%92,6`): `research/atom_lithography_machine/RFQ_SPECIFICATIONS.md`
- 100k Monte Carlo & EVPI deneyi (`v5.0`): `results/exp128_bom_sensitivity/summary_exp128.md` ve `exp128.json`
- Birincil `v5.0` donanım şartnameleri: `results/exp139_epi_cap_process_integration/s56_hardware_spec.json`, `results/exp140_cryo_fpga_boed_mux_readout/s65_hardware_spec.json`
