"""Serial and register parser controls contain only synthetic fixtures."""
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path

from acquire import Serial, capture
from config import PLAN_SHA256, PROFILES
from protocol import decode


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        profile = PROFILES['NUCLEO-F411RE']
        self.ready = {'event': 'ready', 'board': 'NUCLEO-F411RE', 'mcu': profile['mcu'],
                      'variant': 'baseline', 'kind': 'bench', 'plan_sha256': PLAN_SHA256,
                      'cpuid': 0x410fc241, 'dbg_idcode': profile['device_id'],
                      'uid0': 1, 'uid1': 2, 'uid2': 3, 'flash_kib': 512,
                      'nominal_cpu_hz': 16000000, 'rcc_cr': 3, 'rcc_cfgr': 0,
                      'flash_acr': 0, 'cpacr': 0, 'primask': 1}

    def text(self, ready, code=0):
        return json.dumps(ready) + '\n{}\n' + json.dumps({'event': 'done', 'exit_code': code}) + '\n'

    def decode(self, text):
        return decode(text, 'NUCLEO-F411RE', 'baseline', 'bench')

    def test_register_constraints_and_failed_exit(self):
        self.assertEqual(self.decode(self.text(self.ready))[0], self.ready)
        faults = {'board': 'unknown', 'mcu': 'unknown', 'variant': 'our', 'cpuid': 0,
                  'plan_sha256': '0' * 64, 'dbg_idcode': 0, 'flash_kib': 0,
                  'nominal_cpu_hz': 0, 'rcc_cfgr': 4, 'rcc_cr': 1,
                  'flash_acr': 1, 'cpacr': 15 << 20, 'primask': 0, 'synthetic': True}
        for key, value in faults.items():
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    self.decode(self.text(dict(self.ready, **{key: value})))
        with self.assertRaises(ValueError):
            self.decode(self.text(self.ready, 1))

    def test_capture_handshake_and_complete_raw_log(self):
        master, slave = os.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        port = Serial(os.ttyname(slave))
        self.addCleanup(port.close)
        failures = []
        def firmware():
            try:
                os.write(master, json.dumps(dict(self.ready, synthetic=True)).encode() + b'\n')
                if os.read(master, 1) != b'R':
                    failures.append('wrong start command')
                os.write(master, b'{"op":"overhead","sample":0,"cycles":7}\n'
                                b'{"event":"done","exit_code":0}\n')
            except OSError as error:
                failures.append(str(error))
        thread = threading.Thread(target=firmware)
        thread.start()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'synthetic.txt'
            seconds = capture(port, path, 2)
            self.assertGreater(seconds, 0)
            self.assertEqual(len(path.read_text().splitlines()), 3)
            with self.assertRaisesRegex(ValueError, 'synthetic'):
                self.decode(path.read_text())
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertFalse(failures)


if __name__ == '__main__':
    unittest.main()
