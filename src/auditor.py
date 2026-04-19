"""
Core auditor — discovers files, sends them to Claude, collects results.
"""

import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Optional
import anthropic

from .prompts import build_system_prompt, build_user_prompt, build_fix_prompt
from .languages import detect_language, SUPPORTED_EXTENSIONS
from .fixer import apply_fix, record_fixes, filter_known_issues

# Model — Sonnet balances reasoning quality with cost for code analysis
MODEL = "claude-sonnet-4-6"

# Max characters per file before we chunk it
MAX_FILE_CHARS = 12_000

# Health score deductions per severity
SCORE_DEDUCTIONS = {"critical": 15, "warning": 5, "info": 1}


class CodeAuditor:
    def __init__(
        self,
        repo_path: Path,
        languages: Optional[list] = None,
        diff_only: bool = False,
        severity_filter: Optional[list] = None,
        max_files: int = 20,
        model: Optional[str] = None,
        fix: bool = False,
        dry_run: bool = False,
    ):
        self.repo_path = repo_path
        self.languages = languages
        self.diff_only = diff_only
        self.severity_filter = severity_filter or ["critical", "warning", "info"]
        self.max_files = max_files
        self.model = model or MODEL
        self.fix = fix
        self.dry_run = dry_run
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    async def run(self) -> list[dict]:
        files = self._collect_files()
        if not files:
            print("⚠️  No supported source files found.")
            return []

        print(f"📂 Found {len(files)} file(s) to audit...\n")

        tasks = [self._audit_file(f) for f in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = []
        for f, result in zip(files, results):
            if isinstance(result, Exception):
                print(f"  ⚠️  Error auditing {f.name}: {result}")
            elif result:
                output.append(result)

        return output

    def _collect_files(self) -> list[Path]:
        if self.diff_only:
            return self._get_diff_files()

        all_files = []
        for ext, lang in SUPPORTED_EXTENSIONS.items():
            if self.languages and lang not in self.languages:
                continue
            all_files.extend(self.repo_path.rglob(f"*{ext}"))

        # Filter out hidden dirs, venvs, node_modules, etc.
        filtered = [
            f for f in all_files
            if not any(part.startswith(".") or part in {
                "node_modules", "venv", "__pycache__", "dist", "build", ".git"
            } for part in f.parts)
        ]

        return sorted(filtered)[: self.max_files]

    def _get_diff_files(self) -> list[Path]:
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )
            changed = [
                self.repo_path / f.strip()
                for f in result.stdout.splitlines()
                if f.strip()
            ]
            return [
                f for f in changed
                if f.exists() and f.suffix in SUPPORTED_EXTENSIONS
            ][: self.max_files]
        except Exception as e:
            print(f"⚠️  Git diff failed ({e}), falling back to full scan.")
            return self._collect_files()

    async def _audit_file(self, file_path: Path) -> Optional[dict]:
        try:
            original_code = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

        if len(original_code.strip()) < 30:
            return None  # Skip near-empty files

        lang = detect_language(file_path)
        relative_path = str(file_path.relative_to(self.repo_path))

        print(f"  🔎 Auditing: {relative_path} ({lang})")

        # Truncate very large files with a note
        code = original_code
        truncated = False
        if len(code) > MAX_FILE_CHARS:
            code = code[:MAX_FILE_CHARS]
            truncated = True

        issues = await self._call_claude(code, lang, relative_path)

        # Filter out already-fixed/accepted issues from previous runs
        issues = filter_known_issues(self.repo_path, relative_path, issues)

        # Apply severity filter
        filtered_issues = [
            i for i in issues
            if i.get("severity", "info") in self.severity_filter
        ]

        fix_result = None
        if self.fix and filtered_issues:
            print(f"  🔧 Fixing: {relative_path} ({len(filtered_issues)} issue(s))...")
            fixed_code = await self._call_claude_fix(code, lang, relative_path, filtered_issues)
            if fixed_code:
                fix_result = apply_fix(
                    self.repo_path, relative_path,
                    original_code, fixed_code,
                    filtered_issues, dry_run=self.dry_run,
                )
                if not self.dry_run:
                    record_fixes(self.repo_path, relative_path, filtered_issues)
                    print(f"  ✅ Fixed and saved. Backup at {fix_result['backup']}")
                else:
                    print(f"  👁️  Dry run — no files written.")

        return {
            "file": relative_path,
            "language": lang,
            "truncated": truncated,
            "issues": filtered_issues,
            "issue_count": len(filtered_issues),
            "health_score": self._compute_score(filtered_issues),
            "fix_result": fix_result,
        }

    async def _call_claude(self, code: str, lang: str, file_path: str) -> list[dict]:
        loop = asyncio.get_event_loop()

        def _sync_call():
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=build_system_prompt(lang),
                messages=[
                    {"role": "user", "content": build_user_prompt(code, lang, file_path)}
                ],
            )
            return response.content[0].text

        try:
            raw = await loop.run_in_executor(None, _sync_call)
            # Strip markdown fences if present
            clean = raw.strip()
            if clean.startswith("```"):
                clean = "\n".join(clean.split("\n")[1:])
            if clean.endswith("```"):
                clean = "\n".join(clean.split("\n")[:-1])
            return json.loads(clean.strip())
        except json.JSONDecodeError:
            print(f"    ⚠️  Could not parse JSON response for {file_path}")
            return []
        except Exception as e:
            print(f"    ⚠️  Claude API error for {file_path}: {e}")
            return []

    async def _call_claude_fix(self, code: str, lang: str, file_path: str, issues: list) -> Optional[str]:
        """Ask Claude to rewrite the file with all issues fixed. Returns corrected source code."""
        loop = asyncio.get_event_loop()

        def _sync_call():
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": build_fix_prompt(code, lang, file_path, issues),
                }],
            )
            return response.content[0].text

        try:
            raw = await loop.run_in_executor(None, _sync_call)
            # Strip markdown fences if model wraps in them
            clean = raw.strip()
            if clean.startswith("```"):
                clean = "\n".join(clean.split("\n")[1:])
            if clean.endswith("```"):
                clean = "\n".join(clean.split("\n")[:-1])
            return clean.strip()
        except Exception as e:
            print(f"    ⚠️  Fix API error for {file_path}: {e}")
            return None

    def _compute_score(self, issues: list[dict]) -> int:
        """Compute a 0–100 health score. Higher = better."""
        total = sum(SCORE_DEDUCTIONS.get(i.get("severity", "info"), 1) for i in issues)
        return max(0, 100 - total)
