#!/usr/bin/env python3
"""Validate physical run files and summarize every captured observation."""
import argparse
import hashlib
import json
import math
import os
import statistics
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ('baseline', 'prior', 'our')
OPS = ('ntt_forward', 'ntt_inverse', 'pointwise', 'keygen', 'sign', 'verify')
STACK_OPS = ('ntt_forward', 'keygen', 'sign', 'verify')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def statistics_for(values):
    ordered = sorted(values)
    return {'samples': len(values), 'minimum': ordered[0],
            'median': statistics.median(values), 'maximum': ordered[-1],
            'p95_nearest_rank': ordered[math.ceil(0.95 * len(values)) - 1]}


def observations(path, expected_samples):
    cycles = {op: {} for op in OPS}
    stacks, overhead = {}, None
    for line in path.read_text().splitlines():
        record = json.loads(line)
        op = record.get('op')
        if set(record) == {'op', 'sample', 'cycles'}:
            value, index = record['cycles'], record['sample']
            require(type(value) is int and 0 <= value < 2**32, 'invalid cycle value')
            require(type(index) is int and index >= 0, 'invalid sample index')
            if op == 'overhead':
                require(overhead is None and index == 0, 'duplicate/invalid overhead')
                overhead = value
            else:
                require(op in cycles and index not in cycles[op] and value > 0,
                        'unknown operation, duplicate sample or zero measurement')
                cycles[op][index] = value
        elif set(record) == {'op', 'stack_bytes'}:
            value = record['stack_bytes']
            require(op in STACK_OPS and op not in stacks, 'unknown/duplicate stack operation')
            require(type(value) is int and value > 0, 'invalid stack value')
            stacks[op] = value
        else:
            raise ValueError('unknown observation record')
    require(overhead is not None and set(stacks) == set(STACK_OPS), 'missing overhead/stack')
    for op, values in cycles.items():
        n = expected_samples[op]
        require(type(n) is int and n > 0 and set(values) == set(range(n)),
                f'incomplete or noncontiguous {op} samples')
    return {'cycles': {op: statistics_for(list(values.values())) for op, values in cycles.items()},
            'stack_bytes': stacks, 'timer_overhead_cycles': overhead}


def image(path, expected):
    require(sha(path) == expected, f'ELF digest mismatch: {path}')
    content = path.read_bytes()
    require(content[:6] == b'\x7fELF\x01\x01' and content[18:20] == b'\x28\x00',
            f'not a little endian ARM ELF32: {path}')
    fields = subprocess.check_output([os.environ.get('ARM_SIZE', 'arm-none-eabi-size'),
                                      str(path)], text=True).splitlines()[1].split()
    return dict(zip(('text', 'data', 'bss'), map(int, fields[:3])))


def summarize(manifest_path, comparison_path):
    manifest = json.loads(manifest_path.read_text())
    require(manifest.get('schema_version') == 1 and manifest.get('physical_board') is True
            and manifest.get('status') == 'measured', 'physical run is still pending')
    metadata = manifest['metadata']
    fields = ('nucleo_model', 'mcu', 'clock_hz', 'flash_capacity_bytes', 'ram_capacity_bytes',
              'fpu_configuration', 'compiler', 'compiler_flags', 'linker_script',
              'linker_sha256', 'startup_file', 'startup_sha256', 'firmware_commit',
              'benchmark_source_sha256', 'st_link_method', 'serial_method', 'serial_baud',
              'interrupt_policy', 'timer_calibration_method', 'stack_measurement_method',
              'stack_kind', 'stack_reserve_bytes', 'input_schedule', 'sample_counts')
    require(all(metadata.get(key) for key in fields), 'missing actual hardware/build metadata')
    for key in ('clock_hz', 'flash_capacity_bytes', 'ram_capacity_bytes',
                'serial_baud', 'stack_reserve_bytes'):
        require(type(metadata[key]) is int and metadata[key] > 0, f'invalid {key}')
    require(metadata.get('intervals_below_counter_wrap_confirmed') is True,
            'DWT wrap bound has not been confirmed')
    require(metadata['stack_kind'] in ('total_high_water', 'additional_depth_below_callsite'),
            'unknown stack measurement semantics')
    require(set(metadata['sample_counts']) == set(OPS), 'missing operation sample counts')
    require(Path(metadata['linker_script']).name != 'mps2.ld', 'emulator linker is not physical')
    for key in ('linker', 'startup'):
        path = ROOT / metadata[f'{key}_script' if key == 'linker' else 'startup_file']
        require(sha(path) == metadata[f'{key}_sha256'], f'{key} source digest mismatch')
    require(sha(ROOT / 'platform/cortexm4/bench_main.c') == metadata['benchmark_source_sha256'],
            'benchmark source digest mismatch')
    comparison = json.loads(comparison_path.read_text())
    require(comparison['schema_version'] == 1, 'unknown comparison schema')
    for path, expected in comparison['source_sha256'].items():
        if path.startswith(('src/', 'include/')):
            require(sha(ROOT / path) == expected, f'stale operation/certificate evidence: {path}')
    require(set(manifest['variants']) == set(VARIANTS), 'missing or extra variants')
    variants = {}
    for variant in VARIANTS:
        files = manifest['variants'][variant]
        folder = manifest_path.parent
        bench_elf, compact_elf = folder / files['benchmark_elf'], folder / files['compact_elf']
        size = image(bench_elf, files['benchmark_sha256'])
        image(compact_elf, files['compact_sha256'])
        compact_log = folder / files['compact_log']
        expected = json.loads((ROOT / comparison['variants'][variant]['qemu']['record']).read_text())['cases']
        lines = compact_log.read_text().splitlines()
        require(lines == expected, f'{variant}: physical compact output differs')
        log = folder / files['benchmark_log']
        data = observations(log, metadata['sample_counts'])
        data['arm_image'] = size
        data['flash_bytes'] = size['text'] + size['data']
        data['static_ram_bytes'] = size['data'] + size['bss']
        require(data['flash_bytes'] <= metadata['flash_capacity_bytes'], 'flash capacity exceeded')
        require(data['static_ram_bytes'] + metadata['stack_reserve_bytes'] <=
                metadata['ram_capacity_bytes'], 'RAM capacity exceeded')
        require(max(data['stack_bytes'].values()) < metadata['stack_reserve_bytes'],
                'stack watermark reached the reserved boundary')
        data['compact_correctness'] = 'passed'
        data['files_sha256'] = {str(path.relative_to(folder)): sha(path)
                               for path in (bench_elf, compact_elf, compact_log, log)}
        for key in ('checks', 'extra_field_calls', 'modeled_fault_coverage', 'exact_certificate'):
            data[key] = comparison['variants'][variant][key]
        variants[variant] = data
    for data in variants.values():
        for op in OPS:
            base = variants['baseline']['cycles'][op]['median']
            data['cycles'][op]['overhead_percent'] = round(100 * (data['cycles'][op]['median'] / base - 1), 3)
    return {'schema_version': 1, 'status': 'measured', 'physical_board': True,
            'metadata': metadata, 'manifest_sha256': sha(manifest_path),
            'comparison_sha256': sha(comparison_path), 'variants': variants,
            'flash_method': 'linked benchmark ELF text+data; excludes layout padding',
            'static_ram_method': 'linked benchmark ELF data+bss; excludes stack',
            'inverse_protection': 'none in any variant',
            'physical_fault_injection': 'not evaluated'}


def markdown(data):
    lines = ['# Physical Cortex M4 comparison', '',
             'Generated from validated physical run files; cycle overhead uses the baseline median.', '',
             '| Variant | Operation | Samples | Min | Median | Max | P95 | Overhead % |',
             '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for variant, row in data['variants'].items():
        for op in OPS:
            stats = row['cycles'][op]
            values = [stats[key] for key in ('samples', 'minimum', 'median', 'maximum',
                                             'p95_nearest_rank', 'overhead_percent')]
            lines.append('| ' + ' | '.join(map(str, [variant, op] + values)) + ' |')
    lines += ['', '| Variant | Flash bytes | Static RAM bytes | NTT stack bytes | Keygen stack bytes | Sign stack bytes | Verify stack bytes | Extra mul | Extra add | Modeled deviations covered |',
              '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for variant, row in data['variants'].items():
        values = [variant, row['flash_bytes'], row['static_ram_bytes']]
        values += [row['stack_bytes'][op] for op in STACK_OPS]
        values += [row['extra_field_calls'][key] for key in ('mul', 'add')]
        values += [row['modeled_fault_coverage']['additive_wire_deviations']]
        lines.append('| ' + ' | '.join(map(str, values)) + ' |')
    lines += ['', 'Stack semantics: ' + data['metadata']['stack_kind'] + '. Method: ' +
              data['metadata']['stack_measurement_method'] + '.', '',
              'Stack observations cover the specified inputs and are not exhaustive worst case bounds. '
              'Flash excludes linker padding; static RAM excludes stack. Physical correctness does '
              'not establish physical fault resistance. Modeled coverage trusts the checker and '
              'covers nonzero result errors under the certified additive wire model.', '']
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('manifest', type=Path)
    p.add_argument('--comparison', type=Path, default=ROOT / 'bench/comparison.json')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    try:
        data = summarize(args.manifest, args.comparison)
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit(f'Physical report refused: {error}')
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'results.json').write_text(json.dumps(data, indent=2) + '\n')
    (args.output / 'comparison.md').write_text(markdown(data))
    print(f'wrote physical report to {args.output}')


if __name__ == '__main__':
    main()
