import json
import os
import sys
import argparse
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "e2e_artifacts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app
from e2e.quality_checks import check_report


class DummyOrchestrator:
    def __init__(self, response):
        self._response = response

    def ask(self, prompt):
        return self._response


REPORTS = {
    "1": """## Executive Snapshot

- AI infrastructure demand is rising as GenAI adoption expands.
- Performance, scalability, security, and visibility remain key constraints.

## Key Signals

- AI workloads require more GPU orchestration and resilient networking.
- Cloud-native AI services continue to absorb more production demand.

## Risks / Unknowns

- Real-time infrastructure breakthroughs are not always visible in broad reports.
- Distributed training bottlenecks remain underdocumented in short-form summaries.

## Recommended Actions

- Prioritize GPU orchestration, networking, and data pipeline optimization.
- Monitor large-scale AI deployment patterns for new reliability constraints.

## Sources

- [Citation 1](https://www.example.com/a)
- [Citation 2](https://www.example.com/b)
""",
    "2": """## Executive Snapshot

- Zero Trust is a core security architecture for modern environments.
- Identity-first controls and segment isolation remain central priorities.

## Key Signals

- SASE and Zero Trust continue to converge in enterprise deployments.
- AI-driven threats increase the need for adaptive defense.

## Risks / Unknowns

- PQC readiness is not always explicit in broad summary reports.

## Recommended Actions

- Strengthen MFA, DLP, and micro-segmentation controls.
- Review IoT exposure under the Zero Trust model.

## Sources

- [Citation 1](https://www.example.com/c)
""",
    "3": """## Executive Snapshot

- Edge computing is becoming a core enterprise capability.

## Key Signals

- 5G/6G and IoT sensor fusion drive edge demand.
- Local inference reduces latency and backhaul costs.

## Risks / Unknowns

- Hardware acceleration details can be underreported.

## Recommended Actions

- Invest in distributed edge orchestration and security.

## Sources

- [Citation 1](https://www.example.com/d)
- [Citation 2](https://www.example.com/e)
""",
    "5": """## Executive Snapshot

- FinTech and DeFi are converging through tokenization and embedded finance.

## Key Signals

- RegTech and on-chain compliance are expanding.
- Institutional DeFi is pushing the ecosystem toward maturity.

## Risks / Unknowns

- Recent low-level protocol changes are not always surfaced.

## Recommended Actions

- Focus on secure interoperability and compliance tooling.

## Sources

- [Citation 1](https://www.example.com/f)
""",
    "7": """## Executive Snapshot

- Robotics is integrating AI for autonomous control and HRI.

## Key Signals

- Edge-native control and perception are key technical vectors.

## Risks / Unknowns

- Short-term breakthroughs are harder to isolate from broad reports.

## Recommended Actions

- Target low-latency control, sensor fusion, and safety validation.

## Sources

- [Citation 1](https://www.example.com/g)
- [Citation 2](https://www.example.com/h)
""",
    "8": """## Executive Snapshot

- Crypto infrastructure trends center on protocol maturity and security.

## Key Signals

- Layer-2 scaling and institutional adoption remain important.

## Risks / Unknowns

- Broader market analysis can outpace technical detail.

## Recommended Actions

- Strengthen protocol security and scaling observability.

## Sources

- [Citation 1](https://www.example.com/i)
""",
    "9": """## Executive Snapshot

- Custom-domain trends require targeted, narrow-scoped analysis.

## Key Signals

- Source quality improves when the topic is specific.

## Risks / Unknowns

- N/A

## Recommended Actions

- Narrow the scope and rerun for sharper signals.

## Sources

- N/A
""",
}


def _domain_input(domain_id, custom_domain=None):
    payload = {"domain_id": domain_id}
    if custom_domain:
        payload["custom_domain"] = custom_domain
    return payload


def _parse_args():
    parser = argparse.ArgumentParser(description="Run Metis E2E matrix with quality checks.")
    parser.add_argument(
        "--mode",
        choices=["deterministic", "real"],
        default="deterministic",
        help="deterministic uses patched canned reports; real calls orchestrator.",
    )
    parser.add_argument(
        "--domains",
        default="1,2,3,5,7,8,9",
        help="Comma-separated domain IDs to run.",
    )
    parser.add_argument(
        "--custom-domain",
        default="browser rendering",
        help="Custom domain string when domain_id=9 is included.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=240,
        help="Per-request timeout when running in real mode.",
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ARTIFACT_ROOT / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    client = TestClient(app.app)
    requested_ids = [x.strip() for x in args.domains.split(",") if x.strip()]
    runs = [(d, args.custom_domain if d == "9" else None) for d in requested_ids]

    summary = []
    failed = False

    def run_request(payload):
        return client.post("/research", json=payload)

    for domain_id, custom_domain in runs:
        input_payload = _domain_input(domain_id, custom_domain)
        started = time.time()
        status = "ok"
        res = None
        if args.mode == "deterministic":
            response_text = REPORTS.get(domain_id, REPORTS["9"])
            with patch.object(app, "get_metis_orchestrator", return_value=DummyOrchestrator(response_text)):
                res = client.post("/research", json=input_payload)
        else:
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(run_request, input_payload)
            try:
                res = future.result(timeout=args.timeout_seconds)
            except FuturesTimeoutError:
                status = "timeout"
                res = None
            except Exception as exc:
                status = f"error:{type(exc).__name__}"
                res = None
            finally:
                executor.shutdown(wait=False, cancel_futures=True)

        run_dir = out_dir / f"{domain_id}_{custom_domain or 'default'}"
        run_dir.mkdir(parents=True, exist_ok=True)

        report = ""
        status_code = 0
        if res is not None:
            status_code = res.status_code
            if res.status_code == 200:
                report = res.json().get("report", "")
            else:
                status = f"http_{res.status_code}"
        checks = check_report(report) if report else {
            "sections_present": [],
            "sources": {"citation_lines": [], "na_lines": [], "issues": ["no_report_text"]},
            "issues": ["no_report_text"],
            "passed": False,
        }

        elapsed_ms = int((time.time() - started) * 1000)

        with open(run_dir / "input.json", "w", encoding="utf-8") as f:
            json.dump(input_payload, f, indent=2)
        with open(run_dir / "report.md", "w", encoding="utf-8") as f:
            f.write(report)
        with open(run_dir / "checks.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "status": status if not checks["passed"] else "passed",
                    "status_code": status_code,
                    "duration_ms": elapsed_ms,
                    "passed": checks["passed"] and status == "ok",
                    "issues": checks["issues"],
                    "sections_present": checks["sections_present"],
                    "sources": checks["sources"],
                },
                f,
                indent=2,
            )

        passed = status == "ok" and status_code == 200 and checks["passed"]
        failed = failed or not passed
        summary.append(
            {
                "domain_id": domain_id,
                "custom_domain": custom_domain or "",
                "status_code": status_code,
                "status": status if not passed else "passed",
                "passed": passed,
                "issues": ",".join(checks["issues"]) if checks["issues"] else "",
                "duration_ms": elapsed_ms,
            }
        )

    print("domain_id\tcustom_domain\tstatus\tstatus_code\tpassed\tissues")
    for row in summary:
        print(
            f"{row['domain_id']}\t{row['custom_domain']}\t{row['status']}\t{row['status_code']}\t{str(row['passed']).lower()}\t{row['issues']}"
        )

    passed_count = sum(1 for row in summary if row["passed"])
    total = len(summary)
    print(f"\nmode={args.mode} passed={passed_count} failed={total - passed_count} artifacts={out_dir}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
