#!/usr/bin/env python3
"""Check counter-result integrity using the saved experimental observations."""
import copy
import json
import unittest

from qemu_benchmark import OPS, ROOT, parse


def observations():
    data = json.loads((ROOT / 'bench/qemu_benchmark.json').read_text())
    sample_count = data['samples_per_operation']
    source = data['configurations']['o2']['variants']['baseline']
    labels = [('control_empty', [source['correction']]),
              ('control_loop', [source['correction'] + source['counter_control_delta']]),
              ('overhead', source['marker_overhead_samples'])]
    labels += [(op, source['operations'][op]['raw_instructions']) for op in OPS]
    rows, interval = [], 0
    for op, counts in labels:
        for sample, count in enumerate(counts):
            rows += [{'kind': 'count', 'interval': interval, 'instructions': count},
                     {'kind': 'region', 'op': op, 'sample': sample, 'interval': interval}]
            interval += 1
    rows += [{'kind': 'result', 'variant': 'baseline', 'status': 'passed',
              'transcript_shake256': source['output_transcript_shake256']},
             {'kind': 'counter_done', 'intervals': interval, 'failed': False}]
    return rows, sample_count, source


def encode(rows):
    return '\n'.join(json.dumps(row) for row in rows)


class CounterTests(unittest.TestCase):
    def test_saved_observations_preserve_all_counts_and_statistics(self):
        rows, sample_count, source = observations()
        result = parse(encode(rows), 'baseline', sample_count)
        for op in OPS:
            expected = {key: value for key, value in source['operations'][op].items()
                        if key not in ('overhead_percent', 'change_from_prior_percent')}
            self.assertEqual(result['operations'][op], expected)

    def test_missing_duplicate_and_failed_counter_are_refused(self):
        rows, sample_count, _ = observations()
        mutations = (rows[1:], rows + [rows[0]])
        for mutated in mutations:
            with self.assertRaises(ValueError):
                parse(encode(mutated), 'baseline', sample_count)
        mutated = copy.deepcopy(rows)
        mutated[-1]['failed'] = True
        with self.assertRaises(ValueError):
            parse(encode(mutated), 'baseline', sample_count)

    def test_control_and_variant_mismatch_are_refused(self):
        rows, sample_count, _ = observations()
        altered = copy.deepcopy(rows)
        altered[2]['instructions'] += 1
        with self.assertRaises(ValueError):
            parse(encode(altered), 'baseline', sample_count)
        with self.assertRaises(ValueError):
            parse(encode(rows), 'prior', sample_count)


if __name__ == '__main__':
    unittest.main()
