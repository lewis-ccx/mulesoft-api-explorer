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
import re
from html import escape
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


def parse_properties_file(path: Path) -> dict:
    """Read scalar values from a YAML mapping or Java properties file."""
    values = {}
    if path.suffix == '.properties':
        for line in path.read_text(encoding='utf-8-sig', errors='replace').splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(('#', '!')):
                continue
            key, separator, value = stripped.partition('=')
            if not separator:
                key, separator, value = stripped.partition(':')
            if separator:
                values[key.strip()] = value.strip()
        return values

    parents = []
    for line in path.read_text(encoding='utf-8-sig', errors='replace').splitlines():
        if not line.strip() or line.lstrip().startswith('#') or line.strip() in ('---', '...'):
            continue

        indent = len(line) - len(line.lstrip(' '))
        content = line.strip()
        quote = None
        separator_index = None
        for index, character in enumerate(content):
            if character in ("'", '"'):
                quote = None if quote == character else character if quote is None else quote
            elif character == ':' and quote is None:
                separator_index = index
                break
        if separator_index is None:
            continue

        key = content[:separator_index].strip().strip("'\"")
        value = content[separator_index + 1:].strip()
        while parents and parents[-1][0] >= indent:
            parents.pop()

        if not value:
            parents.append((indent, key))
            continue

        value_quote = None
        for index, character in enumerate(value):
            if character in ("'", '"'):
                value_quote = None if value_quote == character else character if value_quote is None else value_quote
            elif character == '#' and value_quote is None and (index == 0 or value[index - 1].isspace()):
                value = value[:index].rstrip()
                break
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values['.'.join([parent for _, parent in parents] + [key])] = value
    return values


def load_environment_properties(project_root: Path) -> list:
    """Load common properties and environment overrides from resources/properties."""
    properties_dir = project_root / 'src' / 'main' / 'resources' / 'properties'
    if not properties_dir.exists():
        return [('default', {})]

    files = sorted(
        path for path in properties_dir.rglob('*')
        if path.is_file() and path.suffix.lower() in ('.yaml', '.yml', '.properties')
    )
    common = {}
    for path in files:
        if path.stem.lower() == 'common':
            common.update(parse_properties_file(path))

    environment_files = [
        path for path in files
        if path.stem.lower() not in ('common', 'local')
    ]
    if not environment_files:
        return [('default', common)]

    priority = {'local': 0, 'dev': 1, 'sit': 2, 'test': 3, 'uat': 4, 'staging': 5, 'prod': 6, 'production': 7}
    environment_files.sort(key=lambda path: (priority.get(path.stem.lower(), 99), path.stem.lower()))
    environments = []
    for path in environment_files:
        properties = common.copy()
        properties.update(parse_properties_file(path))
        environments.append((path.stem, properties))
    return environments


def resolve_property_placeholders(value, properties: dict) -> str:
    if value is None:
        return ''

    def replace(match):
        return properties.get(match.group(1), f'Unresolved: {match.group(0)}')

    return re.sub(r'\$\{([^}]+)\}', replace, str(value))


def render_transfer_listener_section(title: str, listeners: list, environments: list) -> str:
    time_unit_abbreviations = {
        'NANOSECONDS': 'ns',
        'MICROSECONDS': 'µs',
        'MILLISECONDS': 'ms',
        'SECONDS': 's',
        'MINUTES': 'min',
        'HOURS': 'h',
        'DAYS': 'd',
    }
    rows_by_environment = []
    for environment, properties in environments:
        rows = []
        for listener in listeners:
            values = [
                resolve_property_placeholders(listener.get('directory'), properties),
                resolve_property_placeholders(listener.get('filename_pattern'), properties),
                resolve_property_placeholders(listener.get('frequency'), properties),
                resolve_property_placeholders(listener.get('time_unit'), properties),
                resolve_property_placeholders(listener.get('flow'), properties),
                resolve_property_placeholders(listener.get('config_ref'), properties),
            ]
            time_unit = time_unit_abbreviations.get(values[3].upper(), values[3]) if values[3] else ''
            frequency = ' '.join(value for value in (values[2], time_unit) if value)
            rows.append(
                '<tr>'
                f'<td><code>{escape(values[0])}</code></td>'
                f'<td><code>{escape(values[1])}</code></td>'
                f'<td><code>{escape(frequency)}</code></td>'
                f'<td><code>{escape(values[4])}</code></td>'
                f'<td><code>{escape(values[5])}</code></td>'
                '</tr>'
            )
        table = (
            '<table><thead><tr><th>Directory</th><th>Filename Pattern</th><th>Frequency</th>'
            '<th>Flow</th><th>Config</th></tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table>'
            if rows else f'<p>No {title} listeners found.</p>'
        )
        rows_by_environment.append(f'<h3>{escape(environment)}</h3><div class="card">{table}</div>')

    section_id = f"{title.lower()}-listeners"
    return f'<!-- {title} Listeners -->\n<h2 id="{section_id}">&#128230; {title} Listeners</h2>\n' + '\n'.join(rows_by_environment)


def render_anypoint_mq_subscriber_section(subscribers: list, environments: list) -> str:
    environment_sections = []
    for environment, properties in environments:
        rows = []
        for subscriber in subscribers:
            values = {
                key: resolve_property_placeholders(subscriber.get(source_key), properties)
                for key, source_key in (
                    ('destination', 'destination'),
                    ('flow', 'flow'),
                    ('config', 'config_ref'),
                    ('ack_mode', 'acknowledgement_mode'),
                    ('ack_timeout', 'acknowledgement_timeout'),
                    ('ack_unit', 'acknowledgement_timeout_unit'),
                    ('subscription_mode', 'subscription_mode'),
                    ('circuit_breaker_errors_threshold', 'circuit_breaker_errors_threshold'),
                    ('circuit_breaker_trip_timeout', 'circuit_breaker_trip_timeout'),
                    ('circuit_breaker_trip_timeout_unit', 'circuit_breaker_trip_timeout_unit'),
                    ('circuit_breaker_on_error_types', 'circuit_breaker_on_error_types'),
                )
            }
            timeout_unit = {
                'NANOSECONDS': 'ns',
                'MICROSECONDS': 'µs',
                'MILLISECONDS': 'ms',
                'SECONDS': 's',
                'MINUTES': 'min',
                'HOURS': 'h',
                'DAYS': 'd',
            }.get(values['ack_unit'].upper(), values['ack_unit']) if values['ack_unit'] else ''
            timeout = ' '.join(value for value in (values['ack_timeout'], timeout_unit) if value)
            trip_unit = {
                'NANOSECONDS': 'ns',
                'MICROSECONDS': 'µs',
                'MILLISECONDS': 'ms',
                'SECONDS': 's',
                'MINUTES': 'min',
                'HOURS': 'h',
                'DAYS': 'd',
            }.get(values['circuit_breaker_trip_timeout_unit'].upper(), values['circuit_breaker_trip_timeout_unit']) if values['circuit_breaker_trip_timeout_unit'] else ''
            trip_timeout = ' '.join(
                value for value in (values['circuit_breaker_trip_timeout'], trip_unit) if value
            )
            circuit_breaker_details = []
            if values['circuit_breaker_errors_threshold']:
                circuit_breaker_details.append(f"threshold: {values['circuit_breaker_errors_threshold']}")
            if trip_timeout:
                circuit_breaker_details.append(f"trip: {trip_timeout}")
            if values['circuit_breaker_on_error_types']:
                circuit_breaker_details.append(f"errors: {values['circuit_breaker_on_error_types']}")
            circuit_breaker = (
                f"Yes ({', '.join(circuit_breaker_details)})"
                if subscriber.get('circuit_breaker_configured') else 'No'
            )
            rows.append(
                '<tr>'
                f'<td><code>{escape(values["destination"])}</code></td>'
                f'<td><code>{escape(values["flow"])}</code></td>'
                f'<td><code>{escape(values["config"])}</code></td>'
                f'<td><code>{escape(values["ack_mode"])}</code></td>'
                f'<td><code>{escape(timeout)}</code></td>'
                f'<td><code>{escape(values["subscription_mode"])}</code></td>'
                f'<td><code>{escape(circuit_breaker)}</code></td>'
                '</tr>'
            )
        table = (
            '<table><thead><tr><th>Destination</th><th>Flow</th><th>Config</th><th>Acknowledgement Mode</th>'
            '<th>Acknowledgement Timeout</th><th>Subscription Mode</th>'
            '<th>Circuit Breaker</th>'
            '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'
            if rows else '<p>No Anypoint MQ subscribers found.</p>'
        )
        environment_sections.append(f'<h3>{escape(environment)}</h3><div class="card">{table}</div>')

    return '<!-- Anypoint MQ Subscribers -->\n<h2 id="anypoint-mq-subscribers">&#128225; Anypoint MQ Subscribers</h2>\n' + '\n'.join(environment_sections)


def render_scheduler_section(schedulers: list, environments: list) -> str:
    """Render scheduler details with cron placeholders resolved per deployment environment."""
    properties_by_environment = {
        environment.lower(): properties
        for environment, properties in environments
    }
    sections = []
    for environment in ('sit', 'uat', 'prod'):
        properties = properties_by_environment.get(environment)
        if properties is None:
            continue

        rows = []
        for scheduler in schedulers:
            values = (
                scheduler.get('name', ''),
                scheduler.get('flow', ''),
                resolve_property_placeholders(scheduler.get('cron_expression'), properties),
                resolve_property_placeholders(scheduler.get('timezone'), properties),
                scheduler.get('source_file', ''),
            )
            rows.append(
                '<tr>'
                f'<td><code>{escape(values[0])}</code></td>'
                f'<td><code>{escape(values[1])}</code></td>'
                f'<td><code>{escape(values[2])}</code></td>'
                f'<td><code>{escape(values[3])}</code></td>'
                f'<td><code>{escape(values[4])}</code></td>'
                '</tr>'
            )

        table = (
            '<table><thead><tr><th>Name</th><th>Flow</th><th>Cron</th>'
            '<th>Timezone</th><th>Source</th></tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table>'
            if rows else '<p>No schedulers found.</p>'
        )
        sections.append(f'<h3>{escape(environment.upper())}</h3><div class="card">{table}</div>')

    return '<!-- Schedulers -->\n<h2 id="schedulers">&#9200; Schedulers</h2>\n' + '\n'.join(sections)


def render_html(project_info: dict, endpoints: dict, environments: list,
                config_files: list, property_files: list, project_name: str) -> str:
    """Render the full HTML report."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Endpoints
    http_listener_records = [
        endpoint for endpoint in endpoints.get('endpoints', [])
        if endpoint.get('type') == 'http-listener'
    ]
    sftp_listeners = endpoints.get('sftp_listeners', [])
    ftp_listeners = endpoints.get('ftp_listeners', [])
    anypoint_mq_subscribers = endpoints.get('anypoint_mq_subscribers', [])
    flows = endpoints.get('flows', [])
    schedulers = endpoints.get('schedulers', [])
    vm_queues = endpoints.get('vm_queues', [])
    apikit_router_keys = {
        (
            os.path.normcase(str(Path(endpoint.get('source_file', '')).resolve())),
            endpoint.get('config_ref'),
        )
        for endpoint in endpoints.get('endpoints', [])
        if endpoint.get('type') == 'apikit-router' and endpoint.get('config_ref')
    }

    apikit_flows = [
        flow for flow in flows
        if flow.get('name', '').startswith(('get:', 'post:', 'put:', 'delete:', 'patch:'))
        and any(
            os.path.normcase(str(Path(flow.get('source_file', '')).resolve())) == source_file
            and flow.get('name', '').endswith(f":{config_ref}")
            for source_file, config_ref in apikit_router_keys
        )
    ]
    http_endpoint_count = sum(bool(endpoint.get('path')) for endpoint in http_listener_records)
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

    http_listener_rows = '\n'.join(
        f"<tr><td><code>{endpoint.get('method', '*')}</code></td>"
        f"<td><code>{endpoint.get('path', '')}</code></td>"
        f"<td><code>{endpoint.get('flow', '')}</code></td>"
        f"<td><code>{endpoint.get('config_ref', '')}</code></td>"
        f"<td><code>{endpoint.get('source_file', '')}</code></td></tr>"
        for endpoint in http_listener_records
        if endpoint.get('path')
    )

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

    # APIkit-generated flow table
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
  --bg: #f3f6f9; --surface: #ffffff; --border: #dfe6ee;
  --fg: #17365d; --muted: #657b95; --accent: #0875be;
  --cyan: #00a6d8; --green: #368b4d; --yellow: #e6a323; --red: #d94848; --purple: #7d4bb3;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg); color: var(--fg); line-height: 1.55; padding: 16px;
}}
html {{ scroll-behavior: smooth; }}
.container {{ max-width: 1600px; margin: 0 auto; }}
.hero {{
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  background: #0867ad; color: #fff; border-radius: 6px; padding: 16px 22px;
  box-shadow: 0 2px 8px rgba(18, 54, 91, 0.18); margin-bottom: 16px;
}}
h1 {{ font-size: 1.35rem; line-height: 1.3; font-weight: 650; }}
.subtitle {{ color: #d9eafb; margin: 0; font-size: 0.86rem; }}
h2 {{
  font-size: 1.08rem; margin: 1.35rem 0 0.7rem; color: #173f70;
  border-bottom: 1px solid var(--border); padding: 0 0 0.45rem 0.1rem;
  scroll-margin-top: 1rem;
}}
h3 {{ font-size: 0.88rem; margin: 1rem 0 0.35rem; color: #315d8a; text-transform: uppercase; letter-spacing: 0.035em; }}
.stat-link {{ display: block; color: inherit; text-decoration: none; border-radius: 5px; }}
.stat-link:focus-visible {{ outline: 3px solid var(--accent); outline-offset: 3px; }}
.stat-link:hover .stat {{ border-color: var(--accent); }}
.back-to-top {{
  position: fixed; right: 24px; bottom: 24px; z-index: 10;
  display: grid; width: 48px; height: 48px; place-items: center;
  border-radius: 50%; background: var(--accent); color: #fff;
  box-shadow: 0 2px 8px rgba(18, 54, 91, 0.28);
  font-size: 1.5rem; line-height: 1; text-decoration: none;
  visibility: hidden; opacity: 0; pointer-events: none;
  transform: translateY(8px);
  transition: opacity 0.2s ease, transform 0.2s ease, visibility 0.2s;
}}
.back-to-top.is-visible {{
  visibility: visible; opacity: 1; pointer-events: auto; transform: translateY(0);
}}
.back-to-top:hover {{ background: #0867ad; }}
.back-to-top:focus-visible {{ outline: 3px solid var(--fg); outline-offset: 3px; }}
.card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 5px; padding: 14px; margin: 0.55rem 0;
  box-shadow: 0 1px 3px rgba(28, 54, 82, 0.07);
}}
.badge {{
  display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px;
  font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
}}
.badge.flow {{ background: #e6f3fb; color: #0867ad; }}
.badge.subflow {{ background: #f0eafa; color: #7040a0; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
th, td {{ padding: 0.52rem 0.65rem; text-align: left; border-bottom: 1px solid #e8edf2; vertical-align: top; }}
th {{ color: #47627f; background: #f5f8fb; font-weight: 650; text-transform: uppercase; font-size: 0.69rem; letter-spacing: 0.045em; white-space: nowrap; }}
tbody tr:hover {{ background: #f7fbfe; }}
tbody tr:last-child td {{ border-bottom: 0; }}
code {{
  background: #eef5fa; color: #205a8d; padding: 0.1rem 0.3rem; border-radius: 3px;
  font-family: 'Cascadia Code', 'Fira Code', monospace; font-size: 0.82em;
  overflow-wrap: anywhere;
}}
.stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(185px, 1fr)); gap: 0.75rem; margin: 0 0 1.1rem; }}
.stat {{
  min-width: 0; background: var(--surface);
  border: 1px solid var(--border); border-left: 4px solid var(--cyan); border-radius: 5px;
  padding: 0.8rem 1rem; text-align: left; box-shadow: 0 1px 3px rgba(28, 54, 82, 0.07);
}}
.stat .num {{ font-size: 1.75rem; line-height: 1.15; font-weight: 700; color: #173f70; }}
.stat .label {{ color: #607995; font-size: 0.68rem; font-weight: 650; text-transform: uppercase; letter-spacing: 0.035em; margin-top: 0.25rem; }}
.stat-link:nth-child(2) .stat {{ border-left-color: #7d4bb3; }}
.stat-link:nth-child(3) .stat {{ border-left-color: #32a852; }}
.stat-link:nth-child(4) .stat {{ border-left-color: #e2a020; }}
.meta-table td:first-child {{ color: #607995; width: 180px; font-weight: 600; }}
footer {{ margin-top: 1.5rem; padding: 0.8rem 0; border-top: 1px solid var(--border); color: var(--muted); font-size: 0.75rem; }}
@media (max-width: 640px) {{
  body {{ padding: 8px; }}
  .hero {{ align-items: flex-start; flex-direction: column; padding: 14px 16px; }}
  .stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .card {{ overflow-x: auto; }}
  .back-to-top {{ right: 16px; bottom: 16px; }}
}}
@media (prefers-reduced-motion: reduce) {{
  html {{ scroll-behavior: auto; }}
  .back-to-top {{ transition: none; }}
}}
</style>
</head>
<body>
<div class="container" id="top">

<header class="hero">
  <h1>&#128736; MuleSoft API Project Report</h1>
  <p class="subtitle"><code>{project_name}</code> &mdash; generated {now}</p>
</header>

<!-- Summary Stats -->
<div class="stats">
    <a class="stat-link" href="#http-endpoints"><div class="stat total"><div class="num">{http_endpoint_count}</div><div class="label">HTTP Endpoints</div></div></a>
    <a class="stat-link" href="#apikit-generated-flows"><div class="stat total"><div class="num">{len(apikit_flows)}</div><div class="label">APIkit-Generated Flows</div></div></a>
    <a class="stat-link" href="#sftp-listeners"><div class="stat total"><div class="num">{len(sftp_listeners)}</div><div class="label">SFTP Listeners</div></div></a>
    <a class="stat-link" href="#ftp-listeners"><div class="stat total"><div class="num">{len(ftp_listeners)}</div><div class="label">FTP Listeners</div></div></a>
    <a class="stat-link" href="#anypoint-mq-subscribers"><div class="stat total"><div class="num">{len(anypoint_mq_subscribers)}</div><div class="label">Anypoint MQ Subscribers</div></div></a>
    <a class="stat-link" href="#schedulers"><div class="stat total"><div class="num">{len(schedulers)}</div><div class="label">Schedulers</div></div></a>
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

{render_transfer_listener_section('SFTP', sftp_listeners, environments)}

{render_transfer_listener_section('FTP', ftp_listeners, environments)}

<h2 id="http-endpoints">HTTP Endpoints ({http_endpoint_count})</h2>
<div class="card">
{('<table><thead><tr><th>Method</th><th>Path</th><th>Flow</th><th>Config</th><th>Source</th></tr></thead><tbody>' + http_listener_rows + '</tbody></table>') if http_endpoint_count else '<p>No HTTP listeners found.</p>'}
</div>

{render_anypoint_mq_subscriber_section(anypoint_mq_subscribers, environments)}

<h2 id="apikit-generated-flows">APIkit-Generated Flows ({len(apikit_flows)})</h2>
<div class="card">
{('<table><thead><tr><th>Flow Name</th><th>Source</th></tr></thead><tbody>' + apikit_flow_rows + '</tbody></table>') if apikit_flows else '<p>No APIkit-generated flows found.</p>'}
</div>

{render_scheduler_section(schedulers, environments)}

<!-- VM Queues -->
{f'''
<h2>&#9889; VM Queues</h2>
<div class="card">
<table><thead><tr><th>Type</th><th>Queue</th><th>Config</th><th>Flow</th></tr></thead>
<tbody>{endpoint_rows(vm_queues)}</tbody></table>
</div>
''' if vm_queues else ''}

<!-- Property Files -->
<h2>&#9881; Property Files</h2>
<div class="card">
{('<table><thead><tr><th>Path</th><th>Size</th></tr></thead><tbody>' + prop_rows + '</tbody></table>') if property_files else '<p>No property files found.</p>'}
</div>

<footer>
Generated by <code>mulesoft-api-explorer</code> skill &mdash; {now}
</footer>
</div>
<a class="back-to-top" href="#top" aria-label="Back to top" title="Back to top">&#8593;</a>
<script>
const backToTop = document.querySelector('.back-to-top');
const updateBackToTopVisibility = () => {{
  backToTop.classList.toggle('is-visible', window.scrollY > 0);
}};
window.addEventListener('scroll', updateBackToTopVisibility, {{ passive: true }});
updateBackToTopVisibility();
</script>
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
    endpoints = run_script('extract-endpoints.py', str(project_root))
    environments = load_environment_properties(project_root)

    config_files = list_config_files(project_root)
    property_files = list_property_files(project_root)

    # Generate HTML
    html = render_html(
        project_info, endpoints, environments,
        config_files, property_files, project_info['name']
    )

    output_path.write_text(html, encoding='utf-8')
    print(f"Report written: {output_path}", file=sys.stderr)
    print(str(output_path))


if __name__ == '__main__':
    main()
