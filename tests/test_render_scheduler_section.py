import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'generate-report.py'
SPEC = importlib.util.spec_from_file_location('generate_report', SCRIPT_PATH)
GENERATE_REPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATE_REPORT)


class RenderSchedulerSectionTests(unittest.TestCase):
    def test_resolves_cron_per_environment_and_omits_frequency_column(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            properties_dir = Path(temp_dir) / 'src' / 'main' / 'resources' / 'properties'
            properties_dir.mkdir(parents=True)
            for environment, cron in (
                ('sit', '0 0 8 * * ?'),
                ('uat', '0 0 9 * * ?'),
                ('prod', '0 0 10 * * ?'),
            ):
                (properties_dir / f'{environment}.yaml').write_text(
                    f"cron:\n  daily: '{cron}'\n  timezone: Asia/Singapore\n",
                    encoding='utf-8',
                )

            environments = GENERATE_REPORT.load_environment_properties(Path(temp_dir))

        section = GENERATE_REPORT.render_scheduler_section(
            [{
                'name': 'Daily job',
                'flow': 'scheduled-flow',
                'cron_expression': '${cron.daily}',
                'frequency': '10000',
                'timezone': '${cron.timezone}',
                'source_file': 'src/main/mule/scheduler.xml',
            }],
            environments,
        )

        self.assertIn('<h3>SIT</h3>', section)
        self.assertIn('<h3>UAT</h3>', section)
        self.assertIn('<h3>PROD</h3>', section)
        self.assertIn('<code>0 0 8 * * ?</code>', section)
        self.assertIn('<code>0 0 9 * * ?</code>', section)
        self.assertIn('<code>0 0 10 * * ?</code>', section)
        self.assertIn('<code>Asia/Singapore</code>', section)
        self.assertNotIn('${cron.daily}', section)
        self.assertNotIn('<th>Frequency</th>', section)
        self.assertNotIn('10000', section)


if __name__ == '__main__':
    unittest.main()
