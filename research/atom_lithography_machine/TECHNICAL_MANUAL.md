# Atom Litografi Makinesi — Kapsamlı Teknik El Kitabı (`TECHNICAL_MANUAL.md`, v6.0)

**Sürüm:** `v6.0` (Tarih: `2026-11-23`; Tam Modüler Ölçekleme, `qLDPC` Devrimi & Canlı IBM QPU Kilidi — `Exp124`–`Exp146`, `CAD v6.0`, `BOM_DETAILED v6.0` + `9-RFQ`, `Option-Q` `qRAM`/`S1-Multi`, `D3` GRAPE `M4` + `Option-HPC` `100G` RDMA, `[[144,12,12]]` Gross Code `qLDPC`, `CellISA v4.0` + `auto_recal.py` + canlı `156Q` `ibm_marrakesh` QPU & `Exp146` Master `v6.0` Dijital İkiz)
**Kapsam:** Tek-kriyostatlı, **`32×32 = 1.024` eş-adımlı (`0,50 mm`) demetçikli** Atom Litografi Makinesi'nin birinci-ilkeler fiziği (`Exp124–146`), `1530,1 K` flaş + `S5.6` MBE, `D3` `K=8` Fourier GRAPE `M4` (`p_2q = %0,337–%0,395`), **`[[144,12,12]]` Gross Code `qLDPC` (`108L = 1` kriyostat, `$63.827/L_sys`)**, `Option-Q` (`8.403×–25.122×` `qRAM`), `Option-HPC` (`100G` RDMA), **`CellISA v4.0` (`20` op) + `auto_recal` + canlı `156Q` `ibm_marrakesh`**, `CAD v6.0` (`199` parça / `40/40`), `BOM v6.0` (`174` parça / `9-RFQ`) ve `Exp146` Master `v6.0` Dijital İkiz el kitabı.
**Ana Referanslar:** [DESIGN.md](DESIGN.md) (`v6.0`), [MODULAR.md](MODULAR.md) (`v6.0-ICD`), [M1_PROTOTYPE_BLUEPRINT.md](M1_PROTOTYPE_BLUEPRINT.md) (`v6.0`), [PROJECT_DOSSIER.md](PROJECT_DOSSIER.md) (`v6.0`), [BOM_ENGINEERING.md](BOM_ENGINEERING.md) (`v6.0`), [RFQ_SPECIFICATIONS.md](RFQ_SPECIFICATIONS.md) (`9-RFQ`), [LITERATURE.md](LITERATURE.md), `research/atom_lithography_machine/cad/cad_verification.json`, `results/exp124..146/`.

> **Epistemik Sözleşme (Kristal Ayrım):**
> - **Silikon `³¹P` fabrikasyon, `CAD v6.0`, `BOM v6.0`, `M1–M4` makine fiziği ve `auto_recal.py`:** `M0` tasarım & sayısal fizibilite (**`no_lab_measurement=true`, `no_supplier_quotes=true`, `tapeout_done=false`**). Tüm ön-kayıtlı `FAIL` hükümleri (`Exp124, 126, 127, 129, 131, 134, 136, 137, 138, 139, 142, 143`) gizlenmeden raporlanır.
> - **Kontrol yığını (`CellISA v4.0 → OpenQASM 3.0`), `Echo/XY4` DD, `d=3` sendrom dekoderi ve bit-kesin `Q16.16` BOED (`Exp145`):** **Gerçek `156`-kübitlik `ibm_marrakesh` (IBM Heron r2, `job_id = dc1tdo2nj2vs73dfrfl0`, `16 PUB × 4.096 shot`, `32,54 s`) süperiletken bulut QPU üzerinde canlı doğrulandı** (`{Canlı-Donanım-IBM-QPU}`, `SECRET_LEAKS = 0`).

---

## İçindekiler

- [Bölüm 1: Sistem Mimarisi, Çalışma Noktası (`v6.0`) ve Fiziksel Gerçeklik Sınırları](#bölüm-1-sistem-mimarisi-çalışma-noktası-v60-ve-fiziksel-gerçeklik-sınırları)
- [Bölüm 2: İyon Kolonu Optiği & Liouville/Scherzer Matematiği (`Exp124`)](#bölüm-2-iyon-kolonu-optiği--liouvillescherzer-matematiği-exp124)
- [Bölüm 3: Kriyojenik `1,50 T / 22,3 µT` Mıknatıs, Meissner Kalkanı & 5-Kademe Termal/RF Bütçesi (`Exp125`)](#bölüm-3-kriyojenik-150-t--223-µt-mıknatıs-meissner-kalkanı--5-kademe-termalrf-bütçesi-exp125)
- [Bölüm 4: IBIC Tek-İyon Algılama & Soğuk-Ada Ön-Uç Elektroniği (`Exp127` & `src/board/`)](#bölüm-4-ibic-tek-iyon-algılama--soğuk-ada-ön-uç-elektroniği-exp127--srcboard)
- [Bölüm 5: Kuantum Kontrol, `Q16.16` FPGA, `CellISA v4.0`, `auto_recal` & Canlı IBM QPU Kılavuzu](#bölüm-5-kuantum-kontrol-q1616-fpga-cellisa-v40-auto_recal--canlı-ibm-qpu-kılavuzu)
- [Bölüm 6: Parametrik CAD v6.0 Montaj, Kütle Bütçesi & `40/40` Tolerans Rehberi](#bölüm-6-parametrik-cad-v60-montaj-kütle-bütçesi--4040-tolerans-rehberi)
- [Bölüm 7: Modüler BOM v6.0 (`174` Parça), `9-RFQ` Stratejisi, `Exp128 v6.0` MC & `qLDPC` Ekonomisi](#bölüm-7-modüler-bom-v60-174-parça-9-rfq-stratejisi-exp128-v60-mc--qldpc-ekonomisi)
- [Bölüm 8: Kurulum, Devreye Alma, Kalibrasyon SOP & EHS Güvenlik Protokolleri](#bölüm-8-kurulum-devreye-alma-kalibrasyon-sop--ehs-güvenlik-protokolleri)
- [Bölüm 9: `v4.0` Yükseltme Paketi (`Exp129`–`Exp135`): `VOKL-6`, Flaş Tavlama, `M4` cQED, `BOED`, `PT420` & Birleşik Dijital İkiz](#bölüm-9-v40-yükseltme-paketi-exp129exp135-vokl-6-flaş-tavlama-m4-cqed-boed-pt420--birleşik-dijital-ikiz)
- [Bölüm 10: `v5.0` Hata-Toleranslı Yükseltme Paketi (`Exp136`–`Exp141`): `sp³d⁵s*` TB, `P4 Echo CZ`, MWPM FT, `1530 K`+MBE, `N_mux*=32` & Master Dijital İkiz](#bölüm-10-v50-hata-toleranslı-yükseltme-paketi-exp136exp141-sp³d⁵s-tb-p4-echo-cz-mwpm-ft-1530-kmbe-n_mux32--master-dijital-ikiz)
- [Bölüm 11: `v6.0` Modüler Ölçekleme, `qLDPC` Devrimi & Canlı IBM QPU Doğrulaması (`Exp142`–`Exp146`)](#bölüm-11-v60-modüler-ölçekleme-qldpc-devrimi--canlı-ibm-qpu-doğrulaması-exp142exp146)

---

## Bölüm 1: Sistem Mimarisi, Çalışma Noktası (`v6.0`) ve Fiziksel Gerçeklik Sınırları

### 1.1 Tek-Kriyostatlı Entegre Sistem Blok Diyagramı

Atom Litografi Makinesi, ultra-yüksek vakumlu (UHV, `< 1×10⁻⁹ mbar`) tek bir dikey kolon ekseninde **deterministik tek-iyon implantasyonu** ile **kriyojenik spin spektroskopisi, sertifikasyonu ve kuantum programlamayı** birleştiren 8-modüllü (`M1–M8`) bütünleşik bir fabrikadır (`[Exp80, Exp124, Exp125, Exp127 | DESIGN.md, MODULAR.md]`, `{Model}`).

```text
  [S1.1 Duoplasmatron (+5 kV)] --> [S1.4 Yoğuşturucu] --> [S1.2 Wien 0,45 T (10 keV)]
                                                                   |
  [S1.5 HDA-HiRes (ΔE=0,453 eV)] <-- [S1.6 Transfer] <-------------+
          |  (üst astar -5,0 kV; 10 -> 5 keV son yavaşlatma)
          v
  [S2.1 MEMS Açıklık (Ø28 mm)] --> [S2.2 1024-Kanal Boşluklayıcı (0,50 mm)] --> [S2.3 Arch-B Mini-Mercek (WD=0,250 mm)]
                                                                   |  (5 keV 31P+, σ_tot=3,715 nm)
          +----< [S3 Soğuk-Ada 100 K IBIC CSA (LTC6268, ENC=24,1 e-)] <---+
          |      (sayılmış iyon vuruşu -> FPGA 100 MHz blanker_tile.v)    |
          v                                                               v
  [S7 Elektronik Raf + CellISA/GRAPE] <====> [Si Pul (0 V, 100 K implant / 20 mK okuma)]
          |                                         ^
          +--> 56× RF/MW Hattı (NL=160, 8960 kn) ---+--> [S6.3 8-Bobin NbTi Mıknatıs: 1,50 T ± 17,81 ppm]
          |                                              [S6.6 Nb+Cryoperm Kalkan (z=-155 mm): 22,3 µT]
          +--> [S4 Granit + Piezo + 3-Eksen He-Ne] <---> [S5 UHV Oda (34,86 L) + Yük-Kilidi + S6.8 DR]
```

### 1.2 Kilitli `v6.0` Sistem Çalışma Noktası

| Parametre | `v6.0` Kilitli Değer | Önceki (`v5.0` / `Exp136–141`) | Değişim Nedeni & Kaynak | Etiket |
|---|---|---|---|---|
| **`D3` `K=8` Fourier GRAPE `M4`** | **`p_2q = %0,337–%0,395`**, **`F_avg = %99,73`, `F_Bell = %99,69`**, **`Λ_D3_phys = 2,825`** (`0,894 µs` muhaf. / `1,126 µs` yankılı, `%100 ≤ 300 MHz`) | `P4` `p_err = %0,92`, `D2 Λ = 1,40` (`679` kriyo) | `100L` yüzey kodu `679 → 100` kriyo (`6,8×`); `Q=1e6` + Rota C `[Exp143]` | `{Sayısal-Simülasyon}` |
| **`[[144,12,12]]` `qLDPC` Devrimi** | **`L_max = 268,3 µm ≤ 300 µm`** (`0` rezonatör değişikliği!), **`120L` tek `LD400`'de (`108L = 1` kriyo, `$63.827/L_sys`, `W3` `$0,0085/L`)** | Yüzey kodu `679` (`D2`) / `100` (`D3`) kriyo, `$14,94M / $2,76M` | **`234×` sistem maliyeti çöküşü**; `f*=%1,5+2 MV/m, N=8 → %99,94` `108L` yonga `[Exp144]` | `{Sayısal-Simülasyon}` |
| **`Option-Q` (`qRAM` & `S1-Multi`)** | Chebyshev-5 `0,0004 dB`, `F_SWAP_rt = 0,9858`, **`8.403×–25.122×` ömür (`+0,78 µW @ 20 mK`)**; `10 km ¹⁶⁷Er 1.352,3 Hz`, `¹²¹Sb −%41,5` | Yok (yalnız `³¹P`) | Tak-çıkar `+$168k / +9,20 kg` (`S1.7-01` + `S9.4-01..03`) `[Exp142]` | `{Sayısal-Simülasyon}` |
| **`Option-HPC` `100G` RDMA Dekoder** | `τ_ingest = 777 ns`, `d=37 SC 6,34 µs < 6,70 µs`, **`qLDPC 108L 2,32 µs < 2,62 µs`** (tek `4U`, `+$132k / +64 kg / 2.195 W`) | Gerçek-zamanlı dekoder gecikmesi çözülmemişti | `0 W` kriyo yüküyle `backlog-free` dekoder kapanışı `[Exp143]` | `{Sayısal-Simülasyon}` |
| **Canlı IBM QPU & `CellISA v4.0`** | **Gerçek `156Q` `ibm_marrakesh` (`dc1tdo2nj2vs73dfrfl0`):** Bare `0,333` → Echo `0,922` → XY4 `0,928`, Bell `0,9733`, `d=3` `5,16×/7,83×`, `Q16.16 BOED` `1,6 Hz`; `20` op + `auto_recal` `4/4` | `CellISA v3.5` (`17` op), yalnızca simülasyon | Yazılım/DD/QEC/BOED canlı QPU'da doğrulandı; **`252/252` `pytest` (`28/28`)** `[Exp145]` | **`{Canlı-Donanım-IBM-QPU}`** + `{Model}` |
| **CAD & Kütle (`v6.0`)** | **`199` parça, `1.108,137 kg`, `8/8` STL (`39.536` üçgen, `591,200 L`), `0/19.701` çakışma, `40/40` boşluk** | `189` parça, `1.034,94 kg`, `0/17.766`, `32/32` | `+ Option-Q` (`9,20 kg`) + `Option-HPC` (`64,00 kg`), `30/30` test `[cad_verification.json]` | `{EDA}` |
| **Modüler BOM v6.0 & `9-RFQ`** | **`174` parça (`M1 Base $2,466M`, `M3 Base $5,248M`, `M3 Full $5,548M`), `9-RFQ %77,7 / %92,6` MC var**, `P(Prog>$100M) = %4,92 < %5` | `167` parça (`M3 $5,248M`), `8-RFQ %76,4` | `M1/M3 Base` korundu; `+$300k` tak-çıkar `Option-Q/HPC`; `0,000 kg` CAD uyumu `[Exp128 v6.0]` | `{Model}` |

### 1.3 Baz Üretim Modu (Mod B) vs. Deterministik `²⁹Si` Opsiyonu (Mod A) ve Donör Saçılması Gerçeği

Makine iki fiziksel yazmaç üretim modunu destekler, ancak **`Exp124` (`CD8 PASS`) sonrasında üretim omurgası kesin olarak Mod B'de kilitlenmiştir** (`[Exp65, Exp124 | DESIGN.md, results/exp124_ion_column_optics/exp124.json]`):

1. **Mod B — Doğal/Ayarlı `f = %1` `²⁹Si` Alt-Tabakaya `³¹P⁺` İmplantı (BAZ):** Her hücreye yalnızca bir `³¹P⁺` donör yerleştirilir; çevresindeki 8 çekirdek kübiti alt-tabakadaki rastgele `²⁹Si` dağılımından seçilir (`AtlasSelector`, `Exp48`). Donör pozisyonunun 3B saçılması çekirdek kübitlerinin göreceli istatistiğini değiştirmediğinden **Mod B donör saçılmasına tamamen bağışıktır**: tek-deneme sertifikasyon verimi `%51`, 3-deneme çevrimiyle **`%87,92`** (`3.517/4.000`, `certs_v224_demo.jsonl`), günlük fabrika kapasitesi **`1,372×10⁸` – `1,973×10⁸` sertifikalı yazmaç/gün** (`{Model}`).
2. **Mod A — Zenginleştirilmiş `²⁸Si` İçine Deterministik `²⁹Si⁺` + `³¹P⁺` İmplantı (AR-GE OPSİYONU):** Önceki `Exp82/91` hesapları `³¹P` donörünü `(0, 0, z_d)` noktasında sabit varsayıyordu (`%69,25` izotropik). `Exp124`, hem 3B anizotropik `²⁹Si` saçılmasını hem de `³¹P` donörünün kendi 3B implant saçılmasını (`σ_r, σ_z` + geri-saçılma) katınca şu fiziksel gerçeği ortaya çıkardı (`[Exp124 | exp124.json]`, `{Sayısal-Simülasyon}`):
   - Sabit donörde 3B anizotropik BCA (`3,715 × 2,88 nm`) verimi `%76,25`'e yükselir; ancak stokastik `³¹P` donör saçılması açıldığında verim **%33,75 puan düşerek `%42,50`'ye** (`P91` BCA: `%43,75`), Holmes derinlik modelinde ise **%41,50 puan düşerek `%28,00`'e** iner (`%10,0` donör geri-saçılması).
   - Dolayısıyla Mod A, alt-5 nm yüksek hassasiyetli özel çekirdek dizilimleri için Ar-Ge modu olarak tutulur; seri yazmaç üretimi Mod B üzerinden yürür.

### 1.4 Aktif Odak Politikası & SKY130 Boşluklayıcı Çip (`R5` / `Exp123`) Statüsü

Kullanıcı politikası (`2026-11-22`, `{Kullanıcı-Kararı}`) gereği aktif mühendislik odağı **Atom Litografi Makinesi'nin** kendisidir. `S2.4` boşluklayıcı sürücü CMOS denetleyicisinin açık kaynaklı `SKY130` ASIC prototipinde (`Exp123`), `77` anten ihlali otomatik `repair_antennas` akışıyla `10`'a indirilmiş; kalan `10` ihlal (yüksek fanout'lu `clk` ve `rst_n` ağacında `met4/via4/met5`) henüz kapatılmadığı için tape-out yapılmamıştır (`tapeout_done=false`). `M1` prototipinde `S2.2` boşluklayıcı plakası harici `FPGA + HV sürücü` (`S2.4` ayrık kurulum) ile çalıştırılacak, ASIC anten kapanışı yalnızca `M2/M3` yüksek-yoğunluklu tümleşik sürücü aşamasında tetiklenecektir (`[Exp123 | results/exp123_or_antenna/exp123.json]`, `{EDA}`).

---

## Bölüm 2: İyon Kolonu Optiği & Liouville/Scherzer Matematiği (`Exp124`)

Bu bölüm, `experiments/exp124_ion_column_optics/{column_physics.py, anisotropic_yield.py, run_exp124.py}` tarafından doğrulanan (`tests/test_exp124.py` `6/6 PASS`) birinci-ilkeler iyon optiği fiziğini ve `10 → 5 keV` yavaşlatmalı 8-kademeli kolon tasarımını belgeler (`[Exp124 | results/exp124_ion_column_optics/exp124.json]`, `{Sayısal-Simülasyon}`).

### 2.1 Lagrange–Helmholtz Parlaklık Korunumu ve `_attack91.py` Açığının Kapatılması

Paraksiyel elektrostatik iyon optiğinde, faz-uzayı hacminin Liouville korunumu indirgenmiş parlaklık $B_r$'yi enerji boyunca sabit tutar (`{Analitik}`):

$$B_r = \frac{B(E)}{E} = \frac{I}{\pi^2 r_{\text{geom}}^2 \alpha^2 E} = \text{sabit}$$

`Exp91` duoplasmatron referansı (`B = 159.155 A/m²/sr @ 20 keV`) için indirgenmiş parlaklık $B_r = 7,958\text{ A/(m}^2\cdot\text{sr}\cdot\text{V)}$'dir. Eğer kaynak doğrudan $5\text{ keV}$'de çekilseydi parlaklık $B(5\text{ keV}) = 39.789\text{ A/m}^2/\text{sr}$ olurdu; oysa `1 ion/ms` akım ve $r_{\text{geom}} = 1,50\text{ nm}$ için gereken parlaklık $72.149\text{ A/m}^2/\text{sr}$'dir (**`1,813×` eksiklik**, doğrudan $5\text{ keV}$ çekiminde $r_{\text{geom}} = 2,020\text{ nm}$). `Exp124` bu açığı **iki-potansiyelli üst kolon** (`+5,0 kV` kaynak anodu, `−5,0 kV` üst astar → `10 keV` taşıma) ve **`S2.3` mini-mercekte `10 → 5 keV` son yavaşlatma** ile Liouville-tutarlı biçimde kapatır (`CD1 PASS`).

### 2.2 2B Eksenel Laplace Çözücüsü & Scherzer–Delinme Değişmezi (`CD3 FAIL` Keşfi)

Silindirik simetrik $(r, z)$ ızgarada eksenel potansiyel $\Phi(r, z)$, $\nabla^2 \Phi = \frac{\partial^2 \Phi}{\partial r^2} + \frac{1}{r}\frac{\partial \Phi}{\partial r} + \frac{\partial^2 \Phi}{\partial z^2} = 0$ denkleminin seyrek doğrusal çözücüyle (`scipy.sparse.linalg.spsolve`) çözülmesiyle elde edilir. Eksen üstü potansiyel $\phi(z) = \Phi(0, z)$ kullanılarak paraksiyel ışın denklemi (`DOP853`) entegre edilir:

$$r''(z) + \frac{\phi'(z)}{2\phi(z)} r'(z) + \frac{\phi''(z)}{4\phi(z)} r(z) = 0$$

Sayısal tutarlılık kontrolleri (`CD2 PASS`): Lagrange–Helmholtz Wronskian değişmezi $W = \sqrt{\phi}(r_1 r_2' - r_1' r_2)$ tüm geometrilerde $2,05\times 10^{-8}$ – $4,87\times 10^{-8} < 10^{-6}$ aralığında korunur; Scherzer analitik integrali ile doğrudan ışın-izleme kromatik sapma $C_c$ arasındaki fark yalnızca `%0,00` – `%0,12`'dir.

**Temel Fiziksel Alt Sınır (`CD3 FAIL` — Scherzer–Delinme Değişmezi):** Vakum elektrot delinme sınırı $E_{\text{gap}} \le 12\text{ MV/m}$ ve iniş potansiyeli $V_{\text{land}} = 5\text{ kV}$ altında boyutsuz Scherzer–delinme değişmezi tüm statik dairesel elektrostatik merceklerde katı bir alt sınır gösterir (`[Exp124 | exp124.json]`, `{Sayısal-Simülasyon}`):

$$\kappa_c \equiv \frac{C_c \cdot E_{\text{gap}}}{V_{\text{land}}} \ge 4,67 \quad (\text{taranan en düşük: } 4,665;\; \text{Arch-B: } 5,640)$$

Bu eşitsizlik, $V_{\text{land}} = 5\text{ kV}$ ve $E_{\text{gap}} \le 12\text{ MV/m}$ iken $C_c \ge 4,67 \times 5000 / 12\times 10^6 \approx 1,95\text{ mm}$ alt sınırını dayatır. Dolayısıyla `Exp82/91`'de test edilmeden varsayılan `C_c ≤ 0,50 mm` hedefi statik dairesel mercekle **fiziksel olarak ulaşılamaz**.

### 2.3 `Arch-B` Mini-Mercek + `HDA-HiRes` Enerji Süzgeci Ortak Çözümü (`CD4 PASS`)

Toplam demet leke yarıçapı (quadrature) şu 4 katkının karekök toplamıdır (`{Analitik}`):

$$\sigma_{\text{spot}}^2 = \sigma_{\text{geom}}^2 + \left(k_c\, C_c\, \alpha_{\text{land}}\, \frac{\Delta E_{\text{FWHM}}}{E_{\text{land}}}\right)^2 + \left(k_s\, C_s\, \alpha_{\text{land}}^3\right)^2 + \sigma_{\text{diff}}^2$$

Burada $C_c = 2,660\text{ mm}$'lik yükselişi telafi etmek için `S1.5` yarım-küresel saptırıcı analizör **`HDA-HiRes`** (`R₀ = 40 mm`, `E_pass = 100 eV`, yarık `0,35 mm` → **`ΔE_FWHM = 0,453 eV`**, geçiş `τ = 0,071`) olarak sıkılaştırılmıştır.

| Mercek Mimarisi | Enerji Geçişi | Adım / Delik `D` | Yükseklik `h` | Çalışma Uzaklığı `WD` | `E_gap` (`MV/m`) | `C_c` (`mm`) | `C_s` (`mm`) | Not |
|---|---|---|---|---|---|---|---|---|
| **`Arch-B` (BAZ)** | `10 → 5 keV` | `0,50 mm` / `0,30 mm` | `1,76 mm` | **`0,250 mm`** | **`10,60`** | **`2,660`** | **`10,786`** | Alansız `0 V` pul; kilitli baz `[Exp124]` |
| `Arch-B15` (Alt-1) | `15 → 5 keV` | `0,50 mm` / `0,30 mm` | — | `0,480 mm` | `11,04` | `2,615` | `14,311` | Daha geniş `WD`, daha yüksek HV `[Exp124]` |
| `Arch-C` (Alt-2) | `10 → 5 keV` (2-kademe) | `32 µm` üst açıklık | — | `0,083 mm` | `9,79` | `2,383` | `51,58` | Dar `WD`, yüksek `C_s` `[Exp124]` |

**Kilitli `Arch-B` + `HDA-HiRes` Çalışma Noktaları (`CD4 PASS`, `σ_lat_BCA = 3,25 nm`, `σ_tot = √(σ_spot² + σ_lat²)`):**

| Çalışma Noktası | Kaynak `T_i` / Süre | `α_land` (`mrad`) | `σ_spot` (`nm`) | `σ_tot` (`nm`) | Hedef (`≤ 3,80 nm`) | `η_IBIC` (`5 keV, 0,5 pF`)* |
|---|---|---|---|---|---|---|
| `ArchB_HiRes_Ti0p25_10ms` / `LMIS_1ms` | `0,25 eV` / `10 ms` (LMIS `1 ms`) | `6,10` | **`1,428`** | **`3,674`** | **PASS** (`σ_spot ≤ 1,50`) | `0,9914` (`Exp124`) / `0,99936` (`Exp127` 100K) |
| **`ArchB_HiRes_Ti0p5_15ms` (KANONİK BAZ)** | **`0,50 eV` / `15 ms`** | **`6,40`** | **`1,532`** | **`3,715`** | **PASS** (`σ_tot ≤ 3,80`) | `0,9914` (`Exp124`) / `0,99936` (`Exp127` 100K) |
| `ArchB_HiRes_Ti1p0_25ms` (Kötü-Durum) | `1,00 eV` / `25 ms` | `—` | `1,605` | `3,746` | **PASS** (`σ_tot ≤ 3,80`) | `0,9914` (`Exp124`) / `0,99936` (`Exp127` 100K) |

*\*Not: `Exp124`'teki `0,9914` değeri `Exp72` basitleştirilmiş ENC formülüyledir; Bölüm 4'te (`Exp127`) tam Lindhard + soğuk-ada `100 K / 1,2 µs / 1 GΩ` modeliyle kesin algılama verimi `0,99936` olarak doğrulanmıştır.*

### 2.4 Wien Kütle Süzgeci (`S1.2`) & Coulomb/Boersch Bastırma (`CD5 PASS`)

- **Wien Süzgeci (`S1.2`, `10 keV`):** $B = 0,45\text{ T}$, $E_w = v_0 B$ ($V_p = 1.348\text{ V}$), etkin boy $L_w = 80\text{ mm}$, sürüklenme $L_d = 70\text{ mm}$. `³¹P⁺` ($30,974\text{ u}$) ile başlıca izobarik kirletici `³²PH⁺` ($31,982\text{ u}$) arasındaki yatay ayrılma **`dx = 0,785 mm`** (`0,20 mm` çıkış yarığının **`3,92×`** katı; kütle çözünürlüğü **`R_m = 120,6`**).
- **Uzay-Yükü / Boersch (`CD5 PASS`):** Üst kolonu `5 keV` yerine `10 keV`'de taşımak laminar Coulomb bulanıklığını **`2,83×`** (`15 keV`: `5,20×`), stokastik Holtsmark/Boersch bulanıklığını **`2,52×`** (`15 keV`: `4,33×`) bastırır. `1 ion/ms` akışında her demetçikte aynı anda kolonda bulunan ortalama iyon sayısı **`N̄₁ = 1,40×10⁻³ ≪ 0,01`** olduğundan tek-demetçik içinde iyon-iyon çarpışması ihmal edilir.

### 2.5 8-Kademeli İyon Kolonu İstif & Yüksek Gerilim Şeması

Kolon toplam yüksekliği **`562,66 mm`**, en büyük dış çapı **`OD = 110,0 mm`**, temel kütlesi **`25,92 kg`**'dır (`CAD v6.0 S1` flanşlarla temel `25,977 kg`, isteğe bağlı `Option-Q S1-Multi +4,80 kg` ile `30,777 kg`). HV potansiyel mimarisi: **pul/IBIC = `0 V` (toprak)**, **üst kolon astarı = `−5,0 kV`**, **duoplasmatron anodu = `+5,0 kV`** (`[Exp124 | exp124.json]`, `{Sayısal-Simülasyon}`).

| Sıra (Alttan) | Modül Kodu | Bileşen | Yükseklik `h` (`mm`) | Alt Aralık (`mm`) | Dış Çap `OD` (`mm`) | İç Delik (`mm`) | Kütle (`kg`) | Nominal Potansiyel |
|---|---|---|---|---|---|---|---|---|
| 1 | `S2.3` | `Arch-B` `1.024`-Kanal (`32×32 @ 0,50 mm`) Yavaşlatmalı Mini-Mercek | `1,76` | `WD = 0,250` | `60,0` | `0,30` (`×1.024`) | `0,20` | `−5.000 → +3.700 → 0 V` (`E ≤ 10,6 MV/m`) |
| 2 | `S2.2` | `1.024`-Kanal (`0,50 mm` eş-adımlı) Boşluklayıcı + Demet Durdurucu | `4,00` | `1,00` | `60,0` | `0,30` (`×1.024`) | `0,12` | `−5.000 ± 53,3 V` (`16×` 64-ch karo) |
| 3 | `S2.1` | MEMS Açıklık Plakası (`0,50 mm` eş-adımlı) + Kinematik Kafa | `24,00` | `0,65` | `100,0` | **`28,0`** (`2,69 mm` marj) | `1,40` | `−5.000 V` (yüzer astar) |
| 4 | `S1.6` | Telesentrik Transfer Merceği (Einzel) | `65,00` | `8,00` | `84,0` | **`28,0`** (sıfır kırpma) | `2,60` | `−5.000 V` astar / odak |
| 5 | `S1.5` | `HDA-HiRes` Enerji Süzgeci (`R₀=40, slit=0,35`) | `95,00` | `10,00` | `110,0` | `16,0` | `5,20` | `−5.000 V` (`E_pass=100 eV`) |
| 6 | `S1.2` | Wien Kütle Süzgeci (`0,45 T`) + `200 µm` Yarık | `150,00` | `8,00` | `110,0` | `12,0` | `6,80` | `−5.000 V ± 674 V` (`V_p=1.348 V`) |
| 7 | `S1.4` | Çekici & Yoğuşturucu Einzel Mercek | `45,00` | `6,00` | `84,0` | `20,0` | `2,10` | `+5.000 V → −5.000 V` (`10 keV`) |
| 8 | `S1.1` | `PH₃` Duoplasmatron İyon Kaynağı | `140,00` | `4,00` | `90,0` | `0,10` (anot) | `7,50` | `+5.000 V` anot |
| **Toplam** | **`S1+S2`** | **8-Kademe Tam Kolon (`Z_WAFER=500,00 → z_CAD: 500,25..1062,66 mm`)** | **`562,66`** *(aralıklar dahil)* | — | **`max 110,0`** | — | **`25,92`** | `10 → 5 keV` yavaşlatmalı; UHV `R_iç=182,0 mm` |

### 2.6 3B Anizotropik & Stokastik `³¹P` Donör Verim Tablosu (`CD6–CD8`, `400` Deneme)

| Senaryo (`N=1024` deneme kümesi, `400` tam yazmaç denemesi) | Yatay `σ_xy` × Düşey `σ_z` (`nm`) | Yüzey Kesme (`z > 0`) | `³¹P` Donör Saçılması | Sertifikalı Verim | Yüzey Kaybı / Not |
|---|---|---|---|---|---|
| `ISO_EXP91_REF` (Denetim referansı) | `3,80 × 3,80` | Hayır | Sabit | `%69,25` (`277/400`; `49/100`) | `Exp91` tam tekrarlama `[Exp124]` |
| `ANISO_BCA_PURE` | `3,25 × 2,88` | Evet | Sabit | **`%78,75`** (`315/400`) | Yüzey kaybı `%1,26` `[Exp124]` |
| `ANISO_P91_BCA` | `3,80 × 2,88` | Evet | Sabit | **`%76,75`** (`307/400`) | `CD6 PASS` `[Exp124]` |
| `ANISO_EXP124_BCA` (`Arch-B + HDA-HiRes`) | `3,715 × 2,88` | Evet | Sabit | **`%76,25`** | Kanonik sabit-donör Mod A `[Exp124]` |
| `ANISO_P91_HOLMES` (yüzeysiz vs `z > 0`) | `3,80 × 5,27` | Hayır → Evet | Sabit | `%63,25` → **`%69,50`** | **`CD7 FAIL`:** `%11,0` üst-yarı seyirci elenir → spektral sıkışma rahatlar (`elig_med 8→9`) |
| `ANISO_P91_BCA_DONOR` | `3,80 × 2,88` | Evet | **3B Stokastik** | **`%43,75`** (`175/400`) | **`−33,0 pp`**, donör geri-saçılma `%1,5` (`CD8 PASS`) |
| `ANISO_EXP124_BCA_DONOR` | `3,715 × 2,88` | Evet | **3B Stokastik** | **`%42,50`** | Mod A gerçekçi BCA tavanı `[Exp124]` |
| `ANISO_P91_HOLMES_DONOR` | `3,80 × 5,27` | Evet | **3B Stokastik** | **`%28,00`** (`112/400`) | **`−41,5 pp`**, donör geri-saçılma `%10,0` |
| **Mod B (`f = %1` doğal `²⁹Si`, BAZ)** | — | — | **Bağışık** | **`%51,0` / `%87,92` (3-atış)** | Donör saçılmasına sıfır duyarlılık `[Exp65, Exp127]` |

---

## Bölüm 3: Kriyojenik `1,50 T / 22,3 µT` Mıknatıs, Meissner Kalkanı & 5-Kademe Termal/RF Bütçesi (`Exp125`)

Bu bölüm, `experiments/exp125_cryo_magnet_readout/{magnet_solver.py, cryo_rf_solver.py, ancilla_valley_r8.py, run_exp125.py}` tarafından doğrulanan (`CV1–CV6 6/6 PASS`, `tests/test_exp125.py` `11/11 PASS`) ve Risk `R7`'yi kapatan kriyojenik mıknatıs, kalkan, 5-kademe termal/RF ve vadi girişim fiziğini belgeler (`[Exp125 | results/exp125_cryo_magnet_readout/exp125.json]`, `{Sayısal-Simülasyon}`).

### 3.1 Eksenel Simetrik Biot–Savart & Meissner BEM Formülasyonu

Yarıçapı $a$, eksenel konumu $z_0$ olan akım halkasının $(r, z)$ noktasındaki manyetik alan bileşenleri birinci ve ikinci tür tam eliptik integrallerle ($K(k), E(k)$, $k^2 = \frac{4ar}{(a+r)^2 + (z-z_0)^2}$) tam olarak hesaplanır (`{Analitik}`):

$$B_z(r, z) = \frac{\mu_0 I}{2\pi \sqrt{(a+r)^2 + (z-z_0)^2}} \left[ K(k) + \frac{a^2 - r^2 - (z-z_0)^2}{(a-r)^2 + (z-z_0)^2} E(k) \right]$$

$$B_r(r, z) = \frac{\mu_0 I (z-z_0)}{2\pi r \sqrt{(a+r)^2 + (z-z_0)^2}} \left[ -K(k) + \frac{a^2 + r^2 + (z-z_0)^2}{(a-r)^2 + (z-z_0)^2} E(k) \right]$$

`Nb` Meissner kalkanı yüzeyindeki perdeleme akımı $J_\phi(s)$, sınır elemanı yöntemiyle (BEM) $\mathbf{B}_{\text{tot}} \cdot \hat{\mathbf{n}} = 0$ sınır koşulundan çözülür. **Sayısal doğrulama (`CV1 PASS`):**
- $\max\|\nabla \cdot \mathbf{B}\| = 7,90\times 10^{-7}\text{ T/m}$, $\max\|\mathbf{B} - \nabla \times \mathbf{A}\| = 8,77\times 10^{-7}\text{ T}$.
- `8×8` vs `12×12` Gauss–Legendre dördün farkı: $4,54\times 10^{-14}$.
- BEM düğüm yakınsaması (`M = 102` vs `206`): $5,85\times 10^{-8}$.
- Depolanan manyetik enerji tutarlılığı: $\frac{1}{2}\mathbf{I}^T \mathbf{L}\mathbf{I} = 18,941\text{ kJ}$ vs $\int \frac{B^2}{2\mu_0}\,dV = 18,895\text{ kJ}$ (`%0,244` fark).

### 3.2 8-Bobinli `NbTi` Mıknatıs (`S6.3`) Geometrisi, Mekanik & Quench Güvenliği (`CV2–CV3 PASS`)

Mıknatıs **`Ø150,0 mm`** açık iç boşluğa, **`36,0 mm`** orta düzlem erişim aralığına (`4K` soğutma tüpü + optik/interferometre erişimi için) ve **`Ø352,0 mm`** dış çapa sahiptir (toplam `5,48 km` `Cu/NbTi` tel). Koordinat merkezi $z_{\text{loc}} = 0$ pul yüzeyidir (`[Exp125 | exp125.json]`, `{Sayısal-Simülasyon}`).

| Bobin | İç–Dış Yarıçap `R` (`mm`) | Eksenel Konum `z_loc` (`mm`) | Sarım `N` | Akım `I` (`A`) | İşlev |
|---|---|---|---|---|---|
| `M_upper` | `78,0 – 112,0` | `+18,0 .. +72,0` | `1.600` | `+40,24` | Ana alan (üst) |
| `M_lower` | `78,0 – 112,0` | `−72,0 .. −18,0` | `1.600` | `+216,47` | Ana alan (alt) |
| `S_upper` | `78,0 – 116,0` | `+76,0 .. +112,0` | `1.100` | `+255,91` | Homojenlik düzeltme (üst) |
| `S_lower` | `78,0 – 116,0` | `−112,0 .. −76,0` | `1.100` | `−195,26` | Homojenlik & alt gradyan kırıcı |
| `A_upper` | `144,0 – 168,0` | `+20,0 .. +104,0` | `960` | `−167,99` | Aktif dış kaçak kalkanı (üst) |
| `A_lower` | `144,0 – 168,0` | `−104,0 .. −20,0` | `960` | `−57,20` | Aktif dış kaçak kalkanı (alt) |
| `B_upper` | `56,0 – 82,0` | `−145,0 .. −121,0` | `400` | `+83,90` | Sessiz bölge aktif sıfırlama (üst) |
| `B_lower` | `56,0 – 82,0` | `−184,0 .. −160,0` | `400` | `+22,48` | Sessiz bölge aktif sıfırlama (alt) |

- **Örnek Bölgesi (`r ≤ 2,3 mm, \|z\| ≤ 0,5 mm`):** **`B_z(0, 0) = 1,500000 T ± 17,81 ppm`**, `max \|B_r\| = 0,011 mT`.
- **Süperiletken, Mekanik & Quench (`CV3 PASS`):**
  - Kritik akım oranı: **`max(I / I_c) = 0,212 ≤ 0,55`**, minimum sıcaklık marjı **`ΔT_min = 2,55 K`**.
  - Çember (hoop) gerilimi: **`max \|σ_hoop\| = 52,7 MPa ≤ 80 MPa`**.
  - Pasif boşaltma direnci (`R_dump = 1,563 Ω`, `V_max = 400 V`, sönüm zamanı `τ = 0,370 s`, algılama gecikmesi `t_det = 30 ms`): **`T_hotspot = 64,6 K ≤ 150 K`**.

### 3.3 Çift-Katmanlı Meissner + `Cryoperm-10` Kalkanı (`R7` KAPANDI)

`NbTiN` RF rezonatör bankası `z_loc = −155 mm` düzleminde, `r ≤ 25 mm` yarıçaplı sessiz diske yerleştirilir (`1.963,5 mm²` alan; `56` hat rezonatör çipinin `8,43 mm²` ihtiyacının **`233×`** katı):

1. **Kalkansız (yalnız aktif bobinler):** `max \|B\| = 3,08 mT`.
2. **İç Kalkan — Süperiletken `Nb` (`RRR > 300`) Meissner Fincanı:** `R = 32,0 – 34,5 mm`, `z_loc = −174 .. −136 mm`, üst koaksiyel baca `r = 8,0 mm, h = 11,0 mm`. Yüzeydeki azami alan **`117,12 mT < B_c1(4,2 K) = 134,95 mT`** → **vorteks-serbest tam Meissner rejimi**.
3. **Dış Kalkan — `Cryoperm-10` Ferromanyetik Kılıf:** `R = 39,0 – 41,0 mm`, `z_loc = −180 .. −124 mm`. Doyum sınırı `B_sat = 0,75 T`'nin **`38,1×`** altında; kalkanlama faktörü **`SF = 488,8×`**.
4. **Kalkan İçi Sonuç (`CV2 PASS`):** **`max \|B\| = 22,3 µT`** (`\|B_z\| ≤ 21,6 µT`, `\|B_r\| ≤ 7,8 µT`) — yüksek-$Q$ `NbTiN` rezonatörlerin `≤ 1 mT` sınırının **`45×`** altında. Risk `R7` tamamen kapanmıştır.
5. **Üst MEMS Kaçak Alanı:** `S2.3` mini-mercek konumunda (`z_loc = +268 mm`) kaçak alan `108,1 mT`'dir; `S2` gövdesi manyetik olmayan `Si/Ti/BeCu` malzemelerden seçilerek mekanik kuvvetten yalıtılmıştır.

### 3.4 5-Kademeli Termal Bütçe & RF Yansıma SNR (`CV4–CV5 PASS`)

Sistem taban ısı yükleri (destekler, radyasyon, optik pencereler): `50K = 2,5 W`, `4K = 95 mW`, `Still = 0,80 mW`, `CP = 15 µW`, `MXC = 2,0 µW`. `9.000` okuma kanalı için `56–82` koaksiyel RF hattı (`SS304 / CuNi / NbTi`, zayıflatıcılar + `4K` kriyo-LNA) eklenince oluşan tam 5-kademeli bütçe (`[Exp125 | exp125.json]`, `{Sayısal-Simülasyon}`):

| Konfigürasyon | Hat Sayısı | LNA Gücü / Hat | `50 K` (`W`) | `4 K` (`W`) | `Still` (`mW`) | `CP` (`µW`) | `MXC` (`µW`) | `1 K` (`mW`) | Durum / Soğutucu |
|---|---|---|---|---|---|---|---|---|---|
| `20 mK` Baz (`NL=163`, ultra-düşük LNA) | `56` | `2,1 mW` | `7,54` | **`0,325`** | `1,14` | `54,5` | **`3,94`** | — | PASS (`< 1,0 W / < 19 µW`, PT410/420) |
| **`20 mK` Kanonik (`NL=160`, standart HEMT)** | **`57`** | **`7,8 mW`** | — | **`0,654`** | — | — | **`3,97`** | — | **PASS (Baz kilitli; `PT415/420`)** |
| `20 mK` Kanonik (`NL=160`, yüksek HEMT) | `57` | `10,5 mW` | — | `0,808` | — | — | `3,97` | — | PASS (`< 1,0 W`) |
| `20 mK` Geniş (`NL=110`, standart HEMT) | `82` | `7,8 mW` | — | **`0,899`** | — | — | **`4,80`** | — | PASS (`< 1,0 W` sınırda) |
| `20 mK` Geniş (`NL=110`, yüksek HEMT) | `82` | `10,5 mW` | — | `1,121` | — | — | `4,80` | — | `> 1,0 W` → **`PT415/PT420`** zorunlu |
| `1 K` Yükseltme (`S6.8=C`, `NL=160`) | `57` | `7,8 mW` | — | `0,654` | — | — | — | **`11,84`** | PASS (`< 100 mW` `1K` pot kapasitesi) |

- **RF Yansıma `SNR = 10` Entegrasyon Süresi (`P_in = −100 dBm/ton`, `Q_l = 1.000`, `1,5 dB` hat kaybı, `\|ΔΓ\| = 0,05`):**
  - `20 mK` (`T_LNA = 1,4 K`): tek nokta **`0,0627 ms`**, 200-noktalı spektral tarama **`12,5 ms ≪ t_eff = 1.445 ms`**.
  - `1,5 K` (`T_LNA = 3,0 K`): tek nokta **`0,179 ms`**, 200-noktalı tarama **`35,9 ms ≪ 1.445 ms`**.

### 3.5 Risk `R8`: Faz-Duyarlı Koiller 6-Vadi Girişim Analizi (`CV6 PASS`, `200.000` MC)

`1 K` singlet–triplet (PSB) okuması için komşu iki `³¹P` donörü arasındaki değiş-tokuş etkileşimi $J(\mathbf{R})$, silisyumun 6 iletim bandı vadisinin (`a_Si = 0,5431 nm`, `k_0 = 9,834 nm⁻¹`) faz girişimi nedeniyle kafes-düzeyinde şiddetli salınım gösterir (`{Literatür}` Koiller 2001). `200.000` Monte Carlo çiftiyle yapılan analiz (`[Exp125 | exp125.json]`, `{Sayısal-Simülasyon}`):

| Ayar Penceresi & Kapı Kazancı `G` | `V1` (Zarf) Başarı `p` | **`V2` (Koiller 6-Vadi) `p`** | `%99` Çift İçin `N_99` | Yorum |
|---|---|---|---|---|
| `W4` (İdeal geniş, `G = 100×`) | `1,0000` | `1,0000` | `1` | Kuramsal üst sınır |
| **`W2` (Gerçekçi `100 MHz – 10 GHz`, `G = 10×`)** | `0,9694` | **`0,9322`** (`λ=1,5 nm: 0,8781`) | **`2`** | `p_crit` üzerinde ancak `1 K` Mod B hızı **`3,40×`** yavaş (`1,372×10⁸ → 4,042×10⁷`/gün) |
| `W1` (Dar `316 MHz – 3,16 GHz`, `G = 3×`) | — | `0,6096` | `5` | Sınırda uygulanabilir |
| Ayarsız (`G = 1×`) | — | `0,3354` | `12` | Başa-baş altında (`< p_crit_cost = 0,5122`, `< p_crit_frac = 0,4812`) |

---

## Bölüm 4: IBIC Tek-İyon Algılama & Soğuk-Ada Ön-Uç Elektroniği (`Exp127` & `src/board/`)

Tek bir `5 keV ³¹P⁺` iyonunun silisyuma girişini `≥ %99` verim ve `< 10⁻³ / 1 ms` yanlış-tetik oranıyla saymak, deterministik implantasyonun (`S2.2` boşluklayıcı kapanış tetiği, `S2.4` FPGA sürücüsü) kalbidir. `Exp127` (`experiments/exp127_detector_frontend_sim/sim127.py`) ve `src/board/detector_frontend.py`, bu zinciri ilk kez gerçek Lindhard fiziği ve ERC-temiz devre düzeyinde doğrulamıştır (`[Exp127 | results/exp127_detector_frontend_sim/exp127.json, src/board/BOARD.md]`, `{Sayısal-Simülasyon}` / `{EDA}`).

### 4.1 Lindhard Elektronik Durdurma Bölüşümü ve Sinyal Yükü

Düşük enerjili ağır iyonlar enerjilerinin büyük bölümünü nükleer çarpışmalara (fonon/hasar) verir; yalnızca Lindhard elektronik kesri $Y_e(E)$ elektron–deşik çifti üretir (`{Analitik}`):

$$N_e(E, T) = \frac{E \cdot Y_e(E)}{\epsilon_{\text{eh}}(T)}, \qquad \epsilon_{\text{eh}}(300\text{ K}) \approx 3,62\text{ eV},\;\; \epsilon_{\text{eh}}(100\text{ K}) \approx 3,72\text{ eV}$$

Tam Lindhard (`³¹P⁺ → Si`) hesabı, `Exp72`'de kullanılan kaba yaklaşımdan **`~%28` daha düşük** elektron verimi ortaya çıkarmıştır:

| İyon Enerjisi (`³¹P⁺ → Si`) | Lindhard Kesri `Y_e(E)` | Ortalama Yük `N_e` (`300 K`) | Ortalama Yük `N_e` (`100 K`) | Şekillendirici Tepe Gerilimi (`100 K`, `C_det=0,5 pF`) |
|---|---|---|---|---|
| **`5 keV` (P91 Baz)** | **`0,2542`** | `351,2 e⁻` | **`341,7 e⁻`** | **`10,917 mV`** (eşik `4,229 mV`, `t_peak=1.218,4 ns`) |
| `10 keV` (Üst Kolon / Opsiyon) | `0,2867` | `792,0 e⁻` | `770,8 e⁻` | **`24,624 mV`** |
| `20 keV` (Kalibrasyon) | `0,3281` | `1.813,0 e⁻` | `1.764,2 e⁻` | **`56,363 mV`** |

### 4.2 Sonlu GBP'li Transfer Fonksiyonu, Parseval `ENC` & Rice Yanlış-Tetik Sınırı

Yük-duyarlı ön-yükseltici (`LTC6268`, $C_f = 0,25\text{ pF}$, $C_{\text{in}} = 0,45\text{ pF}$, $\text{GBP} = 500\text{ MHz}$) ile aktif `CR-RC` şekillendirici (`ADA4817-1`, $\text{GBP} = 1,05\text{ GHz}$, $G_{\text{stage}} = 136$, balistik açık $1/e$ sonrası net tepe kazancı `×50,0`) zincirinin tam Laplace transfer fonksiyonu $H(s)$ üzerinden hem zaman-domeninde darbe yanıtı hem Parseval integraliyle eşdeğer gürültü yükü (`ENC`) hesaplanır (`{Analitik}`):

$$\text{ENC}^2 = \frac{1}{q^2 V_{\text{peak,1e}}^2} \int_0^\infty \left[ S_{v,\text{tot}}(f)\,\|H_v(j2\pi f)\|^2 + S_{i,\text{tot}}(f)\,\|H_i(j2\pi f)\|^2 \right] df$$

- **Laplace ↔ ODE Doğrulaması (`CZ1 PASS`):** `1.111 e⁻` test darbesinde FFT darbe tepesi `35,200 mV` vs `scipy.signal.impulse` ODE `35,201 mV` (**`%0,004` fark**, `t_peak = 224,7 ns`).
- **Rice Yanlış-Tetik Sınırı:** Şekillendirilmiş Gauss gürültüsünün $T_w = 1\text{ ms}$ bekleme penceresinde eşiği aşma olasılığı $P_{\text{false}} \approx 1 - \exp\left(-f_0 T_w e^{-k_{\text{thr}}^2/2}\right)$ ile verilir. `5,0σ` eşiğinde $P_{\text{false}} \approx 0,3\% - 1,1\%$ (`> 10⁻³` ihlal); **`5,5σ`** eşiğinde (`DAC8568` ile yükselen kenar `V_DAC = V_thr − 0,5·V_hys` kalibreli) **`P_false = 2,59×10⁻⁴ / 1 ms < 10⁻³`** sağlanır.

### 4.3 `300 K` Çöküşü → `100 K` Soğuk-Ada Zorunlu Tasarım Kararı (`CZ3–CZ4 FAIL`, `CZ5 PASS`)

`50.000` iyonluk Monte Carlo (Lindhard + Fano + Gauss ENC + eşik taraması) ile `C_det = 0,5 pF` için iki işletim rejiminin karşılaştırması (`[Exp127 | exp127.json]`, `{Sayısal-Simülasyon}`):

| Rejim | Sıcaklık `T` | Şekillendirme `τ_s` | Geri-Besleme `R_f` | `ENC` (`e⁻ rms`) | `η (5 keV)` | `η (10 keV)` | `P_false / 1 ms` | Karar |
|---|---|---|---|---|---|---|---|---|
| RT Karşılaştırma (`--profile rt300k`, `CZ3/4`) | `300 K` | `200 ns` (`100 pF`) | `100 MΩ` | `89,92` | **`0,09722` (FAIL)** | `0,97742` | `8,06×10⁻⁴` | `5 keV` için YETERSİZ |
| RT Yavaşlatılmış | `300 K` | `1,2 µs` (`600 pF`) | `1 GΩ` | `58,10` | `0,64548` (FAIL) | **`0,99978`** | `2,21×10⁻⁴` | Yalnız `10 keV` opsiyonu |
| **Soğuk-Ada (`COLD_100K` Varsayılan, `CZ5`)** | **`100 K`** | **`1,2 µs` (`600 pF`)** | **`1 GΩ`** | **`24,07`** | **`0,99936` (PASS)** | **`1,00000`** | **`2,59×10⁻⁴`** | **`v3.0` KİLİT (`C_det ≤ 1,5 pF` marjı!)** |

- **Kapasitans Dayanımı:** `100 K / 1,2 µs / 1 GΩ` soğuk-ada tasarımında `η ≥ 0,99` penceresi `C_det = 1,5 pF`'ye kadar açık kalır (`η(5 keV, 1,5 pF) = 0,99064`, **`3×` parazitik kapasitans marjı**). `1,2 µs` şekillendirme süresi `1 ms` atış çevriminin `< %0,2`'sidir; yazma hızına sıfır etkisi vardır.

### 4.4 8-Kanallı Devre Kartı Mimarisi (`src/board/detector_frontend.net` & `.cir`)

`src/board/detector_frontend.py` tarafından varsayılan **`COLD_100K`** profiliyle (`--profile rt300k` opsiyonel) üretilen KiCad S-ifadesi netlist (`detector_frontend.net`, `45.487 B`) ve SPICE3 destesi (`detector_frontend.cir`, `4.283 B`), **`204` bileşen, `107` benzersiz net ve `0` ERC hatası** ile doğrulanmıştır (`pytest tests/test_detector_frontend.py` PASS, `{EDA}`):

| Katman | Referans Tasarımcılar (`CH0..CH7`) | Aday Parça & Etiket | Elektrik Değerleri & Tasarım Kuralları |
|---|---|---|---|
| HV Bias Süzgeci | `RBIAS_BULK/CBIAS_BULK`, `RBIAS{ch}/CBIAS{ch}` | `{Pasif-COTS}` | `−30 V` ortak besleme → `100 kΩ / 100 nF` + kanal başı `10 MΩ / 10 nF` RC |
| Piksel Diyot | `D0..D7` | `IBIC_PIXEL_DIODE_C0p5` `{Özel-Üretim}` | Koruma halkalı Si p-i-n piksel (`C_det ≤ 0,5 pF`, parazitik bütçe `C_par ≤ 0,25 pF`) |
| 1. Kat — CSA (`100 K` ada) | `U0A..U7A`, `CF`, `RF` | **`LTC6268`** `{Aday-COTS}` | `GBP=500 MHz, C_in=0,45 pF, ±2,5 V`; `Cf=0,25 pF`, `Rf=1 GΩ` (`100 K`), `IN+ = AGND` |
| 2. Kat — `CR-RC` Şekillendirici | `CS, RS1, U0B..U7B, RG1/2, RS2, CP` | **`ADA4817-1`** `{Aday-COTS}` | `GBP=1,05 GHz`; soğuk baz `CS=CP=600 pF, RS1=RS2=2,00 kΩ` (`τ_s=1,2 µs`); `RG1=100 Ω, RG2=13,5 kΩ` |
| Kanal-Başı Eşik DAC | `UDAC, RDAC, CDAC` | **`DAC8568`** `{Aday-COTS}` | 8-kanallı 16-bit SPI DAC + `1 kΩ / 100 nF` (`f_c=1,59 kHz`) — kanal başı `5,5σ` ayarı |
| Histerezisli Karşılaştırıcı | `U0C..U7C, RHYS1/2, RTERM` | **`TLV3501`** `{Aday-COTS}` | `t_pd=4,5 ns`, `+3,3 V` CMOS; `RHYS1=1 kΩ, RHYS2=1 MΩ` (`3,3 mV` histerezis); `49,9 Ω` seri sonlandırma |
| FPGA & Güç/Toprak | `JFPGA`, `JPWR`, `R_STAR`, `CD*` | `{Pasif-COTS}` | `COUNT_HIT[0:7]` → `src/rtl/blanker_tile.v` (`100 MHz`, `1 ms` watchdog); `±2,5 V / +3,3 V`; `AGND ↔ DGND` (`R_STAR=0 Ω`) |

---

## Bölüm 5: Kuantum Kontrol, `Q16.16` FPGA, `CellISA v4.0`, `auto_recal` & Canlı IBM QPU Kılavuzu

Bu bölüm, `src/machine_control/` **v4.0** yazılım yığınını (**`85/85`** yazılım/FPGA-DSP/IBM-QPU/auto_recal/Dijital-İkiz/ön-uç/RTL `pytest` [`11` dosya] / **`252/252`** toplam `28/28` staged Atom Litografi `pytest` PASS), `20`-komutlu **`CellISA v4.0`** derleyicisini, otonom **`auto_recal.py`** (`4/4 PASS`) denetleyicisini ve gerçek **`156Q` `ibm_marrakesh`** üzerinde canlı doğrulanan sıfır-`qiskit` **`cloud_qpu_bridge.py`** köprüsünü belgeler (`[Exp127–146 | src/machine_control/]`, `{Model}` + `{Canlı-Donanım-IBM-QPU}`).

### 5.1 Yazılım Modül Haritası & Yapılandırma Ön-Ayarları (`v4.0`)

| Modül (`src/machine_control/`) | Sorumluluk | Temel Sınıflar / İşlevler |
|---|---|---|
| `config.py` | Makine yapılandırma ön-ayarları | `MachineConfig.v400_bayesian()`, `v300_baseline()`, `v224_baseline()`, `v224_1k_upgrade()`, `legacy_exp65()` |
| `adaptive_spectroscopy.py` | **`BOED`** 3-aşamalı uyarlamalı spektroskopi (`$0` HW) | `BayesianSpectroscopy` (`41,03 ms`, `RMS=72,67 Hz`, `FNR=%0,20`, `FPR=%0,00`, `Exp132`) |
| `fpga_boed_dsp.py` | **`Q16.16` sabit-nokta `ZCU216` RFSoC FPGA DSP** | `abs(ΔRMS) = 0,0502 Hz`, `2,336 µs/adım`, `%10,49` DSP48E2 (`Exp140/141`; canlı `ibm_marrakesh` `1,6 Hz`) |
| **`cloud_qpu_bridge.py`** | **Sıfır-`qiskit` IBM Quantum Platform 2026 REST + `OpenQASM 3.0`** | `IBMQuantumRESTClient`, `NativeOpenQASM3Transpiler` (`16-dt`, Heron/Eagle), `select_best_linear_chain` (`Exp145`) |
| **`auto_recal.py`** | **Otonom kendini-onaran 4-arıza kapalı-çevrim kontrolörü** | `AutoRecalController` (`S5.5` lazer, `S5` UHV, `S3` `%5` ölü blanker, `³¹P ±350 Hz` kayma — `4/4 PASS`, `Exp145`) |
| `selector.py` | `Exp48` doğal `²⁹Si` çekirdek seçicisi | `AtlasSelector` (bellek köprüsü, taşınabilir repo-kökü) |
| `writer.py` | Sayılmış tek-iyon yerleştirme modeli | `IonWriter` (`1.024` demetçik [`32×32 @ 0,50 mm`], `15 ms/atış`, `5 keV`) |
| `spectroscopy.py` | Klasik hiperince çizgi tarama (`{A_k}`) | `SpectroscopyEngine` (`NL=160 × 56 = 8.960` kanal) |
| `calibrator.py` | Çift-`α` (`α=1 ∧ α=2`) DD kapılı kalibrasyon | `spectral`, `shaped` ve `grape` kalibrasyon modları |
| `pulse_engine.py` | Birinci-ilkeler spin dinamiği & GRAPE/XY8 | `su2_rotation` (Rodrigues), `MultiSpinSimulator`, 9-köşeli L-BFGS-B GRAPE, OU gürültü + `XY8` |
| `programmer.py` | **`CellISA v4.0`** (`20` komut `VALID_OPCODES_ALL`; `17` donmuş `v3.5`) | `CellInstruction`, `CellProgram`, `AtomCellProgrammer`, `MultiCellProgrammer`, `ProgramCertificate` (SHA-256) |
| `factory.py` & `sim.py` | Çok-yuvalı fabrika yürütücüsü & CLI | `Factory`, `Certificate` (7 alan), `python3 -m machine_control.sim --preset v400` |

- **Kanonik Ön-Ayarlar:** **`v400_bayesian()`** (`--preset v400`, `BOED 41,03 ms` + `Q16.16` FPGA + `CellISA v4.0`), `v300_baseline()` / `v224_baseline()`, `v224_1k_upgrade()`, `legacy_exp65()`.

### 5.2 `SU(2)` Rodrigues Darbe Fiziği, 9-Köşeli GRAPE & `XY8` Dinamik Ayrıştırma

- **Birimlik Doğruluğu:** `pulse_engine.py`, her zaman dilimindeki tek-kübit propagatörünü kapalı-form `SU(2)` Rodrigues formülüyle üretir (`\|\|U^\dagger U - I\|\| < 10^{-13}`).
- **9-Köşeli Sağlam GRAPE:** Seçici RF/MW darbeleri, `±400 Hz` frekans kayması × `±%2` genlik hatası oluşturan 9 köşede (`3 × 3` ızgara) eşzamanlı L-BFGS-B optimizasyonuyla sentezlenir (`CORNER_OFFSETS_HZ`, `CORNER_AMP_SCALES`).
- **Ornstein–Uhlenbeck (OU) Gürültü & `XY8` DD (Soyutlama Sınırı Notu):** Yavaş manyetik gürültü altında serbest bozunma (`FID = 0,1145`) `XY8` dinamik ayrıştırmasıyla **`DD = 0,9533`** düzeyine taşınır (**`8,32× – 14,37×`** eşevrelilik kazancı). **Önemli soyutlama ayrımı:** `src/machine_control/pulse_engine.py` içindeki hızlı `CellISA` derleyici adımı (`apply_dd_hold`), `DD_HOLD` aralığını efektif eşevrelilik faz operatörüyle (`0,5·arccos(dd_coherence)`) modeller; tam `32`-boyutlu (`1e + 4n` + `448` banyo seyircisi + seküler `J_ij`) mikroskobik `XY8`-GRAPE Hamiltonyen doğrulaması Bölüm `5.6`'da (`experiments/exp126_atom_cell_programming/`, `Exp126`) ayrı olarak gerçekleştirilmiştir. Kalibratör ayrıca `α=1` ve `α=2` çift-`α` DD kapısını zorunlu kılar.

### 5.3 `CellISA v4.0` `20`-Komut Referansı (`v2.0` + `v3.0` + `v3.5` + `v4.0`)

Kübit adreslemesi: elektron için `'e'` / `0`; sertifikalı `²⁹Si` çekirdek kübitleri için `'n0'..'n7'` / `1..8` (`parse_qubit()`). `VALID_OPCODES` (`17`) geriye dönük `v3.5` uyumluluğu için dondurulmuştur; `VALID_OPCODES_ALL` tüm `20` `v4.0` komutunu sunar.

| Opcode | Sürüm | Zorunlu / İsteğe Bağlı Argümanlar | Fiziksel Derleme Çıktısı (`ScheduleOp` / `M4` QEC / Bulut QPU) |
|---|---|---|---|
| `INIT` | `v2.0` | `state` (varsayılan `\|0...0>`) | Başlatma / optik-RF hazırlık kaydı |
| `RX` | `v2.0` | `target`, `angle` (`rad`) | Seçici MW (`e`) veya RF (`n_k`, `A_k` frekansında) X-döndürme darbesi |
| `RY` | `v2.0` | `target`, `angle` (`rad`) | Seçici MW/RF Y-döndürme darbesi (`π/2` fazlı) |
| `RZ` | `v2.0` | `target`, `angle` (`rad`) | Sıfır-süreli sanal faz kaydırması (`VIRTUAL_RZ`) |
| `CZ` | `v2.0` | `control`, `target` | Hiperince $A_k S_z I_{z,k}$ koşullu faz kapısı (`π` faz birikimi) |
| `CNOT` | `v2.0` | `control`, `target` | Hadamard + `CZ` + Hadamard ayrıştırması |
| `GHZ` | `v2.0` | `qubits` (liste) | Çok-kübitli dolanık GHZ durum hazırlama makrosu |
| `DD_HOLD` | `v2.0` | `duration_us`, `sequence` (`XY8`) | Bekleme aralığına `XY8` dinamik ayrıştırma sekansı gömme |
| `MEASURE` | `v2.0` | `qubits` (isteğe bağlı), `shots` | RF yansıma / tek-atışlı spin okuma örneklemesi (`visibility = 0,99`) |
| `ARRAY_EXEC` | `v2.0` | `program`, `cells` | Derlenmiş programı seçilen sertifikalı hücre dizisinde paralel yürütme |
| `WAFER_MAP_ROUTE` | `v3.0` | `wafer_map`, `topology`, `n_cells` | Çalışan yonga yuvalarını `M4` veri yolu topolojisine yönlendirme (`Exp132`) |
| `BUS_TUNE` | `v3.0` | `cell`, `detuning_mhz`, `g_eff` | Flip-flop saat-geçişi DC kapı ayarı & `3 kΩ NbTiN` rezonatör eşleştirme |
| `BUS_CZ` | `v3.0` | `cell_a`, `cell_b`, `bus_id` | Hücreler arası kavite-aracılı çıplak `CZ` kapısı (`Exp131/132`) |
| `LOGICAL_ENCODE` | `v3.0` | `code`, `data_cells`, `ancilla` | Çok-hücreli mantıksal kodlama (`bitflip3_plus_ancilla`, `p_L = 3,65×10⁻⁴`) |
| `ECHO_CZ` | `v3.5` | `cell_a`, `cell_b`, `echo_seq` | `Exp137 P4` (`XY4-DRAG-Echo-CZ`) `1/f`-yankılı `CZ` (`0,7791 → 0,9818`, `Exp140/141`) |
| `MUX_READOUT` | `v3.5` | `cells`, `n_mux` (`≤ 32`), `twpa` | `S6.5` Purcell-filtreli TWPA çoklamalı okuma (`N_mux* = 32`, `F_RO = %99,61`) |
| `SYNDROME_CYCLE` | `v3.5` | `stabilizers`, `rounds`, `decoder` | Tam yüzey-kodu sendrom döngüsü (`ECHO_CZ` + `MUX_READOUT`, `F_syn = 0,9427`, `T_cyc = 2,620 µs`) |
| **`QRAM_SWAP`** | **`v4.0`** | `transmon_port`, `cell`, `mode` | `Option-Q` `50 Ω ↔ 3 kΩ` süperiletken ↔ `³¹P` `qRAM` takası (`F_SWAP_rt = 0,9858`, `Exp142/145`) |
| **`QLDPC_ROUND`** | **`v4.0`** | `code` (`BB144`), `blocks`, `decoder` | `[[144,12,12]]` Gross Code derinlik-7 sendrom turu + `Option-HPC` `BP-OSD` (`2,32 µs`, `Exp144/145`) |
| **`AUTO_RECAL`** | **`v4.0`** | `subsystem`, `fault_mode`, `tolerance` | `auto_recal.py` 4-arıza kapalı-çevrim otonom yeniden kalibrasyon (`4/4 PASS`, `Exp145`) |

### 5.4 CLI Kullanımı & Sertifika JSONL Şemaları

```bash
# 4.000 yuvalı fabrika + GRAPE ile QFT-3/Bell/GHZ/RepCode3 program sertifikasyonu:
PYTHONPATH=src python3 -m machine_control.sim \
  --slots 4000 --preset v224 --cal-mode spectral \
  --program bell --program-mode grape --program-cells 3 \
  --certs results/exp127_detector_frontend_sim/certs_v224_demo.jsonl \
  --prog-certs results/exp127_detector_frontend_sim/prog_certs_v224_demo.jsonl
```

- **`Certificate` (`certs_*.jsonl`, 7 zorunlu alan):** `register_id`, `slot`, `attempts`, `shots`, `min_spacing_Hz`, `dd_quality_gate` (`bool`), `lines_Hz` (8 çekirdek frekansı `Hz`).
- **`ProgramCertificate` (`prog_certs_*.jsonl`, SHA-256 imzalı):** `program_name`, `register_id`, `pulse_mode`, `n_qubits`, `active_lines_Hz`, `pulse_count`, `total_duration_us`, `nominal_state_fidelity`, `corner_min_fidelity`, `corner_mean_fidelity`, `dd_coherence_gain`, `dd_coherence`, `measurement_counts`, `readout_visibility`, `certified`, `epistemic_tag`, `sha256`.

### 5.5 Canlı Doğrulama Demosu Sonuçları (`results/exp127_detector_frontend_sim/`)

- **Fabrika Sertifikasyonu (`certs_v224_demo.jsonl`):** `4.000` yuvada **`3.517` sertifikalı yazmaç (`%87,92`)**, ortalama `1,98` atış/spektroskopi, **`1,973×10⁸` yazmaç/gün** eşdeğer hız, **`3.517 / 3.517`** eksiksiz 8-çizgili `lines_Hz` kaydı (`{Model}`).
- **Program Sertifikasyonu (`prog_certs_v224_demo.jsonl`, `4/4` `certified=True, sha256_valid=True`):**

| Program (`CellISA`) | Kübit / Darbe | `F_nom` (Nominal) | `F_cmin` (9-Köşe En Kötü) | `XY8` Kazancı | Karşılaştırma Notu |
|---|---|---|---|---|---|
| `bell` | `2q` / `2` darbe | **`0,9940`** | **`0,9982`** | **`14,37×`** | `ALM-000001` (`700,05 µs`) |
| `ghz4` | `4q` / `—` | **`0,9948`** | **`0,9950`** | **`14,37×`** | 4-kübitli dolanıklık sertifikalı |
| `repcode3` | `3q` / `—` | **`0,9987`** | **`0,9927`** | **`14,37×`** | 3-kübitli tekrar kodu |
| `qft3` | `3q` / **`72`** darbe | **`0,9893`** | **`0,8812`** | — | Şekillendirilmiş Gauss'a (`0,0153`) göre **`57×`** kazanç |

### 5.6 Tam 32-Boyutlu (`1e + 4n`) Hamiltonyen GRAPE/XY8 & 16-Hücre Programlanabilirlik (`Exp126` Kilitli)

`Exp126` (`experiments/exp126_atom_cell_programming/`, NVIDIA RTX 2060 SUPER `complex128` tam üniter matris üsteli, `tests/test_exp126.py` `8/8 PASS`, QA `#69` KABUL), Risk `R3`'ü `Exp63`'ün analitik kestiriminden çıkarıp **`1` elektron + `4` aktif `²⁹Si` çekirdeği (`2⁵ = 32` boyut) + tüm seküler `J_ij` + tüm `448` banyo seyircisi** üzerinde doğrudan doğrulamış ve `5/8 PASS, 3/8 FAIL` (`success_rule_met=false`) ön-kayıtlı hükümlerini dürüstçe raporlamıştır (`[Exp126 | results/exp126_atom_cell_programming/exp126.json]`, `{Sayısal-Simülasyon}`).

#### 5.6.1 İki Temel Fiziksel Keşif: DDRF Seyirci Çöküşü (`10–15 kHz` RF Şartı) & `N = 32` Global Optimumu

1. **DDRF Aşırı-İnce Odaklama Seyirci Çöküşü & RF Genlik Payı (`F1 q3`, `min_gap = 6,89 kHz`):** `XY8` elektron π-darbeleriyle taşıyıcısı `±A_k/2` arasında anahtarlanan yalın `GAUSS500` darbesi, modülasyon frekansı $f_{\text{mod}} = N_{\text{dd}}/(2T)$ en yakın seyirci boşluğunu aştığında 448-seyirci örtüşmesini **`0,9992` (`N_dd=0`) → `0,2035` (`N_dd=8`) → `0,000537` (`N_dd=16`) → `1,51×10⁻⁶` (`N_dd=32`)** düzeyine çökertir. Eski `Exp61` `5 kHz` RF sınırı bu sıkıştırmayı açamaz (`F_nom = 0,7716`). Gerçekçi Si:P NMR bobini payında (**`10–15 kHz`**, `B₁ ≈ 1,2–1,8 mT`, Pla vd. *Nature* 2013 `~30 kHz` sınırının altında) 2-aşamalı 32B `XY8`-GRAPE 448-seyirci örtüşmesini **`0,000537 → 0,9919`** (**`~1.846×` kurtarma**) ve 32B nominal sadakati **`0,9986`** (`q0..q3: 0,99862–0,99985`, `max u_err = 3,47×10⁻¹²`) düzeyine taşır.
2. **Risk `R3` Kapanışı (`P126_4 PASS`) & Gerçek `N_total` Tatlı Noktası (`F1`, `f = %1`, `T2e = 1,269 ms`, `T_tot = 2,0 ms`, `ε = 10⁻³`):**

| `N_total` (`N_dd`/kapı) | İdeal `Q` (448 seyirci) | `sp_ovl448` | 32B `α=1, ε=10⁻³` | `Exp63 α=1` | 32B `α=2, ε=10⁻³` | `Exp63 α=2` | 32B `α=2, ε=10⁻²` |
|---:|---:|---:|---:|---:|---:|---:|---:|
| `0` (`0`) | `0,6011` | `0,2096` | `0,4946` | `0,6034` | `0,4996` | `0,6034` | `0,4996` |
| `8` (`2`) | `0,9173` | `0,8502` | `0,7777` | `0,7854` | `0,8865` | `0,8354` | `0,8439` |
| `16` (`4`) | `0,9261` | `0,8608` | `0,8407` | — | `0,9099` | — | `0,8239` |
| **`32` (`8`, OPTİMUM)** | **`0,9907`** | **`0,9889`** | **`0,9260`** | — | **`0,9648`** | — | `0,7790` |
| **`64` (`16`, `R3` ÇAPASI)** | **`0,9901`** | **`0,9858`** | **`0,9206`** *(çapa `0,9209`)* | `0,8851` | **`0,9452`** *(çapa `0,9433`)* | `0,9250` | **`0,6382`** (`<0,80`) |
| `128` (`32`, DDRF DUVARI) | **`0,5437`** | **`0,0972`** | `0,5064` | `0,8827` | `0,5071` | `0,9134` | `0,2878` |

- **Kritik Tasarım Kuralı:** `Exp63` analitik kestiriminin aksine **`N_total = 128` (`f_mod = 32 kHz`) gerçek 32B Hamiltonyende DDRF seyirci duvarına çarparak çöker (`sp_ovl = 0,0972`)**; kilitli çalışma penceresi **`N_total = 32–64`**'tür (`N = 32` global optimum). Dört bolluk finalistinde (`N = 64`): `F0.5` (`0,9298 / 0,9358`), **`F1` (`%51` verim, `0,9209 / 0,9433`, BAZ)**, `F2` (`0,8545 / 0,9195`), `F4.7` (`0,6755 / 0,8955` — doğal Si `α=1`'de `< 0,85`).

#### 5.6.2 `XY8` vs `CPMG` Zorunluluğu (`P126_5 PASS`) & Elektron-Aracılı `CZ`/`CNOT`/`CCZ`

- **Sistematik Aşırı-Dönme Dayanıklılığı (`F1`, `N = 64`, `f = %1`, `α = 2`):** `δθ_sys = 63,25 mrad` (`ε = 10⁻³`) değerinde **`XY8`** `GHZ_X = 0,9767 / GHZ_Y = 0,9756` korurken **`CPMG`** `0,6454 / 0,6512`'ye çöker (**`XY8` üstünlüğü `+0,3245`**); `δθ_sys = 100 mrad`'da üstünlük **`+0,6189`** (`0,9555` vs `0,3366`) olur. Bu nedenle iç-içe RF altında `CPMG` yasaklanmış, **`XY8` zorunlu** kılınmıştır.
- **İki-Kübit & Doğal 3-Cisim Kapılar (`F1`):** 6 çiftin tamamında `CNOT` ideal `0,98730–0,99646` (ort. `0,99207`), gürültülü (`f=%1, α=2, ε=10⁻³`) `CZ` ortalaması **`0,94442`** (`0,9314–0,9484`); yalnız `q3` (`6,89 kHz`) içeren `CZ(2,3)` ideal `0,98279` ve elektron sızıntısı `3,61×10⁻³` nedeniyle `P126_2` dürüstçe FAIL aldı (`CZ(0,1) = 0,99567`, sızıntı `8,3×10⁻⁴`). Elektron-merkezli doğal 3-cisim **`CCZ(0,1,2)`** kapısı `18,00 ms` toplam sürede (`9,0 ms` `e_sup`, `36` RF darbesi, `288` `XY8` π darbesi) ideal **`F_proc = 0,93379`** (`leak = 6,7×10⁻³`) verir.

#### 5.6.3 16 Heterojen Silisyum Hücresinde 5 Mantıksal Program (`P126_6, P126_7, P126_8 PASS`)

`f = %1` epitaksiyel banyodan bağımsız çekilen 16 tekil sertifikalı hücrede (`16/16` benzersiz `{A_k}`, `A_k CV = %55,6`, tümünde `Lie = 1023/1023`, `Vandermonde = 8/8 & 4/4`, `min_gap = 6,89–46,66 kHz`, `max \|J\| = 6,65 Hz ≤ 100 Hz`, **`D0(17,5 s) ≤ 7,76×10⁻⁹ ≤ 10⁻⁵`**) hücre-özgü derlenmiş 32B `XY8`-GRAPE yürütmesi (`f=%1, α=2, ε=10⁻³`):

| Mantıksal Program | Süre (`e_sup` / DD) | İdeal 32B Ort. | Statik Köşe Ort. (`±400 Hz × ±%2`) | Gürültülü `α=2, ε=10⁻³` Ort. | En Kötü – En İyi (16 Hücre) | Paralel `16×` Hızlanma (`1 µm`) |
|---|---:|---:|---:|---:|---:|---:|
| **`Bell`** | `4,50 ms` (`2,0 ms / 64`) | `0,9950` | `0,9563` | **`0,9501`** *(α=1: `0,9282`)* | `0,9416 – 0,9538` | `4,50 ms` vs `72,0 ms` (`16×`) |
| **`GHZ-4`** | `2,00 ms` (`2,0 ms / 64`) | `0,9867` | `0,8480` | **`0,9401`** *(α=1: `0,9155`)* | `0,9263 – 0,9479` | `2,00 ms` vs `32,0 ms` (`16×`) |
| **`Grover-2`** | `13,00 ms` (`4,0 ms / 128`) | `0,9724` | `0,8985` | **`0,8896`** *(P(\|11⟩): **`0,9237`**)* | `0,8479 – 0,9135` *(P11 min `0,9055`)* | `13,0 ms` vs `208,0 ms` (`16×`) |
| **`BitFlip-3` QEC** | `17,50 ms` (`8,0 ms / 256`) | `0,9710` | `0,9164` | **`0,8878`** *(kodsuz `0,0000`)* | `0,8416 – 0,9046` | `17,5 ms` vs `280,0 ms` (`16×`) |
| **`QFT-3`** | `14,50 ms` (`6,0 ms / 192`) | `0,9626` | `0,8689` | **`0,8377`** *(medyan `0,8445`)* | `0,7500 – 0,8644` | `14,5 ms` vs `232,0 ms` (`16×`) |

- **Hücreler Arası Yalıtım:** `1 µm` adımda maks dipol bağı **`9,50×10⁻⁹ Hz < 10⁻⁶ Hz`** (`2 µm: 1,19×10⁻⁹ Hz`, `5 µm: 7,60×10⁻¹¹ Hz`); ortak `500 µs / XY8` saat çatısı + yerel FDMA/AWG taşıyıcılarıyla `16×` paralel yürütme doğrulanmıştır.
- **Dürüst `3/8 FAIL` Özeti:** `P126_1` (`X q2 nom=0,99423 < 0,995`, `cX q3` 6,89 kHz tam-fazlı köşe `0,97264 < 0,985`, `X q1` tek seyirci `0,96194`), `P126_2` (`CZ(2,3)` ideal `0,98279 < 0,985`, maks elektron sızıntısı `3,61×10⁻³ > 10⁻³`) ve `P126_3` (`F1 α=2` `n_traj=512` MC sonlu-örnek sapması `W=0,3087`, `err=0,0592 > 0,05`; `7/8` hücre PASS). Yeniden kullanım API modülleri: `experiments/exp126_atom_cell_programming/{hamiltonian126,grape_dd126,programs126}.py`.

---

## Bölüm 6: Parametrik CAD v6.0 Montaj, Kütle Bütçesi & `40/40` Tolerans Rehberi

Tüm mekanik tasarım tek bir parametrik kaynaktan (`research/atom_lithography_machine/cad/params.py`) otomatik olarak OpenSCAD (`.scad`), su-geçirmez ikili `.stl` ve 10 teknik çizime (`2400×1600` `.png` + `.svg`, `ALM-600-*`) + `00_v6_overview_dashboard.png` kapak panosuna derlenir (`[CAD v6.0 | research/atom_lithography_machine/cad/cad_verification.json]`, `tests/test_cad.py` `30/30 PASS`, `{EDA}`).

### 6.1 Ana Montaj Özeti (`6.0-exp142-exp143-option-qhpc-locked`, `ISO 2768-mK`)

- **Katı Parça Sayısı:** **`199`** (`7` alt-sistem; `v5.0`'dan `+10` parça: `Option-Q` `+5` [`S1.6` Multi `+2`, `S9.1` qRAM/fiber `+3`] + `Option-HPC` `+5` [`S9.HPC` `4U` 2-düğüm `100G` RDMA]).
- **Toplam Kütle & Hacim:** **`1.108,137 kg`** (`1.034,937` Base + `9,200` `Option-Q` + `64,000` `Option-HPC`; `BOM v6.0` ile **`0,000 kg`** fark!), `591,371 L` (birleşik STL: **`39.536` üçgen**, **`591,200 L`**, `25,723 m²` yüzey, **`0` açık kenar, `0` non-manifold kenar**).
- **Kütle Merkezi (`CoM`):** `(189,67; −8,35; 452,68) mm`; dış zarf `3.062,6 × 937,3 × 1.400 mm`.
- **Çakışma & Boşluk Denetimi:** **`0 / 19.701` katı çakışma** (`113` eşleşmiş temas) ve **`40 / 40` kritik boşluk PASS** (`32` `v5.0` boşluğu + `8` yeni `v6.0` boşluğu).

### 6.2 Alt-Sistem Kütle, STL & Teknik Çizim Envanteri (`CAD v6.0`)

| Kod | Alt-Sistem (`research/atom_lithography_machine/cad/`) | Çizim No | Parça | Kütle (`kg`) | STL Üçgen | STL Hacim (`L`) | Su-Geçirmez |
|---|---|---|---:|---:|---:|---:|---|
| `S1` | `parts/s1_ion_source_column.scad` (`Exp124` + **`S1.6` Multi**) | `ALM-600-S1` (`01_s1_*.png/.svg`) | **`13`** | **`30,777`** | **`3.672`** | **`4,531`** | PASS |
| `S2` | `parts/s2_mems_write_head.scad` (`Arch-B` + MEMS) | `ALM-600-S2` (`02_s2_*.png/.svg`) | `9` | `1,832` | `2.496` | `0,234` | PASS |
| `S3` | `parts/s3_ibic_detector_assembly.scad` (`100 K` IBIC) | `ALM-600-S3` (`03_s3_*.png/.svg`) | `7` | `0,153` | `636` | `0,041` | PASS |
| `S4` | `parts/s4_piezo_stage_interferometry.scad` (Granit + Piezo) | `ALM-600-S4` (`04_s4_*.png/.svg`) | `18` | `302,367` | `2.400` | `110,362` | PASS |
| `S5` | `parts/s5_uhv_chamber_loadlock.scad` (UHV + `S5.5` + `S5.6` MBE) | `ALM-600-S5` (`05_s5_*.png/.svg`) | `29` | `193,941` | `4.732` | `31,772` | PASS |
| `S6` | `parts/s6_cryo_dr_magnet_readout.scad` (DR + MUX + **`S9.1` qRAM**) | `ALM-600-S6` (`06_s6_*.png/.svg`) | **`105`** | **`285,320`** | **`25.204`** | **`59,423`** | PASS |
| `S7` | `parts/s7_electronics_rack_interconnect.scad` (Raf + **`S9.HPC` RDMA**) | `ALM-600-S7` (`07_s7_*.png/.svg`) | **`18`** | **`293,747`** | **`396`** | **`384,838`** | PASS |
| **Ana** | `atom_litho_machine.scad` (`08_assembly`, `09_cutaway`, `10_exploded`, `preview_machine.png`) | `ALM-600-00` | **`199`** | **`1.108,137`** | **`39.536`** | **`591,200`** | **PASS** |

### 6.3 `40 / 40` Kritik Boşluk (Clearance) — `v6.0` Ek 8 Boşluğu (`#33–#40`)

*(İlk `32/32` `v5.0` kritik boşluğu birebir korunup PASS'tır; aşağıda `CAD v6.0` ile eklenen 8 yeni boşluk verilmiştir.)*

| # | Yeni `v6.0` Kritik Arayüz Boşluğu (`cad_verification.json`) | Tasarım Değeri (`mm`) | Alt Sınır (`mm`) | Durum |
|---|---|---:|---:|---|
| 33 | `Exp142 S1.6` Multi kartuş ↔ duoplazmatron (`Y`) | **`27,00`** | `20,00` | PASS |
| 34 | `Exp142 S1.6` Multi kartuş ↔ `−Y PH₃` manifoldu (`Y`) | **`136,00`** | `100,00` | PASS |
| 35 | `Exp142 S9.1` `qRAM` köprüsü ↔ `S6.5` TWPA (`Z`) | **`8,50`** | `5,00` | PASS |
| 36 | `Exp142 S9.1` OVC portu ↔ `PT420` valf sehpası (`X`) | **`144,80`** | `100,00` | PASS |
| 37 | `Exp142 S9.1` fiber demeti ↔ `4K/50K` kalkanları | **`2,00`** | `1,50` | PASS |
| 38 | `Exp143 S9.HPC` sunucu rafı ↔ `S7` servis koridoru (`X`) | **`60,00`** | `40,00` | PASS |
| 39 | `Exp143 S9.HPC` düğüm-1 ↔ düğüm-2 hava payı (`Z`) | **`5,00`** | `3,00` | PASS |
| 40 | `Exp143 S9.HPC` RoCEv2 anahtar ↔ düğüm-2 (`Z`) | **`5,00`** | `3,00` | PASS |

---

## Bölüm 7: Modüler BOM v6.0 (`174` Parça), `9-RFQ` Stratejisi, `Exp128 v6.0` MC & `qLDPC` Ekonomisi

Tüm maliyet hesapları değişmez `BOM.csv` (`$2.531.244`, SHA-256 değişmez) ile `$0,00` köprü hatasıyla ve `CAD v6.0` ile `0,000 kg` kütle eşitliğiyle bağlanan **`BOM_DETAILED.csv v6.0`** (`174` parça = `167` `M3 Base` + `4` `Option-Q` + `3` `Option-HPC`, `tests/test_bom_detailed.py` `7/7 PASS`), `Exp128 v6.0` (`6/6 PASS`) ve `Exp144/146` `qLDPC` ekonomisine dayanır (`no_supplier_quotes=true`).

### 7.1 Modüler `v6.0` Yapılandırma & `9-RFQ` Paketleri (`%77,7` Nom / `%92,6` MC Varyansı)

| Paket / Yapılandırma | Parça | Düşük (`USD`) | Nominal (`USD`) | Yüksek (`USD`) | `M3 Full` Payı / Kütle |
|---|---:|---:|---:|---:|---:|
| `RFQ-01..06` (`S1, S2, S4, S6.3, S6.6, S6.8/6.1`) | `58` | `$1.644.000` | `$2.950.900` | `$5.495.700` | `%53,19` |
| `RFQ-07` (`v4.0` `S5.5` + `S6.9` + `S6.10` net) | `12` | `$187.000` | `$334.000` | `$621.000` | `%6,02` |
| `RFQ-08` (`v5.0` `S5.6` MBE + `S6.5/S6.11` MUX) | `8` | `$523.400` | `$724.200` | `$1.070.200` | `%13,05` |
| **`RFQ-09` (`v6.0` `Option-Q $168k` + `Option-HPC $132k`)** | **`7`** | **`$216.000`** | **`$300.000`** | **`$423.000`** | **`%5,41` (`+73,20 kg`)** |
| **`9-RFQ` Toplamı (`CU4 PASS`)** | **`85`** | **`$2.570.400`** | **`$4.309.100`** | **`$7.609.900`** | **`%77,67` (`%92,61` MC varyansı)** |
| `Non-RFQ` (COTS / UHV / Raf / Sarf / `$0` SW) | `89` | `$685.000` | `$1.238.700` | `$2.339.000` | `%22,33` |
| **`M1 Base` Prototip *(korundu)*** | — | `$1.454.996` | **`$2.466.120`** | `$4.400.788` | `M3 Base`'in `%47,0`'ı |
| **`M3 v5.0 Base` *(korundu, `256`-hücre pilot `$4,790M`)*** | `167` | `$3.039.400` | **`$5.247.800`** | `$9.525.900` | `1.034,94 kg` (`P>100M = %4,37`) |
| **`M3 v6.0 Full` (`+Option-Q` `$5,416M` / `+Option-HPC` `$5,380M`)** | **`174`** | **`$3.255.400`** | **`$5.547.800`** | **`$9.948.900`** | **`1.108,14 kg` (`P>100M = %4,92`)** |

### 7.2 `Exp128 v6.0` 100k MC, EVPI & `Exp144/146` `qLDPC` `$63.827/L_sys` Devrimi

- **`Exp128 v6.0` 100k MC (`CU1–CU6 6/6 PASS`):** `M3 Full` BOM `P50 = $6,46M` (`P95 = $12,98M`); Program `P50 = $36,25M ≤ $50M`, `P95 = $99,48M`, **`P(>$100M) = %4,92 < %5`** (`M3 Base: %4,37`; dürüst not: `FOAK` 5y TCO `%6,90`). Tornado: `#1 S6.6 %70,0`, `#2 S2 %6,0`, `#3 S6.8 %5,3`, `#4 v5.0 %3,3`. EVPI (`20 mK` vs `1 K`): `N=1`'de `$0`, `N_be = 6,02`.
- **`Exp144/146` `100L` Sistem Maliyeti Sıkıştırması (`v5 D2 → v6 D3 → v6 qLDPC`):** `v5 D2 SC` (`679` kriyo, `$14.939.541/L_sys`) → `v6 D3 GRAPE SC` (`100` kriyo, `$2.759.442/L_sys`, `5,4×` ↓) → **`v6 [[144,12,12]] qLDPC 108L` (`1` kriyostat, `$63.827/L_sys` [`234,06×` ↓!], `W3` silikon fab `$0,0085/L_fab`)**!

---

## Bölüm 8: Kurulum, Devreye Alma, Kalibrasyon SOP & EHS Güvenlik Protokolleri

Ayrıntılı `M1` yapım planı ve `10` alt-aşamalık iş kırılımı [M1_PROTOTYPE_BLUEPRINT.md](M1_PROTOTYPE_BLUEPRINT.md) içindedir; aşağıda saha işletmesi için zorunlu **Faz A–G kalibrasyon sırası**, **EHS güvenlik kilitleri** ve **`G1–G8` Go/No-Go kapıları** özetlenmiştir.

### 8.1 Devreye Alma & Kalibrasyon Standart İşletme Prosedürü (SOP)

1. **Faz A — Saha, Granit & UHV Ön-Hazırlık:** `S4` granit sönümleme masası tesviyesi (`≤ 5 µm/m`), `S5` UHV odası (`34,86 L`) `150 °C` fırınlama ve `< 1×10⁻⁹ mbar` temel vakum + `He` kaçak testi (`< 1×10⁻¹⁰ mbar·L/s`).
2. **Faz B — Kriyostat & Mıknatıs Enerjilendirme:** `S6.8` `20 mK` DR soğutma (`4K` yük `≤ 0,654 W`, `MXC ≤ 4,8 µW`); `S6.3` `8`-bobin `NbTi` basamaklı akım yükleme (`0 → 1,500000 T`); Hall/NMR probuyla `±17,81 ppm` homojenlik ve `z_loc = −155 mm` kalkan içinde `≤ 22,3 µT` doğrulaması.
3. **Faz C — `100 K` Soğuk-Ada IBIC Kalibrasyonu:** `S3` soğuk adayı `100 K`'ye indirme; `55Fe` / `α` veya darbe-üreteci enjeksiyonuyla `ENC ≤ 25 e⁻ rms`, `τ_s = 1,2 µs`, kanal başı `DAC8568` `5,5σ` eşik kilidi ve `P_false < 10⁻³ / 1 ms` testi.
4. **Faz D — `10 → 5 keV` İyon Kolonu & Wien/HDA Ayarı:** Önce `Ar⁺`/`Ne⁺` soy gaz ile `S1.1` ateşleme, `S1.2` Wien `0,45 T` kütle taraması (`R_m ≥ 100`), `S1.5` `HDA-HiRes` geçiş eğrisi (`ΔE_FWHM ≤ 0,50 eV`), ardından `PH₃` ile `³¹P⁺` / `³²PH⁺` (`0,785 mm`) ayrıştırma kilidi.
5. **Faz E — `Arch-B` Odaklama & Tek-İyon Sayma Kapalı Çevrimi:** Bıçak-kenarı (`knife-edge`) taramasıyla `σ_spot ≤ 1,6 nm` doğrulaması; `S3` `COUNT_HIT[0:7]` → `FPGA` `blanker_tile.v` (`100 MHz`) kapalı-çevrim tek-iyon kesme gecikmesi (`< 100 ns`) ve `1 ms` watchdog testi.
6. **Faz F — RF Yansıma Spektroskopisi & `CellISA` Doğrulaması:** `56` hat üzerinden `NbTiN` rezonatör taraması (`SNR = 10 @ ≤ 0,18 ms`); `AtlasSelector` + çift-`α` DD kapısıyla ilk sertifikalı yazmaç JSONL (`Certificate`) ve `bell/ghz4/repcode3/qft3` `ProgramCertificate` üretimi.

### 8.2 Çevre, İş Sağlığı ve Güvenliği (EHS) Zorunlu Kilit Matrisi

| Tehlike Sınıfı | Kaynak Alt-Sistem | Risk Sınırı | Zorunlu Mühendislik Kilidi & KKD |
|---|---|---|---|
| **Toksik & Piroforik Gaz (`PH₃`)** | `S1.1` Duoplasmatron | `TLV-TWA = 0,3 ppm`, `IDLH = 50 ppm` | Çift-cidarlı vakum-izlemeli gaz kabini, nokta-kullanım kuru yıkayıcı (scrubber), elektrokimyasal `0,1 ppm` alarm + otomatik kesme vanası (`NC`) |
| **Yüksek Gerilim (HV)** | `S1.1 (+5 kV)`, `S1.2–S2.3 (−5 kV)`, `S3 (−30 V)` | Ark & elektrik çarpması | Kapak açma mikro-anahtarı kilidi, `100 MΩ` boşaltma dirençleri, topraklama çubuğu, HV göstergeleri |
| **Yüksek Manyetik Alan & Quench** | `S6.3` `1,50 T` `NbTi` Mıknatıs (`18,94 kJ`) | `5 G` kalp pili sınırı, mermi etkisi, `He` buharlaşması | `5 G` zemin işaretlemesi, ferromanyetik alet yasağı, pasif `1,563 Ω / 400 V` dump direnci, çatıya bağlı quench tahliye hattı |
| **Kriyojenik (`LHe / LN₂ / 20 mK`)** | `S6.8` DR, `S6.1` `PT420`, `S3` `100 K` ada | `O₂` eksikliği (`< %19,5`), kriyo yanık, aşırı basınç | Oda `O₂` monitörü + sesli alarm, çift basınç tahliye vanası (`PRV`) + patlama diski, kriyo eldiven/yüz siperi |
| **Lazer & Optik (`He-Ne`)** | `S4.3` 3-Eksen İnterferometre | Göz hasarı (`Class 2 / 3R`) | Kapalı ışın boruları, lazer emniyet gözlüğü, kapı uyarı lambası |
| **ESD & Vakum Yoğuşma** | `S2` MEMS, `S3` `LTC6268` soğuk-ada | Kapı oksit delinmesi, `100 K` buzlanma | `ANSI/ESD S20.20` bileklik/zemin; `S3` soğutma yalnızca `P < 10⁻⁶ mbar` vakum kilidi aktifken açılır |

### 8.3 `G1–G8` Go/No-Go Doğrulama Kapıları & Açık Mühendislik Borçları

| Kapı | Konu | Geçiş Kriteri (`M1 → M3/M4`) | Şimdiki Statü (`v6.0`) |
|---|---|---|---|
| `G1` | `9-RFQ` Fiyat & `S6.9` `PT420` | `9` paketten teklif (`%92,6` MC var); `CFG4` `σ_stage ≤ 0,25 nm` (`0,102 nm`) | `{Sayısal-Simülasyon}` PASS (`Exp133`); tedarikçi/lab açık |
| `G2` | `S1` İyon Kolonu & `HDA-HiRes` | `10 → 5 keV`, `ΔE ≤ 0,50 eV`, `R_m ≥ 100`, `σ_spot ≤ 1,6 nm` | `{Sayısal-Simülasyon}` PASS (`Exp124`); lab açık |
| `G3` | `S3` `100 K` Soğuk-Ada IBIC | `ENC ≤ 25 e⁻`, `η(5 keV) ≥ 0,99`, `P_false < 10⁻³ / 1 ms` | `{Sayısal-Simülasyon}` PASS (`Exp127`); PCB/lab açık |
| `G4` | `S5.5` `1530,1 K` + `S5.6` MBE & `S6.3` | `1530,1 K` `%99,99` temizlik (`σ_anneal = 0,430 nm`), Rota C `S_ε ≤ 0,40`; `1,50 T ± 20 ppm`, `≤ 50 µT` | `{Sayısal-Simülasyon}` PASS (`Exp125, Exp130, Exp139`); fab/lab açık |
| `G5` | `S6.8/6.5` Termal, `N_mux*` & `Q16.16` | `4K ≤ 1,0 W`, `MXC ≤ 19 µW`, `N_mux* = 32` (`F_RO = %99,61`), `Q16.16` `2,336 µs` | **`{Canlı-Donanım-IBM-QPU}` (`Q16.16` `1,6 Hz`)** + `{Model}` PASS; silikon lab açık |
| `G6` | `S2` MEMS, `CAD v6.0` & **`G6b` `ENDOR` (`R1`)** | `WD = 0,25 mm`, `0/19.701` CAD çakışma (`40/40`); **`G6b` `p_work(f*=%1,5) ≥ %50`** | `{EDA}` PASS (`CAD v6.0`); **`R1` (`Exp129/136`) lab kapısı AÇIK** |
| `G7` | `CellISA v4.0`, `D3` GRAPE & `qLDPC` | `D3` `p_2q ≤ %0,45` (`%0,337–0,395`), `[[144,12,12]]` `108L = 1` kriyo, `auto_recal` `4/4` | **`{Canlı-Donanım-IBM-QPU}` (`ibm_marrakesh` `dc1tdo2nj2vs73dfrfl0`)** + `{Model}` PASS |
| `G8` | `M2/M3` SKY130 Anten & Bütçe Onayı | `Exp123` `10` anten ihlali `→ 0` (`M2+`); `Exp128 v6.0` + `9-RFQ` | `M1` FPGA ile yürür (`R5` erteli); `M3 Base %4,37` / `M3 Full P50=$36,25M, P(>100M)=%4,92` |

**Açık Teknik Borçlar (Şeffaf Envanter, `v6.0`):** (1) `M1` **`G6b` `ENDOR` Risk `R1` ölçümü** (`Exp136` `R331 %21,1` & all-electron DFT); (2) `src/board/` 4-katmanlı KiCad PCB yerleşimi (`C_par ≤ 0,25 pF`) & `ngspice`; (3) `RFQ-01..09` gerçek tedarikçi fiyat/termin toplama (`no_supplier_quotes=true`) ve `W2/W3` `30 nm` SOI tedarik doğrulaması; (4) `Q_r = 10⁶` `NbTiN` + `S_ε ≤ 0,25 µeV/√Hz` (`D3` GRAPE) ve `[[144,12,12]]` `qLDPC` fiziksel testi + `Exp142` `¹²¹Sb` gerinim/derinlik sınırı (`OQ5/6 FAIL`); (5) `M2/M3` aşamasında `Exp123` `10` SKY130 anten ihlalinin kapanması (`R5` erteli); (6) `M1 Base` silikon laboratuvar ölçümleri (`no_lab_measurement=true` kapanışı — yazılım/QEC/BOED `ibm_marrakesh` üzerinde canlı doğrulanmıştır).

---

## Bölüm 9: `v4.0` Yükseltme Paketi (`Exp129`–`Exp135`): `VOKL-6`, Flaş Tavlama, `M4` cQED, `BOED`, `PT420` & Birleşik Dijital İkiz

Bu bölüm, tarihsel `v4.0` dalgasında üretilen ve her biri bağımsız `pytest` + `@verifier` QA onayı alan 7 birinci-ilkeler deneyini özetler (`tests/test_exp129..135.py`; `v4.0` dönem paketi `142/142 PASS`, güncel `v6.0` tam paketi Bölüm 11'de **`252/252 PASS`** [`28/28` dosya]; tümü `no_lab_measurement=true`).

### 9.1 `Exp129` (`H147`, Risk `R1`) — `VOKL-6` 6-Vadi Merkez-Hücre Modeli (`3/7 PASS, 4/7 FAIL`, QA `#130`)
- **Fizik Çekirdeği:** `216×216` 6-vadi merkez-hücre Kohn–Luttinger modeli (`0` `²⁹Si` uyumu): çıplak EMT `E_EMT = −31,262 meV` (Faulkner `−31,27`, `%0,03`); Morton–Preston `η_P/η_Si = 1,4178` tüm 4 `³¹P` değişmezini (`A1 = −45,5900`, `ΔT2 = 11,7000`, `ΔE = 13,0100 meV`, `A_P(0) = 117,530 MHz`) `< 10⁻¹⁰` (`~10⁻¹¹` mertebesi, maks `7,36×10⁻¹¹`) hassasiyetle tutturur (`a_⊥ / a_∥ = 1,748 / 0,959 nm`; `145`-PW `C_g(0,0,2) = 8,82×10⁻¹⁵`).
- **Dürüst `CE3,4,6,7 FAIL` & Risk `R1` Sonucu:** Out-of-sample ENDOR'da boyuna büzülme `[110]` zikzak zincirini düzeltemez (**`R331 = 0,1034`, `%64,73` hata**, `logRMS = 0,7445`; all-electron/Si `3d` DFT gerekir). Güçlü `|A| ≥ 10 kHz` site sayısı `18.784 → 6.091 / 9.464` düşer; Mod B (`N=400`) `F0.5 / F1 / F2` çalışma verimi `KL_legacy (%26,75 / %50,50 / %67,00)` değerinden gerçek Hale–Mieher `5,962 MHz` ölçeğinde **`VOKL6_HM5962_ext (%12,00 / %33,25 / %54,50)`**, eski `2,981 MHz` ölçeğinde **`VOKL6_norm_ext (%1,00 / %4,75 / %11,75)`** düzeyine iner; `min_gap < 6,893 kHz` (`Exp126` DDRF eşiği) fraksiyonu **`%57,9–%73,7`** olur. **Risk `R1` kapanmamıştır** → `M1` `G6b` deneysel `ENDOR` kapısı zorunludur.

### 9.2 `Exp130` (`H148`, Risk `R6` Model-Kapalı) — `S5.5` `808 nm / 1,0 ms` Flaş Tavlama (`6/6 PASS`, QA `#115`)
- **Difüzyon & Aktivasyon:** `Exp108` çapası (`600 °C/10 dk`: `%93,2` yüzey yığılması; `800 °C/10 dk`: `%52,7` vakum kaçışı; kütle hatası `6,33×10⁻¹⁵`). Fırın ve RTA (`1000 °C/10 s`: `σ = 4,97 nm`, `%21,2` kayıp) yasaklandı. Ergimesiz ms-flaş penceresi: `t_pulse ∈ [0,077, 12,92] ms × T_peak ∈ [1223,6, 1543,6] K`.
- **Kilitli `S5.5` (`$95k` `RFQ-07A`):** İn-line RT load-lock **`808 nm / 1,0 ms / 1440,3 K` (`F = 41,15 J/cm² ± %5`)**, `+Y` CF63 `Ø44 mm` AR safir (`T_AR = %98`, `9,47×` LIDT), `10 µs` çift-renkli pirometre, `MXC < 1 K` + UHV perde kilidi → **`f_act = %99,98`**, **`σ_anneal = 0,328 nm ≤ 0,50 nm`**, yüzey+vakum kaybı **`%0,022`**, `σ_iso = 0,0314 nm`, arka yüz `592,9 K`, `0,00 dk / 0 J` kriyo kayıp (`16×16 mm` kriyo-içi yedek `3,18 dk`).

### 9.3 `Exp131` (`H149`, `M4` cQED & 2B Perkolasyon) — `S6.10` `3 kΩ NbTiN` (`4/7 PASS, 3/7 FAIL`, QA `#124`)
- **Flip-Flop & cQED:** `4×4` Tosi flip-flop (`N=2.000`): kapaksız `Δz_cap = 0` çöker (`%24,15`); **`Δz_cap* = 8,0 ± 1,0 nm`** `²⁸Si` kapağı + yerel DC ayarı **`p_ff = %95,20`**, `C_med = 2.800,1`, `g_eff = 0,620 MHz`. Tam `12×12` Lindblad (`144×144` CUDA `matrix_exp`, `20 mK`, `60` çift): `50 Ω` CPW **`F_Bell = 0,7908`** (`2,78 µs`) çöker; **`3 kΩ NbTiN`** (`L_res = 300 µm`, **`B_M4 = 0,1785 T`** [`%40,5` pay], `P_node = 10 µm`, `968` DC kapı `4K SKY130` çapraz-çubuk, `$245k` `RFQ-07C`) **`F_Bell = 0,9655`** (`0,359 µs`, `M4 Best-of-6`; seçimsiz `0,9386`). **Dürüst `CM3,4 FAIL`:** `≥ 0,99` için **`S_ε ≤ 0,25–0,35 µeV/√Hz`** (`0,9907–0,9918`) veya `1/f` yankısı şarttır (adyabatik `CZ`: `0,9982` gürültüsüz, `0,7768 @ S_ε=1,0`, `0,9392 @ 0,25`).
- **2B Perkolasyon (`N_mc = 2.000`):** 2B Kare örgü Heavy-Hex'e göre (`CM6 FAIL` @ `N=4`) **`−%40` aday tasarrufu** sağlar (`L=21 N=3: %100`; `L=11` FT `≤%5` ölü: `KL N_cand*=6` `%99,40` [Binom `%99,24`]).

### 9.4 `Exp132` (`H150`) — `BOED` Uyarlamalı Spektroskopi & `CellISA v3.0` (`6/6 PASS`, QA `#121`)
- **`BOED` (`src/machine_control/adaptive_spectroscopy.py`, `--preset v400`, `$0` ek HW):** `N=2.000` Mod B MC'de spektroskopi `1.000 ms →` **`41,03 ms`** (medyan `23,04 ms`, **`24,37×` ham hızlanma**; boş `0,73 ms`, sıkışık `14,58 ms`, çalışan `74,49 ms`), **`RMS = 72,67 Hz`** (`CRLB = 58,19 Hz`), **`FNR = %0,20`**, **`FPR = %0,00`**. Fabrika yazma tavanına ulaşır: **`1,503×10⁹/gün` (`7,61×` @ `15 ms`) / `2,254×10⁹/gün` (`11,42×` @ `10 ms`)**.
- **`CellISA v3.0` (`14` komut):** `+ WAFER_MAP_ROUTE`, `BUS_TUNE`, `BUS_CZ`, `LOGICAL_ENCODE`. `4×4` yönlendirme `%97,0`; örnek `4×4` Kraus: **`min_bus_cz = 0,988923`**, **`F_joint = 0,983448`**, `bitflip3_plus_ancilla` **`p_L = 3,65×10⁻⁴` (`30,3×` bastırma)**, SHA-256 doğrulamalı.

### 9.5 `Exp133` (`H151`) — `S6.9` `PT420` Titreşim/FEM/Termal Ayrıştırma (`8/8 PASS`, QA `#118`)
- `40`-elemanlı üst-kolon FEM `f₁ = 118,178 Hz` (Parseval `%0,086`). Rijit `PT420` (`CFG1`) **`σ_stage = 2.051,97 nm`** ile çöker (`25 dB` FF `CFG5`: `145,59 nm`; yalnız mekanik `CFG2`: `1,006–2,362 nm`). Kilitli **`S6.9` `CFG4`** (`VC-E`, `$68k` `RFQ-07B`: `500 mm` uzak valf + `600 mm` He + `2.000 N/m` körük + `4×` OFHC Cu örgü `52,7 N/m, ΔT = 3,7 mK` + `43,57 Hz` PID [`PM = 55,23°, GM = 8,69 dB, ||S||_∞ = 1,676`] + `25 dB` FF + `Zerodur/Invar-36 @ 20 mK`) → **`σ_stage = 0,1024 nm`**, **`σ_pointing = 0,1473 nm`**, **`σ_thermal = 0,0283 nm`** (çıplak `316LN` `1,935 nm` RED).

### 9.6 `Exp135` (`H153`) — 8-Katmanlı Birleşik `v4.0` Dijital İkiz (`7/7 DT PASS`, QA `#137`)
- `11/11` deney JSON dosyası SHA-256 ile birbirine bağlıdır (`results/exp135_v4_digital_twin/v4_digital_twin_cert.json`, ana özet **`feffc1d4ba2b0698c3f61015c6684da47f57ea863a8b3e0da845cc9c71914b57`**):
  - **L1 Yerleştirme:** `3,7155 / 3,6740 nm →` **`3,6201 nm (15 ms) / 3,5776 nm (10 ms)`** (`≤ 3,80 nm`; rijit `CFG1 = 2.076,97 nm` RED).
  - **L2 Sağkalım (`IBIC × flaş`):** **`%99,914`** (`0,99936 × 0,99978`).
  - **L4 `BOED` Kapasite:** `KL %51`: **`1,502–2,253×10⁹/gün`** (`7,61×–11,42×`); **`VOKL-6 HM5962 %33,25`**: **`9,794×10⁸ – 1,469×10⁹/gün`** (`4,96×–7,44×` `v3-KL`, hâlâ yazma-sınırlı); `VOKL-6 norm %4,75`: `1,399×10⁸/gün`.
  - **L6 `Exp131 × Exp129` Perkolasyon Çarpışması (`L=11` FT `≥ %99`):** `KL`: `N_cand* = 6` (`%99,24`); **`HM5962 f = %1`**: `N=6` **`%3,12`**'ye çöker → **`N_cand* = 11`** (`%99,74`); **`HM5962 f = %2`** → **`N_cand* = 6`** (`%99,92`); `VOKL-6 norm`: **`N_cand* = 86`** (mimari kırmızı çizgi!).
  - **L7 Birim Maliyet (`5y $16,07M`):** `v3-KL $52,88 →` **`v4-KL $7,33 (−%86,15) / $4,88 (−%90,77)`**, **`v4-HM5962 $11,24 (−%78,75)`** (`d=17`: `$0,0083 / $0,0055 / $0,0195`).
  - **L8 Canlı `4×4` Yonga İkizi:** `40,82 ms/yuva`, `MultiCellProgrammer` **`F_joint = 0,983448`**, **`min_bus_cz = 0,988923`**.

---

## Bölüm 10: `v5.0` Hata-Toleranslı Yükseltme Paketi (`Exp136`–`Exp141`): `sp³d⁵s*` TB, `P4 Echo CZ`, MWPM FT, `1530 K`+MBE, `N_mux*=32` & Master Dijital İkiz

Bu bölüm, tarihsel `v5.0` hata-toleranslı dalgasında eklenen 6 birinci-ilkeler deneyini özetler (`tests/test_exp136..141.py`; `v5.0` dönem paketi `198/198 PASS`, güncel `v6.0` tam paketi Bölüm 11'de **`252/252 PASS`** [`28/28` dosya]; tümü `no_lab_measurement=true`, `no_supplier_quotes=true`).

- **`Exp136` (`H154`, `4/7 PASS`, `10/10` test):** `16.000` atom / `160.000` orbital `sp³d⁵s*` TB çözücüsü `Exp129` `R331` sapmasını `%64,73 →` **`%21,1`** (`α_cp=0`) / **`%25,7`** (`α_cp=0,015`, `log10-RMS = 0,2426`) indirdi; `f=%1 → %52,75 (%99,74 M4)`, **`f*=%1,5+2 MV/m → %77,50` / DDRF `%54,00` (`%99,88 M4`)**, `f*=%2,0 → %59,75 (%99,99 M4)`, `XY8 T₂e = 10,8–20,3 ms`.
- **`Exp137` (`H155`, `4/7 PASS`, `8/8` test):** `12×12` CUDA + `M=40` OU `1/f^α` altında `P4` (`XY4-DRAG-Echo-CZ`) `δg` cezasını **`5,09×`** bastırır; pasivesiz `S_ε=1,0 µeV/√Hz` `F_Bell=0,9587` (`0,9824` hızlı); **`Exp139` Rota C ile `(Q=2e5, S=0,50) → F_Bell=0,9901`, `(Q=5e5, S=0,25) → F_Bell=0,9949, F_avg=0,9926, p_err=%0,92 < %1`**.
- **`Exp138` (`H156`, `6/7 PASS`, `10/10` test):** `d=3..11` Edmonds Blossom MWPM: **`p_2q,th = %1,60 ± %0,17`**, `P1 Λ=0,00`, `C2 Λ=1,04`, `D1 Λ=1,26`, **`D2 (Q=5e5, S=0,25) Λ=1,40`** (`10⁻⁹: d*=99, 679` kriyo), **`D3 (p_2q=%0,50) Λ=2,52`** (`10⁻⁹: d*=37, 100` kriyo, `1 L/kriyo`, **`6,8×` küçülme**); `f*=%1,5+2 MV/m+N=6 → d_eff/d = %99,5` (`FT5 FAIL` @ `f=%1, N=6: %79,0`).
- **`Exp139` (`H157`, `4/7 PASS`, `9/9` test):** `v4` `1440 K` gizli `+1,318 nm` TED (`3,995 nm` FAIL) keşfedilip **`v5` `1530,1 K` (`43,49 J/cm²`, `%99,99` küme temizliği, `σ_anneal=0,430 nm`, `σ_tot=3,665 nm` PASS)** + **Rota C (`S_ε=0,390 µeV/√Hz`, `2,57×` düşüş, `p_ff=%97,70`)** + **`S5.6` MBE (`22,4 kg`, `$95k`, `0 µW`, `%0` akış cezası)** ile çözüldü.
- **`Exp140` (`H158`, `7/7 PASS`, `7/7` test):** `Q16.16` FPGA `abs(ΔRMS)=0,0502 Hz`, `2,336 µs/adım`, `%10,49` DSP48E2; **`N_mux*=32` (`F_RO=%99,61`, `625×` Purcell; `64` FAIL `%94,13`)**; `1.024` PASS / tek kriyo **`2.887` hücre** / `10.000 ≥ 4` kriyo; `CellISA v3.5` (`17` opcode); `S6.5` (`19,27 kg`, `$629,2k`).
- **`Exp141` (`H159`, `8/8 DT5 PASS`, `9/9` test):** `19/19` artefakt `SHA-256` kilitli tarihsel `v5.0` dijital ikizi (`results/exp141_v5_digital_twin/v5_digital_twin_cert.json`, tam 64-hex **`SHA-256 = 2828e8ce8d9388f7cba5490b2d05add930aadc5fe6d3ba4295f0380f816d43d1`**): yerleştirme **`3,6307 / 3,5883 nm`**, canlı `Q16.16` `0,0183 Hz`, canlı `CellISA v3.5` `ECHO_CZ = 0,9818`, `W2/W3` SOI `CX4 PASS` (`$0,616 / $0,442/çip`, `−%79,5 / −%85,3`), `10⁻⁹` `D2` `$/L_fab=$5,20` / `$/L_sys=$14,94M` vs `D3` `$0,73` / `$2,76M` (`5,41×` ucuz).

---

## Bölüm 11: `v6.0` Modüler Ölçekleme, `qLDPC` Devrimi & Canlı IBM QPU Doğrulaması (`Exp142`–`Exp146`)

Bu bölüm, `v6.0` dalgasında eklenen 5 deney paketini özetler (`tests/test_exp142..146.py`; tüm **`28/28`** staged Atom Litografi test paketi **`252/252 PASS`**; silikon `³¹P` `M0` model, `Exp145` kontrol/DD/dekoder/BOED canlı `156Q` `ibm_marrakesh` donanımı).

- **`Exp142` (`H160`, `5/7 PASS`, `10/10` test):** Tak-çıkar **`Option-Q`** (`$168k / 9,20 kg`) — `5`-kademe Chebyshev `50 Ω ↔ 3 kΩ` (`IL = 0,0004 dB`, `BW = 5,20 GHz`), `F_SWAP_rt = 0,9858`, **`8.403×` (`1 s DD`) – `25.122×` (`3 s`)** bellek ömrü (`+0,78 µW @ 20 mK`); `S1-Multi` `10 km` `¹⁶⁷Er` `1.352,3 Hz` (`F = 0,9474`), `7,5 keV ¹²¹Sb` `−%41,5` keskin saçılma (`OQ5/6` gerinim/derinlik sınırı dürüst `FAIL`).
- **`Exp143` (`H161`, `4/7 PASS`, `9/9` test):** `D3` `K=8` Fourier GRAPE (`0,894 µs` muhaf. / `1,126 µs` yankılı, `%100 ≤ 300 MHz`): yankılı `Q=1e6, S=0,390 → p_2q = %0,395`, **`S=0,25 → p_2q = %0,337 (F_avg = %99,73, F_Bell = %99,69)`**, muhafazakar `high-g → %0,481`, canlı `Exp138` MWPM **`Λ_D3_phys = 2,825`** (`100L SC: 679 → 100` kriyo, `6,8×`); **`Option-HPC`** (`$132k / 64,0 kg / 2.195 W`, `0 W` kriyo): `τ_ingest = 777 ns`, `d=37 SC 6,34 µs < 6,70 µs`, **`qLDPC 108L 2,32 µs < 2,62 µs`**.
- **`Exp144` (`H162`, `7/7 PASS`, `10/10` test):** **`[[144,12,12]]` Gross Code** `P_cell = 20 µm → L_max = 268,3 µm ≤ 300 µm` (`0` rezonatör değişikliği!), `f* = %1,5 + 2 MV/m, N_cand = 8 → %99,64` blok / `%99,94` `108L` yonga verimi; `p_th = %0,633`; `D3+` (`%0,30`) `2,1×10⁻⁵/1L` (`5,2×` iyi, `10,0×` az hücre vs `d=11` SC); **`120L` tek `LD400` kriyostatta (`108L = 1` kriyo, `$63.827/L_sys`, `234×` ucuz vs `v5 D2`, `W3` fab `$0,0085/L`)**.
- **`Exp145` (`H163`, `7/7 PASS`, `12/12` test, `{Canlı-Donanım-IBM-QPU}` + `{Model}`):** Gerçek **`156Q` `ibm_marrakesh` (`dc1tdo2nj2vs73dfrfl0`, `[2,3,4,5,6]`, `16 PUB × 4.096 shot`, `32,54 s`, `0` gizli sızıntı):** Bare `0,3325` → Echo `0,9224` (`+59,0 pp`) → XY4 `0,9280` (`+59,5 pp`), Bell **`0,9733`**, `d=3` `p_phys = %2,96 → MWPM %0,57 (5,16×) / maj %0,38 (7,83×) / postsel %0,00`, `Q16.16 BOED` `3`-nokta `120,11 kHz` (`1,6 Hz` vs FP64); **`CellISA v4.0` (`20` op)** & **`auto_recal.py` (`4/4 PASS`)**.
- **`Exp146` (`H164`, `8/8 DT6 PASS`, `10/10` test):** `24/24` birincil + canlı QPU `SHA-256` kilitli Master `v6.0` Dijital İkiz (`results/exp146_v6_digital_twin/v6_digital_twin_cert.json`):
  - **Tam 64-Hex `v6_digital_twin_cert.json` `SHA-256`:** `ca3f0e0267263bacb973f46c3cc2d321c0f204075ea232f4094758e1a9abf1d7`
  - **Canlı `ibm_qpu_live_results.json` `SHA-256`:** `02b7a19d1704662c6424e76f4971e21b04a98d48230a917c9682853b3ca1fc5a`
