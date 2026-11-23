# Literatür ve Dış Çapa Sicili — Atom Litografi Makinesi (`LITERATURE`)

**Güncelleme Tarihi:** 2026-11-22 (v1: 2026-10-20; `Exp108` eki: 2026-10-22; `Exp109–114` eki: 2026-10-26; `Exp116–118` ve `Exp124–127` kuramsal çapaları: 2026-11-22).  
**Amaç:** `DESIGN.md` (`v2.24+`), `MODULAR.md` (ICD) ve `M1_PROTOTYPE_BLUEPRINT.md` varsayımlarını yayımlanmış birincil literatür, patent ve üretici veri sayfalarıyla çapraz kontrol etmek.

> **Epistemik Sınır:** **Bu belge ikincil literatür ve katalog çapası derlemesidir; proje içi laboratuvar ölçümü değildir (`no_lab_measurement=true`).** Her çapa `{Literatür}` etiketiyle taşınır ve karşılık gelen proje deneyiyle (`ExpID`) bağlanır.

---

## 1. Sayılmış Tek-İyon İmplantasyon ve Algılama (`M4` / Mod A–B)
- **IBIC ile `%99,87` güven (`Exp57`, `Exp72`):** `14 keV ³¹P⁺` tek iyonları, altlık-içi elektrotlar + yük duyarlı ön yükselteç (CSA) ile `%99,87 ± 0,02` güvenle sayıldı (**Jakob vd., `arXiv:2009.02892`**; ayrıca Robson vd. 2022) `{Literatür}`. `Exp72` model çapasıyla (`η ≈ 1 @ 10 keV`, `η = 0,9914 @ 5 keV, C ≤ 0,5 pF`) uyumludur; ancak sayım yalnız iyon *sayısını* sabitler, yerleştirme saçılmasını telafi etmez (`Exp57`).
- **İkincil-elektron (SE) algılama (`DESIGN §3.3` yedek modu):** FIB içinde ikincil elektron sayımıyla `50 keV P`'de `%82 ± 4`, `Sb₂` ikilisinde `%94 ± 8` tespit verimi (**`Adv. Eng. Mater. 2025`, `doi:10.1002/adem.202502911`; `arXiv:2510.01035`**) `{Literatür}`. Altlık-içi IBIC dedektörü gerektirmemesi ölçekleme avantajıdır; verim IBIC'in altında olsa da seçim mimarisi bu oranı tolere edebilir.
- **Molekül iyonu (`PF₂⁺`, Mod A adayı):** Seyirci flor iyonlarının ek sinyali, fosfor çarpma enerjisini (dolayısıyla saçılmayı) artırmadan algılama güvenini yükseltir (**`arXiv:2308.04117`**) `{Literatür}`.
- **RF reflektometriyle hızlı tek-iyon/yük algılama (`Exp108`):** `< 100 ns` zaman çözünürlüklü RF fotoiyonizasyon/yük tespiti (**`arXiv:2212.00440`**) `{Literatür}` — `200 ns` şekillendirme / `1 ms` atış çevrimi (`Exp65`, `BOARD.md`) bant genişliğiyle uyumludur.

---

## 2. Çok-Demet Blanker Dizileri, İyon Kaynağı ve İyon-Katı Durdurma (`M1`, `M2`, `Exp124`, `Exp127`)
- **Çok-demet blanker dizileri (`Exp78–79`):** Blanking aperture array + LSI kontrol, elektron çok-demet yazıcılarında üretime girmiş teknolojidir: **IMS Nanofabrication MBMW-101** (`512.512` demetcik), **NuFlare MBMW** patent ailesi (**`US20240029999A1` / `JP2024012973A`**, üretim blanker adımı **`32 µm`**, `30 µm` Si kalkan — **`US10658158B2`**), ve **Mapper/PML2-eMET** `{Literatür}`. Makinenin özgün katkısı blanker kavramı değil; sayım geri-beslemeli kapalı çevrim (`IBIC → blanker`) + ölçüm-sonrası yazmaç seçimi ve kalibrasyonudur.
- **Yüksek-parlaklıklı iyon kaynağı (`Exp71`, `Exp81–82`):**
  - **Duoplazmatron / plazma kaynağı:** Fabrika akım yoğunluğu `J = 10 mA/cm²` (**`US11289299B2`**) `{Literatür}`; `Exp81` bunun `E = 10 keV, Ti = 1 eV` için `B = 3,183×10⁵ A/m²/sr` (`Exp71` şartının `7,84×` üstü) verdiğini göstermiştir. Plazma FIB aralığı `10³–10⁵ A/cm²/sr` (**`US9401262`**). Ancak çıplak duoplazmatron enerji yayılımı (`ΔE ≈ 6–100 eV`) kromatik sapmayı bozduğu için **`ΔE ≤ 2 eV` enerji süzgeci** (`Exp82`) ve `10 keV` çıkarım → `5 keV` yavaşlatma optiği (`Exp91-BudgetAttack`, `Exp124`) şarttır.
  - **LMIS ve moleküler alternatifler:** Ga LMIS `~10⁶ A/cm²/sr` (NIST FIB notları); B, As, Si, Be alaşım LMIS'leri (**`US4716127A`**) `{Literatür}`. P-taşıyan alaşım LMIS kimyası (buhar basıncı/ıslatma) açık AR-GE maddesidir; kırmızı fosfor buharı + elektron bombardımanı (moleküler P) ikincil adaydır.
  - **Parlaklık tanım birliği (`results/exp71/NOTE_brightness_definition.md`):** Farklı kaynaklar eksenel parlaklık (`B`, `A/m²/sr`) ile indirgenmiş parlaklık (`B_r = B/V`, `A/m²/sr/V` — Liouville/Lagrange–Helmholtz teoremi gereği elektrostatik hızlandırma/yavaşlatma altında korunur) tanımlarını karıştırır; tüm kolon tasarımları (`Exp124`) tek biçimli `B_r` tanımıyla çapraz kontrol edilmelidir.
- **İyon-katı saçılması, elektron-boşluk verimi ve kanalizasyon (`Exp57`, `Exp92–96`, `Exp108`, `Exp124`, `Exp127`):**
  - **Lindhard–Scharff–Schiøtt (LSS) & Lindhard bölüşümü:** Düşük-enerjili (`5–20 keV`) `³¹P⁺ → Si` implantasyonunda elektronik/nükleer durdurma oranı ve IBIC yük oluşturma payının (iyonizasyon verimi `Y_e`) fiziksel temeli (**J. Lindhard, V. Nielsen, M. Scharff, P. V. Thomsen, *Mat. Fys. Medd. Dan. Vid. Selsk.* 33, No. 10 (1963)**; **J. Lindhard, M. Scharff, H. E. Schiøtt, *Mat. Fys. Medd. Dan. Vid. Selsk.* 33, No. 14 (1963)**) `{Literatür}`.
  - **ZBL / SRIM (amorf ikili çarpışma yaklaşımı — BCA):** Evrensel perdelenmiş Coulomb potansiyeli (**J. F. Ziegler, J. P. Biersack, U. Littmark, *The Stopping and Range of Ions in Solids*, Pergamon, 1985**; SRIM) `{Literatür}` — `Exp92` amorf BCA (`σ_x = 3,259 nm @ 5 keV`) modelinin birincil dayanağıdır.
  - **Crystal-TRIM (kristal kanalizasyon):** Kristal silisyumda `<110>` eksenel/düzlemsel kanalizasyon referans motoru (**M. Posselt, *Radiat. Eff. Defects Solids* 130–131, 87–119 (1994), `doi:10.1080/10420159408219774`**) `{Literatür}`. `Exp93–96` ev-yapımı kristal BCA kalibrasyonunu kapatamadığından tasarım `3,80 nm` amorf BCA'da bırakılmıştır.
  - **Tavlama göçü uyarısı (`Exp108`):** İmplante `³¹P`, `600 °C / 10 dk` fırın tavlamasında ön yüzeye göçer, `800 °C`'de yüzeyden kaçar (**`doi:10.1063/1.331355`**) `{Literatür}`. Flaş tavlama penceresi (`σ_tavlama ≤ 0,5 nm`) bu göç eşiğinin altında ms ölçeğinde tasarlanmalıdır.

---

## 3. Konumlandırma, Piezo Kademe ve 4 K SKY130 Ölçümü (`M5`, `M3`, `Exp32–33`, `Exp79`)
- **UHV Piezo Kademe (`Exp79`):** Ticari 6-serbestlikli kaba+ince piezo yığını (**Physik Instrumente `P-561/P-562/P-563` PIMars sınıfı**: `100–300 µm` seyahat, `0,2 nm` tipik çözünürlük, `10⁻⁹ hPa` UHV uyumlu) `{Literatür}` — özel maglev kademeyi (`S4.3 D→C`) kaldırarak sabit tabanı düşürmüştür.
- **4 K SKY130 Ham Ölçüm Verisi (`Exp32–33`):** **NIST/Google SKY130 kriyojenik karakterizasyon veri seti (`mds2-2997`, Apache-2.0)** `{Ölçüm-3.Taraf}` — `4 K` kink yükseltimi (`A` medyan `1.544`) ve azaltılmış ters gövde etkisi (`|dV_T/dV_B| = 0,105`) bu ham ölçümden çıkarılmıştır.

---

## 4. Çoklamalı RF Okuma, Süperiletken Rezonatörler ve Kriyo Termal/Mıknatıs Çapaları (`M7`, `Exp108–114`, `Exp125`)
- **Toplu-LC Kapı Reflektometrisi vs. Süperiletken Rezonatör (`Exp108`):**
  - Standart Si transistörde toplu-LC kapı reflektometrisi: **`Q_loaded ≃ 18`** (**`arXiv:1811.04414`**; çift-kapı reflektometrisi **`arXiv:1610.03657`**) `{Literatür}` — `Exp87` `Q=100` varsayımının toplu-LC için iyimser olduğunu gösterdi.
  - Çoklanmış GHz süperiletken rezonatörlerle kuantum nokta okuması (**`arXiv:2103.03659`**) `{Literatür}` — `Q ≥ 100` (`Ql = 800–1200`) için mimari çataldır.
- **Yüksek Manyetik Alana Dayanıklı NbTiN/NbTi Rezonatörler ve Frekans Saçılması (`Exp109`, `Exp112–113`, `Exp125`):**
  - İçsel kalite faktörü (`Qi`) ve paralel alan dayanımı: NbTiN `Qi ~ 2×10⁵ @ 7 mK` (**`arXiv:2112.08296`**), `Qi > 2×10⁵ @ 0–0,3 T` (**`arXiv:2312.13703`**), 45 nm NbTi `Qi = 1,01×10⁴ @ B∥ = 0,4 T` (**`arXiv:2509.20782`**), AlOx `~7×10⁵ @ 20 mK` (**`arXiv:1408.4347`**) `{Literatür}` → rezonatör düzleminde **`B_rez ≤ 0,4 T`** şartının dayanağı.
  - İmalat frekans saçılması & kırpma (trimming) verimi: yerel saçılma `σ_f/f ≈ 2,7×10⁻³` (**`arXiv:1803.04275`**); çarpışma verimi `%84→%97` (**`arXiv:1711.07914`**); lazer/kırpma ile `1/14` daralma ve `%97` verim (**`arXiv:2105.14046`**) `{Literatür}`.
  - Frekans titreşimi (TLS gürültüsü): GHz sınıfında birkaç kHz / tutucu `σ_frac = 10⁻⁶` (**Niepce vd., `arXiv:2008.07038`**); izleme tabanı `2×10⁻⁹` (**Burnett vd., `arXiv:1210.2351`**) `{Literatür}`.
- **Kriyo Termal Yükler, LNA ve Soğutucu Katalogları (`Exp110–114`):**
  - Hat başına ölçülmüş koaksiyel termal yükler ve seyreltme soğutma güçleri (`MXC`: `13–19 µW @ 20 mK`, `540 µW @ 100 mK`): **Krinner vd., Tablo 2 (`arXiv:1806.07862`)** `{Literatür}`.
  - Düşük güçlü 4 K kriyo-LNA: `2,1 mW @ 4 K`, `1,4 K` gürültü sıcaklığı, `41,6 dB` kazanç (**Rebelo vd., `2026`, `doi:10.1002/pssa.202501018`**) `{Literatür}`.
  - Ticari kriyo-LNA doğrusallığı: **Low Noise Factory `LNF-LNC4_8C`** veri sayfası (`4–8 GHz`, `42 dB`, `OP1dB = −12 dBm`, `OIP3 = −2 dBm`, `10,5 mW` DC) `{Literatür}` — `Exp113` `NL_max = 316 @ −100 dBm/ton` sıkışma çapası (100–900 MHz bandı için alt-GHz ekstrapolasyon uyarısı kayıtlıdır).
  - Pulse-tube soğutucular: **Cryomech `PT410 / PT415 / PT420`** (`1,0 / 1,5 / 2,0 W @ 4,2 K`) `{Literatür}`.
  - `Exp114` fiyat kalibrasyonu (`anchors_exp114.csv`): 4 kamuya açık liste/ilan çapası (`PT410` 2. el `$19k`, `Renishaw XL-80` `$32k–$44,25k`, `Lambda GPU` `$10,6k`, turbo+iyon pompa `~$16k`) → BOM sınıf birimi **`$190–$1.600` (medyan `$720`, `8,42×` yayılım)**; kriyo-LNA ve izolatör teklif usulüdür (`RFQ_SPECIFICATIONS.md` konusu).
- **Aktif Karşı-Sargılı Süperiletken Mıknatıs & Meissner Kalkanlama (`Exp125`):**
  - Kesin eksenel simetrik halka integralleri (`ellipk`/`ellipe` Biot–Savart formülasyonu): **J. D. Jackson, *Classical Electrodynamics*, §5.5**; **M. N. Wilson, *Superconducting Magnets*, Oxford Univ. Press (1983)** (NbTi kritik akım yüzeyi `J_c(B,T)`, aktif karşı-sargılı [actively shielded / bucking] bobin tasarımı, Lorentz çember gerilmesi `σ_hoop = J·B·r` ve quench koruması) `{Literatür}`. Düşük-alan Nb/Cryoperm hibrit Meissner kalkanlaması kriyojenik spin-okuma düzeneklerinde örnek (`1,5 T`) ile rezonatör düzlemi (`≤ 0,4 T`) arasında alan ayrıştırmasının kuramsal temelidir.

---

## 5. Tek-Donor Spin Spektroskopisi ve Sıcak Okuma Çapaları (`Exp116`, `Exp117`, `Exp118`)
- **Tek-Donor `³¹P` Spin-Yüke Çevirme (Elzerman) Pratiği — Neden `4 K` Dışlandı? (`Exp116`):**
  - Tek-donor `³¹P` tek-atış elektron/çekirdek spin okuması standart olarak **`~50–100 mK` (`MXC`) ve `B > 1 T` (`~1,5 T`)** altında çalışır (**Morello grubu hattı: `Nat. Commun. 4:2017`; enerji-seçici tünelleme ve Kane aygıt pratiği: `arXiv:1801.10265`, `arXiv:2009.04081`**) `{Literatür}`.
  - `1,7 K` topluluk (ensemble) ESR'si (**`arXiv:1902.01343`**) tek-donor okuması değildir; `1,5–5 K` sıcak kübit gösterimleri (**`arXiv:2103.07369`**) kuantum nokta/delik Pauli-blokaj aygıtlarıdır `{Literatür}`. `≥ 4 K` tek-donor spin spektroskopisi çapası bulunamadığından `S6.8` seyreltme kademesi (`MXC ~20 mK`, sınıf `D`) `Exp116/121` ile BAZ alınmıştır.
- **`1–3,7 K` Sıcak Okuma (Pauli Spin Blokajı / Kilitli Parite — `Exp117`, Maliyet-İndirme Alternatifi):**
  - **Diraq / UNSW (`Nature 2024`, `s41586-024-07160-2`):** Silikon spin kübitlerinde **`T = 1 K`'da `%99,6` PSB okuma sadakati** (`T1_PSB = 1,36 ms @ 1 K, 0,79 T`) `{Literatür}`.
  - **Geng vd. (`Nat. Commun. 2025`, `doi:10.1038/s41467-025-58279-3`):** Hassas-yerleşimli çok-donorlu kuantum noktalarında **kilitli parite (latched parity) okuması `T = 3,7 K, B = 0,4 T`'de `%97,8` maksimum sadakat** (`mK`'de `%99,44`) `{Literatür}` — `Exp117` CO2 belirleyici donor çapası.
  - Destekleyici donor-nokta PSB ve singlet–triplet çapaları: `ncomms9848` (`Nat. Commun. 2015`, donor noktalarında Pauli blokajı + ayarlanabilir değişim) ve donor çifti singlet–triplet `%98,4` tek-atış okuması (`Nat. Commun. 2017`) `{Literatür}`.
- **Yardımcı-Nokta Tünel Bağlaşımı Ayar Penceresi (`Exp118`):**
  - **House vd. (`Nat. Commun. 6:8848`, 2015):** `Si:P` donor noktalarında `~20 nm` ayrımda `t_c/h ~ 1 GHz` tünel bağlaşımı ve kapı gerilimiyle **`≥ 100×` ayarlanabilir değişim/bağlaşım (`20 µeV – 8 meV`)** `{Literatür}` — `Exp118` `8`-onluk yakalama penceresinin birincil deneysel çapasıdır.

---

## 6. Optimal Kuantum Kontrol (GRAPE), Dinamik Ayrıştırma (CPMG / XY8) ve Bağ Modeli (`Exp42–63`, `Exp126`)
- **GRAPE Optimal Kontrol (`Exp49–61`, `Exp126`):** Parçalı-sabit darbe gradyan yükseltme algoritması (**N. Khaneja, T. Reiss, C. Kehlet, T. Schulte-Herbrüggen, S. J. Glaser, *J. Magn. Reson.* 172, 296–305 (2005)**) `{Literatür}` — yazmaç-özgü köşe-dayanıklı (`±400 Hz`, `±%2`) XY darbe sentezinin (`Exp61`, `Exp126`, `pulse_engine.py`) temelidir.
- **Dinamik Ayrıştırma — CPMG ve Sağlam `XY8` (`Exp63`, `Exp68`, `Exp126`):**
  - Tek-eksenli çok-darbeli yankı dizisi: **H. Y. Carr, E. M. Purcell (*Phys. Rev.* 94, 630, 1954)** ve **S. Meiboom, D. Gill (*Rev. Sci. Instrum.* 29, 688, 1958)** (`CPMG`) `{Literatür}`.
  - Darbe hatasına (`ε`) ve eksen sapmasına karşı iki-eksenli simetrik faz-çevrimli dizi: **T. Gullion, D. B. Baker, M. S. Conradi, *J. Magn. Reson.* 89, 479–484 (1990)** (`XY4 / XY8`) `{Literatür}` — `Exp126` iç-içe elektron-π DD + çekirdek kapı sentezinde `CPMG` ile birlikte kullanılmaktadır.
- **Kohn–Luttinger `³¹P` Aşırı-İnce Bağ Modeli ve ENDOR Çapaları (`Exp25`, `Exp42`, `Exp56`, `Exp60`, `Exp69`, `Exp75`, `Exp129`):**
  - Etkin-kütle kuramı (**W. Kohn, J. M. Luttinger, *Phys. Rev.* 97–98, 1955**; **R. A. Faulkner, *Phys. Rev.* 184, 713, 1969** `E_EMT = -31,27 meV`), Si:P ENDOR kabuk ölçümleri (**G. Feher, *Phys. Rev.* 114, 1219 (1959)**; **E. B. Hale, R. L. Mieher, *Phys. Rev.* 184, 739 (1969)**; **J. L. Ivey, R. L. Mieher, *Phys. Rev. B* 11, 822 (1975)**), `3s` çekirdek yoğunluğu oranı (**J. R. Morton, K. F. Preston, *J. Magn. Reson.* 30, 577 (1978)**) ve atomistik DFT/TB çekirdek-polarizasyon referansları (**H. Overhof, U. Gerstmann, *Phys. Rev. Lett.* 92, 087602 (2004)**; **W. Ma vd., *npj Comput. Mater.* 8, 2022**) `{Literatür}`. `Exp129` (`VOKL-6`), tek-bant süreklilik EMT'nin `[110]` kovalent zikzak zincirindeki (`R331 %64,7`) yapısal sınırını ve Risk `R1`'in gerçek bir aşağı-yönlü Mod B verim riski olduğunu (`VOKL-6 HM5962 %33,25`, `norm %4,75`) kanıtlamıştır.

## 6B. `v4.0` Ek Literatür Çapaları: Flaş-Tavlama, `M4` Kavite-QED, Titreşim & TCO (`Exp130`–`Exp134`)
- **Milisaniye Flaş/Lazer Tavlama & SPE/TED (`Exp130`):** Katı-faz epitaksisi (**G. L. Olson, J. A. Roth, *Mater. Sci. Rep.* 3, 1 (1988)**), geçişli hızlandırılmış difüzyon (`TED`) ve `³¹P` `600 °C/10 dk` yüzey göçü / `800 °C` vakum kaçışı (`doi:10.1063/1.331355`) `{Literatür}` — `Exp130`'da `808 nm / 1,0 ms / 1440 K` (`41,15 J/cm²`) penceresiyle `f_act = %99,98`, `σ_anneal = 0,328 nm` kapatıldı.
- **`M4` Flip-Flop Kübit & Yüksek-Empedanslı `NbTiN` Kavite-QED (`Exp131`):** `³¹P` elektrik-dipol flip-flop kübiti (**G. Tosi vd., *Nat. Commun.* 8, 450 (2017)**) ve yüksek-empedanslı (`3 kΩ`) `NbTiN` mikrodalga rezonatör veri yolu (**N. Samkharadze vd., *Science* 359, 1123 (2018)**; **X. Mi vd., *Nature* 555, 599 (2018)**; **A. J. Landig vd., *Nature* 560, 179 (2018)**) `{Literatür}` — `Exp131`'de `Δz_cap* = 8±1 nm`, `3 kΩ NbTiN` `F_Bell = 0,9655` vs `50 Ω` `0,7908` ve 2B yüzey kodu perkolasyonu (`N_cand* = 6` [KL] / `11` [VOKL-6]) doğrulandı.
- **Bayesyen Uyarlamalı Deney Tasarımı (`Exp132`):** Sıralı Bayesyen frekans kestirimi / CRLB (`BOED`, **C. Ferrie, C. E. Granade, D. G. Cory, *Quantum Inf. Process.* 12, 611 (2013)**) `{Literatür}` — `Exp132` `41,0 ms` (`24,4×` ham okuma, `7,61×–11,42×` net fabrika hızlanması, `$0` ek donanım).
- **Titreşim İzolasyonu (`Exp133`) & Öğrenme Eğrisi (`Exp134`):** Temiz oda titreşim sınıfları (**ISO / IEST-RP-CC012 `VC-C / VC-E / VC-G`**) ve üretim öğrenme yasası (**T. P. Wright, *J. Aeronaut. Sci.* 3, 122 (1936)**, `b = %85`) `{Literatür}`.

---

## 7. Tasarıma Çapraz Geri Besleme Özeti
| Alan | Literatür Çapası | Tasarıma Bağlayıcı Etki (`DESIGN v4.0` / `MODULAR v4.0` / `BOM v4.0`) |
|---|---|---|
| Tek-iyon sayımı | IBIC `%99,87` (`2009.02892`), SE `%82` (`2510.01035`), `PF₂⁺` (`2308.04117`) | `COLD_100K` (`100 K / 1,2 µs / 1 GΩ`) IBIC `η = %99,94 @ 5 keV` baz (`Exp127`) |
| Blanker & kademe | NuFlare `32 µm` (`US10658158B2`, tarihsel `Arch-C`), PI `P-561..563` (`0,2 nm`), `VC-E/G` | Kilitli `Arch-B` `32×32 = 1.024 @ 0,50 mm` (`Ø28 mm`), `PT420` dekuplaj (`σ_stage = 0,102 nm`, `Exp124/133`) |
| Kaynak & tavlama | Duoplazmatron `10 mA/cm²` (`US11289299B2`), `³¹P` göçü (`10.1063/1.331355`), Olson–Roth SPE | `10→5 keV`, `HDA-HiRes ΔE_FWHM = 0,453 eV`; `S5.5` `808 nm / 1 ms / 41,15 J/cm²` (`f_act = %99,98`, `Exp124/130`) |
| Çoklamalı okuma | NbTiN `Qi~2×10⁵` / `≤0,4 T` (`2112.08296`, `2509.20782`), Rebelo `2,1 mW`, Krinner (`1806.07862`) | `8`-bobin `1,500000 T / 22,3 µT` (`R7` kapalı), `56–82` hat `4 K ≤ 0,899 W / MXC ≤ 4,8 µW`, `BOED 41 ms` (`Exp125/132`) |
| Spektroskopi sıcaklığı | Morello `~100 mK`, Diraq `1 K %99,6` (`Nature 2024`), Geng `3,7 K %97,8`, House `100×` | `S6.8=D` (`20 mK` DR) BAZ (`EVPI@N=1 = $0`, `N_be = 6,01` makine, `Exp121/125/128`) |
| Kuantum kontrol & `M4` | Khaneja GRAPE (`2005`), Gullion `XY8` (`1990`), Tosi (`2017`), Samkharadze/Mi (`2018`) | Zorunlu `XY8 N=32–64`, `10–15 kHz` RF (`R3` kapalı); `M4` `3 kΩ NbTiN` `F_Bell = 0,966`, `Δz_cap* = 8 nm` (`Exp126/131`) |
| Bağ modeli & TCO | Hale–Mieher (`1969`), Overhof–Gerstmann (`2004`), Wright (`1936`, `b = %85`) | `R1` aşağı-yönlü risk (`VOKL-6 %33,25` → `M1` ENDOR kapısı); `v4.0` birim maliyet `−%86,2` (`Exp129/134/135`) |
