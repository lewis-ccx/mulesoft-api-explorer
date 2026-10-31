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
    'sftp': 'http://www.mulesoft.org/schema/mule/sftp',
    'ftp': 'http://www.mulesoft.org/schema/mule/ftp',
    'anypoint-mq': 'http://www.mulesoft.org/schema/mule/anypoint-mq',
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


def get_parent_flow(element: ET.Element, parents: Dict[ET.Element, ET.Element]) -> Optional[str]:
    parent = element
    while parent is not None:
        tag = parent.tag.rsplit('}', 1)[-1]
        if tag in ('flow', 'sub-flow'):
            return parent.get('name')
        parent = parents.get(parent)
    return None


def extract_http_listeners(root: ET.Element, filepath: Path,
                           parents: Dict[ET.Element, ET.Element]) -> List[Dict]:
    endpoints = []
    
    # Find http:listener elements
    for listener in root.findall('.//http:listener', NAMESPACES):
        config_ref = listener.get('config-ref') or listener.get('{http://www.mulesoft.org/schema/mule/http}config-ref')
        path = listener.get('path') or listener.get('{http://www.mulesoft.org/schema/mule/http}path')
        method = listener.get('method') or listener.get('{http://www.mulesoft.org/schema/mule/http}method')
        allowed_methods = listener.get('allowedMethods') or listener.get('{http://www.mulesoft.org/schema/mule/http}allowedMethods')
        
        flow_name = get_parent_flow(listener, parents)
        
        endpoints.append({
            'type': 'http-listener',
            'path': path,
            'method': method or allowed_methods or '*',
            'config_ref': config_ref,
            'flow': flow_name,
            'source_file': str(filepath),
        })
    
    return endpoints


def extract_sftp_listeners(root: ET.Element, filepath: Path,
                           parents: Dict[ET.Element, ET.Element]) -> List[Dict]:
    listeners = []

    for listener in root.findall('.//sftp:listener', NAMESPACES):
        fixed_frequency = listener.find('.//mule:fixed-frequency', NAMESPACES)
        matcher = listener.find('.//sftp:matcher', NAMESPACES)
        listeners.append({
            'type': 'sftp-listener',
            'config_ref': listener.get('config-ref'),
            'directory': listener.get('directory'),
            'recursive': listener.get('recursive'),
            'filename_pattern': matcher.get('filenamePattern') if matcher is not None else None,
            'frequency': fixed_frequency.get('frequency') if fixed_frequency is not None else None,
            'start_delay': fixed_frequency.get('startDelay') if fixed_frequency is not None else None,
            'time_unit': (fixed_frequency.get('timeUnit') or 'MILLISECONDS') if fixed_frequency is not None else None,
            'flow': get_parent_flow(listener, parents),
            'source_file': str(filepath),
        })

    return listeners


def extract_ftp_listeners(root: ET.Element, filepath: Path,
                          parents: Dict[ET.Element, ET.Element]) -> List[Dict]:
    listeners = []

    for listener in root.findall('.//ftp:listener', NAMESPACES):
        fixed_frequency = listener.find('.//mule:fixed-frequency', NAMESPACES)
        matcher = listener.find('.//ftp:matcher', NAMESPACES)
        listeners.append({
            'type': 'ftp-listener',
            'config_ref': listener.get('config-ref'),
            'directory': listener.get('directory'),
            'recursive': listener.get('recursive'),
            'filename_pattern': matcher.get('filenamePattern') if matcher is not None else None,
            'frequency': fixed_frequency.get('frequency') if fixed_frequency is not None else None,
            'start_delay': fixed_frequency.get('startDelay') if fixed_frequency is not None else None,
            'time_unit': (fixed_frequency.get('timeUnit') or 'MILLISECONDS') if fixed_frequency is not None else None,
            'flow': get_parent_flow(listener, parents),
            'source_file': str(filepath),
        })

    return listeners


def extract_anypoint_mq_subscribers(root: ET.Element, filepath: Path,
                                   parents: Dict[ET.Element, ET.Element]) -> List[Dict]:
    subscribers = []

    for subscriber in root.findall('.//anypoint-mq:subscriber', NAMESPACES):
        redelivery_policy = subscriber.find('.//mule:redelivery-policy', NAMESPACES)
        prefetch = subscriber.find('.//anypoint-mq:prefetch', NAMESPACES)
        subscriber_type = subscriber.find('.//anypoint-mq:subscriber-type', NAMESPACES)
        subscriber_type_elements = list(subscriber_type.iter()) if subscriber_type is not None else []
        uses_prefetch = any(
            element.tag.rsplit('}', 1)[-1] == 'prefetch'
            for element in subscriber_type_elements
        )
        uses_polling = any(
            element.tag.rsplit('}', 1)[-1] == 'polling'
            for element in subscriber_type_elements
        )
        if uses_prefetch and uses_polling:
            subscription_mode = 'Prefetch and Polling'
        elif uses_prefetch:
            subscription_mode = 'Prefetch'
        elif uses_polling:
            subscription_mode = 'Polling'
        else:
            subscription_mode = 'Unknown'
        circuit_breaker = subscriber.find('.//anypoint-mq:circuit-breaker', NAMESPACES)
        subscribers.append({
            'type': 'anypoint-mq-subscriber',
            'config_ref': subscriber.get('config-ref'),
            'destination': subscriber.get('destination'),
            'acknowledgement_mode': subscriber.get('acknowledgementMode'),
            'acknowledgement_timeout': subscriber.get('acknowledgementTimeout'),
            'acknowledgement_timeout_unit': subscriber.get('acknowledgementTimeoutUnit'),
            'subscription_mode': subscription_mode,
            'max_redelivery_count': redelivery_policy.get('maxRedeliveryCount') if redelivery_policy is not None else None,
            'prefetch_max_local_messages': prefetch.get('maxLocalMessages') if prefetch is not None else None,
            'circuit_breaker_configured': circuit_breaker is not None,
            'circuit_breaker_on_error_types': circuit_breaker.get('onErrorTypes') if circuit_breaker is not None else None,
            'circuit_breaker_errors_threshold': circuit_breaker.get('errorsThreshold') if circuit_breaker is not None else None,
            'circuit_breaker_trip_timeout': circuit_breaker.get('tripTimeout') if circuit_breaker is not None else None,
            'circuit_breaker_trip_timeout_unit': circuit_breaker.get('tripTimeoutUnit') if circuit_breaker is not None else None,
            'flow': get_parent_flow(subscriber, parents),
            'source_file': str(filepath),
        })

    return subscribers


def extract_apikit_routers(root: ET.Element, filepath: Path,
                           parents: Dict[ET.Element, ET.Element]) -> List[Dict]:
    endpoints = []
    
    for router in root.findall('.//apikit:router', NAMESPACES):
        config_ref = router.get('config-ref') or router.get('{http://www.mulesoft.org/schema/mule/apikit}config-ref')
        
        flow_name = get_parent_flow(router, parents)
        
        endpoints.append({
            'type': 'apikit-router',
            'config_ref': config_ref,
            'flow': flow_name,
            'source_file': str(filepath),
            'note': 'Endpoints defined in RAML/OAS referenced by config'
        })
    
    return endpoints


def extract_schedulers(root: ET.Element, filepath: Path,
                       parents: Dict[ET.Element, ET.Element]) -> List[Dict]:
    schedulers = []
    
    # scheduler:trigger
    for trigger in root.findall('.//scheduler:trigger', NAMESPACES):
        config_ref = trigger.get('config-ref')
        
        flow_name = get_parent_flow(trigger, parents)
        
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


def extract_vm_queues(root: ET.Element, filepath: Path,
                      parents: Dict[ET.Element, ET.Element]) -> List[Dict]:
    queues = []
    
    for listener in root.findall('.//vm:listener', NAMESPACES):
        config_ref = listener.get('config-ref')
        queue_name = listener.get('queueName')
        
        flow_name = get_parent_flow(listener, parents)
        
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
        
        flow_name = get_parent_flow(publish, parents)
        
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
    all_sftp_listeners = []
    all_ftp_listeners = []
    all_anypoint_mq_subscribers = []
    all_schedulers = []
    all_flows = []
    all_vm = []
    
    for xml_file in mule_dir.rglob('*.xml'):
        root = parse_xml_file(xml_file)
        if root is None:
            continue
        
        parents = {child: parent for parent in root.iter() for child in parent}
        all_endpoints.extend(extract_http_listeners(root, xml_file, parents))
        all_sftp_listeners.extend(extract_sftp_listeners(root, xml_file, parents))
        all_ftp_listeners.extend(extract_ftp_listeners(root, xml_file, parents))
        all_anypoint_mq_subscribers.extend(extract_anypoint_mq_subscribers(root, xml_file, parents))
        all_endpoints.extend(extract_apikit_routers(root, xml_file, parents))
        all_schedulers.extend(extract_schedulers(root, xml_file, parents))
        all_flows.extend(extract_flows(root, xml_file))
        all_vm.extend(extract_vm_queues(root, xml_file, parents))
    
    result = {
        'endpoints': all_endpoints,
        'sftp_listeners': all_sftp_listeners,
        'ftp_listeners': all_ftp_listeners,
        'anypoint_mq_subscribers': all_anypoint_mq_subscribers,
        'schedulers': all_schedulers,
        'flows': all_flows,
        'vm_queues': all_vm,
    }
    
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()