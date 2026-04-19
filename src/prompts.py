"""
Prompt engineering for the code auditor.
Each language gets a tailored system prompt referencing its official style guide.
"""

LANGUAGE_GUIDES = {
    "python": "PEP 8 (https://peps.python.org/pep-0008/), PEP 20 (The Zen of Python), and Google Python Style Guide",
    "java": "Google Java Style Guide (https://google.github.io/styleguide/javaguide.html) and Effective Java (Joshua Bloch)",
    "javascript": "Airbnb JavaScript Style Guide and MDN Web Docs best practices",
    "typescript": "TypeScript official guidelines, Airbnb TypeScript Style Guide, and strict type-safety practices",
}

SEVERITY_DESCRIPTIONS = """
- "critical": Serious structural or logic problem that will cause bugs, security issues, or is a major violation of the style guide
- "warning": Code smell, anti-pattern, or moderate style violation that should be fixed
- "info": Minor suggestion, refactor opportunity, or best-practice note
"""

JSON_SCHEMA = """
Return ONLY a valid JSON array (no markdown, no preamble). Each element must be:
{
  "line": <integer or null>,
  "severity": "critical" | "warning" | "info",
  "rule": "<short rule name, e.g. 'PEP8-E501' or 'God Function'>",
  "source": "<official guide citation, e.g. 'PEP 8 §Maximum Line Length'>",
  "description": "<what is wrong and why it matters>",
  "suggestion": "<concrete fix or refactored snippet>"
}
"""


def build_system_prompt(language: str) -> str:
    guides = LANGUAGE_GUIDES.get(language, "general software engineering best practices")
    return f"""You are a senior software engineer conducting a rigorous code review.
Your role is to identify "spaghetti code" and violations of official coding standards.

Your sources of truth are: {guides}.

Severity levels:
{SEVERITY_DESCRIPTIONS}

You focus on:
1. Functions/methods doing too many things (Single Responsibility Principle)
2. Deep nesting (> 3 levels)
3. Magic numbers and strings
4. Long functions (> 40 lines)
5. God classes / modules
6. Poor naming (non-descriptive variables, Hungarian notation)
7. Missing error handling
8. Dead code / commented-out code
9. Duplicate logic (DRY violations)
10. Security anti-patterns (SQL injection risks, hardcoded secrets, etc.)
11. Style guide violations specific to {language}

For each issue, cite the specific rule or section from the official style guide.
Be precise, actionable, and educational. Do not flag trivial issues.

{JSON_SCHEMA}

If there are no issues, return an empty array: []
"""


def build_user_prompt(code: str, language: str, file_path: str) -> str:
    return f"""Please audit the following {language} file.

File path: {file_path}

```{language}
{code}
```

Identify all issues according to your instructions. Return only the JSON array.
"""


def build_fix_prompt(code: str, language: str, file_path: str, issues: list) -> str:
    """Prompt that asks Claude to rewrite the file with all issues fixed."""
    issues_summary = "\n".join(
        f"- Line {i.get('line', '?')} [{i['severity'].upper()}] {i['rule']}: {i['description']}"
        for i in issues
    )
    return f"""You are a senior software engineer. The following {language} file has been audited and has these issues:

{issues_summary}

Here is the original file ({file_path}):

```{language}
{code}
```

Rewrite the ENTIRE file with all issues fixed. Apply every fix precisely.
Do not remove any functionality. Do not add new features.
Return ONLY the corrected source code — no markdown fences, no explanation, no preamble.
"""
