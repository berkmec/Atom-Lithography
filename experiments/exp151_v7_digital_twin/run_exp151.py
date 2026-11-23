"""CLI runner for Exp151 (H169): Master v7.0 Digital Twin & Cryptographic SHA-256 Certificate.

Usage:
    PYTHONPATH=src python3 -B experiments/exp151_v7_digital_twin/run_exp151.py
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

from digital_twin151 import run_v7_digital_twin  # noqa: E402


def main() -> None:
    res = run_v7_digital_twin(write_outputs=True)
    cert = res["v7_master_certificate"]
    print(f"Exp151 (H169) Master v7.0 Digital Twin finished in {res['runtime_s']:.3f}s")
    print(f"Verdicts: {res['n_passed']}/{res['n_total']} PASS | success_rule_met={res['success_rule_met']}")
    for k, v in res["verdicts"].items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print(f"Locked artifacts hashed : {cert['n_locked_artifacts']}")
    print(f"v7_digital_twin_cert.json SHA-256 (FULL 64-HEX): {cert['sha256']}")
    if not res["success_rule_met"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
