#!/usr/bin/env python3
"""Rebuild the focused research evidence and publish one comparison dataset."""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from measure_checkers import ROOT, collect
from render_comparison import render

VARIANTS = ('baseline', 'prior', 'our')


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def sources():
    paths = [Path('Makefile')]
    if (ROOT / 'tools/nist_manifest.json').exists():
        paths.append(Path('tools/nist_manifest.json'))
    for folder in ('src', 'include', 'platform', 'test', 'verify', 'tools'):
        paths += [p.relative_to(ROOT) for p in (ROOT / folder).rglob('*')
                  if p.is_file() and p.suffix in ('.c', '.h', '.inc', '.ld', '.py')]
    return {str(p): digest(p) for p in sorted(paths)}


def proof_record(group):
    path = f'verify/results_{group}.json'
    data = json.loads((ROOT / path).read_text())
    for key in ('production_sha256', 'harness_sha256'):
        for source, expected in data[key].items():
            if digest(source) != expected:
                raise RuntimeError(f'stale proof: {source}')
    for view, expected in data['source_view_sha256'].items():
        if digest(f'build/verify/{view}') != expected:
            raise RuntimeError(f'stale proof view: {view}')
    for job in data['proofs']:
        if job['result'] != 'passed' or not job['unwinding_assertions_enabled']:
            raise RuntimeError(f'incomplete proof: {job["name"]}')
        if digest(f'build/verify/{job["name"]}.log') != job['log_sha256']:
            raise RuntimeError(f'proof log changed: {job["name"]}')
    return {'record': path, 'sha256': digest(path), 'cbmc': data['cbmc'],
            'solver': data['solver'], 'model': data['model'],
            'jobs_passed': [job['name'] for job in data['proofs']],
            'unwinding_assertions': 'passed', 'seconds': data['total_seconds']}


def certificate(variant):
    path = f'docs/{variant}_certificate.json'
    data = json.loads((ROOT / path).read_text())
    counts = {key: value for key, value in data.items()
              if key.startswith('zero_') or key == 'duplicate_normalized_responses'}
    if any(counts.values()):
        raise RuntimeError(f'certificate failures: {variant}')
    m = data['modeled_locations']
    if data['checked_pairs'] != m * (m - 1) // 2:
        raise RuntimeError(f'incomplete certificate: {variant}')
    return {'status': 'passed', 'record': path, 'sha256': digest(path),
            'modeled_locations': m, 'checked_pairs': data['checked_pairs'],
            'failure_counts': counts, 'row_identities': data['row_identities'],
            'propagation_identity': data['propagation_identity'],
            'coefficients_sha256': data['coefficients_sha256'],
            'network_sha256': data['network_sha256']}


def collect_result(stages, snapshot):
    data = collect()
    data.update(schema_version=1, purpose='pre hardware research comparison',
                source_sha256=snapshot, stages=stages,
                host_compilers={cc: subprocess.check_output([cc, '--version'], text=True)
                                .splitlines()[0] for cc in ('gcc', 'clang')})
    data['arm_cflags'] = subprocess.check_output(
        ['make', '-s', '--eval=print-arm-flags:;@printf "%s\\n" "$(ARM_CFLAGS)"',
         'print-arm-flags'], cwd=ROOT, text=True).strip()
    data['link_flags'] = '-nostartfiles -nostdlib -Wl,--gc-sections -lc -lgcc'
    data['formal'] = {group: proof_record(group) for group in ('arithmetic', 'checkers')}
    data['formal']['scope'] = ('Portable C component proofs and compositional reasoning; '
                               'no automatically checked global NTT or ML DSA refinement')
    data['formal']['documentation'] = 'docs/reproduction.md'
    for variant, row in data['variants'].items():
        row['exact_certificate'] = (certificate(variant) if variant != 'baseline'
                                    else {'status': 'not applicable'})
        row['formal'] = {
            'status': 'focused component proofs passed',
            'common_jobs': len(data['formal']['arithmetic']['jobs_passed']),
            'checker_jobs': sum(job.startswith(variant + '_') for job in
                                data['formal']['checkers']['jobs_passed']),
            'scope_document': 'docs/reproduction.md',
        }
        row['modeled_fault_coverage'] = {
            'additive_wire_deviations': 0 if variant == 'baseline' else 2,
            'locations': None if variant == 'baseline' else
                         row['exact_certificate']['modeled_locations'],
            'conditions': 'trusted checker arithmetic, stored weights and control flow; '
                          'nonzero erroneous transform result',
            'physical_fault_injection': 'not evaluated',
        }
        row['physical'] = {'status': 'pending', 'board': None, 'clock_hz': None,
                           'cycles': None, 'flash_bytes': None, 'static_ram_bytes': None,
                           'stack_bytes': None}
        row['qemu']['record_sha256'] = digest(row['qemu']['record'])
    return data


def publish(data):
    dst = ROOT / 'bench/comparison.json'
    dst.parent.mkdir(exist_ok=True)
    dst.write_text(json.dumps(data, indent=2) + '\n')
    render(data, None, ROOT / 'bench/comparison.tex')


def main():
    logs = ROOT / 'build/comparison'
    logs.mkdir(parents=True, exist_ok=True)
    snapshot = sources()
    stages = {}
    python = sys.executable
    arm_keys = ('ARM_CC', 'ARM_OBJCOPY', 'ARM_SIZE', 'ARM_INC', 'ARM_LIB')
    arm_args = [f'{key}={os.environ[key]}' for key in arm_keys if key in os.environ]

    def stage(name, command, timeout=180):
        print(f'{name}: running', flush=True)
        start = time.perf_counter()
        log = logs / f'{name}.log'
        with log.open('w') as stream:
            subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                           timeout=timeout, check=True)
        stages[name] = {'status': 'passed', 'command': command,
                        'seconds': round(time.perf_counter() - start, 3),
                        'log': str(log.relative_to(ROOT)),
                        'log_sha256': digest(log)}
        print(f'{name}: passed', flush=True)

    for name, cc, opt, san in (
        ('gcc', 'gcc', '-O2', ''), ('clang', 'clang', '-O2', ''),
        ('asan', 'gcc', '-O1 -g', '-fsanitize=address'),
        ('ubsan', 'gcc', '-O1 -g', '-fsanitize=undefined -fno-sanitize-recover=all'),
    ):
        stage(name, ['make', '-B', 'baseline', 'prior', 'our',
                     f'CC={cc}', f'OPT={opt}', f'SAN={san}'])
    for variant in ('prior', 'our'):
        stage(f'certificate_{variant}', [python, f'tools/gen_{variant}_checker.py',
                                        '--check'], timeout=600)
    for group in ('arithmetic', 'checkers'):
        stage(f'formal_{group}', [python, 'verify/run.py', '--group', group], timeout=960)
    stage('counter', ['make', '-B', 'build/count_checkers', 'CC=gcc', 'OPT=-O2', 'SAN='])
    stage('arm', ['make', '-B', 'arm-mps2', 'arm-mps2-prior', 'arm-mps2-our',
                  'arm-mps2-bench', 'arm-mps2-prior-bench', 'arm-mps2-our-bench'] + arm_args)
    for variant in VARIANTS:
        stage(f'qemu_{variant}', [python, 'tools/run_mps2.py'] +
              ([] if variant == 'baseline' else ['--' + variant]))

    if snapshot != sources():
        raise RuntimeError('Sources changed during comparison; rerun with stable sources')
    publish(collect_result(stages, snapshot))
    print('wrote bench/comparison.json and bench/comparison.tex')


if __name__ == '__main__':
    try:
        main()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, RuntimeError) as error:
        raise SystemExit(f'Comparison failed: {error}; inspect build/comparison logs')
