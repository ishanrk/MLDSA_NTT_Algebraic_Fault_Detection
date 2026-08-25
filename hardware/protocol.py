"""Validate boot identity and complete serial run framing."""
import json

from config import PLAN_SHA256, PROFILES


def decode(text, board, variant, kind, synthetic=False):
    lines = text.splitlines()
    if len(lines) < 3:
        raise ValueError('incomplete serial run')
    ready, done = json.loads(lines[0]), json.loads(lines[-1])
    profile = PROFILES[board]
    expected = {'event': 'ready', 'board': board, 'mcu': profile['mcu'],
                'variant': variant, 'kind': kind, 'plan_sha256': PLAN_SHA256}
    if any(ready.get(key) != value for key, value in expected.items()):
        raise ValueError('firmware/plan/variant identity mismatch')
    if ready.get('synthetic', False) != synthetic:
        raise ValueError('synthetic run cannot be physical evidence')
    if done != {'event': 'done', 'exit_code': 0}:
        raise ValueError('firmware did not finish successfully')
    if not synthetic:
        values = ('cpuid', 'dbg_idcode', 'uid0', 'uid1', 'uid2', 'flash_kib', 'nominal_cpu_hz', 'rcc_cr',
                  'rcc_cfgr', 'flash_acr', 'cpacr', 'primask')
        if any(type(ready.get(key)) is not int for key in values):
            raise ValueError('missing runtime register readings')
        if ((ready['cpuid'] >> 4) & 0xfff) != 0xc24:
            raise ValueError('target is not Cortex M4')
        if (ready['dbg_idcode'] & 0xfff) != profile['device_id']:
            raise ValueError('target MCU does not match selected profile')
        if ready['flash_kib'] * 1024 != profile['flash_bytes']:
            raise ValueError('target flash does not match profile')
        if (ready['nominal_cpu_hz'] != profile['clock_hz'] or ready['rcc_cfgr'] != 0
                or ready['rcc_cr'] & 3 != 3 or ready['rcc_cr'] & ((1 << 16) | (1 << 24))):
            raise ValueError('unexpected clock configuration')
        if ready['flash_acr'] != 0 or ready['cpacr'] & (15 << 20) or ready['primask'] != 1:
            raise ValueError('unexpected flash/FPU/interrupt configuration')
    return ready, lines[1:-1]
