# blanker_tile — Sayılmış-İmplantasyon Blanker Karosu (SKY130 M0/M1 Ön-Foundry Prototipi)

Üretim hedefi: mikro iyon implantasyon dizisi sayılmış tek-iyon blanker bloğu (hiyerarşik `NCH=8` SKY130 alt-karo veya `NCH=64` mantıksal karo).
**Laboratuvar/tape-out yoktur; IO padring, ESD, sealring ve tam-çip PDN kapanışı henüz yapılmamıştır.**

## Modüller ve Sertleştirilmiş Sözleşme
- `blanker_gate.v` — tek kanal sayılmış-iyon kapısı:
  - Varsayılan `WATCHDOG_CYCLES = 7_500_000` (100 MHz'de 75 ms >= 5 × 15 ms Poisson çevrimi -> <%0,67 erken kesme).
  - Dahili 2-FF asenkron-assert / senkron-deassert reset senkronizatörü (`rst_sync_n`).
  - `count_hit` üzerinde 2-FF CDC senkronizatörü + yükselen-kenar dedektörü (30 ns / 3 saatlik IBIC darbesi tam 1 kez sayılır).
  - `target_count == 0` koruması: sıfır hedef için blanker asla açılmaz.
  - `timeout_abort` port adı (SV/C++ anahtar sözcük çakışması yok; `verilator --lint-only -Wall` 0 uyarı).
- `blanker_tile.v` — `NCH=8..64` kanal + birleşik paralel/seri ev sahibi arayüzü:
  - Paralel CSR (`cfg_we`, `cfg_addr`, `cfg_data`, `start_all`, `rd_addr`, `rd_counted`) — `NCH < 64` için tam sınır korumalı (OOB aliasing yok).
  - Birleşik seri arayüz (`ser_sel`, `ser_sclk`, `ser_sdata`, `ser_tile_latch_n`, `ser_frame_latch_n`, `ser_beam_en`, `tile_done_out`, `tile_abort_out`) doğrudan `rtl/machine_ctrl/blanker_array_ctrl.v` ile uyumlu.
  - Ortak 2-FF reset serbest bırakma ağacı.
- `blanker_gate_spec.v` / `blanker_miter.v` / `blanker_tile_formal.v` — bağımsız şartname modeli ve formal güvenlik özellikleri.

## Doğrulama ve Dürüst Fiziksel Durum
- `verilator --lint-only -Wall`: `blanker_gate.v`, `blanker_gate_spec.v`, `blanker_tile.v` (`NCH=64` ve `NCH=8`) üzerinde 0 uyarı.
- `iverilog -g2012 -Wall + vvp`: `blanker_gate_tb.v` ve `tests/test_blanker_tile.py` canlı simülasyonları (30 ns IBIC tek-sayım, `target_count==0`, watchdog, `blanker_array_ctrl <-> blanker_tile` seri/IBIC entegrasyonu) 0 hata.
- SKY130 fiziksel durum (ayrıntılar `hardware/eda_flow/openroad_signoff_manifest.json` içinde):
  - Pilot 4C `NCH=8` gerçek eşzamanlı Fmax: **TT = 272.48 MHz**, **SS = 154.08 MHz** (PDN/antenna/padring/ESD/sealring açık kalemler).
  - Tarihsel 64-kanallı Exp123 Attempt-2 (101 yönlendirilmemiş ağ) ve Exp38/Exp58 `seg6/seg8` tape-out adayı **değildir**.
