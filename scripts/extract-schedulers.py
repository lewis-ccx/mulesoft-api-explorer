#!/usr/bin/env python3
"""
Extract MuleSoft schedulers from project XML files.
Outputs JSON with scheduler details: cron expression, frequency, flow.
"""

import xml.etree.ElementTree as ET
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional

NAMESPACES = {
    'mule': 'http://www.mulesoft.org/schema/mule/core',
    'scheduler': 'http://www.mulesoft.org/schema/mule/scheduler',
    'doc': 'http://www.mulesoft.org/schema/mule/documentation',
}


def register_namespaces():
    for prefix, uri in NAMESPACES.items():
        ET.register_namespace(prefix, uri)


def parse_xml_file(filepath: Path) -> Optional[ET.Element]:
    try:
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=False))
        tree = ET.parse(filepath, parser=parser)
        return tree.getroot()
    except ET.ParseError as e:
        print(f"Warning: Failed to parse {filepath}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Warning: Error reading {filepath}: {e}", file=sys.stderr)
        return None


def get_parent_flow(element: ET.Element, parents: Dict[ET.Element, ET.Element]) -> Optional[str]:
    parent = element
    while parent is not None:
        tag = parent.tag.rsplit('}', 1)[-1]
        if tag in ('flow', 'sub-flow'):
            return parent.get('name')
        parent = parents.get(parent)
    return None


def extract_schedulers(root: ET.Element, filepath: Path,
                       parents: Dict[ET.Element, ET.Element]) -> List[Dict]:
    schedulers = []

    for scheduler_element in root.findall('.//mule:scheduler', NAMESPACES):
        scheduling_strategy = scheduler_element.find('mule:scheduling-strategy', NAMESPACES)
        cron = scheduling_strategy.find('mule:cron', NAMESPACES) if scheduling_strategy is not None else None
        fixed_frequency = (
            scheduling_strategy.find('mule:fixed-frequency', NAMESPACES)
            if scheduling_strategy is not None else None
        )
        schedulers.append({
            'type': 'flow-scheduler',
            'name': scheduler_element.get('doc:name')
                    or scheduler_element.get('{http://www.mulesoft.org/schema/mule/documentation}name')
                    or scheduler_element.get('name'),
            'cron_expression': cron.get('expression') if cron is not None else None,
            'frequency': fixed_frequency.get('frequency') if fixed_frequency is not None else None,
            'timezone': (cron.get('timeZone') or cron.get('timezone')) if cron is not None else None,
            'start_delay': fixed_frequency.get('startDelay') if fixed_frequency is not None else None,
            'flow': get_parent_flow(scheduler_element, parents),
            'source_file': str(filepath),
            'line': None,
        })
    
    # scheduler:trigger elements (inline triggers in flows)
    for trigger in root.findall('.//scheduler:trigger', NAMESPACES):
        config_ref = trigger.get('config-ref')
        flow_name = get_parent_flow(trigger, parents)
        
        schedulers.append({
            'type': 'inline-trigger',
            'config_ref': config_ref,
            'flow': flow_name,
            'source_file': str(filepath),
            'line': trigger.sourceline if hasattr(trigger, 'sourceline') else None,
        })
    
    # scheduler:config elements (standalone config with cron/fixed)
    for config in root.findall('.//scheduler:config', NAMESPACES):
        name = config.get('name')
        cron_expr = None
        frequency = None
        timezone = None
        start_delay = None
        
        trigger_config = config.find('.//scheduler:trigger-config', NAMESPACES)
        if trigger_config is not None:
            cron_trigger = trigger_config.find('.//scheduler:cron-trigger', NAMESPACES)
            if cron_trigger is not None:
                cron_expr = cron_trigger.get('expression')
                timezone = cron_trigger.get('timeZone')
                start_delay = cron_trigger.get('startDelay')
            
            fixed_trigger = trigger_config.find('.//scheduler:fixed-frequency-trigger', NAMESPACES)
            if fixed_trigger is not None:
                frequency = fixed_trigger.get('frequency')
                start_delay = fixed_trigger.get('startDelay')
                timezone = fixed_trigger.get('timeZone')
        
        schedulers.append({
            'type': 'scheduler-config',
            'name': name,
            'cron_expression': cron_expr,
            'frequency': frequency,
            'timezone': timezone,
            'start_delay': start_delay,
            'source_file': str(filepath),
            'line': config.sourceline if hasattr(config, 'sourceline') else None,
        })
    
    return schedulers


def extract_quartz_configs(root: ET.Element, filepath: Path,
                           parents: Dict[ET.Element, ET.Element]) -> List[Dict]:
    """Look for Quartz-specific configurations."""
    quartz = []
    
    # quartz:config or any element with cronExpression attribute
    for elem in root.iter():
        if 'cronExpression' in elem.attrib:
            flow_name = get_parent_flow(elem, parents)
            quartz.append({
                'type': 'quartz-cron',
                'cron_expression': elem.get('cronExpression'),
                'flow': flow_name,
                'element': elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag,
                'source_file': str(filepath),
                'line': elem.sourceline if hasattr(elem, 'sourceline') else None,
            })
        
        if 'frequency' in elem.attrib and 'period' in elem.attrib:
            flow_name = get_parent_flow(elem, parents)
            quartz.append({
                'type': 'quartz-frequency',
                'frequency': elem.get('frequency'),
                'period': elem.get('period'),
                'flow': flow_name,
                'element': elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag,
                'source_file': str(filepath),
                'line': elem.sourceline if hasattr(elem, 'sourceline') else None,
            })
    
    return quartz


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract-schedulers.py <project-root>", file=sys.stderr)
        sys.exit(1)
    
    project_root = Path(sys.argv[1])
    mule_dir = project_root / 'src' / 'main' / 'mule'
    
    if not mule_dir.exists():
        print(f"Error: Mule directory not found: {mule_dir}", file=sys.stderr)
        sys.exit(1)
    
    register_namespaces()
    
    all_schedulers = []
    all_quartz = []
    
    for xml_file in mule_dir.rglob('*.xml'):
        root = parse_xml_file(xml_file)
        if root is None:
            continue
        
        parents = {child: parent for parent in root.iter() for child in parent}
        all_schedulers.extend(extract_schedulers(root, xml_file, parents))
        all_quartz.extend(extract_quartz_configs(root, xml_file, parents))
    
    result = {
        'schedulers': all_schedulers,
        'quartz_configs': all_quartz,
    }
    
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()