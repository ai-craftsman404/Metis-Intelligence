import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "e2e_artifacts"


def _latest_artifact_dir(base: Path) -> Path | None:
    if not base.exists():
        return None
    candidates = [p for p in base.iterdir() if p.is_dir()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.name)


def _load_checks(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _summarize_sources(source_block: dict[str, Any]) -> tuple[int, int, int]:
    citations = len(source_block.get("citation_lines", []) or [])
    na = len(source_block.get("na_lines", []) or [])
    issues = source_block.get("issues", []) or []
    return citations, na, len(issues)


def _review_artifact_dir(artifact_dir: Path) -> int:
    run_dirs = sorted([p for p in artifact_dir.iterdir() if p.is_dir()])
    if not run_dirs:
        print(f"artifact_dir={artifact_dir}")
        print("runs=0")
        return 1

    status_counts = Counter()
    issue_counts = Counter()
    source_counts = Counter()
    total_runs = 0
    passed_runs = 0

    for run_dir in run_dirs:
        checks_path = run_dir / "checks.json"
        if not checks_path.exists():
            continue
        total_runs += 1
        checks = _load_checks(checks_path)
        status = str(checks.get("status", "unknown"))
        passed = bool(checks.get("passed", False))
        status_counts[status] += 1
        if passed:
            passed_runs += 1
        for issue in checks.get("issues", []) or []:
            issue_counts[issue] += 1
        citations, na, source_issues = _summarize_sources(checks.get("sources", {}))
        source_counts["citation_lines"] += citations
        source_counts["na_lines"] += na
        source_counts["source_issues"] += source_issues

    failed_runs = total_runs - passed_runs
    print(f"artifact_dir={artifact_dir}")
    print(f"runs={total_runs} passed={passed_runs} failed={failed_runs}")
    print("status_breakdown=" + ", ".join(f"{k}:{v}" for k, v in sorted(status_counts.items())) if status_counts else "status_breakdown=none")
    if issue_counts:
        top_issues = ", ".join(f"{k}:{v}" for k, v in issue_counts.most_common(5))
        print(f"common_issues={top_issues}")
    else:
        print("common_issues=none")
    print(
        "source_stats="
        f"citations:{source_counts['citation_lines']} "
        f"na:{source_counts['na_lines']} "
        f"source_issue_flags:{source_counts['source_issues']}"
    )
    return 0 if failed_runs == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="Review latest Metis E2E artifacts.")
    parser.add_argument(
        "--artifact-dir",
        default="",
        help="Optional explicit artifact directory. Defaults to latest under e2e_artifacts.",
    )
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir) if args.artifact_dir else _latest_artifact_dir(ARTIFACT_ROOT)
    if artifact_dir is None:
        print("No artifact directories found.")
        return 1

    return _review_artifact_dir(artifact_dir)


if __name__ == "__main__":
    raise SystemExit(main())
