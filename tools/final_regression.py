#!/usr/bin/env python3
"""Run the comprehensive thesis regression once and freeze its raw evidence."""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from compare import VARIANTS, collect_result, digest, publish, sources
from fetch_nist import COMMIT, SETS
from measure_checkers import ROOT
from render_thesis import render

MODES = (
    ('gcc', 'gcc', '-O2', ''), ('clang', 'clang', '-O2', ''),
    ('asan', 'gcc', '-O1 -g', '-fsanitize=address'),
    ('ubsan', 'gcc', '-O1 -g', '-fsanitize=undefined -fno-sanitize-recover=all'),
)


def snapshot():
    result = sources()
    for path in (ROOT / 'hardware').glob('*'):
        if path.is_file() and path.suffix in ('.py', '.c', '.h', '.S', '.ld'):
            relative = str(path.relative_to(ROOT))
            result[relative] = digest(relative)
    return dict(sorted(result.items()))


def inventory():
    pin = json.loads((ROOT / 'tools/nist_manifest.json').read_text())
    if pin['commit'] != COMMIT:
        raise RuntimeError('NIST fetcher and manifest commits differ')
    for relative, expected in pin['files'].items():
        path = ROOT / 'build/nist' / relative
        content = path.read_bytes()
        blob = hashlib.sha1(f'blob {len(content)}\0'.encode() + content).hexdigest()
        if (hashlib.sha256(content).hexdigest() != expected['sha256'] or
                blob != expected['git_blob_sha1'] or len(content) != expected['bytes']):
            raise RuntimeError(f'NIST dataset differs from pinned official blob: {relative}')
    counts = {}
    omitted = {}
    for name in SETS:
        prompt = json.loads((ROOT / 'build/nist' / name / 'prompt.json').read_text())
        answer = json.loads((ROOT / 'build/nist' / name / 'expectedResults.json').read_text())
        results = {t['tcId']: t for group in answer['testGroups'] for t in group['tests']}
        omitted[name] = 0
        for group in prompt['testGroups']:
            selected = group.get('parameterSet', 'ML-DSA-44') == 'ML-DSA-44'
            if 'signatureInterface' in group:
                selected &= (group['signatureInterface'] == 'external' and
                             group.get('preHash') in ('pure', 'preHash'))
            for case in group['tests']:
                byte_aligned = (case.get('len', 0) % 8 == 0 and
                                case.get('outLen', 0) % 8 == 0)
                if not selected or not byte_aligned:
                    omitted[name] += 1
                    continue
                key = name
                if 'preHash' in group:
                    key += '/' + group['preHash']
                counts[key] = counts.get(key, 0) + 1
                if 'testPassed' in results[case['tcId']]:
                    verdict = '/valid' if results[case['tcId']]['testPassed'] else '/invalid'
                    counts[key + verdict] = counts.get(key + verdict, 0) + 1
    return {'provenance': pin, 'selected_cases': counts, 'omitted_cases': omitted,
            'scope': 'ML DSA 44 external pure and prehash interfaces; byte-aligned SHAKE; '
                     'other parameter sets, internal interfaces and bit-oriented SHAKE are unsupported'}


def official_counts(test, output, expected):
    if test == 'keygen':
        counts = [int(re.search(r'keyGen passed: (\d+) cases', output)[1])]
        wanted = [expected['ML-DSA-keyGen-FIPS204']]
    elif test == 'sign':
        counts = [int(re.search(r'sigGen passed: (\d+) pure', output)[1])]
        wanted = [expected['ML-DSA-sigGen-FIPS204/pure']]
    elif test == 'verify':
        match = re.search(r'sigVer passed: (\d+) pure external cases \((\d+) valid\)', output)
        counts = [int(match[1]), int(match[2])]
        wanted = [expected['ML-DSA-sigVer-FIPS204/pure'], expected['ML-DSA-sigVer-FIPS204/pure/valid']]
    else:
        match = re.search(r'passed: (\d+) sign, (\d+) verify \((\d+) valid\)', output)
        counts = [int(match[i]) for i in (1, 2, 3)]
        wanted = [expected['ML-DSA-sigGen-FIPS204/preHash'], expected['ML-DSA-sigVer-FIPS204/preHash'],
                  expected['ML-DSA-sigVer-FIPS204/preHash/valid']]
    if counts != wanted:
        raise RuntimeError(f'{test}: official tests did not cover every selected vector')
    return counts


class Run:
    def __init__(self):
        self.folder = ROOT / 'build/thesis'
        self.folder.mkdir(parents=True, exist_ok=True)
        self.stages = {}

    def stage(self, name, command, timeout=600, environment=None):
        print(f'{name}: running', flush=True)
        path = self.folder / (name + '.log')
        start = time.perf_counter()
        env = os.environ.copy()
        env.update(PYTHONOPTIMIZE='0', PYTHONHASHSEED='0',
                   UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        if environment:
            env.update(environment)
        with path.open('w') as log:
            process = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                     env=env, timeout=timeout, check=False)
        record = {'status': 'passed' if process.returncode == 0 else 'failed',
                  'command': command, 'exit_code': process.returncode,
                  'seconds': round(time.perf_counter() - start, 3),
                  'log': str(path.relative_to(ROOT)), 'log_sha256': digest(path),
                  'test_environment': {'PYTHONOPTIMIZE': '0', 'PYTHONHASHSEED': '0',
                                       'UBSAN_OPTIONS': env['UBSAN_OPTIONS'], **(environment or {})}}
        self.stages[name] = record
        (self.folder / 'progress.json').write_text(json.dumps(self.stages, indent=2) + '\n')
        if process.returncode:
            raise RuntimeError(f'{name} failed; inspect {record["log"]}')
        print(f'{name}: passed ({record["seconds"]}s)', flush=True)
        return path.read_text()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--physical-manifest', type=Path,
                        help='validate completed physical captures; never substitute synthetic values')
    args = parser.parse_args()
    run = Run()
    before = snapshot()
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    started_clock = time.perf_counter()
    run.stage('nist_fetch', [sys.executable, 'tools/fetch_nist.py'])
    nist = inventory()
    run.stage('table_controls', [sys.executable, 'tools/test_thesis.py'])
    host = {}
    make_sources = re.search(r'^SRC = (.+)$', (ROOT / 'Makefile').read_text(), re.M).group(1).split()
    common_python = ('model', 'sample', 'shake')
    libraries = ('build/libmldsa.so', 'build/libmldsa_prior.so', 'build/libmldsa_our.so')
    for mode, compiler, opt, sanitizer in MODES:
        flags = [f'CC={compiler}', f'OPT={opt}', f'SAN={sanitizer}']
        output = run.stage(mode + '_host', ['make', '-B', 'test', 'baseline', 'prior', 'our',
                                          *libraries, *flags], timeout=1200,
                           environment={'ASAN_OPTIONS': 'detect_leaks=1:abort_on_error=1'} if mode == 'asan' else None)
        match = re.search(r'passed: seed=(\d+) random pairs=(\d+)', output)
        negatives = re.search(r'negative cases: (\d+)', output)
        if not match or not negatives:
            raise RuntimeError('Comprehensive C suite did not report its case counts')
        host[mode] = {'compiler': subprocess.check_output([compiler, '--version'], text=True).splitlines()[0],
                      'opt': opt, 'sanitizer': sanitizer, 'status': 'passed',
                      'polynomial_seed': int(match[1]), 'polynomial_random_pairs': int(match[2]),
                      'negative_cases': {'baseline': int(negatives[1])}, 'official_variants': list(VARIANTS)}
        python_env = {}
        if mode == 'asan':
            python_env = {'LD_PRELOAD': subprocess.check_output(
                [compiler, '-print-file-name=libasan.so'], text=True).strip(),
                'ASAN_OPTIONS': 'detect_leaks=0:abort_on_error=1'}
        for target in common_python:
            command = ([sys.executable, 'tools/check_model.py', libraries[0]] if target == 'model' else
                       [sys.executable, f'test/test_{target}.py', libraries[0]])
            if target == 'shake':
                command += ['build/nist']
            run.stage(f'{mode}_{target}', command, environment=python_env)
        for variant, library in zip(VARIANTS, libraries):
            for test in ('keygen', 'sign', 'verify', 'prehash'):
                output = run.stage(f'{mode}_{variant}_{test}',
                          [sys.executable, f'test/test_{test}.py', library, 'build/nist'],
                          environment=python_env)
                host[mode].setdefault('official_case_counts', {}).setdefault(variant, {})[test] = official_counts(
                    test, output, nist['selected_cases'])
            if variant != 'baseline':
                executable = run.folder / f'{mode}-negative-{variant}'
                command = [compiler, '-std=c11', '-Wall', '-Wextra', '-Wpedantic', '-Wconversion',
                           '-Wshadow', '-Iinclude', '-Isrc', '-fno-omit-frame-pointer',
                           *opt.split(), *sanitizer.split(),
                           '-DMLDSA_' + variant.upper() + '_CHECKER', 'test/test_negative.c',
                           *make_sources, '-o', str(executable)]
                run.stage(f'{mode}_{variant}_negative_build', command)
                output = run.stage(f'{mode}_{variant}_negative', [str(executable)],
                                   environment={'ASAN_OPTIONS': 'detect_leaks=1:abort_on_error=1'} if mode == 'asan' else None)
                host[mode]['negative_cases'][variant] = int(re.search(r'negative cases: (\d+)', output)[1])
        if mode == 'gcc':
            metadata = ROOT / 'build/oracle/pqcrypto-1.0.0.dist-info/METADATA'
            if not metadata.exists():
                run.stage('oracle_install', [sys.executable, '-m', 'pip', 'install', '--no-deps',
                                            '--target', 'build/oracle', 'pqcrypto==1.0.0'])
            for variant, library in zip(VARIANTS, libraries):
                output = run.stage('differential_' + variant,
                                   [sys.executable, 'test/test_differential.py', library],
                                   environment={'PYTHONPATH': str(ROOT / 'build/oracle')})
                host[mode].setdefault('differential_cases', {})[variant] = int(
                    re.search(r'passed: (\d+) seeded', output)[1])
    for table in ('zetas', 'keccak'):
        run.stage('constants_' + table, [sys.executable, f'tools/gen_{table}.py', '--check'])
    for variant in ('prior', 'our'):
        run.stage('certificate_' + variant, [sys.executable, f'tools/gen_{variant}_checker.py', '--check'])
    for group in ('arithmetic', 'checkers'):
        run.stage('formal_' + group, [sys.executable, 'verify/run.py', '--group', group], timeout=960)
    run.stage('counter', ['make', '-B', 'build/count_checkers', 'CC=gcc', 'OPT=-O2', 'SAN='])
    arm_keys = ('ARM_CC', 'ARM_OBJCOPY', 'ARM_SIZE', 'ARM_INC', 'ARM_LIB')
    run.stage('arm', ['make', '-B', 'arm-mps2', 'arm-mps2-prior', 'arm-mps2-our',
                     'arm-mps2-bench', 'arm-mps2-prior-bench', 'arm-mps2-our-bench'] +
              [f'{key}={os.environ[key]}' for key in arm_keys if key in os.environ])
    for variant in VARIANTS:
        run.stage('qemu_' + variant, [sys.executable, 'tools/run_mps2.py'] +
                  ([] if variant == 'baseline' else ['--' + variant]))
    if before != snapshot():
        raise RuntimeError('Sources changed during final regression')
    comparison = collect_result(run.stages.copy(), sources())
    publish(comparison)
    run.stage('offline_benchmark', [sys.executable, 'hardware/offline.py'], timeout=900)
    offline = json.loads((ROOT / 'bench/offline_cortexm4.json').read_text())
    physical = {'status': 'pending', 'physical_board': False,
                'reason': 'No completed physical captures supplied; no hardware accessed'}
    if args.physical_manifest:
        run.stage('physical_capture_validation', [sys.executable, 'hardware/report.py',
                  str(args.physical_manifest.resolve()), '--output', str(run.folder / 'physical')])
        physical = json.loads((run.folder / 'physical/results.json').read_text())
        physical['capture_validation'] = 'validated recorded captures; no new board execution by this command'
    proofs = {group: json.loads((ROOT / f'verify/results_{group}.json').read_text())
              for group in ('arithmetic', 'checkers')}
    certs = {variant: json.loads((ROOT / f'docs/{variant}_certificate.json').read_text())
             for variant in ('prior', 'our')}
    if before != snapshot():
        raise RuntimeError('Sources changed during offline benchmarks')
    history = subprocess.check_output(['git', 'log', '--format=fuller', '--stat'], cwd=ROOT, text=True)
    (run.folder / 'git-log-at-run.txt').write_text(history)
    data = {'schema_version': 1, 'purpose': 'thesis material and final comprehensive host regression',
            'status': 'available_evidence_passed', 'hardware_milestone_complete': physical['status'] == 'measured',
            'started_utc': started, 'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'total_seconds': round(time.perf_counter() - started_clock, 3),
            'base_git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'worktree_dirty_at_run': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT)),
            'source_sha256': before, 'stages': run.stages, 'nist': nist, 'host': host,
            'comparison': comparison, 'offline': offline, 'certificates': certs, 'formal': proofs,
            'physical': physical, 'physical_acquisition_in_this_run': 'not performed',
            'oracle': {'package': 'pqcrypto', 'version': '1.0.0',
                       'metadata_sha256': digest('build/oracle/pqcrypto-1.0.0.dist-info/METADATA')},
            'evidence_sha256': {path: digest(path) for path in (
                'bench/comparison.json', 'bench/offline_cortexm4.json', 'docs/prior_certificate.json',
                'docs/our_certificate.json', 'verify/results_arithmetic.json', 'verify/results_checkers.json')},
            'limitations': ['Physical acquisition and reproduction require actual board access.',
                'No physical fault injection or side channel resistance established.',
                'Formal results are portable C component proofs with inspected composition.',
                'Inverse NTT, matrix sampling and the rest of ML DSA are outside checker protection.',
                'Static frames do not bound the complete stack; physical high water remains input dependent.']}
    destination = ROOT / 'bench/thesis.json'
    temporary = destination.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    render(data, ROOT / 'bench/thesis', ROOT / 'docs/thesis_results.md')
    temporary.replace(destination)
    print(f'Final available evidence passed: {len(run.stages)} stages; physical status: {physical["status"]}')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        raise SystemExit(f'Final regression refused: {error}; inspect build/thesis/progress.json and logs')
