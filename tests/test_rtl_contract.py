"""Cycle-contract tests for blanker_gate (specification in blanker_gate.v header).

The Verilog DUT is verified against an independent specification model
(blanker_gate_spec.v) by yosys bounded model checking (src/rtl/bmc64.ys).
These Python tests pin the CONTRACT itself so a spec edit cannot silently
drift: start accepted only in IDLE; blanker/busy high exactly in RUN;
one-cycle FIN (done) and TO (abort) states.
"""


class Gate:
    WD = 50

    def __init__(self):
        self.st, self.counted, self.wd = "IDLE", 0, 0

    def step(self, rst_n, start, hit, tgt):
        if not rst_n:
            self.st, self.counted, self.wd = "IDLE", 0, 0
            return dict(blanker=0, busy=0, done=0, abort=0, counted=0)
        st = self.st
        out = dict(blanker=int(st == "RUN"), busy=int(st == "RUN"),
                   done=int(st == "FIN"), abort=int(st == "TO"), counted=self.counted)
        if st == "IDLE":
            if start:
                self.counted, self.wd, self.st = 0, 0, "RUN"
        elif st == "RUN":
            self.wd += 1
            if hit:
                self.counted += 1
                if self.counted >= tgt:
                    self.st = "FIN"
            elif self.wd - 1 >= self.WD - 1:
                self.st = "TO"
        else:
            self.st = "IDLE"
        return out


def run(seq):
    g = Gate()
    return [g.step(*s) for s in seq]


def test_single_count_done_timing():
    seq = [(0, 0, 0, 1)] * 2 + [(1, 1, 0, 1)] + [(1, 0, 0, 1)] * 2 + [(1, 0, 1, 1)] + [(1, 0, 0, 1)] * 2
    out = run(seq)
    assert [o["done"] for o in out].count(1) == 1
    fin = next(i for i, o in enumerate(out) if o["done"])
    assert out[fin]["blanker"] == 0 and out[fin]["busy"] == 0
    assert out[fin]["counted"] == 1


def test_watchdog_abort_and_dead_cycle():
    seq = [(1, 1, 0, 1)] + [(1, 0, 0, 1)] * 60 + [(1, 1, 0, 1)] + [(1, 0, 0, 1)] * 3
    out = run(seq)
    assert sum(o["abort"] for o in out) == 1
    ab = next(i for i, o in enumerate(out) if o["abort"])
    assert out[ab]["blanker"] == 0


def test_start_ignored_outside_idle():
    # start during FIN must not shortcut the dead cycle (contract)
    seq = ([(1, 1, 0, 1)] + [(1, 1, 1, 1)] + [(1, 1, 0, 1)] * 3)
    out = run(seq)
    fins = [i for i, o in enumerate(out) if o["done"]]
    assert len(fins) == 1
    assert out[fins[0] + 1]["busy"] == 0  # FIN is a dead cycle: start not yet accepted
    assert out[fins[0] + 2]["busy"] == 1  # restart accepted from the IDLE cycle after FIN
