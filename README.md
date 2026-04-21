# 🔍 Code Auditor — AI-Powered Code Review

> AI auditing AI. Point it at any repo and get a structured code review anchored to official style guides — powered by Claude.

---

## ✨ Features

- **Multi-language support**: Python, Java, JavaScript, TypeScript
- **Official sources of truth**: PEP 8, Google Java Style Guide, Airbnb JS, and more
- **Spaghetti code detection**: God classes, deep nesting, magic numbers, SRP violations, DRY violations
- **Security flags**: Hardcoded secrets, SQL injection risks
- **Severity levels**: Critical 🔴 / Warning 🟡 / Info 🔵
- **Health score**: 0–100 per file and repo average
- **Clean terminal output**: Colored, structured CLI report — no browser needed
- **Git diff mode**: Only audit what changed in the last commit
- **JSON export**: Machine-readable output for CI/CD integration (`--json`)

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your API key

```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

### 3. Run an audit

```bash
# Audit a repo (auto-detects languages)
python audit.py ./my-project

# Audit only Python files
python audit.py ./my-project --lang python

# Only audit files changed in last git commit
python audit.py ./my-project --diff

# Filter to only critical issues
python audit.py ./my-project --severity critical

# Preview fixes as a diff (no files written)
python audit.py ./my-project --fix --dry-run

# Apply AI-generated fixes directly to source files
python audit.py ./my-project --fix

# Also export raw JSON results
python audit.py ./my-project --json
```

### 4. Try the sample repo

```bash
python audit.py ./sample_repo
```

---

## 📋 CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `repo_path` | Path to repo or folder | required |
| `--lang` | Languages to audit: `python java javascript typescript` | auto-detect |
| `--diff` | Only audit git-changed files | false |
| `--severity` | Severity levels to show: `critical warning info` | all |
| `--max-files` | Max files to audit | 20 |
| `--json` | Save raw JSON results to `audit_report.json` | false |
| `--model` | Override Claude model | `claude-sonnet-4-6` |
| `--fix` | Apply AI-generated fixes to source files | false |
| `--dry-run` | Preview fixes as a diff, no files written (use with `--fix`) | false |

---

## 📊 Sample Output

```
🔍 Scanning sample_repo  [auto-detect]

📂 Found 2 file(s) to audit...

────────────────────────────────────────────────────────────
  🔍 AI Code Audit Report  2026-04-21 04:25 UTC
────────────────────────────────────────────────────────────

  Repo Health Score:  0/100
  Files Reviewed:     2
  Total Issues:       51  17 critical  32 warnings  2 info

  📄 utils/helpers.py
  Python · 35 issue(s) · Score: 0/100
  ──────────────────────────────────────────────────────────

  🔴 CRITICAL  line 6   Hardcoded Secret
  API_KEY is hardcoded as a string literal in source code.
  📖 Google Python Style Guide §Security / OWASP A02
  💡 Use environment variables: API_KEY = os.environ.get('API_KEY')

  🔴 CRITICAL  line 56  SQL Injection Vulnerability
  String concatenation used to build SQL query with user input.
  📖 OWASP A03 / Google Python Style Guide §Security
  💡 Use parameterized queries: cursor.execute('SELECT ...', (value,))

  ...

────────────────────────────────────────────────────────────
  ⚠  17 critical issue(s) need attention.
────────────────────────────────────────────────────────────
```

Output includes per-file:
- **Repo health score** (0–100 aggregate)
- **Per-file health scores**
- **Issue cards** with:
  - Severity badge (🔴 Critical / 🟡 Warning / 🔵 Info)
  - Rule name (e.g., `PEP8-E501`, `God Function`, `SQL Injection`)
  - Official guide citation (e.g., `PEP 8 §Naming Conventions`)
  - Description of what's wrong and why
  - Concrete suggestion or refactored snippet

---

## 🏗️ Architecture

```
audit.py              ← CLI entry point (argparse)
src/
  auditor.py          ← File discovery, async Claude API calls, scoring, fix orchestration
  prompts.py          ← System/user/fix prompt templates per language
  fixer.py            ← Applies fixes, dry-run diffs, .audit-state.json tracking
  languages.py        ← Extension → language mapping
  reporter.py         ← HTML + JSON report generation (includes fix diffs)
sample_repo/          ← Intentionally bad code for demo
  utils/helpers.py
  models/order.py
.audit-state.json     ← Tracks fixed/accepted issues across runs (auto-generated)
```

---

## 🔧 CI/CD Integration

Add to `.github/workflows/audit.yml`:

```yaml
- name: Run Code Audit
  run: |
    pip install -r requirements.txt
    python audit.py . --diff --severity critical --output audit.html
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

- name: Upload Audit Report
  uses: actions/upload-artifact@v3
  with:
    name: code-audit
    path: audit.html
```

---

## 🗺️ Roadmap

- [x] `--fix` mode: Claude rewrites files with all issues resolved
- [x] `--dry-run`: preview fixes as a unified diff before applying
- [x] `.audit-state.json`: tracks applied fixes, skips re-flagging on future runs
- [ ] Interactive mode: review each fix one at a time before applying
- [ ] Java support (JavaParser AST)
- [ ] Cross-file analysis (duplicate logic detection)
- [ ] VS Code extension
- [ ] GitHub PR comment integration

---

## 📚 Sources of Truth

| Language | Guide |
|----------|-------|
| Python | [PEP 8](https://peps.python.org/pep-0008/), [PEP 20](https://peps.python.org/pep-0020/), [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) |
| Java | [Google Java Style Guide](https://google.github.io/styleguide/javaguide.html), Effective Java |
| JavaScript | [Airbnb Style Guide](https://github.com/airbnb/javascript), MDN Best Practices |
| TypeScript | [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/), Airbnb TS |

---

---

## 💰 Cost Analysis

Audit cost depends on file count and size. Each file makes one API call.

Default model: `claude-sonnet-4-6` ($3.00/M input tokens, $15.00/M output tokens)

| Files audited | Avg tokens/file | Est. cost |
|---|---|---|
| 5 | ~1,500 in / ~500 out | ~$0.03 |
| 20 | ~1,500 in / ~500 out | ~$0.12 |
| 50 | ~1,500 in / ~500 out | ~$0.30 |

**Cost-saving options:**
- Use `--model claude-haiku-4-5` for faster, cheaper runs (~6× cheaper, slightly less precise)
- Use `--diff` to only audit changed files in CI/CD
- Use `--max-files` to cap spend on large repos

> Per-run cost on a typical 20-file project is well under $0.25.

---

## 👤 Author

**Diego Perez** · [github.com/ohdasdiego](https://github.com/ohdasdiego)

Built with ❤️ using [Anthropic Claude API](https://docs.anthropic.com)
