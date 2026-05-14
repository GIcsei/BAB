#!/usr/bin/env python3
"""Generate HTML security reports from JSON scan results."""

import argparse
import json
from datetime import datetime
from pathlib import Path

from jinja2 import Template

REPORT_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 30px; }
        h1 { color: #333; margin-bottom: 10px; border-bottom: 3px solid #2196F3; padding-bottom: 10px; }
        .meta { color: #666; font-size: 14px; margin-bottom: 20px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }
        .metric { background: #f9f9f9; padding: 15px; border-radius: 5px; border-left: 4px solid #2196F3; }
        .metric .label { font-size: 12px; color: #999; text-transform: uppercase; }
        .metric .value { font-size: 28px; font-weight: bold; margin-top: 5px; }
        .critical { border-left-color: #d32f2f !important; }
        .critical .value { color: #d32f2f; }
        .high { border-left-color: #f57c00 !important; }
        .high .value { color: #f57c00; }
        .medium { border-left-color: #fbc02d !important; }
        .medium .value { color: #fbc02d; }
        .low { border-left-color: #388e3c !important; }
        .low .value { color: #388e3c; }
        .details { margin-top: 30px; }
        .details h2 { margin-top: 20px; margin-bottom: 10px; color: #333; }
        pre { background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; font-size: 12px; line-height: 1.4; }
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ title }}</h1>
        <div class="meta">
            <strong>Generated:</strong> {{ timestamp }}<br>
            <strong>Report Version:</strong> BAB CI/CD Security Report v1
        </div>
        <div class="summary">
            <div class="metric critical">
                <div class="label">Critical</div>
                <div class="value">{{ critical }}</div>
            </div>
            <div class="metric high">
                <div class="label">High</div>
                <div class="value">{{ high }}</div>
            </div>
            <div class="metric medium">
                <div class="label">Medium</div>
                <div class="value">{{ medium }}</div>
            </div>
            <div class="metric low">
                <div class="label">Low</div>
                <div class="value">{{ low }}</div>
            </div>
            <div class="metric">
                <div class="label">Total Issues</div>
                <div class="value">{{ total_issues }}</div>
            </div>
        </div>
        <div class="details">
            <h2>Scan Details</h2>
            <pre>{{ details }}</pre>
        </div>
    </div>
</body>
</html>"""


def parse_trivy_json(file_path):
    """Parse Trivy JSON and extract summary."""
    with open(file_path) as f:
        data = json.load(f)

    results = data.get("Results", [])
    vulns = []
    for result in results:
        vulns.extend(result.get("Vulnerabilities", []))

    summary = {
        "critical": sum(1 for v in vulns if v.get("Severity") == "CRITICAL"),
        "high": sum(1 for v in vulns if v.get("Severity") == "HIGH"),
        "medium": sum(1 for v in vulns if v.get("Severity") == "MEDIUM"),
        "low": sum(1 for v in vulns if v.get("Severity") == "LOW"),
    }
    summary["total"] = sum(summary.values())
    summary["details"] = json.dumps(data, indent=2)
    return summary


def parse_bandit_json(file_path):
    """Parse Bandit JSON and extract summary."""
    with open(file_path) as f:
        data = json.load(f)

    results = data.get("results", [])
    summary = {
        "critical": sum(
            1
            for r in results
            if r.get("severity") == "HIGH" and r.get("confidence") == "HIGH"
        ),
        "high": sum(1 for r in results if r.get("severity") == "HIGH"),
        "medium": sum(1 for r in results if r.get("severity") == "MEDIUM"),
        "low": sum(1 for r in results if r.get("severity") == "LOW"),
    }
    summary["total"] = len(results)
    summary["details"] = json.dumps(data, indent=2)
    return summary


def parse_pip_audit_json(file_path):
    """Parse pip-audit JSON and extract summary."""
    with open(file_path) as f:
        data = json.load(f)

    vulnerabilities = data.get("vulnerabilities", [])
    summary = {
        "critical": sum(1 for v in vulnerabilities if not v.get("fix_versions", [])),
        "high": len(vulnerabilities),
        "medium": 0,
        "low": 0,
    }
    summary["total"] = len(vulnerabilities)
    summary["details"] = json.dumps(data, indent=2)
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Generate HTML security reports from JSON scan results"
    )
    parser.add_argument(
        "--input-dir", required=True, help="Directory with JSON scan results"
    )
    parser.add_argument(
        "--output-dir", required=True, help="Directory to write HTML reports"
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process each scan type
    scanners = [
        ("trivy-release.json", "Trivy Security Scan Report", parse_trivy_json),
        ("bandit-release.json", "Bandit Code Security Report", parse_bandit_json),
        (
            "pip-audit.json",
            "Pip-Audit Dependency Vulnerability Report",
            parse_pip_audit_json,
        ),
    ]

    for file_name, title, parser_func in scanners:
        json_file = input_dir / file_name
        if json_file.exists():
            try:
                summary = parser_func(json_file)
                html = Template(REPORT_TEMPLATE).render(
                    title=title,
                    timestamp=datetime.now().isoformat(),
                    total_issues=summary["total"],
                    critical=summary["critical"],
                    high=summary["high"],
                    medium=summary["medium"],
                    low=summary["low"],
                    details=summary["details"],
                )
                output_file = output_dir / f"{file_name.replace('.json', '.html')}"
                output_file.write_text(html)
                print(f"✓ Generated: {output_file}")
            except Exception as e:
                print(f"✗ Error processing {file_name}: {e}")
        else:
            print(f"⊘ Skipped (not found): {json_file}")


if __name__ == "__main__":
    main()
