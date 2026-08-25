"""Reporting integration controls mock device validation; no physical evidence."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config import PLAN_SHA256, PROFILES, ROOT, VARIANTS
from protocol import decode
from report import summarize


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name) / 'synthetic'
        source = ROOT / 'build/hardware-offline/NUCLEO-F411RE'
        shutil.copytree(source, self.folder)
        self.manifest = self.folder / 'run.json'
        self.data = json.loads(self.manifest.read_text())
        self.data.update(status='measured', physical_board=True)
        self.data['metadata'].update(st_link_method='synthetic test fixture',
                                     serial_method='synthetic test fixture',
                                     intervals_below_counter_wrap_confirmed=True,
                                     counter_wrap_guard_frequency_hz=16000000 * 1.1,
                                     capture_seconds={f'{v}-{k}': 1.0 for v in VARIANTS for k in ('compact', 'bench')})
        for variant, files in self.data['variants'].items():
            ready = {'event': 'ready', 'board': 'NUCLEO-F411RE', 'mcu': PROFILES['NUCLEO-F411RE']['mcu'],
                     'variant': variant, 'kind': 'compact', 'plan_sha256': PLAN_SHA256, 'synthetic': True}
            lines = [json.dumps(ready)] + files['expected_compact_cases'] + [json.dumps({'event': 'done', 'exit_code': 0})]
            (self.folder / files['compact_log']).write_text('\n'.join(lines) + '\n')
            shutil.copy2(ROOT / f'build/hardware-offline/gcc-{variant}-synthetic.txt',
                         self.folder / files['benchmark_log'])
        self.save()

    def save(self):
        self.manifest.write_text(json.dumps(self.data))

    def simulated_decode(self, text, board, variant, kind):
        ready, lines = decode(text, board, variant, kind, synthetic=True)
        ready.update(cpuid=0x410fc241, dbg_idcode=0x431, uid0=1, uid1=2, uid2=3)
        return ready, lines

    def test_complete_statistics_and_correction(self):
        with patch('report.decode', side_effect=self.simulated_decode):
            data = summarize(self.manifest)
        for row in data['variants'].values():
            self.assertEqual(row['cycles']['sign']['samples'], 101)
            self.assertEqual(row['cycles']['sign']['median'], 997)
            self.assertEqual(row['cycles']['sign']['overhead_percent'], 0)
            self.assertEqual(row['timer_overhead_statistics']['samples'], 101)
            self.assertEqual(row['stack_statistics']['sign']['samples'], 101)

    def test_real_path_refuses_synthetic_device_records(self):
        with self.assertRaisesRegex(ValueError, 'synthetic'):
            summarize(self.manifest)

    def test_swapped_variant_images_rejected(self):
        files = self.data['variants']
        files['prior']['benchmark_sha256'] = files['baseline']['benchmark_sha256']
        files['prior']['benchmark_elf'] = files['baseline']['benchmark_elf']
        self.save()
        with patch('report.decode', side_effect=self.simulated_decode):
            with self.assertRaisesRegex(ValueError, 'variant images'):
                summarize(self.manifest)

    def test_changed_output_transcript_rejected(self):
        path = self.folder / self.data['variants']['our']['benchmark_log']
        lines = path.read_text().splitlines()
        for i, line in enumerate(lines):
            if '"event":"transcript"' in line:
                lines[i] = json.dumps({'event': 'transcript', 'shake256': 'a' * 64})
        path.write_text('\n'.join(lines) + '\n')
        with patch('report.decode', side_effect=self.simulated_decode):
            with self.assertRaisesRegex(ValueError, 'different key/signature transcripts'):
                summarize(self.manifest)

    def test_counter_wrap_guard_rejected(self):
        self.data['metadata']['capture_seconds']['baseline-bench'] = 300.0
        self.save()
        with self.assertRaisesRegex(ValueError, 'wrap bound'):
            summarize(self.manifest)


if __name__ == '__main__':
    unittest.main()
