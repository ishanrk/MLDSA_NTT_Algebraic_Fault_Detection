#!/usr/bin/env python3
"""Run the board-independent gates and publish unmeasured physical tables."""
import json
import os
import re
import shlex
import subprocess
import sys

from build import build
from config import PLAN, PROFILES, ROOT, VARIANTS, sha, source_hashes
from prepare import prepare
from protocol import decode
from report import parse_observations, render, summarize, tables


def run(command, log, env=None):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, env=env, timeout=120)
    log.write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f'{command[0]} failed; inspect {log}')
    return {'command': command, 'log_sha256': sha(log), 'status': 'passed'}


def main():
    folder = ROOT / 'build/hardware-offline'
    folder.mkdir(parents=True, exist_ok=True)
    snapshot = source_hashes()
    results = {'schema_version': 2, 'purpose': 'offline physical-stage preparation only',
               'physical_board': False, 'physical_measurements': 'pending', 'source_sha256': snapshot,
               'checks': {}, 'profiles': {}}
    for script in ('test_report', 'test_protocol'):
        results['checks'][script] = run([sys.executable, f'hardware/{script}.py'], folder / f'{script}.log')
    debugger = os.environ.get('OPENOCD', 'openocd')
    debug_command = [debugger]
    if 'OPENOCD_SCRIPTS' in os.environ:
        debug_command += ['-s', os.environ['OPENOCD_SCRIPTS']]
    debug_command += ['-f', 'interface/stlink.cfg', '-f', 'target/stm32f4x.cfg',
                      '-c', 'echo OFFLINE_CONFIG_PASS; shutdown']
    results['checks']['openocd_config'] = run(debug_command, folder / 'openocd-config.log')
    debug_version = subprocess.run([debugger, '--version'], capture_output=True, text=True, check=True)
    results['openocd_version'] = (debug_version.stdout + debug_version.stderr).splitlines()[0]
    for board in PROFILES:
        build_dir = build(board)
        destination = folder / board
        if destination.exists():
            # Only this disposable ignored offline gate directory is replaced.
            import shutil
            shutil.rmtree(destination)
        prepare(board, destination)
        report = summarize(destination / 'run.json', pending=True)
        render(report, destination / 'report')
        results['profiles'][board] = report
    sources = re.search(r'^SRC = (.+)$', (ROOT / 'Makefile').read_text(), re.M).group(1).split()
    transcripts = set()
    include = ROOT / 'build/physical/NUCLEO-F411RE'
    for mode, compiler, extra in (
        ('gcc', 'gcc', []), ('clang', 'clang', []),
        ('asan', 'gcc', ['-O1', '-g', '-fsanitize=address']),
        ('ubsan', 'gcc', ['-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=all']),
    ):
        for variant in VARIANTS:
            name = f'{mode}-{variant}'
            flags = ['-std=c11', '-O2', '-Wall', '-Wextra', '-Wpedantic', '-Wconversion', '-Wshadow',
                     '-Iinclude', '-Isrc', '-Ihardware', '-Iplatform/cortexm4', '-I' + str(include),
                     f'-DPHYSICAL_VARIANT="{variant}"'] + extra
            if variant != 'baseline':
                flags += ['-DMLDSA_' + variant.upper() + '_CHECKER']
            obj, executable = folder / f'{name}.o', folder / name
            run([compiler] + flags + ['-Dmain=benchmark_entry', '-c', 'hardware/bench.c', '-o', str(obj)],
                folder / f'{name}-compile.log')
            run([compiler] + flags + ['hardware/mock.c', str(obj)] + sources + ['-o', str(executable)],
                folder / f'{name}-link.log')
            log = folder / f'{name}-synthetic.txt'
            result = run([str(executable)], log)
            _, payload = decode(log.read_text(), 'NUCLEO-F411RE', variant, 'bench', synthetic=True)
            parsed = parse_observations(payload, PLAN['sample_counts'], PLAN['timer_calibration_pairs'])
            transcripts.add(parsed['output_transcript_shake256'])
            results['checks'][name] = result
            print(f'{name}: complete synthetic benchmark control passed', flush=True)
    if len(transcripts) != 1:
        raise RuntimeError('Host variants produced different complete output transcripts')
    executable = folder / 'gcc-baseline'
    env = dict(os.environ, MLDSA_TEST_DWT_UNAVAILABLE='1')
    failed = subprocess.run([str(executable)], cwd=ROOT, capture_output=True, text=True, env=env)
    if failed.returncode != 1 or 'DWT UNAVAILABLE' not in failed.stdout or '"raw_cycles"' in failed.stdout:
        raise RuntimeError('Unavailable counter emitted observations')
    results['checks']['unavailable_counter'] = {'status': 'passed'}
    results['checks']['report_integration'] = run([sys.executable, 'hardware/test_integration.py'],
                                                folder / 'test-integration.log')
    cc = os.environ.get('ARM_CC', 'arm-none-eabi-gcc')
    armflags = shlex.split(re.search(r'^ARM_CFLAGS = (.+)$', (ROOT / 'Makefile').read_text(), re.M).group(1))
    elf = folder / 'core-test.elf'
    command = [cc] + armflags + ['-Iinclude', '-Ihardware', '-Iplatform/cortexm4']
    command += shlex.split(os.environ.get('ARM_INC', ''))
    command += ['hardware/test_core.c', 'hardware/core.c', 'platform/cortexm4/startup.c',
                'platform/cortexm4/mps2_io.c', '-nostartfiles', '-nostdlib', '-Wl,--gc-sections',
                '-Tplatform/cortexm4/mps2.ld']
    command += shlex.split(os.environ.get('ARM_LIB', '')) + ['-lc', '-lgcc', '-o', str(elf)]
    results['checks']['core_compile'] = run(command, folder / 'core-compile.log')
    env = os.environ.copy()
    if 'QEMU_LIBDIR' in env:
        env['LD_LIBRARY_PATH'] = env['QEMU_LIBDIR'] + os.pathsep + env.get('LD_LIBRARY_PATH', '')
    results['checks']['core_qemu'] = run([os.environ.get('QEMU', 'qemu-system-arm'), '-M', 'mps2-an386',
                                       '-kernel', str(elf), '-nographic', '-semihosting-config',
                                       'enable=on,target=native', '-no-reboot'], folder / 'core-qemu.log', env)
    if (folder / 'core-qemu.log').read_text().splitlines() != ['CORE total stack watermark PASS', 'CORE unavailable DWT PASS']:
        raise RuntimeError('Unexpected core QEMU result')
    if snapshot != source_hashes():
        raise RuntimeError('Sources changed during offline gates')
    (ROOT / 'bench/offline_cortexm4.json').write_text(json.dumps(results, indent=2) + '\n')
    tex = ['% Offline compiled reference targets. Physical measurements pending.']
    escape = lambda value: re.sub(r'([&%$#_{}])', r'\\\1', str(value))
    for board, data in results['profiles'].items():
        for title, headers, rows in tables(data):
            tex += ['', '% ' + board + ': ' + title,
                    '\\begin{tabular}{l' + 'r' * (len(headers) - 1) + '}', '\\hline',
                    ' & '.join(map(escape, headers)) + r' \\', '\\hline']
            tex += [' & '.join(map(escape, row)) + r' \\' for row in rows]
            tex += ['\\hline', '\\end{tabular}']
    (ROOT / 'bench/offline_cortexm4.tex').write_text('\n'.join(tex) + '\n')
    print('Offline gates passed; physical measurements remain pending')


if __name__ == '__main__':
    main()
