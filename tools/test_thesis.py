#!/usr/bin/env python3
"""Check refusal of incomplete evidence and preservation of pending fields."""
import copy
import importlib.util
import json
import unittest

from render_thesis import OPS, ROOT, tables, validate


def fixture():
    return {'schema_version': 1, 'status': 'available_evidence_passed',
            'stages': {'test': {'status': 'passed'}},
            'host': {mode: {'status': 'passed', 'official_variants': ['baseline', 'prior', 'our'],
                           'polynomial_seed': 132164, 'polynomial_random_pairs': 10000,
                           'negative_cases': {'baseline': 0, 'prior': 0, 'our': 0}}
                     for mode in ('gcc', 'clang', 'asan', 'ubsan')},
            'comparison': json.loads((ROOT / 'bench/comparison.json').read_text()),
            'offline': json.loads((ROOT / 'bench/offline_cortexm4.json').read_text()),
            'physical': {'status': 'pending', 'physical_board': False},
            'formal': {group: json.loads((ROOT / f'verify/results_{group}.json').read_text())
                       for group in ('arithmetic', 'checkers')},
            'certificates': {variant: json.loads((ROOT / f'docs/{variant}_certificate.json').read_text())
                             for variant in ('prior', 'our')},
            'nist': {'selected_cases': {}}}


class ThesisTests(unittest.TestCase):
    def test_operation_names_match_the_acquisition_protocol(self):
        spec = importlib.util.spec_from_file_location('physical_config', ROOT / 'hardware/config.py')
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)
        self.assertEqual(OPS, config.OPS)

    def test_pending_is_not_zero_or_a_synthetic_measurement(self):
        groups = tables(fixture())
        for name, _, _, rows in groups:
            if name.startswith('performance_'):
                self.assertTrue(all(value == 'pending' for row in rows for value in row[1:]))
            if name == 'overhead':
                self.assertTrue(all(row[-1] == 'pending' for row in rows))

    def test_failed_certificate_and_proof_are_refused(self):
        data = fixture()
        data['certificates']['our']['zero_determinants'] = 1
        with self.assertRaises(ValueError):
            validate(data)
        data = fixture()
        data['formal']['checkers']['proofs'][0]['unwinding_assertions_enabled'] = False
        with self.assertRaises(ValueError):
            validate(data)

    def test_partial_run_and_physical_claim_are_refused(self):
        original = fixture()
        for alter in (
            lambda data: data['stages']['test'].update(status='failed'),
            lambda data: data['host'].pop('asan'),
            lambda data: data['physical'].update(cycles=0),
            lambda data: data['physical'].update(physical_board=True),
            lambda data: data['certificates'].pop('prior'),
        ):
            data = copy.deepcopy(original)
            alter(data)
            with self.assertRaises(ValueError):
                validate(data)


if __name__ == '__main__':
    unittest.main()
