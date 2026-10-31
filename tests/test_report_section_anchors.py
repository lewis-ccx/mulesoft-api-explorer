import importlib.util
import unittest
from html.parser import HTMLParser
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'generate-report.py'
SPEC = importlib.util.spec_from_file_location('generate_report', SCRIPT_PATH)
GENERATE_REPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATE_REPORT)


class ReportAnchorParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.anchor_targets = set()
        self.back_to_top = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if 'id' in attributes:
            self.ids.add(attributes['id'])
        if tag == 'a' and attributes.get('href', '').startswith('#'):
            self.anchor_targets.add(attributes['href'][1:])
        if tag == 'a' and 'back-to-top' in attributes.get('class', '').split():
            self.back_to_top.append(attributes)


class ReportSectionAnchorsTests(unittest.TestCase):
    def test_summary_cards_link_to_all_sections(self):
        html = GENERATE_REPORT.render_html(
            project_info={
                'name': 'sample-api',
                'path': 'C:\\sample-api',
                'mule_version': '4.9',
                'packaging': 'mule-application',
                'java_version': '17',
                'artifact_min_mule': '4.9',
            },
            endpoints={
                'endpoints': [],
                'sftp_listeners': [],
                'ftp_listeners': [],
                'anypoint_mq_subscribers': [],
                'flows': [],
                'schedulers': [],
                'vm_queues': [],
            },
            environments=[('sit', {})],
            config_files=[],
            property_files=[],
            project_name='sample-api',
        )
        parser = ReportAnchorParser()
        parser.feed(html)

        expected = {
            'http-endpoints',
            'apikit-generated-flows',
            'sftp-listeners',
            'ftp-listeners',
            'anypoint-mq-subscribers',
            'schedulers',
        }
        self.assertEqual(parser.anchor_targets, expected | {'top'})
        self.assertTrue(expected.issubset(parser.ids))
        self.assertIn('top', parser.ids)
        self.assertEqual(len(parser.back_to_top), 1)
        self.assertEqual(parser.back_to_top[0].get('href'), '#top')
        self.assertEqual(parser.back_to_top[0].get('aria-label'), 'Back to top')
        self.assertIn('visibility: hidden; opacity: 0; pointer-events: none;', html)
        self.assertIn('.back-to-top.is-visible', html)
        self.assertIn('window.scrollY > 0', html)
        self.assertIn('window.addEventListener(\'scroll\', updateBackToTopVisibility', html)


if __name__ == '__main__':
    unittest.main()
