#!/usr/bin/env python3
"""Flash and capture the frozen six-image experiment when hardware is present."""
import argparse
import json
import os
import re
import select
import subprocess
import termios
import time
from pathlib import Path

from config import PROFILES, VARIANTS, sha
from protocol import decode
from report import render, summarize


class Serial:
    def __init__(self, path):
        self.fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        termios.tcflush(self.fd, termios.TCIOFLUSH)
        settings = termios.tcgetattr(self.fd)
        settings[0] = settings[1] = settings[3] = 0
        settings[2] = termios.CS8 | termios.CLOCAL | termios.CREAD
        settings[4] = settings[5] = termios.B115200
        settings[6][termios.VMIN] = 0
        settings[6][termios.VTIME] = 0
        termios.tcsetattr(self.fd, termios.TCSANOW, settings)
        self.buffer = b''

    def close(self):
        os.close(self.fd)

    def line(self, deadline):
        while b'\n' not in self.buffer:
            left = deadline - time.monotonic()
            if left <= 0 or not select.select([self.fd], [], [], left)[0]:
                raise TimeoutError('serial capture timed out')
            block = os.read(self.fd, 4096)
            if not block:
                raise OSError('serial device disconnected')
            self.buffer += block
        line, self.buffer = self.buffer.split(b'\n', 1)
        return line.decode('ascii').rstrip('\r')


def capture(port, path, timeout):
    deadline = time.monotonic() + timeout
    with path.open('x') as stream:
        ready = port.line(deadline)
        stream.write(ready + '\n')
        stream.flush()
        if json.loads(ready).get('event') != 'ready':
            raise ValueError('firmware readiness record missing')
        start = time.monotonic()
        os.write(port.fd, b'R')
        while True:
            line = port.line(deadline)
            stream.write(line + '\n')
            stream.flush()
            if line.startswith('{') and json.loads(line).get('event') == 'done':
                return time.monotonic() - start


def openocd(command, args):
    run = [args.openocd, '-f', 'interface/stlink.cfg', '-f', 'target/stm32f4x.cfg']
    if args.scripts:
        run[1:1] = ['-s', args.scripts]
    if args.probe_serial:
        if not re.fullmatch('[A-Za-z0-9]+', args.probe_serial):
            raise ValueError('invalid ST-Link probe serial')
        run += ['-c', 'adapter serial ' + args.probe_serial]
    run += ['-c', command]
    proc = subprocess.run(run, capture_output=True, text=True, timeout=60, check=True)
    return proc.stdout + proc.stderr


def main():
    p = argparse.ArgumentParser()
    p.add_argument('manifest', type=Path)
    p.add_argument('--port', required=True, help='Linux serial device exposed by ST-Link VCP')
    p.add_argument('--openocd', default=os.environ.get('OPENOCD', 'openocd'))
    p.add_argument('--probe-serial')
    p.add_argument('--scripts', default=os.environ.get('OPENOCD_SCRIPTS'))
    p.add_argument('--timeout', type=float, default=900)
    args = p.parse_args()
    manifest = json.loads(args.manifest.read_text())
    folder = args.manifest.parent.resolve()
    try:
        if manifest['status'] != 'pending':
            raise ValueError('Use a new prepared run directory')
        if any((folder / files[key]).exists() for files in manifest['variants'].values()
               for key in ('compact_log', 'benchmark_log')):
            raise ValueError('Capture logs already exist; preserve them and prepare a new directory')
        summarize(args.manifest, pending=True)
        board = manifest['metadata']['nucleo_model']
        profile = PROFILES[board]
        probe = openocd('init; reset halt; mdw 0xe000ed00 1; mdw 0xe0042000 1; mdh 0x1fff7a22 1; '
                        'mdw 0x1fff7a10 1; mdw 0x1fff7a14 1; mdw 0x1fff7a18 1; shutdown', args)
        (folder / 'probe.log').write_text(probe)
        registers = {}
        for address, value in re.findall(r'(0x[0-9a-fA-F]+):\s+(?:0x)?([0-9a-fA-F]+)', probe):
            registers[int(address, 16)] = int(value, 16)
        if (registers.get(0xe0042000, 0) & 0xfff != profile['device_id']
                or registers.get(0x1fff7a22, 0) * 1024 != profile['flash_bytes']
                or (registers.get(0xe000ed00, 0) >> 4) & 0xfff != 0xc24):
            raise ValueError('Probe identity does not match selected board profile; no firmware flashed')
        version = subprocess.run([args.openocd, '--version'], capture_output=True, text=True, check=True)
        manifest['metadata']['st_link_method'] = {
            'tool': args.openocd, 'version': (version.stdout + version.stderr).splitlines()[0],
            'interface': 'interface/stlink.cfg', 'target': 'target/stm32f4x.cfg',
            'script_search_dir': args.scripts,
            'method': 'SWD program ELF, verify, reset; probe identity checked before programming',
            'probe_serial': args.probe_serial}
        manifest['metadata']['serial_method'] = {'port': args.port, 'method': 'USART2 PA2/PA3 via ST-Link VCP; 115200 8N1'}
        durations, runtime = {}, {}
        # Every compact suite completes before any benchmark is accepted.
        for kind, key in (('compact', 'compact'), ('bench', 'benchmark')):
            for variant in VARIANTS:
                files = manifest['variants'][variant]
                elf = folder / files[key + '_elf']
                if sha(elf) != files[key + '_sha256']:
                    raise ValueError('Prepared ELF changed')
                # Braced Tcl literals prevent path interpretation; reject delimiters.
                if any(character in str(elf) for character in '{}\\\n\r'):
                    raise ValueError('Run path contains unsupported Tcl characters')
                port = Serial(args.port)
                try:
                    output = openocd('program {' + str(elf) + '} verify reset exit', args)
                    (folder / f'{variant}-{kind}-flash.log').write_text(output)
                    seconds = capture(port, folder / files[key + '_log'], args.timeout)
                finally:
                    port.close()
                ready, payload = decode((folder / files[key + '_log']).read_text(), board, variant, kind)
                if any(ready[f'uid{i}'] != registers.get(0x1fff7a10 + 4*i) for i in range(3)):
                    raise ValueError('Serial output belongs to a different target than the flashed probe')
                if kind == 'compact' and payload != files['expected_compact_cases']:
                    raise ValueError(f'{variant}: physical compact suite differs')
                durations[f'{variant}-{kind}'] = seconds
                runtime[variant] = ready
        # A whole-batch bound, including serial output, also bounds every timed interval.
        wrap_limit = 2**32 / (profile['clock_hz'] * 1.10)
        if any(durations[f'{variant}-bench'] >= wrap_limit for variant in VARIANTS):
            raise ValueError('Whole-batch counter-wrap bound not established; inspect preserved logs')
        cpuid = runtime['baseline']['cpuid']
        manifest['metadata'].update(core_revision=f'r{(cpuid >> 20) & 15}p{cpuid & 15}',
                                    clock_status='HSI source and prescalers read back; nominal frequency, not a frequency measurement',
                                    intervals_below_counter_wrap_confirmed=True,
                                    counter_wrap_guard_frequency_hz=profile['clock_hz'] * 1.10,
                                    capture_seconds=durations)
        manifest.update(status='measured', physical_board=True)
        candidate = folder / 'run.complete.json'
        candidate.write_text(json.dumps(manifest, indent=2) + '\n')
        result = summarize(candidate)
        args.manifest.write_text(candidate.read_text())
        candidate.unlink()
        render(result, folder / 'report')
    except (ValueError, KeyError, OSError, TimeoutError, subprocess.SubprocessError) as error:
        raise SystemExit(f'Physical acquisition stopped: {error}; partial logs are preserved')


if __name__ == '__main__':
    main()
