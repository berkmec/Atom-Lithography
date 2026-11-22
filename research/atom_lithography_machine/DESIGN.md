# Yeni Nesil Atom Litografi Makinesi — Tasarım Belgesi v3.0

Tarih: 2026-10-19 (tam v3.0 mühürlemesi: Exp0–Exp128, CAD v3.0, BOM_DETAILED, CellISA v2.0 — 2026-11-23). Durum: **kâğıt üzerinde tam mühendislik tasarımı + birinci-ilkeler sayısal simülasyon & EDA doğrulaması (`no_lab_measurement=true`, `no_supplier_quotes=true`, `tapeout_done=false`).** Bu belgede laboratuvar ölçümü, üretilmiş donanım, silikon tape-out veya fiziksel atom yoktur. Bütün sayılar bu deponun (`Atom-Lithography`) Exp0–Exp128 model/sayısal-simülasyon/EDA kanıtlarına, üçüncü taraf ölçüm çapalarına (NIST 4 K SKY130) veya açıkça etiketlenmiş literatür ölçeklerine dayanır; varsayım olan her sayı "varsayım" diye işaretlenir. (Aktif geliştirme odağı 2026-11-22 kullanıcı kararıyla çip hattından değil **makineden** devam etmektedir; eşlik eden ana belgeler: `TECHNICAL_MANUAL.md`, `MODULAR.md`, `M1_PROTOTYPE_BLUEPRINT.md`, `BOM_ENGINEERING.md`, `RFQ_SPECIFICATIONS.md`, `PROJECT_DOSSIER.md`.)

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
5. Kontrol & programlama paketi: o yazmaca özgü, `10–15 kHz` (`B₁ ≈ 1,2–1,8 mT`) RF paylı, `±400 Hz × ±%2` köşe-doğrulanmış `XY8`-GRAPE darbe seti (`Exp61`, `Exp126`) + 10-komut `CellISA` derleyicisi ve SHA-256 imzalı `ProgramCertificate` (`src/machine_control/programmer.py`, `Exp126–127`).

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
  **Şartname (`Exp68` + `Exp126` 32B kilitli):** ürün bolluğu **`f = %1`** (tek-atış seçim verimi `%51`, 3-atış `%87,92`;
  her iki `α=1/2` gürültü üssünde `Q_32D > 0,92`), **zorunlu DD sekansı `XY8` (`CPMG` yasak — `+0,3245/+0,6189` üstünlük)**,
  **darbe sayısı `N_total = 32–64`** (**`N = 32` global optimum: `α=1: 0,9260 / α=2: 0,9648`**; `N = 64`: `0,9209 / 0,9433`;
  **`N = 128` DDRF seyirci duvarı yasak: `sp_ovl = 0,0972`**), **RF NMR bobini genlik payı `10–15 kHz` (`B₁ ≈ 1,2–1,8 mT`)**
  ve darbe-başına hata **`ε ≤ 10⁻³`** (`ε = 10⁻² → 0,6382` FAIL). `α=2` doğrulanırsa `f=%2` (`%69`, `Q_32D=0,9195`) yükseltme yoludur.

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

## 5. Konumlandırma & Parametrik CAD v3.0 — sıfır titreşim ve mekanik kilit

"Sıfır titreşim" fiziksel bir mutlak değildir; şartname, **toplam yerleştirme hatası
bütçesinin** implant saçılmasını büyütmeyecek düzeyde tutulmasıdır. Katmanlar:

1. **Pasif kütle:** granit/beton blok + hava yaylı izolatörler (1–2 Hz köşe).
2. **Aktif sönümleme:** jeofon/ivme geri beslemeli piezo aktüatörler (0,5–100 Hz bandı).
3. **Piezo kademe (`Exp79`, `CAD v3.0`):** maglev kaldırıldı (`maglev_stage = 0`); COTS kaba+ince piezo yığını (`PI PIMars` sınıfı, `S4.3=C`, sub-nm çözünürlük, UHV sürümü) + 3-eksen `pm` lazer interferometre + `Invar` kaide (`R=45..52 mm`, `Cryoperm` ve `B`-bobine `4,0 mm` radyal boşluk).
4. **Kafa-kademe göreli metrolojisi:** fiducial referans işaretleriyle sürekli sapma ölçümü ve atış anı düzeltmesi.

Hata bütçesi (`Exp66` + `Exp124`): `Arch-B` (`C_c = 2,660 mm`, `WD = 0,250 mm`) + `HDA-HiRes` (`ΔE = 0,453 eV`) kombinasyonu `σ_spot = 1,428–1,532 nm` ve **`σ_tot = 3,674–3,715 nm ≤ 3,80 nm`** sağlayarak ekipman hatasını implant saçılması (`3,25 nm`) zemininin altında tutar.

**Parametrik CAD v3.0 Doğrulaması (`research/atom_lithography_machine/cad/cad_verification.json`, `3.0-exp124-exp125-locked`, `tests/test_cad.py` `23/23 PASS`, QA `#63` / `#84` KABUL):** **`143` katı parça**, toplam kütle **`956,903 kg`** (`S1 25,98`, `S2 1,83`, `S3 0,15`, `S4 302,37`, `S5 169,99`, `S6 238,34`, `S7 218,25 kg`), `CoM = (141,32; −10,88; 443,33) mm`, dış zarf `2125 × 881 × 1400 mm`, `8/8` su-geçirmez `.stl` (`30.048` üçgen, `468,627 L`, `0` açık/non-manifold kenar), `10` teknik çizim (`2400×1600` `.png`/`.svg`), **`0 / 10.153` katı çakışma** ve **`19 / 19` kritik boşluk PASS** (`WD=0,25 mm`, `32×32` dizi köşegeni ↔ `Ø28 mm` delik **`2,686 mm`**, `UHV R_iç=182,0 mm / V_iç = 34,861 L = 0,1294×`, `Exp84` blanker `f₁ = 2,591 MHz`).

## 6. Termal & Manyetik Mimari — oda sıcaklığında gövde, `20 mK` DR, `1,50 T / 22,3 µT` mıknatıs (`Exp125`)

- Gövde, vakum odası ve kafa oda sıcaklığında çalışır (implant sonrası `³¹P` difüzyonu RT'de donmuştur; MEMS blanker ve kaynak RT'de olgun teknolojidir). Yalnız **IBIC sayım ön-ucu (`S3`, §4)** gerçek Lindhard `5 keV` yükü nedeniyle **`100 K` soğuk adada** çalışır (`Exp127`).
- **Lokal soğutulmuş ölçüm adası (`S6.8` & `S6.1`, `Exp116–121`, `Exp125`, `Exp128`):**
  - `4 K` tek-donor spin spektroskopisi `Exp116`'da fiziksel olarak dışlanmıştır (`B=0,4 T`'de polarizasyon `%6,71`).
  - **BAZ kademe** `S6.8 = D` **seyreltme ünitesidir (`MXC ~20 mK`, `S6.1` `PT415/PT420` `4 K` ön-soğutucu)**. `Exp128` EVPI karar analizi bu seçimi kesinleştirmiştir: `1 K` alternatifinin donanım tasarrufu `$662,9k/makine` olsa da `C_RD = $2,0M, p = %50` altında ilk makinede **`ENV = −$1,67M`, `EVPI = $0`** (filo başa-başı **`N_be = 6,03` makine** / `2×` entegrasyonla `3,02`) ve `1 K` Mod B hızı **`3,40×`** yavaştır (`1,372×10⁸ → 4,042×10⁷`/gün, `Exp125`).
  - **5-kademe termal bütçe (`Exp125 CV4 PASS`, sistem yükleri dahil `9.000` kanal):** `NL=163` (`56` hat, `2,1 mW` HEMT): `50K = 7,54 W`, **`4K = 0,325 W`**, `Still = 1,14 mW`, `CP = 54,5 µW`, **`MXC = 3,94 µW < 19 µW`**. Kanonik `NL=160` (`57` hat, `7,8 mW` HEMT): **`4K = 0,654 W`**, `MXC = 3,97 µW` (`10,5 mW`: `0,808 W`). Geniş `NL=110` (`82` hat): `7,8 mW` **`4K = 0,899 W < 1,0 W`**, `MXC = 4,80 µW` (`10,5 mW`: `1,121 W → PT415/420`). `1 K` opsiyonu (`S6.8=C`, `57` hat): `1K = 11,84 mW < 100 mW`.
- **8-bobinli `NbTi` Mıknatıs & Çift-Katmanlı Meissner Kalkanı (`S6.3`, `Exp125 CV1–CV3 PASS` — Risk `R7` Manyetik Ayrıştırma KAPANDI):**
  - `M/S/A/B` (üst+alt) 8 `NbTi` bobini (`Ø150,0 mm` açık boşluk, `36,0 mm` orta düzlem yarığı, `Ø352,0 mm` OD, `5,48 km` tel, `18,941 kJ` depolanan enerji): örnekte (`r ≤ 2,3 mm, |z| ≤ 0,5 mm`) **`B_z(0,0) = 1,500000 T ± 17,81 ppm`**, `max |B_r| = 0,011 mT`.
  - Süperiletken & Quench güvenliği: `max(I/I_c) = 0,212 ≤ 0,55`, `ΔT_min = 2,55 K`, `max |σ_hoop| = 52,7 MPa ≤ 80 MPa`, pasif boşaltma (`R_dump = 1,563 Ω, V_max = 400 V, τ = 0,370 s`) **`T_hotspot = 64,6 K ≤ 150 K`**.
  - `z_loc = −155 mm` (`r ≤ 25 mm`, `1.963,5 mm² ≫ 8,43 mm²`) `NbTiN` rezonatör diskinde: kalkansız `3,08 mT` → **`Nb (RRR > 300)` Meissner kabı** (`R = 32..34,5 mm`, yüzey `117,12 mT < B_c1(4,2 K) = 134,95 mT` vortekssiz) + **`Cryoperm-10`** (`R = 39..41 mm`, `SF = 488,8×`) ile **`max |B_res| = 22,3 µT`** (`|B_z| ≤ 21,6 µT`, `|B_r| ≤ 7,8 µT` — `≤ 0,4 T` hedefinin `> 17.900×`, `10 mT` sınırının `> 450×` altında). MEMS kaçak alanı (`z_loc = +268 mm`): `108,1 mT`.

## 7. Kapalı çevrim II — ölç, seç, kalibre et & `CellISA` programla (`src/machine_control/` v2.0 + `Exp126`)

Bu katman, projenin `Exp44–61` + `Exp125–127` hattının eksiksiz donanım ve yazılım iş akışıdır:

1. **Yaz:** Mod B'de her yazmaç yuvasına sayılmış `³¹P⁺` donörü implant edilir (`100 K` soğuk-ada IBIC).
2. **Ölç (`Exp125 CV5 PASS`):** `20 mK` DR ve `1,500000 T` altında `56` hatlı (`NL=160`, `8.960` kanal, `Ql=800–1200`, `≤ −100 dBm/ton`, `NbTiN` diskte `22,3 µT`) RF yansıma spektroskopisiyle `{A_k}` çıkarılır (`±200 Hz`). `SNR = 10` entegrasyon süresi **`0,0627 ms`** (`20 mK / 1,4 K` LNA; 200-nokta `12,5 ms`) ve `0,179 ms` (`1,5 K / 3,0 K` LNA; `35,9 ms`) `≪ t_eff = 1.445 ms`.
3. **Seç:** Taşınabilir Linux `AtlasSelector` (`src/machine_control/selector.py`) ve `Factory` (`config.py`: `v224_baseline()`, `v224_1k_upgrade()`, `legacy_exp65()`, zorunlu çift-`α` `α=1 ∧ α=2` DD kapısı) çalışan yazmaçları ayırır. Canlı demo (`results/exp127_detector_frontend_sim/certs_v224_demo.jsonl`): `4.000` yuvada **`3.517` sertifikalı yazmaç (`%87,92`)**, `1,98` atış/spektroskopi, **`1,973×10⁸` yazmaç/gün**, `3.517/3.517` eksiksiz 8-çizgili `lines_Hz`.
4. **Kalibre Et & `CellISA` Programla (`Exp126` & `Exp127`):**
   - **`CellISA` v2.0 (`src/machine_control/programmer.py`, `35/35 pytest PASS`):** 10-komut formal ISA (`INIT`, `RX`, `RY`, `RZ`, `CZ`, `CNOT`, `GHZ`, `DD_HOLD`, `MEASURE`, `ARRAY_EXEC`), `SU(2)` Rodrigues + 9-köşeli L-BFGS-B GRAPE + `XY8` (`14,37×`) ve SHA-256 imzalı `ProgramCertificate` (`prog_certs_v224_demo.jsonl`: `bell`, `ghz4`, `repcode3`, `qft3` `4/4` `certified=True`).
   - **Tam 32B Hamiltonyen Doğrulaması (`Exp126`, `8/8 pytest`, QA `#69` KABUL):** `10–15 kHz` (`B₁ ≈ 1,2–1,8 mT`) RF payı ve 2-aşamalı 32B `XY8`-GRAPE ile `16` heterojen `f = %1` hücrede (`16/16` benzersiz `{A_k}`, `Lie = 1023`, `D0(17,5 s) ≤ 7,76×10⁻⁹`, `1 µm` hücreler arası dipol `9,50×10⁻⁹ Hz` → `16×` paralel FDMA) 5 mantıksal programın gürültülü (`α=2, ε=10⁻³`) ortalamaları: **`Bell = 0,9501`**, **`GHZ-4 = 0,9401`**, **`Grover-2 = 0,8896`** (`P(|11⟩) = 0,9237`), **`BitFlip-3 QEC = 0,8878`**, **`QFT-3 = 0,8377`**; doğal 3-cisim **`CCZ(0,1,2) = 0,9338`**.
5. **Yeniden yaz (onarım hakkı):** Boş kalan yuvalar alan izin verdikçe yeniden doldurulur (`Exp67`: `G = 4,7–7,9`).

## 8. Uçtan uca verim, mühendislik BOM ve `Exp128` 100k MC bütçe yönetimi

**Bütçe tavanı (kullanıcı kararı, `Exp122` + `2026-10-26` onayı):** `50M USD` çizgisinin üstüne gerekmedikçe çıkılmaz; `50M–100M USD` aralığı gerekçe şartına bağlıdır (`BUTCE_DURUMU.md`); **`100M USD` sert sınırdır, aşılamaz.**
**Mühendislik BOM & `Exp128` `100.000` Korelasyonlu Monte Carlo (`BOM_DETAILED.csv`, `BOM_ENGINEERING.md`, `RFQ_SPECIFICATIONS.md`, `tests/test_bom_detailed.py` `6/6`, QA `#63` KABUL, `no_supplier_quotes=true`):**
- Kanonik `BOM.csv` (`40` satır, `$2.531.244,37`, SHA-256 değişmez) ile `$0,00` aritmetik köprü hatasıyla bağlanan `145` parçalı **`BOM_DETAILED.csv`**: **`M3` Tam Makine = `$4.189.600`** (`$2.329.000 – $7.834.700`; `Δ = +$1.658.355,63`: `S2` MEMS NRE `+$764,9k`, COTS/UHV/PT420 `+$285,8k`, `Exp125` mıknatıs+kalkan `+$261,0k`, `S9` yedek `+$148,0k`, `Exp124` kolon+`PH₃` `+$133,6k`, `Exp127` IBIC `+$65,1k`). **`M1` Tek-Demet Prototipi = `$2.189.770`** (`$1.277.070 – $3.940.690`, `M3`'ün `%52,3`'ü, **`%82`'si `M3`'e doğrudan taşınabilir**).
- **100k MC (Model A baz; Model B neredeyse özdeş `P50=$4,99M / $28,01M`):** `M3` Donanım BOM **`P50 = $5,01M`**, `P95 = $11,20M`, **`P(>$50M) = %0,00`**, **`P(>$100M) = %0,00`**. Program çarpanıyla (`×3–×10`, `P50 = 5,48×`): **`P50 = $28,24M ≤ $50M`**, `P95 = $82,11M`, **`P(>$50M) = %18,10`**, **`P(>$100M) = %2,69`**.
- **Tornado & 6-RFQ:** BOM varyansının **`%77,27`'si** (`ρ = 0,889`) tek başına `S6.6` `56×` okuma zinciri `B/C` duvarından gelir (`S2` MEMS `%5,85`, `S6.8` DR `%5,21`). **6-RFQ paketi** (`RFQ-01..06`, `58` parça, `$2.950.900 = %70,43` nominal) toplam BOM MC varyansının **`%92,8`'ini** yakalar.
- **`20 mK` vs `1 K` EVPI:** `E[ΔC_hw] = $662,9k/makine`; `N = 1` ilk makinede **`ENV = −$1,67M`**, **`EVPI = $0`** (`20 mK` kesin optimal); başa-baş **`N_be = 6,03` makine** (`2×` entegrasyonla `3,02`).

Kullanıcının "1 milyon iğne → günde milyar atom" hedefi atom sayısıyla değil, sertifikalı
yazmaç sayısıyla fiyatlanmalıdır. Exp65 referans senaryosu (10⁶ demetcik, 1 ms atış,
10⁴ okuma kanalı, 1 s spektroskopi, %50 görev çevrimi; ölçüm sınırlı olduğu için Exp78–79
altın bandı `10³–10⁴` demetcik aynı günlük üretimi verir):

| Mod/hücre | seçim verimi | sertifikalı yazmaç/gün | spektroskopi/yazmaç | atış/yazmaç |
|---|---:|---:|---:|---:|
| B f=%0,5 | %26 | 1,12×10⁸ | ~3,9 | ~3,9 |
| B f=%1 (BAZ) | %51 (3-atış %87,9) | 1,37×10⁸–2,20×10⁸ | ~2,0 | ~2,0 |
| B f=%2 | %69 | 2,98×10⁸ | ~1,5 | ~1,5 |
| A σ=3,72–3,80 nm (Exp124) | %76,3 sabit / **%42,5 donörlü** (`Holmes %28,0`) | ~1,2–2,1×10⁸ | ~2,0–2,4 | ~2.100 |
| A σ=10 nm | %3 | 1,26×10⁷ | ~34 | ~35.000 |
| A σ=20 nm | %0 | 0 | — | — |

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

## 9. Risk Kapanış Matrisi (`v3.0` — `Exp124–128` Sonrası)

| Risk | Konu | `v3.0` Statü | Kapanış Kanıtı veya Kalan Açık İş |
|---|---|---|---|
| **5 keV Parlaklık & `C_c`** | Liouville açığı & statik mercek alt sınırı | **MODEL-İÇİ KAPANDI** (`Exp124`, `#59` KABUL) | `10→5 keV` yavaşlatma + `Arch-B` (`C_c=2,660 mm`, `WD=0,250 mm`) + `HDA-HiRes` (`ΔE=0,453 eV`) → `σ_spot=1,428–1,532 nm`, `σ_tot=3,674–3,715 nm` (`CD3`: `κ_c≥4,67` fiziksel sınır). Lab doğrulaması `M1 G2`'de açık. |
| **5 keV IBIC Algılama** | Lindhard düşük yükte RT çöküşü | **MODEL-İÇİ KAPANDI** (`Exp127`, `#52` KABUL) | **`100 K / 1,2 µs / 1 GΩ` soğuk-ada `LTC6268`** (`204` bileşen, `0` ERC): `ENC=24,07 e⁻`, `η(5 keV, 0,5 pF)=0,99936`, `C_det≤1,5 pF`, `P_false=2,59×10⁻⁴`. 4-katmanlı PCB & lab `M1 G3`'te açık. |
| **`R1`** | Bağ modeli belirsizliği (`%49` kabuk hatası) | **AÇIK (Atomistik/Lab)** | Vadiler-arası merkez-hücre karışımı (`Exp69/75`) TB/DFT + lab ister; ölçüm-sonrası seçim mimarisi dayanıklıdır. |
| **`R2`** | Saçılma zemini & kanalizasyon + donör saçılması | **KISMEN KAPALI / AÇIK** (`Exp124`) | `Exp124 CD8` stokastik `³¹P` donör saçılmasında Mod A'nın `%42,5` (`BCA`) / `%28,0` (`Holmes`) düştüğünü kanıtladı → **Mod B baz** bağışık. Kanalizasyon için `Crystal-TRIM` + lab açık. |
| **`R3`** | İç-içe DD & 32B Hamiltonyen | **MODEL-İÇİ KAPANDI** (`Exp126`, `#69` KABUL) | Tam 32B CUDA (`448` seyirci + `J_ij`): **`N=32` optimum `α=1: 0,9260 / α=2: 0,9648`**; `N=64`: `0,9209 / 0,9433`; zorunlu `XY8` (`+0,3245/+0,6189` vs `CPMG`) + `10–15 kHz` RF (`1846×` seyirci kurtarma); `N=128` DDRF duvarı yasak. Açık: `K=8` ölçekleme & `M1 G7` lab. |
| **`R4`** | Paralel okuma donanımı & `S6.6` `B/C` duvarı | **AÇIK (Tedarikçi/Lab)** | `Exp128` 100k MC: `S6.6` `B/C` duvarı BOM varyansının **`%77,27`'si**; **6-RFQ** (`%92,8` varyans) gönderimi ve gerçek teklif şart (`no_supplier_quotes=true`). |
| **`R5`** | SKY130 blanker çip anten/reroute borcu | **AÇIK EDA BORCU (ERTELİ)** | `Exp123` (`CU1/2 FAIL`, Attempt 2 `101` telsiz ağ sahte kapanış, Attempt 3b `2026-11-02 06:07` yarım; `tapeout_done=false`). **2026-11-22 kullanıcı kararı:** aktif odak makinede; `M1` FPGA ile yürür, `R5` `M2/M3`'te kapanır. |
| **`R6`** | Tavlama difüzyonu (`600 °C/10 dk` göç) | **AÇIK (Lab — `M1 G4`)** | ms flaş tavlama deneysel doğrulama ister (`σ_tavlama ≤ 0,5 nm`). |
| **`R7`** | Manyetik ayrıştırma (`1,5 T` vs `≤0,4 T`) & alt-GHz LNA | **MANYETİK KAPANDI / LNA AÇIK** (`Exp125`, `#52` KABUL) | `8`-bobin `NbTi` (`1,500000 T ± 17,81 ppm`, `64,6 K` quench) + `Nb (RRR>300)` (`117,1 < 135 mT`) + `Cryoperm-10` → **`22,3 µT`** (`450×` pay). `100–900 MHz` kriyo-LNA tedarikçi/lab (`RFQ-05`) açık. |
| **`R8`** | `1 K` sıcak-okuma alternatifi & Koiller vadi sıfırları | **NİCELENDİRİLDİ / DÜŞÜK ÖNCELİK** (`Exp125/128`) | Koiller 6-vadi `W2 V2 p = 0,9322` (`N_99=2`, `> p_crit_cost=0,5122`), fakat `1 K` Mod B `3,40×` yavaş ve `N=1` **`EVPI = $0`** (`N_be = 6,03` makine). `20 mK` DR baz optimal; `1 K` lab transferi yalnızca filo (`N ≥ 6`) kararıyla açılır. |

*(Tarihsel ayrıntı: `R1–R8` tam kronolojisi ve `Exp119/120/123` adli kayıtları `PROJECT_DOSSIER.md` ve `NOTES_RECOVERY.md` içindedir.)*

## 10. Aşamalı yol haritası

- **M0 (bu proje, `v3.0` tamamlandı):** Kuram, birinci-ilkeler fizik (`Exp124–128`), `CAD v3.0` (`143` parça, `0` çakışma), `145`-parça `BOM_DETAILED` + `6-RFQ`, `src/board/` (`204` bileşen, `0` ERC), `src/machine_control/` v2.0 (`CellISA`) ve `TECHNICAL_MANUAL.md` mühürlendi; açık EDA borcu (`R5/Exp123`) erteli.
- **M1 (`M1_PROTOTYPE_BLUEPRINT.md`, `$2.189.770` nom., `%82` `M3`'e taşınabilir):** Tek-demet `10→5 keV` sayılmış implantasyon (`100 K` IBIC) + `20 mK / 1,50 T / 22,3 µT` tek-yuva ölç–seç–kalibre–`CellISA` gösterimi (`G1–G8` kapıları; dış altyapı & 6-RFQ teklifleri gerekir).
- **M2:** `10²–10³` demetcikli MEMS kafa prototipi + paralel soğuk-ada algılama + `Exp123` SKY130 ASIC anten kapanışı; hata bütçesinin ölçülmesi.
- **M3 (`$4.189.600` nom., `P50=$5,01M` BOM / `$28,24M` Program):** Altın ölçek (**`32×32 = 1.024` eş-adımlı `0,50 mm` demetcik [`16,0×16,0 mm < Ø28,0 mm`, `16×` 64-ch karo]**, `~8.960–9.000` spektroskopi kanalı, `56–82` zincir, `S6.8=D` `20 mK` DR, `1,50 T / 22,3 µT`, `100 K` IBIC, `XY8 N=32–64`); yonga ölçeğinde sertifikalı & programlanabilir yazmaç haritası.
- **M4:** Çok-hücreli bağlaşımlı modüller (`Exp126` `1 µm` adımda `9,50×10⁻⁹ Hz` yalıtım ve `16×` paralel FDMA doğruladı; hücreler arası çift-elektron/tünel bağlaşım donanımı sonraki aşamadır).

## Ek — fizibilite deney programı (durum)

- Exp65–68 (tamam): Verim/hız (`H81`), konum hata bütçesi (`H82`), kapalı çevrim kazancı (`H83`), ilk DD şartnamesi (`H84`).
- **Exp124–128 (tamam, `v3.0` kilidi):** `Exp124` (`H142`, iyon kolonu `Arch-B + HDA-HiRes` & anizotropik/donör saçılması, QA `#59`), `Exp125` (`H143`, `1,50 T / 22,3 µT` mıknatıs + 5-kademe termal/RF + `R8` Koiller, QA `#52`), `Exp126` (`H144`, 32B Hamiltonyen `XY8`-GRAPE + `R3` kapanışı + 16-hücre programlama, QA `#69`), `Exp127` (`H145`, `100 K` soğuk-ada IBIC + `204`-bileşen `0`-ERC + `CellISA v2.0`, QA `#52`), `Exp128` (`H146`, `145`-parça BOM + 6-RFQ + 100k MC & EVPI, QA `#63`).

Belge sürümü **`v3.0`**'dır (`2026-11-23`; `Exp0–Exp128`, `CAD v3.0`, `BOM_DETAILED`, `CellISA v2.0`). Laboratuvar ölçümü, tedarikçi teklifi veya silikon tape-out iddiası hiçbir sürümde yoktur (`no_lab_measurement=true`, `no_supplier_quotes=true`, `tapeout_done=false`).

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
