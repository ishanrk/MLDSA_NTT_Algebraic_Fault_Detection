"""Parser controls use synthetic samples only, never physical evidence."""
import json
import tempfile
import unittest
from pathlib import Path

from report import OPS, ROOT, STACK_OPS, observations, parse_observations, statistics_for, summarize


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'synthetic.jsonl'
        self.counts = {op: 3 for op in OPS}
        self.records = [{'op': 'overhead', 'sample': 0, 'cycles': 7}]
        self.records += [{'op': op, 'sample': i, 'cycles': value}
                         for op in OPS for i, value in enumerate((30, 10, 20))]
        self.records += [{'op': op, 'stack_bytes': 64} for op in STACK_OPS]

    def parse(self, records):
        self.path.write_text(''.join(json.dumps(row) + '\n' for row in records))
        return observations(self.path, self.counts)

    def test_complete_accounting_and_statistics(self):
        data = self.parse(self.records)
        self.assertEqual(data['timer_overhead_cycles'], 7)
        for op in OPS:
            self.assertEqual(data['cycles'][op], {'samples': 3, 'minimum': 10,
                             'median': 20, 'maximum': 30, 'p95_nearest_rank': 30})
        self.assertEqual(statistics_for([1, 2, 3, 4])['median'], 2.5)

    def test_rejected_incomplete_or_invalid_records(self):
        faults = [self.records[1:], self.records[:-1],
                  self.records[:1] + self.records[2:],
                  self.records + [self.records[1]],
                  self.records + [self.records[0]],
                  self.records + [self.records[-1]],
                  self.records + [{'op': 'unknown', 'sample': 0, 'cycles': 1}],
                  self.records + [{'op': 'sign', 'sample': 4, 'cycles': 2**32}],
                  self.records + [{'op': 'sign', 'sample': -1, 'cycles': 12}],
                  self.records + [{'op': 'sign', 'sample': 4, 'cycles': False}],
                  self.records + [{'op': 'sign', 'sample': 4, 'cycles': 0}]]
        for rows in faults:
            with self.subTest(rows=rows[-1]):
                with self.assertRaises(ValueError):
                    self.parse(rows)

    def test_emulator_text_is_rejected(self):
        self.path.write_text('DWT UNAVAILABLE\n')
        with self.assertRaises(ValueError):
            observations(self.path, self.counts)

    def test_pending_template_cannot_publish(self):
        with self.assertRaisesRegex(ValueError, 'still pending'):
            summarize(ROOT / 'hardware/run.template.json', ROOT / 'bench/comparison.json')

    def test_full_calibration_raw_values_and_stack_samples(self):
        rows = [{'op': 'overhead', 'sample': i, 'cycles': value}
                for i, value in enumerate((7, 9, 8))]
        rows += [{'op': op, 'sample': i, 'cycles': value, 'raw_cycles': value + 7}
                 for op in OPS for i, value in enumerate((30, 10, 20))]
        rows += [{'op': op, 'sample': i, 'stack_bytes': value}
                 for op in STACK_OPS for i, value in enumerate((64, 128, 96))]
        rows += [{'event': 'transcript', 'shake256': 'a' * 64}]
        encode = lambda values: [json.dumps(row) for row in values]
        data = parse_observations(encode(rows), self.counts, 3)
        self.assertEqual(data['timer_overhead_statistics']['samples'], 3)
        self.assertEqual(data['stack_bytes']['sign'], 128)
        self.assertEqual(data['stack_statistics']['sign']['samples'], 3)
        bad = [dict(row) for row in rows]
        bad[3]['cycles'] += 1
        with self.assertRaisesRegex(ValueError, 'timer correction'):
            parse_observations(encode(bad), self.counts, 3)
        for index in (0, 3, len(rows) - 2, len(rows) - 1):
            with self.subTest(missing=index):
                with self.assertRaises(ValueError):
                    parse_observations(encode(rows[:index] + rows[index + 1:]), self.counts, 3)


if __name__ == '__main__':
    unittest.main()
