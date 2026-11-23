# CAD Paketi v4.0 — Atom Litografi Makinesi (`Exp124` + `Exp125` + `Exp127` + `Exp130` + `Exp131` + `Exp133` Kilitli)

Sürüm: `4.0-exp130-exp131-exp133-locked` (2026-11-23) · Birim: `mm` · Genel Tolerans: `ISO 2768-mK`  
Durum: **Kâğıt üzerinde parametrik konsept / ön-mühendislik CAD modeli (`no_lab_measurement=true`).** Fiziksel donanım veya laboratuvar ölçümü değildir.

## v4.0 Kilitli Mühendislik Mimarisi (`exp124/125/127/130/131/133_synced=True`)

- **Temel `v3.0` Çekirdeği (Korundu):** Eski `maglev_stage` ve `s=1,0` kalıntıları yok; `s=0,5` altın zarf (`Exp80`, `V_iç = 34,86 L` `BC4 PASS`), **`Exp124`** `562,66 mm / 25,92 kg` `10→5 keV` iyon kolonu (`32×32 @ 0,50 mm`, `16×16 mm` yazma alanı, `Ø28 mm` delikte `2,686 mm` radyal pay, `Arch-B WD=0,250 mm`, `HDA-HiRes ΔE=0,453 eV`), **`Exp125`** vakum-içi 8-bobinli `1,50 T` kriyo-mıknatıs (`Ø150 mm` bore, `36 mm` yarık, `Ø352 mm` OD, `z=−155 mm` `Ø50 mm` NbTiN `22,3 µT` + `Nb` Meissner + `Cryoperm-10`), **`Exp127`** `100 K` `LTC6268` IBIC CSA (`ENC=24,1 e⁻, η=0,99936`) ve `6-DOF` piezo kademe (`S4.3`).
- **`Exp130` (`S5.5`) Flaş-Tavlama Optik Kafası (`+Y`, `Z=500 mm`, CF63 Safir `Ø44 mm` CA):**
  - `s5_flash_window` (`Ø50×8 mm` AR kaplı safir, `Ø36 mm` demet → `4,0 mm` radyal marj), `s5_flash_safety_shutter` (`MXC < 1 K` & UHV vana kilitli mekanik deklanşör), `s5_flash_anneal_head` (`84×88×84 mm`, `808 nm` qCW `1,0 ms / 41,15 J/cm²` homojenleştirici), `s5_flash_dichroic_pyrometer` (`10 µs` iki-renkli InGaAs/Si pirometre) ve `s5_flash_fiber_collimator` (`σ_anneal = 0,328 nm`, `f_act = %99,98`).
- **`Exp131` (`M4`) Kavite-QED Veri Yolu & `4 K` Çapraz-Anahtar Kartı (`S3` / `S6`):**
  - `S6.8` DR `4 K` flanşı altında (`s6_hemt_rack_4k` iç boşluğunda, `HEMT`'e `26,4 mm` ve koaksiyellere `17,0 mm` payla) **`s6_m4_crossbar_4k_mount` + `s6_m4_crossbar_4k_pcb`** (`SKY130` `968`-kapılı çoklama kartı).
  - Yonga şartnamesi kilitli: `Δz_cap* = 8 ± 1 nm` `²⁸Si` epi kaplama, `3 kΩ` yüksek-empedanslı `NbTiN` veri yolu (`L_res = 300 µm`, `f_r = 5,0 GHz`), `B_M4 = 0,1785 T`.
- **`Exp133` (`PT420`) Mekanik Titreşim Ayrıştırma Paketi (`S6.1` / `S6.2`):**
  - Rijit OVC borusu yerine **kenar-kaynaklı 316L UHV CF63 körük** (`s6_ovc_bellows_cf63` + `7×` boğum halkası + UHV/DR flanşlar; `ID=44 mm, OD=68 mm, L_aktif=120 mm, k=2.000 N/m ≤ 6.282 N/m`).
  - Rijit `Ø7` bakır çubuk yerine **`Ø12×397 mm` DR OFHC barası (`s6_mxc_cold_finger`) + `4×` paralel S-ilmek OFHC Cu örgü (`s6_mxc_braid_1..4`, `2.550×Ø50 µm`, `L=100 mm`, `k=52,7 N/m ≤ 4.197 N/m`, `ΔT=3,7 mK @ 2,5 µW`)** — genişletilmiş `Ø18/Ø21 mm` `4 K` kalkan tüpü içinde (`3,0 mm` bara ve `3,32 mm` örgü radyal boşluk).
  - **`500 mm` ofsetli (`x = −1150 mm`) `PT420` uzak döner valf kutusu (`s6_pt420_remote_valve_box`) + akustik zemin sehpası + `600 mm` esnek He U-ilmek hattı** → `VC-E` kapalı-çevrimde `σ_stage = 0,102 nm`, `σ_pointing = 0,147 nm`, `σ_thermal = 0,028 nm`.
- **Toplam Makine Özeti (`cad_verification.json`):** `170` katı parça (`S1`–`S7`), **`993,27 kg`**, `CoM = (97,3; -9,9; 452,2) mm`, **`0 / 14.365` katı çakışma**, **`25 / 25` kritik boşluk PASS**, **`8 / 8` su geçirmez STL (`35.564` üçgen)**.

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
