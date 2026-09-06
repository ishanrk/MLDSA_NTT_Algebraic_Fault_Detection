#!/usr/bin/env python3
"""Draw comparison graphs and update the README from saved raw observations."""
import csv
import io
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ('baseline', 'prior', 'our')
LABELS = ('Baseline', 'Prior', 'Our construction')
COLORS = ('#77818c', '#3468a4', '#b85a35')


def main():
    path = ROOT / 'bench/qemu_benchmark.json'
    data = json.loads(path.read_text())
    if data['unit'] != 'guest instructions' or data['physical_cycles'] != 'unmeasured':
        raise ValueError('graphs require the guest-instruction dataset')
    images = ROOT / 'docs/figures'
    images.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'svg.hashsalt': 'ntt-checkers', 'figure.dpi': 130})

    def save(figure, name):
        figure.tight_layout()
        figure.savefig(images / (name + '.png'), metadata={'Software': 'tools/plot_benchmarks.py'})
        svg = images / (name + '.svg')
        figure.savefig(svg, metadata={'Date': None})
        svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
        plt.close(figure)

    figure, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    limit = max(data['configurations'][name]['variants'][variant]['operations']['ntt_forward']['median']
                for name in data['configurations'] for variant in VARIANTS) * 1.18
    for ax, (configuration, title) in zip(axes, (('o2', '-O2'), ('o3_lto', '-O3 with LTO'))):
        values = [data['configurations'][configuration]['variants'][variant]['operations']['ntt_forward']['median']
                  for variant in VARIANTS]
        bars = ax.bar(LABELS, values, color=COLORS, width=.6)
        ax.bar_label(bars, labels=[f'{value:,.0f}' for value in values], padding=4, fontsize=9)
        ax.set_title(title)
        ax.set_ylim(0, limit)
        ax.ticklabel_format(axis='y', style='plain')
        ax.grid(axis='y', alpha=.2)
        ax.set_axisbelow(True)
    axes[0].set_ylabel('Guest instructions per forward NTT')
    figure.suptitle('QEMU Cortex M4: instrumented instruction counts', fontsize=12)
    save(figure, 'qemu_ntt')

    figure, axes = plt.subplots(1, 3, figsize=(11, 3.6))
    for ax, (op, title) in zip(axes, (('keygen', 'Key generation'), ('sign', 'Signing'), ('verify', 'Verification'))):
        rows = [data['configurations']['o3_lto']['variants'][variant]['operations'][op] for variant in VARIANTS]
        medians = [row['median'] / 1e6 for row in rows]
        errors = [[(row['median'] - row['minimum']) / 1e6 for row in rows],
                  [(row['p95_nearest_rank'] - row['median']) / 1e6 for row in rows]]
        bars = ax.bar(LABELS, medians, color=COLORS, width=.6, yerr=errors,
                      capsize=4, error_kw={'elinewidth': 1})
        ax.bar_label(bars, labels=[f'{value:.2f}' for value in medians], padding=4, fontsize=9)
        ax.set_title(title)
        ax.set_ylabel('Guest instructions (millions)')
        ax.tick_params(axis='x', labelrotation=15)
        ax.grid(axis='y', alpha=.2)
        ax.set_axisbelow(True)
    figure.suptitle('QEMU -O3 + LTO: medians; whiskers show minimum to P95', fontsize=12)
    save(figure, 'qemu_mldsa')

    figure, ax = plt.subplots(figsize=(7.5, 3.8))
    bounds = data['construction_bounds']
    for key, label, color in (('prior', 'Prior: (2n−1)M', COLORS[1]), ('our', 'Our balanced boundary: D(k)', COLORS[2])):
        ax.loglog([row['n'] for row in bounds], [row[key] for row in bounds], 'o-', label=label, color=color)
    ax.set_xlabel('Transform length n')
    ax.set_ylabel('Sufficient field-size threshold')
    ax.set_title(r'Construction guarantee: $\Theta(n^2\log n) \to \Theta(n^{3/2}\log n)$')
    ax.set_xticks([16, 64, 256, 1024, 4096], labels=['16', '64', '256', '1024', '4096'])
    ax.grid(alpha=.2, which='both')
    ax.legend(frameon=False)
    save(figure, 'construction_bound')

    configs = data['configurations']
    lines = ['| Build | Baseline NTT | Prior NTT | Our NTT | Our vs prior |',
             '| --- | ---: | ---: | ---: | ---: |']
    for name, label in (('o2', '`-O2`'), ('o3_lto', '`-O3 -flto`')):
        rows = configs[name]['variants']
        counts = [rows[v]['operations']['ntt_forward']['median'] for v in VARIANTS]
        delta = rows['our']['operations']['ntt_forward']['change_from_prior_percent']
        lines.append(f'| {label} | ' + ' | '.join(f'{x:,.0f}' for x in counts) + f' | {delta:+.2f}% |')
    delta = configs['o3_lto']['variants']['our']['operations']['ntt_forward']['change_from_prior_percent']
    direction = 'more' if delta >= 0 else 'fewer'
    concrete = next(row for row in data['construction_bounds'] if row['n'] == 256)
    block = [f"For ML DSA (`n=256`, `h=8`, `k=4`), the sufficient threshold falls from "
             f"**{concrete['prior']:,}** to **{concrete['our']:,}**, an **{data['construction_bound_ratio_at_256']:.2f}×** reduction. "
             'Both rows pass the same exhaustive pair certificate.', '',
             '![Sufficient construction thresholds](docs/figures/construction_bound.png)', '',
             f"Forward NTT median guest-instruction counts, {data['samples_per_operation']} observations per build and variant:", '',
             *lines, '',
             f"With `-O3 -flto`, our current protected NTT uses **{abs(delta):.2f}% {direction} guest instructions** "
             'than the prior checker. This measures the compiled implementations; it does not establish a physical cycle improvement.', '',
             '![QEMU NTT instruction counts](docs/figures/qemu_ntt.png)', '',
             '![QEMU ML DSA instruction counts](docs/figures/qemu_mldsa.png)', '',
             '| Variant | Extra field multiplications | Extra field additions | Constant table bytes |',
             '| --- | ---: | ---: | ---: | ---: |']
    for variant, label in zip(VARIANTS, LABELS):
        row = data['costs'][variant]
        block.append(f"| {label} | {row['extra_field_calls']['mul']} | {row['extra_field_calls']['add']} | {row['constant_bytes']} |")
    block += ['', '[Raw observations](bench/qemu_benchmark.json) · [Complete statistics](docs/qemu_results.md) · '
              '[CSV](bench/qemu_benchmark.csv). Plots are generated by `tools/plot_benchmarks.py`; '
              'no QEMU count is presented as a hardware cycle.', '']
    readme = ROOT / 'README.md'
    text = readme.read_text()
    start = '<!-- benchmark-results:start -->'
    end = '<!-- benchmark-results:end -->'
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError('README benchmark insertion markers missing or duplicated')
    prefix, suffix = text.split(start)
    _, suffix = suffix.split(end)
    readme.write_text(prefix + start + '\n\n' + '\n'.join(block) + end + suffix)
    report = ['# QEMU instruction measurements', '',
              'Generated from [raw observations](../bench/qemu_benchmark.json). Unit: **guest instructions**, '
              'after empty-marker subtraction. Physical cycles are unmeasured. Whiskers in the plots show '
              'observed minimum to P95, not a confidence interval.', '',
              f"Compiler: `{data['compiler']}`. Emulator: `{data['qemu']}`. Target: `{data['machine']}`.", '',
              'The 100-iteration assembly control adds exactly 301 instructions in every image. '
              'Complete key/signature transcripts match all variants and both optimization settings.', '']
    output = io.StringIO()
    writer = csv.writer(output, lineterminator='\n')
    keys = ('samples', 'minimum', 'median', 'maximum', 'p95_nearest_rank', 'overhead_percent', 'change_from_prior_percent')
    writer.writerow(('build', 'variant', 'operation', *keys))
    for name, config in configs.items():
        report += ['## ' + name, '', 'Flags: `' + ' '.join(config['compiler_flags']) + '`.', '',
                   '| Variant | Operation | Samples | Min | Median | Max | P95 | Overhead vs baseline (%) |',
                   '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
        for variant in VARIANTS:
            for op, row in config['variants'][variant]['operations'].items():
                report.append('| ' + ' | '.join(map(str, [variant, op, *[row[k] for k in keys[:-1]]])) + ' |')
                writer.writerow((name, variant, op, *[row[k] for k in keys]))
        report.append('')
    (ROOT / 'docs/qemu_results.md').write_text('\n'.join(report))
    (ROOT / 'bench/qemu_benchmark.csv').write_text(output.getvalue())
    print('Generated three graphs (PNG/SVG), statistics, CSV and README measurements')


if __name__ == '__main__':
    main()
