import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'extract-schedulers.py'
SPEC = importlib.util.spec_from_file_location('extract_schedulers', SCRIPT_PATH)
EXTRACT_SCHEDULERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXTRACT_SCHEDULERS)


class ExtractSchedulersTests(unittest.TestCase):
    def test_extracts_core_scheduler_and_ignores_unrelated_fixed_frequency(self):
        xml = """<?xml version="1.0"?>
<mule xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:doc="http://www.mulesoft.org/schema/mule/documentation">
    <flow name="scheduled-flow">
        <scheduler doc:name="Daily job">
            <scheduling-strategy>
                <cron expression="0 0 8 * * ?" timeZone="Asia/Singapore" />
            </scheduling-strategy>
        </scheduler>
    </flow>
    <flow name="poller-flow">
        <scheduling-strategy>
            <fixed-frequency frequency="10000" />
        </scheduling-strategy>
    </flow>
</mule>
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            xml_path = Path(temp_dir) / 'mule-config.xml'
            xml_path.write_text(xml, encoding='utf-8')
            root = EXTRACT_SCHEDULERS.parse_xml_file(xml_path)

        parents = {child: parent for parent in root.iter() for child in parent}
        schedulers = EXTRACT_SCHEDULERS.extract_schedulers(root, xml_path, parents)

        self.assertEqual(len(schedulers), 1)
        self.assertEqual(schedulers[0]['type'], 'flow-scheduler')
        self.assertEqual(schedulers[0]['name'], 'Daily job')
        self.assertEqual(schedulers[0]['cron_expression'], '0 0 8 * * ?')
        self.assertEqual(schedulers[0]['timezone'], 'Asia/Singapore')
        self.assertEqual(schedulers[0]['flow'], 'scheduled-flow')


if __name__ == '__main__':
    unittest.main()
