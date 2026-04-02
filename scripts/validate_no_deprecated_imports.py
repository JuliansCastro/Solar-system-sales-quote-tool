from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_PATTERNS = [
    re.compile(r"\bfrom\s+deprecated\b"),
    re.compile(r"\bimport\s+deprecated\b"),
    re.compile(r"\bfrom\s+deprecated\.", re.IGNORECASE),
    re.compile(r"\bimport\s+deprecated\.", re.IGNORECASE),
    re.compile(r"\bcall_command\(\s*['\"](?:run_load_equipment|setup_test_data)['\"]"),
]

EXCLUDED_PARTS = {".git", ".venv", "venv", "__pycache__", "deprecated"}
SCANNED_SUFFIXES = {".py"}


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDED_PARTS for part in path.parts)


def scan_file(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8", errors="ignore")
    findings: list[str] = []
    for idx, line in enumerate(content.splitlines(), start=1):
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(line):
                findings.append(f"{path.relative_to(REPO_ROOT)}:{idx}: {line.strip()}")
                break
    return findings


def main() -> int:
    findings: list[str] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SCANNED_SUFFIXES:
            continue
        if should_skip(path):
            continue
        findings.extend(scan_file(path))

    if findings:
        print("Deprecated references found:")
        for finding in findings:
            print(f" - {finding}")
        return 1

    print("No deprecated references found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
