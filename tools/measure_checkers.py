#!/usr/bin/env python3
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(args):
    return subprocess.check_output(args, cwd=ROOT, text=True)


def collect():
    size = os.environ.get('ARM_SIZE', 'arm-none-eabi-size')
    cc = os.environ.get('ARM_CC', 'arm-none-eabi-gcc')
    counts = json.loads(run(['build/count_checkers']))
    assert counts['baseline'] == {'mul': 1024, 'add': 1024, 'sub': 1024}
    variants = {}
    for name in ('baseline', 'prior', 'our'):
        suffix = '' if name == 'baseline' else '_' + name
        elf = ROOT / f'build/arm/mps2{suffix}_bench.elf'
        usage = run([size, str(elf)]).splitlines()[1].split()
        image = dict(zip(('text', 'data', 'bss'), map(int, usage[:3])))
        record = '' if name == 'baseline' else '-' + name
        path = f'test/qemu-mps2-an386{record}.json'
        qemu = json.loads((ROOT / path).read_text())
        assert qemu['cases'] and all(x.endswith('PASS') for x in qemu['cases'])
        extra = {key: counts[name][key] - counts['baseline'][key] for key in counts[name]}
        data = {
            'checks': 0 if name == 'baseline' else 2,
            'stored_coefficients': 0, 'constant_bytes': 0,
            'field_calls': counts[name], 'extra_field_calls': extra,
            'arm_image': image,
            'elf_sha256': hashlib.sha256(elf.read_bytes()).hexdigest(),
            'qemu': {'status': 'passed', 'target': qemu['target'],
                     'emulator': qemu['emulator'], 'record': path},
        }
        if name != 'baseline':
            cert = json.loads((ROOT / f'docs/{name}_certificate.json').read_text())
            arrays = re.findall(r'static const uint32_t \w+\[(\d+)\]',
                                (ROOT / f'src/{name}_tables.inc').read_text())
            coeffs = sum(map(int, arrays))
            assert coeffs == cert['stored_coefficients']
            data.update(stored_coefficients=coeffs, constant_bytes=4 * coeffs,
                        coefficients_sha256=cert['coefficients_sha256'])
        variants[name] = data
    assert variants['prior']['extra_field_calls'] == {'mul': 640, 'add': 1024, 'sub': 0}
    assert variants['our']['extra_field_calls'] == {'mul': 768, 'add': 1024, 'sub': 0}
    data = {
        'purpose': 'field operation counts and linked emulator image sizes only',
        'compiler': run([cc, '--version']).splitlines()[0],
        'architecture': '-mcpu=cortex-m4 -mthumb -mfloat-abi=soft',
        'optimization': '-O2', 'linker': 'platform/cortexm4/mps2.ld',
        'variants': variants,
        'physical_cycles': 'pending', 'physical_flash_ram_stack': 'pending',
    }
    return data


def main():
    data = collect()
    print(json.dumps(data, indent=2))


if __name__ == '__main__':
    main()
