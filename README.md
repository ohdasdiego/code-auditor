# Code Auditor v2

AI-powered code review CLI. Points at any repo and runs three distinct passes — powered by Claude.

---

## What's new in v2

**Fingerprint pass** — dedicated AI-tell detection. Catches the patterns that mark code as machine-generated:

- Emojis anywhere in code, comments, docstrings, or strings
- Comments that narrate the obvious (`# loop through items`, `# return the result`)
- Generic AI-favorite names (`processData`, `handleEvent`, `executeOperation`, `manageState`)
- Over-structured docstrings with Args/Returns/Raises on trivial private functions
- `TODO: add error handling` deferrals
- Defensive `try/except` around infallible operations
- Alphabetically sorted imports
- Placeholder `print("Starting...")` / `print("Done!")` noise
- Symmetrical naming patterns no human writes naturally
- `if __name__ == "__main__"` guards on non-script files

**Humanize pass** — full naturalizing rewrite. Doesn't just flag issues, rewrites the file so it reads like a working developer wrote it.

**Pass-aware interactive mode** — filter fixes by `fingerprint` or `style` separately.

---

## Audit passes

| Pass | What it finds |
|---|---|
| `style` | Security issues, structural problems, style guide violations |
| `fingerprint` | AI-generated code tells — emojis, generic names, narrator comments |
| `humanize` | Rewrites files to remove all AI fingerprints (not just flags them) |

---

## Quick start

```bash
git clone https://github.com/ohdasdiego/code-auditor.git
cd code-auditor
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# paste your Anthropic API key into .env

# Try the sample repo
python3 audit.py ./sample_repo
```

---

## Usage

```bash
# Default: style + fingerprint passes
python3 audit.py ./my-project

# Fingerprint pass only
python3 audit.py ./my-project --fingerprint

# Rewrite files to remove AI tells (preview first)
python3 audit.py ./my-project --humanize --dry-run
python3 audit.py ./my-project --humanize

# Style pass only, apply fixes interactively
python3 audit.py ./my-project --pass style --interactive

# Only changed files, critical issues, export JSON
python3 audit.py ./my-project --diff --severity critical --json

# Specific language, cheaper model
python3 audit.py ./my-project --lang python --model claude-haiku-4-5
```

---

## CLI reference

| Flag | Description | Default |
|---|---|---|
| `repo_path` | Path to repo or folder | required |
| `--pass` | Passes to run: `style` `fingerprint` | `style fingerprint` |
| `--fingerprint` | Shorthand: fingerprint pass only | — |
| `--humanize` | Rewrite files to remove AI tells | false |
| `--lang` | Languages: `python java javascript typescript` | auto-detect |
| `--diff` | Only audit git-changed files | false |
| `--severity` | Levels: `critical warning info` | all |
| `--max-files` | Cap files audited | 20 |
| `--fix` | Apply AI fixes to source files | false |
| `--dry-run` | Preview as diff, no writes | false |
| `--interactive` | Pick fixes by number, severity, or pass | false |
| `--json` | Save results to `audit_report.json` | false |
| `--model` | Override Claude model | `claude-sonnet-4-6` |

---

## Architecture

```
audit.py              CLI entry point — argparse, mode routing, interactive/humanize loops
src/
  auditor.py          File discovery, async Claude API calls, pass orchestration
  prompts.py          System/user prompt templates for all three passes
  fixer.py            apply_fix, apply_humanize, dry-run diffs, state tracking
  languages.py        Extension → language mapping, skip dirs
  reporter.py         Colored terminal output, pass-aware rendering
sample_repo/          Intentionally bad code with AI tells for demo
  utils/helpers.py
  models/order.py
.env.example          API key template
```

---

## Cost

**Default model:** `claude-sonnet-4-6`

| Files | Mode | Est. cost |
|---|---|---|
| 5 | audit only | ~$0.02 |
| 20 | audit only | ~$0.10 |
| 20 | audit + humanize | ~$0.20 |
| 50 | audit only | ~$0.25 |

Use `--model claude-haiku-4-5` for ~6× cheaper runs. Use `--diff` to cap spend in CI/CD.

---

## CI/CD integration

```yaml
- name: Run fingerprint check
  run: |
    pip install -r requirements.txt
    python3 audit.py . --fingerprint --severity warning --json
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

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
