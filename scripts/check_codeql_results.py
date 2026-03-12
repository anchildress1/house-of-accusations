#!/usr/bin/env python3
"""Fail the build if any CodeQL findings are not covered by approved suppressions.

Reads SARIF files from SARIF_DIR and checks each result against entries in
SUPPRESSIONS_FILE (.github/codeql/suppressions.yml). Exits 1 if any
unapproved findings are found.

Adding a suppression requires user approval and documentation in AGENTS.md.
"""

import fnmatch
import glob
import json
import os
import sys

import yaml


def main() -> int:
    sarif_dir = os.environ.get("SARIF_DIR", "codeql-sarif-results")
    suppressions_file = os.environ.get(
        "SUPPRESSIONS_FILE", ".github/codeql/suppressions.yml"
    )

    with open(suppressions_file) as f:
        config = yaml.safe_load(f) or {}
    suppressions = config.get("suppressions") or []

    sarif_files = glob.glob(f"{sarif_dir}/**/*.sarif", recursive=True)
    if not sarif_files:
        print("No SARIF files found — nothing to check")
        return 0

    findings = []
    for sarif_file in sarif_files:
        with open(sarif_file) as f:
            sarif = json.load(f)
        for run in sarif.get("runs", []):
            for result in run.get("results", []):
                rule_id = result.get("ruleId", "")
                locations = result.get("locations", [])
                uri = ""
                if locations:
                    uri = (
                        locations[0]
                        .get("physicalLocation", {})
                        .get("artifactLocation", {})
                        .get("uri", "")
                    )

                is_suppressed = any(
                    s["rule_id"] == rule_id
                    and (
                        not s.get("path_pattern")
                        or fnmatch.fnmatch(uri, s["path_pattern"])
                    )
                    for s in suppressions
                )
                if not is_suppressed:
                    findings.append({"rule_id": rule_id, "location": uri})

    if findings:
        print(f"CodeQL found {len(findings)} unapproved issue(s):")
        for finding in findings:
            print(f"  - {finding['rule_id']} in {finding['location']}")
        print()
        print("To suppress a finding:")
        print("  1. Add an entry to .github/codeql/suppressions.yml")
        print("  2. Document the approval in AGENTS.md under 'Approved CodeQL Suppressions'")
        print("  3. Get user approval before merging")
        return 1

    print(f"CodeQL: no unapproved findings across {len(sarif_files)} SARIF file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
