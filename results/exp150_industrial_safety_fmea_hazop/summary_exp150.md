# Exp150 (`H168`): Ön Emniyet Tasarım Hedefi, HAZOP, 25-Satırlı FMEA & `S7.SAFETY` Kiti Taslağı (Sertifikasız `M0`)

- **Tarih:** 2026-11-27  
- **Hipotez:** `H168` (`Exp150_industrial_safety_fmea_hazop`, `v7.0` / `v7.2`)  
- **Ön-Kayıtlı Model Kriter Kararı:** **7/7 PASS** (`PASS`, yazılım/analitik model kontrolü)  
- **Sertifikasyon Durumu:** `PRELIMINARY_PARAMETRIC_CALCULATION_NOT_CERTIFIED` — `iec61508_certified = false`, `semi_s2_certified = false`, `sil3_pfd_band_met_at_nominal_assumed_lambda_du = true`, `requires_third_party_assessment = true`  
- **Epistemik Durum:** `{Model}`, `{Analitik}`, `{Literatür}`, `{Varsayım}` — `TRL 1–2 (M0)`, `no_lab_measurement = true`, `no_supplier_quotes = true`.

> [!NOTE]
> **Epistemik ve Sertifikasyon Sınırı (Zorunlu Beyan):** Bu belge Python tabanlı bir **`M0` ön FMEA/HAZOP tasarım taramasıdır**; herhangi bir sertifikasyon veya uygunluk beyanı değildir (`iec61508_certified = false`, `semi_s2_certified = false`, `requires_third_party_assessment = true`). **SEMI, kendi `SEMI S2` kılavuzu için sertifikasyon vermez** (üçüncü-taraf saha değerlendirmesi gerekir). Benzer biçimde **`IEC 61508 SIL-3`**, FMEA/RPN puanı düşürülerek veya varsayılan bir `λ_DU` ile tek-nokta PFD hesaplanarak kazanılan bir etiket olmayıp tam emniyet yaşam döngüsü, donanım mimari kısıtları (`HFT`, `SFF`), tedarikçi FMEDA verisi, sistematik yetkinlik ve bağımsız fonksiyonel emniyet değerlendirmesi gerektirir. Aşağıdaki tablolarda yer alan `SIL-3`, `SIL-2` ve `SIL-1` sınıfları yalnızca **hedeflenen emniyet düzeyini (`tasarım hedefi`)** belirtir; sertifikasyon iddiası değildir.

## 1. Yönetici Özeti ve Ön-Kayıtlı Model Kriterleri (`SF1–SF7`)

Atom Litografi Makinesi kavramsal tasarımı (`CAD v6.0`, `M3 v6.0 Full BOM = $5,547,800`), temizoda senaryosunda beş kritik mühendislik tehlikesi için ön koruma hedefleri tanımlar: (1) `S5.5` Sınıf-4 `808 nm` `43,49 J/cm²` qCW flaş lazer, (2) `S1.1` zehirli/piroforik `PH₃` fosfin ve `S5.6` `%5 H₂/N₂` pasivasyon gazı, (3) `10–22 keV` yüksek gerilim ve Bremsstrahlung X-ışını, (4) `20 mK / 4 K` kriyojenik Helyum ODH (statik + oda kutu-ODE geçişi) + `ASME 0,5 barg` OVC tahliye + `Exp125` `18,94 kJ` mıknatıs quench, (5) plansız elektrik kesintisi (`EPO` / `15 kVA` çevrimiçi UPS). Parametrik `S7.SAFETY-01..06` ön tasarım kiti (`355,0 kg`, `1.090 W`, `0,0 W` kriyo yükü, `$145.000` nominal = `M3 v6.0` BOM'un `%2,61`'i, `no_supplier_quotes = true`) modellendiğinde `25` satırlı ön FMEA taramasındaki maksimum risk puanı `RPN_pre = 280` değerinden **`RPN_post = 42 ≤ 60`** tasarım hedefine (ortalama `%86.3` azalma, `0` artık risk `> 60`) inmektedir.

| Kriter | Kapsam | Gözlenen Değerler | Karar |
|---|---|---|---|
| `SF1_class4_808nm_laser_enclosure_and_sil3_shutter` | Ön-kayıtlı emniyet eşiği | `NOHD_collimated_m=1472.2`, `NHZ_diffuse_m=14.59`, `OD_required_4pulse=6.568`, `residual_ratio_OD8=0.03695`, `shutter_close_ms=3.2`, `sil3_pfd_avg=2.3435e-05` | **PASS** |
| `SF2_ph3_sds_subatmospheric_and_forming_gas_safety` | Ön-kayıtlı emniyet eşiği | `unmitigated_peak_ppm=1206.9`, `mitigated_operator_ppm=0.007153`, `tlv_margin=7.0`, `idlh_margin=6990.0`, `forming_gas_nonflammable=True` | **PASS** |
| `SF3_hv_bremsstrahlung_xray_and_crowbar` | Ön-kayıtlı emniyet eşiği | `dose_6mm_316L_22keV_uSv_h=1.0596e-43`, `dose_s55_shrouded_22keV_uSv_h=1.1939e-23`, `hv_stored_energy_10kV_J=0.075`, `hv_stored_energy_22kV_J=0.363`, `hv_crowbar_50V_ms=18.26` | **PASS** |
| `SF4_cryo_he_odh_rupture_disk_and_quench` | Ön-kayıtlı emniyet eşiği | `cleanroom_60m3_O2_pct=20.567`, `dn50_relief_margin=16.37`, `dump_resistor_peak_C=38.15`, `exp125_hotspot_K=64.62` | **PASS** |
| `SF5_epo_ups_15kva_safe_shutdown` | Ön-kayıtlı emniyet eşiği | `ups_transfer_ms=0.0`, `uhv_gate_valve_close_ms=80.0`, `wafer_oxidation_ML=0.0006`, `full_load_runtime_min=43.2`, `tier1_runtime_min=202.8` | **PASS** |
| `SF6_25row_fmea_and_hazop_closure` | Ön-kayıtlı emniyet eşiği | `n_fmea_rows=25`, `n_hazop_nodes=10`, `max_rpn_pre=280`, `max_rpn_post=42`, `mean_rpn_reduction_pct=86.3` | **PASS** |
| `SF7_safety_kit_spec_ready_for_bom_v7` | Ön-kayıtlı emniyet eşiği | `n_items=6`, `total_mass_kg=355.0`, `cryo_load_W=0.0`, `pct_of_m3_v6_full=2.61`, `no_supplier_quotes=True` | **PASS** |

## 2. Beş Kritik Tehlike Alanının İndirgenmiş-Mertebe Analitik Taraması

### 2.1. Tehlike-1: `S5.5` Sınıf-4 `808 nm` Flaş Lazer (`ANSI Z136.1-2022` / `IEC 60825-1` Referansı)

- **Çapalı Kaynak (`Exp130`/`Exp139`/`CAD v6.0`):** `λ = 808.0 nm`, `t = 1.0 ms`, yonga fluansı `43.49 J/cm²` (`16×16 mm` = `111.33 J`, kaynak `119.53 J`, tepe güç `132.82 kW`), AR safir pencere fluansı `11.16 J/cm²` (`8,96×` LIDT marjı).
- **MPE ve Tehlike Mesafeleri (`C_A = 1.64437`):** Tek-darbe göz MPE = **`16.645 µJ/cm²`**, 4-darbe MPE (`C_P = 4^-0.25`) = **`11.769 µJ/cm²`**, deri MPE = `0.3217 J/cm²`. Kolime (`20 mrad`) `NOHD =` **`1472.2 m`**, fiber demeti (`150 mrad`) `NOHD =` **`196.3 m`**, Lambertian yaygın yansıma (`ρ=1`) `NHZ_diff =` **`14.59 m`**.
- **Gerekli Optik Yoğunluk ve `1oo2D` Parametrik `PFD_avg` (Sertifikasız `M0`):** Gerekli `OD` tek-darbe `6.417`, 4-darbe **`6.568`** → `OD ≥ 7+` gerekir, tasarım hedefi **`OD = 8`** olarak belirlenmiştir (`OD8` artık fluans oranı `0.03695× MPE << 1`). `IEC 61508-6` referans `1oo2D` çift-kanallı perde (`3.2 ms` yay-dönüşlü mekanik bıçak + `<0,1 ms` diyot sürücü kesici) için varsayılan nominal `λ_DU = 2.50e-07 /h`, `T_i = 8760 h`, `β = 2%` altında analitik `PFD_avg =` **`2.3435e-05`** `< 1e-3` (`sil3_pfd_band_met_at_nominal_assumed_lambda_du = true`, `iec61508_certified = false`; sertifikasyon değildir).

| Optik Yoğunluk | Yonga Artık Fluans (J/cm²) | Pencere Artık Fluans (J/cm²) | 4-Darbe MPE Oranı | Pencere Güvenlik Marjı | Gömülü Class-1 Hedefi |
|---|---:|---:|---:|---:|---|
| `OD6` | `4.349e-05` | `1.116e-05` | `3.69515` | `1.05×` | `FAIL` |
| `OD7` | `4.349e-06` | `1.116e-06` | `0.36951` | `10.55×` | `PASS` |
| `OD8` | `4.350e-07` | `1.120e-07` | `0.03695` | `105.46×` | `PASS` |

#### 2.1.1. `1oo2D` Parametrik `PFD_avg` Belirsizlik ve Ortak-Neden (`λ_DU` × `β`) Duyarlılık Taraması

Nominal `λ_DU = 2.50e-07 /h` varsayımı tedarikçi FMEDA ölçümü olmadığından, `λ_DU` çarpanı (`0,5× .. 25×`) ve ortak-neden arıza katsayısı (`β = 2%, 5%, 10%`) boyunca tam parametrik tarama yapılmıştır. Toplam `15` durumun **`11`** tanesi `SIL-3` PFD bandında (`< 1e-3`) kalırken, **`4`** tanesi **`SIL-2` bandına (`1e-3 ≤ PFD < 1e-2`)** düşer — özellikle **`10× λ_DU` + `β = 10%`** kombinasyonunda (`PFD_avg = 1.2245e-03`) ve **`25× λ_DU`** düzeyinde tüm `β` değerlerinde `SIL-3` bandı kaybedilir.

| `λ_DU` Çarpanı | `λ_DU` (/saat) | Tek-Kanal `PFD` | `β = 2%` `1oo2D PFD` (Bant) | `β = 5%` `1oo2D PFD` (Bant) | `β = 10%` `1oo2D PFD` (Bant) |
|---:|---:|---:|---|---|---|
| `0.5×` | `1.25e-07` | `5.475e-04` | `1.133e-05` (`SIL-3_BAND`) | `2.774e-05` (`SIL-3_BAND`) | `5.507e-05` (`SIL-3_BAND`) |
| `1×` | `2.50e-07` | `1.095e-03` | `2.343e-05` (`SIL-3_BAND`) | `5.619e-05` (`SIL-3_BAND`) | `1.108e-04` (`SIL-3_BAND`) |
| `3×` | `7.50e-07` | `3.285e-03` | `7.952e-05` (`SIL-3_BAND`) | `1.772e-04` (`SIL-3_BAND`) | `3.402e-04` (`SIL-3_BAND`) |
| `10×` | `2.50e-06` | `1.095e-02` | `3.725e-04` (`SIL-3_BAND`) | `6.918e-04` (`SIL-3_BAND`) | `1.224e-03` (`SIL-2_BAND`) |
| `25×` | `6.25e-06` | `2.738e-02` | `1.507e-03` (`SIL-2_BAND`) | `2.270e-03` (`SIL-2_BAND`) | `3.547e-03` (`SIL-2_BAND`) |

| Ortak-Neden `β` | `SIL-3` PFD Bandı (`<1e-3`) Üst `λ_DU` Sınırı (/saat) | Nominal `λ_DU` Üzerinde İzin Verilen Maks. Çarpan |
|---:|---:|---:|
| `2%` | `4.842e-06` | `19.37×` |
| `5%` | `3.369e-06` | `13.48×` |
| `10%` | `2.079e-06` | `8.31×` |

### 2.2. Tehlike-2: Zehirli/Piroforik `PH₃` Fosfin (`S1.1`) & `%5 H₂/N₂` Pasivasyon Gazı (`S5.6`)

- **Limitler:** `ACGIH TLV-TWA = 0,05 ppm`, `OSHA PEL = 0,30 ppm`, `NIOSH IDLH = 50,0 ppm` (ölümcül). L1 alarm = `0,02 ppm`, L2 SIL-3 hedef kapatma = `0,05 ppm`.
- **Kötü Senaryo (Önlemsiz `40 bar / 100 g` Basınçlı Silindir):** `Ø2 mm` boru kopmasında kritik boğulmalı akış `18.76 g/s`, silindir `5.33 s` içinde boşalır ve `60 m³` (`20 ACH`) temizodada tepe derişim **`1206.9 ppm`** (`IDLH`'nin **`24.1×`** katı — kesin ölümcül).
- **Önlemli Tasarım (`SDS <650 Torr / 10 g` + Vakum Ceket + `250 CFM` Scrubber + `0,02 ppm` SIL-3 hedefi):** Atmosfer-altı basınç nedeniyle kopmada dışarı advektif akış **0**'dır (hava içeri çekilir); yalnızca saf Fick moleküler difüzyonu (`0.201 mg/dk = 0.1431 sccm`) oluşur. `250 CFM` gaz dolabı + `%99,9` kuru kimyasal scrubber + `12 s` SIL-3 hedef vana kesmesi altında `%2` kaçak fraksiyonlu dolap tepe oda derişimi `6.9e-05 ppm`, dolap bypass edilse bile doğrudan SDS difüzyon kararlı-hal oda derişimi **`0.007153 ppm`** `< 0,01 ppm` kalır (`TLV-TWA` altında **`7.0×`**, `IDLH` altında **`6990×`** güvenlik marjı).
- **`S5.6` `%5,0 H₂ / %95,0 N₂` Pasivasyon Gazı (`ISO 10156`):** `H₂` hacim oranı `5.0% < 5.7%` (`ISO 10156 T_ci` sınırı) olduğundan havayla her seyreltmede **doğal olarak alevlenmez** (`intrinsically_nonflammable_in_air=true`).

### 2.3. Tehlike-3: `10–22 keV` Yüksek Gerilim & Bremsstrahlung X-Işını (`Kramers` + `NIST XCOM`)

- **Muhafazakâr Varsayım:** `I_e = 100.0 µA` geri-saçılan elektron akımı (nominal iyon demetinin `100×` katı), `Z = 42` (`Mo` elektrot), `r = 30 cm`, halk dozu limiti `1,0 µSv/h` (`ICRP 103`).
- **Kritik Mühendislik Bulgusu (`S5.5` Safir Pencere):** `6 mm` muhafazakâr (`10 mm` gerçek `CAD v6.0`) `316L` paslanmaz çelik duvar `22 keV` Bremsstrahlung'u `1,06e-43 µSv/h` (`10 mm`'de `2,21e-73 µSv/h`) düzeyine bastırırken, **çıplak `8 mm` `Al₂O₃` safir pencere** düşük atom numarası nedeniyle `22 keV`'de **`10,11 µSv/h`** (`1,0 µSv/h` halk limitinin `10×` üstü!) sızdırır. Bu nedenle `S5.5` dışına eklenen **`3 mm` çelik `OD8` muhafaza kılıfı** çift-amaçlı (**Sınıf-4 Lazer + X-Işını**) zorunlu bariyerdir (`1,19e-23 µSv/h << 0,01 µSv/h`).
- **HV Aktif Crowbar (`IEC 61010-1` Referansı, `iec61010_certified=false`):** Toplam kaçak kapasitans `1.5 nF`, depolanan enerji `10 kV`'da `0.075 J`, `22 kV`'da **`0.363 J < 0,50 J`**. `2 MΩ` aktif crowbar ile `22 kV → < 50 V` boşalım süresi **`18.26 ms < 50 ms`** (analitik eşik `PASS`).

| Enerji | Kalkan Yok (30 cm, µSv/h) | `6 mm` `316L` (µSv/h) | `10 mm` CAD `316L` (µSv/h) | Çıplak `8 mm` Safir (µSv/h) | `S5.5` Safir + `3 mm` Çelik Kılıf (µSv/h) |
|---|---:|---:|---:|---:|---:|
| `10keV` | `2007554.42` | `3.127e-237` | `1.979e-298` | `2.041e-21` | `9.613e-192` |
| `14keV` | `3984451.68` | `2.337e-137` | `4.175e-229` | `1.070e-06` | `6.423e-77` |
| `22keV` | `8220881.33` | `1.060e-43` | `2.211e-73` | `1.011e+01` | `1.194e-23` |
| `25keV` | `9853947.78` | `2.070e-29` | `9.805e-50` | `7.811e+01` | `1.053e-15` |
| `30keV` | `12607841.21` | `5.218e-17` | `2.482e-29` | `6.217e+02` | `1.031e-08` |
| `40keV` | `18205791.76` | `1.139e-06` | `1.779e-12` | `5.049e+03` | `9.015e-03` |
| `50keV` | `23900839.20` | `1.493e-02` | `6.545e-06` | `1.512e+04` | `2.570e+00` |

### 2.4. Tehlike-4: `20 mK / 4 K` Kriyojenik Helyum ODH (Statik & Kutu-ODE), `ASME 0,5 barg` Tahliye & `Exp125` Quench

- **Kuru Kapalı-Çevrim Helyum ODH (`OSHA ≥ %19,5`):** `LD400` karışımı (`0.065 m³` STP) + `PT420` kompresör/hatları (`0.85 m³` STP) + `%20` marj = **`1.098 m³` STP**. Tüm envanterin anlık salınımında `60 m³` temizodada oksijen oranı **`20.567% >> %19,5`** kalır (aynı odada `100 L` ıslak sıvı Helyum kriyostatı `O₂ = 5.93%` ile ölümcül boğulma yaratırdı). Yine de `15 m³` küçük servis odaları için duvara monteli `O₂` monitörü (`%19,5` alarm) zorunludur.
- **`ASME BPVC Sec VIII` / `CGA S-1.3` OVC Tahliye (Tam Saint-Venant İzentropik Subsonik Akış):** `0,50 barg` ayarlı (`+10%` UG-125 birikimle `0,55 barg`) tek **`DN50` patlama diski** (`250 K`) He kapasitesi `0.1817 kg/s` (paralel yaylı tahliye vanası ek `2×` yedeklik sağlar); analitik/fiziksel taşıma modeli en kötü He girişi (`PT420` `20 bar` `Ø2 mm` `50 K` kırığı + `LD400` `5 s` tam boşalım = `0.0111 kg/s`) karşısında **`16.37×`**, `N₂` cryo-yoğuşma geri-buharlaşması (`0.018 kg/s` vs `0.4629 kg/s`) karşısında **`25.72×`** (`≥ 10×`) güvenlik marjı sağlar.
- **`Exp125` 8-Bobin Mıknatıs Quench:** `1,50 T` tam alanda `18.941 kJ` (`M4` `0,1785 T` modunda `0.2682 kJ`), `R_dump = 1.563 Ω`, `τ = 0.37 s`, `V_max = 400.0 V`, bobin sıcak noktası `T_hotspot = 64.62 K < 150 K`. Harici `2.5 kg` hava-soğutmalı boşaltma direnci yalnızca `ΔT = 15.15 K` ısınarak **`38.15 °C < 55 °C`** güvenli dokunma eşiğinin altında kalır (`5 Gauss` sınırı `r < 0.62 m`).

| Oda Hacmi | Kuru `LD400+PT420` `O₂` (%) | OSHA (`≥%19,5`) | Karşılaştırma: `100 L` Islak LHe `O₂` (%) |
|---|---:|---|---:|
| `15m3` | `19.416%` | `FAIL` | `0.13%` |
| `30m3` | `20.183%` | `PASS` | `1.68%` |
| `60m3` | `20.567%` | `PASS` | `5.93%` |
| `120m3` | `20.758%` | `PASS` | `11.15%` |

#### 2.4.1. Oda ODH Kutu-ODE Geçiş Analizi (RK4, `0–600 s`)

| Senaryo | Oda (`m³`) | `ACH` | Salınım (`m³` STP / `s`) | Minimum `O₂` (%) | `t_min` (`s`) | `600 s` Sonu `O₂` (%) | `<%19,5` Süre (`s`) | OSHA |
|---|---:|---:|---|---:|---:|---:|---:|---|
| `dry_60m3_20ACH` | `60` | `20` | `1.098 / 10` | `20.5804%` | `10.0` | `20.9361%` | `0.0` | `PASS` |
| `dry_60m3_0ACH_hvac_loss` | `60` | `0` | `1.098 / 10` | `20.5701%` | `10.0` | `20.5701%` | `0.0` | `PASS` |
| `dry_15m3_6ACH` | `15` | `6` | `1.098 / 10` | `19.4833%` | `10.0` | `20.4014%` | `7.0` | `FAIL` |
| `dry_15m3_0ACH_hvac_loss` | `15` | `0` | `1.098 / 10` | `19.4712%` | `10.0` | `19.4712%` | `590.2` | `FAIL` |
| `wet_100L_60m3_20ACH` | `60` | `20` | `75.7 / 60` | `7.7408%` | `60.0` | `20.2924%` | `454.2` | `FAIL` |

### 2.5. Tehlike-5: Plansız Güç Kesintisi (`EPO` / `15 kVA` Çevrimiçi UPS & Güvenli Kapanma)

- **`15 kVA / 10 kWh` LFP Online Double-Conversion UPS:** Geçiş süresi **`0.0 ms`**, nominal tam güçte (`13.5 kW`) **`43.2 dk`** (`≥ 30 dk`), kritik Tier-1 güvenlik + UHV + kontrol yükünde (`2.533 kW`) **`202.8 dk`** (`≥ 180 dk`).
- **Hızlı UHV İzolasyon & Yonga Koruma:** Yay-dönüşlü all-metal UHV sürgülü vanalar **`80.0 ms`** (`≤ 100 ms`) içinde kapanır; `5.0e-08 Torr` basınç dalgasında temiz `Si(100)` yonga oksitlenmesi yalnızca **`6.000e-04 ML`** (`<< 0,01 ML`).

| Zaman (`t`) | Alt-Sistem | Deterministik Güvenli Kapanma Eylemi |
|---:|---|---|
| `0.0 ms` | `S7.SAFETY` | Utility-side fast contactor (<5 ms) sheds 12.5 kW PT420 & heavy Tier-2 mains AHEAD of UPS; online UPS holds Tier-1+1B (5.38 kW <= 13.5 kW) at 0 ms |
| `3.2 ms` | `S5.5` | SIL-3 target safety PLC cuts S5.5 808 nm diode driver & drops dual blade shutter |
| `18.3 ms` | `S1/S2` | S1-S2 HV PSU & S1.1-05 15 kV deck inhibited; active crowbars discharge < 50 V (7.9 ms deck / 18.3 ms column) |
| `45.0 ms` | `S5.6/S1` | S5.6 MBE pneumatic shutter closed; PBN heater & SDS PH3/SiF4 slam-shut |
| `80.0 ms` | `S5` | Spring-return all-metal UHV gate valves (S5.3 LL + S5.2 foreline) seal |
| `1 s` | `S6.3/S9.HPC` | Dedicated Tier-1B UPS magnet ramp-down supply initiates controlled 120 s ramp-down (0.65 kW; passive 1.563 Ohm quench dump backup if faulted) + S9.HPC graceful halt |
| `125 s` | `S7.SAFETY` | Magnet at 0 A & S9.HPC halted; Tier-1B sheds leaving 2.533 kW steady Tier-1 (>200 min @ 90% DoD) |
| `300 s` | `S6.8` | LD400 3He/4He mixture recovered into room-temp dump tank (OVC < 0.1 barg) |

## 3. Tam 25-Satırlı Ön FMEA (`S × O × D = RPN`, Önlem Öncesi vs Sonrası — Sertifikasız `M0`)

- **Özet İstatistikler:** `25` satır, `RPN_pre`: ort. `186.1`, maks. **`280`** (`FM-01`, `FM-10`); `RPN_post`: ort. `25.5`, maks. **`42 ≤ 60`** (`0` kabul edilemez artık risk), ortalama risk azalması **`%86.3`**.

| ID | Alt-Sistem | Hata Modu | Etki | `S/O/D` (Önce) | `RPN_pre` | Mühendislik Önlemi (`S7.SAFETY` Tasarım Hedefi) | `S/O/D` (Sonra) | `RPN_post` | Azalma | Hedef SIL (Sertifikasız) |
|---|---|---|---|---|---:|---|---|---:|---:|---|
| `FM-01` | `S1.1` | PH3 silindir / pigtail kopması (basınçlı silindir vs SDS) | Zehirli/piroforik PH3 salınımı (>IDLH 50 ppm, ölümcül) | `10/4/7` | **280** | Sub-atm SDS (<650 Torr, 10 g) + vakum ceket + 250 CFM scrubber + 0,02 ppm SIL-3 hedef vana | `10/1/2` | **20** | `-92.9%` | `SIL-3` |
| `FM-02` | `S1.1` | PH3 MFC/vana iç sızıntısı (1 sccm sürekli kaçak) | Gaz dolabında PH3 birikimi, bakım sırasında maruziyet | `9/5/6` | **270** | Çift elektrokimyasal sensör (0,02/0,05 ppm) + 250 CFM negatif basınç + otomatik N2 süpürme | `9/2/2` | **36** | `-86.7%` | `SIL-3` |
| `FM-03` | `S1.3` | 10–22 kV HV kablo/yalıtkan arkı veya panel açılması | Elektrik çarpması / ark yanığı / HV güç kaynağı hasarı | `10/4/6` | **240** | SIL-2 hedef kilitli HV muhafaza + 2 MOhm aktif crowbar (18,3 ms <50 V, <0,37 J) | `10/1/2` | **20** | `-91.7%` | `SIL-2` |
| `FM-04` | `S1.1-S1.5` | 14–22 keV geri-saçılan elektron Bremsstrahlung X-ışını | Operatör iyonlaştırıcı radyasyon maruziyeti (özellikle S5.5 safir port) | `8/5/7` | **280** | 6–10 mm 316L duvar (<1,1e-43 uSv/h) + S5.5 3 mm çelik OD8 kılıf (1,2e-23 uSv/h) + yıllık ölçüm | `8/2/2` | **32** | `-88.6%` | `SIL-2` |
| `FM-05` | `S1.6` | Option-Q 121Sb (450 °C) / 167Er fırın aşırı ısınması | Termal kaçak, ağır metal (Sb) buhar kontaminasyonu, conta hasarı | `7/4/6` | **168** | Çift K-tipi termokupl + bağımsız donanımsal 500 °C aşırı-sıcaklık rölesi + HEPA bakım | `7/2/2` | **28** | `-83.3%` | `SIL-2` |
| `FM-06` | `S2.3` | Arch-B 0,250 mm WD çökmesi / piezo Z-kaçması yongaya çarpma | 32x32 MEMS lens kırılması ve HV kısa devre | `7/5/6` | **210** | Kapasitif Z-yaklaşma sensörü + donanımsal piezo HV sınırlayıcı + yazılım/FPGA sert durdurma | `7/2/3` | **42** | `-80.0%` | `SIL-2` |
| `FM-07` | `S2.2` | SKY130 16-karo blanker kilidi açık kalması (aşırı doz) | Yonga aşırı implantasyon hasarı, HV besleme aşırı yükü | `6/5/5` | **150** | Donanımsal watchdog (blanker_tile_formal.v) + Faraday kupası akım kilidi | `6/2/2` | **24** | `-84.0%` | `SIL-1` |
| `FM-08` | `S3.2` | 100 K LTC6268 IBIC ön-uç HV/bias arızası | CSA doyumu / yonga kaçak akım ısınması | `5/5/5` | **125** | Seri 10 MOhm akım sınırlayıcı direnç + TVS koruma + otomatik bias kesici | `5/2/2` | **20** | `-84.0%` | `SIL-1` |
| `FM-09` | `S4.1` | 4x pnömatik hava yayı basınç kaybı / deprem sarsıntısı | 900x700 granit bloğun ani çökmesi, körük yırtılması | `8/3/6` | **144** | Mekanik sert durdurma tamponları (2 mm strok) + sismik ankraj + basınç anahtarı | `8/2/2` | **32** | `-77.8%` | `SIL-2` |
| `FM-10` | `S5.5` | 808 nm Sınıf-4 flaş lazer (43,49 J/cm^2) açık kapak ateşlemesi | Anında kalıcı retina körlüğü (NOHD > 1.400 m, NHZ_diff = 14,6 m) | `10/4/7` | **280** | OD>=8 ışık-geçirmez muhafaza hedefi + 1oo2D SIL-3 hedef mekanik perde (3,2 ms) + diyot kesici (nominal PFD=2,34e-5; sertifikasız) | `10/1/2` | **20** | `-92.9%` | `SIL-3` |
| `FM-11` | `S5.5` | CF63 safir pencere termal şok / lazer kaynaklı çatlama | UHV ani atmosfer girişi + lazer demet kaçağı | `9/3/6` | **162** | 8,96x LIDT marjı (11,16 vs 100 J/cm^2) + 10 us pirometre + çift vakum/basınç kilidi | `9/1/3` | **27** | `-83.3%` | `SIL-3` |
| `FM-12` | `S5.5` | MXC 20 mK soğukken yanlışlıkla flaş tavlama tetiklenmesi | DR 20 mK kademesinde şiddetli ısınma ve vakum basınç sıçraması | `7/4/6` | **168** | Donanımsal MXC < 1 K & UHV sürgülü vana durum kilidi (Exp130 / SIL-2 hedefi) | `7/1/2` | **14** | `-91.7%` | `SIL-2` |
| `FM-13` | `S5.6` | S5.6 5% H2/N2 pasivasyon hattı sızıntısı | H2 yangın/patlama riski kaygısı | `8/4/5` | **160** | ISO 10156 <=%5,7 N2 karışımı (havada doğal alevlenmez) + akış sınırlayıcı orifis + egzoz | `8/1/2` | **16** | `-90.0%` | `SIL-2` |
| `FM-14` | `S5.6` | S5.6 345 °C PBN ısıtıcı / 28Si süblimasyon soğutma suyu kesilmesi | CF100 conta aşırı ısınması, vakum kaçağı | `7/4/5` | **140** | Soğutma akış anahtarı + gövde RTD (>80 °C) sert güç kesici + otomatik deklanşör | `7/2/2` | **28** | `-80.0%` | `SIL-2` |
| `FM-15` | `S5.2` | 300 L/s Mag-Lev turbo pompa rotor arızası / ani hava girişi | Mekanik parça fırlaması, UHV oda kontaminasyonu | `8/3/6` | **144** | ISO-27892 rotor muhafaza hedefi + <80 ms yay-dönüşlü sürgülü vana + titreşim sensörü | `8/2/2` | **32** | `-77.8%` | `SIL-2` |
| `FM-16` | `S6.8` | PT420 + LD400 kapalı-çevrim Helyum envanteri temizodaya salınımı | Kapalı küçük hacimde oksijen eksikliği (ODH < %19,5) | `9/3/7` | **189** | Kuru kapalı-çevrim (1,10 m^3 STP -> 60 m^3 odada O2=%20,57) + duvar O2 monitörü (%19,5) | `9/1/2` | **18** | `-90.5%` | `SIL-2` |
| `FM-17` | `S6.8` | Kriyo iç hat patlaması / OVC ani aşırı basınçlanması | DR dış vakum kabı (OVC) mekanik patlaması | `9/3/6` | **162** | ASME 0,5 barg yaylı tahliye + yedekli DN50 patlama diski (16,4x He / 25,7x N2 akış marjı) | `9/1/2` | **18** | `-88.9%` | `SIL-3` |
| `FM-18` | `S6.3` | Exp125 8-bobinli 1,50 T mıknatıs ani quench (18,94 kJ) | Bobin sıcak nokta hasarı, >400 V ark veya boşaltma direnci yangını | `8/4/5` | **160** | 30 ms quench dedektörü + 1,563 Ohm hava-soğutmalı direnç (T_hot=64,6 K, direnç 38,2 °C) | `8/2/2` | **32** | `-80.0%` | `SIL-2` |
| `FM-19` | `S6.3` | 1,50 T mıknatıs kaçak alanı (kalp pili / ferromanyetik fırlama) | 5 Gauss (0,5 mT) aşımında tıbbi cihaz / alet fırlama tehlikesi | `8/4/5` | **160** | Exp125 aktif kalkan bobinleri (0,5 mT < 0,62 m) + zemin sınır çizgisi + ferromanyetik yasak | `8/2/2` | **32** | `-80.0%` | `SIL-1` |
| `FM-20` | `S9.1` | Option-Q 1550 nm SMF-28 optik fiber kopması / konnektör açılması | Görünmez kızılötesi (<10 mW Sınıf 1M/3R) göz maruziyeti | `6/4/6` | **144** | Otomatik optik güç kesme (ALS) + APC kapaklı konnektör + düşük güç (<2 mW) | `6/2/2` | **24** | `-83.3%` | `SIL-1` |
| `FM-21` | `S7.SAFETY` | Plansız şebeke elektrik kesintisi (tam tesis kararması) | UHV geri-akış, yonga oksitlenmesi, DR ısınma aşırı basıncı, kontrol kaybı | `8/5/5` | **200** | 15 kVA / 10 kWh online UPS (0 ms) + <80 ms UHV vana (<0,001 ML) + 180 dk Tier-1 | `8/2/2` | **32** | `-84.0%` | `SIL-2` |
| `FM-22` | `S7.SAFETY` | Acil Durdurma (EPO) basımında tek-kanal röle yapışması | HV veya lazerin acil durumda kesilememesi | `10/3/7` | **210** | 1oo2D çift-kanallı SIL-3 hedef emniyet PLC + zorlamalı-kılavuzlu (force-guided) kontaktörler (sertifikasız M0) | `10/1/2` | **20** | `-90.5%` | `SIL-3` |
| `FM-23` | `S9.HPC` | Option-HPC 4U 100G RDMA rafı (2.195 W) fan/soğutma arızası | Sunucu aşırı ısınması, duman/yangın riski | `7/4/5` | **140** | Yedekli 2,6 kW Titanium PSU + BMC 85 °C termal kesici + raf duman dedektörü | `7/2/2` | **28** | `-80.0%` | `SIL-2` |
| `FM-24` | `S7.3` | Yazılım/FPGA bozuk komut gönderimi (yanlış lazer/HV tetiği) | Otonom yazılımla emniyet sınırlarının aşılması | `9/4/6` | **216** | Yazılımdan bağımsız donanımsal SIL-3 hedef emniyet PLC kilitleme katmanı (sertifikasız M0) | `9/1/2` | **18** | `-91.7%` | `SIL-3` |
| `FM-25` | `Facility` | Temizoda HVAC/sıcaklık kayması veya su soğutma kaçağı | Optik hizalama kayması, elektrik panosunda su kısa devresi | `6/5/5` | **150** | Zemin su kaçağı sensörü + solenoid su kesici + ±10 mK HVAC alarmı (Exp133) | `6/2/2` | **24** | `-84.0%` | `SIL-1` |

## 4. 10-Düğümlü Ön HAZOP Taraması (`IEC 61882` / `SEMI S2` Referansı — Sertifikasız `M0`)

| Düğüm | Sistem | Kılavuz Sözcük | Sapma | Birincil Koruma Bariyeri (Tasarım Hedefi) | Hedef SIL (Sertifikasız) |
|---|---|---|---|---|---|
| `HZ-01` | S5.5 808 nm Flaş Lazer | `OTHER THAN (Kapak açık)` | Sınıf-4 43,49 J/cm^2 demetin dış ortama kaçışı | OD>=8 muhafaza hedefi + 1oo2D SIL-3 hedef 3,2 ms perde + diyot kesici | `SIL-3` |
| `HZ-02` | S1.1 PH3 Gaz Besleme | `MORE (Sızıntı/Basınç)` | Zehirli/piroforik PH3 salınımı (>0,05 ppm TLV / 50 ppm IDLH) | <650 Torr SDS + vakum ceket + 250 CFM scrubber + 0,02 ppm SIL-3 hedef vana | `SIL-3` |
| `HZ-03` | S1-S2 HV Kolon (10-22 kV) | `MORE (Voltaj/Ark)` | HV elektrik çarpması & 22 keV Bremsstrahlung X-ışını | 6-10 mm 316L + S5.5 çelik kılıf (<1,2e-23 uSv/h) + 2 MOhm crowbar (18,3 ms) | `SIL-2` |
| `HZ-04` | S5.6 28Si MBE & %5 H2/N2 | `MORE (Sıcaklık/Akış)` | PBN 345 °C kaçak veya H2 pasivasyon sızıntısı | ISO 10156 alevlenmez %5 H2/N2 (<%5,7) + 80 °C RTD + su akış kilidi | `SIL-2` |
| `HZ-05` | S6.8 DR & PT420 He Devresi | `MORE (OVC Basınç / He Kaçağı)` | OVC aşırı basınçlanması veya temizoda O2 düşüşü | Kuru 1,10 m^3 He (60 m^3 O2=%20,57) + ASME DN50 0,5 barg disk + O2 monitör | `SIL-3` |
| `HZ-06` | S6.3 8-Bobin 1,50 T Mıknatıs | `NO (Soğutma) -> QUENCH` | 18,94 kJ manyetik enerjinin ani boşalımı | 30 ms quench dedektörü + 1,563 Ohm direnç (38,2 °C, T_hot=64,6 K) | `SIL-2` |
| `HZ-07` | S5 Ana UHV Oda & Pompalar | `REVERSE (Geri Akış)` | Güç kesintisi veya turbo arızasında atmosfer girişi | <80 ms yay-dönüşlü all-metal UHV sürgülü vanalar (<0,001 ML oksit) | `SIL-2` |
| `HZ-08` | S7.SAFETY Şebeke / EPO | `NO (Şebeke Gücü)` | Plansız elektrik kesintisi veya EPO aktivasyonu | 15 kVA / 10 kWh online UPS (0 ms) + 40 dk tam / 213 dk Tier-1 + 1oo2D EPO hedefi | `SIL-3` |
| `HZ-09` | S9.HPC 100G RDMA Rafı | `MORE (Termal Yük)` | 2.195 W soğutma kaybı & aşırı ısınma | Yedekli 2,6 kW Titanium PSU + 85 °C BMC kesici + raf duman sensörü | `SIL-2` |
| `HZ-10` | S1.6 Option-Q (Sb/Er) & S9.1 | `OTHER THAN (Bakım/Fiber)` | 450 °C Sb fırını termal kaçağı veya 1550 nm fiber açılması | 500 °C donanım kesici + ALS otomatik optik güç kesme + HEPA bakım | `SIL-2` |

## 5. Ön Emniyet Kiti Tasarım Taslağı (`s_safety_spec.json` — `BOM v7.0` Parametrik Paketi, Sertifikasız `M0`)

- **Toplam Kit Özeti (`S7.SAFETY-01..06`):** `6` kalem, toplam kütle **`355.0 kg`**, elektrik gücü **`1090.0 W`**, kriyojenik ısıl yük **`0.0 W`**, parametrik bütçe aralığı **`$92,000 – $145,000 – $220,000`** (`M3 v6.0` Full BOM `$5,547,800`'ün **`%2.61`**'i). `no_supplier_quotes=true`, `iec61508_certified=false`, `semi_s2_certified=false` (`{Varsayım}` / `{Liste-Capasi}`).

| Parça ID | Donanım Tanımı | Konum | Kütle (kg) | Güç (W) | Kriyo (W) | Maliyet Low / Nom / High (USD) | Hedef SIL | Epistemik |
|---|---|---|---:|---:|---:|---|---|---|
| `S7.SAFETY-01` | Sub-Atmospheric SDS PH3 Micro-Cylinder Gas Cabinet (<650 Torr, 10 g), Vacuum-Jacket Line, 250 CFM Dry Scrubber & Dual 0.02 ppm Sensors | Facility gas bay adjacent to S1/S7 | `118.0` | `480` | `0.0` | `$28,000 / $42,000 / $62,000` | `SIL-3` | `{Varsayim}` |
| `S7.SAFETY-02` | ANSI Z136.1 OD>=8 (808 nm) Interlocked Class-1 Target Laser/X-Ray Steel Shroud & Dual-Channel SIL-3 Target Mechanical Shutter (<5 ms) | S5.5 +Y viewport perimeter | `38.0` | `45` | `0.0` | `$14,000 / $22,000 / $34,000` | `SIL-3` | `{Varsayim}` |
| `S7.SAFETY-03` | IEC 61508 SIL-3 Target 1oo2D Hardwired Safety PLC, 4x E-Stop Mushrooms, Guard Switches & 2 MOhm HV Crowbar Module | S7 rack top / perimeter E-Stop loop | `18.0` | `120` | `0.0` | `$18,000 / $28,000 / $42,000` | `SIL-3` | `{Varsayim}` |
| `S7.SAFETY-04` | 15 kVA / 10 kWh Online Double-Conversion LFP UPS (0 ms Transfer) & Tiered Load-Shed PDU | Facility power bay adjacent to S7/S9.HPC | `145.0` | `350` | `0.0` | `$15,000 / $24,000 / $36,000` | `SIL-2` | `{Liste-Capasi}` |
| `S7.SAFETY-05` | Cleanroom O2 Deficiency Monitor (19.5% Alarm), ASME DN50 0.5 barg OVC Burst Disk/Relief & 1.563 Ohm Quench Dump Bank | S6 DR OVC + Cleanroom wall + S7 dump bay | `24.0` | `35` | `0.0` | `$8,000 / $14,000 / $22,000` | `SIL-3` | `{Liste-Capasi}` |
| `S7.SAFETY-06` | Fast Spring-Return UHV Isolation Gate Valve Actuators (<80 ms), ISO 10156 5% H2/N2 Orifice & X-Ray Survey Meter | S5.2/S5.3/S5.6 vacuum manifolds & cleanroom | `12.0` | `60` | `0.0` | `$9,000 / $15,000 / $24,000` | `SIL-2` | `{Varsayim}` |

## 6. Epistemik Sınırlar ve Kapsam Dışı Maddeler

- Bu rapor indirgenmiş-mertebe analitik fizik modelleri (`{Model}` / `{Analitik}`), uluslararası emniyet standart/kılavuz referansları (`{Literatür}`) ve parametrik bütçe tahminlerine (`{Varsayım}`) dayanır (`TRL 1–2 / M0`).
- **Sertifikasyon Yoktur (`PRELIMINARY_PARAMETRIC_CALCULATION_NOT_CERTIFIED`):** `iec61508_certified = false`, `semi_s2_certified = false`, `requires_third_party_assessment = true`. SEMI kendi `SEMI S2` kılavuzu için sertifika vermez; `IEC 61508 SIL-3` ise tam emniyet yaşam döngüsü, donanım mimari kısıtları (`HFT`, `SFF`), tedarikçi FMEDA verisi, sistematik yetkinlik ve bağımsız fonksiyonel emniyet değerlendirmesi gerektirir. Gerçek saha `X-ışını` dozimetri ölçümü, `PH₃` sızıntı kalibrasyonu, üçüncü-taraf `SEMI S2` / `IEC 61508` saha değerlendirmesi ve gerçek tedarikçi fiyat teklifleri (`no_lab_measurement=true`, `no_supplier_quotes=true`) laboratuvar kurulum fazında yapılmalıdır.
- **Global Carbon & Hydrogen Kuralı:** Bu belge `Hydrogen` (yazar) çıktısıdır; kapanış onayı (`KABUL`) sıfır-bağlamlı **Carbon** denetimine tabidir.
