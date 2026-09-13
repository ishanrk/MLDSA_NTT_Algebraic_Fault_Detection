#!/usr/bin/env python3
"""Render the same measured rows as Markdown and plain LaTeX tabulars."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = {'baseline': 'Baseline', 'prior': 'Abdelmonem et al.',
          'our': 'Current method'}


def tables(data):
    if data['schema_version'] != 1:
        raise ValueError('unsupported comparison schema')
    costs, sizes, evidence, physical = [], [], [], []
    for name in LABELS:
        row = data['variants'][name]
        label = LABELS[name]
        costs.append([label, row['checks'], row['stored_coefficients'],
                      row['field_calls']['mul'], row['field_calls']['add'],
                      row['extra_field_calls']['mul'], row['extra_field_calls']['add']])
        sizes.append([label, row['constant_bytes']] +
                     [row['arm_image'][key] for key in ('text', 'data', 'bss')])
        cert = row['exact_certificate']
        evidence.append([label, cert['status'], cert.get('checked_pairs', 'N/A'),
                         sum(cert['failure_counts'].values()) if 'failure_counts' in cert else 'N/A',
                         f"{row['formal']['common_jobs']} common + {row['formal']['checker_jobs']} checker",
                         row['qemu']['status']])
        if row['physical']['status'] != 'pending':
            raise ValueError('physical observations require a separate measured comparison')
        physical.append([label] + ['pending'] * 7)
    return [
        ('Forward NTT operations', ['Variant', 'Checks', 'Stored coefficients',
         'Total field mul', 'Total field add', 'Extra field mul', 'Extra field add'], costs),
        ('ARM emulator image sizes (bytes)', ['Variant', 'Constant tables',
         'ARM text', 'ARM data', 'ARM BSS'], sizes),
        ('Implementation evidence', ['Variant', 'Exact certificate', 'Pairs',
         'Certificate failures', 'CBMC jobs passed', 'QEMU correctness'], evidence),
        ('Physical measurements', ['Variant', 'NTT cycles', 'Keygen cycles', 'Sign cycles',
         'Verify cycles', 'Flash bytes', 'Static RAM bytes', 'Stack bytes'], physical),
    ]


def latex(value):
    escapes = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$',
               '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
               '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(escapes.get(c, c) for c in str(value))


def render(data, markdown, tex):
    md = ['# Checker research comparison', '',
          'Generated from [raw results](../bench/comparison.json) by '
          '`python3 tools/render_comparison.py`. Rebuild all evidence with `make comparison`.', '']
    lt = ['% Generated from bench/comparison.json; do not edit numbers.']
    for title, headers, rows in tables(data):
        md += ['## ' + title, '', '| ' + ' | '.join(headers) + ' |',
               '| ' + ' | '.join(['---'] * len(headers)) + ' |']
        md += ['| ' + ' | '.join(map(str, row)) + ' |' for row in rows]
        md.append('')
        lt += ['', '% ' + title, r'\begin{tabular}{l' + 'r' * (len(headers) - 1) + '}',
               r'\hline', ' & '.join(map(latex, headers)) + r' \\', r'\hline']
        lt += [' & '.join(map(latex, row)) + r' \\' for row in rows]
        lt += [r'\hline', r'\end{tabular}']
    variants = data['variants']
    dm = variants['our']['extra_field_calls']['mul'] - variants['prior']['extra_field_calls']['mul']
    db = variants['our']['constant_bytes'] - variants['prior']['constant_bytes']
    md += [
        'Counts are actual modular function calls for one fixed nonzero forward NTT input. '
        'Extra counts subtract baseline calls. Stored coefficients count generated uint32 '
        'table entries; implicit unity weights require no storage. Both defenses have two '
        'scalar equality checks, implemented as four checksum accumulations.', '',
        f'The current checker uses {dm} more field multiplications and '
        f'{db} more table bytes than the Abdelmonem et al. checker. Its improvement is the sufficient '
        'construction field bound; these results make no speedup claim.', '',
        f"ARM compiler: `{data['compiler']}`. Flags: `{data['arm_cflags']}`. "
        f"Linker: `{data['linker']}`. Text includes readonly tables and vectors. "
        'All variants use the same benchmark harness without injection hooks. These '
        'sizes describe the emulator layout, not measured Nucleo flash or RAM.', '',
        'CBMC counts refer to [focused component proofs](../docs/reproduction.md#focused-comparison-and-formal-checks), with shared '
        'arithmetic/layer/loop proofs counted once per applicable variant. There is no '
        'automatically checked global transform or ML DSA refinement. No fault acceptance '
        'uses compositional reasoning and exact row certificates. The general determinant '
        'theorem is not a CBMC result.', '',
        'Both protected variants certify nonzero determinants for every distinct pair '
        'of modeled boundary wires, covering nonzero result errors caused by at most two '
        'additive wire deviations with trusted checker arithmetic, weights and control '
        'flow. Baseline has no such checker guarantee. Physical fault injection has not '
        'been evaluated. QEMU supplies correctness evidence only; physical cycles, '
        'overhead percentages, flash, RAM and stack measurements are pending.', '',
    ]
    for path, content in ((markdown, '\n'.join(md)), (tex, '\n'.join(lt) + '\n')):
        if path is None:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('raw', nargs='?', type=Path, default=ROOT / 'bench/comparison.json')
    p.add_argument('--markdown', type=Path, help='optional Markdown output path')
    p.add_argument('--latex', type=Path, default=ROOT / 'bench/comparison.tex')
    args = p.parse_args()
    render(json.loads(args.raw.read_text()), args.markdown, args.latex)


if __name__ == '__main__':
    main()
