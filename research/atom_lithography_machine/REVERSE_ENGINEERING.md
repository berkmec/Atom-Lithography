# Tersine Mühendislik Veri Hattı — Araç Tanıma ve Kullanım Planı

Tarih: 2026-10-20. Kapsam: E: diskine kurulan dört deponun ne olduğu, bu makinede
çalışma önkoşulları ve atom litografi makinesine uygulama hattı.
**Durum güncellemesi (Exp79, aynı gün):** cad-recode bu makinede çalıştırıldı —
NuFlare patenti geometrisinden üretilen nokta bulutu → CadQuery kodu → STEP
(chamfer 0,056). Diğer üç araç henüz çalıştırılmadı.

## Araçlar

### 1. cad-recode (E:\cad-recode) — tersine mühendisliğin çekirdeği
- Nokta bulutu → CadQuery Python kodu üreten model (Qwen2-1.5B ince ayar +
  tek doğrusal katman; HF: filapro/cad-recode-v1.5). ICCV 2025; DeepCAD/Fusion360/
  CC3D'de SOTA iddiası.
- Depo yalnız çıkarım demosu (`demo.ipynb`): mesh'ten 256 nokta örnekle → kod →
  ayrı süreçte CadQuery ile STEP/STL. Eğitim kodu yok.
- Önkoşul: PyTorch+CUDA yığını (Dockerfile Linux/CUDA). Bu makinede GPU var
  (RTX 2060 SUPER); Windows-native yerine WSL yolu gerçekçi. Üretilen kod geçersiz
  olabilir → zaman aşımlı ayrı süreç şart (demo da uyarıyor).

### 2. engineering-toolchain (E:\engineering-toolchain) — model→fizik zinciri
- Tek Docker imajında üç MCP sunucusu: **mcp-syson** (SysML v2 + z3 kısıt çözme),
  **mcp-build123d** (parametrik CAD-as-code, STEP/STL/GLTF, kütle özellikleri),
  **mcp-calculix** (Gmsh ağ + CalculiX FEA). Paylaşılan `/exports` hacmiyle
  STEP, CAD'den FEA'ya akar.
- Depo yalnız paketleme: sunucu kodları kurulumda JSR'den sabit sürümlerle çekilir
  (syson 0.6.0 / build123d 0.5.0 / calculix 0.7.0). GHCR imajı özel; kaynaktan
  derleme yolu README'de var.
- Önkoşul: Docker. **Bu makinede Docker yok** (PATH'te bulunamadı); WSL içi Docker
  veya Docker Desktop kurulumu gerekir.

### 3. AnkusDrive (E:\AnkusDrive) — en geniş yüzey
- FreeCAD 1.1 Python API'sini CLI + MCP (280+ araç) ile sürer: CAD modelleme,
  CalculiX/Elmer FEM ve geniş çözücü aileleri (termal, CFD/CHT, EM, akustik, FSI,
  enjeksiyon, DEM, optik, çok-cisim) + tasarım kontrol katmanı (parça no, reçete,
  varyant aileleri, ECO). Windows birinci sınıf; `scripts\install-core.ps1`.
- Önkoşul: FreeCAD 1.1 kurulumu. **Bu makinede yok** (`C:\Program Files\FreeCAD 1.1`
  bulunamadı). Kurulursa MCP kaydı `ankusdrive mcp` ile yapılır (mcp<2 pini kritik).

### 4. abaqus-mcp (E:\abaqus-mcp) — lisanslı FEA köprüsü
- Abaqus/CAE eklentisi + FastMCP sunucu, dosya IPC'si ile: 8 araç (betik çalıştır,
  model bilgisi, iş listele/gönder, ODB sorgula, viewport görüntüsü, ping/durum).
- Önkoşul: lisanslı Abaqus kurulumu. **Bu makinede yok.** Abaqus gelene kadar FEA
  ihtiyacı CalculiX (AnkusDrive/toolchain) ile karşılanır; bu köprü raf bekler.

## Litografi makinelerinden veri toplama hattı (öneri)
1. **Kaynak toplama (yasal, halka açık):** patent aileleri (çok-demet blanker:
   NuFlare US20240029999A1 vb.), makaleler, satıcı veri sayfaları, kendi
   taramalarımız. Tersine mühendislik yalnız halka açık belge ve kendi ölçümümüzden.
2. **Geometri çıkarımı:** tarama/nokta bulutu → cad-recode ile kaba parametrik kod →
   build123d/FreeCAD'de hassas yeniden model (toleranslar belgelerden).
3. **Doğrulama:** CalculiX ile yapısal/termal FEA; kritik parçada Abaqus (lisans
   olursa) çapraz kontrol. SysON'da gereksinim→parça→analiz izlenebilirliği.
4. **Yeniden tasarım:** Exp78 altın bant (10³–10⁴ demetcik) + zarf küçültme;
   her parça için "özgün / sadeleştirilmiş / COTS karşılığı" üçlü karşılaştırması.
   (Exp121 kullanıcı kararı: maliyet artışı serbesttir — ucuzlatma, riski azaltan
   sağlam seçeneğin karşısında ikincil ölçüttür.)

## İlk somut adımlar (sırayla)
1. FreeCAD 1.1 kur + AnkusDrive `install-core.ps1` + `doctor/ping` duman testi.
2. Docker (WSL içi) + toolchain imajını kaynaktan derle; build123d→calculix STEP akışını doğrula.
3. cad-recode demosunu WSL+GPU'da bir örnek mesh ile çalıştır; çıkan CadQuery kodunu
   mevcut `cad/params.py` zarf modeliyle karşılaştır.
4. İlk tersine mühendislik hedefi: blanker plakası — patent geometrisinden parametrik
   model + elektrostatik sapma bütçesi FEA'sı.
