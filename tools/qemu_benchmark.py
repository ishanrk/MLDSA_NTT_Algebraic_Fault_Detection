#!/usr/bin/env python3
"""Compare matched ARM builds using QEMU TCG instruction instrumentation."""
import argparse
import hashlib
import json
import math
import os
import re
import shlex
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
OPS = ('ntt_forward', 'ntt_inverse', 'pointwise', 'keygen', 'sign', 'verify')
VARIANTS = ('baseline', 'prior', 'our')
HEADER_URL = 'https://raw.githubusercontent.com/qemu/qemu/v6.2.0/include/qemu/qemu-plugin.h'
HEADER_SHA256 = '82c233fc6ab1a9649a26b1a4eae69e94ba2452d280bd82076372ea6bd1a0753f'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def executable(variable, name):
    if variable in os.environ:
        return os.environ[variable]
    installed = shutil.which(name)
    if installed:
        return installed
    local = ROOT / 'build/toolchain/root/usr/bin' / name
    if local.exists():
        return str(local)
    raise RuntimeError(f'Install {name} or set {variable}')


def stats(values):
    ordered = sorted(values)
    return {'samples': len(values), 'minimum': ordered[0], 'median': statistics.median(values),
            'maximum': ordered[-1], 'p95_nearest_rank': ordered[math.ceil(.95 * len(values)) - 1]}


def parse(text, variant, samples):
    counts, regions, results, finishes = {}, {}, [], []
    for line in text.splitlines():
        row = json.loads(line)
        kind = row['kind']
        if kind in ('count', 'region'):
            records = counts if kind == 'count' else regions
            index = row['interval']
            if type(index) is not int or index in records:
                raise ValueError('invalid or duplicate interval')
            records[index] = row
        elif kind == 'result':
            results.append(row)
        elif kind == 'counter_done':
            finishes.append(row)
        else:
            raise ValueError('unknown counter record')
    total = 2 + 7 * samples
    if set(counts) != set(range(total)) or set(regions) != set(counts):
        raise ValueError('incomplete counting regions')
    if finishes != [{'kind': 'counter_done', 'intervals': total, 'failed': False}]:
        raise ValueError('counter did not complete cleanly')
    if len(results) != 1 or results[0]['variant'] != variant or results[0]['status'] != 'passed':
        raise ValueError('benchmark correctness failed')
    transcript = results[0]['transcript_shake256']
    if not re.fullmatch('[0-9a-f]{64}', transcript):
        raise ValueError('invalid output transcript')
    grouped = {op: {} for op in ('control_empty', 'control_loop', 'overhead') + OPS}
    for index, label in regions.items():
        op, sample = label['op'], label['sample']
        if op not in grouped or type(sample) is not int or sample in grouped[op]:
            raise ValueError('invalid or duplicate operation sample')
        value = counts[index]['instructions']
        if type(value) is not int or value < 0:
            raise ValueError('invalid instruction count')
        grouped[op][sample] = value
    for op, values in grouped.items():
        expected = 1 if op.startswith('control_') else samples
        if set(values) != set(range(expected)):
            raise ValueError(f'missing {op} observations')
    control_delta = grouped['control_loop'][0] - grouped['control_empty'][0]
    if control_delta != 301:
        raise ValueError(f'counter control expected 301 instructions, got {control_delta}')
    overhead = list(grouped['overhead'].values())
    correction = min(overhead)
    operations = {}
    for op in OPS:
        raw = [grouped[op][i] for i in range(samples)]
        if any(value <= correction for value in raw):
            raise ValueError('measurement below marker calibration')
        corrected = [value - correction for value in raw]
        operations[op] = {'raw_instructions': raw, 'instructions': corrected, **stats(corrected)}
    return {'counter_control_delta': control_delta, 'marker_overhead': stats(overhead),
            'marker_overhead_samples': overhead, 'correction': correction,
            'operations': operations, 'output_transcript_shake256': transcript}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--samples', type=int, default=101)
    args = parser.parse_args()
    if not 1 <= args.samples <= 101:
        raise ValueError('sample count must be between 1 and 101')
    folder = ROOT / 'build/qemu-benchmark'
    folder.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    library_dir = os.environ.get('QEMU_LIBDIR', str(ROOT / 'build/toolchain/root/usr/lib/x86_64-linux-gnu'))
    if Path(library_dir).exists():
        environment['LD_LIBRARY_PATH'] = library_dir + os.pathsep + environment.get('LD_LIBRARY_PATH', '')
    cc = executable('ARM_CC', 'arm-none-eabi-gcc')
    qemu = executable('QEMU', 'qemu-system-arm')
    nm = os.environ.get('ARM_NM', str(Path(cc).with_name('arm-none-eabi-nm')))
    size = os.environ.get('ARM_SIZE', str(Path(cc).with_name('arm-none-eabi-size')))
    include = shlex.split(os.environ.get('ARM_INC', ''))
    library = shlex.split(os.environ.get('ARM_LIB', ''))
    local = ROOT / 'build/toolchain/root/usr'
    if not include and local.exists():
        include = ['-isystem', str(local / 'include/newlib')]
    if not library and local.exists():
        library = ['-L' + str(local / 'lib/arm-none-eabi/newlib/thumb/v7e-m/nofp')]
    commands = []

    def run(command, label, timeout=180):
        start = time.perf_counter()
        process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                 env=environment, timeout=timeout)
        output = process.stdout + process.stderr
        path = folder / (label + '.log')
        path.write_text(output)
        if process.returncode:
            raise RuntimeError(f'{label} failed; inspect {path}')
        commands.append({'command': command, 'log': str(path.relative_to(ROOT)), 'log_sha256': sha(path),
                         'wall_seconds': round(time.perf_counter() - start, 3), 'status': 'passed'})
        return output

    header = folder / 'deps/qemu-plugin.h'
    header.parent.mkdir(exist_ok=True)
    if not header.exists():
        header.write_bytes(urlopen(HEADER_URL, timeout=30).read())
    if sha(header) != HEADER_SHA256:
        raise RuntimeError('QEMU plugin API header differs from the pinned dependency')
    plugin = folder / 'counter.so'
    run(['gcc', '-std=c11', '-O2', '-fPIC', '-shared', '-Wall', '-Wextra', '-Wpedantic',
         '-Wconversion', '-Wshadow', '-I' + str(header.parent), 'tools/qemu_counter.c', '-o', str(plugin)], 'plugin')
    make = (ROOT / 'Makefile').read_text()
    sources = re.search(r'^SRC = (.+)$', make, re.M).group(1).split()
    flags = shlex.split(re.search(r'^ARM_CFLAGS = (.+)$', make, re.M).group(1))
    inputs = sources + ['Makefile', 'tools/qemu_counter.c', 'tools/qemu_benchmark.py',
                       'tools/plot_benchmarks.py', 'platform/cortexm4/qemu_bench.c',
                       'platform/cortexm4/startup.c', 'platform/cortexm4/mps2_io.c', 'platform/cortexm4/mps2.ld']
    inputs += [str(path.relative_to(ROOT)) for path in (ROOT / 'include').glob('*.h')]
    inputs += [str(path.relative_to(ROOT)) for path in (ROOT / 'src').glob('*.inc')]
    inputs += ['src/mldsa44_internal.h', 'platform/cortexm4/test_main.c', 'platform/cortexm4/mps2_vectors.inc',
               'test/prior_cases.c', 'test/our_cases.c', 'test/prior_cases.h', 'test/our_cases.h', 'test/count_checkers.c']
    snapshot = {path: sha(ROOT / path) for path in sorted(set(inputs))}
    data = {'schema_version': 1, 'unit': 'guest instructions', 'physical_cycles': 'unmeasured',
            'machine': 'mps2-an386', 'samples_per_operation': args.samples,
            'compiler': run([cc, '--version'], 'compiler-version').splitlines()[0],
            'qemu': run([qemu, '--version'], 'qemu-version').splitlines()[0],
            'source_sha256': snapshot, 'plugin_header': {'url': HEADER_URL, 'sha256': HEADER_SHA256},
            'plugin_sha256': sha(plugin), 'configurations': {}, 'commands': commands}
    transcripts = set()
    for name, optimization in (('o2', ['-O2']), ('o3_lto', ['-O3', '-flto'])):
        options = [flag for flag in flags if not flag.startswith('-O')] + optimization
        config = {'compiler_flags': options, 'variants': {}}
        for variant in VARIANTS:
            defines = [] if variant == 'baseline' else ['-DMLDSA_' + variant.upper() + '_CHECKER']
            common = [cc, '-Iinclude', '-Isrc', '-Itest', '-Iplatform/cortexm4', *include, *options, *defines]
            link = ['-nostartfiles', '-nostdlib', '-Wl,--gc-sections', '-Tplatform/cortexm4/mps2.ld',
                    *library, '-lc', '-lgcc']
            runtime = ['platform/cortexm4/startup.c', 'platform/cortexm4/mps2_io.c']
            correctness_elf = folder / f'{name}-{variant}-correctness.elf'
            cases = [] if variant == 'baseline' else [f'test/{variant}_cases.c']
            hooks = [] if variant == 'baseline' else ['-DMLDSA_TEST_FAULTS']
            run(common + [*hooks, *sources, *runtime, 'platform/cortexm4/test_main.c',
                          *cases, *link, '-o', str(correctness_elf)], f'{name}-{variant}-correctness-build')
            base_command = [qemu, '-M', 'mps2-an386', '-nographic', '-semihosting-config',
                            'enable=on,target=native', '-no-reboot']
            output = run(base_command + ['-kernel', str(correctness_elf)], f'{name}-{variant}-correctness')
            record_suffix = '' if variant == 'baseline' else '-' + variant
            expected = json.loads((ROOT / f'test/qemu-mps2-an386{record_suffix}.json').read_text())['cases']
            if output.splitlines() != expected:
                raise ValueError(f'{name}/{variant}: correctness output differs')
            elf = folder / f'{name}-{variant}.elf'
            run(common + [f'-DQEMU_SAMPLES={args.samples}', f'-DQEMU_VARIANT="{variant}"',
                          *sources, *runtime, 'platform/cortexm4/qemu_bench.c', *link, '-o', str(elf)],
                f'{name}-{variant}-build')
            symbols = run([nm, str(elf)], f'{name}-{variant}-symbols')
            pcs = {line.split()[2]: int(line.split()[0], 16) & ~1 for line in symbols.splitlines()
                   if len(line.split()) == 3 and line.split()[2] in ('benchmark_begin', 'benchmark_end')}
            plugin_argument = f'{plugin},begin={pcs["benchmark_begin"]},end={pcs["benchmark_end"]}'
            output = run(base_command + ['-kernel', str(elf), '-plugin', plugin_argument], f'{name}-{variant}-counts')
            row = parse(output, variant, args.samples)
            usage = run([size, str(elf)], f'{name}-{variant}-size').splitlines()[1].split()
            row.update(elf_sha256=sha(elf), arm_image=dict(zip(('text', 'data', 'bss'), map(int, usage[:3]))),
                       correctness_cases=expected, marker_addresses=pcs)
            transcripts.add(row['output_transcript_shake256'])
            config['variants'][variant] = row
            print(f'{name}/{variant}: {args.samples} samples per operation, counter and correctness passed', flush=True)
        for variant, row in config['variants'].items():
            for op, summary in row['operations'].items():
                baseline = config['variants']['baseline']['operations'][op]['median']
                summary['overhead_percent'] = round(100 * (summary['median'] / baseline - 1), 4)
                prior = config['variants']['prior']['operations'][op]['median']
                summary['change_from_prior_percent'] = round(100 * (summary['median'] / prior - 1), 4)
        data['configurations'][name] = config
    if len(transcripts) != 1:
        raise ValueError('complete key/signature transcripts differ across variants or optimization flags')
    if snapshot != {path: sha(ROOT / path) for path in snapshot}:
        raise RuntimeError('benchmark sources changed during collection')
    previous = json.loads((ROOT / 'bench/comparison.json').read_text())
    for path, expected in previous['source_sha256'].items():
        if path.startswith(('src/', 'include/')) and sha(ROOT / path) != expected:
            raise RuntimeError('stored operation data is stale: ' + path)
    run(['make', '-B', 'build/count_checkers', 'CC=gcc', 'OPT=-O2', 'SAN='], 'field-counter-build')
    calls = json.loads(run([str(ROOT / 'build/count_checkers')], 'field-counter'))
    data['costs'] = {}
    for variant in VARIANTS:
        row = previous['variants'][variant]
        if calls[variant] != row['field_calls']:
            raise RuntimeError('operation counts changed: ' + variant)
        data['costs'][variant] = {key: row[key] for key in
                                 ('checks', 'stored_coefficients', 'constant_bytes', 'field_calls', 'extra_field_calls')}
    data['construction_bounds'] = []
    for h in range(4, 13):
        n, k = 2**h, h // 2
        locations = n * (h + 1)
        incidence = 2**(k + 1) + 2**(h - k + 1) - 3
        improved = incidence * locations - incidence * (incidence + 1) // 2
        data['construction_bounds'].append({'n': n, 'h': h, 'k': k, 'M': locations, 'K': incidence,
                                           'prior': (2*n - 1)*locations, 'our': improved})
    cert = json.loads((ROOT / 'docs/our_certificate.json').read_text())
    concrete = next(row for row in data['construction_bounds'] if row['n'] == cert['n'])
    if any(concrete[key] != cert[key] for key in ('h', 'k', 'M', 'K')) or concrete['our'] != cert['D']:
        raise ValueError('bound plot differs from the exact certificate')
    data['construction_bound_ratio_at_256'] = concrete['prior'] / concrete['our']
    destination = ROOT / 'bench/qemu_benchmark.json'
    destination.write_text(json.dumps(data, indent=2) + '\n')
    subprocess.run([sys.executable, 'tools/plot_benchmarks.py'], cwd=ROOT, check=True)
    print('Wrote bench/qemu_benchmark.json and README graphs; physical cycles remain unmeasured')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(f'QEMU benchmark failed: {error}')
