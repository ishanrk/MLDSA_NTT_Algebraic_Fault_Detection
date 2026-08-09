#!/usr/bin/env python3
"""Record connected ST-Link candidates without guessing a board or MCU."""
import argparse
import datetime
import json
import platform
import shutil
import subprocess
from pathlib import Path


def stlink(text):
    return any(name in text.lower() for name in ('st-link', 'stlink', 'stm32 nucleo'))


def discover():
    linux = []
    for device in sorted(Path('/sys/bus/usb/devices').glob('*')):
        def read(name):
            path = device / name
            return path.read_text().strip() if path.exists() else None
        product = read('product')
        if product and stlink(product):
            linux.append({'sysfs_device': device.name, 'product': product,
                          'vendor_id': read('idVendor'), 'product_id': read('idProduct'),
                          'serial': read('serial')})
    windows, errors = [], []
    usbipd = shutil.which('usbipd.exe')
    version = None
    if usbipd:
        try:
            version = subprocess.check_output([usbipd, '--version'], text=True,
                                              timeout=15).strip()
            state = json.loads(subprocess.check_output([usbipd, 'state'], text=True,
                                                       timeout=15))
            for device in state['Devices']:
                if stlink(device.get('Description', '')) and device.get('BusId'):
                    windows.append({key: device.get(key) for key in
                                    ('BusId', 'Description', 'HardwareId', 'ClientIPAddress')})
        except (subprocess.SubprocessError, ValueError, KeyError) as error:
            errors.append(str(error))
    ports = sorted({str(path.resolve()) for pattern in
                    ('/dev/serial/by-id/*', '/dev/ttyACM*', '/dev/ttyUSB*')
                    for path in Path('/').glob(pattern.lstrip('/'))})
    return {'schema_version': 1, 'purpose': 'physical hardware discovery only',
            'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'host_kernel': platform.release(), 'usbipd_version': version,
            'linux_stlink_candidates': linux, 'windows_stlink_candidates': windows,
            'linux_serial_candidates': ports, 'discovery_errors': errors,
            'connected_stlink_observed': bool(linux or windows),
            'linux_stlink_observed': bool(linux),
            'exact_nucleo_model': None, 'exact_stm32_mcu': None,
            'physical_measurements': 'pending',
            'note': 'USB product strings identify probe candidates, not the Nucleo model '
                    'or target MCU. Confirm both before selecting a linker or flashing.'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    result = json.dumps(discover(), indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result)
    print(result, end='')


if __name__ == '__main__':
    main()
