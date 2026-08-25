"""Explicit reference profiles; none identifies the user's physical board."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {
    'NUCLEO-F411RE': {'mcu': 'STM32F411RET6', 'ram_bytes': 128 * 1024, 'device_id': 0x431},
    'NUCLEO-F446RE': {'mcu': 'STM32F446RET6', 'ram_bytes': 128 * 1024, 'device_id': 0x421},
}
for profile in PROFILES.values():
    profile.update(flash_bytes=512 * 1024, clock_hz=16000000, serial_baud=115200,
                   stack_reserve_bytes=96 * 1024,
                   openocd_interface='interface/stlink.cfg', openocd_target='target/stm32f4x.cfg')

OPS = ('ntt_forward', 'ntt_inverse', 'pointwise', 'keygen', 'sign', 'verify')
STACK_OPS = ('ntt_forward', 'keygen', 'sign', 'verify')
VARIANTS = ('baseline', 'prior', 'our')
PLAN = {
    'samples_per_operation': 101, 'timer_calibration_pairs': 101,
    'sample_counts': {op: 101 for op in OPS},
    'message': 'Cortex M4 portable baseline', 'context': 'arm',
    'ntt_input_a': '((i+1)*(i+17)) mod q',
    'ntt_input_b': '((3*i+2)*(7*i+5)) mod q',
    'keygen_seed': 'bytes 0..31, with seed[0]=sample index',
    'signing_key_seed': 'bytes 0..31',
    'sign_randomness': '32 zero bytes, with rnd[0]=sample index',
    'verify_signature': 'last signing sample, rnd[0]=100',
    'stack': 'total high water, each timed forward/keygen/sign/verify invocation',
    'interrupt_policy': 'PRIMASK=1, SysTick off, polling UART',
}
PLAN_SHA256 = hashlib.sha256(json.dumps(PLAN, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_hashes():
    paths = [ROOT / 'Makefile']
    for folder in ('src', 'include', 'hardware', 'platform/cortexm4', 'test'):
        paths += [path for path in (ROOT / folder).rglob('*') if path.is_file()
                  and path.suffix in ('.c', '.h', '.inc', '.S', '.ld', '.py', '.cfg')]
    return {str(path.relative_to(ROOT)): sha(path) for path in sorted(paths)}
