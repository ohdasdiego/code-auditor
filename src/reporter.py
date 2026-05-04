"""
Reporter — colored terminal output for audit results.

Renders style issues and fingerprint issues in separate sections
so they're visually distinct and easy to act on.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

# ANSI
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BLUE   = "\033[94m"
PURPLE = "\033[95m"
GRAY   = "\033[90m"
RESET  = "\033[0m"

SEV_COLOR = {
    "critical": RED,
    "warning":  YELLOW,
    "info":     BLUE,
}

SEV_ICON = {
    "critical": "CRIT",
    "warning":  "WARN",
    "info":     "INFO",
}

PASS_COLOR = {
    "style":       CYAN,
    "fingerprint": PURPLE,
}

PASS_LABEL = {
    "style":       "STYLE",
    "fingerprint": "FINGERPRINT",
}

DIVIDER = "─" * 62


def generate_report(results: list[dict], output_path: Path, save_json: bool = False):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    total_issues = sum(len(r["issues"]) for r in results)
    critical = sum(1 for r in results for i in r["issues"] if i.get("severity") == "critical")
    warnings  = sum(1 for r in results for i in r["issues"] if i.get("severity") == "warning")
    info      = sum(1 for r in results for i in r["issues"] if i.get("severity") == "info")

    fp_issues = sum(1 for r in results for i in r["issues"] if i.get("pass") == "fingerprint")
    style_issues = total_issues - fp_issues

    scores = [r["score"] for r in results if r.get("score") is not None]
    avg_score = round(sum(scores) / len(scores)) if scores else 0

    print(f"\n{BOLD}{DIVIDER}{RESET}")
    print(f"{BOLD}  Code Audit Report  {now}{RESET}")
    print(f"{BOLD}{DIVIDER}{RESET}\n")

    print(f"  Repo Health Score:  {_score_color(avg_score)}{avg_score}/100{RESET}")
    print(f"  Files Reviewed:     {len(results)}")
    print(f"  Total Issues:       {BOLD}{total_issues}{RESET}  "
          f"{RED}{critical} critical{RESET}  "
          f"{YELLOW}{warnings} warnings{RESET}  "
          f"{BLUE}{info} info{RESET}")
    print(f"  Breakdown:          {CYAN}{style_issues} style{RESET}  "
          f"{PURPLE}{fp_issues} fingerprint{RESET}\n")

    for result in results:
        _render_file(result)

    if critical > 0:
        print(f"\n{BOLD}{RED}  {critical} critical issue(s) need attention.{RESET}")
    elif fp_issues > 0:
        print(f"\n{BOLD}{PURPLE}  {fp_issues} AI fingerprint(s) detected — run --humanize to clean.{RESET}")
    else:
        print(f"\n{BOLD}{GREEN}  Looks clean.{RESET}")

    if save_json:
        json_path = output_path.with_suffix(".json")
        _export_json(results, json_path)
        print(f"\n  JSON saved to: {json_path}")


def _render_file(result: dict):
    file_path   = result["file"]
    language    = result["language"]
    issues      = result["issues"]
    score       = result.get("score", 0)
    summaries   = result.get("pass_summaries", {})

    issue_count = len(issues)
    print(f"{BOLD}{DIVIDER}{RESET}")
    print(f"  {CYAN}{file_path}{RESET}")
    print(f"  {GRAY}{language.capitalize()} · {issue_count} issue(s) · "
          f"Score: {_score_color(score)}{score}/100{RESET}")

    for pass_name, summary in summaries.items():
        label = PASS_LABEL.get(pass_name, pass_name.upper())
        color = PASS_COLOR.get(pass_name, GRAY)
        print(f"  {color}[{label}]{RESET} {GRAY}{summary}{RESET}")

    print(f"  {DIVIDER}")

    # Group by pass for cleaner rendering
    style_issues = [i for i in issues if i.get("pass") == "style"]
    fp_issues    = [i for i in issues if i.get("pass") == "fingerprint"]

    if style_issues:
        print(f"\n  {BOLD}{CYAN}Style / Security{RESET}\n")
        for issue in style_issues:
            _render_issue(issue)

    if fp_issues:
        print(f"\n  {BOLD}{PURPLE}AI Fingerprints{RESET}\n")
        for issue in fp_issues:
            _render_issue(issue)

    if not issues:
        print(f"\n  {GREEN}No issues found.{RESET}\n")
    else:
        print()


def _render_issue(issue: dict):
    sev    = issue.get("severity", "info")
    color  = SEV_COLOR.get(sev, GRAY)
    icon   = SEV_ICON.get(sev, "INFO")
    line   = f"line {issue['line']}" if issue.get("line") else "     "
    rule   = issue.get("rule", "")
    desc   = issue.get("description", "")
    sugg   = issue.get("suggestion", "").strip()

    print(f"  {color}{BOLD}{icon}{RESET}  {GRAY}{line:<10}{RESET} {BOLD}{rule}{RESET}")
    print(f"  {' ' * 14}{desc}")

    if sugg:
        first = sugg.splitlines()[0]
        print(f"  {' ' * 14}{GREEN}fix: {first}{RESET}")
    print()


def _score_color(score: int) -> str:
    if score >= 80:
        return GREEN
    if score >= 50:
        return YELLOW
    return RED


def _export_json(results: list[dict], path: Path):
    exportable = [
        {k: v for k, v in r.items() if k != "code"}
        for r in results
    ]
    path.write_text(json.dumps(exportable, indent=2), encoding="utf-8")


def render_diff(diff: str, filename: str):
    print(f"\n{BOLD}{CYAN}Diff preview: {filename}{RESET}")
    print(DIVIDER)
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            print(f"{GREEN}{line}{RESET}")
        elif line.startswith("-") and not line.startswith("---"):
            print(f"{RED}{line}{RESET}")
        elif line.startswith("@@"):
            print(f"{CYAN}{line}{RESET}")
        else:
            print(line)
    print()
