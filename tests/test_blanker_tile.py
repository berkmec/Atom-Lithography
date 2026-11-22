"""Contract tests for blanker_tile host semantics (blanker_tile.v header).

Per-channel behaviour is the BMC-verified blanker_gate contract (Gate model
reused from test_rtl_contract). These tests pin the TILE glue: config map,
start_all fan-out to enabled IDLE channels only, sticky bitmap set/clear.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from test_rtl_contract import Gate

NCH = 8  # model size; RTL default 64, semantics are per-channel


class Tile:
    def __init__(self, n=NCH):
        self.gates = [Gate() for _ in range(n)]
        self.target = [0] * n
        self.enable = [0] * n
        self.done_st = [0] * n
        self.abort_st = [0] * n

    def step(self, cfg=None, start_all=0, hits=0):
        # outputs of this cycle are computed from state at cycle start,
        # exactly like the Gate model; sticky updates apply next cycle.
        outs = []
        for i, g in enumerate(self.gates):
            accepting = (g.st == "IDLE")
            o = g.step(1, start_all & self.enable[i], (hits >> i) & 1, self.target[i])
            if start_all and self.enable[i] and accepting:
                self.done_st[i] = 0
                self.abort_st[i] = 0
            elif o["done"]:
                self.done_st[i] = 1
            elif o["abort"]:
                self.abort_st[i] = 1
            outs.append(o)
        if cfg is not None:
            addr, data = cfg
            if addr < len(self.gates):
                self.target[addr] = data
            else:
                self.enable[addr - 64] = data & 1
        return outs


def bitmap(bits):
    return sum(b << i for i, b in enumerate(bits))


def test_config_map_and_selective_start():
    t = Tile()
    t.step(cfg=(3, 2))            # channel 3 target = 2 ions
    t.step(cfg=(5, 1))            # channel 5 target = 1
    t.step(cfg=(64 + 3, 1))       # enable ch3 only
    outs = t.step(start_all=1)
    outs = t.step()
    assert outs[3]["busy"] == 1 and outs[5]["busy"] == 0  # only enabled ch started
    t.step(hits=1 << 3)
    t.step(hits=1 << 3)
    outs = t.step()
    assert outs[3]["done"] == 1
    t.step()
    assert bitmap(t.done_st) == (1 << 3) and bitmap(t.abort_st) == 0


def test_sticky_cleared_on_restart_and_abort_bitmap():
    t = Tile()
    t.step(cfg=(1, 1)); t.step(cfg=(64 + 1, 1))
    t.step(start_all=1)
    for _ in range(Gate.WD + 5):
        t.step()
    assert bitmap(t.abort_st) == (1 << 1)          # watchdog abort latched
    t.step(start_all=1)                            # restart clears sticky
    t.step()
    assert bitmap(t.abort_st) == 0
    t.step(hits=1 << 1)
    t.step(); t.step()
    assert bitmap(t.done_st) == (1 << 1)


def test_start_all_does_not_disturb_running_channel():
    t = Tile()
    t.step(cfg=(0, 3)); t.step(cfg=(64, 1))
    t.step(start_all=1)
    t.step(hits=1)                # counted = 1
    t.step(start_all=1, hits=1)   # start pulse while RUN: ignored, counted = 2
    outs = t.step(hits=1)         # counted = 3 -> FIN next
    outs = t.step()
    assert outs[0]["done"] == 1 and outs[0]["counted"] == 3
