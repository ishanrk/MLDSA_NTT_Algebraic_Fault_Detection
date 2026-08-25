#!/usr/bin/env python3
"""Cross compile six images for an explicitly selected reference board."""
import argparse
import json
import os
import re
import shlex
import shutil
import subprocess

from config import PLAN, PLAN_SHA256, PROFILES, ROOT, VARIANTS, sha, source_hashes


def build(board):
    profile = PROFILES[board]
    folder = ROOT / 'build/physical' / board
    folder.mkdir(parents=True, exist_ok=True)
    snapshot = source_hashes()
    make = (ROOT / 'Makefile').read_text()
    sources = re.search(r'^SRC = (.+)$', make, re.M).group(1).split()
    flags = shlex.split(re.search(r'^ARM_CFLAGS = (.+)$', make, re.M).group(1))
    cc = os.environ.get('ARM_CC', 'arm-none-eabi-gcc')
    common = flags + ['-Iinclude', '-Isrc', '-Itest', '-Ihardware', '-Iplatform/cortexm4',
                      '-I' + str(folder), '-fstack-usage']
    common += shlex.split(os.environ.get('ARM_INC', ''))
    library = shlex.split(os.environ.get('ARM_LIB', ''))
    linker = folder / 'stm32f4.ld'
    text = (ROOT / 'hardware/stm32f4.ld').read_text()
    for token, key in (('FLASH', 'flash_bytes'), ('RAM', 'ram_bytes'), ('STACK', 'stack_reserve_bytes')):
        text = text.replace('@' + token + '_BYTES@', str(profile[key]))
    linker.write_text(text)
    header = (f'#define BENCH_SAMPLES {PLAN["samples_per_operation"]}U\n'
              f'#define BENCH_CALIBRATION_PAIRS {PLAN["timer_calibration_pairs"]}U\n')
    for name, value in (('BENCH_MESSAGE', PLAN['message']), ('BENCH_CONTEXT', PLAN['context']),
                        ('BENCH_PLAN_SHA256', PLAN_SHA256), ('PHYSICAL_BOARD', board),
                        ('PHYSICAL_MCU', profile['mcu'])):
        header += f'#define {name} {json.dumps(value)}\n'
    (folder / 'bench_plan.h').write_text(header)
    data = {'schema_version': 2, 'status': 'compiled; physical validation pending',
            'physical_board': False, 'board_profile': board, 'profile': profile,
            'plan': PLAN, 'plan_sha256': PLAN_SHA256, 'source_sha256': snapshot,
            'compiler': subprocess.check_output([cc, '--version'], text=True).splitlines()[0],
            'compiler_flags': common, 'linker_script': str(linker.relative_to(ROOT)),
            'linker_sha256': sha(linker), 'startup_file': 'hardware/boot.c',
            'startup_sha256': sha(ROOT / 'hardware/boot.c'),
            'benchmark_file': 'hardware/bench.c', 'benchmark_source_sha256': sha(ROOT / 'hardware/bench.c'),
            'variants': {}, 'commands': []}
    for variant in VARIANTS:
        images = {}
        for kind in ('compact', 'bench'):
            name = f'{variant}-{kind}'
            objects = folder / name
            if objects.exists():
                shutil.rmtree(objects)
            objects.mkdir(exist_ok=True)
            selected = [] if variant == 'baseline' else ['-DMLDSA_' + variant.upper() + '_CHECKER']
            selected += [f'-DPHYSICAL_VARIANT="{variant}"', f'-DPHYSICAL_KIND="{kind}"']
            files = sources + ['hardware/startup.S', 'hardware/boot.c', 'hardware/stm32f4.c']
            if kind == 'compact':
                files += ['platform/cortexm4/test_main.c']
                if variant != 'baseline':
                    selected += ['-DMLDSA_TEST_FAULTS']
                    files += [f'test/{variant}_cases.c']
            else:
                files += ['hardware/core.c', 'hardware/bench.c']
            outputs = []
            for index, source in enumerate(files):
                output = objects / f'{index}-{source.replace("/", "-")}.o'
                command = [cc] + common + selected + ['-c', source, '-o', str(output)]
                subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
                data['commands'].append(command)
                outputs.append(str(output))
            elf = folder / f'{name}.elf'
            command = [cc] + flags + outputs + ['-nostartfiles', '-nostdlib', '-Wl,--gc-sections',
                      '-Wl,-Map,' + str(folder / f'{name}.map'), '-T' + str(linker)] + library + ['-lc', '-lgcc', '-o', str(elf)]
            subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
            data['commands'].append(command)
            usage = subprocess.check_output([os.environ.get('ARM_SIZE', 'arm-none-eabi-size'),
                                             str(elf)], text=True).splitlines()[1].split()
            sizes = dict(zip(('text', 'data', 'bss'), map(int, usage[:3])))
            frames = []
            for path in objects.glob('*.su'):
                for line in path.read_text().splitlines():
                    fields = line.split('\t')
                    frames.append({'function': fields[0], 'bytes': int(fields[1]), 'kind': fields[2]})
            if any(frame['bytes'] >= profile['stack_reserve_bytes'] for frame in frames):
                raise RuntimeError('An individual static frame exhausts the stack reserve')
            images[kind] = {'elf': elf.name, 'sha256': sha(elf), 'size': sizes,
                            'selector_flags': selected, 'stack_frames': frames}
            print(f'{board} {name}: text={sizes["text"]} data={sizes["data"]} bss={sizes["bss"]}', flush=True)
        data['variants'][variant] = images
    if snapshot != source_hashes():
        raise RuntimeError('Sources changed during build')
    (folder / 'build.json').write_text(json.dumps(data, indent=2) + '\n')
    return folder


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--board', required=True, choices=PROFILES)
    args = p.parse_args()
    try:
        print(build(args.board))
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.stderr or str(error))


if __name__ == '__main__':
    main()
