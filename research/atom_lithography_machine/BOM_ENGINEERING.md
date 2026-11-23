# Atom Litografi Makinesi — Parça-Düzeyi Mühendislik BOM Analizi (`BOM_ENGINEERING.md` — `v6.0`)

> **Epistemik Beyan (`no_lab_measurement=true`, `no_supplier_quotes=true`):** Bu belge, kanonik 40 satırlık `BOM.csv` (`SHA-256: cee02adfd207e37bbbc6b66982226b27fa87c2be528ede2b762f72840759cfc2` — kesinlikle değiştirilmemiştir) dosyasının `BOM_DETAILED.csv` altında **`v6.0` için 174 fiziksel parça/alt-montaj satırına** (`167` `M3 v5.0 Base` + `7` `v6.0` Modüler Opsiyon [`4` `Option-Q` + `3` `Option-HPC`]; `163` fiyatlı + `9` `$0` yazılım + `2` `v5.0`'da değiştirilen `$0` çift-sayım önleme satırı) açılmış mühendislik çözümlemesidir. **Hiçbir satır gerçek tedarikçi fiyat teklifi değildir.** Tüm USD değerleri satır-genişletilmiş toplamlar olup `{Liste-Çapası}` (`%13,1`), `{Model-Kalibrasyon-Exp114}` (`%43,8`), `{Varsayım}` (`%43,2`) veya `{Program-NRE-Kapsam}` (`S8` yazılım, `$0` donanım) etiketlidir.

**Tarih:** 2026-11-23 *(`v6.0` modüler donanım entegrasyonu: `M3 v5.0 Base` aynen korundu + `Exp142` `Option-Q` + `Exp143` `Option-HPC`)*  
**Birincil `v5.0` / `v6.0` Girdileri (Salt-Okunur Doğrulamalı):**
- `results/exp139_epi_cap_process_integration/s56_hardware_spec.json` (`S5.6`: `22,40 kg`, `$67k/$95k/$145k`)
- `results/exp140_cryo_fpga_boed_mux_readout/s65_hardware_spec.json` (`Exp140 S6.5` → BOM `S6.11`: `19,27 kg`, `$456,4k/$629,2k/$925,2k`)
- `results/exp142_option_q_multispecies_qram/s9q_hardware_spec.json` (`Option-Q`: `4` parça [`Exp142 S1.6-01` → BOM `S1.7-01` & `Exp142 S9.1-01..03` → BOM `S9.4-01..03`], **`9,20 kg`**, **`$118k/$168k/$242k`**)
- `results/exp143_d3_grape_m4_and_hpc_decoder/s9hpc_hardware_spec.json` (`Option-HPC`: `3` parça [`S9.HPC-01..03`], **`64,00 kg`**, **`$98k/$132k/$181k`**, `2.195 W` raf / `0,0 W` kriyo)

---

## 1. Modüler `v6.0` Yapılandırma Matrisi (Çift Sayım Yok — `$0,00` Köprü & `0,000 kg` Kütle Eşitliği)

`v6.0` yükseltmesinde **`M1 Base` (`$2.466.120`)** ve **`M3 v5.0 Base` (`167` parça, `$5.247.800`)** kesinlikle bozulmadan korunmuş, `Option-Q` (`Exp142`) ve `Option-HPC` (`Exp143`) tamamen **modüler tak-çıkar eklentiler** olarak ayrıştırılmıştır. Kanonik/önceki parça kimlikleriyle (`S1.6 = PH₃/SiF₄`, `S6.5 = RF/ENDOR`, `S9.1 = kalibrasyon yongaları`) sıfır çakışma sağlanmıştır:

| Yapılandırma | Parça | Donanım Alt (`P10`) | Donanım Nominal (`P50`) | Donanım Üst (`P90`) | `CAD v6.0` Kütle | `M3 Base` Farkı (`Δ`) | Kullanım Kapsamı |
|---|---:|---:|---:|---:|---:|---:|---|
| **`M1 Base` Prototip** *(korundu)* | 167 *(ölçekli)* | `$1.454.996` | **`$2.466.120`** | `$4.400.788` | — | `−$2.781.680` | Tek-demet `³¹P⁺` + `20 mK` DR + `S5.5` + `S5.6` MBE + `1× ZU48DR/TWPA` (`v6` opsiyonları hariç) |
| **`M3 v5.0` Pilot (`256`-hücre)** | 167 *(8-hat)* | — | **`$4.790.400`** | — | — | `−$457.400` | Kademeli `256`-hücreli `M4` başlangıç seçeneği (`$100M` marj tamponu) |
| **`M3 v5.0 Base` (`1.024`-hücre)** *(korundu)* | **167** | `$3.039.400` | **`$5.247.800`** | `$9.525.900` | **`1.034,94 kg`** | **`$0`** | Çekirdek `1.024`-demetcik + `S5.6` MBE + `S6.5/S6.11` Cryo-MUX (`v5.0` tam tabanı) |
| **`M3 v6.0 +Option-Q`** | 171 | `$3.157.400` | **`$5.415.800`** | `$9.767.900` | `1.044,14 kg` | **`+$168.000`** | `Base` + `S1-Multi` (`³¹P/¹²¹Sb/¹⁶⁷Er`, `4,80 kg`) + `5`-kademe Chebyshev `qRAM`/`1550 nm` fiber (`4,40 kg`) |
| **`M3 v6.0 +Option-HPC`** | 170 | `$3.137.400` | **`$5.379.800`** | `$9.706.900` | `1.098,94 kg` | **`+$132.000`** | `Base` + `S9.HPC` `4U` 2-düğüm `100G` RoCEv2 RDMA QEC dekoderi + `QSFP28` optik köprü (`64,00 kg`) |
| **`M3 v6.0 Full` (`Option-Q + Option-HPC`)** | **174** | **`$3.255.400`** | **`$5.547.800`** | **`$9.948.900`** | **`1.108,14 kg`** | **`+$300.000`** | Tam `v6.0` hibrit bellek (`qRAM`/telekom) + gerçek-zamanlı `100G` RDMA QEC dekoder paketi |

### 1.1 Alt-Sistem Bazlı Tam Uzlaştırma Tablosu (`Exp122` vs `M1 Base` vs `M3 v6.0 Full`)

| Alt Sistem | Parça Sayısı | `Exp122` Kanonik (`@$720/u`) | `M1 Base` Prototip (Nom `[P10–P90]`) | `M3 v6.0 Full` `BOM_DETAILED` (Nom `[P10–P90]`) | `M3 v6 − Exp122` Farkı (`Δ`) | Farkın Kök Mühendislik Nedeni |
|---|---:|---:|---:|---:|---:|---|
| **S1** Kaynak, Kolon & **`S1.7` Multi** | 23 | `$237.600` | `$319.750` `[$183k–$585k]` | `$484.000` `[$286k–$858k]` | **`+$246.400`** | `v5` `S1` (`$416k`: `Arch-B`, `HDA-HiRes`, `PH₃`) + **`v6` `Option-Q` `S1.7-01` [`Exp142 S1.6-01`] `S1-Multi` (`+$68k`, `4,80 kg`)** |
| **S2** MEMS Çok-Demet Kafa | 18 | `$10.633` | `$147.750` `[$80k–$289k]` | `$775.500` `[$392k–$1.606k]` | **`+$764.867`** | Sabit MEMS maske/DRIE/TSV/bonding NRE (`$370k`) + `Arch-B` `0,50 mm` `32×32=1.024` plakalar + SKY130 |
| **S3** IBIC Algılama | 14 | `$146.081` | `$88.550` `[$48k–$168k]` | `$224.000` `[$120k–$428k]` | **`+$77.919`** | `Exp127` kilitli `100 K` soğuk-ada `16×8` `LTC6268` CSA (`1,2 µs / 1 GΩ, η=0,99936`) + trim DAC |
| **S4** Konum & Titreşim | 17 | `$241.200` | `$233.920` `[$142k–$411k]` | `$253.000` `[$152k–$446k]` | **`+$11.800`** | `Exp122` ile `%4,9` içinde uyum (`Renishaw XL-80` + `PI PIMars` UHV piezo + aktif tabla + Invar) |
| **S5** Vakum, `S5.5` Flaş & `S5.6` MBE | 24 | `$163.800` | `$358.300` `[$219k–$625k]` | `$433.000` `[$260k–$764k]` | **`+$269.200`** | `v3` UHV (`+$79,2k`) + `v4` `S5.5` flaş (`+$95k`, `43,49 J/cm²`) + `v5` `S5.6` In-Situ `²⁸Si` MBE (`+$95k`, `22,40 kg`) |
| **S6** Kriyo, DR, Mıknatıs, Okuma & MUX | 42 | `$1.578.650` | `$1.171.150` `[$700k–$2.048k]` | `$2.794.100` `[$1.683k–$4.844k]` | **`+$1.215.450`** | `S6.6` (`$680.400`) & `S6.8` (`$720.000`) `Exp122` ile birebir; `Exp125` + `S6.9` + `S6.10` net + `S6.11` (`+$629,2k`, `19,27 kg`) |
| **S7** Kontrol & Hesaplama | 14 | `$153.281` | `$104.450` `[$60k–$192k]` | `$204.200` `[$115k–$378k]` | **`+$50.919`** | `2× Lambda Vector` + AWG + SKY130 + EMI/PLC (`S7.1-04` BOED GPU `v5`'te `$0` yapıldı) |
| **S8** Yazılım & RTL | 9 | `$0` | `$0` | `$0` | **`$0`** | Proje-içi yazılım/RTL (`machine_control`, `CellISA v4.0 (20 op)`, `auto_recal.py`, `cloud_qpu_bridge.py`, `fpga_boed_dsp.py`, GRAPE/XY8); işçilik Program NRE içinde |
| **S9** Sarf, Yedek & **`v6` `S9.4`/`S9.HPC`** | 13 | `$0` | `$42.250` `[$22k–$82k]` | `$380.000` `[$246k–$624k]` | **`+$380.000`** | `v3` Yedek/Kalibrasyon (`$148k`) + **`v6` `Option-Q` `S9.4-01..03` [`Exp142 S9.1`] (`+$100k`, `4,40 kg`)** + **`Option-HPC` `S9.HPC-01..03` (`+$132k`, `64,00 kg`)** |
| **TOPLAM (`v6.0 Full`)** | **174** | **`$2.531.244`** | **`$2.466.120`** `[$1,45M–$4,40M]` | **`$5.547.800`** `[$3,26M–$9,95M]` | **`+$3.016.556`** | **Uzlaştırma & köprü hatası: `$0,00` (`Base $5.247.800 + $168.000 + $132.000 = $5.547.800`)** |

### 1.2 Kurumsal Delta Köprüsü & Kütle Doğrulaması (`Exp122` → `v3.0` → `v4.0` → `v5.0 Base` → `v6.0 Full`)

| Köprü Adımı | Tutar (USD) | Kütle (`CAD`) | Açıklama |
|---|---:|---:|---|
| **`Exp122` Merkez Bazı (`3.515,62u @ $720`)** | `$2.531.244` | — | `40` kanonik satır (`BOM.csv` SHA-256 korundu) |
| `+ v3.0` Mühendislik Deltaları (`S2`, `COTS/UHV`, `Exp125`, `S9`, `Exp124`, `Exp127`) | `+$1.658.356` | — | `145` parça `v3.0` tabanı |
| **`= M3 v3.0` Ara Toplam** | **`$4.189.600`** | — | `Exp134` `v3.0` çapası (`$0,00` sapma) |
| `+ v4.0` Paketi (`S5.5 $95k + S6.9 $68k + S6.10 $245k + S7.1-04 $12k`) | `+$420.000` | — | `159` parça `v4.0` tabanı (`Exp130/131/132/133/134`) |
| **`= M3 v4.0` Ara Toplam** | **`$4.609.600`** | `993,27 kg` | `Exp128 v4.0` / `Exp134` çapası (`$0,00` sapma) |
| `+ v5.0` Brüt Yeni Donanım (`S5.6` `$95k/22,40 kg` + `S6.11` `$629,2k/19,27 kg`) | `+$724.200` | `+41,67 kg` | `Exp139` & `Exp140` şartnameleriyle birebir |
| `− v4.0 → v5.0` Çift-Sayım Önleme Kredisi (`S6.10-02 −$54k`, `S6.10-04 −$20k`, `S7.1-04 −$12k`) | `−$86.000` | — | Harici kaplama lotu, 5 GHz RF sürücü ve ayrık BOED GPU çift-sayımı sıfırlandı |
| **`= M3 v5.0 Base` Ara Toplam (`167` parça — DEĞİŞMEDİ)** | **`$5.247.800`** | **`1.034,94 kg`** | **`v5.0` tam makine tabanı (`$0,00` / `0,000 kg` sapma)** |
| `+ v6.0` **`Option-Q`** (`Exp142`: `S1.7-01` `$68k/4,80 kg` + `S9.4-01..03` `$100k/4,40 kg`) | `+$168.000` | **`+9,20 kg`** | `s9q_hardware_spec.json` (`$118k/$168k/$242k`, `9,20 kg`) birebir; kanonik `S1.6`/`S9.1` korundu |
| `+ v6.0` **`Option-HPC`** (`Exp143`: `S9.HPC-01..03` `4U` `100G` RoCEv2 RDMA dekoder + `QSFP28`) | `+$132.000` | **`+64,00 kg`** | `s9hpc_hardware_spec.json` (`$98k/$132k/$181k`, `64,00 kg`, `2.195 W` / `0 W` kriyo) birebir |
| **`= M3 v6.0 Full BOM_DETAILED` (`174` parça)** | **`$5.547.800`** | **`1.108,14 kg`** | **Aritmetik & kütle köprü hatası: `$0,00` / `0,000 kg` (`$50M` sınırının `9,0×` altı)** |

---

## 2. Tedarik Sınıfı ve Epistemik Dağılım (`BOM_DETAILED.csv v6.0`, `174` Parça)

| Tedarik Sınıfı | Parça Sayısı | `M3 v6.0` Alt (`P10`) | `M3 v6.0` Nominal (`P50`) | `M3 v6.0` Üst (`P90`) | `M3 v6.0` Nominal Payı |
|---|---:|---:|---:|---:|---:|
| **`COTS`** (Rafta/Katalog) | 66 | `$1.025.700` | `$1.737.700` | `$3.059.700` | **`%31,3`** |
| **`R&D`** (Gösterimsiz / AR-GE Gerekli) | 14 | `$832.000` | `$1.490.000` | `$2.857.000` | **`%26,9`** |
| **`CUS`** (Özel Üretim, Bilinen Teknoloji) | 62 | `$849.300` | `$1.480.400` | `$2.671.500` | **`%26,7`** |
| **`COTS/CUS`** (Katalog Uyarlama) | 19 | `$475.400` | `$704.700` | `$1.097.700` | `%12,7` |
| **`CUS/R&D`** (Özel + AR-GE Sınırı) | 4 | `$73.000` | `$135.000` | `$263.000` | `%2,4` |
| **`IN-HOUSE`** (`S8` Yazılım/RTL) | 9 | `$0` | `$0` | `$0` | `%0,0` *(HW)* |
| **TOPLAM (`v6.0 Full`)** | **174** | **`$3.255.400`** | **`$5.547.800`** | **`$9.948.900`** | **`%100,0`** |

- **Epistemik Dağılım (`M3 v6.0 Full` Nominal):** `{Liste-Çapası}`: `19` parça (`$724.100`, `%13,1`) | `{Model-Kalibrasyon-Exp114}`: `93` parça (`$2.429.700`, `%43,8`) | `{Varsayım}`: `53` parça (`$2.394.000`, `%43,2`) | `{Program-NRE-Kapsam}`: `9` parça (`$0`).

---

## 3. Çapraz Referanslar

- Parça listesi (`v6.0`, `174` satır): `research/atom_lithography_machine/BOM_DETAILED.csv`
- Kanonik sınıf listesi (değişmez): `research/atom_lithography_machine/BOM.csv` (`SHA-256: cee02adfd207e37bbbc6b66982226b27fa87c2be528ede2b762f72840759cfc2`)
- Tedarikçi teklif teknik şartnameleri (`9` paket = `RFQ-01..RFQ-09`, nominal `%77,7` / MC varyans `%92,6`): `research/atom_lithography_machine/RFQ_SPECIFICATIONS.md`
- 100k Monte Carlo & EVPI deneyi (`v6.0`): `results/exp128_bom_sensitivity/summary_exp128.md` ve `exp128.json`
- Birincil `v5.0/v6.0` donanım şartnameleri: `s56_hardware_spec.json`, `s65_hardware_spec.json`, `s9q_hardware_spec.json`, `s9hpc_hardware_spec.json`
