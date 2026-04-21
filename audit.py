#!/usr/bin/env python3
"""
Code Auditor — AI-powered code review using Claude API.
Usage: python audit.py <path-to-repo> [options]
"""

import argparse
import asyncio
import sys
from pathlib import Path
from src.auditor import CodeAuditor
from src.reporter import generate_report


def parse_args():
    parser = argparse.ArgumentParser(
        description="AI Code Auditor — Powered by Claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python audit.py ./my-project
  python audit.py ./my-project --lang python java
  python audit.py ./my-project --diff --output report.html
  python audit.py ./my-project --severity critical warning
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
    return parser.parse_args()


async def main():
    args = parse_args()
    repo_path = Path(args.repo_path).resolve()

    if not repo_path.exists():
        print(f"❌ Path not found: {repo_path}")
        sys.exit(1)

    fix_mode = ""
    if args.fix:
        fix_mode = f" · fix={'dry-run' if args.dry_run else 'apply'}"
    lang_str = ', '.join(args.lang) if args.lang else 'auto-detect'
    print(f"\n🔍 Scanning {repo_path.name}  [{lang_str}{fix_mode}]\n")

    auditor = CodeAuditor(
        repo_path=repo_path,
        languages=args.lang,
        diff_only=args.diff,
        severity_filter=args.severity,
        max_files=args.max_files,
        model=args.model,
        fix=args.fix,
        dry_run=args.dry_run,
    )

    results = await auditor.run()

    if not results:
        print("✅ No files found to audit.")
        return

    output_path = Path("audit_report")  # base path for JSON if requested
    generate_report(results, output_path, save_json=args.json)


if __name__ == "__main__":
    asyncio.run(main())
