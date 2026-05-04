"""
CodeAuditor — orchestrates file discovery, async Claude API calls,
and coordinates all three audit passes (style, fingerprint, humanize).
"""

import asyncio
import json
import os
import subprocess
from pathlib import Path

import anthropic

from src.languages import EXTENSION_MAP, LANGUAGE_EXTENSIONS, SKIP_DIRS, detect_language
from src.prompts import (
    get_style_prompts,
    get_fingerprint_prompts,
    get_humanize_prompts,
    get_fix_prompts,
)

DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_FILE_CHARS = 12_000  # truncate very large files to keep costs sane


class CodeAuditor:
    def __init__(
        self,
        repo_path: Path,
        languages: list[str] | None = None,
        diff_only: bool = False,
        severity_filter: list[str] | None = None,
        max_files: int = 20,
        model: str | None = None,
        fix: bool = False,
        dry_run: bool = False,
        passes: list[str] | None = None,
    ):
        self.repo_path = repo_path
        self.languages = languages
        self.diff_only = diff_only
        self.severity_filter = set(severity_filter or ["critical", "warning", "info"])
        self.max_files = max_files
        self.model = model or os.environ.get("CLAUDE_MODEL", DEFAULT_MODEL)
        self.fix = fix
        self.dry_run = dry_run
        # passes controls which audit passes run; default is both style + fingerprint
        self.passes = set(passes or ["style", "fingerprint"])
        self._client = anthropic.AsyncAnthropic()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run(self) -> list[dict]:
        files = self._discover_files()
        if not files:
            return []

        print(f"  Found {len(files)} file(s) to audit...\n")
        semaphore = asyncio.Semaphore(5)  # max concurrent API calls

        async def audit_one(f):
            async with semaphore:
                return await self._audit_file(f)

        results = await asyncio.gather(*[audit_one(f) for f in files])
        return [r for r in results if r]

    # ------------------------------------------------------------------
    # File discovery
    # ------------------------------------------------------------------

    def _discover_files(self) -> list[Path]:
        if self.diff_only:
            return self._git_changed_files()

        target_exts: set[str] = set()
        if self.languages:
            for lang in self.languages:
                target_exts.update(LANGUAGE_EXTENSIONS.get(lang, []))
        else:
            target_exts = set(EXTENSION_MAP.keys())

        found = []
        for path in sorted(self.repo_path.rglob("*")):
            if any(skip in path.parts for skip in SKIP_DIRS):
                continue
            if path.suffix.lower() in target_exts and path.is_file():
                found.append(path)
            if len(found) >= self.max_files:
                break

        return found

    def _git_changed_files(self) -> list[Path]:
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            paths = []
            for line in result.stdout.strip().splitlines():
                p = self.repo_path / line.strip()
                if p.exists() and detect_language(p):
                    paths.append(p)
            return paths[: self.max_files]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Per-file audit orchestration
    # ------------------------------------------------------------------

    async def _audit_file(self, path: Path) -> dict | None:
        language = detect_language(path)
        if not language:
            return None

        try:
            code = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

        if len(code) > MAX_FILE_CHARS:
            code = code[:MAX_FILE_CHARS] + "\n# ... [truncated for audit]"

        rel_path = str(path.relative_to(self.repo_path))
        all_issues: list[dict] = []
        scores: list[int] = []
        pass_summaries: dict[str, str] = {}

        # --- Style pass ---
        if "style" in self.passes:
            style_result = await self._call_claude_audit(
                *get_style_prompts(language, rel_path, code)
            )
            if style_result:
                filtered = self._filter_severity(style_result.get("issues", []))
                all_issues.extend(self._tag_issues(filtered, "style"))
                if (s := style_result.get("score")) is not None:
                    scores.append(s)
                if summary := style_result.get("summary"):
                    pass_summaries["style"] = summary

        # --- Fingerprint pass ---
        if "fingerprint" in self.passes:
            fp_result = await self._call_claude_audit(
                *get_fingerprint_prompts(rel_path, language, code)
            )
            if fp_result:
                filtered = self._filter_severity(fp_result.get("issues", []))
                all_issues.extend(self._tag_issues(filtered, "fingerprint"))
                if (s := fp_result.get("score")) is not None:
                    scores.append(s)
                if summary := fp_result.get("summary"):
                    pass_summaries["fingerprint"] = summary

        score = round(sum(scores) / len(scores)) if scores else 0

        return {
            "file": rel_path,
            "language": language,
            "issues": all_issues,
            "score": score,
            "pass_summaries": pass_summaries,
            "code": code,
        }

    # ------------------------------------------------------------------
    # Claude API calls
    # ------------------------------------------------------------------

    async def _call_claude_audit(self, system: str, user: str) -> dict | None:
        try:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            raw = response.content[0].text.strip()
            # strip accidental markdown fences
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw)
        except (json.JSONDecodeError, IndexError, anthropic.APIError) as e:
            print(f"    [warn] Claude API error: {e}")
            return None

    async def _call_claude_humanize(self, code: str, language: str, filename: str) -> str | None:
        system, user = get_humanize_prompts(filename, language, code)
        try:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            result = response.content[0].text.strip()
            # strip accidental markdown fences
            if result.startswith("```"):
                lines = result.splitlines()
                result = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])
            return result
        except anthropic.APIError as e:
            print(f"    [warn] Humanize API error: {e}")
            return None

    async def _call_claude_fix(
        self, code: str, language: str, filename: str, issues: list
    ) -> str | None:
        system, user = get_fix_prompts(filename, language, code, issues)
        try:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            result = response.content[0].text.strip()
            if result.startswith("```"):
                lines = result.splitlines()
                result = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])
            return result
        except anthropic.APIError as e:
            print(f"    [warn] Fix API error: {e}")
            return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _filter_severity(self, issues: list) -> list:
        return [i for i in issues if i.get("severity") in self.severity_filter]

    @staticmethod
    def _tag_issues(issues: list, pass_name: str) -> list:
        for issue in issues:
            issue["pass"] = pass_name
        return issues
