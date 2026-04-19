"""
fixer.py
Applies Claude-generated fixes to source files.
Supports --dry-run (preview only) and tracks applied fixes in .audit-state.json.
"""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

AUDIT_STATE_FILE = ".audit-state.json"


def load_state(repo_path: Path) -> dict:
    state_file = repo_path / AUDIT_STATE_FILE
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except Exception:
            pass
    return {"fixed": [], "accepted": [], "deferred": []}


def save_state(repo_path: Path, state: dict):
    state_file = repo_path / AUDIT_STATE_FILE
    state_file.write_text(json.dumps(state, indent=2))


def make_issue_key(file_path: str, issue: dict) -> str:
    """Stable key to identify an issue across runs."""
    return f"{file_path}:{issue.get('rule', 'unknown')}:line-{issue.get('line', '?')}"


def apply_fix(
    repo_path: Path,
    file_path: str,
    original_code: str,
    fixed_code: str,
    issues: list,
    dry_run: bool = False,
) -> dict:
    """
    Write fixed code to file (unless dry_run).
    Returns a summary of what was done.
    """
    abs_path = repo_path / file_path

    if dry_run:
        diff = _get_inline_diff(original_code, fixed_code, file_path)
        return {
            "file": file_path,
            "status": "dry-run",
            "issues_fixed": len(issues),
            "diff": diff,
        }

    # Back up original
    backup_path = abs_path.with_suffix(abs_path.suffix + ".audit-backup")
    backup_path.write_text(original_code, encoding="utf-8")

    # Write fixed version
    abs_path.write_text(fixed_code, encoding="utf-8")

    diff = _get_git_diff(repo_path, file_path)

    return {
        "file": file_path,
        "status": "applied",
        "issues_fixed": len(issues),
        "backup": str(backup_path),
        "diff": diff,
    }


def record_fixes(repo_path: Path, file_path: str, issues: list):
    """Persist applied fixes to .audit-state.json."""
    state = load_state(repo_path)
    for issue in issues:
        key = make_issue_key(file_path, issue)
        entry = {
            "key": key,
            "file": file_path,
            "rule": issue.get("rule"),
            "severity": issue.get("severity"),
            "fixed_at": datetime.now(timezone.utc).isoformat(),
        }
        # Avoid duplicates
        if not any(f["key"] == key for f in state["fixed"]):
            state["fixed"].append(entry)
    save_state(repo_path, state)


def mark_accepted(repo_path: Path, file_path: str, issues: list):
    """Mark issues as intentionally accepted (won't be re-flagged)."""
    state = load_state(repo_path)
    for issue in issues:
        key = make_issue_key(file_path, issue)
        if key not in state["accepted"]:
            state["accepted"].append(key)
    save_state(repo_path, state)


def filter_known_issues(repo_path: Path, file_path: str, issues: list) -> list:
    """Remove issues already fixed or accepted in a previous run."""
    state = load_state(repo_path)
    known = set(state["accepted"]) | {f["key"] for f in state["fixed"]}
    return [i for i in issues if make_issue_key(file_path, i) not in known]


def _get_git_diff(repo_path: Path, file_path: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--", file_path],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() or None
    except Exception:
        return None


def _get_inline_diff(original: str, fixed: str, label: str) -> str:
    """Simple line-by-line diff without subprocess."""
    orig_lines = original.splitlines(keepends=True)
    fixed_lines = fixed.splitlines(keepends=True)

    import difflib
    diff = list(difflib.unified_diff(
        orig_lines, fixed_lines,
        fromfile=f"a/{label}",
        tofile=f"b/{label}",
        lineterm="",
    ))
    return "".join(diff) if diff else "(no changes)"
