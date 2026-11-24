# Hipotezler ve durumları

Fikir: elektrikle uyarılan transistör+süperkapasitör hücreleri, içlerinde daha küçük hücreler doğurur;
en küçük nesil kuantum rejimine geçer.

Not: Deney 0 (`results/exp0`) yazdığım analitik bir ön hesaptı, fiziksel simülasyon değildi.
Aşağıdaki durumlar Deney 1'e (`results/exp1`, 3B FEM, doğrulanmış) dayanır; kapsam dışı olanlar açıkça belirtildi.

| # | Hipotez | Durum (Deney 1) |
|---|---|---|
| H1 | Nesil küçüldükçe E_C ∝ 1/L büyür ve bir nesilde E_C ≥ 10 kT olur | FEM'de C ∝ a (ölçek değişmezliği), r=0.5 için c_Σ ≈ 23 ε0·a (±~%1,2). 4 K: nesil 2 (25 nm, ε=3,9) veya nesil 4 (6 nm, ε=11,7). 77 K: yalnız <1 nm'de (model geçersiz). 300 K: yok. **Kısmen destekleniyor (yalnız kriyojenik).** |
| H2 | Yüksek kapasitanslı "süperkapasitör" hapsetmeyi güçlendirir | FEM'de ayrıca test edilmedi. E_C = e²/2C ilişkisi gereği C arttırmak E_C'yi düşürür; hücrede c_g toplamın ≈%76'sı. Deney 0'daki sonuç (ters etki) fizik kimliğiyle tutarlı. **Desteklenmiyor; doğrudan FEM testi yapılmadı.** |
| H3 | Çoğalma kuralı derinlemesine devam eder (enerji/kırılma penceresi) | Çoğalma kuralı FEM'e taşınmadı; Deney 0'ın analitik kuralı yalnız bir ön hesap. **Sınanmadı.** |
| H4 | Seviye ayrışması (hapsolma) Coulomb'dan önce gelir | FEM (Si/SiO2, V0=3,1 eV): ΔE sert duvar formülünden küçük (3 nm'de 0,69×, 1 nm'de 0,34×). 300 K'de ΔE ≥ 10 kT nesil 5'te (3,1 nm), marj küçük. **Destekleniyor, daha zayıf biçimde.** |
| H5 | İç içe iletken kabuk adayı "ekranlar" / bağlaşımı değiştirir | Yüzer kabuk eş-potansiyel; adanın C'si pencereden yalnız ≈%1 etkileniyor, kabuk ise C'yi %12 artırıyor. **Desteklenmedi.** |

## Deney 2 ve 3 (zincir, çift nokta, oda sıcaklığı qubit taraması) sonuçları

| # | Hipotez | Durum |
|---|---|---|
| H6 | Boyutu kademeli küçülen nokta zinciri, küçük hücreleri sırayla yükler ve en küçük hücre kuantum rejimine geçer | FEM kapasitans + ana denklem (12/6/3 nm): 4 K'de ada 0 ve 1 yük basamakları gösteriyor, **3 nm'lik en küçük ada hiç yüklenmiyor**; 77 K ve 300 K'de yük sürekli (kuantizasyon ≈ 0), akım salınımı yok. **Desteklenmedi (oda sıcaklığında).** |
| H7 | Çift hücrede (iki nokta) 300 K'de başlatılabilir ve koherant qubit oluşturulabilir | FEM Schrödinger + tek-fonon akustik altın kural, 9 geometri: 300 K polarizasyon ≥ 0,9 olan yok (en iyi 0,74, L=1 nm, d=0,5 nm, Δ=50 meV). En iyi geometride bile X-kapı doğruluğu 0,78 (τφ=100 fs, iyimser hızlı kapı); elektriksel 10 ps kapıda 0,5 (ölü). **Gösterilemedi.** |
| H8 | Fonon darboğazı büyük Δ'da koheransı korur | Δ=50 meV'de <F²> ≈ 8e-5 (q₀ ≈ 9 nm⁻¹ nokta boyutundan çok küçük dalga boyu), Δ≈10 meV'de ≈ 0,3-0,4. Yani akustik fonon etkisi büyük Δ'da gerçekten bastırılıyor. **Destekleniyor, yalnız akustik tek-fonon kanalı için.** |

Önemli: En iyi geometri taramanın kenarında (en küçük L, en ince d). 1 nm altında sürekli ortam modeli geçersiz; atomistik yöntem gerekli.
Optik fonon, Raman, yük gürültüsü ve vadi/orbital kanalları hesaplanmadı: T2 değerleri ÜST sınırdır. 300 K'de τφ = 10 fs/100 fs/1 ps senaryoları tahmin değil, varsayımdır.

## SKY130 yığını (Aşama 2a-2b), yol haritası: `research/roadmap/ROADMAP.md`

| # | Hipotez | Durum |
|---|---|---|
| H9 | SKY130 nFET kanalında dikey olarak 2B elektron gazı oluşur (kuantize alt bantlar) | 1B Poisson-Schrödinger (toxe 4,148 nm, ndep 1,7e17): tabaka ağırlık merkezi 2,45 nm, E₀ ≈ 50 meV (n_s = 10¹² cm⁻²). **Destekleniyor (model).** |
| H10 | Rastgele katkı potansiyeli minimum aygıtta kazara kuantum nokta oluşturur | MC (4 varyant, 3B FEM kontrollü): cihazların ≈ %4–21'inde bağlı durumlu nokta (a ≈ 15–23 nm, E_C/k_B ≈ 25–40 K). 3B FEM görüntü modelinden %18'e kadar büyük potansiyel verdi (düzeltme eklendi). Tünel bariyeri modellenmedi, istatistik küçük. **Geçerlilik sorunlu (exp9, bkz. `results/exp9/COMPARISON.md`):** düzeltmenin z<10 nm kısmı kesilince σ_ψ %23 düşüyor, katı oran %2,5–10'a iniyor; model oranı T'den bağımsız sayıyor, ama 4 K'de katkılar tam iyonlaşmıyor (NA = 1,7e17 ≪ N_c ≈ 3,7e18, bellekten). Doğrulanmadı; 4 K tahmini yeni model çıkana kadar kullanılmamalı.** **İnceleme (2026-10-11): oran tahmini geri çekildi.** Noktalar kutu kenarı artefaktı: kubbe σ_ψ²'nin %55–59'u, dört kenar dışlanınca 0/80. Yalnız rastgele RDF: 31/80–76/80, a ≈ 35–41 nm, E_C/kT ≈ 3,5–4. FEM düzeltmesi fiziksel 1,5 sınırını aşıyor; ekranlama yok. 4 K'de tükenme bölgesi alıcıları iyonize, asıl sorun yüzer gövde. **Belirsiz; öz-uyumlu modelle yeniden yapılmalı.** |
| H11 | V_T tanımı BSIM4 vth0 ile uyumlu | Sabit yük tanımı (n_s=10¹² cm⁻²) V_g = 0,513 V vs vth0 = 0,519 V; doğrusal ekstrapolasyon 0,34 V. **Tanıma bağlı; belirsiz.** |

## "Bölünme" mekanizmaları (Deney 8, soyut model)

| # | Hipotez | Durum |
|---|---|---|
| H12 | Yüklü bir küme, yük belirli bir eşiği aşınca iki parçaya bölünmek enerjice avantajlıdır (Coulomb fisyonu) ve eşik N^−1 ile ölçeklenir | LJ kümesi + Coulomb: g_c ∝ N^−1,08 (d=∞). g ızgarası ×1,45, eşikler ±%45 belirsiz. **Destekleniyor.** |
| H13 | Gate (kapasitör) uzaklığı bölünmeyi/hücre boyutunu belirler | Domain dalga boyu d=1,5'te 1,5–1,7× büyük; A_c(d) gate yaklaştıkça artıyor; φ̄=−0,4, A=0,15'te gate yaklaşınca desen başlıyor. **Destekleniyor (soyut model).** |
| H14 | Simetrik durum kararsızlaşınca sonlu boyutlu hücrelere ayrılır (bifurkasyon) | Süperkritik çatal bifurkasyonu: A_c analitik = sayısal, genlik üssü 0,502. **Destekleniyor (doğrulanmış).** |
| H15 | Hazır tek bir hücre (domain) Coulomb frustrasyonuyla ikiye bölünür | Disk, çubuk, elips: hiçbiri bölünmedi (küçüldü/çözündü). **Çürütüldü (bu 2B modelde, yalnız dengede).** Exp11: sürülen (disipatif) sistemde tek hücre bölünebiliyor (H17). Exp11'deki Coulomb + şarj koşularında da (28 koşu) bölünme yok (H18). |
| H16 | Bu mekanizmalar SKY130 evirme tabakasında geçerlidir | Exp10: φ ≈ (n − n₀)/n₀. Yerel ters kompresibilite n_s ≲ 1,5–3·10¹² cm⁻²'de negatif (çift kuyu fiziksel olarak var), ama kapı ekranlı Hartree k_F'ye kadar \|K\|'nın 11–21 katı (inceleme: 27 değil, Fang–Howard çarpanı unutulmuştu): düzgün tabaka kararlı, bölünme yok. Kararsızlık yalnız n ≲ 3·10⁹–2·10¹⁰ (r_s ≳ 20–50), model geçerliliği dışında. **Çürütüldü (SKY130 çalışma aralığında, dengede).** Yeniden kontrol: kod Thomas–Fermi analitiğiyle birebir; bölünme yalnız kapı ≤1 nm (SiO₂) ya da ≤2 nm (ε=20) ve n ≲ 1–5·10¹⁰ cm⁻² (r_s ≈ 12–26) için çıkıyor; hücre boyutu kesme sınırına bağlı, güvenilmez. Exp11: tutarlı HF (korelasyon olmadan) hiçbir kapasitansta (0,05–3000 µF/cm²) kararsızlık vermiyor; korelasyonlu sonuç, kapı ekranlı olmayan vekile dayanıyor (model içi tutarsızlık). **İnceleme (2026-10-11): "yakın kapı bölünmeyi açar" sonucu bu tutarsızlığın ürünü.** Tutarlı HF'de S/K_kin ≥ +1,006, n_s = 10⁹–10¹³ cm⁻² ve her ε_kapı için. **Çürütüldü (her kapıda, tutarlı modelde).** |

## Sürülen (disipatif) bölünme: Deney 11 (`results/exp11/summary_exp11.md`)

| # | Hipotez | Durum |
|---|---|---|
| H17 | Disipatif sürüş (Prigogine) tek bir hücreyi çoğaltır | Gray–Scott: 5/42 (F,k) noktasında çoğalma (inceleme: 6 değil, biri labirent), %5 gürültü ve 3 tohumla 6/6. Aktif damla 2B'de ikili bölünme 0/30 (9 solucan, 1 kopma); 3B'de Δν −0,002…+0,004 aralığının hepsinde ikiye bölünüyor, **Δν = 0 dahil** (denge eşdeğeri). **Gray–Scott için destekleniyor; aktif damlada bölünme disipasyona özgü değil (sürüm 2).** |
| H18 | Süperkapasitör fikri (yüklü hücre + kapı ekranlı Coulomb + elektrikle şarj) tek hücreyi böler | 2B'de 0/28 kalıcı bölünme. Dambıl koşusu t = 60 000'e uzatıldı, bölünmedi. Güçlü şarjda 12/12 ortamdan doğum var, bölünme yok. 3B'de ekransız Coulomb'lu yüklü damla (≡ Δν = 0) bölünüyor. **2B kapılı tabakada çürütüldü; 3B ekransız durumda destekleniyor (sıvı damla fisyonu).** |
| H19 | Sızıntılı şarj (s = J − λc), disipatif modelin Δν = 0 çizgisine (Ohta–Kawasaki λ/q²) eşdeğerdir | Cebirsel olarak gösterildi ve testle doğrulandı. 2B'de bu çizgide 0/5 (ε = 0,20 noktası T'de hâlâ değişiyordu); **3B'de bölünüyor** (iki eşit kız, R = 8,8). **Destekleniyor (eşdeğerlik); 3B'de bölünme için yeterli.** |
| H20 | Sürüş arttıkça hücreler bölünerek küçülür ("küçülerek çoğalma") | Gray–Scott'ta D/2 ≡ uzunluk ölçeğinin √2 küçülmesi; N'nin artması bu yüzden kaçınılmaz. Gösterilen şey artışın **bölünmeyle** olması: soy takibinde doğum 0, N 83 → 127. Taban ℓ. **Destekleniyor (Gray–Scott; mekanizma olarak bölünme).** |
| H21 | Disipatif hücreler silikonda 4 K kuantum boyutuna iner (R ≈ 6–20 nm, geometriye bağlı) | Olay enerjisi ≈ E_g (kink mekanizması) ile en iyimser 123 nm (2B tabaka), ≈ 1,6 µm (3B), tipik ≈ 0,4 µm. 45 meV varsayımı kink literatürüyle desteklenmiyor. **Desteklenmiyor (mertebe tahmini).** |
| H22 | 4 K'de geniş bir SKY130 nFET'te darbe iyonlaşması akım filamanları (disipatif desen) oluşur | Exp12 (ngspice + resmî BSIM4 + indirgenmiş 4 K modeli). Eşik üstünde geri besleme zayıf, histerezis yok. Eşik altında yüzer gövde kilitlenmesi var: histerezis 26–105/108 kombinasyonda. Donmuş kuyu R_□ ≳ 10¹⁰–10¹² Ω/□ (ℓ ≪ W) iken yük direnciyle tek bir akım filamanı oluşuyor; V_ds analitik Maxwell geriliminde (0,80 V) kenetli, filaman akımla genişliyor (47 → 94 µm) ve bölünmüyor. **Model düzeyinde ve koşullu destekleniyor; klasik, kuantum değil; ölçülmeli.** Exp13: 5 parametre setinin 5'inde tek filaman; R_□ = 10¹⁰ dy ≤ 0,1 µm'de yakınsadı. |
| H23 | Eşik altı kilitlenme ortamında filaman, yerel bir inhibitör (dirençli drenaj) varsa Gray–Scott gibi bölünür | Exp13: yalnız global bağlaşımla bölünme yok. Uçlardan beslenen hatta filamanlar kontaklarda doğuyor; aşağı taramada ortadan bölünme var. Dağıtık balastta (λ = 40 µm, 5 kΩ, W = 300 µm) büyüme → ikiye bölünme 3/3 tohumda (≈ 4λ'da; merkezde V_D en düşük). Tekrarlayan çoğalma yok; kızlar 70–100 µm. **Model düzeyinde destekleniyor (tek bölünme); tekrarlayan çoğalma ve küçülme yok.** Exp16: λ = 5–20 µm'de filaman 203 µm'ye bölünmeden ulaştı, yani "≈ 4λ" genel bir yasa değil. |
| H24 | Aktif damlada bölünme boyuta bağlıdır (6B hiperküpte Cahn–Hilliard ile gösterilebilir) | Exp14: boyut sürekli değişken yapıldı (O(d−1) indirgeme; 3B Kartezyen ve gerçek 6B hiperküp 16⁶ ile doğrulandı). Bölünme yalnız bir boyut penceresinde oluyor. Altında şerit var (2B), üstünde damla bölünmeden içten boşalıp sıvı kabuk oluyor. Pencere Δν ile yukarı kayıyor: −0,004'te 2,25–2,5; −0,001'de 2,3–3,5; +0,004'te 2,5–4; Δν ≥ +0,012'de 6B de bölünüyor. Pasif RP bandı kR < √(d−2) d = 3–6'da %2,5–4 içinde doğrulandı. **Destekleniyor, ama tekdüze değil: yüksek boyut daha güçlü sürüş istiyor.** |
| H25 | Gerçek bir fiziksel 6B faz uzayı sisteminde (Vlasov–Poisson) yapılar boyuta göre bölünür | Exp15 (doğrulanmış PIC): elektron delikleri 1B'de yalnız birleşiyor. 2B/3B'de kıvrılıp parçalanıp sönüyor; kalıcı bölünme 0–1. Eşik 1B↔2B (Morse & Nielson 1969 ile uyumlu); kuvvetli B kırılmayı bastırıyor. **Boyuta bağlılık var ama bölünme yok (yok olma); silikonda 4 K'de model geçersiz.** |
| H26 | Proje verilerinden seyrek regresyonla (PySINDy) denklem türetilebilir | Exp16: bilinen yasalar geri bulundu (Gray–Scott PDE ≤ %0,19; BSIM4 Chynoweth 90/90; HF −1,65335; BenDaniel–Duke). %1 gürültüde başarısız. Aday yasalar: R*₂B = 0,233 ε/ν₋ (LOO %3); filaman w = I/j_f, j_f = 2,55 µA/µm; fisyon g_c ∝ N^≈−1 (Exp8'deki "kapı üssü düzleştirir" yorumu desteklenmiyor). **Temiz simülasyon verisinde destekleniyor; gürültülü veride değil.** |
| H27 | Silikonda (SKY130 nFET, 4 K) dağıtık balastlı drenajlı geniş cihazda akım filamanı büyüyüp tekrar tekrar bölünür; bölünme genişliği cihaz sabitlerinden öngörülebilir | Exp17: genel ölçüt merkez V_D = V_down (merkez–kenar farkı = V_M − V_down). Tek filaman için w_s = 2λ ln[λ/(λ−λ_c)], λ_c = √(2(V_M−V_down)/(r_D j_on)); dizi için kapalı form (sınanmadı); w_top = I/j_on. Öngörüler önceden kaydedildi. Temiz protokolün 22 bölünmesinde oran 1,001 ± 0,069 (63 olayın tamamı Exp17 düzeltme kutusunda), iki farklı cihaz setinde 0,979 ± 0,133 (n = 9); 14 ilk bölünmede RMS %9 (Exp20 örtük çözücüyle 13/14 yeniden üretildi, RMS %8,6; G_rD5_lam80 artık tarama içinde bölünmüyor; geçerlilik dışı düşük sızıntı koşusu 1 s/adımda da ~2 kat geç bölünüyor); λ = 36 µm (eşiğin %1 üstü) ıskalandı. Fizik formu veriden tek katsayıyla uydurulunca kuramın 1,01 katı. Sınır: yarı statik sürüş gerekli (düşük sızıntıda gecikme). 2B parmak dizisinde (duvarlı ve duvarsız) leke bölünmüyor; yuvarlak → dambıl → solucan. Bölünme için 1B'ye hapsetmek gerekiyor. **Model düzeyinde güçlü destek (1B); tekrarlayan bölünme var; ölçülmeli. Kuantum değil.** |
| H28 | Akım filamanlarının doğum yeri kapı gerilimiyle programlanabilir | Exp18: hücre, kapı aşırı sürüşü en büyük tek hücrede doğuyor (kalibrasyon 19/20; önceden kaydedilmiş öngörü 77/80). 10 µm'lik +30 mV tohum ilk hücreyi 10/10 seçilen yerde doğurdu. Doğumda tek kazanan seçiliyor: WTA'da en güçlü giriş 8/10, iki eşit tohum birlikte 2/10; k-WTA beklentisi yanlıştı. **Model düzeyinde destekleniyor; ölçülmedi.** |
| H29 | Bilinçli hasar verilen bir hücre ayıklanıp yerine programlı bölünmeyle yenisi konabilir (yenilenme) | Exp18 v3 (yavaş ölüm): ölen hücrenin akımı sağlam hücrelere geçiyor, gerçek doğum yok (16/16); −150 mV'luk zayıf nokta komşuyu bölüyor, kız hücre boşalan yere yerleşiyor (3,3 V: 3 → 2 → 3); hareketli kapı deseniyle dışarı atma çalışıyor; 5,0 V'ta yenilenme kendiliğinden. Ani ölüm (v2) gerilim sıçramasıyla yeni hücre doğuruyor (anlık yük doğrusuna bağlı). İlk protokolün (v1) öngörülerinin çoğu tutmadı. **Model düzeyinde destekleniyor; ölçülmedi; tek rastgele alan.** |
| H30 | Ani bir akım değişimi, yavaş sürüşün tek kazanan kuralını kırıp birden çok hücre doğurur | Exp19: ani V_DD adımı, programlı 4 tohumdan kaç tanesinin hücre olacağını adım yüksekliğiyle belirliyor (≤ 1,0 V: 1; 1,05–1,1 V: 10/10 tam 2; 1,4 V: 10/10 dördü); yavaş tarama hep 1 (10/10); tohum dışı doğum yok. Hangi tohumların kazandığı en güçlü k ile örtüşmüyor (2–3/10; uçtakiler yeğleniyor), yani k-WTA değil. Ani ölüm yalnız 0,1 s'den hızlı ölümde yeni hücre doğuruyor. **Model düzeyinde kısmen destekleniyor; anlık yük doğrusu varsayımına bağlı; ölçülmedi.** |
| H31 | Toplam akımın ani zorla küçülmesi hücreleri eşzamanlı böler | Exp20 (örtük çözücü): kapı çukuru sırasında bölünme yok (12/12); bırakmadan 20 ms sonra 3,3 V'ta 3 → 3/5/6, 5,0 V'ta 3 → 5/6/7 (−20/−40/−60 mV, iki süre); ≥ 0,2 V V_DD düşüşünün ilk 20 ms'inde de bölünme (5,0 V 0,2 V: 3 → 4; 0,5 V: 3 → 6). Hücre payına dayalı eşik (D1) ✗; eşik payın 20–180 katı. **Model düzeyinde destekleniyor; mekanizma sonradan; ölçülmedi.** |
| H32 | Standart bölünme 300 K'de SKY130'da çalışır | Exp21: 300 K değerleriyle bistabilite yalnız tasarlanmış kuyu sızıntısıyla (pencere 43–68 mV, oran 5–12). Gerçek kuyu iletken → tek düğüm (R1 ✓); bağımsız hücrelerde uyumsuzluk → çekirdeklenmeyle çoğalma; 21 koşuda 0 bölünme. **Desteklenmiyor (bu modelde); bipolar kilitlenme yolu denenmedi.** |
| H33 | Elimizdeki veride (SKY130) kuantum durumu görülebilir | Exp22: alt bantlar çözücüde (300 K'de taban bantta %47–72; 4 K tek alt bant); resmî kart C–V'si klasiğin %2,4 altında (BSIM4 capMod 2, model düzeyi); tünelleme kartta kapalı. **Kısmen: yalnız model düzeyinde iz, ölçüm verisi yok. Ölçüm önerisi: C–V, elektrometreyle tünelleme, 4 K SdH, ≤ 1 K Coulomb.** |
| H34 | Programlanabilir hücre öldürülünce enerjisinin önemli bir kısmı kaybolur | Exp23: ölen hücrenin gücü kalanlara %98,5–102,3 geçiyor (muhasebe hatası 0); asıl kayıp mimari (yük direnci %75–83). **Desteklenmiyor: geri dönüşüm neredeyse kayıpsız.** |
| H35 | Bu hücrelerle atomlar programlanabilir | Exp23: hücrenin kendi enerjisiyle örgü atomunu oynatmak yok (V_M kenetlenmesi yapısal, 0,82 eV; eşikler 2–11 mertebe uzak); toplu yük durumu kontrolü var (~4400 B/µm). Exp24: gövdedeki atomlar gerilim adresiyle tek tek 0/1 (bkz. H37); konum/spin dolaylı yollarla (H38). **Ayrıştırıldı: doğrudan konum değiştirme hayır; yük durumu evet (model); konum/spin dolaylı evet (literatür + model).** |
| H36 | Programlanabilen hücre atom boyuna küçülebilir | Exp24: w ≥ max(2λ_c, ℓ_b, W_dep, ~36 nm, litografi); ℓ_b ≈ 2,2 µm (bu modelde) altında tohumla programlama kayboldu (λ_c 0,36 µm, 150 mV: 0/10, öngörü 10/10); atom boyutunda 2e-5 katkı. Oksitteki iyonik filaman hücresi ise KMC'de tek atom genişliğine iniyor; genişliği silikon hücrenin gövde gerilimi seçiyor (0,81–0,90 V: 1 atom, 0,95–1,00 V: 2 atom; IC1–IC3 ✓, IC4 ✗). **Silikonun elektronik filamanı için desteklenmiyor; iyonik filaman hücresi için model düzeyinde destekleniyor.** |
| H37 | Hücre gövdesine hapsolmuş tek tek doğal atomlar dışarıdan 0/1 yapılabilir | Exp24 atom atom Coulomb camı: her bor atomunun kendi anahtarlama gerilimi var; 100 nm gövdede ~94 atom anahtarlanıyor. Isıl sınama (Metropolis): ortalama doğruluk 4 K 0,82, 1 K 0,88 (kayıtlı ≥ 0,9 tutmadı); pay ≥ 8 kT/e gerekiyor. Hücrenin kendi penceresinde (0,805–1,006 V) güvenle programlanabilen atom: 1 K'de ~35/100 nm gövde, 4 K'de 0. Türetilen yöntem sınandı (SB1 ✓): 60 nm gövde, dengede kalibre adres ve ≥ 8 kT/e payla 4 K'de doğruluk ~%99, pencerede gövde başına ~3,3 atom. 40 nm'de adresler pencerenin dışına çıkıyor (SB2 ✗). **Model düzeyinde 4 K'de (60 nm gövde) ve 1 K'de destekleniyor; ölçülmedi.** |
| H38 | Atomun konumu ya da spini hücre üzerinden programlanabilir | ReRAM O-boşluğu zinciri ~1,2 G₀ (SKY130 ReRAM var; HfO₂ 4 K'de çalışıyor), tek atomluk temas (Schirm 2013; 10–50 µA = 3,9–19,5 µm hücre kolu), ³¹P çekirdek spini (7–42 MHz seçicilik; simülasyon: B = 1 T, 10 kHz Rabi ile hedef çekirdek P = 1,000000, komşularda ≤ 1,7·10⁻⁷, SP1–SP2 ✓). Konum: iyonik filaman KMC'si (4 K, SET 1,46 V'a kalibre) her yazmada 2–4 oksijen atomunun yerini değiştiriyor, genişlik 1–2 atom. **Spin ve konum: model düzeyinde destekleniyor (varsayımlar: n-gövdeli ayna hücre; KMC parametreleri); ölçülmedi.** |
| H39 | Hücre enerjisi istenen hücreye yönlendirilebilir | Exp25 E1: ölen hücrenin gücü %97–98 verimle geçiyor, ama payı yakınlık belirliyor (%73/%27); ±15–30 mV kapı ön gerilimi payı ±%4 değiştiriyor (EN2, EN4 ✗). **Kapıyla desteklenmiyor; geometriyle (doğum yeri) yönlendirme sınanmadı.** |
| H40 | Hücre alanı atomun enerji düzeylerini seçici olarak kaydırır | Exp25 E3 (Bradbury 2006 katsayılarıyla): 0,4–1,8 V/µm'de ³¹P aşırı ince 0,4–7,6 MHz, ESR 47–906 kHz kayıyor; çizgi genişliklerinden çok büyük. **Hesapla destekleniyor (literatür katsayıları); ölçülmedi.** |
| H41 | Alanla bağlı doğal atomlar evrensel mantık (NAND) kurar | Exp25: kalibre eşikle 27/28 üçlü, 9/10 adada dört satır ≥ 0,9 (4 K); her atomun alanı 30 nm içindeki hepsinde > kT. İlk yöntem 3/28 (LG1 ✗, pencere hatası). **Model düzeyinde destekleniyor; yerel kapı varsayımı; ölçülmedi.** |
| H42 | Programlanabilir merkez atom bütün komşularıyla etkileşir ve onları evrensel olarak yönetir | Exp25: ³¹P bütün yakın ²⁹Si'lerle etkileşiyor; doğal Si'de 10 kHz seçicilikle ~5 çekirdek tek tek yönetiliyor, elektron + 4 çekirdek GHZ 0,987 (seyircilerle). 100 kHz tasarımı tutmadı (RG1, RG4 ✗); güçlü komşuların yalnızca %1–3'ü (doğal Si) / %40–64'ü (%0,1–0,05 ²⁹Si) tek tek seçilebiliyor (RG5 ✗). Dolaylı global kontrol (Lloyd–Landahl–Slotine): Lie cebiri 3 çekirdekte 10/10, 4 çekirdekte genel yönlü B ile 10/10 tam (B ∥ [001]'de 7/10; CT1 kısmen ✗). Sıkışık (1 kHz) komşuya CNOT 0,999–1,000 (1500 yineleme; 400'de 0,989, CT3 ✗), 3 çekirdekli GHZ 1,000. Süre ~1/(bağ farkı): doğal Si'de en güçlü 10 komşu için ~0,8 ms. Her N için Vandermonde mekanizması: N = 6, 8 tam (hata ≤ 2·10⁻¹²). N = 10'daki 8/10 yalnız çift duyarlık sınırı. Kesin (kesirli) aritmetikle: N = 10 ve 20'de rank tam; N = 40'ta 1 eşit çift var (ters simetri eşi), N = 100'de 3 (2'si ters simetri eşi). 6 nm içindeki bütün ²⁹Si'ler ölçülmüş T2e (²⁸Si'de 2 s) içinde: 50 ppm'de %98, %0,1'de %75 (< 1 s); doğal Si'de hiç. **Bağı farklı bütün spinli komşular merkez atom üzerinden evrensel kontrol edilebilir; ölçülmüş eşevrelilikle seyreltilmiş ²⁸Si'de pratikte de; doğal Si'de değil (çekirdek yolu da ²⁹Si dimerlerinde takılıyor: H43). Model + kontrol kuramı + literatür; ölçülmedi.** |
| H43 | Doğal silisyumda merkez atomun bütün ²⁹Si komşularına (6 nm, ~2100) tek tek erişim ve evrensel kontrol mümkün | Exp26: adresleme mümkün (D+ yazma + yönü seçilebilen gradyan + MREV-16; her çekirdek bir yönde ≥ 0,015 nm yalıtılıyor, 20/20; L2 yasası doğrulandı; veri yolu bağlı, Lie rankı tam). Ama kesin çok-spinli benzetim (7 spinlik gerçek kümeler, Ladd'ın sonlu darbeli MREV-16'sı, t_c = 1,568 ms) depolamanın çöktüğünü gösterdi: tek bir 17,5 s yazmada bitlerin yalnız %31'i korunuyor; en yakın komşu ²⁹Si çiftleri (%17, \|J\| 52–574 Hz) ve onlara bağlı çekirdekler sızıyor (üç spin etkisi). Benzetim ölçümden iyimser (17,5 s'de 0,86 / ölçülen 0,50). 16× hızlı döngüde (uzatma) %94, ama çift üyelerinin %35'i hâlâ > 0,1. Önceki 'ölçülmüş değerlerle 6 nm'nin tamamı' ve '0,4 ms ile %99,995' iddiaları yalnız adreslemeydi, geri alındı. Ölçülmüş değerlerle kalan: D0 donmuş çekirdekle ~69 çekirdek (R_all ~0,8 nm), elektron kapılarıyla ~5. **Doğal Si'de ölçülmüş değerlerle desteklenmiyor; engel ²⁹Si dimerleri. Saflaştırılmış ²⁸Si'de destekleniyor (Exp25, 50 ppm'de %98). Ölçümle doğrulama (yayımlanmış deneyler): alanla tek atom programlama (Asaad 2020), donör elektronuyla tek ²⁹Si kontrolü (Pla 2014; doğal Si'de T2 6,3 ms, ²⁹Si banyosu), elektron + 2 çekirdek evrensel kapılar (Mądzik 2022: %99,95/%99,37), elmasta merkez + 9 çekirdek (Bradley 2019); 50 ppm'de bir donörün bütün spinli komşuları ~2 (%61'inde ≤ 2) yani ölçülmüş ölçekte; aynı yöntem elmastaki 27/8 küme boyutunu büyüklük düzeyinde veriyor; KL, Pla'nın 2,205 MHz sitesini vermiyor. Doğrudan ölçüm: Thorvaldson 2025 (3P + elektron, ~200 ppm ²⁸Si; bütün çekirdek çiftlerinde CZ %99,32–99,65, GHZ %96,2) ve Edlbauer 2025 (4P/5P kayıtları, bütün çekirdekler kontrollü, CZ %99,90, ²⁹Si sinyali yok): saflaştırılmış Si'de tek yapay atom bağlı olduğu bütün spinli komşuları evrensel yönetiyor. Sınanabilir: doğal Si'de MREV altında ~%17'lik hızlı sönen bileşen.** |
| H44 | Bölünen hücrelerin geri dönüştürülen enerjisi, vakum kontrolü (Casimir / dinamik Casimir) ve programlanabilir atomlarla metrik mühendisliği, kapalı bir araca roket denkleminin ötesinde itki verir (Vakum-Metrik Roket) | Exp27: enerji-momentum korunumundan β = tanh(η ln(M₀/M₁)), η = η_dön η_yön (tam adımlı sayısal sınama, korunum 1e-12); kapalı araçta F/P ≤ 1/c = 3,34 nN/W. Statik Casimir çevrimi tam sıfır iş (durum fonksiyonu). Dinamik Casimir: 1 GHz/1 nm ayna 4,5e-39 N/m², Wilson 2011 düzeyi ≤ 2,3e-21 N, hücreler 7e-78 N. Metrik: warp negatif enerjisi Casimir'le elde edilebilenden 39–71 mertebe büyük; kütleçekim dalgası itkisi 9e-39 N; her warp sürücüsü roket denklemine uyar (Bobrick & Martire 2021); EmDrive sıfır (Tajmar 2021). VR1 kısmen (sayısal eşik), VR2–VR5 ✓. **Desteklenmiyor: vakum ve metrik ayakları korunum yasalarıyla kapalı. Doğru kapı: η → 1 foton roketi (hücre geri dönüşümü + programlanabilir yönlendirme) ve dışarıdan ışınlanan güç (ışık yelkeni, F = (1+R)P/c).** |
| H45 | Bölünen hücrelerin pozitif enerjisi, programlanabilir atomlar ve yapay atomlarla, momentumu atomların taşıdığı bir itkiç kurulabilir ve foton/vakum sınırının çok üstüne çıkar | Exp28 (Exp0–27'nin bütün verisi, `data_registry.json`): F/P = 2η/v_e (atom) ile 1/c (foton) arası uçurum 2c/v_e ≈ 10⁴; denklem NSTAR'ı η = 0,61 ile veriyor; hücre = kuantumlu akım kanalı (I_c = P_c/V_M = 0,17–0,27 mA, Exp23/17), hücre başına 7–26 µN (In⁺ 1–5 kV), sayıyla basamaklı itki (Exp19/20), hücre ölümünde ≤ %0,8 (Exp23); Exp24 yayma yasası 4 K'de 10¹²⁶ aç/kapa; yapay atom turnikesi impuls biti 1,75e-20 N·s (Exp0–4); WKB vakuma tünelleme 3–21 V/nm (β ≥ 10³); 10 kg/100 W/2 kg In: 13,4 km/s, 1,9 yıl. Keşif: çip gerilimli nano aralık (önceden yüklü iyonlarla) 10⁴–10⁷ N/m², 170–450 µN/W; ortam atomlarıyla kütle oranı sınırı yok (v_e = v(1 + C_D/2εf_m), 200 km 330–660 W/m²); ışınlanan güç + atom yelkenin 1500–3000 katı. AR1–AR6, EX1–EX5: 8 ✓, 3 kısmen. **Model düzeyinde destekleniyor; hücreler 4 K ister (Exp21). Exp29: itki halkası F = γJ√(2mV/q) NEXT'in 40 ölçülmüş noktasında serbest parametresiz doğrulandı (kök ortalama kare %1,45); hücre halkası ölçülmedi.** |
| H46 | Exp28 atom + pozitif enerji denkleminin her halkası, girdisi ve çıktısı ayrı ölçülmüş yayımlanmış deneylerle serbest parametre olmadan doğrulanır | Exp29 (`predictions_exp29.json` 14:44, kör değil, açıklandı): MC1 NEXT 40 nokta (Diamant 2010 tezgâh; Pollard 2010 plüm γ): 40/40 ≤ 2σ, ortalama +%1,01, kök ortalama kare %1,45 (≥ 1000 V'ta %1,18) ✓; artık β'nın V_b ile kötüleşmesini izliyor. MC2 Ca⁺/CaO⁺ uçuş süresi oranı √m: 1,1953 ± 0,0061 vs 1,1833 (1,97σ, sınırda ✓). MC3 istek üzerine tek iyon 123/139, algılama sınırlı ✓ (Schnitzler 2009). MC4 I = e·f 0,27 ppm ✓ (Zhao 2017). MC5 gerilimle taşınan oksijen (SiOx) vakum yayımını 50/130 ns'de açıp kapıyor ✓ (Wu 2018; ikili, elektron). MC6 SKY130 hücreleri ölçülmedi. Exp28 AR1 bir özdeşlikti (düzeltildi). **Denklem ölçümle doğrulandı; hücre halkası için 4 K akım basamağı ölçümü gerekiyor (itki tezgâhı gerekmez).** |
| H47 | Exp0–Exp27'nin her sonucu bağımsız bir ölçümle kapanır; alanla denetlenen atom yayımıyla gerçek itki Exp28 denklemine uyar | Exp30 (`predictions_exp30.json` 14:56, çapalar okunmadan önce): 28 sonuç → 9 ✓, 5 ✗ (Exp1 kapasitans 1,7–3,8×; Exp6 eşleşmezlik 3,5–5,6×; Exp22 alt bant; Exp25 GHZ; Exp26 eşevrelilik), 5 karışık, 6 ölçüm yok (Exp13, 14, 17, 19, 20, 23), 3 yöntem. İndiyum FEEP (Mühlich 2022): doğrudan itki, denklemle %1,6–4,3 içinde ✓; yayan iğne sayısı akımla artıyor (1/28 → 28/28). Düzeltmeler: oda sıcaklığı tek elektron adası ölçümde ~2 nm (model 0,4 nm); hücre mekanizması sınıfı 180 nm CMOS'ta 30 K'de var, 40 K'de yok. **Bütün veri ölçümle kapandı; ölçülmemiş tek katman silisyum hücre yasaları (laboratuvar).** |
| H48 | Hücre yasaları (Exp13, 14, 17, 18, 19, 20, 23) ölçülmüş akım filamanlarının yapısıyla tutarlıdır | Exp31 (`predictions_exp31.json` 15:14, kör değil, açıklandı): Mamanee 2012 (TU Wien, silisyum ESD, 300 K, TIM): sabit N'de j sabit (%0,1 / %5,2) ✓; N = I/(0,75 j w_s) ölçülen aralıklarda (0,84–0,90×) ✓; tek filaman sınırı 0,889 A ≈ 0,9 A ✓; j N ile −%22 ✗; bölünme, eşit paylaşım, tohumla doğum yeri, kısa darbede daha çok filaman ✓. V₂O₃'te akım düşüşüyle çoklu filaman (Lange 2020; mekanizma farklı); aktif damlalarda sıvı kabuk (Bergmann 2023). Son sayım Exp0–27: 13 ✓, 7 karışık, 5 ✗, 3 yöntem, 0 ölçüm yok. **Yapı ölçümle destekleniyor; SKY130'a özgü sabitler (j_on, V_M, 4 K) ölçülmedi.** |
| H49 | SKY130'un kendi 4 K ölçümü hücre mekanizmasını destekler; tutmayan modeller ölçümle düzeltilip bağımsız veriyle doğrulanır | Exp32: NIST mds2-2997 (SKY130 ETest, 4 K, Agilent 4156B) + aynı aygıtın 300 K verisi: kink 4 K'de var (W7/L0,15 oran 2,77; 10/10 aygıt), 300 K'de yok (1,15) ✓; kink başlangıcı 1,25–1,525 V (kayıtlı 0,6–1,2 ölçütü ✗). Ölçülmüş M (BSIM4×10 varsayımı 7–22× fazlaydı) ve ölçülmüş transfer eğrisiyle V_M = 0,70 V, j_on = 64 µA/µm, w_s 20–54 µm, I_c 1–2,6 mA. Düzeltmeler: ada öz-kapasitansı Shin'i %3,3 ile öngörüyor (C1 ✓); Pelgrom–PDK 1,24–1,49× (C2 ✓); alt bant çözücüsü ✗ (C3). Son durum: 16 ✓, 6 karışık, 3 ✗ (Exp22, 25, 26; itki denklemine girmiyor), 3 yöntem. **Kilitlenmenin kendisi geniş SKY130 aygıtında doğrudan ölçülmedi; histerezis verisi yok.** |
| H50 | SKY130 hücresinin 4 K gövde girdileri (gövde etkisi, gövde diyotu, kink yükseltimi) NIST ham verisinden ölçülebilir ve Exp12 BSIM çapalarıyla tutarlıdır | Exp33 (`predictions_exp33.json`, hesaptan önce): gövde etkisi ters yönde ölçüldü — \|dVT/dVB\| medyan 0,105, BSIM4 300 K çapasının (~0,32) yaklaşık üçte biri ✗ (C33-1); gövde diyotu ölçülemez (4 K IDVG'de IB sütunu yok, VB > 0 yok, C33-2); kink yükseltimi medyan 1544 (475–6333) ✓ (C33-3); 4 K'de kilitlenme basamağı yok (44 tarama), kayıtlı ölçüt 300 K taban artefaktıyla ✗ (C33-4); bütün taramalar tek yönlü, histerezis veriden ölçülemez (C33-5). Geniş/balastlı laboratuvar koşusunun protokolü ve hedefleri kaydedildi (V_M 0,701 / V_down 0,639 / V_up 2,323 V — V_up anma üstünde, tohum şart). **İleri-yön gövde etkisi laboratuvar öncesi en kritik ölçülmemiş girdidir; vekil duyarlılık V_M'yi 1,15 V'a, j_on'u 0,85 µA/µm'ye kadar kaydırabilir.** |
| H51 | Bütün veriden (Exp0–Exp33) optimize edilen itki zarfı, ölçülmüş itki çekirdeğini bozmadan nano-aralık ön-yüklü rejimde ~400–525 µN/W ve görev dizinde NSTAR düzeyinde F/P verir | Exp34 (`predictions_exp34.json`, ızgaradan önce): iç optimum V* = V_M + E_giris/e ✓ (EMI⁺ 523,8 µN/W @1,70 V, Isp 175 s); fizibil optimum yayma sınırında 392,7 µN/W @8,4 V, Isp 388 s (UT2 kısmen — gereken uç beta 5,28 çıktı, kayıtlı ≥50 maddesi denklem lehine falsifiye oldu); CL yoğunluğu 3,06·10⁷ N/m² (UT3 kayıtlı aralığı 10³ kat düşüktü ✗ — tasarım güç/ısıl sınırlıdır, yoğunluk sınırlı değil); diz: In @1195 V, 39,9 µN/W, Isp 4570 s, Δv 10 km/s (UT4 kısmen); hücre beslemesi gövde bandında I_c 0,33–2,60 mA (UT5 kayıtlı biçimiyle ✗, s=0,33 çekirdeği tuttu); NEXT kapanışı aynen korunur (UT6 ✓, RMS %1,45). Zarf: R1 nano-aralık, R2 hücreli kV, R3 soluma, R4 ışınlama (yelkenin 29.431 katına kadar). **Yayma hızı tarafı ve hücre kilidi fiziksel ölçüm bekler.** |
| H52 | Ortak sayım–kalibrasyon–yaz–oku–düzelt yığını, hücre ve atom katmanlarında keyfî çok elemanlı desenleri tam kontrol eşiğine taşır | Exp35 (öngörüler hesaptan önce; v1 örnekleyici/MONO yönü hatası nedeniyle geçersiz arşivlendi, düzeltilmiş v2 + v3): tek küresel sürüş MONO'da 7/7 ama ALT+RAND'da 0/14 modal başarı verir (UC1 ✓); sabit çalışma noktalı yerel/geri besleme yetmez (v2 CL20 zor desenlerde marjinal 0,756, tam desen 0,357, modal 5/14); küresel düzeltimli CL20M ve tavlamalı CL20A bütün görevlerde 21/21 modal başarıya ulaşır (ALT+RAND marjinal 0,992/0,994, tam desen 0,973/0,980; UC3.2/3.4/3.6 ✓). Kalibreli bağımsız-bit ölçeklemede ≤3 doğrulama denemesi N=100 için 0,990 verir (UC5 ✓). **Bu, seçilmiş hedef altkümesinde model içi tam kontroldür: analog ortalama okuma ve idealleştirilmiş yerel alan kipleri varsayılır; hedef dışı modal çevrilme %6,25–6,29 ile kayıtlı %5 izolasyon sınırını aşar, fiziksel laboratuvar kontrolü yapılmamıştır.** |
| H53 | Yeterince ince yüzey-dilimi alan çekirdeği, arka-plan cezalı aktüatör ve gürültülü tek-atış geri beslemeyle seçilmiş atom desenlerinde toplam hata bütçesini kapatır | Exp36 (beş ayrı kayıtlı öngörü sürümü): 15 nm SEG4'te skaler ceza/aktif güvenlik Pareto sınırı aşılamadı (v2 SS1 marjinal 0,960/modal 13/14 ama arka plan %6,00; v4 arka plan %2,22 ama 0,777/6/14). 10 nm SEG6, SS1 (%1 tek okuma) ve SS5 (%5 üçlü çoğunluk) altında 0,982/0,981 marjinal, 13/14 modal ve %4,70/%4,75 toplam arka planla kayıtlı tam-kontrol kuralını geçti; 7,5 nm SEG8 iki protokolde de 14/14 ve %3,95/%4,21 verdi (RY1–RY4, RY6 ✓; derinlik ilk-fark biçimi RY5 ✗). **Model düzeyinde destekleniyor; çekirdek Gauss/derinlik-zayıflamalı vekildir, RAND sınıfı arka planı %9,2–10,4 ile desen başına %5'i aşar, sensör/dedektör fiziği ve laboratuvar kontrolü ölçülmedi.** |
| H54 | Exp36 atom denetleyicisinin gerçek zamanlı çekirdeği, katsayı çözümü ana bilgisayarda bırakılarak sentezlenebilir çip RTL'sine indirgenebilir ve AutoChip/Icarus geri beslemesiyle doğrulanabilir | Exp37: yerel AutoChip + Icarus 12.0 doğrulandı; sağlayıcı API anahtarı olmadığından tam LLM üretim döngüsü temiz eksik-anahtar hatasıyla durdu. Kayıtlı isteme göre yazılan `exp36_atom_ctrl` (ilk düzeltme hesabı, 1+36 DAC akışı, SS1/SS5 çoğunluk-onay mantığı, ±30 mV güncelleme ve ±220 mV doyma, resolve el sıkışması, 20-tur zaman aşımı) AutoChip `check_verilog` rankında 1.000 ve 0/194 hata aldı; STEP/onay mutasyonları 0,954/0,892'ye düştü, SEG8 NSEG=64 elaborasyonu geçti, VCD/SVG/HTML üretildi (AC1–AC7 ✓). **RTL/model düzeyinde destekleniyor; LLM üretimi yapılmadı, Yosys/OpenLane/SKY130 fiziksel kapanışı ve analog DAC/sensör/laboratuvar ölçümü yoktur.** |
| H55 | Exp36/37 atom denetleyici RTL'si SKY130 HD hücreleriyle sentezlenebilir ve global yerleştirilebilir; SEG8 alan bedeli iki katın altında kalır | Exp38 (S1–S6 kayıtlı): SEG8 tam testbench AutoChip rank 1.000 ve 0/250; Yosys 0.69 ile tt 1,80 V sentezde SEG6 27.545 µm²/2.440 hücre/541 FF, SEG8 41.474 µm²/3.367 hücre/877 FF (oran 1,506), kara kutu/kilit yok; SEG6 kapı netlisti FUNCTIONAL SKY130 modelleriyle 0/194; OpenROAD floorplan+global placement DEF/ODB ile tamam (307 µm kalıp, %30 kullanım, overflow 0,099). **Sentez/global-yerleşim düzeyinde destekleniyor; ayrıntılı yerleştirme/CTS/routing/STA/GDS, SEG8 kapı simülasyonu ve fiziksel çip ölçümü yoktur.** |
| H56 | Denklem 1 (tam bütün) `ε=sqrt(1-β²)=m0c²/E=m0c²/(hν)=0,1^n` biçiminde genelleştirildiğinde γ=10^n katsayısı nonilyona ulaşırken hız c altında kalır; Exp34 iyon gemisi bu merdivenin ilk basamağına kendi yakıtıyla ulaşamaz | Exp39 (D1–D7 kayıtlı, tümü PASS): n=1'de γ=10, β=0,994987; n=30'da γ=10^30 (1 nonilyon) ve 1−β=5×10^-61. 10→8 kg yanışta EMI/In diz/In 5 kV son Δv değerleri 0,85/10,0/20,5 km/s ve ε>0,999999997; n=1 için log10R In dizde 8.696, foton alt sınırında R=19,95 (referans 1,25). 8 kg için n=1 kinetik enerjisi 6,47×10^18 J ve kayıpsız 100 W tedariki 2,05×10^9 yıl; tek In `hν` dalga boyu n=17,856'da Planck boyuna iner. Yazılı `E=-mc²` dalı oran olarak −10^-n verdiği için pozitif eşitlikle işaret çelişkisi taşır; tanımsız `f(r_s)` itkiye bağlanmadı. **Özel-görelilik modeli içinde destekleniyor; negatif dal mevcut biçimiyle reddediliyor; laboratuvar motoru/fiziksel uzay gemisi sonucu değildir.** |
| H57 | Denklem 1 grubunun `hν` hattı (Denklem 2) birim boyutunu koruyarak Planck ölçek rejimlerine iner, fakat denklemin kendisi uzamsal boyut değiştirmez | Exp40 (V1–V6 kayıtlı, tümü PASS): `m0c²/(hν)` her n için boyutsuz ve en büyük artık 3,33×10^-16. Eşik sırası elektron/proton/indiyumda Planck enerjisi → λ=r_s → λ=ℓ_P olup Planck-boyu n değerleri 23,176/19,913/17,856; 10^-18 m değerleri 6,385/3,121/1,064. `λ_h/λ_dB=β`; n=1'de foton momentumu %0,503 fazla. 8 kg tek-kuantum varsayımı n=0'da Planck boyunun 1,71×10^-8 katında kalır. Denklemde kompakt boyut yarıçapı/bağlaşım yoktur; varsayımsal KK katmanında geometrik ve enerji eşikleri 0,798 dex ayrılır. **Ölçek inişi destekleniyor; uzamsal ek boyuta geçiş denklemden gözlenmiyor ve kanıtlanmıyor.** |
| H58 | Hedefsiz serbest hızlı bir sanal laboratuvarda sonlu iyon gemisinin son hızı gaz profilinden bağımsız, dış beslemeli sabit öz-ivmeli test kütlesinin hızı ise c'ye asimptotik ve enerji faturasıyla sınırlıdır | Exp41 (G1–G6 kayıtlı, tümü PASS): Exp34 EMI/In diz/In 5 kV hatlarında tam/%25/rampa/darbe profilleri aynı son Δv=0,850/10,001/20,455 km/s değerlerini verdi (yayılım <8×10^-9); yalnız yanış süreleri değişti. Dış beslemeli 1g tezgâhta γ=10 okuması 2,900 öz-yıl/9,639 Dünya yılı, In λ=ℓ_P okuması 40,499 öz-yıl/6,948×10^17 Dünya yılı ve γ=10^30 okuması 67,588 öz-yıl/9,687×10^29 Dünya yılında oluştu; 8 kg enerjisi son okumada 7,190×10^47 J ve anlık dış güç 1g'de 23,5 GW'a doydu. Hareket Planck göstergesinde düzgün kaldı. **Sanal laboratuvar modelinde destekleniyor; dış besleme fiziksel gemi/ laboratuvar motoru değildir.** |
| H59 | Bir ³¹P merkez atomu çevresinde seçilmiş örgü siteleri ²⁹Si'ye çevrilirse, tekdüze rastgele izotop bolluğunun spektral kalabalık–dimer ödünleşimi kırılabilir ve model düzeyinde evrensel bir yapay atom kurulabilir | Exp42 (I1–I7 kayıtlı; I4 olumlu yönde FAIL, ötekiler PASS): B\|\|[123] aday havuzu 18.784 site. ISO_CODE K=8, 155,8 kHz en küçük geçiş boşluğu, 158 kHz en küçük \|A\|, 21,2 Hz en büyük J, 0,665 nm en küçük çift uzaklığı, tam A² Vandermonde rankı ve 0,0063 ms ayırma süresi verdi; rastgele eşleştirilmiş medyan boşluk 0,360 kHz ve tam adresleme 0/200, en güçlü siteler dejenere bağlarla boşluk=0 verdi. K=4 dört B yönünde Lie 1023/1023; GHZ 0,99987 (T2e=10 ms'de 0,96763). K=8 800 ppm artık ²⁹Si'de en az 7/8 çekirdeği %99 olasılıkla korur; %1'de medyan 7/8 (I4'ün ≤6 öngörüsü olumlu yönde tutmadı). Kayıtlı evrensel-atom başarı kuralı true. **Model içinde destekleniyor; tek-site izotop yerleştirme, KL bağ hatası, K≥8 darbe sentezi ve laboratuvar üretimi açıktır.** |
| H60 | Exp42 izotop kodu üretim hatalarına karşı ancak üretim-sonrası spektroskopi/yeniden kalibrasyonla dayanıklıdır; önceden sabitlenmiş kod ve darbeler toplu yerleştirme hatasında evrenselliğini kaybeder, fakat doğru yerleştirilmiş kodun kapı ve depolama katmanı güçlüdür | Exp43 (J1–J7 kayıtlı; yalnız J6 PASS): tek-site R=0,50 nm hatada K=8 tam kod 0,487 ve kaymış çekirdeğin nominal darbe çevirmesi medyan 1,30×10^-4; toplu Gauss σ=0,25 nm/eksen tam kodu 0/1000 yapar (medyan 3/8, 30 kHz). Bağ hatası daha yumuşaktır (σ_lnA=0,50'de tam kod 0,469; J2'nin ≤0,30 öngörüsü FAIL). B-yönü yeniden ayarı medyan boşluğu ×2,06 yapar ama tam kodu 0'dan kurtaramaz. 20 µs GRAPE nominalde 1,000000 ve dayanıklı toplulukta 0,999424 verir, ancak dikdörtgen zaten 0,998048 olduğundan J5 kazanç eşiği FAIL. Kesin 256-boyut depolamada D0 en kötü sızıntı 1,20×10^-9; D+ serbest 0,99933 iken ölçülen MREV-16 2,55×10^-4'e ezer (J6 PASS). **Önceden sabit kod hipotezi üretim hatası altında reddedildi; uyarlanabilir üretim-sonrası kod seçimi gerekli. Laboratuvar üretimi yoktur.** |
| H61 | En güçlü nominal siteleri aşırı örnekleyip üretim sonrası en iyi sekiz ²⁹Si çekirdeğini seçmek, seçilmeyen izotopları seyirci olarak bırakmak koşuluyla evrensel yazmacı kurtarır | Exp44 (U1–U7 kayıtlı; yalnız U6 PASS): hedefli σ=0,50 nm bulutlarda tam K=8 30-kHz başarı M=16'da 0,010, M=32/64/128'de 0; M=64 medyan boşluk 0,578 kHz ve bulutun kendisinde bireysel adreslenebilir çekirdek medyanı 3. Tekdüze aday ve doğal bulutlarda da tam kod 0; doğal adreslenebilir medyanı 2 (U6 PASS). Ölçüm hatasında nominal/dayanıklı seçiciler tam kod üretemedi. Seçilmiş–seyirci NN olasılığı M=64/128'de %83/%91 ve medyan en büyük seyirci J yaklaşık 365 Hz. Finalist yoktur; uyarlanabilir başarı kuralı false. **En-güçlü-hedef aşırı örnekleme hipotezi reddedildi. Sonraki aday, az sayıda spektral katmanlı hedef ve seyirci maliyetini içeren üretim-sonrası seçimdir.** |
| H62 | Az sayıda spektral katmanlı hedeften implantasyon yapıp üretim sonrası seyirci-cezalı yeniden seçim uygulamak, en güçlü hedefleri aşırı örneklemekten daha yüksek verimli bir evrensel ²⁹Si yazmacı verir | Exp45 (S1–S7 kayıtlı; S4 ve S7 PASS, ötekiler FAIL): nominal spektral boşluk M=16/24/32 için 53,6/23,4/10,0 kHz; tam K=8 başarısı σ=0,10 nm'de M=16'da %49,5 ile tepe yapar, σ=0,25 nm'de bütün M değerlerinde ≤%1,0'a çöker. Bütün 45.214 siteden tekdüze M=256 bulutta adreslenebilir medyanı 2 ve tam kod 0. Seyirci-J cezası NN oranını %46'dan %26'ya indirir (S4 PASS) ama medyan korunan çekirdek 3/8 kalır; B retune yalnız ×1,30. Tek finalist (M=24, σ=0,25, gerçekleşme 102; 1/200) K=8 koşulları, K=4 Lie 1023/1023, 20 seyircili GHZ 0,99697/0,96488 ve D0/MREV depolama denetimlerinden geçer (S7 PASS), fakat kayıtlı %20 verim kuralı false. **Hipotez üretim yöntemi olarak reddedildi; σ≈0,10 nm ve M≈16 çevresinde dar bir model penceresi vardır. Sonraki aday, yer değiştirme dağılımına göre olasılıksal/minimax hedef tasarımıdır.** |
| H63 | Yer değiştirme dağılımında yerel düz kalan sitelere ²⁹Si hedeflemek ve medyan bağlara göre spektral bölmeler kurmak, nominal spektral koda göre üretim verimini artırır | Exp46 (T1–T7 kayıtlı; T1,T5 PASS, ötekiler FAIL): σ=0,25 nm'de 8.891 güçlü siteden ortak düzlük ölçütünü (P≥0,80 ve q10–q90 yayılımı ≤0,50) geçen **0** site; medyan yayılım 3,25 ve medyan P=0,458. Eğitimde STOCH M16 ortalama adreslenebilir sayısı 2,98 iken Nominal45 M16 3,67; bağımsız testte STOCH M16 σ=0,10/0,25'te %0/%0, Nominal45 %46,0/%0. Kesin C(16,8) arama açgözlü seçiciyi 100 bulutun yalnız 1'inde ≥1 çekirdek iyileştirir; medyan fark 0 ve all-8 iki yöntemde %0 (T5 PASS). Finalist yok, başarı kuralı false. **Yerel-düz/medyan tasarım sınıfı reddedildi; darboğaz seçici değil bulut içeriği ve yerleştirme kesinliğidir.** |
| H64 | 30 kHz katı spektral eşik yerine şekilli π darbelerinin gerçek çapraz konuşma bütçesi kullanılırsa, σ=0,25 nm yerleştirme hatasında bile evrensel ²⁹Si yazmacı çift haneli verimle seçilebilir | Exp47 (R1–R7 kayıtlı; R3,R7 PASS, başarı kuralı **true**): RECT/GAUSS/HANN kesin iki-düzey haritada Δ=10 kHz ve T=500 µs çapraz konuşma 1,10×10⁻² / 3,72×10⁻⁶ / 2,85×10⁻⁵. NOMINAL M16 σ=0,25'te taban all-5/all-10/all-30 %22,0/%5,5/%0,5 iken HANN500 darbe-uygun verim %17,5 ve GAUSS500 %21,0; σ=0,10'da HANN500 %85,0. İlk finalist (gerçekleşme 2) en küçük boşluk 13,76 kHz, K=4 Lie 1023/1023, 12 seyircili GHZ 0,99965 ve T2e=10 ms'de 0,90908; D0 sızıntı 1,20×10⁻⁸. Kesin eşik araması all-5'i %23'ten %62'ye çıkarır (R4 FAIL): taban seçici düşük eşikte darboğazdır. **Model içinde destekleniyor; 500 µs darbeler T2e'ye duyarlıdır ve laboratuvar/GRAPE doğrulaması yoktur.** |
| H65 | Darbe-uygun çekirdekleri önceden hesaplayıp kesin klik seçimi yapmak, spektral seçimden sonra darbe uygunluğunu ölçmekten çok daha yüksek evrensel-yazmaç verimi verir | Exp48 (W1–W7 kayıtlı; W1,W2,W5,W6 PASS, başarı kuralı **true**): M16 σ=0,25 nm'de GAUSS500 uygun medyanı 9; kesin verim %61,5 ve HANN500 %50,0 iken taban %18,5/%12,5. GAUSS1000 kesin %88,5 fakat yazmaç-içi K=4 şekilli GHZ T2e=10 ms'de 0,83515; GAUSS500 finalisti Lie 1023/1023, GHZ 0,99998/0,90935 ve D0 sızıntı 1,24×10⁻⁶. Açgözlü verimde 3,5 puan yakın ama medyan sürede kesinden ~40× yavaş (W3 FAIL); M24 açgözlü %88,5 ile M16 kesini aşar (W4 FAIL); σ=0,50 kesin GAUSS500 %48,5 (W7 FAIL). Bütün-bulut K=4 seçici A≈0 seyirci seçerek GHZ'yi 0,251 yapar; yazmaç-içi çekirdek kusuru değildir. **Model içinde destekleniyor; kalibrasyon/KL hatası ve tam K=8 kapı sentezi açıktır.** |
| H66 | Çarpımsal bağ ölçüm hatasına karşı 2σ aralıklarla en-kötü-durum darbe seçimi ve ±500 Hz taşıyıcı köşeleri, GAUSS500 evrensel yazmacını dayanıklı kılar | Exp49 (X1–X7 kayıtlı; tamamı FAIL, başarı kuralı false): INTERVAL uygun medyanı σ_meas=0,05/0,10/0,25'te 3/1/0'a çöker ve hiç seçim bulamaz; NOMINAL gerçek verim %61,5→%38,0→%32,5→%23,0 ile yumuşak bozulur, MARGIN10 neredeyse aynıdır. Uygulama verimi bütün yöntemlerde %0'dır çünkü ±500 Hz kaymada GAUSS500 hedef çevirmesi 0,9280'dir; 0,99 için kaba ızgarada en büyük kayma 180 Hz. Kayıtlı dayanıklı finalist yoktur. Exp48 finalistinde tanı K=8 GRAPE nominalde ~1,000000 ve dayanıklı toplulukta en kötü 0,99648 verir (hükme sayılmaz). **Aralık temsili ve kalibresiz basit darbe hipotezi reddedildi; sonraki model hat frekanslarında toplamsal Hz belirsizliği ve hedef-başına kilitlemedir.** |
| H67 | Spektroskopik belirsizliği hat frekanslarında toplamsal Hz hatası olarak temsil edip hedef başına taşıyıcıyı kilitlemek, çarpımsal A aralıklarının çöküşünü kaldırır ve GAUSS500 yazmacını dayanıklı kılar | Exp50 (Y1–Y7 kayıtlı; Y4,Y7 PASS, başarı kuralı false): NOMINAL_F gerçek verimi σ_f=100/200/500/1000 Hz'de %57,0/%56,0/%54,0/%50,5 kalır ve INTERVAL_F uygun medyanı 500 Hz'de 7'dir; fakat LOCKED verim σ_f=100'de ~%28–30, 200 Hz'de ~%0'dır çünkü sekiz hedefin artık hatasının aynı anda ~180 Hz çevirme penceresinde kalması gerekir. COMMON500 her yerde 0. Kayıtlı finalist true-only'dir; yazmaç-içi K=4 Lie 1023/1023, GHZ 0,99999/0,90936 ve D0 4,88×10⁻⁶ (Y7 PASS), GRAPE dayanıklı en kötü 0,99889 fakat nominalden fark +0,00956 (Y6 FAIL). **Temsil düzeltmesi destekleniyor; basit GAUSS kilitleme hipotezi reddedildi. Sonraki kaldıraç çevirme penceresini genişleten GRAPE-duyarlı seçimdir.** |
| H68 | Ortalama topluluk skoruyla optimize edilen evrensel X-only GRAPE darbeleri, geniş hedef çevirme penceresi ile 5–10 kHz seyirci bastırmasını aynı anda sağlar | Exp51 (Z1–Z7 kayıtlı; tamamı FAIL, başarı kuralı false): ROBUST500 W99=710 Hz fakat titreşim zarfında P(5 kHz)=0,118 ve P(10 kHz)=0,095; ROBUST200 W99=250 Hz ve P(5 kHz)=0,032. Topluluk ortalama/en-kötü skorları 0,97365/0,65187 ve 0,93972/0,49398. İki darbede de uygun çekirdek medyanı 0, seçim ve bütün verimler %0; eşleştirilmiş GAUSS500 Exp50 değerlerini birebir doğrular (σ_f=200 gerçek %56,0, LOCKED %0,5). Finalist yoktur. **Ortalama-skor evrensel tasarım reddedildi; seyirci bütçesi sert kısıt/minimax olarak temsil edilmelidir. Bulut-hedefe özgü GRAPE başarısı (Exp49/50) bu sonuçla çelişmez.** |
| H69 | Yumuşak-minimum (minimax) veya seyirci log-bariyer amacıyla optimize edilen evrensel X-only darbeler, ±1 kHz hedef aralığında tekdüze çevirme ile 2 kHz'den başlayan seyirci bastırmasını 500–750 µs ve 5 kHz sınırda aynı anda sağlar | Exp52 (AA1–AA7 kayıtlı; tamamı FAIL, başarı kuralı false): softmin en kötü sistem skorunu Exp51'in 0,652 değerinden MINIMAX500'de 0,886 ve MINIMAX750'de 0,919'a yükseltti, fakat sıfır detuning çevirmeleri 0,960/0,939 olduğundan W99=0 Hz; titreşim zarfı P(5/10 kHz) MINIMAX500'de 0,0813/0,725. BARRIER500 yakın seyircileri 0,0027/0,0025'e indirdi ama hedef çevirmesi 0,464'e düştü. Üç evrensel yöntemde de eşleştirilmiş uygun medyanı ≤1, seçim ve bütün verimler %0; GAUSS500 tabanı Exp51'i birebir doğruladı. Finalist yoktur. **Amaç-fonksiyonu düzeltmesi en kötü durumu iyileştirdi ancak %99 tekdüzeliği bu süre/genlik/pencere şartlarında zaman-bant genişliği fizibilite sınırının dışında kaldı; evrensel darbe hattı bu şartlarda kapandı. Sonraki adım fizibilite sınırı taraması veya hedefe özgü GRAPE'dir.** |
| H70 | Evrensel X-only darbede tekdüze ≥0,99 bölgesi, genlik sınırından çok süre×hedef-pencere zaman-bant genişliği ürünüyle açılır; kullanılabilir köşe ±250 Hz pencerede ~1000 µs'dir | Exp53 (AB1–AB7 kayıtlı; AB2,AB4,AB6,AB7 PASS, başarı kuralı **true**): 27 hücrenin 12'si ≥0,99. 5 kHz sınırda en kötü skor ±250 Hz'de 500/1000/2000 µs için 0,961/0,996/0,999; ±1000 Hz'de 0,803/0,970/0,992 (AB1'in kapalı-köşe öngörüsü FAIL). Genlik 5→20 kHz skoru ≤~0,02 değiştirdi; 20 kHz/500 µs (0,821) 5 kHz/2000 µs'yi (0,992) yakalayamadı (AB3 FAIL). Monotonluk ihlali 0. En iyi hücre W250/B5/T2000: W99=420 Hz, zarf P(5 kHz)=3,82×10⁻⁴ ama P(2 kHz)=0,0247. T2e=10 ms koherans kalanı 1000/2000 µs'de 0,905/0,819. **Model içinde destekleniyor: fizibilite sınırı süre eksenindedir; seçim verimi/GHZ bu deneyde ölçülmedi, 2 kHz zarf sızıntısı ve T2e bedeli açıktır.** |
| H71 | Ayrık örneklenen seyirci topluluğunda fizibil olan evrensel darbe (Exp53 W250/T1000 köşesi), titreşim zarfı uygunluğuyla eşleştirilmiş seçimde de kilitli verimi kurtarır | Exp54 (AC1–AC7 kayıtlı; yalnız AC5 PASS, başarı kuralı false): FRONTIER1000 sıfır çevirmesi 0,99957 ve W99=380 Hz olmasına rağmen zarf P(5/10/30 kHz)=0,0943/0,0362/0,0992; uygun medyanı σ_f=200'de 1 ve bütün verimler %0. FRONTIER2000 evrensel darbeler arasında ilk sıfırdan büyük kilitli verimi verdi (σ_f=200'de gerçek %3,5, kilitli %2,5; GAUSS kilitli %0,5) fakat zarf P(2 kHz)=0,0247 ve eşiklerin çok altında; finalist yok. **Hipotez reddedildi: optimize edici örneklenen detuningler arası çentikleri kullanıyor; fizibilite iddiası zarfın kendisi topluluğa katılmadan seçim aşamasına taşınamaz. Sonraki adım zarf-duyarlı (komşuluk en-kötüsü) topluluk optimizasyonudur.** |
| H72 | Üç parametreli (a,b,k0) Kohn–Luttinger zarfının çok-kabuk ENDOR kalibrasyonu bağ hatasını giderir ve Exp48 ana verimi kalibre modelde korunur | Exp56 (AE1–AE5 kayıtlı; AE1,AE4,AE5 PASS, başarı kuralı false): mevcut KL (1,1,1) oranında %13,8 ama (3,3,1)'de %49,0 hatalı (Ma vd. Commun. Phys. 5,165 Şek.3 deney oranları). Fit sınırlara dayandı (a=1,20, b=2,50), (3,3,1)'i %22,7'ye indirirken (1,1,1)'i %67,7'ye bozdu; güçlü sitelerin %86,4'ü %50'den çok değişti (Spearman 0,608). Aynı 200 bulutta GAUSS500 kesin verim %61,5→%54,5 (−7 puan). Exp42 ISO_CODE boşluğu 155,8→22,3 kHz çöktü. Kayıt dışı tanı: alt-örgü Bloch fazlı genişletme dört oranı %3,3 içine soktu ama a üst sınırda/k0f=0,789 ile aşırı uyum şüphesi taşıyor. **Kalibrasyon hipotezi bu zarf ailesiyle reddedildi; verim dayanıklılığı ve önceden tasarlanmış kodun kırılganlığı nicel olarak sabitlendi. Sonraki hesaplar iki modeli belirsizlik aralığı olarak taşımalı.** |
| H73 | Sayılmış tek-iyon implantasyonu, Crystal-TRIM gerçekçi saçılmasında (σ≈10 nm) bile üretim-sonrası darbe-duyarlı seçimle çift haneli evrensel yazmaç verimi verir | Exp57 (AF1–AF6 kayıtlı; AF1,AF4,AF5 PASS, başarı kuralı false): verim σ=5 nm'de N=64/256/1024 için %0/%8/%49; σ=10 nm'de %0/%0/%3; σ=20/40 nm'de her N'de %0. Seyreltme mekanizması ölçüldü: σ=10, N=256'da güçlü çekirdek medyanı 5, uygun medyan 2. Deterministik sayım (≥%99,87 güven) yerleşim saçılmasını telafi etmiyor; darboğaz donör dalga fonksiyonu boyutuna karşı σ oranı. **Hipotez bugünün saçılma değerleriyle reddedildi; yol σ≲5 nm sınıfında veya izotop-mühendisliği seyreltik banyosunda açıktır. Laboratuvar implantasyonu yapılmadı.** |
| H74 | Exp38 SKY130 SEG8 tasarımı açık araçlarla tam fiziksel kapanışa (PDN, CTS, yönlendirme, STA, GDS) taşınabilir | Exp58 (AG1–AG6 kayıtlı; AG1,AG2,AG4,AG5 PASS, başarı kuralı **true**): OpenROAD tam akışında DRT ihlali 3655→0, WNS +40,25 ns @100 ns TT, TNS 0, alan 49.608 µm² (%36), güç 0,874 mW; KLayout ile 6,87 MB GDS üretildi. KLayout DRC 130 öğe (tamamı m3.6). AG3 FAIL: 21 net anten ihlali kaldı, bu OpenROAD derlemesinde repair_antennas GRT-0069/çökme veriyor. AG6 FAIL: LVS raporu üretildi ama eşleşme yok (araç çıkışı 1). Ölçüm protokolü önceden-tanımlı 4 K başarı ölçütleriyle yazıldı. **Fiziksel kapanış büyük ölçüde tamam; tape-out, IO halkası, çok-köşe STA ve laboratuvar ölçümü yapılmadı.** |
| H75 | Yoğun log seyirci ızgarasıyla zarf-duyarlı optimize edilen evrensel darbe, kilitli verimi çift haneye çıkarır | Exp55 (AD1–AD7 kayıtlı; AD2,AD3,AD6,AD7 PASS, başarı kuralı false): ENV1000 çevirme 0,99942/W99=350 Hz, zarf P(5/10 kHz)=1,18×10⁻⁴/3,8×10⁻⁵ ama kötü bölge payı %43,4. σ_f=200'de gerçek/kilitli verim %5,0/%2,0 (ENV2000 %8,5/%3,0; GAUSS kilitli %0,5). Hat ilk kilitli finalistini verdi (gerçekleşme 71): yazmaç-içi Lie 1023/1023, GHZ 0,999997/0,90936 (T2e=10 ms), D0 sızıntısı 4,7×10⁻⁸. **Hipotez verim eşiğinde reddedildi ama mekanizma doğrulandı: çentik oyunu kapandı, darboğaz 1–2 kHz geçiş bandı zarfı ve 350 Hz pencereye karşı σ_f=200 Hz artık hatası.** |
| H76 | Seyreltik epitaksiyel ²⁹Si banyosu + sayılmış donör + üretim-sonrası darbe-duyarlı seçim, gösterilmiş üretim teknolojisiyle çift haneli evrensel yazmaç verimi verir | Exp59 (AH1–AH6 kayıtlı; AH5,AH6 PASS, başarı kuralı **true**): verim bollukla monoton — %0,05/0,08/0,1/0,25/0,5/1 için %0,5/0,5/1/8/26/51. 800 ppm gösterilmiş epi noktası yetersiz (%0,5); %0,5 kasıtlı katkıda %26 ve dört denetimi geçen finalist (Lie 1023/1023, GHZ 0,999993/0,90936, D0 3,1×10⁻¹⁰). İç optimum %1 üstünde; banyo T2e bedeli modellenmedi. **Model içinde destekleniyor: implantasyon saçılmasına (%3) karşı epitaksiyel banyo, gösterilmiş teknolojiye dayanan ilk kayıtlı-başarılı üretim yoludur. Fiziksel üretim/ölçüm yapılmadı.** |
| H77 | Alt-örgü Bloch fazlı genişletilmiş KL modeli fiziksel k0 kısıtıyla da kabuk oranlarını tutar ve ana verimler model aralığında kalır | Exp60 (AI1–AI5 kayıtlı; AI3,AI5 PASS, başarı kuralı false): k0f=0,85 sabitli fit R331'de %43 hatalı (AI1 FAIL, b üst sınırda). Yalnız-deney fiti tutulan LMTO oranlarını %3/%17 ile öngördü (AI5 PASS). EXT_DIAG altında Exp48 verimi %61,5→%86 (AI2 FAIL — aralık yukarı aşıldı), banyo f=%0,5 verimi %26→%69 (AI3 PASS); Spearman 0,390 (AI4 FAIL). **Hipotez reddedildi: zarf biçimi (saf üstel) muhtemelen yanlış, etkin k0 kayması bunu emiyor. Projenin bütün verim sayıları bundan böyle aralık olarak okunmalı (Exp48 %54,5–86; banyo %26–69) ve eski KL muhtemelen kötümser tarafta.** |
| H78 | Spektral seçim + hedefe özgü GRAPE doğrulaması, kilitli uygulama verimini evrensel darbelerin %2-3 bandından nominal seçim düzeyine çıkarır | Exp61 (AJ1–AJ6 kayıtlı; **tamamı PASS**, başarı kuralı **true**): 20 bulutta GAUSS kesin = spektral aday = GRAPE-doğrulanmış = %65; denenen 104 hedefin tamamı ±400 Hz köşeler + %2 ölçek topluluğunda çevirme ≥0,99 ve seyirci tutunması ≥0,999 verdi (medyan en-kötü çevirme 0,9975). Finalist (bulut 2): Lie 1023/1023, GHZ 0,999983/0,90935, D0 9,3×10⁻⁸. Kazanç seçimden değil kilitli uygulamadan geliyor. **Model içinde destekleniyor: kalibrasyon darboğazının çözümü evrensel darbe değil, ölçülen hatlara sentezlenen hedefe özgü GRAPE'tir. XY genlik hataları ve çok-cisim dinamiği modellenmedi; laboratuvar ölçümü yok.** |
| H79 | Epitaksiyel banyo verimi yüksek bollukta kalabalıklaşmayla döner ve etkin (T2e-fiyatlı) optimum %0,5–2 aralığında, verim ≥%40 ile GHZ kalitesi ≥0,85'i birlikte sağlayan bir noktada oluşur | Exp62 (AK1–AK6 kayıtlı; AK2,AK4,AK5,AK6 PASS, başarı kuralı false): verim %2'de %69, doğal bolluk %4,7'de %66 (AK1 FAIL); uygun medyan 9/9 (AK3 FAIL). İki çapalılı T2e(f) modeliyle Q: %0,5/1/2/4,7 için 0,8659/0,8224/0,7354/0,5006; üç yeni finalist Lie 1023/1023. Kalabalıklaşma hipotezi reddedildi, darboğaz eşevresizlik: verim ≥%40 olan hücrelerde Q<0,85, etkin optimum %0,5 (%26). **Sonraki hatlar dinamik ayrıştırmalı GHZ (T2e kazancı), hücre-içi Q dağılımı ve atomistik bağ modeli; fiziksel üretim/ölçüm ortam dışı.** |
| H80 | Donor elektronundaki CPMG dinamik ayrıştırması, banyo T2e darboğazını açarak %1–2 bollukta verim ≥%40 ile GHZ kalitesi ≥0,85'i birlikte veren bir çalışma noktası oluşturur | Exp63 (AL1–AL6 kayıtlı; **tamamı PASS**, başarı kuralı **true**): T2(N)=T2e(f)·N^(α/(α+1)) filtre-ölçeklemesi ve (1−ε)^N darbe maliyetiyle α=2, N=64, ε=10⁻³ altında Q63 f=%1/%2 için 0,9250/0,8900 (verimler %51/%69). Darbe hatası tavanı ölçüldü (Q(N=512)<Q(N=64); ε=10⁻² kapalı); doğal bolluk kurtulamıyor. Kayıt notu: N=0 doğrudan-üstel değerlendirmesi Exp62 enterpolasyonundan daha serttir (0,7057 vs 0,8659); hükümler sert modelle verildi. **Model içinde destekleniyor (α=2 koşuluyla); dizi sentezi ve laboratuvar ölçümü yok. Sonraki hatlar yankı-içi kapı dizisi sentezi ve atomistik bağ modeli.** |
| H81 | Çok-demelli implantasyon + ölç-seç-kalibre mimarisi (Atom Litografi Makinesi), ürün modunda (epitaksiyel banyo + implant donor) günde ≥10⁴ sertifikalı evrensel yazmaç üretir ve hız yazmadan çok ölçümden sınırlanır | Exp65 (AN1–AN6 kayıtlı; **tamamı PASS**; başarı kuralı Mod A bacağında **false**): merkez senaryoda (10⁶ demetcik, 10⁴ okuma kanalı) Mod B f=%1 2,20×10⁸/gün, Mod A σ=10 nm bile 1,26×10⁷/gün — paralellik kötü verimi de ürüne çevirdiğinden kuralın Mod A<10⁴ bacağı tutmadı. Ayırt edici hız değil maliyettir: Mod A σ=10 yazmaç başına ~17 kat spektroskopi, ~17.500 kat atış tüketir; yavaş-spektroskopide ayrım 17 kata çıkar. **Mimari düzeyde destekleniyor (model içinde); paralel okuma kanalı sayısı gösterilmiş teknoloji değildir. Sonraki hatlar Exp66 hata bütçesi ve Exp67 kapalı-çevrim kazancı.** |
| H82 | EUV-sınıfı konumlandırma (maglev kademe + aktif sönümleme + interferometri) makine hata bütçesini implant saçılma zemininin altına indirir; Mod A bu sınıfta ≤10 keV'de çift haneli verime ulaşır | Exp66 (AO1–AO5 kayıtlı; **tamamı PASS**, başarı kuralı **true**): RSS bütçesinde EUV sınıfı 10 keV'de σ_toplam 5,53 nm (saçılmanın 1,11 katı) ve Exp57 eşlemesiyle %32,6 verim; 5 keV'de 3,82 nm/%49 (tavan). Kaba sınıf 12,5 nm ile her enerjide ~%2. En büyük ekipman terimi demet noktası; tavlama terimi ikincil. **Model içinde destekleniyor; saçılma çapaları varsayımdır (SRIM ölçeği), laboratuvar ölçümü yoktur. Sonraki hat Exp67 kapalı-çevrim kazancı.** |
| H83 | Sayılmış-iyon algılaması + spektroskopik yeniden deneme kapalı çevrimi, kör dozlamaya göre yuva başarısını ≥3 katına çıkarır ve kazanç η=0,9 algılama veriminde de korunur | Exp67 (AP1–AP5 kayıtlı; **tamamı PASS**, başarı kuralı **true**): G (η=0,99, s=0,5) B f=%0,5 6,19; B f=%1 4,69; A σ=10 7,87; A σ=5 4,80. η=0,9'da G≥5 korunur (B f=%0,5 6,0); η=0,5 deneme verimini %33 eritir. Alan maliyeti ≤1,6 alt-yuva/yazmaç. Kazanç en çok düşük verimli hücrelerde — kapalı çevrim, zayıf atış fiziğinin telafisidir. **Model içinde destekleniyor; s ve b varsayımdır. Sonraki hat DESIGN v2 ve Exp68 DD şartname çevrimi.** |
| H84 | Makinenin DD işletim şartnamesi tek sağlam bolluğa iner: f=%1 her iki banyo gürültü üssünde (α=1 ve 2) fizibil kalırken f=%2 yalnız α=2'de açıktır ve ε=10⁻² darbe hatası f≥%1 hücrelerini kapatır | Exp68 (AQ1–AQ5 kayıtlı; AQ1–AQ3 PASS, başarı kuralı **true**): fizibil N aralıkları ε=10⁻³'te f=%0,5 8–256 (iki α), f=%1 64–256 (iki α), f=%2 yalnız α=2, f=%4,7 hiçbiri. AQ4 FAIL: ε=10⁻²'de f=%0,5 N=8'de 0,8695 ile hayatta; AQ5 FAIL: f=%2 optimumu N=128 (düz tepe). Şartname: ürün bolluğu f=%1, N=64–128, ε≤10⁻³. **Model içinde destekleniyor; laboratuvar ölçümü yok.** |
| H85 | Exp58 kontrol çipinin açık anten ihlalleri ve LVS eşleşmesi mevcut açık araçlarla kapanır | Exp64 (AM1–AM5 kayıtlı; yalnız AM5 PASS, başarı kuralı false): repair_antennas bu OpenROAD derlemesinde STA-0327/GRT-0069 ve segfault ile kanıtlı bozuk. Netlist'e diyot ön-ekleme 21→13 nete indirdi; tur 2 ve ODB-ECO yeniden yönlendirme çalkantısıyla 17/16 nette kaldı — sıfır yok. LVS: tek sınıf farkı 1794 tap hücresi; çıkarma sonrası da KLayout deck'i eşleşmedi. netgen çapraz kontrolünde bütün hücre alt devreleri tekil eşleşiyor, üst devre çıkarımda VPWR/VGND birleşmesi nedeniyle açık: kök neden Exp58 DEF→GDS üretimi. **Hipotez bu araç zinciriyle reddedildi; kapanış güncel OpenROAD/OpenLane hattı gerektirir (DESIGN R5 açık). Tape-out/ölçüm yok.** |
| H86 | Sayısal çok-vadili etkin-kütle zarfı (tek parametre bağlanma fitli), analitik KL'nin ENDOR kabuk hatasını fiziksel k0'da onarır | Exp69 (AS1–AS6 kayıtlı; AS1 FAIL, AS2–AS6 PASS, başarı kuralı false): kayıtlı fit kaba ızgarada −45,6 meV'a ulaşmadı (E=−28,75 meV). Sayısal zarf KL hatasını aynen üretiyor (R331 %48,8'e karşı %49,0; R111 %13,6; Spearman 0,978; ızgara yakınsak). Tanı taramasında merkez-hücre derinleşmesi R331'i büyütüyor, A≥6 ızgara çökmesi. EMT verimi %58,5 ile ortak bantta. **Hipotez reddedildi: hata zarf biçiminde değil Bloch/alt-örgü fiziğinde; kesin çözüm atomistik TB/DFT gerektirir (DESIGN R1 açık, mimari ölçüm-sonrası seçimle dayanıklı).** |
| H87 | Frekans-çoğullamalı ESR okuması Exp65 merkez senaryosundaki 10⁴ paralel kanalı 4 K ısı bütçesi içinde besler | Exp70 (AR1–AR4 kayıtlı; **tamamı PASS**, başarı kuralı **true**): Δ=1 MHz'de zincir başına 2000 yazmaç; merkez 5 zincir/40 mW (%4 bütçe); fast_all 10⁶ kanal 4,0 W ile kapalı. **Senaryo fiziği (kayıtlı varsayımlar); tek-atış okuma sadakati ayrı boşluk (S6.7).** |
| H88 | Sayılmış implantasyonda bağlayıcı demet kısıtı uzay yükü değil kaynak parlaklığıdır; σ=2 nm şartı LMIS sınıfı kaynak gerektirir | Exp71 (AT1–AT4 kayıtlı; **tamamı PASS**, başarı kuralı **true**): B_gerekli(2 nm, 10 mrad)=4,06×10⁴ A/m²/sr (plazma 10¹–10² yetersiz, LMIS 10⁶ içinde); gevşek nokta 56 kat kazandırır ama Exp66 şartıyla çelişir. Child–Langmuir payı ~10⁻¹⁰. **BOM S1.1 R&D sınıfına çevrildi.** |
| H89 | IBIC sayılmış algılaması küçük kapasiteli piksel diyotla η≥0,99'a ulaşır ve büyük alanlı diyot şartı kaçırır | Exp72 (AU1–AU4 kayıtlı; AU2 FAIL, başarı kuralı **true**): η(10 keV, 0,5 pF)=1,0000 (model); 5 pF'de 0,9217 (0,9 şartı geçer, 0,99 hedefi kaçar — AU2 öngörüsü tutmadı). 8σ eşiğinde bile ≥0,95. **Şartname: C≤0,5 pF piksel diyot.** |

## Açık / sonraki deney adayları
- Hücreler arası tünel bağlaşımıyla koherans (hiçbir deneyde yok).
- Çoğalma fiziği Exp11'de modellendi (disipatif: Gray–Scott, aktif damla). Silikon karşılığı açık: 4 K darbe iyonlaşması filamanları (H22), e-h damlaları.
- Poisson-Schrödinger öz-uyum döngüsü ve çok-elektron etkileri (şu an tek-parçacık, bağımsız).
- <1 nm için atomistik yöntem (tight-binding / DFT); sürekli ortam burada geçersiz.

| # | Kod | Hipotez / Özet | Kaynak | Durum |
|---|---|---|---|---|
| H90 | 2bj | Anten ihlalleri yönlendirme pertürbasyonuyla (met3 cezası/yoğunluk) kapanmaz; üç koşu 13/17/15 net çalkalanması verdi. Kapanış repair_antennas gerektirir (bu derlemede bozuk) → araç zinciri güncellemesi şart | Exp74 (AW1-AW3) | SUPPORTED |
| H91 | 2bk | Bloch alt-örgü faktörü q=1 simetri kilitlidir (tersinim+zaman tersinimi+Delta aynaları); (3,3,1) ENDOR güçlenmesi Bloch periyodik kısmından gelemez — eksik fizik vadiler-arası merkez-hücre karışımıdır | Exp75 (AX1-AX6) | SUPPORTED |
| H92 | 2bl | Literatür çapraz kontrolü: sayılmış implantasyon %99,87 (IBIC) yayınlanmış durumda; ikincil-elektron sayımı %82 (P) yedek mod; PF2+ molekül iyonu Mod A adayı; blanker dizisi LSI kontrolü üretim teknolojisi — makinenin özgünlüğü kapalı çevrim + seçimde | LITERATURE.md 2026-10-20 | SUPPORTED |
| H93 | 2bm | Blanker karosu (64 kanal) SKY130 P&R kapatıyor: DRC temiz, WNS +7,21 ns @100 MHz, 0,140 mm2, 24,2 mW; anten (106 net) ve reset agaci entegrasyon maddeleri | Exp76 (AY1-AY4) | SUPPORTED |
| H94 | 2bn | Karo anteni diyot on-eklemeyle 106->70 net: strateji tavani ~\%35, cokme yine calkalanma; sifir kapanis bu arac derlemesinde yok (Exp64/74/77 uclu tekrar) | Exp77 (AZ1-AZ4) | SUPPORTED |
| H95 | 2bo | Altin oran: uretim olcum tavaninda analitik denge ~10 demetcik; pratik bant 10^3-10^4 demetcik ayni uretimi verir, maliyetin \%79u sabit tabanda (kafa kucultme tavani ~\%40) | Exp78 (BA1-BA5) | SUPPORTED |
| H96 | 2bp | Dis veri (NuFlare 32 um adim + PI piezo kademe) altin bandi uretim geometrisiyle hizalar; CAD-Recode hatti patent hucresinden STEP uretti (chamfer 0,056); maglev->piezo degisimi BA4u kapatir (\%60,3->\%55,1) | Exp79 (BB1-BB5) | SUPPORTED |
| H97 | 2bq | Zarf kucultme orani doyurur: olceklenen kalemler \%77 duser ama altin oran \%52,7de kalir; kalan kaldirac olceklenmeyen sabit kalemlerdir | Exp80 (BC1-BC4) | SUPPORTED |
| H98 | 2br | Exp71 plazma yetersiz hukmu birim/tanim artefaktidir: duoplazmatron parlakligi (fabrika 10 mA/cm2den turetilen) sartin 7,8 kati; S1.1 D->C ile altin oran \%45,5 | Exp81 (BD1-BD4) | SUPPORTED |
| H99 | 2bs | Duoplazmatron enerji yayilimi kromatik butceyi asar (6 eV/Cc=1mm: 6,09 nm); 2 eV enerji suzgeci parlaklik marjindan odenerek Exp66 kosulunu geri getirir (5,60 nm, \%31) | Exp82 (BE1-BE4) | SUPPORTED |
| H100 | 2bt | Tum-maliyet (enerji suzgeci + PH3 guvenlik dahil) altin oran \%45,65 ve mutlak tasarruf \%44,6; uc MCP zinciri (SysON 31 arac dahil) bu makinede calisiyor | Exp83 (BF1-BF2) + gozlem kayitlari | SUPPORTED |

## H101 (Exp84, 2026-10-20) — Plaka rezonansı + SysML kısıtı

Kalkan plakası kesiti modal: f1=2,59 MHz (analitik 2,68 MHz, oran 0,97) — servo bandından 3 mertebe yukarıda. Exp66 yüklemi SysON SysML kısıtına bağlandı (SpotBudgetInt): süzülmüş PASS (+0,404), çıplak FAIL (−0,089). Araç bulgusu: mcp-syson çıkarıcısı LiteralRational ayrıştıramaz; tam sayı sabit kullanılmalı.

durum: desteklendi (tahminler_exp84 öncesi kayıtlı; BG1–BG3 PASS)

## H102 (Exp85, 2026-10-20) — Altın bedelin iç yapısı

Exp83 altın bedeli (2599,77 birim) ayrıştırıldı: baskın terim S6.6 spektroskopi
elektroniği (1000, %38,5); sabit taban 1595 (%61,3), kafa+karo %0,2. Mutlak
üretim hedefi 10^6 kayıt/gün ile asgari bedel 1599,9 (referansın %28,1'i),
sabit pay %99,7 — %45,65'lik oran azami-ölçek referansa görelidir. Sabit
taban 18 düz C kalemden platon; BH4 (ilk-5 >= %40) FAIL kayıtlı (%31,7):

durum: karışık — BH1/BH2/BH3 desteklendi, BH4 reddedildi (tahminler öncesi kayıtlı)

## H103 (Exp86, 2026-10-20) — Hız koşu bandı, sınıf kolu

2B altın taraması: spektroskopi hızı göreli oranı iyileştirmez, kötüleştirir
(2 s'de 0,4389; 2 ms'de 0,4593; 20 µs'de 0,9824) — BI1/BI2 FAIL kayıtlı.
S6.6 sınıfı D->C ise oranı 0,3524'e indirir (BI3 PASS). Hedef fonksiyonu
göreli oran değil mutlak hedefte mutlak bedeldir (Exp85).

durum: karışık — BI1/BI2 reddedildi, BI3 desteklendi (tahminler öncesi kayıtlı)

## H104 (Exp87, 2026-10-20) — Zincir-basamak spektroskopi maliyeti

Rezonatör paketleme: hat başına 24 kanal (Q=100). Altın ölçek 375 zincir
(S6.6 D sınıfı haklı), ürün ölçeği 2 zincir. Zincir modeliyle altın oran
0,6035; mutlak hedef bedeli 1619,8 birim — doğrusal model iki yönde de hatalıydı.

durum: desteklendi (BJ1-BJ4 PASS; tahminler öncesi kayıtlı)

## H105 (Exp88, 2026-10-21) — Anten kapanışı kısmi: 106->20

ornew OpenROAD da ayni derleme; repair_antennas cokmesi tekrarlandi (BK1 FAIL).
Uç tur blanket diyot (toplam 933): 68 -> 37 -> 20 net; sifir kapanis yok
(BK2 FAIL). Alan +%1,6, bagimsiz STA WNS 7,21 ns (BK3 PASS). Kalan 20:
10 diyotlu inatci (cfg_data bus), 9 yerlesim-churn, 2 saat neti. R5 acik;
kapanis güncel OpenROAD veya CTS kisiti gerektirir.

durum: karisik — BK1/BK2 reddedildi, BK3 desteklendi (tahminler öncesi kayıtli)

## H106 (Exp89, 2026-10-21) — STA RC gerçeği

set_layer_rc (tech-LEF türevi) WNS'i oynatmadi (7,21 -> 7,21; x100 probu da
ayni): global-routing parazitikleri zaten tech-LEF RC kullaniyor; CTS-0104
sifir-RC yalniz CTS ic modeline ait. BL1 FAIL kayitli; zamanlama kapanisi
(BL2) ve saat carpikligi 140 ps (BL3) PASS. Gercek SPEF icin OpenRCX kurali gerekir (yok).

durum: karisik — BL1 reddedildi, BL2/BL3 desteklendi (tahminler öncesi kayıtlı)

## H107 (Exp90, 2026-10-21) — Birleşik GDS üretildi

klayout (PyPI; conda rotasi BM1 FAIL kayitli) ile r3 DEF + hucre GDS
birlestirildi: 23,4 MB, tepe blanker_tile, kalip 636,13 um birebir,
101/101 hucre tipinde DEF ile ornek mutabakati (fark yalniz via hucreleri).
BM2/BM3 PASS. DRC destesi kosulmadi (sonraki kapi).

durum: karisik — BM1 (rota) reddedildi, BM2/BM3 desteklendi

## H108 (Exp91, 2026-10-22) — Bağlaşım istatistiği: yerleştirme hatası J'yi dekatlarca dağıtır

Donör çiftinin değiş tokuş bağlaşımı yanal hatayla 0,444 dekat/nm·σ_xy yayılır (girişimsiz, düzlem içi; MC ile %2 içinde).
Kullanılabilir çift oranı p*₃ (3 dekatlık pencere), erişilebilir senaryolarda (Exp66 yanal σ × Holmes ölçekli σ_z): EUV sınıfı 5/10/20 keV
0,587/0,447/0,296; 1 dekatlık pencere için 0,216/0,158/0,102. Kare kafes ağı p_bond > 0,5'te süzülür; yalnız EUV 5 keV (W = 3, tam
aktivasyon) kayıtlı kuralı sağlar (en büyük küme %87; p_act = 0,7'de %9). Dipolar bağ yerleştirmeye dayanıklı (p* ±0,5 dekat 0,64–0,93,
ağ her senaryoda süzülür) ama R₀ = 30 nm'de ≈ 1 kHz (geçit ≈ 255 µs, T2e·f ≈ 1,2–2,2). Kırılganlık (kayıt dışı): M3 0,482, derinlik ×2 0,462.
Vadi girişimi σ ≳ 4 nm'de p*'yi ≤ 0,02 değiştirir; kristal yönü etkisi kaybolur.

durum: karışık — kayıtlı öngörülerin 7/13'ü PASS (BN0–2, 9–12); BN3–BN8 reddedildi; başarı kuralı SAĞLANDI (öngörü YANLIŞ'tı); öngörüler kör değildi (disclosure kayıtlı); bağımsız denetim 16/16

## H109 (Exp91_budget_attack, 2026-10-21) — 5 keV iç optimum: sigma 3,58 nm

P91 calisma noktasi (5 keV, suzgec 2 eV, Cc 0,5 mm, nokta 1,5 nm, tavlama
0,5): sigma_toplam 3,58 nm, Mod A verimi %49 tavani. Parlaklik ve IBIC
kapilari gecti; sertifikali uretim 6,05e5/gun (1000x1000). Enerji taramasi
ic optimum: altinda kromatik, ustunde sacilma buyur. BN1-BN4 PASS.
Not: H108 paralel oturumun Exp91_coupling_statistics kaydidir; bu giris
numara cakismasini onlemek icin H109'a alinmistir.

durum: desteklendi (model icinde; sacilma capalari varsayim)

## H110 (Exp92, 2026-10-21) — BCA saçılma çapaları doğruladı

Ev yapımı BCA (ZBL + LSS): yanal sigma 5/10/20 keV'de 3,26/4,87/7,50 nm
(Exp66 capalari 3/5/9; sapma +%9/-%3/-%17). P91 toplamı 3,80 nm. Sacilma-
only optimum 3 keV ama IBIC eta orada coker (0,13 @0,5pF): tespit fiyati
5 keV optimumunu korur. BO1/BO2/BO4 PASS, BO3 FAIL kayitli.

durum: karisik — BO3 reddedildi, digerleri desteklendi

## H111 (Exp93, 2026-10-21) — Kristal BCA kanalizasyonu ölçemedi

Iki kosu da kontrolu (7 derece egim) gecemedi: sigma_x <110> 1,84 vs egim
1,88 nm — eksen etkisi yok; dusus carpisma istatistigi artefakti. BP1/BP4
bicimsel sayilari BP3 kontrolu yuzunden gecersiz; basari kurali FAIL.
Kanalizasyon sorusu acik: eszamanli carpisma/sicim modeli gerekir.

durum: reddedildi (yontem yetersiz; soru acik)

## H112 (Exp95, 2026-10-21) — Kanalizasyon imzası (düzlem-doğru BCA)

Duzlem-dogru sacilma duzeltmesiyle eksen imzasi belirdi: sigma_x <110>
1,46 / 7deg 1,51 / 25deg 1,90 nm; Rp 8,44/8,12/5,71 nm. BR1/BR2/BR4 PASS;
BR3 FAIL: 25deg kontrol amorfun -%42sinde (duzlemsel kalinti + sema farki).
Mutlak kalibrasyon acik; P91 amorf 3,80 nmde kalir. Basari kurali FAIL.

durum: karisik — imza desteklendi, kalibrasyon reddedildi

## H113 (Exp96, 2026-10-22) — Kanalizasyon kalibrasyonu kapanmadı; hat durur

Rastgele-yon toplulugu 2,09 nm (amorf 3,26, -%36): BS1 FAIL. Oksitli kanal
1,844 nm kil payi BS2 FAIL. Goreli imza kalici (Rp 6,82 vs 4,53). Iki
ardisik kalibrasyon basarisizligi sonrasi alt hat durduruldu; P91 amorf
3,80 nmde kalir. Kantitatif kanal = Crystal-TRIM sinifi motor (ortam disi).

durum: reddedildi (basari kurali); goreci imza not edildi

## H114 (Exp97, 2026-10-22) — KLayout DRC: tek kalan sinif m3.6

Debian KLayout 0.30.0 ile sky130A.lydrc, tek-tepe GDS uzerinde 301 sn'de
tamamlandi: toplam 234 oge, tamami m3.6 (min met3 alani 0,24 um2) via inis
saplamalari; genislik/aralik/kuyu siniflari sifir. BT1-BT3 PASS. Yogunluk
desteleri ve anten (destede yok) kapsam disi.

durum: desteklendi (BT1-BT3 PASS)

## H115 (Exp98, 2026-10-22) — m3.6 yaması: 234 -> 0, yan etki 13 m3.2

GDS duzeyi cokgen buyutme (312 cokgen, delta 0,06 um) m3.6 sinifini sifirladi;
toplam DRC 234 -> 13 (%-94), yeni sinif yalniz m3.2 aralik (13). BU1-BU3 PASS.
Yama yalniz GDSde; ODB ile ECO farki kayitli.

durum: desteklendi

## H116 (Exp99, 2026-10-22) — Aciklik-duyarli yama v2 basarisiz

Cokgen basina azalan delta + orijinal met3 bolgesine 0,30 um separation_check:
309/312 kabul (%99,0). DRC tekrarinda toplam 57 (56 m3.2 + 1 m3.6):
BV1 FAIL (1), BV2 FAIL (57), BV3 PASS. Tani: kontrol orijinal geometriye
karsiydi; komsu iki kucuk cokgen ayni anda buyutunce birbirlerinin
araligina girdi (kenar-cifti ~0,29 um). Duzeltme Exp100: birikimli kontrol
(her kabul others bolgesine eklenir), buyukten kucuge siralama.

durum: curutuldu (yon: birikimli siralama)
## H117 (Exp100, 2026-10-22) — DRC ana deste sifira kapandi: oracle + blob semantigi

H116 tanisi duzeltildi: Exp99 betigi zaten birikimliydi; gercek kok nedenler
(1) Region.separation_check (Euclidian dahil) kayik kenarlarda 0,29 um
ihlali goremez - sentetik mikro-test; guvenilir oracle sisirme testidir.
(2) Deste birlestirilmis (merged) geometriyle calisir: 312 ham kucuk sekil
= 234 kucuk blob (Exp97 m3.6 sayisiyla birebir). (3) Carve genislik (m3.1)
uretir; delta-offset genislik-guvenlidir, son 3 blob tek-yon sweep ile
kapandi. Sonuc: sky130A.lydrc toplam 0; BW1-BW4 PASS; katman sayimi birebir.
Yama yalniz GDSde (ECO borcu durur); yogunluk desteleri + LVS siradaki kapi.

durum: desteklendi
## H118 (Exp101, 2026-10-22) — Kapılar: mr 0, LVS MATCH; tek açık: li1 yoğunluğu

Yogunluk destesi (azami kaplama): li1 ca_density 0,338 < 0,40 (FAIL, 102
oge tek kural li1.pd.1d; asal etken 46,3 bin decap); metal katmanlari rahat.
Blok duzeyi siniflandirma: GDS yamasiyla giderilemez, entegrasyon maddesi.
Bagimsiz mr destesi (FEOL+BEOL+offgrid+floating, 261 kategori): toplam 0 -
Exp100 kapanisi capraz dogrulandi. LVS: sema kaynagi final.def (r3.v bayat);
anahtarlar lvs_sub=VGND + convert_subckts + scale + schematic_simplify;
VNB->VGND donusumu; aygitsiz uc fiziksel tip (fill/tap/diode) sema disi.
Yamali ve yamasiz MATCH (99/99 devre); cikarilan envanterler birebir
(60492 eleman) - Exp100 yamasi elektriksel olarak notr. BX1 FAIL nedeniyle
deney basari kurali FAIL; cihazin kalan blok-duzeyi acik kapisi li1 yogunlugu.

durum: desteklendi (BX1 haric)
## H119 (Exp102, 2026-10-22) — li1 yogunlugu decap dozuyla kapanir (esik %14)

li1 alaninin %70,9u decap_4 (46.309 ornek). decap_4 ile fill_4 ayak izi
birebir (LEF 1,840x2,720). Ornek degisimi doz-yaniti: f=0 -> ca 0,338;
%15 -> 0,405 (gecer); %25 -> 0,450; %50 -> 0,561; %100 -> 0,783.
Dogrusal esik f* ~ %13,8. f15 varyantinda ana deste yine 0 (349 sn).
BY1-BY4 PASS. Kapsam: GDS duzeyi calisma; uretim cozumu akista decap
oranini sinirlamak (LVS/DEF tutarliligi orada korunur). Blok duzeyi
tuem EDA kapilari (DRC ana+mr, yogunluk, LVS) artik olculmus durumda;
kalan aciklar ortam disi (anten 20 net icin guncel OpenROAD, SPEF icin
OpenRCX kurallari, ECO geri tasima, M1 lab).

durum: desteklendi
## H120 (Exp103, 2026-10-22) — Anten: ham model 84 ihlal, korumasiz yalniz 6

Bagimsiz ham-oran olcumu (DEF yonlendirme geometrisi + SPICE kapi alanlari,
sinir 400, difuzyon kredisi yok): 13.393 agin 84u ihlalci; diyotlular
cikarilinca korumasiz 6 ag (_04579_ 946, _03422_ 595, _05425_ 501, clk 486,
_05429_ 455, _05562_ 448; besi met5-agirlikli). OpenROAD'un 20 ihlaliyle
tutarli: fark, diyotlu kismi-anten durumlari (cfg_data sinifi ham oranda
180-386. sirada, BZ3 FAIL - model siniri kayitli). Exp100 yamasi met3
alanini %0,084 degistirdi (BZ4). Kapanis icin alici-yakini diyot + guncel
OpenROAD gerekli (ortam disi). Cip blok-duzeyi EDA kapilarinin tamami
olculmus durumda: DRC ana 0, mr 0, yogunluk dozla kapanir, LVS MATCH,
anten 6 korumasiz aday.

durum: desteklendi (BZ3 haric)
## H121 (Exp104, 2026-10-22) — Kısmi anten mekanizması doğrulandı; büyüklük parantezi

Topolojik katman-oneki modeli (DEF parca grafi + LEF pin capalari, baglanti
%100): cfg_data[0..7] 8/8 kismi ihlalci - Exp88 inatci kumesinin mekanizmasi
kismi antendir (CB1 PASS). Kayitli pin-basina model 38 ag / 3251 pin (CB2
FAIL: pin sayisi tavanda, rst_n baskin); paylasimli (klasik) varyant 6/6.
OpenROAD 20/58 iki ucun arasinda - parantez 500 kat, daraltma kalibre PWL
ister. CB3 FAIL: Exp103 korumasiz 6 agdan yalniz _05425_ her iki modelde de
ihlalci (otekiler erken difuzyon baglantisi koruyor). CB4 PASS: ihlallerin
%67si met3+ (jumper imzasi). Anten sifir kapanisi ortam disi kalir.

durum: kismi (mekanizma dogrulandi, buyukluk acik)
## H122 (Exp105, 2026-10-22) — %49 verim tavani yokmus; maliyet sigma'ya duyarsiz

Exp57 modeli aynen (denetim 49/100 birebir), sigma<5 ilk kez hesaplandi:
N=1024 verimi 2,0 nm -> 0,912; 3,0 -> 0,812; 3,8 (P91/BCA) -> 0,693;
5,0 -> 0,455 (yeni tohum). Exp91'in sigma<=5 icin %49 tavan varsayimi
curutuldu (CC2). t_eff 2,0 -> 1,445 s. Ama Exp87 zincir modelinde mutlak
bedel ayni: 1619,8 (zincir sayisi 2de sabit; sabit taban baskin, CC3).
Oz-tutarli uretim (1000x1000, Mod A) 2,9e7/gun - Exp91in hibrit capali
6,05e5 tablosu gecersiz (CC4 FAIL, bant yukari asildi). Ucuzlatma adresi
spektroskopi degil sabit tabandir; sigma kazanci verim/hiz cephesine yazar.

durum: desteklendi (CC4 haric)
## H123 (Exp106, 2026-10-22) — Sabit taban genis; kanal-olcegi duzeltmesi -%28

Sabit taban (1595) yogun degil: ~14 C-satiri x100, ust-3 payi %19 (CD1 FAIL).
Zarf kolu tukenmis: S=0,5->0,25 yalniz -%3 (CD2 PASS, tabanlar bagliyor).
Asil bulgu model tutarliligi: BOMda "kanal sayisinca/grubunca" yazan 5 satir
(S3.2, S6.4, S6.5, S6.7, S7.2; 410 birim) sabit sayilmis. (ns/10^4)^0,7
duzeltmesiyle mutlak bedel 1619,8 -> 1217,4; zarfla birlesik 1169,0 (-%28,
CD4 <1000 FAIL). Altin olcekte etki yok (0,6035->0,6002). Miknatis C->B
senaryosu -1,4 (kol degil). Kalan ~1140 birim satir bazinda tedarikci
sinifi dogrulamasi ister - bu ortamda kanit uretilemez, acik is.

durum: desteklendi (CD1/CD4 haric)
## H124 (Exp107, 2026-10-22) — Maliyet belirsizligi artik sinif bandi; paketleme Q kolu

BOM sinif denetimi: COTS isaretli 9 sabit satir C bandinda, 5 satir B
bandinda - gerekcesiz ikilik (CE1 PASS). Tek-tip B duyarliligi -%34
(1169 -> 772): modelin baskin belirsizligi fiyat bandi atamasi, fizik degil
(CE2 PASS, duyarlilik olarak). Paketleme: Q=200 (46/hat) altin oran 0,514
(CE3 esik 0,50 FAIL, kil payi); Q=400 (89/hat) 0,445. Mutlak bedel paketlemeye
duyarsiz (1159-1179). Web erisilebilir (HTTP 200) ama tedarikciler teklif
usulu - kamuya acik fiyat bandi yok (CE4 FAIL). Durust mutlak aralik:
~770 (iyimser bant) - 1620 (baz), gerekceli orta 1169. Daraltma tedarikci
teklifi ister (dis etkilesim).

durum: kismi (CE1/CE2 desteklendi; CE3/CE4 acik)
## H125 (Exp108, 2026-10-22) — Q capasi tersine dondu: kapi reflektometrisi Q~18

Literatur taramasi (arXiv + Crossref): toplu-LC kapi reflektometrisinde
Q_loaded ~= 18 (arXiv:1811.04414 tam metin). Exp87 Q=100 varsayimi bu mimari
icin iyimser; altin oran Q egrisi: 18->0,79; 50->0,69; 100->0,60; 400->0,44.
Q>=400 ancak superiletken GHz rezonator mimarisinde fiziksel
(arXiv:2103.03659) - S6.x tasarim catali. Kanalizasyon faktoru ozet
duzeyinde bulunamadi (CF2 FAIL); sayisal kaynak 3 (CF3 FAIL). Yan bulgu:
P tavlama gocu 600C/10dk (doi:10.1063/1.331355) LITERATURE ekine islendi.
Altin oran artik iki dis karara bagli: okuma mimarisi + tedarikci capasi.

durum: CF1-CF3 curutuldu; tasarim catali kayitli
## H126 (Exp109, 2026-10-22) — Superiletken rezonator kolu kredili (Qi ~2e5)

NbTiN Qint ~= 2x10^5 (tek foton, 7 mK, arXiv:2112.08296); 0-0,3 Tde korunuyor
(2312.13703); NbTi 45 nm Qi=1,01x10^4 @0,4 T (2509.20782). Alan kisiti:
rezonatorde B|| <= 0,4 T (ornekte S6.3 0,3-1,5 T olabilir). Sacilma yerel
sigma %0,27 (1803.04275), kirpma /14 (2105.14046). Sifir-pay merdivende
NL_eff=55 (CG2 FAIL); %25 tasarim payiyla 67 kullanilabilir kanal (literatur
%84-97 verim bandiyla tutarli). Altin oran NL=55te 0,493 (zincir B); zincir
sinifi C olursa 0,785 - kol, kriyojenik zincir sinifinin teyidine duyarli.
Ayak izi toplam 8,4 mm2 (CG4 PASS). Karar: okuma mimarisi secimi kullanici/
proje duzeyinde.

durum: desteklendi (CG2 kayitli haliyle FAIL)
## H127 (Exp110, 2026-10-22) — Termal duvar MXC degil 4K HEMT yuku

Krinner olcumleri (arXiv:1806.07862 Tablo 2): hat basina MXC pasif yuk
surucu 0,013 + cikis (NbTi) 0,020 uW. Altin olcekte (9000 kanal, NL=58,
156 hat) MXC toplami 5,24 uW - 20 mK butcesinin (19 uW) %28i (CH2 duvar
ongorusu FAIL, iyimser surpriz). 4K kademesi: 156 HEMT ile 1,09-2,65 W
(5-15 mW/HEMT) - tek PT410 sinifi (~1 W) yetmez, ikinci sogutucu ya da
dusuk guclu HEMT gerekir (CH3 PASS). Urun olcegi termal olarak serbest
(CH4). Altin olcekte S6.1 +1 sogutucu tasiyabilir (modelde islenmedi,
kayitli acik nokta).

durum: desteklendi (CH2 haric)
## H128 (Exp111, 2026-10-26) — Ikinci sogutucu altin orani bozmuyor; kader zincir sinifi

Baz tekrari birebir (Exp109 B 0,4928 / C 0,7849; Exp110 1,482 W). Ikinci
sogutucu en pahali haliyle (S6.1 tam kopya 30 birim, yalniz altin tarafa)
orani 0,4974 yapiyor (CI1). NL tutarliligi: 55->58 farki 0,0055; NL=67
orani 0,4714e iyilestiriyor (CI2). Tek PT410 icin hat-basi LNA tavani
%25 payla 2,57/2,81/3,56 mW (NL 55/58/67) (CI3) ve 2,1 mW InP HEMT LNA
4 K'da olculmus (Rebelo 2026, doi:10.1002/pssa.202501018; 1,4 K gurultu,
41,6 dB) (CI6). Alternatif: tipik 7,8 mW LNA + PT420 (2,0 W). Zincir
B->C hamlesi (0,292) sogutucu cezasinin (0,0046) 63 kati; altin oranin
birinci-mertebe bilinmeyeni artik yalniz zincir sinifi (tedarikci duvari).
Urun mutlak bedeli degismedi: 1159 (CI5).

durum: desteklendi (6/6)
## H129 (Exp112, 2026-10-26) — NL Ql ile buyuyor (164, oran 0,401); kirpma sifir payda olu

Ql x tasarim-araligi taramasi (baz kapisi birebir): optimum izgara kosesi
Ql=1200/D10, NL_eff=163,8 (nominal 263). NL=163te altin oran zincir-B
0,4009 (C 0,658); hat sayisi 56 -> 4K yuku tipik LNA ile bile 0,55 W,
termal duvar kalkiyor. Saglamlik kupu: B 18/18 <0,50, C 0/18 (CJ3).
CJ4 FAIL: kirpma (sigma/14) sifir tasarim payinda NLyi hic artirmiyor
(55,2 vs 55,3) - pay yokken sacilma buyuklugu onemsiz, kullanilabilir
oran ~%62 kilitli; kirpma ancak payla birlikte kol. T_EFF denetimi:
altin oran T_EFFe tamamen kor (olcek metrigi). Model Ql bedelini eksik
saydigi icin (164 ton dinamik aralik, 83 kHz cizgiye karsi kayma, yerel
sigma) sartname bandi NL 110-160 (Ql 800-1200) yazildi.

durum: desteklendi (CJ4 haric)
## H130 (Exp113, 2026-10-26) — Ton butcesi: NL=163 sikismadan geciyor; kayma degil ton gucu sart

Capali: LNF-LNC4_8C veri sayfasi giris P1dB -53 dBm (42 dB kazanc, cikis
P1dB -12, OIP3 -2). Referans noktada (-100 dBm/ton, tepe 12 dB, 10 dB
geri cekilme) NL_max=316 > 164; -90 dBmde 32 -> sartname: ton <=-100 dBm/
kanal. Kesirsel kayma ~1e-6 (Niepce 2008.07038 birkac kHz) ile Q1200de
kayma 0,0012 cizgi genisligi, Q_max 5e5: baglayici sinir kayma degil
sikisma. NL_design=163, oran 0,401, 4K yuku 0,70 W (10,5 mW LNA ile bile).
Modelli (capasiz) 2,1 mW bias senaryosu: NL~126, oran 0,417. IMD tondan
68 dB asagi. Bant uyarisi suruyor (capali LNA 4-8 GHz, merdiven 0,1-0,9 GHz).

durum: desteklendi (5/5)
## H131 (Exp114, 2026-10-26) — Zincir sinifi merkezi ~17; B/C duvari halka acik fiyatla cozulemiyor

Kalibrasyon (CL1 PASS): PT410 ikinci el `$19.000` (C->birim `$190`), XL-80
`$32.000-$44.250` (C->`~$380`), GPU istasyonu `$10.599` / `$10,6k` (B->`$1.060`), pompa seti `~$16.000`
(B->`$1.600`). BOM sinif birimi kendi icinde 8,4 kat tutarsiz; medyan `$720`.
Zincir faturasi merkez `$12.150`/hat (aralik `$6.500-$22.200`) ama capali kapsama %33 (2/6) -> CL2
FAIL (kriyo LNA fiyati halka acik degil). Surekli zincir sinifi merkez
16,9, durust bant [4,1-116,8] -> CL3 FAIL. Merkezde altin oran NL163
0,438 (CL4 PASS), NL67 0,533. Raporlama uclusu: B 0,401 / merkez 0,438 /
C 0,658. Iceriden saldiri tukendi; duvari LNA+izolator teklifi cozer.

durum: kismi (CL1/CL4 desteklendi; basari kurali FAIL)
## H132 (Exp115, 2026-10-26) — Tasarim belgeleri Exp105-114 siciline senkronize edildi

395 sayisal aday satir triyaji: 13 bayat iddia grubu, 23 duzeltme islemi
(DESIGN 13, BOM.csv 5, BOM.md 2, MODULAR 2, LITERATURE ek). En agirlar:
MODULAR NL=24 -> 110-160; BOM S6.6 "5 zincir" -> 56-82 zincir; DESIGN
mutlak maliyet 1619,8 -> 1159/1166/1249 uclusu; %49 tavan -> %69; maglev
govde metni -> piezo; miknatis sartina rezonator-duzlemi <=0,4 T eklendi;
6. bolume MXC kademesi isilendi. Ilk geciste tirnaksiz CSV alanina giren
virgul modeli 0,5819a oynatti; degiskenlik kapisi yakalayip onardi, son
kapi birebir (0,49280386/1159,0004). Surum notlari tarihsel birakildi;
R5 yogunluk ifadesi guncel dogrulandi.

durum: desteklendi (3/3)
## H133 (Exp116, 2026-10-26) — Spektroskopi seyreltme kademesi ister; eksik BOM satiri orani 0,522ye tasidi

Fizik: 0,4 Tde Ez/k=0,537 K; 4 Kde polarizasyon %6,7 (CN1 ilk yari PASS)
ama %25 sicakligi 1,052 K > kayitli 1,05 esik -> CN1 FAIL (kil payi,
esnetilmedi). Alan pratigi tek-donorde ~100 mK (CN2 PASS); >=4 K tek-donor
capasi yok. 1K kademesi 0,4 Tde secicilik vermez (Ez/kT=0,54); kayitli
yontem (spin-yuke cevirme) MXC ister. BOMa S6.8 seyreltme unitesi sinif D
eklendi (DR artisi ~350-625 birim; senaryolar: C 0,448/1266, surekli 350
0,470/1516, D 0,522/2166 - NL163 merkez sinif). YENI BAZ: NL55-B
0,5603/2159,0 (40 satir). Exp105-115 maliyet sayilari kademesiz BOMa
aittir; manset artik D senaryosudur. Sicak-kubit (1,5 K Pauli blokaj)
rotasi donor-disinda gosterimli - 1K alternatifi arastirma yonudur.

durum: kismi (CN1 FAIL kil payi; kademe hukmu ve BOM revizyonu gecerli)
## H134 (Exp117, 2026-10-26) — Sicak okuma kredili: kademe D->C, oran merkezde 0,448

Belirleyici capa donorun kendisinde: cok-donorlu noktalarda kilitli parite
okumasi 3,7 Kde %97,8 (Geng 2025, 10.1038/s41467-025-58279-3; B=0,4 T).
Diraq Nature 2024 >1 Kda %99,6. Termal model: E_ST=0,5 meV, 1,5 Kde
V=0,959; polarizasyonla birlesik ortalama bedeli 3,16x (abs 1275).
Kayitli politika (CO1+CO2+CO3) tetiklendi: S6.8 sinif D->C (1K kapali-
cevrim kademe). YENI BAZ: NL55-B 0,5005/1259,0; NL163 merkez 0,4478/1265,9.
Kalan risk kayitli: capali aygitlar STM-hassas yerlesimli; implant
sacilmasiyla yardimci-nokta baglasim verimi modellenmedi. D senaryosu
(0,522/2166) Elzerman kolu alternatifi olarak sicilde durur.

durum: desteklendi (4/4; entegrasyon verimi acik risk)
## H135 (Exp118, 2026-10-26) — Yardimci-nokta baglasim verimi p~1,0; vadi cezasi yok

Exp92 BCA sacilmasi (yatay 3,25 nm; derinlik 6,46+-2,88) + House 2015
capalari (tc ~1 GHz, degisim >=100x ayar, ayrim ~20 nm). Yakalama
penceresi [1MHz-10GHz]xayar=8 onluk, baglasim dagilimi 0,70 onluk ->
p=1,000 (R0=20/G100); en kotu hucre (15nm/G1) 0,535. CP2 FAIL: log-duzgun
vadi faktoru ceza degil yakin ayrimda kurtarma yapti (0,535->0,776) -
sorun fazla baglasim tarafindaymis. N99=1; altin oran degismedi (0,4478).
Risk, model bicimi (lambda=2nm, kaba vadi modeli) kaydiyla emekli.

durum: desteklendi (CP2 haric; basari kurali PASS)
## H136 (Exp119, 2026-10-26) — GDS cikarimiyla anten sayimi: 84 (kredisiz) -> 1 (kredili)

KLayout hiyerarsik ag cikarimi yamali GDS uzerinde (BNH_Flatten; S/D =
diff-poly kesimi). Butunluk: katman korunumu ~1,000-1,004, kapi alani
birebir 1,0; aglar kuresel (69878/70684 ust devrede). RAW ihlalci 84 -
Exp103 DEF modeliyle birebir (bagimsiz yontem dogrulamasi). Difuzyon
met1den kredilenince tek ihlalci kaliyor (oran 485, li1 adimi; ikinci 41).
Exp104 parantezi [6-3251] -> [1-84]e indi. Kalan is: o tek agin ECOda
kopru/diyodu + DEF/ODB borcu + OpenRCX (dis ortam).

durum: desteklendi (3/3)
## H137 (Exp120, 2026-10-26) — FAILED: tek anten ihlalcisi GDS yamasiyla kapanmadi

Ihlalci: saat girisi -> clkbuf_4 (m0 313720,318240); oran met4te 485,
agda difuzyon yok. D1 via kulesi (400nm inis) komsu aglara kisa devre
yapti; cikarimin sahte "0 ihlal"i teshisle yakalandi (birlesen ag kapi
alani 1,95 um2). D2 aciklik taramasinda temiz kule noktasi yok. D3 decap
takasi geometrik olarak ideal (decap_4 m0 311880; diode 312800 + fill x2)
ama decap_4 LVS envanterinde (60492 X satiri) - CR3 birebir-envanter
sartini bozar, uygulanmadi. ECO tarifi OpenROAD donemi icin ozette
koordinatli birakildi. Deneme-1 GDSi invalid olarak isaretlendi.

durum: FAIL (kayitli sinirlar icinde geometri/envanter blogu)
## H138 (Exp121, 2026-10-26) — Kullanici karari: maliyet artisi serbest; seyreltme baz kademe

Deney degil karar kaydidir (tahmin yok). Kullanici talimati: "makinenin
pahalilasmaasina izin veriyorum; proje genelinde uygula." Uygulama:
BOM S6.8 C->D (seyreltme baz; Exp117 1K sicak-okuma maliyet-indirme
alternatifi olarak sicildedir), DESIGN S6 baz cumlesi, REVERSE ilke-4
(ucuzlatma ikincil). Dogrulama: Exp116 D senaryosu birebir - yeni baz
NL55-B 0,56029503/2159,0004; NL163 B/merkez/C = 0,4957/0,5215/0,6869;
NL67 merkez 0,5894; mutlak 2159/2166/2249. Zincir uclu raporlama ve NL
bandi bilincli degistirilmedi. Exp121-transfer plani bu kararla dustu.

durum: karar kaydi (hukum yok)
## H139 (Exp122, 2026-10-26) — Butce tavani 100M USD: tasarim 1-2 mertebe icerde

Kullanici karari: uretim maliyeti 50M USD ustu olabilir, 100M son sinir.
Exp114 kalibrasyonuyla (birim `$190-$1.600`, medyan `$720`): altin olcek BOM-
kapsami NL163 merkez 3.516 birim = `$2,53M` (`$2,531M`); en kotu kayitli kose (NL163
zincir C @ `$1.600`) `$13,1M` (`$13,073M`) < `$50M` (CT1 PASS); merkez x10 program carpani
`$25,3M` (`$25,312M`) < `$100M` (CT2 PASS). Uclu-asiri kose (C + ust birim `$1.600` + x10) `$131M` (`$130,73M`) ile
asar - kayitli. BOM kapsami tesis/iscilik/Ar-Ge icermez; tavan DESIGN
S8e islendi, tekliflerle yeniden sinanacak.

durum: desteklendi (2/2)
## H140 (2026-10-26) — Kullanici karari: butce cizgisi kurali (50M yumusak / 100M sert)

Deney degil karar kaydidir. Kural: <=50M USD normal bolge; 50-100M arasi
izinli ancak masustune BUTCE_DURUMU.md ile gerekcelendirilmesi zorunlu;
>100M asilamaz. Guncel durum asimsizdir (Exp122: merkez 2,5M, program
x10 ile 25,3M). Dosya, asim gerekirse gerekcenin yazilacagi yer olarak
simdiden olusturuldu (durum: asim yok). DESIGN S8 + v2.23 guncellendi.

durum: karar kaydi (hukum yok)

## Ek Capraz Not (Exp94, 2026-10-21 / mtime 2026-10-26) — Kristal BCA yonelim + sirali carpisma duzeltmesi (H111-H112 arasi kayit disi kosu)

H1-H140 numaralamasini bozmamak icin sona eklenen capraz kayittir (`results/exp94_channeling2/exp94.json`,
BQ1-BQ4). Exp93 kafes/yonelim hatasi duzeltildi (z//[110], 265.163 atom, 2,0 A adimda sirali carpisma)
ancak azimut rastgele kaldi: 5 keV <110> sigma_x=2,068 nm, Rp=5,220 nm (BQ1/BQ4 PASS) vs 7 deg kontrol
2,078 nm, Rp=5,261 nm (BQ2/BQ3 FAIL; post-hoc 0-25 deg taramasi duz). Basari kurali FAIL; Exp95'e (H112)
devredilip Exp96'da (H113) kanalizasyon hatti durduruldu.

durum: curutuldu (BQ1/BQ4 PASS, BQ2/BQ3 FAIL; success_rule_met=false, Exp95 ile asildi)

## H141 (Exp123, 2026-11-02) — OpenROAD 2024 blanker karo anten onarimi: ara durum (FAIL / yarim; aktif odak makinede)

Yeni kurulan OpenROAD `v2.0-17598-ga008522d8` ile `Exp88 flow_r3` uzerinde 4 deneme + 2 geometri kontrolu
kosuldu (`results/exp123_or_antenna/exp123.json`, `tapeout_done=false`, `summary_exp123.md` henuz yok):
- Deneme 1: `Exp88 final.odb` sema uyumsuz (`incompatible database schema revision` -> CU1 FAIL). DEF fallback
  on-sayim 20 net / 58 pin (`20/84 = 0,2381` -> CU3 PASS); dolgular varken `repair_antennas` `DPL-0036` +
  `STA-0562` ile dustu -> 20 net / 58 pin degismedi (SHA-256 ozdes -> CU2 FAIL).
- Deneme 2 (`remove_fillers -> repair_antennas -iterations 3 -> filler_placement`, `detailed_route` yok):
  94 diyot + 117 jumper sonrasi gorunurde 0 net / 0 pin basti ancak (i) `write_verilog` `malloc() Signal 6`
  ile coktu (`final_repaired_attempt2.v` kesik) ve (ii) dogrudan DEF ayristirmasi `13.393` agdan **`101` agda
  `+ ROUTED` geometrisinin silindigini (`13.292` routed / `101` unrouted) ve `20/20` orijinal anten ihlalcisinin
  tamaminin telsiz kaldigini** kanitladi (`met2=0,8823x`, `met3=0,8600x`) — **sahte kapanis**.
- Deneme 3 (`reroute`): 2 ihlalde salinim + WSL oturum kaybi (`output_def=null`).
- Deneme 3b (`2026-11-02 06:03-06:07`, `attempt3b_reroute/or123d.log`): `ckpt_grt0.odb` ardindan
  `repair_grt_1iter` (`Found 19 antenna violations` / `Inserted 32 jumpers for 17 nets`) asamasinda yarim kaldi
  (`output_def=null`).
- Politika notu (kullanici karari, 2026-11-22): `H141/Exp123` acik EDA borcu olarak sicilde tutulur;
  projenin aktif calisma odagi cip hattindan degil **Atom Litografi Makinesi'nden** devam etmektedir.

durum: curutuldu / yarim (CU1 FAIL, CU2 FAIL, CU3 PASS; ara kayit, tapeout_done=false)

## H142 (Exp124, 2026-11-22) — 10->5 keV iyon kolonu optigi (Arch-B + HDA-HiRes), Scherzer alt siniri & 3B anizotropik + donor sacilmasi

2B eksenel simetrik Laplace (`spsolve`) + `DOP853` isin izleme + 3B anizotropik/stokastik donor verim motoru (`results/exp124_ion_column_optics/exp124.json`, `tests/test_exp124.py` 6/6 PASS, `no_lab_measurement=true`, QA `#59` KABUL):
- Liouville parlaklik acigi kapatildi (`CD1 PASS`): `B_r = B/E = 7,958 A/m^2/sr/V` sabit oldugundan dogrudan `5 keV` cekim `39.789 < 72.149 A/m^2/sr` (`1,813x` acik, `r_geom=2,020 nm`) verir; `10 keV` ust kolon (`-5 kV` astar, `+5 kV` anot) + `5 keV` alansiz (`0 V`) pul zorunludur. Wronskian kaymasi `2,05-4,87e-8 < 1e-6`, Scherzer-isin `C_c` farki `%0,00-%0,12` (`CD2 PASS`).
- **Scherzer-delinme degismezi (`CD3 FAIL` — gercek fiziksel alt sinir):** `kappa_c = C_c * E_gap / V_land >= 4,67` (`min 4,665`; `Arch-B: 5,640`). `E_gap <= 12 MV/m` ve `5 keV` altinda `Exp82/91`'in test edilmemis `C_c <= 0,50 mm` hedefi statik dairesel elektrostatik mercekle fiziksel olarak imkansizdir.
- **Liouville-tutarli cozum (`CD4, CD5 PASS`):** **`Arch-B`** (`32x32 = 1.024` demetcik, es-adimli `0,50 mm` [`S2.1/S2.2/S2.3`], aktif kare `16,0x16,0 mm`, kosegen `22,63 mm < Ø28,0 mm` `S1.6/S2.1` acikligi -> `2,69 mm` radyal marj; `16x` 64-kanalli karo; `D=0,30 mm, h=1,76 mm, OD=60 mm`, `WD=0,250 mm, E_gap=10,60 MV/m, C_c=2,660 mm, C_s=10,786 mm`) + **`HDA-HiRes`** (`R0=40 mm, E_pass=100 eV, slit=0,35 mm -> dE_FWHM=0,453 eV, tau=0,071`): `Ti=0,25 eV, 10 ms` (veya LMIS `1 ms`) -> `sigma_spot=1,428 nm <= 1,50 nm, sigma_tot=3,674 nm <= 3,80 nm` (kosullu `MachineConfig` ham demetcik ust siniri `4,42e9` atis/gun); kanonik `Ti=0,5 eV, 15 ms` -> `1,532 / 3,715 nm <= 3,80 nm` (kosullu ham demetcik ust siniri `2,95e9` atis/gun — bekleme/hizalama/okuma/kriyojenik cevrim kayiplari haric). Wien (`10 keV, 0,45 T, V_p=1.348 V`): `dx(32PH+)=0,785 mm`, `R_m=120,6`; Coulomb/Boersch bastirmasi `2,83x / 2,52x`, `N_bar_1=1,40e-3`. 8-kademe kolon (`Z_WAFER=500,00 mm -> z_CAD: 500,25..1062,66 mm`): `562,66 mm / max OD 110,0 mm / 25,92 kg`.
- **3B anizotropik & stokastik `31P` donor verimi (`400` deneme, `N=1024`, `CD6, CD8 PASS; CD7 FAIL`):** Denetim birebir (`49/100`, `277/400 = %69,25`). Sabit donorde 3B anizotropik (`z>0`): `ANISO_BCA_PURE %78,75`, `ANISO_P91_BCA %76,75`, `ANISO_EXP124_BCA %76,25`; `ANISO_P91_HOLMES` yuzeysiz `%63,25` -> `z>0` **`%69,50`** (`CD7 FAIL`: `%11,0` ust-yari seyirci kesilince spektral sikisma rahatladi, `elig_med 8->9`). **Stokastik `31P` donor 3B sacilmasi (`CD8 PASS`):** `ANISO_P91_BCA_DONOR %43,75` (`-33,0 pp`), `ANISO_EXP124_BCA_DONOR %42,50`, `ANISO_P91_HOLMES_DONOR %28,00` (`-41,5 pp`, geri-sacilma `%10,0`). Mod B (`f=%1`, `%51`) donor sacilmasina tamamen bagisiktir.

durum: kismen desteklendi (6/8 PASS: CD1,2,4,5,6,8 PASS; CD3, CD7 FAIL; success_rule_met=false — iki FAIL gercek fiziksel kesif)

## H143 (Exp125, 2026-11-22) — 1,50 T / 22,3 uT 8-bobinli kriyo miknatis, Meissner kalkani, 5-kademe termal/RF & R8 Koiller 6-vadi

Eksenel simetrik tam eliptik integral (`ellipk/ellipe`) Biot-Savart + `Nb` Meissner BEM + 5-kademe termal/RF + `200k` MC Koiller 6-vadi analizi (`results/exp125_cryo_magnet_readout/exp125.json`, `tests/test_exp125.py` 11/11 PASS, `no_lab_measurement=true`, QA `#52` KABUL):
- **Sayisal dogrulama & 8-bobin `NbTi` (`CV1, CV3 PASS`):** `max|div B|=7,90e-7`, `max|B-curl A|=8,77e-7`, `8x8 vs 12x12` `4,54e-14`, BEM `5,85e-8`, enerji `18,941 vs 18,895 kJ` (`%0,244`). `M/S/A/B` ust+alt (`Ø150,0 mm` bore / `36,0 mm` yarik / `Ø352,0 mm` OD, `5,48 km` tel): ornekte (`r<=2,3 mm, |z|<=0,5 mm`) **`B_z(0,0) = 1,500000 T +- 17,81 ppm`**, `max|B_r|=0,011 mT`; `max(I/I_c)=0,212 <= 0,55`, `min dT=2,55 K`, `max|sigma_hoop|=52,7 MPa <= 80 MPa`, pasif dump quench (`R_dump=1,563 Ohm, V_max=400 V, tau=0,370 s`) **`T_hotspot = 64,6 K <= 150 K`**.
- **Risk `R7` manyetik ayristirma KAPANDI (`CV2 PASS`):** `z_loc=-155 mm` (`r<=25 mm`, `1.963,5 mm^2`) sessiz diskte kalkansiz `3,08 mT` -> **`Nb (RRR>300)`** (`R=32..34,5 mm`, yuzey `117,12 mT < B_c1=134,95 mT` vortekssiz) + **`Cryoperm-10`** (`R=39..41 mm`, `SF=488,8x`) ile **`max|B| = 22,3 uT`** (`|B_z|<=21,6 uT, |B_r|<=7,8 uT`). MEMS kacak alani (`z_loc=+268 mm`): `108,1 mT`.
- **5-kademe termal & RF SNR (`CV4, CV5 PASS`):** `9.000` kanal (`56-82` hat): `20 mK` baz `NL=163` (`56` hat, `2,1 mW`) `4K=0,325 W, MXC=3,94 uW`; kanonik `NL=160` (`57` hat, `7,8 mW`) **`4K=0,654 W, MXC=3,97 uW`**; `NL=110` (`82` hat, `7,8 mW`) `4K=0,899 W < 1,0 W, MXC=4,80 uW` (`10,5 mW`: `1,121 W -> PT415/420`); `1 K` alt `1K=11,84 mW < 100 mW`. RF `SNR=10` suresi: **`0,0627 ms`** (`20 mK`) / **`0,179 ms`** (`1,5 K`) `<< t_eff=1.445 ms`.
- **Risk `R8` Koiller 6-vadi (`CV6 PASS`, `200k` MC):** `W4/G=100x` `p=1,0000`; gercekci `W2` (`100 MHz-10 GHz, G=10x`) `V1=0,9694`, **`V2=0,9322`** (`N_99=2`; `lambda=1,5 nm: 0,8781`); `W1 (G=3x)` `0,6096`; `G=1x` `0,3354` (`< p_crit_cost=0,5122, p_crit_frac=0,4812`). Ayrica `1 K` Mod B hizi `3,40x` yavaslar (`1,372e8 -> 4,042e7/gun`).

durum: desteklendi (6/6 PASS: CV1-CV6 PASS; success=true; Risk R7 manyetik ayristirma model-ici kapandi)

## H144 (Exp126, 2026-11-23) — Tam 32-boyutlu Hamiltonyen XY8-GRAPE, Risk R3 kapanisi & 16-hucreli atom programlanabilirligi

NVIDIA RTX 2060 SUPER (`complex128` tam `32x32` uniter matris usteli, `2.397,5 s`, `1e + 4n + 448` banyo seyircisi + sekuler `J_ij`; `results/exp126_atom_cell_programming/exp126.json`, `tests/test_exp126.py` 8/8 PASS, `no_lab_measurement=true`, QA `#69` KABUL):
- **Risk `R3` tam 32B Hamiltonyende KAPANDI (`P126_4 PASS`):** `Exp62 F1` (`f=%1, T2e=1,269 ms, T_tot=2,0 ms, eps=1e-3`): `N_total=64` ic-ice `XY8`-GRAPE ile **`alpha=1 -> Q_32D = 0,9209`** (`Exp63: 0,8851`, `+3,58` puan) ve **`alpha=2 -> Q_32D = 0,9433`** (`Exp63: 0,9250`, `+1,83` puan) — her ikisi de `>= 0,85`.
- **Iki kritik fiziksel kesif:** (1) **`N_total` tatli noktasi & DDRF duvari:** global optimum **`N_total = 32` (`N_dd=8`/kapi: `alpha=1: 0,9260`, `alpha=2: 0,9648`, `sp_ovl448 = 0,9889`)**; buna karsin `Exp63`'te calisan **`N_total = 128` (`f_mod=32 kHz`) DDRF seyirci rezonansiyla coker (`ideal=0,5437, sp_ovl=0,0972`)**. (2) **DDRF seyirci cokusu & RF genlik payi (`F1 q3, min_gap=6,89 kHz`):** yalin `GAUSS500` 448-seyirci ortusmesi `0,9992 (N_dd=0) -> 0,2035 (8) -> 0,000537 (16) -> 1,51e-6 (32)` duser; eski `5 kHz` RF siniri bunu acamaz (`F_nom=0,7716`), **`10-15 kHz` (`B1 ~ 1,2-1,8 mT`)** 2-asamali 32B `XY8`-GRAPE ortusmeyi **`0,9919`** (`~1.846x` kurtarma) ve `F_nom=0,9986` duzeyine cikarir.
- **`XY8` vs `CPMG` & `eps=1e-2` tavani (`P126_5 PASS`):** `eps=1e-2` -> `Q_32D=0,6382 < 0,80`. Sistematik asiri-donmede (`N=64`): `dtheta=63,25 mrad` **`XY8` `0,9767/0,9756` vs `CPMG` `0,6454/0,6512` (`+0,3245`)**; `100 mrad` **`+0,6189`** (`0,9555 vs 0,3366`) -> **`XY8` zorunlu, `CPMG` yasak**.
- **16 heterojen hucre x 5 program & `D0`/yalitim (`P126_6,7,8 PASS`):** `16/16` tekil `f=%1` hucre (`CV=0,556`, `Lie=1023/1023`, `gap=6,89-46,66 kHz`, `max|J|=6,65 Hz`), gurultulu (`alpha=2, eps=1e-3`) 16-hucre ortalamalari: **`Bell 0,9501`** (`min 0,9416`), **`GHZ-4 0,9401`** (`min 0,9263`), **`Grover-2 0,8896`** (`P(|11>)=0,9237`), **`BitFlip-3 QEC 0,8878`** (kodsuz `0,0000`), **`QFT-3 0,8377`**; dogal 3-cisim **`CCZ(0,1,2) = 0,9338`**. `max D0(17,5 s) = 7,76e-9 <= 1e-5`, `1 um` hucreler arasi dipol `9,50e-9 Hz < 1e-6 Hz` -> `16x` paralel FDMA.
- **Durust 3 FAIL (`P126_1,2,3 FAIL`):** `max u_err = 3,47e-12` gecti ancak `P126_1` (`X q2 nom=0,99423 < 0,995`, `X q1` tek seyirci `0,96194`, `cX q3` `6,89 kHz` tam-fazli 32B kose `0,97264 < 0,985`), `P126_2` (`CNOT` 6/6 `>=0,9873` ve gurultulu `CZ` ort `0,94442` gecti, yalniz `CZ(2,3)` ideal `0,98279 < 0,985` ve elektron sizintisi `3,61e-3 > 1e-3`) ve `P126_3` (`7/8` Hahn-eko gecti, `F1 alpha=2` `n_traj=512` MC `W=0,3087`, `err=0,0592 > 0,05`).

durum: kismen desteklendi (5/8 PASS: P126_4..8 PASS; P126_1,2,3 FAIL; success_rule_met=false; Risk R3 model-ici kapandi)

## H145 (Exp127, 2026-11-22) — 100 K soguk-ada IBIC on-uc elektronigi, 0-ERC KiCad/SPICE & CellISA v2.0 kontrol yigini

Tam Lindhard (`31P+ -> Si`) durdurma bolusu, sonlu GBP Laplace `H(s)` / Parseval ENC, Rice yanlis-tetik, `50.000`-iyon MC + `src/board/` v2.0 + `src/machine_control/` v2.0 (`results/exp127_detector_frontend_sim/exp127.json`, `35/35 pytest PASS`, `no_lab_measurement=true`, QA `#52` KABUL):
- **Lindhard sertlesmesi & Laplace/ODE dogrulamasi (`CZ1, CZ2 PASS`):** Gercek Lindhard `Exp72`'den ~`%28` daha dusuktur: `5 keV` `Y_e=0,2542` -> **`351,2 e- @ 300 K / 341,7 e- @ 100 K`**, `10 keV` `Y_e=0,2867` -> `792,0 / 770,8 e-`, `20 keV` `Y_e=0,3281` -> `1.813,0 / 1.764,2 e-`. Laplace<->ODE uyumu `%0,004` (`35,200 vs 35,201 mV`, `t_peak=224,7 ns`).
- **RT cokusu -> `100 K` soguk-ada zorunlulugu (`CZ3, CZ4 FAIL; CZ5 PASS`):** `RT 300 K / 200 ns / 100 MOhm` (eski RT profili) devrede `ENC=89,92 e-`, `5 keV eta = 0,09722` (FAIL), `10 keV eta = 0,97742` (`RT 1,2 us / 1 GOhm`: `ENC=58,10 e-`, `5 keV 0,64548`, `10 keV 0,99978`). **Kilitli `COLD_100K` (`100 K / 1,2 us / 1 GOhm`) soguk-ada `LTC6268` + `ADA4817-1` (`x50`) + `DAC8568` (`5,5 sigma` Rice) + `TLV3501`:** **`ENC(0,5 pF) = 24,07 e-`**, **`P_false = 2,59e-4 / 1 ms`**, **`eta(5 keV, 0,5 pF) = 0,99936`**, **`eta(10 keV) = 1,00000`**, **`eta >= 0,99` penceresi `C_det <= 1,5 pF` (`0,99064`, `3x` marj)**.
- **0-ERC netlist & `CellISA v2.0` (`CZ6 PASS`):** `src/board/detector_frontend.net` (**`204` bilesen, `107` net, `0` ERC**, varsayilan `COLD_100K` `Rf=1 GOhm, CS=CP=600 pF`) + `detector_frontend.cir`. `src/machine_control/` v2.0: tasinabilir Linux `AtlasSelector`, `v224_baseline` (`beamlets=1024`, `15 ms/atis`, `3.517/4.000 = %87,92`, `3.517/3.517` dolu `lines_Hz`), 10-komut **`CellISA`** + SHA-256 `ProgramCertificate` (`4/4` `certified=True`: `bell 0,9982`, `ghz4 0,9950`, `repcode3 0,9927`, `qft3 0,8812` — Gauss'a `57x` ustunluk).

durum: kismen desteklendi (4/6 PASS: CZ1,2,5,6 PASS; CZ3,4 FAIL; success_rule_met=false — RT 5 keV cokusu 100 K soguk-adayla kapatildi)

## H146 (Exp128, 2026-11-22) — 145-parcali muhendislik BOM, 6-RFQ, 100k korelasyonlu MC butce & 20 mK vs 1 K EVPI

Degismez kanonik `BOM.csv` (`$2.531.244,37`) ile `$0,00` kopru hatasinda `145` parcali `BOM_DETAILED.csv` + `6-RFQ` + `100.000` orneklemli korelasyonlu MC + EVPI karar analizi (`results/exp128_bom_sensitivity/exp128.json`, `tests/test_bom_detailed.py` 6/6 PASS, `no_supplier_quotes=true`, QA `#63` KABUL):
- **BOM koprusu & `M1` tasinabilirligi (`CU1 PASS`):** **`M3 = $4.189.600`** (`$2.329.000-$7.834.700`, `Delta = +$1.658.355,63`: `S2` MEMS NRE `+$764.867`, COTS/UHV/PT420 `+$285.769`, `Exp125` miknatis/kalkan `+$261.000`, `S9` yedek `+$148.000`, `Exp124` kolon/`PH3` `+$133.600`, `Exp127` IBIC `+$65.119`). **`M1 = $2.189.770`** (`$1.277.070-$3.940.690`, `M3`'un `%52,3`'u, **`%82`'si `M3`'e dogrudan tasinabilir**).
- **100k korelasyonlu MC & Tornado (`CU2, CU3 PASS; CU4, CU6 FAIL`):** Model A `M3` BOM **`P50 = $5,01M`, `P95 = $11,20M`, `P(>$50M) = %0,00`, `P(>$100M) = %0,00`**; Program (`x3-x10`, `P50=5,48x`) **`P50 = $28,24M <= $50M`, `P95 = $82,11M`, `P(>$50M) = %18,10`, `P(>$100M) = %2,69`** (Model B: `P50=$4,99M / $28,01M`). Tornado BOM varyansi: **`S6.6 B/C duvari %77,27`** (`rho=0,889`), `S2` MEMS `%5,85`, `S6.8` DR `%5,21`. **`CU4 FAIL`:** 6-RFQ (`58` parca, `$2.950.900`) nominal payi `%70,43 < %75` esigi, ancak **toplam BOM MC varyansinin `%92,8`'ini yakalar**. **`CU6 FAIL`:** agir sag kuyrukta `Delta P95 = %1,46 > %1,0`.
- **`20 mK` vs `1 K` EVPI (`CU5 PASS`):** `E[Delta C_hw] = $662,9k/makine`; `C_RD=$2,0M, p=%50` altinda `N=1` **`ENV = -$1,67M`**, **`EVPI = $0`** (`20 mK` baz ilk makine icin kesin optimal); filo basa-basi **`N_be = 6,03` makine** (`2x` entegrasyonla `3,02`; tepe `EVPI=$657k @ N=5`).

durum: kismen desteklendi (4/6 PASS: CU1,2,3,5 PASS; CU4,6 FAIL; success=false — 6-RFQ %92,8 varyansi yakalar, 20 mK baz optimal; Dalga-2 v4.0 yenilemesinde 159 parca `M3 = $4.609.600`, `M1 = $2.336.270`, 7-RFQ `%92,6` MC var, `P(>100M)=%3,38`, `CU1,2,3,5,6 PASS`, `CU4 FAIL`, `success=true`)

## H147 (Exp129, 2026-11-23) — Risk R1: VOKL-6 alti-vadili merkez-hucre asiri-ince teorisi & Mod B verim yeniden kalibrasyonu

Yari-ampirik / etkin-kutle `216x216` 6-vadi merkez-hucre Kohn-Luttinger cozucu (`H_6v`) + 145-PW CB-EPM + `N_cell = 400` Mod B banyo kalibrasyonu (`results/exp129_valley_orbital_hyperfine/exp129.json`, `tests/test_exp129.py` 6/6 PASS, `no_lab_measurement=true`, QA `#130` KABUL):
- **Spektral & simetri kapanisi (`CE1, CE2 PASS`, sifir `29Si` uydurmasi):** Yalin EMT `E_EMT = -31,262 meV` (Faulkner `-31,27 meV`, `%0,03`); Morton-Preston `3s` orani (`eta_P/eta_Si = 1,4178`) ile 4 `31P` degismezi (`A1 = -45,5900`, `Delta_T2 = 11,7000`, `Delta_E = 13,0100 meV`, `A_P(0) = 117,530 MHz`) `< 10^-10` (`~10^-11` mertebesi, maks `7,36e-11`) duyarlikla saglandi; 145-PW `C_g(0,0,2) = 8,82e-15` (Lax-Birman yasakli); `a_perp/a_par = 1,748 / 0,959 nm`.
- **Orneklem-disi ENDOR siniri (`CE3, CE4 FAIL`):** Ab-initio `(0,0,4)` `2,66 -> 7,95 MHz` (`eta_Si=186`; Hale-Mieher `5,962 MHz`); `(1,1,1)` `0,0551` (`%40,1`), `(2,2,0)` `0,0683` iyilesti; ancak `-45,59 meV` boylamasina daralmasi (`a_par: 1,28->0,96 nm`) **`R331`'i `0,1034` (`%64,73` hata vs KL `%49,05`)** ve `logRMS = 0,7445` (vs `0,5736`) duzeyinde birakti -> `[110]` kovalent zikzak zinciri tum-elektron cekirdek-polarizasyonu / Si `3d` DFT/TB gerektirir.
- **Kritik asagi-yonlu Mod B verim kesfi (`CE5 PASS`, `CE6, CE7 FAIL`):** `Exp59/62` denetimi birebir (`26/51/69`). `45.214` noktada guclu bag (`|A|>=10 kHz`) `18.784 -> 6.091` (`VOKL6_norm_ext`) / `9.464` (`VOKL6_HM5962_ext`). **`KL_legacy` (`N=400`):** `F0.5/F1/F2 = %26,75 / %50,50 / %67,00`. **`VOKL6_norm_ext` (eski `2,981 MHz` kurali):** **`%1,00 / %4,75 / %11,75`**. **`VOKL6_HM5962_ext` (gercek Hale-Mieher `5,962 MHz`, `Exp25` cift-yarilanma duzeltmesi):** **`%12,00 / %33,25 / %54,50`**. Ayrica `f=%1`'de `min_gap < 6,893 kHz` (`Exp126` DDRF esigi) orani **`%57,9-%73,7`** (`KL: %47,5`) -> Risk `R1` kapanmamistir, `M1` ilk ENDOR go/no-go kapisidir.

durum: curutuldu / kritik bulgu (3/7 PASS: CE1,2,5 PASS; CE3,4,6,7 FAIL; success_rule_met=false — Risk R1 asagi-yonlu gercek verim riski)

## H148 (Exp130, 2026-11-23) — Risk R6 kapanisi: milisaniye flas/lazer tavlama (31P aktivasyonu vs TED & 29Si karisimi)

1B dogrusal-olmayan termal PDE + `SPE/TED` cift-faz difuzyon & `S5.5` optik donanim tasarimi (`results/exp130_flash_anneal_diffusion/exp130.json`, `tests/test_exp130.py` 7/7 PASS, `no_lab_measurement=true`, QA `#115` KABUL):
- **`EA1–EA3 PASS`:** `Exp108` (`doi:10.1063/1.331355`) capasi dogrulandi (`600 C/10 dk` `%93,2` yuzey birikimi, `800 C/10 dk` `%52,7` vakum kacisi; kutle koruma `6,33e-15`). Termal PDE yakinsamasi `%0,184`, enerji dengesi `%0,0033`. Geleneksel firin (`600 C`: `sigma=6,11 nm`, `800 C`: `3,13 nm`) ve RTA (`1000 C/10 s`: `4,97 nm`, `%21,2` kayip) tamaminda basarisiz.
- **`EA4–EA6 PASS` (Kilitli `S5.5` Pencere & Donanim):** Erimeden calisan kesintisiz pencere `t_pulse in [0,077, 12,92] ms x T_peak in [1223,6, 1543,6] K`. Optimal **`808 nm / 1,0 ms / 1440,3 K` (`F = 41,15 J/cm^2`)**: **`f_act = %99,98`**, **`sigma_anneal = 0,328 nm <= 0,50 nm`**, yuzey+vakum kaybi **`%0,022`**, `29Si` karisimi **`sigma_iso = 0,0314 nm`**, arka yuz `592,9 K`. `Exp124` toplam konum hatasi `3,674 -> 3,655 nm` iyilesir; `16x16 mm` kriyo toparlanma `3,18 dk` (hat-ici RT yuk-kilidi bazinda `0,00 dk / 0 J`). `S5.5` donanimi: `+Y` CF63 safir (`Ø44 mm` CA, `T_AR=%98`, `9,47x` LIDT), `10 us` pirometre, MXC `<1 K` deklansor (`$95k` `RFQ-07A`).

durum: desteklendi (6/6 PASS: EA1-EA6 PASS; Risk R6 kuramsal/surec/optik sartname duzeyinde kapandi, M1 G4 lab acik)

## H149 (Exp131, 2026-11-23) — M4 olceklenebilir mimari: 3 kOhm NbTiN kavite-QED veri yolu, flip-flop kubit & 2B perkolasyon

`4x4` Tosi flip-flop + kesin `12x12` (`144x144` CUDA `matrix_exp`) Lindblad veri yolu + `N_mc = 2.000` 2B perkolasyon (`results/exp131_scalable_m4_architecture/exp131.json`, `tests/test_exp131.py` 7/7 PASS, `no_lab_measurement=true`, QA `#124` KABUL):
- **Epitaksiyel kaplama & empedans duvari (`CM1, CM2 PASS`):** Kaplamasiz `Delta z_cap = 0` `%24,15`'te coker; optimal **`Delta z_cap* = 8,0 +- 1,0 nm`** yerel DC ayarla verimi **`%95,20`** (`C_med = 2.800,1`, `g_eff = 0,620 MHz`). `60` heterojen ciftte `50 Ohm` CPW **`F_Bell = 0,7908`** ile cokerken **`3 kOhm NbTiN`** **`F_Bell = 0,9655`** (`0,359 us`, `M4 Best-of-6`; secimsiz `0,9386`).
- **Durust gurultu sinirlari (`CM3, CM4 FAIL`):** Yankisiz Markovian `1/f` (`S_eps = 0,5 ueV/rtHz`) altinda `(4 kOhm, Q=5e5)` `F_Bell = 0,9877` (`-0,0023`); Tosi `S_eps = 0,25 ueV/rtHz` oksitte **`0,9907–0,9918`** yuzey-kodu esigini asar. Adyabatik `CZ` (gurultusuz `0,9982`): `S_eps = 1,0 -> F_avg = 0,7768`, `S_eps = 0,25 -> 0,9392` (med `0,9554`) -> `M4` evrensel `CZ` icin `S_eps <= 0,25-0,35 ueV/rtHz` veya `1/f` yanki zorunlu.
- **2B Yuzey Kodu vs Heavy-Hex & Donanim (`CM5, CM7 PASS; CM6 FAIL`):** `p_M4 = 0,4855` altinda 2B Kare `N_cand = 3` `%100,0` sizar, **`N_cand = 6`** (`L=11`, `<=%5` olu) **`%99,40`** (`Binom %99,24`); Heavy-Hex `N_cand = 4` `%98,35` (`CM6 FAIL`), `%99` icin `N_cand = 5` (`-%40` daha az aday yuva ile 2B Kare kazandi). Donanim: `L_res = 300 um`, **`B_M4 = 0,1785 T`** (`%40,5` marj), `P_node = 10 um`, `968` DC kapi `4 K SKY130` capraz-anahtar (`$245k` `RFQ-07C`).

durum: kismen desteklendi (4/7 PASS: CM1,2,5,7 PASS; CM3,4,6 FAIL; 3 kOhm NbTiN & 2B yuzey kodu kilitlendi)

## H150 (Exp132, 2026-11-23) — Kapali dongu Bayesyen uyarlamali spektroskopi (BOED) & CellISA v3.0 coklu-hucre M4 derleyici

3-asamali BOED spektrometresi (`src/machine_control/adaptive_spectroscopy.py`) + `CellISA v3.0` (`WAFER_MAP_ROUTE`, `BUS_TUNE`, `BUS_CZ`, `LOGICAL_ENCODE`) (`results/exp132_bayesian_spectroscopy_cellisa3/exp132.json`, `tests/test_exp132.py` 6/6 PASS, `41/41` yazilim/on-uc/RTL pytest (`Exp135` oncesi 6-dosya; `Exp135` ile `47/47`), `no_lab_measurement=true`, QA `#121` KABUL):
- **BOED `24,37x` ham okuma hizlanmasi (`DA1–DA4 PASS`, `$0` ek donanim):** `N = 2.000` Mod B (`f=%1`) MC'de ortalama sure `1.000 ms ->` **`41,03 ms`** (medyan `23,04 ms`; bos `0,73 ms`, kalabalik `14,58 ms`, calisan `74,49 ms`). `7.952` cizgide **`RMS = 72,67 Hz`** (`CRLB = 58,19 Hz`, `2,75x` daha keskin), **`FNR = %0,20`**, **`FPR = %0,00`**. Fabrika verimi yazma tavanina dayandi: `1.024 @ 15 ms` -> **`1,503e9 reg/gun` (`7,61x`)**; `1.024 @ 10 ms` -> **`2,254e9 reg/gun` (`11,42x`)**.
- **`CellISA v3.0` & `Exp126` koprusu (`DA5, DA6 PASS`):** `N=200` `%51` verimli `4x4` yongada `4`-hucre yonlendirilebilirlik **`%97,0`** (ort `1,009` hop), `6`-hucre `%89,0`. Ornek `4x4` `M4` Kraus kanali: **`min_bus_cz = 0,988923`**, **`F_joint = 0,983448`**, `bitflip3_plus_ancilla` **`p_L = 3,65e-4` (`30,3x` baskilama)**, `SHA-256` imzali; `verify_with_exp126_bridge()` `Exp126` defterine canli bagli.

durum: desteklendi (6/6 PASS: DA1-DA6 PASS; `$0` ek HW ile 7,61x-11,42x fabrika hizlanmasi & CellISA v3.0)

## H151 (Exp133, 2026-11-23) — Kuple titresim, 40-elemanli kolon FEM, termal suruklenme & 6-DOF PT420 ayrıştırma kapanisi

`CAD v3.0` (`956,903 kg`) uzerinde `40`-elemanli Euler-Bernoulli FEM + `6-DOF` PSD/zaman-alani Parseval + termal suruklenme modeli (`results/exp133_coupled_vibration_thermal/exp133.json`, `tests/test_exp133.py` 12/12 PASS, `no_lab_measurement=true`, QA `#118` KABUL):
- **Rijit `PT420` cokusu (`CY1–CY3 PASS`):** Kolon `f_1 = 118,178 Hz` (ag farki `1,24e-7`, Parseval `%0,086`). Rijit `CAD v3.0` koprusu (`CFG1`) **`sigma_stage = 2.051,97 nm`** (`CFG5` `25 dB` FF ile bile `145,59 nm` RED); yalniz mekanik ayristirma (`CFG2` acik-cevrim) `1,0063 / 2,3617 nm` ile hâlâ `>0,50 nm`.
- **`CAD v4.0` kilitli `CFG4` cozumu (`CY4–CY8 PASS`):** `500 mm` uzak valf + `600 mm` esnek He hatti + `k_bellows = 2.000 N/m` (`<= 6.282 N/m`) 316L CF63 koruk + `4x` S-ilmek OFHC Cu orgu `k_braid = 52,7 N/m` (`<= 4.197 N/m`, `Delta T = 3,7 mK`) + `43,57 Hz` PID (`PM=55,23 deg`, `GM=8,69 dB`, `||S||_inf=1,676`) + `25 dB` harmonik FF (`VC-E` zemin): **`sigma_stage = 0,1024 nm`**, **`sigma_pointing = 0,1473 nm`**, **`sigma_thermal = 0,0283 nm`** (`Zerodur + Invar-36 + 20 mK`; naif 316LN `1,935 nm` RED). Birlesik `Exp124` toplam hatasi **`3,6397 nm` (`15 ms`) / `3,5974 nm` (`10 ms`) <= 3,80 nm** (`$68k` `RFQ-07B`).

durum: desteklendi (8/8 PASS: CY1-CY8 PASS; PT420 dekuplaj mekanik/kontrol paketi CAD v4.0'a kilitlendi)

## H152 (Exp134, 2026-11-23) — Fab birim ekonomisi, 5-yillik TCO, Wright ogrenme & v3.0->v4.0 deger analizi

`N = 50.000` korelasyonlu MC (`seed=2026134`) ile `v3.0 -> v4.0` 5-yillik TCO, Rejim I/II birim maliyeti & Wright (`b=%85`) ogrenme analizi (`results/exp134_fab_economics_tco/exp134.json`, `tests/test_exp134.py` 7/7 PASS, `no_supplier_quotes=true`, QA `#115` KABUL):
- **TCO & `$100M` tavan guvenligi (`CX1, CX2, CX3, CX5, CX6 PASS`):** `v4.0` donanim artisi `+$420k` (`M3 = $4,61M`); yillik sabit OPEX `$1,124M -> $1,162M/yil`; 5y Fab (`N=1`) TCO **`$15,23M -> $16,07M`** (`M1 Lab $8,62M`; FOAK `$36,73M -> $39,66M`, `P95 = $97,19M < $100M`). Program `P50 = $30,96M`, `P(>$50M) = %20,94`, **`P(>$100M) = %3,19 +- %0,08 < %5`**.
- **Rejim I kapasite kaldiraci:** `v3.0` `$52,89 uUSD/reg` -> `v4.0-5x` **`$11,15 uUSD/reg` (`-%78,9`)** (`46,3x` CAPEX / `80,0x` TCO kaldiraci); `15 ms` tavaninda `$7,32 uUSD/reg`, `10 ms`'de **`$5,58 uUSD/reg` (`-%89,5`)**, `d=17` mantiksal kubit `$0,0063`. Wright (`b=%85`, `N=1->100`): HW `$4,61M -> $1,57M` (`-%66,0`), 5y TCO `$16,07M -> $7,24M`.
- **Rejim II silisyum-zemini kesfi (`CX4 FAIL`):** Yogun `M4` (`5e7 reg/w, 1 s` mekik) fab ciktisini `3,20x` artirip makine payini **`-%67,0`** (`$0,616 -> $0,203/cip`) dusurse de `$2,40/cip` ham `28Si` epi yongasi toplam `$2,603/cip` bedelin **`%92,2`'sini** kilitlediginden toplam cip dususu **`-%13,7 < %50`** kalir.

durum: desteklendi (5/6 PASS: CX1,2,3,5,6 PASS; durust CX4 FAIL silisyum zemini; success_rule_met=true)

## H153 (Exp135, 2026-11-23) — Uctan uca v4.0 tam makine dijital ikizi (Exp124-Exp134 + canli kontrol yigini)

`11/11` `Exp124–Exp134` birincil JSON'unu `SHA-256` ile baglayan 8-katmanli birlesik dijital ikiz + canli `Factory`/`AtomCellProgrammer`/`MultiCellProgrammer` entegrasyonu (`results/exp135_v4_digital_twin/exp135.json`, `v4_digital_twin_cert.json`, `tests/test_exp135.py` 6/6 PASS, `no_lab_measurement=true`, QA `#137` KABUL):
- **Birlesik `v3.0 -> v4.0` kazanimi (`DT1, DT2, DT4, DT5 PASS`):** Yerlestirme **`3,6201 nm` (`15 ms`) / `3,5776 nm` (`10 ms`)** (`<= 3,80 nm`); IBIC x flas-tavlama sagkalimi **`%99,914`**; BOED `KL %51` -> **`1,502e9 / 2,253e9 reg/gun` (`7,61x / 11,42x`)**, birim maliyet **`$7,33` (`-%86,15`) / `$4,88` (`-%90,77`) `uUSD/reg`** (`d=17 = $0,0083 / $0,0055`). Risk `R1` **`VOKL-6 HM5962 (%33,25)`** altinda dahi erken iptalle `t_BOED = 29,87 ms` -> **`9,794e8 / 1,469e9 reg/gun` (`v3-KL`'nin `4,96x / 7,44x`'i, `$11,24 uUSD/reg` `-%78,75`)** tamamen YAZMA-SINIRLI kalir.
- **`Exp131 x Exp129` `M4` perkolasyon carpismasi (`DT3 PASS`):** `VOKL-6 HM5962 f=%1` (`p_M4 = 0,31654`) altinda kanonik `N_cand = 6` **`%3,12`'ye coker**; `L=11` `>=%99` FT icin **`N_cand* = 11` (`%99,74`)** gerekir (`HM5962 f=%2` ile `N_cand* = 6` `%99,92` geri kazanilir; `VOKL-6 norm` `N_cand* = 86` kirmizi cizgi).
- **Kontrol yigini & `SHA-256` dosya butunlugu ozeti (`DT6, DT7 PASS`):** BOED-taranmis `4x4` model yonga (`40,82 ms/yuva`, `MultiCellProgrammer` **`F_joint = 0,983448`**, **`min_bus_cz = 0,988923`**); `v4_digital_twin_cert.json` `SHA-256 = feffc1d4ba2b0698c3f61015c6684da47f57ea863a8b3e0da845cc9c71914b57` (yalnizca dosya butunlugu/provenans ozeti; fiziksel dogrulama degildir); sifir hardcoded yol, `0` GFM hatasi.

durum: desteklendi (7/7 PASS: DT1-DT7 PASS; success_rule_met=true; v4.0 dijital ikiz dosya ozeti kayitlandi)

## H154 (Exp136, 2026-11-23) — Atomistik 10-bant sp3d5s* tight-binding hiperince, R331 cekirdek polarizasyonu & optimal 29Si orani f*

Elmas orgude `16.000` atom / `160.000` orbital Boykin-Klimeck `sp3d5s*` 10-bant TB + `31P` cozucusu (`results/exp136_tb_sp3d5s_hyperfine/exp136.json`, `tests/test_exp136.py` 10/10 PASS, `no_lab_measurement=true`):
- **Atomistik `R331` atilimi (`TB1, TB2, TB3 PASS`):** `Exp129` `VOKL-6` `%64,73` sapmasi atomistik `sp3d5s*` ile **`%21,1`** (`alpha_cp = 0`) / **`%25,7`** (`alpha_cp = 0,015`) duzeyine dustu (`3x` iyilesme; `log10-RMS = 0,2426` vs `VOKL-6` `0,7445`). `TB4 FAIL`: cok-kabuklu tum-ENDOR hedefi hala all-electron DFT ister (`TB5 FAIL`: Stark kaymasi dogrulandi ama hedef tek-kabuk esigi tutmadi).
- **Optimal `29Si` bollugu `f*` & `E_z` Stark taramasi (`TB6 PASS`, `TB7 FAIL`):** `f = %1,0` Mod B verimi **`%52,75`** (`M4` `%99,74`), **`f* = %1,5 + 2 MV/m` Stark** ile **`%77,50`** (DDRF `6,89 kHz` sinirli **`%54,00`**, `M4` **`%99,88`**), `f* = %2,0` **`%59,75`** (`M4` **`%99,99`**). `XY8` elektron koheransi **`T2e = 10,8–20,3 ms`** (`TB7 FAIL`: en siki ayni-anda `f*` + ciplak Hahn-echo `>= 10 ms` esigi `XY8` gerektirir).

durum: kismen desteklendi (4/7 PASS: TB1,2,3,6 PASS; durust TB4,5,7 FAIL; R331 %64,73->%21,1 ve f*=%1,5+2 MV/m Stark kilidi)

## H155 (Exp137, 2026-11-23) — 1/f gurultulu M4 3 kOhm NbTiN veri yolunda yankili (Echo) CZ kapisi (Exp131 CM4 kapanisi)

`12x12` CUDA kesin Lindblad + `M = 40` Ornstein-Uhlenbeck renkli `1/f^alpha` zaman-serisi cozucusu (`results/exp137_echoed_m4_bus_gate/exp137.json`, `tests/test_exp137.py` 8/8 PASS, `no_lab_measurement=true`):
- **Yankili `P4` protokolu & enine `dg` bastirma (`EC1, EC3, EC6, EC7 PASS`):** `P4` (`XY4-DRAG-Echo-CZ`) enine baglasim `dg` cezasini **`5,09x`** bastirir (`EC6 PASS`); tam `16`-elemanli Pauli kanali `Exp138` yuzey-kodu dekoderine ihrac edildi (`EC7 PASS`).
- **Durust `1/f` esik duvarlari (`EC2, EC4, EC5 FAIL`):** Pasivesiz `S_eps = 1,0 ueV/rtHz`'de `P4` `F_Bell = 0,9587` (`0,9824` hizli ciftler) — tek basina yanki `S_eps = 1,0`'da `%99` esigini gecemez! **`Exp139` Rota C arayuz pasivasyonu ile birlikte:** `(Q_L = 2e5, S_eps = 0,50 ueV/rtHz)` -> **`F_Bell = 0,9901`**, **`(Q_L = 5e5, S_eps = 0,25 ueV/rtHz)` -> `F_Bell = 0,9949`, `F_avg = 0,9926`, `p_err = %0,92 < %1`** (yuzey kodu esigi altinda!).

durum: kismen desteklendi (4/7 PASS: EC1,3,6,7 PASS; durust EC2,4,5 FAIL; pasivesiz 1,0 ueV/rtHz yetersiz, Rota C ile F_Bell=0,9949 / p_err=%0,92)

## H156 (Exp138, 2026-11-23) — Kusurlu dondurulmus yuzey kodu (d=3..11) kesin Edmonds Blossom MWPM hata-tolerans kapanisi

`d = 3, 5, 7, 9, 11` tam CSS cebiri + `Exp137` `pauli_16` + `Exp140` `p_meas = %0,386` + `Exp126` `p_1q = %0,083` + `Exp136` `p_idle,Z = %0,032` uzerinde kesin Edmonds Blossom MWPM dekoderi (`results/exp138_defective_surface_code_ft/exp138.json`, `tests/test_exp138.py` 10/10 PASS, `no_lab_measurement=true`):
- **Hata-tolerans esigi & kriyostat filosu (`FT1, FT2, FT3, FT4, FT6, FT7 PASS`):** Dongu-basi esik **`p_2q,th = %1,60 +- %0,17`** (`Z: %1,62`, `X: %1,75`). Negatif kontrol `v4` ciplak `P1`: **`Lambda = 0,00`** (`FAIL`). `v5` Rota C gecisi: `C2 (Q=2e5, S=0,390)` **`Lambda = 1,04`**, `D1 (Q=5e5, S=0,390)` **`Lambda = 1,26`**, **`D2 (Q=5e5, S=0,25, p_2q=%0,92)` `Lambda = 1,40`** (`10^-9`: `d* = 99`, `679` kriyostat), **`D3 (p_2q=%0,50)` `Lambda = 2,52`** (`10^-9`: `d* = 37`, `100` kriyostat, `1 L/kriyo` bolunmez, **`6,8x` filo kuculmesi**).
- **Durust kusurlu-kafes bulgusu (`FT5 FAIL`):** `f = %1, N_cand = 6` (`p_drop = %1,31`) Auger agirlik-8 delikleri nedeniyle `d_eff/d = %79,0 < %85` verir; **`f* = %1,5 + 2 MV/m Stark + N_cand = 6`** (`p_drop = %0,021`) **`d_eff/d = %99,5`** ile kusursuzluga ulasir.

durum: desteklendi (6/7 PASS: FT1,2,3,4,6,7 PASS; durust FT5 FAIL; success_rule_met=true; D2 Lambda=1,40 / D3 Lambda=2,52)

## H157 (Exp139, 2026-11-23) — 8 nm 28Si epitaksiyel kapak surec entegrasyonu, gizli TED kesfi, 1530 K cozum & S5.6 MBE donanimi

`Exp131` `Delta z_cap* = 8 nm` kapagi icin kuple BCA + geri-tepme oksijen + LT-MBE + McWhorter 2B yuk-gurultusu + kuple TED modeli (`results/exp139_epi_cap_process_integration/exp139.json`, `tests/test_exp139.py` 9/9 PASS, `no_lab_measurement=true`):
- **Kritik fiziksel kesif (`EP3, EP5, EP7 FAIL`):** `v4.0` `1440 K` (`41,15 J/cm2`) flas tavlamada `{311}` kusur kumelerinin `%13,6`'si sag kalir ve LT-MBE kaplama sirasinda **`+1,318 nm` gizli arka-uc TED** yaratarak toplam yerlestirmeyi **`3,995 nm > 3,80 nm` FAIL** eder!
- **`v5.0` `1530 K` kume-temizleyici cozum & Rota C (`EP1, EP2, EP4, EP6 PASS`):** Flas sicakliginin **`1530 K` (`43,49 J/cm2`)** yukselmesiyle `{311}` kume temizligi **`%99,99`**, **`sigma_anneal = 0,430 nm`**, birlesik **`sigma_tot = 3,665 nm <= 3,80 nm` PASS** (`Exp141` `CFG4`: `3,6307 / 3,5883 nm`) olur. **Rota C** (`345 C` LT-MBE + `350 C` FG/H pasivasyonu) yuk gurultusunu **`S_eps = 0,390 ueV/rtHz`**'ye (`2,57x` dusus), flip-flop verimini **`p_ff = %97,70`**'e cikarir. **`S5.6` MBE kapak modulu:** `22,4 kg`, `` `$95k` `` (`RFQ-08`), `0 uW` kriyo yuku, `%0` akis cezasi.

durum: kismen desteklendi (4/7 PASS: EP1,2,4,6 PASS; durust EP3,5,7 FAIL; v4 gizli TED kesfedilip v5 1530 K + Rota C + S5.6 MBE ile model uzayinda iyilestirildi, deneysel lab acik)

## H158 (Exp140, 2026-11-23) — Q16.16 FPGA BOED DSP, TWPA/Purcell N_mux* = 32, 1024/2887 kriyo tavani & CellISA v3.5

`ZCU216` sabit-nokta `Q16.16` FPGA BOED DSP (`src/machine_control/fpga_boed_dsp.py`), Purcell-filtreli TWPA okuma ve `CellISA v3.5` (`17` opcode) (`results/exp140_cryo_fpga_boed_mux_readout/exp140.json`, `tests/test_exp140.py` 7/7 PASS, `no_lab_measurement=true`):
- **FPGA DSP & `N_mux* = 32` (`FM1–FM4 PASS`):** `Q16.16` FPGA FP64 esitligi **`abs(Delta RMS) = 0,0502 Hz`**, dongu-kesin gecikme **`2,336 us/adim`**, kaynak **`%10,49` DSP48E2**. Fiziksel çoklama tavanı **`N_mux* = 32`** (`F_RO = %99,61`, **`625x` Purcell** bastirma; `N_mux = 64` `%94,13` FAIL).
- **Kriyostat tavanı & `CellISA v3.5` (`FM5–FM7 PASS`):** **`1.024` hucre `4/4` termal kademede PASS**; tek `LD400/PT420` kriyostat fiziki tavani **`2.887` hucre** (`20 mK` MXC darbogazi); `10.000` hucre **`>= 4` moduler kriyostat** gerektirir. **`CellISA v3.5`** `17` komut (`+ ECHO_CZ, MUX_READOUT, SYNDROME_CYCLE`). **`S6.5` (`S6.11`) donanim:** `19,27 kg`, `` `$629,2k` `` (`RFQ-08`).

durum: desteklendi (7/7 PASS: FM1-FM7 PASS; Q16.16 FPGA, N_mux*=32, 2.887 hucre/kriyo & CellISA v3.5 kilitlendi)

## H159 (Exp141, 2026-11-23) — Master v5.0 uctan uca hata-toleransli dijital ikiz, wafer CX4 model yinelemesi & SHA-256 dosya ozeti

`17/17` birincil deney (`Exp124–Exp140`) + `CAD v5.0` (`189` parca, `1.034,94 kg`, `38.876` STL ucgen, `0/17.766` nominal cakisma, `32/32` bosluk, `27/27` test) + `BOM v5.0` (`167` parca, `` `M3 = $5.247.800` ``, `` `M1 = $2.466.120` ``, `8-RFQ = %76,4` nom / `%92,6` MC var, `` `P(Prog > $100M) = %4,23 < %5` `` [FOAK 5y TCO `%5,91`]) = `19/19` artefakti birlestiren master dijital ikiz (`results/exp141_v5_digital_twin/exp141.json`, `v5_digital_twin_cert.json`, `tests/test_exp141.py` 9/9 PASS, `23/23` staged test dosyasi `198/198` PASS, `no_lab_measurement=true`, `no_supplier_quotes=true`):
- **Birlesik fizik & kontrol yazilimi (`DT5_1–DT5_5 PASS`):** Yerlestirme **`3,6307 nm` (`15 ms`) / `3,5883 nm` (`10 ms`)** (`v4` gizli TED `3,9634 nm` FAIL'i model uzayinda iyilestirildi); `Q16.16` FPGA `abs(Delta RMS) = 0,0183 Hz`; `CellISA v3.5` `Bare CZ = 0,7791 ->` **`ECHO_CZ = 0,9818 (+20,27 pp)`**, `F_syn = 0,9427`, `T_cyc = 2,620 us`; yuzey kodu `P1 (Lambda=0) -> D2 (Lambda=1,40) -> D3 (Lambda=2,52, 679->100 kriyostat)`.
- **Wafer `CX4` maliyet tabaninin model uzayinda asilmasi & durust mantiksal kubit ekonomisi (`DT5_6–DT5_8 PASS`):** **`W2`** (`30 nm` `200 mm` SOI `` `$2,2k` ``, `` `$0` `` makine degisikligi -> `` `$0,616/cip` ``, **`-%79,5`**, `CX4 PASS`) ve **`W3`** (`300 mm` SOI `` `$3,6k` `` -> `` `$0,442/cip` ``, **`-%85,3`**, `CX4 PASS`) *(tamami model/varsayim; tedarikci teklifi yok)*. `10^-9` mantiksal kubit: **`D2`** fab `` `$/L_fab = $5,20` `` / dagitilmis 100L kriyo `` `$/L_sys = $14,94M` `` vs **`D3`** `` `$/L_fab = $0,73` `` / `` `$/L_sys = $2,76M` `` (**`5,41x` ucuz**). Tam 64-hex `v5_digital_twin_cert.json` **`SHA-256 = 2828e8ce8d9388f7cba5490b2d05add930aadc5fe6d3ba4295f0380f816d43d1`** *(yalnizca dosya butunlugu/provenans ozeti; fiziksel dogrulama degildir)*.

durum: desteklendi (8/8 PASS: DT5_1-DT5_8 PASS; v5.0 dijital ikiz, CX4 SOI modeli & 19/19 SHA-256 dosya butunlugu kayitlandi)


## H160 (Exp142, 2026-11-23) — Option-Q: 50 Ohm <-> 3 kOhm qRAM bellek koprusu & S1-Multi cok-turlu platform (167Er 1536 nm + 121Sb qudit)

Tak-cikar **`Option-Q`** (`5`-kademe Chebyshev `50 Ohm <-> 3 kOhm` empedans donusturucu + `12x12` Lindblad transmon-`31P` `SWAP` koprusu + `S1-Multi` `167Er`/`121Sb` cok-turlu kaynak kartusu, `results/exp142_option_q_multispecies_qram/exp142.json`, `s9q_hardware_spec.json`, `tests/test_exp142.py` 10/10 PASS, `no_lab_measurement=true`):
- **Superiletken `qRAM` koprusu (`OQ1, OQ2, OQ3 PASS`):** `5`-kademe Chebyshev donusturucu gecis kaybi **`IL = 0,0004 dB`** (`0,000375 dB`), bant genisligi **`BW = 5,20 GHz`**, donus kaybi `S11 = -39,56 dB`. Gidis-donus `SWAP` sadakati **`F_SWAP_rt = 0,9858`** (`0,98575`); `31P` cekirdek bellegi transmona kiyasla **`8.403x` (`1 s` DD) – `25.122x` (`3 s`)** saklama omru kazanci saglar; kriyojenik isi yuku yalniz **`+0,78 uW @ 20 mK`** (mevcut `LD400` tavanini bozmaz).
- **`S1-Multi` telekom `167Er` & `121Sb` qudit (`OQ4, OQ7 PASS`; durust `OQ5, OQ6 FAIL`):** `167Er` (`1536 nm` C-bant) `10 km` SMF-28 fiberde **`1.352,3 Hz`** (`F = 0,9474`) dolaniklik uretir. `7,5 keV 121Sb` (`I = 7/2`, `8`-seviye qudit) `-%41,5` (`-%41,46`) daha keskin yanal sacilma verir ancak yuksek-enerji derinlik/kuadrupol gerinim duvari nedeniyle `OQ5/OQ6` durustce `FAIL` almistir. **`Option-Q` donanim paketi:** **`9,20 kg`** (`S1.7-01` `4,80 kg` + `S9.4-01..03` `4,40 kg`), `` `$168.000` `` (`` `$118k–$242k` ``, `RFQ-09`).

durum: kismen desteklendi (5/7 PASS: OQ1,2,3,4,7 PASS; durust OQ5,6 FAIL; qRAM 8.403x-25.122x & 10 km 167Er 1.352,3 Hz kilitlendi)

## H161 (Exp143, 2026-11-23) — D3 K=8 Fourier GRAPE M4 kapisi (p_2q <= %0,45) & Option-HPC 100 Gbps RDMA gercek-zamanli dekoder

`12x12` CUDA Strang-Lindblad + `M = 40` OU `1/f^alpha` uzerinde `K = 8` Fourier GRAPE `M4` `CZ` sentezi, canli `Exp138` MWPM koprusu ve **`Option-HPC`** `100G` RoCEv2 RDMA gercek-zamanli dekoder mimarisi (`results/exp143_d3_grape_m4_and_hpc_decoder/exp143.json`, `s9hpc_hardware_spec.json`, `tests/test_exp143.py` 9/9 PASS, `no_lab_measurement=true`):
- **`D3` `K=8` Fourier GRAPE `M4` kapisi (`DH4 PASS`; durust `DH1,2,3 FAIL`):** `0,894 us` (muhaf.) / `1,126 us` (yankili) darbe (`%100 <= 300 MHz` AWG bant genisligi, CPTP temiz): yankili `Q = 1e6, S_eps = 0,390 ueV/rtHz ->` **`p_2q = %0,395`** (`<= %0,45`), **`S_eps = 0,25 ueV/rtHz -> p_2q = %0,337 (F_avg = %99,73, F_Bell = %99,69)`**, muhafazakar `high-g -> %0,481`. Canli `Exp138` Edmonds Blossom MWPM **`Lambda_D3_phys = 2,825`** (`100L` yuzey kodu `679 -> 100` kriyostat, `6,8x` kuculme). (`DH1`: gurultusuz sizinti `1,37e-4 > 1e-4`; `DH2/3`: muhafazakar/yankisiz alt-kosullar durust `FAIL`.)
- **`Option-HPC` `100G` RoCEv2 RDMA dekoder gecikme sinirinin model uzayinda cozulmesi (`DH5, DH6, DH7 PASS`):** `tau_ingest = 777 ns`; `d = 37` yuzey kodu E2E **`6,34 us < 6,70 us`** ve **`qLDPC 108L` BP-OSD E2E `2,32 us < 2,62 us`** (`backlog-free`). Donanim (`S9.HPC-01..03`): tek `4U` 2-dugumlu raf, **`64,0 kg`**, `2.195 W` (`0 W` kriyo), `` `$132.000` `` (`` `$98k–$181k` ``, `RFQ-09`).

durum: kismen desteklendi (4/7 PASS: DH4,5,6,7 PASS; durust DH1,2,3 FAIL; D3 GRAPE p_2q=%0,337-%0,395, Lambda=2,825 & Option-HPC 2,32 us kilitlendi)

## H162 (Exp144, 2026-11-23) — 300 um M4 veri yolu uzerinde qLDPC [[144,12,12]] Gross Code & tek-kriyostat 108L-120L devrimi

Bravyi (Nature 2024) kalinlik-2 Bivariate Bicycle (`[[72,12,6]]`, `[[90,8,10]]`, **`[[144,12,12]]` Gross Code**) kesin `GF(2)` cebri, derinlik-7 sifir-geri-tepmeli CNOT cizelgesi, katli-torus `M4` yerlesimi ve 3B devre `DEM` + `BP+OSD-2` dekoderi (`results/exp144_qldpc_bivariate_bicycle_m4/exp144.json`, `tests/test_exp144.py` 10/10 PASS, `no_lab_measurement=true`, `no_supplier_quotes=true`):
- **Sifir rezonator yeniden tasarimi & blok verimi (`QL1, QL2, QL6 PASS`):** `P_cell = 20 um` ile **`L_max = 268,3 um <= 300 um`** (`Exp131` `3 kOhm NbTiN` rezonatorune birebir sigar, `0` yeniden tasarim!). Stark'siz `f=%1, N=6` `%2,23` cokerken **`f* = %1,5 + 2 MV/m, N_cand = 8`** ile **`%99,64` blok / `%99,94` `108L` yonga verimi** elde edilir.
- **3B `BP+OSD-2` esigi & `234x` sistem maliyeti sikistirmasi (`QL3, QL4, QL5, QL7 PASS`):** `OSD-2` saf `BP`'yi `12,92x` yener; devre esigi **`p_th = %0,633`** (`d_eff = 12,81`); `D3+` (`%0,30`) mantiksal hata **`2,1e-5/1L`** (`5,2x` daha iyi, `10,0x` daha az hucre vs `d=11` SC). **`120L` (`10` blok = `2.880 <= 2.887` hucre) tek `LD400` kriyostatina sigar (`108L = 1` kriyostat: `` `$63.827/L_sys` ``, `v5 D2`'ye gore `234x` [`234,06x`], `D3` SC'ye gore `43,23x` ucuz; `W3` silikon fab `` `$0,0085/L_fab` ``)!**

durum: desteklendi (7/7 PASS: QL1-QL7 PASS; [[144,12,12]] qLDPC 108L tek kriyostat & `$63.827/L_sys` kilitlendi)

## H163 (Exp145, 2026-11-23) — CellISA v4.0, 156Q ibm_marrakesh (IBM Heron r2) silikon-disi kontrol vekili kosumu & auto_recal.py

Sifir-`qiskit` saf-`requests` IBM Quantum Platform 2026 REST koprusu (`src/machine_control/cloud_qpu_bridge.py`), `20`-komutlu **`CellISA v4.0`** (`+ QRAM_SWAP, QLDPC_ROUND, AUTO_RECAL`) ve otonom ariza kurtarma (`src/machine_control/auto_recal.py`) (`results/exp145_cloud_qpu_ibm_validation/exp145.json`, `ibm_qpu_live_results.json`, `tests/test_exp145.py` 12/12 PASS):
- **Epistemik ayrim:** Silikon `31P` fabrikasyon ve `auto_recal.py` `M0` modelidir (`no_lab_measurement=true`); **`CellISA v4.0 -> OpenQASM 3.0` kontrol, `Echo/XY4` DD, `d=3` sendrom dekoderi ve `Q16.16` BOED gercek `156`-kubitlik `ibm_marrakesh` (IBM Heron r2, `job_id = dc1tdo2nj2vs73dfrfl0`, `[q2,q3,q4,q5,q6]`, `16 PUB x 4.096 shot`, `32,54 s`) superiletken bulut QPU uzerinde silikon-disi yazilim/kontrol vekili (`proxy`) olarak kosturulmustur** (`{Canli-Donanim-IBM-QPU}`, `SECRET_LEAKS = 0` — silikon `31P` atom donanimi dogrulamasi degildir).
- **Superiletken `ibm_marrakesh` kontrol vekili sonuclari & `auto_recal` (`CQ1–CQ7` `7/7 PASS`):** Bare Idle `0,3325` -> **Hahn-Echo `0,9224` (`+59,0 pp`)** -> **XY4 DD `0,9280` (`+59,5 pp`)**; 2Q Bell **`F = 0,9733`**; `d = 3` tekrar kodu `p_phys = %2,96 ->` **MWPM `%0,57` (`5,16x`) / cogunluk `%0,38` (`7,83x`) / postsel `%0,00`** (`0/7.451` hata); bit-kesin **`Q16.16` BOED** `3`-nokta Ramsey **`120,11 kHz`** (FP64'ten **`1,6 Hz`** fark). **`auto_recal.py`** 4 ariza kipinde (`S5.5` lazer, `S5` UHV, `S3` `%5` olu blanker, `31P +-350 Hz` kayma) **`4/4 PASS`**.

durum: desteklendi (7/7 PASS: CQ1-CQ7 PASS; 156Q ibm_marrakesh silikon-disi kontrol vekili, CellISA v4.0 & auto_recal 4/4 kayitlandi)

## H164 (Exp146, 2026-11-23) — Master v6.0 dijital ikiz, 24/24 + QPU vekili SHA-256 dosya ozeti & moduler CAD/BOM v6.0

`22/22` deney (`Exp124–Exp145`) + `CAD v6.0` (`199` parca, `1.108,14 kg`, `39.536` STL, `0/19.701` nominal cakisma, `40/40` nominal bosluk, `30/30` test) + `BOM v6.0` (`174` parca, `` `M1 Base = $2.466.120` ``, `` `M3 Base = $5.247.800` ``, `` `Option-Q +$168k` ``, `` `Option-HPC +$132k` ``, `` `M3 Full = $5.547.800` ``, `9-RFQ = %77,7` nom / `%92,6` MC var, `` `P(Prog > $100M) = %4,92 < %5` `` [FOAK `%6,90`], `0,000 kg` CAD uyumu) + `ibm_qpu_live_results.json` (`24/24` + QPU vekili `SHA-256` provenans ozeti) birlesik master dijital ikizi (`results/exp146_v6_digital_twin/exp146.json`, `v6_digital_twin_cert.json`, `tests/test_exp146.py` 10/10 PASS; `28/28` staged test dosyasi **`252/252` yazilim regresyon testi PASS**):
- **`v3 -> v6` model-ici sistem sikistirmasi (`DT6_1–DT6_8` `8/8 PASS`):** `100L (10^-9)` kriyostat filosu **`679 (v5 D2 SC) -> 100 (v6 D3 GRAPE SC, 6,8x) -> 1 (v6 [[144,12,12]] qLDPC 108L, 679x)`**; dağıtılmış sistem maliyeti `` `$14,94M -> $2,76M -> $63.827/L_sys` `` (**`234,06x`** dusus; `W3` silikon fab `` `$0,0085/L_fab` ``).
- **`SHA-256` dosya butunlugu ozetleri (yalnizca provenans; fiziksel/muhendislik sertifikasyonu degildir):**
  - `v6_digital_twin_cert.json`: `ca3f0e0267263bacb973f46c3cc2d321c0f204075ea232f4094758e1a9abf1d7`
  - `ibm_qpu_live_results.json` (`ibm_marrakesh` kontrol vekili): `02b7a19d1704662c6424e76f4971e21b04a98d48230a917c9682853b3ca1fc5a`
  - *(Korunan tarihsel dosya ozetleri: `v5` `2828e8ce8d9388f7cba5490b2d05add930aadc5fe6d3ba4295f0380f816d43d1` · `v4` `feffc1d4ba2b0698c3f61015c6684da47f57ea863a8b3e0da845cc9c71914b57`)*

durum: desteklendi (8/8 PASS: DT6_1-DT6_8 PASS; v6.0 Master Dijital Ikiz, 24/24+QPU SHA-256 dosya butunlugu, 252/252 regresyon testi kayitlandi)

## H165 (Exp147, 2026-11-23) — Evrensel [[288,12,18]] (d=18) qLDPC, T-kapisi sihirli durum fabrikalari & FeMoco / RSA-2048 kaynak analizi

Bravyi (Nature 2024) **`[[288,12,18]]`** (`l=12, m=12`) kesin `GF(2)` cebri (`H_X H_Z^T = 0`, `rank = 138`, derinlik-7 `1.728` CNOT `0` geri-tepme), `Z_12` otomorfizmli (`b' = 5b mod 12`) `24x24` kalinlik-2 `M4` yerlesimi, 4-kodlu (`d = 6, 10, 12, 18`) 3B devre `DEM` + `BP+OSD-2`, Litinski/Gidney sihirli durum fabrikalari ve iki bayrak algoritma (**FeMoco** & **`RSA-2048` Shor**) tam kaynak/maliyet butcesi (`results/exp147_universal_qldpc_d18_magic_state/exp147.json`, `tests/test_exp147.py` 10/10 PASS, `no_lab_measurement=true`, `no_supplier_quotes=true`):
- **`[[288,12,18]]` `M4` uyumu & `3B BP+OSD-2` esigi (`UQ1, UQ2, UQ3 PASS`):** `P_cell = 20 um` ile **`L_max = 268,3 um <= 300 um`** (`0` rezonator yeniden tasarimi!), `f* = %1,5 + 2 MV/m` `576`-hucreli blok verimi **`%99,27 (N=8)` / `%99,82 (N=9)`** (Stark'siz `f=%1, N=6`: `%0,050` cokus); devre esigi **`p_th = %0,781`**, `Exp143 D3 (%0,337)` `0/1.200` hata (`< 3,55e-4`), `10^-9/1L` siniri `p_2q* = %0,127` (depol) / `%0,075` (`2 us` RO sinirli).
- **Sihirli durum fabrikalari & bayrak algoritmalar (`UQ6, UQ7 PASS`; durust `UQ4, UQ5 FAIL`):** `D3` (`Lambda_SC = 2,825`) altinda tek-kademe `15-to-1` `2,74e-6` (fail); `Cult + (116-to-12)` `p_T = 7,90e-11 @ 8,22 kHz` (`12` kriyostat; saf Litinski `32` kriyo & Cult+`15-to-1` `7` kriyo -> on-kayitli `<=15/<=6` sinirini astigindan durust `UQ4 FAIL`). **FeMoco (`192L, 10^8 T`):** **`16` kriyostat (`37,1x` sikistirma vs `593` SC), `3,38 sa`, `406,6 kW`, `` `$59,3M` `` TCO / `` `$6.537/cozum` `` (`35,3x` ucuz)** — ANCAK `2-3 us` okuma tavani (`p_meas = %0,22-%0,39`) `d=18` bellek hata tabanini sinirladigindan durust `UQ5 FAIL` (`p_meas <= %0,15` + `D3++` veya `d=24/34` gerekli!). **`RSA-2048` (`4.096L, 10^10 T`):** **`291` kriyostat (`52,7x` vs `15.327` SC), `7,37 MW` (`52,1x` vs `383,8 MW`), `21,1 sa`, `` `$711,3M` `` (`35,9x` ucuz, `UQ6 PASS`)**.

durum: kismen desteklendi (5/7 PASS: UQ1,2,3,6,7 PASS; durust UQ4,5 FAIL; [[288,12,18]] L_max=268,3 um, FeMoco 16 kriyo [37,1x] & RSA-2048 291 kriyo / 7,37 MW [52,7x] model sonuclari kayitlandi)

## H166 (Exp148, 2026-11-23) — 121Sb I=7/2 tek-atom qudit dinamik kuadrupol yankisi (Q-Echo-8) & SU(8) GRAPE kontrolu (Exp142 OQ6 model-ici yinelemesi)

`Exp142 OQ6 FAIL` (`500 Hz` kuadrupol gerinim engelinin `121Sb` Gross binomiyal kodunu `1 ms`'de `0,58` duzeyine cokertmesi) icin kesin `8x8`/`16x16` CPTP Lindblad, tugla-duvar `Q-Echo-8` (`P_brick^8 = I_8`) ve `11`-kipli `SU(8)` Fourier GRAPE cozumlemesi (`results/exp148_sb121_quadrupole_echo_qudit/exp148.json`, `tests/test_exp148.py` 9/9 PASS, `no_lab_measurement=true`):
- **Statik `500 Hz` `OQ6` engelinin model uzayinda iyilestirilmesi & `SU(8)` kapilar (`SQ1,2,3,5,6,7 PASS`):** Nötr `121Sb` (`473,9 kHz` NMR ayrilimi, `Omega = 25 kHz`, Levitt-Freeman kompozit `90-240-90` + kuadratur faz): **`Q-Echo-8`** statik `500 Hz` Gross sadakatini **`0,5800 -> 0,99908` (`455,5x` infidelite dususu)** ve `|+-7/2>` Cat sadakatini **`0,9424 -> 0,99914`** duzeyine cikardi (`iyonize 121Sb+ 70 kHz`'te RF capraz-etkilesim cokusu dogrulandi -> yalniz notr rejim). AC-Stark telafili `SU(8)` GRAPE (`104 us, <= 22,89 kHz`): **`X_L = 0,9954 / Z_L = 0,9971 / H_L = 0,9959`** (`500 Hz`: `>= 0,9851`).
- **Genis-bant `1/f` gerinimde durust Cywinski siniri (`SQ4 FAIL`):** `1 Hz - 100 kHz` `500 Hz rms` `1/f` gurultu altinda Cywinski `T_2,eff ~ N_cyc^{1/2}` yasasi nedeniyle tek-cevrim `Q-Echo-8` **`8,39x` (`0,433 ms`)** verip on-kayitli `>=20x / >=1 ms` hedefinin altinda kaldi (`SQ4 FAIL`); cok-cevrimli **`Q-Echo-64` `28,08x` (`1,45 ms`)**, `|+-7/2>` Cat **`20,73 ms`** (`0,9989 @ 1 ms`) ulasir. `31P` ana bellek omurgasi olarak ustunlugunu korur; `121Sb` notr-rejim `S1-Multi` yogun qudit yukseltmesidir.

durum: kismen desteklendi (6/7 PASS: SQ1,2,3,5,6,7 PASS; durust SQ4 FAIL; statik 500 Hz OQ6 engeli model uzayinda 455,5x infidelite dususuyle 0,99908'e iyilestirildi, deneysel olcum acik)

## H167 (Exp149, 2026-11-23) — Sentezlenebilir Q16.16 BOED-FPGA Verilog RTL (rtl/boed_fpga/) & sifir-CDN interaktif HTML5 model gezgini

`Exp140` `fpga_boed_dsp.py` sabit-nokta motorunun sentezlenebilir IEEE 1364-2005 Verilog RTL'ye (`rtl/boed_fpga/`, `10` dosya) indirilmesi ve tek-dosya cevrimdisi interaktif HTML5 parametrik model gezgininin (`docs/digital_twin_interactive.html`) uretimi (`results/exp149_boed_verilog_rtl_and_interactive_twin/exp149.json`, `tests/test_exp149.py` 10/10 PASS, `no_external_eda_sim=true`, `no_lab_measurement_rtl=true`):
- **Sentezlenebilir Verilog RTL & bit-kesin es-dogrulama (`RV1-RV5, RV7 PASS`):** `4` sentezlenebilir `.v` modulu (`boed_lut_rom.v`, `boed_isqrt_cordic.v`, `boed_q16_core.v`, `boed_top_16ch.v`, toplam **`894` satir**): `0` yasak/port/genislik hatasi, `1.024/1.024` ROM `.hex` kelimesi **`0`-bit fark**, `64/64` altin vektor + `1.000` `isqrt` **`0 LSB`** hata, kesin **`584` cevrim = `2,336 us @ 250 MHz`** (`4` cevrim SPRT), `ZU48DR` `16`-kanal `%10,49` DSP48E2 / `%5,93` BRAM36 / `0 W` kriyo. (`no_external_eda_sim=true`: konakta `iverilog`/`vivado` yok; Vivado sentezi sonraki adimdir.)
- **Interaktif HTML5 parametrik model gezgini (`RV6 PASS`):** `docs/digital_twin_interactive.html` (`v7.1` epistemik guncellemesiyle **`67,5 KB` [`67.505` bayt], `5` sekme, `0` harici CDN/HTTP, `0` sizinti**) birincil model JSON'larini ve `ibm_marrakesh` silikon-disi kontrol vekili verisini tarayicida etkilesimli olarak sunar.

durum: desteklendi (7/7 PASS: RV1-RV7 PASS; 894-satir Verilog RTL 0 LSB / 584 cevrim & sifir-CDN HTML5 model gezgini kayitlandi; no_external_eda_sim=true)

## H168 (Exp150, 2026-11-23) — On emniyet analizi, 25-satirli FMEA, 10-dugumlu HAZOP & S7.SAFETY M0 butce taslagi (SEMI S2 / IEC 61508 SIL-3 hedefi — sertifikasiz)

Temizoda bes kritik tehlikesi (`S5.5` Sinif-4 `808 nm` lazer, `S1.1` `PH3` + `S5.6` `%5 H2/N2`, `10-22 keV` HV/Bremsstrahlung X-isini, `20 mK/4 K` He ODH + `ASME DN50` + quench, EPO/UPS) icin indirgenmis-dereceli analitik emniyet modeli, 25-satirli FMEA, 10-dugumlu HAZOP ve **`S7.SAFETY-01..06`** M0 butce taslagi (`results/exp150_industrial_safety_fmea_hazop/exp150.json`, `s_safety_spec.json`, `tests/test_exp150.py` 12/12 PASS, `no_lab_measurement=true`, `no_supplier_quotes=true` — **resmi `SEMI S2 / IEC 61508 SIL-3` uyumu veya sertifikasyonu degildir; yalnizca M0 on tasarim hedefidir**):
- **5 tehlike on analizi & FMEA (`SF1-SF7 7/7 PASS`):** `25` FMEA `max RPN` **`280 -> 42 <= 60` (`-%86,3` ortalama, `0` artik `>60`)**; `OD=8 + 3 mm` celik Lazer+X-isini (`22 keV`: ciplak safir `10,11 uSv/h` -> **`1,19e-23 uSv/h`**, `3,2 ms` SIL-3 hedef perde, `PFD = 2,34e-5`); sub-atm `SDS PH3` **`0,00715 ppm << 0,05 ppm` ACGIH TLV-TWA** (`7x` marj; onlemsiz `1.207 ppm` IDLH felaketi sifirlandi); kuru He `60 m3` **`O2 = %20,57`**, `ASME DN50 0,5 barg` `16,37x/25,72x`, quench direnci `38,15 C`; `15 kVA` LFP UPS **`40,0 / 213,2 dk`** (`0 ms`), **`80 ms` UHV vana** (`6,0e-4 ML`).
- **`S7.SAFETY` M0 donanim butcesi & `BOM v7.0` (`RFQ-10` taslak):** `6` kalem = `` `$145.000` `` (`` `$92k-$220k` ``, `M3 v6 Full`'un `%2,61`'i), **`355,0 kg`** harici tesis emniyeti (`CAD v6` sasi `1.108,137 kg` degismez -> toplam `1.463,137 kg`), `1.090 W`, `0,0 W` kriyo.

durum: desteklendi (7/7 PASS: SF1-SF7 PASS; 25-FMEA max RPN 280->42 & S7.SAFETY M0 taslagi kayitlandi; SEMI S2/SIL-3 sertifikasyonu yoktur)

## H169 (Exp151, 2026-11-23; v7.1 guncellemesi 2026-11-24) — Master v7.0/v7.1 dijital ikiz, 38/38 SHA-256 dosya butunlugu ozeti, fazli BOM v7.0 (10-RFQ) & 306/306 yazilim regresyon testi

`27` deney JSON'u (`Exp124-Exp150`) + `ibm_qpu_live_results.json` (silikon-disi kontrol vekili) + `CAD v6.0` (`199p, 1.108,137 kg, 0/19.701 nominal cakisma, 40/40 nominal bosluk`) + `BOM v7.0` (`180p, 10-RFQ %78,24 nom / %92,58 var`, `` `$0,00` `` kopru, `0,0000 kg` sasi uyumu + `355,0 kg` tesis = `1.463,137 kg`) + `7` `rtl/boed_fpga/` dosyasi + `docs/digital_twin_interactive.html` (`67,5 KB`, `5` sekme, `0` CDN) = **`38/38` birincil eser `SHA-256` dosya butunlugu ozeti** master dijital ikizi (`results/exp151_v7_digital_twin/exp151.json`, `v7_digital_twin_cert.json`, `tests/test_exp151.py` 13/13 PASS; **`33/33` staged test dosyasi `306/306` yazilim regresyon testi PASS — kod tutarliligi; fiziksel donanim dogrulamasi degildir**):
- **Fazli `v7.0` tedarik & epistemik ayrim (`DT7_1-DT7_8 8/8 PASS`):** `M1 Base` `` `$2.466.120` `` (`M1+Safety` `` `$2.611.120` ``), `M3 Base` `` `$5.247.800` `` (`%4,44`), **Faz-1 onerilen `M3 Base+Safety` `` `$5.392.800` `` (`P>100M = %4,67 < %5`, `6/6 CU PASS`)**, `M3 v6 Full` `` `$5.547.800` `` (`%4,95`), durust **`M3 v7 Full` `` `$5.692.800` `` (`P>100M = %5,22 > %5` `CU3_v7_full FAIL`, FOAK `%7,25` -> Faz-1 -> `RFQ-05` kilidi -> Faz-2 `+Option-Q/HPC`)**. Silikon `31P/121Sb/167Er` + RTL EDA (`no_external_eda_sim=true`) + On Emniyet (sertifikasiz) + Tedarik = `TRL 1-2` (`M0`); kontrol/DD/dekoder/BOED = **156Q `ibm_marrakesh` superiletken bulut QPU silikon-disi kontrol vekili (`dc1tdo2nj2vs73dfrfl0`, `0` sizinti)**.
- **Tam 64-hex `SHA-256` dosya butunlugu ozetleri (yalnizca veri provenansi; fiziksel/muhendislik sertifikasyonu degildir):**
  - `v7_digital_twin_cert.json`: `7a3dca56839c1d4aefedf01c61fd5f6b1c62f498f45d9a2329568f04cc437d43`
  - `docs/digital_twin_interactive.html`: `e78b7e9a61ecc19ce753765ed23be20d6544e2f37ccc23e2516ffd1d1197fc61`
  - `ibm_qpu_live_results.json` (`ibm_marrakesh` kontrol vekili): `02b7a19d1704662c6424e76f4971e21b04a98d48230a917c9682853b3ca1fc5a`
  - *(Korunan tarihsel dosya ozetleri: `v6` `ca3f0e0267263bacb973f46c3cc2d321c0f204075ea232f4094758e1a9abf1d7` · `v5` `2828e8ce8d9388f7cba5490b2d05add930aadc5fe6d3ba4295f0380f816d43d1` · `v4` `feffc1d4ba2b0698c3f61015c6684da47f57ea863a8b3e0da845cc9c71914b57`)*

durum: desteklendi (8/8 PASS: DT7_1-DT7_8 PASS; v7.1 Master Dijital Ikiz, 38/38 SHA-256 dosya butunlugu ozeti, 306/306 yazilim regresyon testi kayitlandi)
