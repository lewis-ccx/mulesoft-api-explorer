#!/usr/bin/env python3
"""
Generate an HTML report for a MuleSoft API project.
Runs the analysis scripts internally and produces a self-contained HTML file.

Usage:
    python generate-report.py <project-root> [output.html]

If output.html is omitted, writes to <project-root>/target/mulesoft-report.html
"""

import subprocess
import sys
import json
import os
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent


def run_script(script_name: str, project_root: str) -> dict:
    """Run an analysis script and parse its JSON output."""
    script_path = SCRIPT_DIR / script_name
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), project_root],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout.strip()
        if output:
            return json.loads(output)
        return {}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        print(f"Warning: {script_name} failed: {e}", file=sys.stderr)
        return {}


def build_project_info(project_root: Path) -> dict:
    """Gather basic project metadata."""
    info = {
        'name': project_root.name,
        'path': str(project_root),
        'mule_version': None,
        'packaging': None,
        'java_version': None,
        'artifact_min_mule': None,
    }

    # pom.xml
    pom = project_root / 'pom.xml'
    if pom.exists():
        content = pom.read_text(errors='replace')
        import re
        m = re.search(r'<mule\.version>([^<]+)</mule\.version>', content)
        if m:
            info['mule_version'] = m.group(1)
        m = re.search(r'<packaging>([^<]+)</packaging>', content)
        if m:
            info['packaging'] = m.group(1)
        m = re.search(r'<java\.version>([^<]+)</java\.version>', content)
        if m:
            info['java_version'] = m.group(1)
        m = re.search(r'<maven\.compiler\.source>([^<]+)</maven\.compiler\.source>', content)
        if m:
            info['java_version'] = m.group(1)

    # mule-artifact.json
    artifact = project_root / 'mule-artifact.json'
    if artifact.exists():
        try:
            data = json.loads(artifact.read_text())
            info['artifact_min_mule'] = data.get('minMuleVersion')
        except json.JSONDecodeError:
            pass

    return info


def list_config_files(project_root: Path) -> list:
    """List all Mule XML config files."""
    mule_dir = project_root / 'src' / 'main' / 'mule'
    if not mule_dir.exists():
        return []
    files = []
    for f in mule_dir.rglob('*.xml'):
        files.append({
            'path': str(f.relative_to(project_root)),
            'size': f.stat().st_size,
        })
    return files


def list_property_files(project_root: Path) -> list:
    """List property files."""
    resources = project_root / 'src' / 'main' / 'resources'
    if not resources.exists():
        return []
    files = []
    for pattern in ['*.yaml', '*.yml', '*.properties', '*.yml']:
        for f in resources.rglob(pattern):
            files.append({
                'path': str(f.relative_to(project_root)),
                'size': f.stat().st_size,
            })
    # dedupe
    seen = set()
    unique = []
    for f in files:
        if f['path'] not in seen:
            seen.add(f['path'])
            unique.append(f)
    return unique


def render_html(project_info: dict, validation: dict, endpoints: dict,
                config_files: list, property_files: list, project_name: str) -> str:
    """Render the full HTML report."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Validation summary
    v_summary = validation.get('summary', {})
    v_issues = validation.get('issues', [])
    errors = [i for i in v_issues if i['level'] == 'error']
    warnings = [i for i in v_issues if i['level'] == 'warning']
    infos = [i for i in v_issues if i['level'] == 'info']

    # Endpoints
    ep_list = endpoints.get('endpoints', [])
    flows = endpoints.get('flows', [])
    schedulers = endpoints.get('schedulers', [])
    vm_queues = endpoints.get('vm_queues', [])

    http_listeners = [e for e in ep_list if e.get('type') == 'http-listener']
    apikit_routers = [e for e in ep_list if e.get('type') == 'apikit-router']
    apikit_flows = [f for f in flows if f.get('name', '').startswith(('get:', 'post:', 'put:', 'delete:', 'patch:'))]

    # Build issue rows
    def issue_rows(issues):
        rows = []
        for i in issues:
            level_cls = {'error': 'err', 'warning': 'warn', 'info': 'info'}.get(i['level'], 'info')
            icon = {'error': '&#10060;', 'warning': '&#9888;&#65039;', 'info': '&#8505;&#65039;'}.get(i['level'], '&#8505;&#65039;')
            file_col = f"<code>{i.get('file', '')}</code>" if i.get('file') else ''
            rows.append(f'<tr class="{level_cls}"><td>{icon}</td><td><code>{i["check"]}</code></td><td>{i["message"]}</td><td>{file_col}</td></tr>')
        return '\n'.join(rows)

    # Build endpoint table
    def endpoint_rows(items):
        rows = []
        for e in items:
            rows.append(
                f"<tr><td><code>{e.get('method', '*')}</code></td>"
                f"<td><code>{e.get('path', e.get('queue', e.get('config_ref', '')))}</code></td>"
                f"<td><code>{e.get('flow', '')}</code></td>"
                f"<td><code>{e.get('config_ref', '')}</code></td></tr>"
            )
        return '\n'.join(rows)

    # Flow table
    flow_rows = '\n'.join(
        f"<tr><td><span class='badge {'flow' if f['type']=='flow' else 'subflow'}'>{f['type']}</span></td>"
        f"<td><code>{f['name']}</code></td>"
        f"<td><code>{f.get('source_file', '')}</code></td></tr>"
        for f in flows
    )

    # Config files
    config_rows = '\n'.join(
        f"<tr><td><code>{c['path']}</code></td><td>{c['size']:,} B</td></tr>"
        for c in config_files
    )

    # Property files
    prop_rows = '\n'.join(
        f"<tr><td><code>{c['path']}</code></td><td>{c['size']:,} B</td></tr>"
        for c in property_files
    )

    # APIkit flow table
    apikit_flow_rows = '\n'.join(
        f"<tr><td><code>{f['name']}</code></td>"
        f"<td><code>{f.get('source_file', '')}</code></td></tr>"
        for f in apikit_flows
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MuleSoft Report — {project_name}</title>
<style>
:root {{
  --bg: #0d1117; --surface: #161b22; --border: #30363d;
  --fg: #e6edf3; --muted: #8b949e; --accent: #58a6ff;
  --green: #3fb950; --yellow: #d29922; --red: #f85149; --purple: #bc8cff;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg); color: var(--fg); line-height: 1.6; padding: 2rem;
}}
.container {{ max-width: 1100px; margin: 0 auto; }}
h1 {{ font-size: 1.8rem; margin-bottom: 0.3rem; }}
h2 {{ font-size: 1.3rem; margin: 2rem 0 1rem; color: var(--accent); border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }}
h3 {{ font-size: 1.1rem; margin: 1.2rem 0 0.6rem; color: var(--purple); }}
.subtitle {{ color: var(--muted); margin-bottom: 2rem; }}
.card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; padding: 1.2rem; margin: 0.8rem 0;
}}
.badge {{
  display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px;
  font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
}}
.badge.flow {{ background: #1f3a5f; color: #58a6ff; }}
.badge.subflow {{ background: #2d1f5f; color: #bc8cff; }}
.badge.err {{ background: #3d1418; color: #f85149; }}
.badge.warn {{ background: #3d2e14; color: #d29922; }}
.badge.info {{ background: #1a2e1a; color: #3fb950; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
th, td {{ padding: 0.5rem 0.7rem; text-align: left; border-bottom: 1px solid var(--border); }}
th {{ color: var(--muted); font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }}
tr.err td:first-child {{ color: var(--red); }}
tr.warn td:first-child {{ color: var(--yellow); }}
tr.info td:first-child {{ color: var(--green); }}
code {{
  background: #21262d; padding: 0.1rem 0.35rem; border-radius: 3px;
  font-family: 'Cascadia Code', 'Fira Code', monospace; font-size: 0.85em;
}}
.stats {{ display: flex; gap: 1rem; flex-wrap: wrap; margin: 1rem 0; }}
.stat {{
  flex: 1; min-width: 120px; background: var(--surface);
  border: 1px solid var(--border); border-radius: 8px;
  padding: 1rem; text-align: center;
}}
.stat .num {{ font-size: 2rem; font-weight: 700; }}
.stat .label {{ color: var(--muted); font-size: 0.8rem; text-transform: uppercase; }}
.stat.error .num {{ color: var(--red); }}
.stat.warning .num {{ color: var(--yellow); }}
.stat.info .num {{ color: var(--green); }}
.stat.total .num {{ color: var(--accent); }}
.meta-table td:first-child {{ color: var(--muted); width: 180px; }}
footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border); color: var(--muted); font-size: 0.8rem; }}
</style>
</head>
<body>
<div class="container">

<h1>&#128736; MuleSoft API Project Report</h1>
<p class="subtitle"><code>{project_name}</code> &mdash; generated {now}</p>

<!-- Summary Stats -->
<div class="stats">
  <div class="stat error"><div class="num">{len(errors)}</div><div class="label">Errors</div></div>
  <div class="stat warning"><div class="num">{len(warnings)}</div><div class="label">Warnings</div></div>
  <div class="stat info"><div class="num">{len(infos)}</div><div class="label">Info</div></div>
  <div class="stat total"><div class="num">{len(http_listeners) + len(apikit_routers)}</div><div class="label">HTTP Endpoints</div></div>
  <div class="stat total"><div class="num">{len(flows)}</div><div class="label">Flows</div></div>
  <div class="stat total"><div class="num">{len(schedulers)}</div><div class="label">Schedulers</div></div>
</div>

<!-- Project Info -->
<h2>Project Overview</h2>
<div class="card">
<table class="meta-table">
  <tr><td>Project Name</td><td><code>{project_info['name']}</code></td></tr>
  <tr><td>Path</td><td><code>{project_info['path']}</code></td></tr>
  <tr><td>Mule Version</td><td>{project_info.get('mule_version') or project_info.get('artifact_min_mule') or '<em>Not found in POM (check parent)</em>'}</td></tr>
  <tr><td>Packaging</td><td>{project_info.get('packaging') or 'N/A'}</td></tr>
  <tr><td>Java Version</td><td>{project_info.get('java_version') or 'N/A'}</td></tr>
  <tr><td>Min Mule (artifact)</td><td>{project_info.get('artifact_min_mule') or 'N/A'}</td></tr>
</table>
</div>

<!-- Validation -->
<h2>&#128737; Validation</h2>
<div class="card">
<table>
<thead><tr><th></th><th>Check</th><th>Message</th><th>File</th></tr></thead>
<tbody>
{issue_rows(v_issues)}
</tbody>
</table>
</div>

<!-- HTTP Endpoints -->
<h2>&#127760; HTTP Listeners</h2>
<div class="card">
{f'<table><thead><tr><th>Method</th><th>Path</th><th>Flow</th><th>Config</th></tr></thead><tbody>{endpoint_rows(http_listeners)}</tbody></table>' if http_listeners else '<p>No HTTP listeners found.</p>'}
</div>

<!-- APIkit -->
<h2>&#128203; APIkit Router</h2>
<div class="card">
{f'<table><thead><tr><th>Config Ref</th><th>Flow</th><th>Note</th></tr></thead><tbody>' + ''.join(f"<tr><td><code>{r.get('config_ref','')}</code></td><td><code>{r.get('flow','')}</code></td><td>{r.get('note','')}</td></tr>" for r in apikit_routers) + '</tbody></table>' if apikit_routers else '<p>No APIkit router found.</p>'}
</div>

{f'''
<h3>APIkit-Generated Flows ({len(apikit_flows)})</h3>
<div class="card">
<table><thead><tr><th>Flow Name</th><th>Source</th></tr></thead>
<tbody>{apikit_flow_rows}</tbody></table>
</div>
''' if apikit_flows else ''}

<!-- Flows -->
<h2>&#9889; Flows &amp; Sub-Flows</h2>
<div class="card">
<table><thead><tr><th>Type</th><th>Name</th><th>Source</th></tr></thead>
<tbody>{flow_rows}</tbody></table>
</div>

<!-- Schedulers -->
<h2>&#9200; Schedulers</h2>
<div class="card">
{('<table><thead><tr><th>Name</th><th>Cron</th><th>Frequency</th></tr></thead><tbody>' + ''.join(f"<tr><td><code>{s.get('name','')}</code></td><td><code>{s.get('cron_expression','')}</code></td><td><code>{s.get('frequency','')}</code></td></tr>" for s in schedulers) + '</tbody></table>') if schedulers else '<p>No schedulers found.</p>'}
</div>

<!-- VM Queues -->
{f'''
<h2>&#9889; VM Queues</h2>
<div class="card">
<table><thead><tr><th>Type</th><th>Queue</th><th>Config</th><th>Flow</th></tr></thead>
<tbody>{endpoint_rows(vm_queues)}</tbody></table>
</div>
''' if vm_queues else ''}

<!-- Config Files -->
<h2>&#128196; Mule Config Files</h2>
<div class="card">
<table><thead><tr><th>Path</th><th>Size</th></tr></thead>
<tbody>{config_rows}</tbody></table>
</div>

<!-- Property Files -->
<h2>&#9881; Property Files</h2>
<div class="card">
{('<table><thead><tr><th>Path</th><th>Size</th></tr></thead><tbody>' + prop_rows + '</tbody></table>') if property_files else '<p>No property files found.</p>'}
</div>

<footer>
Generated by <code>mulesoft-api-explorer</code> skill &mdash; {now}
</footer>
</div>
</body>
</html>"""
    return html


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate-report.py <project-root> [output.html]", file=sys.stderr)
        sys.exit(1)

    project_root = Path(sys.argv[1]).resolve()
    if not project_root.exists():
        print(f"Error: Project not found: {project_root}", file=sys.stderr)
        sys.exit(1)

    # Determine output path
    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    else:
        output_path = project_root / 'target' / 'mulesoft-report.html'
        output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Analyzing: {project_root}", file=sys.stderr)

    # Run analysis
    project_info = build_project_info(project_root)
    validation = run_script('validate-project.py', str(project_root))
    endpoints = run_script('extract-endpoints.py', str(project_root))

    config_files = list_config_files(project_root)
    property_files = list_property_files(project_root)

    # Generate HTML
    html = render_html(
        project_info, validation, endpoints,
        config_files, property_files, project_info['name']
    )

    output_path.write_text(html, encoding='utf-8')
    print(f"Report written: {output_path}", file=sys.stderr)
    print(str(output_path))


if __name__ == '__main__':
    main()
