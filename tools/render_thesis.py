#!/usr/bin/env python3
"""Generate thesis tables from one frozen raw result, without measuring anything."""
import argparse
import json
import os
from pathlib import Path

from render_comparison import LABELS, ROOT, latex

OPS = ('ntt_forward', 'ntt_inverse', 'pointwise', 'keygen', 'sign', 'verify')


def validate(data):
    if data['schema_version'] != 1 or data['status'] != 'available_evidence_passed':
        raise ValueError('not a completed available-evidence run')
    if not data['stages'] or any(row['status'] != 'passed' for row in data['stages'].values()):
        raise ValueError('failed or missing regression stages')
    if set(data['host']) != {'gcc', 'clang', 'asan', 'ubsan'}:
        raise ValueError('missing compiler or sanitizer coverage')
    for row in data['host'].values():
        if row['status'] != 'passed' or set(row['official_variants']) != set(LABELS):
            raise ValueError('incomplete host variant coverage')
    for variant, cert in data['certificates'].items():
        locations = cert['modeled_locations']
        failures = [value for key, value in cert.items() if key.startswith('zero_') or
                    key == 'duplicate_normalized_responses']
        if any(failures) or cert['checked_pairs'] != locations * (locations - 1) // 2:
            raise ValueError(f'{variant}: incomplete or failed certificate')
    if set(data['certificates']) != {'prior', 'our'}:
        raise ValueError('missing exact certificate')
    if set(data['formal']) != {'arithmetic', 'checkers'}:
        raise ValueError('missing formal group')
    for record in data['formal'].values():
        if not record['proofs'] or any(job['result'] != 'passed' or not job['unwinding_assertions_enabled']
               for job in record['proofs']):
            raise ValueError('failed formal property or disabled unwinding assertions')
    physical = data['physical']
    if physical['status'] == 'pending':
        if physical.get('physical_board') is not False or any(
                physical.get(key) is not None for key in ('cycles', 'stack_bytes')):
            raise ValueError('pending physical result contains observations')
    elif physical['status'] == 'measured':
        if physical['physical_board'] is not True or set(physical['variants']) != set(LABELS):
            raise ValueError('not validated complete physical evidence')
        for variant in LABELS:
            row = physical['variants'][variant]
            if row['compact_correctness'] != 'passed' or set(row['cycles']) != set(OPS):
                raise ValueError('missing measured operation or physical correctness result')
            for operation in OPS:
                stats = row['cycles'][operation]
                if stats['samples'] != physical['metadata']['sample_counts'][operation]:
                    raise ValueError('incomplete physical samples')
    else:
        raise ValueError('unknown physical status')


def tables(data):
    validate(data)
    groups = []
    physical = data['physical']
    measured = physical['status'] == 'measured'
    overhead = []
    for variant, label in LABELS.items():
        rows = []
        for operation in OPS:
            stats = physical['variants'][variant]['cycles'][operation] if measured else None
            rows.append([operation] + [stats[key] if stats else 'pending' for key in
                         ('samples', 'minimum', 'median', 'maximum', 'p95_nearest_rank')])
            overhead.append([label, operation, stats['overhead_percent'] if stats else 'pending'])
        groups.append(('performance_' + variant, label + ': physical cycle statistics',
                       ['Operation', 'Samples', 'Min', 'Median', 'Max', 'P95'], rows))
    groups.append(('overhead', 'Physical cycle overhead relative to baseline median',
                   ['Variant', 'Operation', 'Overhead (percent)'], overhead))
    memory = []
    profiles = ({physical['metadata']['nucleo_model']: physical} if measured else
                data['offline']['profiles'])
    for board, profile in profiles.items():
        for variant, label in LABELS.items():
            row = profile['variants'][variant]
            memory.append([board, label, row['flash_bytes'], row['static_ram_bytes']] +
                          [row['stack_bytes'][op] if row['stack_bytes'] else 'pending'
                           for op in ('keygen', 'sign', 'verify')])
    groups.append(('memory', 'Reference target linked memory and physical stack high water (bytes)',
                   ['Target', 'Variant', 'Linked flash', 'Static RAM', 'Keygen stack',
                    'Sign stack', 'Verify stack'], memory))
    costs, storage, parameters, failures, identities = [], [], [], [], []
    for variant, label in LABELS.items():
        row = data['comparison']['variants'][variant]
        costs.append([label] + [row['field_calls'][key] for key in ('mul', 'add', 'sub')] +
                     [row['extra_field_calls'][key] for key in ('mul', 'add')])
        storage.append([label, row['checks'], row['stored_coefficients'], row['constant_bytes']])
        if variant != 'baseline':
            cert = data['certificates'][variant]
            parameters.append([label] + [cert[key] for key in ('n', 'q', 'h', 'modeled_locations', 'checked_pairs')] +
                              [cert.get(key, 'N/A') for key in ('k', 'K', 'D')])
            failures.append([label, cert['zero_first_responses'], cert['zero_second_responses'],
                             cert.get('duplicate_normalized_responses', 'not separately recorded'),
                             cert['zero_determinants']])
            identities.append([label, cert['row_identities'], cert['propagation_identity'],
                               cert.get('intermediate_identity', 'N/A')])
    groups.extend([
        ('operations', 'Modular function calls per forward transform',
         ['Variant', 'Total mul', 'Total add', 'Total sub', 'Extra mul', 'Extra add'], costs),
        ('storage', 'Scalar checks and generated coefficient storage',
         ['Variant', 'Checks', 'Stored coefficients', 'Constant bytes'], storage),
        ('certificate_parameters', 'Exact modeled network and certificate parameters',
         ['Variant', 'n', 'q', 'h', 'Locations', 'Pairs', 'k', 'K', 'D'], parameters),
        ('certificate_failures', 'Exact certificate failure counts',
         ['Variant', 'Zero first', 'Zero second', 'Duplicate ratios', 'Zero determinants'], failures),
        ('certificate_identities', 'Exact certificate row and propagation identities',
         ['Variant', 'Row identities', 'Unit propagation', 'Intermediate identity'], identities),
    ])
    summaries = []
    for group, record in data['formal'].items():
        jobs = record['proofs']
        summaries.append([group, record['cbmc'], record['solver'], len(jobs),
                          round(sum(job['seconds'] for job in jobs), 3), 'passed'])
        groups.append(('formal_' + group, 'Focused CBMC properties: ' + group,
                       ['Property', 'Unwind', 'Unwinding checks', 'Result', 'Seconds'],
                       [[job['name'], job['unwind'], 'enabled; passed', job['result'], job['seconds']]
                        for job in jobs]))
    groups.append(('formal_summary', 'Focused portable C verification summary',
                   ['Group', 'CBMC', 'Solver', 'Jobs', 'Seconds', 'Result'], summaries))
    regression = []
    for mode, record in data['host'].items():
        regression.append([mode, record['polynomial_seed'], record['polynomial_random_pairs']] +
                          [record['negative_cases'][variant] for variant in LABELS] + ['passed'])
    groups.append(('regression', 'Final comprehensive host regression',
                   ['Mode', 'Polynomial seed', 'Random pairs', 'Baseline negatives',
                    'Prior negatives', 'Current negatives', 'Result'], regression))
    groups.append(('official_vectors', 'All supported official vectors per applicable variant and build mode',
                   ['Dataset / interface', 'Cases'], [[key, value] for key, value in
                     data['nist']['selected_cases'].items() if not key.endswith(('/valid', '/invalid'))]))
    return groups


def render(data, folder, markdown):
    groups = tables(data)
    folder.mkdir(parents=True, exist_ok=True)
    md = ['# Thesis results from repository evidence', '',
          'Generated from [bench/thesis.json](../bench/thesis.json) by '
          '`python3 tools/render_thesis.py`. Numbers are read from the raw dataset.', '',
          f"Available regression: **passed**, {len(data['stages'])} stages, "
          f"{data['total_seconds']} seconds wall time. Physical status: **{data['physical']['status']}**. "
          'Regression and proof wall times are host reproduction times, not performance measurements.', '',
          f"Run started `{data['started_utc']}`; source base `{data['base_git_commit']}`. "
          'Source digests identify the tested tree, including uncommitted artifact tooling at collection.', '',
          'The physical milestone is incomplete while cycles, stack and physical correctness tests are pending. '
          'Linked flash is ELF text + data; static RAM is ELF data + BSS. Reference builds do not identify '
          'the attached board. Baseline physical overhead also stays pending until measured.', '']
    includes = ['% Generated from bench/thesis.json; requires only standard LaTeX tabular.',
                '% Run from the repository root, or adjust the input paths.']
    filenames = []
    for slug, title, headers, rows in groups:
        md += ['## ' + title, '', '| ' + ' | '.join(headers) + ' |',
               '| ' + ' | '.join(['---'] * len(headers)) + ' |']
        md += ['| ' + ' | '.join('`' + str(value) + '`' if str(value).startswith('NUCLEO-')
                               else str(value) for value in row) + ' |' for row in rows]
        md.append('')
        tex = ['% ' + title, '% Source: bench/thesis.json; physical status: ' + data['physical']['status'],
               r'\begin{tabular}{' + 'l' * len(headers) + '}', r'\hline',
               ' & '.join(map(latex, headers)) + r' \\', r'\hline']
        tex += [' & '.join(map(latex, row)) + r' \\' for row in rows]
        tex += [r'\hline', r'\end{tabular}', '']
        filename = slug + '.tex'
        filenames.append(filename)
        (folder / filename).write_text('\n'.join(tex))
        includes += ['', '% ' + title, '\\input{' + os.path.relpath(folder / filename, ROOT) + '}']
    (folder / 'tables.tex').write_text('\n'.join(includes) + '\n')
    (folder / 'manifest.json').write_text(json.dumps({'raw': 'bench/thesis.json', 'files': filenames}, indent=2) + '\n')
    md += ['## Certificate coefficient digests', '']
    for variant, cert in data['certificates'].items():
        md += [f"{LABELS[variant]}: `{cert['coefficients_sha256']}`.", '']
    md += ['The prior generator verifies distinct normalized ratios internally and enumerates every '
           'determinant, but does not store a separate duplicate ratio counter; the table preserves that '
           'distinction. Both certificates have zero recorded failures.', '',
           'These are exact checks of concrete finite field coefficient conditions. They do not formally '
           'verify the generator or prove the general construction theorem. CBMC verifies portable C '
           'components under the [documented contracts and assumptions](verification.md), with inspected '
           'composition rather than an automatically checked global ML DSA or NTT refinement.', '',
           'The NIST scope is ' + data['nist']['scope'] + '. Keygen, pure signing, verification and prehash '
           'vectors run for all three variants in each of the four host modes. SHAKE, arithmetic and '
           'sampling use shared baseline code; protected compact tests check checksum behavior. '
           'The existing test of 10000 pairs executes once per compiler/sanitizer mode with the recorded seed. '
           'The existing pqcrypto differential suite of 200 cases executes once per variant with GCC.', '',
           'Threat model: at most two additive deviations at modeled forward NTT boundary wires over '
           'the finite field, with trusted checker arithmetic, weights and control flow. Physical Cortex M4 '
           'cycle/stack observations, when collected, establish cost on those inputs; they do not establish '
           'resistance against every physical fault mechanism.', '',
           'Individual LaTeX fragments are in [bench/thesis](../bench/thesis); '
           '`bench/thesis/tables.tex` includes every table. Wrap or resize wide tables in the thesis layout. '
           'No additional LaTeX package is required by the generated fragments.', '',
           'Manual thesis work: integrate the theorem proof and its assumptions; position the result '
           'against related work; explain the cost/construction tradeoff; add board observations and '
           'physical measurement discussion after capture; write the conclusions and institutional formatting.', '']
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text('\n'.join(md))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('raw', nargs='?', type=Path, default=ROOT / 'bench/thesis.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'bench/thesis')
    parser.add_argument('--markdown', type=Path, default=ROOT / 'docs/thesis_results.md')
    args = parser.parse_args()
    render(json.loads(args.raw.read_text()), args.output.resolve(), args.markdown)


if __name__ == '__main__':
    main()
