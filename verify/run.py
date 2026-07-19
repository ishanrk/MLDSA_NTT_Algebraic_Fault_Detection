#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import shlex
import signal
import subprocess
import time
from pathlib import Path

from source_views import ROOT, generate

GROUPS = {
    'arithmetic': [
        (name, ['verify/arithmetic.c', 'src/poly.c'], name, 1, [])
        for name in ('reduce', 'add', 'sub', 'mul', 'center', 'uncenter')
    ] + [
        ('forward_butterfly', ['verify/butterfly.c'], 'butterfly', 1, []),
        ('inverse_butterfly', ['verify/butterfly.c'], 'butterfly', 1, ['-DINVERSE']),
    ] + [
        (f'forward_layer_{i}', ['verify/layer.c'], 'layer', 257, [f'-DLAYER={i}'])
        for i in range(8)
    ] + [
        ('forward_memory', ['verify/ntt_memory.c', 'src/ntt.c'], 'forward_memory', 257, []),
        ('inverse_memory', ['verify/ntt_memory.c', 'src/ntt.c'], 'inverse_memory', 257, []),
        ('pointwise_memory', ['verify/ntt_memory.c', 'src/ntt.c'], 'pointwise_memory', 257, []),
    ],
    'checkers': [
        (f'{variant}_{entry}', ['verify/checker_step.c'], entry, 1,
         ['-DPRIOR'] if variant == 'prior' else [])
        for variant in ('prior', 'our') for entry in ('base', 'input_step', 'output_step', 'decide')
    ] + [
        (f'{variant}_memory', ['verify/checker_memory.c', f'src/{variant}.c'], 'memory', 257,
         ['-DPRIOR'] if variant == 'prior' else []) for variant in ('prior', 'our')
    ],
}


def digests(group):
    paths = ['src/poly.c', 'src/ntt.c', 'src/zetas.inc', 'src/prior.c', 'src/prior_tables.inc',
             'src/our.c', 'src/our_tables.inc', 'include/mldsa_poly.h', 'include/mldsa_checker.h']
    paths += sorted({source for _, sources, _, _, _ in GROUPS[group] for source in sources
                     if source.startswith('verify/')})
    paths += ['verify/run.py', 'verify/source_views.py', 'verify/range_ops.h']
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--group', choices=GROUPS, default='arithmetic')
    p.add_argument('--timeout', type=float, default=45)
    args = p.parse_args()
    cbmc = os.environ.get('CBMC', 'cbmc')
    version = subprocess.check_output([cbmc, '--version'], text=True).strip()
    if int(version.split('.')[0]) < 6:
        raise SystemExit('Set CBMC to the installed version 6 executable')
    snapshot = digests(args.group)
    generate()
    views = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
             for path in sorted((ROOT / 'build/verify').glob('*.inc'))}
    flags = ['-Iinclude', '-Ibuild/verify', '--arch', 'i386', '--32', '--little-endian',
             '--bounds-check', '--pointer-check', '--pointer-overflow-check',
             '--signed-overflow-check', '--unsigned-overflow-check', '--conversion-check',
             '--undefined-shift-check', '--unwinding-assertions', '--drop-unused-functions', '--z3']
    flags += shlex.split(os.environ.get('CBMC_INCLUDES', ''))
    headers = ROOT / 'build/verify/headers/root/usr/include/x86_64-linux-gnu'
    if headers.exists():
        flags += ['-I' + str(headers.relative_to(ROOT)), '-I/usr/include/x86_64-linux-gnu']
    results = []
    for name, sources, entry, unwind, extra in GROUPS[args.group]:
        cmd = [cbmc] + sources + flags + extra + ['--function', entry, '--unwind', str(unwind)]
        start = time.perf_counter()
        try:
            proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, start_new_session=True)
            output, _ = proc.communicate(timeout=args.timeout)
            code = proc.returncode
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            output, _ = proc.communicate()
            code = None
        seconds = time.perf_counter() - start
        log = ROOT / f'build/verify/{name}.log'
        log.write_text(output)
        passed = code == 0 and 'VERIFICATION SUCCESSFUL' in output
        result = {'name': name, 'entry': entry, 'command': cmd, 'unwind': unwind,
                  'unwinding_assertions_enabled': True,
                  'result': 'passed' if passed else 'timeout' if code is None else 'failed',
                  'seconds': round(seconds, 3), 'exit_code': code,
                  'log_sha256': hashlib.sha256(output.encode()).hexdigest()}
        results.append(result)
        print(f"{name}: {result['result']} {seconds:.3f}s", flush=True)
    if snapshot != digests(args.group):
        raise SystemExit('Proof sources changed during the run; rerun with stable sources')
    data = {'cbmc': version, 'solver': subprocess.check_output(['z3', '--version'], text=True).strip(),
            'model': '32 bit little endian portable C with i386 preprocessing',
            'timeout_per_job_seconds': args.timeout,
            'production_sha256': {path: digest for path, digest in snapshot.items()
                                  if path.startswith(('src/', 'include/'))},
            'harness_sha256': {path: digest for path, digest in snapshot.items() if path.startswith('verify/')},
            'source_view_sha256': views,
            'proofs': results, 'total_seconds': round(sum(x['seconds'] for x in results), 3)}
    (ROOT / f'verify/results_{args.group}.json').write_text(json.dumps(data, indent=2) + '\n')
    if any(x['result'] != 'passed' for x in results):
        raise SystemExit('Some proof jobs did not pass; inspect build/verify logs')


if __name__ == '__main__':
    main()
