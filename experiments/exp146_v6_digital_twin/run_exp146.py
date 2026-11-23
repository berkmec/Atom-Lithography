"""CLI runner for Exp146 (H164): Master v6.0 Digital Twin & Cryptographic SHA-256 Certificate.

Usage:
    PYTHONPATH=src python3 -B experiments/exp146_v6_digital_twin/run_exp146.py
"""
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from digital_twin146 import run_v6_digital_twin


def main() -> None:
    res = run_v6_digital_twin(write_outputs=True)
    cert = res["v6_master_certificate"]
    print(f"Exp146 v6.0 Master Digital Twin finished in {res['runtime_s']}s")
    print(f"Verdicts: {res['n_passed']}/{res['n_total']} PASS (success_rule_met={res['success_rule_met']})")
    for k, v in res["verdicts"].items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print(f"v6_digital_twin_cert.json SHA-256 (64-hex): {cert['sha256']}")
    if not res["success_rule_met"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
