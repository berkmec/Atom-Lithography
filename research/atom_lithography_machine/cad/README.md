# CAD Paketi v3.0 — Atom Litografi Makinesi (`Exp124` + `Exp125` + `Exp127` Kilitli)

Sürüm: `3.0-exp124-exp125-locked` (2026-11-22) · Birim: `mm` · Genel Tolerans: `ISO 2768-mK`  
Durum: **Kâğıt üzerinde parametrik konsept / ön-mühendislik CAD modeli (`no_lab_measurement=true`).** Fiziksel donanım veya laboratuvar ölçümü değildir.

## v3.0 Kilitli Mühendislik Mimarisi (`exp124_synced=True`, `exp125_synced=True`, `exp127_synced=True`)
- Eski `maglev_stage` ve `s=1,0` kalıntıları tamamen kaldırıldı; `s=0,5` altın zarf (`Exp80`) korundu.
- **`Exp124` Kilitli İyon Kolonu (`S1` + `S2`, Seçenek A Eş-Adımlı `Arch-B`):** Toplam yükseklik **`562,66 mm`** (`z_wafer = 500,00 → 1062,66 mm`), maks. `OD = 110,0 mm`, 8-kademe kolon kütlesi **`25,92 kg`**; HV şeması: wafer/kriyo/IBIC `0 V` toprak, üst kolon gömleği `−5,0 kV`, kaynak anodu `+5,0 kV`.
  - Aktif `Arch-B` dizisi: **`32×32 = 1.024` demetcik**, `S2.1` apertür + `S2.2` blanker + `S2.3` `Arch-B` mini-lens **eş-adımlı `0,50 mm`** → aktif kare **`16,0×16,0 mm`** (köşegen **`22,63 mm`**), `S2.4` **`16×` 64-kanallı SKY130 karo** (`1.024` kanal).
  - `S1.1` Duoplazmatron (`h=140, OD=90`), `S1.4` Kondansör (`h=45, OD=84`), `S1.2` Wien (`h=150, OD=110, 0,45 T`), `S1.5` `HDA-HiRes` enerji süzgeci (`h=95, OD=110, R₀=40 mm, ΔE_FWHM=0,453 eV`), `S1.6` Transfer lensi (`h=65, Ø28/Ø84`), `S2.1` Apertür & kinematik tutucu (`h=24, Ø28/Ø100` — köşegen `22,63 mm`'ye **`2,686 mm` temiz radyal marj**, sıfır demet kırpması), `S2.2` Eş-adımlı `0,50 mm` Blanker (`h=4, OD=60, Exp84 f₁=2,591 MHz`), `S2.3` `Arch-B` yavaşlatıcı mini-lens (`h=1,76, OD=60, WD=0,250 mm, E_gap=10,60 MV/m, C_c=2,660 mm`).
- **`Exp125` Kilitli 8-Bobinli Kriyo-Mıknatıs & Sessiz Rezonatör Bölgesi (`S6`):**
  - 8 kesin NbTi bobin (`M_upper/lower`, `S_upper/lower`, `A_upper/lower`, `B_upper/lower`): açık iç delik **`Ø150,0 mm`** (`r=75 mm`), orta düzlem yarığı **`36,0 mm`** (`z=482..518 mm`), dış karkas çapı **`Ø352,0 mm`** (`r=176 mm`), vakum-içi montajlı (`s=0,5` UHV oda `R_iç=182 mm` içinde `6 mm` radyal vakum boşluğu).
  - `z_loc = −155,0 mm` (`z = 345,0 mm`) konumunda **`Ø50 mm` NbTiN rezonatör diski (`|B| = 22,3 µT`)**, çevresinde **`Nb RRR>300` Meissner kabı** (`R=32..34,5 mm, z_loc=−174..−136 mm`, baca `r=8 mm, h=11 mm`) ve **`Cryoperm-10` dış kılıfı** (`R=39..41 mm, z_loc=−180..−124 mm`).
  - `S6.8` 5-kademeli `50K/4K/Still/CP/MXC (20 mK)` kuru seyreltme kriyostatı + `PT415/420` (`S6.1`) + `4 K` InP HEMT rafı + `56–82` koaksiyel demet.
- **`Exp127` Kilitli `S3` IBIC Ön-Uç:** `100 K` soğuk adada `LTC6268` CSA (`1,2 µs / 1 GΩ, ENC=24,1 e⁻, η=0,99936`) + `80×80 mm` AlN taşıyıcı (`Exp80 BC1`) + `Ø64/Ø78 mm` BeCu/Au kontak halkası.
- **Konumlandırma & UHV (`S4` + `S5`):** `6-DOF` piezo kademe (`S4.3`, `Exp79`), `Cryoperm (R=41)` ile `B`-bobinler (`R=56`) arasından `4 mm` radyal boşlukla geçen Invar tüp kaide (`R=45..52 mm`), Zerodur metroloji halkası + 3-eksen interferometre (`S4.4–S4.5`), `V_iç = 34,86 L` (`Exp80 BC4 PASS`) 4-portlu UHV oda (`S5.1`), turbo+iyon/TSP (`S5.2`), load-lock (`S5.3`), safir ms-flaş tavlama (`S5.5`).
- **Toplam Makine Özeti (`cad_verification.json`):** `143` katı parça (`S1`–`S7`), **`956,90 kg`**, `CoM = (141,3; -10,9; 443,3) mm`, **`0 / 10.153` katı çakışma**, **`19 / 19` kritik boşluk PASS** (`beam_array_diagonal_to_bore_clearance_mm = 2,686 mm`), **`8 / 8` su geçirmez STL (`30.048` üçgen)**.

## Dosya Yapısı & Yeniden Üretim
- `params.py`, `mesh_engine.py`, `gen_scad.py`, `gen_stl.py`, `gen_drawings.py`, `preview.py`
- `parts/s1..s7.scad` + `atom_litho_machine.scad` (8 parametrik OpenSCAD dosyası)
- `stl/s1..s7.stl` + `stl/atom_litho_machine.stl` (8 su geçirmez ikili STL) + `cad_verification.json`
- `drawings/01..10.{svg,png}` (10 adet `2400×1600` px ISO/ANSI teknik resim) + `preview_machine.png` (`2000×1020`)

```bash
cd research/atom_lithography_machine/cad
python3 -B gen_scad.py
python3 -B gen_stl.py
python3 -B gen_drawings.py
python3 -B preview.py
cd ../../..
python3 -B -m pytest tests/test_cad.py -v
```
