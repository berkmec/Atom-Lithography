# Yeni Nesil Atom Litografi Makinesi — Tasarım Belgesi v4.0

Tarih: 2026-10-19 (tam **v4.0** gece dalgası mühürlemesi: `Exp0–Exp135`, `CAD v4.0`, `BOM_DETAILED v4.0` + `7-RFQ`, `BOED` & `CellISA v3.0`, `S5.5` Flaş Tavlama, `S6.9` `PT420` Ayrıştırma, `M4` `3 kΩ NbTiN` cQED & `Exp135` Birleşik Dijital İkiz — 2026-11-23). Durum: **kâğıt üzerinde tam mühendislik tasarımı + birinci-ilkeler sayısal simülasyon & EDA doğrulaması (`no_lab_measurement=true`, `no_supplier_quotes=true`, `tapeout_done=false`).** Bu belgede laboratuvar ölçümü, üretilmiş donanım, silikon tape-out veya fiziksel atom yoktur. Bütün sayılar bu deponun (`Atom-Lithography`) `Exp0–Exp135` model/sayısal-simülasyon/EDA kanıtlarına, üçüncü taraf ölçüm çapalarına (NIST `4 K` SKY130) veya açıkça etiketlenmiş literatür ölçeklerine dayanır; varsayım olan her sayı "varsayım" diye işaretlenir ve başarısız (`FAIL`) deney kontrolleri (`Exp124, 126, 127, 128, 129, 131, 134`) gizlenmeden raporlanır. (Aktif geliştirme odağı 2026-11-22 kullanıcı kararıyla çip hattından değil **makineden** devam etmektedir; eşlik eden ana belgeler: `TECHNICAL_MANUAL.md`, `MODULAR.md` [`v4.0-ICD`], `M1_PROTOTYPE_BLUEPRINT.md` [`v3.0`], `BOM_ENGINEERING.md`, `RFQ_SPECIFICATIONS.md` [`7-RFQ`], `PROJECT_DOSSIER.md`.)

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
5. Kontrol & programlama paketi: o yazmaca özgü, `10–15 kHz` (`B₁ ≈ 1,2–1,8 mT`) RF paylı, `±400 Hz × ±%2` köşe-doğrulanmış `XY8`-GRAPE darbe seti (`Exp61`, `Exp126`) + **`CellISA v3.0` (`14` komut: `WAFER_MAP_ROUTE`, `BUS_TUNE`, `BUS_CZ`, `LOGICAL_ENCODE` dahil)** derleyicisi, **`BOED` uyarlamalı spektroskopi** (`41,03 ms`, `Exp132`) ve SHA-256 imzalı `ProgramCertificate` (`src/machine_control/programmer.py`, `src/machine_control/adaptive_spectroscopy.py`, `Exp126–135`).

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
   - **8-kademe toplam kolon (`S1+S2`, `Exp124` + `CAD v3.0`):** `Z_WAFER = 500,00 mm` çerçevesinde **`z_CAD: 500,25 → 1062,66 mm`** (`562,66 mm` toplam yükseklik), `S1.6`/`S2.1` iç açıklığı **`Ø28,0 mm`**, `max OD = 110,0 mm`, kütle **`25,92 kg`** (`CAD S1` flanşlarla `25,98 kg`).
3. **Apertür plakası (`S2.1`, MEMS):** **`32×32 = 1.024` demetcik, eş-adımlı `0,50 mm`** (`16,0×16,0 mm` aktif kare, köşegen **`22,63 mm < Ø28,0 mm`** iç açıklık → **`2,69 mm` radyal marj**, sıfır demet kırpması); `S2.1` kinematik kafa taşıyıcısı (`h = 24 mm, OD = 100 mm, bore = Ø28,0 mm, 1,40 kg`).
4. **Blanker plakası (`S2.2`):** **`32×32 = 1.024` eş-adımlı `0,50 mm`** elektrostatik saptırıcı (`h = 4,0 mm, OD = 60 mm, −5000 ± 53,3 V`); atış süresi ve sayısı programlanabilir (`f₁ = 2,591 MHz`, `Exp84`), **`16×` 64-kanallı `S2.4` `blanker_tile.v`** (`100 MHz`, `1 ms` watchdog) ile sürülür.
5. **Mini lens dizisi (`S2.3`, `Arch-B` kilitli):** `Exp124` 2B eksenel Laplace (`spsolve`) + `DOP853` ışın izleme (Wronskian kayması `≤ 4,87×10⁻⁸`) temel bir fiziksel sınır keşfetti (**`CD3 FAIL` — Scherzer–delinme değişmezi**): `κ_c = C_c · E_gap / V_land ≥ 4,67` (`min 4,665`; `Arch-B: 5,640`). Bu nedenle `E_gap ≤ 12 MV/m` ve `5 keV` altında `Exp82/91`'in test edilmemiş **`C_c ≤ 0,50 mm` hedefi statik dairesel elektrostatik mercekle fiziksel olarak imkânsızdır**. Kilitli Liouville-tutarlı çözüm (**`CD4 PASS`**): **`Arch-B`** (**`32×32 = 1.024` demetcik, eş-adımlı `0,50 mm`**, `D = 0,30 mm, h = 1,76 mm, OD = 60 mm`, **`WD = 0,250 mm`**, **`E_gap = 10,60 MV/m`**, **`C_c = 2,660 mm`**, **`C_s = 10,786 mm`**, alansız `0 V` pul; alt `Arch-B15 15→5 keV`: `WD=0,480`, tarihsel alternatif `Arch-C 32 µm`: `WD=0,083`). `HDA-HiRes` ile birlikte:
   - `Ti = 0,25 eV, 10 ms` (veya `LMIS 1 ms`): `α_land = 6,10 mrad`, **`σ_spot = 1,428 nm ≤ 1,50 nm`**, **`σ_tot = 3,674 nm ≤ 3,80 nm`** (`4,42×10⁹` atış/gün `@10 ms`, `%50` duty).
   - Kanonik `Ti = 0,50 eV, 15 ms`: `α_land = 6,40 mrad`, **`σ_spot = 1,532 nm`**, **`σ_tot = 3,715 nm ≤ 3,80 nm`** (**`1.024` demetçik → `2,95×10⁹` atış/gün**, okuma sınırının `15×` üstünde!). `Ti = 1,0 eV, 25 ms`: `1,605 / 3,746 nm`.
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
  **Şartname (`Exp68` + `Exp126` 32B + `Exp129` `VOKL-6` + `Exp130` Flaş Tavlama kilitli):** ürün bolluğu **`f = %1`**
  (`KL` tek-atış seçim verimi `%50,50`, 3-atış `%87,92`; **DÜRÜST `Exp129` RİSK `R1` BULGUSU:** `VOKL-6` 6-vadi merkez-hücre
  modeli gerçek Hale–Mieher `5,962 MHz` ölçeğinde tek-atış verimini **`%33,25`**, eski `2,981 MHz` ölçeğinde **`%4,75`** olarak
  verir ve `min_gap < 6,893 kHz` oranını `%57,9–%73,7`'ye çıkarır — **`M1` `G6b` `ENDOR` doğrulaması zorunludur**!),
  **zorunlu DD sekansı `XY8` (`CPMG` yasak — `+0,3245/+0,6189` üstünlük)**, **darbe sayısı `N_total = 32–64`**
  (**`N = 32` global optimum: `α=1: 0,9260 / α=2: 0,9648`**; `N = 64`: `0,9209 / 0,9433`; **`N = 128` DDRF duvarı yasak**),
  **RF NMR bobini genlik payı `10–15 kHz` (`B₁ ≈ 1,2–1,8 mT`)**, darbe-başına hata **`ε ≤ 10⁻³`** ve **implantasyon sonrası
  `S5.5` `808 nm / 1,0 ms` (`41,15 J/cm² ± %5`, `1440,3 K`) flaş tavlama (`f_act = %99,98`, `σ_anneal = 0,328 nm ≤ 0,50 nm`,
  yüzey+vakum kaybı `%0,022`, `Exp130`)**. `α=2` (veya `G6b` düşük `f=%1` verimi) durumunda **`f = %2`** (`KL %67,0`, `HM5962 %54,5`,
  `Q_32D = 0,9195`, `M4 N_cand* = 6`) yükseltme yoludur.

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

## 5. Konumlandırma, `S6.9` `PT420` Titreşim Ayrıştırma & Parametrik CAD v4.0 (`Exp133`)

"Sıfır titreşim" fiziksel bir mutlak değildir; şartname, **toplam yerleştirme hatası bütçesinin** implant saçılmasını (`3,25 nm`) büyütmeyecek düzeyde (`≤ 3,80 nm`) tutulmasıdır. **`Exp133` (`8/8 PASS`, `12/12 pytest`, QA `#118`)** `40`-elemanlı üst-kolon FEM (`f₁ = 118,178 Hz`) ve birleşik PSD/servo çözümüyle rijit `CAD v3.0` `PT420` köprüsünün (`CFG1`: **`σ_stage = 2.051,97 nm`**; yalnız `25 dB` FF `CFG5`: `145,59 nm`; yalnız mekanik `CFG2`: `1,006–2,362 nm`) çöktüğünü kanıtlayarak **`CAD v4.0` `CFG4` ayrıştırma zincirini** kilitlemiştir:

1. **Pasif zemin & `S6.9` `PT420` Ayrıştırma (`$68k`, `RFQ-07B`):** `VC-E` (ops. `VC-G`, `3,76×` ek işaretleme payı) tabanlı granit + hava yaylı aktif masa + **`500 mm` uzak döner valf + `600 mm` esnek He hattı + `k_bellows = 2.000 N/m` (`≤ 6.282`) 316L CF63 körük + `4×` S-halka OFHC Cu termal örgü (`k_braid = 52,7 N/m ≤ 4.197`, `ΔT = 3,7 mK`)**.
2. **Aktif sönümleme & Harmonik FF:** `6-DOF` UHV piezo kademesi (`S4.3`, maglev kaldırıldı) + **`43,57 Hz` PID** (`PM = 55,23°`, `GM = 8,69 dB`, `||S||_∞ = 1,676`) + **`25 dB` senkron harmonik FF** → **`σ_stage = 0,1024 nm`**, **`σ_pointing = 0,1473 nm`**.
3. **Atermal Yapı & İnterferometri:** 3-eksen `pm` lazer interferometre + **`Zerodur` optik köprü + `Invar-36` kaide** (`20 mK` termal kararlılık → **`σ_thermal = 0,0283 nm`**; çıplak `316LN` `1,935 nm` RED).
4. **Birleşik Hata Bütçesi (`Exp124` + `Exp133` + `Exp135`):** `Arch-B` + `HDA-HiRes` + `CFG4` birleşik yerleştirme hatası **`σ_tot = 3,6201 nm (15 ms) / 3,5776 nm (10 ms) ≤ 3,80 nm`** (`Exp133` `Exp124`-çapalı: `3,6397 / 3,5974 nm`; rijit `CFG1`: `2.076,97 nm` RED).

**Parametrik CAD v4.0 Doğrulaması (`research/atom_lithography_machine/cad/cad_verification.json`, `4.0-exp130-exp131-exp133-locked`, `tests/test_cad.py` `24/24 PASS`, QA `#137` KABUL):** **`170` katı parça**, toplam kütle **`993,267 kg`** (`S1 25,98`, `S2 1,83`, `S3 0,15`, `S4 302,37`, `S5 171,54` [`S5.5` flaş tavlama dahil], `S6 273,15` [`S6.9` `PT420` + `S6.10` `M4` cQED dahil], `S7 218,25 kg`), `CoM = (97,25; −9,90; 452,25) mm`, `483,996 L`, `8/8` su-geçirmez `.stl` (**`35.564` üçgen**, **`483,840 L`**, `0` açık/non-manifold kenar), `10/10` `ALM-400-*` teknik çizim (`2400×1600` `.png`/`.svg`) + `00_v4_overview_dashboard.png`, **`0 / 14.365` katı çakışma** ve **`25 / 25` kritik boşluk PASS** (`WD = 0,25 mm`, `32×32` dizi köşegeni ↔ `Ø28 mm` delik `2,686 mm`, `+Y` CF63 `Ø44 mm` `S5.5` safir pencere, `S6.9` körük/Cu örgü boşlukları, `S6.10` `M4` cQED paket zarfı).

## 6. Termal, Flaş Tavlama & Manyetik Mimari — `S5.5` (`Exp130`), `20 mK` DR, `1,50 T / 22,3 µT` (`Exp125`) & `M4` cQED (`Exp131`)

- **Oda sıcaklığı gövde + `100 K` IBIC + `S5.5` Flaş Tavlama (`Exp130`, `6/6 PASS`, Risk `R6` Model-İçi KAPANDI):** Gövde, UHV oda ve MEMS kafa RT'de, IBIC ön-ucu `100 K` soğuk adada (`Exp127`) çalışır. İmplant sonrası aktivasyon için fırın (`600 °C/10 dk`: `%93,2` yüzey yığılması; `800 °C/10 dk`: `%52,7` vakum kaçışı) ve RTA (`1000 °C/10 s`: `σ = 4,97 nm`, `%21,2` kayıp) dışlanmıştır. Kilitli **`S5.5` (`$95k`, `RFQ-07A`)** in-line RT load-lock **`808 nm / 1,0 ms / 1440,3 K` (`F = 41,15 J/cm² ± %5`)** ms-flaş tavlama (`+Y` CF63 `Ø44 mm` AR safir pencere, `T_AR = %98`, `9,47×` LIDT, `10 µs` pirometre, `MXC < 1 K` + UHV perde kilidi) **`f_act = %99,98`**, **`σ_anneal = 0,328 nm ≤ 0,50 nm`**, yüzey+vakum kaybı **`%0,022`**, `²⁹Si` karışma **`σ_iso = 0,0314 nm`**, arka yüz `592,9 K` ve `0,00 dk / 0 J` kriyo kayıp (`16×16 mm` kriyo-içi yedek: `3,18 dk`) verir. `IBIC × flaş` birleşik sağkalımı **`%99,914`** (`Exp135`).
- **Lokal soğutulmuş ölçüm adası (`S6.8` & `S6.1` & `S6.9`, `Exp116–121`, `Exp125`, `Exp128 v4.0`):**
  - `4 K` tek-donor spin spektroskopisi `Exp116`'da dışlanmıştır (`%6,71` polarizasyon). **BAZ kademe** `S6.8 = D` **seyreltme ünitesidir (`MXC ~20 mK`, `S6.1` `PT420` + `S6.9` ayrıştırma)**. `Exp128 v4.0` EVPI: `N = 1` ilk makinede `EVPI = $0`, başa-başı **`N_be = 6,01` makine** (`1 K` Mod B `3,40×` yavaş).
  - **5-kademe termal bütçe (`Exp125 CV4 PASS` + `Exp133` `ΔT = 3,7 mK` Cu örgü):** `NL=163` (`56` hat, `2,1 mW` HEMT): `50K = 7,54 W`, **`4K = 0,325 W`**, `Still = 1,14 mW`, `CP = 54,5 µW`, **`MXC = 3,94 µW < 19 µW`**. Kanonik `NL=160` (`57` hat, `7,8 mW` HEMT): **`4K = 0,654 W`**, `MXC = 3,97 µW`.
- **8-bobinli `NbTi` Mıknatıs & Çift-Katmanlı Meissner Kalkanı (`S6.3`, `Exp125`, Risk `R7` Manyetik Ayrıştırma KAPANDI):** `Ø150 / 36 / Ø352 mm`, `18,941 kJ`: örnekte **`B_z(0,0) = 1,500000 T ± 17,81 ppm`**, `I/I_c = 0,212`, `T_hotspot = 64,6 K`; `z_loc = −155 mm` `NbTiN` diskinde `Nb (RRR>300)` + `Cryoperm-10` ile **`max |B_res| = 22,3 µT`**.
- **`M4` Ölçeklenebilir cQED & 2B Perkolasyon Mimarisi (`S6.10`, `$245k` `RFQ-07C`, `Exp131`, `4/7 PASS, 3/7 FAIL`, QA `#124`):**
  - `4×4` Tosi flip-flop: kapaksız `Δz_cap = 0` çöker (`%24,15`); optimal **`Δz_cap* = 8,0 ± 1,0 nm`** `²⁸Si` kapağı + yerel DC ayarı **`p_ff = %95,20`**, medyan `C = 2.800,1`, `g_eff = 0,620 MHz` verir.
  - Tam `12×12` Lindblad (`20 mK`, `60` çift): `50 Ω` CPW **`F_Bell = 0,7908`** (`2,78 µs`) ile çöker; **`3 kΩ NbTiN`** (`L_res = 300 µm`, **`B_M4 = 0,1785 T`** [`%40,5` pay], `P_node = 10 µm`, `968` DC kapı `4 K SKY130` çapraz-çubuk) **`F_Bell = 0,9655`** (`0,359 µs`, `M4 Best-of-6`; seçimsiz `0,9386`) sağlar. **Dürüst gürültü sınırları (`CM3/CM4 FAIL`):** yankısız `S_ε = 0,5 µeV/√Hz` `0,9877`, Tosi `S_ε = 0,25 µeV/√Hz` yüzey-kodu eşiği **`0,9907–0,9918`** verir; adyabatik `CZ` (`0,9982` gürültüsüz) `S_ε = 1,0`'da `0,7768`, `S_ε = 0,25`'te `0,9392` (medyan `0,9554`) olur → **`S_ε ≤ 0,25–0,35 µeV/√Hz` veya `1/f` yankısı şarttır**.
  - 2B Perkolasyon (`L=11` FT `≥ %99`, `Exp131` × `Exp129` `Exp135 L6`): 2B Kare örgü Heavy-Hex'e göre (`CM6 FAIL` @ `N=4`, `N=5` ister) **`−%40` aday tasarrufu** sağlar; `KL` için **`N_cand* = 6`** (`%99,24`), ancak **`VOKL-6 HM5962 f = %1`** altında `N_cand = 6` **`%3,12`**'ye çöker → **`N_cand* = 11`** (`%99,74`) veya **`f = %2` → `N_cand* = 6`** (`%99,92`) gerekir (`VOKL-6 norm`: `N_cand* = 86` kırmızı çizgi!).

## 7. Kapalı çevrim II — `BOED` Spektroskopi, Seçim, Kalibrasyon & `CellISA v3.0` (`src/machine_control/` v3.0 + `Exp126/132/135`)

Bu katman, projenin `Exp44–61` + `Exp125–135` hattının eksiksiz donanım ve yazılım iş akışıdır:

1. **Yaz & Tavlama:** Mod B'de `100 K` soğuk-ada IBIC sayımlı `³¹P⁺` implantasyonu + `S5.5` `808 nm / 1,0 ms` flaş tavlama (`%99,914` birleşik sağkalım).
2. **`BOED` Uyarlamalı Ölçüm (`Exp132`, `6/6 PASS`, `$0` ek donanım, `src/machine_control/adaptive_spectroscopy.py` + `--preset v400`):** Klasik `1.000 ms` kör tarama kaldırıldı. `3`-aşamalı Bayesci uyarlamalı tasarım (`N = 2.000` Mod B MC) yuva başına ortalama süreyi **`41,03 ms`**'ye (medyan `23,04 ms`, **`24,37×` ham hızlanma**; boş yuva `0,73 ms`, sıkışık `14,58 ms`, çalışan `74,49 ms`), frekans hatasını **`RMS = 72,67 Hz`**'ye (`CRLB = 58,19 Hz`, `200 Hz`'den `2,75×` keskin), **`FNR = %0,20`** ve **`FPR = %0,00`**'a indirir. Darboğaz `v3.0`'daki okuma sınırından yazma tavanına taşınır: **`1,503×10⁹/gün` (`7,61×` @ `15 ms`) / `2,254×10⁹/gün` (`11,42×` @ `10 ms`)**; `VOKL-6 HM5962 (%33,25)` altında dahi **`9,794×10⁸ – 1,469×10⁹/gün`** (`4,96× – 7,44×` `v3-KL`, hâlâ yazma-sınırlı, `Exp135 L4`).
3. **Seç:** Taşınabilir Linux `AtlasSelector` + `Factory` (`MachineConfig.v400_bayesian()`, `v224_baseline()`, `v224_1k_upgrade()`, `legacy_exp65()`, zorunlu `α=1 ∧ α=2` DD kapısı).
4. **Kalibre Et & `CellISA v3.0` Programla (`Exp126` + `Exp132` + `Exp135`):**
   - **`CellISA v3.0` (`14` komut, `47/47` yazılım/ön-uç/RTL `pytest` [`src/machine_control/ + Exp132 + Exp135 + board + RTL`] / `142/142` toplam Atom Litografi `pytest` PASS):** `v2.0`'daki 10 temel komuta (`INIT`, `RX`, `RY`, `RZ`, `CZ`, `CNOT`, `GHZ`, `DD_HOLD`, `MEASURE`, `ARRAY_EXEC`) ek olarak **`WAFER_MAP_ROUTE`**, **`BUS_TUNE`**, **`BUS_CZ`** ve **`LOGICAL_ENCODE`** eklenmiştir. `4×4` yonga yönlendirmesi `%97,0` (`4`-hücre); canlı `4×4` Kraus dijital ikizinde (`Exp132/135 L8`) `40,82 ms/yuva`, **`min_bus_cz = 0,988923`**, **`F_joint = 0,983448`**, `bitflip3_plus_ancilla` **`p_L = 3,65×10⁻⁴` (`30,3×` hata bastırma)**, tümü SHA-256 `ProgramCertificate` imzalıdır.
   - **Tam 32B Hamiltonyen (`Exp126`):** `10–15 kHz` RF payı + 32B `XY8`-GRAPE ile `16` heterojen hücrede `Bell = 0,9501`, `GHZ-4 = 0,9401`, `Grover-2 = 0,8896` (`P(|11⟩) = 0,9237`), `BitFlip-3 = 0,8878`, `QFT-3 = 0,8377`, doğal `CCZ = 0,9338`, `D0(17,5 s) ≤ 7,76×10⁻⁹`.
5. **Yeniden yaz (onarım hakkı):** Boş kalan yuvalar alan izin verdikçe yeniden doldurulur (`Exp67`: `G = 4,7–7,9`).

## 8. Uçtan Uca Verim, Mühendislik BOM v4.0, `Exp128 v4.0` MC & `Exp134` 5 Yıllık TCO

**Bütçe tavanı (kullanıcı kararı, `Exp122` + `2026-10-26` onayı):** `50M USD` çizgisinin üstüne gerekmedikçe çıkılmaz; `50M–100M USD` aralığı gerekçe şartına bağlıdır (`BUTCE_DURUMU.md`); **`100M USD` sert sınırdır, aşılamaz.**
**Mühendislik BOM v4.0 + `7-RFQ` + `Exp128 v4.0` (`100k` MC) + `Exp134` (5y TCO, `7/7` + `7/7 pytest`, QA `#115/#137` KABUL, `no_supplier_quotes=true`):**
- Kanonik `BOM.csv` (`40` satır, `$2.531.244,37`, SHA-256 değişmez) ile `$0,00` aritmetik köprü hatasıyla bağlanan **`159` parçalı (`150` fiyatlı + `9` yazılım `$0`) `BOM_DETAILED.csv v4.0`**: **`M3 v4.0` = `$4.609.600`** (`$2.564.000 – $8.616.700`; `v3.0`'dan `+$420.000` artış: `S5.5` flaş tavlama `+$95k`, `S6.9` `PT420` ayrıştırma `+$68k`, `S6.10` `M4` cQED `+$245k`, `S7.1-04` `BOED` GPU `+$12k`). **`M1 v4.0` = `$2.336.270`** (`$1.360.570 – $4.210.190`, `M3`'ün `%50,7`'si, **`%83`'ü `M3`'e doğrudan taşınabilir**).
- **`Exp128 v4.0` (`100k` MC, `5/6 PASS`, dürüst `CU4 FAIL` [`%72,9 < %75`]):** `M3` BOM **`P50 = $5,50M`**, `P95 = $11,83M`, `P(>$50M) = %0,001`. Program (`×3–×10`): **`P50 = $30,87M ≤ $50M`**, `P(>$50M) = %21,62`, **`P(>$100M) = %3,38 ± %0,06 < %5`**. Tornado: `#1 S6.6 %73,4`, `#2 S2 %6,0`, `#3 S6.8 %5,3`, `#4 v4.0 %3,4`. **`7-RFQ` paketi** (`RFQ-01..07`, `70` parça, `$3.358.900 = %72,9` nominal; yeni `RFQ-07 = $408k` [`7A S5.5 / 7B S6.9 / 7C S6.10`]) BOM MC varyansının **`%92,6`'sını** yakalar. `1 K` EVPI: `N = 1`'de `$0`, başa-başı **`N_be = 6,01` makine**.
- **`Exp134` 5 Yıllık TCO & Birim Ekonomi (`5/6 PASS`, dürüst `CX4 FAIL`):**
  - Yıllık OPEX `$1,124M → $1,162M/yıl`; **5y Fab TCO (`N=1`) = `$16,07M`** (`v3.0 $15,23M`; `M1` Lab 5y TCO = **`$8,62M`**; FOAK `$39,66M`, `P95 = $97,19M < $100M`; Program `P50 = $30,96M`, `P(>$100M) = %3,19 < %5`).
  - **Rejim I (Kapasite / Birim Yazmaç, `Exp134/135 L7`):** `v3.0-KL` **`$52,88 µUSD/yazmaç`** → **`v4.0-KL` `$7,33 (−%86,15 @ 15 ms)` / `$4,88 (−%90,77 @ 10 ms)`** (`d=17` yüzey kodu mantıksal kübit `$0,0083 / $0,0055`); **`VOKL-6 HM5962`** altında bile **`$11,24 µUSD/yazmaç (−%78,75)`** (`d=17 = $0,0195` / `$0,0713 @ N_cand*=11`). Wright öğrenme (`b = %85`, `N = 1 → 100`): HW `$4,61M → $1,57M` (`−%66,0`), 5y TCO `$16,07M → $7,24M`.
  - **Rejim II (Yoğun `M4` Silikon Tabanı — dürüst `CX4 FAIL`):** `5×10⁷ reg/w, 1 s` yoğun `M4` akışında makine payı **`−%67,0`** (`$0,616 → $0,203/çip`) düşer ve fab çıktısı `3,20×` artar, ancak ham `²⁸Si` epi yonga (`$2,40/çip`) toplam `$2,603/çip` maliyetinin **`%92,2`'sini** oluşturduğu için toplam çip indirimi `−%13,7 < %50` kalır (silikon tabanı limiti).

`Exp135` birleşik `v3.0 → v4.0` dijital ikiz tablosu (`7/7 DT PASS`, `11/11` JSON SHA-256 bağlı, ana sertifika `feffc1d4ba2b0698c3f61015c6684da47f57ea863a8b3e0da845cc9c71914b57`):

| Mod / Senaryo (`v3.0` vs `v4.0`) | Tek-Atış Verim | Spektroskopi Süresi | Sertifikalı Yazmaç/Gün | 5y TCO Birim Maliyet (`µUSD/reg`) | `M4` `L=11` FT `N_cand*` (`≥%99`) |
|---|---:|---:|---:|---:|---:|
| **`v3.0` Baz (`KL f=%1`, klasik `1 s`)** | `%50,50` | `1.000 ms` | `1,973×10⁸` (okuma-sınırlı) | `$52,88` | `6` (`%99,24`) |
| **`v4.0` Baz (`KL f=%1`, `BOED 15 ms`)** | `%50,50` | **`41,72 ms`** | **`1,502×10⁹`** (`7,61×`, yazma-tavanlı) | **`$7,33`** (`−%86,15`) | `6` (`%99,24`) |
| **`v4.0` Baz (`KL f=%1`, `BOED 10 ms`)** | `%50,50` | **`41,72 ms`** | **`2,253×10⁹`** (`11,42×`, yazma-tavanlı) | **`$4,88`** (`−%90,77`) | `6` (`%99,24`) |
| **`v4.0` `R1` Dürüst (`VOKL-6 HM5962 f=%1`)** | **`%33,25`** | **`29,87 ms`** | **`9,794×10⁸` (`15 ms`) / `1,469×10⁹` (`10 ms`)** | **`$11,24`** (`−%78,75`) | **`11`** (`%99,74`; `N=6`: `%3,12` FAIL) |
| **`v4.0` `R1` Kurtarma (`VOKL-6 HM5962 f=%2`)** | **`%54,50`** | `~44 ms` | yazma-tavanlı | `~$6,9` | **`6`** (`%99,92`) |
| **`v4.0` `R1` Kırmızı Çizgi (`VOKL-6 norm f=%1`)** | **`%4,75`** | `10,83 ms` | `1,399×10⁸` (`15 ms`) | `$78,6` | **`86`** (mimari kırmızı çizgi!) |
| `Mod A` (`σ=3,72 nm`, `Exp124 CD8` donörlü) | `%42,50` (`Holmes %28,0`) | klasik/BOED | AR-GE opsiyonu | — | — |

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

## 9. Risk Kapanış Matrisi (`v4.0` — `Exp124–135` Sonrası)

| Risk | Konu | `v4.0` Statü | Kapanış Kanıtı veya Kalan Açık İş |
|---|---|---|---|
| **5 keV Parlaklık & `C_c`** | Liouville açığı & statik mercek alt sınırı | **MODEL-İÇİ KAPANDI** (`Exp124`, `#59` KABUL) | `10→5 keV` yavaşlatma + `Arch-B` (`C_c=2,660 mm`, `WD=0,250 mm`) + `HDA-HiRes` (`ΔE=0,453 eV`) → `σ_spot=1,428–1,532 nm`, birleşik `σ_tot=3,578–3,620 nm` (`CD3`: `κ_c≥4,67` fiziksel sınır). Lab doğrulaması `M1 G2`'de açık. |
| **5 keV IBIC Algılama** | Lindhard düşük yükte RT çöküşü | **MODEL-İÇİ KAPANDI** (`Exp127`, `#52` KABUL) | **`100 K / 1,2 µs / 1 GΩ` soğuk-ada `LTC6268`** (`204` bileşen, `0` ERC): `ENC=24,07 e⁻`, `η(5 keV, 0,5 pF)=0,99936`, `C_det≤1,5 pF`, `P_false=2,59×10⁻⁴`. 4-katmanlı PCB & lab `M1 G3`'te açık. |
| **`PT420` Titreşim & Termal Kayma** | Rijit `PT420` `2.052 nm` çöküşü & `316LN` sürüklenmesi | **MODEL-İÇİ KAPANDI** (`Exp133`, `#118` KABUL) | `S6.9` `CFG4`: `500 mm` uzak döner valf + `600 mm` He hattı + `k_bellows=2.000 N/m` körük + `4×` S-halka OFHC Cu örgü (`ΔT=3,7 mK`) + `43,57 Hz` PID + `25 dB` FF + `Zerodur/Invar-36` (`20 mK`) → `σ_stage=0,1024 nm`, `σ_pointing=0,1473 nm`, `σ_thermal=0,0283 nm`. Lab `M1 G1`'de açık. |
| **`R1`** | Bağ modeli belirsizliği (`VOKL-6` 6-vadi merkez-hücre) | **AÇIK — GERÇEK AŞAĞI YÖNLÜ VERİM RİSKİ (`Exp129`, `3/7 PASS, 4/7 FAIL`, `#130`)** | `VOKL-6` tüm 4 `³¹P` değişmezini `< 10⁻¹⁰` (`~10⁻¹¹` mertebesi, maks `7,36×10⁻¹¹`) ile tutar ama `R331=0,1034` (`%64,73` hata, `CE3/4 FAIL` → Si `3d`/DFT ister). **KRİTİK BULGU:** `f=%1` Mod B verimi `KL %50,50 →` **`HM5962 %33,25`** (`norm %4,75` kırmızı çizgi), `min_gap < 6,893 kHz` `%57,9–%73,7`; `M4` `N_cand*` `6 → 11` (veya `f=%2 → 6`, `norm → 86`) çıkar. **`M1 G6b` ilk `ENDOR` kapısı zorunludur!** |
| **`R2`** | Saçılma zemini & kanalizasyon + donör saçılması | **KISMEN KAPALI / AÇIK** (`Exp124`) | `Exp124 CD8` stokastik `³¹P` donör saçılmasında Mod A'nın `%42,5` (`BCA`) / `%28,0` (`Holmes`) düştüğünü kanıtladı → **Mod B baz** bağışık. Kanalizasyon için `Crystal-TRIM` + lab açık. |
| **`R3`** | İç-içe DD & 32B Hamiltonyen | **MODEL-İÇİ KAPANDI** (`Exp126`, `#69` KABUL) | Tam 32B CUDA (`448` seyirci + `J_ij`): **`N=32` optimum `α=1: 0,9260 / α=2: 0,9648`**; `N=64`: `0,9209 / 0,9433`; zorunlu `XY8` (`+0,3245/+0,6189` vs `CPMG`) + `10–15 kHz` RF; `N=128` DDRF duvarı yasak. Açık: `K=8` ölçekleme & `M1 G7` lab. |
| **`R4`** | Paralel okuma donanımı & `S6.6` `B/C` duvarı | **AÇIK (Tedarikçi/Lab)** | `Exp128 v4.0` 100k MC: `S6.6` `B/C` duvarı BOM varyansının **`%73,4`'ü**; **`7-RFQ`** (`%92,6` varyans, `$3,359M`) gönderimi ve gerçek teklif şart (`no_supplier_quotes=true`). |
| **`R5`** | SKY130 blanker çip anten/reroute borcu | **AÇIK EDA BORCU (ERTELİ)** | `Exp123` (`CU1/2 FAIL`, Attempt 2 `101` telsiz ağ sahte kapanış, Attempt 3b `2026-11-02 06:07` yarım; `tapeout_done=false`). **2026-11-22 kullanıcı kararı:** aktif odak makinede; `M1` FPGA ile yürür, `R5` `M2/M3`'te kapanır. |
| **`R6`** | Tavlama difüzyonu (`600 °C/10 dk` göç) | **MODEL-İÇİ KAPANDI (`Exp130`, `#115` KABUL) / LAB AÇIK (`M1 G4`)** | `S5.5` in-line RT load-lock **`808 nm / 1,0 ms / 1440,3 K` (`41,15 J/cm² ± %5`)** ms-flaş tavlama (`+Y` CF63 safir): **`f_act=%99,98`**, **`σ_anneal=0,328 nm ≤ 0,50 nm`**, kayıp `%0,022`, `σ_iso=0,0314 nm`. Fırın/RTA yasak. Fiziksel SIMS doğrulaması `M1 G4`'te açık. |
| **`R7`** | Manyetik ayrıştırma (`1,5 T` vs `≤0,4 T`) & alt-GHz LNA | **MANYETİK KAPANDI / LNA AÇIK** (`Exp125`, `#52` KABUL) | `8`-bobin `NbTi` (`1,500000 T ± 17,81 ppm`, `64,6 K` quench) + `Nb (RRR>300)` (`117,1 < 135 mT`) + `Cryoperm-10` → **`22,3 µT`** (`450×` pay). `100–900 MHz` kriyo-LNA tedarikçi/lab (`RFQ-05`) açık. |
| **`R8`** | `1 K` sıcak-okuma alternatifi & Koiller vadi sıfırları | **NİCELENDİRİLDİ / DÜŞÜK ÖNCELİK** (`Exp125/128 v4.0`) | Koiller 6-vadi `W2 V2 p = 0,9322` (`N_99=2`), fakat `1 K` Mod B `3,40×` yavaş ve `N=1` **`EVPI = $0`** (`N_be = 6,01` makine). `20 mK` DR baz optimal; `1 K` lab transferi yalnızca filo (`N ≥ 6`) kararıyla açılır. |
| **`M4` Şarj Gürültüsü & Silikon Tabanı** | `3 kΩ NbTiN` `1/f` gürültüsü & dense `²⁸Si` yonga maliyeti | **AÇIK — DÜRÜST SINIRLAR (`Exp131`, `Exp134`)** | `Exp131 CM3/4 FAIL`: `3 kΩ NbTiN` `F_Bell=0,9655` (`0,359 µs`, `Δz_cap*=8±1 nm`), ancak `≥0,99` için **`S_ε ≤ 0,25–0,35 µeV/√Hz` veya `1/f` yankısı** şart. `Exp134 CX4 FAIL`: yoğun `M4` çipte `$2,40/çip` `²⁸Si` yonga `%92,2` taban koyar. |

*(Tarihsel ayrıntı: `R1–R8` tam kronolojisi ve `Exp119/120/123` adli kayıtları `PROJECT_DOSSIER.md` ve `NOTES_RECOVERY.md` içindedir.)*

## 10. Aşamalı yol haritası

- **M0 (bu proje, `v4.0` tamamlandı):** Kuram, birinci-ilkeler fizik (`Exp124–135`), `CAD v4.0` (`170` parça, `993,27 kg`, `0/14.365` çakışma, `25/25` boşluk), `159`-parça `BOM_DETAILED v4.0` + `7-RFQ`, `src/board/` (`204` bileşen, `0` ERC), `src/machine_control/` v3.0 (`BOED` + `CellISA v3.0`, `142/142` Atom Litografi `pytest`), `Exp135` Birleşik Dijital İkiz ve `TECHNICAL_MANUAL.md v4.0` mühürlendi; açık EDA borcu (`R5/Exp123`) erteli.
- **M1 (`M1_PROTOTYPE_BLUEPRINT.md v3.0`, `$2.336.270` nom., 5y Lab TCO `$8,62M`, `%83` `M3`'e taşınabilir):** Tek-demet `10→5 keV` sayılmış implantasyon (`100 K` IBIC) + `S5.5` `808 nm / 1,0 ms` flaş tavlama + `S6.9` ayrıştırılmış `PT420` + `20 mK / 1,50 T / 22,3 µT` + `BOED` + **`G6b` `ENDOR` Risk `R1` verim ölçümü** + `CellISA v3.0` (`G1–G8` kapıları; dış altyapı & `7-RFQ` teklifleri gerekir).
- **M2:** `10²–10³` demetcikli MEMS kafa prototipi + paralel soğuk-ada algılama + `Exp123` SKY130 ASIC anten kapanışı; hata bütçesinin ölçülmesi.
- **M3 (`$4.609.600` nom., `P50=$5,50M` BOM / `$30,87M` Program, 5y Fab TCO `$16,07M`):** Altın ölçek (**`32×32 = 1.024` eş-adımlı `0,50 mm` demetcik**, `~8.960` spektroskopi kanalı, `S6.8=D` `20 mK` DR + `S6.9` `PT420` ayrıştırma, `S5.5` flaş tavlama, `1,50 T / 22,3 µT`, `100 K` IBIC, `BOED` `1,50–2,25×10⁹/gün` [`HM5962`: `0,98–1,47×10⁹/gün`], `XY8 N=32–64`).
- **M4 (`S6.10` `$245k` `RFQ-07C`, `Exp131/135`):** `Δz_cap* = 8,0 ± 1,0 nm` `²⁸Si` kapaklı flip-flop düğümler + `3 kΩ NbTiN` (`L_res = 300 µm`, `B_M4 = 0,1785 T`, `P_node = 10 µm`, `968` kapı `4 K SKY130` çapraz-çubuk) 2B yüzey-kodu (`L=11` FT `N_cand* = 6` [`KL`/`f=%2`] veya `11` [`HM5962 f=%1`]; `S_ε ≤ 0,25–0,35 µeV/√Hz` veya `1/f` yankı şartıyla).

## Ek — fizibilite deney programı (durum)

- Exp65–68 (tamam): Verim/hız (`H81`), konum hata bütçesi (`H82`), kapalı çevrim kazancı (`H83`), ilk DD şartnamesi (`H84`).
- Exp124–128 (tamam, `v3.0` kilidi): `Exp124` (`H142`), `Exp125` (`H143`), `Exp126` (`H144`), `Exp127` (`H145`), `Exp128` (`H146`, `v4.0` yenilendi).
- **Exp129–135 (tamam, `v4.0` gece dalgası kilidi):** `Exp129` (`H147`, `VOKL-6` Risk `R1`, `3/7 PASS / 4/7 FAIL`, QA `#130`), `Exp130` (`H148`, `S5.5` flaş tavlama Risk `R6`, `6/6 PASS`, QA `#115`), `Exp131` (`H149`, `M4` `3 kΩ NbTiN` cQED & 2B perkolasyon, `4/7 PASS / 3/7 FAIL`, QA `#124`), `Exp132` (`H150`, `BOED` & `CellISA v3.0`, `6/6 PASS`, QA `#121`), `Exp133` (`H151`, `PT420` titreşim/FEM/termal ayrıştırma, `8/8 PASS`, QA `#118`), `Exp134` (`H152`, 5y TCO & Wright öğrenme, `5/6 PASS / 1/6 FAIL`, QA `#115`), `Exp135` (`H153`, 8-katmanlı birleşik `v4.0` dijital ikiz & SHA-256 sertifika, `7/7 PASS`, QA `#137`).

Belge sürümü **`v4.0`**'dır (`2026-11-23`; `Exp0–Exp135`, `CAD v4.0`, `BOM_DETAILED v4.0` + `7-RFQ`, `BOED` & `CellISA v3.0`, `Exp135` Dijital İkiz). Laboratuvar ölçümü, tedarikçi teklifi veya silikon tape-out iddiası hiçbir sürümde yoktur (`no_lab_measurement=true`, `no_supplier_quotes=true`, `tapeout_done=false`).

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
