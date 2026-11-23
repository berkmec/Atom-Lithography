# CAD Paketi v5.0 — Atom Litografi Makinesi (`Exp124`..`Exp133` + `Exp139 S5.6` + `Exp140 S6.5` Kilitli)

Sürüm: `5.0-exp139-exp140-locked` (2026-11-23) · Birim: `mm` · Genel Tolerans: `ISO 2768-mK`  
Durum: **Kâğıt üzerinde parametrik konsept / ön-mühendislik CAD modeli (`no_lab_measurement=true`).** Fiziksel donanım veya laboratuvar ölçümü değildir.

## v5.0 Kilitli Mühendislik Mimarisi (`exp124/125/127/130/131/133/139/140_synced=True`)

- **Temel `v3.0/v4.0` Çekirdeği (Korundu):** Eski `maglev_stage` ve `s=1,0` kalıntıları yok; `s=0,5` altın zarf (`Exp80`, `V_iç = 34,86 L` `BC4 PASS`), **`Exp124`** `562,66 mm / 25,92 kg` `10→5 keV` iyon kolonu (`32×32 @ 0,50 mm`, `16×16 mm` yazma alanı, `Ø28 mm` delikte `2,686 mm` radyal pay, `Arch-B WD=0,250 mm`, `HDA-HiRes ΔE=0,453 eV`), **`Exp125`** vakum-içi 8-bobinli `1,50 T` kriyo-mıknatıs (`Ø150 mm` bore, `36 mm` yarık, `Ø352 mm` OD, `z=−155 mm` `Ø50 mm` NbTiN `22,3 µT` + `Nb` Meissner + `Cryoperm-10`), **`Exp127`** `100 K` `LTC6268` IBIC CSA (`ENC=24,1 e⁻, η=0,99936`), **`Exp130`** `S5.5` `+Y` `808 nm` qCW flaş tavlama kafası (`43,49 J/cm² @ 1530 K` v5.0 reçetesiyle uyumlu, `Ø44 mm` CA, `10 µs` dikroik pirometre & güvenlik deklanşörü), **`Exp131`** `M4` `4 K` `968`-kapılı `SKY130` çapraz-anahtar kartı ve **`Exp133`** `PT420` titreşim ayrıştırma paketi (`500 mm` uzak döner valf, `600 mm` esnek He hattı, `CF63` kenar-kaynaklı körük `2.000 N/m`, `4×` OFHC Cu S-ilmek örgü `52,7 N/m`).
- **`Exp139` (`S5.6`) Yerinde `²⁸Si` UHV MBE Kaplayıcı & Forming-Gas Pasivasyon Modülü (`S5` Load-Lock `+Z`, `+22,40 kg`):**
  - `s5_loadlock_chamber` üst yüzeyi (`X = 420,0 mm, Y = 0,0 mm, Z = 585,1..865,0 mm`) üzerine `CF100 DN100CF` (`Ø152 mm` OD / `Ø100 mm` iç çap) ile monte edilmiş `6` katı parça:
    - `s5_mbe_cf100_flange` (`2,40 kg`) + `s5_mbe_source_body` (`6,90 kg`) + `s5_mbe_top_feedthrough` (`2,50 kg`) = `11,80 kg` pota-sız `²⁸Si` süblimasyon kaynağı, kriyo/su gömleği ve pnömatik deklanşör;
    - `s5_mbe_qcm_valve` (`3,40 kg`, `−Y` yanı) QCM film kalınlık sensörü & vana aktüatörü;
    - `s5_mbe_pbn_heater_fg` (`4,20 kg`, `+Y` yanı) `345 °C` PBN radyatif ısıtıcı geçişi & `350 °C` `%5 H₂/N₂` pasivasyon manifoldu;
    - `s5_mbe_tmp_neg_pump` (`3,00 kg`, `+X` yanı) `80 L/s` kompakt TMP + NEG yardımcı pompa paketi.
  - Boşluklar: UHV ana oda üst flanşına **`119,0 mm`** (`X`), transfer koluna **`70,1 mm`** (`Z`), `S7` geçiş paneline **`186,0 mm`** (`X`). Sürgülü UHV vana sayesinde `20 mK` MXC kademesine **`0 µW`** termal sızıntı.
- **`Exp140` (`S6.5`) `1.024`-Hücreli Kriyo-MUX (`TWPA`/`Purcell`/`HEMT`/`96-Koaks`) & `2U` `19"` `ZU48DR` `Q16.16` BOED-FPGA RFSoC (`+19,27 kg` = `7,77 kg` Soğuk `S6` + `11,50 kg` Kabin `S7`):**
  - **Soğuk `S6` Paketi (`7,77 kg`, `12` katı parça, `S6.8` DR kulesi içinde):**
    - `s6_s65_twpa_purcell_pack` (`2,72 kg`, `180×140×55 mm`, `20 mK MXC` altı): `32`-kanallı Josephson TWPA + band-geçiren Purcell filtresi + çift kriyo-izolatör paketi (`4 K` kalkanına `17,98 mm` radyal boşluk);
    - `s6_s65_hemt_bank_32ch` (`1,02 kg`, `Ø176/Ø244×40 mm`, `4 K` kademesi): `32` adet `LNF-LNC4_8C` ultra-düşük gürültülü HEMT bankası (`4 K` kalkanına `10,0 mm` radyal pay);
    - `s6_s65_coax_loom_*` (`10` segment, `4,03 kg`, `300 K ↔ 20 mK`): `96`-hat `0,86 mm` CuNi/NbTi koaksiyel demet & zayıflatıcı paketi (`4 K M4` çapraz-anahtarına `8,0 mm` `X` boşluğu).
  - **Oda Sıcaklığı `S7` Kabin Modülü (`11,50 kg`, `1` katı parça, `87,96 W`):**
    - `s7_s65_rfsoc_boed_bay` (`2U = 88,9 mm`, `482,6 mm` `19"` genişlik × `430 mm` kısa-derinlik şasi): `2×` `ZU48DR` `Q16.16` BOED-FPGA RFSoC (`32` doğrudan-RF zinciri), `AWG` rafının `20,0 mm` üzerinde ve `3U` Rb saat rafının `16,1 mm` altında.
- **Toplam Makine Özeti (`cad_verification.json`):** **`189`** katı parça (`S1`–`S7`), **`1.034,94 kg`** (`v4.0`'a göre tam `+41,67 kg` = `+22,40 kg S5.6` + `+7,77 kg S6.5 soğuk` + `+11,50 kg S6.5 RFSoC`), `CoM = (109,0; -9,4; 467,7) mm`, **`0 / 17.766` katı çakışma**, **`32 / 32` kritik boşluk PASS**, **`8 / 8` su geçirmez STL (`38.876` üçgen)**.

## Alt Sistem Kütle & Parça Özeti (`CAD v5.0`)

| Kod | Alt Sistem | Parça | Kütle (kg) | `v4.0 → v5.0` Fark | STL Üçgen |
|---|---|---:|---:|---:|---:|
| `S1` | `s1_ion_source_column` | 11 | 25,98 | 0,00 | 3.468 |
| `S2` | `s2_mems_write_head` | 9 | 1,83 | 0,00 | 2.496 |
| `S3` | `s3_ibic_detector_assembly` | 7 | 0,15 | 0,00 | 636 |
| `S4` | `s4_piezo_stage_interferometry` | 18 | 302,37 | 0,00 | 2.400 |
| `S5` | `s5_uhv_chamber_loadlock` (+`S5.6`) | 29 | 193,94 | +22,40 | 4.732 |
| `S6` | `s6_cryo_dr_magnet_readout` (+`S6.5` soğuk) | 102 | 280,92 | +7,77 | 24.988 |
| `S7` | `s7_electronics_rack_interconnect` (+`S6.5-01`) | 13 | 229,75 | +11,50 | 156 |
| **Top.** | **`atom_litho_machine.stl`** | **189** | **1.034,94** | **+41,67** | **38.876** |

## Dosya Yapısı & Yeniden Üretim

- `params.py`, `mesh_engine.py`, `gen_scad.py`, `gen_stl.py`, `gen_drawings.py`, `preview.py`
- `parts/s1..s7.scad` + `atom_litho_machine.scad` (8 parametrik OpenSCAD dosyası)
- `stl/s1..s7.stl` + `stl/atom_litho_machine.stl` (8 su geçirmez ikili STL) + `cad_verification.json`
- `drawings/01..10.{svg,png}` (10 adet `2400×1600` px ISO/ANSI teknik resim, `ALM-500-*`) + `preview_machine.png` (`2000×1020`)

```bash
cd research/atom_lithography_machine/cad
python3 -B gen_scad.py
python3 -B gen_stl.py
python3 -B gen_drawings.py
python3 -B preview.py
cd ../../..
python3 -B -m pytest tests/test_cad.py -v
```
