# Yeni Nesil Atom Litografi Makinesi — Tasarım Belgesi v7.2 (`TRL 1–2 / M0`)

Tarih: 2026-10-19 (güncelleme `v7.2` gerçek açık-kaynak EDA + birleşik 164-parça CAD + gerçek `1% ²⁹Si` örgü banyosu + fiziksel kontrol yükseltmesi — 2026-11-27; `Exp0–Exp151`, **birleşik 164-parça su-sızdırmaz 3B CAD [`164p / 2.957,95 kg`, `0/13.366` çakışma, `32/32` kriyo termal, `10/10` GD&T; `10/10` KiCad 8 PCB `1.128/1.128` ağ `0` ERC/`0` DRC + `ngspice-47`]**, parametrik `BOM_DETAILED v7.0` [`180` satır, `50 mm` FOAK pul + `10-RFQ` taslağı], `[[288,12,18]]` `qLDPC` + dürüst FeMoco/RSA-2048 ufuk sınırları, `¹²¹Sb` `Q-Echo-8` + `SU(8)` GRAPE, gerçek EDA doğrulamalı `rtl/boed_fpga/` & `rtl/machine_ctrl/` Verilog RTL + `nextpnr-ecp5` vekili + `docs/digital_twin_interactive.html`, gerçek `1% ²⁹Si` banyo BOED kıyaslaması [`130,4 ms/aday`], `Exp150` sertifikasız `M0` ön emniyet taraması + `12,0 kWh` LFP UPS [`202,8 dk @ %90 DoD`], `CellISA v4.0` + `auto_recal.py` + `ibm_marrakesh` bulut QPU kontrol proxy & `Exp151` `39/39` + `parts_registry.json` `1.392/1.392` dosya bütünlüğü manifestosu). **Epistemik Sınır (`TRL 1–2 / M0/M1 DESIGN_ONLY`):**
- **Silikon `³¹P/¹²¹Sb/¹⁶⁷Er` fabrikasyon, birleşik 164-parça CAD (`2.957,95 kg`), `10/10` PCB (`ngspice-47`, tam 3B EM/FEM ön-üretim kapısı açık), parametrik `BOM v7.0`, `M1–M4` makine fiziği, gerçek `1% ²⁹Si` banyo BOED, `Exp150` sertifikasız ön emniyet taraması & `auto_recal.py`/`programmer.py`:** `TRL 1–2 (M0/M1 DESIGN_ONLY)` kavramsal sistem tasarımı ve indirgenmiş-mertebe çok-fizikli modellemedir (**`no_lab_measurement=true`, `no_supplier_quotes=true`, `iec61508_certified=false`, `semi_s2_certified=false`, `tapeout_done=false`**). `rtl/boed_fpga/` & `rtl/machine_ctrl/` konak makinede gerçek açık-kaynak EDA araçlarıyla (`iverilog 14.0`, `verilator 5.055 -Wall`, `yosys 0.71+101`, `nextpnr-ecp5` vekili; **`no_external_eda_sim=false`, `real_eda_verified=true`, `no_vendor_vivado_pnr=true`, `no_lab_measurement_rtl=true`**) doğrulanmıştır; SKY130 `blanker_tile` (`S8.2-02`) **`PRE_FOUNDRY_NCH8_MACRO_PROTOTYPE_NOT_TAPEOUT_READY`** (doğrudan `Yosys+OpenROAD+KLayout`, `LibreLane` yok) durumundadır. `SEMI`, `SEMI S2` için sertifika vermez; `IEC 61508 SIL-3` bağımsız fonksiyonel emniyet değerlendirmesi ve tedarikçi FMEDA verisi gerektirir. Tüm ön-kayıtlı `FAIL` hükümleri (Stim eşiği `%0,60–%0,98`, `Exp147` `UQ4/UQ5/UQ6 FAIL`: `FeMoco d=18` ve `RSA-2048 d=24` `p_fail_total=1,0`, `RSA-2048 d_req=174,1`) ve fiziksel duvarlar gizlenmeden raporlanır.
- **Kontrol yığını (`CellISA v4.0 → OpenQASM 3.0`), `Echo/XY4` DD, `d=3` sendrom dekoderi ve bit-kesin `Q16.16` BOED:** `156`-kübitlik süperiletken `ibm_marrakesh` (IBM Heron r2, `job_id = dc1tdo2nj2vs73dfrfl0`, `16 PUB × 4.096 shot`, `32,54 s`) üzerinde **bulut süperiletken-QPU kontrol/dekoder proxy kıyaslaması** olarak çalıştırılmıştır (**silikon fabrikasyonunu doğrulamaz**, `SECRET_LEAKS = 0`).
(Aktif geliştirme odağı 2026-11-22 kullanıcı kararıyla makineden devam etmektedir; eşlik eden ana belgeler: `TECHNICAL_MANUAL.md`, `MODULAR.md`, `M1_PROTOTYPE_BLUEPRINT.md`, `BOM_ENGINEERING.md`, `RFQ_SPECIFICATIONS.md`, `PROJECT_DOSSIER.md`, `rtl/boed_fpga/README.md`, `docs/digital_twin_interactive.html`.)

v2 değişikliği (2026-10-19): Exp65 (üretim hızı), Exp66 (konum hata bütçesi) ve Exp67
(kapalı-çevrim kazancı) sonuçları şartnameye işlendi; v1'deki "Exp65'te kesinleşir/fiyatlanır"
notları ölçülen (model) sayılarla değiştirildi. v1 metni DESIGN_v1.md olarak saklıdır.

## 0. Tek cümlelik tanım

Makine, silikon içinde **doğrulanmış ve programlanabilir evrensel atom yazmaçları** üreten bir fabrikadır: çok-demelli
bir mikro iyon implantasyon kafası aday atomları paralel yazar; soğuk-ada sayılmış-iyon algılaması her atışı
kayıt altına alır; kriyojenik spektroskopik ölçüm gerçek hatları çıkarır; yazılım çalışan yazmaçları seçer,
ölçülen hatlara özgü `XY8`-GRAPE kontrol darbelerini sentezler ve `CellISA` üzerinden sertifikalı kuantum
programları yürütür. Ürün "yerleştirilmiş atom" değil, **ölçülmüş, kalibre edilmiş ve programlanabilir çalışan yazmaçtır.**

Bu tanım projenin en sert bulgusunun doğrudan sonucudur: deterministik tek-site yerleştirme
gösterilmiş bir üretim yöntemi değildir (Exp57). Dolayısıyla makine, hassasiyeti tek atışta
aramaz; paralellik + algılama + seçim + kalibrasyondan üretir.

## 1. Görev tanımı ve ürün şartnamesi

Ürün birimi: bir **K=8 çekirdek-spin yazmacı** taşıyan donor hücresi (²⁸Si epitaksiyel katman
içinde ³¹P donoru + seçilmiş ²⁹Si çekirdekleri), şu kayıtlı kabul denetimleriyle (Exp48–61, Exp126–127):

1. Spektral kimlik: yazmaç hatları tekil adreslenebilir (geçiş boşlukları `≥ 5 kHz` ve Vandermonde rank `8/8`).
2. Evrensellik: K=4 çekirdek alt yazmacında Lie rank `1023/1023` (tam kontrol edilebilirlik; `Exp126`'da `16/16` bağımsız hücrede doğrulandı).
3. Dolaşıklık: tam `32`-boyutlu (`1e + 4n` + `448` seyirci + `J_ij`) iç-içe `XY8`-GRAPE bütçesinde **`Q_32D ≥ 0,85`** (`Exp126`, `f=%1`, `ε=10⁻³`: **`N=32` global optimum `α=1: 0,9260 / α=2: 0,9648`**; `N=64` `0,9209 / 0,9433`).
4. Depolama: `D0` sızıntısı `≤ 10⁻⁶` mertebesi (`Exp126`'da `16/16` hücrede `D0(17,5 s) ≤ 7,76×10⁻⁹` doğrulandı).
5. Kontrol & programlama paketi: o yazmaca özgü, `10–15 kHz` (`B₁ ≈ 1,2–1,8 mT`) RF paylı, `±400 Hz × ±%2` köşe-doğrulanmış `XY8`-GRAPE darbe seti (`Exp61`, `Exp126`) + **`CellISA v4.0` (`20` komut: `QRAM_SWAP`, `QLDPC_ROUND`, `AUTO_RECAL` dahil)** derleyicisi, **`BOED` + `Q16.16` FPGA DSP** (`2,336 µs/adım`, `Exp132/140`), otonom **`auto_recal.py`** (`4/4 PASS`), saf-`requests` **`cloud_qpu_bridge.py`** (bulut süperiletken-QPU kontrol vekili `156Q` `ibm_marrakesh` üzerinde koşturuldu — silikon `³¹P` doğrulaması değil, `Exp145`) ve SHA-256 imzalı `ProgramCertificate` (`src/machine_control/`, `Exp126–146`).

Kabul edilmeyen adaylar çip üzerinde ölü alan olarak kalır; makinenin çıktısı, üzerinde kaç
çalışan yazmaç olduğu **ölçümle sertifikalanmış** bir yongadır (wafer).

## 2. Mimari genel bakış

Kullanıcının beş temel fikri, proje kanıtıyla eşleştirilmiş alt sistemlere çevrilmiştir:

| Kullanıcı fikri | Alt sistem | Proje kanıt bağı |
|---|---|---|
| Çoklu iğne dizisi | MEMS çok-demelli iyon kafası (Bölüm 3) | Exp57 verim eğrileri: verim aday sayısıyla büyür |
| Paralel yazma | Alan-alan paralel implant + paralel okuma | Exp59: seçim verimi bollukla %51'e çıkar |
| Sıfır titreşim | Piezo kademe (Exp79'da maglev kaldırıldı) + aktif sönümleme + interferometri (Bölüm 5) | Hata bütçesi Exp66'da fiyatlandı (EUV σ_ekipman=2,36 nm; P91 1,95 nm, Exp91-BudgetAttack) |
| Hata geri beslemesi | Sayılmış iyon algılama + ölç-seç-kalibre (Bölüm 4, 7) | Exp48/50/61 kapalı-çevrim hattının donanım hâli |
| Oda sıcaklığı + lokal soğutma | RT gövde, lokal soğutulmuş yazma/ölçüm bölgesi (Bölüm 6) | SKY130 4 K ölçümleri (Exp33) kontrol elektroniği tarafıdır |

Ek genişletmeler (kullanıcının "genişletebilirsin" izniyle):

- **Seçim-verimi mühendisliği:** Makine hiçbir zaman tek aday yazmaz; her yazmaç yuvasına N aday
  yazar ve ölçüm sonrası seçim uygular. Bu, Exp48'in %61,5, Exp59'un %26–51, Exp57'nin σ'ya
  bağlı verimlerinin makine düzeyi karşılığıdır.
- **Ölçülen hata özgü kontrol:** Evrensel darbe arayışı Exp52–55'te %2–3 kilitli verimde kaldı;
  Exp61 GRAPE hattı %65 verdi. Makine bu yüzden evrensel darbe taşımaz; her yazmacın darbesi
  kendi ölçülen spektrumundan sentezlenir.
- **İzotop banyosu opsiyonu:** Substrat, Exp59/62'nin kazananı olan seyreltik ²⁹Si epitaksiyel
  katmanı (f≈%0,5, DD ile f=%1–2 de açık, Exp63) olarak da hazırlanabilir; implantasyon kafası
  bu durumda yalnız donorları yazar. İki mod da Bölüm 3.4'te tanımlıdır.

## 3. Yazma kafası: çok-demelli mikro iyon implantasyon dizisi

### 3.1 Neden "iğne" değil "demet"?
Mekanik iğneler (STM/AFM uçları) aşınır, tek tek kalibre ister ve milyon ölçeğinde
sürdürülemez. Yüklü-parçacık çok-demet teknolojisi ise endüstriyel olarak kanıtlıdır:
çok-demetli elektron litografisi (IMS Nanofabrication MBMW-101 sınıfı) 512.512 programlanabilir
demetciği tek apertür/blanker plakasıyla çalıştırır. Bu tasarım aynı mimariyi iyonlara taşır:
"1 cm²'ye milyon iğne" fikri, fiziksel olarak MEMS apertür dizisinden geçen paralel demetcikler olarak
gerçekleşir; Exp78–79 altın konfigürasyonu üretim ölçüm sınırlı olduğu için bunu `10³–10⁴` demetcik bandına
daraltmıştır (tarihsel `Exp78/79` `32 µm` elektron-yazıcı adımı yalnızca `Arch-C` alternatif notu olarak ayrılmıştır;
`v3.0` **`Arch-B` kilitli baz dizisi** `S2.1/S2.2/S2.3` tamamı eş-adımlı **`0,50 mm`**, **`32×32 = 1.024` demetcik**,
aktif kare **`16,0×16,0 mm`**, köşegen **`22,63 mm < Ø28,0 mm`** açıklık ve **`16×` 64-kanallı blanker karosu**dur).
Her demetcik bağımsız blanker (aç/kapa) elektroduna sahiptir.

### 3.2 Kafa katmanları ve 8-kademeli `10 → 5 keV` kolon (`Exp124` kilitli)
1. **İyon kaynağı (`S1.1`):** `PH₃` beslemeli duoplazmatron (`h=140 mm, OD=90 mm, 7,50 kg`, anot `+5,0 kV`; üst kolon astarı `−5,0 kV`, pul/IBIC `0 V` → `10 keV` üst kolon taşıma). `Exp124`, `_attack91.py` Liouville açığını kapattı: indirgenmiş parlaklık `B_r = B/E = 7,958 A/m²/sr/V` sabit olduğundan doğrudan `5 keV` çekim (`39.789 < 72.149 A/m²/sr`, `1,813×` açık, `r_geom = 2,020 nm`) yetersizdir; `10 keV` çıkarım + son yavaşlatma zorunludur (`CD1 PASS`). Üst kolon `10 keV` taşıması ayrıca laminar Coulomb bulanıklığını `2,83×`, Holtsmark/Boersch bulanıklığını `2,52×` bastırır (`N̄₁ = 1,40×10⁻³ < 0,01`, `CD5 PASS`). `S1.1` maliyet sınıfı `C` (`BOM.csv`); toksik `PH₃` kabini/yıkayıcı (`S1.6`, `< 50 ppb`) zorunludur.
2. **Yoğuşturucu (`S1.4`), Wien kütle seçici (`S1.2`), `HDA-HiRes` enerji süzgeci (`S1.5`) ve transfer (`S1.6`):**
   - **Wien (`S1.2`, `10 keV`):** `B = 0,45 T, L_w = 80 mm, L_d = 70 mm, V_p = 1.348 V` → `³¹P⁺ / ³²PH⁺` ayrımı **`dx = 0,785 mm`** (`3,92×` yarık, **`R_m = 120,6`**).
   - **`HDA-HiRes` (`S1.5`, zorunlu):** `R₀ = 40 mm, E_pass = 100 eV, slit = 0,35 mm` → **`ΔE_FWHM = 0,453 eV`** (`τ = 0,071`, `h = 95 mm, OD = 110 mm`). Eski `Exp82/91` `ΔE ≤ 2 eV` süzgeci yeni Scherzer alt sınırında yetersizdir.
   - **8-kademe toplam kolon (`S1+S2`, `Exp124/142` + `CAD v6.0`):** `Z_WAFER = 500,00 mm` çerçevesinde **`z_CAD: 500,25 → 1062,66 mm`** (`562,66 mm` toplam yükseklik), `S1.6`/`S2.1` iç açıklığı **`Ø28,0 mm`**, `max OD = 110,0 mm`, temel kütle **`25,92 kg`** (`CAD v6.0 S1` flanşlar + isteğe bağlı `Option-Q` `S1-Multi` `+4,80 kg` ile `30,78 kg`).
3. **Apertür plakası (`S2.1`, MEMS):** **`32×32 = 1.024` demetcik, eş-adımlı `0,50 mm`** (`16,0×16,0 mm` aktif kare, köşegen **`22,63 mm < Ø28,0 mm`** iç açıklık → **`2,69 mm` radyal marj**, sıfır demet kırpması); `S2.1` kinematik kafa taşıyıcısı (`h = 24 mm, OD = 100 mm, bore = Ø28,0 mm, 1,40 kg`).
4. **Blanker plakası (`S2.2`):** **`32×32 = 1.024` eş-adımlı `0,50 mm`** elektrostatik saptırıcı (`h = 4,0 mm, OD = 60 mm, −5000 ± 53,3 V`); atış süresi ve sayısı programlanabilir (`f₁ = 2,591 MHz`, `Exp84`), **`16×` 64-kanallı `S2.4` `blanker_tile.v`** (`100 MHz`, `1 ms` watchdog) ile sürülür.
5. **Mini lens dizisi (`S2.3`, `Arch-B` kilitli):** `Exp124` 2B eksenel Laplace (`spsolve`) + `DOP853` ışın izleme (Wronskian kayması `≤ 4,87×10⁻⁸`) temel bir fiziksel sınır keşfetti (**`CD3 FAIL` — Scherzer–delinme değişmezi**): `κ_c = C_c · E_gap / V_land ≥ 4,67` (`min 4,665`; `Arch-B: 5,640`). Bu nedenle `E_gap ≤ 12 MV/m` ve `5 keV` altında `Exp82/91`'in test edilmemiş **`C_c ≤ 0,50 mm` hedefi statik dairesel elektrostatik mercekle fiziksel olarak imkânsızdır**. Kilitli Liouville-tutarlı çözüm (**`CD4 PASS`**): **`Arch-B`** (**`32×32 = 1.024` demetcik, eş-adımlı `0,50 mm`**, `D = 0,30 mm, h = 1,76 mm, OD = 60 mm`, **`WD = 0,250 mm`**, **`E_gap = 10,60 MV/m`**, **`C_c = 2,660 mm`**, **`C_s = 10,786 mm`**, alansız `0 V` pul; alt `Arch-B15 15→5 keV`: `WD=0,480`, tarihsel alternatif `Arch-C 32 µm`: `WD=0,083`). `HDA-HiRes` ile birlikte:
   - `Ti = 0,25 eV, 10 ms` (veya `LMIS 1 ms`): `α_land = 6,10 mrad`, **`σ_spot = 1,428 nm ≤ 1,50 nm`**, **`σ_tot = 3,674 nm ≤ 3,80 nm`** (`4,42×10⁹` atış/gün `@10 ms`, `%50` duty).
   - Kanonik `Ti = 0,50 eV, 15 ms`: `α_land = 6,40 mrad`, **`σ_spot = 1,532 nm`**, **`σ_tot = 3,715 nm ≤ 3,80 nm`** (`1.024` demetçik → **`2,95×10⁹` atış/gün** — varsayılan `MachineConfig` girdileri altında koşullu matematiksel kapasite üst-sınırı; fiziksel makinede ölçülmüş throughput değildir). `Ti = 1,0 eV, 25 ms`: `1,605 / 3,746 nm`.
6. **Son yavaşlatma (`10 → 5 keV`) ve 3B anizotropik + donör saçılması (`Exp124`):** Çarpma enerjisi `5 keV` bazdır (`Exp92/105`: BCA yatay `σ_lat = 3,25 nm`, `σ_tot = 3,715–3,80 nm`). `Exp124` `CD6–CD8` (`400` deneme): sabit donörde 3B anizotropik BCA (`3,715 × 2,88 nm`, `z > 0`) verimi `%76,25` (`P91 BCA: %76,75`, `Holmes z>0: %69,50` — `CD7 FAIL` spektral sıkışma rahatlaması) olur; ancak **`³¹P` donörünün kendi 3B stokastik saçılması açıldığında Mod A verimi `%42,50`'ye (`P91 BCA: %43,75`, `−33,0 pp`; `Holmes: %28,00`, `−41,5 pp`) düşer (`CD8 PASS`)**. Ürün modu **Mod B** bu donör saçılmasına tamamen bağışıktır.

### 3.3 Atış protokolü (sayılmış implantasyon)
Her demetcik hedef yuvaya tek iyon atar; substrattaki algılama katmanı (Bölüm 4) iyonun
enerji bırakımını kaydeder ve blanker aynı yuvaya ikinci atışı ancak komutla yapar.
Deterministik sayım güveni (literatürde %99,87 sınıfı) yerleştirme saçılmasını telafi
etmez (Exp57 bulgusu); bu yüzden atış protokolü "tek atış tek yazmaç" değil,
**"yuva başına N aday atışı + ölçüm sonrası seçim"**dir. Yedek algılama modu: ikincil-
elektron sayımı (P'de ~%82 yayınlanmış verim) IBIC katmanı olmayan altlıklar için
şartnameye girebilir; seçim mimarisi bu verimi tolere eder (LITERATURE.md §1).

### 3.4 İki çalışma modu
- **Mod A (doğrudan ²⁹Si yazımı — AR-GE opsiyonu):** ²⁸Si substrata hem ³¹P donorları hem ²⁹Si çekirdek
  adayları implant edilir. `Exp124 CD8` gerçek 3B stokastik `³¹P` donör saçılması altında Mod A veriminin
  **`%42,50` (BCA) / `%28,00` (Holmes)** bandına indiğini gösterdiğinden Mod A kesin olarak araştırma modudur.
  Aday iyileştirme: `PF₂⁺` molekül iyonu (LITERATURE.md §1).
- **Mod B (banyo + donor — KİLİTLİ ÜRÜN BAZI):** Substrat önceden seyreltik ²⁹Si epitaksiyel banyosu taşır
  (Exp59/62 hattı); kafa yalnız ³¹P yazar, çekirdekler banyodan seçilir — **donör 3B saçılmasına tamamen bağışıktır**.
  **Şartname (`Exp68/126/129/136/139` `v5.0` kilitli):** `Exp136` atomistik `16.000`-atom / `160.000`-orbital `sp³d⁵s*`
  tight-binding modeli `Exp129` `VOKL-6` `%64,73` `R331` sapmasını **`%21,1`**'e (`α_cp=0`; `%25,7` @ `α_cp=0,015`, `log10-RMS=0,2426`)
  indirerek `f = %1,0` Mod B verimini **`%52,75`** (`M4` `%99,74`), **`f* = %1,5 + 2 MV/m` Stark** ile **`%77,50`** (DDRF `6,89 kHz`
  sınırlı **`%54,00`**, `M4` **`%99,88`**, kusurlu `d=7` yüzey kodu `d_eff/d = %99,5 @ N=6`) ve `f* = %2,0` ile **`%59,75`** (`M4` **`%99,99`**)
  olarak kanıtladı (`XY8 T₂e = 10,8–20,3 ms`; `M1 G6b ENDOR` kapısı yine zorunludur).
  **Zorunlu DD:** `XY8` (`CPMG` yasak), `N_total = 32–64` (`N = 32` optimum `0,9260 / 0,9648`), **RF `10–15 kHz`**, `ε ≤ 10⁻³`.
  **`v5.0` `1530 K` Flaş Tavlama + `S5.6` MBE Kapak (`Exp139`):** `v4` `1440 K`'daki gizli `+1,318 nm` arka-uç TED keşfi (`3,995 nm` FAIL)
  sonrası **`S5.5` `808 nm / 1,0 ms / 1530 K` (`43,49 J/cm²`, `%99,99` `{311}` temizliği, `σ_anneal = 0,430 nm`) + `S5.6` `8 nm` LT-MBE
  Rota C (`345 °C` + `350 °C` FG/H → `S_ε = 0,390 µeV/√Hz`, `p_ff = %97,70`)** kilitlenmiştir.

## 4. Kapalı çevrim I — soğuk-ada sayılmış iyon algılaması (`Exp127` & `src/board/`)

Her iyonun substratta bıraktığı elektron-delik yükü, yüzeyin altındaki koruma halkalı Si p-i-n algılama
diyotlarıyla okunur (IBIC). **`Exp127` (`tests/test_detector_frontend.py` `6/6` + `tests/test_machine_control.py` `12/12` + `tests/test_atom_programmer.py` `11/11`, QA `#52` KABUL)**,
tam Lindhard durdurma bölüşümü (`³¹P⁺ → Si`), sonlu GBP Laplace `H(s)` (ODE uyumu `%0,004`) ve Parseval gürültü integraliyle
kritik bir tasarım şartını kesinleştirdi:

- **Gerçek Lindhard Sinyali (`Exp72`'den ~%28 daha düşük):** `5 keV ³¹P⁺` için `Y_e = 0,2542` → **`351,2 e⁻ @ 300 K` / `341,7 e⁻ @ 100 K`** (`10 keV`: `792,0 / 770,8 e⁻`).
- **Oda Sıcaklığı (`300 K`) Çöküşü (`CZ3/CZ4 FAIL`):** `300 K / 200 ns / 100 MΩ` baz devrede `ENC = 89,92 e⁻ rms` → `5 keV` verimi **`η = 0,09722` (FAIL)**, `10 keV` `η = 0,97742` (`RT 1,2 µs / 1 GΩ`: `5 keV 0,6455`, `10 keV 0,99978`).
- **Kilitli Çözüm — `100 K` Soğuk-Ada Ön-Uç (`CZ5 PASS`):** `LTC6268` CSA (`Cf = 0,25 pF`, **`R_f = 1 GΩ`**) + `ADA4817-1` `CR-RC` şekillendirici (**`τ_s = 1,2 µs`**, net tepe kazancı `×50,0`, `t_peak = 1.218,4 ns`) + kanal-başı 16-bit `DAC8568` (`5,5σ` Rice eşiği) + `TLV3501` (`3,3 mV` histerezis, `4,5 ns`) + `49,9 Ω` `JFPGA` (`src/board/detector_frontend.net`: **`204` bileşen, `107` net, `0` ERC hatası** + `detector_frontend.cir`):
  - **`ENC(0,5 pF) = 24,07 e⁻ rms`**, **`P_false = 2,59×10⁻⁴ / 1 ms < 10⁻³`**, **`η(5 keV, 0,5 pF) = 0,99936`**, **`η(10 keV) = 1,00000`**.
  - `η ≥ 0,99` penceresi **`C_det ≤ 1,5 pF`**'ye kadar açıktır (`η = 0,99064`, `3×` parazitik kapasitans marjı); `1,2 µs` şekillendirme `1 ms` atış çevriminin `< %0,2`'sidir.
- **Kayıt & İzlenebilirlik:** Her atış (yuva kimliği, tür, enerji, algılama genliği) `Certificate` / `ShotRecord` JSONL veritabanında saklanır. Algılama "iyon geldi mi" sorusunu yanıtlar; "nereye oturdu" yanıtı Bölüm 7 spektroskopisidir.

## 5. Konumlandırma, `S6.9` `PT420` Ayrıştırma & Parametrik CAD v6.0 (`Exp133`, `Exp139–143`)

"Sıfır titreşim" fiziksel bir mutlak değildir; şartname, **toplam yerleştirme hatası bütçesinin** implant saçılmasını (`3,25 nm`) büyütmeyecek düzeyde (`≤ 3,80 nm`) tutulmasıdır. **`Exp133` (`8/8 PASS`, `12/12 pytest`)** rijit `PT420` köprüsünün (`CFG1`: `2.051,97 nm`) çöktüğünü kanıtlayarak **`CFG4` ayrıştırma zincirini** kilitlemiştir:

1. **Pasif zemin & `S6.9` `PT420` Ayrıştırma (`$68k`, `RFQ-07B`):** `VC-E` (`VC-G` ops.) granit + aktif masa + `500 mm` uzak valf + `600 mm` esnek He + `k_bellows = 2.000 N/m` 316L körük + `4×` OFHC Cu örgü (`k_braid = 52,7 N/m`, `ΔT = 3,7 mK`).
2. **Aktif sönümleme & Atermal Yapı:** `6-DOF` piezo (`43,57 Hz` PID + `25 dB` FF) + `Zerodur/Invar-36` (`20 mK`) → **`σ_stage = 0,1024 nm`**, **`σ_pointing = 0,1473 nm`**, **`σ_thermal = 0,0283 nm`**.
3. **Birleşik `v5/v6` Hata Bütçesi (`Exp124` + `Exp133` + `Exp139` + `Exp141`):** `Exp139` `v4` `1440 K` flaşta `+1,318 nm` gizli TED (`3,995 nm > 3,80` FAIL) keşfetti; **`v5/v6` `1530,1 K` (`σ_anneal = 0,430 nm`) + `CFG4`** birleşik bütçeyi **`σ_tot = 3,6307 nm (15 ms) / 3,5883 nm (10 ms) ≤ 3,80 nm`** (`Exp139`: `3,665 nm`) ile kapatır.

**Birleşik 164-Parça Mühendislik CAD Doğrulaması (`hardware/cad_parts/cad_parts_verification.json`, tek kanonik baz — `OBS-067`):** **`164` fiziksel katı parça** (`180` BOM satırı = `164` katı + `5` NRE/hizmet/gaz + `9` `S8.*` IN-HOUSE SW/RTL/EDA + `2` `$0` pointer), toplam kütle **`2.957,9454 kg`** (`S7.SAFETY = 355,0 kg`, `S9.HPC = 64,0 kg` dahil; eski `v6.0` `199p / 1.108,14 kg` şematik montaj yalnızca tarihsel arşiv olarak korunur), `164/164` su-sızdırmaz `.stl` (**`757.196` üçgen**, `0` açık/non-manifold kenar), **`0 / 13.366` küresel 3B katı çakışma**, **`32 / 32` NIST `0,02–423,15 K` kriyo termal kontrol**, **`10 / 10` GD&T yığını**, `32/32` açık optik/gaz görüş hattı (Möller–Trumbore) ve `S4.3-01` EDM fleksür CalculiX C3D10 FEA (`k_eff = 1,97–2,02 MN/m`).

## 6. Termal, `1530,1 K` + `S5.6` MBE, `D3` GRAPE `M4`, `[[144,12,12]]` `qLDPC` & `Option-Q` (`Exp125–144`)

- **`S5.5` `1530,1 K` Flaş & `S5.6` LT-MBE Rota C (`Exp130`, `Exp139`, `9/9 pytest`):** `808 nm / 1,0 ms / 1530,1 K` (`43,49 J/cm²`, `%99,99` `{311}` temizliği, `σ_anneal = 0,430 nm`) + `S5.6` LT-MBE (`22,4 kg`, `$95k`, `0 µW`, `%0` akış cezası) Rota C (`345 °C` `8 nm` `²⁸Si` + `350 °C` `FG/H₂` — `1 atm` ayrı fırınlama hücresi gerekir, `OBS-094`) → **`S_ε = 0,390 µeV/√Hz` (`2,57×` düşüş)**; **`≥150–200 °C` UHV fırınlama zorunludur** (fırınlamasız stres gaz salınımı `1,12×10⁻⁸ mbar > 10⁻⁹ mbar`, `OBS-124`). Gerçek sonsuz-alan ZBL/`iradina` 5 keV `³¹P⁺` saçılması (`σ_lat = 4,39–4,44 nm`, `Rp = 10,31 nm`) + vadi girişimi altında `M4` tünel kuplajı verim düşüşü (`OBS-006/039/047`) açık Faz-3 Ar-Ge duvarıdır.
- **Kriyo (`20 mK` DR), Düzlem-İçi Mıknatıs, `S6.5` MUX & `Option-Q` `qRAM` (`Exp125`, `Exp140`, `Exp142`):** Yatay düzlem-içi vektör mıknatıs (`B_∥ = 0,1785 T`, `NbTiN` dik `B_⊥` vorteks kaybı giderildi, `OBS-008`), iç içe `50 K / 4 K` UHV radyasyon/kriyopompa kalkanları (`OBS-010/046`), 5. derece Chebyshev Purcell süzgeci (`OBS-012`); `Option-Q` `7`-kademe toplu süperiletken `NbTiN` kriyo LC merdiveni (`50 Ω ↔ 3 kΩ`, `>200 Ω` T-hattı yok).
- **Dürüst QEC, `Stim` Eşiği, `qLDPC` & `Exp147` Ufuk Sınırları (`Exp137/138/143/144/147`, `OBS-022/023/030/045/124`):**
  - Gerçek **Stim devre eşiği `%0,60–%0,98`**'dir (eski tur-başı `%1,60` değil); sentetik sıkıştırmasız 4×4 Tosi + Route C (`S_ε = 0,39–0,55`) üst-eşikte kalır (`Exp137`/`138`/`143` `HORIZON_TARGET_REQUIRED`). `Option-HPC` gerçek C++ `ldpc` `BP+OSD-2` CPU süresi **`34,7–181,7 ms/vuruş`** (`%41,8–%90,0` OSD, depoda sıfır QEC dekoder RTL — `OBS-023`).
  - **`Exp144` (`4/7 PASS`) & `Exp147` (`3/7 PASS`, dürüst `UQ2/UQ4/UQ5/UQ6 FAIL`):** `BB_144/288` cebiri doğrulandıysa da düzlem-katlı yerleşim `10.372 / 24.256` hava köprüsü ve `%26,4 / %48,6` `>300 µm` Manhattan aşımı gerektirir (`OBS-045`). **`Exp147` D3 altında hem FeMoco (`d=18`) hem RSA-2048 (`d=24`) `p_fail_total = 1,0` (%100 başarısızlık) verir (`RSA-2048` için `d_req = 174,1`, `OBS-030`)**; `16` / `291` kriyostat sayıları yalnızca fiziksel hata `p_2q ≤ %0,15–%0,20` ve `p_meas ≤ %0,15` (`D3++`) sağlanırsa geçerli ayak-izi alt-sınırlarıdır.
  - **`Exp148` (`6/7 PASS`, `9/9` test — `Exp142 OQ6` Model İterasyonu):** Nötr `¹²¹Sb` (`473,9 kHz`) **`Q-Echo-8`** statik `500 Hz` gürültü modelini Gross **`0,5800 → 0,99908` (`455,5×` infidelite ↓)** & `|±7/2⟩` Cat **`0,9424 → 0,99914`** ile model uzayında giderir (deneysel doğrulama yok); `SU(8)` GRAPE `≥ 0,9954`; `1/f` `SQ4 FAIL` → `Q-Echo-64: 28,08× (1,45 ms)`; `B_M4 = 0,1785 T` spin karışımı dürüst sınır (`OBS-073`).

## 7. Kapalı Çevrim II — Gerçek-EDA Verilog RTL, `nextpnr-ecp5`, `12,0 kWh` UPS, `CellISA v4.0` & Bulut `ibm_marrakesh` QPU Proxy (`Exp126–151`)

1. **Yaz, Flaş, MBE & Ön Emniyet Tasarımı (`Exp139`, `Exp150`):** Mod B `100 K` IBIC + `1530,1 K` `S5.5` flaş + `S5.6` `8 nm` LT-MBE Rota C + **`S7.SAFETY`** (`PRELIMINARY_PARAMETRIC_CALCULATION_NOT_CERTIFIED`, `iec61508_certified=false`, `semi_s2_certified=false`: `25` FMEA `max RPN 280 → 42 ≤ 60`, IEC 61508-6 yüksek-talep `PFH` & `15`-durumlu `1oo2D` `λ_DU × β` duyarlılık taraması, RK4 oda ODH `60 m³ 0 ACH = %20,57` [havalandırmasız `≤15 m³` oda `%19,47 < %19,5` OSHA **yasaktır**], `SDS PH₃ 0,00715 ppm`, yükseltilmiş **`15 kVA / 13,5 kW / 12,0 kWh` LFP UPS: `202,8 dk @ %90 DoD ≥ 180 dk`** [`255,8 dk` nominal, `12,5 kW` PT420 şebeke tarafında], `80 ms` UHV vana).
2. **Gerçek-EDA Doğrulamalı Verilog RTL (`rtl/boed_fpga/`, `rtl/machine_ctrl/`), OpenROAD & HTML5 Gezgin (`Exp149`, `OBS-049/050`):** `verilator 5.055 --lint-only -Wall` `0` uyarı/hata, `iverilog 14.0 + vvp` `64/64` vektör + `4`-ch AXI4-Stream `0 LSB` / `584` çevrim (`2,336 µs @ 250 MHz`), `yosys 0.71+101` ön-P&R `xcup`/`xc7`/`ecp5`, **`nextpnr-ecp5` (`LFE5U-85F` vekili, `no_vendor_vivado_pnr = true`)**: `boed_q16_core 43,58 MHz`, `aom_pid_ctrl 34,34 MHz`, `cryo_mux_ddc_ctrl 69,76 MHz`, `fpga_top_carrier_wrap 79/205 TRELLIS_IO (%38,5)`. SKY130 `blanker_tile` (`S8.2-02`) **`PRE_FOUNDRY_NCH8_MACRO_PROTOTYPE_NOT_TAPEOUT_READY`** (`tapeout_done = false`). Çevrimdışı **`docs/digital_twin_interactive.html`** (`80,3 KB` / `80.339` bayt, `5` sekme, `0` CDN).
3. **Gerçek `1% ²⁹Si` Banyo BOED, Fiziksel `CellISA v4.0` / `auto_recal.py` & Bulut `156Q` `ibm_marrakesh` QPU Kontrol Proxy (`Exp145`, `results/boed_real_bath_benchmark.json`; **`621/621` çıplak `pytest`, `50` takip edilen suit**):** Gerçek `1% ²⁹Si` elmas-kübik örgü banyosunda (`45.214` konum, `N=260`) BOED **`%91,15`** vs Uniform `%84,62` (`130,4 ms/aday` [`Exp132` `41,0 ms`'nin `3,18×` yavaşı], `10,46×` prob / `26,29×` zaman hızlanması, `A_par RMSE=96,17 Hz`, eski `Exp132` `%100` FNR; dürüst `2 kHz` Fourier duvarı & `SNR ≤ 3` uçurumu). `auto_recal.py`: UHV Radau ODE, Si FVM PDE PID, dürüst step-and-stitch (`%100` kapsama / **`%61,51` dürüst verim**). Süperiletken **`ibm_marrakesh` (`156Q`, `job_id = dc1tdo2nj2vs73dfrfl0`, `0` sızıntı — silikon-dışı proxy):** Bare `0,3325` → XY4 `0,9280`, Bell `0,9733`, `d=3` MWPM `5,16×`, `Q16.16 BOED` `1,6 Hz`.

## 8. Uçtan Uca Model Kapasitesi, Parametrik BOM v7.0 (`10-RFQ`), `qLDPC` Ekonomisi & `Exp151` Dosya Bütünlüğü Manifestosu

**Bütçe tavanı (kullanıcı kararı, `Exp122`):** `50M USD` yumuşak sınır; **`100M USD` sert sınır.**
**Parametrik BOM v7.0 + `10-RFQ` taslağı + `Exp128 v7.0` (`no_supplier_quotes=true`) + `Exp151` (`8/8 DT7 PASS`) + `hardware/parts_registry.json` (`1.392/1.392` `%100` `SHA-256`):**
- Kanonik `BOM.csv` (`$2.531.244,37`, SHA-256 değişmez) ile `$0,00` iç mutabakat ve **tek birleştirilmiş 164-parça CAD kütlesi `2.957,9454 kg`** (`S7.SAFETY 355,0 kg` + `S9.HPC 64,0 kg` dahil; `180` BOM satırı, `50 mm` FOAK kanonik pul):
  - **`M1 Base` (korundu):** `$2.466.120` | **`M1 + Safety` (+Ön Emniyet Kiti, Sertifikasız `M0`):** **`$2.611.120`** (`355,0 kg` tesis) | `M3 Pilot` (`256`-hücre): `$4.790.400`
  - **`M3 v5.0 Base` (korundu, `167p`):** `$5.247.800` (`Prog P50 = $34,62M`, `P(>$100M) = %4,44 < %5`)
  - **Önerilen Faz-1 `M3 Base + Safety` (`173` satır):** **`$5.392.800`** (`Prog P50 = $35,48M`, **`P(>$100M) = %4,66 < %5`, `6/6 CU PASS`**)
  - **`M3 v6.0 Full` (`174p`):** `$5.547.800` (`%4,95`) | **`M3 v7.0 Full (+Ön Emniyet Kiti, Sertifikasız M0)` (`180` satır):** **`$5.692.800`** (`Prog P50 = $37,24M`, **dürüst `P(>$100M) = %5,22 > %5` [`CU3_v7_full FAIL`] → kademeli Faz-1 `Base+Safety` → `RFQ-05` fiyat kilidi → Faz-2 `+Option-Q/HPC`**).

`Exp151` Dosya Bütünlüğü ve İzlenebilirlik Manifestosu (`8/8 DT7 PASS`, `39/39` v7.2 artefakt + `7/7` ham disk baytı `SHA-256` doğrulandı — **yalnızca değiştirilmezlik kontrolüdür, bilimsel doğrulama değildir**, `OBS-123`):
- **`v7_digital_twin_cert.json`:** Ham Disk `SHA-256` = `65d3ed45899792bda06fa42a91134e6a2186a82c6388f534b005ee27e32456a2` · Kanonik Yük `cert["sha256"]` = `694cfe8420d73e22b66dbfb12a4a405894cc7bf3aaad6e95457ac660f2e4cd5b`
- **`docs/digital_twin_interactive.html` (`80.339` bayt):** Ham Disk `SHA-256` = `fcfbd62687233712a95ac5f7f388917df8a488427855e5b9cd0ff5df98b4c7ef`
- **`results/boed_real_bath_benchmark.json`:** Ham Disk `SHA-256` = `5ef83da01ffe635c362ec887a07f82ed043eaa03799403e3645e505551f055a8`
- **`ibm_qpu_live_results.json`:** Ham Disk `SHA-256` = `02b7a19d1704662c6424e76f4971e21b04a98d48230a917c9682853b3ca1fc5a`
- **Korunan tarihsel manifestolar (Ham Disk `SHA-256` / Kanonik Yük `cert["sha256"]`):**
  - `v6_digital_twin_cert.json`: `c46134b6e284be7851d714ff879970638c827a78f618082d71e6fbfd09faf001` / `ca3f0e0267263bacb973f46c3cc2d321c0f204075ea232f4094758e1a9abf1d7`
  - `v5_digital_twin_cert.json`: `336394f48f320f27127134f1055c55d5d7cda18496cc7c0599055ac81f7be055` / `2828e8ce8d9388f7cba5490b2d05add930aadc5fe6d3ba4295f0380f816d43d1`
  - `v4_digital_twin_cert.json`: `a8f723ab658942529d9ed245682618f6a3333d27a00d5c7bd17fce550907ef77` / `feffc1d4ba2b0698c3f61015c6684da47f57ea863a8b3e0da845cc9c71914b57`

| Sürüm / Mimari | `M4` / QEC / Modelleme | Kriyostat / Koşullu Kapasite | Ekonomi / Ön Emniyet | Parametrik BOM / Birleşik CAD / `pytest` |
|---|---|---|---|---|
| **`v3.0` (`Exp124–128`)** | `50 Ω` `0,791` / `P1 Λ = 0,00` | `1,973×10⁸`/gün (koşullu model) | `W1 $3,012/çip` (`$52,88 µUSD/reg`) | `145p` `$4,19M` / `143p` / `89` |
| **`v4.0` (`Exp129–135`)** | `3 kΩ` `0,9655` / `P1 Λ = 0,00` | `1,50–2,25G`/gün (`MachineConfig` koşullu üst-sınır) | `W1 $2,603/çip` (`CX4 FAIL`) / `$7,33 µUSD/reg` | `159p` `$4,61M` / `170p` / `142` |
| **`v5.0` Base (`D2` SC `d=99`)** | `P4` `p_err=%0,92` / `Λ = 1,40` | `100L`: `679` kriyo | `$5,20/L_fab` / `$14.939.541/L_sys` | `167p` `$5,25M` / `189p` / `198` |
| **`v6.0` Full (`[[144,12,12]]` `qLDPC`)** | `D3` `%0,337–%0,395`, `Λ=2,825`, `ibm_marrakesh` Proxy | `108L`: `1` kriyo (tarihsel iyimser model) | `$0,0085/L_fab` / `$63.827/L_sys` | `174p` `$5,55M` / `199p` (arşiv) / `252` |
| **`v7.2` + Stage-2 (`Exp147–151` + 164p CAD/PCB/RTL)** | **Gerçek EDA + `nextpnr-ecp5`, `1% ²⁹Si` BOED (`130,4 ms`, `%91,15`), dürüst Stim `%0,60–%0,98` & `Exp147` `p_fail_total=1,0`** | **FeMoco `16` / RSA `291` yalnızca `D3++` ayak-izi alt-sınırı (`d_req=174,1`); `%61,51` stitch** | **Sertifikasız `M0` FMEA `280→42` + PFH + `12,0 kWh` UPS (`202,8 dk @ %90 DoD`), Faz-1 `$5,39M (%4,66)` / Full `$5,69M (%5,22)`** | **`180` satır / `164p` (`2.957,95 kg`, `0/13.366`, `10/10` PCB `0` ERC/DRC) / `621` (`50` suit)** |

- **P91 geri beslemesi (Exp105):** Exp57 modeli σ<5 bölgesine ilk kez işletildi
  (denetim hücresi 49/100 birebir; `_yield105.py` 3B izotropik Gauss `σ_x=σ_y=σ_z=3,8 nm`
  varsayımıyla). Verim σ=3,8 nm'de **%69,25** (`277/400`, N=1024) — Exp91-BudgetAttack'in
  %49 tavan varsayımı çürüdü; `t_eff = 1,445 s` (`1,4448 s`). Mutlak maliyet o tarihteki
  39-satır zincir modelinde 1.619,8 (Exp106/114'te S6.8'siz 1.159–1.249, merkez 1.166) idi;
  **güncel 40-satır baz (Exp116/121, S6.8=D seyreltme dahil)** mutlak bedel **`2.159` (zincir B)
  / `2.166` (merkez ~17) / `2.249` (C)**, `NL163` altın oran **`0,4957 / 0,5215 / 0,6869`**'dur
  (`1 K` sıcak-okuma alternatifi `S6.8=C`: mutlak `1.259 / 1.266`, oran `0,4478`) — sabit taban
  baskın, σ kazancı maliyet denklemine yansımaz. Exp91-BudgetAttack'in üretim tablosu (hibrit
  çapa) geçersizdir; öz-tutarlı üretim (1000 demetcik, 1000 kanal, Mod A): `2,92×10⁷`/gün.
- Darboğaz her senaryoda ölçümdür; yazma kapasitesi iki mertebe boldur (AN1/AN6).
- Paralellik kötü verimi bile ürüne çevirir (σ=10 nm'de 1,26×10⁷/gün); mod seçimini hız
  değil **yazmaç başına maliyet** belirler: A σ=10, B f=%1'e göre ~17 kat spektroskopi ve
  ~17.500 kat atış tüketir. Yavaş-spektroskopi senaryosunda (10 s, 10² kanal) oranlar:
  B f=%1 2,20×10⁵/gün, A σ=10 1,26×10⁴/gün.
- Kapalı çevrim kazancı (Exp67): kör dozlamaya göre G = 4,7–7,9; η=0,9'da korunur.
- Bu sayılar 10⁴ paralel okuma kanalını **senaryo girdisi** olarak alır; kanal sayısı
  gösterilmiş teknoloji değildir (R4) ve ürün hızı doğrusal onunla ölçeklenir.
- **Altın konfigürasyon (Exp78):** üretim ölçüm sınırlı olduğundan analitik denge
  ~10 demetciktedir; kapsama/yedeklilik payıyla pratik bant 10³–10⁴ demetcik
  (16–157 karo) aynı üretimi verir. Sabit taban baskındır (Exp85: mutlak hedefte sabit
  pay %99,7; Exp106: zarf kolu yalnız −%3) — en büyük tekil maliyet kolu **`S6.8` kademesidir
  (`D↔C`, ±900 birim, Exp116/117/121)**, ardından zincir sınıfı (`B/C`, Exp114) ve `NL` (`110–160`)
  gelir; ancak Exp121 kullanıcı kararıyla risk-maliyet takasında sağlam baz (`S6.8=D`) önceliklidir.
  Tersine mühendislik veri hattı: REVERSE_ENGINEERING.md.
- **Sabit taban revizyonu (Exp79):** üretim blanker adımı 32 µm'dir (NuFlare
  US10658158B2) — altın bant dizisi 3,2 mm ile patentin yönetilebilir çarpıklık
  rejimindedir, 10⁶ demetcik (32 mm) dışındadır. S4.3 özel maglev yerine COTS
  kaba+ince piezo yığını (PI PIMars sınıfı; sub-nm çözünürlük, UHV sürümü) altın
  maliyeti referansın %55,1'ine indirir (BA4 kapandı). Kaba adımlama + S4.4/S4.5
  interferometrik çevrimi şarttır.

## 9. Risk Kapanış Matrisi (`v7.0` — `Exp124–151` Sonrası)

| Risk | Konu | `v7.0` Statü | Kapanış Kanıtı veya Kalan Açık İş |
|---|---|---|---|
| **5 keV Optik, IBIC & `PT420`** | Liouville/Scherzer, Lindhard `100 K`, `PT420` `CFG4` | **MODEL-İÇİ KAPANDI** (`Exp124/127/133`) | `Arch-B` + `HDA-HiRes` + `100 K` IBIC (`η=%99,94`, `0` ERC) + `S6.9` `CFG4` (`σ_stage=0,102 nm`). Lab `M1 G1–G3`. |
| **`R6` + Gizli TED & `S5.6` MBE** | Flaş difüzyon & `v4` `1440 K` `{311}` arka-uç TED | **MODEL-İÇİ KAPANDI (`Exp130/139`)** | `v5/v7` `1530,1 K` (`43,49 J/cm²`, `%99,99` temizlik, `σ_anneal=0,430 nm`) + `S5.6` LT-MBE Rota C (`S_ε=0,390 µeV/√Hz`, `p_ff=%97,70`) → `σ_tot=3,588–3,631 nm` PASS. Lab `M1 G4`. |
| **`R1`** | `³¹P–²⁹Si` atomistik bağ & optimal `f*` | **ATOMİSTİK DARALDI / `M1 G6b` AÇIK (`Exp136`)** | `160k`-orb `sp³d⁵s*` TB: `R331 %64,73 → %21,1`, `f*=%1,5 + 2 MV/m → %77,50` (`M4 %99,88`, `qLDPC d=18 %99,27` @ `N=8`). `M1 G6b` `ENDOR` & all-electron DFT açık. |
| **Evrensel `qLDPC d=18` & `T`-Fabrikası** | `10⁻⁹` derin rejim, FeMoco & RSA-2048 ölçeği | **KISMİ KAPANDI (`Exp147`, `5/7 PASS`)** | `[[288,12,18]]` `L_max=268,3 µm`, `p_th=%0,781`, FeMoco `16` kriyo (`37,1×`, `$6.537`), RSA-2048 `291` kriyo (`52,7×`, `7,37 MW`); dürüst `UQ4/5` okuma tavanı (`p_meas ≤ %0,15`) açık. |
| **`¹²¹Sb` `OQ6` Kuadrupol Kısıtı** | `500 Hz` statik & `1/f` gerinim gürültüsü | **MODEL UZAYINDA GİDERİLDİ / `1/f` DÜRÜST SINIR (`Exp148`, `6/7 PASS`)** | `Q-Echo-8` statik `500 Hz` Gross `0,5800 → 0,99908` (`455,5×` ↓; deneysel doğrulama yok), `SU(8) ≥ 0,9954`; `1/f` `SQ4 FAIL` → `Q-Echo-64: 28,08× (1,45 ms)`, Cat `20,73 ms`. |
| **`Q16.16` BOED Verilog RTL & Bulut QPU Proxy** | Sentezlenebilir RTL, `CellISA v4.0`, DD, `d=3` QEC | **GERÇEK EDA `0 LSB` + BULUT QPU PROXY (`Exp145/149`, VİVADO/SİLİKON AÇIK)** | `rtl/boed_fpga/` `1.193` LOC (`0` `/` bölücü, `verilator -Wall` `0` uyarı, `iverilog` `64/64` + `4`-ch `0 LSB` / `584` çevrim, `yosys` `xcup_top16` `1.584` DSP / `102.886` LUT / `96` BRAM36; `no_external_eda_sim=false`, `no_vendor_vivado_pnr=true`) + `ibm_marrakesh` (`dc1tdo2nj2vs73dfrfl0`, silikon-dışı proxy). |
| **Ön Emniyet Tasarımı (`PRELIMINARY_PARAMETRIC_CALCULATION_NOT_CERTIFIED`)** | Sınıf-4 lazer, `22 keV` X-ışını, `PH₃`, He ODH, EPO/UPS | **ÖN TASARIM TARAMASI (`Exp150`, SERTİFİKASIZ `M0`)** | `iec61508_certified=false`, `semi_s2_certified=false`; `25` FMEA `max RPN 280 → 42`, `15`-durumlu `λ_DU × β` taraması (`10× @ β=%10 → SIL-2`), RK4 ODH `60 m³ 0 ACH = %20,57`, `S7.SAFETY $145k / 355 kg` (`RFQ-10`; bağımsız SIL/SEMI S2 değerlendirmesi gerekir). |
| **`R4`, `R7`, `R2`, `R8`, `R5`** | `10-RFQ` `S6.6` (`%69,6`), Fazlı Bütçe, LNA, SKY130 | **AÇIK (Tedarikçi / Lab / Erteli EDA)** | `10-RFQ` (`%78,24 / %92,58`); **Faz-1 `Base+Safety $5,393M (%4,67 PASS)` → `RFQ-05` → Faz-2 `v7 Full $5,693M (%5,22)`**; `R7` LNA, `R8` EVPI `N_be=6,02`, `R5` (`Exp123`) erteli. |

## 10. Aşamalı yol haritası (`v7.2`, `TRL 1–2 / M0`)

- **M0 (`v7.2` + Stage-2 kavramsal tasarım, gerçek açık-kaynak EDA & sayısal fizibilite):** `Exp0–151`, **birleşik 164-parça su-sızdırmaz CAD (`2.957,95 kg`, `0/13.366` çakışma, `32/32` termal, `10/10` GD&T)**, `10/10` KiCad 8 PCB (`1.128/1.128` ağ, `0` ERC/`0` DRC + `ngspice-47`), `180`-satır parametrik `BOM_DETAILED v7.0` (`50 mm` FOAK pul) + `10-RFQ` taslağı, gerçek EDA doğrulamalı `rtl/boed_fpga/` & `rtl/machine_ctrl/` (`verilator`/`iverilog`/`yosys`/`nextpnr-ecp5` vekili; `no_vendor_vivado_pnr=true`), SKY130 `S8.2-02` `PRE_FOUNDRY_NCH8_MACRO_PROTOTYPE_NOT_TAPEOUT_READY`, `docs/digital_twin_interactive.html` (`80,3 KB`, `5` sekme, `0` CDN), gerçek `1% ²⁹Si` örgü banyosu BOED (`130,4 ms/aday`, `%91,15`), fiziksel `auto_recal.py` / `programmer.py`, `Exp150` sertifikasız `M0` ön emniyet taraması + `12,0 kWh` LFP UPS (`202,8 dk @ %90 DoD`), `ibm_marrakesh` bulut QPU kontrol proxy, `Exp151` `39/39` + `parts_registry.json` `1.392/1.392` `SHA-256` manifestosu ve **`621/621` çıplak `pytest` (`50` takip edilen suit)**.
- **M1 Base / `M1 + Safety` (`$2.466.120` / **`$2.611.120`**, `M1_PROTOTYPE_BLUEPRINT.md`):** Tek-demet `10→5 keV` (`100 K` IBIC) + `S5.5` `1530,1 K` + `S5.6` MBE + `S6.9` `PT420` + **`S7.SAFETY` ön emniyet tasarım kiti** (bağımsız `SEMI S2` / `IEC 61508` saha değerlendirmesi lab fazında) + `G6b` `ENDOR` `R1` ölçümü + `10-RFQ` teklifleri + Vivado `ZU48DR` P&R sentezi.
- **M2–M3 Fazlı Tedarik:** **Faz-1 `M3 Base + Safety` (`$5.392.800`, `173p`, `P(Prog>$100M) = %4,67 < %5`, `6/6 CU PASS`)** → `RFQ-05` fiyat kilidi → **Faz-2 `+Option-Q ($168k)` & `+Option-HPC ($132k)` (`M3 v7 Full = $5.692.800`)**.
- **M4 (`Exp143/144/147/148`):** `D3` GRAPE (`p_2q = %0,337–%0,395`) + `[[144,12,12]]` (`108L = 1` kriyo, `$63.827/L_sys`) → evrensel **`[[288,12,18]]` + `T`-fabrikası** (FeMoco `16` kriyo, RSA-2048 `291` kriyo / `7,37 MW`; okuma yükseltmesi `p_meas ≤ %0,15`) + nötr `¹²¹Sb` `Q-Echo-8` (`0,99908`).

## Ek — fizibilite deney programı (durum)

- Exp65–68, Exp124–128 (`v3.0`), Exp129–135 (`v4.0`, `ccde9b0`), Exp136–141 (`v5.0`, `a8d2506`), Exp142–146 (`v6.0`, `a9189ef`) — tamamlandı ve yayınlandı.
- **Exp147–151 (`v7.0`–`v7.2`, `TRL 1–2 / M0`):** `Exp147` (`H165`, `[[288,12,18]]` `qLDPC` & FeMoco/RSA-2048, `5/7 PASS`, `10/10`), `Exp148` (`H166`, `¹²¹Sb` `Q-Echo-8` & `SU(8)` GRAPE, `6/7 PASS`, `9/9`), `Exp149` (`H167`, gerçek EDA doğrulamalı `rtl/boed_fpga/` & HTML5 gezgin, `8/8 PASS`, `14/14`), `Exp150` (`H168`, sertifikasız `M0` `25`-FMEA/HAZOP, `λ_DU×β` sweep & RK4 ODH, `7/7 PASS`, `15/15`), `Exp151` (`H169`, `39/39` `SHA-256` dosya bütünlüğü manifestosu, `8/8 PASS`, `13/13`), + `boed_real_bath_benchmark.json` (`6/6`), + `test_control_physics_upgrades.py` (`14/14`).

Belge sürümü **`v7.2`**'dir (`2026-11-25`; `TRL 1–2 / M0`, `Exp0–Exp151`, nominal statik `CAD v6.0`, parametrik `BOM_DETAILED v7.0` + `10-RFQ`, gerçek-EDA doğrulamalı `rtl/boed_fpga/`, `docs/digital_twin_interactive.html`, gerçek `1% ²⁹Si` örgü banyosu BOED, fiziksel `auto_recal`/`programmer`, sertifikasız `S7.SAFETY` hedefi, `ibm_marrakesh` bulut QPU proxy, `Exp151` `39/39` dosya bütünlüğü manifestosu).

- **v7.2 (2026-11-25 — Gerçek Açık-Kaynak EDA + Gerçek `1% ²⁹Si` Banyo + Fiziksel Kontrol & Sertifikasız Emniyet Yükseltmesi):**
  - `Exp149` (`H167`, `8/8 PASS`, `14/14`, `no_external_eda_sim=false`, `no_vendor_vivado_pnr=true`, `no_lab_measurement_rtl=true`): `4+1` gerçek RTL donanım hatası giderildi (`0` `/` bölücü, bit-seri geri-yüklemeli bölücüler, `1.193` LOC); `verilator 5.055 --lint-only -Wall` `0` uyarı/hata; `iverilog 14.0 + vvp` `64/64` vektör + `4`-ch AXI4-Stream `0 LSB` / `584` çevrim (`2,336 µs`); `yosys 0.71+101` ön-P&R `xcup_top16` (`102.886` LUT, `59.157` FF, `192` RAMB18E2 / `96` BRAM36, `1.584` DSP48E2) + `xc7` (`5.467` LUT, `99` DSP) + `ecp5` (`3.871` LUT4, `106` MULT18X18D); `docs/digital_twin_interactive.html` (`78,7 KB`, `5` sekme, `0` CDN).
  - Gerçek `1% ²⁹Si` elmas-kübik örgü banyosu (`results/boed_real_bath_benchmark.json`, `6/6` `test_boed_real_bath`): `45.214` konum, `N=260` (`452,5` spin/donör), BOED `%91,15` vs Uniform `%84,62` (`10,46×` prob / `26,29×` zaman hızlanması, `A_par RMSE=96,17 Hz`, eski `Exp132` `%100` FNR; dürüst `2 kHz` Fourier duvarı & `SNR ≤ 3` uçurumu).
  - Fiziksel `auto_recal.py` & `programmer.py` (`14/14` `test_control_physics_upgrades`): 2-oda UHV ODE + Langmuir (`0,00784 L`, `0,002214 ML`), 1B doğrusal-olmayan Si termal PDE PID (`1532,82 K`), dürüst wafer-sahne step-and-stitch (`%100` kapsama / `%61,51` verim), exact 16B Lindblad + Gillespie-OU Echo-CZ (`F_Bell=0,9804`, `+0,212` kazanç), Exp140 dispersif mux (`N=32: 0,9954` vs `N=64: 0,9370`), exact GF(2) BB qLDPC Min-Sum BP+OSD.
  - `Exp150` (`H168`, `7/7 PASS`, `15/15`, `iec61508_certified=false`, `semi_s2_certified=false`): yanıltıcı `sil3_achieved` kaldırıldı; `15`-durumlu `1oo2D` `λ_DU × β` duyarlılık taraması (`10× @ β=%10 → 1,2245×10⁻³` `SIL-2`), RK4 oda ODH geçişi (`60 m³ 0 ACH = %20,57`), `25` FMEA `max RPN 280 → 42`, `S7.SAFETY = $145k / 355,0 kg`.
  - `Exp151` (`H169`, `8/8 PASS`, `13/13`) & `BOM v7.0`: `39/39` v7.2 artefakt + `1.392/1.392` Stage-2 dosya-bütünlüğü `SHA-256` manifestosu (`v7_digital_twin_cert.json` **Ham Disk `SHA-256 = 65d3ed45899792bda06fa42a91134e6a2186a82c6388f534b005ee27e32456a2`**, Kanonik Yük `cert["sha256"] = 694cfe8420d73e22b66dbfb12a4a405894cc7bf3aaad6e95457ac660f2e4cd5b` — yalnızca değiştirilmezlik kontrolü); **`621/621` çıplak `pytest` (`50` takip edilen suit) PASS**.

- **v6.0 (2026-11-23, Modüler Ölçekleme, `qLDPC` & Bulut IBM QPU Kontrol Vekili — `Exp142–146` + `CAD v6.0` + `BOM v6.0`/`9-RFQ` + `CellISA v4.0` + `Exp146` Master Dijital İkiz):**
  - `Exp142` (`H160`, `5/7 PASS`, `10/10`): `Option-Q` (`$168k / 9,20 kg`) — `5`-kademe Chebyshev (`0,0004 dB, 5,20 GHz`), `F_SWAP_rt=0,9858`, **`8.403×–25.122×` bellek ömrü (`+0,78 µW @ 20 mK`)**; `S1-Multi` `10 km` `¹⁶⁷Er` `1.352,3 Hz` (`F=0,9474`), `7,5 keV ¹²¹Sb` `−%41,5` saçılma (`OQ5/6` dürüst `FAIL`).
  - `Exp143` (`H161`, `4/7 PASS`, `9/9`): `D3` `K=8` Fourier GRAPE (`0,894 µs` muhaf. / `1,126 µs` yankılı, `%100 ≤ 300 MHz`): yankılı `Q=1e6, S=0,390 → p_2q=%0,395`, **`S=0,25 → p_2q=%0,337 (F_avg=%99,73, F_Bell=%99,69, Λ_D3_phys=2,825)`** (`100L SC: 679 → 100` kriyo); **`Option-HPC`** (`$132k / 64,0 kg / 2.195 W`): `τ_ingest=777 ns`, `d=37 SC 6,34 µs < 6,70 µs`, **`qLDPC 108L 2,32 µs < 2,62 µs`**.
  - `Exp144` (`H162`, `7/7 PASS`, `10/10`): **`[[144,12,12]]` Gross Code** `P_cell=20 µm → L_max=268,3 µm ≤ 300 µm` (`0` rezonatör değişikliği!), `f*=%1,5+2 MV/m, N_cand=8 → %99,64` blok / `%99,94` `108L` yonga verimi, `p_th=%0,633`, `D3+` `2,1×10⁻⁵/1L`, **`120L` tek `LD400` kriyostatta (`108L = 1` kriyo, `$63.827/L_sys`, `234×` ucuz vs `v5 D2`, `W3` fab `$0,0085/L`)**.
  - `Exp145` (`H163`, `7/7 PASS`, `12/12`): **Bulut süperiletken-QPU kontrol vekili (`156Q` `ibm_marrakesh`, `dc1tdo2nj2vs73dfrfl0`, `[2,3,4,5,6]`, `16 PUB × 4.096 shot`, `32,54 s`, `0` gizli sızıntı — `proxy`, silikon `³¹P` doğrulamaz):** Bare `0,3325` → Echo `0,9224` (`+59,0 pp`) → XY4 `0,9280` (`+59,5 pp`), Bell `0,9733`, `d=3` `p_phys=%2,96 → MWPM %0,57 (5,16×) / maj %0,38 (7,83×) / postsel %0,00`, `Q16.16 BOED` `120,11 kHz` (`1,6 Hz` vs FP64); **`CellISA v4.0` (`20` opcode)** & **`auto_recal.py` (`4/4 PASS`)**.
  - `Exp146` (`H164`, `8/8 PASS`, `10/10`), `CAD v6.0` (`199p, 1.108,14 kg, 39.536 STL, 0/19.701, 40/40, 30/30`) & `BOM v6.0` (`174p, M1 Base $2.466.120, M3 Base $5.247.800, M3 Full $5.547.800, 9-RFQ %77,7/%92,6, P(Prog>$100M)=%4,92 < %5`): `v6_digital_twin_cert.json` **`SHA-256 = ca3f0e0267263bacb973f46c3cc2d321c0f204075ea232f4094758e1a9abf1d7`**; **`252/252` (`28/28` dosya) yazılım regresyon testi PASS**.

- **v5.0 (2026-11-23, Hata-Toleranslı Dalga — `Exp136–141` + `CAD v5.0` + `BOM v5.0`/`8-RFQ` + `CellISA v3.5` + `Exp141` Master Dijital İkiz):**
  - `Exp136` (`H154`, `4/7 PASS`, `10/10`): `16.000` atom / `160.000` orbital `sp³d⁵s*` TB `R331`'i `%64,73 → %21,1` (`log10-RMS=0,2426`) indirdi; `f=%1 → %52,75`, **`f*=%1,5+2 MV/m → %77,50` (DDRF `%54,00`, `M4 %99,88`)**, `f*=%2,0 → %59,75`, `XY8 T₂e=10,8–20,3 ms`.
  - `Exp137` (`H155`, `4/7 PASS`, `8/8`) & `Exp138` (`H156`, `6/7 PASS`, `10/10`): `P4 Echo CZ` `δg` cezasını `5,09×` bastırır; `Exp139` Rota C ile `(Q=5e5, S=0,25)` **`F_Bell=0,9949, F_avg=0,9926, p_err=%0,92 < %1`**. Edmonds Blossom MWPM **`p_2q,th=%1,60 ± %0,17`**, `P1 Λ=0,00 → D2 Λ=1,40 (679 kriyo) → D3 Λ=2,52 (100 kriyo, 1 L/kriyo, 6,8× küçülme)`; `f*=%1,5+2 MV/m+N=6 → d_eff/d=%99,5`.
  - `Exp139` (`H157`, `4/7 PASS`, `9/9`): `v4` `1440 K` gizli `+1,318 nm` TED (`3,995 nm` FAIL) keşfedilip **`v5` `1530 K` (`43,49 J/cm²`, `%99,99` temizlik, `σ_anneal=0,430 nm`, `σ_tot=3,665 nm` PASS)** + **`S5.6` LT-MBE Rota C (`22,4 kg`, `$95k`, `S_ε=0,390 µeV/√Hz`, `p_ff=%97,70`)** ile model uzayında iyileştirildi.
  - `Exp140` (`H158`, `7/7 PASS`, `7/7`): `Q16.16` FPGA `abs(ΔRMS)=0,0502 Hz`, `2,336 µs/adım`, `%10,49` DSP48E2; **`N_mux*=32` (`F_RO=%99,61`, `625×` Purcell)**; `1.024` PASS / tek kriyo **`2.887` hücre** / `10k ≥ 4` kriyo; **`CellISA v3.5` (`17` opcode)**; `S6.5` (`19,27 kg`, `$629,2k`).
  - `Exp141` (`H159`, `8/8 PASS`, `9/9`), `CAD v5.0` (`189` parça, `1.034,94 kg`, `38.876` STL, `0/17.766` çakışma, `32/32` boşluk, `27/27`) & `BOM v5.0` (`167` parça, `M3=$5.247.800`, `M1=$2.466.120`, `8-RFQ %76,4/%92,6`, `P(Prog>$100M)=%4,23 < %5`): **`W2/W3` SOI senaryosuyla `CX4` model uzayında aşıldı (`−%79,5 / −%85,3`, `$0,616 / $0,442/çip`)**, `D2` `$/L_fab=$5,20` / `$/L_sys=$14,94M` vs `D3` `$0,73` / `$2,76M` (`5,41×`); `v5_digital_twin_cert.json` **`SHA-256 = 2828e8ce8d9388f7cba5490b2d05add930aadc5fe6d3ba4295f0380f816d43d1`**; **`198/198` (`23/23` dosya) yazılım regresyon testi PASS**.

- **v4.0 (2026-11-23, Gece `/goal` Dalgası — `Exp129–135` + `CAD v4.0` + `BOM_DETAILED v4.0` + `7-RFQ` + `BOED` & `CellISA v3.0` + Birleşik Dijital İkiz):**
  - `Exp129` (`H147`, `3/7 PASS, 4/7 FAIL`, QA `#130`): `VOKL-6` 6-vadi merkez-hücre modeli 4 `³¹P` değişmezini `< 10⁻¹⁰` (maks `7,36×10⁻¹¹`) tutturdu ama `[110]` ENDOR (`R331=%64,73`) başarısız kaldı (`CE3/4 FAIL`, DFT/Si `3d` gerekir); **kritik bulgu:** `f=%1` verimi `KL %50,50 → HM5962 %33,25` (`norm %4,75`), `min_gap < 6,893 kHz` `%57,9–%73,7` → Risk `R1` kapanmadı, `M1 G6b ENDOR` kapısı eklendi.
  - `Exp130` (`H148`, `6/6 PASS`, QA `#115`): Risk `R6` model-içi KAPANDI — `S5.5` (`$95k` `RFQ-07A`, `+Y` CF63 `Ø44 mm` AR safir) **`808 nm / 1,0 ms / 1440,3 K` (`41,15 J/cm² ± %5`)** in-line RT load-lock flaş tavlama (`f_act=%99,98`, `σ_anneal=0,328 nm ≤ 0,50 nm`, kayıp `%0,022`, `σ_iso=0,0314 nm`).
  - `Exp131` (`H149`, `4/7 PASS, 3/7 FAIL`, QA `#124`): `M4` `S6.10` (`$245k` `RFQ-07C`) — `Δz_cap* = 8,0 ± 1,0 nm` (`p_ff=%95,20`), `3 kΩ NbTiN` (`B_M4=0,1785 T`, `968` DC kapı) `F_Bell=0,9655` (`0,359 µs`; `50 Ω` `0,7908` çöküşü); dürüst `CM3/4 FAIL` (`≥0,99` için `S_ε ≤ 0,25–0,35 µeV/√Hz` veya `1/f` yankı şart); 2B Kare perkolasyon Heavy-Hex'e göre `−%40` aday tasarrufu.
  - `Exp132` (`H150`, `6/6 PASS`, QA `#121`): `adaptive_spectroscopy.py` + `--preset v400` (`$0` ek HW) `BOED` spektroskopiyi `1.000 ms → 41,03 ms` (`24,37×` ham, `RMS=72,67 Hz`, `FNR=%0,20`, `FPR=%0,00`) indirdi → yazma tavanı **`1,503–2,254×10⁹/gün` (`7,61×–11,42×`)**; **`CellISA v3.0`** (`14` komut) `4×4` Kraus `F_joint=0,983448`, `p_L=3,65×10⁻⁴` (`30,3×`).
  - `Exp133` (`H151`, `8/8 PASS`, QA `#118`): Rijit `PT420` `2.051,97 nm` çöker → **`S6.9` `CFG4`** (`$68k` `RFQ-07B`: `500 mm` uzak valf + `600 mm` He + `2.000 N/m` körük + `4×` OFHC Cu örgü `ΔT=3,7 mK` + `43,57 Hz` PID + `25 dB` FF + `Zerodur/Invar-36`) ile `σ_stage=0,1024 nm`, `σ_pointing=0,1473 nm`, `σ_thermal=0,0283 nm`, birleşik `σ_tot=3,578–3,620 nm`.
  - `Exp134` (`H152`, `5/6 PASS, 1/6 FAIL`, QA `#115`) & `Exp128 v4.0` (`QA #137`): `159`-parça `BOM_DETAILED v4.0` (`M3=$4.609.600`, `M1=$2.336.270`, `7-RFQ %92,6` MC var, `Prog P50=$30,87M, P(>$100M)=%3,38`), 5y Fab TCO `$16,07M` (`M1 $8,62M`), birim maliyet **`−%86,15 / −%90,77`** (`$52,88 → $7,33 / $4,88 µUSD/reg`; `HM5962 $11,24`), Wright `N=100` `$1,57M` HW; dürüst `CX4 FAIL` (`²⁸Si` yonga `%92,2` taban).
  - `Exp135` (`H153`, `7/7 PASS`, QA `#137`) & `CAD v4.0` (`24/24 pytest`): `170` katı parça, `993,267 kg`, `8/8` STL (`35.564` üçgen, `483,840 L`), `0/14.365` çakışma, `25/25` boşluk, `00_v4_overview_dashboard.png`, 8-katmanlı `v4.0` dijital ikiz (`SHA-256 feffc1d4...`), **`Exp131 × Exp129` çarpışması** (`KL/f=%2 N_cand*=6` vs `HM5962 f=%1 N_cand*=11` vs `norm N_cand*=86`).

- **v3.0 (2026-11-23, `Exp124–128` + `CAD v3.0` + `BOM_DETAILED` + `CellISA v2.0` + `TECHNICAL_MANUAL.md` tam mühendislik kilidi):**
  - `Exp124`: Liouville `10→5 keV` yavaşlatma, Scherzer–delinme `κ_c ≥ 4,67` (`CD3 FAIL` → eski `C_c≤0,50 mm` imkânsız), **`Arch-B`** (**`32×32 = 1.024` eş-adımlı `0,50 mm` dizi [`16,0×16,0 mm`, köşegen `22,63 mm < Ø28,0 mm` açıklık → `2,69 mm` marj; `16×` karo; `2,95×10⁹` atış/gün `@15 ms`]**, `WD=0,250 mm, C_c=2,660 mm, E_gap=10,60 MV/m`) + **`HDA-HiRes`** (`ΔE=0,453 eV`) → `σ_spot=1,428–1,532 nm, σ_tot=3,674–3,715 nm`, 8-kademe kolon (`Z_WAFER=500,00 → z_CAD: 500,25..1062,66 mm`, `562,66 mm / 25,92 kg`, UHV `R_iç=182,0 mm`), 3B anizotropik + stokastik `³¹P` donör saçılması (`Mod A %42,5 BCA / %28,0 Holmes` → Mod B baz kesinleşti).
  - `Exp125`: `8`-bobin `NbTi` mıknatıs (`Ø150/36/Ø352`, **`1,500000 T ± 17,81 ppm`**, `T_hotspot=64,6 K`) + `Nb (RRR>300)` (`117,1<135 mT`) + `Cryoperm-10` → **`22,3 µT`** (`R7` manyetik ayrıştırma KAPANDI); 5-kademe termal (`4K=0,325–0,899 W`, `MXC=3,94–4,80 µW`) & RF `SNR=10` (`0,0627/0,179 ms`); `R8` Koiller 6-vadi `W2 V2 p=0,9322`.
  - `Exp126`: Tam 32B CUDA (`1e+4n+448` seyirci+`J_ij`): **Risk `R3` KAPANDI** (`N=32` global optimum `α=1: 0,9260 / α=2: 0,9648`; `N=64`: `0,9209 / 0,9433`), DDRF seyirci duvarı keşfi (`N=128` yasak, **`10–15 kHz` RF payı** `1846×` kurtarma), **`XY8` zorunlu** (`+0,3245/+0,6189` vs `CPMG`), `16` heterojen hücre × `5` program (`Bell 0,9501`, `GHZ-4 0,9401`, `Grover-2 P(|11⟩)=0,9237`, `BitFlip-3 0,8878`, `QFT-3 0,8377`, doğal `CCZ 0,9338`, `D0≤7,76×10⁻⁹`, `16×` paralel).
  - `Exp127` + `src/board/` + `src/machine_control/` v2.0: Lindhard `5 keV → 341,7 e⁻ @ 100 K` (`RT 200 ns` `η=0,097` FAIL) → **`100 K / 1,2 µs / 1 GΩ` soğuk-ada `LTC6268`** (`ENC=24,07 e⁻`, `η=0,99936`, `C_det≤1,5 pF`, `204` bileşen / `0` ERC); taşınabilir Linux `AtlasSelector`, **`CellISA`** 10-komut ISA + SHA-256 `ProgramCertificate` (`35/35 pytest`).
  - `CAD v3.0`: `143` parça, `956,903 kg`, `0/10.153` çakışma, `19/19` kritik boşluk (`2,686 mm` dizi köşegen marjı), `8/8` su-geçirmez `.stl` (`468,627 L`), `10` çizim (`23/23 pytest`).
  - `BOM_DETAILED` + `6-RFQ` + `Exp128`: `145` parça (`BOM.csv` değişmez, `$0,00` köprü), **`M3=$4.189.600`**, **`M1=$2.189.770`** (`%82` taşınabilir), 6-RFQ `%92,8` MC varyansı, 100k MC (`BOM P50=$5,01M, P(>$50M)=%0`; `Prog P50=$28,24M, P(>$100M)=%2,69`), Tornado `S6.6 %77,27`, `1 K` EVPI `$0 @ N=1` (`N_be=6,03`).
  - Yeni ana belgeler: `TECHNICAL_MANUAL.md`, `M1_PROTOTYPE_BLUEPRINT.md`, `BOM_ENGINEERING.md`, `RFQ_SPECIFICATIONS.md`, `MODULAR.md v3.0-ICD`.

- v2.24 (2026-11-22, tek-klasör konsolidasyonu + Exp116–123 tam gövde senkronu): proje
  tek çalışma klasöründe (`atom_lithography_machine`) toplandı (`PROJECT_DOSSIER.md` eklendi). Gövdedeki 11 iç çelişki kapatıldı: başlık/sürüm `v2.24`,
  §3.1/§3.2/§5 altın bant (`10³–10⁴`) + `S1.1=C` + P91 (`σ_nokta ≤ 1,5 nm, Cc ≤ 0,5 mm`,
  10 keV çıkarım→5 keV yavaşlatma şartı), §6 4 K dışlama + `S6.8` baz / `Exp118`, §7.2
  `B_rez ≤ 0,4 T` + Elzerman/PSB, §8 40-satır baz maliyet (`2.159/2.166/2.249`) + `S6.8`
  maliyet kolu, §9 R4/R5 (`Exp119/120/123` — Attempt 2 `101` telsiz ağ sahte kapanış,
  Attempt 3b `2026-11-02 06:07` yarım) + R7/R8, §10 M3. Kullanıcı kararıyla aktif geliştirme
  odağı çip hattından değil **Atom Litografi Makinesi'nden** devam etmektedir.

- v2.2 (2026-10-20, Exp84): kalkan plakası rezonansı 2,59 MHz (FEM;
  analitik 2,68 MHz, oran 0,97) — servo bandından açık ara yüksek.
  Exp66 yüklemi SysON'da SysML kısıtı (SpotBudgetInt) olarak modellenip
  makineyle denetlendi: süzülmüş PASS (marj +0,404), çıplak FAIL (−0,089).
  Araç notu: mcp-syson çıkarıcısı LiteralRational (6.0) ayrıştıramaz;
  kısıtlarda tam sayı sabit kullanılmalı.
- v2.3 (2026-10-20, Exp85): maliyet iç yapısı çözüldü — baskın terim S6.6
  (%38,5); mutlak 10^6/gün hedefinde bedel 1599,9 (sabit pay %99,7).
  BOM.csv bu revizyonla senkron: S1.1 ve S4.3 sınıfı C, kademe piezo.
- v2.4 (2026-10-21, Exp91): çalışma noktası 5 keV (P91) — ΔE≤2 eV süzgeç,
  Cc≤0,5 mm, nokta 1,5 nm (parlaklık 7,22e4, süzülmüş net içinde),
  sigma_toplam 3,58 nm (Exp66 10 keV 5,53); IBIC eta(5 keV)=0,9914.
  Baskın terim saçılma (%70 varyans). Modüler arayüz kontratı: MODULAR.md.
- v2.23 (2026-10-26, kullanici onayi): butce kurali sertlesti - 50M cizgisi
  gerekmedikce asilmaz, 50-100M gerekce sartli (masaustu BUTCE_DURUMU.md),
  100M sert sinir. Su an asim yok.
- v2.22 (2026-10-26, Exp122): butce tavani 100M USD (kullanici karari) S8e
  islendi; tasarim BOM-kapsaminda 2,5-13,1M USD bandinda, tavan baglayici degil.
- v2.21 (2026-10-26, Exp121 kullanici karari): maliyet artisi serbest -
  seyreltme kademesi (D) baz; 1K sicak-okuma indirme alternatifi. Oran NL163
  merkezde 0,522, mutlak 2166; yeni baz NL55-B 0,5603/2159,0.
- v2.20 (2026-10-26, Exp120 FAILED): tek anten ihlalcisi (clk girisi) GDS
  yamasiyla kapanmadi (kisa devre/aciklik/envanter blogu); ECO tarifi koordinatli
  olarak OpenROAD donemine devredildi.
- v2.19 (2026-10-26, Exp119): GDS cikarimiyla kismi anten sayimi - kredili
  modelde tek ihlalci ag (oran 485, li1 adimi); kredisiz 84 (Exp103 ile birebir).
  Anten isi tek ag + ECO borcuna indi.
- v2.18 (2026-10-26, Exp118): yardimci-nokta baglasim verimi MC p~1,0
  (Exp92 sacilmasi; pencere 8 onluk >> dagilim 0,7 onluk). Exp117 acik riski
  model-ici emekli; altin oran degismedi (0,448 merkez).
- v2.17 (2026-10-26, Exp117): sicak okuma - donor kilitli okuma 3,7 Kde %97,8
  capali; S6.8 sinif D->C (1K kademe). Oran NL163 merkezde 0,448, mutlak 1266.
  Yeni baz NL55-B 0,5005/1259,0. Yardimci-nokta verimi acik risk.
- v2.16 (2026-10-26, Exp116): spektroskopi sicakligi - seyreltme kademesi sart
  (tek-donor pratigi ~100 mK; 4 K fizikce dislandi). BOMa S6.8 (sinif D) eklendi;
  oran NL163 merkezde 0,522, mutlak 2166. Yeni baz NL55-B 0,5603/2159,0.
- v2.15 (2026-10-26, Exp115): tutarlilik denetimi - govde Exp105-114 siciline
  senkronize (13 bayat grup/23 islem); maliyet modeli birebir korundu.
- v2.14 (2026-10-26, Exp114): zincir fiyati tersine muhendisligi - surekli
  sinif merkezi ~17 (bant 4-117), oran NL163te B/merkez/C = 0,401/0,438/0,658.
  BOM birimi 8,4x tutarsiz; B/C duvari yalniz LNA+izolator teklifiyle cozulur.
- v2.13 (2026-10-26, Exp113): ton butcesi - NL=163 capali sikisma sinirinin
  (NL_max=316) icinde; sart: ton gucu <=-100 dBm/kanal. Kayma 0,0012 cizgi
  genisligi (onemsiz). Dusuk-guclu bias degisimi NL~126 / oran 0,417.
- v2.12 (2026-10-26, Exp112): NL optimizasyonu - model optimumu Ql=1200de
  NL=164, oran 0,401 (izgara kosesi; sartname bandi NL 110-160 / Ql 800-1200).
  Kirpma sifir payda olu kol (CJ4 FAIL). Termal duvar NL>=110da kalkar.
- v2.11 (2026-10-26, Exp111): maliyet kapanisi - ikinci sogutucu orani
  0,493->0,497 yapiyor (ust sinir); tek-PT410 sartnamesi LNA <=2,8 mW/hat
  (2,1 mW InP HEMT capali, Rebelo 2026) veya PT420 yukseltmesi; oran
  NL=67de 0,471. Birinci-mertebe bilinmeyen yalniz zincir sinifi (B/C).
- v2.10 (2026-10-22, Exp110): termal butce - MXC rahat (5,2 uW/156 hat),
  dar bogaz 4K HEMT yuku (1,1-2,7 W); altin olcekte ikinci sogutucu
  gerekebilir (S6.1 notu).
- v2.9 (2026-10-22, Exp109): superiletken rezonator kolu kredili (NbTiN
  Qi~2e5 @mK, <=0,4 T rezonator alani; carpisma payla NL_eff~58-67);
  altin oran 0,493 (zincir sinifi B kosullu). Okuma mimarisi karari acik:
  toplu-LC (0,79) vs superiletken (0,49).
- v2.8 (2026-10-22, Exp107): sinif denetimi - COTS satirlarinda B/C ikiligi;
  mutlak bedel araligi ~770-1620 (gerekceli 1169), daraltma tedarikci teklifi
  ister. Altin oranin fiziksel kolu rezonator Q'su (Q=400 -> 0,445).
- v2.7 (2026-10-22, Exp106): sabit taban geniş (~14 C-satırı); zarf kolu
  tükendi (−%3). Kanal-ölçeği düzeltmesi (BOM miktar diliyle tutarlılık)
  mutlak bedeli 1169'a indirir (−%28); altın ölçek oranı 0,6002. Kalan
  taban satır bazında tedarikçi sınıfı doğrulaması ister (açık iş).
- v2.6 (2026-10-22, Exp104–105): kısmi anten mekanizması doğrulandı
  (cfg 8/8; büyüklük parantezi 6–3251 pin, OpenROAD 58 arada).
  P91 geri beslemesi: verim tavanı yok (%69 @σ=3,8), maliyet 1619,8'de
  sabit — ucuzlatma adresi sabit tabandır.
- v2.5 (2026-10-22, Exp92–103): BCA saçılmasıyla P91 σ=3,80 nm (hesaplanmış);
  kanalizasyon hattı kalibrasyonsuz kapandı. Çip sign-off ölçümleri tamam:
  DRC ana deste 0, mr destesi 0, LVS MATCH (yama elektriksel nötr),
  yoğunluk %15 decap dozuyla kapanır, anten korumasız 6 ağ (ham model).
  Altın maliyet son durumu (Exp87): zincir-basamak modeli oran 0,6035,
  mutlak hedefte 1619,8 birim. Blok düzeyi kalan işler ortam dışı:
  güncel OpenROAD (anten sıfır + ECO), OpenRCX SPEF, Crystal-TRIM, M1.
