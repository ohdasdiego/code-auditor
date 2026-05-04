"""
Fixer — applies Claude-generated fixes and humanize rewrites to source files.

Tracks applied fixes in .audit-state.json so re-runs skip already-fixed issues.
"""

import difflib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


STATE_FILE = ".audit-state.json"


# ---------------------------------------------------------------------------
# Core apply functions
# ---------------------------------------------------------------------------

def apply_fix(
    repo_path: Path,
    rel_file: str,
    original_code: str,
    fixed_code: str,
    issues: list,
    dry_run: bool = False,
) -> dict:
    abs_path = repo_path / rel_file

    if dry_run:
        diff = _unified_diff(original_code, fixed_code, rel_file)
        return {
            "file": rel_file,
            "dry_run": True,
            "diff": diff,
            "issues_fixed": len(issues),
        }

    backup_path = _write_backup(abs_path)
    abs_path.write_text(fixed_code, encoding="utf-8")

    return {
        "file": rel_file,
        "dry_run": False,
        "backup": str(backup_path.relative_to(repo_path)),
        "issues_fixed": len(issues),
    }


def apply_humanize(
    repo_path: Path,
    rel_file: str,
    original_code: str,
    humanized_code: str,
    dry_run: bool = False,
) -> dict:
    abs_path = repo_path / rel_file

    if dry_run:
        diff = _unified_diff(original_code, humanized_code, rel_file)
        return {
            "file": rel_file,
            "dry_run": True,
            "diff": diff,
            "type": "humanize",
        }

    backup_path = _write_backup(abs_path)
    abs_path.write_text(humanized_code, encoding="utf-8")

    return {
        "file": rel_file,
        "dry_run": False,
        "backup": str(backup_path.relative_to(repo_path)),
        "type": "humanize",
    }


# ---------------------------------------------------------------------------
# State tracking
# ---------------------------------------------------------------------------

def record_fixes(repo_path: Path, rel_file: str, issues: list):
    state = _load_state(repo_path)
    file_state = state.setdefault(rel_file, {"fixed": [], "accepted": []})
    for issue in issues:
        key = _issue_key(issue)
        if key not in file_state["fixed"]:
            file_state["fixed"].append(key)
    state["_last_updated"] = datetime.now(timezone.utc).isoformat()
    _save_state(repo_path, state)


def mark_accepted(repo_path: Path, rel_file: str, issues: list):
    state = _load_state(repo_path)
    file_state = state.setdefault(rel_file, {"fixed": [], "accepted": []})
    for issue in issues:
        key = _issue_key(issue)
        if key not in file_state["accepted"]:
            file_state["accepted"].append(key)
    _save_state(repo_path, state)


def already_fixed(repo_path: Path, rel_file: str, issue: dict) -> bool:
    state = _load_state(repo_path)
    file_state = state.get(rel_file, {})
    key = _issue_key(issue)
    return key in file_state.get("fixed", []) or key in file_state.get("accepted", [])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unified_diff(original: str, modified: str, filename: str) -> str:
    orig_lines = original.splitlines(keepends=True)
    mod_lines = modified.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines,
        mod_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
    )
    return "".join(diff)


def _write_backup(path: Path) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    backup = path.with_suffix(f".{ts}.bak{path.suffix}")
    shutil.copy2(path, backup)
    return backup


def _issue_key(issue: dict) -> str:
    return f"{issue.get('rule','')}:{issue.get('line','')}:{issue.get('category','')}"


def _load_state(repo_path: Path) -> dict:
    state_path = repo_path / STATE_FILE
    if state_path.exists():
        try:
            return json.loads(state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_state(repo_path: Path, state: dict):
    state_path = repo_path / STATE_FILE
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
