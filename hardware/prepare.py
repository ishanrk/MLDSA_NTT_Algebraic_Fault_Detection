#!/usr/bin/env python3
"""Freeze compiled inputs in a new run directory without accessing hardware."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

from config import PLAN, PROFILES, ROOT, VARIANTS, sha, source_hashes


def prepare(board, destination):
    build_dir = ROOT / 'build/physical' / board
    build = json.loads((build_dir / 'build.json').read_text())
    if build['source_sha256'] != source_hashes():
        raise ValueError('Build sources changed; rebuild before preparing a run')
    if destination.exists():
        raise ValueError('Use a new run directory to preserve previous observations')
    destination.mkdir(parents=True)
    profile = PROFILES[board]
    comparison = json.loads((ROOT / 'bench/comparison.json').read_text())
    shutil.copy2(ROOT / 'bench/comparison.json', destination / 'comparison.json')
    shutil.copy2(ROOT / build['linker_script'], destination / 'linker.ld')
    shutil.copy2(ROOT / 'hardware/boot.c', destination / 'boot.c')
    shutil.copy2(ROOT / 'hardware/startup.S', destination / 'startup.S')
    shutil.copy2(build_dir / 'build.json', destination / 'build.json')
    metadata = dict(nucleo_model=board, mcu=profile['mcu'], core_revision=None,
                    clock_hz=profile['clock_hz'], clock_status='configured nominal HSI; hardware pending',
                    flash_capacity_bytes=profile['flash_bytes'], ram_capacity_bytes=profile['ram_bytes'],
                    fpu_configuration='FPU disabled, soft ABI', compiler=build['compiler'],
                    compiler_flags=build['compiler_flags'], linker_script='linker.ld',
                    linker_sha256=build['linker_sha256'], startup_file='boot.c',
                    startup_sha256=build['startup_sha256'],
                    startup_assembly_sha256=sha(destination / 'startup.S'),
                    build_manifest_sha256=sha(destination / 'build.json'),
                    firmware_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    firmware_worktree_dirty=bool(subprocess.check_output(
                        ['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
                    benchmark_source_sha256=build['benchmark_source_sha256'], benchmark_file='hardware/bench.c',
                    plan_sha256=build['plan_sha256'], input_schedule=PLAN,
                    sample_counts=PLAN['sample_counts'], calibration_pairs=PLAN['timer_calibration_pairs'],
                    stack_kind='total_high_water', stack_reserve_bytes=profile['stack_reserve_bytes'],
                    stack_measurement_method='frameless watermark helpers; stack top minus deepest changed word; all samples',
                    timer_calibration_method='minimum of complete DWT read-pair distribution; raw counts retained',
                    interrupt_policy=PLAN['interrupt_policy'], intervals_below_counter_wrap_confirmed=None,
                    st_link_method=None, serial_method=None, serial_baud=profile['serial_baud'])
    manifest = {'schema_version': 2, 'status': 'pending', 'physical_board': False,
                'metadata': metadata, 'comparison_record': 'comparison.json',
                'source_sha256': build['source_sha256'], 'variants': {}}
    for variant in VARIANTS:
        row = {}
        for kind, key in (('compact', 'compact'), ('bench', 'benchmark')):
            image = build['variants'][variant][kind]
            path = build_dir / image['elf']
            if sha(path) != image['sha256']:
                raise ValueError(f'Compiled image changed: {path}')
            shutil.copy2(path, destination / path.name)
            row[key + '_elf'] = path.name
            row[key + '_sha256'] = image['sha256']
            row[key + '_log'] = f'{variant}-{kind}.txt'
        row['expected_compact_cases'] = json.loads((ROOT / comparison['variants'][variant]['qemu']['record']).read_text())['cases']
        if sha(ROOT / comparison['variants'][variant]['qemu']['record']) != comparison['variants'][variant]['qemu']['record_sha256']:
            raise ValueError('QEMU correctness record changed; refresh comparison evidence')
        manifest['variants'][variant] = row
    (destination / 'run.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--board', required=True, choices=PROFILES)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    try:
        prepare(args.board, args.output)
    except (ValueError, OSError) as error:
        raise SystemExit(str(error))
    print(f'Prepared {args.output}; physical correctness and measurements remain pending')


if __name__ == '__main__':
    main()
