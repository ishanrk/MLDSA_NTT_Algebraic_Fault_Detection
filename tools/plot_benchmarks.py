#!/usr/bin/env python3
"""Draw comparison graphs and update the README from saved raw observations."""
import csv
import io
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ('baseline', 'prior', 'our')
LABELS = ('Baseline', 'Abdelmonem et al.', 'Current method')
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

    figure, ax = plt.subplots(figsize=(8, 4))
    for offset, configuration, title, color in ((-.18, 'o2', 'O2', COLORS[0]),
                                               (.18, 'o3_lto', 'O3 + LTO', COLORS[1])):
        values = [data['configurations'][configuration]['variants'][variant]['operations']['ntt_forward']['median'] / 1000
                  for variant in VARIANTS]
        bars = ax.bar([i + offset for i in range(3)], values, color=color, width=.34, label=title)
        ax.bar_label(bars, labels=[f'{value:.1f}' for value in values], padding=4, fontsize=10)
    ax.set_xticks(range(3), LABELS)
    ax.set_xlabel('Method')
    ax.set_ylabel('Instruction count (thousands)')
    ax.set_title('Forward NTT on QEMU Cortex M4')
    limit = max(config['variants'][variant]['operations']['ntt_forward']['median'] / 1000
                for config in data['configurations'].values() for variant in VARIANTS)
    ax.set_ylim(0, limit * 1.2)
    ax.yaxis.set_major_locator(MaxNLocator(5, integer=True))
    ax.grid(axis='y', alpha=.2)
    ax.set_axisbelow(True)
    ax.legend(frameon=False)
    save(figure, 'qemu_ntt')

    figure, axes = plt.subplots(1, 3, figsize=(11, 3.6))
    for ax, (op, title) in zip(axes, (('keygen', 'Key generation'), ('sign', 'Signing'), ('verify', 'Verification'))):
        rows = [data['configurations']['o3_lto']['variants'][variant]['operations'][op] for variant in VARIANTS]
        medians = [row['median'] / 1e6 for row in rows]
        bars = ax.bar(('Baseline', 'Abdelmonem\net al.', 'Current'), medians, color=COLORS, width=.6)
        ax.bar_label(bars, labels=[f'{value:.2f}' for value in medians], padding=4, fontsize=9)
        ax.set_title(title)
        ax.set_ylabel('Instruction count (millions)')
        ax.set_xlabel('Method')
        ax.set_ylim(0, max(medians) * 1.18)
        ax.yaxis.set_major_locator(MaxNLocator(4, integer=True))
        ax.grid(axis='y', alpha=.2)
        ax.set_axisbelow(True)
    figure.suptitle('ML-DSA-44 on QEMU: O3 + LTO medians', fontsize=12)
    save(figure, 'qemu_mldsa')

    concrete = next(row for row in data['construction_bounds'] if row['n'] == 256)
    figure, ax = plt.subplots(figsize=(6, 4))
    values = [concrete[key] / 1000 for key in ('prior', 'our')]
    bars = ax.bar(LABELS[1:], values, color=COLORS[1:], width=.5)
    ax.bar_label(bars, labels=[f'{value:,.1f}' for value in values], padding=5)
    ax.set_xlabel('Method')
    ax.set_ylabel('Sufficient field bound (thousands)')
    ax.set_title('Construction bound at n = 256')
    ax.set_ylim(0, max(values) * 1.18)
    ax.yaxis.set_major_locator(MaxNLocator(5, integer=True))
    ax.grid(axis='y', alpha=.2)
    ax.set_axisbelow(True)
    save(figure, 'construction_bound')

    configs = data['configurations']
    lines = ['| Build | Baseline | Abdelmonem et al. | Current method | Current vs Abdelmonem et al. |',
             '| --- | ---: | ---: | ---: | ---: |']
    for name, label in (('o2', '`-O2`'), ('o3_lto', '`-O3 -flto`')):
        rows = configs[name]['variants']
        counts = [rows[v]['operations']['ntt_forward']['median'] for v in VARIANTS]
        delta = rows['our']['operations']['ntt_forward']['change_from_prior_percent']
        lines.append(f'| {label} | ' + ' | '.join(f'{x:,.0f}' for x in counts) + f' | {delta:+.2f}% |')
    delta = configs['o3_lto']['variants']['our']['operations']['ntt_forward']['change_from_prior_percent']
    direction = 'more' if delta >= 0 else 'fewer'
    certificate = json.loads((ROOT / 'docs/our_certificate.json').read_text())
    construction = [f"For `n={concrete['n']}`, `h={concrete['h']}` and `k={concrete['k']}`, "
                    f"the generator verifies `M={concrete['M']}`, `K={concrete['K']}`, "
                    f"`D={concrete['our']}` and `q={certificate['q']}>D`.", '',
                    '| Method | Sufficient threshold |', '| --- | ---: |',
                    f"| Abdelmonem et al. | {concrete['prior']:,} |", f"| Current method | {concrete['our']:,} |", '',
                    f"The sufficient threshold is **{data['construction_bound_ratio_at_256']:.2f} times smaller**. "
                    f"Both methods certify all **{certificate['checked_pairs']:,}** location pairs with zero determinant failures.", '',
                    '![Construction bound at transform length 256](docs/figures/construction_bound.png)', '']
    first = configs['o2']['variants']['our']['operations']['ntt_forward']['median']
    optimized = configs['o3_lto']['variants']['our']['operations']['ntt_forward']['median']
    reduction = 100 * (1 - optimized / first)
    block = [f"Median forward NTT instruction count, `{data['samples_per_operation']}` samples per build:", '',
             *lines, '',
             f"At `-O3 -flto`, my checker uses **{reduction:.2f}% fewer NTT instructions** than its `-O2` build "
             f"and **{abs(delta):.2f}% {direction}** than Abdelmonem et al.", '',
             '![Forward NTT instruction counts](docs/figures/qemu_ntt.png)', '',
             'Full ML-DSA-44 overhead at `-O3 -flto`, relative to baseline median instruction count:', '',
             '| Operation | Abdelmonem et al. | Current method |', '| --- | ---: | ---: |']
    for operation, label in (('keygen', 'Key generation'), ('sign', 'Signing'), ('verify', 'Verification')):
        rows = configs['o3_lto']['variants']
        overheads = [rows[v]['operations'][operation]['overhead_percent'] for v in VARIANTS[1:]]
        block.append(f'| {label} | ' + ' | '.join(f'{value:.2f}%' for value in overheads) + ' |')
    costs = data['costs']
    block += ['', '![ML-DSA instruction counts](docs/figures/qemu_mldsa.png)', '',
              f"Each protected NTT adds `{costs['prior']['extra_field_calls']['mul']}` field multiplications "
              f"for Abdelmonem et al. and `{costs['our']['extra_field_calls']['mul']}` for my checker. "
              f"Both add `{costs['our']['extra_field_calls']['add']}` field additions. "
              '[Operation and storage counts](bench/comparison.json).', '',
              '[Raw observations](bench/qemu_benchmark.json), [all statistics](docs/qemu_results.md) and '
              '[CSV](bench/qemu_benchmark.csv). Python generates these tables and graphs from the raw record.', '']
    readme = ROOT / 'README.md'
    text = readme.read_text()
    for name, content in (('construction-results', construction), ('benchmark-results', block)):
        start, end = f'<!-- {name}:start -->', f'<!-- {name}:end -->'
        if text.count(start) != 1 or text.count(end) != 1:
            raise ValueError('README insertion markers missing or duplicated')
        prefix, suffix = text.split(start)
        _, suffix = suffix.split(end)
        text = prefix + start + '\n\n' + '\n'.join(content) + end + suffix
    readme.write_text(text)
    report = ['# QEMU instruction measurements', '',
              'Generated from [raw observations](../bench/qemu_benchmark.json). Unit: **instruction count**, '
              'after empty marker subtraction. Physical cycles are unmeasured. The plots show medians; '
              'this table retains the complete range and P95.', '',
              f"Compiler: `{data['compiler']}`. Emulator: `{data['qemu']}`. Target: `{data['machine']}`.", '',
              'The 100 iteration assembly control adds exactly 301 instructions in every image. '
              'Complete key/signature transcripts are identical for all methods and both optimization settings.', '']
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
                label = LABELS[VARIANTS.index(variant)]
                report.append('| ' + ' | '.join(map(str, [label, '`' + op + '`', *[row[k] for k in keys[:-1]]])) + ' |')
                writer.writerow((name, variant, op, *[row[k] for k in keys]))
        report.append('')
    (ROOT / 'docs/qemu_results.md').write_text('\n'.join(report))
    (ROOT / 'bench/qemu_benchmark.csv').write_text(output.getvalue())
    print('Generated three graphs (PNG/SVG), statistics, CSV and README measurements')


if __name__ == '__main__':
    main()
