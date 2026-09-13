#!/usr/bin/env python3
"""Validate frozen physical runs and generate JSON/Markdown/LaTeX results."""
import argparse
import json
import math
import os
import re
import statistics
import subprocess
from pathlib import Path

from config import OPS, PLAN, PLAN_SHA256, PROFILES, ROOT, STACK_OPS, VARIANTS, sha, source_hashes
from protocol import decode


def require(condition, message):
    if not condition:
        raise ValueError(message)


def statistics_for(values):
    ordered = sorted(values)
    return {'samples': len(values), 'minimum': ordered[0], 'median': statistics.median(values),
            'maximum': ordered[-1], 'p95_nearest_rank': ordered[math.ceil(0.95 * len(values)) - 1]}


def parse_observations(lines, expected_samples, calibration_pairs=None):
    cycles = {op: {} for op in OPS}
    raw = {op: {} for op in OPS}
    stacks = {op: {} for op in STACK_OPS}
    overhead, transcript = {}, None
    for line in lines:
        record = json.loads(line)
        op = record.get('op')
        if set(record) == {'event', 'shake256'} and record['event'] == 'transcript':
            require(transcript is None and re.fullmatch('[0-9a-f]{64}', record['shake256']),
                    'duplicate/invalid transcript')
            transcript = record['shake256']
            continue
        if set(record) in ({'op', 'sample', 'cycles'}, {'op', 'sample', 'cycles', 'raw_cycles'}):
            value, index = record['cycles'], record['sample']
            require(type(value) is int and 0 <= value < 2**32, 'invalid cycle value')
            require(type(index) is int and index >= 0, 'invalid sample index')
            if op == 'overhead':
                require(index not in overhead and 'raw_cycles' not in record, 'invalid overhead')
                overhead[index] = value
            else:
                require(op in cycles and index not in cycles[op] and value > 0,
                        'unknown operation, duplicate sample or zero measurement')
                cycles[op][index] = value
                if 'raw_cycles' in record:
                    require(type(record['raw_cycles']) is int and 0 <= record['raw_cycles'] < 2**32,
                            'invalid raw cycle value')
                    raw[op][index] = record['raw_cycles']
        elif set(record) in ({'op', 'stack_bytes'}, {'op', 'sample', 'stack_bytes'}):
            value, index = record['stack_bytes'], record.get('sample', 0)
            require(type(index) is int and index >= 0, 'invalid stack index')
            require(op in stacks and index not in stacks[op], 'unknown/duplicate stack operation')
            require(type(value) is int and value > 0, 'invalid stack value')
            stacks[op][index] = value
        else:
            raise ValueError('unknown observation record')
    count = calibration_pairs if calibration_pairs is not None else 1
    require(set(overhead) == set(range(count)), 'missing/noncontiguous overhead')
    correction = min(overhead.values())
    for op, values in cycles.items():
        n = expected_samples[op]
        require(type(n) is int and n > 0 and set(values) == set(range(n)),
                f'incomplete or noncontiguous {op} samples')
        if calibration_pairs is not None:
            require(set(raw[op]) == set(values), f'missing raw {op} cycles')
        for index, value in raw[op].items():
            require(cycles[op][index] == max(value - correction, 0), 'wrong timer correction')
    for op, values in stacks.items():
        n = expected_samples[op] if calibration_pairs is not None else 1
        require(set(values) == set(range(n)), f'incomplete {op} stack samples')
    if calibration_pairs is not None:
        require(transcript is not None, 'missing output transcript')
    return {'cycles': {op: statistics_for(list(values.values())) for op, values in cycles.items()},
            'stack_bytes': {op: max(values.values()) for op, values in stacks.items()},
            'stack_statistics': {op: statistics_for(list(values.values())) for op, values in stacks.items()},
            'timer_overhead_cycles': correction, 'timer_overhead_statistics': statistics_for(list(overhead.values())),
            'output_transcript_shake256': transcript}


def observations(path, expected_samples, calibration_pairs=None):
    return parse_observations(path.read_text().splitlines(), expected_samples, calibration_pairs)


def image(path, expected):
    require(sha(path) == expected, f'ELF digest mismatch: {path}')
    content = path.read_bytes()
    require(content[:6] == b'\x7fELF\x01\x01' and content[18:20] == b'\x28\x00',
            f'not a little endian ARM ELF32: {path}')
    fields = subprocess.check_output([os.environ.get('ARM_SIZE', 'arm-none-eabi-size'), str(path)],
                                      text=True).splitlines()[1].split()
    return dict(zip(('text', 'data', 'bss'), map(int, fields[:3])))


def summarize(manifest_path, comparison_path=None, pending=False):
    manifest = json.loads(manifest_path.read_text())
    require(manifest.get('schema_version') == 2, 'prepare a version 2 run with hardware/prepare.py')
    require(pending or (manifest.get('physical_board') is True and manifest.get('status') == 'measured'),
            'physical run is still pending')
    metadata, folder = manifest['metadata'], manifest_path.parent
    board = metadata['nucleo_model']
    profile = PROFILES[board]
    require(manifest['source_sha256'] == source_hashes(), 'frozen build sources changed')
    require(metadata['plan_sha256'] == PLAN_SHA256 and metadata['input_schedule'] == PLAN,
            'benchmark input schedule changed')
    require(metadata['sample_counts'] == PLAN['sample_counts']
            and metadata['calibration_pairs'] == PLAN['timer_calibration_pairs'], 'sample plan changed')
    for key, expected in (('clock_hz', 'clock_hz'), ('flash_capacity_bytes', 'flash_bytes'),
                          ('ram_capacity_bytes', 'ram_bytes'), ('stack_reserve_bytes', 'stack_reserve_bytes')):
        require(metadata[key] == profile[expected], 'board memory/clock profile changed')
    for path, expected in ((metadata['linker_script'], metadata['linker_sha256']),
                           (metadata['startup_file'], metadata['startup_sha256']),
                           ('startup.S', metadata['startup_assembly_sha256']),
                           ('build.json', metadata['build_manifest_sha256'])):
        require(sha(folder / path) == expected, f'frozen build artifact changed: {path}')
    build = json.loads((folder / 'build.json').read_text())
    require(build['source_sha256'] == manifest['source_sha256'] and build['board_profile'] == board,
            'manifest differs from compiled source/profile')
    require(metadata['compiler'] == build['compiler'] and metadata['compiler_flags'] == build['compiler_flags'],
            'compiler metadata differs from build')
    require(sha(ROOT / metadata['benchmark_file']) == metadata['benchmark_source_sha256'],
            'benchmark source digest mismatch')
    comparison_path = comparison_path or folder / manifest['comparison_record']
    comparison = json.loads(comparison_path.read_text())
    for path, expected in comparison['source_sha256'].items():
        if path.startswith(('src/', 'include/')):
            require(sha(ROOT / path) == expected, f'stale operation/certificate evidence: {path}')
    require(set(manifest['variants']) == set(VARIANTS), 'missing or extra variants')
    if not pending:
        require(metadata['intervals_below_counter_wrap_confirmed'] is True, 'DWT wrap bound unconfirmed')
        require(metadata['st_link_method'] and metadata['serial_method'], 'missing physical transport details')
        durations = metadata['capture_seconds']
        require(set(durations) == {f'{v}-{k}' for v in VARIANTS for k in ('compact', 'bench')},
                'missing complete capture durations')
        require(metadata['counter_wrap_guard_frequency_hz'] == profile['clock_hz'] * 1.10,
                'counter wrap guard frequency changed')
        require(all(0 < durations[f'{v}-bench'] < 2**32 / metadata['counter_wrap_guard_frequency_hz']
                    for v in VARIANTS), 'whole-batch wrap bound not established')
    variants = {}
    for variant in VARIANTS:
        files = manifest['variants'][variant]
        for kind, key in (('compact', 'compact'), ('bench', 'benchmark')):
            require(files[key + '_sha256'] == build['variants'][variant][kind]['sha256'],
                    'variant images differ from frozen build')
        record = comparison['variants'][variant]['qemu']
        require(sha(ROOT / record['record']) == record['record_sha256'], 'compact evidence record changed')
        cases = json.loads((ROOT / record['record']).read_text())['cases']
        require(files['expected_compact_cases'] == cases, 'expected compact cases changed')
        size = image(folder / files['benchmark_elf'], files['benchmark_sha256'])
        image(folder / files['compact_elf'], files['compact_sha256'])
        data = {'cycles': None, 'stack_bytes': None, 'compact_correctness': 'pending'}
        if not pending:
            ready, lines = decode((folder / files['compact_log']).read_text(), board, variant, 'compact')
            require(lines == files['expected_compact_cases'], f'{variant}: physical compact output differs')
            bench_ready, payload = decode((folder / files['benchmark_log']).read_text(), board, variant, 'bench')
            require(all(ready[key] == bench_ready[key] for key in ('cpuid', 'dbg_idcode', 'uid0', 'uid1', 'uid2')),
                    'compact and benchmark target identity changed')
            data = parse_observations(payload, metadata['sample_counts'], metadata['calibration_pairs'])
            require(max(data['stack_bytes'].values()) < profile['stack_reserve_bytes'], 'stack watermark exhausted')
            data['compact_correctness'] = 'passed'
            data['runtime_registers'] = bench_ready
            data['files_sha256'] = {files[key]: sha(folder / files[key]) for key in
                                   ('compact_log', 'benchmark_log', 'compact_elf', 'benchmark_elf')}
        data.update(arm_image=size, flash_bytes=size['text'] + size['data'],
                    static_ram_bytes=size['data'] + size['bss'])
        largest_frame = max(build['variants'][variant]['bench']['stack_frames'], key=lambda row: row['bytes'])
        data['stack_static_analysis'] = {'largest_individual_frame': largest_frame,
                                         'reserved_bytes': profile['stack_reserve_bytes'],
                                         'total_call_stack_bound': 'not proven'}
        require(data['flash_bytes'] <= profile['flash_bytes'], 'flash capacity exceeded')
        require(data['static_ram_bytes'] + profile['stack_reserve_bytes'] <= profile['ram_bytes'], 'RAM capacity exceeded')
        for key in ('checks', 'extra_field_calls', 'modeled_fault_coverage', 'exact_certificate'):
            data[key] = comparison['variants'][variant][key]
        variants[variant] = data
        cert = data['exact_certificate']
        if variant != 'baseline':
            require(cert['status'] == 'passed' and not any(cert['failure_counts'].values())
                    and sha(ROOT / cert['record']) == cert['sha256'], 'certificate record changed')
    if not pending:
        identities = {tuple(data['runtime_registers'][key] for key in
                            ('cpuid', 'dbg_idcode', 'uid0', 'uid1', 'uid2')) for data in variants.values()}
        require(len(identities) == 1, 'variants ran on different physical targets')
        transcripts = {data['output_transcript_shake256'] for data in variants.values()}
        require(len(transcripts) == 1, 'variants produced different key/signature transcripts')
        for data in variants.values():
            for op in OPS:
                base = variants['baseline']['cycles'][op]['median']
                data['cycles'][op]['overhead_percent'] = round(100 * (data['cycles'][op]['median'] / base - 1), 3)
    return {'schema_version': 2, 'status': 'pending' if pending else 'measured', 'physical_board': not pending,
            'metadata': metadata, 'manifest_sha256': sha(manifest_path),
            'comparison_sha256': sha(comparison_path), 'variants': variants,
            'flash_method': 'linked benchmark ELF text+data; excludes layout padding',
            'static_ram_method': 'linked benchmark ELF data+bss; excludes stack',
            'inverse_protection': 'none in any variant', 'physical_fault_injection': 'not evaluated'}


def tables(data):
    cycles, memory, samples = [], [], []
    for variant, row in data['variants'].items():
        label = {'baseline': 'Baseline', 'prior': 'Abdelmonem et al.', 'our': 'Current method'}[variant]
        values = [label]
        for op in ('ntt_forward', 'sign', 'verify', 'keygen'):
            values += ([row['cycles'][op]['median'], row['cycles'][op]['overhead_percent']]
                       if row['cycles'] else ['pending', 'pending'])
        cycles.append(values)
        values = [label, row['flash_bytes'], row['static_ram_bytes']]
        values += ([row['stack_bytes'][op] for op in ('keygen', 'sign', 'verify')]
                   if row['stack_bytes'] else ['pending'] * 3)
        values += [row['extra_field_calls'][key] for key in ('mul', 'add')]
        values += [row['modeled_fault_coverage']['additive_wire_deviations'], row['compact_correctness']]
        memory.append(values)
        if row['cycles']:
            for op in OPS:
                stats = row['cycles'][op]
                samples.append([label, op] + [stats[key] for key in
                               ('samples', 'minimum', 'median', 'maximum', 'p95_nearest_rank')])
    groups = [('Cycle comparison', ['Variant', 'NTT median', 'NTT overhead %', 'Sign median',
               'Sign overhead %', 'Verify median', 'Verify overhead %', 'Keygen median', 'Keygen overhead %'], cycles),
              ('Memory and evidence', ['Variant', 'Linked flash', 'Static RAM', 'Keygen stack', 'Sign stack',
               'Verify stack', 'Extra mul', 'Extra add', 'Modeled deviations', 'Board correctness'], memory)]
    if samples:
        groups.append(('All sample statistics', ['Variant', 'Operation', 'Samples', 'Min', 'Median', 'Max', 'P95'], samples))
    return groups


def render(data, folder):
    md = ['# Cortex M4 physical comparison', '', 'Status: **' + data['status'] + '**. '
          'Linked image sizes are compile results; physical cycle and stack observations require a board.', '']
    tex = ['% Generated from results.json; physical status: ' + data['status']]
    escape = lambda value: re.sub(r'([&%$#_{}])', r'\\\1', str(value))
    for title, headers, rows in tables(data):
        md += ['## ' + title, '', '| ' + ' | '.join(headers) + ' |',
               '| ' + ' | '.join(['---'] * len(headers)) + ' |']
        md += ['| ' + ' | '.join(map(str, row)) + ' |' for row in rows]
        md.append('')
        tex += ['', '% ' + title, '\\begin{tabular}{l' + 'r' * (len(headers) - 1) + '}', '\\hline',
                ' & '.join(map(escape, headers)) + r' \\', '\\hline']
        tex += [' & '.join(map(escape, row)) + r' \\' for row in rows]
        tex += ['\\hline', '\\end{tabular}']
    md += ['Stack is total high water, including the caller frame, over all planned samples. '
           'It is not an exhaustive worst case bound. Cycle overhead uses baseline medians. '
           'The P95 uses nearest rank. Full overhead calibration and raw cycle values remain in the logs. '
           'Inverse NTT is unprotected in every variant. Mathematical coverage trusts the checker; '
           'physical fault injection has not been evaluated.', '']
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'results.json').write_text(json.dumps(data, indent=2) + '\n')
    (folder / 'comparison.md').write_text('\n'.join(md))
    (folder / 'comparison.tex').write_text('\n'.join(tex) + '\n')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('manifest', type=Path)
    p.add_argument('--comparison', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--pending', action='store_true', help='render linked sizes with unmeasured physical fields')
    args = p.parse_args()
    try:
        data = summarize(args.manifest, args.comparison, args.pending)
        render(data, args.output)
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit(f'Physical report refused: {error}')
    print(f'wrote {data["status"]} report to {args.output}')


if __name__ == '__main__':
    main()
