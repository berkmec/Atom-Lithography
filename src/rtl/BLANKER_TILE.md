# blanker_tile — 64 kanallı sayılmış-implantasyon karosu (SKY130 sayıları)

2026-10-20. Üretim hedefi: mikro iyon implantasyon dizisinin 8×8 demetcik bloğu.
**Laboratuvar/tape-out yoktur; sayılar yosys+ABC sentezidir (yerleşimsiz).**

## Modüller
- `blanker_gate.v` — tek kanal: hedef sayısına ulaşınca blanker'ı kapatır, watchdog
  ölü kanalı abort eder. Sözleşme BMC ile bağımsız şartname modeline karşı kanıtlı
  (`bmc64.ys`, SAT proof SUCCESS, WD=50/seq ölçeğinde).
- `blanker_tile.v` — 64 kanal + ev sahibi arayüzü: cfg yazma (0–63 hedef, 64–127
  enable), `start_all` (yalnız IDLE kanalları başlatır, sticky'leri temizler),
  done/abort sticky bitmapleri, `rd_counted` okuma.
- `blanker_tile_formal.v` — özellikler: blanker açıkken sticky set olamaz; done ve
  abort sticky aynı kanalda birlikte set olamaz. **Zamansal tümevarımla kanıtlı**
  (`tile_formal.ys`: Induction step proven: SUCCESS!, NCH=2, WD=6).

## Sentez (sky130_fd_sc_hd, TT 25 °C 1,8 V, `tile_synth.ys`)
| | 32-bit watchdog | 17-bit doygun watchdog |
|---|---|---|
| Hücre | 16 668 | 11 835 |
| Alan | 161 889 µm² (0,162 mm²) | **117 541 µm² (0,118 mm²)** |
| Kanal başına | 2 530 µm² | 1 837 µm² |

Watchdog daraltması BMC'de gerçek bir köşe durumu yakalattı: sürekli `count_hit`
zaman-aşımı kontrolünü bastırdığı için saran sayaç spec'ten sapıyordu; eşikte doyan
sayaç her girdi dizisinde sınırsız sayaçla eşdeğer (BMC + tümevarım yeniden kanıtlı).

Testler: `tests/test_blanker_tile.py` (3) + `tests/test_rtl_contract.py` (3); repo
toplamı 87/87. Sentez netlisti: `blanker_tile_synth.v`.

Açık: karonun OpenROAD yerleşimi (alan/zamanlama kapanışı), IO halkası entegrasyonu,
10⁴ kanal = 157 karo ölçeğinde güç dağıtımı (Exp70 bütçesi içinde).
