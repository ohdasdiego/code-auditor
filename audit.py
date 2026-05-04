#!/usr/bin/env python3
"""
Code Auditor — AI-powered code review CLI.

Three audit passes:
  style        — correctness, security, style-guide compliance
  fingerprint  — AI-tell detection (emojis, generic names, comment narration, etc.)
  humanize     — full naturalizing rewrite pass (rewrites the file, not just flags)

Usage examples:
  python3 audit.py ./my-project
  python3 audit.py ./my-project --fingerprint
  python3 audit.py ./my-project --humanize --dry-run
  python3 audit.py ./my-project --pass style fingerprint --fix
  python3 audit.py ./my-project --diff --severity critical --json
  python3 audit.py ./my-project --interactive
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.auditor import CodeAuditor
from src.reporter import generate_report, render_diff
from src.fixer import apply_fix, apply_humanize, record_fixes, mark_accepted

__version__ = "2.0.0"

_BOLD   = "\033[1m"
_CYAN   = "\033[96m"
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_RED    = "\033[91m"
_PURPLE = "\033[95m"
_GRAY   = "\033[90m"
_RESET  = "\033[0m"

SEV_COLOR = {"critical": _RED, "warning": _YELLOW, "info": "\033[94m"}
PASS_COLOR = {"style": _CYAN, "fingerprint": _PURPLE}


def parse_args():
    parser = argparse.ArgumentParser(
        description=f"Code Auditor v{__version__} — AI-powered code review powered by Claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Passes:
  style        Standard style/security/structure review against official guides
  fingerprint  Hunt for AI-generated code tells (emojis, generic names, narrator comments...)

Examples:
  python3 audit.py ./project                          # style + fingerprint (default)
  python3 audit.py ./project --fingerprint            # fingerprint pass only
  python3 audit.py ./project --humanize               # rewrite files to remove AI tells
  python3 audit.py ./project --humanize --dry-run     # preview humanize changes as diff
  python3 audit.py ./project --pass style --fix       # style fixes only
  python3 audit.py ./project --interactive            # pick which fixes to apply
  python3 audit.py ./project --diff --severity critical --json
        """,
    )

    parser.add_argument("repo_path", help="Path to the repo or folder to audit")
    parser.add_argument("--lang", nargs="+", default=None,
                        choices=["python", "java", "javascript", "typescript"],
                        help="Languages to audit (default: auto-detect)")
    parser.add_argument("--pass", dest="passes", nargs="+",
                        default=["style", "fingerprint"],
                        choices=["style", "fingerprint"],
                        help="Which audit passes to run (default: style fingerprint)")
    parser.add_argument("--fingerprint", action="store_true",
                        help="Shorthand: run fingerprint pass only")
    parser.add_argument("--diff", action="store_true",
                        help="Only audit files changed in the last git commit")
    parser.add_argument("--severity", nargs="+",
                        default=["critical", "warning", "info"],
                        choices=["critical", "warning", "info"],
                        help="Severity levels to include")
    parser.add_argument("--max-files", type=int, default=20,
                        help="Max files to audit (default: 20)")
    parser.add_argument("--fix", action="store_true",
                        help="Apply AI-generated fixes to source files")
    parser.add_argument("--humanize", action="store_true",
                        help="Run humanize rewrite pass — removes AI fingerprints from source files")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes as unified diff without writing any files")
    parser.add_argument("--interactive", action="store_true",
                        help="Review proposed fixes and choose which to apply")
    parser.add_argument("--json", action="store_true",
                        help="Save results to audit_report.json")
    parser.add_argument("--model", default=None,
                        help="Override Claude model (default: claude-sonnet-4-6)")
    parser.add_argument("--version", action="version", version=f"code-auditor {__version__}")

    return parser.parse_args()


# ---------------------------------------------------------------------------
# Interactive fix mode
# ---------------------------------------------------------------------------

async def run_interactive(auditor: CodeAuditor, results: list):
    repo_path = auditor.repo_path

    fixable = []
    for result in results:
        for issue in result.get("issues", []):
            fixable.append({
                "file": result["file"],
                "issue": issue,
                "language": result["language"],
            })

    if not fixable:
        print(f"\n{_GREEN}No fixable issues found.{_RESET}")
        return

    print(f"\n{_BOLD}{_CYAN}{'─' * 62}{_RESET}")
    print(f"{_BOLD}{_CYAN}  Fix Review — {len(fixable)} proposed fix(es){_RESET}")
    print(f"{_BOLD}{_CYAN}{'─' * 62}{_RESET}\n")

    for idx, item in enumerate(fixable, 1):
        issue = item["issue"]
        sev = issue.get("severity", "info")
        color = SEV_COLOR.get(sev, _GRAY)
        pass_name = issue.get("pass", "style")
        pass_color = PASS_COLOR.get(pass_name, _GRAY)
        line = f"line {issue['line']}" if issue.get("line") else "-"
        desc = issue.get("description", "")[:90]

        print(f"  {_BOLD}[{idx:>2}]{_RESET}  "
              f"{color}{sev.upper():<8}{_RESET}  "
              f"{pass_color}[{pass_name.upper():<11}]{_RESET}  "
              f"{_CYAN}{item['file']}{_RESET}  {_GRAY}{line}{_RESET}")
        print(f"         {issue.get('rule','')} — {desc}")
        if sugg := issue.get("suggestion", "").strip():
            print(f"         {_GREEN}fix: {sugg.splitlines()[0]}{_RESET}")
        print()

    print(f"{_BOLD}Apply which fixes?{_RESET}")
    print(f"  Numbers (e.g. {_GRAY}1,3,5{_RESET}), "
          f"{_BOLD}all{_RESET}, "
          f"{_BOLD}critical{_RESET}, "
          f"{_BOLD}warning{_RESET}, "
          f"{_BOLD}fingerprint{_RESET}, "
          f"{_BOLD}style{_RESET}, "
          f"or {_BOLD}none{_RESET}\n")

    try:
        raw = input(f"{_CYAN}> {_RESET}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print(f"\n{_YELLOW}Aborted.{_RESET}")
        return

    if not raw or raw == "none":
        print(f"\n{_GRAY}No fixes applied.{_RESET}")
        return

    if raw == "all":
        selected = list(range(len(fixable)))
    elif raw in ("critical", "warning", "info"):
        selected = [i for i, item in enumerate(fixable)
                    if item["issue"].get("severity") == raw]
    elif raw in ("fingerprint", "style"):
        selected = [i for i, item in enumerate(fixable)
                    if item["issue"].get("pass") == raw]
    else:
        selected = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(fixable):
                    selected.append(idx)

    if not selected:
        print(f"\n{_GRAY}Nothing selected.{_RESET}")
        return

    print(f"\n  {_GRAY}Selected {len(selected)} fix(es).{_RESET}\n")

    by_file: dict[str, list] = {}
    for idx in selected:
        item = fixable[idx]
        by_file.setdefault(item["file"], []).append((item["issue"], item["language"]))

    for rel_file, issue_lang_pairs in by_file.items():
        abs_path = repo_path / rel_file
        original = abs_path.read_text(encoding="utf-8", errors="replace")
        issues = [p[0] for p in issue_lang_pairs]
        language = issue_lang_pairs[0][1]

        print(f"  {_CYAN}Fixing {rel_file} ({len(issues)} issue(s))...{_RESET}")
        fixed = await auditor._call_claude_fix(original, language, rel_file, issues)
        if not fixed:
            print(f"  {_RED}Could not generate fix for {rel_file}{_RESET}")
            continue

        result = apply_fix(repo_path, rel_file, original, fixed, issues)
        record_fixes(repo_path, rel_file, issues)
        print(f"  {_GREEN}Done — backup: {result['backup']}{_RESET}")

    print(f"\n{_BOLD}{_GREEN}All done.{_RESET}")


# ---------------------------------------------------------------------------
# Humanize mode
# ---------------------------------------------------------------------------

async def run_humanize(auditor: CodeAuditor, results: list, dry_run: bool):
    repo_path = auditor.repo_path

    targets = [r for r in results if any(
        i.get("pass") == "fingerprint" for i in r.get("issues", [])
    )]

    if not targets:
        print(f"\n{_GREEN}No fingerprint issues found — nothing to humanize.{_RESET}")
        return

    verb = "Previewing" if dry_run else "Humanizing"
    print(f"\n{_BOLD}{verb} {len(targets)} file(s)...{_RESET}\n")

    for result in targets:
        rel_file = result["file"]
        language = result["language"]
        fp_count = sum(1 for i in result["issues"] if i.get("pass") == "fingerprint")
        abs_path = repo_path / rel_file
        original = abs_path.read_text(encoding="utf-8", errors="replace")

        print(f"  {_PURPLE}{rel_file}{_RESET} ({fp_count} fingerprint issue(s))")
        humanized = await auditor._call_claude_humanize(original, language, rel_file)
        if not humanized:
            print(f"  {_RED}Humanize failed for {rel_file}{_RESET}")
            continue

        outcome = apply_humanize(repo_path, rel_file, original, humanized, dry_run=dry_run)
        if dry_run:
            render_diff(outcome["diff"], rel_file)
        else:
            print(f"  {_GREEN}Done — backup: {outcome['backup']}{_RESET}")

    if not dry_run:
        print(f"\n{_BOLD}{_GREEN}Humanize complete.{_RESET}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    args = parse_args()
    repo_path = Path(args.repo_path).resolve()

    if not repo_path.exists():
        print(f"Error: path not found: {repo_path}")
        sys.exit(1)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\nError: ANTHROPIC_API_KEY not set.")
        print("  Add it to a .env file:  cp .env.example .env")
        print("  Or export it:           export ANTHROPIC_API_KEY=your_key")
        print("\n  Get a key at: https://console.anthropic.com/\n")
        sys.exit(1)

    # Resolve passes
    passes = ["fingerprint"] if args.fingerprint else args.passes
    # Humanize implies fingerprint pass so we know what to target
    if args.humanize and "fingerprint" not in passes:
        passes = list(passes) + ["fingerprint"]

    lang_str = ", ".join(args.lang) if args.lang else "auto-detect"
    mode_parts = []
    if args.humanize:
        mode_parts.append("humanize" + (" dry-run" if args.dry_run else ""))
    elif args.fix:
        mode_parts.append("fix" + (" dry-run" if args.dry_run else ""))
    elif args.interactive:
        mode_parts.append("interactive")

    mode_str = f" [{', '.join(mode_parts)}]" if mode_parts else ""
    passes_str = ", ".join(passes)
    print(f"\nScanning {repo_path.name}  [{lang_str}]  passes: {passes_str}{mode_str}\n")

    auditor = CodeAuditor(
        repo_path=repo_path,
        languages=args.lang,
        diff_only=args.diff,
        severity_filter=args.severity,
        max_files=args.max_files,
        model=args.model,
        fix=args.fix and not args.interactive and not args.humanize,
        dry_run=args.dry_run,
        passes=passes,
    )

    results = await auditor.run()

    if not results:
        print("No files found to audit.")
        return

    generate_report(results, Path("audit_report"), save_json=args.json)

    if args.humanize:
        await run_humanize(auditor, results, dry_run=args.dry_run)
    elif args.interactive:
        await run_interactive(auditor, results)


if __name__ == "__main__":
    asyncio.run(main())
