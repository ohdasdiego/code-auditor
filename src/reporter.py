"""
Terminal reporter — clean, colored CLI output. No browser needed.
"""

import json
from pathlib import Path
from datetime import datetime, timezone


# ANSI color codes
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"

RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
GREEN  = "\033[92m"
CYAN   = "\033[96m"
WHITE  = "\033[97m"
GRAY   = "\033[90m"

SEVERITY_STYLE = {
    "critical": (RED,    "🔴 CRITICAL"),
    "warning":  (YELLOW, "🟡 WARNING "),
    "info":     (BLUE,   "🔵 INFO    "),
}


def generate_report(results: list[dict], output_path: Path, save_json: bool = False):
    """Print a terminal report. output_path is ignored (kept for API compat); use --json to save."""
    if save_json:
        json_path = output_path.with_suffix(".json")
        json_path.write_text(json.dumps(results, indent=2))
        print(f"   📦 JSON saved: {json_path.resolve()}")

    _print_report(results)


def _print_report(results: list[dict]):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    all_issues = [i for r in results for i in r.get("issues", [])]
    total_issues = len(all_issues)
    critical_count = sum(1 for i in all_issues if i.get("severity") == "critical")
    warning_count  = sum(1 for i in all_issues if i.get("severity") == "warning")
    info_count     = sum(1 for i in all_issues if i.get("severity") == "info")
    avg_score = (
        round(sum(r.get("health_score", 100) for r in results) / len(results))
        if results else 100
    )

    W = 60

    # ── Header ──────────────────────────────────────────────────
    print()
    print(f"{BOLD}{CYAN}{'─' * W}{RESET}")
    print(f"{BOLD}{CYAN}  🔍 AI Code Audit Report{RESET}  {GRAY}{now}{RESET}")
    print(f"{BOLD}{CYAN}{'─' * W}{RESET}")

    # ── Summary row ─────────────────────────────────────────────
    score_color = GREEN if avg_score >= 80 else YELLOW if avg_score >= 50 else RED
    print(f"\n  {BOLD}Repo Health Score:{RESET}  {score_color}{BOLD}{avg_score}/100{RESET}")
    print(f"  {BOLD}Files Reviewed:   {RESET}  {WHITE}{len(results)}{RESET}")
    print(f"  {BOLD}Total Issues:     {RESET}  {WHITE}{total_issues}{RESET}  "
          f"{RED}{critical_count} critical{RESET}  "
          f"{YELLOW}{warning_count} warnings{RESET}  "
          f"{BLUE}{info_count} info{RESET}")

    # ── Per-file sections ────────────────────────────────────────
    for result in results:
        _print_file(result, W)

    # ── Footer ───────────────────────────────────────────────────
    print(f"\n{BOLD}{CYAN}{'─' * W}{RESET}")
    if critical_count > 0:
        print(f"  {RED}{BOLD}⚠  {critical_count} critical issue(s) need attention.{RESET}")
    else:
        print(f"  {GREEN}{BOLD}✅  No critical issues found.{RESET}")
    print(f"{BOLD}{CYAN}{'─' * W}{RESET}\n")


def _print_file(result: dict, width: int):
    issues   = result.get("issues", [])
    score    = result.get("health_score", 100)
    lang     = result.get("language", "").capitalize()
    filepath = result.get("file", "")
    truncated = " (truncated)" if result.get("truncated") else ""

    score_color = GREEN if score >= 80 else YELLOW if score >= 50 else RED

    print(f"\n  {BOLD}{CYAN}📄 {filepath}{RESET}{GRAY}{truncated}{RESET}")
    print(f"  {GRAY}{lang} · {len(issues)} issue(s) · Score: "
          f"{score_color}{BOLD}{score}/100{RESET}")
    print(f"  {'─' * (width - 2)}")

    if not issues:
        print(f"  {GREEN}✅  No issues found{RESET}")
        return

    for issue in issues:
        sev = issue.get("severity", "info")
        color, label = SEVERITY_STYLE.get(sev, (GRAY, "⚪ UNKNOWN  "))
        line  = f"line {issue['line']}" if issue.get("line") else "—"
        rule  = issue.get("rule", "")
        desc  = issue.get("description", "")
        src   = issue.get("source", "")
        sugg  = issue.get("suggestion", "").strip()

        print(f"\n  {color}{BOLD}{label}{RESET}  {GRAY}{line}{RESET}  "
              f"{CYAN}{rule}{RESET}")
        print(f"  {WHITE}{desc}{RESET}")
        if src:
            print(f"  {GRAY}📖 {src}{RESET}")
        if sugg:
            # Indent multi-line suggestions
            lines = sugg.splitlines()
            print(f"  {GREEN}💡 {lines[0]}{RESET}")
            for l in lines[1:]:
                print(f"     {GREEN}{l}{RESET}")

    # Fix result banner
    fix = result.get("fix_result")
    if fix:
        if fix.get("status") == "applied":
            print(f"\n  {GREEN}✅ {fix['issues_fixed']} issue(s) fixed — "
                  f"backup: {fix['backup']}{RESET}")
        elif fix.get("status") == "dry-run" and fix.get("diff"):
            print(f"\n  {YELLOW}👁  Dry-run diff:{RESET}")
            for l in fix["diff"].splitlines():
                if l.startswith("+"):
                    print(f"  {GREEN}{l}{RESET}")
                elif l.startswith("-"):
                    print(f"  {RED}{l}{RESET}")
                else:
                    print(f"  {GRAY}{l}{RESET}")
