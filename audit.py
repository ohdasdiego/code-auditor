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
    parser.add_argument("--output", default="audit_report.html",
                        help="Output file for the HTML report (default: audit_report.html)")
    parser.add_argument("--severity", nargs="+",
                        default=["critical", "warning", "info"],
                        choices=["critical", "warning", "info"],
                        help="Severity levels to include in the report")
    parser.add_argument("--max-files", type=int, default=20,
                        help="Max files to audit (default: 20)")
    parser.add_argument("--json", action="store_true",
                        help="Also save raw JSON results alongside the HTML report")
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

    print(f"\n🔍 Code Auditor — AI-Powered Code Review")
    print(f"{'=' * 50}")
    print(f"📁 Repo: {repo_path}")
    print(f"🌐 Languages: {', '.join(args.lang) if args.lang else 'auto-detect'}")
    print(f"🎯 Severity filter: {', '.join(args.severity)}")
    if args.fix:
        mode = "DRY RUN (no files written)" if args.dry_run else "APPLY FIXES"
        print(f"🔧 Fix mode: {mode}")
    print(f"{'=' * 50}\n")

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

    output_path = Path(args.output)
    generate_report(results, output_path, save_json=args.json)

    total_issues = sum(len(r.get("issues", [])) for r in results)
    critical = sum(1 for r in results for i in r.get("issues", []) if i.get("severity") == "critical")
    warnings = sum(1 for r in results for i in r.get("issues", []) if i.get("severity") == "warning")
    files_fixed = sum(1 for r in results if r.get("fix_result") and r["fix_result"].get("status") == "applied")
    files_dry = sum(1 for r in results if r.get("fix_result") and r["fix_result"].get("status") == "dry-run")

    print(f"\n{'=' * 50}")
    print(f"✅ Audit complete! {len(results)} file(s) reviewed.")
    print(f"   🔴 Critical: {critical}  🟡 Warning: {warnings}  🔵 Total: {total_issues}")
    if files_fixed:
        print(f"   🔧 Files fixed: {files_fixed} (backups saved as *.audit-backup)")
    if files_dry:
        print(f"   👁️  Dry-run diffs generated for {files_dry} file(s) — no files written")
    print(f"   📄 Report: {output_path.resolve()}")
    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    asyncio.run(main())
