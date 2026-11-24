# CAD Paketi v6.0 — Atom Litografi Makinesi (`Exp124`..`Exp140` + `Option-Q` [`Exp142`] + `Option-HPC` [`Exp143`] Kilitli)

Sürüm: `6.0-exp142-exp143-option-qhpc-locked` (2026-11-24 `v7.1` epistemik kapsam notu) · Birim: `mm` · Genel Tolerans: `ISO 2768-mK`  
Durum: **TRL 1–2 (`M0`) nominal statik parametrik konsept CAD modeli (`no_lab_measurement = true`).** Fiziksel donanım veya laboratuvar ölçümü değildir.

> [!NOTE]
> **Geometrik Doğrulama Kapsamı ve Sınırları (`0/19.701` çakışma / `40/40` boşluk):** `cad_verification.json` içindeki `0/19.701` katı çakışma ve `40/40` boşluk sonucu **yalnızca nominal statik geometrik çakışma ve zarf kontrolüdür**. Bu kontrol **GD&T tolerans yığılmasını, `300 K → 20 mK` termal büzülmeyi, mekanik titreşim kuplajını, kablo/boru/tesisat yönlendirmesini, UHV gaz salınımı ve uyumluluğunu, manyetik malzeme uyumunu, üretilebilirliği (`DFM`) ve fiziksel montaj sırasını KAPSAMAZ.**

## v6.0 Kilitli Mühendislik Mimarisi (`exp124..143_synced=True`)

- **Temel `v3.0–v5.0` Çekirdeği (`1.034,94 kg`, `189` parça — Korundu):** Eski `maglev_stage` yok; `s=0,5` altın zarf (`Exp80`, `V_iç = 34,86 L`), **`Exp124`** `562,66 mm / 25,92 kg` `10→5 keV` iyon kolonu (`32×32 @ 0,50 mm`, `Arch-B WD=0,250 mm`, `HDA ΔE=0,453 eV`), **`Exp125`** `8`-bobinli `1,50 T / 22,3 µT` kriyo-mıknatıs + `S6.8` `20 mK` DR, **`Exp127`** `100 K` `LTC6268` IBIC CSA, **`Exp130`** `S5.5` `+Y` `808 nm` flaş kafası (`1530 K`), **`Exp131`** `4 K M4` `968`-kapılı anahtar, **`Exp133`** `PT420` titreşim ayrıştırma (`CF63` körük + `4×` OFHC örgü + `500 mm` uzak valf), **`Exp139`** `S5.6` `+Z` `²⁸Si` UHV MBE kaplayıcı (`22,40 kg`) ve **`Exp140`** `S6.5` `1.024`-hücreli Kriyo-MUX (`7,77 kg` soğuk) + `2U` `ZU48DR` `BOED-RFSoC` (`11,50 kg` kabin).
- **`Exp142` (`Option-Q`) Çok-Türlü İyon Kartuşu & Kriyo-`qRAM` / `1550 nm` Fiber Köprüsü (`+9,20 kg`, `5` katı parça):**
  - **`S1.6` Çok-Türlü Kaynak Kartuş Yuvası (`S1` `+Y`, `+4,80 kg`, `2` parça):** `s1_multi_species_cartridge` (`76×76×95 mm`, `4,45 kg`, merkez `(0; 110; 992,66) mm`, `³¹P` gaz / `¹²¹Sb` `450 °C` fırın / `¹⁶⁷Er` mikro-Paul/fırın hızlı değişim) + `s1_multi_species_neck` (`CF40` geçiş boğazı, `0,35 kg`). Boşluklar: `s1_duoplasmatron`'a **`27,0 mm`**, `−Y PH₃` manifolduna **`136,0 mm`**.
  - **`S9.1` Kriyo-`qRAM` & `1550 nm` Optik Köprü (`S6` DR, `+4,40 kg`, `3` parça, `0,78 µW @ 20 mK`):**
    - `s6_s91_ovc_feedthrough` (`3,20 kg`, `100×120×120 mm`, `(−875,2; 0; 690) mm`): DR `−X` `OVC` `CF63` `4`-port RF + `1550 nm` `SMF-28` vakum geçişi (PT420 valf sehpasına **`144,8 mm`** `X` boşluğu);
    - `s6_s91_qram_bridge_20mk` (`0,38 kg`, `60×30×16 mm`, `(−650; 0; 410) mm`): `20 mK` `5`-kademe Chebyshev/Klopfenstein `50 Ω ↔ 3 kΩ` `NbTiN` `qRAM` köprüsü (`S6.5` TWPA paketinin **`8,5 mm`** altında);
    - `s6_s91_qram_fiber_loom` (`0,82 kg`, `Ø10×308 mm`, `(−793; 0; 564) mm`): `4× NbTi` süperiletken koaks + `1550 nm` `SMF-28` kriyo-fiber demeti (`4 K` ve `50 K` kalkanlar arasında **`2,0 mm`** radyal pay).
- **`Exp143` (`Option-HPC`) `S9.HPC` `4U+1U` `100 Gbps` RoCEv2 RDMA QEC Dekoder Rafı (`S7` `+X` bitişik, `+64,00 kg`, `5` katı parça, `2.195 W`, `0,0 W` kriyo):**
  - `S7` kontrol kabininin `+X` yanında **`60,0 mm`** servis/hava koridoruyla konumlandırılmış `19"` derin sunucu bloğu (`X = [1340,0; 1822,6] mm`, `Y = [−390; +390] mm`, `Z = [0; 297,3] mm`):
    - `s7_s9hpc_rail_psu_kit` (`3,80 kg`, `482,6×780×60 mm`): `2,6 kW` yedekli Titanium PSU & `19"` kızak tabanı;
    - `s7_s9hpc_decoder_node_1` & `s7_s9hpc_decoder_node_2` (`2× 28,00 = 56,00 kg`, `2× [482,6×780×88,9 mm]` = `4U 177,8 mm`, `5,0 mm` hava payı): `2× H100/Alveo-U280` sınıfı + çift `100G ConnectX-7 RoCEv2` (`d=37 16L` / `qLDPC 108L`, `0,777 µs` tek-yön erişim);
    - `s7_s9hpc_rocev2_switch` (`3,60 kg`, `1U 482,6×380×44,5 mm`) + `s7_s9hpc_qsfp28_fiber_duct` (`0,60 kg`, `4× QSFP28-100G-SR4 OM4` köprü = `4,20 kg`).
- **Toplam Makine Özeti (`cad_verification.json`):** **`199`** katı parça (`S1`–`S7`), **`1.108,14 kg`** (`v5.0` `1.034,94 kg` + `9,20 kg Option-Q` + `64,00 kg Option-HPC` = **`+73,20 kg`**, `BOM v6.0` ile gramına kadar eşit!), `CoM = (189,7; -8,3; 452,7) mm`, **`0 / 19.701` katı çakışma**, **`40 / 40` kritik boşluk PASS**, **`8 / 8` su geçirmez STL (`39.536` üçgen)**.

## Alt Sistem Kütle & Parça Özeti (`CAD v6.0`)

| Kod | Alt Sistem | Parça | Kütle (kg) | `v5.0 → v6.0` Fark | STL Üçgen |
|---|---|---:|---:|---:|---:|
| `S1` | `s1_ion_source_column` (+`S1.6` Option-Q) | 13 | 30,78 | +4,80 | 3.672 |
| `S2` | `s2_mems_write_head` | 9 | 1,83 | 0,00 | 2.496 |
| `S3` | `s3_ibic_detector_assembly` | 7 | 0,15 | 0,00 | 636 |
| `S4` | `s4_piezo_stage_interferometry` | 18 | 302,37 | 0,00 | 2.400 |
| `S5` | `s5_uhv_chamber_loadlock` (+`S5.5/S5.6`) | 29 | 193,94 | 0,00 | 4.732 |
| `S6` | `s6_cryo_dr_magnet_readout` (+`S6.5/S9.1`) | 105 | 285,32 | +4,40 | 25.204 |
| `S7` | `s7_electronics_rack_interconnect` (+`S6.5-01/S9.HPC`) | 18 | 293,75 | +64,00 | 396 |
| **Top.** | **`atom_litho_machine.stl`** | **199** | **1.108,14** | **+73,20** | **39.536** |

## Dosya Yapısı & Yeniden Üretim

- `params.py`, `mesh_engine.py`, `gen_scad.py`, `gen_stl.py`, `gen_drawings.py`, `preview.py`, `gen_dashboard.py`, `gen_v5_dashboard.py`, `gen_v6_dashboard.py`, `gen_v7_dashboard.py`
- `parts/s1..s7.scad` + `atom_litho_machine.scad` (8 parametrik OpenSCAD dosyası)
- `stl/s1..s7.stl` + `stl/atom_litho_machine.stl` (8 su geçirmez ikili STL) + `cad_verification.json`
- `drawings/01..10.{svg,png}` (10 adet `2400×1600` px ISO/ANSI teknik resim, `ALM-600-*`) + `drawings/00_v{3,4,5,6,7}_overview_dashboard.png` (`v7.0` kapak panosu dahil) + `preview_machine.png` (`2000×1020`)
- **`v7.0` Ön Tesis Emniyeti Ayrımı (`Exp150` / `BOM v7.0`, Sertifikasız `M0`):** `CAD v6.0` makine şasi-üstü (`on-frame`) nominal statik kütlesi **`1.108,137 kg`** (`199` parça, `0/19.701` nominal statik çakışma, `40/40` nominal zarf) değişmeden korunur; `S7.SAFETY-01..06` (`355,0 kg`, `1.090 W`, `0,0 W` kriyo) harici temizoda ön emniyet tasarım paketi (sertifikasız `M0`) olarak ayrı tutulur (toplam tesis yükü `1.463,137 kg`).

```bash
cd research/atom_lithography_machine/cad
python3 -B gen_scad.py
python3 -B gen_stl.py
python3 -B gen_drawings.py
python3 -B preview.py
cd ../../..
python3 -B -m pytest tests/test_cad.py -v
```
