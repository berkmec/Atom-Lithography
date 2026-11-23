"""Live IBM Quantum Platform 2026 QPU Execution Script for Exp145 (H163).

Submits the 16-PUB native-ISA OpenQASM 3.0 validation suite (C1 DD + Bell tomography,
C2 5-qubit linear d=3 repetition code, C3 8-point Ramsey fringe for Q16.16 BOED) as ONE
SamplerV2 job using pure ``requests`` (ZERO ``qiskit`` dependency).

Environment variables required (live mode):
    IBM_QUANTUM_TOKEN     IBM Cloud API key (exchanged via IAM for short-lived Bearer token)
    IBM_QUANTUM_INSTANCE  IBM Quantum instance Service-CRN

Security guarantee:
    Credentials are NEVER printed, logged, serialized, or written to disk. Output JSON
    (``results/exp145_cloud_qpu_ibm_validation/ibm_qpu_live_results.json``) stores only
    public hardware telemetry, raw shot counts, and decoded scientific metrics.

Usage:
    python3 -B experiments/exp145_cloud_qpu_ibm_validation/run_ibm_live_qpu.py [--shots 4096]
    python3 -B experiments/exp145_cloud_qpu_ibm_validation/run_ibm_live_qpu.py --dry-run
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.machine_control.cloud_qpu_bridge import (
    C1_IDLE_US,
    C2_IDLE_US,
    C3_DELAYS_US,
    C3_DETUNING_KHZ,
    IBMQuantumRESTClient,
    NativeOpenQASM3Transpiler,
    SUITE_PUB_SPECS,
    analyze_validation_suite_counts,
    make_synthetic_heavy_hex_backend,
    parse_sampler_v2_counts,
    redact_secrets,
    select_best_linear_chain,
    simulate_offline_heron_counts,
    validate_openqasm3_isa,
)


def _assert_no_secrets_in_payload(text: str, secrets: tuple[str, ...]) -> None:
    """Fail-closed guard ensuring zero credential material can ever be written to disk."""
    for s in secrets:
        if s and len(s) >= 6 and s in text:
            raise RuntimeError("SECURITY ABORT: credential substring detected in output payload")
    if "crn:v1:" in text.lower() or "bearer " in text.lower():
        raise RuntimeError("SECURITY ABORT: CRN or Bearer token pattern detected in output payload")


def execute_live_qpu(
    shots: int = 4096,
    preferred_backend: str | None = None,
    poll_interval_s: float = 5.0,
    timeout_s: float = 600.0,
    out_path: Path | None = None,
) -> dict[str, Any]:
    """Authenticate, select best online IBM QPU, run 16-PUB SamplerV2 job, and save sanitized JSON."""
    t_start = time.time()
    token_env = os.environ.get("IBM_QUANTUM_TOKEN", "").strip()
    inst_env = os.environ.get("IBM_QUANTUM_INSTANCE", "").strip()
    if not token_env or not inst_env:
        raise EnvironmentError(
            "IBM_QUANTUM_TOKEN and IBM_QUANTUM_INSTANCE environment variables must be set for live execution."
        )

    client = IBMQuantumRESTClient(api_key=token_env, service_crn=inst_env)
    print("[exp145-live] Authenticating with IBM Cloud IAM...")
    bearer = client.authenticate()
    secrets_tuple = (token_env, inst_env, bearer)

    print("[exp145-live] Discovering operational real IBM QPU backends...")
    backend_info = client.select_best_online_backend(preferred_backend=preferred_backend, min_qubits=5)
    backend_name = backend_info["name"]
    cfg = backend_info["configuration"]
    props = backend_info.get("properties")
    print(
        f"[exp145-live] Selected backend: {backend_name} "
        f"(n_qubits={backend_info['n_qubits']}, native_2q={backend_info['native_2q']}, "
        f"pending_jobs={backend_info['pending_jobs']})"
    )

    chain_info = select_best_linear_chain(cfg, props, length=5)
    print(
        f"[exp145-live] Optimal 5Q linear chain: {chain_info['qubits']} "
        f"(2Q_errs={chain_info['chain_edge_errors']}, RO_errs={chain_info['chain_readout_errors']})"
    )

    transpiler = NativeOpenQASM3Transpiler(
        qubits=chain_info["qubits"],
        native_2q=chain_info["native_2q"],
        dt_s=chain_info["dt_s"],
        granularity=chain_info["granularity"],
        min_delay_dt=chain_info["min_delay_dt"],
        directed_edges=chain_info["directed_edges"],
    )
    suite = transpiler.build_validation_suite(
        c1_idle_us=C1_IDLE_US,
        c2_idle_us=C2_IDLE_US,
        c3_detuning_kHz=C3_DETUNING_KHZ,
    )

    pub_names = [name for name, _nb in SUITE_PUB_SPECS]
    expected_bits = [nb for _name, nb in SUITE_PUB_SPECS]
    qasm_list: list[str] = []
    for name in pub_names:
        qasm = suite[name]["qasm"]
        chk = validate_openqasm3_isa(
            qasm,
            native_2q=chain_info["native_2q"],
            granularity=chain_info["granularity"],
        )
        if not chk["valid"]:
            raise RuntimeError(f"Static ISA check failed on {name}: {chk['errors']}")
        qasm_list.append(qasm)

    print(f"[exp145-live] Submitting 1 SamplerV2 job ({len(qasm_list)} PUBs x {shots} shots) to {backend_name}...")
    sub = client.submit_sampler_v2(backend_name=backend_name, qasm_circuits=qasm_list, shots=shots)
    job_id = sub["job_id"]
    print(f"[exp145-live] Submitted job_id={job_id}; polling for completion (timeout={timeout_s:.0f}s)...")

    job_meta = client.wait_for_job(job_id=job_id, poll_interval_s=poll_interval_s, timeout_s=timeout_s)
    elapsed_s = round(time.time() - t_start, 2)
    print(f"[exp145-live] Job {job_id} completed in {elapsed_s}s; fetching results...")

    raw_results = client.get_job_results(job_id)
    counts_list = parse_sampler_v2_counts(raw_results, expected_num_bits=expected_bits)
    if len(counts_list) != len(pub_names):
        raise RuntimeError(
            f"Expected {len(pub_names)} PUB count dicts from job {job_id}, got {len(counts_list)}"
        )
    counts_by_pub = dict(zip(pub_names, counts_list))

    c3_actual_delays = [
        suite[f"C3_ramsey_{f'{d:.1f}'.replace('.', 'p')}us"]["actual_delay_us"]
        for d in C3_DELAYS_US
    ]
    analysis = analyze_validation_suite_counts(
        counts_by_pub,
        c3_delays_us=c3_actual_delays,
        c3_programmed_kHz=C3_DETUNING_KHZ,
        c1_idle_us=suite["C1a_bare_idle"]["idle_us"],
    )

    usage = job_meta.get("usage") or job_meta.get("metrics", {}).get("usage") or {}
    payload: dict[str, Any] = {
        "experiment": "exp145_cloud_qpu_ibm_validation",
        "mode": "live_ibm_qpu_hardware",
        "epistemic_tag": "Canli-Donanim-IBM-QPU",
        "no_lab_measurement": False,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "api_version_used": client.api_version,
        "backend": {
            "name": backend_name,
            "n_qubits": backend_info["n_qubits"],
            "native_2q": chain_info["native_2q"],
            "dt_ns": round(chain_info["dt_s"] * 1e9, 4),
            "granularity_dt": chain_info["granularity"],
            "selected_5q_chain": chain_info["qubits"],
            "chain_edge_errors": chain_info["chain_edge_errors"],
            "chain_readout_errors": chain_info["chain_readout_errors"],
            "chain_t1_us": chain_info["chain_t1_us"],
            "chain_t2_us": chain_info["chain_t2_us"],
        },
        "job": {
            "job_id": job_id,
            "status": str(job_meta.get("status") or job_meta.get("state", {}).get("status", "Completed")),
            "shots_per_pub": int(shots),
            "n_pubs": len(pub_names),
            "wall_clock_seconds": elapsed_s,
            "quantum_usage": usage,
        },
        "timing_actual": {
            "c1_idle_us": suite["C1a_bare_idle"]["idle_us"],
            "c2_idle_us": suite["C2a_rep3_logical0"]["idle_us"],
            "c3_delays_us": c3_actual_delays,
            "c3_programmed_detuning_kHz": C3_DETUNING_KHZ,
        },
        "counts_by_pub": counts_by_pub,
        "analysis": analysis,
    }

    serialized = json.dumps(payload, indent=2) + "\n"
    _assert_no_secrets_in_payload(serialized, secrets_tuple)

    target = out_path or (
        REPO_ROOT / "results" / "exp145_cloud_qpu_ibm_validation" / "ibm_qpu_live_results.json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(serialized, encoding="utf-8")
    print(f"[exp145-live] Saved sanitized live QPU results to {target.relative_to(REPO_ROOT)}")

    c1 = analysis["C1_dd_and_bell"]
    c2 = analysis["C2_repcode3"]
    c3 = analysis["C3_ramsey_boed"]
    print(
        f"[exp145-live] C1 DD: bare={c1['p0_bare_idle']:.4f}, echo={c1['p0_hahn_echo']:.4f}, "
        f"xy4={c1['p0_xy4_dd']:.4f} | Bell F(|Phi+>)={c1['bell_fidelity_Phi_plus']:.4f}"
    )
    print(
        f"[exp145-live] C2 d=3: p_phys={c2['avg_p_phys']:.4f}, p_L_decoded={c2['avg_p_L_decoded']:.4f} "
        f"({c2['suppression_ratio_decoded']:.2f}x), p_L_postsel={c2['avg_p_L_postsel']:.4f}"
    )
    print(
        f"[exp145-live] C3 Ramsey: blind8={c3['blind_8pt']['est_freq_kHz']:.2f} kHz, "
        f"FP64_BOED={c3['fp64_boed']['est_freq_kHz']:.2f} kHz ({c3['fp64_boed']['n_points']} pts), "
        f"Q16_BOED={c3['q16_16_boed']['est_freq_kHz']:.2f} kHz ({c3['q16_16_boed']['n_points']} pts, "
        f"diff={c3['q16_16_boed']['q16_vs_fp64_diff_kHz']:.3f} kHz)"
    )
    return payload


def execute_dry_run(shots: int = 4096) -> None:
    """Validate circuit compilation, ISA checks, and analyzer locally without hitting IBM network."""
    cfg, props = make_synthetic_heavy_hex_backend(family="heron", seed=2026145)
    chain_info = select_best_linear_chain(cfg, props, length=5)
    tr = NativeOpenQASM3Transpiler(
        qubits=chain_info["qubits"],
        native_2q=chain_info["native_2q"],
        dt_s=chain_info["dt_s"],
        granularity=chain_info["granularity"],
        min_delay_dt=chain_info["min_delay_dt"],
        directed_edges=chain_info["directed_edges"],
    )
    suite = tr.build_validation_suite()
    for name, _nb in SUITE_PUB_SPECS:
        chk = validate_openqasm3_isa(suite[name]["qasm"], native_2q="cz", granularity=16)
        if not chk["valid"]:
            raise RuntimeError(f"Dry-run ISA check failed on {name}: {chk['errors']}")
    counts = simulate_offline_heron_counts(shots=shots, seed=2026145)
    analysis = analyze_validation_suite_counts(counts)
    print(
        f"[exp145-dry-run] OK: 16 PUBs ISA-valid on chain {chain_info['qubits']} | "
        f"Bell F={analysis['C1_dd_and_bell']['bell_fidelity_Phi_plus']:.4f} | "
        f"d=3 {analysis['C2_repcode3']['suppression_ratio_decoded']:.2f}x | "
        f"Q16 BOED={analysis['C3_ramsey_boed']['q16_16_boed']['est_freq_kHz']:.2f} kHz"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Exp145 16-PUB validation suite on IBM Quantum QPU.")
    parser.add_argument("--shots", type=int, default=4096, help="Shots per PUB (default: 4096)")
    parser.add_argument("--backend", type=str, default=None, help="Optional explicit IBM backend name")
    parser.add_argument("--poll", type=float, default=5.0, help="Job status poll interval in seconds")
    parser.add_argument("--timeout", type=float, default=600.0, help="Job completion timeout in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Validate locally without IBM API calls")
    args = parser.parse_args()

    if args.dry_run:
        execute_dry_run(shots=args.shots)
        return

    try:
        execute_live_qpu(
            shots=args.shots,
            preferred_backend=args.backend,
            poll_interval_s=args.poll,
            timeout_s=args.timeout,
        )
    except EnvironmentError as exc:
        print(f"[exp145-live] ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:
        safe = redact_secrets(
            str(exc),
            (
                os.environ.get("IBM_QUANTUM_TOKEN", ""),
                os.environ.get("IBM_QUANTUM_INSTANCE", ""),
            ),
        )
        print(f"[exp145-live] ERROR: {safe}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
