import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'extract-endpoints.py'
SPEC = importlib.util.spec_from_file_location('extract_endpoints', SCRIPT_PATH)
EXTRACT_ENDPOINTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXTRACT_ENDPOINTS)


class ExtractAnypointMqSubscribersTests(unittest.TestCase):
    def test_ignores_subscriber_inside_xml_comment(self):
        xml = """<?xml version="1.0"?>
<mule xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:anypoint-mq="http://www.mulesoft.org/schema/mule/anypoint-mq">
    <!--
    <flow name="commented-flow">
        <anypoint-mq:subscriber destination="commented-queue" />
    </flow>
    -->
    <flow name="active-flow">
        <anypoint-mq:subscriber destination="active-queue" />
        <anypoint-mq:publish destination="published-queue" />
    </flow>
    <flow name="publisher-only-flow">
        <anypoint-mq:publish destination="another-published-queue" />
    </flow>
</mule>
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            xml_path = Path(temp_dir) / 'mule-config.xml'
            xml_path.write_text(xml, encoding='utf-8')
            root = EXTRACT_ENDPOINTS.parse_xml_file(xml_path)

        parents = {child: parent for parent in root.iter() for child in parent}
        subscribers = EXTRACT_ENDPOINTS.extract_anypoint_mq_subscribers(
            root, xml_path, parents
        )

        self.assertEqual(len(subscribers), 1)
        self.assertEqual(subscribers[0]['destination'], 'active-queue')
        self.assertEqual(subscribers[0]['flow'], 'active-flow')

    def test_excludes_publish_operations_from_subscriber_count(self):
        xml = """<?xml version="1.0"?>
<mule xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:anypoint-mq="http://www.mulesoft.org/schema/mule/anypoint-mq">
    <flow name="subscriber-flow">
        <anypoint-mq:subscriber destination="subscribed-queue" />
        <anypoint-mq:publish destination="published-queue" />
    </flow>
    <flow name="publisher-only-flow">
        <anypoint-mq:publish destination="another-published-queue" />
    </flow>
</mule>
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            xml_path = Path(temp_dir) / 'mule-config.xml'
            xml_path.write_text(xml, encoding='utf-8')
            root = EXTRACT_ENDPOINTS.parse_xml_file(xml_path)

        parents = {child: parent for parent in root.iter() for child in parent}
        subscribers = EXTRACT_ENDPOINTS.extract_anypoint_mq_subscribers(
            root, xml_path, parents
        )

        self.assertEqual(len(subscribers), 1)
        self.assertEqual(subscribers[0]['destination'], 'subscribed-queue')
        self.assertEqual(subscribers[0]['flow'], 'subscriber-flow')


if __name__ == '__main__':
    unittest.main()
