"""
Report generator — produces a styled HTML dashboard and optional JSON output.
"""

import json
from pathlib import Path
from datetime import datetime


SEVERITY_COLORS = {
    "critical": ("#ff4444", "rgba(255,68,68,0.12)", "🔴"),
    "warning":  ("#f5a623", "rgba(245,166,35,0.12)", "🟡"),
    "info":     ("#4a90e2", "rgba(74,144,226,0.12)", "🔵"),
}


def generate_report(results: list[dict], output_path: Path, save_json: bool = False):
    if save_json:
        json_path = output_path.with_suffix(".json")
        json_path.write_text(json.dumps(results, indent=2))
        print(f"   📦 JSON saved: {json_path.resolve()}")

    html = _build_html(results)
    output_path.write_text(html, encoding="utf-8")


def _build_html(results: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_files = len(results)
    all_issues = [i for r in results for i in r.get("issues", [])]
    total_issues = len(all_issues)
    critical_count = sum(1 for i in all_issues if i.get("severity") == "critical")
    warning_count = sum(1 for i in all_issues if i.get("severity") == "warning")
    info_count = sum(1 for i in all_issues if i.get("severity") == "info")

    avg_score = (
        round(sum(r.get("health_score", 100) for r in results) / total_files)
        if total_files else 100
    )

    score_color = "#27ae60" if avg_score >= 80 else "#f5a623" if avg_score >= 50 else "#ff4444"

    files_html = "\n".join(_render_file(r) for r in results)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Code Audit Report — {now}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #0f1117; color: #e0e0e0; line-height: 1.6; }}
  .header {{ background: linear-gradient(135deg, #1a1d2e 0%, #2d1b69 100%);
             padding: 40px; border-bottom: 2px solid #6c63ff; }}
  .header h1 {{ font-size: 2rem; color: #fff; }}
  .header .subtitle {{ color: #aaa; margin-top: 4px; }}
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 16px; padding: 32px 40px; background: #16192a; }}
  .stat-card {{ background: #1e2236; border-radius: 12px; padding: 20px;
                border-left: 4px solid #6c63ff; }}
  .stat-card .label {{ font-size: 0.75rem; color: #888; text-transform: uppercase;
                       letter-spacing: 0.05em; }}
  .stat-card .value {{ font-size: 2rem; font-weight: 700; margin-top: 4px; }}
  .score-ring {{ color: {score_color}; }}
  .critical-val {{ color: #ff4444; }}
  .warning-val {{ color: #f5a623; }}
  .info-val {{ color: #4a90e2; }}
  .files {{ padding: 32px 40px; max-width: 1400px; }}
  .file-card {{ background: #1e2236; border-radius: 12px; margin-bottom: 24px;
                border: 1px solid #2a2d45; overflow: hidden; }}
  .file-header {{ padding: 16px 20px; background: #252840;
                  display: flex; justify-content: space-between; align-items: center;
                  cursor: pointer; user-select: none; }}
  .file-header:hover {{ background: #2d3058; }}
  .file-title {{ font-family: 'Courier New', monospace; font-size: 0.9rem; color: #c9c9ff; }}
  .file-meta {{ font-size: 0.8rem; color: #888; }}
  .file-score {{ font-weight: 700; font-size: 1.1rem; }}
  .issues-list {{ padding: 0; }}
  .issue {{ padding: 16px 20px; border-top: 1px solid #2a2d45; }}
  .issue-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }}
  .badge {{ padding: 2px 8px; border-radius: 20px; font-size: 0.72rem;
            font-weight: 600; text-transform: uppercase; }}
  .rule-name {{ font-family: 'Courier New', monospace; font-size: 0.82rem;
                color: #c9c9ff; background: #252840; padding: 2px 8px; border-radius: 4px; }}
  .line-ref {{ font-size: 0.8rem; color: #888; }}
  .description {{ color: #ccc; font-size: 0.9rem; margin: 4px 0; }}
  .source-cite {{ font-size: 0.78rem; color: #888; font-style: italic; margin: 4px 0; }}
  .suggestion {{ background: #0d1f0d; border-left: 3px solid #27ae60; padding: 10px 14px;
                 border-radius: 0 6px 6px 0; margin-top: 8px; font-size: 0.85rem; color: #a8e6a8;
                 font-family: 'Courier New', monospace; white-space: pre-wrap; }}
  .no-issues {{ padding: 24px 20px; text-align: center; color: #27ae60; }}
  .toggle-icon {{ transition: transform 0.2s; }}
  .collapsed .toggle-icon {{ transform: rotate(-90deg); }}
  footer {{ text-align: center; padding: 32px; color: #555; font-size: 0.8rem; }}
</style>
</head>
<body>

<div class="header">
  <h1>🔍 AI Code Audit Report</h1>
  <div class="subtitle">Generated {now} · Powered by Claude API</div>
</div>

<div class="stats">
  <div class="stat-card">
    <div class="label">Repo Health Score</div>
    <div class="value score-ring">{avg_score}/100</div>
  </div>
  <div class="stat-card">
    <div class="label">Files Reviewed</div>
    <div class="value">{total_files}</div>
  </div>
  <div class="stat-card">
    <div class="label">Total Issues</div>
    <div class="value">{total_issues}</div>
  </div>
  <div class="stat-card">
    <div class="label">🔴 Critical</div>
    <div class="value critical-val">{critical_count}</div>
  </div>
  <div class="stat-card">
    <div class="label">🟡 Warnings</div>
    <div class="value warning-val">{warning_count}</div>
  </div>
  <div class="stat-card">
    <div class="label">🔵 Info</div>
    <div class="value info-val">{info_count}</div>
  </div>
</div>

<div class="files">
  <h2 style="margin-bottom:20px; color:#aaa; font-weight:400;">File Details</h2>
  {files_html}
</div>

<footer>Code Auditor · AI-powered static analysis · Claude API</footer>

<script>
document.querySelectorAll('.file-header').forEach(h => {{
  h.addEventListener('click', () => {{
    h.parentElement.classList.toggle('collapsed');
    const list = h.parentElement.querySelector('.issues-list');
    list.style.display = list.style.display === 'none' ? '' : 'none';
  }});
}});
</script>
</body>
</html>"""


def _render_file(result: dict) -> str:
    issues = result.get("issues", [])
    score = result.get("health_score", 100)
    score_color = "#27ae60" if score >= 80 else "#f5a623" if score >= 50 else "#ff4444"
    truncated_note = " <span style='color:#f5a623'>(truncated)</span>" if result.get("truncated") else ""

    issues_html = ""
    if not issues:
        issues_html = '<div class="no-issues">✅ No issues found</div>'
    else:
        for issue in issues:
            sev = issue.get("severity", "info")
            color, bg, icon = SEVERITY_COLORS.get(sev, ("#888", "#f9f9f9", "⚪"))
            line_text = f"Line {issue['line']}" if issue.get("line") else "—"
            suggestion = issue.get("suggestion", "").strip()
            suggestion_html = (
                f'<div class="suggestion">{_escape(suggestion)}</div>'
                if suggestion else ""
            )
            issues_html += f"""
<div class="issue">
  <div class="issue-header">
    <span class="badge" style="background:{bg};color:{color};">{icon} {sev}</span>
    <span class="rule-name">{_escape(issue.get("rule", ""))}</span>
    <span class="line-ref">{line_text}</span>
  </div>
  <div class="description">{_escape(issue.get("description", ""))}</div>
  <div class="source-cite">📖 {_escape(issue.get("source", ""))}</div>
  {suggestion_html}
</div>"""

    fix_result = result.get("fix_result")
    fix_banner = ""
    if fix_result:
        if fix_result["status"] == "applied":
            fix_banner = f'<div style="padding:10px 20px;background:rgba(39,174,96,0.1);border-top:1px solid #2a2d45;font-size:0.8rem;color:#27ae60;">✅ {fix_result["issues_fixed"]} issue(s) fixed — backup saved at {_escape(fix_result["backup"])}</div>'
        elif fix_result["status"] == "dry-run" and fix_result.get("diff"):
            escaped_diff = _escape(fix_result["diff"])
            fix_banner = f'<div style="padding:12px 20px;background:#0a1a0a;border-top:1px solid #2a2d45;"><div style="font-size:0.75rem;color:#27ae60;margin-bottom:6px;">👁 DRY RUN DIFF</div><pre style="font-size:0.75rem;color:#a8e6a8;white-space:pre-wrap;overflow-x:auto;">{escaped_diff}</pre></div>'

    return f"""
<div class="file-card">
  <div class="file-header">
    <span class="file-title">📄 {_escape(result['file'])}{truncated_note}</span>
    <span style="display:flex;gap:12px;align-items:center;">
      <span class="file-meta">{result.get('language','').capitalize()} · {len(issues)} issue(s)</span>
      <span class="file-score" style="color:{score_color}">{score}/100</span>
      <span class="toggle-icon">▼</span>
    </span>
  </div>
  <div class="issues-list">{issues_html}</div>
  {fix_banner}
</div>"""


def _escape(text: str) -> str:
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))
