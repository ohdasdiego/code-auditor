#!/usr/bin/env python3
"""
Code Auditor - AI-powered code review using Claude API.
Usage: python3 audit.py <path-to-repo> [options]
"""

import argparse
import asyncio
import sys
from pathlib import Path
from src.auditor import CodeAuditor
from src.reporter import generate_report
from src.fixer import apply_fix, record_fixes, mark_accepted

# ANSI helpers for interactive mode
_BOLD   = "\033[1m"
_CYAN   = "\033[96m"
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_RED    = "\033[91m"
_GRAY   = "\033[90m"
_RESET  = "\033[0m"

SEV_COLOR = {"critical": _RED, "warning": _YELLOW, "info": "\033[94m"}


def parse_args():
    parser = argparse.ArgumentParser(
        description="AI Code Auditor - Powered by Claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 audit.py ./my-project
  python3 audit.py ./my-project --lang python
  python3 audit.py ./my-project --diff
  python3 audit.py ./my-project --severity critical
  python3 audit.py ./my-project --fix --dry-run
  python3 audit.py ./my-project --interactive
        """
    )
    parser.add_argument("repo_path", help="Path to the repository or folder to audit")
    parser.add_argument("--lang", nargs="+", default=None,
                        choices=["python", "java", "javascript", "typescript"],
                        help="Languages to audit (default: auto-detect all supported)")
    parser.add_argument("--diff", action="store_true",
                        help="Only audit files changed in the last git commit")
    parser.add_argument("--severity", nargs="+",
                        default=["critical", "warning", "info"],
                        choices=["critical", "warning", "info"],
                        help="Severity levels to include in the report")
    parser.add_argument("--max-files", type=int, default=20,
                        help="Max files to audit (default: 20)")
    parser.add_argument("--json", action="store_true",
                        help="Save raw JSON results to audit_report.json")
    parser.add_argument("--model", default=None,
                        help="Override the Claude model (default: claude-sonnet-4-6)")
    parser.add_argument("--fix", action="store_true",
                        help="Apply AI-generated fixes directly to source files")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview fixes as a diff without writing any files (use with --fix)")
    parser.add_argument("--interactive", action="store_true",
                        help="Review all proposed fixes and choose which to apply by number")
    return parser.parse_args()


async def run_interactive(auditor: CodeAuditor, results: list):
    """
    Interactive fix mode: show a numbered list of all fixable issues,
    let the user pick which ones to apply (e.g. '1,3,5' or 'all' or 'none').
    """
    repo_path = auditor.repo_path

    # Collect all fixable issues across files
    fixable = []
    for result in results:
        for issue in result.get("issues", []):
            fixable.append({
                "file": result["file"],
                "issue": issue,
                "original_code": (repo_path / result["file"]).read_text(encoding="utf-8", errors="replace"),
            })

    if not fixable:
        print(f"\n{_GREEN}No fixable issues found.{_RESET}")
        return

    # Print numbered summary
    print(f"\n{_BOLD}{_CYAN}{'─' * 60}{_RESET}")
    print(f"{_BOLD}{_CYAN}  Fix Review — {len(fixable)} proposed fix(es){_RESET}")
    print(f"{_BOLD}{_CYAN}{'─' * 60}{_RESET}\n")

    for idx, item in enumerate(fixable, 1):
        issue = item["issue"]
        sev = issue.get("severity", "info")
        color = SEV_COLOR.get(sev, _GRAY)
        line = f"line {issue['line']}" if issue.get("line") else "-"
        rule = issue.get("rule", "")
        desc = issue.get("description", "")[:80]
        print(f"  {_BOLD}[{idx:>2}]{_RESET}  {color}{sev.upper():<8}{_RESET}  "
              f"{_CYAN}{item['file']}{_RESET}  {_GRAY}{line}{_RESET}")
        print(f"         {rule}  —  {desc}")
        sugg = issue.get("suggestion", "").strip()
        if sugg:
            first_line = sugg.splitlines()[0]
            print(f"         {_GREEN}fix: {first_line}{_RESET}")
        print()

    # Prompt
    print(f"{_BOLD}Which fixes do you want to apply?{_RESET}")
    print(f"  Enter numbers separated by commas  {_GRAY}(e.g. 1,3,5){_RESET}")
    print(f"  or {_BOLD}'all'{_RESET} to apply everything")
    print(f"  or {_BOLD}'none'{_RESET} to skip all\n")

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
    else:
        selected = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(fixable):
                    selected.append(idx)
                else:
                    print(f"  {_YELLOW}Skipping out-of-range index: {part}{_RESET}")

    if not selected:
        print(f"\n{_GRAY}No valid selections. Nothing applied.{_RESET}")
        return

    # Group selected issues by file
    by_file: dict[str, list] = {}
    for idx in selected:
        item = fixable[idx]
        by_file.setdefault(item["file"], []).append(item["issue"])

    # For each file, ask Claude to fix only selected issues, then apply
    print(f"\n{_BOLD}Applying {len(selected)} fix(es) across {len(by_file)} file(s)...{_RESET}\n")

    for file_path, issues in by_file.items():
        abs_path = repo_path / file_path
        original_code = abs_path.read_text(encoding="utf-8", errors="replace")
        lang = next(
            (r["language"] for r in results if r["file"] == file_path), "python"
        )

        print(f"  {_CYAN}Fixing {file_path} ({len(issues)} issue(s))...{_RESET}")
        fixed_code = await auditor._call_claude_fix(original_code, lang, file_path, issues)

        if not fixed_code:
            print(f"  {_RED}Could not generate fix for {file_path}{_RESET}")
            continue

        fix_result = apply_fix(repo_path, file_path, original_code, fixed_code, issues)
        record_fixes(repo_path, file_path, issues)

        print(f"  {_GREEN}Done — {fix_result['issues_fixed']} issue(s) fixed. "
              f"Backup: {fix_result['backup']}{_RESET}")

    print(f"\n{_BOLD}{_GREEN}All done!{_RESET}")


async def main():
    args = parse_args()
    repo_path = Path(args.repo_path).resolve()

    if not repo_path.exists():
        print(f"Error: Path not found: {repo_path}")
        sys.exit(1)

    fix_mode = ""
    if args.interactive:
        fix_mode = " - interactive"
    elif args.fix:
        fix_mode = f" - fix={'dry-run' if args.dry_run else 'apply'}"
    lang_str = ', '.join(args.lang) if args.lang else 'auto-detect'
    print(f"\nScanning {repo_path.name}  [{lang_str}{fix_mode}]\n")

    auditor = CodeAuditor(
        repo_path=repo_path,
        languages=args.lang,
        diff_only=args.diff,
        severity_filter=args.severity,
        max_files=args.max_files,
        model=args.model,
        fix=args.fix and not args.interactive,
        dry_run=args.dry_run,
    )

    results = await auditor.run()

    if not results:
        print("No files found to audit.")
        return

    output_path = Path("audit_report")
    generate_report(results, output_path, save_json=args.json)

    if args.interactive:
        await run_interactive(auditor, results)


if __name__ == "__main__":
    asyncio.run(main())
