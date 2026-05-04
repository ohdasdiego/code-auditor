# Code Auditor — AI-Powered Code Review

> AI auditing AI. Point it at any repo and get a structured code review anchored to official style guides — powered by Claude.

---

## Features

- **Multi-language support**: Python, Java, JavaScript, TypeScript
- **Official sources of truth**: PEP 8, Google Java Style Guide, Airbnb JS, and more
- **Spaghetti code detection**: God classes, deep nesting, magic numbers, SRP violations, DRY violations
- **Security flags**: Hardcoded secrets, SQL injection risks
- **Severity levels**: Critical / Warning / Info 
- **Health score**: 0–100 per file and repo average
- **Clean terminal output**: Colored, structured CLI report — no browser needed
- **Interactive fix mode**: Review all proposed fixes, apply by number, severity, or all at once
- **Auto-fix mode**: Claude rewrites files with all issues resolved
- **Dry-run mode**: Preview fixes as a unified diff before writing anything
- **Git diff mode**: Only audit what changed in the last commit
- **JSON export**: Machine-readable output for CI/CD integration
- **`.env` support**: Set your API key once, never export again

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/ohdasdiego/code-auditor.git
cd code-auditor
python3 -m venv venv
source venv/bin/activate # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set your API key (one time only)

```bash
cp .env.example .env
nano .env # paste your Anthropic API key
```

Get your key at: https://console.anthropic.com/

> The tool loads `.env` automatically — no `export` needed.

### 3. Run an audit

```bash
# Audit a repo (auto-detects languages)
python3 audit.py ./my-project

# Audit only Python files
python3 audit.py ./my-project --lang python

# Only audit files changed in last git commit
python3 audit.py ./my-project --diff

# Filter to only critical issues
python3 audit.py ./my-project --severity critical

# Interactive mode — review and pick which fixes to apply
python3 audit.py ./my-project --interactive

# Preview fixes as a diff (no files written)
python3 audit.py ./my-project --fix --dry-run

# Apply AI-generated fixes directly to source files
python3 audit.py ./my-project --fix

# Also export raw JSON results
python3 audit.py ./my-project --json

# Check version
python3 audit.py --version
```

### 4. Try the sample repo

```bash
python3 audit.py ./sample_repo
```

---

## CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `repo_path` | Path to repo or folder | required |
| `--lang` | Languages to audit: `python java javascript typescript` | auto-detect |
| `--diff` | Only audit git-changed files | false |
| `--severity` | Severity levels to show: `critical warning info` | all |
| `--max-files` | Max files to audit | 20 |
| `--interactive` | Review fixes and choose which to apply | false |
| `--fix` | Apply AI-generated fixes to source files | false |
| `--dry-run` | Preview fixes as a diff, no files written (use with `--fix`) | false |
| `--json` | Save raw JSON results to `audit_report.json` | false |
| `--model` | Override Claude model | `claude-sonnet-4-6` |
| `--version` | Show version and exit | — |

---

## Sample Output

```
Scanning sample_repo [auto-detect]

 Found 2 file(s) to audit...

────────────────────────────────────────────────────────────
 AI Code Audit Report 2026-04-21 04:25 UTC
────────────────────────────────────────────────────────────

 Repo Health Score: 0/100
 Files Reviewed: 2
 Total Issues: 51 17 critical 32 warnings 2 info

 utils/helpers.py
 Python · 35 issue(s) · Score: 0/100
 ──────────────────────────────────────────────────────────

 CRITICAL line 6 Hardcoded Secret
 API_KEY is hardcoded as a string literal in source code.
 Google Python Style Guide §Security / OWASP A02
 Use environment variables: API_KEY = os.environ.get('API_KEY')

 CRITICAL line 56 SQL Injection Vulnerability
 String concatenation used to build SQL query with user input.
 OWASP A03 / Google Python Style Guide §Security
 Use parameterized queries: cursor.execute('SELECT ...', (value,))

 ...

────────────────────────────────────────────────────────────
 17 critical issue(s) need attention.
────────────────────────────────────────────────────────────
```

### Interactive Fix Mode

```
────────────────────────────────────────────────────────────
 Fix Review — 17 proposed fix(es)
────────────────────────────────────────────────────────────

 [ 1] CRITICAL utils/helpers.py line 6
 Hardcoded Secret — API_KEY is hardcoded as a string literal...
 fix: API_KEY = os.environ.get('API_KEY')

 [ 2] CRITICAL utils/helpers.py line 56
 SQL Injection — String concatenation used to build SQL query...
 fix: cursor.execute('SELECT * FROM users WHERE id = ?', (uid,))
 ...

Which fixes do you want to apply?
 Enter numbers (e.g. 1,3,5)
 or 'all' - apply everything
 or 'critical' - apply all critical fixes
 or 'warning' - apply all warning fixes
 or 'none' - skip all

> critical
 Selected 11 critical fix(es).
 Fixing utils/helpers.py (8 issue(s))... Done
 Fixing models/order.py (3 issue(s))... Done
```

---

## Architecture

```
audit.py ← CLI entry point (argparse, .env auto-load, interactive mode)
src/
 auditor.py ← File discovery, async Claude API calls, scoring, fix orchestration
 prompts.py ← System/user/fix prompt templates per language
 fixer.py ← Applies fixes, dry-run diffs, .audit-state.json tracking
 languages.py ← Extension → language mapping
 reporter.py ← Colored terminal report output
sample_repo/ ← Intentionally bad code for demo
 utils/helpers.py
 models/order.py
.env.example ← API key template (copy to .env)
.audit-state.json ← Tracks fixed/accepted issues across runs (auto-generated)
```

---

## CI/CD Integration

Add to `.github/workflows/audit.yml`:

```yaml
- name: Run Code Audit
 run: |
 pip install -r requirements.txt
 python3 audit.py . --diff --severity critical --json
 env:
 ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

- name: Upload Audit Results
 uses: actions/upload-artifact@v3
 with:
 name: code-audit
 path: audit_report.json
```

---

## Roadmap

- [ ] Multi-provider support (OpenAI, Gemini, local models via Ollama)
- [ ] Java support (JavaParser AST)
- [ ] Cross-file analysis (duplicate logic detection)
- [ ] VS Code extension
- [ ] GitHub PR comment integration

---

## Sources of Truth

| Language | Guide |
|----------|-------|
| Python | [PEP 8](https://peps.python.org/pep-0008/), [PEP 20](https://peps.python.org/pep-0020/), [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) |
| Java | [Google Java Style Guide](https://google.github.io/styleguide/javaguide.html), Effective Java |
| JavaScript | [Airbnb Style Guide](https://github.com/airbnb/javascript), MDN Best Practices |
| TypeScript | [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/), Airbnb TS |

---

## Cost Analysis

Each file makes two API calls: one for the audit, one for fixes (if requested).

**Default model:** `claude-sonnet-4-6` ($3.00/M input · $15.00/M output tokens)

| Files audited | Mode | Est. cost |
|---|---|---|
| 5 | audit only | ~$0.02 |
| 20 | audit only | ~$0.09 |
| 50 | audit only | ~$0.22 |
| 5 | audit + fix all | ~$0.05 |
| 20 | audit + fix all | ~$0.18 |
| 50 | audit + fix all | ~$0.45 |

**Cost-saving options:**
- Use `--model claude-haiku-4-5` for ~6× cheaper runs (slightly less precise)
- Use `--diff` to only audit changed files in CI/CD
- Use `--interactive` to fix only what matters — skip issues you don't care about
- Use `--max-files` to cap spend on large repos

> A typical 20-file audit-only run costs under $0.10.

---

## ADOStack

| # | Project | Live | Role |
|---|---------|------|------|
| 1 | [AI Infra Monitor](https://github.com/ohdasdiego/ai-infra-monitor) | [monitor.ado-runner.com](https://monitor.ado-runner.com) | Metric collection + AI health analysis |
| 2 | [AI Incident Logger](https://github.com/ohdasdiego/ai-incident-logger) | [incidents.ado-runner.com](https://incidents.ado-runner.com) | Threshold alerting + incident records |
| **3** | **Code Auditor** | **CLI** | **← You are here** |
| 4 | [RAG Runbook Assistant](https://github.com/ohdasdiego/rag-runbook-assistant) | [runbooks.ado-runner.com](https://runbooks.ado-runner.com) | Vector search over IT runbooks |
| 5 | [K8s Event Summarizer](https://github.com/ohdasdiego/k8s-event-summarizer) | [k8s.ado-runner.com](https://k8s.ado-runner.com) | Kubernetes cluster health digests |
| 6 | [AI Incident Orchestrator](https://github.com/ohdasdiego/ai-incident-orchestrator) | [orchestrator.ado-runner.com](https://orchestrator.ado-runner.com) | Multi-agent triage pipeline |
| 7 | [On-Call Assistant](https://github.com/ohdasdiego/oncall-assistant) | [oncall.ado-runner.com](https://oncall.ado-runner.com) | Incident response + escalation routing |

---

## Author

**Diego Perez** · [github.com/ohdasdiego](https://github.com/ohdasdiego)

Integrates the [Anthropic Claude API](https://docs.anthropic.com) for AI-powered code analysis.
