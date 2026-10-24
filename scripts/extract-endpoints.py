#!/usr/bin/env python3
"""
Extract MuleSoft API endpoints from project XML files.
Outputs JSON with endpoint details: path, method, flow, config.
"""

import xml.etree.ElementTree as ET
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional

# Mule namespaces
NAMESPACES = {
    'mule': 'http://www.mulesoft.org/schema/mule/core',
    'http': 'http://www.mulesoft.org/schema/mule/http',
    'apikit': 'http://www.mulesoft.org/schema/mule/apikit',
    'scheduler': 'http://www.mulesoft.org/schema/mule/scheduler',
    'vm': 'http://www.mulesoft.org/schema/mule/vm',
    'jms': 'http://www.mulesoft.org/schema/mule/jms',
}


def register_namespaces():
    for prefix, uri in NAMESPACES.items():
        ET.register_namespace(prefix, uri)


def parse_xml_file(filepath: Path) -> Optional[ET.Element]:
    try:
        tree = ET.parse(filepath)
        return tree.getroot()
    except ET.ParseError as e:
        print(f"Warning: Failed to parse {filepath}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Warning: Error reading {filepath}: {e}", file=sys.stderr)
        return None


def extract_http_listeners(root: ET.Element, filepath: Path) -> List[Dict]:
    endpoints = []
    
    # Find http:listener elements
    for listener in root.findall('.//http:listener', NAMESPACES):
        config_ref = listener.get('config-ref') or listener.get('{http://www.mulesoft.org/schema/mule/http}config-ref')
        path = listener.get('path') or listener.get('{http://www.mulesoft.org/schema/mule/http}path')
        method = listener.get('method') or listener.get('{http://www.mulesoft.org/schema/mule/http}method')
        allowed_methods = listener.get('allowedMethods') or listener.get('{http://www.mulesoft.org/schema/mule/http}allowedMethods')
        
        # Find parent flow
        flow_name = None
        parent = listener
        while parent is not None:
            if parent.tag.endswith('flow') or parent.tag.endswith('sub-flow'):
                flow_name = parent.get('name')
                break
            parent = parent.getparent() if hasattr(parent, 'getparent') else None
        
        endpoints.append({
            'type': 'http-listener',
            'path': path,
            'method': method or allowed_methods or '*',
            'config_ref': config_ref,
            'flow': flow_name,
            'source_file': str(filepath),
        })
    
    return endpoints


def extract_apikit_routers(root: ET.Element, filepath: Path) -> List[Dict]:
    endpoints = []
    
    for router in root.findall('.//apikit:router', NAMESPACES):
        config_ref = router.get('config-ref') or router.get('{http://www.mulesoft.org/schema/mule/apikit}config-ref')
        
        # Find parent flow
        flow_name = None
        parent = router
        while parent is not None:
            if parent.tag.endswith('flow') or parent.tag.endswith('sub-flow'):
                flow_name = parent.get('name')
                break
            parent = parent.getparent() if hasattr(parent, 'getparent') else None
        
        endpoints.append({
            'type': 'apikit-router',
            'config_ref': config_ref,
            'flow': flow_name,
            'source_file': str(filepath),
            'note': 'Endpoints defined in RAML/OAS referenced by config'
        })
    
    return endpoints


def extract_schedulers(root: ET.Element, filepath: Path) -> List[Dict]:
    schedulers = []
    
    # scheduler:trigger
    for trigger in root.findall('.//scheduler:trigger', NAMESPACES):
        config_ref = trigger.get('config-ref')
        
        flow_name = None
        parent = trigger
        while parent is not None:
            if parent.tag.endswith('flow') or parent.tag.endswith('sub-flow'):
                flow_name = parent.get('name')
                break
            parent = parent.getparent() if hasattr(parent, 'getparent') else None
        
        schedulers.append({
            'type': 'scheduler-trigger',
            'config_ref': config_ref,
            'flow': flow_name,
            'source_file': str(filepath),
        })
    
    # scheduler:config with cron/interval
    for config in root.findall('.//scheduler:config', NAMESPACES):
        name = config.get('name')
        cron_expr = None
        frequency = None
        
        for trigger_config in config.findall('.//scheduler:trigger-config', NAMESPACES):
            for cron in trigger_config.findall('.//scheduler:cron-trigger', NAMESPACES):
                cron_expr = cron.get('expression')
            for fixed in trigger_config.findall('.//scheduler:fixed-frequency-trigger', NAMESPACES):
                frequency = fixed.get('frequency')
        
        schedulers.append({
            'type': 'scheduler-config',
            'name': name,
            'cron_expression': cron_expr,
            'frequency': frequency,
            'source_file': str(filepath),
        })
    
    return schedulers


def extract_flows(root: ET.Element, filepath: Path) -> List[Dict]:
    flows = []
    
    for flow in root.findall('.//mule:flow', NAMESPACES):
        flows.append({
            'type': 'flow',
            'name': flow.get('name'),
            'source_file': str(filepath),
        })
    
    for subflow in root.findall('.//mule:sub-flow', NAMESPACES):
        flows.append({
            'type': 'sub-flow',
            'name': subflow.get('name'),
            'source_file': str(filepath),
        })
    
    return flows


def extract_vm_queues(root: ET.Element, filepath: Path) -> List[Dict]:
    queues = []
    
    for listener in root.findall('.//vm:listener', NAMESPACES):
        config_ref = listener.get('config-ref')
        queue_name = listener.get('queueName')
        
        flow_name = None
        parent = listener
        while parent is not None:
            if parent.tag.endswith('flow') or parent.tag.endswith('sub-flow'):
                flow_name = parent.get('name')
                break
            parent = parent.getparent() if hasattr(parent, 'getparent') else None
        
        queues.append({
            'type': 'vm-listener',
            'queue': queue_name,
            'config_ref': config_ref,
            'flow': flow_name,
            'source_file': str(filepath),
        })
    
    for publish in root.findall('.//vm:publish', NAMESPACES):
        config_ref = publish.get('config-ref')
        queue_name = publish.get('queueName')
        
        flow_name = None
        parent = publish
        while parent is not None:
            if parent.tag.endswith('flow') or parent.tag.endswith('sub-flow'):
                flow_name = parent.get('name')
                break
            parent = parent.getparent() if hasattr(parent, 'getparent') else None
        
        queues.append({
            'type': 'vm-publish',
            'queue': queue_name,
            'config_ref': config_ref,
            'flow': flow_name,
            'source_file': str(filepath),
        })
    
    return queues


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract-endpoints.py <project-root>", file=sys.stderr)
        sys.exit(1)
    
    project_root = Path(sys.argv[1])
    mule_dir = project_root / 'src' / 'main' / 'mule'
    
    if not mule_dir.exists():
        print(f"Error: Mule directory not found: {mule_dir}", file=sys.stderr)
        sys.exit(1)
    
    register_namespaces()
    
    all_endpoints = []
    all_schedulers = []
    all_flows = []
    all_vm = []
    
    for xml_file in mule_dir.rglob('*.xml'):
        root = parse_xml_file(xml_file)
        if root is None:
            continue
        
        all_endpoints.extend(extract_http_listeners(root, xml_file))
        all_endpoints.extend(extract_apikit_routers(root, xml_file))
        all_schedulers.extend(extract_schedulers(root, xml_file))
        all_flows.extend(extract_flows(root, xml_file))
        all_vm.extend(extract_vm_queues(root, xml_file))
    
    result = {
        'endpoints': all_endpoints,
        'schedulers': all_schedulers,
        'flows': all_flows,
        'vm_queues': all_vm,
    }
    
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()