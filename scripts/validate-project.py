#!/usr/bin/env python3
"""
MuleSoft project validation checklist.
Checks for common issues and best practices.
"""

import xml.etree.ElementTree as ET
import json
import sys
import os
import re
from pathlib import Path
from typing import Dict, List, Set

NAMESPACES = {
    'mule': 'http://www.mulesoft.org/schema/mule/core',
    'http': 'http://www.mulesoft.org/schema/mule/http',
    'ee': 'http://www.mulesoft.org/schema/mule/ee/core',
    'api-gateway': 'http://www.mulesoft.org/schema/mule/api-gateway',
    'apikit': 'http://www.mulesoft.org/schema/mule/apikit',
    'scheduler': 'http://www.mulesoft.org/schema/mule/scheduler',
    'db': 'http://www.mulesoft.org/schema/mule/db',
    'vm': 'http://www.mulesoft.org/schema/mule/vm',
    'jms': 'http://www.mulesoft.org/schema/mule/jms',
}


def register_namespaces():
    for prefix, uri in NAMESPACES.items():
        ET.register_namespace(prefix, uri)


def parse_xml_file(filepath: Path):
    try:
        tree = ET.parse(filepath)
        return tree.getroot(), None
    except ET.ParseError as e:
        return None, f"Parse error: {e}"
    except Exception as e:
        return None, f"Read error: {e}"


def check_pom(project_root: Path) -> List[Dict]:
    issues = []
    pom = project_root / 'pom.xml'
    
    if not pom.exists():
        issues.append({'level': 'error', 'check': 'pom.xml', 'message': 'pom.xml not found'})
        return issues
    
    content = pom.read_text()
    
    if '<packaging>mule-application</packaging>' not in content:
        issues.append({'level': 'warning', 'check': 'pom.xml', 'message': 'Packaging should be mule-application'})
    
    mule_version_match = re.search(r'<mule\.version>([^<]+)</mule\.version>', content)
    if not mule_version_match:
        issues.append({'level': 'warning', 'check': 'pom.xml', 'message': 'mule.version property not found'})
    else:
        version = mule_version_match.group(1)
        issues.append({'level': 'info', 'check': 'pom.xml', 'message': f'Mule version: {version}'})
    
    if 'mule-maven-plugin' not in content:
        issues.append({'level': 'error', 'check': 'pom.xml', 'message': 'mule-maven-plugin not configured'})
    
    if re.search(r'<version>[0-9]+\.[0-9]+\.[0-9]+</version>', content):
        issues.append({'level': 'warning', 'check': 'pom.xml', 'message': 'Hardcoded dependency versions found; use properties'})
    
    return issues


def check_mule_artifact(project_root: Path) -> List[Dict]:
    issues = []
    artifact = project_root / 'mule-artifact.json'
    
    if not artifact.exists():
        issues.append({'level': 'error', 'check': 'mule-artifact.json', 'message': 'mule-artifact.json not found'})
        return issues
    
    try:
        data = json.loads(artifact.read_text())
        
        if 'minMuleVersion' not in data:
            issues.append({'level': 'warning', 'check': 'mule-artifact.json', 'message': 'minMuleVersion not specified'})
        
        if data.get('requiredProduct') not in ['MULE', 'API_GATEWAY']:
            issues.append({'level': 'warning', 'check': 'mule-artifact.json', 'message': f"requiredProduct should be MULE or API_GATEWAY, got {data.get('requiredProduct')}"})
        
        classloader = data.get('classLoaderModelLoaderDescriptor', {})
        if classloader.get('id') != 'mule':
            issues.append({'level': 'warning', 'check': 'mule-artifact.json', 'message': 'classLoaderModelLoaderDescriptor.id should be mule'})
        
    except json.JSONDecodeError as e:
        issues.append({'level': 'error', 'check': 'mule-artifact.json', 'message': f'Invalid JSON: {e}'})
    
    return issues


def check_xml_files(project_root: Path) -> List[Dict]:
    issues = []
    mule_dir = project_root / 'src' / 'main' / 'mule'
    
    if not mule_dir.exists():
        issues.append({'level': 'error', 'check': 'xml-files', 'message': 'src/main/mule directory not found'})
        return issues
    
    xml_files = list(mule_dir.rglob('*.xml'))
    if not xml_files:
        issues.append({'level': 'error', 'check': 'xml-files', 'message': 'No XML config files found in src/main/mule'})
        return issues
    
    all_placeholders = set()
    hardcoded_urls = []
    hardcoded_secrets = []
    missing_error_handlers = []
    flows_without_names = []
    
    for xml_file in xml_files:
        root, error = parse_xml_file(xml_file)
        if error:
            issues.append({'level': 'error', 'check': 'xml-syntax', 'file': str(xml_file), 'message': str(error)})
            continue
        
        content = xml_file.read_text()
        placeholders = re.findall(r'\$\{[^}]+\}', content)
        all_placeholders.update(placeholders)
        
        for match in re.finditer(r'(https?://localhost:[0-9]+|https?://127\.0\.0\.1:[0-9]+)', content):
            hardcoded_urls.append({'file': str(xml_file), 'url': match.group()})
        
        for match in re.finditer(r'(password|secret|api[_-]?key|token)\s*[:=]\s*["\'][^"\']+["\']', content, re.IGNORECASE):
            hardcoded_secrets.append({'file': str(xml_file), 'match': match.group()[:80]})
        
        flows = root.findall('.//mule:flow', NAMESPACES)
        for flow in flows:
            flow_name = flow.get('name')
            if not flow_name:
                flows_without_names.append(str(xml_file))
            
            error_handler_ref = flow.get('errorHandler-ref')
            if not error_handler_ref:
                has_error_handling = False
                for child in flow:
                    tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if 'error' in tag.lower():
                        has_error_handling = True
                        break
                if not has_error_handling:
                    missing_error_handlers.append({'file': str(xml_file), 'flow': flow_name})
    
    if hardcoded_urls:
        for item in hardcoded_urls:
            issues.append({'level': 'warning', 'check': 'hardcoded-urls', 'file': item['file'], 'message': f'Hardcoded URL: {item["url"]}'})
    
    if hardcoded_secrets:
        for item in hardcoded_secrets:
            issues.append({'level': 'error', 'check': 'hardcoded-secrets', 'file': item['file'], 'message': f'Potential hardcoded secret: {item["match"]}'})
    
    if missing_error_handlers:
        for item in missing_error_handlers:
            issues.append({'level': 'warning', 'check': 'error-handling', 'file': item['file'], 'message': f'Flow "{item["flow"]}" has no error handling'})
    
    if flows_without_names:
        for f in flows_without_names:
            issues.append({'level': 'error', 'check': 'flow-naming', 'file': f, 'message': 'Flow missing name attribute'})
    
    if all_placeholders:
        issues.append({'level': 'info', 'check': 'placeholders', 'message': f'Found {len(all_placeholders)} unique property placeholders', 'details': sorted(all_placeholders)})
    
    return issues


def check_properties(project_root: Path) -> List[Dict]:
    issues = []
    resources = project_root / 'src' / 'main' / 'resources'
    
    if not resources.exists():
        issues.append({'level': 'warning', 'check': 'properties', 'message': 'src/main/resources directory not found'})
        return issues
    
    prop_files = list(resources.glob('*.yaml')) + list(resources.glob('*.properties'))
    if not prop_files:
        issues.append({'level': 'warning', 'check': 'properties', 'message': 'No property files found in src/main/resources'})
    
    env_files = [f for f in prop_files if f.stem in ['dev', 'test', 'staging', 'prod', 'production']]
    if not env_files:
        issues.append({'level': 'info', 'check': 'properties', 'message': 'No environment-specific property files found (dev.yaml, prod.yaml, etc.)'})
    
    return issues


def check_api_definitions(project_root: Path) -> List[Dict]:
    issues = []
    api_dir = project_root / 'src' / 'main' / 'api'
    
    if not api_dir.exists():
        issues.append({'level': 'info', 'check': 'api-definitions', 'message': 'src/main/api directory not found (optional)'})
        return issues
    
    api_files = list(api_dir.glob('*.raml')) + list(api_dir.glob('*.yaml')) + list(api_dir.glob('*.json'))
    if not api_files:
        issues.append({'level': 'warning', 'check': 'api-definitions', 'message': 'API directory exists but no RAML/OAS files found'})
    
    for api_file in api_files:
        content = api_file.read_text()
        
        if api_file.suffix in ['.raml', '.yaml']:
            if 'title:' not in content:
                issues.append({'level': 'warning', 'check': 'api-definitions', 'file': str(api_file), 'message': 'Missing title in API definition'})
            if 'version:' not in content:
                issues.append({'level': 'warning', 'check': 'api-definitions', 'file': str(api_file), 'message': 'Missing version in API definition'})
        elif api_file.suffix == '.json':
            try:
                data = json.loads(content)
                if 'info' not in data:
                    issues.append({'level': 'warning', 'check': 'api-definitions', 'file': str(api_file), 'message': 'OpenAPI missing info object'})
                elif 'title' not in data.get('info', {}) or 'version' not in data.get('info', {}):
                    issues.append({'level': 'warning', 'check': 'api-definitions', 'file': str(api_file), 'message': 'OpenAPI missing title or version'})
            except json.JSONDecodeError:
                issues.append({'level': 'error', 'check': 'api-definitions', 'file': str(api_file), 'message': 'Invalid JSON in OpenAPI file'})
    
    return issues


def check_tests(project_root: Path) -> List[Dict]:
    issues = []
    test_dir = project_root / 'src' / 'test' / 'mule'
    
    if not test_dir.exists():
        issues.append({'level': 'info', 'check': 'tests', 'message': 'src/test/mule directory not found (no MUnit tests)'})
        return issues
    
    test_files = list(test_dir.rglob('*.xml'))
    if not test_files:
        issues.append({'level': 'info', 'check': 'tests', 'message': 'Test directory exists but no MUnit test files found'})
    else:
        issues.append({'level': 'info', 'check': 'tests', 'message': f'Found {len(test_files)} MUnit test file(s)'})
    
    return issues


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate-project.py <project-root>", file=sys.stderr)
        sys.exit(1)
    
    project_root = Path(sys.argv[1]).resolve()
    
    if not project_root.exists():
        print(f"Error: Project root not found: {project_root}", file=sys.stderr)
        sys.exit(1)
    
    register_namespaces()
    
    all_issues = []
    
    all_issues.extend(check_pom(project_root))
    all_issues.extend(check_mule_artifact(project_root))
    all_issues.extend(check_xml_files(project_root))
    all_issues.extend(check_properties(project_root))
    all_issues.extend(check_api_definitions(project_root))
    all_issues.extend(check_tests(project_root))
    
    errors = [i for i in all_issues if i['level'] == 'error']
    warnings = [i for i in all_issues if i['level'] == 'warning']
    infos = [i for i in all_issues if i['level'] == 'info']
    
    result = {
        'summary': {
            'errors': len(errors),
            'warnings': len(warnings),
            'infos': len(infos),
            'total': len(all_issues),
        },
        'issues': all_issues,
    }
    
    print(json.dumps(result, indent=2))
    
    if errors:
        sys.exit(1)

if __name__ == '__main__':
    main()